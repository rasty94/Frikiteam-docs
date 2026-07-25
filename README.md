# FrikiTeam Docs

Documentación técnica multi‑idioma (ES/EN) basada en MkDocs Material, con despliegue continuo. Las entradas de blog se publican en frikiteam.es vía `wordpress_sync.py`.

## Estructura del proyecto

```
docs/
  index.md                 # Página de inicio (ES)
  about.md                 # Acerca de (ES)
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
  doc/                     # Technical docs (EN)
    ansible/...
    ceph/...
    ...

mkdocs.yml                 # Configuración del sitio
macros.py                  # Macros (metadatos, badges de sincronización)
```

Notas clave:

- Idioma por defecto: Español en la raíz `docs/`. Inglés bajo `docs/en/`.
- Rutas internas consistentes: usa `doc/...` en ambos idiomas para facilitar enlaces.

## Requisitos

- Python 3.10+
- mkdocs-material, mkdocs-static-i18n, mkdocs-macros-plugin, mkdocs-minify-plugin

## Características

- **Multi-idioma**: Soporte completo para español e inglés
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
python3 internal/mermaid/tools/check_diagrams.py
```

### Documentación

Consulta la [Guía de Diagramas Mermaid](diagramas_guia.md) para más información sobre sintaxis y mejores prácticas.

## Flujo de trabajo de contribución

1. Crea una rama desde `main`: `feat/...`, `fix/...` o `docs/...`.
2. Edítalo en local y verifica con `mkdocs serve`.
3. Para diagramas, verifica la sintaxis con `python3 internal/mermaid/tools/check_diagrams.py`.
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
