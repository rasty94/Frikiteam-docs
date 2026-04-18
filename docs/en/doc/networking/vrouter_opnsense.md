# OPNsense (virtual router/firewall)

OPNsense is a strong choice when you prioritize firewalling, segmentation and day-to-day operations through a clear web UI.

## When to choose OPNsense

- You need a full GUI for daily operations
- You want robust firewalling with auditable rules
- You want a good balance between usability and enterprise features

## Recommended deployment (homelab/edge)

- At least 2 vNICs:
  - WAN (uplink)
  - LAN (internal network)
- CPU: 2 vCPU minimum, RAM: 2-4 GB
- Disk: 16 GB+

## Baseline setup

1. Assign WAN/LAN interfaces correctly.
2. Replace default credentials and enable MFA where possible.
3. Define LAN addressing and DHCP scope.
4. Keep WAN on deny-by-default policy.
5. Add explicit service and source-based rules.

## Good practices

- Use VLAN segmentation when possible.
- Export config backups before critical changes.
- Keep firmware/plugins updated in maintenance windows.
- Enable firewall logging and review deny patterns.

## Operational checklist

- Are WAN and LAN mapped to different interfaces with no overlap?
- Is config backup and restore tested?
- Are latency, packet loss and session counters monitored?
- Is there a rollback procedure?
