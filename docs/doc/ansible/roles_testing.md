---
title: Ansible — Roles y Testing con Molecule
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
