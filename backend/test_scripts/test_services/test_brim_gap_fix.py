"""
Test Suite: BRIM report sets, phase A3 — gap-fix: the bank's truth points against LibreFolio's state

Written red-first, before the code (plan step 4, §3 A3), with the conventions of
``test_brim_report_sets.py``: every new symbol is looked up inside the test that
needs it (``_schema``, ``_gap``, ``_balances_at_end_of``, ``_balances_before``,
``_absorbed``), so collection always succeeds and each test fails on its own,
naming what phase A3 still has to add. A test whose docstring starts with
"Fixture guard" checks this file's own infrastructure, and the one starting with
"Retro-compatibility guard" checks behaviour A3 must keep: both pass before and
after A3.

Covered, by item of the A3 interface:

1. ``transaction_service``: ``_get_balances_before_date`` gains ``exclude_tx_ids``,
   and the new ``get_balances_at_end_of`` sums a broker's rows dated on or before
   a day (the day itself included, other brokers never, any collection of
   excluded ids);
2. schemas: ``BRIMAbsorbedRow``, the additive ``BRIMAbsorbed.rows`` and
   ``opening_cash`` (A1 payloads stay valid), ``BRIMGapFixRequest`` and the
   response family, from ``BRIMGapFixCashRow`` to ``BRIMGapFixResponse``;
3. the new service ``brim_gap_fix.compute_gap_fix``:
   A the plugin (unknown: ``BRIMSetPluginNotFound``; any registered plugin; tag
     and name read from it);
   B first import, an import that overlaps the previous one, a gap;
   C cash: a deposit or a withdrawal beyond 0.01, one correction per currency;
   D positions: exact both ways, at_least, the cost or a blocking todo, assets
     left unresolved;
   E LibreFolio's state at C: pending deletes, pending creates, selection, other
     brokers, later rows, earlier proposals;
   F the explanation: absorbed rows matched one to one, the opening cash, the
     unexplained part (design A12);
   G verifications;
   H the proposals: tags, date, broker, deterministic description, nothing
     written;
   I order and consistency: input order, one import against three, a removed
     proposal (D-S24), two sets on an empty broker (scenario 8).

Every test gets a private in-memory SQLite database with the ORM schema
(``db_session``), holding two brokers and three assets: never the shared test
database. All data is synthetic. Amounts and quantities are compared as numbers,
never as strings, and the proposals of a checkpoint as a multiset: the interface
fixes neither their order nor the scale of their decimals.

Design: LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/design-phase00BrimReportSets.md (v5.3), §3.6, §11.3 (scenario 8), D-S24
Plan: LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md, §3 A3
"""

from __future__ import annotations

import importlib
import inspect
from collections import Counter
from collections.abc import AsyncIterator, Iterable, Iterator, Sequence
from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, NoReturn, Optional, Tuple

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from backend.app.db.models import Asset, Broker, Transaction, TransactionType
from backend.app.schemas import brim as brim_schemas
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMAbsorbed, BRIMCheckpoint, BRIMFieldTodo, BRIMNotice, BRIMParseOutput, BRIMTruthCash, BRIMTruthPosition, BRIMVerification
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services import brim_report_sets
from backend.app.services.brim_provider import BRIMProvider
from backend.app.services.provider_registry import BRIMProviderRegistry
from backend.app.services.transaction_service import TransactionService

A3 = "A3"
GAP_FIX_MODULE = "backend.app.services.brim_gap_fix"

BROKER_ID = 42
OTHER_BROKER_ID = 43
ASSET_A, ASSET_B, ASSET_C = 101, 102, 103
UNRESOLVED_ASSET = FAKE_ASSET_ID_BASE  # a fake id the wizard did not resolve

# Any registered plugin is accepted: the gap-fix reads only its history tag and its name.
GENERIC_CODE = "broker_generic_csv"
GENERIC_TAG = "generic_csv"
GENERIC_NAME = "Generic CSV"
FAKE_BANK_CODE = "broker_fake_gap_bank"
FAKE_BANK_TAG = "fake_gap_history"  # deliberately not the code without "broker_": the tag must come from history_tag
FAKE_BANK_NAME = "Fake Gap Bank (tests)"
UNKNOWN_CODE = "no_such_plugin_a3"
GAP_FIX_TAG = "gap_fix"
COST_TODO = ("cost_basis_override", "blocker", "gap_fix_cost")

# The eves of three yearly segments, where a report-set plugin dates its checkpoints.
EVE_2023, EVE_2024, EVE_2025 = date(2023, 12, 31), date(2024, 12, 31), date(2025, 12, 31)

DEPOSIT, WITHDRAWAL, BUY, SELL, DIVIDEND, ADJUSTMENT = (
    TransactionType.DEPOSIT,
    TransactionType.WITHDRAWAL,
    TransactionType.BUY,
    TransactionType.SELL,
    TransactionType.DIVIDEND,
    TransactionType.ADJUSTMENT,
)


# =============================================================================
# HELPERS — new symbols are looked up inside each test, never at import time
# =============================================================================


def _missing(what: str) -> NoReturn:
    """Fail the current test (not the collection), naming what phase A3 has to add."""
    pytest.fail(f"{what}: not implemented yet (BRIM report sets, phase {A3})", pytrace=False)


def _schema(name: str) -> Any:
    """A schema class of ``backend.app.schemas.brim``."""
    found = getattr(brim_schemas, name, None)
    if found is None:
        _missing(f"backend.app.schemas.brim.{name} does not exist")
    return found


def _require_fields(model: Any, *names: str) -> None:
    """The model declares every field in ``names``."""
    absent = [name for name in names if name not in model.model_fields]
    if absent:
        _missing(f"{model.__name__} has no field {', '.join(absent)}")


def _gap_fix_module() -> Optional[ModuleType]:
    """The new service module, or None while it does not exist. An import error *inside* it is not swallowed."""
    try:
        return importlib.import_module(GAP_FIX_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != GAP_FIX_MODULE:
            raise
        return None


def _gap(name: str) -> Any:
    """A function of the new service module ``backend.app.services.brim_gap_fix``."""
    module = _gap_fix_module()
    if module is None:
        _missing(f"{GAP_FIX_MODULE} does not exist")
    found = getattr(module, name, None)
    if found is None:
        _missing(f"{GAP_FIX_MODULE}.{name} does not exist")
    return found


def _balances_at_end_of(session: AsyncSession) -> Any:
    """The new ``TransactionService.get_balances_at_end_of``, bound to ``session``."""
    method = getattr(TransactionService(session), "get_balances_at_end_of", None)
    if method is None:
        _missing("TransactionService.get_balances_at_end_of does not exist")
    return method


def _balances_before(session: AsyncSession) -> Any:
    """``TransactionService._get_balances_before_date`` bound to ``session``, once it takes ``exclude_tx_ids``."""
    method = TransactionService(session)._get_balances_before_date
    if "exclude_tx_ids" not in inspect.signature(method).parameters:
        _missing("TransactionService._get_balances_before_date() has no 'exclude_tx_ids' parameter")
    return method


def _d(day: str) -> date:
    return date.fromisoformat(day)


def _nonzero(balances: Dict[Any, Decimal]) -> Dict[Any, Decimal]:
    """A balance map without its zero entries: whether a fully excluded key is dropped or kept at zero is not part of the contract."""
    return {key: value for key, value in balances.items() if value != 0}


def _decimals(mapping: Dict[Any, str]) -> Dict[Any, Decimal]:
    return {key: Decimal(value) for key, value in mapping.items()}


# -----------------------------------------------------------------------------
# Truth points and transactions (A1 types, plus the A3 absorbed rows)
# -----------------------------------------------------------------------------


def _money(code: str, amount: str) -> Currency:
    return Currency(code=code, amount=Decimal(amount))


def _truth(currency: str, amount: str) -> BRIMTruthCash:
    """A cash balance the bank states."""
    return BRIMTruthCash(currency=currency, amount=Decimal(amount))


def _position(asset_id: int, quantity: str, exactness: str = "exact", unit_cost: Optional[Currency] = None) -> BRIMTruthPosition:
    """A position the bank's files prove, exactly or as a minimum."""
    return BRIMTruthPosition(asset_id=asset_id, quantity=Decimal(quantity), exactness=exactness, unit_cost=unit_cost)


def _checkpoint(as_of: date, kind: str = "gap", *, cash: Sequence[BRIMTruthCash] = (), positions: Sequence[BRIMTruthPosition] = (), absorbed: Optional[BRIMAbsorbed] = None) -> BRIMCheckpoint:
    return BRIMCheckpoint(as_of=as_of, kind=kind, cash=list(cash), positions=list(positions), absorbed=absorbed if absorbed is not None else BRIMAbsorbed())


def _verification(as_of: date, *cash: BRIMTruthCash) -> BRIMVerification:
    return BRIMVerification(as_of=as_of, cash=list(cash))


def _absorbed(rows: Sequence[Tuple[str, str, str]] = (), opening_cash: Sequence[BRIMTruthCash] = (), count: Optional[int] = None) -> BRIMAbsorbed:
    """The rows a checkpoint summarises, each ``(value date, currency, amount)``, and the opening balance: the A3 fields of ``BRIMAbsorbed``."""
    _require_fields(BRIMAbsorbed, "rows", "opening_cash")
    absorbed_row = _schema("BRIMAbsorbedRow")
    listed = [absorbed_row(as_of=_d(day), currency=currency, amount=Decimal(amount)) for day, currency, amount in rows]
    return BRIMAbsorbed(count=len(listed) if count is None else count, rows=listed, opening_cash=list(opening_cash))


def _tx(tx_type: TransactionType, day: str, *, cash: Optional[Tuple[str, str]] = None, asset_id: Optional[int] = None, quantity: str = "0", broker_id: int = BROKER_ID) -> TXCreateItem:
    """An unsaved transaction, as the wizard selects it or the editor holds it."""
    return TXCreateItem(broker_id=broker_id, type=tx_type, date=_d(day), asset_id=asset_id, quantity=Decimal(quantity), cash=_money(*cash) if cash else None)


def _request(
    *,
    checkpoints: Sequence[BRIMCheckpoint] = (),
    verifications: Sequence[BRIMVerification] = (),
    selection: Sequence[TXCreateItem] = (),
    pending_creates: Sequence[TXCreateItem] = (),
    pending_delete_tx_ids: Sequence[int] = (),
    plugin_code: str = GENERIC_CODE,
    broker_id: int = BROKER_ID,
) -> Any:
    """A ``BRIMGapFixRequest`` for ``BROKER_ID`` with the generic CSV plugin, unless told otherwise."""
    return _schema("BRIMGapFixRequest")(
        broker_id=broker_id,
        plugin_code=plugin_code,
        checkpoints=list(checkpoints),
        verifications=list(verifications),
        selection=list(selection),
        pending_creates=list(pending_creates),
        pending_delete_tx_ids=list(pending_delete_tx_ids),
    )


async def _run(session: AsyncSession, **request: Any) -> Any:
    """``compute_gap_fix`` on ``_request(**request)``: the service is looked up first, so a missing module is what the test reports."""
    compute_gap_fix = _gap("compute_gap_fix")
    return await compute_gap_fix(session, _request(**request))


# -----------------------------------------------------------------------------
# The private database
# -----------------------------------------------------------------------------


def _saved(tx_type: TransactionType, day: str, *, amount: str = "0", currency: Optional[str] = None, asset_id: Optional[int] = None, quantity: str = "0", broker_id: int = BROKER_ID) -> Transaction:
    """A transaction already in LibreFolio's database (sums do not look at its type, the type only keeps the row realistic)."""
    return Transaction(broker_id=broker_id, type=tx_type, date=_d(day), amount=Decimal(amount), currency=currency, asset_id=asset_id, quantity=Decimal(quantity))


async def _add(session: AsyncSession, *rows: Transaction) -> List[Transaction]:
    """Save ``rows`` in the private database; they come back with their ids."""
    session.add_all(rows)
    await session.commit()
    return list(rows)


async def _commit_items(session: AsyncSession, items: Iterable[TXCreateItem]) -> None:
    """Save unsaved transactions the way the batch pipeline does (``apply_creates``): here, "the user accepted and saved them"."""
    session.add_all(
        [
            Transaction(
                broker_id=item.broker_id,
                asset_id=item.asset_id,
                type=item.type,
                date=item.date,
                quantity=item.quantity,
                amount=item.get_amount(),
                currency=item.get_currency(),
                tags=item.get_tags_csv(),
                description=item.description,
                cost_basis_override=item.cost_basis_override.amount if item.cost_basis_override else None,
                cost_basis_currency=item.cost_basis_override.code if item.cost_basis_override else None,
            )
            for item in items
        ]
    )
    await session.commit()


async def _db_totals(session: AsyncSession, broker_id: int = BROKER_ID) -> Tuple[Dict[str, Decimal], Dict[int, Decimal]]:
    """Cash per currency and quantity per asset of every saved row of the broker, summed in Python (independent of the code under test)."""
    rows = (await session.execute(select(Transaction.currency, Transaction.amount, Transaction.asset_id, Transaction.quantity).where(Transaction.broker_id == broker_id))).all()
    cash: Dict[str, Decimal] = {}
    positions: Dict[int, Decimal] = {}
    for currency, amount, asset_id, quantity in rows:
        if currency:
            cash[currency] = cash.get(currency, Decimal(0)) + amount
        if asset_id:
            positions[asset_id] = positions.get(asset_id, Decimal(0)) + quantity
    return _nonzero(cash), _nonzero(positions)


async def _transaction_count(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(Transaction))).scalar_one()


