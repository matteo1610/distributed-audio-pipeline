"""Authentication route tests."""
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from app.models.user import User


def test_register_user_success():
    """Register endpoint returns user data."""
    app = create_app()
    client = TestClient(app)

    created_user = User(
        id=uuid4(),
        username="alice",
        email="alice@example.com",
        password_hash="hashed",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

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


def test_login_success():
    """Login endpoint returns bearer token."""
    app = create_app()
    client = TestClient(app)

    valid_user = User(
        id=uuid4(),
        username="alice",
        email="alice@example.com",
        password_hash="hashed",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

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
