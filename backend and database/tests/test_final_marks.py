from fastapi import status


def setup_exam_and_submission(client, teacher_token_headers, student_token_headers):
    # Create Exam
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Database Systems",
            "subject": "CS",
            "semester": 6,
            "section": 1,
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Explain 3NF Normalization.",
                    "model_answer": "No transitive dependencies; every non-prime attribute is non-transitively dependent on primary key.",
                    "max_marks": 10.0
                }
            ]
        }
    )
    exam_id = exam_res.json()["id"]
    question_id = exam_res.json()["questions"][0]["id"]

    # Student Submission
    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={"exam_id": exam_id, "file_reference": "s3://db_ans.pdf"}
    )
    submission_id = sub_res.json()["id"]

    # Student Answer text
    ans_res = client.post(
        f"/api/v1/submissions/{submission_id}/answers",
        headers=teacher_token_headers,
        json={
            "submission_id": submission_id,
            "question_id": question_id,
            "extracted_text": "3NF means no transitive dependencies exist in the table relation.",
            "ocr_confidence": 0.95
        }
    )
    answer_id = ans_res.json()["id"]

    # AI Evaluation
    client.post(
        "/api/v1/evaluations",
        headers=teacher_token_headers,
        json={
            "answer_id": answer_id,
            "similarity_score": 0.88,
            "suggested_marks": 8.5,
            "feedback": "Good definition."
        }
    )

    return submission_id, question_id, answer_id


def test_teacher_mark_approval_and_out_of_bounds_validation(
    client, teacher_token_headers, student_token_headers
):
    submission_id, question_id, answer_id = setup_exam_and_submission(
        client, teacher_token_headers, student_token_headers
    )

    # 1. Attempt to approve marks > max_marks (10.0) -> HTTP 400 Bad Request
    invalid_res = client.post(
        "/api/v1/final-marks/review",
        headers=teacher_token_headers,
        json={
            "answer_id": answer_id,
            "approved_marks": 15.0,  # Exceeds max 10.0
            "approval_status": "APPROVED",
            "reason": "Exceeding max marks"
        }
    )
    assert invalid_res.status_code == status.HTTP_400_BAD_REQUEST
    assert "must be between 0.0 and maximum marks" in invalid_res.json()["detail"]

    # 2. Attempt negative marks -> HTTP 422 Unprocessable Entity (pydantic validation)
    neg_res = client.post(
        "/api/v1/final-marks/review",
        headers=teacher_token_headers,
        json={
            "answer_id": answer_id,
            "approved_marks": -2.0,
            "approval_status": "APPROVED"
        }
    )
    assert neg_res.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    # 3. Valid Teacher Mark Approval (9.0 out of 10.0)
    valid_res = client.post(
        "/api/v1/final-marks/review",
        headers=teacher_token_headers,
        json={
            "answer_id": answer_id,
            "approved_marks": 9.0,
            "approval_status": "APPROVED",
            "reason": "Verified accuracy of relational normalization definition."
        }
    )
    assert valid_res.status_code == status.HTTP_200_OK
    assert valid_res.json()["approved_marks"] == 9.0

    # 4. Check Audit Log generated for Teacher
    audit_res = client.get("/api/v1/audit-logs", headers=teacher_token_headers)
    assert audit_res.status_code == status.HTTP_200_OK
    logs = audit_res.json()
    assert len(logs) >= 1
    assert logs[0]["action"] == "CREATE"


def test_student_cannot_modify_marks(client, student_token_headers):
    response = client.post(
        "/api/v1/final-marks/review",
        headers=student_token_headers,
        json={
            "answer_id": 1,
            "approved_marks": 10.0,
            "approval_status": "APPROVED"
        }
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_student_retrieves_authorized_final_results(
    client, teacher_token_headers, student_token_headers, second_student_token_headers
):
    submission_id, question_id, answer_id = setup_exam_and_submission(
        client, teacher_token_headers, student_token_headers
    )

    # Approve mark as teacher
    client.post(
        "/api/v1/final-marks/review",
        headers=teacher_token_headers,
        json={
            "answer_id": answer_id,
            "approved_marks": 9.5,
            "approval_status": "APPROVED",
            "reason": "Clear explanation."
        }
    )

    # Authorized student fetches results
    st_res = client.get(
        f"/api/v1/final-marks/student/results/{submission_id}",
        headers=student_token_headers
    )
    assert st_res.status_code == status.HTTP_200_OK
    data = st_res.json()
    assert data["total_final_marks"] == 9.5
    assert data["questions"][0]["final_approved_marks"] == 9.5
    assert data["questions"][0]["ai_suggested_marks"] == 8.5  # Separate AI vs Final marks

    # Unauthorized student fetches results -> HTTP 403 Forbidden
    unauth_res = client.get(
        f"/api/v1/final-marks/student/results/{submission_id}",
        headers=second_student_token_headers
    )
    assert unauth_res.status_code == status.HTTP_403_FORBIDDEN
