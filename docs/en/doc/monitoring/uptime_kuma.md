# Monitoring with Uptime Kuma

🚧 **TRANSLATION PENDING** - Last updated in Spanish: 2026-01-25


Uptime Kuma is a self-hosted monitoring tool that is easy to use and features a modern interface. It is ideal for homelabs and small/medium environments.

## Features

- Monitoring for HTTP(s), TCP, Ping, DNS, Push, etc.
- Notifications (Telegram, Discord, Slack, Email, etc.).
- Public Status Pages.
- Docker support.

## Docker Installation

The easiest way to deploy Uptime Kuma is via Docker.

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

## Basic Configuration

1. Access `http://yourserver:3001`.
2. Create an admin user.
3. Add your first monitor by clicking "Add New Monitor".

## Prometheus Integration

Uptime Kuma does not natively export advanced metrics to Prometheus without configuration, but there are exporter projects or integration via Pushgateway if centralization is desired.
