---
title: Troubleshooting — Errores Comunes y Soluciones
description: Soluciones a problemas comunes en MkDocs, Docker, Kubernetes, Ansible y otras tecnologías. Guía de debugging y resolución de errores.
keywords: troubleshooting, errores, debugging, problemas comunes, soluciones, mkdocs, docker, kubernetes
tags: [troubleshooting, errores, debugging, soporte]
---

# Troubleshooting — Errores Comunes y Soluciones

Este documento recoge problemas y soluciones comunes al trabajar con la documentación y el sitio MkDocs.

## Error: "Config value 'plugins': The 'minify' plugin is not installed"
- Causa: El plugin `mkdocs-minify-plugin` no está instalado en el entorno.
- Solución:
  - Instalar localmente:

```bash
pip install mkdocs-minify-plugin
```
  - O eliminar/comentar `minify` en `mkdocs.yml` si no estás listo para instalarlo.

## Problemas de rutas de assets (logo, css, js)
- Causa: Rutas relativas que no existen en `docs/`.
- Solución: Asegúrate de que los archivos referenciados en `mkdocs.yml` existan en `docs/` (por ejemplo `docs/images/logo.png`, `docs/stylesheets/extra.css`).

## Problemas de Mermaid (diagramas no renderizados)
- Causa: Errores de sintaxis o plugins faltantes.
- Solución:
  - Ejecutar el script de verificación (si existe) o revisar la consola del navegador.
  - Usa `internal/mermaid/diagramas_guia.md` para revisar ejemplos y `internal/mermaid/tools/check_diagrams.py` para verificaciones automáticas.

## Enlaces rotos
- Solución: Ejecuta `mkdocs build` y revisa las advertencias/errores. Usa comprobadores de enlaces en CI.

## Otros
- Reporta fallos en Issues o crea una PR con un fix y referencia `TODO.md` para añadir nuevas tareas o posts de documentación.
