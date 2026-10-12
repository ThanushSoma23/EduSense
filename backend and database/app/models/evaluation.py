from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Index, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    answer_id = Column(Integer, ForeignKey("student_answers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    similarity_score = Column(Float, nullable=True)  # AI semantic similarity score (0.0 to 1.0)
    concept_coverage = Column(Float, nullable=True)  # Concept coverage percentage/score (0.0 to 1.0)
    suggested_marks = Column(Float, nullable=False, default=0.0)
    feedback = Column(Text, nullable=True)
    supporting_references = Column(Text, nullable=True)  # JSON or formatted string of references/key phrases
    evaluation_status = Column(String(50), nullable=False, default="COMPLETED")  # PENDING, COMPLETED, FAILED
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    answer = relationship("StudentAnswer", back_populates="evaluation")

    __table_args__ = (
        CheckConstraint("similarity_score IS NULL OR (similarity_score >= 0.0 AND similarity_score <= 1.0)", name="chk_eval_similarity_range"),
        CheckConstraint("concept_coverage IS NULL OR (concept_coverage >= 0.0 AND concept_coverage <= 1.0)", name="chk_eval_concept_range"),
        CheckConstraint("suggested_marks >= 0.0", name="chk_eval_suggested_marks_positive"),
        Index("idx_evaluations_answer_id", "answer_id"),
    )
