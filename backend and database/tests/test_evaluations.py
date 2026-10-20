from fastapi import status


def test_ai_evaluation_storage_and_retrieval(client, teacher_token_headers, student_token_headers):
    # Setup exam, question, submission, answer
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Machine Learning",
            "subject": "AI",
            "semester": 6,
            "section": 1,
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "What is Gradient Descent?",
                    "model_answer": "Optimization algorithm to minimize loss function by taking steps proportional to negative gradient.",
                    "max_marks": 10.0
                }
            ]
        }
    )
    exam_id = exam_res.json()["id"]
    question_id = exam_res.json()["questions"][0]["id"]

    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={"exam_id": exam_id, "file_reference": "s3://ml_ans.pdf"}
    )
    submission_id = sub_res.json()["id"]

    ans_res = client.post(
        f"/api/v1/submissions/{submission_id}/answers",
        headers=teacher_token_headers,
        json={
            "submission_id": submission_id,
            "question_id": question_id,
            "extracted_text": "Gradient descent minimizes cost function using negative gradient steps.",
            "ocr_confidence": 0.98
        }
    )
    answer_id = ans_res.json()["id"]

    # Store AI evaluation result
    eval_res = client.post(
        "/api/v1/evaluations",
        headers=teacher_token_headers,
        json={
            "answer_id": answer_id,
            "similarity_score": 0.92,
            "concept_coverage": 0.90,
            "suggested_marks": 9.0,
            "feedback": "Excellent coverage of core optimization concept.",
            "supporting_references": "Matched keywords: minimize, cost function, negative gradient.",
            "evaluation_status": "COMPLETED"
        }
    )
    assert eval_res.status_code == status.HTTP_201_CREATED
    eval_data = eval_res.json()
    assert eval_data["suggested_marks"] == 9.0
    assert eval_data["similarity_score"] == 0.92

    # Retrieve evaluation by answer ID
    get_eval = client.get(f"/api/v1/evaluations/answer/{answer_id}", headers=student_token_headers)
    assert get_eval.status_code == status.HTTP_200_OK
    assert get_eval.json()["suggested_marks"] == 9.0


def test_get_nonexistent_evaluation_returns_404(client, student_token_headers):
    response = client.get("/api/v1/evaluations/answer/99999", headers=student_token_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
