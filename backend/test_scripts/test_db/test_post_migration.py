"""Post-migration fixes and their first fix, ``autoincrement`` (plan 34_accountAndIdReuse §2.3, §7).

A 1.1 install upgraded to head has no AUTOINCREMENT: SQLite gives the id of a deleted broker, asset
or user to the next one, while the old id is still saved in URLs, localStorage, BRIM sidecars and
``broker_<id>`` folders. ``run_post_migration_fixes`` runs after ``alembic upgrade head``, detects the
anomaly and rebuilds the census tables with AUTOINCREMENT. The contract pinned here:

1. A new database (fresh ``upgrade head``) needs nothing: outcome ``clean``, the database as it was,
   no backup, no folder renamed.
2. A populated 1.1 database upgraded to head is converted: outcome ``applied``; AUTOINCREMENT on
   exactly the census tables; every row of every table identical, ids included; the indexes
   identical; the DDL identical but for AUTOINCREMENT; no foreign key violation; ``sqlite_sequence``
   at each census table's highest id; a deleted highest id never comes back; no backup left (D2).
3. A schema from a later migration (a census table with a new column, an index on it, rows using
   it) is converted from the DDL in force and loses none of it (D1, the developer's request).
4. A second run finds nothing to do: ``clean``, no backup, nothing written.
5. A conversion that must stop half way (one census table declared with a table-level
   ``PRIMARY KEY (id)``, a form the fix refuses) leaves the whole database as it was: outcome
   ``failed`` with its reason, the backup kept beside the database as
   ``<db name>.pre-autoincrement-<UTC yyyymmddThhmmss>.bak``, equal to the database before, in the
   report. The startup hook survives a run that raises, and returns ``None``.
6. A database failing the integrity check (``_integrity_ok`` → False) is not touched at all.
7. Orphan broker folders (D4), ``broker_reports/{uploaded,parsed,failed}/broker_<n>`` with ``<n>``
   absent from ``brokers``: deleted with their files after a verified fix, while live brokers'
   folders, ``broker_none``, non-numeric names and everything else stay; back under their names
   with their files when the fix fails; listed and untouched in a dry run; untouched when the
   database is outside the data dir.
8. A dry run reports ``would_apply`` and writes nothing: the database byte-identical, no backup.
9. ``python -m backend.app.db.post_migration`` converts and exits 0; ``--dry-run`` exits 0 and writes
   nothing; a failed fix exits 1.
10. ``run_post_migration_fixes_at_startup()`` runs the fixes on the configured database and data
    dir and returns their report.
11. Beyond the brief (plan §2.3, §7): the lifespan runs the hook right after the migrations and
    before the first connection, and the server starts even when the fixes raise.
12. Concurrent runs (review defect: several workers start together and race): the run holds an
    exclusive ``fcntl.flock`` on ``<db name>.post-migration.lock`` beside the database for its whole
    run — detection included, dry runs included — and leaves the file on disk; a second offline
    script started meanwhile waits, then finds nothing to do: ``clean``, exit 0, no backup.
13. The log says how long it took (plan §5, risk 3: a big database makes the first start slower,
    once): the closing event of a run that applies fixes — ``Post-migration fixes applied and
    verified`` or ``Post-migration fix failed: the database was left as it was``, logger
    ``backend.app.db.post_migration`` — carries ``seconds``, a float >= 0, beside its usual fields.
14. A foreign-key violation already in the database (W-B22) blocks no fix: the run's foreign-key check, like
    its row counts, compares with the database just before each fix, and only a violation the fix brings
    is a problem. A received TRANSFER whose partner was deleted with foreign keys off — its link names a row
    that no longer exists — no longer fails ``autoincrement``: both fixes ``applied``, the half an ADJUSTMENT
    without a link, nothing left broken, no backup, a second run ``clean``. A violation in another table — a
    price of a deleted asset — stays as it is and is reported once per run, in a warning of logger
    ``backend.app.db.post_migration`` whose event starts with ``Foreign key violations``, with its count and
    rows; ``applied``, no backup, a second run ``clean``. RED until the cure: today either fails
    ``autoincrement`` at every start, a backup kept each time, and ``orphan_pair_halves`` never runs. Guard,
    green before and after: a fix that breaks a link itself still fails, the database as it was, the backup kept.
15. The offline script logs to the console only (W-B23, guard, green before and after): a run through
    ``python -m backend.app.db.post_migration`` writes no file in the configured data dir — no ``logs/`` —
    and leaves its canary as it was.
16. The lock file is never a link, and is its owner's alone (Z-28, as the backup and scheduler locks): the run opens
    ``<db name>.post-migration.lock`` with ``os.open(…, O_RDWR | O_CREAT | O_NOFOLLOW, 0o600)`` and ``flock``s the
    descriptor. A symbolic link at that path — dangling, or to an existing file — makes the run raise ``OSError``
    before the database is opened: no connection, so no fix, the database byte-identical and unconverted, no backup;
    nothing created behind a dangling link, an existing file behind it unchanged (bytes and mode), the link as it was.
    A lock file the run creates gives its owner read and write and group and others nothing (0o600, which the umask
    can only narrow: never pinned exactly). RED until the cure: today ``open(…, "a+")`` follows the link — creating a
    dangling one's target — and runs the fixes, and creates the file 0o666 less the umask (0o644 under the usual 0o022).
17. Table names a database brings are quoted (B-36: the fixes run on a restored archive's copy too, whose names are
    user data). A 1.1 database at head, ``autoincrement`` pending, also holding a table named ``x"y`` and one named
    ``a" WHERE 1 --``: the run applies the fix with no exception and no error, every count of rows it takes
    (``_row_counts``) holds both tables with their rows, they keep them, no backup left. RED until the cure: today
    ``_row_counts`` puts the name between double quotes as it is, and the run raises ``OperationalError``.

The 1.1 database is real: ``fixtures/db/schema_v1_1_0.sql`` (the v1.1.0 schema at revision
5b1333fa6b07), populated here with foreign keys on — every table, rows of non-census tables pointing
into census ones, a self-referencing transfer pair — and with gaps: deleted rows, among them the
highest broker id, so that "ids identical" means something. The real migrations then take it to head.

Safety. Every database and data dir is temporary. Alembic always gets ``-x sqlalchemy.url=`` (without
it ``backend/alembic/env.py`` migrates the configured database). Every test, and every child process,
runs with the configured test data dir pointed at a sandbox holding a canary broker folder that is
checked afterwards: an implementation reaching for ``get_data_dir()`` on its own could only ever meet
that sandbox.

Barriers. A test asserting that something was *kept* first proves that the same run *did* its work:
a run that does nothing keeps everything, and must not pass for it. The one guard, green on the stub,
is the offline script's ``--dry-run`` test, and it says so.
"""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import importlib
import json
import os
import re
import select
import sqlite3
import stat
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Optional

import pytest
import structlog
from structlog.testing import capture_logs

from backend.app.config import PROJECT_ROOT
from backend.app.db import post_migration
from backend.app.db.post_migration import PostMigrationReport
from backend.app.db.post_migration.autoincrement import AutoincrementFix

FIX = "autoincrement"
# Decision D1 of the developer (plan §0.1), written out: test_autoincrement_schema pins AUTOINCREMENT_TABLES to the same six.
CENSUS = frozenset({"users", "brokers", "assets", "transactions", "fx_conversion_routes", "asset_events"})
V110_SCHEMA = Path(__file__).resolve().parents[1] / "fixtures" / "db" / "schema_v1_1_0.sql"
CHILD_TIMEOUT = 300
CSV_BYTES = b"date,amount\n2025-01-02,100\n"
CANARY = b"canary: a configured data dir that no run was given\n"
CANARY_FILE = Path("broker_reports", "uploaded", "broker_999", "canary.csv")

# The census ids of the populated 1.1 database: every table has gaps, and brokers lost its highest id, 5.
V110_IDS = {
    "asset_events": [1, 3, 5],
    "assets": [1, 3, 4, 5],
    "brokers": [1, 2, 4],
    "fx_conversion_routes": [1, 3],
    "transactions": [1, 2, 3, 4, 5, 8, 10],
    "users": [1, 3, 4],
}
# Below broker_reports/: the folders of brokers that no longer exist (3, 5) or never did (42).
DEAD_BROKER_DIRS = ("failed/broker_5", "parsed/broker_3", "parsed/broker_42", "uploaded/broker_3")
# The same folders as the report lists them: relative to the data dir.
ORPHAN_BROKER_DIRS = sorted(f"broker_reports/{folder}" for folder in DEAD_BROKER_DIRS)

NOT_APPLIED = "barrier: the fix did not report 'applied', so the assertions below would prove nothing about a conversion"
NOT_CONVERTED = "barrier: the census tables have no AUTOINCREMENT, so no conversion happened and the comparison below would pass for a run that does nothing"
NOT_FAILED = "barrier: the fix did not report 'failed', so the provoked refusal did not happen and 'nothing changed' would pass for a run that does nothing"
NOT_DRY = "barrier: the dry run did not report 'would_apply', so it did not even detect the anomaly and 'nothing written' would pass for a run that does nothing"
NO_CLEANUP = "barrier: the orphan folders are still there, so the cleanup did not run and 'the rest survives' would pass for a run that does nothing"

Master = list[tuple[str, str, str, Optional[str]]]
Rows = dict[str, tuple[list[str], list[tuple[Any, ...]]]]
Tree = dict[str, tuple[str, Any]]

