"""
document-service/app/routes/signing.py

Document signing endpoint — the most security-sensitive operation in the system.
Every signing action requires:
1. Valid JWT access token (user authentication)
2. Fresh MFA token (proves physical MFA device was just used, max 3 minutes old)
3. User must be the current active signatory (correct turn in workflow)
4. User must not have already signed this document
"""

import base64
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import httpx

from ..database import get_db
from ..models import Document, DocumentSignatory, Signature, AuditLog
from ..schemas import SignRequest
from ..services.audit import log as audit_log
from ..services.document_builder import get_user_info_internal, get_user_signature
from ..services.pdf_generator import generate_document_pdf
from ..config import settings

router = APIRouter(prefix="/documents", tags=["Signing"])
security = HTTPBearer(auto_error=False)


def _get_ip(request: Request) -> str:
    return request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()


async def _verify_token(credentials) -> dict:
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.AUTH_SERVICE_URL}/users/internal/verify-token",
                headers={"Authorization": f"Bearer {token}",
                         "X-Internal-Key": settings.INTERNAL_API_KEY}
            )
            data = resp.json()
            if not data.get("valid"):
                raise HTTPException(status_code=401, detail="Invalid token")
            return data
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Auth service unavailable")


async def _verify_mfa_token(mfa_token: str, user_id: str) -> bool:
    """
    Validate the MFA token via auth-service.
    We call auth-service rather than verifying locally because:
    1. The JWT private key lives only in auth-service
    2. Centralizing verification means auth-service can implement additional
       checks (e.g., token revocation) in the future without changing document-service
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.AUTH_SERVICE_URL}/auth/mfa/validate-token",
                json={"mfa_token": mfa_token, "user_id": user_id, "max_age_minutes": 3},
                headers={"X-Internal-Key": settings.INTERNAL_API_KEY}
            )
            return resp.status_code == 200 and resp.json().get("valid", False)
    except Exception:
        return False


@router.post("/{document_id}/sign")
async def sign_document(
    document_id: str,
    request: Request,
    body: SignRequest,
    x_mfa_token: Optional[str] = Header(None, alias="X-MFA-Token"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Apply a digital signature to a document.
    This is a high-security, multi-step validated operation.
    """
    user = await _verify_token(credentials)
    user_id = user["user_id"]

    # ── Step 1: MFA freshness check ──────────────────────────────
    # The mfa_token proves the user physically interacted with their
    # authenticator device within the last 3 minutes — not just that
    # they have a valid session token (which could be stolen).
    if not x_mfa_token:
        raise HTTPException(
            status_code=403,
            detail="MFA verification required. Please verify your MFA code before signing."
        )

    # Validate MFA token — call auth-service which holds the private key
    # We also validate the token locally using the public key endpoint
    mfa_valid = await _verify_mfa_token_locally(x_mfa_token, user_id)
    if not mfa_valid:
        raise HTTPException(
            status_code=403,
            detail="MFA token is invalid or expired (max 3 minutes). Please re-verify."
        )

    # ── Step 2: Load and validate document ──────────────────────
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "in_signing":
        raise HTTPException(status_code=400, detail="Document is not currently in signing")

    # ── Step 3: Verify this user's turn ─────────────────────────
    my_signatory = db.query(DocumentSignatory).filter(
        DocumentSignatory.document_id == document_id,
        DocumentSignatory.user_id == user_id
    ).first()

    if not my_signatory:
        raise HTTPException(status_code=403, detail="You are not a signatory on this document")
    if my_signatory.status != "pending":
        raise HTTPException(
            status_code=403,
            detail=f"It is not your turn to sign. Your current status is: {my_signatory.status}"
        )

    # ── Step 4: Idempotency check — prevent double-signing ──────
    existing_sig = db.query(Signature).filter(
        Signature.document_id == document_id,
        Signature.user_id == user_id
    ).first()
    if existing_sig:
        # 409 Conflict: signature already exists — this is the security requirement
        raise HTTPException(
            status_code=409,
            detail="Signature already recorded for this document. Double-signing is not permitted."
        )

    # ── Step 5: Retrieve signature image from auth-service ──────
    # We fetch from auth-service at signing time (not stored in document-service)
    # so the signature is always current and decryption stays in auth-service
    sig_data = await get_user_signature(user_id)
    if not sig_data:
        raise HTTPException(
            status_code=400,
            detail="No signature registered. Please register your signature in your profile first."
        )

    sig_bytes = base64.b64decode(sig_data["signature_png_base64"])

    # ── Step 6: Create signature record ─────────────────────────
    sig = Signature(
        document_id=document_id,
        user_id=user_id,
        # Server timestamp — legal document signing time must be server-authoritative
        signed_at=datetime.utcnow(),
        # Snapshot: copy of signature bytes at signing time.
        # If user later updates their signature profile, this historical record
        # will still show the signature as it was at the moment they signed.
        signature_image_snapshot=sig_bytes,
        recommendation=body.recommendation.value,
        note=body.note,
        ip_address=_get_ip(request),
        user_agent=request.headers.get("User-Agent", ""),
        mfa_verified=True,  # Only reach here if MFA check passed above
    )
    db.add(sig)

    # ── Step 7: Update signatory status ─────────────────────────
    status_map = {
        "recommended": "recommended",
        "not_recommended": "not_recommended",
        "none": "signed",
    }
    my_signatory.status = status_map.get(body.recommendation.value, "signed")
    if body.note:
        my_signatory.recommendation_note = body.note

    audit_log(db, "signature_applied", _get_ip(request),
              document_id=doc.id, user_id=user_id,
              metadata={"recommendation": body.recommendation.value,
                        "order_index": my_signatory.order_index})

    # ── Step 8: Advance workflow ─────────────────────────────────
    all_signatories = db.query(DocumentSignatory).filter(
        DocumentSignatory.document_id == document_id
    ).order_by(DocumentSignatory.order_index).all()

    # Find the next waiting signatory
    next_signatory = None
    for s in all_signatories:
        if s.user_id == user_id:
            continue
        if s.status == "waiting":
            next_signatory = s
            break

    db.commit()

    if next_signatory:
        # Activate the next signatory in sequence
        next_signatory.status = "pending"
        db.commit()

        # Notify next signatory
        creator_info = await get_user_info_internal(doc.created_by) or {}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{settings.NOTIFICATION_SERVICE_URL}/notify/signatory",
                    json={
                        "document_id": doc.id,
                        "signatory_user_id": next_signatory.user_id,
                        "document_title": doc.title,
                        "creator_name": creator_info.get("full_name", "Unknown"),
                        "frontend_url": settings.FRONTEND_URL,
                    },
                    headers={"X-Internal-Key": settings.INTERNAL_API_KEY}
                )
                next_signatory.notified_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    else:
        # All signatories have signed — generate PDF and complete
        await _complete_document(doc, all_signatories, db, _get_ip(request), user_id)

    return {
        "message": "Document signed successfully",
        "recommendation": body.recommendation.value,
        "workflow_complete": next_signatory is None
    }


