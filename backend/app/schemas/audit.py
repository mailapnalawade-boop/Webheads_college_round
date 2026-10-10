from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class VerdictEnum(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LOGICAL_INCONSISTENCY = "LOGICAL_INCONSISTENCY"

class DocumentInput(BaseModel):
    filename: str
    content: str
    content_type: Optional[str] = "text/plain"  # "text/plain" or "application/pdf" (base64)

class AuditOptions(BaseModel):
    enable_web_search: bool = False
    force_deterministic_fallback: bool = False
    verification_mode: Optional[str] = "auto"  # "llm", "offline", or "auto"
    top_k_passages: int = 3
    similarity_threshold: float = 0.25

class EvidenceItem(BaseModel):
    excerpt: str
    source_name: str
    page_number: Optional[int] = 1
    relevance_score: float
    match_type: str = "bm25_passage"  # "bm25_passage" or "web_search"
    is_contradictory: bool = False
    is_external: bool = False

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
    uncertainty_level: str = "Low"  # "Low", "Moderate", "High"
    explanation: str
    evidence: List[EvidenceItem] = []
    supporting_evidence: List[EvidenceItem] = []
    contradicting_evidence: List[EvidenceItem] = []
    source_references: List[str] = []
    inconsistency_details: Optional[str] = None
    safety_details: Optional[str] = None
    flags: ClaimFlags = Field(default_factory=ClaimFlags)

class UnsafeRecommendation(BaseModel):
    recommendation_id: str
    text: str
    reason: str
    potential_risk: str
    severity: str = "Moderate"  # "Low", "Moderate", "High", "Critical"
    safer_alternative: Optional[str] = None
    relevant_limitations: Optional[str] = None
    evidence_excerpt: Optional[str] = None

class SafetyAnalysisResult(BaseModel):
    flagged_count: int = 0
    recommendations: List[UnsafeRecommendation] = []
    summary: str = "No potentially unsafe recommendations were flagged by the automated audit against the provided evidence."

class LogicalInconsistencyItem(BaseModel):
    conflict_id: str
    claim_id_1: str
    claim_id_2: Optional[str] = None
    claim_text_1: str
    claim_text_2: Optional[str] = None
    inconsistency_type: str = "mutual_contradiction"  # "mutual_contradiction" or "non_sequitur"
    explanation: str

class SummaryMetrics(BaseModel):
    total_claims: int
    supported_count: int
    contradicted_count: int
    insufficient_evidence_count: int
    logical_inconsistency_count: int = 0
    unsafe_recommendations_count: int = 0
    credibility_score: float = Field(..., ge=0.0, le=100.0)
    credibility_breakdown: Optional[Dict[str, Any]] = None
    internal_contradictions_detected: int = 0
    sources_analyzed: int = 0

class AuditRequest(BaseModel):
    answer_text: str
    documents: List[DocumentInput] = []
    options: AuditOptions = Field(default_factory=AuditOptions)
    api_key: Optional[str] = None  # Optional user-provided override, backend env preferred

class AuditResponse(BaseModel):
    audit_id: str
    timestamp: str
    verification_mode: str = "offline_deterministic"  # "llm_api" or "offline_deterministic"
    model_info: str = "Deterministic Rule & BM25 Engine"
    cached: bool = False
    audit_configuration: Optional[Dict[str, Any]] = None
    limitations: str = "Automated audit based strictly on provided documents. Confidence scores reflect internal model certainty, not calibrated probabilities of truth."
    summary: SummaryMetrics
    claims: List[ClaimItem]
    logical_inconsistencies: List[LogicalInconsistencyItem] = []
    safety_analysis: SafetyAnalysisResult = Field(default_factory=SafetyAnalysisResult)
    original_answer: str