# The rows of a 1.1 install, written with foreign keys on. Every table gets rows; non-census tables point into
# census ones; transactions 4 and 5 are a transfer pair pointing at each other; then rows are deleted the way the
# app deletes them, leaving gaps — broker 5, the highest broker id, among them.
V110_ROWS = """
PRAGMA foreign_keys = ON;
BEGIN;

INSERT INTO users (id, username, email, hashed_password, is_active, is_superuser, login_count,
                   donation_popup_last_shown_at, donation_popup_logins_since_shown, created_at, updated_at) VALUES
    (1, 'alice', 'alice@example.test', '$argon2id$alice', 1, 1, 42, '2026-05-01 08:00:00.000000', 3, '2025-01-10 09:00:00.000000', '2026-09-01 18:30:00.000000'),
    (2, 'bob',   'bob@example.test',   '$argon2id$bob',   1, 0,  7, NULL, 0, '2025-02-11 10:00:00.000000', '2025-02-11 10:00:00.000000'),
    (3, 'carol', 'carol@example.test', '$argon2id$carol', 0, 0,  1, NULL, 1, '2025-03-12 11:00:00.000000', '2025-04-01 11:00:00.000000'),
    (4, 'dave',  'dave@example.test',  '$argon2id$dave',  1, 0,  5, NULL, 0, '2025-04-13 12:00:00.000000', '2025-04-13 12:00:00.000000');

INSERT INTO user_settings (id, user_id, base_currency, language, theme, avatar_url, created_at, updated_at) VALUES
    (1, 1, 'EUR', 'it', 'dark',  '/api/v1/uploads/avatar-alice.png', '2025-01-10 09:00:00.000000', '2025-06-01 09:00:00.000000'),
    (2, 2, 'USD', 'en', 'light', NULL, '2025-02-11 10:00:00.000000', '2025-02-11 10:00:00.000000'),
    (3, 3, 'CHF', 'fr', 'light', NULL, '2025-03-12 11:00:00.000000', '2025-03-12 11:00:00.000000'),
    (4, 4, 'EUR', 'es', 'dark',  NULL, '2025-04-13 12:00:00.000000', '2025-04-13 12:00:00.000000');

INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id) VALUES
    -- The registration switch as 1.1 named it: migration 006 converts it to registration_mode on the way to head
    -- (test_migration_006_registration asserts it on these very rows). A 1.1 install never had the new key.
    ('enable_registration', 'false', 'bool',   'Allow new users to register', '2025-05-01 10:00:00.000000', 1),
    ('default_language',    'en',    'string', 'Language of new accounts',    '2025-05-02 10:00:00.000000', 2),
    ('scheduler_timezone',  'UTC',   'string', NULL,                          '2025-05-03 10:00:00.000000', NULL);

INSERT INTO brokers (id, name, description, portal_url, icon_url, default_import_plugin, allow_cash_overdraft,
                     allow_asset_shorting, is_active, opened_at, created_at, updated_at) VALUES
    (1, 'Broker Alpha', 'Main account', 'https://alpha.example.test', NULL, 'broker_generic_csv', 0, 0, 1, '2024-12-01', '2025-01-10 09:05:00.000000', '2025-01-10 09:05:00.000000'),
    (2, 'Broker Beta',  NULL, NULL, '/icons/beta.svg', NULL, 1, 0, 1, NULL, '2025-02-11 10:05:00.000000', '2025-03-01 10:05:00.000000'),
    (3, 'Broker Gamma', 'Closed, then deleted', NULL, NULL, NULL, 0, 0, 0, NULL, '2025-03-12 11:05:00.000000', '2025-03-12 11:05:00.000000'),
    (4, 'Broker Delta', NULL, NULL, NULL, NULL, 0, 1, 1, '2025-04-01', '2025-04-13 12:05:00.000000', '2025-04-13 12:05:00.000000'),
    (5, 'Broker Omega', 'The highest id, deleted before the conversion', NULL, NULL, NULL, 0, 0, 1, NULL, '2025-05-14 13:05:00.000000', '2025-05-14 13:05:00.000000');

INSERT INTO broker_user_access (id, user_id, broker_id, role, share_percentage, created_at, updated_at) VALUES
    (1, 1, 1, 'OWNER',  1,    '2025-01-10 09:05:00.000000', '2025-01-10 09:05:00.000000'),
    (2, 3, 1, 'VIEWER', 0.25, '2025-03-12 11:06:00.000000', '2025-03-12 11:06:00.000000'),
    (3, 1, 2, 'OWNER',  0.5,  '2025-02-11 10:05:00.000000', '2025-02-11 10:05:00.000000'),
    (4, 2, 2, 'EDITOR', 0.5,  '2025-02-11 10:06:00.000000', '2025-02-11 10:06:00.000000'),
    (5, 4, 4, 'OWNER',  1,    '2025-04-13 12:05:00.000000', '2025-04-13 12:05:00.000000'),
    (6, 1, 3, 'OWNER',  1,    '2025-03-12 11:05:00.000000', '2025-03-12 11:05:00.000000'),
    (7, 1, 5, 'OWNER',  1,    '2025-05-14 13:05:00.000000', '2025-05-14 13:05:00.000000');

INSERT INTO assets (id, display_name, currency, icon_url, classification_params, asset_type, quote_base_quantity, active,
                    user_url, identifier_isin, identifier_ticker, identifier_cusip, identifier_sedol, identifier_figi,
                    identifier_uuid, identifier_other, created_at, updated_at) VALUES
    (1, 'Apple Inc.', 'USD', NULL, '{"sector": "Technology"}', 'STOCK', 1, 1, NULL, 'US0378331005', 'AAPL', '037833100', NULL, 'BBG000B9XRY4', NULL, '["AAPL.US"]', '2025-01-10 09:10:00.000000', '2025-01-10 09:10:00.000000'),
    (2, 'Delisted Corp', 'EUR', NULL, NULL, 'STOCK', 1, 0, NULL, 'IT0000000001', 'DLST', NULL, NULL, NULL, NULL, NULL, '2025-01-11 09:10:00.000000', '2025-01-11 09:10:00.000000'),
    (3, 'MSCI World Index', 'USD', NULL, NULL, 'INDEX', 1, 1, NULL, NULL, 'MSCIWORLD', NULL, NULL, NULL, NULL, NULL, '2025-01-12 09:10:00.000000', '2025-01-12 09:10:00.000000'),
    (4, 'BTP 2030', 'EUR', NULL, NULL, 'BOND', 100, 1, 'https://bond.example.test/btp-2030', 'IT0005383309', NULL, NULL, NULL, NULL, NULL, NULL, '2025-01-13 09:10:00.000000', '2025-01-13 09:10:00.000000'),
    (5, 'Crowd Loan 7', 'EUR', NULL, NULL, 'CROWDFUND', 1, 1, NULL, NULL, NULL, NULL, NULL, NULL, '6f1c1b1e-7a43-4b8e-9d55-2b8e8d0c6a11', NULL, '2025-01-14 09:10:00.000000', '2025-01-14 09:10:00.000000');

INSERT INTO asset_provider_assignments (id, asset_id, provider_code, identifier, identifier_type, provider_params,
                                        last_fetch_at, created_at, updated_at) VALUES
    (1, 1, 'yfinance',       'AAPL',         'TICKER', NULL,                  '2026-09-30 22:00:00.000000', '2025-01-10 09:11:00.000000', '2026-09-30 22:00:00.000000'),
    (2, 2, 'justetf',        'IT0000000001', 'ISIN',   '{"exchange": "MIL"}', NULL, '2025-01-11 09:11:00.000000', '2025-01-11 09:11:00.000000'),
    (3, 3, 'mockprov',       'MSCIWORLD',    'TICKER', NULL,                  NULL, '2025-01-12 09:11:00.000000', '2025-01-12 09:11:00.000000'),
    (4, 4, 'borsa_italiana', 'IT0005383309', 'ISIN',   NULL,                  NULL, '2025-01-13 09:11:00.000000', '2025-01-13 09:11:00.000000');

INSERT INTO price_history (id, asset_id, date, open, high, low, close, volume, adjusted_close, currency,
                           source_plugin_key, fetched_at) VALUES
    (1, 1, '2025-01-02', 248.93, 249.10, 241.82, 243.85, 55740700, 243.58, 'USD', 'yfinance', '2025-01-03 06:00:00.000000'),
    (2, 1, '2025-01-03', 243.36, 244.18, 241.89, 243.36, 40244100, NULL,   'USD', 'yfinance', '2025-01-04 06:00:00.000000'),
    (3, 2, '2025-01-02', NULL, NULL, NULL, 1.5,    NULL, NULL, 'EUR', 'justetf',        '2025-01-03 06:00:00.000000'),
    (4, 3, '2025-01-02', NULL, NULL, NULL, 3707.5, NULL, NULL, 'USD', 'mockprov',       '2025-01-03 06:00:00.000000'),
    (5, 4, '2025-01-02', NULL, NULL, NULL, 98.12,  NULL, NULL, 'EUR', 'borsa_italiana', '2025-01-03 06:00:00.000000'),
    (6, 5, '2025-01-02', NULL, NULL, NULL, 1,      NULL, NULL, 'EUR', 'manual',         '2025-01-03 06:00:00.000000');

INSERT INTO asset_events (id, asset_id, date, type, value, currency, provider_assignment_id, notes, created_at, updated_at) VALUES
    (1, 1, '2025-02-14', 'DIVIDEND',         0.25, 'USD', 1,    NULL,                '2025-02-15 06:00:00.000000', '2025-02-15 06:00:00.000000'),
    (2, 2, '2025-03-01', 'DIVIDEND',         0.1,  'EUR', 2,    NULL,                '2025-03-02 06:00:00.000000', '2025-03-02 06:00:00.000000'),
    (3, 4, '2025-06-30', 'INTEREST',         1.35, 'EUR', NULL, 'Semiannual coupon', '2025-07-01 06:00:00.000000', '2025-07-01 06:00:00.000000'),
    (4, 1, '2025-05-15', 'DIVIDEND',         0.26, 'USD', 1,    'A duplicate',       '2025-05-16 06:00:00.000000', '2025-05-16 06:00:00.000000'),
    (5, 3, '2025-07-01', 'PRICE_ADJUSTMENT', 2,    'USD', NULL, NULL,                '2025-07-02 06:00:00.000000', '2025-07-02 06:00:00.000000');

INSERT INTO transactions (id, broker_id, asset_id, type, date, quantity, amount, currency, related_transaction_id, tags,
                          description, cost_basis_override, cost_basis_currency, asset_event_id, created_at, updated_at) VALUES
    (1,  1, NULL, 'DEPOSIT',  '2025-01-02', 0,  10000,   'EUR', NULL, NULL,        'Initial deposit',   NULL,  NULL,  NULL, '2025-01-02 10:00:00.000000', '2025-01-02 10:00:00.000000'),
    (2,  1, 1,    'BUY',      '2025-01-03', 10, -2433.6, 'USD', NULL, 'core,long', NULL,                NULL,  NULL,  NULL, '2025-01-03 10:00:00.000000', '2025-01-03 10:00:00.000000'),
    (3,  1, 1,    'DIVIDEND', '2025-02-14', 0,  2.5,     'USD', NULL, NULL,        NULL,                NULL,  NULL,  1,    '2025-02-15 10:00:00.000000', '2025-02-15 10:00:00.000000'),
    (4,  1, 1,    'TRANSFER', '2025-03-01', -4, 0,       NULL,  5,    NULL,        'To Broker Beta',    NULL,  NULL,  NULL, '2025-03-01 10:00:00.000000', '2025-03-01 10:00:00.000000'),
    (5,  2, 1,    'TRANSFER', '2025-03-01', 4,  0,       NULL,  4,    NULL,        'From Broker Alpha', 980.5, 'USD', NULL, '2025-03-01 10:00:00.000000', '2025-03-01 10:00:00.000000'),
    (6,  3, NULL, 'DEPOSIT',  '2025-03-05', 0,  500,     'EUR', NULL, NULL,        NULL,                NULL,  NULL,  NULL, '2025-03-05 10:00:00.000000', '2025-03-05 10:00:00.000000'),
    (7,  5, 4,    'BUY',      '2025-03-06', 10, -981.2,  'EUR', NULL, NULL,        NULL,                NULL,  NULL,  NULL, '2025-03-06 10:00:00.000000', '2025-03-06 10:00:00.000000'),
    (8,  2, 4,    'INTEREST', '2025-06-30', 0,  13.5,    'EUR', NULL, NULL,        NULL,                NULL,  NULL,  3,    '2025-07-01 10:00:00.000000', '2025-07-01 10:00:00.000000'),
    (9,  2, NULL, 'FEE',      '2025-07-01', 0,  -2,      'EUR', NULL, NULL,        NULL,                NULL,  NULL,  NULL, '2025-07-01 10:00:00.000000', '2025-07-01 10:00:00.000000'),
    (10, 1, 4,    'BUY',      '2025-07-15', 5,  -490.6,  'EUR', NULL, NULL,        NULL,                NULL,  NULL,  NULL, '2025-07-15 10:00:00.000000', '2025-07-15 10:00:00.000000');

INSERT INTO fx_rates (id, date, base, quote, rate, source, fetched_at) VALUES
    (1, '2025-01-02', 'EUR', 'USD', 1.0321, 'ECB', '2025-01-02 17:00:00.000000'),
    (2, '2025-01-03', 'EUR', 'USD', 1.0299, 'ECB', '2025-01-03 17:00:00.000000'),
    (3, '2025-01-02', 'CHF', 'EUR', 1.0712, 'SNB', '2025-01-02 17:00:00.000000');

INSERT INTO fx_conversion_routes (id, base, quote, priority, chain_steps, created_at, updated_at) VALUES
    (1, 'EUR', 'USD', 1, '[{"base": "EUR", "quote": "USD", "provider": "ECB"}]', '2025-01-02 09:00:00.000000', '2025-01-02 09:00:00.000000'),
    (2, 'CHF', 'USD', 1, '[{"base": "CHF", "quote": "EUR", "provider": "SNB"}, {"base": "EUR", "quote": "USD", "provider": "ECB"}]', '2025-01-02 09:00:00.000000', '2025-01-02 09:00:00.000000'),
    (3, 'GBP', 'USD', 2, '[{"base": "GBP", "quote": "USD", "provider": "BOE"}]', '2025-01-02 09:00:00.000000', '2025-01-02 09:00:00.000000');

-- The gaps. A broker goes with its transactions first; its accesses go with it.
DELETE FROM transactions WHERE id IN (6, 7, 9);
DELETE FROM brokers WHERE id IN (3, 5);
-- An asset takes its assignment, prices and events with it.
DELETE FROM assets WHERE id = 2;
DELETE FROM asset_events WHERE id = 4;
-- A user takes settings and accesses with it; global_settings keeps the row, updated_by_user_id becomes NULL.
DELETE FROM users WHERE id = 2;
DELETE FROM fx_conversion_routes WHERE id = 2;
DELETE FROM fx_rates WHERE id = 2;

COMMIT;
"""

# A migration after 004, simulated: a census table gains a column with a default and an index on it, and rows use it.
LATER_MIGRATION = """
PRAGMA foreign_keys = ON;
BEGIN;
ALTER TABLE brokers ADD COLUMN external_ref VARCHAR(40) NOT NULL DEFAULT 'unset';
CREATE INDEX ix_brokers_external_ref ON brokers (external_ref);
UPDATE brokers SET external_ref = 'ext-alpha' WHERE id = 1;
INSERT INTO brokers (name, external_ref, allow_cash_overdraft, allow_asset_shorting, is_active, created_at, updated_at)
    VALUES ('Broker Future', 'ext-future', 0, 0, 1, '2026-11-02 09:00:00.000000', '2026-11-02 09:00:00.000000');
INSERT INTO broker_user_access (user_id, broker_id, role, share_percentage, created_at, updated_at)
    VALUES (1, last_insert_rowid(), 'OWNER', 1, '2026-11-02 09:00:00.000000', '2026-11-02 09:00:00.000000');
COMMIT;
"""


