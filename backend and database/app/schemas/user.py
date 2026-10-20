from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, ConfigDict, Field, model_validator
from app.models.user import UserRole


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.STUDENT


class TeacherRegisterSchema(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    college_id: Optional[str] = None
    access_code: Optional[str] = None
    subjects: Optional[List[Any]] = None


class StudentRegisterSchema(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    roll_number: Optional[str] = None
    college_id: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=12)
    section: Optional[int] = Field(None, ge=1, le=4)


class AcademicProfileUpdate(BaseModel):
    semester: int = Field(..., ge=1, le=12, description="Student academic semester (1-8)")
    section: int = Field(..., ge=1, le=4, description="Student academic section (1-4)")
    department: Optional[str] = Field(None, max_length=100)
    roll_number: Optional[str] = Field(None, max_length=50)


class TeacherProvisioningRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    admin_key: str


class UserLogin(BaseModel):
    email: Optional[str] = None
    roll_number: Optional[str] = None
    college_id: Optional[str] = None
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    full_name: Optional[str] = None
    email: EmailStr
    role: UserRole
    account_status: str
    status: Optional[str] = None
    roll_number: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_alias_fields(self):
        if not self.full_name:
            self.full_name = self.name
        if not self.status:
            self.status = self.account_status
        return self


class Token(BaseModel):
    access_token: str
    token: Optional[str] = None
    token_type: str = "bearer"
    user: UserResponse

    @model_validator(mode="after")
    def populate_token_alias(self):
        if not self.token:
            self.token = self.access_token
        return self


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None
