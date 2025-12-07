---
tags:
  - databases
  - postgres
  - docker
---

# PostgreSQL on Docker

PostgreSQL is the world's most advanced open source relational database. Running it in Docker simplifies deployment and maintenance.

## Basic Deployment (docker-compose)

```yaml
version: "3.8"
services:
  db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mysecretpassword
      POSTGRES_DB: mydatabase
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
```

## High Availability (HA)

For critical production environments, **Patroni** or **CloudNativePG** (on Kubernetes) is recommended.
A simple Master-Replica setup requires manual configuration of `primary_conninfo` on the replica and `wal_level=replica` on the primary.

## Backups

Regular use of `pg_dump` is fundamental:

```bash
docker exec -t my-postgres pg_dump -U myuser mydatabase > backup.sql
```
