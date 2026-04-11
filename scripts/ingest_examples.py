import os
import json
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    db_url = os.environ.get("DATABASE_URL", "postgresql://memtrace:memtrace_dev_secret@127.0.0.1:5432/memtrace")
    return psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)

def ingest_spec_kb():
    base_path = "../examples/spec-as-kb"
    nodes_dir = os.path.join(base_path, "nodes")
    edges_file = os.path.join(base_path, "edges", "edges.json")
    
    ws_id = "ws_spec_template"
    author_id = "memtrace-spec"

    conn = get_conn()
    cur = conn.cursor()

    try:
        # 1. Ensure User and Workspace exist
        cur.execute("INSERT INTO users (id, display_name, email, email_verified) VALUES (%s, %s, %s, true) ON CONFLICT (id) DO NOTHING", 
                    (author_id, "MemTrace Spec", "spec@memtrace.local"))
        
        cur.execute("""
            INSERT INTO workspaces (id, name_zh, name_en, visibility, owner_id)
            VALUES (%s, %s, %s, 'public', %s)
            ON CONFLICT (id) DO UPDATE SET name_zh = EXCLUDED.name_zh
        """, (ws_id, "MemTrace 範本知識庫", "MemTrace Template KB", author_id))

        # 2. Ingest Nodes
        node_count = 0
        for filename in os.listdir(nodes_dir):
            if filename.endswith(".json"):
                with open(os.path.join(nodes_dir, filename), "r", encoding="utf-8") as f:
                    n = json.load(f)
                    
                    prov = n.get("provenance", {})
                    trust = n.get("trust", {})
                    dims = trust.get("dimensions", {})
                    
                    cur.execute("""
                        INSERT INTO memory_nodes (
                            id, workspace_id, title_zh, title_en,
                            content_type, content_format, body_zh, body_en,
                            tags, visibility, author, signature, source_type,
                            trust_score, dim_accuracy, dim_freshness, dim_utility, dim_author_rep
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET 
                            title_zh = EXCLUDED.title_zh, 
                            body_zh = EXCLUDED.body_zh
                    """, (
                        n["id"], ws_id, n["title"]["zh-TW"], n["title"]["en"],
                        n["content"]["type"], n["content"]["format"], 
                        n["content"]["body"]["zh-TW"], n["content"]["body"]["en"],
                        n.get("tags", []), n.get("visibility", "public"), 
                        prov.get("author", author_id), 
                        prov.get("signature", "placeholder-sig-" + n["id"]), 
                        prov.get("source_type", "human"),
                        trust.get("score", 0.5), 
                        dims.get("accuracy", 0.5),
                        dims.get("freshness", 1.0),
                        dims.get("utility", 0.5),
                        dims.get("author_rep", 0.5)
                    ))
                    node_count += 1

        # 3. Ingest Edges
        edge_count = 0
        if os.path.exists(edges_file):
            with open(edges_file, "r", encoding="utf-8") as f:
                edges = json.load(f)
                for e in edges:
                    decay = e.get("decay", {})
                    cur.execute("""
                        INSERT INTO edges (
                            id, workspace_id, from_id, to_id, relation, 
                            weight, half_life_days, min_weight
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (
                        e["id"], ws_id, e["from"], e["to"], e["relation"],
                        e.get("weight", 1.0), 
                        decay.get("half_life_days", 30), 
                        decay.get("min_weight", 0.1)
                    ))
                    edge_count += 1

        conn.commit()
        print(f"DONE: Successfully ingested {node_count} nodes and {edge_count} edges into workspace '{ws_id}'.")

    except Exception as err:
        conn.rollback()
        print(f"ERROR during ingestion: {err}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    ingest_spec_kb()
