---
title: "Complete Observability Stack"
description: "Complete guide to implement a modern observability system with Prometheus, Grafana, Loki, Tempo, Jaeger and OpenTelemetry in Kubernetes and cloud environments"
keywords: "observability, prometheus, grafana, loki, tempo, jaeger, opentelemetry, kubernetes, monitoring, alerting"
tags: [monitoring, observability, prometheus, grafana, loki, tempo, jaeger, opentelemetry]
updated: 2026-01-25
difficulty: advanced
estimated_time: 45 min
category: Monitoring
status: published
last_reviewed: 2026-01-25
prerequisites: ["Basic Kubernetes knowledge", "Docker familiarity", "Understanding of metrics and logs"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Complete Observability Stack

> Complete guide to implement a modern observability system that includes metrics, logs, traces, alerting and advanced troubleshooting in Kubernetes and cloud-native environments.

## 📋 Summary

This guide covers the complete implementation of a modern observability stack that includes metrics with Prometheus, visualization with Grafana, centralized logs with Loki, distributed tracing with Jaeger/OpenTelemetry, and advanced alerting with Alertmanager. You'll learn from basic installation to production configurations, custom dashboards, and troubleshooting strategies.

## 🎯 Audience

- DevOps/SRE engineers
- Cloud-native system administrators
- Developers who need production monitoring
- Operations teams that require alerting and advanced troubleshooting

## 📚 Prerequisites

- Basic Kubernetes knowledge
- Docker and containers familiarity
- Basic understanding of metrics, logs and tracing
- Working Kubernetes cluster (minikube, k3s, EKS, GKE, AKS, or self-hosted)

## 🏗️ Arquitectura Completa del Stack

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Aplicaciones  │───▶│   OpenTelemetry │───▶│     Jaeger      │
│   (Instrumented)│    │   Collector     │    │  (Tracing)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │    │      Loki       │    │    Grafana      │
│   (Métricas)    │    │    (Logs)       │    │ (Visualización) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                   ┌─────────────────┐
                   │  Alertmanager  │
                   │   (Alerting)   │
                   └─────────────────┘
```

### Componentes del Stack

- **Prometheus**: Recolección y almacenamiento de métricas time-series
- **Grafana**: Visualización, dashboards y alerting
- **Loki**: Logs centralizados y búsqueda eficiente
- **Jaeger**: Tracing distribuido y análisis de latencia
- **OpenTelemetry**: Estándar para instrumentación de aplicaciones
- **Alertmanager**: Gestión y enrutamiento de alertas
- **Node Exporter**: Métricas del sistema operativo
- **cAdvisor/Kubelet**: Métricas de contenedores y Kubernetes

## 🚀 Installation in Kubernetes with Helm

### Prepare the environment

```bash
# Añadir repositorios de Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update

# Crear namespace para observabilidad
kubectl create namespace observability
```

### Install complete Prometheus stack

```bash
# Instalar kube-prometheus-stack (Prometheus + Grafana + Alertmanager)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace observability \
  --set grafana.enabled=true \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.retentionSize="50GB" \
  --wait
```

### Instalar Loki para logs centralizados

```bash
# Instalar Loki Stack (Loki + Promtail + Grafana datasource)
helm install loki grafana/loki-stack \
  --namespace observability \
  --set grafana.enabled=true \
  --set prometheus.enabled=true \
  --set loki.persistence.enabled=true \
  --set loki.persistence.size=50Gi \
  --set loki.config.limits_config.retention_period=168h \
  --wait
```

### Instalar Jaeger para tracing distribuido

```bash
# Instalar Jaeger completo con Cassandra
helm install jaeger jaegertracing/jaeger \
  --namespace observability \
  --set cassandra.config.max_heap_size=1024M \
  --set cassandra.config.heap_new_size=256M \
  --set storage.type=cassandra \
  --wait
```

### Instalar OpenTelemetry Collector

```yaml
# otel-collector-values.yaml
mode: deployment
image:
  repository: otel/opentelemetry-collector-contrib

config:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318
    prometheus:
      config:
        scrape_configs:
          - job_name: 'otel-collector'
            static_configs:
              - targets: ['localhost:8888']

  processors:
    batch:
      timeout: 1s
      send_batch_size: 1024
    memory_limiter:
      limit_mib: 512
      spike_limit_mib: 128

  exporters:
    jaeger:
      endpoint: jaeger-collector:14268
      tls:
        insecure: true
    prometheus:
      endpoint: "prometheus-kube-prometheus-prometheus:9090"
    loki:
      endpoint: "http://loki:3100/loki/api/v1/push"

  service:
    pipelines:
      traces:
        receivers: [otlp]
        processors: [memory_limiter, batch]
        exporters: [jaeger]
      metrics:
        receivers: [prometheus]
        processors: [memory_limiter, batch]
        exporters: [prometheus]
      logs:
        receivers: [otlp]
        processors: [memory_limiter, batch]
        exporters: [loki]

# Instalar
helm install opentelemetry-collector open-telemetry/opentelemetry-collector \
  --namespace observability \
  -f otel-collector-values.yaml \
  --wait
```

## 📊 Exposición de Servicios

```bash
# Exponer Prometheus
kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090

# Exponer Grafana
kubectl port-forward -n observability svc/prometheus-grafana 3000:3000

# Exponer Jaeger UI
kubectl port-forward -n observability svc/jaeger-query 16686:16686

# Exponer Loki (opcional)
kubectl port-forward -n observability svc/loki 3100:3100
```

### Acceso inicial a Grafana

```bash
# Obtener contraseña de admin
kubectl get secret -n observability prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 --decode ; echo

# Usuario: admin
# URL: http://localhost:3000
```

## 🎨 Dashboards Personalizados en Grafana

### Dashboard de Nodes de Kubernetes

Importa el dashboard ID `1860` (Node Exporter Full) o crea uno personalizado:

```json
{
  "dashboard": {
    "title": "Kubernetes Nodes - Custom",
    "tags": ["kubernetes", "nodes", "custom"],
    "panels": [
      {
        "title": "CPU Usage by Node",
        "type": "bargauge",
        "targets": [
          {
            "expr": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "{{instance}}"
          }
        ]
      },
      {
        "title": "Memory Usage by Node",
        "type": "bargauge",
        "targets": [
          {
            "expr": "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100",
            "legendFormat": "{{instance}}"
          }
        ]
      },
      {
        "title": "Network I/O",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(node_network_receive_bytes_total[5m])",
            "legendFormat": "RX {{instance}}"
          },
          {
            "expr": "rate(node_network_transmit_bytes_total[5m])",
            "legendFormat": "TX {{instance}}"
          }
        ]
      },
      {
        "title": "Disk I/O",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(node_disk_reads_completed_total[5m])",
            "legendFormat": "Reads {{instance}}"
          },
          {
            "expr": "rate(node_disk_writes_completed_total[5m])",
            "legendFormat": "Writes {{instance}}"
          }
        ]
      }
    ]
  }
}
```

### Dashboard de Pods y Contenedores

```json
{
  "dashboard": {
    "title": "Kubernetes Pods - Custom",
    "tags": ["kubernetes", "pods", "containers"],
    "panels": [
      {
        "title": "Pod CPU Usage",
        "type": "table",
        "targets": [
          {
            "expr": "sum(rate(container_cpu_usage_seconds_total{container!=\"\"}[5m])) by (pod, namespace)",
            "legendFormat": "{{pod}}"
          }
        ],
        "fieldConfig": {
          "overrides": [
            {
              "matcher": { "id": "byName", "options": "Time" },
              "properties": [{ "id": "custom.hidden", "value": true }]
            }
          ]
        }
      },
      {
        "title": "Pod Memory Usage",
        "type": "table",
        "targets": [
          {
            "expr": "sum(container_memory_usage_bytes{container!=\"\"}) by (pod, namespace) / 1024 / 1024",
            "legendFormat": "{{pod}}"
          }
        ]
      },
      {
        "title": "Container Restarts",
        "type": "table",
        "targets": [
          {
            "expr": "kube_pod_container_status_restarts_total",
            "legendFormat": "{{pod}}"
          }
        ]
      }
    ]
  }
}
```

### Dashboard de Ingress y Services

```json
{
  "dashboard": {
    "title": "Kubernetes Ingress & Services",
    "tags": ["kubernetes", "ingress", "services"],
    "panels": [
      {
        "title": "HTTP Requests by Ingress",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(nginx_ingress_controller_requests{ingress!=\"\"}[5m])) by (ingress, status)",
            "legendFormat": "{{ingress}} - {{status}}"
          }
        ]
      },
      {
        "title": "Response Time by Ingress",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(nginx_ingress_controller_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p95 {{ingress}}"
          }
        ]
      },
      {
        "title": "Active Connections",
        "type": "singlestat",
        "targets": [
          {
            "expr": "nginx_ingress_controller_nginx_process_connections_total{state=\"active\"}",
            "legendFormat": "Active"
          }
        ]
      }
    ]
  }
}
```

## � OpenTelemetry y Tracing Distribuido

### Instrumentación de Aplicaciones

#### Python con OpenTelemetry

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Configurar tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configurar exportador OTLP
otlp_exporter = OTLPSpanExporter(
    endpoint="otel-collector.observability.svc.cluster.local:4317",
    insecure=True
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Auto-instrumentación para frameworks populares
FlaskInstrumentor().instrument()
RequestsInstrumentor().instrument()

# Instrumentación manual
@app.route('/api/users')
def get_users():
    with tracer.start_as_current_span("get_users") as span:
        span.set_attribute("operation.name", "database_query")
        span.set_attribute("db.table", "users")

        # Tu lógica de negocio aquí
        users = db.query("SELECT * FROM users")

        span.set_attribute("db.rows_returned", len(users))
        return jsonify(users)
```

