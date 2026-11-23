---
title: "Mermaid — Verificación y uso"
description: "Cómo validar diagramas Mermaid en local y en GitHub Actions usando mermaid-cli y validate_mermaid.sh."
tags: ['documentation']
updated: 2026-11-23
---

# Mermaid — Verificación y uso

## El problema

MkDocs no valida la sintaxis de los diagramas Mermaid durante `mkdocs build`: un paréntesis sin comillas o una flecha mal cerrada pasa la compilación en verde y solo se descubre cuando alguien abre la página en el navegador y ve un bloque de error.

En FrikiTeam validamos todos los diagramas antes de publicar usando `@mermaid-js/mermaid-cli` (`mmdc`) y el script `validate_mermaid.sh` de la raíz del repositorio.

## Validación en local

Instala la misma versión fijada en CI (fijamos la mayor para evitar cambios de sintaxis entre versiones):

```bash
npm install -g @mermaid-js/mermaid-cli@12
```

Después ejecuta el validador desde la raíz de `Frikiteam-docs`:

```bash
./validate_mermaid.sh
```

El script recorre todos los ficheros `.md` bajo `docs/`, extrae cada bloque Mermaid con `awk` y lo renderiza contra Chromium headless mediante:

```bash
printf "%b" "$diagram" | mmdc -i /dev/stdin -o "$tmp_out" -p puppeteer-config.json
```

Si todos los diagramas renderizan sin error, descarta las salidas temporales y termina con código `0`. Si falla alguno, muestra el fichero y el bloque afectado y devuelve código distinto de cero.

## Integración en CI

El workflow `.github/workflows/docs-ci.yml` incluye el job `quality`, que ejecuta la validación en cada `push` y `pull_request` sobre `main`:

```yaml
- run: npm install -g @mermaid-js/mermaid-cli@12
- name: Validate Mermaid diagrams
  run: ./validate_mermaid.sh
```

## Buenas prácticas

- **Entrecomilla las etiquetas con caracteres especiales**: paréntesis, corchetes o dos puntos dentro de un nodo suelen romper el parser si no van entre comillas (`A["API (v2)"]`).
- **Mantén cada diagrama acotado**: si un diagrama supera ~15 nodos, suele ser más legible dividirlo en dos vistas (arquitectura general y flujo concreto).
- **No pongas fences literales de Mermaid en texto de ejemplo**: el extractor de `validate_mermaid.sh` busca líneas que abran bloque Mermaid en todo `docs/` e intentaría compilarlo.
- **Valida siempre antes del commit**: ejecutar `./validate_mermaid.sh` en local ahorra rondas de CI.

## Problemas comunes

- **El diagrama no se renderiza en el navegador**: revisa la salida de `./validate_mermaid.sh` o la consola del navegador; casi siempre es un carácter reservado sin comillas o un tipo de diagrama no soportado por la versión de Mermaid de MkDocs Material.
- **`mmdc` falla al arrancar Chromium en Linux/CI**: asegúrate de pasar `-p puppeteer-config.json` (el script ya lo incluye) para desactivar el sandbox cuando corre en contenedores sin privilegios.
- **Colisión de estilos en el tema**: revisa `docs/stylesheets/extra.css` si un diagrama aparece recortado o con contraste bajo en modo oscuro.
