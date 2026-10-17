"""The ledger's control totals of a database file, for the manifest of a backup and the check of a restore (lot B-13).

J computes them (``services/financial_math/ledger_totals.py``, ``compute_control_totals``: one home for financial
math); this module only reads a database file through J's function, and compares two readings.

- **A backup** records them in its manifest, read on the snapshot of the database (``archive.build_archive``).
- **The check of a restore** reads them again on the copy, once upgraded, and compares (``staging``): a difference is a
  warning, never a refusal, since a migration may correct data. An archive without them (made by hand, or before this
  lot) or with another version of J's method is not compared.

Each reading opens the file read-only through a dedicated engine, closed at the end: never the live database, never the
app's engine or its caches.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import aiosqlite
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.logging_config import get_logger
from backend.app.services.financial_math.ledger_totals import CONTROL_TOTALS_VERSION, ControlTotals, compute_control_totals

logger = get_logger(__name__)

TotalsStatus = Literal["same", "changed", "absent", "other_version", "unreadable"]
#: The differences a comparison keeps; ``differences_count`` counts them all.
MAX_DIFFERENCES = 20


class TotalsDifference(BaseModel):
    """One line of the totals that differs: the cash of a broker in a currency, or the quantity of an asset at a broker.
    ``before`` is the backup's, ``after`` the copy's, in J's canonical text; ``None`` where the line is absent (zero).
    Kept in the report of the check, beside the copy."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    kind: Literal["cash", "quantity"]
    broker_id: int
    currency: str | None = None
    asset_id: int | None = None
    before: str | None = None
    after: str | None = None


@dataclass(frozen=True)
class TotalsComparison:
    """How the totals the backup recorded compare with the copy's."""

    status: TotalsStatus
    differences: tuple[TotalsDifference, ...] = ()
    differences_count: int = 0


def ledger_totals_of(database: Path) -> dict[str, Any] | None:
    """J's control totals of the database file ``database``, as ``ControlTotals.to_json()``; ``None`` when they cannot
    be read (a damaged or missing file, another kind of database), with one error logged. Never raises; synchronous:
    called from a worker thread or the command line, never on a running event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        logger.error("The ledger's control totals could not be read", error="RuntimeError")
        return None
    try:
        # Read as immutable, which ignores a write-ahead log: one still holding frames would give stale totals.
        wal = database.with_name(database.name + "-wal")
        if wal.exists() and wal.stat().st_size > 0:
            logger.error("The ledger's control totals could not be read", error="PendingWriteAheadLog")
            return None
        return asyncio.run(_read(database))
    except Exception as exc:  # noqa: BLE001 — never raises: the backup or the check goes on without the totals
        logger.error("The ledger's control totals could not be read", error=type(exc).__name__)
        return None


async def _read(database: Path) -> dict[str, Any]:
    # Immutable, not only read-only: every engine of the process sets the journal mode when it connects (db/session.py),
    # which a read-only connection to a rollback-journal file refuses; nothing is created beside the file either.
    uri = f"{database.resolve().as_uri()}?mode=ro&immutable=1"
    opened: list[aiosqlite.Connection] = []

    async def connect() -> aiosqlite.Connection:
        connection = await aiosqlite.connect(uri, uri=True)
        opened.append(connection)
        # A schema's functions only if innocuous: the database is an archive's copy (lot B-28).
        await connection.execute("PRAGMA trusted_schema=OFF")
        return connection

    engine = create_async_engine("sqlite+aiosqlite://", async_creator=connect)
    try:
        async with AsyncSession(engine) as session:
            return (await compute_control_totals(session)).to_json()
    finally:
        await engine.dispose()
        # A file that is not a database fails in the engine's connect hook, after the connection opened: the pool drops
        # it without closing it, so it is closed here, whatever the engine did.
        for connection in opened:
            with contextlib.suppress(Exception):
                await connection.close()


def compare_totals(recorded: Any, current: dict[str, Any] | None) -> TotalsComparison:
    """Compare the totals a backup recorded with the copy's; ``recorded`` as read from the manifest, never trusted."""
    if recorded is None:
        return TotalsComparison("absent")
    if isinstance(recorded, dict) and type(recorded.get("version")) is int and recorded["version"] != CONTROL_TOTALS_VERSION:
        return TotalsComparison("other_version")
    try:
        # J's reader refuses an amount that is not plain decimal text before reading it (J-27): an exponent the archive
        # recorded is never expanded. One rule, in J's home.
        before = ControlTotals.from_json(recorded)
    except ValueError:
        logger.warning("The control totals the backup recorded cannot be read: they are not compared")
        return TotalsComparison("absent")
    if current is None:
        return TotalsComparison("unreadable")
    try:
        after = ControlTotals.from_json(current)
    except ValueError:
        # What J computed on the copy but cannot read back, an amount past its bound: not compared (B-29).
        logger.warning("The control totals of the copy cannot be read: they are not compared")
        return TotalsComparison("unreadable")
    differences = _differences(before, after)
    if not differences:
        return TotalsComparison("same")
    return TotalsComparison("changed", tuple(differences[:MAX_DIFFERENCES]), len(differences))


def _differences(before: ControlTotals, after: ControlTotals) -> list[TotalsDifference]:
    """Every line that differs, cash first, then quantities, each by broker and then currency or asset; the amounts in
    J's canonical text, so equal amounts read the same whatever text, order or zero lines the backup recorded."""
    found: list[TotalsDifference] = []
    was_document, now_document = before.to_json(), after.to_json()
    for kind, lines, key, amount in (("cash", "cash", "currency", "balance"), ("quantity", "quantities", "asset_id", "quantity")):
        # J's canonical zero is "0": a line written with it reads as the absent line it equals.
        was = {(row["broker_id"], row[key]): row[amount] for row in was_document[lines] if row[amount] != "0"}
        now = {(row["broker_id"], row[key]): row[amount] for row in now_document[lines] if row[amount] != "0"}
        for broker, other in sorted(set(was) | set(now)):
            if was.get((broker, other)) != now.get((broker, other)):
                found.append(
                    TotalsDifference(
                        kind=kind,
                        broker_id=broker,
                        currency=other if kind == "cash" else None,
                        asset_id=other if kind == "quantity" else None,
                        before=was.get((broker, other)),
                        after=now.get((broker, other)),
                    )
                )
    return found
