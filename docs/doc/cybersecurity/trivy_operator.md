---
title: "Trivy Operator: Escaneo Continuo en Kubernetes"
date: 2026-01-25
updated: 2026-01-25
tags: [security, kubernetes, trivy, vulnerability-scanning, opa, alerts]
difficulty: intermediate
estimated_time: 5 min
category: Ciberseguridad
status: published
last_reviewed: 2026-01-25
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Trivy Operator: Escaneo Continuo en Kubernetes

Monitorea imágenes, configuraciones y recursos en el clúster con findings continuos, políticas y alertas.

## Instalación rápida

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts
helm repo update
helm install trivy-operator aqua/trivy-operator -n trivy-system --create-namespace \
  --set trivy.ignoreUnfixed=true \
  --set trivy.severity=HIGH,CRITICAL
```

## Recursos que genera
- VulnerabilityReports (por imagen)
- ConfigAuditReports (por objeto Kubernetes)
- ExposedSecretReports (búsqueda de secretos)
- RbacAssessmentReports (hallazgos RBAC)

Consultar reportes:
```bash
kubectl get vulnerabilityreports -A
kubectl get configauditreports -A
kubectl get rbacassessmentreports -A
```

## Alertas con PrometheusRule

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: trivy-operator-alerts
  namespace: trivy-system
spec:
  groups:
  - name: trivy
    rules:
    - alert: TrivyHighVulns
      expr: sum by (severity) (trivy_image_vulnerabilities{severity=~"HIGH|CRITICAL"}) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Vulnerabilidades altas detectadas"
        description: "Trivy Operator reporta HIGH/CRITICAL en imágenes"
```

## Enforcing con Kyverno (ejemplo)

{% raw %}
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: block-high-cves
spec:
  validationFailureAction: Enforce
  background: true
  rules:
  - name: image-must-have-report
    match:
      resources:
        kinds: [Pod]
    preconditions:
    - key: "{{ request.operation }}"
      operator: AnyIn
      value: ["CREATE", "UPDATE"]
    validate:
      message: "Imagen sin reporte Trivy o con HIGH/CRITICAL"
      deny:
        conditions:
        - key: "{{ vulnerabilities.high }}"
          operator: GreaterThan
          value: 0
```
{% endraw %}

## Buenas prácticas
- Ejecutar Trivy Operator en namespace dedicado con PSP/PSA restrictivas
- Usar `trivy.ignoreUnfixed=true` para reducir ruido inicial
- Exportar métricas a Prometheus y alertar en Slack/Email
- Revisar hallazgos de RBAC y secretos expuestos regularmente
