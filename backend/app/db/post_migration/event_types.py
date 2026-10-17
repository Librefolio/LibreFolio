"""Post-migration fix ``event_types``: asset event types the app does not know (decision 23 of release 1.3, I-09).

Until 1.3 an event type was stored as it came: a CSV written by hand could save ``dividend`` or ``dividendo``. The
column is ``AssetEventType``, so every later read of that asset's events failed (``LookupError``, a 500), and the
events were not shown. Since 1.3 the type is trimmed and upper-cased on the way in, and refused when still unknown
(``FAAssetEventPoint``); this fix repairs the rows already stored, once:

- a type that becomes valid once trimmed and upper-cased (``dividend``, `` Split ``) is corrected in place: the event
  keeps its id, and its transactions stay linked;
- an event whose type stays unknown is deleted (the developer's decision, 15/10: the only way for the rows saved wrong
  is to delete them, and they are not shown already). The transactions linked to it are unlinked first
  (``asset_event_id`` NULL): each transaction stays, without its event.

"Trimmed and upper-cased" is Python's ``str.strip().upper()``, the same rule the schema applies on the way in
(``FAAssetEventPoint``, lot E1a), so a type the app accepts today and one this fix corrects are read alike.

The detection logs, as a warning, what it would do — the events to correct, by stored type; the events to delete;
the transactions to unlink — so a dry run (``python -m backend.app.db.post_migration --dry-run``, server stopped) is
the count, on any database. After the commit, each row it changed gets its own INFO line. The fix declares the events
it deletes (``row_count_changes``), and the framework checks every row count against it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

from backend.app.db.models import AssetEventType
from backend.app.db.post_migration.base import FixContext, PostMigrationError, PostMigrationFix
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

# The types the app reads: the values of AssetEventType.
VALID_TYPES: tuple[str, ...] = tuple(kind.value for kind in AssetEventType)


@dataclass(frozen=True)
class _Event:
    """One stored asset event whose type the app does not know."""

    id: int
    asset_id: int
    date: str
    type: Any
    value: Any
    currency: Optional[str]
    provider_assignment_id: Optional[int]

    @property
    def corrected_type(self) -> Optional[str]:
        """The valid type the stored one becomes once trimmed and upper-cased, or ``None`` when there is none."""
        candidate = self.type.strip().upper() if isinstance(self.type, str) else None
        return candidate if candidate in VALID_TYPES else None


@dataclass(frozen=True)
class _Linked:
    """A transaction linked to an event the fix deletes."""

    id: int
    broker_id: int
    type: str
    date: str


@dataclass
class _Anomaly:
    corrections: list[_Event]
    deletions: list[_Event]
    linked: dict[int, list[_Linked]] = field(default_factory=dict)  # event id → its transactions


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone() is not None


def _unknown_events(conn: sqlite3.Connection) -> list[_Event]:
    placeholders = ", ".join("?" for _ in VALID_TYPES)
    sql = f"SELECT id, asset_id, date, type, value, currency, provider_assignment_id FROM asset_events WHERE type NOT IN ({placeholders}) ORDER BY id"
    return [_Event(*row) for row in conn.execute(sql, VALID_TYPES).fetchall()]


class EventTypesFix(PostMigrationFix):
    fix_id = "event_types"

    def detect(self, conn: sqlite3.Connection, ctx: FixContext) -> Optional[_Anomaly]:
        if not _table_exists(conn, "asset_events"):
            return None
        events = _unknown_events(conn)
        if not events:
            return None
        anomaly = _Anomaly(corrections=[e for e in events if e.corrected_type], deletions=[e for e in events if not e.corrected_type])
        for event in anomaly.deletions:
            rows = conn.execute("SELECT id, broker_id, type, date FROM transactions WHERE asset_event_id = ? ORDER BY id", (event.id,)).fetchall()
            if rows:
                anomaly.linked[event.id] = [_Linked(*row) for row in rows]
        corrections: dict[str, list[int]] = {}
        for event in anomaly.corrections:
            corrections.setdefault(f"{event.type}->{event.corrected_type}", []).append(event.id)
        deletions: dict[str, list[int]] = {}
        for event in anomaly.deletions:
            deletions.setdefault(str(event.type), []).append(event.id)
        logger.warning(
            "Asset events whose type the app does not know: corrected when trimming and upper-casing makes it valid, deleted otherwise (their transactions unlinked first)",
            count=len(events),
            corrections=corrections,
            deletions=deletions,
            unlinked_transactions=[tx.id for txs in anomaly.linked.values() for tx in txs],
        )
        return anomaly

    def row_count_changes(self, anomaly: _Anomaly, ctx: FixContext) -> dict[str, int]:
        return {"asset_events": -len(anomaly.deletions)}

    def apply(self, conn: sqlite3.Connection, anomaly: _Anomaly, ctx: FixContext) -> None:
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")
        for event in anomaly.corrections:
            cursor = conn.execute("UPDATE asset_events SET type = ?, updated_at = ? WHERE id = ? AND type = ?", (event.corrected_type, now, event.id, event.type))
            if cursor.rowcount != 1:
                raise PostMigrationError(f"asset event {event.id}: changed while being corrected; left as it is")
        for event in anomaly.deletions:
            linked = anomaly.linked.get(event.id, [])
            cursor = conn.execute("UPDATE transactions SET asset_event_id = NULL, updated_at = ? WHERE asset_event_id = ?", (now, event.id))
            if cursor.rowcount != len(linked):
                raise PostMigrationError(f"asset event {event.id}: its transactions changed while being unlinked; left as it is")
            cursor = conn.execute("DELETE FROM asset_events WHERE id = ? AND type = ?", (event.id, event.type))
            if cursor.rowcount != 1:
                raise PostMigrationError(f"asset event {event.id}: changed while being deleted; left as it is")
        ctx.state[self.fix_id] = anomaly

    def verify(self, conn: sqlite3.Connection, anomaly: _Anomaly, ctx: FixContext) -> list[str]:
        problems = [f"asset event {event.id}: type {event.type!r} still unknown" for event in _unknown_events(conn)]
        for event in anomaly.corrections:
            row = conn.execute("SELECT type FROM asset_events WHERE id = ?", (event.id,)).fetchone()
            if row != (event.corrected_type,):
                problems.append(f"asset event {event.id}: {row} after the correction, {event.corrected_type} expected")
        for event in anomaly.deletions:
            if conn.execute("SELECT 1 FROM asset_events WHERE id = ?", (event.id,)).fetchone() is not None:
                problems.append(f"asset event {event.id}: still there after its deletion")
            if conn.execute("SELECT 1 FROM transactions WHERE asset_event_id = ?", (event.id,)).fetchone() is not None:
                problems.append(f"asset event {event.id}: a transaction still names it")
        return problems

    def finish(self, ctx: FixContext, *, success: bool) -> None:
        if not success:
            return
        anomaly: Optional[_Anomaly] = ctx.state.get(self.fix_id)
        if anomaly is None:
            return
        for event in anomaly.corrections:
            logger.info("Asset event type corrected", event_id=event.id, asset_id=event.asset_id, date=event.date, from_type=event.type, to_type=event.corrected_type)
        for event in anomaly.deletions:
            linked = anomaly.linked.get(event.id, [])
            for tx in linked:
                logger.info("Transaction unlinked from an asset event of unknown type", transaction_id=tx.id, broker_id=tx.broker_id, transaction_type=tx.type, date=tx.date, former_event_id=event.id)
            logger.info(
                "Asset event of unknown type deleted",
                event_id=event.id,
                asset_id=event.asset_id,
                date=event.date,
                type=str(event.type),
                value=str(event.value),
                currency=event.currency,
                is_auto=event.provider_assignment_id is not None,
                unlinked_transactions=[tx.id for tx in linked],
            )
