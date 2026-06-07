"""
auth-service/app/models.py

SQLAlchemy ORM models for the auth service.
These map to the MySQL tables defined in mysql/init.sql.
We define them here independently rather than sharing a codebase
so each microservice can evolve its schema view independently.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Integer,
    ForeignKey, JSON, LargeBinary, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from .database import Base


def generate_uuid() -> str:
    """Generate a new UUID4 string. Used as default for PK columns."""
    return str(uuid.uuid4())


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    # JSON list of permission strings — stored as JSON in MySQL
    permissions = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user_roles = relationship("UserRole", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255))
    title = Column(String(100))         # Job title e.g. "Head of Finance"
    department = Column(String(100))
    password_hash = Column(Text, nullable=False)
    # Fernet-encrypted TOTP secret — encrypted before storage so a DB breach
    # alone cannot compromise MFA codes
    mfa_secret = Column(Text, nullable=True)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    # RSA+Fernet encrypted PNG bytes of the user's drawn signature
    signature_encrypted = Column(LargeBinary, nullable=True)
    # Stores key derivation metadata (e.g., which version of master key was used)
    signature_iv = Column(Text, nullable=True)
    # True once the user has verified identity by registering a signature with MFA
    identity_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    # Admin-created accounts must change their temp password on first login
    force_password_change = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_roles = relationship("UserRole", foreign_keys="UserRole.user_id", back_populates="user")


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    assigned_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class AuditLog(Base):
    """
    Append-only audit log — MySQL triggers prevent UPDATE and DELETE.
    This model is intentionally write-once in both the DB and the ORM.
    Never call session.delete() or session.merge() on these records.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(36), nullable=True)  # No FK — document may be from another service
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)  # 'metadata' is reserved in SQLAlchemy
    ip_address = Column(String(45), nullable=False, default="0.0.0.0")
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
