"""
MF-W56 — the average cost the WAC facade hands out is rounded to the column it becomes (C-97, decision D6; agreed with
workstream W).

The defect. ``compute_wac_iterative`` (``portfolio_service.py``), the facade over ``financial_math.average_cost``,
returned ``WACPreviewResultItem.wac`` as ``average_cost.unit_cost_report`` computed it: for a pool whose average is a
periodic quotient — 3 units bought for 1000 EUR — ``333.3333333333333333333333333``, 25 decimals. That value leaves the
calculation and becomes an INPUT: the preview of ``POST /transactions/validate`` (``wac_results``), which the Form
shows and the user freezes into a manual cost basis, refused by C-97a's input limit (decision D2: a value the user
sends is refused, never rounded); and the Auto cost, which ``_write_auto_cost`` (``transactions/auto_cost.py``) writes
on ``Transaction.cost_basis_override`` as it is.

The cure (D6). The facade rounds the average it returns with ``round_computed_value(value, Transaction,
"cost_basis_override")`` (``db/precision.py``): ``ROUND_HALF_EVEN`` to the column's 12 decimals and its 15 significant
digits, a value that already fits coming back as it is, its form included (``100.00`` stays ``100.00``). Never in
``financial_math.average_cost``, which stays exact: the house computes exactly, and rounds where a value leaves it.

What is read, and why never from the database (W's warning). ``cost_basis_override`` is a ``RealDecimal(24, 12)``: it
reads the stored double back at 15 significant digits and 12 decimals, so 1000 / 3 reads ``333.333333333333`` with or
without the cure — a read-back is green on the defect (W pins that read-back in ``test_transaction_decimal_places.py``,
``AUTO_COST_OF_HUNDRED_OVER_THREE``). Every value here is read BEFORE it is stored: the ``WACPreviewResultItem`` the
facade returns, the batch's ``wac_results``, and the ORM attribute ``_write_auto_cost`` has just assigned (recorded by
a spy that calls the real method, before any flush or expiry). The exact average the facade rounds is likewise read on
its way through, from the facade's own ``compute_average_costs`` (a spy that runs the real function), so the parity
guard compares with the very value the facade received, whatever form the rows were loaded in.

Reds — fail on HEAD ``ca2f00c35`` (facade unrounded), pass with the cure:

- ``TestTheFacadeRoundsAPeriodicAverage``: four pools of 3 units — 100, 1000, 200 (the half-even step rounds up) and
  1000000 EUR (the 15 significant digits bind: ``333333.333333333``) — whose exact average financial_math hands the
  facade unrounded (pinned: the rounding is the facade's, not ``average_cost``'s); the ``wac`` returned has no
  ``decimal_limit_issue`` on ``cost_basis_override`` and equals ``round_computed_value`` of the exact quotient. On HEAD
  it IS the exact quotient: ``decimalPlacesExceeded`` ``{"max": 12}``.
- ``TestTheBatchWritesARoundedAutoCost``: an ADJUSTMENT +1 created, or a stored one updated, in ``auto`` or
  ``auto-detail`` on top of a periodic pool (100 / 3, 1000000 / 3), through ``/validate`` as the endpoint runs it: the
  ``wac_results`` item of that row and the ``cost_basis_override`` ``_write_auto_cost`` assigned are the rounded
  average, in EUR. On HEAD both are the exact quotient.
- ``TestTheFrozenPreviewIsAccepted``: the preview's average, as ``/validate`` serializes it in ``wac_results`` (what the
  Form receives), frozen into a ``manual`` cost basis of a new ADJUSTMENT +1 passes ``decimal_limit_issue`` and the
  second ``/validate`` accepts it with no issue at all. On HEAD the frozen amount has 22 to 26 decimals and the batch
  refuses it on its row, ``decimalPlacesExceeded`` ``{"max": 12}`` (D2).

Guards — green on HEAD and with the cure:

- ``TestTheFacadeKeepsAnExactAverage``: pools whose average is exact — 200.00 EUR for 2 units, 5 for 2, 1 for 8 — come
  back from the facade in the very form financial_math computed (``str`` equal, so ``100.00`` is not turned into
  ``100.000000000000``) and equal in value to 100, 2.5 and 0.125. A cure that quantizes every value turns it red.

Not covered here: ``POST /portfolio/wac`` charts ``wac_qualifying_txs[].running_wac``, which the cure leaves exact (it
rounds ``wac`` only); whether that series should be rounded too is not decided.

Ownership. Every test builds its own asset and broker under a unique marker, writes its rows with the ORM in one
session that is flushed and never committed, and runs each batch inside a savepoint it rolls back, as ``/validate``
does; the session fixture rolls everything back. EUR only: no conversion, no FX row, no network. The facade is called
with ``use_cache=False``; the batch path cannot pass it, so ``_wac_cache`` is cleared before each test (the keys hold
this test's own never-reused ids, so this only removes what could not be hit anyway).

Run: ``./dev.py test services roi-fifo-utils`` (the action runs ``test_financial/`` whole); this file alone:
``./dev.py test services roi-fifo-utils test_wac_rounded_to_column`` (the extra argument becomes pytest's ``-k``).
"""

