---
title: "Instalar Proxmox VE 9 sobre Debian 13 (Trixie)"
description: "Documentación sobre instalar proxmox ve 9 sobre debian 13 (trixie)"
tags: ['documentation']
updated: 2026-01-25
difficulty: advanced
estimated_time: 5 min
category: General
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Instalar Proxmox VE 9 sobre Debian 13 (Trixie)

> Esta guía describe cómo instalar Proxmox VE 9.x sobre una instalación mínima de Debian 13 (Trixie). Está orientada a entornos caseros y de laboratorio. Para producción, sigue la documentación oficial de Proxmox.

## Requisitos previos

- **Sistema base**: Debian 13 minimal (amd64) con red y acceso sudo
- **Nombre de host** configurado (FQDN recomendado)
- **Actualizaciones aplicadas** y reinicio si el kernel lo requiere
- **Acceso root** o usuario con sudo

## 1) Preparar el sistema

Actualiza el sistema y paquetes esenciales:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y curl gnupg lsb-release ca-certificates apt-transport-https
```

Configura el hostname y `/etc/hosts` (ajusta `pve01` y el dominio):

```bash
echo "pve01.example.lan" | sudo tee /etc/hostname
sudo hostnamectl set-hostname pve01.example.lan
cat <<'EOF' | sudo tee -a /etc/hosts
# Proxmox
192.168.1.10  pve01.example.lan pve01
EOF
```

Deshabilita `swap` (Proxmox lo recomienda para rendimiento):

```bash
sudo swapoff -a
sudo sed -i.bak '/\sswap\s/s/^/#/' /etc/fstab
```

Configura la zona horaria y NTP:

```bash
sudo timedatectl set-timezone Europe/Madrid
sudo apt install -y systemd-timesyncd && sudo timedatectl set-ntp true
```

## 2) Repositorios Proxmox

Añade el repositorio `pve-no-subscription` (adecuado para lab) para Proxmox 9 en Debian 13 (trixie):

```bash
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://enterprise.proxmox.com/debian/proxmox-release-trixie.gpg | sudo tee /etc/apt/keyrings/proxmox-release.gpg > /dev/null

echo "deb [signed-by=/etc/apt/keyrings/proxmox-release.gpg] http://download.proxmox.com/debian/pve trixie pve-no-subscription" | sudo tee /etc/apt/sources.list.d/pve-no-subscription.list
```

## 3) Instalar Proxmox VE

Actualiza índices e instala:

```bash
sudo apt update
sudo apt install -y proxmox-ve postfix open-iscsi
```

- Selecciona `No configuration` en Postfix si no enviarás correo desde el host.
- El instalador puede eliminar `os-prober` y otros paquetes; acepta si es solicitado.

Tras la instalación, reinicia:

```bash
sudo reboot
```

## 4) Primer acceso Web UI

Accede vía navegador a:

- https://pve01.example.lan:8006
- Usuario: `root`
- Autenticación: `PAM` (por defecto)

Si aparece un aviso de suscripción, puedes ocultarlo instalando el paquete alternativo de la comunidad o dejando el aviso (recomendado dejarlo tal cual en lab).

## 5) Ajustes recomendados

- Actualiza el sistema desde `Shell` o la UI.
- Configura `Datacenter → Storage` según tus discos (LVM-Thin, ZFS, NFS, CIFS).
- Habilita `open-iscsi` al arranque:

```bash
sudo systemctl enable --now iscsid
```

- Si usas ZFS, ajusta ARC si la RAM es limitada:

```bash
echo "options zfs zfs_arc_max=$((4*1024*1024*1024))" | sudo tee /etc/modprobe.d/zfs.conf
sudo update-initramfs -u
```

- Crea puentes de red (`vmbr0`) si no fueron creados automáticamente. Ejemplo (systemd-networkd):

```bash
cat <<'EOF' | sudo tee /etc/systemd/network/10-ens18.network
[Match]
Name=ens18

[Network]
Bridge=vmbr0
EOF

