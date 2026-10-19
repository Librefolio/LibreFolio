"""Release 1.3.0 schema: accounts, registration mode, plugin settings, email addresses unique regardless of case, and
only the indexes a query uses

Revision ID: 005_release_1_3_0_schema
Revises: 004_release_1_2_0_schema
Create Date: 2026-10-19

CONSOLIDATION NOTE — what this file replaces.

One migration per release, as 004 is for 1.2 (the developer's decision, 19/10/2026). This revision replaces the seven
written during the 1.3 cycle, none of which was ever released:

    005_accounts_invites                steps 1 and 2 below
    006_registration_mode               step 3
    007_plugin_settings                 step 4
    008_registration_invite_default     step 5
    009_email_unique_ignoring_case      step 6
    010_provider_reported_currency      not kept: no ``asset_provider_assignments.reported_currency`` (developer)
    011_provider_exchange_timezone      removed earlier (Z-33r)

A database stamped with one of those ids was made by an unreleased build only. No code handles it (the developer:
no one-off code): the developer journal gives the manual procedure that brings one at 011 or 010 here (plan H,
«Procedura manuale»), and a backup at one of them is refused as from a newer LibreFolio. The equivalence with the
retired chain is a test (``test_migration_005_release_1_3``, against the schema frozen when the chain was deleted).

Every step checks before it acts, so a run that stopped half way can be run again. Columns are added with plain
``ALTER TABLE ADD COLUMN``, never with a batch: a batch rebuilds a table — create a copy, move the rows, drop the
original, rename — and every connection of the application runs with ``PRAGMA foreign_keys=ON``, so dropping the
original would fire the foreign-key action of every row that points at it. ``DROP COLUMN`` (SQLite 3.35+) in the
downgrade changes the table in place and fires none.

────────────────────────────────────────────────────────────────────────────────
1. **Three columns of ``users``** (workstream A): ``session_version`` (``0``), the session generation the server
   checks on every request; ``email_verified_at`` (``NULL``: existing accounts are not verified, which is true; how
   they are treated once verification is required is decided in the logic, not in the data, coordinator decision of
   15/10/2026); ``last_seen_version`` (``NULL``), the release whose changelog the user last saw.

2. **``account_tokens``** (workstream A): the single-use links — invitations, password resets, email verification, the
   initial administrator's setup link (``services/accounts/token_service.py``). Only the SHA-256 of a token is stored.
   ``purpose`` binds a token to one use, ``expires_at`` bounds its life, ``consumed_at`` and ``revoked_at`` end it.
   ``user_id`` is the account a token acts on, and its tokens go with it (``CASCADE``); ``created_by_user_id`` and
   ``consumed_by_user_id`` only record who (``SET NULL``). A plain ``INTEGER PRIMARY KEY``, without AUTOINCREMENT: not
   one of the six tables of decision D1's census (plan 34_accountAndIdReuse). Tokens are not deleted, only consumed or
   revoked, except that deleting an account takes its own tokens with it: when those were the newest rows, the next
   token gets one of their ids again. An invitation is never among them, as it belongs to no account.

3. **``registration_mode`` takes the place of ``enable_registration``** (workstream A): ``open``, ``invite`` or
   ``disabled``. The stored text is read as the settings service read the boolean — ``lower(value)`` among ``true``,
   ``1``, ``yes``, ``on`` — so ``open`` is what the server treated as open and every other value is ``disabled``:
   closed, as it was. The date and the author of the last change are kept; the old row is deleted.

4. **Plugin settings** (workstream X): ``plugin_system_settings``, one value per field for the instance, and
   ``plugin_user_settings``, one per field and user (``CASCADE`` with the account). A row holds a plain value as JSON or
   a secret encrypted with a key derived from the instance key, with the id of that key: exactly one of the two, as two
   CHECK constraints keep it. Two tables rather than one with a nullable ``user_id``: in SQLite NULLs never collide in a
   UNIQUE constraint.

5. **A new install registers by invitation, an upgraded one keeps registration open** (decision 36): where the
   ``registration_mode`` row is missing and ``users`` is not empty, ``open`` is written, the earlier default made
   explicit. A database without accounts is a new install: nothing is written, and the settings service seeds
   ``invite``. A row is never touched, whatever its value.

6. **Email addresses unique regardless of case** (workstream A, decision P18): the unique index
   ``ux_users_email_lower`` on ``lower(email)``. SQLite's built-in ``lower()`` folds A–Z only, so letters outside ASCII
   compare as written (``user_service.email_fold()`` is the same rule). Before the index, every account is read: if two
   share an address apart from case, the upgrade stops, naming the accounts by id and username, never by address
   (workstream E's rule), with the remedy, ``./dev.py user set-email``. It stops where the retired 009 stopped, after
   steps 1 to 5: the remedy reads and writes the accounts through the 1.3 model (the columns of step 1, the tokens of
   step 2), and a run after it goes on from there. Accounts are never merged, and no account row is changed.

7. **Only the indexes a query uses** (plan H's index analysis, 19/10/2026: every query of 67 endpoints read with
   ``EXPLAIN QUERY PLAN``). Thirteen indexes of ``001_initial`` are dropped; ``001`` itself stays as released:
   - the copy of the index a UNIQUE constraint already makes: ``idx_price_history_asset_date``,
     ``idx_asset_provider_asset_id``, ``uq_assets_display_name`` (the index; the UNIQUE on ``display_name`` stays),
     ``ix_brokers_name``, ``ix_users_username``, ``ix_users_email`` (``ux_users_email_lower`` is stronger);
   - the left prefix of another index, which serves the same queries and the same foreign-key checks:
     ``ix_transactions_broker_id``, ``ix_transactions_asset_id``, ``ix_broker_user_access_user_id``,
     ``idx_route_base_quote``, ``ix_fx_conversion_routes_base``;
   - no reader: ``ix_transactions_date`` (every query on transactions is scoped by broker or asset),
     ``ix_fx_conversion_routes_quote`` (a pair is always looked up with its base).
   Removing all thirteen changed no query plan for the worse. The models no longer declare them, and
   ``db validate`` refuses an index equal to, or a left prefix of, another. The rule: ``patterns/alembic.md``.

**Not a step: the decimals of C-97** (quantities keep 10 decimal places and prices 12, issue #43; carried over from the
retired 009): no DDL, no data step.

``transactions.quantity`` was declared ``NUMERIC(18, 6)``, and so were the per-unit cost basis
``transactions.cost_basis_override`` (a price: it is multiplied by the quantity) and the ``open``, ``high``, ``low``,
``close`` and ``adjusted_close`` of ``price_history``. Since 16/10/2026 the declarations in 001_initial read
``NUMERIC(22, 10)`` for the quantity and ``NUMERIC(24, 12)`` for the prices and the cost basis; released SQLite
databases keep their 18, 6, and that is deliberate: the reasoning of 002 and 004 (``VARCHAR(14)``).

SQLite stores these values as a double (REAL; INTEGER for a whole value) whatever the declaration says: a quantity of
``0.12345678`` has always been saved whole. The six decimals were applied in Python: by the model when it read the
value back (``Numeric(18, 6)`` formats it with ``'%.6f'``), and by ``truncate_priceHistory`` when a price was written.
Both change with the code. The model now reads quantities and prices through ``RealDecimal`` (``db/real_decimal.py``),
which gives back the decimal that was written, up to 15 significant digits, what a double keeps exactly. The input
refuses what the column could not give back (``db/precision.decimal_limit_issue``), and provider prices are truncated
to 12 decimals and 15 significant digits. Rebuilding ``transactions`` and ``price_history`` on every installation to
change a number the engine ignores would trade a real risk for no effect, so this migration performs no DDL for it.

Nothing stored is rewritten either (the developer's decision, 16/10/2026). A quantity saved with more than six
decimals, by 1.1, an import or the API, now reads back with its digits, up to ten. A price keeps the six decimals it
was truncated to when it was written. A per-unit cost basis saved with more than six decimals (Auto computes it as a
total divided by the quantity) now reads back with up to twelve. A value with six decimals or fewer reads back exactly
as before, ``10.000000`` included. On the developer's demo data every stored quantity and price reads back identical.

The downgrade goes back step by step: the thirteen indexes again with their ``001`` definitions, then
``ux_users_email_lower``, the plugin tables, ``enable_registration`` from ``registration_mode`` (``open`` is ``true``,
``invite`` and ``disabled`` are ``false``: the old setting had no middle ground), ``account_tokens`` and the three
columns. Tokens, plugin settings and the values of the columns are lost.
"""

