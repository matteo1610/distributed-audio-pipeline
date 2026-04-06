#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${0}")" && pwd)"
srcs_dir="$(cd "${script_dir}/.." && pwd)"

sync_file() {
  local source_path="$1"
  local target_path="$2"

  mkdir -p "$(dirname "${target_path}")"
  cp "${source_path}" "${target_path}"
}

sync_file "${srcs_dir}/db/init.sql" "${srcs_dir}/k8s/distributed-audio-pipeline/files/init.sql"
sync_file "${srcs_dir}/observability/prometheus/prometheus.yml" "${srcs_dir}/k8s/observability/files/prometheus.yml"
sync_file "${srcs_dir}/observability/prometheus/alerts.yml" "${srcs_dir}/k8s/observability/files/alerts.yml"
sync_file "${srcs_dir}/observability/grafana/provisioning/datasources/datasource.yml" "${srcs_dir}/k8s/observability/files/grafana-datasource.yml"
sync_file "${srcs_dir}/observability/grafana/provisioning/dashboards/dashboards.yml" "${srcs_dir}/k8s/observability/files/grafana-dashboards.yml"
sync_file "${srcs_dir}/observability/grafana/dashboards/distributed-audio-overview.json" "${srcs_dir}/k8s/observability/files/distributed-audio-overview.json"

echo "Synchronized Kubernetes chart assets."
