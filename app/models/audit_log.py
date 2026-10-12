from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    final_mark_id = Column(Integer, ForeignKey("final_marks.id", ondelete="SET NULL"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, APPROVE, REJECT
    previous_value = Column(Text, nullable=True)  # JSON or text string of previous state
    updated_value = Column(Text, nullable=False)   # JSON or text string of updated state
    reason = Column(Text, nullable=True)          # Teacher's rationale for modification
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    final_mark = relationship("FinalMark", back_populates="audit_logs")
    teacher = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_teacher_time", "teacher_id", "timestamp"),
        Index("idx_audit_logs_mark_id", "final_mark_id"),
    )