cat <<'EOF' | sudo tee /etc/systemd/network/20-vmbr0.netdev
[NetDev]
Name=vmbr0
Kind=bridge
EOF

cat <<'EOF' | sudo tee /etc/systemd/network/21-vmbr0.network
[Match]
Name=vmbr0

[Network]
Address=192.168.1.10/24
Gateway=192.168.1.1
DNS=1.1.1.1 8.8.8.8
EOF

sudo systemctl restart systemd-networkd
```

### Posibles fallos o cambios necesarios (ifupdown: /etc/network/interfaces)

En Proxmox es habitual gestionar la red con `ifupdown`, editando `/etc/network/interfaces`. Si tu sistema no usa `systemd-networkd` o prefieres el método clásico, estos ejemplos te servirán.

- Asegúrate de tener incluida la línea para directorio de `interfaces.d` (opcional):

```bash
sudo mkdir -p /etc/network/interfaces.d
printf "source /etc/network/interfaces.d/*\n" | sudo tee -a /etc/network/interfaces >/dev/null
```

- Ejemplo 1: interfaz física en modo manual + puente `vmbr0` con IP estática:

```text
auto lo
iface lo inet loopback

# Interfaz física sin IP; la IP va en el bridge
auto eno1
iface eno1 inet manual

# Bridge principal para VMs/CTs
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.10/24
    gateway 192.168.1.1
    bridge-ports eno1
    bridge-stp off
    bridge-fd 0
```

- Ejemplo 2: bonding 802.3ad (LACP) sobre dos NICs y bridge encima:

```text
# Bond LACP
auto bond0
iface bond0 inet manual
    bond-slaves eno1 eno2
    bond-miimon 100
    bond-mode 802.3ad
    bond-xmit-hash-policy layer3+4
    lacp-rate 1

# Bridge con IP sobre el bond
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.10/24
    gateway 192.168.1.1
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
```

- Opcional: bridge consciente de VLANs (gestión sin IP o con IP en una VLAN):

```text
# Bridge VLAN-aware (sin IP)
auto vmbr0
iface vmbr0 inet manual
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes

# Interfaz VLAN para la gestión (ej. VLAN 10)
auto vmbr0.10
iface vmbr0.10 inet static
    address 192.168.10.10/24
    gateway 192.168.10.1
```

- Recarga de red y utilidades:

```bash
sudo ifreload -a || sudo systemctl restart networking
ip -br a
bridge link
```

- Consejos de resolución de problemas:

- Verifica nombres de interfaz (ej. `ip -br a`), pueden variar (`ens18`, `enp3s0`, etc.)
- Comprueba que no haya dos puertas de enlace simultáneas o DHCP activo en la misma red
- Si usas LACP, configura el puerto del switch como LAG/802.3ad y que todos los miembros del bond coincidan
- Evita conflictos con NetworkManager: deshabilítalo si gestiona las mismas NICs (`systemctl disable --now NetworkManager`)

## 6) Limpieza del repositorio enterprise (opcional)

Para evitar avisos de repos Enterprise sin suscripción:

```bash
sudo sed -i.bak 's/^deb /# deb /' /etc/apt/sources.list.d/pve-enterprise.list || true
sudo apt update
```

## 7) Backup y snapshots

- Configura `Datacenter → Backup` con almacenamiento local o remoto
- Prueba un `backup` manual y la restauración de una VM de prueba
- Habilita `Guest Agent` en VMs para mejores integraciones

## 8) CLI útil

```bash
# Estado de clúster y servicios
pveversion -v
systemctl status pvedaemon pve-cluster pveproxy

# Discos y ZFS
lsblk
zpool status

# Redes
ip -br a
bridge link

# Gestionar repos
proxmox-backup-manager datastore list || true
```

## 9) Referencias

- Documentación oficial: https://pve.proxmox.com/wiki/Main_Page
- Repos Proxmox: https://enterprise.proxmox.com/debian/pve
- Guía Proxmox 9 en Debian: https://pve.proxmox.com/wiki/Install_Proxmox_VE_on_Debian_13_Trixie
