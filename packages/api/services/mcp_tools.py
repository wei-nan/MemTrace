from typing import Any, Dict, Optional, List, Union
import datetime
import logging
import re
import json
from fastapi import BackgroundTasks, HTTPException
from core.database import db_cursor
from core.security import generate_id, compute_signature
from core.constants import VALID_RELATIONS, VALID_CONTENT_T
from services.workspaces import require_ws_access, get_effective_role, list_workspaces_in_db
from services.edges import write_mcp_interaction_edge, create_edge_in_db
from services.search import bfs_neighborhood, search_nodes_in_db, perform_semantic_search
from services.analytics import handle_search_miss, log_mcp_query_internal
from services.nodes import (
    list_nodes_in_db, 
    get_node_in_db, 
    update_node_in_db, 
    delete_node_in_db, 
    create_node_full_with_dedup,
    confirm_node_validity_in_db,
    list_review_queue_in_db
)
from services.bg_jobs import trigger_node_background_jobs
from core.ai import extract_nodes_structured
from services.ingest.pipeline import resolve_with_fallback, process_ingestion, safe_parse_nodes_with_repair
from services.ingest.persistence import persist_nodes

logger = logging.getLogger(__name__)

# ─── Schema Metadata (P4.11-I-106) ───────────────────────────────────────────

RELATION_DESCRIPTIONS = {
    "depends_on": "The source node requires the target node's information to be complete or valid.",
    "extends": "The source node provides additional details or builds upon the target node.",
    "related_to": "Generic connection between two relevant concepts.",
    "contradicts": "The source node contains information that conflicts with the target node.",
    "answered_by": "The source node (inquiry) is answered or resolved by the target node (factual/procedural).",
    "similar_to": "Both nodes cover similar topics or concepts.",
    "queried_via_mcp": "The node was involved in a query made through the MCP interface.",
}

CONTENT_TYPE_DESCRIPTIONS = {
    "factual": "Concrete, verifiable information and definitions.",
    "procedural": "Step-by-step instructions, guides, or workflows.",
    "preference": "User preferences, style guides, or subjective choices.",
    "context": "Background information necessary to understand other nodes.",
    "inquiry": "Questions, issues, or gaps in knowledge that need answering.",
}

RELATION_WEIGHTS = {
    "depends_on": 0.8,
    "extends": 0.7,
    "related_to": 0.5,
    "contradicts": -1.0,
    "answered_by": 1.0,
    "similar_to": 0.4,
    "queried_via_mcp": 0.2,
}

# ─── JSON-RPC Helpers ─────────────────────────────────────────────────────────

