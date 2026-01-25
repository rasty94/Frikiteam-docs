---
title: Proxmox — Guía de Migración (VMs y Contenedores)
updated: 2026-01-25
difficulty: intermediate
estimated_time: 1 min
category: Virtualización
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Proxmox — Guía de Migración (VMs y Contenedores)

## Resumen
Pasos prácticos para migrar máquinas virtuales y contenedores entre hosts o hacia/desde VMware/OpenStack.

## Pasos generales
1. Verificar compatibilidad de discos y controladores.
2. Exportar/convertir imágenes si es necesario.
3. Probar en entorno de staging antes del cutover.

## Consideraciones
- IPs y networking, snapshots, backups y tiempos de inactividad.

---
