import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Enum as SQLEnum, DateTime, Index, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, enum.Enum):
    TEACHER = "teacher"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.STUDENT)
    account_status = Column(String(50), nullable=False, default="active")
    roll_number = Column(String(50), nullable=True, index=True)
    department = Column(String(100), nullable=True)
    semester = Column(Integer, nullable=True, index=True)
    section = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    exams = relationship("Exam", back_populates="teacher", cascade="all, delete-orphan")
    submissions = relationship("AnswerSheet", back_populates="student", cascade="all, delete-orphan")
    reviewed_final_marks = relationship("FinalMark", back_populates="reviewing_teacher")
    audit_logs = relationship("AuditLog", back_populates="teacher")

    __table_args__ = (
        Index("idx_users_email_role", "email", "role"),
        CheckConstraint("section IS NULL OR (section >= 1 AND section <= 4)", name="chk_user_section_1_to_4"),
        Index("idx_users_class", "semester", "section"),
    )
