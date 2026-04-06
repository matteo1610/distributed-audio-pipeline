# Observability Setup for Distributed Audio Pipeline

This directory contains a Docker Compose overlay for running observability locally **without Kubernetes**, designed for educational purposes and local development.

## Overview

The observability stack includes:

- **Prometheus** (v2.55.1): Metrics collection and alerting engine
- **Grafana** (11.2.0): Metrics visualization and dashboarding

This setup allows you to monitor the API and worker services locally to understand:
- Service health and uptime
- Job processing metrics
- Upload performance
- Alert generation and evaluation

## Quick Start

From the `srcs/` directory:

```bash
docker compose \
  -f docker-compose.yaml \
  -f observability/docker-compose.observability.yaml \
  up -d
```

This merges the main application stack with the observability overlay.

### Verify Services

Wait ~30 seconds for services to stabilize, then check:

```bash
# Verify Prometheus targets are up
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].labels.job'

# Verify alert rules are loaded
curl -s http://localhost:9090/api/v1/rules | jq '.data[].groups[].rules[].alert'
```

## Endpoints

- **Prometheus UI**: http://localhost:9090
- **Grafana UI**: http://localhost:3000 (admin / admin)
- **API metrics**: http://localhost:8000/metrics
- **Worker metrics**: http://localhost:9100/metrics

## Architecture

```
┌─────────────────┐          ┌──────────────────┐
│   API Service   │          │ Worker Service   │
│  (port 8000)    │          │  (port 9100)     │
└────────┬────────┘          └────────┬─────────┘
         │ /metrics                   │ /metrics
         │                            │
         └──────────────┬─────────────┘
                        │
                   ┌────▼─────┐
                   │Prometheus │
                   │ (9090)    │
                   └────┬──────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
    ┌────▼──────┐            ┌────────▼──────┐
    │  Grafana  │            │  Alertmanager │
    │  (3000)   │            │  (alerts)     │
    └───────────┘            └───────────────┘
```

## Metrics Collection

### Prometheus Scrape Targets

Prometheus is configured to scrape metrics from:

1. **API Service** (`api:8000/metrics`)
   - `uploads_total`: Counter of total uploads
   - `processing_duration_seconds`: Histogram of processing time
   - `up`: Service uptime indicator (1 = up, 0 = down)

2. **Worker Service** (`worker:9100/metrics`)
   - `jobs_completed_total`: Counter of successfully completed jobs
   - `jobs_failed_total`: Counter of failed jobs
   - `job_processing_duration_seconds`: Histogram of job processing time
   - `up`: Service uptime indicator

3. **Prometheus Self-Monitoring** (`prometheus:9090/metrics`)
   - Prometheus internal health metrics

### Configuration

- **Scrape interval**: 15 seconds
- **Evaluation interval**: 15 seconds
- **Metrics retention**: 15 days (default)

## Alert Rules

Four educational alert rules are included to demonstrate conditions you should monitor:

### 1. ApiDown
- **Condition**: API service is unreachable (up{job="api"} == 0)
- **Duration**: 30 seconds
- **Severity**: critical
- **What it means**: The API service is not responding to Prometheus scrapes
- **Trigger test**: Stop the API container and wait 30 seconds

### 2. WorkerDown
- **Condition**: Worker service is unreachable (up{job="worker"} == 0)
- **Duration**: 30 seconds
- **Severity**: critical
- **What it means**: The worker service is not responding to Prometheus scrapes
- **Trigger test**: Stop the worker container and wait 30 seconds

### 3. JobFailuresDetected
- **Condition**: Job failures increase in 5-minute window (increase(jobs_failed_total[5m]) > 0)
- **Duration**: 1 minute
- **Severity**: warning
- **What it means**: At least one job has failed in the last 5 minutes
- **Trigger test**: Upload invalid files or cause a processing error

### 4. HighUploadLatency
- **Condition**: Average upload latency exceeds 0.5 seconds
- **Duration**: 2 minutes
- **Severity**: warning
- **What it means**: Users are experiencing slower uploads than normal
- **Trigger test**: Run stress test with high concurrency

For details, see [prometheus/alerts.yml](prometheus/alerts.yml).

## Grafana Dashboard

The auto-provisioned starter dashboard (`Distributed Audio Pipeline Overview`) displays:

### Panels

1. **Total Uploads** (stat)
   - Query: `sum(uploads_total{job="api"})`
   - Shows cumulative count of all uploads since API start

2. **Completed Jobs** (stat)
   - Query: `sum(jobs_completed_total{job="worker"})`
   - Shows cumulative count of successfully processed jobs

3. **Failed Jobs** (stat)
   - Query: `sum(jobs_failed_total)`
   - Shows cumulative count of failed jobs

4. **Average Upload Latency** (stat)
   - Query: `clamp_min(rate(processing_duration_seconds_sum[5m]) / rate(..._count[5m]), 0)`
   - Shows average request latency in seconds over the last 5 minutes

### Accessing Grafana

1. Open http://localhost:3000
2. Login with `admin` / `admin`
3. The dashboard is auto-provisioned and appears in the sidebar

### Customizing the Dashboard

