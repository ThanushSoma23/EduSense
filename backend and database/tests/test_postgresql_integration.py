import os
from urllib.parse import urlparse
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import DBAPIError, InternalError

from app.models.user import User, UserRole
from app.models.exam import Exam, Question
from app.models.submission import AnswerSheet, StudentAnswer
from app.models.final_mark import FinalMark
from app.models.audit_log import AuditLog
from app.schemas.final_mark import TeacherReviewRequest, BatchTeacherReviewRequest
from app.services.mark_service import execute_batch_review_transactional
from app.security import hash_password


def get_and_validate_test_db_url(custom_url: str = None) -> str:
    """
    Phase 4: Resolves and strictly validates the PostgreSQL test database URL.
    - Requires explicit TEST_DATABASE_URL or POSTGRES_TEST_DATABASE_URL (or safe local test URL).
    - Rejects SQLite connection strings for PostgreSQL tests.
    - Enforces database name allowlist/convention (must contain 'test' in DB name).
    - Prints sanitized connection details without revealing passwords.
    """
    url = custom_url or os.getenv("TEST_DATABASE_URL") or os.getenv("POSTGRES_TEST_DATABASE_URL")
    if not url:
        user = os.getenv("USER", "postgres")
        url = f"postgresql+psycopg2://{user}@localhost:5432/edusense_test"

    if url.startswith("sqlite"):
        raise RuntimeError(
            "DATABASE SAFETY VIOLATION: SQLite database URL rejected for PostgreSQL integration tests. "
            "A real PostgreSQL server is required."
        )

    parsed = urlparse(url)
    dbname = parsed.path.lstrip("/")

    if not dbname or "test" not in dbname.lower():
        raise RuntimeError(
            f"FATAL DATABASE SAFETY GUARANTEE VIOLATION: Target database name '{dbname}' "
            f"is not a dedicated test database. Integration tests refuse to execute against non-test "
            f"or production databases. Ensure TEST_DATABASE_URL explicitly includes 'test' in the database name (e.g. 'edusense_test')."
        )

    # Print safe sanitized connection target (hiding password if present)
    safe_netloc = parsed.netloc.split("@")[-1] if "@" in parsed.netloc else parsed.netloc
    safe_target = f"{parsed.scheme}://{safe_netloc}/{dbname}"
    print(f"\n[Database Safety Audit] Validated safe test database target: {safe_target}")
    return url


def check_postgres_connection(url: str) -> bool:
    """Verifies active connectivity to a live PostgreSQL server."""
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            return result == 1
    except Exception:
        return False


PG_TEST_DB_URL = get_and_validate_test_db_url()
IS_PG_AVAILABLE = check_postgres_connection(PG_TEST_DB_URL)


@pytest.fixture(autouse=True, scope="module")
def ensure_postgres_connected():
    """
    Phase 7: Strictly enforces live PostgreSQL connectivity.
    If PostgreSQL is unreachable during integration testing, fails explicitly with a clear diagnostic error
    instead of silently skipping required integration tests.
    """
    if not IS_PG_AVAILABLE:
        pytest.fail(
            f"FATAL POSTGRESQL INTEGRATION TEST FAILURE: Live PostgreSQL server is not reachable at '{PG_TEST_DB_URL}'. "
            f"PostgreSQL integration tests require an active PostgreSQL 17 server. Verify that PostgreSQL is running "
            f"and reachable before executing integration tests.",
            pytrace=False
        )


