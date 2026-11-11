
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.models import Role, User


ALGORITHM = "HS256"

bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user_id: int, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the logged-in user, or raise 401."""

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_error

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id = int(payload.get("sub"))
    except (InvalidTokenError, TypeError, ValueError):
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()

    if user is None or not user.is_active:
        raise credentials_error

    role = db.query(Role).filter(Role.id == user.role_id).first()
    user.role_name = role.name if role else "user"

    return user


def require_role(*allowed_roles: str):
    """Use as: Depends(require_role("admin")). Wrong role -> 403."""

    allowed = {name.lower() for name in allowed_roles}

    def checker(current_user: User = Depends(get_current_user)) -> User:
        role_name = str(getattr(current_user, "role_name", "") or "").lower()

        if role_name not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to do this.",
            )

        return current_user

    return checker
