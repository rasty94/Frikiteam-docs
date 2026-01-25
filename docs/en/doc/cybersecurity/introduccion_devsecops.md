---
title: Introduction to Cybersecurity in DevOps
date: 2026-01-09
tags: [cybersecurity, devsecops, devops]
draft: false
---

🚧 **TRANSLATION PENDING** - Last updated in Spanish: 2026-01-25


## Overview

This guide introduces DevSecOps—the integration of security into every stage of the software delivery lifecycle. Security shifts left: it starts at planning and coding, not just in production.

## Prerequisites

- Basic DevOps knowledge (CI/CD, containers, infrastructure as code).
- Basic security concepts (authentication, encryption, vulnerabilities).

## What Is DevSecOps?

DevSecOps evolves DevOps by embedding security into each step.

### Core Principles

- **Security is shared:** Dev, Ops, and Security are all accountable.
- **Automation-first:** Security scans baked into CI/CD.
- **Security culture:** Ongoing training and awareness.

## Integrating Security in CI/CD Pipelines

### Typical Stages

1. **Plan:** Threat modeling and security requirements.
2. **Code:** SAST during development.
3. **Build/Test:** Dependency scanning (SCA) and container scanning.
4. **Deploy:** Configuration hardening and compliance checks.
5. **Monitor:** Continuous detection in production.

### Common Tools

- **SAST:** SonarQube, Checkmarx.
- **DAST:** OWASP ZAP, Burp Suite.
- **SCA:** Snyk, Dependabot.
- **Container scanning:** Trivy, Clair.

## Benefits

- Fewer vulnerabilities in production.
- Lower remediation cost (fix early).
- Faster delivery without sacrificing security.
- Higher product trust.

## Example CI Workflow (GitHub Actions)

```yaml
name: DevSecOps Pipeline
on: [push]
jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run SAST
        uses: sonarsource/sonarcloud-github-action@v2
      - name: Dependency check
        uses: dependency-check/Dependency-Check_Action@main
```

## Further Reading

- [OWASP DevSecOps Guideline](https://owasp.org/www-project-devsecops-guideline/)
- [Microsoft DevSecOps](https://learn.microsoft.com/en-us/devops/develop/security/devsecops)
- Book: *The DevOps Handbook* (security chapters)
