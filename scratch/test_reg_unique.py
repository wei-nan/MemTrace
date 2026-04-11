import httpx
import secrets

user_id = f"test_{secrets.token_hex(4)}"
email = f"{user_id}@example.com"

data = {
    "display_name": "Test User",
    "email": email,
    "password": "Password123!"
}

try:
    with httpx.Client() as client:
        resp = client.post("http://localhost:8000/auth/register", json=data)
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
