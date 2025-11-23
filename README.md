# FrikiTeam Docs

Documentación técnica multi‑idioma (ES/EN) basada en MkDocs Material, con blog automático por categorías, archivo temporal y despliegue continuo.

## Estructura del proyecto

```
docs/
  index.md                 # Página de inicio (ES)
  about.md                 # Acerca de (ES)
  blog/
    index.md               # Índice del blog (listado automático por categorías)
    archive.md             # Archivo por año/mes (automático)
    categories.md          # Listado de categorías (automático)
    posts/
      YYYY/
        tu-post.md         # Entrada de blog (ES)
  doc/                     # Documentación técnica (ES)
    ansible/...
    ceph/...
    docker/...
    kubernetes/...
    openstack/...
    terraform/...

docs/en/
  index.md                 # Home (EN)
  about.md                 # About (EN)
  blog/
    index.md               # Blog index (auto categories)
    archive.md             # Archive (auto)
    categories.md          # Categories (auto)
    posts/
      YYYY/
        your-post.md       # Blog post (EN)
  doc/                     # Technical docs (EN)
    ansible/...
    ceph/...
    ...

mkdocs.yml                 # Configuración del sitio
macros.py                  # Macros para blog automático (listados, archivo, categorías)
scripts/new_post.sh        # Script para crear posts
```

Notas clave:
- Idioma por defecto: Español en la raíz `docs/`. Inglés bajo `docs/en/`.
- Rutas internas consistentes: usa `doc/...` en ambos idiomas para facilitar enlaces.
- El blog no requiere plugin externo: se generan listados con `macros.py`.

## Requisitos

- Python 3.10+
- mkdocs-material, mkdocs-static-i18n, mkdocs-macros-plugin, mkdocs-minify-plugin

## Características

- **Multi-idioma**: Soporte completo para español e inglés
- **Blog automático**: Generación automática de listados, archivos y categorías
- **Diagramas Mermaid**: Soporte completo para diagramas técnicos
- **Tema responsive**: Adaptado para dispositivos móviles y escritorio
- **Navegación avanzada**: Tabs, búsqueda y navegación instantánea

Instalación en local (opcional pero recomendado con venv):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Servir en local:

```bash
source venv/bin/activate
mkdocs serve
```

## i18n (multi‑idioma)

- Español: archivos bajo `docs/`.
- Inglés: archivos equivalentes bajo `docs/en/`.
- Añade contenidos de EN espejando la misma ruta que ES. Ej.:
  - ES: `docs/doc/docker/docker_base.md`
  - EN: `docs/en/doc/docker/docker_base.md`

## Blog (automático)

El blog lista entradas y categorías automáticamente mediante macros Jinja en `macros.py`:
- `docs/blog/index.md` y `docs/en/blog/index.md` usan: `{{ blog_list(group_by_category=True) }}`
- `docs/blog/archive.md` y `docs/en/blog/archive.md` usan: `{{ blog_archive() }}`
- `docs/blog/categories.md` y `docs/en/blog/categories.md` usan: `{{ blog_categories() }}`

### Crear un nuevo post de blog

Usa el script para generar la estructura y el front‑matter:

```bash
scripts/new_post.sh "Título del post" 2025-08-24 general es
scripts/new_post.sh "Post title" 2025-08-24 general en
```

Parámetros:
- Título (obligatorio)
- Fecha `YYYY-MM-DD` (obligatorio)
- Categoría (opcional, por defecto `General`)
- Idioma `es` | `en` (opcional, por defecto `es`)

Ubicación de los posts:
- ES: `docs/blog/posts/YYYY/`
- EN: `docs/en/blog/posts/YYYY/`

Front‑matter mínimo del post:

```yaml
---
date: 2025-08-24
title: "Bienvenida"
categories:
  - General
---
```

## Diagramas Mermaid

La documentación incluye soporte completo para diagramas Mermaid, permitiendo crear diagramas técnicos directamente en Markdown.

### Tipos de Diagramas Soportados

- **Flowcharts**: Diagramas de flujo
- **Sequence Diagrams**: Diagramas de secuencia
- **Class Diagrams**: Diagramas de clases
- **State Diagrams**: Diagramas de estado
- **Entity-Relationship**: Diagramas entidad-relación
- **Git Graphs**: Diagramas de Git
- **Gantt Charts**: Diagramas de Gantt
- **Pie Charts**: Gráficos de tarta

### Verificación de Diagramas

Usa el script incluido para verificar la sintaxis de todos los diagramas:

```bash
python3 scripts/check_diagrams.py
```

### Documentación

Consulta la [Guía de Diagramas Mermaid](diagramas_guia.md) para más información sobre sintaxis y mejores prácticas.

## Flujo de trabajo de contribución

1. Crea una rama desde `main`: `feat/...`, `fix/...` o `docs/...`.
2. Edítalo en local y verifica con `mkdocs serve`.
3. Para diagramas, verifica la sintaxis con `python3 scripts/check_diagrams.py`.
4. Sube la rama y abre un Pull Request.
5. Al aprobarse, se fusiona en `main` para desplegar.

Convenciones:
- Enlaces relativos consistentes (no usar rutas absolutas del sitio).
- Mantén el mismo árbol en ES y EN cuando apliquen traducciones.
- Verifica la sintaxis de diagramas Mermaid antes de hacer commit.

## CI/CD (despliegue)

El sitio está preparado para una publicación automática (p. ej. GitHub Pages con dominio personalizado `docs.frikiteam.es` y `docs/CNAME`).

### Recomendación de pipeline (GitHub Actions)

Archivo de ejemplo `.github/workflows/deploy.yml`:

```yaml
name: deploy
on:
  push:
    branches: [ main ]
  workflow_dispatch: {}

jobs:
  build-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Build
        run: mkdocs build --strict
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
          cname: docs.frikiteam.es
```

Notas CI/CD:
- `--strict` ayuda a detectar enlaces rotos en CI.
- Para previsualización en PRs, añade un job que suba `site/` como artifact.
- Si usas otra plataforma (Cloudflare Pages, Netlify), configura el build command `mkdocs build` y output `site/`.

## Sincronización con WordPress

Para sincronizar artículos de la documentación a WordPress:

1. Configura las variables de entorno (copia `.env.example` a `.env` y edita):

   ```bash
   export WP_SITE_URL=https://frikiteam.es
   export WP_USERNAME=tu_usuario
   export WP_APP_PASSWORD=tu_app_password
   ```

2. Ejecuta el script:
   - Modo interactivo: `python wordpress_sync.py --interactive` (permite buscar por título o nombre de archivo)
   - Archivo específico: `python wordpress_sync.py --file docs/doc/docker/docker_base.md --status draft`

El script actualizará automáticamente `TODO.md` con el progreso de publicación.