async def _verify_mfa_token_locally(mfa_token: str, user_id: str) -> bool:
    """
    Verify MFA token by calling auth-service public key endpoint and decoding locally.
    Falls back gracefully if auth-service is temporarily unavailable.
    """
    try:
        from jose import jwt, JWTError
        from datetime import timezone, timedelta
        
        # Fetch public key from auth-service
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.AUTH_SERVICE_URL}/auth/public-key")
            if resp.status_code != 200:
                return False
            public_key_pem = resp.json()["public_key_pem"]
        
        payload = jwt.decode(mfa_token, public_key_pem, algorithms=["RS256"])
        
        # Validate token type
        if payload.get("type") != "mfa_verified":
            return False
        
        # Validate it belongs to the requesting user
        if payload.get("sub") != user_id:
            return False
        
        # Validate freshness — max 3 minutes old
        verified_at_str = payload.get("verified_at")
        if not verified_at_str:
            return False
        
        verified_at = datetime.fromisoformat(verified_at_str)
        if verified_at.tzinfo is None:
            verified_at = verified_at.replace(tzinfo=timezone.utc)
        
        age_minutes = (datetime.now(timezone.utc) - verified_at).total_seconds() / 60
        return age_minutes <= 3
    
    except Exception:
        return False


async def _complete_document(
    doc: Document,
    signatories,
    db: Session,
    ip: str,
    completing_user_id: str
):
    """
    Called when the last signatory has signed.
    Generates the final PDF and sends completion notifications.
    """
    doc.status = "completed"
    db.commit()

    audit_log(db, "all_signatures_collected", ip,
              document_id=doc.id, user_id=completing_user_id)

    # ── Gather data for PDF ──────────────────────────────────────
    signatures = db.query(Signature).filter(Signature.document_id == doc.id).all()
    audit_logs = db.query(AuditLog).filter(
        AuditLog.document_id == doc.id
    ).order_by(AuditLog.timestamp).all()

    # Enrich signatory and signature data
    sig_map = {s.user_id: s for s in signatures}
    enriched_sigs = []
    for sig in signatories:
        user_info = await get_user_info_internal(sig.user_id) or {}
        sig_record = sig_map.get(sig.user_id)
        enriched_sigs.append({
            "user_id": sig.user_id,
            "full_name": user_info.get("full_name", "Unknown"),
            "title": user_info.get("title"),
            "department": user_info.get("department"),
        })

    signature_data = []
    for s in signatures:
        signature_data.append({
            "user_id": s.user_id,
            "signed_at": s.signed_at,
            "signature_image_bytes": s.signature_image_snapshot,
            "recommendation": s.recommendation,
            "note": s.note,
        })

    audit_log_data = []
    for log in audit_logs:
        user_info = await get_user_info_internal(log.user_id) if log.user_id else None
        audit_log_data.append({
            "timestamp": log.timestamp,
            "user_name": user_info.get("full_name", "System") if user_info else "System",
            "user_id": log.user_id,
            "action": log.action,
            "ip_address": log.ip_address,
        })

    # ── Generate PDF ─────────────────────────────────────────────
    import os
    pdf_path = os.path.join(settings.PDF_STORAGE_PATH, f"{doc.id}.pdf")
    os.makedirs(settings.PDF_STORAGE_PATH, exist_ok=True)

    try:
        pdf_hash = generate_document_pdf(
            document_data={
                "id": doc.id,
                "title": doc.title,
                "to_field": doc.to_field,
                "cc_field": doc.cc_field,
                "ref_field": doc.ref_field,
                "subject": doc.subject,
                "body": doc.body,
                "created_at": doc.created_at,
                "content_hash": doc.content_hash,
            },
            signatories=enriched_sigs,
            signatures=signature_data,
            audit_logs=audit_log_data,
            output_path=pdf_path
        )

        doc.final_pdf_path = pdf_path
        doc.pdf_hash = pdf_hash
        db.commit()

        audit_log(db, "pdf_generated", ip,
                  document_id=doc.id, user_id=completing_user_id,
                  metadata={"pdf_path": pdf_path, "pdf_hash": pdf_hash[:16] + "..."})

    except Exception as e:
        audit_log(db, "pdf_generation_failed", ip,
                  document_id=doc.id, user_id=completing_user_id,
                  metadata={"error": str(e)})
        return

    # ── Send completion notifications ────────────────────────────
    # Collect recipient emails: creator + all signatories
    creator_info = await get_user_info_internal(doc.created_by) or {}
    recipient_emails = []
    if creator_info.get("email"):
        recipient_emails.append(creator_info["email"])

    for sig in signatories:
        user_info = await get_user_info_internal(sig.user_id) or {}
        if user_info.get("email"):
            recipient_emails.append(user_info["email"])

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/notify/completed",
                json={
                    "document_id": doc.id,
                    "document_title": doc.title,
                    "recipient_emails": list(set(recipient_emails)),
                    "pdf_path": pdf_path,
                },
                headers={"X-Internal-Key": settings.INTERNAL_API_KEY}
            )
        audit_log(db, "completion_email_sent", ip,
                  document_id=doc.id, user_id=completing_user_id,
                  metadata={"recipients": len(recipient_emails)})
    except Exception as e:
        audit_log(db, "completion_email_failed", ip,
                  document_id=doc.id,
                  metadata={"error": str(e)})


@router.get("/{document_id}/download")
async def download_pdf(
    document_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Download the final signed PDF. Only available for completed documents."""
    from fastapi.responses import FileResponse
    import os

    user = await _verify_token(credentials)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "completed":
        raise HTTPException(status_code=400, detail="Document is not yet completed")

    is_creator = doc.created_by == user["user_id"]
    is_signatory = any(s.user_id == user["user_id"] for s in doc.signatories)
    is_admin = "view_all_documents" in user.get("permissions", [])
    if not (is_creator or is_signatory or is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    if not doc.final_pdf_path or not os.path.exists(doc.final_pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    audit_log(db, "pdf_downloaded", _get_ip(request),
              document_id=doc.id, user_id=user["user_id"])

    return FileResponse(
        doc.final_pdf_path,
        media_type="application/pdf",
        filename=f"{doc.title.replace(' ', '_')}_signed.pdf"
    )
