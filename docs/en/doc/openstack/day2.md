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
prerequisites: ["Basic DevOps knowledge"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# OpenStack — Day-2 Operations

## 🎯 Introduction

Day-2 Operations covers every operational task that comes after the initial OpenStack deployment. This guide covers:

- ✅ Upgrades and updates
- ✅ Backups and disaster recovery
- ✅ Monitoring and alerting
- ✅ Capacity planning
- ✅ Recurring troubleshooting
- ✅ Security management
- ✅ Performance tuning

## 📅 Recommended Maintenance Schedule

### Daily Tasks

```bash
# Automated health check (via cron)
0 9 * * * /usr/local/bin/openstack-health-check.sh

# Check critical services
openstack compute service list
openstack network agent list
openstack volume service list

# Review error logs
docker logs --since 24h nova_compute | grep -i error
docker logs --since 24h neutron_openvswitch_agent | grep -i error
```

### Weekly Tasks

```bash
# Clean up stale ERROR instances (>7 days)
openstack server list --all-projects --status ERROR \
  --long | awk '{print $1}' | xargs -I {} openstack server delete {}

# Clean up old snapshots (>30 days)
# Custom script, depending on your policy

# Verify backups
ls -lh /backups/openstack/ | tail -10

# Review resource usage
openstack hypervisor stats show
ceph df  # If Ceph is in use
```

### Monthly Tasks

```bash
# Refresh base images
# Download new Ubuntu, CentOS, etc. releases
# Upload to Glance and mark the old ones as deprecated

# Capacity review
# Check trends in Grafana
# Plan an expansion if needed

# Security updates
apt update && apt upgrade  # On every node
# Reconfigure OpenStack if anything changed
kolla-ansible -i /etc/kolla/multinode reconfigure
```

### Quarterly Tasks

```bash
# OpenStack upgrades (following the release cadence)
# See the Upgrades section below

# Disaster recovery drill
# Restore backups into a test environment

# Security review
# Audit users, roles and security groups
# Verify compliance
```

## 🔄 OpenStack Upgrades

### Upgrade Strategy

OpenStack follows a SLURP model (stable releases roughly every year):

```
2023.1 (Antelope) → 2023.2 (Bobcat) → 2024.1 (Caracal) → 2024.2 (Dalmatian)
```

**Recommendation**: upgrade every 2-3 releases (skip the intermediate ones when using SLURP)

### Pre-Upgrade Checklist

```bash
# 1. Check the current release
kolla-ansible --version
openstack --version

# 2. Full backup (see the Backups section)
./backup-openstack.sh

# 3. Check cluster health
kolla-ansible -i /etc/kolla/multinode prechecks

# 4. Read the release notes
# https://releases.openstack.org/caracal/index.html

# 5. Prepare the maintenance window
# Notify users, schedule the downtime

# 6. Check Kolla image compatibility
# https://quay.io/repository/openstack.kolla/
```

### Upgrade Process (Kolla-Ansible)

```bash
# 1. Update Kolla-Ansible
pip install --upgrade kolla-ansible==18.0.0  # New version

# 2. Update Ansible dependencies
kolla-ansible install-deps

# 3. Regenerate passwords (for new services)
kolla-genpwd

# 4. Merge configuration
# Compare /etc/kolla/globals.yml against the new template
diff /etc/kolla/globals.yml \
  ~/kolla-venv/share/kolla-ansible/etc_examples/kolla/globals.yml

# 5. Pull the new images
kolla-ansible -i /etc/kolla/multinode pull

# 6. Prechecks
kolla-ansible -i /etc/kolla/multinode prechecks

# 7. Upgrade (no downtime when running HA)
kolla-ansible -i /etc/kolla/multinode upgrade

# 8. Post-upgrade checks
openstack service list
openstack compute service list
openstack network agent list

# 9. Launch a test instance
openstack server create --flavor m1.small --image cirros test-upgrade
```

### Rollback Strategy

```bash
# If the upgrade fails:

# 1. Stop the new services
kolla-ansible -i /etc/kolla/multinode stop

# 2. Restore the previous images
# Edit /etc/kolla/globals.yml:
# openstack_release: "2023.2"  # Previous version

# 3. Reconfigure with the previous version
kolla-ansible -i /etc/kolla/multinode reconfigure

# 4. Restore the DB if needed
# See the Backups section

# 5. Verify everything works
openstack server list
```

## 💾 Backups

### What to Back Up

| Component | What to Back Up | Frequency | Retention |
|-----------|-----------------|-----------|-----------|
| **MariaDB** | All databases | Daily | 30 days |
| **Config Files** | /etc/kolla | On change | 90 days |
| **Glance Images** | Images pool (Ceph) or /var/lib/glance | Weekly | 60 days |
| **Cinder Volumes** | Critical volumes | Per SLA | Per SLA |
| **Keystone** | User/role dump | Weekly | 90 days |

### MariaDB Backup Script

```bash
#!/bin/bash
# /usr/local/bin/backup-openstack-dbs.sh

BACKUP_DIR="/backups/openstack/mariadb"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# Get the MariaDB password
DB_PASSWORD=$(grep database_password /etc/kolla/passwords.yml | awk '{print $2}')

# Back up each database
for db in keystone glance nova nova_api nova_cell0 neutron cinder heat; do
  echo "Backing up $db..."
  docker exec mariadb mysqldump \
    -uroot -p$DB_PASSWORD \
    --single-transaction \
    --routines \
    --triggers \
    $db | gzip > $BACKUP_DIR/${db}_${DATE}.sql.gz
done

# Full backup (alternative)
docker exec mariadb mysqldump \
  -uroot -p$DB_PASSWORD \
  --all-databases \
  --single-transaction \
  --routines \
  --triggers | gzip > $BACKUP_DIR/all_databases_${DATE}.sql.gz

# Prune old backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_DIR"
ls -lh $BACKUP_DIR | tail -5
```

### Restoring MariaDB

```bash
#!/bin/bash
# restore-openstack-db.sh

BACKUP_FILE="/backups/openstack/mariadb/keystone_20260125_100000.sql.gz"
DB_NAME="keystone"
DB_PASSWORD=$(grep database_password /etc/kolla/passwords.yml | awk '{print $2}')

# Stop the services using this DB
kolla-ansible -i /etc/kolla/multinode stop --tags keystone

# Restore
zcat $BACKUP_FILE | docker exec -i mariadb mysql -uroot -p$DB_PASSWORD $DB_NAME

# Restart the services
kolla-ansible -i /etc/kolla/multinode deploy --tags keystone

# Verify
openstack user list
```

### Ceph Backups (if in use)

```bash
# Snapshot of the whole pool
rbd snap create images@backup-$(date +%Y%m%d)
rbd snap create volumes@backup-$(date +%Y%m%d)

# Incremental export (more efficient)
rbd export-diff images/<image-name> /backups/ceph/image-diff-$(date +%Y%m%d).diff

# Automate it with cron
0 2 * * * /usr/local/bin/backup-ceph-pools.sh
```

### Disaster Recovery Plan

```markdown
## DR Procedure (RTO: 4 hours, RPO: 24 hours)

1. **Prepare the replacement infrastructure** (1h)
   - Provision hardware/VMs
   - Set up basic networking

2. **Restore the controllers** (1.5h)
   - Fresh Kolla-Ansible deploy
   - Restore /etc/kolla
   - Restore MariaDB from backup

3. **Restore the Compute nodes** (30min)
   - Deploy nova-compute
   - Sync with the DB

4. **Restore Storage** (30min)
   - Restore the Ceph cluster, or
   - Mount the storage backends

5. **Verification** (30min)
   - Launch test instances
   - Check access to volumes and images
   - Test connectivity
```

## 📊 Monitoring and Alerting

### Monitoring Stack

```yaml
Prometheus:  # Metrics
  - OpenStack Exporter
  - Ceph Exporter (MGR module)
  - Node Exporter (hardware)
  - cAdvisor (containers)
  
Grafana:  # Visualization
  - Dashboards pre-configured by Kolla
  - Custom dashboards

Elasticsearch + Kibana:  # Centralized logs
  - Logs from every OpenStack service
  - Event correlation

Alertmanager:  # Alerts
  - PagerDuty/Slack/Email
  - Escalation policies
```

### Key Metrics to Monitor

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

### Critical Alerts (Examples)

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

### Capacity Calculation

```python
# capacity_calculator.py

def calculate_capacity(current_vms, growth_rate_monthly, months):
    """
    Calculates the future capacity required
    
    Args:
        current_vms: current VMs
        growth_rate_monthly: monthly growth rate in % (e.g. 10 = 10%)
        months: months to project
    """
    future_vms = current_vms * ((1 + growth_rate_monthly/100) ** months)
    
    # Assuming an average of 4 vCPUs and 8GB RAM per VM
    vcpus_needed = future_vms * 4
    ram_gb_needed = future_vms * 8
    
    # With 1.5x CPU overcommit and 1.2x RAM
    physical_cores = vcpus_needed / 1.5
    physical_ram_gb = ram_gb_needed / 1.2
    
    print(f"Projection over {months} months:")
    print(f"  Estimated VMs: {int(future_vms)}")
    print(f"  vCPUs needed: {int(vcpus_needed)}")
    print(f"  Physical cores: {int(physical_cores)}")
    print(f"  Physical RAM: {int(physical_ram_gb)} GB")
    print(f"  Servers needed (32c, 256GB): {int(physical_ram_gb / 256) + 1}")

# Example
calculate_capacity(current_vms=500, growth_rate_monthly=5, months=12)
```

### Monitoring Trends

```bash
# Query Prometheus to see usage trends
# Instance growth (last 30 days)
rate(openstack_nova_running_vms[30d])

# Average hypervisor utilization
avg(openstack_nova_vcpus_used / openstack_nova_vcpus) * 100

# Capacity projection (example with Grafana)
# Find out when 80% utilization will be reached
```

### When to Scale

| Metric | Expansion Threshold |
|--------|---------------------|
| Hypervisor CPU | >70% sustained average |
| Hypervisor RAM | >80% sustained average |
| Disk Storage | >75% used |
| Ceph OSDs | >70% used (any OSD) |
| Network bandwidth | >60% sustained peak |
| Failed spawns | >5% of attempts |

## 🔒 Security Management

### Post-Deployment Security Hardening

```bash
# 1. Enable TLS on every API
# See the deployment guide

# 2. Rotate passwords regularly
vim /etc/kolla/passwords.yml
# Change the critical passwords:
# - keystone_admin_password
# - database_password
# - rabbitmq_password

kolla-ansible -i /etc/kolla/multinode reconfigure

# 3. Audit inactive users
openstack user list --long
# Disable users inactive for more than 90 days
openstack user set --disable <user-id>

# 4. Review permissive security groups
openstack security group list --all-projects
openstack security group rule list default
# Remove any unnecessary 0.0.0.0/0 rules

# 5. Enable audit logging
# Edit /etc/kolla/config/keystone/keystone.conf:
[audit]
enabled = True

kolla-ansible -i /etc/kolla/multinode reconfigure --tags keystone
```

### Patch Management

```bash
# Automate it with Ansible
# Create the playbook patch-openstack.yml:

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

# Run it in a rolling fashion (one node at a time)
ansible-playbook -i inventory patch-openstack.yml --limit compute01
# Wait for it to come back and migrate the VMs
# Repeat for each compute node
```

## 🚨 Incident Response

### Procedure for a Critical Outage

```markdown
## Incident Response Runbook

### Severity 1: Core Service Down (RTO: 1 hour)

1. **Detection** (0-5 min)
   - Monitoring alert
   - Check the scope: `openstack service list`

2. **Communication** (5-10 min)
   - Notify stakeholders
   - Update the status page

3. **Diagnosis** (10-20 min)
   - `docker ps -a` - find containers that are down
   - `docker logs <service>` - identify the root cause
   - `ceph -s` if it is a storage issue

4. **Mitigation** (20-40 min)
   - Restart services: `docker restart <service>`
   - Failover to standby (if running HA)
   - Roll back if there was a recent upgrade

5. **Resolution** (40-60 min)
   - Permanent fix
   - Verify end-to-end functionality
   - Launch test instance

6. **Post-Mortem** (after the incident)
   - Root cause analysis
   - Prevent recurrence
   - Update the runbooks
```

### Audit Logs

```bash
# Enable auditing in Keystone
# /etc/kolla/config/keystone/keystone.conf
[audit]
enabled = True
audit_map_file = /etc/keystone/api_audit_map.conf

# Review the audit trail
# In Kibana, filter by the "audit" tag

# Examples of events worth auditing:
# - User creation/deletion
# - Role changes
# - Failed logins
# - Quota changes
```

## 🎓 Runbooks for Common Operations

### Adding a New Compute Node

```bash
# 1. Prepare the hardware and OS
# 2. Configure networking (see the deployment guide)
# 3. Add it to the inventory
vim /etc/kolla/multinode
# Add compute03 under [compute]

# 4. Deploy only on the new node
kolla-ansible -i /etc/kolla/multinode deploy --limit compute03

# 5. Verify
openstack hypervisor list
```

### Draining a Compute Node (Maintenance)

```bash
# 1. Disable scheduling
openstack compute service set --disable compute01 nova-compute \
  --disable-reason "Scheduled maintenance"

# 2. Migrate the instances
# List the instances running on the host
openstack server list --all-projects --host compute01

# Migrate each one (cold migration if there is no shared storage)
for vm in $(openstack server list --host compute01 -f value -c ID); do
  openstack server migrate $vm --wait
done

# 3. Confirm no VMs are left
openstack server list --host compute01

# 4. Proceed with the maintenance
# Reboot, patch, etc.

# 5. Re-enable it
openstack compute service set --enable compute01 nova-compute
```

### Cleaning Up Orphaned Resources

```bash
#!/bin/bash
# cleanup-orphaned-resources.sh

echo "Cleaning up orphaned resources..."

# Ports with no device
echo "1. Ports with no device:"
openstack port list --device-owner none -f value -c ID | while read port; do
  echo "  Deleting port $port"
  openstack port delete $port
done

# Volumes in ERROR for >7 days
echo "2. Volumes in ERROR (stale):"
# Requires a Python script to filter by date

# Unassigned floating IPs
echo "3. Unused floating IPs:"
openstack floating ip list --status DOWN -f value -c ID | while read fip; do
  echo "  Releasing floating IP $fip"
  openstack floating ip delete $fip
done

echo "Cleanup completed"
```

## 📚 References

- [OpenStack Operations Guide](https://docs.openstack.org/operations-guide/)
- [Kolla-Ansible Operations](https://docs.openstack.org/kolla-ansible/latest/user/operating-kolla.html)
- [OpenStack Upgrade Guide](https://docs.openstack.org/operations-guide/ops-upgrades.html)

---

!!! success "Day-2 Operations in Place"
    With these practices, your OpenStack cloud is ready for long-term production use.

!!! tip "Automation"
    Automate as much as possible with Ansible, scripts and proactive monitoring.
