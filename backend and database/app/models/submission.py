from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class AnswerSheet(Base):
    __tablename__ = "answer_sheets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    file_reference = Column(String(512), nullable=False)  # Path or URL to scanned answer sheet PDF/image
    submission_time = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    processing_status = Column(String(50), nullable=False, default="PENDING")  # PENDING, EXTRACTED, EVALUATED, REVIEWED, FAILED
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    student = relationship("User", back_populates="submissions")
    exam = relationship("Exam", back_populates="submissions")
    answers = relationship("StudentAnswer", back_populates="submission", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("student_id", "exam_id", name="uq_student_exam_submission"),
        Index("idx_answer_sheets_student_exam", "student_id", "exam_id"),
    )


class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("answer_sheets.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    extracted_text = Column(Text, nullable=True)  # Extracted answer text supplied by OCR module
    ocr_confidence = Column(Float, nullable=True)  # 0.0 to 1.0 confidence score
    extraction_status = Column(String(50), nullable=False, default="SUCCESS")  # SUCCESS, LOW_CONFIDENCE, FAILED
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    submission = relationship("AnswerSheet", back_populates="answers")
    question = relationship("Question", back_populates="student_answers")
    evaluation = relationship("Evaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan")
    final_mark = relationship("FinalMark", back_populates="answer", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("submission_id", "question_id", name="uq_submission_question"),
        Index("idx_student_answers_sub_q", "submission_id", "question_id"),
    )
