from typing import Any, Dict, Optional, List, Union
import datetime
import logging
import re
import json
import time as _time
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
    list_review_queue_in_db,
    sync_node_from_source_in_db,
    transfer_authorship_in_db,
    resolve_conflict_in_db
)
from services.synthesis import generate_cluster_summary, suggest_missing_edges
from services.bg_jobs import trigger_node_background_jobs
from core.ai import extract_nodes_structured
from services.ingest.pipeline import resolve_with_fallback, process_ingestion, safe_parse_nodes_with_repair, resolve_provider
from services.ingest.persistence import persist_nodes
from services.audit import verify_audit_chain

logger = logging.getLogger(__name__)

# ── D3: Task claim registry (run-state, not knowledge graph — A7) ─────────────
# Per-process in-memory store. Fine for single-process; swap to Redis for multi.
_TASK_CLAIMS: dict[str, dict] = {}   # "<ws_id>:<task_id>" → {"agent_sub": str, "at": float}
_CLAIM_TTL = 1800                    # 30-minute auto-release

def _claim_key(ws_id: str, task_id: str) -> str:
    return f"{ws_id}:{task_id}"

def _gc_claims():
    now = _time.monotonic()
    for k in list(_TASK_CLAIMS):
        if now - _TASK_CLAIMS[k]["at"] > _CLAIM_TTL:
            _TASK_CLAIMS.pop(k, None)

# ─── Schema Metadata (P4.11-I-106) ───────────────────────────────────────────

