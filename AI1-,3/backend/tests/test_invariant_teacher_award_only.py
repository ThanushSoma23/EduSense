import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.supabase import db
from app.core.config import settings

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_seed_answer():
    # Ensure answer and question exist for test (Question ID matches seed.sql: a1111111-1111-1111-1111-111111111111)
    ans_id = "ans-test-1111-1111-1111-111111111111"
    q_id = "a1111111-1111-1111-1111-111111111111"
    db.answers[ans_id] = {
        "id": ans_id,
        "sheet_id": "s1111111-1111-1111-1111-111111111111",
        "question_id": q_id,
        "text": "A binary search tree starts at root node.",
        "ocr_confidence": 0.98,
        "needs_review": False
    }

def test_teacher_can_award_marks():
    ans_id = "ans-test-1111-1111-1111-111111111111"
    headers = {"Authorization": "Bearer dev-token-teacher"}
    payload = {"final_marks": 4.5, "award_source": "manual", "remarks": "Excellent answer"}
    res = client.post(f"/api/v1/marks/{ans_id}/award", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["mark"]["final_marks"] == 4.5

def test_student_cannot_award_marks_returns_403():
    ans_id = "ans-test-1111-1111-1111-111111111111"
    headers = {"Authorization": "Bearer dev-token-student"}
    payload = {"final_marks": 5.0, "award_source": "manual"}
    res = client.post(f"/api/v1/marks/{ans_id}/award", json=payload, headers=headers)
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

def test_unauthenticated_award_attempt_returns_401():
    ans_id = "ans-test-1111-1111-1111-111111111111"
    payload = {"final_marks": 5.0, "award_source": "manual"}
    res = client.post(f"/api/v1/marks/{ans_id}/award", json=payload)
    assert res.status_code == 401

def test_dev_tokens_rejected_when_app_env_not_dev(monkeypatch):
    ans_id = "ans-test-1111-1111-1111-111111111111"
    monkeypatch.setattr(settings, "APP_ENV", "production")
    headers = {"Authorization": "Bearer dev-token-teacher"}
    payload = {"final_marks": 4.5, "award_source": "manual"}
    res = client.post(f"/api/v1/marks/{ans_id}/award", json=payload, headers=headers)
    assert res.status_code == 401
    assert "disabled" in res.json()["detail"].lower()

def test_prod_env_with_missing_supabase_fails_loudly(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_KEY", "")

    from app.db.supabase import init_db
    with pytest.raises(RuntimeError) as exc_info:
        init_db()
    assert "FATAL" in str(exc_info.value)
    assert "production" in str(exc_info.value)

def test_direct_db_award_by_non_teacher_rejected():
    ans_id = "ans-test-1111-1111-1111-111111111111"
    with pytest.raises(ValueError) as exc_info:
        db.award_marks(
            answer_id=ans_id,
            final_marks=5.0,
            awarded_by="22222222-2222-2222-2222-222222222222" # Student ID
        )
    assert "Unauthorized" in str(exc_info.value)
