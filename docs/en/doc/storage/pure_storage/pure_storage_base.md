---
title: "Pure Storage — Quick Guide"
description: "Pure Storage FlashArray in self-hosted infrastructure: tiers, volumes, hosts, snapshots, protection groups, ActiveCluster and CSI for Kubernetes and virtualization."
keywords: "pure storage, flasharray, purity, purevol, purehost, protection group, activecluster, csi, iscsi, multipath, snapshots"
tags: ['storage', 'pure-storage']
updated: 2026-10-11
difficulty: beginner
estimated_time: 12 min
category: Storage
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Basic SAN concepts (LUN, iSCSI, multipath)"
  - "Administrative access to a FlashArray (CLI over SSH or GUI)"
  - "Kubernetes or a hypervisor as the storage consumer"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Pure Storage — Quick Guide

## The problem

You have an expensive all-flash array and a very mixed set of consumers: a database that demands low, steady latency, a virtualization cluster with hundreds of near-identical VMs, and a Kubernetes cluster that requests volumes through an API. If you present LUNs by hand, you end up with unlabeled volumes, badly defined hosts and snapshots nobody knows whether they can delete.

A FlashArray performs well when you treat it as **a small set of declarative objects**: thin volumes, hosts, protection groups and policies. This page covers that model and how to wire it into the site's infrastructure, without repeating the vendor manual.

!!! note "What this covers and what it does not"
    It covers the object model, integration with hypervisors and Kubernetes, and data protection. Network configuration, performance figures and exact limits depend on the model and the Purity version: check the vendor documentation for your array.

## 📋 Table of Contents

