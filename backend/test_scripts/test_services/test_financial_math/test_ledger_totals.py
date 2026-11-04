"""
Red tests for the control totals of the transaction ledger (release 1.3, workstream J, lot CP-15).

Module under test: ``backend/app/services/financial_math/ledger_totals.py`` — ``ControlTotals`` with ``to_json`` and
``from_json``, ``CONTROL_TOTALS_VERSION``, ``position_quantities``, ``control_totals`` and ``compute_control_totals``.

What the module owes its caller, in one line: workstream B (backup) writes ``control_totals`` of the whole ledger into
the backup manifest and recomputes them after a restore, on a session opened on another SQLite file in the same
process; a difference means rows lost, added or altered in broker, asset, currency, amount or quantity, and nothing
else (a row's type, date, id or cost basis) may make one. The contract pinned here, agreed with B on 15/10:

* cash per (broker, currency) is ``native_balances`` of ``cash_movement_from_transaction`` of every row, any type, at
  100 % (a row without a currency moves no cash); the quantity per (broker, asset) follows the portfolio engine's
  rule, every row with an asset and a quantity other than zero, any type, at 100 %. Lines that sum to zero are dropped
  (``position_quantities`` keeps them at zero, like ``native_balances``); lines are sorted by (broker, currency) and
  (broker, asset); dust below the Dashboard's ``QUANTITY_DUST_THRESHOLD`` is kept; no cost basis anywhere;
* sums are exact: a sum that cannot be represented raises ``decimal.Inexact`` instead of becoming a rounded total, and
  the caller's decimal context is left as it was;
* ``to_json()`` is ``{"version": 1, "cash": [{"broker_id", "currency", "balance"}, ...], "quantities": [{"broker_id",
  "asset_id", "quantity"}, ...]}``, keys in that order, every amount as canonical decimal text (plain notation, no
  trailing zeros, "0" for zero, never "-0"); ``from_json()`` is its inverse and raises ``ValueError`` for another
  version or a malformed manifest;
* ``compute_control_totals(session)`` reads ``transactions`` through that session only: the agreed columns, keyset
  blocks of ``_BLOCK_SIZE`` rows, never an SQL ``SUM``, and no settings, cache, rate, price or clock.

Pure, except the tests on file: rows are ``SimpleNamespace`` objects with the attributes of a transaction, and
``convert_bulk`` is replaced, on the FX service and on both financial math modules that call it, by a probe that
records and fails. The tests on file build private SQLite files under ``tmp_path`` with the app schema
(``SQLModel.metadata.create_all``) and open them with an engine of their own (``sqlite+aiosqlite``, NullPool), disposed
at teardown: no server, no session on the lane's database, no network. The static guard parses the module's source
with ``ast``.

Red first: the module is a stub with the agreed API that returns empty totals, so every test fails on a value. The
tests marked GUARD are green today and must stay green: the value object and its constants, the empty ledger (rows
and file) and the static guard with its self-test.

Lot J-27 (16/10) narrows ``from_json``: an amount is read only as plain decimal text, of the shape ``to_json`` writes,
an optional "-" and 1 to 60 ASCII digits, then optionally "." and 1 to 60 more (60 is ``_EXACT.prec``). ``Decimal``
reads far more, and the canonical form writes it out digit by digit: a hand-written manifest holding "1E+50000000"
costs 121 MB to read. Its reds are the texts ``Decimal`` reads; its GUARDs are the ones it refuses already, and plain
text up to the bound, read back canonically as before.
"""

from __future__ import annotations

import ast
import dataclasses
import decimal
import inspect
import json
import math
import re
import sys
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from importlib.util import resolve_name
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app import config as app_config
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # every model, for create_all; importing backend.app.db brings the session module and its PRAGMA listener
from backend.app.db.models import Asset, Broker, Transaction, TransactionType
from backend.app.services.financial_math import average_cost, ledger_totals, native_cash
from backend.app.services.financial_math.average_cost import CostPosition, _fold_average_costs, cost_movement_from_transaction
from backend.app.services.financial_math.ledger_totals import CONTROL_TOTALS_VERSION, ControlTotals, compute_control_totals, control_totals, position_quantities
from backend.app.services.financial_math.native_cash import cash_movement_from_transaction, native_balances
from backend.app.services.fx import conversion as fx_conversion
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD
from backend.app.utils.runtime import cache as runtime_cache
from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[4]
LEDGER_TOTALS_SOURCE = REPO_ROOT / "backend" / "app" / "services" / "financial_math" / "ledger_totals.py"
#: The package the module's relative imports resolve against.
LEDGER_TOTALS_PACKAGE = "backend.app.services.financial_math"

BUY = TransactionType.BUY
SELL = TransactionType.SELL
DIVIDEND = TransactionType.DIVIDEND
INTEREST = TransactionType.INTEREST
DEPOSIT = TransactionType.DEPOSIT
WITHDRAWAL = TransactionType.WITHDRAWAL
FEE = TransactionType.FEE
ADJUSTMENT = TransactionType.ADJUSTMENT
TRANSFER = TransactionType.TRANSFER
FX_CONVERSION = TransactionType.FX_CONVERSION
CASH_TRANSFER = TransactionType.CASH_TRANSFER

B1, B2, B3 = 1, 2, 3
A5, A7, A8, A10, A11, A12, A13 = 5, 7, 8, 10, 11, 12, 13

BEFORE_ANY_ROW = date(2024, 1, 1)
D1 = date(2024, 1, 2)
D2 = date(2024, 2, 1)
D3 = date(2024, 3, 1)
D4 = date(2024, 4, 2)
D5 = date(2024, 5, 2)
D6 = date(2024, 6, 3)
D7 = date(2024, 7, 1)
D8 = date(2024, 8, 1)
FAR_FUTURE = date(2099, 12, 31)


# =============================================================================
# Rows
# =============================================================================


def tx(tx_id: int, tx_type: TransactionType, day: date, broker_id: int, *, asset_id: int | None = None, currency: str | None = None, amount: str = "0", quantity: str = "0", cbo: str | None = None, cbo_currency: str | None = None) -> SimpleNamespace:
    """A row of ``transactions`` as the table holds it: ``amount`` and ``quantity`` never null, ``currency`` null on a row without cash."""
    return SimpleNamespace(
        id=tx_id,
        type=tx_type,
        date=day,
        broker_id=broker_id,
        asset_id=asset_id,
        currency=currency,
        amount=Decimal(amount),
        quantity=Decimal(quantity),
        cost_basis_override=None if cbo is None else Decimal(cbo),
        cost_basis_currency=cbo_currency,
    )


def _copy(row: SimpleNamespace, **changes: Any) -> SimpleNamespace:
    """``row`` with ``changes`` applied, as a new object: no test mutates a row that another test could read."""
    return SimpleNamespace(**{**vars(row), **changes})


def _changed(book: list[SimpleNamespace], changes: dict[int, dict[str, Any]]) -> list[SimpleNamespace]:
    """``book`` with the rows named by id rewritten, every other row copied as it was."""
    return [_copy(row, **changes.get(row.id, {})) for row in book]


# =============================================================================
# The reference book and its totals
# =============================================================================


def reference_book() -> list[SimpleNamespace]:
    """The reference ledger, built afresh on every call; broker 2's rows come first, so that the sort is observable.

    Broker 1 holds EUR and, through an FX_CONVERSION pair, USD; it sends 100 EUR to broker 2 with a CASH_TRANSFER pair
    and 4 units of asset 10 with a TRANSFER pair. Asset 10 on broker 1: bought 5, sold 2, a 2:1 split adds 3 (the
    ADJUSTMENT linked to the split, row 11), 1 given away (ADJUSTMENT-out), 4 transferred: 1 left. Asset 12 on broker 1
    is bought and sold back to zero. Asset 11 on broker 2 keeps 0.000001 units of dust. Broker 2's GBP deposit and
    withdrawal cancel out. Row 10 has an amount but no currency and row 17 a quantity but no asset: neither counts.
    Amounts carry six decimals, as SQLite gives them back.
    """
    return [
        tx(21, DEPOSIT, D1, B2, currency="USD", amount="500.000000"),
        tx(22, BUY, D2, B2, asset_id=A11, currency="USD", amount="-100.000000", quantity="10.000000"),
        tx(23, SELL, D4, B2, asset_id=A11, currency="USD", amount="110.000000", quantity="-9.999999"),
        tx(24, DIVIDEND, D5, B2, asset_id=A13, currency="EUR", amount="7.000000"),
        tx(25, DEPOSIT, D3, B2, currency="GBP", amount="40.000000"),
        tx(26, WITHDRAWAL, D8, B2, currency="GBP", amount="-40.000000"),
        tx(1, DEPOSIT, D1, B1, currency="EUR", amount="1000.000000"),
        tx(2, BUY, D2, B1, asset_id=A10, currency="EUR", amount="-250.500000", quantity="5.000000"),
        tx(3, SELL, D3, B1, asset_id=A10, currency="EUR", amount="120.250000", quantity="-2.000000"),
        tx(4, DIVIDEND, D4, B1, asset_id=A10, currency="EUR", amount="3.750000"),
        tx(5, FEE, D4, B1, currency="EUR", amount="-2.000000"),
        tx(6, FX_CONVERSION, D5, B1, currency="EUR", amount="-500.000000"),
        tx(7, FX_CONVERSION, D5, B1, currency="USD", amount="545.500000"),
        tx(8, CASH_TRANSFER, D6, B1, currency="EUR", amount="-100.000000"),
        tx(9, CASH_TRANSFER, D6, B2, currency="EUR", amount="100.000000"),
        tx(10, FEE, D6, B1, amount="-3.000000"),
        tx(11, ADJUSTMENT, D6, B1, asset_id=A10, quantity="3.000000"),
        tx(12, ADJUSTMENT, D7, B1, asset_id=A10, quantity="-1.000000"),
        tx(13, TRANSFER, D7, B1, asset_id=A10, quantity="-4.000000"),
        tx(14, TRANSFER, D7, B2, asset_id=A10, quantity="4.000000", cbo="50.100000", cbo_currency="EUR"),
        tx(15, BUY, D7, B1, asset_id=A12, currency="EUR", amount="-70.000000", quantity="7.000000"),
        tx(16, SELL, D8, B1, asset_id=A12, currency="EUR", amount="77.000000", quantity="-7.000000"),
        tx(17, ADJUSTMENT, D8, B1, quantity="2.000000"),
    ]


