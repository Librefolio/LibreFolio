"""
LibreFolio FastAPI application.
Main entry point for the backend API.
"""

import asyncio
import contextlib
import os
import sqlite3
import subprocess
import sys
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

# Suppress pycountry warnings about duplicate currency names (leone, bolívar soberano)
# These are ISO 4217 duplicates (old SLL + new SLE, old VEF + new VES) — harmless.
warnings.filterwarnings("ignore", message=".*already taken in index.*")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.router import router as api_v1_router
from backend.app.config import (
    API_V1_PREFIX,
    PROJECT_NAME,
    PROJECT_ROOT,
    ensure_data_dirs,
    get_settings,
    get_version,
    is_test_mode,
    set_test_mode,
)
from backend.app.db.session import get_async_engine
from backend.app.logging_config import configure_logging, get_logger
from backend.app.services.brim_parse_pool import shutdown_pool as shutdown_brim_parse_pool
from backend.app.services.provider_registry import (
    AssetProviderRegistry,
    BRIMProviderRegistry,
    FXProviderRegistry,
    SignalPluginRegistry,
)
from backend.app.services.risk.quant.workers import (
    shutdown_quant_worker_pools,
)
from backend.app.services.risk.scenario_catalog import (
    initialize_risk_scenario_catalog,
)
from backend.app.services.scheduler import get_shutdown_event, scheduler_loop
from backend.app.services.settings_service import initialize_global_settings
from backend.app.services.signal_runtime import validate_signal_runtime
from backend.app.services.static_uploads import seed_default_avatars
from backend.app.utils.cache_utils import close_all_caches
from backend.app.utils.version import get_git_version

# Check for test mode via environment variable ONLY
# NOTE: Do NOT check sys.argv here - it causes issues when this module is imported
# by other scripts (like test_runner). The --test flag is handled by dev.py which
# sets LIBREFOLIO_TEST_MODE env var before starting uvicorn.
if os.environ.get("LIBREFOLIO_TEST_MODE", "").lower() in ("1", "true", "yes"):
    set_test_mode(True)
    print("[LibreFolio] 🧪 Test mode enabled (LIBREFOLIO_TEST_MODE env var)")

# Get settings after test mode is set
settings = get_settings()

# Configure logging with settings
configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)
_background_tasks: set[asyncio.Task] = set()


def _alembic_head_revision():
    """Return the head revision id from the migration scripts, or None on error.

    Read in-process (no subprocess) so the hot-reload dev loop can cheaply tell
    whether an existing DB is already at head and skip the `alembic upgrade`
    subprocess when there is nothing to apply.
    """
    try:
        from alembic.config import Config  # noqa: PLC0415 — startup-only, keep alembic out of app import scope
        from alembic.script import ScriptDirectory  # noqa: PLC0415 — startup-only

        alembic_ini = PROJECT_ROOT / "backend" / "alembic.ini"
        return ScriptDirectory.from_config(Config(str(alembic_ini))).get_current_head()
    except Exception as e:
        logger.warning(f"Could not determine Alembic head revision: {e}")
        return None


