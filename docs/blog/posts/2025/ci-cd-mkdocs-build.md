---
title: CI/CD — Validando MkDocs y build de contenedores
summary: Ejemplo de workflow que instala dependencias, valida `mkdocs build`, ejecuta verificación de diagramas y construye imágenes de contenedor.
---

# CI/CD: Validando MkDocs y Build de contenedores

Este post describe un workflow de ejemplo (GitHub Actions) que:

- instala dependencias desde `requirements.txt`
- ejecuta verificación de diagramas Mermaid
- ejecuta `mkdocs build` para validar la documentación
- construye y publica imágenes de contenedor (opcional)

## Pasos clave
1. Preparar entorno (Python + venv) e instalar `pip install -r requirements.txt`.
2. Ejecutar verificación de diagramas: `python3 internal/mermaid/tools/check_diagrams.py`.
3. Ejecutar `mkdocs build` y fallar si hay errores.
4. Construir imágenes Docker y publicar en un registry (opcional).

## Ejemplo de workflow (sintético)

```yaml
name: docs-ci
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install deps
        run: |
          python -m venv .venv
          source .venv/bin/activate
          pip install -r requirements.txt
      - name: Verify mermaid diagrams
        run: python3 internal/mermaid/tools/check_diagrams.py || true
      - name: Build site
        run: |
          source .venv/bin/activate
          mkdocs build
```

## Consideraciones
- Añadir comprobación de enlaces y pruebas adicionales según sea necesario.
- Para previews, usar acciones que desplieguen en entornos temporales.

---

Si quieres, creo el archivo `.github/workflows/docs-ci.yml` con esta configuración de ejemplo.