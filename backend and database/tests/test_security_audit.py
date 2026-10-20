import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi import status
from app.config import Settings, settings
from app.models.user import UserRole
from app.models.final_mark import FinalMark
from app.models.audit_log import AuditLog
from app.models.evaluation import Evaluation


# -----------------------------------------------------------------------------
# FIX A: Prevent Unauthorized Teacher Registration
# -----------------------------------------------------------------------------
def test_public_registration_forces_student_role(client):
    """
    Public registration MUST NOT allow callers to self-assign teacher role.
    Role is safely forced to student.
    """
    res = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Attacker Trying Teacher Role",
            "email": "hacker@edusense.edu",
            "password": "password123",
            "role": "teacher"  # Attempting self-promotion
        }
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["role"] == UserRole.STUDENT.value  # Forced to STUDENT


def test_provision_teacher_account_security(client):
    """
    Teacher account provisioning requires valid admin key.
    """
    # 1. Invalid admin key -> 403 Forbidden
    fail_res = client.post(
        "/api/v1/auth/provision-teacher",
        json={
            "name": "Prof. Unauthorized",
            "email": "unauth_prof@edusense.edu",
            "password": "password123",
            "admin_key": "wrong-admin-key"
        }
    )
    assert fail_res.status_code == status.HTTP_403_FORBIDDEN

    # 2. Valid admin key -> 201 Created as Teacher
    success_res = client.post(
        "/api/v1/auth/provision-teacher",
        json={
            "name": "Prof. Authorized Admin Created",
            "email": "auth_prof@edusense.edu",
            "password": "password123",
            "admin_key": settings.ADMIN_SECRET_KEY
        }
    )
    assert success_res.status_code == status.HTTP_201_CREATED
    assert success_res.json()["role"] == UserRole.TEACHER.value


# -----------------------------------------------------------------------------
# FIX B: Enforce Teacher Ownership When Approving Marks
# -----------------------------------------------------------------------------
def test_teacher_ownership_enforcement_on_mark_approval(
    client, db, teacher_token_headers, teacher_user, student_token_headers
):
    """
    Teacher 2 CANNOT approve or modify marks for an exam created by Teacher 1.
    """
    from app.models.user import User
    from app.security import hash_password, create_access_token

    teacher2 = User(
        name="Prof. Second Teacher",
        email="teacher2@edusense.edu",
        password_hash=hash_password("password123"),
        role=UserRole.TEACHER,
        account_status="active"
    )
    db.add(teacher2)
    db.commit()
    t2_token = create_access_token(data={"sub": str(teacher2.id), "role": teacher2.role.value})
    t2_headers = {"Authorization": f"Bearer {t2_token}"}

    # Teacher 1 creates exam
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Teacher 1 Calculus Exam",
            "subject": "Math",
            "semester": 6,
            "section": 1,
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Integrate x^2 dx",
                    "model_answer": "x^3/3 + C",
                    "max_marks": 10.0
                }
            ]
        }
    )
    exam_id = exam_res.json()["id"]
    question_id = exam_res.json()["questions"][0]["id"]

    # Student submits
    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={"exam_id": exam_id, "file_reference": "s3://calc_sub.pdf"}
    )
    sub_id = sub_res.json()["id"]

    ans_res = client.post(
        f"/api/v1/submissions/{sub_id}/answers",
        headers=teacher_token_headers,
        json={"submission_id": sub_id, "question_id": question_id, "extracted_text": "x^3 / 3"}
    )
    answer_id = ans_res.json()["id"]

    # Teacher 2 attempts to approve marks on Teacher 1's exam -> HTTP 403 Forbidden
    unauth_review = client.post(
        "/api/v1/final-marks/review",
        headers=t2_headers,
        json={
            "answer_id": answer_id,
            "approved_marks": 10.0,
            "approval_status": "APPROVED"
        }
    )
    assert unauth_review.status_code == status.HTTP_403_FORBIDDEN
    assert "was created by another teacher" in unauth_review.json()["detail"]


