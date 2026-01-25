---
title: "OpenStack Day-2 Operations: Maintenance and Production Management"
description: "Complete guide for Day-2 operations in OpenStack: upgrades, backups, monitoring, capacity planning, and incident response."
keywords: OpenStack, Day-2, operations, maintenance, upgrades, backups, monitoring, capacity planning, production, ops
date: 2026-01-25
updated: 2026-01-25
difficulty: intermediate
estimated_time: 11 min
category: Cloud Computing
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# OpenStack — Day-2 Operations

## 🎯 Introducción

Day-2 Operations se refiere a todas las tareas operacionales después del despliegue inicial de OpenStack. Esta guía cubre:

- ✅ Upgrades y actualizaciones
- ✅ Backups y disaster recovery
- ✅ Monitorización y alerting
- ✅ Capacity planning
- ✅ Troubleshooting recurrente
- ✅ Gestión de seguridad
- ✅ Optimización de performance

## 📅 Calendario de Mantenimiento Recomendado

### Tareas Diarias

```bash
# Health check automático (vía cron)
0 9 * * * /usr/local/bin/openstack-health-check.sh

# Verificar servicios críticos
openstack compute service list
openstack network agent list
openstack volume service list

# Revisar logs de errores
docker logs --since 24h nova_compute | grep -i error
docker logs --since 24h neutron_openvswitch_agent | grep -i error
```

### Tareas Semanales

```bash
# Limpiar instancias ERROR antiguas (>7 días)
openstack server list --all-projects --status ERROR \
  --long | awk '{print $1}' | xargs -I {} openstack server delete {}

# Limpiar snapshots antiguos (>30 días)
# Script personalizado según política

# Verificar backups
ls -lh /backups/openstack/ | tail -10

# Revisar uso de recursos
openstack hypervisor stats show
ceph df  # Si se usa Ceph
```

### Tareas Mensuales

```bash
# Actualizar imágenes base
# Descargar nuevas versiones de Ubuntu, CentOS, etc.
# Subir a Glance y marcar antiguas como deprecated

# Review de capacity
# Ver trends en Grafana
# Planificar expansión si es necesario

# Security updates
apt update && apt upgrade  # En todos los nodos
# Reconfigura OpenStack si hay cambios
kolla-ansible -i /etc/kolla/multinode reconfigure
```

### Tareas Trimestrales

```bash
# Upgrades de OpenStack (según release cadence)
# Ver sección de Upgrades más abajo

# Disaster recovery drill
# Restaurar backups en entorno de test

# Revisión de seguridad
# Auditar usuarios, roles, security groups
# Verificar compliance
```

## 🔄 Upgrades de OpenStack

### Estrategia de Upgrade

OpenStack sigue un modelo SLURP (releases estables cada ~1 año):

```
2023.1 (Antelope) → 2023.2 (Bobcat) → 2024.1 (Caracal) → 2024.2 (Dalmatian)
```

**Recomendación**: Upgrade cada 2-3 releases (skip releases intermedios si es SLURP)

### Pre-Upgrade Checklist

```bash
# 1. Verificar release actual
kolla-ansible --version
openstack --version

# 2. Backup completo (ver sección Backups)
./backup-openstack.sh

# 3. Verificar salud del clúster
kolla-ansible -i /etc/kolla/multinode prechecks

# 4. Revisar release notes
# https://releases.openstack.org/caracal/index.html

# 5. Preparar ventana de mantenimiento
# Comunicar a usuarios, agendar downtime

# 6. Verificar compatibilidad de Kolla images
# https://quay.io/repository/openstack.kolla/
```

### Proceso de Upgrade (Kolla-Ansible)

```bash
# 1. Actualizar Kolla-Ansible
pip install --upgrade kolla-ansible==18.0.0  # Nueva versión

# 2. Actualizar dependencias Ansible
kolla-ansible install-deps

# 3. Regenerar passwords (para nuevos servicios)
kolla-genpwd

# 4. Merge configuración
# Comparar /etc/kolla/globals.yml con nuevo template
diff /etc/kolla/globals.yml \
  ~/kolla-venv/share/kolla-ansible/etc_examples/kolla/globals.yml

# 5. Pull nuevas imágenes
kolla-ansible -i /etc/kolla/multinode pull

# 6. Prechecks
kolla-ansible -i /etc/kolla/multinode prechecks

# 7. Upgrade (sin downtime en HA)
kolla-ansible -i /etc/kolla/multinode upgrade

# 8. Post-upgrade checks
openstack service list
openstack compute service list
openstack network agent list

# 9. Lanzar instancia de prueba
openstack server create --flavor m1.small --image cirros test-upgrade
```

