# EduSense AI — Backend & Database Security Audit & Implementation

Welcome to the backend and database repository for **EduSense AI** (Automated Answer Evaluation System). This project implements a modular FastAPI backend paired with a PostgreSQL/Supabase database architecture using SQLAlchemy 2.x, Alembic migrations, and security audit hardening.

---

## 1. Security & Data-Integrity Fixes Summary

### Fix A: Unauthorized Teacher Registration Prevention
- **Issue**: Public registration allowed self-assigning `role="teacher"`.
- **Resolution**: Public registration endpoint (`/api/v1/auth/register`) strictly forces `role = UserRole.STUDENT`. Teacher accounts are provisioned via a dedicated admin endpoint (`/api/v1/auth/provision-teacher`) protected by a secret `ADMIN_SECRET_KEY`.

### Fix B: Teacher Ownership Enforcement on Mark Approval
- **Issue**: Teachers could potentially modify final marks for exams created by other teachers.
- **Resolution**: Implemented server-side ownership chain validation (`Authenticated Teacher -> Exam -> Question -> Student Answer`). Any approval attempt on an unowned exam returns `HTTP 403 Forbidden`. The authenticated teacher ID is recorded directly from token claims.

### Fix C: Secure Evaluation Ingestion & Score Validation
- **Issue**: Evaluation endpoints accepted arbitrary payload updates from any user.
- **Resolution**: Secured `POST /api/v1/evaluations` using a dedicated service-to-service key (`X-Service-Key: <EVALUATION_SERVICE_KEY>`) or exam teacher authentication. Validated score bounds ($0.0 \le \text{similarity\_score} \le 1.0$, $0.0 \le \text{concept\_coverage} \le 1.0$, $0.0 \le \text{suggested\_marks} \le \text{max\_marks}$). Restricted evaluation reads to authorized students and exam teachers.

### Fix D: Removal of Insecure JWT Secret Defaults
- **Issue**: Hardcoded fallback JWT signing secrets could be used in production.
- **Resolution**: Added strict startup validation in `app/config.py`. In `ENVIRONMENT=production`, if `SECRET_KEY` is missing or matches known placeholder strings, the application fails to start immediately with a `ValueError`. Restricted JWT verification strictly to `algorithms=[settings.ALGORITHM]`.

### Fix E: Transactional & Atomic Batch Mark Reviews
- **Issue**: Batch mark reviews committed each item independently.
- **Resolution**: Created `app/services/mark_service.py` to execute batch mark reviews within a single nested database transaction block. If any single item fails validation or authorization, the entire batch rolls back atomically, leaving 0 partial final marks or orphan audit log entries.

### Fix F: Supabase Row Level Security & Identity Mapping
- **Issue**: `auth.uid()` did not account for custom JWT claims (`sub`).
- **Resolution**: Updated `scripts/supabase_rls.sql` with a helper function `current_app_user_id()` that extracts `COALESCE(auth.jwt() ->> 'sub', auth.uid()::text)` to seamlessly map JWT user IDs to PostgreSQL table policies.

### Fix G: Additional Database Integrity & Check Constraints
- Added PostgreSQL CheckConstraints for numeric ranges:
  - `chk_eval_similarity_range` ($0.0 \le \text{similarity\_score} \le 1.0$)
  - `chk_eval_concept_range` ($0.0 \le \text{concept\_coverage} \le 1.0$)
  - `chk_eval_suggested_marks_positive` ($\text{suggested\_marks} \ge 0.0$)
  - `chk_final_marks_positive` ($\text{approved\_marks} \ge 0.0$)
- Created Alembic migration `002_security_and_integrity_constraints.py`.
- Verified cross-exam relationship integrity preventing answer association to questions from another exam.

---

## 2. Directory Structure

