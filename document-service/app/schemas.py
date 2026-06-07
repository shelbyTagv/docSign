"""
document-service/app/schemas.py

Pydantic schemas for the document service API.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    draft = "draft"
    in_signing = "in_signing"
    completed = "completed"
    recalled = "recalled"


class SignatoryStatus(str, Enum):
    pending = "pending"
    signed = "signed"
    recommended = "recommended"
    not_recommended = "not_recommended"
    waiting = "waiting"


class RecommendationEnum(str, Enum):
    recommended = "recommended"
    not_recommended = "not_recommended"
    none = "none"


# ─── Document Schemas ─────────────────────────────────────────────────────────

class DocumentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    to_field: str = Field(..., min_length=1)
    cc_field: Optional[str] = None
    ref_field: Optional[str] = None
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    to_field: Optional[str] = None
    cc_field: Optional[str] = None
    ref_field: Optional[str] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    body: Optional[str] = None


class SignatoryInput(BaseModel):
    user_id: str
    order_index: int = Field(..., ge=1)
    is_final_decision_maker: bool = False


class SignatorySchema(BaseModel):
    id: int
    document_id: str
    user_id: str
    order_index: int
    is_final_decision_maker: bool
    status: SignatoryStatus
    recommendation_note: Optional[str]
    notified_at: Optional[datetime]
    # User info populated from auth-service lookup
    user_full_name: Optional[str] = None
    user_email: Optional[str] = None
    user_title: Optional[str] = None
    user_department: Optional[str] = None
    # Signature info if signed
    signed_at: Optional[datetime] = None
    signature_image_base64: Optional[str] = None

    class Config:
        from_attributes = True


class SignatureSchema(BaseModel):
    id: str
    document_id: str
    user_id: str
    signed_at: datetime
    recommendation: RecommendationEnum
    note: Optional[str]
    ip_address: str
    mfa_verified: bool
    user_full_name: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    id: str
    title: str
    to_field: str
    cc_field: Optional[str]
    ref_field: Optional[str]
    subject: str
    body: str
    created_by: str
    created_at: datetime
    locked_at: Optional[datetime]
    status: DocumentStatus
    content_hash: Optional[str]
    final_pdf_path: Optional[str]
    signatories: List[SignatorySchema] = []
    signatures: List[SignatureSchema] = []
    creator_name: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    id: str
    title: str
    subject: str
    status: DocumentStatus
    created_at: datetime
    created_by: str
    creator_name: Optional[str] = None
    signatory_count: int = 0
    my_signatory_status: Optional[SignatoryStatus] = None

    class Config:
        from_attributes = True


# ─── Signing Schemas ──────────────────────────────────────────────────────────

class SignRequest(BaseModel):
    recommendation: RecommendationEnum = RecommendationEnum.none
    note: Optional[str] = None


# ─── Audit Schemas ────────────────────────────────────────────────────────────

class AuditLogSchema(BaseModel):
    id: int
    document_id: Optional[str]
    user_id: Optional[str]
    action: str
    metadata_: Optional[dict]
    ip_address: str
    timestamp: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True
