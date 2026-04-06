# Distributed Audio Processing Pipeline with Observability

## Overview

This repository now includes an initial local development stack for the first end-to-end pipeline slice:

- API service (FastAPI)
- Worker service (queue consumer)
- PostgreSQL
- RabbitMQ
- MinIO

## Quickstart

From the repository root:

```bash
cd srcs
docker compose up --build
```

Services:

- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- RabbitMQ Management: http://localhost:15672 (app/app)
- MinIO Console: http://localhost:9001 (minio/minio123)

## Observability

For detailed documentation on the local observability setup (Prometheus + Grafana), metrics, alerting rules, educational experiments, and troubleshooting, see [srcs/observability/README.md](srcs/observability/README.md).

Quick start from `srcs/`:

```bash
docker compose \
	-f docker-compose.yaml \
	-f observability/docker-compose.observability.yaml \
	up -d
```

Then access:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## API Documentation

The backend API is documented in [srcs/app/README.md](srcs/app/README.md). It covers the endpoints, request formats, responses, environment variables, and local development instructions.

## Notes

- The worker currently extracts basic WAV metadata (duration, sample rate, channels).
- For non-WAV files, metadata fields are stored as null and the job still completes.

## Python Dependencies With Poetry

Both Python services now use Poetry as the source of truth for dependencies:

- `srcs/app/pyproject.toml`
- `srcs/worker/pyproject.toml`

To install dependencies locally:

```bash
cd srcs/app
poetry install

cd ../worker
poetry install
```

To add a new dependency:

```bash
cd srcs/app
poetry add <package>

cd ../worker
poetry add <package>
```

## Running Tests

Run tests with Poetry in each service folder:

```bash
cd srcs/app
poetry install --with dev
poetry run pytest

cd ../worker
poetry install --with dev
poetry run pytest
```
