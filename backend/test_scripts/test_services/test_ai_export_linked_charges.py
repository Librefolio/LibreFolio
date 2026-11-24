"""Project 66, M3 — AI Export reads the linked charges through the lots, with no code of its own (GUARD).

M3 changes no production code: these tests pin what M1, M1b and M2 already delivered, as the AI Export sees it. They
are green from the start; a red here is a behaviour change, not a test to adjust.

AI Export reads three things of a ``LotsAnalysisResponse``: ``calculation_status``, ``failure_codes`` (the issues with
``fails_analysis``) and each lot's ``allocated_fees`` / ``allocated_taxes``. A linked charge reaches its lots through
those figures alone (``asset.lot_detail``; ``portfolio.fifo_lots`` and ``broker.fifo_lots`` through
``map_fifo_lot_row``). A charge the lots cannot hold — waiting for a parent after the end (M1b,
``ASSET_COST_LINKED_PARENT_AFTER_RANGE``) or orphan with its income (M2, ``ASSET_COST_LINKED_INCOME_NO_ELIGIBLE_LOTS``),
both WARNINGs — makes the reconstruction DEGRADED, never FAILED, and appears in no lot. It is still among the period's
fees of the position (``asset.performance``, ``period_fees_taxes``): the difference between those period fees and the
lots' fees and taxes is exactly the orphan charge, the gap the contract leaves to the backlog (M3 contract §2.1).

Why a file of its own. ``test_ai_export_components_asset.py`` and ``test_ai_export_components_portfolio_broker_financial.py``
monkeypatch ``LotsAnalysisService.get_lots_analysis`` on a tableless session: a mocked lot with fees 2 and 19 proves
nothing about the link. Here, as in ``test_ai_export_fifo_failed_reconstruction.py``, the real components run on the
real lots analysis and the real portfolio report, over rows of this test's own (``_scope_boundary_books`` helpers, uuid4
names) written into the session and rolled back. EUR only, dates in February 2025, period 1–14 Feb.

THE BOOKS (one broker A of a new user, one asset with its own quotes, 100 EUR on 3 and 10 Feb):
- LINKED: on 3 Feb A buys 10 for 1 000 EUR and 90 for 9 000 EUR, with a FEE of 2 EUR and one of 19 EUR, each linked to
  its BUY → the lots carry 2 and 19. The same-day ladder (the control: both FEEs unlinked) splits the 21 EUR by amount,
  2.10 and 18.90.
- WAITING (M1b): lot A, 10 for 1 000 EUR on 3 Feb with its linked FEE of 2 EUR; a FEE of 5 EUR on 12 Feb linked to a BUY
  of 20 Feb, after the end.
- ORPHAN WITH ITS INCOME (M2): lot C, 5 for 500 EUR on 10 Feb with its linked FEE of 2 EUR; a DIVIDEND of 10 Feb, which
  no lot earned (nothing is held on 9 Feb); a FEE of 1 EUR on 12 Feb linked to it. With a DIVIDEND of 50 EUR the dividend
  is orphan too (ASSET_INCOME_NO_ELIGIBLE_LOTS); with one of 0 (M2b, the service drops it and hands the engine its facts)
  the linked charge's own code is the only one.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Broker, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.services.ai_export.components.asset_resources import ASSET_LOTS_RESOURCE
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.types import BrokerScopeSource, BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.test_scripts.test_services._scope_boundary_books import add_prices, asset_row, new_asset, new_broker, new_user

D = Decimal
PERIOD_START = date(2025, 2, 1)
PERIOD_END = date(2025, 2, 14)
BUY_DAY = date(2025, 2, 3)
INCOME_DAY = date(2025, 2, 10)
CHARGE_DAY = date(2025, 2, 12)
PARENT_AFTER_END = date(2025, 2, 20)
PRICES = {BUY_DAY: "100", INCOME_DAY: "100"}
AFTER_RANGE = "ASSET_COST_LINKED_PARENT_AFTER_RANGE"
INCOME_ORPHAN_LINKED = "ASSET_COST_LINKED_INCOME_NO_ELIGIBLE_LOTS"
MULTI_ASSET_DOMAINS = ["broker", "portfolio"]


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


@dataclass(frozen=True)
class Book:
    owner: User
    broker: Broker
    asset: Asset


async def _book(session: AsyncSession, label: str) -> Book:
    owner = await new_user(session, f"m3_{label}")
    broker = await new_broker(session, f"M3 {label}", owner)
    asset = await new_asset(session, f"M3 {label}")
    add_prices(session, asset, PRICES)
    await session.flush()
    return Book(owner, broker, asset)


def _fee(book: Book, day: date, amount: str, parent: Transaction | None) -> Transaction:
    """A FEE of the book's asset, linked to ``parent`` when given (its id must exist: flush the parent first)."""
    row = asset_row(book.broker, book.asset, TransactionType.FEE, day, "0", amount=amount)
    row.parent_transaction_id = None if parent is None else parent.id
    return row


