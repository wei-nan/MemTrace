"""
Security-headers middleware.

Adds standard defensive HTTP headers to every response.
HSTS is only emitted when the configured APP_URL uses HTTPS,
so local dev (http://localhost) is unaffected.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Append security headers to every outbound response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Disallow embedding in frames (clickjacking protection)
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS filter (IE / older Chrome)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Limit referrer leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict powerful browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # HSTS — only meaningful over HTTPS
        if settings.app_url.startswith("https://"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response
