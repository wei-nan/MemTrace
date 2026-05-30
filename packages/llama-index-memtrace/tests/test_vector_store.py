import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from llama_index_memtrace import MemTraceVectorStore
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores.types import VectorStoreQuery
from memtrace.models import Node

def test_llama_index_vector_store_sync():
    mock_node = Node(
        id="mem_123",
        workspace_id="ws_abc",
        title="Test Vector Store",
        content_type="factual",
        content_format="plain",
        body="Body of test.",
        tags=["test"],
        visibility="private",
        author="admin",
        trust_score=0.8
    )

    with patch("llama_index_memtrace.vector_store.MemTraceClient") as MockClient:
        mock_client_instance = MockClient.return_value
        mock_client_instance.create_node.return_value = mock_node
        mock_client_instance.search_semantic.return_value = [mock_node]
        mock_client_instance.delete_node.return_value = {"status": "archived"}

        store = MemTraceVectorStore(
            base_url="http://localhost:8000",
            api_key="mt_mock",
            workspace_id="ws_abc"
        )

        # 1. Test add
        llama_node = TextNode(text="Body of test.", metadata={"title": "Test Vector Store"})
        ids = store.add([llama_node])
        assert ids == ["mem_123"]
        mock_client_instance.create_node.assert_called_once_with(
            workspace_id="ws_abc",
            title="Test Vector Store",
            content_type="factual",
            body="Body of test.",
            tags=[],
            visibility="private"
        )

        # 2. Test query
        query = VectorStoreQuery(query_str="test query", similarity_top_k=2)
        result = store.query(query)
        assert len(result.nodes) == 1
        assert result.nodes[0].get_content() == "Body of test."
        assert result.nodes[0].node_id == "mem_123"
        assert result.ids == ["mem_123"]
        mock_client_instance.search_semantic.assert_called_once_with(
            workspace_id="ws_abc",
            query="test query",
            limit=2
        )

        # 3. Test delete
        store.delete("mem_123")
        mock_client_instance.delete_node.assert_called_once_with(
            workspace_id="ws_abc",
            node_id="mem_123"
        )

@pytest.mark.asyncio
async def test_llama_index_vector_store_async():
    mock_node = Node(
        id="mem_123",
        workspace_id="ws_abc",
        title="Test Vector Store Async",
        content_type="factual",
        content_format="plain",
        body="Body of async test.",
        tags=[],
        visibility="private",
        author="admin",
        trust_score=0.8
    )

    with patch("llama_index_memtrace.vector_store.MemTraceClient") as MockClient:
        mock_client_instance = MockClient.return_value
        mock_client_instance.acreate_node = AsyncMock(return_value=mock_node)
        mock_client_instance.asearch_semantic = AsyncMock(return_value=[mock_node])
        mock_client_instance.adelete_node = AsyncMock(return_value={"status": "archived"})

        store = MemTraceVectorStore(
            base_url="http://localhost:8000",
            api_key="mt_mock",
            workspace_id="ws_abc"
        )

        # 1. Test aadd
        llama_node = TextNode(text="Body of async test.", metadata={"title": "Test Vector Store Async"})
        ids = await store.aadd([llama_node])
        assert ids == ["mem_123"]

        # 2. Test aquery
        query = VectorStoreQuery(query_str="async query", similarity_top_k=3)
        result = await store.aquery(query)
        assert len(result.nodes) == 1
        assert result.nodes[0].get_content() == "Body of async test."
        assert result.nodes[0].node_id == "mem_123"

        # 3. Test adelete
        await store.adelete("mem_123")
        mock_client_instance.adelete_node.assert_called_once_with(
            workspace_id="ws_abc",
            node_id="mem_123"
        )
