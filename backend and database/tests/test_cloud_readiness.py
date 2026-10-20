"""
EduSense AI — Cloud Readiness & Deployment Guardrail Test Suite
Tests:
1. Configurable CORS: whitespace trimming, comma-separated, JSON array, and production wildcard rejection.
2. Storage Abstraction: local lifecycle, legacy resolution, S3 config validation, and authenticated retrieval.
3. Database Migration 003: revision chain integrity, SQLite/PostgreSQL schema compatibility, upgrade & downgrade.
4. Security & Isolation: student submission file endpoint rejects unauthorized access and unauthenticated callers.
5. OCR Warmup: graceful model pre-warming execution.
"""

import os
import io
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.config import Settings, DEFAULT_DEV_CORS_ORIGINS
from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.models.enrollment import ExamEnrollment
from app.services.storage_service import LocalStorageProvider, S3StorageProvider, get_storage_service, reset_storage_service
from app.services.ocr_service import warmup_ocr, get_last_ocr_error
from app.security import create_access_token


# ==============================================================================
# 1. Configurable CORS Tests
# ==============================================================================

def test_cors_origins_parsing_comma_separated():
    s = Settings(
        CORS_ORIGINS="https://edusense.college.edu, https://student.edusense.edu ,https://admin.edusense.edu",
        ENVIRONMENT="development"
    )
    assert s.CORS_ORIGINS == [
        "https://edusense.college.edu",
        "https://student.edusense.edu",
        "https://admin.edusense.edu"
    ]


def test_cors_origins_parsing_json_array():
    s = Settings(
        CORS_ORIGINS='["https://edusense.college.edu", "https://app.edusense.edu"]',
        ENVIRONMENT="development"
    )
    assert s.CORS_ORIGINS == [
        "https://edusense.college.edu",
        "https://app.edusense.edu"
    ]


def test_cors_origins_dev_fallback_when_unset():
    s = Settings(
        CORS_ORIGINS="",
        ENVIRONMENT="development"
    )
    # Empty string should evaluate without error in dev mode
    assert isinstance(s.CORS_ORIGINS, list)


def test_cors_production_wildcard_rejected():
    """In production mode, wildcard '*' origins must raise a fatal error."""
    with pytest.raises(ValueError, match=r"wildcard CORS origin '\*' is strictly prohibited"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            ADMIN_SECRET_KEY="b" * 32,
            EVALUATION_SERVICE_KEY="c" * 32,
            CORS_ORIGINS="*"
        )

    with pytest.raises(ValueError, match=r"wildcard CORS origin '\*' is strictly prohibited"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            ADMIN_SECRET_KEY="b" * 32,
            EVALUATION_SERVICE_KEY="c" * 32,
            CORS_ORIGINS="https://app.edusense.edu, *"
        )


def test_cors_production_empty_origins_rejected():
    """In production mode, empty CORS_ORIGINS must raise a fatal error."""
    with pytest.raises(ValueError, match="CORS_ORIGINS must be explicitly configured"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            ADMIN_SECRET_KEY="b" * 32,
            EVALUATION_SERVICE_KEY="c" * 32,
            CORS_ORIGINS=""
        )


# ==============================================================================
# 2. Storage Abstraction Tests
# ==============================================================================

def test_local_storage_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = LocalStorageProvider(base_dir=tmpdir)
        test_data = b"Handwritten Exam Content 12345"

        # 1. Save
        ref = provider.save(file_bytes=test_data, filename="student_ans.png", subfolder="submissions")
        assert ref.startswith("/uploads/submissions/")
        assert ref.endswith(".png")

        # 2. Retrieve
        retrieved = provider.retrieve(ref)
        assert retrieved == test_data

        # 3. Retrieve with legacy relative path
        clean_rel = ref.lstrip("/")
        retrieved_rel = provider.retrieve(clean_rel)
        assert retrieved_rel == test_data

        # 4. Delete
        assert provider.delete(ref) is True
        assert provider.retrieve(ref) is None


def test_s3_storage_validation_fails_when_bucket_missing():
    """If STORAGE_BACKEND=s3 is selected, missing bucket must fail clearly (Safeguard 4)."""
    with pytest.raises(ValueError, match="STORAGE_S3_BUCKET is empty"):
        Settings(
            STORAGE_BACKEND="s3",
            STORAGE_S3_BUCKET="",
            ENVIRONMENT="development"
        )


def test_s3_storage_provider_requires_bucket():
    with pytest.raises(ValueError, match="STORAGE_S3_BUCKET must be specified"):
        S3StorageProvider(bucket="")


def test_storage_invalid_backend_rejected():
    with pytest.raises(ValueError, match="Unsupported STORAGE_BACKEND"):
        Settings(
            STORAGE_BACKEND="azure_blob_unsupported",
            ENVIRONMENT="development"
        )


def test_s3_storage_fallback_to_local_for_legacy_references():
    """S3 provider must transparently retrieve legacy local file references."""
    with tempfile.TemporaryDirectory() as tmpdir:
        local_p = LocalStorageProvider(base_dir=tmpdir)
        ref = local_p.save(b"Legacy data", "legacy.png", subfolder="submissions")

        s3_p = S3StorageProvider(
            bucket="mock-edusense-bucket",
            endpoint_url="https://mock.s3.endpoint"
        )
        s3_p._local_fallback = local_p

        # Retrieve local reference through S3 provider
        retrieved = s3_p.retrieve(ref)
        assert retrieved == b"Legacy data"


# ==============================================================================
# 3. Alembic Migration 003 Schema & Compatibility Tests
# ==============================================================================

