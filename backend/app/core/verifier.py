import json
import uuid
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

class AuditEngine:
    """
    Main Verification Orchestrator for Second Opinion.
    Integrates Extraction, Retrieval, Gemini 2.5 Flash Verification, and Deterministic Fallback.
    """

    @staticmethod
    def run_audit(request: AuditRequest) -> AuditResponse:
        audit_id = f"audit_{uuid.uuid4().hex[:8]}"
        
        # 1. Extract Atomic Claims
        extracted_claims = ClaimExtractor.extract_claims(request.answer_text)
        
        # 2. Ingest Documents into Passages
        parsed_passages = DocumentParser.parse_documents(request.documents)
        retriever = PassageRetriever(parsed_passages)

        # 3. Detect Internal Contradictions between claims
        internal_conflicts = DeterministicVerifier.detect_internal_contradictions(extracted_claims)
        conflicting_claim_ids = set()
        for conflict in internal_conflicts:
            conflicting_claim_ids.add(conflict["claim_id_1"])
            conflicting_claim_ids.add(conflict["claim_id_2"])

        # Determine if live Gemini API key is available
        api_key = request.api_key or settings.GEMINI_API_KEY
        use_live_api = bool(api_key) and not request.options.force_deterministic_fallback

        verified_claims = []
        supported_count = 0
        contradicted_count = 0
        insufficient_count = 0

        for claim in extracted_claims:
            claim_id = claim["claim_id"]
            claim_text = claim["text"]
            start_char = claim["start_char"]
            end_char = claim["end_char"]

            # Retrieve top matching passages
            evidence_matches = retriever.retrieve(claim_text, top_k=request.options.top_k_passages)

            verdict = VerdictEnum.INSUFFICIENT_EVIDENCE
            confidence = 0.50
            explanation = ""

            # Try Live Gemini Verification if key exists
            if use_live_api and evidence_matches:
                try:
                    verdict, confidence, explanation = AuditEngine._verify_with_gemini(
                        claim_text=claim_text,
                        evidence_matches=evidence_matches,
                        api_key=api_key
                    )
                except Exception as e:
                    # Seamless Fallback to Deterministic Verifier on API error
                    verdict, confidence, explanation = DeterministicVerifier.verify_claim(
                        claim_text, evidence_matches
                    )
            else:
                # Deterministic Rule Verification
                verdict, confidence, explanation = DeterministicVerifier.verify_claim(
                    claim_text, evidence_matches
                )

            # Update Metrics Counter
            if verdict == VerdictEnum.SUPPORTED:
                supported_count += 1
            elif verdict == VerdictEnum.CONTRADICTED:
                contradicted_count += 1
            else:
                insufficient_count += 1

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

            verified_claims.append(ClaimItem(
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
            ))

        total_claims = len(verified_claims)
        credibility_score = round(
            (supported_count / total_claims * 100.0) if total_claims > 0 else 0.0, 1
        )

        summary = SummaryMetrics(
            total_claims=total_claims,
            supported_count=supported_count,
            contradicted_count=contradicted_count,
            insufficient_evidence_count=insufficient_count,
            credibility_score=credibility_score,
            internal_contradictions_detected=len(internal_conflicts),
            sources_analyzed=len(request.documents)
        )

        return AuditResponse(
            audit_id=audit_id,
            timestamp=types.datetime.datetime.now(types.datetime.timezone.utc).isoformat() if hasattr(types, 'datetime') else "2026-10-10T15:25:04Z",
            summary=summary,
            claims=verified_claims,
            original_answer=request.answer_text
        )

    @staticmethod
    def _verify_with_gemini(claim_text: str, evidence_matches: List[Dict[str, Any]], api_key: str) -> tuple:
        client = genai.Client(api_key=api_key)
        
        evidence_str = "\n".join([f"- [{e['source_name']} (Page {e.get('page_number', 1)})]: {e['excerpt']}" for e in evidence_matches])
        
        prompt = f"""You are an expert AI Answer Auditor. Verify the following CLAIM against the provided EVIDENCE passages.

CLAIM: "{claim_text}"

EVIDENCE PASSAGES:
{evidence_str}

Analyze whether the evidence SUPPORTS, CONTRADICTS, or provides INSUFFICIENT_EVIDENCE for the claim.
Return strictly a valid JSON object with key names:
"verdict": "SUPPORTED" or "CONTRADICTED" or "INSUFFICIENT_EVIDENCE",
"confidence": float between 0.0 and 1.0,
"explanation": a concise 1-2 sentence evidence-based justification.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        data = json.loads(response.text)
        verdict_str = data.get("verdict", "INSUFFICIENT_EVIDENCE")
        verdict = VerdictEnum(verdict_str) if verdict_str in VerdictEnum.__members__ else VerdictEnum.INSUFFICIENT_EVIDENCE
        confidence = float(data.get("confidence", 0.85))
        explanation = str(data.get("explanation", "Verified via Gemini audit engine."))

        return verdict, confidence, explanation
