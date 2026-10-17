"""Release 1.3: the exchange's timezone of a price provider, and the mark of the Yahoo rows dated the day before (Z-33)

Revision ID: 011_provider_exchange_timezone
Revises: 010_provider_reported_currency
Create Date: 2026-10-17

yfinance stamps a daily bar, a dividend or a split at midnight in the exchange's timezone; before this release the Yahoo
plugin took the UTC date of that instant, the day before the session for every exchange east of UTC (Milan all year,
London in summer time, Tokyo). From this revision the plugin keeps the local date and reports the exchange's timezone,
which the refresh keeps on the provider assignment, in the new column ``asset_provider_assignments.exchange_timezone``
(``VARCHAR(64)``, nullable).

The upgrade adds the column and writes ``'legacy-utc'`` on every ``yfinance`` assignment: the rows they hold were dated
by the old rule. The next refresh of each re-dates its prices and events once, with the timezone Yahoo reports, then
stores that timezone. Every other assignment, and every one created later, stays NULL until its first fetch, and is
never re-dated.

The downgrade drops the column, and the marks and timezones with it. A database taken back below 011 after its rows were
re-dated, then upgraded again, would mark them again: do not downgrade past this revision once the server has synced.

Plain ``ALTER TABLE`` only, as 010: a batch would rebuild the table, and with foreign keys on dropping the original fires
``asset_events.provider_assignment_id``'s action. Each step checks before it acts, so a run that stopped half way can be
run again: the mark only goes on a ``yfinance`` assignment whose value is still NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_provider_exchange_timezone"
down_revision: Union[str, Sequence[str], None] = "010_provider_reported_currency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "asset_provider_assignments"
_COLUMN = "exchange_timezone"
#: The declaration ``create_all`` gives the model's field: the same table whichever way a database is built.
_DECLARATION = "VARCHAR(64)"
#: ``backend.app.utils.exchange_dates.LEGACY_UTC_DATES`` and ``LEGACY_UTC_PROVIDER``, written out: a migration never
#: imports the application.
_LEGACY_MARK = "legacy-utc"
_LEGACY_PROVIDER = "yfinance"


def _columns(conn: sa.engine.Connection) -> set[str]:
    """Return the current column names of the assignments table."""
    return {row[1] for row in conn.execute(sa.text(f"PRAGMA table_info({_TABLE})")).fetchall()}


def upgrade() -> None:
    """Add ``exchange_timezone``, then mark the ``yfinance`` assignments still NULL."""
    conn = op.get_bind()
    if _COLUMN not in _columns(conn):
        conn.execute(sa.text(f"ALTER TABLE {_TABLE} ADD COLUMN {_COLUMN} {_DECLARATION}"))
    conn.execute(
        sa.text(f"UPDATE {_TABLE} SET {_COLUMN} = :mark WHERE provider_code = :provider AND {_COLUMN} IS NULL"),
        {"mark": _LEGACY_MARK, "provider": _LEGACY_PROVIDER},
    )


def downgrade() -> None:
    """Drop ``exchange_timezone`` (its marks and timezones are lost), unless it is already gone."""
    conn = op.get_bind()
    if _COLUMN in _columns(conn):
        # SQLite supports DROP COLUMN since 3.35 (2021); the bundled sqlite3 is well past it.
        conn.execute(sa.text(f"ALTER TABLE {_TABLE} DROP COLUMN {_COLUMN}"))
