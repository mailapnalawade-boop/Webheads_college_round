import os
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from app.config import settings
from app.schemas.audit import AuditRequest, AuditResponse
from app.core.verifier import AuditEngine

router = APIRouter()

@router.get("/health", tags=["Health"])
def health_check():
    effective_key = bool(
        (settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    )
    return {
        "status": "healthy",
        "service": "Second Opinion AI Answer Auditor Engine",
        "version": "1.0.0",
        "has_gemini_api_key": effective_key
    }

@router.get("/config", tags=["Configuration"])
def get_config():
    """
    Returns server capabilities and verification engine readiness
    without exposing any confidential API keys to the frontend.
    """
    effective_key = bool(
        (settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    )
    return {
        "has_gemini_api_key": effective_key,
        "default_model": settings.DEFAULT_MODEL,
        "default_top_k": settings.DEFAULT_TOP_K,
        "active_mode": "online_llm" if effective_key else "offline_deterministic",
        "offline_supported": True
    }

@router.api_route("/model-check", methods=["GET", "POST"], tags=["Configuration"])
def check_model_availability():
    """
    Performs a minimal health check against the configured Gemini model using the server-side API key.
    """
    effective_key = (settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip().strip('"').strip("'")

    if not effective_key:
        return {
            "status": "unconfigured",
            "model": settings.DEFAULT_MODEL,
            "message": "GEMINI_API_KEY is not configured on backend."
        }
    try:
        from google import genai
        from google.genai import types
        from app.config import call_gemini_with_retry
        client = genai.Client(api_key=effective_key)
        resp = call_gemini_with_retry(
            client=client,
            model_name=settings.DEFAULT_MODEL,
            contents="ping",
            config=types.GenerateContentConfig(max_output_tokens=5)
        )
        return {
            "status": "available",
            "model": settings.DEFAULT_MODEL,
            "response": resp.text.strip() if resp.text else "ok"
        }
    except Exception as e:
        status_code, err_detail = AuditEngine._classify_llm_error(e, settings.DEFAULT_MODEL, "model verification check")
        raise HTTPException(
            status_code=status_code,
            detail=err_detail
        )


@router.post("/audit", response_model=AuditResponse, tags=["Audit"])
def create_audit(request: AuditRequest):
    if not request.answer_text or not request.answer_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="answer_text cannot be empty."
        )
    try:
        response = AuditEngine.run_audit(request)
        return response
    except HTTPException:
        # Re-raise explicit HTTP exceptions with correct status code (e.g. 400, 502)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit execution error: {str(e)}"
        )
