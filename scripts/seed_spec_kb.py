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

# psycopg2 and python-dotenv are imported lazily inside main(); the --check /
# --write paths are DB-free and must run without those packages installed.

# ── Config ────────────────────────────────────────────────────────────────────

REPO_ROOT = pathlib.Path(__file__).parent.parent
KB_DIR = REPO_ROOT / "examples" / "spec-as-kb"
ZH_NODES_DIR = KB_DIR / "nodes" / "zh"
EN_NODES_DIR = KB_DIR / "nodes" / "en"
ZH_EDGES_FILE = KB_DIR / "edges" / "edges.zh.json"
EN_EDGES_FILE = KB_DIR / "edges" / "edges.en.json"

# DATABASE_URL and .env are loaded lazily in main() (the only DB path).

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

# Generated seed SQL outputs. The generator writes identical SQL to every path
# here so the migration and its schema-history mirror never hand-drift. The
# first path is canonical (the migration that actually runs); the second is a
# generated mirror. --check compares the regenerated SQL against exactly these.
SQL_OUTPUT_PATHS = [
    REPO_ROOT / "packages" / "api" / "migrations" / "003_seed_spec_kb.sql",  # canonical
    REPO_ROOT / "docs" / "schema-history" / "003_seed_spec_kb.sql",          # generated mirror
]
COMMITTED_SQL_PATHS = SQL_OUTPUT_PATHS


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


# ── Check (dry-run drift detection) ───────────────────────────────────────────

def run_check() -> int:
    """Read-only: regenerate SQL from seed JSON and compare to committed copies;
    report zh/en parity. No DB connection. Returns process exit code."""
    zh_nodes = load_nodes(ZH_NODES_DIR)
    en_nodes = load_nodes(EN_NODES_DIR)
    zh_edges = load_edges(ZH_EDGES_FILE)
    en_edges = load_edges(EN_EDGES_FILE)

    regenerated = generate_sql_seed(zh_nodes, en_nodes, zh_edges, en_edges)
    gen_nodes = regenerated.count("INSERT INTO memory_nodes")
    gen_edges = regenerated.count("INSERT INTO edges")

    print(">>  spec-sync --check (dry-run, no DB)\n")
    print(f"  seed JSON:   {len(zh_nodes)} zh + {len(en_nodes)} en nodes, "
          f"{len(zh_edges)} zh + {len(en_edges)} en edges")
    print(f"  regenerated: {gen_nodes} node-inserts, {gen_edges} edge-inserts\n")

    drift = False

    # 1. seed JSON <-> committed SQL
    existing = [p for p in COMMITTED_SQL_PATHS if p.exists()]
    if not existing:
        print("  ! no committed seed SQL found to compare against")
        drift = True
    for p in existing:
        committed = p.read_text(encoding="utf-8")
        c_nodes = committed.count("INSERT INTO memory_nodes")
        c_edges = committed.count("INSERT INTO edges")
        rel = p.relative_to(REPO_ROOT)
        if committed == regenerated:
            print(f"  OK    {rel}  (byte-identical)")
        elif c_nodes == gen_nodes and c_edges == gen_edges:
            print(f"  WARN  {rel}  same insert counts, content differs "
                  f"(likely timestamps/owner) — {c_nodes} nodes")
        else:
            drift = True
            print(f"  DRIFT {rel}  committed {c_nodes} nodes / {c_edges} edges "
                  f"!= regenerated {gen_nodes} / {gen_edges}")

    # 2. zh/en parity (by node id; en ids carry an _en suffix)
    zh_ids = {n["id"] for n in zh_nodes}
    en_ids = {n["id"].removesuffix("_en") for n in en_nodes}
    zh_only = sorted(zh_ids - en_ids)
    en_orphan = sorted(en_ids - zh_ids)
    print()
    print(f"  parity: {len(zh_ids)} zh, {len(en_ids)} en; "
          f"{len(zh_only)} zh-without-en (warn), {len(en_orphan)} en-orphan (error)")
    if zh_only:
        preview = ", ".join(zh_only[:10])
        more = f" …(+{len(zh_only) - 10})" if len(zh_only) > 10 else ""
        print(f"  WARN  zh without en: {preview}{more}")
    if en_orphan:
        drift = True
        print(f"  ERROR en orphan (no zh source): {', '.join(en_orphan)}")

    print()
    if drift:
        print("FAIL  spec drift detected (regenerate SQL and/or reconcile parity).")
        return 1
    print("OK    spec in sync.")
    return 0


def write_sql_outputs(sql: str) -> None:
    for p in SQL_OUTPUT_PATHS:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(sql, encoding="utf-8")
        print(f">>  SQL written: {p.relative_to(REPO_ROOT)}")


def run_write() -> int:
    """Regenerate the seed SQL from the JSON source of truth and write all
    committed copies. No DB connection."""
    zh_nodes = load_nodes(ZH_NODES_DIR)
    en_nodes = load_nodes(EN_NODES_DIR)
    zh_edges = load_edges(ZH_EDGES_FILE)
    en_edges = load_edges(EN_EDGES_FILE)
    sql = generate_sql_seed(zh_nodes, en_nodes, zh_edges, en_edges)
    write_sql_outputs(sql)
    print(f">>  regenerated {sql.count('INSERT INTO memory_nodes')} nodes / "
          f"{sql.count('INSERT INTO edges')} edges")
    return 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    try:
        import psycopg2
        import psycopg2.extras
        from dotenv import load_dotenv
    except ImportError:
        print("Missing dependencies. Run:  pip install psycopg2-binary python-dotenv")
        sys.exit(1)

    load_dotenv(REPO_ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set. Copy .env.example to .env and fill in credentials.")
        sys.exit(1)

    zh_nodes = load_nodes(ZH_NODES_DIR)
    en_nodes = load_nodes(EN_NODES_DIR)
    zh_edges = load_edges(ZH_EDGES_FILE)
    en_edges = load_edges(EN_EDGES_FILE)

    print("\n>>  Connecting to database...")
    conn = psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)
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
    write_sql_outputs(sql)


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        sys.exit(run_check())
    if "--write" in sys.argv[1:]:
        sys.exit(run_write())
    main()
