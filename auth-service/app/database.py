"""
auth-service/app/database.py

SQLAlchemy engine and session factory for the auth service.
We use a single shared engine with connection pooling tuned for
FastAPI's async request patterns (pre_ping catches stale connections
that MySQL closes after wait_timeout).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings


# pre_ping=True: issue a cheap "SELECT 1" before using a pooled connection
# This prevents cryptic "MySQL server has gone away" errors on idle connections
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,  # Recycle connections every hour to avoid MySQL's 8h timeout
    echo=False,         # Set to True for SQL query debugging — never True in production
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_db():
    """
    FastAPI dependency that yields a database session.
    Uses a try/finally pattern to guarantee the session is closed
    even if an exception occurs — preventing connection pool exhaustion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
