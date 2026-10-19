"""Migration ``005_release_1_3_0_schema``: the whole schema of release 1.3 in one revision (lot H-57).

The developer's decisions of 19/10/2026. One migration per release, as ``004`` is for 1.2: the revisions written during
the 1.3 cycle, none of them in a released tag, become one, ``005_release_1_3_0_schema`` on ``004_release_1_2_0_schema``.
It replaces ``005_accounts_invites`` to ``010_provider_reported_currency`` (``011`` had gone already, with Z-33r), and
this file replaces their six test files: their data scenarios, aimed at the one revision.

Variant V4. The old steps in their order — the three ``users`` columns and ``account_tokens`` (old 005),
``registration_mode`` from ``enable_registration`` (006), the two plugin settings tables (007), ``open`` where accounts
exist without a registration row (008), then the check for addresses equal but for A–Z case and
``ux_users_email_lower`` (009) —, without ``asset_provider_assignments.reported_currency`` (010 is not kept), then
``DROP INDEX IF EXISTS`` of the 13 indexes of ``001_initial`` no query needs. The check stops the upgrade where the
retired 009 stopped it, after the steps of 005–008: the remedy it names reads the accounts through the 1.3 model, and
needs their columns. Every step checks before it acts. The downgrade goes back step by step, the 13 indexes again with
their ``001`` definitions.

Why a frozen snapshot. Once the retired files are deleted their chain can no longer run, so what it built was frozen
first: ``fixtures/migrations/schema_1_3_retired_chain_v4.json``, the schema of a new database after
``upgrade 009_email_unique_ignoring_case`` and the 13 ``DROP INDEX`` — every row of ``sqlite_master``, its SQL with
whitespace collapsed, and the rows of every table but ``alembic_version``, none on a new database. It is never
regenerated: the chain that made it is gone, and the file is the only witness of what the one revision must reproduce.
``_snapshot`` is the function that made it, written again here.

The contract pinned here:

1. The revision, in ``005_release_1_3_0_schema.py``, revises ``004`` and is its only child; the chain keeps one head;
   no retired id is left.
2. A new database taken to the revision — by name, not ``head``, so that the pin outlives the next migrations — is the
   frozen snapshot exactly: objects, SQL text, rows.
3. The 1.3 objects at work, with foreign keys on: the defaults of the ``users`` columns; ``account_tokens`` (its CHECK,
   its UNIQUE, three foreign keys with ``CASCADE`` and ``SET NULL``, two indexes); the plugin tables (two CHECKs each,
   one value per field, their foreign keys); ``ux_users_email_lower`` refusing ``Alice@x`` beside ``alice@x``; no
   ``reported_currency``.
4. None of the 13 indexes is left, on a new database or on a populated 1.2 install, and every UNIQUE constraint one of
   them copied or prefixed still refuses a duplicate.
5. ``SQLModel.metadata.create_all`` builds the 1.3 tables as the migrations do, and neither declares any of the 13: on
   each table that held one, the two agree on every index and every unique column set. Guards pin ``_shape`` itself.
6. Registration: ``enable_registration`` becomes ``registration_mode`` as the application read it, date and author
   kept, the old row gone; with accounts and no row, ``open``, written by the upgrade; without accounts, nothing; a
   ``registration_mode`` already there is never touched; the row is the one a new install seeds, but for its value.
7. A populated 1.2 install keeps every row of every table, its users get ``0``, ``NULL``, ``NULL``, its registration
   becomes a mode with its metadata, the new tables are empty, and nothing is violated.
8. Accounts whose addresses are equal but for A–Z stop the upgrade before ``ux_users_email_lower``: a ``RuntimeError``
   in the old wording, the accounts named ``#id 'username'``, no address in the error, the output or the log;
   ``alembic_version`` still ``004``, no ``ux_users_email_lower``, no account row changed; the ``users`` columns and
   ``account_tokens`` there — DDL run before the first DML, which pysqlite commits as it goes —, as the remedy needs
   them. The rest of what the stopped run leaves depends on its transaction, and is not pinned. The remedy the error
   names works on that database, and the run after it reaches the frozen schema. ``Émile@`` beside ``émile@`` is no
   collision.
9. An upgrade stopped half way, and one run again over its own work, end with the frozen schema.
10. The downgrade gives a new database the schema of a new ``004`` one, the 13 indexes with their ``001`` definitions;
    it converts ``registration_mode`` back as the old 006 did; one stopped half way completes; the populated install
    goes down to its own 1.2 schema with every other row, and up again.

Safety and fidelity: ``alembic_harness``. Every database is a file under ``tmp_path``; Alembic runs in this process on
that file alone — a connect listener refuses any other — with ``PRAGMA foreign_keys`` asserted 1 at every step, as
production migrates. Rows are written with plain SQL, the way a real install holds them. The populated 1.2 install is
the v1.1.0 schema and rows of ``test_post_migration`` (every table, gaps, a transfer pair, a deleted user), taken to
``004`` by the real migrations and converted by the post-migration fixes a 1.2 server runs at startup, plus rows only
1.2 writes. ``get_async_engine`` is a tripwire: no lane database.

Red until the cure: Alembic cannot locate ``005_release_1_3_0_schema`` — each test that migrates to it fails saying so,
never as an error of its fixture —, the head does not include it, ``db/models.py`` still declares 12 of the 13 indexes.
Guards, green before and after: the frozen snapshot is what it says, ``_shape`` sees what it must.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import re
import sqlite3
import uuid
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any, NamedTuple, NoReturn, Optional

import pytest
from alembic import command
from sqlalchemy import DateTime
from sqlalchemy.dialects import sqlite as sqlite_dialect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db import post_migration
from backend.app.db import session as db_session
from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS
from backend.app.services.email import flows as email_flows
from backend.app.services.email import verification as email_verification
from backend.test_scripts.test_db.alembic_harness import (
    ALEMBIC_SCRIPT_LOCATION,
    Rows,
    _alembic_config,
    _alembic_connections,
    _connect,
    _copy,
    _create_all,
    _foreign_keys,
    _foreign_keys_on,
    _full_shape,
    _index_list,
    _integrity,
    _known,
    _lineage,
    _migrate,
    _revision,
    _row_changes,
    _rows,
    _scripts,
    _shape,
    _table_info,
    _tables,
    _violations,
)
from backend.test_scripts.test_db.test_post_migration import _install_v110
from backend.test_scripts.test_utils import print_section, print_success

REV_004 = "004_release_1_2_0_schema"
REV_005 = "005_release_1_3_0_schema"
#: The revisions of the 1.3 cycle the one revision replaces; ``011_provider_exchange_timezone`` went before, with Z-33r.
RETIRED_REVISIONS = (
    "005_accounts_invites",
    "006_registration_mode",
    "007_plugin_settings",
    "008_registration_invite_default",
    "009_email_unique_ignoring_case",
    "010_provider_reported_currency",
)
#: What the retired chain left on a new database, variant V4: frozen when the chain was deleted, never regenerated.
SNAPSHOT = Path(__file__).resolve().parents[1] / "fixtures" / "migrations" / "schema_1_3_retired_chain_v4.json"
#: Alembic's own bookkeeping: its row changes with every step, and is asserted on its own.
BOOKKEEPING = frozenset({"alembic_version"})
AUTOINCREMENT_FIX = "autoincrement"

#: The 13 indexes of ``001_initial`` the revision drops — the copy of the index a UNIQUE constraint already makes, the
#: left prefix of another index, or read by no query —, each with its table and its ``001`` definition, whitespace
#: collapsed: what the downgrade recreates.
REDUNDANT_INDEXES: dict[str, tuple[str, str]] = {
    "idx_price_history_asset_date": ("price_history", "CREATE INDEX idx_price_history_asset_date ON price_history (asset_id, date)"),
    "idx_asset_provider_asset_id": ("asset_provider_assignments", "CREATE INDEX idx_asset_provider_asset_id ON asset_provider_assignments (asset_id)"),
    "uq_assets_display_name": ("assets", "CREATE UNIQUE INDEX uq_assets_display_name ON assets (display_name)"),
    "ix_brokers_name": ("brokers", "CREATE UNIQUE INDEX ix_brokers_name ON brokers (name)"),
    "ix_users_username": ("users", "CREATE UNIQUE INDEX ix_users_username ON users (username)"),
    "ix_users_email": ("users", "CREATE UNIQUE INDEX ix_users_email ON users (email)"),
    "ix_transactions_broker_id": ("transactions", "CREATE INDEX ix_transactions_broker_id ON transactions (broker_id)"),
    "ix_transactions_asset_id": ("transactions", "CREATE INDEX ix_transactions_asset_id ON transactions (asset_id)"),
    "ix_transactions_date": ("transactions", "CREATE INDEX ix_transactions_date ON transactions (date)"),
    "ix_broker_user_access_user_id": ("broker_user_access", "CREATE INDEX ix_broker_user_access_user_id ON broker_user_access (user_id)"),
    "idx_route_base_quote": ("fx_conversion_routes", "CREATE INDEX idx_route_base_quote ON fx_conversion_routes (base, quote)"),
    "ix_fx_conversion_routes_base": ("fx_conversion_routes", "CREATE INDEX ix_fx_conversion_routes_base ON fx_conversion_routes (base)"),
    "ix_fx_conversion_routes_quote": ("fx_conversion_routes", "CREATE INDEX ix_fx_conversion_routes_quote ON fx_conversion_routes (quote)"),
}
#: The tables that held one of them: on each, the models and the migration must agree on every index.
INDEXED_TABLES = tuple(sorted({table for table, _definition in REDUNDANT_INDEXES.values()}))
#: The entries of ``_shape`` about indexes: those written with ``CREATE INDEX``, and every column set held unique.
INDEX_ENTRIES = ("indexes (name, columns, unique)", "unique column sets")

#: The three columns the revision adds to ``users``, in their order, each as the revision declares it.
USER_COLUMNS = {
    "session_version": "INTEGER NOT NULL DEFAULT 0",
    "email_verified_at": "DATETIME DEFAULT NULL",
    "last_seen_version": "VARCHAR(40) DEFAULT NULL",
}
#: The statements that add them, as the revision runs them.
ADD_USER_COLUMNS = tuple(f"ALTER TABLE users ADD COLUMN {name} {declaration}" for name, declaration in USER_COLUMNS.items())
#: What every user the upgrade finds gets in them, ``session_version`` an integer: no backfill, ``email_verified_at``
#: included (the developer's decision of 15/10/2026).
EXISTING_USER_VALUES = (0, None, None)

PURPOSES = ("invite", "password_reset", "email_verification", "admin_setup")
#: column: (target table, target column, ON DELETE)
TOKEN_FOREIGN_KEYS = {
    "user_id": ("users", "id", "CASCADE"),
    "created_by_user_id": ("users", "id", "SET NULL"),
    "consumed_by_user_id": ("users", "id", "SET NULL"),
}
TOKEN_INDEXES = {
    "ix_account_tokens_purpose_expires_at": ("purpose", "expires_at"),
    "ix_account_tokens_user_id": ("user_id",),
}
TOKEN_CHECK = "ck_account_tokens_purpose"
TOKEN_UNIQUE = "uq_account_tokens_token_hash"

SYSTEM_TABLE, USER_TABLE = "plugin_system_settings", "plugin_user_settings"
PLUGIN_TABLES = (SYSTEM_TABLE, USER_TABLE)
#: The tables release 1.3 adds.
NEW_TABLES = frozenset({"account_tokens", SYSTEM_TABLE, USER_TABLE})
KEY_ID = "0123456789abcdef0123456789abcdef"
BLOB = b"\x01" + bytes(range(12)) + b"ciphertext-and-tag-of-test"
#: Rows the two CHECKs of a plugin table refuse, each with the CHECK that refuses it.
BROKEN_VALUES = [
    pytest.param({"value_json": None}, "one_value", id="neither-value-nor-secret"),
    pytest.param({"value_json": '"us"', "ciphertext": BLOB, "key_id": KEY_ID}, "one_value", id="value-and-secret"),
    pytest.param({"value_json": None, "ciphertext": BLOB}, "key_id", id="secret-without-key-id"),
    pytest.param({"value_json": '"us"', "key_id": KEY_ID}, "key_id", id="key-id-without-secret"),
]

EMAIL_INDEX = "ux_users_email_lower"
#: How the refusal opens and ends, and the remedy it names: the wording of the retired 009, kept.
REFUSAL_OPENING = "Email addresses must be unique regardless of case (release 1.3), and these accounts share one apart from upper and lower case: "
REMEDY = "./dev.py user set-email"
REFUSAL_CLOSING = "No account was changed."
#: What the accounts written as rows hold for a hash: nobody signs in with them.
MARKER_HASH = "$argon2id$h57-marker"
#: An account as a row, in plain SQL, with an id of its own and the columns of 1.2: at 004 and at the revision alike.
INSERT_ACCOUNT = "INSERT INTO users (id, username, email, hashed_password, is_active, is_superuser, created_at, updated_at) VALUES (?, ?, ?, ?, 1, 0, ?, ?)"
#: The SQL loggers: below WARNING they print every statement and every row read — the addresses the check reads
#: included. ``configure_logging`` sets them to WARNING: a running server never writes those records.
SQL_LOGGERS = ("aiosqlite", "sqlalchemy.engine", "sqlalchemy.pool")
#: Removed for the remedy: an email it might send must find no transport, and no account variable applies.
INHERITED_PREFIXES = ("LIBREFOLIO_SMTP_", "LIBREFOLIO_ADMIN_")
INHERITED_VARIABLES = ("LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS")
USER_CLI_MODULE = "scripts.user_cli"
#: What the remedy reads and writes through the 1.3 model: ``users`` with its three new columns, and ``account_tokens``.
#: DDL the upgrade runs before its first DML, which pysqlite commits as it goes: there after the duplicate check stops it.
REMEDY_NEEDS = ("account_tokens", "users")

OLD_KEY = "enable_registration"
NEW_KEY = "registration_mode"
#: The value_type of every text setting in ``schemas/settings.py``: what a new install seeds.
NEW_TYPE = "str"
NEW_DESCRIPTION = "Who may create an account: open, invite or disabled"
OLD_DESCRIPTION = "Allow new user registration"
#: What an install with accounts and no row ran with until 1.3, and what the upgrade writes for it (decision 36).
OPEN = "open"
# A row written before the upgrade ran, with metadata the upgrade never writes: the 1.1 spelling of the type, a
# description of its own.
EARLIER_TYPE = "string"
EARLIER_DESCRIPTION = "Registration, as an administrator left it"
# The row of the 1.1 install (test_post_migration.V110_ROWS): 'false', written by alice (user 1) on 2025-05-01.
V110_ROW = ("false", "bool", "Allow new users to register", "2025-05-01 10:00:00.000000", 1)
V110_ROW_STAMP, V110_ROW_AUTHOR = V110_ROW[3], V110_ROW[4]

# How get_setting_value read a "bool" until 1.3: value.lower() in ("true", "1", "yes", "on"), no strip.
OPEN_SPELLINGS = ("true", "TRUE", "1", "yes", "ON", "On")
CLOSED_SPELLINGS = ("false", "0", "no", "off", "", "maybe", " true", "yes\n", "2")
CONVERSIONS = [pytest.param(value, "open", id=f"{value!r}->open") for value in OPEN_SPELLINGS] + [pytest.param(value, "disabled", id=f"{value!r}->disabled") for value in CLOSED_SPELLINGS]
DOWNGRADES = [pytest.param("open", "true", id="open->true"), pytest.param("invite", "false", id="invite->false"), pytest.param("disabled", "false", id="disabled->false")]
# users.is_active of the only account: an account counts whether it may sign in or not.
ACCOUNTS = [pytest.param(1, id="an-active-account"), pytest.param(0, id="only-an-inactive-account")]
# How users came to be empty: never filled; never filled, other settings written; filled, then emptied.
NO_ACCOUNTS = [pytest.param("never", id="never-an-account"), pytest.param("settings", id="never-an-account-other-settings"), pytest.param("deleted", id="every-account-deleted")]
# A registration_mode already there before the upgrade: alone, or beside an enable_registration that says true.
KEPT = [pytest.param(value, False, id=f"{value!r}-alone") for value in ("open", "invite", "disabled", "OPEN", "", "maybe")] + [pytest.param(value, True, id=f"{value!r}-beside-true") for value in ("invite", "disabled")]

STAMP = "2026-10-15 09:30:00.000000"
LATER = "2026-10-22 09:30:00.000000"
NEIGHBOUR_STAMP = "2026-10-16 07:00:00.000000"

#: A user with the columns 1.2 always wrote — at 004 and at the revision alike —, the 1.3 ones left to their defaults.
INSERT_USER = "INSERT INTO users (username, email, hashed_password, created_at, updated_at) VALUES (?, ?, '$argon2id$test', ?, ?)"
INSERT_BROKER = "INSERT INTO brokers (name, created_at, updated_at) VALUES (?, ?, ?)"
INSERT_ASSET = "INSERT INTO assets (display_name, currency, asset_type, active, created_at, updated_at) VALUES (?, 'EUR', 'STOCK', 1, ?, ?)"
INSERT_PRICE = "INSERT INTO price_history (asset_id, date, close, currency, source_plugin_key, fetched_at) SELECT id, ?, 1.5, 'EUR', 'manual', ? FROM assets WHERE display_name = ?"
INSERT_ASSIGNMENT = "INSERT INTO asset_provider_assignments (asset_id, provider_code, identifier, identifier_type, created_at, updated_at) SELECT id, 'yfinance', ?, 'TICKER', ?, ? FROM assets WHERE display_name = ?"


class Duplicate(NamedTuple):
    """A UNIQUE constraint one of the 13 copied or prefixed: its table and columns, and the rows a test writes, the last
    of them the same key again; ``set_aside``, a stronger index that would answer before the constraint, dropped first.
    """

    table: str
    columns: tuple[str, ...]
    writes: tuple[tuple[str, tuple[Any, ...]], ...]
    set_aside: Optional[str] = None


DUPLICATES = {
    "users.username": Duplicate("users", ("username",), ((INSERT_USER, ("taken", "first@example.test", STAMP, STAMP)), (INSERT_USER, ("taken", "second@example.test", STAMP, STAMP)))),
    "users.email": Duplicate("users", ("email",), ((INSERT_USER, ("first", "same@example.test", STAMP, STAMP)), (INSERT_USER, ("second", "same@example.test", STAMP, STAMP))), set_aside=EMAIL_INDEX),
    "brokers.name": Duplicate("brokers", ("name",), ((INSERT_BROKER, ("Broker Unique", STAMP, STAMP)), (INSERT_BROKER, ("Broker Unique", LATER, LATER)))),
    "assets.display_name": Duplicate("assets", ("display_name",), ((INSERT_ASSET, ("Asset Unique", STAMP, STAMP)), (INSERT_ASSET, ("Asset Unique", LATER, LATER)))),
    "price_history.asset_id+date": Duplicate("price_history", ("asset_id", "date"), ((INSERT_ASSET, ("Priced", STAMP, STAMP)), (INSERT_PRICE, ("2026-01-02", STAMP, "Priced")), (INSERT_PRICE, ("2026-01-02", LATER, "Priced")))),
    "asset_provider_assignments.asset_id": Duplicate("asset_provider_assignments", ("asset_id",), ((INSERT_ASSET, ("Assigned", STAMP, STAMP)), (INSERT_ASSIGNMENT, ("FIRST", STAMP, STAMP, "Assigned")), (INSERT_ASSIGNMENT, ("SECOND", LATER, LATER, "Assigned")))),
}

#: Upgrades stopped half way, as a database at 004 holds them, the revision still 004: each step a statement of the run
#: itself (``"sql"``), or an object the run creates, as the frozen snapshot declares it (``"frozen"``).
STOPPED_UPGRADES: dict[str, tuple[tuple[str, str], ...]] = {
    "after-its-first-alter": (("sql", ADD_USER_COLUMNS[0]),),
    "after-account-tokens": (
        ("sql", ADD_USER_COLUMNS[0]),
        ("sql", ADD_USER_COLUMNS[1]),
        ("sql", ADD_USER_COLUMNS[2]),
        ("frozen", "account_tokens"),
        ("frozen", "ix_account_tokens_purpose_expires_at"),
        ("frozen", "ix_account_tokens_user_id"),
    ),
    "a-plugin-table-the-email-index-and-three-indexes-gone": (
        ("frozen", SYSTEM_TABLE),
        ("frozen", EMAIL_INDEX),
        ("sql", "DROP INDEX ix_users_username"),
        ("sql", "DROP INDEX ix_transactions_date"),
        ("sql", "DROP INDEX idx_route_base_quote"),
    ),
}

#: The 1.3 tables the models and the migration must build alike, each with the reader that compares them:
#: ``_full_shape`` also compares declared types, unique constraint names and CHECK texts, all named on these two.
MODELLED_TABLES = [
    pytest.param("users", _shape, id="users"),
    pytest.param("account_tokens", _shape, id="account_tokens"),
    pytest.param(SYSTEM_TABLE, _full_shape, id=SYSTEM_TABLE),
    pytest.param(USER_TABLE, _full_shape, id=USER_TABLE),
]

A26_INDEXES_KEY = "indexes (name, columns, unique)"
#: An index on an expression of users, as SQLite reports its key: ``_index_list`` names it by its text.
A26_EXPRESSION = "lower(username)"
A26_PROBE_INDEX = "ix_a26_probe"

# The 1.2 tables that point at users: what a rebuild of users would empty, or unlink, with foreign keys on.
CHILDREN_OF_USERS = frozenset({"user_settings", "broker_user_access", "global_settings", "user_onboarding_progress", "user_onboarding_step_progress"})

# Rows only a 1.2 server writes, on top of the 1.1 install it upgraded and converted. Erin signed up after the upgrade:
# AUTOINCREMENT gives her an id above every id ever used. Her onboarding rows are created lazily, as the service does.
ROWS_1_2 = """
PRAGMA foreign_keys = ON;
BEGIN;

