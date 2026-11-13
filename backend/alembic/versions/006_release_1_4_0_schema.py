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

**Broker operating profile** (project 67, P1): ``brokers.operating_profile``, a nullable ``TEXT`` holding the broker's
operating profile as JSON — order modes and fees per currency, conversion mode, tax regime
(``schemas/broker_profile.BrokerOperatingProfile``). Every existing broker gets ``NULL``: no profile. Declared
``TEXT DEFAULT NULL``, as ``user_settings.ui_preferences`` in 005. The downgrade drops the column, and the profiles with it.
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


# Broker operating profile ─────────────────────────────────────────────────────────

_BROKER_PROFILE_COLUMN = "operating_profile"


def _upgrade_broker_operating_profile(conn: sa.engine.Connection) -> None:
    if _BROKER_PROFILE_COLUMN not in _columns(conn, "brokers"):
        conn.execute(sa.text(f"ALTER TABLE brokers ADD COLUMN {_BROKER_PROFILE_COLUMN} TEXT DEFAULT NULL"))


def _downgrade_broker_operating_profile(conn: sa.engine.Connection) -> None:
    if _BROKER_PROFILE_COLUMN in _columns(conn, "brokers"):
        conn.execute(sa.text(f"ALTER TABLE brokers DROP COLUMN {_BROKER_PROFILE_COLUMN}"))


# ───────────────────────────────────────────────────────────────────────────────────


def upgrade() -> None:
    """The steps of the docstring, one line each."""
    conn = op.get_bind()
    _upgrade_broker_operating_profile(conn)


def downgrade() -> None:
    """Back to 1.3, step by step, in the reverse order of ``upgrade``."""
    conn = op.get_bind()
    _downgrade_broker_operating_profile(conn)
