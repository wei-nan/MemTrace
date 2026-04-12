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
SPEC_WS_NAME_ZH = "規格知識庫"
SPEC_WS_NAME_EN = "Spec Knowledge Base"
SPEC_OWNER   = "system"         # matches the system user already in DB

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
    # Resolve actual system user ID by email (handles pre-existing users with different IDs)
    cur.execute("SELECT id FROM users WHERE email = 'system@memtrace.local'")
    row = cur.fetchone()
    if row:
        global SPEC_OWNER
        SPEC_OWNER = row["id"]
        print(f"  system user: found existing id={SPEC_OWNER}")
        return
    cur.execute("""
        INSERT INTO users (id, display_name, email, email_verified)
        VALUES (%s, %s, %s, true)
        ON CONFLICT (id) DO NOTHING
    """, (SPEC_OWNER, "MemTrace System", "system@memtrace.local"))
    print(f"  system user: created id={SPEC_OWNER}")


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
            ON CONFLICT (id) DO UPDATE SET
                title_zh = EXCLUDED.title_zh,
                title_en = EXCLUDED.title_en,
                content_type = EXCLUDED.content_type,
                content_format = EXCLUDED.content_format,
                body_zh = EXCLUDED.body_zh,
                body_en = EXCLUDED.body_en,
                tags = EXCLUDED.tags,
                trust_score = EXCLUDED.trust_score,
                dim_accuracy = EXCLUDED.dim_accuracy,
                dim_freshness = EXCLUDED.dim_freshness,
                dim_utility = EXCLUDED.dim_utility,
                dim_author_rep = EXCLUDED.dim_author_rep
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
    print(f"  nodes:     {inserted} upserted")


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

SQL_SEED_FILE = REPO_ROOT / "schema" / "sql" / "003_seed_spec_kb.sql"


def _esc(s: str) -> str:
    return s.replace("'", "''") if s else ""


def _arr(lst: list) -> str:
    items = ", ".join(f"'{_esc(t)}'" for t in lst)
    return f"ARRAY[{items}]::text[]"


def generate_sql_seed(nodes: list[dict], edges: list[dict]) -> str:
    """Re-generate schema/sql/003_seed_spec_kb.sql from current JSON source files."""
    now = now_iso()
    lines = [
        "-- =========================================================",
        "-- 003_seed_spec_kb.sql",
        "-- Auto-generated by scripts/seed_spec_kb.py — do not edit by hand.",
        "-- Seeds the MemTrace spec knowledge base (ws_spec0001).",
        "-- Runs automatically on Docker first-init via docker-entrypoint-initdb.d.",
        "-- =========================================================",
        "",
        "-- System user (idempotent)",
        "INSERT INTO users (id, email, display_name, email_verified)",
        "VALUES ('system', 'system@memtrace.internal', 'MemTrace System', true)",
        "ON CONFLICT (id) DO NOTHING;",
        "",
        "-- Spec workspace",
        f"INSERT INTO workspaces (id, name_zh, name_en, visibility, kb_type, owner_id)",
        f"VALUES ('{SPEC_WS_ID}', '{SPEC_WS_NAME_ZH}', '{SPEC_WS_NAME_EN}', 'public', 'evergreen', '{SPEC_OWNER}')",
        "ON CONFLICT (id) DO NOTHING;",
        "",
        "-- Nodes",
    ]

    for n in nodes:
        p     = n["provenance"]
        c     = n["content"]
        t     = n.get("trust", DEFAULT_TRUST)
        tr    = n.get("traversal", DEFAULT_TRAVERSAL)
        dim   = t.get("dimensions", DEFAULT_TRUST["dimensions"])
        votes = t.get("votes", DEFAULT_TRUST["votes"])

        lines += [
            "INSERT INTO memory_nodes",
            "  (id,schema_version,workspace_id,title_zh,title_en,content_type,content_format,",
            "   body_zh,body_en,tags,visibility,author,created_at,signature,source_type,",
            "   trust_score,dim_accuracy,dim_freshness,dim_utility,dim_author_rep,",
            "   votes_up,votes_down,verifications,traversal_count,unique_traverser_count)",
            "VALUES",
            f"  ('{n['id']}','1.0','{SPEC_WS_ID}',"
            f"'{_esc(n['title']['zh-TW'])}','{_esc(n['title']['en'])}','{c['type']}','{c.get('format','plain')}',",
            f"   '{_esc(c['body']['zh-TW'])}','{_esc(c['body']['en'])}',{_arr(n.get('tags',[]))},"
            f"'{n.get('visibility','public')}',",
            f"   '{_esc(p['author'])}','{p.get('created_at', now)}','{_esc(p.get('signature',''))}','{p.get('source_type','human')}',",
            f"   {t.get('score',0.8)},{dim.get('accuracy',0.8)},{dim.get('freshness',1.0)},"
            f"{dim.get('utility',0.8)},{dim.get('author_rep',0.8)},",
            f"   {votes.get('up',0)},{votes.get('down',0)},{votes.get('verifications',0)},"
            f"{tr.get('count',0)},{tr.get('unique_traversers',0)})",
            "ON CONFLICT (id) DO UPDATE SET",
            "  title_zh=EXCLUDED.title_zh, title_en=EXCLUDED.title_en,",
            "  body_zh=EXCLUDED.body_zh, body_en=EXCLUDED.body_en,",
            "  tags=EXCLUDED.tags, trust_score=EXCLUDED.trust_score,",
            "  dim_accuracy=EXCLUDED.dim_accuracy, dim_freshness=EXCLUDED.dim_freshness,",
            "  dim_utility=EXCLUDED.dim_utility, dim_author_rep=EXCLUDED.dim_author_rep;",
            "",
        ]

    lines += ["", "-- Edges"]
    for e in edges:
        d    = e.get("decay", {})
        tr_e = e.get("traversal", {})
        pin  = "true" if d.get("pinned", False) else "false"
        lines += [
            "INSERT INTO edges (id,workspace_id,from_id,to_id,relation,weight,half_life_days,min_weight,pinned,co_access_count,traversal_count)",
            f"VALUES ('{e['id']}','{SPEC_WS_ID}','{e['from']}','{e['to']}','{e['relation']}',"
            f"{d.get('weight',1.0)},{d.get('half_life_days',90)},{d.get('min_weight',0.05)},"
            f"{pin},{tr_e.get('co_access_count',0)},{tr_e.get('count',0)})",
            "ON CONFLICT (id) DO NOTHING;",
            "",
        ]

    return "\n".join(lines)


def main():
    nodes = load_nodes()
    edges = load_edges()

    print(f"\n>>  Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            print(f">>  Seeding spec-as-kb into workspace {SPEC_WS_ID}...\n")
            upsert_system_user(cur)
            upsert_workspace(cur)
            upsert_nodes(cur, nodes)
            upsert_edges(cur, edges)
        conn.commit()
        print(f"\nOK  Seed complete.")
    except Exception as e:
        conn.rollback()
        print(f"\nFAIL  Seed failed: {e}")
        raise
    finally:
        conn.close()

    # Keep SQL init file in sync with JSON sources
    sql = generate_sql_seed(nodes, edges)
    SQL_SEED_FILE.write_text(sql, encoding="utf-8")
    print(f">>  SQL init file updated: {SQL_SEED_FILE.name}")


if __name__ == "__main__":
    main()
