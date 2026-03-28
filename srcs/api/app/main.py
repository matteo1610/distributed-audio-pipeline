import json
import os
import time
import uuid
from datetime import datetime, timezone

import pika
import psycopg
from fastapi import FastAPI, File, HTTPException, UploadFile
from minio import Minio
from minio.error import S3Error
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

app = FastAPI(title="Distributed Audio Pipeline API")

DB_URL = os.getenv("DATABASE_URL", "postgresql://app:app@postgres:5432/audio_pipeline")
RABBIT_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBIT_USER = os.getenv("RABBITMQ_USER", "app")
RABBIT_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "app")
RABBIT_QUEUE = os.getenv("RABBITMQ_QUEUE", "audio.jobs")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "raw-audio")

upload_counter = Counter("uploads_total", "Total uploaded audio files")
published_jobs_counter = Counter("jobs_published_total", "Total jobs published to queue")
upload_latency = Histogram("upload_seconds", "Upload request latency")


def db_conn() -> psycopg.Connection:
    return psycopg.connect(DB_URL)


def rabbit_channel() -> pika.adapters.blocking_connection.BlockingChannel:
    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
    params = pika.ConnectionParameters(host=RABBIT_HOST, credentials=credentials)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=RABBIT_QUEUE, durable=True)
    return channel


def minio_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


@app.on_event("startup")
def startup() -> None:
    for _ in range(20):
        try:
            with db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            break
        except Exception:
            time.sleep(1)

    client = minio_client()
    try:
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
    except S3Error as exc:
        raise RuntimeError(f"Unable to prepare MinIO bucket: {exc}") from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/uploads")
def upload_audio(file: UploadFile = File(...)) -> dict:
    start = time.perf_counter()
    job_id = uuid.uuid4()
    object_key = f"{job_id}/{file.filename}"

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    client = minio_client()
    client.put_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_key,
        data=__import__("io").BytesIO(data),
        length=len(data),
        content_type=file.content_type or "application/octet-stream",
    )

    now = datetime.now(timezone.utc)
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jobs (id, status, created_at, updated_at)
                VALUES (%s, 'PENDING', %s, %s)
                """,
                (job_id, now, now),
            )
            cur.execute(
                """
                INSERT INTO audio_files (job_id, object_key, original_filename, content_type, size_bytes)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (job_id, object_key, file.filename, file.content_type, len(data)),
            )
        conn.commit()

    channel = rabbit_channel()
    payload = {
        "job_id": str(job_id),
        "object_key": object_key,
        "submitted_at": now.isoformat(),
        "retry_count": 0,
    }
    channel.basic_publish(
        exchange="",
        routing_key=RABBIT_QUEUE,
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    channel.connection.close()

    upload_counter.inc()
    published_jobs_counter.inc()
    upload_latency.observe(time.perf_counter() - start)

    return {"job_id": str(job_id), "status": "PENDING"}


@app.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID) -> dict:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, status, error_message, created_at, updated_at FROM jobs WHERE id = %s",
                (job_id,),
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": str(row[0]),
        "status": row[1],
        "error_message": row[2],
        "created_at": row[3].isoformat(),
        "updated_at": row[4].isoformat(),
    }


@app.get("/jobs/{job_id}/result")
def get_result(job_id: uuid.UUID) -> dict:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM jobs WHERE id = %s", (job_id,))
            job_row = cur.fetchone()
            if not job_row:
                raise HTTPException(status_code=404, detail="Job not found")
            if job_row[0] != "DONE":
                raise HTTPException(status_code=409, detail=f"Job status is {job_row[0]}")

            cur.execute(
                """
                SELECT r.duration_seconds, r.sample_rate, r.channels, f.original_filename, f.size_bytes
                FROM processing_results r
                JOIN audio_files f ON f.job_id = r.job_id
                WHERE r.job_id = %s
                """,
                (job_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Result not found")

    return {
        "job_id": str(job_id),
        "duration_seconds": float(row[0]) if row[0] is not None else None,
        "sample_rate": row[1],
        "channels": row[2],
        "original_filename": row[3],
        "size_bytes": row[4],
    }
