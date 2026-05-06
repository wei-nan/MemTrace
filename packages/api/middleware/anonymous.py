from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from core.auth import AnonymousUser

class AnonymousAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # /public/* path + no valid token -> mark as anonymous
        # We also support marking as anonymous for any path if no token is provided,
        # but the logic in P4.6-F1-4 specifically mentions /public/*
        
        is_public_path = request.url.path.startswith("/public") or request.url.path.startswith("/api/v1/public")
        
        if is_public_path:
            # Check for Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                # No token provided, assign AnonymousUser to request state
                request.state.user = AnonymousUser()
            # If token exists, we let the normal auth dependency handle it later
            # (or we could try to decode it here, but it's better to stay lightweight)
            
        response = await call_next(request)
        return response
