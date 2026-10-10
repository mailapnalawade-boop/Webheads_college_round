import os
from pydantic import BaseModel, Field

def _load_env_file():
    """Simple parser for .env file if present without requiring external libraries."""
    candidate_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), "..", ".env"),
    ]
    seen = set()
    for env_path in candidate_paths:
        norm_path = os.path.abspath(env_path)
        if norm_path not in seen and os.path.exists(norm_path):
            seen.add(norm_path)
            try:
                with open(norm_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip('"').strip("'")
                            if not os.environ.get(k):
                                os.environ[k] = v
            except Exception:
                pass

    # Normalize aliases: if GOOGLE_API_KEY is present and GEMINI_API_KEY is not, map it
    if not os.environ.get("GEMINI_API_KEY"):
        alias = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_GENAI_API_KEY") or os.environ.get("API_KEY")
        if alias:
            os.environ["GEMINI_API_KEY"] = alias

_load_env_file()

def _resolve_gemini_api_key() -> str:
    key = (
        os.getenv("GEMINI_API_KEY") or
        os.getenv("GOOGLE_API_KEY") or
        os.getenv("GOOGLE_GENAI_API_KEY") or
        os.getenv("API_KEY") or
        ""
    )
    return key.strip().strip('"').strip("'")

def _resolve_gemini_model() -> str:
    model = (
        os.getenv("GEMINI_MODEL") or
        os.getenv("GOOGLE_GENAI_MODEL") or
        os.getenv("MODEL_NAME") or
        "gemini-2.5-flash"
    )
    return model.strip().strip('"').strip("'")

class Settings(BaseModel):
    APP_NAME: str = "Second Opinion API"
    DEBUG: bool = True
    GEMINI_API_KEY: str = Field(default_factory=_resolve_gemini_api_key)
    DEFAULT_MODEL: str = Field(default_factory=_resolve_gemini_model)
    DEFAULT_TOP_K: int = 3
    SIMILARITY_THRESHOLD: float = 0.20

    # --- Semantic verification (meaning-based, not keyword-based) ---
    ENABLE_SEMANTIC_MODELS: bool = Field(default_factory=lambda: os.getenv("SO_ENABLE_SEMANTIC_MODELS", "1") != "0")
    NLI_MODEL_NAME: str = Field(default_factory=lambda: os.getenv("SO_NLI_MODEL", "cross-encoder/nli-deberta-v3-small"))
    EMBEDDING_MODEL_NAME: str = Field(default_factory=lambda: os.getenv("SO_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    NLI_ENTAIL_THRESHOLD: float = 0.70
    NLI_CONTRADICT_THRESHOLD: float = 0.70
    NLI_NEUTRAL_FLOOR: float = 0.25
    SEMANTIC_MIN_SIMILARITY: float = 0.35
    MAX_CANDIDATE_SENTENCES: int = 6
    MAX_CONFLICT_PAIRS: int = 40
    AUDIT_CACHE_SIZE: int = 128

settings = Settings()

import time
import logging
from typing import Any

logger = logging.getLogger("second_opinion.gemini")
FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]

def call_gemini_with_retry(
    client: Any,
    model_name: str,
    contents: Any,
    config: Any,
    max_retries: int = 3
) -> Any:
    """
    Executes Gemini generate_content with automatic exponential backoff retry logic
    and fallback model support for transient 503 UNAVAILABLE / 429 high demand spikes.
    """
    primary = model_name or settings.DEFAULT_MODEL
    models_to_try = [primary]
    for fb in FALLBACK_MODELS:
        if fb != primary and fb not in models_to_try:
            models_to_try.append(fb)

    last_exception = None

    for current_model in models_to_try:
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=current_model,
                    contents=contents,
                    config=config
                )
                return response
            except Exception as e:
                last_exception = e
                err_str = str(e)
                err_lower = err_str.lower()

                # Don't retry on fatal auth errors (401 / API_KEY_INVALID)
                is_invalid_key = any(pattern in err_str for pattern in [
                    "API_KEY_INVALID", "API key not valid", "API_KEY_SERVICE_BLOCKED",
                    "IP_NOT_PERMITTED", "PERMISSION_DENIED", "UNAUTHENTICATED"
                ])
                if is_invalid_key:
                    raise e

                is_transient = any(token in err_str or token in err_lower for token in [
                    "503", "unavailable", "429", "resource_exhausted", "high demand", "overloaded", "500", "502", "504"
                ])

                if is_transient and attempt < max_retries - 1:
                    sleep_time = (attempt + 1) * 1.5
                    logger.warning(f"Gemini model '{current_model}' hit transient high demand ({err_str[:80]}). Retrying in {sleep_time}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"Gemini model '{current_model}' attempt {attempt + 1} failed: {err_str[:100]}.")
                    break

    if last_exception:
        raise last_exception


