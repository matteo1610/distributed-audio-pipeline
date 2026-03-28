import uuid
from datetime import datetime, timezone
from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import main


class _DummyCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, _query, _params=None):
        return None

    def fetchone(self):
        if self._rows:
            return self._rows.pop(0)
        return None


class _DummyConn:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _DummyCursor(self._rows)

    def commit(self):
        return None


def _db_conn_factory(rows):
    def _db_conn():
        return _DummyConn(rows)

    return _db_conn


def _client_without_startup(monkeypatch):
    monkeypatch.setattr(main.app.router, "on_startup", [])
    return TestClient(main.app)


def test_health_endpoint(monkeypatch):
    client = _client_without_startup(monkeypatch)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_empty_file_returns_400(monkeypatch):
    client = _client_without_startup(monkeypatch)
    response = client.post("/uploads", files={"file": ("empty.wav", b"", "audio/wav")})

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty"


def test_get_job_not_found_returns_404(monkeypatch):
    monkeypatch.setattr(main, "db_conn", _db_conn_factory([None]))
    client = _client_without_startup(monkeypatch)

    response = client.get(f"/jobs/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_get_result_done_returns_payload(monkeypatch):
    job_id = uuid.uuid4()
    monkeypatch.setattr(
        main,
        "db_conn",
        _db_conn_factory(
            [
                ("DONE",),
                (12.5, 44100, 2, "sample.wav", 2048),
            ]
        ),
    )
    client = _client_without_startup(monkeypatch)

    response = client.get(f"/jobs/{job_id}/result")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": str(job_id),
        "duration_seconds": 12.5,
        "sample_rate": 44100,
        "channels": 2,
        "original_filename": "sample.wav",
        "size_bytes": 2048,
    }


def test_get_job_returns_serialized_dates(monkeypatch):
    job_id = uuid.uuid4()
    now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        main,
        "db_conn",
        _db_conn_factory([(job_id, "PENDING", None, now, now)]),
    )
    client = _client_without_startup(monkeypatch)

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["created_at"] == now.isoformat()
    assert response.json()["updated_at"] == now.isoformat()