@dataclass(frozen=True)
class Run:
    """One observed call of ``run_post_migration_fixes``: its report, and the world just before and just after it."""

    db: Path
    report: PostMigrationReport
    master_before: Master
    master_after: Master
    rows_before: Rows
    rows_after: Rows
    digest_before: str
    digest_after: str
    backups_after: list[str]
    tree_before: Tree
    tree_after: Tree
    started: datetime
    finished: datetime


# =============================================================================
# HELPERS — files and folders
# =============================================================================


def _plant(path: Path, content: bytes = CSV_BYTES) -> Path:
    """Write ``content`` at ``path``, creating its folders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _plant_report(folder: Path, n: int) -> None:
    """One stored report as the BRIM storage writes it: ``<uuid>.csv`` and its ``<uuid>.json`` sidecar."""
    file_id = str(uuid.UUID(int=n))
    _plant(folder / f"{file_id}.csv")
    _plant(folder / f"{file_id}.json", json.dumps({"file_id": file_id}).encode())


def _plant_broker_reports(data_dir: Path) -> None:
    """``broker_reports`` as uploads leave it beside the 1.1 database, whose live brokers are 1, 2 and 4."""
    reports = data_dir / "broker_reports"
    _plant_report(reports / "uploaded" / "broker_1", 1)
    _plant_report(reports / "parsed" / "broker_2", 2)
    (reports / "failed" / "broker_4").mkdir(parents=True)  # every upload creates its folder under all three statuses
    _plant_report(reports / "uploaded" / "broker_3", 3)  # broker 3 was deleted: a gap
    (reports / "parsed" / "broker_3").mkdir(parents=True)
    _plant_report(reports / "failed" / "broker_5", 5)  # broker 5, the highest id, was deleted
    _plant(reports / "failed" / "broker_5" / "pages" / "page-2.csv")
    _plant_report(reports / "parsed" / "broker_42", 42)  # a broker of a database since recreated
    _plant_report(reports / "uploaded" / "broker_none", 6)
    _plant_report(reports / "uploaded" / "broker_abc", 7)
    _plant_report(reports / "uploaded" / "broker_3_old", 8)  # not an integer: not broker 3's
    _plant_report(reports / "uploaded", 9)  # an upload with no broker sits at the folder root
    _plant(reports / ".locks" / "broker_5.lock", b"")


def _tree(root: Path) -> Tree:
    """Every entry below ``root`` by relative path: ``("dir", None)``, ``("file", bytes)`` or ``("link", target)``."""
    tree: Tree = {}
    if not root.exists():
        return tree
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            tree[relative] = ("link", str(path.readlink()))
        elif path.is_dir():
            tree[relative] = ("dir", None)
        else:
            tree[relative] = ("file", path.read_bytes())
    return tree


def _under(relative: str, folders: tuple[str, ...]) -> bool:
    """Whether ``relative`` is one of ``folders`` or lies below one."""
    return any(relative == folder or relative.startswith(f"{folder}/") for folder in folders)


def _quarantined(tree: Tree) -> list[str]:
    """The entries of ``tree`` that are, or lie below, a ``.quarantine-…`` folder."""
    return sorted(relative for relative in tree if any(part.startswith(".quarantine-") for part in relative.split("/")))


def _listed(report: PostMigrationReport) -> list[str]:
    """``orphan_broker_dirs`` as sorted POSIX strings, whether the report holds strings or paths."""
    return sorted(Path(folder).as_posix() for folder in report.orphan_broker_dirs)


# =============================================================================
# HELPERS — the configured data dir and the child processes
# =============================================================================


@contextmanager
def _configured_sandbox(sandbox: Path) -> Iterator[Path]:
    """Point the configured test data dir (what ``get_data_dir()`` returns) at ``sandbox``, with a canary in it.

    The code under test always gets its database and data dir explicitly. This makes sure that an
    implementation reaching for the configuration anyway, and every child process, can only ever meet
    a temporary folder — never the lane's data — and the canary says whether it was touched.
    """
    canary = _plant(sandbox / CANARY_FILE, CANARY)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("LIBREFOLIO_TEST_MODE", "1")
        patch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(sandbox))
        yield sandbox
    assert canary.is_file() and canary.read_bytes() == CANARY, f"safety: a run touched the configured data dir {sandbox}, which it was never given"


def _child_env() -> dict[str, str]:
    """This process's environment for a child process: only ever inside a configured sandbox, canary and all."""
    env = dict(os.environ)
    sandbox = Path(env.get("LIBREFOLIO_TEST_DATA_DIR") or "/nonexistent")
    assert env.get("LIBREFOLIO_TEST_MODE") == "1" and (sandbox / CANARY_FILE).is_file(), "safety: a child process starts only with the configured data dir pointed at a sandbox"
    return env


def _alembic_upgrade_head(db: Path) -> None:
    """``alembic upgrade head`` on ``db`` in a child process — always with ``-x sqlalchemy.url=``: without it ``env.py`` migrates the configured database."""
    assert db.is_absolute(), db
    db.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "-x", f"sqlalchemy.url=sqlite:///{db}", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT,
        check=False,
    )
    assert completed.returncode == 0, f"setup: alembic upgrade head failed on {db}\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}"


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    """``python -m backend.app.db.post_migration`` with ``args``, in a child process."""
    return subprocess.run(
        [sys.executable, "-m", "backend.app.db.post_migration", *args],
        cwd=PROJECT_ROOT,
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT,
        check=False,
    )


def _output(completed: subprocess.CompletedProcess[str]) -> str:
    """What a child process said, for an assertion message."""
    return f"exit {completed.returncode}\n--- stdout\n{completed.stdout[-3000:]}\n--- stderr\n{completed.stderr[-3000:]}"


# =============================================================================
# HELPERS — databases
# =============================================================================

AUTOINCREMENT_WORD = re.compile(r"\bAUTOINCREMENT\b", re.IGNORECASE)
AUTOINCREMENT_CLAUSE = re.compile(r"\s+AUTOINCREMENT\b", re.IGNORECASE)
CREATE_TABLE = re.compile(r'\s*CREATE\s+TABLE\s+(?:"(?P<double>[^"]+)"|`(?P<back>[^`]+)`|\[(?P<square>[^\]]+)\]|(?P<bare>[^\s(]+))\s*', re.IGNORECASE)
COLUMN_KEY = re.compile(r"\bid(\s+)INTEGER\s+PRIMARY\s+KEY\b", re.IGNORECASE)


def _connect(db: Path) -> closing[sqlite3.Connection]:
    """A connection to an existing database: ``sqlite3.connect`` would silently create a missing one."""
    assert db.is_file(), f"{db} does not exist"
    return closing(sqlite3.connect(db))


def _install_v110(db: Path) -> Path:
    """A 1.1 install: the real v1.1.0 schema, populated with foreign keys on, gaps included."""
    db.parent.mkdir(parents=True, exist_ok=True)
    assert not db.exists(), f"setup: {db} already exists"
    with closing(sqlite3.connect(db)) as conn:
        conn.executescript(V110_SCHEMA.read_text(encoding="utf-8"))
        conn.executescript(V110_ROWS)
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == [], "setup: the 1.1 rows must be consistent"
    return db


def _build_v110_db(db: Path) -> Path:
    """A 1.1 install upgraded to head by the real migrations: what a 1.2 server finds at startup."""
    _install_v110(db)
    _alembic_upgrade_head(db)
    assert _autoincrement_tables(_master(db)) == set(), "setup: a 1.1 install upgraded to head has no AUTOINCREMENT"
    assert _ids(db) == V110_IDS, "setup: the census ids, gaps included"
    return db


def _master(db: Path) -> Master:
    """``sqlite_master`` but the root pages: type, name, table and SQL of every object."""
    with _connect(db) as conn:
        return conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name").fetchall()


