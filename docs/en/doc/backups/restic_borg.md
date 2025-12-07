# Agnostic Backups: Restic and Borg

Tools for backing up files on any Linux/Unix system (including containers).

## Restic

Modern, written in Go, fast, and secure by default.

```bash
# Initialize repository (s3, sftp, local)
restic -r /srv/mybackup init

# Backup
restic -r /srv/mybackup backup /home/user

# Restore
restic -r /srv/mybackup restore latest --target /tmp/restore
```

## BorgBackup

Very mature, excellent compression and deduplication.

```bash
# Initialize
borg init --encryption=repokey /path/to/repo

# Create backup
borg create /path/to/repo::Monday /home/user

# List
borg list /path/to/repo
```
