# auth/utils.py
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ✅ Hash password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# ✅ Verify password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ✅ Create JWT token
def create_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

# ✅ Create both access & refresh tokens
def create_tokens(user_id: str, email: str, username: str, remember_me: bool = False):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # If remember_me is True, set refresh token to 30 days, otherwise use default (7 days)
    refresh_days = 30 if remember_me else REFRESH_TOKEN_EXPIRE_DAYS
    refresh_token_expires = timedelta(days=refresh_days)

    access_payload = {"sub": user_id, "type": "access", "email": email, "username": username}
    refresh_payload = {"sub": user_id, "type": "refresh", "email": email, "username": username}

    access_token = create_token(access_payload, access_token_expires)
    refresh_token = create_token(refresh_payload, refresh_token_expires)

    return access_token, refresh_token

# ✅ Verify and decode JWT token
def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None