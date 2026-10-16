"""
Red tests for the loader of split links (release 1.3, workstream MF, lot MF-I1).

Module under test: ``backend/app/services/financial_math/splits.py``, new — ``SplitLink``, ``load_split_links`` and
``is_valid_split_ratio``.

What the module replaces: five copies of one join, «the ADJUSTMENT rows linked to a SPLIT AssetEvent»,
``Transaction ⋈ AssetEvent ON Transaction.asset_event_id == AssetEvent.id WHERE Transaction.id IN (candidates) AND
AssetEvent.type == SPLIT``, the candidates being the ids of the given transactions that carry an ``asset_event_id``.
Each copy reads its own columns of the join today:

* ``financial_math/portfolio/engine.py`` (step 3b): transaction id, event id, event asset id, event date, event value;
  raises ``ValueError`` on a ratio that is None, not finite or not positive, and keeps one record per event;
* ``lots_analysis_service.py``, ``_load_split_ratios``: transaction id → event value, nothing checked;
* ``financial_math/yield_on_cost.py``, ``_load_split_records``: ten columns into ``_SplitRecord``, ordered by
  transaction id, a row whose transaction has no asset dropped;
* ``portfolio_service.py`` and ``brokers/summary.py``: the transaction ids only (a later lot).

The contract pinned here, agreed for MF-I1:

* ``SplitLink`` is a frozen, slotted dataclass of the ten columns of ``_SplitRecord``, in that order, the transaction's
  asset id nullable;
* ``load_split_links(db, transactions)`` returns one ``SplitLink`` per given transaction linked to a SPLIT AssetEvent,
  ordered by transaction id whatever the order it was given in; ``[]`` and no statement at all when no given
  transaction carries an ``asset_event_id``; a linked row of the table that was not given is never returned;
* the loader filters nothing beyond the join and validates nothing: a ratio of zero, a negative or a null one, a
  transaction that is not an ADJUSTMENT, a zero quantity, an asset or a date other than the event's, a transaction
  without an asset (``None``) all come back as stored — each caller decides what it accepts;
* ``is_valid_split_ratio(ratio)`` is the rule the engine and Yield on Cost write in place today — present, finite and
  positive — as a ``bool``, and it never raises, not even on a signalling NaN.

On file: every test that reads builds a private SQLite file under ``tmp_path`` with the app schema
(``SQLModel.metadata.create_all``), opened with an engine of its own (``sqlite+aiosqlite``, NullPool, the PRAGMA
listener of ``backend.app.db.session``, so foreign keys are enforced) and disposed at teardown, before the aiosqlite
leak guard looks: no server, no session on the lane's database, no network. One file departs from the app schema on
purpose: ``asset_events.value`` is ``NOT NULL`` in the model and in the migration, so the null ratio that
``SplitLink.ratio`` admits can only be stored on a file whose copy of the schema lets that one column be null
(``_create_schema_admitting_a_null_ratio``; the app's metadata is never touched). Rows are seeded with explicit ids,
each kind in its own range (brokers 1-2, assets 5-7, transactions 11-29, events 31-39), so a column read in place of
another shows.

Red by absence until MF-I1: ``splits.py`` is imported while each test runs (``_splits()``), never at module level, so
the file collects today and every test fails on the missing module (``ModuleNotFoundError``) before it seeds anything.

MF-I2 adds ``split_linked_ids(db, transactions) -> set[int]``: the ids of the given transactions linked to a SPLIT
asset event, ``{link.transaction_id for link in load_split_links(...)}``, what an average-cost replay needs to mark a
row as a split rescale (the WAC preview of ``portfolio_service.py``, the broker summary, the auto cost). It judges no
ratio: the rescale reads the row's own quantity, never the event's ratio. ``TestSplitLinkedIds`` reads it off the module
when each test runs (``_split_linked_ids()``), before seeding anything: on a tree with MF-I1's ``splits.py`` and without
it, every one of those tests fails on ``AttributeError`` and the rest of the file still collects and runs.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Sequence
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import MetaData, event, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # every model, for create_all; importing backend.app.db brings the session module and its PRAGMA listener
from backend.app.db.models import Asset, AssetEvent, AssetEventType, Broker, Transaction, TransactionType
from backend.test_scripts.test_utils import print_section, print_success

SPLITS_MODULE = "backend.app.services.financial_math.splits"

#: The ten columns of the join, in the order of Yield on Cost's ``_SplitRecord``.
SPLIT_LINK_FIELDS = ("transaction_id", "event_id", "transaction_asset_id", "event_asset_id", "broker_id", "transaction_type", "transaction_quantity", "transaction_date", "event_date", "ratio")

SPLIT = AssetEventType.SPLIT
#: Every other type of AssetEvent: a row linked to one of them is not a split, whatever else it looks like.
NON_SPLIT_EVENT_TYPES = tuple(event_type for event_type in AssetEventType if event_type is not AssetEventType.SPLIT)

ADJUSTMENT = TransactionType.ADJUSTMENT
BUY = TransactionType.BUY
DEPOSIT = TransactionType.DEPOSIT
DIVIDEND = TransactionType.DIVIDEND

B1, B2 = 1, 2
A5, A7 = 5, 7

D_BUY = date(2024, 1, 2)
D_SPLIT = date(2024, 6, 3)
D_LATE = date(2024, 6, 5)
D_REVERSE_SPLIT = date(2024, 9, 2)

#: Ratios ``is_valid_split_ratio`` refuses: missing, zero (with an exponent and a sign too), negative, not finite.
INVALID_RATIOS = (None, Decimal("0"), Decimal("-0"), Decimal("0.000000"), Decimal("-1"), Decimal("-0.5"), Decimal("NaN"), Decimal("-NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity"))
#: Ratios it accepts: a split, a reverse split, a no-op, the six decimals SQLite gives back, the smallest the column holds.
VALID_RATIOS = (Decimal("2"), Decimal("0.5"), Decimal("1"), Decimal("10"), Decimal("2.000000"), Decimal("0.000001"))


def _splits() -> ModuleType:
    """``financial_math/splits.py``, imported when a test runs: until MF-I1 it does not exist."""
    return importlib.import_module(SPLITS_MODULE)


def _split_linked_ids() -> Callable[[AsyncSession, Sequence[Transaction]], Awaitable[set[int]]]:
    """``splits.split_linked_ids``, read when a test runs: until MF-I2 the module has no such name (AttributeError)."""
    return _splits().split_linked_ids


def _engine_rejects_today(ratio: Decimal | None) -> bool:
    """The engine's check, ``portfolio/engine.py`` step 3b, as written (Yield on Cost's ``_index_split_records`` writes the same)."""
    return ratio is None or not ratio.is_finite() or ratio <= 0


# =============================================================================
# Rows
# =============================================================================


def _asset_event(event_id: int, asset_id: int, day: date, *, event_type: AssetEventType = SPLIT, value: str | None = "2") -> AssetEvent:
    """A row of ``asset_events``: ``value`` is the ratio of a SPLIT; ``None`` only on a file that admits it."""
    return AssetEvent(id=event_id, asset_id=asset_id, date=day, type=event_type, value=None if value is None else Decimal(value), currency="EUR")


def _transaction(tx_id: int, tx_type: TransactionType, day: date, broker_id: int, *, asset_id: int | None, quantity: str = "0", amount: str = "0", currency: str | None = None, asset_event_id: int | None = None) -> Transaction:
    """A row of ``transactions``: ``quantity`` and ``amount`` never null, ``currency`` only on a row that moves cash."""
    return Transaction(id=tx_id, broker_id=broker_id, asset_id=asset_id, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency, asset_event_id=asset_event_id)


def _link(
    splits: ModuleType,
    transaction_id: int,
    event_id: int,
    *,
    transaction_asset_id: int | None,
    event_asset_id: int,
    broker_id: int,
    transaction_type: TransactionType,
    transaction_quantity: str,
    transaction_date: date,
    event_date: date,
    ratio: str | None,
) -> Any:
    """The ``SplitLink`` a row of the join must come back as. Amounts compare by value: SQLite gives six decimals back."""
    return splits.SplitLink(
        transaction_id=transaction_id,
        event_id=event_id,
        transaction_asset_id=transaction_asset_id,
        event_asset_id=event_asset_id,
        broker_id=broker_id,
        transaction_type=transaction_type,
        transaction_quantity=Decimal(transaction_quantity),
        transaction_date=transaction_date,
        event_date=event_date,
        ratio=None if ratio is None else Decimal(ratio),
    )


def _shown(links: Sequence[Any]) -> str:
    """One link per line, for a failure message."""
    return "\n".join(repr(link) for link in links) or "(none)"


def _assert_link_types(splits: ModuleType, links: Any) -> None:
    """A list of ``SplitLink`` whose columns have the types the dataclass declares (an enum, Decimals, dates, ints)."""
    assert type(links) is list, f"load_split_links returned a {type(links).__name__}, not a list"
    for link in links:
        assert type(link) is splits.SplitLink, f"not a SplitLink: {link!r}"
        assert all(type(value) is int for value in (link.transaction_id, link.event_id, link.event_asset_id, link.broker_id)), f"ids must be ints: {link!r}"
        assert link.transaction_asset_id is None or type(link.transaction_asset_id) is int, f"transaction_asset_id must be an int or None: {link!r}"
        assert isinstance(link.transaction_type, TransactionType), f"transaction_type must be a TransactionType, not {type(link.transaction_type).__name__}"
        assert type(link.transaction_quantity) is Decimal, f"transaction_quantity must be a Decimal: {link!r}"
        assert type(link.transaction_date) is date and type(link.event_date) is date, f"both dates must be dates: {link!r}"
        assert link.ratio is None or type(link.ratio) is Decimal, f"ratio must be a Decimal or None: {link!r}"


# =============================================================================
# Private SQLite files
# =============================================================================

SplitFile = Callable[..., Awaitable[AsyncEngine]]


def _create_schema_admitting_a_null_ratio(sync_connection: Any) -> None:
    """The app schema with one change, ``asset_events.value`` nullable, built from a copy: the app's metadata stays as it is."""
    metadata = MetaData()
    for table in SQLModel.metadata.tables.values():
        table.to_metadata(metadata)
    metadata.tables["asset_events"].c["value"].nullable = True
    metadata.create_all(sync_connection)


