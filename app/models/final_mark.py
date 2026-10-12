from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Index, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class FinalMark(Base):
    __tablename__ = "final_marks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    answer_id = Column(Integer, ForeignKey("student_answers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    approved_marks = Column(Float, nullable=False)
    reviewing_teacher_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    approval_status = Column(String(50), nullable=False, default="APPROVED")  # APPROVED, MODIFIED, REJECTED
    approval_timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    answer = relationship("StudentAnswer", back_populates="final_mark")
    reviewing_teacher = relationship("User", back_populates="reviewed_final_marks")
    audit_logs = relationship("AuditLog", back_populates="final_mark", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("approved_marks >= 0.0", name="chk_final_marks_positive"),
        Index("idx_final_marks_answer_teacher", "answer_id", "reviewing_teacher_id"),
    )
