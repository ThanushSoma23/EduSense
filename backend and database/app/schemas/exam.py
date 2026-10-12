from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class QuestionCreate(BaseModel):
    question_number: int = Field(..., gt=0, description="1-indexed question number within the exam")
    question_text: str = Field(..., min_length=1)
    model_answer: str = Field(..., min_length=1)
    max_marks: float = Field(..., gt=0, description="Maximum achievable marks for this question")
    rubric: Optional[str] = None


class QuestionUpdate(BaseModel):
    question_number: Optional[int] = Field(None, gt=0)
    question_text: Optional[str] = None
    model_answer: Optional[str] = None
    max_marks: Optional[float] = Field(None, gt=0)
    rubric: Optional[str] = None


class QuestionResponse(BaseModel):
    id: int
    exam_id: int
    question_number: int
    question_text: str
    model_answer: str
    max_marks: float
    rubric: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExamCreate(BaseModel):
    title: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    questions: Optional[List[QuestionCreate]] = None


class ExamUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    status: Optional[str] = None  # DRAFT, PUBLISHED, COMPLETED, ARCHIVED


class ExamResponse(BaseModel):
    id: int
    title: str
    subject: str
    teacher_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    questions: List[QuestionResponse] = []

    model_config = ConfigDict(from_attributes=True)
