---
title: "CI Security Scanning: SAST, DAST y Contenedores"
updated: 2026-10-11
tags: ['cybersecurity', 'ci-cd', 'devsecops', 'containers', 'vulnerability-scanning']
difficulty: intermediate
estimated_time: 5 min
category: Ciberseguridad
status: published
last_reviewed: 2026-10-11
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
    container:
      image: semgrep/semgrep
    steps:
      - uses: actions/checkout@v7
      - run: semgrep scan --config p/ci --sarif --output semgrep.sarif
      - uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: semgrep.sarif

  containers:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .
      - name: Trivy scan
        uses: aquasecurity/trivy-action@v0.36.0
        with:
          image-ref: myapp:${{ github.sha }}
          severity: HIGH,CRITICAL
          format: sarif
          output: trivy.sarif
      - uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: trivy.sarif

  iac:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Checkov IaC scan
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          output_format: sarif
          output_file_path: results.sarif
      - uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: results.sarif
```
{% endraw %}

## Políticas de Aprobación

- Requerir 0 vulnerabilidades CRITICAL para merge
- Bloquear despliegues si `policy-as-code` falla (OPA/Gatekeeper, Kyverno)

## DAST con OWASP ZAP

```bash
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
  -t https://staging.myapp.example.com \
  -r zap-report.html --minlevel WARN
```

## Buenas Prácticas

- Ejecutar escaneos en PR y en release
- Exportar SARIF y publicar alertas en Security tab
- Usar runners efímeros (aislados) para scans
- Automatizar excepciones con plazos (no indefinidas)

## Referencias

- [Semgrep: documentación](https://semgrep.dev/docs/)
- [trivy-action](https://github.com/aquasecurity/trivy-action)
- [checkov-action](https://github.com/bridgecrewio/checkov-action)
- [ZAP: baseline scan con Docker](https://www.zaproxy.org/docs/docker/baseline-scan/)
- [GitHub: subir un fichero SARIF](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/uploading-a-sarif-file-to-github)
