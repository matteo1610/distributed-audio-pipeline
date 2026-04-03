"""User domain model."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID


class UserRole(Enum):
    """Supported user roles."""

    USER = "USER"
    ADMIN = "ADMIN"
    WORKER = "WORKER"


@dataclass
class User:
    """Represents an authenticated user."""

    id: UUID
    username: str
    email: str
    password_hash: str
    role: UserRole = UserRole.USER
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
