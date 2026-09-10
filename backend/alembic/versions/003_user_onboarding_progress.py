"""add versioned per-user onboarding progress

Revision ID: 003_user_onboarding_progress
Revises: 5b1333fa6b07
Create Date: 2026-09-10

Existing users are grandfathered into every current flow as completed. Users created
after this migration receive pending rows lazily through the onboarding service.
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
    """Create onboarding progress and grandfather every existing user."""
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

    conn = op.get_bind()
    conn.execute(
        sa.text("""
            INSERT OR IGNORE INTO user_onboarding_progress
                (user_id, flow, status, version, created_at, updated_at, completed_at)
            SELECT users.id, flows.flow, 'completed', :version,
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM users
            CROSS JOIN (
                SELECT 'welcome' AS flow
                UNION ALL SELECT 'intro_tour'
                UNION ALL SELECT 'import_guide'
            ) AS flows
            """),
        {"version": _CURRENT_VERSION},
    )


def downgrade() -> None:
    """Remove onboarding progress without touching users or preferences."""
    op.drop_table("user_onboarding_progress")
