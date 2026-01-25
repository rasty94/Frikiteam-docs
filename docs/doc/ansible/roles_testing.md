---
title: Ansible — Roles y Testing con Molecule
updated: 2026-01-25
difficulty: intermediate
estimated_time: 1 min
category: Automatización
status: published
last_reviewed: 2026-01-25
prerequisites:
  - "Conocimientos básicos de DevOps"
  - "SSH y Linux básico"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Ansible — Roles y Testing con Molecule

## Resumen
Guía rápida para organizar roles y probarlos con `molecule` en local y en CI.

## Estructura recomendada
- roles/
  - myrole/
  - tasks/
  - handlers/
  - defaults/
  - meta/
  - tests/

## Molecule
- Usa `molecule init role -r myrole -d docker` para crear scaffolding.
- Ejecuta `molecule test` en local o en CI.

## Integración en CI
- Añade pasos en el workflow para ejecutar `molecule test` en un runner adecuado.

---
