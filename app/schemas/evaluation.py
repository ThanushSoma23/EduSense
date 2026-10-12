from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class EvaluationCreate(BaseModel):
    answer_id: int
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    concept_coverage: Optional[float] = Field(None, ge=0.0, le=1.0)
    suggested_marks: float = Field(..., ge=0.0)
    feedback: Optional[str] = None
    supporting_references: Optional[str] = None
    evaluation_status: str = "COMPLETED"


class EvaluationUpdate(BaseModel):
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    concept_coverage: Optional[float] = Field(None, ge=0.0, le=1.0)
    suggested_marks: Optional[float] = Field(None, ge=0.0)
    feedback: Optional[str] = None
    supporting_references: Optional[str] = None
    evaluation_status: Optional[str] = None


class EvaluationResponse(BaseModel):
    id: int
    answer_id: int
    similarity_score: Optional[float] = None
    concept_coverage: Optional[float] = None
    suggested_marks: float
    feedback: Optional[str] = None
    supporting_references: Optional[str] = None
    evaluation_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
