---
title: "CI Security Scanning: SAST, DAST y Contenedores"
date: 2026-01-25
updated: 2026-01-25
tags: [security, ci, sast, dast, containers, trivy, grype]
difficulty: intermediate
estimated_time: 5 min
category: Ciberseguridad
status: published
last_reviewed: 2026-01-25
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Escaneo de Seguridad en CI/CD

Integra escáneres de seguridad en pipelines para detectar vulnerabilidades de código (SAST), comportamiento en ejecución (DAST) y riesgos en contenedores e IaC.

## Herramientas Recomendadas

- **SAST**: Semgrep, CodeQL
- **DAST**: OWASP ZAP, Nikto
- **Contenedores/IaC**: Trivy, Grype, Checkov, kube-score

## GitHub Actions: Workflow de ejemplo

{% raw %}
```yaml
name: security-scan
on:
  pull_request:
    branches: [ main ]

jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: semgrep/semgrep-action@v1
        with:
          config: "p/ci"
          generateSarif: true
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: semgrep.sarif

  containers:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .
      - name: Trivy scan
        uses: aquasecurity/trivy-action@0.20.0
        with:
          image-ref: myapp:${{ github.sha }}
          severity: HIGH,CRITICAL
          format: sarif
          output: trivy.sarif
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: trivy.sarif

  iac:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Checkov IaC scan
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          output_format: sarif
          output_file_path: checkov.sarif
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: checkov.sarif
```
{% endraw %}

## Políticas de Aprobación

- Requerir 0 vulnerabilidades CRITICAL para merge
- Bloquear despliegues si `policy-as-code` falla (OPA/Gatekeeper, Kyverno)

## DAST con OWASP ZAP

```bash
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://staging.myapp.example.com \
  -r zap-report.html --minlevel WARN
```

## Buenas Prácticas

- Ejecutar escaneos en PR y en release
- Exportar SARIF y publicar alertas en Security tab
- Usar runners efímeros (aislados) para scans
- Automatizar excepciones con plazos (no indefinidas)
