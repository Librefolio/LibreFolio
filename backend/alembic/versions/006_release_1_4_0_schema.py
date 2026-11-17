"""Release 1.4.0 schema

Revision ID: 006_release_1_4_0_schema
Revises: 005_release_1_3_0_schema
Create Date: 2026-11-13

One migration per release (the developer's decision, 19/10/2026, confirmed 24/10/2026): every schema change of the 1.4
cycle edits this file, never a new revision. Workstreams developed in parallel each add their own step on their branch,
and the steps are merged into this one file at integration (never ``alembic merge``, never a second head).

How a step is written, so that the steps of different workstreams merge without touching each other (plan of project 67,
passo 4, «La migrazione in dettaglio»):

- one ``_upgrade_<step>`` and one ``_downgrade_<step>`` function per step, with its constants next to it;
- one line per step in ``upgrade()`` and in ``downgrade()``, the steps independent of each other;
- a section of this docstring named after the step (no progressive numbers: two workstreams would both write «step 2»);
- every part checks before it acts (``_columns``), so a run that stopped half way can be run again;
- columns are added with plain ``ALTER TABLE ADD COLUMN`` and dropped with ``DROP COLUMN``, never with a batch: a batch
  rebuilds the table, and with ``PRAGMA foreign_keys=ON`` dropping the original would fire the foreign-key action of every
  row that points at it (the rule of ``005_release_1_3_0_schema``).

────────────────────────────────────────────────────────────────────────────────
The steps of 1.4.0 follow, one section each.

asset_profile (project 68, lot A2)
──────────────────────────────────
The asset profile: the descriptive facts of an asset, each with its source and its history (plan 68, §3.1).

- ``asset_profile_updates``: one row per change of one voice of an asset's profile; a row is never updated, it is
  inserted, and deleted only to forget a change. ``key`` is plain text with no CHECK: the voices are listed by the
  catalogue (``services/assets/profile/catalogue.py``), so a new voice needs no migration. ``value`` is JSON text,
  NULL for a value left empty on purpose. ``asset_id`` goes with its asset (``CASCADE``); ``user_id``, the author of a
  value written by hand, is emptied with its account (``SET NULL``). A plain ``INTEGER PRIMARY KEY``: the table is a
  series, outside the AUTOINCREMENT census of plan 34.
- ``asset_enrichers``: one row per asset, ``asset_id`` its primary key (``CASCADE``). ``config`` is the user's ordered
  dictionary of enrichers, ``state`` what each one last read: two columns so that neither write overwrites the other.
  Both start as ``'{}'``.
- One index, ``ix_asset_profile_updates_asset_key_read_on (asset_id, key, read_on)``; ``asset_enrichers`` needs none
  beyond its primary key. Every read of the profile store (``services/assets/profile/store.py``) searches it, and its
  order is the store's (``read_on``, ``id``) order within a voice, so none sorts (SQLite 3.53)::

    the rows of some assets and voices up to a day (steps; «now» of the voices a write touches, without the day):
    SELECT … FROM asset_profile_updates WHERE asset_id IN (?, ?) AND key IN (?, ?) AND read_on <= ?
      ORDER BY asset_id, key, read_on, id
    → SEARCH asset_profile_updates USING INDEX ix_asset_profile_updates_asset_key_read_on (asset_id=? AND key=? AND read_on<?)

    the same for every voice (a read that names none): the index on its asset_id prefix
    → SEARCH asset_profile_updates USING INDEX ix_asset_profile_updates_asset_key_read_on (asset_id=?)

    the first day of each asset («start: min»):
    SELECT asset_id, min(read_on) FROM asset_profile_updates WHERE asset_id IN (?, ?) AND key IN (?) GROUP BY asset_id
    → SEARCH asset_profile_updates USING COVERING INDEX ix_asset_profile_updates_asset_key_read_on (asset_id=? AND key=?)

  Its ``asset_id`` prefix also serves the ``CASCADE`` of a deleted asset.
- Downgrade: the two tables are dropped, the index with its table.

asset_profile_legacy_copy (project 68, lot A4)
──────────────────────────────────────────────
Data only: what ``classification_params`` holds today becomes the first history of the profile (plan 68, §3.7).

- For every asset, ``short_description`` (a non-empty text), ``geographic_area`` and ``sector_area`` become rows of
  ``asset_profile_updates`` for the voices ``description``, ``geography`` and ``sector``: ``source`` ``legacy``, no
  author, ``read_on`` the day of the upgrade in the scheduler's time zone (the ``scheduler_timezone`` setting, UTC when
  it is missing or not valid). A map holds its weights as decimal strings, without the ``{"distribution": …}`` envelope.
- The JSON is read with Decimals (``parse_float=Decimal``): weights written as numbers (the test data) and as strings
  (the app) copy alike. The copy does not translate country or sector names: the profile store reads every row back
  through its catalogue, so a row keeps the spelling the column had and still reads as the catalogue's stored form.
- Nothing to copy (NULL, empty, not JSON, not an object) → no row; a distribution today's rule refuses (not an object,
  empty, a weight not a number or negative, a sum farther than 0.01 from 1) → that voice skipped, the others copied.
  Each skip is a warning of logger ``alembic.runtime.migration``.
- Checks before it acts: an asset and voice that already has a ``legacy`` row is not copied again.
- Downgrade, before the tables go: each asset's ``classification_params`` is rebuilt from its last row of each voice
  in (``read_on``, ``id``) order — what the profile learned since the upgrade goes back to the column. A voice without
  rows keeps its part; a last row left empty removes it; an asset without rows keeps its column as it was.

plugin_call_counters (project 76, lot U1)
─────────────────────────────────────────
How many calls each plugin that reaches an external service made, per calendar window (plan 76, §3.5).

- ``plugin_call_counters``: one row per ``family`` and ``plugin_code`` (a shared group with ``family`` ``group``), the
  pair its primary key; no other id, no AUTOINCREMENT (outside the census of plan 34), no foreign key: a plugin is code,
  not a row. Five windows aligned in UTC (minute, hour, day, ISO week, month), each ``<window>_since`` (epoch seconds of
  the window's start) and ``<window>_count``, all INTEGER NOT NULL; ``updated_at`` DATETIME NOT NULL.
- One atomic ``INSERT … ON CONFLICT (family, plugin_code) DO UPDATE … WHERE … RETURNING`` per call
  (``services/platform/call_counter.py``) reaches the row through its primary key: no index beyond it.
- Starts empty: no call was counted before 1.4.
- Downgrade: the table is dropped.

charge_links (project 66, lot R1)
─────────────────────────────────
A FEE or a TAX can say which transaction it belongs to (issue #25, plan 66, «Il dato»).

- ``transactions.parent_transaction_id``: INTEGER, NULL, a foreign key to ``transactions (id)`` with no action,
  ``DEFERRABLE INITIALLY DEFERRED`` like ``related_transaction_id``: checked at commit, so a batch that deletes a parent
  and its charges does not depend on their order, and a charge that points at a row gone cannot be saved. The charge
  points at its parent; the parent knows nothing. ``related_transaction_id`` stays the link of the three pairs, untouched.
- Added with a plain ``ALTER TABLE ADD COLUMN`` and a column-level ``REFERENCES``: SQLite drops a column that carries
  its own ``REFERENCES``, not one named in a table-level ``FOREIGN KEY``. Every existing row gets NULL: no charge is
  linked by the upgrade (no clean-up of stored data).
- One partial index, ``idx_transactions_parent (parent_transaction_id) WHERE parent_transaction_id IS NOT NULL``: only
  linked charges are in it, a handful of rows next to the whole ledger. The charges of some parents (the list, the
  delete check, the lot engine; ``services/transactions/charges.py``, from lot R2), and SQLite's own foreign-key check
  when any transaction is deleted, search it (SQLite 3.53)::

    SELECT id FROM transactions WHERE parent_transaction_id IN (?, ?)
    → SEARCH transactions USING COVERING INDEX idx_transactions_parent (parent_transaction_id=?)

    DELETE FROM transactions WHERE id = ?   (foreign_keys=ON: the check for children of the deleted row)
    → EXPLAIN shows an OpenRead on the rootpage of idx_transactions_parent; 2 000 deletes in 200 000 rows take
      0.01 s with it (as with a full index) and 11.8 s without any index

- Downgrade: the index, then the column.
"""

