"""Logic tests for the semantic pipeline.

A scripted FakeNLI stands in for the real model so the *decision logic* (thresholds, conflict handling,
LLM cross-checking) is tested everywhere. These tests do NOT measure model accuracy: that is what
`python -m tests.eval.run` does with the real model.
"""
import json
from types import SimpleNamespace

import pytest

from app.core.confidence import Signals, compute_confidence
from app.core.entity_check import compare_entities
from app.core.judge import SemanticJudge
from app.core.llm_verifier import LLMVerdict, merge_with_local, parse_llm_response, quote_exists
from app.core.nli import CrossEncoderNLI, NLIScores
from app.core.text_utils import split_sentences
from app.schemas.audit import AuditRequest, DocumentInput, ErrorCategory, VerdictEnum
from app.core.verifier import AuditEngine


class FakeNLI:
    """Returns scripted scores: first rule whose keyword is in the premise wins; default = neutral."""
    name = "fake-nli"

    def __init__(self, rules):
        self.rules = rules

    def predict_batch(self, pairs):
        out = []
        for premise, _claim in pairs:
            scores = next((s for key, s in self.rules.items() if key in premise), (0.05, 0.05, 0.90))
            out.append(NLIScores(entailment=scores[0], contradiction=scores[1], neutral=scores[2]))
        return out


def ev(*texts):
    return [{"excerpt": t, "source_name": f"s{i}", "relevance_score": 0.6} for i, t in enumerate(texts)]


# ---------------------------------------------------------------- NLI decision logic
def test_entailment_supports():
    j = SemanticJudge(FakeNLI({"important": (0.95, 0.02, 0.03)}))
    r = j.judge("Sleep is essential for the body.", ev("Sleep is important for the body."))
    assert r.verdict == VerdictEnum.SUPPORTED and r.confidence > 0.7


def test_nli_contradiction_without_entities_is_flagged_with_approximate_span():
    j = SemanticJudge(FakeNLI({"fell": (0.02, 0.95, 0.03)}))
    r = j.judge("Sales grew strongly last quarter.", ev("Sales fell sharply last quarter."))
    assert r.verdict == VerdictEnum.CONTRADICTED and r.category == ErrorCategory.CONTRADICTS_SOURCE
    assert r.span and r.span.precision == "approximate" and "grew" in r.span.text


def test_neutral_is_insufficient_not_an_error():
    j = SemanticJudge(FakeNLI({}))
    r = j.judge("The CEO enjoys sailing at the lake.", ev("The CEO announced the lake office opening."))
    assert r.verdict == VerdictEnum.INSUFFICIENT_EVIDENCE


def test_middling_scores_are_ambiguous():
    j = SemanticJudge(FakeNLI({"outline": (0.45, 0.10, 0.45)}))
    r = j.judge("The project launched in 2025.", ev("The project outline was drafted in 2025."))
    assert r.verdict == VerdictEnum.AMBIGUOUS and r.confidence <= 0.5


def test_numeric_mismatch_beats_nli_that_missed_it_but_confidence_is_capped():
    j = SemanticJudge(FakeNLI({"150": (0.90, 0.03, 0.07)}))
    r = j.judge("The study enrolled 200 participants.", ev("The study enrolled 150 participants."))
    assert r.verdict == VerdictEnum.CONTRADICTED and r.category == ErrorCategory.NUMERIC_MISMATCH
    assert r.span.text == "200" and r.span.precision == "exact" and r.confidence <= 0.55


def test_name_mismatch_that_nli_calls_equivalent_is_ambiguous_alias_risk():
    j = SemanticJudge(FakeNLI({"New York": (0.92, 0.02, 0.06)}))
    r = j.judge("The summit was held in NYC.", ev("The summit was held in New York."))
    assert r.verdict == VerdictEnum.AMBIGUOUS


def test_sources_that_disagree_are_ambiguous():
    j = SemanticJudge(FakeNLI({"approved": (0.95, 0.02, 0.03), "rejected": (0.02, 0.95, 0.03)}))
    r = j.judge("The proposal was approved.", ev("The proposal was approved by the board.", "The proposal was rejected by the audit team."))
    assert r.verdict == VerdictEnum.AMBIGUOUS and r.source_disagreement


# ------------------------------------------------- no-NLI mode never guesses SUPPORTED
@pytest.mark.parametrize("claim,source", [
    ("Paris is the capital of Germany.", "Paris is the capital of France. Berlin is the capital of Germany."),
    ("The project was led by Dr. Smith.", "The project was led by Dr. Jones."),
    ("The treaty was signed in Geneva.", "The treaty was signed in Vienna."),
    ("Sales grew strongly last quarter.", "Sales fell sharply last quarter."),
])
def test_without_nli_wrong_claims_are_never_supported(claim, source):
    assert SemanticJudge().judge(claim, ev(source)).verdict != VerdictEnum.SUPPORTED


def test_without_nli_near_verbatim_is_supported():
    r = SemanticJudge().judge("Marie Curie won the Nobel Prize in Physics.", ev("Marie Curie won the Nobel Prize in Physics in 1903."))
    assert r.verdict == VerdictEnum.SUPPORTED and r.confidence <= 0.80


