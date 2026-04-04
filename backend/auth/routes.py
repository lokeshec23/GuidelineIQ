from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sql_database import get_db
from auth.models import find_user_by_email, find_user_by_username, create_user, get_all_users, get_user_by_id, update_user_password, update_user_role
from auth.schemas import UserCreate, UserLogin, UserOut, TokenResponse, TokenRefresh, ForgotPasswordCheck, PasswordResetRequest, ResetPassword, UserRoleUpdate, SSOVerifyModel, SSOTokenResponse
from auth.utils import hash_password, verify_password, create_tokens, verify_token, create_reset_token, verify_reset_token, hash_password, verify_password, create_tokens, verify_token, create_reset_token, verify_reset_token
from utils.logger import setup_logger
from datetime import datetime, timedelta
import urllib.parse
import random
import base64
import zlib
import xmltodict
import uuid
import os
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

logger = setup_logger(__name__)

# SSO temporary store for tokens
SSO_TEMP_STORE = {}
SSO_TOKEN_TTL = 300 # 5 minutes

router = APIRouter(prefix="/auth", tags=["Authentication"])

# SSO Routes
@router.get("/ValidateAzureAD")
async def login_azure():
    logger.info("SSO: Azure AD Login Triggered")
    
    tenant_id = os.getenv('TENANT_ID')
    sso_reply_url = os.getenv('SSO_REPLY_URL')
    
    if not tenant_id or not sso_reply_url:
        logger.error("SSO: Missing TENANT_ID or SSO_REPLY_URL in environment")
        raise HTTPException(status_code=500, detail="SSO configuration missing")

    number = random.randint(100000, 999999)
    unique_id = f"_{number}"
    issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    sso_login_url = f"https://login.microsoftonline.com/{tenant_id}/saml2"
    application_base_url = os.getenv('APPLICATION_BASE_URL', "LoanDNAPlatform")

    xml = f"""<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{unique_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{sso_login_url}"
    AssertionConsumerServiceURL="{sso_reply_url}"
    ForceAuthn="false">
    <saml:Issuer>{application_base_url}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
        AllowCreate="true"/>
</samlp:AuthnRequest>"""

    def deflate_raw(data: bytes) -> bytes:
        compressor = zlib.compressobj(level=9, wbits=-15)
        compressed = compressor.compress(data)
        compressed += compressor.flush()
        return compressed

    xml_bytes = xml.encode("utf-8")
    deflated = deflate_raw(xml_bytes)
    base64_encoded = base64.b64encode(deflated).decode("utf-8")
    url_encoded = urllib.parse.quote(base64_encoded)

    relay_state = "IncomeAnalyzer"
    redirect_url = f"{sso_login_url}?SAMLRequest={url_encoded}&RelayState={urllib.parse.quote(relay_state)}"

    logger.info(f"SSO: Redirecting to Microsoft: {sso_login_url}")
    return RedirectResponse(url=redirect_url)