INSERT INTO users (username, email, hashed_password, is_active, is_superuser, login_count,
                   donation_popup_last_shown_at, donation_popup_logins_since_shown, created_at, updated_at) VALUES
    ('erin', 'erin@example.test', '$argon2id$erin', 1, 0, 2, NULL, 2, '2026-09-25 08:00:00.000000', '2026-09-25 08:00:00.000000');

INSERT INTO user_settings (user_id, base_currency, language, theme, avatar_url, created_at, updated_at)
    SELECT id, 'EUR', 'it', 'dark', NULL, '2026-09-25 08:00:00.000000', '2026-09-25 08:00:00.000000' FROM users WHERE username = 'erin';

INSERT INTO user_onboarding_progress (user_id, flow, status, version, created_at, updated_at, completed_at, skipped_at)
    SELECT id, 'welcome', 'completed', 1, '2026-09-25 08:00:01.000000', '2026-09-25 08:05:00.000000', '2026-09-25 08:05:00.000000', NULL FROM users WHERE username = 'erin';
INSERT INTO user_onboarding_progress (user_id, flow, status, version, created_at, updated_at, completed_at, skipped_at)
    SELECT id, 'intro_tour', 'pending', 1, '2026-09-25 08:00:01.000000', '2026-09-25 08:00:01.000000', NULL, NULL FROM users WHERE username = 'erin';
INSERT INTO user_onboarding_step_progress (user_id, flow, step_id, status, version, created_at, updated_at, completed_at, skipped_at)
    SELECT id, 'import_guide', 'import.upload', 'pending', 1, '2026-09-25 08:00:01.000000', '2026-09-25 08:00:01.000000', NULL, NULL FROM users WHERE username = 'erin';

INSERT INTO broker_user_access (user_id, broker_id, role, share_percentage, created_at, updated_at)
    SELECT id, 1, 'VIEWER', 0, '2026-09-25 08:10:00.000000', '2026-09-25 08:10:00.000000' FROM users WHERE username = 'erin';

INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id)
    SELECT 'session_ttl_hours', '48', 'int', 'Session cookie TTL in hours', '2026-09-26 09:00:00.000000', id FROM users WHERE username = 'erin';

-- 004 seeded the flag on the INDEX assets only; a user then offered a bond for comparison.
UPDATE assets SET is_benchmark = 1 WHERE id = 4;
-- An existing user went through the tour the upgrade had marked skipped.
UPDATE user_onboarding_progress
   SET status = 'completed', completed_at = '2026-09-27 10:00:00.000000', skipped_at = NULL, updated_at = '2026-09-27 10:00:00.000000'
 WHERE user_id = 1 AND flow = 'intro_tour';

COMMIT;
"""

# Five distinct 64-hex-character hashes, as hash_token writes them.
RESET_HASH, ADMIN_INVITE_HASH, VERIFICATION_HASH, CONSUMED_INVITE_HASH, SETUP_HASH = (str(n) * 64 for n in range(1, 6))

# What a 1.3 server writes once at the revision: values of their own in the new user columns, tokens pointing at users
# through all three foreign keys, plugin settings of the instance and of users, secrets included — the rows a careless
# downgrade would have to get rid of first.
ROWS_1_3 = f"""
PRAGMA foreign_keys = ON;
BEGIN;

UPDATE users SET session_version = 3, email_verified_at = '2026-10-02 08:00:00.000000', last_seen_version = '1.3.0' WHERE username = 'alice';
UPDATE users SET session_version = 1, last_seen_version = '1.2.0' WHERE username = 'carol';
UPDATE users SET email_verified_at = '2026-10-03 09:30:00.000000' WHERE username = 'erin';

INSERT INTO account_tokens (purpose, token_hash, user_id, email, grants_admin, created_by_user_id, created_at, expires_at, consumed_at, revoked_at, consumed_by_user_id) VALUES
    -- alice's reset, asked for by carol, used by dave: the three foreign keys at once
    ('password_reset', '{RESET_HASH}', 1, NULL, 0, 3, '{STAMP}', '{LATER}', '2026-10-15 09:40:00.000000', NULL, 4),
    -- an admin invite alice created, still pending
    ('invite', '{ADMIN_INVITE_HASH}', NULL, 'frank@example.test', 1, 1, '{STAMP}', '{LATER}', NULL, NULL, NULL),
    -- dave's e-mail verification, pending
    ('email_verification', '{VERIFICATION_HASH}', 4, NULL, 0, NULL, '{STAMP}', '{LATER}', NULL, NULL, NULL);

INSERT INTO account_tokens (purpose, token_hash, user_id, email, grants_admin, created_by_user_id, created_at, expires_at, consumed_at, revoked_at, consumed_by_user_id)
    -- an invite erin created, consumed by carol
    SELECT 'invite', '{CONSUMED_INVITE_HASH}', NULL, NULL, 0, id, '{STAMP}', '{LATER}', '2026-10-16 11:00:00.000000', NULL, 3 FROM users WHERE username = 'erin';
INSERT INTO account_tokens (purpose, token_hash, user_id, email, grants_admin, created_by_user_id, created_at, expires_at, consumed_at, revoked_at, consumed_by_user_id)
    -- erin's setup link, revoked
    SELECT 'admin_setup', '{SETUP_HASH}', id, NULL, 0, NULL, '{STAMP}', '{LATER}', NULL, '2026-10-15 10:00:00.000000', NULL FROM users WHERE username = 'erin';

INSERT INTO plugin_system_settings (family, plugin_code, field_key, value_json, secret_ciphertext, key_id, updated_at, updated_by_user_id)
    SELECT 'asset', 'lab', 'region', '"us"', NULL, NULL, '{STAMP}', id FROM users WHERE username = 'alice';
INSERT INTO plugin_system_settings (family, plugin_code, field_key, value_json, secret_ciphertext, key_id, updated_at, updated_by_user_id)
    SELECT 'asset', 'lab', 'api_key', NULL, X'{BLOB.hex()}', '{KEY_ID}', '{STAMP}', id FROM users WHERE username = 'erin';
INSERT INTO plugin_system_settings (family, plugin_code, field_key, value_json, secret_ciphertext, key_id, updated_at, updated_by_user_id) VALUES
    ('fx', 'LAB', 'decimals', '3', NULL, NULL, '{STAMP}', NULL);
INSERT INTO plugin_user_settings (user_id, family, plugin_code, field_key, value_json, secret_ciphertext, key_id, updated_at)
    SELECT id, 'asset', 'lab', 'limit', '7', NULL, NULL, '{STAMP}' FROM users WHERE username = 'alice';
INSERT INTO plugin_user_settings (user_id, family, plugin_code, field_key, value_json, secret_ciphertext, key_id, updated_at)
    SELECT id, 'asset', 'lab', 'token', NULL, X'{BLOB.hex()}', '{KEY_ID}', '{STAMP}' FROM users WHERE username = 'erin';

