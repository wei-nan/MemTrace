"""
Load examples/agent-loop-kb/ nodes and edges into a MemTrace workspace.

Usage (run inside the api container or with PYTHONPATH set):
    python -m scripts.load_agent_loop_kb --ws WS_ID --user USER_ID [--api http://...]

Or call load_agent_loop_kb_direct() from a Python REPL for in-process use.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the KB data relative to the repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_KB_DIR = _REPO_ROOT / "examples" / "agent-loop-kb"


def _load_json(name: str) -> list:
    path = _KB_DIR / name
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_agent_loop_kb_direct(ws_id: str, user_id: str) -> dict:
    """
    Load the agent-loop KB directly via the service layer (in-process).
    Call this from inside the API container (e.g. docker exec).
    """
    import sys, os
    # Ensure packages/api is on the path
    api_dir = Path(__file__).resolve().parent.parent
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))

    from core.database import db_cursor
    from services.nodes import create_node_in_db
    from services.edges import create_edge_in_db

    nodes = _load_json("nodes.json")
    edges = _load_json("edges.json")

    node_id_map: dict[str, str] = {}   # stable_key → actual DB id
    created_nodes = 0
    skipped_nodes = 0
    created_edges = 0
    skipped_edges = 0

    with db_cursor(commit=True) as cur:
        # Check workspace exists
        cur.execute("SELECT id FROM workspaces WHERE id = %s", (ws_id,))
        if not cur.fetchone():
            raise ValueError(f"Workspace {ws_id!r} not found")

        for node in nodes:
            stable_key = node["id"]  # e.g. "mem_loop001"

            # Check if a node with this title already exists (idempotent)
            cur.execute(
                "SELECT id FROM memory_nodes WHERE workspace_id=%s AND title=%s AND status='active'",
                (ws_id, node["title"]),
            )
            existing = cur.fetchone()
            if existing:
                node_id_map[stable_key] = existing["id"]
                skipped_nodes += 1
                logger.info(f"  skip (exists) {stable_key}: {node['title']}")
                continue

            node_data = {
                "title":          node["title"],
                "body":           node.get("body", ""),
                "content_type":   node["content_type"],
                "content_format": node.get("content_format", "markdown"),
                "tags":           node.get("tags", []),
                "visibility":     node.get("visibility", "public"),
                "source_type":    node.get("source_type", "human"),
                "status":         "active",
                "author":         user_id,
            }
            row = create_node_in_db(cur, ws_id, node_data)
            node_id_map[stable_key] = row["id"]
            created_nodes += 1
            logger.info(f"  created {stable_key} → {row['id']}: {node['title']}")

        for edge in edges:
            from_key = edge["from_id"]
            to_key   = edge["to_id"]
            from_id  = node_id_map.get(from_key)
            to_id    = node_id_map.get(to_key)
            if not from_id or not to_id:
                logger.warning(f"  skip edge {from_key}→{to_key}: node not mapped")
                skipped_edges += 1
                continue

            # Check for duplicate edge
            cur.execute(
                "SELECT id FROM edges WHERE workspace_id=%s AND from_id=%s AND to_id=%s AND relation=%s",
                (ws_id, from_id, to_id, edge["relation"]),
            )
            if cur.fetchone():
                skipped_edges += 1
                continue

            try:
                create_edge_in_db(cur, ws_id, {
                    "from_id":  from_id,
                    "to_id":    to_id,
                    "relation": edge["relation"],
                    "weight":   edge.get("weight", 0.5),
                })
                created_edges += 1
                logger.info(f"  edge {from_key}→{to_key} ({edge['relation']})")
            except Exception as e:
                logger.warning(f"  skip edge {from_key}→{to_key}: {e}")
                skipped_edges += 1

    return {
        "workspace_id":  ws_id,
        "created_nodes": created_nodes,
        "skipped_nodes": skipped_nodes,
        "created_edges": created_edges,
        "skipped_edges": skipped_edges,
        "node_id_map":   node_id_map,
    }


def load_agent_loop_kb_http(api_base: str, ws_id: str, api_key: str) -> dict:
    """
    Load the KB via the HTTP API (useful when running outside the container).
    Requires a valid API key with editor access to ws_id.
    """
    import urllib.request

    nodes = _load_json("nodes.json")
    edges = _load_json("edges.json")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    node_id_map: dict[str, str] = {}
    created_nodes = 0
    skipped_nodes = 0

    def post(path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(f"{api_base}{path}", data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise RuntimeError(f"HTTP {e.code}: {body}") from e

    for node in nodes:
        stable_key = node["id"]
        payload = {
            "title":          node["title"],
            "body":           node.get("body", ""),
            "content_type":   node["content_type"],
            "content_format": node.get("content_format", "markdown"),
            "tags":           node.get("tags", []),
            "visibility":     node.get("visibility", "public"),
            "source_type":    node.get("source_type", "human"),
        }
        try:
            result = post(f"/api/v1/kb/{ws_id}/nodes", payload)
            node_id = result.get("id") or (result.get("data") or {}).get("id")
            if node_id:
                node_id_map[stable_key] = node_id
                created_nodes += 1
                logger.info(f"  created {stable_key} → {node_id}")
            else:
                logger.warning(f"  no id in response for {stable_key}: {result}")
                skipped_nodes += 1
        except Exception as e:
            logger.warning(f"  skip {stable_key}: {e}")
            skipped_nodes += 1

    created_edges = 0
    skipped_edges = 0
    for edge in edges:
        from_id = node_id_map.get(edge["from_id"])
        to_id   = node_id_map.get(edge["to_id"])
        if not from_id or not to_id:
            skipped_edges += 1
            continue
        try:
            post(f"/api/v1/kb/{ws_id}/edges", {
                "from_id":  from_id,
                "to_id":    to_id,
                "relation": edge["relation"],
                "weight":   edge.get("weight", 0.5),
            })
            created_edges += 1
        except Exception as e:
            logger.warning(f"  skip edge {edge['from_id']}→{edge['to_id']}: {e}")
            skipped_edges += 1

    return {
        "workspace_id":  ws_id,
        "created_nodes": created_nodes,
        "skipped_nodes": skipped_nodes,
        "created_edges": created_edges,
        "skipped_edges": skipped_edges,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description="Load agent-loop KB into MemTrace")
    parser.add_argument("--ws",   required=True, help="Workspace ID")
    parser.add_argument("--user", help="User/author ID (for direct mode)")
    parser.add_argument("--api",  help="API base URL (for HTTP mode, e.g. http://localhost:8001)")
    parser.add_argument("--key",  help="API key (for HTTP mode)")
    args = parser.parse_args()

    if args.api:
        if not args.key:
            sys.exit("--key required in HTTP mode")
        result = load_agent_loop_kb_http(args.api.rstrip("/"), args.ws, args.key)
    else:
        if not args.user:
            sys.exit("--user required in direct mode")
        result = load_agent_loop_kb_direct(args.ws, args.user)

    print(json.dumps(result, indent=2, ensure_ascii=False))
