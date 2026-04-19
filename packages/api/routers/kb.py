from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from core.database import db_cursor
from core.deps import get_current_user, get_current_user_optional
from core.diff import build_node_diff
from core.security import compute_signature, generate_id
from core.ai import resolve_provider, embed, record_usage, AIProviderUnavailable
from models.kb import (
    EdgeCreate,
    EdgeResponse,
    GraphPreviewResponse,
    NodeCreate,
    NodeResponse,
    NodeUpdate,
    RateEdgeRequest,
    TraverseEdgeRequest,
    WorkspaceAssociationResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from models.review import NodeRevisionMetaResponse, NodeRevisionResponse

router = APIRouter(prefix="/api/v1", tags=["knowledge-base"])

VALID_RELATIONS = {"depends_on", "extends", "related_to", "contradicts"}
VALID_KB_VIS = {"public", "restricted", "private", "conditional_public"}
VALID_NODE_VIS = {"public", "team", "private"}
VALID_CONTENT_T = {"factual", "procedural", "preference", "context"}
VALID_FORMAT = {"plain", "markdown"}
NODE_EDITABLE_FIELDS = [
    "title_zh",
    "title_en",
    "content_type",
    "content_format",
    "body_zh",
    "body_en",
    "tags",
    "visibility",
]


def _require_ws_access(cur, ws_id: str, user: Optional[dict], write: bool = False):
    cur.execute("SELECT visibility, owner_id FROM workspaces WHERE id = %s", (ws_id,))
    ws = cur.fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    vis = ws["visibility"]
    user_id = user["sub"] if user else None

    if user_id == ws["owner_id"]:
        return ws

    if vis == "private":
        raise HTTPException(status_code=403, detail="Access denied")

    if vis == "public" and not write:
        return ws

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
    if not user_id:
        return None
    if user_id == owner_id:
        return "admin"
    cur.execute(
        "SELECT role FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
        (ws_id, user_id),
    )
    row = cur.fetchone()
    return row["role"] if row else None


def _strip_body_if_viewer(node_row: dict, role: Optional[str]):
    if role not in ("editor", "admin"):
        node_row = dict(node_row)
        node_row["body_zh"] = ""
        node_row["body_en"] = ""
    return node_row


def _validate_node_payload(data: dict):
    if data.get("content_type") not in VALID_CONTENT_T:
        raise HTTPException(status_code=400, detail="Invalid content_type")
    if data.get("content_format") not in VALID_FORMAT:
        raise HTTPException(status_code=400, detail="Invalid content_format")
    if data.get("visibility") not in VALID_NODE_VIS:
        raise HTTPException(status_code=400, detail="Invalid visibility")
    if not (data.get("body_zh") or data.get("body_en")):
        raise HTTPException(status_code=400, detail="At least one body language field must be non-empty")


def _node_row_to_snapshot(row: dict | None) -> dict | None:
    if not row:
        return None
    return {field: (list(row[field]) if field == "tags" and row.get(field) is not None else row.get(field)) for field in NODE_EDITABLE_FIELDS}


def _prepare_node_data(data: dict, author: str, source_type: str = "human") -> dict:
    payload = {field: data.get(field) for field in NODE_EDITABLE_FIELDS}
    payload["tags"] = list(payload.get("tags") or [])
    _validate_node_payload(payload)
    payload["author"] = data.get("author") or author
    payload["source_type"] = data.get("source_type") or source_type
    payload["signature"] = compute_signature(
        {"zh-TW": payload["title_zh"], "en": payload["title_en"]},
        {
            "type": payload["content_type"],
            "format": payload["content_format"],
            "body": {"zh-TW": payload["body_zh"], "en": payload["body_en"]},
        },
        payload["tags"],
        payload["author"],
    )
    return payload


def _create_node_in_db(cur, ws_id: str, node_data: dict) -> dict:
    payload = _prepare_node_data(node_data, node_data["author"], node_data.get("source_type", "human"))
    node_id = node_data.get("id") or generate_id("mem")
    cur.execute(
        """
        INSERT INTO memory_nodes (
            id, workspace_id, title_zh, title_en, content_type, content_format, body_zh, body_en,
            tags, visibility, author, signature, source_type, copied_from_node, copied_from_ws
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING *
        """,
        (
            node_id,
            ws_id,
            payload["title_zh"],
            payload["title_en"],
            payload["content_type"],
            payload["content_format"],
            payload["body_zh"],
            payload["body_en"],
            payload["tags"],
            payload["visibility"],
            payload["author"],
            payload["signature"],
            payload["source_type"],
            node_data.get("copied_from_node"),
            node_data.get("copied_from_ws"),
        ),
    )
    return cur.fetchone()


def _update_node_in_db(cur, ws_id: str, node_id: str, node_data: dict, actor_id: str) -> dict:
    cur.execute("SELECT * FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
    existing = cur.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Node not found")

    merged = {**dict(existing), **{field: node_data.get(field, existing.get(field)) for field in NODE_EDITABLE_FIELDS}}
    payload = _prepare_node_data(merged, actor_id, merged.get("source_type", "human"))
    cur.execute(
        """
        UPDATE memory_nodes
        SET title_zh = %s, title_en = %s, content_type = %s, content_format = %s,
            body_zh = %s, body_en = %s, tags = %s, visibility = %s, signature = %s, updated_at = %s
        WHERE id = %s AND workspace_id = %s
        RETURNING *
        """,
        (
            payload["title_zh"],
            payload["title_en"],
            payload["content_type"],
            payload["content_format"],
            payload["body_zh"],
            payload["body_en"],
            payload["tags"],
            payload["visibility"],
            payload["signature"],
            datetime.now(timezone.utc),
            node_id,
            ws_id,
        ),
    )
    return cur.fetchone()


def _delete_node_in_db(cur, ws_id: str, node_id: str):
    cur.execute("DELETE FROM memory_nodes WHERE id = %s AND workspace_id = %s RETURNING *", (node_id, ws_id))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Node not found")
    return row


def _write_node_revision(
    cur,
    node_id: str,
    workspace_id: str,
    snapshot: dict,
    signature: str,
    proposer_type: str,
    proposer_id: Optional[str],
    review_id: Optional[str],
):
    cur.execute("SELECT COALESCE(MAX(revision_no), 0) AS max_rev FROM node_revisions WHERE node_id = %s", (node_id,))
    revision_no = int(cur.fetchone()["max_rev"]) + 1
    cur.execute(
        """
        INSERT INTO node_revisions (id, node_id, workspace_id, revision_no, snapshot, signature, proposer_type, proposer_id, review_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            generate_id("nrev"),
            node_id,
            workspace_id,
            revision_no,
            json.dumps(snapshot, ensure_ascii=False),
            signature,
            proposer_type,
            proposer_id,
            review_id,
        ),
    )
    cur.execute(
        """
        DELETE FROM node_revisions
        WHERE id IN (
          SELECT id FROM node_revisions
          WHERE node_id = %s
          ORDER BY revision_no DESC
          OFFSET 10
        )
        """,
        (node_id,),
    )


def _propose_change(
    cur,
    ws_id: str,
    change_type: Literal["create", "update", "delete"],
    target_node_id: Optional[str],
    node_data: Optional[dict],
    proposer_type: Literal["human", "ai"],
    proposer_id: Optional[str],
    proposer_meta: Optional[dict] = None,
    suggested_edges: Optional[list[dict]] = None,
    source_info: Optional[str] = None,
) -> str:
    before_snapshot = None
    after_snapshot = None

    if target_node_id:
        cur.execute("SELECT * FROM memory_nodes WHERE id = %s AND workspace_id = %s", (target_node_id, ws_id))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Target node not found")
        before_snapshot = _node_row_to_snapshot(existing)

    if change_type != "delete":
        payload = dict(node_data or {})
        if change_type == "update" and before_snapshot:
            payload = {**before_snapshot, **payload}
        payload["tags"] = list(payload.get("tags") or [])
        after_snapshot = _prepare_node_data(payload, payload.get("author") or proposer_id or "system", payload.get("source_type", proposer_type))
        after_snapshot = {field: after_snapshot[field] for field in NODE_EDITABLE_FIELDS} | {
            "author": payload.get("author") or proposer_id,
            "source_type": payload.get("source_type", proposer_type),
            "signature": after_snapshot["signature"],
        }

    diff_summary = build_node_diff(before_snapshot, after_snapshot, change_type)
    review_id = generate_id("rev")
    cur.execute(
        """
        INSERT INTO review_queue (
            id, workspace_id, change_type, target_node_id, before_snapshot, node_data, diff_summary,
            suggested_edges, status, source_info, proposer_type, proposer_id, proposer_meta
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s)
        """,
        (
            review_id,
            ws_id,
            change_type,
            target_node_id,
            json.dumps(before_snapshot, ensure_ascii=False) if before_snapshot is not None else None,
            json.dumps(after_snapshot or {}, ensure_ascii=False),
            json.dumps(diff_summary, ensure_ascii=False),
            json.dumps(suggested_edges or [], ensure_ascii=False),
            source_info,
            proposer_type,
            proposer_id,
            json.dumps(proposer_meta or {}, ensure_ascii=False) if proposer_meta is not None else None,
        ),
    )
    return review_id


async def _bg_embed_node(ws_id: str, node_id: str, text: str, user_id: str):
    try:
        resolved = resolve_provider(user_id, "embedding")
        vector, tokens = await embed(resolved, text)
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE memory_nodes SET embedding = %s WHERE id = %s AND workspace_id = %s", (vector, node_id, ws_id))
        record_usage(resolved, "embedding", tokens, ws_id, node_id)
    except Exception as exc:
        print(f"BG Embedding failed for node {node_id}: {exc}")


@router.get("/workspaces", response_model=list[WorkspaceResponse])
def list_workspaces(user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM workspaces
            WHERE owner_id = %s
               OR id IN (SELECT workspace_id FROM workspace_members WHERE user_id = %s)
               OR visibility IN ('public', 'conditional_public')
            ORDER BY updated_at DESC
            """,
            (user["sub"], user["sub"]),
        )
        return cur.fetchall()


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
def create_workspace(body: WorkspaceCreate, user: dict = Depends(get_current_user)):
    if body.visibility not in VALID_KB_VIS:
        raise HTTPException(status_code=400, detail="Invalid visibility")
    ws_id = generate_id("ws")
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO workspaces (
                id, name_zh, name_en, visibility, kb_type, owner_id, archive_window_days, min_traversals
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (ws_id, body.name_zh, body.name_en, body.visibility, body.kb_type, user["sub"], body.archive_window_days, body.min_traversals),
        )
        return cur.fetchone()


@router.get("/workspaces/{ws_id}/graph-preview", response_model=GraphPreviewResponse)
def get_graph_preview(ws_id: str):
    with db_cursor() as cur:
        cur.execute("SELECT visibility FROM workspaces WHERE id = %s", (ws_id,))
        ws = cur.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if ws["visibility"] not in ("conditional_public", "public"):
            raise HTTPException(status_code=403, detail="Graph preview only available for public/conditional_public workspaces")
        cur.execute("SELECT id, content_type FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
        nodes = cur.fetchall()
        cur.execute("SELECT from_id, to_id, relation FROM edges WHERE workspace_id = %s AND status = 'active'", (ws_id,))
        edges = cur.fetchall()
        id_map = {node["id"]: f"p_node_{i}" for i, node in enumerate(nodes)}
        return {
            "nodes": [{"preview_id": id_map[n["id"]], "content_type": n["content_type"]} for n in nodes],
            "edges": [
                {"from_preview_id": id_map[e["from_id"]], "to_preview_id": id_map[e["to_id"]], "relation": e["relation"]}
                for e in edges
                if e["from_id"] in id_map and e["to_id"] in id_map
            ],
        }


@router.patch("/workspaces/{ws_id}", response_model=WorkspaceResponse)
def update_workspace(ws_id: str, body: WorkspaceUpdate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM workspaces WHERE id = %s", (ws_id,))
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
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        cur.execute(f"UPDATE workspaces SET {set_clause} WHERE id = %s RETURNING *", list(updates.values()) + [ws_id])
        return cur.fetchone()


@router.get("/workspaces/{ws_id}/associations", response_model=list[WorkspaceAssociationResponse])
def list_associations(ws_id: str, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            """
            SELECT a.*, w.name_en AS target_name_en, w.name_zh AS target_name_zh
            FROM workspace_associations a
            JOIN workspaces w ON a.target_ws_id = w.id
            WHERE a.source_ws_id = %s
            """,
            (ws_id,),
        )
        return cur.fetchall()


@router.post("/workspaces/{ws_id}/associations/{target_ws_id}", response_model=WorkspaceAssociationResponse)
def create_association(ws_id: str, target_ws_id: str, user: dict = Depends(get_current_user)):
    if ws_id == target_ws_id:
        raise HTTPException(status_code=400, detail="Cannot associate a workspace with itself")
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user)
        _require_ws_access(cur, target_ws_id, user)
        assoc_id = generate_id("asc")
        cur.execute(
            """
            INSERT INTO workspace_associations (id, source_ws_id, target_ws_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (source_ws_id, target_ws_id) DO UPDATE SET created_at = now()
            RETURNING id, source_ws_id, target_ws_id, created_at
            """,
            (assoc_id, ws_id, target_ws_id),
        )
        row = cur.fetchone()
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


@router.get("/workspaces/{ws_id}/nodes", response_model=list[NodeResponse])
def list_nodes(
    ws_id: str,
    q: Optional[str] = Query(None),
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
            filters.append("(title_zh ILIKE %s OR title_en ILIKE %s OR body_zh ILIKE %s OR body_en ILIKE %s)")
            like = f"%{q}%"
            params += [like, like, like, like]
        if tag:
            filters.append("%s = ANY(tags)")
            params.append(tag)
        if content_type:
            filters.append("content_type = %s")
            params.append(content_type)
        params += [limit, offset]
        cur.execute(f"SELECT * FROM memory_nodes WHERE {' AND '.join(filters)} ORDER BY created_at DESC LIMIT %s OFFSET %s", params)
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"] if user else None)
        return [_strip_body_if_viewer(row, role) for row in cur.fetchall()]


@router.post("/workspaces/{ws_id}/nodes/search-semantic", response_model=List[NodeResponse])
async def search_nodes_semantic(ws_id: str, query: str, limit: int = 10, user: dict = Depends(get_current_user)):
    try:
        resolved = resolve_provider(user["sub"], "embedding")
        vector, tokens = await embed(resolved, query)
        record_usage(resolved, "embedding", tokens, ws_id)
        with db_cursor() as cur:
            _require_ws_access(cur, ws_id, user)
            cur.execute(
                """
                SELECT *, (1 - (embedding <=> %s::vector)) AS similarity
                FROM memory_nodes
                WHERE workspace_id = %s AND embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT %s
                """,
                (vector, ws_id, limit),
            )
            return cur.fetchall()
    except AIProviderUnavailable as exc:
        raise HTTPException(status_code=402, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Embedding error: {exc}")


@router.get("/workspaces/{ws_id}/nodes/{node_id}", response_model=NodeResponse)
def get_node(ws_id: str, node_id: str, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        ws = _require_ws_access(cur, ws_id, user)
        cur.execute("SELECT * FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
        node = cur.fetchone()
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"] if user else None)
        return _strip_body_if_viewer(node, role)


@router.post("/workspaces/{ws_id}/nodes", response_model=NodeResponse, status_code=201)
def create_node(ws_id: str, body: NodeCreate, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    payload = body.model_dump()
    _validate_node_payload(payload)
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True)
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        proposer_id = user["sub"]
        if role == "editor":
            review_id = _propose_change(
                cur,
                ws_id,
                "create",
                None,
                payload | {"author": proposer_id, "source_type": "human"},
                "human",
                proposer_id,
                {"source": "node_editor"},
                source_info=f"Proposed new node by {proposer_id}",
            )
            from core.ai_review import run_ai_review_for_item
            background_tasks.add_task(run_ai_review_for_item, review_id)
            raise HTTPException(status_code=202, detail="Your new node has been submitted for review")

        node = _create_node_in_db(cur, ws_id, payload | {"author": proposer_id, "source_type": "human"})
        _write_node_revision(cur, node["id"], ws_id, _node_row_to_snapshot(node), node["signature"], "human", proposer_id, None)
        background_tasks.add_task(_bg_embed_node, ws_id, node["id"], f"{node['title_zh']}\n{node['title_en']}\n{node['body_zh']}\n{node['body_en']}", user["sub"])
        return node


@router.patch("/workspaces/{ws_id}/nodes/{node_id}", response_model=NodeResponse)
def update_node(ws_id: str, node_id: str, body: NodeUpdate, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    updates = body.model_dump(exclude_none=True)
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True)
        cur.execute("SELECT * FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Node not found")
        if not updates:
            return existing
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role == "editor":
            review_id = _propose_change(
                cur,
                ws_id,
                "update",
                node_id,
                updates,
                "human",
                user["sub"],
                {"source": "node_editor"},
                source_info=f"Proposed edit by {user['sub']} for {node_id}",
            )
            from core.ai_review import run_ai_review_for_item
            background_tasks.add_task(run_ai_review_for_item, review_id)
            raise HTTPException(status_code=202, detail="Your changes have been submitted for review")

        node = _update_node_in_db(cur, ws_id, node_id, updates, user["sub"])
        _write_node_revision(cur, node["id"], ws_id, _node_row_to_snapshot(node), node["signature"], "human", user["sub"], None)
        return node


@router.delete("/workspaces/{ws_id}/nodes/{node_id}", status_code=204)
def delete_node(ws_id: str, node_id: str, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True)
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        if role == "editor":
            review_id = _propose_change(
                cur,
                ws_id,
                "delete",
                node_id,
                None,
                "human",
                user["sub"],
                {"source": "node_editor"},
                source_info=f"Proposed delete by {user['sub']} for {node_id}",
            )
            from core.ai_review import run_ai_review_for_item
            background_tasks.add_task(run_ai_review_for_item, review_id)
            return
        _delete_node_in_db(cur, ws_id, node_id)


@router.get("/workspaces/{ws_id}/nodes/{node_id}/revisions", response_model=list[NodeRevisionMetaResponse])
def list_node_revisions(ws_id: str, node_id: str, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            """
            SELECT id, node_id, workspace_id, revision_no, signature, proposer_type, proposer_id, review_id, created_at
            FROM node_revisions
            WHERE workspace_id = %s AND node_id = %s
            ORDER BY revision_no DESC
            """,
            (ws_id, node_id),
        )
        return cur.fetchall()


@router.get("/workspaces/{ws_id}/nodes/{node_id}/revisions/{revision_no}", response_model=NodeRevisionResponse)
def get_node_revision(ws_id: str, node_id: str, revision_no: int, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("SELECT * FROM node_revisions WHERE workspace_id = %s AND node_id = %s AND revision_no = %s", (ws_id, node_id, revision_no))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Revision not found")
        return row


@router.get("/workspaces/{ws_id}/nodes/{node_id}/revisions/{rev_a}/diff/{rev_b}")
def diff_node_revisions(ws_id: str, node_id: str, rev_a: int, rev_b: int, user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute(
            "SELECT revision_no, snapshot FROM node_revisions WHERE workspace_id = %s AND node_id = %s AND revision_no IN (%s, %s)",
            (ws_id, node_id, rev_a, rev_b),
        )
        rows = {row["revision_no"]: row["snapshot"] for row in cur.fetchall()}
        if rev_a not in rows or rev_b not in rows:
            raise HTTPException(status_code=404, detail="Revision not found")
        return build_node_diff(rows[rev_a], rows[rev_b], "update")


@router.post("/workspaces/{ws_id}/nodes/{node_id}/revisions/{revision_no}/restore")
def restore_node_revision(ws_id: str, node_id: str, revision_no: int, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        ws = _require_ws_access(cur, ws_id, user, write=True)
        cur.execute("SELECT snapshot FROM node_revisions WHERE workspace_id = %s AND node_id = %s AND revision_no = %s", (ws_id, node_id, revision_no))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Revision not found")
        role = _get_effective_role(cur, ws_id, ws["owner_id"], user["sub"])
        review_id = _propose_change(
            cur, ws_id, "update", node_id, row["snapshot"], "human", user["sub"], {"source": "restore", "revision_no": revision_no},
            source_info=f"Restore node {node_id} from revision {revision_no}"
        )
        from core.ai_review import run_ai_review_for_item
        background_tasks.add_task(run_ai_review_for_item, review_id)
        return {"review_id": review_id, "status": "pending_review"}


@router.get("/workspaces/{ws_id}/edges", response_model=list[EdgeResponse])
def list_edges(ws_id: str, node_id: Optional[str] = Query(None), user: dict = Depends(get_current_user_optional)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        if node_id:
            cur.execute(
                """
                SELECT *, CASE WHEN rating_count > 0 THEN ROUND(rating_sum / rating_count, 2) ELSE NULL END AS rating_avg
                FROM edges
                WHERE workspace_id = %s AND (from_id = %s OR to_id = %s)
                ORDER BY weight DESC
                """,
                (ws_id, node_id, node_id),
            )
        else:
            cur.execute(
                """
                SELECT *, CASE WHEN rating_count > 0 THEN ROUND(rating_sum / rating_count, 2) ELSE NULL END AS rating_avg
                FROM edges WHERE workspace_id = %s AND status = 'active' ORDER BY weight DESC
                """,
                (ws_id,),
            )
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
        for nid in (body.from_id, body.to_id):
            cur.execute("SELECT id FROM memory_nodes WHERE id = %s AND workspace_id = %s", (nid, ws_id))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Node not found: {nid}")
        if body.half_life_days == 30:
            cur.execute("SELECT content_type FROM memory_nodes WHERE id = %s", (body.from_id,))
            row = cur.fetchone()
            if row:
                body.half_life_days = {"factual": 365, "procedural": 90, "preference": 30, "context": 14}.get(row["content_type"], 30)
        try:
            cur.execute(
                """
                INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, half_life_days, pinned)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *, CASE WHEN rating_count > 0 THEN ROUND(rating_sum / rating_count, 2) ELSE NULL END AS rating_avg
                """,
                (edge_id, ws_id, body.from_id, body.to_id, body.relation, body.weight, body.half_life_days, body.pinned),
            )
            return cur.fetchone()
        except Exception as exc:
            if "unique_edge" in str(exc):
                raise HTTPException(status_code=409, detail="Edge with this relation already exists")
            raise


@router.post("/nodes/{node_id}/traverse", status_code=204)
def traverse_node(node_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        is_new = not _actor_has_traversed_node(cur, node_id, user["sub"])
        cur.execute("INSERT INTO traversal_log (node_id, actor_id) VALUES (%s, %s)", (node_id, user["sub"]))
        cur.execute(
            """
            UPDATE memory_nodes SET traversal_count = traversal_count + 1, unique_traverser_count = unique_traverser_count + %s
            WHERE id = %s
            """,
            (1 if is_new else 0, node_id),
        )


@router.post("/edges/{edge_id}/traverse", status_code=204)
def traverse_edge(edge_id: str, body: TraverseEdgeRequest, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT from_id, to_id FROM edges WHERE id = %s", (edge_id,))
        edge = cur.fetchone()
        if not edge:
            raise HTTPException(status_code=404, detail="Edge not found")
        cur.execute("SELECT record_traversal(%s, %s, NULL, %s)", (edge_id, user["sub"], body.note))


@router.post("/edges/{edge_id}/rate", status_code=204)
def rate_edge(edge_id: str, body: RateEdgeRequest, user: dict = Depends(get_current_user)):
    if not (1 <= body.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM edges WHERE id = %s", (edge_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Edge not found")
        cur.execute("SELECT record_traversal(%s, %s, %s, %s)", (edge_id, user["sub"], body.rating, body.note))


def _actor_has_traversed_node(cur, node_id: str, actor_id: str) -> bool:
    cur.execute("SELECT 1 FROM traversal_log WHERE node_id = %s AND actor_id = %s", (node_id, actor_id))
    return bool(cur.fetchone())

