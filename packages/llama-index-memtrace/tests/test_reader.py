import pytest
from unittest.mock import MagicMock, patch
from llama_index_memtrace import MemTraceReader
from memtrace.models import Node

def test_memtrace_reader():
    mock_node = Node(
        id="mem_123",
        workspace_id="ws_abc",
        title="Test Node",
        content_type="factual",
        content_format="plain",
        body="Body of test node.",
        tags=["test"],
        visibility="private",
        author="admin",
        trust_score=0.8
    )

    with patch("llama_index_memtrace.reader.MemTraceClient") as MockClient:
        mock_client_instance = MockClient.return_value
        mock_client_instance.list_nodes.return_value = [mock_node]

        reader = MemTraceReader(
            base_url="http://localhost:8000",
            api_key="mt_mock"
        )

        documents = reader.load_data(
            workspace_id="ws_abc",
            tag="test",
            content_type="factual",
            limit=50
        )

        assert len(documents) == 1
        assert documents[0].get_content() == "Body of test node."
        assert documents[0].node_id == "mem_123"
        assert documents[0].metadata["title"] == "Test Node"
        assert documents[0].metadata["tags"] == ["test"]
        assert documents[0].metadata["content_type"] == "factual"

        mock_client_instance.list_nodes.assert_called_once_with(
            workspace_id="ws_abc",
            tag="test",
            content_type="factual",
            limit=50,
            status="active"
        )
