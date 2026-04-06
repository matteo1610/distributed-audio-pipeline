"""Authentication service logic."""
from uuid import UUID

from passlib.context import CryptContext

from app.infrastructure.database import DatabaseConnection
from app.models.user import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Handles user registration and authentication."""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        """Verify plaintext password against hash."""
        return pwd_context.verify(plain_password, password_hash)

    def get_user_by_username(self, username: str) -> User | None:
        """Fetch a user by username."""
        row = self.db.fetch_one(
            """
            SELECT id, username, email, password_hash, role, is_active, created_at
            FROM users
            WHERE username = %s
            """,
            (username,),
        )
        if not row:
            return None

        return User(
            id=UUID(str(row[0])),
            username=row[1],
            email=row[2],
            password_hash=row[3],
            role=UserRole(str(row[4])),
            is_active=row[5],
            created_at=row[6],
        )

    def get_user_by_id(self, user_id: UUID) -> User | None:
        """Fetch a user by ID."""
        row = self.db.fetch_one(
            """
            SELECT id, username, email, password_hash, role, is_active, created_at
            FROM users
            WHERE id = %s
            """,
            (str(user_id),),
        )
        if not row:
            return None

        return User(
            id=UUID(str(row[0])),
            username=row[1],
            email=row[2],
            password_hash=row[3],
            role=UserRole(str(row[4])),
            is_active=row[5],
            created_at=row[6],
        )

    def register_user(self, username: str, email: str, password: str) -> User:
        """Register a new user."""
        password_hash = self.hash_password(password)
        row = self.db.fetch_one(
            """
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
            RETURNING id, username, email, password_hash, role, is_active, created_at
            """,
            (username, email, password_hash),
        )

        if not row:
            raise ValueError("Failed to create user")

        return User(
            id=UUID(str(row[0])),
            username=row[1],
            email=row[2],
            password_hash=row[3],
            role=UserRole(str(row[4])),
            is_active=row[5],
            created_at=row[6],
        )

    def authenticate_user(self, username: str, password: str) -> User | None:
        """Authenticate a user with username and password."""
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not user.is_active:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        return user