@asynccontextmanager
async def _private_database() -> AsyncIterator[AsyncSession]:
    """A private in-memory SQLite database with the ORM schema, both brokers and the three assets."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        session.add_all([Broker(id=broker_id, name=f"Gap-fix broker {broker_id}") for broker_id in (BROKER_ID, OTHER_BROKER_ID)])
        session.add_all([Asset(id=asset_id, display_name=f"Gap-fix asset {asset_id}", currency="EUR") for asset_id in (ASSET_A, ASSET_B, ASSET_C)])
        await session.commit()
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """This test's own database: never the shared test database."""
    async with _private_database() as session:
        yield session


# -----------------------------------------------------------------------------
# A test-only plugin whose history tag is not derived from its code
# -----------------------------------------------------------------------------


class _FakeGapBankProvider(BRIMProvider):
    """Test-only single-file plugin: it never claims a file, and its ``history_tag`` is not its code without ``broker_``."""

    @property
    def provider_code(self) -> str:
        return FAKE_BANK_CODE

    @property
    def provider_name(self) -> str:
        return FAKE_BANK_NAME

    @property
    def description(self) -> str:
        return "Test-only plugin for the gap-fix tests."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def history_tag(self) -> str:
        return FAKE_BANK_TAG

    def can_parse(self, file_path: Path) -> bool:
        return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        return BRIMParseOutput()


@pytest.fixture
def fake_bank_plugin() -> Iterator[BRIMProvider]:
    """Register the fake for this test only, then put the registry back exactly as it was (discovery first, as in ``test_brim_report_sets.py``)."""
    BRIMProviderRegistry.auto_discover()
    registered = BRIMProviderRegistry._providers
    snapshot = dict(registered)
    assert FAKE_BANK_CODE not in snapshot, "the fake gap-fix plugin leaked out of a previous test"
    BRIMProviderRegistry.register(_FakeGapBankProvider)
    try:
        plugin = BRIMProviderRegistry.get_provider_instance(FAKE_BANK_CODE)
        assert isinstance(plugin, _FakeGapBankProvider)
        yield plugin
    finally:
        registered.clear()
        registered.update(snapshot)


# -----------------------------------------------------------------------------
# Reading a response
# -----------------------------------------------------------------------------


def _at(response: Any, as_of: date) -> Any:
    """The result of the checkpoint dated ``as_of``: exactly one per checkpoint."""
    found = [item for item in response.checkpoints if item.as_of == as_of]
    assert len(found) == 1, f"one result expected for the checkpoint of {as_of}, got {[item.as_of for item in response.checkpoints]}"
    return found[0]


def _verified(response: Any, as_of: date) -> Any:
    """The result of the verification dated ``as_of``: exactly one per verification."""
    found = [item for item in response.verifications if item.as_of == as_of]
    assert len(found) == 1, f"one result expected for the verification of {as_of}, got {[item.as_of for item in response.verifications]}"
    return found[0]


def _cash_rows(result: Any) -> Dict[str, Tuple[Decimal, Decimal, Decimal]]:
    """``{currency: (bank, librefolio, difference)}`` of a checkpoint or verification result."""
    return {row.currency: (row.bank, row.librefolio, row.difference) for row in result.cash}


def _cash_row(bank: str, librefolio: str, difference: str) -> Tuple[Decimal, Decimal, Decimal]:
    return Decimal(bank), Decimal(librefolio), Decimal(difference)


def _position_rows(result: Any) -> Dict[int, Tuple[str, Decimal, Decimal, Decimal]]:
    """``{asset_id: (exactness, bank, librefolio, difference)}`` of a checkpoint result."""
    return {row.asset_id: (row.exactness, row.bank, row.librefolio, row.difference) for row in result.positions}


def _position_row(exactness: str, bank: str, librefolio: str, difference: str) -> Tuple[str, Decimal, Decimal, Decimal]:
    return exactness, Decimal(bank), Decimal(librefolio), Decimal(difference)


def _amounts(items: Iterable[BRIMTruthCash]) -> Dict[str, Decimal]:
    """A per-currency list (missing, opening or unexplained cash) as ``{currency: amount}``."""
    return {item.currency: item.amount for item in items}


def _num(value: Any) -> str:
    """A number in plain notation, whatever its scale: ``523.400000`` and ``523.40`` are both ``523.4``."""
    return format(Decimal(value).normalize() + 0, "f")


def _key(item: TXCreateItem) -> Tuple[str, str, int, int, str, str, str, str]:
    """What a proposal does: type, date, broker, asset, quantity, cash and cost basis. A zero cash counts as no cash."""
    cash = item.cash if item.cash is not None and not item.cash.is_zero() else None
    cost = item.cost_basis_override
    return (item.type.value, item.date.isoformat(), item.broker_id, item.asset_id or 0, _num(item.quantity), cash.code if cash else "", _num(cash.amount) if cash else "", f"{cost.code} {_num(cost.amount)}" if cost else "")


def _expected(tx_type: TransactionType, as_of: date, *, cash: Optional[Tuple[str, str]] = None, asset_id: Optional[int] = None, quantity: str = "0", cost: Optional[Tuple[str, str]] = None) -> Tuple[str, str, int, int, str, str, str, str]:
    """The ``_key`` of the proposal a test expects, for ``BROKER_ID``."""
    return (tx_type.value, as_of.isoformat(), BROKER_ID, asset_id or 0, _num(quantity), cash[0] if cash else "", _num(cash[1]) if cash else "", f"{cost[0]} {_num(cost[1])}" if cost else "")


def _deposit(as_of: date, currency: str, amount: str) -> Tuple[str, str, int, int, str, str, str, str]:
    return _expected(DEPOSIT, as_of, cash=(currency, amount))


def _withdrawal(as_of: date, currency: str, amount: str) -> Tuple[str, str, int, int, str, str, str, str]:
    return _expected(WITHDRAWAL, as_of, cash=(currency, amount))


def _adjustment(as_of: date, asset_id: int, quantity: str, cost: Optional[Tuple[str, str]] = None) -> Tuple[str, str, int, int, str, str, str, str]:
    return _expected(ADJUSTMENT, as_of, asset_id=asset_id, quantity=quantity, cost=cost)


def _proposals(result: Any) -> Counter:
    """The proposals of one checkpoint result, as a multiset of ``_key``."""
    return Counter(_key(item) for item in result.proposals)


def _todo_kinds(result: Any) -> List[Tuple[str, str, str]]:
    return [(todo.field, todo.severity, todo.reason_code) for todo in result.todos]


def _todo_target(result: Any, todo: Any) -> TXCreateItem:
    """The proposal a todo points at: ``tx_index`` indexes this checkpoint's own proposals."""
    assert 0 <= todo.tx_index < len(result.proposals), f"tx_index {todo.tx_index} is outside the {len(result.proposals)} proposals of {result.as_of}"
    return result.proposals[todo.tx_index]


# =============================================================================
# 1 — TRANSACTION SERVICE: balances at a date, without the rows being deleted
# =============================================================================


async def _seed_ledger(session: AsyncSession) -> Dict[str, Transaction]:
    """A small ledger for both brokers, by name.

    Own broker, at the end of each day: 2024-03-30 EUR 600, A 10 · 2024-03-31 EUR 600,
    USD 20, A 10, B 3 · 2024-04-01 EUR 590, USD 20, A 8, B 3. The other broker holds
    EUR 7776 and A 99, which must never reach the own broker's balances.
    """
    rows = {
        "deposit_eur": _saved(DEPOSIT, "2024-01-10", amount="1000", currency="EUR"),
        "buy_a": _saved(BUY, "2024-02-01", amount="-400", currency="EUR", asset_id=ASSET_A, quantity="10"),
        "deposit_usd": _saved(DEPOSIT, "2024-03-31", amount="50", currency="USD"),
        "buy_b": _saved(BUY, "2024-03-31", amount="-30", currency="USD", asset_id=ASSET_B, quantity="3"),
        "withdrawal": _saved(WITHDRAWAL, "2024-04-01", amount="-100", currency="EUR"),
        "sell_a": _saved(SELL, "2024-04-01", amount="90", currency="EUR", asset_id=ASSET_A, quantity="-2"),
        "foreign_deposit": _saved(DEPOSIT, "2024-01-15", amount="7777", currency="EUR", broker_id=OTHER_BROKER_ID),
        "foreign_buy": _saved(BUY, "2024-02-02", amount="-1", currency="EUR", asset_id=ASSET_A, quantity="99", broker_id=OTHER_BROKER_ID),
    }
    await _add(session, *rows.values())
    return rows


