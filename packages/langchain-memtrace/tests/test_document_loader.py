import pytest
from unittest.mock import MagicMock, patch
from langchain_memtrace import MemTraceDocumentLoader
from memtrace.models import Node

def test_memtrace_document_loader():
    mock_node_1 = Node(
        id="mem_1",
        workspace_id="ws_abc",
        title="Node 1",
        content_type="factual",
        content_format="plain",
        body="Content 1",
        tags=["tag1"],
        visibility="private",
        author="admin",
        trust_score=0.8
    )
    mock_node_2 = Node(
        id="mem_2",
        workspace_id="ws_abc",
        title="Node 2",
        content_type="procedural",
        content_format="plain",
        body="Content 2",
        tags=["tag2"],
        visibility="private",
        author="admin",
        trust_score=0.9
    )

    with patch("langchain_memtrace.document_loader.MemTraceClient") as MockClient:
        mock_client_instance = MockClient.return_value
        
        # Paginated mock responses: 
        # First call returns 2 nodes. Second call (offset 2) returns empty list to stop loader.
        mock_client_instance.list_nodes.side_effect = [
            [mock_node_1, mock_node_2],
            []
        ]

        loader = MemTraceDocumentLoader(
            base_url="http://localhost:8000",
            api_key="mt_mock",
            workspace_id="ws_abc",
            tag="tag1",
            content_type="factual",
            chunk_size=2
        )

        # 1. Test load
        docs = loader.load()
        assert len(docs) == 2
        assert docs[0].page_content == "Content 1"
        assert docs[0].metadata["id"] == "mem_1"
        assert docs[0].metadata["tags"] == ["tag1"]
        assert docs[1].page_content == "Content 2"
        assert docs[1].metadata["id"] == "mem_2"

        # Verify SDK client calls
        calls = mock_client_instance.list_nodes.call_args_list
        assert len(calls) == 2
        
        # Verify first call parameters
        first_call_args = calls[0][1]
        assert first_call_args["workspace_id"] == "ws_abc"
        assert first_call_args["tag"] == "tag1"
        assert first_call_args["content_type"] == "factual"
        assert first_call_args["limit"] == 2
        assert first_call_args["offset"] == 0

        # Verify second call parameters (pagination offset)
        second_call_args = calls[1][1]
        assert second_call_args["offset"] == 2