async def _write(engine: AsyncEngine, asset_events: list[AssetEvent], transactions: list[Transaction]) -> None:
    """The rows written, with the brokers and assets their foreign keys need, nothing more."""
    broker_ids = sorted({row.broker_id for row in transactions})
    asset_ids = sorted({row.asset_id for row in transactions if row.asset_id is not None} | {row.asset_id for row in asset_events})
    async with AsyncSession(engine) as session:
        session.add_all([Broker(id=broker_id, name=f"mf-i1-broker-{broker_id}") for broker_id in broker_ids])
        session.add_all([Asset(id=asset_id, display_name=f"mf-i1-asset-{asset_id}", currency="EUR") for asset_id in asset_ids])
        await session.flush()
        session.add_all(asset_events)
        await session.flush()
        session.add_all(transactions)
        await session.commit()


@pytest_asyncio.fixture
async def split_file(tmp_path: Path) -> AsyncIterator[SplitFile]:
    """A factory of private SQLite files under ``tmp_path``: the app schema, the rows given, an engine of their own.

    Opened as production opens its database (``sqlite+aiosqlite``, NullPool, the PRAGMA listener of
    ``backend.app.db.session``); every engine is disposed at teardown, before the aiosqlite leak guard looks.
    ``null_ratio_allowed=True`` builds the one schema that departs from the app's (``asset_events.value`` nullable).
    """
    engines: list[AsyncEngine] = []

    async def make(name: str, asset_events: list[AssetEvent], transactions: list[Transaction], *, null_ratio_allowed: bool = False) -> AsyncEngine:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / name}", poolclass=NullPool)
        engines.append(engine)
        async with engine.begin() as connection:
            await connection.run_sync(_create_schema_admitting_a_null_ratio if null_ratio_allowed else SQLModel.metadata.create_all)
        await _write(engine, asset_events, transactions)
        return engine

    try:
        yield make
    finally:
        for engine in engines:
            await engine.dispose()


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


