# MemTrace Python SDK

Official Python SDK for interacting with the MemTrace API.

## Installation

```bash
pip install -e packages/sdk-python
```

## Quick Start

```python
from memtrace import MemTraceClient

client = MemTraceClient(
    base_url="http://localhost:8000",
    api_key="mt_your_api_key_here"
)

# List available workspaces
workspaces = client.list_workspaces()
for ws in workspaces:
    print(ws.id, ws.name)

# Search nodes in a workspace
nodes = client.search_nodes(workspace_id="ws_abc", query="how to configure auth")
for node in nodes:
    print(node.title, node.body)
```
