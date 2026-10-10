from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class VerdictEnum(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class DocumentInput(BaseModel):
    filename: str
    content: str
    content_type: Optional[str] = "text/plain"  # "text/plain" or "application/pdf" (base64)

class AuditOptions(BaseModel):
    enable_web_search: bool = False
    force_deterministic_fallback: bool = False
    top_k_passages: int = 3
    similarity_threshold: float = 0.25

class EvidenceItem(BaseModel):
    excerpt: str
    source_name: str
    page_number: Optional[int] = 1
    relevance_score: float
    match_type: str = "bm25_passage"  # "bm25_passage" or "web_search"

class ClaimFlags(BaseModel):
    is_ambiguous: bool = False
    source_disagreement: bool = False
    internal_contradiction: bool = False

class ClaimItem(BaseModel):
    claim_id: str
    text: str
    start_char: int
    end_char: int
    verdict: VerdictEnum
    confidence: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    evidence: List[EvidenceItem] = []
    flags: ClaimFlags = Field(default_factory=ClaimFlags)

class SummaryMetrics(BaseModel):
    total_claims: int
    supported_count: int
    contradicted_count: int
    insufficient_evidence_count: int
    credibility_score: float = Field(..., ge=0.0, le=100.0)
    credibility_breakdown: Optional[Dict[str, Any]] = None
    internal_contradictions_detected: int = 0
    sources_analyzed: int = 0

class AuditRequest(BaseModel):
    answer_text: str
    documents: List[DocumentInput] = []
    options: AuditOptions = Field(default_factory=AuditOptions)
    api_key: Optional[str] = None  # Optional user-provided Gemini key

class AuditResponse(BaseModel):
    audit_id: str
    timestamp: str
    summary: SummaryMetrics
    claims: List[ClaimItem]
    original_answer: str
