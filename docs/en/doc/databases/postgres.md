---
title: "PostgreSQL on Docker"
description: "Deploy and operate PostgreSQL in containers on your own infrastructure: Compose with secrets, roles and pg_hba.conf, memory and connection tuning, diagnostics with pg_stat_activity and EXPLAIN ANALYZE, pg_dump backups and major upgrades."
keywords: "postgresql, postgres, docker, compose, pg_dump, pg_restore, pg_hba.conf, shared_buffers, work_mem, max_connections, roles, explain analyze, pg_stat_activity, backup, quadlet"
tags: ['databases', 'docker']
updated: 2026-10-10
difficulty: intermediate
estimated_time: 21 min
category: Databases
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Docker or Podman installed"
  - "[Docker Base](../docker/docker_base.md)"
  - "Basic SQL"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# PostgreSQL on Docker

## The problem

You bring up PostgreSQL with a `docker-compose.yml` copied from a tutorial: user `postgres`, a plain-text password inside the file, port 5432 published and the application connecting as superuser. It works until it needs to be operated. One day the container runs out of free connections because every request opens a new one. Another day a query takes minutes and nobody knows which one. And the day you bump the image to the next major version, the container refuses to start with the old data.

PostgreSQL is the most advanced open source object-relational database management system and running it in containers simplifies deployment, but it does not remove operations. This page covers the basics: a sensible deployment, users with minimal permissions, the parameters that really matter, how to diagnose what is slow, backups you can actually restore and how to approach a major upgrade.

!!! note "What this covers and what it does not"
    This page covers a single instance. Replication, automatic failover and connection routing are in [PostgreSQL High Availability](postgresql_ha.md). To place the data on distributed storage see [PostgreSQL on Ceph](../storage/postgresql_ceph.md).

## 📋 Table of Contents

