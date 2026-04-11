import httpx

data = {
    "display_name": "Test User 3",
    "email": "test3@example.com",
    "password": "Password123!"
}

try:
    with httpx.Client() as client:
        resp = client.post("http://localhost:8000/auth/register", json=data)
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
