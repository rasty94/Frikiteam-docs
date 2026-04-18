---
title: "VyOS (vRouter orientado a automatización)"
description: "Guía rápida para desplegar VyOS con enfoque en BGP/OSPF y automatización"
tags: ['networking', 'vyos', 'automation']
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

VyOS encaja muy bien en equipos que trabajan con automatización, GitOps e infraestructura reproducible.

## Cuándo elegir VyOS

- Necesitas BGP/OSPF con automatización declarativa
- Quieres versionar configuración de red como código
- Tu operación se apoya en pipelines DevOps/NetOps

## Despliegue recomendado

- 2+ vNIC según diseño
- CPU: 2+ vCPU, RAM: 2-4 GB
- Disco: 8 GB+

## Configuración base

1. Define interfaces y direccionamiento.
2. Endurece acceso SSH y cuentas administrativas.
3. Configura políticas firewall por zonas.
4. Implementa routing estático o dinámico (FRR).
5. Automatiza backups y validaciones de configuración.

## Buenas prácticas

- Usa plantillas y repositorio Git para la configuración.
- Introduce cambios por pull request y revisión técnica.
- Separa entornos lab/preprod/prod cuando sea posible.
- Ejecuta pruebas de convergencia y failover periódicas.

## Riesgos comunes

- Cambios manuales fuera de flujo GitOps.
- Falta de validaciones previas al despliegue.
- No medir tiempos de convergencia ante fallos.

## Checklist operativo

- ¿Toda la configuración crítica está versionada?
- ¿Existe pipeline de validación sintáctica y funcional?
- ¿Se han probado escenarios de caída de enlace/peer?
- ¿Hay snapshots o backups listos para rollback?
