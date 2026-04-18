---
title: "MikroTik CHR (Cloud Hosted Router)"
description: "Guía rápida para desplegar MikroTik CHR orientado a routing L3 y labs ISP/WISP"
tags: ['networking', 'mikrotik', 'chr']
updated: 2026-04-18
difficulty: advanced
estimated_time: 10 min
category: Redes
status: published
last_reviewed: 2026-04-18
prerequisites:
  - "Fundamentos de redes"
  - "Conocimientos básicos de virtualización"
  - "Conceptos de routing dinámico"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

MikroTik CHR destaca cuando necesitas rendimiento L3 y funciones de routing avanzadas con coste contenido.

## Cuándo elegir MikroTik CHR

- Escenarios ISP/WISP o laboratorios carrier
- Necesidad de políticas routing avanzadas
- Equipos con experiencia en RouterOS

## Despliegue recomendado

- 2-4 vNIC según topología
- CPU: 2+ vCPU, RAM: 2-4 GB
- Disco: 2-8 GB (según logs/paquetes)
- Licencia CHR ajustada a throughput esperado

## Configuración base

1. Define esquema de interfaces y direcciones.
2. Asegura acceso de administración (ACL + puertos).
3. Configura rutas estáticas o protocolos dinámicos.
4. Aplica filtros de entrada/salida en firewall.
5. Activa backups export/binary y snapshots de VM.

## Buenas prácticas

- Separa plano de gestión y plano de datos.
- Documenta route filters y policy routing.
- Evalúa FastTrack/FastPath con cautela en producción.
- Controla versión de RouterOS para evitar regresiones.

## Riesgos comunes

- Configuraciones rápidas sin control de cambios.
- Falta de límites en servicios de management.
- No validar impacto de upgrades sobre rendimiento.

## Checklist operativo

- ¿Licencia CHR cubre el throughput real?
- ¿Existen filtros anti-spoofing y bogons?
- ¿Se monitoriza CPU, pps y colas?
- ¿Hay procedimiento de rollback por versión?
