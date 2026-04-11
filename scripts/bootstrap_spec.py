import os
import sys
import re
import json
import hashlib
import secrets
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from contextlib import contextmanager

# Simple DB handling
def get_conn():
    # Hardcoded/fallback connection info matching .env or docker defaults
    db_url = os.environ.get("DATABASE_URL", "postgresql://memtrace:memtrace_dev_secret@localhost:5432/memtrace")
    return psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)

@contextmanager
def db_cursor(commit=False):
    conn = get_conn()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def generate_id(prefix):
    return f"{prefix}_{secrets.token_hex(4)}"

def compute_signature(title, content, tags, author):
    payload = json.dumps({
        "title":   title,
        "content": content,
        "tags":    sorted(tags),
        "author":  author,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()

def bootstrap_spec():
    spec_path = "../docs/SPEC.md"
    if not os.path.exists(spec_path):
        print(f"Error: {spec_path} not found")
        return

    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by headings (##)
    sections = re.split(r'\n(## .+)', content)
    
    # The first element is the title (# MemTrace Specification)
    main_title_match = re.search(r'^# (.+)', sections[0])
    main_title = main_title_match.group(1) if main_title_match else "MemTrace Specification"
    
    # Create Workspace
    ws_id = "ws_spec_template"
    author_id = "system"
    
    with db_cursor(commit=True) as cur:
        # Check if workspace exists
        cur.execute("SELECT id FROM workspaces WHERE id = %s", (ws_id,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO workspaces (id, name_zh, name_en, visibility, owner_id)
                VALUES (%s, %s, %s, 'public', %s)
            """, (ws_id, "MemTrace 產品規格書", "MemTrace Specification", author_id))
            print(f"Created public workspace: {ws_id}")
        else:
            print(f"Workspace {ws_id} already exists, updating nodes...")
            cur.execute("DELETE FROM memory_nodes WHERE workspace_id = %s", (ws_id,))

        # Parse sections
        nodes = []
        
        # Add a root node for the whole spec
        intro = sections[0].strip()
        nodes.append({
            "title_zh": "MemTrace 規格總覽",
            "title_en": "MemTrace Spec Overview",
            "body_zh": intro,
            "body_en": intro,
            "type": "context"
        })

        for i in range(1, len(sections), 2):
            title_line = sections[i]
            body = sections[i+1] if i+1 < len(sections) else ""
            
            title = title_line.replace("## ", "").strip()
            
            # Simple heuristic: if it looks like bullet points, it's factual
            # if it starts with numbers, it's procedural
            content_type = "factual"
            if re.search(r'^\d\.', body.strip()):
                content_type = "procedural"
            
            nodes.append({
                "title_zh": title,
                "title_en": title,
                "body_zh": body.strip(),
                "body_en": body.strip(),
                "type": content_type
            })

        # Insert nodes
        node_ids = []
        for n in nodes:
            node_id = generate_id("mem")
            node_ids.append(node_id)
            
            title_map = {"zh-TW": n["title_zh"], "en": n["title_en"]}
            content_map = {"type": n["type"], "format": "markdown",
                          "body": {"zh-TW": n["body_zh"], "en": n["body_en"]}}
            sig = compute_signature(title_map, content_map, [], author_id)
            
            cur.execute("""
                INSERT INTO memory_nodes (
                    id, workspace_id, title_zh, title_en,
                    content_type, content_format, body_zh, body_en,
                    tags, visibility, author, signature, source_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ai_verified')
            """, (
                node_id, ws_id, n["title_zh"], n["title_en"],
                n["type"], "markdown", n["body_zh"], n["body_en"],
                [], "public", author_id, sig
            ))
        
        # Link nodes sequentially
        for i in range(len(node_ids) - 1):
            edge_id = generate_id("edge")
            cur.execute("""
                INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight)
                VALUES (%s, %s, %s, %s, 'extends', 1.0)
            """, (edge_id, ws_id, node_ids[i], node_ids[i+1]))

    print(f"Successfully ingested {len(nodes)} nodes from SPEC.md into {ws_id}")

if __name__ == "__main__":
    # Ensure "system" user exists
    try:
        with db_cursor(commit=True) as cur:
            cur.execute("SELECT id FROM users WHERE id = 'system'")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users (id, display_name, email, email_verified)
                    VALUES ('system', 'System Template', 'system@memtrace.local', true)
                """)
        
        bootstrap_spec()
    except Exception as e:
        print(f"Error: {e}")
