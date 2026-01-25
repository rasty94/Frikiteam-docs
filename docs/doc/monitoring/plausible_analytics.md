---
title: "Plausible Analytics Self-Hosted"
description: "Guía completa para implementar Plausible Analytics auto-hospedado: alternativa ligera y respetuosa con la privacidad a Google Analytics"
keywords: "analytics, plausible, privacy, gdpr, self-hosted, docker"
tags: [monitoring, analytics, privacy, plausible]
updated: 2026-01-25
difficulty: intermediate
estimated_time: 4 min
category: Monitoreo
status: published
last_reviewed: 2026-01-25
prerequisites: ["Conocimientos básicos de DevOps"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Plausible Analytics Self-Hosted

**Fecha de creación**: 2026-01-25  
**Última actualización**: 2026-01-25

## 🎯 Introducción

[Plausible Analytics](https://plausible.io/) es una alternativa ligera, open source y respetuosa con la privacidad a Google Analytics. No usa cookies, es GDPR-compliant y puede auto-hospedarse.

## 🚀 Características Clave

- ✅ **Sin cookies**: No requiere banner de consentimiento
- ✅ **GDPR/PECR compliant**: Cumple con normativas europeas de privacidad
- ✅ **Ligero**: Script de ~1KB (vs 45KB de Google Analytics)
- ✅ **Open Source**: [Código disponible en GitHub](https://github.com/plausible/analytics)
- ✅ **Self-hosted**: Control total de tus datos
- ✅ **Simple**: Dashboard intuitivo y minimalista

## 📦 Despliegue con Docker

### docker-compose.yml

```yaml
version: "3.8"

services:
  plausible_db:
    image: postgres:15-alpine
    restart: unless-stopped
    volumes:
      - plausible-db-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=plausible

  plausible_events_db:
    image: clickhouse/clickhouse-server:23.11-alpine
    restart: unless-stopped
    volumes:
      - plausible-event-data:/var/lib/clickhouse
      - ./clickhouse/clickhouse-config.xml:/etc/clickhouse-server/config.d/logging.xml:ro
      - ./clickhouse/clickhouse-user-config.xml:/etc/clickhouse-server/users.d/logging.xml:ro
    ulimits:
      nofile:
        soft: 262144
        hard: 262144

  plausible:
    image: plausible/analytics:v2.0
    restart: unless-stopped
    command: sh -c "sleep 10 && /entrypoint.sh db createdb && /entrypoint.sh db migrate && /entrypoint.sh run"
    depends_on:
      - plausible_db
      - plausible_events_db
    ports:
      - "8000:8000"
    environment:
      - BASE_URL=https://analytics.frikiteam.es
      - SECRET_KEY_BASE=your-secret-key-here  # Generar con: openssl rand -base64 64
      - TOTP_VAULT_KEY=your-totp-key-here     # Generar con: openssl rand -base64 32
      - DATABASE_URL=postgres://postgres:postgres@plausible_db:5432/plausible
      - CLICKHOUSE_DATABASE_URL=http://plausible_events_db:8123/plausible_events_db
      - DISABLE_REGISTRATION=true  # Desactivar después del primer registro
      - MAILER_EMAIL=noreply@frikiteam.es
      - SMTP_HOST_ADDR=smtp.yourdomain.com
      - SMTP_HOST_PORT=587

volumes:
  plausible-db-data:
  plausible-event-data:
```

### Archivos de configuración ClickHouse

**clickhouse/clickhouse-config.xml**:
```xml
<clickhouse>
    <logger>
        <level>warning</level>
        <console>true</console>
    </logger>

    <!-- Deshabilita logging de queries -->
    <query_thread_log remove="remove"/>
    <query_log remove="remove"/>
    <text_log remove="remove"/>
    <trace_log remove="remove"/>
    <metric_log remove="remove"/>
    <asynchronous_metric_log remove="remove"/>
    <session_log remove="remove"/>
    <part_log remove="remove"/>
</clickhouse>
```

**clickhouse/clickhouse-user-config.xml**:
```xml
<clickhouse>
    <profiles>
        <default>
            <log_queries>0</log_queries>
            <log_query_threads>0</log_query_threads>
        </default>
    </profiles>
</clickhouse>
```

## 🔧 Configuración Inicial

### 1. Generar claves secretas

```bash
# SECRET_KEY_BASE
openssl rand -base64 64

# TOTP_VAULT_KEY
openssl rand -base64 32
```

### 2. Desplegar servicios

```bash
cd /path/to/plausible
docker-compose up -d
```

### 3. Crear primer usuario

Accede a `http://localhost:8000/register` y crea tu cuenta. Luego, establece `DISABLE_REGISTRATION=true` y reinicia:

```bash
docker-compose down
docker-compose up -d
```

## 🌐 Integración en MkDocs Material

### Añadir en mkdocs.yml

```yaml
extra:
  analytics:
    provider: custom
    # Plausible self-hosted
  
extra_javascript:
  - https://analytics.frikiteam.es/js/script.js
  
extra:
  analytics:
    feedback:
      title: ¿Te ha sido útil esta página?
      ratings:
        - icon: material/emoticon-happy-outline
          name: Sí, muy útil
          data: 1
          note: >-
            ¡Gracias! Nos ayuda a mejorar.
        - icon: material/emoticon-sad-outline
          name: Podría mejorarse
          data: 0
          note: >-
            Gracias por tu feedback. Trabajaremos en mejorarlo.
```

### Configurar dominio en Plausible

1. Accede a tu instancia de Plausible
2. Añade nuevo sitio: `docs.frikiteam.es`
3. Copia el script de tracking
4. Configura metas/objetivos personalizados (opcional)

## 📊 Métricas Disponibles

### Por defecto
- **Visitantes únicos**: Por día/semana/mes
- **Páginas vistas**: Total y por página
- **Duración de visita**: Tiempo promedio
- **Tasa de rebote**: Porcentaje de visitas de una sola página
- **Fuentes de tráfico**: Directo, referido, buscadores
- **Ubicación geográfica**: País (sin IP específica)
- **Dispositivos**: Desktop, tablet, móvil
- **Navegadores y SO**: Estadísticas básicas

### Eventos personalizados

Puedes trackear eventos específicos:

```javascript
// En tu JavaScript
plausible('Download', {props: {document: 'kubernetes-cheatsheet.pdf'}})
plausible('Signup', {props: {method: 'email'}})
```

## 🔒 Privacidad y GDPR

### ¿Por qué es GDPR-compliant?

1. **No usa cookies**: Solo localStorage para evitar doble conteo (opcional)
2. **IP anónima**: Hash de IP + rotación diaria
3. **Sin información personal**: No trackea usuarios individuales
4. **Sin tracking entre sitios**: Sin fingerprinting
5. **Data residency**: Tus datos en tu servidor

### Configuración recomendada

```yaml
# En docker-compose.yml
environment:
  - IP_GEOLOCATION=false  # Desactivar geolocalización si no es necesario
  - DISABLE_AUTH=false    # Mantener autenticación activa
  - LOG_FAILED_LOGIN_ATTEMPTS=true
```

## 🛡️ Proxy Inverso con Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name analytics.frikiteam.es;

    ssl_certificate /etc/letsencrypt/live/analytics.frikiteam.es/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/analytics.frikiteam.es/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📈 Backups

### Script de backup diario

```bash
#!/bin/bash
# /usr/local/bin/backup-plausible.sh

BACKUP_DIR="/backups/plausible"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL backup
docker exec plausible_plausible_db_1 pg_dump -U postgres plausible > \
  "$BACKUP_DIR/plausible_db_$DATE.sql"

# ClickHouse backup (opcional, datos de eventos)
# docker exec plausible_plausible_events_db_1 clickhouse-client --query \
#   "BACKUP DATABASE plausible_events_db TO Disk('backups', '$DATE.zip')"

# Retener últimos 30 días
find "$BACKUP_DIR" -name "*.sql" -mtime +30 -delete

echo "Backup completado: $DATE"
```

### Crontab

```bash
# Backup diario a las 3 AM
0 3 * * * /usr/local/bin/backup-plausible.sh >> /var/log/plausible-backup.log 2>&1
```

## 🔍 Alternativas

Si Plausible no se ajusta a tus necesidades:

### Umami
- **Pros**: Más simple, menos recursos
- **Contras**: Menos features
- **Repo**: [umami-software/umami](https://github.com/umami-software/umami)

### Matomo
- **Pros**: Feature-rich, similar a GA
- **Contras**: Más pesado, más complejo
- **Repo**: [matomo-org/matomo](https://github.com/matomo-org/matomo)

### GoatCounter
- **Pros**: Minimalista, muy ligero
- **Contras**: Básico
- **Repo**: [arp242/goatcounter](https://github.com/arp242/goatcounter)

## 📚 Referencias

- [Documentación oficial de Plausible](https://plausible.io/docs)
- [Self-hosting guide](https://plausible.io/docs/self-hosting)
- [GitHub - plausible/analytics](https://github.com/plausible/analytics)
- [Comparison: Plausible vs Google Analytics](https://plausible.io/vs-google-analytics)

## 🎓 Mejores Prácticas

1. **Actualiza regularmente**: `docker-compose pull && docker-compose up -d`
2. **Monitoriza recursos**: ClickHouse puede consumir bastante RAM
3. **Configura alertas**: Para caídas del servicio
4. **Revisa logs**: `docker-compose logs -f plausible`
5. **Protege el acceso**: Usa contraseñas fuertes y 2FA