COMMIT;
"""

#: A ``global_settings`` row as SQLite holds it: (value, value_type, description, updated_at, updated_by_user_id).
Setting = tuple[str, str, Optional[str], str, Optional[int]]


# =============================================================================
# HELPERS — the revision, and the schema as the snapshot reads it
# =============================================================================


def _missing_005() -> Optional[str]:
    """Why nothing can be migrated to ``005_release_1_3_0_schema`` yet, or None when Alembic knows the revision."""
    if _known(REV_005):
        return None
    return f"red until H-57: Alembic cannot locate {REV_005}; the chain's heads are {list(_scripts().get_heads())}"


def _require_005() -> None:
    """Barrier of the tests that migrate to the revision themselves: the test fails, saying why, rather than erroring in Alembic."""
    missing = _missing_005()
    if missing is not None:
        pytest.fail(missing, pytrace=False)


def _ran[ResultT](result: ResultT | str) -> ResultT:
    """The result of a fixture that migrates to the revision, or the test fails with the reason the fixture could not."""
    if isinstance(result, str):
        pytest.fail(result, pytrace=False)
    return result


def _assert_includes_005(db: Path) -> None:
    """Barrier: ``db`` is at ``005_release_1_3_0_schema`` or above; otherwise nothing that follows is about it."""
    revision = _revision(db)
    assert REV_005 in _lineage(revision), f"red until H-57: the database is at {revision}, which does not include {REV_005}: the assertions that follow would say nothing about the revision"


def _collapsed(sql: Optional[str]) -> Optional[str]:
    """``sql`` with every run of whitespace one space, trimmed; None for an object without SQL (an index SQLite makes for a constraint)."""
    return re.sub(r"\s+", " ", sql).strip() if sql else None


def _snapshot(db: Path) -> dict[str, Any]:
    """``snapshot()`` of the script that froze ``SNAPSHOT``, written again: every row of ``sqlite_master`` as ``[type, name, tbl_name, sql]``, its SQL with whitespace collapsed, by type and name; and, for the tables that have any, the rows of every table but ``alembic_version`` and SQLite's own, each as JSON, sorted."""
    with _connect(db) as conn:
        objects = [[kind, name, table, _collapsed(sql)] for kind, name, table, sql in conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name")]
        tables = [name for kind, name, _table, _sql in objects if kind == "table" and not name.startswith("sqlite_") and name not in BOOKKEEPING]
        rows = {table: sorted(json.dumps(list(row), default=str) for row in conn.execute(f'SELECT * FROM "{table}"')) for table in tables}
    return {"objects": objects, "rows": {table: content for table, content in rows.items() if content}}


def _raw_schema(db: Path) -> list[tuple[Any, ...]]:
    """Every row of ``sqlite_master`` but the root page, its SQL as written, by type and name."""
    with _connect(db) as conn:
        return conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name").fetchall()


def _declared(objects: list[Any], names: Iterable[str]) -> dict[str, Optional[str]]:
    """The SQL of the objects ``names`` among ``objects`` (``[type, name, tbl_name, sql]``, as ``_snapshot`` lists them), by name; an object missing is missing."""
    wanted = set(names)
    return {name: sql for _kind, name, _table, sql in objects if name in wanted}


def _schema_differences(expected: list[Any], actual: list[Any]) -> dict[str, list[Any]]:
    """What differs between two lists of ``[type, name, tbl_name, sql]``, by type and name: the objects missing, the unexpected ones, and those whose table or SQL differ."""
    wanted = {(kind, name): (table, sql) for kind, name, table, sql in expected}
    found = {(kind, name): (table, sql) for kind, name, table, sql in actual}
    differences = {
        "missing": sorted(key for key in wanted if key not in found),
        "unexpected": sorted(key for key in found if key not in wanted),
        "different (object, expected, found)": [(key, wanted[key], found[key]) for key in sorted(wanted.keys() & found.keys()) if wanted[key] != found[key]],
    }
    return {kind: entries for kind, entries in differences.items() if entries}


def _redundant_present(db: Path) -> dict[str, Optional[str]]:
    """The indexes of ``REDUNDANT_INDEXES`` that ``db`` holds, each with its SQL, whitespace collapsed."""
    with _connect(db) as conn:
        indexes = conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'index'").fetchall()
    return {name: _collapsed(sql) for name, sql in indexes if name in REDUNDANT_INDEXES}


def _index_entries(db: Path, table: str) -> dict[str, Any]:
    """The entries of ``_shape`` about the indexes of ``table``: the comparison of the models with the migration, on indexes only."""
    shape = _shape(db, table)
    assert shape is not None, f"barrier: {db.parent.name} has no {table} table"
    return {key: shape[key] for key in INDEX_ENTRIES}


def _statements(steps: tuple[tuple[str, str], ...], frozen: dict[str, Any]) -> list[str]:
    """The SQL of each step of ``STOPPED_UPGRADES``: a statement as it is, or the frozen snapshot's SQL of the object it names."""
    sql_of = {name: sql for _kind, name, _table, sql in frozen["objects"]}
    return [sql_of[value] if source == "frozen" else value for source, value in steps]


# =============================================================================
# HELPERS — settings, users, tokens and plugin settings, in plain SQL
# =============================================================================


def _settings(db: Path) -> dict[str, Setting]:
    """Every row of ``global_settings``, by key, exactly as SQLite holds it."""
    with _connect(db) as conn:
        rows = conn.execute("SELECT key, value, value_type, description, updated_at, updated_by_user_id FROM global_settings").fetchall()
    return {key: (value, value_type, description, updated_at, updated_by) for key, value, value_type, description, updated_at, updated_by in rows}


def _registration(settings: dict[str, Setting]) -> dict[str, Setting]:
    """``settings`` reduced to the two rows the registration steps are about."""
    return {key: setting for key, setting in settings.items() if key in (OLD_KEY, NEW_KEY)}


def _others(settings: dict[str, Setting]) -> dict[str, Setting]:
    """``settings`` without the two rows the registration steps are about."""
    return {key: setting for key, setting in settings.items() if key not in (OLD_KEY, NEW_KEY)}


def _write_setting(conn: sqlite3.Connection, key: str, setting: Setting) -> None:
    """One ``global_settings`` row, written as a real install holds it."""
    conn.execute("INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id) VALUES (?, ?, ?, ?, ?, ?)", (key, *setting))


def _write_neighbours(conn: sqlite3.Connection, author: int) -> dict[str, Setting]:
    """Two other settings beside the registration row, one with an author and one without; what was written, by key."""
    neighbours: dict[str, Setting] = {
        "session_ttl_hours": ("48", "int", "Session cookie TTL in hours", NEIGHBOUR_STAMP, author),
        "default_language": ("it", "str", None, NEIGHBOUR_STAMP, None),
    }
    for key, setting in neighbours.items():
        _write_setting(conn, key, setting)
    return neighbours


def _without_registration_rows(rows: Rows) -> Rows:
    """Every table but Alembic's bookkeeping, with ``global_settings`` stripped of the two rows the registration steps are about."""
    kept: Rows = {}
    for table, (columns, content) in rows.items():
        if table in BOOKKEEPING:
            continue
        if table == "global_settings":
            key_at = columns.index("key")
            kept[table] = (columns, [row for row in content if row[key_at] not in (OLD_KEY, NEW_KEY)])
        else:
            kept[table] = (columns, content)
    return kept


def _insert_user(conn: sqlite3.Connection, username: str, *, email: Optional[str] = None) -> int:
    """A user with the columns 1.2 always wrote, the 1.3 ones left to their defaults: at 004 and at the revision alike."""
    return conn.execute(INSERT_USER, (username, email or f"{username}@example.test", STAMP, STAMP)).lastrowid


def _accounts(db: Path) -> int:
    """How many rows ``users`` holds, active or not: the condition the ``open`` step reads."""
    with _connect(db) as conn:
        return conn.execute("SELECT count(*) FROM users").fetchone()[0]


def _leave_no_account(conn: sqlite3.Connection, history: str) -> None:
    """``users`` empty, one of three ways: never filled; never filled, other settings written; filled, then emptied."""
    if history == "settings":
        _write_setting(conn, "session_ttl_hours", ("48", "int", "Session cookie TTL in hours", STAMP, None))
        _write_setting(conn, "default_language", ("it", "str", None, STAMP, None))
    elif history == "deleted":
        account = _insert_user(conn, "gone")
        _write_neighbours(conn, account)
        assert conn.execute("DELETE FROM users WHERE id = ?", (account,)).rowcount == 1, "setup: the only account is deleted"


def _new_user_columns(db: Path) -> dict[int, tuple[Any, ...]]:
    """``{user id: (session_version, email_verified_at, last_seen_version)}``, with ``session_version`` as SQLite stores it."""
    with _connect(db) as conn:
        rows = conn.execute("SELECT id, session_version, typeof(session_version), email_verified_at, last_seen_version FROM users").fetchall()
    return {user_id: (version if kind == "integer" else f"{version!r} stored as {kind}", verified, seen) for user_id, version, kind, verified, seen in rows}


def _tables_pointing_at_users(db: Path) -> set[str]:
    """The tables with at least one row whose foreign key points at an existing user."""
    found: set[str] = set()
    with _connect(db) as conn:
        tables = [name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()]
        for table in tables:
            columns = [column for _id, _seq, target, column, *_rest in conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall() if target == "users"]
            if any(conn.execute(f'SELECT 1 FROM "{table}" WHERE "{column}" IN (SELECT id FROM users) LIMIT 1').fetchone() for column in columns):
                found.add(table)
    return found


def _utc_now() -> datetime:
    """Now, as the database holds a time: UTC, without an offset."""
    return datetime.now(UTC).replace(tzinfo=None)


def _read_back(stamp: Any) -> datetime:
    """``stamp`` as the application reads ``global_settings.updated_at``: through SQLAlchemy's ``DateTime`` on SQLite."""
    dialect = sqlite_dialect.dialect()
    read = DateTime().dialect_impl(dialect).result_processor(dialect, None)
    assert read is not None, "setup: SQLAlchemy reads a SQLite DateTime through a result processor"
    return read(stamp)


def _assert_written_by_the_upgrade(setting: Optional[Setting], started: datetime, finished: datetime) -> None:
    """``setting`` is the row the upgrade writes for an install with accounts and no row: ``open``, ``str``, the frozen description, nobody's, at the UTC time of the upgrade.

    ``updated_at`` is read back the way the application reads it, and must be what every other timestamp of the database
    is: text without an offset, in UTC. The window opens at the second the upgrade started: ``CURRENT_TIMESTAMP`` has no
    fraction.
    """
    assert setting is not None, f"the install has accounts and no {NEW_KEY}: the upgrade must write it, {OPEN!r}"
    value, value_type, description, updated_at, updated_by = setting
    assert (value, value_type, description, updated_by) == (OPEN, NEW_TYPE, NEW_DESCRIPTION, None), f"{NEW_KEY} must be {OPEN!r}, value_type {NEW_TYPE!r}, described {NEW_DESCRIPTION!r}, signed by nobody; got {setting}"
    assert isinstance(updated_at, str) and updated_at, f"updated_at must be a timestamp, is {updated_at!r}"
    try:
        written = _read_back(updated_at)
    except (TypeError, ValueError) as error:
        pytest.fail(f"updated_at {updated_at!r} is not a timestamp the application can read back: {error}")
    assert written.tzinfo is None, f"updated_at {updated_at!r} carries an offset: the application would read an aware datetime where every other timestamp of the database is naive UTC"
    assert started.replace(microsecond=0) <= written <= finished, f"updated_at {updated_at!r} must be the UTC time of the upgrade, between {started:%Y-%m-%d %H:%M:%S} and {finished:%Y-%m-%d %H:%M:%S}"


def _token_hash(n: int) -> str:
    """A distinct 64-hex-character hash, as ``hash_token`` writes them."""
    return f"{n:064x}"


def _insert_token(conn: sqlite3.Connection, purpose: str, token_hash: str, **columns: Any) -> int:
    """An ``account_tokens`` row with the NOT NULL columns filled in and ``columns`` on top (``grants_admin`` left to its default unless given)."""
    values = {"purpose": purpose, "token_hash": token_hash, "created_at": STAMP, "expires_at": LATER, **columns}
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    return conn.execute(f"INSERT INTO account_tokens ({names}) VALUES ({marks})", tuple(values.values())).lastrowid


def _token_links(conn: sqlite3.Connection) -> dict[int, tuple[Optional[int], Optional[int], Optional[int]]]:
    """``{token id: (user_id, created_by_user_id, consumed_by_user_id)}`` for every token."""
    return {token_id: (user_id, created_by, consumed_by) for token_id, user_id, created_by, consumed_by in conn.execute("SELECT id, user_id, created_by_user_id, consumed_by_user_id FROM account_tokens").fetchall()}


def _insert_system(conn: sqlite3.Connection, key: str, *, family: str = "asset", code: str = "lab", value_json: Optional[str] = '"us"', ciphertext: Optional[bytes] = None, key_id: Optional[str] = None, author: Optional[int] = None) -> int:
    return conn.execute(
        f"INSERT INTO {SYSTEM_TABLE} (family, plugin_code, field_key, value_json, secret_ciphertext, key_id, updated_at, updated_by_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (family, code, key, value_json, ciphertext, key_id, STAMP, author),
    ).lastrowid


def _insert_user_setting(conn: sqlite3.Connection, user_id: int, key: str, *, family: str = "asset", code: str = "lab", value_json: Optional[str] = "7", ciphertext: Optional[bytes] = None, key_id: Optional[str] = None) -> int:
    return conn.execute(
        f"INSERT INTO {USER_TABLE} (user_id, family, plugin_code, field_key, value_json, secret_ciphertext, key_id, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, family, code, key, value_json, ciphertext, key_id, STAMP),
    ).lastrowid


def _insert_into(conn: sqlite3.Connection, table: str, user_id: int, key: str, **columns: Any) -> int:
    if table == SYSTEM_TABLE:
        return _insert_system(conn, key, **columns)
    return _insert_user_setting(conn, user_id, key, **columns)


@contextmanager
def _refused(conn: sqlite3.Connection, *fragments: str) -> Iterator[None]:
    """The statement in the block must fail with an integrity error naming every fragment; the transaction is rolled back."""
    with pytest.raises(sqlite3.IntegrityError) as refused:
        yield
    conn.rollback()
    assert all(fragment in str(refused.value) for fragment in fragments), f"refused for another reason: {refused.value}"


# =============================================================================
# HELPERS — accounts whose addresses collide, the refusal, the remedy
# =============================================================================


def _tag() -> str:
    """Twelve random hex characters: time alone is not unique across workers."""
    return uuid.uuid4().hex[:12]


@dataclass(frozen=True)
class Account:
    """A ``users`` row: an id of its own, that nothing else prints, and a username that shares nothing with its address."""

    id: int
    username: str
    email: str


@dataclass(frozen=True)
class Collisions:
    """Two groups whose addresses differ only in A–Z case — a pair, and a trio whose domains vary in case too — and an account alone."""

    pair: tuple[Account, Account]
    trio: tuple[Account, Account, Account]
    alone: Account

    @property
    def colliding(self) -> tuple[Account, ...]:
        return (*self.pair, *self.trio)

    @property
    def everyone(self) -> tuple[Account, ...]:
        return (*self.pair, *self.trio, self.alone)


def _collisions() -> Collisions:
    pair_box, trio_box, alone_box = f"dupe.{_tag()}", f"twin.{_tag()}", f"solo.{_tag()}"
    pair = (Account(4101, f"ina_{_tag()}", f"{pair_box}@example.com"), Account(4102, f"ivo_{_tag()}", f"{pair_box.upper()}@EXAMPLE.COM"))
    trio = (
        Account(5201, f"kai_{_tag()}", f"{trio_box}@example.com"),
        Account(5202, f"lea_{_tag()}", f"{trio_box.capitalize()}@Example.com"),
        Account(5203, f"max_{_tag()}", f"{trio_box.upper()}@example.COM"),
    )
    return Collisions(pair=pair, trio=trio, alone=Account(6301, f"zed_{_tag()}", f"{alone_box}@example.com"))


def _non_ascii_pair() -> tuple[Account, Account]:
    """``Émile.<hex>@example.com`` and ``émile.<hex>@example.com``: two addresses, É not being A–Z."""
    tag = _tag()
    return (Account(8101, f"emi_{_tag()}", f"Émile.{tag}@example.com"), Account(8102, f"eme_{_tag()}", f"émile.{tag}@example.com"))


def _values(account: Account) -> tuple[Any, ...]:
    """The parameters of ``INSERT_ACCOUNT`` for ``account``."""
    return (account.id, account.username, account.email, MARKER_HASH, STAMP, STAMP)


def _insert_accounts(db: Path, accounts: Iterable[Account]) -> None:
    """The accounts as rows, in plain SQL with foreign keys on."""
    with _foreign_keys_on(db) as conn:
        conn.executemany(INSERT_ACCOUNT, [_values(account) for account in accounts])
        conn.commit()


def _scene(at_004: Path, target: Path, accounts: Iterable[Account]) -> Path:
    """A copy of the new database at 004 holding ``accounts``; the first has its settings and signed ``enable_registration``, the row the upgrade converts before its check."""
    db = _copy(at_004, target)
    written = list(accounts)
    _insert_accounts(db, written)
    with _foreign_keys_on(db) as conn:
        conn.execute("INSERT INTO user_settings (user_id, base_currency, language, theme, avatar_url, created_at, updated_at) VALUES (?, 'EUR', 'it', 'dark', NULL, ?, ?)", (written[0].id, STAMP, STAMP))
        _write_setting(conn, OLD_KEY, ("true", "bool", "Allow new users to register", STAMP, written[0].id))
        conn.commit()
    return db


def _emails(db: Path) -> dict[int, str]:
    """``{user id: email}`` of every account."""
    with _connect(db) as conn:
        return dict(conn.execute("SELECT id, email FROM users").fetchall())


def _refused_by_sql(db: Path, statement: str, parameters: tuple[Any, ...]) -> Optional[str]:
    """``statement`` in plain SQL, in a transaction of its own: None when SQLite took it (committed), else the message of its ``IntegrityError`` (rolled back)."""
    with _foreign_keys_on(db) as conn:
        try:
            with conn:
                conn.execute(statement, parameters)
        except sqlite3.IntegrityError as refused:
            return str(refused)
    return None


@dataclass(frozen=True)
class Refusal:
    """What a stopped upgrade gives to read: its errors, the message of its ``RuntimeError``, what it printed, what it logged."""

    error: str
    message: Optional[str]
    output: str
    log: str


def _chain(error: BaseException) -> list[BaseException]:
    """``error`` and every error it was raised from or during."""
    chain: list[BaseException] = []
    current: Optional[BaseException] = error
    while current is not None and all(current is not seen for seen in chain):
        chain.append(current)
        current = current.__cause__ or current.__context__
    return chain


def _written_by_a_server(record: logging.LogRecord) -> bool:
    """Every record a running server writes: all but those below WARNING of the SQL loggers and their children."""
    of_sql = any(record.name == name or record.name.startswith(f"{name}.") for name in SQL_LOGGERS)
    return record.levelno >= logging.WARNING or not of_sql


def _refused_upgrade(db: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> Refusal:
    """``alembic upgrade 005_release_1_3_0_schema`` on ``db``, in this process and on ``db`` alone, expected to stop: its errors, and everything printed or logged meanwhile — stdlib records at DEBUG, structlog events."""
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    capsys.readouterr()
    stopped: Optional[BaseException] = None
    with capture_logs() as events, _alembic_connections(db):
        try:
            command.upgrade(_alembic_config(db), REV_005)
        except Exception as error:  # whatever reaches here: the RuntimeError of the check is looked for in its chain
            stopped = error
    printed = capsys.readouterr()
    if stopped is None:
        pytest.fail(f"the upgrade went through over accounts whose addresses differ only in A–Z case, and left the database at {_revision(db)}: it must stop before {EMAIL_INDEX}", pytrace=False)
    if isinstance(stopped, RuntimeError) and str(stopped).startswith("safety:"):
        raise stopped
    chain = _chain(stopped)
    records = [f"{record.name}: {record.getMessage()} {vars(record)!r}" for record in caplog.records if _written_by_a_server(record)]
    return Refusal(
        error="\n".join(f"{type(link).__name__}: {link}" for link in chain),
        message=next((str(link) for link in chain if isinstance(link, RuntimeError)), None),
        output=printed.out + printed.err,
        log="\n".join([*records, repr(events)]),
    )


def _showing(text: str, addresses: Iterable[str]) -> list[str]:
    """The ``addresses`` that ``text`` shows, whole or by their local part, in any case."""
    lowered = text.lower()
    return sorted({address for address in addresses if address.lower() in lowered or address.lower().partition("@")[0] in lowered})


def _named(account: Account) -> str:
    """How the refusal names an account: ``#id 'username'``."""
    return f"#{account.id} {account.username!r}"


def _groups(*groups: Iterable[Account]) -> str:
    """The groups of colliding accounts as the refusal writes them: by id within a group, the groups apart with ``; ``."""
    return "; ".join(", ".join(_named(account) for account in sorted(group, key=lambda account: account.id)) for group in groups)


def _assert_refusal(refusal: Refusal, *, groups: str, named: Iterable[Account], unnamed: Iterable[Account], addresses: Iterable[str]) -> None:
    """The stop of the check: a ``RuntimeError`` in the old wording that names ``groups`` and each account of ``named`` as ``#id 'username'``, no username of ``unnamed``, and no address anywhere."""
    message = refusal.message
    assert message is not None, f"the upgrade must stop with a RuntimeError: {refusal.error}"
    assert message.startswith(f"{REFUSAL_OPENING}{groups}. "), f"the message must open as the old one did and name the groups as {groups!r}: {message}"
    assert REMEDY in message and message.endswith(REFUSAL_CLOSING), f"the message must name the remedy, {REMEDY}, and end with {REFUSAL_CLOSING!r}: {message}"
    missing = [_named(account) for account in named if _named(account) not in message]
    assert missing == [], f"the message must name every colliding account by id and username; it misses {missing}: {message}"
    outside = [account.username for account in unnamed if account.username in refusal.error]
    assert outside == [], f"the error must name no account outside a group, yet it names {outside}: {refusal.error}"
    needles = list(addresses)
    for where, text in (("the error", refusal.error), ("the standard output and error", refusal.output), ("the log", refusal.log)):
        shown = _showing(text, needles)
        assert shown == [], f"{where} must show no address, whole or by its local part, in any case (workstream E's rule): it shows {shown}"


async def _set_email(user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], db: Path, username: str, address: str) -> tuple[Any, str]:
    """``cmd_set_email(username, address)`` in this process, its ``get_async_engine`` an engine of ``db``, disposed after: what it answered, and what it printed."""
    set_email = getattr(user_cli, "cmd_set_email", None)
    if set_email is None:
        pytest.fail(f"scripts/user_cli.py has no cmd_set_email: the refusal names {REMEDY}", pytrace=False)
    private = create_async_engine(f"sqlite+aiosqlite:///{db}", poolclass=NullPool)
    monkeypatch.setattr(user_cli, "get_async_engine", lambda: private)
    capsys.readouterr()
    try:
        answer = await set_email(username, address)
    finally:
        await private.dispose()
    return answer, capsys.readouterr().out


async def _remedy(user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], db: Path, account: Account, address: str) -> None:
    """The remedy the refusal names, ``./dev.py user set-email``, for ``account``: it answers with a line starting with ✅, and the account holds ``address``."""
    try:
        answer, printed = await _set_email(user_cli, monkeypatch, capsys, db, account.username, address)
    except Exception as error:  # what keeps the command from running on the refused database is the finding itself
        pytest.fail(f"{REMEDY} cannot run on the database the upgrade refused, at {_revision(db)}: {type(error).__name__}: {error}", pytrace=False)
    assert answer and any(line.startswith("✅") for line in printed.splitlines()), f"{REMEDY} {account.username} must succeed on the refused database: {printed!r}"
    assert _emails(db)[account.id] == address, f"{REMEDY} must give {account.username} the new address"


