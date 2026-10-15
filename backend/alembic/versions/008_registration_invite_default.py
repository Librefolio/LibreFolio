"""Accounts: a new install registers by invitation, an upgraded one keeps registration open (release 1.3, workstream A)

Revision ID: 008_registration_invite_default
Revises: 007_plugin_settings
Create Date: 2026-10-15

Decision 36: the default of the global setting ``registration_mode`` becomes ``invite``. A new instance accepts its
first account from anyone (an administrator, in any mode) and every later one only through an invitation link. The
default applies where the row is missing: the settings service seeds missing rows at startup.

An instance that already holds accounts keeps the behaviour it had. Its row normally exists (the startup seeding wrote
``enable_registration``, and ``006_registration_mode`` converted it), and a row is never touched, whatever its value.
Where it is missing and ``users`` is not empty, this migration writes ``registration_mode`` = ``open``, the earlier
default, now explicit. A database without accounts is a new install: nothing is written, and it gets the new default.

Data only. The downgrade does nothing: an ``open`` row is what the earlier default meant, and the earlier migrations
read it as before (``006_registration_mode`` turns it back into ``enable_registration`` = true).

The upgrade checks before it acts, so it can be run again.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_registration_invite_default"
down_revision: Union[str, Sequence[str], None] = "007_plugin_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_KEY = "registration_mode"
_DESCRIPTION = "Who may create an account: open, invite or disabled"


def upgrade() -> None:
    """Write ``registration_mode`` = ``open`` where the row is missing and accounts exist."""
    op.get_bind().execute(
        sa.text("""
            INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id)
            SELECT :key, 'open', 'str', :description, CURRENT_TIMESTAMP, NULL
            WHERE NOT EXISTS (SELECT 1 FROM global_settings WHERE key = :key)
              AND EXISTS (SELECT 1 FROM users)
            """),
        {"key": _KEY, "description": _DESCRIPTION},
    )


def downgrade() -> None:
    """Nothing to undo: an ``open`` row is the earlier default, read as before by the earlier migrations."""
