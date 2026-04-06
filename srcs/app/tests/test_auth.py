"""Authentication route tests."""
from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.auth.dependencies import get_current_user
from app.auth.jwt_handler import create_access_token, decode_access_token
from app.main import create_app
from app.models.user import User
from app.models.user import UserRole


TEST_USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def make_user(
    *,
    user_id: UUID | None = None,
    username: str = "alice",
    email: str = "alice@example.com",
    role: UserRole = UserRole.USER,
    is_active: bool = True,
) -> User:
    return User(
        id=user_id or uuid4(),
        username=username,
        email=email,
        password_hash="hashed",
        role=role,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
    )


def test_register_user_success():
    """Register endpoint returns user data."""
    app = create_app()
    client = TestClient(app)

    created_user = make_user()

    with patch("app.auth.routes._auth_service") as auth_service:
        auth_service.get_user_by_username.return_value = None
        auth_service.register_user.return_value = created_user

        response = client.post(
            "/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "supersecret",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"


def test_register_user_conflict():
    """Register endpoint rejects duplicate usernames."""
    app = create_app()
    client = TestClient(app)

    with patch("app.auth.routes._auth_service") as auth_service:
        auth_service.get_user_by_username.return_value = make_user()

        response = client.post(
            "/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "supersecret",
            },
        )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    auth_service.register_user.assert_not_called()


def test_login_success():
    """Login endpoint returns bearer token."""
    app = create_app()
    client = TestClient(app)

    valid_user = make_user()

    with patch("app.auth.routes._auth_service") as auth_service:
        auth_service.authenticate_user.return_value = valid_user

        response = client.post(
            "/auth/login",
            data={"username": "alice", "password": "supersecret"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_failure():
    """Login endpoint rejects invalid credentials."""
    app = create_app()
    client = TestClient(app)

    with patch("app.auth.routes._auth_service") as auth_service:
        auth_service.authenticate_user.return_value = None

        response = client.post(
            "/auth/login",
            data={"username": "alice", "password": "wrong-password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_me_returns_current_user():
    """Me endpoint returns the authenticated user profile."""
    app = create_app()
    current_user = make_user(user_id=TEST_USER_ID)
    app.dependency_overrides[get_current_user] = lambda: current_user
    client = TestClient(app)

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(TEST_USER_ID),
        "username": "alice",
        "email": "alice@example.com",
    }


def test_get_current_user_success():
    """Dependency resolves a user from a valid JWT subject."""
    token = create_access_token(subject=str(TEST_USER_ID))
    expected_user = make_user(user_id=TEST_USER_ID)

    with patch("app.auth.dependencies._auth_service") as auth_service:
        auth_service.get_user_by_id.return_value = expected_user

        user = get_current_user(token)

    assert user.id == TEST_USER_ID
    auth_service.get_user_by_id.assert_called_once_with(TEST_USER_ID)


def test_get_current_user_rejects_invalid_token():
    """Dependency rejects tokens that fail validation."""
    with patch("app.auth.dependencies.decode_access_token", return_value=None):
        with patch("app.auth.dependencies._auth_service") as auth_service:
            with pytest.raises(HTTPException) as exc_info:
                get_current_user("invalid-token")

    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail
    auth_service.get_user_by_id.assert_not_called()


def test_get_current_user_rejects_missing_subject():
    """Dependency rejects payloads without a subject claim."""
    with patch("app.auth.dependencies.decode_access_token", return_value={"exp": 9999999999}):
        with patch("app.auth.dependencies._auth_service") as auth_service:
            with pytest.raises(HTTPException) as exc_info:
                get_current_user("token")

    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail
    auth_service.get_user_by_id.assert_not_called()


def test_get_current_user_rejects_unknown_user():
    """Dependency rejects tokens whose user no longer exists."""
    with patch("app.auth.dependencies.decode_access_token", return_value={"sub": str(TEST_USER_ID)}):
        with patch("app.auth.dependencies._auth_service") as auth_service:
            auth_service.get_user_by_id.return_value = None
            with pytest.raises(HTTPException) as exc_info:
                get_current_user("token")

    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail
    auth_service.get_user_by_id.assert_called_once_with(TEST_USER_ID)


def test_jwt_round_trip():
    """JWT helpers should preserve the subject claim."""
    token = create_access_token(subject=str(TEST_USER_ID))

    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == str(TEST_USER_ID)
