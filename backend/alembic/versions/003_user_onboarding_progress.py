"""add versioned per-user onboarding progress

Revision ID: 003_user_onboarding_progress
Revises: 5b1333fa6b07
Create Date: 2026-09-10

Existing users are not taught an application they already use. Welcome is
grandfathered as completed because their settings are demonstrably configured;
every tour and guide is seeded as skipped, which suppresses the trigger exactly
like completed while staying truthful that they were never offered it. Only
users created after this migration receive pending rows, lazily, through the
onboarding service.

Skipped is deliberate over completed: it keeps "was never shown this" distinct
from "went through it", so the flows can still be offered retroactively.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_user_onboarding_progress"
down_revision: Union[str, Sequence[str], None] = "5b1333fa6b07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CURRENT_VERSION = 1


def upgrade() -> None:
    """Create onboarding progress and seed existing users by flow policy."""
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
        sa.CheckConstraint("status IN ('pending', 'completed', 'skipped')", name="ck_user_onboarding_step_progress_status"),
        sa.CheckConstraint("version >= 1", name="ck_user_onboarding_step_progress_version"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "flow", "step_id", name="uq_user_onboarding_step_progress_user_flow_step"),
    )

    conn = op.get_bind()
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


def downgrade() -> None:
    """Remove onboarding progress without touching users or preferences."""
    op.drop_table("user_onboarding_step_progress")
    op.drop_table("user_onboarding_progress")
