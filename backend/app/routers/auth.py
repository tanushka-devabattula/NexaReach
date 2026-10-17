
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.models.models import Role
from app.schemas.auth import UserRegister, UserResponse
from app.schemas.login import LoginRequest, LoginResponse
from app.services.auth_service import authenticate_user, register_user

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
    return register_user(db, user_data)


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

    role = db.query(Role).filter(Role.id == user.role_id).first()
    role_name = role.name if role else "user"

    token = create_access_token(
        user_id=user.id,
        role=role_name,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }
