# MikroTik CHR (Cloud Hosted Router)

MikroTik CHR is a strong fit when you need high-performance L3 routing with a tight cost envelope.

## When to choose MikroTik CHR

- ISP/WISP scenarios or carrier-style labs
- Advanced routing policy requirements
- Teams comfortable with RouterOS operations

## Recommended deployment

- 2-4 vNICs depending on topology
- CPU: 2+ vCPU, RAM: 2-4 GB
- Disk: 2-8 GB (based on logs and packages)
- CHR license tier aligned to expected throughput

## Baseline setup

1. Define interface and addressing plan.
2. Lock down management access (ACL + service ports).
3. Configure static or dynamic routing policies.
4. Apply ingress/egress firewall filters.
5. Enable export/binary backups and VM snapshots.

## Good practices

- Separate management and data planes.
- Document route filters and policy routing logic.
- Evaluate FastTrack/FastPath impact before production.
- Control RouterOS versioning to reduce regressions.

## Operational checklist

- Is CHR license tier sufficient for real traffic?
- Are anti-spoofing and bogon filters in place?
- Are CPU, pps and queue metrics monitored?
- Is there a tested rollback path by version?
