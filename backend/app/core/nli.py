"""Natural-language-inference wrapper: judges whether a source sentence entails or contradicts a claim."""
import logging
import math
from dataclasses import dataclass
from typing import List, Optional, Protocol, Sequence, Tuple

logger = logging.getLogger("second_opinion.nli")


@dataclass(frozen=True)
class NLIScores:
    entailment: float
    contradiction: float
    neutral: float


class NLIModel(Protocol):
    name: str

    def predict_batch(self, pairs: Sequence[Tuple[str, str]]) -> List[NLIScores]:
        """pairs are (premise=source sentence, hypothesis=claim)."""


class CrossEncoderNLI:
    """sentence-transformers CrossEncoder trained on SNLI/MNLI (loaded lazily, once)."""

    _DEFAULT_ORDER = ("contradiction", "entailment", "neutral")

    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder  # heavy import kept lazy
        self.name = model_name
        self._model = CrossEncoder(model_name)
        self._order = self._label_order()

    def _label_order(self) -> Tuple[str, ...]:
        try:
            id2label = self._model.model.config.id2label
            labels = [str(id2label[i]).lower() for i in range(len(id2label))]
            if sorted(self._canonical(l) for l in labels) == sorted(self._DEFAULT_ORDER):
                return tuple(self._canonical(l) for l in labels)
        except Exception:
            logger.warning("Could not read NLI label map; assuming %s", self._DEFAULT_ORDER)
        return self._DEFAULT_ORDER

    @staticmethod
    def _canonical(label: str) -> str:
        for key in ("contradiction", "entailment", "neutral"):
            if key[:5] in label:
                return key
        return label

    def predict_batch(self, pairs: Sequence[Tuple[str, str]]) -> List[NLIScores]:
        if not pairs:
            return []
        rows = self._model.predict(list(pairs))
        return [self._to_scores(list(map(float, row))) for row in rows]

    def _to_scores(self, row: List[float]) -> NLIScores:
        probs = row if _looks_like_probabilities(row) else _softmax(row)
        by_label = dict(zip(self._order, probs))
        return NLIScores(by_label["entailment"], by_label["contradiction"], by_label["neutral"])


def _looks_like_probabilities(row: List[float]) -> bool:
    return all(0.0 <= x <= 1.0 for x in row) and abs(sum(row) - 1.0) < 1e-3


def _softmax(row: List[float]) -> List[float]:
    peak = max(row)
    exps = [math.exp(x - peak) for x in row]
    total = sum(exps)
    return [e / total for e in exps]


def load_nli(model_name: str) -> Optional[NLIModel]:
    try:
        return CrossEncoderNLI(model_name)
    except Exception as err:  # missing package, offline first run, bad model name
        logger.warning("NLI model '%s' unavailable (%s: %s). Verdicts will be limited to "
                       "entity checks and near-exact matches.", model_name, type(err).__name__, err)
        return None
