"""
document-service/app/models.py

ORM models for the document service. Shares the same MySQL DB as auth-service
but only defines tables relevant to documents. Foreign keys to users table
are present but the User model is not defined here — we treat user records
as opaque UUIDs resolved via internal API calls to auth-service.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Integer,
    ForeignKey, JSON, LargeBinary, Enum as SAEnum, BigInteger, CHAR
)
from sqlalchemy.orm import relationship
from .database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    title = Column(String(255), nullable=False)
    to_field = Column(Text, nullable=False)
    cc_field = Column(Text, nullable=True)
    ref_field = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    created_by = Column(String(36), nullable=False)  # User UUID from auth-service
    # Server-generated timestamp — NEVER accept from client for legal documents
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    locked_at = Column(DateTime, nullable=True)
    status = Column(
        SAEnum("draft", "in_signing", "completed", "recalled"),
        nullable=False,
        default="draft"
    )
    content_hash = Column(String(64), nullable=True)  # SHA-256 of content at lock time
    final_pdf_path = Column(Text, nullable=True)
    pdf_hash = Column(String(64), nullable=True)  # SHA-256 of PDF bytes for authenticity

    signatories = relationship(
        "DocumentSignatory",
        back_populates="document",
        order_by="DocumentSignatory.order_index"
    )
    signatures = relationship("Signature", back_populates="document")
    audit_logs = relationship("AuditLog", back_populates="document")


class DocumentSignatory(Base):
    __tablename__ = "document_signatories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), nullable=False)
    order_index = Column(Integer, nullable=False)
    is_final_decision_maker = Column(Boolean, nullable=False, default=False)
    status = Column(
        SAEnum("pending", "signed", "recommended", "not_recommended", "waiting"),
        nullable=False,
        default="waiting"
    )
    recommendation_note = Column(Text, nullable=True)
    notified_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="signatories")


class Signature(Base):
    __tablename__ = "signatures"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    user_id = Column(String(36), nullable=False)
    # Server timestamp — legal document signing time must always be server-authoritative
    signed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # Snapshot of the signature image at time of signing.
    # Even if the user later updates their signature, historical signed documents
    # preserve the signature exactly as it appeared when they signed.
    signature_image_snapshot = Column(LargeBinary, nullable=False)
    recommendation = Column(
        SAEnum("recommended", "not_recommended", "none"),
        nullable=False,
        default="none"
    )
    note = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(Text, nullable=True)
    mfa_verified = Column(Boolean, nullable=False, default=False)

    document = relationship("Document", back_populates="signatures")


class AuditLog(Base):
    """
    Local copy of audit logs for document events.
    Immutable at DB level via MySQL triggers defined in init.sql.
    """
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    ip_address = Column(String(45), nullable=False, default="0.0.0.0")
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    document = relationship("Document", back_populates="audit_logs")