def ensure_database_exists():
    """
    Ensure database exists and is migrated.

    Creates the schema from scratch when the DB file is missing/empty/corrupted,
    AND applies any pending migrations when an existing DB is behind the latest
    revision (e.g. a released install upgraded over an existing data volume, or a
    dev DB opened after a new migration was added). `alembic upgrade head` only
    runs when there is actually something to do.

    This function is used by:
    - Backend server on startup (via lifespan) — covers both `./dev.py server`
      and the Docker image, since both launch the app.
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
            db_path = PROJECT_ROOT / db_path_str
        else:
            db_path = Path(db_path_str)

        needs_migration = False  # DB must be created from scratch (missing/empty/no-tables/corrupt)
        pending_migration = False  # DB exists with a schema but is behind the latest revision

        if not db_path.exists():
            logger.warning("Database file not found, running migrations", db_path=str(db_path))
            needs_migration = True
        elif db_path.stat().st_size == 0:
            logger.warning("Database file is empty (0 bytes), running migrations", db_path=str(db_path))
            needs_migration = True
        else:
            # Check if database has tables using SQLite directly

            try:
                # closing() rather than a bare connect: the close used to sit at the
                # end of the try, so the corruption branch below — the one branch
                # that is *expected* to fire — skipped it and leaked a handle to the
                # very file it was about to rebuild.
                with contextlib.closing(sqlite3.connect(str(db_path))) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                    table_count = cursor.fetchone()[0]

                    if table_count == 0:
                        logger.warning("Database has no tables, running migrations", db_path=str(db_path))
                        needs_migration = True
                    else:
                        # DB already has a schema. Compare its current Alembic revision
                        # against the head revision in the migration scripts: if they
                        # differ, migrations were added since this DB was last opened and
                        # must be applied now. Skipping this is exactly what let a stale
                        # DB (still at 001 while 002 was pending) reach the app and crash
                        # on the first query touching a changed column.
                        try:
                            cursor.execute("SELECT version_num FROM alembic_version LIMIT 1")
                            row = cursor.fetchone()
                            db_rev = row[0] if row else None
                        except sqlite3.DatabaseError:
                            db_rev = None  # no alembic_version table

                        head_rev = _alembic_head_revision()
                        if head_rev is not None and db_rev is not None and db_rev != head_rev:
                            logger.warning(
                                "Database schema is behind head, applying pending migrations",
                                db_path=str(db_path),
                                db_revision=db_rev,
                                head_revision=head_rev,
                            )
                            pending_migration = True
                        elif db_rev is None:
                            logger.warning(
                                "Database has tables but no alembic_version row; leaving schema as-is",
                                db_path=str(db_path),
                            )
                        else:
                            logger.info(
                                f"Database initialized with {table_count} tables (schema up to date)",
                                db_path=str(db_path),
                            )

            except sqlite3.DatabaseError as e:
                logger.warning(f"Database appears corrupted, running migrations: {e}", db_path=str(db_path))
                needs_migration = True

        if needs_migration or pending_migration:
            if needs_migration:
                # Ensure directory exists before creating a brand-new DB file
                db_path.parent.mkdir(parents=True, exist_ok=True)

            # Run Alembic migrations (idempotent upgrade to head)
            try:
                alembic_ini = PROJECT_ROOT / "backend" / "alembic.ini"

                logger.info("Running Alembic migrations (upgrade head)...")
                result = subprocess.run(
                    ["alembic", "-c", str(alembic_ini), "upgrade", "head"],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    logger.info("Database schema is up to date")
                else:
                    logger.error("Failed to apply database migrations", stderr=result.stderr)
                    sys.exit(1)

            except Exception as e:
                logger.error("Error applying database migrations", error=str(e))
                sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    git_version = get_git_version()
    logger.info(
        "Starting LibreFolio",
        version=git_version,
        database_url=settings.DATABASE_URL.split("///")[-1],  # Hide full path in logs
        test_mode=is_test_mode(),
    )

    signal_runtime = validate_signal_runtime()
    SignalPluginRegistry.auto_discover()
    logger.info(
        "Signal plugin runtime ready",
        pandas_ta_classic_version=signal_runtime.pandas_ta_classic_version,
        talib_version=signal_runtime.talib_version,
        plugin_count=len(SignalPluginRegistry.list_plugin_codes()),
    )

    # Ensure all data directories exist (prod or test based on mode)
    ensure_data_dirs()

    scenario_catalog = await initialize_risk_scenario_catalog()
    logger.info(
        "Risk scenario catalog ready",
        built_in_count=scenario_catalog.status.built_in_count,
        host_count=scenario_catalog.status.host_count,
        warning_count=scenario_catalog.status.warning_count,
    )

    # Seed default avatar images on first startup
    seeded = seed_default_avatars()
    if seeded > 0:
        logger.info(f"Seeded {seeded} default avatar(s) into static resources")

    # Ensure database exists and is migrated
    ensure_database_exists()

    # Initialize global settings with defaults (if not already present)
    await _initialize_global_settings()

    # Pre-warm provider caches in background (non-blocking)
    provider_prewarm_task = asyncio.create_task(_prewarm_provider_caches())
    _background_tasks.add(provider_prewarm_task)
    provider_prewarm_task.add_done_callback(_background_tasks.discard)

    # Start scheduler daemon
    shutdown_event = get_shutdown_event()
    scheduler_task = asyncio.create_task(scheduler_loop(shutdown_event))

    yield
    # Shutdown — stop scheduler first, then cleanup providers
    logger.info("Shutting down LibreFolio")
    shutdown_event.set()
    await scheduler_task

    AssetProviderRegistry.shutdown_all_providers()
    FXProviderRegistry.shutdown_all_providers()
    BRIMProviderRegistry.shutdown_all_providers()
    # wait=True: releasing the parse workers has to actually happen here. The
    # runner escalates to SIGKILL after a grace period, and a SIGKILL skips the
    # atexit handler that would otherwise join them — the workers then survive,
    # re-parented to init, holding the stdout they inherited. Nothing is running
    # at this point anyway: uvicorn has already drained in-flight requests, and
    # a parse only exists inside one.
    shutdown_brim_parse_pool(wait=True)
    await shutdown_quant_worker_pools()

    # Close all TTL caches (stop timer wheel threads for clean exit)
    close_all_caches()


async def _initialize_global_settings():
    """Initialize global settings with default values if not present."""
    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        created = await initialize_global_settings(session)
        if created > 0:
            logger.info(f"Initialized {created} global setting(s)")


async def _prewarm_provider_caches():
    """Pre-warm provider instances and their caches in background."""
    try:
        for provider_info in AssetProviderRegistry.list_providers():
            code = provider_info["code"]
            AssetProviderRegistry.get_provider_instance(code)
        logger.debug("Provider caches pre-warmed successfully")
    except Exception as e:
        logger.warning(f"Provider cache pre-warm failed (non-blocking): {e}")


# Create FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    version=get_version(),
    openapi_url=f"{API_V1_PREFIX}/openapi.json",
    docs_url=f"{API_V1_PREFIX}/docs",
    redoc_url=f"{API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_v1_router, prefix=API_V1_PREFIX)

# Serve mkdocs site from FastAPI at /mkdocs if site directory exists, otherwise return placeholder HTML.
SITE_DIR = PROJECT_ROOT / "mkdocs_src" / "site"

# Frontend build directory (generated by `./dev.sh fe:build`)
FRONTEND_BUILD_DIR = PROJECT_ROOT / "frontend" / "build"


def frontend_available() -> bool:
    """Check if frontend build exists and has index.html."""
    return FRONTEND_BUILD_DIR.exists() and (FRONTEND_BUILD_DIR / "index.html").exists()


def docs_available() -> bool:  # pragma: no cover
    return SITE_DIR.exists() and (SITE_DIR / "index.html").exists()


def render_docs_not_built() -> HTMLResponse:  # pragma: no cover
    return HTMLResponse("""<html><body>
        <h1>Documentation not generated</h1>
        <p>To build the <b>MkDocs</b> site, change into the <b>LibreFolio</b> installation directory and run:</p>
        <pre><code>cd `/path/to/LibreFolio`
