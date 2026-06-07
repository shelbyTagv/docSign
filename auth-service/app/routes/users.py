"""
auth-service/app/routes/users.py

User profile management and signature registration.
The signature endpoint is particularly security-sensitive:
it requires a fresh MFA token (max 2 minutes old) to prevent
an attacker who has gained access to a session from registering
a fraudulent signature without the physical MFA device.
"""

import base64
import io
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from PIL import Image

from ..database import get_db
from ..models import User, UserRole, Role, AuditLog
from ..schemas import (
    UserPublic, UserUpdateRequest, SignatureUploadRequest,
    PasswordChangeRequest, InternalUserSignatureResponse
)
from ..services import jwt as jwt_service
from ..services.crypto import encrypt_for_user, decrypt_for_user
from ..middleware.rate_limit import limiter
from ..config import settings

router = APIRouter(prefix="/users", tags=["Users"])
security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_current_user(
    credentials: HTTPAuthorizationCredentials,
    db: Session
) -> User:
    """Extract and verify the authenticated user from the Bearer token."""
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    payload = jwt_service.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found or inactive")
    
    return user


def _build_user_public(user: User) -> UserPublic:
    roles = [ur.role for ur in user.user_roles if ur.role]
    all_permissions = list({p for r in roles for p in (r.permissions or [])})
    role_schemas = [{"id": r.id, "name": r.name, "permissions": r.permissions or [], "created_at": r.created_at} for r in roles]
    return UserPublic(
        id=user.id, email=user.email, full_name=user.full_name,
        title=user.title, department=user.department,
        mfa_enabled=user.mfa_enabled, identity_verified=user.identity_verified,
        is_active=user.is_active, force_password_change=user.force_password_change,
        created_at=user.created_at, roles=role_schemas, permissions=all_permissions
    )