#### JavaScript/Node.js con OpenTelemetry

```javascript
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-otlp-grpc');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');

const provider = new NodeTracerProvider();
const exporter = new OTLPTraceExporter({
  url: 'http://otel-collector.observability.svc.cluster.local:4318/v1/traces'
});

provider.addSpanProcessor(new BatchSpanProcessor(exporter));
provider.register();

// Auto-instrumentación
provider.addSpanProcessor(new ExpressInstrumentation());
provider.addSpanProcessor(new HttpInstrumentation());

// Instrumentación manual
app.get('/api/users', (req, res) => {
  const span = trace.getTracer('my-service').startSpan('get_users');
  span.setAttribute('operation.name', 'database_query');

  // Tu lógica aquí
  db.query('SELECT * FROM users', (err, results) => {
    span.setAttribute('db.rows_returned', results.length);
    span.end();
    res.json(results);
  });
});
```

#### Java con OpenTelemetry

```java
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.exporter.otlp.trace.OtlpGrpcSpanExporter;
import io.opentelemetry.sdk.trace.SdkTracerProvider;
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor;

public class MyService {
    private static final Tracer tracer = GlobalOpenTelemetry.getTracer("my-service");

    public void processRequest() {
        Span span = tracer.spanBuilder("process_request").startSpan();

        try (Scope scope = span.makeCurrent()) {
            span.setAttribute("operation.name", "business_logic");

            // Tu lógica de negocio
            doBusinessLogic();

            span.setAttribute("result", "success");
        } catch (Exception e) {
            span.setAttribute("error", true);
            span.recordException(e);
            throw e;
        } finally {
            span.end();
        }
    }
}
```