def test_not_harmful_vs_safe_is_not_a_false_contradiction():
    r = SemanticJudge().judge("The drug is not harmful when taken as directed.", ev("The drug is safe when taken as directed."))
    assert r.verdict != VerdictEnum.CONTRADICTED


# ---------------------------------------------------------------- entity checks
@pytest.mark.parametrize("claim,source,expected", [
    ("Completed in 1899.", "Completed in 1889.", True),
    ("Dose is 750mg three times daily.", "Dose is 500mg to 1000mg three times daily.", False),  # inside range
    ("The dose is 0.05 g.", "The dose is 50 mg.", False),                                     # unit conversion
    ("Revenue was 5 million dollars.", "Revenue was $5,000,000.", False),
    ("Revenue was 5M in 2022.", "Revenue was 7M in 2023.", False),                            # different situation
    ("Dr. Smith led the trial.", "Dr. Jones led the trial.", True),
])
def test_entity_mismatch_rules(claim, source, expected):
    assert compare_entities(claim, source).has_verified_mismatch is expected


def test_sentence_splitter_keeps_abbreviations_together():
    assert [s for s, _, _ in split_sentences("It was led by Dr. Smith. Then J. K. Rowling spoke.")] == [
        "It was led by Dr. Smith.", "Then J. K. Rowling spoke."]


# ----------------------------------------------------------- LLM verification hardening
EVIDENCE = ev("The recommended dosage of Amoxicillin is 500mg three times daily.")


def _llm_json(**kw):
    base = {"verdict": "CONTRADICTED", "explanation": "x", "passage_index": 0,
            "evidence_quote": "dosage of Amoxicillin is 500mg three times daily", "error_text": "50mg"}
    return json.dumps({**base, **kw})


def test_llm_verdict_with_real_quote_is_kept():
    v = parse_llm_response(_llm_json(), "Amoxicillin 50mg daily.", EVIDENCE)
    assert v.verdict == VerdictEnum.CONTRADICTED and v.quote_verified and v.error_text == "50mg"


def test_llm_fabricated_quote_is_downgraded():
    v = parse_llm_response(_llm_json(evidence_quote="The label forbids this drug entirely"), "Amoxicillin 50mg daily.", EVIDENCE)
    assert v.verdict == VerdictEnum.INSUFFICIENT_EVIDENCE and v.quote_verified is False


def test_llm_error_text_must_be_a_real_substring_of_the_claim():
    v = parse_llm_response(_llm_json(error_text="made up words"), "Amoxicillin 50mg daily.", EVIDENCE)
    assert v.error_text is None


def test_quote_matching_ignores_case_and_whitespace_but_not_content():
    assert quote_exists("DOSAGE of  amoxicillin is 500mg", EVIDENCE[0]["excerpt"])
    assert not quote_exists("dosage of amoxicillin is 900mg", EVIDENCE[0]["excerpt"])


def test_llm_and_local_disagreement_becomes_ambiguous():
    local = SemanticJudge().judge("Sales were 5 million dollars.", ev("Sales were 5 million dollars."))  # SUPPORTED
    llm = LLMVerdict(VerdictEnum.CONTRADICTED, "claims otherwise", [], [0], quote_verified=True)
    merged = merge_with_local(local, llm, "Sales were 5 million dollars.", 0.6)
    assert merged.verdict == VerdictEnum.AMBIGUOUS and merged.confidence <= 0.55


def test_verified_value_mismatch_outranks_llm_abstaining():
    claim = "The study enrolled 200 participants."
    local = SemanticJudge().judge(claim, ev("The study enrolled 150 participants."))
    merged = merge_with_local(local, LLMVerdict(VerdictEnum.INSUFFICIENT_EVIDENCE, "unsure"), claim, 0.6)
    assert merged.verdict == VerdictEnum.CONTRADICTED


# --------------------------------------------------- confidence + NLI wrapper plumbing
def test_conflicting_signals_cap_confidence():
    conf, _ = compute_confidence(Signals(nli_probability=0.99, entity_verified=True, retrieval_relevance=1.0, conflicting=True))
    assert conf <= 0.55


def test_cross_encoder_label_order_and_softmax_are_handled():
    model = CrossEncoderNLI.__new__(CrossEncoderNLI)
    model._model = SimpleNamespace(model=SimpleNamespace(config=SimpleNamespace(
        id2label={0: "contradiction", 1: "entailment", 2: "neutral"})))
    model._order = model._label_order()
    scores = model._to_scores([0.1, 4.0, 0.2])   # raw logits
    assert scores.entailment > 0.9 and abs(scores.entailment + scores.contradiction + scores.neutral - 1) < 1e-6


# ------------------------------------------------------------------ engine integration
def test_engine_reports_exact_error_span_and_signals_in_answer_coordinates():
    req = AuditRequest(
        answer_text="The company was founded in Pune. Its CEO announced the study enrolled 200 participants.",
        documents=[DocumentInput(filename="a.txt", content="The study enrolled 150 participants across three sites.")],
        options={"force_deterministic_fallback": True})
    res = AuditEngine.run_audit(req)
    flagged = [c for c in res.claims if c.error_span]
    assert flagged, "expected the 200 vs 150 error to be localised"
    span = flagged[0].error_span
    assert res.original_answer[span.start_char:span.end_char] == span.text == "200"
    assert flagged[0].confidence_signals and res.warnings  # warns that the NLI model is absent
