"""Maps upstream Gemini failures to HTTP status codes and actionable messages."""
from typing import Tuple

from fastapi import status

_KEY_PATTERNS = ("API_KEY_INVALID", "API key not valid", "API_KEY_SERVICE_BLOCKED", "IP_NOT_PERMITTED")
_OFFLINE_HINT = "or switch to Offline Deterministic Mode in Advanced Settings."


def classify_llm_error(err: Exception, model_name: str, stage: str) -> Tuple[int, str]:
    text, lower = str(err), str(err).lower()
    invalid_key = (any(p in text for p in _KEY_PATTERNS)
                   or ("api key" in lower or "api_key" in lower) and any(
                       w in lower for w in ("invalid", "rejected", "not valid", "unauthorized", "expired", "missing"))
                   or "PERMISSION_DENIED" in text or "UNAUTHENTICATED" in text)
    if invalid_key:
        return (status.HTTP_401_UNAUTHORIZED,
                "The provided Gemini API key is invalid or has been rejected by Google AI (API_KEY_INVALID). "
                "Please verify your API key in Configure Key or set a valid GEMINI_API_KEY in your environment, "
                + _OFFLINE_HINT)
    if "404" in text or "NOT_FOUND" in text or "not found" in lower:
        return (status.HTTP_404_NOT_FOUND,
                f"Configured Gemini model '{model_name}' was not found or is no longer available during {stage} "
                f"(404 NOT_FOUND: {text}). Please update the GEMINI_MODEL environment variable "
                f"(e.g., 'gemini-1.5-flash'), " + _OFFLINE_HINT)
    if "429" in text or "RESOURCE_EXHAUSTED" in text or "ResourceExhausted" in text or "quota" in lower:
        return (status.HTTP_502_BAD_GATEWAY,
                f"Gemini API {stage} failed with model '{model_name}': Google GenAI RateLimit (429 ResourceExhausted). "
                "You can retry the audit, check your API key/network, " + _OFFLINE_HINT)
    return (status.HTTP_502_BAD_GATEWAY,
            f"Gemini API {stage} failed with model '{model_name}': {text}. "
            "You can retry the audit, check your API key/network, " + _OFFLINE_HINT)