class TestBalancesBeforeDate:
    """1 — ``_get_balances_before_date(broker_id, before_date, exclude_tx_ids=())``: the excluded rows leave both sums; nothing else changes."""

    @pytest.mark.asyncio
    async def test_retro_compatibility_guard_without_exclusions(self, db_session: AsyncSession) -> None:
        """Retro-compatibility guard (passes before and after A3): strictly before the date, per currency and per asset, this broker only."""
        await _seed_ledger(db_session)

        cash, assets = await TransactionService(db_session)._get_balances_before_date(BROKER_ID, _d("2024-03-31"))

        assert (_nonzero(cash), _nonzero(assets)) == ({"EUR": Decimal("600")}, {ASSET_A: Decimal("10")})

    @pytest.mark.asyncio
    async def test_excluded_ids_leave_both_sums(self, db_session: AsyncSession) -> None:
        before = _balances_before(db_session)
        ledger = await _seed_ledger(db_session)

        cash, assets = await before(BROKER_ID, _d("2024-04-01"), exclude_tx_ids=[ledger["buy_a"].id, ledger["deposit_usd"].id])

        assert (_nonzero(cash), _nonzero(assets)) == ({"EUR": Decimal("1000"), "USD": Decimal("-30")}, {ASSET_B: Decimal("3")})

    @pytest.mark.asyncio
    async def test_ids_outside_the_sums_change_nothing(self, db_session: AsyncSession) -> None:
        """Another broker's rows, rows dated from the day on and unknown ids: excluding them changes nothing."""
        before = _balances_before(db_session)
        ledger = await _seed_ledger(db_session)
        outside = [ledger["foreign_deposit"].id, ledger["foreign_buy"].id, ledger["withdrawal"].id, ledger["sell_a"].id, 987654]

        plain_cash, plain_assets = await before(BROKER_ID, _d("2024-04-01"))
        cash, assets = await before(BROKER_ID, _d("2024-04-01"), exclude_tx_ids=outside)

        assert (_nonzero(cash), _nonzero(assets)) == (_nonzero(plain_cash), _nonzero(plain_assets)) == ({"EUR": Decimal("600"), "USD": Decimal("20")}, {ASSET_A: Decimal("10"), ASSET_B: Decimal("3")})


