---
title: "Ceph Troubleshooting: Common Issues and Solutions"
tags: ['storage', 'ceph']
description: "Comprehensive guide to diagnose and fix common Ceph problems. OSDs down, PG issues, slow operations, and cluster health recovery."
keywords: Ceph, troubleshooting, debugging, OSD down, PG stuck, slow ops, cluster health, recovery, ceph health
updated: 2026-07-18
difficulty: intermediate
estimated_time: 31 min
category: Almacenamiento
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Troubleshooting Ceph

## 🎯 Diagnóstico Inicial

### Comandos Esenciales

```bash
# Estado del clúster
ceph -s
ceph health detail

# Estado de OSDs
ceph osd tree
ceph osd stat
ceph osd df

# Estado de PGs
ceph pg stat
ceph pg dump | grep -v "^version"

# Performance
ceph osd perf
ceph tell osd.* bench

# Logs
journalctl -u ceph-osd@* -f
journalctl -u ceph-mon@* -f
```

## 🔴 HEALTH_WARN y HEALTH_ERR

### HEALTH_WARN: OSDs near full

**Síntoma**:
```bash
$ ceph -s
  health: HEALTH_WARN
          1 nearfull osd(s)
          OSD.5 is near full (85%)
```

**Diagnóstico**:

```bash
# Ver uso por OSD
ceph osd df tree

# Ver pools más grandes
ceph df

# Ver qué está ocupando espacio
for pool in $(ceph osd pool ls); do
  echo "Pool: $pool"
  rbd du $pool 2>/dev/null || rados df -p $pool
done
```

**Soluciones**:

```bash
# 1. Añadir más OSDs
ceph orch daemon add osd <host>:<device>

# 2. Ajustar thresholds temporalmente
ceph osd set-full-ratio 0.95
ceph osd set-nearfull-ratio 0.90

# 3. Eliminar datos innecesarios
# Eliminar snapshots antiguos
rbd snap ls <pool>/<image>
rbd snap rm <pool>/<image>@<snapshot>

# 4. Rebalancear
ceph osd reweight <osd-id> 0.95  # Reducir peso del OSD lleno
```

### HEALTH_ERR: OSDs down

**Síntoma**:
```bash
$ ceph -s
  health: HEALTH_ERR
          3 osds down
          Degraded data redundancy (...)
```

**Diagnóstico**:

```bash
# Identificar OSDs down
ceph osd tree | grep down

# Ver por qué están down
systemctl status ceph-osd@5
journalctl -u ceph-osd@5 -n 100

# Verificar disco
lsblk
smartctl -a /dev/sdb
```

**Soluciones según causa**:

#### OSD crashed (fallo de software):

```bash
# Reiniciar OSD
systemctl restart ceph-osd@5

# Si no arranca, ver logs
journalctl -u ceph-osd@5 --since "10 minutes ago"

# Intentar repair
ceph-objectstore-tool --data-path /var/lib/ceph/osd/ceph-5 --op fsck
```

#### Disco fallado:

```bash
# Marcar OSD como out
ceph osd out 5

# Remover OSD del clúster
ceph osd purge 5 --yes-i-really-mean-it

# Reemplazar disco
# 1. Físicamente reemplazar
# 2. Añadir nuevo OSD
ceph orch daemon add osd <host>:/dev/sdb

# Esperar a que se rebalancee
watch ceph -s
```

#### Problemas de red:

```bash
# Verificar conectividad
ping <osd-host>
ceph tell osd.* version  # Ver cuáles responden

# Verificar interfaces
ip addr show
ip link show

# Reiniciar networking si es necesario
systemctl restart networking
```

### HEALTH_WARN: PGs stuck

**Síntomas comunes**:
- `X pgs stuck unclean`
- `X pgs stuck inactive`  
- `X pgs stuck degraded`
- `X pgs stuck undersized`

**Diagnóstico**:

```bash
# Ver PGs problemáticos
ceph pg dump | grep -E "stuck|stale|inactive"

# Detalles de un PG específico
ceph pg <pg-id> query

# Ver mapeo de PG a OSDs
ceph pg map <pg-id>
```

**Soluciones**:

#### PGs stuck inactive/unclean:

```bash
# Forzar scrub
ceph pg scrub <pg-id>
ceph pg deep-scrub <pg-id>

# Forzar recovery
ceph pg force-recovery <pg-id>

# Si persiste, revisar OSDs responsables
ceph pg <pg-id> query | grep acting
```

#### PGs stuck undersized:

```bash
# Significa que faltan réplicas
# Verificar cuántas réplicas tiene el pool
ceph osd pool get <pool-name> size
ceph osd pool get <pool-name> min_size

# Si tienes menos OSDs que el size del pool:
# Opción 1: Añadir OSDs
# Opción 2: Reducir size (solo para testing)
ceph osd pool set <pool-name> size 2
```

#### PGs remapped:

