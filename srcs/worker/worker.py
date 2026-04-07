"""Standalone worker service for processing audio jobs."""
import json
import logging
import os
import sys
import time
from pathlib import Path
from uuid import UUID

import pika
from prometheus_client import start_http_server

# Ensure the shared app package is importable when running from srcs/worker.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.infrastructure.broker import RabbitMQBroker
from app.infrastructure.database import DatabaseConnection
from app.infrastructure.metrics import MetricsCollector
from app.infrastructure.storage import MinIOStorage
from app.repositories.job_repository import JobRepository
from app.services.audio_processor import AudioProcessor
from app.services.job_service import JobService

logger = logging.getLogger(__name__)


class ProcessorWorker:
    """Consumes queue messages and processes audio jobs."""

    def __init__(
        self,
        broker: RabbitMQBroker,
        storage: MinIOStorage,
        job_service: JobService,
        metrics: MetricsCollector,
        max_retries: int = 3,
        retry_delay_seconds: float = 0.0,
    ):
        self.broker = broker
        self.storage = storage
        self.job_service = job_service
        self.metrics = metrics
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def process_message(
        self,
        ch: pika.adapters.blocking_connection.BlockingChannel,
        method,
        _properties,
        body: bytes,
    ) -> None:
        payload: dict = {}
        job_id: UUID | None = None
        object_key: str | None = None
        attempt = 0

        try:
            payload = json.loads(body.decode("utf-8"))
            job_id = UUID(payload["job_id"])
            object_key = payload["object_key"]
            attempt = int(payload.get("attempt", 0))

            self.job_service.mark_job_processing(job_id)
            audio_data = self.storage.download_bytes(object_key)
            duration, sample_rate, channels = AudioProcessor.extract_audio_features(audio_data)
            self.job_service.save_job_results(job_id, duration, sample_rate, channels)
            self.job_service.mark_job_completed(job_id)
            self.metrics.record_job_completed()
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            logger.exception("Failed to process job message")
            try:
                if job_id and object_key and attempt < self.max_retries:
                    next_attempt = attempt + 1
                    logger.warning(
                        "Retrying job %s after failure (attempt %s/%s)",
                        job_id,
                        next_attempt,
                        self.max_retries,
                    )
                    self.job_service.mark_job_pending(job_id)
                    if self.retry_delay_seconds > 0:
                        time.sleep(self.retry_delay_seconds)
                    self.broker.publish_message({
                        "job_id": str(job_id),
                        "object_key": object_key,
                        "attempt": next_attempt,
                    })
                elif job_id:
                    self.job_service.mark_job_failed(job_id, str(exc))
                    self.metrics.record_job_failed()
            except Exception:
                logger.exception("Failed to update failed job status")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def start(self) -> None:
        self.broker.consume_messages(callback=self.process_message)


def _wait_for_database(db: DatabaseConnection) -> None:
    for _ in range(20):
        if db.is_healthy():
            return
        time.sleep(1)
    raise RuntimeError("Database is not ready")


def run_worker() -> None:
    logging.basicConfig(level=logging.INFO)

    db = DatabaseConnection()
    storage = MinIOStorage()
    broker = RabbitMQBroker()
    metrics = MetricsCollector()
    job_repo = JobRepository(db)
    job_service = JobService(job_repo, broker, storage)
    max_retries = int(os.getenv("WORKER_MAX_RETRIES", "3"))
    retry_delay_seconds = float(os.getenv("WORKER_RETRY_DELAY_SECONDS", "0"))

    start_http_server(int(os.getenv("WORKER_METRICS_PORT", "9100")))
    _wait_for_database(db)
    storage.ensure_bucket_exists()

    ProcessorWorker(
        broker,
        storage,
        job_service,
        metrics,
        max_retries=max_retries,
        retry_delay_seconds=retry_delay_seconds,
    ).start()


if __name__ == "__main__":
    run_worker()
