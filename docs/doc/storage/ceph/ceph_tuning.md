---
title: "Ceph — Optimización y Planificación de Capacidad"
description: "Documentación sobre ceph — optimización y planificación de capacidad"
tags: ['storage']
updated: 2026-01-25
difficulty: expert
estimated_time: 1 min
category: Almacenamiento
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

```markdown
---
title: Ceph — Optimización y Planificación de Capacidad
---

# Ceph — Optimización y Planificación de Capacidad

## Resumen
Consejos para dimensionar y tunear un clúster Ceph: OSDs, CRUSH map, réplicas y rendimiento.

## Puntos clave
- Planificar capacidad y rendimiento por separado.
- Balancear OSDs por disco y por nodo.
- Ajustar `osd_pool_default_size` y `pg_num` con cuidado.

## Monitorización y mantenimiento
- Usar Prometheus + Grafana para métricas.
- Revisar latencias y rebalanceos frecuentes.

---

```
