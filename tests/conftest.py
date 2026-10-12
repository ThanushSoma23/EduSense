import sys
import os
import pytest

# Add root directory to sys.path to enable app module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.security import hash_password, create_access_token

# Isolated in-memory SQLite database for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """
    Creates fresh database tables before each test and tears them down afterwards.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """
    FastAPI TestClient with overridden get_db dependency.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def teacher_user(db):
    teacher = User(
        name="Prof. Alan Turing",
        email="turing@edusense.edu",
        password_hash=hash_password("teachersecret123"),
        role=UserRole.TEACHER,
        account_status="active"
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


@pytest.fixture
def teacher_token_headers(teacher_user):
    token = create_access_token(data={"sub": str(teacher_user.id), "role": teacher_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def student_user(db):
    student = User(
        name="Ada Lovelace",
        email="ada@edusense.edu",
        password_hash=hash_password("studentsecret123"),
        role=UserRole.STUDENT,
        account_status="active"
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@pytest.fixture
def student_token_headers(student_user):
    token = create_access_token(data={"sub": str(student_user.id), "role": student_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_student_user(db):
    student2 = User(
        name="Grace Hopper",
        email="grace@edusense.edu",
        password_hash=hash_password("studentsecret456"),
        role=UserRole.STUDENT,
        account_status="active"
    )
    db.add(student2)
    db.commit()
    db.refresh(student2)
    return student2


@pytest.fixture
def second_student_token_headers(second_student_user):
    token = create_access_token(data={"sub": str(second_student_user.id), "role": second_student_user.role.value})
    return {"Authorization": f"Bearer {token}"}
