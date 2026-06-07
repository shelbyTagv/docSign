"""
auth-service/app/services/crypto.py

Encryption utilities for storing sensitive user data (MFA secrets, signatures).

Security architecture:
- Master key: Fernet key loaded from environment variable MASTER_ENCRYPTION_KEY
- Per-user key derivation: HKDF(master_key + user_id) produces a unique Fernet key
  per user, so a breach of one user's encrypted data doesn't expose others.
- Signatures are stored as Fernet-encrypted blobs. The IV/salt metadata is stored
  separately in signature_iv so we can re-derive keys if master key rotation is needed.
"""

import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from ..config import settings


def _derive_user_key(user_id: str) -> Fernet:
    """
    Derive a unique Fernet key for a specific user using HKDF.
    
    Why per-user keys instead of one master key?
    If all data is encrypted with the same key, a single key compromise
    exposes every user's data. Per-user derivation means an attacker
    needs BOTH the master key AND the user_id to decrypt any record.
    
    HKDF is the standard key derivation function (RFC 5869) — it's
    designed specifically for deriving strong keys from existing key material.
    """
    master_key_bytes = base64.urlsafe_b64decode(settings.MASTER_ENCRYPTION_KEY)
    
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # Fernet requires exactly 32 bytes
        salt=None,  # No salt needed — user_id is the domain separation info
        info=user_id.encode("utf-8"),
        backend=default_backend()
    )
    
    derived_key = hkdf.derive(master_key_bytes)
    # Fernet requires URL-safe base64-encoded 32-byte key
    fernet_key = base64.urlsafe_b64encode(derived_key)
    return Fernet(fernet_key)


def encrypt_for_user(user_id: str, data: bytes) -> tuple[bytes, str]:
    """
    Encrypt bytes using a user-specific derived key.
    Returns (encrypted_bytes, metadata_string).
    The metadata string records the key version — useful if master key is rotated.
    """
    f = _derive_user_key(user_id)
    encrypted = f.encrypt(data)
    # Store key version info so we know which master key version was used
    # In a production system with key rotation, this would be a version number
    metadata = f"v1:user:{user_id}"
    return encrypted, metadata


def decrypt_for_user(user_id: str, encrypted_data: bytes) -> bytes:
    """
    Decrypt data that was encrypted with encrypt_for_user().
    """
    f = _derive_user_key(user_id)
    return f.decrypt(encrypted_data)


def encrypt_mfa_secret(user_id: str, secret: str) -> str:
    """
    Encrypt a TOTP secret string for storage.
    Returns base64url-encoded ciphertext (safe to store in TEXT column).
    """
    f = _derive_user_key(user_id)
    encrypted = f.encrypt(secret.encode("utf-8"))
    # Return as string for TEXT column storage
    return encrypted.decode("utf-8")


def decrypt_mfa_secret(user_id: str, encrypted_secret: str) -> str:
    """Decrypt a stored MFA secret back to the raw TOTP secret string."""
    f = _derive_user_key(user_id)
    return f.decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")


def hash_password_policy_check(password: str) -> bool:
    """Simple boolean check for password policy (used in service layer)."""
    import re
    return bool(
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
        and re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password)
    )


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest. Used for content integrity verification."""
    return hashlib.sha256(data).hexdigest()
