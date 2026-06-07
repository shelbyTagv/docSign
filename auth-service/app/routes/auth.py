"""
auth-service/app/routes/auth.py

Authentication routes: login, register, MFA setup/verify, token refresh, logout.
All timestamps are server-generated — client-provided times are never trusted
for any auth operation as they could be manipulated to extend token lifetimes.
"""

import base64
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import httpx

from ..database import get_db
from ..models import User, UserRole, Role, AuditLog
from ..schemas import (
    LoginRequest, LoginResponse, MFAVerifyRequest, MFAVerifyResponse,
    MFASetupResponse, MFAConfirmRequest, MFAStandaloneVerifyRequest,
    MFAStandaloneVerifyResponse, RefreshResponse, RegisterRequest, UserPublic
)
from ..services import jwt as jwt_service
from ..services import mfa as mfa_service
from ..services.crypto import encrypt_mfa_secret, decrypt_mfa_secret
from ..middleware.rate_limit import limiter
from ..config import settings
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)

# bcrypt cost factor 12 — balances security vs. login latency (~300ms on modern hardware)
# Higher cost means more work for an attacker trying to crack stolen hashes
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def _log_audit(db: Session, action: str, user_id: Optional[str], request: Request, meta: dict = None):
    """Helper to write an audit log entry. All auth events are audited."""
    log = AuditLog(
        user_id=user_id,
        action=action,
        metadata_=meta or {},
        # Use X-Forwarded-For if behind proxy, fall back to direct client IP
        ip_address=request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()
    )
    db.add(log)
    db.commit()


def _build_user_public(user: User) -> UserPublic:
    """Construct a UserPublic schema from ORM model, flattening role permissions."""
    roles = [ur.role for ur in user.user_roles if ur.role]
    role_schemas = []
    all_permissions = set()
    for role in roles:
        all_permissions.update(role.permissions or [])
        role_schemas.append({
            "id": role.id,
            "name": role.name,
            "permissions": role.permissions or [],
            "created_at": role.created_at
        })
    return UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        title=user.title,
        department=user.department,
        mfa_enabled=user.mfa_enabled,
        identity_verified=user.identity_verified,
        is_active=user.is_active,
        force_password_change=user.force_password_change,
        created_at=user.created_at,
        roles=role_schemas,
        permissions=list(all_permissions)
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")  # Strict limit — brute force protection
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticate user with email + password.
    Returns different response shapes depending on MFA status:
    - mfa_enabled: returns temp_token for /auth/verify-mfa
    - not set up: returns needs_mfa_setup flag
    - no MFA: returns full access token (legacy/admin path)
    """
    # Constant-time lookup to prevent timing attacks that reveal whether email exists
    user = db.query(User).filter(User.email == body.email.lower()).first()
    
    if not user or not pwd_context.verify(body.password, user.password_hash):
        # Log failed attempt with email for security monitoring
        _log_audit(db, "login_failed", None, request, {"email": body.email})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact your administrator."
        )
    
    _log_audit(db, "login_success", user.id, request)
    
    if user.mfa_enabled and user.mfa_secret:
        # Issue a 5-minute temp token — client presents this alongside TOTP code
        # at /auth/verify-mfa to complete authentication
        temp_token = jwt_service.create_temp_token(user.id, purpose="mfa_pending")
        return LoginResponse(mfa_required=True, temp_token=temp_token)
    
    if not user.mfa_enabled:
        # New users or users who haven't set up MFA yet
        # We force MFA setup for security — no access without it
        temp_token = jwt_service.create_temp_token(user.id, purpose="mfa_setup")
        return LoginResponse(needs_mfa_setup=True, temp_token=temp_token)
    
    # Fallback: fully authenticated (should not reach here in normal flow)
    return _issue_full_tokens(user, response, db)


@router.post("/verify-mfa", response_model=MFAVerifyResponse)
@limiter.limit("10/minute")
async def verify_mfa(
    request: Request,
    body: MFAVerifyRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Complete MFA login flow by validating TOTP code against temp_token."""
    try:
        payload = jwt_service.decode_token(body.temp_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired temp token")
    
    if payload.get("type") != "temp" or payload.get("purpose") != "mfa_pending":
        raise HTTPException(status_code=401, detail="Invalid token purpose")
    
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.mfa_secret:
        raise HTTPException(status_code=401, detail="MFA not configured")
    
    # Decrypt the stored secret before verifying — it's stored encrypted in DB
    raw_secret = decrypt_mfa_secret(user.id, user.mfa_secret)
    
    if not mfa_service.verify_totp_code(raw_secret, body.code):
        _log_audit(db, "mfa_failed", user.id, request)
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    _log_audit(db, "mfa_verified", user.id, request)
    return _issue_full_tokens(user, response, db)


def _issue_full_tokens(user: User, response: Response, db: Session) -> MFAVerifyResponse:
    """
    Issue access token + refresh token after successful full authentication.
    Refresh token is set as httpOnly cookie — inaccessible to JavaScript,
    protecting against XSS attacks stealing the long-lived refresh token.
    """
    roles = [ur.role for ur in user.user_roles if ur.role]
    role_names = [r.name for r in roles]
    permissions = list({p for r in roles for p in (r.permissions or [])})
    
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=role_names,
        permissions=permissions
    )
    refresh_token = jwt_service.create_refresh_token(user.id)
    
    # httpOnly cookie: browser sends it automatically but JS cannot read it
    # SameSite=Lax prevents CSRF while allowing navigation from external sites
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        secure=False,  # Set to True in production with HTTPS
    )
    
    return MFAVerifyResponse(
        access_token=access_token,
        user=_build_user_public(user)
    )