class TestBalancesAtEndOf:
    """1 — ``get_balances_at_end_of(broker_id, as_of, exclude_tx_ids=())``: the broker's rows dated on or before ``as_of``, minus the excluded ones."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("day", "cash", "assets"),
        [
            pytest.param("2024-03-30", {"EUR": "600"}, {ASSET_A: "10"}, id="the-eve"),
            pytest.param("2024-03-31", {"EUR": "600", "USD": "20"}, {ASSET_A: "10", ASSET_B: "3"}, id="the-day-itself-counts"),
            pytest.param("2024-04-01", {"EUR": "590", "USD": "20"}, {ASSET_A: "8", ASSET_B: "3"}, id="the-next-day"),
        ],
    )
    async def test_rows_dated_on_or_before_the_day(self, db_session: AsyncSession, day: str, cash: Dict[str, str], assets: Dict[int, str]) -> None:
        at_end_of = _balances_at_end_of(db_session)
        await _seed_ledger(db_session)

        got_cash, got_assets = await at_end_of(BROKER_ID, _d(day))

        assert (_nonzero(got_cash), _nonzero(got_assets)) == (_decimals(cash), _decimals(assets))
        assert all(isinstance(value, Decimal) for value in [*got_cash.values(), *got_assets.values()])

    @pytest.mark.asyncio
    async def test_other_brokers_never_count(self, db_session: AsyncSession) -> None:
        """The other broker's balances are its own rows only; the own broker's rows never reach them (nor the reverse, see above)."""
        at_end_of = _balances_at_end_of(db_session)
        await _seed_ledger(db_session)

        cash, assets = await at_end_of(OTHER_BROKER_ID, EVE_2024)

        assert (_nonzero(cash), _nonzero(assets)) == ({"EUR": Decimal("7776")}, {ASSET_A: Decimal("99")})

    @pytest.mark.asyncio
    @pytest.mark.parametrize("container", [list, tuple, set, frozenset], ids=["list", "tuple", "set", "frozenset"])
    async def test_excluded_ids_leave_both_sums(self, db_session: AsyncSession, container: type) -> None:
        """``exclude_tx_ids`` is any collection of ids (the gap-fix passes the editor's pending deletes)."""
        at_end_of = _balances_at_end_of(db_session)
        ledger = await _seed_ledger(db_session)

        cash, assets = await at_end_of(BROKER_ID, _d("2024-04-01"), exclude_tx_ids=container([ledger["buy_b"].id, ledger["withdrawal"].id]))

        assert (_nonzero(cash), _nonzero(assets)) == ({"EUR": Decimal("690"), "USD": Decimal("50")}, {ASSET_A: Decimal("8")})

    @pytest.mark.asyncio
    async def test_empty_broker(self, db_session: AsyncSession) -> None:
        at_end_of = _balances_at_end_of(db_session)

        cash, assets = await at_end_of(BROKER_ID, EVE_2024)

        assert (_nonzero(cash), _nonzero(assets)) == ({}, {})

    @pytest.mark.asyncio
    @pytest.mark.parametrize("day", ["2024-03-30", "2024-03-31", "2024-04-01"])
    async def test_is_the_balance_before_the_next_day(self, db_session: AsyncSession, day: str) -> None:
        """The end of ``C`` is the eve of ``C`` + 1 day, exclusions included: one state under two names (plan §3 A3)."""
        at_end_of = _balances_at_end_of(db_session)
        before = _balances_before(db_session)
        ledger = await _seed_ledger(db_session)
        excluded = [ledger["deposit_eur"].id, ledger["sell_a"].id]

        end_cash, end_assets = await at_end_of(BROKER_ID, _d(day), exclude_tx_ids=excluded)
        eve_cash, eve_assets = await before(BROKER_ID, _d(day) + timedelta(days=1), exclude_tx_ids=excluded)

        assert _nonzero(end_cash) and _nonzero(end_assets), "precondition: something to compare"
        assert (_nonzero(end_cash), _nonzero(end_assets)) == (_nonzero(eve_cash), _nonzero(eve_assets))


# =============================================================================
# 2 — SCHEMAS
# =============================================================================


class TestAbsorbedRowSchema:
    """2 — ``BRIMAbsorbedRow``: one row a checkpoint summarises (value date, currency, amount), for the explanation (design A12)."""

    def test_currency_is_normalised_and_label_defaults_to_none(self) -> None:
        row = _schema("BRIMAbsorbedRow")(as_of="2024-11-20", currency="eur", amount="-80.50")

        assert (row.as_of, row.currency, row.amount, row.label) == (date(2024, 11, 20), "EUR", Decimal("-80.50"), None)

    def test_currency_must_be_iso_4217(self) -> None:
        absorbed_row = _schema("BRIMAbsorbedRow")

        with pytest.raises(ValidationError):
            absorbed_row(as_of="2024-11-20", currency="ZZZ", amount="1")

    def test_amount_is_a_safe_decimal(self) -> None:
        row = _schema("BRIMAbsorbedRow")(as_of="2024-11-20", currency="EUR", amount=Decimal("1E+3"), label="Osto ACME")

        dumped = row.model_dump(mode="json")

        assert (dumped["as_of"], dumped["amount"], dumped["label"]) == ("2024-11-20", "1000", "Osto ACME")

    @pytest.mark.parametrize("missing", ["as_of", "currency", "amount"])
    def test_required_fields(self, missing: str) -> None:
        absorbed_row = _schema("BRIMAbsorbedRow")
        payload = {"as_of": "2024-11-20", "currency": "EUR", "amount": "1"}
        payload.pop(missing)

        with pytest.raises(ValidationError):
            absorbed_row.model_validate(payload)


class TestAbsorbedNewFields:
    """2 — ``BRIMAbsorbed`` gains ``rows`` and ``opening_cash``, both defaulted, so every A1 payload stays valid."""

    def test_defaults(self) -> None:
        _require_fields(BRIMAbsorbed, "rows", "opening_cash")

        absorbed = BRIMAbsorbed()

        assert (absorbed.count, absorbed.cash, absorbed.rows, absorbed.opening_cash) == (0, [], [], [])

    def test_a1_payload_still_validates(self) -> None:
        _require_fields(BRIMAbsorbed, "rows", "opening_cash")

        absorbed = BRIMAbsorbed.model_validate({"count": 3, "cash": [{"currency": "EUR", "amount": "-250.00"}]})

        assert (absorbed.count, [(item.currency, item.amount) for item in absorbed.cash], absorbed.rows, absorbed.opening_cash) == (3, [("EUR", Decimal("-250.00"))], [], [])

    def test_rows_and_opening_cash_are_typed(self) -> None:
        _require_fields(BRIMAbsorbed, "rows", "opening_cash")
        absorbed_row = _schema("BRIMAbsorbedRow")

        absorbed = BRIMAbsorbed.model_validate({"count": 1, "rows": [{"as_of": "2024-11-20", "currency": "eur", "amount": "-80.50", "label": "Osto"}], "opening_cash": [{"currency": "sek", "amount": "12.00"}]})

        assert all(isinstance(item, absorbed_row) for item in absorbed.rows)
        assert [(item.as_of, item.currency, item.amount, item.label) for item in absorbed.rows] == [(date(2024, 11, 20), "EUR", Decimal("-80.50"), "Osto")]
        assert absorbed.opening_cash == [BRIMTruthCash(currency="SEK", amount=Decimal("12.00"))]

    def test_checkpoint_round_trips_through_json(self) -> None:
        _require_fields(BRIMAbsorbed, "rows", "opening_cash")
        payload = {
            "as_of": "2024-12-31",
            "kind": "opening",
            "cash": [{"currency": "EUR", "amount": "1523.40"}],
            "absorbed": {
                "count": 2,
                "cash": [{"currency": "EUR", "amount": "-50.00"}],
                "rows": [{"as_of": "2024-11-20", "currency": "EUR", "amount": "-80.00"}, {"as_of": "2024-12-02", "currency": "EUR", "amount": "30.00", "label": "Myynti"}],
                "opening_cash": [{"currency": "EUR", "amount": "1000.00"}],
            },
        }

        checkpoint = BRIMCheckpoint.model_validate(payload)

        assert BRIMCheckpoint.model_validate_json(checkpoint.model_dump_json()) == checkpoint
        dumped = checkpoint.model_dump(mode="json")["absorbed"]
        assert (dumped["opening_cash"], [row["amount"] for row in dumped["rows"]]) == (payload["absorbed"]["opening_cash"], ["-80.00", "30.00"])


class TestGapFixRequestSchema:
    """2 — ``BRIMGapFixRequest``: the truth points of a parse, and what the wizard and the editor are about to save."""

    def test_defaults(self) -> None:
        request = _schema("BRIMGapFixRequest")(broker_id=1, plugin_code=GENERIC_CODE)

        assert (request.broker_id, request.plugin_code) == (1, GENERIC_CODE)
        assert (request.checkpoints, request.verifications, request.selection, request.pending_creates, request.pending_delete_tx_ids) == ([], [], [], [], [])

    @pytest.mark.parametrize("missing", ["broker_id", "plugin_code"])
    def test_required_fields(self, missing: str) -> None:
        gap_fix_request = _schema("BRIMGapFixRequest")
        payload: Dict[str, Any] = {"broker_id": 1, "plugin_code": GENERIC_CODE}
        payload.pop(missing)

        with pytest.raises(ValidationError):
            gap_fix_request.model_validate(payload)

    @pytest.mark.parametrize("broker_id", [0, -1])
    def test_broker_id_is_positive(self, broker_id: int) -> None:
        gap_fix_request = _schema("BRIMGapFixRequest")

        with pytest.raises(ValidationError):
            gap_fix_request(broker_id=broker_id, plugin_code=GENERIC_CODE)

    def test_lists_are_typed(self) -> None:
        gap_fix_request = _schema("BRIMGapFixRequest")

        request = gap_fix_request.model_validate(
            {
                "broker_id": 1,
                "plugin_code": GENERIC_CODE,
                "checkpoints": [{"as_of": "2024-12-31", "kind": "opening", "cash": [{"currency": "EUR", "amount": "1523.40"}]}],
                "verifications": [{"as_of": "2025-01-17", "cash": [{"currency": "EUR", "amount": "1475.90"}]}],
                "selection": [{"broker_id": 1, "type": "DEPOSIT", "date": "2025-01-02", "cash": {"code": "EUR", "amount": "10"}}],
                "pending_creates": [{"broker_id": 1, "type": "WITHDRAWAL", "date": "2025-01-03", "cash": {"code": "EUR", "amount": "-5"}}],
                "pending_delete_tx_ids": [7, 9],
            }
        )

        assert (type(request.checkpoints[0]), type(request.verifications[0]), type(request.selection[0]), type(request.pending_creates[0])) == (BRIMCheckpoint, BRIMVerification, TXCreateItem, TXCreateItem)
        assert (request.checkpoints[0].as_of, request.selection[0].type, request.pending_creates[0].type, request.pending_delete_tx_ids) == (EVE_2024, DEPOSIT, WITHDRAWAL, [7, 9])

    def test_unsaved_rows_are_validated_as_transactions(self) -> None:
        """A selected row is a ``TXCreateItem`` with its rules: a deposit with a negative amount is refused."""
        gap_fix_request = _schema("BRIMGapFixRequest")

        with pytest.raises(ValidationError):
            gap_fix_request.model_validate({"broker_id": 1, "plugin_code": GENERIC_CODE, "selection": [{"broker_id": 1, "type": "DEPOSIT", "date": "2025-01-02", "cash": {"code": "EUR", "amount": "-10"}}]})


# A full response, as the wizard receives it: one checkpoint with every part, one verification.
RESPONSE_PAYLOAD: Dict[str, Any] = {
    "checkpoints": [
        {
            "as_of": "2024-12-31",
            "kind": "opening",
            "cash": [{"currency": "EUR", "bank": "1523.40", "librefolio": "1000.00", "difference": "523.40"}],
            "positions": [{"asset_id": ASSET_B, "exactness": "exact", "bank": "4", "librefolio": "0", "difference": "4"}],
            "proposals": [
                {"broker_id": BROKER_ID, "type": "DEPOSIT", "date": "2024-12-31", "cash": {"code": "EUR", "amount": "523.40"}, "tags": ["import", GENERIC_TAG, GAP_FIX_TAG], "description": f"Gap-fix 2024-12-31 — {GENERIC_NAME}"},
                {"broker_id": BROKER_ID, "type": "ADJUSTMENT", "date": "2024-12-31", "asset_id": ASSET_B, "quantity": "4", "tags": ["import", GENERIC_TAG, GAP_FIX_TAG], "description": f"Gap-fix 2024-12-31 — {GENERIC_NAME}"},
            ],
            "todos": [{"tx_index": 1, "field": "cost_basis_override", "severity": "blocker", "reason_code": "gap_fix_cost", "message": "Unit cost unknown"}],
            "explanation": {
                "absorbed_count": 2,
                "absorbed_missing_count": 1,
                "absorbed_missing_cash": [{"currency": "EUR", "amount": "-80.00"}],
                "opening_cash": [{"currency": "EUR", "amount": "1000.00"}],
                "unexplained_cash": [{"currency": "EUR", "amount": "-396.60"}],
                "notes": [{"severity": "warning", "code": "unresolved_asset", "message": "Asset left unresolved"}],
            },
        }
    ],
    "verifications": [{"as_of": "2025-01-17", "ok": False, "cash": [{"currency": "EUR", "bank": "1475.90", "librefolio": "1475.00", "difference": "0.90"}]}],
}


class TestGapFixResponseSchemas:
    """2 — the response: per checkpoint the rows, the proposals, the todos and the explanation; per verification the comparison."""

    def test_cash_row(self) -> None:
        row = _schema("BRIMGapFixCashRow")(currency="EUR", bank=Decimal("1523.40"), librefolio=Decimal("1E+3"), difference=Decimal("523.40"))

        assert row.model_dump(mode="json") == {"currency": "EUR", "bank": "1523.40", "librefolio": "1000", "difference": "523.40"}

    def test_position_row(self) -> None:
        row = _schema("BRIMGapFixPositionRow")(asset_id=ASSET_A, exactness="at_least", bank=Decimal("5"), librefolio=Decimal("2"), difference=Decimal("3"))

        assert row.model_dump(mode="json") == {"asset_id": ASSET_A, "exactness": "at_least", "bank": "5", "librefolio": "2", "difference": "3"}

    def test_position_row_exactness_is_exact_or_at_least(self) -> None:
        position_row = _schema("BRIMGapFixPositionRow")

        with pytest.raises(ValidationError):
            position_row(asset_id=ASSET_A, exactness="approximate", bank=Decimal("5"), librefolio=Decimal("2"), difference=Decimal("3"))

    def test_explanation_defaults(self) -> None:
        explanation = _schema("BRIMGapFixExplanation")()

        assert (explanation.absorbed_count, explanation.absorbed_missing_count) == (0, 0)
        assert (explanation.absorbed_missing_cash, explanation.opening_cash, explanation.unexplained_cash, explanation.notes) == ([], [], [], [])

    def test_checkpoint_result_defaults(self) -> None:
        result = _schema("BRIMGapFixCheckpointResult")(as_of=EVE_2024, kind="gap", explanation=_schema("BRIMGapFixExplanation")())

        assert (result.as_of, result.kind) == (EVE_2024, "gap")
        assert (result.cash, result.positions, result.proposals, result.todos) == ([], [], [], [])

    def test_checkpoint_result_kind_is_opening_or_gap(self) -> None:
        checkpoint_result, explanation = _schema("BRIMGapFixCheckpointResult"), _schema("BRIMGapFixExplanation")

        with pytest.raises(ValidationError):
            checkpoint_result(as_of=EVE_2024, kind="closing", explanation=explanation())

    def test_verification_result_defaults(self) -> None:
        result = _schema("BRIMGapFixVerificationResult")(as_of=_d("2025-01-17"), ok=True)

        assert (result.as_of, result.ok, result.cash) == (_d("2025-01-17"), True, [])

    def test_response_defaults(self) -> None:
        response = _schema("BRIMGapFixResponse")()

        assert (response.checkpoints, response.verifications) == ([], [])

    def test_response_round_trips_through_json(self) -> None:
        gap_fix_response = _schema("BRIMGapFixResponse")

        response = gap_fix_response.model_validate(RESPONSE_PAYLOAD)

        assert gap_fix_response.model_validate_json(response.model_dump_json()) == response
        result = response.checkpoints[0]
        assert isinstance(result, _schema("BRIMGapFixCheckpointResult"))
        assert (type(result.cash[0]), type(result.positions[0]), type(result.explanation)) == (_schema("BRIMGapFixCashRow"), _schema("BRIMGapFixPositionRow"), _schema("BRIMGapFixExplanation"))
        assert (type(result.proposals[0]), type(result.todos[0]), type(result.explanation.notes[0]), type(result.explanation.unexplained_cash[0])) == (TXCreateItem, BRIMFieldTodo, BRIMNotice, BRIMTruthCash)
        assert isinstance(response.verifications[0], _schema("BRIMGapFixVerificationResult"))
        dumped = response.model_dump(mode="json")
        assert (dumped["checkpoints"][0]["cash"], dumped["verifications"][0]["cash"]) == (RESPONSE_PAYLOAD["checkpoints"][0]["cash"], RESPONSE_PAYLOAD["verifications"][0]["cash"])


# (schema name, a valid payload): each new schema refuses a key it does not declare.
A3_STRICT_SCHEMAS = [
    ("BRIMAbsorbedRow", {"as_of": "2024-11-20", "currency": "EUR", "amount": "1"}),
    ("BRIMGapFixRequest", {"broker_id": 1, "plugin_code": GENERIC_CODE}),
    ("BRIMGapFixCashRow", {"currency": "EUR", "bank": "1", "librefolio": "0", "difference": "1"}),
    ("BRIMGapFixPositionRow", {"asset_id": ASSET_A, "exactness": "exact", "bank": "1", "librefolio": "0", "difference": "1"}),
    ("BRIMGapFixExplanation", {}),
    ("BRIMGapFixCheckpointResult", {"as_of": "2024-12-31", "kind": "gap", "explanation": {}}),
    ("BRIMGapFixVerificationResult", {"as_of": "2025-01-17", "ok": True}),
    ("BRIMGapFixResponse", {}),
]


class TestA3SchemasAreStrict:
    """2 — every A3 schema is a ``StrictModel``: an unknown key is a 422, not a value that silently goes nowhere."""

    @pytest.mark.parametrize(("name", "valid"), A3_STRICT_SCHEMAS, ids=[name for name, _valid in A3_STRICT_SCHEMAS])
    def test_rejects_an_unknown_key(self, name: str, valid: Dict[str, Any]) -> None:
        model = _schema(name)
        model.model_validate(valid)  # precondition: the payload is valid

        with pytest.raises(ValidationError):
            model.model_validate({**valid, "unexpected_key": 1})


# =============================================================================
# 3·A — SERVICE: the plugin
# =============================================================================


class TestGapFixPlugin:
    """3·A — ``compute_gap_fix`` takes any registered plugin, and reads only its history tag and its name."""

    @pytest.mark.asyncio
    async def test_unknown_plugin_is_not_found(self, db_session: AsyncSession) -> None:
        compute_gap_fix = _gap("compute_gap_fix")
        request = _request(plugin_code=UNKNOWN_CODE, checkpoints=[_checkpoint(EVE_2024, "opening", cash=[_truth("EUR", "100")])])

        with pytest.raises(brim_report_sets.BRIMSetPluginNotFound) as caught:
            await compute_gap_fix(db_session, request)

        assert (caught.value.status_code, caught.value.code) == (404, "plugin_not_found")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("plugin_code", [GENERIC_CODE, "broker_degiro"])
    async def test_any_registered_plugin_is_accepted(self, db_session: AsyncSession, plugin_code: str) -> None:
        """A single-file plugin works as a report-set one would: its proposals carry its history tag and its name."""
        plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
        assert plugin is not None and not plugin.is_report_set_plugin  # precondition: a registered single-file plugin

        response = await _run(db_session, plugin_code=plugin_code, checkpoints=[_checkpoint(EVE_2024, "opening", cash=[_truth("EUR", "100")])])

        proposals = _at(response, EVE_2024).proposals
        assert [(proposal.type, proposal.tags) for proposal in proposals] == [(DEPOSIT, ["import", plugin.history_tag, GAP_FIX_TAG])]
        assert plugin.provider_name in proposals[0].description, proposals[0].description

    @pytest.mark.asyncio
    async def test_tag_and_name_come_from_the_plugin(self, db_session: AsyncSession, fake_bank_plugin: BRIMProvider) -> None:
        """The tag is ``history_tag``, not the code: here the two differ on purpose."""
        response = await _run(db_session, plugin_code=FAKE_BANK_CODE, checkpoints=[_checkpoint(EVE_2024, "opening", cash=[_truth("EUR", "100")], positions=[_position(ASSET_A, "2", unit_cost=_money("EUR", "5"))])])

        proposals = _at(response, EVE_2024).proposals
        assert [proposal.tags for proposal in proposals] == [["import", FAKE_BANK_TAG, GAP_FIX_TAG]] * 2
        assert all(FAKE_BANK_NAME in proposal.description for proposal in proposals), [proposal.description for proposal in proposals]


# =============================================================================
# 3·B — SERVICE: first import, overlapping import, gap
# =============================================================================


def _first_import() -> Dict[str, Any]:
    """A first import on an empty broker: cash, an exact position with its unit cost, one without, and a minimum with its cost."""
    positions = [_position(ASSET_A, "10", unit_cost=_money("EUR", "31.25")), _position(ASSET_B, "4"), _position(ASSET_C, "3", "at_least", _money("EUR", "12.00"))]
    return {"checkpoints": [_checkpoint(EVE_2024, "opening", cash=[_truth("EUR", "1523.40")], positions=positions)]}


class TestFirstImport:
    """3·B — first import on an empty broker: the opening, i.e. the cash and every proven position (design §3.6)."""

    @pytest.mark.asyncio
    async def test_rows_compare_the_bank_with_librefolio(self, db_session: AsyncSession) -> None:
        response = await _run(db_session, **_first_import())

        result = _at(response, EVE_2024)
        assert result.kind == "opening"
        assert _cash_rows(result) == {"EUR": _cash_row("1523.40", "0", "1523.40")}
        assert _position_rows(result) == {ASSET_A: _position_row("exact", "10", "0", "10"), ASSET_B: _position_row("exact", "4", "0", "4"), ASSET_C: _position_row("at_least", "3", "0", "3")}
        assert response.verifications == []

    @pytest.mark.asyncio
    async def test_proposes_the_opening(self, db_session: AsyncSession) -> None:
        response = await _run(db_session, **_first_import())

        assert _proposals(_at(response, EVE_2024)) == Counter(
            [
                _deposit(EVE_2024, "EUR", "1523.40"),
                _adjustment(EVE_2024, ASSET_A, "10", ("EUR", "31.25")),
                _adjustment(EVE_2024, ASSET_B, "4"),
                _adjustment(EVE_2024, ASSET_C, "3", ("EUR", "12.00")),
            ]
        )

    @pytest.mark.asyncio
    async def test_unknown_cost_is_a_blocking_todo_on_its_adjustment(self, db_session: AsyncSession) -> None:
        """Only the positive ADJUSTMENT without a unit cost gets the todo, and ``tx_index`` points at it."""
        response = await _run(db_session, **_first_import())

        result = _at(response, EVE_2024)
        assert _todo_kinds(result) == [COST_TODO]
        target = _todo_target(result, result.todos[0])
        assert (target.type, target.asset_id, target.cost_basis_override) == (ADJUSTMENT, ASSET_B, None)


class TestMatchingImport:
    """3·B — an import overlapping the previous one: LibreFolio already agrees with the bank, so nothing is proposed."""

    @pytest.mark.asyncio
    async def test_nothing_to_propose_and_the_verification_is_ok(self, db_session: AsyncSession) -> None:
        await _add(db_session, _saved(DEPOSIT, "2024-06-03", amount="2000", currency="EUR"), _saved(BUY, "2024-07-01", amount="-476.60", currency="EUR", asset_id=ASSET_A, quantity="10"))

        response = await _run(
            db_session,
            checkpoints=[_checkpoint(EVE_2024, "opening", cash=[_truth("EUR", "1523.40")], positions=[_position(ASSET_A, "10", unit_cost=_money("EUR", "31.25"))])],
            verifications=[_verification(_d("2025-01-17"), _truth("EUR", "1523.40"))],
        )

        result = _at(response, EVE_2024)
        assert (result.proposals, result.todos) == ([], [])
        assert _cash_rows(result) == {"EUR": _cash_row("1523.40", "1523.40", "0")}
        assert _position_rows(result) == {ASSET_A: _position_row("exact", "10", "10", "0")}
        assert result.explanation.unexplained_cash == []
        verification = _verified(response, _d("2025-01-17"))
        assert (verification.ok, _cash_rows(verification)) == (True, {"EUR": _cash_row("1523.40", "1523.40", "0")})


class TestGapCheckpoint:
    """3·B — a gap: LibreFolio has part of the story, and only the difference is proposed."""

    @staticmethod
    async def _gap_response(session: AsyncSession) -> Any:
        await _add(session, _saved(DEPOSIT, "2024-03-01", amount="1000", currency="EUR"), _saved(ADJUSTMENT, "2024-04-02", asset_id=ASSET_A, quantity="6"))
        return await _run(session, checkpoints=[_checkpoint(EVE_2024, "gap", cash=[_truth("EUR", "1523.40")], positions=[_position(ASSET_A, "10", unit_cost=_money("EUR", "31.25"))])])

    @pytest.mark.asyncio
    async def test_only_the_difference_is_proposed(self, db_session: AsyncSession) -> None:
        response = await self._gap_response(db_session)

        result = _at(response, EVE_2024)
        assert result.kind == "gap"
        assert _cash_rows(result) == {"EUR": _cash_row("1523.40", "1000", "523.40")}
        assert _position_rows(result) == {ASSET_A: _position_row("exact", "10", "6", "4")}
        assert _proposals(result) == Counter([_deposit(EVE_2024, "EUR", "523.40"), _adjustment(EVE_2024, ASSET_A, "4", ("EUR", "31.25"))])
        assert result.todos == []

    @pytest.mark.asyncio
    async def test_without_absorbed_rows_the_whole_difference_is_unexplained(self, db_session: AsyncSession) -> None:
        response = await self._gap_response(db_session)

        explanation = _at(response, EVE_2024).explanation
        assert (explanation.absorbed_count, explanation.absorbed_missing_count, explanation.absorbed_missing_cash, explanation.opening_cash) == (0, 0, [], [])
        assert _amounts(explanation.unexplained_cash) == {"EUR": Decimal("523.40")}


# =============================================================================
# 3·C — SERVICE: cash
# =============================================================================


class TestCashCorrections:
    """3·C — cash, per currency the checkpoint states: a DEPOSIT or a WITHDRAWAL of the difference when it exceeds 0.01, dated C."""

    @pytest.mark.asyncio
    async def test_withdrawal_when_librefolio_has_more(self, db_session: AsyncSession) -> None:
        await _add(db_session, _saved(DEPOSIT, "2024-05-02", amount="2000", currency="EUR"))

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, cash=[_truth("EUR", "1523.40")])])

        result = _at(response, EVE_2024)
        assert _cash_rows(result) == {"EUR": _cash_row("1523.40", "2000", "-476.60")}
        assert _proposals(result) == Counter([_withdrawal(EVE_2024, "EUR", "-476.60")])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("librefolio", "expected"),
        [
            pytest.param("99.99", None, id="plus-a-cent-is-tolerated"),
            pytest.param("100.01", None, id="minus-a-cent-is-tolerated"),
            pytest.param("99.98", (DEPOSIT, "0.02"), id="plus-two-cents-is-corrected"),
            pytest.param("100.02", (WITHDRAWAL, "-0.02"), id="minus-two-cents-is-corrected"),
        ],
    )
    async def test_tolerance_of_a_cent_both_ways(self, db_session: AsyncSession, librefolio: str, expected: Optional[Tuple[TransactionType, str]]) -> None:
        """The row always shows the difference; a correction appears only beyond 0.01."""
        await _add(db_session, _saved(DEPOSIT, "2024-05-02", amount=librefolio, currency="EUR"))

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, cash=[_truth("EUR", "100.00")])])

        result = _at(response, EVE_2024)
        assert _cash_rows(result) == {"EUR": (Decimal("100.00"), Decimal(librefolio), Decimal("100.00") - Decimal(librefolio))}
        assert _proposals(result) == Counter([_expected(expected[0], EVE_2024, cash=("EUR", expected[1]))] if expected else [])

    @pytest.mark.asyncio
    async def test_one_correction_per_currency(self, db_session: AsyncSession) -> None:
        """EUR and USD are compared on their own; SEK, which LibreFolio has and the checkpoint does not mention, is ignored."""
        await _add(db_session, *(_saved(DEPOSIT, "2024-02-01", amount=amount, currency=currency) for currency, amount in (("EUR", "800"), ("USD", "80"), ("SEK", "10"))))

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, cash=[_truth("EUR", "1000"), _truth("USD", "50")])])

        result = _at(response, EVE_2024)
        assert _cash_rows(result) == {"EUR": _cash_row("1000", "800", "200"), "USD": _cash_row("50", "80", "-30")}
        assert _proposals(result) == Counter([_deposit(EVE_2024, "EUR", "200"), _withdrawal(EVE_2024, "USD", "-30")])


