---
title: Mermaid — Verificación y uso
---

# Mermaid — Verificación y uso

En el proyecto FrikiTeam utilizamos Mermaid para diagramas incluidos en la documentación. Aquí te explico cómo verificar diagramas y cómo integrarlos en CI.

## Scripts de verificación
- Existe `internal/mermaid/tools/check_diagrams.py` que se puede usar para validar la sintaxis de los diagramas.

```bash
python3 internal/mermaid/tools/check_diagrams.py
```

> Nota: Si el script devuelve un error o está vacío, documenta su comportamiento y añade un test en CI.

## Mejores prácticas
- Escribe diagramas claros y evita dependencias del tamaño del contenedor
- Añade comentarios cuando la lógica del diagrama sea compleja
- Usa los ejemplos de `internal/mermaid/diagramas_guia.md`

## Integración en CI
- Añadir un paso que ejecute la verificación de diagramas como parte del workflow (antes de `mkdocs build`).

```yaml
# ejemplo: steps
- name: Verificar diagramas
  run: python3 internal/mermaid/tools/check_diagrams.py
```

## Problemas comunes
- Diagrama no se renderiza -> validar sintaxis o la consola del navegador.
- Colisión de estilos -> revisar `docs/stylesheets/extra.css`.

---

Si prefieres que implemente una versión mínima del `check_diagrams.py` para validar la existencia de bloques `mermaid` en los `md`, lo puedo hacer y añadir la configuración en CI (opcional).