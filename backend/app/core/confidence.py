"""Calibrated-by-construction confidence: built from measurable signals, never self-reported by an LLM."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

MIN_CONF, MAX_CONF = 0.05, 0.97
CONFLICT_CAP = 0.55
LEXICAL_ONLY_CAP = 0.80


@dataclass
class Signals:
    """Everything that can raise or lower our belief in a verdict. None = signal not available."""
    nli_probability: Optional[float] = None      # probability of the NLI label matching the verdict
    entity_verified: Optional[bool] = None       # True: hard value mismatch / clean match confirms verdict
    retrieval_relevance: Optional[float] = None  # 0..1 relevance of the best passage
    containment: Optional[float] = None          # share of claim content words found in source (no-NLI mode)
    quote_verified: Optional[bool] = None        # LLM mode: quoted evidence really exists in the passage
    llm_local_agreement: Optional[bool] = None   # LLM verdict agrees with the independent local judge
    conflicting: bool = False
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return {k: v for k, v in self.__dict__.items() if v not in (None, [], False) or k == "conflicting"}


def compute_confidence(signals: Signals, lexical_only: bool = False) -> Tuple[float, Dict[str, object]]:
    parts: List[Tuple[float, float]] = []  # (value, weight)
    if signals.nli_probability is not None:
        parts.append((signals.nli_probability, 0.50))
    if signals.entity_verified is not None:
        parts.append((0.92 if signals.entity_verified else 0.35, 0.30))
    if signals.retrieval_relevance is not None:
        parts.append((min(1.0, signals.retrieval_relevance / 0.6), 0.15))
    if signals.containment is not None and signals.nli_probability is None:
        parts.append((signals.containment, 0.30))
    if signals.quote_verified is not None:
        parts.append((1.0 if signals.quote_verified else 0.2, 0.40))
    if signals.llm_local_agreement is not None:
        parts.append((0.95 if signals.llm_local_agreement else 0.30, 0.30))
    if not parts:
        return 0.40, signals.as_dict()
    score = sum(v * w for v, w in parts) / sum(w for _, w in parts)
    if lexical_only:
        score = min(score, LEXICAL_ONLY_CAP)
    if signals.conflicting:
        score = min(score, CONFLICT_CAP)
    return round(max(MIN_CONF, min(MAX_CONF, score)), 2), signals.as_dict()