#: Broker 1: 1000 - 250.5 + 120.25 + 3.75 - 2 - 500 - 100 - 70 + 77 = 278.5 EUR, and 545.5 USD. Broker 2: 7 + 100 = 107
#: EUR and 500 - 100 + 110 = 510 USD; its GBP is 40 - 40 = 0, dropped. Row 10, counted, would make broker 1's EUR 275.5.
EXPECTED_CASH = (
    (B1, "EUR", Decimal("278.5")),
    (B1, "USD", Decimal("545.5")),
    (B2, "EUR", Decimal("107")),
    (B2, "USD", Decimal("510")),
)
#: Asset 10: 5 - 2 + 3 - 1 - 4 = 1 on broker 1 and 4 on broker 2. Asset 11 on broker 2: 10 - 9.999999 = 0.000001.
#: Asset 12 on broker 1: 7 - 7 = 0, dropped.
EXPECTED_QUANTITIES = (
    (B1, A10, Decimal("1")),
    (B2, A10, Decimal("4")),
    (B2, A11, Decimal("0.000001")),
)
EXPECTED_TOTALS = ControlTotals(version=1, cash=EXPECTED_CASH, quantities=EXPECTED_QUANTITIES)
#: What position_quantities keeps: asset 12 at zero; never a line for asset 13, whose only row moves no quantity.
EXPECTED_POSITIONS = {B1: {A10: Decimal("1"), A12: Decimal("0")}, B2: {A10: Decimal("4"), A11: Decimal("0.000001")}}
EXPECTED_JSON = {
    "version": 1,
    "cash": [
        {"broker_id": 1, "currency": "EUR", "balance": "278.5"},
        {"broker_id": 1, "currency": "USD", "balance": "545.5"},
        {"broker_id": 2, "currency": "EUR", "balance": "107"},
        {"broker_id": 2, "currency": "USD", "balance": "510"},
    ],
    "quantities": [
        {"broker_id": 1, "asset_id": 10, "quantity": "1"},
        {"broker_id": 2, "asset_id": 10, "quantity": "4"},
        {"broker_id": 2, "asset_id": 11, "quantity": "0.000001"},
    ],
}
#: The same manifest as text, as ``json.dumps`` writes it: the canonical text is the point, so it is spelled out.
EXPECTED_JSON_TEXT = (
    '{"version": 1, "cash": ['
    '{"broker_id": 1, "currency": "EUR", "balance": "278.5"}, '
    '{"broker_id": 1, "currency": "USD", "balance": "545.5"}, '
    '{"broker_id": 2, "currency": "EUR", "balance": "107"}, '
    '{"broker_id": 2, "currency": "USD", "balance": "510"}], '
    '"quantities": ['
    '{"broker_id": 1, "asset_id": 10, "quantity": "1"}, '
    '{"broker_id": 2, "asset_id": 10, "quantity": "4"}, '
    '{"broker_id": 2, "asset_id": 11, "quantity": "0.000001"}]}'
)
#: position_quantities of the reference book as of each day, the day's own rows included.
AS_OF_POSITIONS = (
    (BEFORE_ANY_ROW, {}),
    (D1, {}),
    (D2, {B1: {A10: Decimal("5")}, B2: {A11: Decimal("10")}}),
    (D3, {B1: {A10: Decimal("3")}, B2: {A11: Decimal("10")}}),
    (D4, {B1: {A10: Decimal("3")}, B2: {A11: Decimal("0.000001")}}),
    (D5, {B1: {A10: Decimal("3")}, B2: {A11: Decimal("0.000001")}}),
    (D6, {B1: {A10: Decimal("6")}, B2: {A11: Decimal("0.000001")}}),
    (D7, {B1: {A10: Decimal("1"), A12: Decimal("7")}, B2: {A10: Decimal("4"), A11: Decimal("0.000001")}}),
    (D8, EXPECTED_POSITIONS),
    (FAR_FUTURE, EXPECTED_POSITIONS),
)


# =============================================================================
# The canonical book: every trap of decimal text
# =============================================================================


def canonical_book() -> list[SimpleNamespace]:
    """A small ledger whose lines hold every trap of decimal text, built afresh on every call; broker 3 comes first.

    Cash lines 30, -100, -2.5 and 10 (``normalize()`` turns 30, -100 and 10 into 3E+1, -1E+2 and 1E+1), quantity lines
    0.000001, -3 (a short position) and 10. Broker 1's GBP line is a FEE of -0.000000: zero, dropped, never "-0".
    """
    return [
        tx(1, DEPOSIT, D1, B3, currency="EUR", amount="10.000000"),
        tx(2, FEE, D2, B3, currency="CHF", amount="-2.500000"),
        tx(3, ADJUSTMENT, D2, B3, asset_id=A5, quantity="10.000000"),
        tx(4, BUY, D3, B1, asset_id=A7, currency="USD", amount="-100.000000", quantity="0.000001"),
        tx(5, SELL, D3, B1, asset_id=A8, currency="EUR", amount="30.000000", quantity="-3.000000"),
        tx(6, FEE, D4, B1, currency="GBP", amount="-0.000000"),
    ]


EXPECTED_CANONICAL_TOTALS = ControlTotals(
    version=1,
    cash=((B1, "EUR", Decimal("30")), (B1, "USD", Decimal("-100")), (B3, "CHF", Decimal("-2.5")), (B3, "EUR", Decimal("10"))),
    quantities=((B1, A7, Decimal("0.000001")), (B1, A8, Decimal("-3")), (B3, A5, Decimal("10"))),
)
EXPECTED_CANONICAL_TEXT = (
    '{"version": 1, "cash": ['
    '{"broker_id": 1, "currency": "EUR", "balance": "30"}, '
    '{"broker_id": 1, "currency": "USD", "balance": "-100"}, '
    '{"broker_id": 3, "currency": "CHF", "balance": "-2.5"}, '
    '{"broker_id": 3, "currency": "EUR", "balance": "10"}], '
    '"quantities": ['
    '{"broker_id": 1, "asset_id": 7, "quantity": "0.000001"}, '
    '{"broker_id": 1, "asset_id": 8, "quantity": "-3"}, '
    '{"broker_id": 3, "asset_id": 5, "quantity": "10"}]}'
)


# =============================================================================
# Stand-ins: no rate, no settings
# =============================================================================


@dataclasses.dataclass
class RateProbe:
    """Stands in for ``convert_bulk``: control totals need no exchange rate, so a call is recorded, then fails."""

    calls: list[tuple[Any, ...]] = dataclasses.field(default_factory=list)

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(args)
        raise AssertionError("convert_bulk was called: control totals need no exchange rate")


@pytest.fixture(autouse=True)
def no_rates(monkeypatch: pytest.MonkeyPatch) -> Iterator[RateProbe]:
    """Every test: ``convert_bulk`` replaced on the FX service and on both financial math modules that call it.

    The record is checked at teardown too, so a caller that swallowed the probe's exception is still caught.
    """
    probe = RateProbe()
    for module in (fx_conversion, native_cash, average_cost):
        monkeypatch.setattr(module, "convert_bulk", probe)
    yield probe
    assert probe.calls == [], f"convert_bulk was called {len(probe.calls)} time(s): control totals need no exchange rate"


class SettingsForbidden(AssertionError):
    """``get_settings()`` called while control totals were computed from a session."""


@contextmanager
def settings_forbidden() -> Iterator[list[str]]:
    """While the block runs, ``get_settings`` raises wherever it is read from; every call is recorded as well.

    Patching ``backend.app.config.get_settings`` alone would miss each module that imported the function by name,
    ``backend.app.db.session`` among them, whose ``get_async_engine()`` opens the database the settings name: every
    loaded module holding the original gets the stand-in. The record catches a caller that swallowed the exception.
    """
    calls: list[str] = []
    original = app_config.get_settings

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        calls.append("get_settings()")
        raise SettingsForbidden("get_settings() was called: control totals read the session they are given, never a database the settings choose")

    with pytest.MonkeyPatch.context() as patch:
        for module in list(sys.modules.values()):
            if getattr(module, "__dict__", {}).get("get_settings") is original:
                patch.setattr(module, "get_settings", forbidden)
        assert app_config.get_settings is forbidden and db_session.get_settings is forbidden, "the stand-in did not reach backend.app.config and backend.app.db.session"
        yield calls