import sys
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Before any app module that reads DATABASE_URL: this lane's test database.
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.base import NO_VALUE

import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetType, Broker, Transaction, TransactionType
from backend.app.db.precision import decimal_limit_issue, round_computed_value
from backend.app.db.session import get_async_engine
from backend.app.schemas.transactions.batch import TXBatchResponse, TXValidationIssue
from backend.app.schemas.wac import WACPreviewResultItem
from backend.app.services.portfolio_service import compute_wac_iterative
from backend.app.services.transactions.auto_cost import TransactionAutoCostMixin
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow

EUR = "EUR"
# The pool is bought before the day the subject row lands on; the facade averages up to that day.
SEED_DAY = date(2025, 3, 3)
DAY = date(2025, 3, 10)
# The column every average here becomes: a per-unit cost basis, RealDecimal(24, 12).
COST_COLUMN = (Transaction, "cost_basis_override")
# The codes of C-97's input limit (db/precision.decimal_limit_issue), as the batch reports them.
LIMIT_CODES = ("decimalPlacesExceeded", "significantDigitsExceeded", "integerDigitsExceeded")
AUTO_MODES = ("auto", "auto-detail")
# The amount an Auto row carries: in the limit, and not any pool's average, so a written cost of 1 would mean the
# amount sent was kept instead of the average computed.
AUTO_AMOUNT_SENT = "1"


@dataclass(frozen=True)
class Pool:
    """A BUY of ``quantity`` units on the test's broker for ``cost`` EUR, and its average as the column keeps it
    (``column_value``): the expected value, in the form the facade must return."""

    cost: str
    quantity: str
    column_value: str

    @property
    def exact(self) -> Decimal:
        """The pool's average as an exact quotient, at the default context's 28 significant digits."""
        return Decimal(self.cost) / Decimal(self.quantity)


# Periodic averages: past the column's 12 decimals as computed. 200 / 3 rounds up (half-even, never a cut); for
# 1000000 / 3 the 15 significant digits bind before the 12 decimals do.
HUNDRED_OVER_THREE = Pool(cost="100", quantity="3", column_value="33.333333333333")
THOUSAND_OVER_THREE = Pool(cost="1000", quantity="3", column_value="333.333333333333")
TWO_HUNDRED_OVER_THREE = Pool(cost="200", quantity="3", column_value="66.666666666667")
MILLION_OVER_THREE = Pool(cost="1000000", quantity="3", column_value="333333.333333333")
PERIODIC_POOLS = [
    pytest.param(HUNDRED_OVER_THREE, id="100-over-3"),
    pytest.param(THOUSAND_OVER_THREE, id="1000-over-3"),
    pytest.param(TWO_HUNDRED_OVER_THREE, id="200-over-3-rounds-up"),
    pytest.param(MILLION_OVER_THREE, id="1000000-over-3-15-significant-digits"),
]
# The batch path on two of them: W's own 100 / 3, and the one where the significant digits bind.
BATCH_POOLS = [
    pytest.param(HUNDRED_OVER_THREE, id="100-over-3"),
    pytest.param(MILLION_OVER_THREE, id="1000000-over-3-15-significant-digits"),
]
# Exact averages, already within the column: the facade must return them untouched, form included.
EXACT_POOLS = [
    pytest.param(Pool(cost="200.00", quantity="2", column_value="100.00"), id="200.00-over-2-is-100.00"),
    pytest.param(Pool(cost="5", quantity="2", column_value="2.5"), id="5-over-2-is-2.5"),
    pytest.param(Pool(cost="1", quantity="8", column_value="0.125"), id="1-over-8-is-0.125"),
]


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def engine():
    """The app's async engine, on this lane's test database."""
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    """One session per test, rolled back at the end: nothing a test writes reaches the lane's database."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
def _fresh_wac_cache():
    """No average served from the facade's cache: the batch path calls it with ``use_cache=True``."""
    portfolio_service_module._wac_cache.clear()
    yield