- [Deployment with Compose](#deployment-with-compose)
- [Initialization and data](#initialization-and-data)
- [Roles and permissions](#roles-and-permissions)
- [Network access and pg_hba.conf](#network-access-and-pg_hbaconf)
- [Parameter tuning](#parameter-tuning)
- [Diagnosing slow queries](#diagnosing-slow-queries)
- [Maintenance](#maintenance)
- [Backups and restore](#backups-and-restore)
- [Upgrading to a major version](#upgrading-to-a-major-version)
- [As a systemd service](#as-a-systemd-service)
- [High availability and storage](#high-availability-and-storage)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## Deployment with Compose

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD_FILE: /run/secrets/pg_password
      POSTGRES_DB: mydatabase
    secrets:
      - pg_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myuser -d mydatabase"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:

secrets:
  pg_password:
    file: ./pg_password.txt
```

What changes compared with the minimal version and why:

- **`POSTGRES_PASSWORD_FILE`** reads the password from a file mounted as a secret, so it does not show up in `docker inspect` or in the compose file. The `pg_password.txt` file must have `600` permissions and stay out of git.
- **Named volume** instead of `./pgdata`: avoids permission and ownership problems on the host directory.
- **Port on `127.0.0.1`**: if the application is in the same Compose network, publish nothing; it reaches the database by the name `db`. If you need external access, use the private IP and not `0.0.0.0`.
- **`pg_isready`** lets other services wait for the database to be ready with `depends_on` and `condition: service_healthy`.

!!! warning "Pin the major version and check the data path"
    Always use a tag with the major version (`16-alpine`, not `latest`). Also, the path where the image expects the data directory can vary between major versions of the image: check the image documentation for the version you deploy before mounting the volume.

To open an interactive session:

```bash
docker compose exec db psql -U myuser -d mydatabase
```

## Initialization and data

The image runs the `.sql`, `.sql.gz` and `.sh` files it finds in `/docker-entrypoint-initdb.d/`, in alphabetical order. It is the place to create roles, extensions and the initial schema.

```yaml
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./initdb:/docker-entrypoint-initdb.d:ro
```

A detail that causes many tickets: these scripts **only run the first time**, when the data directory is empty. If you change a script and restart, nothing happens. To repeat it in a test environment you have to delete the volume; in production, apply changes with migrations on the already-created database.

The data lives in the volume, not in the container. Recreating the container (`docker compose up -d` after changing the image) keeps the database; `docker compose down -v` deletes it together with the volume.

## Roles and permissions

The `POSTGRES_USER` user is a superuser. The application should not connect with it. Create one role per application with just the right permissions:

```sql
CREATE ROLE app LOGIN PASSWORD 'change-this-key';
CREATE DATABASE appdb OWNER app;
REVOKE CONNECT ON DATABASE appdb FROM PUBLIC;
GRANT CONNECT ON DATABASE appdb TO app;
```

For a read-only role (reports, Grafana, an analyst), connected to `appdb`:

```sql
CREATE ROLE reader LOGIN PASSWORD 'another-key';
GRANT USAGE ON SCHEMA public TO reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO reader;
```

The last command is the one people forget: without `ALTER DEFAULT PRIVILEGES`, tables created later will not be readable by `reader`. In `psql`, `\du` lists the roles and `\l` the databases with their owners. Change passwords with `ALTER ROLE app PASSWORD '...'`.

## Network access and pg_hba.conf

Two settings control who gets in: `listen_addresses` (which interfaces the server listens on) and `pg_hba.conf` (who may authenticate, from where and how). The official image listens on all interfaces *of the container*; the real exposure is decided by how you publish the port.

Each `pg_hba.conf` line has the format type, database, user, address and method. They are evaluated top to bottom and the first match wins:

```conf
# TYPE  DATABASE  USER    ADDRESS         METHOD
local   all       all                     scram-sha-256
host    appdb     app     10.0.0.0/24     scram-sha-256
host    all       all     0.0.0.0/0       reject
```

Use `scram-sha-256` and not `md5`, and certainly not `trust`, which lets anyone in without a password. A `host ... reject` line at the end makes it explicit that anything not listed is out.

!!! warning "Depends on the version and the image"
    The default method for new passwords depends on `password_encryption` and the version. If you migrate from an old database with `md5` hashes, passwords must be set again to move to SCRAM. With the official image, `pg_hba.conf` lives in the data directory and is generated at initialization; to replace it, mount it with `-c hba_file=...` or edit it and reload with `SELECT pg_reload_conf();`.

When connecting from outside the host, encrypt the connection with TLS (`ssl = on` and certificates) or use a VPN such as [WireGuard](../linux/wireguard.md).

## Parameter tuning

The defaults are designed for a small machine. They are passed to the image with `command: ["postgres", "-c", "key=value"]` or stored with `ALTER SYSTEM`. The most important ones:

| Parameter | What it controls | Usual starting point |
| --- | --- | --- |
| `shared_buffers` | PostgreSQL's own cache memory | Around 25 % of the dedicated RAM |
| `effective_cache_size` | Hint to the planner about total cache (including the system's) | Between 50 and 75 % of RAM |
| `work_mem` | Memory per sort or hash **operation** | A few MB; it multiplies by operations and connections |
| `maintenance_work_mem` | Memory for `VACUUM` and index creation | Quite a bit higher than `work_mem` |
| `max_connections` | Maximum simultaneous connections | The minimum needed; use a pooler |

```yaml
    command:
      - postgres
      - -c
      - shared_buffers=1GB
      - -c
      - effective_cache_size=3GB
      - -c
      - work_mem=16MB
      - -c
      - max_connections=100
```

Two traps. `work_mem` is not a per-connection limit: a complex query can use it several times, and with hundreds of connections consumption shoots up until the kernel kills the process. And raising `max_connections` is not the fix for an app that opens too many connections: each one consumes memory. Put a pooler such as PgBouncer in front (see [PostgreSQL High Availability](postgresql_ha.md)) and keep the number moderate.

`shared_buffers` and `max_connections` require a restart; others apply with `SELECT pg_reload_conf();`. The `pending_restart` column of the `pg_settings` view shows which ones are waiting for a restart. Remember that the container has its own memory limit: compute the values against that limit, not against the host's RAM.

## Diagnosing slow queries

First, what is happening right now? The `pg_stat_activity` view shows every connection:

```sql
SELECT pid, usename, state, now() - query_start AS duration, left(query, 80) AS query
FROM pg_stat_activity
WHERE state <> 'idle'
ORDER BY duration DESC;
```

Reading the result: the rows with the largest `duration` are the candidates. A prolonged `idle in transaction` state is suspicious, because it holds locks and stalls `VACUUM`. To stop a query use `SELECT pg_cancel_backend(pid);`, and if it does not respond, `pg_terminate_backend(pid)`, which closes the whole connection.

Second, why is that query slow? `EXPLAIN ANALYZE` actually runs the query and shows the plan with real timings:

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE customer_id = 42;
```

In the output look for three things: a sequential scan (`Seq Scan`) on a large table when you expected an index, a big gap between estimated and actual rows (stale statistics: run `ANALYZE`) and the nodes that concentrate the time. Careful: since it runs the query, wrap it in `BEGIN; ... ROLLBACK;` if it is an `UPDATE` or `DELETE`.

To see the costliest accumulated queries there is the `pg_stat_statements` extension. It must be loaded with `shared_preload_libraries=pg_stat_statements` (requires a restart) and enabled with `CREATE EXTENSION pg_stat_statements;`.

## Maintenance

PostgreSQL does not delete dead rows instantly: `VACUUM` cleans them, and the autovacuum process launches it on its own. Leave it enabled. What is worth watching:

- Tables with many dead rows, visible in `pg_stat_user_tables` (column `n_dead_tup`).
- Transactions open for hours, which prevent cleanup.
- A manual `VACUUM (ANALYZE)` after a bulk load, to refresh the planner statistics.
- Volume growth: watch the free disk space, because a full database can go read-only or stop.

`pg_size_pretty(pg_database_size('appdb'))` gives the size of a database in a readable format.

## Backups and restore

`pg_dump` produces a logical copy of a database, consistent even while in use. The custom format (`-Fc`) is compressed and allows selective restore:

```bash
docker compose exec -T db pg_dump -U myuser -Fc mydatabase > backup-$(date +%F).dump
docker compose exec -T db pg_dumpall -U myuser --globals-only > globals-$(date +%F).sql
```

`pg_dump` does not include roles or tablespaces; `pg_dumpall --globals-only` saves them separately. Without that second file, restoring on a new machine fails because of missing roles.

To restore with `pg_restore`:

```bash
docker compose exec -T db createdb -U myuser restored
docker compose exec -T db pg_restore -U myuser -d restored --no-owner < backup-2026-10-10.dump
```

A plain SQL dump (`-Fp`, the default) is restored with `psql -f` instead of `pg_restore`. The logical copy works for a moderately sized database; for large databases or point-in-time recovery you need physical copies (`pg_basebackup`) and WAL archiving, which are covered together with replication in [PostgreSQL High Availability](postgresql_ha.md).

Schedule dumps with a systemd timer or cron, store them off the host and encrypt them; retention and encryption criteria are in [Secure Backup](../cybersecurity/backup_seguro.md). And above all, test the restore: a backup that has never been restored is nothing more than an assumption.

## Upgrading to a major version

Minor versions (for example, within 16) are upgraded by changing the image tag. **Major** ones are not: the data directory format changes and the new version rejects the previous version's volume. Two paths:

1. **Dump and restore.** Run `pg_dump` (and `--globals-only`) with the old version, bring up a new volume with the new version and restore. It is the simplest and safest, with downtime proportional to size.
2. **`pg_upgrade`.** Converts the data directory in place and is faster on large databases. In containers it requires having the binaries of both versions, so it is more delicate.

In any case, rehearse first with a copy, check the release notes for incompatible changes and keep the old volume until the new one is validated. After upgrading, run `ANALYZE` to regenerate the statistics.

## As a systemd service

With Podman, a Quadlet file turns the container into a service (details in [Podman Quadlet](../docker/quadlets.md)):

```ini
# ~/.config/containers/systemd/postgres.container
[Container]
Image=docker.io/library/postgres:16-alpine
Environment=POSTGRES_USER=myuser POSTGRES_DB=mydatabase
Secret=pg_password,type=env,target=POSTGRES_PASSWORD
Volume=pgdata.volume:/var/lib/postgresql/data
PublishPort=127.0.0.1:5432:5432
HealthCmd=pg_isready -U myuser -d mydatabase

[Service]
Restart=always

[Install]
WantedBy=default.target
```

The secret is created beforehand with `podman secret create pg_password -`, reading the password from standard input. With Docker, `restart: unless-stopped` and a systemd service that invokes `docker compose up` serve a similar purpose. Databases stop slowly: give systemd a generous `TimeoutStopSec` so PostgreSQL shuts down cleanly.

## High availability and storage

A single instance is a single point of failure. For streaming replication, Patroni, automatic failover and split-brain prevention, follow [PostgreSQL High Availability](postgresql_ha.md). To run PostgreSQL with the volume on a Ceph cluster (I/O performance, access mode, snapshots) see [PostgreSQL on Ceph](../storage/postgresql_ceph.md). Neither replaces the logical backups of the previous section.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `FATAL: sorry, too many clients already` | `max_connections` reached, usually for lack of a pooler | Close idle connections, add PgBouncer and tune the app pool |
| `FATAL: password authentication failed` | Wrong password, or the role was created with another | `ALTER ROLE ... PASSWORD`; remember `POSTGRES_PASSWORD` only applies on first start |
| `FATAL: no pg_hba.conf entry for host` | No rule admits that IP, user or database | Add the line to `pg_hba.conf` and reload with `pg_reload_conf()` |
| Changes to the `initdb.d` script are not applied | They only run with an empty data directory | Apply a migration, or recreate the volume in tests |
| The container will not start after a major version change | The volume belongs to another major version | Go back to the previous version and do a dump and restore |
| Permission denied when mounting `./pgdata` | The directory owner does not match the container user | Use a named volume, or fix the owner |
| A query that used to be fine is now very slow | Stale statistics or a missing index | `ANALYZE`, and review the plan with `EXPLAIN ANALYZE` |
| The disk fills up | Bloated tables, accumulated WAL or huge logs | Check `pg_size_pretty`, autovacuum and long transactions |
| The container dies with no error | Out of memory from excessive `work_mem` or `shared_buffers` | Recompute against the container limit and lower connections |
| `pg_restore` fails because of missing roles | Restored without the global roles | Restore the `pg_dumpall --globals-only` file first |

## Best practices

1. Pin the major version of the image and plan major upgrades.
2. Use `POSTGRES_PASSWORD_FILE` or a secret, never the password in the compose file.
3. One role per application with minimal permissions; the app never connects as superuser.
4. `scram-sha-256` in `pg_hba.conf`, no `trust`, and the port bound to a private IP.
5. Use a pooler instead of raising `max_connections` without limit.
6. Compute memory against the container limit and remember `work_mem` multiplies.
7. Leave autovacuum enabled and watch long transactions.
8. Run `pg_dump` plus `pg_dumpall --globals-only`, off the host, and test the restore.
9. Monitor disk space, connections and slow queries.
10. For critical production, do not stop at one instance: move to [High Availability](postgresql_ha.md).

## References

- [Official PostgreSQL documentation](https://www.postgresql.org/docs/)
- [Official PostgreSQL image on Docker Hub](https://hub.docker.com/_/postgres)
- [pg_hba.conf](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html)
- [PostgreSQL High Availability](postgresql_ha.md)
- [PostgreSQL on Ceph](../storage/postgresql_ceph.md)
- [Podman Quadlet](../docker/quadlets.md)
- [Secure Backup](../cybersecurity/backup_seguro.md)
