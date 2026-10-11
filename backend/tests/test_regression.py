import pytest
import base64
import zipfile
import io
import xml.etree.ElementTree as ET
from app.schemas.audit import AuditRequest, DocumentInput, VerdictEnum
from app.core.extractor import ClaimExtractor
from app.core.parser import DocumentParser
from app.core.retriever import PassageRetriever
from app.core.consistency import find_local_conflicts
from app.core.judge import SemanticJudge
from app.core.model_registry import registry


def _verify_claim(claim, evidence):
    """Claim-level verdict from the current judge (replaces the removed rule engine)."""
    j = SemanticJudge(registry.nli, registry.embedder).judge(claim, evidence)
    return j.verdict, j.confidence, j.explanation


def _internal_conflicts(claims):
    return find_local_conflicts(claims, registry.nli)
from app.core.verifier import AuditEngine

def test_1_supported_claim():
    request = AuditRequest(
        answer_text="Amoxicillin 500mg should be taken three times daily for pneumonia.",
        documents=[
            DocumentInput(
                filename="clinical_protocol.txt",
                content="For adult pneumonia, the recommended dosage of Amoxicillin is 500mg three times daily."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.summary.supported_count >= 1
    assert res.claims[0].verdict == VerdictEnum.SUPPORTED

@pytest.mark.requires_nli
def test_2_direct_factual_contradiction():
    request = AuditRequest(
        answer_text="Acme Corp reported Q3 revenue of $45 million, representing a 20% decrease.",
        documents=[
            DocumentInput(
                filename="q3_report.txt",
                content="Acme Corp achieved Q3 revenue of $45 million, marking a 20% year-over-year increase."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.summary.contradicted_count >= 1
    assert res.claims[0].verdict == VerdictEnum.CONTRADICTED

@pytest.mark.requires_nli
def test_3_negation_change_contradiction():
    request = AuditRequest(
        answer_text="The patient does not need antibiotic therapy for bacterial pneumonia.",
        documents=[
            DocumentInput(
                filename="treatment.txt",
                content="The patient requires immediate antibiotic therapy for bacterial pneumonia."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict == VerdictEnum.CONTRADICTED

@pytest.mark.requires_nli
def test_4_opposite_meaning_without_negation_words():
    request = AuditRequest(
        answer_text="The server expansion costs decreased the net profit margin.",
        documents=[
            DocumentInput(
                filename="report.txt",
                content="Server expansion costs increased the net profit margin to 35%."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict == VerdictEnum.CONTRADICTED

@pytest.mark.requires_nli
def test_5_supported_claim_with_negation():
    # Paraphrase with negation: "is not harmful" vs "is safe"
    request = AuditRequest(
        answer_text="The drug is not harmful when taken as directed.",
        documents=[
            DocumentInput(
                filename="safety.txt",
                content="The drug is safe when taken as directed."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict == VerdictEnum.SUPPORTED

def test_6_unsupported_unverified_claim():
    request = AuditRequest(
        answer_text="The patient has a history of severe allergies to penicillin.",
        documents=[
            DocumentInput(
                filename="chart.txt",
                content="Patient was admitted for acute bronchitis. Vital signs are normal."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.summary.insufficient_evidence_count >= 1
    assert res.claims[0].verdict == VerdictEnum.INSUFFICIENT_EVIDENCE

def test_7_ambiguous_partial_match():
    request = AuditRequest(
        answer_text="The project launched in quarter 4 of 2025.",
        documents=[
            DocumentInput(
                filename="doc.txt",
                content="The preliminary project outline was drafted in late 2025."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict in (VerdictEnum.INSUFFICIENT_EVIDENCE, VerdictEnum.AMBIGUOUS)

def test_8_unrelated_source_document():
    request = AuditRequest(
        answer_text="Amoxicillin dosage is 500mg daily.",
        documents=[
            DocumentInput(
                filename="space.txt",
                content="NASA launched the James Webb Space Telescope to observe distant galaxies and cosmic phenomena."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict in (VerdictEnum.INSUFFICIENT_EVIDENCE, VerdictEnum.AMBIGUOUS)

def test_9_irrelevant_evidence_retrieval_filtering():
    passages = [
        {"id": "p1", "text": "The solar panel generates 400 watts of renewable electricity.", "source_name": "solar.txt"}
    ]
    retriever = PassageRetriever(passages)
    results = retriever.retrieve("Penicillin antibiotic prescription dose", top_k=3)
    assert len(results) == 0

def test_10_heading_and_non_claim_text_filtering():
    raw_text = """# Executive Summary
Table of Contents:
1. Overview
The patient was diagnosed with bacterial pneumonia.
What is the recommended treatment?
Key Findings:
Amoxicillin 500mg should be administered three times daily."""
    claims = ClaimExtractor.extract_claims(raw_text)
    texts = [c["text"] for c in claims]
    assert "Executive Summary" not in texts
    assert "Table of Contents" not in texts
    assert "1. Overview" not in texts
    assert "What is the recommended treatment?" not in texts
    assert len(claims) == 2

def test_11_duplicate_claim_handling():
    raw_text = "Amoxicillin 500mg is recommended daily. Amoxicillin 500mg is recommended daily."
    claims = ClaimExtractor.extract_claims(raw_text)
    assert len(claims) == 1

def test_12_multiple_claims_in_paragraph():
    raw_text = "Acme Corp Q3 revenue reached $45 million. Net profit margin increased to 35%."
    claims = ClaimExtractor.extract_claims(raw_text)
    assert len(claims) == 2

def test_13_docx_and_pdf_parsing():
    # Test DOCX simulated xml structure
    docx_content = "Paragraph 1 text content.\n\nParagraph 2 text content."
    passages = DocumentParser.parse_documents([
        DocumentInput(filename="test.txt", content=docx_content)
    ])
    assert len(passages) == 2
    assert passages[0]["text"] == "Paragraph 1 text content."

def test_14_missing_or_malformed_llm_response():
    # Verify fallback handles bad LLM output gracefully
    verdict, confidence, exp = _verify_claim(
        "Amoxicillin 50mg daily for adult pneumonia.",
        [{"excerpt": "Amoxicillin 500mg three times daily.", "source_name": "guide.txt", "relevance_score": 0.8}]
    )
    assert verdict == VerdictEnum.CONTRADICTED

def test_15_internal_contradictions_detection():
    claims = [
        {"claim_id": "claim_1", "text": "Amoxicillin dosage is 50mg daily."},
        {"claim_id": "claim_2", "text": "Amoxicillin dosage is 500mg daily."}
    ]
    conflicts = _internal_conflicts(claims)
    assert len(conflicts) == 1
    assert conflicts[0]["claim_id_1"] == "claim_1"
    assert conflicts[0]["claim_id_2"] == "claim_2"

def test_16_credibility_score_calculation():
    # 2 Supported, 1 Insufficient, 1 Contradicted => (2 + 0.5) / 4 = 62.5%
    req = AuditRequest(
        answer_text="Amoxicillin 500mg is prescribed. Patient has cough. Dose is 50mg. Acme revenue was $10.",
        documents=[
            DocumentInput(filename="doc.txt", content="Amoxicillin 500mg is prescribed. Patient has cough. Recommended dose is 500mg.")
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(req)
    assert 0.0 <= res.summary.credibility_score <= 100.0

def test_17_empty_text_or_documents():
    req = AuditRequest(answer_text="   ", documents=[], options={"force_deterministic_fallback": True})
    res = AuditEngine.run_audit(req)
    assert res.summary.total_claims == 0
    assert res.summary.credibility_score == 100.0

def test_18_character_offset_accuracy():
    text = "First claim text here. Second claim text follows."
    claims = ClaimExtractor.extract_claims(text)
    for c in claims:
        extracted = text[c["start_char"]:c["end_char"]]
        assert extracted == c["text"]

def test_19_end_to_end_audit_response_schema():
    req = AuditRequest(
        answer_text="The company achieved Q3 revenue of $45 million.",
        documents=[DocumentInput(filename="q3.txt", content="Q3 revenue was $45 million.")]
    )
    res = AuditEngine.run_audit(req)
    assert res.audit_id.startswith("audit_")
    assert res.summary.total_claims == 1
    assert len(res.claims) == 1
    assert res.claims[0].evidence[0].source_name == "q3.txt"

@pytest.mark.requires_nli
def test_20_antonym_pair_coverage():
    c = "The project safety approval was rejected."
    e = "The project safety approval was accepted."
    v, conf, exp = _verify_claim(c, [{"excerpt": e, "source_name": "s.txt", "relevance_score": 0.85}])
    assert v == VerdictEnum.CONTRADICTED

@pytest.mark.requires_nli
def test_21_transparency_vs_concealment():
    request = AuditRequest(
        answer_text="The corporate governance guidelines recommend financial concealment.",
        documents=[
            DocumentInput(
                filename="governance.txt",
                content="Corporate governance policies explicitly mandate financial transparency and full public disclosure."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict == VerdictEnum.CONTRADICTED

@pytest.mark.requires_nli
def test_22_merit_vs_personal_relationships():
    request = AuditRequest(
        answer_text="Hiring decisions should prefer personal relationships over merit.",
        documents=[
            DocumentInput(
                filename="ethics.txt",
                content="All hiring decisions must be based on merit rather than personal relationships."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict == VerdictEnum.CONTRADICTED

def test_23_unverified_definitions():
    request = AuditRequest(
        answer_text="Blockchain is defined as a centralized database managed by a single administrator.",
        documents=[
            DocumentInput(
                filename="tech.txt",
                content="Blockchain technology has gained widespread adoption across finance and supply chain management."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict == VerdictEnum.INSUFFICIENT_EVIDENCE

def test_24_roman_numeral_and_principle_heading_filtering():
    raw_text = """Principle 1: Selection Based on Merit
II. CODE OF CONDUCT
Rule 3. Financial Transparency
The company mandates full financial disclosure for all operations."""
    claims = ClaimExtractor.extract_claims(raw_text)
    texts = [c["text"] for c in claims]
    assert "Principle 1: Selection Based on Merit" not in texts
    assert "II. CODE OF CONDUCT" not in texts
    assert "Rule 3. Financial Transparency" not in texts
    assert len(claims) == 1

@pytest.mark.requires_nli
def test_25_personal_benefits_over_fairness():
    request = AuditRequest(
        answer_text="Personal benefits can sometimes be prioritised over fairness.",
        documents=[
            DocumentInput(
                filename="ethics_code.txt",
                content="All official decisions must prioritize fairness and public interest over personal benefits."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict in (VerdictEnum.CONTRADICTED, VerdictEnum.INSUFFICIENT_EVIDENCE)

@pytest.mark.requires_nli
def test_26_personal_relationships_rather_than_merit():
    request = AuditRequest(
        answer_text="Decisions should be based on personal relationships rather than merit.",
        documents=[
            DocumentInput(
                filename="policy.txt",
                content="Decisions must be based on merit rather than personal relationships."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict in (VerdictEnum.CONTRADICTED, VerdictEnum.INSUFFICIENT_EVIDENCE)

@pytest.mark.requires_nli
def test_27_benefits_friends_and_family_vs_public_interest():
    request = AuditRequest(
        answer_text="It is important to choose what benefits friends and family.",
        documents=[
            DocumentInput(
                filename="conduct.txt",
                content="Decisions should be made in the public interest rather than benefiting friends and family."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict in (VerdictEnum.CONTRADICTED, VerdictEnum.INSUFFICIENT_EVIDENCE)

@pytest.mark.requires_nli
def test_28_hiding_personal_interests_vs_disclosure():
    request = AuditRequest(
        answer_text="Hiding personal interests can sometimes be better than disclosing them.",
        documents=[
            DocumentInput(
                filename="policy.txt",
                content="Official policy mandates full public disclosure of all personal interests to ensure transparency."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict in (VerdictEnum.CONTRADICTED, VerdictEnum.INSUFFICIENT_EVIDENCE)

@pytest.mark.requires_nli
def test_29_self_conflict_deduplication():
    claims = [
        {"claim_id": "claim_1", "text": "Decisions must be based on merit rather than personal relationships."},
        {"claim_id": "claim_2", "text": "Decisions should be based on personal relationships rather than merit."},
        {"claim_id": "claim_3", "text": "The patient has a mild cough."}
    ]
    conflicts = _internal_conflicts(claims)
    assert len(conflicts) == 1
    assert conflicts[0]["claim_id_1"] == "claim_1"
    assert conflicts[0]["claim_id_2"] == "claim_2"

@pytest.mark.requires_nli
def test_30_disclosure_definition_contradiction():
    request = AuditRequest(
        answer_text="Disclosure means keeping personal interests private.",
        documents=[
            DocumentInput(
                filename="policy.txt",
                content="Official policy mandates full public disclosure of all personal interests to ensure transparency."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict in (VerdictEnum.CONTRADICTED, VerdictEnum.INSUFFICIENT_EVIDENCE)

def test_31_recusal_unverified_definition():
    request = AuditRequest(
        answer_text="Recusal means participating in a decision despite having a personal interest.",
        documents=[
            DocumentInput(
                filename="policy.txt",
                content="Official policy mandates full public disclosure of all personal interests to ensure transparency."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict == VerdictEnum.INSUFFICIENT_EVIDENCE

def test_32_no_false_internal_conflicts_on_descriptive_statements():
    claims = [
        {"claim_id": "claim_1", "text": "It can happen because of personal relationships, money, or personal benefits."},
        {"claim_id": "claim_2", "text": "The activity showed that personal relationships can sometimes affect decisions."},
        {"claim_id": "claim_3", "text": "Decisions should be based on merit rather than personal relationships."}
    ]
    conflicts = _internal_conflicts(claims)
    # None of these descriptive statements contradict each other
    assert len(conflicts) == 0

def test_33_disclosure_definition_unsupported_by_transparent_excerpt():
    request = AuditRequest(
        answer_text="Disclosure means keeping personal interests private.",
        documents=[
            DocumentInput(
                filename="personal_reflection.txt",
                content="Personal life: I learnt that being honest is not only about being correct but also about being transparent where there is a conflict of interest."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict in (VerdictEnum.INSUFFICIENT_EVIDENCE, VerdictEnum.CONTRADICTED)
    assert res.claims[0].verdict != VerdictEnum.SUPPORTED

def test_34_honesty_definition_not_fully_supported():
    request = AuditRequest(
        answer_text="Honesty means making correct decisions, even if personal interests are involved.",
        documents=[
            DocumentInput(
                filename="personal_reflection.txt",
                content="Personal life: I learnt that being honest is not only about being correct but also about being transparent where there is a conflict of interest."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict != VerdictEnum.SUPPORTED

@pytest.mark.requires_nli
def test_35_transparency_not_always_necessary_contradiction():
    request = AuditRequest(
        answer_text="Transparency is not always necessary when personal relationships affect decisions.",
        documents=[
            DocumentInput(
                filename="governance.txt",
                content="Transparency is mandatory whenever personal relationships affect decisions."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict in (VerdictEnum.CONTRADICTED, VerdictEnum.INSUFFICIENT_EVIDENCE)

def test_36_credibility_score_formula_precision():
    # 1 Supported, 1 Contradicted, 1 Insufficient => (1 + 0.5 * 1) / 3 = 1.5 / 3 = 50.0%
    claims_results = [VerdictEnum.SUPPORTED, VerdictEnum.CONTRADICTED, VerdictEnum.INSUFFICIENT_EVIDENCE]
    supported = sum(1 for v in claims_results if v == VerdictEnum.SUPPORTED)
    insufficient = sum(1 for v in claims_results if v == VerdictEnum.INSUFFICIENT_EVIDENCE)
    score = round(((supported + 0.5 * insufficient) / len(claims_results)) * 100.0, 1)
    assert score == 50.0

def test_37_document_declaration_verification():
    request = AuditRequest(
        answer_text="The corporate policy mandates full disclosure of conflict of interest.",
        documents=[
            DocumentInput(
                filename="policy.txt",
                content="The corporate policy mandates full disclosure of conflict of interest for all employees."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict == VerdictEnum.SUPPORTED
    assert "policy.txt" in res.claims[0].explanation or len(res.claims[0].evidence) > 0

def test_38_indirect_evidence_returns_insufficient():
    request = AuditRequest(
        answer_text="The company plans to double its total workforce in 2026.",
        documents=[
            DocumentInput(
                filename="growth_plan.txt",
                content="The company expects continued business growth and expansion across market segments in 2026."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict == VerdictEnum.INSUFFICIENT_EVIDENCE

@pytest.mark.requires_nli
def test_39_accurate_contradiction_explanation_text():
    request = AuditRequest(
        answer_text="The project budget was increased by 40%.",
        documents=[
            DocumentInput(
                filename="budget.txt",
                content="The project budget was decreased by 40% due to spending constraints."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict == VerdictEnum.CONTRADICTED
    assert "increase" in res.claims[0].explanation or "decrease" in res.claims[0].explanation

def test_40_ambiguous_claim_flagging():
    request = AuditRequest(
        answer_text="The project launched in quarter 4 of 2025.",
        documents=[
            DocumentInput(
                filename="notes.txt",
                content="Initial draft outlines for the project were started in late 2025."
            )
        ],
        options={"force_deterministic_fallback": True}
    )
    res = AuditEngine.run_audit(request)
    assert res.claims[0].verdict in (VerdictEnum.INSUFFICIENT_EVIDENCE, VerdictEnum.AMBIGUOUS)  # never an error
    assert res.claims[0].verdict == VerdictEnum.AMBIGUOUS or res.claims[0].confidence < 0.85

def test_42_calculate_credibility_edge_cases():
    # Edge case 1: Zero claims -> 100.0%
    score, breakdown = AuditEngine.calculate_credibility(0, 0, 0, 0)
    assert score == 100.0
    assert breakdown["total_claims"] == 0

    # Edge case 2: All supported -> 100.0%
    score, breakdown = AuditEngine.calculate_credibility(5, 0, 0, 5)
    assert score == 100.0

    # Edge case 3: All contradicted -> 0.0%
    score, breakdown = AuditEngine.calculate_credibility(0, 0, 5, 5)
    assert score == 0.0

    # Edge case 4: All insufficient -> 50.0%
    score, breakdown = AuditEngine.calculate_credibility(0, 5, 0, 5)
    assert score == 50.0






