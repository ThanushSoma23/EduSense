import json
from datetime import datetime
from typing import Optional, List, Any, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator


class QuestionCreate(BaseModel):
    question_number: Optional[int] = Field(None, gt=0, description="1-indexed question number within the exam")
    number: Optional[int] = Field(None, gt=0)
    question_text: Optional[str] = None
    text: Optional[str] = None
    model_answer: str = Field(..., min_length=1)
    max_marks: float = Field(..., gt=0, description="Maximum achievable marks for this question")
    rubric: Optional[Union[str, List[Any]]] = None
    concepts: Optional[List[Any]] = None
    image_url: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any):
        if isinstance(data, dict):
            # Normalize question_number from number
            if not data.get("question_number") and data.get("number"):
                data["question_number"] = data["number"]
            # Normalize question_text from text
            if not data.get("question_text") and data.get("text"):
                data["question_text"] = data["text"]
            # Normalize rubric from concepts array
            if not data.get("rubric") and data.get("concepts"):
                concepts = data["concepts"]
                if isinstance(concepts, list):
                    labels = [c.get("label", str(c)) if isinstance(c, dict) else str(c) for c in concepts]
                    data["rubric"] = json.dumps(labels)
            elif isinstance(data.get("rubric"), list):
                data["rubric"] = json.dumps(data["rubric"])
        return data

    @model_validator(mode="after")
    def validate_required_fields(self):
        if not self.question_number:
            raise ValueError("question_number or number is required")
        if not self.question_text:
            raise ValueError("question_text or text is required")
        if isinstance(self.rubric, list):
            self.rubric = json.dumps(self.rubric)
        return self


class QuestionUpdate(BaseModel):
    question_number: Optional[int] = Field(None, gt=0)
    question_text: Optional[str] = None
    model_answer: Optional[str] = None
    max_marks: Optional[float] = Field(None, gt=0)
    rubric: Optional[str] = None
    image_url: Optional[str] = None


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
    code: Optional[str] = None
    semester: int = Field(..., ge=1, le=12, description="Target academic semester (1 to 8)")
    section: int = Field(..., ge=1, le=4, description="Target section (1, 2, 3, or 4)")
    questions: Optional[List[QuestionCreate]] = None


class ExamUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    code: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=12)
    section: Optional[int] = Field(None, ge=1, le=4)
    status: Optional[str] = None  # DRAFT, PUBLISHED, COMPLETED, ARCHIVED


class ExamResponse(BaseModel):
    id: int
    title: str
    subject: str
    teacher_id: int
    status: str
    code: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    questions: List[QuestionResponse] = []
    exam: Optional[Any] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_self_alias(self):
        if not self.exam:
            self.exam = {
                "id": self.id,
                "title": self.title,
                "subject": self.subject,
                "status": self.status,
                "semester": self.semester,
                "section": self.section,
                "code": self.code
            }
        return self


class AvailableExamResponse(BaseModel):
    id: int
    title: str
    subject: str
    code: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[int] = None
    teacher_name: str
    total_marks: float
    status: str
    is_enrolled: bool = False
    enrolled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

