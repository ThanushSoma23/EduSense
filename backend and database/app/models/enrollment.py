from datetime import datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class ExamEnrollment(Base):
    __tablename__ = "exam_enrollments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    enrolled_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    exam = relationship("Exam", backref="enrollments")
    student = relationship("User", backref="exam_enrollments")

    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_exam_student_enrollment"),
        Index("idx_enrollment_exam_student", "exam_id", "student_id"),
    )
