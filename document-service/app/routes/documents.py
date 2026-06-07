"""
document-service/app/routes/documents.py

Document CRUD and workflow endpoints.
All write operations are guarded by JWT verification.
Content hash validation runs on every document read.
"""

import base64
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import httpx

from ..database import get_db
from ..models import Document, DocumentSignatory, Signature, AuditLog
from ..schemas import (
    DocumentCreateRequest, DocumentUpdateRequest, DocumentResponse,
    DocumentListItem, SignatoryInput, SignatorySchema, SignatureSchema
)
from ..services.audit import log as audit_log
from ..services.document_builder import (
    compute_content_hash, verify_content_hash,
    get_user_signature, get_user_info_internal
)
from ..config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])
security = HTTPBearer(auto_error=False)


def _get_ip(request: Request) -> str:
    return request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()


async def _verify_token(credentials, internal_key=None) -> dict:
    """Call auth-service to verify the JWT and return the payload."""
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.AUTH_SERVICE_URL}/users/internal/verify-token",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Internal-Key": settings.INTERNAL_API_KEY
                }
            )
            data = resp.json()
            if not data.get("valid"):
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            return data
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Auth service unavailable")


async def _enrich_signatories(signatories: List[DocumentSignatory], signatures: List[Signature]) -> List[dict]:
    """Add user info and signature data to signatory records."""
    sig_map = {s.user_id: s for s in signatures}
    result = []
    for s in signatories:
        user_info = await get_user_info_internal(s.user_id) or {}
        sig = sig_map.get(s.user_id)
        item = {
            "id": s.id,
            "document_id": s.document_id,
            "user_id": s.user_id,
            "order_index": s.order_index,
            "is_final_decision_maker": s.is_final_decision_maker,
            "status": s.status,
            "recommendation_note": s.recommendation_note,
            "notified_at": s.notified_at,
            "user_full_name": user_info.get("full_name"),
            "user_email": user_info.get("email"),
            "user_title": user_info.get("title"),
            "user_department": user_info.get("department"),
            "signed_at": sig.signed_at if sig else None,
            "signature_image_base64": (
                base64.b64encode(sig.signature_image_snapshot).decode() if sig else None
            ),
        }
        result.append(item)
    return result


