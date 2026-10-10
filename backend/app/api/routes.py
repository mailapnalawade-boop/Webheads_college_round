import os
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.config import settings
from app.schemas.audit import AuditRequest, AuditResponse
from app.core.verifier import AuditEngine

router = APIRouter()

class ConfigUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    model: Optional[str] = None

class ModelCheckRequest(BaseModel):
    api_key: Optional[str] = None

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

@router.post("/config", tags=["Configuration"])
def update_config(body: ConfigUpdateRequest):
    """
    Dynamically configures or updates API key and default model settings in memory.
    Ensures secure configuration without persisting secrets to version control.
    """
    key_input = body.gemini_api_key if body.gemini_api_key is not None else body.api_key
    if key_input is not None:
        clean_key = key_input.strip().strip('"').strip("'")
        settings.GEMINI_API_KEY = clean_key
        os.environ["GEMINI_API_KEY"] = clean_key

    model_input = body.default_model if body.default_model is not None else body.model
    if model_input is not None:
        clean_model = model_input.strip().strip('"').strip("'")
        if clean_model:
            settings.DEFAULT_MODEL = clean_model
            os.environ["GEMINI_MODEL"] = clean_model

    return get_config()

@router.api_route("/model-check", methods=["GET", "POST"], tags=["Configuration"])
def check_model_availability(api_key: Optional[str] = None, body: Optional[ModelCheckRequest] = None):
    """
    Performs a minimal health check against the configured Gemini model using the backend or provided API key.
    Supports GET query parameters or POST JSON payload body for secure key transmission without URL logging.
    """
    raw_key = None
    if body and body.api_key is not None:
        raw_key = body.api_key
    elif api_key is not None:
        raw_key = api_key

    effective_key = (
        raw_key if raw_key is not None
        else (settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "")
    ).strip().strip('"').strip("'")

    if not effective_key:
        return {
            "status": "unconfigured",
            "model": settings.DEFAULT_MODEL,
            "message": "GEMINI_API_KEY is not configured on backend and no key was supplied."
        }
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=effective_key)
        resp = client.models.generate_content(
            model=settings.DEFAULT_MODEL,
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

@router.get("/sample", tags=["Benchmark Samples"])
def get_sample_data():
    """
    Returns pre-loaded benchmark audit datasets for instant hackathon demonstration.
    """
    return {
        "medical_case": {
            "title": "Clinical Treatment Plan Audit",
            "answer_text": "The patient was diagnosed with community-acquired pneumonia. The recommended dose of Amoxicillin is 50mg taken once daily. Treatment should be discontinued immediately if mild cough occurs.",
            "documents": [
                {
                    "filename": "clinical_guidelines_2026.txt",
                    "content": "Official Treatment Protocol 2026:\n\nFor adult community-acquired pneumonia, the standard recommended dosage of Amoxicillin is 500mg to 1000mg orally three times daily for 5 to 7 days.\n\nMild cough is a normal expected symptom during respiratory recovery and does not warrant discontinuing antibiotic treatment unless severe adverse allergic reactions occur."
                }
            ]
        },
        "financial_case": {
            "title": "Quarterly Financial Report Audit",
            "answer_text": "Acme Corp reported Q3 revenue of $45 million, representing a 20% year-over-year decrease. Net profit margin increased to 35% driven by server expansion costs.",
            "documents": [
                {
                    "filename": "acme_q3_report.txt",
                    "content": "Acme Corp Q3 Financial Statement:\n\nAcme Corp achieved Q3 revenue of $45 million, marking a 20% year-over-year increase compared to Q3 prior year.\n\nNet profit margin stood at 18%, impacted by server infrastructure expansion costs."
                }
            ]
        },
        "logical_conflict_case": {
            "title": "Internal Logic & Metrics Inconsistency",
            "answer_text": "Project Orion delivered 150MW of green power in 2025. Total energy output from Project Orion in 2025 was only 85MW. Consequently, the facility exceeded its annual operational target.",
            "documents": [
                {
                    "filename": "project_orion_charter.txt",
                    "content": "Project Orion Charter 2025:\n\nProject Orion is a renewable clean power initiative that commenced commercial operations in early 2025 to supply regional grid electricity."
                }
            ]
        }
    }
