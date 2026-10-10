"""Audit orchestration. Each stage lives in its own module; this file only wires them together.

Pipeline: extract claims -> retrieve evidence (BM25 + embeddings) -> judge meaning (NLI + entity checks,
cross-checked by Gemini when enabled) -> internal consistency -> safety -> report.
"""
import hashlib
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from app.config import settings
from app.core import consistency
from app.core.cache import LRUCache
from app.core.extractor import ClaimExtractor
from app.core.judge import ClaimSpan, Judgement, SemanticJudge
from app.core.llm_errors import classify_llm_error
from app.core.llm_verifier import GeminiVerifier, LLMVerdict, coerce_llm_result, merge_with_local
from app.core.model_registry import registry
from app.core.parser import DocumentParser
from app.core.retriever import PassageRetriever
from app.core.safety import SafetyAnalyzer
from app.schemas.audit import (AuditRequest, AuditResponse, ClaimFlags, ClaimItem, ErrorCategory, ErrorSpan,
                               EvidenceItem, LogicalInconsistencyItem, SafetyAnalysisResult, SummaryMetrics,
                               VerdictEnum)

logger = logging.getLogger("second_opinion.verifier")

PROMPT_VERSION = "2026.10.1"
NO_NLI_WARNING = ("Semantic (NLI) model not loaded: offline verdicts are limited to verified value mismatches, "
                  "polarity flips and near-verbatim matches; everything else is reported as Ambiguous rather than guessed. "
                  "Install sentence-transformers and allow the one-time model download for meaning-based checking.")


@dataclass
class RunMode:
    use_llm: bool
    explicit_llm: bool
    api_key: str
    model_name: str

    @property
    def active_mode(self) -> str:
        return "llm_api" if self.use_llm else "offline_deterministic"


