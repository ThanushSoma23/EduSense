from fastapi import status


def test_create_exam_as_teacher(client, teacher_token_headers):
    response = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Data Structures & Algorithms Final Exam",
            "subject": "Computer Science",
            "semester": 6,
            "section": 1,
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Explain Binary Search Tree insertion algorithm.",
                    "model_answer": "Compare target with node key, recurse left if smaller, right if larger.",
                    "max_marks": 10.0,
                    "rubric": "Correct comparison (4m), recursion/iteration (4m), base case (2m)."
                },
                {
                    "question_number": 2,
                    "question_text": "What is the time complexity of QuickSort average vs worst case?",
                    "model_answer": "Average: O(N log N), Worst: O(N^2) when pivot is min/max.",
                    "max_marks": 5.0
                }
            ]
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Data Structures & Algorithms Final Exam"
    assert data["semester"] == 6
    assert data["section"] == 1
    assert len(data["questions"]) == 2
    assert data["questions"][0]["question_number"] == 1
    assert data["questions"][0]["max_marks"] == 10.0


def test_create_exam_as_student_forbidden(client, student_token_headers):
    response = client.post(
        "/api/v1/exams",
        headers=student_token_headers,
        json={
            "title": "Unauthorized Exam",
            "subject": "Physics",
            "semester": 6,
            "section": 1
        }
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_add_question_to_exam(client, teacher_token_headers):
    # 1. Create Exam
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={"title": "Linear Algebra", "subject": "Mathematics", "semester": 6, "section": 1}
    )
    exam_id = exam_res.json()["id"]

    # 2. Add question
    q_res = client.post(
        f"/api/v1/exams/{exam_id}/questions",
        headers=teacher_token_headers,
        json={
            "question_number": 1,
            "question_text": "Define Matrix Rank.",
            "model_answer": "The maximum number of linearly independent column vectors.",
            "max_marks": 5.0
        }
    )
    assert q_res.status_code == status.HTTP_201_CREATED
    assert q_res.json()["question_number"] == 1

    # 3. Add duplicate question number should fail
    dup_res = client.post(
        f"/api/v1/exams/{exam_id}/questions",
        headers=teacher_token_headers,
        json={
            "question_number": 1,
            "question_text": "Duplicate Q1",
            "model_answer": "Dummy",
            "max_marks": 5.0
        }
    )
    assert dup_res.status_code == status.HTTP_400_BAD_REQUEST