def _a26_copy(source: Path, target: Path, statement: Optional[str] = None) -> Path:
    """A copy of ``source`` at ``target``, with ``statement`` run on it and committed when given."""
    db = _copy(source, target)
    if statement is not None:
        with _connect(db) as conn:
            with conn:
                conn.execute(statement)
    return db


def _a26_differences(first: Path, second: Path) -> dict[str, dict[str, Any]]:
    """The keys of ``_shape(…, "users")`` that differ between two copies, with both values."""
    shape_first, shape_second = _shape(first, "users"), _shape(second, "users")
    assert shape_first is not None and shape_second is not None, "barrier: both copies have a users table"
    return {key: {"first": shape_first[key], "second": shape_second[key]} for key in shape_first if shape_first[key] != shape_second.get(key)}


# =============================================================================
# FIXTURES
# =============================================================================


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> NoReturn:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not one of this module's private files")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_async_engine`` raises — in the session module, and in the email modules that import it by name and open sessions of their own —: the remedy reaches its private file through ``user_cli``'s own name only."""
    for module in (db_session, email_flows, email_verification):
        monkeypatch.setattr(module, "get_async_engine", _lane_database_tripwire, raising=False)


@pytest.fixture
def quiet_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """None of the email and accounts variables of the shell that started the run: whatever the remedy might send finds no transport."""
    for name in list(os.environ):
        if name.startswith(INHERITED_PREFIXES) or name in INHERITED_VARIABLES:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def user_cli() -> ModuleType:
    """``scripts/user_cli.py``, in this process."""
    return importlib.import_module(USER_CLI_MODULE)


@pytest.fixture(scope="module")
def frozen() -> dict[str, Any]:
    """The frozen snapshot of the retired chain, as written: ``about``, ``objects``, ``rows``."""
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def at_004(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database at 004: the 1.2 schema, no setting, no account. Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("at-004") / "app.db"
    _migrate(db, "upgrade", REV_004)
    assert _revision(db) == REV_004 and _settings(db) == {} and _accounts(db) == 0, "setup: a new database at 004 holds no setting and no account"
    return db


@pytest.fixture(scope="module")
def fresh_005(tmp_path_factory: pytest.TempPathFactory) -> Path | str:
    """A new database taken to ``005_release_1_3_0_schema`` by name, not to head: the next migrations will move the head, and what they add is theirs to pin. Read-only for the tests: ``_copy`` it to write. While Alembic knows no such revision, the reason instead: each test fails on it."""
    missing = _missing_005()
    if missing is not None:
        return missing
    db = tmp_path_factory.mktemp("fresh-005") / "app.db"
    _migrate(db, "upgrade", REV_005)
    assert _revision(db) == REV_005, f"setup: the new database is at {_revision(db)}, not at {REV_005}"
    return db


@pytest.fixture(scope="module")
def fresh_head(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to head by the real migrations: what the models describe. Read-only."""
    db = tmp_path_factory.mktemp("fresh-head") / "app.db"
    _migrate(db, "upgrade", "head")
    return db


