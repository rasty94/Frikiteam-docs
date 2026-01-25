---
tags:
  - databases
  - redis
  - cache
updated: 2026-01-25
difficulty: beginner
estimated_time: 1 min
category: Bases de Datos
status: published
last_reviewed: 2026-01-25
prerequisites: ["Ninguno"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Redis: Caché de Alto Rendimiento

Redis es un almacén de estructura de datos en memoria, utilizado como base de datos, caché y broker de mensajería.

## Despliegue Rápido

```bash
docker run --name my-redis -d redis
```

## Persistencia

Redis ofrece dos modos: RDB (snapshots) y AOF (Append Only File). Para habilitar persistencia:

```yaml
version: "3.8"
services:
  redis:
    image: redis:alpine
    command: redis-server --appendonly yes
    volumes:
      - ./redis_data:/data
    ports:
      - "6379:6379"
```

## Casos de Uso Comunes

1.  **Caché de sesiones:** Almacenar tokens de usuario.
2.  **Colas de tareas:** Backend para Celery o BullMQ.
3.  **Leaderboard:** Uso de Sorted Sets.