async def _given(session: AsyncSession, transaction_ids: Sequence[int]) -> list[Transaction]:
    """The transactions with these ids, read through ``session`` as a caller reads them, in this order."""
    if not transaction_ids:
        return []
    rows = (await session.execute(select(Transaction).where(Transaction.id.in_(transaction_ids)))).scalars().all()
    by_id = {row.id: row for row in rows}
    missing = [tx_id for tx_id in transaction_ids if tx_id not in by_id]
    assert not missing, f"transactions {missing} are not on the file: the seed is wrong, not the loader"
    return [by_id[tx_id] for tx_id in transaction_ids]


async def _load(splits: ModuleType, engine: AsyncEngine, transaction_ids: Sequence[int], *, container: Callable[[list[Transaction]], Sequence[Transaction]] = list) -> tuple[Any, list[str]]:
    """``load_split_links`` on a fresh session of ``engine``, given those transactions in that order; with every statement the call sent."""
    async with AsyncSession(engine) as session:
        given = container(await _given(session, transaction_ids))
        with captured_statements(engine) as statements:
            links = await splits.load_split_links(session, given)
    return links, statements


def _unsaved(asset_event_id: int) -> Transaction:
    """An ADJUSTMENT of asset 5 never written, so without an id, that already names the event ``asset_event_id``."""
    unsaved = Transaction(broker_id=B1, asset_id=A5, type=ADJUSTMENT, date=D_SPLIT, quantity=Decimal("10"), amount=Decimal("0"), asset_event_id=asset_event_id)
    assert unsaved.id is None, "precondition: a transaction never written has no id"
    return unsaved


async def _load_ids(split_linked_ids: Callable[..., Awaitable[Any]], engine: AsyncEngine, given: Sequence[int | Transaction], *, container: Callable[[list[Transaction]], Sequence[Transaction]] = list) -> tuple[Any, list[str]]:
    """``split_linked_ids`` on a fresh session of ``engine``, with every statement the call sent.

    ``given`` in that order: an int is the transaction of that id, read from the file; a ``Transaction`` is passed as it is.
    """
    async with AsyncSession(engine) as session:
        read = {row.id: row for row in await _given(session, [item for item in given if isinstance(item, int)])}
        transactions = container([read[item] if isinstance(item, int) else item for item in given])
        with captured_statements(engine) as statements:
            ids = await split_linked_ids(session, transactions)
    return ids, statements


def _assert_id_set(ids: Any) -> None:
    """A ``set`` of ints: the ids as the database gives them, not links, not a list."""
    assert type(ids) is set, f"split_linked_ids returned a {type(ids).__name__}, not a set: {ids!r}"
    assert all(type(tx_id) is int for tx_id in ids), f"the ids must be ints: {ids!r}"


def _assert_one_read(statements: Sequence[str]) -> None:
    """With a candidate the ids are read in one statement, a SELECT, through the session given."""
    assert len(statements) == 1, f"one query for every candidate, not {len(statements)}: {statements}"
    assert statements[0].lstrip().upper().startswith("SELECT"), f"split_linked_ids only reads: {statements}"


# =============================================================================
# M0 — the agreed API
# =============================================================================


class TestAgreedApi:
    def test_m0_split_link_is_a_frozen_slotted_dataclass_of_the_ten_columns(self):
        """``SplitLink`` has the ten columns of ``_SplitRecord`` in that order, is frozen and slotted, compares and hashes
        by value; ``load_split_links`` is a coroutine function, ``is_valid_split_ratio`` a plain one.

        Before MF-I1: ModuleNotFoundError (no ``financial_math/splits.py``).
        """
        print_section("M0 — the agreed API")
        splits = _splits()
        assert dataclasses.is_dataclass(splits.SplitLink), "SplitLink must be a dataclass"
        assert tuple(field.name for field in dataclasses.fields(splits.SplitLink)) == SPLIT_LINK_FIELDS
        link = _link(splits, 21, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="10", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="2")
        same = _link(splits, 21, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="10.000000", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="2.000000")
        assert link == same, "compared by value: a Decimal read back from SQLite with six decimals equals the one written"
        assert hash(link) == hash(same), "hashed by value"
        with pytest.raises(dataclasses.FrozenInstanceError):
            link.ratio = Decimal("3")
        assert not hasattr(link, "__dict__"), "a dataclass with slots has no instance __dict__"
        assert inspect.iscoroutinefunction(splits.load_split_links), "load_split_links reads the database: a coroutine function"
        assert callable(splits.is_valid_split_ratio) and not inspect.iscoroutinefunction(splits.is_valid_split_ratio), "is_valid_split_ratio is a plain function"
        print_success("ten columns in order, frozen, slotted, compared by value")