import json
import logging
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Sequence, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sqlalchemy as sa
from alembic import op

revision: str = "006_release_1_4_0_schema"
down_revision: Union[str, Sequence[str], None] = "005_release_1_3_0_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(conn: sa.engine.Connection, table: str) -> set[str]:
    """Return the current column names of ``table``."""
    return {row[1] for row in conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()}


# ─── step asset_profile (project 68, lot A2) ─────────────────────────────────────────────────────────────────────────

_PROFILE_UPDATES = "asset_profile_updates"
_ENRICHERS = "asset_enrichers"
_PROFILE_INDEX = "ix_asset_profile_updates_asset_key_read_on"


def _asset_profile_tables(conn: sa.engine.Connection) -> set[str]:
    """Which of the two tables of the step exist already."""
    rows = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type = 'table' AND name IN (:updates, :enrichers)"), {"updates": _PROFILE_UPDATES, "enrichers": _ENRICHERS})
    return {row[0] for row in rows}


def _upgrade_asset_profile(conn: sa.engine.Connection) -> None:
    """Step ``asset_profile``: create ``asset_profile_updates``, its index, and ``asset_enrichers``, those missing."""
    existing = _asset_profile_tables(conn)
    if _PROFILE_UPDATES not in existing:
        op.create_table(
            _PROFILE_UPDATES,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("asset_id", sa.Integer(), nullable=False),
            sa.Column("key", sa.String(), nullable=False),
            sa.Column("value", sa.Text(), nullable=True),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("read_on", sa.Date(), nullable=False),
            sa.Column("source_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        )
    conn.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {_PROFILE_INDEX} ON {_PROFILE_UPDATES} (asset_id, key, read_on)"))
    if _ENRICHERS not in existing:
        op.create_table(
            _ENRICHERS,
            sa.Column("asset_id", sa.Integer(), primary_key=True),
            sa.Column("config", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("state", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        )


def _downgrade_asset_profile(conn: sa.engine.Connection) -> None:
    """Step ``asset_profile`` undone: drop the two tables (the index goes with its table), those still there."""
    existing = _asset_profile_tables(conn)
    for table in (_ENRICHERS, _PROFILE_UPDATES):
        if table in existing:
            op.drop_table(table)


# ─── step asset_profile_legacy_copy (project 68, lot A4) ─────────────────────────────────────────────────────────────

_LEGACY = "legacy"
#: classification_params part → profile voice, and how a part becomes a value.
_LEGACY_TEXT_PARTS = (("short_description", "description"),)
_LEGACY_MAP_PARTS = (("geographic_area", "geography"), ("sector_area", "sector"))
_LEGACY_VOICES = ("description", "geography", "sector")
#: Today's rule for a distribution (``BaseDistribution``): weights not negative, summing to 1 within this.
_LEGACY_SUM_TOLERANCE = Decimal("0.01")
_legacy_log = logging.getLogger("alembic.runtime.migration")


def _legacy_today(conn: sa.engine.Connection) -> date:
    """The day of the upgrade in the scheduler's time zone (``scheduler_timezone``; UTC when unset or not valid)."""
    name = conn.execute(sa.text("SELECT value FROM global_settings WHERE key = 'scheduler_timezone'")).scalar()
    try:
        zone = ZoneInfo(str(name)) if name else ZoneInfo("UTC")
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")
    return datetime.now(UTC).astimezone(zone).date()


def _legacy_distribution(asset_id: int, part: str, block: object) -> dict[str, str] | None:
    """The weights of a ``{"distribution": {...}}`` block as decimal strings, or None (logged) when today's rule refuses it."""
    weights = block.get("distribution") if isinstance(block, dict) else None
    if not isinstance(weights, dict) or not weights:
        _legacy_log.warning("006 legacy copy: %s of asset %s is not a distribution, skipped", part, asset_id)
        return None
    parsed: dict[str, Decimal] = {}
    for name, weight in weights.items():
        if isinstance(weight, bool) or not isinstance(weight, (int, Decimal, str)):
            _legacy_log.warning("006 legacy copy: %s of asset %s has a weight that is not a number, skipped", part, asset_id)
            return None
        try:
            parsed[str(name)] = Decimal(str(weight))
        except InvalidOperation:
            _legacy_log.warning("006 legacy copy: %s of asset %s has a weight that is not a number, skipped", part, asset_id)
            return None
    if any(not weight.is_finite() or weight < 0 for weight in parsed.values()) or abs(sum(parsed.values()) - 1) > _LEGACY_SUM_TOLERANCE:
        _legacy_log.warning("006 legacy copy: the weights of %s of asset %s fail today's rule, skipped", part, asset_id)
        return None
    return {name: format(weight, "f") for name, weight in sorted(parsed.items())}


def _legacy_values(asset_id: int, text: str | None) -> dict[str, str]:
    """The profile voices of one ``classification_params`` text, as JSON value texts; {} when there is nothing to copy."""
    if not text or not text.strip():
        return {}
    try:
        params = json.loads(text, parse_float=Decimal)
    except ValueError:
        _legacy_log.warning("006 legacy copy: classification_params of asset %s is not JSON, skipped", asset_id)
        return {}
    if not isinstance(params, dict):
        _legacy_log.warning("006 legacy copy: classification_params of asset %s is not an object, skipped", asset_id)
        return {}
    values: dict[str, str] = {}
    for part, voice in _LEGACY_TEXT_PARTS:
        description = params.get(part)
        if isinstance(description, str) and description.strip():
            values[voice] = json.dumps(description.strip(), ensure_ascii=False)
    for part, voice in _LEGACY_MAP_PARTS:
        if params.get(part) is not None and (weights := _legacy_distribution(asset_id, part, params[part])) is not None:
            values[voice] = json.dumps(weights, separators=(",", ":"))
    return values


def _upgrade_asset_profile_legacy_copy(conn: sa.engine.Connection) -> None:
    """Step ``asset_profile_legacy_copy``: each asset's description, countries and sectors become ``legacy`` rows."""
    already = {(row[0], row[1]) for row in conn.execute(sa.text(f"SELECT DISTINCT asset_id, key FROM {_PROFILE_UPDATES} WHERE source = :legacy"), {"legacy": _LEGACY})}
    read_on = _legacy_today(conn)
    created_at = datetime.now(UTC).replace(tzinfo=None)
    rows = []
    for asset_id, text in conn.execute(sa.text("SELECT id, classification_params FROM assets WHERE classification_params IS NOT NULL ORDER BY id")):
        for voice, value in _legacy_values(asset_id, text).items():
            if (asset_id, voice) not in already:
                rows.append({"asset_id": asset_id, "key": voice, "value": value, "source": _LEGACY, "read_on": read_on, "created_at": created_at})
    if rows:
        updates = sa.table(
            _PROFILE_UPDATES,
            sa.column("asset_id", sa.Integer),
            sa.column("key", sa.String),
            sa.column("value", sa.Text),
            sa.column("source", sa.String),
            sa.column("read_on", sa.Date),
            sa.column("created_at", sa.DateTime),
        )
        conn.execute(updates.insert(), rows)
    _legacy_log.info("006 legacy copy: %s profile rows written", len(rows))


def _downgrade_asset_profile_legacy_copy(conn: sa.engine.Connection) -> None:
    """Step ``asset_profile_legacy_copy`` undone: each asset's ``classification_params`` rebuilt from its last rows of
    ``description``, ``geography`` and ``sector`` (in (``read_on``, ``id``) order), the profile being what changed since."""
    if _PROFILE_UPDATES not in _asset_profile_tables(conn):
        return
    last: dict[int, dict[str, str | None]] = {}
    statement = sa.text(f"SELECT asset_id, key, value FROM {_PROFILE_UPDATES} WHERE key IN ('description', 'geography', 'sector') ORDER BY asset_id, key, read_on, id")
    for asset_id, voice, value in conn.execute(statement):
        last.setdefault(asset_id, {})[voice] = value
    for asset_id, voices in last.items():
        text = conn.execute(sa.text("SELECT classification_params FROM assets WHERE id = :id"), {"id": asset_id}).scalar()
        try:
            params = json.loads(text, parse_float=Decimal) if text else {}
        except ValueError:
            params = {}
        if not isinstance(params, dict):
            params = {}
        for part, voice in (*_LEGACY_TEXT_PARTS, *_LEGACY_MAP_PARTS):
            if voice not in voices:
                continue
            value = None if voices[voice] is None else json.loads(voices[voice], parse_float=Decimal)
            if value is None:
                params.pop(part, None)
            elif voice == "description":
                params[part] = value
            else:
                params[part] = {"distribution": {name: format(Decimal(str(weight)), "f") for name, weight in value.items()}}
        rebuilt = json.dumps(params, default=str) if params else None
        conn.execute(sa.text("UPDATE assets SET classification_params = :params WHERE id = :id"), {"params": rebuilt, "id": asset_id})


# ─── step plugin_call_counters (project 76, lot U1) ──────────────────────────────────────────────────────────────────

_CALL_COUNTERS = "plugin_call_counters"
_CALL_WINDOWS = ("minute", "hour", "day", "week", "month")


def _call_counters_table(conn: sa.engine.Connection) -> bool:
    """Whether ``plugin_call_counters`` exists already."""
    return conn.execute(sa.text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :name"), {"name": _CALL_COUNTERS}).first() is not None


def _upgrade_plugin_call_counters(conn: sa.engine.Connection) -> None:
    """Step ``plugin_call_counters``: create the table, when missing."""
    if _call_counters_table(conn):
        return
    windows = [sa.Column(f"{window}_{part}", sa.Integer(), nullable=False) for window in _CALL_WINDOWS for part in ("since", "count")]
    op.create_table(
        _CALL_COUNTERS,
        sa.Column("family", sa.String(16), nullable=False),
        sa.Column("plugin_code", sa.String(64), nullable=False),
        *windows,
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("family", "plugin_code"),
    )


def _downgrade_plugin_call_counters(conn: sa.engine.Connection) -> None:
    """Step ``plugin_call_counters`` undone: drop the table, when there."""
    if _call_counters_table(conn):
        op.drop_table(_CALL_COUNTERS)


# ─── step charge_links (project 66, lot R1) ──────────────────────────────────────────────────────────────────────────

_TRANSACTIONS = "transactions"
_PARENT_COLUMN = "parent_transaction_id"
_PARENT_INDEX = "idx_transactions_parent"


def _upgrade_charge_links(conn: sa.engine.Connection) -> None:
    """Step ``charge_links``: add ``transactions.parent_transaction_id`` and its partial index, those missing."""
    if _PARENT_COLUMN not in _columns(conn, _TRANSACTIONS):
        conn.execute(sa.text(f"ALTER TABLE {_TRANSACTIONS} ADD COLUMN {_PARENT_COLUMN} INTEGER REFERENCES {_TRANSACTIONS} (id) DEFERRABLE INITIALLY DEFERRED"))
    conn.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {_PARENT_INDEX} ON {_TRANSACTIONS} ({_PARENT_COLUMN}) WHERE {_PARENT_COLUMN} IS NOT NULL"))


def _downgrade_charge_links(conn: sa.engine.Connection) -> None:
    """Step ``charge_links`` undone: drop the index, then the column, those still there."""
    conn.execute(sa.text(f"DROP INDEX IF EXISTS {_PARENT_INDEX}"))
    if _PARENT_COLUMN in _columns(conn, _TRANSACTIONS):
        conn.execute(sa.text(f"ALTER TABLE {_TRANSACTIONS} DROP COLUMN {_PARENT_COLUMN}"))


def upgrade() -> None:
    """The steps of the docstring, one line each."""
    conn = op.get_bind()
    _upgrade_asset_profile(conn)
    _upgrade_asset_profile_legacy_copy(conn)
    _upgrade_plugin_call_counters(conn)
    _upgrade_charge_links(conn)


def downgrade() -> None:
    """Back to 1.3, step by step, in the reverse order of ``upgrade``."""
    conn = op.get_bind()
    _downgrade_charge_links(conn)
    _downgrade_plugin_call_counters(conn)
    _downgrade_asset_profile_legacy_copy(conn)
    _downgrade_asset_profile(conn)
