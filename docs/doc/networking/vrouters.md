---
title: "vRouters y firewalls virtuales"
description: "Comparativa práctica de OPNsense, pfSense, MikroTik CHR y VyOS para laboratorios y producción"
tags: ['networking', 'security', 'vrouter']
updated: 2026-04-18
difficulty: intermediate
estimated_time: 6 min
category: Redes
status: published
last_reviewed: 2026-04-18
prerequisites:
  - "Fundamentos de redes"
  - "Conocimientos básicos de virtualización"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

Cuando necesitas enrutamiento avanzado, funciones de cortafuegos y servicios de red en formato virtual, las opciones más comunes son **OPNsense**, **pfSense**, **MikroTik CHR** y **VyOS**.

Este documento resume diferencias clave y te ayuda a elegir según el escenario.

## Guías por plataforma

- [Plantilla de pruebas de rendimiento de vRouters](vrouter_benchmark_template.md)
- [OPNsense: guía rápida para laboratorio doméstico y perímetro](vrouter_opnsense.md)
- [pfSense: guía rápida para producción tradicional](vrouter_pfsense.md)
- [MikroTik CHR: guía rápida para enrutamiento L3](vrouter_mikrotik_chr.md)
- [VyOS: guía rápida para automatización y BGP/OSPF](vrouter_vyos.md)

## Casos de uso típicos

- Laboratorios de redes y ciberseguridad
- Routers virtuales en laboratorio doméstico o perímetro
- Firewall perimetral en infraestructura on-prem
- BGP/OSPF estático-dinámico en entornos híbridos
- VPN de sede a sede y acceso remoto

## Comparativa rápida

| Solución | Base tecnológica | Fortalezas | Limitaciones | Escenario recomendado |
| -------- | ---------------- | ---------- | ------------ | --------------------- |
| **OPNsense** | FreeBSD + pf | Interfaz moderna, buen ecosistema de complementos, actualizaciones frecuentes | Menos documentación histórica que pfSense | Laboratorio doméstico, pyme, perímetro con foco en seguridad |
| **pfSense** | FreeBSD + pf | Muy estable, comunidad amplia, gran madurez operativa | Cambios de licenciamiento/ecosistema según edición | Producción tradicional y entornos consolidados |
| **MikroTik CHR** | RouterOS | Alto rendimiento por coste, funcionalidades de enrutamiento muy amplias | Curva de aprendizaje de RouterOS, licencia por rendimiento | ISP/WISP, enrutamiento L3 intensivo, laboratorios de operador |
| **VyOS** | Linux + FRR + nftables/iptables | CLI declarativa, fuerte en automatización IaC y enrutamiento avanzado | Menos amigable para quien prefiera interfaz gráfica completa | Automatización, BGP/OSPF, red troncal virtual |

## Tabla técnica avanzada

| Criterio | OPNsense | pfSense | MikroTik CHR | VyOS |
| -------- | -------- | ------- | ------------ | ---- |
| Plano de gestión | Interfaz web + CLI limitada | Interfaz web + shell | Interfaz WinBox/WebFig + CLI RouterOS | CLI declarativa + API/automatización |
| Enrutamiento dinámico (BGP/OSPF) | Soportado (complementos/FRR) | Soportado (paquete FRR) | Muy robusto en RouterOS | Muy robusto con FRR nativo |
| Enfoque principal | Cortafuegos/UTM moderno | Cortafuegos estable y maduro | Enrutamiento de alto rendimiento | Enrutamiento + automatización como código |
| VPN habitual | IPsec, OpenVPN, WireGuard | IPsec, OpenVPN, WireGuard | IPsec, WireGuard, L2TP/PPTP heredado | IPsec, OpenVPN, WireGuard |
| Alta disponibilidad | CARP/conmutación por error y sincronización de configuración | CARP/conmutación por error y sincronización de configuración | VRRP/conmutación por error según diseño | VRRP/alta disponibilidad según arquitectura |
| Curva de aprendizaje | Baja-media | Baja-media | Media-alta | Media-alta |
| Automatización | Media (API/complementos) | Media (API/copia de configuración) | Alta (scripts/Ansible/API RouterOS) | Alta (GitOps + plantillas CLI) |
| Perfil recomendado | Pyme, perímetro seguro, laboratorio doméstico | Producción clásica y conservadora | ISP/WISP y laboratorios de operador | Entornos de automatización de redes y seguridad |

## Objetivos de rendimiento (laboratorio inicial)

