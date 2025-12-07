# Redis: High Performance Cache

Redis is an in-memory data structure store, used as a database, cache, and message broker.

## Quick Deployment

```bash
docker run --name my-redis -d redis
```

## Persistence

Redis offers two modes: RDB (snapshots) and AOF (Append Only File). To enable persistence:

```yaml
version: "3.8"
services:
  redis:
    image: redis:alpine
    command: redis-server --appendonly yes
    volumes:
      - ./redis_data:/data
    ports:
      - "6379:6379"
```

## Common Use Cases

1.  **Session Cache:** Storing user tokens.
2.  **Task Queues:** Backend for Celery or BullMQ.
3.  **Leaderboard:** Using Sorted Sets.
