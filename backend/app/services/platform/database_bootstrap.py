"""The database at startup: created or migrated to the head revision, then the repairs that cannot be migrations.

Owner: workstream H (platform). Moved out of ``main.py`` as it was (CP2b). The head revision now comes from
``readiness.alembic_head_revision()``, the one reader of it; the warning it used to log when the head cannot be read is
logged here. ``app_lifespan.py`` runs both functions at startup; the test scripts call ``ensure_database_exists()``.
"""

import contextlib
import sqlite3
import subprocess
import sys
from pathlib import Path

from backend.app.config import PROJECT_ROOT, get_data_dir, get_settings
from backend.app.db.post_migration import configured_sqlite_path, run_post_migration_fixes
from backend.app.logging_config import get_logger
from backend.app.services.platform.readiness import alembic_head_revision

logger = get_logger(__name__)


def ensure_database_exists():  # noqa: C901 — sequential DB bootstrap state checks, flag-based
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

                        head_rev = alembic_head_revision()
                        if head_rev is None:
                            logger.warning("Could not determine Alembic head revision")
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
                logger.exception("Error applying database migrations", error=str(e))
                sys.exit(1)


def run_post_migration_fixes_at_startup():
    """Run the post-migration fixes on the configured SQLite database and data dir.

    The repairs that cannot be Alembic migrations (``backend.app.db.post_migration``), right
    after them. Returns their report, or ``None`` when the run itself failed. Never raises:
    a repair that cannot run leaves the database as it was, and the server starts anyway.
    Plan ``34_accountAndIdReuse`` §2.3.
    """
    try:
        db_path = configured_sqlite_path()
        if db_path is None:
            return None
        report = run_post_migration_fixes(db_path, get_data_dir())
    except Exception as exc:  # noqa: BLE001 — startup never blocks on a repair
        logger.warning("Post-migration fixes could not run; starting normally", error=str(exc))
        return None
    if report.failed:
        logger.warning("Post-migration fixes failed; starting normally", outcomes=report.outcomes, backup=str(report.backup_path) if report.backup_path else None, errors=report.errors)
    return report
