"""Accounts: single-use account tokens and three new user columns (release 1.3, workstream A)

Revision ID: 005_accounts_invites
Revises: 004_release_1_2_0_schema
Create Date: 2026-10-15

1. ``account_tokens`` — the single-use links of the accounts domain: invitations, password-reset
   links, email verification and the initial administrator's setup link
   (``services/accounts/token_service.py``). Only the SHA-256 of a token is stored: the token itself
   is shown once, to whoever asked for it. ``purpose`` binds a token to one use (a reset link is never
   an invitation), ``expires_at`` bounds its life, ``consumed_at`` and ``revoked_at`` end it.

   - ``user_id`` is the account a token acts on (reset, verification, setup), and its tokens go with
     it (``ON DELETE CASCADE``). An invitation has none: its account does not exist yet.
   - ``created_by_user_id`` and ``consumed_by_user_id`` only record who: deleting that account keeps
     the token and forgets the name (``ON DELETE SET NULL``).
   - A plain ``INTEGER PRIMARY KEY``, without AUTOINCREMENT: the census of decision D1 (plan
     34_accountAndIdReuse) is six tables, and this is not one of them. Tokens are not deleted, only
     consumed or revoked, with one exception: deleting an account takes its own tokens with it, and when
     those were the newest rows the next token gets one of their ids again. An invitation is never among
     them, as it belongs to no account.

2. ``users`` gains three columns:

   - ``session_version`` (``0``): the session generation of the account. It is here so that one
     migration carries the whole schema of workstream A; the code that raises it, and checks it on
     every request, comes in a later lot.
   - ``email_verified_at`` (``NULL``): when the address was verified. Existing accounts stay ``NULL``
     — not verified, which is true; how they are treated once verification is required is decided in
     the logic, not in the data (coordinator decision, 15/10/2026).
   - ``last_seen_version`` (``NULL``): the release whose changelog the user last saw.

   The columns are added with plain ``ALTER TABLE ADD COLUMN``, never with a batch. A batch rebuilds
   ``users`` — create a copy, move the rows, drop the original, rename — and every connection of the
   application runs with ``PRAGMA foreign_keys=ON``: dropping the original would delete, in cascade,
   the rows of every table that references it. ``DROP COLUMN`` in the downgrade rewrites the table in
   place and fires no foreign-key action.

Every step checks before it acts, as 004 does, so a run that stopped half way can be run again.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_accounts_invites"
down_revision: Union[str, Sequence[str], None] = "004_release_1_2_0_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Name and declaration of each new column of ``users``, in the order they are added.
_USER_COLUMNS: tuple[tuple[str, str], ...] = (
    ("session_version", "INTEGER NOT NULL DEFAULT 0"),
    ("email_verified_at", "DATETIME DEFAULT NULL"),
    ("last_seen_version", "VARCHAR(40) DEFAULT NULL"),
)

_TOKEN_INDEXES: tuple[tuple[str, str], ...] = (
    ("ix_account_tokens_purpose_expires_at", "purpose, expires_at"),
    ("ix_account_tokens_user_id", "user_id"),
)


def _columns(conn: sa.engine.Connection, table: str) -> set[str]:
    """Return the current column names of ``table``."""
    return {row[1] for row in conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()}


def _tables(conn: sa.engine.Connection) -> set[str]:
    """Return the names of the tables in the database."""
    return {row[0] for row in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type = 'table'")).fetchall()}


def _upgrade_user_columns(conn: sa.engine.Connection) -> None:
    """Add the new columns of ``users`` that are not there yet."""
    existing = _columns(conn, "users")
    for name, declaration in _USER_COLUMNS:
        if name not in existing:
            conn.execute(sa.text(f"ALTER TABLE users ADD COLUMN {name} {declaration}"))


def _upgrade_account_tokens(conn: sa.engine.Connection) -> None:
    """Create ``account_tokens`` and its indexes, those that are missing."""
    if "account_tokens" not in _tables(conn):
        op.create_table(
            "account_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("purpose", sa.String(length=32), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("grants_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("consumed_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("consumed_by_user_id", sa.Integer(), nullable=True),
            sa.CheckConstraint(
                "purpose IN ('invite', 'password_reset', 'email_verification', 'admin_setup')",
                name="ck_account_tokens_purpose",
            ),
            sa.UniqueConstraint("token_hash", name="uq_account_tokens_token_hash"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["consumed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        )
    for name, columns in _TOKEN_INDEXES:
        conn.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {name} ON account_tokens ({columns})"))


def upgrade() -> None:
    """Add the user columns, then the token table."""
    conn = op.get_bind()
    _upgrade_user_columns(conn)
    _upgrade_account_tokens(conn)


def downgrade() -> None:
    """Drop the token table and the three user columns. Tokens and the column values are lost."""
    conn = op.get_bind()
    if "account_tokens" in _tables(conn):
        op.drop_table("account_tokens")
    existing = _columns(conn, "users")
    for name, _declaration in reversed(_USER_COLUMNS):
        if name in existing:
            # SQLite supports DROP COLUMN since 3.35 (2021); the bundled sqlite3 is well past it.
            conn.execute(sa.text(f"ALTER TABLE users DROP COLUMN {name}"))
