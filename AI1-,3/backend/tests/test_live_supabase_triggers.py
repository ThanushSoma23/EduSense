import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.db.supabase import db

client = TestClient(app)

# Live Supabase DB tests (unskipped when valid live credentials exist)
@pytest.mark.skipif(
    not settings.SUPABASE_URL or not settings.SUPABASE_KEY or "your-supabase" in settings.SUPABASE_URL,
    reason="Requires live Supabase project credentials in .env to test Postgres triggers."
)
def test_live_supabase_postgres_triggers():
    from supabase import create_client
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    student_id = "22222222-2222-2222-2222-222222222222"
    answer_id = "a1111111-1111-1111-1111-111111111111"

    # 1. (a) Service-role INSERT into public.marks with student ID MUST be rejected by trigger
    with pytest.raises(Exception) as exc_info:
        supabase.table("marks").insert({
            "answer_id": answer_id,
            "final_marks": 5.0,
            "awarded_by": student_id # Non-teacher ID
        }).execute()

    assert any(term in str(exc_info.value).lower() for term in ["unauthorized", "teacher", "violates", "exception"])

    # 1. (a) Service-role INSERT into public.marks with NULL awarded_by MUST be rejected by trigger
    with pytest.raises(Exception) as exc_null:
        supabase.table("marks").insert({
            "answer_id": answer_id,
            "final_marks": 5.0,
            "awarded_by": None
        }).execute()
    assert exc_null is not None

    # 2. Test Postgres trigger 'prevent_profile_role_status_escalation'
    if settings.SUPABASE_ANON_KEY:
        anon_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        with pytest.raises(Exception) as exc_escalation:
            anon_client.table("profiles").update({"role": "admin", "status": "active"}).eq("id", student_id).execute()
        assert exc_escalation is not None

def test_pending_teacher_gets_403_on_protected_endpoints():
    """Verify (c): pending teacher gets HTTP 403 on upload, evaluate, and kb endpoints."""
    # Reset rate limiter history for clean test execution
    from app.core.rate_limiter import auth_rate_limiter
    auth_rate_limiter.history.clear()

    # Register pending teacher

    pending_teacher_payload = {
        "full_name": "Dr. Pending Guard",
        "email": "pending_guard@stanford.edu",
        "password": "Password123!",
        "college_id": "c1111111-1111-1111-1111-111111111111",
        "access_code": "TEACH2026",
        "subjects": []
    }

    # Set AUTO_APPROVE_TEACHERS to False for test
    settings.AUTO_APPROVE_TEACHERS = False
    reg_res = client.post("/api/v1/auth/register/teacher", json=pending_teacher_payload)
    assert reg_res.status_code == 200
    token = reg_res.json()["token"]
    user = reg_res.json()["user"]

    # Explicitly set status to pending in DB
    user_id = user["id"]
    if user_id in db.profiles:
        db.profiles[user_id]["status"] = "pending"

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Sheet upload endpoint
    res_upload = client.post("/api/v1/sheets/upload", headers=headers)
    assert res_upload.status_code == 403

    # 2. Evaluate sheet endpoint
    res_eval = client.post("/api/v1/evaluate/sheet-123", headers=headers)
    assert res_eval.status_code == 403

    # 3. KB upload endpoint
    res_kb = client.post("/api/v1/kb/upload", headers=headers)
    assert res_kb.status_code == 403

def test_student_cannot_read_another_students_evaluations_or_sheets():
    """Verify (b): student cannot read another student's/tenant's evaluations or un-published results."""
    headers = {"Authorization": "Bearer dev-token-student"}
    # Attempt to read evaluation results for an answer sheet belonging to another student
    res = client.get("/api/v1/evaluate/sheet-other-student/result", headers=headers)
    # Returns 404 or 403
    assert res.status_code in [403, 404]
