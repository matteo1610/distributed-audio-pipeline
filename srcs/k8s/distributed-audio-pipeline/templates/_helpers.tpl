{{- define "dap.chart" -}}
{{- printf "%s-%s" .Chart.Name (.Chart.Version | replace "+" "_") -}}
{{- end -}}

{{- define "dap.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "dap.baseLabels" -}}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ include "dap.chart" . }}
{{- end -}}

{{- define "dap.apiName" -}}{{ include "dap.fullname" . }}-api{{- end -}}
{{- define "dap.workerName" -}}{{ include "dap.fullname" . }}-worker{{- end -}}
{{- define "dap.postgresqlName" -}}{{ include "dap.fullname" . }}-postgresql{{- end -}}
{{- define "dap.rabbitmqName" -}}{{ include "dap.fullname" . }}-rabbitmq{{- end -}}
{{- define "dap.minioName" -}}{{ include "dap.fullname" . }}-minio{{- end -}}
{{- define "dap.workerMetricsName" -}}{{ include "dap.fullname" . }}-worker-metrics{{- end -}}
