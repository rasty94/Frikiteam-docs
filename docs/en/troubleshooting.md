---
title: Troubleshooting — Common Errors and Solutions
---

# Troubleshooting — Common Errors and Solutions

This document collects common problems and solutions when working with the documentation and MkDocs site.

## Error: "Config value 'plugins': The 'minify' plugin is not installed"
- Cause: The `mkdocs-minify-plugin` plugin is not installed in the environment.
- Solution:
  - Install locally:

```bash
pip install mkdocs-minify-plugin
```
  - Or remove/comment `minify` in `mkdocs.yml` if you're not ready to install it.

## Asset path problems (logo, css, js)
- Cause: Relative paths that don't exist in `docs/`.
- Solution: Make sure the files referenced in `mkdocs.yml` exist in `docs/` (for example `docs/images/logo.png`, `docs/stylesheets/extra.css`).

## Mermaid problems (diagrams not rendering)
- Cause: Syntax errors or missing plugins.
- Solution:
  - Run the verification script (if it exists) or check the browser console.
  - Use `internal/mermaid/diagramas_guia.md` to review examples and `internal/mermaid/tools/check_diagrams.py` for automated checks.

## Broken links
- Solution: Run `mkdocs build` and check warnings/errors. Use link checkers in CI.

## Others
- Report issues in Issues or create a PR with a fix and reference `TODO.md` to add new documentation tasks or posts.