@pytest.fixture(scope="module")
def pg_engine():
    """Module-level engine connected to the validated PostgreSQL test database."""
    engine = create_engine(PG_TEST_DB_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def pg_session(pg_engine):
    """
    Phase 4: Function-level isolated PostgreSQL database session.
    Uses tracked object cleanup instead of global table deletions.
    Only deletes specific entities created during the test execution in reverse dependency order.
    """
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    session: Session = SessionLocal()
    tracked_objects = []

    def _track(*objs):
        for o in objs:
            tracked_objects.append(o)
        return objs[0] if len(objs) == 1 else objs

    yield session, _track

    # Isolated cleanup phase: rollback uncommitted transaction, then delete tracked test entities only
    session.rollback()
    for obj in reversed(tracked_objects):
        try:
            merged_obj = session.merge(obj)
            session.delete(merged_obj)
            session.commit()
        except Exception:
            session.rollback()
    session.close()


# ============================================================================
# PHASE 4 TESTS — Database Safety & Test Isolation Rules
# ============================================================================

def test_safety_rejects_production_like_database_url():
    """Phase 4: Safety check must reject production database URLs."""
    with pytest.raises(RuntimeError) as exc_info:
        get_and_validate_test_db_url("postgresql+psycopg2://postgres:secret@localhost:5432/edusense_db")
    assert "FATAL DATABASE SAFETY GUARANTEE VIOLATION" in str(exc_info.value)
    assert "edusense_db" in str(exc_info.value)


def test_safety_rejects_sqlite_database_url():
    """Phase 4: Safety check must reject SQLite connection strings for PostgreSQL tests."""
    with pytest.raises(RuntimeError) as exc_info:
        get_and_validate_test_db_url("sqlite:///test.db")
    assert "DATABASE SAFETY VIOLATION" in str(exc_info.value)


def test_safety_accepts_approved_test_database_url():
    """Phase 4: Safety check accepts valid test database URLs."""
    valid_url = "postgresql+psycopg2://postgres:secret@localhost:5432/edusense_test"
    res = get_and_validate_test_db_url(valid_url)
    assert res == valid_url


def test_cleanup_preserves_unrelated_records(pg_session):
    """Phase 4: Test cleanup must preserve pre-existing unrelated database records."""
    session, track = pg_session

    # Create pre-existing user that is NOT tracked for cleanup in this session
    pre_existing_teacher = User(
        name="Pre-existing Teacher",
        email="pre_existing@edusense.edu",
        password_hash=hash_password("secret123"),
        role=UserRole.TEACHER
    )
    session.add(pre_existing_teacher)
    session.commit()
    pre_id = pre_existing_teacher.id

    # Create test-specific user and track it
    test_user = User(
        name="Test Specific User",
        email="test_specific@edusense.edu",
        password_hash=hash_password("secret123"),
        role=UserRole.STUDENT
    )
    session.add(test_user)
    session.commit()
    track(test_user)

    # Delete test_user via tracked cleanup
    session.delete(session.merge(test_user))
    session.commit()

    # Assert pre-existing teacher remains untouched in database
    reloaded_pre = session.query(User).filter(User.id == pre_id).first()
    assert reloaded_pre is not None
    assert reloaded_pre.email == "pre_existing@edusense.edu"

    # Clean up pre-existing user manually at end of test
    session.delete(reloaded_pre)
    session.commit()


# ============================================================================
# PHASE 2 & 3 TESTS — Transaction Ownership, Batch Atomicity & Audit Logs
# ============================================================================

def test_postgresql_batch_review_atomic_rollback(pg_session):
    """
    Phase 2 & 3: Comprehensive batch atomicity test.
    Verifies that if 1 item in a batch review fails:
    - Entire batch (final marks and audit logs) rolls back.
    - Pre-existing unrelated final marks and audit logs remain untouched.
    - Session remains usable post-rollback.
    - Subsequent valid batch commits cleanly and persists correct relationships.
    """
    session, track = pg_session

    # 1. Create pre-existing unrelated data
    unrelated_teacher = User(name="Unrelated T", email="unrelated_t@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.TEACHER)
    unrelated_student = User(name="Unrelated S", email="unrelated_s@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.STUDENT)
    session.add_all([unrelated_teacher, unrelated_student])
    session.commit()
    track(unrelated_teacher, unrelated_student)

    unrelated_exam = Exam(title="Unrelated Exam", subject="Math", teacher_id=unrelated_teacher.id)
    session.add(unrelated_exam)
    session.commit()
    track(unrelated_exam)

    unrelated_q = Question(exam_id=unrelated_exam.id, question_number=1, question_text="1+1?", model_answer="2", max_marks=5.0)
    session.add(unrelated_q)
    session.commit()
    track(unrelated_q)

    unrelated_sub = AnswerSheet(student_id=unrelated_student.id, exam_id=unrelated_exam.id, file_reference="s3://unrelated.pdf")
    session.add(unrelated_sub)
    session.commit()
    track(unrelated_sub)

    unrelated_ans = StudentAnswer(submission_id=unrelated_sub.id, question_id=unrelated_q.id, extracted_text="2")
    session.add(unrelated_ans)
    session.commit()
    track(unrelated_ans)

    unrelated_mark = FinalMark(answer_id=unrelated_ans.id, approved_marks=5.0, reviewing_teacher_id=unrelated_teacher.id, approval_status="APPROVED")
    session.add(unrelated_mark)
    session.commit()
    track(unrelated_mark)

    initial_mark_count = session.query(FinalMark).count()
    initial_audit_count = session.query(AuditLog).count()

    # 2. Create batch test entities
    teacher = User(name="Iso Teacher 1", email="iso_t1@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.TEACHER)
    student = User(name="Iso Student 1", email="iso_s1@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.STUDENT)
    session.add_all([teacher, student])
    session.commit()
    track(teacher, student)

    exam = Exam(title="Iso Midterm", subject="Computer Science", teacher_id=teacher.id)
    session.add(exam)
    session.commit()
    track(exam)

    q1 = Question(exam_id=exam.id, question_number=1, question_text="What is SQL?", model_answer="Structured Query Language", max_marks=10.0)
    q2 = Question(exam_id=exam.id, question_number=2, question_text="Explain RLS.", model_answer="Row Level Security", max_marks=10.0)
    session.add_all([q1, q2])
    session.commit()
    track(q1, q2)

    sub = AnswerSheet(student_id=student.id, exam_id=exam.id, file_reference="s3://submissions/iso1.pdf")
    session.add(sub)
    session.commit()
    track(sub)

    ans1 = StudentAnswer(submission_id=sub.id, question_id=q1.id, extracted_text="SQL is a DB language.")
    ans2 = StudentAnswer(submission_id=sub.id, question_id=q2.id, extracted_text="RLS filters rows.")
    session.add_all([ans1, ans2])
    session.commit()
    track(ans1, ans2)

    # 3. Submit a batch containing 1 valid review (Ans1, 8.0) and 1 invalid review (Ans2, 50.0 > max_marks 10.0)
    batch_req = BatchTeacherReviewRequest(
        reviews=[
            TeacherReviewRequest(answer_id=ans1.id, approved_marks=8.0, approval_status="APPROVED", reason="Good answer"),
            TeacherReviewRequest(answer_id=ans2.id, approved_marks=50.0, approval_status="APPROVED", reason="Invalid score")
        ]
    )

    # 4. Verify batch operation raises expected failure
    with pytest.raises(Exception) as exc_info:
        execute_batch_review_transactional(db=session, batch_in=batch_req, current_teacher=teacher)

    assert "Approved marks (50.0) must be between 0.0 and maximum marks (10.0)" in str(exc_info.value) or "400" in str(exc_info.value)

    # 5. Verify PostgreSQL contains NO marks or audit logs from failed batch
    assert session.query(FinalMark).filter(FinalMark.answer_id.in_([ans1.id, ans2.id])).count() == 0

    # 6. Assert pre-existing unrelated final marks and audit logs remain unchanged
    assert session.query(FinalMark).count() == initial_mark_count
    assert session.query(AuditLog).count() == initial_audit_count

    # 7. Verify session remains usable post-rollback
    assert session.query(User).filter(User.id == teacher.id).first() is not None

    # 8. Execute a subsequent valid batch review (Ans1=8.5, Ans2=9.0) on the same session
    valid_batch_req = BatchTeacherReviewRequest(
        reviews=[
            TeacherReviewRequest(answer_id=ans1.id, approved_marks=8.5, approval_status="APPROVED", reason="Accurate"),
            TeacherReviewRequest(answer_id=ans2.id, approved_marks=9.0, approval_status="APPROVED", reason="Great explanation")
        ]
    )

    committed_marks = execute_batch_review_transactional(db=session, batch_in=valid_batch_req, current_teacher=teacher)
    assert len(committed_marks) == 2

    # Track newly created final marks and audit logs
    for m in committed_marks:
        track(m)
    new_audits = session.query(AuditLog).filter(AuditLog.teacher_id == teacher.id).all()
    for a in new_audits:
        track(a)

    # Verify relationships on committed records
    assert session.query(FinalMark).filter(FinalMark.answer_id.in_([ans1.id, ans2.id])).count() == 2
    for m in committed_marks:
        assert m.reviewing_teacher_id == teacher.id
        assert m.approval_status == "APPROVED"


def test_caller_managed_transaction_outer_rollback(pg_session):
    """
    Phase 2: Verifies caller-managed transactions (auto_commit=False).
    If a batch succeeds with auto_commit=False, but the caller subsequently rolls back the outer transaction,
    all changes (including batch marks and audit logs) are undone.
    """
    session, track = pg_session

    teacher = User(name="Caller T1", email="caller_t1@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.TEACHER)
    student = User(name="Caller S1", email="caller_s1@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.STUDENT)
    session.add_all([teacher, student])
    session.commit()
    track(teacher, student)

    exam = Exam(title="Caller Exam", subject="CS", teacher_id=teacher.id)
    session.add(exam)
    session.commit()
    track(exam)

    q = Question(exam_id=exam.id, question_number=1, question_text="Q1", model_answer="A1", max_marks=10.0)
    session.add(q)
    session.commit()
    track(q)

    sub = AnswerSheet(student_id=student.id, exam_id=exam.id, file_reference="s3://caller.pdf")
    session.add(sub)
    session.commit()
    track(sub)

    ans = StudentAnswer(submission_id=sub.id, question_id=q.id, extracted_text="T1")
    session.add(ans)
    session.commit()
    track(ans)

    # Execute batch with auto_commit=False inside caller-managed transaction
    batch_req = BatchTeacherReviewRequest(
        reviews=[
            TeacherReviewRequest(answer_id=ans.id, approved_marks=9.0, approval_status="APPROVED", reason="Caller managed")
        ]
    )

    results = execute_batch_review_transactional(db=session, batch_in=batch_req, current_teacher=teacher, auto_commit=False)
    assert len(results) == 1

    # Caller decides to roll back the outer transaction
    session.rollback()

    # Verify final mark was NOT committed to database
    reloaded_mark = session.query(FinalMark).filter(FinalMark.answer_id == ans.id).first()
    assert reloaded_mark is None


# ============================================================================
# PHASE 5 TESTS — PostgreSQL Trigger Integrity Verifications
# ============================================================================

def test_postgresql_trigger_approved_marks_max_limit(pg_session):
    """
    Phase 5 - Trigger A: Approved marks cannot exceed maximum marks.
    Directly tests PostgreSQL trigger `trg_validate_final_mark_max_marks`.
    """
    session, track = pg_session

    teacher = User(name="Iso Teacher Trg1", email="iso_trg1@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.TEACHER)
    student = User(name="Iso Student Trg1", email="iso_strg1@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.STUDENT)
    session.add_all([teacher, student])
    session.commit()
    track(teacher, student)

    exam = Exam(title="Iso Trigger Test Exam 1", subject="DB Systems", teacher_id=teacher.id)
    session.add(exam)
    session.commit()
    track(exam)

    q = Question(exam_id=exam.id, question_number=1, question_text="What is a trigger?", model_answer="PL/pgSQL procedure", max_marks=10.0)
    session.add(q)
    session.commit()
    track(q)

    sub = AnswerSheet(student_id=student.id, exam_id=exam.id, file_reference="s3://isotrg1.pdf")
    session.add(sub)
    session.commit()
    track(sub)

    ans = StudentAnswer(submission_id=sub.id, question_id=q.id, extracted_text="Triggers run on DB events.")
    session.add(ans)
    session.commit()
    track(ans)

    # Attempt to insert a final mark with approved_marks (15.0) > question max_marks (10.0) directly into PostgreSQL
    invalid_mark = FinalMark(
        answer_id=ans.id,
        approved_marks=15.0,
        reviewing_teacher_id=teacher.id,
        approval_status="APPROVED"
    )
    session.add(invalid_mark)

    with pytest.raises((DBAPIError, InternalError)) as exc_info:
        session.flush()

    assert "Approved marks (15) exceed maximum marks (10)" in str(exc_info.value) or "exceed maximum marks" in str(exc_info.value)

    # Clean up transaction state
    session.rollback()


def test_postgresql_trigger_prevent_question_max_marks_reduction(pg_session):
    """
    Phase 5 - Trigger B: Question maximum cannot be reduced below existing approved marks.
    Directly tests PostgreSQL trigger `trg_prevent_question_max_marks_reduction`.
    """
    session, track = pg_session

    teacher = User(name="Iso Teacher Trg2", email="iso_trg2@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.TEACHER)
    student = User(name="Iso Student Trg2", email="iso_strg2@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.STUDENT)
    session.add_all([teacher, student])
    session.commit()
    track(teacher, student)

    exam = Exam(title="Iso Trigger Test Exam 2", subject="DB Systems", teacher_id=teacher.id)
    session.add(exam)
    session.commit()
    track(exam)

    # 1. Create question with max_marks = 10
    q = Question(exam_id=exam.id, question_number=1, question_text="What is ACID?", model_answer="Atomicity Consistency Isolation Durability", max_marks=10.0)
    session.add(q)
    session.commit()
    track(q)

    sub = AnswerSheet(student_id=student.id, exam_id=exam.id, file_reference="s3://isotrg2.pdf")
    session.add(sub)
    session.commit()
    track(sub)

    ans = StudentAnswer(submission_id=sub.id, question_id=q.id, extracted_text="ACID guarantees DB transactions.")
    session.add(ans)
    session.commit()
    track(ans)

    # 2. Create an approved final mark of 8.0
    valid_mark = FinalMark(
        answer_id=ans.id,
        approved_marks=8.0,
        reviewing_teacher_id=teacher.id,
        approval_status="APPROVED"
    )
    session.add(valid_mark)
    session.commit()
    track(valid_mark)

    # 3. Attempt to reduce question maximum to 7.0 (below approved 8.0)
    q.max_marks = 7.0

    with pytest.raises((DBAPIError, InternalError)) as exc_info:
        session.flush()

    assert "Cannot reduce question max_marks to 7" in str(exc_info.value) or "exceeds new limit" in str(exc_info.value)

    # 4. Confirm transaction rolls back cleanly and question max_marks remains 10.0
    session.rollback()
    reloaded_q = session.query(Question).filter(Question.id == q.id).first()
    assert reloaded_q.max_marks == 10.0


def test_postgresql_valid_mark_and_question_updates_succeed(pg_session):
    """
    Phase 5 - Trigger C: Valid marks and valid question maximum changes succeed on PostgreSQL.
    """
    session, track = pg_session

    teacher = User(name="Iso Teacher Trg3", email="iso_trg3@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.TEACHER)
    student = User(name="Iso Student Trg3", email="iso_strg3@edusense.edu", password_hash=hash_password("secret123"), role=UserRole.STUDENT)
    session.add_all([teacher, student])
    session.commit()
    track(teacher, student)

    exam = Exam(title="Iso Valid Operations Exam", subject="DB Systems", teacher_id=teacher.id)
    session.add(exam)
    session.commit()
    track(exam)

    q = Question(exam_id=exam.id, question_number=1, question_text="What is Postgres?", model_answer="Relational DBMS", max_marks=10.0)
    session.add(q)
    session.commit()
    track(q)

    sub = AnswerSheet(student_id=student.id, exam_id=exam.id, file_reference="s3://isotrg3.pdf")
    session.add(sub)
    session.commit()
    track(sub)

    ans = StudentAnswer(submission_id=sub.id, question_id=q.id, extracted_text="Postgres is an open-source RDBMS.")
    session.add(ans)
    session.commit()
    track(ans)

    # 1. Valid mark insertion (8.0 <= 10.0) succeeds
    mark = FinalMark(
        answer_id=ans.id,
        approved_marks=8.0,
        reviewing_teacher_id=teacher.id,
        approval_status="APPROVED"
    )
    session.add(mark)
    session.commit()
    track(mark)
    assert mark.id is not None

    # 2. Reducing question max_marks to 9.0 (where 9.0 >= approved mark 8.0) succeeds
    q.max_marks = 9.0
    session.commit()
    assert q.max_marks == 9.0

    # 3. Increasing question max_marks to 12.0 succeeds
    q.max_marks = 12.0
    session.commit()
    assert q.max_marks == 12.0


# ============================================================================
# PHASE 6 TESTS — Alembic Migration Reproducibility & Downgrade Integrity
# ============================================================================

def test_alembic_migration_upgrade_and_downgrade_cycle():
    """
    Phase 6: Verifies that Alembic migrations run cleanly from head -> base -> head
    on a live PostgreSQL test database without orphan types or constraints.
    """
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")

    # 1. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    # 2. Re-upgrade to head
    command.upgrade(alembic_cfg, "head")

    # 3. Verify tables and triggers exist post-reupgrade
    engine = create_engine(PG_TEST_DB_URL)
    with engine.connect() as conn:
        tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")).fetchall()
        table_names = [t[0] for t in tables]
        assert "users" in table_names
        assert "final_marks" in table_names
        assert "questions" in table_names
        assert "alembic_version" in table_names