# =============================================================================
# M5 (rule) — is_valid_split_ratio
# =============================================================================


class TestIsValidSplitRatio:
    @pytest.mark.parametrize("ratio", INVALID_RATIOS, ids=repr)
    def test_m5_a_missing_zero_negative_or_non_finite_ratio_is_not_valid(self, ratio):
        """False, a ``bool``, never an exception: a quiet or signalling NaN refuses ordering, so the finiteness check must come first.

        Agrees with the check the engine writes in place today. Before MF-I1: ModuleNotFoundError.
        """
        print_section(f"M5 — is_valid_split_ratio({ratio!r})")
        assert _engine_rejects_today(ratio), "the oracle: today's check rejects it"
        splits = _splits()
        assert splits.is_valid_split_ratio(ratio) is False
        print_success(f"{ratio!r} is not a usable split ratio")

    @pytest.mark.parametrize("ratio", VALID_RATIOS, ids=repr)
    def test_m5_a_present_finite_positive_ratio_is_valid(self, ratio):
        """True, a ``bool``: a split, a reverse split, a no-op, the six decimals SQLite gives back.

        Agrees with the check the engine writes in place today. Before MF-I1: ModuleNotFoundError.
        """
        print_section(f"M5 — is_valid_split_ratio({ratio!r})")
        assert not _engine_rejects_today(ratio), "the oracle: today's check accepts it"
        splits = _splits()
        assert splits.is_valid_split_ratio(ratio) is True
        print_success(f"{ratio!r} is a usable split ratio")


# =============================================================================
# M1-M7 — load_split_links on private SQLite files
# =============================================================================


