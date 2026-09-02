# CONTRIBUTING

Gracias por contribuir a la documentación de FrikiTeam 🥳

## Flujo básico
1. Haz un fork o crea una rama a partir de `main`.
2. Crea una rama con un nombre descriptivo (`feat/doc-quickstart`).
3. Haz tus cambios y prueba localmente:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdocs serve
```

4. Añade tests o verifica diagramas (si procede):

```bash
# Verificar diagramas mermaid (si el script está disponible)
python3 internal/mermaid/tools/check_diagrams.py || true
```

5. Asegúrate de que `mkdocs build` no falla:

```bash
mkdocs build
```

6. Crea un PR y espera revisión. Añade descripción clara y uno o dos puntos que el revisor debe verificar.

## Checklist Antes de Publicar

Mantén simple. Solo lo esencial:

- [ ] **El contenido es correcto** (revisado personalmente)
- [ ] **Los enlaces internos funcionan** (probado localmente)
- [ ] **Tiene ejemplos o código** si aplica
- [ ] **Frontmatter actualizado** (title, date, updated, tags). Los tags salen del vocabulario cerrado en `scripts/validate_metadata.py` (`TAG_VOCABULARY`); comprueba con `python scripts/validate_metadata.py --strict`. Un tag nuevo se justifica con al menos 2-3 páginas que lo usen.
- [ ] **`category`** sale del vocabulario cerrado `CATEGORY_VOCABULARY` (15 valores). El árbol ES usa el nombre en español y el EN su traducción exacta; el validador comprueba que los gemelos coincidan.
- [ ] Si el commit solo toca frontmatter (tags, metadatos), usa el prefijo `chore(meta):` para que `check_freshness.py` no lo cuente como revisión de contenido.
- [ ] **Build sin errores**: `mkdocs build --strict`

## Código de conducta
- Mantén el respeto hacia otros colaboradores.
- Si quieres, podemos añadir un archivo `CODE_OF_CONDUCT.md` más adelante.

Gracias por ayudar a mejorar la documentación 💡