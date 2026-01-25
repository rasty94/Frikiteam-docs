---
title: "Supply Chain Security: SBOM, SLSA y Firma de Imágenes"
date: 2026-01-25
updated: 2026-01-25
tags: [security, supply-chain, sbom, slsa, sigstore, cosign]
difficulty: intermediate
estimated_time: 6 min
category: Ciberseguridad
status: published
last_reviewed: 2026-01-25
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Seguridad de la Cadena de Suministro (Supply Chain)

Esta guía refuerza la seguridad end-to-end del ciclo de software: generación de SBOMs, verificación de vulnerabilidades, firma/verificación de imágenes y niveles de garantía SLSA.

## Objetivos

- Generar SBOMs reproducibles (Syft)
- Escanear vulnerabilidades (Grype/Trivy)
- Firmar y verificar imágenes (Sigstore/Cosign)
- Registrar evidencia de verificación (Rekor)
- Elevar garantías con SLSA (nivel 3 recomendado)

## SBOMs con Syft

```bash
# Generar SBOM (CycloneDX o SPDX)
syft packages myapp:latest -o cyclonedx-json > sbom.json

# Para repositorios
syft dir:./ -o spdx-json > repo-sbom.json
```

Buenas prácticas:
- Incluir SBOM en artefactos de release
- Versionar SBOMs y publicarlos junto a la imagen
- Validar formato con herramientas CycloneDX/SPDX

## Escaneo de Vulnerabilidades

```bash
# Grype contra imagen
grype myregistry/myapp:1.2.3 --fail-on high

# Trivy contra Dockerfile y FS
trivy image myregistry/myapp:1.2.3 --severity HIGH,CRITICAL
trivy fs . --security-checks vuln,secret,config
```

Integración CI:
- Fail temprano con `--fail-on` en niveles altos
- Exportar reportes SARIF para GitHub Security

## Firma y Verificación con Cosign (Sigstore)

```bash
# Login OIDC y keyless
cosign login myregistry.example.com

# Firma keyless con OIDC (GitHub/GitLab/Workload Identity)
COSIGN_EXPERIMENTAL=1 cosign sign myregistry/myapp:1.2.3

# Verificación (incluye identidad y provisión)
COSIGN_EXPERIMENTAL=1 cosign verify myregistry/myapp:1.2.3 \
  --certificate-identity "https://github.com/org/repo/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

Recomendaciones:
- Usar keyless con OIDC (menos gestión de claves)
- Requerir verificación en el clúster (Admission Controller)

## Registro en Rekor

```bash
# Publicar artefacto firmado en transparencia log
cosign upload blob --yes --rekor-url https://rekor.sigstore.dev signed.json

# Buscar evidencia
rekor-cli search --artifact myregistry/myapp:1.2.3
```

## SLSA: Niveles de Garantía

- SLSA 1: Origen rastreable
- SLSA 2: Build controlado
- SLSA 3: Builds reproducibles, aislamiento de entorno
- SLSA 4: End-to-end hardened, verificaciones independientes

Guía práctica:
- Build en entornos aislados (ephemeral runners)
- Generar provenance (`attestations`) y asociarlas a la imagen
- Validar provenance en deployment (policy-as-code)

## Políticas de Admisión (Kubernetes)

Ejemplo OPA Gatekeeper que exige firma verificada:

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
          msg := sprintf("Imagen no permitida o sin firma verificada: %s", [img])
        }
```

## Checklist Rápido

- SBOM generado y publicado
- Escaneo automático en CI/CD
- Firma/verificación de imágenes habilitada
- Políticas de admisión que bloquean imágenes no verificadas
- Evidencias registradas en Rekor
- Objetivo SLSA ≥ 3 documentado
