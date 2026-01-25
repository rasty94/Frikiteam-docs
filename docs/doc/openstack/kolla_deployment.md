---
title: "OpenStack Deployment with Kolla-Ansible: Complete Production Guide"
description: "Step-by-step guide to deploy OpenStack in production using Kolla-Ansible. Hardware requirements, network design, installation, and post-deployment verification."
keywords: OpenStack, Kolla-Ansible, deployment, production, containers, Docker, infrastructure, cloud, installation guide
date: 2026-01-25
updated: 2026-01-25
difficulty: intermediate
estimated_time: 8 min
category: Cloud Computing
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Despliegue de OpenStack con Kolla-Ansible

## 🎯 Introducción

Kolla-Ansible es la herramienta recomendada para desplegar OpenStack en producción usando contenedores Docker. Esta guía cubre desde la planificación hasta el despliegue completo de un cloud funcional.

### ¿Por qué Kolla-Ansible?

- ✅ **Contenedorizado**: Todos los servicios en Docker, fácil actualización
- ✅ **Alta Disponibilidad**: Soporte nativo para HA con HAProxy y Keepalived
- ✅ **Modular**: Activa solo los servicios que necesites
- ✅ **Mantenible**: Upgrades simplificados entre releases
- ✅ **Comunidad activa**: Respaldado por OpenStack Foundation

## 📋 Requisitos Previos

### Hardware Mínimo

#### Nodo Controller (mínimo 3 para HA)
- **CPU**: 8 cores (16 threads recomendado)
- **RAM**: 32 GB (64 GB recomendado)
- **Disco**: 
  - 100 GB SSD para SO
  - 500 GB para imágenes y logs
- **Red**: 2 interfaces mínimo (4 recomendado)

#### Nodo Compute (escalable)
- **CPU**: 16+ cores con soporte VT-x/AMD-V
- **RAM**: 64 GB+ (depende de sobresuscripción deseada)
- **Disco**: 
  - 100 GB SSD para SO
  - Resto para instancias efímeras
- **Red**: 2 interfaces mínimo (4 recomendado)

#### Nodo Storage (para Ceph, mínimo 3)
- **CPU**: 4 cores por OSD
- **RAM**: 2-4 GB por OSD
- **Disco**: 
  - 100 GB SSD para SO
  - 1+ discos para OSDs (NVMe/SSD preferible)
- **Red**: 2 interfaces 10Gbps+ (storage + replicación)

### Software Base

```bash
# Sistema operativo soportado
Ubuntu 22.04 LTS  # Recomendado
Rocky Linux 9
Debian 12
```

## 🌐 Diseño de Red

### Arquitectura de 4 Redes (Recomendada)

```yaml
Redes:
  Management Network (VLAN 10):
    Subnet: 10.0.10.0/24
    Uso: Gestión, Ansible, SSH
    
  Internal API Network (VLAN 20):
    Subnet: 10.0.20.0/24
    Uso: Comunicación entre servicios OpenStack
    
  Tunnel Network (VLAN 30):
    Subnet: 10.0.30.0/24
    Uso: VXLAN/GRE para redes de tenant
    
  External Network (sin VLAN o VLAN específica):
    Subnet: 192.168.100.0/24  # Ejemplo
    Uso: Floating IPs, acceso externo
    
  Storage Network (VLAN 40, opcional):
    Subnet: 10.0.40.0/24
    Uso: Tráfico Ceph (front-end)
    
  Storage Replication (VLAN 50, opcional):
    Subnet: 10.0.50.0/24
    Uso: Tráfico Ceph (replicación OSD)
```

### Mapeo de Interfaces

```ini
# Ejemplo para nodo con 4 NICs
eno1: Management Network (bond con eno2 opcional)
eno2: Internal API + Tunnel (trunk VLAN)
eno3: External Network
eno4: Storage Network (si se usa Ceph)
```

## 🔧 Preparación del Entorno

### 1. Configurar Nodos Base

En **todos los nodos**:

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y python3-dev libffi-dev gcc libssl-dev

# Configurar NTP (crítico para Ceph)
sudo apt install -y chrony
sudo systemctl enable --now chrony

# Deshabilitar firewall (se configurará después)
sudo systemctl stop ufw
sudo systemctl disable ufw

