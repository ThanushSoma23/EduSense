import io
import os
import pytest
import numpy as np
import cv2
from PIL import Image, ImageDraw
from fastapi import status

from app.services.ocr_service import (
    preprocess_page_for_ocr,
    transcribe_and_segment,
    segment_ocr_lines,
    extract_document_pages,
    get_last_ocr_error
)
from app.services.pipeline_service import (
    match_segmented_answers_to_questions,
    process_submission_pipeline
)
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.models.evaluation import Evaluation
from app.models.final_mark import FinalMark
from app.models.enrollment import ExamEnrollment


def create_synthetic_handwritten_image(text_lines: list[str], blur: bool = False) -> bytes:
    """Creates a synthetic handwritten-style answer image for testing."""
    img = Image.new("RGB", (800, 400), color=(250, 248, 240))
    draw = ImageDraw.Draw(img)
    
    y = 30
    for line in text_lines:
        draw.text((40, y), line, fill=(20, 25, 45))
        y += 50

    np_img = np.array(img)
    if blur:
        # Apply strong Gaussian blur to simulate severe out-of-focus camera
        np_img = cv2.GaussianBlur(np_img, (35, 35), 15)

    is_success, buf = cv2.imencode(".png", np_img)
    assert is_success
    return buf.tobytes()


def test_clear_handwritten_answer_sheet():
    """Requirement E.1: Test clear handwritten answer sheet preprocessing and segmentation."""
    lines = [
        "Q1. Binary search operates in O(log n) time complexity.",
        "Q2. QuickSort uses a divide and conquer partitioning approach."
    ]
    img_bytes = create_synthetic_handwritten_image(lines, blur=False)
    pages, err = extract_document_pages(img_bytes)
    assert err is None
    assert pages is not None and len(pages) == 1

    proc_img, flags = preprocess_page_for_ocr(pages[0])
    assert "blurry" not in flags
    assert proc_img.shape[0] > 0 and proc_img.shape[1] > 0

    # Test segmentation on clear lines
    mock_detections = [
        {"text": "Q1 Binary search operates in logarithmic time.", "confidence": 0.94},
        {"text": "Q2 QuickSort uses divide and conquer.", "confidence": 0.91}
    ]
    segmented = segment_ocr_lines(mock_detections, threshold=0.70)
    assert len(segmented) == 2
    assert segmented[0]["question_number"] == 1
    assert segmented[0]["extraction_status"] == "SUCCESS"
    assert segmented[0]["needs_review"] is False
    assert segmented[1]["question_number"] == 2
    assert segmented[1]["extraction_status"] == "SUCCESS"


def test_low_quality_or_blurry_image():
    """Requirement E.2: Test low-quality or blurry image detection."""
    lines = ["Q1 Blurry text that cannot be read easily."]
    blurry_bytes = create_synthetic_handwritten_image(lines, blur=True)
    pages, err = extract_document_pages(blurry_bytes)
    assert err is None
    assert pages is not None and len(pages) == 1

    proc_img, flags = preprocess_page_for_ocr(pages[0])
    assert "blurry" in flags

    # Low-confidence lines in blurry image must be flagged PARTIAL with needs_review
    mock_detections = [
        {"text": "Q1 Blurry unreadable smudge", "confidence": 0.38}
    ]
    segmented = segment_ocr_lines(mock_detections, threshold=0.70)
    assert len(segmented) == 1
    assert segmented[0]["extraction_status"] == "PARTIAL"
    assert segmented[0]["needs_review"] is True


def test_corrupt_image_handling():
    """Requirement E.3: Test corrupt image bytes do not crash the pipeline."""
    corrupt_bytes = b"CORRUPT_NOT_AN_IMAGE_OR_PDF_DATA_GARBAGE"
    pages, err = extract_document_pages(corrupt_bytes)
    assert pages is None
    assert err is not None

    answers, backend_used = transcribe_and_segment(corrupt_bytes, backend="easyocr")
    assert len(answers) == 0
    ocr_err = get_last_ocr_error()
    assert ocr_err is not None
    assert "corrupt" in ocr_err.lower() or "unreadable" in ocr_err.lower()


def test_multiple_numbered_answers_and_sequence():
    """Requirement E.4: Test multiple numbered answers segmentation."""
    detections = [
        {"text": "Question 1: Recursion has base and inductive steps.", "confidence": 0.88},
        {"text": "Question 2: Hash tables provide average O(1) lookups.", "confidence": 0.85},
        {"text": "Ans 3: Dynamic programming caches subproblem solutions.", "confidence": 0.92}
    ]
    segmented = segment_ocr_lines(detections, threshold=0.70)
    assert len(segmented) == 3
    assert [s["question_number"] for s in segmented] == [1, 2, 3]
    for s in segmented:
        assert s["extraction_status"] == "SUCCESS"
        assert len(s["text"]) > 10


