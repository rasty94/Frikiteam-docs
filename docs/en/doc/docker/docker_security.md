# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: Docker — Seguridad y Scanning
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

---
