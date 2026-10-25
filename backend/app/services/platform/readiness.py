"""Readiness of the instance (``GET /system/ready``): the database answers, and its schema is at the head revision.

The head revision, and the revisions the migration scripts know, are read once per process, in a worker thread: the
read parses ``alembic.ini`` and imports the migration scripts, synchronous I/O that must not block the event loop. A
failure to read it is not cached, so the next check tries again. A database that is not at the head is ``behind`` when
its revision is one the scripts know (a migration was not applied, or failed) and ``ahead`` when they do not (the
database is newer than this image, or from another LibreFolio). The result carries one code per check and the database's
revision (developer decision, 25/10/2026); an error message and a path go to the log, once per change of state, because
a monitor may ask every few seconds.
"""

import asyncio
from functools import cache
from typing import NamedTuple

from sqlalchemy import column, literal, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import PROJECT_ROOT
from backend.app.config.platform import awaiting_restore
from backend.app.logging_config import get_logger
from backend.app.schemas.system import ReadinessChecks, ReadinessDatabaseState, ReadinessMigrationsState, ReadinessResponse

logger = get_logger(__name__)

_ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"
_ALEMBIC_VERSION = table("alembic_version", column("version_num"))
# The checks of the last result logged: a change of state is logged once, not at every check.
_logged: list[ReadinessChecks] = []


class _Scripts(NamedTuple):
    """What one read of the migration scripts gives: the head, and every revision they know."""

    head: str
    known: frozenset[str]


@cache
def _read_alembic_scripts() -> _Scripts:
    from alembic.config import Config  # noqa: PLC0415 — keep alembic out of the app's import scope
    from alembic.script import ScriptDirectory  # noqa: PLC0415

    directory = ScriptDirectory.from_config(Config(str(_ALEMBIC_INI)))
    head = directory.get_current_head()
    if head is None:
        raise LookupError("the migration scripts have no revision")
    return _Scripts(head, frozenset(script.revision for script in directory.walk_revisions()))


def _read_scripts() -> _Scripts | None:
    try:
        return _read_alembic_scripts()
    except Exception as exc:
        logger.debug("Could not determine the Alembic head revision", error=str(exc))
        return None


def alembic_head_revision() -> str | None:
    """The head revision of the migration scripts, or None when it cannot be read (several heads, missing scripts)."""
    scripts = _read_scripts()
    return None if scripts is None else scripts.head


async def _run_checks(session: AsyncSession) -> tuple[ReadinessDatabaseState, ReadinessMigrationsState, str | None, str | None]:
    """The two codes, the database's revision (None when it cannot be read), and what went wrong for the log (None when both are ok)."""
    try:
        await session.execute(select(literal(1)))
    except Exception as exc:
        return "unreachable", "unknown", None, f"the database does not answer: {exc}"
    head = await asyncio.to_thread(alembic_head_revision)
    # The read above filled the cache: this one touches no file, so it may run on the event loop
    scripts = _read_scripts() if head is not None else None
    try:
        revisions = (await session.execute(select(_ALEMBIC_VERSION.c.version_num))).scalars().all()
    except Exception as exc:
        return "ok", "unknown", None, f"the revision of the database cannot be read: {exc}"
    if len(revisions) != 1:
        return "ok", "unknown", None, f"alembic_version holds {len(revisions)} rows instead of one"
    revision = revisions[0]
    if scripts is None:
        return "ok", "unknown", revision, "the head revision of the migration scripts cannot be read"
    if revision == scripts.head:
        return "ok", "ok", revision, None
    if revision in scripts.known:
        return "ok", "behind", revision, f"the database is at revision {revision}, the migration scripts at {scripts.head}: a migration was not applied or failed"
    return "ok", "ahead", revision, f"the database is at revision {revision}, which the migration scripts (head {scripts.head}) do not know: it is newer than this version"


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
    database, migrations, revision, problem = await _run_checks(session)
    checks = ReadinessChecks(database=database, migrations=migrations)
    _log_change(checks, problem)
    # H-62: an instance awaiting its restore says so; ready then means ready to receive the backup
    return ReadinessResponse(status="ready" if problem is None else "not_ready", checks=checks, database_revision=revision, mode="awaiting_restore" if awaiting_restore() else "normal")
