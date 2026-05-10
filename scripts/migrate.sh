#!/usr/bin/env bash
# =============================================================================
# scripts/migrate.sh
# Apply incremental schema migrations against the running development DB.
#
# Usage:
#   ./scripts/migrate.sh                   # apply all pending migrations
#   ./scripts/migrate.sh --dry-run         # show what would be applied
#   ./scripts/migrate.sh 044 046           # apply specific files by number prefix
#
# Notes:
#   - All migrations in schema/sql/ must be idempotent (IF NOT EXISTS etc.)
#   - Files skipped: 001_init.sql (full schema), *seed*.sql (seed data)
#   - Connects to the Docker DB container; requires `docker` in PATH.
#   - For CI / non-Docker envs, set DATABASE_URL to override the connection.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIGRATIONS_DIR="$REPO_ROOT/schema/sql"

# ── Connection ──────────────────────────────────────────────────────────────
DOCKER_CONTAINER="${POSTGRES_CONTAINER:-memtrace-db}"
DB_USER="${POSTGRES_USER:-memtrace}"
DB_NAME="${POSTGRES_DB:-memtrace}"

# psql_query: run a -c query, stdin explicitly from /dev/null (safe inside loops)
psql_query() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    psql "$DATABASE_URL" "$@" < /dev/null
  else
    docker exec "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" "$@" < /dev/null
  fi
}

# psql_file: pipe a SQL file into psql
psql_file() {
  local filepath="$1"
  if [[ -n "${DATABASE_URL:-}" ]]; then
    psql "$DATABASE_URL" < "$filepath"
  else
    docker exec -i "$DOCKER_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$filepath"
  fi
}

# ── Argument parsing ─────────────────────────────────────────────────────────
DRY_RUN=false
FILTER_NUMS=()

for arg in "$@"; do
  if [[ "$arg" == "--dry-run" ]]; then
    DRY_RUN=true
  elif [[ "$arg" =~ ^[0-9]+$ ]]; then
    FILTER_NUMS+=("$arg")
  else
    echo "Unknown argument: $arg" >&2
    exit 1
  fi
done

# ── Ensure schema_migrations tracking table exists ───────────────────────────
if ! $DRY_RUN; then
  psql_query -q -c "
    CREATE TABLE IF NOT EXISTS schema_migrations (
      filename   TEXT PRIMARY KEY,
      applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );"
fi

# ── Skip patterns (files that are not incremental migrations) ─────────────────
SKIP_PATTERNS=("001_init" "seed" "099_")

should_skip() {
  local filename="$1"
  for pattern in "${SKIP_PATTERNS[@]}"; do
    [[ "$filename" == *"$pattern"* ]] && return 0
  done
  return 1
}

applied=0
skipped_already=0
skipped_pattern=0

echo ""
echo "=== MemTrace Migration Runner ====================="
echo "    Dir : $MIGRATIONS_DIR"
echo "    Mode: $( $DRY_RUN && echo 'DRY RUN' || echo 'APPLY' )"
echo "==================================================="
echo ""

# Collect all migration file paths into a temp file first (bash 3.2 compatible)
_tmplist="$(mktemp)"
find "$MIGRATIONS_DIR" -name "*.sql" | sort > "$_tmplist"
trap 'rm -f "$_tmplist"' EXIT

while IFS= read -r filepath; do
  filename="$(basename "$filepath")"

  # Skip init / seed files
  if should_skip "$filename"; then
    skipped_pattern=$((skipped_pattern + 1))
    continue
  fi

  # If specific numbers requested, filter by prefix
  if [[ ${#FILTER_NUMS[@]} -gt 0 ]]; then
    match=false
    for num in "${FILTER_NUMS[@]}"; do
      [[ "$filename" == "${num}_"* ]] && match=true && break
    done
    $match || continue
  fi

  # Check if already applied (skip in dry-run)
  if ! $DRY_RUN; then
    already=$(psql_query -t -c "SELECT COUNT(*) FROM schema_migrations WHERE filename='$filename';" 2>/dev/null | tr -d ' \n')
    if [[ "$already" -gt 0 ]]; then
      echo "  ✓ already applied: $filename"
      skipped_already=$((skipped_already + 1))
      continue
    fi
  fi

  echo "  → applying: $filename"

  if ! $DRY_RUN; then
    psql_file "$filepath"
    psql_query -q -c "INSERT INTO schema_migrations (filename) VALUES ('$filename') ON CONFLICT DO NOTHING;"
    applied=$((applied + 1))
  fi

done < "$_tmplist"

echo ""
echo "==================================================="
if $DRY_RUN; then
  echo "  Dry run complete. Use without --dry-run to apply."
else
  echo "  Applied : $applied"
  echo "  Already : $skipped_already"
  echo "  Skipped : $skipped_pattern (init/seed files)"
fi
echo "==================================================="
echo ""
