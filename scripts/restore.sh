#!/usr/bin/env bash
# Restore PostgreSQL from a .sql.gz backup file.
# Usage: ./scripts/restore.sh <path/to/backup.sql.gz>
set -euo pipefail

BACKUP_FILE="${1:?Usage: restore.sh <path/to/backup.sql.gz>}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
set -a; source "$REPO_ROOT/.env"; set +a

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: file not found: $BACKUP_FILE" >&2
  exit 1
fi

echo "⚠  This will OVERWRITE '$POSTGRES_DB' with:"
echo "   $BACKUP_FILE"
echo ""
read -r -p "Type 'yes' to continue: " confirm
[ "$confirm" = "yes" ] || { echo "Aborted."; exit 1; }

echo "▶ Restoring..."
gunzip -c "$BACKUP_FILE" | docker exec -i memtrace-db psql \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --single-transaction -q

echo "✓ Restore complete."
