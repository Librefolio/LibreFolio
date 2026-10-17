"""
The stored currency audit — lot E-19a (workstream E), item 4.

Before E-18 the write paths validated a currency with ``Currency.validate_code``, which also takes an ISO name or a
numeric code and stores it as given. So a database can hold ``EURO``, ``978``, ``US DOLLAR``, ``YEN`` or ``eur`` where an
ISO 4217 alphabetic code belongs. E-18 stops new ones; E-19a reports those already stored, without changing anything.

The new module ``backend.app.services.platform.stored_currencies``, as the release coordinator decided on 17/10 (the
fourteenth place, ``global_settings.default_currency``, added the same day):

- ``STORED_CURRENCY_PLACES``: the 14 places a currency code is stored, in this order — ``transactions.currency``,
  ``transactions.cost_basis_currency``, ``assets.currency``, ``price_history.currency``, ``asset_events.currency``,
  ``fx_rates.base``, ``fx_rates.quote``, ``fx_conversion_routes.base``, ``fx_conversion_routes.quote``, the ``from``
  and ``to`` of each step of ``fx_conversion_routes.chain_steps`` (a JSON text array of
  ``{"from", "to", "provider"}``), the ``currency`` of ``asset_provider_assignments.provider_params`` (a JSON text
  object), ``user_settings.base_currency`` and the ``value`` of the ``global_settings`` row whose key is
  ``default_currency`` (plain text, not JSON).
- ``StoredCurrencyFinding``: a frozen dataclass ``place``, ``value``, ``rows``, ``suggestion`` (the
  ``suggested_iso_currency`` of the value).
- ``find_stored_currency_findings(connection)``: read-only over a ``sqlite3`` connection. One finding per place and
  stored value that is not already canonical — ``iso_currency_code(value) == value`` —, ``rows`` the number of rows (or
  JSON entries) holding it. NULLs are ignored, malformed JSON is ignored without raising. Sorted by place (the order
  above), then rows descending, then value.
- ``summarize_findings(findings, limit=10)``: ``""`` for none; else ``place 'value' ×rows → CODE`` (``→ no ISO code``
  without a suggestion) joined by ``; ``, ending ``and N more`` past ``limit``.
- ``log_stored_currency_audit(db_path=None)``: the configured database
  (``backend.app.db.post_migration.configured_sqlite_path()``) when None, opened read-only. Findings: one WARNING whose
  event contains ``ISO 4217``, with ``findings`` (the count) and ``summary``, and the list returned. Clean: nothing at
  warning level, ``[]``. A missing or non-database file: never raises, one warning whose event contains ``could not``,
  ``None``.
- ``main(argv=None) -> int`` with ``--db-file PATH``, also ``python -m``: one line per finding naming its place, value,
  rows and suggestion (``—`` without one), exit 1; ``No stored currency code`` and exit 0 when clean; exit 2 with a
  message on stderr when the file cannot be read.

Each database is a file in ``tmp_path``: the app tables are created with ``SQLModel.metadata.create_all`` on a sync
engine, then filled with raw ``sqlite3`` SQL, so that no validator runs and every lenient value lands as an older version
left it. The expected findings are written out, not computed by the module under test. Every call must leave the
database file as it was (its sha256, and the names in its folder).

Every test here is RED (``# red until E-19a``): the module does not exist yet. It is looked up inside each test, so the
file collects and each test fails on its own. The one GUARD (green today) checks this file's own database builder, so a
red can only be about the product. Two tests rest on an assumption the contract does not state (valid JSON of another
shape, a path with a space and a ``#``): their docstrings say so.

Lot E-19b1.3 (B's review of E-19b1) adds two rules, RED until it (``# red until E-19b1.3``):

- A currency stored as a BLOB is a finding. A TEXT column keeps a value bound as bytes as a BLOB, and a restored archive
  can carry one. Its value is SQLite's ``quote()`` of it, ``X'`` and its bytes in upper-case hex and ``'`` (the bytes of
  ``EUR``: ``X'455552'``): never canonical, never a suggestion. Today ``_as_text`` gives the bytes to ``json.dumps``,
  whose ``TypeError`` ends the whole audit: no finding at all, the startup's check «could not be checked», and
  ``./dev.py db currencies`` ends with a traceback (SCA-015, SCA-035, SCA-044, SCA-045).
- The warning of a check that fails names the class of the error (and SQLite's error name), never the error's text: a
  currency stored as TEXT that is not UTF-8 makes ``sqlite3`` raise an ``OperationalError`` whose message quotes it, and
  after a restore those are an archive's bytes (SCA-036).

The preconditions of these tests (a BLOB, a text that is not UTF-8) are read by SQL, never through the audit.

Pure: no server, no network, no shared database; only files of ``tmp_path`` (and subprocess runs of the module).
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, NoReturn, Optional

import pytest
from sqlalchemy import create_engine
from sqlmodel import SQLModel
from structlog.testing import capture_logs

import backend.app.db.models  # noqa: F401 — registers the app tables on SQLModel.metadata
from backend.app.db import post_migration

AUDIT_MODULE = "backend.app.services.platform.stored_currencies"
WORKTREE_ROOT = Path(__file__).resolve().parents[3]

PLACES = (
    "transactions.currency",
    "transactions.cost_basis_currency",
    "assets.currency",
    "price_history.currency",
    "asset_events.currency",
    "fx_rates.base",
    "fx_rates.quote",
    "fx_conversion_routes.base",
    "fx_conversion_routes.quote",
    "fx_conversion_routes.chain_steps.from",
    "fx_conversion_routes.chain_steps.to",
    "asset_provider_assignments.provider_params.currency",
    "user_settings.base_currency",
    "global_settings.default_currency",
)

#: A finding as this file compares it: (place, value, rows, suggestion).
Finding = tuple[str, str, int, Optional[str]]

WARNING_LEVELS = frozenset({"warning", "warn"})
WARNING_OR_ABOVE = WARNING_LEVELS | {"error", "exception", "critical", "fatal"}

#: The lot that adds what the audit does with a value it cannot read as text (B's review of E-19b1), and why its reds fail.
READ_LOT = "E-19b1.3"
BLOB_RED = "_as_text does not handle a BLOB yet"
LOG_RED = "the failure log still carries the error's text"

# =============================================================================
# THE MODULE UNDER TEST, LOOKED UP WHEN A TEST RUNS (absent before E-19a)
# =============================================================================


def _red(what: str, lot: str = "E-19a") -> NoReturn:
    pytest.fail(f"red until {lot}: {what}", pytrace=False)


def _audit_module() -> ModuleType:
    """The new module, or the test fails. An import error *inside* it is not swallowed."""
    try:
        return importlib.import_module(AUDIT_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != AUDIT_MODULE:
            raise
        _red(f"{AUDIT_MODULE} does not exist yet")


def _audit(name: str) -> Any:
    """A symbol of the new module, or the test fails."""
    found = getattr(_audit_module(), name, None)
    if found is None:
        _red(f"{AUDIT_MODULE}.{name} does not exist yet")
    return found


def _as_tuples(findings: Any) -> list[Finding]:
    """The findings as ``(place, value, rows, suggestion)``, each checked to be a ``StoredCurrencyFinding``."""
    finding_class = _audit("StoredCurrencyFinding")
    assert isinstance(findings, list), f"the findings must be a list, got {type(findings).__name__}"
    assert all(isinstance(item, finding_class) for item in findings), f"every finding must be a StoredCurrencyFinding: {findings!r}"
    return [(item.place, item.value, item.rows, item.suggestion) for item in findings]


# =============================================================================
# THE DATABASES: the app schema, then raw SQL (no validator runs)
# =============================================================================

STAMP = "2024-01-01 00:00:00.000000"
DAY_1, DAY_2 = "2024-01-02", "2024-01-03"


def _route(*steps: tuple[str, str, str]) -> str:
    """The JSON text ``create_routes_bulk`` writes for a chain: ``[{"from": …, "to": …, "provider": …}, …]``."""
    return json.dumps([{"from": source, "to": target, "provider": provider} for source, target, provider in steps])


def _insert(connection: sqlite3.Connection, table: str, rows: Iterable[Mapping[str, Any]]) -> None:
    for row in rows:
        columns = ", ".join(f'"{column}"' for column in row)
        marks = ", ".join("?" for _ in row)
        connection.execute(f'INSERT INTO "{table}" ({columns}) VALUES ({marks})', tuple(row.values()))


def _users(count: int) -> list[dict[str, Any]]:
    base = {"hashed_password": "x", "is_active": 1, "is_superuser": 0, "login_count": 0, "donation_popup_logins_since_shown": 0, "session_version": 0, "created_at": STAMP, "updated_at": STAMP}
    return [{"id": user_id, "username": f"audit_user_{user_id}", "email": f"audit_user_{user_id}@example.test", **base} for user_id in range(1, count + 1)]


def _assets(currencies: Sequence[str | bytes]) -> list[dict[str, Any]]:
    """One asset per currency, from asset 1: a ``bytes`` currency is bound, so stored, as a BLOB."""
    base = {"asset_type": "OTHER", "active": 1, "is_benchmark": 0, "quote_base_quantity": 1, "created_at": STAMP, "updated_at": STAMP}
    return [{"id": asset_id, "display_name": f"Audit asset {asset_id}", "currency": currency, **base} for asset_id, currency in enumerate(currencies, start=1)]


def _transactions(rows: Sequence[tuple[Optional[str], Optional[str]]]) -> list[dict[str, Any]]:
    """Cash only (``(currency, None)``), or a cost basis on asset 1 (``(currency, cost basis currency)``)."""
    built = []
    for index, (currency, cost_currency) in enumerate(rows, start=1):
        row = {"broker_id": 1, "type": "DEPOSIT", "date": f"2024-02-{index:02d}", "quantity": 0, "amount": 0 if currency is None else 10, "currency": currency, "created_at": STAMP, "updated_at": STAMP}
        if cost_currency is not None:
            row.update(type="ADJUSTMENT", asset_id=1, quantity=1, cost_basis_override=1.5, cost_basis_currency=cost_currency)
        built.append(row)
    return built


def _price_history(rows: Sequence[tuple[int, str, str]]) -> list[dict[str, Any]]:
    return [{"asset_id": asset_id, "date": day, "close": 10, "currency": currency, "source_plugin_key": "mockprov", "fetched_at": STAMP} for asset_id, day, currency in rows]


def _asset_events(rows: Sequence[tuple[int, str]]) -> list[dict[str, Any]]:
    return [{"asset_id": asset_id, "date": f"2024-03-{index:02d}", "type": "DIVIDEND", "value": 1.5, "currency": currency, "created_at": STAMP, "updated_at": STAMP} for index, (asset_id, currency) in enumerate(rows, start=1)]


def _fx_rates(rows: Sequence[tuple[str, str, str]]) -> list[dict[str, Any]]:
    """``(date, base, quote)``: the CHECK wants ``base < quote`` (binary order: a digit sorts before every letter)."""
    return [{"date": day, "base": base, "quote": quote, "rate": 1.1, "source": "ECB", "fetched_at": STAMP} for day, base, quote in rows]


def _routes(rows: Sequence[tuple[str, str, int, str]]) -> list[dict[str, Any]]:
    """``(base, quote, priority, chain_steps)``: ``base < quote``, and (base, quote, priority) unique."""
    return [{"base": base, "quote": quote, "priority": priority, "chain_steps": steps, "created_at": STAMP, "updated_at": STAMP} for base, quote, priority, steps in rows]


def _assignments(params: Sequence[Optional[str]]) -> list[dict[str, Any]]:
    """One assignment per asset, from asset 1: ``provider_params`` as stored (JSON text, malformed text or NULL)."""
    base = {"provider_code": "cssscraper", "identifier": "https://example.test/price", "identifier_type": "URL", "created_at": STAMP, "updated_at": STAMP}
    return [{"asset_id": asset_id, "provider_params": text, **base} for asset_id, text in enumerate(params, start=1)]


def _user_settings(currencies: Sequence[str]) -> list[dict[str, Any]]:
    """One row per user, from user 1."""
    return [{"user_id": user_id, "base_currency": currency, "language": "en", "theme": "auto", "created_at": STAMP, "updated_at": STAMP} for user_id, currency in enumerate(currencies, start=1)]


def _global_settings(values: Mapping[str, str]) -> list[dict[str, Any]]:
    return [{"key": key, "value": value, "value_type": "str", "description": None, "updated_at": STAMP} for key, value in values.items()]


def _build(path: Path, tables: Mapping[str, Sequence[Mapping[str, Any]]]) -> Path:
    """A database file at ``path``: the app tables (``create_all``), then ``tables`` by raw SQL, in order. A broker
    always exists (``transactions.broker_id`` points at it)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")
    try:
        SQLModel.metadata.create_all(engine)
    finally:
        engine.dispose()
    connection = sqlite3.connect(path)
    try:
        _insert(connection, "brokers", [{"id": 1, "name": "Audit broker", "allow_cash_overdraft": 0, "allow_asset_shorting": 0, "is_active": 1, "created_at": STAMP, "updated_at": STAMP}])
        for table, rows in tables.items():
            _insert(connection, table, rows)
        connection.commit()
    finally:
        connection.close()
    return path