### Configuración del Collector OpenTelemetry

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  # Receivers adicionales para métricas del sistema
  prometheus:
    config:
      scrape_configs:
        - job_name: 'otel-collector'
          static_configs:
            - targets: ['localhost:8888']

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
  memory_limiter:
    limit_mib: 512
    spike_limit_mib: 128

  # Procesador para añadir atributos comunes
  resource:
    attributes:
      - key: service.namespace
        value: "production"
        action: insert
      - key: k8s.cluster.name
        value: "my-cluster"
        action: insert

exporters:
  jaeger:
    endpoint: jaeger-collector.observability.svc.cluster.local:14268
    tls:
      insecure: true
  prometheus:
    endpoint: "prometheus-kube-prometheus-prometheus.observability.svc.cluster.local:9090"
  loki:
    endpoint: "http://loki.observability.svc.cluster.local:3100/loki/api/v1/push"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [jaeger]
    metrics:
      receivers: [otlp, prometheus]
      processors: [memory_limiter, resource, batch]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [loki]
```

## 🔔 Alerting Avanzado con Alertmanager

### Reglas de Alerting para Kubernetes

```yaml
# alert-rules.yaml
groups:
- name: kubernetes-apps
  rules:
  - alert: HighPodRestartRate
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0.1
    for: 10m
    labels:
      severity: warning
      team: platform
    annotations:
      summary: "High pod restart rate"
      description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} has restarted {{ $value }} times in the last 15 minutes."
      runbook_url: "https://docs.frikiteam.es/doc/monitoring/troubleshooting#pod-restarts"

  - alert: PodNotReady
    expr: kube_pod_status_ready{condition="false"} == 1
    for: 5m
    labels:
      severity: critical
      team: platform
    annotations:
      summary: "Pod not ready"
      description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} is not ready for 5+ minutes."

  - alert: HighMemoryUsage
    expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 > 90
    for: 5m
    labels:
      severity: warning
      team: infrastructure
    annotations:
      summary: "High memory usage on {{ $labels.instance }}"
      description: "Memory usage is {{ $value }}% on {{ $labels.instance }}."

  - alert: HighCPUUsage
    expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
    for: 5m
    labels:
      severity: warning
      team: infrastructure
    annotations:
      summary: "High CPU usage on {{ $labels.instance }}"
      description: "CPU usage is {{ $value }}% on {{ $labels.instance }}."

