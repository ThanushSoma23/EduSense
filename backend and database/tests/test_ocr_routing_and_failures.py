import io
import os
import pytest
from PIL import Image
from fastapi import status

from app.services.ocr_service import (
    transcribe_and_segment,
    segment_ocr_lines,
    get_last_ocr_error,
    get_mock_ocr_lines
)
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.models.evaluation import Evaluation
from app.models.final_mark import FinalMark
from app.models.enrollment import ExamEnrollment


SAMPLE_IMAGE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "AIML-2", "sample", "answer_sheet.jpg")
)


def get_sample_image_bytes() -> bytes:
    if os.path.exists(SAMPLE_IMAGE_PATH):
        with open(SAMPLE_IMAGE_PATH, "rb") as f:
            return f.read()
    # Fallback to simple RGB image if sample is missing
    img = Image.new("RGB", (300, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_explicit_mock_backend():
    """Verify that backend='mock' explicitly returns mock data with backend_used='mock'."""
    sample_bytes = get_sample_image_bytes()
    answers, backend_used = transcribe_and_segment(sample_bytes, backend="mock")

    assert backend_used == "mock"
    assert len(answers) >= 2
    assert any("deadlock" in a["text"].lower() for a in answers)


def test_configured_easyocr_backend():
    """Verify that easyocr backend runs real local inference and extracts text."""
    sample_bytes = get_sample_image_bytes()
    answers, backend_used = transcribe_and_segment(sample_bytes, backend="easyocr")

    assert backend_used == "easyocr"
    # EasyOCR on the sample answer sheet extracts text lines
    assert len(answers) >= 1
    for a in answers:
        assert "extraction_status" in a
        assert a["extraction_status"] in ["SUCCESS", "PARTIAL", "LOW_CONFIDENCE"]
        assert "confidence" in a
        assert 0.0 <= a["confidence"] <= 1.0


def test_trocr_dependency_failure_no_mock_leak():
    """Verify TrOCR fails safely with missing sentencepiece and NEVER leaks mock text."""
    sample_bytes = get_sample_image_bytes()
    answers, backend_used = transcribe_and_segment(sample_bytes, backend="trocr")

    assert backend_used == "trocr"
    # When sentencepiece is missing, TrOCR must fail and return empty answers, NOT mock data
    err = get_last_ocr_error()
    assert err is not None, "Expected an explicit error recorded for TrOCR failure"
    assert "sentencepiece" in err.lower() or "not found" in err.lower() or "failed" in err.lower()
    assert len(answers) == 0, "TrOCR failure must NEVER return mock answers"


def test_blank_image_handling_not_mocked():
    """Verify a blank image returns empty extraction and does not fabricate text."""
    blank_img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    blank_img.save(buf, format="JPEG")
    blank_bytes = buf.getvalue()

    answers, backend_used = transcribe_and_segment(blank_bytes, backend="easyocr")
    assert backend_used == "easyocr"
    # A completely blank image contains no text
    assert len(answers) == 0


def test_partial_answer_preserves_text_and_needs_review():
    """Verify that low-confidence lines preserve extracted text and flag PARTIAL status."""
    low_conf_lines = [
        {"text": "Q1 Partial handwriting deciphered here.", "confidence": 0.42}
    ]
    segmented = segment_ocr_lines(low_conf_lines, threshold=0.70)
    assert len(segmented) == 1
    assert segmented[0]["question_number"] == 1
    assert segmented[0]["text"] == "Partial handwriting deciphered here."
    assert segmented[0]["extraction_status"] == "PARTIAL"
    assert segmented[0]["needs_review"] is True


def test_upload_endpoint_runs_easyocr_and_never_creates_final_marks(
    client, db, teacher_user, teacher_token_headers, student_user
):
    """
    Integration test: Uploading answer sheet through /exams/{id}/sheets:
    1. Executes EasyOCR through the real upload route.
    2. Persists StudentAnswer and Evaluation records.
    3. Guarantees that FinalMark is NEVER created or auto-approved.
    """
    # 1. Create an exam with 2 questions
    exam = Exam(
        title="Operating Systems Midterm",
        subject="Computer Science",
        teacher_id=teacher_user.id
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    q1 = Question(
        exam_id=exam.id,
        question_number=1,
        question_text="Explain deadlock.",
        model_answer="Deadlock occurs when processes wait for resources held by each other.",
        rubric="Processes wait for resources, circular wait, mutual exclusion",
        max_marks=10.0
    )
    q2 = Question(
        exam_id=exam.id,
        question_number=2,
        question_text="What is a process?",
        model_answer="A process is a program in execution with its own address space.",
        rubric="Program in execution, virtual address space",
        max_marks=10.0
    )
    db.add_all([q1, q2])

    # Enroll student
    enrollment = ExamEnrollment(
        exam_id=exam.id,
        student_id=student_user.id
    )
    db.add(enrollment)
    db.commit()

    # 2. Upload sample answer sheet
    sample_bytes = get_sample_image_bytes()
    upload_res = client.post(
        f"/api/v1/exams/{exam.id}/sheets",
        headers=teacher_token_headers,
        data={"student_id": student_user.id},
        files={"files": ("answer_sheet.jpg", sample_bytes, "image/jpeg")}
    )

    assert upload_res.status_code == status.HTTP_200_OK
    data = upload_res.json()
    assert data["success"] is True
    assert data["status"] == "ready"
    assert data["answers_count"] == 2

    # 3. Verify database state
    submission_id = data["submission_id"]
    sub = db.query(AnswerSheet).filter(AnswerSheet.id == submission_id).first()
    assert sub is not None
    assert sub.processing_status == "EVALUATED"

    # Verify student answers exist with real text
    answers = db.query(StudentAnswer).filter(StudentAnswer.submission_id == submission_id).all()
    assert len(answers) == 2
    for ans in answers:
        assert ans.extraction_status in ["SUCCESS", "PARTIAL", "FAILED"]
        # Evaluations exist
        eval_record = db.query(Evaluation).filter(Evaluation.answer_id == ans.id).first()
        assert eval_record is not None
        assert eval_record.evaluation_status == "COMPLETED"

    # CRITICAL VERIFICATION: FinalMark must NEVER be created by OCR or pipeline
    final_marks = db.query(FinalMark).all()
    assert len(final_marks) == 0, "OCR pipeline must NEVER create FinalMark records without teacher approval"


def test_ocr_failure_does_not_create_final_marks_or_bypass_approval(
    client, db, teacher_user, student_user
):
    """
    Verify that when OCR completely fails (e.g. unreadable/corrupt image):
    1. Processing status is marked FAILED.
    2. Extraction status is FAILED with empty text.
    3. Evaluation status is FAILED and no marks are awarded.
    4. FinalMark is NEVER created, preserving teacher approval.
    """
    from app.services.pipeline_service import process_submission_pipeline

    exam = Exam(
        title="Database Systems",
        subject="Computer Science",
        teacher_id=teacher_user.id
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    q = Question(
        exam_id=exam.id,
        question_number=1,
        question_text="Explain B+ Trees.",
        model_answer="B+ trees are self-balancing search trees with data in leaves.",
        rubric="Self balancing, search tree, leaves",
        max_marks=10.0
    )
    db.add(q)
    db.commit()

    sub = AnswerSheet(
        student_id=student_user.id,
        exam_id=exam.id,
        file_reference="/uploads/submissions/test_corrupt.png",
        processing_status="PENDING"
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    # Pass corrupt bytes that trigger OCR failure
    corrupt_bytes = b"NOT_A_VALID_IMAGE_DATA_CORRUPT"
    answers = process_submission_pipeline(
        db=db,
        submission=sub,
        exam=exam,
        image_bytes=corrupt_bytes
    )

    assert sub.processing_status == "FAILED"
    assert len(answers) == 1
    assert answers[0].extraction_status == "FAILED"
    assert answers[0].extracted_text == ""
    assert answers[0].ocr_confidence == 0.0

    eval_rec = db.query(Evaluation).filter(Evaluation.answer_id == answers[0].id).first()
    assert eval_rec is not None
    assert eval_rec.evaluation_status == "FAILED"
    assert "OCR" in eval_rec.feedback
    assert eval_rec.similarity_score is None

    # Verify no FinalMark records exist
    assert db.query(FinalMark).count() == 0
