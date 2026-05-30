import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from langchain_memtrace import MemTraceVectorStore
from memtrace.models import Node

def test_memtrace_vectorstore_sync():
    mock_node = Node(
        id="mem_1",
        workspace_id="ws_abc",
        title="Test Vector Store",
        content_type="factual",
        content_format="plain",
        body="This is a body.",
        tags=["test"],
        visibility="private",
        author="admin",
        trust_score=0.8
    )

    with patch("langchain_memtrace.vectorstore.MemTraceClient") as MockClient:
        mock_client_instance = MockClient.return_value
        mock_client_instance.create_node.return_value = mock_node
        mock_client_instance.search_semantic.return_value = [mock_node]
        mock_client_instance.delete_node.return_value = {"status": "archived"}

        store = MemTraceVectorStore(
            base_url="http://localhost:8000",
            api_key="mt_mock",
            workspace_id="ws_abc"
        )

        # 1. Test add_texts
        ids = store.add_texts(["This is a body."], metadatas=[{"title": "Test Vector Store"}])
        assert ids == ["mem_1"]
        mock_client_instance.create_node.assert_called_once_with(
            workspace_id="ws_abc",
            title="Test Vector Store",
            content_type="factual",
            body="This is a body.",
            tags=[],
            visibility="private"
        )

        # 2. Test similarity_search
        docs = store.similarity_search("query")
        assert len(docs) == 1
        assert docs[0].page_content == "This is a body."
        assert docs[0].metadata["id"] == "mem_1"

        # 3. Test delete
        success = store.delete(["mem_1"])
        assert success is True
        mock_client_instance.delete_node.assert_called_once_with(
            workspace_id="ws_abc",
            node_id="mem_1"
        )

@pytest.mark.asyncio
async def test_memtrace_vectorstore_async():
    mock_node = Node(
        id="mem_1",
        workspace_id="ws_abc",
        title="Test Vector Store Async",
        content_type="factual",
        content_format="plain",
        body="This is async body.",
        tags=[],
        visibility="private",
        author="admin",
        trust_score=0.8
    )

    with patch("langchain_memtrace.vectorstore.MemTraceClient") as MockClient:
        mock_client_instance = MockClient.return_value
        mock_client_instance.acreate_node = AsyncMock(return_value=mock_node)
        mock_client_instance.asearch_semantic = AsyncMock(return_value=[mock_node])
        mock_client_instance.adelete_node = AsyncMock(return_value={"status": "archived"})

        store = MemTraceVectorStore(
            base_url="http://localhost:8000",
            api_key="mt_mock",
            workspace_id="ws_abc"
        )

        # 1. Test aadd_texts
        ids = await store.aadd_texts(["This is async body."], metadatas=[{"title": "Test Vector Store Async"}])
        assert ids == ["mem_1"]
        mock_client_instance.acreate_node.assert_called_once_with(
            workspace_id="ws_abc",
            title="Test Vector Store Async",
            content_type="factual",
            body="This is async body.",
            tags=[],
            visibility="private"
        )

        # 2. Test asimilarity_search
        docs = await store.asimilarity_search("query")
        assert len(docs) == 1
        assert docs[0].page_content == "This is async body."

        # 3. Test adelete
        success = await store.adelete(["mem_1"])
        assert success is True
        mock_client_instance.adelete_node.assert_called_once_with(
            workspace_id="ws_abc",
            node_id="mem_1"
        )