- name: application-metrics
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100 > 5
    for: 5m
    labels:
      severity: critical
      team: backend
    annotations:
      summary: "High error rate on {{ $labels.service }}"
      description: "Error rate is {{ $value }}% for service {{ $labels.service }}."

  - alert: SlowResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
      team: backend
    annotations:
      summary: "Slow response time on {{ $labels.service }}"
      description: "95th percentile response time is {{ $value }}s for service {{ $labels.service }}."
```

### Configuración Avanzada de Alertmanager

```yaml
# alertmanager-config.yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@frikiteam.es'
  smtp_auth_username: 'alerts@frikiteam.es'
  smtp_auth_password: 'your-app-password'

# Plantillas de notificaciones
templates:
  - '/etc/alertmanager/templates/*.tmpl'

route:
  group_by: ['alertname', 'team']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
    continue: true
  - match:
      team: platform
    receiver: 'platform-team'
  - match:
      team: infrastructure
    receiver: 'infra-team'
  - match:
      team: backend
    receiver: 'backend-team'

receivers:
- name: 'default'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
    channel: '#alerts'
    title: '{{ .GroupLabels.alertname }}'
    text: '{{ .CommonAnnotations.description }}'
    color: '{{ if eq .Status "firing" }}danger{{ else }}good{{ end }}'

- name: 'critical-alerts'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/CRITICAL/WEBHOOK'
    channel: '#critical-alerts'
    title: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
    text: '{{ .CommonAnnotations.description }}'
    color: 'danger'
  pagerduty_configs:
  - service_key: 'your-pagerduty-integration-key'

- name: 'platform-team'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/PLATFORM/WEBHOOK'
    channel: '#platform-alerts'

- name: 'infra-team'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/INFRA/WEBHOOK'
    channel: '#infra-alerts'
  email_configs:
  - to: 'infra@frikiteam.es'
    subject: 'Infrastructure Alert: {{ .GroupLabels.alertname }}'
    body: '{{ .CommonAnnotations.description }}'

- name: 'backend-team'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/BACKEND/WEBHOOK'
    channel: '#backend-alerts'
  email_configs:
  - to: 'backend@frikiteam.es'

# Inhibiciones para evitar alertas duplicadas
inhibit_rules:
  - source_match:
      alertname: 'NodeDown'
    target_match:
      alertname: 'PodNotReady|HighMemoryUsage|HighCPUUsage'
    equal: ['instance']
```

## � Monitoreo de Storage (Ceph, Pure Storage, NetApp)

### Métricas de Ceph

```yaml
# ceph-exporter-service-monitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ceph-mgr
  namespace: observability