To modify the dashboard:
1. Make changes in Grafana UI (panels, queries, layout)
2. Export the updated dashboard JSON
3. Replace [grafana/dashboards/distributed-audio-overview.json](grafana/dashboards/distributed-audio-overview.json) with the exported version

Note: Manual changes may be overwritten on next container restart if provisioning reloads.

## Educational Experiments

Try these exercises to understand monitoring in action:

### Experiment 1: Service Downtime Detection

```bash
# Terminal 1: Watch Prometheus (stay at this URL)
open http://localhost:9090/alerts

# Terminal 2: Stop the API container
docker stop srcs-api-1

# Expected: ApiDown alert fires after ~30 seconds
#           Panel shows "Pending" then "Firing"

# Restart the service
docker start srcs-api-1

# Expected: Alert clears after ~30 seconds
```

### Experiment 2: Performance Under Load

```bash
# Terminal 1: Watch Grafana latency panel
open http://localhost:3000

# Terminal 2: Run stress test with controlled concurrency
cd srcs
TOTAL_UPLOADS=200 CONCURRENCY=20 ./scripts/stress_uploads.sh

# Expected: 
# - uploads_total counter increases
# - Average latency may spike
# - Eventually HighUploadLatency alert may fire
# - Uploads complete within ~30 seconds at 20 concurrency
```

### Experiment 3: Failure Tracking

```bash
# Terminal 1: Watch Grafana failed jobs panel

# Terminal 2: Upload an invalid/corrupt file
# Or cause a processing error in your application

# Expected: jobs_failed_total counter increments
#           JobFailuresDetected fires after 1 minute of failure
```

### Experiment 4: Query Prometheus Directly

Prometheus provides a query language (PromQL) for custom exploration:

```bash
# Examples:
curl 'http://localhost:9090/api/v1/query?query=up'
curl 'http://localhost:9090/api/v1/query?query=jobs_completed_total'
curl 'http://localhost:9090/api/v1/query_range?query=uploads_total&start=1609459200&end=1609545600&step=60'

# Or use the Prometheus UI:
open http://localhost:9090/graph
```

## Common Tasks

### Restart the Full Stack

```bash
docker compose \
  -f docker-compose.yaml \
  -f observability/docker-compose.observability.yaml \
  down

docker compose \
  -f docker-compose.yaml \
  -f observability/docker-compose.observability.yaml \
  up -d
```

### View Prometheus Configuration

```bash
curl -s http://localhost:9090/api/v1/configuration
```

### Query Metrics in Prometheus

Open http://localhost:9090/graph and enter queries like:
- `up` (all services and their uptime)
- `increase(uploads_total[5m])` (uploads in last 5 minutes)
- `rate(jobs_completed_total[5m])` (job completion rate in jobs/second)

### Stop Only Observability, Keep App Running

```bash
docker compose -f observability/docker-compose.observability.yaml down
```

### Access Grafana Dashboards Programmatically

Grafana API is available at http://localhost:3000/api:

```bash
curl -s http://localhost:3000/api/dashboards/db/distributed-audio-overview \
  -H "Authorization: Bearer admin:admin" | jq .
```

## Directory Structure

```
observability/
├── README.md                                    # This file
├── docker-compose.observability.yaml            # Compose overlay
├── prometheus/
│   ├── prometheus.yml                           # Prometheus configuration
│   └── alerts.yml                               # Alert rules
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── datasource.yml                   # Auto-provision Prometheus datasource
    │   └── dashboards/
    │       └── provider.yml                     # Dashboard provisioning config
    └── dashboards/
        └── distributed-audio-overview.json      # Default dashboard
```

## Troubleshooting

### No Data in Grafana

1. Check Prometheus targets are healthy:
   ```bash
   curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets'
   ```

2. Verify datasource connection:
   - Grafana UI → Configuration → Data Sources → Prometheus
   - Click "Test" button

3. Restart Grafana:
   ```bash
   docker restart srcs-grafana-1
   ```

### Alerts Not Firing

1. Check alert rules loaded:
   ```bash
   curl -s http://localhost:9090/api/v1/rules | jq '.data[].groups[].rules'
   ```

2. Check if condition is met:
   - Go to Prometheus UI → Alerts
   - Look at rule evaluation results

3. Verify Prometheus config:
   ```bash
   curl -s http://localhost:9090/api/v1/configuration | jq '.config'
   ```

### High Memory Usage

- Default Prometheus retention is 15 days. Reduce via `--storage.tsdb.retention.time=7d` in docker-compose.observability.yaml
- Grafana memory is typically 256-512MB; adjust `mem_limit` if needed

## Next Steps (For Production)

The current setup is suitable for **local development and education**. For production monitoring:

1. **Add Alertmanager**: Route alerts to email, Slack, PagerDuty, etc.
2. **Store metrics externably**: Use cloud-managed Prometheus or long-term storage backends
3. **Add tracing**: Integrate OpenTelemetry for distributed tracing
4. **Centralized logging**: Add Loki + Promtail for log aggregation
5. **Infrastructure metrics**: Export container and database host metrics
6. **Kubernetes**: Deploy with kube-prometheus-stack and Helm on production clusters
7. **SLOs**: Define Service Level Objectives and alert on burn rates

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Alert Rule Writing](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