@router.post("/", status_code=201)
async def create_document(
    request: Request,
    body: DocumentCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Create a new document in draft status."""
    user = await _verify_token(credentials)
    if "create_document" not in user.get("permissions", []):
        raise HTTPException(status_code=403, detail="create_document permission required")

    doc = Document(
        title=body.title,
        to_field=body.to_field,
        cc_field=body.cc_field,
        ref_field=body.ref_field,
        subject=body.subject,
        body=body.body,
        created_by=user["user_id"],
        # Server timestamp — never trust client for document creation time
        created_at=datetime.utcnow(),
        status="draft"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    audit_log(db, "document_created", _get_ip(request),
              document_id=doc.id, user_id=user["user_id"],
              metadata={"title": doc.title})

    return {"id": doc.id, "status": doc.status, "created_at": doc.created_at.isoformat()}


@router.get("/", response_model=List[DocumentListItem])
async def list_documents(
    request: Request,
    filter: Optional[str] = Query("all", regex="^(created|pending_signature|signed|all)$"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """List documents relevant to the current user."""
    user = await _verify_token(credentials)
    user_id = user["user_id"]

    # Documents the user created
    created_ids = {d.id for d in db.query(Document.id).filter(Document.created_by == user_id).all()}

    # Documents where user is a signatory
    signatory_doc_ids = {
        s.document_id for s in db.query(DocumentSignatory.document_id)
        .filter(DocumentSignatory.user_id == user_id).all()
    }

    all_ids = created_ids | signatory_doc_ids
    if not all_ids:
        return []

    docs = db.query(Document).filter(Document.id.in_(all_ids)).order_by(Document.created_at.desc()).all()

    result = []
    for doc in docs:
        # Filter logic
        if filter == "created" and doc.created_by != user_id:
            continue
        if filter == "pending_signature":
            my_sig = next((s for s in doc.signatories if s.user_id == user_id and s.status == "pending"), None)
            if not my_sig:
                continue
        if filter == "signed":
            my_sig_exists = any(s.user_id == user_id for s in doc.signatures)
            if not my_sig_exists:
                continue

        my_signatory = next((s for s in doc.signatories if s.user_id == user_id), None)
        creator_info = await get_user_info_internal(doc.created_by) or {}

        result.append(DocumentListItem(
            id=doc.id,
            title=doc.title,
            subject=doc.subject,
            status=doc.status,
            created_at=doc.created_at,
            created_by=doc.created_by,
            creator_name=creator_info.get("full_name"),
            signatory_count=len(doc.signatories),
            my_signatory_status=my_signatory.status if my_signatory else None
        ))

    return result


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get full document detail. Validates content hash on every read."""
    user = await _verify_token(credentials)
    user_id = user["user_id"]

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check access: creator or signatory
    is_creator = doc.created_by == user_id
    is_signatory = any(s.user_id == user_id for s in doc.signatories)
    is_admin = "view_all_documents" in user.get("permissions", [])
    if not (is_creator or is_signatory or is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    # Content integrity check — detect any direct DB tampering
    if doc.content_hash and not verify_content_hash(doc):
        raise HTTPException(
            status_code=409,
            detail="SECURITY ALERT: Document content hash mismatch. Possible tampering detected."
        )

    audit_log(db, "document_viewed", _get_ip(request),
              document_id=doc.id, user_id=user_id)

    creator_info = await get_user_info_internal(doc.created_by) or {}
    enriched_signatories = await _enrich_signatories(doc.signatories, doc.signatures)
    
    sig_schemas = []
    for s in doc.signatures:
        u = await get_user_info_internal(s.user_id) or {}
        sig_schemas.append({
            "id": s.id, "document_id": s.document_id, "user_id": s.user_id,
            "signed_at": s.signed_at, "recommendation": s.recommendation,
            "note": s.note, "ip_address": s.ip_address, "mfa_verified": s.mfa_verified,
            "user_full_name": u.get("full_name")
        })

    return {
        "id": doc.id, "title": doc.title, "to_field": doc.to_field,
        "cc_field": doc.cc_field, "ref_field": doc.ref_field,
        "subject": doc.subject, "body": doc.body,
        "created_by": doc.created_by, "created_at": doc.created_at,
        "locked_at": doc.locked_at, "status": doc.status,
        "content_hash": doc.content_hash, "final_pdf_path": doc.final_pdf_path,
        "signatories": enriched_signatories,
        "signatures": sig_schemas,
        "creator_name": creator_info.get("full_name"),
    }


@router.put("/{document_id}")
async def update_document(
    document_id: str,
    request: Request,
    body: DocumentUpdateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Update a draft document. Only the creator can edit; only drafts can be edited."""
    user = await _verify_token(credentials)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.created_by != user["user_id"]:
        raise HTTPException(status_code=403, detail="Only the creator can edit this document")
    if doc.status != "draft":
        # Once sent for signing, the document is legally locked — no edits allowed
        raise HTTPException(status_code=403, detail="Cannot edit a document that is not in draft status")

    if body.title is not None: doc.title = body.title
    if body.to_field is not None: doc.to_field = body.to_field
    if body.cc_field is not None: doc.cc_field = body.cc_field
    if body.ref_field is not None: doc.ref_field = body.ref_field
    if body.subject is not None: doc.subject = body.subject
    if body.body is not None: doc.body = body.body

    db.commit()
    audit_log(db, "document_updated", _get_ip(request),
              document_id=doc.id, user_id=user["user_id"])

    return {"message": "Document updated", "id": doc.id}


@router.post("/{document_id}/signatories")
async def set_signatories(
    document_id: str,
    request: Request,
    body: List[SignatoryInput],
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Set the signatory list for a draft document. Replaces existing list."""
    user = await _verify_token(credentials)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.created_by != user["user_id"]:
        raise HTTPException(status_code=403, detail="Only creator can set signatories")
    if doc.status != "draft":
        raise HTTPException(status_code=403, detail="Cannot modify signatories after sending")

    # Validate no duplicate order indices
    order_indices = [s.order_index for s in body]
    if len(order_indices) != len(set(order_indices)):
        raise HTTPException(status_code=400, detail="Duplicate order indices not allowed")

    # Validate all signatories have registered signatures (prerequisite for sending)
    for sig_input in body:
        sig_data = await get_user_signature(sig_input.user_id)
        if not sig_data:
            raise HTTPException(
                status_code=400,
                detail=f"User {sig_input.user_id} has not registered a signature. "
                       "All signatories must register a signature before being added."
            )

    # Replace existing signatory list
    db.query(DocumentSignatory).filter(
        DocumentSignatory.document_id == document_id
    ).delete()

    for sig_input in body:
        s = DocumentSignatory(
            document_id=document_id,
            user_id=sig_input.user_id,
            order_index=sig_input.order_index,
            is_final_decision_maker=sig_input.is_final_decision_maker,
            status="waiting"
        )
        db.add(s)

    db.commit()
    audit_log(db, "signatories_set", _get_ip(request),
              document_id=doc.id, user_id=user["user_id"],
              metadata={"count": len(body)})

    return {"message": f"{len(body)} signatories set"}


@router.post("/{document_id}/send")
async def send_document(
    document_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Lock document and initiate signing workflow."""
    user = await _verify_token(credentials)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.created_by != user["user_id"]:
        raise HTTPException(status_code=403, detail="Only creator can send document")
    if doc.status != "draft":
        raise HTTPException(status_code=400, detail="Document is not in draft status")

    signatories = db.query(DocumentSignatory).filter(
        DocumentSignatory.document_id == document_id
    ).order_by(DocumentSignatory.order_index).all()

    if not signatories:
        raise HTTPException(status_code=400, detail="Add at least one signatory before sending")

    # Lock document: compute and store content hash at this exact moment
    # After this point, any change to the stored content fields will be detectable
    doc.content_hash = compute_content_hash(doc)
    doc.locked_at = datetime.utcnow()
    doc.status = "in_signing"

    # Set first signatory to 'pending', rest to 'waiting'
    # Sequential signing: each person must sign before the next is notified
    for i, sig in enumerate(signatories):
        sig.status = "pending" if i == 0 else "waiting"

    db.commit()
    audit_log(db, "document_sent_for_signing", _get_ip(request),
              document_id=doc.id, user_id=user["user_id"],
              metadata={"signatory_count": len(signatories), "content_hash": doc.content_hash})

    # Notify first signatory
    first_sig = signatories[0]
    creator_info = await get_user_info_internal(doc.created_by) or {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/notify/signatory",
                json={
                    "document_id": doc.id,
                    "signatory_user_id": first_sig.user_id,
                    "document_title": doc.title,
                    "creator_name": creator_info.get("full_name", "Unknown"),
                    "frontend_url": settings.FRONTEND_URL,
                },
                headers={"X-Internal-Key": settings.INTERNAL_API_KEY}
            )
        first_sig.notified_at = datetime.utcnow()
        db.commit()
    except Exception:
        pass  # Email failure must not block the sending workflow

    return {"message": "Document sent for signing", "status": "in_signing"}


@router.post("/{document_id}/recall")
async def recall_document(
    document_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Recall a document that's in signing (only if no signatures yet)."""
    user = await _verify_token(credentials)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.created_by != user["user_id"]:
        raise HTTPException(status_code=403, detail="Only creator can recall")
    if doc.status != "in_signing":
        raise HTTPException(status_code=400, detail="Can only recall documents that are in signing")

    existing_sigs = db.query(Signature).filter(Signature.document_id == document_id).count()
    if existing_sigs > 0:
        raise HTTPException(status_code=400, detail="Cannot recall — signatures have already been applied")

    doc.status = "recalled"
    db.commit()

    audit_log(db, "document_recalled", _get_ip(request),
              document_id=doc.id, user_id=user["user_id"])

    # Notify all signatories
    signatories = db.query(DocumentSignatory).filter(
        DocumentSignatory.document_id == document_id
    ).all()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/notify/recalled",
                json={
                    "document_id": doc.id,
                    "document_title": doc.title,
                    "signatory_user_ids": [s.user_id for s in signatories],
                },
                headers={"X-Internal-Key": settings.INTERNAL_API_KEY}
            )
    except Exception:
        pass

    return {"message": "Document recalled"}


@router.get("/{document_id}/audit")
async def get_audit_trail(
    document_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get the full audit trail for a document. Admin or creator only."""
    user = await _verify_token(credentials)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    is_creator = doc.created_by == user["user_id"]
    is_admin = "view_all_documents" in user.get("permissions", [])
    if not (is_creator or is_admin):
        raise HTTPException(status_code=403, detail="Audit trail access restricted to creator and admin")

    logs = db.query(AuditLog).filter(
        AuditLog.document_id == document_id
    ).order_by(AuditLog.timestamp.asc()).all()

    result = []
    for log in logs:
        user_info = await get_user_info_internal(log.user_id) if log.user_id else None
        result.append({
            "id": log.id,
            "document_id": log.document_id,
            "user_id": log.user_id,
            "action": log.action,
            "metadata": log.metadata_,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp,
            "user_name": user_info.get("full_name") if user_info else "System"
        })

    return result
