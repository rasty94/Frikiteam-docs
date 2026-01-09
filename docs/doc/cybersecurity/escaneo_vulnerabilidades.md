---
title: "Escaneo de Vulnerabilidades"
date: 2026-01-09
tags: [cybersecurity, vulnerability-scanning, trivy, clair, snyk]
draft: false
---

## Resumen

Esta guía explica cómo escanear vulnerabilidades en contenedores, imágenes Docker y dependencias de aplicaciones. Se enfoca en herramientas open-source como Trivy, Clair y Snyk, con integración en pipelines CI/CD.

## Prerrequisitos

- Conocimientos básicos de Docker y contenedores.
- Acceso a un entorno con Docker instalado.
- Familiaridad con pipelines CI/CD (GitHub Actions, GitLab CI).

## Herramientas Principales

### Trivy

Escáner rápido y versátil para vulnerabilidades en contenedores, imágenes, filesystem y repositorios.

#### Instalación

```bash
# Usando brew (macOS)
brew install trivy

# O descarga binaria
wget https://github.com/aquasecurity/trivy/releases/latest/download/trivy_$(uname -s)-$(uname -m).tar.gz
tar -xzf trivy_*.tar.gz
sudo mv trivy /usr/local/bin/
```

#### Uso Básico

```bash
# Escanear imagen Docker
trivy image nginx:latest

# Escanear contenedor corriendo
trivy container my-container

# Escanear filesystem
trivy fs /path/to/project

# Salida en JSON
trivy image --format json --output results.json nginx:latest
```

#### Integración en CI/CD

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

Escáner estático de vulnerabilidades en imágenes de contenedores, desarrollado por Red Hat.

#### Instalación y Uso

Clair requiere una base de datos PostgreSQL y es más complejo de configurar. Se recomienda usar Trivy para casos simples.

```bash
# Usando Docker
docker run -d --name clair-db -e POSTGRES_PASSWORD=password postgres:13
docker run -d --name clair --link clair-db:postgres -p 6060:6060 quay.io/projectquay/clair:latest
```

### Snyk

Herramienta comercial con versión gratuita, escanea vulnerabilidades en código, dependencias y contenedores.

#### Instalación

```bash
npm install -g snyk
snyk auth  # Autenticarse
```

#### Uso

```bash
# Escanear dependencias
snyk test

# Escanear imagen Docker
snyk container test nginx:latest

# Monitorizar proyecto
snyk monitor
```

## Mejores Prácticas

- **Escaneo Regular:** Integrar en pipelines para cada commit/PR.
- **Falsos Positivos:** Configurar excepciones para vulnerabilidades no aplicables.
- **Actualizaciones:** Mantener imágenes base actualizadas.
- **SBOM:** Generar Software Bill of Materials para rastreo.

## Ejemplos Avanzados

### Script de escaneo completo

```text
#!/bin/bash
# scan.sh

echo "Escaneando vulnerabilidades..."

# Trivy en imágenes
for image in $(docker images --format "{{.Repository}}:{{.Tag}}" | grep -v '<none>'); do
  echo "Escaneando $image"
  trivy image "$image" --exit-code 1 --no-progress
done

# Snyk en dependencias
if [ -f "package.json" ]; then
  snyk test --severity-threshold=high
fi

echo "Escaneo completado"
```

## Referencias

- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Clair Documentation](https://quay.github.io/clair/)
- [Snyk CLI](https://docs.snyk.io/snyk-cli)
- [OWASP Vulnerability Scanning](https://owasp.org/www-community/Vulnerability_Scanning_Tools)