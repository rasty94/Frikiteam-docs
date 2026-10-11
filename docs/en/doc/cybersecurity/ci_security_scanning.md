---
title: "CI Security Scanning: SAST, DAST and Containers"
updated: 2026-10-11
tags: ['cybersecurity', 'ci-cd', 'devsecops', 'containers', 'vulnerability-scanning']
difficulty: intermediate
estimated_time: 5 min
category: Cybersecurity
status: published
last_reviewed: 2026-10-11
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Security Scanning in CI/CD

Wire security scanners into your pipelines to catch code-level vulnerabilities (SAST), runtime behaviour (DAST), and risks in containers and IaC.

## Recommended Tools

- **SAST**: Semgrep, CodeQL
- **DAST**: OWASP ZAP, Nikto
- **Containers/IaC**: Trivy, Grype, Checkov, kube-score

## GitHub Actions: Example Workflow

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

## Approval Policies

- Require zero CRITICAL vulnerabilities before merging
- Block deployments when `policy-as-code` fails (OPA/Gatekeeper, Kyverno)

## DAST with OWASP ZAP

```bash
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
  -t https://staging.myapp.example.com \
  -r zap-report.html --minlevel WARN
```

## Best Practices

- Run scans both on PRs and on releases
- Export SARIF and surface alerts in the Security tab
- Use ephemeral (isolated) runners for scans
- Automate exceptions with an expiry date (never open-ended)

## References

- [Semgrep: documentation](https://semgrep.dev/docs/)
- [trivy-action](https://github.com/aquasecurity/trivy-action)
- [checkov-action](https://github.com/bridgecrewio/checkov-action)
- [ZAP: baseline scan with Docker](https://www.zaproxy.org/docs/docker/baseline-scan/)
- [GitHub: uploading a SARIF file](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/uploading-a-sarif-file-to-github)
