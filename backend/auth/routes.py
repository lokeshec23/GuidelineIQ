from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sql_database import get_db
from auth.models import find_user_by_email, create_user, get_all_users, get_user_by_id, update_user_password, update_user_role
from auth.schemas import UserCreate, UserLogin, UserOut, TokenResponse, TokenRefresh, ForgotPasswordCheck, PasswordResetRequest, ResetPassword, UserRoleUpdate
from auth.utils import hash_password, verify_password, create_tokens, verify_token, create_reset_token, verify_reset_token
from utils.logger import setup_logger
from datetime import datetime

logger = setup_logger(__name__)


router = APIRouter(prefix="/auth", tags=["Authentication"])

# ✅ Register new user
@router.post("/register", response_model=UserOut)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user = await find_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(user.password)
    user_data = {
        "username": user.username, 
        "email": user.email, 
        "hashed_password": hashed_pw, 
        "role": user.role,
        "created_at": datetime.utcnow()
    }
    
    # We pass user_data dict, create_user -> User(**user_data).
    # ensure keys match User mapping.
    new_user = await create_user(db, user_data)
    
    logger.info(f"User registered: {user.email}")

    return UserOut(
        id=str(new_user.id), 
        username=new_user.username, 
        email=new_user.email, 
        role=new_user.role,
        created_at=new_user.created_at.isoformat() if new_user.created_at else None
    )


# ✅ Login user
@router.post("/login", response_model=TokenResponse)
async def login_user(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await find_user_by_email(db, credentials.email)
    
    if not user:
        logger.warning(f"Failed login attempt: User not found for email: {credentials.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(credentials.password, user.hashed_password):
        logger.warning(f"Failed login attempt: Invalid password for email: {credentials.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")


    access_token, refresh_token = create_tokens(str(user.id), user.email, user.username, credentials.remember_me)
    logger.info(f"User logged in successfully: {user.email}")


    user_data = UserOut(id=str(user.id), username=user.username, email=user.email, role=user.role)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_data,
    )


# ✅ Get current logged-in user
@router.get("/me", response_model=UserOut)
async def get_current_user(authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    
    user = await get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(id=str(user.id), username=user.username, email=user.email, role=user.role)


# ✅ Refresh access token using refresh token
@router.post("/refresh")
async def refresh_token(data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    payload = verify_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    
    user = await get_user_by_id(db, user_id)
    if not user:
         logger.warning(f"Refresh token used for non-existent user_id: {user_id}")
         raise HTTPException(status_code=401, detail="User not found")

    new_access_token, _ = create_tokens(user_id, user.email, user.username)
    logger.info(f"Token refreshed for user: {user.email}")


    return JSONResponse({"access_token": new_access_token})


# ✅ Forgot Password - Check if email exists
@router.post("/forgot-password/check")
async def forgot_password_check(data: ForgotPasswordCheck, db: AsyncSession = Depends(get_db)):
    user = await find_user_by_email(db, data.email)
    if not user:
        logger.info(f"Forgot password check: email not found - {data.email}")
        raise HTTPException(status_code=404, detail="Email not registered")
    
    logger.info(f"Forgot password check: email found - {data.email}")
    return JSONResponse({"exists": True, "message": "Email found. You can reset your password."})


# ✅ Forgot Password - Request reset token
@router.post("/forgot-password/request")
async def forgot_password_request(data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    user = await find_user_by_email(db, data.email)
    if not user:
        # Return success even if email not found (prevent email enumeration)
        return JSONResponse({"message": "If the email is registered, a reset token has been generated."})
    
    reset_token = create_reset_token(data.email)
    logger.info(f"Password reset token generated for: {data.email}")
    # In production, send this token via email. For now, return it directly.
    return JSONResponse({"reset_token": reset_token, "message": "Reset token generated. Use it to reset your password."})


# ✅ Forgot Password - Reset password (requires reset token)
@router.post("/forgot-password/reset")
async def forgot_password_reset(data: ResetPassword, db: AsyncSession = Depends(get_db)):
    # Verify the reset token
    token_email = verify_reset_token(data.reset_token)
    if not token_email:
        raise HTTPException(status_code=401, detail="Invalid or expired reset token")
    
    # Ensure the token email matches the request email
    if token_email.lower() != data.email.lower():
        raise HTTPException(status_code=401, detail="Reset token does not match the provided email")
    
    # Verify passwords match (also validated in schema)
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Check if user exists
    user = await find_user_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")
    
    # Hash and update password
    hashed_pw = hash_password(data.new_password)
    updated_user = await update_user_password(db, data.email, hashed_pw)
    
    if not updated_user:
        raise HTTPException(status_code=500, detail="Failed to update password")
    
    logger.info(f"Password reset successful for: {data.email}")
    return JSONResponse({"message": "Password updated successfully!"})


# ✅ Get all users (Admin only)
@router.get("/users", response_model=list[UserOut])
async def list_users(authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Verify admin role by checking the actual user in the database
    user_id = payload.get("sub")
    requesting_user = await get_user_by_id(db, user_id)
    if not requesting_user:
        raise HTTPException(status_code=401, detail="User not found")
    if requesting_user.role != "admin" and not requesting_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await get_all_users(db)
    return [
        UserOut(
            id=str(u.id), 
            username=u.username, 
            email=u.email, 
            role=u.role,
            created_at=u.created_at.isoformat() if u.created_at else None
        ) 
        for u in users
    ]

# ✅ Update user role (Admin only)
@router.put("/users/{user_id}/role", response_model=UserOut)
async def change_user_role(user_id: str, role_update: UserRoleUpdate, authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Verify admin role
    requesting_user_id = payload.get("sub")
    requesting_user = await get_user_by_id(db, requesting_user_id)
    if not requesting_user:
        raise HTTPException(status_code=401, detail="User not found")
    if requesting_user.role != "admin" and not requesting_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if target user exists
    target_user = await get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # Optional: Prevent admin from demoting themselves (simplest check)
    if requesting_user_id == user_id and role_update.role != "admin":
         raise HTTPException(status_code=400, detail="Cannot change your own admin role")
        
    updated_user = await update_user_role(db, target_user.email, role_update.role)
    if not updated_user:
        raise HTTPException(status_code=500, detail="Failed to update role")
        
    logger.info(f"User {target_user.email} role updated to {role_update.role} by admin {requesting_user.email}")
        
    return UserOut(
        id=str(updated_user.id),
        username=updated_user.username,
        email=updated_user.email,
        role=updated_user.role,
        created_at=updated_user.created_at.isoformat() if updated_user.created_at else None
    )