import string
from collections import defaultdict
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_release_1_3_0_schema"
down_revision: Union[str, Sequence[str], None] = "004_release_1_2_0_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: SQLite's lower(): A–Z to a–z, nothing else. Written here, not imported: a migration keeps the rule of its day.
_FOLD = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
_EMAIL_INDEX = "ux_users_email_lower"
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
_OLD_REGISTRATION_KEY = "enable_registration"
_REGISTRATION_KEY = "registration_mode"
_REGISTRATION_DESCRIPTION = "Who may create an account: open, invite or disabled"
_OLD_REGISTRATION_DESCRIPTION = "Allow new user registration"
_PLUGIN_SYSTEM_TABLE = "plugin_system_settings"
_PLUGIN_USER_TABLE = "plugin_user_settings"
#: The indexes of ``001_initial`` no query needs (step 7), with their ``001`` definitions for the downgrade.
_REDUNDANT_INDEXES: tuple[tuple[str, str], ...] = (
    ("idx_price_history_asset_date", "CREATE INDEX idx_price_history_asset_date ON price_history (asset_id, date)"),
    ("idx_asset_provider_asset_id", "CREATE INDEX idx_asset_provider_asset_id ON asset_provider_assignments (asset_id)"),
    ("uq_assets_display_name", "CREATE UNIQUE INDEX uq_assets_display_name ON assets (display_name)"),
    ("ix_brokers_name", "CREATE UNIQUE INDEX ix_brokers_name ON brokers (name)"),
    ("ix_users_username", "CREATE UNIQUE INDEX ix_users_username ON users (username)"),
    ("ix_users_email", "CREATE UNIQUE INDEX ix_users_email ON users (email)"),
    ("ix_transactions_broker_id", "CREATE INDEX ix_transactions_broker_id ON transactions (broker_id)"),
    ("ix_transactions_asset_id", "CREATE INDEX ix_transactions_asset_id ON transactions (asset_id)"),
    ("ix_transactions_date", "CREATE INDEX ix_transactions_date ON transactions (date)"),
    ("ix_broker_user_access_user_id", "CREATE INDEX ix_broker_user_access_user_id ON broker_user_access (user_id)"),
    ("idx_route_base_quote", "CREATE INDEX idx_route_base_quote ON fx_conversion_routes (base, quote)"),
    ("ix_fx_conversion_routes_base", "CREATE INDEX ix_fx_conversion_routes_base ON fx_conversion_routes (base)"),
    ("ix_fx_conversion_routes_quote", "CREATE INDEX ix_fx_conversion_routes_quote ON fx_conversion_routes (quote)"),
)


