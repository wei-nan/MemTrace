"""
services/workspaces.py — Workspace access control and business logic.

Extracted from routers/kb.py (S2-1). All routers should import from here
instead of referencing private _functions in routers/kb.py.

Key exports:
  - require_ws_access(cur, ws_id, user, write, required_scope) → workspace row
  - get_effective_role(cur, ws_id, owner_id, user_id) → role string or None
  - strip_body_if_viewer(node_row, role) → redacted node dict
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import HTTPException

from core.constants import VALID_KB_VIS


# ─── Access Control ───────────────────────────────────────────────────────────

def require_ws_access(
    cur,
    ws_id: str,
    user: Optional[dict],
    write: bool = False,
    required_role: Optional[str] = None,
    required_scope: Optional[str] = None,
) -> dict:
    """
    Verify the caller has access to the workspace.
    - required_role: enforces a minimum role ("viewer"|"contributor"|"editor"|"admin")
    - required_scope: legacy (§29 workspace service tokens)
    """
    # API key scope and workspace validation
    if user and "api_key_id" in user:
        ak_ws_id = user.get("workspace_id")
        if ak_ws_id and ak_ws_id != ws_id:
            raise HTTPException(status_code=403, detail="API key is restricted to another workspace")
        if required_scope:
            scopes = user.get("scopes") or []
            if "*" not in scopes and required_scope not in scopes:
                raise HTTPException(
                    status_code=403,
                    detail={"error": "insufficient_scope", "required": required_scope},
                )

    cur.execute("SELECT * FROM workspaces WHERE id = %s", (ws_id,))
    ws = cur.fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    vis = ws["visibility"]
    user_id = user["sub"] if user else None
    role = get_effective_role(cur, ws_id, ws["owner_id"], user_id)

    # Role hierarchy validation
    if required_role:
        from core.deps import ROLE_HIERARCHY
        if not role:
            raise HTTPException(status_code=403, detail={"error": "no_membership", "message": "No membership in this workspace"})
        if ROLE_HIERARCHY.get(role, -1) < ROLE_HIERARCHY.get(required_role, 0):
            raise HTTPException(status_code=403, detail={"error": "insufficient_role", "required": required_role, "actual": role})

    if user_id == ws["owner_id"]:
        pass # Owner has access
    elif vis == "private":
        if not required_role:  # If we didn't check required_role above, at least ensure they have access
            if not role:
                raise HTTPException(status_code=403, detail="Access denied")
    elif vis in ("public", "conditional_public") and not write:
        pass # Public read access
    elif vis == "restricted" or write:
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        if not role:
            raise HTTPException(status_code=403, detail="Access denied")
        if write and role not in ("editor", "admin") and not required_role:
            raise HTTPException(status_code=403, detail="Editor or Admin role required")

    ws = dict(ws)
    ws["my_role"] = role
    return ws



def get_effective_role(cur, ws_id: str, owner_id: str, user_id: Optional[str]) -> Optional[str]:
    """Return the effective role of user_id in ws_id ('admin' / 'editor' / 'viewer' / None)."""
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


def strip_body_if_viewer(node_row: dict, role: Optional[str]) -> dict:
    """Redact body fields for non-editor/admin viewers (unless the node is public)."""
    node_row = dict(node_row)
    node_row["content_stripped"] = False
    if role not in ("editor", "admin"):
        if node_row.get("visibility") == "public":
            return node_row
        node_row["body"] = None
        node_row["content_stripped"] = True
    return node_row


# ─── Backward-compat aliases (keep old _ names working during migration) ──────
# routers/kb.py still defines these; once kb.py is updated to import from here,
# these aliases can be removed.

_require_ws_access = require_ws_access
_get_effective_role = get_effective_role
_strip_body_if_viewer = strip_body_if_viewer

# ─── Workspace CRUD ───────────────────────────────────────────────────────────

from core.security import generate_id

def list_workspaces_in_db(cur, search: Optional[str], user: Optional[dict]) -> list[dict]:
    uid = user["sub"] if user else None
    if uid:
        filters = [
            "(w.owner_id = %s OR w.id IN (SELECT workspace_id FROM workspace_members WHERE user_id = %s) OR w.visibility = 'public')"
        ]
        params = [uid, uid]
        query_params = [uid, uid] + params
    else:
        filters = ["w.visibility = 'public'"]
        params = []
        query_params = [None, None]

    if user and user.get("api_key_id") and user.get("workspace_id"):
        filters.append("w.id = %s")
        query_params.append(user["workspace_id"])

    if search:
        filters.append("w.name ILIKE %s")
        like = f"%{search}%"
        query_params.append(like)

    cur.execute(
        f"""
        SELECT w.*,
               (SELECT count(*) FROM memory_nodes WHERE workspace_id = w.id AND status='active') AS node_count,
               CASE WHEN w.owner_id = %s THEN 'admin'
                    ELSE wm.role::text
               END AS my_role
        FROM workspaces w
        LEFT JOIN workspace_members wm ON wm.workspace_id = w.id AND wm.user_id = %s
        WHERE {' AND '.join(filters)}
        ORDER BY w.updated_at DESC
        """,
        query_params,
    )
    return cur.fetchall()

def create_workspace_in_db(cur, uid: str, body_dict: dict) -> dict:
    from core.agent import get_or_create_agent_node
    from core.ai import resolve_provider, get_embedding_dim, AIProviderUnavailable

    if body_dict.get("visibility") not in VALID_KB_VIS:
        raise HTTPException(status_code=400, detail="Invalid visibility")

    embedding_model = body_dict.get("embedding_model")
    if not embedding_model:
        try:
            resolved = resolve_provider(uid, "embedding")
            embedding_model = resolved.model
            embedding_dim = get_embedding_dim(embedding_model)
            embedding_provider = resolved.provider.name
        except AIProviderUnavailable:
            embedding_model = "text-embedding-3-small"
            embedding_dim = 1536
            embedding_provider = "openai"
    else:
        # If model is provided, infer provider or use explicitly provided one
        embedding_provider = body_dict.get("embedding_provider")
        if not embedding_provider:
            # Inference logic (simple version)
            if "text-embedding-3" in embedding_model or "text-embedding-ada" in embedding_model:
                embedding_provider = "openai"
            elif "text-embedding-00" in embedding_model:
                embedding_provider = "gemini"
            else:
                embedding_provider = "ollama"
        embedding_dim = get_embedding_dim(embedding_model)

    ws_id = generate_id("ws")
    name = body_dict.get("name") or body_dict.get("name_zh") or body_dict.get("name_en") or ""
    language = body_dict.get("language")
    if not language:
        raise HTTPException(status_code=400, detail="language is required")
    
    cur.execute(
        """
        INSERT INTO workspaces (
            id, name, language, visibility, kb_type, owner_id,
            archive_window_days, min_traversals, embedding_model, embedding_dim,
            qa_archive_mode, extraction_provider, embedding_provider, auto_split,
            consult_trust_tier, consult_provider, settings
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            ws_id, name, language,
            body_dict.get("visibility"), body_dict.get("kb_type"),
            uid, body_dict.get("archive_window_days", 90), body_dict.get("min_traversals", 1),
            embedding_model, embedding_dim, body_dict.get("qa_archive_mode", "auto_active"),
            body_dict.get("extraction_provider", "gemini"), embedding_provider,
            body_dict.get("auto_split", False),
            body_dict.get("consult_trust_tier", "ask"),
            body_dict.get("consult_provider"),
            json.dumps({
                "node_complexity": {"enabled": True, "char_threshold": 600, "auto_split": False},
                "auto_dedup_threshold": 0.92,
                "mcp_ingest_enabled": False,
                "mcp_ingest_daily_quota": 5,
                **(body_dict.get("settings") or {}),
            })
        ),
    )
    res = cur.fetchone()
    get_or_create_agent_node(ws_id, cur)
    return {**dict(res), "my_role": "admin"}

