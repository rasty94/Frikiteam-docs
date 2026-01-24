# Upgrade Proxmox VE 8 to Proxmox VE 9 (Debian 13 Trixie)

> Practical guide to upgrade a node or cluster from Proxmox VE 8 (Debian 12) to Proxmox VE 9 (Debian 13). Recommended to test first in lab or have backups and maintenance window.

## 1) Pre-upgrade Checklist (essential)

- **Complete backup** of VMs/CTs and configuration (`/etc/pve`, `/etc/network/interfaces`, storage, etc.)
- **Cluster health OK**: `pvecm status`, `systemctl status pve*`, `journalctl -p err -b`
- **Free space** sufficient (min. 5-10 GB in `/` and `/var`)
- **Clean repositories**: no broken external repos, enterprise commented if no subscription
- **Kernel and packages updated** in PVE 8: `apt update && apt full-upgrade -y` and reboot
- **CPU/BIOS/firmware versions** up to date if applicable (especially for ZFS)
- **Maintenance window**: planned; service interruption likely

## 2) Preparation in PVE 8 (Bookworm)

Make sure you're fully up to date in PVE 8:

```bash
apt update && apt full-upgrade -y
reboot
```

Disable enterprise repos if you don't have subscription:

```bash
sed -i.bak 's/^deb /# deb /' /etc/apt/sources.list.d/pve-enterprise.list || true
apt update
```

## 3) Switch to Proxmox 9 repos (Trixie)

Create keyring and `trixie` repos:

```bash
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://enterprise.proxmox.com/debian/proxmox-release-trixie.gpg > /etc/apt/keyrings/proxmox-release.gpg

cat >/etc/apt/sources.list.d/pve-no-subscription.list <<'EOF'
deb [signed-by=/etc/apt/keyrings/proxmox-release.gpg] http://download.proxmox.com/debian/pve trixie pve-no-subscription
EOF
```

Adjust other repos to `trixie` (Debian base):

```bash
sed -ri 's/bookworm/trixie/g' /etc/apt/sources.list
```

Review files in `/etc/apt/sources.list.d/` and remove/adjust old entries.

## 4) Perform the major upgrade

Update indexes and perform dist-upgrade:

```bash
apt update
apt dist-upgrade -y
```

Resolve configuration prompts if they appear (keep local files unless you know otherwise). When finished, reboot:

```bash
reboot
```

Verify version after reboot:

```bash
pveversion -v
cat /etc/os-release | grep PRETTY_NAME
```

## 5) Post-upgrade validations

- UI at `https://<host>:8006` functional and without errors
- Services OK:

```bash
systemctl status pvedaemon pve-cluster pveproxy
journalctl -p err -b | tail -n +1
```

- Network operational; if using `ifupdown`, confirm `/etc/network/interfaces` and bridges/bonds
- Storages mounted and accessible (LVM, ZFS, NFS, CIFS)
- ZFS healthy:

```bash
zpool status
```

- Scheduled backups active and tested

## 6) Notes and common changes in PVE 9

- Base Debian 13 (trixie), newer packages and kernels
- Possible changes in network/storage drivers; verify interface names
- If using `networkd` vs `ifupdown`, make sure to use only one network stack
- Enterprise repo may come enabled; comment if you don't have subscription

## 7) Rollback (options and warnings)

No supported automatic rollback exists between major versions. Options:

- Restore from complete system backup (host image or snapshot)
- Reinstall PVE 8 and restore VM/CT backups
- If network fails, maintain physical access to correct `/etc/network/interfaces`

## 8) Useful commands

```bash
# Simulate before (optional)
apt -o APT::Get::Trivial-Only=true dist-upgrade

# See held packages
apt-mark showhold || true

# Clean obsolete packages
autoremove --purge -y || true
apt clean
```

## 9) References

- Official PVE 9 upgrade: https://pve.proxmox.com/wiki/Upgrade_from_8_to_9
- Release notes: https://pve.proxmox.com/wiki/Roadmap
- Debian 13 repos: https://www.debian.org/releases/trixie/
