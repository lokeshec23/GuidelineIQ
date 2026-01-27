# auth/routes.py
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse
from bson import ObjectId
from auth.models import find_user_by_email, create_user
from auth.schemas import UserCreate, UserLogin, UserOut, TokenResponse, TokenRefresh
from auth.utils import hash_password, verify_password, create_tokens, verify_token
from utils.logger import setup_logger
import database

logger = setup_logger(__name__)


router = APIRouter(prefix="/auth", tags=["Authentication"])

# ✅ Register new user
@router.post("/register", response_model=UserOut)
async def register_user(user: UserCreate):
    existing_user = await find_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(user.password)
    user_data = {"username": user.username, "email": user.email, "password": hashed_pw, "role": "user"}
    new_user = await create_user(user_data)
    user_id = str(new_user["_id"])
    
    # Initialize default prompts for the new user
    try:
        from prompts.models import initialize_user_prompts
        await initialize_user_prompts(user_id)
        print(f"✅ Initialized default prompts for user: {user.email}")
    except Exception as e:
        print(f"⚠️ Failed to initialize prompts for user {user.email}: {e}")

    return UserOut(id=str(new_user["_id"]), username=new_user["username"], email=new_user["email"], role=new_user["role"])


# ✅ Login user
@router.post("/login", response_model=TokenResponse)
async def login_user(credentials: UserLogin):
    user = await find_user_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user["password"]):
        logger.warning(f"Failed login attempt for email: {credentials.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token, refresh_token = create_tokens(str(user["_id"]), user["email"], user["username"], credentials.remember_me)
    logger.info(f"User logged in successfully: {user['email']}")


    user_data = UserOut(id=str(user["_id"]), username=user["username"], email=user["email"], role=user["role"])
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_data,
    )


# ✅ Get current logged-in user
@router.get("/me", response_model=UserOut)
async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    
    # Use helper from models instead of direct DB access
    from auth.models import get_user_by_id
    user = await get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(id=str(user["_id"]), username=user["username"], email=user["email"], role=user["role"])


# ✅ Refresh access token using refresh token
@router.post("/refresh")
async def refresh_token(data: TokenRefresh):
    payload = verify_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    
    # Fetch user to get current email/username
    from auth.models import get_user_by_id
    user = await get_user_by_id(user_id)
    if not user:
         logger.warning(f"Refresh token used for non-existent user_id: {user_id}")
         raise HTTPException(status_code=401, detail="User not found")

    new_access_token, _ = create_tokens(user_id, user["email"], user["username"])
    logger.info(f"Token refreshed for user: {user['email']}")


    return JSONResponse({"access_token": new_access_token})