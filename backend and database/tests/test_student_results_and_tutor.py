import os
import pytest
from fastapi import status
from app.services.storage_service import get_storage_service


def setup_multi_question_exam_and_results(client, teacher_token_headers, student_token_headers):
    # 1. Create Exam with 2 questions
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Systems Architecture Exam",
            "subject": "CS-401",
            "semester": 6,
            "section": 1,
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Differentiate between process and thread.",
                    "model_answer": "Process has separate memory space; threads share process address space.",
                    "rubric": "[]",
                    "max_marks": 10.0
                },
                {
                    "question_number": 2,
                    "question_text": "Explain virtual memory paging mechanism.",
                    "model_answer": "Paging divides virtual memory into fixed size pages mapped to physical frames.",
                    "rubric": "[]",
                    "max_marks": 5.0
                }
            ]
        }
    )
    assert exam_res.status_code == status.HTTP_201_CREATED, exam_res.text
    exam_data = exam_res.json()
    exam_id = exam_data["id"]
    q1_id = exam_data["questions"][0]["id"]
    q2_id = exam_data["questions"][1]["id"]

    # 2. Store a test PDF file in storage
    storage = get_storage_service()
    pdf_bytes = b"%PDF-1.4 test dummy content for answersheet"
    file_ref = storage.save(pdf_bytes, filename="test_answersheet.pdf")

    # 3. Student Submission
    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={"exam_id": exam_id, "file_reference": file_ref}
    )
    assert sub_res.status_code == status.HTTP_201_CREATED, sub_res.text
    submission_id = sub_res.json()["id"]

    # 4. Answers for Q1 and Q2
    ans1_res = client.post(
        f"/api/v1/submissions/{submission_id}/answers",
        headers=teacher_token_headers,
        json={
            "submission_id": submission_id,
            "question_id": q1_id,
            "extracted_text": "Process has separate memory, thread shares memory.",
            "ocr_confidence": 0.92
        }
    )
    ans1_id = ans1_res.json()["id"]

    ans2_res = client.post(
        f"/api/v1/submissions/{submission_id}/answers",
        headers=teacher_token_headers,
        json={
            "submission_id": submission_id,
            "question_id": q2_id,
            "extracted_text": "Paging splits virtual address into page number and offset.",
            "ocr_confidence": 0.88
        }
    )
    ans2_id = ans2_res.json()["id"]

    # 5. Evaluations
    client.post(
        "/api/v1/evaluations",
        headers=teacher_token_headers,
        json={
            "answer_id": ans1_id,
            "similarity_score": 0.9,
            "suggested_marks": 9.0,
            "feedback": "Accurate distinction between process and thread address space."
        }
    )
    client.post(
        "/api/v1/evaluations",
        headers=teacher_token_headers,
        json={
            "answer_id": ans2_id,
            "similarity_score": 0.8,
            "suggested_marks": 4.0,
            "feedback": "Good explanation of address mapping."
        }
    )

    # 6. Teacher final approvals: Q1 = 8.5/10.0, Q2 = 4.0/5.0 (Total: 12.5/15.0)
    client.post(
        "/api/v1/final-marks/review",
        headers=teacher_token_headers,
        json={
            "answer_id": ans1_id,
            "approved_marks": 8.5,
            "approval_status": "APPROVED",
            "reason": "Clear explanation"
        }
    )
    client.post(
        "/api/v1/final-marks/review",
        headers=teacher_token_headers,
        json={
            "answer_id": ans2_id,
            "approved_marks": 4.0,
            "approval_status": "APPROVED",
            "reason": "Complete paging answer"
        }
    )

    return exam_id, q1_id, q2_id, submission_id, file_ref


def test_student_exam_result_endpoint_accuracy(client, teacher_token_headers, student_token_headers):
    """
    Test Issue 1: Verifies student results return exact question IDs, question text,
    approved final marks (not fabricated 85%), total score, and answer sheet file URL.
    """
    exam_id, q1_id, q2_id, submission_id, file_ref = setup_multi_question_exam_and_results(
        client, teacher_token_headers, student_token_headers
    )

    # Publish the exam
    pub_res = client.put(
        f"/api/v1/exams/{exam_id}",
        headers=teacher_token_headers,
        json={"status": "PUBLISHED"}
    )
    assert pub_res.status_code == status.HTTP_200_OK

    # Fetch results as student
    res = client.get(
        f"/api/v1/final-marks/student/exam/{exam_id}",
        headers=student_token_headers
    )
    assert res.status_code == status.HTTP_200_OK, res.text
    data = res.json()

    assert data["submission_id"] == submission_id
    assert data["exam_id"] == exam_id
    assert data["total_max_marks"] == 15.0
    assert data["total_final_marks"] == 12.5
    assert data["file_url"] == f"/api/v1/submissions/{submission_id}/file"
    assert data["file_reference"] == file_ref

    # Verify per-question breakdown
    questions = data["questions"]
    assert len(questions) == 2

    q1 = next(q for q in questions if q["question_id"] == q1_id)
    assert q1["question_number"] == 1
    assert q1["question_text"] == "Differentiate between process and thread."
    assert q1["max_marks"] == 10.0
    assert q1["final_approved_marks"] == 8.5
    assert "process and thread address space" in q1["ai_feedback"]

    q2 = next(q for q in questions if q["question_id"] == q2_id)
    assert q2["question_number"] == 2
    assert q2["question_text"] == "Explain virtual memory paging mechanism."
    assert q2["max_marks"] == 5.0
    assert q2["final_approved_marks"] == 4.0
    assert "address mapping" in q2["ai_feedback"]


