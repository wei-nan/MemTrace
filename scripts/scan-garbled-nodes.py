#!/usr/bin/env python3
"""
scan-garbled-nodes.py — I-103 remediation
Scans memory_nodes for rows whose body_en or title_en contain garbled
Big5-misread characters (substitution characters from a UTF-8 misdecode).

Usage:
    python scripts/scan-garbled-nodes.py [--workspace ws_spec0001] [--fix]

Options:
    --workspace WS_ID   Limit scan to one workspace (default: all)
    --fix               Print PATCH curl commands to stdout for manual review
    --limit N           Max rows to inspect (default: 500)

Garbled fingerprint: when Big5 bytes are decoded as UTF-8 (with errors='replace'),
the resulting string contains characteristic CJK radicals that are unlikely to appear
in clean bilingual technical text:
    嚗 蝟 閮 霅 箏 皞 撠 暺 銵 蝝 銝 韏
"""
from __future__ import annotations

import argparse
import os
import sys
import re

# ─── Garbled character fingerprint ───────────────────────────────────────────
# Characters that appear when Big5/GB2312 bytes are misread as UTF-8
GARBLED_CHARS = set("嚗蝟閮霅箏皞撠暺銵蝝銝韏蝭蝑蝣撘皞撣蝘啣瘙蝙蝛撣")

GARBLED_PATTERN = re.compile(
    r"[嚗蝟閮霅箏皞撠暺銵蝝銝韏蝭蝑蝣撘撣蝘啣蝙蝛]{2,}"
)


def is_garbled(text: str | None) -> bool:
    if not text:
        return False
    return bool(GARBLED_PATTERN.search(text))


def scan(ws_id: str | None, limit: int, fix: bool) -> list[dict]:
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    db_url = os.environ.get("DATABASE_URL", "postgresql://memtrace:memtrace@localhost:5432/memtrace")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = """
        SELECT id, workspace_id, title_zh, title_en,
               LEFT(body_en, 120) AS body_en_preview,
               LEFT(body_zh, 60)  AS body_zh_preview
        FROM memory_nodes
        WHERE status = 'active'
    """
    params: list = []
    if ws_id:
        query += " AND workspace_id = %s"
        params.append(ws_id)
    query += f" ORDER BY created_at DESC LIMIT {int(limit)}"

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    hits = []
    for row in rows:
        fields_garbled = []
        if is_garbled(row.get("title_en")):
            fields_garbled.append("title_en")
        if is_garbled(row.get("body_en_preview")):
            fields_garbled.append("body_en")
        if fields_garbled:
            hits.append(dict(row) | {"garbled_fields": fields_garbled})

    return hits


def main():
    parser = argparse.ArgumentParser(description="Scan for garbled nodes (I-103)")
    parser.add_argument("--workspace", default=None, help="Workspace ID to scan")
    parser.add_argument("--fix",       action="store_true", help="Print curl PATCH commands")
    parser.add_argument("--limit",     type=int, default=500)
    args = parser.parse_args()

    hits = scan(args.workspace, args.limit, args.fix)

    if not hits:
        print("✅ No garbled nodes found.")
        return

    print(f"🔴 Found {len(hits)} garbled node(s):\n")
    for h in hits:
        print(f"  [{h['workspace_id']}] {h['id']}  —  {h['title_zh']}")
        print(f"    Garbled fields: {', '.join(h['garbled_fields'])}")
        print(f"    title_en preview : {h['title_en'][:80]!r}")
        print(f"    body_en preview  : {h['body_en_preview'][:80]!r}")
        print()

    if args.fix:
        token = os.environ.get("MEMTRACE_TOKEN", "<YOUR_TOKEN>")
        print("\n# ── Suggested PATCH commands (review before running) ──────────────────")
        for h in hits:
            ws  = h["workspace_id"]
            nid = h["id"]
            print(
                f"curl -s -X PATCH -H 'Authorization: Bearer {token}' "
                f"-H 'Content-Type: application/json' "
                f"-d '{{\"body_en\": \"<CORRECTED_CONTENT>\"}}' "
                f"'http://localhost:8000/api/v1/workspaces/{ws}/nodes/{nid}'"
            )


if __name__ == "__main__":
    main()
