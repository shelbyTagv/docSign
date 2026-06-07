"""
auth-service/app/schemas.py

Pydantic v2 schemas for request validation and response serialization.
Separating schemas from models keeps the API contract independent of the
DB schema — we can change the DB without breaking the API and vice versa.
"""

from __future__ import annotations
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


# ─── Auth Schemas ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """
    Three possible outcomes:
    1. mfa_required=True → user has MFA enabled, needs TOTP code
    2. needs_mfa_setup=True → user hasn't set up MFA yet (new admin-created account)
    3. access_token present → fully authenticated (no MFA configured path)
    """
    access_token: Optional[str] = None
    token_type: str = "bearer"
    mfa_required: bool = False
    needs_mfa_setup: bool = False
    # Short-lived token passed to /auth/verify-mfa to complete MFA flow
    temp_token: Optional[str] = None
    user: Optional["UserPublic"] = None


class MFAVerifyRequest(BaseModel):
    temp_token: str
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class MFAVerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserPublic"


class MFASetupResponse(BaseModel):
    """QR code image as base64 PNG for Google Authenticator."""
    qr_code_base64: str
    secret: str   # Raw secret shown as fallback for manual entry


class MFAConfirmRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class MFAStandaloneVerifyRequest(BaseModel):
    """Used for pre-signing MFA check — returns a short-lived mfa_token."""
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class MFAStandaloneVerifyResponse(BaseModel):
    mfa_token: str   # Short-lived JWT (3 min) proving MFA was just verified
    verified: bool = True


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    title: Optional[str] = None
    department: Optional[str] = None
    # Admin provides a temporary password; user must change on first login
    password: str = Field(..., min_length=8)
    role_id: Optional[int] = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Enforce password policy: 8+ chars with uppercase, lowercase, digit,
        and special character. This is checked at the API layer (not just frontend)
        because API endpoints can be called directly bypassing UI validation.
        """
        errors = []
        if len(v) < 8:
            errors.append("at least 8 characters")
        if not re.search(r"[A-Z]", v):
            errors.append("one uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("one lowercase letter")
        if not re.search(r"\d", v):
            errors.append("one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            errors.append("one special character")
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        return v


# ─── User Schemas ─────────────────────────────────────────────────────────────

class RoleSchema(BaseModel):
    id: int
    name: str
    permissions: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    """Safe user representation — excludes all sensitive fields."""
    id: str
    email: str
    full_name: Optional[str]
    title: Optional[str]
    department: Optional[str]
    mfa_enabled: bool
    identity_verified: bool
    is_active: bool
    force_password_change: bool
    created_at: datetime
    roles: List[RoleSchema] = []
    permissions: List[str] = []

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    title: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)


class SignatureUploadRequest(BaseModel):
    """
    Signature image sent as base64-encoded PNG from the canvas component.
    MFA token header is validated separately in the route handler.
    """
    image_base64: str  # data:image/png;base64,... or raw base64


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        errors = []
        if len(v) < 8:
            errors.append("at least 8 characters")
        if not re.search(r"[A-Z]", v):
            errors.append("one uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("one lowercase letter")
        if not re.search(r"\d", v):
            errors.append("one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            errors.append("one special character")
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        return v


# ─── Role Management Schemas ──────────────────────────────────────────────────

class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    permissions: List[str] = Field(default_factory=list)


class AssignRoleRequest(BaseModel):
    role_id: int


# ─── Internal Schemas (service-to-service) ────────────────────────────────────

class InternalUserSignatureResponse(BaseModel):
    """
    Returned by the internal /internal/signature/{user_id} endpoint.
    Document service calls this to retrieve a user's decrypted signature
    at signing time. Never expose this on public API routes.
    """
    user_id: str
    signature_png_base64: str  # Decrypted PNG as base64
    full_name: str
    title: Optional[str]
    department: Optional[str]


class InternalTokenVerifyResponse(BaseModel):
    """Response from /internal/verify-token used by document service."""
    valid: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []


# Resolve forward references
LoginResponse.model_rebuild()
MFAVerifyResponse.model_rebuild()
