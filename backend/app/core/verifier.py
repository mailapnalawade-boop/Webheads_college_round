import json
import uuid
<<<<<<< HEAD
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
=======
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from fastapi import HTTPException, status
>>>>>>> ec6e633c716b8e29e61a630b74e1116960f129a3
from google import genai
from google.genai import types

from app.config import settings
from app.schemas.audit import (
    AuditRequest, AuditResponse, ClaimItem, EvidenceItem,
    SummaryMetrics, VerdictEnum, ClaimFlags,
    LogicalInconsistencyItem, SafetyAnalysisResult
)
from app.core.extractor import ClaimExtractor
from app.core.parser import DocumentParser
from app.core.retriever import PassageRetriever
from app.core.fallback import DeterministicVerifier
from app.core.safety import SafetyAnalyzer

logger = logging.getLogger("second_opinion.verifier")

PROMPT_VERSION = "2026.04.1"
_AUDIT_CACHE: Dict[str, AuditResponse] = {}
_MAX_CACHE_SIZE = 128

class AuditEngine:
    """
    Verification Orchestrator for Second Opinion.
    Integrates Atomic Claim Extraction, Ground-Truth Evidence Retrieval,
    Low-Temperature LLM / Deterministic Verification, Logical Inconsistency Analysis,
    and Potentially Unsafe Recommendation Analysis.
    """

    @staticmethod
    def _classify_llm_error(err: Exception, model_name: str, stage: str) -> Tuple[int, str]:
        """
        Classifies upstream LLM errors into actionable diagnostics and appropriate HTTP status codes.
        - Invalid/rejected API key -> HTTP 401 Unauthorized with clear actionable guidance.
        - Model 404/NOT_FOUND -> HTTP 404 Not Found with GEMINI_MODEL configuration guidance.
        - Rate limit / Quota exceeded -> HTTP 502 Bad Gateway with ResourceExhausted detail.
        - General API/Network failure -> HTTP 502 Bad Gateway.
        """
        err_str = str(err)
        err_lower = err_str.lower()

        # 1. Invalid or Rejected API Key
        is_invalid_key = any(pattern in err_str for pattern in [
            "API_KEY_INVALID", "API key not valid", "API_KEY_SERVICE_BLOCKED",
            "IP_NOT_PERMITTED"
        ]) or (
            ("api key" in err_lower or "api_key" in err_lower) and
            any(w in err_lower for w in ["invalid", "rejected", "not valid", "unauthorized", "expired", "missing"])
        ) or "PERMISSION_DENIED" in err_str or "UNAUTHENTICATED" in err_str

        if is_invalid_key:
            return (
                status.HTTP_401_UNAUTHORIZED,
                f"The provided Gemini API key is invalid or has been rejected by Google AI (API_KEY_INVALID). "
                f"Please verify your API key in Configure Key or set a valid GEMINI_API_KEY in your environment, "
                f"or switch to Offline Deterministic Mode in Advanced Settings."
            )

        # 2. Model 404 / NOT_FOUND
        if "404" in err_str or "NOT_FOUND" in err_str or "not found" in err_lower:
            return (
                status.HTTP_404_NOT_FOUND,
                f"Configured Gemini model '{model_name}' was not found or is no longer available during {stage} "
                f"(404 NOT_FOUND: {err_str}). Please verify model availability for your API key and update the "
                f"GEMINI_MODEL environment variable (e.g., 'gemini-3.8-flash' or another currently supported model), "
                f"or switch to Offline Deterministic Mode in Advanced Settings."
            )

        # 3. Rate Limit / Resource Exhausted
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "ResourceExhausted" in err_str or "quota" in err_lower:
            return (
                status.HTTP_502_BAD_GATEWAY,
                f"Gemini API {stage} failed with model '{model_name}': Google GenAI RateLimit (429 ResourceExhausted). "
                f"You can retry the audit, check your API key/network, or switch to Offline Deterministic Mode in Advanced Settings."
            )

        # 4. General Upstream Provider Failure
        return (
            status.HTTP_502_BAD_GATEWAY,
            f"Gemini API {stage} failed with model '{model_name}': {err_str}. "
            f"You can retry the audit, check your API key/network, or switch to Offline Deterministic Mode in Advanced Settings."
        )

    @staticmethod
    def _format_llm_error(err: Exception, model_name: str, stage: str) -> str:
        """Formats upstream LLM errors with clear diagnostics and availability guidance (backward compatible)."""
        _, detail = AuditEngine._classify_llm_error(err, model_name, stage)
        return detail

    @staticmethod
    def _compute_cache_key(request: AuditRequest, mode: str, model_name: str) -> str:
        """Generates a deterministic hash for identical input and model configurations."""
        norm_answer = " ".join(request.answer_text.strip().split())
        doc_signature = "|".join(
            f"{d.filename}:{hashlib.sha256((d.content or '').encode('utf-8')).hexdigest()[:12]}:{d.content_type}"
            for d in sorted(request.documents, key=lambda x: x.filename or "")
        )
        options_sig = f"{mode}:{model_name}:{request.options.enable_web_search}:{request.options.top_k_passages}:{request.options.similarity_threshold}:{PROMPT_VERSION}"
        raw = f"{norm_answer}###{doc_signature}###{options_sig}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def run_audit(request: AuditRequest) -> AuditResponse:
        audit_id = f"audit_{uuid.uuid4().hex[:8]}"
        logger.info(f"Starting audit {audit_id} with {len(request.documents)} documents.")

        # 1. Resolve Verification Mode
        force_offline = (
            request.options.force_deterministic_fallback or
            request.options.verification_mode == "offline"
        )
        import os
        api_key = (
            request.api_key or
            settings.GEMINI_API_KEY or
            os.getenv("GEMINI_API_KEY") or
            os.getenv("GOOGLE_API_KEY") or
            ""
        ).strip().strip('"').strip("'")
        explicit_llm_mode = request.options.verification_mode == "llm"

        if explicit_llm_mode and not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GEMINI_API_KEY is not configured on the backend environment. Please set GEMINI_API_KEY in the server environment or switch to Offline Deterministic Mode in Advanced Settings."
            )

        use_llm = not force_offline and bool(api_key)
        active_mode = "llm_api" if use_llm else "offline_deterministic"
        model_name = settings.DEFAULT_MODEL if use_llm else "Deterministic Rule & BM25 Engine"

        # 2. Check Cache for Identical Normalized Inputs
        cache_key = AuditEngine._compute_cache_key(request, active_mode, model_name)
        if cache_key in _AUDIT_CACHE:
            cached_resp = _AUDIT_CACHE[cache_key].model_copy(deep=True)
            cached_resp.audit_id = audit_id
            cached_resp.timestamp = datetime.now(timezone.utc).isoformat()
            cached_resp.cached = True
            logger.info(f"Returning cached audit report for key {cache_key[:12]}")
            return cached_resp

        # 3. Extract Atomic Claims
        if use_llm:
            try:
                extracted_claims = ClaimExtractor.extract_claims_with_llm(
                    request.answer_text, api_key=api_key, model_name=model_name
                )
            except Exception as e:
                logger.error(f"LLM claim extraction failed: {type(e).__name__}")
                status_code, err_detail = AuditEngine._classify_llm_error(e, model_name, "claim extraction")
                raise HTTPException(status_code=status_code, detail=err_detail)
        else:
            extracted_claims = ClaimExtractor.extract_claims(request.answer_text)

        logger.info(f"Extracted {len(extracted_claims)} atomic claims.")

        # 4. Ingest Reference Documents into Passages
        parsed_passages = DocumentParser.parse_documents(request.documents)
        retriever = PassageRetriever(parsed_passages)

        # 5. Detect Logical Inconsistencies between Extracted Claims
        logical_inconsistencies = AuditEngine._detect_logical_inconsistencies(
            extracted_claims=extracted_claims,
            use_llm=use_llm,
            api_key=api_key,
            model_name=model_name
        )

        conflicting_claim_ids = set()
        for li in logical_inconsistencies:
            conflicting_claim_ids.add(li.claim_id_1)
            if li.claim_id_2:
                conflicting_claim_ids.add(li.claim_id_2)

        # 6. Verify Each Claim against Evidence
        verified_claims: List[ClaimItem] = []

        for claim in extracted_claims:
            claim_id = claim["claim_id"]
            claim_text = claim["text"]
            start_char = claim["start_char"]
            end_char = claim["end_char"]

            # Retrieve top matching passages deterministically
            evidence_matches = retriever.retrieve(claim_text, top_k=request.options.top_k_passages)

            # Public web search fallback if enabled and document evidence is scarce
            if request.options.enable_web_search and (not evidence_matches or evidence_matches[0]["relevance_score"] < 0.35):
                web_matches = PassageRetriever.search_web(claim_text, max_results=2)
                if web_matches:
                    evidence_matches = (evidence_matches or []) + web_matches

            evidence_matches.sort(key=lambda x: (x["relevance_score"], x["source_name"]), reverse=True)

            verdict = VerdictEnum.INSUFFICIENT_EVIDENCE
            confidence = 0.50
            explanation = ""
            supporting_indices = []
            contradicting_indices = []
            has_source_disagreement = False

            if use_llm:
                try:
                    (
                        verdict,
                        confidence,
                        explanation,
                        supporting_indices,
                        contradicting_indices,
                        has_source_disagreement
                    ) = AuditEngine._verify_with_gemini(
                        claim_text=claim_text,
                        evidence_matches=evidence_matches,
                        api_key=api_key,
                        model_name=model_name
                    )
                except Exception as err:
                    logger.error(f"Gemini API verification failed for {claim_id}: {type(err).__name__}")
                    # NEVER silently fall back to BM25 when LLM mode is active
                    status_code, err_detail = AuditEngine._classify_llm_error(err, model_name, f"claim verification ('{claim_text[:40]}...')")
                    raise HTTPException(
                        status_code=status_code,
                        detail=err_detail
                    )
            else:
                verdict, confidence, explanation = DeterministicVerifier.verify_claim(
                    claim_text, evidence_matches
                )
                if verdict == VerdictEnum.SUPPORTED and evidence_matches:
                    supporting_indices = [0]
                elif verdict == VerdictEnum.CONTRADICTED and evidence_matches:
                    contradicting_indices = [0]

            is_internally_inconsistent = claim_id in conflicting_claim_ids

            # Primary Category Assignment (Mutually Exclusive):
            # 1. Contradicted by evidence -> CONTRADICTED
            # 2. Mutually inconsistent with another claim & not contradicted -> LOGICAL_INCONSISTENCY
            # 3. Supported by evidence -> SUPPORTED
            # 4. Otherwise -> INSUFFICIENT_EVIDENCE
            if verdict == VerdictEnum.CONTRADICTED:
                primary_verdict = VerdictEnum.CONTRADICTED
            elif is_internally_inconsistent and verdict != VerdictEnum.CONTRADICTED:
                primary_verdict = VerdictEnum.LOGICAL_INCONSISTENCY
            elif verdict == VerdictEnum.SUPPORTED:
                primary_verdict = VerdictEnum.SUPPORTED
            else:
                primary_verdict = VerdictEnum.INSUFFICIENT_EVIDENCE

            # Separate and populate Supporting and Contradicting Evidence
            supporting_evidence: List[EvidenceItem] = []
            contradicting_evidence: List[EvidenceItem] = []

            for idx, match in enumerate(evidence_matches):
                is_contradictory = (idx in contradicting_indices) or (
                    primary_verdict == VerdictEnum.CONTRADICTED and not supporting_indices and idx == 0
                )
                is_supporting = (idx in supporting_indices) or (
                    primary_verdict == VerdictEnum.SUPPORTED and not contradicting_indices and idx == 0
                )

                ev_item = EvidenceItem(
                    excerpt=match["excerpt"],
                    source_name=match["source_name"],
                    page_number=match.get("page_number", 1),
                    relevance_score=match["relevance_score"],
                    match_type=match["match_type"],
                    is_contradictory=is_contradictory,
                    is_external=(match["match_type"] == "web_search")
                )

                if is_contradictory:
                    contradicting_evidence.append(ev_item)
                elif is_supporting:
                    supporting_evidence.append(ev_item)

            all_candidate_evidence = []
            for match in evidence_matches:
                all_candidate_evidence.append(EvidenceItem(
                    excerpt=match["excerpt"],
                    source_name=match["source_name"],
                    page_number=match.get("page_number", 1),
                    relevance_score=match["relevance_score"],
                    match_type=match["match_type"],
                    is_contradictory=(primary_verdict == VerdictEnum.CONTRADICTED),
                    is_external=(match["match_type"] == "web_search")
                ))

            reported_evidence = supporting_evidence + contradicting_evidence
            if not reported_evidence:
                reported_evidence = all_candidate_evidence

            source_references = list(dict.fromkeys(e.source_name for e in reported_evidence))

            # Uncertainty Level classification (Low, Moderate, High)
            if confidence >= 0.85:
                uncertainty_level = "Low"
            elif confidence >= 0.60:
                uncertainty_level = "Moderate"
            else:
                uncertainty_level = "High"

            inconsistency_note = None
            if is_internally_inconsistent:
                matching_conflicts = [
                    c.explanation for c in logical_inconsistencies
                    if c.claim_id_1 == claim_id or c.claim_id_2 == claim_id
                ]
                inconsistency_note = "; ".join(matching_conflicts) if matching_conflicts else "Contradicts another statement in the answer."

            verified_claims.append(ClaimItem(
                claim_id=claim_id,
                text=claim_text,
                start_char=start_char,
                end_char=end_char,
                verdict=primary_verdict,
                confidence=confidence,
                uncertainty_level=uncertainty_level,
                explanation=explanation,
                evidence=reported_evidence,
                supporting_evidence=supporting_evidence,
                contradicting_evidence=contradicting_evidence,
                source_references=source_references,
                inconsistency_details=inconsistency_note,
                flags=ClaimFlags(
                    is_ambiguous=(uncertainty_level == "High"),
                    source_disagreement=has_source_disagreement,
                    internal_contradiction=is_internally_inconsistent
                )
            ))

        verified_claims.sort(key=lambda c: (c.start_char, c.claim_id))

        # 7. Potentially Unsafe Recommendation Analysis
        if use_llm:
            try:
                safety_analysis = SafetyAnalyzer.analyze_with_llm(
                    answer_text=request.answer_text,
                    claims=[c.model_dump() for c in verified_claims],
                    passages=parsed_passages,
                    api_key=api_key,
                    model_name=model_name,
                    raise_on_error=True
                )
            except Exception as e:
                logger.error(f"LLM safety analysis failed: {type(e).__name__}")
                status_code, err_detail = AuditEngine._classify_llm_error(e, model_name, "safety analysis")
                raise HTTPException(
                    status_code=status_code,
                    detail=err_detail
                )
        else:
            safety_analysis = SafetyAnalyzer.analyze_deterministic(
                answer_text=request.answer_text,
                claims=[c.model_dump() for c in verified_claims],
                passages=parsed_passages
            )

        # 8. Compute Summary Metrics (Mutually Exclusive, exactly sums to total_claims)
        supported_count = sum(1 for c in verified_claims if c.verdict == VerdictEnum.SUPPORTED)
        contradicted_count = sum(1 for c in verified_claims if c.verdict == VerdictEnum.CONTRADICTED)
        insufficient_count = sum(1 for c in verified_claims if c.verdict == VerdictEnum.INSUFFICIENT_EVIDENCE)
        inconsistent_count = sum(1 for c in verified_claims if c.verdict == VerdictEnum.LOGICAL_INCONSISTENCY)
        total_claims = len(verified_claims)

        credibility_score, credibility_breakdown = AuditEngine.calculate_credibility(
            supported_count=supported_count,
            insufficient_count=insufficient_count,
            contradicted_count=contradicted_count,
            total_claims=total_claims,
            inconsistent_count=inconsistent_count
        )

        summary = SummaryMetrics(
            total_claims=total_claims,
            supported_count=supported_count,
            contradicted_count=contradicted_count,
            insufficient_evidence_count=insufficient_count,
            logical_inconsistency_count=inconsistent_count,
            unsafe_recommendations_count=safety_analysis.flagged_count,
            credibility_score=credibility_score,
            credibility_breakdown=credibility_breakdown,
            internal_contradictions_detected=len(logical_inconsistencies),
            sources_analyzed=len(request.documents)
        )

        audit_config = {
            "verification_mode": active_mode,
            "model_name": model_name,
            "deterministic_temperature": 0.0 if use_llm else None,
            "top_k_passages": request.options.top_k_passages,
            "similarity_threshold": request.options.similarity_threshold,
            "enable_web_search": request.options.enable_web_search,
            "sources_analyzed_count": len(request.documents)
        }

        response = AuditResponse(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
<<<<<<< HEAD
=======
            verification_mode=active_mode,
            model_info=model_name,
            cached=False,
            audit_configuration=audit_config,
            limitations="Automated audit evaluated strictly against supplied reference documents. Self-reported confidence reflects internal certainty, not calibrated statistical probability of ground truth.",
>>>>>>> ec6e633c716b8e29e61a630b74e1116960f129a3
            summary=summary,
            claims=verified_claims,
            logical_inconsistencies=logical_inconsistencies,
            safety_analysis=safety_analysis,
            original_answer=request.answer_text
        )

        # Cache response
        if len(_AUDIT_CACHE) >= _MAX_CACHE_SIZE:
            _AUDIT_CACHE.pop(next(iter(_AUDIT_CACHE)))
        _AUDIT_CACHE[cache_key] = response

        logger.info(f"Audit {audit_id} complete. Score: {credibility_score}%. Claims: {total_claims}. Mode: {active_mode}.")
        return response

    @staticmethod
    def _detect_logical_inconsistencies(
        extracted_claims: List[Dict[str, Any]],
        use_llm: bool,
        api_key: str = "",
        model_name: Optional[str] = None
    ) -> List[LogicalInconsistencyItem]:
        """
        Detects pairwise mutual contradictions and logical non-sequiturs across claims.
        Combines deterministic graph analysis with low-temperature LLM consistency checking.
        """
        logical_inconsistencies: List[LogicalInconsistencyItem] = []
        seen_pairs = set()

        # 1. Deterministic Rule Contradictions
        internal_conflicts = DeterministicVerifier.detect_internal_contradictions(extracted_claims)
        for idx, conflict in enumerate(internal_conflicts):
            c1_id = conflict["claim_id_1"]
            c2_id = conflict["claim_id_2"]
            pair_key = tuple(sorted([c1_id, c2_id]))
            seen_pairs.add(pair_key)

            c1_text = next((c["text"] for c in extracted_claims if c["claim_id"] == c1_id), "")
            c2_text = next((c["text"] for c in extracted_claims if c["claim_id"] == c2_id), "")

            logical_inconsistencies.append(LogicalInconsistencyItem(
                conflict_id=f"conflict_{len(logical_inconsistencies) + 1}",
                claim_id_1=c1_id,
                claim_id_2=c2_id,
                claim_text_1=c1_text,
                claim_text_2=c2_text,
                inconsistency_type="mutual_contradiction",
                explanation=conflict["reason"]
            ))

        # 2. LLM Consistency Analysis (if in LLM mode and multiple claims exist)
        if use_llm and len(extracted_claims) >= 2:
            try:
                resolved_model = model_name or settings.DEFAULT_MODEL
                client = genai.Client(api_key=(api_key or "").strip().strip('"').strip("'"))
                claims_payload = [{"claim_id": c["claim_id"], "text": c["text"]} for c in extracted_claims]
                prompt = f"""You are a formal logic and consistency auditor. Inspect these atomic claims extracted from an AI-generated answer.
Identify ANY mutual contradictions (e.g. conflicting numerical metrics, opposite outcomes for the same entity) or logical non-sequiturs.

CLAIMS:
{json.dumps(claims_payload, indent=2)}

RULES:
- Only flag clear, explicit logical conflicts.
- Do NOT flag ordinary complementary or sequential claims.
- Return ONLY valid JSON matching:
{{
  "conflicts": [
    {{
      "claim_id_1": "claim_x",
      "claim_id_2": "claim_y",
      "inconsistency_type": "mutual_contradiction" | "non_sequitur",
      "explanation": "concise explanation of the contradiction or reasoning gap"
    }}
  ]
}}"""
                resp = client.models.generate_content(
                    model=resolved_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json"
                    )
                )
                raw_text = resp.text.strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[-1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text.rsplit("```", 1)[0]
                    raw_text = raw_text.strip()

                data = json.loads(raw_text)
                llm_conflicts = data.get("conflicts", [])
                for lc in llm_conflicts:
                    c1 = lc.get("claim_id_1")
                    c2 = lc.get("claim_id_2")
                    if not c1 or not c2 or c1 == c2:
                        continue
                    pair_key = tuple(sorted([c1, c2]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    c1_text = next((c["text"] for c in extracted_claims if c["claim_id"] == c1), "")
                    c2_text = next((c["text"] for c in extracted_claims if c["claim_id"] == c2), "")

                    logical_inconsistencies.append(LogicalInconsistencyItem(
                        conflict_id=f"conflict_{len(logical_inconsistencies) + 1}",
                        claim_id_1=c1,
                        claim_id_2=c2,
                        claim_text_1=c1_text,
                        claim_text_2=c2_text,
                        inconsistency_type=lc.get("inconsistency_type", "mutual_contradiction"),
                        explanation=lc.get("explanation", "Claims assert mutually incompatible statements.")
                    ))
            except Exception as e:
                logger.warning(f"LLM logical inconsistency check skipped on error: {e}")

        return logical_inconsistencies

    @staticmethod
    def calculate_credibility(
        supported_count: int,
        insufficient_count: int,
        contradicted_count: int,
        total_claims: int,
        inconsistent_count: int = 0
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculates credibility score with transparent mathematical breakdown:
        - Supported claims: 1.0 point
        - Insufficient evidence claims: 0.5 point (unverified, neutral)
        - Contradicted claims: 0.0 point (penalized)
        - Logical inconsistencies: 0.0 point (penalized)
        """
        if total_claims > 0:
            raw_score = ((supported_count + 0.5 * insufficient_count) / total_claims) * 100.0
            credibility_score = round(raw_score, 1)
        else:
            credibility_score = 100.0

        credibility_breakdown = {
            "formula": "(Supported + 0.5 * Insufficient) / Total * 100",
            "supported_claims": supported_count,
            "insufficient_evidence_claims": insufficient_count,
            "contradicted_claims": contradicted_count,
            "logical_inconsistency_claims": inconsistent_count,
            "total_claims": total_claims,
            "supported_points": float(supported_count),
            "insufficient_points": float(0.5 * insufficient_count),
            "penalized_points": float(contradicted_count + inconsistent_count)
        }
        return credibility_score, credibility_breakdown

    @staticmethod
    def _verify_with_gemini(
        claim_text: str,
        evidence_matches: List[Dict[str, Any]],
        api_key: str,
        model_name: Optional[str] = None
    ) -> Tuple[VerdictEnum, float, str, List[int], List[int], bool]:
        """
        Calls Gemini API with deterministic temperature=0.0 and schema validation.
        Returns: (verdict, confidence, explanation, supporting_indices, contradicting_indices, source_disagreement)
        """
        resolved_model = model_name or settings.DEFAULT_MODEL
        client = genai.Client(api_key=(api_key or "").strip().strip('"').strip("'"))

        indexed_passages = []
        for idx, e in enumerate(evidence_matches):
            indexed_passages.append(
                f"[{idx}] Source: {e['source_name']} (Page {e.get('page_number', 1)}):\n\"{e['excerpt']}\""
            )
        evidence_str = "\n\n".join(indexed_passages) or "No relevant reference passages found in provided documents."

        prompt = f"""You are a rigorous, evidence-grounded AI Answer Auditor. Evaluate the CLAIM strictly against the REFERENCE EVIDENCE PASSAGES.

CLAIM:
\"{claim_text}\"

REFERENCE EVIDENCE PASSAGES:
{evidence_str}

CLASSIFICATION CRITERIA:
1. "SUPPORTED": The reference evidence directly affirms, substantiates, or directly entails the claim.
2. "CONTRADICTED": The reference evidence directly conflicts with the claim (e.g. conflicting numerical figure, opposite direction/polarity, contradictory fact).
3. "INSUFFICIENT_EVIDENCE": The reference evidence does not contain sufficient facts to prove or disprove the claim. Absence of evidence is NOT proof of falsehood.

STRICT INTEGRITY RULES:
- Never fabricate citations, URLs, page numbers, or external facts. Only reference the provided numbered passages.
- Distinguish between missing evidence (INSUFFICIENT_EVIDENCE) and direct contradiction (CONTRADICTED).
- In "supporting_indices", specify 0-based indices of passages that directly support the claim.
- In "contradicting_indices", specify 0-based indices of passages that directly contradict the claim.
- If multiple sources disagree with each other, set "source_disagreement": true.
- Provide a concise 1-2 sentence factual explanation.

Return ONLY a valid JSON object matching:
{{
  "verdict": "SUPPORTED" | "CONTRADICTED" | "INSUFFICIENT_EVIDENCE",
  "confidence": 0.0 to 1.0,
  "explanation": "concise evidence-grounded explanation",
  "supporting_indices": [0],
  "contradicting_indices": [],
  "source_disagreement": false
}}"""

        for attempt in range(2):
            response = client.models.generate_content(
                model=resolved_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )

            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1]
                if raw_text.endswith("```"):
                    raw_text = raw_text.rsplit("```", 1)[0]
                raw_text = raw_text.strip()

            try:
                data = json.loads(raw_text)
                verdict_str = data.get("verdict", "INSUFFICIENT_EVIDENCE")
                if verdict_str in ("SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE"):
                    verdict = VerdictEnum(verdict_str)
                else:
                    verdict = VerdictEnum.INSUFFICIENT_EVIDENCE

                confidence = max(0.0, min(1.0, float(data.get("confidence", 0.85))))
                explanation = str(data.get("explanation", "Verified against reference evidence passages.")).strip()

                sup_raw = data.get("supporting_indices", [])
                con_raw = data.get("contradicting_indices", [])
                num_matches = len(evidence_matches)

                supporting_indices = [int(i) for i in sup_raw if isinstance(i, int) and 0 <= i < num_matches]
                contradicting_indices = [int(i) for i in con_raw if isinstance(i, int) and 0 <= i < num_matches]
                source_disagreement = bool(data.get("source_disagreement", False))

                return verdict, confidence, explanation, supporting_indices, contradicting_indices, source_disagreement
            except Exception as parse_err:
                if attempt == 1:
                    raise parse_err
                logger.warning(f"Retrying malformed Gemini JSON output (attempt {attempt + 1}): {parse_err}")

        return VerdictEnum.INSUFFICIENT_EVIDENCE, 0.50, "Verification inconclusive.", [], [], False