# =============================================================================
# 3·D — SERVICE: positions
# =============================================================================


class TestPositionCorrections:
    """3·D — positions: exact gives an ADJUSTMENT of the difference either way; at_least only the missing part; the cost or a blocking todo."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("unit_cost", [pytest.param(("EUR", "31.25"), id="cost-known"), pytest.param(None, id="cost-unknown")])
    async def test_more_than_the_bank_is_a_negative_adjustment_without_cost(self, db_session: AsyncSession, unit_cost: Optional[Tuple[str, str]]) -> None:
        """Even with a known unit cost, a negative ADJUSTMENT carries none and needs no todo (a known limit, design A6)."""
        await _add(db_session, _saved(ADJUSTMENT, "2024-02-01", asset_id=ASSET_A, quantity="12"))

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, positions=[_position(ASSET_A, "10", unit_cost=_money(*unit_cost) if unit_cost else None)])])

        result = _at(response, EVE_2024)
        assert _position_rows(result) == {ASSET_A: _position_row("exact", "10", "12", "-2")}
        assert _proposals(result) == Counter([_adjustment(EVE_2024, ASSET_A, "-2")])
        assert result.todos == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize("librefolio", ["5", "7"], ids=["exactly-the-minimum", "more-than-the-minimum"])
    async def test_minimum_already_covered(self, db_session: AsyncSession, librefolio: str) -> None:
        await _add(db_session, _saved(ADJUSTMENT, "2024-02-01", asset_id=ASSET_A, quantity=librefolio))

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, positions=[_position(ASSET_A, "5", "at_least")])])

        result = _at(response, EVE_2024)
        assert _position_rows(result) == {ASSET_A: _position_row("at_least", "5", librefolio, "0")}
        assert (result.proposals, result.todos) == ([], [])

    @pytest.mark.asyncio
    async def test_minimum_proposes_only_the_missing_part(self, db_session: AsyncSession) -> None:
        await _add(db_session, _saved(ADJUSTMENT, "2024-02-01", asset_id=ASSET_A, quantity="2"))

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, positions=[_position(ASSET_A, "5", "at_least", _money("EUR", "9.00"))])])

        result = _at(response, EVE_2024)
        assert _position_rows(result) == {ASSET_A: _position_row("at_least", "5", "2", "3")}
        assert _proposals(result) == Counter([_adjustment(EVE_2024, ASSET_A, "3", ("EUR", "9.00"))])
        assert result.todos == []

    @pytest.mark.asyncio
    async def test_unresolved_asset_is_skipped_with_a_note(self, db_session: AsyncSession) -> None:
        """A position still on a fake id gives no row, no proposal and no todo, only a note; the other positions go on as usual."""
        positions = [_position(UNRESOLVED_ASSET, "5"), _position(ASSET_A, "2", unit_cost=_money("EUR", "3.00"))]

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, positions=positions)])

        result = _at(response, EVE_2024)
        assert "unresolved_asset" in [note.code for note in result.explanation.notes]
        assert _proposals(result) == Counter([_adjustment(EVE_2024, ASSET_A, "2", ("EUR", "3.00"))])
        assert set(_position_rows(result)) == {ASSET_A}
        assert result.todos == []

    @pytest.mark.asyncio
    async def test_todos_index_their_own_checkpoint(self, db_session: AsyncSession) -> None:
        """Two checkpoints, each with an ADJUSTMENT without cost: each todo points into its own checkpoint's proposals."""
        response = await _run(
            db_session,
            checkpoints=[
                _checkpoint(EVE_2023, "opening", cash=[_truth("EUR", "100")], positions=[_position(ASSET_B, "4")]),
                _checkpoint(EVE_2024, cash=[_truth("EUR", "100")], positions=[_position(ASSET_C, "3")]),
            ],
        )

        for as_of, asset_id in ((EVE_2023, ASSET_B), (EVE_2024, ASSET_C)):
            result = _at(response, as_of)
            assert _todo_kinds(result) == [COST_TODO], as_of
            target = _todo_target(result, result.todos[0])
            assert (target.type, target.asset_id) == (ADJUSTMENT, asset_id)
        assert _proposals(_at(response, EVE_2024)) == Counter([_adjustment(EVE_2024, ASSET_C, "3")]), "the 2024 cash is already right: the 2023 opening counts"


