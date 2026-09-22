"""merge the benchmark taxonomy and onboarding heads

Revision ID: ab290f6b6756
Revises: 003_asset_benchmark_flag_and_taxonomy, 003_user_onboarding_progress
Create Date: 2026-09-21 18:46:01.598749

WHY THIS MIGRATION IS EMPTY, AND WHY IT HAS TO EXIST.

Two migrations were written in parallel on top of `5b1333fa6b07` and both
declared it as their `down_revision`:

    5b1333fa6b07
        ├── 003_asset_benchmark_flag_and_taxonomy   (asset benchmark flag + risk taxonomy)
        └── 003_user_onboarding_progress            (guided onboarding progress)

They live in **different files**, so merging the two lines of work produced no
textual conflict and Git had nothing to report. The revision graph forked all
the same, and `alembic upgrade head` then refuses to choose:

    Multiple head revisions are present for given argument 'head'

The failure is invisible to anyone whose database is already stamped on one of
the two heads — it only bites when a database is created from scratch or when
an existing install upgrades. That is why it surfaced in a fresh worktree and
not in the lanes that were already running.

This revision changes no schema. It exists solely to rejoin the two branches
into one head, so that `upgrade head` has a single target again. Neither of the
two migrations above is rewritten.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Always import sqlmodel for SQLModel compatibility
# (Alembic autogenerate may use sqlmodel.sql.sqltypes.AutoString)
try:
    import sqlmodel
except ImportError:
    pass

# revision identifiers, used by Alembic.
revision: str = 'ab290f6b6756'
down_revision: Union[str, Sequence[str], None] = ('003_asset_benchmark_flag_and_taxonomy', '003_user_onboarding_progress')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    print(f"🔧 Running migration {revision}: merge the benchmark taxonomy and onboarding heads")
    pass
    print(f"✅ Migration {revision} completed")


def downgrade() -> None:
    """Downgrade schema."""
    print(f"⏪ Rolling back migration {revision}: merge the benchmark taxonomy and onboarding heads")
    pass
    print(f"✅ Rollback {revision} completed")
