---
title: "Monitorización con Uptime Kuma"
description: "Guía de Uptime Kuma: monitorización auto-hospedada para servicios, páginas de estado y notificaciones"
keywords: "uptime kuma, monitoring, status pages, notifications, self-hosted"
tags: [monitoring, uptime, status-pages, notifications]
updated: 2026-01-25
---

# Monitorización con Uptime Kuma

Uptime Kuma es una herramienta de monitorización auto-hospedada, fácil de usar y con una interfaz moderna. Es ideal para "homelabs" y entornos pequeños/medianos.

## Características

- Monitorización de servicios HTTP(s), TCP, Ping, DNS, Push, etc.
- Notificaciones (Telegram, Discord, Slack, Email, etc.).
- Páginas de estado (Status Pages) públicas.
- Soporte para Docker.

## Instalación con Docker

La forma más sencilla de desplegar Uptime Kuma es mediante Docker.

```yaml
version: "3.3"
services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    volumes:
      - ./uptime-kuma-data:/app/data
    ports:
      - 3001:3001
    restart: always
```

## Configuración Básica

1. Accede a `http://tuserver:3001`.
2. Crea un usuario administrador.
3. Añade tu primer monitor clican en "Add New Monitor".

## Integración con Prometheus

Uptime Kuma no exporta métricas a Prometheus nativamente de forma avanzada sin configuración, pero existen proyectos de exportadores o integración vía Pushgateway si se desea centralizar.
