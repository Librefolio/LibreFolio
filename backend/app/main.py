"""
LibreFolio FastAPI application.
Main entry point for the backend API.
"""
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import router as api_v1_router
from backend.app.config import get_settings, set_test_mode, is_test_mode
from backend.app.logging_config import configure_logging, get_logger

# Check for --test flag in command line arguments
# This must be done before any imports that might use settings
if "--test" in sys.argv:
    set_test_mode(True)
    print("[LibreFolio] 🧪 Test mode enabled (--test flag detected)")
    sys.argv.remove("--test")  # Remove flag so uvicorn doesn't complain

# Get settings after test mode is set
settings = get_settings()

# Configure logging with settings
configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


def ensure_database_exists():
    """
    Ensure database exists and is migrated.
    If database file doesn't exist OR is empty, run migrations automatically.

    This function is used by:
    - Backend server on startup (via lifespan)
    - Test scripts (db_schema_validate, populate_db)
    """
    # Get settings at call time to respect test mode
    settings = get_settings()

    # Extract database path from DATABASE_URL
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path_str = db_url.replace("sqlite:///", "")

        # Handle relative paths
        if not db_path_str.startswith("/"):
            # Relative path - resolve from project root
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / db_path_str
        else:
            db_path = Path(db_path_str)

        needs_migration = False

        if not db_path.exists():
            logger.warning(
                "Database file not found, running migrations",
                db_path=str(db_path)
                )
            needs_migration = True
        elif db_path.stat().st_size == 0:
            logger.warning(
                "Database file is empty (0 bytes), running migrations",
                db_path=str(db_path)
                )
            needs_migration = True
        else:
            # Check if database has tables using SQLite directly
            # This is faster than importing SQLAlchemy
            import sqlite3
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                table_count = cursor.fetchone()[0]
                conn.close()

                if table_count == 0:
                    logger.warning(
                        "Database has no tables, running migrations",
                        db_path=str(db_path)
                        )
                    needs_migration = True
                else:
                    logger.info(
                        f"Database initialized with {table_count} tables",
                        db_path=str(db_path)
                        )
            except sqlite3.DatabaseError as e:
                logger.warning(
                    f"Database appears corrupted, running migrations: {e}",
                    db_path=str(db_path)
                    )
                needs_migration = True

        if needs_migration:
            # Ensure directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Run Alembic migrations
            try:
                project_root = Path(__file__).parent.parent.parent
                alembic_ini = project_root / "backend" / "alembic.ini"

                logger.info("Running Alembic migrations...")
                result = subprocess.run(
                    ["alembic", "-c", str(alembic_ini), "upgrade", "head"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    )

                if result.returncode == 0:
                    logger.info("Database created and migrated successfully")
                else:
                    logger.error(
                        "Failed to create database",
                        stderr=result.stderr
                        )
                    sys.exit(1)

            except Exception as e:
                logger.error("Error creating database", error=str(e))
                sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "Starting LibreFolio",
        version=settings.VERSION,
        database_url=settings.DATABASE_URL.split("///")[-1],  # Hide full path in logs
        test_mode=is_test_mode(),
        )

    # Ensure database exists and is migrated
    ensure_database_exists()

    yield
    # Shutdown
    logger.info("Shutting down LibreFolio")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

# Mount API v1 router
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """
    Root endpoint.
    Provides basic API information.
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs",
        }
