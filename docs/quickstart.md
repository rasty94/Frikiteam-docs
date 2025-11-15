---
title: Quickstart — Arranca y contribuye
summary: Guía rápida para poner en marcha el sitio y contribuir con contenido.
---

# Quickstart — Arranca y contribuye

Este documento ayuda a que un nuevo contribuidor ponga en marcha el sitio y aporte contenido en menos de 10 minutos.

## Prerrequisitos
- Python 3.10+ (recomendado)
- Git
- Opcional: Docker (para ejemplos de contenedores)

## Preparar entorno (recomendado con virtualenv)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Servir localmente

```bash
mkdocs serve
# Abre http://127.0.0.1:8000 en tu navegador
```

## Compilar el sitio

```bash
mkdocs build
# La salida queda en la carpeta 'site/'
```

## Ejemplo rápido con Docker (ver contenido en el sitio)

```bash
# Ejecuta un nginx de ejemplo
docker run --rm -p 8080:80 nginx
# Abre http://127.0.0.1:8080
```

## Crear un post (blog)

Usa el script que viene en `scripts/new_post.sh` para crear posts del blog con front-matter básico:

```bash
./scripts/new_post.sh "Mi nuevo post" 2025-11-15 general es
```

Luego edita el archivo creado en `docs/blog/posts/` o `docs/en/blog/posts/` y crea contenido.

## Comprobar y enviar cambios

- Revisa enlaces y errores con `mkdocs build`.
- Si todo está bien, crea un PR siguiendo `CONTRIBUTING.md`.

---

Si quieres, puedo añadir comandos de prueba y ejemplos adicionales (ej.: pre-commit hooks, linters).