def update_workspace_in_db(cur, ws_id: str, uid: str, body_dict: dict) -> dict:
    cur.execute("SELECT * FROM workspaces WHERE id = %s", (ws_id,))
    ws = cur.fetchone()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["owner_id"] != uid:
        raise HTTPException(status_code=403, detail="Only workspace owner can update settings")
    
    # description can be set to empty string (clearing it), so exclude only None
    updates = {k: v for k, v in body_dict.items() if v is not None or k == "description"}
    updates = {k: v for k, v in updates.items() if v is not None or k == "description"}
    if not updates:
        return ws
    for immutable in ("kb_type", "embedding_model", "embedding_dim", "embedding_provider"):
        if immutable in updates:
            raise HTTPException(status_code=400, detail=f"Immutable field: {immutable}")
    if "visibility" in updates and updates["visibility"] not in VALID_KB_VIS:
        raise HTTPException(status_code=400, detail="Invalid visibility")
    
    if "settings" in updates and isinstance(updates["settings"], dict):
        updates["settings"] = json.dumps(updates["settings"])
        
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    cur.execute(f"UPDATE workspaces SET {set_clause} WHERE id = %s RETURNING *", list(updates.values()) + [ws_id])
    updated_ws = cur.fetchone()

    # If migration started, create migration record
    if updates.get("migration_status") == "in_progress" and updates.get("migrating_to_model"):
        migration_id = generate_id("mig")
        cur.execute(
            """
            INSERT INTO workspace_migrations (id, workspace_id, target_provider, target_model, status)
            VALUES (%s, %s, %s, %s, 'in_progress')
            """,
            (
                migration_id, 
                ws_id, 
                updates.get("migrating_to_provider", ws["embedding_provider"]),
                updates["migrating_to_model"]
            )
        )

    return updated_ws

