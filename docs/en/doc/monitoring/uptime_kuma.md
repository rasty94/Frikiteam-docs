---
title: "Monitoring with Uptime Kuma"
description: "Deploy and operate self-hosted Uptime Kuma: container, reverse proxy, monitor types, notifications, status pages, Prometheus integration and backups."
keywords: "uptime kuma, monitoring, status pages, notifications, self-hosted, docker, reverse proxy, push monitor, backup"
tags: ['monitoring']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 14 min
category: Monitoring
status: published
last_reviewed: 2026-10-10
prerequisites:
  - "Docker or Podman with Compose"
  - "A reverse proxy with TLS ([Traefik](../traefik/traefik_base.md) or [HAProxy](../haproxy/haproxy_base.md))"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Monitoring with Uptime Kuma

## The problem

You find out a service is down when someone messages you. Building a full metrics stack just to know whether a website answers is disproportionate, and a `curl` in a cron job notifies nobody and keeps no history.

Uptime Kuma fills that gap: a single application with a web interface that periodically checks whether things respond, alerts you through the channel you prefer and publishes a status page. It does not replace internal metrics (CPU, latencies, traces), which are covered in the [observability stack](observability_stack.md); it answers one question: is it working, seen from the outside?

!!! note "Point of view"
    If Uptime Kuma runs on the same host as what it watches, a host outage takes both down and nobody is alerted. Place it on another machine, another network or even another provider.

## 📋 Table of Contents

