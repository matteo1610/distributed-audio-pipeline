# Observability With kind

This is the optional Helm release for Prometheus and Grafana.

Install the app chart first, then install this chart into the same kind cluster.

## Assumptions

The default scrape targets expect the app release name to be `dap`:

- API: `dap-api:8000`
- Worker metrics: `dap-worker-metrics:9100`

If you use a different app release name, override `prometheus.scrapeTargets` in `values.yaml` or `values-kind.yaml`.

The Grafana datasource target is release-aware and points to the Prometheus service of the same observability Helm release (for example `dap-observability-prometheus:9090`).

## Install

From `srcs/`:

```bash
helm install dap-observability k8s/observability -f k8s/observability/values-kind.yaml
```

## Access

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## Remove

```bash
helm uninstall dap-observability
```
