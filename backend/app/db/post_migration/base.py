"""Shared types of the post-migration fixes (plan ``34_accountAndIdReuse`` §2.3)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class PostMigrationReport:
    """What one run found and did.

    ``outcomes`` maps each fix id to ``clean``, ``applied``, ``would_apply`` (dry run) or
    ``failed``. ``backup_path`` is the backup that is *kept*: ``None`` when none was needed
    or when it was deleted after a verified fix. ``orphan_broker_dirs`` lists the orphan
    ``broker_<n>`` folders found, relative to the data dir.
    """

    outcomes: dict[str, str] = field(default_factory=dict)
    integrity_ok: bool = True
    backup_path: Optional[Path] = None
    orphan_broker_dirs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return not self.integrity_ok or "failed" in self.outcomes.values()


@dataclass
class FixContext:
    """What a fix needs besides the connection: where the data lives, the run's timestamp, the report."""

    db_path: Path
    data_dir: Optional[Path]
    timestamp: str
    report: PostMigrationReport
    state: dict[str, Any] = field(default_factory=dict)


class PostMigrationError(Exception):
    """A fix met something it does not know how to correct safely."""


class PostMigrationFix:
    """One repair. ``detect`` never writes; ``apply`` and ``verify`` run inside the fix's transaction.

    ``prepare`` runs outside the transaction, after the backup (filesystem work that must be undone
    on failure); ``finish`` runs after the commit or the rollback.
    """

    fix_id: str = ""

    def detect(self, conn: sqlite3.Connection, ctx: FixContext) -> Optional[Any]:
        raise NotImplementedError

    def prepare(self, anomaly: Any, ctx: FixContext) -> None:
        return None

    def apply(self, conn: sqlite3.Connection, anomaly: Any, ctx: FixContext) -> None:
        raise NotImplementedError

    def verify(self, conn: sqlite3.Connection, anomaly: Any, ctx: FixContext) -> list[str]:
        return []

    def finish(self, ctx: FixContext, *, success: bool) -> None:
        return None
