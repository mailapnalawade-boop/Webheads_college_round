import pytest
from app.schemas.audit import AuditRequest, DocumentInput, VerdictEnum
from app.core.verifier import AuditEngine

def test_audit_engine_contradiction_detection():
    request = AuditRequest(
        answer_text="The patient was prescribed 50mg of Amoxicillin once daily.",
        documents=[
            DocumentInput(
                filename="protocol.txt",
                content="Standard protocol: Administer 500mg Amoxicillin three times daily for pneumonia."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    
    response = AuditEngine.run_audit(request)
    
    assert response.summary.total_claims == 1
    assert response.summary.contradicted_count == 1
    assert response.claims[0].verdict == VerdictEnum.CONTRADICTED

def test_audit_engine_supported_detection():
    request = AuditRequest(
        answer_text="Standard dosage of Amoxicillin is 500mg three times daily.",
        documents=[
            DocumentInput(
                filename="protocol.txt",
                content="Standard protocol: Administer 500mg Amoxicillin three times daily for pneumonia."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    
    response = AuditEngine.run_audit(request)
    
    assert response.summary.total_claims == 1
    assert response.summary.supported_count == 1
    assert response.claims[0].verdict == VerdictEnum.SUPPORTED
