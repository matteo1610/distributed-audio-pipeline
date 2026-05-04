# Distributed Audio Processing Pipeline with Observability
## Overview
This project implements a scalable, distributed audio processing pipeline with built-in observability features. It enables efficient processing of large-scale audio workloads across multiple nodes with comprehensive monitoring and tracing capabilities. For detailed architecture and implementation specifics refer to the [project report](./docs/report/distributed-systems-final-report.pdf).

## Structure

- **`.github/`** - CI/CD workflows for Docker and Python tests
- **`docs/`** - Diagrams, proposal, next steps, and the full project report with LaTeX source
- **`srcs/`** - All source code:
  - **`app/`** - API with routes, auth, models, repositories, schemas, services, tests
  - **`frontend/`** - Web UI with HTML, CSS, and JavaScript
  - **`worker/`** - Background job processor
  - **`k8s/`** - Two Helm charts (main app and observability) plus kind config
  - **`observability/`** - Prometheus and Grafana configurations
  - **`db/`** - Database initialization scripts
  - **`scripts/`** - Utility scripts
  - **`docker-compose.yaml`** - Docker Compose for local development
- **Root files** - LICENSE, .gitignore, README

For more details each folder contains a README with specific instructions.

## Deployment
It can be deployed locally with Docker Compose or on Kubernetes using Helm charts.

### Docker Compose
Navigate to the `srcs/` directory and run:

```bash
docker compose up -d
```

This will start all components (API, worker, RabbitMQ, MinIO, PostgreSQL) in separate containers. The API will be accessible at http://localhost:8000 and the frontend at http://localhost:8080.

For deploy the observability stack separately, see [srcs/observability/README.md](./srcs/observability/README.md).

### Kubernetes
For Kubernetes deployment, see [srcs/k8s/README.md](./srcs/k8s/README.md).

## License
This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.