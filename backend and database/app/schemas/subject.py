from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SubjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Full subject / course name")
    code: Optional[str] = Field(None, max_length=50, description="Course code, e.g. CSE311, CS-301")
    department: Optional[str] = Field("Computer Science & Engineering", max_length=100)
    default_semester: Optional[int] = Field(None, ge=1, le=12, description="Target academic semester")


class SubjectCreate(SubjectBase):
    pass


class SubjectResponse(SubjectBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
