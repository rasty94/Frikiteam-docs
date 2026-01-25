# Observability: Prometheus + Grafana + Loki/Tempo + Alertmanager

🚧 **TRANSLATION PENDING** - Last updated in Spanish: 2026-01-25


Practical guide to deploy a unified observability stack covering metrics, logs, traces, and alerts. Includes architecture, reference docker-compose, retention, and security tips.

## 🎯 Goal
- Metrics with Prometheus + exporters
- Dashboards and alerting with Grafana
- Centralized logs with Loki + Promtail
- Distributed traces with Tempo (OTLP)
- Alerts with Alertmanager (Slack/Email)

## 🏗️ Architecture

```mermaid
graph TD
  subgraph Data
    A[Node Exporter] --> P[Prometheus]
    B[cAdvisor/Kubelet] --> P
    C[Promtail] --> L[Loki]
    D[OTLP SDK/Agent] --> T[Tempo]
  end

  subgraph Control
    P --> G[Grafana]
    L --> G
    T --> G
    P --> AM[Alertmanager]
  end

  AM --> Slack[(Slack/Webhook)]
  AM --> Email[(Email/SMTP)]
```

## 🚀 Quick deploy (docker-compose)

```yaml
version: "3.9"
services:
  prometheus:
    image: prom/prometheus:v2.51.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prom_data:/prometheus
    ports: ["9090:9090"]

  alertmanager:
    image: prom/alertmanager:v0.27.0
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    ports: ["9093:9093"]

  loki:
    image: grafana/loki:2.9.6
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml:ro
      - loki_data:/loki
    ports: ["3100:3100"]

  promtail:
    image: grafana/promtail:2.9.6
    command: -config.file=/etc/promtail/config.yml
    volumes:
      - ./promtail-config.yml:/etc/promtail/config.yml:ro
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    depends_on: [loki]

  tempo:
    image: grafana/tempo:2.4.1
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml:ro
      - tempo_data:/tmp/tempo
    ports: ["4317:4317", "3200:3200"]

  grafana:
    image: grafana/grafana:10.3.3
    ports: ["3000:3000"]
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_AUTH_ANONYMOUS_ENABLED=false
      - GF_FEATURE_TOGGLES_ENABLE=traceqlEditor
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on: [prometheus, loki, tempo]

volumes:
  prom_data:
  loki_data:
  tempo_data:
  grafana_data:
```

## ⚙️ Essential configuration

### Prometheus (prometheus.yml)
```yaml
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: node_exporter
    static_configs:
      - targets: ["node-exporter:9100"]
  - job_name: cadvisor
    static_configs:
      - targets: ["cadvisor:8080"]
  - job_name: prometheus
    static_configs:
      - targets: ["prometheus:9090"]
alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]
```

### Alertmanager (alertmanager.yml)
```yaml
global:
  smtp_smarthost: smtp.example.com:587
  smtp_from: alerts@example.com
route:
  receiver: default
receivers:
  - name: default
    slack_configs:
      - api_url: https://hooks.slack.com/services/TOKEN
        channel: "#alerts"
```

### Loki (loki-config.yaml)
```yaml
server:
  http_listen_port: 3100
limits_config:
  retention_period: 168h  # 7d
schema_config:
  configs:
    - from: 2023-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v12
      index:
        prefix: index_
        period: 24h
storage_config:
  filesystem:
    directory: /loki
```

### Promtail (promtail-config.yml)
```yaml
server:
  http_listen_port: 9080
positions:
  filename: /tmp/positions.yaml
clients:
  - url: http://loki:3100/loki/api/v1/push
scrape_configs:
  - job_name: varlogs
    static_configs:
      - targets: ["localhost"]
        labels:
          job: varlogs
          __path__: /var/log/*.log
```

### Tempo (tempo.yaml)
```yaml
server:
  http_listen_port: 3200
  grpc_listen_port: 4317
compactor:
  compaction:
    block_retention: 168h
storage:
  trace:
    backend: local
    local:
      path: /tmp/tempo
```

## 📈 Grafana
- **Data sources**: Prometheus, Loki, Tempo.
- **Recommended dashboards**: Node Exporter Full, Kubernetes / Use Method, API latency percentiles, Loki logs by label, Tempo Trace Explorer.
- **Alerting**: Use Alertmanager as notifier or Grafana alerting for simple cases.

## 🔔 Alerting best practices
- Define SLOs (p95/p99 latency, error rate, CPU/memory saturation).
- Use **inhibitions** to avoid alert storms between related services.
- Group by `service`, `cluster`, `env` in Alertmanager for clear context.
- Add **runbooks** (URL) in alert annotations.

## 🔒 Security
- Enable **auth** and **TLS** on public endpoints (reverse proxy or ingress with mTLS).
- Restrict access to Prometheus/Alertmanager/Loki/Tempo behind VPN/authenticated ingress.
- Set **retention** per compliance (logs 7-30d; raw metrics 15-30d; traces 3-7d).
- Backup volumes (Grafana, Loki index, Tempo blocks) if persistence is required.

## 🧪 Quick verification
```bash
# Metrics
curl -s http://localhost:9090/-/ready

# Logs
curl -G -s "http://localhost:3100/loki/api/v1/labels"

# Traces
curl -s http://localhost:3200/ready

# Dashboards
open http://localhost:3000
```

## 📌 Kubernetes operation (summary)
- Use official Helm charts: `kube-prometheus-stack`, `loki-stack`, `tempo-distributed`.
- Enable `persistence.enabled=true` for Prometheus/Loki/Tempo if retention >7d is needed.
- Enable `serviceMonitor` and `podMonitor` for automatic metric discovery.
- Add `networkPolicy` to limit access to control plane/ingress only.

## ✅ Checklist
- [ ] Retention tuned (metrics, logs, traces)
- [ ] Alerts with contacts and runbooks
- [ ] TLS/Auth on public endpoints
- [ ] Baseline dashboards imported in Grafana
- [ ] Backups configured if applicable
- [ ] Basic load tests (prometheus + loki + tempo)
