# MemTrace MCP Server

MemTrace knowledge graph as a [Model Context Protocol](https://modelcontextprotocol.io) server. Lets AI agents (Claude, etc.) query and write to knowledge bases without reading raw spec documents.

## Quick Start

### stdio (local dev, Claude Desktop)

```json
// .mcp.json
{
  "mcpServers": {
    "memtrace": {
      "command": "node",
      "args": ["packages/mcp/dist/index.js"],
      "env": {
        "MEMTRACE_API": "http://localhost:8000/api/v1",
        "MEMTRACE_WS": "ws_your_workspace_id",
        "MEMTRACE_TOKEN": "mt_live_...",
        "MEMTRACE_LANG": "zh-TW"
      }
    }
  }
}
```

### HTTP + SSE (remote agents, production)

```bash
MCP_TRANSPORT=sse MEMTRACE_API=http://api:8000/api/v1 MEMTRACE_TOKEN=mt_live_... node dist/index.js
```

Exposes `GET /sse` (SSE connection) and `POST /messages` (MCP messages) on port `MCP_PORT` (default 3001).

Via Docker Compose: `docker compose up mcp`

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEMTRACE_API` | yes | `http://localhost:8000/api/v1` | API base URL |
| `MEMTRACE_TOKEN` | yes (write) | — | Bearer token for auth. Read-only tools work without it but write tools will fail |
| `MEMTRACE_WS` | no | `ws_spec0001` | Default workspace ID |
| `MEMTRACE_LANG` | no | `zh-TW` | Display language (`zh-TW` or `en`) |
| `MCP_TRANSPORT` | no | `stdio` | `stdio` or `sse` |
| `MCP_PORT` | no | `3001` | HTTP port (SSE mode only) |
| `MEMTRACE_INTERNAL_TOKEN` | no | — | Internal service token for logging |

## Multi-Workspace

All query tools accept an optional `workspace_id` parameter. Omit it to use `MEMTRACE_WS`.

```
// Query the default workspace
search_nodes({ query: "decay algorithm" })

// Query a specific workspace
search_nodes({ query: "onboarding flow", workspace_id: "ws_product_abc" })

// List all accessible workspaces
list_workspaces()
```

Single server instance, multiple KBs — no need to start one process per workspace.

## Available Tools

### Read tools

| Tool | Description |
|------|-------------|
| `search_nodes` | Keyword search across nodes |
| `get_node` | Fetch a single node by ID |
| `traverse` | Walk a node's direct associations (depth 1 or 2) |
| `list_by_tag` | List all nodes with a specific tag |
| `list_workspaces` | List accessible workspaces |
| `get_schema` | Node/edge field reference |

### Write tools (require `MEMTRACE_TOKEN`)

| Tool | Description |
|------|-------------|
| `create_node` | Propose a new node (enters review queue) |
| `update_node` | Propose edits to an existing node |
| `delete_node` | Propose deletion of a node |
| `create_edge` | Create a relationship between two nodes |
| `traverse_edge` | Record edge traversal, triggers co-access boost |
| `confirm_node_validity` | Mark a node as manually verified |
| `list_review_queue` | List pending AI proposals |

### Resources

Nodes are also exposed as MCP Resources with URI `memtrace://node/{node_id}`, readable via `resources/read`.

## Agent Best Practices

1. **Always call `get_schema` first** if unsure about field names or valid values.
2. **Check for duplicates** with `search_nodes` before creating new nodes.
3. **Call `traverse_edge`** after following a reasoning path — this feeds the co-access boost mechanism and improves edge weights over time.
4. **Call `confirm_node_validity`** after using a node to assert its content is still accurate.
5. **Use `list_workspaces`** to discover available KBs rather than hardcoding IDs.
