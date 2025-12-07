# PostgreSQL en Docker

PostgreSQL es el sistema de gestión de bases de datos relacional de objetos más avanzado del mundo. Ejecutarlo en Docker simplifica su despliegue y mantenimiento.

## Despliegue Básico (docker-compose)

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

## Alta Disponibilidad (HA)

Para entornos de producción crítica, se recomienda usar **Patroni** o **CloudNativePG** (en Kubernetes).
Una configuración simple de Master-Replica requiere configuración manual de `primary_conninfo` en la réplica y `wal_level=replica` en el primario.

## Backups

Utilizar `pg_dump` regularmente es fundamental:

```bash
docker exec -t my-postgres pg_dump -U myuser mydatabase > backup.sql
```