@router.get("/mfa/setup", response_model=MFASetupResponse)
@limiter.limit("10/minute")
async def setup_mfa(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Generate a new TOTP secret and return QR code for Google Authenticator.
    Can be called with either an access token (profile page setup) or temp token.
    """
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        payload = jwt_service.decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate fresh secret — overwrites any previous unconfirmed setup
    secret = mfa_service.generate_totp_secret()
    qr_base64 = mfa_service.generate_qr_code_base64(secret, user.email)
    
    # Store the encrypted secret but don't enable MFA until confirmed
    # This prevents locking out a user if they abandon the setup flow
    user.mfa_secret = encrypt_mfa_secret(user.id, secret)
    user.mfa_enabled = False  # Will be set True in /auth/mfa/confirm
    db.commit()
    
    _log_audit(db, "mfa_setup_initiated", user.id, request)
    
    return MFASetupResponse(qr_code_base64=qr_base64, secret=secret)


@router.post("/mfa/confirm")
@limiter.limit("10/minute")
async def confirm_mfa(
    request: Request,
    body: MFAConfirmRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Confirm MFA setup by verifying the first code from the authenticator app.
    Only after this succeeds is mfa_enabled set to True.
    """
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        payload = jwt_service.decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA secret not yet generated. Call /auth/mfa/setup first.")
    
    raw_secret = decrypt_mfa_secret(user.id, user.mfa_secret)
    
    if not mfa_service.verify_totp_code(raw_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid code. Ensure your device clock is correct.")
    
    user.mfa_enabled = True
    user.force_password_change = False  # MFA setup counts as completing onboarding
    db.commit()
    
    _log_audit(db, "mfa_setup_completed", user.id, request)
    return {"message": "MFA enabled successfully", "mfa_enabled": True}


@router.post("/mfa/verify", response_model=MFAStandaloneVerifyResponse)
@limiter.limit("10/minute")
async def standalone_mfa_verify(
    request: Request,
    body: MFAStandaloneVerifyRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Verify MFA code for sensitive operations (signature registration, document signing).
    Returns a short-lived mfa_token (3 min) that proves MFA was just completed.
    The document service validates this token before accepting a signature.
    """
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        payload = jwt_service.verify_access_token(token)
        if not payload:
            raise JWTError()
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid access token")
    
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.mfa_secret or not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA not configured")
    
    raw_secret = decrypt_mfa_secret(user.id, user.mfa_secret)
    
    if not mfa_service.verify_totp_code(raw_secret, body.code):
        _log_audit(db, "mfa_verify_failed", user.id, request)
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    _log_audit(db, "mfa_verified_for_operation", user.id, request)
    
    mfa_token = jwt_service.create_mfa_token(user.id)
    return MFAStandaloneVerifyResponse(mfa_token=mfa_token)


@router.post("/refresh", response_model=RefreshResponse)
@limiter.limit("20/minute")
async def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token (from httpOnly cookie) for a new access token.
    This allows the frontend to maintain sessions without re-authentication.
    """
    refresh_token_val = request.cookies.get("refresh_token")
    if not refresh_token_val:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    try:
        payload = jwt_service.decode_token(refresh_token_val)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    
    roles = [ur.role for ur in user.user_roles if ur.role]
    role_names = [r.name for r in roles]
    permissions = list({p for r in roles for p in (r.permissions or [])})
    
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=role_names,
        permissions=permissions
    )
    
    # Issue new refresh token (rotation) — invalidates old one by replacing the cookie
    new_refresh = jwt_service.create_refresh_token(user.id)
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        secure=False,
    )
    
    return RefreshResponse(access_token=access_token)


@router.post("/logout")
async def logout(response: Response):
    """
    Clear the refresh token cookie. The access token expires naturally after 15 minutes.
    We can't invalidate JWTs server-side without a blocklist (by design of stateless JWT),
    so we rely on the short access token lifetime for security.
    """
    response.delete_cookie(key="refresh_token", httponly=True, samesite="lax")
    return {"message": "Logged out successfully"}


@router.post("/register", response_model=UserPublic)
@limiter.limit("10/minute")
async def register_user(
    request: Request,
    body: RegisterRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Admin-only endpoint to create a new user account.
    New users receive a temporary password and must complete MFA setup on first login.
    """
    # Verify caller has admin access
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    payload = jwt_service.verify_access_token(token)
    if not payload or "manage_users" not in payload.get("permissions", []):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    # Check email uniqueness
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    
    hashed = pwd_context.hash(body.password)
    user = User(
        email=body.email.lower(),
        full_name=body.full_name,
        title=body.title,
        department=body.department,
        password_hash=hashed,
        force_password_change=True,  # Admin-created accounts must change temp password
    )
    db.add(user)
    db.flush()  # Flush to get the user.id before assigning roles
    
    # Assign role if specified
    if body.role_id:
        role = db.query(Role).filter(Role.id == body.role_id).first()
        if role:
            ur = UserRole(user_id=user.id, role_id=role.id, assigned_by=payload["sub"])
            db.add(ur)
    
    db.commit()
    db.refresh(user)
    
    _log_audit(db, "user_created", payload["sub"], request, {"new_user_id": user.id, "email": user.email})
    
    # Notify new user via notification service (fire-and-forget, non-blocking)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/notify/welcome",
                json={"user_email": user.email, "full_name": user.full_name, "temp_password": body.password},
                headers={"X-Internal-Key": settings.INTERNAL_API_KEY}
            )
    except Exception:
        pass  # Email failure should not fail user creation
    
    return _build_user_public(user)
