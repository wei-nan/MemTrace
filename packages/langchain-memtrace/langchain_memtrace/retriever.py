from typing import List, Optional, Literal
from langchain_core.callbacks import CallbackManagerForRetrieverRun, AsyncCallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field, PrivateAttr

from memtrace import MemTraceClient

class MemTraceRetriever(BaseRetriever):
    """
    MemTrace knowledge graph memory network retriever compatible with LangChain.
    """

    base_url: str = Field(description="The base URL of the MemTrace API server.")
    api_key: str = Field(description="The API key (Bearer mt_...) for authentication.")
    workspace_id: str = Field(description="The workspace ID to query.")
    search_type: Literal["hybrid", "text", "semantic"] = Field(
        default="hybrid",
        description="The search strategy to employ: 'hybrid', 'text' or 'semantic'."
    )
    k: int = Field(default=5, description="The maximum number of documents to retrieve.")

    _client: MemTraceClient = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._client = MemTraceClient(
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

    def _get_relevant_documents(
        self, query: str, *, run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[Document]:
        """
        Synchronous retrieval implementation.
        """
        if self.search_type == "semantic":
            nodes = self._client.search_semantic(workspace_id=self.workspace_id, query=query, limit=self.k)
        else:
            # "hybrid" and "text" both fallback to general nodes-search
            nodes = self._client.search_nodes(workspace_id=self.workspace_id, query=query, limit=self.k)

        return [self._node_to_document(node) for node in nodes]

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: Optional[AsyncCallbackManagerForRetrieverRun] = None
    ) -> List[Document]:
        """
        Asynchronous retrieval implementation.
        """
        if self.search_type == "semantic":
            nodes = await self._client.asearch_semantic(workspace_id=self.workspace_id, query=query, limit=self.k)
        else:
            # "hybrid" and "text" both fallback to general nodes-search
            nodes = await self._client.asearch_nodes(workspace_id=self.workspace_id, query=query, limit=self.k)

        return [self._node_to_document(node) for node in nodes]
