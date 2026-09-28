import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.supabase import db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_tutor_test_data():
    exam_id = "exam-tutor-test"
    student1_id = "22222222-2222-2222-2222-222222222222"
    q_id = "q-tutor-1"

    # Reset rate limiter
    from app.core.rate_limiter import auth_rate_limiter
    auth_rate_limiter.history.clear()

    db.profiles[student1_id] = {
        "id": student1_id,
        "full_name": "Tutor Student 1",
        "email": "tutor_student1@stanford.edu",
        "role": "student",
        "status": "active"
    }

    db.exams[exam_id] = {"id": exam_id, "title": "Tutor Test Exam", "subject": "CS-101"}
    db.questions[q_id] = {"id": q_id, "exam_id": exam_id, "text": "What is RAM?", "max_marks": 5.0}

    db.answer_sheets["sheet-tutor-1"] = {
        "id": "sheet-tutor-1",
        "exam_id": exam_id,
        "student_id": student1_id,
        "status": "ready"
    }

    # Clear publications & tutor messages
    db.publications.clear()
    if hasattr(db, "tutor_messages"):
        db.tutor_messages.clear()

def test_tutor_refuses_before_publication():
    """Verify AI Tutor refuses requests before exam results are published."""
    headers = {"Authorization": "Bearer dev-token-student"}
    payload = {
        "exam_id": "exam-tutor-test",
        "question_id": "q-tutor-1",
        "message": "Why did I lose marks?"
    }

    res = client.post("/api/v1/tutor/chat", json=payload, headers=headers)
    assert res.status_code == 403
    assert "not been published" in res.json()["detail"].lower()

def test_tutor_no_fabricated_citations_when_kb_empty():
    """Verify tutor returns explicit no-citation message when KB is empty."""
    exam_id = "exam-tutor-test"
    student_id = "22222222-2222-2222-2222-222222222222"

    # Mark exam as published
    db.publications["pub-1"] = {"id": "pub-1", "exam_id": exam_id, "published_by": "11111111-1111-1111-1111-111111111111"}
    db.answer_sheets["sheet-tutor-1"]["student_id"] = student_id

    headers = {"Authorization": "Bearer dev-token-student"}
    payload = {
        "exam_id": exam_id,
        "question_id": "q-tutor-1",
        "message": "Teach me advanced quantum computing"
    }

    res = client.post("/api/v1/tutor/chat", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["citations"] == []
    assert "no matching reference passages were found" in data["reply"].lower()
