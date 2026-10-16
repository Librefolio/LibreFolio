"""Accounts: email addresses are unique regardless of case (release 1.3, workstream A, decision P18)

Revision ID: 009_email_unique_ignoring_case
Revises: 008_registration_invite_default
Create Date: 2026-10-16

Until now ``users.email`` was unique as written: ``alice@example.com`` and ``Alice@example.com`` could belong to two
accounts. From this revision a unique index on ``lower(email)`` refuses that. SQLite's built-in ``lower()`` folds A–Z
only, so letters outside ASCII compare as written: a documented limit (``user_service.email_fold()`` is the same rule).

The upgrade reads every account first and groups the addresses with that same fold. If two accounts share an address
apart from case, it stops before writing anything, naming the accounts by id and username, never by address (no
address goes in a log, workstream E's rule), and how to separate them: ``./dev.py user set-email``, which works on the
database as it is. Accounts are never merged. Otherwise it creates the index. The downgrade drops it.

The upgrade checks before it acts, so it can be run again.
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