def explore_workspaces_in_db(cur, user: Optional[dict], q: Optional[str], lang: Optional[str], sort: str) -> list[dict]:
    uid = user["sub"] if user else None

    public_filter = "w.visibility IN ('public', 'conditional_public')"
    params: list = []

    if uid:
        where = f"({public_filter} OR w.owner_id = %s OR w.id IN (SELECT workspace_id FROM workspace_members WHERE user_id = %s))"
        params = [uid, uid]
    else:
        where = public_filter

    if q:
        where += " AND (w.name ILIKE %s OR w.description ILIKE %s)"
        like = f"%{q}%"
        params += [like, like]

    if lang:
        where += " AND w.language = %s"
        params.append(lang)

    order = "w.created_at DESC" if sort == "newest" else "node_count DESC"

    cur.execute(
        f"""
        SELECT w.id, w.name, w.description, w.language, w.visibility, w.kb_type,
               w.owner_id, w.created_at, w.updated_at,
               u.display_name AS owner_display_name,
               (SELECT count(*) FROM memory_nodes mn WHERE mn.workspace_id = w.id AND mn.status = 'active') AS node_count,
               CASE WHEN w.owner_id = %s THEN 'admin'
                    ELSE wm.role::text
               END AS my_role
        FROM workspaces w
        LEFT JOIN users u ON u.id = w.owner_id
        LEFT JOIN workspace_members wm ON wm.workspace_id = w.id AND wm.user_id = %s
        WHERE w.deleted_at IS NULL AND w.status = 'active' AND {where}
        ORDER BY {order}
        LIMIT 200
        """,
        [uid, uid] + params,
    )
    return cur.fetchall()


def delete_workspace_in_db(cur, ws_id: str, user: dict) -> None:
    ws = require_ws_access(cur, ws_id, user, write=True)
    if ws["owner_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Only the workspace owner can delete it")
    cur.execute("DELETE FROM workspaces WHERE id = %s", (ws_id,))

def purge_workspace_in_db(cur, ws_id: str, user: dict) -> dict:
    ws = require_ws_access(cur, ws_id, user, write=True, required_role="admin")
    if ws["owner_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Only workspace owner can purge it")
    cur.execute("DELETE FROM edges WHERE workspace_id = %s", (ws_id,))
    ec = cur.rowcount
    cur.execute("DELETE FROM memory_nodes WHERE workspace_id = %s", (ws_id,))
    nc = cur.rowcount
    cur.execute("DELETE FROM review_queue WHERE workspace_id = %s", (ws_id,))
    cur.execute("DELETE FROM node_revisions WHERE workspace_id = %s", (ws_id,))
    cur.execute("DELETE FROM ingest_jobs WHERE workspace_id = %s", (ws_id,))
    return {"deleted_nodes_count": nc, "deleted_edges_count": ec}