# Configurar hostname
sudo hostnamectl set-hostname controller01.cloud.local

# Añadir entradas /etc/hosts
cat <<EOF | sudo tee -a /etc/hosts
10.0.10.10 controller01.cloud.local controller01
10.0.10.11 controller02.cloud.local controller02
10.0.10.12 controller03.cloud.local controller03
10.0.10.20 compute01.cloud.local compute01
10.0.10.21 compute02.cloud.local compute02
10.0.10.30 storage01.cloud.local storage01
10.0.10.31 storage02.cloud.local storage02
10.0.10.32 storage03.cloud.local storage03
EOF

# Configurar interfaces de red
# Ejemplo con netplan (Ubuntu)
sudo tee /etc/netplan/01-netcfg.yaml <<EOF
network:
  version: 2
  renderer: networkd
  ethernets:
    eno1:
      dhcp4: no
      addresses:
        - 10.0.10.10/24
      routes:
        - to: default
          via: 10.0.10.1
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
    
    eno2:
      dhcp4: no
    
    eno3:
      dhcp4: no
    
    eno4:
      dhcp4: no
  
  vlans:
    eno2.20:
      id: 20
      link: eno2
      addresses:
        - 10.0.20.10/24
    
    eno2.30:
      id: 30
      link: eno2
      addresses:
        - 10.0.30.10/24
EOF

sudo netplan apply
```

### 2. Configurar Nodo Deployment

Desde un nodo de deployment (puede ser controller01):

```bash
# Crear usuario para deployment
sudo useradd -m -s /bin/bash kolla
echo "kolla ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/kolla

# Cambiar a usuario kolla
sudo su - kolla

# Generar clave SSH
ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519

# Copiar clave a todos los nodos
for host in controller{01..03} compute{01..02} storage{01..03}; do
  ssh-copy-id -i ~/.ssh/id_ed25519.pub kolla@$host
done

# Crear entorno virtual Python
python3 -m venv ~/kolla-venv
source ~/kolla-venv/bin/activate

# Instalar Ansible y Kolla-Ansible
pip install -U pip
pip install 'ansible-core>=2.14,<2.16'
pip install 'kolla-ansible==17.0.0'  # OpenStack 2024.1 (Caracal)

# Instalar colecciones Ansible requeridas
kolla-ansible install-deps

# Crear directorio de configuración
sudo mkdir -p /etc/kolla
sudo chown kolla:kolla /etc/kolla

