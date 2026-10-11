---
title: "Vulnerability Scanning"
tags: ['cybersecurity', 'vulnerability-scanning']

updated: 2026-01-24
last_reviewed: 2026-01-25
difficulty: intermediate
category: Cybersecurity
status: published
estimated_time: 5 min
prerequisites:
  - "Basic DevOps knowledge"
  - "Intermediate Linux"
---

## Summary

This guide explains how to scan for vulnerabilities in containers, Docker images and application dependencies. It focuses on open-source tools such as Trivy, Clair and Snyk, with integration into CI/CD pipelines.

## Prerequisites

- Basic knowledge of Docker and containers.
- Access to an environment with Docker installed.
- Familiarity with CI/CD pipelines (GitHub Actions, GitLab CI).

## Main Tools

### Trivy

Fast and versatile scanner for vulnerabilities in containers, images, filesystems and repositories.

#### Installation

```bash
# Using brew (macOS)
brew install trivy

# Or download the binary
wget https://github.com/aquasecurity/trivy/releases/latest/download/trivy_$(uname -s)-$(uname -m).tar.gz
tar -xzf trivy_*.tar.gz
sudo mv trivy /usr/local/bin/
```

#### Basic Usage

```bash
# Scan Docker image
trivy image nginx:latest

# Scan running container
trivy container my-container

# Scan filesystem
trivy fs /path/to/project

# JSON output
trivy image --format json --output results.json nginx:latest
```

#### CI/CD Integration

```yaml
# .github/workflows/security-scan.yml
name: Security Scan
on: [push]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
```

### Clair

Static vulnerability scanner for container images, developed by Red Hat.

#### Installation and Usage

Clair requires a PostgreSQL database and is more complex to configure. Trivy is recommended for simple cases.

```bash
# Using Docker
docker run -d --name clair-db -e POSTGRES_PASSWORD=password postgres:13
docker run -d --name clair --link clair-db:postgres -p 6060:6060 quay.io/projectquay/clair:latest
```

### Snyk

Commercial tool with a free tier that scans code, dependencies and containers for vulnerabilities.

#### Installation

```bash
npm install -g snyk
snyk auth  # Authenticate
```

#### Usage

```bash
# Scan dependencies
snyk test

# Scan Docker image
snyk container test nginx:latest

# Monitor project
snyk monitor
```

## Best Practices

- **Regular Scanning:** Integrate into pipelines for every commit/PR.
- **False Positives:** Configure exceptions for vulnerabilities that do not apply.
- **Updates:** Keep base images up to date.
- **SBOM:** Generate a Software Bill of Materials for tracking.

## Advanced Examples

### Complete scan script

{% raw %}
```text
#!/bin/bash
# scan.sh

echo "Scanning for vulnerabilities..."

# Trivy on images
for image in $(docker images --format "{{.Repository}}:{{.Tag}}" | grep -v '<none>'); do
  echo "Scanning $image"
  trivy image "$image" --exit-code 1 --no-progress
done

# Snyk on dependencies
if [ -f "package.json" ]; then
  snyk test --severity-threshold=high
fi

echo "Scan completed"
```
{% endraw %}

## References

- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Clair Documentation](https://quay.github.io/clair/)
- [Snyk CLI](https://docs.snyk.io/snyk-cli)
- [OWASP Vulnerability Scanning](https://owasp.org/www-community/Vulnerability_Scanning_Tools)