```bash
# Normal durante rebalanceos
# Ver progreso
ceph -w

# Acelerar recovery (con cuidado, impacta performance)
ceph tell 'osd.*' injectargs '--osd-max-backfills 8'
ceph tell 'osd.*' injectargs '--osd-recovery-max-active 4'

# Restaurar valores por defecto después
ceph tell 'osd.*' injectargs '--osd-max-backfills 1'
ceph tell 'osd.*' injectargs '--osd-recovery-max-active 3'
```

## ⚡ Problemas de Performance

### Slow Operations (slow ops)

**Síntoma**:
```bash
$ ceph -s
  health: HEALTH_WARN
          30 slow ops, oldest one blocked for 45 sec
```

**Diagnóstico**:

```bash
# Ver operaciones lentas
ceph daemon osd.5 dump_historic_slow_ops

# Ver latencia de OSDs
ceph osd perf

# Ver stats de pools
ceph df detail

# Benchmark de un OSD específico
ceph tell osd.5 bench
```

**Causas y soluciones**:

#### Discos lentos/fallando:

```bash
# Test de I/O en disco
fio --filename=/dev/sdb --direct=1 --rw=randread --bs=4k \
    --ioengine=libaio --iodepth=64 --runtime=60 --name=test

# Ver SMART health
smartctl -a /dev/sdb | grep -E "Reallocated|Pending|Uncorrectable"

# Si disco está mal, reemplazar (ver sección OSDs down)
```

#### Red saturada:

```bash
# Test de bandwidth entre nodos
iperf3 -s  # En un nodo
iperf3 -c <ip-del-nodo> -t 30  # En otro nodo

# Ver tráfico de red
iftop -i eth0

# Solución: Mejorar red (10GbE, bonding, jumbo frames)
```

#### Journal/WAL en disco lento:

```bash
# Verificar dónde está el journal
ceph-volume lvm list

# Migrar journal/WAL a SSD
ceph-volume lvm new-wal /dev/nvme0n1 --osd-id 5
```

#### PGs mal balanceados:

```bash
# Ver distribución de PGs por OSD
ceph osd df tree

# Si hay desbalanceo:
ceph balancer on
ceph balancer mode upmap
ceph balancer eval
```

### Alto uso de CPU en OSDs

**Diagnóstico**:

```bash
# Ver procesos
top -b -n 1 | grep ceph-osd
htop

# Ver operaciones activas
ceph daemon osd.5 dump_ops_in_flight
```

**Soluciones**:

```bash
# Limitar scrubbing
ceph tell osd.* injectargs '--osd-max-scrubs 1'
ceph config set osd osd_scrub_begin_hour 2
ceph config set osd osd_scrub_end_hour 6

# Reducir recovery concurrente
ceph tell 'osd.*' injectargs '--osd-max-backfills 1'

# Aumentar recursos (más cores, más RAM)
```

## 🗄️ Problemas de Pools y RBD

### Error: "pool has too few PGs"

**Síntoma**:
```bash
$ ceph -s
  health: HEALTH_WARN
          pool 'volumes' has too few pgs
```

**Solución**:

```bash
# Calcular PGs adecuados
# Fórmula: (OSDs * 100) / pool_size / num_pools
# Ejemplo: (30 * 100) / 3 / 4 = 250 → redondear a 256

# Aumentar PGs (automático en Octopus+)
ceph osd pool set volumes pg_num 256

# Esperar autoscaling
ceph osd pool autoscale-status

# Habilitar autoscaling si no está activo
ceph osd pool set volumes pg_autoscale_mode on
```

### No se puede eliminar pool

**Síntoma**:
```bash
$ ceph osd pool delete mypool mypool --yes-i-really-really-mean-it
Error EPERM: pool deletion is disabled; configure mon_allow_pool_delete
```

**Solución**:

```bash
# Habilitar eliminación
ceph config set mon mon_allow_pool_delete true

# Eliminar pool
ceph osd pool delete mypool mypool --yes-i-really-really-mean-it

# Deshabilitar eliminación (buena práctica)
ceph config set mon mon_allow_pool_delete false
```

### RBD image corrupta

**Diagnóstico**:

```bash
# Verificar imagen
rbd info <pool>/<image>
rbd check <pool>/<image>

# Ver snapshots
rbd snap ls <pool>/<image>
```

**Solución**:

```bash
# Intentar repair
rbd repair <pool>/<image>

# Si hay snapshots, flatten
rbd flatten <pool>/<image>

# Recuperar desde snapshot válido
rbd snap rollback <pool>/<image>@<snapshot-name>

# Último recurso: exportar/reimportar
rbd export <pool>/<image> /tmp/image_backup.raw
rbd rm <pool>/<image>
rbd import /tmp/image_backup.raw <pool>/<image>
```

## 🔧 Problemas de MON (Monitors)

### MON down o clock skew

**Síntoma**:
```bash
$ ceph -s
  health: HEALTH_WARN
          clock skew detected on mon.node2
```

**Solución**:

