"""
auth-service/app/services/jwt.py

JWT token management using RS256 (RSA + SHA-256).
RS256 is chosen over HS256 because:
1. The public key can be shared with other microservices so they can
   VERIFY tokens without knowing the private key (which would allow forgery).
2. Asymmetric keys: if a service is compromised, only the auth service's
   private key allows token creation — not any service that can verify.
3. Industry standard for OAuth2/OIDC compatibility.

Keys are generated on first startup and persisted to /app/keys/ volume.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from jose import jwt, JWTError

from ..config import settings

PRIVATE_KEY_PATH = Path("/app/keys/private.pem")
PUBLIC_KEY_PATH = Path("/app/keys/public.pem")

_private_key_pem: Optional[bytes] = None
_public_key_pem: Optional[bytes] = None


def _ensure_keys() -> None:
    """
    Generate RSA key pair on first startup, then load from disk on subsequent starts.
    Persistence via Docker volume ensures tokens issued before a restart remain valid.
    """
    global _private_key_pem, _public_key_pem

    if _private_key_pem and _public_key_pem:
        return  # Already loaded in this process

    if PRIVATE_KEY_PATH.exists() and PUBLIC_KEY_PATH.exists():
        # Load existing keys — critical for token continuity across restarts
        _private_key_pem = PRIVATE_KEY_PATH.read_bytes()
        _public_key_pem = PUBLIC_KEY_PATH.read_bytes()
        return

    # Generate a new 2048-bit RSA key pair
    # 2048-bit is the minimum recommended by NIST for new systems
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    _private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
        # No passphrase — the container's filesystem is the security boundary
        # A passphrase would require manual entry on each restart, breaking automation
    )

    _public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Persist to volume — ensure directory exists first
    PRIVATE_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_KEY_PATH.write_bytes(_private_key_pem)
    # Private key: only owner can read
    os.chmod(PRIVATE_KEY_PATH, 0o600)
    PUBLIC_KEY_PATH.write_bytes(_public_key_pem)


def get_public_key_pem() -> bytes:
    """Returns PEM-encoded public key for external verification."""
    _ensure_keys()
    return _public_key_pem


def create_access_token(
    user_id: str,
    email: str,
    roles: list[str],
    permissions: list[str],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a short-lived JWT access token.
    Payload includes roles and permissions so downstream services can
    perform authorization without a DB lookup on every request.
    """
    _ensure_keys()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": user_id,
        "email": email,
        "roles": roles,
        "permissions": permissions,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, _private_key_pem, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """
    Refresh tokens are long-lived (7 days) but contain minimal claims.
    They are delivered via httpOnly cookie — inaccessible to JavaScript,
    protecting against XSS-based token theft.
    """
    _ensure_keys()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, _private_key_pem, algorithm=settings.JWT_ALGORITHM)


def create_temp_token(user_id: str, purpose: str = "mfa_pending") -> str:
    """
    Short-lived token (5 minutes) used during multi-step auth flows.
    The 'purpose' claim prevents temp tokens from being misused
    in place of access tokens (defense in depth).
    """
    _ensure_keys()
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "temp",
        "purpose": purpose,
    }
    return jwt.encode(payload, _private_key_pem, algorithm=settings.JWT_ALGORITHM)


def create_mfa_token(user_id: str) -> str:
    """
    Ultra-short-lived token (3 minutes) proving MFA was just completed.
    Document service requires this header on /sign endpoint.
    The 3-minute window is a balance: long enough for the UI to submit the
    signature, short enough to prevent replay attacks.
    """
    _ensure_keys()
    expire = datetime.now(timezone.utc) + timedelta(minutes=3)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "mfa_verified",
        # Store exact verification time so document service can double-check freshness
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    return jwt.encode(payload, _private_key_pem, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises JWTError on invalid/expired tokens.
    """
    _ensure_keys()
    return jwt.decode(token, _public_key_pem, algorithms=[settings.JWT_ALGORITHM])


def verify_access_token(token: str) -> Optional[dict[str, Any]]:
    """Returns payload dict if valid access token, None otherwise."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def verify_mfa_token(token: str, max_age_minutes: int = 3) -> Optional[dict[str, Any]]:
    """
    Verify an MFA token and check it was issued within max_age_minutes.
    We re-check the issue time here because the exp claim gives a 3-minute
    window from creation, but the document service needs to know it hasn't
    been sitting in the client for 2m59s after a 5-minute delay.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "mfa_verified":
            return None
        verified_at_str = payload.get("verified_at")
        if not verified_at_str:
            return None
        verified_at = datetime.fromisoformat(verified_at_str)
        age = (datetime.now(timezone.utc) - verified_at).total_seconds() / 60
        if age > max_age_minutes:
            return None
        return payload
    except JWTError:
        return None