RELATION_DESCRIPTIONS = {
    "depends_on": "The source node requires the target node's information to be complete or valid.",
    "extends": "The source node provides additional details or builds upon the target node.",
    "related_to": "Generic connection between two relevant concepts.",
    "contradicts": "The source node contains information that conflicts with the target node.",
    "answered_by": "The source node (inquiry) is answered or resolved by the target node (factual/procedural).",
    "similar_to": "Both nodes cover similar topics or concepts.",
    "queried_via_mcp": "The node was involved in a query made through the MCP interface.",
    "proceeds_to": "Conditional next step in a troubleshooting or workflow graph. Use edge metadata.condition to specify when this path is taken.",
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
    "proceeds_to": 0.9,
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
                "include_answered_inquiries": {"type": "boolean", "description": "Whether to include inquiry nodes already resolved by answered_by edges", "default": False},
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
                "detail_level": {"type": "string", "enum": ["probe", "brief", "full"], "description": "Detail level of returned nodes (optional)"},
                "max_response_tokens": {"type": "integer", "description": "Max response tokens (optional)"},
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
                "detail_level": {"type": "string", "enum": ["probe", "brief", "full"], "description": "Detail level of returned nodes (optional)"},
                "max_response_tokens": {"type": "integer", "description": "Max response tokens (optional)"},
                "include_answered_inquiries": {"type": "boolean", "description": "Whether to include inquiry nodes already resolved by answered_by edges", "default": False},
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
                "include_answered_inquiries": {"type": "boolean", "description": "Whether to include inquiry nodes already resolved by answered_by edges", "default": False},
            },
            "required": ["query"],
        },
    },
    {
        "name": "create_node",
        "description": "Create a new knowledge node in a workspace. NOTE: If you need to immediately search or retrieve this node by meaning (semantic search) after creation, you must call `wait_for_embedding(workspace_id, node_id)` first. Creating a node schedules an asynchronous embedding task, and it will not appear in semantic search results until that task completes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "content_type": {"type": "string", "enum": sorted(list(VALID_CONTENT_T))},
                "content_format": {"type": "string", "enum": ["plain", "markdown"], "default": "plain"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "visibility": {"type": "string", "enum": ["public", "team", "private"], "default": "private"},
                "source_type": {"type": "string", "enum": ["human", "ai"], "default": "human"},
                "trust_score": {"type": "number", "description": "0.0–1.0"},
            },
            "required": ["workspace_id", "title", "content_type"],
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
                "title": {"type": "string"},
                "body": {"type": "string"},
                "content_type": {"type": "string"},
                "content_format": {"type": "string", "enum": ["plain", "markdown"]},
                "tags": {"type": "array", "items": {"type": "string"}},
                "visibility": {"type": "string", "enum": ["public", "team", "private"]},
                "trust_score": {"type": "number"},
                "resolution_status": {"type": "string", "enum": ["open", "resolved", "superseded"]},
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
        "name": "wait_for_embedding",
        "description": "Block until the background embedding task for a given node completes. Use this immediately after `create_node` if you need the new node to appear in subsequent semantic searches.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_id": {"type": "string"},
                "timeout_seconds": {"type": "integer", "description": "Max seconds to wait (default 30, max 60)"}
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "get_embedding_status",
        "description": "Check the workspace's embedding queue status. Returns the number of nodes waiting for embeddings or failing in the retry queue.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"}
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "create_edge",
        "description": "Create a directed edge (relationship) between two nodes. For troubleshooting graphs, use relation='proceeds_to' with metadata.condition to specify when this path is taken.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "from_id": {"type": "string", "description": "Source node ID"},
                "to_id": {"type": "string", "description": "Target node ID"},
                "relation": {"type": "string", "enum": sorted(list(VALID_RELATIONS))},
                "weight": {"type": "number", "description": "Edge weight 0.0–1.0"},
                "half_life_days": {"type": "integer", "description": "Days before this edge decays (default: auto from content_type). Use 365 for troubleshooting steps."},
                "metadata": {
                    "type": "object",
                    "description": "Arbitrary metadata. For troubleshooting edges: {\"condition\": \"timeout\", \"condition_type\": \"tool_output_match\"}",
                    "properties": {
                        "condition": {"type": "string", "description": "The condition string to match against tool output (e.g. 'timeout', 'connection refused')"},
                        "condition_type": {"type": "string", "enum": ["tool_output_match", "manual", "always"], "description": "How the condition is evaluated"}
                    }
                },
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
                "detail_level": {"type": "string", "enum": ["probe", "brief", "full"], "description": "Detail level of returned nodes (optional)"},
                "max_response_tokens": {"type": "integer", "description": "Max response tokens (optional)"},
                "tool_output": {"type": "string", "description": "The output of the last tool execution to evaluate conditions (optional)"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "consult",
        "description": "Consult the higher-level troubleshooting assistant when stuck at a dead-end.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "stuck_node_id": {"type": "string", "description": "The node ID where the traversal got stuck"},
                "problem_context": {"type": "string", "description": "Context of the issue or tool outputs that did not match any condition"},
                "mode": {"type": "string", "enum": ["interpret", "generate"], "description": "Consultation mode: 'interpret' to recommend existing nodes, 'generate' to generate a new troubleshooting step"},
                "inquiry_path_id": {"type": "string", "description": "Optional inquiry path ID to track this session"},
            },
            "required": ["workspace_id", "stuck_node_id", "problem_context", "mode"],
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
    {
        "name": "sync_from_source",
        "description": "Manually pull and sync a copy node from its original source.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_id": {"type": "string", "description": "ID of the copy node"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "transfer_authorship",
        "description": "Transfer authorship of nodes to a new user (useful when an author leaves).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_ids": {"type": "array", "items": {"type": "string"}},
                "new_author_id": {"type": "string", "description": "User ID of the new author"},
            },
            "required": ["workspace_id", "node_ids", "new_author_id"],
        },
    },
    {
        "name": "resolve_conflict",
        "description": "Resolve a contradiction conflict between two nodes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "review_id": {"type": "string", "description": "ID of the conflict review item"},
                "resolution": {"type": "string", "enum": ["keep_a", "keep_b", "merge", "both_valid"]},
                "merge_data": {"type": "object", "description": "New node data if resolution is 'merge'"},
            },
            "required": ["workspace_id", "review_id", "resolution"],
        },
    },
    {
        "name": "verify_audit",
        "description": "Verify the integrity of the workspace audit trail (hash chain).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "summarize_cluster",
        "description": "Generate a hierarchical summary node for a group of related nodes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_ids": {"type": "array", "items": {"type": "string"}, "description": "List of node IDs to summarize"},
            },
            "required": ["workspace_id", "node_ids"],
        },
    },
    {
        "name": "complement_node_languages",
        "description": "Automatically translate or complete missing ZH/EN content for a node.",
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
        "name": "suggest_edges",
        "description": "Find and suggest missing 'similar_to' edges based on semantic similarity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "threshold": {"type": "number", "description": "Similarity threshold (default 0.85)", "default": 0.85},
            },
            "required": ["workspace_id"],
        },
    },
    # ── Phase 6: Document tools ────────────────────────────────────────────────
    {
        "name": "list_documents",
        "description": "List all uploaded documents in a workspace. Documents are first-class citizens that can be linked to multiple knowledge nodes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "limit":  {"type": "integer", "description": "Max results (default 20, max 100)"},
                "offset": {"type": "integer", "description": "Pagination offset"},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "get_document",
        "description": "Retrieve a document's metadata and its list of linked knowledge nodes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "document_id": {"type": "string", "description": "Document ID (doc_...)"},
            },
            "required": ["workspace_id", "document_id"],
        },
    },
    {
        "name": "get_node_sources",
        "description": "Return the source documents linked to a knowledge node, including excerpt and paragraph reference.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "node_id": {"type": "string", "description": "Node ID (mem_...)"},
            },
            "required": ["workspace_id", "node_id"],
        },
    },
    {
        "name": "attach_url",
        "description": "Register an external URL as a source document and optionally link it to a knowledge node. Use this to permanently associate a web page, data source, or reference link with a node so it can be retrieved later.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "url":          {"type": "string", "description": "The external URL to attach (must start with http:// or https://)"},
                "node_id":      {"type": "string", "description": "Node ID to link this URL to (optional)"},
                "title":        {"type": "string", "description": "Human-readable title for the link (optional)"},
            },
            "required": ["workspace_id", "url"],
        },
    },
    {
        "name": "attach_evidence",
        "description": "Attach a lightweight evidence snippet to a node without triggering AI extraction.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "node_id": {"type": "string", "description": "Node ID to attach evidence to"},
                "raw_text": {"type": "string", "description": "Raw text content of the evidence"},
                "source_url": {"type": "string", "description": "Source URL of the evidence (optional)"},
                "paragraph_ref": {"type": "string", "description": "Reference within the source (optional)"},
            },
            "required": ["workspace_id", "node_id", "raw_text"],
        },
    },
    {
        "name": "upload_file",
        "description": "Upload a file as a source document (base64-encoded, max 30 MB) and optionally link it to a knowledge node. Suitable for attaching CSV, Excel, PDF, or other data files that should be retrievable later.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id":   {"type": "string", "description": "Workspace ID"},
                "filename":       {"type": "string", "description": "Original filename including extension (e.g. data.csv)"},
                "content_base64": {"type": "string", "description": "File content encoded as base64"},
                "mime_type":      {"type": "string", "description": "MIME type (e.g. text/csv, application/pdf). Inferred from filename if omitted."},
                "node_id":        {"type": "string", "description": "Node ID to link this file to (optional)"},
            },
            "required": ["workspace_id", "filename", "content_base64"],
        },
    },
    {
        "name": "record_path",
        "description": "Record an agent inquiry session exploration path including query text, node sequence, and outcome.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "query_text": {"type": "string", "description": "The search query that started the exploration"},
                "node_sequence": {"type": "array", "items": {"type": "string"}, "description": "List of node IDs visited during the exploration"},
                "outcome": {"type": "string", "enum": ["success", "partial", "failed", "gap"], "description": "Exploration result outcome"},
                "started_at": {"type": "string", "description": "ISO datetime string when the exploration session started"},
                "token_used": {"type": "integer", "description": "Approximate token count consumed (optional)"},
                "rating": {"type": "integer", "description": "Optional human rating or agent rating of the path usefulness"},
                "metadata": {"type": "object", "description": "Arbitrary metadata associated with the path (optional)"},
            },
            "required": ["workspace_id", "query_text", "node_sequence", "outcome", "started_at"],
        },
    },
    {
        "name": "search_with_history",
        "description": "Search for highly similar past inquiry paths to reuse or replay successful exploration trajectories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "query_text": {"type": "string", "description": "The search query to match against history"},
                "similarity_threshold": {"type": "number", "description": "Minimum similarity score 0.0-1.0 (default 0.85)"},
                "limit": {"type": "integer", "description": "Max results to return (default 3)"},
            },
            "required": ["workspace_id", "query_text"],
        },
    },
    # ── Phase 6: Agent loop spine tools ───────────────────────────────────────
    {
        "name": "get_next_task",
        "description": (
            "Pick the next pending inquiry node and return a token-limited context bundle "
            "containing: the task, its ancestor intent (via depends_on), any related spec "
            "nodes, and the relevant development playbook. "
            "Use this to start a small-task development loop."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "tag": {"type": "string", "description": "Filter inquiries by this tag (optional)"},
                "limit": {"type": "integer", "description": "Max tasks to return (default 3, max 10)"},
                "max_response_tokens": {"type": "integer", "description": "Token budget for the context bundle (optional)"},
                "exclusive": {"type": "boolean", "description": "If true, claimed tasks are filtered out and returned tasks are auto-claimed — enables multi-planner coordination (default false)."},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "get_playbook",
        "description": (
            "Retrieve a procedural playbook node given a situation description. "
            "Use this to find the relevant how-to guide before developing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "situation": {"type": "string", "description": "Description of the current situation or task type"},
                "tag": {"type": "string", "description": "Filter procedural nodes by tag (optional)"},
                "limit": {"type": "integer", "description": "Max playbooks to return (default 3)"},
            },
            "required": ["workspace_id", "situation"],
        },
    },
    {
        "name": "propose_decision",
        "description": (
            "Submit a proposed decision (new node or update) to the human review queue. "
            "High-risk changes (public interface, security, cross-module) always require human approval. "
            "Low-risk changes may be auto-accepted if confidence meets the workspace threshold."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "title": {"type": "string", "description": "Title of the proposed node/decision"},
                "body": {"type": "string", "description": "Body/rationale of the proposal"},
                "content_type": {"type": "string", "enum": ["factual", "procedural", "preference", "context"], "description": "Content type (default factual)"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for the proposed node"},
                "task_node_id": {"type": "string", "description": "The inquiry node this decision resolves (optional)"},
                "confidence_score": {"type": "number", "description": "Agent confidence 0.0-1.0 (default 0.7)"},
                "risk_level": {"type": "string", "enum": ["low", "medium", "high"], "description": "Risk level (default medium); low may be auto-accepted"},
            },
            "required": ["workspace_id", "title"],
        },
    },
    {
        "name": "submit_outcome",
        "description": (
            "Report the outcome of a completed small task. "
            "On success: links the implementation node via answered_by; "
            "if all sibling subtasks of the parent inquiry are now answered, "
            "automatically queues a per-feature integration-check for human review "
            "(feature_complete_triggered=true in response). "
            "On failure: flags any procedural playbooks visited for human review "
            "(returned as flagged_playbooks). "
            "Records the path for reinforcement learning. "
            "This is the auto side of two-speed evolution — no human gate."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "task_node_id": {"type": "string", "description": "The inquiry node that was completed"},
                "outcome": {"type": "string", "enum": ["success", "partial", "failed"], "description": "Outcome of the task"},
                "implementation_node_id": {"type": "string", "description": "Node that answers/implements the inquiry (required for success/partial)"},
                "node_sequence": {"type": "array", "items": {"type": "string"}, "description": "IDs of nodes visited during the task"},
                "message": {"type": "string", "description": "Free-text result summary"},
                "token_used": {"type": "integer", "description": "Approximate tokens consumed"},
            },
            "required": ["workspace_id", "task_node_id", "outcome"],
        },
    },
    {
        "name": "emit_residue",
        "description": (
            "Create new pending inquiry nodes from conclusions/observations of the current loop. "
            "Each residue becomes fuel for the next planning iteration. "
            "This is a lightweight auto write — residues enter the graph as pending inquiries "
            "and are triaged by the planner in the next loop without per-item human approval."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "residues": {
                    "type": "array",
                    "description": "List of new gaps/observations to record",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "body":  {"type": "string"},
                            "tags":  {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["title"],
                    },
                },
                "parent_task_id": {"type": "string", "description": "The task node that generated these residues (optional)"},
            },
            "required": ["workspace_id", "residues"],
        },
    },
    # ── Phase 6 Sprint D: convergence + multi-planner ─────────────────────────
    {
        "name": "converge_check",
        "description": (
            "Check whether the agent loop should converge (stop), continue, or escalate to human. "
            "Returns pending/answered task counts and a recommendation based on simple heuristics: "
            "'converge' when no pending tasks remain or <10% left; "
            "'escalate' when recent failure rate ≥50% over ≥3 paths; "
            "'continue' otherwise."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "tag": {"type": "string", "description": "Filter scope to this tag (optional)"},
            },
            "required": ["workspace_id"],
        },
    },
    {
        "name": "converge_proposals",
        "description": (
            "Decide whether competing planning proposals have converged or should escalate to a human. "
            "Reuses the consult synthesizer: returns 'converge' when proposals reach consensus, "
            "'escalate' when they diverge/contradict. "
            "Use this at the multi-agent planning/discussion stage before committing to a next step."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "proposals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Competing planner proposals (free text) to compare for consensus",
                },
                "task_node_id": {"type": "string", "description": "The inquiry node being planned (optional, for logging)"},
            },
            "required": ["workspace_id", "proposals"],
        },
    },
    {
        "name": "claim_task",
        "description": (
            "Claim a pending inquiry node so other planners won't pick it up. "
            "Claims expire after 30 minutes. "
            "Returns claimed=false if already claimed by another agent."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "task_node_id": {"type": "string", "description": "Inquiry node to claim"},
            },
            "required": ["workspace_id", "task_node_id"],
        },
    },
    {
        "name": "release_task",
        "description": (
            "Release your claim on a task so other planners can pick it up. "
            "No-op if the task is not currently claimed. "
            "Returns released=false if the claim belongs to a different agent."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Workspace ID"},
                "task_node_id": {"type": "string", "description": "Inquiry node to release"},
            },
            "required": ["workspace_id", "task_node_id"],
        },
    },
]

# ─── Token Budget & Detail Level Helpers ──────────────────────────────────────
USER_CAPABILITIES: dict[str, dict] = {}
LEVEL_ORDER = ["full", "brief", "probe"]

try:
    import tiktoken
    _encoder = tiktoken.get_encoding("cl100k_base")
    def estimate_tokens(text: str) -> int:
        return len(_encoder.encode(text))
