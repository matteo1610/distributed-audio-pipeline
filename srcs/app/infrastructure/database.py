"""Database connection management."""
import os
from typing import Generator

import psycopg


class DatabaseConnection:
    """Manages PostgreSQL database connections."""

    def __init__(self, db_url: str | None = None):
        """Initialize database connection manager.
        
        Args:
            db_url: Database URL. If None, reads from DATABASE_URL env var.
        """
        self.db_url = db_url or os.getenv(
            "DATABASE_URL", "postgresql://app:app@postgres:5432/audio_pipeline"
        )

    def get_connection(self) -> psycopg.Connection:
        """Get a new database connection.
        
        Returns:
            A new PostgreSQL connection.
            
        Raises:
            psycopg.Error: If connection fails.
        """
        return psycopg.connect(self.db_url)

    def execute_query(self, query: str, params: tuple = ()) -> None:
        """Execute a query without returning results.
        
        Args:
            query: SQL query to execute.
            params: Query parameters.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
            conn.commit()

    def fetch_one(self, query: str, params: tuple = ()):
        """Fetch a single row.
        
        Args:
            query: SQL query to execute.
            params: Query parameters.
            
        Returns:
            First row or None.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()

    def fetch_all(self, query: str, params: tuple = ()):
        """Fetch all rows.
        
        Args:
            query: SQL query to execute.
            params: Query parameters.
            
        Returns:
            List of rows.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def is_healthy(self) -> bool:
        """Check database health.
        
        Returns:
            True if database is accessible, False otherwise.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception:
            return False