# Copiar archivos de configuración base
cp -r ~/kolla-venv/share/kolla-ansible/etc_examples/kolla/* /etc/kolla
cp ~/kolla-venv/share/kolla-ansible/ansible/inventory/multinode /etc/kolla/
```

## 📝 Configuración de Kolla-Ansible

### 1. Inventario de Hosts

Editar `/etc/kolla/multinode`:

```ini
[control]
controller01 ansible_host=10.0.10.10
controller02 ansible_host=10.0.10.11
controller03 ansible_host=10.0.10.12

[network]
controller01
controller02
controller03

[compute]
compute01 ansible_host=10.0.10.20
compute02 ansible_host=10.0.10.21

[monitoring]
controller01

[storage]
storage01 ansible_host=10.0.10.30
storage02 ansible_host=10.0.10.31
storage03 ansible_host=10.0.10.32

# Variables comunes
[all:vars]
ansible_user=kolla
ansible_become=true
ansible_python_interpreter=/usr/bin/python3
```

### 2. Configuración Global

Editar `/etc/kolla/globals.yml`:

```yaml
---
# Configuración básica
kolla_base_distro: "ubuntu"
kolla_install_type: "source"
openstack_release: "2024.1"  # Caracal

# Networking
network_interface: "eno1"               # Management
api_interface: "eno2.20"                # Internal API
tunnel_interface: "eno2.30"             # Tunnels (VXLAN)
neutron_external_interface: "eno3"      # External (sin IP configurada)
storage_interface: "eno4"               # Storage (opcional)

kolla_internal_vip_address: "10.0.20.100"
kolla_external_vip_address: "192.168.100.100"

# Neutron
neutron_plugin_agent: "openvswitch"
neutron_extension_drivers:
  - name: "port_security"
  - name: "dns"

enable_neutron_provider_networks: "yes"

# Servicios habilitados
enable_cinder: "yes"
enable_cinder_backup: "no"
enable_cinder_backend_lvm: "no"
enable_cinder_backend_nfs: "no"

enable_heat: "yes"
enable_horizon: "yes"
enable_horizon_neutron_lbaas: "{{ enable_neutron_lbaas }}"

enable_glance: "yes"
enable_nova: "yes"
enable_neutron: "yes"
enable_keystone: "yes"

# Ceph integration (si se usa)
enable_ceph: "no"  # Cambiar a "yes" si se despliega Ceph
glance_backend_ceph: "yes"
cinder_backend_ceph: "yes"
nova_backend_ceph: "yes"
ceph_nova_user: "cinder"
ceph_nova_keyring: "ceph.client.cinder.keyring"

# Monitorización
enable_prometheus: "yes"
enable_grafana: "yes"

# Logs
enable_central_logging: "yes"
enable_elasticsearch: "yes"
enable_kibana: "yes"

# Passwords
# NOTA: Se generarán automáticamente con kolla-genpwd
```

### 3. Generar Passwords

```bash
kolla-genpwd
```

Esto genera `/etc/kolla/passwords.yml` con todas las passwords aleatorias.

## 🚀 Despliegue

### 1. Verificar Configuración

```bash
# Activar venv si no está activo
source ~/kolla-venv/bin/activate

# Verificar conectividad
ansible -i /etc/kolla/multinode all -m ping

# Verificar dependencias
kolla-ansible -i /etc/kolla/multinode bootstrap-servers
```

### 2. Precheck

```bash
kolla-ansible -i /etc/kolla/multinode prechecks
```

Esto verifica:
- Conectividad de red
- Versiones de software
- Espacio en disco
- Configuración de Docker
- Puertos requeridos

### 3. Deploy

```bash
# Desplegar OpenStack (20-40 minutos)
kolla-ansible -i /etc/kolla/multinode deploy

# Verificar estado de contenedores
docker ps -a

# Generar archivo de credenciales
kolla-ansible -i /etc/kolla/multinode post-deploy

# Las credenciales se guardan en:
cat /etc/kolla/admin-openrc.sh
```

### 4. Inicializar OpenStack

```bash
# Cargar credenciales
source /etc/kolla/admin-openrc.sh

# Instalar cliente OpenStack
pip install python-openstackclient

# Verificar servicios
openstack service list
openstack endpoint list

# Crear recursos iniciales
kolla-ansible -i /etc/kolla/multinode init-runonce
```

El script `init-runonce` crea:
- Flavors básicos (m1.tiny, m1.small, m1.medium)
- Imagen Cirros de prueba
- Red externa y subnet
- Red de demo
- Security groups con reglas SSH/ICMP
- Keypair de prueba

## ✅ Verificación Post-Despliegue

### 1. Verificar Servicios

```bash
source /etc/kolla/admin-openrc.sh

# Listar servicios
openstack service list

# Output esperado:
# +----------------------------------+------------+--------------+
# | ID                               | Name       | Type         |
# +----------------------------------+------------+--------------+
# | ...                              | keystone   | identity     |
# | ...                              | glance     | image        |
# | ...                              | nova       | compute      |
# | ...                              | neutron    | network      |
# | ...                              | cinder     | volumev3     |
# | ...                              | heat       | orchestration|
# +----------------------------------+------------+--------------+

# Verificar compute hosts
openstack compute service list

# Verificar network agents
openstack network agent list

# Verificar hypervisors
openstack hypervisor list
```

### 2. Lanzar Instancia de Prueba

```bash
# Crear instancia
openstack server create \
  --flavor m1.small \
  --image cirros \
  --network demo-net \
  --key-name mykey \
  --security-group default \
  test-instance

# Verificar estado
openstack server list

# Ver console log
openstack console log show test-instance

# Asignar Floating IP
FLOATING_IP=$(openstack floating ip create public1 -f value -c floating_ip_address)
openstack server add floating ip test-instance $FLOATING_IP

# Probar conectividad
ping -c 4 $FLOATING_IP
ssh -i mykey.pem cirros@$FLOATING_IP
```

### 3. Acceder a Horizon

```
URL: https://192.168.100.100
Usuario: admin
Password: (ver /etc/kolla/passwords.yml, keystone_admin_password)
```

## 🔍 Comandos Útiles de Operación

### Gestión de Contenedores

```bash
# Ver logs de un servicio
docker logs nova_compute

# Reiniciar un servicio
docker restart nova_compute

# Ejecutar comando en contenedor
docker exec -it nova_compute bash

# Ver recursos consumidos
docker stats

# Ver todos los contenedores Kolla
docker ps --filter "label=kolla_version"
```

### Reconfiguraciones

```bash
# Después de modificar /etc/kolla/globals.yml
kolla-ansible -i /etc/kolla/multinode reconfigure

# Actualizar solo un servicio
kolla-ansible -i /etc/kolla/multinode reconfigure --tags nova
```

### Upgrades

```bash
# Actualizar Kolla-Ansible
pip install --upgrade kolla-ansible

# Upgrade OpenStack
kolla-ansible -i /etc/kolla/multinode prechecks
kolla-ansible -i /etc/kolla/multinode pull  # Descargar nuevas imágenes
kolla-ansible -i /etc/kolla/multinode upgrade
```

## 🛡️ Seguridad Post-Despliegue

### 1. Cambiar Passwords por Defecto

```bash
# Editar /etc/kolla/passwords.yml manualmente
# O regenerar passwords específicas:
sed -i 's/keystone_admin_password:.*/keystone_admin_password: NuevoPassword123/' /etc/kolla/passwords.yml

