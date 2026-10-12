from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserRegister, TeacherProvisioningRequest, UserLogin, UserResponse, Token
from app.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication & User Management"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserRegister, db: Session = Depends(get_db)):
    """
    Public registration endpoint. Safely creates STUDENT accounts only.
    Any attempt to request a privileged teacher role via public registration is safely ignored/overridden to STUDENT.
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Force public registration to create STUDENT accounts exclusively
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


import secrets

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
    JSON Login endpoint for users returning JWT access token.
    """
    user = db.query(User).filter(User.email == user_credentials.email).first()
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
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
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
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def read_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Returns information for the currently authenticated user.
    """
    return current_user
