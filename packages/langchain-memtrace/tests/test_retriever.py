import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from langchain_memtrace import MemTraceRetriever
from memtrace.models import Node

def test_memtrace_retriever_sync():
    # Setup mock nodes from SDK client
    mock_node = Node(
        id="mem_123",
        workspace_id="ws_abc",
        title="Test Retriever Node",
        content_type="factual",
        content_format="plain",
        body="This is a test document content.",
        tags=["test"],
        visibility="public",
        author="admin",
        trust_score=0.9
    )
    
    with patch("langchain_memtrace.retriever.MemTraceClient") as MockClient:
        # Configure client search mocks
        mock_client_instance = MockClient.return_value
        mock_client_instance.search_nodes.return_value = [mock_node]
        mock_client_instance.search_semantic.return_value = [mock_node]
        
        # Instantiate retriever
        retriever = MemTraceRetriever(
            base_url="http://localhost:8000",
            api_key="mt_mock",
            workspace_id="ws_abc",
            search_type="hybrid",
            k=5
        )
        
        # Get relevant documents
        docs = retriever.invoke("test query")
        assert len(docs) == 1
        assert docs[0].page_content == "This is a test document content."
        assert docs[0].metadata["id"] == "mem_123"
        assert docs[0].metadata["title"] == "Test Retriever Node"
        assert docs[0].metadata["tags"] == ["test"]
        assert docs[0].metadata["trust_score"] == 0.9
        
        # Verify correct SDK method was called
        mock_client_instance.search_nodes.assert_called_once_with(
            workspace_id="ws_abc",
            query="test query",
            limit=5
        )

@pytest.mark.asyncio
async def test_memtrace_retriever_async():
    mock_node = Node(
        id="mem_123",
        workspace_id="ws_abc",
        title="Test Retriever Node",
        content_type="factual",
        content_format="plain",
        body="This is a test document content.",
        tags=["test"],
        visibility="public",
        author="admin",
        trust_score=0.9
    )
    
    with patch("langchain_memtrace.retriever.MemTraceClient") as MockClient:
        mock_client_instance = MockClient.return_value
        mock_client_instance.asearch_nodes = AsyncMock(return_value=[mock_node])
        mock_client_instance.asearch_semantic = AsyncMock(return_value=[mock_node])
        
        retriever = MemTraceRetriever(
            base_url="http://localhost:8000",
            api_key="mt_mock",
            workspace_id="ws_abc",
            search_type="semantic",
            k=3
        )
        
        # Test ainvoke (async retrieval)
        docs = await retriever.ainvoke("test query async")
        assert len(docs) == 1
        assert docs[0].page_content == "This is a test document content."
        
        # Verify correct SDK semantic method was called
        mock_client_instance.asearch_semantic.assert_called_once_with(
            workspace_id="ws_abc",
            query="test query async",
            limit=3
        )