#: The main database: lenient values in every place, canonical ones beside them, NULLs, malformed JSON.
MAIN_TABLES: dict[str, list[dict[str, Any]]] = {
    "users": _users(4),
    "assets": _assets(["EUR", "EUR", "840", "840", "usd", "CHF", "GBP"]),
    "transactions": _transactions(
        [
            ("978", None),
            ("978", None),
            ("978", "EURO"),
            ("US DOLLAR", None),
            ("US DOLLAR", "EURO"),
            ("eur", None),
            ("EUR", "Bolívar Soberano"),
            ("EUR", "YEN"),
            ("USD", "GBP"),
            (None, None),
            (None, None),
        ]
    ),
    "price_history": _price_history([(1, DAY_1, "EUR"), (1, DAY_2, "EUR"), (2, DAY_1, "GBX"), (3, DAY_1, "SOL"), (4, DAY_1, "EUR ")]),
    "asset_events": _asset_events([(1, "won"), (2, "won"), (3, "999"), (1, "EUR")]),
    "fx_rates": _fx_rates([(DAY_1, "978", "USD"), (DAY_2, "978", "USD"), (DAY_1, "EUR", "USD"), (DAY_1, "826", "978"), (DAY_1, "CHF", "EURO")]),
    "fx_conversion_routes": _routes(
        [
            ("978", "USD", 1, _route(("978", "USD", "ECB"))),
            ("CHF", "USD", 1, _route(("CHF", "EUR", "ECB"), ("EUR", "USD", "ECB"))),
            ("RON", "USD", 2, _route(("RON", "978", "ECB"), ("978", "USD", "FED"))),
            ("EUR", "GBP", 1, "not json"),
            ("826", "SEK", 1, _route(("826", "SEK", "BOE"))),
            ("EUR", "Yen", 1, _route(("EUR", "Yen", "ECB"))),
        ]
    ),
    "asset_provider_assignments": _assignments(
        [
            '{"currency": "EURO", "selector": ".price"}',
            "{}",
            None,
            "not json",
            '{"currency": "EUR"}',
            '{"currency": "lek"}',
            '{"currency": "EURO"}',
        ]
    ),
    "user_settings": _user_settings(["EUR", "978", "978", "eur"]),
    "global_settings": _global_settings({"default_currency": "EURO", "default_language": "978", "default_theme": "auto"}),
}

