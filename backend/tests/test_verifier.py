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

@pytest.mark.requires_nli
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

@pytest.mark.requires_nli
def test_synonymous_statement_semantic_verification():
    request = AuditRequest(
        answer_text="Sleep is essential for our body.",
        documents=[
            DocumentInput(
                filename="health_guide.txt",
                content="Sleep is important for our body."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    
    response = AuditEngine.run_audit(request)
    
    assert response.summary.total_claims == 1
    assert response.summary.supported_count == 1
    assert response.claims[0].verdict == VerdictEnum.SUPPORTED

def test_call_gemini_with_retry_handles_503(monkeypatch):
    from app.config import call_gemini_with_retry

    calls = []

    class MockModels:
        def generate_content(self, model, contents, config):
            calls.append(model)
            if len(calls) < 2:
                raise Exception("503 UNAVAILABLE: Model experiencing high demand.")
            class MockResp:
                text = '{"status": "ok"}'
            return MockResp()

    class MockClient:
        models = MockModels()

    # Fast-forward time.sleep during test
    monkeypatch.setattr("time.sleep", lambda s: None)

    resp = call_gemini_with_retry(
        client=MockClient(),
        model_name="gemini-1.5-flash",
        contents="test",
        config=None,
        max_retries=2
    )

@pytest.mark.requires_nli
def test_sleep_guide_full_verification():
    answer_text = (
        "Sleep is an important part of a healthy lifestyle. "
        "Getting 7–9 hours of sleep is generally recommended for most adults. "
        "Proper sleep helps improve memory, concentration, and overall well-being. "
        "However, sleeping for only two hours every night is enough for every adult to maintain good health. "
        "Maintaining a regular sleep schedule can improve sleep quality. "
        "Using a mobile phone immediately before bedtime always improves sleep quality. "
        "Lack of sleep can cause tiredness and difficulty concentrating. "
        "Although proper sleep is necessary for good health, humans can function perfectly well without sleeping for several consecutive days. "
        "Therefore, sleep plays an important role in maintaining physical and mental health."
    )
    doc_text = (
        "Sleep is essential and an important part of a healthy lifestyle. "
        "Getting 7–9 hours of sleep is generally recommended for most adults. "
        "Proper sleep helps improve memory, concentration, and overall well-being. "
        "Sleeping for only two hours is insufficient and harmful to health. "
        "Maintaining a regular sleep schedule can improve sleep quality. "
        "Using a mobile phone before bedtime reduces sleep quality due to blue light. "
        "Lack of sleep can cause tiredness and difficulty concentrating. "
        "Humans cannot function well without sleeping for several consecutive days. "
        "Sleep plays an important role in maintaining physical and mental health."
    )
    request = AuditRequest(
        answer_text=answer_text,
        documents=[DocumentInput(filename="sleep_guide.txt", content=doc_text)],
        options={"force_deterministic_fallback": True}
    )
    response = AuditEngine.run_audit(request)

    verdicts = {c.text: c.verdict for c in response.claims}
    
    assert verdicts["Sleep is an important part of a healthy lifestyle."] in (VerdictEnum.SUPPORTED, VerdictEnum.AMBIGUOUS)
    assert verdicts["Getting 7–9 hours of sleep is generally recommended for most adults."] == VerdictEnum.SUPPORTED
    assert verdicts["Proper sleep helps improve memory, concentration, and overall well-being."] == VerdictEnum.SUPPORTED
    assert verdicts["However, sleeping for only two hours every night is enough for every adult to maintain good health."] == VerdictEnum.CONTRADICTED
    assert verdicts["Maintaining a regular sleep schedule can improve sleep quality."] == VerdictEnum.SUPPORTED
    assert verdicts["Using a mobile phone immediately before bedtime always improves sleep quality."] == VerdictEnum.CONTRADICTED
    assert verdicts["Lack of sleep can cause tiredness and difficulty concentrating."] == VerdictEnum.SUPPORTED
    assert verdicts["Although proper sleep is necessary for good health, humans can function perfectly well without sleeping for several consecutive days."] == VerdictEnum.CONTRADICTED
    assert verdicts["Therefore, sleep plays an important role in maintaining physical and mental health."] == VerdictEnum.SUPPORTED



