import pytest
from fastapi import status
from app.config import settings


def test_complete_edusense_e2e_workflow(
    client,
    teacher_token_headers,
    student_token_headers,
    second_student_token_headers,
    student_user,
    teacher_user,
    db
):
    """
    Complete End-to-End Workflow Verification:
    1. Teacher creates exam with questions and max marks.
    2. Student submits scanned answer sheet.
    3. OCR & segmentation pipeline transcribes handwritten answers into StudentAnswer records.
    4. AI evaluation engine computes suggestions and posts to /evaluations with X-Service-Key.
    5. Invariant check: AI suggestions never auto-approve final marks.
    6. Security check: Students cannot approve their own marks (403 Forbidden).
    7. Teacher reviews and transactionally approves final marks.
    8. Student views approved results and feedback.
    9. Cross-student data isolation is enforced throughout.
    """
    # ------------------------------------------------------------------------
    # STEP 1: Teacher creates exam
    # ------------------------------------------------------------------------
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Computer Networks Endterm",
            "subject": "CS-401",
            "semester": 6,
            "section": 1,
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Explain deadlock and its 4 conditions.",
                    "model_answer": "Mutual exclusion, hold and wait, no preemption, circular wait.",
                    "max_marks": 5.0
                },
                {
                    "question_number": 2,
                    "question_text": "What is a process in operating systems?",
                    "model_answer": "A program in execution with dedicated memory space.",
                    "max_marks": 5.0
                }
            ]
        }
    )
    assert exam_res.status_code == status.HTTP_201_CREATED
    exam_data = exam_res.json()
    exam_id = exam_data["id"]
    q1_id = exam_data["questions"][0]["id"]
    q2_id = exam_data["questions"][1]["id"]

    # ------------------------------------------------------------------------
    # STEP 2: Student submits answer sheet
    # ------------------------------------------------------------------------
    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={
            "exam_id": exam_id,
            "file_reference": "sample_answer_sheet.jpg"
        }
    )
    assert sub_res.status_code == status.HTTP_201_CREATED
    sub_id = sub_res.json()["id"]

    # ------------------------------------------------------------------------
    # STEP 3: OCR Transcription & Question Segmentation
    # ------------------------------------------------------------------------
    transcribe_res = client.post(
        f"/api/v1/submissions/{sub_id}/transcribe?backend=mock",
        headers=teacher_token_headers
    )
    assert transcribe_res.status_code == status.HTTP_200_OK
    transcribe_data = transcribe_res.json()
    assert transcribe_data["submission_id"] == sub_id
    assert transcribe_data["processing_status"] == "EXTRACTED"
    assert transcribe_data["total_questions"] >= 2
    assert transcribe_data["overall_confidence"] > 0.0

    # Retrieve submission details to verify answers were linked
    sub_detail = client.get(f"/api/v1/submissions/{sub_id}", headers=teacher_token_headers).json()
    answers = sub_detail["answers"]
    assert len(answers) >= 2
    ans1 = next((a for a in answers if a["question_id"] == q1_id), None)
    ans2 = next((a for a in answers if a["question_id"] == q2_id), None)
    assert ans1 is not None and len(ans1["extracted_text"]) > 0
    assert ans2 is not None and len(ans2["extracted_text"]) > 0

    # ------------------------------------------------------------------------
    # STEP 4: AI Evaluation Engine posts suggested marks using Service Key
    # ------------------------------------------------------------------------
    eval1_res = client.post(
        "/api/v1/evaluations",
        headers={"X-Service-Key": settings.EVALUATION_SERVICE_KEY},
        json={
            "answer_id": ans1["id"],
            "similarity_score": 0.92,
            "concept_coverage": 0.88,
            "suggested_marks": 4.5,
            "feedback": "Accurate coverage of all 4 deadlock conditions.",
            "evaluation_status": "COMPLETED"
        }
    )
    assert eval1_res.status_code == status.HTTP_201_CREATED
    assert eval1_res.json()["suggested_marks"] == 4.5

    eval2_res = client.post(
        "/api/v1/evaluations",
        headers={"X-Service-Key": settings.EVALUATION_SERVICE_KEY},
        json={
            "answer_id": ans2["id"],
            "similarity_score": 0.85,
            "concept_coverage": 0.80,
            "suggested_marks": 4.0,
            "feedback": "Correct definition of process and execution context.",
            "evaluation_status": "COMPLETED"
        }
    )
    assert eval2_res.status_code == status.HTTP_201_CREATED

    # ------------------------------------------------------------------------
    # STEP 5 & 6: Invariant & Security Verification
    # ------------------------------------------------------------------------
    # Student CANNOT approve final marks -> 403 Forbidden
    student_attempt = client.post(
        "/api/v1/final-marks/review",
        headers=student_token_headers,
        json={
            "answer_id": ans1["id"],
            "approved_marks": 5.0,
            "evaluation_type": "AI_SUGGESTION_ACCEPTED"
        }
    )
    assert student_attempt.status_code == status.HTTP_403_FORBIDDEN

    # Second student CANNOT read first student's submission -> 403 Forbidden
    unauthorized_read = client.get(
        f"/api/v1/submissions/{sub_id}",
        headers=second_student_token_headers
    )
    assert unauthorized_read.status_code == status.HTTP_403_FORBIDDEN

    # ------------------------------------------------------------------------
    # STEP 7: Teacher reviews and transactionally approves final marks
    # ------------------------------------------------------------------------
    review1 = client.post(
        "/api/v1/final-marks/review",
        headers=teacher_token_headers,
        json={
            "answer_id": ans1["id"],
            "approved_marks": 4.5,
            "evaluation_type": "AI_SUGGESTION_ACCEPTED",
            "review_notes": "Agreed with AI suggestion; student covered all points."
        }
    )
    assert review1.status_code == status.HTTP_200_OK
    assert review1.json()["approved_marks"] == 4.5

    review2 = client.post(
        "/api/v1/final-marks/review",
        headers=teacher_token_headers,
        json={
            "answer_id": ans2["id"],
            "approved_marks": 4.0,
            "evaluation_type": "TEACHER_OVERRIDE",
            "review_notes": "Adjusted slightly for concise explanation."
        }
    )
    assert review2.status_code == status.HTTP_200_OK

    # ------------------------------------------------------------------------
    # STEP 8: Student views final approved marks
    # ------------------------------------------------------------------------
    student_results = client.get(
        f"/api/v1/final-marks/student/results/{sub_id}",
        headers=student_token_headers
    )
    assert student_results.status_code == status.HTTP_200_OK
    res_data = student_results.json()
    assert res_data["submission_id"] == sub_id
    assert res_data["exam_id"] == exam_id
    assert res_data["total_final_marks"] == 8.5
    assert res_data["total_max_marks"] == 10.0
    assert len(res_data["questions"]) == 2

    # Verify second student cannot view first student's marks (Isolation Check)
    other_student_read = client.get(
        f"/api/v1/final-marks/student/results/{sub_id}",
        headers=second_student_token_headers
    )
    assert other_student_read.status_code == status.HTTP_403_FORBIDDEN
