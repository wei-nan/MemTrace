#!/usr/bin/env bash
# On-demand backup: pg_dump + exports archive with timestamp.
# Usage: ./scripts/backup.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$REPO_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# shellcheck disable=SC1091
set -a; source "$REPO_ROOT/.env"; set +a

mkdir -p "$BACKUP_DIR"

echo "▶ Dumping PostgreSQL..."
docker exec memtrace-db pg_dump \
  -U "$POSTGRES_USER" --format=plain "$POSTGRES_DB" \
  | gzip -9 > "$BACKUP_DIR/manual_${TIMESTAMP}.sql.gz"
echo "  ✓ DB  → backups/manual_${TIMESTAMP}.sql.gz"

EXPORTS_DIR="$REPO_ROOT/packages/api/data/exports"
if [ -d "$EXPORTS_DIR" ] && [ -n "$(ls -A "$EXPORTS_DIR" 2>/dev/null)" ]; then
  echo "▶ Archiving exports..."
  tar -czf "$BACKUP_DIR/exports_${TIMESTAMP}.tar.gz" -C "$EXPORTS_DIR" .
  echo "  ✓ Exports → backups/exports_${TIMESTAMP}.tar.gz"
fi

echo ""
echo "Backup complete:"
ls -lh "$BACKUP_DIR"/*"$TIMESTAMP"* 2>/dev/null || true
