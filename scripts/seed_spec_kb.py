#!/usr/bin/env python3
"""
Seed script: load the MemTrace spec knowledge base into the PostgreSQL database.
Requires the database to be running (docker compose up -d) and DATABASE_URL in env.

Usage:
  cd packages/api && source venv/bin/activate
  python ../../scripts/seed_spec_kb.py
"""

import json
import os
import pathlib
import sys
import uuid
from datetime import datetime, timezone

try:
    import psycopg2
    from psycopg2.extras import execute_values
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependencies. Run:  pip install psycopg2-binary python-dotenv")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────

REPO_ROOT   = pathlib.Path(__file__).parent.parent
NODES_DIR   = REPO_ROOT / "examples" / "spec-as-kb" / "nodes"
EDGES_FILE  = REPO_ROOT / "examples" / "spec-as-kb" / "edges" / "edges.json"

load_dotenv(REPO_ROOT / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not set. Copy .env.example to .env and fill in credentials.")
    sys.exit(1)

# ── Seed workspace ────────────────────────────────────────────────────────────

SPEC_WS_ID   = "ws_spec0001"
SPEC_WS_NAME_ZH = "MemTrace 規格知識庫"
SPEC_WS_NAME_EN = "MemTrace Spec Knowledge Base"
SPEC_OWNER   = "usr_system01"   # placeholder — adjust to a real user id

# ── Helpers ───────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_nodes() -> list[dict]:
    nodes = []
    for f in sorted(NODES_DIR.glob("*.json")):
        nodes.append(json.loads(f.read_text(encoding="utf-8")))
    return nodes

def load_edges() -> list[dict]:
    return json.loads(EDGES_FILE.read_text(encoding="utf-8"))

# ── Insert functions ──────────────────────────────────────────────────────────

def upsert_system_user(cur):
    cur.execute("""
        INSERT INTO users (id, display_name, email, email_verified)
        VALUES (%s, %s, %s, true)
        ON CONFLICT (id) DO NOTHING
    """, (SPEC_OWNER, "MemTrace System", "system@memtrace.local"))


def upsert_workspace(cur):
    cur.execute("""
        INSERT INTO workspaces (id, name_zh, name_en, visibility, owner_id)
        VALUES (%s, %s, %s, 'public', %s)
        ON CONFLICT (id) DO NOTHING
    """, (SPEC_WS_ID, SPEC_WS_NAME_ZH, SPEC_WS_NAME_EN, SPEC_OWNER))
    print(f"  workspace: {SPEC_WS_ID}")


DEFAULT_TRUST = {"score": 0.8, "dimensions": {"accuracy": 0.8, "freshness": 1.0, "utility": 0.8, "author_rep": 0.8}, "votes": {"up": 0, "down": 0, "verifications": 0}}
DEFAULT_TRAVERSAL = {"count": 0, "unique_traversers": 0}

def upsert_nodes(cur, nodes: list[dict]):
    inserted = 0
    for n in nodes:
        p   = n["provenance"]
        c   = n["content"]
        t   = n.get("trust", DEFAULT_TRUST)
        tr  = n.get("traversal", DEFAULT_TRAVERSAL)
        dim = t.get("dimensions", DEFAULT_TRUST["dimensions"])
        votes = t.get("votes", DEFAULT_TRUST["votes"])
        cur.execute("""
            INSERT INTO memory_nodes (
                id, schema_version, workspace_id,
                title_zh, title_en,
                content_type, content_format,
                body_zh, body_en,
                tags, visibility,
                author, created_at, signature, source_type,
                trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
                votes_up, votes_down, verifications,
                traversal_count, unique_traverser_count
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (id) DO NOTHING
        """, (
            n["id"], n.get("schema_version", "1.0"), SPEC_WS_ID,
            n["title"]["zh-TW"], n["title"]["en"],
            c["type"], c.get("format", "plain"),
            c["body"]["zh-TW"], c["body"]["en"],
            n.get("tags", []), n.get("visibility", "public"),
            p["author"], p.get("created_at", now_iso()),
            p.get("signature", ""), p.get("source_type", "human"),
            t.get("score", 0.8),
            dim.get("accuracy", 0.8), dim.get("freshness", 1.0),
            dim.get("utility", 0.8),  dim.get("author_rep", 0.8),
            votes.get("up", 0), votes.get("down", 0), votes.get("verifications", 0),
            tr.get("count", 0), tr.get("unique_traversers", 0),
        ))
        inserted += 1
    print(f"  nodes:     {inserted} inserted (duplicates skipped)")


def upsert_edges(cur, edges: list[dict]):
    inserted = 0
    for e in edges:
        d = e["decay"]
        tr = e["traversal"]
        rating_sum = 0.0
        if tr["rating_avg"] is not None and tr["rating_count"] > 0:
            rating_sum = tr["rating_avg"] * tr["rating_count"]
        cur.execute("""
            INSERT INTO edges (
                id, workspace_id, from_id, to_id, relation,
                weight, co_access_count, last_co_accessed,
                half_life_days, min_weight,
                traversal_count, rating_sum, rating_count
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s
            )
            ON CONFLICT (id) DO NOTHING
        """, (
            e["id"], SPEC_WS_ID, e["from"], e["to"], e["relation"],
            e["weight"], e["co_access_count"], e["last_co_accessed"],
            d["half_life_days"], d["min_weight"],
            tr["count"], rating_sum, tr["rating_count"],
        ))
        inserted += 1
    print(f"  edges:     {inserted} inserted (duplicates skipped)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n>>  Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            print(f">>  Seeding spec-as-kb into workspace {SPEC_WS_ID}...\n")
            upsert_system_user(cur)
            upsert_workspace(cur)
            upsert_nodes(cur, load_nodes())
            upsert_edges(cur, load_edges())
        conn.commit()
        print(f"\nOK  Seed complete.")
    except Exception as e:
        conn.rollback()
        print(f"\nFAIL  Seed failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
