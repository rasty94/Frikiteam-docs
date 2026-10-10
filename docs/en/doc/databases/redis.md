---
title: "Redis: High Performance Cache"
description: "Deploy and operate Redis on your own infrastructure: container with a volume, RDB and AOF persistence, memory limit and eviction policy, ACL access control, backups and diagnostics with redis-cli. Includes the license change and Valkey."
keywords: "redis, valkey, cache, rdb, aof, maxmemory, eviction, acl, redis-cli, persistence, containers, systemd, backup"
tags: ['databases']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 20 min
category: Databases
status: published
last_reviewed: 2026-10-10
prerequisites:
  - "Docker or Podman installed"
  - "[Docker Base](../docker/docker_base.md)"
  - "Basic networking and systemd"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Redis: High Performance Cache

## The problem

You put Redis in front of the application with `docker run redis`, everything flies, and weeks later three surprises show up. You restart the container and the cache is gone (you never mounted a volume). One day the process dies without warning because the server ran out of memory (nobody set `maxmemory`). And a network scan finds that port 6379 answers anyone, with no password, because you published it on all interfaces.

Redis is easy to start and easy to leave badly configured. This page covers what to decide before putting it in production on your own infrastructure: where the data lives, how much memory it can use, what happens when it fills up, who can connect and how it recovers after a failure.

!!! note "What this covers and what it does not"
    This page covers a single, well-operated instance. High availability (Sentinel, Cluster) is out of scope. For running containers as services see [Podman Quadlet](../docker/quadlets.md) and [Docker Base](../docker/docker_base.md).

## 📋 Table of Contents

