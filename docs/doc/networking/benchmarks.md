---
title: "Networking: Comparativa de Rendimiento"
description: "Documentación sobre networking: comparativa de rendimiento"
tags: ['networking']
updated: 2026-01-25
difficulty: intermediate
estimated_time: 1 min
category: Redes
status: published
last_reviewed: 2026-01-25
prerequisites:
  - "Conocimientos básicos de DevOps"
  - "Fundamentos de redes"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Networking: Comparativa de Rendimiento

Resumen de rendimiento entre diferentes soluciones de VPN y Overlay Networking.

## Prerrequisitos

- Acceso SSH a dos nodos de prueba.
- Herramientas instaladas: `iperf3`, `mtr`, `ping`.

## Metodología

- Pruebas realizadas en red local 10Gbps.
- Cifrado habilitado en todos los casos.

## Resultados

| Protocolo | Latencia (ms) | Throughput (Gbps) | Uso CPU |
| --------- | ------------- | ----------------- | ------- |
| WireGuard | 0.5           | 8.5               | Bajo    |
| Tailscale | 0.8           | 7.2               | Medio   |
| NetBird   | 0.7           | 7.8               | Medio   |
| ZeroTier  | 1.2           | 6.5               | Alto    |

> **Nota**: Los valores mostrados son aproximados y pueden variar según la configuración del hardware y la red.

## Referencias

- [Documentación WireGuard](https://www.wireguard.com/)
