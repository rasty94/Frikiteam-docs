---
title: "Supply Chain Security: SBOM, SLSA y Firma de Imágenes"
updated: 2026-10-11
tags: ['cybersecurity', 'supply-chain']
difficulty: intermediate
estimated_time: 6 min
category: Ciberseguridad
status: published
last_reviewed: 2026-10-11
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
syft scan myapp:latest -o cyclonedx-json > sbom.json

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
trivy fs . --scanners vuln,secret,misconfig
```

Integración CI:
- Fail temprano con `--fail-on` en niveles altos
- Exportar reportes SARIF para GitHub Security

## Firma y Verificación con Cosign (Sigstore)

```bash
# Autenticación contra el registro (no es el login OIDC: la firma keyless lo pide sola)
cosign login myregistry.example.com

# Firma keyless con OIDC (GitHub/GitLab/Workload Identity)
cosign sign --yes myregistry/myapp@sha256:<digest>

# Verificación (incluye identidad y provisión)
cosign verify myregistry/myapp@sha256:<digest> \
  --certificate-identity "https://github.com/org/repo/.github/workflows/release.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

Recomendaciones:
- Usar keyless con OIDC (menos gestión de claves)
- Requerir verificación en el clúster (Admission Controller)

## Registro en Rekor

```bash
# Firmar un artefacto suelto: la firma keyless queda registrada en Rekor
cosign sign-blob --yes --bundle release.tar.gz.bundle release.tar.gz

# Buscar evidencia
rekor-cli search --artifact release.tar.gz
```

## SLSA: Niveles de Garantía

- Build L0: sin garantías (la escala de SLSA 1.0 sustituyó a los antiguos niveles 1-4)
- Build L1: existe provenance que describe cómo se construyó el artefacto
- Build L2: build en una plataforma alojada que firma la provenance
- Build L3: plataforma endurecida que aísla los builds entre sí y protege la clave de firma

Guía práctica:
- Build en entornos aislados (ephemeral runners)
- Generar provenance (`attestations`) y asociarlas a la imagen
- Validar provenance en deployment (policy-as-code)

## Políticas de Admisión (Kubernetes)

Ejemplo OPA Gatekeeper que exige firma verificada:

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
