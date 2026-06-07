"""
auth-service/app/routes/roles.py

Role management endpoints — admin-only CRUD for roles.
Roles are referenced by document_signatories to determine signing authority.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Role, UserRole
from ..schemas import RoleSchema, RoleCreateRequest, AssignRoleRequest
from ..services import jwt as jwt_service
from ..middleware.rate_limit import limiter

router = APIRouter(prefix="/roles", tags=["Roles"])
security = HTTPBearer(auto_error=False)


def _require_admin(credentials, payload_key="manage_roles"):
    """Extract token and verify admin permission."""
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = jwt_service.verify_access_token(token)
    if not payload or payload_key not in payload.get("permissions", []):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return payload


@router.get("/", response_model=List[RoleSchema])
@limiter.limit("30/minute")
async def list_roles(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """List all available roles."""
    token = credentials.credentials if credentials else None
    if not token or not jwt_service.verify_access_token(token):
        raise HTTPException(status_code=401, detail="Authentication required")
    return db.query(Role).all()


@router.post("/", response_model=RoleSchema)
@limiter.limit("10/minute")
async def create_role(
    request: Request,
    body: RoleCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Admin only: create a new role."""
    _require_admin(credentials)
    
    if db.query(Role).filter(Role.name == body.name).first():
        raise HTTPException(status_code=409, detail=f"Role '{body.name}' already exists")
    
    role = Role(name=body.name, permissions=body.permissions)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.post("/{user_id}/assign")
@limiter.limit("10/minute")
async def assign_role_to_user(
    user_id: str,
    request: Request,
    body: AssignRoleRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Admin only: assign a role to a user."""
    payload = _require_admin(credentials)
    
    role = db.query(Role).filter(Role.id == body.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if assignment already exists to prevent duplicates
    existing = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == body.role_id
    ).first()
    
    if existing:
        return {"message": "Role already assigned"}
    
    user_role = UserRole(
        user_id=user_id,
        role_id=body.role_id,
        assigned_by=payload["sub"]
    )
    db.add(user_role)
    db.commit()
    
    return {"message": f"Role '{role.name}' assigned to user {user_id}"}
