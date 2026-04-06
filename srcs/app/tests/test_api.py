"""API route tests."""
import io
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.main import create_app
from app.models.audio_job import AudioFeatures, AudioJob, JobStatus, ProcessedAudio
from app.models.user import User, UserRole


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


@patch("app.api.routes.upload._storage")
@patch("app.api.routes.upload._job_service")
@patch("app.api.routes.upload._metrics")
def test_upload_audio_storage_failure(mock_metrics, mock_job_service, mock_storage, client):
    """Test upload failure when storage rejects the file."""
    mock_storage.upload_bytes.side_effect = RuntimeError("storage unavailable")

    response = client.post(
        "/api/uploads",
        files={"file": ("test.wav", io.BytesIO(b"fake audio data"), "audio/wav")},
    )

    assert response.status_code == 500
    assert "Failed to upload file" in response.json()["detail"]
    mock_metrics.record_upload.assert_not_called()
    mock_metrics.record_job_published.assert_not_called()
    mock_metrics.record_upload_latency.assert_not_called()
    mock_job_service.create_and_publish_job.assert_not_called()


@patch("app.api.routes.upload._storage")
@patch("app.api.routes.upload._job_service")
@patch("app.api.routes.upload._metrics")
def test_upload_audio_job_creation_failure(mock_metrics, mock_job_service, mock_storage, client):
    """Test upload failure when job creation fails after storage succeeds."""
    mock_job_service.create_and_publish_job.side_effect = RuntimeError("broker unavailable")

    response = client.post(
        "/api/uploads",
        files={"file": ("test.wav", io.BytesIO(b"fake audio data"), "audio/wav")},
    )

    assert response.status_code == 500
    assert "Failed to create job" in response.json()["detail"]
    mock_storage.upload_bytes.assert_called_once()
    mock_metrics.record_upload.assert_called_once()
    mock_metrics.record_job_published.assert_not_called()
    mock_metrics.record_upload_latency.assert_not_called()


@patch("app.api.routes.upload._job_repo")
def test_get_job_status_invalid_id(mock_job_repo, client):
    """Test invalid job IDs are rejected before repository access."""
    response = client.get("/api/jobs/not-a-uuid")

    assert response.status_code == 400
    assert "Invalid job ID format" in response.json()["detail"]
    mock_job_repo.get_job.assert_not_called()


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


def test_get_job_status_admin_override(client):
    """Test that admins can access jobs owned by other users."""
    admin_user = User(
        id=TEST_USER_ID,
        username="admin-user",
        email="admin@example.com",
        password_hash="not-used",
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: admin_user
    admin_client = TestClient(app)

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
        response = admin_client.get(f"/api/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "DONE"


@patch("app.api.routes.upload._job_repo")
def test_get_job_results_success(mock_job_repo, client):
    """Test retrieving processing results for a completed job."""
    job_id = uuid.uuid4()
    job = AudioJob(
        id=job_id,
        owner_id=TEST_USER_ID,
        object_key="uploads/example.wav",
        status=JobStatus.DONE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    result = ProcessedAudio(
        job_id=job_id,
        filename="example.wav",
        output_path="processed/uploads/example.wav",
        features=AudioFeatures(
            duration_seconds=12.5,
            sample_rate=44100,
            channels=2,
            audio_format="wav",
        ),
    )
    mock_job_repo.get_job.return_value = job
    mock_job_repo.get_processing_result.return_value = result

    response = client.get(f"/api/jobs/{job_id}/results")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == str(job_id)
    assert data["status"] == "DONE"
    assert data["filename"] == "example.wav"
    assert data["output_path"] == "processed/uploads/example.wav"
    assert data["features"]["duration_seconds"] == 12.5
    assert data["features"]["sample_rate"] == 44100
    assert data["features"]["channels"] == 2
    assert data["features"]["audio_format"] == "wav"


@patch("app.api.routes.upload._job_repo")
def test_get_job_results_fallback_values(mock_job_repo, client):
    """Test result response uses derived values when processing output is missing."""
    job_id = uuid.uuid4()
    job = AudioJob(
        id=job_id,
        owner_id=TEST_USER_ID,
        object_key="uploads/raw/example.flac",
        status=JobStatus.PROCESSING,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_job_repo.get_job.return_value = job
    mock_job_repo.get_processing_result.return_value = None

    response = client.get(f"/api/jobs/{job_id}/results")

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "example.flac"
    assert data["output_path"] == "processed/uploads/raw/example.flac"
    assert data["features"]["audio_format"] == "flac"
    assert data["features"]["duration_seconds"] is None


@patch("app.api.routes.upload._job_repo")
def test_get_job_results_invalid_id(mock_job_repo, client):
    """Test invalid job IDs are rejected for results endpoint."""
    response = client.get("/api/jobs/not-a-uuid/results")

    assert response.status_code == 400
    assert "Invalid job ID format" in response.json()["detail"]
    mock_job_repo.get_job.assert_not_called()


def test_get_job_results_forbidden(client):
    """Test that a different user cannot access another user's results."""
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
        response = client.get(f"/api/jobs/{job_id}/results")

    assert response.status_code == 403
    assert "Not allowed" in response.json()["detail"]


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