@router.get("/me", response_model=UserPublic)
@limiter.limit("30/minute")
async def get_me(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Return the authenticated user's profile."""
    user = _get_current_user(credentials, db)
    return _build_user_public(user)


@router.put("/me", response_model=UserPublic)
@limiter.limit("10/minute")
async def update_me(
    request: Request,
    body: UserUpdateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Update mutable profile fields (name, title, department)."""
    user = _get_current_user(credentials, db)
    
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.title is not None:
        user.title = body.title
    if body.department is not None:
        user.department = body.department
    
    db.commit()
    db.refresh(user)
    
    log = AuditLog(user_id=user.id, action="profile_updated",
                   ip_address=request.client.host, metadata_={})
    db.add(log)
    db.commit()
    
    return _build_user_public(user)


@router.post("/me/signature")
@limiter.limit("5/minute")  # Very strict — signature registration is a high-value action
async def register_signature(
    request: Request,
    body: SignatureUploadRequest,
    x_mfa_token: Optional[str] = Header(None, alias="X-MFA-Token"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Register a user's drawn signature image after MFA verification.
    
    Why require a fresh MFA token here?
    Even if an attacker has stolen the user's access token (e.g., via XSS),
    they cannot register a fraudulent signature without also having the
    physical MFA device. The 2-minute window limits replay attack exposure.
    """
    user = _get_current_user(credentials, db)
    
    # Validate fresh MFA token — must be signed by auth service and < 2 minutes old
    if not x_mfa_token:
        raise HTTPException(status_code=403, detail="MFA verification required. Include X-MFA-Token header.")
    
    mfa_payload = jwt_service.verify_mfa_token(x_mfa_token, max_age_minutes=2)
    if not mfa_payload:
        raise HTTPException(status_code=403, detail="MFA token expired or invalid. Please re-verify.")
    
    # Ensure the MFA token belongs to the same user making the request
    if mfa_payload.get("sub") != user.id:
        raise HTTPException(status_code=403, detail="MFA token user mismatch")
    
    # Parse the base64 image — strip data URL prefix if present
    image_data = body.image_base64
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]
    
    try:
        png_bytes = base64.b64decode(image_data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")
    
    # Validate it's actually a PNG image using Pillow
    try:
        img = Image.open(io.BytesIO(png_bytes))
        if img.format not in ("PNG", "JPEG"):
            raise ValueError("Not PNG/JPEG")
        # Normalize to PNG for consistent storage format
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image data — must be PNG or JPEG")
    
    # Validate minimum signature content (reject blank/near-blank drawings)
    if len(png_bytes) < 2000:  # ~2KB minimum for any real signature stroke
        raise HTTPException(status_code=400, detail="Signature appears empty. Please draw a complete signature.")
    
    # Encrypt with user-derived key — see crypto.py for key derivation details
    encrypted_bytes, metadata = encrypt_for_user(user.id, png_bytes)
    
    user.signature_encrypted = encrypted_bytes
    user.signature_iv = metadata
    user.identity_verified = True
    db.commit()
    
    # Audit log — do NOT log the actual signature bytes (sensitive biometric data)
    log = AuditLog(
        user_id=user.id,
        action="signature_registered",
        ip_address=request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip(),
        metadata_={"image_size_bytes": len(png_bytes)}
    )
    db.add(log)
    db.commit()
    
    return {"message": "Signature registered successfully", "identity_verified": True}


@router.get("/me/signature/preview")
@limiter.limit("20/minute")
async def preview_signature(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Return the current user's decrypted signature as base64 PNG for display."""
    user = _get_current_user(credentials, db)
    
    if not user.signature_encrypted:
        raise HTTPException(status_code=404, detail="No signature registered")
    
    png_bytes = decrypt_for_user(user.id, user.signature_encrypted)
    return {"signature_base64": base64.b64encode(png_bytes).decode("utf-8")}


@router.post("/me/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    body: PasswordChangeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Change the authenticated user's password."""
    user = _get_current_user(credentials, db)
    
    if not pwd_context.verify(body.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    user.password_hash = pwd_context.hash(body.new_password)
    user.force_password_change = False
    db.commit()
    
    log = AuditLog(user_id=user.id, action="password_changed",
                   ip_address=request.client.host, metadata_={})
    db.add(log)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.get("/", response_model=List[UserPublic])
@limiter.limit("20/minute")
async def list_users(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Admin only: list all users."""
    token = credentials.credentials if credentials else None
    payload = jwt_service.verify_access_token(token) if token else None
    if not payload or "manage_users" not in payload.get("permissions", []):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    users = db.query(User).all()
    return [_build_user_public(u) for u in users]


@router.get("/search", response_model=List[UserPublic])
@limiter.limit("30/minute")
async def search_users(
    request: Request,
    q: str = "",
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Search users by name or email — used by document creator when adding signatories."""
    token = credentials.credentials if credentials else None
    payload = jwt_service.verify_access_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    users = db.query(User).filter(
        User.is_active == True,
        (User.full_name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
    ).limit(20).all()
    
    return [_build_user_public(u) for u in users]


# ─── Internal Endpoints (service-to-service only) ────────────────────────────

@router.get("/internal/signature/{user_id}", response_model=InternalUserSignatureResponse)
async def get_user_signature_internal(
    user_id: str,
    request: Request,
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
    db: Session = Depends(get_db)
):
    """
    INTERNAL ONLY — used by document-service to retrieve a user's decrypted signature
    at signing time. Protected by INTERNAL_API_KEY so external clients cannot call it.
    
    We decrypt here rather than in document-service because:
    1. The encryption key (MASTER_ENCRYPTION_KEY) lives only in auth-service
    2. This follows the principle of least privilege — document service
       never has access to the raw encryption key
    """
    if x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Internal access only")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.signature_encrypted:
        raise HTTPException(status_code=404, detail="User has no registered signature")
    
    png_bytes = decrypt_for_user(user.id, user.signature_encrypted)
    
    return InternalUserSignatureResponse(
        user_id=user.id,
        signature_png_base64=base64.b64encode(png_bytes).decode("utf-8"),
        full_name=user.full_name or "",
        title=user.title,
        department=user.department
    )


@router.get("/internal/verify-token")
async def verify_token_internal(
    request: Request,
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
    authorization: Optional[str] = Header(None)
):
    """
    INTERNAL ONLY — document-service calls this to validate a user's access token
    and retrieve their permissions without maintaining a copy of the JWT public key.
    This centralizes token verification in auth-service.
    """
    if x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Internal access only")
    
    if not authorization or not authorization.startswith("Bearer "):
        return {"valid": False}
    
    token = authorization.split(" ", 1)[1]
    payload = jwt_service.verify_access_token(token)
    
    if not payload:
        return {"valid": False}
    
    return {
        "valid": True,
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
        "permissions": payload.get("permissions", [])
    }