class TestLoadSplitLinks:
    @pytest.mark.asyncio
    async def test_m1_a_split_on_two_brokers_comes_back_column_by_column(self, split_file):
        """A 3:1 split of asset 5 realized on two brokers: each ADJUSTMENT comes back with every column of the join.

        The buys that precede it are given too and are not linked to anything: they are not returned. The read goes
        through the session given (at least one statement reaches its engine), and is only a read.
        Before MF-I1: ModuleNotFoundError.
        """
        print_section("M1 — a split pair on two brokers")
        splits = _splits()
        engine = await split_file(
            "split-pair.db",
            [_asset_event(31, A5, D_SPLIT, value="3")],
            [
                _transaction(11, BUY, D_BUY, B1, asset_id=A5, quantity="10", amount="-1000", currency="EUR"),
                _transaction(12, BUY, D_BUY, B2, asset_id=A5, quantity="4", amount="-400", currency="EUR"),
                _transaction(21, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="20", asset_event_id=31),
                _transaction(22, ADJUSTMENT, D_SPLIT, B2, asset_id=A5, quantity="8", asset_event_id=31),
            ],
        )
        links, statements = await _load(splits, engine, [11, 12, 21, 22])

        _assert_link_types(splits, links)
        expected = [
            _link(splits, 21, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="20", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="3"),
            _link(splits, 22, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B2, transaction_type=ADJUSTMENT, transaction_quantity="8", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="3"),
        ]
        assert links == expected, f"the links:\n{_shown(links)}"
        assert links[0].transaction_type is ADJUSTMENT and links[1].transaction_type is ADJUSTMENT, "the member of TransactionType, not its text"
        assert statements, "no statement reached the engine of the session given: the links were read from somewhere else"
        assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements), f"the loader only reads: {statements}"
        print_success("two links, every column right, read through the session given")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("event_type", NON_SPLIT_EVENT_TYPES, ids=str)
    async def test_m2_a_row_linked_to_another_type_of_event_is_not_returned(self, split_file, event_type):
        """An ADJUSTMENT linked to an event of another type is not a split link, even on the split's asset, date and value.

        Row 22 differs from row 21 only by the type of its event; a DIVIDEND realizing a DIVIDEND event (row 23) is
        not returned either. Row 21, linked to the SPLIT, is the presence barrier: the absence of 22 and 23 means
        something only because 21 comes back. Before MF-I1: ModuleNotFoundError.
        """
        print_section(f"M2 — a row linked to a {event_type} event")
        splits = _splits()
        engine = await split_file(
            "other-event-type.db",
            [
                _asset_event(31, A5, D_SPLIT, value="2"),
                _asset_event(32, A5, D_SPLIT, event_type=event_type, value="2"),
                _asset_event(33, A5, D_LATE, event_type=AssetEventType.DIVIDEND, value="0.35"),
            ],
            [
                _transaction(11, BUY, D_BUY, B1, asset_id=A5, quantity="10", amount="-1000", currency="EUR"),
                _transaction(21, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=31),
                _transaction(22, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=32),
                _transaction(23, DIVIDEND, D_LATE, B1, asset_id=A5, amount="7", currency="EUR", asset_event_id=33),
            ],
        )
        links, _statements = await _load(splits, engine, [11, 21, 22, 23])

        _assert_link_types(splits, links)
        assert links == [_link(splits, 21, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="10", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="2")], f"only the row linked to the SPLIT, got:\n{_shown(links)}"
        print_success(f"the row linked to the {event_type} event is not a split link")

    @pytest.mark.asyncio
    async def test_m3_without_a_candidate_the_loader_returns_an_empty_list_and_sends_nothing(self, split_file):
        """No transaction given, or none that carries an ``asset_event_id``: ``[]``, and not a single statement.

        The same file then given a linked row among unlinked ones (a buy, a cash deposit without an asset), as a tuple:
        only the linked row comes back, and this time the loader does read — the barrier that makes the two silences
        above mean "nothing to ask" rather than "never asks". Before MF-I1: ModuleNotFoundError.
        """
        print_section("M3 — no candidate")
        splits = _splits()
        engine = await split_file(
            "no-candidate.db",
            [_asset_event(31, A5, D_SPLIT, value="2")],
            [
                _transaction(11, BUY, D_BUY, B1, asset_id=A5, quantity="10", amount="-1000", currency="EUR"),
                _transaction(12, DEPOSIT, D_BUY, B1, asset_id=None, amount="5000", currency="EUR"),
                _transaction(21, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=31),
            ],
        )
        nothing_given, nothing_given_statements = await _load(splits, engine, [])
        unlinked_only, unlinked_only_statements = await _load(splits, engine, [11, 12])
        mixed, mixed_statements = await _load(splits, engine, [12, 21, 11], container=tuple)

        assert nothing_given == [] and type(nothing_given) is list, f"nothing given: {nothing_given!r}"
        assert nothing_given_statements == [], f"nothing given, yet the loader sent: {nothing_given_statements}"
        assert unlinked_only == [] and type(unlinked_only) is list, f"no linked row given: {unlinked_only!r}"
        assert unlinked_only_statements == [], f"no candidate, yet the loader sent: {unlinked_only_statements}"
        _assert_link_types(splits, mixed)
        assert mixed == [_link(splits, 21, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="10", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="2")], f"the linked row among unlinked ones:\n{_shown(mixed)}"
        assert mixed_statements, "with a candidate the loader must read"
        print_success("no candidate: [] and no statement; with one, only the linked row")

    @pytest.mark.asyncio
    async def test_m4_links_come_back_by_transaction_id_whatever_the_order_given(self, split_file):
        """Ordered by transaction id: not by the order given, not by date, not by event.

        A 2:1 split of asset 5 in June (event 31) and a 1:2 reverse split of asset 7 in September (event 32), their
        rows interleaved: 21 and 23 realize the September event, 22 and 24 the June one. Ordered by date or by event the
        rows would read 22, 24, 21, 23; by transaction id they read 21, 22, 23, 24, whatever the order of the input.
        Before MF-I1: ModuleNotFoundError.
        """
        print_section("M4 — ordered by transaction id")
        splits = _splits()
        engine = await split_file(
            "order.db",
            [_asset_event(31, A5, D_SPLIT, value="2"), _asset_event(32, A7, D_REVERSE_SPLIT, value="0.5")],
            [
                _transaction(11, BUY, D_BUY, B1, asset_id=A5, quantity="10", amount="-1000", currency="EUR"),
                _transaction(12, BUY, D_BUY, B2, asset_id=A5, quantity="4", amount="-400", currency="EUR"),
                _transaction(13, BUY, D_BUY, B1, asset_id=A7, quantity="30", amount="-300", currency="EUR"),
                _transaction(14, BUY, D_BUY, B2, asset_id=A7, quantity="8", amount="-80", currency="EUR"),
                _transaction(21, ADJUSTMENT, D_REVERSE_SPLIT, B1, asset_id=A7, quantity="-15", asset_event_id=32),
                _transaction(22, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=31),
                _transaction(23, ADJUSTMENT, D_REVERSE_SPLIT, B2, asset_id=A7, quantity="-4", asset_event_id=32),
                _transaction(24, ADJUSTMENT, D_SPLIT, B2, asset_id=A5, quantity="4", asset_event_id=31),
            ],
        )
        orders = {
            "by id": [11, 12, 13, 14, 21, 22, 23, 24],
            "reversed": [24, 23, 22, 21, 14, 13, 12, 11],
            "shuffled": [22, 11, 24, 13, 21, 12, 23, 14],
            "by date": [11, 12, 13, 14, 22, 24, 21, 23],
        }
        results = {name: (await _load(splits, engine, order))[0] for name, order in orders.items()}

        expected = [
            _link(splits, 21, 32, transaction_asset_id=A7, event_asset_id=A7, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="-15", transaction_date=D_REVERSE_SPLIT, event_date=D_REVERSE_SPLIT, ratio="0.5"),
            _link(splits, 22, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="10", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="2"),
            _link(splits, 23, 32, transaction_asset_id=A7, event_asset_id=A7, broker_id=B2, transaction_type=ADJUSTMENT, transaction_quantity="-4", transaction_date=D_REVERSE_SPLIT, event_date=D_REVERSE_SPLIT, ratio="0.5"),
            _link(splits, 24, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B2, transaction_type=ADJUSTMENT, transaction_quantity="4", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="2"),
        ]
        for name, links in results.items():
            _assert_link_types(splits, links)
            assert [link.transaction_id for link in links] == [21, 22, 23, 24], f"given {name} ({orders[name]}), the order came back as {[link.transaction_id for link in links]}"
            assert links == expected, f"given {name}:\n{_shown(links)}"
        print_success(f"{len(orders)} input orders, one output order: by transaction id")

    @pytest.mark.asyncio
    async def test_m5_the_loader_validates_nothing_it_returns_every_row_of_the_join_as_stored(self, split_file):
        """No validation inside the loader: what Yield on Cost and the engine refuse today still comes back, as stored.

        A SPLIT with a ratio of zero (row 21), one with a negative ratio (row 22), a DIVIDEND with no quantity linked to a
        split (row 23), an ADJUSTMENT on another asset and another date than its event's (row 24, which also tells the
        transaction's asset and date from the event's), a second row of the same event on the same broker (row 25).
        ``is_valid_split_ratio`` is what tells the usable ratios apart, on the links themselves.
        Before MF-I1: ModuleNotFoundError.
        """
        print_section("M5 — no validation in the loader")
        splits = _splits()
        engine = await split_file(
            "unvalidated.db",
            [
                _asset_event(31, A5, D_SPLIT, value="0"),
                _asset_event(32, A5, D_SPLIT, value="-1"),
                _asset_event(33, A5, D_SPLIT, value="2"),
            ],
            [
                _transaction(11, BUY, D_BUY, B1, asset_id=A5, quantity="10", amount="-1000", currency="EUR"),
                _transaction(21, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=31),
                _transaction(22, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=32),
                _transaction(23, DIVIDEND, D_SPLIT, B1, asset_id=A5, amount="7", currency="EUR", asset_event_id=33),
                _transaction(24, ADJUSTMENT, D_LATE, B2, asset_id=A7, quantity="6", asset_event_id=33),
                _transaction(25, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=33),
            ],
        )
        links, _statements = await _load(splits, engine, [11, 21, 22, 23, 24, 25])

        _assert_link_types(splits, links)
        expected = [
            _link(splits, 21, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="10", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="0"),
            _link(splits, 22, 32, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="10", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="-1"),
            _link(splits, 23, 33, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=DIVIDEND, transaction_quantity="0", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="2"),
            _link(splits, 24, 33, transaction_asset_id=A7, event_asset_id=A5, broker_id=B2, transaction_type=ADJUSTMENT, transaction_quantity="6", transaction_date=D_LATE, event_date=D_SPLIT, ratio="2"),
            _link(splits, 25, 33, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="10", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="2"),
        ]
        assert links == expected, f"every row of the join, as stored:\n{_shown(links)}"
        assert links[2].transaction_type is DIVIDEND, "the transaction's own type, whatever its event"
        assert [splits.is_valid_split_ratio(link.ratio) for link in links] == [False, False, True, True, True], "is_valid_split_ratio on the links' ratios"
        print_success("zero, negative, foreign type, zero quantity, other asset and date, duplicate: all returned")

    @pytest.mark.asyncio
    async def test_m5_a_null_ratio_comes_back_as_none(self, split_file):
        """A SPLIT whose value is NULL comes back with ``ratio=None``: no ``IS NOT NULL`` in the query, no row skipped.

        Only reachable on a file whose schema admits it (the app's says ``NOT NULL``): the file is checked to hold the
        NULL first, or the test would prove nothing. Row 22, on a split with a ratio, comes back beside it.
        Before MF-I1: ModuleNotFoundError.
        """
        print_section("M5 — a null ratio")
        splits = _splits()
        engine = await split_file(
            "null-ratio.db",
            [_asset_event(31, A5, D_SPLIT, value=None), _asset_event(32, A5, D_LATE, value="2")],
            [
                _transaction(21, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=31),
                _transaction(22, ADJUSTMENT, D_LATE, B1, asset_id=A5, quantity="20", asset_event_id=32),
            ],
            null_ratio_allowed=True,
        )
        async with AsyncSession(engine) as session:
            stored = (await session.execute(select(AssetEvent.value).where(AssetEvent.id == 31))).scalar_one()
        assert stored is None, f"the file holds {stored!r} for event 31, not NULL: the schema did not admit a null ratio"

        links, _statements = await _load(splits, engine, [22, 21])

        _assert_link_types(splits, links)
        expected = [
            _link(splits, 21, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="10", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio=None),
            _link(splits, 22, 32, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="20", transaction_date=D_LATE, event_date=D_LATE, ratio="2"),
        ]
        assert links == expected, f"the null ratio, as stored:\n{_shown(links)}"
        assert links[0].ratio is None
        assert splits.is_valid_split_ratio(links[0].ratio) is False and splits.is_valid_split_ratio(links[1].ratio) is True
        print_success("ratio None returned, and refused by is_valid_split_ratio")

    @pytest.mark.asyncio
    async def test_m6_only_the_transactions_given_are_considered(self, split_file):
        """A linked row on the file that was not given is never returned: the candidates are the transactions given.

        Three rows linked to two splits, given one, then the two others in reverse: each call returns exactly what it
        was given, by transaction id. Before MF-I1: ModuleNotFoundError.
        """
        print_section("M6 — only the transactions given")
        splits = _splits()
        engine = await split_file(
            "given-only.db",
            [_asset_event(31, A5, D_SPLIT, value="3"), _asset_event(32, A7, D_LATE, value="2")],
            [
                _transaction(21, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="20", asset_event_id=31),
                _transaction(22, ADJUSTMENT, D_SPLIT, B2, asset_id=A5, quantity="8", asset_event_id=31),
                _transaction(23, ADJUSTMENT, D_LATE, B1, asset_id=A7, quantity="5", asset_event_id=32),
            ],
        )
        first, _first_statements = await _load(splits, engine, [21])
        others, _other_statements = await _load(splits, engine, [23, 22])

        _assert_link_types(splits, first)
        _assert_link_types(splits, others)
        assert first == [_link(splits, 21, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="20", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="3")], f"given row 21 only:\n{_shown(first)}"
        assert others == [
            _link(splits, 22, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B2, transaction_type=ADJUSTMENT, transaction_quantity="8", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="3"),
            _link(splits, 23, 32, transaction_asset_id=A7, event_asset_id=A7, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="5", transaction_date=D_LATE, event_date=D_LATE, ratio="2"),
        ], f"given rows 23 and 22:\n{_shown(others)}"
        print_success("each call returns the linked rows it was given, and no other")

    @pytest.mark.asyncio
    async def test_m7_a_transaction_without_an_asset_comes_back_with_a_null_asset_id(self, split_file):
        """A linked row whose transaction has no asset comes back with ``transaction_asset_id=None``: callers decide.

        Yield on Cost's ``_load_split_records`` drops that row inside the loader today; the shared loader returns it,
        with the event's asset beside it, and the caller filters. Row 22, on the same split with an asset, comes back
        beside it. Before MF-I1: ModuleNotFoundError.
        """
        print_section("M7 — a transaction without an asset")
        splits = _splits()
        engine = await split_file(
            "no-asset.db",
            [_asset_event(31, A5, D_SPLIT, value="2")],
            [
                _transaction(21, ADJUSTMENT, D_SPLIT, B1, asset_id=None, quantity="10", asset_event_id=31),
                _transaction(22, ADJUSTMENT, D_SPLIT, B2, asset_id=A5, quantity="4", asset_event_id=31),
            ],
        )
        links, _statements = await _load(splits, engine, [22, 21])

        _assert_link_types(splits, links)
        expected = [
            _link(splits, 21, 31, transaction_asset_id=None, event_asset_id=A5, broker_id=B1, transaction_type=ADJUSTMENT, transaction_quantity="10", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="2"),
            _link(splits, 22, 31, transaction_asset_id=A5, event_asset_id=A5, broker_id=B2, transaction_type=ADJUSTMENT, transaction_quantity="4", transaction_date=D_SPLIT, event_date=D_SPLIT, ratio="2"),
        ]
        assert links == expected, f"the row without an asset, returned:\n{_shown(links)}"
        assert links[0].transaction_asset_id is None
        print_success("transaction_asset_id None returned beside the event's asset")


