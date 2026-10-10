import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from google import genai
from google.genai import types

from app.config import settings
from app.schemas.audit import (
    AuditRequest, AuditResponse, ClaimItem, EvidenceItem,
    SummaryMetrics, VerdictEnum, ClaimFlags
)
from app.core.extractor import ClaimExtractor
from app.core.parser import DocumentParser
from app.core.retriever import PassageRetriever
from app.core.fallback import DeterministicVerifier

logger = logging.getLogger("second_opinion.verifier")

class AuditEngine:
    """
    Main Verification Orchestrator for Second Opinion.
    Integrates Claim Extraction, Document Parsing, Hybrid Passage Retrieval,
    LLM (Gemini) Verification, and Deterministic Fallback Verification.
    """

    @staticmethod
    def run_audit(request: AuditRequest) -> AuditResponse:
        audit_id = f"audit_{uuid.uuid4().hex[:8]}"
        logger.info(f"Starting audit {audit_id} with {len(request.documents)} documents.")
        
        # 1. Extract Atomic Claims (excluding section headers, filler lines, and formatting)
        extracted_claims = ClaimExtractor.extract_claims(request.answer_text)
        logger.info(f"Extracted {len(extracted_claims)} atomic claims.")
        
        # 2. Ingest Reference Documents into Passages
        parsed_passages = DocumentParser.parse_documents(request.documents)
        retriever = PassageRetriever(parsed_passages)

        # 3. Detect Internal Contradictions between extracted claims
        internal_conflicts = DeterministicVerifier.detect_internal_contradictions(extracted_claims)
        conflicting_claim_ids = set()
        for conflict in internal_conflicts:
            conflicting_claim_ids.add(conflict["claim_id_1"])
            conflicting_claim_ids.add(conflict["claim_id_2"])

        # Determine if live Gemini API key is available
        api_key = request.api_key or settings.GEMINI_API_KEY
        use_live_api = bool(api_key) and not request.options.force_deterministic_fallback

        def verify_single_claim(claim: Dict[str, Any]) -> ClaimItem:
            claim_id = claim["claim_id"]
            claim_text = claim["text"]
            start_char = claim["start_char"]
            end_char = claim["end_char"]

            # Retrieve top matching passages
            evidence_matches = retriever.retrieve(claim_text, top_k=request.options.top_k_passages)

            # If web search is enabled and document evidence is insufficient or absent
            if request.options.enable_web_search and (not evidence_matches or evidence_matches[0]["relevance_score"] < 0.35):
                web_matches = PassageRetriever.search_web(claim_text, max_results=2)
                if web_matches:
                    evidence_matches = (evidence_matches or []) + web_matches

            verdict = VerdictEnum.INSUFFICIENT_EVIDENCE
            confidence = 0.50
            explanation = ""

            # Try Live Gemini Verification if key and evidence exist
            if use_live_api and evidence_matches:
                try:
                    verdict, confidence, explanation = AuditEngine._verify_with_gemini(
                        claim_text=claim_text,
                        evidence_matches=evidence_matches,
                        api_key=api_key
                    )
                except Exception as err:
                    logger.warning(f"Gemini API verification failed for {claim_id}: {err}. Falling back to deterministic verifier.")
                    # Fallback to Deterministic Verifier on API error, timeout, or parsing failure
                    verdict, confidence, explanation = DeterministicVerifier.verify_claim(
                        claim_text, evidence_matches
                    )
            else:
                # Deterministic Rule Verification
                verdict, confidence, explanation = DeterministicVerifier.verify_claim(
                    claim_text, evidence_matches
                )

            evidence_items = [
                EvidenceItem(
                    excerpt=match["excerpt"],
                    source_name=match["source_name"],
                    page_number=match.get("page_number", 1),
                    relevance_score=match["relevance_score"],
                    match_type=match["match_type"]
                ) for match in evidence_matches
            ]

            is_internal_contradiction = claim_id in conflicting_claim_ids

            return ClaimItem(
                claim_id=claim_id,
                text=claim_text,
                start_char=start_char,
                end_char=end_char,
                verdict=verdict,
                confidence=confidence,
                explanation=explanation,
                evidence=evidence_items,
                flags=ClaimFlags(
                    is_ambiguous=confidence < 0.60,
                    source_disagreement=False,
                    internal_contradiction=is_internal_contradiction
                )
            )

        # Parallelize claim verification across threads for fast execution
        verified_claims: List[ClaimItem] = []
        if extracted_claims:
            from concurrent.futures import ThreadPoolExecutor
            workers = min(10, max(1, len(extracted_claims)))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                verified_claims = list(executor.map(verify_single_claim, extracted_claims))

        supported_count = sum(1 for c in verified_claims if c.verdict == VerdictEnum.SUPPORTED)
        contradicted_count = sum(1 for c in verified_claims if c.verdict == VerdictEnum.CONTRADICTED)
        insufficient_count = sum(1 for c in verified_claims if c.verdict == VerdictEnum.INSUFFICIENT_EVIDENCE)
        total_claims = len(verified_claims)

        credibility_score, credibility_breakdown = AuditEngine.calculate_credibility(
            supported_count=supported_count,
            insufficient_count=insufficient_count,
            contradicted_count=contradicted_count,
            total_claims=total_claims
        )

        summary = SummaryMetrics(
            total_claims=total_claims,
            supported_count=supported_count,
            contradicted_count=contradicted_count,
            insufficient_evidence_count=insufficient_count,
            credibility_score=credibility_score,
            credibility_breakdown=credibility_breakdown,
            internal_contradictions_detected=len(internal_conflicts),
            sources_analyzed=len(request.documents)
        )

        logger.info(f"Audit {audit_id} complete. Credibility: {credibility_score}%. Supported: {supported_count}, Contradicted: {contradicted_count}, Insufficient: {insufficient_count}.")

        return AuditResponse(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            claims=verified_claims,
            original_answer=request.answer_text
        )

    @staticmethod
    def calculate_credibility(supported_count: int, insufficient_count: int, contradicted_count: int, total_claims: int) -> tuple:
        """
        Calculates a defensible, weighted credibility percentage and breakdown.
        - Supported claims contribute 1.0 point (100%)
        - Insufficient evidence claims contribute 0.5 point (50%, neutral state)
        - Contradicted claims contribute 0.0 point (0%, penalized)
        Formula: ((supported_count + 0.5 * insufficient_count) / total_claims) * 100
        """
        if total_claims > 0:
            credibility_score = round(((supported_count + 0.5 * insufficient_count) / total_claims) * 100.0, 1)
        else:
            credibility_score = 100.0

        credibility_breakdown = {
            "formula": "(Supported + 0.5 * Insufficient) / Total * 100",
            "supported_claims": supported_count,
            "insufficient_evidence_claims": insufficient_count,
            "contradicted_claims": contradicted_count,
            "total_claims": total_claims,
            "supported_points": float(supported_count),
            "insufficient_points": float(0.5 * insufficient_count),
            "contradicted_points": 0.0
        }
        return credibility_score, credibility_breakdown

    @staticmethod
    def _verify_with_gemini(claim_text: str, evidence_matches: List[Dict[str, Any]], api_key: str) -> tuple:
        client = genai.Client(api_key=api_key)
        
        evidence_str = "\n".join([f"- [{e['source_name']} (Page {e.get('page_number', 1)})]: {e['excerpt']}" for e in evidence_matches])
        
        prompt = f"""You are an expert AI Answer Auditor. Evaluate the following CLAIM against the provided REFERENCE EVIDENCE passages.

CLAIM: "{claim_text}"

REFERENCE EVIDENCE PASSAGES:
{evidence_str}

STRICT CLASSIFICATION RULES:
1. "SUPPORTED": The source evidence explicitly supports the claim or communicates the exact same meaning through a valid paraphrase.
2. "CONTRADICTED": The source evidence directly conflicts with the claim (e.g. numerical mismatch, opposite action, or contradictory fact).
3. "INSUFFICIENT_EVIDENCE": The source evidence does not provide enough information to verify whether the claim is supported or contradicted.

IMPORTANT INSTRUCTIONS:
- Do not use outside knowledge. Treat the reference evidence as the sole source of truth.
- Do not confuse missing evidence with contradictory evidence.
- Recognize valid paraphrases and double negations (e.g. "not harmful" matches "safe").
- Return a concise, claim-specific 1-2 sentence explanation citing the evidence.

Return ONLY a valid JSON object matching this schema:
{{
  "verdict": "SUPPORTED" | "CONTRADICTED" | "INSUFFICIENT_EVIDENCE",
  "confidence": float between 0.0 and 1.0,
  "explanation": "concise evidence-based justification"
}}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        raw_text = response.text.strip()
        # Clean potential markdown fences (```json ... ```)
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1]
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]
            raw_text = raw_text.strip()

        data = json.loads(raw_text)
        verdict_str = data.get("verdict", "INSUFFICIENT_EVIDENCE")
        verdict = VerdictEnum(verdict_str) if verdict_str in VerdictEnum.__members__ else VerdictEnum.INSUFFICIENT_EVIDENCE
        confidence = float(data.get("confidence", 0.85))
        explanation = str(data.get("explanation", "Verified against reference evidence passages."))

        return verdict, confidence, explanation