# =============================================================================
# 3·E — SERVICE: LibreFolio's state at a checkpoint
# =============================================================================


class TestLibreFolioState:
    """3·E — LibreFolio at C: the saved rows up to C without the pending deletes, plus the editor's pending rows, the selection and the earlier proposals; this broker only."""

    @pytest.mark.asyncio
    async def test_pending_deletes_are_left_out(self, db_session: AsyncSession) -> None:
        _kept, deleting_cash, deleting_asset = await _add(
            db_session,
            _saved(DEPOSIT, "2024-03-01", amount="1000", currency="EUR"),
            _saved(DEPOSIT, "2024-04-01", amount="500", currency="EUR"),
            _saved(BUY, "2024-05-02", amount="-300", currency="EUR", asset_id=ASSET_A, quantity="3"),
        )
        checkpoints = [_checkpoint(EVE_2024, cash=[_truth("EUR", "1000")], positions=[_position(ASSET_A, "3", unit_cost=_money("EUR", "100"))])]

        counted = await _run(db_session, checkpoints=checkpoints)
        response = await _run(db_session, checkpoints=checkpoints, pending_delete_tx_ids=[deleting_cash.id, deleting_asset.id, 987654])

        assert _proposals(_at(counted, EVE_2024)) == Counter([_withdrawal(EVE_2024, "EUR", "-200")]), "presence barrier: without pending deletes every saved row counts"
        result = _at(response, EVE_2024)
        assert _cash_rows(result) == {"EUR": _cash_row("1000", "1000", "0")}
        assert _position_rows(result) == {ASSET_A: _position_row("exact", "3", "0", "3")}
        assert _proposals(result) == Counter([_adjustment(EVE_2024, ASSET_A, "3", ("EUR", "100"))])

    @pytest.mark.asyncio
    @pytest.mark.parametrize("source", ["pending_creates", "selection"])
    async def test_unsaved_rows_are_counted(self, db_session: AsyncSession, source: str) -> None:
        """A row pending in the editor or selected in the wizard counts like a saved one: cash per currency, quantity per asset."""
        rows = [_tx(DEPOSIT, "2024-05-02", cash=("EUR", "300")), _tx(BUY, "2024-07-01", cash=("EUR", "-50"), asset_id=ASSET_A, quantity="2")]

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, cash=[_truth("EUR", "500")], positions=[_position(ASSET_A, "2")])], **{source: rows})

        result = _at(response, EVE_2024)
        assert _cash_rows(result) == {"EUR": _cash_row("500", "250", "250")}
        assert _position_rows(result) == {ASSET_A: _position_row("exact", "2", "2", "0")}
        assert _proposals(result) == Counter([_deposit(EVE_2024, "EUR", "250")])

    @pytest.mark.asyncio
    async def test_saved_pending_and_selected_rows_add_up(self, db_session: AsyncSession) -> None:
        await _add(db_session, _saved(DEPOSIT, "2024-03-01", amount="100", currency="EUR"))

        response = await _run(
            db_session,
            checkpoints=[_checkpoint(EVE_2024, cash=[_truth("EUR", "650")])],
            pending_creates=[_tx(DEPOSIT, "2024-04-01", cash=("EUR", "200"))],
            selection=[_tx(DEPOSIT, "2024-05-02", cash=("EUR", "300"))],
        )

        result = _at(response, EVE_2024)
        assert _cash_rows(result) == {"EUR": _cash_row("650", "600", "50")}
        assert _proposals(result) == Counter([_deposit(EVE_2024, "EUR", "50")])

    @pytest.mark.asyncio
    async def test_other_brokers_and_later_rows_do_not_count(self, db_session: AsyncSession) -> None:
        """Saved, pending or selected: another broker's rows never count, and neither do rows dated after C; rows dated C do."""
        await _add(
            db_session,
            _saved(DEPOSIT, "2024-12-31", amount="100", currency="EUR"),
            _saved(DEPOSIT, "2025-01-01", amount="100", currency="EUR"),
            _saved(DEPOSIT, "2024-01-02", amount="5000", currency="EUR", broker_id=OTHER_BROKER_ID),
            _saved(ADJUSTMENT, "2024-01-02", asset_id=ASSET_A, quantity="5", broker_id=OTHER_BROKER_ID),
        )

        response = await _run(
            db_session,
            checkpoints=[_checkpoint(EVE_2024, cash=[_truth("EUR", "125")], positions=[_position(ASSET_A, "1", unit_cost=_money("EUR", "10"))])],
            pending_creates=[_tx(DEPOSIT, "2024-06-03", cash=("EUR", "700"), broker_id=OTHER_BROKER_ID), _tx(DEPOSIT, "2025-01-02", cash=("EUR", "40"))],
            selection=[
                _tx(BUY, "2024-06-04", cash=("EUR", "-10"), asset_id=ASSET_A, quantity="5", broker_id=OTHER_BROKER_ID),
                _tx(BUY, "2025-01-03", cash=("EUR", "-10"), asset_id=ASSET_A, quantity="1"),
                _tx(DEPOSIT, "2024-12-31", cash=("EUR", "25")),
            ],
        )

        result = _at(response, EVE_2024)
        assert _cash_rows(result) == {"EUR": _cash_row("125", "125", "0")}
        assert _position_rows(result) == {ASSET_A: _position_row("exact", "1", "0", "1")}
        assert _proposals(result) == Counter([_adjustment(EVE_2024, ASSET_A, "1", ("EUR", "10"))])

    @pytest.mark.asyncio
    async def test_earlier_proposals_count_as_accepted(self, db_session: AsyncSession) -> None:
        """D-S24: a later checkpoint counts the earlier proposals as accepted, so it never proposes them a second time."""
        checkpoints = [
            _checkpoint(EVE_2023, "opening", cash=[_truth("EUR", "1000")], positions=[_position(ASSET_A, "10", unit_cost=_money("EUR", "20"))]),
            _checkpoint(EVE_2024, cash=[_truth("EUR", "1100")], positions=[_position(ASSET_A, "10", unit_cost=_money("EUR", "20"))]),
        ]

        response = await _run(db_session, checkpoints=checkpoints)

        later = _at(response, EVE_2024)
        assert _cash_rows(later) == {"EUR": _cash_row("1100", "1000", "100")}
        assert _position_rows(later) == {ASSET_A: _position_row("exact", "10", "10", "0")}
        assert _proposals(later) == Counter([_deposit(EVE_2024, "EUR", "100")])


# =============================================================================
# 3·F — SERVICE: the explanation
# =============================================================================


class TestExplanation:
    """3·F — the explanation: the absorbed rows LibreFolio does not have yet, the opening cash, and the part nothing explains (design §3.6, A12)."""

    @pytest.mark.asyncio
    async def test_absorbed_rows_are_matched_one_to_one(self, db_session: AsyncSession) -> None:
        """Multiset matching: two saved deposits cover two of three identical rows, one saved withdrawal one of two."""
        await _add(
            db_session,
            _saved(DEPOSIT, "2024-11-04", amount="200", currency="EUR"),
            _saved(DEPOSIT, "2024-11-04", amount="200", currency="EUR"),
            _saved(WITHDRAWAL, "2024-11-05", amount="-50", currency="EUR"),
        )
        absorbed = _absorbed(rows=[("2024-11-04", "EUR", "200")] * 3 + [("2024-11-05", "EUR", "-50")] * 2)

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, cash=[_truth("EUR", "350")], absorbed=absorbed)])

        explanation = _at(response, EVE_2024).explanation
        assert (explanation.absorbed_count, explanation.absorbed_missing_count) == (5, 2)
        assert _amounts(explanation.absorbed_missing_cash) == {"EUR": Decimal("150")}

    @pytest.mark.asyncio
    async def test_what_librefolio_already_has(self, db_session: AsyncSession) -> None:
        """Present: a saved row, a selected row, a pending row. Missing: a row being deleted, another broker's, another currency, another day, another amount."""
        saved = await _add(
            db_session,
            _saved(WITHDRAWAL, "2024-10-01", amount="-120", currency="EUR"),
            _saved(DEPOSIT, "2024-10-04", amount="60", currency="EUR"),
            _saved(DEPOSIT, "2024-10-05", amount="70", currency="EUR", broker_id=OTHER_BROKER_ID),
            _saved(DEPOSIT, "2024-10-06", amount="80", currency="USD"),
            _saved(DEPOSIT, "2024-10-08", amount="90", currency="EUR"),
            _saved(DEPOSIT, "2024-10-09", amount="100.01", currency="EUR"),
        )
        absorbed = _absorbed(
            rows=[
                ("2024-10-01", "EUR", "-120"),
                ("2024-10-02", "EUR", "35"),
                ("2024-10-03", "EUR", "12.50"),
                ("2024-10-04", "EUR", "60"),
                ("2024-10-05", "EUR", "70"),
                ("2024-10-06", "EUR", "80"),
                ("2024-10-07", "EUR", "90"),
                ("2024-10-09", "EUR", "100"),
            ]
        )

        response = await _run(
            db_session,
            checkpoints=[_checkpoint(EVE_2024, cash=[_truth("EUR", "1000")], absorbed=absorbed)],
            selection=[_tx(DEPOSIT, "2024-10-02", cash=("EUR", "35"))],
            pending_creates=[_tx(DEPOSIT, "2024-10-03", cash=("EUR", "12.50"))],
            pending_delete_tx_ids=[saved[1].id],
        )

        explanation = _at(response, EVE_2024).explanation
        assert (explanation.absorbed_count, explanation.absorbed_missing_count) == (8, 5)
        assert _amounts(explanation.absorbed_missing_cash) == {"EUR": Decimal("400")}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("kind", "opening", "unexplained"),
        [
            pytest.param("opening", {"EUR": Decimal("1000")}, {"EUR": Decimal("350")}, id="opening-checkpoint"),
            pytest.param("gap", {}, {"EUR": Decimal("1350")}, id="gap-checkpoint"),
        ],
    )
    async def test_opening_cash_and_the_unexplained_part(self, db_session: AsyncSession, kind: str, opening: Dict[str, Decimal], unexplained: Dict[str, Decimal]) -> None:
        """Difference 1300 = missing rows (-50) + opening cash (1000, an opening only) + unexplained."""
        await _add(db_session, _saved(DEPOSIT, "2024-11-04", amount="200", currency="EUR"))
        absorbed = _absorbed(rows=[("2024-11-04", "EUR", "200"), ("2024-11-20", "EUR", "-80"), ("2024-12-02", "EUR", "30")], opening_cash=[_truth("EUR", "1000")])

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, kind, cash=[_truth("EUR", "1500")], absorbed=absorbed)])

        result = _at(response, EVE_2024)
        explanation = result.explanation
        assert _cash_rows(result) == {"EUR": _cash_row("1500", "200", "1300")}
        assert (explanation.absorbed_count, explanation.absorbed_missing_count) == (3, 2)
        assert _amounts(explanation.absorbed_missing_cash) == {"EUR": Decimal("-50")}
        assert _amounts(explanation.opening_cash) == opening
        assert _amounts(explanation.unexplained_cash) == unexplained

    @pytest.mark.asyncio
    async def test_unexplained_lists_only_what_exceeds_a_cent(self, db_session: AsyncSession) -> None:
        """EUR: 100.00 against 99.99 of missing rows leaves 0.01, within the tolerance; USD has nothing to explain it."""
        absorbed = _absorbed(rows=[("2024-12-02", "EUR", "99.99")])

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, cash=[_truth("EUR", "100.00"), _truth("USD", "50.00")], absorbed=absorbed)])

        explanation = _at(response, EVE_2024).explanation
        assert _amounts(explanation.absorbed_missing_cash) == {"EUR": Decimal("99.99")}
        assert _amounts(explanation.unexplained_cash) == {"USD": Decimal("50.00")}

    @pytest.mark.asyncio
    async def test_absorbed_count_is_the_number_of_listed_rows(self, db_session: AsyncSession) -> None:
        """``absorbed_count`` is ``len(absorbed.rows)``, not the A1 ``absorbed.count``."""
        absorbed = _absorbed(rows=[("2024-12-02", "EUR", "10"), ("2024-12-03", "EUR", "20")], count=5)

        response = await _run(db_session, checkpoints=[_checkpoint(EVE_2024, cash=[_truth("EUR", "30")], absorbed=absorbed)])

        assert _at(response, EVE_2024).explanation.absorbed_count == 2


