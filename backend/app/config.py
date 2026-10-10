import os
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "Second Opinion API"
    DEBUG: bool = True
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEFAULT_TOP_K: int = 3
    SIMILARITY_THRESHOLD: float = 0.20

settings = Settings()
