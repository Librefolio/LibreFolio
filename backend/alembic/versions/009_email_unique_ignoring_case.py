"""Release 1.3: email addresses unique regardless of case (P18); the decimals of C-97 need no DDL

Revision ID: 009_email_unique_ignoring_case
Revises: 008_registration_invite_default
Create Date: 2026-10-16

1. Email addresses are unique regardless of case (workstream A, decision P18).

   Until now ``users.email`` was unique as written: ``alice@example.com`` and ``Alice@example.com`` could belong to
   two accounts. From this revision a unique index on ``lower(email)`` refuses that. SQLite's built-in ``lower()``
   folds A–Z only, so letters outside ASCII compare as written: a documented limit (``user_service.email_fold()`` is
   the same rule).

   The upgrade reads every account first and groups the addresses with that same fold. If two accounts share an
   address apart from case, it stops before writing anything, naming the accounts by id and username, never by
   address (no address goes in a log, workstream E's rule), and how to separate them: ``./dev.py user set-email``,
   which works on the database as it is. Accounts are never merged. Otherwise it creates the index. The downgrade
   drops it.

   The upgrade checks before it acts, so it can be run again.

2. Quantities keep 10 decimal places and prices 12 (C-97, issue #43): no DDL, no data step.

   ``transactions.quantity`` was declared ``NUMERIC(18, 6)``, and so were the per-unit cost
   basis ``transactions.cost_basis_override`` (a price: it is multiplied by the quantity)
   and the ``open``, ``high``, ``low``, ``close`` and ``adjusted_close`` of
   ``price_history``. Since 16/10/2026 the declarations in 001_initial read
   ``NUMERIC(22, 10)`` for the quantity and ``NUMERIC(24, 12)`` for the prices and the cost
   basis; released SQLite databases keep their 18, 6, and that is deliberate: the
   reasoning of 002 and 004 (``VARCHAR(14)``).

   SQLite stores these values as a double (REAL; INTEGER for a whole value) whatever the
   declaration says: a quantity of ``0.12345678`` has always been saved whole. The six
   decimals were applied in Python: by the model when it read the value back
   (``Numeric(18, 6)`` formats it with ``'%.6f'``), and by ``truncate_priceHistory`` when
   a price was written. Both change with the code. The model now reads quantities and
   prices through ``RealDecimal`` (``db/real_decimal.py``), which gives back the decimal
   that was written, up to 15 significant digits, what a double keeps exactly. The input
   refuses what the column could not give back (``db/precision.decimal_limit_issue``),
   and provider prices are truncated to 12 decimals and 15 significant digits.
   Rebuilding ``transactions`` and ``price_history`` on every installation to change a
   number the engine ignores would trade a real risk for no effect, so this migration
   performs no DDL for it.

   Nothing stored is rewritten either (the developer's decision, 16/10/2026). A quantity
   saved with more than six decimals, by 1.1, an import or the API, now reads back with
   its digits, up to ten. A price keeps the six decimals it was truncated to when it was
   written. A per-unit cost basis saved with more than six decimals (Auto computes it as a
   total divided by the quantity) now reads back with up to twelve. A value with six
   decimals or fewer reads back exactly as before, ``10.000000`` included. On the
   developer's demo data every stored quantity and price reads back identical.
"""

import string
from collections import defaultdict
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_email_unique_ignoring_case"
down_revision: Union[str, Sequence[str], None] = "008_registration_invite_default"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ux_users_email_lower"
#: SQLite's lower(): A–Z to a–z, nothing else. Written here, not imported: a migration keeps the rule of its day.
_FOLD = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


def _duplicates(rows) -> list[list[tuple[int, str]]]:
    """The groups of accounts whose addresses are the same once folded, more than one account each, by id."""
    groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for account_id, username, email in rows:
        groups[email.translate(_FOLD)].append((account_id, username))
    return [sorted(group) for group in groups.values() if len(group) > 1]


def upgrade() -> None:
    """Stop, naming the accounts, if two share an address apart from case; otherwise create the unique index."""
    bind = op.get_bind()
    duplicates = _duplicates(bind.execute(sa.text("SELECT id, username, email FROM users")).fetchall())
    if duplicates:
        groups = "; ".join(", ".join(f"#{account_id} {username!r}" for account_id, username in group) for group in sorted(duplicates))
        raise RuntimeError(
            "Email addresses must be unique regardless of case (release 1.3), and these accounts share one apart from "
            f"upper and lower case: {groups}. Give all but one account of each group another address with "
            "`./dev.py user set-email <username> <address>` (in Docker, with the container stopped: `docker compose run "
            "--rm librefolio python dev.py user set-email <username> <address>`), then start LibreFolio again. No account "
            "was changed."
        )
    bind.execute(sa.text(f"CREATE UNIQUE INDEX IF NOT EXISTS {_INDEX} ON users (lower(email))"))


def downgrade() -> None:
    """Drop the index: addresses are unique as written again, as before release 1.3."""
    op.get_bind().execute(sa.text(f"DROP INDEX IF EXISTS {_INDEX}"))