spec:
  selector:
    matchLabels:
      app: ceph-mgr
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
    scrapeTimeout: 10s
```

#### Dashboard de Ceph en Grafana

```json
{
  "dashboard": {
    "title": "Ceph Cluster Overview",
    "tags": ["ceph", "storage"],
    "panels": [
      {
        "title": "Cluster Health",
        "type": "stat",
        "targets": [
          {
            "expr": "ceph_health_status",
            "legendFormat": "Health"
          }
        ]
      },
      {
        "title": "OSD Usage",
        "type": "bargauge",
        "targets": [
          {
            "expr": "ceph_osd_stat_bytes_used / ceph_osd_stat_bytes",
            "legendFormat": "{{osd}}"
          }
        ]
      },
      {
        "title": "Pool Usage",
        "type": "table",
        "targets": [
          {
            "expr": "ceph_pool_bytes_used / ceph_pool_max_avail * 100",
            "legendFormat": "{{pool}}"
          }
        ]
      },
      {
        "title": "IOPS by Pool",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(ceph_pool_rd[5m]) + rate(ceph_pool_wr[5m])",
            "legendFormat": "{{pool}}"
          }
        ]
      }
    ]
  }
}
```

### Métricas de Pure Storage

```yaml
# pure-storage-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: pure-storage-exporter
  namespace: observability
spec:
  selector:
    matchLabels:
      app: pure-storage-exporter
  endpoints:
  - port: metrics
    interval: 60s
```

### Métricas de NetApp

```promql
# Consultas PromQL para NetApp
# Usage por volumen
netapp_volume_size_used / netapp_volume_size_total * 100

# IOPS por LUN
rate(netapp_lun_read_ops[5m]) + rate(netapp_lun_write_ops[5m])

# Latencia de storage
netapp_lun_avg_read_latency + netapp_lun_avg_write_latency
```

## 🌐 Monitoreo de Networking

### Métricas de Red Básicas

```promql
# Bandwidth por interface
rate(node_network_receive_bytes_total[5m]) * 8 / 1000000

# Latencia de red (si tienes blackbox exporter)
probe_duration_seconds

# Errores de red
rate(node_network_receive_errs_total[5m])
rate(node_network_transmit_errs_total[5m])

# Conexiones TCP
node_netstat_Tcp_CurrEstab
node_netstat_Tcp_ActiveOpens
```

### Dashboard de Networking

```json
{
  "dashboard": {
    "title": "Network Monitoring",
    "tags": ["networking", "infrastructure"],
    "panels": [
      {
        "title": "Network Traffic by Interface",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(node_network_receive_bytes_total[5m]) * 8 / 1000000",
            "legendFormat": "RX {{device}}"
          },
          {
            "expr": "rate(node_network_transmit_bytes_total[5m]) * 8 / 1000000",
            "legendFormat": "TX {{device}}"
          }
        ]
      },
      {
        "title": "Network Errors",
        "type": "table",
        "targets": [
          {
            "expr": "rate(node_network_receive_errs_total[5m])",
            "legendFormat": "RX Errors {{device}}"
          },
          {
            "expr": "rate(node_network_transmit_errs_total[5m])",
            "legendFormat": "TX Errors {{device}}"
          }
        ]
      },
      {
        "title": "TCP Connections",
        "type": "singlestat",
        "targets": [
          {
            "expr": "node_netstat_Tcp_CurrEstab",
            "legendFormat": "Established"
          }
        ]
      }
    ]
  }
}
```

## 🔧 Troubleshooting con Jaeger

### Configuración de Jaeger para Producción

```yaml
# jaeger-production-values.yaml
collector:
  enabled: true
  service:
    annotations:
      prometheus.io/scrape: "true"
      prometheus.io/port: "14268"

storage:
  type: cassandra
  cassandra:
    host: jaeger-cassandra
    keyspace: jaeger_v1_dc1
    # Para producción, considera Elasticsearch:
    # type: elasticsearch
    # elasticsearch:
    #   host: elasticsearch-master
    #   indexPrefix: jaeger

query:
  enabled: true
  service:
    type: ClusterIP