def _columns(conn: sa.engine.Connection, table: str) -> set[str]:
    """Return the current column names of ``table``."""
    return {row[1] for row in conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()}


def _tables(conn: sa.engine.Connection) -> set[str]:
    """Return the names of the tables in the database."""
    return {row[0] for row in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type = 'table'")).fetchall()}


def _indexes(conn: sa.engine.Connection) -> set[str]:
    """Return the names of the indexes in the database."""
    return {row[0] for row in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type = 'index'")).fetchall()}


def _has_setting(conn: sa.engine.Connection, key: str) -> bool:
    """Whether the global setting ``key`` exists."""
    return conn.execute(sa.text("SELECT 1 FROM global_settings WHERE key = :key"), {"key": key}).first() is not None


def _email_duplicates(conn: sa.engine.Connection) -> list[list[tuple[int, str]]]:
    """The groups of accounts whose addresses are the same once folded, more than one account each, by id."""
    groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for account_id, username, email in conn.execute(sa.text("SELECT id, username, email FROM users")).fetchall():
        groups[email.translate(_FOLD)].append((account_id, username))
    return [sorted(group) for group in groups.values() if len(group) > 1]


def _refuse_email_duplicates(conn: sa.engine.Connection) -> None:
    """Step 6, before the index: stop, naming the accounts, if two share an address apart from case."""
    duplicates = _email_duplicates(conn)
    if duplicates:
        groups = "; ".join(", ".join(f"#{account_id} {username!r}" for account_id, username in group) for group in sorted(duplicates))
        raise RuntimeError(
            "Email addresses must be unique regardless of case (release 1.3), and these accounts share one apart from "
            f"upper and lower case: {groups}. Give all but one account of each group another address with "
            "`./dev.py user set-email <username> <address>` (in Docker, with the container stopped: `docker compose run "
            "--rm librefolio python dev.py user set-email <username> <address>`), then start LibreFolio again. No account "
            "was changed."
        )


def _upgrade_user_columns(conn: sa.engine.Connection) -> None:
    """Step 1: add the new columns of ``users`` that are not there yet."""
    existing = _columns(conn, "users")
    for name, declaration in _USER_COLUMNS:
        if name not in existing:
            conn.execute(sa.text(f"ALTER TABLE users ADD COLUMN {name} {declaration}"))


def _upgrade_account_tokens(conn: sa.engine.Connection) -> None:
    """Step 2: create ``account_tokens`` and its indexes, those that are missing."""
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


def _upgrade_registration_mode(conn: sa.engine.Connection) -> None:
    """Step 3: write ``registration_mode`` from ``enable_registration``, then delete the old row."""
    if not _has_setting(conn, _OLD_REGISTRATION_KEY):
        return
    if not _has_setting(conn, _REGISTRATION_KEY):
        conn.execute(
            sa.text("""
                INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id)
                SELECT :new_key,
                       CASE WHEN lower(value) IN ('true', '1', 'yes', 'on') THEN 'open' ELSE 'disabled' END,
                       'str', :description, updated_at, updated_by_user_id
                FROM global_settings WHERE key = :old_key
                """),
            {"new_key": _REGISTRATION_KEY, "old_key": _OLD_REGISTRATION_KEY, "description": _REGISTRATION_DESCRIPTION},
        )
    conn.execute(sa.text("DELETE FROM global_settings WHERE key = :key"), {"key": _OLD_REGISTRATION_KEY})


def _plugin_value_columns() -> list[sa.Column]:
    """The columns both plugin tables share after their keys: the plain value, the secret and the id of its key."""
    return [
        sa.Column("value_json", sa.Text(), nullable=True),
        sa.Column("secret_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("key_id", sa.String(length=32), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def _upgrade_plugin_settings(conn: sa.engine.Connection) -> None:
    """Step 4: create the two plugin settings tables, those that are missing."""
    existing = _tables(conn)
    if _PLUGIN_SYSTEM_TABLE not in existing:
        op.create_table(
            _PLUGIN_SYSTEM_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("family", sa.String(length=16), nullable=False),
            sa.Column("plugin_code", sa.String(length=64), nullable=False),
            sa.Column("field_key", sa.String(length=64), nullable=False),
            *_plugin_value_columns(),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
            sa.UniqueConstraint("family", "plugin_code", "field_key", name="uq_plugin_system_settings_field"),
            sa.CheckConstraint("(value_json IS NULL) <> (secret_ciphertext IS NULL)", name="ck_plugin_system_settings_one_value"),
            sa.CheckConstraint("(secret_ciphertext IS NULL) = (key_id IS NULL)", name="ck_plugin_system_settings_key_id"),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        )
    if _PLUGIN_USER_TABLE not in existing:
        op.create_table(
            _PLUGIN_USER_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("family", sa.String(length=16), nullable=False),
            sa.Column("plugin_code", sa.String(length=64), nullable=False),
            sa.Column("field_key", sa.String(length=64), nullable=False),
            *_plugin_value_columns(),
            sa.UniqueConstraint("user_id", "family", "plugin_code", "field_key", name="uq_plugin_user_settings_field"),
            sa.CheckConstraint("(value_json IS NULL) <> (secret_ciphertext IS NULL)", name="ck_plugin_user_settings_one_value"),
            sa.CheckConstraint("(secret_ciphertext IS NULL) = (key_id IS NULL)", name="ck_plugin_user_settings_key_id"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )


def _upgrade_registration_default(conn: sa.engine.Connection) -> None:
    """Step 5: write ``registration_mode`` = ``open`` where the row is missing and accounts exist."""
    conn.execute(
        sa.text("""
            INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id)
            SELECT :key, 'open', 'str', :description, CURRENT_TIMESTAMP, NULL
            WHERE NOT EXISTS (SELECT 1 FROM global_settings WHERE key = :key)
              AND EXISTS (SELECT 1 FROM users)
            """),
        {"key": _REGISTRATION_KEY, "description": _REGISTRATION_DESCRIPTION},
    )


def upgrade() -> None:
    """The steps of the docstring, in their order."""
    conn = op.get_bind()
    _upgrade_user_columns(conn)
    _upgrade_account_tokens(conn)
    _upgrade_registration_mode(conn)
    _upgrade_plugin_settings(conn)
    _upgrade_registration_default(conn)
    _refuse_email_duplicates(conn)
    conn.execute(sa.text(f"CREATE UNIQUE INDEX IF NOT EXISTS {_EMAIL_INDEX} ON users (lower(email))"))
    for name, _definition in _REDUNDANT_INDEXES:
        conn.execute(sa.text(f"DROP INDEX IF EXISTS {name}"))


def downgrade() -> None:
    """Back to 1.2, step by step: tokens, plugin settings and the values of the new columns are lost."""
    conn = op.get_bind()
    present = _indexes(conn)
    for name, definition in _REDUNDANT_INDEXES:
        if name not in present:
            conn.execute(sa.text(definition))
    conn.execute(sa.text(f"DROP INDEX IF EXISTS {_EMAIL_INDEX}"))
    existing = _tables(conn)
    for table in (_PLUGIN_USER_TABLE, _PLUGIN_SYSTEM_TABLE):
        if table in existing:
            op.drop_table(table)
    if _has_setting(conn, _REGISTRATION_KEY):
        if not _has_setting(conn, _OLD_REGISTRATION_KEY):
            conn.execute(
                sa.text("""
                    INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id)
                    SELECT :old_key,
                           CASE WHEN value = 'open' THEN 'true' ELSE 'false' END,
                           'bool', :description, updated_at, updated_by_user_id
                    FROM global_settings WHERE key = :new_key
                    """),
                {"new_key": _REGISTRATION_KEY, "old_key": _OLD_REGISTRATION_KEY, "description": _OLD_REGISTRATION_DESCRIPTION},
            )
        conn.execute(sa.text("DELETE FROM global_settings WHERE key = :key"), {"key": _REGISTRATION_KEY})
    if "account_tokens" in _tables(conn):
        op.drop_table("account_tokens")
    existing = _columns(conn, "users")
    for name, _declaration in reversed(_USER_COLUMNS):
        if name in existing:
            conn.execute(sa.text(f"ALTER TABLE users DROP COLUMN {name}"))
