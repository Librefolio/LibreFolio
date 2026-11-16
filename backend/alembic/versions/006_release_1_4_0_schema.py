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
"""

from typing import Sequence, Union

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


def upgrade() -> None:
    """The steps of the docstring, one line each."""
    conn = op.get_bind()
    _upgrade_asset_profile(conn)


def downgrade() -> None:
    """Back to 1.3, step by step, in the reverse order of ``upgrade``."""
    conn = op.get_bind()
    _downgrade_asset_profile(conn)
