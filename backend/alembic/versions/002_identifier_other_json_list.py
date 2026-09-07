"""identifier_other scalar -> JSON list of soft identifiers

Revision ID: 002_identifier_other_json_list
Revises: 001_initial
Create Date: 2026-07-28

Valid from 2026-07-28 and the current head of the schema — it stays the latest applied
revision (the schema in force today) until a future 003 supersedes it.

``Asset.identifier_other`` changes from a single scalar string to a JSON list of soft
identifiers (technical codes + soft broker labels), additive across imports. This is a
**data-only** migration: on SQLite the column keeps its ``VARCHAR`` declaration (length
is advisory and JSON is stored as TEXT), so we only rewrite the existing values from a
bare scalar ``"x"`` into a one-element JSON array ``["x"]``. The statements are guarded
by ``substr(...,1,1)`` so re-running is a no-op (already-``[`` values are left alone).

NOTE: on a future Postgres port the column type must be changed explicitly (e.g. to
``JSONB``); on SQLite no type change is required.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_identifier_other_json_list"
down_revision: Union[str, Sequence[str], None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Wrap each existing scalar identifier_other into a one-element JSON array."""
    conn = op.get_bind()
    # Blank strings become NULL (never store an empty scalar as a list).
    conn.execute(sa.text("UPDATE assets SET identifier_other = NULL WHERE identifier_other IS NOT NULL AND trim(identifier_other) = ''"))
    # Wrap bare scalars into a JSON array; skip values that are already JSON arrays.
    conn.execute(sa.text("UPDATE assets SET identifier_other = json_array(identifier_other) WHERE identifier_other IS NOT NULL AND substr(identifier_other, 1, 1) != '['"))


def downgrade() -> None:
    """Unwrap the JSON list back to its first element (extra soft identifiers are dropped)."""
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE assets SET identifier_other = json_extract(identifier_other, '$[0]') WHERE identifier_other IS NOT NULL AND substr(identifier_other, 1, 1) = '['"))
