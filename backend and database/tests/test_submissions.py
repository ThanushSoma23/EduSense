from fastapi import status


def test_create_and_read_submission(client, teacher_token_headers, student_token_headers, student_user):
    # 1. Teacher creates exam with 1 question
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Operating Systems Midterm",
            "subject": "CS",
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Define process deadlocks and 4 necessary conditions.",
                    "model_answer": "Mutual exclusion, Hold and wait, No preemption, Circular wait.",
                    "max_marks": 10.0
                }
            ]
        }
    )
    exam_id = exam_res.json()["id"]
    question_id = exam_res.json()["questions"][0]["id"]

    # 2. Student submits answer sheet record
    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={
            "exam_id": exam_id,
            "file_reference": "https://s3.amazonaws.com/edusense-bucket/answer_sheet_101.pdf"
        }
    )
    assert sub_res.status_code == status.HTTP_201_CREATED
    sub_data = sub_res.json()
    submission_id = sub_data["id"]
    assert sub_data["student_id"] == student_user.id
    assert sub_data["processing_status"] == "PENDING"

    # 3. Duplicate submission by same student should be rejected
    dup_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={
            "exam_id": exam_id,
            "file_reference": "https://s3.amazonaws.com/edusense-bucket/answer_sheet_101_dup.pdf"
        }
    )
    assert dup_res.status_code == status.HTTP_400_BAD_REQUEST

    # 4. Record student extracted answer
    ans_res = client.post(
        f"/api/v1/submissions/{submission_id}/answers",
        headers=teacher_token_headers,
        json={
            "submission_id": submission_id,
            "question_id": question_id,
            "extracted_text": "Deadlock happens when processes wait indefinitely. Conditions: Mutual exclusion, hold wait, no preemption, circular wait.",
            "ocr_confidence": 0.96,
            "extraction_status": "SUCCESS"
        }
    )
    assert ans_res.status_code == status.HTTP_201_CREATED
    assert ans_res.json()["ocr_confidence"] == 0.96


def test_student_isolation_forbidden(client, teacher_token_headers, student_token_headers, second_student_token_headers):
    # Create Exam & Submission for student 1
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "Networking", "subject": "CS"}
    )
    exam_id = exam_res.json()["id"]

    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={"exam_id": exam_id, "file_reference": "s3://net_sub_1.pdf"}
    )
    sub_id = sub_res.json()["id"]

    # Student 2 tries to access Student 1 submission -> HTTP 403 Forbidden
    access_res = client.get(
        f"/api/v1/submissions/{sub_id}",
        headers=second_student_token_headers
    )
    assert access_res.status_code == status.HTTP_403_FORBIDDEN