./dev.sh info:mk build</code></pre>
        <p>If you are using <b>Docker</b> (coming soon), open a shell in the backend container and run the same command:</p>
        <pre><code>docker compose exec backend /bin/bash
./dev.sh info:mk build</code></pre>
        </body></html>""")


@app.get("/mkdocs", response_class=HTMLResponse)
def mkdocs_root():  # pragma: no cover
    if docs_available():
        return FileResponse(SITE_DIR / "index.html")
    return render_docs_not_built()


@app.get("/mkdocs/{path:path}")
def mkdocs_static(path: str):  # pragma: no cover
    if not docs_available():
        return render_docs_not_built()

    requested_path = path.strip("/")
    target = SITE_DIR / requested_path
    if target.is_dir():
        target = target / "index.html"

    if target.exists() and target.is_file():
        return FileResponse(target)

    return HTMLResponse("<h1>Documentation file not found</h1>", status_code=404)


@app.get("/")
async def root():  # pragma: no cover
    """
    Root endpoint.
    Serves frontend if build exists, otherwise provides API information.
    """
    if frontend_available():
        return FileResponse(FRONTEND_BUILD_DIR / "index.html")

    return {
        "name": PROJECT_NAME,
        "version": get_version(),
        "docs": f"{API_V1_PREFIX}/docs",
        "frontend": "Not built. Run: ./dev.sh fe:build",
    }


# Serve frontend static assets (JS, CSS, images) if build exists
# This must be mounted AFTER all API routes to avoid conflicts
#
# PERFORMANCE: StaticFiles uses Starlette's async file serving (anyio),
# which does NOT block the event loop. This is critical for serving 15+
# JS chunks in parallel during SvelteKit page navigation.
if frontend_available():
    # Mount _app directory for SvelteKit immutable assets (JS/CSS chunks).
    # Content-hashed filenames → safe to cache hard for a year.
    class ImmutableStaticFiles(StaticFiles):
        def file_response(self, *args, **kwargs):
            resp = super().file_response(*args, **kwargs)
            resp.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
            return resp

    if (FRONTEND_BUILD_DIR / "_app").exists():
        app.mount("/_app", ImmutableStaticFiles(directory=FRONTEND_BUILD_DIR / "_app"), name="frontend_app")


# Catch-all for frontend routes (SPA support) - ALWAYS registered
# Checks at runtime if frontend exists
#
# IMPORTANT: This is a sync `def` (NOT `async def`) on purpose!
# FastAPI runs sync endpoints in a thread pool, so the blocking filesystem
# calls (Path.exists, Path.is_file, FileResponse) do NOT block the uvicorn
# event loop.
#
# NOTE: Direct /_app/... requests are handled by the StaticFiles mount above
# (registered before this route). This catch-all only handles:
# 1. Direct static files in build root (favicon, manifest, robots.txt, etc.)
# 2. SPA fallback (200.html for client-side routing)
@app.get("/{path:path}")
def frontend_catchall(path: str):  # pragma: no cover
    """Serve frontend for any non-API route (SPA support)."""
    # Skip API and docs routes
    if path.startswith(("api/", "mkdocs")):
        return HTMLResponse("<h1>Not Found</h1>", status_code=404)

    # Check if frontend is available at runtime
    if not frontend_available():
        return HTMLResponse("<h1>Frontend not built</h1><p>Run: ./dev.py front build</p>", status_code=503)

    # Try to serve the exact file from the build directory
    # This handles: favicon.png, robots.txt, manifest, etc.
    target = FRONTEND_BUILD_DIR / path
    if target.exists() and target.is_file():
        return FileResponse(target)

    # For SPA routes, serve 200.html (fallback generated by adapter-static)
    # This contains the full SvelteKit app that can handle client-side routing.
    # Never cache it: it references the hashed chunks of the CURRENT build, so a
    # cached copy pins the user to an old bundle until a manual refresh (beta
    # report: version stayed on an old build until an explicit F5).
    fallback = FRONTEND_BUILD_DIR / "200.html"
    if fallback.exists():
        return FileResponse(fallback, headers={"Cache-Control": "no-cache, must-revalidate"})

    # Fallback to index.html if 200.html doesn't exist
    return FileResponse(FRONTEND_BUILD_DIR / "index.html", headers={"Cache-Control": "no-cache, must-revalidate"})
