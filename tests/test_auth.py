from fastapi import status
from app.models.user import UserRole


def test_register_user_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "John Doe",
            "email": "john@edusense.edu",
            "password": "password123",
            "role": "teacher"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["email"] == "john@edusense.edu"
    assert data["role"] == "student"  # Public registration forces STUDENT role
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email_fails(client, teacher_user):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Duplicate User",
            "email": teacher_user.email,
            "password": "password123",
            "role": "student"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"]


def test_login_success(client, teacher_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": teacher_user.email,
            "password": "teachersecret123"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == teacher_user.email


def test_login_invalid_password(client, teacher_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": teacher_user.email,
            "password": "wrongpassword"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_read_current_user_me(client, student_token_headers, student_user):
    response = client.get("/api/v1/auth/me", headers=student_token_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == student_user.email
    assert data["role"] == UserRole.STUDENT.value
