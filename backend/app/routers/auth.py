from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_user
from app.db.session import get_db
from app.models.models import Role, User
from app.schemas.auth import UserRegister, UserResponse
from app.schemas.login import LoginRequest, LoginResponse
from app.services.auth_service import authenticate_user, register_user, user_to_dict

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    user = register_user(db, user_data)
    return user_to_dict(db, user)


@router.post("/login", response_model=LoginResponse)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db,
        credentials.email,
        credentials.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact an administrator.",
        )

    role = db.query(Role).filter(Role.id == user.role_id).first()
    role_name = role.name if role else "user"

    token = create_access_token(
        user_id=user.id,
        role=role_name,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "full_name": user.full_name,
        "role": role_name,
    }


@router.get("/me", response_model=UserResponse, summary="Profile and role of the logged-in user")
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_to_dict(db, current_user)
