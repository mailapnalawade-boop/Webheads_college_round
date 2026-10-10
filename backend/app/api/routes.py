from fastapi import APIRouter, HTTPException, status
from app.schemas.audit import AuditRequest, AuditResponse
from app.core.verifier import AuditEngine

router = APIRouter()

@router.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "Second Opinion AI Answer Auditor Engine",
        "version": "1.0.0"
    }

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
        }
    }