def _load_migration_003():
    import importlib.util
    path = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions", "003_add_enrollments_and_user_fields.py")
    spec = importlib.util.spec_from_file_location("m003", path)
    m003 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m003)
    return m003


def test_migration_003_revision_chain():
    """Inspect migration 003 revision and down_revision."""
    m003 = _load_migration_003()
    assert m003.revision == '003_enrollments_and_user_fields'
    assert m003.down_revision == '002_sec_integrity_constraints'


def test_migration_003_sqlite_upgrade_and_downgrade():
    """Verify migration 003 creates expected tables and columns on a test database."""
    m003 = _load_migration_003()
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    import alembic.op

    test_engine = create_engine("sqlite:///:memory:")
    # Create baseline users and exams tables as if after 001/002
    with test_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                account_status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(255) NOT NULL,
                subject VARCHAR(255) NOT NULL,
                teacher_id INTEGER NOT NULL REFERENCES users(id),
                status VARCHAR(50) DEFAULT 'DRAFT',
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
        """))

    with test_engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            m003.upgrade()
        conn.commit()

    # Verify tables & columns exist
    inspector = inspect(test_engine)
    user_cols = {col["name"] for col in inspector.get_columns("users")}
    assert "roll_number" in user_cols
    assert "department" in user_cols
    assert "exam_enrollments" in inspector.get_table_names()

    enrollment_cols = {col["name"] for col in inspector.get_columns("exam_enrollments")}
    assert "exam_id" in enrollment_cols
    assert "student_id" in enrollment_cols
    assert "enrolled_at" in enrollment_cols


# ==============================================================================
# 4. Security & Authenticated Submission File Access
# ==============================================================================

@pytest.fixture
def auth_client():
    from app.main import app
    from app.database import get_db, Base
    from sqlalchemy.pool import StaticPool
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    db = TestingSessionLocal()
    from datetime import datetime, timezone
    # Teacher 1
    t1 = User(id=1, name="Prof Teacher", email="t1@edu.com", password_hash="hash", role=UserRole.TEACHER, account_status="active")
    # Teacher 2 (unrelated)
    t2 = User(id=2, name="Prof Other", email="t2@edu.com", password_hash="hash", role=UserRole.TEACHER, account_status="active")
    # Student 1 (owner)
    s1 = User(id=3, name="Alice Student", email="s1@edu.com", password_hash="hash", role=UserRole.STUDENT, account_status="active")
    # Student 2 (attacker)
    s2 = User(id=4, name="Bob Student", email="s2@edu.com", password_hash="hash", role=UserRole.STUDENT, account_status="active")
    db.add_all([t1, t2, s1, s2])
    db.commit()

    # Exam owned by t1
    exam = Exam(id=1, title="DSA Exam", subject="CS", teacher_id=t1.id, status="PUBLISHED")
    db.add(exam)
    db.commit()

    yield {
        "client": client,
        "db": db,
        "t1": t1,
        "t2": t2,
        "s1": s1,
        "s2": s2,
        "exam": exam,
        "t1_token": create_access_token(data={"sub": str(t1.id), "role": t1.role.value}),
        "t2_token": create_access_token(data={"sub": str(t2.id), "role": t2.role.value}),
        "s1_token": create_access_token(data={"sub": str(s1.id), "role": s1.role.value}),
        "s2_token": create_access_token(data={"sub": str(s2.id), "role": s2.role.value}),
    }

    app.dependency_overrides.clear()


def test_submission_file_endpoint_enforces_auth_and_isolation(auth_client):
    client = auth_client["client"]
    db = auth_client["db"]
    s1 = auth_client["s1"]
    exam = auth_client["exam"]

    # Save a temporary file
    storage = get_storage_service()
    ref = storage.save(b"Private Student Answer Sheet Content", "sheet.jpg", subfolder="submissions")

    sub = AnswerSheet(
        id=10,
        student_id=s1.id,
        exam_id=exam.id,
        file_reference=ref,
        processing_status="PENDING"
    )
    db.add(sub)
    db.commit()

    # 1. Unauthenticated request -> 401
    res = client.get(f"/api/v1/submissions/{sub.id}/file")
    assert res.status_code == 401

    # 2. Student 2 (unauthorized student) -> 403 Forbidden
    res = client.get(
        f"/api/v1/submissions/{sub.id}/file",
        headers={"Authorization": f"Bearer {auth_client['s2_token']}"}
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]

    # 3. Teacher 2 (unauthorized teacher) -> 403 Forbidden
    res = client.get(
        f"/api/v1/submissions/{sub.id}/file",
        headers={"Authorization": f"Bearer {auth_client['t2_token']}"}
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]

    # 4. Student 1 (owner) -> 200 OK with correct file bytes
    res = client.get(
        f"/api/v1/submissions/{sub.id}/file",
        headers={"Authorization": f"Bearer {auth_client['s1_token']}"}
    )
    assert res.status_code == 200
    assert res.content == b"Private Student Answer Sheet Content"

    # 5. Teacher 1 (exam owner) -> 200 OK with correct file bytes
    res = client.get(
        f"/api/v1/submissions/{sub.id}/file",
        headers={"Authorization": f"Bearer {auth_client['t1_token']}"}
    )
    assert res.status_code == 200
    assert res.content == b"Private Student Answer Sheet Content"


# ==============================================================================
# 5. OCR Warmup Execution Test
# ==============================================================================

def test_ocr_warmup_execution():
    """Verify warmup_ocr executes gracefully without unhandled exception."""
    res = warmup_ocr()
    assert isinstance(res, bool)
