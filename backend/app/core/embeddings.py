"""Sentence embeddings for meaning-based retrieval (finds 'car' when the claim says 'automobile')."""
import logging
from typing import List, Optional, Sequence

logger = logging.getLogger("second_opinion.embeddings")


class SentenceEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # heavy import kept lazy
        self.name = model_name
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: Sequence[str]) -> List[List[float]]:
        """L2-normalised vectors, so a dot product is the cosine similarity."""
        if not texts:
            return []
        return self._model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False).tolist()

    def similarities(self, query: str, texts: Sequence[str]) -> List[float]:
        if not texts:
            return []
        q = self.encode([query])[0]
        return [sum(a * b for a, b in zip(q, v)) for v in self.encode(texts)]


def load_embedder(model_name: str) -> Optional[SentenceEmbedder]:
    try:
        return SentenceEmbedder(model_name)
    except Exception as err:
        logger.warning("Embedding model '%s' unavailable (%s: %s). Retrieval falls back to BM25 only.",
                       model_name, type(err).__name__, err)
        return None