@pytest.fixture(scope="module")
def created_by_models(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database built by ``SQLModel.metadata.create_all``, as the service suites build theirs. Read-only."""
    return _create_all(tmp_path_factory.mktemp("create-all") / "app.db")


@pytest.fixture(scope="module")
def install_1_2(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A populated 1.2 install at 004 (see the module docstring). Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("install-1.2") / "sqlite" / "app.db"
    _install_v110(db)
    _migrate(db, "upgrade", REV_004)
    report = post_migration.run_post_migration_fixes(db, None)
    assert report.outcomes.get(AUTOINCREMENT_FIX) == "applied", f"setup: the post-migration fixes a 1.2 server runs at startup did not convert the 1.1 rows: {report}"
    with _foreign_keys_on(db) as conn:
        conn.executescript(ROWS_1_2)
    assert _revision(db) == REV_004, "setup: a 1.2 install is at 004"
    assert _violations(db) == [], "setup: the 1.2 rows must be consistent"
    assert _registration(_settings(db)) == {OLD_KEY: V110_ROW}, f"setup: the 1.1 rows hold enable_registration = 'false', by user 1: {_settings(db)}"
    assert CHILDREN_OF_USERS <= _tables_pointing_at_users(db), f"setup: every table that points at users must have rows pointing at one; found {sorted(_tables_pointing_at_users(db))}"
    return db


@dataclass(frozen=True)
class Upgrade:
    """A copy of the 1.2 install, before and right after ``upgrade 005_release_1_3_0_schema``."""

    db: Path
    rows_before: Rows
    rows_after: Rows
    violations: list[tuple[Any, ...]]
    integrity: list[tuple[Any, ...]]


@pytest.fixture(scope="module")
def upgraded_1_2(install_1_2: Path, tmp_path_factory: pytest.TempPathFactory) -> Upgrade | str:
    """The 1.2 install upgraded to the revision; or, while Alembic knows no such revision, the reason: each test fails on it."""
    missing = _missing_005()
    if missing is not None:
        return missing
    db = _copy(install_1_2, tmp_path_factory.mktemp("upgraded-1.2") / "app.db")
    rows_before = _rows(db)
    _migrate(db, "upgrade", REV_005)
    return Upgrade(db=db, rows_before=rows_before, rows_after=_rows(db), violations=_violations(db), integrity=_integrity(db))


@dataclass(frozen=True)
class RoundTrip:
    """A copy of the 1.2 install taken to the revision, given ``ROWS_1_3``, downgraded to 004, then upgraded again."""

    schema_at_004: list[Any]
    schema_at_005: list[Any]
    rows_with_1_3: Rows
    revision_down: str
    schema_down: list[Any]
    rows_down: Rows
    settings_down: dict[str, Setting]
    violations_down: list[tuple[Any, ...]]
    integrity_down: list[tuple[Any, ...]]
    revision_again: str
    schema_again: list[Any]
    rows_again: Rows
    settings_again: dict[str, Setting]
    new_columns_again: dict[int, tuple[Any, ...]]
    violations_again: list[tuple[Any, ...]]


@pytest.fixture(scope="module")
def round_trip(install_1_2: Path, tmp_path_factory: pytest.TempPathFactory) -> RoundTrip | str:
    """The 1.2 install up to the revision, given ``ROWS_1_3``, down to 004 and up again; or, while Alembic knows no such revision, the reason: each test fails on it."""
    missing = _missing_005()
    if missing is not None:
        return missing
    db = _copy(install_1_2, tmp_path_factory.mktemp("round-trip") / "app.db")
    schema_at_004 = _snapshot(db)["objects"]
    _migrate(db, "upgrade", REV_005)
    schema_at_005 = _snapshot(db)["objects"]
    with _foreign_keys_on(db) as conn:
        conn.executescript(ROWS_1_3)
    pointing = _tables_pointing_at_users(db)
    assert CHILDREN_OF_USERS | NEW_TABLES <= pointing, f"barrier: every table that points at users must have rows pointing at one before the downgrade, or «nothing cascades» proves nothing for it; found {sorted(pointing)}"
    rows_with_1_3 = _rows(db)

    _migrate(db, "downgrade", REV_004)
    down = {"revision_down": _revision(db), "schema_down": _snapshot(db)["objects"], "rows_down": _rows(db), "settings_down": _settings(db), "violations_down": _violations(db), "integrity_down": _integrity(db)}

    _migrate(db, "upgrade", REV_005)
    again = {"revision_again": _revision(db), "schema_again": _snapshot(db)["objects"], "rows_again": _rows(db), "settings_again": _settings(db), "new_columns_again": _new_user_columns(db), "violations_again": _violations(db)}
    return RoundTrip(schema_at_004=schema_at_004, schema_at_005=schema_at_005, rows_with_1_3=rows_with_1_3, **down, **again)


# =============================================================================
# 1. THE REVISION
# =============================================================================


def test_the_1_3_schema_is_one_revision_on_top_of_004() -> None:
    """``005_release_1_3_0_schema`` exists, in ``005_release_1_3_0_schema.py``, fits ``alembic_version.version_num`` (``VARCHAR(32)``), revises ``004_release_1_2_0_schema`` and is its only child; the chain keeps one head, which is not named: the next migrations go on top."""
    print_section(f"The revision {REV_005}")
    scripts = _scripts()
    revisions = {script.revision: script for script in scripts.walk_revisions()}

    assert REV_005 in revisions, f"red until H-57: revision {REV_005} not found; the chain has {sorted(revisions)}"
    script = revisions[REV_005]
    assert len(script.revision) <= 32, f"{script.revision!r} is {len(script.revision)} characters: alembic_version.version_num is VARCHAR(32)"
    assert script.down_revision == REV_004, f"{REV_005} must revise {REV_004}, revises {script.down_revision!r}"
    assert Path(script.path).name == f"{REV_005}.py", f"the revision id is the file name without .py, found in {Path(script.path).name}"
    children = sorted(revision for revision, other in revisions.items() if other.down_revision == REV_004)
    assert children == [REV_005], f"{REV_004} must have one child, {REV_005}: {children}"
    heads = scripts.get_heads()
    assert len(heads) == 1, f"the chain must not fork: {len(heads)} heads {heads}"
    print_success(f"{REV_005} revises {REV_004}; one head ({heads[0]})")


def test_the_retired_1_3_revisions_are_gone_from_the_chain() -> None:
    """None of ``005_accounts_invites`` … ``010_provider_reported_currency`` is a revision any more, nor a file of ``versions``: the one revision replaces them. A database still stamped with one of them is the manual procedure's (plan H, 19/10/2026), not the code's."""
    revisions = {script.revision for script in _scripts().walk_revisions()}
    files = sorted(path.name for path in (ALEMBIC_SCRIPT_LOCATION / "versions").glob("*.py") if path.stem in RETIRED_REVISIONS)

    left = sorted(set(RETIRED_REVISIONS) & revisions)
    assert (left, files) == ([], []), f"red until H-57: the retired revisions {left} are still in the chain, their files {files} still in backend/alembic/versions"


# =============================================================================
# 2. EQUIVALENCE WITH THE RETIRED CHAIN
# =============================================================================


def test_the_frozen_snapshot_is_the_v4_schema_it_describes(frozen: dict[str, Any]) -> None:
    """GUARD, green before and after: the frozen snapshot holds what its ``about`` says — the 1.3 objects (``account_tokens`` and its two indexes, the two plugin tables, ``ux_users_email_lower``, the three ``users`` columns as declared), none of the 13 indexes, no ``reported_currency``, no row —, its objects by type and name, as ``_snapshot`` reads them.

    It pins what the fixture means, so that the equivalence cannot pass against a snapshot that says something else.
    """
    objects = frozen["objects"]
    names = {name for _kind, name, _table, _sql in objects}
    sql_of = {name: sql for _kind, name, _table, sql in objects}

    assert set(frozen) == {"about", "objects", "rows"} and frozen["rows"] == {}, f"the snapshot holds its about, the objects and no row: keys {sorted(frozen)}, rows {frozen.get('rows')}"
    assert objects == sorted(objects, key=lambda entry: (entry[0], entry[1])), "the objects must be listed by type and name, as sqlite_master is read"
    missing = sorted((NEW_TABLES | {"ix_account_tokens_purpose_expires_at", "ix_account_tokens_user_id", EMAIL_INDEX}) - names)
    assert missing == [], f"the snapshot lacks 1.3 objects: {missing}"
    assert all(f"{name} {declaration}" in sql_of["users"] for name, declaration in USER_COLUMNS.items()), f"users must hold the three columns as declared: {sql_of['users']}"
    assert sorted(names & set(REDUNDANT_INDEXES)) == [], f"the snapshot must hold none of the 13 redundant indexes: {sorted(names & set(REDUNDANT_INDEXES))}"
    assert "reported_currency" not in sql_of["asset_provider_assignments"], "variant V4 keeps no reported_currency"


def test_a_new_database_at_the_revision_is_the_schema_the_retired_chain_left(fresh_005: Path | str, frozen: dict[str, Any]) -> None:
    """``_snapshot`` of a new database taken to ``005_release_1_3_0_schema`` — by name, not to head — is the frozen snapshot exactly: the same objects of ``sqlite_master``, each with the same table and the same SQL text (whitespace collapsed), in the same order, and the same rows, none but ``alembic_version``'s."""
    print_section("A new database at the revision = the retired chain, frozen")
    db = _ran(fresh_005)
    snapshot = _snapshot(db)

    differences = _schema_differences(frozen["objects"], snapshot["objects"])
    assert not differences, f"the revision must build the schema the retired chain left, SQL text included: {differences}"
    assert snapshot["rows"] == frozen["rows"], f"a new database holds no row but alembic_version's: {snapshot['rows']}"
    assert snapshot == {"objects": frozen["objects"], "rows": frozen["rows"]}, "the same objects, in the same order"
    print_success(f"{len(snapshot['objects'])} objects of sqlite_master, as the retired chain left them")


# =============================================================================
# 3. THE 1.3 OBJECTS AT WORK
# =============================================================================


def test_a_user_written_without_the_new_columns_gets_their_defaults(fresh_005: Path | str, tmp_path: Path) -> None:
    """A user written without the three columns reads back 0 (an integer) / NULL / NULL; ``session_version`` refuses NULL. What every user an older code path creates gets: the defaults are behaviour, not DDL text."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")

    with _foreign_keys_on(db) as conn:
        user_id = _insert_user(conn, "defaults")
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError, match=r"users\.session_version"):
            conn.execute("UPDATE users SET session_version = NULL WHERE id = ?", (user_id,))

    assert _new_user_columns(db) == {user_id: EXISTING_USER_VALUES}


def test_account_tokens_points_at_users_with_its_indexes_and_named_constraints(fresh_005: Path | str) -> None:
    """``user_id`` → ``users.id`` ON DELETE CASCADE, ``created_by_user_id`` and ``consumed_by_user_id`` ON DELETE SET NULL; two plain indexes, on ``(purpose, expires_at)`` and on ``user_id``; ``token_hash`` unique as ``uq_account_tokens_token_hash``; ``ck_account_tokens_purpose``."""
    db = _ran(fresh_005)
    shape = _full_shape(db, "account_tokens")
    assert shape is not None, "account_tokens is missing"
    indexes = {name: (unique, columns) for name, (unique, origin, columns) in _index_list(db, "account_tokens").items() if origin == "c"}

    assert _foreign_keys(db, "account_tokens") == TOKEN_FOREIGN_KEYS
    assert indexes == {name: (False, columns) for name, columns in TOKEN_INDEXES.items()}, f"indexes of account_tokens: {indexes}"
    assert shape["unique constraints"] == [(TOKEN_UNIQUE, ("token_hash",))], f"unique constraints of account_tokens: {shape['unique constraints']}"
    assert [name for name, _sql in shape["check constraints (name: sql)"]] == [TOKEN_CHECK], f"check constraints of account_tokens: {shape['check constraints (name: sql)']}"


@pytest.mark.parametrize("purpose", ["magic_link", "INVITE", ""])
def test_account_tokens_refuses_an_unknown_purpose(fresh_005: Path | str, tmp_path: Path, purpose: str) -> None:
    """With foreign keys on, ``ck_account_tokens_purpose`` refuses any other value: the enum's names, an empty string."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")

    with _foreign_keys_on(db) as conn:
        with pytest.raises(sqlite3.IntegrityError, match=TOKEN_CHECK):
            _insert_token(conn, purpose, _token_hash(1))


def test_account_tokens_takes_the_four_purposes(fresh_005: Path | str, tmp_path: Path) -> None:
    """``invite``, ``password_reset``, ``email_verification`` and ``admin_setup`` are stored as written."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")

    with _foreign_keys_on(db) as conn:
        owner = _insert_user(conn, "owner")
        written = {_insert_token(conn, purpose, _token_hash(n), user_id=None if purpose == "invite" else owner): purpose for n, purpose in enumerate(PURPOSES, start=1)}
        conn.commit()
        stored = dict(conn.execute("SELECT id, purpose FROM account_tokens").fetchall())

    assert stored == written


def test_account_tokens_refuses_a_second_token_with_the_same_hash(fresh_005: Path | str, tmp_path: Path) -> None:
    """Two tokens never share a hash, whatever their purposes: the hash is how a token is found."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")

    with _foreign_keys_on(db) as conn:
        owner = _insert_user(conn, "owner")
        _insert_token(conn, "invite", _token_hash(7))
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError, match=r"account_tokens\.token_hash"):
            _insert_token(conn, "password_reset", _token_hash(7), user_id=owner)


def test_grants_admin_defaults_to_false_and_is_never_null(fresh_005: Path | str, tmp_path: Path) -> None:
    """A token written without ``grants_admin`` does not grant admin; NULL is refused."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")

    with _foreign_keys_on(db) as conn:
        token_id = _insert_token(conn, "invite", _token_hash(1))
        conn.commit()
        stored = conn.execute("SELECT grants_admin FROM account_tokens WHERE id = ?", (token_id,)).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError, match=r"account_tokens\.grants_admin"):
            _insert_token(conn, "invite", _token_hash(2), grants_admin=None)

    assert stored == 0


def test_deleting_a_user_deletes_its_tokens_and_unlinks_the_others(fresh_005: Path | str, tmp_path: Path) -> None:
    """With foreign keys on, deleting a user deletes the tokens whose ``user_id`` is that user and sets ``created_by_user_id`` / ``consumed_by_user_id`` to NULL where it created or consumed someone else's; every other token and link stays. The database is this test's alone: the comparison is exact."""
    print_section("account_tokens: deleting a user")
    db = _copy(_ran(fresh_005), tmp_path / "app.db")

    with _foreign_keys_on(db) as conn:
        gone, creator, consumer, bystander = (_insert_user(conn, name) for name in ("gone", "creator", "consumer", "bystander"))
        owned = _insert_token(conn, "password_reset", _token_hash(1), user_id=gone, created_by_user_id=creator, consumed_by_user_id=consumer, consumed_at=STAMP)
        created = _insert_token(conn, "invite", _token_hash(2), created_by_user_id=gone)
        consumed = _insert_token(conn, "invite", _token_hash(3), created_by_user_id=creator, consumed_by_user_id=gone, consumed_at=STAMP)
        unrelated = _insert_token(conn, "email_verification", _token_hash(4), user_id=bystander, created_by_user_id=creator, consumed_by_user_id=consumer, consumed_at=STAMP)
        conn.commit()
        assert set(_token_links(conn)) == {owned, created, consumed, unrelated}, "setup: the four tokens are written"

        conn.execute("DELETE FROM users WHERE id = ?", (gone,))
        conn.commit()
        links = _token_links(conn)

    assert links == {created: (None, None, None), consumed: (None, creator, None), unrelated: (bystander, creator, consumer)}, f"(user_id, created_by_user_id, consumed_by_user_id) by token after deleting user {gone}: {links}"
    assert _violations(db) == []
    print_success("its own tokens deleted, its links to the others set to NULL, nothing else touched")


@pytest.mark.parametrize("table", PLUGIN_TABLES)
@pytest.mark.parametrize(("columns", "constraint"), BROKEN_VALUES)
def test_a_plugin_setting_holds_exactly_one_value_and_a_key_id_only_with_a_secret(fresh_005: Path | str, tmp_path: Path, table: str, columns: dict[str, Any], constraint: str) -> None:
    """The two CHECKs of each plugin table, each case refused by the one it names; the two valid shapes, a plain value and a secret with its key id, accepted."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")

    with _foreign_keys_on(db) as conn:
        user = _insert_user(conn, "owner")
        conn.commit()
        with _refused(conn, "CHECK constraint failed", f"ck_{table}_{constraint}"):
            _insert_into(conn, table, user, "field", **columns)
        _insert_into(conn, table, user, "plain")
        _insert_into(conn, table, user, "secret", value_json=None, ciphertext=BLOB, key_id=KEY_ID)
        conn.commit()
        stored = conn.execute(f"SELECT field_key FROM {table} ORDER BY id").fetchall()

    assert stored == [("plain",), ("secret",)]


def test_a_plugin_field_is_stored_once_per_instance_and_once_per_user(fresh_005: Path | str, tmp_path: Path) -> None:
    """The unique constraints of the plugin tables: a field twice is refused; the same field for two users, in two families or for two plugins is accepted."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")

    with _foreign_keys_on(db) as conn:
        alice, bob = _insert_user(conn, "alice"), _insert_user(conn, "bob")
        _insert_system(conn, "region")
        _insert_user_setting(conn, alice, "limit")
        conn.commit()

        with _refused(conn, "UNIQUE constraint failed", SYSTEM_TABLE):
            _insert_system(conn, "region", value_json='"eu"')
        with _refused(conn, "UNIQUE constraint failed", USER_TABLE):
            _insert_user_setting(conn, alice, "limit", value_json="9")
        _insert_system(conn, "region", family="fx")
        _insert_system(conn, "region", code="other")
        _insert_user_setting(conn, bob, "limit")
        _insert_user_setting(conn, alice, "limit", family="fx")
        conn.commit()
        counts = [conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in PLUGIN_TABLES]

    assert counts == [3, 3], f"the accepted rows of {PLUGIN_TABLES}: {counts}"


def test_a_user_plugin_setting_needs_a_user(fresh_005: Path | str, tmp_path: Path) -> None:
    """A user row for no user is refused by its foreign key; one without a user, by NOT NULL."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")

    with _foreign_keys_on(db) as conn:
        with _refused(conn, "FOREIGN KEY constraint failed"):
            _insert_user_setting(conn, 987_654, "limit")
        with _refused(conn, "NOT NULL constraint failed", "user_id"):
            conn.execute(f"INSERT INTO {USER_TABLE} (family, plugin_code, field_key, value_json, updated_at) VALUES ('asset', 'lab', 'limit', '7', ?)", (STAMP,))


