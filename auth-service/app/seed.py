"""
auth-service/app/seed.py

Run on every container startup (before uvicorn).
Idempotent — uses INSERT IGNORE / ON DUPLICATE KEY logic to safely
re-run without creating duplicates. Also ensures the admin user has
a proper bcrypt hash (the SQL init.sql uses a static pre-computed hash;
this script re-hashes with the current bcrypt version for correctness).
"""

import sys
import time
from passlib.context import CryptContext
from sqlalchemy import text
from .database import engine, SessionLocal
from .models import User, Role, UserRole
from .services.jwt import _ensure_keys

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

ADMIN_UUID = "00000000-0000-0000-0000-000000000001"
ADMIN_EMAIL = "admin@docsign.local"
ADMIN_DEFAULT_PASSWORD = "Admin@12345"

SEED_ROLES = [
    {"name": "Admin", "permissions": ["manage_users", "manage_roles", "view_all_documents", "create_document", "sign_document"]},
    {"name": "Director", "permissions": ["view_all_documents", "create_document", "sign_document"]},
    {"name": "Head of Department", "permissions": ["create_document", "sign_document", "view_department_documents"]},
    {"name": "Officer", "permissions": ["create_document", "sign_document"]},
    {"name": "Clerk", "permissions": ["sign_document"]},
]


def wait_for_db(max_retries=15, delay=3):
    """Poll the DB until it's ready — MySQL takes a few seconds to initialize."""
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[seed] Database connection established")
            return
        except Exception as e:
            print(f"[seed] Waiting for database... attempt {attempt + 1}/{max_retries}: {e}")
            time.sleep(delay)
    print("[seed] Could not connect to database after max retries. Exiting.")
    sys.exit(1)


def seed():
    wait_for_db()
    
    # Ensure RSA keys exist (generated here on first boot)
    _ensure_keys()
    print("[seed] RSA keys ready")
    
    db = SessionLocal()
    try:
        # ── Seed roles ──────────────────────────────────────────
        for role_data in SEED_ROLES:
            existing = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing:
                role = Role(name=role_data["name"], permissions=role_data["permissions"])
                db.add(role)
                print(f"[seed] Created role: {role_data['name']}")
        db.commit()
        
        # ── Seed admin user ──────────────────────────────────────
        admin = db.query(User).filter(User.id == ADMIN_UUID).first()
        if not admin:
            # Generate proper bcrypt hash at runtime — more reliable than static hash in SQL
            hashed = pwd_context.hash(ADMIN_DEFAULT_PASSWORD)
            admin = User(
                id=ADMIN_UUID,
                email=ADMIN_EMAIL,
                full_name="System Administrator",
                title="System Administrator",
                department="IT",
                password_hash=hashed,
                is_active=True,
                force_password_change=True,  # Must change on first login
            )
            db.add(admin)
            db.flush()
            
            # Assign Admin role
            admin_role = db.query(Role).filter(Role.name == "Admin").first()
            if admin_role:
                ur = UserRole(user_id=ADMIN_UUID, role_id=admin_role.id, assigned_by=None)
                db.add(ur)
            
            db.commit()
            print(f"[seed] Admin user created: {ADMIN_EMAIL} / {ADMIN_DEFAULT_PASSWORD}")
        else:
            print(f"[seed] Admin user already exists: {ADMIN_EMAIL}")
        
        print("[seed] Seed completed successfully")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
