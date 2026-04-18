# VyOS (automation-first virtual router)

VyOS works especially well for teams using automation, GitOps and reproducible network infrastructure.

## When to choose VyOS

- You need BGP/OSPF with declarative automation
- You want network config versioned as code
- Your operations rely on DevOps/NetOps pipelines

## Recommended deployment

- 2+ vNICs depending on design
- CPU: 2+ vCPU, RAM: 2-4 GB
- Disk: 8 GB+

## Baseline setup

1. Define interfaces and addressing.
2. Harden SSH and admin accounts.
3. Configure zone-based firewall policies.
4. Implement static or dynamic routing (FRR).
5. Automate backups and configuration validation.

## Good practices

- Store config templates in Git.
- Introduce changes via pull requests and reviews.
- Separate lab/preprod/prod when feasible.
- Run periodic failover and convergence testing.

## Operational checklist

- Is all critical config version-controlled?
- Is there a syntax/functional validation pipeline?
- Have link/peer failure scenarios been tested?
- Are snapshots or backups ready for rollback?
