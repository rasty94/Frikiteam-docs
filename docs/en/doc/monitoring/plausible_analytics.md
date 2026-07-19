---
title: "Plausible Analytics Self-Hosted"
description: "Complete guide to deploying self-hosted Plausible Analytics: a lightweight, privacy-friendly alternative to Google Analytics"
keywords: "analytics, plausible, privacy, gdpr, self-hosted, docker"
tags: [monitoring, analytics, privacy, plausible]
updated: 2026-07-18
difficulty: intermediate
estimated_time: 4 min
category: Monitoring
status: published
last_reviewed: 2026-01-25
prerequisites: ["Basic DevOps knowledge"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Plausible Analytics Self-Hosted

**Created**: 2026-01-25  
**Last updated**: 2026-01-25

## 🎯 Introduction

[Plausible Analytics](https://plausible.io/) is a lightweight, open source and privacy-friendly alternative to Google Analytics. It uses no cookies, is GDPR-compliant and can be self-hosted.

## 🚀 Key Features

- ✅ **Cookie-free**: No consent banner required
- ✅ **GDPR/PECR compliant**: Meets European privacy regulations
- ✅ **Lightweight**: ~1KB script (vs 45KB for Google Analytics)
- ✅ **Open Source**: [Source available on GitHub](https://github.com/plausible/analytics)
- ✅ **Self-hosted**: Full control over your data
- ✅ **Simple**: Clean, minimalist dashboard

## 📦 Deploying with Docker

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
      - SECRET_KEY_BASE=your-secret-key-here  # Generate with: openssl rand -base64 64
      - TOTP_VAULT_KEY=your-totp-key-here     # Generate with: openssl rand -base64 32
      - DATABASE_URL=postgres://postgres:postgres@plausible_db:5432/plausible
      - CLICKHOUSE_DATABASE_URL=http://plausible_events_db:8123/plausible_events_db
      - DISABLE_REGISTRATION=true  # Disable after the first sign-up
      - MAILER_EMAIL=noreply@frikiteam.es
      - SMTP_HOST_ADDR=smtp.yourdomain.com
      - SMTP_HOST_PORT=587

volumes:
  plausible-db-data:
  plausible-event-data:
```

### ClickHouse configuration files

**clickhouse/clickhouse-config.xml**:
```xml
<clickhouse>
    <logger>
        <level>warning</level>
        <console>true</console>
    </logger>

    <!-- Disables query logging -->
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

## 🔧 Initial Setup

### 1. Generate secret keys

```bash
# SECRET_KEY_BASE
openssl rand -base64 64

# TOTP_VAULT_KEY
openssl rand -base64 32
```

### 2. Deploy the services

```bash
cd /path/to/plausible
docker-compose up -d
```

### 3. Create the first user

Go to `http://localhost:8000/register` and create your account. Then set `DISABLE_REGISTRATION=true` and restart:

```bash
docker-compose down
docker-compose up -d
```

## 🌐 Integrating with MkDocs Material

### Add to mkdocs.yml

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
      title: Was this page helpful?
      ratings:
        - icon: material/emoticon-happy-outline
          name: Yes, very helpful
          data: 1
          note: >-
            Thanks! It helps us improve.
        - icon: material/emoticon-sad-outline
          name: Could be improved
          data: 0
          note: >-
            Thanks for your feedback. We'll work on improving it.
```

### Configure the domain in Plausible

1. Log in to your Plausible instance
2. Add a new site: `docs.frikiteam.es`
3. Copy the tracking script
4. Set up custom goals (optional)

## 📊 Available Metrics

### Out of the box
- **Unique visitors**: Per day/week/month
- **Page views**: Total and per page
- **Visit duration**: Average time
- **Bounce rate**: Percentage of single-page visits
- **Traffic sources**: Direct, referral, search engines
- **Geographic location**: Country (without storing the specific IP)
- **Devices**: Desktop, tablet, mobile
- **Browsers and OS**: Basic statistics

### Custom events

You can track specific events:

```javascript
// In your JavaScript
plausible('Download', {props: {document: 'kubernetes-cheatsheet.pdf'}})
plausible('Signup', {props: {method: 'email'}})
```

## 🔒 Privacy and GDPR

### Why is it GDPR-compliant?

1. **No cookies**: Only localStorage to avoid double counting (optional)
2. **Anonymised IP**: Hashed IP with daily rotation
3. **No personal data**: Individual users are never tracked
4. **No cross-site tracking**: No fingerprinting
5. **Data residency**: Your data stays on your server

### Recommended configuration

```yaml
# In docker-compose.yml
environment:
  - IP_GEOLOCATION=false  # Turn off geolocation if you don't need it
  - DISABLE_AUTH=false    # Keep authentication enabled
  - LOG_FAILED_LOGIN_ATTEMPTS=true
```

## 🛡️ Reverse Proxy with Nginx

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

### Daily backup script

```bash
#!/bin/bash
# /usr/local/bin/backup-plausible.sh

BACKUP_DIR="/backups/plausible"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL backup
docker exec plausible_plausible_db_1 pg_dump -U postgres plausible > \
  "$BACKUP_DIR/plausible_db_$DATE.sql"

# ClickHouse backup (optional, event data)
# docker exec plausible_plausible_events_db_1 clickhouse-client --query \
#   "BACKUP DATABASE plausible_events_db TO Disk('backups', '$DATE.zip')"

# Keep the last 30 days
find "$BACKUP_DIR" -name "*.sql" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Crontab

```bash
# Daily backup at 3 AM
0 3 * * * /usr/local/bin/backup-plausible.sh >> /var/log/plausible-backup.log 2>&1
```

## 🔍 Alternatives

If Plausible doesn't fit your needs:

### Umami
- **Pros**: Simpler, lighter on resources
- **Cons**: Fewer features
- **Repo**: [umami-software/umami](https://github.com/umami-software/umami)

### Matomo
- **Pros**: Feature-rich, similar to GA
- **Cons**: Heavier, more complex
- **Repo**: [matomo-org/matomo](https://github.com/matomo-org/matomo)

### GoatCounter
- **Pros**: Minimalist, very lightweight
- **Cons**: Basic
- **Repo**: [arp242/goatcounter](https://github.com/arp242/goatcounter)

## 📚 References

- [Official Plausible documentation](https://plausible.io/docs)
- [Self-hosting guide](https://plausible.io/docs/self-hosting)
- [GitHub - plausible/analytics](https://github.com/plausible/analytics)
- [Comparison: Plausible vs Google Analytics](https://plausible.io/vs-google-analytics)

## 🎓 Best Practices

1. **Update regularly**: `docker-compose pull && docker-compose up -d`
2. **Watch resource usage**: ClickHouse can consume a fair amount of RAM
3. **Set up alerts**: For service outages
4. **Check the logs**: `docker-compose logs -f plausible`
5. **Protect access**: Use strong passwords and 2FA