#: What the main database holds that is no canonical code: by place (the order above), then rows descending, then value.
MAIN_FINDINGS: list[Finding] = [
    ("transactions.currency", "978", 3, "EUR"),
    ("transactions.currency", "US DOLLAR", 2, "USD"),
    ("transactions.currency", "eur", 1, "EUR"),
    ("transactions.cost_basis_currency", "EURO", 2, "EUR"),
    ("transactions.cost_basis_currency", "Bolívar Soberano", 1, None),
    ("transactions.cost_basis_currency", "YEN", 1, "JPY"),
    ("assets.currency", "840", 2, "USD"),
    ("assets.currency", "usd", 1, "USD"),
    ("price_history.currency", "EUR ", 1, "EUR"),
    ("price_history.currency", "GBX", 1, None),
    ("price_history.currency", "SOL", 1, "PEN"),
    ("asset_events.currency", "won", 2, "KRW"),
    ("asset_events.currency", "999", 1, "XXX"),
    ("fx_rates.base", "978", 2, "EUR"),
    ("fx_rates.base", "826", 1, "GBP"),
    ("fx_rates.quote", "978", 1, "EUR"),
    ("fx_rates.quote", "EURO", 1, "EUR"),
    ("fx_conversion_routes.base", "826", 1, "GBP"),
    ("fx_conversion_routes.base", "978", 1, "EUR"),
    ("fx_conversion_routes.quote", "Yen", 1, "JPY"),
    ("fx_conversion_routes.chain_steps.from", "978", 2, "EUR"),
    ("fx_conversion_routes.chain_steps.from", "826", 1, "GBP"),
    ("fx_conversion_routes.chain_steps.to", "978", 1, "EUR"),
    ("fx_conversion_routes.chain_steps.to", "Yen", 1, "JPY"),
    ("asset_provider_assignments.provider_params.currency", "EURO", 2, "EUR"),
    ("asset_provider_assignments.provider_params.currency", "lek", 1, "ALL"),
    ("user_settings.base_currency", "978", 2, "EUR"),
    ("user_settings.base_currency", "eur", 1, "EUR"),
    ("global_settings.default_currency", "EURO", 1, "EUR"),
]

#: A clean database: canonical codes in every place, NULLs, malformed JSON, an empty ``provider_params``, and a global
#: setting that is no currency holding ``978``.
CLEAN_TABLES: dict[str, list[dict[str, Any]]] = {
    "users": _users(2),
    "assets": _assets(["EUR", "USD", "EUR", "CHF"]),
    "transactions": _transactions([("EUR", None), ("USD", "EUR"), (None, None)]),
    "price_history": _price_history([(1, DAY_1, "EUR")]),
    "asset_events": _asset_events([(1, "USD")]),
    "fx_rates": _fx_rates([(DAY_1, "EUR", "USD")]),
    "fx_conversion_routes": _routes(
        [
            ("EUR", "USD", 1, _route(("EUR", "USD", "ECB"))),
            ("CHF", "USD", 1, _route(("CHF", "EUR", "ECB"), ("EUR", "USD", "ECB"))),
            ("EUR", "GBP", 1, "not json"),
        ]
    ),
    "asset_provider_assignments": _assignments(['{"currency": "EUR", "selector": ".price"}', "{}", None, "not json"]),
    "user_settings": _user_settings(["EUR", "USD"]),
    "global_settings": _global_settings({"default_currency": "EUR", "default_language": "978", "default_theme": "auto"}),
}

#: A small database for the command line: four findings, one without a suggestion, in four places.
CLI_TABLES: dict[str, list[dict[str, Any]]] = {
    "users": _users(1),
    "assets": _assets(["BTC", "EUR"]),
    "transactions": _transactions([("978", None), ("978", None), ("EUR", None)]),
    "user_settings": _user_settings(["eur"]),
    "global_settings": _global_settings({"default_currency": "EURO", "default_language": "978"}),
}
CLI_FINDINGS: list[Finding] = [
    ("transactions.currency", "978", 2, "EUR"),
    ("assets.currency", "BTC", 1, None),
    ("user_settings.base_currency", "eur", 1, "EUR"),
    ("global_settings.default_currency", "EURO", 1, "EUR"),
]

