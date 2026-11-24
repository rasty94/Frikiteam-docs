# Roadmap de Documentación Frikiteam

Este documento rastrea las tareas pendientes y mejoras planificadas. El historial de tareas completadas vive en [`done.md`](done.md).

## Diagnóstico (actualizado 2026-11-24)

La estructura está sana y sincronizada; la fuente de verdad vive aquí y el blog (`frikiteam.es`, en Astro) se genera desde estas páginas con `scripts/publish_to_astro.py`.

**Lo que ya está bien (no tocar):**
- 154 páginas ES y 154 EN sincronizadas, todas con frontmatter válido (salvo los `index.md` de navegación excluidos a propósito).
- CI: `mkdocs build --strict`, `validate_metadata.py --strict`, `check_sync.py --strict` y `test_publish_to_astro.py` en el job `build`; Mermaid y enlaces rotos en el job `quality`.
- `draft: true` excluye la página del sitio de verdad (`hooks/drafts.py`), y el validador exige que ambos idiomas coincidan.
- `check_sync.py --strict` falla si una gemela difiere más de un 40% en tamaño o conserva prosa sin traducir.
- Vocabularios cerrados y validados: 76 tags y 15 categorías, comprobando que la traducción EN coincide con la ES.
- Señal de frescura derivada de `git log`, ignorando los commits `chore(meta):` (`check_freshness.py` en 0 páginas >90 días).
- Badges de metadatos renderizados directamente en `overrides/main.html` (sin `mkdocs-macros-plugin` ni `mkdocs-jupyter`).
- Índice de tags navegable en `docs/tags.md` y `docs/en/tags.md`.

## Plan de mejora (por orden de retorno)

### 1. Deuda de verificación real
- [ ] **OpenSCAP:** los comandos `oscap` y los paquetes SSG de Debian en `doc/cybersecurity/cumplimiento_auditoria.md` no se han probado aún en una máquina Debian real; verificar cuando haya laboratorio disponible.
- [ ] **Evaluar migración a Zensical (antes del 05/05/2027, EOL de Material for MkDocs 9.x):** cuando Zensical incorpore i18n nativo, probar en rama `zensical` (adaptando `hooks/drafts.py` y el despliegue con `actions/deploy-pages`).

### 2. Ampliaciones puntuales en páginas existentes
- [ ] **Cifrado en reposo en cabinas** (Ceph/Pure/NetApp): LUKS ya está a fondo en `cybersecurity/criptografia_aplicada.md`; falta solo el ángulo de cabina.
- [ ] `doc/storage/protocols/protocols.md`: añadir más ejemplos reales de medición y diagnóstico.

### Aparcado: Inteligencia Artificial
AI ya es una de las secciones más grandes del sitio (25 docs). Se mantiene aparcada por prioridad:
- Multi-agent systems, LLMs en edge, seguridad y privacidad (GDPR), observabilidad de costes/latencias, CI/CD para modelos, fine-tuning por dominio, networking para inferencia.

---

### Convenciones para nuevas páginas

- Frontmatter, tal como lo validan `validate_metadata.py` y `check_sync.py`:

    ```yaml
    title: "Título claro"
    description: "Una frase que explique qué resuelve la página"
    keywords: "palabras, clave, separadas, por, comas"
    tags: ['storage', 'ceph']      # solo valores de TAG_VOCABULARY (76)
    updated: 2026-11-24            # debe coincidir con la gemela EN
    last_reviewed: 2026-11-24
    difficulty: intermediate       # beginner | intermediate | advanced | expert
    estimated_time: 20 min
    category: Almacenamiento       # solo valores de CATEGORY_VOCABULARY (15)
    status: published              # draft | review | published | archived
    prerequisites:
      - "Lo que hay que saber antes"
    reviewers: ["@rasty94"]
    contributors: ["@rasty94"]
    ```

    El campo `date:` aparece en páginas antiguas y no lo lee nadie; no lo añadas. `draft: true` excluye la página del sitio (`hooks/drafts.py`). En el árbol EN, `category` va traducido según `CATEGORY_VOCABULARY`; `updated` y `last_reviewed` deben ser idénticos a los de la página ES.

- Estructura recomendada del Markdown:
    1. «El problema» (1–2 párrafos directos)
    2. Tabla de contenidos / prerrequisitos
    3. Explicación técnica con ejemplos reproducibles
    4. Troubleshooting (tabla síntoma → causa → solución)
    5. Buenas prácticas y referencias oficiales

### Checklist de publicación

- [ ] `mkdocs build --strict`: sin avisos ni errores.
- [ ] `python scripts/validate_metadata.py --strict`: tags, categorías, fechas y `estimated_time` válidos en ES y EN.
- [ ] `python scripts/check_sync.py --strict`: sin desincronizados ni asimetría mayor del 40%.
- [ ] `python test_publish_to_astro.py`: correcto.
- [ ] `./validate_mermaid.sh` si has tocado diagramas.
- [ ] Página gemela en el otro idioma con la misma estructura y fechas.
- [ ] Imágenes con texto alternativo (`alt`).
- [ ] Entrada fechada en Novedades de `docs/index.md` y `docs/en/index.md` si es contenido nuevo.

**Prefijo de commit:** si el cambio solo toca frontmatter o metadatos, usa `chore(meta):` para que `check_freshness.py` lo ignore.

---

## Comandos útiles

```bash
# crear/activar entorno (el del repo es .venv)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# servir sitio localmente
mkdocs serve -a 0.0.0.0:8000

# lo mismo que ejecuta la CI
mkdocs build --strict
python scripts/validate_metadata.py --strict
python scripts/check_sync.py --strict
python test_publish_to_astro.py

# generar entradas en frikiteam-astro
python scripts/publish_to_astro.py --write

# informativos, no bloquean
python scripts/check_freshness.py     # páginas sin tocar en 90+ días
./validate_mermaid.sh                 # renderiza todos los diagramas
```