### Rollback Strategy

```bash
# Si el upgrade falla:

# 1. Detener servicios nuevos
kolla-ansible -i /etc/kolla/multinode stop

# 2. Restaurar imágenes anteriores
# Editar /etc/kolla/globals.yml:
# openstack_release: "2023.2"  # Versión anterior

# 3. Reconfigure con versión anterior
kolla-ansible -i /etc/kolla/multinode reconfigure

# 4. Restaurar DB si es necesario
# Ver sección de Backups

# 5. Verificar funcionamiento
openstack server list
```

## 💾 Backups

### ¿Qué BackupGear?

| Componente | Qué Respaldar | Frecuencia | Retención |
|------------|---------------|------------|-----------|
| **MariaDB** | Todas las bases de datos | Diario | 30 días |
| **Config Files** | /etc/kolla | Cambios | 90 días |
| **Glance Images** | Images pool (Ceph) o /var/lib/glance | Semanal | 60 días |
| **Cinder Volumes** | Volúmenes críticos | Según SLA | Según SLA |
| **Keystone** | Dump de usuarios/roles | Semanal | 90 días |

### Script de Backup de MariaDB

```bash
#!/bin/bash
# /usr/local/bin/backup-openstack-dbs.sh

BACKUP_DIR="/backups/openstack/mariadb"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# Obtener password de MariaDB
DB_PASSWORD=$(grep database_password /etc/kolla/passwords.yml | awk '{print $2}')

# Backup de cada base de datos
for db in keystone glance nova nova_api nova_cell0 neutron cinder heat; do
  echo "Backing up $db..."
  docker exec mariadb mysqldump \
    -uroot -p$DB_PASSWORD \
    --single-transaction \
    --routines \
    --triggers \
    $db | gzip > $BACKUP_DIR/${db}_${DATE}.sql.gz
done

# Backup completo (alternativa)
docker exec mariadb mysqldump \
  -uroot -p$DB_PASSWORD \
  --all-databases \
  --single-transaction \
  --routines \
  --triggers | gzip > $BACKUP_DIR/all_databases_${DATE}.sql.gz

# Limpieza de backups antiguos
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_DIR"
ls -lh $BACKUP_DIR | tail -5
```

### Restauración de MariaDB

```bash
#!/bin/bash
# restore-openstack-db.sh

BACKUP_FILE="/backups/openstack/mariadb/keystone_20260125_100000.sql.gz"
DB_NAME="keystone"
DB_PASSWORD=$(grep database_password /etc/kolla/passwords.yml | awk '{print $2}')

# Detener servicios que usan esta DB
kolla-ansible -i /etc/kolla/multinode stop --tags keystone

# Restaurar
zcat $BACKUP_FILE | docker exec -i mariadb mysql -uroot -p$DB_PASSWORD $DB_NAME

# Reiniciar servicios
kolla-ansible -i /etc/kolla/multinode deploy --tags keystone

# Verificar
openstack user list
```

### Backup de Ceph (si se usa)

```bash
# Snapshot de pool completo
rbd snap create images@backup-$(date +%Y%m%d)
rbd snap create volumes@backup-$(date +%Y%m%d)

# Export incremental (más eficiente)
rbd export-diff images/<image-name> /backups/ceph/image-diff-$(date +%Y%m%d).diff

# Automatizar con cron
0 2 * * * /usr/local/bin/backup-ceph-pools.sh
```

### Disaster Recovery Plan

```markdown
## DR Procedure (RTO: 4 hours, RPO: 24 hours)

1. **Preparar infraestructura de reemplazo** (1h)
   - Provisionar hardware/VMs
   - Configurar red básica

2. **Restaurar controladores** (1.5h)
   - Deploy Kolla-Ansible fresh
   - Restaurar /etc/kolla
   - Restaurar MariaDB desde backup

3. **Restaurar Compute nodes** (30min)
   - Deploy nova-compute
   - Sincronizar con DB

4. **Restaurar Storage** (30min)
   - Restaurar Ceph cluster o
   - Montar backends de storage

5. **Verificación** (30min)
   - Lanzar instancias de prueba
   - Verificar acceso a volúmenes/imágenes
   - Probar conectividad
```

## 📊 Monitorización y Alerting

### Stack de Monitorización

```yaml
Prometheus:  # Métricas
  - OpenStack Exporter
  - Ceph Exporter (MGR module)
  - Node Exporter (hardware)
  - cAdvisor (contenedores)
  
Grafana:  # Visualización
  - Dashboards pre-configurados por Kolla
  - Custom dashboards

Elasticsearch + Kibana:  # Logs centralizados
  - Logs de todos los servicios OpenStack
  - Correlación de eventos

Alertmanager:  # Alertas
  - PagerDuty/Slack/Email
  - Escalation policies
```

