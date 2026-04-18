---
title: "VyOS (vRouter orientado a automatización)"
description: "Guía rápida para desplegar VyOS con enfoque en BGP/OSPF y automatización"
tags: ['networking', 'vyos', 'automatizacion']
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

VyOS encaja muy bien en equipos que trabajan con automatización, GitOps e infraestructura reproducible.

## Cuándo elegir VyOS

- Necesitas BGP/OSPF con automatización declarativa
- Quieres versionar configuración de red como código
- Tu operación se apoya en canalizaciones de desarrollo y operaciones de red

## Despliegue recomendado

- 2+ vNIC según diseño
- CPU: 2+ vCPU, RAM: 2-4 GB
- Disco: 8 GB+

## Configuración base

1. Define interfaces y direccionamiento.
2. Endurece acceso SSH y cuentas administrativas.
3. Configura políticas firewall por zonas.
4. Implementa enrutamiento estático o dinámico (FRR).
5. Automatiza copias de seguridad y validaciones de configuración.

## Buenas prácticas

- Usa plantillas y repositorio Git para la configuración.
- Introduce cambios mediante solicitudes de cambio (pull request) y revisión técnica.
- Separa entornos de laboratorio/preproducción/producción cuando sea posible.
- Ejecuta pruebas periódicas de convergencia y conmutación por error.

## Riesgos comunes

- Cambios manuales fuera de flujo GitOps.
- Falta de validaciones previas al despliegue.
- No medir tiempos de convergencia ante fallos.

## Lista de comprobación operativa

- ¿Toda la configuración crítica está versionada?
- ¿Existe canalización de validación sintáctica y funcional?
- ¿Se han probado escenarios de caída de enlace/vecino?
- ¿Hay instantáneas o copias de seguridad listas para reversión?
