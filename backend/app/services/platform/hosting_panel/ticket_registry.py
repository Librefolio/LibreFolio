"""The registry of the hosting panel's used tickets (lot H-61, level L2): each ``jti`` is accepted once.

Owner: workstream H (platform). A small SQLite file of its own, ``DATA_DIR/panel_tickets.sqlite3`` (decision of 20/10:
no table in the release's database, whose single migration is already applied on real instances). One table, a row per
ticket accepted, ``(jti, expires_at)``. ``record`` checks and records in one write transaction (``BEGIN IMMEDIATE``), so
the workers of one instance, which share the file and its lock, never accept the same ticket twice, and a restart
forgets nothing. Each record first deletes the rows whose ticket expired more than ``PRUNE_MARGIN_SECONDS`` ago: the
widest tolerance plus the longest life of a ticket, whatever tolerance is configured now. A margin that follows the
verification's own edge (``now - skew``) would let a pruned ticket pass a second time when the clock steps back (an NTP
step, a machine resumed) or when the tolerance is raised at a restart.

The file is created on first use, never at import, with permissions 600, and it is used only while it is a regular
file: a symbolic link in its place (dangling, or to a file elsewhere) is never followed. It is not in a backup: an
archive carries only the database and three folders (``instance_backup/paths.py``), and a restore does not touch it. A
file the server cannot use raises ``TicketRegistryError``, which the access turns into the scope's 503; whatever stands
in the file's place is left as it was.
"""

import os
import sqlite3
import stat
from contextlib import closing
from pathlib import Path

from backend.app.config import get_data_dir
from backend.app.config.hosting_panel import PANEL_CLOCK_SKEW_MAX_SECONDS
from backend.app.services.platform.hosting_panel.tickets import TICKET_MAX_LIFETIME_SECONDS

REGISTRY_FILE = "panel_tickets.sqlite3"
#: A row is deleted once its ticket expired this long ago: the widest tolerance plus the longest life of a ticket.
PRUNE_MARGIN_SECONDS = PANEL_CLOCK_SKEW_MAX_SECONDS + TICKET_MAX_LIFETIME_SECONDS
#: How long a writer waits for another one's lock before the registry counts as unreachable.
_BUSY_TIMEOUT_SECONDS = 10.0


class TicketRegistryError(RuntimeError):
    """The registry of used tickets cannot be read or written: the panel's tickets are refused with a 503."""


def registry_path() -> Path:
    """The file of the registry, in the data directory of the moment."""
    return get_data_dir() / REGISTRY_FILE


def _create(path: Path) -> None:
    """Create the file empty with permissions 600, when nothing is there: SQLite then opens it as a new database."""
    if os.path.lexists(path):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except FileExistsError:  # another worker created it first
        return
    os.close(descriptor)


def _ensure_regular_file(path: Path) -> None:
    """Refuse anything but a regular file at ``path``, a symbolic link above all: SQLite would follow it."""
    if not stat.S_ISREG(os.lstat(path).st_mode):
        raise TicketRegistryError("the registry of used panel tickets is not a regular file")


def record(jti: str, expires_at: int, now: float) -> bool:
    """Record the ticket ``jti``, valid until ``expires_at``: True when it was never seen, False when it was used before."""
    try:
        cutoff = now - PRUNE_MARGIN_SECONDS
        path = registry_path()
        _create(path)
        _ensure_regular_file(path)
        with closing(sqlite3.connect(path, timeout=_BUSY_TIMEOUT_SECONDS, isolation_level=None)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute("CREATE TABLE IF NOT EXISTS used_ticket (jti TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)")
                connection.execute("DELETE FROM used_ticket WHERE expires_at < ?", (cutoff,))
                try:
                    connection.execute("INSERT INTO used_ticket (jti, expires_at) VALUES (?, ?)", (jti, expires_at))
                except sqlite3.IntegrityError:
                    connection.execute("COMMIT")
                    return False
                connection.execute("COMMIT")
                return True
            except BaseException:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
    except (sqlite3.Error, OSError) as exc:
        raise TicketRegistryError(f"the registry of used panel tickets cannot be used: {type(exc).__name__}") from exc
