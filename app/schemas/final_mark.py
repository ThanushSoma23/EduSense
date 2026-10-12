from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class TeacherReviewRequest(BaseModel):
    answer_id: int
    approved_marks: float = Field(..., ge=0.0, description="Final teacher-approved marks")
    approval_status: str = Field("APPROVED", description="APPROVED, MODIFIED, or REJECTED")
    reason: Optional[str] = Field(None, description="Reason for teacher modification or approval comments")


class BatchTeacherReviewRequest(BaseModel):
    reviews: List[TeacherReviewRequest]


class FinalMarkResponse(BaseModel):
    id: int
    answer_id: int
    approved_marks: float
    reviewing_teacher_id: int
    approval_status: str
    approval_timestamp: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentQuestionResult(BaseModel):
    question_id: int
    question_number: int
    question_text: str
    max_marks: float
    extracted_text: Optional[str] = None
    ai_suggested_marks: Optional[float] = None
    ai_feedback: Optional[str] = None
    final_approved_marks: Optional[float] = None
    approval_status: Optional[str] = None
    reviewing_teacher_id: Optional[int] = None
    reviewing_teacher_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StudentExamResultResponse(BaseModel):
    submission_id: int
    exam_id: int
    exam_title: str
    subject: str
    student_id: int
    student_name: str
    submission_time: datetime
    processing_status: str
    total_max_marks: float
    total_final_marks: Optional[float] = None
    is_published: bool = False
    questions: List[StudentQuestionResult] = []

    model_config = ConfigDict(from_attributes=True)
