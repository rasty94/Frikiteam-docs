---
title: "Introducción a GitHub Actions"
description: "Primeros pasos con GitHub Actions: workflows, eventos, jobs, steps y un ejemplo práctico de build y tests en Python."
tags: ['ci-cd', 'automation']
updated: 2026-10-11
difficulty: intermediate
estimated_time: 1 min
category: DevOps
status: published
last_reviewed: 2026-10-11
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Introducción a GitHub Actions

Compilar a mano, acordarse de pasar los tests antes de cada *push* y subir cambios a producción desde el portátil funciona hasta el primer descuido. GitHub Actions automatiza ese flujo directamente desde el repositorio con archivos YAML que reaccionan a cada cambio. Aquí tienes las piezas básicas y un primer workflow funcional en Python.

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

## Referencias

- [GitHub Actions: documentación](https://docs.github.com/en/actions)
- [Sintaxis de workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [MkDocs: desplegar la documentación](https://www.mkdocs.org/user-guide/deploying-your-docs/)
