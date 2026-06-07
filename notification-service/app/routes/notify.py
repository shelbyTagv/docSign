"""
notification-service/app/routes/notify.py

Notification endpoints called by other services (document-service, auth-service).
All endpoints require the X-Internal-Key header — external callers are rejected.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

from ..services.mailer import (
    send_signatory_notification, send_completion_notification,
    send_recall_notification, send_welcome_email, send_reminder_email
)
from ..config import settings

router = APIRouter(prefix="/notify", tags=["Notifications"])


def _require_internal(key: Optional[str]):
    if key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Internal access only")


class SignatoryNotifyRequest(BaseModel):
    document_id: str
    signatory_user_id: str
    document_title: str
    creator_name: str
    signatory_email: Optional[str] = None
    signatory_name: Optional[str] = None
    frontend_url: Optional[str] = None


class CompletedNotifyRequest(BaseModel):
    document_id: str
    document_title: str
    recipient_emails: List[str]
    pdf_path: Optional[str] = None
    frontend_url: Optional[str] = None


class RecalledNotifyRequest(BaseModel):
    document_id: str
    document_title: str
    signatory_user_ids: List[str]
    signatory_emails: Optional[List[str]] = None
    recalled_by: Optional[str] = "Document Creator"


class ReminderRequest(BaseModel):
    document_id: str
    document_title: str
    signatory_email: str
    signatory_name: str
    frontend_url: Optional[str] = None


class WelcomeRequest(BaseModel):
    user_email: str
    full_name: str
    temp_password: str


@router.post("/signatory")
async def notify_signatory(
    body: SignatoryNotifyRequest,
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key")
):
    """Notify a signatory that it's their turn to sign."""
    _require_internal(x_internal_key)
    
    # Use provided email/name or generate placeholders
    # In a full implementation, document-service would always include these
    to_email = body.signatory_email or f"user-{body.signatory_user_id}@docsign.local"
    name = body.signatory_name or "Signatory"
    frontend_url = body.frontend_url or settings.FRONTEND_URL
    
    success = await send_signatory_notification(
        to_email=to_email,
        signatory_name=name,
        document_title=body.document_title,
        creator_name=body.creator_name,
        document_id=body.document_id,
        frontend_url=frontend_url
    )
    
    return {"sent": success, "recipient": to_email}


@router.post("/completed")
async def notify_completed(
    body: CompletedNotifyRequest,
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key")
):
    """Send final signed document PDF to all recipients."""
    _require_internal(x_internal_key)
    
    if not body.recipient_emails:
        return {"sent": False, "reason": "No recipients"}
    
    frontend_url = body.frontend_url or settings.FRONTEND_URL
    
    success = await send_completion_notification(
        to_emails=body.recipient_emails,
        document_title=body.document_title,
        pdf_path=body.pdf_path,
        document_id=body.document_id,
        frontend_url=frontend_url
    )
    
    return {"sent": success, "recipients": len(body.recipient_emails)}


@router.post("/recalled")
async def notify_recalled(
    body: RecalledNotifyRequest,
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key")
):
    """Notify all signatories that a document was recalled."""
    _require_internal(x_internal_key)
    
    emails = body.signatory_emails or []
    if not emails:
        return {"sent": False, "reason": "No email addresses provided"}
    
    success = await send_recall_notification(
        to_emails=emails,
        document_title=body.document_title,
        recalled_by=body.recalled_by or "Document Creator"
    )
    
    return {"sent": success}


@router.post("/reminder")
async def notify_reminder(
    body: ReminderRequest,
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key")
):
    """Send a reminder to a signatory who hasn't signed after 48 hours."""
    _require_internal(x_internal_key)
    
    frontend_url = body.frontend_url or settings.FRONTEND_URL
    
    success = await send_reminder_email(
        to_email=body.signatory_email,
        signatory_name=body.signatory_name,
        document_title=body.document_title,
        document_id=body.document_id,
        frontend_url=frontend_url
    )
    
    return {"sent": success}


@router.post("/welcome")
async def notify_welcome(
    body: WelcomeRequest,
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key")
):
    """Send welcome email to a newly created user."""
    _require_internal(x_internal_key)
    
    success = await send_welcome_email(
        to_email=body.user_email,
        full_name=body.full_name,
        temp_password=body.temp_password
    )
    
    return {"sent": success}
