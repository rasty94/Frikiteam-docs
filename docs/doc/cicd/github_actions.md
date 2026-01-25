---
title: "Introducción a GitHub Actions"
description: "Documentación sobre introducción a github actions"
tags: ['documentation']
updated: 2026-01-25
---

# Introducción a GitHub Actions

GitHub Actions es una plataforma de Integración Continua y Despliegue Continuo (CI/CD) que permite automatizar tu flujo de trabajo de construcción, pruebas y despliegue.

## Conceptos Clave

- **Workflow**: Proceso automatizado configurable (archivo YAML en `.github/workflows`).
- **Event**: Actividad que dispara el workflow (ej. `push`, `pull_request`).
- **Job**: Conjunto de pasos que se ejecutan en el mismo runner.
- **Step**: Tarea individual (comando shell o acción).

## Ejemplo: Build y Test de Python

```yaml
name: Python application

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.x"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Test with pytest
        run: |
          pytest
```

## Ejemplo: Despliegue de MkDocs

Este es el workflow usado en este mismo repositorio para desplegar la documentación:

```yaml
name: ci
on:
  push:
    branches:
      - master
      - main
permissions:
  contents: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"
      - run: pip install -r requirements.txt
      - run: mkdocs gh-deploy --force
```