async def seed_linked(session: AsyncSession, *, linked: bool = True) -> Book:
    """LINKED: two BUYs of 3 Feb, 1 000 and 9 000 EUR, with FEEs of 2 and 19 EUR — each linked to its BUY, or neither."""
    book = await _book(session, "linked")
    small = asset_row(book.broker, book.asset, TransactionType.BUY, BUY_DAY, "10", amount="-1000")
    large = asset_row(book.broker, book.asset, TransactionType.BUY, BUY_DAY, "90", amount="-9000")
    session.add_all([small, large])
    await session.flush()
    session.add_all([_fee(book, BUY_DAY, "-2", small if linked else None), _fee(book, BUY_DAY, "-19", large if linked else None)])
    await session.flush()
    return book


@dataclass(frozen=True)
class OrphanBook:
    book: Book
    orphan_fee: Transaction  # the linked charge the lots cannot hold
    orphan_amount: Decimal
    lot_quantity: Decimal  # the one lot exported, which carries its own linked FEE of 2 EUR
    expected_code: str
    expected_key: str  # the catalogue key the frontend renders (lotDataQualityHelpers.test.ts, ORPHAN_KEY)


async def seed_waiting(session: AsyncSession) -> OrphanBook:
    """WAITING (M1b): lot A with its linked FEE of 2 EUR; a FEE of 5 EUR on 12 Feb linked to a BUY of 20 Feb."""
    book = await _book(session, "waiting")
    lot_a = asset_row(book.broker, book.asset, TransactionType.BUY, BUY_DAY, "10", amount="-1000")
    after_end = asset_row(book.broker, book.asset, TransactionType.BUY, PARENT_AFTER_END, "10", amount="-1000")
    session.add_all([lot_a, after_end])
    await session.flush()
    waiting = _fee(book, CHARGE_DAY, "-5", after_end)
    session.add_all([_fee(book, BUY_DAY, "-2", lot_a), waiting])
    await session.flush()
    return OrphanBook(book, waiting, D("5"), D("10"), AFTER_RANGE, "dataQuality.assetCostLinkedParentAfterRange")


async def seed_orphan_with_its_income(session: AsyncSession, *, dividend: str) -> OrphanBook:
    """ORPHAN WITH ITS INCOME (M2): lot C of 10 Feb with its linked FEE of 2 EUR; a DIVIDEND of 10 Feb no lot earned; a
    FEE of 1 EUR on 12 Feb linked to it."""
    book = await _book(session, f"orphan_income_{dividend}")
    lot_c = asset_row(book.broker, book.asset, TransactionType.BUY, INCOME_DAY, "5", amount="-500")
    income = asset_row(book.broker, book.asset, TransactionType.DIVIDEND, INCOME_DAY, "0", amount=dividend)
    session.add_all([lot_c, income])
    await session.flush()
    orphan = _fee(book, CHARGE_DAY, "-1", income)
    session.add_all([_fee(book, INCOME_DAY, "-2", lot_c), orphan])
    await session.flush()
    return OrphanBook(book, orphan, D("1"), D("5"), INCOME_ORPHAN_LINKED, "dataQuality.assetCostLinkedIncomeNoEligibleLots")