#: E-19b1.3: currencies stored as BLOBs, as a crafted archive can carry them: the bytes of ``EUR`` in two assets and
#: ``00 FF`` in one, beside the text ``EUR``; ordinary findings in a place before theirs (``transactions.currency``) and
#: in one after it (``user_settings.base_currency``).
BLOB_TABLES: dict[str, list[dict[str, Any]]] = {
    "users": _users(1),
    "assets": _assets(["EUR", b"EUR", b"\x00\xff", b"EUR"]),
    "transactions": _transactions([("978", None), ("978", None), ("EUR", None)]),
    "user_settings": _user_settings(["978"]),
}
#: What it holds that is no canonical code: a BLOB as SQLite's ``quote()`` writes it, without a suggestion.
BLOB_FINDINGS: list[Finding] = [
    ("transactions.currency", "978", 2, "EUR"),
    ("assets.currency", "X'455552'", 2, None),
    ("assets.currency", "X'00FF'", 1, None),
    ("user_settings.base_currency", "978", 1, "EUR"),
]
#: How the assets of ``BLOB_TABLES`` store their currency, read by SQL: (id, storage class, its bytes in hex).
BLOB_STORAGE = [(1, "text", "455552"), (2, "blob", "455552"), (3, "blob", "00FF"), (4, "blob", "455552")]

#: E-19b1.3: a currency stored as TEXT whose bytes are not UTF-8 (a ``CAST`` of bytes writes one: SQLite checks no
#: encoding). ``sqlite3`` cannot read it back as text, and the message of its ``OperationalError`` quotes it, the byte
#: replaced by U+FFFD: «Could not decode to UTF-8 column 'currency' with text '…'».
NOT_UTF8_MARKER = "sca-stored-text"
NOT_UTF8 = b"E\xffR " + NOT_UTF8_MARKER.encode()
#: What no line of the log may hold of that error: the stored text (its ASCII part; as the message quotes it) and the
#: words of the message.
NOT_UTF8_FRAGMENTS = (NOT_UTF8_MARKER, "E\ufffdR", "\ufffd", "Could not decode", "with text")


