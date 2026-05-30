from __future__ import annotations

from typing import Iterator, List, Optional

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

from memtrace import MemTraceClient

class MemTraceDocumentLoader(BaseLoader):
    """
    Load all memory nodes from a MemTrace workspace as LangChain Documents.
    
    Supports pagination and tags/content_type filtering.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        workspace_id: str,
        tag: Optional[str] = None,
        content_type: Optional[str] = None,
        chunk_size: int = 100,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.tag = tag
        self.content_type = content_type
        self.chunk_size = chunk_size
        
        self.client = MemTraceClient(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def _node_to_document(self, node) -> Document:
        metadata = {
            "id": node.id,
            "title": node.title,
            "content_type": node.content_type,
            "tags": node.tags,
            "trust_score": node.trust_score,
            "workspace_id": node.workspace_id,
            "author": node.author,
            "status": node.status
        }
        return Document(
            page_content=node.body or "",
            metadata=metadata
        )

    def lazy_load(self) -> Iterator[Document]:
        """
        Yield document nodes using pagination to keep memory usage low.
        """
        offset = 0
        while True:
            nodes = self.client.list_nodes(
                workspace_id=self.workspace_id,
                tag=self.tag,
                content_type=self.content_type,
                limit=self.chunk_size,
                offset=offset,
                status="active"
            )
            
            if not nodes:
                break
                
            for node in nodes:
                yield self._node_to_document(node)
                
            if len(nodes) < self.chunk_size:
                break
                
            offset += len(nodes)

    def load(self) -> List[Document]:
        """
        Load all documents in the workspace into memory.
        """
        return list(self.lazy_load())
