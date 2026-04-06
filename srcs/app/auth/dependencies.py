"""Authentication dependencies for FastAPI routes."""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.auth.jwt_handler import decode_access_token
from app.auth.service import AuthService
from app.infrastructure.database import DatabaseConnection
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
_db = DatabaseConnection()
_auth_service = AuthService(_db)


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """Resolve current user from bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    sub = payload.get("sub")
    if not sub:
        raise credentials_exception

    try:
        user_id = UUID(str(sub))
    except ValueError as exc:
        raise credentials_exception from exc

    user = _auth_service.get_user_by_id(user_id)
    if not user:
        raise credentials_exception

    return user
