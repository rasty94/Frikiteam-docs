# Proxmox VE

Complete guide to Proxmox Virtual Environment: enterprise-grade open-source virtualization platform.

## 📋 Table of Contents

- [Introduction](#introduction)
- [Installation](#installation)
- [Basic Configuration](#basic-configuration)
- [Virtual Machine Management](#virtual-machine-management)
- [LXC Containers](#lxc-containers)
- [Storage](#storage)
- [Networking](#networking)
- [Backup and Recovery](#backup-and-recovery)
- [Clustering](#clustering)
- [Security](#security)
- [Monitoring](#monitoring)
- [Use Cases](#use-cases)
- [Useful Tools](#useful-tools)
- [References](#references)

## Introduction

Proxmox Virtual Environment (Proxmox VE) is an enterprise-grade open-source virtualization platform that combines:

- **Virtual machine virtualization** (KVM/QEMU)
- **LXC containers** for lightweight applications
- **Unified web management** with intuitive interface
- **Distributed storage** with multiple options
- **Clustering** for high availability
- **Integrated backup** with multiple destinations

### Key Features

- **Open source**: Based on Debian GNU/Linux
- **High performance**: KVM for hardware virtualization
- **Scalability**: Native clustering for multiple nodes
- **Flexibility**: Support for multiple storage types
- **Security**: Isolated LXC containers
- **Monitoring**: Real-time metrics

## Installation

### System Requirements

- **CPU**: 64-bit with virtualization support (Intel VT-x/AMD-V)
- **RAM**: Minimum 4GB, recommended 8GB+
- **Storage**: Minimum 32GB, recommended 100GB+
- **Network**: Configured network interface

### Installation from ISO

1. **Download ISO** from [proxmox.com](https://www.proxmox.com/en/downloads)
2. **Create bootable USB** or use PXE
3. **Boot** from installation media
4. **Follow** the installation wizard

```bash
# Example of automated installation
# Create configuration file for unattended installation
cat > /tmp/proxmox-ve.conf << EOF
# Network configuration
interface=eth0
ip=192.168.1.100/24
gateway=192.168.1.1
dns=8.8.8.8

# Storage configuration
target=sda
filesystem=ext4

# User configuration
password=YourSecurePassword
email=admin@yourdomain.com
EOF
```

### Installation on Debian

```bash
# Add Proxmox repository
echo "deb http://download.proxmox.com/debian/pve bullseye pve-no-subscription" > /etc/apt/sources.list.d/pve-install-repo.list

# Add GPG key
wget https://enterprise.proxmox.com/debian/proxmox-release-bullseye.gpg -O /etc/apt/trusted.gpg.d/proxmox-release-bullseye.gpg

# Update and install
apt update
apt install proxmox-ve postfix open-iscsi
```

## Basic Configuration

### Web Interface Access

```bash
# Access URL
https://SERVER-IP:8006

# Default credentials
Username: root
Password: (configured during installation)
```

### Network Configuration

```bash
# Edit network configuration
nano /etc/network/interfaces

# Example configuration
auto lo
iface lo inet loopback

auto vmbr0
iface vmbr0 inet static
    address 192.168.1.100/24
    gateway 192.168.1.1
    bridge-ports eth0
    bridge-stp off
    bridge-fd 0
```

### DNS Configuration

```bash
# Edit resolv.conf
nano /etc/resolv.conf

# Add DNS servers
nameserver 8.8.8.8
nameserver 8.8.4.4
```

## Virtual Machine Management

### Create VM from Web Interface

1. **Navigate** to Datacenter → Node → Create VM
2. **Configure** basic parameters:
   - **General**: Name, ID, OS Type
   - **OS**: ISO image, OS version
   - **System**: SCSI controller, Qemu agent
   - **Hard Disk**: Size, storage location
   - **CPU**: Sockets, cores
   - **Memory**: RAM allocation
   - **Network**: Bridge, model

### Create VM from Command Line

```bash
# Create VM with ID 100
qm create 100 --name "Ubuntu-Server" --memory 2048 --cores 2

# Add disk
qm set 100 --scsi0 local-lvm:32

# Add ISO
qm set 100 --ide2 local:iso/ubuntu-22.04-server-amd64.iso,media=cdrom

# Configure boot
qm set 100 --boot c --bootdisk scsi0

# Configure network
qm set 100 --net0 virtio,bridge=vmbr0

# Start VM
qm start 100
```

### Advanced VM Management

```bash
# Clone VM
qm clone 100 101 --name "Ubuntu-Server-Clone"

# Migrate VM
qm migrate 100 target-node --online

# Snapshot
qm snapshot 100 snap1

# Backup
qm backup 100 local:backup

# Monitor
qm monitor 100
```

## LXC Containers

### Create Container

```bash
# Create Ubuntu container
pct create 200 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.gz \
  --hostname ubuntu-ct \
  --memory 512 \
  --cores 1 \
  --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.200/24,gw=192.168.1.1

# Start container
pct start 200

# Access container
pct enter 200
```

### Container Management

```bash
# List containers
pct list

# Stop container
pct stop 200

# Restart container
pct restart 200

# Clone container
pct clone 200 201

# Backup
pct backup 200 local:backup
```

## Storage

### Storage Types

- **local**: Local storage on the node
- **local-lvm**: LVM for VMs and containers
- **NFS**: Network file system
- **Ceph**: Distributed storage
- **iSCSI**: Network block storage
- **ZFS**: Advanced file system

### Configure NFS

```bash
# Add NFS storage
pvesm add nfs nfs-storage --server 192.168.1.10 --export /mnt/storage --content images,iso,vztmpl
```

### Configure Ceph

```bash
# Install Ceph
apt install ceph

# Create Ceph cluster
ceph-deploy new node1 node2 node3

# Add OSDs
ceph-deploy osd create node1:/dev/sdb
ceph-deploy osd create node2:/dev/sdb
ceph-deploy osd create node3:/dev/sdb

# Add Ceph storage to Proxmox
pvesm add ceph ceph-storage --monhost 192.168.1.10,192.168.1.11,192.168.1.12 --username admin
```

## Networking

### Bridge Configuration

```bash
# Simple bridge
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.100/24
    gateway 192.168.1.1
    bridge-ports eth0
    bridge-stp off
    bridge-fd 0
```

### VLAN

```bash
# Bridge with VLAN
auto vmbr0.100
iface vmbr0.100 inet static
    address 192.168.100.100/24
    vlan-raw-device vmbr0
```

### Bonding

```bash
# Bond of two interfaces
auto bond0
iface bond0 inet manual
    bond-slaves eth0 eth1
    bond-mode 802.3ad
    bond-miimon 100

auto vmbr0
iface vmbr0 inet static
    address 192.168.1.100/24
    gateway 192.168.1.1
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
```

## Backup and Recovery

### Configure Backup

```bash
# Configure backup job
nano /etc/pve/nodes/node/backup.conf

# Example configuration
backup: local:backup
compress: lz4
mode: snapshot
retention: 7
schedule: daily 02:00
storage: local:backup
```

### Manual Backup

```bash
# VM backup
qm backup 100 local:backup --compress lz4

# Container backup
pct backup 200 local:backup --compress lz4

# Restore backup
qm restore 100 /var/lib/vz/dump/vzdump-qemu-100-2023_01_01-02_00_00.vma.lz4
pct restore 200 /var/lib/vz/dump/vzdump-lxc-200-2023_01_01-02_00_00.tar.lz4
```

## Clustering

### Create Cluster

```bash
# On first node
pvecm create cluster1

# On additional nodes
pvecm add 192.168.1.100
```

### Cluster Management

```bash
# View cluster status
pvecm status

# Migrate VM between nodes
qm migrate 100 node2 --online

# Configure HA (High Availability)
ha-manager add vm:100
ha-manager add ct:200
```

## Security

### Firewall Configuration

```bash
# Enable firewall
pve-firewall set --enable 1

# Node rules
pve-firewall set --policy-in ACCEPT
pve-firewall set --policy-out ACCEPT

# VM rules
qm set 100 --firewall 1
pve-firewall set --rulegroup vm:100 --policy-in ACCEPT
```

### SSL Certificates

```bash
# Generate self-signed certificate
pvecm updatecerts --force

# Configure Let's Encrypt certificate
apt install certbot
certbot certonly --standalone -d proxmox.yourdomain.com
```

## Monitoring

### System Metrics

```bash
# View resource usage
pvesm status
qm list
pct list

# Network monitoring
iftop -i vmbr0
```

### Logs

```bash
# System logs
tail -f /var/log/syslog

# Proxmox logs
tail -f /var/log/pve/tasks/

# VM logs
tail -f /var/log/pve/qemu-server/100.log
```

## Use Cases

### Development Environment

```bash
# Create development VM
qm create 300 --name "Dev-Ubuntu" --memory 4096 --cores 4
qm set 300 --scsi0 local-lvm:50
qm set 300 --net0 virtio,bridge=vmbr0
qm set 300 --ide2 local:iso/ubuntu-22.04-desktop-amd64.iso,media=cdrom
```

### Web Server

```bash
# Create container for web
pct create 400 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.gz \
  --hostname webserver \
  --memory 1024 \
  --cores 2 \
  --rootfs local-lvm:20 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.10/24,gw=192.168.1.1
```

### Database Server

```bash
# VM for database
qm create 500 --name "DB-Server" --memory 8192 --cores 4
qm set 500 --scsi0 local-lvm:100
qm set 500 --scsi1 local-lvm:200  # Additional disk for data
qm set 500 --net0 virtio,bridge=vmbr0
```

## Best Practices

- ✅ **Use snapshots** before important changes
- ✅ **Configure automatic backups** regularly
- ✅ **Monitor system resources**
- ✅ **Use LXC containers** for lightweight applications
- ✅ **Configure HA** for critical services
- ✅ **Keep system updated**
- ✅ **Document important configurations**
- ✅ **Use VLANs** to separate networks

## Useful Tools

### ProxMenuX

ProxMenuX is an advanced management tool for Proxmox VE that provides an enhanced graphical interface and additional functionalities.

**Main features:**
- Enhanced web interface with better UX/UI
- Advanced VM and container management
- Real-time monitoring with graphs
- Simplified backup and restore
- User and permission management
- Integration with multiple storage types

**Installation:**
```bash
# Clone repository
git clone https://github.com/ayufan/proxmox-ve-helper.git
cd proxmox-ve-helper

# Install dependencies
npm install

# Configure and run
npm run build
npm start
```

### Proxmox VE Helper

Proxmox VE Helper is a collection of scripts and tools to automate common tasks in Proxmox VE.

**Functionalities:**
- Automation scripts for backup
- VM migration tools
- Monitoring and alerting utilities
- Network configuration scripts
- Cluster maintenance tools

**Installation:**
```bash
# Download scripts
wget https://github.com/ayufan/proxmox-ve-helper/archive/refs/heads/master.zip
unzip master.zip
cd proxmox-ve-helper-master

# Give execution permissions
chmod +x scripts/*.sh

# Run installation script
./scripts/install.sh
```

**Usage examples:**
```bash
# Automatic backup of all VMs
./scripts/backup-all-vms.sh

# VM migration with verification
./scripts/migrate-vm.sh 100 target-node

# Resource monitoring
./scripts/monitor-resources.sh
```

### Other Recommended Tools

- **Proxmox Backup Server**: Dedicated backup solution
- **Cockpit**: Web interface for server management
- **Grafana**: Advanced monitoring dashboards
- **Prometheus**: Monitoring and alerting system
- **Ansible**: Configuration automation

## References

- **Official documentation**: https://pve.proxmox.com/wiki/Documentation
- **Proxmox Wiki**: https://pve.proxmox.com/wiki/Main_Page
- **Community forum**: https://forum.proxmox.com/
- **Git repository**: https://git.proxmox.com/
- **Downloads**: https://www.proxmox.com/en/downloads
- **ProxMenuX**: https://github.com/ayufan/proxmox-ve-helper
- **Proxmox VE Helper**: https://github.com/ayufan/proxmox-ve-helper

