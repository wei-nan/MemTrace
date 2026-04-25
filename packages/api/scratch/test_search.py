import httpx
token = "mt_df5193298bc41b2848b85258cc68dbea82441409"
ws_id = "ws_9804775a"
url = f"http://localhost:8000/api/v1/workspaces/{ws_id}/nodes/search?query=decay"

headers = {"Authorization": f"Bearer {token}"}
res = httpx.get(url, headers=headers)
print(res.status_code)
print(res.text)