def jsonrpc_error(id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def jsonrpc_ok(id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def serialize(obj: Any) -> Any:
    """Convert psycopg2 Row objects and datetime to JSON-serializable types."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serialize(i) for i in obj]
    # Handle psycopg2 RealDictRow
    try:
        return {k: serialize(v) for k, v in dict(obj).items()}
    except Exception:
        return str(obj)

# ─── Unified Logging ──────────────────────────────────────────────────────────

def log_mcp_interaction(
    background_tasks: BackgroundTasks,
    ws_id: str,
    tool_name: str,
    query_text: str = "",
    node_id: Optional[str] = None,
    result_count: int = 0,
    tokens: int = 0
):
    """
    Unified logging for MCP: records both the query log and interaction edges.
    Fulfills P4.8-S3-5.
    """
    # 1. Log query for analytics
    background_tasks.add_task(log_mcp_query_internal, ws_id, tool_name, query_text, result_count, tokens)
    
    # 2. Record interaction edge if a specific node was involved
    if node_id:
        background_tasks.add_task(write_mcp_interaction_edge, ws_id, node_id, tool_name, query_text)


TOOLS = [
    {
        "name": "list_workspaces",
        "description": "List all workspaces accessible to the authenticated user.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_nodes",
        "description": "List knowledge nodes in a workspace. Supports keyword search and filtering.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "q":  {"type": "string",  "description": "Keyword search query (optional)"},
                "limit":  {"type": "integer", "description": "Max results (default 50, max 200)"},
                "offset": {"type": "integer", "description": "Pagination offset"},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "get_node",
        "description": "Get a single knowledge node by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "node_id": {"type": "string"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "search_nodes",
        "description": "Search nodes by keyword (supports Chinese/CJK). Returns matching nodes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results (default 20)"},
            },
            "required": ["workspace_id", "query"],
        },
    },
    {
        "name": "search_cross_workspace",
        "description": "Search nodes across ALL accessible workspaces using semantic search.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results per workspace (default 5)"},
                "include_archived": {"type": "boolean", "description": "Whether to include archived nodes", "default": False},
            },
            "required": ["query"],
        },
    },
    {
        "name": "create_node",
        "description": "Create a new knowledge node in a workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "title_zh": {"type": "string"},
                "title_en": {"type": "string"},
                "body_zh": {"type": "string"},
                "body_en": {"type": "string"},
                "content_type": {"type": "string", "enum": sorted(list(VALID_CONTENT_T))},
                "content_format": {"type": "string", "enum": ["plain", "markdown"], "default": "plain"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "visibility": {"type": "string", "enum": ["public", "team", "private"], "default": "private"},
                "source_type": {"type": "string", "enum": ["human", "ai"], "default": "human"},
                "trust_score": {"type": "number", "description": "0.0–1.0"},
            },
            "required": ["workspace_id", "title_en", "content_type"],
        },
    },
    {
        "name": "update_node",
        "description": "Update an existing knowledge node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_id": {"type": "string"},
                "title_zh": {"type": "string"},
                "title_en": {"type": "string"},
                "body_zh": {"type": "string"},
                "body_en": {"type": "string"},
                "content_type": {"type": "string"},
                "content_format": {"type": "string", "enum": ["plain", "markdown"]},
                "tags": {"type": "array", "items": {"type": "string"}},
                "visibility": {"type": "string", "enum": ["public", "team", "private"]},
                "trust_score": {"type": "number"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "delete_node",
        "description": "Archive (soft-delete) a knowledge node.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_id": {"type": "string"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "create_edge",
        "description": "Create a directed edge (relationship) between two nodes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "from_id": {"type": "string", "description": "Source node ID"},
                "to_id": {"type": "string", "description": "Target node ID"},
                "relation": {"type": "string", "enum": sorted(list(VALID_RELATIONS))},
                "weight": {"type": "number", "description": "Edge weight 0.0–1.0"},
            },
            "required": ["workspace_id", "from_id", "to_id", "relation"],
        },
    },
    {
        "name": "traverse",
        "description": "Traverse the knowledge graph from a starting node, following edges up to a given depth.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_id": {"type": "string", "description": "Starting node ID"},
                "depth": {"type": "integer", "description": "Max traversal depth (default 2)"},
                "relation": {"type": "string", "description": "Filter by relation type (optional)"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "list_by_tag",
        "description": "List all nodes in a workspace that have a specific tag.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "tag": {"type": "string"},
            },
            "required": ["workspace_id", "tag"],
        },
    },
    {
        "name": "get_schema",
        "description": "Return the MemTrace node schema (content types, relations, field definitions).",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_review_queue",
        "description": "List nodes that need review (low trust score or flagged).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "limit": {"type": "integer", "description": "Max results (default 20)"},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "extract_from_text",
        "description": "Extract knowledge nodes from a short snippet of text (up to 8000 chars).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "text": {"type": "string", "description": "Snippet of text to extract from"},
                "doc_type": {"type": "string", "description": "Hint for extraction (e.g. 'api_spec', 'research')", "default": "generic"},
            },
            "required": ["workspace_id", "text"],
        },
    },
    {
        "name": "ingest_document",
        "description": "Ingest a long document into the knowledge base (chunks and extract).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "content": {"type": "string", "description": "Full document content"},
                "title": {"type": "string", "description": "Title for the source document node"},
                "doc_type": {"type": "string", "description": "Document type hint", "default": "generic"},
            },
            "required": ["workspace_id", "content", "title"],
        },
    },
    {
        "name": "get_ingestion_status",
        "description": "Check status of a long-running ingestion job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "job_id": {"type": "string"},
            },
            "required": ["workspace_id", "job_id"],
        },
    },
]

async def execute_tool(name: str, args: dict, user: dict, background_tasks: BackgroundTasks) -> Any:
    # ── list_workspaces ───────────────────────────────────────────────────────
    if name == "list_workspaces":
        with db_cursor() as cur:
            return list_workspaces_in_db(cur, search=None, user=user)

    # ── list_nodes ────────────────────────────────────────────────────────────
    if name == "list_nodes":
        ws_id = args.get("workspace_id", "")
        q      = args.get("q", "")
        limit  = min(int(args.get("limit", 50)), 200)
        offset = int(args.get("offset", 0))
        with db_cursor() as cur:
             return list_nodes_in_db(cur, ws_id, q=q, tag=None, content_type=None, limit=limit, offset=offset, status="active", filter=None, include_source=False, user=user)

    # ── get_node ──────────────────────────────────────────────────────────────
    # ── get_node ──────────────────────────────────────────────────────────────
    if name == "get_node":
        ws_id   = args["workspace_id"]
        node_id = args["node_id"]
        with db_cursor() as cur:
            node = get_node_in_db(cur, ws_id, node_id, user)
            if node:
                log_mcp_interaction(background_tasks, ws_id, name, node_id=node_id)
            return node

    # ── search_nodes ──────────────────────────────────────────────────────────
    if name == "search_nodes":
        ws_id = args["workspace_id"]
        query = args.get("query", "")
        limit = min(int(args.get("limit", 20)), 100)
        with db_cursor() as cur:
            results = await search_nodes_in_db(cur, ws_id, query, limit, user)
            if not results and query:
                background_tasks.add_task(handle_search_miss, ws_id, query, user["sub"])
            elif results:
                log_mcp_interaction(background_tasks, ws_id, name, query_text=query, result_count=len(results))
                for r in results[:3]:
                    background_tasks.add_task(write_mcp_interaction_edge, ws_id, r["id"], name, query)
            return results

    # ── search_cross_workspace ────────────────────────────────────────────────
    if name == "search_cross_workspace":
        query_text = args["query"]
        limit_per = min(int(args.get("limit", 5)), 10)
        include_archived = args.get("include_archived", False)
        
        results = []
        warnings = []
        with db_cursor() as cur:
            workspaces = list_workspaces_in_db(cur, search=None, user=user)
            
            # Group by (prov, model) to minimize embedding calls and detect dim issues early
            model_groups = {}
            for ws in workspaces:
                ws_id = ws["id"]
                cur.execute("SELECT embedding_model, embedding_provider FROM workspaces WHERE id = %s", (ws_id,))
                row = cur.fetchone()
                key = (row["embedding_provider"], row["embedding_model"]) if row else (None, None)
                if key not in model_groups: model_groups[key] = []
                model_groups[key].append(ws)
                
            for (prov, model), group_wss in model_groups.items():
                try:
                    # Search each workspace in the group. perform_semantic_search will
                    # call embed() for the first one in the group (internally cached or per-call).
                    # Note: perform_semantic_search now raises RuntimeError on failure.
                    for ws in group_wss:
                        try:
                            ws_res = await perform_semantic_search(
                                cur, ws["id"], query_text, user["sub"], 
                                limit=limit_per, ws_model=model, ws_prov=prov,
                                include_archived=include_archived
                            )
                            for r in ws_res:
                                r["workspace_name"] = ws["name"]
                            results.extend(ws_res)
                        except Exception as e:
                            warnings.append(f"Skipped workspace '{ws['name']}': {str(e)}")
                except Exception as group_err:
                    # This shouldn't happen usually as the inner loop catches, but just in case
                    warnings.append(f"Model group {model} failed: {str(group_err)}")
        
        # Sort combined results by similarity
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        final_res = results[:20]
        
        log_mcp_interaction(background_tasks, "all", name, query_text=query_text, result_count=len(final_res))
        
        output = {"results": final_res}
        if warnings:
            output["warnings"] = warnings
        return output

    # ── create_node ───────────────────────────────────────────────────────────
    if name == "create_node":
        ws_id = args["workspace_id"]
        with db_cursor() as cur:
            cur.execute("SELECT settings FROM workspaces WHERE id = %s", (ws_id,))
            ws_row = cur.fetchone()
            settings = ws_row["settings"] if ws_row else {}
            if not settings.get("mcp_ingest_enabled"):
                raise HTTPException(status_code=403, detail="MCP ingestion is not enabled for this workspace. Enable it in Workspace Settings.")

        force_create = args.get("force_create", False)
        # S9-1c: Force source_type to 'mcp'
        mcp_payload = args.copy()
        mcp_payload["source_type"] = "mcp"
        
        with db_cursor(commit=True) as cur:
            node, review_id, dup_info = await create_node_full_with_dedup(cur, ws_id, mcp_payload, user, force_create=force_create)
            
            if dup_info:
                return dup_info
            
            if review_id:
                from core.ai_review import run_ai_review_for_item
                background_tasks.add_task(run_ai_review_for_item, review_id)
                log_mcp_interaction(background_tasks, ws_id, name, query_text=f"Create pending: {args.get('title_en') or args.get('title_zh')}")
                return {"review_id": review_id, "status": "pending_review"}
            
            log_mcp_interaction(background_tasks, ws_id, name, node_id=node["id"], query_text=f"Created: {node.get('title_en') or node.get('title_zh')}")
            trigger_node_background_jobs(background_tasks, ws_id, node["id"], user["sub"], node)
            return node

    # ── update_node ───────────────────────────────────────────────────────────
    if name == "update_node":
        ws_id   = args["workspace_id"]
        node_id = args["node_id"]
        with db_cursor(commit=True) as cur:
            res = update_node_in_db(cur, ws_id, node_id, args, user["sub"])
            log_mcp_interaction(background_tasks, ws_id, name, node_id=node_id)
            return res

    # ── delete_node ───────────────────────────────────────────────────────────
    if name == "delete_node":
        ws_id   = args["workspace_id"]
        node_id = args["node_id"]
        with db_cursor(commit=True) as cur:
            res = delete_node_in_db(cur, ws_id, node_id)
            log_mcp_interaction(background_tasks, ws_id, name, node_id=node_id)
            return res

    # ── create_edge ───────────────────────────────────────────────────────────
    if name == "create_edge":
        ws_id = args["workspace_id"]
        with db_cursor(commit=True) as cur:
            require_ws_access(cur, ws_id, user, write=True, required_role="admin")
            return create_edge_in_db(cur, ws_id, args)

    # ── traverse ──────────────────────────────────────────────────────────────
    if name == "traverse":
        ws_id     = args["workspace_id"]
        root_id   = args["node_id"]
        depth     = min(int(args.get("depth", 2)), 4)
        with db_cursor() as cur:
            workspace = require_ws_access(cur, ws_id, user, write=False)
            viewer_role = get_effective_role(cur, ws_id, workspace["owner_id"], user["sub"])
            result = bfs_neighborhood(
                cur, ws_id, root_id,
                depth=depth,
                relation=None,
                direction="both",
                include_source=False,
                viewer_role=viewer_role,
            )
            log_mcp_interaction(background_tasks, ws_id, name, node_id=root_id)
            return result

    # ── list_by_tag ───────────────────────────────────────────────────────────
    if name == "list_by_tag":
        ws_id = args["workspace_id"]
        tag   = args["tag"]
        with db_cursor() as cur:
            return list_nodes_in_db(cur, ws_id, tag=tag, status="active", user=user)

    # ── get_schema ────────────────────────────────────────────────────────────
    if name == "get_schema":
        relation_info = {
            r: {
                "description": RELATION_DESCRIPTIONS.get(r, ""),
                "default_weight": RELATION_WEIGHTS.get(r, 1.0)
            } for r in VALID_RELATIONS
        }
        content_type_info = {
            ct: CONTENT_TYPE_DESCRIPTIONS.get(ct, "") for ct in VALID_CONTENT_T
        }
        return {
            "content_types": content_type_info,
            "relations":     relation_info,
            "fields": {
                "id":             "string — unique node ID (mem_...)",
                "workspace_id":   "string — workspace identifier",
                "title_zh":       "string — Chinese title",
                "title_en":       "string — English title",
                "body_zh":        "string — Chinese body content",
                "body_en":        "string — English body content",
                "content_type":   "string — classification (factual, procedural, inquiry, etc.)",
                "content_format": "string — 'plain' or 'markdown'",
                "tags":           "array of strings — keywords and categories",
                "visibility":     "string — 'public', 'team', or 'private'",
                "trust_score":    "float 0.0–1.0 — composite reliability score",
                "dim_accuracy":   "float 0.0–1.0 — accuracy dimension of trust",
                "dim_freshness":  "float 0.0–1.0 — freshness dimension of trust",
                "dim_utility":    "float 0.0–1.0 — utility dimension of trust",
                "dim_author_rep": "float 0.0–1.0 — author reputation dimension",
                "source_type":    "string — 'human', 'ai', 'mcp', 'document', etc.",
                "source_doc_node_id": "string — ID of the source document node (if extracted)",
                "source_paragraph_ref": "string — reference to specific paragraph in source",
                "validity_confirmed_at": "datetime — last manual confirmation of validity",
                "validity_confirmed_by": "string — email of the confirmer",
                "ask_count":      "integer — number of times this node was explicitly requested",
                "miss_count":     "integer — number of times this node was a candidate but dismissed",
                "traversal_count": "integer — number of times this node was traversed via edges",
                "unique_traverser_count": "integer — number of unique users who traversed this node",
                "status":         "string — 'active', 'archived', 'gap', etc.",
                "archived_at":    "datetime — when the node was archived",
                "created_at":     "datetime — node creation time",
                "updated_at":     "datetime — last update time",
                "author":         "string — email or ID of the creator",
                "signature":      "string — SHA-256 content signature",
            },
        }

    # ── list_review_queue ─────────────────────────────────────────────────────
    if name == "list_review_queue":
        ws_id = args["workspace_id"]
        limit = min(int(args.get("limit", 20)), 100)
        with db_cursor() as cur:
            return list_review_queue_in_db(cur, ws_id, limit, user)

    # ── extract_from_text ─────────────────────────────────────────────────────
    if name == "extract_from_text":
        ws_id = args["workspace_id"]
        text = args["text"]
        doc_type = args.get("doc_type", "generic")
        if len(text) > 8000:
             raise HTTPException(status_code=400, detail="Text too long for extract_from_text (max 8000 chars); use ingest_document instead")
        
        with db_cursor() as cur:
            cur.execute("SELECT settings, extraction_provider FROM workspaces WHERE id = %s", (ws_id,))
            ws_row = cur.fetchone()
            settings = ws_row["settings"] if ws_row else {}
            if not settings.get("mcp_ingest_enabled"):
                raise HTTPException(status_code=403, detail="MCP ingestion is not enabled for this workspace. Enable it in Workspace Settings.")
            ws_extraction_provider = ws_row["extraction_provider"] if ws_row else None

        if ws_extraction_provider:
            resolved = resolve_provider(user["sub"], "extraction", preferred_provider=ws_extraction_provider)
        else:
            resolved = resolve_with_fallback(user["sub"], "extraction")

        raw_nodes, tokens = await extract_nodes_structured(resolved, text, [], doc_type=doc_type)
        nodes_data, _ = await safe_parse_nodes_with_repair(raw_nodes, resolved, "mcp_snippet")
        
        with db_cursor(commit=True) as cur:
            r_ids = await persist_nodes(cur, ws_id, nodes_data, "mcp_job", "mcp_snippet", user["sub"], resolved, doc_type=doc_type)
            
            # P4.8-S9-4e: Trigger complexity detection
            from services.bg_jobs import bg_check_complexity
            from core.ai_review import run_ai_review_for_item
            
            extracted_info = []
            for rid, node_data in r_ids:
                if rid:
                    background_tasks.add_task(run_ai_review_for_item, rid)
                    background_tasks.add_task(bg_check_complexity, ws_id, rid, user["sub"])
                    extracted_info.append({
                        "review_id": rid,
                        "title_zh": node_data.get("title_zh"),
                        "title_en": node_data.get("title_en"),
                        "status": "pending_review"
                    })
                else:
                    extracted_info.append({
                        "title_en": node_data.get("title_en"),
                        "status": "skipped_duplicate"
                    })
            
            log_mcp_interaction(background_tasks, ws_id, name, query_text=f"Extracted {len(nodes_data)} nodes from snippet")
            return {
                "nodes_extracted": len(nodes_data),
                "nodes": extracted_info,
                "skipped_duplicates": len([1 for rid, _ in r_ids if not rid])
            }

    # ── ingest_document ───────────────────────────────────────────────────────
    if name == "ingest_document":
        ws_id = args["workspace_id"]
        content = args["content"]
        title = args["title"]
        doc_type = args.get("doc_type", "generic")
        
        job_id = generate_id("ing")
        
        with db_cursor(commit=True) as cur:
            require_ws_access(cur, ws_id, user, write=True)
            
            # P4.8-S9-7f: Workspace check mcp_ingest_enabled
            cur.execute("SELECT settings FROM workspaces WHERE id = %s", (ws_id,))
            ws_row = cur.fetchone()
            settings = ws_row["settings"] if ws_row else {}
            if not settings.get("mcp_ingest_enabled"):
                raise HTTPException(status_code=403, detail="MCP ingestion is not enabled for this workspace. Enable it in Workspace Settings.")
            
            # P4.8-S9-7g: Quota check
            quota = settings.get("mcp_ingest_daily_quota", 5)
            cur.execute(
                "SELECT COUNT(*) FROM ingestion_logs WHERE workspace_id = %s AND source = 'mcp' AND created_at >= CURRENT_DATE",
                (ws_id,)
            )
            count = cur.fetchone()["count"]
            if count >= quota:
                raise HTTPException(status_code=429, detail=f"Daily MCP ingestion quota ({quota}) exceeded for this workspace.")

            cur.execute(
                """INSERT INTO ingestion_logs (id, workspace_id, filename, status, created_at, source)
                   VALUES (%s, %s, %s, 'pending', now(), 'mcp')""",
                (job_id, ws_id, title),
            )
        
        # We always run it via background_tasks to avoid MCP timeout
        background_tasks.add_task(process_ingestion, job_id, ws_id, content, user["sub"], title, doc_type)
        log_mcp_interaction(background_tasks, ws_id, name, query_text=f"Ingesting: {title}")
        return {"job_id": job_id, "status": "pending"}

    # ── get_ingestion_status ──────────────────────────────────────────────────
    if name == "get_ingestion_status":
        ws_id = args["workspace_id"]
        job_id = args["job_id"]
        with db_cursor() as cur:
            require_ws_access(cur, ws_id, user)
            cur.execute(
                """SELECT status, progress, error_message, started_at, created_at, 
                          nodes_created, nodes_skipped, source, chunks_total, chunks_done
                   FROM ingestion_logs WHERE id = %s AND workspace_id = %s""", 
                (job_id, ws_id)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Job not found")
            return dict(row)

    raise ValueError(f"Unknown tool: {name}")

async def dispatch(payload: dict, user: dict, background_tasks: BackgroundTasks) -> dict:
    msg_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    try:
        if method == "initialize":
             return jsonrpc_ok(msg_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "memtrace", "version": "1.0.0"}})
        if method == "tools/list":
             return jsonrpc_ok(msg_id, {"tools": TOOLS})
        if method == "tools/call":
             tool_name = params.get("name")
             tool_args = params.get("arguments", {})
             logger.info(f"MCP Call: {tool_name} with args {tool_args}")
             result = await execute_tool(tool_name, tool_args, user, background_tasks)
             return jsonrpc_ok(msg_id, {"content": [{"type": "text", "text": json.dumps(serialize(result), indent=2, ensure_ascii=False)}]})
        
        return jsonrpc_error(msg_id, -32601, f"Method not found: {method}")
    except Exception as e:
        logger.exception(f"MCP dispatch error: {e}")
        return jsonrpc_error(msg_id, -32603, str(e))