- [Features](#features)
- [Docker deployment](#docker-deployment)
- [Behind a reverse proxy](#behind-a-reverse-proxy)
- [First steps](#first-steps)
- [Monitor types](#monitor-types)
- [Notifications](#notifications)
- [Status pages](#status-pages)
- [Prometheus integration](#prometheus-integration)
- [Backup and recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## Features

- Monitoring of HTTP(s), TCP, Ping, DNS, Push services and more.
- Notifications (Telegram, Discord, Slack, Email, etc.).
- Public status pages (Status Pages).
- TLS certificate expiry warnings on HTTPS monitors.
- Maintenance windows to silence planned alerts.
- Docker support: it deploys as a single container.

It is a Node.js application whose interface communicates over WebSocket. It keeps all its state (monitors, history, settings) in one data directory, which makes it trivial to move and back up.

## Docker deployment

The simplest way to deploy Uptime Kuma is with Docker. The image is `louislam/uptime-kuma`, the port is 3001 and the state lives in `/app/data`.

```yaml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    restart: unless-stopped
    volumes:
      - ./uptime-kuma-data:/app/data
    ports:
      - "127.0.0.1:3001:3001"
```

The port only listens on `127.0.0.1`: the reverse proxy publishes it. If you have no proxy and use it only on your local network, change it to `"3001:3001"`.

!!! warning "Version dependent"
    The `:1` tag follows the 1.x branch. A 2.x branch exists with storage changes (among them, support for external databases in addition to the local file) and its own migration. Do not switch branches blindly: back up the data directory and read the release notes before upgrading.

To monitor the host's Docker containers, the container needs access to the socket (`/var/run/docker.sock`), and that is equivalent to giving it control over the daemon. Use it only if you need it, read-only when possible, or prefer HTTP/TCP monitors that do not require the socket. To run it as a systemd service, see [Quadlets](../docker/quadlets.md).

## Behind a reverse proxy

The interface depends on WebSocket. A proxy that does not forward it produces the classic symptom: the login page loads and then stays on "connecting".

- **Traefik:** forwards WebSocket with no extra configuration. See [Traefik](../traefik/traefik_base.md).
- **HAProxy:** `http` mode handles it, but check the `timeout tunnel` values if connections drop. See [HAProxy](../haproxy/haproxy_base.md).

```yaml
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.kuma.rule=Host(`status.example.com`)"
      - "traefik.http.routers.kuma.tls=true"
      - "traefik.http.services.kuma.loadbalancer.server.port=3001"
```

The application settings include a trusted proxy option (*Settings → Reverse Proxy*) so Uptime Kuma reads the real client IP from the `X-Forwarded-*` headers. Enable it only when the proxy overwrites them.

## First steps

1. Open `http://yourserver:3001` (or the proxy's public URL).
2. Create the administrator user on first access. Until you do, anyone who reaches the URL can create it: do not expose the new instance to the Internet beforehand.
3. Under *Settings → Security* enable two-factor authentication (2FA) for the administrator.
4. Add your first monitor under "Add New Monitor".
5. Configure at least one notification channel before creating more monitors; a monitor with no alert is only good for looking at.

The main parameters of each monitor are the check interval (every how many seconds), the number of retries before marking it down and the retry interval. A single blip should not wake anyone up: one or two retries filter most network noise.

For planned work (updates, reboots) use a maintenance window instead of pausing monitors by hand: that way you do not forget to re-enable them and the history does not count that stop as an outage.

## Monitor types

| Type | What it checks | When to use it |
|---|---|---|
| HTTP(s) | Status code of a URL, with certificate validity | Websites and APIs |
| HTTP(s) with keyword | That the response contains (or not) a text | Pages that return 200 with an error inside |
| TCP Port | That a port accepts connections | Databases, SSH, non-HTTP services |
| Ping | ICMP reply from a host | Network and machine reachability |
| DNS | That a name resolves to the expected record | Detecting DNS failures or changes |
| Push | The application calls Uptime Kuma; if it stops, the alarm fires | Cron, backups, tasks with no port |
| Docker Container | Container state, via the Docker socket | Containers on the host itself |

The *Push* monitor reverses the direction and is the most useful for scheduled tasks: the monitor generates a URL with a token; the job calls it when it finishes successfully, and if the interval passes without receiving it the monitor is marked down. This is how you detect a backup that stopped running, something an active check would never see.

```bash
# At the end of the backup script, only if everything went well
curl -fsS "https://status.example.com/api/push/<token>?status=up&msg=OK" > /dev/null
```

The exact names of the types and the available options vary between versions; those in the table exist in the 1.x branch, but check the dropdown of your installation.

## Notifications

Under *Settings → Notifications* you define the channels and then attach them to each monitor. There are integrations for Telegram, Discord, Slack, SMTP email, generic webhooks and many more.

- Create one channel per destination and mark it *Default enabled* if you want every new monitor to use it.
- Use the test button when creating the channel: it confirms the alert arrives before you depend on it.
- It alerts on state changes (down and recovery), not on every failed check. A configurable periodic resend exists for long incidents.
- Combine two independent channels for critical things (for example email and Telegram): if the mail server is what goes down, the email alert does not arrive.

Channel credentials (bot tokens, SMTP passwords) are stored in the application data. Treat the volume and its copies as sensitive material.

## Status pages

A *status page* is a public view of a subset of monitors, with no login required.

1. Under "Status Pages" create a page with a title and a *slug*; it will be reachable under the `/status/<slug>` path.
2. Add monitor groups and order them; show only what matters to whoever is looking, not your internal infrastructure.
3. Optionally, assign a custom domain to the page and publish incidents with manual messages.

A page being public does not mean it should show host names, IPs or internal paths: use descriptive names ("Mail", "Web") instead of the technical monitor names.

## Prometheus integration

Uptime Kuma exposes a `/metrics` endpoint in Prometheus format with the state and latency of each monitor. It is protected: you access it with basic authentication using an application user and password or an API key created in the settings.

```yaml
scrape_configs:
  - job_name: uptime-kuma
    scheme: https
    metrics_path: /metrics
    basic_auth:
      username: ""
      password_file: /etc/prometheus/kuma_api_key
    static_configs:
      - targets: ["status.example.com"]
```

!!! warning "Version dependent"
    The metrics and the authentication format (API key as password with an empty username, or user credentials) depend on the version. Check on your instance what `/metrics` accepts before configuring Prometheus. Keep the key in a separate file (`password_file`) instead of putting it in the configuration in plain text.

With this you can graph availability in Grafana and alert from Alertmanager, reusing what is described in the [observability stack](observability_stack.md). If you do not need that level, Uptime Kuma's own notifications are enough.

## Backup and recovery

All the state is in the `/app/data` directory. In the 1.x branch the database is a SQLite file (`kuma.db`) inside that directory, along with auxiliary files.

- **Cold copy:** stop the container, copy the directory and start it again. It is the safest option because SQLite is not writing.
- **Hot copy:** copying `kuma.db` while the application writes may give an inconsistent file. Use SQLite's backup API or a snapshot of the volume or filesystem.

```bash
docker compose stop uptime-kuma
tar -czf uptime-kuma-$(date +%F).tar.gz uptime-kuma-data
docker compose start uptime-kuma
```

Ship the archive off the host with your usual backup tool (see [Restic and Borg](../backups/restic_borg.md)). To restore, stop the container, empty the data directory, extract the archive and start again.

The only thing you need to do to change machines is move that directory and bring up the same compose file. If you use the 2.x branch with an external database, back that database up too.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| The page loads but stays on "connecting" | The proxy does not forward WebSocket | Check the proxy's WebSocket configuration and timeouts |
| All monitors show down at the same time | Network or DNS failure on the Uptime Kuma host itself | Test outbound connectivity and DNS resolution from the container; place the instance on another network |
| HTTPS monitor down because of the certificate | Expired, self-signed or incomplete-chain certificate | Renew the certificate; for internal use only, use the ignore-TLS-errors option on that monitor |
| The monitor answers 200 but the site is broken | Check only by status code | Switch to a keyword monitor that validates the content |
| Notifications that do not arrive | Channel not attached to the monitor or wrong credentials | Use the test button; check the channel is enabled on the monitor |
| Monitors and settings are lost when recreating the container | No volume mounted at `/app/data` | Mount the volume and restore from the latest copy |
| Frequent false positives | Short interval and no retries | Increase retries and the check interval |
| Error reading Docker containers | The socket is not mounted or permissions are missing | Mount `/var/run/docker.sock` and weigh the risk before doing so |

## Best practices

- Run Uptime Kuma outside of what it monitors, or at least in a different failure domain.
- Pin the image tag and upgrade deliberately, with a prior copy of the volume.
- Use retries to filter noise and two alert channels for critical things.
- Monitor scheduled tasks with *Push* monitors, not only services with a port.
- Enable 2FA, do not expose the admin interface to the Internet and publish only the status page if needed.
- Do not mount the Docker socket unless you need it.
- Test restoring the backup at least once; an untested copy is not a copy.
- Add Uptime Kuma itself to an external monitor (another Kuma or a free service) to know if the watcher goes down.

## References

- [Uptime Kuma repository](https://github.com/louislam/uptime-kuma)
- [Uptime Kuma wiki](https://github.com/louislam/uptime-kuma/wiki)
- [Full observability stack](observability_stack.md)
- [Podman Quadlet](../docker/quadlets.md)
- [Keycloak](../identity/keycloak.md), a critical service to watch
