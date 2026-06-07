#!/usr/bin/env bash
set -euo pipefail

CONTAINER="postgres-db"
DB_NAME="${DB_NAME:-app_db}"
DB_USER="${DB_USER:-db_user}"
BACKUP_DIR="/var/backups/postgres"
RETENTION_DAYS=3

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

if docker exec "$CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    echo "[$(date)] Backup created: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
else
    echo "[$(date)] ERROR: Backup failed" >&2
    exit 1
fi

find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +"$RETENTION_DAYS" -delete
echo "[$(date)] Rotation complete. Removed backups older than $RETENTION_DAYS days."
