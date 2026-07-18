---
title: "OpenStack Deployment with Kolla-Ansible: Complete Production Guide"
description: "Step-by-step guide to deploying OpenStack in production with Kolla-Ansible. Hardware requirements, network design, installation, and post-deployment verification."
keywords: OpenStack, Kolla-Ansible, deployment, production, containers, Docker, infrastructure, cloud, installation guide
date: 2026-01-25
updated: 2026-01-25
difficulty: intermediate
estimated_time: 8 min
category: Cloud Computing
status: published
last_reviewed: 2026-01-25
prerequisites: ["Basic DevOps knowledge"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# OpenStack Deployment with Kolla-Ansible

## 🎯 Introduction

Kolla-Ansible is the recommended tool for deploying OpenStack in production using Docker containers. This guide takes you from planning all the way through to a fully working cloud.

### Why Kolla-Ansible?

- ✅ **Containerised**: Every service runs in Docker, making updates straightforward
- ✅ **High Availability**: Native HA support with HAProxy and Keepalived
- ✅ **Modular**: Enable only the services you actually need
- ✅ **Maintainable**: Simplified upgrades between releases
- ✅ **Active community**: Backed by the OpenStack Foundation

## 📋 Prerequisites

### Minimum Hardware

#### Controller Node (at least 3 for HA)
- **CPU**: 8 cores (16 threads recommended)
- **RAM**: 32 GB (64 GB recommended)
- **Disk**:
  - 100 GB SSD for the OS
  - 500 GB for images and logs
- **Network**: 2 interfaces minimum (4 recommended)

#### Compute Node (scalable)
- **CPU**: 16+ cores with VT-x/AMD-V support
- **RAM**: 64 GB+ (depends on your target overcommit ratio)
- **Disk**:
  - 100 GB SSD for the OS
  - Remaining capacity for ephemeral instances
- **Network**: 2 interfaces minimum (4 recommended)

#### Storage Node (for Ceph, at least 3)
- **CPU**: 4 cores per OSD
- **RAM**: 2-4 GB per OSD
- **Disk**:
  - 100 GB SSD for the OS
  - 1+ disks for OSDs (NVMe/SSD preferred)
- **Network**: 2 interfaces at 10Gbps+ (storage + replication)

### Base Software

```bash
# Supported operating systems
Ubuntu 22.04 LTS  # Recommended
Rocky Linux 9
Debian 12
```

## 🌐 Network Design

### Four-Network Architecture (Recommended)

```yaml
Networks:
  Management Network (VLAN 10):
    Subnet: 10.0.10.0/24
    Purpose: Management, Ansible, SSH

  Internal API Network (VLAN 20):
    Subnet: 10.0.20.0/24
    Purpose: Communication between OpenStack services

  Tunnel Network (VLAN 30):
    Subnet: 10.0.30.0/24
    Purpose: VXLAN/GRE for tenant networks

  External Network (untagged or a dedicated VLAN):
    Subnet: 192.168.100.0/24  # Example
    Purpose: Floating IPs, external access

  Storage Network (VLAN 40, optional):
    Subnet: 10.0.40.0/24
    Purpose: Ceph traffic (front-end)

  Storage Replication (VLAN 50, optional):
    Subnet: 10.0.50.0/24
    Purpose: Ceph traffic (OSD replication)
```

### Interface Mapping

```ini
# Example for a node with 4 NICs
eno1: Management Network (optionally bonded with eno2)
eno2: Internal API + Tunnel (VLAN trunk)
eno3: External Network
eno4: Storage Network (if Ceph is used)
```

## 🔧 Preparing the Environment

### 1. Configure the Base Nodes

On **every node**:

```bash
# Update the system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-dev libffi-dev gcc libssl-dev

# Configure NTP (critical for Ceph)
sudo apt install -y chrony
sudo systemctl enable --now chrony

# Disable the firewall (it will be configured later)
sudo systemctl stop ufw
sudo systemctl disable ufw

# Set the hostname
sudo hostnamectl set-hostname controller01.cloud.local

# Add the /etc/hosts entries
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

# Configure the network interfaces
# Example using netplan (Ubuntu)
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

### 2. Configure the Deployment Node

From a deployment node (controller01 works fine):

```bash
# Create the deployment user
sudo useradd -m -s /bin/bash kolla
echo "kolla ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/kolla

# Switch to the kolla user
sudo su - kolla

# Generate an SSH key
ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519

# Copy the key to every node
for host in controller{01..03} compute{01..02} storage{01..03}; do
  ssh-copy-id -i ~/.ssh/id_ed25519.pub kolla@$host
done

# Create a Python virtual environment
python3 -m venv ~/kolla-venv
source ~/kolla-venv/bin/activate

# Install Ansible and Kolla-Ansible
pip install -U pip
pip install 'ansible-core>=2.14,<2.16'
pip install 'kolla-ansible==17.0.0'  # OpenStack 2024.1 (Caracal)

# Install the required Ansible collections
kolla-ansible install-deps

# Create the configuration directory
sudo mkdir -p /etc/kolla
sudo chown kolla:kolla /etc/kolla

# Copy the base configuration files
cp -r ~/kolla-venv/share/kolla-ansible/etc_examples/kolla/* /etc/kolla
cp ~/kolla-venv/share/kolla-ansible/ansible/inventory/multinode /etc/kolla/
```

## 📝 Kolla-Ansible Configuration

### 1. Host Inventory

Edit `/etc/kolla/multinode`:

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

# Shared variables
[all:vars]
ansible_user=kolla
ansible_become=true
ansible_python_interpreter=/usr/bin/python3
```

### 2. Global Configuration

Edit `/etc/kolla/globals.yml`:

```yaml
---
# Basic configuration
kolla_base_distro: "ubuntu"
kolla_install_type: "source"
openstack_release: "2024.1"  # Caracal

# Networking
network_interface: "eno1"               # Management
api_interface: "eno2.20"                # Internal API
tunnel_interface: "eno2.30"             # Tunnels (VXLAN)
neutron_external_interface: "eno3"      # External (no IP assigned)
storage_interface: "eno4"               # Storage (optional)

kolla_internal_vip_address: "10.0.20.100"
kolla_external_vip_address: "192.168.100.100"

# Neutron
neutron_plugin_agent: "openvswitch"
neutron_extension_drivers:
  - name: "port_security"
  - name: "dns"

enable_neutron_provider_networks: "yes"

# Enabled services
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

# Ceph integration (if used)
enable_ceph: "no"  # Set to "yes" if you are deploying Ceph
glance_backend_ceph: "yes"
cinder_backend_ceph: "yes"
nova_backend_ceph: "yes"
ceph_nova_user: "cinder"
ceph_nova_keyring: "ceph.client.cinder.keyring"

# Monitoring
enable_prometheus: "yes"
enable_grafana: "yes"

# Logs
enable_central_logging: "yes"
enable_elasticsearch: "yes"
enable_kibana: "yes"

# Passwords
# NOTE: these are generated automatically by kolla-genpwd
```

### 3. Generate Passwords

```bash
kolla-genpwd
```

This creates `/etc/kolla/passwords.yml` with all the random passwords.

## 🚀 Deployment

### 1. Verify the Configuration

```bash
# Activate the venv if it is not already active
source ~/kolla-venv/bin/activate

# Check connectivity
ansible -i /etc/kolla/multinode all -m ping

# Check dependencies
kolla-ansible -i /etc/kolla/multinode bootstrap-servers
```

### 2. Precheck

```bash
kolla-ansible -i /etc/kolla/multinode prechecks
```

This validates:
- Network connectivity
- Software versions
- Disk space
- Docker configuration
- Required ports

### 3. Deploy

```bash
# Deploy OpenStack (20-40 minutes)
kolla-ansible -i /etc/kolla/multinode deploy

# Check the container status
docker ps -a

# Generate the credentials file
kolla-ansible -i /etc/kolla/multinode post-deploy

# Credentials are stored in:
cat /etc/kolla/admin-openrc.sh
```

### 4. Initialise OpenStack

```bash
# Load the credentials
source /etc/kolla/admin-openrc.sh

# Install the OpenStack client
pip install python-openstackclient

# Check the services
openstack service list
openstack endpoint list

# Create the initial resources
kolla-ansible -i /etc/kolla/multinode init-runonce
```

The `init-runonce` script creates:
- Basic flavors (m1.tiny, m1.small, m1.medium)
- A Cirros test image
- An external network and subnet
- A demo network
- Security groups with SSH/ICMP rules
- A test keypair

## ✅ Post-Deployment Verification

### 1. Check the Services

```bash
source /etc/kolla/admin-openrc.sh

# List the services
openstack service list

# Expected output:
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

# Check the compute hosts
openstack compute service list

# Check the network agents
openstack network agent list

# Check the hypervisors
openstack hypervisor list
```

### 2. Launch a Test Instance

```bash
# Create the instance
openstack server create \
  --flavor m1.small \
  --image cirros \
  --network demo-net \
  --key-name mykey \
  --security-group default \
  test-instance

# Check its status
openstack server list

# View the console log
openstack console log show test-instance

# Assign a Floating IP
FLOATING_IP=$(openstack floating ip create public1 -f value -c floating_ip_address)
openstack server add floating ip test-instance $FLOATING_IP

# Test connectivity
ping -c 4 $FLOATING_IP
ssh -i mykey.pem cirros@$FLOATING_IP
```

### 3. Access Horizon

```
URL: https://192.168.100.100
User: admin
Password: (see /etc/kolla/passwords.yml, keystone_admin_password)
```

## 🔍 Handy Operational Commands

### Container Management

```bash
# View the logs of a service
docker logs nova_compute

# Restart a service
docker restart nova_compute

# Run a command inside a container
docker exec -it nova_compute bash

# View resource usage
docker stats

# List all Kolla containers
docker ps --filter "label=kolla_version"
```

### Reconfiguration

```bash
# After modifying /etc/kolla/globals.yml
kolla-ansible -i /etc/kolla/multinode reconfigure

# Update a single service
kolla-ansible -i /etc/kolla/multinode reconfigure --tags nova
```

### Upgrades

```bash
# Update Kolla-Ansible
pip install --upgrade kolla-ansible

# Upgrade OpenStack
kolla-ansible -i /etc/kolla/multinode prechecks
kolla-ansible -i /etc/kolla/multinode pull  # Pull the new images
kolla-ansible -i /etc/kolla/multinode upgrade
```

## 🛡️ Post-Deployment Security

### 1. Change the Default Passwords

```bash
# Edit /etc/kolla/passwords.yml manually
# Or regenerate specific passwords:
sed -i 's/keystone_admin_password:.*/keystone_admin_password: NewPassword123/' /etc/kolla/passwords.yml

# Apply the changes
kolla-ansible -i /etc/kolla/multinode reconfigure --tags keystone
```

### 2. Configure the Firewall

```bash
# Allow only what is needed
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

### 3. TLS/SSL for the APIs

Edit `/etc/kolla/globals.yml`:

```yaml
kolla_enable_tls_external: "yes"
kolla_external_fqdn: "cloud.example.com"
kolla_external_fqdn_cert: "/etc/kolla/certificates/cloud.example.com.crt"
kolla_external_fqdn_key: "/etc/kolla/certificates/cloud.example.com.key"
```

Copy the certificates:

```bash
sudo mkdir -p /etc/kolla/certificates
sudo cp /path/to/cert.crt /etc/kolla/certificates/cloud.example.com.crt
sudo cp /path/to/cert.key /etc/kolla/certificates/cloud.example.com.key

kolla-ansible -i /etc/kolla/multinode reconfigure
```

## 📊 Monitoring

### Access Grafana

```
URL: http://10.0.20.100:3000
User: admin
Password: (see /etc/kolla/passwords.yml, grafana_admin_password)
```

Preconfigured dashboards:
- OpenStack Overview
- Nova Compute Metrics
- Neutron Network Stats
- Cinder Volume Stats

### Centralised Logs (Kibana)

```
URL: http://10.0.20.100:5601
```

## 📚 Additional Resources

- [Kolla-Ansible Docs](https://docs.openstack.org/kolla-ansible/latest/)
- [OpenStack Install Guide](https://docs.openstack.org/install-guide/)
- [Kolla-Ansible GitHub](https://github.com/openstack/kolla-ansible)

## 🎓 Next Steps

1. **Integrate Ceph**: See [OpenStack + Ceph Integration](openstack_ceph_integration.md)
2. **Day-2 Operations**: See [Day-2 Operations](day2.md)
3. **Troubleshooting**: See [Troubleshooting](troubleshooting_openstack.md)

---

!!! tip "Running into trouble during the deployment?"
    Check the logs with `docker logs <container>` and take a look at our [troubleshooting guide](troubleshooting_openstack.md).

!!! warning "High Availability"
    This guide covers basic HA. For advanced setups (Pacemaker, active-active), see the [official HA documentation](https://docs.openstack.org/ha-guide/).
