---
title: "Plantilla de benchmark de vRouters"
description: "Plantilla reutilizable para medir rendimiento y estabilidad en OPNsense, pfSense, MikroTik CHR y VyOS"
tags: ['networking', 'benchmark', 'vrouter']
updated: 2026-04-18
difficulty: intermediate
estimated_time: 12 min
category: Redes
status: published
last_reviewed: 2026-04-18
prerequisites:
  - "Fundamentos de redes"
  - "Conocimientos básicos de virtualización"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

Usa esta plantilla para comparar vRouters en condiciones equivalentes y tomar decisiones basadas en métricas.

## 1) Datos del escenario

- Plataforma evaluada: `OPNsense | pfSense | MikroTik CHR | VyOS`
- Hipervisor: `Proxmox | KVM | VMware | Hyper-V | otro`
- CPU/RAM VM: `____ vCPU / ____ GB`
- Tipo de NIC virtual: `virtio | e1000 | vmxnet3 | otro`
- Versión del sistema: `________`
- Fecha de prueba: `YYYY-MM-DD`
- Topología: `intra-sede | site-to-site | híbrida`

## 2) Preparación previa

- Mismo hardware base para todas las plataformas.
- Misma versión de `iperf3` y herramientas de medición.
- Sin cargas ajenas durante la ventana de pruebas.
- MTU consistente en ambos extremos.
- NTP sincronizado para correlación de eventos.

## 3) Comandos de prueba recomendados

Servidor de prueba:

```bash
iperf3 -s
```

Cliente TCP (3 corridas):

```bash
iperf3 -c <ip_servidor> -P 4 -t 30
```

Cliente UDP (jitter/pérdida):

```bash
iperf3 -c <ip_servidor> -u -b 300M -t 30
```

Latencia y pérdida:

```bash
ping -c 100 <ip_servidor>
mtr -rwzc 100 <ip_servidor>
```

## 4) Registro de resultados

| KPI | Corrida 1 | Corrida 2 | Corrida 3 | Promedio | Objetivo | Pass/Fail |
| --- | --------- | --------- | --------- | -------- | -------- | --------- |
| Throughput L3 (Gbps) | | | | | >= 1.0 | |
| Throughput VPN (Mbps) | | | | | >= 300 | |
| Latencia extra (ms) | | | | | <= 5 | |
| Pérdida (%) | | | | | <= 0.5 | |
| CPU promedio (%) | | | | | < 80 | |
| Failover (s) | | | | | <= 30 | |

## 5) Prueba de failover (procedimiento)

1. Establece tráfico continuo (`iperf3` o ping persistente).
2. Fuerza caída del enlace principal o peer.
3. Mide tiempo hasta recuperación estable.
4. Repite 3 veces y anota promedio.

## 6) Criterio de aceptación final

- Aceptar plataforma si cumple al menos:
  - 5/6 KPIs en verde.
  - Ningún fail en estabilidad de sesión o failover.
  - Sin picos de CPU sostenidos > 90%.

## 7) Observaciones operativas

- Incidencias detectadas: `________`
- Cambios aplicados para estabilizar: `________`
- Riesgos pendientes: `________`
- Decisión recomendada: `adoptar | condicional | descartar`

## 8) Buenas prácticas de comparación

- No mezclar resultados con cifrado y sin cifrado en la misma tabla.
- Mantener tamaño de paquete, paralelismo y duración constantes.
- Repetir benchmark tras cambios de versión, driver o hipervisor.

## 9) Perfiles de referencia (objetivos por entorno)

| Perfil | Throughput L3 | Throughput VPN | Latencia extra | Pérdida | Failover | CPU promedio |
| ------ | ------------- | -------------- | -------------- | ------- | -------- | ------------ |
| Homelab | >= 500 Mbps | >= 150 Mbps | <= 10 ms | <= 1.0% | <= 60 s | < 85% |
| PyME | >= 1 Gbps | >= 300 Mbps | <= 5 ms | <= 0.5% | <= 30 s | < 80% |
| ISP/WISP | >= 3 Gbps | >= 800 Mbps | <= 3 ms | <= 0.2% | <= 10 s | < 70% |

Recomendación:

- Empieza por el perfil más cercano a tu realidad actual y endurece objetivos en cada iteración.

## 10) Errores frecuentes y mitigación

| Síntoma | Causa probable | Mitigación |
| ------- | -------------- | ---------- |
| Throughput inconsistente | CPU steal o noisy neighbors en hipervisor | Reservar recursos, aislar host, repetir en ventana controlada |
| Pérdida alta en UDP | MTU/MSS no ajustado, colas saturadas | Revisar MTU extremo a extremo, ajustar qdisc/colas |
| Failover lento | Timers conservadores o detección tardía | Ajustar timers de HA/routing, validar detección de enlace |
| Latencia errática | Offloading/NIC virtual no homogénea | Unificar tipo de NIC y offloads entre pruebas |
| CPU excesiva en VPN | Cifrado no acelerado o pocos hilos | Activar aceleración cuando aplique, revisar paralelismo |

## 11) Plantilla de informe ejecutivo

- Resumen: `La plataforma ____ cumple ____/6 KPIs y se recomienda ____.`
- Riesgo principal: `________`
- Riesgo secundario: `________`
- Acción inmediata (7 días): `________`
- Acción de mejora (30 días): `________`
- Decisión final: `adoptar | condicional | descartar`

## 12) Criterio de salida de la fase de benchmark

- Se evaluaron al menos 2 ventanas horarias (valle y pico).
- Se ejecutaron mínimo 3 corridas por KPI y plataforma.
- Se documentó configuración exacta de cada plataforma.
- Se adjuntaron evidencias (comandos/salidas/gráficas).
- La decisión fue revisada por NetOps/SecOps.
