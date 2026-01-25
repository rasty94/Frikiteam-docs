---
title: Terraform — Backend de Estado y Migración
updated: 2026-01-25
difficulty: intermediate
estimated_time: 1 min
category: Infraestructura como Código
status: published
last_reviewed: 2026-01-25
prerequisites:
  - "Conocimientos básicos de DevOps"
  - "Conceptos de cloud"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Terraform — Backend de Estado y Migración

## Resumen
Buenas prácticas para gestionar el estado de Terraform en equipos: backends remotos, locking y migraciones.

## Backends comunes
- S3 + DynamoDB (AWS)
- GCS (Google Cloud Storage)
- Consul

## Migración de state
- Usar `terraform init -backend-config=...` para reconfigurar.
- Hacer backup del state antes de migrar.

## Validación
- Ejecutar `terraform validate` y `terraform plan` en CI.

---
