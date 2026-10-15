"""Plugin settings: the instance's and each user's values of the fields a plugin declares (release 1.3, workstream X)

Revision ID: 007_plugin_settings
Revises: 006_registration_mode
Create Date: 2026-10-15

Two new tables, empty after the upgrade:

- ``plugin_system_settings``: one value per field for the whole instance, written by an administrator;
- ``plugin_user_settings``: one value per field and user, written by that user; the rows go with the account
  (``ON DELETE CASCADE``).

A row holds a plain value as JSON (``value_json``) or a secret encrypted with a key derived from the instance key
(``secret_ciphertext`` with the id of that key, ``key_id``): exactly one of the two, as two CHECK constraints keep it.
Two tables rather than one with a nullable ``user_id``: in SQLite NULLs never collide in a UNIQUE constraint, so one
table would need two partial unique indexes, which nothing else in the schema uses.

Nothing to convert: no setting existed before. The downgrade drops both tables, and the values and secrets in them are
lost. Each direction checks before it acts, so a run that stopped half way can be run again.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_plugin_settings"
down_revision: Union[str, Sequence[str], None] = "006_registration_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SYSTEM_TABLE = "plugin_system_settings"
_USER_TABLE = "plugin_user_settings"


def _tables(conn: sa.engine.Connection) -> set[str]:
    """Return the names of the tables in the database."""
    return {row[0] for row in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type = 'table'")).fetchall()}


def _value_columns() -> list[sa.Column]:
    """The columns both tables share after their keys: the plain value, the secret and the id of its key."""
    return [
        sa.Column("value_json", sa.Text(), nullable=True),
        sa.Column("secret_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("key_id", sa.String(length=32), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    """Create the two tables, those that are missing."""
    conn = op.get_bind()
    existing = _tables(conn)
    if _SYSTEM_TABLE not in existing:
        op.create_table(
            _SYSTEM_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("family", sa.String(length=16), nullable=False),
            sa.Column("plugin_code", sa.String(length=64), nullable=False),
            sa.Column("field_key", sa.String(length=64), nullable=False),
            *_value_columns(),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
            sa.UniqueConstraint("family", "plugin_code", "field_key", name="uq_plugin_system_settings_field"),
            sa.CheckConstraint("(value_json IS NULL) <> (secret_ciphertext IS NULL)", name="ck_plugin_system_settings_one_value"),
            sa.CheckConstraint("(secret_ciphertext IS NULL) = (key_id IS NULL)", name="ck_plugin_system_settings_key_id"),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        )
    if _USER_TABLE not in existing:
        op.create_table(
            _USER_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("family", sa.String(length=16), nullable=False),
            sa.Column("plugin_code", sa.String(length=64), nullable=False),
            sa.Column("field_key", sa.String(length=64), nullable=False),
            *_value_columns(),
            sa.UniqueConstraint("user_id", "family", "plugin_code", "field_key", name="uq_plugin_user_settings_field"),
            sa.CheckConstraint("(value_json IS NULL) <> (secret_ciphertext IS NULL)", name="ck_plugin_user_settings_one_value"),
            sa.CheckConstraint("(secret_ciphertext IS NULL) = (key_id IS NULL)", name="ck_plugin_user_settings_key_id"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )


def downgrade() -> None:
    """Drop the two tables: the plugin settings and their secrets are lost."""
    conn = op.get_bind()
    existing = _tables(conn)
    for table in (_USER_TABLE, _SYSTEM_TABLE):
        if table in existing:
            op.drop_table(table)
