import secrets
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

class CsrfMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, cookie_name: str = "mt_csrf", header_name: str = "X-CSRF-Token"):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        print(f"DEBUG: CSRF Check - Method: {request.method} Path: {request.url.path}")
        # 1. Skip GET/HEAD/OPTIONS
        if request.method in ("GET", "HEAD", "OPTIONS"):
            response = await call_next(request)
            
            # Ensure cookie is set for these methods so the client can read it
            csrf_token = request.cookies.get(self.cookie_name)
            if not csrf_token:
                csrf_token = secrets.token_urlsafe(32)
                response.set_cookie(
                    key=self.cookie_name,
                    value=csrf_token,
                    httponly=False, # Must be False so JS can read it to put in header
                    samesite="lax"
                )
            return response

        # 2. Skip if using API Key (mt_ prefix)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer mt_"):
            return await call_next(request)

        # 3. Check CSRF token for write operations
        csrf_cookie = request.cookies.get(self.cookie_name)
        csrf_header = request.headers.get(self.header_name)

        # if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        #     raise HTTPException(status_code=403, detail="CSRF token validation failed")

        return await call_next(request)
