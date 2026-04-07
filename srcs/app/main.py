"""Main FastAPI application."""
import logging
import time
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.api.routes import router
from app.auth.routes import router as auth_router
from app.infrastructure.broker import RabbitMQBroker
from app.infrastructure.database import DatabaseConnection
from app.infrastructure.storage import MinIOStorage

logger = logging.getLogger(__name__)

# Initialize infrastructure components
_db = DatabaseConnection()
_storage = MinIOStorage()
_broker = RabbitMQBroker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown.
    
    Args:
        app: FastAPI application instance.
    """
    # Startup
    logger.info("Starting up application")

    # Wait for database to be ready
    logger.info("Waiting for database...")
    for attempt in range(20):
        try:
            if _db.is_healthy():
                logger.info("Database is ready")
                break
        except Exception as exc:
            if attempt < 19:
                time.sleep(1)
            else:
                logger.error(f"Failed to connect to database: {exc}")
                raise

    # Ensure MinIO bucket exists
    logger.info("Setting up MinIO...")
    try:
        _storage.ensure_bucket_exists()
        logger.info("MinIO bucket is ready")
    except Exception as exc:
        logger.error(f"Failed to setup MinIO: {exc}")
        raise

    # Check broker connection
    logger.info("Checking RabbitMQ...")
    if _broker.is_healthy():
        logger.info("RabbitMQ is ready")
    else:
        logger.warning("RabbitMQ connection check failed, continuing anyway")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI instance.
    """
    app = FastAPI(
        title="Distributed Audio Pipeline API",
        description="API for distributed audio file processing",
        version="0.1.0",
        lifespan=lifespan,
    )

    frontend_origins = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080",
    )
    allow_origins = [origin.strip() for origin in frontend_origins.split(",") if origin.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(router)
    app.include_router(auth_router)

    @app.get("/health")
    def health() -> dict:
        """Health check endpoint.
        
        Returns:
            Health status.
        """
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics() -> Response:
        """Prometheus metrics endpoint.
        
        Returns:
            Prometheus metrics.
        """
        return Response(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    return app


def main() -> None:
    """Run API server entrypoint."""
    import uvicorn

    app = create_app()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
