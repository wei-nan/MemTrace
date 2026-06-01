#!/usr/bin/env python3
"""
Seed script: load the MemTrace spec knowledge base into PostgreSQL.

Two-workspace model (matches the live single-column schema):
  ws_spec0001     "MemTrace 規格知識庫"     language zh-TW
  ws_spec0001_en  "MemTrace Specification"  language en
The two are mutually linked via workspaces.linked_workspace_id.

Source files (produced by scripts/split_spec_kb_bilingual.py):
  examples/spec-as-kb/nodes/zh/*.json      -> ws_spec0001
  examples/spec-as-kb/nodes/en/*.json      -> ws_spec0001_en
  examples/spec-as-kb/edges/edges.zh.json  -> ws_spec0001
  examples/spec-as-kb/edges/edges.en.json  -> ws_spec0001_en

Requires the database running (docker compose up -d) and DATABASE_URL in env.

Usage:
  cd packages/api && source venv/bin/activate
  python ../../scripts/seed_spec_kb.py
"""

import json
import os
import pathlib
import sys
from datetime import datetime, timezone

try:
    import psycopg2
    import psycopg2.extras
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependencies. Run:  pip install psycopg2-binary python-dotenv")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────

REPO_ROOT = pathlib.Path(__file__).parent.parent
KB_DIR = REPO_ROOT / "examples" / "spec-as-kb"
ZH_NODES_DIR = KB_DIR / "nodes" / "zh"
EN_NODES_DIR = KB_DIR / "nodes" / "en"
ZH_EDGES_FILE = KB_DIR / "edges" / "edges.zh.json"
EN_EDGES_FILE = KB_DIR / "edges" / "edges.en.json"

load_dotenv(REPO_ROOT / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not set. Copy .env.example to .env and fill in credentials.")
    sys.exit(1)

# ── Seed workspaces ─────────────────────────────────────────────────────────────

ZH_WS_ID = "ws_spec0001"
EN_WS_ID = "ws_spec0001_en"
ZH_WS_NAME = "MemTrace 規格知識庫"
EN_WS_NAME = "MemTrace Specification"
SPEC_OWNER = "system"  # resolved against the live system user below

# (ws_id, name, language, linked_to) — one entry per workspace
WORKSPACES = [
    (ZH_WS_ID, ZH_WS_NAME, "zh-TW", EN_WS_ID),
    (EN_WS_ID, EN_WS_NAME, "en", ZH_WS_ID),
]

DEFAULT_TRUST = {"score": 0.8, "dimensions": {"accuracy": 0.8, "freshness": 1.0, "utility": 0.8, "author_rep": 0.8}, "votes": {"up": 0, "down": 0, "verifications": 0}}
DEFAULT_TRAVERSAL = {"count": 0, "unique_traversers": 0}

# ── Helpers ───────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_nodes(d: pathlib.Path) -> list[dict]:
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(d.glob("*.json"))]


def load_edges(f: pathlib.Path) -> list[dict]:
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


# ── Insert functions ──────────────────────────────────────────────────────────

def upsert_system_user(cur):
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


def upsert_workspaces(cur):
    # Phase 1: insert both rows with linked_workspace_id NULL, so neither row's
    # self-referential FK can point at a not-yet-inserted sibling.
    for ws_id, name, lang, _linked in WORKSPACES:
        cur.execute("""
            INSERT INTO workspaces (id, name, language, visibility, kb_type, owner_id)
            VALUES (%s, %s, %s, 'public', 'evergreen', %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                language = EXCLUDED.language
        """, (ws_id, name, lang, SPEC_OWNER))
        print(f"  workspace: {ws_id} ({lang})")
    # Phase 2: now both rows exist, wire up the mutual links.
    for ws_id, _name, _lang, linked in WORKSPACES:
        cur.execute("UPDATE workspaces SET linked_workspace_id = %s WHERE id = %s", (linked, ws_id))


