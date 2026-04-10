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


from typing import Optional, List

# Schema for returning user info
class UserOut(BaseModel):
    id: str
    username: Optional[str] = None
    email: EmailStr
    role: Optional[str] = None
    created_at: Optional[str] = None

class UserPaginatedResponse(BaseModel):
    items: List[UserOut]
    total: int
    page: int
    pageSize: int


# Schema for token responses
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# Schema for refresh request
class TokenRefresh(BaseModel):
    refresh_token: str


# Schema for forgot password - check email
class ForgotPasswordCheck(BaseModel):
    email: EmailStr


# Schema for requesting a password reset (generates a token)
class PasswordResetRequest(BaseModel):
    email: EmailStr


# Schema for reset password (requires token verification)
class ResetPassword(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str = Field(..., min_length=6, max_length=16)
    confirm_password: str

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v

# Schema for updating a user's role
class UserRoleUpdate(BaseModel):
    role: str

# SSO Verify Request
class SSOVerifyModel(BaseModel):
    token: str

# SSO Token Response
class SSOTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    email: str
    role: str
    username: str
    status: str = "active"
    is_first_time_user: bool = False