def _rows(db: Path) -> Rows:
    """Every row of every table, ``sqlite_sequence`` included, with the table's columns: ``{table: (columns, rows)}``."""
    with _connect(db) as conn:
        tables = [name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        rows: Rows = {}
        for table in tables:
            cursor = conn.execute(f'SELECT * FROM "{table}"')
            rows[table] = ([column[0] for column in cursor.description], sorted(cursor.fetchall(), key=repr))
        return rows


def _data_rows(rows: Rows) -> Rows:
    """``rows`` without SQLite's own tables."""
    return {table: content for table, content in rows.items() if not table.startswith("sqlite_")}


def _ids(db: Path) -> dict[str, list[int]]:
    with _connect(db) as conn:
        return {table: [row_id for (row_id,) in conn.execute(f'SELECT id FROM "{table}" ORDER BY id')] for table in sorted(CENSUS)}


def _highest_ids(db: Path) -> dict[str, int]:
    with _connect(db) as conn:
        return {table: conn.execute(f'SELECT max(id) FROM "{table}"').fetchone()[0] for table in sorted(CENSUS)}


def _sequence(db: Path) -> dict[str, int]:
    """``sqlite_sequence`` as ``{table: seq}``; empty when it does not exist, i.e. no table has AUTOINCREMENT."""
    with _connect(db) as conn:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'").fetchone() is None:
            return {}
        return dict(conn.execute("SELECT name, seq FROM sqlite_sequence").fetchall())


def _foreign_key_violations(db: Path) -> list[tuple[Any, ...]]:
    with _connect(db) as conn:
        return conn.execute("PRAGMA foreign_key_check").fetchall()


def _settle(db: Path) -> None:
    """Fold any WAL content into the database file, so that the file's bytes are the whole database."""
    with _connect(db) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def _digest(db: Path) -> str:
    return hashlib.sha256(db.read_bytes()).hexdigest()


def _backups(db: Path) -> list[str]:
    """The backup files beside ``db``: ``<db name>.pre-…``, or anything ending in ``.bak``."""
    return sorted(path.name for path in db.parent.iterdir() if path.name.startswith(f"{db.name}.pre-") or path.name.endswith(".bak"))


def _autoincrement_tables(master: Master) -> set[str]:
    return {name for kind, name, _table, sql in master if kind == "table" and sql and AUTOINCREMENT_WORD.search(sql)}


def _without_autoincrement(sql: str) -> str:
    """A ``CREATE TABLE`` statement without its AUTOINCREMENT, and with its table name unquoted.

    SQLite writes a renamed table's name quoted (``CREATE TABLE "users"``), so the rebuild the plan
    prescribes — create ``<t>__autoinc``, copy, drop ``<t>``, rename — respells the name and nothing
    else. That spelling and AUTOINCREMENT are the only differences forgiven: everything after the name
    must match to the character.
    """
    header = CREATE_TABLE.match(sql)
    assert header, f"not a CREATE TABLE statement: {sql[:80]!r}"
    name = next(group for group in header.group("double", "back", "square", "bare") if group)
    return f"CREATE TABLE {name} {AUTOINCREMENT_CLAUSE.sub('', sql[header.end() :])}"


def _schema_but_autoincrement(master: Master) -> Master:
    """``sqlite_master`` without ``sqlite_sequence``, the census tables' DDL taken through ``_without_autoincrement``."""
    return [(kind, name, table, _without_autoincrement(sql) if kind == "table" and name in CENSUS and sql else sql) for kind, name, table, sql in master if name != "sqlite_sequence"]


def _indexes(master: Master) -> Master:
    return [entry for entry in master if entry[0] == "index"]


def _give_a_table_level_primary_key(db: Path, table: str) -> None:
    """Rebuild ``table`` declaring its key at table level — ``id INTEGER NOT NULL, …, PRIMARY KEY (id)`` — with its rows and indexes.

    The same table: only the form of the declaration changes, to one the fix must refuse rather than
    guess at (plan §2.3). ``fx_conversion_routes`` comes after users, brokers, assets and transactions
    in the census, so a fix converting table by table has rebuilt those when it meets it.
    """
    with _connect(db) as conn:
        (sql,) = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
        indexes = [index_sql for (index_sql,) in conn.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND tbl_name = ? AND sql IS NOT NULL", (table,))]
        assert len(COLUMN_KEY.findall(sql)) == 1, f"setup: {table} no longer declares id INTEGER PRIMARY KEY"
        declared = COLUMN_KEY.sub(r"id\1INTEGER NOT NULL", sql)
        end = declared.rindex(")")
        declared = f"{declared[:end].rstrip()},\n    PRIMARY KEY (id)\n{declared[end:]}"
        renamed, count = re.subn(rf"^(\s*CREATE\s+TABLE\s+){table}\b", rf"\g<1>{table}__pk", declared, count=1)
        assert count == 1, f"setup: unexpected header {sql[:60]!r}"
        conn.executescript(f"BEGIN; {renamed}; INSERT INTO {table}__pk SELECT * FROM {table}; DROP TABLE {table}; ALTER TABLE {table}__pk RENAME TO {table}; {'; '.join(indexes)}; COMMIT;")
        (rebuilt,) = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    assert "PRIMARY KEY (id)" in rebuilt and not COLUMN_KEY.search(rebuilt), f"setup: {table} was not rebuilt with a table-level key"


def _delete_highest_and_insert_it_again(conn: sqlite3.Connection, table: str) -> tuple[int, int]:
    """Delete the row with the highest id of ``table``, insert its values again without the id: ``(deleted id, new id)``."""
    cursor = conn.execute(f'SELECT * FROM "{table}" ORDER BY id DESC LIMIT 1')
    row = dict(zip([column[0] for column in cursor.description], cursor.fetchone(), strict=True))
    deleted = row.pop("id")
    conn.execute(f'DELETE FROM "{table}" WHERE id = ?', (deleted,))
    names = ", ".join(f'"{column}"' for column in row)
    marks = ", ".join("?" for _ in row)
    new = conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({marks})', tuple(row.values())).lastrowid
    conn.commit()
    return deleted, new


def _columns(db: Path, table: str) -> list[tuple[Any, ...]]:
    """``PRAGMA table_xinfo``: every column with its position, type, NOT NULL, default and key."""
    with _connect(db) as conn:
        return conn.execute(f'PRAGMA table_xinfo("{table}")').fetchall()


def _index(db: Path, name: str) -> Optional[tuple[str, str]]:
    """The table and the SQL of index ``name``, or ``None``."""
    with _connect(db) as conn:
        return conn.execute("SELECT tbl_name, sql FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)).fetchone()


def _external_refs(db: Path) -> dict[int, str]:
    with _connect(db) as conn:
        return dict(conn.execute("SELECT id, external_ref FROM brokers").fetchall())


def _observe_run(db: Path, data_dir: Optional[Path] = None, *, dry_run: bool = False) -> Run:
    """Call ``run_post_migration_fixes`` once; record the database, the backups and ``broker_reports`` around the call."""
    reports = data_dir / "broker_reports" if data_dir is not None else None
    master_before, rows_before = _master(db), _rows(db)
    tree_before = _tree(reports) if reports is not None else {}
    _settle(db)
    digest_before = _digest(db)
    started = datetime.now(UTC)
    report = post_migration.run_post_migration_fixes(db, data_dir, dry_run=dry_run)
    finished = datetime.now(UTC)
    digest_after = _digest(db)  # first, before any connection of ours
    return Run(
        db=db,
        report=report,
        master_before=master_before,
        master_after=_master(db),
        rows_before=rows_before,
        rows_after=_rows(db),
        digest_before=digest_before,
        digest_after=digest_after,
        backups_after=_backups(db),
        tree_before=tree_before,
        tree_after=_tree(reports) if reports is not None else {},
        started=started,
        finished=finished,
    )


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def configured_sandbox(tmp_path: Path) -> Iterator[Path]:
    """Every test runs with the configured data dir pointed at a sandbox of its own (see ``_configured_sandbox``)."""
    with _configured_sandbox(tmp_path / "configured-lane") as sandbox:
        yield sandbox


@pytest.fixture(scope="module")
def converted(tmp_path_factory: pytest.TempPathFactory) -> Run:
    """A populated 1.1 database upgraded to head, then one run without a data dir. Read-only for the tests."""
    root = tmp_path_factory.mktemp("converted")
    with _configured_sandbox(root / "configured-lane"):
        return _observe_run(_build_v110_db(root / "sqlite" / "app.db"))


@pytest.fixture(scope="module")
def refused(tmp_path_factory: pytest.TempPathFactory) -> Run:
    """As ``converted``, but ``fx_conversion_routes`` declares a table-level key: the run must refuse half way."""
    root = tmp_path_factory.mktemp("refused")
    with _configured_sandbox(root / "configured-lane"):
        db = _build_v110_db(root / "sqlite" / "app.db")
        _give_a_table_level_primary_key(db, "fx_conversion_routes")
        return _observe_run(db)


@pytest.fixture(scope="module")
def orphans_converted(tmp_path_factory: pytest.TempPathFactory) -> Run:
    """A populated 1.1 database at head inside its data dir, beside orphan and live broker folders, then one run."""
    root = tmp_path_factory.mktemp("orphans-converted")
    with _configured_sandbox(root / "configured-lane"):
        data_dir = root / "data"
        db = _build_v110_db(data_dir / "sqlite" / "app.db")
        _plant_broker_reports(data_dir)
        return _observe_run(db, data_dir)


@pytest.fixture(scope="module")
def previewed(tmp_path_factory: pytest.TempPathFactory) -> Run:
    """As ``orphans_converted``, with ``dry_run=True``."""
    root = tmp_path_factory.mktemp("dry-run")
    with _configured_sandbox(root / "configured-lane"):
        data_dir = root / "data"
        db = _build_v110_db(data_dir / "sqlite" / "app.db")
        _plant_broker_reports(data_dir)
        return _observe_run(db, data_dir, dry_run=True)


# =============================================================================
# 1. A NEW DATABASE NEEDS NOTHING
# =============================================================================


def test_a_new_database_needs_nothing_and_is_left_as_it_was(tmp_path: Path) -> None:
    """Contract 1: on a fresh ``upgrade head`` the fix detects nothing — ``clean`` — and writes nothing.

    The database keeps every ``sqlite_master`` entry and every row, no backup appears beside it, and
    no folder is renamed: not even an orphan ``broker_7``, since a new database has no broker and
    there is nothing to convert.
    """
    data_dir = tmp_path / "data"
    db = data_dir / "sqlite" / "app.db"
    _alembic_upgrade_head(db)
    _plant_report(data_dir / "broker_reports" / "uploaded" / "broker_7", 7)

    run = _observe_run(db, data_dir)

    assert run.report.outcomes.get(FIX) == "clean"
    assert run.master_after == run.master_before
    assert run.rows_after == run.rows_before
    assert run.report.backup_path is None
    assert run.backups_after == []
    assert run.tree_after == run.tree_before


# =============================================================================
# 2. A 1.1 DATABASE AT HEAD IS CONVERTED
# =============================================================================


def test_the_conversion_reports_applied(converted: Run) -> None:
    """Contract 2: the run on a 1.1 database at head reports ``applied`` for ``autoincrement``, the integrity check passed, no error."""
    assert converted.report.outcomes.get(FIX) == "applied"
    assert converted.report.integrity_ok is True
    assert converted.report.errors == []


def test_the_conversion_gives_autoincrement_to_exactly_the_census_tables(converted: Run) -> None:
    """Contract 2: afterwards AUTOINCREMENT is on the six census tables and on no other — the onboarding tables, the series and the rest keep their key as it was."""
    found = _autoincrement_tables(converted.master_after)

    assert found == CENSUS, f"missing: {sorted(CENSUS - found)}, unexpected: {sorted(found - CENSUS)}"


def test_the_conversion_keeps_every_row_with_its_id(converted: Run) -> None:
    """Contract 2 (D4): every table, census or not, has the same columns and the same rows — ids included — as before.

    The database has gaps (``V110_IDS``) and rows pointing into the census tables, so a copy that
    renumbered, dropped or cascaded anything would show here.
    """
    assert _autoincrement_tables(converted.master_after) == CENSUS, NOT_CONVERTED
    assert _data_rows(converted.rows_after) == _data_rows(converted.rows_before)


def test_the_conversion_keeps_every_index(converted: Run) -> None:
    """Contract 2: every index — name, table and SQL, SQLite's own ``sqlite_autoindex_*`` included — is as it was."""
    assert _autoincrement_tables(converted.master_after) == CENSUS, NOT_CONVERTED
    assert _indexes(converted.master_after) == _indexes(converted.master_before)


def test_the_conversion_changes_nothing_in_the_schema_but_autoincrement(converted: Run) -> None:
    """Contract 2: each census table's DDL is the one before plus AUTOINCREMENT; every other ``sqlite_master`` entry is identical.

    Forgiven: the quoting SQLite gives a renamed table's name (see ``_without_autoincrement``), and the
    ``sqlite_sequence`` table AUTOINCREMENT brings. Nothing else may appear, change or disappear — no
    leftover ``__autoinc`` table, no column of the 1.1 DDL lost (``VARCHAR(14)`` stays 14).
    """
    assert _autoincrement_tables(converted.master_after) == CENSUS, NOT_CONVERTED
    assert _schema_but_autoincrement(converted.master_after) == _schema_but_autoincrement(converted.master_before)


def test_the_conversion_leaves_no_foreign_key_violation(converted: Run) -> None:
    """Contract 2: ``PRAGMA foreign_key_check`` is empty — every reference into a rebuilt table still finds its row."""
    assert _autoincrement_tables(converted.master_after) == CENSUS, NOT_CONVERTED
    assert _foreign_key_violations(converted.db) == []


def test_the_conversion_starts_each_census_sequence_at_the_highest_id(converted: Run) -> None:
    """Contract 2: ``sqlite_sequence`` holds one row per census table, at that table's highest id.

    For brokers that is 4: broker 5 was deleted before the conversion, and its folders are the job of
    contract 7.
    """
    assert _sequence(converted.db) == _highest_ids(converted.db)


def test_after_the_conversion_a_deleted_highest_id_is_never_given_again(tmp_path: Path) -> None:
    """Contract 2: once converted, the highest row of each census table, deleted and inserted again, gets a higher id.

    Without AUTOINCREMENT SQLite hands out ``max(id) + 1``: the deleted id, the very reuse the plan
    closes. Each highest row is deleted with foreign keys on, as the app would — nothing points at
    it — and inserted again with the same values and no id.
    """
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")
    post_migration.run_post_migration_fixes(db, None)

    reused: dict[str, tuple[int, int]] = {}
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        for table in sorted(CENSUS):
            deleted, new = _delete_highest_and_insert_it_again(conn, table)
            if new <= deleted:
                reused[table] = (deleted, new)

    assert reused == {}, f"(deleted id, new id) of the tables that gave an id again: {reused}"


def test_the_conversion_deletes_its_backup(converted: Run) -> None:
    """Contract 2 (D2): after a verified conversion no backup is left beside the database, and the report keeps none."""
    assert converted.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    assert converted.report.backup_path is None
    assert converted.backups_after == []


# =============================================================================
# 3. A SCHEMA FROM A LATER MIGRATION (D1, the developer's explicit request)
# =============================================================================


def test_a_schema_from_a_later_migration_is_converted_from_the_ddl_in_force(tmp_path: Path) -> None:
    """Contract 3: the fix rebuilds a census table from the DDL it finds, at whatever head — not from a DDL frozen at 004.

    A later migration is simulated on the database at head: ``brokers`` gains ``external_ref
    VARCHAR(40) NOT NULL DEFAULT 'unset'`` and an index on it; broker 1 gets a value, a new broker is
    created with one. Afterwards ``brokers`` has AUTOINCREMENT, and the column keeps its declaration
    and place, each broker its value, the index its definition.
    """
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")
    with _connect(db) as conn:
        conn.executescript(LATER_MIGRATION)
    columns, index, values = _columns(db, "brokers"), _index(db, "ix_brokers_external_ref"), _external_refs(db)
    assert values == {1: "ext-alpha", 2: "unset", 4: "unset", 5: "ext-future"}, "setup: the later migration ran (broker 5's id given again: no AUTOINCREMENT yet)"

    post_migration.run_post_migration_fixes(db, None)

    assert "brokers" in _autoincrement_tables(_master(db)), NOT_CONVERTED
    assert _columns(db, "brokers") == columns
    assert _external_refs(db) == values
    assert _index(db, "ix_brokers_external_ref") == index


# =============================================================================
# 4. A SECOND RUN
# =============================================================================


def test_a_second_run_finds_nothing_to_do_and_writes_nothing(tmp_path: Path) -> None:
    """Contract 4: run again on a converted database, the fix reports ``clean``, makes no backup and leaves every entry and row as it was."""
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")
    first = post_migration.run_post_migration_fixes(db, None)
    assert first.outcomes.get(FIX) == "applied", "precondition: the first run must convert, or the second proves nothing"

    second = _observe_run(db)

    assert second.report.outcomes.get(FIX) == "clean"
    assert second.report.backup_path is None
    assert second.backups_after == []
    assert second.master_after == second.master_before
    assert second.rows_after == second.rows_before


# =============================================================================
# 5. A CONVERSION REFUSED HALF WAY
# =============================================================================


def test_a_refused_conversion_reports_failed_and_why(refused: Run) -> None:
    """Contract 5: a census table in a form the fix does not recognise stops it — outcome ``failed``, with at least one error saying why."""
    assert refused.report.outcomes.get(FIX) == "failed"
    assert refused.report.errors, "a failed fix must say why"


def test_a_refused_conversion_leaves_the_whole_database_as_it_was(refused: Run) -> None:
    """Contract 5: after the refusal every ``sqlite_master`` entry and every row is as before — no table converted, no ``sqlite_sequence``.

    The tables the fix may have rebuilt before meeting ``fx_conversion_routes`` are rolled back with
    the rest: one transaction.
    """
    assert refused.report.outcomes.get(FIX) == "failed", NOT_FAILED
    assert refused.master_after == refused.master_before
    assert refused.rows_after == refused.rows_before


def test_a_refused_conversion_keeps_its_backup_beside_the_database_and_reports_it(refused: Run) -> None:
    """Contract 5 (D2): the backup stays — one file beside the database, named in ``backup_path`` — and holds the database as it was before the run."""
    assert refused.report.backup_path is not None, "a failed fix must keep its backup and report its path"
    backup = Path(refused.report.backup_path)
    assert backup.is_file(), backup
    assert backup.parent.resolve() == refused.db.parent.resolve()
    assert refused.backups_after == [backup.name]
    assert _master(backup) == refused.master_before
    assert _rows(backup) == refused.rows_before


def test_the_kept_backup_is_named_after_the_database_the_fix_and_the_utc_time(refused: Run) -> None:
    """Contract 5: the backup is ``<db name>.pre-autoincrement-<yyyymmddThhmmss>.bak``, the stamp in UTC, taken during the run.

    The stamp must fall between the run's start and end read in UTC: a local-time stamp is off by
    the UTC offset. A trailing ``Z`` is accepted.
    """
    assert refused.report.backup_path is not None, "a failed fix must keep its backup and report its path"
    name = Path(refused.report.backup_path).name
    match = re.fullmatch(rf"{re.escape(refused.db.name)}\.pre-{FIX}-(\d{{8}}T\d{{6}})Z?\.bak", name)
    assert match, f"{name!r} is not <db name>.pre-{FIX}-<UTC yyyymmddThhmmss>.bak"
    stamp = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=UTC)
    assert refused.started.replace(microsecond=0) <= stamp <= refused.finished, f"{stamp:%Y-%m-%d %H:%M:%S} UTC is not within the run ({refused.started:%H:%M:%S}–{refused.finished:%H:%M:%S} UTC)"


def test_the_startup_hook_survives_a_run_that_raises_and_returns_none(configured_sandbox: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 5: ``run_post_migration_fixes_at_startup()`` swallows an exception of the run and returns ``None``: startup never blocks.

    ``run_post_migration_fixes`` is replaced, in ``backend.app.services.platform.database_bootstrap`` where the hook
    reaches it, by one that raises. Barrier first: the hook did call it — otherwise "it did not raise" proves nothing.
    """
    _install_v110(configured_sandbox / "sqlite" / "app.db")
    database_bootstrap = importlib.import_module("backend.app.services.platform.database_bootstrap")
    calls: list[Any] = []

    def raising_run(db_path: Path, data_dir: Optional[Path] = None, *, dry_run: bool = False) -> PostMigrationReport:
        calls.append(db_path)
        raise RuntimeError("provoked: the post-migration run itself failed")

    monkeypatch.setattr(database_bootstrap, "run_post_migration_fixes", raising_run)

    try:
        result = database_bootstrap.run_post_migration_fixes_at_startup()
    except Exception as exc:
        pytest.fail(f"the startup hook raised {exc!r}: startup must never block")

    assert calls, "barrier: the hook never called run_post_migration_fixes, so 'it does not raise' proves nothing"
    assert result is None


# =============================================================================
# 6. A DATABASE FAILING THE INTEGRITY CHECK
# =============================================================================


def test_a_database_failing_the_integrity_check_is_not_touched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 6: when ``_integrity_ok(conn)`` says False, nothing is fixed, backed up or renamed, and the report says so.

    ``integrity_ok`` is False and the outcome is not ``applied``; database, backups and broker folders
    are as they were. Barrier first: the run did ask ``_integrity_ok`` — the module-level function the
    contract names — or the False below was never seen.
    """
    data_dir = tmp_path / "data"
    db = _build_v110_db(data_dir / "sqlite" / "app.db")
    _plant_broker_reports(data_dir)
    consulted: list[bool] = []

    def damaged(conn: sqlite3.Connection) -> bool:
        consulted.append(True)
        return False

    monkeypatch.setattr(post_migration, "_integrity_ok", damaged, raising=False)

    run = _observe_run(db, data_dir)

    assert consulted, "barrier: the run never called post_migration._integrity_ok(conn)"
    assert run.report.integrity_ok is False
    assert run.report.outcomes.get(FIX) != "applied"
    assert run.master_after == run.master_before
    assert run.rows_after == run.rows_before
    assert run.report.backup_path is None
    assert run.backups_after == []
    assert run.tree_after == run.tree_before


# =============================================================================
# 7. ORPHAN BROKER FOLDERS (D4)
# =============================================================================


def test_orphan_broker_folders_are_deleted_with_their_files_after_a_verified_fix(orphans_converted: Run) -> None:
    """Contract 7: after a verified conversion the folders of brokers 3, 5 and 42 — absent from ``brokers`` — are gone, files and subfolders with them.

    Their quarantine names (``.quarantine-autoincrement-<UTC>-broker_<n>``) are gone too.
    """
    assert orphans_converted.report.outcomes.get(FIX) == "applied", NOT_APPLIED
    assert [relative for relative in orphans_converted.tree_after if _under(relative, DEAD_BROKER_DIRS)] == []
    assert _quarantined(orphans_converted.tree_after) == []


def test_every_other_entry_of_broker_reports_survives_a_verified_fix(orphans_converted: Run) -> None:
    """Contract 7: live brokers' folders (1, 2, 4), ``broker_none``, ``broker_abc``, ``broker_3_old``, root-level reports and ``.locks`` stay, byte for byte.

    ``broker_reports`` afterwards is exactly the tree before minus the four orphan folders: nothing
    else removed, renamed or added. Barrier first: the orphans are gone.
    """
    assert not any(_under(relative, DEAD_BROKER_DIRS) for relative in orphans_converted.tree_after), NO_CLEANUP
    assert orphans_converted.tree_after == {relative: entry for relative, entry in orphans_converted.tree_before.items() if not _under(relative, DEAD_BROKER_DIRS)}


def test_a_verified_fix_reports_the_orphan_broker_folders_it_found(orphans_converted: Run) -> None:
    """Contract 7: ``orphan_broker_dirs`` lists exactly the four orphan folders, relative to the data dir."""
    assert _listed(orphans_converted.report) == ORPHAN_BROKER_DIRS


def test_orphan_broker_folders_get_their_names_and_files_back_when_the_fix_fails(tmp_path: Path) -> None:
    """Contract 7 (D4): when the conversion is refused half way, every orphan folder is back under its own name with its files.

    ``broker_reports`` is exactly as before: nothing deleted, nothing left in quarantine. Barrier
    first: the fix did fail.
    """
    data_dir = tmp_path / "data"
    db = _build_v110_db(data_dir / "sqlite" / "app.db")
    _plant_broker_reports(data_dir)
    _give_a_table_level_primary_key(db, "fx_conversion_routes")

    run = _observe_run(db, data_dir)

    assert run.report.outcomes.get(FIX) == "failed", NOT_FAILED
    assert run.tree_after == run.tree_before


def test_a_dry_run_lists_the_orphan_broker_folders(previewed: Run) -> None:
    """Contract 7 (D4, D5): a dry run lists the four orphan folders in ``orphan_broker_dirs``, relative to the data dir; contract 8 shows it touches none."""
    assert _listed(previewed.report) == ORPHAN_BROKER_DIRS


@pytest.mark.parametrize("where", ["sibling-folder", "name-prefix-sibling"])
def test_no_broker_folder_is_touched_when_the_database_is_outside_the_data_dir(tmp_path: Path, where: str) -> None:
    """Contract 7: with the database outside the data dir the folders are not its own — none is touched — and the fix goes on with the database.

    ``name-prefix-sibling`` (``data-old/sqlite/app.db`` beside ``data``) is outside, though a string
    prefix comparison says inside. Barrier first: the conversion was applied.
    """
    data_dir = tmp_path / "data"
    _plant_broker_reports(data_dir)
    db = {"sibling-folder": tmp_path / "elsewhere" / "app.db", "name-prefix-sibling": tmp_path / "data-old" / "sqlite" / "app.db"}[where]
    _build_v110_db(db)

    run = _observe_run(db, data_dir)

    assert run.report.outcomes.get(FIX) == "applied", "barrier: the fix must go on with the database"
    assert run.tree_after == run.tree_before


# =============================================================================
# 8. DRY RUN (D5)
# =============================================================================


def test_a_dry_run_reports_would_apply_and_writes_nothing(previewed: Run) -> None:
    """Contract 8: a dry run on a database that needs the conversion reports ``would_apply`` and writes nothing.

    The database file is byte-identical (WAL folded in before the run), no backup appears, no broker
    folder is renamed or removed.
    """
    assert previewed.report.outcomes.get(FIX) == "would_apply", NOT_DRY
    assert previewed.digest_after == previewed.digest_before, "the database file changed"
    assert previewed.report.backup_path is None
    assert previewed.backups_after == []
    assert previewed.tree_after == previewed.tree_before


# =============================================================================
# 9. THE OFFLINE SCRIPT
# =============================================================================


def test_the_offline_script_converts_and_exits_0(tmp_path: Path) -> None:
    """Contract 9: ``python -m backend.app.db.post_migration --db … --data-dir …`` converts a 1.1 database at head and exits 0."""
    data_dir = tmp_path / "data"
    db = _build_v110_db(data_dir / "sqlite" / "app.db")

    completed = _run_script("--db", str(db), "--data-dir", str(data_dir))

    assert completed.returncode == 0, _output(completed)
    assert _autoincrement_tables(_master(db)) == CENSUS, _output(completed)


def test_the_offline_script_dry_run_exits_0_and_writes_nothing(tmp_path: Path) -> None:
    """Contract 9 — guard: ``--dry-run`` exits 0 and leaves the database byte-identical, no backup, every broker folder in place.

    Green on the stub, which exits 0 and does nothing; it fails if the dry run writes or exits
    otherwise. That it detects is contract 8's business.
    """
    data_dir = tmp_path / "data"
    db = _build_v110_db(data_dir / "sqlite" / "app.db")
    _plant_broker_reports(data_dir)
    _settle(db)
    digest, tree = _digest(db), _tree(data_dir / "broker_reports")

    completed = _run_script("--db", str(db), "--data-dir", str(data_dir), "--dry-run")

    assert completed.returncode == 0, _output(completed)
    assert _digest(db) == digest, _output(completed)
    assert _backups(db) == []
    assert _tree(data_dir / "broker_reports") == tree


def test_the_offline_script_exits_1_when_a_fix_fails(tmp_path: Path) -> None:
    """Contract 9: on the database of contract 5 — a census table the fix refuses — the script exits 1."""
    data_dir = tmp_path / "data"
    db = _build_v110_db(data_dir / "sqlite" / "app.db")
    _give_a_table_level_primary_key(db, "fx_conversion_routes")

    completed = _run_script("--db", str(db), "--data-dir", str(data_dir))

    assert completed.returncode == 1, _output(completed)


# =============================================================================
# 10. THE STARTUP HOOK
# =============================================================================


def test_the_startup_hook_runs_the_fixes_on_the_configured_database_and_data_dir(configured_sandbox: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 10: ``run_post_migration_fixes_at_startup()`` calls ``run_post_migration_fixes`` once — configured database, configured data dir, not a dry run — and returns its report.

    The configuration is the sandbox (``LIBREFOLIO_TEST_MODE=1``, ``LIBREFOLIO_TEST_DATA_DIR``), whose
    ``sqlite/app.db`` is a 1.1 database needing the conversion; it is read when the hook runs, as
    ``ensure_database_exists`` reads it. ``run_post_migration_fixes`` is replaced in
    ``backend.app.services.platform.database_bootstrap``, where the hook reaches it, by a spy returning a report of its own.
    """
    db = _install_v110(configured_sandbox / "sqlite" / "app.db")
    database_bootstrap = importlib.import_module("backend.app.services.platform.database_bootstrap")
    report = PostMigrationReport(outcomes={FIX: "applied"})
    calls: list[tuple[Any, Any, bool]] = []

    def spy(db_path: Path, data_dir: Optional[Path] = None, *, dry_run: bool = False) -> PostMigrationReport:
        calls.append((db_path, data_dir, dry_run))
        return report

    monkeypatch.setattr(database_bootstrap, "run_post_migration_fixes", spy)

    result = database_bootstrap.run_post_migration_fixes_at_startup()

    assert len(calls) == 1, f"the hook must call run_post_migration_fixes once, it called it {len(calls)} times"
    db_path, data_dir, as_dry_run = calls[0]
    assert Path(db_path).resolve() == db.resolve()
    assert data_dir is not None and Path(data_dir).resolve() == configured_sandbox.resolve()
    assert as_dry_run is False
    assert result is report


# =============================================================================
# 11. THE LIFESPAN — beyond the brief: plan §2.3 ("nel lifespan, subito dopo ensure_database_exists()") and §7
# =============================================================================


def _quiet_the_rest_of_the_lifespan(monkeypatch: pytest.MonkeyPatch, app_lifespan: ModuleType, events: list[str]) -> None:
    """Everything else the lifespan starts or stops reduced to nothing, as the lifespan tests of ``test_market_calendar`` do.

    Two steps are recorded instead: the migrations (``ensure_database_exists``) and the first
    connection after them (``_initialize_global_settings``).
    """

    async def nothing(*_args: Any, **_kwargs: Any) -> None:
        return None

    async def catalog() -> SimpleNamespace:
        return SimpleNamespace(status=SimpleNamespace(built_in_count=0, host_count=0, warning_count=0))

    async def first_connection() -> None:
        events.append("first_connection")

    def prewarm() -> asyncio.Task[None]:
        return asyncio.get_running_loop().create_task(nothing())

    shutdown_event = asyncio.Event()

    async def scheduler(event: asyncio.Event) -> None:
        await event.wait()

    monkeypatch.setattr(app_lifespan, "validate_signal_runtime", lambda: SimpleNamespace(pandas_ta_classic_version="test", talib_version="test"))
    monkeypatch.setattr(app_lifespan.SignalPluginRegistry, "auto_discover", lambda: None)
    monkeypatch.setattr(app_lifespan.SignalPluginRegistry, "list_plugin_codes", lambda: [])
    monkeypatch.setattr(app_lifespan.ToolPluginRegistry, "get_snapshot", lambda: SimpleNamespace(definitions=[], failures=[]))
    monkeypatch.setattr(app_lifespan, "ensure_data_dirs", lambda: None)
    monkeypatch.setattr(app_lifespan, "initialize_risk_scenario_catalog", catalog)
    monkeypatch.setattr(app_lifespan, "seed_default_avatars", lambda: 0)
    monkeypatch.setattr(app_lifespan, "ensure_database_exists", lambda: events.append("migrations"))
    monkeypatch.setattr(app_lifespan, "_initialize_global_settings", first_connection)
    monkeypatch.setattr(app_lifespan, "_prewarm_provider_caches", nothing)
    monkeypatch.setattr(app_lifespan, "start_market_holiday_prewarm", prewarm)
    # W-B53: the BRIM parse pool's forkserver, started in the background by the cure; raising=False: absent before it
    monkeypatch.setattr(app_lifespan, "prewarm_brim_parse_pool", lambda: None, raising=False)
    monkeypatch.setattr(app_lifespan, "get_shutdown_event", lambda: shutdown_event)
    monkeypatch.setattr(app_lifespan, "scheduler_loop", scheduler)
    monkeypatch.setattr(app_lifespan, "shutdown_tool_executor", nothing)
    for registry in (app_lifespan.AssetProviderRegistry, app_lifespan.FXProviderRegistry, app_lifespan.BRIMProviderRegistry):
        monkeypatch.setattr(registry, "shutdown_all_providers", lambda: None)
    monkeypatch.setattr(app_lifespan, "shutdown_brim_parse_pool", lambda wait=False: None)
    monkeypatch.setattr(app_lifespan, "shutdown_quant_worker_pools", nothing)
    monkeypatch.setattr(app_lifespan, "shutdown_market_holidays", nothing)
    monkeypatch.setattr(app_lifespan, "close_all_caches", lambda: None)


@pytest.mark.asyncio
async def test_the_server_runs_the_fixes_right_after_the_migrations_and_starts_even_when_they_raise(configured_sandbox: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 11 (beyond the brief): the lifespan runs the fixes between the migrations and the first connection, and serves even when they raise.

    ``run_post_migration_fixes`` raises; the rest of the lifespan is reduced to nothing. The order
    must be migrations, fixes, first connection, serving. On the stub the lifespan never calls the
    hook, so the fixes never appear.
    """
    _install_v110(configured_sandbox / "sqlite" / "app.db")
    app_lifespan = importlib.import_module("backend.app.services.platform.app_lifespan")
    database_bootstrap = importlib.import_module("backend.app.services.platform.database_bootstrap")
    app = importlib.import_module("backend.app.main").app
    events: list[str] = []

    def raising_run(db_path: Path, data_dir: Optional[Path] = None, *, dry_run: bool = False) -> PostMigrationReport:
        events.append("post_migration_fixes")
        raise RuntimeError("provoked: the post-migration run itself failed")

    _quiet_the_rest_of_the_lifespan(monkeypatch, app_lifespan, events)
    monkeypatch.setattr(database_bootstrap, "run_post_migration_fixes", raising_run)

    async def serve() -> None:
        async with app_lifespan.lifespan(app):
            events.append("serving")

    try:
        await asyncio.wait_for(serve(), timeout=60)
    except Exception as exc:
        pytest.fail(f"the server did not start: the lifespan raised {exc!r}")

    assert events == ["migrations", "post_migration_fixes", "first_connection", "serving"]


# =============================================================================
# 12. CONCURRENT RUNS — several workers start together (review defect)
# =============================================================================

MARK = "@@post-migration-test@@"
MARK_TIMEOUT = 60

# Shared by the two children of the end-to-end test: say() prints a mark line the test waits for; the work is the
# offline script's own main(), and ``started`` is set just before it, after every import.
CHILD_PRELUDE = """
import importlib, sys

MARK = "@@post-migration-test@@"
started = []

def say(*words):
    print(MARK, *words, flush=True)

def run_the_offline_script():
    script = importlib.import_module("backend.app.db.post_migration.__main__")
    started.append(True)
    sys.exit(script.main(sys.argv[1:]))
"""

# The first child: the offline script, paused inside AutoincrementFix.apply until the test writes a line on its stdin.
PAUSED_IN_APPLY = CHILD_PRELUDE + """
from backend.app.db.post_migration.autoincrement import AutoincrementFix

original_apply = AutoincrementFix.apply

def paused_apply(self, *args, **kwargs):
    say("inside-apply")
    sys.stdin.readline()
    return original_apply(self, *args, **kwargs)

AutoincrementFix.apply = paused_apply
run_the_offline_script()
"""

# The second child: the offline script, saying when it is about to wait on fcntl.flock, and what its detection found.
ANNOUNCING = CHILD_PRELUDE + """
import fcntl

real_flock = fcntl.flock
announced = []

def announcing_flock(fd, operation):
    if started and not announced:
        announced.append(True)
        say("waiting-for-the-lock")
    return real_flock(fd, operation)

fcntl.flock = announcing_flock

from backend.app.db.post_migration.autoincrement import AutoincrementFix

original_detect = AutoincrementFix.detect

def announcing_detect(self, *args, **kwargs):
    anomaly = original_detect(self, *args, **kwargs)
    say("detected", "clean" if anomaly is None else "anomaly")
    return anomaly

AutoincrementFix.detect = announcing_detect
run_the_offline_script()
"""


def _lock_file(db: Path) -> Path:
    """The lock file of the contract: ``<db file name>.post-migration.lock``, beside the database."""
    return db.with_name(f"{db.name}.post-migration.lock")


def _try_the_lock(lock: Path) -> str:
    """Try ``LOCK_EX | LOCK_NB`` on ``lock`` from a descriptor of our own: ``refused``, ``granted`` (released at once) or ``missing``.

    ``flock`` locks belong to the open file, not to the process: a new descriptor in this same
    process competes like another worker. The file is opened without ``O_CREAT``, so the probe can
    never be what leaves a lock file on disk — the test's last assertion stays about the run.
    """
    try:
        fd = os.open(lock, os.O_RDONLY)
    except FileNotFoundError:
        return "missing"
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return "refused"
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return "granted"
    finally:
        os.close(fd)


def _probe_the_lock_inside(monkeypatch: pytest.MonkeyPatch, method: str, lock: Path) -> list[str]:
    """Make each call of ``AutoincrementFix.<method>`` first try the lock (``_try_the_lock``), then go on unchanged; returns the results in order."""
    probes: list[str] = []
    original = getattr(AutoincrementFix, method)

    def probing(self: AutoincrementFix, *args: Any, **kwargs: Any) -> Any:
        probes.append(_try_the_lock(lock))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(AutoincrementFix, method, probing)
    return probes


def _start_child(code: str, *args: str, stdin: int = subprocess.DEVNULL) -> subprocess.Popen[bytes]:
    """``python -c code args…`` in a child process, stdout and stderr together on one unbuffered pipe."""
    return subprocess.Popen([sys.executable, "-c", code, *args], cwd=PROJECT_ROOT, env=_child_env(), stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)


def _await_mark(child: subprocess.Popen[bytes]) -> tuple[Optional[str], bytes]:
    """Read ``child``'s output up to its first mark line: ``(what follows the mark, every byte read)``.

    ``None`` when the child ends, or prints no mark within ``MARK_TIMEOUT``: a deadline against a
    hang, never a wait for something to happen — every ordering in the test is a handshake. Bytes are
    read one at a time, so nothing past the mark is taken from ``communicate()``.
    """
    assert child.stdout is not None
    fd = child.stdout.fileno()
    seen = bytearray()
    line_start = 0
    deadline = time.monotonic() + MARK_TIMEOUT
    while (remaining := deadline - time.monotonic()) > 0 and select.select([fd], [], [], remaining)[0]:
        byte = os.read(fd, 1)
        if not byte:
            break
        seen += byte
        if byte == b"\n":
            line = seen[line_start:].decode(errors="replace").strip()
            line_start = len(seen)
            if line.startswith(MARK):
                return line[len(MARK) :].strip(), bytes(seen)
    return None, bytes(seen)


def _script_outcome(output: bytes) -> Optional[str]:
    """The ``autoincrement`` outcome the offline script printed (``Fix autoincrement: <outcome>``), or ``None``."""
    found = re.search(rf"^Fix {FIX}: (\w+)\s*$", output.decode(errors="replace"), re.MULTILINE)
    return found.group(1) if found else None


def test_the_run_holds_its_lock_while_it_applies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 12: while the run is inside ``AutoincrementFix.apply``, ``<db name>.post-migration.lock`` is exclusively locked; the file stays after.

    The probe — a new descriptor on the lock file, ``LOCK_EX | LOCK_NB`` — must be refused there;
    then the original ``apply`` runs and the conversion is still ``applied``. No clock: the probe
    runs once, at the point the run itself reaches.
    """
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")
    lock = _lock_file(db)
    probes = _probe_the_lock_inside(monkeypatch, "apply", lock)

    report = post_migration.run_post_migration_fixes(db, None)

    assert probes, "barrier: the run never entered AutoincrementFix.apply, so the probe never ran"
    assert set(probes) == {"refused"}, f"inside apply, LOCK_EX | LOCK_NB on {lock.name} from a new descriptor gave {probes}: 'missing' = no lock file, 'granted' = nothing held it"
    assert report.outcomes.get(FIX) == "applied"
    assert lock.is_file(), f"{lock.name} must stay beside the database after the run"


@pytest.mark.parametrize("dry_run", [False, True], ids=["run", "dry-run"])
def test_the_run_already_holds_its_lock_while_it_detects_dry_runs_included(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dry_run: bool) -> None:
    """Contract 12, beyond the brief: the lock is held from detection on — in a dry run too — not only around ``apply``.

    That is the half that closes the race: two workers that both detect before either converts
    would still both apply, one after the other, and the second would fail. A lock taken around
    ``apply`` alone passes the test above and keeps the defect. Same probe, inside ``detect``.
    """
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")
    lock = _lock_file(db)
    probes = _probe_the_lock_inside(monkeypatch, "detect", lock)

    report = post_migration.run_post_migration_fixes(db, None, dry_run=dry_run)

    assert probes, "barrier: the run never called AutoincrementFix.detect, so the probe never ran"
    assert set(probes) == {"refused"}, f"inside detect, LOCK_EX | LOCK_NB on {lock.name} from a new descriptor gave {probes}: 'missing' = no lock file, 'granted' = nothing held it"
    assert report.outcomes.get(FIX) == ("would_apply" if dry_run else "applied")


def test_two_offline_runs_started_together_convert_once_and_both_succeed(tmp_path: Path) -> None:
    """Contract 12, end to end: two offline scripts on one 1.1 database — one ``applied``, the other ``clean``, both exit 0, no ``.bak`` left.

    The defect as reviewed: both runs detect before either converts; the second then meets tables
    already converted, reports ``failed`` and keeps a backup of a database that is fine.

    Deterministic by handshakes, no sleep. The first child pauses inside ``apply`` and says so;
    only then does the second start, and the test waits for its first sign: about to wait on
    ``fcntl.flock`` (the cure) or done detecting (no lock: it saw the tables unconverted). Only then
    does the first go on. So the second's fate is fixed in both worlds: it waits and finds
    ``clean`` with the lock, it fails in ``apply`` without. ``MARK_TIMEOUT`` and ``CHILD_TIMEOUT``
    only stop a hang.
    """
    data_dir = tmp_path / "data"
    db = _build_v110_db(data_dir / "sqlite" / "app.db")
    args = ("--db", str(db), "--data-dir", str(data_dir))
    first = _start_child(PAUSED_IN_APPLY, *args, stdin=subprocess.PIPE)
    second: Optional[subprocess.Popen[bytes]] = None
    try:
        first_sign, first_seen = _await_mark(first)
        assert first_sign == "inside-apply", f"setup: the first run never paused inside apply\n{first_seen.decode(errors='replace')}"
        second = _start_child(ANNOUNCING, *args)
        second_sign, second_seen = _await_mark(second)
        first_rest, _ = first.communicate(input=b"go\n", timeout=CHILD_TIMEOUT)
        second_rest, _ = second.communicate(timeout=CHILD_TIMEOUT)
    finally:
        for child in (first, second):
            if child is not None and child.poll() is None:
                child.kill()
                child.wait()

    first_output, second_output = first_seen + first_rest, second_seen + second_rest
    said = f"the second's first sign: {second_sign!r}\n--- first\n{first_output.decode(errors='replace')[-3000:]}\n--- second\n{second_output.decode(errors='replace')[-3000:]}"
    assert sorted([_script_outcome(first_output) or "?", _script_outcome(second_output) or "?"]) == ["applied", "clean"], said
    assert (first.returncode, second.returncode) == (0, 0), said
    assert _backups(db) == [], said


# =============================================================================
# 13. THE LOG SAYS HOW LONG IT TOOK (plan §5, risk 3)
# =============================================================================
#
# capture_logs swaps structlog's processors for a LogCapture *inside the configured list*, so a bound
# logger cached with cache_logger_on_first_use=True (set by configure_logging when backend.app.main is
# imported) still reaches it: it holds that same list. The list is only ever replaced by configure_logging,
# once per process, while caching is still off — so no ordering of tests leaves this module's logger blind.
# The barrier in each test says so if that ever changes.

LOGGER = "backend.app.db.post_migration"
APPLIED_EVENT = "Post-migration fixes applied and verified"
FAILED_EVENT = "Post-migration fix failed: the database was left as it was"


def _closing_events(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The captured events that close a run that applied fixes: success or failure, from any logger."""
    return [entry for entry in logs if entry.get("event") in {APPLIED_EVENT, FAILED_EVENT}]


def _seconds_problem(event: dict[str, Any]) -> Optional[str]:
    """``None`` when ``event['seconds']`` is a float >= 0; otherwise what is wrong with it."""
    seconds = event.get("seconds", "<missing>")
    if isinstance(seconds, float) and seconds >= 0:
        return None
    return f"the closing event must carry 'seconds', the time the apply phase took, as a float >= 0; got {seconds!r} in {event}"


def test_a_run_that_converts_logs_how_long_it_took(tmp_path: Path) -> None:
    """Contract 13: a conversion closes with exactly one ``Post-migration fixes applied and verified`` from ``backend.app.db.post_migration``, carrying ``seconds``.

    No failure event beside it; ``db_path`` and ``fixes`` as before. Only the type and the sign of
    ``seconds`` are asserted — never a duration. Barrier first: the capture saw the closing event.
    """
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")

    with capture_logs(processors=[structlog.stdlib.add_logger_name]) as logs:
        report = post_migration.run_post_migration_fixes(db, None)

    assert report.outcomes.get(FIX) == "applied", NOT_APPLIED
    closing = _closing_events(logs)
    assert closing, f"barrier: capture_logs saw no closing event among {[entry.get('event') for entry in logs]}: the module's logger does not reach the capture"
    assert [(entry["event"], entry.get("logger")) for entry in closing] == [(APPLIED_EVENT, LOGGER)]
    event = closing[0]
    assert (event.get("db_path"), event.get("fixes")) == (str(db), [FIX])
    assert _seconds_problem(event) is None, _seconds_problem(event)


def test_a_run_that_fails_logs_how_long_it_took(tmp_path: Path) -> None:
    """Contract 13: a refused conversion (contract 5) closes with exactly one ``Post-migration fix failed: …`` from ``backend.app.db.post_migration``, carrying ``seconds``.

    No success event beside it; ``db_path``, ``backup`` and ``errors`` as before. Only the type and
    the sign of ``seconds`` are asserted. Barrier first: the capture saw the closing event.
    """
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")
    _give_a_table_level_primary_key(db, "fx_conversion_routes")

    with capture_logs(processors=[structlog.stdlib.add_logger_name]) as logs:
        report = post_migration.run_post_migration_fixes(db, None)

    assert report.outcomes.get(FIX) == "failed", NOT_FAILED
    closing = _closing_events(logs)
    assert closing, f"barrier: capture_logs saw no closing event among {[entry.get('event') for entry in logs]}: the module's logger does not reach the capture"
    assert [(entry["event"], entry.get("logger")) for entry in closing] == [(FAILED_EVENT, LOGGER)]
    event = closing[0]
    assert (event.get("db_path"), event.get("backup"), event.get("errors")) == (str(db), str(report.backup_path), report.errors)
    assert report.errors, "a failed run must say why"
    assert _seconds_problem(event) is None, _seconds_problem(event)


# =============================================================================
# 14. A FOREIGN-KEY VIOLATION ALREADY IN THE DATABASE (W-B22)
# =============================================================================

ORPHAN_FIX = "orphan_pair_halves"
FK_WARNING = "Foreign key violations"  # how the warning listing the violations found before a fix starts — pinned loosely


def _leave_a_received_half_whose_partner_is_gone(db: Path) -> int:
    """A TRANSFER pair of 2 Apple from broker 1 to broker 2, then its giving half deleted with foreign keys off: the received half's link names a row that no longer exists. Its id."""
    stamp = "2025-08-01 10:00:00.000000"
    columns = "broker_id, asset_id, type, date, quantity, amount, cost_basis_override, cost_basis_currency, description, created_at, updated_at"
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        giving = conn.execute(f"INSERT INTO transactions ({columns}) VALUES (1, 1, 'TRANSFER', '2025-08-01', -2, 0, NULL, NULL, 'To Broker Beta', ?, ?)", (stamp, stamp)).lastrowid
        received = conn.execute(f"INSERT INTO transactions ({columns}) VALUES (2, 1, 'TRANSFER', '2025-08-01', 2, 0, 243.36, 'USD', 'From Broker Alpha', ?, ?)", (stamp, stamp)).lastrowid
        conn.execute("UPDATE transactions SET related_transaction_id = ? WHERE id = ?", (received, giving))
        conn.execute("UPDATE transactions SET related_transaction_id = ? WHERE id = ?", (giving, received))
        conn.execute("DELETE FROM transactions WHERE id = ?", (giving,))
        conn.commit()
    found = [(table, rowid, parent) for table, rowid, parent, _key in _foreign_key_violations(db)]
    assert found == [("transactions", received, "transactions")], f"setup: the received half's link is the only broken one; found {found}"
    return received


def _leave_a_price_of_a_deleted_asset(db: Path) -> list[tuple[Any, ...]]:
    """A price of Delisted Corp — asset 2, deleted — written with foreign keys off: a row of ``price_history`` whose parent is missing. The violations after it."""
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("INSERT INTO price_history (asset_id, date, close, currency, source_plugin_key, fetched_at) VALUES (2, '2025-01-02', 1.5, 'EUR', 'justetf', '2025-01-03 06:00:00.000000')")
        conn.commit()
    violations = _foreign_key_violations(db)
    assert [(table, parent) for table, _rowid, parent, _key in violations] == [("price_history", "assets")], f"setup: the price is the only broken link; found {violations}"
    return violations


def _foreign_key_warnings(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [entry for entry in logs if entry.get("logger") == LOGGER and entry.get("log_level") == "warning" and str(entry.get("event", "")).startswith(FK_WARNING)]


def _carries(event: dict[str, Any], violation: tuple[Any, ...]) -> bool:
    """Whether a field of ``event`` beyond its name, logger, level and count names ``violation``: its table, its row and its parent."""
    table, rowid, parent, _key = violation
    return any(table in str(value) and parent in str(value) and str(rowid) in str(value) for name, value in event.items() if name not in {"event", "logger", "log_level", "count"})


def test_a_broken_link_already_there_no_longer_blocks_the_fixes(tmp_path: Path) -> None:
    """Contract 14 (RED): a 1.1 database at head with a received TRANSFER whose partner is gone — both fixes ``applied``, the half an ADJUSTMENT without a link, nothing broken, no backup; a second run ``clean``.

    Today ``autoincrement`` meets the half's broken link in the foreign key check of the whole database,
    which must be empty after it: ``failed``, the backup kept, and ``orphan_pair_halves``, which would mend
    that very link, never runs — ``would_apply`` — at every start.
    """
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")
    half = _leave_a_received_half_whose_partner_is_gone(db)

    first = post_migration.run_post_migration_fixes(db, None)
    with _connect(db) as conn:
        half_after = conn.execute("SELECT type, related_transaction_id FROM transactions WHERE id = ?", (half,)).fetchone()
    broken_after = _foreign_key_violations(db)
    second = post_migration.run_post_migration_fixes(db, None)
    print(f"first: {first.outcomes} {first.errors} backup {first.backup_path}; the half: {half_after}; broken: {broken_after}; second: {second.outcomes} {second.errors}")

    assert ([first.outcomes.get(FIX), first.outcomes.get(ORPHAN_FIX)], first.backup_path, first.errors) == (["applied", "applied"], None, [])
    assert half_after == ("ADJUSTMENT", None)
    assert broken_after == []
    assert ([second.outcomes.get(FIX), second.outcomes.get(ORPHAN_FIX)], second.backup_path) == (["clean", "clean"], None)
    assert _backups(db) == []


def test_a_broken_link_in_another_table_is_left_as_it_is_and_reported(tmp_path: Path) -> None:
    """Contract 14 (RED): a 1.1 database at head with a price of a deleted asset — ``autoincrement`` ``applied``, the price and its broken link as they were, listed once in the run's warning, no backup; a second run ``clean``.

    Today the run fails at every start on a violation no fix brought or can mend: ``failed`` twice, a
    backup kept each time (one file when both runs fall in the same second: the name is stamped to it).
    """
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")
    violations = _leave_a_price_of_a_deleted_asset(db)
    prices = _rows(db)["price_history"]

    with capture_logs(processors=[structlog.stdlib.add_logger_name]) as logs:
        first = post_migration.run_post_migration_fixes(db, None)
    second = post_migration.run_post_migration_fixes(db, None)
    print(f"first: {first.outcomes} {first.errors} backup {first.backup_path}; second: {second.outcomes} {second.errors} backup {second.backup_path}; beside the database: {_backups(db)}")

    assert ([first.outcomes.get(FIX), second.outcomes.get(FIX)], [first.backup_path is not None, second.backup_path is not None]) == (["applied", "clean"], [False, False])
    assert (first.errors, second.errors, _backups(db)) == ([], [], [])
    assert _foreign_key_violations(db) == violations, "the violation stays as it was: no fix mends a price"
    assert _rows(db)["price_history"] == prices
    assert _closing_events(logs), "barrier: the capture saw no closing event of the run"
    warnings = _foreign_key_warnings(logs)
    assert [(warning.get("count"), _carries(warning, violations[0])) for warning in warnings] == [(1, True)], f"one warning per run, with the count and the violating row: {warnings}"


def test_a_fix_that_breaks_a_link_itself_still_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 14 (guard, green before and after): ``autoincrement`` made to point an access at a broker that does not exist, after its own work — ``failed`` with that link named, the database as it was, the backup kept and equal to it.

    The link is broken by an UPDATE, not a deletion: a deleted parent would also change a row count, which
    fails the fix on its own, and the guard would hold without the foreign key check.
    """
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")
    original_apply = AutoincrementFix.apply
    broken: list[int] = []

    def apply_then_break_a_link(self: AutoincrementFix, conn: sqlite3.Connection, anomaly: Any, ctx: Any) -> None:
        original_apply(self, conn, anomaly, ctx)
        conn.execute("UPDATE broker_user_access SET broker_id = 999 WHERE id = 1")
        broken.append(1)

    monkeypatch.setattr(AutoincrementFix, "apply", apply_then_break_a_link)

    run = _observe_run(db)

    assert broken, "barrier: the fix never reached its apply, so nothing was broken"
    assert run.report.outcomes.get(FIX) == "failed", NOT_FAILED
    assert any("broker_user_access" in error for error in run.report.errors), run.report.errors
    assert run.master_after == run.master_before
    assert run.rows_after == run.rows_before
    assert run.report.backup_path is not None and run.backups_after == [Path(run.report.backup_path).name]
    assert _rows(Path(run.report.backup_path)) == run.rows_before


# =============================================================================
# 15. THE OFFLINE SCRIPT LOGS TO THE CONSOLE ONLY (W-B23)
# =============================================================================


def test_the_offline_script_writes_no_file_in_the_configured_data_dir(configured_sandbox: Path, tmp_path: Path) -> None:
    """Contract 15 (guard, green before and after): a real run through ``python -m`` converts and leaves the configured data dir — the sandbox — as it was: no ``logs/``, the canary alone; no ``logs/`` in the data dir it was given either."""
    data_dir = tmp_path / "data"
    db = _build_v110_db(data_dir / "sqlite" / "app.db")
    before = _tree(configured_sandbox)

    completed = _run_script("--db", str(db), "--data-dir", str(data_dir))

    assert completed.returncode == 0, _output(completed)
    assert _autoincrement_tables(_master(db)) == CENSUS, f"barrier: the script converted, so it had lines to log\n{_output(completed)}"
    assert _tree(configured_sandbox) == before, f"a file appeared in the configured data dir\n{_output(completed)}"
    assert not (data_dir / "logs").exists(), _output(completed)


# =============================================================================
# 16. THE LOCK FILE IS NEVER A LINK, AND IS ITS OWNER'S ALONE (Z-28)
# =============================================================================
#
# As the backup and scheduler locks: ``os.open(<lock>, O_RDWR | O_CREAT | O_NOFOLLOW, 0o600)``, then ``flock`` on the
# descriptor. Nothing here holds a lock while the run is called: its ``flock`` waits, and no test may hang on it. The
# umask is left alone: it can only narrow 0o600, so the mode is pinned as "owner read and write, nothing for group and
# others", never as an exact value.

BEHIND_THE_LINK = b"not a lock file: behind a symbolic link\n"
BEHIND_THE_LINK_MODE = 0o644
LINKS = ("dangling", "to-an-existing-file")
OWNER_RW = 0o600
GROUP_AND_OTHERS = 0o077


def _link_at(lock: Path, behind: Path, kind: str) -> Path:
    """A symbolic link at ``lock``, to ``behind/never-created`` (``dangling``) or to ``behind/existing-file`` (``BEHIND_THE_LINK``, mode ``BEHIND_THE_LINK_MODE``): its target.

    The dangling link's folder exists, so a lock that follows the link creates its target there rather than fail on a
    missing folder: a ``FileNotFoundError`` is an ``OSError`` too, and would pass for the refusal.
    """
    behind.mkdir(parents=True)
    target = behind / ("never-created" if kind == "dangling" else "existing-file")
    if kind != "dangling":
        target.write_bytes(BEHIND_THE_LINK)
        target.chmod(BEHIND_THE_LINK_MODE)
    lock.symlink_to(target)
    return target


def _what_is_at(path: Path) -> tuple[Any, ...]:
    """What is at ``path`` itself, never following a link: ``("absent",)``, ``("link", <target>)`` or ``("file", <bytes>, <mode>)``."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return ("absent",)
    if stat.S_ISLNK(info.st_mode):
        return ("link", str(path.readlink()))
    return ("file", path.read_bytes(), oct(stat.S_IMODE(info.st_mode)))


def _mode_bits(path: Path) -> tuple[str, str, str]:
    """``path`` itself, never following a link: ``(its ls-style mode, its owner's read and write bits, its group's and others' bits)``."""
    mode = path.lstat().st_mode
    return stat.filemode(mode), oct(stat.S_IMODE(mode) & OWNER_RW), oct(stat.S_IMODE(mode) & GROUP_AND_OTHERS)


def _run_recording_connections(db: Path) -> tuple[Optional[OSError], Optional[PostMigrationReport], list[str]]:
    """``run_post_migration_fixes(db, None)``: ``(the OSError it raised, the report it returned, every database it opened)``.

    ``sqlite3.connect`` — the module the run reaches it through — is wrapped for the call only: the test's own reads
    afterwards are not counted.
    """
    opened: list[str] = []
    real_connect = sqlite3.connect

    def recording_connect(database: Any, *args: Any, **kwargs: Any) -> sqlite3.Connection:
        opened.append(str(database))
        return real_connect(database, *args, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sqlite3, "connect", recording_connect)
        try:
            report = post_migration.run_post_migration_fixes(db, None)
        except OSError as error:
            return error, None, opened
    return None, report, opened


@pytest.mark.parametrize("kind", LINKS)
def test_a_symbolic_link_at_the_lock_file_is_refused_before_the_database_is_opened(tmp_path: Path, kind: str) -> None:
    """Contract 16 (RED): with a symbolic link at ``<db name>.post-migration.lock``, the run raises ``OSError`` without having opened the database.

    The database is a 1.1 install at head, which a run that got past its lock would convert (contract 2): here no
    connection is made, so no fix runs — the file byte-identical, unconverted, no backup. Behind a dangling link
    nothing is created; an existing file behind it keeps its bytes and its mode; the link is still there, to the
    same target. Today ``open(<lock>, "a+")`` follows the link — creating a dangling one's target —, locks the file
    behind it and converts the database: no ``OSError``.
    """
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")
    lock = _lock_file(db)
    assert _what_is_at(lock) == ("absent",), "setup: no lock file beside the database yet"
    target = _link_at(lock, tmp_path / "behind-the-link", kind)
    _settle(db)
    digest, behind, link = _digest(db), _what_is_at(target), _what_is_at(lock)

    error, report, opened = _run_recording_connections(db)

    assert error is not None, f"the run followed the symbolic link {lock.name} -> {target}: no OSError; it opened {opened}, outcomes {getattr(report, 'outcomes', None)}; behind the link: {behind[0]}, now {_what_is_at(target)[0]}"
    assert opened == [], f"{type(error).__name__}, but only once the database was opened: {opened}"
    assert _what_is_at(target) == behind, f"{type(error).__name__}, but behind the link {behind[0]} is now {_what_is_at(target)[0]}: the lock followed it"
    assert _what_is_at(lock) == link, f"the link is left as it was: {link}, now {_what_is_at(lock)}"
    assert (_digest(db), _autoincrement_tables(_master(db)), _backups(db)) == (digest, set(), []), "no fix ran: the database byte-identical, unconverted, no backup"


def test_the_lock_file_a_run_creates_is_its_owners_alone(tmp_path: Path) -> None:
    """Contract 16 (RED): a run that finds no lock file beside the database creates one its owner reads and writes, with nothing for group and others.

    A new database: ``clean``, its lock taken all the same (contract 12), the file kept. Created 0o600, which the
    umask can only narrow, so only those bits are pinned, and the umask is left alone. Today ``open(<lock>, "a+")``
    creates it 0o666 less the umask: 0o644 under the usual 0o022, readable by every user of the machine. Under a umask
    that already takes everything from group and others the defect cannot show, and this passes either way.
    """
    db = tmp_path / "sqlite" / "app.db"
    _alembic_upgrade_head(db)
    lock = _lock_file(db)
    assert _what_is_at(lock) == ("absent",), "setup: no lock file beside the new database yet"

    report = post_migration.run_post_migration_fixes(db, None)

    assert report.outcomes.get(FIX) == "clean", f"barrier: the run went through its detection, under its lock: {report.outcomes}"
    filemode, owner, others = _mode_bits(lock)
    assert (filemode[0], owner, others) == ("-", oct(OWNER_RW), oct(0)), f"{lock.name} was created {filemode}: a regular file its owner reads and writes, group and others nothing (0o600, which the umask can only narrow)"


# =============================================================================
# 17. TABLE NAMES A DATABASE BRINGS, QUOTED (B-36)
# =============================================================================
#
# The fixes run on a restored archive's copy too (``staging``), whose tables the archive names: a name is user data. A
# name holding a double quote broke the count of every table's rows (``_row_counts``), and one built as ``a" WHERE 1
# --`` turned that count into another statement. The file's own readers (``_rows``) quote as the code did, so this
# section reads its odd tables with ``_quoted``.

#: Tables an archive may bring (B-36), with their rows: a name holding a double quote, and one that, unquoted, ends the
#: name and comments the rest out.
ODD_TABLES: dict[str, list[tuple[int]]] = {'x"y': [(1,), (2,), (3,)], 'a" WHERE 1 --': [(7,), (8,)]}


def _quoted(name: str) -> str:
    """A name as SQL quotes it: between double quotes, each double quote it holds doubled."""
    return '"' + name.replace('"', '""') + '"'


def _add_odd_tables(db: Path) -> None:
    """``ODD_TABLES``, created in ``db`` with their rows."""
    with _connect(db) as conn, conn:
        for name, rows in ODD_TABLES.items():
            conn.execute(f"CREATE TABLE {_quoted(name)} (v INTEGER)")
            conn.executemany(f"INSERT INTO {_quoted(name)} (v) VALUES (?)", rows)


def _odd_rows(db: Path) -> dict[str, list[tuple[Any, ...]]]:
    """The rows of each of ``ODD_TABLES`` in ``db``."""
    with _connect(db) as conn:
        return {name: sorted(conn.execute(f"SELECT v FROM {_quoted(name)}").fetchall()) for name in ODD_TABLES}


def test_a_table_name_holding_a_double_quote_is_counted_and_the_pending_fix_applied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 17 (B-36, RED): a 1.1 database at head — ``autoincrement`` pending — that also holds a table named
    ``x"y`` and one named ``a" WHERE 1 --``. The run applies the fix without an exception and reports no error; every
    count of rows it takes (``_row_counts``, before and after the fix) holds the two tables with their rows; they keep
    their rows; the census converted, no backup left. Today ``_row_counts`` writes ``FROM "x"y"`` (a syntax error) and
    ``FROM "a" WHERE 1 --"`` (a table ``a`` that does not exist): ``OperationalError``, out of the run."""
    db = _build_v110_db(tmp_path / "sqlite" / "app.db")
    _add_odd_tables(db)
    rows_before = _odd_rows(db)
    counted: list[dict[str, int]] = []
    real_row_counts = post_migration._row_counts

    def row_counts(conn: sqlite3.Connection) -> dict[str, int]:
        counts = real_row_counts(conn)
        counted.append(counts)
        return counts

    monkeypatch.setattr(post_migration, "_row_counts", row_counts)
    try:
        report = post_migration.run_post_migration_fixes(db, None)
    except sqlite3.Error as exc:
        pytest.fail(f"the run raised {type(exc).__name__} on a table whose name holds a double quote: {exc}")

    assert (report.outcomes.get(FIX), report.errors, report.integrity_ok) == ("applied", [], True), f"the pending fix applied, no error: {report.outcomes}, {report.errors}"
    assert counted, "barrier: the run counts the rows of every table (_row_counts) around the fix it applies"
    expected = {name: len(rows) for name, rows in ODD_TABLES.items()}
    odd_counts = [{name: counts.get(name) for name in ODD_TABLES} for counts in counted]
    assert all(found == expected for found in odd_counts), f"every count of the run holds the odd tables with their rows, {expected}: {odd_counts}"
    assert _odd_rows(db) == rows_before, "the odd tables keep their rows"
    assert (_autoincrement_tables(_master(db)), _backups(db)) == (CENSUS, []), "the census converted, no backup left"
