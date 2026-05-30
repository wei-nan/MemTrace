from __future__ import annotations

from typing import Any, List, Optional

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document

from memtrace import MemTraceClient

class MemTraceReader(BaseReader):
    """
    MemTrace workspace reader for LlamaIndex.
    
    Loads active memory nodes in a workspace as LlamaIndex Documents.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = MemTraceClient(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def load_data(
        self,
        workspace_id: str,
        tag: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> List[Document]:
        """
        Load active memory nodes from a workspace as Documents.
        """
        nodes = self._client.list_nodes(
            workspace_id=workspace_id,
            tag=tag,
            content_type=content_type,
            limit=limit,
            status="active"
        )

        documents = []
        for node in nodes:
            doc = Document(
                text=node.body or "",
                id_=node.id,
                metadata={
                    "title": node.title,
                    "content_type": node.content_type,
                    "tags": node.tags,
                    "trust_score": node.trust_score,
                    "author": node.author,
                    "status": node.status,
                    "workspace_id": node.workspace_id
                }
            )
            documents.append(doc)
        return documents
