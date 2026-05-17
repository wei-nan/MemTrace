from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, List, Literal, Optional, Union
import hashlib
import hmac
import json
from collections import defaultdict, deque

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.database import db_cursor
from core.config import settings






from core.deps import get_current_user, get_current_user_optional, RequireScope, RequireRole
from core.ratelimit import TraversalGuard
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
    ValidityConfirmationResponse,
    WorkspaceAssociationResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
    TableViewResponse,
    WorkspacePurgeResponse,
    AnalyticsTopNode,
    WorkspaceAnalyticsResponse,
    TokenEfficiencyResponse,
    VoteTrustRequest,
    WorkspaceCloneRequest,
    WorkspaceCloneJobResponse,
    ForkWorkspaceRequest,
    BulkArchiveRequest,
    BulkArchiveResponse,
    TableViewRequest,
)
from core.agent import get_or_create_agent_node
from models.review import NodeRevisionMetaResponse, NodeRevisionResponse, ApplySplitRequest


from services.bg_jobs import bg_embed_node as _bg_embed_node, bg_suggest_edges as _bg_suggest_edges, bg_clone_workspace as _bg_clone_workspace, run_connect_orphans as _run_connect_orphans, trigger_node_background_jobs as _trigger_node_background_jobs
from services.workspaces import (
    require_ws_access as _require_ws_access,
    get_effective_role as _get_effective_role,
    strip_body_if_viewer as _strip_body_if_viewer
)
from services.nodes import (
    validate_node_payload as _validate_node_payload,
    prepare_node_data as _prepare_node_data,
    node_row_to_snapshot as _node_row_to_snapshot,
    create_node_in_db as _create_node_in_db,
    update_node_in_db as _update_node_in_db,
    delete_node_in_db as _delete_node_in_db,
    create_edges_directly as _create_edges_directly,
    write_node_revision as _write_node_revision,
    propose_change as _propose_change,
    create_node_full_with_dedup as _create_node_full_with_dedup,
    apply_split_in_db,
    NODE_PUBLIC_COLUMNS,
    NODE_EDITABLE_FIELDS,
    confirm_node_validity_in_db as _confirm_node_validity_in_db
)
from services.edges import (
    write_mcp_interaction_edge as _write_mcp_interaction_edge,
    record_traversal as _record_traversal,
    create_edge_in_db as _create_edge_in_db,
)
from services.search import (
    bfs_neighborhood as _bfs_neighborhood,
    apply_text_search as _apply_text_search,
    perform_semantic_search
)
from core.ai import get_embedding_dim as _get_embedding_dim
router = APIRouter(prefix="/api/v1", tags=["knowledge-base"])

from core.constants import (
    VALID_RELATIONS,
    VALID_KB_VIS,
    VALID_NODE_VIS,
    VALID_CONTENT_T,
    VALID_FORMAT
)
# Constant imports from consolidated services.nodes above








