def _fingerprint(path: Path) -> tuple[Optional[str], tuple[str, ...]]:
    """The sha256 of a file (None when absent) and the names in its folder: a read-only audit changes neither."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    names = tuple(sorted(item.name for item in path.parent.iterdir())) if path.parent.exists() else ()
    return digest, names


def _find(path: Path) -> list[Finding]:
    """``find_stored_currency_findings`` on a read-write connection to ``path``: it changes no row, leaves no
    transaction open, and the file and its folder are as they were."""
    find = _audit("find_stored_currency_findings")
    before = _fingerprint(path)
    connection = sqlite3.connect(path)
    try:
        found = find(connection)
        state = (connection.total_changes, connection.in_transaction)
    finally:
        connection.close()
    assert state == (0, False), f"a read-only audit changes no row and leaves no transaction open on its connection: (total_changes, in_transaction) = {state}"
    assert _fingerprint(path) == before, "the audit changed the database file or its folder"
    return _as_tuples(found)


def _reader(path: Path) -> sqlite3.Connection:
    """A connection that reads the file at ``path`` and leaves nothing beside it. Read-write with ``query_only``, as the
    audit's own reader, never ``mode=ro``: on these WAL databases a ``mode=ro`` connection leaves the ``-wal`` and
    ``-shm`` files behind, and a fingerprint taken after it would no longer be the database as built."""
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA query_only = ON")
    return connection


def _stored(path: Path, sql: str, *, as_bytes: bool = False) -> list[tuple[Any, ...]]:
    """What ``sql`` reads of the file at ``path``, never through the audit; with ``as_bytes``, every text as its bytes (a
    text that is not UTF-8 included)."""
    connection = _reader(path)
    try:
        if as_bytes:
            connection.text_factory = bytes
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


def _blob_database(tmp_path: Path) -> Path:
    """The database of ``BLOB_TABLES``. Verified by SQL, not assumed: the BLOBs are stored as BLOBs, the ``EUR`` beside
    them as text; and the reads that verify it leave the file and its folder as built."""
    path = _build(tmp_path / "app.db", BLOB_TABLES)
    built = _fingerprint(path)
    stored = _stored(path, "SELECT id, typeof(currency), hex(currency) FROM assets ORDER BY id")
    assert stored == BLOB_STORAGE, f"precondition: the assets store their currencies as {BLOB_STORAGE}: {stored}"
    assert _fingerprint(path) == built, "precondition: reading the database as built changed it or its folder"
    return path


def _not_utf8_database(tmp_path: Path) -> Path:
    """A database whose asset 2 stores ``NOT_UTF8`` as TEXT, beside asset 1's ``EUR`` and a ``978`` in
    ``transactions.currency``. Verified, not assumed: read back as bytes, the value is TEXT, its bytes as written; the
    audit fails on the file with an ``OperationalError`` whose message quotes it, so a log of that message would hold it;
    and the reads that verify it leave the file and its folder as written."""
    path = _build(tmp_path / "app.db", {"assets": _assets(["EUR", "EUR"]), "transactions": _transactions([("978", None)])})
    connection = sqlite3.connect(path)
    try:
        connection.execute("UPDATE assets SET currency = CAST(? AS TEXT) WHERE id = 2", (NOT_UTF8,))
        connection.commit()
    finally:
        connection.close()
    written = _fingerprint(path)
    stored = _stored(path, "SELECT id, typeof(currency), currency FROM assets ORDER BY id", as_bytes=True)
    assert stored == [(1, b"text", b"EUR"), (2, b"text", NOT_UTF8)], f"precondition: asset 2 stores its currency as TEXT that is not UTF-8: {stored}"
    connection = _reader(path)
    try:
        with pytest.raises(sqlite3.OperationalError) as raised:
            _audit("find_stored_currency_findings")(connection)
    finally:
        connection.close()
    assert NOT_UTF8_MARKER in str(raised.value), f"precondition: the error the audit fails with quotes the stored text: {raised.value}"
    assert _fingerprint(path) == written, "precondition: reading the database as written changed it or its folder"
    return path


# =============================================================================
# 1. The places and the finding
# =============================================================================


def test_places_are_the_fourteen_in_order():  # red until E-19a
    """SCA-001 — RED: ``STORED_CURRENCY_PLACES`` is exactly the tuple of the 14 places, ``global_settings.default_currency`` last."""
    places = _audit("STORED_CURRENCY_PLACES")
    assert isinstance(places, tuple), f"STORED_CURRENCY_PLACES must be a tuple, got {type(places).__name__}"
    assert places == PLACES


def test_finding_is_a_frozen_dataclass():  # red until E-19a
    """SCA-002 — RED: ``StoredCurrencyFinding`` is a frozen dataclass of ``place``, ``value``, ``rows`` and ``suggestion``, in that order."""
    finding_class = _audit("StoredCurrencyFinding")
    assert dataclasses.is_dataclass(finding_class), f"{finding_class!r} is not a dataclass"
    assert [field.name for field in dataclasses.fields(finding_class)] == ["place", "value", "rows", "suggestion"]
    finding = finding_class(place="transactions.currency", value="978", rows=3, suggestion="EUR")
    assert finding == finding_class(place="transactions.currency", value="978", rows=3, suggestion="EUR")
    with pytest.raises(dataclasses.FrozenInstanceError):
        finding.rows = 4


# =============================================================================
# 2. find_stored_currency_findings
# =============================================================================


def test_findings_of_every_place(tmp_path):  # red until E-19a
    """SCA-010 — RED: the main database gives exactly ``MAIN_FINDINGS``: every lenient value of every place, with its
    rows and suggestion, sorted by place, rows descending, value.

    Not reported: the canonical codes, the NULLs, the malformed JSON (``not json``), ``provider_params`` of ``{}`` or
    NULL, and the global settings other than ``default_currency`` (``default_language`` holds ``978``). Reported:
    ``eur`` (lower case), ``EUR `` (a trailing space), the numeric codes, the names, ``Bolívar Soberano`` and ``GBX``
    (both without a suggestion). The connection is read-write, and the audit writes nothing through it.
    """
    path = _build(tmp_path / "app.db", MAIN_TABLES)
    assert _find(path) == MAIN_FINDINGS


def test_clean_database_gives_no_finding(tmp_path):  # red until E-19a
    """SCA-011 — RED: a database holding only canonical codes gives ``[]``, whatever else it holds (NULLs, malformed JSON,
    ``{}``, ``default_currency`` ``EUR`` beside ``default_language`` ``978``)."""
    path = _build(tmp_path / "app.db", CLEAN_TABLES)
    assert _find(path) == []


def test_rows_count_json_entries(tmp_path):  # red until E-19a
    """SCA-012 — RED: for a JSON place, ``rows`` counts the entries holding the value: one route whose steps go AUD → 978
    → 826 → 978 → NZD holds ``978`` twice as a ``from`` and twice as a ``to``."""
    looped = _route(("AUD", "978", "ECB"), ("978", "826", "BOE"), ("826", "978", "BOE"), ("978", "NZD", "ECB"))
    path = _build(tmp_path / "app.db", {"fx_conversion_routes": _routes([("AUD", "NZD", 1, looped)])})
    assert _find(path) == [
        ("fx_conversion_routes.chain_steps.from", "978", 2, "EUR"),
        ("fx_conversion_routes.chain_steps.from", "826", 1, "GBP"),
        ("fx_conversion_routes.chain_steps.to", "978", 2, "EUR"),
        ("fx_conversion_routes.chain_steps.to", "826", 1, "GBP"),
    ]


def test_only_the_default_currency_global_setting_is_a_place(tmp_path):  # red until E-19a
    """SCA-013 — RED: of the global settings, only the value of ``default_currency`` is read, as plain text:
    ``default_language`` ``978`` and ``default_theme`` ``EURO`` are never reported, ``default_currency`` ``usd`` is."""
    path = _build(tmp_path / "app.db", {"global_settings": _global_settings({"default_currency": "usd", "default_language": "978", "default_theme": "EURO"})})
    assert _find(path) == [("global_settings.default_currency", "usd", 1, "USD")]


def test_json_of_another_shape_is_ignored(tmp_path):  # red until E-19a
    """SCA-014 — RED, ASSUMPTION (the contract names malformed JSON only): valid JSON of another shape is ignored as
    malformed JSON is, without raising — a ``chain_steps`` that is an object, a string, a number or a list of
    non-objects, a ``provider_params`` that is a list, a string or a number, and a ``currency`` of JSON null.

    Each holds ``978`` where a reader that trusted the shape would find it. Beside them, well-formed rows still give
    their findings.
    """
    routes = _routes(
        [
            ("EUR", "USD", 1, '{"from": "978", "to": "USD", "provider": "ECB"}'),
            ("EUR", "USD", 2, '"978"'),
            ("EUR", "USD", 3, "978"),
            ("EUR", "USD", 4, '[978, "978", null, ["978"]]'),
            ("826", "USD", 1, _route(("826", "USD", "BOE"))),
        ]
    )
    params = ['[{"currency": "978"}]', '"978"', "978", '{"currency": null}', '{"currency": "lek"}']
    path = _build(tmp_path / "app.db", {"assets": _assets(["EUR"] * len(params)), "fx_conversion_routes": routes, "asset_provider_assignments": _assignments(params)})
    assert _find(path) == [
        ("fx_conversion_routes.base", "826", 1, "GBP"),
        ("fx_conversion_routes.chain_steps.from", "826", 1, "GBP"),
        ("asset_provider_assignments.provider_params.currency", "lek", 1, "ALL"),
    ]


def test_a_blob_is_a_finding_as_sqlite_quotes_it(tmp_path):  # red until E-19b1.3: _as_text does not handle a BLOB yet
    """SCA-015 — RED until E-19b1.3: a currency stored as a BLOB is a finding, as any value that is no canonical code:
    its value is SQLite's ``quote()`` of it (``X'455552'`` for the bytes of ``EUR``, ``X'00FF'``), with its rows and no
    suggestion. The BLOB of ``EUR`` is not the text ``EUR`` beside it, which is not reported. The places before and
    after its own keep their findings: all of them are returned, sorted as ever.

    Precondition, read by SQL (``_blob_database``): the BLOBs are stored as BLOBs. Today ``_as_text`` gives the bytes to
    ``json.dumps``, whose ``TypeError`` ends the whole audit.
    """
    path = _blob_database(tmp_path)
    try:
        found = _find(path)
    except TypeError as exc:
        _red(f"{BLOB_RED}: {type(exc).__name__}: {exc}", lot=READ_LOT)
    assert found == BLOB_FINDINGS


# =============================================================================
# 3. summarize_findings
# =============================================================================


def _findings(rows: Sequence[Finding]) -> list[Any]:
    finding_class = _audit("StoredCurrencyFinding")
    return [finding_class(place=place, value=value, rows=count, suggestion=suggestion) for place, value, count, suggestion in rows]


def _summary_item(place: str, value: str, rows: int, suggestion: Optional[str]) -> str:
    return f"{place} '{value}' ×{rows} → {suggestion or 'no ISO code'}"


def test_summary_of_no_finding_is_empty():  # red until E-19a
    """SCA-020 — RED: ``summarize_findings([])`` is ``""``."""
    assert _audit("summarize_findings")([]) == ""


def test_summary_lists_each_finding():  # red until E-19a
    """SCA-021 — RED: one ``place 'value' ×rows → CODE`` per finding (``→ no ISO code`` without a suggestion), joined by ``; ``."""
    rows = [("transactions.currency", "978", 3, "EUR"), ("price_history.currency", "GBX", 1, None), ("global_settings.default_currency", "EURO", 1, "EUR")]
    summary = _audit("summarize_findings")(_findings(rows))
    assert summary == "transactions.currency '978' ×3 → EUR; price_history.currency 'GBX' ×1 → no ISO code; global_settings.default_currency 'EURO' ×1 → EUR"


@pytest.mark.parametrize("count,limit", [pytest.param(12, None, id="12-default-limit-10"), pytest.param(12, 3, id="12-limit-3"), pytest.param(10, None, id="10-default-limit-10")])
def test_summary_past_the_limit_ends_with_how_many_more(count, limit):  # red until E-19a
    """SCA-022 — RED: past ``limit`` (10 by default) the summary lists the first ``limit`` findings and ends ``and N more``;
    at the limit exactly, it lists them all and says nothing more."""
    summarize = _audit("summarize_findings")
    rows = [("transactions.currency", f"{100 + index}", count - index, "XXX") for index in range(count)]
    summary = summarize(_findings(rows)) if limit is None else summarize(_findings(rows), limit=limit)
    shown = 10 if limit is None else limit
    listed = "; ".join(_summary_item(*row) for row in rows[:shown])
    if count <= shown:
        assert summary == listed
        return
    assert summary.startswith(listed), summary
    assert summary.endswith(f"and {count - shown} more"), summary
    hidden = [_summary_item(*row) for row in rows[shown:]]
    assert not [item for item in hidden if item in summary], f"the findings past the limit must not be listed: {summary}"


# =============================================================================
# 4. log_stored_currency_audit
# =============================================================================


def _audit_and_capture(*args: Any) -> tuple[Any, list[dict[str, Any]]]:
    log_audit = _audit("log_stored_currency_audit")
    with capture_logs() as logs:
        result = log_audit(*args)
    return result, logs


def _at_least_warning(logs: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [entry for entry in logs if entry.get("log_level") in WARNING_OR_ABOVE]


def _one_warning(logs: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """The one entry at warning level or above, at warning level exactly."""
    entries = _at_least_warning(logs)
    assert len(entries) == 1 and entries[0].get("log_level") in WARNING_LEVELS, f"exactly one WARNING expected, got {entries}"
    return entries[0]


def _assert_logged_findings(result: Any, logs: Sequence[Mapping[str, Any]], expected: list[Finding]) -> None:
    """The result is the findings, and the log one WARNING naming ISO 4217, with their count and summary."""
    assert _as_tuples(result) == expected
    entry = _one_warning(logs)
    assert "ISO 4217" in str(entry.get("event")), entry
    assert entry.get("findings") == len(expected), f"'findings' must be the count, {len(expected)}: {entry}"
    assert entry.get("summary") == _audit("summarize_findings")(result), f"'summary' must be summarize_findings of the findings: {entry}"


def test_log_audit_warns_once_and_returns_the_findings(tmp_path):  # red until E-19a
    """SCA-030 — RED: with findings, one WARNING whose event names ``ISO 4217``, with ``findings`` (29, the count) and
    ``summary``; the findings are returned, and the file is as it was."""
    path = _build(tmp_path / "app.db", MAIN_TABLES)
    before = _fingerprint(path)
    result, logs = _audit_and_capture(path)
    _assert_logged_findings(result, logs, MAIN_FINDINGS)
    assert _fingerprint(path) == before, "the audit changed the database file or its folder"


def test_log_audit_of_a_clean_database_says_nothing(tmp_path):  # red until E-19a
    """SCA-031 — RED: a clean database logs nothing at warning level or above and returns ``[]``."""
    path = _build(tmp_path / "app.db", CLEAN_TABLES)
    before = _fingerprint(path)
    result, logs = _audit_and_capture(path)
    assert (result, _at_least_warning(logs)) == ([], [])
    assert _fingerprint(path) == before, "the audit changed the database file or its folder"


@pytest.mark.parametrize("kind", ["missing", "not-a-database"])
def test_log_audit_of_an_unreadable_file_warns_and_returns_none(tmp_path, kind):  # red until E-19a
    """SCA-032 — RED: a missing file or a file that is no database never raises: one warning whose event says ``could
    not``, and ``None``. The file is opened read-only: a missing one is not created, a foreign one is not changed."""
    path = tmp_path / "app.db"
    if kind == "not-a-database":
        path.write_bytes(b"This is no SQLite database, only text.\n" * 200)
    before = _fingerprint(path)
    result, logs = _audit_and_capture(path)
    assert result is None, f"an unreadable database gives None, got {result!r}"
    assert "could not" in str(_one_warning(logs).get("event")).lower(), _at_least_warning(logs)
    assert _fingerprint(path) == before, f"the audit created or changed {path.name} ({kind})"


def test_log_audit_without_a_path_reads_the_configured_database(tmp_path, monkeypatch):  # red until E-19a
    """SCA-033 — RED: ``log_stored_currency_audit()`` audits ``configured_sqlite_path()`` (patched here to a file of
    ``tmp_path``, wherever the module reads it from: never the real database)."""
    module = _audit_module()
    path = _build(tmp_path / "configured" / "app.db", CLI_TABLES)
    monkeypatch.setattr(post_migration, "configured_sqlite_path", lambda: path)
    monkeypatch.setattr(module, "configured_sqlite_path", lambda: path, raising=False)
    result, logs = _audit_and_capture()
    _assert_logged_findings(result, logs, CLI_FINDINGS)


def test_log_audit_opens_a_path_with_a_space_and_a_hash(tmp_path):  # red until E-19a
    """SCA-034 — RED, ASSUMPTION (the contract says "opens the file read-only", not how): the database of a folder named
    ``data dir #1`` is the one audited. A read-only URI built from the raw path (``file:…?mode=ro``) would cut it at the
    ``#`` and find no such file."""
    built = _build(tmp_path / "build" / "app.db", CLI_TABLES)
    path = tmp_path / "data dir #1" / "app.db"
    path.parent.mkdir()
    shutil.copyfile(built, path)
    before = _fingerprint(path)
    result, logs = _audit_and_capture(path)
    _assert_logged_findings(result, logs, CLI_FINDINGS)
    assert _fingerprint(path) == before, "the audit changed the database file or its folder"


