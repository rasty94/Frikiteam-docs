---
title: "NetApp ONTAP — Base Guide"
description: "ONTAP concepts (cluster, aggregates, SVM, volumes, LIFs), basic CLI, NFS exports and SMB shares, snapshots and SnapMirror, space efficiency and integration with Proxmox and Kubernetes over NFS and iSCSI."
keywords: "netapp, ontap, svm, flexvol, aggregate, lif, snapshot, snapmirror, nfs, smb, iscsi, trident, proxmox"
tags: ['storage', 'netapp']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 18 min
category: Storage
status: published
last_reviewed: 2026-10-10
prerequisites:
  - "NFS, SMB and iSCSI concepts"
  - "[Storage protocols](../protocols/protocols.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# NetApp ONTAP — Base Guide

## The problem

You are handed a NetApp array and discover it does not look like a NAS server: there is a cluster, nodes, aggregates, something called an SVM, and IP addresses that belong to "logical interfaces" instead of a network card. You create a volume, export it and the clients cannot see it, because in ONTAP creating the volume does not publish it: you also need the *junction path*, the export policy and a LIF in the right SVM. Each layer has its reason to exist, but you have to learn them in order.

This page is the map: what each object is, how they relate, the basic commands to inspect them, and how it all connects to Proxmox and Kubernetes. It is a starting point, not an ONTAP administration manual.

!!! note "What this covers and what it does not"
    This page covers the **object model** and access over NFS/SMB/iSCSI from your infrastructure. For comparing protocols and measuring performance see [Storage protocols](../protocols/protocols.md); for another commercial array, [Pure Storage](../pure_storage/pure_storage_base.md); for software-defined storage, [Ceph](../ceph/ceph_base.md).

## 📋 Table of Contents