def upsert_nodes(cur, nodes: list[dict], ws_id: str):
    for n in nodes:
        p = n["provenance"]
        c = n["content"]
        t = n.get("trust") or DEFAULT_TRUST
        tr = n.get("traversal") or DEFAULT_TRAVERSAL
        dim = t.get("dimensions", DEFAULT_TRUST["dimensions"])
        votes = t.get("votes", DEFAULT_TRUST["votes"])
        cur.execute("""
            INSERT INTO memory_nodes (
                id, schema_version, workspace_id,
                title, content_type, content_format, body,
                tags, visibility,
                author, created_at, signature, source_type,
                trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep,
                votes_up, votes_down, verifications,
                traversal_count, unique_traverser_count
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                body = EXCLUDED.body,
                content_type = EXCLUDED.content_type,
                content_format = EXCLUDED.content_format,
                tags = EXCLUDED.tags,
                trust_score = EXCLUDED.trust_score,
                dim_accuracy = EXCLUDED.dim_accuracy,
                dim_freshness = EXCLUDED.dim_freshness,
                dim_utility = EXCLUDED.dim_utility,
                dim_author_rep = EXCLUDED.dim_author_rep
        """, (
            n["id"], n.get("schema_version", "1.0"), ws_id,
            n["title"], c["type"], c.get("format", "plain"), c["body"],
            n.get("tags", []), n.get("visibility", "public"),
            p["author"], p.get("created_at", now_iso()),
            p.get("signature", ""), p.get("source_type", "human"),
            t.get("score", 0.8),
            dim.get("accuracy", 0.8), dim.get("freshness", 1.0),
            dim.get("utility", 0.8), dim.get("author_rep", 0.8),
            votes.get("up", 0), votes.get("down", 0), votes.get("verifications", 0),
            tr.get("count", 0), tr.get("unique_traversers", 0),
        ))
    print(f"  nodes:     {len(nodes)} upserted into {ws_id}")


def upsert_edges(cur, edges: list[dict], ws_id: str):
    for e in edges:
        d = e.get("decay", {})
        tr = e.get("traversal", {})
        rating_sum = 0.0
        if tr.get("rating_avg") is not None and tr.get("rating_count", 0) > 0:
            rating_sum = tr["rating_avg"] * tr["rating_count"]
        cur.execute("""
            INSERT INTO edges (
                id, workspace_id, from_id, to_id, relation,
                weight, co_access_count, last_co_accessed,
                half_life_days, min_weight, pinned,
                traversal_count, rating_sum, rating_count
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s
            )
            ON CONFLICT (id) DO NOTHING
        """, (
            e["id"], ws_id, e["from"], e["to"], e["relation"],
            e.get("weight", 1.0), e.get("co_access_count", 0), e.get("last_co_accessed", now_iso()),
            d.get("half_life_days", 90), d.get("min_weight", 0.05), d.get("pinned", False),
            tr.get("count", 0), rating_sum, tr.get("rating_count", 0),
        ))
    print(f"  edges:     {len(edges)} inserted into {ws_id} (duplicates skipped)")


# ── SQL generation ──────────────────────────────────────────────────────────────

SQL_SEED_FILE = REPO_ROOT / "schema" / "sql" / "003_seed_spec_kb.sql"


def _esc(s: str) -> str:
    return s.replace("'", "''") if s else ""


def _arr(lst: list) -> str:
    items = ", ".join(f"'{_esc(t)}'" for t in lst)
    return f"ARRAY[{items}]::text[]"


def _node_sql(n: dict, ws_id: str) -> list[str]:
    p = n["provenance"]
    c = n["content"]
    t = n.get("trust") or DEFAULT_TRUST
    tr = n.get("traversal") or DEFAULT_TRAVERSAL
    dim = t.get("dimensions", DEFAULT_TRUST["dimensions"])
    votes = t.get("votes", DEFAULT_TRUST["votes"])
    return [
        "INSERT INTO memory_nodes",
        "  (id,schema_version,workspace_id,title,content_type,content_format,body,",
        "   tags,visibility,author,created_at,signature,source_type,",
        "   trust_score,dim_accuracy,dim_freshness,dim_utility,dim_author_rep,",
        "   votes_up,votes_down,verifications,traversal_count,unique_traverser_count)",
        "VALUES",
        f"  ('{n['id']}','1.0','{ws_id}',"
        f"'{_esc(n['title'])}','{c['type']}','{c.get('format','plain')}','{_esc(c['body'])}',",
        f"   {_arr(n.get('tags',[]))},'{n.get('visibility','public')}',"
        f"'{_esc(p['author'])}','{p.get('created_at', now_iso())}','{_esc(p.get('signature',''))}','{p.get('source_type','human')}',",
        f"   {t.get('score',0.8)},{dim.get('accuracy',0.8)},{dim.get('freshness',1.0)},"
        f"{dim.get('utility',0.8)},{dim.get('author_rep',0.8)},",
        f"   {votes.get('up',0)},{votes.get('down',0)},{votes.get('verifications',0)},"
        f"{tr.get('count',0)},{tr.get('unique_traversers',0)})",
        "ON CONFLICT (id) DO UPDATE SET",
        "  title=EXCLUDED.title, body=EXCLUDED.body,",
        "  tags=EXCLUDED.tags, trust_score=EXCLUDED.trust_score,",
        "  dim_accuracy=EXCLUDED.dim_accuracy, dim_freshness=EXCLUDED.dim_freshness,",
        "  dim_utility=EXCLUDED.dim_utility, dim_author_rep=EXCLUDED.dim_author_rep;",
        "",
    ]