```
edusense/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Settings & secret validation via pydantic-settings
│   ├── database.py               # SQLAlchemy engine, session maker, get_db dependency
│   ├── security.py               # Passwords hashing (bcrypt/PBKDF2) & JWT token handling
│   ├── main.py                   # FastAPI app instance, CORS middleware, OpenAPI docs setup
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py               # User model & UserRole enum
│   │   ├── exam.py               # Exam & Question models
│   │   ├── submission.py         # AnswerSheet & StudentAnswer models
│   │   ├── evaluation.py         # AI Evaluation model & CheckConstraints
│   │   ├── final_mark.py         # FinalMark model & CheckConstraints
│   │   └── audit_log.py          # AuditLog model
│   ├── schemas/                  # Pydantic validation schemas
│   │   ├── __init__.py
│   │   ├── user.py               # User & TeacherProvisioningRequest schemas
│   │   ├── exam.py
│   │   ├── submission.py
│   │   ├── evaluation.py
│   │   ├── final_mark.py
│   │   └── audit_log.py
│   ├── api/                      # API Endpoints
│   │   ├── __init__.py
│   │   ├── deps.py               # Role & JWT dependencies (get_current_user, get_current_teacher, get_current_student)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py         # Aggregated v1 API router
│   │       ├── auth.py           # Registration, Teacher Provisioning, Login, /me
│   │       ├── exams.py          # Exam & Question routes (/exams)
│   │       ├── submissions.py    # Answer sheets & student answer routes (/submissions)
│   │       ├── evaluations.py    # Ingestion & retrieval routes (/evaluations)
│   │       ├── final_marks.py    # Teacher review & student results routes (/final-marks)
│   │       └── audit_logs.py     # Audit log routes (/audit-logs)
│   └── services/
│       ├── __init__.py
│       ├── mark_service.py       # Transactional single & batch mark review logic
│       └── audit_service.py      # Transactional audit logging helper
├── alembic/                      # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 001_initial_schema.py # Initial 8-table migration
│       └── 002_security_and_integrity_constraints.py # Check constraints migration
├── scripts/
│   └── supabase_rls.sql          # Supabase Row Level Security policy script
├── tests/                        # Automated Pytest suite
│   ├── conftest.py               # In-memory database setup & test fixtures
│   ├── test_auth.py
│   ├── test_exams.py
│   ├── test_submissions.py
│   ├── test_evaluations.py
│   ├── test_final_marks.py
│   ├── test_security_audit.py    # Security audit regression test suite
│   └── test_database_integrity.py
├── alembic.ini
├── .env.example
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 3. Database Schema & Migration History

The PostgreSQL database uses 8 normalized tables with schema migrations managed via Alembic:

- Migration `001_initial_schema.py`: Creates `users`, `exams`, `questions`, `answer_sheets`, `student_answers`, `evaluations`, `final_marks`, and `audit_logs`.
- Migration `002_security_and_integrity_constraints.py`: Adds numerical range check constraints to `evaluations` and `final_marks`.

---

## 4. macOS Setup and Execution Instructions

### Step 1: Environment & Virtualenv Setup
```bash
cd edusense
python3 -m venv venv
source venv/bin/activate
pip install --only-binary=:all: -r requirements.txt
pip install email-validator
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure you configure production secret keys in `.env`:
```ini
ENVIRONMENT="development"
DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/edusense_db"
SECRET_KEY="a-very-strong-random-jwt-secret-key"
ADMIN_SECRET_KEY="edusense-admin-key-2026"
EVALUATION_SERVICE_KEY="edusense-ai-eval-service-key-2026"
```

### Step 3: Run Database Migrations
```bash
alembic upgrade head
```

### Step 4: Run FastAPI Web Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive API docs are available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 5. Automated Regression Test Execution

Run the complete test suite:
```bash
source venv/bin/activate
PYTHONPATH=. pytest --cov=app --cov-report=term-missing
```

### Test Results:
- **Total Test Cases**: 26 Passed / 0 Failed
- **Code Coverage**: 81%

```
================================ tests coverage ================================
tests/test_auth.py .....                                                 [ 19%]
tests/test_database_integrity.py ...                                     [ 30%]
tests/test_evaluations.py ..                                             [ 38%]
tests/test_exams.py ...                                                  [ 50%]
tests/test_final_marks.py ...                                            [ 61%]
tests/test_security_audit.py ........                                    [ 92%]
tests/test_submissions.py ..                                             [100%]
======================== 26 passed in 8.94s ========================
```
