"""Gemini-based semantic verification, hardened so the LLM cannot make unverifiable claims.

The LLM reads meaning; code then verifies its output: a SUPPORTED/CONTRADICTED verdict must
quote the source verbatim and the quote must actually exist in the cited passage, otherwise
the verdict is downgraded. Confidence is never self-reported: it comes from verification
signals (quote check + agreement with the independent local judge).
"""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

from google import genai
from google.genai import types

from app.config import call_gemini_with_retry, settings
from app.core.confidence import Signals, compute_confidence
from app.core.judge import ClaimSpan, Judgement
from app.schemas.audit import ErrorCategory, VerdictEnum

logger = logging.getLogger("second_opinion.llm_verifier")
_VALID = {v.value for v in (VerdictEnum.SUPPORTED, VerdictEnum.CONTRADICTED,
                            VerdictEnum.INSUFFICIENT_EVIDENCE, VerdictEnum.AMBIGUOUS)}


@dataclass
class LLMVerdict:
    verdict: VerdictEnum
    explanation: str
    supporting_idx: List[int] = field(default_factory=list)
    contradicting_idx: List[int] = field(default_factory=list)
    source_disagreement: bool = False
    quote_verified: Optional[bool] = None
    error_text: Optional[str] = None

    @property
    def confidence_hint(self) -> float:
        if self.quote_verified:
            return 0.90
        return 0.40 if self.quote_verified is False else 0.50

    def __iter__(self) -> Iterator[Any]:  # keeps the legacy 6-tuple contract of _verify_with_gemini
        yield from (self.verdict, self.confidence_hint, self.explanation, self.supporting_idx,
                    self.contradicting_idx, self.source_disagreement)


def coerce_llm_result(raw: Any) -> LLMVerdict:
    """Accept an LLMVerdict or the legacy (verdict, conf, explanation, sup, con, disagree) tuple."""
    if isinstance(raw, LLMVerdict):
        return raw
    verdict, _conf, explanation, sup, con, disagree = raw
    return LLMVerdict(verdict, explanation, list(sup), list(con), bool(disagree))


def _norm(text: str) -> str:
    text = re.sub(r"[\"“”‘’'`]", "", text.lower())
    return re.sub(r"\s+", " ", text).strip(" .…")


def quote_exists(quote: str, passage: str) -> bool:
    q = _norm(quote.replace("...", " ").replace("…", " "))
    return len(q) >= 8 and q in _norm(passage)


def build_prompt(claim: str, evidence: Sequence[Dict[str, Any]]) -> str:
    passages = "\n\n".join(
        f"[{i}] Source: {e['source_name']} (Page {e.get('page_number', 1)}):\n\"{e['excerpt']}\"" for i, e in enumerate(evidence)
    ) or "No relevant reference passages were found."
    return f"""You are a rigorous, evidence-grounded AI Answer Auditor. Judge the CLAIM against the REFERENCE PASSAGES by MEANING, not by shared words.

CLAIM:
"{claim}"

REFERENCE PASSAGES:
{passages}

VERDICTS:
- SUPPORTED: a passage states or entails the claim (paraphrases and synonyms count).
- CONTRADICTED: a passage states something incompatible with the claim (different number, name, date, polarity or outcome).
- INSUFFICIENT_EVIDENCE: the passages do not address the claim. Absence of evidence is NOT contradiction.
- AMBIGUOUS: evidence is partial, vague, or the passages disagree with each other.

RULES:
- Use only the passages. Never use outside knowledge, never invent sources.
- For SUPPORTED or CONTRADICTED you MUST copy one exact, contiguous sentence or phrase from a passage into "evidence_quote" (verbatim, no edits).
- For CONTRADICTED, put the exact words of the CLAIM that are wrong in "error_text" (a verbatim substring of the claim).
- Do not report a confidence number.

Return ONLY JSON:
{{"verdict": "SUPPORTED|CONTRADICTED|INSUFFICIENT_EVIDENCE|AMBIGUOUS", "explanation": "1-2 sentences",
  "passage_index": 0, "evidence_quote": "verbatim text or empty", "error_text": "verbatim claim words or empty",
  "source_disagreement": false}}"""


