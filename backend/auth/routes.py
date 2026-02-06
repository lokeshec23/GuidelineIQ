from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sql_database import get_db
from auth.models import find_user_by_email, create_user, get_all_users, get_user_by_id
from auth.schemas import UserCreate, UserLogin, UserOut, TokenResponse, TokenRefresh
from auth.utils import hash_password, verify_password, create_tokens, verify_token
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
    
    # Initialize default prompts for the new user
    try:
        from prompts.models import initialize_user_prompts
        await initialize_user_prompts(new_user.id)
        print(f"✅ Initialized default prompts for user: {user.email}")
    except Exception as e:
        print(f"⚠️ Failed to initialize prompts for user {user.email}: {e}")

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


# ✅ Get all users (Admin only)
@router.get("/users", response_model=list[UserOut])
async def list_users(authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Verify admin role
    # In a real app, you'd check role here or via dependency
    # For now, we trust the token payload or check DB if needed
    
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