except Exception:
    def estimate_tokens(text: str) -> int:
        return len(text) // 4 + 1

def serialize_and_estimate_tokens(obj: Any) -> tuple[str, int]:
    serialized_str = json.dumps(serialize(obj), ensure_ascii=False)
    return serialized_str, estimate_tokens(serialized_str)

def get_default_detail_level(user_sub: Optional[str]) -> str:
    if not user_sub:
        return "brief"
    cap = USER_CAPABILITIES.get(user_sub, {})
    model_size = cap.get("model_size", "medium")
    if model_size == "small":
        return "probe"
    elif model_size == "large":
        return "full"
    return "brief"

def optimize_node_response(cur, ws_id: str, node: dict, initial_level: str, max_tokens: Optional[int]) -> dict:
    from services.node_projection import project_node, get_node_top_edges
    
    top_edges = get_node_top_edges(cur, ws_id, node["id"])
    
    current_level = initial_level
    level_idx = LEVEL_ORDER.index(current_level) if current_level in LEVEL_ORDER else 1
    
    projected = None
    while level_idx < len(LEVEL_ORDER):
        lvl = LEVEL_ORDER[level_idx]
        projected = project_node(node, lvl, top_edges)
        if max_tokens is None:
            return projected
        
        _, token_count = serialize_and_estimate_tokens(projected)
        if token_count <= max_tokens:
            return projected
        
        level_idx += 1
        
    original_size = serialize_and_estimate_tokens(projected)[1]
    
    if "top_edges" in projected and projected["top_edges"]:
        projected = dict(projected)
        projected["top_edges"] = []
        _, token_count = serialize_and_estimate_tokens(projected)
        if token_count <= max_tokens:
            projected["truncated"] = True
            projected["original_size"] = original_size
            return projected
            
    if "tags" in projected and projected["tags"]:
        projected = dict(projected)
        projected["tags"] = []
        _, token_count = serialize_and_estimate_tokens(projected)
        if token_count <= max_tokens:
            projected["truncated"] = True
            projected["original_size"] = original_size
            return projected
            
    if "summary_1line" in projected and len(projected["summary_1line"]) > 10:
        projected = dict(projected)
        summary = projected["summary_1line"]
        while len(summary) > 10:
            summary = summary[:-10]
            projected["summary_1line"] = summary + "..."
            _, token_count = serialize_and_estimate_tokens(projected)
            if token_count <= max_tokens:
                projected["truncated"] = True
                projected["original_size"] = original_size
                return projected
                
    min_node = {
        "id": node.get("id"),
        "title": node.get("title"),
        "truncated": True,
        "original_size": original_size
    }
    return min_node

def optimize_nodes_list_response(cur, ws_id: str, nodes: list[dict], initial_level: str, max_tokens: Optional[int]) -> Any:
    from services.node_projection import project_node, get_node_top_edges
    
    if not nodes:
        return []
        
    current_level = initial_level
    level_idx = LEVEL_ORDER.index(current_level) if current_level in LEVEL_ORDER else 1
    
    projected_list = []
    while level_idx < len(LEVEL_ORDER):
        lvl = LEVEL_ORDER[level_idx]
        projected_list = []
        for n in nodes:
            top_edges = get_node_top_edges(cur, ws_id, n["id"]) if lvl in ('probe', 'brief') else None
            projected_list.append(project_node(n, lvl, top_edges))
            
        if max_tokens is None:
            return projected_list
            
        _, token_count = serialize_and_estimate_tokens(projected_list)
        if token_count <= max_tokens:
            return projected_list
            
        level_idx += 1
        
    original_size = serialize_and_estimate_tokens(projected_list)[1]
    
    while len(projected_list) > 1:
        projected_list.pop()
        resp = {
            "results": projected_list,
            "truncated": True,
            "original_size": original_size
        }
        _, token_count = serialize_and_estimate_tokens(resp)
        if token_count <= max_tokens:
            return resp
            
    min_single_node = optimize_node_response(cur, ws_id, nodes[0], "probe", max_tokens)
    return {
        "results": [min_single_node],
        "truncated": True,
        "original_size": original_size
    }