# Aplicar cambios
kolla-ansible -i /etc/kolla/multinode reconfigure --tags keystone
```

### 2. Configurar Firewall

```bash
# Permitir solo lo necesario
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # Horizon HTTP
sudo ufw allow 443/tcp     # Horizon HTTPS
sudo ufw allow 6080/tcp    # NoVNC (console)
sudo ufw allow 8774/tcp    # Nova API
sudo ufw allow 9292/tcp    # Glance API
sudo ufw allow 9696/tcp    # Neutron API
sudo ufw allow 8776/tcp    # Cinder API
sudo ufw allow 5000/tcp    # Keystone API
sudo ufw enable
```

### 3. TLS/SSL para APIs

Modificar `/etc/kolla/globals.yml`:

```yaml
kolla_enable_tls_external: "yes"
kolla_external_fqdn: "cloud.example.com"
kolla_external_fqdn_cert: "/etc/kolla/certificates/cloud.example.com.crt"
kolla_external_fqdn_key: "/etc/kolla/certificates/cloud.example.com.key"
```

Copiar certificados:

```bash
sudo mkdir -p /etc/kolla/certificates
sudo cp /path/to/cert.crt /etc/kolla/certificates/cloud.example.com.crt
sudo cp /path/to/cert.key /etc/kolla/certificates/cloud.example.com.key

kolla-ansible -i /etc/kolla/multinode reconfigure
```

## 📊 Monitorización

### Acceder a Grafana

```
URL: http://10.0.20.100:3000
Usuario: admin
Password: (ver /etc/kolla/passwords.yml, grafana_admin_password)
```

Dashboards preconfigurados:
- OpenStack Overview
- Nova Compute Metrics
- Neutron Network Stats
- Cinder Volume Stats

### Logs Centralizados (Kibana)

```
URL: http://10.0.20.100:5601
```

## 📚 Recursos Adicionales

- [Kolla-Ansible Docs](https://docs.openstack.org/kolla-ansible/latest/)
- [OpenStack Install Guide](https://docs.openstack.org/install-guide/)
- [Kolla-Ansible GitHub](https://github.com/openstack/kolla-ansible)

## 🎓 Próximos Pasos

1. **Integrar Ceph**: Ver [Integración OpenStack + Ceph](openstack_ceph_integration.md)
2. **Day-2 Operations**: Ver [Operaciones Day-2](day2.md)
3. **Troubleshooting**: Ver [Resolución de Problemas](troubleshooting_openstack.md)

---

!!! tip "¿Problemas durante el despliegue?"
    Revisa los logs con `docker logs <contenedor>` y consulta nuestra [guía de troubleshooting](troubleshooting_openstack.md).

!!! warning "Alta Disponibilidad"
    Esta guía cubre HA básico. Para configuraciones avanzadas (Pacemaker, activo-activo), consulta la [documentación oficial de HA](https://docs.openstack.org/ha-guide/).
