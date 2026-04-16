# Local Kubernetes With kind

This folder contains the first Helm-based local deployment for the distributed audio pipeline.

The chart deploys:

- Frontend
- API
- Worker
- PostgreSQL
- RabbitMQ
- MinIO

Stateful services use PVCs by default (PostgreSQL, RabbitMQ, MinIO, Prometheus, and Grafana). If needed for quick experiments, you can disable each PVC in chart values and fall back to `emptyDir`.

The API and worker images are pulled from DockerHub:

- `docker.io/matteo1610/distributed-audio-api:latest`
- `docker.io/matteo1610/distributed-audio-frontend:latest`
- `docker.io/matteo1610/distributed-audio-worker:latest`

The CI workflow publishes these images as multi-arch manifests (`linux/amd64` and `linux/arm64`) so kind clusters on Apple Silicon can pull them without platform mismatch errors.

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

## Optional ingress (single endpoint for frontend + API)

Install ingress-nginx in the kind cluster:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
	--for=condition=ready pod \
	--selector=app.kubernetes.io/component=controller \
	--timeout=180s
```

Enable ingress in the Helm release:

```bash
helm upgrade --install dap k8s/distributed-audio-pipeline \
	-f k8s/values-kind.yaml \
	--set ingress.enabled=true
```

Then access everything through:

- Frontend: http://localhost/
- API health: http://localhost/health

In the frontend console, set API Base URL to `http://localhost` when using ingress.

## Optional observability

If you want Prometheus and Grafana in the same kind cluster, install the separate chart after the app release:

```bash
helm install dap-observability k8s/observability -f k8s/observability/values-kind.yaml
```

## Access the services

- API: http://localhost:30080
- Frontend: http://localhost:30517
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