### Métricas Clave a Monitorizar

```yaml
Compute (Nova):
  - Hypervisor utilization (CPU, RAM, disk)
  - Instance count per tenant
  - Failed instance spawns
  - Instance migration errors
  
Network (Neutron):
  - Agent status (all should be UP)
  - Router count
  - Floating IP exhaustion
  - DHCP failures
  
Storage (Cinder + Ceph):
  - Volume creation failures
  - Ceph health (HEALTH_OK)
  - OSD utilization
  - Slow ops
  
Database:
  - MariaDB connections
  - Query latency
  - Galera cluster status
  
APIs:
  - Response time per endpoint
  - Error rate (4xx, 5xx)
  - Request rate
```

### Alertas Críticas (Ejemplos)

```yaml
# prometheus-alerts.yml

groups:
  - name: openstack_critical
    rules:
      - alert: HypervisorDown
        expr: openstack_nova_agent_state{service="nova-compute"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Hypervisor {% raw %}{{ $labels.hostname }}{% endraw %} is down"
      
      - alert: CephHealthError
        expr: ceph_health_status == 2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Ceph cluster is in HEALTH_ERR state"
      
      - alert: APIResponseTimeSlow
        expr: histogram_quantile(0.99, http_request_duration_seconds) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "API response time is high (p99 > 5s)"
```

## 📈 Capacity Planning

### Cálculo de Capacidad

```python
# capacity_calculator.py

def calculate_capacity(current_vms, growth_rate_monthly, months):
    """
    Calcula capacidad futura necesaria
    
    Args:
        current_vms: VMs actuales
        growth_rate_monthly: % de crecimiento mensual (ej: 10 = 10%)
        months: Meses a proyectar
    """
    future_vms = current_vms * ((1 + growth_rate_monthly/100) ** months)
    
    # Asumiendo promedio de 4 vCPUs y 8GB RAM por VM
    vcpus_needed = future_vms * 4
    ram_gb_needed = future_vms * 8
    
    # Con 1.5x overcommit CPU, 1.2x RAM
    physical_cores = vcpus_needed / 1.5
    physical_ram_gb = ram_gb_needed / 1.2
    
    print(f"Proyección a {months} meses:")
    print(f"  VMs estimadas: {int(future_vms)}")
    print(f"  vCPUs needed: {int(vcpus_needed)}")
    print(f"  Physical cores: {int(physical_cores)}")
    print(f"  Physical RAM: {int(physical_ram_gb)} GB")
    print(f"  Servers needed (32c, 256GB): {int(physical_ram_gb / 256) + 1}")

# Ejemplo
calculate_capacity(current_vms=500, growth_rate_monthly=5, months=12)
```

### Monitorizar Trends

```bash
# Query Prometheus para ver trends de uso
# Growth de instancias (últimos 30 días)
rate(openstack_nova_running_vms[30d])

# Utilización promedio de hypervisors
avg(openstack_nova_vcpus_used / openstack_nova_vcpus) * 100

# Proyección de capacidad (ejemplo con Grafana)
# Ver cuando se alcanzará 80% de utilización
```

### Cuándo Escalar

| Métrica | Threshold para Expansión |
|---------|--------------------------|
| CPU Hypervisor | >70% promedio sostenido |
| RAM Hypervisor | >80% promedio sostenido |
| Disk Storage | >75% usado |
| Ceph OSDs | >70% usado (any OSD) |
| Network bandwidth | >60% pico sostenido |
| Failed spawns | >5% de intentos |

## 🔒 Gestión de Seguridad

### Security Hardening Post-Deployment

```bash
# 1. Habilitar TLS para todas las APIs
# Ver guía de deployment

# 2. Rotar passwords periódicamente
vim /etc/kolla/passwords.yml
# Cambiar passwords críticas:
# - keystone_admin_password
# - database_password
# - rabbitmq_password

kolla-ansible -i /etc/kolla/multinode reconfigure

# 3. Auditar usuarios inactivos
openstack user list --long
# Deshabilitar usuarios >90 días inactivos
openstack user set --disable <user-id>

# 4. Revisar security groups permisivos
openstack security group list --all-projects
openstack security group rule list default
# Eliminar reglas 0.0.0.0/0 innecesarias

# 5. Habilitar audit logging
# Editar /etc/kolla/config/keystone/keystone.conf:
[audit]
enabled = True

kolla-ansible -i /etc/kolla/multinode reconfigure --tags keystone
```

### Gestión de Parches

