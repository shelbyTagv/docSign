"""
document-service/app/services/document_builder.py

Helper functions for document business logic:
- Content hashing for tamper detection
- User info resolution via auth-service
- Workflow state transitions

Centralizing these here keeps the route handlers thin and focused
on HTTP concerns only.
"""

import json
import hashlib
from typing import Optional
import httpx
from ..config import settings


def compute_content_hash(document) -> str:
    """
    Compute SHA-256 of the document's content fields at lock time.
    
    Why hash only these specific fields?
    These are the fields that form the legal content of the document.
    Metadata like status, locked_at, and pdf_path can legitimately change
    after locking; but the actual document content must be immutable.
    
    The hash is stored in documents.content_hash and re-verified on every
    read to detect any tampering with stored document content.
    """
    content = {
        "id": document.id,
        "title": document.title,
        "to_field": document.to_field,
        "cc_field": document.cc_field,
        "ref_field": document.ref_field,
        "subject": document.subject,
        "body": document.body,
        "created_by": document.created_by,
        # Include created_at as ISO string — ensures time is part of the hash
        "created_at": document.created_at.isoformat() if document.created_at else None,
    }
    # sort_keys=True ensures deterministic JSON output regardless of dict insertion order
    content_json = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content_json.encode("utf-8")).hexdigest()


def verify_content_hash(document) -> bool:
    """
    Re-compute the content hash and compare to the stored value.
    Returns False if hashes don't match, indicating potential tampering.
    Returns True if document hasn't been locked yet (no hash to compare).
    """
    if not document.content_hash:
        return True  # Not yet locked — no hash to verify
    return compute_content_hash(document) == document.content_hash


async def get_user_info(user_id: str, access_token: str) -> Optional[dict]:
    """
    Fetch user profile info from auth-service.
    Used to enrich document responses with user names/titles.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.AUTH_SERVICE_URL}/users/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Internal-Key": settings.INTERNAL_API_KEY
                }
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


async def get_user_info_internal(user_id: str) -> Optional[dict]:
    """
    Fetch user info using internal API key (no user token needed).
    Used when document-service needs user info without a client request context.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Call the /users/search endpoint which is available with just internal key
            resp = await client.get(
                f"{settings.AUTH_SERVICE_URL}/users/search",
                params={"q": user_id},
                headers={"X-Internal-Key": settings.INTERNAL_API_KEY,
                         "Authorization": "Bearer internal"}
            )
            if resp.status_code == 200:
                results = resp.json()
                for u in results:
                    if u["id"] == user_id:
                        return u
    except Exception:
        pass
    return None


async def get_user_signature(user_id: str) -> Optional[dict]:
    """
    Retrieve a user's decrypted signature PNG from auth-service.
    Called at signing time to get the current signature for stamping.
    The auth-service decrypts it server-side — document-service never
    sees the encryption key.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.AUTH_SERVICE_URL}/users/internal/signature/{user_id}",
                headers={"X-Internal-Key": settings.INTERNAL_API_KEY}
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None
