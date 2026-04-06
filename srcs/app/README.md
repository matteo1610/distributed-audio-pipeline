# Distributed Audio Pipeline API

This service exposes the HTTP API for the distributed audio pipeline. It handles user authentication, audio uploads, and job status retrieval.

The app is built with FastAPI and relies on PostgreSQL, RabbitMQ, and MinIO for persistence, messaging, and object storage.

## What lives here

- [main.py](main.py) - FastAPI app factory and server entrypoint
- [api/](api/) - HTTP routes
- [auth/](auth/) - Login, registration, JWT helpers, and auth dependencies
- [services/](services/) - Business logic
- [repositories/](repositories/) - Database access
- [models/](models/) - Domain objects
- [schemas/](schemas/) - Pydantic request/response models
- [infrastructure/](infrastructure/) - Database, broker, storage, metrics clients
- [tests/](tests/) - Test suite

## Run

```bash
poetry install
poetry run api
```

## Main endpoints

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /api/uploads`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/results`
- `GET /health`
- `GET /metrics`

## Configuration

The application works with built-in defaults, but these environment variables are the ones you would normally set in deployment.

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
AUTH_SECRET_KEY=change-me-in-production
AUTH_TOKEN_EXPIRE_MINUTES=60
```

## Notes

- Upload and job routes require a Bearer token.
- The API uses PostgreSQL, RabbitMQ, and MinIO.
- The worker service lives in [srcs/worker](../worker).
- Run tests for this service with `poetry run pytest` from this directory.
