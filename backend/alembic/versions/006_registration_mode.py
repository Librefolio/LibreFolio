"""Accounts: registration_mode takes the place of enable_registration (release 1.3, workstream A)

Revision ID: 006_registration_mode
Revises: 005_accounts_invites
Create Date: 2026-10-15

The global setting ``enable_registration`` — anyone may sign up, or nobody — becomes ``registration_mode``, one of three
values:

- ``open``: anyone may create an account, and an invitation, if given, sets its role;
- ``invite``: only whoever holds a valid invitation link;
- ``disabled``: nobody, invitation or not.

Data only: the row is converted and the old one deleted. The stored text is read the way the settings service read the
boolean until now — ``value.lower()`` among ``true``, ``1``, ``yes``, ``on`` — so ``open`` is what the server treated
as open, and every other value, the odd ones included, is ``disabled``: closed, as it was. The date and the author of
the last change are kept. A database without the row has nothing to convert: if it already holds accounts,
``008_registration_invite_default`` writes ``open``; otherwise the settings service seeds the default, ``invite`` since
decision 36.

The downgrade converts back: ``open`` is ``true``; ``invite`` and ``disabled`` are ``false``, since the old setting had
no middle ground and closed is the safe reading of invitation-only.

Each direction checks before it acts, so a run that stopped half way can be run again.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_registration_mode"
down_revision: Union[str, Sequence[str], None] = "005_accounts_invites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_KEY = "enable_registration"
_NEW_KEY = "registration_mode"
_NEW_DESCRIPTION = "Who may create an account: open, invite or disabled"
_OLD_DESCRIPTION = "Allow new user registration"


def _has(conn: sa.engine.Connection, key: str) -> bool:
    """Whether the global setting ``key`` exists."""
    return conn.execute(sa.text("SELECT 1 FROM global_settings WHERE key = :key"), {"key": key}).first() is not None


def upgrade() -> None:
    """Write ``registration_mode`` from ``enable_registration``, then delete the old row."""
    conn = op.get_bind()
    if not _has(conn, _OLD_KEY):
        return
    if not _has(conn, _NEW_KEY):
        conn.execute(
            sa.text("""
                INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id)
                SELECT :new_key,
                       CASE WHEN lower(value) IN ('true', '1', 'yes', 'on') THEN 'open' ELSE 'disabled' END,
                       'str', :description, updated_at, updated_by_user_id
                FROM global_settings WHERE key = :old_key
                """),
            {"new_key": _NEW_KEY, "old_key": _OLD_KEY, "description": _NEW_DESCRIPTION},
        )
    conn.execute(sa.text("DELETE FROM global_settings WHERE key = :key"), {"key": _OLD_KEY})


def downgrade() -> None:
    """Write ``enable_registration`` back from ``registration_mode``, then delete the new row."""
    conn = op.get_bind()
    if not _has(conn, _NEW_KEY):
        return
    if not _has(conn, _OLD_KEY):
        conn.execute(
            sa.text("""
                INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id)
                SELECT :old_key,
                       CASE WHEN value = 'open' THEN 'true' ELSE 'false' END,
                       'bool', :description, updated_at, updated_by_user_id
                FROM global_settings WHERE key = :new_key
                """),
            {"new_key": _NEW_KEY, "old_key": _OLD_KEY, "description": _OLD_DESCRIPTION},
        )
    conn.execute(sa.text("DELETE FROM global_settings WHERE key = :key"), {"key": _NEW_KEY})
