from __future__ import annotations

import logging
from typing import Any, List, Optional

from llama_index.core.vector_stores.types import (
    BasePydanticVectorStore,
    VectorStoreQuery,
    VectorStoreQueryResult,
)
from llama_index.core.schema import BaseNode, TextNode
from pydantic.v1 import PrivateAttr, Field

from memtrace import MemTraceClient

logger = logging.getLogger(__name__)

class MemTraceVectorStore(BasePydanticVectorStore):
    """
    MemTrace knowledge graph vector store for LlamaIndex.
    
    Delegates all semantic search and creation embedding calculations to the MemTrace API.
    """

    base_url: str = Field(description="The base URL of the MemTrace API server.")
    api_key: str = Field(description="The API key for authentication.")
    workspace_id: str = Field(description="The workspace ID to index/query.")
    stores_text: bool = Field(default=True, description="Whether the vector store stores text.")
    is_embedding_query: bool = Field(default=False, description="Whether query embedding is run on the client side.")

    _client: MemTraceClient = PrivateAttr()

    def __init__(
        self,
        base_url: str,
        api_key: str,
        workspace_id: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            workspace_id=workspace_id,
            **kwargs,
        )
        self._client = MemTraceClient(
            base_url=self.base_url,
            api_key=self.api_key
        )

    @property
    def client(self) -> Any:
        """Get client."""
        return self._client

    def add(self, nodes: List[BaseNode], **add_kwargs: Any) -> List[str]:
        """
        Add nodes to the vector store.
        """
        ids = []
        for node in nodes:
            metadata = node.metadata or {}
            body = node.get_content()
            title = metadata.get("title") or (body[:40] + ("..." if len(body) > 40 else ""))
            content_type = metadata.get("content_type") or "factual"
            tags = metadata.get("tags") or []
            visibility = metadata.get("visibility") or "private"

            extra_args = {k: v for k, v in metadata.items() if k not in ("title", "content_type", "tags", "visibility")}

            created_node = self._client.create_node(
                workspace_id=self.workspace_id,
                title=title,
                content_type=content_type,
                body=body,
                tags=tags,
                visibility=visibility,
                **extra_args
            )
            ids.append(created_node.id)
        return ids

    async def aadd(self, nodes: List[BaseNode], **add_kwargs: Any) -> List[str]:
        """
        Asynchronously add nodes to the vector store.
        """
        ids = []
        for node in nodes:
            metadata = node.metadata or {}
            body = node.get_content()
            title = metadata.get("title") or (body[:40] + ("..." if len(body) > 40 else ""))
            content_type = metadata.get("content_type") or "factual"
            tags = metadata.get("tags") or []
            visibility = metadata.get("visibility") or "private"

            extra_args = {k: v for k, v in metadata.items() if k not in ("title", "content_type", "tags", "visibility")}

            created_node = await self._client.acreate_node(
                workspace_id=self.workspace_id,
                title=title,
                content_type=content_type,
                body=body,
                tags=tags,
                visibility=visibility,
                **extra_args
            )
            ids.append(created_node.id)
        return ids

    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        """
        Archive a node by its ID.
        """
        try:
            self._client.delete_node(workspace_id=self.workspace_id, node_id=ref_doc_id)
        except Exception as e:
            logger.error(f"Failed to delete node {ref_doc_id}: {e}")

    async def adelete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        """
        Asynchronously archive a node by its ID.
        """
        try:
            await self._client.adelete_node(workspace_id=self.workspace_id, node_id=ref_doc_id)
        except Exception as e:
            logger.error(f"Failed to delete node {ref_doc_id}: {e}")

    def _to_llama_node(self, node) -> TextNode:
        return TextNode(
            text=node.body or "",
            id_=node.id,
            metadata={
                "title": node.title,
                "content_type": node.content_type,
                "tags": node.tags,
                "trust_score": node.trust_score,
                "author": node.author,
                "status": node.status
            }
        )

    def query(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        """
        Query vector store.
        """
        if not query.query_str:
            raise ValueError("Query string must be provided.")

        limit = query.similarity_top_k or 4
        nodes = self._client.search_semantic(
            workspace_id=self.workspace_id,
            query=query.query_str,
            limit=limit
        )

        llama_nodes = [self._to_llama_node(node) for node in nodes]
        return VectorStoreQueryResult(
            nodes=llama_nodes,
            similarities=[1.0] * len(llama_nodes),
            ids=[n.id_ for n in llama_nodes]
        )

    async def aquery(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        """
        Asynchronously query vector store.
        """
        if not query.query_str:
            raise ValueError("Query string must be provided.")

        limit = query.similarity_top_k or 4
        nodes = await self._client.asearch_semantic(
            workspace_id=self.workspace_id,
            query=query.query_str,
            limit=limit
        )

        llama_nodes = [self._to_llama_node(node) for node in nodes]
        return VectorStoreQueryResult(
            nodes=llama_nodes,
            similarities=[1.0] * len(llama_nodes),
            ids=[n.id_ for n in llama_nodes]
        )