@dataclass(frozen=True)
class World:
    """One test's own ground, by id: an EUR asset and the broker its pool and subject rows sit on. The broker may
    overdraw its cash (the BUY spends cash no DEPOSIT brought) and may not go short, as a broker does by default."""

    session: AsyncSession
    marker: str
    asset_id: int
    broker_id: int

    @property
    def batch_description(self) -> str:
        """The description of every row a batch of this test sends."""
        return f"{self.marker} batch"


@pytest_asyncio.fixture
async def world(session) -> World:
    """The test's asset and broker, under a marker of its own."""
    marker = f"MF-W56 wac {uuid.uuid4().hex}"
    now = utcnow()
    asset = Asset(display_name=f"{marker} asset", asset_type=AssetType.STOCK, currency=EUR, created_at=now, updated_at=now)
    broker = Broker(name=f"{marker} broker", description="MF-W56: the broker the pool sits on", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    session.add_all([asset, broker])
    await session.flush()
    return World(session=session, marker=marker, asset_id=asset.id, broker_id=broker.id)


@pytest.fixture
def averages_handed_to_the_facade(monkeypatch) -> list[Decimal]:
    """The averages ``financial_math.average_cost`` hands the facade, before the facade does anything with them: the
    real ``compute_average_costs`` runs, and each position's ``unit_cost_report`` is recorded on its way through."""
    seen: list[Decimal] = []
    real = portfolio_service_module.compute_average_costs

    async def recording(*args: Any, **kwargs: Any):
        averages = await real(*args, **kwargs)
        seen.extend(average.unit_cost_report for average in averages.values())
        return averages

    monkeypatch.setattr(portfolio_service_module, "compute_average_costs", recording)
    return seen


@dataclass(frozen=True)
class WrittenAutoCost:
    """What ``_write_auto_cost`` left on a row, read off the ORM object the moment it returned: before any flush sends
    it to the REAL and before any expiry could make a read reload it from there."""

    tx_id: Any
    amount: Any
    currency: Any


@pytest.fixture
def auto_costs_written(monkeypatch) -> list[WrittenAutoCost]:
    """Every Auto cost the batch writes, recorded right after the real ``_write_auto_cost`` assigned it. The attributes
    are read from the object's loaded state (``loaded_value``), so the recording never triggers a load: an attribute
    that is not in memory is recorded as ``NO_VALUE``."""
    written: list[WrittenAutoCost] = []
    real = TransactionAutoCostMixin._write_auto_cost

    def recording(db_tx: Transaction, wac_result: WACPreviewResultItem) -> None:
        real(db_tx, wac_result)
        attrs = inspect(db_tx).attrs
        written.append(WrittenAutoCost(tx_id=attrs.id.loaded_value, amount=attrs.cost_basis_override.loaded_value, currency=attrs.cost_basis_currency.loaded_value))

    monkeypatch.setattr(TransactionAutoCostMixin, "_write_auto_cost", staticmethod(recording))
    return written


# ============================================================================
# HELPERS
# ============================================================================


async def _insert(world: World, **columns) -> int:
    """A row written with the ORM, without the batch and its checks; its id."""
    now = utcnow()
    row = Transaction(broker_id=world.broker_id, asset_id=world.asset_id, description=f"{world.marker} seed", created_at=now, updated_at=now, **columns)
    world.session.add(row)
    await world.session.flush()
    return row.id


async def _seed_pool(world: World, pool: Pool) -> int:
    """The pool every average here is taken on: a BUY of ``pool.quantity`` units for ``pool.cost`` EUR, before ``DAY``."""
    return await _insert(world, type=TransactionType.BUY, date=SEED_DAY, quantity=Decimal(pool.quantity), amount=-Decimal(pool.cost), currency=EUR)


async def _seed_adjustment_in(world: World) -> int:
    """A stored ADJUSTMENT +1 on ``DAY`` at a manual cost of 100 EUR: the row an update turns to Auto. Its own Auto cost
    averages its broker without itself (``_auto_cost_source``), so the pool alone."""
    return await _insert(world, type=TransactionType.ADJUSTMENT, date=DAY, quantity=Decimal("1"), amount=Decimal("0"), currency=None, cost_basis_override=Decimal("100"), cost_basis_currency=EUR)


def _adjustment_in(world: World, mode: str, cost: dict) -> dict:
    """A create of an ADJUSTMENT +1 on ``DAY`` with ``cost_basis_mode`` ``mode`` and the cost basis ``cost``
    (``{"code", "amount"}``), as the app sends it."""
    return {
        "broker_id": world.broker_id,
        "asset_id": world.asset_id,
        "type": "ADJUSTMENT",
        "date": DAY.isoformat(),
        "quantity": "1",
        "description": world.batch_description,
        "cost_basis_mode": mode,
        "cost_basis_override": cost,
    }


async def _preview(world: World) -> WACPreviewResultItem:
    """The facade's average of the test's position up to ``DAY``, as the preview and the Auto cost ask it, uncached."""
    return await compute_wac_iterative(world.session, broker_id=world.broker_id, asset_id=world.asset_id, as_of_date=DAY, asset_currency=EUR, use_cache=False)


async def _validate(world: World, *, creates: Optional[list[dict]] = None, updates: Optional[list[dict]] = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/validate`` runs it: inside a transaction that is always rolled back
    (``api/v1/transactions.py``); no user, so no access check. A savepoint stands in for the request's transaction: the
    rows written before it survive its rollback, and the session fixture still rolls everything back."""
    savepoint = await world.session.begin_nested()
    try:
        return await TransactionService(world.session).execute_batch(creates_raw=creates or [], updates_raw=updates or [], deletes=[], commit=False)
    finally:
        await savepoint.rollback()


def _render(issues: list[TXValidationIssue]) -> str:
    """The issues, for a failure message."""
    return "; ".join(f"{issue.operation}[{issue.index}] ref_id={issue.ref_id} code={issue.code} field={issue.field} params={issue.params} error={issue.error!r}" for issue in issues) or "none"


def _limit_issues(response: TXBatchResponse) -> list[tuple]:
    """The batch's refusals over a column's limit, as ``(operation, index, code, field, params)``."""
    return [(issue.operation, issue.index, issue.code, issue.field, issue.params) for issue in response.issues if issue.code in LIMIT_CODES]


def _wac_result_of(response: TXBatchResponse, operation: str, index: int) -> WACPreviewResultItem:
    """The ``wac_results`` item of the row ``(operation, index)``: there must be exactly one."""
    items = [item for item in response.wac_results or [] if item.operation == operation and item.index == index]
    assert len(items) == 1, f"scaffold: the batch must answer one wac_results item for {operation}[{index}], an Auto row; it answered {response.wac_results}"
    return items[0]


def _created_id(response: TXBatchResponse, index: int) -> int:
    """The id the create at ``index`` got."""
    ids = [result.ids[0] for result in response.results if result.operation == "create" and result.index == index and result.ids]
    assert len(ids) == 1, f"scaffold: the batch must report the id of create {index}; its results are {response.results}"
    return ids[0]


# ============================================================================
# RED — THE FACADE ROUNDS A PERIODIC AVERAGE
# ============================================================================


class TestTheFacadeRoundsAPeriodicAverage:
    """RED (MF-W56, D6): the average ``compute_wac_iterative`` returns fits the column it becomes, rounded by
    ``round_computed_value``, while ``financial_math.average_cost`` keeps the exact quotient."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("pool", PERIODIC_POOLS)
    async def test_a_periodic_average_comes_back_rounded_to_the_column(self, world, averages_handed_to_the_facade, pool):
        """RED: 3 units bought for ``pool.cost`` EUR — the facade's ``wac`` has no ``decimal_limit_issue`` on
        ``cost_basis_override`` and is ``round_computed_value`` of the exact quotient, ``pool.column_value`` EUR.

        Red on HEAD: the facade returns the exact quotient (22 to 26 decimals), refused with ``decimalPlacesExceeded``
        ``{"max": 12}``.
        """
        await _seed_pool(world, pool)

        preview = await _preview(world)

        handed, exact = averages_handed_to_the_facade, [pool.exact]
        assert handed == exact, f"D6: financial_math.average_cost stays exact and the rounding is the facade's, so the average it hands the facade for {pool.quantity} units bought for {pool.cost} EUR must be the exact quotient {pool.exact}; it handed {handed}"
        assert decimal_limit_issue(pool.exact, *COST_COLUMN) is not None, f"scaffold: the exact average {pool.exact} must be over the column's limit, or this pool proves nothing"
        expected = round_computed_value(pool.exact, *COST_COLUMN)
        assert expected == Decimal(pool.column_value), f"scaffold: round_computed_value({pool.exact}) on cost_basis_override must be {pool.column_value}, the oracle this test was written against; it is {expected}"
        assert preview.wac is not None and preview.wac.code == EUR, f"scaffold: an EUR pool has an average in EUR, with no conversion to miss; the facade answered wac={preview.wac}, missing pairs {preview.wac_missing_pairs}"
        issue = decimal_limit_issue(preview.wac.amount, *COST_COLUMN)
        assert issue is None, f"MF-W56 (D6): the average the facade returns becomes a cost basis — frozen by the user, written as the Auto cost — so it must fit cost_basis_override; {preview.wac.amount} EUR gets {issue}"
        assert preview.wac.amount == expected and str(preview.wac.amount) == str(expected), f"MF-W56 (D6): the facade must return round_computed_value of the exact average, {expected} EUR; it returned {preview.wac.amount} EUR"


# ============================================================================
# GUARD — THE FACADE KEEPS AN EXACT AVERAGE, FORM INCLUDED
# ============================================================================


class TestTheFacadeKeepsAnExactAverage:
    """GUARD (MF-W56, D6): an average that already fits the column comes back as financial_math computed it."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("pool", EXACT_POOLS)
    async def test_an_exact_average_keeps_its_form(self, world, averages_handed_to_the_facade, pool):
        """GUARD: ``pool.quantity`` units bought for ``pool.cost`` EUR — the facade's ``wac`` is, character for
        character, the average financial_math handed it, ``pool.column_value`` in value.

        Green on HEAD (nothing is rounded) and with the cure (``round_computed_value`` returns a value that fits as it
        is). A cure that quantizes every average to 12 decimals (``100.000000000000``) turns it red.
        """
        await _seed_pool(world, pool)

        preview = await _preview(world)

        assert len(averages_handed_to_the_facade) == 1, f"scaffold: the facade must compute one position's average through compute_average_costs; it handed {averages_handed_to_the_facade}"
        exact = averages_handed_to_the_facade[0]
        assert exact == Decimal(pool.column_value), f"scaffold: {pool.quantity} units bought for {pool.cost} EUR average exactly {pool.column_value} EUR; financial_math handed {exact}"
        assert decimal_limit_issue(exact, *COST_COLUMN) is None, f"scaffold: the exact average {exact} must already fit cost_basis_override, or this is not the guard's case"
        assert preview.wac is not None and preview.wac.code == EUR, f"scaffold: an EUR pool has an average in EUR; the facade answered wac={preview.wac}, missing pairs {preview.wac_missing_pairs}"
        assert str(preview.wac.amount) == str(exact), f"MF-W56 (D6): an average that already fits the column comes back as computed, its form included; financial_math handed {exact!s}, the facade returned {preview.wac.amount!s}"


# ============================================================================
# RED — THE BATCH WRITES A ROUNDED AUTO COST
# ============================================================================


class TestTheBatchWritesARoundedAutoCost:
    """RED (MF-W56, D6): the Auto cost of a batch row — the facade's average — is rounded before it is stored, in the
    ``wac_results`` the batch answers and on the row ``_write_auto_cost`` writes it to."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", AUTO_MODES)
    @pytest.mark.parametrize("operation", ("create", "update"))
    @pytest.mark.parametrize("pool", BATCH_POOLS)
    async def test_the_auto_cost_is_rounded_before_it_is_stored(self, world, auto_costs_written, pool, operation, mode):
        """RED: an ADJUSTMENT +1 created, or a stored one updated, in ``mode`` on top of 3 units bought for
        ``pool.cost`` EUR, through ``/validate``: its ``wac_results`` item and the ``cost_basis_override``
        ``_write_auto_cost`` assigned on its row are ``round_computed_value`` of the pool's average, in EUR, with no
        ``decimal_limit_issue``.

        Red on HEAD: both are the exact quotient. Never read back from the database: the REAL reads 12 decimals with or
        without the cure (W's ``AUTO_COST_OF_HUNDRED_OVER_THREE``).
        """
        await _seed_pool(world, pool)
        cost_sent = {"code": EUR, "amount": AUTO_AMOUNT_SENT}
        if operation == "create":
            response = await _validate(world, creates=[_adjustment_in(world, mode, cost_sent)])
        else:
            stored_id = await _seed_adjustment_in(world)
            response = await _validate(world, updates=[{"id": stored_id, "cost_basis_mode": mode, "cost_basis_override": cost_sent}])

        assert response.issues == [], f"scaffold: the {mode} {operation} of an ADJUSTMENT +1 must validate with no issue; the batch answered: {_render(response.issues)}"
        subject_id = _created_id(response, 0) if operation == "create" else stored_id
        expected = round_computed_value(pool.exact, *COST_COLUMN)
        answered = _wac_result_of(response, operation, 0).wac
        assert answered is not None and answered.code == EUR, f"scaffold: an EUR pool has an Auto cost in EUR; the batch answered {answered}"
        answered_issue = decimal_limit_issue(answered.amount, *COST_COLUMN)
        got, wanted = (answered.amount, answered_issue), (expected, None)
        assert got == wanted, f"MF-W56 (D6): the {mode} cost the batch answers for {operation}[0] (wac_results) must be the pool's average rounded to cost_basis_override, {expected} EUR; it answered {answered.amount} EUR ({answered_issue or 'within the limit'})"

        mine = [record for record in auto_costs_written if record.tx_id == subject_id]
        assert len(mine) == 1, f"scaffold: _write_auto_cost must write the Auto cost on row id={subject_id} once; it wrote {auto_costs_written}"
        written = mine[0]
        assert written.amount is not NO_VALUE and written.currency is not NO_VALUE, f"scaffold: the cost written on row id={subject_id} must be read from memory, before it is stored; the attribute was not loaded: {written}"
        written_issue = decimal_limit_issue(written.amount, *COST_COLUMN)
        got, wanted = (written.amount, written.currency, written_issue), (expected, EUR, None)
        assert got == wanted, f"MF-W56 (D6): the {mode} cost written on the {operation}d ADJUSTMENT id={subject_id} must be the pool's average rounded to its column, {expected} EUR, not the {AUTO_AMOUNT_SENT} EUR sent; it is {written.amount} {written.currency} ({written_issue or 'in the limit'})"


# ============================================================================
# RED — THE FROZEN PREVIEW IS ACCEPTED AS A MANUAL COST
# ============================================================================


class TestTheFrozenPreviewIsAccepted:
    """RED (MF-W56, D2 + D6): the average the preview shows can be frozen into a manual cost basis as it is."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("pool", PERIODIC_POOLS)
    async def test_the_previews_average_frozen_into_a_manual_cost_is_accepted(self, world, pool):
        """RED: the Form's preview — ``/validate`` of an Auto ADJUSTMENT +1 on top of 3 units bought for ``pool.cost``
        EUR, its ``wac_results`` serialized as the Form receives them — frozen into the ``manual`` cost basis of a new
        ADJUSTMENT +1: the amount passes ``decimal_limit_issue``, and the second ``/validate`` answers no issue at all.

        Red on HEAD: the preview serializes the exact quotient, and the manual cost basis is refused on its row with
        ``decimalPlacesExceeded`` ``{"max": 12}`` — a value of the user's is refused, never rounded (D2).
        """
        await _seed_pool(world, pool)
        preview = await _validate(world, creates=[_adjustment_in(world, "auto", {"code": EUR, "amount": AUTO_AMOUNT_SENT})])
        assert preview.issues == [], f"scaffold: the Auto preview must validate with no issue; the batch answered: {_render(preview.issues)}"
        frozen = _wac_result_of(preview, "create", 0).model_dump(mode="json")["wac"]  # as the Form receives it
        assert frozen is not None and frozen["code"] == EUR, f"scaffold: an EUR pool has a preview in EUR; the batch answered {frozen}"

        frozen_issue = decimal_limit_issue(Decimal(frozen["amount"]), *COST_COLUMN)
        assert frozen_issue is None, f"MF-W56 (D6): the preview's average, {frozen['amount']} EUR as /validate serializes it, is what the user freezes into a manual cost basis; it must fit cost_basis_override, it gets {frozen_issue}"
        response = await _validate(world, creates=[_adjustment_in(world, "manual", frozen)])
        assert _limit_issues(response) == [], f"MF-W56 (D2 + D6): a manual cost basis equal to the preview's average, {frozen['amount']} EUR, must be accepted; the batch refused it: {_render(response.issues)}"
        assert response.issues == [], f"MF-W56: nothing else may refuse the frozen ADJUSTMENT +1: {_render(response.issues)}"
