from __future__ import annotations

import logging
from typing import Any, Iterable, List, Optional, Tuple, Type

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from memtrace import MemTraceClient

logger = logging.getLogger(__name__)

class MemTraceVectorStore(VectorStore):
    """
    MemTrace knowledge graph vector store.
    
    All embedding and retrieval operations are performed on the server-side,
    meaning client-side embedding computation is bypassed.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        workspace_id: str,
        client: Optional[MemTraceClient] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.workspace_id = workspace_id
        
        self.client = client or MemTraceClient(
            base_url=self.base_url,
            api_key=self.api_key
        )

    @property
    def embeddings(self) -> Optional[Embeddings]:
        # Embeddings are handled entirely server-side
        return None

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        Upload texts and store them as memory nodes in the workspace.
        """
        ids = []
        metadatas = metadatas or [None] * len(list(texts))
        
        for text, metadata in zip(texts, metadatas):
            meta = metadata or {}
            title = meta.get("title") or (text[:40] + ("..." if len(text) > 40 else ""))
            content_type = meta.get("content_type") or "factual"
            tags = meta.get("tags") or []
            visibility = meta.get("visibility") or "private"
            
            # Extract additional creation args
            extra_args = {k: v for k, v in meta.items() if k not in ("title", "content_type", "tags", "visibility")}
            
            node = self.client.create_node(
                workspace_id=self.workspace_id,
                title=title,
                content_type=content_type,
                body=text,
                tags=tags,
                visibility=visibility,
                **extra_args
            )
            ids.append(node.id)
            
        return ids

    async def aadd_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        Asynchronously upload texts and store them as memory nodes.
        """
        ids = []
        metadatas = metadatas or [None] * len(list(texts))
        
        for text, metadata in zip(texts, metadatas):
            meta = metadata or {}
            title = meta.get("title") or (text[:40] + ("..." if len(text) > 40 else ""))
            content_type = meta.get("content_type") or "factual"
            tags = meta.get("tags") or []
            visibility = meta.get("visibility") or "private"
            
            # Extract additional creation args
            extra_args = {k: v for k, v in meta.items() if k not in ("title", "content_type", "tags", "visibility")}
            
            node = await self.client.acreate_node(
                workspace_id=self.workspace_id,
                title=title,
                content_type=content_type,
                body=text,
                tags=tags,
                visibility=visibility,
                **extra_args
            )
            ids.append(node.id)
            
        return ids

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

    def similarity_search(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> List[Document]:
        """
        Perform a semantic/vector search over the memory nodes.
        """
        nodes = self.client.search_semantic(
            workspace_id=self.workspace_id,
            query=query,
            limit=k
        )
        return [self._node_to_document(node) for node in nodes]

    async def asimilarity_search(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> List[Document]:
        """
        Asynchronously perform a semantic/vector search over the memory nodes.
        """
        nodes = await self.client.asearch_semantic(
            workspace_id=self.workspace_id,
            query=query,
            limit=k
        )
        return [self._node_to_document(node) for node in nodes]

    def similarity_search_with_score(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> List[Tuple[Document, float]]:
        """
        Perform a semantic search and return documents with relevance scores.
        """
        docs = self.similarity_search(query, k=k, **kwargs)
        # Score is returned as 1.0 since precise similarity metric is stripped by API serialization
        return [(doc, 1.0) for doc in docs]

    def delete(self, ids: Optional[List[str]] = None, **kwargs: Any) -> Optional[bool]:
        """
        Archive memory nodes by their IDs.
        """
        if not ids:
            return False
            
        for node_id in ids:
            try:
                self.client.delete_node(workspace_id=self.workspace_id, node_id=node_id)
            except Exception as e:
                logger.error(f"Failed to delete node {node_id}: {e}")
                
        return True

    async def adelete(self, ids: Optional[List[str]] = None, **kwargs: Any) -> Optional[bool]:
        """
        Asynchronously archive memory nodes by their IDs.
        """
        if not ids:
            return False
            
        for node_id in ids:
            try:
                await self.client.adelete_node(workspace_id=self.workspace_id, node_id=node_id)
            except Exception as e:
                logger.error(f"Failed to delete node {node_id}: {e}")
                
        return True

    @classmethod
    def from_texts(
        cls: Type[MemTraceVectorStore],
        texts: List[str],
        embedding: Optional[Embeddings] = None,
        metadatas: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> MemTraceVectorStore:
        """
        Construct a MemTraceVectorStore from texts.
        """
        base_url = kwargs.pop("base_url")
        api_key = kwargs.pop("api_key")
        workspace_id = kwargs.pop("workspace_id")
        
        store = cls(
            base_url=base_url,
            api_key=api_key,
            workspace_id=workspace_id,
            **kwargs
        )
        store.add_texts(texts, metadatas=metadatas)
        return store

    @classmethod
    async def afrom_texts(
        cls: Type[MemTraceVectorStore],
        texts: List[str],
        embedding: Optional[Embeddings] = None,
        metadatas: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> MemTraceVectorStore:
        """
        Asynchronously construct a MemTraceVectorStore from texts.
        """
        base_url = kwargs.pop("base_url")
        api_key = kwargs.pop("api_key")
        workspace_id = kwargs.pop("workspace_id")
        
        store = cls(
            base_url=base_url,
            api_key=api_key,
            workspace_id=workspace_id,
            **kwargs
        )
        await store.aadd_texts(texts, metadatas=metadatas)
        return store
