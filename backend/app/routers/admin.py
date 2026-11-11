"""Admin-only user management: list users, change role, activate / deactivate."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.models import Role, User
from app.schemas.auth import ActiveChange, RoleChange, UserResponse
from app.services.auth_service import DEFAULT_ROLES, ensure_default_roles, user_to_dict

router = APIRouter(prefix="/admin", tags=["Admin"])


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.get("/users", response_model=list[UserResponse], summary="List all users (admin only)")
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    users = db.query(User).order_by(User.id).all()
    return [user_to_dict(db, u) for u in users]


@router.get("/roles", summary="Available role names (admin only)")
def list_roles(_admin: User = Depends(require_role("admin"))):
    return list(DEFAULT_ROLES.keys())


@router.patch("/users/{user_id}/role", response_model=UserResponse, summary="Change a user's role (admin only)")
def change_role(
    user_id: int,
    payload: RoleChange,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    ensure_default_roles(db)
    new_name = payload.role.strip().lower()
    new_role = db.query(Role).filter(Role.name == new_name).first()
    if new_role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown role. Use one of: " + ", ".join(DEFAULT_ROLES.keys()) + ".",
        )
    user = _get_user_or_404(db, user_id)
    if user.id == admin.id and new_name != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin role.",
        )
    user.role_id = new_role.id
    db.commit()
    db.refresh(user)
    return user_to_dict(db, user)


@router.patch("/users/{user_id}/active", response_model=UserResponse, summary="Activate or deactivate a user (admin only)")
def change_active(
    user_id: int,
    payload: ActiveChange,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    user = _get_user_or_404(db, user_id)
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user_to_dict(db, user)
