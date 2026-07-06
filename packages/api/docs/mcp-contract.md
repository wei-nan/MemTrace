# MemTrace MCP Contract

**Version**: 1.0  
**Protocol**: [Model Context Protocol (MCP)](https://modelcontextprotocol.io) — JSON-RPC 2.0 over HTTP  
**Base URL**: `POST /api/v1/mcp` (SSE streaming) · `POST /mcp` (Streamable HTTP)  
**Authentication**: Bearer token (`Authorization: Bearer <token>`) — issue via `/api/v1/auth/token`

---

## Overview

MemTrace exposes a full MCP-compliant tool interface that allows AI agents (Claude, GPT, etc.) to read, write, and traverse the knowledge graph directly. All tools follow the [MCP specification](https://spec.modelcontextprotocol.io).

### Connection

```
POST /api/v1/mcp        → Server-Sent Events (SSE) streaming
POST /mcp               → Streamable HTTP (simpler, for MCP clients that prefer it)
```

Each request body must be a JSON-RPC 2.0 envelope:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "<tool_name>",
    "arguments": { ... }
  }
}
```

---

## Tool Reference

### `list_workspaces`
List all workspaces accessible to the authenticated user.

**Input**: _(none)_

**Output**:
```json
[
  {
    "id": "ws_abc123",
    "name": "My Knowledge Base",
    "language": "zh-TW",
    "visibility": "private",
    "kb_type": "evergreen"
  }
]
```

---

### `list_nodes`
List knowledge nodes in a workspace with optional keyword search.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | Workspace ID |
| `q` | string | | Keyword search query |
| `limit` | integer | | Max results (default: 50, max: 200) |
| `offset` | integer | | Pagination offset |

**Output**: Array of node objects (see [Node Schema](#node-schema))

---

### `get_node`
Get a single knowledge node by ID.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | Workspace ID |
| `node_id` | string | ✅ | Node ID (`mem_...`) |
| `detail_level` | string | | `"probe"` · `"brief"` · `"full"` |
| `max_response_tokens` | integer | | Token budget cap |

**Output**: Single node object

---

### `search_nodes`
Full-text + semantic search within a workspace. Supports Chinese/CJK.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | Workspace ID |
| `query` | string | ✅ | Search query |
| `limit` | integer | | Max results (default: 20, max: 100) |
| `detail_level` | string | | `"probe"` · `"brief"` · `"full"` |
| `max_response_tokens` | integer | | Token budget cap |
| `include_archived` | boolean | | Whether to include archived nodes (default: false) |
| `include_answered_inquiries` | boolean | | Whether to include resolved inquiry nodes (default: false) |

---

### `search_cross_workspace`
Semantic search across ALL accessible workspaces simultaneously.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | ✅ | Search query |
| `limit` | integer | | Max results per workspace (default: 5) |
| `include_archived` | boolean | | Whether to include archived nodes (default: false) |
| `include_answered_inquiries` | boolean | | Whether to include resolved inquiry nodes (default: false) |

---

### `create_node`
Create a new knowledge node.

> ⚠️ **Embedding note**: Creation schedules an async embedding task. To use the node in subsequent semantic searches, call `wait_for_embedding` first.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | Workspace ID |
| `title` | string | ✅ | Node title |
| `content_type` | string | ✅ | One of: `factual`, `procedural`, `preference`, `context`, `inquiry`, `document` (Phase 6.1), `gap` (Phase 6.2) |
| `body` | string | | Node content |
| `content_format` | string | | `"plain"` (default) or `"markdown"` |
| `tags` | string[] | | Tag array |
| `visibility` | string | | `"public"` · `"team"` · `"private"` (default) |
| `source_type` | string | | `"human"` (default) or `"ai"` |
| `trust_score` | number | | 0.0–1.0 |

**Output**:

- Active success: compact write summary with `id`, `title`, `status`, and `created_at`.
- Pending review: `{ "review_id": "...", "status": "pending_review" }`.
- Duplicate detection: duplicate metadata such as `action` and `existing_node_id`.

The active success response intentionally does not echo `body` or internal bookkeeping fields. Call `get_node` after creation if the full node content is needed.

---

### `update_node`
Update an existing knowledge node.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | |
| `node_id` | string | ✅ | Node ID |
| `title` | string | | |
| `body` | string | | |
| `content_type` | string | | |
| `content_format` | string | | `"plain"` or `"markdown"` |
| `tags` | string[] | | |
| `visibility` | string | | |
| `trust_score` | number | | |

**Output**:

- Active success: compact write summary with `id`, `title`, `status`, and `updated_at`.
- Pending review: `{ "review_id": "...", "status": "pending_review" }`.

The active success response intentionally does not echo `body` or internal bookkeeping fields. Call `get_node` after updating if the full node content is needed.

---

### `delete_node`
Soft-archive a knowledge node (reversible).

**Input**: `workspace_id` (required), `node_id` (required)

---

### `wait_for_embedding`
Block until a node's embedding is computed. Call after `create_node` when semantic search is needed immediately.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | |
| `node_id` | string | ✅ | |
| `timeout_seconds` | integer | | Max wait time (default: 30, max: 60) |

**Output**: `{ "status": "ready" | "timeout" | "not_found" }`

---

### `get_embedding_status`
Check workspace embedding queue status — how many nodes are queued or failing.

**Input**: `workspace_id` (required)

**Output**: `{ "pending_count": N, "retry_queue_count": M }`

---

### `create_edge`
Create a directed semantic edge between two nodes.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | |
| `from_id` | string | ✅ | Source node ID |
| `to_id` | string | ✅ | Target node ID |
| `relation` | string | ✅ | See [Relations](#relations) |
| `weight` | number | | Edge weight 0.0–1.0 |

---

### `traverse`
Traverse the graph from a node, following edges up to a depth.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | |
| `node_id` | string | ✅ | Starting node |
| `depth` | integer | | Max depth (default: 2) |
| `relation` | string | | Filter by relation type |
| `detail_level` | string | | |
| `max_response_tokens` | integer | | |
| `include_faded` | boolean | | Whether to include faded edges (default: false) |

**Output**: `{ "nodes": [...], "edges": [...], "total_nodes": N }`

---

### `list_by_tag`
List all nodes with a specific tag.

**Input**: `workspace_id` (required), `tag` (required)

---

### `get_schema`
Return the MemTrace schema — content types, relations, field definitions.

**Output**: Schema metadata including `content_types`, `relations`, `field_descriptions`

---

### `list_review_queue`
List nodes in the pending-review queue (low trust or flagged).

**Input**: `workspace_id` (required), `limit` (optional, default 20)

---

### `extract_from_text`
Extract knowledge nodes from a text snippet (≤ 8,000 chars) using AI.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | |
| `text` | string | ✅ | Text to extract from |
| `doc_type` | string | | Hint: `"api_spec"`, `"research"`, `"generic"` |

---

### `ingest_document`
Ingest a long document (chunked extraction). Returns a job ID for tracking.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | |
| `content` | string | ✅ | Full document text |
| `title` | string | ✅ | Document title |
| `doc_type` | string | | Type hint |

**Output**: `{ "job_id": "...", "status": "pending" }`

---

### `get_ingestion_status`
Poll a long-running ingestion job.

**Input**: `workspace_id`, `job_id`

**Output**: `{ "status": "pending|processing|completed|failed", "chunks_done": N, "chunks_total": M }`

---

### `sync_from_source`
Pull and sync a copy-node from its original source workspace.

**Input**: `workspace_id`, `node_id`

---

### `transfer_authorship`
Transfer authorship of nodes to a new user.

**Input**: `workspace_id`, `node_ids: string[]`, `new_author_id`

---

### `resolve_conflict`
Resolve a contradiction conflict between two nodes.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | |
| `review_id` | string | ✅ | Conflict review item ID |
| `resolution` | string | ✅ | `"keep_a"` · `"keep_b"` · `"merge"` · `"both_valid"` |
| `merge_data` | object | | New node data when `resolution == "merge"` |

---

### `verify_audit`
Verify the integrity of the workspace audit trail hash chain.

**Input**: `workspace_id`

**Output**: `{ "valid": true|false, "checked": N, "first_broken_at": "..." }`

---

### `summarize_cluster`
Generate a hierarchical summary node for a group of nodes using AI.

**Input**: `workspace_id`, `node_ids: string[]`

---

### `complement_node_languages`
Auto-translate/complete missing ZH/EN content for a node.

**Input**: `workspace_id`, `node_id`

---

### `suggest_edges`
Find and propose missing `similar_to` edges based on semantic similarity.

**Input**: `workspace_id`, `threshold` (default: 0.85)

---

### `list_documents`
List uploaded documents in a workspace.

**Input**: `workspace_id`, `limit` (default: 20, max: 100), `offset`

---

### `get_document`
Get a document's metadata and linked nodes.

**Input**: `workspace_id`, `document_id`

---

### `get_node_sources`
Return source documents linked to a node.

**Input**: `workspace_id`, `node_id`

---

### `attach_url`
Register an external URL as a source document.

**Input**: `workspace_id`, `url` (required), `node_id` (optional), `title` (optional)

---

### `attach_evidence`
Attach a raw text evidence snippet to a node.

**Input**: `workspace_id`, `node_id`, `raw_text`, `source_url` (optional), `paragraph_ref` (optional)

---

### `upload_file`
Upload a file (base64-encoded, max 30 MB) as a source document.

**Input**: `workspace_id`, `filename`, `content_base64`, `mime_type` (optional), `node_id` (optional)

---

### `record_path`
Record an agent inquiry exploration path for later reuse.

**Input**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | string | ✅ | |
| `query_text` | string | ✅ | Initial search query |
| `node_sequence` | string[] | ✅ | Node IDs visited in order |
| `outcome` | string | ✅ | `"success"` · `"partial"` · `"failed"` · `"gap"` |
| `started_at` | string | ✅ | ISO datetime |
| `token_used` | integer | | Token count |
| `rating` | integer | | Usefulness rating |
| `metadata` | object | | Arbitrary metadata |

---

### `search_with_history`
Find similar past inquiry paths to replay successful trajectories.

**Input**: `workspace_id`, `query_text`, `similarity_threshold` (default: 0.85), `limit` (default: 3)

---

## Schemas

### Node Schema

```typescript
interface Node {
  id: string;                // "mem_..."
  workspace_id: string;
  title: string;
  content_type: ContentType;
  content_format: "plain" | "markdown";
  body: string;
  tags: string[];
  visibility: "public" | "team" | "private";
  author: string;            // user_id
  trust_score: number;       // 0.0–1.0 composite
  dim_accuracy: number;      // 0.0–1.0 accuracy dimension
  dim_freshness: number;     // 0.0–1.0 freshness dimension
  dim_utility: number;       // 0.0–1.0 utility dimension
  dim_author_rep: number;    // 0.0–1.0 author reputation dimension
  traversal_count: number;
  status: NodeStatus;
  source_type: "human" | "ai" | "document" | "mcp";
  created_at: string;        // ISO 8601
  updated_at: string;
}
```

### Content Types

| Value | Description |
|-------|-------------|
| `factual` | Concrete, verifiable information and definitions |
| `procedural` | Step-by-step instructions, guides, or workflows |
| `preference` | User preferences, style guides, or subjective choices |
| `context` | Background information necessary to understand other nodes |
| `inquiry` | Questions, issues, or gaps in knowledge that need answering |
| `document` | First-class document node — represents an uploaded file or URL (Phase 6.1) |
| `gap` | Knowledge gap node — auto-created when a search miss is detected (Phase 6.2) |

### Node Status

| Value | Description |
|-------|-------------|
| `active` | Normal state |
| `pending_review` | Awaiting human or AI review |
| `archived` | Soft-deleted |
| `gap` | Knowledge gap identified — inquiry node auto-created for a search miss |
| `conflicted` | Contradiction detected with another node |
| `answered` | Inquiry that has been resolved |
| `answered-low-trust` | Resolved inquiry with trust score below threshold |

### Relations

| Relation | Weight | Description |
|----------|--------|-------------|
| `depends_on` | 0.8 | Source requires target info to be complete/valid |
| `extends` | 0.7 | Source builds upon target |
| `related_to` | 0.5 | Generic semantic connection |
| `contradicts` | -1.0 | Source conflicts with target |
| `answered_by` | 1.0 | Inquiry answered by target node |
| `similar_to` | 0.4 | Similar topics or concepts |
| `queried_via_mcp` | 0.2 | Node was involved in an MCP query |
| `extracted_from` | 0.6 | Knowledge node was extracted from a document node (Phase 6.1) |
| `proceeds_to` | 0.9 | Conditional next step in a troubleshooting/workflow graph. Use `edge.metadata.condition` to specify when this path is taken (Phase 6.3) |

### Detail Levels

| Level | Contents |
|-------|----------|
| `full` | All fields including full body text |
| `brief` | Summary, top edges, no full body |
| `probe` | ID, title, tags, type only |

---

## Error Codes

| Code | Meaning |
|------|---------|
| `-32601` | Method not found |
| `-32602` | Invalid params |
| `401` | Unauthorized |
| `403` | Forbidden (insufficient workspace role) |
| `404` | Resource not found |
| `429` | Rate limited |

---

## Example Session

```python
# 1. Create a node
resp = mcp.call("create_node", {
    "workspace_id": "ws_abc123",
    "title": "Python async/await basics",
    "content_type": "procedural",
    "body": "Use `async def` to declare coroutines...",
    "tags": ["python", "async"]
})
node_id = resp["id"]

