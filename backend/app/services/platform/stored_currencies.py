"""Stored currency codes that are not canonical ISO 4217 codes (E-19a, MF-SEC9b): found, summarized, logged, listed.

Since E-18 a request that writes a currency takes only an ISO 4217 alphabetic code, while older versions stored what
``Currency.validate_code`` accepted, as given: a numeric code or a currency name (``"978"``, ``"EURO"``). Such a row
reads as before, but saving it again after an edit is refused (422) until its code is corrected, and a restored backup
can bring such rows back at any time. This module finds them, read-only, on a ``sqlite3`` connection:

- the server's start logs one warning (``log_stored_currency_audit``, a step of ``app_lifespan``);
- ``./dev.py db currencies`` lists them (``main``; also ``python -m backend.app.services.platform.stored_currencies``).

A value is canonical when it is stored as ``iso_currency_code`` stores it (``is_canonical_iso_currency``): ``"EUR"`` is,
``"eur"`` is not (an exact SQL comparison misses it), nor ``"978"``. Each finding carries ``suggested_iso_currency``: the
code the value stands for, or None (no code, two codes, a subunit code). A BLOB in a column of text is a finding too,
shown as ``X'…'`` (E-19b1), and so is a text that is not UTF-8, read as its bytes (E-20): LibreFolio writes neither, but
a database put back by hand, another program or a damaged file can hold one.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from backend.app.logging_config import get_logger
from backend.app.schemas.common import is_canonical_iso_currency, shown_currency_text, suggested_iso_currency

logger = get_logger(__name__)


def _json_text(document: str, path: str) -> str:
    """The SQL of ``path`` in the JSON text column ``document``: NULL when the text is no JSON object."""
    return f"CASE WHEN json_valid({document}) AND json_type({document}) = 'object' THEN json_extract({document}, '{path}') END"


#: The steps of a route, never malformed for ``json_each``: an array, or an empty one.
_STEPS = "json_each(CASE WHEN json_valid(route.chain_steps) AND json_type(route.chain_steps) = 'array' THEN route.chain_steps ELSE '[]' END) AS step"


def _step_field(field: str) -> str:
    return f"SELECT CASE WHEN step.type = 'object' THEN json_extract(step.value, '$.{field}') END AS code, COUNT(*) FROM fx_conversion_routes AS route, {_STEPS} WHERE code IS NOT NULL GROUP BY code"


#: Where a currency code is stored, in the order of the findings, with the query of its distinct values and their rows:
#: ten columns, the two JSON texts that hold codes (the steps of a route, a provider's parameters), and the global default.
_PLACES: dict[str, str] = {
    "transactions.currency": "SELECT currency, COUNT(*) FROM transactions WHERE currency IS NOT NULL GROUP BY currency",
    "transactions.cost_basis_currency": "SELECT cost_basis_currency, COUNT(*) FROM transactions WHERE cost_basis_currency IS NOT NULL GROUP BY cost_basis_currency",
    "assets.currency": "SELECT currency, COUNT(*) FROM assets WHERE currency IS NOT NULL GROUP BY currency",
    "price_history.currency": "SELECT currency, COUNT(*) FROM price_history WHERE currency IS NOT NULL GROUP BY currency",
    "asset_events.currency": "SELECT currency, COUNT(*) FROM asset_events WHERE currency IS NOT NULL GROUP BY currency",
    "fx_rates.base": "SELECT base, COUNT(*) FROM fx_rates WHERE base IS NOT NULL GROUP BY base",
    "fx_rates.quote": "SELECT quote, COUNT(*) FROM fx_rates WHERE quote IS NOT NULL GROUP BY quote",
    "fx_conversion_routes.base": "SELECT base, COUNT(*) FROM fx_conversion_routes WHERE base IS NOT NULL GROUP BY base",
    "fx_conversion_routes.quote": "SELECT quote, COUNT(*) FROM fx_conversion_routes WHERE quote IS NOT NULL GROUP BY quote",
    "fx_conversion_routes.chain_steps.from": _step_field("from"),
    "fx_conversion_routes.chain_steps.to": _step_field("to"),
    "asset_provider_assignments.provider_params.currency": f"SELECT {_json_text('provider_params', '$.currency')} AS code, COUNT(*) FROM asset_provider_assignments WHERE code IS NOT NULL GROUP BY code",
    "user_settings.base_currency": "SELECT base_currency, COUNT(*) FROM user_settings WHERE base_currency IS NOT NULL GROUP BY base_currency",
    "global_settings.default_currency": "SELECT value, COUNT(*) FROM global_settings WHERE key = 'default_currency' AND value IS NOT NULL GROUP BY value",
}

STORED_CURRENCY_PLACES: tuple[str, ...] = tuple(_PLACES)


@dataclass(frozen=True)
class StoredCurrencyFinding:
    """A stored currency value that is not a canonical ISO 4217 code: where, what, in how many rows, and what it means."""

    place: str
    value: str
    rows: int
    suggestion: Optional[str]


def _as_text(value: Any) -> str:
    """A stored value as text: a JSON number or object read out of a parameter is shown as JSON; a BLOB, which a column of
    text can hold (a hand-made or damaged database, a crafted backup), or a text that is not UTF-8, which the audit reads
    as its bytes (E-20), in SQLite's own notation, ``X'455552'``: never a code, so always a finding, never a crash of the
    check (E-19b1)."""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return f"X'{value.hex().upper()}'"
    return json.dumps(value)


def _lenient_text(data: bytes) -> str | bytes:
    """A stored text as ``str`` when it is UTF-8, else its bytes (E-20): on ``sqlite3``'s default ``text_factory`` a
    text that is not UTF-8 raises an ``OperationalError`` quoting it, which would end the check on one value."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data


