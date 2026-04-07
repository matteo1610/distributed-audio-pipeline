"""Worker tests for the standalone service."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from worker import ProcessorWorker
from worker.worker import _wait_for_database, run_worker


def make_worker():
    """Build a worker with isolated mock dependencies for each test."""
    broker = MagicMock()
    storage = MagicMock()
    job_service = MagicMock()
    metrics = MagicMock()
    return ProcessorWorker(broker, storage, job_service, metrics), broker, storage, job_service, metrics


def test_process_message_success():
    worker, broker, storage, job_service, metrics = make_worker()

    job_id = uuid4()
    payload = {"job_id": str(job_id), "object_key": f"{job_id}/test.wav"}

    ch = MagicMock()
    method = MagicMock(delivery_tag=1)
    storage.download_bytes.return_value = b"fake audio data"

    # Keep feature extraction deterministic so the test only checks wiring.
    with patch("worker.worker.AudioProcessor.extract_audio_features", return_value=(12.5, 44100, 2)):
        worker.process_message(ch, method, None, json.dumps(payload).encode("utf-8"))

    job_service.mark_job_processing.assert_called_once_with(job_id)
    storage.download_bytes.assert_called_once_with(payload["object_key"])
    job_service.save_job_results.assert_called_once_with(job_id, 12.5, 44100, 2)
    job_service.mark_job_completed.assert_called_once_with(job_id)
    metrics.record_job_completed.assert_called_once()
    ch.basic_ack.assert_called_once()


def test_process_message_extract_failure():
    worker, broker, storage, job_service, metrics = make_worker()

    job_id = uuid4()
    payload = {"job_id": str(job_id), "object_key": f"{job_id}/test.wav"}

    ch = MagicMock()
    method = MagicMock(delivery_tag=1)
    storage.download_bytes.return_value = b"fake audio data"

    with patch("worker.worker.AudioProcessor.extract_audio_features", side_effect=RuntimeError("decode failed")):
        worker.process_message(ch, method, None, json.dumps(payload).encode("utf-8"))

    job_service.mark_job_processing.assert_called_once_with(job_id)
    job_service.save_job_results.assert_not_called()
    job_service.mark_job_completed.assert_not_called()
    job_service.mark_job_pending.assert_called_once_with(job_id)
    job_service.mark_job_failed.assert_not_called()
    broker.publish_message.assert_called_once_with({
        "job_id": str(job_id),
        "object_key": payload["object_key"],
        "attempt": 1,
    })
    metrics.record_job_failed.assert_not_called()
    ch.basic_ack.assert_called_once()


def test_process_message_failure():
    worker, broker, storage, job_service, metrics = make_worker()

    job_id = uuid4()
    payload = {"job_id": str(job_id), "object_key": f"{job_id}/test.wav"}

    ch = MagicMock()
    method = MagicMock(delivery_tag=1)
    storage.download_bytes.side_effect = Exception("Download failed")

    worker.process_message(ch, method, None, json.dumps(payload).encode("utf-8"))

    job_service.mark_job_processing.assert_called_once_with(job_id)
    job_service.mark_job_pending.assert_called_once_with(job_id)
    job_service.mark_job_failed.assert_not_called()
    broker.publish_message.assert_called_once_with({
        "job_id": str(job_id),
        "object_key": payload["object_key"],
        "attempt": 1,
    })
    metrics.record_job_failed.assert_not_called()
    ch.basic_ack.assert_called_once()


def test_process_message_failure_after_max_retries_marks_failed():
    worker, _, storage, job_service, metrics = make_worker()

    job_id = uuid4()
    payload = {"job_id": str(job_id), "object_key": f"{job_id}/test.wav", "attempt": 3}

    ch = MagicMock()
    method = MagicMock(delivery_tag=1)
    storage.download_bytes.side_effect = Exception("Download failed")

    worker.process_message(ch, method, None, json.dumps(payload).encode("utf-8"))

    job_service.mark_job_processing.assert_called_once_with(job_id)
    job_service.mark_job_pending.assert_not_called()
    job_service.mark_job_failed.assert_called_once()
    assert "Download failed" in job_service.mark_job_failed.call_args.args[1]
    metrics.record_job_failed.assert_called_once()
    ch.basic_ack.assert_called_once()


def test_process_message_invalid_json():
    worker, _, _, job_service, metrics = make_worker()

    ch = MagicMock()
    method = MagicMock(delivery_tag=1)

    worker.process_message(ch, method, None, b"not-json")

    job_service.mark_job_processing.assert_not_called()
    job_service.mark_job_failed.assert_not_called()
    metrics.record_job_failed.assert_not_called()
    ch.basic_ack.assert_called_once()


def test_process_message_missing_job_id():
    worker, _, _, job_service, metrics = make_worker()

    ch = MagicMock()
    method = MagicMock(delivery_tag=1)
    body = json.dumps({"object_key": "uploads/test.wav"}).encode("utf-8")

    worker.process_message(ch, method, None, body)

    job_service.mark_job_processing.assert_not_called()
    job_service.mark_job_failed.assert_not_called()
    metrics.record_job_failed.assert_not_called()
    ch.basic_ack.assert_called_once()


def test_start_delegates_to_broker():
    broker = MagicMock()
    worker = ProcessorWorker(broker, MagicMock(), MagicMock(), MagicMock())

    worker.start()

    broker.consume_messages.assert_called_once_with(callback=worker.process_message)


def test_wait_for_database_success():
    db = MagicMock()
    db.is_healthy.side_effect = [False, False, True]

    with patch("worker.worker.time.sleep") as sleep:
        _wait_for_database(db)

    assert db.is_healthy.call_count == 3
    assert sleep.call_count == 2


def test_wait_for_database_timeout():
    db = MagicMock()
    db.is_healthy.return_value = False

    with patch("worker.worker.time.sleep"):
        with pytest.raises(RuntimeError, match="Database is not ready"):
            _wait_for_database(db)


def test_run_worker_wires_dependencies():
    """Verify the worker bootstraps infrastructure and starts processing."""
    fake_db = MagicMock()
    fake_storage = MagicMock()
    fake_broker = MagicMock()
    fake_metrics = MagicMock()
    fake_job_repo = MagicMock()
    fake_job_service = MagicMock()
    fake_worker = MagicMock()

    with patch("worker.worker.DatabaseConnection", return_value=fake_db), \
        patch("worker.worker.MinIOStorage", return_value=fake_storage), \
        patch("worker.worker.RabbitMQBroker", return_value=fake_broker), \
        patch("worker.worker.MetricsCollector", return_value=fake_metrics), \
        patch("worker.worker.JobRepository", return_value=fake_job_repo), \
        patch("worker.worker.JobService", return_value=fake_job_service), \
        patch("worker.worker.start_http_server") as start_http_server, \
        patch("worker.worker._wait_for_database") as wait_for_database, \
        patch("worker.worker.ProcessorWorker", return_value=fake_worker) as processor_worker:
        # The startup path should only compose dependencies and launch the worker.
        run_worker()

    start_http_server.assert_called_once_with(9100)
    wait_for_database.assert_called_once_with(fake_db)
    fake_storage.ensure_bucket_exists.assert_called_once()
    processor_worker.assert_called_once_with(
        fake_broker,
        fake_storage,
        fake_job_service,
        fake_metrics,
        max_retries=3,
        retry_delay_seconds=0.0,
    )
    fake_worker.start.assert_called_once()
