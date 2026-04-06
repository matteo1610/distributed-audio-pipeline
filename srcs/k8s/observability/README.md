# Observability With kind

This is the optional Helm release for Prometheus and Grafana.

Install the app chart first, then install this chart into the same kind cluster.

## Assumptions

The default scrape targets expect the app release name to be `dap`:

- API: `dap-api:8000`
- Worker metrics: `dap-worker-metrics:9100`

If you use a different app release name, override `prometheus.scrapeTargets` in `values.yaml` or `values-kind.yaml`.

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
