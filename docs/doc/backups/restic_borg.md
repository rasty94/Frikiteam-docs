---
tags:
  - backups
  - linux
  - cli
updated: 2026-01-25
---

# Backups Agnósticos: Restic y Borg

Herramientas para hacer backup de archivos de cualquier sistema Linux/Unix (incluyendo contenedores).

## Restic

Moderno, escrito en Go, rápido y seguro por defecto.

```bash
# Inicializar repositorio (s3, sftp, local)
restic -r /srv/mybackup init

# Hacer backup
restic -r /srv/mybackup backup /home/user

# Restaurar
restic -r /srv/mybackup restore latest --target /tmp/restore
```

## BorgBackup

Muy maduro, excelente compresión y deduplicación.

```bash
# Inicializar
borg init --encryption=repokey /path/to/repo

# Crear backup
borg create /path/to/repo::Monday /home/user

# Listar
borg list /path/to/repo
```
