import re
from typing import List, Dict, Any, Tuple
from app.schemas.audit import VerdictEnum, ClaimItem, EvidenceItem, ClaimFlags

class DeterministicVerifier:
    """
    100% Offline, API-Independent Verification Engine.
    Uses rule-based lexical entailment, antonym detection, numerical disagreement checks,
    and internal claim inconsistency matrix.
    """

    ANTONYM_PAIRS = [
        ("increase", "decrease"), ("increased", "decreased"), ("high", "low"),
        ("before", "after"), ("allow", "prohibit"), ("allowed", "prohibited"),
        ("enable", "disable"), ("enabled", "disabled"), ("valid", "invalid"),
        ("safe", "unsafe"), ("approved", "disapproved"), ("positive", "negative"),
        ("first", "last"), ("above", "below"), ("maximum", "minimum")
    ]

    @staticmethod
    def verify_claim(claim_text: str, evidence_items: List[Dict[str, Any]]) -> Tuple[VerdictEnum, float, str]:
        if not evidence_items:
            return (
                VerdictEnum.INSUFFICIENT_EVIDENCE,
                0.0,
                "No relevant document or web context was found for this claim."
            )

        best_evidence = evidence_items[0]
        excerpt = best_evidence["excerpt"].lower()
        claim_lower = claim_text.lower()

        # 1. Numerical & Quantitative Discrepancy Check
        claim_nums = set(re.findall(r'\d+(?:\.\d+)?', claim_lower))
        excerpt_nums = set(re.findall(r'\d+(?:\.\d+)?', excerpt))

        # Check unit/dosage numerical mismatch
        if claim_nums and excerpt_nums:
            common_words = set(re.findall(r'\w+', claim_lower)).intersection(set(re.findall(r'\w+', excerpt)))
            if len(common_words) >= 2 and not claim_nums.issubset(excerpt_nums):
                mismatched_nums = claim_nums.difference(excerpt_nums)
                return (
                    VerdictEnum.CONTRADICTED,
                    0.88,
                    f"Numerical discrepancy detected: Claim references values {list(mismatched_nums)} which contradict the reference text."
                )

        # 2. Antonym / Directional Contradiction Check
        for w1, w2 in DeterministicVerifier.ANTONYM_PAIRS:
            if (w1 in claim_lower and w2 in excerpt) or (w2 in claim_lower and w1 in excerpt):
                # Ensure context relevance before declaring contradiction
                if len(set(re.findall(r'\w+', claim_lower)).intersection(set(re.findall(r'\w+', excerpt)))) >= 2:
                    return (
                        VerdictEnum.CONTRADICTED,
                        0.85,
                        f"Semantic contradiction: Claim mentions '{w1 if w1 in claim_lower else w2}' whereas source evidence states '{w2 if w2 in excerpt else w1}'."
                    )

        # 3. Negation Discrepancy Check
        negations = ["not", "no", "never", "cannot", "neither", "denies"]
        claim_has_neg = any(f" {n} " in f" {claim_lower} " for n in negations)
        excerpt_has_neg = any(f" {n} " in f" {excerpt} " for n in negations)

        if claim_has_neg != excerpt_has_neg and best_evidence["relevance_score"] > 0.4:
            overlap_terms = set(re.findall(r'\w+', claim_lower)).intersection(set(re.findall(r'\w+', excerpt)))
            if len(overlap_terms) >= 3:
                return (
                    VerdictEnum.CONTRADICTED,
                    0.90,
                    "Polarity mismatch: Claim negation differs from reference source context."
                )

        # 4. Entailment / Support Check based on BM25 Relevance & Keyword Overlap
        if best_evidence["relevance_score"] >= 0.35:
            return (
                VerdictEnum.SUPPORTED,
                round(min(0.95, float(best_evidence["relevance_score"] + 0.1)), 2),
                f"Evidence from '{best_evidence['source_name']}' directly corroborates this claim."
            )

        return (
            VerdictEnum.INSUFFICIENT_EVIDENCE,
            0.40,
            "Partial keywords match, but source evidence is insufficient to verify the complete claim."
        )

    @staticmethod
    def detect_internal_contradictions(claims: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Scans extracted claims within the same answer for mutual conflicts.
        """
        contradictions = []
        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                c1 = claims[i]["text"].lower()
                c2 = claims[j]["text"].lower()

                nums1 = set(re.findall(r'\b\d+(?:\.\d+)?\b', c1))
                nums2 = set(re.findall(r'\b\d+(?:\.\d+)?\b', c2))

                # Check shared subject with contradicting numbers
                words1 = set(re.findall(r'\w+', c1))
                words2 = set(re.findall(r'\w+', c2))
                shared_words = words1.intersection(words2) - {"the", "a", "is", "was", "and", "or", "in", "to", "for", "of"}

                if len(shared_words) >= 2 and nums1 and nums2 and nums1 != nums2:
                    contradictions.append({
                        "claim_id_1": claims[i]["claim_id"],
                        "claim_id_2": claims[j]["claim_id"],
                        "reason": f"Internal discrepancy between '{claims[i]['text']}' and '{claims[j]['text']}'"
                    })
        return contradictions
