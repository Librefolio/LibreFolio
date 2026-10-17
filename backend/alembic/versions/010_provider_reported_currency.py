"""Release 1.3: the quote currency a price provider reports, as it reports it (Z-32)

Revision ID: 010_provider_reported_currency
Revises: 009_email_unique_ignoring_case
Create Date: 2026-10-17

Yahoo Finance quotes London lines in pence and says so with the currency ``GBp``. The schemas accept a currency code
whatever its case and store ``GBP`` with the numbers unchanged, so those prices are pence read as pounds until the
asset's quote base (``quote_base_quantity``, "Units per single price") is 100. From this revision the refresh keeps the
provider's own code on the asset's provider assignment, in the new column ``asset_provider_assignments.reported_currency``
(``VARCHAR(8)``, nullable), and the portfolio data-quality report warns about a held asset quoted in a minor unit whose
quote base does not divide it back (``QUOTE_IN_MINOR_UNIT``).

The upgrade adds the column, NULL on every row: a provider's code is learnt at the asset's next history fetch. The
downgrade drops it, and the codes with it; an upgrade learns them again.

Both use plain ``ALTER TABLE``, never a batch, as 005 does: a batch rebuilds the table (create a copy, move the rows,
drop the original, rename), and with ``PRAGMA foreign_keys=ON``, as every connection of the application runs, dropping
the original would fire the foreign-key action of every row that points at it (``asset_events.provider_assignment_id``).
``ADD COLUMN`` and ``DROP COLUMN`` (SQLite 3.35+) change the table in place and fire none.

Each step checks before it acts, so a run that stopped half way can be run again.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_provider_reported_currency"
down_revision: Union[str, Sequence[str], None] = "009_email_unique_ignoring_case"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "asset_provider_assignments"
_COLUMN = "reported_currency"
#: The declaration ``create_all`` gives the model's field: the same table whichever way a database is built.
_DECLARATION = "VARCHAR(8)"


def _columns(conn: sa.engine.Connection) -> set[str]:
    """Return the current column names of the assignments table."""
    return {row[1] for row in conn.execute(sa.text(f"PRAGMA table_info({_TABLE})")).fetchall()}


def upgrade() -> None:
    """Add ``reported_currency``, NULL on every row, unless a previous run did."""
    conn = op.get_bind()
    if _COLUMN not in _columns(conn):
        conn.execute(sa.text(f"ALTER TABLE {_TABLE} ADD COLUMN {_COLUMN} {_DECLARATION}"))


def downgrade() -> None:
    """Drop ``reported_currency`` (its values are lost), unless it is already gone."""
    conn = op.get_bind()
    if _COLUMN in _columns(conn):
        # SQLite supports DROP COLUMN since 3.35 (2021); the bundled sqlite3 is well past it.
        conn.execute(sa.text(f"ALTER TABLE {_TABLE} DROP COLUMN {_COLUMN}"))
