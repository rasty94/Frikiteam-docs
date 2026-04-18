---
title: "MikroTik CHR (enrutador en la nube)"
description: "Guía rápida para desplegar MikroTik CHR orientado a enrutamiento L3 y laboratorios ISP/WISP"
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
  - "Conceptos de enrutamiento dinámico"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

MikroTik CHR destaca cuando necesitas rendimiento L3 y funciones de enrutamiento avanzadas con coste contenido.

## Cuándo elegir MikroTik CHR

- Escenarios ISP/WISP o laboratorios de operador
- Necesidad de políticas de enrutamiento avanzadas
- Equipos con experiencia en RouterOS

## Despliegue recomendado

- 2-4 vNIC según topología
- CPU: 2+ vCPU, RAM: 2-4 GB
- Disco: 2-8 GB (según logs/paquetes)
- Licencia CHR ajustada al rendimiento esperado

## Configuración base

1. Define esquema de interfaces y direcciones.
2. Asegura acceso de administración (ACL + puertos).
3. Configura rutas estáticas o protocolos dinámicos.
4. Aplica filtros de entrada/salida en firewall.
5. Activa copias export/binarias e instantáneas de la máquina virtual.

## Buenas prácticas

- Separa plano de gestión y plano de datos.
- Documenta filtros de rutas y enrutamiento por políticas.
- Evalúa FastTrack/FastPath con cautela en producción.
- Controla versión de RouterOS para evitar regresiones.

## Riesgos comunes

- Configuraciones rápidas sin control de cambios.
- Falta de límites en servicios de gestión.
- No validar el impacto de las actualizaciones sobre el rendimiento.

## Lista de comprobación operativa

- ¿La licencia CHR cubre el rendimiento real?
- ¿Existen filtros anti-spoofing y bogons?
- ¿Se monitoriza CPU, paquetes/s y colas?
- ¿Hay procedimiento de reversión por versión?