| KPI | Objetivo base | Cómo medirlo | Criterio de aceptación |
| --- | ------------- | ------------ | ---------------------- |
| Rendimiento L3 (sin cifrado) | >= 1 Gbps sostenido | `iperf3` TCP/UDP entre segmentos | Variación < 15% entre 3 corridas |
| Rendimiento VPN de sede a sede | >= 300 Mbps sostenido | `iperf3` a través del túnel | Uso CPU < 80% promedio |
| Latencia intra-sede | <= 5 ms adicional | `ping` baseline vs con vRouter | Delta estable sin picos anómalos |
| Pérdida de paquetes | <= 0.5% | `mtr`/`ping -f` controlado | Sin pérdida sostenida > 1 minuto |
| Convergencia de conmutación por error | <= 30 s | Corte controlado de enlace/vecino | Recuperación sin intervención manual |
| Estabilidad de sesiones | 0 reinicios no planificados | Monitorización 24-72 h | Sin caída de plano de control |

Notas:

- Ejecuta pruebas en hora valle y hora punta para detectar degradación por carga.
- Mantén el mismo tamaño de paquete y paralelismo al comparar plataformas.
- Repite pruebas tras cambios de versión, controladores o tipo de hipervisor.
- Si necesitas objetivos por contexto (laboratorio doméstico, pyme, ISP/WISP), usa la [Plantilla de pruebas de rendimiento de vRouters](vrouter_benchmark_template.md).

## Hardening mínimo homogéneo (todas las plataformas)

- Cambia credenciales por defecto y elimina usuarios no necesarios.
- Restringe acceso de administración por IP/red de gestión dedicada.
- Habilita MFA para GUI/portal administrativo cuando esté disponible.
- Desactiva servicios de gestión no utilizados (SSH, API, GUI pública).
- Aplica política `deny by default` en WAN y reglas explícitas por servicio.
- Separa redes de gestión, usuarios y servidores (VLAN/zonas).
- Activa logs de seguridad y envíalos a un colector central.
- Configura NTP fiable para trazabilidad de eventos y auditoría.
- Cifra y valida copias de seguridad de configuración; prueba la restauración de forma periódica.
- Define proceso de parcheado con ventana de mantenimiento y plan de reversión.

## Qué elegir según prioridad

```mermaid
flowchart TD
    A[¿Qué priorizas?] --> B{Interfaz principal}

    B -->|GUI| C{¿Perfil?}
    B -->|CLI + IaC| D[VyOS]

    C -->|Firewall moderno + plugins| E[OPNsense]
    C -->|Estabilidad tradicional| F[pfSense]
    C -->|Enrutamiento agresivo + coste| G[MikroTik CHR]

    E --> H[Laboratorio doméstico / pyme / perímetro]
    F --> I[Producción clásica]
    G --> J[ISP / WISP / Lab de operador]
    D --> K[Automatización y BGP]

    style E fill:#4caf50,color:#ffffff
    style F fill:#1e88e5,color:#ffffff
    style G fill:#f57c00,color:#ffffff
    style D fill:#8e24aa,color:#ffffff
```

## Criterios técnicos clave

### 1) Enrutamiento dinámico

- **VyOS** y **MikroTik CHR** destacan en BGP/OSPF para topologías complejas.
- **OPNsense/pfSense** cubren enrutamiento dinámico, pero suelen brillar más como cortafuegos/UTM.

### 2) Operación diaria

- Si prefieres **GUI completa**, OPNsense/pfSense te reducen fricción.
- Si priorizas **GitOps/automatización**, VyOS encaja mejor por su modelo declarativo en CLI.

### 3) VPN y acceso remoto

- Todas soportan VPN de sede a sede y acceso remoto (IPsec/WireGuard/OpenVPN según versión y paquetes).
- Verifica compatibilidad exacta por versión antes de estandarizar en producción.

### 4) Licenciamiento y soporte

- Revisa siempre la edición/comercialización vigente para evitar sorpresas en actualizaciones.
- En entornos críticos, valida soporte empresarial o socio local.

## Recomendaciones prácticas

- Empieza con una **prueba de concepto** con tráfico realista (norte-sur y este-oeste).
- Define indicadores clave (KPI): latencia, rendimiento, conmutación por error, tiempo de recuperación.
- Documenta copia/restauración de configuración y procedimiento de reversión.
- Versiona la configuración (cuando sea posible) para auditar cambios.
- Cierra cada evaluación con informe ejecutivo corto (riesgos, acciones 7/30 días y decisión final).

## Lista de comprobación de decisión

- ¿Necesitas GUI o CLI declarativa?
- ¿La prioridad es cortafuegos, enrutamiento avanzado o ambos?
- ¿Cuántos túneles VPN y peers BGP vas a mantener?
- ¿Qué capacidad de operación tiene el equipo de redes y seguridad?
- ¿Hay requisitos de soporte comercial y SLA?

Si dudas entre dos opciones, compara ambas en el mismo laboratorio durante una semana y decide por métricas, no por preferencia personal.
