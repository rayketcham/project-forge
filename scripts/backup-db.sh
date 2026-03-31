#!/bin/bash
# Nightly database backup
set -euo pipefail

DB_PATH="${FORGE_DB_PATH:-/opt/project-forge/data/forge.db}"
BACKUP_DIR="/opt/project-forge/data/backups"

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/forge-$(date +%Y%m%d).db"

sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
echo "$(date): Backed up to $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/forge-*.db 2>/dev/null | tail -n +8 | xargs -r rm