```bash
# Automatizar con Ansible
# Crear playbook patch-openstack.yml:

---
- hosts: all
  become: yes
  tasks:
    - name: Update all packages
      apt:
        upgrade: dist
        update_cache: yes
      when: ansible_os_family == "Debian"
    
    - name: Check if reboot required
      stat:
        path: /var/run/reboot-required
      register: reboot_required
    
    - name: Reboot if needed
      reboot:
        reboot_timeout: 300
      when: reboot_required.stat.exists

# Ejecutar en rolling fashion (un nodo a la vez)
ansible-playbook -i inventory patch-openstack.yml --limit compute01
# Esperar a que vuelva y migrar VMs
# Repetir para cada compute
```

## 🚨 Incident Response

### Procedure para Outage Crítico

```markdown
## Incident Response Runbook

### Severity 1: Servicio Principal Caído (RTO: 1 hour)

1. **Detección** (0-5 min)
   - Alerta de monitorización
   - Verificar scope: `openstack service list`

2. **Comunicación** (5-10 min)
   - Notificar a stakeholders
   - Actualizar status page

3. **Diagnóstico** (10-20 min)
   - `docker ps -a` - Ver contenedores down
   - `docker logs <servicio>` - Identificar causa raíz
   - `ceph -s` si es storage issue

4. **Mitigación** (20-40 min)
   - Restart servicios: `docker restart <servicio>`
   - Failover to standby (si está en HA)
   - Rollback si upgrade reciente

5. **Resolución** (40-60 min)
   - Fix permanente
   - Verificar funcionalidad end-to-end
   - Launch test instance

6. **Post-Mortem** (después del incidente)
   - Root cause analysis
   - Prevenir recurrencia
   - Actualizar runbooks
```

### Logs de Auditoría

```bash
# Habilitar audit en Keystone
# /etc/kolla/config/keystone/keystone.conf
[audit]
enabled = True
audit_map_file = /etc/keystone/api_audit_map.conf

# Ver auditoría
# En Kibana, filtrar por "audit" tag

# Ejemplo de eventos a auditar:
# - Creación/eliminación de usuarios
# - Cambios de roles
# - Accesos fallidos
# - Modificación de quotas
```

## 🎓 Runbooks de Operaciones Comunes

### Agregar Nuevo Compute Node

```bash
# 1. Preparar hardware y OS
# 2. Configurar networking (ver guía de deployment)
# 3. Añadir al inventario
vim /etc/kolla/multinode
# Añadir compute03 en [compute]

# 4. Deploy solo en nuevo nodo
kolla-ansible -i /etc/kolla/multinode deploy --limit compute03

# 5. Verificar
openstack hypervisor list
```

### Drenar Compute Node (Mantenimiento)

```bash
# 1. Deshabilitar scheduling
openstack compute service set --disable compute01 nova-compute \
  --disable-reason "Mantenimiento programado"

# 2. Migrar instancias
# Listar instancias en el host
openstack server list --all-projects --host compute01

# Migrar cada una (cold migration si no hay shared storage)
for vm in $(openstack server list --host compute01 -f value -c ID); do
  openstack server migrate $vm --wait
done

# 3. Verificar que no queden VMs
openstack server list --host compute01

# 4. Proceder con mantenimiento
# Reiniciar, patch, etc.

# 5. Rehabilitar
openstack compute service set --enable compute01 nova-compute
```

### Limpiar Recursos Huérfanos

```bash
#!/bin/bash
# cleanup-orphaned-resources.sh

echo "Limpiando recursos huérfanos..."

# Puertos sin dispositivo
echo "1. Puertos sin dispositivo:"
openstack port list --device-owner none -f value -c ID | while read port; do
  echo "  Eliminando port $port"
  openstack port delete $port
done

# Volúmenes error >7 días
echo "2. Volúmenes en ERROR (antiguos):"
# Requiere script Python para filtrar por fecha

# Floating IPs sin asignar
echo "3. Floating IPs sin uso:"
openstack floating ip list --status DOWN -f value -c ID | while read fip; do
  echo "  Liberando floating IP $fip"
  openstack floating ip delete $fip
done

echo "Limpieza completada"
```

## 📚 Referencias

- [OpenStack Operations Guide](https://docs.openstack.org/operations-guide/)
- [Kolla-Ansible Operations](https://docs.openstack.org/kolla-ansible/latest/user/operating-kolla.html)
- [OpenStack Upgrade Guide](https://docs.openstack.org/operations-guide/ops-upgrades.html)

---

!!! success "Operaciones Day-2 Implementadas"
    Con estas prácticas, tu cloud OpenStack estará listo para producción a largo plazo.

!!! tip "Automatización"
    Automatiza todo lo posible con Ansible, scripts y monitorización proactiva.
