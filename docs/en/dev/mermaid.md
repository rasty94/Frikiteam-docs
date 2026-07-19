---
title: Mermaid — Validation and usage
updated: 2026-07-18
---

# Mermaid — Validation and usage

In the FrikiTeam project we use Mermaid for the diagrams included in the documentation. This page explains how to validate diagrams and how to wire them into CI.

## Validation scripts
- There is an `internal/mermaid/tools/check_diagrams.py` script that can be used to validate diagram syntax.

```bash
python3 internal/mermaid/tools/check_diagrams.py
```

> Note: If the script returns an error or produces no output, document its behavior and add a test in CI.

## Best practices
- Write clear diagrams and avoid depending on the container size
- Add comments when the diagram logic is complex
- Use the examples in `internal/mermaid/diagramas_guia.md`

## CI integration
- Add a step that runs the diagram validation as part of the workflow (before `mkdocs build`).

```yaml
# example: steps
- name: Validate diagrams
  run: python3 internal/mermaid/tools/check_diagrams.py
```

## Common problems
- Diagram does not render -> check the syntax or the browser console.
- Style collisions -> review `docs/stylesheets/extra.css`.

---

If you would rather I implement a minimal version of `check_diagrams.py` to validate the presence of `mermaid` blocks in the `md` files, I can do that and add the CI configuration (optional).