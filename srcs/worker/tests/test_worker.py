"""Worker tests for the standalone service."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

sys.path.append(str(Path(__file__).resolve().parents[2]))

from worker import ProcessorWorker


def test_process_message_success():
    broker = MagicMock()
    storage = MagicMock()
    job_service = MagicMock()
    metrics = MagicMock()
    worker = ProcessorWorker(broker, storage, job_service, metrics)

    job_id = uuid4()
    payload = {"job_id": str(job_id), "object_key": f"{job_id}/test.wav"}

    ch = MagicMock()
    method = MagicMock(delivery_tag=1)
    storage.download_bytes.return_value = b"fake audio data"

    worker.process_message(ch, method, None, json.dumps(payload).encode("utf-8"))

    job_service.mark_job_processing.assert_called_once_with(job_id)
    storage.download_bytes.assert_called_once_with(payload["object_key"])
    job_service.mark_job_completed.assert_called_once_with(job_id)
    metrics.record_job_completed.assert_called_once()
    ch.basic_ack.assert_called_once()


def test_process_message_failure():
    broker = MagicMock()
    storage = MagicMock()
    job_service = MagicMock()
    metrics = MagicMock()
    worker = ProcessorWorker(broker, storage, job_service, metrics)

    job_id = uuid4()
    payload = {"job_id": str(job_id), "object_key": f"{job_id}/test.wav"}

    ch = MagicMock()
    method = MagicMock(delivery_tag=1)
    storage.download_bytes.side_effect = Exception("Download failed")

    worker.process_message(ch, method, None, json.dumps(payload).encode("utf-8"))

    job_service.mark_job_failed.assert_called_once()
    metrics.record_job_failed.assert_called_once()
    ch.basic_ack.assert_called_once()