# =============================================================================
# MF-I2 — split_linked_ids on private SQLite files
# =============================================================================


class TestSplitLinkedIds:
    def test_i2_split_linked_ids_is_a_coroutine_function(self):
        """``split_linked_ids`` reads the database: a coroutine function, beside ``load_split_links``.

        Before MF-I2: AttributeError (``financial_math.splits`` has no ``split_linked_ids``).
        """
        print_section("I2 — split_linked_ids is a coroutine function")
        split_linked_ids = _split_linked_ids()
        assert inspect.iscoroutinefunction(split_linked_ids), "split_linked_ids reads the database: a coroutine function"
        print_success("a coroutine function of financial_math.splits")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("event_type", NON_SPLIT_EVENT_TYPES, ids=str)
    async def test_i2_the_ids_of_the_given_rows_linked_to_a_split_and_of_no_other(self, split_file, event_type):
        """Exactly the given rows linked to a SPLIT event, as a set of ids, in agreement with ``load_split_links``.

        Two splits: 2:1 of asset 5 (event 31, row 21 on broker 1 and row 25 on broker 2) and 1:2 of asset 7 (event 34,
        row 24). Row 22 differs from row 21 only by the type of its event (32); row 23 is a DIVIDEND realizing a DIVIDEND
        event (33); rows 11 and 12 are buys linked to nothing. Given all but row 25, in no particular order: {21, 24},
        read in one statement, the transaction ids of the links ``load_split_links`` returns for the same input. Given
        row 25 alone: {25} — the barrier that makes its absence above mean «not given», not «not linked».
        Before MF-I2: AttributeError.
        """
        print_section(f"I2 — split_linked_ids beside a row linked to a {event_type} event")
        split_linked_ids = _split_linked_ids()
        splits = _splits()
        engine = await split_file(
            "linked-ids.db",
            [
                _asset_event(31, A5, D_SPLIT, value="2"),
                _asset_event(32, A5, D_SPLIT, event_type=event_type, value="2"),
                _asset_event(33, A5, D_LATE, event_type=AssetEventType.DIVIDEND, value="0.35"),
                _asset_event(34, A7, D_REVERSE_SPLIT, value="0.5"),
            ],
            [
                _transaction(11, BUY, D_BUY, B1, asset_id=A5, quantity="10", amount="-1000", currency="EUR"),
                _transaction(12, BUY, D_BUY, B2, asset_id=A7, quantity="8", amount="-80", currency="EUR"),
                _transaction(21, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=31),
                _transaction(22, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=32),
                _transaction(23, DIVIDEND, D_LATE, B1, asset_id=A5, amount="7", currency="EUR", asset_event_id=33),
                _transaction(24, ADJUSTMENT, D_REVERSE_SPLIT, B2, asset_id=A7, quantity="-4", asset_event_id=34),
                _transaction(25, ADJUSTMENT, D_SPLIT, B2, asset_id=A5, quantity="10", asset_event_id=31),
            ],
        )
        given = [24, 11, 23, 22, 21, 12]
        ids, statements = await _load_ids(split_linked_ids, engine, given)
        links, _link_statements = await _load(splits, engine, given)
        alone, _alone_statements = await _load_ids(split_linked_ids, engine, [25])

        _assert_id_set(ids)
        assert ids == {21, 24}, f"given {given}: {sorted(ids)}"
        _assert_one_read(statements)
        assert ids == {link.transaction_id for link in links}, f"split_linked_ids {sorted(ids)} disagrees with load_split_links:\n{_shown(links)}"
        _assert_id_set(alone)
        assert alone == {25}, f"given row 25 alone: {sorted(alone)}"
        print_success(f"{{21, 24}}: not the unlinked rows, not the row linked to the {event_type} event, not the row not given")

    @pytest.mark.asyncio
    async def test_i2_without_a_candidate_an_empty_set_and_not_a_statement(self, split_file):
        """Nothing given, no row with an ``asset_event_id``, or a row that names the SPLIT event but was never written (no
        id): an empty ``set``, and not a single statement.

        The same rows then given with row 21, linked to the split, as a tuple: {21}, in one statement — the barrier that
        makes the silences above mean «nothing to ask» rather than «never asks»; the row without an id is still left out,
        and still has no id: it was not written to be read. Before MF-I2: AttributeError.
        """
        print_section("I2 — split_linked_ids without a candidate")
        split_linked_ids = _split_linked_ids()
        engine = await split_file(
            "no-candidate-ids.db",
            [_asset_event(31, A5, D_SPLIT, value="2")],
            [
                _transaction(11, BUY, D_BUY, B1, asset_id=A5, quantity="10", amount="-1000", currency="EUR"),
                _transaction(12, DEPOSIT, D_BUY, B1, asset_id=None, amount="5000", currency="EUR"),
                _transaction(21, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=31),
            ],
        )
        unsaved = _unsaved(31)
        silent: dict[str, list[int | Transaction]] = {
            "nothing given": [],
            "unlinked rows only": [11, 12],
            "an unsaved row only": [unsaved],
            "unlinked and unsaved rows": [11, unsaved, 12],
        }
        for name, given in silent.items():
            ids, statements = await _load_ids(split_linked_ids, engine, given)
            assert ids == set() and type(ids) is set, f"{name}: {ids!r}"
            assert statements == [], f"{name}: no candidate, yet split_linked_ids sent {statements}"
        mixed, mixed_statements = await _load_ids(split_linked_ids, engine, [unsaved, 21, 12, 11], container=tuple)

        _assert_id_set(mixed)
        assert mixed == {21}, f"the linked row among unlinked and unsaved ones: {sorted(mixed)}"
        _assert_one_read(mixed_statements)
        assert unsaved.id is None, "the unsaved row was written: split_linked_ids only reads"
        print_success(f"{len(silent)} inputs without a candidate: set() and no statement; with one, {{21}}")

    @pytest.mark.asyncio
    async def test_i2_no_ratio_is_judged(self, split_file):
        """A row linked to a SPLIT whose ratio is null, zero or negative is still returned: an average-cost replay rescales
        the pool by the row's own quantity, never by the ratio, so ``split_linked_ids`` refuses none of them.

        On the file whose schema admits a null ratio (checked to hold the NULL), events 31 (NULL), 32 (0), 33 (-1) and 34
        (2), one ADJUSTMENT each, beside an unlinked buy: {21, 22, 23, 24}, the ids of ``load_split_links``. The barrier is
        ``is_valid_split_ratio`` on those links: it refuses three of the four, so the set of four means «not judged»
        rather than «nothing to judge». Before MF-I2: AttributeError.
        """
        print_section("I2 — split_linked_ids judges no ratio")
        split_linked_ids = _split_linked_ids()
        splits = _splits()
        engine = await split_file(
            "unjudged-ratios.db",
            [
                _asset_event(31, A5, D_SPLIT, value=None),
                _asset_event(32, A5, D_SPLIT, value="0"),
                _asset_event(33, A5, D_LATE, value="-1"),
                _asset_event(34, A5, D_REVERSE_SPLIT, value="2"),
            ],
            [
                _transaction(11, BUY, D_BUY, B1, asset_id=A5, quantity="10", amount="-1000", currency="EUR"),
                _transaction(21, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=31),
                _transaction(22, ADJUSTMENT, D_SPLIT, B1, asset_id=A5, quantity="10", asset_event_id=32),
                _transaction(23, ADJUSTMENT, D_LATE, B1, asset_id=A5, quantity="10", asset_event_id=33),
                _transaction(24, ADJUSTMENT, D_REVERSE_SPLIT, B1, asset_id=A5, quantity="40", asset_event_id=34),
            ],
            null_ratio_allowed=True,
        )
        async with AsyncSession(engine) as session:
            stored = (await session.execute(select(AssetEvent.value).where(AssetEvent.id == 31))).scalar_one()
        assert stored is None, f"the file holds {stored!r} for event 31, not NULL: the schema did not admit a null ratio"

        given = [11, 24, 23, 22, 21]
        ids, statements = await _load_ids(split_linked_ids, engine, given)
        links, _link_statements = await _load(splits, engine, given)

        _assert_id_set(ids)
        assert ids == {21, 22, 23, 24}, f"every row linked to a SPLIT, whatever its ratio: {sorted(ids)}"
        _assert_one_read(statements)
        assert [(link.transaction_id, splits.is_valid_split_ratio(link.ratio)) for link in links] == [(21, False), (22, False), (23, False), (24, True)], f"the barrier: three of the four ratios are refused by the rule\n{_shown(links)}"
        assert ids == {link.transaction_id for link in links}, f"split_linked_ids {sorted(ids)} disagrees with load_split_links:\n{_shown(links)}"
        print_success("null, zero and negative ratios: still split-linked")