# 2. Wait for embedding (optional, needed for semantic search)
mcp.call("wait_for_embedding", {
    "workspace_id": "ws_abc123",
    "node_id": node_id
})

# 3. Semantic search
results = mcp.call("search_nodes", {
    "workspace_id": "ws_abc123",
    "query": "how to write async python",
    "limit": 5
})

# 4. Traverse neighbors
neighborhood = mcp.call("traverse", {
    "workspace_id": "ws_abc123",
    "node_id": node_id,
    "depth": 2
})
```

---

## Token Budget

The `detail_level` and `max_response_tokens` parameters allow agents to control response size:

- **Default**: `"brief"` for most agents
- **Large model**: `"full"` (more detail)
- **Small model**: `"probe"` (minimal)

If the response exceeds `max_response_tokens`, the server automatically degrades to a lower detail level. Truncated responses include `"truncated": true` and `"original_size"` tokens.

---

## Rate Limits

- **Per user per minute**: 120 requests
- **Burst**: 30 requests
- Exceeding limits returns HTTP 429 with a `Retry-After` header.

---

## MCP Client Configuration

For Claude Desktop or other MCP-compatible clients:

```json
{
  "mcpServers": {
    "memtrace": {
      "command": "npx",
      "args": ["-y", "@memtrace/mcp-client"],
      "env": {
        "MEMTRACE_API_URL": "https://your-instance.example.com",
        "MEMTRACE_API_TOKEN": "<your-personal-api-key>"
      }
    }
  }
}
```

Alternatively, use HTTP transport directly:

```json
{
  "mcpServers": {
    "memtrace": {
      "url": "https://your-instance.example.com/mcp",
      "headers": {
        "Authorization": "Bearer <your-personal-api-key>"
      }
    }
  }
}
```
