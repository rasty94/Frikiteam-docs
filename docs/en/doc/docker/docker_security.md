---
title: "Docker — Security: hardening, secrets and scanning"
description: "Hardening Docker images and containers: why the daemon is root-equivalent, non-root users, capabilities, read-only filesystems, no-new-privileges, resource limits, seccomp/AppArmor, keeping secrets out of images, scanning with Trivy and publishing ports safely."
keywords: "docker, security, hardening, containers, capabilities, seccomp, apparmor, no-new-privileges, read-only, secrets, trivy, scanning, cosign, dockerfile"
tags: ['docker', 'containers', 'hardening', 'cybersecurity']
updated: 2026-09-02
difficulty: intermediate
estimated_time: 25 min
category: Containers
status: published
last_reviewed: 2026-09-02
prerequisites:
  - "[Docker — Basics](docker_base.md)"
  - "Intermediate Linux (users, permissions, processes)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Docker — Security: hardening, secrets and scanning

## The problem

A container is not a virtual machine. It is a host process with namespaces, cgroups and a few filters on top. Everything that separates "a compromised application" from "a compromised host" is a set of options **you** turn on: nearly all of them are off by default, because Docker's defaults optimise for things starting on the first try. The usual result is a container running as root, with the capabilities Docker grants by default, a writable filesystem, no memory limits, the database password in an environment variable visible through `docker inspect`, and the port published on every interface of the machine. Each of those is a one-line fix.

!!! note "What this covers and what it doesn't"
    This page is about **hardening images and containers** with the default runtime (`runc`). The daemonless privilege model lives in [Rootless Podman](podman_rootless.md); kernel isolation with gVisor or Kata lives in [Docker — Runtime Security](docker_runtime_security.md). They are complementary, not alternatives.

## 📋 Table of Contents

