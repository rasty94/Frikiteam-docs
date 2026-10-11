---
title: "Kubernetes Backup: Velero and etcd Snapshots"
description: "Protect a self-hosted Kubernetes cluster: what to copy and what to skip with GitOps, etcd snapshots (kubeadm and k3s), Velero with MinIO, volumes via CSI snapshot or File System Backup, consistency hooks and restore testing."
keywords: "kubernetes, backup, velero, etcd, etcdctl, k3s, minio, csi, snapshot, kopia, restic, gitops, restore"
tags: ['kubernetes', 'backups', 'storage']
updated: 2026-10-11
difficulty: advanced
estimated_time: 32 min
category: Backups
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "A Kubernetes cluster (kubeadm, k3s or other) and kubectl access"
  - "[3-2-1 Backup Strategy](strategy_321.md)"
  - "S3-compatible storage (MinIO or other) outside the cluster"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Kubernetes Backup: Velero and etcd Snapshots

## The problem

A cluster looks easy to back up because "it's all YAML". Then your only control-plane node fails, or someone runs `kubectl delete namespace` in the wrong context, and you find out the YAML you had was not everything: the Secrets that never went through Git, the database data living on persistent volumes, the certificates cert-manager issued and the objects an operator created are all missing. You also find out that your VM backups with [PBS](pbs.md) copy the node's disk, not the intent of the cluster: restoring a three-day-old control-plane node into a three-node cluster that kept running produces an etcd that contradicts everything else.

A cluster has three layers with different risks and tools: the **API state** (objects stored in etcd), the **volume data** and the **configuration that rebuilds the cluster** (certificates, tokens, control-plane manifests). This page explains how to protect each one with etcd snapshots and Velero, and how the result fits into a [3-2-1 strategy](strategy_321.md).

!!! note "What this covers and what it doesn't"
    This page covers **cluster backup and restore**. What a CSI driver is and how StorageClasses are created is in [Kubernetes CSI](../storage/kubernetes_csi.md); the Kubernetes object model is in [Kubernetes base](../kubernetes/kubernetes_base.md). The logic of copies, media and location is not repeated here: it lives in [3-2-1 Backup Strategy](strategy_321.md), and destination encryption and immutability in [Secure Backup](../cybersecurity/backup_seguro.md).

## 📋 Table of Contents