def test_deleting_a_user_deletes_its_plugin_settings_and_unlinks_the_system_ones_it_wrote(fresh_005: Path | str, tmp_path: Path) -> None:
    """With foreign keys on: the user's rows go with the user, a system row it wrote stays without its author; every other row and link stays."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")

    with _foreign_keys_on(db) as conn:
        gone, kept = _insert_user(conn, "gone"), _insert_user(conn, "kept")
        written_by_gone = _insert_system(conn, "region", author=gone)
        written_by_kept = _insert_system(conn, "verbose", value_json="true", author=kept)
        _insert_user_setting(conn, gone, "limit")
        _insert_user_setting(conn, gone, "token", value_json=None, ciphertext=BLOB, key_id=KEY_ID)
        kept_row = _insert_user_setting(conn, kept, "limit")
        conn.commit()

        conn.execute("DELETE FROM users WHERE id = ?", (gone,))
        conn.commit()
        system = conn.execute(f"SELECT id, updated_by_user_id FROM {SYSTEM_TABLE} ORDER BY id").fetchall()
        user = conn.execute(f"SELECT id, user_id FROM {USER_TABLE} ORDER BY id").fetchall()

    assert system == [(written_by_gone, None), (written_by_kept, kept)], "the system rows stay; the deleted author is unlinked"
    assert user == [(kept_row, kept)], "the deleted user's rows go, the others stay"
    assert _violations(db) == []


def test_the_email_index_refuses_an_address_another_account_has_in_another_case(fresh_005: Path | str, tmp_path: Path) -> None:
    """``ux_users_email_lower``, with plain SQL and foreign keys on: beside ``Box.<hex>@Example.com``, an INSERT of ``box.<hex>@example.com`` and an UPDATE of another account to ``BOX.<HEX>@EXAMPLE.COM`` are refused naming the index, and change nothing; ``Émile.<hex>@`` and ``émile.<hex>@`` go in as two addresses, É not being A–Z (the documented limit)."""
    print_section(f"{EMAIL_INDEX}: Alice@x beside alice@x")
    db = _copy(_ran(fresh_005), tmp_path / "app.db")
    tag = _tag()
    holder, other = Account(9101, f"hal_{_tag()}", f"Box.{tag}@Example.com"), Account(9102, f"oli_{_tag()}", f"other.{_tag()}@example.com")
    _insert_accounts(db, (holder, other))

    inserted = _refused_by_sql(db, INSERT_USER, (f"new_{_tag()}", f"box.{tag}@example.com", STAMP, STAMP))
    updated = _refused_by_sql(db, "UPDATE users SET email = ? WHERE id = ?", (f"BOX.{tag.upper()}@EXAMPLE.COM", other.id))
    pair = _non_ascii_pair()
    taken = [_refused_by_sql(db, INSERT_ACCOUNT, _values(account)) for account in pair]

    assert inserted is not None and EMAIL_INDEX in inserted, f"an INSERT of the same address but for A–Z must be refused by {EMAIL_INDEX}: {inserted}"
    assert updated is not None and EMAIL_INDEX in updated, f"an UPDATE to the same address but for A–Z must be refused by {EMAIL_INDEX}: {updated}"
    emails = _emails(db)
    assert (emails[holder.id], emails[other.id]) == (holder.email, other.email), f"the refused statements must change nothing: {emails}"
    assert sorted(email for email in emails.values() if email.lower().startswith(f"box.{tag}")) == [holder.email], "the address must keep its one account"
    assert taken == [None, None], f"Émile… and émile… are two addresses (É is not A–Z): both must go in; refused: {taken}"
    assert [emails[account.id] for account in pair] == [account.email for account in pair], "the non-ASCII pair is stored as written"
    print_success(f"{EMAIL_INDEX} refuses A–Z case, takes É beside é")


def test_the_upgrade_adds_no_reported_currency(fresh_005: Path | str) -> None:
    """``010_provider_reported_currency`` is not kept (the developer's decision of 19/10/2026): at the revision ``asset_provider_assignments`` has no ``reported_currency``."""
    columns = _table_info(_ran(fresh_005), "asset_provider_assignments")

    assert columns, "barrier: asset_provider_assignments is there"
    assert "reported_currency" not in columns, f"variant V4 adds no reported_currency: {sorted(columns)}"


# =============================================================================
# 4. THE 13 REDUNDANT INDEXES
# =============================================================================


@pytest.mark.parametrize("database", ["a-new-database", "a-populated-1.2-install"])
def test_the_upgrade_drops_the_13_redundant_indexes(at_004: Path, install_1_2: Path, tmp_path: Path, database: str) -> None:
    """At 004 the database holds the 13 indexes of ``001_initial`` (barrier: their absence after would prove nothing otherwise); after ``upgrade`` to the revision it holds none of them — on a new database, and on a populated 1.2 install whose tables the post-migration fixes rebuilt."""
    print_section(f"The 13 redundant indexes: {database}")
    _require_005()
    db = _copy(at_004 if database == "a-new-database" else install_1_2, tmp_path / "app.db")
    before = _redundant_present(db)
    assert sorted(before) == sorted(REDUNDANT_INDEXES), f"barrier: at 004, {database} must hold the 13 indexes of 001_initial; it holds {sorted(before)}"

    _migrate(db, "upgrade", REV_005)

    assert _revision(db) == REV_005, f"the upgrade must reach {REV_005}: {_revision(db)}"
    left = _redundant_present(db)
    assert left == {}, f"the upgrade must drop the 13 redundant indexes; left: {sorted(left)}"
    print_success("none of the 13 is left")


@pytest.mark.parametrize("name", sorted(DUPLICATES))
def test_every_unique_constraint_one_of_the_13_copied_still_refuses_a_duplicate(fresh_005: Path | str, tmp_path: Path, name: str) -> None:
    """After the upgrade, with foreign keys on: a username, an address, a broker name, an asset display name, a price for an asset and a date, an assignment for an asset — each written twice, the second is refused by the table's own UNIQUE constraint, named by its columns. The index that copied or prefixed it is gone, and the constraint is there (``PRAGMA index_list``, origin ``u``).

    For the address, ``ux_users_email_lower`` is set aside on this private copy first: SQLite checks the newest index first, and that one would refuse an exact duplicate before the column's own UNIQUE could show it is still there.
    """
    case = DUPLICATES[name]
    db = _copy(_ran(fresh_005), tmp_path / "app.db")
    expected = "UNIQUE constraint failed: " + ", ".join(f"{case.table}.{column}" for column in case.columns)

    with _foreign_keys_on(db) as conn:
        if case.set_aside is not None:
            conn.execute(f"DROP INDEX {case.set_aside}")
        *first, (duplicate, parameters) = case.writes
        written = [conn.execute(statement, values).rowcount for statement, values in first]
        conn.commit()
        assert written == [1] * len(first), f"setup: each row before the duplicate is written: {written}"
        with _refused(conn, expected):
            conn.execute(duplicate, parameters)

    indexes = _index_list(db, case.table)
    assert case.columns in {columns for unique, origin, columns in indexes.values() if unique and origin == "u"}, f"{case.table} must hold the UNIQUE constraint on {case.columns}: {indexes}"
    assert sorted(set(indexes) & set(REDUNDANT_INDEXES)) == [], f"{case.table} still holds {sorted(set(indexes) & set(REDUNDANT_INDEXES))}"


# =============================================================================
# 5. THE MODELS AND THE MIGRATION AGREE
# =============================================================================


@pytest.mark.parametrize(("table", "reader"), MODELLED_TABLES)
def test_the_models_and_the_migration_build_the_same_1_3_table(fresh_head: Path, created_by_models: Path, table: str, reader: Callable[[Path, str], Optional[dict[str, Any]]]) -> None:
    """``create_all`` and ``alembic upgrade head`` build ``table`` alike: columns and nullability, primary key, foreign keys and their ON DELETE, indexes (one on an expression by its text), unique column sets, CHECKs; for the plugin tables also declared types, unique constraint names and CHECK texts. The service suites build their databases with ``create_all``: a drift would test them against a schema production lacks.

    At head on purpose, behind a barrier that the head includes the revision: the models describe the head, whichever
    revision it is.
    """
    print_section(f"{table}: migration = models")
    _assert_includes_005(fresh_head)
    migrated, modelled = reader(fresh_head, table), reader(created_by_models, table)

    assert migrated is not None and modelled is not None, f"barrier: {table} is built by the migration: {migrated is not None}; by the models: {modelled is not None}"
    differences = {key: {"migration": migrated[key], "models": modelled.get(key)} for key in migrated if migrated[key] != modelled.get(key)}
    assert not differences, f"{table}: the migration and the models disagree on {differences}"
    print_success(f"{table}: the same table both ways")


@pytest.mark.parametrize("table", INDEXED_TABLES)
def test_the_models_and_the_migration_agree_on_every_index_and_declare_none_of_the_13(fresh_head: Path, created_by_models: Path, table: str) -> None:
    """On ``table``, which held one of the 13 indexes, neither ``alembic upgrade head`` nor ``create_all`` has any of them, and the two agree on every index written with ``CREATE INDEX`` — name, keys, uniqueness — and on every column set held unique, by a constraint or by an index: the models no longer declare the 13, so they cannot come back through ``create_all``, and no UNIQUE was lost with them. ``unique=True, index=True`` builds a unique index and no constraint; ``unique=True`` alone builds the constraint, as the migrated database holds it.

    Red until the cure twice over: the head does not include the revision, and ``db/models.py`` still declares 12 of the
    13 (``uq_assets_display_name`` is a constraint's name there). Only the indexes are compared: the rest of these
    tables carries older drifts that are not this lot's (``asset_provider_assignments``: the ON DELETE of ``asset_id``,
    the length of ``identifier_type``, ``reported_currency`` until its removal lands).
    """
    _assert_includes_005(fresh_head)
    dropped = {name for name, (owner, _definition) in REDUNDANT_INDEXES.items() if owner == table}
    declared = {origin: sorted(dropped & set(_index_list(db, table))) for origin, db in (("alembic upgrade head", fresh_head), ("SQLModel.metadata.create_all", created_by_models))}

    assert declared == {"alembic upgrade head": [], "SQLModel.metadata.create_all": []}, f"none of the 13 redundant indexes may be declared on {table}: {declared}"
    migrated, modelled = _index_entries(fresh_head, table), _index_entries(created_by_models, table)
    assert migrated == modelled, f"{table}: the migration and the models disagree on its indexes: migration {migrated}, models {modelled}"


# The comparison above is only as good as ``_shape``. SQLAlchemy's inspector skips an index on an expression, on both
# sides alike: ``_shape`` reads indexes from ``PRAGMA index_list`` instead (lot A-26). These guards put such an index on
# one of two copies of a database at 004 and ask ``_shape`` to see it. The copies are written, never ``at_004``.


def test_shape_sees_an_index_on_an_expression_present_on_one_side_only(at_004: Path, tmp_path: Path) -> None:
    """GUARD of the harness (lot A-26), green before and after: a NON-unique index on ``lower(username)``, on one of two copies only, makes ``_shape`` of users differ under "indexes (name, columns, unique)" alone, the probe named on the copy that has it. The inspector skips it, and "unique column sets" counts only unique ones."""
    with_index = _a26_copy(at_004, tmp_path / "with" / "app.db", f"CREATE INDEX {A26_PROBE_INDEX} ON users ({A26_EXPRESSION})")
    without = _a26_copy(at_004, tmp_path / "without" / "app.db")
    assert _index_list(with_index, "users").get(A26_PROBE_INDEX) == (False, "c", (A26_EXPRESSION,)), f"barrier: the probe index must be on the copy: {_index_list(with_index, 'users')}"
    assert A26_PROBE_INDEX not in _index_list(without, "users"), "barrier: the other copy has no probe index"

    differences = _a26_differences(with_index, without)

    assert set(differences) == {A26_INDEXES_KEY}, f"_shape must see {A26_PROBE_INDEX} on {A26_EXPRESSION}, under {A26_INDEXES_KEY!r} alone: {differences}"
    entries = differences[A26_INDEXES_KEY]
    assert A26_PROBE_INDEX in repr(entries["first"]) and A26_PROBE_INDEX not in repr(entries["second"]), f"{A26_INDEXES_KEY!r} must name {A26_PROBE_INDEX} on the copy that has it, and only there: {entries}"


@pytest.mark.parametrize("create", ["CREATE INDEX", "CREATE UNIQUE INDEX"], ids=["non-unique", "unique"])
def test_shape_sees_an_index_on_an_expression_under_another_name(at_004: Path, tmp_path: Path, create: str) -> None:
    """GUARD of the harness (lot A-26), green before and after: the same index on ``lower(username)``, under a name of its own on each copy, makes ``_shape`` differ under "indexes (name, columns, unique)" alone — a model and a migration that named an index differently would build that. Unique, "unique column sets" holds the key on both sides and has no names."""
    names = {"a": f"{A26_PROBE_INDEX}_a", "b": f"{A26_PROBE_INDEX}_b"}
    copies = {side: _a26_copy(at_004, tmp_path / side / "app.db", f"{create} {name} ON users ({A26_EXPRESSION})") for side, name in names.items()}
    unique = create == "CREATE UNIQUE INDEX"
    for side, name in names.items():
        other = names["b" if side == "a" else "a"]
        indexes = _index_list(copies[side], "users")
        assert indexes.get(name) == (unique, "c", (A26_EXPRESSION,)) and other not in indexes, f"barrier: copy {side} must hold {name} on {A26_EXPRESSION}, unique={unique}, and not {other}: {indexes}"

    differences = _a26_differences(copies["a"], copies["b"])

    assert set(differences) == {A26_INDEXES_KEY}, f"_shape must see that the index on {A26_EXPRESSION} is {names['a']} on one copy and {names['b']} on the other, under {A26_INDEXES_KEY!r} alone: {differences}"
    entries = differences[A26_INDEXES_KEY]
    assert names["a"] in repr(entries["first"]) and names["b"] in repr(entries["second"]), f"{A26_INDEXES_KEY!r} must name each copy's index: {entries}"


def test_shape_of_two_untouched_copies_is_the_same(at_004: Path, tmp_path: Path) -> None:
    """GUARD of the harness, green before and after: two untouched copies have the same ``_shape`` of users, so a difference above is the index's, not the copy's."""
    first, second = _a26_copy(at_004, tmp_path / "first" / "app.db"), _a26_copy(at_004, tmp_path / "second" / "app.db")

    assert _a26_differences(first, second) == {}


# =============================================================================
# 6. REGISTRATION: enable_registration BECOMES registration_mode
# =============================================================================


@pytest.mark.parametrize(("old_value", "mode"), CONVERSIONS)
def test_the_upgrade_converts_enable_registration_as_the_application_read_it(at_004: Path, tmp_path: Path, old_value: str, mode: str) -> None:
    """``open`` exactly when ``old_value.lower()`` is true, 1, yes or on — no strip, as ``get_setting_value`` read a bool until 1.3 —, ``disabled`` for every other value, closed as it was; ``value_type`` ``str``, the new description, the old row's date and author; the old row gone; the neighbours as they were."""
    _require_005()
    db = _copy(at_004, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        author = _insert_user(conn, "author")
        _write_setting(conn, OLD_KEY, (old_value, "bool", "Allow new users to register", STAMP, author))
        neighbours = _write_neighbours(conn, author)
        conn.commit()

    _migrate(db, "upgrade", REV_005)
    settings = _settings(db)

    expected = (mode, NEW_TYPE, NEW_DESCRIPTION, STAMP, author)
    assert OLD_KEY not in settings, f"the upgrade must delete {OLD_KEY}: {settings}"
    assert settings.get(NEW_KEY) == expected, f"{OLD_KEY}={old_value!r} was read as {mode == 'open'} until 1.3: {NEW_KEY} must be {expected}; got {settings.get(NEW_KEY)}"
    assert _others(settings) == neighbours, f"the upgrade touched other settings: {_others(settings)}"


def test_the_conversion_keeps_a_row_nobody_signed_unsigned(at_004: Path, tmp_path: Path) -> None:
    """An ``enable_registration`` nobody signed (``updated_by_user_id`` NULL) gives a ``registration_mode`` nobody signed: NULL is copied, never filled in."""
    _require_005()
    db = _copy(at_004, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        _write_setting(conn, OLD_KEY, ("true", "bool", "Allow new users to register", STAMP, None))
        conn.commit()

    _migrate(db, "upgrade", REV_005)

    assert _settings(db) == {NEW_KEY: (OPEN, NEW_TYPE, NEW_DESCRIPTION, STAMP, None)}


@pytest.mark.parametrize("how", ["converted", "written-for-accounts"])
def test_the_row_the_upgrade_writes_is_the_row_a_new_install_seeds_but_for_its_value(at_004: Path, tmp_path: Path, how: str) -> None:
    """The ``value_type`` and the description of the ``registration_mode`` the upgrade writes — converted from ``enable_registration``, or written for an install with accounts and no row — are the registry's, ``GLOBAL_SETTINGS_DEFAULTS["registration_mode"]``, from which a new install seeds its row: an upgraded install and a new one hold the same row. The value is the install's: ``open`` here, whatever default the registry gives a new install (``invite``, decision 36).

    GUARD of a drift: it compares the migration's frozen text with the registry, whatever both say; ``NEW_TYPE`` and
    ``NEW_DESCRIPTION`` pin what they say.
    """
    _require_005()
    db = _copy(at_004, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        if how == "converted":
            _write_setting(conn, OLD_KEY, ("true", "bool", "Allow new users to register", STAMP, None))
        else:
            _insert_user(conn, "account")
        conn.commit()

    _migrate(db, "upgrade", REV_005)
    written = _settings(db).get(NEW_KEY)
    seeded = GLOBAL_SETTINGS_DEFAULTS[NEW_KEY]

    assert written is not None, f"the upgrade must write {NEW_KEY} ({how})"
    assert written[1:3] == (seeded["type"], seeded["description"]), f"the migration writes {written}, a new install seeds {seeded}: the same row but for its value"
    assert written[0] == OPEN, f"the value is the one the install ran with, {OPEN!r}; got {written[0]!r}"


@pytest.mark.parametrize("is_active", ACCOUNTS)
def test_an_install_with_accounts_and_no_row_gets_open_written_by_the_upgrade(at_004: Path, tmp_path: Path, is_active: int) -> None:
    """One account, active or not, and no registration row — 1.1 and 1.2 read a missing ``enable_registration`` as true —: the upgrade writes ``open``, ``str``, the frozen description, nobody's, at the UTC time of the upgrade, before the startup seeding can write the new default; no other setting changes."""
    _require_005()
    db = _copy(at_004, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        account = _insert_user(conn, "account")
        assert conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, account)).rowcount == 1, "setup: the account is as the case says"
        neighbours = _write_neighbours(conn, account)
        conn.commit()

    started = _utc_now()
    _migrate(db, "upgrade", REV_005)
    finished = _utc_now()
    settings = _settings(db)

    _assert_written_by_the_upgrade(settings.get(NEW_KEY), started, finished)
    assert settings.keys() == neighbours.keys() | {NEW_KEY}, f"the upgrade must write {NEW_KEY} and no other setting: {sorted(settings)}"
    assert _others(settings) == neighbours, f"the upgrade touched other settings: {_others(settings)}"


@pytest.mark.parametrize("history", NO_ACCOUNTS)
def test_without_accounts_and_without_a_row_nothing_is_written_up_or_down(at_004: Path, tmp_path: Path, history: str) -> None:
    """``users`` empty — never filled, never filled with other settings written, or emptied — and no registration row: the upgrade and the downgrade change no setting. A new install gets its default from the startup seeding, not from the migration."""
    _require_005()
    db = _copy(at_004, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        _leave_no_account(conn, history)
        conn.commit()
    before = _settings(db)
    assert _accounts(db) == 0 and _registration(before) == {}, f"setup: no account and no registration row: {before}"

    _migrate(db, "upgrade", REV_005)
    after_upgrade = _settings(db)
    _migrate(db, "downgrade", REV_004)
    after_downgrade = _settings(db)

    assert after_upgrade == before, f"without accounts the upgrade must write nothing: {before} then {after_upgrade}"
    assert after_downgrade == before, f"the downgrade must change no setting: {before} then {after_downgrade}"
    assert _revision(db) == REV_004


@pytest.mark.parametrize(("value", "beside_the_old_row"), KEPT)
def test_a_registration_mode_already_there_is_never_touched(at_004: Path, tmp_path: Path, value: str, beside_the_old_row: bool) -> None:
    """An account, and a ``registration_mode`` written before the upgrade ran — seeded early, or by a run that stopped — with metadata the upgrade never writes: it stays exactly as it was, whatever its value, an odd one included. An ``enable_registration`` beside it that says ``true`` is deleted and converts nothing. Every other setting as it was.

    The account is there on purpose: without it, «no accounts, nothing written» alone would explain why the row is kept.
    """
    _require_005()
    db = _copy(at_004, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        author = _insert_user(conn, "author")
        existing: Setting = (value, EARLIER_TYPE, EARLIER_DESCRIPTION, NEIGHBOUR_STAMP, author)
        _write_setting(conn, NEW_KEY, existing)
        if beside_the_old_row:
            _write_setting(conn, OLD_KEY, ("true", "bool", "Allow new users to register", STAMP, author))
        neighbours = _write_neighbours(conn, author)
        conn.commit()

    _migrate(db, "upgrade", REV_005)
    settings = _settings(db)

    assert settings == {NEW_KEY: existing, **neighbours}, f"{NEW_KEY} was there: the upgrade must leave it as it was, {existing}, and drop {OLD_KEY} if any; got {settings}"


def test_up_down_and_up_again_gives_the_settings_of_the_first_upgrade(at_004: Path, tmp_path: Path) -> None:
    """An account and no row: the upgrade writes ``open``; the downgrade turns it into ``enable_registration = 'true'``, a ``bool`` with its old description, at the time the upgrade wrote it, by nobody; upgrading again converts it back: every setting as after the first upgrade, ``updated_at`` included."""
    _require_005()
    db = _copy(at_004, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        _write_neighbours(conn, _insert_user(conn, "author"))
        conn.commit()

    _migrate(db, "upgrade", REV_005)
    first = _settings(db)
    _migrate(db, "downgrade", REV_004)
    between = _settings(db)
    _migrate(db, "upgrade", REV_005)
    again = _settings(db)

    written = first.get(NEW_KEY)
    assert written is not None and written[0] == OPEN, f"barrier: the first upgrade did not write the open row, so the round trip would be about nothing: {first}"
    assert between == {**_others(first), OLD_KEY: ("true", "bool", OLD_DESCRIPTION, written[3], None)}, f"the downgrade must turn the open row into enable_registration = 'true', with its time: {between}"
    assert again == first, f"up, down and up again must give the settings of the first upgrade: {first} then {again}"


# =============================================================================
# 7. A POPULATED 1.2 INSTALL UPGRADED
# =============================================================================


def test_a_1_2_install_keeps_every_row_of_every_table(upgraded_1_2: Upgrade | str) -> None:
    """Every table of the 1.2 install, ids included and ``sqlite_sequence`` too, read on the columns it had: as it was, but for the registration row, which becomes a mode (below); the tables added are the three of 1.3, and no table is lost."""
    print_section("A populated 1.2 install, upgraded")
    up = _ran(upgraded_1_2)
    before, after = _without_registration_rows(up.rows_before), _without_registration_rows(up.rows_after)

    assert set(after) - set(before) == NEW_TABLES and set(before) <= set(after), f"the upgrade must add the three 1.3 tables and lose none: added {sorted(set(after) - set(before))}, lost {sorted(set(before) - set(after))}"
    changes = _row_changes(before, after, set(before), columns_of=before)
    assert not changes, f"the upgrade changed rows of the 1.2 install: {changes}"
    print_success(f"{len(before)} tables, every row as it was")


def test_a_1_2_install_gives_every_existing_user_the_defaults(upgraded_1_2: Upgrade | str) -> None:
    """Every user of the 1.2 install has ``session_version`` 0 and NULL ``email_verified_at`` and ``last_seen_version``: no backfill (the developer's decision); how a verification requirement treats them is decided in the logic, not in the data."""
    up = _ran(upgraded_1_2)
    columns, rows = up.rows_before["users"]
    existing = {row[columns.index("id")] for row in rows}

    assert existing, "barrier: the 1.2 install has users"
    assert _new_user_columns(up.db) == dict.fromkeys(existing, EXISTING_USER_VALUES)


def test_a_1_2_install_holds_its_registration_as_a_mode_with_its_metadata(upgraded_1_2: Upgrade | str) -> None:
    """The install's ``enable_registration = 'false'``, written by user 1 on 2025-05-01, is ``registration_mode = 'disabled'``, ``str``, with the new description, by the same user at the same time; the old row is gone."""
    settings = _settings(_ran(upgraded_1_2).db)

    assert _registration(settings) == {NEW_KEY: ("disabled", NEW_TYPE, NEW_DESCRIPTION, V110_ROW_STAMP, V110_ROW_AUTHOR)}, f"the 1.1 install had registration off: {_registration(settings)}"


def test_a_1_2_install_gets_the_new_tables_empty_the_email_index_and_no_violation(upgraded_1_2: Upgrade | str) -> None:
    """``account_tokens`` and the plugin tables exist and are empty, ``ux_users_email_lower`` is there (the addresses are distinct), no ``reported_currency``; ``PRAGMA foreign_key_check`` is empty and ``integrity_check`` answers ok."""
    up = _ran(upgraded_1_2)

    assert {table: up.rows_after[table][1] for table in sorted(NEW_TABLES)} == {"account_tokens": [], SYSTEM_TABLE: [], USER_TABLE: []}
    assert EMAIL_INDEX in _index_list(up.db, "users"), f"the 1.2 install must get {EMAIL_INDEX}"
    assert "reported_currency" not in _table_info(up.db, "asset_provider_assignments")
    assert (up.violations, up.integrity) == ([], [("ok",)])


def test_a_1_2_install_without_its_registration_row_gets_open(install_1_2: Path, tmp_path: Path) -> None:
    """A 1.2 install with accounts and no ``enable_registration`` — deleted with plain SQL; 1.1 and 1.2 read the missing row as their default, true —: the upgrade writes ``registration_mode = 'open'``, nobody's, at the time of the upgrade; nothing brings ``enable_registration`` back; every other row of every table as it was."""
    _require_005()
    db = _copy(install_1_2, tmp_path / "sqlite" / "app.db")
    with _foreign_keys_on(db) as conn:
        deleted = conn.execute("DELETE FROM global_settings WHERE key = ?", (OLD_KEY,)).rowcount
        conn.commit()
    assert deleted == 1 and _accounts(db) > 0, "setup: a 1.2 install with accounts and no enable_registration"
    rows_before = _rows(db)

    started = _utc_now()
    _migrate(db, "upgrade", REV_005)
    finished = _utc_now()
    settings = _settings(db)

    _assert_written_by_the_upgrade(settings.get(NEW_KEY), started, finished)
    assert OLD_KEY not in settings, f"nothing may bring {OLD_KEY} back: {settings}"
    before, after = _without_registration_rows(rows_before), _without_registration_rows(_rows(db))
    changes = _row_changes(before, after, set(before), columns_of=before)
    assert not changes, f"the upgrade changed rows it had no reason to touch: {changes}"


# =============================================================================
# 8. ADDRESSES EQUAL BUT FOR A–Z: THE UPGRADE STOPS BEFORE THE INDEX, AND CHANGES NO ACCOUNT
# =============================================================================


def test_colliding_addresses_stop_the_upgrade_before_the_email_index_and_change_no_account(at_004: Path, frozen: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    """A database at 004 holding a pair and a trio of accounts whose addresses differ only in A–Z case (the trio's domains too), an account alone, settings, and an ``enable_registration`` one of them signed: ``upgrade`` stops with a ``RuntimeError`` in the retired 009's wording — the groups as ``#id 'username'``, the remedy ``./dev.py user set-email``, «No account was changed.» —, naming no account outside a group. No address shows, whole or by its local part, in any case, in the error, the output or the log a server would write.

    It stops where the retired 009 stopped, after the steps of 005–008, and what is pinned is what that guarantees: the
    database is still at 004, without ``ux_users_email_lower``; every account keeps every value it had; ``users`` has
    its three new columns and ``account_tokens`` is there, each declared as the frozen schema declares it — DDL run
    before the first DML, which pysqlite commits as it goes —, as the remedy the message names needs them. Whether the
    plugin tables and the converted registration row survive depends on the transaction the stop rolls back: not pinned.
    Barrier: before the run, the database holds the six accounts and none of the three objects.
    """
    print_section("Colliding addresses stop the upgrade before the email index")
    _require_005()
    scene = _collisions()
    db = _scene(at_004, tmp_path / "app.db", scene.everyone)
    rows_before = _rows(db)
    columns, accounts = rows_before["users"]
    assert {row[columns.index("id")] for row in accounts} == {account.id for account in scene.everyone}, "barrier: the database holds the six accounts of the scene"
    assert not set(USER_COLUMNS) & set(columns) and "account_tokens" not in _tables(db) and EMAIL_INDEX not in _index_list(db, "users"), "barrier: at 004 neither the users columns, nor account_tokens, nor the email index is there"
    assert set(_declared(frozen["objects"], REMEDY_NEEDS)) == set(REMEDY_NEEDS), "barrier: the frozen schema declares what the remedy needs"

    refusal = _refused_upgrade(db, capsys, caplog)

    _assert_refusal(refusal, groups=_groups(scene.pair, scene.trio), named=scene.colliding, unnamed=[scene.alone], addresses=[account.email for account in scene.everyone])
    assert _revision(db) == REV_004, f"a stopped upgrade must leave the database at {REV_004}: {_revision(db)}"
    assert EMAIL_INDEX not in _index_list(db, "users"), f"a stopped upgrade must not leave {EMAIL_INDEX} behind"
    changes = _row_changes(rows_before, _rows(db), {"users"}, columns_of=rows_before)
    assert not changes, f"«No account was changed.»: every account must keep the values it had: {changes}"
    left = _declared(_snapshot(db)["objects"], REMEDY_NEEDS)
    assert left == _declared(frozen["objects"], REMEDY_NEEDS), f"the users columns and account_tokens, which the remedy needs, must be there as the frozen schema declares them: {sorted(left)}"
    print_success("stopped before the email index; five accounts named, no address shown, no account changed, the remedy's tables there")


def test_the_non_ascii_pair_does_not_stop_the_upgrade(at_004: Path, tmp_path: Path) -> None:
    """The documented limit: ``Émile.<hex>@example.com`` beside ``émile.<hex>@example.com`` is no collision — É is not A–Z, and the check folds as SQLite's ``lower()`` does —: the upgrade goes through, both accounts keep their address as written, and the index then refuses ``ÉMILE.<HEX>@EXAMPLE.COM``, Émile's address but for A–Z."""
    _require_005()
    capital, small = _non_ascii_pair()
    db = _scene(at_004, tmp_path / "app.db", (capital, small))

    _migrate(db, "upgrade", REV_005)

    assert _revision(db) == REV_005, f"the non-ASCII pair must not stop the upgrade: {_revision(db)}"
    emails = _emails(db)
    assert (emails[capital.id], emails[small.id]) == (capital.email, small.email), "both accounts keep their address, as written"
    refused = _refused_by_sql(db, INSERT_ACCOUNT, _values(Account(8103, f"emu_{_tag()}", capital.email.upper())))
    assert refused is not None and EMAIL_INDEX in refused, f"{capital.email.upper()!r} is Émile's address but for A–Z: {EMAIL_INDEX} must refuse it: {refused}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("quiet_environment")
async def test_the_remedy_the_refusal_names_works_on_the_database_it_refused(at_004: Path, frozen: dict[str, Any], tmp_path: Path, user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    """The refusal tells the administrator to run ``./dev.py user set-email <username> <address>``: on the database it refused, in this process, the command answers with a ✅ line and moves the address, and leaves the database at 004 — the ``user`` commands do not migrate. With the pair separated the upgrade still stops, naming the trio alone; with the trio separated too it goes through, every account holds the address the remedy left, and the schema is the frozen one: the run completes whatever the stopped runs left done or undone.

    The remedy reads and writes the accounts through the 1.3 ``User`` model (``select(User)``, the session version, the
    password-reset and setup links in ``account_tokens``): it runs because the stop comes after the ``users`` columns
    and ``account_tokens``. Red until the cure only.
    """
    print_section("The remedy the refusal names, on the database it refused")
    _require_005()
    scene = _collisions()
    db = _scene(at_004, tmp_path / "app.db", scene.everyone)
    refusal = _refused_upgrade(db, capsys, caplog)
    assert refusal.message is not None and REMEDY in refusal.message, f"barrier: the upgrade did not stop naming the remedy, so there is nothing to remedy: {refusal.error}"
    moves = {account.id: f"moved.{_tag()}@example.com" for account in (scene.pair[1], *scene.trio[1:])}
    addresses = [account.email for account in scene.everyone] + list(moves.values())

    await _remedy(user_cli, monkeypatch, capsys, db, scene.pair[1], moves[scene.pair[1].id])
    assert _revision(db) == REV_004, f"a user command must not migrate the database: {_revision(db)}"
    _assert_refusal(_refused_upgrade(db, capsys, caplog), groups=_groups(scene.trio), named=scene.trio, unnamed=[*scene.pair, scene.alone], addresses=addresses)
    for account in scene.trio[1:]:
        await _remedy(user_cli, monkeypatch, capsys, db, account, moves[account.id])
    _migrate(db, "upgrade", REV_005)

    assert _revision(db) == REV_005, f"with no collision left the upgrade must go through: {_revision(db)}"
    assert _emails(db) == {account.id: moves.get(account.id, account.email) for account in scene.everyone}, "every account holds the address the remedy left"
    differences = _schema_differences(frozen["objects"], _snapshot(db)["objects"])
    assert not differences, f"the run after the remedy must end with the frozen schema, {EMAIL_INDEX} included: {differences}"
    print_success("set-email on the refused database, then the upgrade through, to the frozen schema")


# =============================================================================
# 9. EVERY STEP CHECKS BEFORE IT ACTS
# =============================================================================


@pytest.mark.parametrize("state", sorted(STOPPED_UPGRADES))
def test_an_upgrade_stopped_half_way_completes_to_the_frozen_schema(at_004: Path, frozen: dict[str, Any], tmp_path: Path, state: str) -> None:
    """A database at 004 holding part of what the upgrade creates — a run stopped after its first ``ALTER``; after the DDL that pysqlite commits before the first DML, ``account_tokens`` included, what the duplicate check leaves when ``enable_registration`` is there; or a plugin table with a row, the email index and three of the 13 gone —, the revision still 004: ``upgrade`` goes through and ends with the frozen schema, and a row the run found is kept."""
    _require_005()
    db = _copy(at_004, tmp_path / "app.db")
    steps = STOPPED_UPGRADES[state]
    with _foreign_keys_on(db) as conn:
        for statement in _statements(steps, frozen):
            conn.execute(statement)
        survivor = _insert_system(conn, "survivor") if ("frozen", SYSTEM_TABLE) in steps else None
        conn.commit()
    assert _revision(db) == REV_004, "setup: the run stopped before Alembic recorded the revision"

    _migrate(db, "upgrade", REV_005)

    assert _revision(db) == REV_005, f"the upgrade must go through: {_revision(db)}"
    differences = _schema_differences(frozen["objects"], _snapshot(db)["objects"])
    assert not differences, f"an upgrade that finds part of its work done must end with the schema of a new database: {differences}"
    if survivor is not None:
        with _connect(db) as conn:
            kept = conn.execute(f"SELECT id, field_key FROM {SYSTEM_TABLE}").fetchall()
        assert kept == [(survivor, "survivor")], f"the table found must be kept with its rows: {kept}"


def test_the_upgrade_run_again_over_its_own_work_changes_nothing(fresh_005: Path | str, tmp_path: Path) -> None:
    """The whole revision applied, then ``alembic_version`` set back to 004 by hand — an upgrade that wrote everything and stopped before Alembic recorded it —, with an account, a ``registration_mode`` and a plugin setting: ``upgrade`` goes through and changes no object of ``sqlite_master``, not even its SQL text, and no row."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        author = _insert_user(conn, "author")
        _write_setting(conn, NEW_KEY, ("invite", NEW_TYPE, NEW_DESCRIPTION, STAMP, author))
        _insert_system(conn, "region", author=author)
        conn.execute("UPDATE alembic_version SET version_num = ?", (REV_004,))
        conn.commit()
    schema_before, rows_before = _raw_schema(db), _rows(db)

    _migrate(db, "upgrade", REV_005)

    assert _revision(db) == REV_005, f"the upgrade over its own work must go through: {_revision(db)}"
    assert _raw_schema(db) == schema_before, "the body run again must leave the schema as it found it"
    changes = _row_changes(rows_before, _rows(db), set(rows_before) - BOOKKEEPING, columns_of=rows_before)
    assert not changes, f"the body run again must change no row: {changes}"


# =============================================================================
# 10. THE DOWNGRADE
# =============================================================================


def test_the_downgrade_of_a_new_database_gives_a_new_004_database(fresh_005: Path | str, at_004: Path, tmp_path: Path) -> None:
    """``downgrade`` to 004 of a new database at the revision gives what a new database at 004 is: the same objects of ``sqlite_master``, SQL text included (whitespace collapsed) — ``users`` declared as ``001`` declares it —, and the same rows."""
    print_section("The downgrade of a new database")
    db = _copy(_ran(fresh_005), tmp_path / "app.db")

    _migrate(db, "downgrade", REV_004)

    assert _revision(db) == REV_004
    expected, actual = _snapshot(at_004), _snapshot(db)
    differences = _schema_differences(expected["objects"], actual["objects"])
    assert not differences, f"the downgrade must give the schema of a new 004 database: {differences}"
    assert actual == expected, "the same objects in the same order, and the same rows"
    print_success("a new 004 database, SQL text included")


def test_the_downgrade_recreates_the_13_indexes_with_their_001_definitions(fresh_005: Path | str, at_004: Path, tmp_path: Path) -> None:
    """After the downgrade each of the 13 indexes is there again, ``CREATE [UNIQUE] INDEX <name> ON <table> (<columns>)`` exactly as ``001_initial`` wrote it. Barrier: a new database at 004 holds those 13 definitions, and the database at the revision none of them."""
    expected = {name: definition for name, (_table, definition) in REDUNDANT_INDEXES.items()}
    assert _redundant_present(at_004) == expected, f"barrier: a new database at 004 must hold the 13 indexes with these definitions: {_redundant_present(at_004)}"
    db = _copy(_ran(fresh_005), tmp_path / "app.db")
    assert _redundant_present(db) == {}, "barrier: at the revision none of the 13 is left"

    _migrate(db, "downgrade", REV_004)

    assert _redundant_present(db) == expected, f"the downgrade must recreate the 13 with their 001 definitions: {_redundant_present(db)}"


@pytest.mark.parametrize(("mode", "old_value"), DOWNGRADES)
def test_the_downgrade_converts_registration_mode_back(fresh_005: Path | str, tmp_path: Path, mode: str, old_value: str) -> None:
    """As the old 006 downgrade did: ``open`` → ``"true"``, ``invite`` and ``disabled`` → ``"false"`` — the old setting had no middle ground, and closed is the safe reading of invitation-only —; a ``bool`` with its old description, the date and author copied; the new row gone; the neighbours as they were; at 004."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        author = _insert_user(conn, "author")
        _write_setting(conn, NEW_KEY, (mode, NEW_TYPE, NEW_DESCRIPTION, STAMP, author))
        neighbours = _write_neighbours(conn, author)
        conn.commit()

    _migrate(db, "downgrade", REV_004)
    settings = _settings(db)

    assert _revision(db) == REV_004
    assert _registration(settings) == {OLD_KEY: (old_value, "bool", OLD_DESCRIPTION, STAMP, author)}, f"{NEW_KEY}={mode!r} must go back to {OLD_KEY}={old_value!r}: {_registration(settings)}"
    assert _others(settings) == neighbours, f"the downgrade touched other settings: {_others(settings)}"


def test_a_downgrade_that_finds_enable_registration_keeps_it_and_drops_the_new_row(fresh_005: Path | str, tmp_path: Path) -> None:
    """Both rows at the revision — a downgrade that wrote the old row and stopped —, disagreeing on purpose (``'true'`` against ``disabled``): ``enable_registration`` stays exactly as it is and ``registration_mode`` goes."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")
    existing: Setting = ("true", "bool", "Allow new users to register", NEIGHBOUR_STAMP, None)
    with _foreign_keys_on(db) as conn:
        author = _insert_user(conn, "author")
        _write_setting(conn, NEW_KEY, ("disabled", NEW_TYPE, NEW_DESCRIPTION, STAMP, author))
        _write_setting(conn, OLD_KEY, existing)
        conn.commit()

    _migrate(db, "downgrade", REV_004)

    assert _revision(db) == REV_004
    assert _registration(_settings(db)) == {OLD_KEY: existing}, f"{OLD_KEY} was there: the downgrade must keep it as it was and drop {NEW_KEY}: {_registration(_settings(db))}"


def test_a_downgrade_stopped_half_way_completes_to_a_new_004_database(fresh_005: Path | str, at_004: Path, tmp_path: Path) -> None:
    """A downgrade that stopped after its first steps — the 13 indexes recreated, ``ux_users_email_lower`` and ``plugin_user_settings`` dropped —, the revision still the new one: ``downgrade`` to 004 goes through and gives the schema of a new database at 004."""
    db = _copy(_ran(fresh_005), tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        for _table, definition in REDUNDANT_INDEXES.values():
            conn.execute(definition)
        conn.execute(f"DROP INDEX {EMAIL_INDEX}")
        conn.execute(f"DROP TABLE {USER_TABLE}")
        conn.commit()
    assert _revision(db) == REV_005 and len(_redundant_present(db)) == len(REDUNDANT_INDEXES) and USER_TABLE not in _tables(db), "setup: the interrupted state"

    _migrate(db, "downgrade", REV_004)

    assert _revision(db) == REV_004
    assert _snapshot(db) == _snapshot(at_004), f"a downgrade that finds part of its work done must end with a new 004 database: {_schema_differences(_snapshot(at_004)['objects'], _snapshot(db)['objects'])}"


def test_the_downgrade_of_a_1_2_install_gives_back_its_1_2_schema(round_trip: RoundTrip | str) -> None:
    """The 1.2 install at the revision, holding what 1.3 writes — tokens through the three foreign keys, plugin settings of the instance and of users, values of its own in the user columns —, downgraded to 004 with foreign keys on: the schema it had at 004 comes back, SQL text included (whitespace collapsed) — the three tables, the three columns and the email index gone, the 13 indexes back —; ``foreign_key_check`` empty, ``integrity_check`` ok."""
    print_section("The downgrade of a populated install")
    trip = _ran(round_trip)

    assert trip.revision_down == REV_004
    differences = _schema_differences(trip.schema_at_004, trip.schema_down)
    assert not differences, f"the downgrade must give back the schema the install had at 004: {differences}"
    assert (trip.violations_down, trip.integrity_down) == ([], [("ok",)])
    print_success("the 1.2 schema back, SQL text included")


def test_the_downgrade_of_a_1_2_install_touches_no_other_row(round_trip: RoundTrip | str) -> None:
    """Every row of every table the downgrade keeps is the row it had at the revision, read on the columns the table keeps: no user lost, nothing cascaded into ``user_settings``, ``broker_user_access`` or the onboarding tables, nothing unlinked in ``global_settings``. The registration row is ``enable_registration = 'false'`` again, a bool with its old description, by its 1.1 author at its 1.1 time.

    The downgrade ran with foreign keys on (asserted by ``_migrate``), and before it every one of those tables had rows
    pointing at users (asserted by the fixture): a rebuild of ``users`` would show here.
    """
    trip = _ran(round_trip)
    expected, actual = _without_registration_rows(trip.rows_with_1_3), _without_registration_rows(trip.rows_down)

    changes = _row_changes(expected, actual, set(actual), columns_of=actual)
    assert not changes, f"the downgrade changed rows it had no reason to touch: {changes}"
    assert CHILDREN_OF_USERS | {"users"} <= set(actual), f"the downgrade lost tables: {sorted((CHILDREN_OF_USERS | {'users'}) - set(actual))}"
    assert _registration(trip.settings_down) == {OLD_KEY: (V110_ROW[0], "bool", OLD_DESCRIPTION, V110_ROW_STAMP, V110_ROW_AUTHOR)}, f"the mode must go back to the old row: {_registration(trip.settings_down)}"


def test_upgrading_the_1_2_install_again_brings_the_1_3_schema_back_empty(round_trip: RoundTrip | str) -> None:
    """``upgrade`` after the downgrade gives the schema of the first upgrade, SQL text included; ``account_tokens`` and the plugin tables empty; every user at 0 / NULL / NULL — the values they held went with the downgrade —; ``registration_mode = 'disabled'`` again with its 1.1 metadata; every other row as after the downgrade; no violation."""
    trip = _ran(round_trip)
    columns, rows = trip.rows_down["users"]
    users = {row[columns.index("id")] for row in rows}
    expected, actual = _without_registration_rows(trip.rows_down), _without_registration_rows(trip.rows_again)

    assert trip.revision_again == REV_005
    assert not _schema_differences(trip.schema_at_005, trip.schema_again), f"upgrading again must give the schema of the first upgrade: {_schema_differences(trip.schema_at_005, trip.schema_again)}"
    assert {table: trip.rows_again[table][1] for table in sorted(NEW_TABLES)} == {"account_tokens": [], SYSTEM_TABLE: [], USER_TABLE: []}
    assert trip.new_columns_again == dict.fromkeys(users, EXISTING_USER_VALUES)
    assert _registration(trip.settings_again) == {NEW_KEY: ("disabled", NEW_TYPE, NEW_DESCRIPTION, V110_ROW_STAMP, V110_ROW_AUTHOR)}
    changes = _row_changes(expected, actual, set(expected), columns_of=expected)
    assert not changes, f"upgrading again changed rows: {changes}"
    assert trip.violations_again == []
