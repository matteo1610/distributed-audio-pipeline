# Local Kubernetes With kind

This folder contains the first Helm-based local deployment for the distributed audio pipeline.

The chart deploys:

- API
- Worker
- PostgreSQL
- RabbitMQ
- MinIO

Stateful services now use PVCs by default (PostgreSQL, RabbitMQ, MinIO, Prometheus, and Grafana).
If needed for quick experiments, you can disable each PVC in chart values and fall back to `emptyDir`.
The API and worker images are pulled from DockerHub:

- `docker.io/matteo1610/distributed-audio-api:latest`
- `docker.io/matteo1610/distributed-audio-worker:latest`

Observability is split into a separate optional chart under [observability/](observability/README.md).

The chart-local files are generated from the canonical sources in `db/` and `observability/` by running:

```bash
./scripts/sync_k8s_assets.sh
```

## Create the cluster

From `srcs/`:

```bash
kind create cluster --name audio-pipeline --config k8s/kind/kind-config.yaml
```

## Install the chart

```bash
helm install dap k8s/distributed-audio-pipeline -f k8s/values-kind.yaml
```

## Optional observability

If you want Prometheus and Grafana in the same kind cluster, install the separate chart after the app release:

```bash
helm install dap-observability k8s/observability -f k8s/observability/values-kind.yaml
```

## Access the services

- API: http://localhost:8000
- RabbitMQ management: http://localhost:15672
- MinIO console: http://localhost:9001
- Worker metrics: http://localhost:9100/metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## Cleanup

```bash
helm uninstall dap
kind delete cluster --name audio-pipeline
```