def optimize_traverse_response(cur, ws_id: str, traverse_result: dict, initial_level: str, max_tokens: Optional[int]) -> dict:
    from services.node_projection import project_node, get_node_top_edges
    
    nodes = traverse_result.get("nodes", [])
    edges = traverse_result.get("edges", [])
    orig_truncated = traverse_result.get("truncated", False)
    
    current_level = initial_level
    level_idx = LEVEL_ORDER.index(current_level) if current_level in LEVEL_ORDER else 1
    
    projected_result = {}
    dead_end_val = traverse_result.get("dead_end", False)
    
    while level_idx < len(LEVEL_ORDER):
        lvl = LEVEL_ORDER[level_idx]
        projected_nodes = []
        for n in nodes:
            top_edges = get_node_top_edges(cur, ws_id, n["id"]) if lvl in ('probe', 'brief') else None
            projected_nodes.append(project_node(n, lvl, top_edges))
            
        projected_result = {
            "nodes": projected_nodes,
            "edges": edges,
            "truncated": orig_truncated,
            "total_nodes": len(projected_nodes),
            "dead_end": dead_end_val
        }
        
        if max_tokens is None:
            return projected_result
            
        _, token_count = serialize_and_estimate_tokens(projected_result)
        if token_count <= max_tokens:
            return projected_result
            
        level_idx += 1
        
    original_size = serialize_and_estimate_tokens(projected_result)[1]
    
    if edges:
        projected_result["edges"] = []
        projected_result["truncated"] = True
        projected_result["original_size"] = original_size
        _, token_count = serialize_and_estimate_tokens(projected_result)
        if token_count <= max_tokens:
            return projected_result
            
    p_nodes = projected_result["nodes"]
    while len(p_nodes) > 1:
        p_nodes.pop()
        projected_result["nodes"] = p_nodes
        projected_result["truncated"] = True
        projected_result["original_size"] = original_size
        _, token_count = serialize_and_estimate_tokens(projected_result)
        if token_count <= max_tokens:
            return projected_result
            
    min_single_node = optimize_node_response(cur, ws_id, nodes[0], "probe", max_tokens)
    projected_result["nodes"] = [min_single_node]
    projected_result["truncated"] = True
    projected_result["original_size"] = original_size
    return projected_result

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
        include_answered_inquiries = bool(args.get("include_answered_inquiries", False))
        with db_cursor() as cur:
             return list_nodes_in_db(
                 cur,
                 ws_id,
                 q=q,
                 tag=None,
                 content_type=None,
                 limit=limit,
                 offset=offset,
                 status="active",
                 filter=None,
                 include_source=False,
                 user=user,
                 include_answered_inquiries=include_answered_inquiries,
             )

    # ── get_node ──────────────────────────────────────────────────────────────
    # ── get_node ──────────────────────────────────────────────────────────────
    if name == "get_node":
        ws_id   = args["workspace_id"]
        node_id = args["node_id"]
        detail_level = args.get("detail_level") or get_default_detail_level(user.get("sub"))
        max_tokens = args.get("max_response_tokens")
        if max_tokens is not None:
            max_tokens = int(max_tokens)
        with db_cursor() as cur:
            node = get_node_in_db(cur, ws_id, node_id, user)
            if node:
                log_mcp_interaction(background_tasks, ws_id, name, node_id=node_id)
                return optimize_node_response(cur, ws_id, node, detail_level, max_tokens)
            return node

    # ── search_nodes ──────────────────────────────────────────────────────────
    if name == "search_nodes":
        ws_id = args["workspace_id"]
        query = args.get("query", "")
        limit = min(int(args.get("limit", 20)), 100)
        detail_level = args.get("detail_level") or get_default_detail_level(user.get("sub"))
        max_tokens = args.get("max_response_tokens")
        if max_tokens is not None:
            max_tokens = int(max_tokens)
        include_answered_inquiries = bool(args.get("include_answered_inquiries", False))
        with db_cursor() as cur:
            results = await search_nodes_in_db(
                cur,
                ws_id,
                query,
                limit,
                user,
                include_answered_inquiries=include_answered_inquiries,
            )
            if not results and query:
                background_tasks.add_task(handle_search_miss, ws_id, query, user["sub"])
            elif results:
                log_mcp_interaction(background_tasks, ws_id, name, query_text=query, result_count=len(results))
                for r in results[:3]:
                    background_tasks.add_task(write_mcp_interaction_edge, ws_id, r["id"], name, query)
                results = optimize_nodes_list_response(cur, ws_id, results, detail_level, max_tokens)
            return results

    # ── search_cross_workspace ────────────────────────────────────────────────
    if name == "search_cross_workspace":
        query_text = args["query"]
        limit_per = min(int(args.get("limit", 5)), 10)
        include_archived = args.get("include_archived", False)
        include_answered_inquiries = bool(args.get("include_answered_inquiries", False))
        
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
                                include_archived=include_archived,
                                include_answered_inquiries=include_answered_inquiries,
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
            settings = (ws_row["settings"] if ws_row else {}) or {}
            if not settings.get("mcp_ingest_enabled"):
                logger.warning(f"MCP Ingestion blocked: ws_id={ws_id}, settings={settings}, row_exists={ws_row is not None}")
                raise HTTPException(status_code=403, detail=f"MCP ingestion is not enabled for workspace '{ws_id}'. Enable it in Workspace Settings.")

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
                log_mcp_interaction(background_tasks, ws_id, name, query_text=f"Create pending: {args.get('title')}")
                return {"review_id": review_id, "status": "pending_review"}
            
            log_mcp_interaction(background_tasks, ws_id, name, node_id=node["id"], query_text=f"Created: {node.get('title')}")
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
        detail_level = args.get("detail_level") or get_default_detail_level(user.get("sub"))
        max_tokens = args.get("max_response_tokens")
        tool_output = args.get("tool_output")
        if max_tokens is not None:
            max_tokens = int(max_tokens)
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
                tool_output=tool_output,
            )
            log_mcp_interaction(background_tasks, ws_id, name, node_id=root_id)
            return optimize_traverse_response(cur, ws_id, result, detail_level, max_tokens)

    # ── consult ───────────────────────────────────────────────────────────────
    if name == "consult":
        ws_id = args["workspace_id"]
        stuck_node_id = args["stuck_node_id"]
        problem_context = args["problem_context"]
        mode = args["mode"]
        inquiry_path_id = args.get("inquiry_path_id")
        
        from services.consult import consult as run_consult
        res = await run_consult(
            ws_id=ws_id,
            stuck_node_id=stuck_node_id,
            problem_context=problem_context,
            mode=mode,
            user=user,
            inquiry_path_id=inquiry_path_id
        )
        return res

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
                "title":          "string — title of the node",
                "body":           "string — body content of the node",
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
            settings = (ws_row["settings"] if ws_row else {}) or {}
            if not settings.get("mcp_ingest_enabled"):
                logger.warning(f"MCP Ingestion blocked: ws_id={ws_id}, settings={settings}, row_exists={ws_row is not None}")
                raise HTTPException(status_code=403, detail=f"MCP ingestion is not enabled for workspace '{ws_id}'. Enable it in Workspace Settings.")
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
                        "title": node_data.get("title"),
                        "status": "pending_review"
                    })
                else:
                    extracted_info.append({
                        "title": node_data.get("title"),
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
            settings = (ws_row["settings"] if ws_row else {}) or {}
            if not settings.get("mcp_ingest_enabled"):
                logger.warning(f"MCP Ingestion blocked: ws_id={ws_id}, settings={settings}, row_exists={ws_row is not None}")
                raise HTTPException(status_code=403, detail=f"MCP ingestion is not enabled for workspace '{ws_id}'. Enable it in Workspace Settings.")
            
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
                """INSERT INTO ingestion_logs (id, workspace_id, user_id, filename, status, created_at, source)
                   VALUES (%s, %s, %s, %s, 'pending', now(), 'mcp')""",
                (job_id, ws_id, user["sub"], title),
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
                """SELECT status, progress, error_msg, started_at, created_at, 
                          nodes_created, nodes_skipped, source, chunks_total, chunks_done
                   FROM ingestion_logs WHERE id = %s AND workspace_id = %s""", 
                (job_id, ws_id)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Job not found")
            return dict(row)
            
    # ── sync_from_source ──────────────────────────────────────────────────────
    if name == "sync_from_source":
        ws_id = args["workspace_id"]
        node_id = args["node_id"]
        with db_cursor(commit=True) as cur:
            node, review_id = sync_node_from_source_in_db(cur, ws_id, node_id, user)
            if review_id:
                return {"review_id": review_id, "status": "pending_review", "detail": "Sync request submitted for review."}
            log_mcp_interaction(background_tasks, ws_id, name, node_id=node_id)
            return node

    # ── transfer_authorship ───────────────────────────────────────────────────
    if name == "transfer_authorship":
        ws_id = args["workspace_id"]
        node_ids = args["node_ids"]
        new_author_id = args["new_author_id"]
        with db_cursor(commit=True) as cur:
            count = transfer_authorship_in_db(cur, ws_id, node_ids, new_author_id, user)
            log_mcp_interaction(background_tasks, ws_id, name, query_text=f"Transferred {count} nodes to {new_author_id}")
            return {"transferred_count": count}

    # ── resolve_conflict ──────────────────────────────────────────────────────
    if name == "resolve_conflict":
        ws_id = args["workspace_id"]
        review_id = args["review_id"]
        resolution = args["resolution"]
        merge_data = args.get("merge_data")
        with db_cursor(commit=True) as cur:
            res = resolve_conflict_in_db(cur, ws_id, review_id, resolution, user["sub"], merge_data)
            log_mcp_interaction(background_tasks, ws_id, name, query_text=f"Resolved conflict {review_id} via {resolution}")
            return res

    # ── verify_audit ──────────────────────────────────────────────────────────
    if name == "verify_audit":
        ws_id = args["workspace_id"]
        with db_cursor() as cur:
            return verify_audit_chain(cur, ws_id)

    # ── summarize_cluster ─────────────────────────────────────────────────────
    if name == "summarize_cluster":
        ws_id = args["workspace_id"]
        node_ids = args["node_ids"]
        with db_cursor(commit=True) as cur:
            summary_id = await generate_cluster_summary(cur, ws_id, node_ids, user["sub"])
            if not summary_id:
                return {"error": "Failed to generate summary."}
            log_mcp_interaction(background_tasks, ws_id, name, node_id=summary_id, query_text=f"Summarized {len(node_ids)} nodes")
            return {"summary_node_id": summary_id, "status": "created"}

    # ── complement_node_languages ─────────────────────────────────────────────
    if name == "complement_node_languages":
        raise HTTPException(status_code=410, detail="This tool is obsolete under single-language schema")

    # ── suggest_edges ─────────────────────────────────────────────────────────
    if name == "suggest_edges":
        ws_id = args["workspace_id"]
        threshold = float(args.get("threshold", 0.85))
        with db_cursor() as cur:
            suggestions = await suggest_missing_edges(cur, ws_id, threshold)
            return {"suggestions": suggestions}

    # ── list_documents ────────────────────────────────────────────────────────
    if name == "list_documents":
        ws_id  = args["workspace_id"]
        limit  = min(int(args.get("limit", 20)), 100)
        offset = int(args.get("offset", 0))
        from services.documents import list_documents_in_db
        with db_cursor() as cur:
            require_ws_access(cur, ws_id, user)
            return list(list_documents_in_db(cur, ws_id, limit=limit, offset=offset))

    # ── get_document ──────────────────────────────────────────────────────────
    if name == "get_document":
        ws_id   = args["workspace_id"]
        doc_id  = args["document_id"]
        from services.documents import get_document_in_db, get_document_linked_nodes
        with db_cursor() as cur:
            require_ws_access(cur, ws_id, user)
            doc = get_document_in_db(cur, doc_id)
            if not doc or doc["workspace_id"] != ws_id:
                raise HTTPException(status_code=404, detail="Document not found")
            nodes = get_document_linked_nodes(cur, doc_id)
            return {**dict(doc), "linked_nodes": list(nodes)}

    # ── get_node_sources ──────────────────────────────────────────────────────
    if name == "get_node_sources":
        ws_id   = args["workspace_id"]
        node_id = args["node_id"]
        from services.documents import get_node_sources
        with db_cursor() as cur:
            require_ws_access(cur, ws_id, user)
            cur.execute(
                "SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s",
                (node_id, ws_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Node not found")
            sources = get_node_sources(cur, node_id)
            log_mcp_interaction(background_tasks, ws_id, name, node_id=node_id)
            return list(sources)

    # ── attach_url ────────────────────────────────────────────────────────────
    if name == "attach_url":
        ws_id   = args["workspace_id"]
        url     = args["url"]
        node_id = args.get("node_id")
        title   = args.get("title")
        if not url.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        from services.documents import (
            create_url_document_in_db, create_node_document_link,
            get_existing_document, get_document_in_db,
        )
        import hashlib as _hl
        with db_cursor(commit=True) as cur:
            require_ws_access(cur, ws_id, user, write=True)
            row = create_url_document_in_db(cur, ws_id, url, user["sub"], title=title)
            if row is None:
                row = get_existing_document(cur, ws_id, _hl.sha256(url.encode()).hexdigest())
            if node_id:
                cur.execute(
                    "SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s",
                    (node_id, ws_id),
                )
                if cur.fetchone():
                    create_node_document_link(cur, node_id, row["id"])
        with db_cursor() as cur:
            doc = get_document_in_db(cur, row["id"])
        result = {k: v for k, v in dict(doc).items() if k != "embedding"}
        log_mcp_interaction(background_tasks, ws_id, name, node_id=node_id)
        return result

    # ── attach_evidence (C1-T25) ──────────────────────────────────────────────
    if name == "attach_evidence":
        ws_id = args["workspace_id"]
        node_id = args["node_id"]
        raw_text = args["raw_text"]
        source_url = args.get("source_url")
        paragraph_ref = args.get("paragraph_ref")
        
        import hashlib as _hl
        content_hash = _hl.sha256(raw_text.encode('utf-8')).hexdigest()
        
        from services.documents import create_document_in_db, get_existing_document, create_node_document_link
        with db_cursor(commit=True) as cur:
            require_ws_access(cur, ws_id, user, write=True)
            
            # Check if node exists
            cur.execute("SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
            if not cur.fetchone():
                raise ValueError(f"Node {node_id} not found in workspace {ws_id}")
                
            existing = get_existing_document(cur, ws_id, content_hash)
            if existing:
                doc_id = existing["id"]
            else:
                title_snip = raw_text[:50].replace('\n', ' ')
                title = f"Agent Evidence: {title_snip}..." if len(raw_text) > 50 else f"Agent Evidence: {raw_text}"
                row = create_document_in_db(
                    cur, workspace_id=ws_id, filename=title,
                    file_bytes=raw_text.encode('utf-8'), mime_type="text/plain",
                    storage_path=None, uploaded_by=user["sub"],
                    source_url=source_url,
                    evidence_type="agent_attached"
                )
                doc_id = row["id"]
                
            # Create link and extracted_from edge (P61-T01 requirement)
            link_id = create_node_document_link(cur, node_id, doc_id, paragraph_ref)
            
            # For P61-T01 extracted_from edge
            # Ensure document node exists (it might be created by trigger_node_background_jobs or create_document_in_db natively now)
            cur.execute("SELECT node_id FROM documents WHERE id = %s", (doc_id,))
            doc_row = cur.fetchone()
            if doc_row and doc_row.get("node_id"):
                doc_node_id = doc_row["node_id"]
                try:
                    create_edge_in_db(cur, ws_id, {
                        "from_id": node_id,
                        "to_id": doc_node_id,
                        "relation": "extracted_from",
                        "weight": 1.0,
                    })
                except Exception as e:
                    logger.warning(f"Failed to create extracted_from edge: {e}")

            log_mcp_interaction(background_tasks, ws_id, name, node_id=node_id)
            return {"document_id": doc_id, "link_id": link_id}

    # ── upload_file ───────────────────────────────────────────────────────────
    if name == "upload_file":
        import base64, mimetypes as _mt, uuid as _uuid
        ws_id    = args["workspace_id"]
        filename = args["filename"]
        b64      = args["content_base64"]
        node_id  = args.get("node_id")
        mime     = args.get("mime_type") or _mt.guess_type(filename)[0] or "application/octet-stream"
        try:
            file_bytes = base64.b64decode(b64)
        except Exception:
            raise ValueError("content_base64 is not valid base64")
        if len(file_bytes) > 30 * 1024 * 1024:
            raise ValueError("File exceeds 30 MB limit")
        from services.documents import (
            create_document_in_db, create_node_document_link,
            get_existing_document, get_document_in_db,
        )
        from core.storage import default_storage
        import hashlib as _hl
        content_hash = _hl.sha256(file_bytes).hexdigest()
        with db_cursor(commit=True) as cur:
            require_ws_access(cur, ws_id, user, write=True)
            existing = get_existing_document(cur, ws_id, content_hash)
            if existing:
                doc_id = existing["id"]
            else:
                storage_path = default_storage.make_path(ws_id, f"{_uuid.uuid4().hex}_{filename}")
                default_storage.put(storage_path, file_bytes)
                row = create_document_in_db(
                    cur, workspace_id=ws_id, filename=filename,
                    file_bytes=file_bytes, mime_type=mime,
                    storage_path=storage_path, uploaded_by=user["sub"],
                )
                doc_id = row["id"] if row else existing["id"]
            if node_id:
                cur.execute(
                    "SELECT 1 FROM memory_nodes WHERE id = %s AND workspace_id = %s",
                    (node_id, ws_id),
                )
                if cur.fetchone():
                    create_node_document_link(cur, node_id, doc_id)
        with db_cursor() as cur:
            doc = get_document_in_db(cur, doc_id)
        result = {k: v for k, v in dict(doc).items() if k not in ("embedding", "storage_path")}
        log_mcp_interaction(background_tasks, ws_id, name, node_id=node_id)
        return result

    # ── wait_for_embedding (C3-T32) ───────────────────────────────────────────
    if name == "wait_for_embedding":
        ws_id = args["workspace_id"]
        node_id = args["node_id"]
        timeout = min(int(args.get("timeout_seconds", 30)), 60)
        
        import asyncio
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            with db_cursor() as cur:
                require_ws_access(cur, ws_id, user, write=False)
                cur.execute("SELECT embedding FROM memory_nodes WHERE id = %s AND workspace_id = %s", (node_id, ws_id))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Node {node_id} not found")
                if row["embedding"] is not None:
                    return {"status": "ready", "node_id": node_id, "waited_seconds": round(asyncio.get_event_loop().time() - start_time, 2)}
            
            await asyncio.sleep(1.0)
            
        return {"status": "timeout", "message": f"Embedding still not ready after {timeout} seconds", "node_id": node_id}

    # ── get_embedding_status (C3-T32) ─────────────────────────────────────────
    if name == "get_embedding_status":
        ws_id = args["workspace_id"]
        with db_cursor() as cur:
            require_ws_access(cur, ws_id, user, write=False)
            cur.execute("SELECT count(*) as count FROM memory_nodes WHERE workspace_id = %s AND embedding IS NULL", (ws_id,))
            null_count = cur.fetchone()["count"]
            cur.execute("SELECT count(*) as count FROM embed_retry_queue WHERE workspace_id = %s", (ws_id,))
            failed_count = cur.fetchone()["count"]
            return {
                "workspace_id": ws_id,
                "missing_embeddings_count": null_count,
                "failed_embeddings_count": failed_count,
                "system_status": "congested" if failed_count > 10 or null_count > 50 else "normal"
            }

    # ── record_path ───────────────────────────────────────────────────────────
    if name == "record_path":
        ws_id = args["workspace_id"]
        from services.inquiry_paths import record_path_in_db
        with db_cursor(commit=True) as cur:
            require_ws_access(cur, ws_id, user, write=False)
            res = await record_path_in_db(cur, ws_id, user["sub"], args)
            return res

    # ── search_with_history ───────────────────────────────────────────────────
    if name == "search_with_history":
        ws_id = args["workspace_id"]
        query_text = args["query_text"]
        similarity_threshold = float(args.get("similarity_threshold", 0.85))
        limit = int(args.get("limit", 3))
        from services.inquiry_paths import search_with_history_in_db
        with db_cursor() as cur:
            require_ws_access(cur, ws_id, user, write=False)
            res = await search_with_history_in_db(cur, ws_id, query_text, similarity_threshold, limit, user["sub"])
            return res

    # ── get_next_task ─────────────────────────────────────────────────────────
    if name == "get_next_task":
        ws_id     = args["workspace_id"]
        tag       = args.get("tag")
        limit     = min(int(args.get("limit", 3)), 10)
        max_tok   = args.get("max_response_tokens")
        exclusive = bool(args.get("exclusive", False))
        if max_tok is not None:
            max_tok = int(max_tok)

        with db_cursor() as cur:
            require_ws_access(cur, ws_id, user, write=False)

            # 1. Find pending inquiry nodes
            if tag:
                cur.execute(
                    """SELECT id, title, body, tags, trust_score
                       FROM memory_nodes
                       WHERE workspace_id = %s AND content_type = 'inquiry'
                         AND status = 'active' AND %s = ANY(tags)
                       ORDER BY trust_score DESC, created_at ASC
                       LIMIT %s""",
                    (ws_id, tag, limit),
                )
            else:
                cur.execute(
                    """SELECT id, title, body, tags, trust_score
                       FROM memory_nodes
                       WHERE workspace_id = %s AND content_type = 'inquiry'
                         AND status = 'active'
                       ORDER BY trust_score DESC, created_at ASC
                       LIMIT %s""",
                    (ws_id, limit),
                )
            inquiry_rows = cur.fetchall()

            # D3: exclusive mode — filter out claimed tasks, auto-claim returned ones
            if exclusive:
                _gc_claims()
                inquiry_rows = [r for r in inquiry_rows if _claim_key(ws_id, r["id"]) not in _TASK_CLAIMS]
                inquiry_rows = inquiry_rows[:limit]

            tasks = []
            for row in inquiry_rows:
                task_id = row["id"]
                bundle = {
                    "task": {
                        "id": task_id,
                        "title": row["title"],
                        "body": row["body"],
                        "tags": list(row["tags"] or []),
                        "trust_score": float(row["trust_score"]),
                    },
                    "ancestors": [],
                    "playbooks": [],
                }

                # 2. Traverse up via depends_on for ancestor intent
                cur.execute(
                    """WITH RECURSIVE ancestors AS (
                           SELECT e.to_id AS node_id, 1 AS depth
                           FROM edges e
                           WHERE e.workspace_id = %s AND e.from_id = %s
                             AND e.relation = 'depends_on' AND e.status = 'active'
                           UNION ALL
                           SELECT e.to_id, a.depth + 1
                           FROM edges e
                           JOIN ancestors a ON e.from_id = a.node_id
                           WHERE e.workspace_id = %s AND e.relation = 'depends_on'
                             AND e.status = 'active' AND a.depth < 4
                       )
                       SELECT DISTINCT m.id, m.title, m.body, m.content_type
                       FROM ancestors a
                       JOIN memory_nodes m ON m.id = a.node_id
                       WHERE m.workspace_id = %s AND m.status = 'active'
                       ORDER BY m.id""",
                    (ws_id, task_id, ws_id, ws_id),
                )
                bundle["ancestors"] = [
                    {"id": r["id"], "title": r["title"],
                     "body": r["body"][:300], "content_type": r["content_type"]}
                    for r in cur.fetchall()
                ]

                # 3. Find related playbooks (procedural) via related_to edges or shared tags
                related_ids_via_edge = set()
                cur.execute(
                    """SELECT CASE WHEN e.from_id = %s THEN e.to_id ELSE e.from_id END AS other_id
                       FROM edges e
                       WHERE e.workspace_id = %s AND (e.from_id = %s OR e.to_id = %s)
                         AND e.relation IN ('related_to', 'depends_on') AND e.status = 'active'""",
                    (task_id, ws_id, task_id, task_id),
                )
                for er in cur.fetchall():
                    related_ids_via_edge.add(er["other_id"])

                if related_ids_via_edge:
                    cur.execute(
                        """SELECT id, title, body FROM memory_nodes
                           WHERE workspace_id = %s AND id = ANY(%s)
                             AND content_type = 'procedural' AND status = 'active'
                           LIMIT 3""",
                        (ws_id, list(related_ids_via_edge)),
                    )
                    bundle["playbooks"] = [
                        {"id": r["id"], "title": r["title"], "body": r["body"][:500]}
                        for r in cur.fetchall()
                    ]

                # Fallback: tag-based playbook lookup
                if not bundle["playbooks"]:
                    task_tags = list(row["tags"] or [])
                    if task_tags:
                        cur.execute(
                            """SELECT id, title, body FROM memory_nodes
                               WHERE workspace_id = %s AND content_type = 'procedural'
                                 AND status = 'active' AND tags && %s
                               ORDER BY trust_score DESC LIMIT 3""",
                            (ws_id, task_tags),
                        )
                        bundle["playbooks"] = [
                            {"id": r["id"], "title": r["title"], "body": r["body"][:500]}
                            for r in cur.fetchall()
                        ]

                tasks.append(bundle)

            if exclusive:
                now_mono = _time.monotonic()
                for t in tasks:
                    _TASK_CLAIMS[_claim_key(ws_id, t["task"]["id"])] = {
                        "agent_sub": user.get("sub"),
                        "at": now_mono,
                    }

            log_mcp_interaction(background_tasks, ws_id, name,
                                query_text=f"get_next_task tag={tag}", result_count=len(tasks))
            result = {"tasks": tasks, "total": len(tasks)}
            if max_tok:
                _, tc = serialize_and_estimate_tokens(result)
                if tc > max_tok:
                    result["truncated"] = True
            return result

    # ── get_playbook ──────────────────────────────────────────────────────────
    if name == "get_playbook":
        ws_id     = args["workspace_id"]
        situation = args["situation"]
        tag       = args.get("tag")
        limit     = min(int(args.get("limit", 3)), 10)

        with db_cursor() as cur:
            require_ws_access(cur, ws_id, user, write=False)

            if tag:
                cur.execute(
                    """SELECT id, title, body, tags, trust_score
                       FROM memory_nodes
                       WHERE workspace_id = %s AND content_type = 'procedural'
                         AND status = 'active' AND %s = ANY(tags)
                       ORDER BY trust_score DESC LIMIT %s""",
                    (ws_id, tag, limit),
                )
                rows = cur.fetchall()
            else:
                # Keyword search in search_vector
                cur.execute(
                    """SELECT id, title, body, tags, trust_score,
                              ts_rank(search_vector,
                                  to_tsquery('simple', regexp_replace(%s, '\W+', ' | ', 'g'))
                              ) AS rank
                       FROM memory_nodes
                       WHERE workspace_id = %s AND content_type = 'procedural'
                         AND status = 'active'
                         AND search_vector @@ plainto_tsquery('simple', %s)
                       ORDER BY rank DESC, trust_score DESC LIMIT %s""",
                    (situation, ws_id, situation, limit),
                )
                rows = cur.fetchall()
                if not rows:
                    # Fallback: return top procedural nodes by trust
                    cur.execute(
                        """SELECT id, title, body, tags, trust_score
                           FROM memory_nodes
                           WHERE workspace_id = %s AND content_type = 'procedural'
                             AND status = 'active'
                           ORDER BY trust_score DESC LIMIT %s""",
                        (ws_id, limit),
                    )
                    rows = cur.fetchall()

            playbooks = [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "body": r["body"],
                    "tags": list(r["tags"] or []),
                    "trust_score": float(r["trust_score"]),
                }
                for r in rows
            ]
            log_mcp_interaction(background_tasks, ws_id, name,
                                query_text=situation, result_count=len(playbooks))
            return {"playbooks": playbooks}

    # ── propose_decision ──────────────────────────────────────────────────────
    if name == "propose_decision":
        ws_id          = args["workspace_id"]
        title          = args["title"]
        body           = args.get("body", "")
        content_type   = args.get("content_type", "factual")
        tags           = args.get("tags", [])
        task_node_id   = args.get("task_node_id")
        confidence     = float(args.get("confidence_score", 0.7))
        risk_level     = args.get("risk_level", "medium")

        with db_cursor(commit=True) as cur:
            require_ws_access(cur, ws_id, user, write=True)

            # Check workspace auto-accept threshold
            cur.execute(
                "SELECT settings FROM workspaces WHERE id = %s", (ws_id,)
            )
            ws_row = cur.fetchone()
            settings = (ws_row["settings"] if ws_row else {}) or {}
            auto_accept_threshold = float(
                settings.get("ai_reviewers", {}).get("auto_accept_threshold", 0.95)
            )
            auto_reject_threshold = float(
                settings.get("ai_reviewers", {}).get("auto_reject_threshold", 0.2)
            )

            from core.security import generate_id as _gen_id
            review_id = _gen_id("rev")

            node_data = {
                "title": title,
                "body": body,
                "content_type": content_type,
                "content_format": "markdown",
                "tags": tags,
                "visibility": "team",
                "source_type": "mcp",
            }

            cur.execute(
                """INSERT INTO review_queue
                     (id, workspace_id, node_data, change_type, target_node_id,
                      proposer_type, proposer_id, confidence_score, status, source_info)
                   VALUES (%s, %s, %s::jsonb, 'create', %s, 'agent', %s, %s, %s, %s)""",
                (
                    review_id, ws_id,
                    json.dumps(node_data),
                    task_node_id,
                    user.get("sub"),
                    confidence,
                    "pending",
                    f"risk={risk_level}",
                ),
            )

            # Auto-accept low-risk high-confidence proposals
            status = "pending"
            if risk_level == "low" and confidence >= auto_accept_threshold:
                from services.nodes import create_node_in_db
                node_data["author"] = user.get("sub")
                node_data["status"] = "active"
                node = create_node_in_db(cur, ws_id, node_data)
                cur.execute(
                    "UPDATE review_queue SET status='approved', reviewer_type='auto' WHERE id=%s",
                    (review_id,),
                )
                if task_node_id:
                    from services.edges import create_edge_in_db as _create_edge
                    try:
                        _create_edge(cur, ws_id, {
                            "from_id": task_node_id,
                            "to_id": node["id"],
                            "relation": "answered_by",
                            "weight": confidence,
                        })
                    except Exception:
                        pass
                status = "auto_approved"
                log_mcp_interaction(background_tasks, ws_id, name,
                                    node_id=node["id"], query_text=f"Auto-approved: {title}")
                return {"review_id": review_id, "status": status, "node_id": node["id"]}

            if confidence <= auto_reject_threshold:
                cur.execute(
                    "UPDATE review_queue SET status='rejected', reviewer_type='auto' WHERE id=%s",
                    (review_id,),
                )
                status = "auto_rejected"

            log_mcp_interaction(background_tasks, ws_id, name,
                                query_text=f"Proposed: {title}")
            return {"review_id": review_id, "status": status}

    # ── submit_outcome ────────────────────────────────────────────────────────
    if name == "submit_outcome":
        ws_id       = args["workspace_id"]
        task_id     = args["task_node_id"]
        outcome     = args["outcome"]
        impl_id     = args.get("implementation_node_id")
        node_seq    = args.get("node_sequence") or [task_id]
        message     = args.get("message", "")
        token_used  = args.get("token_used")
        flagged_playbooks: list[str] = []
        feature_complete_triggered = False

        with db_cursor(commit=True) as cur:
            require_ws_access(cur, ws_id, user, write=True)

            # Validate inquiry node exists
            cur.execute(
                "SELECT id, status FROM memory_nodes WHERE id = %s AND workspace_id = %s",
                (task_id, ws_id),
            )
            task_row = cur.fetchone()
            if not task_row:
                raise HTTPException(status_code=404, detail=f"Task node {task_id} not found")

            if outcome in ("success", "partial") and impl_id:
                # Create answered_by edge
                try:
                    from services.edges import create_edge_in_db as _create_edge
                    _create_edge(cur, ws_id, {
                        "from_id": task_id,
                        "to_id": impl_id,
                        "relation": "answered_by",
                        "weight": 1.0 if outcome == "success" else 0.7,
                    })
                except Exception:
                    pass

                if outcome == "success":
                    cur.execute(
                        "UPDATE memory_nodes SET status='answered', updated_at=now() "
                        "WHERE id=%s AND workspace_id=%s",
                        (task_id, ws_id),
                    )

                    # C3: If every sibling subtask of the parent inquiry is now answered,
                    # queue a per-feature integration-check for human review.
                    cur.execute(
                        """SELECT e.to_id AS parent_id
                           FROM edges e
                           WHERE e.workspace_id = %s AND e.from_id = %s
                             AND e.relation = 'depends_on' AND e.status = 'active'
                           LIMIT 1""",
                        (ws_id, task_id),
                    )
                    parent_row = cur.fetchone()
                    if parent_row:
                        parent_id = parent_row["parent_id"]
                        cur.execute(
                            """SELECT
                                 COUNT(*) AS total,
                                 COUNT(*) FILTER (WHERE m.status = 'answered') AS answered
                               FROM edges e
                               JOIN memory_nodes m ON m.id = e.from_id
                               WHERE e.workspace_id = %s AND e.to_id = %s
                                 AND e.relation = 'depends_on' AND e.status = 'active'
                                 AND m.content_type = 'inquiry'""",
                            (ws_id, parent_id),
                        )
                        counts = cur.fetchone()
                        if counts and counts["total"] > 0 and counts["total"] == counts["answered"]:
                            cur.execute(
                                """SELECT 1 FROM review_queue
                                   WHERE workspace_id = %s AND target_node_id = %s
                                     AND source_info LIKE 'feature_complete:%%' AND status = 'pending'""",
                                (ws_id, parent_id),
                            )
                            if not cur.fetchone():
                                from services.nodes import propose_change as _propose_change
                                try:
                                    _propose_change(
                                        cur, ws_id,
                                        change_type="update",
                                        target_node_id=parent_id,
                                        node_data={},
                                        proposer_type="ai",
                                        proposer_id=user.get("sub"),
                                        proposer_meta={
                                            "completed_subtasks": list(set(node_seq)),
                                            "subtask_count": int(counts["total"]),
                                        },
                                        source_info=f"feature_complete:parent={parent_id}",
                                        confidence_score=0.6,
                                    )
                                    feature_complete_triggered = True
                                except Exception as e:
                                    logger.warning(f"submit_outcome C3: feature check failed for parent {parent_id}: {e}")

            # B2: On failure, flag procedural playbooks visited during the task for human review.
            # Skips any playbook that already has a pending update review (dedup).
            if outcome == "failed" and node_seq:
                from services.nodes import propose_change as _propose_change
                cur.execute(
                    """SELECT id FROM memory_nodes
                       WHERE workspace_id = %s AND id = ANY(%s)
                         AND content_type = 'procedural' AND status = 'active'
                       LIMIT 3""",
                    (ws_id, list(node_seq)),
                )
                for pb in cur.fetchall():
                    pb_id = pb["id"]
                    cur.execute(
                        """SELECT 1 FROM review_queue
                           WHERE workspace_id = %s AND target_node_id = %s
                             AND change_type = 'update' AND status = 'pending'""",
                        (ws_id, pb_id),
                    )
                    if cur.fetchone():
                        continue
                    try:
                        _propose_change(
                            cur, ws_id,
                            change_type="update",
                            target_node_id=pb_id,
                            node_data={},
                            proposer_type="ai",
                            proposer_id=user.get("sub"),
                            proposer_meta={"task_node_id": task_id, "failure_message": message},
                            source_info=f"agent_failure:task={task_id}",
                            confidence_score=0.5,
                        )
                        flagged_playbooks.append(pb_id)
                    except Exception as e:
                        logger.warning(f"submit_outcome B2: failed to flag playbook {pb_id}: {e}")

        # Record path for reinforcement (auto side, no human gate)
        import datetime as _dt
        from services.inquiry_paths import record_path_in_db
        with db_cursor(commit=True) as cur:
            await record_path_in_db(cur, ws_id, user["sub"], {
                "query_text": message or task_id,
                "node_sequence": node_seq,
                "outcome": outcome if outcome != "partial" else "partial",
                "started_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "token_used": token_used,
                "metadata": {"task_node_id": task_id, "implementation_node_id": impl_id},
            })

        log_mcp_interaction(background_tasks, ws_id, name,
                            node_id=task_id, query_text=f"outcome={outcome}")
        return {
            "task_node_id": task_id,
            "outcome": outcome,
            "implementation_node_id": impl_id,
            "message": message,
            "flagged_playbooks": flagged_playbooks,
            "feature_complete_triggered": feature_complete_triggered,
        }

    # ── emit_residue ──────────────────────────────────────────────────────────
    if name == "emit_residue":
        ws_id       = args["workspace_id"]
        residues    = args["residues"]
        parent_id   = args.get("parent_task_id")

        if not residues:
            return {"created": [], "count": 0}

        created_ids = []
        with db_cursor(commit=True) as cur:
            require_ws_access(cur, ws_id, user, write=True)

            from services.nodes import create_node_in_db
            from services.edges import create_edge_in_db as _create_edge

            for residue in residues[:20]:  # cap at 20 per call
                title = (residue.get("title") or "").strip()
                if not title:
                    continue
                body = residue.get("body") or ""
                tags = list(residue.get("tags") or [])

                node_data = {
                    "title": title,
                    "body": body,
                    "content_type": "inquiry",
                    "content_format": "markdown",
                    "tags": tags,
                    "visibility": "team",
                    "source_type": "mcp",
                    "status": "active",
                    "author": user.get("sub"),
                }
                try:
                    node = create_node_in_db(cur, ws_id, node_data)
                    created_ids.append(node["id"])

                    if parent_id:
                        try:
                            _create_edge(cur, ws_id, {
                                "from_id": node["id"],
                                "to_id": parent_id,
                                "relation": "depends_on",
                                "weight": 0.5,
                            })
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f"emit_residue: skipped node '{title}': {e}")

        log_mcp_interaction(background_tasks, ws_id, name,
                            query_text=f"Emitted {len(created_ids)} residue inquiries")
        return {"created": created_ids, "count": len(created_ids)}

    # ── converge_check ────────────────────────────────────────────────────────
    if name == "converge_check":
        ws_id = args["workspace_id"]
        tag   = args.get("tag")

        with db_cursor() as cur:
            require_ws_access(cur, ws_id, user, write=False)
            if tag:
                cur.execute(
                    """SELECT
                         COUNT(*) FILTER (WHERE status = 'active')   AS pending,
                         COUNT(*) FILTER (WHERE status = 'answered') AS answered
                       FROM memory_nodes
                       WHERE workspace_id = %s AND content_type = 'inquiry'
                         AND %s = ANY(tags)""",
                    (ws_id, tag),
                )
            else:
                cur.execute(
                    """SELECT
                         COUNT(*) FILTER (WHERE status = 'active')   AS pending,
                         COUNT(*) FILTER (WHERE status = 'answered') AS answered
                       FROM memory_nodes
                       WHERE workspace_id = %s AND content_type = 'inquiry'""",
                    (ws_id,),
                )
            counts   = cur.fetchone()
            pending  = int(counts["pending"]  or 0)
            answered = int(counts["answered"] or 0)

            cur.execute(
                """SELECT
                     COUNT(*) FILTER (WHERE outcome = 'failed') AS failed,
                     COUNT(*) AS total
                   FROM inquiry_paths
                   WHERE workspace_id = %s AND started_at > now() - interval '1 hour'""",
                (ws_id,),
            )
            path_row      = cur.fetchone()
            recent_failed = int(path_row["failed"] or 0) if path_row else 0
            recent_total  = int(path_row["total"]  or 0) if path_row else 0
            failure_rate  = round(recent_failed / recent_total, 2) if recent_total else 0.0

        stats = {
            "pending":       pending,
            "answered":      answered,
            "recent_failed": recent_failed,
            "recent_total":  recent_total,
            "failure_rate":  failure_rate,
        }

        if pending == 0:
            recommendation = "converge"
            reason = "No pending inquiries remain — all tasks answered."
        elif failure_rate >= 0.5 and recent_total >= 3:
            recommendation = "escalate"
            reason = f"High failure rate ({failure_rate:.0%}) over last {recent_total} paths. Human review needed."
        elif answered > 0 and pending <= max(1, answered // 10):
            recommendation = "converge"
            reason = f"Only {pending} task(s) remaining vs {answered} answered (≤10%). Near-complete."
        else:
            recommendation = "continue"
            reason = f"{pending} pending vs {answered} answered. Loop should continue."

        log_mcp_interaction(background_tasks, ws_id, name, query_text=f"tag={tag}")
        return {"recommendation": recommendation, "reason": reason, "stats": stats}

    # ── converge_proposals ────────────────────────────────────────────────────
    if name == "converge_proposals":
        ws_id     = args["workspace_id"]
        proposals = args.get("proposals") or []
        task_id   = args.get("task_node_id")

        with db_cursor() as cur:
            require_ws_access(cur, ws_id, user, write=False)

        # Reuse the consult synthesizer for the converge-vs-escalate decision (D2).
        from services.consult import synthesize_responses
        synthesis_result, reasoning = await synthesize_responses(
            ws_id, user.get("sub", "system"), [str(p) for p in proposals]
        )
        recommendation = "converge" if synthesis_result == "consensus" else "escalate"

        log_mcp_interaction(background_tasks, ws_id, name,
                            node_id=task_id,
                            query_text=f"converge_proposals n={len(proposals)} → {recommendation}")
        return {
            "recommendation": recommendation,
            "synthesis_result": synthesis_result,
            "reasoning": reasoning,
            "proposal_count": len(proposals),
        }

    # ── claim_task ────────────────────────────────────────────────────────────
    if name == "claim_task":
        ws_id   = args["workspace_id"]
        task_id = args["task_node_id"]

        _gc_claims()
        key = _claim_key(ws_id, task_id)

        with db_cursor() as cur:
            require_ws_access(cur, ws_id, user, write=False)
            cur.execute(
                "SELECT id FROM memory_nodes WHERE id = %s AND workspace_id = %s AND status = 'active'",
                (task_id, ws_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found or not active")

        existing = _TASK_CLAIMS.get(key)
        if existing and _time.monotonic() - existing["at"] < _CLAIM_TTL:
            if existing["agent_sub"] != user.get("sub"):
                return {"claimed": False, "reason": "already_claimed", "task_node_id": task_id}

        _TASK_CLAIMS[key] = {"agent_sub": user.get("sub"), "at": _time.monotonic()}
        return {"claimed": True, "task_node_id": task_id}

    # ── release_task ──────────────────────────────────────────────────────────
    if name == "release_task":
        ws_id   = args["workspace_id"]
        task_id = args["task_node_id"]

        key   = _claim_key(ws_id, task_id)
        entry = _TASK_CLAIMS.get(key)

        if not entry:
            return {"released": True, "task_node_id": task_id, "note": "task was not claimed"}

        if entry["agent_sub"] != user.get("sub"):
            return {"released": False, "reason": "not_your_claim", "task_node_id": task_id}

        _TASK_CLAIMS.pop(key, None)
        return {"released": True, "task_node_id": task_id}

    raise ValueError(f"Unknown tool: {name}")

async def dispatch(payload: dict, user: dict, background_tasks: BackgroundTasks) -> dict:
    msg_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    try:
        if method == "initialize":
             user_sub = user.get("sub")
             if user_sub:
                 client_capabilities = params.get("capabilities", {})
                 model_size = client_capabilities.get("model_size") or params.get("model_size")
                 context_limit = client_capabilities.get("context_limit") or params.get("context_limit")
                 prefer_format = client_capabilities.get("prefer_format") or params.get("prefer_format")
                 
                 USER_CAPABILITIES[user_sub] = {
                     "model_size": model_size or "medium",
                     "context_limit": context_limit or 8192,
                     "prefer_format": prefer_format or "json"
                 }
             return jsonrpc_ok(msg_id, {
                 "protocolVersion": "2024-11-05", 
                 "capabilities": {
                     "tools": {},
                     "resources": {}
                 }, 
                 "serverInfo": {
                     "name": "memtrace", 
                     "version": "1.0.0"
                 }
             })
             
        if method == "tools/list":
             return jsonrpc_ok(msg_id, {"tools": TOOLS})
             
        if method == "tools/call":
             tool_name = params.get("name")
             tool_args = params.get("arguments", {})
             logger.warning(f"MCP Call: {tool_name} with args {tool_args}")
             result = await execute_tool(tool_name, tool_args, user, background_tasks)
             return jsonrpc_ok(msg_id, {"content": [{"type": "text", "text": json.dumps(serialize(result), indent=2, ensure_ascii=False)}]})

        # ── Markdown Resource Handlers (A2-T03) ──────────────────────────────────
        if method == "resources/list":
             return jsonrpc_ok(msg_id, {"resources": []})

        if method == "resources/templates/list":
             return jsonrpc_ok(msg_id, {
                 "resourceTemplates": [
                     {
                         "uriTemplate": "memtrace://node/{id}",
                         "name": "Node Markdown",
                         "description": "Concise Markdown of a knowledge node by ID.",
                         "mimeType": "text/markdown"
                     },
                     {
                         "uriTemplate": "memtrace://workspace/{workspace_id}/summary",
                         "name": "Workspace Summary",
                         "description": "Overview of a workspace.",
                         "mimeType": "text/markdown"
                     }
                 ]
             })

        if method == "resources/read":
             uri = params.get("uri", "")
             
             node_match = re.match(r"^memtrace://node/([^/]+)$", uri)
             if node_match:
                 node_id = node_match.group(1)
                 with db_cursor() as cur:
                     from services.workspaces import list_workspaces_in_db
                     workspaces = list_workspaces_in_db(cur, search=None, user=user)
                     ws_ids = [w["id"] for w in workspaces]
                     
                     cur.execute(
                         "SELECT * FROM memory_nodes WHERE id = %s AND workspace_id = ANY(%s) AND status = 'active'",
                         (node_id, ws_ids)
                     )
                     node = cur.fetchone()
                     if not node:
                         return jsonrpc_error(msg_id, -32602, f"Node {node_id} not found or no access")
                         
                     cur.execute(
                         """
                         SELECT e.relation, e.from_id, e.to_id, 
                                n.title AS target_title, n.id AS target_id
                         FROM edges e
                         JOIN memory_nodes n ON n.id = CASE WHEN e.from_id = %s THEN e.to_id ELSE e.from_id END
                         WHERE e.workspace_id = %s AND e.status = 'active' AND (e.from_id = %s OR e.to_id = %s)
                         """,
                         (node_id, node["workspace_id"], node_id, node_id)
                     )
                     edges = cur.fetchall()
                     
                     depends_on_list = []
                     extends_list = []
                     contradicts_list = []
                     
                     for e in edges:
                         link = f"[{e['target_title']}](memtrace://node/{e['target_id']})"
                         if e["from_id"] == node_id and e["relation"] == "depends_on":
                             depends_on_list.append(link)
                         elif e["relation"] == "extends":
                             extends_list.append(link)
                         elif e["relation"] == "contradicts":
                             contradicts_list.append(link)
                             
                     depends_str = ", ".join(depends_on_list) if depends_on_list else "無"
                     extends_str = ", ".join(extends_list) if extends_list else "無"
                     contradicts_str = ", ".join(contradicts_list) if contradicts_list else "無"
                     
                     body = node.get("body") or ""
                     body_excerpt = body[:300] + ("..." if len(body) > 300 else "")
                     
                     tags_str = ", ".join(node.get("tags") or []) if node.get("tags") else "無"
                     
                     markdown_content = f"""# {node['title']}

**類型**：{node['content_type']} ｜ **信任**：{node['trust_score'] or 0.0} ｜ **標籤**：{tags_str}

{body_excerpt}

## 關聯
- **依賴**：{depends_str}
- **延伸**：{extends_str}
- **矛盾**：{contradicts_str}
"""
                     return jsonrpc_ok(msg_id, {
                         "contents": [
                             {
                                 "uri": uri,
                                 "mimeType": "text/markdown",
                                 "text": markdown_content
                             }
                         ]
                     })
                     
             ws_match = re.match(r"^memtrace://workspace/([^/]+)/summary$", uri)
             if ws_match:
                 ws_id = ws_match.group(1)
                 with db_cursor() as cur:
                     from services.workspaces import require_ws_access
                     workspace = require_ws_access(cur, ws_id, user, write=False)
                     
                     cur.execute("SELECT COUNT(*) as count FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
                     nodes_count = cur.fetchone()["count"]
                     
                     cur.execute("SELECT COUNT(*) as count FROM edges WHERE workspace_id = %s AND status = 'active'", (ws_id,))
                     edges_count = cur.fetchone()["count"]
                     
                     cur.execute("SELECT tags FROM memory_nodes WHERE workspace_id = %s AND status = 'active'", (ws_id,))
                     rows = cur.fetchall()
                     import collections
                     tag_counter = collections.Counter()
                     for r in rows:
                         if r["tags"]:
                             tag_counter.update(r["tags"])
                             
                     most_common_tags = tag_counter.most_common(10)
                     tags_summary = "\n".join([f"- **{t}** (出現 {c} 次)" for t, c in most_common_tags]) if most_common_tags else "無標籤"
                     
                     cur.execute(
                         "SELECT id, title, content_type, created_at FROM memory_nodes WHERE workspace_id = %s AND status = 'active' ORDER BY created_at DESC LIMIT 5",
                         (ws_id,)
                     )
                     latest_nodes = cur.fetchall()
                     latest_nodes_list = ""
                     for ln in latest_nodes:
                         created_str = ln["created_at"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(ln["created_at"], datetime.datetime) else str(ln["created_at"])
                         latest_nodes_list += f"- [{ln['title']}](memtrace://node/{ln['id']}) ({ln['content_type']}) - {created_str}\n"
                         
                     if not latest_nodes_list:
                         latest_nodes_list = "無節點"
                         
                     created_at_str = workspace["created_at"].strftime("%Y-%m-%d") if isinstance(workspace["created_at"], datetime.datetime) else str(workspace["created_at"])
                     
                     markdown_content = f"""# Workspace 概覽：{workspace['name']}

**語言**：{workspace.get('language') or 'zh-TW'} ｜ **創立時間**：{created_at_str}

## 統計資訊
- **節點總數**：{nodes_count}
- **關聯總數**：{edges_count}

## 主要標籤 (Tags)
{tags_summary}

## 最新節點 (前 5 筆)
{latest_nodes_list}
"""
                     return jsonrpc_ok(msg_id, {
                         "contents": [
                             {
                                 "uri": uri,
                                 "mimeType": "text/markdown",
                                 "text": markdown_content
                             }
                         ]
                     })
                     
             return jsonrpc_error(msg_id, -32602, f"Unknown resource URI: {uri}")
        
        return jsonrpc_error(msg_id, -32601, f"Method not found: {method}")
    except Exception as e:
        logger.exception(f"MCP dispatch error: {e}")
        return jsonrpc_error(msg_id, -32603, str(e))