def _edge_sql(e: dict, ws_id: str) -> list[str]:
    d = e.get("decay", {})
    tr_e = e.get("traversal", {})
    pin = "true" if d.get("pinned", False) else "false"
    weight = e.get("weight", d.get("weight", 1.0))
    return [
        "INSERT INTO edges (id,workspace_id,from_id,to_id,relation,weight,half_life_days,min_weight,pinned,co_access_count,traversal_count)",
        f"VALUES ('{e['id']}','{ws_id}','{e['from']}','{e['to']}','{e['relation']}',"
        f"{weight},{d.get('half_life_days',90)},{d.get('min_weight',0.05)},"
        f"{pin},{e.get('co_access_count',0)},{tr_e.get('count',0)})",
        "ON CONFLICT (id) DO NOTHING;",
        "",
    ]


def generate_sql_seed(zh_nodes, en_nodes, zh_edges, en_edges) -> str:
    lines = [
        "-- =========================================================",
        "-- 003_seed_spec_kb.sql",
        "-- Auto-generated by scripts/seed_spec_kb.py — do not edit by hand.",
        "-- Seeds the MemTrace spec KB as two linked monolingual workspaces:",
        "--   ws_spec0001    (zh-TW)  <-->  ws_spec0001_en  (en)",
        "-- Runs automatically on Docker first-init via docker-entrypoint-initdb.d.",
        "-- =========================================================",
        "",
        "SET client_encoding = 'UTF8';",
        "",
        "-- System user (idempotent)",
        "INSERT INTO users (id, email, display_name, email_verified)",
        "VALUES ('system', 'system@memtrace.internal', 'MemTrace System', true)",
        "ON CONFLICT (id) DO NOTHING;",
        "",
        "-- Spec workspaces (linked pair)",
        f"INSERT INTO workspaces (id, name, language, linked_workspace_id, visibility, kb_type, owner_id) VALUES",
        f"  ('{ZH_WS_ID}', '{_esc(ZH_WS_NAME)}', 'zh-TW', '{EN_WS_ID}', 'public', 'evergreen', '{SPEC_OWNER}'),",
        f"  ('{EN_WS_ID}', '{_esc(EN_WS_NAME)}', 'en', '{ZH_WS_ID}', 'public', 'evergreen', '{SPEC_OWNER}')",
        "ON CONFLICT (id) DO UPDATE SET",
        "  name=EXCLUDED.name, language=EXCLUDED.language, linked_workspace_id=EXCLUDED.linked_workspace_id;",
        "",
        "-- ── zh-TW nodes ─────────────────────────────────────────",
    ]
    for n in zh_nodes:
        lines += _node_sql(n, ZH_WS_ID)
    lines += ["", "-- ── en nodes ────────────────────────────────────────────"]
    for n in en_nodes:
        lines += _node_sql(n, EN_WS_ID)
    lines += ["", "-- ── zh-TW edges ─────────────────────────────────────────"]
    for e in zh_edges:
        lines += _edge_sql(e, ZH_WS_ID)
    lines += ["", "-- ── en edges ────────────────────────────────────────────"]
    for e in en_edges:
        lines += _edge_sql(e, EN_WS_ID)
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    zh_nodes = load_nodes(ZH_NODES_DIR)
    en_nodes = load_nodes(EN_NODES_DIR)
    zh_edges = load_edges(ZH_EDGES_FILE)
    en_edges = load_edges(EN_EDGES_FILE)

    print("\n>>  Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = False
    conn.set_client_encoding("UTF8")

    try:
        with conn.cursor() as cur:
            print(">>  Seeding spec-as-kb (two-workspace model)...\n")
            upsert_system_user(cur)
            upsert_workspaces(cur)
            upsert_nodes(cur, zh_nodes, ZH_WS_ID)
            upsert_nodes(cur, en_nodes, EN_WS_ID)
            upsert_edges(cur, zh_edges, ZH_WS_ID)
            upsert_edges(cur, en_edges, EN_WS_ID)
        conn.commit()
        print("\nOK  Seed complete.")
    except Exception as e:
        conn.rollback()
        print(f"\nFAIL  Seed failed: {e}")
        raise
    finally:
        conn.close()

    sql = generate_sql_seed(zh_nodes, en_nodes, zh_edges, en_edges)
    SQL_SEED_FILE.write_text(sql, encoding="utf-8")
    print(f">>  SQL init file updated: {SQL_SEED_FILE.name}")


if __name__ == "__main__":
    main()
