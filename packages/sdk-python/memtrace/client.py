import httpx
import json
from typing import List, Dict, Any, Optional, Generator, AsyncGenerator
from .exceptions import APIError, AuthenticationError, NotFoundError
from .models import Workspace, Node, Edge

class MemTraceClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        if response.is_success:
            return response
        
        status_code = response.status_code
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text

        if status_code == 401:
            raise AuthenticationError(f"Authentication failed: {detail}")
        elif status_code == 404:
            raise NotFoundError(f"Resource not found: {detail}")
        else:
            raise APIError(f"API returned error {status_code}", status_code, response.text)

    # --- Sync API ---

    def list_workspaces(self) -> List[Workspace]:
        url = f"{self.base_url}/api/v1/workspaces"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self.headers)
            self._handle_response(resp)
            return [Workspace(**ws) for ws in resp.json()]

    def get_workspace(self, workspace_id: str) -> Workspace:
        url = f"{self.base_url}/api/v1/workspaces/{workspace_id}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self.headers)
            self._handle_response(resp)
            return Workspace(**resp.json())

    def search_nodes(self, workspace_id: str, query: str, limit: int = 20) -> List[Node]:
        url = f"{self.base_url}/api/v1/workspaces/{workspace_id}/nodes-search"
        params = {"query": query, "limit": limit}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self.headers, params=params)
            self._handle_response(resp)
            return [Node(**node) for node in resp.json()]

    def search_semantic(self, workspace_id: str, query: str, limit: int = 20) -> List[Node]:
        url = f"{self.base_url}/api/v1/workspaces/{workspace_id}/nodes/search-semantic"
        payload = {"query": query, "limit": limit}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=self.headers, json=payload)
            self._handle_response(resp)
            return [Node(**node) for node in resp.json()]

    def get_node(self, workspace_id: str, node_id: str) -> Node:
        url = f"{self.base_url}/api/v1/workspaces/{workspace_id}/nodes/{node_id}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self.headers)
            self._handle_response(resp)
            return Node(**resp.json())

    def create_node(self, workspace_id: str, title: str, content_type: str, body: str = "", tags: Optional[List[str]] = None, visibility: str = "private", **kwargs) -> Node:
        url = f"{self.base_url}/api/v1/workspaces/{workspace_id}/nodes"
        payload = {
            "title": title,
            "content_type": content_type,
            "body": body,
            "tags": tags or [],
            "visibility": visibility,
            **kwargs
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=self.headers, json=payload)
            self._handle_response(resp)
            return Node(**resp.json())

    def chat(self, workspace_id: str, message: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/ai/chat"
        payload = {
            "workspace_id": workspace_id,
            "message": message,
            "history": history or [],
            **kwargs
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=self.headers, json=payload)
            self._handle_response(resp)
            return resp.json()

    def chat_stream(self, workspace_id: str, message: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Generator[Dict[str, Any], None, None]:
        url = f"{self.base_url}/api/v1/ai/chat-stream"
        payload = {
            "workspace_id": workspace_id,
            "message": message,
            "history": history or [],
            **kwargs
        }
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", url, headers=self.headers, json=payload) as response:
                if not response.is_success:
                    self._handle_response(response)
                for line in response.iter_lines():
                    if line:
                        yield json.loads(line)

    # --- Async API ---

    async def alist_workspaces(self) -> List[Workspace]:
        url = f"{self.base_url}/api/v1/workspaces"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self.headers)
            self._handle_response(resp)
            return [Workspace(**ws) for ws in resp.json()]

    async def aget_workspace(self, workspace_id: str) -> Workspace:
        url = f"{self.base_url}/api/v1/workspaces/{workspace_id}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self.headers)
            self._handle_response(resp)
            return Workspace(**resp.json())

    async def asearch_nodes(self, workspace_id: str, query: str, limit: int = 20) -> List[Node]:
        url = f"{self.base_url}/api/v1/workspaces/{workspace_id}/nodes-search"
        params = {"query": query, "limit": limit}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            self._handle_response(resp)
            return [Node(**node) for node in resp.json()]

    async def asearch_semantic(self, workspace_id: str, query: str, limit: int = 20) -> List[Node]:
        url = f"{self.base_url}/api/v1/workspaces/{workspace_id}/nodes/search-semantic"
        payload = {"query": query, "limit": limit}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            self._handle_response(resp)
            return [Node(**node) for node in resp.json()]

    async def aget_node(self, workspace_id: str, node_id: str) -> Node:
        url = f"{self.base_url}/api/v1/workspaces/{workspace_id}/nodes/{node_id}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self.headers)
            self._handle_response(resp)
            return Node(**resp.json())

    async def acreate_node(self, workspace_id: str, title: str, content_type: str, body: str = "", tags: Optional[List[str]] = None, visibility: str = "private", **kwargs) -> Node:
        url = f"{self.base_url}/api/v1/workspaces/{workspace_id}/nodes"
        payload = {
            "title": title,
            "content_type": content_type,
            "body": body,
            "tags": tags or [],
            "visibility": visibility,
            **kwargs
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            self._handle_response(resp)
            return Node(**resp.json())

    async def achat(self, workspace_id: str, message: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/ai/chat"
        payload = {
            "workspace_id": workspace_id,
            "message": message,
            "history": history or [],
            **kwargs
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            self._handle_response(resp)
            return resp.json()

    async def achat_stream(self, workspace_id: str, message: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        url = f"{self.base_url}/api/v1/ai/chat-stream"
        payload = {
            "workspace_id": workspace_id,
            "message": message,
            "history": history or [],
            **kwargs
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=self.headers, json=payload) as response:
                if not response.is_success:
                    self._handle_response(response)
                async for line in response.aiter_lines():
                    if line:
                        yield json.loads(line)
