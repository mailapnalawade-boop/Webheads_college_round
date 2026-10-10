"""Internal-consistency checks between the claims of ONE answer (no source needed)."""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types

from app.config import call_gemini_with_retry, settings
from app.core.entity_check import compare_entities
from app.core.nli import NLIModel
from app.core.text_utils import containment, negation_parity_differs
from app.schemas.audit import LogicalInconsistencyItem

logger = logging.getLogger("second_opinion.consistency")
NLI_CONFLICT_THRESHOLD = 0.85
MIN_SHARED_CONTEXT = 2


def find_local_conflicts(claims: List[Dict[str, Any]], nli: Optional[NLIModel]) -> List[Dict[str, str]]:
    """Value mismatches, polarity flips and (if available) NLI contradictions between claim pairs."""
    pairs = _related_pairs(claims)
    conflicts: List[Dict[str, str]] = []
    nli_candidates: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for a, b in pairs:
        reason = _rule_conflict(a, b)
        if reason:
            conflicts.append(_conflict(a, b, reason))
        else:
            nli_candidates.append((a, b))
    if nli and nli_candidates:
        conflicts.extend(_nli_conflicts(nli, nli_candidates))
    return conflicts


def _related_pairs(claims: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    scored = []
    for i, a in enumerate(claims):
        for b in claims[i + 1:]:
            cmp = compare_entities(a["text"], b["text"])
            shared = max(cmp.context_overlap, int(10 * containment(a["text"], b["text"])))
            if shared >= MIN_SHARED_CONTEXT:
                scored.append((shared, a, b))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [(a, b) for _, a, b in scored[: settings.MAX_CONFLICT_PAIRS]]


def _rule_conflict(a: Dict[str, Any], b: Dict[str, Any]) -> Optional[str]:
    cmp = compare_entities(a["text"], b["text"])
    if cmp.has_verified_mismatch:
        m = cmp.mismatches[0]
        return f"The answer gives two different values for the same thing: '{m.claim_entity.text}' vs '{m.source_entity.text}'."
    if negation_parity_differs(a["text"], b["text"]) and min(containment(a["text"], b["text"]), containment(b["text"], a["text"])) >= 0.85:
        return "One statement asserts what the other negates."
    return None


def _nli_conflicts(nli: NLIModel, pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> List[Dict[str, str]]:
    """Contradiction must hold in BOTH directions on average, which removes one-way false alarms."""
    forward = nli.predict_batch([(b["text"], a["text"]) for a, b in pairs])
    backward = nli.predict_batch([(a["text"], b["text"]) for a, b in pairs])
    return [_conflict(a, b, "The meaning of these two statements is incompatible (NLI contradiction).")
            for (a, b), f, r in zip(pairs, forward, backward)
            if (f.contradiction + r.contradiction) / 2 >= NLI_CONFLICT_THRESHOLD]


def _conflict(a: Dict[str, Any], b: Dict[str, Any], reason: str) -> Dict[str, str]:
    return {"claim_id_1": a["claim_id"], "claim_id_2": b["claim_id"],
            "reason": f"Claim {a['claim_id']} ('{a['text']}') vs Claim {b['claim_id']} ('{b['text']}'): {reason}"}


def find_llm_conflicts(claims: List[Dict[str, Any]], api_key: str, model_name: Optional[str]) -> List[Dict[str, str]]:
    """Reasoning-level check by the LLM (contradictions and non-sequiturs)."""
    payload = [{"claim_id": c["claim_id"], "text": c["text"]} for c in claims]
    prompt = f"""You are a formal logic auditor. Inspect these atomic claims from ONE AI-generated answer.
Flag only CLEAR mutual contradictions (conflicting values/outcomes for the same subject) or non-sequiturs
(a conclusion that does not follow from the other claims). Do not flag complementary claims.

CLAIMS:
{json.dumps(payload, indent=2)}

Return ONLY JSON: {{"conflicts": [{{"claim_id_1": "...", "claim_id_2": "...", "inconsistency_type": "mutual_contradiction"|"non_sequitur", "explanation": "..."}}]}}"""
    client = genai.Client(api_key=(api_key or "").strip().strip('"').strip("'"))
    resp = call_gemini_with_retry(client=client, model_name=model_name or settings.DEFAULT_MODEL, contents=prompt,
                                  config=types.GenerateContentConfig(temperature=0.0, response_mime_type="application/json"))
    text = resp.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(text).get("conflicts", [])


def to_items(conflicts: List[Dict[str, Any]], claims: List[Dict[str, Any]], start_index: int = 0,
             kind: str = "mutual_contradiction") -> List[LogicalInconsistencyItem]:
    text_of = {c["claim_id"]: c["text"] for c in claims}
    items = []
    for n, c in enumerate(conflicts):
        c1, c2 = c.get("claim_id_1"), c.get("claim_id_2")
        if not c1 or not c2 or c1 == c2:
            continue
        items.append(LogicalInconsistencyItem(
            conflict_id=f"conflict_{start_index + len(items) + 1}", claim_id_1=c1, claim_id_2=c2,
            claim_text_1=text_of.get(c1, ""), claim_text_2=text_of.get(c2, ""),
            inconsistency_type=c.get("inconsistency_type", kind),
            explanation=c.get("reason") or c.get("explanation") or "Claims assert mutually incompatible statements."))
    return items
