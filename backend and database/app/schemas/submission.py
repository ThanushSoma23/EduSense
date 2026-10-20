from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class AnswerSheetCreate(BaseModel):
    exam_id: int
    student_id: Optional[int] = None  # If null, inferred from authenticated student token
    file_reference: str = Field(..., min_length=1, description="URL or S3 file reference of scanned answer sheet")


class AnswerSheetUpdate(BaseModel):
    processing_status: Optional[str] = None  # PENDING, EXTRACTED, EVALUATED, REVIEWED, FAILED


class StudentAnswerCreate(BaseModel):
    submission_id: int
    question_id: int
    extracted_text: Optional[str] = None
    ocr_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_status: Optional[str] = "SUCCESS"


class StudentAnswerResponse(BaseModel):
    id: int
    submission_id: int
    question_id: int
    extracted_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    extraction_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnswerSheetResponse(BaseModel):
    id: int
    student_id: int
    exam_id: int
    file_reference: str
    submission_time: datetime
    processing_status: str
    created_at: datetime
    updated_at: datetime
    answers: List[StudentAnswerResponse] = []

    model_config = ConfigDict(from_attributes=True)


class TranscribedAnswerItem(BaseModel):
    question_number: int
    question_id: Optional[int] = None
    extracted_text: str
    ocr_confidence: float
    needs_review: bool
    extraction_status: str


class TranscribeSubmissionResponse(BaseModel):
    submission_id: int
    processing_status: str
    total_questions: int
    answers: List[TranscribedAnswerItem]
    overall_confidence: float
    needs_review: bool
    backend_used: str
