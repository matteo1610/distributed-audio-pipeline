import io
import json
import os
import time
import wave
from datetime import datetime, timezone

import pika
import psycopg
from minio import Minio
from prometheus_client import Counter, start_http_server

DB_URL = os.getenv("DATABASE_URL", "postgresql://app:app@postgres:5432/audio_pipeline")
RABBIT_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBIT_USER = os.getenv("RABBITMQ_USER", "app")
RABBIT_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "app")
RABBIT_QUEUE = os.getenv("RABBITMQ_QUEUE", "audio.jobs")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "raw-audio")

jobs_completed = Counter("jobs_completed_total", "Total completed jobs")
jobs_failed = Counter("jobs_failed_total", "Total failed jobs")


def db_conn() -> psycopg.Connection:
    return psycopg.connect(DB_URL)


def minio_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


def set_job_status(job_id: str, status: str, error_message: str | None = None) -> None:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE jobs
                SET status = %s, error_message = %s, updated_at = %s
                WHERE id = %s
                """,
                (status, error_message, datetime.now(timezone.utc), job_id),
            )
        conn.commit()


def save_result(job_id: str, duration_seconds: float | None, sample_rate: int | None, channels: int | None) -> None:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO processing_results (job_id, duration_seconds, sample_rate, channels)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE
                SET duration_seconds = EXCLUDED.duration_seconds,
                    sample_rate = EXCLUDED.sample_rate,
                    channels = EXCLUDED.channels
                """,
                (job_id, duration_seconds, sample_rate, channels),
            )
        conn.commit()


def extract_basic_audio_features(data: bytes) -> tuple[float | None, int | None, int | None]:
    try:
        with wave.open(io.BytesIO(data), "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            frame_count = wav_file.getnframes()
            duration = frame_count / float(frame_rate)
            return duration, frame_rate, channels
    except Exception:
        return None, None, None


def process_message(ch: pika.adapters.blocking_connection.BlockingChannel, method, _properties, body: bytes) -> None:
    payload = json.loads(body.decode("utf-8"))
    job_id = payload["job_id"]
    object_key = payload["object_key"]

    try:
        set_job_status(job_id, "PROCESSING")

        client = minio_client()
        obj = client.get_object(MINIO_BUCKET, object_key)
        data = obj.read()
        obj.close()
        obj.release_conn()

        duration, sample_rate, channels = extract_basic_audio_features(data)
        save_result(job_id, duration, sample_rate, channels)
        set_job_status(job_id, "DONE")
        jobs_completed.inc()

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        set_job_status(job_id, "FAILED", str(exc))
        jobs_failed.inc()
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    start_http_server(9100)

    while True:
        try:
            with db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            break
        except Exception:
            time.sleep(1)

    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
    params = pika.ConnectionParameters(host=RABBIT_HOST, credentials=credentials)

    while True:
        try:
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=RABBIT_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=RABBIT_QUEUE, on_message_callback=process_message)
            channel.start_consuming()
        except Exception:
            time.sleep(2)


if __name__ == "__main__":
    main()