def test_log_audit_of_blobs_warns_of_their_findings(tmp_path):  # red until E-19b1.3: _as_text does not handle a BLOB yet
    """SCA-035 — RED until E-19b1.3: on the database of SCA-015, the startup's check returns its findings and logs the one
    warning of findings (``ISO 4217``, their count, a summary naming the BLOBs), never one saying it could not check:
    today the BLOB's ``TypeError`` makes it lose every finding of every place."""
    path = _blob_database(tmp_path)
    before = _fingerprint(path)
    result, logs = _audit_and_capture(path)
    if result is None:
        _red(f"{BLOB_RED}: the startup's check lost every finding, logging {_at_least_warning(logs)}", lot=READ_LOT)
    _assert_logged_findings(result, logs, BLOB_FINDINGS)
    summary = str(_one_warning(logs).get("summary"))
    assert all(value in summary for value in ("X'455552'", "X'00FF'")), f"the summary names the BLOBs: {summary}"
    assert _fingerprint(path) == before, "the audit changed the database file or its folder"


def test_log_audit_that_fails_names_the_class_of_the_error_never_its_text(tmp_path):  # red until E-19b1.3: the failure log still carries the error's text
    """SCA-036 — RED until E-19b1.3: the warning of a check that fails names the class of the error (and SQLite's error
    name), never the error's text, which can quote what the database stores: after a restore, an archive's bytes. A
    currency stored as TEXT that is not UTF-8 makes ``sqlite3`` raise an ``OperationalError`` quoting it: the check
    returns None and logs one warning whose event says ``could not``, a field of which names ``OperationalError``; no
    line of the log holds the stored text or the words of the message (``NOT_UTF8_FRAGMENTS``).

    Preconditions (``_not_utf8_database``): the value is stored as TEXT, its bytes as written, and the audit fails on the
    file with that ``OperationalError``, its message quoting the text. Today the warning carries ``str(error)``.
    """
    path = _not_utf8_database(tmp_path)
    before = _fingerprint(path)
    result, logs = _audit_and_capture(path)
    assert result is None, f"a check that fails gives None, got {result!r}"
    entry = _one_warning(logs)
    assert "could not" in str(entry.get("event")).lower(), entry
    told = [line for line in logs if any(fragment in repr(line) for fragment in NOT_UTF8_FRAGMENTS)]
    if told:
        _red(f"{LOG_RED}: {told}", lot=READ_LOT)
    fields = {key: value for key, value in entry.items() if key not in ("event", "log_level")}
    assert any(isinstance(value, str) and "OperationalError" in value for value in fields.values()), f"a field of the warning names the class of the error, OperationalError: {fields}"
    assert _fingerprint(path) == before, "the audit changed the database file or its folder"


