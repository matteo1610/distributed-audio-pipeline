# Local Kubernetes With kind

This folder contains the first Helm-based local deployment for the distributed audio pipeline.

The chart deploys:

- API
- Worker
- PostgreSQL
- RabbitMQ
- MinIO

Storage is intentionally ephemeral in this first slice so the stack works on kind without extra storage add-ons.

## Create the cluster

From `srcs/`:

```bash
kind create cluster --name audio-pipeline --config k8s/kind/kind-config.yaml
```

## Build the images

```bash
docker build -t distributed-audio-pipeline-api:dev -f app/Dockerfile app
docker build -t distributed-audio-pipeline-worker:dev -f worker/Dockerfile .
```

Load them into kind:

```bash
kind load docker-image --name audio-pipeline distributed-audio-pipeline-api:dev
kind load docker-image --name audio-pipeline distributed-audio-pipeline-worker:dev
```

## Install the chart

```bash
helm install dap k8s/distributed-audio-pipeline -f k8s/values-kind.yaml
```

## Access the services

- API: http://localhost:8000
- RabbitMQ management: http://localhost:15672
- MinIO console: http://localhost:9001
- Worker metrics: http://localhost:9100/metrics

## Cleanup

```bash
helm uninstall dap
kind delete cluster --name audio-pipeline
```
