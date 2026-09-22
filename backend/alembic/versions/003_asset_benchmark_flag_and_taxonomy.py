"""asset benchmark flag + taxonomy widening (ETF subtypes, COMMODITY, REAL_ESTATE)

Revision ID: 003_asset_benchmark_flag_and_taxonomy
Revises: 5b1333fa6b07
Create Date: 2026-09-18

Two changes that ship together because they touch the same table and the same release.

1. ``Asset.is_benchmark`` — a new boolean. It marks an asset as available for comparison
   in risk and chart selectors. The flag is **shared**, not per-user: ``assets`` has no
   owner column, so there is nowhere to hang a per-user preference and inventing one
   here would be a far larger change than this release intends.

   It is deliberately **independent from ``asset_type``**. Benchmark-ness is a role an
   asset plays, not a nature it has: a plain ETF can serve as a comparison, and an INDEX
   can exist without being offered as one. Existing INDEX rows are backfilled to ``1``
   because that is what they were created for and it preserves today's behaviour — but
   the backfill runs **only when the column is created**, so a user who later clears the
   flag on an index does not get it silently restored by a re-run.

2. ``AssetType`` gains eight values: two base types (``COMMODITY``, ``REAL_ESTATE``) and
   six ETF subtypes (``ETF_STOCK``, ``ETF_BOND``, ``ETF_COMMODITY``, ``ETF_REAL_ESTATE``,
   ``ETF_CRYPTO``, ``ETF_MONETARY``).

   This requires **no DDL**. ``assets.asset_type`` is a plain ``VARCHAR`` with no CHECK
   constraint (see 001_initial), so the enum lives entirely in Python and widening it is
   a code change, not a schema change. No existing row changes meaning: every current
   value survives unaltered, and plain ``ETF`` remains valid as the residual for mixed or
   unstated content.

NOTE — the ``VARCHAR(14)`` on ``assets.asset_type`` is now too narrow to describe the
enum, and we are leaving it that way **on purpose**.

    ``ETF_REAL_ESTATE`` is 15 characters. The 14 is a fossil: the enum once contained
    ``CROWDFUND_LOAN`` — exactly fourteen characters — which was later shortened to
    ``CROWDFUND`` while the column declaration stayed behind. It has therefore been
    describing a value that no longer exists for some time.

    On SQLite the length is advisory: type affinity ignores it and nothing is truncated
    or rejected, which is the same reasoning migration 002 recorded for
    ``identifier_other``. Rebuilding ``assets`` on released installations to correct a
    number that has no runtime effect would trade a real risk for a cosmetic gain, and
    shortening the enum names to fit would bend the taxonomy around a phantom
    constraint.

    On a future Postgres port this column must be widened explicitly (or changed to
    ``TEXT``), because there the length **is** enforced and ``ETF_REAL_ESTATE`` would be
    rejected.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_asset_benchmark_flag_and_taxonomy"
down_revision: Union[str, Sequence[str], None] = "5b1333fa6b07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _assets_columns(conn: sa.engine.Connection) -> set[str]:
    """Return the current column names of the assets table."""
    return {row[1] for row in conn.execute(sa.text("PRAGMA table_info(assets)")).fetchall()}


def upgrade() -> None:
    """Add is_benchmark and seed it from the existing INDEX assets."""
    conn = op.get_bind()
    if "is_benchmark" in _assets_columns(conn):
        return

    conn.execute(sa.text("ALTER TABLE assets ADD COLUMN is_benchmark BOOLEAN NOT NULL DEFAULT 0"))
    # Only on creation: a re-run must never resurrect a flag the user cleared.
    conn.execute(sa.text("UPDATE assets SET is_benchmark = 1 WHERE asset_type = 'INDEX'"))


def downgrade() -> None:
    """Drop is_benchmark. Assets whose type is not INDEX lose the flag irreversibly."""
    conn = op.get_bind()
    if "is_benchmark" not in _assets_columns(conn):
        return

    # SQLite supports DROP COLUMN since 3.35 (2021); the bundled sqlite3 is well past it.
    conn.execute(sa.text("ALTER TABLE assets DROP COLUMN is_benchmark"))
