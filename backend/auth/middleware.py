# auth/middleware.py

from fastapi import HTTPException, Header
from bson import ObjectId
from auth.utils import verify_token
from database import users_collection

async def get_current_user_from_token(authorization: str = Header(...)) -> dict:
    """
    Extracts and validates user from JWT token.
    Returns the full user object including role.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token does not contain a user ID")
    
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

async def require_admin(authorization: str = Header(...)) -> dict:
    """
    FastAPI dependency that ensures the current user is an admin.
    Returns the admin user object if valid, raises 403 otherwise.
    """
    user = await get_current_user_from_token(authorization)
    
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Access denied. Admin privileges required."
        )
    
    return user

async def get_admin_user() -> dict:
    """
    Fetches the admin user from the database.
    Returns None if no admin exists.
    """
    admin = await users_collection.find_one({"role": "admin"})
    return admin