def test_student_results_publication_isolation(client, teacher_token_headers, student_token_headers, second_student_token_headers):
    """
    Test Issue 1 Security: Results remain inaccessible to student until published or reviewed,
    and students cannot view other students' submissions.
    """
    # 1. Create Draft Exam
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Unpublished Exam",
            "subject": "CS-999",
            "semester": 6,
            "section": 1,
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Sample draft question.",
                    "model_answer": "Official draft model answer.",
                    "max_marks": 5.0
                }
            ]
        }
    )
    exam_id = exam_res.json()["id"]

    # 2. Student 1 submits (processing_status is PENDING)
    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={"exam_id": exam_id, "file_reference": "uploads/draft_ans.pdf"}
    )
    submission_id = sub_res.json()["id"]

    # 3. Student 1 tries to access results while pending and unpublished -> HTTP 403 Forbidden
    res = client.get(
        f"/api/v1/final-marks/student/exam/{exam_id}",
        headers=student_token_headers
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 4. Student 2 tries to access results for an exam they never submitted -> HTTP 404
    res_s2 = client.get(
        f"/api/v1/final-marks/student/exam/{exam_id}",
        headers=second_student_token_headers
    )
    assert res_s2.status_code == status.HTTP_404_NOT_FOUND

    # 5. Student 2 tries to directly access Student 1's submission ID -> HTTP 403
    direct_res = client.get(
        f"/api/v1/final-marks/student/results/{submission_id}",
        headers=second_student_token_headers
    )
    assert direct_res.status_code == status.HTTP_403_FORBIDDEN


def test_submission_file_serving_with_token(client, teacher_token_headers, student_token_headers):
    """
    Test Issue 2: Scanned answer sheet endpoint serves file with token query param,
    proper content-type application/pdf, and content-disposition header.
    """
    exam_id, q1_id, q2_id, submission_id, file_ref = setup_multi_question_exam_and_results(
        client, teacher_token_headers, student_token_headers
    )

    # Publish exam
    client.put(
        f"/api/v1/exams/{exam_id}",
        headers=teacher_token_headers,
        json={"status": "PUBLISHED"}
    )

    # Extract raw token string from student_token_headers
    auth_header = student_token_headers["Authorization"]
    token = auth_header.replace("Bearer ", "")

    # Request file with token query param
    file_res = client.get(f"/api/v1/submissions/{submission_id}/file?token={token}")
    assert file_res.status_code == status.HTTP_200_OK
    assert file_res.headers.get("content-type") == "application/pdf"
    assert "submission_" in file_res.headers.get("content-disposition", "")
    assert ".pdf" in file_res.headers.get("content-disposition", "")
    assert b"%PDF-1.4 test dummy content" in file_res.content


def test_tutor_chat_question_isolation_and_no_stale_fallback(client, teacher_token_headers, student_token_headers):
    """
    Test Issues 3 & 4: Tutor returns question-specific context for Q1 and Q2,
    does NOT return Q1's answer when asking about Q2, and returns 404 for non-existent question.
    """
    exam_id, q1_id, q2_id, submission_id, file_ref = setup_multi_question_exam_and_results(
        client, teacher_token_headers, student_token_headers
    )

    # Publish exam
    client.put(
        f"/api/v1/exams/{exam_id}",
        headers=teacher_token_headers,
        json={"status": "PUBLISHED"}
    )

    # Ask tutor about Q1
    q1_tutor_res = client.post(
        "/api/v1/tutor/chat",
        headers=student_token_headers,
        json={
            "exam_id": exam_id,
            "question_id": q1_id,
            "message": "Give me a model solution."
        }
    )
    assert q1_tutor_res.status_code == status.HTTP_200_OK
    q1_reply = q1_tutor_res.json()["reply"]
    assert "process" in q1_reply.lower() or "thread" in q1_reply.lower()
    # Q1 reply should NOT contain Q2's paging concept
    assert "virtual memory paging" not in q1_reply.lower()

    # Ask tutor about Q2
    q2_tutor_res = client.post(
        "/api/v1/tutor/chat",
        headers=student_token_headers,
        json={
            "exam_id": exam_id,
            "question_id": q2_id,
            "message": "Give me a model solution."
        }
    )
    assert q2_tutor_res.status_code == status.HTTP_200_OK
    q2_reply = q2_tutor_res.json()["reply"]
    assert "paging" in q2_reply.lower() or "page" in q2_reply.lower()
    # Q2 reply MUST NOT contain Q1's process/thread solution (no DELETE/TRUNCATE-like stale fallback!)
    assert "differentiate between process and thread" not in q2_reply.lower()

    # Empty rubric check: verify '• Rubric Criteria: []' is NOT present
    assert "Rubric Criteria: []" not in q1_reply
    assert "Rubric Criteria: []" not in q2_reply

    # Invalid question ID check: should return HTTP 404, NOT fall back silently to Q1
    invalid_q_res = client.post(
        "/api/v1/tutor/chat",
        headers=student_token_headers,
        json={
            "exam_id": exam_id,
            "question_id": 999999,
            "message": "Explain this."
        }
    )
    assert invalid_q_res.status_code == status.HTTP_404_NOT_FOUND
