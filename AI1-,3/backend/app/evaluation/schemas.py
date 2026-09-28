from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class Citation(BaseModel):
    source: str
    page: int
    excerpt: str

class ConceptVerdict(BaseModel):
    concept: str
    status: Literal["covered", "partial", "missing"]
    quote: Optional[str] = None
    justification: str
    weight: float = 1.0

class ConceptCoverageResponse(BaseModel):
    verdicts: List[ConceptVerdict] = Field(default_factory=list)
    rationale: str = ""

class EvaluationResult(BaseModel):
    similarity_pct: float
    covered: List[Dict[str, Any]] = Field(default_factory=list)
    partial: List[Dict[str, Any]] = Field(default_factory=list)
    missing: List[Dict[str, Any]] = Field(default_factory=list)
    keywords_missing: List[str] = Field(default_factory=list)
    ai_suggested_min: Optional[float] = None
    ai_suggested_max: Optional[float] = None

    ai_confidence: float
    rationale: str
    citations: List[Citation] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)
    prompt_version: str = "v1.0"
    model: str = "bge-small-en-v1.5"
    tokens: int = 0
    latency_ms: int = 0

class DocumentChunk(BaseModel):
    id: str
    text: str
    source: str
    page: int
    heading: str
    institution_id: str
    subject_id: str
    embedding: Optional[List[float]] = None
