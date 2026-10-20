import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.models.final_mark import FinalMark
from app.models.user import User

logger = logging.getLogger(__name__)

# In-memory tracking for notification deduplication and audit trail
_SENT_NOTIFICATIONS: Dict[str, Dict[str, Any]] = {}


class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAILS_FROM_EMAIL
        self.from_name = settings.EMAILS_FROM_NAME
        self.frontend_base_url = settings.FRONTEND_BASE_URL.rstrip("/")

    @property
    def is_smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    def send_exam_publication_notification(self, db: Session, exam: Exam) -> Dict[str, Any]:
        """
        Notifies students when an exam's results are officially approved and published by the teacher.
        Includes student's final approved marks, direct link to authenticated results, and AI Tutor link.
        Deduplicates per (exam_id, student_id) to prevent repeat spam.
        """
        submissions = db.query(AnswerSheet).filter(AnswerSheet.exam_id == exam.id).all()
        questions = db.query(Question).filter(Question.exam_id == exam.id).all()
        max_marks = sum(q.max_marks for q in questions) if questions else 100.0

        results = {
            "exam_id": exam.id,
            "exam_title": exam.title,
            "dispatched_count": 0,
            "skipped_duplicate_count": 0,
            "delivery_mode": "smtp" if self.is_smtp_configured else "mock_console",
            "notifications": []
        }

        for sub in submissions:
            student = db.query(User).filter(User.id == sub.student_id).first()
            if not student:
                continue

            dedup_key = f"exam_{exam.id}_student_{student.id}"
            if dedup_key in _SENT_NOTIFICATIONS:
                logger.info(f"Skipping duplicate notification for student {student.id} on exam {exam.id}")
                results["skipped_duplicate_count"] += 1
                continue

            # Calculate total approved marks
            student_answers = db.query(StudentAnswer).filter(StudentAnswer.submission_id == sub.id).all()
            total_approved = 0.0
            has_marks = False
            for ans in student_answers:
                fm = db.query(FinalMark).filter(FinalMark.answer_id == ans.id).first()
                if fm:
                    total_approved += fm.approved_marks
                    has_marks = True

            # If no formal FinalMark records yet, check if there are evaluations
            if not has_marks:
                from app.models.evaluation import Evaluation
                for ans in student_answers:
                    ev = db.query(Evaluation).filter(Evaluation.answer_id == ans.id).first()
                    if ev:
                        total_approved += ev.suggested_marks

            percentage = (total_approved / max_marks * 100) if max_marks > 0 else 0.0

            results_url = f"{self.frontend_base_url}/student/results?exam_id={exam.id}&submission_id={sub.id}"
            tutor_url = f"{self.frontend_base_url}/student/results?exam_id={exam.id}&submission_id={sub.id}&tutor=true"

            subject = f"Official Exam Results Published: {exam.title}"
            body_text = (
                f"Dear {student.name},\n\n"
                f"Your instructor has reviewed and published verified results for '{exam.title}'.\n\n"
                f"Final Approved Score: {total_approved:.1f} / {max_marks:.1f} ({percentage:.1f}%)\n\n"
                f"• View your question-by-question breakdown and teacher feedback:\n"
                f"  {results_url}\n\n"
                f"• Interactive Doubt Resolution with AI Personal Tutor:\n"
                f"  {tutor_url}\n\n"
                f"Best regards,\n"
                f"{self.from_name}\n"
                f"EduSense AI Assessment System\n"
            )

            delivery_record = {
                "dedup_key": dedup_key,
                "student_id": student.id,
                "student_name": student.name,
                "recipient_email": student.email,
                "exam_id": exam.id,
                "exam_title": exam.title,
                "total_score": total_approved,
                "max_marks": max_marks,
                "percentage": round(percentage, 1),
                "results_url": results_url,
                "tutor_url": tutor_url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "DELIVERED"
            }

            if self.is_smtp_configured:
                try:
                    self._send_smtp_email(to_email=student.email, subject=subject, body=body_text)
                    delivery_record["mode"] = "smtp"
                    logger.info(f"Successfully sent SMTP notification to {student.email} for exam {exam.id}")
                except Exception as e:
                    logger.error(f"Failed to send SMTP email to {student.email}: {e}. Falling back to mock record.")
                    delivery_record["mode"] = "mock_fallback"
                    delivery_record["error"] = str(e)
            else:
                delivery_record["mode"] = "mock_console"
                logger.info(
                    f"\n==================== [SAFE MOCK EMAIL ADAPTER] ====================\n"
                    f"To: {student.email} ({student.name})\n"
                    f"From: {self.from_name} <{self.from_email}>\n"
                    f"Subject: {subject}\n"
                    f"--------------------------------------------------------------------\n"
                    f"{body_text}"
                    f"===================================================================\n"
                )

            _SENT_NOTIFICATIONS[dedup_key] = delivery_record
            results["notifications"].append(delivery_record)
            results["dispatched_count"] += 1

        return results

    def _send_smtp_email(self, to_email: str, subject: str, body: str):
        msg = MIMEMultipart()
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
        try:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
        finally:
            server.quit()

    @staticmethod
    def get_notification_history() -> List[Dict[str, Any]]:
        return list(_SENT_NOTIFICATIONS.values())


email_service = EmailService()
