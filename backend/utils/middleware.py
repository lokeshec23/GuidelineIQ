from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from utils.logger import user_context
from jose import jwt
from config import JWT_SECRET_KEY, JWT_ALGORITHM

class LogContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token_context = {"username": "Anonymous", "email": "anonymous"}
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # We decode strictly to get payload, duplicate validation happens in dependecies usually
                # But for logging context, we just want "who is this attempting to be"
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
                
                if payload:
                    token_context["username"] = payload.get("username", "Unknown")
                    token_context["email"] = payload.get("email", "Unknown")
            except Exception:
                # Token might be invalid, expired, or malformed. 
                # We don't block the request here (auth middleware handles 401), 
                # we just log as Anonymous/Invalid for now.
                token_context = {"username": "InvalidToken", "email": "unknown"}

        # Set the context for this request
        token = user_context.set(token_context)
        
        try:
            response = await call_next(request)
            return response
        finally:
            # Reset the context after the request
            user_context.reset(token)