# =============================================================================
# 3·G — SERVICE: verifications
# =============================================================================


class TestVerifications:
    """3·G — verifications: the same state at V, with every proposal dated up to V; compared, never corrected."""

    @pytest.mark.asyncio
    async def test_ok_within_a_cent_and_not_ok_beyond(self, db_session: AsyncSession) -> None:
        await _add(db_session, _saved(DEPOSIT, "2025-01-02", amount="1000", currency="EUR"), _saved(DEPOSIT, "2025-01-03", amount="20", currency="USD"))

        response = await _run(
            db_session,
            verifications=[_verification(_d("2025-01-17"), _truth("EUR", "1000"), _truth("USD", "25")), _verification(_d("2025-01-18"), _truth("EUR", "1000.01"), _truth("USD", "20"))],
        )

        assert response.checkpoints == []
        off, within = _verified(response, _d("2025-01-17")), _verified(response, _d("2025-01-18"))
        assert (off.ok, within.ok) == (False, True)
        assert _cash_rows(off) == {"EUR": _cash_row("1000", "1000", "0"), "USD": _cash_row("25", "20", "5")}
        assert _cash_rows(within) == {"EUR": _cash_row("1000.01", "1000", "0.01"), "USD": _cash_row("20", "20", "0")}

    @pytest.mark.asyncio
    async def test_proposals_count_up_to_its_date(self, db_session: AsyncSession) -> None:
        """The opening proposal (dated 2024-12-31) counts at a later verification, not at an earlier one."""
        await _add(db_session, _saved(DEPOSIT, "2025-01-02", amount="1000", currency="EUR"))

        response = await _run(
            db_session,
            checkpoints=[_checkpoint(EVE_2024, "opening", cash=[_truth("EUR", "500")])],
            verifications=[_verification(_d("2025-01-17"), _truth("EUR", "1500")), _verification(_d("2024-12-30"), _truth("EUR", "0"))],
        )

        assert _proposals(_at(response, EVE_2024)) == Counter([_deposit(EVE_2024, "EUR", "500")])
        after, before = _verified(response, _d("2025-01-17")), _verified(response, _d("2024-12-30"))
        assert (after.ok, _cash_rows(after)) == (True, {"EUR": _cash_row("1500", "1500", "0")})
        assert (before.ok, _cash_rows(before)) == (True, {"EUR": _cash_row("0", "0", "0")})

    @pytest.mark.asyncio
    async def test_editor_and_selection_count(self, db_session: AsyncSession) -> None:
        """At V as at C: without the pending deletes, with the pending and selected rows up to V."""
        _kept, deleting = await _add(db_session, _saved(DEPOSIT, "2025-01-02", amount="1000", currency="EUR"), _saved(DEPOSIT, "2025-01-03", amount="300", currency="EUR"))

        response = await _run(
            db_session,
            verifications=[_verification(_d("2025-01-17"), _truth("EUR", "1025"))],
            pending_creates=[_tx(DEPOSIT, "2025-01-04", cash=("EUR", "40"))],
            selection=[_tx(WITHDRAWAL, "2025-01-05", cash=("EUR", "-15")), _tx(DEPOSIT, "2025-01-20", cash=("EUR", "999"))],
            pending_delete_tx_ids=[deleting.id],
        )

        verification = _verified(response, _d("2025-01-17"))
        assert (verification.ok, _cash_rows(verification)) == (True, {"EUR": _cash_row("1025", "1025", "0")})


# =============================================================================
# 3·H — SERVICE: the proposals themselves
# =============================================================================


def _descriptions(response: Any) -> List[Tuple[Tuple[Any, ...], str]]:
    return sorted((_key(item), item.description) for result in response.checkpoints for item in result.proposals)


class TestProposals:
    """3·H — proposals are ordinary transactions: tags ``import``, the plugin's history tag and ``gap_fix``; dated C; a deterministic description."""

    @pytest.mark.asyncio
    async def test_tags_date_broker_and_description(self, db_session: AsyncSession) -> None:
        response = await _run(
            db_session,
            checkpoints=[
                _checkpoint(EVE_2023, "opening", cash=[_truth("EUR", "100")], positions=[_position(ASSET_A, "3")]),
                _checkpoint(EVE_2024, cash=[_truth("EUR", "50"), _truth("USD", "7")], positions=[_position(ASSET_A, "1")]),
            ],
        )

        proposals = [(result.as_of, item) for result in response.checkpoints for item in result.proposals]
        assert len(proposals) == 5, "precondition: 2023 deposit and adjustment; 2024 withdrawal, deposit and adjustment"
        for as_of, item in proposals:
            assert item.tags == ["import", GENERIC_TAG, GAP_FIX_TAG]
            assert (item.date, item.broker_id) == (as_of, BROKER_ID)
            assert item.description.startswith(f"Gap-fix {as_of.isoformat()}"), item.description
            assert GENERIC_NAME in item.description, item.description

    @pytest.mark.asyncio
    async def test_descriptions_are_deterministic(self, db_session: AsyncSession) -> None:
        """The duplicate detector compares descriptions: the same request must describe the same proposals the same way."""
        first = await _run(db_session, **_first_import())
        second = await _run(db_session, **_first_import())

        assert _descriptions(first) == _descriptions(second)
        assert len(_descriptions(first)) == 4

    @pytest.mark.asyncio
    async def test_writes_nothing(self, db_session: AsyncSession) -> None:
        await _add(db_session, _saved(DEPOSIT, "2024-03-01", amount="1000", currency="EUR"))

        response = await _run(db_session, **_first_import(), verifications=[_verification(_d("2025-01-17"), _truth("EUR", "1"))])

        assert _at(response, EVE_2024).proposals, "presence barrier: there was something to propose"
        assert await _transaction_count(db_session) == 1


# =============================================================================
# 3·I — SERVICE: order and consistency
# =============================================================================


def _three_checkpoints() -> List[BRIMCheckpoint]:
    """Three yearly segments. Bank: 2023-12-31 EUR 1000, A exactly 10, B at least 4 · 2024-12-31 EUR 1200, A 12, B at least 5 · 2025-12-31 EUR 880, A 14, B at least 5."""
    return [
        _checkpoint(EVE_2023, "opening", cash=[_truth("EUR", "1000")], positions=[_position(ASSET_A, "10", unit_cost=_money("EUR", "20")), _position(ASSET_B, "4", "at_least", _money("EUR", "5"))]),
        _checkpoint(EVE_2024, cash=[_truth("EUR", "1200")], positions=[_position(ASSET_A, "12", unit_cost=_money("EUR", "21")), _position(ASSET_B, "5", "at_least", _money("EUR", "6"))]),
        _checkpoint(EVE_2025, cash=[_truth("EUR", "880")], positions=[_position(ASSET_A, "14", unit_cost=_money("EUR", "22")), _position(ASSET_B, "5", "at_least")]),
    ]


def _segment_2024() -> List[TXCreateItem]:
    """The rows imported in 2024: EUR -43, A +5, B -1."""
    return [_tx(BUY, "2024-03-01", cash=("EUR", "-100"), asset_id=ASSET_A, quantity="5"), _tx(DEPOSIT, "2024-06-03", cash=("EUR", "50")), _tx(SELL, "2024-09-02", cash=("EUR", "7"), asset_id=ASSET_B, quantity="-1")]


def _segment_2025() -> List[TXCreateItem]:
    """The rows imported in 2025: EUR -344, A +2."""
    return [_tx(WITHDRAWAL, "2025-02-03", cash=("EUR", "-300")), _tx(BUY, "2025-05-05", cash=("EUR", "-44"), asset_id=ASSET_A, quantity="2")]


def _three_segments_expected() -> Dict[date, Counter]:
    """2023: the opening. 2024: 957 against 1200, A 15 against exactly 12, B 3 against at least 5. 2025: 856 against 880, A and B right."""
    return {
        EVE_2023: Counter([_deposit(EVE_2023, "EUR", "1000"), _adjustment(EVE_2023, ASSET_A, "10", ("EUR", "20")), _adjustment(EVE_2023, ASSET_B, "4", ("EUR", "5"))]),
        EVE_2024: Counter([_deposit(EVE_2024, "EUR", "243"), _adjustment(EVE_2024, ASSET_A, "-3"), _adjustment(EVE_2024, ASSET_B, "2", ("EUR", "6"))]),
        EVE_2025: Counter([_deposit(EVE_2025, "EUR", "24")]),
    }