# Configuración de sampling
collector:
  otlp:
    enabled: true
  sampling:
    strategies:
      probabilistic:
        samplingRate: 0.1  # 10% de traces
      rateLimiting:
        maxTracesPerSecond: 100
```

### Análisis de Traces en Jaeger

```bash
# Buscar traces por servicio
curl -G "http://jaeger-query:16686/api/traces" \
  --data-urlencode "service=my-service" \
  --data-urlencode "limit=20"

# Buscar traces con errores
curl -G "http://jaeger-query:16686/api/traces" \
  --data-urlencode "service=my-service" \
  --data-urlencode "tags={\"error\":\"true\"}"

# Buscar traces por duración
curl -G "http://jaeger-query:16686/api/traces" \
  --data-urlencode "service=my-service" \
  --data-urlencode "maxDuration=5s"
```

### Consultas TraceQL en Grafana

```traceql
# Traces lentas
{ duration > 5s }

# Traces con errores
{ status = error }

# Traces por servicio y operación
{ service.name = "my-service" && name = "http_request" }

# Traces con tags específicos
{ resource.service.name = "api-gateway" && span.http.status_code = "500" }
```

## 🚀 Configuración de Producción

### Alta Disponibilidad

```yaml
# prometheus-ha-values.yaml
prometheus:
  prometheusSpec:
    replicas: 2
    retention: 90d
    retentionSize: "200GB"
    ruleSelector:
      matchLabels:
        prometheus: kube-prometheus
    serviceMonitorSelector:
      matchLabels:
        prometheus: kube-prometheus
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: fast-ssd
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 100Gi
    securityContext:
      runAsUser: 65534
      runAsNonRoot: true
      runAsGroup: 65534
      fsGroup: 65534

alertmanager:
  alertmanagerSpec:
    replicas: 2
    storage:
      volumeClaimTemplate:
        spec:
          storageClassName: fast-ssd
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 10Gi
```

### Backup y Recuperación

```bash
# Backup de Prometheus
kubectl exec -n observability prometheus-prometheus-0 -- tar czf /tmp/prometheus-backup.tar.gz -C /prometheus .

# Backup de Loki
kubectl exec -n observability loki-0 -- tar czf /tmp/loki-backup.tar.gz -C /loki .

# Backup de Grafana
kubectl exec -n observability prometheus-grafana-0 -- tar czf /tmp/grafana-backup.tar.gz -C /var/lib/grafana .

# Copiar backups a storage seguro
kubectl cp observability/prometheus-prometheus-0:tmp/prometheus-backup.tar.gz ./backups/
kubectl cp observability/loki-0:tmp/loki-backup.tar.gz ./backups/
kubectl cp observability/prometheus-grafana-0:tmp/grafana-backup.tar.gz ./backups/
```

### Monitoreo de Costos

```promql
# Costo estimado por namespace (AWS ejemplo)
sum(rate(container_cpu_usage_seconds_total[1h])) by (namespace) * 0.000024 * 730 +
sum(container_memory_usage_bytes / 1024 / 1024 / 1024) by (namespace) * 0.000018 * 730

# Costo de storage
sum(kube_persistentvolumeclaim_resource_requests_storage_bytes) by (namespace) / 1024 / 1024 / 1024 * 0.12
```

## 📊 SLOs y SLIs

### Definición de SLOs

```yaml
# slos.yaml
- name: api-availability
  objective: 99.9
  sli:
    events:
      good:
        metric: http_requests_total{status!~"5.."}
      total:
        metric: http_requests_total

- name: api-latency
  objective: 99
  sli:
    events:
      good:
        metric: http_request_duration_seconds{quantile="0.95"} < 0.1
      total:
        metric: http_request_duration_seconds_count

- name: storage-availability
  objective: 99.99
  sli:
    events:
      good:
        metric: ceph_health_status == 0
      total:
        metric: up{job="ceph-mgr"}
