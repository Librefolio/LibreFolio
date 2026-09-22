"""Release 1.2.0 schema: asset benchmark flag, widened taxonomy, onboarding progress

Revision ID: 004_release_1_2_0_schema
Revises: 5b1333fa6b07
Create Date: 2026-09-22

CONSOLIDATION NOTE — what this file replaces, and what it deliberately does not.

This revision merges three files that existed between the v1.1.0 release and the
Release 2 round, and that were never shipped to anyone:

    003_asset_benchmark_flag_and_taxonomy   (benchmark flag + taxonomy widening)
    003_user_onboarding_progress            (guided onboarding progress)
    ab290f6b6756                            (empty merge node rejoining the two)

Those three forked the graph in a way that only bit on a *fresh* database —
`alembic upgrade head` found two heads and refused to choose, while every
already-stamped install upgraded fine. Consolidating them removes the fork at
the source instead of patching it with a merge node.

It does **not** absorb `5b1333fa6b07` (scheduler timezone), even though that one
also sits after 002. That migration shipped inside the public v1.1.0 release of
2026-09-07, so existing installs carry its revision id in `alembic_version`.
Removing it from the graph would orphan every one of those databases. Its file
was renamed to `003_scheduler_timezone.py` for ordering only — the revision id
is untouched, because the id is the contract and the filename is not.

────────────────────────────────────────────────────────────────────────────────
1. ``Asset.is_benchmark`` — a new boolean. It marks an asset as available for
   comparison in risk and chart selectors. The flag is **shared**, not per-user:
   ``assets`` has no owner column, so there is nowhere to hang a per-user
   preference and inventing one here would be a far larger change than this
   release intends.

   It is deliberately **independent from ``asset_type``**. Benchmark-ness is a
   role an asset plays, not a nature it has: a plain ETF can serve as a
   comparison, and an INDEX can exist without being offered as one. Existing
   INDEX rows are backfilled to ``1`` because that is what they were created
   for and it preserves today's behaviour — but the backfill runs **only when
   the column is created**, so a user who later clears the flag on an index does
   not get it silently restored by a re-run.

2. ``AssetType`` gains eight values: two base types (``COMMODITY``,
   ``REAL_ESTATE``) and six ETF subtypes (``ETF_STOCK``, ``ETF_BOND``,
   ``ETF_COMMODITY``, ``ETF_REAL_ESTATE``, ``ETF_CRYPTO``, ``ETF_MONETARY``).

   This requires **no DDL**. ``assets.asset_type`` is a plain ``VARCHAR`` with no
   CHECK constraint (see 001_initial), so the enum lives entirely in Python and
   widening it is a code change, not a schema change. No existing row changes
   meaning: every current value survives unaltered, and plain ``ETF`` remains
   valid as the residual for mixed or unstated content.

   NOTE — ``assets.asset_type`` and ``transactions.type`` were declared
   ``VARCHAR(14)``. Since 22/09/2026 the declaration in 001_initial reads
   ``VARCHAR(32)``; released SQLite databases keep their original 14 and that is
   deliberate.

       The 14 was a fossil twice over. ``ETF_REAL_ESTATE`` is 15 characters, so
       the asset column had been describing less than the enum could produce;
       and the number itself came from ``CROWDFUND_LOAN`` — exactly fourteen —
       which was later shortened to ``CROWDFUND``. On the transaction side
       ``FX_CONVERSION`` is 13: one character of margin, which the next type
       name would have consumed in silence.

       Widening the declaration is free where it is read — a fresh build, on any
       engine — and costly where it is not. On SQLite the length is advisory:
       measured 22/09/2026 by storing a 30-character value in a ``VARCHAR(14)``
       column, which was accepted unchanged. Rebuilding ``assets`` and
       ``transactions`` on every released installation to correct a number the
       engine ignores would trade a real risk for no effect, so this migration
       performs no DDL for it. The same reasoning migration 002 recorded for
       ``identifier_other``.

       The divergence that remains is therefore: installations created before
       this date declare 14, those created after declare 32, and on SQLite the
       two behave identically. It stops being harmless the day the schema is
       built on an engine that enforces the length — and on that day the schema
       is built from these migrations, which now say 32.

       32 rather than 24: it is what Alembic itself uses for ``version_num``, it
       leaves room for a composite such as ``CROWDFUND_REAL_ESTATE`` (21), and
       the declaration costs the same either way.

3. Versioned per-user onboarding progress. Existing users are not taught an
   application they already use. Welcome is grandfathered as completed because
   their settings are demonstrably configured; every tour and guide is seeded as
   skipped, which suppresses the trigger exactly like completed while staying
   truthful that they were never offered it. Only users created after this
   migration receive pending rows, lazily, through the onboarding service.

   Skipped is deliberate over completed: it keeps "was never shown this"
   distinct from "went through it", so the flows can still be offered
   retroactively.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_release_1_2_0_schema"
down_revision: Union[str, Sequence[str], None] = "5b1333fa6b07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CURRENT_VERSION = 1


def _assets_columns(conn: sa.engine.Connection) -> set[str]:
    """Return the current column names of the assets table."""
    return {row[1] for row in conn.execute(sa.text("PRAGMA table_info(assets)")).fetchall()}


def _upgrade_asset_benchmark(conn: sa.engine.Connection) -> None:
    """Add is_benchmark and seed it from the existing INDEX assets."""
    if "is_benchmark" in _assets_columns(conn):
        return

    conn.execute(sa.text("ALTER TABLE assets ADD COLUMN is_benchmark BOOLEAN NOT NULL DEFAULT 0"))
    # Only on creation: a re-run must never resurrect a flag the user cleared.
    conn.execute(sa.text("UPDATE assets SET is_benchmark = 1 WHERE asset_type = 'INDEX'"))


def _upgrade_onboarding_progress(conn: sa.engine.Connection) -> None:
    """Create onboarding progress tables and seed existing users by flow policy."""
    op.create_table(
        "user_onboarding_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("flow", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("skipped_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'completed', 'skipped')", name="ck_user_onboarding_progress_status"),
        sa.CheckConstraint("version >= 1", name="ck_user_onboarding_progress_version"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "flow", name="uq_user_onboarding_progress_user_flow"),
    )
    op.create_table(
        "user_onboarding_step_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("flow", sa.String(length=50), nullable=False),
        sa.Column("step_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("skipped_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'skipped')", name="ck_user_onboarding_step_progress_status"
        ),
        sa.CheckConstraint("version >= 1", name="ck_user_onboarding_step_progress_version"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "flow", "step_id", name="uq_user_onboarding_step_progress_user_flow_step"),
    )

    conn.execute(
        sa.text("""
            INSERT OR IGNORE INTO user_onboarding_progress
                (user_id, flow, status, version, created_at, updated_at, completed_at, skipped_at)
            SELECT users.id, flows.flow, flows.status, :version,
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                   CASE WHEN flows.status = 'completed' THEN CURRENT_TIMESTAMP ELSE NULL END,
                   CASE WHEN flows.status = 'skipped' THEN CURRENT_TIMESTAMP ELSE NULL END
            FROM users
            CROSS JOIN (
                SELECT 'welcome' AS flow, 'completed' AS status
                UNION ALL SELECT 'intro_tour', 'skipped'
                UNION ALL SELECT 'transactions_page_guide', 'skipped'
                UNION ALL SELECT 'transaction_create_guide', 'skipped'
                UNION ALL SELECT 'transaction_bulk_guide', 'skipped'
                UNION ALL SELECT 'import_guide', 'skipped'
                UNION ALL SELECT 'broker_page_guide', 'skipped'
                UNION ALL SELECT 'broker_guide', 'skipped'
                UNION ALL SELECT 'broker_detail_guide', 'skipped'
                UNION ALL SELECT 'fx_page_guide', 'skipped'
                UNION ALL SELECT 'fx_guide', 'skipped'
                UNION ALL SELECT 'fx_detail_guide', 'skipped'
                UNION ALL SELECT 'asset_page_guide', 'skipped'
                UNION ALL SELECT 'asset_guide', 'skipped'
                UNION ALL SELECT 'asset_detail_guide', 'skipped'
            ) AS flows
            """),
        {"version": _CURRENT_VERSION},
    )
    conn.execute(
        sa.text("""
            INSERT OR IGNORE INTO user_onboarding_step_progress
                (user_id, flow, step_id, status, version, created_at, updated_at, skipped_at)
            SELECT users.id, steps.flow, steps.step_id, 'skipped', :version,
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM users
            CROSS JOIN (
                SELECT 'transaction_bulk_guide' AS flow, 'transaction.bulk.workspace' AS step_id
                UNION ALL SELECT 'transaction_bulk_guide', 'transaction.bulk.validation'
                UNION ALL SELECT 'transaction_bulk_guide', 'transaction.bulk.selection'
                UNION ALL SELECT 'transaction_bulk_guide', 'transaction.bulk.save'
                UNION ALL SELECT 'import_guide', 'import.upload'
                UNION ALL SELECT 'import_guide', 'import.select'
                UNION ALL SELECT 'import_guide', 'import.analyze'
                UNION ALL SELECT 'import_guide', 'import.assets'
                UNION ALL SELECT 'import_guide', 'import.fix'
                UNION ALL SELECT 'import_guide', 'import.duplicates'
                UNION ALL SELECT 'import_guide', 'import.review'
                UNION ALL SELECT 'import_guide', 'import.bulk'
            ) AS steps
            """),
        {"version": _CURRENT_VERSION},
    )


def upgrade() -> None:
    """Apply the Release 2 schema additions in dependency order."""
    conn = op.get_bind()
    _upgrade_asset_benchmark(conn)
    _upgrade_onboarding_progress(conn)


def downgrade() -> None:
    """Reverse the additions. Non-INDEX benchmark flags are lost irreversibly."""
    op.drop_table("user_onboarding_step_progress")
    op.drop_table("user_onboarding_progress")

    conn = op.get_bind()
    if "is_benchmark" not in _assets_columns(conn):
        return
    # SQLite supports DROP COLUMN since 3.35 (2021); the bundled sqlite3 is well past it.
    conn.execute(sa.text("ALTER TABLE assets DROP COLUMN is_benchmark"))
