from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)
    semester = Column(Integer, nullable=True, index=True)
    section = Column(Integer, nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="DRAFT")  # DRAFT, PUBLISHED, COMPLETED, ARCHIVED
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    teacher = relationship("User", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan", order_by="Question.question_number")
    submissions = relationship("AnswerSheet", back_populates="exam", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("section IS NULL OR (section >= 1 AND section <= 4)", name="chk_exam_section_1_to_4"),
        CheckConstraint("semester IS NULL OR (semester >= 1 AND semester <= 12)", name="chk_exam_semester_range"),
        Index("idx_exams_class_lookup", "semester", "section", "subject"),
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    model_answer = Column(Text, nullable=False)
    max_marks = Column(Float, nullable=False)
    rubric = Column(Text, nullable=True)  # Evaluation criteria / grading rubric text or JSON
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    exam = relationship("Exam", back_populates="questions")
    student_answers = relationship("StudentAnswer", back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("exam_id", "question_number", name="uq_exam_question_number"),
        CheckConstraint("max_marks > 0", name="chk_max_marks_positive"),
        Index("idx_questions_exam_id", "exam_id"),
    )