```bash
# Verificar NTP/chrony en todos los nodos
systemctl status chronyd
chronyc tracking

# Sincronizar tiempo
sudo chronyc -a makestep

# Verificar timesync
timedatectl status

# Reiniciar MON si es necesario
systemctl restart ceph-mon@node2
```

### Quorum perdido

**Síntoma**:
Ceph -s no responde o muestra "no quorum".

**Solución (PELIGROSO)**:

```bash
# Ver estado de MONs
ceph mon stat

# Si tienes >50% MONs UP, esperar a que formen quorum

# Si has perdido mayoría, recuperar manualmente:
# En el MON superviviente:
ceph-mon -i <mon-id> --extract-monmap /tmp/monmap
monmaptool --print /tmp/monmap

# Editar monmap si es necesario
monmaptool --rm <mon-id-down> /tmp/monmap

# Inyectar monmap
ceph-mon -i <mon-id> --inject-monmap /tmp/monmap

# Reiniciar
systemctl restart ceph-mon@<mon-id>
```

## 🛠️ Herramientas de Diagnóstico

### Script de Health Check

```bash
#!/bin/bash
# ceph-health-check.sh

echo "=== Ceph Health Check ==="
ceph -s

echo -e "\n=== OSDs Status ==="
ceph osd tree

echo -e "\n=== Disk Usage ==="
ceph osd df tree

echo -e "\n=== PG Status ==="
ceph pg stat

echo -e "\n=== Pool Usage ==="
ceph df

echo -e "\n=== Slow Ops ==="
ceph daemon osd.* dump_historic_slow_ops | grep -A5 "slow_ops"

echo -e "\n=== Network Check ==="
ceph tell mon.* version
ceph tell osd.* version | grep -c "version"
```

### Benchmark Storage

```bash
#!/bin/bash
# benchmark-ceph.sh

POOL="benchmark-pool"

# Crear pool temporal
ceph osd pool create $POOL 128
rados bench -p $POOL 30 write --no-cleanup
rados bench -p $POOL 30 seq
rados bench -p $POOL 30 rand

# Cleanup
ceph osd pool delete $POOL $POOL --yes-i-really-really-mean-it
```

## 📊 Logs y Debugging

### Ubicaciones de Logs

```bash
# Logs de OSDs
/var/log/ceph/ceph-osd.*.log

# Logs de MONs
/var/log/ceph/ceph-mon.*.log

# Logs de MGRs
/var/log/ceph/ceph-mgr.*.log

# Ver en tiempo real
tail -f /var/log/ceph/ceph-osd.5.log
journalctl -u ceph-osd@5 -f
```

### Habilitar Debug

```bash
# Aumentar debug level (0-30, default 1)
ceph tell osd.5 injectargs '--debug-osd 20'
ceph tell mon.* injectargs '--debug-mon 20'

# Restaurar
ceph tell osd.5 injectargs '--debug-osd 1'
```

## 📚 Comandos de Emergencia

### Pausar Recovery/Rebalancing

```bash
# Pausar operaciones (para mantenimiento)
ceph osd set noout
ceph osd set norebalance
ceph osd set norecover
ceph osd set nobackfill

# Reanudar
ceph osd unset noout
ceph osd unset norebalance
ceph osd unset norecover
ceph osd unset nobackfill
```

### Forzar Completar Recovery

```bash
# Ver PGs en recovery
ceph pg dump | grep -E "recovery|backfill"

# Acelerar (¡impacta performance!)
ceph tell 'osd.*' injectargs '--osd-recovery-max-active 10'
ceph tell 'osd.*' injectargs '--osd-max-backfills 10'
ceph tell 'osd.*' injectargs '--osd-recovery-sleep-hdd 0'

# Restaurar defaults
ceph tell 'osd.*' injectargs '--osd-recovery-max-active 3'
ceph tell 'osd.*' injectargs '--osd-max-backfills 1'
ceph tell 'osd.*' injectargs '--osd-recovery-sleep-hdd 0.1'
```

## 🎓 Mejores Prácticas de Troubleshooting

1. **Siempre revisar logs primero**: `journalctl -u ceph-* -f`
2. **No hacer cambios drásticos sin backup**: Especialmente con `ceph osd purge`
3. **Un cambio a la vez**: Para identificar qué solucionó el problema
4. **Documentar**: Mantener registro de cambios y comandos ejecutados
5. **Monitorizar**: Usar Grafana + Prometheus para detección proactiva

## 📚 Referencias

- [Ceph Troubleshooting Guide](https://docs.ceph.com/en/latest/rados/troubleshooting/)
- [Ceph Operations Manual](https://docs.ceph.com/en/latest/rados/operations/)
- [Ceph Health Checks](https://docs.ceph.com/en/latest/rados/operations/health-checks/)

---

!!! danger "Comandos Destructivos"
    Nunca ejecutes `ceph osd purge`, `ceph osd pool delete` o `--force` sin entender completamente las consecuencias.

!!! tip "Antes de Hacer Cambios"
    Siempre ejecuta `ceph -s` y `ceph health detail` para tener un baseline del estado del clúster.