class AuditEngine:
    cache: LRUCache = LRUCache(settings.AUDIT_CACHE_SIZE)

    # ---------------------------------------------------------- error helpers
    @staticmethod
    def _classify_llm_error(err: Exception, model_name: str, stage: str) -> Tuple[int, str]:
        return classify_llm_error(err, model_name, stage)

    @staticmethod
    def _format_llm_error(err: Exception, model_name: str, stage: str) -> str:
        return classify_llm_error(err, model_name, stage)[1]

    @staticmethod
    def _raise_llm_error(err: Exception, mode: RunMode, stage: str) -> None:
        status_code, detail = classify_llm_error(err, mode.model_name, stage)
        raise HTTPException(status_code=status_code, detail=detail)

    # ------------------------------------------------------------------ main
    @staticmethod
    def run_audit(request: AuditRequest) -> AuditResponse:
        audit_id = f"audit_{uuid.uuid4().hex[:8]}"
        mode = AuditEngine._resolve_mode(request)
        cache_key = AuditEngine._compute_cache_key(request, mode.active_mode, mode.model_name)
        cached = AuditEngine.cache.get(cache_key)
        if cached is not None:
            return AuditEngine._as_cached(cached, audit_id)

        claims = AuditEngine._extract_claims(request, mode)
        passages = DocumentParser.parse_documents(request.documents)
        retriever = PassageRetriever(passages, embedder=registry.embedder)
        judge = SemanticJudge(registry.nli, registry.embedder)
        inconsistencies = AuditEngine._detect_logical_inconsistencies(claims, mode.use_llm, mode.api_key, mode.model_name)
        conflicted = {cid for li in inconsistencies for cid in (li.claim_id_1, li.claim_id_2) if cid}

        verified = [AuditEngine._audit_claim(c, request, retriever, judge, mode, inconsistencies, conflicted)
                    for c in claims]
        verified.sort(key=lambda c: (c.start_char, c.claim_id))
        safety = AuditEngine._analyze_safety(request, verified, passages, mode)
        response = AuditEngine._assemble(audit_id, request, mode, verified, inconsistencies, safety)
        AuditEngine.cache.put(cache_key, response)
        logger.info("Audit %s done. Score %s%%, claims %s, mode %s", audit_id, response.summary.credibility_score,
                    len(verified), mode.active_mode)
        return response

    # ------------------------------------------------------------ mode/cache
    @staticmethod
    def _resolve_mode(request: AuditRequest) -> RunMode:
        opts = request.options
        force_offline = opts.force_deterministic_fallback or opts.verification_mode == "offline"
        api_key = (request.api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
                   or os.getenv("GOOGLE_API_KEY") or "").strip().strip('"').strip("'")
        explicit = opts.verification_mode == "llm"
        if explicit and not api_key:
            raise HTTPException(status_code=400, detail=(
                "GEMINI_API_KEY is not configured on the backend environment. Please set GEMINI_API_KEY in the "
                "server environment or switch to Offline Deterministic Mode in Advanced Settings."))
        use_llm = not force_offline and bool(api_key)
        return RunMode(use_llm, explicit, api_key, settings.DEFAULT_MODEL if use_llm else AuditEngine._offline_model_name())

    @staticmethod
    def _offline_model_name() -> str:
        nli = getattr(registry.nli, "name", None)
        return f"Semantic NLI + Entity Engine ({nli})" if nli else "Entity & Lexical Engine (NLI model not loaded)"

    @staticmethod
    def _compute_cache_key(request: AuditRequest, mode: str, model_name: str) -> str:
        norm_answer = " ".join(request.answer_text.strip().split())
        docs = "|".join(
            f"{d.filename}:{hashlib.sha256((d.content or '').encode('utf-8')).hexdigest()[:12]}:{d.content_type}"
            for d in sorted(request.documents, key=lambda x: x.filename or ""))
        o = request.options
        sig = f"{mode}:{model_name}:{o.enable_web_search}:{o.top_k_passages}:{o.similarity_threshold}:{PROMPT_VERSION}"
        return hashlib.sha256(f"{norm_answer}###{docs}###{sig}".encode("utf-8")).hexdigest()

    @staticmethod
    def _as_cached(cached: AuditResponse, audit_id: str) -> AuditResponse:
        copy = cached.model_copy(deep=True)
        copy.audit_id, copy.cached = audit_id, True
        copy.timestamp = datetime.now(timezone.utc).isoformat()
        return copy

    # ------------------------------------------------------------ extraction
    @staticmethod
    def _extract_claims(request: AuditRequest, mode: RunMode) -> List[Dict[str, Any]]:
        if not mode.use_llm:
            return ClaimExtractor.extract_claims(request.answer_text)
        try:
            return ClaimExtractor.extract_claims_with_llm(request.answer_text, api_key=mode.api_key,
                                                          model_name=mode.model_name)
        except Exception as err:
            logger.error("LLM claim extraction failed: %s - %s", type(err).__name__, err)
            if mode.explicit_llm:
                AuditEngine._raise_llm_error(err, mode, "claim extraction")
            mode.use_llm, mode.model_name = False, AuditEngine._offline_model_name() + " (LLM failover)"
            return ClaimExtractor.extract_claims(request.answer_text)

    # ----------------------------------------------------------- per claim
    @staticmethod
    def _audit_claim(claim: Dict[str, Any], request: AuditRequest, retriever: PassageRetriever, judge: SemanticJudge,
                     mode: RunMode, inconsistencies: List[LogicalInconsistencyItem], conflicted: set) -> ClaimItem:
        text = claim["text"]
        evidence = AuditEngine._gather_evidence(text, request, retriever)
        judgement = AuditEngine._judge_claim(text, evidence, judge, mode)
        inconsistent = claim["claim_id"] in conflicted
        verdict = AuditEngine._primary_verdict(judgement.verdict, inconsistent)
        supporting, contradicting, reported = AuditEngine._split_evidence(evidence, judgement, verdict)
        notes = [li.explanation for li in inconsistencies if claim["claim_id"] in (li.claim_id_1, li.claim_id_2)]
        category = (ErrorCategory.INTERNAL_CONTRADICTION if verdict == VerdictEnum.LOGICAL_INCONSISTENCY
                    else judgement.category)
        confidence = judgement.confidence
        level = "Low" if confidence >= 0.85 else "Moderate" if confidence >= 0.60 else "High"
        return ClaimItem(
            claim_id=claim["claim_id"], text=text, start_char=claim["start_char"], end_char=claim["end_char"],
            verdict=verdict, confidence=confidence, uncertainty_level=level, explanation=judgement.explanation,
            evidence=reported, supporting_evidence=supporting, contradicting_evidence=contradicting,
            source_references=list(dict.fromkeys(e.source_name for e in reported)),
            inconsistency_details="; ".join(notes) if inconsistent and notes else (
                "Contradicts another statement in the answer." if inconsistent else None),
            error_category=category, error_span=AuditEngine._answer_span(judgement.span, claim, request.answer_text),
            confidence_signals=judgement.signals,
            flags=ClaimFlags(is_ambiguous=verdict == VerdictEnum.AMBIGUOUS,
                             source_disagreement=judgement.source_disagreement, internal_contradiction=inconsistent))

    @staticmethod
    def _gather_evidence(text: str, request: AuditRequest, retriever: PassageRetriever) -> List[Dict[str, Any]]:
        matches = retriever.retrieve(text, top_k=request.options.top_k_passages)
        if request.options.enable_web_search and (not matches or matches[0]["relevance_score"] < 0.35):
            matches = (matches or []) + PassageRetriever.search_web(text, max_results=2)
        matches.sort(key=lambda m: (m["relevance_score"], m["source_name"]), reverse=True)
        return matches

    @staticmethod
    def _judge_claim(text: str, evidence: List[Dict[str, Any]], judge: SemanticJudge, mode: RunMode) -> Judgement:
        local = judge.judge(text, evidence)
        if not mode.use_llm:
            return local
        try:
            raw = AuditEngine._verify_with_gemini(claim_text=text, evidence_matches=evidence,
                                                  api_key=mode.api_key, model_name=mode.model_name)
        except Exception as err:
            logger.error("Gemini verification failed: %s - %s", type(err).__name__, err)
            if mode.explicit_llm:
                AuditEngine._raise_llm_error(err, mode, f"claim verification ('{text[:40]}...')")
            return local
        top = max((float(e.get("relevance_score", 0.0)) for e in evidence), default=0.0)
        return merge_with_local(local, coerce_llm_result(raw), text, top)

    @staticmethod
    def _verify_with_gemini(claim_text: str, evidence_matches: List[Dict[str, Any]], api_key: str,
                            model_name: Optional[str] = None) -> LLMVerdict:
        """Iterates as (verdict, confidence_hint, explanation, supporting, contradicting, source_disagreement)."""
        return GeminiVerifier.verify(claim_text, evidence_matches, api_key, model_name)

    @staticmethod
    def _primary_verdict(verdict: VerdictEnum, inconsistent: bool) -> VerdictEnum:
        if verdict == VerdictEnum.CONTRADICTED:
            return verdict
        if inconsistent:
            return VerdictEnum.LOGICAL_INCONSISTENCY
        return verdict if verdict in (VerdictEnum.SUPPORTED, VerdictEnum.AMBIGUOUS) else VerdictEnum.INSUFFICIENT_EVIDENCE

    @staticmethod
    def _split_evidence(matches: List[Dict[str, Any]], j: Judgement, verdict: VerdictEnum):
        sup_idx, con_idx = set(j.supporting_idx), set(j.contradicting_idx)
        if verdict == VerdictEnum.CONTRADICTED and not con_idx and not sup_idx and matches:
            con_idx = {0}
        if verdict == VerdictEnum.SUPPORTED and not sup_idx and not con_idx and matches:
            sup_idx = {0}
        items = [EvidenceItem(excerpt=m["excerpt"], source_name=m["source_name"], page_number=m.get("page_number", 1),
                              relevance_score=m["relevance_score"], match_type=m["match_type"],
                              is_contradictory=i in con_idx, is_external=m["match_type"] == "web_search")
                 for i, m in enumerate(matches)]
        supporting = [e for i, e in enumerate(items) if i in sup_idx and i not in con_idx]
        contradicting = [e for i, e in enumerate(items) if i in con_idx]
        return supporting, contradicting, (supporting + contradicting) or items

    @staticmethod
    def _answer_span(span: Optional[ClaimSpan], claim: Dict[str, Any], answer: str) -> Optional[ErrorSpan]:
        """Map a claim-relative span onto the original answer, verifying answer[start:end] == text."""
        if span is None:
            return None
        region_start = claim["start_char"]
        offset = answer[region_start:claim["end_char"]].find(span.text)
        if offset < 0:
            return None
        start = region_start + offset
        return ErrorSpan(start_char=start, end_char=start + len(span.text), text=answer[start:start + len(span.text)],
                         precision=span.precision)

    # ----------------------------------------------------------- consistency
    @staticmethod
    def _detect_logical_inconsistencies(extracted_claims: List[Dict[str, Any]], use_llm: bool, api_key: str = "",
                                        model_name: Optional[str] = None) -> List[LogicalInconsistencyItem]:
        """Local value/polarity/NLI checks always run; the LLM adds reasoning-level checks when enabled."""
        local = consistency.find_local_conflicts(extracted_claims, registry.nli)
        items = consistency.to_items(local, extracted_claims)
        if use_llm and len(extracted_claims) >= 2:
            try:
                seen = {tuple(sorted((i.claim_id_1, i.claim_id_2))) for i in items}
                extra = [c for c in consistency.find_llm_conflicts(extracted_claims, api_key, model_name)
                         if tuple(sorted((c.get("claim_id_1", ""), c.get("claim_id_2", "")))) not in seen]
                items += consistency.to_items(extra, extracted_claims, start_index=len(items))
            except Exception as err:
                logger.warning("LLM logical inconsistency check skipped on error: %s", err)
        return items

    # ----------------------------------------------------------------- safety
    @staticmethod
    def _analyze_safety(request: AuditRequest, claims: List[ClaimItem], passages, mode: RunMode) -> SafetyAnalysisResult:
        dumped = [c.model_dump() for c in claims]
        if not mode.use_llm:
            return SafetyAnalyzer.analyze_deterministic(answer_text=request.answer_text, claims=dumped, passages=passages)
        try:
            return SafetyAnalyzer.analyze_with_llm(answer_text=request.answer_text, claims=dumped, passages=passages,
                                                   api_key=mode.api_key, model_name=mode.model_name, raise_on_error=True)
        except Exception as err:
            logger.error("LLM safety analysis failed: %s", type(err).__name__)
            AuditEngine._raise_llm_error(err, mode, "safety analysis")

    # ---------------------------------------------------------------- report
    @staticmethod
    def calculate_credibility(supported_count: int, insufficient_count: int, contradicted_count: int,
                              total_claims: int, inconsistent_count: int = 0, ambiguous_count: int = 0
                              ) -> Tuple[float, Dict[str, Any]]:
        """Supported = 1 point; unverified or ambiguous = 0.5 (neutral); contradicted/inconsistent = 0."""
        neutral = insufficient_count + ambiguous_count
        score = round(((supported_count + 0.5 * neutral) / total_claims) * 100.0, 1) if total_claims else 100.0
        return score, {
            "formula": "(Supported + 0.5 * (Insufficient + Ambiguous)) / Total * 100",
            "supported_claims": supported_count, "insufficient_evidence_claims": insufficient_count,
            "ambiguous_claims": ambiguous_count, "contradicted_claims": contradicted_count,
            "logical_inconsistency_claims": inconsistent_count, "total_claims": total_claims,
            "supported_points": float(supported_count), "insufficient_points": float(0.5 * insufficient_count),
            "ambiguous_points": float(0.5 * ambiguous_count),
            "penalized_points": float(contradicted_count + inconsistent_count)}

    @staticmethod
    def _assemble(audit_id: str, request: AuditRequest, mode: RunMode, claims: List[ClaimItem],
                  inconsistencies: List[LogicalInconsistencyItem], safety: SafetyAnalysisResult) -> AuditResponse:
        count = lambda v: sum(1 for c in claims if c.verdict == v)  # noqa: E731
        score, breakdown = AuditEngine.calculate_credibility(
            count(VerdictEnum.SUPPORTED), count(VerdictEnum.INSUFFICIENT_EVIDENCE), count(VerdictEnum.CONTRADICTED),
            len(claims), count(VerdictEnum.LOGICAL_INCONSISTENCY), count(VerdictEnum.AMBIGUOUS))
        summary = SummaryMetrics(
            total_claims=len(claims), supported_count=count(VerdictEnum.SUPPORTED),
            contradicted_count=count(VerdictEnum.CONTRADICTED),
            insufficient_evidence_count=count(VerdictEnum.INSUFFICIENT_EVIDENCE),
            ambiguous_count=count(VerdictEnum.AMBIGUOUS), logical_inconsistency_count=count(VerdictEnum.LOGICAL_INCONSISTENCY),
            unsafe_recommendations_count=safety.flagged_count, credibility_score=score, credibility_breakdown=breakdown,
            internal_contradictions_detected=len(inconsistencies), sources_analyzed=len(request.documents))
        opts = request.options
        warnings = [] if (mode.use_llm or registry.nli) else [NO_NLI_WARNING]
        return AuditResponse(
            audit_id=audit_id, timestamp=datetime.now(timezone.utc).isoformat(), verification_mode=mode.active_mode,
            model_info=mode.model_name, cached=False, warnings=warnings,
            audit_configuration={
                "verification_mode": mode.active_mode, "model_name": mode.model_name,
                "deterministic_temperature": 0.0 if mode.use_llm else None, "top_k_passages": opts.top_k_passages,
                "similarity_threshold": opts.similarity_threshold, "enable_web_search": opts.enable_web_search,
                "sources_analyzed_count": len(request.documents), **registry.describe()},
            limitations=("Automated audit evaluated strictly against supplied reference documents. Confidence is computed "
                         "from verification signals (meaning-model probability, verified value checks, evidence quality); "
                         "it is not a calibrated probability of ground truth."),
            summary=summary, claims=claims, logical_inconsistencies=inconsistencies, safety_analysis=safety,
            original_answer=request.answer_text)
