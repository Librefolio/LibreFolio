"""Readiness of the instance (``GET /system/ready``): the database answers, and its schema is at the head revision.

The head revision is read from the migration scripts once per process, in a worker thread: the read parses
``alembic.ini`` and imports the migration scripts, synchronous I/O that must not block the event loop. A failure to
read it is not cached, so the next check tries again. The result carries one code per check and never an error message,
a path or a revision id: those go to the log, once per change of state, because a monitor may ask every few seconds.
"""

import asyncio
from functools import cache

from sqlalchemy import column, literal, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import PROJECT_ROOT
from backend.app.logging_config import get_logger
from backend.app.schemas.system import ReadinessChecks, ReadinessDatabaseState, ReadinessMigrationsState, ReadinessResponse

logger = get_logger(__name__)

_ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"
_ALEMBIC_VERSION = table("alembic_version", column("version_num"))
# The checks of the last result logged: a change of state is logged once, not at every check.
_logged: list[ReadinessChecks] = []


@cache
def _read_alembic_head() -> str:
    from alembic.config import Config  # noqa: PLC0415 — keep alembic out of the app's import scope
    from alembic.script import ScriptDirectory  # noqa: PLC0415

    head = ScriptDirectory.from_config(Config(str(_ALEMBIC_INI))).get_current_head()
    if head is None:
        raise LookupError("the migration scripts have no revision")
    return head


def alembic_head_revision() -> str | None:
    """The head revision of the migration scripts, or None when it cannot be read (several heads, missing scripts)."""
    try:
        return _read_alembic_head()
    except Exception as exc:
        logger.debug("Could not determine the Alembic head revision", error=str(exc))
        return None


async def _run_checks(session: AsyncSession) -> tuple[ReadinessDatabaseState, ReadinessMigrationsState, str | None]:
    """The two codes, and what went wrong for the log (None when both are ok)."""
    try:
        await session.execute(select(literal(1)))
    except Exception as exc:
        return "unreachable", "unknown", f"the database does not answer: {exc}"
    head = await asyncio.to_thread(alembic_head_revision)
    if head is None:
        return "ok", "unknown", "the head revision of the migration scripts cannot be read"
    try:
        revisions = (await session.execute(select(_ALEMBIC_VERSION.c.version_num))).scalars().all()
    except Exception as exc:
        return "ok", "unknown", f"the revision of the database cannot be read: {exc}"
    if len(revisions) != 1:
        return "ok", "unknown", f"alembic_version holds {len(revisions)} rows instead of one"
    if revisions[0] != head:
        return "ok", "mismatch", f"the database is at revision {revisions[0]}, the migration scripts at {head}"
    return "ok", "ok", None


def _log_change(checks: ReadinessChecks, problem: str | None) -> None:
    if _logged and _logged[0] == checks:
        return
    _logged[:] = [checks]
    if problem is None:
        logger.info("Instance ready", database=checks.database, migrations=checks.migrations)
    else:
        logger.warning("Instance not ready", database=checks.database, migrations=checks.migrations, problem=problem)


async def check_readiness(session: AsyncSession) -> ReadinessResponse:
    """Check the database and its migrations: ``ready`` only when every check is ``ok``."""
    database, migrations, problem = await _run_checks(session)
    checks = ReadinessChecks(database=database, migrations=migrations)
    _log_change(checks, problem)
    return ReadinessResponse(status="ready" if problem is None else "not_ready", checks=checks)