def parse_llm_response(raw_text: str, claim: str, evidence: Sequence[Dict[str, Any]]) -> LLMVerdict:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    data = json.loads(text)
    verdict_str = str(data.get("verdict", "INSUFFICIENT_EVIDENCE")).upper()
    verdict = VerdictEnum(verdict_str if verdict_str in _VALID else "INSUFFICIENT_EVIDENCE")
    explanation = str(data.get("explanation", "")).strip() or "Evaluated against the reference passages."
    idx = data.get("passage_index")
    idx = idx if isinstance(idx, int) and 0 <= idx < len(evidence) else None
    quote_ok: Optional[bool] = None
    if verdict in (VerdictEnum.SUPPORTED, VerdictEnum.CONTRADICTED):
        quote = str(data.get("evidence_quote", "") or "")
        pool = [evidence[idx]] if idx is not None else list(evidence)
        found = next((i for i, e in enumerate(pool) if quote_exists(quote, e["excerpt"])), None) if quote else None
        quote_ok = found is not None
        if quote_ok:
            idx = idx if idx is not None else found
        else:
            verdict = VerdictEnum.INSUFFICIENT_EVIDENCE
            explanation = "Downgraded: the model's quoted evidence could not be found verbatim in the source. " + explanation
    error_text = str(data.get("error_text", "") or "").strip()
    error_text = error_text if error_text and error_text in claim else None
    sup = [idx] if verdict == VerdictEnum.SUPPORTED and idx is not None else []
    con = [idx] if verdict == VerdictEnum.CONTRADICTED and idx is not None else []
    return LLMVerdict(verdict, explanation, sup, con, bool(data.get("source_disagreement", False)), quote_ok, error_text)


class GeminiVerifier:
    @staticmethod
    def verify(claim: str, evidence: Sequence[Dict[str, Any]], api_key: str, model_name: Optional[str] = None) -> LLMVerdict:
        client = genai.Client(api_key=(api_key or "").strip().strip('"').strip("'"))
        prompt = build_prompt(claim, evidence)
        config = types.GenerateContentConfig(temperature=0.0, response_mime_type="application/json")
        for attempt in range(2):
            response = call_gemini_with_retry(client=client, model_name=model_name or settings.DEFAULT_MODEL,
                                              contents=prompt, config=config)
            try:
                return parse_llm_response(response.text, claim, evidence)
            except (ValueError, KeyError, TypeError) as err:
                if attempt == 1:
                    raise
                logger.warning("Retrying malformed Gemini JSON (attempt %s): %s", attempt + 1, err)
        return LLMVerdict(VerdictEnum.INSUFFICIENT_EVIDENCE, "Verification inconclusive.")


def merge_with_local(local: Judgement, llm: LLMVerdict, claim: str, top_relevance: float) -> Judgement:
    """Cross-check the LLM against the independent local judge (NLI + entity checks)."""
    decisive = (VerdictEnum.SUPPORTED, VerdictEnum.CONTRADICTED)
    if llm.verdict in decisive and local.verdict in decisive and llm.verdict != local.verdict:
        sig = Signals(quote_verified=llm.quote_verified, llm_local_agreement=False, conflicting=True,
                      retrieval_relevance=top_relevance, notes=["LLM and local judge disagree"])
        conf, details = compute_confidence(sig)
        text = (f"The language model says {llm.verdict.value} but the independent semantic/entity check says "
                f"{local.verdict.value}. Treated as ambiguous. LLM: {llm.explanation} | Check: {local.explanation}")
        return Judgement(VerdictEnum.AMBIGUOUS, min(conf, 0.5), text, local.supporting_idx, local.contradicting_idx,
                         ErrorCategory.AMBIGUOUS, None, details, source_disagreement=llm.source_disagreement)
    if llm.verdict not in decisive and local.verdict == VerdictEnum.CONTRADICTED and local.category in (
            ErrorCategory.NUMERIC_MISMATCH, ErrorCategory.ENTITY_MISMATCH):
        return local  # a verified value mismatch outranks an LLM that merely abstained
    if llm.verdict == local.verdict or llm.verdict in decisive:
        return _llm_result(local, llm, claim, top_relevance, agreed=(local.verdict == llm.verdict) or None)
    return local if local.verdict in decisive else _llm_result(local, llm, claim, top_relevance, agreed=None)


def _llm_result(local: Judgement, llm: LLMVerdict, claim: str, top_rel: float, agreed: Optional[bool]) -> Judgement:
    nli_p = local.signals.get("nli_probability") if agreed else None
    sig = Signals(quote_verified=llm.quote_verified, llm_local_agreement=agreed, nli_probability=nli_p,
                  retrieval_relevance=top_rel)
    conf, details = compute_confidence(sig)
    span = local.span if llm.verdict == local.verdict else None
    if span is None and llm.verdict == VerdictEnum.CONTRADICTED and llm.error_text:
        start = claim.find(llm.error_text)
        span = ClaimSpan(start, start + len(llm.error_text), llm.error_text, "llm_verified_substring")
    category = {VerdictEnum.CONTRADICTED: local.category if local.verdict == llm.verdict and local.category
                else ErrorCategory.CONTRADICTS_SOURCE,
                VerdictEnum.INSUFFICIENT_EVIDENCE: ErrorCategory.UNSUPPORTED_CLAIM,
                VerdictEnum.AMBIGUOUS: ErrorCategory.AMBIGUOUS}.get(llm.verdict)
    return Judgement(llm.verdict, conf, llm.explanation, llm.supporting_idx, llm.contradicting_idx, category, span,
                     details, llm.source_disagreement)
