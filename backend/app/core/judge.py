"""Claim-vs-evidence judge.

Verdict policy (in order of authority):
  1. VERIFIED VALUE MISMATCH   (number/year/frequency/name differs in the same context) -> CONTRADICTED
  2. NLI MEANING JUDGEMENT     (a trained model reads claim + source sentence together)  -> SUPPORTED / CONTRADICTED
  3. Without an NLI model the judge may only say SUPPORTED when the source states the claim almost
     verbatim, and otherwise answers AMBIGUOUS. It never guesses from word overlap alone.
Word overlap is used for ranking candidate sentences only, never to decide a verdict.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.config import settings
from app.core.confidence import Signals, compute_confidence
from app.core.entity_check import NAME, EntityComparison, Mismatch, all_values_matched, compare_entities, entity_masked
from app.core.nli import NLIModel, NLIScores
from app.core.text_utils import (STOP_WORDS, bigram_overlap, containment, content_stems, negation_parity_differs,
                                 split_sentences, stem)
from app.schemas.audit import ErrorCategory, VerdictEnum

NEAR_VERBATIM = 0.85
NEG_FLIP_MIN_CONTAINMENT = 0.85  # claim words found in source; plus the reverse direction below
NEG_FLIP_MIN_REVERSE = 0.60
MIN_PASSAGE_RELEVANCE = 0.15
MIN_ORDER_OVERLAP = 0.40  # adjacent word pairs preserved: 'A acquired B' must not pass as 'B acquired A'


@dataclass
class ClaimSpan:
    """Span relative to the claim text."""
    start: int
    end: int
    text: str
    precision: str


@dataclass
class Candidate:
    sentence: str
    evidence_idx: int
    relevance: float
    containment: float = 0.0
    entities: Optional[EntityComparison] = None
    nli: Optional[NLIScores] = None
    negation_flip: bool = False
    order_overlap: float = 1.0

    @property
    def mismatch(self) -> Optional[Mismatch]:
        if self.entities and self.entities.has_verified_mismatch:
            return self.entities.mismatches[0]
        return None


@dataclass
class Judgement:
    verdict: VerdictEnum
    confidence: float
    explanation: str
    supporting_idx: List[int] = field(default_factory=list)
    contradicting_idx: List[int] = field(default_factory=list)
    category: Optional[ErrorCategory] = None
    span: Optional[ClaimSpan] = None
    signals: Dict[str, Any] = field(default_factory=dict)
    source_disagreement: bool = False


class SemanticJudge:
    def __init__(self, nli: Optional[NLIModel] = None, embedder: Optional[Any] = None):
        self.nli = nli
        self.embedder = embedder

    # ------------------------------------------------------------------ public
    def judge(self, claim: str, evidence: Sequence[Dict[str, Any]]) -> Judgement:
        if not evidence:
            return self._insufficient("No relevant reference passage was found for this claim.", None, [])
        top_relevance = max(float(e.get("relevance_score", 0.0)) for e in evidence)
        cands = self._annotate(claim, self._candidates(claim, evidence))
        if not cands or top_relevance < MIN_PASSAGE_RELEVANCE and not any(c.mismatch for c in cands):
            return self._insufficient("Retrieved passages are not about this claim.", None, [])
        decide = self._decide_semantic if self.nli else self._decide_lexical
        return decide(claim, cands, evidence, top_relevance)

    # ------------------------------------------------------------- candidates
    def _candidates(self, claim: str, evidence: Sequence[Dict[str, Any]]) -> List[Candidate]:
        pool = [(s, i) for i, ev in enumerate(evidence) for s, _, _ in split_sentences(ev["excerpt"])]
        sims = self.embedder.similarities(claim, [s for s, _ in pool]) if self.embedder and pool else [0.0] * len(pool)
        ranked = [Candidate(s, i, 0.5 * containment(claim, s) + 0.5 * max(0.0, sim))
                  for (s, i), sim in zip(pool, sims)]
        ranked.sort(key=lambda c: c.relevance, reverse=True)
        return ranked[: settings.MAX_CANDIDATE_SENTENCES]

    def _annotate(self, claim: str, cands: List[Candidate]) -> List[Candidate]:
        for c in cands:
            c.containment, c.order_overlap = self._word_signals(claim, c.sentence)
            c.entities = compare_entities(claim, c.sentence)
            c.negation_flip = (negation_parity_differs(claim, c.sentence) and c.containment >= NEG_FLIP_MIN_CONTAINMENT
                               and containment(c.sentence, claim) >= NEG_FLIP_MIN_REVERSE)
        if self.nli and cands:
            for c, scores in zip(cands, self.nli.predict_batch([(c.sentence, claim) for c in cands])):
                c.nli = scores
        return cands

    @staticmethod
    def _word_signals(claim: str, sentence: str) -> Tuple[float, float]:
        """(containment, order overlap), counting equal values written differently (0.05 g == 50 mg) as matching."""
        cont, order = containment(claim, sentence), bigram_overlap(claim, sentence)
        if all_values_matched(claim, sentence):
            mc, ms = entity_masked(claim), entity_masked(sentence)
            cont, order = max(cont, containment(mc, ms)), max(order, bigram_overlap(mc, ms))
        return cont, order

    # ------------------------------------------------------ decision: with NLI
    def _decide_semantic(self, claim, cands, evidence, top_rel) -> Judgement:
        t_e, t_c = settings.NLI_ENTAIL_THRESHOLD, settings.NLI_CONTRADICT_THRESHOLD
        clean = [c for c in cands if not c.mismatch]
        support = max(clean, key=lambda c: c.nli.entailment, default=None)
        support = support if support and support.nli.entailment >= t_e else None
        contra = max(cands, key=lambda c: c.nli.contradiction, default=None)
        contra = contra if contra and contra.nli.contradiction >= t_c else None
        mism = max((c for c in cands if c.mismatch), key=lambda c: c.relevance, default=None)

        if (mism or contra) and support:
            bad = mism or contra
            return self._disagreement(claim, support, bad, top_rel)
        if mism:
            return self._from_mismatch(claim, mism, top_rel)
        if contra:
            return self._from_nli_contradiction(claim, contra, top_rel)
        if support:
            if support.negation_flip and support.nli.entailment < 0.90:
                return self._ambiguous("The source wording differs in negation; the meaning match is not clear-cut.",
                                       support, top_rel, conflicting=True)
            return self._supported(claim, support, top_rel, nli_prob=support.nli.entailment)
        strongest = max(max(c.nli.entailment, c.nli.contradiction) for c in cands)
        if strongest < settings.NLI_NEUTRAL_FLOOR:
            return self._insufficient("The source discusses related material but does not state or contradict this claim.",
                                      cands[0], evidence and [], top_rel)
        return self._ambiguous("The source only partly matches the claim; meaning could not be settled.", cands[0], top_rel)

    # ---------------------------------------------------- decision: no NLI model
    def _decide_lexical(self, claim, cands, evidence, top_rel) -> Judgement:
        mism = max((c for c in cands if c.mismatch), key=lambda c: c.relevance, default=None)
        verbatim = [c for c in cands if not c.mismatch and c.containment >= NEAR_VERBATIM and not c.negation_flip
                    and c.order_overlap >= MIN_ORDER_OVERLAP]
        if mism and verbatim:
            return self._disagreement(claim, verbatim[0], mism, top_rel)
        if mism:
            return self._from_mismatch(claim, mism, top_rel)
        flip = next((c for c in cands if c.negation_flip), None)
        if flip:
            return self._from_negation_flip(claim, flip, top_rel)
        if verbatim:
            return self._supported(claim, verbatim[0], top_rel, nli_prob=None)
        best = cands[0]
        if best.containment < 0.34:
            return self._insufficient("No passage states or contradicts this claim.", best, [], top_rel)
        return self._ambiguous("A related passage exists, but without the semantic (NLI) model the claim cannot be "
                               "confirmed or refuted. Not treated as an error.", best, top_rel, lexical=True)

    # --------------------------------------------------------------- builders
    def _supported(self, claim, cand, top_rel, nli_prob) -> Judgement:
        sig = Signals(nli_probability=nli_prob, retrieval_relevance=top_rel, containment=cand.containment,
                      entity_verified=True if cand.entities and not cand.entities.mismatches else None)
        conf, details = compute_confidence(sig, lexical_only=nli_prob is None)
        how = "its meaning matches (NLI)" if nli_prob is not None else "it is stated almost verbatim"
        return Judgement(VerdictEnum.SUPPORTED, conf, f"Supported: {how} — \"{cand.sentence}\"",
                         supporting_idx=[cand.evidence_idx], signals=details)

    def _from_mismatch(self, claim, cand, top_rel) -> Judgement:
        m = cand.mismatch
        nli_conflict = bool(cand.nli and cand.nli.entailment >= 0.85)
        if nli_conflict and m.kind == NAME:
            return self._ambiguous(f"The answer says '{m.claim_entity.text}' but the source says '{m.source_entity.text}', "
                                   "yet the meaning model judges them equivalent (possible alias).", cand, top_rel, conflicting=True)
        sig = Signals(nli_probability=cand.nli.contradiction if cand.nli else None, entity_verified=True,
                      retrieval_relevance=top_rel, conflicting=nli_conflict)
        conf, details = compute_confidence(sig)
        category = ErrorCategory.ENTITY_MISMATCH if m.kind == NAME else ErrorCategory.NUMERIC_MISMATCH
        span = ClaimSpan(m.claim_entity.start, m.claim_entity.end, claim[m.claim_entity.start:m.claim_entity.end], "exact")
        text = (f"Value mismatch: the answer states '{m.claim_entity.text}' but the source states "
                f"'{m.source_entity.text}' — \"{cand.sentence}\"")
        return Judgement(VerdictEnum.CONTRADICTED, conf, text, contradicting_idx=[cand.evidence_idx],
                         category=category, span=span, signals=details)

    def _from_nli_contradiction(self, claim, cand, top_rel) -> Judgement:
        sig = Signals(nli_probability=cand.nli.contradiction, retrieval_relevance=top_rel,
                      entity_verified=False if cand.entities and not cand.entities.mismatches else None)
        conf, details = compute_confidence(sig)
        text = f"The source conveys the opposite meaning (NLI contradiction {cand.nli.contradiction:.2f}) — \"{cand.sentence}\""
        return Judgement(VerdictEnum.CONTRADICTED, conf, text, contradicting_idx=[cand.evidence_idx],
                         category=ErrorCategory.CONTRADICTS_SOURCE, span=approximate_span(claim, cand.sentence),
                         signals=details)

    def _from_negation_flip(self, claim, cand, top_rel) -> Judgement:
        sig = Signals(containment=cand.containment, retrieval_relevance=top_rel, notes=["negation_flip"])
        conf, details = compute_confidence(sig, lexical_only=True)
        text = f"The answer and the source say the same thing with opposite polarity (negation) — \"{cand.sentence}\""
        return Judgement(VerdictEnum.CONTRADICTED, min(conf, 0.70), text, contradicting_idx=[cand.evidence_idx],
                         category=ErrorCategory.CONTRADICTS_SOURCE, span=approximate_span(claim, cand.sentence), signals=details)

    def _disagreement(self, claim, support, bad, top_rel) -> Judgement:
        sig = Signals(retrieval_relevance=top_rel, conflicting=True, notes=["sources disagree"])
        conf, details = compute_confidence(sig)
        text = ("Sources disagree: one passage supports the claim while another conflicts with it — "
                f"supports: \"{support.sentence}\"; conflicts: \"{bad.sentence}\"")
        return Judgement(VerdictEnum.AMBIGUOUS, min(conf, 0.5), text, supporting_idx=[support.evidence_idx],
                         contradicting_idx=[bad.evidence_idx], category=ErrorCategory.AMBIGUOUS, signals=details,
                         source_disagreement=True)

    def _ambiguous(self, reason, cand, top_rel, conflicting=False, lexical=False) -> Judgement:
        sig = Signals(retrieval_relevance=top_rel, conflicting=conflicting, containment=cand.containment if cand else None)
        conf, details = compute_confidence(sig, lexical_only=lexical)
        return Judgement(VerdictEnum.AMBIGUOUS, min(conf, 0.5), f"Ambiguous: {reason}",
                         category=ErrorCategory.AMBIGUOUS, signals=details)

    def _insufficient(self, reason, cand, _unused, top_rel: float = 0.0) -> Judgement:
        sig = Signals(retrieval_relevance=top_rel, containment=cand.containment if cand else None)
        conf, details = compute_confidence(sig)
        span = None
        return Judgement(VerdictEnum.INSUFFICIENT_EVIDENCE, round(max(0.4, min(0.7, 1.0 - top_rel)), 2),
                         f"Not verifiable from the provided sources: {reason}", category=ErrorCategory.UNSUPPORTED_CLAIM,
                         span=span, signals=details)


def approximate_span(claim: str, sentence: str) -> Optional[ClaimSpan]:
    """Longest run of claim words that the source sentence does not contain (a hint, not proof)."""
    source_stems = set(content_stems(sentence))
    words = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9.,'’%$-]*", claim)]
    flags = [w[2].lower() not in STOP_WORDS and stem(w[2].strip(".,")) not in source_stems for w in words]
    best, cur = (0, 0), None
    for i, off in enumerate(flags):
        if off:
            cur = (cur[0], i + 1) if cur else (i, i + 1)
            best = max(best, cur, key=lambda r: r[1] - r[0])
        else:
            cur = None
    if best[1] - best[0] == 0 or (best[1] - best[0]) > 0.6 * len(words):
        return None
    start, end = words[best[0]][0], words[best[1] - 1][1]
    return ClaimSpan(start, end, claim[start:end], "approximate")