def _scope(book: Book, domain: str) -> BuildScope:
    common = {"request_id": f"m3-{domain}-{uuid4().hex}", "user_id": book.owner.id, "detail_level": DetailLevel.STANDARD, "period_start": PERIOD_START, "period_end": PERIOD_END, "target_currency": "EUR"}
    if domain == "broker":
        return BuildScope(domain=Domain.BROKER, broker_id=book.broker.id, broker_scope=(book.broker.id,), **common)
    # 78 L10b: no broker list means the owned brokers; the book's owner owns its broker (an empty scope means no broker).
    owned = {"broker_scope": (book.broker.id,), "broker_scope_source": BrokerScopeSource.OWNED, "owned_broker_ids": (book.broker.id,)}
    if domain == "asset":
        return BuildScope(domain=Domain.ASSET, asset_id=book.asset.id, **owned, **common)
    return BuildScope(domain=Domain.PORTFOLIO, **owned, **common)


def _context(session: AsyncSession, scope: BuildScope) -> BuildContext:
    return BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)


def _loaded_by_the_component(_session: AsyncSession):
    raise AssertionError("the component should have loaded its lots: the resource is memoized per request")


def _amount(value: object) -> Decimal | None:
    """A payload amount as a Decimal: a bare decimal (``asset.*``) or a ``{code, amount}`` money (``*.fifo_lots``)."""
    if value is None:
        return None
    if isinstance(value, dict):
        assert value["code"] == "EUR", value
        value = value["amount"]
    return D(str(value))


def _fees_by_quantity(rows: list[dict], fee_field: str) -> dict[Decimal, Decimal | None]:
    """Each lot's fees by its original quantity: both LINKED lots share day and broker, so their quantity tells them apart."""
    by_quantity = {D(str(row["original_quantity"])): _amount(row[fee_field]) for row in rows}
    assert len(by_quantity) == len(rows), f"one lot per quantity: {rows}"
    return by_quantity


# --------------------------------------------------------------------------- #
# Guard 1 — a linked FEE reaches its own lot: 2 and 19, never the ladder's 2.10 and 18.90
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("linked", "expected"),
    [
        pytest.param(True, {D("10"): D("2"), D("90"): D("19")}, id="linked-each-fee-on-its-buy"),
        pytest.param(False, {D("10"): D("2.10"), D("90"): D("18.90")}, id="control-unlinked-same-day-ladder"),
    ],
)
async def test_lot_detail_exports_each_linked_fee_on_the_lot_its_buy_opened(session, linked, expected):
    """``asset.lot_detail``: the lot of 10 carries the 2 EUR FEE linked to its BUY, the lot of 90 the 19 EUR one, and the
    reconstruction is COMPLETE. The control (both FEEs unlinked) shows the numbers tell the link from the ladder: the
    same-day ladder splits 21 EUR by amount, 2.10 and 18.90."""
    book = await seed_linked(session, linked=linked)
    context = _context(session, _scope(book, "asset"))

    payload = (await context.resolve("asset.lot_detail", required=True)).payload

    assert (payload["lot_reconstruction_status"], payload["failure_codes"]) == ("COMPLETE", [])
    assert _fees_by_quantity(payload["lots"], "allocated_fees") == expected
    assert {_amount(row["allocated_taxes"]) for row in payload["lots"]} == {D("0")}


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", MULTI_ASSET_DOMAINS)
async def test_fifo_lots_export_each_linked_fee_on_the_lot_its_buy_opened(session, domain):
    """``{domain}.fifo_lots``: the same two lots, by ``map_fifo_lot_row``, with fees 2 and 19 EUR on the lots of 10 and 90."""
    book = await seed_linked(session)

    payload = (await _context(session, _scope(book, domain)).resolve(f"{domain}.fifo_lots", required=True)).payload

    rows = [row for row in payload["lots"] if row["asset_id"] == book.asset.id]
    assert _fees_by_quantity(rows, "fees") == {D("10"): D("2"), D("90"): D("19")}
    assert payload["failed_reconstruction_asset_count"] == 0