- [Product line and tiers](#product-line-and-tiers)
- [Object model](#object-model)
- [Provisioning from the CLI](#provisioning-from-the-cli)
- [Connecting hosts: iSCSI, multipath and NFS](#connecting-hosts-iscsi-multipath-and-nfs)
- [Data reduction and thin provisioning](#data-reduction-and-thin-provisioning)
- [Snapshots, clones and protection groups](#snapshots-clones-and-protection-groups)
- [Replication and ActiveCluster](#replication-and-activecluster)
- [Kubernetes with the CSI driver](#kubernetes-with-the-csi-driver)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [References](#references)

## Product line and tiers

- **FlashArray//X and //XL**: high-performance NVMe block storage for databases, VMs and latency-sensitive workloads.
- **FlashArray//C**: capacity on QLC flash. Fits warm data, replicas and test environments, where cost per TB is what matters.
- **FlashBlade**: file and object (NFS/SMB/S3) for backups, logs and analytics.

The tier idea in a self-hosted environment is simple: whatever hurts when slow goes to //X; whatever just has to exist goes to //C or to a cheap NFS/S3 repository. For the cheap repository, see also [Restic and Borg](../../backups/restic_borg.md) and the [3-2-1 strategy](../../backups/strategy_321.md): an array, however good, is not a backup.

## Object model

| Object | What it is | CLI command (family) |
|--------|------------|----------------------|
| Volume | Thin block device, with a name and size | `purevol` |
| Host | Initiators (IQN, WWN or NQN) of a consumer | `purehost` |
| Host group | Set of hosts sharing volumes (clusters) | `purehgroup` |
| Protection group | Volumes + snapshot schedule + replication target | `purepgroup` |
| Array | Global state, Purity version, capacity | `purearray` |

The rule of thumb: **volumes shared between nodes are connected to the host group, not to each host**. That way, adding a node to the cluster means adding it to the group, and every LUN shows up with the same number.

## Provisioning from the CLI

Everything the GUI does is in the CLI over SSH, which is handy for scripts and for documenting the process. Check the exact syntax for your version with `--help` before automating.

```bash
# General array state and Purity version
purearray list

# 2 TiB thin volume for the database
purevol create --size 2T db-prod

# Define the host with its iSCSI initiators
purehost create --iqnlist iqn.2026-01.lab.example:esx01 esx01

# Present the volume to the host
purevol connect --host esx01 db-prod

# Review volumes and connections
purevol list
purehost list --connect
```

!!! warning "QoS limits depend on the version"
    Per-volume IOPS and bandwidth limits exist in recent Purity versions, and their syntax changes between versions. Before applying them, check the help for `purevol setattr` and your array's release notes. Without limits, a noisy volume can hurt all the others.

## Connecting hosts: iSCSI, multipath and NFS

- **iSCSI with multipath**: two separate storage networks or VLANs, one portal IP per controller and per network. With `multipath-tools` on Linux, apply the policy the vendor recommends for its LUNs; check its settings guide for your distribution.
- **Fibre Channel or NVMe/TCP**: if your array and hosts support it, avoid translation layers. Defining hosts and connecting volumes works the same way; only the identifiers change.
- **NFS**: FlashBlade offers it as a file service. For virtualization over NFS, validate the protocol version your hypervisor supports and the mount mode. Compare protocols in [Storage protocols](../protocols/protocols.md).

On Proxmox and VMware the pattern is the same: one large LUN shared by the whole cluster, presented to the host group. On VMware, the vSphere plugin and VAAI offloads speed up clones and deletes; on Proxmox, shared LVM over iSCSI with multipath is the usual setup.

!!! tip "A dedicated storage network"
    Keep storage traffic apart from management and VM traffic, with MTU 9000 only if the **whole** path supports it. A single 1500 hop in the middle causes fragmentation and erratic latency that gets mistaken for array problems.

## Data reduction and thin provisioning

Volumes are thin by design and the array applies inline deduplication and compression. Consequences that matter when operating:

- The capacity you see on the host (2 TiB) is not what the array consumes. Watch the available **physical** space, not the sum of what is provisioned.
- Data reduction depends on content: databases and identical VMs reduce a lot; already compressed or encrypted data, almost nothing. Do not size against the best figure you can find.
- If you encrypt in the guest (LUKS, disk encryption), you cancel a large part of the reduction. Decide where to encrypt before sizing.
- `discard`/`UNMAP` from the guest or hypervisor returns space to the array; without it, the filesystem's free space still counts.

## Snapshots, clones and protection groups

A FlashArray snapshot costs almost nothing to create and is crash-consistent. For application consistency, quiesce or notify the application first (for example, a `CHECKPOINT` in PostgreSQL or the backup mode of whatever tool you use).

```bash
# Manual snapshot of a volume with a readable suffix
purevol snap --suffix pre-upgrade db-prod

# Clone a volume (or a snapshot) for testing
purevol copy db-prod db-test

# List snapshots
purevol list --snap
```

For anything recurring, do not schedule crons: use a **protection group**. It bundles volumes, a snapshot schedule (for example, hourly with short retention and daily with long retention) and, optionally, a replication target. Changing the policy in one place changes the behavior of every volume in the group.

Recommendations:

- One protection group per **workload**, not a global one: a database's retention is not that of an ISO volume.
- Name by service and environment (`pg-prod`, `k8s-dev`) so the snapshot list makes sense without opening each one.
- A snapshot on the same array **does not protect against losing the array**. Combine it with replication or an off-site copy.

## Replication and ActiveCluster

- **Asynchronous replication**: a protection group targeting another array. Meant for disaster recovery with an RPO of minutes to hours.
- **ActiveCluster**: synchronous replication between two arrays, with volumes accessible from both sites and a mediator that decides who keeps serving on a link failure. Requires low latency between sites and a dedicated network.
- **ActiveDR**: near-synchronous replication, aimed at a very low RPO without the latency constraint of synchronous.

!!! warning "Availability depends on model and license"
    Which replication options are available, their latency requirements and the minimum Purity version depend on your model and license. Confirm them in the vendor documentation before designing DR around them.

In a homelab or small business, the usual setup is a single array plus asynchronous replication or a copy to an external repository. ActiveCluster pays off when you have two sites and near-zero downtime as a business requirement.

## Kubernetes with the CSI driver

Pure offers the Portworx CSI driver (PX-CSI) —the older Pure Service Orchestrator was announced as discontinued in 2022— that creates and expands volumes on demand. General details of the CSI model are in [Kubernetes CSI](../kubernetes_csi.md). With a well-defined StorageClass, the developer asks for a PVC and the array creates the volume.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pure-gold
provisioner: pure-csi
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

!!! warning "The provisioner name depends on the driver"
    The `provisioner` value and the supported parameters (`backend`, volume type, etc.) depend on the driver and its version. Take the manifest from the documentation of the driver you install, not from this page.

- `WaitForFirstConsumer` avoids creating volumes before knowing which node the pod is scheduled on, and therefore on a node without connectivity to the array.
- `allowVolumeExpansion: true` allows online growth by editing the PVC.
- `reclaimPolicy: Retain` in production: deleting a PVC by mistake must not delete the data. In development, `Delete` cleans up on its own.
- One StorageClass per level (`gold`, `silver`, `bronze`), each mapped to different limits on the array.

## Monitoring

What to watch, in order of usefulness:

1. **Physical capacity and reduction ratio**: the important alert. A full array degrades and ends up rejecting writes.
2. **Read and write latency per volume**: what the application sees. A sustained spike points to a noisy neighbor or the network.
3. **IOPS and bandwidth per volume**: to identify who consumes and decide on limits.
4. **Controller, disk and path health**: a failed path goes unnoticed if multipath works, until the second one fails.

For metrics and alerting you can use the vendor's Prometheus exporter and Grafana dashboards, like the rest of the site's infrastructure.

## Troubleshooting

| Symptom | Probable cause | Fix |
|---------|----------------|-----|
| The host does not see the LUN | Initiator wrongly declared in `purehost` or volume not connected | `purehost list`, compare IQN/WWN with the host's and reconnect with `purevol connect` |
| Each LUN appears several times on the host | Multipath not configured | Install and enable multipath and apply the vendor-recommended policy |
| Erratic iSCSI latency | Inconsistent MTU or network shared with management | Verify MTU along the whole path, isolate the storage VLAN or network |
| Free space does not rise after deleting data | Guest or hypervisor does not send `discard`/`UNMAP` | Enable `discard` in the guest or run `fstrim` periodically |
| The PVC stays in `Pending` | Missing StorageClass, driver down or no connectivity to the array | `kubectl describe pvc`, check the CSI driver logs and the network path |
| One volume degrades all the others | No performance limits | Apply IOPS/bandwidth limits (version-dependent) or move the workload to another tier |
| Snapshots take up too much space | Long retention on high-change workloads | Review the protection group schedule and the volume's change rate |

## Best Practices

- Work with **host groups** for clusters: adding a node should not mean revisiting every volume.
- Define **protection groups per workload**, with self-explanatory names, and review retention every quarter.
- Watch **physical space**, not provisioned: thin provisioning moves the risk from the volume to the array.
- A snapshot is not a backup. Keep a copy outside the array following [the 3-2-1 rule](../../backups/strategy_321.md).
- Document which volume belongs to which service. A volume without an owner is a volume nobody dares delete.
- Test **restoration** (clone a snapshot and mount it) before you need it, not during the incident.
- If you already have another array, compare approaches in [NetApp ONTAP](../netapp/netapp_base.md) before duplicating processes.

## References

- [Official Pure Storage documentation](https://support.purestorage.com/)
- [Portworx CSI (docs.portworx.com)](https://docs.portworx.com/portworx-csi/)
- [Storage protocols](../protocols/protocols.md)
- [Kubernetes CSI](../kubernetes_csi.md)
- [NetApp ONTAP](../netapp/netapp_base.md)
- [3-2-1 backup strategy](../../backups/strategy_321.md)