def _all_proposals(response: Any) -> List[TXCreateItem]:
    return [item for result in response.checkpoints for item in result.proposals]


class TestOrderAndConsistency:
    """3·I — checkpoints are computed in date order, whatever the input order; one import or three give the same history (design §3.6)."""

    @pytest.mark.asyncio
    async def test_checkpoints_are_computed_in_date_order(self, db_session: AsyncSession) -> None:
        checkpoints = _three_checkpoints()

        in_order = await _run(db_session, checkpoints=checkpoints, selection=_segment_2024() + _segment_2025())
        shuffled = await _run(db_session, checkpoints=[checkpoints[2], checkpoints[0], checkpoints[1]], selection=_segment_2024() + _segment_2025())

        assert [result.as_of for result in in_order.checkpoints] == [EVE_2023, EVE_2024, EVE_2025]
        assert {result.as_of: _proposals(result) for result in in_order.checkpoints} == _three_segments_expected()
        assert shuffled.model_dump() == in_order.model_dump()

    @pytest.mark.asyncio
    async def test_one_import_or_three_give_the_same_result(self) -> None:
        """Three checkpoints in one call, or three calls in time order each saving what it proposed and selected: same proposals, same final state."""
        compute_gap_fix = _gap("compute_gap_fix")
        checkpoints = _three_checkpoints()
        segments = [_segment_2024(), _segment_2025(), []]
        async with _private_database() as one_import, _private_database() as three_imports:
            together = await compute_gap_fix(one_import, _request(checkpoints=checkpoints, selection=segments[0] + segments[1]))
            await _commit_items(one_import, _all_proposals(together) + segments[0] + segments[1])
            one_at_a_time: Dict[date, Counter] = {}
            for checkpoint, selection in zip(checkpoints, segments, strict=True):
                response = await compute_gap_fix(three_imports, _request(checkpoints=[checkpoint], selection=selection))
                one_at_a_time.update({result.as_of: _proposals(result) for result in response.checkpoints})
                await _commit_items(three_imports, _all_proposals(response) + selection)

            assert {result.as_of: _proposals(result) for result in together.checkpoints} == one_at_a_time == _three_segments_expected()
            final = ({"EUR": Decimal("880")}, {ASSET_A: Decimal("14"), ASSET_B: Decimal("5")})
            assert await _db_totals(one_import) == await _db_totals(three_imports) == final

    @pytest.mark.asyncio
    async def test_a_removed_proposal_returns_at_the_next_import(self, db_session: AsyncSession) -> None:
        """D-S24: this import does not compensate a proposal the user removes; the next one, compared with the database, proposes it again."""
        checkpoints = [_checkpoint(EVE_2023, "opening", cash=[_truth("EUR", "1000")]), _checkpoint(EVE_2024, cash=[_truth("EUR", "1100")])]
        first = await _run(db_session, checkpoints=checkpoints)
        assert _proposals(_at(first, EVE_2023)) == Counter([_deposit(EVE_2023, "EUR", "1000")])
        assert _proposals(_at(first, EVE_2024)) == Counter([_deposit(EVE_2024, "EUR", "100")])

        await _commit_items(db_session, _at(first, EVE_2024).proposals)  # the user removed the 2023 opening and saved the rest
        # The saved gap-fix is dated 2024-12-31, so the next import keeps only the checkpoints from that eve on (H0, D-S25).
        second = await _run(db_session, checkpoints=[checkpoints[1]])

        result = _at(second, EVE_2024)
        assert _cash_rows(result) == {"EUR": _cash_row("1100", "100", "1000")}
        assert _proposals(result) == Counter([_deposit(EVE_2024, "EUR", "1000")])

    @pytest.mark.asyncio
    async def test_two_sets_imported_together_on_an_empty_broker(self, db_session: AsyncSession) -> None:
        """Scenario 8 (design §11.3): two sets at once, each with its own opening; computed on the union, the second opening is already right."""
        cost = _money("EUR", "20")

        response = await _run(
            db_session,
            checkpoints=[
                _checkpoint(EVE_2024, "opening", cash=[_truth("EUR", "1000")], positions=[_position(ASSET_A, "10", unit_cost=cost)]),
                _checkpoint(EVE_2025, "opening", cash=[_truth("EUR", "700")], positions=[_position(ASSET_A, "15", unit_cost=cost)]),
            ],
            verifications=[_verification(_d("2026-12-31"), _truth("EUR", "880"))],
            selection=[
                _tx(BUY, "2025-03-10", cash=("EUR", "-250"), asset_id=ASSET_A, quantity="5"),
                _tx(DIVIDEND, "2025-06-16", cash=("EUR", "30"), asset_id=ASSET_A),
                _tx(WITHDRAWAL, "2025-09-01", cash=("EUR", "-80")),
                _tx(SELL, "2026-02-02", cash=("EUR", "180"), asset_id=ASSET_A, quantity="-3"),
            ],
        )

        assert _proposals(_at(response, EVE_2024)) == Counter([_deposit(EVE_2024, "EUR", "1000"), _adjustment(EVE_2024, ASSET_A, "10", ("EUR", "20"))])
        second = _at(response, EVE_2025)
        assert (second.proposals, second.todos) == ([], [])
        assert _cash_rows(second) == {"EUR": _cash_row("700", "700", "0")}
        assert _position_rows(second) == {ASSET_A: _position_row("exact", "15", "15", "0")}
        assert _verified(response, _d("2026-12-31")).ok is True


# =============================================================================
# FIXTURE GUARDS
# =============================================================================


class TestA3FixtureGuards:
    """Fixture guards (pass before and after A3): the infrastructure of this file works, so every A3 red is about the product.

    Most A3 tests look the missing piece up first and never reach their helpers
    before the cure; without these, a broken helper would only surface afterwards,
    looking like a product defect.
    """

    @pytest.mark.asyncio
    async def test_fixture_guard_private_database(self, db_session: AsyncSession) -> None:
        """Fixture guard: both brokers and the three assets are there; ``_add``, ``_db_totals`` and ``_transaction_count`` agree."""
        await _add(
            db_session,
            _saved(DEPOSIT, "2024-01-02", amount="100", currency="EUR"),
            _saved(BUY, "2024-01-03", amount="-40", currency="EUR", asset_id=ASSET_A, quantity="2"),
            _saved(DEPOSIT, "2024-01-04", amount="9", currency="EUR", broker_id=OTHER_BROKER_ID),
        )

        brokers = (await db_session.execute(select(Broker.id))).scalars().all()
        assets = (await db_session.execute(select(Asset.id))).scalars().all()

        assert (sorted(brokers), sorted(assets)) == ([BROKER_ID, OTHER_BROKER_ID], [ASSET_A, ASSET_B, ASSET_C])
        assert await _db_totals(db_session) == ({"EUR": Decimal("60")}, {ASSET_A: Decimal("2")})
        assert await _db_totals(db_session, OTHER_BROKER_ID) == ({"EUR": Decimal("9")}, {})
        assert await _transaction_count(db_session) == 3

    @pytest.mark.asyncio
    async def test_fixture_guard_ledger(self, db_session: AsyncSession) -> None:
        """Fixture guard: the section 1 ledger holds what its docstring says, per broker."""
        ledger = await _seed_ledger(db_session)

        assert len({row.id for row in ledger.values()}) == 8
        assert await _db_totals(db_session) == ({"EUR": Decimal("590"), "USD": Decimal("20")}, {ASSET_A: Decimal("8"), ASSET_B: Decimal("3")})
        assert await _db_totals(db_session, OTHER_BROKER_ID) == ({"EUR": Decimal("7776")}, {ASSET_A: Decimal("99")})

    @pytest.mark.asyncio
    async def test_fixture_guard_commit_items(self, db_session: AsyncSession) -> None:
        """Fixture guard: ``_commit_items`` saves unsaved transactions as the batch pipeline does: cash, quantity, tags and cost basis."""
        items = [
            TXCreateItem(broker_id=BROKER_ID, type=DEPOSIT, date=EVE_2024, cash=_money("EUR", "12.50"), tags=["import", GENERIC_TAG, GAP_FIX_TAG], description="Gap-fix 2024-12-31"),
            TXCreateItem(broker_id=BROKER_ID, type=ADJUSTMENT, date=EVE_2024, asset_id=ASSET_A, quantity=Decimal("3"), cost_basis_override=_money("EUR", "7")),
        ]

        await _commit_items(db_session, items)

        rows = (await db_session.execute(select(Transaction).order_by(Transaction.id))).scalars().all()
        assert [(row.type, row.date, row.amount, row.currency, row.asset_id, row.quantity, row.tags, row.cost_basis_override, row.cost_basis_currency) for row in rows] == [
            (DEPOSIT, EVE_2024, Decimal("12.5"), "EUR", None, Decimal("0"), "import,generic_csv,gap_fix", None, None),
            (ADJUSTMENT, EVE_2024, Decimal("0"), None, ASSET_A, Decimal("3"), None, Decimal("7"), "EUR"),
        ]
        assert await _db_totals(db_session) == ({"EUR": Decimal("12.5")}, {ASSET_A: Decimal("3")})

    def test_fixture_guard_fake_bank_plugin(self, fake_bank_plugin: BRIMProvider) -> None:
        """Fixture guard: the fake is registered under its code, and its history tag is not derived from that code."""
        assert BRIMProviderRegistry.get_provider_instance(FAKE_BANK_CODE) is not None
        assert (fake_bank_plugin.provider_code, fake_bank_plugin.history_tag, fake_bank_plugin.provider_name) == (FAKE_BANK_CODE, FAKE_BANK_TAG, FAKE_BANK_NAME)
        assert fake_bank_plugin.history_tag != FAKE_BANK_CODE.removeprefix("broker_")
        assert not fake_bank_plugin.is_report_set_plugin

    def test_fixture_guard_builders_and_keys(self) -> None:
        """Fixture guard: the builders make valid A1 objects, the scenarios are valid, and ``_key`` compares numbers whatever their scale."""
        checkpoint = _checkpoint(EVE_2024, "opening", cash=[_truth("eur", "1523.40")], positions=[_position(ASSET_A, "10", unit_cost=_money("EUR", "31.25"))])
        deposit = TXCreateItem(broker_id=BROKER_ID, type=DEPOSIT, date=EVE_2024, quantity=Decimal("0E-6"), cash=_money("EUR", "1523.400000"))
        adjustment = TXCreateItem(broker_id=BROKER_ID, type=ADJUSTMENT, date=EVE_2024, asset_id=ASSET_A, quantity=Decimal("4.000000"), cash=_money("EUR", "0"), cost_basis_override=_money("EUR", "31.250000"))

        assert (checkpoint.as_of, checkpoint.kind, checkpoint.cash[0].currency, checkpoint.positions[0].unit_cost) == (EVE_2024, "opening", "EUR", _money("EUR", "31.25"))
        assert (_key(deposit), _key(adjustment)) == (_deposit(EVE_2024, "EUR", "1523.40"), _adjustment(EVE_2024, ASSET_A, "4", ("EUR", "31.25")))
        assert [len(checkpoints) for checkpoints in (_first_import()["checkpoints"], _three_checkpoints())] == [1, 3]
        assert (len(_segment_2024()), len(_segment_2025()), sum(len(counter) for counter in _three_segments_expected().values())) == (3, 2, 7)
