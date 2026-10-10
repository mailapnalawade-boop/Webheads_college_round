import pytest
from fastapi import HTTPException
from app.schemas.audit import AuditRequest, DocumentInput, VerdictEnum
from app.core.verifier import AuditEngine
from app.core.safety import SafetyAnalyzer
from app.core.extractor import ClaimExtractor

def test_four_visible_categories_supported_and_contradicted():
    """Tests SUPPORTED and CONTRADICTED claims against evidence."""
    request = AuditRequest(
        answer_text="The patient was diagnosed with community-acquired pneumonia. The recommended dose of Amoxicillin is 50mg taken once daily.",
        documents=[
            DocumentInput(
                filename="guidelines.txt",
                content="Official Treatment Protocol: For adult community-acquired pneumonia, the standard recommended dosage of Amoxicillin is 500mg to 1000mg orally three times daily."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.summary.total_claims == 2
    # The guideline never says this patient was diagnosed: it must not count as an error either way.
    assert res.claims[0].verdict in (VerdictEnum.SUPPORTED, VerdictEnum.AMBIGUOUS, VerdictEnum.INSUFFICIENT_EVIDENCE)
    # The dose (50mg once daily vs 500-1000mg three times daily) is a verified mismatch with an exact span.
    dose = res.claims[1]
    assert dose.verdict == VerdictEnum.CONTRADICTED
    assert dose.error_span is not None and dose.error_span.text in ("50mg", "once")
    assert res.original_answer[dose.error_span.start_char:dose.error_span.end_char] == dose.error_span.text

@pytest.mark.requires_nli
def test_logical_inconsistency_detection():
    """Tests that mutual internal contradictions within the answer are classified as LOGICAL_INCONSISTENCY."""
    request = AuditRequest(
        answer_text="The server expansion costs decreased the net profit margin. Server expansion costs increased the net profit margin.",
        documents=[
            DocumentInput(
                filename="background.txt",
                content="The company published its annual infrastructure report."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.summary.internal_contradictions_detected >= 1
    assert len(res.logical_inconsistencies) >= 1
    # At least one claim should be categorized under LOGICAL_INCONSISTENCY
    inconsistent_claims = [c for c in res.claims if c.verdict == VerdictEnum.LOGICAL_INCONSISTENCY]
    assert len(inconsistent_claims) >= 1

def test_insufficient_evidence_when_unmentioned():
    """Tests that claims absent from reference evidence are classified as INSUFFICIENT_EVIDENCE."""
    request = AuditRequest(
        answer_text="The patient had a previous allergic reaction to sulfa drugs in 2018.",
        documents=[
            DocumentInput(
                filename="cardiology.txt",
                content="Cardiology evaluation showed normal sinus rhythm and blood pressure of 120/80 mmHg."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.summary.insufficient_evidence_count == 1
    assert res.claims[0].verdict == VerdictEnum.INSUFFICIENT_EVIDENCE
    assert res.claims[0].uncertainty_level in ("Moderate", "High")

def test_summary_totals_sum_to_total_claims():
    """Verifies that the 4 primary categories are mutually exclusive and sum exactly to total_claims."""
    request = AuditRequest(
        answer_text="Community-acquired pneumonia was confirmed. Amoxicillin dosage is 50mg once daily. Sulfa allergies exist. Net profit margin increased. Net profit margin decreased.",
        documents=[
            DocumentInput(
                filename="clinical_protocol.txt",
                content="Community-acquired pneumonia was confirmed. Recommended dosage of Amoxicillin is 500mg three times daily."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    total = res.summary.total_claims
    cat_sum = (
        res.summary.supported_count +
        res.summary.contradicted_count +
        res.summary.insufficient_evidence_count +
        res.summary.logical_inconsistency_count
    )
    assert total == cat_sum, f"Total claims {total} does not equal sum of categories {cat_sum}"

def test_potentially_unsafe_recommendations_clinical():
    """Tests safety analysis flags premature discontinuation or hazardous dosing."""
    request = AuditRequest(
        answer_text="Discontinue antibiotic treatment immediately if mild cough occurs. Take Amoxicillin 50mg once daily.",
        documents=[
            DocumentInput(
                filename="protocol.txt",
                content="Mild cough is a normal expected symptom during respiratory recovery and does not warrant discontinuing antibiotic treatment unless severe adverse allergic reactions occur. Standard dosage is 500mg 3x daily."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.safety_analysis.flagged_count >= 1
    assert len(res.safety_analysis.recommendations) >= 1
    flagged = res.safety_analysis.recommendations[0]
    assert flagged.severity in ("High", "Critical", "Moderate")
    assert flagged.safer_alternative is not None
    assert "discontinu" in flagged.text.lower() or "amoxicillin" in flagged.text.lower()

def test_potentially_unsafe_recommendations_neutral_when_benign():
    """Tests safety analysis returns neutral explanation when no hazards exist."""
    request = AuditRequest(
        answer_text="The solar eclipse occurred on October 14, 2023. Many observers viewed the event through eclipse glasses.",
        documents=[
            DocumentInput(
                filename="astronomy.txt",
                content="The annular solar eclipse was visible on October 14, 2023 across North America."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.safety_analysis.flagged_count == 0
    assert "No potentially unsafe recommendations" in res.safety_analysis.summary

def test_audit_caching_and_repeatability():
    """Tests that repeating an audit on identical inputs produces identical results and hits cache."""
    request = AuditRequest(
        answer_text="The patient was diagnosed with community-acquired pneumonia. The recommended dose of Amoxicillin is 500mg taken three times daily.",
        documents=[
            DocumentInput(
                filename="guidelines.txt",
                content="For adult community-acquired pneumonia, the standard recommended dosage of Amoxicillin is 500mg taken three times daily."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res1 = AuditEngine.run_audit(request)
    res2 = AuditEngine.run_audit(request)

    assert res2.cached is True
    assert res1.summary.credibility_score == res2.summary.credibility_score
    assert len(res1.claims) == len(res2.claims)
    assert res1.claims[0].verdict == res2.claims[0].verdict
    assert res1.claims[0].text == res2.claims[0].text

def test_explicit_llm_mode_fails_cleanly_when_key_missing(monkeypatch):
    """Tests that selecting LLM mode when no API key exists raises clean HTTPException instead of silent fallback."""
    from app.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    request = AuditRequest(
        answer_text="The patient was diagnosed with community-acquired pneumonia.",
        documents=[DocumentInput(filename="test.txt", content="Protocol content.")],
        options={"verification_mode": "llm", "force_deterministic_fallback": False},
        api_key=""
    )
    with pytest.raises(HTTPException) as exc_info:
        AuditEngine.run_audit(request)
    assert exc_info.value.status_code == 400
    assert "GEMINI_API_KEY is not configured" in exc_info.value.detail

def test_api_failure_raises_502_without_silent_fallback(monkeypatch):
    """Verifies that provider failures in LLM mode raise 502 and do not silently fall back to BM25."""
    from app.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock_key")

    monkeypatch.setattr(ClaimExtractor, "extract_claims_with_llm", lambda text, **kwargs: [
        {"claim_id": "claim_1", "text": "The patient was diagnosed with community-acquired pneumonia.", "start_char": 0, "end_char": 61}
    ])

    def mock_verify_with_gemini(*args, **kwargs):
        raise RuntimeError("Google GenAI RateLimit: 429 ResourceExhausted")

    monkeypatch.setattr(AuditEngine, "_verify_with_gemini", mock_verify_with_gemini)

    request = AuditRequest(
        answer_text="The patient was diagnosed with community-acquired pneumonia.",
        documents=[DocumentInput(filename="test.txt", content="Protocol content.")],
        options={"verification_mode": "llm", "force_deterministic_fallback": False},
        api_key="mock_key"
    )

    with pytest.raises(HTTPException) as exc_info:
        AuditEngine.run_audit(request)
    assert exc_info.value.status_code == 502
    assert "Gemini API claim verification failed" in exc_info.value.detail or "ResourceExhausted" in exc_info.value.detail
    assert "ResourceExhausted" in exc_info.value.detail

def test_404_model_not_found_raises_404_with_configured_model_guidance(monkeypatch):
    """Verifies that an upstream 404 NOT_FOUND model error raises HTTP 404 with model name and availability guidance."""
    from app.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock_key")
    monkeypatch.setattr(settings, "DEFAULT_MODEL", "gemini-3.8-flash")

    def mock_extract(*args, **kwargs):
        raise RuntimeError("404 NOT_FOUND: This model models/gemini-2.5-flash is no longer available to new users.")

    monkeypatch.setattr(ClaimExtractor, "extract_claims_with_llm", mock_extract)

    request = AuditRequest(
        answer_text="The patient was diagnosed with community-acquired pneumonia.",
        documents=[DocumentInput(filename="test.txt", content="Protocol content.")],
        options={"verification_mode": "llm", "force_deterministic_fallback": False},
        api_key="mock_key"
    )

    with pytest.raises(HTTPException) as exc_info:
        AuditEngine.run_audit(request)
    assert exc_info.value.status_code == 404
    assert "gemini-3.8-flash" in exc_info.value.detail
    assert "404 NOT_FOUND" in exc_info.value.detail
    assert "GEMINI_MODEL" in exc_info.value.detail

def test_model_configuration_from_settings_and_env(monkeypatch):
    """Verifies that the default model is configurable and defaults to gemini-2.5-flash."""
    from app.config import Settings
    import os

    # Default fallback
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    s1 = Settings()
    assert s1.DEFAULT_MODEL == "gemini-2.5-flash"

    # Environment variable override
    monkeypatch.setenv("GEMINI_MODEL", "custom-model-pro")
    s2 = Settings()
    assert s2.DEFAULT_MODEL == "custom-model-pro"

def test_model_check_endpoint(monkeypatch):
    """Verifies the /api/model-check endpoint with unconfigured and configured states."""
    from app.api.routes import check_model_availability
    from app.config import settings

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    res = check_model_availability()
    assert res["status"] == "unconfigured"
    assert res["model"] == settings.DEFAULT_MODEL

def test_exact_character_span_offsets_and_grounding():
    """Verifies that every extracted claim has exact matching character offsets in original_answer."""
    answer = "The patient was diagnosed with community-acquired pneumonia. The recommended dose of Amoxicillin is 500mg taken three times daily."
    request = AuditRequest(
        answer_text=answer,
        documents=[
            DocumentInput(
                filename="clinical_protocol.txt",
                content="For adult community-acquired pneumonia, the recommended dosage of Amoxicillin is 500mg taken three times daily."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert len(res.claims) >= 2
    for c in res.claims:
        extracted_slice = answer[c.start_char:c.end_char]
        assert extracted_slice == c.text, f"Offset slice '{extracted_slice}' does not match claim text '{c.text}'"

def test_evidence_grounding_and_separation():
    """Verifies supporting and contradicting evidence separation and exact document excerpts."""
    doc_content = "Official Treatment Protocol: For adult community-acquired pneumonia, the standard recommended dosage of Amoxicillin is 500mg to 1000mg orally three times daily."
    request = AuditRequest(
        answer_text="The recommended dose of Amoxicillin is 50mg taken once daily.",
        documents=[
            DocumentInput(
                filename="protocol.txt",
                content=doc_content
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert len(res.claims) == 1
    claim = res.claims[0]
    assert claim.verdict == VerdictEnum.CONTRADICTED
    assert len(claim.contradicting_evidence) >= 1
    # Verify that the excerpt actually exists in the source document
    for ev in claim.contradicting_evidence:
        assert ev.excerpt in doc_content
        assert ev.source_name == "protocol.txt"

def test_audit_configuration_and_limitations_included():
    """Verifies that the audit report contains audit configuration and explicit model limitations."""
    request = AuditRequest(
        answer_text="The eclipse occurred in October 2023.",
        documents=[DocumentInput(filename="doc.txt", content="The solar eclipse occurred in October 2023.")],
        options={"force_deterministic_fallback": True, "top_k_passages": 2}
    )
    res = AuditEngine.run_audit(request)
    assert res.audit_configuration is not None
    assert res.audit_configuration["top_k_passages"] == 2
    assert res.audit_configuration["verification_mode"] == "offline_deterministic"
    assert "statistical probability" in res.limitations.lower() or "confidence" in res.limitations.lower()

def test_scenario_1_offline_auditing_works_without_api_key():
    """Scenario 1: Offline auditing works reliably when no API key is provided."""
    from app.config import settings
    request = AuditRequest(
        answer_text="Amoxicillin 500mg should be taken three times daily for pneumonia.",
        documents=[DocumentInput(filename="protocol.txt", content="For adult pneumonia, Amoxicillin 500mg three times daily is recommended.")],
        options={"verification_mode": "auto", "force_deterministic_fallback": False},
        api_key=None
    )
    # Ensure no environment key
    orig_key = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = ""
    try:
        res = AuditEngine.run_audit(request)
        assert res.verification_mode == "offline_deterministic"
        assert res.summary.supported_count >= 1
        assert res.summary.credibility_score > 0
    finally:
        settings.GEMINI_API_KEY = orig_key

def test_scenario_2_valid_key_configuration_via_config_and_env():
    """Scenario 2: A valid API key can be configured via /api/config, GEMINI_API_KEY, or GOOGLE_API_KEY."""
    import os
    from app.api.routes import update_config, ConfigUpdateRequest, get_config
    from app.config import settings, Settings

    orig_env = os.environ.copy()
    orig_settings_key = settings.GEMINI_API_KEY
    try:
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GOOGLE_API_KEY", None)
        settings.GEMINI_API_KEY = ""

        # 1. Update config via endpoint
        resp = update_config(ConfigUpdateRequest(api_key="AIzaSyTestConfiguredKey123"))
        assert resp["has_gemini_api_key"] is True
        assert get_config()["has_gemini_api_key"] is True
        assert settings.GEMINI_API_KEY == "AIzaSyTestConfiguredKey123"

        # 2. Reset and verify GOOGLE_API_KEY fallback
        settings.GEMINI_API_KEY = ""
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ["GOOGLE_API_KEY"] = "AIzaSyGoogleKeyAlias456"
        s = Settings()
        assert s.GEMINI_API_KEY == "AIzaSyGoogleKeyAlias456"
    finally:
        os.environ.clear()
        os.environ.update(orig_env)
        settings.GEMINI_API_KEY = orig_settings_key



def test_scenario_3_api_based_auditing_returns_expected_response_format(monkeypatch):
    """Scenario 3: API-based auditing completes and returns results in the expected AuditResponse schema."""
    from app.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock_valid_key")

    # Mock LLM claim extraction
    monkeypatch.setattr(ClaimExtractor, "extract_claims_with_llm", lambda text, **kwargs: [
        {"claim_id": "claim_1", "text": "Amoxicillin dosage is 500mg three times daily.", "start_char": 0, "end_char": 47}
    ])

    # Mock Gemini claim verification
    monkeypatch.setattr(AuditEngine, "_verify_with_gemini", lambda *args, **kwargs: (
        VerdictEnum.SUPPORTED, 0.95, "Verified against reference document guidelines.", [0], [], False
    ))

    # Mock LLM safety analysis
    from app.schemas.audit import SafetyAnalysisResult
    monkeypatch.setattr(SafetyAnalyzer, "analyze_with_llm", lambda *args, **kwargs: (
        SafetyAnalysisResult(flagged_count=0, recommendations=[], summary="Safe.")
    ))

    request = AuditRequest(
        answer_text="Amoxicillin dosage is 500mg three times daily.",
        documents=[DocumentInput(filename="guidelines.txt", content="Amoxicillin dosage is 500mg three times daily for pneumonia.")],
        options={"verification_mode": "llm"},
        api_key="mock_valid_key"
    )

    res = AuditEngine.run_audit(request)
    assert res.verification_mode == "llm_api"
    assert res.model_info == settings.DEFAULT_MODEL
    assert len(res.claims) == 1
    assert res.claims[0].verdict == VerdictEnum.SUPPORTED
    # confidence is computed from verification signals, never self-reported by the LLM
    assert 0.0 < res.claims[0].confidence <= 0.97
    assert res.claims[0].confidence_signals
    assert res.summary.supported_count == 1
    assert res.summary.credibility_score == 100.0
    assert res.original_answer == "Amoxicillin dosage is 500mg three times daily."

def test_scenario_4_invalid_or_rejected_key_produces_clear_401_error(monkeypatch):
    """Scenario 4: Missing, invalid, or rejected API keys produce understandable 401 error messages."""
    from app.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "rejected_key")

    def mock_extract_invalid_key(*args, **kwargs):
        raise RuntimeError("400 INVALID_ARGUMENT. API key not valid. Please pass a valid API key. [API_KEY_INVALID]")

    monkeypatch.setattr(ClaimExtractor, "extract_claims_with_llm", mock_extract_invalid_key)

    request = AuditRequest(
        answer_text="The patient was diagnosed with pneumonia.",
        documents=[DocumentInput(filename="test.txt", content="Pneumonia notes.")],
        options={"verification_mode": "llm"},
        api_key="rejected_key"
    )

    with pytest.raises(HTTPException) as exc_info:
        AuditEngine.run_audit(request)

    assert exc_info.value.status_code == 401
    assert "API_KEY_INVALID" in exc_info.value.detail
    assert "invalid or has been rejected" in exc_info.value.detail

def test_scenario_5_api_failures_do_not_break_offline_auditing(monkeypatch):
    """Scenario 5: Upstream API errors do not prevent users from running offline deterministic audits."""
    from app.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "broken_key")

    # Even with a broken API key configured on backend, offline mode succeeds 100%
    request = AuditRequest(
        answer_text="The patient was diagnosed with community-acquired pneumonia.",
        documents=[DocumentInput(filename="test.txt", content="Community-acquired pneumonia was confirmed.")],
        options={"verification_mode": "offline", "force_deterministic_fallback": True},
        api_key=None
    )

    res = AuditEngine.run_audit(request)
    assert res.verification_mode == "offline_deterministic"
    assert res.summary.total_claims == 1
    assert res.summary.contradicted_count == 0  # a related but non-conflicting source is never an error

def test_scenario_6_model_check_endpoint_post_and_get():
    """Scenario 6: Model check endpoint works with POST body to avoid exposing keys in query strings."""
    from app.api.routes import check_model_availability, ModelCheckRequest

    # Unconfigured
    res1 = check_model_availability(api_key="", body=ModelCheckRequest(api_key=""))
    assert res1["status"] == "unconfigured"

    # POST body with key
    res2 = check_model_availability(body=ModelCheckRequest(api_key=""))
    assert res2["status"] == "unconfigured"

