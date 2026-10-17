
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from pwdlib import PasswordHash

from app.models.models import User, Role
from app.schemas.auth import UserRegister

password_hash = PasswordHash.recommended()


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

    user_role = (
        db.query(Role)
        .filter(Role.name == "user")
        .first()
    )

    if not user_role:
        user_role = Role(
            name="user",
            description="Standard registered user",
        )
        db.add(user_role)
        db.flush()

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

    if not user.is_active:
        return None

    return user
