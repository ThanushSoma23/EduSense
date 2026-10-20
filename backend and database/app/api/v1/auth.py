import secrets
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    UserRegister,
    TeacherProvisioningRequest,
    TeacherRegisterSchema,
    StudentRegisterSchema,
    UserLogin,
    UserResponse,
    Token,
    AcademicProfileUpdate
)
from app.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication & User Management"])


@router.get("/colleges")
def list_colleges():
    """
    Returns list of authorized institutions/colleges for registration.
    """
    return {
        "colleges": [
            {"id": "col-1", "name": "Indian Institute of Information Technology", "code": "IIITK"},
            {"id": "col-2", "name": "National Institute of Technology", "code": "NIT"},
            {"id": "col-3", "name": "Indian Institute of Technology", "code": "IIT"},
            {"id": "col-4", "name": "International Institute of Tech & Science", "code": "IITS"}
        ]
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserRegister, db: Session = Depends(get_db)):
    """
    Public registration endpoint. Safely creates STUDENT accounts only.
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    db_user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=UserRole.STUDENT,
        account_status="active"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/register/teacher", status_code=status.HTTP_201_CREATED)
def register_teacher(payload: TeacherRegisterSchema, db: Session = Depends(get_db)):
    """
    Dedicated teacher registration matching the original UI contract.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    teacher = User(
        name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.TEACHER,
        account_status="active"
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    access_token = create_access_token(data={"sub": str(teacher.id), "role": teacher.role.value})
    user_resp = UserResponse.model_validate(teacher)
    return {
        "token": access_token,
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_resp,
        "message": "Teacher account registered successfully!"
    }


@router.post("/register/student", status_code=status.HTTP_201_CREATED)
def register_student(payload: StudentRegisterSchema, db: Session = Depends(get_db)):
    """
    Dedicated student registration matching the original UI contract.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    student = User(
        name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.STUDENT,
        account_status="active",
        roll_number=payload.roll_number,
        department=payload.department or "Computer Science",
        semester=payload.semester,
        section=payload.section
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    access_token = create_access_token(data={"sub": str(student.id), "role": student.role.value})
    user_resp = UserResponse.model_validate(student)
    return {
        "token": access_token,
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_resp,
        "message": "Student account registered successfully!"
    }


@router.post("/provision-teacher", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def provision_teacher_account(prov_in: TeacherProvisioningRequest, db: Session = Depends(get_db)):
    """
    Admin-controlled endpoint for provisioning authorized Teacher accounts.
    Requires a valid admin secret key.
    """
    if not settings.ADMIN_SECRET_KEY or not secrets.compare_digest(prov_in.admin_key, settings.ADMIN_SECRET_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Invalid admin secret key for teacher provisioning."
        )

    existing_user = db.query(User).filter(User.email == prov_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    db_teacher = User(
        name=prov_in.name,
        email=prov_in.email,
        password_hash=hash_password(prov_in.password),
        role=UserRole.TEACHER,
        account_status="active"
    )
    db.add(db_teacher)
    db.commit()
    db.refresh(db_teacher)
    return db_teacher


@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    JSON Login endpoint supporting both email and roll-number logins.
    """
    login_id = user_credentials.email or user_credentials.roll_number
    if not login_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address or roll number required."
        )

    # Search by email or case-insensitive match
    user = db.query(User).filter(User.email == login_id).first()
    if not user:
        # Fallback to finding user by name if roll number format
        user = db.query(User).filter(User.name.ilike(f"%{login_id}%")).first()

    if not user or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or suspended"
        )

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    user_response = UserResponse.model_validate(user)
    return Token(
        access_token=access_token,
        token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.post("/token", response_model=Token, include_in_schema=False)
def login_oauth(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 compatible token login for FastAPI Docs UI.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    user_resp = UserResponse.model_validate(user)
    return Token(
        access_token=access_token,
        token=access_token,
        token_type="bearer",
        user=user_resp
    )


@router.get("/me")
def read_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Returns profile information for the authenticated user, supporting both flat and nested schemas.
    """
    user_resp = UserResponse.model_validate(current_user)
    data = user_resp.model_dump()
    data["user"] = user_resp
    return data


@router.put("/me/academic-profile", response_model=UserResponse)
def update_academic_profile(
    payload: AcademicProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates student's registered semester, section, and academic details.
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can update an academic class profile."
        )

    current_user.semester = payload.semester
    current_user.section = payload.section
    if payload.department:
        current_user.department = payload.department.strip()
    if payload.roll_number:
        current_user.roll_number = payload.roll_number.strip()

    db.commit()
    db.refresh(current_user)
    return current_user

