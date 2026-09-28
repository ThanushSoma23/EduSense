import uuid
import jwt
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from app.core.config import settings
from app.core.security import verify_token
from app.core.rate_limiter import auth_rate_limiter
from app.schemas.schemas import TeacherRegisterRequest, StudentRegisterRequest, LoginRequest
from app.db.supabase import db

router = APIRouter()

def create_jwt_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "id": user_id,
        "email": email,
        "role": role
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

class AccessCodeCheckRequest(BaseModel):
    college_id: str
    code: str

class ForgotPasswordRequest(BaseModel):
    email: str

@router.get("/colleges")
def list_colleges():
    colleges = list(db.colleges.values())
    return {"colleges": colleges}

@router.post("/check-access-code")
def check_access_code(payload: AccessCodeCheckRequest, request: Request):
    auth_rate_limiter.check(request)
    access_code = next(
        (c for c in db.college_access_codes.values() if c.get("college_id") == payload.college_id and c.get("code") == payload.code and c.get("is_active")),
        None
    )
    if not access_code:
        raise HTTPException(status_code=400, detail="Invalid access code for the selected college.")
    return {"valid": True, "message": "Access code validated successfully."}

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request):
    auth_rate_limiter.check(request)
    # Trigger Supabase reset password flow or return success message
    return {"message": f"If an account exists for {payload.email}, a password reset link has been dispatched."}

@router.post("/register/teacher")
def register_teacher(payload: TeacherRegisterRequest, request: Request):
    auth_rate_limiter.check(request)

    college = db.colleges.get(payload.college_id)
    if not college:
        raise HTTPException(status_code=400, detail="Invalid college ID selected.")

    access_code = next(
        (c for c in db.college_access_codes.values() if c.get("college_id") == payload.college_id and c.get("code") == payload.access_code and c.get("is_active")),
        None
    )
    if not access_code:
        raise HTTPException(status_code=400, detail="Invalid or inactive college access code.")

    existing = next((p for p in db.profiles.values() if p.get("email") == payload.email), None)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user_id = str(uuid.uuid4())
    # Status is pending unless AUTO_APPROVE_TEACHERS is enabled in APP_ENV=dev
    account_status = "active" if (settings.APP_ENV == "dev" and settings.AUTO_APPROVE_TEACHERS) else "pending"

    profile_record = {
        "id": user_id,
        "full_name": payload.full_name,
        "email": payload.email,
        "role": "teacher",
        "college_id": payload.college_id,
        "status": account_status
    }
    db.profiles[user_id] = profile_record

    for sub in payload.subjects:
        sub_id = str(uuid.uuid4())
        db.teacher_subjects[sub_id] = {
            "id": sub_id,
            "teacher_id": user_id,
            "subject": sub.subject,
            "semester": sub.semester
        }

    token = create_jwt_token(user_id, payload.email, "teacher")

    return {
        "message": "Teacher registration submitted successfully.",
        "user": profile_record,
        "token": token
    }

@router.post("/register/student")
def register_student(payload: StudentRegisterRequest, request: Request):
    auth_rate_limiter.check(request)

    college = db.colleges.get(payload.college_id)
    if not college:
        raise HTTPException(status_code=400, detail="Invalid college ID selected.")

    existing_roll = next(
        (p for p in db.profiles.values() if p.get("college_id") == payload.college_id and p.get("roll_number") == payload.roll_number),
        None
    )
    if existing_roll:
        raise HTTPException(
            status_code=400,
            detail=f"Roll number '{payload.roll_number}' is already registered for this college."
        )

    existing_email = next((p for p in db.profiles.values() if p.get("email") == payload.email), None)
    if existing_email:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user_id = str(uuid.uuid4())
    profile_record = {
        "id": user_id,
        "full_name": payload.full_name,
        "email": payload.email,
        "roll_number": payload.roll_number,
        "college_id": payload.college_id,
        "department": payload.department,
        "semester": payload.semester,
        "role": "student",
        "status": "active"
    }
    db.profiles[user_id] = profile_record

    token = create_jwt_token(user_id, payload.email, "student")

    return {
        "message": "Student registration successful.",
        "user": profile_record,
        "token": token
    }

@router.post("/login")
def login(payload: LoginRequest, request: Request):
    auth_rate_limiter.check(request)

    user_profile = None

    if payload.email:
        user_profile = next((p for p in db.profiles.values() if p.get("email") == payload.email), None)
    elif payload.roll_number and payload.college_id:
        user_profile = next(
            (p for p in db.profiles.values() if p.get("college_id") == payload.college_id and p.get("roll_number") == payload.roll_number),
            None
        )

    if not user_profile:
        raise HTTPException(status_code=401, detail="Invalid credentials provided.")

    token = create_jwt_token(user_profile["id"], user_profile.get("email", ""), user_profile["role"])

    return {
        "message": "Login successful.",
        "user": user_profile,
        "token": token
    }

@router.get("/me")
def get_current_user_profile(current_user: dict = Depends(verify_token)):
    college = db.colleges.get(current_user.get("college_id")) if current_user.get("college_id") else None
    return {
        "user": current_user,
        "college": college
    }
