---
title: Docker — Seguridad y Scanning
updated: 2026-01-25
difficulty: intermediate
estimated_time: 1 min
category: Contenedores
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Docker — Seguridad (hardening, secrets y scanning)

## Resumen
Buenas prácticas para reducir la superficie de ataque en imágenes Docker y en despliegues.

## Puntos clave
- No almacenar secretos en el `Dockerfile` o en la imagen.
- Usar usuarios no-root dentro de la imagen.
- Escanear imágenes con `trivy` o `docker scan`.
- Hacer builds reproducibles y firmar imágenes si procede.

## Ejemplo: escaneo con Trivy

```bash
trivy image --severity CRITICAL,HIGH myregistry/myimage:tag
```

## Gestión de secretos
- Usa `.env` (con cuidado), Docker secrets o soluciones externas (Vault).
- No añadir archivos `.env` al repositorio.

## Recomendaciones
- Actualizar dependencias regularmente.
- Aplicar políticas de pull/scan en el registry.

##
