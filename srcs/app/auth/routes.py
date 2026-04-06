"""Authentication HTTP routes."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

from app.auth.dependencies import get_current_user
from app.auth.jwt_handler import create_access_token
from app.auth.service import AuthService
from app.infrastructure.database import DatabaseConnection
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
_db = DatabaseConnection()
_auth_service = AuthService(_db)


class RegisterRequest(BaseModel):
    """User registration payload."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Safe public user response."""

    id: str
    username: str
    email: EmailStr


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest) -> UserResponse:
    """Register a new user account."""
    existing = _auth_service.get_user_by_username(payload.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = _auth_service.register_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
    )

    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
    )


@router.post("/login", response_model=TokenResponse)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
    """Authenticate user and issue JWT token."""
    user = _auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    """Get current authenticated user."""
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
    )
