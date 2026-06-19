"""
security_headers.py
-------------------
Applies OWASP-recommended security headers to every HTTP response.
Prevents clickjacking, XSS, MIME sniffing, and enforces HTTPS.
"""

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses automatically.
    Protects against: clickjacking, XSS, MIME sniffing, referrer leakage.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent clickjacking — blocks embedding in iframes
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing — stops browsers from guessing file types
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable browser XSS filter (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Hide referrer URL — prevents data leakage to external sites
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy — restrict script/style sources
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )

        # Enforce HTTPS in production (31536000s = 1 year)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Prevent browsers from storing sensitive data
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

        # Permissions Policy — restrict browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(self), geolocation=()"
        )

        return response
