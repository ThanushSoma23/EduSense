import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.supabase import db
from app.core.config import settings

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_college_and_limiter():
    c_id = "c1111111-1111-1111-1111-111111111111"
    db.colleges[c_id] = {
        "id": c_id,
        "name": "Stanford Institute of Technology",
        "code": "STANFORD"
    }
    db.college_access_codes["code-1"] = {
        "id": "code-1",
        "college_id": c_id,
        "code": "TEACH2026",
        "is_active": True
    }
    # Reset rate limiter history for clean tests
    from app.core.rate_limiter import auth_rate_limiter
    auth_rate_limiter.history.clear()

def test_teacher_registration_pending_by_default(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "dev")
    monkeypatch.setattr(settings, "AUTO_APPROVE_TEACHERS", False)

    payload = {
        "full_name": "Dr. Alan Turing",
        "email": "turing@stanford.edu",
        "password": "SecretPassword123!",
        "college_id": "c1111111-1111-1111-1111-111111111111",
        "access_code": "TEACH2026",
        "subjects": [{"subject": "Algorithms", "semester": 6}]
    }

    res = client.post("/api/v1/auth/register/teacher", json=payload)
    assert res.status_code == 200
    user = res.json()["user"]
    assert user["role"] == "teacher"
    assert user["status"] == "pending"

def test_auto_approve_teachers_ignored_when_app_env_not_dev(monkeypatch):
    # Set APP_ENV to production and AUTO_APPROVE_TEACHERS to True
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "AUTO_APPROVE_TEACHERS", True)

    payload = {
        "full_name": "Dr. Prod Teacher",
        "email": "prodteacher@stanford.edu",
        "password": "SecretPassword123!",
        "college_id": "c1111111-1111-1111-1111-111111111111",
        "access_code": "TEACH2026",
        "subjects": []
    }

    res = client.post("/api/v1/auth/register/teacher", json=payload)
    assert res.status_code == 200
    user = res.json()["user"]
    assert user["status"] == "pending"  # MUST stay pending in production mode!

def test_pending_teacher_gets_403_on_teacher_endpoints(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "dev")
    monkeypatch.setattr(settings, "AUTO_APPROVE_TEACHERS", False)

    payload = {
        "full_name": "Dr. Pending Teacher",
        "email": "pending@stanford.edu",
        "password": "SecretPassword123!",
        "college_id": "c1111111-1111-1111-1111-111111111111",
        "access_code": "TEACH2026",
        "subjects": []
    }
    reg_res = client.post("/api/v1/auth/register/teacher", json=payload)
    token = reg_res.json()["token"]

    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/exams", headers=headers)
    assert res.status_code == 403
    assert "pending" in res.json()["detail"].lower()

def test_duplicate_roll_number_in_same_college_rejected():
    c_id = "c1111111-1111-1111-1111-111111111111"
    student1 = {
        "full_name": "Student One",
        "email": "student1@stanford.edu",
        "roll_number": "ROLL-1001",
        "college_id": c_id,
        "department": "Computer Science",
        "semester": 6,
        "password": "Password123!"
    }
    res1 = client.post("/api/v1/auth/register/student", json=student1)
    assert res1.status_code == 200

    # Duplicate roll number
    student2 = {
        "full_name": "Student Two",
        "email": "student2@stanford.edu",
        "roll_number": "ROLL-1001",
        "college_id": c_id,
        "department": "Computer Science",
        "semester": 6,
        "password": "Password123!"
    }
    res2 = client.post("/api/v1/auth/register/student", json=student2)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"].lower()

def test_auth_rate_limiting():
    # Make 5 rapid login calls (limit is 5/min)
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"email": "teacher@edusense.ai", "password": "pass"})

    # 6th call should trigger 429
    res = client.post("/api/v1/auth/login", json={"email": "teacher@edusense.ai", "password": "pass"})
    assert res.status_code == 429
    assert "rate limit" in res.json()["detail"].lower()