def clone_workspace_in_db(cur, ws_id: str, body_dict: dict, user: dict) -> dict:
    from services.workspaces import require_ws_access
    from core.security import generate_id
    from core.ai import get_embedding_dim
    # from routers.kb import VALID_KB_VIS
    source = require_ws_access(cur, ws_id, user)
    
    name = body_dict.get("name") or (f"{source.get('name')} (Clone)")
    language = body_dict.get("language") or source.get("language")
    
    new_model = body_dict.get("new_embedding_model")
    if new_model:
        new_dim = get_embedding_dim(new_model)
    else:
        new_model = source["embedding_model"]
        new_dim   = source["embedding_dim"]

    new_visibility = body_dict.get("visibility") if body_dict.get("visibility") in VALID_KB_VIS else "private"
    target_ws_id = generate_id("ws")
    new_qa_mode = body_dict.get("qa_archive_mode") or source["qa_archive_mode"] or "manual_review"
    new_extraction = body_dict.get("extraction_provider") if body_dict.get("extraction_provider") is not None else source.get("extraction_provider")
    cur.execute(
        """
        INSERT INTO workspaces (
            id, name, language, visibility, kb_type, owner_id,
            archive_window_days, min_traversals, embedding_model, embedding_dim,
            qa_archive_mode, extraction_provider, embedding_provider
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            target_ws_id, name, language, new_visibility, source["kb_type"],
            user["sub"], source["archive_window_days"], source["min_traversals"],
            new_model, new_dim, new_qa_mode, new_extraction, source["embedding_provider"]
        ),
    )

    job_id = generate_id("cln")
    cur.execute(
        """
        INSERT INTO workspace_clone_jobs (id, source_ws_id, target_ws_id, status)
        VALUES (%s, %s, %s, 'pending')
        RETURNING *
        """,
        (job_id, ws_id, target_ws_id),
    )
    return cur.fetchone()

def get_clone_status_in_db(cur, ws_id: str) -> dict:
    cur.execute("SELECT * FROM workspace_clone_jobs WHERE target_ws_id = %s ORDER BY created_at DESC LIMIT 1", (ws_id,))
    return cur.fetchone()

def fork_workspace_in_db(cur, ws_id: str, body_dict: dict, user: dict) -> dict:
    from services.workspaces import require_ws_access
    from core.security import generate_id
    from core.ai import get_embedding_dim
    source = require_ws_access(cur, ws_id, user, write=False)

    name = body_dict.get("name") or (f"{source.get('name')} (Fork)")
    language = body_dict.get("language") or source.get("language")

    new_model = body_dict.get("embedding_model") or source["embedding_model"]
    new_dim   = get_embedding_dim(new_model)

    target_ws_id = generate_id("ws")
    fork_qa_mode = body_dict.get("qa_archive_mode") or source["qa_archive_mode"] or "manual_review"
    fork_extraction = body_dict.get("extraction_provider") if body_dict.get("extraction_provider") is not None else source.get("extraction_provider")
    cur.execute(
        """
        INSERT INTO workspaces (
            id, name, language, visibility, kb_type, owner_id,
            archive_window_days, min_traversals, embedding_model, embedding_dim,
            qa_archive_mode, extraction_provider, embedding_provider
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            target_ws_id, name, language, 'private', source["kb_type"], user["sub"],
            source["archive_window_days"], source["min_traversals"],
            new_model, new_dim, fork_qa_mode, fork_extraction, source["embedding_provider"],
        ),
    )

    job_id = generate_id("cln")
    cur.execute(
        """
        INSERT INTO workspace_clone_jobs
          (id, source_ws_id, target_ws_id, status, is_fork)
        VALUES (%s, %s, %s, 'pending', TRUE)
        RETURNING *
        """,
        (job_id, ws_id, target_ws_id),
    )
    return cur.fetchone()

def cancel_clone_job_in_db(cur, job_id: str, user: dict) -> None:
    from fastapi import HTTPException
    cur.execute(
        """
        SELECT cj.id, cj.status, w.owner_id
        FROM workspace_clone_jobs cj
        JOIN workspaces w ON w.id = cj.target_ws_id
        WHERE cj.id = %s
        """,
        (job_id,),
    )
    job = cur.fetchone()
    if not job:
        raise HTTPException(status_code=404, detail="Clone job not found")
    if job["owner_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Only the target workspace owner can cancel this job")
    if job["status"] not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a job that is already '{job['status']}'")

    cur.execute("UPDATE workspace_clone_jobs SET status = 'cancelling' WHERE id = %s", (job_id,))

def list_associations_in_db(cur, ws_id: str, user: dict) -> list[dict]:
    from services.workspaces import require_ws_access
    require_ws_access(cur, ws_id, user)
    cur.execute(
        """
        SELECT a.id, a.source_ws_id, a.target_ws_id,
               w.name AS target_name, a.created_at
        FROM workspace_associations a
        JOIN workspaces w ON w.id = a.target_ws_id
        WHERE a.source_ws_id = %s
        ORDER BY a.created_at DESC
        """,
        (ws_id,),
    )
    return cur.fetchall()

def create_association_in_db(cur, ws_id: str, target_ws_id: str, user: dict) -> dict:
    from services.workspaces import require_ws_access
    require_ws_access(cur, ws_id, user, write=True)
    require_ws_access(cur, target_ws_id, user)
    from core.security import generate_id
    assoc_id = generate_id("asc")
    cur.execute(
        """
        INSERT INTO workspace_associations (id, source_ws_id, target_ws_id)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id, source_ws_id, target_ws_id, created_at
        """,
        (assoc_id, ws_id, target_ws_id),
    )
    row = cur.fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Association already exists")
    cur.execute("SELECT name FROM workspaces WHERE id = %s", (target_ws_id,))
    ws_row = cur.fetchone()
    return {
        "id": row["id"],
        "source_ws_id": row["source_ws_id"],
        "target_ws_id": row["target_ws_id"],
        "target_name": ws_row["name"] if ws_row else target_ws_id,
        "created_at": row["created_at"],
    }

def delete_association_in_db(cur, ws_id: str, target_ws_id: str, user: dict) -> None:
    from services.workspaces import require_ws_access
    require_ws_access(cur, ws_id, user, write=True)
    cur.execute(
        """
        DELETE FROM workspace_associations
        WHERE source_ws_id = %s AND target_ws_id = %s
        RETURNING *
        """,
        (ws_id, target_ws_id),
    )
    if not cur.fetchone():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Association not found")