- [The daemon is root-equivalent](#the-daemon-is-root-equivalent)
- [Non-root user in the image](#non-root-user-in-the-image)
- [Capabilities: drop all, add back only what is needed](#capabilities-drop-all-add-back-only-what-is-needed)
- [Read-only filesystem](#read-only-filesystem)
- [no-new-privileges](#no-new-privileges)
- [Resource limits](#resource-limits)
- [seccomp and AppArmor](#seccomp-and-apparmor)
- [Secrets: what never goes into the image](#secrets-what-never-goes-into-the-image)
- [Minimal base images and multi-stage](#minimal-base-images-and-multi-stage)
- [Scanning with Trivy](#scanning-with-trivy)
- [Signing and provenance](#signing-and-provenance)
- [Network: where you publish ports](#network-where-you-publish-ports)
- [Troubleshooting](#troubleshooting)
- [Checklist](#checklist)
- [Related links](#related-links)

## The daemon is root-equivalent

`dockerd` runs as root and is the parent of every container. Anyone who can talk to its socket can ask it to do anything **as root**, including mounting the host filesystem:

```bash
docker run -it -v /:/host alpine chroot /host sh
```

That command exploits nothing: it is a documented feature. Two consequences are worth internalising. First, **being in the `docker` group is equivalent to passwordless `sudo`**; that is not rhetorical shorthand, the command above proves it, so audit that group the way you audit administrator access. Second, **mounting `/var/run/docker.sock` inside a container hands it that same power**: it is the pattern used by CI agents, automatic updaters and container dashboards, and every one of them is effectively root on the host.

If a tool genuinely needs to talk to Docker, the reasonable ways out are a **socket proxy** exposing only the endpoints it needs, mounting the socket `:ro` while knowing that protects very little — read-only affects the file, not the API operations — or changing engines: with [rootless Podman](podman_rootless.md) there is no privileged socket to mount.

!!! tip "Rootless Docker"
    Docker also has a rootless mode where the daemon runs under your user, with limitations similar to rootless Podman (privileged ports, some network and storage drivers). Check the documentation for your version before migrating a production host.

## Non-root user in the image

With no `USER` instruction, the main process runs as root **inside** the container. With a rootful daemon and no `userns-remap`, that UID 0 is the host's UID 0: on a mounted host directory, it is real root.

```dockerfile
# syntax=docker/dockerfile:1
FROM alpine:3.20
RUN addgroup -g 10001 app && \
    adduser -D -u 10001 -G app app
COPY --chown=10001:10001 app /usr/local/bin/app
USER 10001:10001
ENTRYPOINT ["/usr/local/bin/app"]
```

Four details make the difference: use **numeric UID and GID** in `USER` rather than a name, because Kubernetes can check `runAsNonRoot` against a number but not against a name it would have to resolve inside the image; pick a **high UID (>10000)** so you don't collide with real host users on shared volumes; prefer **`COPY --chown`** over a later `RUN chown -R`, which duplicates the files in a new layer; and put **everything that installs packages before the `USER` line**, because after it the build is no longer root.

Verify what you built, which is not the same as what you thought you built:

{% raw %}

```bash
docker run --rm --entrypoint id myimage:1.0
docker inspect -f '{{.Config.User}}' myimage:1.0
```

{% endraw %}

If the second command returns nothing, the image runs as root no matter what the README claims. At runtime you can force it with `--user 10001:10001`, which is useful for third-party images you cannot rebuild.

## Capabilities: drop all, add back only what is needed

Root inside a container is not full root: Docker keeps a subset of capabilities (`CHOWN`, `SETUID`, `NET_RAW`, `KILL`…) and drops the most dangerous ones, such as `SYS_ADMIN`. That subset is still far more than a web application needs.

```bash
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE nginx:alpine
```

The rule is always the same: **`--cap-drop=ALL`, then add back only what breaks**. Most services running with a non-root `USER` on high ports need none at all.

| Capability | When it is genuinely needed |
|---|---|
| `NET_BIND_SERVICE` | Listening on a port `<1024` |
| `CHOWN`, `FOWNER`, `DAC_OVERRIDE` | Entrypoints that fix volume permissions at startup |
| `SETUID`, `SETGID` | The process drops privileges by itself after starting |
| `NET_RAW` | `ping`, `traceroute` and raw sockets |
| `SYS_ADMIN` | Almost never; it lifts a large part of the isolation |

`--privileged` is not "a few more permissions": it grants every capability plus access to the host's devices, disabling most of the barriers. If something asks for it, look first for the specific `--cap-add` or `--device` it actually needs.

## Read-only filesystem

If the attacker cannot write, they cannot drop a binary, install a cron job, or modify your application in place.

```bash
docker run --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --tmpfs /run:rw,noexec,nosuid,size=8m \
  -v data:/var/lib/app \
  myimage:1.0
```

`--read-only` applies to the container's writable layer; volumes and `--tmpfs` mounts stay writable, which is exactly what you want. `noexec` and `nosuid` kill the classic trick of downloading something into `/tmp` and running it, and `size` stops a runaway process from filling the host's RAM. The awkward part is finding out which directories the application needs to write: start it read-only, see where it fails and add one `--tmpfs` per directory. Usual suspects: `/tmp`, `/run`, `/var/run`, caches under `/var/cache` and interpreter session directories.

## no-new-privileges

This flag stops a process from gaining privileges by executing a `setuid` binary. Without it, a `sudo` or a badly set SUID bit inside the image is a direct local escalation path.

```bash
docker run --security-opt no-new-privileges:true myimage:1.0
```

It is one of the cheapest options on this page: a well-built image never needs to escalate privileges at runtime, so it breaks almost nothing. If something stops working when you turn it on, that "something" is exactly what you wanted to know about. In Compose the equivalent key is `security_opt: ["no-new-privileges:true"]`, and it pairs naturally with `user:`, `read_only:`, `cap_drop:` and `tmpfs:`.

## Resource limits

Limits rarely appear on security checklists, yet they are the only defence against **one container taking down all the others**. Without `--memory`, runaway consumption — a bug, an enormous query, an attack — ends up invoking the host's OOM killer, which may kill entirely unrelated processes.

```bash
docker run --memory=512m --memory-swap=512m \
  --cpus=1.0 --pids-limit=200 \
  --ulimit nofile=1024:2048 myimage:1.0
```

Setting **`--memory-swap` to the same value as `--memory`** disables swap for that container: otherwise the limit becomes a RAM+swap limit and the process agonises on disk instead of dying quickly. **`--pids-limit`** stops fork bombs dead, accidental or not, and **`--ulimit nofile`** prevents exhausting the host's file descriptors. Pick the numbers by measuring real consumption under load and adding headroom: a limit that is too tight kills the service at the worst possible moment, and one that is too generous protects against nothing.

## seccomp and AppArmor

These two layers sit below capabilities: on system calls and on file access.

**seccomp** filters syscalls. Docker applies a default profile that blocks a set of dangerous calls and allows the rest, which is enough for the vast majority of applications. You can supply your own with `--security-opt seccomp=/path/profile.json`, though writing one from scratch is a project in itself: you have to enumerate every syscall used on any code path, startup and shutdown included. What matters day to day is the opposite, **not disabling it**: `--security-opt seccomp=unconfined` circulates on forums as a quick fix for odd errors, and what it does is remove the filter entirely. Before copying it, find out with `dmesg` or the host's audit log which specific syscall is being blocked.

**AppArmor** (Debian, Ubuntu, SUSE) or **SELinux** (Fedora, RHEL) restrict which files and capabilities the process can reach. On hosts with AppArmor enabled, Docker applies a `docker-default` profile to containers; with SELinux, labelling is what makes a volume without `:Z` return "Permission denied".

```bash
# Custom profile, previously loaded on the host with apparmor_parser
docker run --security-opt apparmor=my-profile myimage:1.0
# What a running container actually has applied
{% raw %}docker inspect -f '{{.AppArmorProfile}} {{json .HostConfig.SecurityOpt}}' mycontainer{% endraw %}
```

!!! warning "It depends on the host, not on the image"
    These profiles are applied by the daemon according to what the host kernel supports. The same image is confined differently on Ubuntu than on RHEL, and not at all on a host with no LSM enabled. Don't assume what you haven't verified on the specific machine.

## Secrets: what never goes into the image

An image is a stack of immutable layers: whatever appears in a layer is there forever, even if a later layer deletes it. These two patterns leak the secret to anyone who can `docker pull`, and build `ARG`s are no safer either, since they are recorded in the image history.

```dockerfile
# ❌ Stays in the metadata, visible through docker inspect
ENV DB_PASSWORD=s3cr3t
# ❌ Stays in the layer, even though the later rm "deletes" it
COPY .npmrc /root/.npmrc
RUN npm install && rm /root/.npmrc
```

The correct approach with BuildKit is to mount the secret only for that `RUN`, so it never reaches a layer:

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine
COPY package*.json ./
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm ci --omit=dev
```

```bash
docker build --secret id=npmrc,src=$HOME/.npmrc -t myimage:1.0 .
```

At **runtime**, environment variables are readable through `docker inspect`, in the environment of any process in the container and often in the startup logs. Prefer mounted files the application reads at startup (Docker Secrets in Swarm, a Kubernetes `Secret` mounted as a volume, or a file injected by your secret manager). The full treatment is in [Secrets Management](../cybersecurity/gestion_secretos.md) and, for GitOps, in [Secrets in GitOps](../cybersecurity/secrets_gitops.md).

How to audit an image that already exists:

{% raw %}

```bash
# Full command of each layer: this is where the telltale ARGs and COPYs show up
docker history --no-trunc --format '{{.CreatedBy}}' myimage:1.0
# Environment variables baked into the image
docker inspect -f '{{json .Config.Env}}' myimage:1.0
# Secret scanning over the image filesystem
trivy image --scanners secret myimage:1.0
```

{% endraw %}

!!! danger "A secret leaked in a published image is a burned secret"
    Rebuilding the image does not fix it: the old layer is still in the registry and in the cache of everyone who pulled it. The only real remedy is to **rotate the credential**. Deleting the tag is housekeeping, not mitigation.

## Minimal base images and multi-stage

Every installed package is attack surface and a potential CVE somebody will have to triage. A full-distribution base drags in a shell, a package manager and dozens of libraries your application never uses.

| Base | Note |
|---|---|
| `debian`, `ubuntu` | Comfortable to debug, lots of surface |
| `alpine` | Small; musl instead of glibc, watch out for glibc-linked binaries |
| `*-slim` (Debian) | Good middle ground when musl causes trouble |
| Distroless | Runtime only: no shell, no package manager |
| `scratch` | Static binaries only; no TLS certificates, no timezone data |

Multi-stage separates what you need to **build** from what you need to **run**: compiler, headers and development dependencies stay in the first stage.

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.22 AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /out/app ./cmd/app

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/app /app
USER nonroot:nonroot
ENTRYPOINT ["/app"]
```

With no shell inside, `docker exec ... sh` does not work: that is the price for it not working for whoever gets in uninvited either; to debug, use an ephemeral container sharing the namespaces of the one under investigation. Layer and cache techniques are in [Docker optimisation](docker_optimizations.md).

## Scanning with Trivy

[Trivy](https://trivy.dev/) walks the image layers, identifies the installed packages and cross-references them with vulnerability databases.

```bash
# What can be fixed today, without the background noise
trivy image --severity CRITICAL,HIGH --ignore-unfixed myregistry/myimage:1.0
# In CI: non-zero exit code when there are blocking findings
trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 myimage:1.0
# Report for further processing
trivy image --format json --output report.json myimage:1.0
```

The option that changes daily life the most is **`--ignore-unfixed`**: it filters out vulnerabilities with no patch available. Without it, a Debian-based image ships dozens of CVEs nobody can fix yet, and the team learns to ignore the whole report. **What to do with the results**, in this order:

1. **Is there a fixed version?** Rebuild against the updated base (`docker build --pull`). A good share of an image's CVEs disappear right there, without touching your code.
2. **Is the package yours?** Update the dependency in the lock file (`package-lock.json`, `go.sum`, `requirements.txt`) and rebuild.
3. **Is the vulnerability reachable?** A CVE in a component your container never executes is real but not urgent. Write the reasoning down; don't leave it in a chat message.
4. **Is there no patch?** Record it in `.trivyignore` **with a date and a reason**, and review it. An exception with no expiry is a permanent exception.

Scan at three moments: locally while you develop, in the pipeline as a quality gate, and **periodically against what is already deployed** — an image that was clean in March is not clean in September even though nobody touched it. The CI setup is in [CI Security Scanning](../cybersecurity/ci_security_scanning.md), and the continuous variant on Kubernetes in [Trivy Operator](../cybersecurity/trivy_operator.md).

## Signing and provenance

Scanning answers "does this image have known flaws?". Signing answers something else: **"is this image the one my pipeline built?"**. No scanner detects a compromised registry or an overwritten tag.

- **Signature**: a cryptographic signature bound to the image digest. Today's reference tool is [Cosign](https://docs.sigstore.dev/), from the Sigstore project, with key-based signing or *keyless* signing using an OIDC identity (the pipeline's own, for instance).
- **Provenance**: verifiable metadata about how the image was built — commit, builder, parameters — along the lines of the SLSA framework. BuildKit can generate provenance and SBOM attestations during the build.
- **Verification at deploy time**: a signature is only useful if something checks it before running. On Kubernetes, an admission controller with a policy; on a standalone host, an explicit step before `docker run`.

Referencing by digest is the prerequisite for all of the above and needs no new tooling: `docker pull myregistry/myimage@sha256:<digest>`. A tag can be reassigned, a digest cannot. The full signing, SBOM and verification flow is in [Supply Chain Security](../cybersecurity/supply_chain_security.md).

!!! note "Docker Content Trust"
    `DOCKER_CONTENT_TRUST=1` still exists and is based on Notary v1. The ecosystem has moved towards Sigstore/Cosign; if you are starting today, start there, and check what your registry supports before deciding.

## Network: where you publish ports

`-p 8080:80` publishes on **every** host interface: `0.0.0.0`. If the machine has a public IP, that port is on the Internet. It is the most common way to accidentally expose a database or an admin panel.

```bash
docker run -p 127.0.0.1:8080:80 nginx:alpine   # local only
docker run -p 8080:80 nginx:alpine             # every interface
docker ps --format 'table {% raw %}{{.Names}}\t{{.Ports}}{% endraw %}'
```

A database consumed only by another container does not need publishing at all: on a user-defined *bridge* network, containers reach each other by name. The operational rule is to publish only what serves external traffic and to put it behind a [reverse proxy](../traefik/traefik_base.md).

!!! danger "Docker and the host firewall"
    Docker manages its own `iptables`/`nftables` rules for port forwarding, and those rules can bypass a firewall configured through `ufw`: a published port stays reachable even though `ufw status` says it is denied. Always verify from **another machine**, not from the host. If you need real control over filtering, publish on `127.0.0.1` and let the reverse proxy be the only exposed service. See [nftables and fail2ban](../cybersecurity/nftables_fail2ban.md).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Permission denied` writing to a volume | The `USER` UID does not own the host directory | `chown` on the host to the image's UID, or `--user` with the right UID |
| `Read-only file system` at startup | The app writes to an unplanned directory | A `--tmpfs` for that directory, or a volume if the data must persist |
| `bind: permission denied` on port 80 with a non-root user | `NET_BIND_SERVICE` missing | `--cap-add=NET_BIND_SERVICE`, or listen high and map `-p 80:8080` |
| `Operation not permitted` on a syscall | seccomp profile or missing capability | Identify the syscall before loosening anything; add the specific capability, never `seccomp=unconfined` |
| Container dies with exit code 137 | OOM: it exceeded `--memory` | Measure real consumption and adjust; check for memory leaks |
| Everything breaks after adding `no-new-privileges` | The entrypoint uses `sudo`, `su` or a SUID binary | Rewrite the entrypoint so it doesn't escalate; it usually reveals a design problem |
| Trivy reports CVEs you cannot fix | Stale base or no upstream patch | `docker build --pull`; `--ignore-unfixed` to separate the actionable ones |
| An internal service is reachable from outside | Published on `0.0.0.0` | `-p 127.0.0.1:...`, or don't publish and use the internal network |
| `docker exec` fails on the new image | Distroless or `scratch` base: there is no shell | Debug with an ephemeral container sharing namespaces |

## Checklist

- [ ] No container with `--privileged` or with `/var/run/docker.sock` mounted without a written justification.
- [ ] The host's `docker` group treated and audited as administrator access.
- [ ] `USER` with a numeric non-root UID, verified with `docker run --entrypoint id`.
- [ ] `--cap-drop=ALL` plus, at most, the capabilities proven necessary.
- [ ] `--read-only` with the minimum `--tmpfs` mounts, using `noexec,nosuid` and a `size`.
- [ ] `--security-opt no-new-privileges:true` on every service.
- [ ] `--memory`, `--cpus` and `--pids-limit` with measured values, not guessed ones.
- [ ] Default seccomp profile active; no `seccomp=unconfined` left unanalysed.
- [ ] Zero secrets in `ENV`, `ARG` or layers; checked with `docker history` and `trivy --scanners secret`.
- [ ] Build secrets via `--mount=type=secret`; runtime secrets as files.
- [ ] Minimal base image and multi-stage, with no build toolchain in the final stage.
- [ ] `trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1` in the pipeline, plus periodic rescans of what is already deployed.
- [ ] Images referenced by digest in production.
- [ ] Ports published only where they should be, verified from another machine.
- [ ] Scheduled periodic rebuilds: the base ages even when your code does not.

## Related links

- [Docker — Basics](docker_base.md) · [Docker optimisation](docker_optimizations.md)
- [Rootless Podman](podman_rootless.md) — removing the root daemon from the threat model.
- [Docker — Runtime Security (gVisor/Kata)](docker_runtime_security.md) — kernel isolation.
- [Secrets Management](../cybersecurity/gestion_secretos.md) · [Supply Chain Security](../cybersecurity/supply_chain_security.md)
- [CI Security Scanning](../cybersecurity/ci_security_scanning.md) · [Trivy Operator](../cybersecurity/trivy_operator.md)
- [Linux Server Hardening](../cybersecurity/hardening_linux.md) — the host that carries all of the above.
- [Docker security (official documentation)](https://docs.docker.com/engine/security/) · [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
