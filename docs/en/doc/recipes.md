---
title: "Quick Recipes"
description: "Documentation on quick recipes"
tags: ['documentation']
updated: 2026-01-25
difficulty: intermediate
estimated_time: 2 min
category: General
status: published
last_reviewed: 2026-01-25
prerequisites: ["Basic DevOps knowledge"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Quick Recipes

Welcome to the **Quick Recipes** section. Here you will find fast solutions and copy-paste commands for common problems across the technologies we cover.

## Ansible

### Run a playbook with a specific inventory

```bash
ansible-playbook -i inventory.ini playbook.yml
```

### Check connectivity with hosts

```bash
ansible all -m ping
```

## Docker

### Clean up unused containers and images

```bash
docker system prune -a
```

### View a container's logs

```bash
docker logs <container_name>
```

## Kubernetes

### List pods across all namespaces

```bash
kubectl get pods --all-namespaces
```

### Apply a YAML manifest

```bash
kubectl apply -f deployment.yaml
```

## HAProxy

### Reload the configuration with no downtime

```bash
sudo systemctl reload haproxy
```

### View real-time statistics

```bash
echo "show stat" | socat stdio /var/run/haproxy.sock
```

## Networking

### Show the routing table

```bash
ip route show
```

### Show network interfaces

```bash
ip addr show
```

## Proxmox

### Update the system

```bash
apt update && apt upgrade
```

### Create a VM from the CLI

```bash
qm create 100 --name myvm --memory 2048 --net0 virtio,bridge=vmbr0
```

## OpenStack

### List instances

```bash
openstack server list
```

### Create a network

```bash
openstack network create mynetwork
```

## Terraform

### Initialize a directory

```bash
terraform init
```

### Plan changes

```bash
terraform plan
```

## Ceph

### Check cluster health

```bash
ceph status
```

### List OSDs

```bash
ceph osd tree
```

!!! tip "Contribute"
    If you have a quick recipe you think would be useful, send a PR or open an issue in our [repository](https://github.com/rasty94/Frikiteam-docs)!

## Links to full guides

For detailed explanations and complete guides, see:

- **[Ansible Base](ansible/ansible_base.md)** - Complete Ansible guide
- **[Docker Base](docker/docker_base.md)** - Complete Docker guide
- **[Kubernetes Base](kubernetes/kubernetes_base.md)** - Complete Kubernetes guide
- **[HAProxy Base](haproxy/haproxy_base.md)** - Complete HAProxy guide
- **[Networking](networking/index.md)** - Networking guides
- **[Proxmox VE](proxmox/proxmox_base.md)** - Complete Proxmox guide
- **[OpenStack](openstack/openstack_base.md)** - Complete OpenStack guide
- **[Terraform Base](terraform/terraform_base.md)** - Complete Terraform guide
- **[Ceph Base](storage/ceph/ceph_base.md)** - Complete Ceph guide

Need help with troubleshooting? Check out our **[troubleshooting section](../troubleshooting.md)**.