# =============================================================================
# Private SQLite files
# =============================================================================

SQL_SUM = re.compile(r"\bsum\s*\(", re.IGNORECASE)
SELECT_ALL = re.compile(r"\bselect\s+(?:\w+\.)?\*", re.IGNORECASE)
#: The columns compute_control_totals reads, as agreed with B: any other column of ``transactions`` is one too many.
AGREED_COLUMNS = frozenset({"id", "type", "date", "broker_id", "asset_id", "currency", "amount", "quantity"})
OTHER_COLUMNS = tuple(sorted(set(Transaction.__table__.columns.keys()) - AGREED_COLUMNS))
OTHER_TABLES = tuple(sorted(set(SQLModel.metadata.tables) - {"transactions"}))

LedgerFile = Callable[[str, list[SimpleNamespace]], Awaitable[AsyncEngine]]


@contextmanager
def captured_statements(engine: AsyncEngine) -> Iterator[list[str]]:
    """Every SQL statement ``engine`` sends to SQLite while the block runs (the connect PRAGMAs bypass this hook)."""
    statements: list[str] = []

    def capture(_connection: Any, _cursor: Any, statement: str, _parameters: Any, _context: Any, _executemany: bool) -> None:
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        yield statements
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)


def _statement_problem(statement: str) -> str | None:
    """What makes ``statement`` more than a read of the agreed columns of ``transactions``; None when it is just that."""
    if not statement.lstrip().upper().startswith("SELECT"):
        return "not a read"
    if SQL_SUM.search(statement):
        return "an SQL SUM (Numeric goes through a float on SQLite)"
    if not re.search(r"\btransactions\b", statement):
        return "does not read transactions"
    tables = [table for table in OTHER_TABLES if re.search(rf"\b{re.escape(table)}\b", statement)]
    if tables:
        return f"reads other tables {tables} (no price, no rate)"
    columns = [column for column in OTHER_COLUMNS if re.search(rf"\b{re.escape(column)}\b", statement)]
    if columns or SELECT_ALL.search(statement):
        return f"reads more than the agreed columns ({columns or 'every column'})"
    return None


def _statement_problems(statements: list[str]) -> list[str]:
    """Each statement that is not a plain read of the agreed columns of ``transactions``, with what is wrong with it."""
    return [f"{problem}: {statement}" for statement in statements if (problem := _statement_problem(statement))]


def _transaction_row(row: SimpleNamespace) -> Transaction:
    """The ORM row of a book's row: the eight columns control totals read, and the cost basis they must ignore."""
    return Transaction(
        id=row.id,
        broker_id=row.broker_id,
        asset_id=row.asset_id,
        type=row.type,
        date=row.date,
        quantity=row.quantity,
        amount=row.amount,
        currency=row.currency,
        cost_basis_override=row.cost_basis_override,
        cost_basis_currency=row.cost_basis_currency,
    )


