# Install Proxmox VE 9 on Debian 13 (Trixie)

> This guide describes how to install Proxmox VE 9.x on a minimal Debian 13 (Trixie) installation. It is oriented towards home and lab environments. For production, follow the official Proxmox documentation.

## Prerequisites

- **Base system**: Debian 13 minimal (amd64) with network and sudo access
- **Hostname** configured (FQDN recommended)
- **Updates applied** and reboot if kernel requires it
- **Root access** or user with sudo

## 1) Prepare the system

Update the system and essential packages:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y curl gnupg lsb-release ca-certificates apt-transport-https
```

Configure the hostname and `/etc/hosts` (adjust `pve01` and the domain):

```bash
echo "pve01.example.lan" | sudo tee /etc/hostname
sudo hostnamectl set-hostname pve01.example.lan
cat <<'EOF' | sudo tee -a /etc/hosts
# Proxmox
192.168.1.10  pve01.example.lan pve01
EOF
```

Disable `swap` (Proxmox recommends it for performance):

```bash
sudo swapoff -a
sudo sed -i.bak '/\sswap\s/s/^/#/' /etc/fstab
```

Configure timezone and NTP:

```bash
sudo timedatectl set-timezone Europe/Madrid
sudo apt install -y systemd-timesyncd && sudo timedatectl set-ntp true
```

## 2) Proxmox Repositories

Add the `pve-no-subscription` repository (suitable for lab) for Proxmox 9 on Debian 13 (trixie):

```bash
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://enterprise.proxmox.com/debian/proxmox-release-trixie.gpg | sudo tee /etc/apt/keyrings/proxmox-release.gpg > /dev/null

echo "deb [signed-by=/etc/apt/keyrings/proxmox-release.gpg] http://download.proxmox.com/debian/pve trixie pve-no-subscription" | sudo tee /etc/apt/sources.list.d/pve-no-subscription.list
```

## 3) Install Proxmox VE

Update indexes and install:

```bash
sudo apt update
sudo apt install -y proxmox-ve postfix open-iscsi
```

- Select `No configuration` in Postfix if you won't send mail from the host.
- The installer may remove `os-prober` and other packages; accept if requested.

After installation, reboot:

```bash
sudo reboot
```

## 4) First Web UI Access

Access via browser at:

- https://pve01.example.lan:8006
- User: `root`
- Authentication: `PAM` (default)

If a subscription notice appears, you can hide it by installing the community alternative package or leave the notice (recommended to leave as is in lab).

## 5) Recommended Settings

- Update the system from `Shell` or the UI.
- Configure `Datacenter → Storage` according to your disks (LVM-Thin, ZFS, NFS, CIFS).
- Enable `open-iscsi` at boot:

```bash
sudo systemctl enable --now iscsid
```

- If using ZFS, adjust ARC if RAM is limited:

```bash
echo "options zfs zfs_arc_max=$((4*1024*1024*1024))" | sudo tee /etc/modprobe.d/zfs.conf
sudo update-initramfs -u
```

- Create network bridges (`vmbr0`) if not created automatically. Example (systemd-networkd):

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

### Possible failures or necessary changes (ifupdown: /etc/network/interfaces)

In Proxmox it's common to manage networking with `ifupdown`, editing `/etc/network/interfaces`. If your system doesn't use `systemd-networkd` or you prefer the classic method, these examples will serve you.

- Make sure to include the line for `interfaces.d` directory (optional):

```bash
sudo mkdir -p /etc/network/interfaces.d
printf "source /etc/network/interfaces.d/*\n" | sudo tee -a /etc/network/interfaces >/dev/null
```

- Example 1: physical interface in manual mode + `vmbr0` bridge with static IP:

```text
auto lo
iface lo inet loopback

# Physical interface without IP; IP goes in the bridge
auto eno1
iface eno1 inet manual

# Main bridge for VMs/CTs
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.10/24
    gateway 192.168.1.1
    bridge-ports eno1
    bridge-stp off
    bridge-fd 0
```

- Example 2: 802.3ad bonding (LACP) over two NICs and bridge on top:

```text
# LACP Bond
auto bond0
iface bond0 inet manual
    bond-slaves eno1 eno2
    bond-miimon 100
    bond-mode 802.3ad
    bond-xmit-hash-policy layer3+4
    lacp-rate 1

# Bridge with IP over the bond
auto vmbr0
iface vmbr0 inet static
    address 192.168.1.10/24
    gateway 192.168.1.1
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
```

- Optional: VLAN-aware bridge (management without IP or with IP in a VLAN):

```text
# VLAN-aware bridge (no IP)
auto vmbr0
iface vmbr0 inet manual
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes

# VLAN interface for management (e.g. VLAN 10)
auto vmbr0.10
iface vmbr0.10 inet static
    address 192.168.10.10/24
    gateway 192.168.10.1
```

- Network reload and utilities:

```bash
sudo ifreload -a || sudo systemctl restart networking
ip -br a
bridge link
```

- Troubleshooting tips:

- Verify interface names (e.g. `ip -br a`), they may vary (`ens18`, `enp3s0`, etc.)
- Check that there are no two simultaneous gateways or active DHCP on the same network
- If using LACP, configure the switch port as LAG/802.3ad and ensure all bond members match
- Avoid conflicts with NetworkManager: disable it if it manages the same NICs (`systemctl disable --now NetworkManager`)

## 6) Enterprise Repository Cleanup (optional)

To avoid Enterprise repo notices without subscription:

```bash
sudo sed -i.bak 's/^deb /# deb /' /etc/apt/sources.list.d/pve-enterprise.list || true
sudo apt update
```

## 7) Backup and snapshots

- Configure `Datacenter → Backup` with local or remote storage
- Test a manual `backup` and restoration of a test VM
- Enable `Guest Agent` in VMs for better integrations

## 8) Useful CLI

```bash
# Cluster and services status
pveversion -v
systemctl status pvedaemon pve-cluster pveproxy

# Disks and ZFS
lsblk
zpool status

# Networks
ip -br a
bridge link

# Manage repos
proxmox-backup-manager datastore list || true
```

## 9) References

- Official documentation: https://pve.proxmox.com/wiki/Main_Page
- Proxmox repos: https://enterprise.proxmox.com/debian/pve
- Proxmox 9 on Debian guide: https://pve.proxmox.com/wiki/Install_Proxmox_VE_on_Debian_13_Trixie