@router.post("/api/SSOReplyURI")
async def sso_reply(req: Request):
    form = await req.form()
    saml_response = form.get("SAMLResponse")
    logger.info("SSO: Reply Received from Microsoft")

    if not saml_response:
        logger.warning("SSO: Missing SAMLResponse in form data")
        raise HTTPException(status_code=400, detail="Missing SAMLResponse")

    try:
        decoded_xml = base64.b64decode(saml_response).decode("utf-8")
        parsed = xmltodict.parse(decoded_xml)
    except Exception as e:
        logger.error(f"SSO: Failed to decode/parse SAML response: {e}")
        raise HTTPException(status_code=400, detail="Invalid SAML response")

    # Try various SAML response namespaces
    response = (
        parsed.get("samlp:Response") or
        parsed.get("saml2p:Response") or
        parsed.get("Response") or
        parsed.get("{urn:oasis:names:tc:SAML:2.0:protocol}Response")
    )

    if not response:
        logger.warning("SSO: Invalid SAML response - no response key found")
        raise HTTPException(status_code=400, detail="Invalid SAML response structure")

    assertion = (
        response.get("saml:Assertion") or
        response.get("saml2:Assertion") or
        response.get("Assertion") or
        response.get("{urn:oasis:names:tc:SAML:2.0:assertion}Assertion")
    )

    if not assertion:
        logger.warning("SSO: SAML Assertion missing or encrypted")
        raise HTTPException(status_code=400, detail="SAML Assertion missing")

    attr_stmt = (
        assertion.get("saml:AttributeStatement", {}) or
        assertion.get("saml2:AttributeStatement", {}) or
        assertion.get("AttributeStatement", {})
    )

    attributes = (
        attr_stmt.get("saml:Attribute", []) or
        attr_stmt.get("saml2:Attribute", []) or
        attr_stmt.get("Attribute", [])
    )

    if isinstance(attributes, dict):
        attributes = [attributes]

    sso_email = None
    for attr in attributes:
        name = attr.get("@Name", "")
        if "email" in name.lower() or "mail" in name.lower():
            attr_value = (
                attr.get("saml:AttributeValue") or
                attr.get("saml2:AttributeValue") or
                attr.get("AttributeValue")
            )
            
            if isinstance(attr_value, dict):
                sso_email = attr_value.get("#text") or attr_value.get("text")
            elif isinstance(attr_value, str):
                sso_email = attr_value
            elif isinstance(attr_value, list) and len(attr_value) > 0:
                first_val = attr_value[0]
                if isinstance(first_val, dict):
                    sso_email = first_val.get("#text") or first_val.get("text")
                else:
                    sso_email = first_val

            if sso_email:
                break

    if not sso_email:
        logger.warning("SSO: Email not found in SAML attributes")
        raise HTTPException(status_code=400, detail="SSO email not found")

    sso_email = sso_email.lower()
    
    # Check if user exists in DB
    # Note: We need a db session here, but this endpoint is usually called by Microsoft's browser redirect.
    # We'll use a temporary token and let the frontend 'exchange' it where we can easily use Depends(get_db).
    
    temp_token = str(uuid.uuid4())
    SSO_TEMP_STORE[temp_token] = {
        "email": sso_email,
        "expires": datetime.utcnow() + timedelta(seconds=SSO_TOKEN_TTL)
    }
    
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    redirect_to = f"{frontend_url}/sso?token={temp_token}"
    
    logger.info(f"SSO: Success for {sso_email}. Redirecting to frontend with temp token.")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url={redirect_to}">
        <title>Redirecting...</title>
    </head>
    <body>
        <p>Login successful. Redirecting...</p>
        <script>
            window.location.href = "{redirect_to}";
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/sso-exchange", response_model=SSOTokenResponse)
async def sso_exchange(payload: SSOVerifyModel, db: AsyncSession = Depends(get_db)):
    token = payload.token
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    data = SSO_TEMP_STORE.pop(token, None)
    if not data:
        logger.warning(f"SSO: Invalid or expired token exchange attempt: {token[:8]}...")
        raise HTTPException(status_code=401, detail="Invalid or expired SSO token")

    if data["expires"] < datetime.utcnow():
        logger.warning(f"SSO: Expired token for email: {data.get('email')}")
        raise HTTPException(status_code=401, detail="SSO token has expired")

    email = data.get("email")
    user = await find_user_by_email(db, email)
    
    if not user:
        logger.warning(f"SSO: Access denied - unregistered email: {email}")
        raise HTTPException(status_code=403, detail="Account not registered. Please contact your administrator.")

    access_token, refresh_token = create_tokens(str(user.id), user.email, user.username)
    
    logger.info(f"SSO: Final login successful for {email}")

    return SSOTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        email=user.email,
        role=user.role,
        username=user.username,
        status="active",
        is_first_time_user=getattr(user, "is_first_time_user", False)
    )


# ✅ Register new user
@router.post("/register", response_model=UserOut)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user_email = await find_user_by_email(db, user.email)
    if existing_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    if user.username:
        existing_user_username = await find_user_by_username(db, user.username)
        if existing_user_username:
            raise HTTPException(status_code=400, detail="Username already registered")

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
    
    if requesting_user.email != "admin@admin.com":
        raise HTTPException(status_code=403, detail="Only superadmin (admin@admin.com) can change roles")
    
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
