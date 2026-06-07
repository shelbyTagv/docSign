"""
document-service/app/services/audit.py

Audit logging service for document events.
All entries are append-only (enforced by DB trigger in init.sql).
This module provides a clean interface for writing audit records
without directly coupling route handlers to the ORM model.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from ..models import AuditLog


def log(
    db: Session,
    action: str,
    ip_address: str,
    document_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> None:
    """
    Append an immutable audit log record.
    
    This function is the single point of entry for all audit writes.
    Using a dedicated function (rather than direct ORM calls) makes it
    easier to add structured logging, event streaming, or SIEM integration
    in the future without changing every call site.
    """
    entry = AuditLog(
        document_id=document_id,
        user_id=user_id,
        action=action,
        metadata_=metadata or {},
        ip_address=ip_address,
        # Server timestamp — never use datetime from request payload
        timestamp=datetime.utcnow()
    )
    db.add(entry)
    db.commit()  # Commit immediately — audit logs must persist even if the main tx fails
