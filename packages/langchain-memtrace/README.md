# LangChain MemTrace Integration

LangChain integration package for MemTrace, providing a retriever that can be easily plugged into LangChain Expression Language (LCEL) chains.

## Installation

```bash
pip install -e packages/langchain-memtrace
```

## Usage

```python
from langchain_memtrace import MemTraceRetriever

retriever = MemTraceRetriever(
    base_url="http://localhost:8000",
    api_key="mt_your_api_key_here",
    workspace_id="ws_abc",
    k=5
)

# Invoke the retriever
docs = retriever.invoke("how to configure auth")
for doc in docs:
    print(doc.page_content)
    print(doc.metadata)
```