# =============================================================================
# 5. The command line: main(argv) and python -m
# =============================================================================


def _lines_naming(output: str, finding: Finding) -> list[str]:
    """The lines of ``output`` naming the finding's place, value, rows (as a number of its own) and suggestion, or ``—``.

    A line naming several places (a summary, a log line) is no finding's own line: it is left out.
    """
    place, value, rows, suggestion = finding
    rows_token = re.compile(rf"(?<!\d){rows}(?!\d)")
    own = [line for line in output.splitlines() if sum(name in line for name in PLACES) == 1]
    return [line for line in own if place in line and value in line and rows_token.search(line) and (suggestion or "—") in line]


def test_cli_lists_each_finding_and_exits_1(tmp_path, capsys):  # red until E-19a
    """SCA-040 — RED: ``main(["--db-file", path])`` prints one line per finding — its place, value, rows and suggestion,
    ``—`` without one — and returns 1. Structured logs are captured, so stdout holds what ``main`` prints."""
    main = _audit("main")
    path = _build(tmp_path / "app.db", CLI_TABLES)
    before = _fingerprint(path)
    with capture_logs():
        code = main(["--db-file", str(path)])
    out, _ = capsys.readouterr()
    assert code == 1, f"findings: exit 1 expected, got {code!r}; printed {out!r}"
    lines = {finding: _lines_naming(out, finding) for finding in CLI_FINDINGS}
    assert all(len(found) == 1 for found in lines.values()), f"one line per finding expected: {lines}\n{out}"
    assert _fingerprint(path) == before, "the audit changed the database file or its folder"


def test_cli_of_a_clean_database_exits_0(tmp_path, capsys):  # red until E-19a
    """SCA-041 — RED: on a clean database, ``main`` prints a line containing ``No stored currency code`` and returns 0."""
    main = _audit("main")
    path = _build(tmp_path / "app.db", CLEAN_TABLES)
    code = main(["--db-file", str(path)])
    out, _ = capsys.readouterr()
    assert (code, any("No stored currency code" in line for line in out.splitlines())) == (0, True), f"exit {code!r}, printed {out!r}"


@pytest.mark.parametrize("kind", ["missing", "not-a-database"])
def test_cli_of_an_unreadable_file_exits_2(tmp_path, capsys, kind):  # red until E-19a
    """SCA-042 — RED: on a missing file or a file that is no database, ``main`` returns 2 with a message on stderr, and
    creates or changes nothing."""
    main = _audit("main")
    path = tmp_path / "app.db"
    if kind == "not-a-database":
        path.write_bytes(b"This is no SQLite database, only text.\n" * 200)
    before = _fingerprint(path)
    code = main(["--db-file", str(path)])
    _, err = capsys.readouterr()
    assert (code, bool(err.strip())) == (2, True), f"exit 2 and a message on stderr expected; got exit {code!r}, stderr {err!r}"
    assert _fingerprint(path) == before, f"the command created or changed {path.name} ({kind})"


