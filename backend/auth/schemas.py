# auth/schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Schema for user registration
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=16)
    role: str

    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v) < 6 or len(v) > 16:
             logger.warning(f"Password validation failed: length {len(v)}")
             raise ValueError('Password must be between 6 and 16 characters')
        return v


# Schema for login
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False


# Schema for returning user info
class UserOut(BaseModel):
    id: str
    username: Optional[str] = None
    email: EmailStr
    role: Optional[str] = None


# Schema for token responses
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# Schema for refresh request
class TokenRefresh(BaseModel):
    refresh_token: str