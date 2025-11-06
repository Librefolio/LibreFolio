"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# Always import sqlmodel for SQLModel compatibility
# (Alembic autogenerate may use sqlmodel.sql.sqltypes.AutoString)
try:
    import sqlmodel
except ImportError:
    pass

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema."""
    print(f"🔧 Running migration {revision}: ${message}")
    ${upgrades if upgrades else "pass"}
    print(f"✅ Migration {revision} completed")


def downgrade() -> None:
    """Downgrade schema."""
    print(f"⏪ Rolling back migration {revision}: ${message}")
    ${downgrades if downgrades else "pass"}
    print(f"✅ Rollback {revision} completed")
