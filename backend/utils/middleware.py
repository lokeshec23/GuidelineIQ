# backend/utils/middleware.py

from starlette.types import ASGIApp, Receive, Scope, Send
from utils.logger import user_context
from jose import jwt
from config import JWT_SECRET_KEY, JWT_ALGORITHM


class LogContextMiddleware:
    """
    Pure ASGI middleware for logging context.
    
    Unlike BaseHTTPMiddleware, this does NOT serialize requests or buffer
    request/response bodies — allowing true concurrent request processing.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token_context = {"username": "Anonymous", "email": "anonymous"}

        # Extract Authorization header from scope
        headers = dict(scope.get("headers", []))
        auth_header_value = headers.get(b"authorization", b"").decode("utf-8", errors="ignore")

        if auth_header_value and auth_header_value.startswith("Bearer "):
            token = auth_header_value.split(" ", 1)[1]
            try:
                payload = jwt.decode(
                    token,
                    JWT_SECRET_KEY,
                    algorithms=[JWT_ALGORITHM],
                    options={"verify_exp": False},
                )
                if payload:
                    token_context["username"] = payload.get("username", "Unknown")
                    token_context["email"] = payload.get("email", "Unknown")
            except Exception:
                token_context = {"username": "InvalidToken", "email": "unknown"}

        # Set the context for this request
        ctx_token = user_context.set(token_context)

        try:
            await self.app(scope, receive, send)
        finally:
            # Reset the context after the request
            user_context.reset(ctx_token)
