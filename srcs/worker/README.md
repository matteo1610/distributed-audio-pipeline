# Distributed Audio Pipeline Worker

This service consumes audio processing jobs from RabbitMQ, downloads the source audio from MinIO, extracts basic features, and stores the results back in the shared job database.

It is designed to run as a separate background process alongside the API service.

## What lives here

- [worker.py](worker.py) - Worker entrypoint and message processing loop
- [tests/](tests/) - Worker test suite

## Run

```bash
poetry install
poetry run worker
```

## Behavior

- Connects to PostgreSQL to wait until the database is ready.
- Ensures the MinIO bucket exists before consuming jobs.
- Exposes Prometheus metrics on port `9100` by default.
- Consumes messages from the `audio.jobs` queue unless overridden by configuration.

## Required environment variables

```bash
DATABASE_URL=postgresql://app:app@postgres:5432/audio_pipeline
RABBITMQ_HOST=rabbitmq
RABBITMQ_USER=app
RABBITMQ_PASSWORD=app
RABBITMQ_QUEUE=audio.jobs
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=minio123
MINIO_BUCKET=raw-audio
WORKER_METRICS_PORT=9100
```

## Notes

- The worker expects audio messages with `job_id` and `object_key` fields.
- It marks jobs as processing, completed, or failed in the shared job repository.
- It currently extracts WAV features and records duration, sample rate, and channel count.
- Run tests for this service with `poetry run pytest` from this directory.
