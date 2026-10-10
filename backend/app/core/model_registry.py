"""Single place that owns the (optional) semantic models. Injectable, so tests never download weights."""
import threading
from typing import Optional

from app.config import settings
from app.core.embeddings import SentenceEmbedder, load_embedder
from app.core.nli import NLIModel, load_nli


class ModelRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._nli: Optional[NLIModel] = None
        self._embedder: Optional[SentenceEmbedder] = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        with self._lock:
            if self._loaded:
                return
            if settings.ENABLE_SEMANTIC_MODELS:
                self._nli = load_nli(settings.NLI_MODEL_NAME)
                self._embedder = load_embedder(settings.EMBEDDING_MODEL_NAME)
            self._loaded = True

    @property
    def nli(self) -> Optional[NLIModel]:
        self._ensure_loaded()
        return self._nli

    @property
    def embedder(self) -> Optional[SentenceEmbedder]:
        self._ensure_loaded()
        return self._embedder

    def override(self, nli: Optional[NLIModel] = None, embedder: Optional[object] = None) -> None:
        """Inject models (tests, or a custom model). Marks the registry as loaded."""
        with self._lock:
            self._nli, self._embedder, self._loaded = nli, embedder, True

    def reset(self) -> None:
        """Forget loaded models so the next access loads them again (used by tests)."""
        with self._lock:
            self._nli, self._embedder, self._loaded = None, None, False

    def describe(self) -> dict:
        return {"nli_model": getattr(self.nli, "name", None), "embedding_model": getattr(self.embedder, "name", None)}


registry = ModelRegistry()
