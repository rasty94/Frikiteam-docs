---
title: "Trivy Operator: Continuous Scanning in Kubernetes"
date: 2026-01-25
updated: 2026-01-25
tags: [security, kubernetes, trivy, vulnerability-scanning, opa, alerts]
difficulty: intermediate
estimated_time: 5 min
category: Cybersecurity
status: published
last_reviewed: 2026-01-25
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Trivy Operator: Continuous Scanning in Kubernetes

Keep an eye on images, configurations and cluster resources with continuous findings, policies and alerts.

## Quick Install

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts
helm repo update
helm install trivy-operator aqua/trivy-operator -n trivy-system --create-namespace \
  --set trivy.ignoreUnfixed=true \
  --set trivy.severity=HIGH,CRITICAL
```

## Resources It Creates
- VulnerabilityReports (per image)
- ConfigAuditReports (per Kubernetes object)
- ExposedSecretReports (secret discovery)
- RbacAssessmentReports (RBAC findings)

Querying the reports:
```bash
kubectl get vulnerabilityreports -A
kubectl get configauditreports -A
kubectl get rbacassessmentreports -A
```

## Alerting with PrometheusRule

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
        summary: "High severity vulnerabilities detected"
        description: "Trivy Operator reports HIGH/CRITICAL findings in images"
```

## Enforcement with Kyverno (example)

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
      message: "Image has no Trivy report, or contains HIGH/CRITICAL findings"
      deny:
        conditions:
        - key: "{{ vulnerabilities.high }}"
          operator: GreaterThan
          value: 0
```
{% endraw %}

## Best Practices
- Run Trivy Operator in a dedicated namespace with restrictive PSP/PSA
- Set `trivy.ignoreUnfixed=true` to cut down the initial noise
- Export metrics to Prometheus and alert via Slack/Email
- Review RBAC and exposed-secret findings on a regular basis