@router.post("/workspaces/{ws_id}/clone", response_model=WorkspaceCloneJobResponse)
def clone_workspace(ws_id: str, body: WorkspaceCloneRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    from services.workspaces import clone_workspace_in_db
    with db_cursor(commit=True) as cur:
        job = clone_workspace_in_db(cur, ws_id, body.model_dump(), user)
    from services.bg_jobs import bg_clone_workspace as _bg_clone_workspace
    background_tasks.add_task(_bg_clone_workspace, job["id"], ws_id, job["target_ws_id"], user["sub"])
    return job


@router.get("/workspaces/{ws_id}/clone-status", response_model=Optional[WorkspaceCloneJobResponse])
def get_clone_status(ws_id: str, user: dict = Depends(get_current_user)):
    from services.workspaces import get_clone_status_in_db
    with db_cursor() as cur:
        return get_clone_status_in_db(cur, ws_id)


# ── P4.1-F: Fork public workspace ─────────────────────────────────────────────

@router.post("/workspaces/{ws_id}/fork", response_model=WorkspaceCloneJobResponse, status_code=202)
def fork_workspace(ws_id: str, body: ForkWorkspaceRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    from services.workspaces import fork_workspace_in_db
    with db_cursor(commit=True) as cur:
        job = fork_workspace_in_db(cur, ws_id, body.model_dump(), user)
    from services.bg_jobs import bg_clone_workspace as _bg_clone_workspace
    background_tasks.add_task(_bg_clone_workspace, job["id"], ws_id, job["target_ws_id"], user["sub"])
    return job


@router.post("/clone-jobs/{job_id}/cancel", status_code=204)
def cancel_clone_job(job_id: str, user: dict = Depends(get_current_user)):
    from services.workspaces import cancel_clone_job_in_db
    with db_cursor(commit=True) as cur:
        cancel_clone_job_in_db(cur, job_id, user)


# ── Re-embed all nodes ────────────────────────────────────────────────────────

@router.post("/workspaces/{ws_id}/reembed-all", status_code=202)
async def reembed_all_nodes(ws_id: str, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    from services.nodes import reembed_all_nodes_in_db
    with db_cursor() as cur:
        count = reembed_all_nodes_in_db(cur, ws_id, user)
    # We need to fetch node info again if we want to add background tasks in router
    # but let's just move the task adding to service or handle it here
    with db_cursor() as cur:
        cur.execute("SELECT id, title_zh, title_en, body_zh, body_en FROM memory_nodes WHERE workspace_id = %s AND embedding IS NULL AND status = 'active'", (ws_id,))
        nodes = cur.fetchall()
    from services.bg_jobs import bg_embed_node as _bg_embed_node
    for node in nodes:
        text = f"{node['title_zh']}\n{node['title_en']}\n{node['body_zh']}\n{node['body_en']}"
        background_tasks.add_task(_bg_embed_node, ws_id, node["id"], text, user["sub"])
    return {"queued": len(nodes)}


@router.get("/workspaces", response_model=list[WorkspaceResponse])
def list_workspaces(search: Optional[str] = Query(None), user: Optional[dict] = Depends(get_current_user_optional)):
    from services.workspaces import list_workspaces_in_db
    with db_cursor() as cur:
        return list_workspaces_in_db(cur, search, user)




@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
def create_workspace(body: WorkspaceCreate, user: dict = Depends(get_current_user)):
    from services.workspaces import create_workspace_in_db
    with db_cursor(commit=True) as cur:
        return create_workspace_in_db(cur, user["sub"], body.model_dump())


@router.get("/workspaces/{ws_id}/decay-stats")
def get_decay_stats(ws_id: str, user: dict = Depends(get_current_user_optional)):
    from services.analytics import get_decay_stats_in_db
    with db_cursor() as cur:
        return get_decay_stats_in_db(cur, ws_id, user)


@router.get("/workspaces/{ws_id}/graph-preview", response_model=GraphPreviewResponse)
def get_graph_preview(ws_id: str, limit: int = 100, user: dict = Depends(get_current_user_optional)):
    from services.analytics import get_graph_preview_in_db
    with db_cursor() as cur:
        return get_graph_preview_in_db(cur, ws_id, limit, user)


@router.patch("/workspaces/{ws_id}", response_model=WorkspaceResponse)
def update_workspace(ws_id: str, body: WorkspaceUpdate, user: dict = Depends(get_current_user)):
    from services.workspaces import update_workspace_in_db
    with db_cursor(commit=True) as cur:
        return update_workspace_in_db(cur, ws_id, user["sub"], body.model_dump())


@router.get("/workspaces/{ws_id}/associations", response_model=list[WorkspaceAssociationResponse])
def list_associations(ws_id: str, user: dict = Depends(get_current_user)):
    from services.workspaces import list_associations_in_db
    with db_cursor() as cur:
        return list_associations_in_db(cur, ws_id, user)


@router.post("/workspaces/{ws_id}/associations/{target_ws_id}", response_model=WorkspaceAssociationResponse, status_code=201)
def create_association(ws_id: str, target_ws_id: str, user: dict = Depends(get_current_user)):
    from services.workspaces import create_association_in_db
    with db_cursor(commit=True) as cur:
        return create_association_in_db(cur, ws_id, target_ws_id, user)


@router.delete("/workspaces/{ws_id}/associations/{target_ws_id}", status_code=204)
def delete_association(ws_id: str, target_ws_id: str, user: dict = Depends(get_current_user)):
    from services.workspaces import delete_association_in_db
    with db_cursor(commit=True) as cur:
        delete_association_in_db(cur, ws_id, target_ws_id, user)


@router.delete("/workspaces/{ws_id}", status_code=204)
def delete_workspace(ws_id: str, user: dict = Depends(get_current_user)):
    from services.workspaces import delete_workspace_in_db
    with db_cursor(commit=True) as cur:
        delete_workspace_in_db(cur, ws_id, user)


@router.post("/workspaces/{ws_id}/purge", response_model=WorkspacePurgeResponse)
def purge_workspace(ws_id: str, user: dict = Depends(get_current_user)):
    from services.workspaces import purge_workspace_in_db
    with db_cursor(commit=True) as cur:
        return purge_workspace_in_db(cur, ws_id, user)


@router.post("/workspaces/{ws_id}/nodes/{node_id}/vote-trust")
def vote_trust(ws_id: str, node_id: str, body: VoteTrustRequest, user: dict = Depends(get_current_user)):
    from services.nodes import vote_trust_in_db
    with db_cursor(commit=True) as cur:
        return vote_trust_in_db(cur, ws_id, node_id, body.model_dump(), user)


@router.get("/workspaces/{ws_id}", response_model=WorkspaceResponse)
def get_workspace(ws_id: str, user: Optional[dict] = Depends(get_current_user_optional)):
    from services.workspaces import require_ws_access
    with db_cursor() as cur:
        return require_ws_access(cur, ws_id, user)


@router.get("/workspaces/{workspace_id}/nodes/{node_id}/neighborhood")
async def get_neighborhood(
    workspace_id: str,
    node_id: str,
    depth: int = Query(2, ge=1, le=3),
    relation: Optional[str] = None,
    direction: Literal["both", "outbound", "inbound"] = "both",
    include_source: bool = Query(True),
    current_user = Depends(get_current_user_optional),
):
    with db_cursor() as cur:
        workspace = _require_ws_access(cur, workspace_id, current_user)
        
        viewer_id = current_user["sub"] if current_user else None
        viewer_role = _get_effective_role(cur, workspace_id, workspace["owner_id"], viewer_id)

        result = _bfs_neighborhood(
            cur, workspace_id, node_id, depth, relation, direction,
            include_source=include_source,
            viewer_role=viewer_role,
        )

        return result


@router.get("/workspaces/{ws_id}/nodes", response_model=list[NodeResponse])
def list_nodes(
    ws_id: str,
    q: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    limit: int = Query(50, description="Use a large number for unlimited"),
    offset: int = Query(0),
    status: str = Query("active"),
    filter: Optional[str] = Query(None, description="orphan | faded | never_traversed"),
    include_source: bool = Query(False, description="Include source_document nodes"),
    user: dict = Depends(get_current_user_optional),
):
    from services.nodes import list_nodes_in_db
    with db_cursor() as cur:
        return list_nodes_in_db(cur, ws_id, q, tag, content_type, limit, offset, status, filter, include_source, user)


@router.get("/workspaces/{ws_id}/table-view", response_model=TableViewResponse)
def get_table_view(
    ws_id: str, 
    q: Optional[str] = Query(None),
    filter: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    order: Optional[str] = Query("desc"),
    limit: int = Query(50, le=200), 
    offset: int = Query(0), 
    user: dict = Depends(get_current_user_optional)
):
    from services.nodes import get_table_view_in_db
    with db_cursor() as cur:
        return get_table_view_in_db(cur, ws_id, q, filter, sort_by, order, limit, offset, user)


@router.get("/workspaces/{ws_id}/nodes-search", response_model=List[NodeResponse])
def search_nodes(ws_id: str, query: str = Query(...), limit: int = 20, user: dict = Depends(get_current_user_optional)):
    from services.nodes import search_nodes_in_db
    with db_cursor() as cur:
        return search_nodes_in_db(cur, ws_id, query, limit, user)


@router.post("/workspaces/{ws_id}/nodes/search-semantic", response_model=List[NodeResponse])
async def search_nodes_semantic(ws_id: str, query: str, limit: int = 10, user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        _require_ws_access(cur, ws_id, user)
        cur.execute("SELECT embedding_model, embedding_provider FROM workspaces WHERE id = %s", (ws_id,))
        ws_row = cur.fetchone()
        ws_model = ws_row["embedding_model"] if ws_row else None
        ws_prov = ws_row["embedding_provider"] if ws_row else None
        return await perform_semantic_search(cur, ws_id, query, user["sub"], limit, ws_model=ws_model, ws_prov=ws_prov)


@router.get("/workspaces/{ws_id}/nodes/health")
def get_nodes_health(ws_id: str, user: dict = Depends(get_current_user_optional)):
    from services.nodes import get_nodes_health_in_db
    with db_cursor() as cur:
        return get_nodes_health_in_db(cur, ws_id, user)


@router.post("/workspaces/{ws_id}/nodes/backfill-embeddings")
async def backfill_embeddings(ws_id: str, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    from services.nodes import backfill_embeddings_in_db
    with db_cursor() as cur:
        nodes = backfill_embeddings_in_db(cur, ws_id, user)
    from services.bg_jobs import bg_embed_node as _bg_embed_node
    for node in nodes:
        text = " ".join(filter(None, [node["title_zh"], node["title_en"], node["body_zh"], node["body_en"]]))
        background_tasks.add_task(_bg_embed_node, ws_id, node["id"], text, user["sub"])
    return {"queued": len(nodes)}


@router.post("/workspaces/{ws_id}/nodes/{node_id}/suggest-edges")
def suggest_edges_for_node(ws_id: str, node_id: str, user: dict = Depends(get_current_user)):
    from services.nodes import suggest_edges_for_node_in_db
    with db_cursor(commit=True) as cur:
        return suggest_edges_for_node_in_db(cur, ws_id, node_id, user)


@router.get("/workspaces/{ws_id}/nodes/{node_id}", response_model=NodeResponse)
def get_node(ws_id: str, node_id: str, user: dict = Depends(get_current_user_optional)):
    from services.nodes import get_node_in_db
    with db_cursor() as cur:
        return get_node_in_db(cur, ws_id, node_id, user)


@router.post("/workspaces/{ws_id}/nodes", response_model=NodeResponse, status_code=201)
async def create_node(ws_id: str, body: NodeCreate, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        node, review_id, dup_info = await _create_node_full_with_dedup(cur, ws_id, body.model_dump(), user, force_create=body.force_create)
        
        if dup_info:
            return JSONResponse(status_code=409, content=dup_info)

        if review_id:
            from core.ai_review import run_ai_review_for_item
            background_tasks.add_task(run_ai_review_for_item, review_id)
            return JSONResponse(status_code=202, content={"review_id": review_id, "detail": "Your new node has been submitted for review"})
            
        _trigger_node_background_jobs(background_tasks, ws_id, node["id"], user["sub"], node)
        return node


@router.patch("/workspaces/{ws_id}/nodes/{node_id}", response_model=NodeResponse)
def update_node(ws_id: str, node_id: str, body: NodeUpdate, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    from services.nodes import update_node_full_in_db
    with db_cursor(commit=True) as cur:
        node, review_id = update_node_full_in_db(cur, ws_id, node_id, body.model_dump(exclude_unset=True), user)
        if review_id:
            from core.ai_review import run_ai_review_for_item
            background_tasks.add_task(run_ai_review_for_item, review_id)
            return JSONResponse(status_code=202, content={"review_id": review_id, "detail": "Your update has been submitted for review"})
            
        from services.bg_jobs import bg_embed_node as _bg_embed_node
        text = " ".join(filter(None, [node["title_zh"], node["title_en"], node["body_zh"], node["body_en"]]))
        background_tasks.add_task(_bg_embed_node, ws_id, node["id"], text, user["sub"])
        return node


@router.delete("/workspaces/{ws_id}/nodes/{node_id}")
def delete_node(ws_id: str, node_id: str, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    from services.nodes import delete_node_full_in_db
    with db_cursor(commit=True) as cur:
        node, review_id = delete_node_full_in_db(cur, ws_id, node_id, user)
        if review_id:
            from core.ai_review import run_ai_review_for_item
            background_tasks.add_task(run_ai_review_for_item, review_id)
            return JSONResponse(status_code=202, content={"review_id": review_id, "detail": "Your deletion request has been submitted for review"})
            
        return {"status": "archived", "node_id": node["id"]}


@router.get("/workspaces/{ws_id}/nodes/{node_id}/revisions", response_model=list[NodeRevisionMetaResponse])
def list_node_revisions(ws_id: str, node_id: str, user: dict = Depends(get_current_user_optional)):
    from services.nodes import list_node_revisions_in_db
    with db_cursor() as cur:
        return list_node_revisions_in_db(cur, ws_id, node_id, user)


@router.get("/workspaces/{ws_id}/nodes/{node_id}/revisions/{revision_no}", response_model=NodeRevisionResponse)
def get_node_revision(ws_id: str, node_id: str, revision_no: int, user: dict = Depends(get_current_user_optional)):
    from services.nodes import get_node_revision_in_db
    with db_cursor() as cur:
        return get_node_revision_in_db(cur, ws_id, node_id, revision_no, user)


@router.get("/workspaces/{ws_id}/nodes/{node_id}/revisions/{rev_a}/diff/{rev_b}")
def diff_node_revisions(ws_id: str, node_id: str, rev_a: int, rev_b: int, user: dict = Depends(get_current_user_optional)):
    from services.nodes import diff_node_revisions_in_db
    with db_cursor() as cur:
        return diff_node_revisions_in_db(cur, ws_id, node_id, rev_a, rev_b, user)


@router.post("/workspaces/{ws_id}/nodes/{node_id}/revisions/{revision_no}/restore")
def restore_node_revision(ws_id: str, node_id: str, revision_no: int, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    from services.nodes import restore_node_revision_in_db
    with db_cursor(commit=True) as cur:
        node, review_id = restore_node_revision_in_db(cur, ws_id, node_id, revision_no, user)
        if review_id:
            from core.ai_review import run_ai_review_for_item
            background_tasks.add_task(run_ai_review_for_item, review_id)
            return JSONResponse(status_code=202, content={"review_id": review_id, "detail": "Your restoration request has been submitted for review"})
            
        from services.bg_jobs import bg_embed_node as _bg_embed_node
        text = " ".join(filter(None, [node["title_zh"], node["title_en"], node["body_zh"], node["body_en"]]))
        background_tasks.add_task(_bg_embed_node, ws_id, node["id"], text, user["sub"])
        return node


@router.get("/workspaces/{ws_id}/edges", response_model=List[EdgeResponse])
def list_edges(ws_id: str, node_id: Optional[str] = Query(None), user: dict = Depends(get_current_user_optional)):
    from services.edges import list_edges_in_db
    with db_cursor() as cur:
        return list_edges_in_db(cur, ws_id, node_id, user)


@router.post("/workspaces/{ws_id}/nodes/connect-orphans", status_code=202)
async def connect_orphans(ws_id: str, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    from services.workspaces import require_ws_access
    with db_cursor() as cur:
        require_ws_access(cur, ws_id, user, write=True)
    from services.bg_jobs import run_connect_orphans as _run_connect_orphans
    background_tasks.add_task(_run_connect_orphans, ws_id)
    return {"message": "Connecting orphans in background"}






@router.post("/workspaces/{ws_id}/edges", response_model=EdgeResponse, status_code=201)
def create_edge(ws_id: str, body: EdgeCreate, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_role="admin")
        return _create_edge_in_db(cur, ws_id, body.model_dump())


@router.post("/nodes/{node_id}/traverse", status_code=204)
def traverse_node(node_id: str, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    from services.nodes import traverse_node_in_db
    with db_cursor() as cur:
        ws_id = traverse_node_in_db(cur, node_id, user)
    from services.edges import record_traversal as _record_traversal
    background_tasks.add_task(_record_traversal, ws_id, node_id, user["sub"])


@router.post(
    "/workspaces/{ws_id}/nodes/{node_id}/confirm-validity",
    response_model=ValidityConfirmationResponse,
)
def confirm_node_validity(ws_id: str, node_id: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        _require_ws_access(cur, ws_id, user, write=True, required_role="admin")
        _confirm_node_validity_in_db(cur, ws_id, node_id, user["email"])
        return {"confirmed_at": datetime.now(timezone.utc).isoformat(), "confirmed_by": user["email"]}


@router.post("/edges/{edge_id}/traverse", status_code=204)
def traverse_edge(edge_id: str, body: TraverseEdgeRequest, user: dict = Depends(get_current_user)):
    from services.edges import traverse_edge_in_db
    with db_cursor(commit=True) as cur:
        traverse_edge_in_db(cur, edge_id, body.note, user)


@router.post("/edges/{edge_id}/rate", status_code=204)
def rate_edge(edge_id: str, body: RateEdgeRequest, user: dict = Depends(get_current_user)):
    from services.edges import rate_edge_in_db
    with db_cursor(commit=True) as cur:
        rate_edge_in_db(cur, edge_id, body.rating, body.note, user)




@router.post("/internal/mcp-log", status_code=204)
def log_mcp_query(body: dict, authorization: Optional[str] = Header(default=None)):
    from services.analytics import log_mcp_query_in_db
    with db_cursor(commit=True) as cur:
        log_mcp_query_in_db(cur, body, authorization)


@router.get("/workspaces/{ws_id}/analytics", response_model=WorkspaceAnalyticsResponse)
def get_workspace_analytics(ws_id: str, user: dict = Depends(get_current_user_optional)):
    from services.analytics import get_workspace_analytics_in_db
    with db_cursor() as cur:
        return get_workspace_analytics_in_db(cur, ws_id, user)


@router.get("/workspaces/{ws_id}/stats/top-gaps", response_model=List[AnalyticsTopNode])
def get_top_gaps(ws_id: str, limit: int = 5, user: dict = Depends(get_current_user_optional)):
    from services.analytics import get_top_gaps_in_db
    with db_cursor() as cur:
        return get_top_gaps_in_db(cur, ws_id, limit, user)


@router.get("/workspaces/{ws_id}/analytics/token-efficiency", response_model=TokenEfficiencyResponse)
def get_workspace_token_efficiency(ws_id: str, user: dict = Depends(get_current_user_optional)):
    from services.analytics import get_workspace_token_efficiency_in_db
    with db_cursor() as cur:
        return get_workspace_token_efficiency_in_db(cur, ws_id, user)


# ─── A4 / D4: Archive & Restore ───────────────────────────────────────────────



@router.post("/workspaces/{ws_id}/nodes/bulk-archive", response_model=BulkArchiveResponse)
def bulk_archive_nodes(ws_id: str, body: BulkArchiveRequest, user: dict = Depends(get_current_user)):
    from services.nodes import bulk_archive_nodes_in_db
    with db_cursor(commit=True) as cur:
        count = bulk_archive_nodes_in_db(cur, ws_id, body.node_ids, user)
        return {"archived_count": count}


@router.post("/workspaces/{ws_id}/nodes/{node_id}/archive", status_code=204)
def archive_node(ws_id: str, node_id: str, user: dict = Depends(get_current_user)):
    from services.nodes import archive_node_in_db
    with db_cursor(commit=True) as cur:
        archive_node_in_db(cur, ws_id, node_id, user)


@router.post("/workspaces/{ws_id}/nodes/{node_id}/restore", status_code=204)
def restore_node(ws_id: str, node_id: str, user: dict = Depends(get_current_user)):
    from services.nodes import restore_node_in_db
    with db_cursor(commit=True) as cur:
        restore_node_in_db(cur, ws_id, node_id, user)


# ─── A3: Node Health Scores ────────────────────────────────────────────────────

@router.get("/workspaces/{ws_id}/nodes/health-scores")
def get_health_scores(ws_id: str, user: dict = Depends(get_current_user_optional)):
    from services.nodes import get_health_scores_in_db
    with db_cursor() as cur:
        return get_health_scores_in_db(cur, ws_id, user)


# ─── A6: Manual Validity Stamp ────────────────────────────────────────────────



# ─── B1: viewer body stripping on GET single node ─────────────────────────────
# (handled via _strip_body_if_viewer already in the existing get_node endpoint)


# ─── D3 / D1: Workspace search for cross-KB operations ───────────────────────




# ─── G-2: Manual Link Detection ──────────────────────────────────────────────

@router.post("/workspaces/{ws_id}/nodes/detect-links", status_code=202)
def trigger_link_detection(ws_id: str, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    from services.nodes import trigger_link_detection_in_db
    with db_cursor() as cur:
        node_ids = trigger_link_detection_in_db(cur, ws_id, user)
    from routers.ingest import detect_cross_file_associations_for_nodes
    background_tasks.add_task(detect_cross_file_associations_for_nodes, ws_id, node_ids)
    return {"message": "Link detection started in background", "nodes_checked": len(node_ids)}

# ─── MCP Interaction Tracking ───────────────────────────────────────────────

@router.post("/workspaces/{ws_id}/review/{rev_id}/apply-split")
def apply_split(ws_id: str, rev_id: str, body: ApplySplitRequest, user: dict = Depends(get_current_user)):
    """P4.8-S9-3f: Approve and execute a node split proposal."""
    with db_cursor(commit=True) as cur:
        # 1. Fetch the review record to get the target node ID
        cur.execute("SELECT target_node_id, split_suggestion FROM review_queue WHERE id = %s AND workspace_id = %s", (rev_id, ws_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Review record not found")

        target_node_id = row["target_node_id"]
        # Use provided proposals if any, otherwise use from DB
        proposals = body.proposals or row["split_suggestion"]

        if not proposals:
            raise HTTPException(status_code=400, detail="No split proposals found")

        return apply_split_in_db(cur, ws_id, rev_id, target_node_id, proposals, user["sub"])


# ── Node Clusters ─────────────────────────────────────────────────────────────

class ClusterCreate(BaseModel):
    name_zh: str
    name_en: str
    color: str = "blue"

class ClusterUpdate(BaseModel):
    name_zh: Optional[str] = None
    name_en: Optional[str] = None
    color: Optional[str] = None

class NodeClusterAssign(BaseModel):
    cluster_id: Optional[str] = None


@router.get("/workspaces/{ws_id}/clusters")
def list_clusters(ws_id: str, user: dict = Depends(get_current_user)):
    _require_ws_access(ws_id, user["sub"], "viewer")
    from services.clusters import list_clusters as _list_clusters
    return _list_clusters(ws_id)


@router.post("/workspaces/{ws_id}/clusters", status_code=201)
def create_cluster(ws_id: str, body: ClusterCreate, user: dict = Depends(get_current_user)):
    _require_ws_access(ws_id, user["sub"], "editor")
    from services.clusters import get_or_create_cluster
    with db_cursor(commit=True) as cur:
        cluster_id = get_or_create_cluster(cur, ws_id, body.name_zh, body.name_en, body.color)
    from services.clusters import list_clusters as _list_clusters
    rows = _list_clusters(ws_id)
    return next((r for r in rows if r["id"] == cluster_id), {"id": cluster_id})


@router.patch("/workspaces/{ws_id}/clusters/{cluster_id}")
def update_cluster(ws_id: str, cluster_id: str, body: ClusterUpdate, user: dict = Depends(get_current_user)):
    _require_ws_access(ws_id, user["sub"], "editor")
    from services.clusters import update_cluster as _update_cluster
    try:
        return _update_cluster(ws_id, cluster_id, body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/workspaces/{ws_id}/clusters/{cluster_id}", status_code=204)
def delete_cluster(ws_id: str, cluster_id: str, user: dict = Depends(get_current_user)):
    _require_ws_access(ws_id, user["sub"], "editor")
    from services.clusters import delete_cluster as _delete_cluster
    _delete_cluster(ws_id, cluster_id)


@router.patch("/workspaces/{ws_id}/nodes/{node_id}/cluster")
def assign_node_cluster(ws_id: str, node_id: str, body: NodeClusterAssign, user: dict = Depends(get_current_user)):
    _require_ws_access(ws_id, user["sub"], "editor")
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE memory_nodes SET cluster_id = %s, updated_at = now() "
            "WHERE id = %s AND workspace_id = %s RETURNING id",
            (body.cluster_id, node_id, ws_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Node not found")
    return {"ok": True}


