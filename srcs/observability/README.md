# Observability

This directory contains the local observability overlay for the audio pipeline.

It is implemented with Docker Compose and adds:

- Prometheus for scraping metrics from the API and worker services.
- Grafana for dashboards.
- Alert rules defined in [prometheus/alerts.yml](prometheus/alerts.yml).

The API exposes metrics on `/metrics` at port `8000`, and the worker exposes metrics on `/metrics` at port `9100`.
Prometheus is configured in [prometheus/prometheus.yml](prometheus/prometheus.yml) to scrape those endpoints.

## Deployment

The observability stack is deployed as a Docker Compose overlay. To run only the observability services from the `srcs/` directory:

```bash
docker compose -f observability/docker-compose.observability.yaml up -d
```

Ensure the API (port 8000) and worker (port 9100) are already running so Prometheus can scrape their metrics endpoints.

It's also possible deploy in kubernetes using the Helm chart in [k8s/README.md](../k8s/README.md), which includes Prometheus and Grafana with similar configurations.

## Endpoints

- **Prometheus UI**: http://localhost:9090
- **Grafana UI**: http://localhost:3000 (default credentials: admin/admin)

The Grafana dashboard is provisioned automatically from [grafana/dashboards/distributed-audio-overview.json](grafana/dashboards/distributed-audio-overview.json).