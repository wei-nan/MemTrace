# LlamaIndex MemTrace Integration

LlamaIndex integration package for MemTrace, providing a vector store and reader to easily connect your knowledge graph as a data source or index.

## Installation

```bash
pip install -e packages/llama-index-memtrace
```

## Usage

```python
from llama_index_memtrace import MemTraceVectorStore

vector_store = MemTraceVectorStore(
    base_url="http://localhost:8000",
    api_key="mt_your_api_key_here",
    workspace_id="ws_abc"
)
```
