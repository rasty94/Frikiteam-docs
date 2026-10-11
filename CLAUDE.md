# Frikiteam-docs

Sitio MkDocs Material bilingüe (ES primero, EN espejo) de infraestructura, DevOps,
redes, storage, seguridad e IA. Una sola persona lo mantiene. La prioridad es que lo
publicado sea correcto y verificable, no que haya mucho.

## Entorno y verificación

- El entorno es `.venv`, no `venv`. `source .venv/bin/activate`.
- Antes de dar algo por terminado, ejecuta lo mismo que la CI, en este orden:

  ```bash
  mkdocs build --strict
  python scripts/validate_metadata.py --strict   # vocabularios, borradores, campos y fechas ES/EN, estimated_time
  python scripts/check_sync.py --strict          # fechas, asimetría de tamaño y EN con el cuerpo en español
  python test_wordpress_format.py
  ```

- `./validate_mermaid.sh` renderiza todos los diagramas y tarda minutos: lánzalo en
  segundo plano y solo si has tocado diagramas.
- Verifica los problemas de renderizado sobre `site/*.html`, no sobre el fuente. Los
  fallos del plugin de macros son invisibles en el Markdown.
- Nunca ejecutes más de un `mkdocs build` a la vez. Si despachas agentes en paralelo,
  diles que no compilen y compila tú una vez al final.

## Árbol bilingüe

- Cada `docs/doc/**/x.md` tiene su gemela en `docs/en/doc/**/x.md`, y `docs/x.md` en
  `docs/en/x.md`. Misma estructura, mismas secciones, mismos bloques de código, mismo
  número de líneas aproximado. Los enlaces relativos se mantienen idénticos.
- `updated`, `last_reviewed` y `tags` deben ser iguales en las dos; lo exige
  `validate_metadata.py --strict`. `check_sync.py --strict` falla si el tamaño difiere
  más de un 40% o si la prosa de una EN sigue en español, pero una traducción a medias
  del mismo tamaño pasa: comprueba la paridad de secciones y bloques tú mismo.
- `category` va traducida según `CATEGORY_VOCABULARY` en `scripts/validate_metadata.py`.
  Los tags son los mismos en ambos idiomas.
- Si un agente muere a medias, lo típico es ES escrito y EN sin tocar. Revisa antes de
  seguir; `check_sync.py` lo señala como desincronizado.

## Frontmatter

- `tags` solo de `TAG_VOCABULARY` (76) y `category` solo de `CATEGORY_VOCABULARY` (15),
  ambos en `scripts/validate_metadata.py`. Un tag nuevo se justifica con 2-3 páginas.
- `draft: true` **excluye la página del sitio** (`hooks/drafts.py`): nav, buscador e
  índice de tags. Debe ir en los dos idiomas o en ninguno, y hay que quitar antes los
  enlaces entrantes o `--strict` falla. El estado editorial normal se lleva en `status`.
- `date:` y `draft: false` aparecen en páginas antiguas y no los lee nadie. No los
  añadas. La plantilla completa está en `TODO.md`, sección "Convenciones".
- `estimated_time` lo ve el lector como badge: 150 palabras/min de prosa más 5 s por
  línea de código, igual en ES y EN. `--strict` falla si se aleja de la fórmula;
  `python scripts/validate_metadata.py --fix-reading-time` lo recalcula en las dos.
  No lo repitas a mano en el cuerpo de la página.

## Jinja dentro de bloques de código

El plugin `macros` pasa cada página por Jinja2 antes que Markdown, también dentro de
los bloques de código. Envuelve el bloque entero en `{% raw %}` … `{% endraw %}` cuando
contenga:

- `{{ … }}`: plantillas Go, Helm, Grafana, Ansible. Una variable indefinida no rompe
  (`on_undefined: keep`) pero sale con los espacios normalizados; `{{ obj.campo }}` sí
  rompe.
- `{% … %}`: bloques de control de Ansible/Jinja.
- `{#`: **el peligroso**. `${#array[@]}` abre un comentario Jinja; si más adelante hay
  un `#}`, se borra todo lo de en medio sin error. Si no lo hay, el build muere.

`${VAR}` y `$(cmd)` son inofensivos. Para mostrar `{% raw %}` literalmente en una página
usa `{{ "{% raw %}" }}`. Nunca escribas el cercado ```` ```mermaid ```` completo dentro
de prosa: el `awk` de `validate_mermaid.sh` se cree que empieza un diagrama.

## Escribir contenido

- Referencia de calidad: `docs/doc/docker/quadlets.md` (unas 330 líneas). Estructura:
  H1, «El problema», tabla de contenidos, secciones técnicas, «Troubleshooting» con
  tabla síntoma → causa → arreglo, «Buenas prácticas», «Referencias».
- Una página de menos de 40 líneas con título ambicioso es deuda, no contenido.
- No inventes versiones, flags ni salidas de comando. Cuando algo dependa de la
  versión, dilo en el texto con un aviso. Describe errores en prosa en vez de fabricar
  transcripciones. El repo registra en `TODO.md` lo "escrito de conocimiento, no
  probado" como deuda; no la amplíes.
- Las páginas de la sección Programación se escriben desde el ángulo de construir,
  empaquetar y desplegar sobre la infraestructura del sitio, no de enseñar el framework.
- Contenido nuevo lleva entrada fechada en «Últimas Novedades» de `docs/index.md` y
  `docs/en/index.md`, en el mismo commit.

## Commits

- Directo a `main`. No hagas `push` sin que te lo pidan.
- `docs:` para contenido, `feat(ci):`/`feat:` para tooling, `chore(meta):` para cambios
  que solo tocan frontmatter o metadatos. **El prefijo `chore(meta):` no es decorativo**:
  `check_freshness.py` lo ignora al calcular qué páginas llevan tiempo sin revisar. Un
  cambio masivo de metadatos sin él marca como recién revisadas páginas que nadie leyó.
- Separa contenido y metadatos en commits distintos cuando toques las dos cosas.

## Registro de trabajo

- `TODO.md`: solo pendientes, con cifras verificadas contra el repo y fecha. Cuando
  cierres algo, quítalo de ahí y anótalo en `done.md` con qué se hizo y qué se
  comprobó. Si un resumen anterior resultó inexacto, corrígelo con una nota fechada en
  vez de reescribir la historia.
- Antes de proponer contenido nuevo, `grep` el repo: varias tareas del roadmap ya
  estaban cubiertas cuando se listaron.


## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- `graphify update .` solo reextrae código (AST). Los Markdown se reindexan con
  `/graphify --update`, que usa LLM; el `manifest.json` apenas conserva `semantic_hash`,
  así que ese paso querrá reprocesar todo el corpus. Comprueba el coste antes.
