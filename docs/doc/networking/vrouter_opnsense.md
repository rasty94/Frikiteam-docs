---
title: "OPNsense (vRouter/cortafuegos virtual)"
description: "Guía rápida para desplegar OPNsense en entornos virtualizados"
tags: ['networking', 'security', 'opnsense']
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

OPNsense es una opción muy sólida cuando priorizas funciones de cortafuegos, segmentación y operación cómoda desde interfaz web.

## Cuándo elegir OPNsense

- Necesitas una interfaz gráfica clara para la operación diaria
- Quieres un cortafuegos robusto con reglas visibles y auditables
- Buscas equilibrio entre facilidad de uso y funciones profesionales

## Despliegue recomendado (laboratorio doméstico/perímetro)

- 2 vNIC mínimo:
  - WAN (enlace ascendente)
  - LAN (red interna)
- CPU: 2 vCPU (mínimo), RAM: 2-4 GB
- Disco: 16 GB+

## Configuración base

1. Asigna interfaces WAN/LAN correctamente.
2. Cambia credenciales por defecto y habilita autenticación multifactor (MFA) si aplica.
3. Define direccionamiento LAN y DHCP.
4. Aplica política por defecto de denegación en WAN.
5. Crea reglas explícitas por servicio y origen.

## Buenas prácticas

- Separa redes por VLAN cuando puedas.
- Exporta copia de seguridad de configuración antes de cambios críticos.
- Mantén firmware y complementos al día en ventana de mantenimiento.
- Activa registros del cortafuegos y revisa patrones de denegación.

## Riesgos comunes

- Reglas permisivas tipo `any any` en LAN sin control.
- No documentar NAT/redirecciones de puertos críticos.
- No validar MTU/MSS en túneles VPN y enlaces WAN.

## Lista de comprobación operativa

- ¿WAN y LAN están en interfaces distintas sin solapamiento?
- ¿Existe una copia de seguridad probada de la configuración?
- ¿Se monitoriza latencia, pérdida y sesiones activas?
- ¿Hay procedimiento de reversión?