```

### Dashboard de SLOs

```json
{
  "dashboard": {
    "title": "Service Level Objectives",
    "tags": ["slo", "reliability"],
    "panels": [
      {
        "title": "API Availability",
        "type": "stat",
        "targets": [
          {
            "expr": "1 - (rate(http_requests_total{status=~\"5..\"}[30d]) / rate(http_requests_total[30d]))",
            "legendFormat": "Availability"
          }
        ]
      },
      {
        "title": "API Latency p95",
        "type": "stat",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[30d]))",
            "legendFormat": "p95 Latency"
          }
        ]
      }
    ]
  }
}
```

## 🛠️ Comandos Útiles

```bash
# Ver estado de componentes
kubectl get pods -n observability
kubectl get svc -n observability

# Logs de troubleshooting
kubectl logs -n observability -l app=prometheus --tail=100
kubectl logs -n observability -l app.kubernetes.io/name=grafana --tail=100

# Reiniciar componentes
kubectl rollout restart deployment/prometheus-grafana -n observability
kubectl rollout restart statefulset/prometheus-prometheus -n observability

# Ver alertas activas
kubectl port-forward -n observability svc/prometheus-kube-prometheus-alertmanager 9093:9093
# Luego: http://localhost:9093

# Backup de configuraciones
kubectl get configmap -n observability -o yaml > observability-configs.yaml

# Ver métricas de Prometheus
kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090
# Luego: http://localhost:9090

# Consultas directas a Loki
kubectl port-forward -n observability svc/loki 3100:3100
curl "http://localhost:3100/loki/api/v1/query_range?query={namespace=\"default\"}&start=1640995200&end=1640998800&step=60"

# Ver traces en Jaeger
kubectl port-forward -n observability svc/jaeger-query 16686:16686
# Luego: http://localhost:16686

# Monitoreo de recursos
kubectl top nodes
kubectl top pods -n observability

# Ver eventos de Kubernetes
kubectl get events -n observability --sort-by=.metadata.creationTimestamp

# Debug de ServiceMonitors
kubectl get servicemonitor -n observability
kubectl describe servicemonitor prometheus-kube-prometheus -n observability
```

## 📚 Recursos Adicionales

### Documentación Oficial
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)

### Dashboards y Configuraciones
- [Grafana Dashboards Gallery](https://grafana.com/grafana/dashboards/)
- [Awesome Prometheus Alerts](https://awesome-prometheus-alerts.grep.to/)
- [Prometheus Monitoring Mixins](https://monitoring.mixins.dev/)

### Comunidad y Soporte
- [Prometheus Community](https://prometheus.io/community/)
- [Grafana Community](https://community.grafana.com/)
- [Kubernetes Slack (#monitoring)](https://slack.k8s.io/)

### Libros y Cursos
- [Prometheus: Up & Running](https://www.oreilly.com/library/view/prometheus-up/9781492034131/)
- [Monitoring Kubernetes](https://www.oreilly.com/library/view/monitoring-kubernetes/9781492052685/)
- [Distributed Tracing in Practice](https://www.oreilly.com/library/view/distributed-tracing-in/9781492056638/)

## ✅ Checklist Completo de Implementación

### Instalación Base
- [x] Namespace `observability` creado
- [x] Prometheus instalado con Helm
- [x] Grafana instalado con Helm
- [x] Loki instalado con Helm
- [x] Jaeger instalado con Helm
- [x] OpenTelemetry Collector configurado

### Configuración
- [x] Servicios expuestos correctamente
- [x] Data sources configurados en Grafana
- [x] Reglas de alerting definidas
- [x] Dashboards básicos importados

### Monitoreo Avanzado
- [x] Dashboards personalizados para Kubernetes
- [x] Instrumentación OpenTelemetry en aplicaciones
- [x] Alerting con enrutamiento por equipos
- [x] Monitoreo de storage (Ceph/Pure/NetApp)
- [x] Monitoreo de networking
- [x] SLOs y SLIs definidos

### Producción
- [x] Alta disponibilidad configurada
- [x] Persistencia de datos habilitada
- [x] Backups automáticos configurados
- [x] Seguridad (TLS, RBAC) implementada
- [x] Retención de datos optimizada
- [x] Monitoreo de costos habilitado

### Troubleshooting
- [x] Runbooks documentados
- [x] Alertas con contexto suficiente
- [x] Tracing distribuido operativo
- [x] Logs centralizados funcionando
- [x] Métricas de rendimiento recopiladas