def _module_env(tmp_path: Path) -> dict[str, str]:
    """The environment of a ``python -m`` run of the module: UTF-8 output, no test mode, and a data dir in ``tmp_path``,
    so a command that ignored ``--db-file`` would never reach a real database."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "LIBREFOLIO_DATA_DIR": str(tmp_path / "data")}
    env.pop("LIBREFOLIO_TEST_MODE", None)
    return env


def _run_as_module(path: Path, env: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    """``python -m backend.app.services.platform.stored_currencies --db-file <path>``, what ``./dev.py db currencies``
    runs, in a process of its own."""
    return subprocess.run([sys.executable, "-m", AUDIT_MODULE, "--db-file", str(path)], cwd=WORKTREE_ROOT, env=dict(env), capture_output=True, text=True, encoding="utf-8", timeout=300, check=False)


def test_cli_as_a_module_exits_1_0_2(tmp_path):  # red until E-19a
    """SCA-043 — RED: ``python -m backend.app.services.platform.stored_currencies --db-file <path>`` exits 1 with
    findings (each finding's place printed), 0 when clean, 2 when the file is no database; never with a traceback.

    The module is looked up in-process first: before E-19a, ``python -m`` of a missing module also exits 1. The data
    dir points into ``tmp_path``, so a command that ignored ``--db-file`` would never reach a real database.
    """
    _audit_module()
    garbage = tmp_path / "garbage.db"
    garbage.write_bytes(b"This is no SQLite database, only text.\n" * 200)
    cases = (("findings", _build(tmp_path / "findings" / "app.db", CLI_TABLES), 1), ("clean", _build(tmp_path / "clean" / "app.db", CLEAN_TABLES), 0), ("unreadable", garbage, 2))
    env = _module_env(tmp_path)
    for name, path, expected in cases:
        before = _fingerprint(path)
        done = _run_as_module(path, env)
        said = f"{name}: exit {done.returncode}\nstdout: {done.stdout[-2000:]}\nstderr: {done.stderr[-2000:]}"
        assert done.returncode == expected, said
        assert "Traceback" not in done.stderr, said
        assert _fingerprint(path) == before, f"{name}: the command changed the database file or its folder"
        if name == "findings":
            assert all(place in done.stdout for place, _, _, _ in CLI_FINDINGS), said
        if name == "unreadable":
            assert done.stderr.strip(), said


def test_cli_lists_blobs_and_exits_1(tmp_path, capsys):  # red until E-19b1.3: _as_text does not handle a BLOB yet
    """SCA-044 — RED until E-19b1.3: ``main`` on the database of SCA-015 returns 1, never raises, and prints one line per
    finding: a BLOB's value as SQLite's ``quote()`` writes it, its rows, ``—`` for its suggestion. Today the
    ``TypeError`` of ``_as_text`` escapes ``main``, which catches only what cannot be read."""
    main = _audit("main")
    path = _blob_database(tmp_path)
    before = _fingerprint(path)
    try:
        with capture_logs():
            code = main(["--db-file", str(path)])
    except TypeError as exc:
        _red(f"{BLOB_RED}: main raised {type(exc).__name__}: {exc}", lot=READ_LOT)
    out, _ = capsys.readouterr()
    assert code == 1, f"findings: exit 1 expected, got {code!r}; printed {out!r}"
    lines = {finding: _lines_naming(out, finding) for finding in BLOB_FINDINGS}
    assert all(len(found) == 1 for found in lines.values()), f"one line per finding expected: {lines}\n{out}"
    assert _fingerprint(path) == before, "the audit changed the database file or its folder"


def test_cli_as_a_module_lists_blobs_without_a_traceback(tmp_path):  # red until E-19b1.3: _as_text does not handle a BLOB yet
    """SCA-045 — RED until E-19b1.3: what ``./dev.py db currencies`` runs (``python -m``) on the database of SCA-015
    exits 1 and prints one line per finding, the BLOBs' among them, never a traceback.

    The exit code alone proves nothing: Python's own exit on an uncaught exception is 1 too. Today the command ends
    with the traceback of the ``TypeError`` of ``_as_text``, no finding printed.
    """
    _audit_module()
    path = _blob_database(tmp_path)
    before = _fingerprint(path)
    done = _run_as_module(path, _module_env(tmp_path))
    said = f"exit {done.returncode}\nstdout: {done.stdout[-2000:]}\nstderr: {done.stderr[-2000:]}"
    if "Traceback" in done.stderr:
        _red(f"{BLOB_RED}: the command ends with a traceback\n{said}", lot=READ_LOT)
    assert done.returncode == 1, said
    lines = {finding: _lines_naming(done.stdout, finding) for finding in BLOB_FINDINGS}
    assert all(len(found) == 1 for found in lines.values()), f"one line per finding expected: {lines}\n{said}"
    assert _fingerprint(path) == before, "the command changed the database file or its folder"


# =============================================================================
# 6. This file's own database builder
# =============================================================================


def test_builder_stores_the_values_as_written(tmp_path):
    """SCA-050 — GUARD (green today): the builder's raw SQL stores every lenient value as written, NULLs as NULL and the
    malformed JSON as text, in a database that passes ``PRAGMA integrity_check`` and ``foreign_key_check``. Without
    it, a red above could come from this file instead of the product."""
    path = _build(tmp_path / "app.db", MAIN_TABLES)
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        counts = {table: connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0] for table in MAIN_TABLES}
        cash = connection.execute("SELECT currency, typeof(currency) FROM transactions ORDER BY id").fetchall()
        cost = sorted(row[0] for row in connection.execute("SELECT cost_basis_currency FROM transactions WHERE cost_basis_currency IS NOT NULL"))
        steps = [row[0] for row in connection.execute("SELECT chain_steps FROM fx_conversion_routes ORDER BY id")]
        params = [row[0] for row in connection.execute("SELECT provider_params FROM asset_provider_assignments ORDER BY asset_id")]
        default = connection.execute("SELECT value FROM global_settings WHERE key = 'default_currency'").fetchone()
    finally:
        connection.close()
    assert counts == {table: len(rows) for table, rows in MAIN_TABLES.items()}
    assert [value for value, _ in cash] == ["978", "978", "978", "US DOLLAR", "US DOLLAR", "eur", "EUR", "EUR", "USD", None, None]
    assert [kind for _, kind in cash] == ["text"] * 9 + ["null"] * 2
    assert cost == ["Bolívar Soberano", "EURO", "EURO", "GBP", "YEN"]
    assert ("not json" in steps, json.loads(steps[2])[0]["to"]) == (True, "978")
    assert params[1:4] == ["{}", None, "not json"]
    assert default == ("EURO",)
