# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: Terraform — Backend de Estado y Migración
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
