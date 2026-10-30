{{/* Expand the name of the chart. */}}
{{- define "online-excel.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "online-excel.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/* Create chart name and version as used by the chart label. */}}
{{- define "online-excel.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Общие метки всех объектов релиза */}}
{{- define "online-excel.labels" -}}
app.kubernetes.io/part-of: online-excel
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/* Метки компонента: селектор остаётся `app: <name>` */}}
{{- define "online-excel.componentLabels" -}}
app: {{ .name }}
{{ include "online-excel.labels" .root }}
{{- end }}

{{/* Образ приложения: repo:tag */}}
{{- define "online-excel.image" -}}
{{ .image }}:{{ .tag }}
{{- end }}

{{/* Ссылка на ключ общего Secret app-secrets */}}
{{- define "online-excel.secretRef" -}}
valueFrom:
  secretKeyRef:
    name: app-secrets
    key: {{ . }}
{{- end }}

{{/* env auth_service — для Deployment и Job миграций */}}
{{- define "online-excel.authSecretEnv" -}}
- name: DB_PASSWORD
  {{- include "online-excel.secretRef" "AUTH_DB_PASSWORD" | nindent 2 }}
- name: RABBITMQ_URL
  {{- include "online-excel.secretRef" "RABBITMQ_URL" | nindent 2 }}
{{- end }}

{{/* env table_service — для Deployment и Job миграций */}}
{{- define "online-excel.tableSecretEnv" -}}
- name: EXCEL_APP__DB_PASSWORD
  {{- include "online-excel.secretRef" "TABLE_DB_PASSWORD" | nindent 2 }}
- name: EXCEL_APP__RABBITMQ_USER
  {{- include "online-excel.secretRef" "RABBITMQ_USER" | nindent 2 }}
- name: EXCEL_APP__RABBITMQ_PASSWORD
  {{- include "online-excel.secretRef" "RABBITMQ_PASSWORD" | nindent 2 }}
{{- end }}
