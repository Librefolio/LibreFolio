"""Migration ``006_owner_email_change``: who the instance owner is, and the ``email_change`` token purpose (A5-1b part 2).

On a managed instance the hoster changes the owner's address from the host: it changes ``LIBREFOLIO_ADMIN_EMAIL`` and
restarts. The variable's address cannot identify the owner once it has changed, so the owner is recorded, and the link
the instance emails to the new address is a token of a new purpose. Two steps, in this order:

1. ``users.is_instance_owner`` — ``BOOLEAN NOT NULL DEFAULT 0`` — and the partial unique index
   ``ux_users_instance_owner ON users (is_instance_owner) WHERE is_instance_owner = 1``: at most one owner. Every
   account the upgrade finds gets ``0``: the owner is recorded by the startup sync, which finds it by the variable's
   address. The query that reads the index is ``SELECT id FROM users WHERE is_instance_owner = 1``; its plan is
   ``SEARCH users USING COVERING INDEX ux_users_instance_owner`` (pinned by ``test_migration_006_owner_email_change``).
2. ``account_tokens`` rebuilt (SQLite cannot alter a CHECK in place: ``batch_alter_table`` creates the table again, copies
   the rows and renames it, its indexes recreated) so that ``ck_account_tokens_purpose`` also accepts ``email_change``.
   Nothing references ``account_tokens``; its own foreign keys (``CASCADE`` to the user, ``SET NULL`` for the creator and
   the consumer) are kept.

Every step checks before it acts, so a run stopped half way completes. The downgrade goes back: the index and the
column dropped, the ``email_change`` rows removed (the old CHECK would refuse them), the CHECK restored.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_owner_email_change"
down_revision: Union[str, Sequence[str], None] = "005_release_1_3_0_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OWNER_COLUMN = "is_instance_owner"
_OWNER_INDEX = "ux_users_instance_owner"
_CHECK = "ck_account_tokens_purpose"
_OLD_PURPOSES: tuple[str, ...] = ("invite", "password_reset", "email_verification", "admin_setup")
_NEW_PURPOSES: tuple[str, ...] = (*_OLD_PURPOSES, "email_change")


def _columns(conn: sa.engine.Connection, table: str) -> set[str]:
    """Return the current column names of ``table``."""
    return {row[1] for row in conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()}


def _tokens_sql(conn: sa.engine.Connection) -> str:
    """The ``CREATE TABLE`` text of ``account_tokens`` as SQLite keeps it."""
    return conn.execute(sa.text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'account_tokens'")).scalar_one()


def _check_expression(purposes: tuple[str, ...]) -> str:
    return "purpose IN (" + ", ".join(f"'{purpose}'" for purpose in purposes) + ")"


def _rebuild_tokens(purposes: tuple[str, ...]) -> None:
    """Create ``account_tokens`` again with a CHECK that accepts exactly ``purposes``: rows, keys and indexes kept."""
    with op.batch_alter_table("account_tokens", recreate="always") as batch:
        batch.drop_constraint(_CHECK, type_="check")
        batch.create_check_constraint(_CHECK, _check_expression(purposes))


def upgrade() -> None:
    """The steps of the docstring."""
    conn = op.get_bind()
    if _OWNER_COLUMN not in _columns(conn, "users"):
        conn.execute(sa.text(f"ALTER TABLE users ADD COLUMN {_OWNER_COLUMN} BOOLEAN NOT NULL DEFAULT 0"))
    conn.execute(sa.text(f"CREATE UNIQUE INDEX IF NOT EXISTS {_OWNER_INDEX} ON users ({_OWNER_COLUMN}) WHERE {_OWNER_COLUMN} = 1"))
    if "'email_change'" not in _tokens_sql(conn):
        _rebuild_tokens(_NEW_PURPOSES)


def downgrade() -> None:
    """Back to 005: the owner's mark and the ``email_change`` links are lost."""
    conn = op.get_bind()
    conn.execute(sa.text(f"DROP INDEX IF EXISTS {_OWNER_INDEX}"))
    if _OWNER_COLUMN in _columns(conn, "users"):
        conn.execute(sa.text(f"ALTER TABLE users DROP COLUMN {_OWNER_COLUMN}"))
    if "'email_change'" in _tokens_sql(conn):
        conn.execute(sa.text("DELETE FROM account_tokens WHERE purpose = 'email_change'"))
        _rebuild_tokens(_OLD_PURPOSES)
