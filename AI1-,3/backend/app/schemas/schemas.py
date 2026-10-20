from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr

class SubjectSelection(BaseModel):
    subject: str
    semester: int

class TeacherRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    college_id: str
    access_code: str
    subjects: List[SubjectSelection] = []

class StudentRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    roll_number: str
    college_id: str
    department: str
    semester: int

class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    roll_number: Optional[str] = None
    college_id: Optional[str] = None
    password: str

class TranscriptUpdate(BaseModel):
    text: str

class AdminApproveTeacherRequest(BaseModel):
    teacher_id: str
    action: str  # 'approve' or 'reject'

class AppealCreate(BaseModel):
    answer_id: str
    student_reason: str

class QuestionCreate(BaseModel):
    number: int
    text: str
    max_marks: float
    model_answer: str
    concepts: List[Dict[str, Any]] = []

class ExamCreate(BaseModel):
    title: str
    subject: str
    code: str
    questions: List[QuestionCreate] = []

class AwardMarksRequest(BaseModel):
    final_marks: float
    award_source: str
    remarks: Optional[str] = None
