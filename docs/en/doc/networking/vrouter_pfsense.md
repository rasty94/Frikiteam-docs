# pfSense (virtual router/firewall)

pfSense is a mature and stable platform, especially useful for teams that value predictable operations.

## When to choose pfSense

- You need high operational stability
- Your team prefers traditional GUI-driven workflows
- You want clear firewall and NAT policy management

## Recommended deployment (traditional production)

- 2-3 vNICs:
  - WAN
  - LAN
  - Optional DMZ
- CPU: 2-4 vCPU, RAM: 4 GB recommended
- Disk: 16-32 GB

## Baseline setup

1. Assign interfaces and gateways.
2. Build network aliases for cleaner policy definitions.
3. Apply zone-based firewall rules (LAN/DMZ/WAN).
4. Keep outbound NAT and port forwards minimal.
5. Enable NTP, DNS Resolver and regular backups.

## Good practices

- Prefer aliases over one-off IP rules.
- Label rules by service/owner for auditing.
- Validate changes during maintenance windows.
- Monitor firewall states and resource usage.

## Operational checklist

- Is WAN closed by default?
- Do LAN/DMZ policies follow least privilege?
- Is backup/restore fully validated?
- Does the team have a clear outage runbook?