# -----------------------------------------------------------------------------
# FIX C: Secure Evaluation Ingestion and Retrieval
# -----------------------------------------------------------------------------
def test_evaluation_ingestion_security_and_bounds(
    client, teacher_token_headers, student_token_headers
):
    # Setup Exam & Submission
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "AI Security",
            "subject": "CS",
            "semester": 6,
            "section": 1,
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "What is RLS?",
                    "model_answer": "Row Level Security",
                    "max_marks": 5.0
                }
            ]
        }
    )
    exam_id = exam_res.json()["id"]
    q_id = exam_res.json()["questions"][0]["id"]

    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={"exam_id": exam_id, "file_reference": "s3://rls_ans.pdf"}
    )
    sub_id = sub_res.json()["id"]

    ans_res = client.post(
        f"/api/v1/submissions/{sub_id}/answers",
        headers=teacher_token_headers,
        json={"submission_id": sub_id, "question_id": q_id, "extracted_text": "Row level security"}
    )
    ans_id = ans_res.json()["id"]

    # 1. Student attempting to post evaluation without service key -> HTTP 403 Forbidden
    student_eval_res = client.post(
        "/api/v1/evaluations",
        headers=student_token_headers,
        json={
            "answer_id": ans_id,
            "similarity_score": 0.9,
            "suggested_marks": 5.0
        }
    )
    assert student_eval_res.status_code == status.HTTP_403_FORBIDDEN

    # 2. Out of bounds similarity score (> 1.0) with service key -> HTTP 400 Bad Request / 422 Unprocessable Entity
    invalid_sim_res = client.post(
        "/api/v1/evaluations",
        headers={"X-Service-Key": settings.EVALUATION_SERVICE_KEY},
        json={
            "answer_id": ans_id,
            "similarity_score": 1.5,  # Out of bounds (> 1.0)
            "suggested_marks": 4.0
        }
    )
    assert invalid_sim_res.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    # 3. Out of bounds suggested marks (> max_marks 5.0) -> HTTP 400 Bad Request
    invalid_marks_res = client.post(
        "/api/v1/evaluations",
        headers={"X-Service-Key": settings.EVALUATION_SERVICE_KEY},
        json={
            "answer_id": ans_id,
            "similarity_score": 0.9,
            "suggested_marks": 10.0  # Exceeds question max 5.0
        }
    )
    assert invalid_marks_res.status_code == status.HTTP_400_BAD_REQUEST

    # 4. Valid evaluation via Service Key -> HTTP 201 Created
    valid_eval_res = client.post(
        "/api/v1/evaluations",
        headers={"X-Service-Key": settings.EVALUATION_SERVICE_KEY},
        json={
            "answer_id": ans_id,
            "similarity_score": 0.95,
            "concept_coverage": 0.90,
            "suggested_marks": 4.5,
            "feedback": "Great explanation."
        }
    )
    assert valid_eval_res.status_code == status.HTTP_201_CREATED


# -----------------------------------------------------------------------------
# FIX D: Remove Insecure JWT Secret Defaults & Key Separation
# -----------------------------------------------------------------------------
def test_production_config_rejects_placeholder_secrets():
    """
    Verifies that Settings raises ValueError when production environment uses weak/placeholder secret.
    """
    with pytest.raises(ValueError, match="FATAL SECURITY CONFIGURATION ERROR"):
        test_settings = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short-secret",
            ADMIN_SECRET_KEY="distinct-admin-key-32-bytes-minimum-length",
            EVALUATION_SERVICE_KEY="distinct-eval-key-32-bytes-minimum-length"
        )
        test_settings.validate_secrets()


def test_production_config_rejects_missing_or_dev_fallback_secrets():
    """
    Proves that missing production secrets or default development values fail validation in production.
    """
    with pytest.raises(ValueError, match="FATAL SECURITY CONFIGURATION ERROR"):
        test_settings = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="dev-jwt-secret-key-edusense-2026-v1-distinct",
            ADMIN_SECRET_KEY="distinct-admin-key-32-bytes-minimum-length",
            EVALUATION_SERVICE_KEY="distinct-eval-key-32-bytes-minimum-length"
        )
        test_settings.validate_secrets()


def test_distinct_keys_enforced():
    """
    Verifies that Settings rejects configuration where keys are identical.
    """
    with pytest.raises(ValueError, match="must all be strictly distinct"):
        same_key = "same-shared-secret-key-32-bytes-minimum"
        test_settings = Settings(
            ENVIRONMENT="development",
            SECRET_KEY=same_key,
            ADMIN_SECRET_KEY=same_key,
            EVALUATION_SERVICE_KEY="distinct-eval-key"
        )
        test_settings.validate_secrets()


def test_invalid_and_expired_jwt_tokens_rejected(client):
    """
    Expired and malformed JWT tokens must be rejected with 401 Unauthorized.
    """
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": "1",
        "role": "teacher",
        "exp": now - timedelta(days=1),
        "iat": now - timedelta(days=2)
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    res_exp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_exp.status_code == status.HTTP_401_UNAUTHORIZED

    wrong_key_token = jwt.encode(
        {"sub": "1", "role": "teacher", "exp": now + timedelta(hours=1)},
        "wrong-secret-key-12345",
        algorithm=settings.ALGORITHM
    )
    res_wrong = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {wrong_key_token}"})
    assert res_wrong.status_code == status.HTTP_401_UNAUTHORIZED