- [License and Valkey](#license-and-valkey)
- [Quick deployment](#quick-deployment)
- [Persistent deployment](#persistent-deployment)
- [Persistence: RDB and AOF](#persistence-rdb-and-aof)
- [Memory and eviction policy](#memory-and-eviction-policy)
- [Security and access control](#security-and-access-control)
- [Operating with redis-cli](#operating-with-redis-cli)
- [As a systemd service](#as-a-systemd-service)
- [Backups and restore](#backups-and-restore)
- [Common use cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## License and Valkey

Redis is an in-memory data structure store, used as a database, cache and message broker. For years it was BSD-licensed software. The project later moved to source-available licenses (not OSI-approved) and, afterwards, added an open source license again as an option in later versions.

In reaction to that change, the Linux Foundation backed **Valkey**, a community-maintained fork of Redis under the BSD license. Valkey keeps the protocol, the commands and the data files, so `redis-cli`, clients and the configurations on this page work the same.

!!! warning "Check the license of the version you deploy"
    The license depends on the Redis version. Before packaging an image for a customer or a product, read the license file of that specific version. If you need an unambiguous permissive license, Valkey is the direct alternative. Compatibility is very high, but it is not guaranteed for new features: test your application against the version you pick.

## Quick deployment

For a local test:

```bash
docker run --name my-redis -d -p 127.0.0.1:6379:6379 redis:7-alpine
```

This container is for learning, not for production: the data dies with it and there is no memory limit. Note that the port is published only on `127.0.0.1`; without that prefix Docker would open it on all interfaces and, on top of that, bypass the host firewall rules.

!!! warning "Pin the image version"
    `redis:alpine` or `latest` change major version without warning. Pin a specific tag (such as `7-alpine`) and upgrade deliberately, reading the release notes first.

## Persistent deployment

A reasonable `compose.yaml` for an internal service: password from an environment variable, a volume for the data and the port bound to the host's private IP.

```yaml
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command:
      - redis-server
      - --appendonly
      - "yes"
      - --maxmemory
      - 512mb
      - --maxmemory-policy
      - allkeys-lru
      - --requirepass
      - ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "10.0.0.5:6379:6379"
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a \"$$REDIS_PASSWORD\" ping | grep PONG"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  redis_data:
```

The password goes in a `.env` file next to the compose file, with `600` permissions. If the app runs in the same Compose network, do not even publish the port: the other services reach it by the name `redis`.

!!! tip "Password in the healthcheck"
    The healthcheck uses `$$REDIS_PASSWORD` so Compose does not substitute it. For it to exist inside the container, add `environment: REDIS_PASSWORD: ${REDIS_PASSWORD}` to the service. With ACLs (see below) you can create a user that can only run `PING`.

## Persistence: RDB and AOF

Redis keeps everything in memory and offers two durability mechanisms, which can be combined:

| Mode | What it does | Advantage | Cost |
| --- | --- | --- | --- |
| **RDB** | Binary snapshot every so often or after a number of changes | Compact file, fast startup, easy to copy | You lose what was written since the last snapshot |
| **AOF** | Logs every write to a file that is replayed on startup | Minimal loss (by default, up to one second) | Bigger file, slower startup |
| **None** | Memory only | Maximum performance | Everything is lost on restart |

Usual configuration in `redis.conf`:

```conf
# RDB: snapshot if >=1 change in 1 h, >=100 in 5 min or >=10000 in 1 min
save 3600 1 300 100 60 10000

# AOF: log every write, sync to disk every second
appendonly yes
appendfsync everysec

# Data directory (the volume)
dir /data
```

`appendfsync everysec` is the usual trade-off. `always` syncs on every write and is much slower; `no` leaves the decision to the operating system.

Choose according to the role of Redis. If it is **only a cache**, persistence is unnecessary: disable it with `save ""` and `appendonly no`, and accept that it starts empty. If it holds **sessions or queues** you do not want to lose, enable AOF and keep RDB as a periodic copy for backups.

!!! warning "Persisting is not backing up"
    AOF and RDB protect against restarts, not against deletions, corruption or losing the disk. Backup is a different matter; see [Backups and restore](#backups-and-restore).

## Memory and eviction policy

Redis keeps everything in RAM. With no limit, it grows until the kernel kills the process (OOM killer). Always set `maxmemory` below the available RAM: leave room for the system, the buffers and the cost of copying memory when taking snapshots.

```conf
maxmemory 512mb
maxmemory-policy allkeys-lru
```

When the limit is reached, the policy decides what happens:

| Policy | Behavior | When to use it |
| --- | --- | --- |
| `noeviction` | Rejects writes with an error | Redis as a database: you prefer an error to losing data |
| `allkeys-lru` | Evicts the least recently used keys | Pure cache, the most common option |
| `allkeys-lfu` | Evicts the least frequently used keys | Cache with very popular, stable keys |
| `volatile-lru` | Evicts only keys with an expiry (TTL) | Mix of cache and permanent data |
| `volatile-ttl` | Evicts first the keys that expire soonest | Priority by remaining lifetime |

`volatile-*` only acts on keys with a TTL: if none has one, it behaves like `noeviction` and writes fail. Use `allkeys-*` for a cache and set a TTL on whatever you cache.

On the host, `vm.overcommit_memory=1` in `sysctl` is advisable; without it, the `fork` used for snapshots can fail when free memory is low. Redis warns about this in its logs at startup.

## Security and access control

A Redis exposed without authentication is a common entry point in incidents. Three layers, from the outside in:

1. **Network.** With `bind` you limit the interfaces it listens on (`bind 127.0.0.1 10.0.0.5`). In containers, `bind` inside the image does not replace publishing the port only on the desired IP. Close 6379 in the firewall except for the clients.
2. **Authentication.** `requirepass` sets a single password. It is the bare minimum.
3. **ACLs.** Users with specific permissions, better than sharing an administrator password.

Example user for an application limited to its own keys, without dangerous commands:

```bash
redis-cli ACL SETUSER app on '>change-this-key' '~app:*' +@read +@write -@dangerous
redis-cli ACL LIST
```

The `app` user can read and write only keys prefixed with `app:` and cannot run commands such as `FLUSHALL`, `CONFIG` or `KEYS`. For users to survive a restart, define them in the configuration file or in an `aclfile`, not only with `ACL SETUSER`.

!!! warning "Avoid the password on the command line"
    `redis-cli -a key` leaves the password in the history and the process list, and prints a warning. Use the `REDISCLI_AUTH` environment variable, or run `AUTH` inside the session.

Redis does not encrypt traffic by default. If it crosses untrusted networks, enable TLS in Redis or put it behind a VPN such as [WireGuard](../linux/wireguard.md).

## Operating with redis-cli

Daily checks, in order of use:

```bash
redis-cli ping                       # answers PONG if alive
redis-cli INFO memory                # used_memory, maxmemory, fragmentation
redis-cli INFO stats                 # evicted_keys, keyspace_hits/misses
redis-cli INFO persistence           # state of the last RDB and of the AOF
redis-cli DBSIZE                     # number of keys
redis-cli SLOWLOG GET 10             # the last 10 slow commands
redis-cli --latency                  # live measured latency
redis-cli --bigkeys                  # looks for the biggest keys
redis-cli MEMORY USAGE app:session:1 # bytes of a specific key
```

Reading the key metrics, in prose:

- A growing `evicted_keys` means `maxmemory` is in use and keys are being evicted. It is normal in a cache, serious in a database.
- The ratio between `keyspace_hits` and `keyspace_misses` measures cache effectiveness. If almost everything is a miss, the TTL is too short or the wrong things are being cached.
- A `mem_fragmentation_ratio` well above 1 indicates reserved memory that Redis does not use.

To walk through keys, use `SCAN`, never `KEYS *`: the latter blocks the server while it traverses the whole keyspace. Redis runs commands on a single thread, so one slow command stalls every client.

```bash
redis-cli --scan --pattern 'app:session:*' | head
```

Changes made with `CONFIG SET` apply instantly, but are lost on restart unless you save them with `CONFIG REWRITE` or carry them into the configuration file.

## As a systemd service

If you prefer the container to be the service, a Podman Quadlet file (details in [Podman Quadlet](../docker/quadlets.md)) avoids writing the unit by hand:

```ini
# ~/.config/containers/systemd/redis.container
[Unit]
Description=Redis

[Container]
Image=docker.io/library/redis:7-alpine
Exec=redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
Volume=redis-data.volume:/data
PublishPort=127.0.0.1:6379:6379
HealthCmd=redis-cli ping
HealthInterval=10s

[Service]
Restart=always

[Install]
WantedBy=default.target
```

```ini
# ~/.config/containers/systemd/redis-data.volume
[Volume]
```

After a `systemctl --user daemon-reload` the `redis.service` service appears. Logs are read with `journalctl --user -u redis`. With Docker, `restart: unless-stopped` in Compose plays the same role.

## Backups and restore

The usual strategy: generate a consistent RDB snapshot and copy it off the host.

```bash
redis-cli BGSAVE                     # background snapshot
redis-cli LASTSAVE                   # timestamp of the last successful save
docker cp my-redis:/data/dump.rdb ./redis-$(date +%F).rdb
```

`BGSAVE` is asynchronous: wait for `LASTSAVE` to change before copying the file, or you will copy an older one. With AOF enabled, copy the whole data directory with Redis stopped, or use the RDB snapshot.

To restore: stop Redis, replace `dump.rdb` in the volume with the copy, check that `appendonly` is not enabled with an old AOF that would override it, and start again. If Redis has AOF enabled, **it loads the AOF and not the RDB**; restoring an RDB with AOF on and an empty AOF gives an empty database. If the AOF is corrupted by a power cut, the `redis-check-aof` tool diagnoses it and can repair the truncated tail.

A backup that has never been restored is an assumption. Test the restore on another machine now and then. For encryption, rotation and off-site copies, apply what is described in [Secure Backup](../cybersecurity/backup_seguro.md).

## Common use cases

1.  **Session cache:** store user tokens with a TTL.
2.  **Task queue:** backend for Celery or BullMQ. Here AOF and `noeviction` are advisable.
3.  **Leaderboard:** use of Sorted Sets (`ZADD`, `ZRANGE`).
4.  **Rate limiting:** counters with `INCR` and `EXPIRE`.
5.  **Light messaging:** Pub/Sub and Streams, with no delivery guarantees in Pub/Sub.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Data disappears when the container is recreated | No volume on `/data` or persistence is off | Mount a volume and enable `appendonly yes` |
| Error `OOM command not allowed when used memory > 'maxmemory'` | `noeviction` policy (or `volatile-*` without TTL) with memory full | Switch to `allkeys-lru`, set a TTL or raise `maxmemory` |
| The container dies with no apparent error | The kernel killed it for lack of memory | Set `maxmemory` below the container and host limit |
| `NOAUTH Authentication required` | The client is missing the password | Use `REDISCLI_AUTH` or `AUTH` in the session |
| `DENIED Redis is running in protected mode` | External connection without a password and without an explicit `bind` | Define `requirepass` and `bind`; do not simply disable protected mode |
| Snapshots or AOF rewrite fail | Little free memory for the `fork` | Enable `vm.overcommit_memory=1` and leave RAM headroom |
| Latency spikes | Slow commands (`KEYS`, huge keys) or the disk with AOF | Check `SLOWLOG GET`, use `SCAN` and look at `--bigkeys` |
| Very slow startup | Very large AOF | Check the automatic rewrite or combine with RDB |
| After restoring, the database is empty | Active AOF ignores the restored RDB | Restore the AOF, or disable AOF on the first start |

## Best practices

1. Always set `maxmemory` and choose the policy by role: `allkeys-lru` for cache, `noeviction` for data.
2. Pin the image version and upgrade deliberately.
3. Never publish 6379 to the Internet; bind the port to a private IP or do not publish it.
4. Use ACLs with one user per application and minimal permissions.
5. Keep the password in a `600` file or a secrets manager, not on the command line.
6. Set a TTL on everything you cache.
7. Monitor `used_memory`, `evicted_keys` and the hit rate.
8. Back up off the host and test the restore.
9. Avoid `KEYS`, `FLUSHALL` and `DEBUG` in production.
10. Review the version license and consider Valkey if it matters to you.

## References

- [Official Redis documentation](https://redis.io/docs/)
- [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- [Redis ACL](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/)
- [Valkey](https://valkey.io/)
- [Docker Base](../docker/docker_base.md)
- [Podman Quadlet](../docker/quadlets.md)
- [Secure Backup](../cybersecurity/backup_seguro.md)
