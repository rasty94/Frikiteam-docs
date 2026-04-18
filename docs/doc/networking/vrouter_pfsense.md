---
title: "pfSense (vRouter/firewall virtual)"
description: "Guía rápida para desplegar pfSense como firewall y router virtual"
tags: ['networking', 'security', 'pfsense']
updated: 2026-04-18
difficulty: intermediate
estimated_time: 8 min
category: Redes
status: published
last_reviewed: 2026-04-18
prerequisites:
  - "Fundamentos de redes"
  - "Conocimientos básicos de virtualización"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

pfSense es una plataforma madura y estable, especialmente útil para entornos que valoran predictibilidad operativa.

## Cuándo elegir pfSense

- Necesitas estabilidad y una base muy extendida en producción
- Tu equipo prefiere operación por GUI con flujos tradicionales
- Quieres políticas firewall/NAT claras y conocidas

## Despliegue recomendado (producción tradicional)

- 2-3 vNIC:
  - WAN
  - LAN
  - DMZ opcional
- CPU: 2-4 vCPU, RAM: 4 GB recomendado
- Disco: 16-32 GB

## Configuración base

1. Asigna interfaces y define gateways.
2. Configura alias de red para simplificar reglas.
3. Implementa firewall por zonas (LAN/DMZ/WAN).
4. Ajusta NAT de salida y port forwarding mínimo.
5. Habilita NTP, DNS Resolver y copias de seguridad.

## Buenas prácticas

- Usa aliases en vez de IPs sueltas en reglas.
- Etiqueta reglas por servicio/equipo para auditoría.
- Valida cambios en ventana de mantenimiento.
- Monitoriza estados de firewall y consumo de recursos.

## Riesgos comunes

- Reglas acumuladas sin limpieza periódica.
- Dependencia excesiva de reglas temporales.
- No probar restore de backup antes de incidentes.

## Checklist operativo

- ¿Política WAN está cerrada por defecto?
- ¿Reglas LAN/DMZ siguen mínimo privilegio?
- ¿Backup y restore están verificados?
- ¿El equipo conoce runbook de caída?
