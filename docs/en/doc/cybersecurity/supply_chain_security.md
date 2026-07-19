---
title: "Supply Chain Security: SBOM, SLSA and Image Signing"
date: 2026-01-25
updated: 2026-07-18
tags: [security, supply-chain, sbom, slsa, sigstore, cosign]
difficulty: intermediate
estimated_time: 6 min
category: Cybersecurity
status: published
last_reviewed: 2026-01-25
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Software Supply Chain Security

This guide hardens the software lifecycle end to end: generating SBOMs, checking for vulnerabilities, signing and verifying images, and raising your SLSA assurance level.

## Goals

- Generate reproducible SBOMs (Syft)
- Scan for vulnerabilities (Grype/Trivy)
- Sign and verify images (Sigstore/Cosign)
- Record verification evidence (Rekor)
- Raise assurance with SLSA (level 3 recommended)

## SBOMs with Syft

```bash
# Generate an SBOM (CycloneDX or SPDX)
syft packages myapp:latest -o cyclonedx-json > sbom.json

# For repositories
syft dir:./ -o spdx-json > repo-sbom.json
```

Best practices:
- Ship the SBOM as part of your release artifacts
- Version SBOMs and publish them alongside the image
- Validate the format with CycloneDX/SPDX tooling

## Vulnerability Scanning

```bash
# Grype against an image
grype myregistry/myapp:1.2.3 --fail-on high

# Trivy against a Dockerfile and the filesystem
trivy image myregistry/myapp:1.2.3 --severity HIGH,CRITICAL
trivy fs . --security-checks vuln,secret,config
```

CI integration:
- Fail fast with `--fail-on` at high severities
- Export SARIF reports for GitHub Security

## Signing and Verification with Cosign (Sigstore)

```bash
# OIDC login, keyless
cosign login myregistry.example.com

# Keyless signing with OIDC (GitHub/GitLab/Workload Identity)
COSIGN_EXPERIMENTAL=1 cosign sign myregistry/myapp:1.2.3

# Verification (checks identity and provenance)
COSIGN_EXPERIMENTAL=1 cosign verify myregistry/myapp:1.2.3 \
  --certificate-identity "https://github.com/org/repo/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

Recommendations:
- Prefer keyless with OIDC (far less key management)
- Enforce verification inside the cluster (Admission Controller)

## Recording in Rekor

```bash
# Publish the signed artifact to the transparency log
cosign upload blob --yes --rekor-url https://rekor.sigstore.dev signed.json

# Look up the evidence
rekor-cli search --artifact myregistry/myapp:1.2.3
```

## SLSA: Assurance Levels

- SLSA 1: Traceable provenance
- SLSA 2: Controlled build
- SLSA 3: Reproducible builds, isolated build environment
- SLSA 4: End-to-end hardened, independently verified

Practical guidance:
- Build in isolated environments (ephemeral runners)
- Generate provenance (`attestations`) and attach it to the image
- Validate provenance at deploy time (policy-as-code)

## Admission Policies (Kubernetes)

An OPA Gatekeeper example that requires a verified signature:

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8sverifiedimages
spec:
  crd:
    spec:
      names:
        kind: K8sVerifiedImages
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sverifiedimages

        violation[{
          "msg": msg,
          "details": {}}] {
          input.review.kind.kind == "Pod"
          some i
          img := input.review.object.spec.containers[i].image
          not startswith(img, "myregistry.example.com/")
          msg := sprintf("Image not allowed or signature not verified: %s", [img])
        }
```

## Quick Checklist

- SBOM generated and published
- Automated scanning in CI/CD
- Image signing/verification enabled
- Admission policies blocking unverified images
- Evidence recorded in Rekor
- A documented SLSA ≥ 3 target
