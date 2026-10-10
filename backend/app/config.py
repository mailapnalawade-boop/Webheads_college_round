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
        "gemini-3.8-flash"
    )
    return model.strip().strip('"').strip("'")

class Settings(BaseModel):
    APP_NAME: str = "Second Opinion API"
    DEBUG: bool = True
    GEMINI_API_KEY: str = Field(default_factory=_resolve_gemini_api_key)
    DEFAULT_MODEL: str = Field(default_factory=_resolve_gemini_model)
    DEFAULT_TOP_K: int = 3
    SIMILARITY_THRESHOLD: float = 0.20

settings = Settings()

