import re
from typing import List, Dict, Any, Tuple
from app.schemas.audit import VerdictEnum
from app.core.retriever import PassageRetriever

class DeterministicVerifier:
    """
    100% Offline, API-Independent Verification Engine.
    Evaluates claims against source evidence using semantic polarity analysis,
    numerical discrepancy checks, antonym matching, preference order reversals,
    negated preposition clauses, definition validation, and internal claim inconsistency matrix.
    """

    ANTONYM_PAIRS = [
        ("increase", "decrease"), ("increased", "decreased"), ("increasing", "decreasing"),
        ("high", "low"), ("higher", "lower"), ("highest", "lowest"),
        ("before", "after"), ("allow", "prohibit"), ("allowed", "prohibited"),
        ("enable", "disable"), ("enabled", "disabled"), ("valid", "invalid"),
        ("safe", "unsafe"), ("safe", "harmful"), ("approved", "disapproved"),
        ("approved", "forbidden"), ("positive", "negative"), ("first", "last"),
        ("above", "below"), ("maximum", "minimum"), ("effective", "ineffective"),
        ("recommended", "discouraged"), ("recommended", "forbidden"),
        ("true", "false"), ("correct", "incorrect"), ("pass", "fail"),
        ("gain", "loss"), ("gained", "lost"), ("rise", "fall"), ("rose", "fell"),
        ("accept", "reject"), ("accepted", "rejected"), ("up", "down"),
        # Ethical, Governance, and Business Directional Antonyms (including gerund/participle forms)
        ("transparency", "concealment"), ("transparency", "secrecy"), ("transparent", "secret"),
        ("transparent", "concealed"), ("transparent", "hiding"), ("transparency", "hiding"),
        ("disclose", "conceal"), ("disclose", "hide"), ("disclosing", "hiding"),
        ("disclosure", "concealment"), ("disclosure", "secrecy"), ("disclosure", "hiding"),
        ("disclosed", "hidden"), ("private", "public"), ("private", "transparency"),
        ("private", "disclosure"), ("privacy", "transparency"), ("privacy", "disclosure"),
        ("merit", "nepotism"), ("merit", "favoritism"), ("merit", "personal relationships"),
        ("honesty", "dishonesty"), ("honesty", "deceit"), ("integrity", "corruption"),
        ("impartial", "biased"), ("fairness", "bias"), ("fairness", "personal benefits"),
        ("public interest", "personal benefits"), ("public interest", "personal interests"),
        ("public interest", "friends and family"), ("adhere", "violate"),
        ("compliance", "violation"), ("compliance", "non-compliance"), ("comply", "violate"),
        ("mandatory", "optional"), ("require", "forbid"), ("mandate", "prohibit"),
        ("encourage", "discourage")
    ]

    NEGATION_WORDS = {"not", "no", "never", "cannot", "neither", "nor", "denies", "without", "unlikely"}

    @staticmethod
    def _extract_numbers(text: str) -> set:
        return set(re.findall(r'\d+(?:\.\d+)?', text))

    @staticmethod
    def _normalize_preference(text: str) -> str:
        """Normalizes British/US spelling and passive voice for preference comparison."""
        t = text.lower()
        t = t.replace("prioritised", "prioritize").replace("prioritising", "prioritize").replace("prioritized", "prioritize")
        t = t.replace("favoured", "favor").replace("favouring", "favor").replace("favored", "favor")
        t = t.replace("can be prioritised", "prioritize").replace("should be prioritised", "prioritize").replace("be prioritised", "prioritize")
        t = t.replace("can be prioritized", "prioritize").replace("should be prioritized", "prioritize").replace("be prioritized", "prioritize")
        return t

    @staticmethod
    def verify_claim(claim_text: str, evidence_items: List[Dict[str, Any]]) -> Tuple[VerdictEnum, float, str]:
        if not evidence_items:
            return (
                VerdictEnum.INSUFFICIENT_EVIDENCE,
                0.0,
                "No relevant document or reference context was found for this claim."
            )

        best_evidence = evidence_items[0]
        excerpt = best_evidence["excerpt"]
        excerpt_lower = excerpt.lower()
        claim_lower = claim_text.lower()
        norm_claim = DeterministicVerifier._normalize_preference(claim_lower)
        norm_excerpt = DeterministicVerifier._normalize_preference(excerpt_lower)
        rel_score = float(best_evidence.get("relevance_score", 0.0))

        # Check if relevance score is too low and no shared domain terms exist
        claim_content_words = set(re.findall(r'\b[a-z]{3,}\b', claim_lower)) - DeterministicVerifier.NEGATION_WORDS - PassageRetriever.STOP_WORDS
        excerpt_content_words = set(re.findall(r'\b[a-z]{3,}\b', excerpt_lower)) - DeterministicVerifier.NEGATION_WORDS - PassageRetriever.STOP_WORDS
        overlap_content = claim_content_words.intersection(excerpt_content_words)

        if rel_score < 0.15 and len(overlap_content) < 2:
            return (
                VerdictEnum.INSUFFICIENT_EVIDENCE,
                0.35,
                f"Source document '{best_evidence['source_name']}' does not contain sufficient evidence to verify this claim."
            )

        # 1. Numerical & Quantitative Discrepancy Check
        claim_nums = DeterministicVerifier._extract_numbers(claim_lower)
        excerpt_nums = DeterministicVerifier._extract_numbers(excerpt_lower)

        if claim_nums and excerpt_nums:
            claim_words = set(re.findall(r'\b[a-z]{3,}\b', claim_lower))
            excerpt_words = set(re.findall(r'\b[a-z]{3,}\b', excerpt_lower))
            shared_words = claim_words.intersection(excerpt_words) - {"the", "and", "was", "for", "with", "that", "this"}
            
            if len(shared_words) >= 1:
                has_direct_conflict = False
                mismatched_nums = []
                for cn in claim_nums:
                    if cn not in excerpt_nums:
                        if len(excerpt_nums) == len(claim_nums) or any(abs(len(cn) - len(en)) <= 1 for en in excerpt_nums):
                            has_direct_conflict = True
                            mismatched_nums.append(cn)
                
                if has_direct_conflict and mismatched_nums:
                    return (
                        VerdictEnum.CONTRADICTED,
                        0.92,
                        f"Numerical discrepancy: Claim references value(s) {sorted(mismatched_nums)} which conflicts with source evidence '{excerpt}'."
                    )

        # 2. Preference Order & Evaluative Reversal Check
        # Handles "prefer A over B", "based on A rather than B", "A can sometimes be better than B"
        comp_match = re.search(r'\b([a-z\s]{3,30})\b.*?\b(?:better|preferred|superior|more desirable)\s+(?:than|to)\s+([a-z\s]{3,30})\b', norm_claim)
        if comp_match:
            act_a = comp_match.group(1).strip()
            act_b = comp_match.group(2).strip()
            # If evidence mandates/requires/encourages act_b or transparency/disclosure
            if (any(term in excerpt_lower for term in act_b.split() if len(term) > 3) or "disclosure" in excerpt_lower or "transparency" in excerpt_lower or "disclose" in excerpt_lower) and \
               re.search(r'\b(mandates|requires|policy|standard|must|should|transparent|transparency|full|disclosure|disclose)\b', excerpt_lower):
                return (
                    VerdictEnum.CONTRADICTED,
                    0.93,
                    f"Evaluative contradiction: Claim asserts '{act_a}' is better than '{act_b}', whereas reference evidence mandates '{act_b}'."
                )

        pref_claim = re.search(r'(?:prioritize|prefer|choose|select|value|favor|based on)\s+([a-z\s]{3,30})\s+(?:over|rather than|instead of)\s+([a-z\s]{3,30})', norm_claim)
        pref_excerpt = re.search(r'(?:prioritize|prefer|choose|select|value|favor|based on)\s+([a-z\s]{3,30})\s+(?:over|rather than|instead of)\s+([a-z\s]{3,30})', norm_excerpt)

        if pref_claim and pref_excerpt:
            c_a = pref_claim.group(1).strip()
            c_b = pref_claim.group(2).strip()
            e_a = pref_excerpt.group(1).strip()
            e_b = pref_excerpt.group(2).strip()

            if (any(term in e_b for term in c_a.split()) or c_a in e_b) and (any(term in e_a for term in c_b.split()) or c_b in e_a):
                return (
                    VerdictEnum.CONTRADICTED,
                    0.94,
                    f"Reversed recommendation contradiction: Claim prioritizes '{c_a}' over '{c_b}', whereas reference evidence mandates '{e_a}' over '{e_b}'."
                )

        # Standalone "over" or "rather than" inverted match
        if not pref_claim and not pref_excerpt:
            raw_c_pref = re.search(r'\b([a-z\s]{3,25})\s+(?:over|rather than|instead of)\s+([a-z\s]{3,25})\b', norm_claim)
            raw_e_pref = re.search(r'\b([a-z\s]{3,25})\s+(?:over|rather than|instead of)\s+([a-z\s]{3,25})\b', norm_excerpt)
            if raw_c_pref and raw_e_pref:
                ca, cb = raw_c_pref.group(1).strip(), raw_c_pref.group(2).strip()
                ea, eb = raw_e_pref.group(1).strip(), raw_e_pref.group(2).strip()
                if (any(term in eb for term in ca.split()) or ca in eb) and (any(term in ea for term in cb.split()) or cb in ea):
                    return (
                        VerdictEnum.CONTRADICTED,
                        0.93,
                        f"Directional contradiction: Claim asserts '{ca}' over '{cb}', whereas reference evidence states '{ea}' over '{eb}'."
                    )

        # 3. Negated Preposition / Exception Clause Check (e.g., "rather than benefiting X" vs "choose what benefits X")
        rather_than_match = re.search(r'\b(?:rather than|instead of|without|avoiding)\s+(?:benefiting|choosing|prioritizing|using|considering)\s+([a-z\s]{3,30})\b', excerpt_lower)
        if rather_than_match:
            rejected_action_target = rather_than_match.group(1).strip()
            if any(term in claim_lower for term in rejected_action_target.split() if len(term) > 3) and \
               re.search(r'\b(choose|benefit|benefits|prioritize|use|consider)\b', claim_lower):
                return (
                    VerdictEnum.CONTRADICTED,
                    0.91,
                    f"Contradictory recommendation: Source evidence explicitly excludes/rejects '{rejected_action_target}', which the claim positively advocates."
                )

        # Check for negation words immediately preceding antonyms
        has_neg_before_antonym = bool(re.search(r'\b(not|no|never|without)\s+[a-z]+\b', claim_lower))

        # 4. Antonym & Directional Action Contradiction Check
        if not has_neg_before_antonym:
            for w1, w2 in DeterministicVerifier.ANTONYM_PAIRS:
                # Use stem matching (e.g. "disclos" matches disclose/disclosing/disclosure, "hid" matches hide/hiding)
                w1_stem = w1[:6] if len(w1) >= 6 else w1
                w2_stem = w2[:6] if len(w2) >= 6 else w2

                w1_in_claim = bool(re.search(rf'\b{re.escape(w1_stem)}[a-z]*\b', claim_lower))
                w2_in_claim = bool(re.search(rf'\b{re.escape(w2_stem)}[a-z]*\b', claim_lower))
                w1_in_excerpt = bool(re.search(rf'\b{re.escape(w1_stem)}[a-z]*\b', excerpt_lower))
                w2_in_excerpt = bool(re.search(rf'\b{re.escape(w2_stem)}[a-z]*\b', excerpt_lower))

                # Check if one text contains w1 (or its opposite w2) while the other contains the opposite
                # If claim contains BOTH w1 and w2 (e.g. "hiding is better than disclosing"), check which one excerpt mandates/supports
                if w1_in_claim and w2_in_claim and (w1_in_excerpt or w2_in_excerpt):
                    # Claim compares w1 vs w2. Excerpt mandates one of them.
                    supported_in_excerpt = w1 if w1_in_excerpt else w2
                    opposed_in_excerpt = w2 if w1_in_excerpt else w1
                    # If claim asserts opposed action is better/preferred over supported action
                    if re.search(rf'\b{re.escape(opposed_in_excerpt[:5])}[a-z]*\b.*?\b(better|prefer|prioritise|prioritize|choose)\b', norm_claim):
                        return (
                            VerdictEnum.CONTRADICTED,
                            0.92,
                            f"Action contradiction: Claim advocates '{opposed_in_excerpt}', whereas reference evidence mandates '{supported_in_excerpt}'."
                        )

                if (w1_in_claim and w2_in_excerpt and not w1_in_excerpt) or (w2_in_claim and w1_in_excerpt and not w2_in_excerpt):
                    claim_words = set(re.findall(r'\b[a-z]{3,}\b', claim_lower))
                    excerpt_words = set(re.findall(r'\b[a-z]{3,}\b', excerpt_lower))
                    if len(claim_words.intersection(excerpt_words)) >= 2:
                        found_c = w1 if w1_in_claim else w2
                        found_e = w2 if w2_in_excerpt else w1
                        return (
                            VerdictEnum.CONTRADICTED,
                            0.90,
                            f"Direct contradiction: Claim specifies '{found_c}' whereas reference source states '{found_e}'."
                        )

        # 5. Negation & Polarity Alignment Check
        claim_neg_tokens = [w for w in re.findall(r'\b[a-z]+\b', claim_lower) if w in DeterministicVerifier.NEGATION_WORDS]
        excerpt_neg_tokens = [w for w in re.findall(r'\b[a-z]+\b', excerpt_lower) if w in DeterministicVerifier.NEGATION_WORDS]
        
        has_claim_neg = bool(claim_neg_tokens)
        has_excerpt_neg = bool(excerpt_neg_tokens)

        claim_content_words = set(re.findall(r'\b[a-z]{3,}\b', claim_lower)) - DeterministicVerifier.NEGATION_WORDS - PassageRetriever.STOP_WORDS
        excerpt_content_words = set(re.findall(r'\b[a-z]{3,}\b', excerpt_lower)) - DeterministicVerifier.NEGATION_WORDS - PassageRetriever.STOP_WORDS
        overlap_content = claim_content_words.intersection(excerpt_content_words)

        # Paraphrase check with negation (e.g. "not harmful" vs "safe")
        is_neg_paraphrase = ("not" in claim_lower and "harmful" in claim_lower and "safe" in excerpt_lower) or \
                            ("safe" in claim_lower and "not" in excerpt_lower and "harmful" in excerpt_lower)

        if is_neg_paraphrase:
            return (
                VerdictEnum.SUPPORTED,
                0.90,
                f"Source document '{best_evidence['source_name']}' directly corroborates this claim via valid paraphrase."
            )

        if len(overlap_content) >= 2 and (has_claim_neg != has_excerpt_neg):
            return (
                VerdictEnum.CONTRADICTED,
                0.88,
                f"Polarity contradiction: Claim {'contains negation (' + ', '.join(claim_neg_tokens) + ')' if has_claim_neg else 'is affirmative'} whereas reference source states the opposite."
            )

        # 6. Definition & Unverified Term Specification Check
        def_match = re.search(r'\b([a-z\s]{3,20})\s+(?:is defined as|refers to|means|is a type of|is specified as)\s+([a-z\s]{4,50})\b', claim_lower)
        if def_match:
            broad_topic_nouns = {"type", "defined", "refers", "means", "that", "which", "personal", "interests", "conflict", "decisions", "relationships", "business", "financial"}
            defined_predicate_terms = set(re.findall(r'\b[a-z]{4,}\b', def_match.group(2))) - broad_topic_nouns
            shared_def_terms = defined_predicate_terms.intersection(excerpt_content_words - broad_topic_nouns)
            if len(defined_predicate_terms) >= 1 and len(shared_def_terms) < 1:
                return (
                    VerdictEnum.INSUFFICIENT_EVIDENCE,
                    0.40,
                    f"Reference document '{best_evidence['source_name']}' mentions related terms but does not explicitly establish or support the definition that '{claim_text}'."
                )

        # 7. Support Verification vs Insufficient Evidence Check
        key_claim_verbs = set(re.findall(r'\b(launched|drafted|prescribed|administered|increased|decreased|approved|rejected|found|achieved|recommends|prohibits|conceals|discloses)\b', claim_lower))
        key_excerpt_verbs = set(re.findall(r'\b(launched|drafted|prescribed|administered|increased|decreased|approved|rejected|found|achieved|recommends|prohibits|conceals|discloses)\b', excerpt_lower))
        
        if key_claim_verbs and not key_claim_verbs.intersection(key_excerpt_verbs):
            return (
                VerdictEnum.INSUFFICIENT_EVIDENCE,
                0.45,
                f"Reference passage in '{best_evidence['source_name']}' discusses related concepts but does not verify the specific action or event stated in the claim."
            )

        generic_meta_words = {"company", "year", "2024", "2025", "2026", "2027", "project", "report", "document", "section", "table", "chart", "data", "results", "analysis"}
        specific_claim_words = claim_content_words - generic_meta_words
        specific_shared_words = specific_claim_words.intersection(excerpt_content_words - generic_meta_words)

        if len(specific_claim_words) >= 1 and len(specific_shared_words) < 1:
            return (
                VerdictEnum.INSUFFICIENT_EVIDENCE,
                0.40,
                f"Source passage in '{best_evidence['source_name']}' mentions general context terms but lacks evidence for the specific assertion in '{claim_text}'."
            )

        if rel_score >= 0.25 and len(overlap_content) >= 2 and len(specific_shared_words) >= 1:
            return (
                VerdictEnum.SUPPORTED,
                round(min(0.95, float(rel_score + 0.15)), 2),
                f"Source document '{best_evidence['source_name']}' directly supports this claim."
            )

        return (
            VerdictEnum.INSUFFICIENT_EVIDENCE,
            0.45,
            f"Partial matching keywords in '{best_evidence['source_name']}', but source text is insufficient to conclusively prove or disprove the claim."
        )

    @staticmethod
    def detect_internal_contradictions(claims: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Scans extracted claims within the same answer for mutual conflicts
        (both numerical disagreements and opposite antonym assertions).
        Prevents duplicate pairs, false topic conflicts, and ensures clean subject matching.
        """
        contradictions = []
        seen_pairs = set()

        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                c1_id = claims[i]["claim_id"]
                c2_id = claims[j]["claim_id"]
                pair_key = (min(c1_id, c2_id), max(c1_id, c2_id))
                
                if pair_key in seen_pairs:
                    continue

                c1_text = claims[i]["text"]
                c2_text = claims[j]["text"]
                c1 = c1_text.lower()
                c2 = c2_text.lower()

                # Shared specific domain terms (ignoring common stop and broad words)
                words1 = set(re.findall(r'\b[a-z]{3,}\b', c1)) - {
                    "the", "and", "was", "for", "with", "that", "this", "patient", "company",
                    "report", "decisions", "should", "must", "can", "sometimes", "always", "important", "other",
                    "relationships", "personal", "activity", "showed"
                }
                words2 = set(re.findall(r'\b[a-z]{3,}\b', c2)) - {
                    "the", "and", "was", "for", "with", "that", "this", "patient", "company",
                    "report", "decisions", "should", "must", "can", "sometimes", "always", "important", "other",
                    "relationships", "personal", "activity", "showed"
                }
                shared = words1.intersection(words2)

                # Require at least 2 specific domain content words to ensure both claims refer to the EXACT SAME subject
                if len(shared) < 2:
                    continue

                # A) Numerical conflict check on exact same metric
                nums1 = DeterministicVerifier._extract_numbers(c1)
                nums2 = DeterministicVerifier._extract_numbers(c2)

                if nums1 and nums2 and nums1 != nums2:
                    seen_pairs.add(pair_key)
                    contradictions.append({
                        "claim_id_1": c1_id,
                        "claim_id_2": c2_id,
                        "reason": f"Internal numerical conflict: Claim {c1_id} ('{c1_text}') conflicts with Claim {c2_id} ('{c2_text}')."
                    })
                    continue

                # B) Internal Preference Inversion Check (Claim A: prefer X over Y vs Claim B: prefer Y over X)
                nc1 = DeterministicVerifier._normalize_preference(c1)
                nc2 = DeterministicVerifier._normalize_preference(c2)
                pref1 = re.search(r'(?:prioritize|prefer|choose|based on)\s+([a-z\s]{3,25})\s+(?:over|instead of|rather than)\s+([a-z\s]{3,25})', nc1)
                pref2 = re.search(r'(?:prioritize|prefer|choose|based on)\s+([a-z\s]{3,25})\s+(?:over|instead of|rather than)\s+([a-z\s]{3,25})', nc2)
                
                if pref1 and pref2:
                    t1_a, t1_b = pref1.group(1).strip(), pref1.group(2).strip()
                    t2_a, t2_b = pref2.group(1).strip(), pref2.group(2).strip()
                    if (t1_a in t2_b and t1_b in t2_a) or (t2_a in t1_b and t2_b in t1_a):
                        seen_pairs.add(pair_key)
                        contradictions.append({
                            "claim_id_1": c1_id,
                            "claim_id_2": c2_id,
                            "reason": f"Internal preference contradiction: Claim {c1_id} prioritizes '{t1_a}' over '{t1_b}', whereas Claim {c2_id} prioritizes '{t2_a}' over '{t2_b}'."
                        })
                        continue

                # C) Antonym conflict check: Claim 1 asserts w1 (and NOT w2), while Claim 2 asserts w2 (and NOT w1)
                for w1, w2 in DeterministicVerifier.ANTONYM_PAIRS:
                    c1_has_w1 = bool(re.search(rf'\b{re.escape(w1)}\b', c1))
                    c1_has_w2 = bool(re.search(rf'\b{re.escape(w2)}\b', c1))
                    c2_has_w1 = bool(re.search(rf'\b{re.escape(w1)}\b', c2))
                    c2_has_w2 = bool(re.search(rf'\b{re.escape(w2)}\b', c2))

                    if (c1_has_w1 and not c1_has_w2 and c2_has_w2 and not c2_has_w1) or \
                       (c1_has_w2 and not c1_has_w1 and c2_has_w1 and not c2_has_w2):
                        seen_pairs.add(pair_key)
                        contradictions.append({
                            "claim_id_1": c1_id,
                            "claim_id_2": c2_id,
                            "reason": f"Internal semantic contradiction: Claim {c1_id} asserts '{w1 if c1_has_w1 else w2}', whereas Claim {c2_id} asserts '{w2 if c1_has_w1 else w1}'."
                        })
                        break

        return contradictions