async def _write_book(engine: AsyncEngine, book: list[SimpleNamespace]) -> None:
    """The rows of ``book`` written into ``transactions``, with the brokers and assets their foreign keys need, nothing more."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add_all([Broker(id=broker_id, name=f"cp15-broker-{broker_id}") for broker_id in sorted({row.broker_id for row in book})])
        session.add_all([Asset(id=asset_id, display_name=f"cp15-asset-{asset_id}", currency="EUR") for asset_id in sorted({row.asset_id for row in book if row.asset_id is not None})])
        await session.flush()
        session.add_all([_transaction_row(row) for row in book])
        await session.commit()


async def _compute_on(engine: AsyncEngine) -> ControlTotals:
    """``compute_control_totals`` on a fresh session of ``engine``: what B does on the file of a backup copy."""
    async with AsyncSession(engine) as session:
        return await compute_control_totals(session)


@pytest_asyncio.fixture
async def ledger_file(tmp_path: Path) -> AsyncIterator[LedgerFile]:
    """A factory of private SQLite files under ``tmp_path``: the app schema, the rows of a book, an engine of their own.

    Opened as production opens its database (``sqlite+aiosqlite``, NullPool, the PRAGMA listener of
    ``backend.app.db.session``); every engine is disposed at teardown, before the aiosqlite leak guard looks.
    """
    engines: list[AsyncEngine] = []

    async def make(name: str, book: list[SimpleNamespace]) -> AsyncEngine:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / name}", poolclass=NullPool)
        engines.append(engine)
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        await _write_book(engine, book)
        return engine

    try:
        yield make
    finally:
        for engine in engines:
            await engine.dispose()


# =============================================================================
# Helpers
# =============================================================================


def _lines(lines: tuple[tuple[Any, Any, Decimal], ...], changes: dict[Any, str | None]) -> tuple[tuple[Any, Any, Decimal], ...]:
    """``lines`` with some set to a new value and some gone (None), sorted again by their key."""
    by_key = {(first, second): value for first, second, value in lines}
    for key, value in changes.items():
        if value is None:
            del by_key[key]
        else:
            by_key[key] = Decimal(value)
    return tuple((first, second, value) for (first, second), value in sorted(by_key.items()))


def _expected_with(cash: dict[tuple[int, str], str | None], quantities: dict[tuple[int, int], str | None]) -> ControlTotals:
    """EXPECTED_TOTALS with the given cash and quantity lines changed or gone."""
    return ControlTotals(version=1, cash=_lines(EXPECTED_CASH, cash), quantities=_lines(EXPECTED_QUANTITIES, quantities))


_DROP = object()


def _manifest_with(path: tuple[Any, ...], value: Any = _DROP) -> Any:
    """A fresh copy of the expected manifest with the entry at ``path`` set to ``value``, or removed when none is given."""
    data = json.loads(EXPECTED_JSON_TEXT)
    *parents, last = path
    target = data
    for key in parents:
        target = target[key]
    if value is _DROP:
        del target[last]
    else:
        target[last] = value
    return data


def _context_snapshot() -> tuple[Any, ...]:
    """The settings of the current decimal context: never its flags, which any arithmetic may raise."""
    context = decimal.getcontext()
    traps = tuple(sorted((condition.__name__, bool(trapped)) for condition, trapped in context.traps.items()))
    return context.prec, context.rounding, context.Emin, context.Emax, context.capitals, context.clamp, traps


#: The currency of each asset of the reference book, for the fold (a quantity never depends on it).
ASSET_CURRENCIES = {A10: "EUR", A11: "USD", A12: "EUR", A13: "EUR"}
#: The rows of the reference book the engine finds linked to a SPLIT AssetEvent.
SPLIT_LINKED_IDS = frozenset({11})


def _average_cost_quantities(book: list[SimpleNamespace]) -> dict[tuple[int, int], Decimal]:
    """The quantity of every (broker, asset) by the average-cost fold at share 1, fed as ``build_cost_positions`` feeds it.

    Nothing is resolved (``resolved={}``): an acquisition without its rate still adds its units, so the quantity is the
    fold's whole. The fold clamps a sale beyond the pool, so a parity book must never sell more than it holds.
    """
    movements: dict[tuple[int, int], list[Any]] = defaultdict(list)
    for row in book:
        movement = None if row.asset_id is None else cost_movement_from_transaction(row, asset_currency=ASSET_CURRENCIES[row.asset_id], split_linked=row.id in SPLIT_LINKED_IDS)
        if movement is not None:
            movements[(row.broker_id, row.asset_id)].append(movement)
    positions = [CostPosition(key=key, asset_currency=ASSET_CURRENCIES[key[1]], movements=tuple(items)) for key, items in movements.items()]
    folded = _fold_average_costs(positions, report_currency="EUR", asset_leg=False, resolved={})
    oversold = {key: result.oversold_movement_ids for key, result in folded.items() if result.oversold_movement_ids}
    assert oversold == {}, f"the parity book sells more than it holds, so the fold clamps: {oversold}"
    return {key: result.quantity for key, result in folded.items()}


# =============================================================================
# Parameter tables
# =============================================================================

#: Rewrites that must change nothing: a row's type (the V-3 orphan repair), its cost basis, its date, its id, the order.
INSENSITIVE_REWRITES = [
    pytest.param(lambda book: _changed(book, {13: {"type": ADJUSTMENT}, 14: {"type": ADJUSTMENT}}), id="transfer-pair-as-two-adjustments"),
    pytest.param(lambda book: _changed(book, {8: {"type": WITHDRAWAL}, 9: {"type": DEPOSIT}}), id="cash-transfer-pair-as-withdrawal-and-deposit"),
    pytest.param(lambda book: _changed(book, {8: {"type": WITHDRAWAL}, 9: {"type": DEPOSIT}, 13: {"type": ADJUSTMENT}, 14: {"type": ADJUSTMENT}}), id="both-reclassifications-of-the-orphan-repair"),
    pytest.param(lambda book: _changed(book, {12: {"cost_basis_override": Decimal("12.000000"), "cost_basis_currency": "EUR"}, 14: {"cost_basis_override": Decimal("999.999999"), "cost_basis_currency": "USD"}}), id="cost-basis-override-added-and-changed"),
    pytest.param(lambda book: _changed(book, {14: {"cost_basis_override": None, "cost_basis_currency": None}}), id="cost-basis-override-removed"),
    pytest.param(lambda book: [_copy(row, date=D4) for row in book], id="every-row-dated-the-same-day"),
    pytest.param(lambda book: [_copy(row, id=1000 - row.id) for row in book], id="ids-renumbered"),
    pytest.param(lambda book: list(reversed(book)), id="rows-in-reverse-order"),
]

#: One change each, with the cash and quantity lines it must change (a new value, or None when the line goes).
SENSITIVE_CHANGES = [
    pytest.param(lambda book: [row for row in book if row.id != 2], {(B1, "EUR"): "529"}, {(B1, A10): "-4"}, id="row-lost-a-buy"),
    pytest.param(lambda book: [row for row in book if row.id != 14], {}, {(B2, A10): None}, id="row-lost-one-leg-of-the-transfer"),
    pytest.param(lambda book: [*book, tx(30, INTEREST, D8, B2, currency="EUR", amount="0.010000")], {(B2, "EUR"): "107.01"}, {}, id="row-added"),
    pytest.param(lambda book: _changed(book, {21: {"broker_id": B1}}), {(B1, "USD"): "1045.5", (B2, "USD"): "10"}, {}, id="broker-altered"),
    pytest.param(lambda book: _changed(book, {22: {"asset_id": A13}}), {}, {(B2, A11): "-9.999999", (B2, A13): "10"}, id="asset-altered"),
    pytest.param(lambda book: _changed(book, {1: {"currency": "CHF"}}), {(B1, "CHF"): "1000", (B1, "EUR"): "-721.5"}, {}, id="currency-altered"),
    pytest.param(lambda book: _changed(book, {4: {"amount": Decimal("3.760000")}}), {(B1, "EUR"): "278.51"}, {}, id="amount-altered-by-a-cent"),
    pytest.param(lambda book: _changed(book, {9: {"amount": Decimal("10.000000")}}), {(B2, "EUR"): "17"}, {}, id="amount-altered-on-a-cash-transfer-leg"),
    pytest.param(lambda book: _changed(book, {2: {"quantity": Decimal("5.000001")}}), {}, {(B1, A10): "1.000001"}, id="quantity-altered-by-a-millionth"),
    pytest.param(lambda book: _changed(book, {23: {"quantity": Decimal("-10.000000")}}), {}, {(B2, A11): None}, id="quantity-altered-and-the-dust-line-closes"),
]

#: (Decimal text, canonical text): six decimals as SQLite gives them back, exponent forms, zeros of every sign.
CANONICAL_TEXT = (
    ("10.000000", "10"),
    ("10.500000", "10.5"),
    ("100", "100"),
    ("1E+2", "100"),
    ("100.000000", "100"),
    ("510.000000", "510"),
    ("0.000001", "0.000001"),
    ("1E-6", "0.000001"),
    ("0.0000010", "0.000001"),
    ("1E-7", "0.0000001"),
    ("-2.500000", "-2.5"),
    ("-100.000000", "-100"),
    ("-1E+2", "-100"),
    ("-0.000001", "-0.000001"),
    ("123456789012.123456", "123456789012.123456"),
    ("2999999999999.999997", "2999999999999.999997"),
    ("1E+21", "1000000000000000000000"),
    ("12345678901234567890123456789.5", "12345678901234567890123456789.5"),
    ("0", "0"),
    ("0.000000", "0"),
    ("0E+3", "0"),
    ("-0", "0"),
    ("-0.000000", "0"),
)

OTHER_VERSIONS = [
    pytest.param(2, id="version-2"),
    pytest.param(0, id="version-0"),
    pytest.param("1", id="version-1-as-text"),
    pytest.param(None, id="version-null"),
]

MALFORMED_MANIFESTS = [
    pytest.param(None, id="none"),
    pytest.param([EXPECTED_JSON], id="a-list"),
    pytest.param(EXPECTED_JSON_TEXT, id="the-json-text-not-parsed"),
    pytest.param(1, id="a-number"),
    pytest.param(_manifest_with(("version",)), id="no-version"),
    pytest.param(_manifest_with(("cash",)), id="no-cash"),
    pytest.param(_manifest_with(("quantities",)), id="no-quantities"),
    pytest.param(_manifest_with(("cash", 0, "broker_id")), id="cash-entry-without-broker_id"),
    pytest.param(_manifest_with(("cash", 1, "currency")), id="cash-entry-without-currency"),
    pytest.param(_manifest_with(("cash", 2, "balance")), id="cash-entry-without-balance"),
    pytest.param(_manifest_with(("quantities", 0, "broker_id")), id="quantity-entry-without-broker_id"),
    pytest.param(_manifest_with(("quantities", 1, "asset_id")), id="quantity-entry-without-asset_id"),
    pytest.param(_manifest_with(("quantities", 2, "quantity")), id="quantity-entry-without-quantity"),
    pytest.param(_manifest_with(("cash", 0, "balance"), "abc"), id="balance-not-a-number"),
    pytest.param(_manifest_with(("cash", 0, "balance"), ""), id="balance-empty"),
    pytest.param(_manifest_with(("cash", 0, "balance"), "278,5"), id="balance-with-a-decimal-comma"),
    pytest.param(_manifest_with(("quantities", 0, "quantity"), "one"), id="quantity-not-a-number"),
    pytest.param(_manifest_with(("cash", 0, "balance"), 278.5), id="balance-a-json-number"),
    pytest.param(_manifest_with(("quantities", 2, "quantity"), 0.5), id="quantity-a-json-number"),
    pytest.param(_manifest_with(("cash", 0, "balance"), None), id="balance-null"),
    pytest.param(_manifest_with(("cash",), None), id="cash-null"),
    pytest.param(_manifest_with(("quantities", 0), [1, 10, "1"]), id="quantity-entry-an-array"),
]

#: How many digits plain decimal text may hold on each side of the point: ``_EXACT.prec``, and the bound of B-13's own
#: check (``-?[0-9]{1,60}(\.[0-9]{1,60})?``) before it calls ``from_json``.
PLAIN_DIGITS = 60
#: The widest side plain decimal text may have, and one digit more.
WIDEST_SIDE = "9" * PLAIN_DIGITS
TOO_WIDE_SIDE = "9" * (PLAIN_DIGITS + 1)

#: Where an amount sits in the manifest, by its field: the first cash line's balance, (1, EUR), and the first position's
#: quantity, (1, 10). The sections of a manifest are named as the fields of ``ControlTotals``.
AMOUNT_PATHS = {"balance": ("cash", 0, "balance"), "quantity": ("quantities", 0, "quantity")}

#: Amounts that are not plain decimal text but that ``Decimal`` reads, so ``from_json`` takes them today: one red each.
#: GUARD: the ones ``Decimal`` refuses already, refused today and after.
NOT_PLAIN_TEXT = (
    ("exponent", "1E+100"),
    ("exponent-lowercase", "1e5"),
    ("exponent-negative", "-2.5E-3"),
    ("leading-plus", "+5"),
    ("leading-space", " 5"),
    ("trailing-space", "5 "),
    ("trailing-newline", "5\n"),  # a pattern anchored with "$" lets it through: "$" also matches before a final newline
    ("GUARD-inner-space", "1 000"),
    ("underscores", "1_000"),
    ("arabic-indic-digits", "\u0661\u0662\u0663"),  # ARABIC-INDIC DIGIT ONE, TWO, THREE: "\d" and str.isdigit() accept them
    ("full-width-digits", "\uff11\uff12"),  # FULLWIDTH DIGIT ONE, TWO
    ("61-integer-digits", TOO_WIDE_SIDE),
    ("61-fraction-digits", f"0.{TOO_WIDE_SIDE}"),
    ("61-integer-digits-led-by-zeros", "0" * PLAIN_DIGITS + "7"),  # every digit of the text counts, zeros too
    ("61-fraction-digits-ending-in-zeros", "10.5" + "0" * PLAIN_DIGITS),
    ("GUARD-infinity", "Infinity"),
    ("GUARD-nan", "NaN"),
    ("no-integer-digit", ".5"),
    ("no-fraction-digit", "5."),
    ("GUARD-minus-alone", "-"),
    ("minus-and-no-integer-digit", "-.5"),
)
NOT_PLAIN_AMOUNTS = [
    *(pytest.param(path, text, id=f"{case}-{field}") for case, text in NOT_PLAIN_TEXT for field, path in AMOUNT_PATHS.items()),
    # The real case, on a balance only: today it is read as fifty million digits before the test can fail.
    pytest.param(AMOUNT_PATHS["balance"], "1E+50000000", id="exponent-of-fifty-million-balance"),
]

#: Plain decimal text and the canonical text it is read as: the bound on each side, a sign that is not a digit, zeros.
PLAIN_TEXT = (
    ("60-integer-digits", WIDEST_SIDE, WIDEST_SIDE),
    ("60-fraction-digits", f"0.{WIDEST_SIDE}", f"0.{WIDEST_SIDE}"),
    ("60-digits-each-side", f"{WIDEST_SIDE}.{WIDEST_SIDE}", f"{WIDEST_SIDE}.{WIDEST_SIDE}"),
    ("60-digits-each-side-negative", f"-{WIDEST_SIDE}.{WIDEST_SIDE}", f"-{WIDEST_SIDE}.{WIDEST_SIDE}"),
    ("minus-zero", "-0", "0"),
    ("leading-zeros", "007", "7"),
    ("trailing-zeros", "10.500", "10.5"),
)
PLAIN_AMOUNTS = [pytest.param(path, text, canonical, id=f"{case}-{field}") for case, text, canonical in PLAIN_TEXT for field, path in AMOUNT_PATHS.items()]

#: 1E+70 and 1E-10 on one line: the exact sum has 81 significant digits.
INEXACT_BOOKS = [
    pytest.param([tx(1, DEPOSIT, D1, B1, currency="EUR", amount="1E+70"), tx(2, DEPOSIT, D2, B1, currency="EUR", amount="1E-10")], id="cash-line"),
    pytest.param([tx(1, ADJUSTMENT, D1, B1, asset_id=A10, quantity="1E+70"), tx(2, ADJUSTMENT, D2, B1, asset_id=A10, quantity="1E-10")], id="quantity-line"),
]


# =============================================================================
# L0 — the agreed API (GUARD)
# =============================================================================


class TestAgreedApi:
    def test_l0_the_value_object_and_its_constants(self):
        """GUARD (green today, stays green): the value object and the constants B builds on.

        ``ControlTotals(version, cash, quantities)`` is frozen, has slots, and compares and hashes by value, so a
        Decimal read back from SQLite with six decimals equals the one written; ``CONTROL_TOTALS_VERSION`` is 1 and
        ``_BLOCK_SIZE`` 5000; ``compute_control_totals`` is a coroutine function; ``as_of`` defaults to None.
        """
        print_section("L0 — the agreed API")
        assert (CONTROL_TOTALS_VERSION, ledger_totals._BLOCK_SIZE) == (1, 5000)
        assert [field.name for field in dataclasses.fields(ControlTotals)] == ["version", "cash", "quantities"]
        totals = ControlTotals(version=1, cash=((B1, "EUR", Decimal("1.500000")),), quantities=((B1, A10, Decimal("2")),))
        same = ControlTotals(version=1, cash=((B1, "EUR", Decimal("1.5")),), quantities=((B1, A10, Decimal("2.000000")),))
        assert totals == same, "compared by value"
        assert hash(totals) == hash(same), "hashed by value"
        with pytest.raises(dataclasses.FrozenInstanceError):
            totals.version = 2
        assert not hasattr(totals, "__dict__"), "a dataclass with slots has no instance __dict__"
        assert inspect.iscoroutinefunction(compute_control_totals)
        assert inspect.signature(position_quantities).parameters["as_of"].default is None
        print_success("frozen, slotted, compared by value; version 1, blocks of 5000")

    def test_l0_an_empty_ledger_has_empty_totals(self):
        """GUARD: an instance without a transaction, a fresh install backed up, has version 1 and two empty lists."""
        print_section("L0 — the empty ledger")
        empty = ControlTotals(version=1, cash=(), quantities=())
        assert control_totals([]) == empty
        assert position_quantities([]) == {}
        assert json.dumps(control_totals([]).to_json()) == '{"version": 1, "cash": [], "quantities": []}'
        assert ControlTotals.from_json({"version": 1, "cash": [], "quantities": []}) == empty
        print_success("version 1, no line")


# =============================================================================
# L1 — cash per (broker, currency)
# =============================================================================


class TestCash:
    def test_l1_cash_is_the_native_balance_of_every_row_with_a_currency(self):
        """Cash per (broker, currency): every row with a currency, whatever its type, at 100 %.

        DEPOSIT, BUY (negative), SELL, DIVIDEND, FEE, an FX_CONVERSION pair on broker 1 (500 EUR out, 545.5 USD in) and a
        CASH_TRANSFER pair from broker 1 to broker 2 all count, so each broker holds two currencies. Broker 2's GBP
        deposit and withdrawal cancel out: the line is dropped. Row 10, a FEE with an amount and no currency, moves no
        cash (counted, broker 1's EUR would read 275.5). Sorted by (broker, currency) though broker 2's rows come first.
        These are the lines B compares after a restore: a cash row lost or altered shows up here.
        """
        print_section("L1 — cash per broker and currency")
        totals = control_totals(reference_book())
        assert totals.cash == EXPECTED_CASH, f"cash per (broker, currency): got {totals.cash}"
        assert totals.version == CONTROL_TOTALS_VERSION
        print_success("278.5 EUR and 545.5 USD on broker 1, 107 EUR and 510 USD on broker 2, GBP dropped")


# =============================================================================
# L2, L3 — quantity per (broker, asset)
# =============================================================================


class TestQuantities:
    def test_l2_quantities_follow_the_engine_rule_for_every_type(self):
        """Quantity per (broker, asset): every row with an asset and a quantity other than zero, any type, at 100 %.

        Asset 10 on broker 1: BUY 5, SELL 2, the split-linked ADJUSTMENT +3, an ADJUSTMENT-out of 1 and the TRANSFER out
        of 4 leave 1; the TRANSFER in gives broker 2 its 4. The rule is the portfolio engine's (every row with an asset
        and a quantity), not a list of types. Asset 11 on broker 2 keeps 0.000001, below the Dashboard's dust
        threshold: a control total sees every unit, so it is kept. Asset 12 on broker 1 is bought and sold back to
        zero: dropped from the totals, kept at 0 by ``position_quantities`` (the shape of ``native_balances``). The
        DIVIDEND on asset 13 moves no quantity and makes no line; row 17, a quantity without an asset, makes none.
        """
        print_section("L2 — quantity per broker and asset")
        assert Decimal("0.000001") < QUANTITY_DUST_THRESHOLD, "the dust line must sit below the Dashboard's threshold, or this test proves nothing about dust"
        book = reference_book()
        positions = position_quantities(book)
        assert positions == EXPECTED_POSITIONS, f"position_quantities: got {positions}"
        quantities = control_totals(book).quantities
        assert quantities == EXPECTED_QUANTITIES, f"control_totals quantities: got {quantities}"
        print_success("1 and 4 units of asset 10, 0.000001 of asset 11 kept, asset 12 dropped (kept at 0 by position_quantities)")

    def test_l3_as_of_keeps_the_rows_dated_on_or_before_the_day(self):
        """``position_quantities(as_of=day)`` keeps the rows with ``date <= day``, the day itself included.

        A line appears with its first quantity row on or before the day, never earlier: a day before any quantity row
        gives no line at all, not lines at zero. A line whose rows cancel by the day stays at zero; ``as_of=None`` is
        every row.
        """
        print_section("L3 — position_quantities as of a day")
        book = reference_book()
        mismatches = []
        for day, expected in AS_OF_POSITIONS:
            got = position_quantities(book, as_of=day)
            if got != expected:
                mismatches.append(f"{day}: got {got}, expected {expected}")
        assert mismatches == [], "position_quantities(as_of=...) differs on:\n" + "\n".join(mismatches)
        assert position_quantities(book, as_of=None) == EXPECTED_POSITIONS
        print_success(f"{len(AS_OF_POSITIONS)} days, the boundary day included")


# =============================================================================
# L4, L5 — what B was promised: what changes the totals, and what never does
# =============================================================================


class TestPromisesToBackup:
    @pytest.mark.parametrize("rewrite", INSENSITIVE_REWRITES)
    def test_l4_type_cost_basis_date_id_and_order_change_nothing(self, rewrite):
        """A reclassified, re-dated, renumbered or reordered ledger has the same totals, to the last character.

        The migration that repairs V-3's orphans rewrites a TRANSFER pair as two ADJUSTMENTs and a CASH_TRANSFER pair as
        a WITHDRAWAL and a DEPOSIT: a backup taken before it must still match a restore after it, so the totals never
        read a row's type. Nor a cost basis (the native cost is out of CP-15), nor a date (the whole ledger counts),
        nor an id, nor the order the rows come in.
        """
        print_section("L4 — what must not change the totals")
        assert control_totals(reference_book()) == EXPECTED_TOTALS, "the reference totals first: two empty results would be equal and prove nothing"
        rewritten = control_totals(rewrite(reference_book()))
        assert rewritten == EXPECTED_TOTALS, f"the totals changed: {rewritten}"
        assert rewritten.to_json() == EXPECTED_JSON, "the manifest changed"
        print_success("same totals, same manifest")

    @pytest.mark.parametrize(("change", "cash", "quantities"), SENSITIVE_CHANGES)
    def test_l5_a_lost_added_or_altered_row_changes_the_totals(self, change, cash, quantities):
        """Losing, adding or altering one row in broker, asset, currency, amount or quantity changes the totals.

        That difference is what B reports after a restore. The lines that change are exact: a lost BUY gives broker 1
        its cash back and takes its units; a quantity altered by one millionth moves its line by one millionth; a SELL
        altered to close the dust line drops it.
        """
        print_section("L5 — a difference means a lost, added or altered row")
        baseline = control_totals(reference_book())
        assert baseline == EXPECTED_TOTALS, "the reference totals first: two empty results would be equal and prove nothing"
        changed = control_totals(change(reference_book()))
        assert changed != baseline, "the change went unnoticed"
        assert json.dumps(changed.to_json()) != json.dumps(baseline.to_json()), "the manifest text did not change"
        assert changed == _expected_with(cash, quantities), f"not the lines the change touched: {changed}"
        print_success("the change shows, on the lines it touched")


# =============================================================================
# L6, L7 — the manifest: canonical text, read back
# =============================================================================


class TestManifest:
    def test_l6_to_json_is_canonical_text_in_a_fixed_order(self):
        """A ledger has one manifest text, whatever the order its rows are read in.

        Keys in the agreed order; lines by (broker, currency) and (broker, asset) though broker 3's rows come first;
        amounts as plain decimal text: "30" and "10", neither "30.000000" nor "3E+1"; "-100", not "-1E+2"; "0.000001";
        negatives with their sign. Broker 1's GBP line, a FEE of -0.000000, is zero and dropped, so "-0" never appears.
        """
        print_section("L6 — the manifest text")
        totals = control_totals(canonical_book())
        assert totals == EXPECTED_CANONICAL_TOTALS, f"got {totals}"
        assert json.dumps(totals.to_json()) == EXPECTED_CANONICAL_TEXT
        assert json.dumps(control_totals(list(reversed(canonical_book()))).to_json()) == EXPECTED_CANONICAL_TEXT, "rows read in another order gave another text"
        assert json.dumps(control_totals(reference_book()).to_json()) == EXPECTED_JSON_TEXT
        print_success("one text per ledger")

    def test_l6_every_amount_is_written_as_canonical_decimal_text(self):
        """``to_json`` writes any Decimal, read from SQLite with six decimals or in exponent form, as canonical text.

        Plain notation, never an exponent ("1E+2", "1E-7"); no trailing zero after the point and no trailing point; "0"
        for every zero, never "-0"; a leading "-" for negatives; every digit kept, even beyond the 28 digits of the
        default decimal context. The same rule for a balance and for a quantity.
        """
        print_section("L6 — canonical decimal text")
        mismatches = []
        for value, text in CANONICAL_TEXT:
            totals = ControlTotals(version=1, cash=((B1, "EUR", Decimal(value)),), quantities=((B1, A10, Decimal(value)),))
            expected = {"version": 1, "cash": [{"broker_id": 1, "currency": "EUR", "balance": text}], "quantities": [{"broker_id": 1, "asset_id": 10, "quantity": text}]}
            got = totals.to_json()
            if got != expected:
                mismatches.append(f"Decimal({value!r}): expected {text!r}, got {got}")
        assert mismatches == [], "amounts not written as canonical decimal text:\n" + "\n".join(mismatches)
        print_success(f"{len(CANONICAL_TEXT)} values, one text each")

    def test_l6_rows_read_in_one_pass_give_the_same_totals(self):
        """``transactions`` is an ``Iterable`` in the agreed signatures: a one-pass iterator gives the totals of a list.

        ``control_totals`` needs both halves of every row, its cash and its quantity; a second pass over an iterator
        would find it empty and lose one half without a word.
        """
        print_section("L6 — one pass over the rows")
        assert control_totals(iter(reference_book())) == EXPECTED_TOTALS
        assert position_quantities(iter(reference_book())) == EXPECTED_POSITIONS
        print_success("an iterator read once gives both halves")

    def test_l7_from_json_is_the_inverse_of_to_json(self):
        """``from_json`` reads back what ``to_json`` wrote, through ``json.dumps`` and ``json.loads`` as the manifest stores it.

        The agreed text read back gives the expected totals (tuples of tuples, Decimal amounts), and written again it is
        the same text: B compares the manifest of one backup with the totals recomputed after its restore.
        """
        print_section("L7 — the manifest read back")
        assert json.loads(EXPECTED_JSON_TEXT) == EXPECTED_JSON, "the two spellings of the expected manifest must agree"
        assert ControlTotals.from_json(EXPECTED_JSON) == EXPECTED_TOTALS
        assert EXPECTED_TOTALS.to_json() == EXPECTED_JSON
        for totals in (EXPECTED_TOTALS, EXPECTED_CANONICAL_TOTALS):
            manifest = json.dumps(totals.to_json())
            read_back = ControlTotals.from_json(json.loads(manifest))
            assert read_back == totals, f"{manifest} read back as {read_back}"
            assert json.dumps(read_back.to_json()) == manifest
        print_success("from_json(to_json(t)) == t, and the text is stable")

    @pytest.mark.parametrize("version", OTHER_VERSIONS)
    def test_l7_from_json_refuses_another_version(self, version):
        """A manifest written by another version of the method is not comparable: ``ValueError``, never a comparison."""
        print_section("L7 — another version")
        with pytest.raises(ValueError):
            ControlTotals.from_json(_manifest_with(("version",), version))
        print_success(f"version {version!r} refused")

    @pytest.mark.parametrize("data", MALFORMED_MANIFESTS)
    def test_l7_from_json_refuses_a_malformed_manifest(self, data):
        """Not an object, a missing key, an amount that is not decimal text: ``ValueError``, the one error B handles."""
        print_section("L7 — a malformed manifest")
        with pytest.raises(ValueError):
            ControlTotals.from_json(data)
        print_success("refused with ValueError")

    @pytest.mark.parametrize(("path", "text"), NOT_PLAIN_AMOUNTS)
    def test_l7_from_json_refuses_an_amount_that_is_not_plain_decimal_text(self, path, text):
        """J-27: a balance or a quantity that is not plain decimal text is malformed: ``ValueError``, the one error B handles.

        Plain decimal text has the shape of what ``to_json`` writes: an optional "-", 1 to 60 ASCII digits, then
        optionally "." and 1 to 60 more (60 is ``_EXACT.prec``). ``Decimal`` reads much more, and the canonical form then
        writes every digit out: "1E+50000000" costs 121 MB, so a hand-written manifest could exhaust memory in B's
        restore check. Red: an exponent, a "+", a space or a newline around the digits, underscores, Arabic-Indic or
        full-width digits, a 61st digit on either side (zeros count), a side without digits. GUARD: what ``Decimal``
        refuses already (an inner space, "Infinity", "NaN", a lone "-").
        """
        print_section("L7 — an amount that is not plain decimal text")
        with pytest.raises(ValueError):
            ControlTotals.from_json(_manifest_with(path, text))
        print_success(f"{path[-1]} refused with ValueError")

    @pytest.mark.parametrize(("path", "text", "canonical"), PLAIN_AMOUNTS)
    def test_l7_from_json_reads_plain_decimal_text_canonically(self, path, text, canonical):
        """GUARD (green today, stays green): plain decimal text up to the bound is read as today, ``Decimal`` made canonical.

        60 digits before the point, 60 after, both at once (120 digits, twice the precision of ``_EXACT``, kept to the
        last one), with a "-" that is not a digit; zeros ``to_json`` never writes: "-0" is 0, "007" is 7, "10.500" is
        10.5. The amount read is the canonical Decimal itself, the rest of the manifest is read as written, and
        ``to_json`` writes the canonical text back.
        """
        print_section("L7 — plain decimal text read back")
        section, index, _ = path
        read = ControlTotals.from_json(_manifest_with(path, text))
        amount = getattr(read, section)[index][2]
        assert amount.as_tuple() == Decimal(canonical).as_tuple(), f"read as {amount!r}, not as the canonical Decimal({canonical!r})"
        assert read.to_json() == _manifest_with(path, canonical), "written back as another manifest: the amount is not its canonical text, or another line changed"
        print_success(f"{path[-1]} read back canonically")


# =============================================================================
# L8 — exact sums
# =============================================================================


class TestExactness:
    @pytest.mark.parametrize("book", INEXACT_BOOKS)
    def test_l8_a_sum_that_cannot_be_exact_raises_inexact(self, book):
        """1E+70 and 1E-10 on one line: the module raises ``decimal.Inexact`` instead of writing a rounded total.

        Called inside the default context, where ``Inexact`` is not trapped, so the raise can only come from the
        module's own local context; the caller's context is the same after the call.
        """
        print_section("L8 — Inexact, never a rounded total")
        with decimal.localcontext(decimal.Context()):
            caller = _context_snapshot()
            with pytest.raises(decimal.Inexact):
                control_totals(book)
            assert _context_snapshot() == caller, "control_totals changed its caller's decimal context"
        print_success("decimal.Inexact raised")

    def test_l8_database_sized_amounts_sum_exactly(self):
        """Three amounts and three quantities at the top of ``Numeric(18, 6)`` sum exactly: no false alarm on a real ledger."""
        print_section("L8 — exact sums of database-sized amounts")
        book = [tx(row_id, DEPOSIT, D1, B1, currency="EUR", amount="999999999999.999999") for row_id in (1, 2, 3)]
        book += [tx(row_id, ADJUSTMENT, D1, B1, asset_id=A10, quantity="999999999999.999999") for row_id in (4, 5, 6)]
        with decimal.localcontext(decimal.Context()):
            caller = _context_snapshot()
            totals = control_totals(book)
            assert _context_snapshot() == caller, "control_totals changed its caller's decimal context"
        assert totals == ControlTotals(version=1, cash=((B1, "EUR", Decimal("2999999999999.999997")),), quantities=((B1, A10, Decimal("2999999999999.999997")),))
        assert totals.to_json() == {"version": 1, "cash": [{"broker_id": 1, "currency": "EUR", "balance": "2999999999999.999997"}], "quantities": [{"broker_id": 1, "asset_id": 10, "quantity": "2999999999999.999997"}]}
        print_success("2999999999999.999997, to the last digit")


# =============================================================================
# L9 — parity with the figures the rest of LibreFolio computes
# =============================================================================


class TestParity:
    def test_l9_quantities_match_the_average_cost_fold_and_cash_matches_native_balances(self):
        """The totals are the figures the rest of LibreFolio computes, not a third reconstruction.

        Quantities: the average-cost fold's at share 1 for the same rows (``cost_movement_from_transaction`` with the
        split link, ``CostPosition``, ``_fold_average_costs`` with nothing resolved: a missing rate never costs the fold
        a unit), its zero lines kept by ``position_quantities`` and dropped from the totals. Cash: ``native_balances``
        of the same movements, zero lines dropped. The book never sells more than it holds, where the fold would clamp.
        """
        print_section("L9 — parity with the average-cost fold and native_balances")
        book = reference_book()
        fold = _average_cost_quantities(book)
        assert fold == {(B1, A10): Decimal("1"), (B1, A12): Decimal("0"), (B2, A10): Decimal("4"), (B2, A11): Decimal("0.000001")}, f"the fold itself: {fold}"
        positions = position_quantities(book)
        flattened = {(broker_id, asset_id): quantity for broker_id, by_asset in positions.items() for asset_id, quantity in by_asset.items()}
        assert flattened == fold, f"position_quantities: {positions}"
        totals = control_totals(book)
        assert totals.quantities == tuple((broker_id, asset_id, quantity) for (broker_id, asset_id), quantity in sorted(fold.items()) if quantity != 0)
        movements = [cash_movement_from_transaction(row) for row in book]
        balances = native_balances(movement for movement in movements if movement is not None)
        assert totals.cash == tuple((broker_id, currency, balance) for broker_id, by_currency in sorted(balances.items()) for currency, balance in sorted(by_currency.items()) if balance != 0)
        print_success("the fold's quantities and native_balances' cash")


# =============================================================================
# L10 — compute_control_totals on private SQLite files
# =============================================================================


class TestOnFile:
    @pytest.mark.asyncio
    async def test_l0_an_empty_ledger_file_has_empty_totals(self, ledger_file):
        """GUARD: an empty ``transactions`` table, a fresh instance backed up, reads as version 1 and no line."""
        print_section("L0 — an empty ledger file")
        engine = await ledger_file("empty.db", [])
        with settings_forbidden() as settings_calls:
            totals = await _compute_on(engine)
        assert totals == ControlTotals(version=1, cash=(), quantities=())
        assert settings_calls == [], "get_settings() was called"
        print_success("no line, no settings")

    @pytest.mark.asyncio
    async def test_l10_compute_control_totals_reads_the_ledger_of_its_session_in_keyset_blocks(self, ledger_file, monkeypatch):
        """``compute_control_totals`` on a private SQLite file gives ``control_totals`` of the rows written into it.

        The file has the app schema and an engine of its own, as the copy B restores. SQLite does not give back what was
        written, ``Numeric(18, 6)`` returns six decimals (278.500000), and the totals and their text are the same all
        the same. Pinned on the way: blocks of 2 rows (``_BLOCK_SIZE`` patched on the module) give the totals of blocks
        of 5000, with at least one statement per two rows (keyset blocks, not one read); every statement is a SELECT of
        the agreed columns of ``transactions`` and of no other table (no price, no rate), never an SQL ``SUM``;
        ``get_settings`` raises during the whole call, wherever it is read from, and is never called.
        """
        print_section("L10 — compute_control_totals on a private SQLite file")
        book = reference_book()
        engine = await ledger_file("ledger.db", book)
        with captured_statements(engine) as whole_blocks, settings_forbidden() as settings_calls:
            whole = await _compute_on(engine)
        monkeypatch.setattr(ledger_totals, "_BLOCK_SIZE", 2)
        with captured_statements(engine) as pair_blocks, settings_forbidden() as pair_settings_calls:
            in_pairs = await _compute_on(engine)

        assert whole == EXPECTED_TOTALS, f"the totals of the file: {whole}"
        assert whole == control_totals(book), "the totals of the file must be control_totals of the rows written into it"
        assert whole.to_json() == EXPECTED_JSON, "amounts read back with six decimals must be written as canonical text"
        assert in_pairs == whole, f"blocks of 2 rows: {in_pairs}"
        assert in_pairs.to_json() == whole.to_json()
        assert settings_calls == [] and pair_settings_calls == [], "get_settings() was called"
        assert whole_blocks and pair_blocks, "no statement reached the engine of the session given: the ledger was read from somewhere else"
        problems = _statement_problems(whole_blocks + pair_blocks)
        assert problems == [], "statements beyond a read of the agreed columns of transactions:\n" + "\n".join(problems)
        assert len(pair_blocks) >= math.ceil(len(book) / 2), f"{len(book)} rows in blocks of 2 took {len(pair_blocks)} statement(s): not keyset blocks of _BLOCK_SIZE rows"
        assert len(whole_blocks) < len(pair_blocks), f"blocks of 5000 took {len(whole_blocks)} statement(s), blocks of 2 took {len(pair_blocks)}: _BLOCK_SIZE does not drive the reads"
        print_success(f"{len(book)} rows: {len(whole_blocks)} read(s) in blocks of 5000, {len(pair_blocks)} in blocks of 2, the same totals")

    @pytest.mark.asyncio
    async def test_l10_the_restore_check_on_other_files_in_the_same_process(self, ledger_file):
        """B's restore check end to end: the manifest of one file compared with totals recomputed from other files.

        Four files in one process, read in turn: the backup, another instance, a restored copy that lost a row (the SELL
        of row 23) and a faithful restored copy, then the backup again. Each gives the totals of its own rows: no module
        cache hands one file's totals to another, and the registered TTL caches are exactly as they were. The manifest,
        read back with ``from_json``, equals the faithful copy's totals and differs from the damaged copy's on the lines
        of the lost row.
        """
        print_section("L10 — the restore check, on four files in one process")
        backup = await ledger_file("backup.db", reference_book())
        other_instance = await ledger_file("other-instance.db", canonical_book())
        lost_row = await ledger_file("restored-with-a-lost-row.db", [row for row in reference_book() if row.id != 23])
        restored = await ledger_file("restored.db", reference_book())
        caches = runtime_cache.list_caches()
        with settings_forbidden() as settings_calls:
            manifest = json.dumps((await _compute_on(backup)).to_json())
            of_other_instance = await _compute_on(other_instance)
            of_lost_row = await _compute_on(lost_row)
            of_restored = await _compute_on(restored)
            of_backup_again = await _compute_on(backup)

        assert json.loads(manifest) == EXPECTED_JSON, f"the manifest of the backup: {manifest}"
        assert of_other_instance == EXPECTED_CANONICAL_TOTALS, f"another file in the same process: {of_other_instance}"
        assert of_restored == EXPECTED_TOTALS, f"the faithful restore: {of_restored}"
        assert ControlTotals.from_json(json.loads(manifest)) == of_restored, "the manifest must match a faithful restore"
        assert of_backup_again == of_restored, "the backup read again, after three other files"
        assert ControlTotals.from_json(json.loads(manifest)) != of_lost_row, "a restore that lost a row matched the manifest"
        assert of_lost_row == _expected_with({(B2, "USD"): "400"}, {(B2, A11): "10"}), f"the lost SELL of row 23: {of_lost_row}"
        assert settings_calls == [], "get_settings() was called"
        assert runtime_cache.list_caches() == caches, "a TTL cache changed while totals were computed"
        print_success("each file its own totals; the manifest matches the faithful restore and not the damaged one")


# =============================================================================
# L11 — static guard of the module's source
# =============================================================================

#: Modules the module never imports, nor anything under them nor a name from them, with the reason.
FORBIDDEN_MODULES = {
    "backend.app.config": "the settings, which would choose a database for B",
    "backend.app.services.fx": "the FX service: control totals need no rate",
    "backend.app.services.fx_providers": "the FX providers: no rate, no network",
    "backend.app.services.assets": "the asset services: no price",
    "backend.app.services.asset_source_providers": "the price providers: no price, no network",
    "backend.app.services.financial_math.price_marks": "prices: control totals need no price",
    "backend.app.utils.runtime.cache": "a module cache",
    "functools.lru_cache": "a module cache",
    "functools.cache": "a module cache",
    "functools.cached_property": "a module cache",
    "theine": "a module cache",
    "cachetools": "a module cache",
    "aiocache": "a module cache",
    "diskcache": "a module cache",
}
#: Names the module never imports, from anywhere, nor reads as an attribute, with the reason.
FORBIDDEN_NAMES = {
    "get_settings": "the settings, which would choose a database for B",
    "convert_bulk": "the FX service: control totals need no rate",
    "compute_native_cash": "the FX service, which it calls for every foreign movement",
    "compute_average_costs": "the FX service, which it calls for every acquisition",
    "get_ttl_cache": "a module cache",
    "lru_cache": "a module cache",
    "cached_property": "a module cache",
    "PriceHistory": "prices: control totals need no price",
    "FxRate": "rates: control totals need no exchange rate",
    "today": "today's date: totals must not depend on the day they are computed",
    "today_date": "today's date: totals must not depend on the day they are computed",
    "now": "the clock: totals must not depend on the moment they are computed",
    "utcnow": "the clock: totals must not depend on the moment they are computed",
}
#: What the agreed API defines at module level: a scan of a file without it would be a scan of the wrong file.
AGREED_API = frozenset({"CONTROL_TOTALS_VERSION", "_BLOCK_SIZE", "ControlTotals", "position_quantities", "control_totals", "compute_control_totals"})


def _dotted(node: ast.AST) -> str:
    """``a.b.c`` for a chain of attributes on a name; the empty string for anything else."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else ""
    return ""


