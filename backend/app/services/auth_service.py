
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from pwdlib import PasswordHash

from app.models.models import User, Role
from app.schemas.auth import UserRegister

password_hash = PasswordHash.recommended()


DEFAULT_ROLES = {
    "admin": "Administrator: full access, manages users",
    "campaign_manager": "Campaign Manager: audience, segments, campaigns, sending",
    "communication_team": "Communication Team: creates and reviews content",
    "user": "Standard registered user",
}


def ensure_default_roles(db: Session) -> None:
    """Create the default roles if they are missing (safe to run many times)."""
    changed = False
    for name, description in DEFAULT_ROLES.items():
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name, description=description))
            changed = True
    if changed:
        db.commit()


def user_to_dict(db: Session, user: User) -> dict:
    role = db.query(Role).filter(Role.id == user.role_id).first()
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "organization": user.organization,
        "role_id": user.role_id,
        "role": role.name if role else None,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }


def register_user(db: Session, user_data: UserRegister) -> User:
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    ensure_default_roles(db)
    user_role = db.query(Role).filter(Role.name == user_data.role).first()

    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        organization=user_data.organization,
        hashed_password=password_hash.hash(user_data.password),
        role_id=user_role.id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()

    if not user or not password_hash.verify(
        password, user.hashed_password
    ):
        return None

    # Deactivated accounts are rejected by the login route with a clear message.
    return user