# --------------------------------------------------------------------------- #
# Guard 2 — a linked charge the lots cannot hold: DEGRADED, no failure code, in no lot, still in the period's fees
# --------------------------------------------------------------------------- #


async def _seed_orphan(session: AsyncSession, case: str) -> OrphanBook:
    if case == "waiting":
        return await seed_waiting(session)
    return await seed_orphan_with_its_income(session, dividend={"orphan-with-its-dividend": "50", "orphan-with-its-zero-dividend": "0"}[case])


ORPHAN_CASES = ["waiting", "orphan-with-its-dividend", "orphan-with-its-zero-dividend"]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ORPHAN_CASES)
async def test_lot_detail_with_an_orphan_linked_charge_is_degraded_with_no_failure_and_no_lot_carries_it(session, case):
    """``asset.lot_detail``: DEGRADED, ``failure_codes`` empty, and the one exported lot carries its own linked 2 EUR FEE
    (the presence barrier), never the orphan charge. The analysis the component read holds the charge's WARNING, for that
    charge, with no ``fails_analysis``. With a dividend of 50 EUR the dividend's own ASSET_INCOME_NO_ELIGIBLE_LOTS degrades
    the analysis too; the waiting case and the zero dividend have no other cause."""
    seeded = await _seed_orphan(session, case)
    context = _context(session, _scope(seeded.book, "asset"))

    payload = (await context.resolve("asset.lot_detail", required=True)).payload

    assert (payload["lot_reconstruction_status"], payload["failure_codes"]) == ("DEGRADED", [])
    assert _fees_by_quantity(payload["lots"], "allocated_fees") == {seeded.lot_quantity: D("2")}
    assert {_amount(row["allocated_taxes"]) for row in payload["lots"]} == {D("0")}

    analysis = await context.db_resource(ASSET_LOTS_RESOURCE, _loaded_by_the_component)
    assert analysis.data_quality is not None
    issues = [issue for issue in analysis.data_quality.issues if issue.message_params.get("transaction_id") == seeded.orphan_fee.id]
    assert [(str(issue.code), issue.severity, issue.message_i18n_key, issue.message_params.get("fails_analysis")) for issue in issues] == [(seeded.expected_code, "warning", seeded.expected_key, None)]
    other_codes = {str(issue.code) for issue in analysis.data_quality.issues} - {seeded.expected_code}
    expected_others = {"ASSET_INCOME_NO_ELIGIBLE_LOTS"} if case == "orphan-with-its-dividend" else set()
    assert other_codes == expected_others, f"issues={analysis.data_quality.issues}"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ORPHAN_CASES)
async def test_the_orphan_linked_charge_is_the_gap_between_the_period_fees_and_the_lots_fees(session, case):
    """Today's gap, pinned (M3 contract §2.1): an orphan lot charge is in no AI Export lot field, only in the position's
    period fees. ``asset.performance`` (the broker row's ``period_fees_taxes``) and ``asset.lot_detail`` (the lots'
    ``allocated_fees`` + ``allocated_taxes``) are two payloads of one export; every charge of the book is dated inside the
    period, so the period fees count all of them, and their difference is exactly the orphan charge.

    No single payload holds both figures: the comparison runs across the two the test builds in one context."""
    seeded = await _seed_orphan(session, case)
    context = _context(session, _scope(seeded.book, "asset"))

    performance = (await context.resolve("asset.performance", required=True)).payload
    lots = (await context.resolve("asset.lot_detail", required=True)).payload

    [row] = [row for row in performance["brokers"] if row["broker_id"] == seeded.book.broker.id]
    period_fees_taxes = _amount(row["period_fees_taxes"])
    lot_fees_taxes = sum((_amount(lot["allocated_fees"]) + _amount(lot["allocated_taxes"]) for lot in lots["lots"]), start=D("0"))
    assert (period_fees_taxes, lot_fees_taxes) == (D("2") + seeded.orphan_amount, D("2"))
    assert period_fees_taxes - lot_fees_taxes == seeded.orphan_amount, "the difference is the orphan linked charge"