def find_stored_currency_findings(connection: sqlite3.Connection) -> list[StoredCurrencyFinding]:
    """Every stored currency value that is not a canonical ISO 4217 code, read-only: one finding per place and value.

    In the order of ``STORED_CURRENCY_PLACES``, then the most rows first, then the value. NULLs and JSON texts that are
    not JSON are left out. A place whose table the database lacks (an older schema) is skipped. The reads go through
    ``_lenient_text``, so a text that is not UTF-8 is a finding, ``X'…'``, and the connection's own ``text_factory`` is
    put back when the audit returns or raises (E-20).
    """
    findings: list[StoredCurrencyFinding] = []
    previous_text_factory = connection.text_factory
    connection.text_factory = _lenient_text
    try:
        for place, query in _PLACES.items():
            try:
                rows = connection.execute(query).fetchall()
            except sqlite3.OperationalError as error:
                if "no such table" not in str(error) and "no such column" not in str(error):
                    raise
                continue
            found = [StoredCurrencyFinding(place, text, count, suggested_iso_currency(text)) for raw, count in rows if not is_canonical_iso_currency(text := _as_text(raw))]
            findings.extend(sorted(found, key=lambda finding: (-finding.rows, finding.value)))
    finally:
        connection.text_factory = previous_text_factory
    return findings


def _finding_text(finding: StoredCurrencyFinding) -> str:
    return f"{finding.place} {shown_currency_text(finding.value)!r} ×{finding.rows} → {finding.suggestion or 'no ISO code'}"


def summarize_findings(findings: list[StoredCurrencyFinding], limit: int = 10) -> str:
    """One line for a log: ``place 'value' ×rows → CODE`` per finding (``→ no ISO code``), ``; ``-joined, at most ``limit``."""
    if not findings:
        return ""
    parts = [_finding_text(finding) for finding in findings[:limit]]
    if len(findings) > limit:
        parts.append(f"and {len(findings) - limit} more")
    return "; ".join(parts)


def _read_only(path: Path) -> sqlite3.Connection:
    """The database at ``path``, opened for reading only: a missing file is an error, never a new database.

    ``mode=rw`` with ``PRAGMA query_only``, not ``mode=ro``: on a WAL database (LibreFolio's) with no other connection,
    a ``mode=ro`` connection creates the ``-wal`` and ``-shm`` files and cannot remove them when it closes, so a check
    of a stopped server's database would leave them behind; this one refuses every write and closes as any reader does.
    Through a ``file:`` URI made by ``Path.as_uri()``, which escapes a space or a ``#`` in the path (``data dir #1``):
    pasted as it is, a ``#`` would start the URI's fragment. ``trusted_schema`` off before anything else (H's review of
    E-19a), as on every connection to a backup's copy: the database may come from a restore, and no function its schema
    names runs from a view, a trigger or an index while the audit reads.
    """
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=rw", uri=True)
    try:
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA query_only = ON")
    except sqlite3.Error:
        connection.close()
        raise
    return connection


def _configured_path() -> Optional[Path]:
    from backend.app.db.post_migration import configured_sqlite_path  # noqa: PLC0415 — the settings, only when asked

    return configured_sqlite_path()


def log_stored_currency_audit(db_path: Optional[Path] = None) -> Optional[list[StoredCurrencyFinding]]:
    """The startup's check (E-19a): one warning when stored currency codes are not ISO 4217 codes, nothing when clean.

    ``db_path``: the configured SQLite database when None. Returns the findings, or None when the check could not run:
    it never raises, and the server starts anyway.
    """
    try:
        path = db_path if db_path is not None else _configured_path()
        if path is None:
            return None
        with closing(_read_only(path)) as connection:
            findings = find_stored_currency_findings(connection)
    except Exception as error:  # noqa: BLE001 — the start never stops on a check
        # The class and SQLite's error name only: a message may quote stored data, as sqlite3's did for a text that is
        # not UTF-8 until E-20 (E-19b1)
        logger.warning("Stored currency codes could not be checked", error=type(error).__name__, sqlite_error=getattr(error, "sqlite_errorname", None))
        return None
    if findings:
        logger.warning(
            "Stored currency codes that are not ISO 4217 codes: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them)",
            findings=len(findings),
            summary=summarize_findings(findings),
        )
    return findings


def main(argv: Optional[list[str]] = None) -> int:
    """List the stored currency codes that are not ISO 4217 codes. Exit 0: none; 1: some; 2: the database cannot be read."""
    parser = argparse.ArgumentParser(prog="python -m backend.app.services.platform.stored_currencies", description="List the stored currency codes that are not ISO 4217 alphabetic codes (read-only).")
    parser.add_argument("--db-file", type=Path, default=None, help="the SQLite database (default: the configured one)")
    args = parser.parse_args(argv)
    path = args.db_file if args.db_file is not None else _configured_path()
    if path is None:
        print("No SQLite database is configured", file=sys.stderr)
        return 2
    try:
        with closing(_read_only(path)) as connection:
            findings = find_stored_currency_findings(connection)
    except (sqlite3.Error, OSError) as error:
        print(f"Cannot read {path}: {error}", file=sys.stderr)
        return 2
    if not findings:
        print("No stored currency code needs attention: every one is an ISO 4217 alphabetic code.")
        return 0
    print(f"{len(findings)} stored currency value(s) are not ISO 4217 alphabetic codes; an edit of their rows is refused until they are corrected:")
    for finding in findings:
        print(f"  {finding.place:<52} {shown_currency_text(finding.value)!r:<20} {finding.rows:>8} row(s)  → {finding.suggestion or '—'}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
