---
title: "Supply Chain Security: SBOM, SLSA and Image Signing"
updated: 2026-10-11
tags: ['cybersecurity', 'supply-chain']
difficulty: intermediate
estimated_time: 6 min
category: Cybersecurity
status: published
last_reviewed: 2026-10-11
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
syft scan myapp:latest -o cyclonedx-json > sbom.json

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
trivy fs . --scanners vuln,secret,misconfig
```

CI integration:
- Fail fast with `--fail-on` at high severities
- Export SARIF reports for GitHub Security

## Signing and Verification with Cosign (Sigstore)

```bash
# Authenticate against the registry (not the OIDC login: keyless signing asks for it itself)
cosign login myregistry.example.com

# Keyless signing with OIDC (GitHub/GitLab/Workload Identity)
cosign sign --yes myregistry/myapp@sha256:<digest>

# Verification (checks identity and provenance)
cosign verify myregistry/myapp@sha256:<digest> \
  --certificate-identity "https://github.com/org/repo/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

Recommendations:
- Prefer keyless with OIDC (far less key management)
- Enforce verification inside the cluster (Admission Controller)

## Recording in Rekor

```bash
# Sign a standalone artifact: the keyless signature is recorded in Rekor
cosign sign-blob --yes --bundle release.tar.gz.bundle release.tar.gz

# Look up the evidence
rekor-cli search --artifact release.tar.gz
```

## SLSA: Assurance Levels

- Build L0: no guarantees (SLSA 1.0 replaced the old levels 1-4 with this track)
- Build L1: provenance exists describing how the artifact was built
- Build L2: build on a hosted platform that signs the provenance
- Build L3: hardened platform that isolates builds from each other and protects the signing key

Practical guidance:
- Build in isolated environments (ephemeral runners)
- Generate provenance (`attestations`) and attach it to the image
- Validate provenance at deploy time (policy-as-code)

## Admission Policies (Kubernetes)

An OPA Gatekeeper example that requires a verified signature:

```yaml
apiVersion: templates.gatekeeper.sh/v1
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

## References

- [SLSA 1.0: levels](https://slsa.dev/spec/v1.0/levels)
- [Sigstore: signing with cosign](https://docs.sigstore.dev/cosign/signing/overview/)
- [Syft](https://github.com/anchore/syft)
- [Grype](https://github.com/anchore/grype)
- [Trivy: documentation](https://trivy.dev/latest/docs/)
- [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/website/docs/)