- [ONTAP concepts](#ontap-concepts)
- [Basic CLI](#basic-cli)
- [Creating and publishing a volume](#creating-and-publishing-a-volume)
- [Space efficiency](#space-efficiency)
- [Snapshots and SnapMirror](#snapshots-and-snapmirror)
- [Proxmox integration](#proxmox-integration)
- [Kubernetes integration](#kubernetes-integration)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## ONTAP concepts

ONTAP is the operating system of NetApp arrays (FAS, AFF, ASA). The objects, from the bottom up:

| Object | What it is |
|---|---|
| **Node** | A physical controller. Nodes are grouped into high-availability pairs (HA pairs) that cover for each other |
| **Cluster** | The set of nodes managed as one unit, with a single management point |
| **Aggregate** | A pool of disks on a node. It provides the physical capacity on which volumes live |
| **SVM** (vserver) | *Storage Virtual Machine*: a virtual file/block server with its own namespace, users, protocols and LIFs. It is the multi-tenancy boundary |
| **Volume (FlexVol)** | The unit clients see: it holds files (NAS) or LUNs (SAN). It belongs to an SVM and lives in an aggregate |
| **Qtree** | A subdirectory inside a volume to which quotas can be applied |
| **LUN** | A block disk presented over iSCSI or FC, stored inside a volume |
| **LIF** | *Logical Interface*: the service IP (or WWPN) of an SVM. It is bound to a physical port and can migrate between nodes |

The ideas that prevent the most stumbles:

- **Clients talk to the SVM, not the cluster.** You mount `svm1:/vol_datos`, not a node. The IP you point to is a data LIF of that SVM.
- **LIFs are mobile.** If a node goes down or a takeover happens, the LIF migrates and the IP keeps answering. That is why the client must never point to a node's management IP.
- **A NAS volume needs a *junction path***: its position in the SVM's namespace tree (`/vol_datos`). Without it the volume exists but cannot be exported.
- **Access = enabled protocol + LIF + policy.** In NFS the policy is the *export policy*; in SMB, the share and its ACLs; in iSCSI, the *igroup* that maps the LUN to the initiators.

## Basic CLI

The ONTAP CLI is hierarchical (`volume show`, `network interface show`) and you connect over SSH to the cluster management LIF with an administrator user. The inspection commands are safe and change nothing:

```text
cluster show                  # cluster nodes and their state
storage aggregate show        # aggregates, used and free capacity
vserver show                  # SVMs and allowed protocols
volume show                   # volumes, their SVM, aggregate and size
network interface show        # LIFs: current IP, node and port, status
volume snapshot show          # snapshots per volume
```

Each command can be filtered by SVM or volume with parameters such as `-vserver` and `-volume`, and completes with the tab key. Read them in prose: `network interface show` tells you whether each LIF is up and whether it is on its home node or has migrated; `volume show` tells you the available space and which aggregate each volume belongs to.

!!! warning "Version dependent"
    The syntax and displayed fields change between ONTAP versions (9.x adds parameters and reorganizes some outputs). Check the help for your version with `?` in the CLI itself before copying commands from another installation.

## Creating and publishing a volume

Logical order: volume, access policy, publication. Example for an NFS datastore:

```text
volume create -vserver svm1 -volume vol_datos -aggregate aggr1_nodo1 -size 500GB -junction-path /vol_datos
vserver export-policy create -vserver svm1 -policyname pol_proxmox
vserver export-policy rule create -vserver svm1 -policyname pol_proxmox -clientmatch 10.0.10.0/24 -protocol nfs -rorule sys -rwrule sys -superuser sys
volume modify -vserver svm1 -volume vol_datos -policy pol_proxmox
```

The *export policy* is the equivalent of the `/etc/exports` file: it defines which clients get in and with what privileges. `-superuser sys` is equivalent to `no_root_squash` and should only be granted to trusted hosts, such as hypervisors. An empty policy lets nobody through, and the default rule of the `default` policy is rarely what you want.

To expose the same volume over SMB you create a share on its junction path, provided the SVM has CIFS configured and joined to the domain:

```text
vserver cifs share create -vserver svm1 -share-name datos -path /vol_datos
vserver cifs share show -vserver svm1
```

The share controls access by user and group through ACLs; the export policy plays no part in SMB. If the volume is shared over NFS and SMB at the same time, the volume's security style (unix, ntfs or mixed) decides how permissions are resolved between the two worlds: choose it when creating the volume and do not change it once there is data inside.

### Checking from a Linux client

Before accepting the volume as good, mount it by hand from an authorized host and write a test file:

```bash
sudo mkdir -p /mnt/netapp
sudo mount -t nfs -o vers=4.1 10.0.10.50:/vol_datos /mnt/netapp
touch /mnt/netapp/prueba && ls -l /mnt/netapp
sudo umount /mnt/netapp
```

The IP is that of a data LIF of the SVM and the path is the junction path. If the mount fails, the client's message almost always distinguishes between "there is no route to the LIF" and "the LIF answers but the export policy rejects you". If the server only offers NFSv3, change `vers=4.1` to `vers=3`.

!!! warning "NFS version"
    Which NFS versions are enabled is an SVM setting and varies with its configuration and the ONTAP version. Confirm it with your administrator before fixing `vers=` in `/etc/fstab`.

## Space efficiency

ONTAP applies deduplication, compression and compaction at the volume level. On all-flash systems (AFF, ASA) they usually come enabled by default; on FAS with spinning disks it is worth checking.

- **Thin provisioning**: the volume declares a size but only consumes what is written. Watch the free space of the **aggregate**, not just the volume: you can promise more than exists.
- **`volume autosize`**: lets the volume grow by itself up to a defined maximum. Always use it with a limit, so a runaway client does not eat the aggregate.
- **Quotas on qtrees**: if several teams share a volume, one qtree per team with its quota bounds consumption.
- **FabricPool**: moves cold blocks to an S3 object store (on-prem or cloud). The volume's policy (`auto`, `snapshot-only`...) decides what counts as cold; evaluate the retrieval latency before applying it to data that is read often.

!!! warning "Efficiency is not guaranteed capacity"
    Dedupe and compression ratios depend on the data: compressed databases, video or already-encrypted data barely improve. Size with the real data, not the brochure ratio.

## Snapshots and SnapMirror

An ONTAP **snapshot** is a point-in-time image of the volume based on pointers, not a data copy: it is created in seconds and only consumes space when the original blocks change. That is why you can have many.

```text
volume snapshot create -vserver svm1 -volume vol_datos -snapshot antes_de_migrar
volume snapshot show -vserver svm1 -volume vol_datos
```

- **Snapshot policies**: assigned to the volume, they generate periodic copies (for example hourly, daily and weekly) with a retention for each. This is where you define how much history you get "for free".
- **Restoring**: you can recover a specific file from the volume's hidden `.snapshot` directory or revert the whole volume to a snapshot. Reverting the volume discards everything after it: it is the nuclear option.
- **SnapMirror**: replicates a volume to another (in the same cluster or another) by transferring only the blocks changed between snapshots. It is the basis of disaster recovery. There are asynchronous modes, with an RPO equal to the schedule interval, and synchronous modes for near-zero RPO.
- **Snapshot labels (`snapmirror-label`)**: let the relationship replicate or retain only certain snapshots, useful for having different retentions at source and destination.
- **SnapVault / long-retention destination**: the destination keeps more history than the source. Schedule an update after critical events, such as a database dump.

```text
snapmirror show               # replication relationships, their state and lag
```

A relationship is created and initialized between two volumes, with the destination marked as type DP or its equivalent in your version. The exact steps change between versions and between cluster peering and SVM peering, so follow the guide for your version.

!!! danger "A snapshot is not a backup"
    Snapshots live in the same volume and the same aggregate as the data: if the array is lost, or an administrator deletes the volume, they go with it. SnapMirror to another cluster improves the case a lot, but it is still a copy managed by the same system. Apply the rule from [3-2-1 Strategy](../../backups/strategy_321.md) and complement it with an independent copy, for example with [Restic and Borg](../../backups/restic_borg.md).

## Proxmox integration

Two paths, depending on what matters most:

**NFS** is the simplest: the volume is mounted as shared storage, ideal for disk images, ISOs and backups, and for live migration between nodes without configuring anything else. In Proxmox it is added from the interface or with `pvesm`:

```bash
pvesm add nfs netapp-nfs --server 10.0.10.50 --export /vol_datos --content images,iso,backup
```

The IP is an NFS data LIF of the SVM, not the management one. Allow **all** Proxmox nodes in the export policy. Prefer NFSv4.1 when the environment supports it and tune `rsize`/`wsize` only after measuring with `fio`, as explained in [Storage protocols](../protocols/protocols.md). For a data LIF with several network paths, check your Proxmox version's support for NFS multipath and session options before basing the design on them.

**iSCSI** offers block storage and better latency for databases or sensitive VMs. The LUN is published to each node's initiators (igroup), `multipath` is configured on the hosts and shared LVM or similar is set up on top of the device. It is more work and multipath needs care: two iSCSI LIFs on different networks and active paths on both nodes.

Rule of thumb: NFS for general datastores, iSCSI for the workloads where you measure latency and can justify it. Platform details are in [Proxmox base](../../proxmox/proxmox_base.md).

## Kubernetes integration

NetApp's CSI provider is called **Trident**. It is installed in the cluster, given a *backend* (the SVM and its credentials) and *StorageClasses* are exposed pointing to that backend. The backend type defines the protocol: the `ontap-nas` drivers for NFS and `ontap-san` for iSCSI.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ontap-nas
provisioner: csi.trident.netapp.io
parameters:
  backendType: "ontap-nas"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

- `WaitForFirstConsumer` delays volume creation until a pod exists, so it is created where it will be used.
- `allowVolumeExpansion: true` allows growing the PVC online.
- One StorageClass per service level (for example `ontap-nas` for shared files and a block one for databases) lets the application team decide without touching the array.
- Kubernetes nodes need access in the export policy (NFS) or the igroup (iSCSI), and the NFS/iSCSI clients installed.

!!! warning "Names and parameters depend on the Trident version"
    The StorageClass parameters, the backend format and the available drivers change between Trident and ONTAP versions. Check against the documentation for the installed version. The general CSI model and access modes are in [Kubernetes and CSI](../kubernetes_csi.md).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| The NFS client gets `access denied` when mounting | The client IP matches no rule in the export policy, or the policy is not assigned to the volume | Check `vserver export-policy rule show` and that the volume uses that policy |
| The volume exists but cannot be mounted | It has no junction path, or the SVM does not have NFS enabled | Check `volume show` and `vserver show` |
| It mounts but files belong to `nobody` | ID domain mismatch in NFSv4 or user mapping mismatch | Align the ID domain between client and SVM, or use NFSv3 if there is no central identity |
| The client cannot reach the IP | The LIF migrated, is down or is on a different VLAN | `network interface show`: the LIF's status and current node |
| The volume fills up even though the aggregate has space | `autosize` disabled or with a low maximum | Adjust `volume autosize` or enlarge the volume |
| The aggregate fills up suddenly | Oversubscribed thin provisioning, or retained snapshots consuming space | Check `storage aggregate show` and the snapshot policy |
| The SMB share does not authenticate | The SVM is not joined to the domain or there is clock skew with the domain controller | Check the SVM's CIFS configuration and synchronize time |
| Irregular performance over iSCSI | Misconfigured multipath or only one active path | Verify there are active paths for each LIF and the balancing on the host |
| SnapMirror shows growing lag | Saturated link or a previous transfer that has not finished | `snapmirror show` and check bandwidth and schedule |

## Best practices

- **One SVM per trust domain** (environments, customers, teams): it is the boundary of access and protocols.
- **Data LIFs separate from management**, and at least one per node and protocol so failover keeps the service up.
- **Minimal export policies**: specific subnets, `superuser` only for hypervisors, never `0.0.0.0/0`.
- **One volume per datastore or application**, not one giant volume: snapshots, quotas and restores per unit.
- **`autosize` with a limit and alerts** on the aggregate's free space.
- **Explicit snapshot policies**, with labels to decide what SnapMirror replicates.
- **Test the restore**, from `.snapshot` and from the SnapMirror destination, before you need it.
- **An independent copy outside the array**: a snapshot and a replica do not replace a real backup.
- **Document the ONTAP and Trident versions** in use; the commands and parameters on this page may differ in others.

## References

- [NetApp ONTAP documentation](https://docs.netapp.com/us-en/ontap/)
- [Trident documentation](https://docs.netapp.com/us-en/trident/)
- [Storage protocols](../protocols/protocols.md) · [Kubernetes and CSI](../kubernetes_csi.md)
- [Pure Storage](../pure_storage/pure_storage_base.md) · [Ceph](../ceph/ceph_base.md)
- [3-2-1 Strategy](../../backups/strategy_321.md) · [Restic and Borg](../../backups/restic_borg.md)
- [Proxmox base](../../proxmox/proxmox_base.md)
