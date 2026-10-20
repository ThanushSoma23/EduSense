from fastapi import status


def test_create_and_read_submission(client, teacher_token_headers, student_token_headers, student_user):
    # 1. Teacher creates exam with 1 question
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Operating Systems Midterm",
            "subject": "CS",
            "semester": 6,
            "section": 1,
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
        json={"title": "Networking", "subject": "CS", "semester": 6, "section": 1}
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


def test_transcribe_submission_workflow(client, teacher_token_headers, student_token_headers, second_student_token_headers):
    # 1. Teacher creates exam with 2 questions
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Operating Systems Final",
            "subject": "CS",
            "semester": 6,
            "section": 1,
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Explain deadlock.",
                    "model_answer": "Processes wait indefinitely for resources.",
                    "max_marks": 5.0
                },
                {
                    "question_number": 2,
                    "question_text": "What is a process?",
                    "model_answer": "A program in execution.",
                    "max_marks": 5.0
                }
            ]
        }
    )
    assert exam_res.status_code == status.HTTP_201_CREATED
    exam_id = exam_res.json()["id"]

    # 2. Student submits answer sheet
    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={
            "exam_id": exam_id,
            "file_reference": "mock_sample_reference.jpg"
        }
    )
    assert sub_res.status_code == status.HTTP_201_CREATED
    sub_id = sub_res.json()["id"]

    # 3. Unauthorized student cannot transcribe
    forbidden_res = client.post(
        f"/api/v1/submissions/{sub_id}/transcribe?backend=mock",
        headers=second_student_token_headers
    )
    assert forbidden_res.status_code == status.HTTP_403_FORBIDDEN

    # 4. Authorized teacher transcribes submission
    transcribe_res = client.post(
        f"/api/v1/submissions/{sub_id}/transcribe?backend=mock",
        headers=teacher_token_headers
    )
    assert transcribe_res.status_code == status.HTTP_200_OK
    data = transcribe_res.json()
    assert data["submission_id"] == sub_id
    assert data["processing_status"] == "EXTRACTED"
    assert data["total_questions"] >= 2
    assert "overall_confidence" in data
    assert "backend_used" in data

    # 5. Verify answers persisted in submission details
    detail_res = client.get(
        f"/api/v1/submissions/{sub_id}",
        headers=teacher_token_headers
    )
    assert detail_res.status_code == status.HTTP_200_OK
    detail_data = detail_res.json()
    assert detail_data["processing_status"] == "EXTRACTED"
    assert len(detail_data["answers"]) >= 2

    # 6. Idempotent retry: transcribing again updates without duplicate key errors
    retry_res = client.post(
        f"/api/v1/submissions/{sub_id}/transcribe?backend=mock",
        headers=teacher_token_headers
    )
    assert retry_res.status_code == status.HTTP_200_OK
