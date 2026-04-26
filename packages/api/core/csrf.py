import secrets
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from .config import settings

logger = logging.getLogger(__name__)

# Only set the Secure flag when running behind HTTPS (i.e. in production).
_COOKIE_SECURE: bool = settings.app_url.startswith("https://")

class CsrfMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, cookie_name: str = "mt_csrf", header_name: str = "X-CSRF-Token"):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Skip GET/HEAD/OPTIONS — issue / refresh token on these
        if request.method in ("GET", "HEAD", "OPTIONS"):
            response = await call_next(request)

            # Ensure cookie is set so the client can read it for subsequent writes
            csrf_token = request.cookies.get(self.cookie_name)
            if not csrf_token:
                csrf_token = secrets.token_urlsafe(32)
                response.set_cookie(
                    key=self.cookie_name,
                    value=csrf_token,
                    httponly=False,          # Must be readable by JS to echo in the header
                    samesite="lax",
                    secure=_COOKIE_SECURE,   # True in production (HTTPS), False in dev
                )
            return response

        # 2. Skip if using API Key (Bearer mt_…) — API keys are their own CSRF-safe credential
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer mt_"):
            return await call_next(request)

        # 2b. Skip CSRF for unauthenticated auth endpoints.
        #     These run before any CSRF cookie exists (fresh browser session), and
        #     cannot be CSRF-attacked since there is no authenticated session to hijack.
        _CSRF_EXEMPT = {"/auth/login", "/auth/register", "/auth/refresh"}
        if request.url.path in _CSRF_EXEMPT:
            return await call_next(request)

        # 3. Enforce double-submit cookie pattern for browser-originated write requests
        csrf_cookie = request.cookies.get(self.cookie_name)
        csrf_header = request.headers.get(self.header_name)

        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            logger.warning(
                "CSRF validation failed: method=%s path=%s cookie_present=%s header_present=%s",
                request.method,
                request.url.path,
                bool(csrf_cookie),
                bool(csrf_header),
            )
            # NB: BaseHTTPMiddleware does NOT route HTTPException through FastAPI's
            # exception handlers, so raising would surface as 500. Return a Response
            # directly so the client sees the intended 403.
            return Response(
                content='{"detail":"CSRF token validation failed"}',
                status_code=403,
                media_type="application/json",
            )

        return await call_next(request)
