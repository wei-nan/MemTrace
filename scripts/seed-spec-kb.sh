#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Seed script: load the MemTrace spec knowledge base into local CLI storage
# Usage:  bash scripts/seed-spec-kb.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NODES_DIR="$REPO_ROOT/examples/spec-as-kb/nodes"
EDGES_FILE="$REPO_ROOT/examples/spec-as-kb/edges/edges.json"

# Build the CLI if not already built
if [ ! -f "$REPO_ROOT/packages/cli/dist/index.js" ]; then
  echo "Building CLI..."
  npm run build --workspace=packages/cli
fi

CLI="node $REPO_ROOT/packages/cli/dist/index.js"

echo ""
echo "▶  Importing spec-as-kb nodes..."
$CLI import "$NODES_DIR" --skip-invalid

echo ""
echo "▶  Importing spec-as-kb edges..."
$CLI import "$EDGES_FILE" --skip-invalid

echo ""
echo "▶  Listing imported nodes:"
$CLI list

echo ""
echo "✓  spec-as-kb seed complete."