- [What to protect](#what-to-protect)
- [etcd snapshots](#etcd-snapshots)
- [etcd in k3s](#etcd-in-k3s)
- [Velero: architecture](#velero-architecture)
- [Installing Velero with MinIO](#installing-velero-with-minio)
- [Backups, schedules and restore](#backups-schedules-and-restore)
- [Volumes: CSI snapshots or file copy](#volumes-csi-snapshots-or-file-copy)
- [Consistency: pre and post hooks](#consistency-pre-and-post-hooks)
- [Testing the restore](#testing-the-restore)
- [Fit with the 3-2-1 rule](#fit-with-the-3-2-1-rule)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## What to protect

| Layer | Where it lives | How to protect it |
|---|---|---|
| API objects (Deployments, Services, ConfigMaps, CRDs, RBAC) | etcd | Git if you use GitOps; etcd snapshot or Velero otherwise |
| Secrets | etcd, and in Git only if encrypted | See the caveat below |
| Persistent volume data | The storage backend (Ceph, NFS, local disks) | Velero with CSI snapshots or File System Backup; native database backup |
| PKI, tokens and control-plane configuration | Control-plane node disk (`/etc/kubernetes/pki` in kubeadm) | File copy with [restic or Borg](restic_borg.md) |
| The nodes themselves | VM or machine disks | Optional: they get reinstalled; rebuilding is cheaper than restoring |

### What you don't need to copy with GitOps

If the cluster is managed with [Argo CD](../cicd/argocd.md) or similar, the Deployments, Services, Ingresses and ConfigMaps are already in Git, which is a better backup than any snapshot: it has history, review, and lives outside the cluster. Rebuilding means installing an empty cluster, installing Argo CD and letting it sync. That saves you from copying most of the API state, but **it does not save you from three things**:

1. **Data.** Git holds the PostgreSQL `StatefulSet` manifest, not its tables. Volumes still need a backup.
2. **Secrets.** If Secrets exist in the cluster and never in Git, they are lost with it. If you use SOPS or Sealed Secrets, what must be backed up outside the cluster is the **decryption key** (age key or the controller's private key): without it, the encrypted files in Git are unrecoverable. See [Secrets in GitOps](../cybersecurity/secrets_gitops.md).
3. **Generated state.** Certificates issued by cert-manager (they can be reissued, but with Let's Encrypt rate limits), resources an operator creates (the database an operator spins up from a CR) and objects created by hand with `kubectl apply` that never reached Git.

!!! warning "An etcd snapshot contains the Secrets"
    Without Secret encryption at rest configured in the API server, Secrets sit in etcd in the clear (base64-encoded, which is not encryption). The same applies to a Velero backup: the namespace's Secrets travel to the bucket as they are. Encrypt the destination and restrict who can read the bucket; see [Secure Backup](../cybersecurity/backup_seguro.md).

## etcd snapshots

etcd is the database that holds the cluster's full state. A snapshot is a consistent copy of that database at one instant. It is the simplest tool for total control-plane disaster, and the least selective: you recover the whole cluster to that instant, or nothing.

### Creating the snapshot

In a kubeadm cluster, etcd runs as a static pod and its certificates are in `/etc/kubernetes/pki/etcd/`. Run from a control-plane node (or from a pod with `etcdctl` and those files mounted):

```bash
ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /var/backups/etcd/etcd-$(date +%F-%H%M).db
```

A snapshot is taken from a single member and contains the data of the whole cluster; there is no need to repeat it on every control-plane node. It is wise to take it from a healthy member and check that the resulting file is valid:

```bash
etcdutl snapshot status /var/backups/etcd/etcd-2026-10-11-0300.db --write-out=table
```

The output is a table with the hash, revision, key count and size. A reasonable revision and a non-zero key count suggest the file is readable; it does not prove it is restorable.

!!! warning "Depends on version"
    In etcd 3.5 the `snapshot status` subcommand of `etcdctl` is marked deprecated in favor of `etcdutl`, and so is `snapshot restore`; in later versions it may no longer exist in `etcdctl`. Check `etcdctl snapshot --help` and `etcdutl snapshot --help` to see what your version offers. The ports, certificate paths and file names above are kubeadm's; other distributions differ.

A snapshot that lives on the control-plane node only survives as long as the node does. Schedule it with a systemd timer (or a CronJob with `hostNetwork` on the control-plane node), and copy the file to an external destination with [restic or Borg](restic_borg.md) or with `rclone`. Local rotation is simple: keep the last N files and leave the history to the backup repository.

### Restoring etcd

Restoring a snapshot **is not an operation on a node, but on the whole cluster**. The snapshot holds the state of every object at one instant: restoring it on a single member of a three-member etcd creates a member that contradicts the other two. The general procedure is therefore:

1. Stop the API server and etcd on **all** control-plane nodes (in kubeadm, move the manifests out of `/etc/kubernetes/manifests/`).
2. Restore the snapshot into a new data directory, on every member, with `etcdutl snapshot restore`, giving the member name, the initial member list and the cluster URLs.
3. Point the etcd manifest (the data directory `hostPath`) at the restored directory.
4. Put the manifests back and wait for the cluster to form quorum.

With a single control-plane node it is shorter: restore into a new directory, change the `hostPath` in the etcd manifest and start. Consequences worth having clear before you need it:

- **Everything created after the snapshot is lost.** If a Pod was scheduled, a PVC created or a Secret rotated afterwards, the cluster doesn't know. The real volumes may exist in the backend with no object claiming them.
- **Worker nodes are not touched**, but the state they report (kubelet) may differ from the restored one until it reconciles.
- **The certificates in the snapshot may have expired** if it is old. Back up the control-plane PKI too.

!!! warning "Depends on distribution and version"
    The exact flags of `etcdutl snapshot restore`, the location of the etcd manifest and the start order change between kubeadm, RKE2, k3s, Talos and managed services. Follow the procedure for **your** distribution and version, and rehearse it on a test cluster before you need it. On a managed service (EKS, GKE, AKS) you have no access to etcd: only Velero or GitOps apply there.

## etcd in k3s

k3s has two storage modes and the procedure depends on which one you use.

**SQLite (the default with a single server).** There is no etcd: the state is in a SQLite database file inside the server's data directory (`/var/lib/rancher/k3s/server/db/`). `k3s etcd-snapshot` **does not apply**. The copy consists of stopping the service and copying the `db/` directory together with `/var/lib/rancher/k3s/server/token`, or copying a SQLite file live with SQLite's own backup tool; copying an open SQLite file with `cp` can produce an inconsistent copy.

**Embedded etcd (`--cluster-init`, or HA clusters).** k3s ships its own command:

```bash
k3s etcd-snapshot save --name before-upgrade
k3s etcd-snapshot ls
k3s etcd-snapshot prune --name before-upgrade --etcd-snapshot-retention 3
```

With embedded etcd, k3s also takes scheduled snapshots on its own, configurable in `/etc/rancher/k3s/config.yaml`:

```yaml
etcd-snapshot-schedule-cron: "0 */6 * * *"
etcd-snapshot-retention: 14
etcd-snapshot-dir: /var/backups/k3s
# Copy to an S3-compatible bucket (MinIO) outside the cluster
etcd-s3: true
etcd-s3-endpoint: minio.example.lan:9000
etcd-s3-bucket: k3s-etcd
etcd-s3-access-key: "<access-key>"
etcd-s3-secret-key: "<secret-key>"
```

To restore, stop k3s and start the server in cluster-reset mode with the snapshot path:

```bash
systemctl stop k3s
k3s server --cluster-reset --cluster-reset-restore-path=/var/backups/k3s/<snapshot>
```

After that start, on a multi-server cluster, the other control-plane nodes need their etcd data directory deleted and must be rejoined. Keep the server token as well: without it, the encrypted bootstrap data inside the snapshot cannot be decrypted.

!!! warning "Depends on version"
    The names of the `etcd-snapshot` and `etcd-s3` flags have changed between k3s versions, and so have the default schedule and retention. Check `k3s etcd-snapshot --help` and the documentation for your version. The S3 snapshots and the `/etc/rancher/k3s/config.yaml` contents above are a reference, not a recipe to copy without checking.

## Velero: architecture

Velero solves what etcd cannot: restoring **one namespace, one resource or one volume** without touching the rest, even into another cluster. It works through the Kubernetes API (not etcd directly) and stores objects as files in object storage.

| Piece | What it is |
|---|---|
| **Velero server** | A Deployment in the `velero` namespace, with controllers for backups, schedules and restores |
| **`velero` CLI** | Client that creates the objects (`Backup`, `Schedule`, `Restore`) in the cluster |
| **BackupStorageLocation (BSL)** | Where backup objects are stored: an S3-compatible bucket (MinIO, Ceph RGW, AWS S3) |
| **VolumeSnapshotLocation (VSL)** | Where volume snapshots go for providers Velero manages with its own plugin (cloud disks); with CSI, Kubernetes `VolumeSnapshot` objects are used |
| **Provider plugin** | Image that teaches Velero to talk to a specific storage; for S3 and MinIO, the AWS plugin |
| **Node agent** | DaemonSet that performs file-level copy of volumes (File System Backup) |

Everything Velero creates is a resource of the cluster itself (CRDs), which means the state of which backups exist is rebuilt by reading the bucket: a fresh Velero pointing at the same BSL "discovers" the existing backups.

## Installing Velero with MinIO

You need a bucket and dedicated credentials with permissions on that bucket only. Create the credentials file in the AWS format:

```ini
[default]
aws_access_key_id = <access-key>
aws_secret_access_key = <secret-key>
```

And run the install against a MinIO that runs **outside the protected cluster** (another host, the NAS, another cluster):

```bash
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:<version> \
  --bucket velero-backups \
  --secret-file ./credentials-velero \
  --backup-location-config region=minio,s3ForcePathStyle=true,s3Url=https://minio.example.lan:9000 \
  --use-node-agent \
  --use-volume-snapshots=false
```

`<version>` is the plugin version compatible with your Velero version; the compatibility table is in the plugin's repository. `s3ForcePathStyle=true` is required with MinIO because it doesn't use subdomain addressing. `--use-node-agent` deploys the DaemonSet for file copy; omit it if you will only use CSI snapshots. If MinIO uses a private CA, add `--cacert` with the CA.

Check that the server is ready and that the BSL reaches the bucket:

```bash
kubectl -n velero get pods
velero backup-location get
```

The BSL should show as `Available`. If it stays `Unavailable`, the cause is almost always the endpoint, the credentials or the CA.

!!! warning "Depends on version"
    Velero changes flags and behaviors between minor versions: `--use-node-agent` replaced `--use-restic`, CSI support lived in a separate plugin before being merged, and some versions require `--features=EnableCSI`. Read the release notes for the version you install and check `velero install --help`.

## Backups, schedules and restore

A backup of one namespace, with its volumes according to the default configuration:

```bash
velero backup create app-prod-manual --include-namespaces app-prod
velero backup describe app-prod-manual --details
velero backup logs app-prod-manual
```

`describe --details` shows the phase (`Completed`, `PartiallyFailed`, `Failed`), the number of resources and, with `--details`, the volumes copied. `logs` shows the detail of what failed. A `PartiallyFailed` backup **is not a good backup**: something was not copied, and it is usually exactly what matters.

To schedule recurring copies, a `schedule` with cron and retention via `--ttl`:

```bash
velero schedule create app-prod-daily \
  --schedule="0 3 * * *" \
  --include-namespaces app-prod \
  --ttl 720h0m0s
velero schedule get
velero backup get
```

`--ttl` is the backup's lifetime: after that time, Velero deletes it from the bucket. It is your retention policy and applies per schedule, so you can have a daily schedule with a short TTL and a weekly one with a long TTL (a simple version of GFS). Backups created by a schedule are named after the schedule plus a timestamp.

To restore:

```bash
velero restore create --from-backup app-prod-daily-<timestamp>
velero restore describe <restore-name>
velero restore logs <restore-name>
```

Behaviors that surprise people:

- **It doesn't overwrite what already exists.** If the resource is in the cluster, Velero skips it and warns in the logs. To recover a modified object you must delete it first.
- **If the cluster uses GitOps**, restoring objects with Velero competes with the controller: Argo CD will sync them back against Git. Restore only the data (volumes and resources not in Git) and leave the manifests to Argo CD.

## Volumes: CSI snapshots or file copy

Velero has two mechanisms for a PV's data, with different consequences.

| Aspect | CSI snapshot | File System Backup (Kopia) |
|---|---|---|
| What it does | Asks the CSI driver for a `VolumeSnapshot` of the PV | A node agent pod reads the mounted volume's files and uploads them to the bucket |
| Where the data ends up | In the storage backend, not in the bucket | In the bucket, encrypted and deduplicated |
| Speed | Seconds: it is a backend operation | Proportional to the volume; the first pass is the slow one |
| Survives losing the backend | **No** (equivalent to a ZFS snapshot, not a copy) | **Yes**: the data is elsewhere |
| Requirements | CSI driver with snapshot support and a `VolumeSnapshotClass`; see [Kubernetes CSI](../storage/kubernetes_csi.md) | Any volume a pod can mount; `hostPath` and NFS included |
| Consistency | Block level: crash-consistent, not application-consistent | File level with the app running: may see half-written files |

The consequence for 3-2-1 is clear: a bare CSI snapshot is the first line of defense, not a copy. If the backend (the Ceph pool, the NFS server) disappears, the snapshots go with it. For the data to reach the bucket there are two paths: File System Backup, or CSI snapshot data movement (`--snapshot-move-data` in recent versions), which uploads the snapshot's contents to the backup store.

File System Backup is enabled per volume by annotating the pod, or for all of them with a flag:

```bash
# Per pod: list of volumes to copy
kubectl -n app-prod annotate pod/postgres-0 backup.velero.io/backup-volumes=data

# For all volumes in the backup
velero backup create app-prod-fs \
  --include-namespaces app-prod \
  --default-volumes-to-fs-backup
```

!!! warning "Depends on version"
    File System Backup used to be called the Restic integration (`--use-restic`, `--default-volumes-to-restic`). In recent versions the default engine is Kopia and the flags use `fs-backup` or `node-agent`; in older versions the old names coexist. If you read tutorials with `restic` in Velero's flags, they predate the change. Check `velero backup create --help` and the value of `--uploader-type` in your version.

## Consistency: pre and post hooks

A snapshot or file copy of a volume with a database writing to it captures an arbitrary instant: it may give a volume PostgreSQL can recover from a crash (crash-consistent) or, worse, files from different moments. There are three strategies, from most to least recommended for databases:

1. **Application-level logical backup** (`pg_dump`, `mysqldump`) in a CronJob that writes to a volume or to the bucket, with Velero backing up the result. It is independent of the volume engine and restorable on another version.
2. **Velero hooks** that freeze or prepare the application before the snapshot and release it afterwards.
3. **Accepting crash consistency**, which works with engines designed to recover from a cut (PostgreSQL, MySQL/InnoDB) but is not a formal guarantee.

Hooks are declared as pod annotations. An example with `fsfreeze` (the pattern Velero's own documentation uses):

```yaml
metadata:
  annotations:
    pre.hook.backup.velero.io/container: fsfreeze
    pre.hook.backup.velero.io/command: '["/sbin/fsfreeze", "--freeze", "/var/lib/postgresql/data"]'
    post.hook.backup.velero.io/container: fsfreeze
    post.hook.backup.velero.io/command: '["/sbin/fsfreeze", "--unfreeze", "/var/lib/postgresql/data"]'
```

`fsfreeze` needs a privileged container sharing the volume, normally a sidecar; keep that in mind with the namespace's security policies (see [Kubernetes Security](../cybersecurity/kubernetes_security.md)). A failing `pre` hook can, depending on its configuration, abort the backup or be ignored: review the hook's error field and the backup logs. With a database operator (CloudNativePG and similar), its native backup mechanism is usually better than a hook.

## Testing the restore

A backup that has never been restored is a hypothesis. Two tests, from cheapest to most expensive:

**Same cluster, another namespace.** Restore the backup renaming the namespace and check that the application starts and the data is there:

```bash
velero restore create restore-test \
  --from-backup app-prod-daily-<timestamp> \
  --namespace-mappings app-prod:app-prod-restore
```

Beware of what isn't namespaced: an Ingress with the same host or a LoadBalancer Service can clash with production. Review what gets restored before letting it receive traffic.

**Another cluster.** This is the test that actually validates the disaster. On a clean cluster (a VM with k3s is enough), install Velero pointing at the **same bucket** but with the BSL read-only, so the test cannot delete or modify real backups:

```bash
velero backup-location create production-ro \
  --provider aws \
  --bucket velero-backups \
  --config region=minio,s3ForcePathStyle=true,s3Url=https://minio.example.lan:9000 \
  --access-mode=ReadOnly
velero backup get
velero restore create --from-backup <production-backup>
```

This also checks what is most often forgotten: that the bucket's credentials and endpoint are **documented outside the cluster**. If they only lived in a Secret of the cluster that died, there is no restore. Time the test: it is your real RTO. The clean cluster must have the same StorageClass (or a StorageClass map in a Velero ConfigMap) for the PVCs to bind.

## Fit with the 3-2-1 rule

Applying the logic of [3-2-1 Backup Strategy](strategy_321.md) to a cluster:

| Element | Counts as a copy? | Why |
|---|---|---|
| Live data on the PVs | It is copy 1 (production) | It is the source |
| CSI snapshot on the same backend | **No**, it is a first line of defense | Dies with the pool or the NFS server |
| etcd snapshot on the control-plane node | **No** | Dies with the node |
| MinIO bucket **inside** the protected cluster | **No** | If the cluster falls, the bucket falls |
| MinIO bucket on another host with Velero and etcd snapshots | **Yes**, it is copy 2 | Another device, another failure domain |
| Bucket replica to another site (MinIO replication, `rclone`, restic over the bucket) | **Yes**, it is the off-site copy 3 | Another physical and administrative location |

The full pattern: Velero and the etcd snapshots write to a MinIO running outside the cluster (copy 2), and that bucket is replicated to an external destination with different credentials (copy 3). The "1 off-site" breaks easily: if Velero's credentials can delete from the bucket and the cluster is compromised, the attacker deletes the backups. Use minimum-permission credentials and, for the remote copy, immutability as explained in [Secure Backup](../cybersecurity/backup_seguro.md). Watch the interaction: Velero's TTL deletes expired backups, which clashes with a bucket under Object Lock; decide which component governs retention and verify the behavior in your version.

Keys count as in any backup: the Kopia repository password and the bucket credentials must exist outside the cluster. A perfect backup with the key inside the lost cluster is a lost backup.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| The BSL stays `Unavailable` | Wrong endpoint, credentials or CA; missing `s3ForcePathStyle=true` with MinIO | Check `velero backup-location get` and the Velero pod logs; test the endpoint with `mc` or `aws s3` from a pod |
| The backup ends `PartiallyFailed` | A hook failed, a volume could not be copied or an RBAC permission is missing | `velero backup describe --details` and `velero backup logs`; treat it as an invalid backup until fixed |
| PVCs are not copied although the backup is `Completed` | No `VolumeSnapshotClass` and File System Backup not enabled | Annotate the pods or use `--default-volumes-to-fs-backup`; check that the node agent is running |
| The restore skips the resources and does nothing | The resources already exist in the cluster | Delete the objects first, or restore into another namespace with `--namespace-mappings` |
| The restored PVC stays `Pending` | The backup's StorageClass doesn't exist in the target cluster | Create the StorageClass or map it with a Velero StorageClass-change ConfigMap |
| The restore brings a corrupt database | File copy with no hook or quiesce | Logical backup (`pg_dump`) or freeze hooks; see the consistency section |
| Restoring etcd on a single member breaks the cluster | The restored member contradicts the rest | Restore on all members in a coordinated way, or rebuild the remaining members |
| Argo CD reverts what Velero just restored | Both manage the same objects | Restore only data with Velero and leave the manifests to Argo CD, or pause sync during the test |

## Best practices

- **GitOps for state, Velero for data.** What is in Git needs no object backup; what isn't, does.
- **Back up the secrets key** (SOPS, Sealed Secrets) outside the cluster, together with the control-plane PKI.
- **The backup store, outside the cluster.** A MinIO inside the protected cluster is not a copy.
- **A CSI snapshot is not a copy.** Use it for speed; add File System Backup or data movement so the data reaches another failure domain.
- **Explicit consistency for databases**: logical backup or hooks. Don't assume the snapshot is good.
- **A `PartiallyFailed` backup is a failure.** Alert on it just like on a backup that doesn't run.
- **Minimum, rotated credentials** for Velero, without delete permission if the destination supports immutability.
- **Restore for real, on another cluster, with a read-only BSL,** and time it. Document the procedure outside the cluster.

## References

- [3-2-1 Backup Strategy](strategy_321.md) · [Restic and Borg](restic_borg.md) · [Proxmox Backup Server](pbs.md)
- [Kubernetes CSI](../storage/kubernetes_csi.md) · [Kubernetes base](../kubernetes/kubernetes_base.md) · [Probes](../kubernetes/probes.md)
- [Argo CD](../cicd/argocd.md) · [Secrets in GitOps](../cybersecurity/secrets_gitops.md)
- [Secure Backup: encryption, immutability and testing](../cybersecurity/backup_seguro.md) · [Kubernetes Security](../cybersecurity/kubernetes_security.md)
- [Velero: official documentation](https://velero.io/docs/)
- [Kubernetes: operating an etcd cluster](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
- [K3s: backup and restore](https://docs.k3s.io/datastore/backup-restore)