def test_missing_and_ambiguous_question_numbers(db, teacher_user):
    """Requirement E.5: Test missing and ambiguous/misread question numbers."""
    exam = Exam(
        title="Algorithms Exam",
        subject="CS",
        teacher_id=teacher_user.id
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    q1 = Question(exam_id=exam.id, question_number=1, question_text="Binary Search", model_answer="Binary search", rubric="log n", max_marks=5.0)
    q2 = Question(exam_id=exam.id, question_number=2, question_text="Merge Sort", model_answer="Merge sort divide conquer", rubric="divide conquer", max_marks=5.0)
    q3 = Question(exam_id=exam.id, question_number=3, question_text="Dijkstra Shortest Path", model_answer="Dijkstra priority queue shortest path", rubric="shortest path priority queue", max_marks=5.0)
    db.add_all([q1, q2, q3])
    db.commit()

    # Suppose OCR misrecognized Question 3 as Question 5, but text mentions Dijkstra priority queue
    # Question 2 was not attempted at all.
    segmented = [
        {"question_number": 1, "text": "Binary search algorithm halves search space.", "confidence": 0.90, "extraction_status": "SUCCESS"},
        {"question_number": 5, "raw_question_number": 5, "text": "Dijkstra computes shortest path using priority queue.", "confidence": 0.85, "extraction_status": "SUCCESS"}
    ]

    exam_questions = sorted(exam.questions, key=lambda q: q.question_number)
    matched = match_segmented_answers_to_questions(segmented, exam_questions)

    # Q1: Exact match
    assert matched[q1.id]["text"] == "Binary search algorithm halves search space."
    assert matched[q1.id]["extraction_status"] == "SUCCESS"

    # Q2: Missing / unattempted
    assert matched[q2.id]["text"] == ""
    assert matched[q2.id]["needs_review"] is True
    assert matched[q2.id]["extraction_status"] == "PARTIAL"
    assert "not detected" in matched[q2.id]["mapping_note"].lower()

    # Q3: Content-matched from Q5 misread
    assert "dijkstra" in matched[q3.id]["text"].lower()
    assert matched[q3.id]["needs_review"] is True
    assert matched[q3.id]["extraction_status"] == "PARTIAL"
    assert "mapped to question 3" in matched[q3.id]["mapping_note"].lower()


def test_question_answer_and_rubric_associations(db, teacher_user, student_user):
    """Requirement E.6: Test question-to-answer and rubric associations in pipeline."""
    exam = Exam(
        title="Networking Exam",
        subject="CS",
        teacher_id=teacher_user.id
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    q1 = Question(
        exam_id=exam.id,
        question_number=1,
        question_text="Explain TCP handshake.",
        model_answer="TCP uses SYN, SYN-ACK, ACK three way handshake.",
        rubric="SYN, SYN-ACK, ACK handshake",
        max_marks=10.0
    )
    q2 = Question(
        exam_id=exam.id,
        question_number=2,
        question_text="Explain UDP protocol.",
        model_answer="UDP is a connectionless unreliable transport protocol.",
        rubric="Connectionless, datagram, no guarantee",
        max_marks=10.0
    )
    db.add_all([q1, q2])
    db.commit()

    sub = AnswerSheet(
        student_id=student_user.id,
        exam_id=exam.id,
        file_reference="/uploads/submissions/test_net.png",
        processing_status="PENDING"
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    # Create synthetic answer sheet with both questions
    raw_img = create_synthetic_handwritten_image([
        "Q1. TCP requires SYN, SYN-ACK, and ACK for 3-way connection setup.",
        "Q2. UDP is connectionless without retransmissions or ordering."
    ])

    answers = process_submission_pipeline(db=db, submission=sub, exam=exam, image_bytes=raw_img)
    assert len(answers) == 2

    # Verify associations: Question 1 answer matches Question 1
    sa1 = next(a for a in answers if a.question_id == q1.id)
    assert sa1.question_id == q1.id
    eval1 = db.query(Evaluation).filter(Evaluation.answer_id == sa1.id).first()
    assert eval1 is not None
    assert eval1.evaluation_status == "COMPLETED"

    # Question 2 answer matches Question 2
    sa2 = next(a for a in answers if a.question_id == q2.id)
    assert sa2.question_id == q2.id
    eval2 = db.query(Evaluation).filter(Evaluation.answer_id == sa2.id).first()
    assert eval2 is not None
    assert eval2.evaluation_status == "COMPLETED"

    # Verify no FinalMark created
    answer_ids = [a.id for a in answers]
    assert db.query(FinalMark).filter(FinalMark.answer_id.in_(answer_ids)).count() == 0


def test_teacher_correction_of_ocr_text_and_reevaluation(
    client, db, teacher_user, teacher_token_headers, student_user
):
    """Requirement E.7: Test teacher correction of OCR text via PUT /answers/{id}."""
    exam = Exam(
        title="Compiler Design",
        subject="CS",
        teacher_id=teacher_user.id
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    q1 = Question(
        exam_id=exam.id,
        question_number=1,
        question_text="Define lexical analysis.",
        model_answer="Lexical analysis converts stream of characters into tokens using regular expressions.",
        rubric="Tokens, lexemes, regular expressions",
        max_marks=10.0
    )
    db.add(q1)
    db.commit()

    sub = AnswerSheet(
        student_id=student_user.id,
        exam_id=exam.id,
        file_reference="/uploads/submissions/test_compiler.png",
        processing_status="EVALUATED"
    )
    db.add(sub)
    db.commit()

    # Initial garbled OCR text
    sa = StudentAnswer(
        submission_id=sub.id,
        question_id=q1.id,
        extracted_text="Garbled misread ocr text without tokens",
        ocr_confidence=0.35,
        extraction_status="PARTIAL"
    )
    db.add(sa)
    db.commit()

    init_eval = Evaluation(
        answer_id=sa.id,
        similarity_score=0.20,
        concept_coverage=0.10,
        suggested_marks=2.0,
        feedback="Missing tokenization concepts.",
        evaluation_status="COMPLETED"
    )
    db.add(init_eval)
    db.commit()

    # Teacher corrects the transcript
    corrected_text = "Lexical analysis converts a stream of characters into meaningful tokens using regular expressions."
    res = client.put(
        f"/api/v1/submissions/{sub.id}/answers/{sa.id}",
        headers=teacher_token_headers,
        json={"extracted_text": corrected_text}
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["answer"]["extracted_text"] == corrected_text
    assert data["answer"]["extraction_status"] == "CORRECTED"

    # Verify Evaluation was recomputed and score improved
    db.refresh(init_eval)
    assert init_eval.suggested_marks > 5.0
    assert init_eval.similarity_score > 0.60


def test_final_marks_approval_and_student_access_rules(
    client, db, teacher_user, teacher_token_headers, student_user, student_token_headers
):
    """Requirement E.8: Test preservation of teacher-controlled final marks and student access rules."""
    exam = Exam(
        title="Software Engineering",
        subject="CS",
        teacher_id=teacher_user.id
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    q = Question(
        exam_id=exam.id,
        question_number=1,
        question_text="Explain Agile methodology.",
        model_answer="Agile is an iterative approach to software development and project management.",
        rubric="Iterative, sprints, collaboration",
        max_marks=10.0
    )
    db.add(q)
    db.commit()

    enrollment = ExamEnrollment(exam_id=exam.id, student_id=student_user.id)
    db.add(enrollment)
    db.commit()

    sub = AnswerSheet(
        student_id=student_user.id,
        exam_id=exam.id,
        file_reference="/uploads/submissions/test_se.png",
        processing_status="EVALUATED"
    )
    db.add(sub)
    db.commit()

    sa = StudentAnswer(
        submission_id=sub.id,
        question_id=q.id,
        extracted_text="Agile involves iterative development cycles called sprints.",
        ocr_confidence=0.88,
        extraction_status="SUCCESS"
    )
    db.add(sa)
    db.commit()

    ev = Evaluation(
        answer_id=sa.id,
        similarity_score=0.85,
        concept_coverage=0.90,
        suggested_marks=8.5,
        feedback="Good explanation.",
        evaluation_status="COMPLETED"
    )
    db.add(ev)
    db.commit()

    # Rule 1: Student results endpoint is forbidden before exam is published or reviewed
    student_res_before = client.get(
        f"/api/v1/final-marks/student/results/{sub.id}",
        headers=student_token_headers
    )
    assert student_res_before.status_code == status.HTTP_403_FORBIDDEN
    assert "not been published" in student_res_before.json()["detail"].lower()

    # Rule 2: Student cannot approve final marks
    student_approve_attempt = client.post(
        "/api/v1/final-marks/review",
        headers=student_token_headers,
        json={
            "answer_id": sa.id,
            "approved_marks": 9.0,
            "approval_status": "APPROVED",
            "reason": "Student attempt"
        }
    )
    assert student_approve_attempt.status_code == status.HTTP_403_FORBIDDEN

    # Rule 3: Teacher approves final mark
    teacher_approve = client.post(
        "/api/v1/final-marks/review",
        headers=teacher_token_headers,
        json={
            "answer_id": sa.id,
            "approved_marks": 9.0,
            "approval_status": "APPROVED",
            "reason": "Verified and approved."
        }
    )
    assert teacher_approve.status_code == status.HTTP_200_OK
    assert teacher_approve.json()["approved_marks"] == 9.0

    # Rule 4: Student can now access approved final mark once reviewed
    student_res_after = client.get(
        f"/api/v1/final-marks/student/results/{sub.id}",
        headers=student_token_headers
    )
    assert student_res_after.status_code == status.HTTP_200_OK
    data_after = student_res_after.json()
    assert data_after["total_final_marks"] == 9.0
    assert data_after["questions"][0]["final_approved_marks"] == 9.0
    assert data_after["questions"][0]["ai_suggested_marks"] == 8.5
