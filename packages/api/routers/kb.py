from datetime import datetime, timezone
from typing import Optional, List, Literal
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks

from core.database import db_cursor
from core.deps import get_current_user, get_current_user_optional
from core.security import compute_signature, generate_id
from core.ai import resolve_provider, embed, record_usage, AIProviderUnavailable
from models.kb import (
    NodeCreate, NodeResponse, NodeUpdate,
    EdgeCreate, EdgeResponse,
    RateEdgeRequest, TraverseEdgeRequest,
    WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate,
    WorkspaceAssociationResponse,
    GraphPreviewResponse,
)

router = APIRouter(prefix="/api/v1", tags=["knowledge-base"])

VALID_RELATIONS = {"depends_on", "extends", "related_to", "contradicts"}
VALID_KB_VIS    = {"public", "restricted", "private", "conditional_public"}
VALID_NODE_VIS  = {"public", "team", "private"}
VALID_CONTENT_T = {"factual", "procedural", "preference", "context"}
VALID_FORMAT    = {"plain", "markdown"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_ws_access(cur, ws_id: str, user: Optional[dict], write: bool = False):
    cur.execute("SELECT visibility, owner_id FROM workspaces WHERE id = %s", (ws_id,))
    ws = cur.fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    vis     = ws["visibility"]
    user_id = user["sub"] if user else None

    if user_id == ws["owner_id"]:
        return ws  # owner can always access

    if vis == "private":
        raise HTTPException(status_code=403, detail="Access denied")

    if vis == "public" and not write:
        return ws  # public read allowed

    if vis == "restricted" or write:
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        cur.execute(
            "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
            (ws_id, user_id),
        )
        member = cur.fetchone()
        if not member:
            raise HTTPException(status_code=403, detail="Access denied")
        if write and member["role"] not in ("editor", "admin"):
            raise HTTPException(status_code=403, detail="Editor or Admin role required")

    return ws

def _get_effective_role(cur, ws_id: str, owner_id: str, user_id: Optional[str]) -> Optional[str]:
    if not user_id: return None
    if user_id == owner_id: return "admin"
    cur.execute("SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s", (ws_id, user_id))
    m = cur.fetchone()
    return m["role"] if m else None

def _strip_body_if_viewer(node_row: dict, role: Optional[str]):
    # If the user is not editor/admin, they are acting as a viewer or public guest
    if role not in ("editor", "admin"):
        node_row["body_zh"] = ""
        node_row["body_en"] = ""
    return node_row


# ── Workspaces ────────────────────────────────────────────────────────────────

@router.get("/workspaces", response_model=list[WorkspaceResponse])
def list_workspaces(user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM workspaces
            WHERE owner_id = %s
               OR id IN (SELECT workspace_id FROM workspace_members WHERE user_id = %s)
               OR visibility IN ('public', 'conditional_public')
            ORDER BY updated_at DESC
        """, (user["sub"], user["sub"]))
        return cur.fetchall()


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
def create_workspace(body: WorkspaceCreate, user: dict = Depends(get_current_user)):
    if body.visibility not in VALID_KB_VIS:
        raise HTTPException(status_code=400, detail="Invalid visibility")
    ws_id = generate_id("ws")
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO workspaces (
                id, name_zh, name_en, visibility, kb_type, owner_id,
                archive_window_days, min_traversals
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            ws_id, body.name_zh, body.name_en, body.visibility, body.kb_type, user["sub"],
            body.archive_window_days, body.min_traversals
        ))
        return cur.fetchone()


@router.get("/workspaces/{ws_id}/graph-preview", response_model=GraphPreviewResponse)
def get_graph_preview(ws_id: str):
    """
    Publicly accessible de-identified graph preview for 'conditional_public' workspaces.
    """
    with db_cursor() as cur:
        cur.execute("SELECT visibility FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        if ws["visibility"] not in ("conditional_public", "public"):
            raise HTTPException(status_code=403, detail="Graph preview only available for public/conditional_public workspaces")

        # Fetch nodes and edges
        cur.execute("SELECT id, content_type FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
        nodes = cur.fetchall()
        cur.execute("SELECT from_id, to_id, relation FROM edges WHERE workspace_id = %s AND status = 'active'", (ws_id,))
        edges = cur.fetchall()

        # Mapping original IDs to anonymous preview IDs
        id_map = {node["id"]: f"p_node_{i}" for i, node in enumerate(nodes)}

        node_previews = [
            {"preview_id": id_map[n["id"]], "content_type": n["content_type"]}
            for n in nodes
        ]
        
        edge_previews = [
            {
                "from_preview_id": id_map[e["from_id"]],
                "to_preview_id": id_map[e["to_id"]],
                "relation": e["relation"]
            }
            for e in edges
            if e["from_id"] in id_map and e["to_id"] in id_map
        ]

        return {"nodes": node_previews, "edges": edge_previews}



@router.patch("/workspaces/{ws_id}", response_model=WorkspaceResponse)
def update_workspace(ws_id: str, body: WorkspaceUpdate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        # Check if user is owner
        cur.execute("SELECT owner_id FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["owner_id"] != user["sub"]:
            raise HTTPException(status_code=403, detail="Only workspace owner can update settings")

        updates = body.dict(exclude_unset=True)
        if not updates:
            return ws

        if "visibility" in updates and updates["visibility"] not in VALID_KB_VIS:
            raise HTTPException(status_code=400, detail="Invalid visibility")

        set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
        params = list(updates.values()) + [ws_id]
        
        cur.execute(f"UPDATE workspaces SET {set_clause} WHERE id = %s RETURNING *", params)
        return cur.fetchone()


# ── Associations ─────────────────────────────────────────────────────────────

@router.get("/workspaces/{ws_id}/associations", response_model=list[WorkspaceAssociationResponse])
def list_associations(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("""
            SELECT a.*, w.name_en AS target_name_en, w.name_zh AS target_name_zh
            FROM workspace_associations a
            JOIN workspaces w ON a.target_ws_id = w.id
            WHERE a.source_ws_id = %s
        """, (ws_id,))
        return cur.fetchall()

@router.post("/workspaces/{ws_id}/associations/{target_ws_id}", response_model=WorkspaceAssociationResponse)
def create_association(ws_id: str, target_ws_id: str, user: dict = Depends(get_current_user)):
    if ws_id == target_ws_id:
        raise HTTPException(status_code=400, detail="Cannot associate a workspace with itself")
    
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user) # Must have access to source
        _require_ws_access(cur, target_ws_id, user) # Must have access to target
        
        assoc_id = generate_id("asc")
        cur.execute("""
            INSERT INTO workspace_associations (id, source_ws_id, target_ws_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (source_ws_id, target_ws_id) DO UPDATE 
               SET created_at = now()
            RETURNING id, source_ws_id, target_ws_id, created_at
        """, (assoc_id, ws_id, target_ws_id))
        row = cur.fetchone()
        
        # Add names
        cur.execute("SELECT name_en, name_zh FROM workspaces WHERE id = %s", (target_ws_id,))
        names = cur.fetchone()
        return {**dict(row), "target_name_en": names["name_en"], "target_name_zh": names["name_zh"]}

@router.delete("/workspaces/{ws_id}/associations/{target_ws_id}", status_code=204)
def delete_association(ws_id: str, target_ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("DELETE FROM workspace_associations WHERE source_ws_id = %s AND target_ws_id = %s", (ws_id, target_ws_id))


@router.get("/workspaces/{ws_id}", response_model=WorkspaceResponse)
def get_workspace(ws_id: str, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("SELECT * FROM workspaces WHERE id = %s", (ws_id,))
        return cur.fetchone()


# ── Nodes ─────────────────────────────────────────────────────────────────────

@router.get("/workspaces/{ws_id}/nodes", response_model=list[NodeResponse])
def list_nodes(
    ws_id: str,
    q: Optional[str] = Query(None, description="Full-text keyword search across titles and body"),
    tag: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    status: str = Query("active"),
    user: dict = Depends(get_current_user_optional),
):
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user)
        filters = ["workspace_id = %s"]
        params: list = [ws_id]
        if status != "all":
            filters.append("status = %s")
            params.append(status)
        if q:
            filters.append(
                "(title_zh ILIKE %s OR title_en ILIKE %s OR body_zh ILIKE %s OR body_en ILIKE %s)"
            )
            like = f"%{q}%"
            params += [like, like, like, like]
        if tag:
            filters.append("%s = ANY(tags)")
            params.append(tag)
        if content_type:
            filters.append("content_type = %s")
            params.append(content_type)
        where = " AND ".join(filters)
        params += [limit, offset]
        cur.execute(
            f"SELECT * FROM memory_nodes WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params,
        )
        nodes = cur.fetchall()
        
        # Determine effective role for content stripping
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"] if user else None)
        return [_strip_body_if_viewer(n, role) for n in nodes]

async def _bg_embed_node(ws_id: str, node_id: str, text: str, user_id: str):
    try:
        resolved = resolve_provider(user_id, "embedding")
        vector, tokens = await embed(resolved, text)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE memory_nodes SET embedding = %s WHERE id = %s AND workspace_id = %s",
                (vector, node_id, ws_id)
            )
        record_usage(resolved, "embedding", tokens, ws_id, node_id)
    except Exception as e:
        print(f"BG Embedding failed for node {node_id}: {e}")

@router.post("/workspaces/{ws_id}/nodes/search-semantic", response_model=List[NodeResponse])
async def search_nodes_semantic(ws_id: str, query: str, limit: int = 10, user: dict = Depends(get_current_user)):
    try:
        resolved = resolve_provider(user["sub"], "embedding")
        vector, tokens = await embed(resolved, query)
        record_usage(resolved, "embedding", tokens, ws_id)
        
        with db_cursor() as cur:
            _require_ws_access(cur, ws_id, user)
            cur.execute("""
                SELECT *, (1 - (embedding <=> %s::vector)) AS similarity
                FROM memory_nodes
                WHERE workspace_id = %s AND embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT %s
            """, (vector, ws_id, limit))
            return cur.fetchall()
    except AIProviderUnavailable as e:
        raise HTTPException(status_code=402, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding error: {str(e)}")


@router.get("/workspaces/{ws_id}/nodes/{node_id}", response_model=NodeResponse)
def get_node(ws_id: str, node_id: str, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user)
        cur.execute(
            "SELECT * FROM memory_nodes WHERE id = %s AND workspace_id = %s",
            (node_id, ws_id),
        )
        node = cur.fetchone()
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
            
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"] if user else None)
        return _strip_body_if_viewer(node, role)


@router.post("/workspaces/{ws_id}/nodes", response_model=NodeResponse, status_code=201)
def create_node(ws_id: str, body: NodeCreate, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    if body.content_type not in VALID_CONTENT_T:
        raise HTTPException(status_code=400, detail="Invalid content_type")
    if body.content_format not in VALID_FORMAT:
        raise HTTPException(status_code=400, detail="Invalid content_format")
    if body.visibility not in VALID_NODE_VIS:
        raise HTTPException(status_code=400, detail="Invalid visibility")
    if not body.body_zh and not body.body_en:
        raise HTTPException(status_code=400, detail="At least one body language field must be non-empty")

    author = user["sub"]
    title   = {"zh-TW": body.title_zh, "en": body.title_en}
    content = {"type": body.content_type, "format": body.content_format,
               "body": {"zh-TW": body.body_zh, "en": body.body_en}}
    sig = compute_signature(title, content, body.tags, author)
    node_id = generate_id("mem")

    with db_cursor(commit=True) as cur:
        ws     = _require_ws_access(cur, ws_id, user, write=True)
        role   = _get_effective_role(cur, ws_id, ws["owner_id"], author)
        
        if role == "editor":
            review_id = generate_id("rev")
            # Construct suggested node data
            suggested_node = {
                "id": node_id,
                "workspace_id": ws_id,
                "title_zh": body.title_zh,
                "title_en": body.title_en,
                "content_type": body.content_type,
                "content_format": body.content_format,
                "body_zh": body.body_zh,
                "body_en": body.body_en,
                "tags": body.tags,
                "visibility": body.visibility,
                "author": author,
                "signature": sig,
                "source_type": "human"
            }
            cur.execute("""
                INSERT INTO review_queue (id, workspace_id, node_data, source_info, status)
                VALUES (%s, %s, %s, %s, 'pending')
            """, (review_id, ws_id, json.dumps(suggested_node), f"Proposed new node by {author}"))
            
            raise HTTPException(status_code=202, detail="Your new node has been submitted for review")

        cur.execute("""
            INSERT INTO memory_nodes (
                id, workspace_id,
                title_zh, title_en,
                content_type, content_format, body_zh, body_en,
                tags, visibility,
                author, signature, source_type,
                copied_from_node, copied_from_ws
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'human',%s,%s)
            RETURNING *
        """, (
            node_id, ws_id,
            body.title_zh, body.title_en,
            body.content_type, body.content_format,
            body.body_zh, body.body_en,
            body.tags, body.visibility,
            author, sig,
            body.copied_from_node, body.copied_from_ws
        ))
        node = cur.fetchone()
        
        # Trigger background embedding
        bg_text = f"{body.title_zh}\n{body.title_en}\n{body.body_zh}\n{body.body_en}"
        background_tasks.add_task(_bg_embed_node, ws_id, node_id, bg_text, user["sub"])
        
        return node


@router.patch("/workspaces/{ws_id}/nodes/{node_id}", response_model=NodeResponse)
def update_node(ws_id: str, node_id: str, body: NodeUpdate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True)
        cur.execute(
            "SELECT * FROM memory_nodes WHERE id = %s AND workspace_id = %s",
            (node_id, ws_id),
        )
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Node not found")

        updates: dict = {k: v for k, v in body.model_dump(exclude_none=True).items()}
        if not updates:
            return existing

        # Recompute signature if any content field changed
        content_keys = {"title_zh", "title_en", "content_type", "content_format", "body_zh", "body_en", "tags"}
        if updates.keys() & content_keys:
            merged = dict(existing) | updates
            sig = compute_signature(
                {"zh-TW": merged["title_zh"], "en": merged["title_en"]},
                {"type": merged["content_type"], "format": merged["content_format"],
                 "body": {"zh-TW": merged["body_zh"], "en": merged["body_en"]}},
                merged["tags"],
                user["sub"],
            )
            updates["signature"] = sig
            updates["updated_at"] = datetime.now(timezone.utc)

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        params     = list(updates.values()) + [node_id, ws_id]

        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role == "editor":
            # Redirect to review queue
            review_id = generate_id("rev")
            # We want to store the "target updated state" in review queue
            suggested_node = dict(existing) | updates
            # Remove DB internal fields before storing in suggested_node if necessary
            # For simplicity, we just store the whole thing
            cur.execute("""
                INSERT INTO review_queue (id, workspace_id, node_data, source_info, status)
                VALUES (%s, %s, %s, %s, 'pending')
            """, (review_id, ws_id, json.dumps(suggested_node), f"Proposed edit by {user['sub']} for {node_id}"))
            
            # Return existing node but maybe with a flag? or just raise 202
            raise HTTPException(status_code=202, detail="Your changes have been submitted for review")

        cur.execute(
            f"UPDATE memory_nodes SET {set_clause} WHERE id = %s AND workspace_id = %s RETURNING *",
            params,
        )
        return cur.fetchone()


@router.delete("/workspaces/{ws_id}/nodes/{node_id}", status_code=204)
def delete_node(ws_id: str, node_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True)
        cur.execute(
            "DELETE FROM memory_nodes WHERE id = %s AND workspace_id = %s",
            (node_id, ws_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Node not found")


# ── Edges ─────────────────────────────────────────────────────────────────────

@router.get("/workspaces/{ws_id}/edges", response_model=list[EdgeResponse])
def list_edges(
    ws_id: str,
    node_id: Optional[str] = Query(None, description="Filter edges connected to this node"),
    user: dict = Depends(get_current_user_optional),
):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        if node_id:
            cur.execute("""
                SELECT *,
                  CASE WHEN rating_count > 0 THEN ROUND(rating_sum / rating_count, 2) ELSE NULL END AS rating_avg
                FROM edges
                WHERE workspace_id = %s AND (from_id = %s OR to_id = %s)
                ORDER BY weight DESC
            """, (ws_id, node_id, node_id))
        else:
            cur.execute("""
                SELECT *,
                  CASE WHEN rating_count > 0 THEN ROUND(rating_sum / rating_count, 2) ELSE NULL END AS rating_avg
                FROM edges WHERE workspace_id = %s AND status = 'active' ORDER BY weight DESC
            """, (ws_id,))
        return cur.fetchall()


@router.post("/workspaces/{ws_id}/edges", response_model=EdgeResponse, status_code=201)
def create_edge(ws_id: str, body: EdgeCreate, user: dict = Depends(get_current_user)):
    if body.relation not in VALID_RELATIONS:
        raise HTTPException(status_code=400, detail="Invalid relation type")
    if body.from_id == body.to_id:
        raise HTTPException(status_code=400, detail="Cannot link a node to itself")
    if not (0.1 <= body.weight <= 1.0):
        raise HTTPException(status_code=400, detail="Weight must be between 0.1 and 1.0")

    edge_id = generate_id("edge")
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True)

        # Verify both nodes belong to this workspace
        for nid in (body.from_id, body.to_id):
            cur.execute(
                "SELECT id FROM memory_nodes WHERE id = %s AND workspace_id = %s", (nid, ws_id)
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Node not found: {nid}")

        # Choose default half-life based on node content_type (SPEC §7.1)
        if body.half_life_days == 30: # If using old default
            cur.execute("SELECT content_type FROM memory_nodes WHERE id = %s", (body.from_id,))
            node_row = cur.fetchone()
            if node_row:
                ct = node_row["content_type"]
                if   ct == "factual":    body.half_life_days = 365
                elif ct == "procedural": body.half_life_days = 90
                elif ct == "preference": body.half_life_days = 30
                elif ct == "context":    body.half_life_days = 14

        try:
            cur.execute("""
                INSERT INTO edges (
                    id, workspace_id, from_id, to_id, relation, 
                    weight, half_life_days, pinned
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *,
                  CASE WHEN rating_count > 0 THEN ROUND(rating_sum / rating_count, 2) ELSE NULL END AS rating_avg
            """, (edge_id, ws_id, body.from_id, body.to_id, body.relation, body.weight, body.half_life_days, body.pinned))
            return cur.fetchone()
        except Exception as e:
            if "unique_edge" in str(e):
                raise HTTPException(status_code=409, detail="Edge with this relation already exists")
            raise


# ── Traversal & Rating ────────────────────────────────────────────────────────

@router.post("/nodes/{node_id}/traverse", status_code=204)
def traverse_node(node_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        is_new = not _actor_has_traversed_node(cur, node_id, user["sub"])
        cur.execute("""
            INSERT INTO traversal_log (node_id, actor_id) VALUES (%s, %s)
        """, (node_id, user["sub"]))
        cur.execute("""
            UPDATE memory_nodes SET
                traversal_count        = traversal_count + 1,
                unique_traverser_count = unique_traverser_count + %s
            WHERE id = %s
        """, (1 if is_new else 0, node_id))


@router.post("/edges/{edge_id}/traverse", status_code=204)
def traverse_edge(edge_id: str, body: TraverseEdgeRequest, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT from_id, to_id FROM edges WHERE id = %s", (edge_id,))
        edge = cur.fetchone()
        if not edge:
            raise HTTPException(status_code=404, detail="Edge not found")
        cur.execute(
            "SELECT record_traversal(%s, %s, NULL, %s)",
            (edge_id, user["sub"], body.note),
        )


@router.post("/edges/{edge_id}/rate", status_code=204)
def rate_edge(edge_id: str, body: RateEdgeRequest, user: dict = Depends(get_current_user)):
    if not (1 <= body.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM edges WHERE id = %s", (edge_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Edge not found")
        cur.execute(
            "SELECT record_traversal(%s, %s, %s, %s)",
            (edge_id, user["sub"], body.rating, body.note),
        )


def _actor_has_traversed_node(cur, node_id: str, actor_id: str) -> bool:
    cur.execute(
        "SELECT 1 FROM traversal_log WHERE node_id = %s AND actor_id = %s",
        (node_id, actor_id),
    )
    return bool(cur.fetchone())