def _docstring_ids(tree: ast.Module) -> set[int]:
    """The ``id`` of every docstring node: prose may say "never an SQL SUM(...)" without being one."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                found.add(id(first.value))
    return found


def _is_sql_sum(node: ast.AST, docstrings: set[int]) -> bool:
    """``func.sum`` or ``functions.sum``, ``sum`` imported from SQLAlchemy, or ``sum(`` in a string that is not a docstring."""
    if isinstance(node, ast.Attribute):
        return [part.lower() for part in _dotted(node).split(".")[-2:]] in (["func", "sum"], ["functions", "sum"])
    if isinstance(node, ast.ImportFrom):
        return (node.module or "").startswith("sqlalchemy") and any(alias.name.lower() == "sum" for alias in node.names)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return id(node) not in docstrings and SQL_SUM.search(node.value) is not None
    return False


def _module_reason(target: str) -> str | None:
    """Why the module ``target``, or the name inside one, is forbidden; None when it is not."""
    for module, reason in FORBIDDEN_MODULES.items():
        if target == module or target.startswith(f"{module}."):
            return reason
    return None


def _import_targets(node: ast.AST, package: str) -> list[str]:
    """What an import binds, fully qualified: ``a.b`` for ``import a.b``; ``a`` and each ``a.name`` for ``from a import name``.

    Relative forms resolve against ``package``, as the interpreter resolves them.
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        base = resolve_name("." * node.level + (node.module or ""), package)
        return [base, *(f"{base}.{alias.name}" for alias in node.names)]
    return []


def forbidden_constructs(source: str, package: str = LEDGER_TOTALS_PACKAGE) -> list[str]:
    """Everything in ``source`` that control totals must not do, one finding each; empty when the source is clean.

    ``ast.walk`` visits every node, so an import inside a function or under ``if TYPE_CHECKING:`` counts. Three
    detectors: an SQL ``SUM`` (Python's own ``sum()`` is a call, not a query, and stays allowed); an import of a
    forbidden module, or of a forbidden name from any module; a forbidden name read as an attribute (``date.today()``,
    ``datetime.now()``, ``config.get_settings()``, ``functools.cache``).
    """
    tree = ast.parse(source)
    docstrings = _docstring_ids(tree)
    findings: set[str] = set()
    for node in ast.walk(tree):
        if _is_sql_sum(node, docstrings):
            findings.add(f"line {node.lineno}: an SQL SUM — Numeric goes through a float on SQLite; sum the Decimals in Python")
        for target in _import_targets(node, package):
            reason = _module_reason(target) or FORBIDDEN_NAMES.get(target.rsplit(".", 1)[-1])
            if reason:
                findings.add(f"line {node.lineno}: imports {target} — {reason}")
        if isinstance(node, ast.Attribute):
            reason = FORBIDDEN_NAMES.get(node.attr) or _module_reason(_dotted(node))
            if reason:
                findings.add(f"line {node.lineno}: reads {_dotted(node) or node.attr} — {reason}")
    return sorted(findings)


def _module_level_names(tree: ast.Module) -> set[str]:
    """The names a module defines at its top level: functions, classes and assigned constants."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


#: Every shape the guard must report, written as if inside ``financial_math``, with a word its finding must contain.
FORBIDDEN_SHAPES = (
    ("from sqlalchemy import func, select\nstatement = select(func.sum(Transaction.amount))\n", "SQL SUM"),
    ("import sqlalchemy as sa\nstatement = sa.select(sa.func.SUM(Transaction.quantity))\n", "SQL SUM"),
    ("from sqlalchemy.sql.functions import sum as sql_sum\n", "SQL SUM"),
    ("from sqlalchemy import text\nquery = text('SELECT broker_id, SUM(amount) FROM transactions GROUP BY broker_id')\n", "SQL SUM"),
    ("query = f'select sum(quantity) from {table}'\n", "SQL SUM"),
    ("from backend.app.config import get_settings\n", "settings"),
    ("import backend.app.config\n", "settings"),
    ("from backend.app import config\n", "settings"),
    ("from ...config import get_settings\n", "settings"),
    ("async def load(session):\n    from backend.app.config import get_settings\n\n    return get_settings()\n", "settings"),
    ("database_url = app_config.get_settings().DATABASE_URL\n", "settings"),
    ("from backend.app.utils.runtime.cache import get_ttl_cache\n", "cache"),
    ("from functools import lru_cache\n", "cache"),
    ("from functools import cache\n", "cache"),
    ("import functools\n\n\n@functools.cache\ndef totals():\n    return None\n", "cache"),
    ("import cachetools\n", "cache"),
    ("from theine import Cache\n", "cache"),
    ("from backend.app.services.fx.conversion import convert_bulk\n", "FX"),
    ("from backend.app.services import fx\n", "FX"),
    ("from backend.app.services.financial_math.native_cash import compute_native_cash\n", "FX"),
    ("from backend.app.services.financial_math import average_cost\n\nresult = average_cost.compute_average_costs(None, [], report_currency='EUR')\n", "FX"),
    ("from backend.app.db.models import FxRate, Transaction\n", "rates"),
    ("from backend.app.db.models import PriceHistory\n", "prices"),
    ("from backend.app.services.financial_math.price_marks import resolve_marks\n", "prices"),
    ("from datetime import date\n\nday = date.today()\n", "today"),
    ("from datetime import date as date_type\n\nday = date_type.today()\n", "today"),
    ("import datetime\n\nmoment = datetime.datetime.now()\n", "clock"),
    ("from backend.app.utils.datetime_utils import today_date\n", "today"),
)

#: A plausible implementation the guard must leave alone: docstrings that mention SUM(...), Python's sum(), keyset reads.
ALLOWED_SOURCE = '''"""Control totals of the ledger. Never an SQL ``SUM(amount)``: Numeric goes through a float on SQLite."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal, Inexact, localcontext

from sqlalchemy import select

from backend.app.db.models import Transaction
from backend.app.services.financial_math.native_cash import cash_movement_from_transaction, native_balances

CONTROL_TOTALS_VERSION = 1
_BLOCK_SIZE = 5000


@dataclass(frozen=True, slots=True)
class ControlTotals:
    """Sums with Python's sum(), never with SUM( in a query."""

    version: int


def position_quantities(transactions: Iterable, as_of: date_type | None = None) -> Decimal:
    """Every row with an asset and a quantity; never a SUM(quantity) query."""
    with localcontext() as context:
        context.traps[Inexact] = True
        return sum((row.quantity for row in transactions if as_of is None or row.date <= as_of), Decimal(0))


async def compute_control_totals(session):
    statement = select(Transaction.id, Transaction.currency, Transaction.amount).where(Transaction.id > 0).order_by(Transaction.id).limit(_BLOCK_SIZE)
    rows = (await session.execute(statement)).all()
    return native_balances(movement for row in rows if (movement := cash_movement_from_transaction(row)) is not None)
'''


class TestSourceGuard:
    def test_l11_the_guard_reports_every_forbidden_shape_and_nothing_allowed(self):
        """GUARD: the detectors see what they look for, so their silence on the module can be believed.

        Each forbidden shape, written as if inside ``financial_math``, is reported with its reason; a plausible
        implementation, whose docstrings mention SUM(...) and which sums with Python's ``sum()`` and reads in keyset
        blocks, is reported for nothing.
        """
        print_section("L11 — the guard's own detectors")
        missed = []
        for source, word in FORBIDDEN_SHAPES:
            findings = forbidden_constructs(source)
            if not any(word in finding for finding in findings):
                missed.append(f"{source!r}: expected a finding naming {word!r}, got {findings}")
        assert missed == [], "shapes the guard did not report:\n" + "\n".join(missed)
        assert forbidden_constructs(ALLOWED_SOURCE) == [], "the guard reports an allowed implementation"
        print_success(f"{len(FORBIDDEN_SHAPES)} forbidden shapes reported, the allowed implementation left alone")

    def test_l11_the_module_never_sums_in_sql_nor_reads_settings_caches_rates_prices_or_the_clock(self):
        """GUARD: ``ledger_totals.py`` holds nothing that could make two computations on the same file disagree.

        No SQL ``SUM`` (Numeric goes through a float on SQLite); no settings (B passes the session of a backup copy,
        and the settings would name another database); no module cache (B computes on two files in one process); no
        FX service beyond what ``native_cash`` imports for its own use, no price, no rate; no ``date.today()`` and no
        clock (the totals of a backup must not depend on the day they are recomputed).
        """
        print_section("L11 — the module's source")
        source = LEDGER_TOTALS_SOURCE.read_text(encoding="utf-8")
        missing = sorted(AGREED_API - _module_level_names(ast.parse(source)))
        assert missing == [], f"{LEDGER_TOTALS_SOURCE} does not define {missing}: the scan would prove nothing about the module of the API"
        findings = forbidden_constructs(source)
        assert findings == [], "ledger_totals.py:\n" + "\n".join(findings)
        print_success("no SQL SUM, settings, cache, rate, price or clock")