# -----------------------------------------------------------------------------
# FIX E: Transactional Batch Mark Reviews & Atomic Rollback
# -----------------------------------------------------------------------------
def test_batch_review_atomic_rollback_on_failure(
    client, db, teacher_token_headers, student_token_headers
):
    """
    If 1 item out of N in a batch fails validation (e.g. invalid marks),
    the ENTIRE batch MUST roll back, leaving 0 final marks and 0 audit logs created!
    """
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Batch Transaction Test Exam",
            "subject": "CS",
            "semester": 6,
            "section": 1,
            "questions": [
                {"question_number": 1, "question_text": "Q1", "model_answer": "A1", "max_marks": 10.0},
                {"question_number": 2, "question_text": "Q2", "model_answer": "A2", "max_marks": 10.0}
            ]
        }
    )
    exam_id = exam_res.json()["id"]
    q1_id = exam_res.json()["questions"][0]["id"]
    q2_id = exam_res.json()["questions"][1]["id"]

    sub_res = client.post(
        "/api/v1/submissions",
        headers=student_token_headers,
        json={"exam_id": exam_id, "file_reference": "s3://batch_sub.pdf"}
    )
    sub_id = sub_res.json()["id"]

    ans1 = client.post(f"/api/v1/submissions/{sub_id}/answers", headers=teacher_token_headers, json={"submission_id": sub_id, "question_id": q1_id, "extracted_text": "Text 1"}).json()["id"]
    ans2 = client.post(f"/api/v1/submissions/{sub_id}/answers", headers=teacher_token_headers, json={"submission_id": sub_id, "question_id": q2_id, "extracted_text": "Text 2"}).json()["id"]

    initial_marks_count = db.query(FinalMark).count()
    initial_audit_count = db.query(AuditLog).count()

    # Batch Request: Item 1 is VALID (9.0), Item 2 is INVALID (50.0 > max 10.0)
    batch_res = client.post(
        "/api/v1/final-marks/batch-review",
        headers=teacher_token_headers,
        json={
            "reviews": [
                {"answer_id": ans1, "approved_marks": 9.0, "approval_status": "APPROVED"},
                {"answer_id": ans2, "approved_marks": 50.0, "approval_status": "APPROVED"}  # INVALID!
            ]
        }
    )
    assert batch_res.status_code == status.HTTP_400_BAD_REQUEST

    # Verify ATOMIC ROLLBACK: Item 1 was NOT committed to DB!
    assert db.query(FinalMark).count() == initial_marks_count
    assert db.query(AuditLog).count() == initial_audit_count


def test_batch_review_nonexistent_record_rollback(
    client, db, teacher_token_headers, student_token_headers
):
    """
    If a batch contains a nonexistent answer_id, the complete transaction rolls back.
    """
    exam_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Batch Nonexistent Test Exam",
            "subject": "CS",
            "semester": 6,
            "section": 1,
            "questions": [{"question_number": 1, "question_text": "Q1", "model_answer": "A1", "max_marks": 10.0}]
        }
    )
    exam_id = exam_res.json()["id"]
    q1_id = exam_res.json()["questions"][0]["id"]

    sub_res = client.post("/api/v1/submissions", headers=student_token_headers, json={"exam_id": exam_id, "file_reference": "s3://b.pdf"})
    sub_id = sub_res.json()["id"]
    ans1 = client.post(f"/api/v1/submissions/{sub_id}/answers", headers=teacher_token_headers, json={"submission_id": sub_id, "question_id": q1_id, "extracted_text": "T1"}).json()["id"]

    initial_marks_count = db.query(FinalMark).count()

    batch_res = client.post(
        "/api/v1/final-marks/batch-review",
        headers=teacher_token_headers,
        json={
            "reviews": [
                {"answer_id": ans1, "approved_marks": 8.0, "approval_status": "APPROVED"},
                {"answer_id": 999999, "approved_marks": 5.0, "approval_status": "APPROVED"}  # NONEXISTENT!
            ]
        }
    )
    assert batch_res.status_code == status.HTTP_404_NOT_FOUND
    assert db.query(FinalMark).count() == initial_marks_count


# -----------------------------------------------------------------------------
# FIX F: Cross-exam Relationship Integrity
# -----------------------------------------------------------------------------
def test_cross_exam_relationship_integrity(client, teacher_token_headers, student_token_headers):
    """
    Attempting to associate a student answer with a question from Exam B when submission is for Exam A
    MUST be rejected.
    """
    exam_a = client.post("/api/v1/exams", headers=teacher_token_headers, json={"title": "Exam A", "subject": "CS", "semester": 6, "section": 1}).json()["id"]
    exam_b_res = client.post(
        "/api/v1/exams",
        headers=teacher_token_headers,
        json={
            "title": "Exam B",
            "subject": "CS",
            "semester": 6,
            "section": 1,
            "questions": [{"question_number": 1, "question_text": "QB", "model_answer": "AB", "max_marks": 10.0}]
        }
    )
    qb_id = exam_b_res.json()["questions"][0]["id"]

    sub_a = client.post("/api/v1/submissions", headers=student_token_headers, json={"exam_id": exam_a, "file_reference": "s3://sub_a.pdf"}).json()["id"]

    mismatch_res = client.post(
        f"/api/v1/submissions/{sub_a}/answers",
        headers=teacher_token_headers,
        json={
            "submission_id": sub_a,
            "question_id": qb_id,
            "extracted_text": "Cross exam attempt"
        }
    )
    assert mismatch_res.status_code == status.HTTP_400_BAD_REQUEST
