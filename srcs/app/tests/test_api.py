"""API route tests."""
import io
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.main import create_app
from app.models.user import User


TEST_USER_ID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()

    def _fake_user() -> User:
        return User(
            id=TEST_USER_ID,
            username="test-user",
            email="test@example.com",
            password_hash="not-used",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

    app.dependency_overrides[get_current_user] = _fake_user
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"# HELP" in response.content


@patch("app.api.routes.upload._storage")
@patch("app.api.routes.upload._job_service")
@patch("app.api.routes.upload._metrics")
def test_upload_audio_success(mock_metrics, mock_job_service, mock_storage, client):
    """Test successful audio upload."""
    mock_metrics.record_upload = MagicMock()
    mock_metrics.record_job_published = MagicMock()
    mock_metrics.record_upload_latency = MagicMock()
    mock_job_service.create_and_publish_job = MagicMock(return_value=uuid.uuid4())

    audio_content = b"fake audio data"
    response = client.post(
        "/api/uploads",
        files={"file": ("test.wav", io.BytesIO(audio_content), "audio/wav")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "object_key" in data
    assert data["message"] == "Job created successfully"

    mock_metrics.record_upload.assert_called_once()
    mock_metrics.record_job_published.assert_called_once()
    mock_job_service.create_and_publish_job.assert_called_once()
    called_owner_id, called_object_key = mock_job_service.create_and_publish_job.call_args.args
    assert called_owner_id == TEST_USER_ID
    assert called_object_key.startswith("uploads/")


@patch("app.api.routes.upload._job_repo")
def test_get_job_status(mock_job_repo, client):
    """Test getting job status."""
    from app.models.audio_job import AudioJob, JobStatus

    job_id = uuid.uuid4()
    job = AudioJob(
        id=job_id,
        owner_id=TEST_USER_ID,
        object_key="test/file.wav",
        status=JobStatus.DONE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_job_repo.get_job.return_value = job

    response = client.get(f"/api/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == str(job_id)
    assert data["status"] == "DONE"


def test_get_job_status_forbidden(client):
    """Test that a different user cannot access another user's job."""
    from app.models.audio_job import AudioJob, JobStatus

    job_id = uuid.uuid4()
    job = AudioJob(
        id=job_id,
        owner_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        object_key="test/file.wav",
        status=JobStatus.DONE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch("app.api.routes.upload._job_repo") as mock_job_repo:
        mock_job_repo.get_job.return_value = job
        response = client.get(f"/api/jobs/{job_id}")

    assert response.status_code == 403
    assert "Not allowed" in response.json()["detail"]


def test_get_job_status_not_found(client):
    """Test getting status for non-existent job."""
    job_id = uuid.uuid4()

    with patch("app.api.routes.upload._job_repo") as mock_job_repo:
        mock_job_repo.get_job.return_value = None
        response = client.get(f"/api/jobs/{job_id}")

    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


def test_upload_empty_file(client):
    """Test uploading empty file."""
    with patch("app.api.routes.upload._storage"):
        with patch("app.api.routes.upload._metrics"):
            response = client.post(
                "/api/uploads",
                files={"file": ("test.wav", io.BytesIO(b""), "audio/wav")},
            )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
