"""J-12 (decision N81, option A) — AI Export: a FAILED lot reconstruction is declared, never shown with wrong figures.

Workstream J «Numeri e analisi», release 1.3. The AI Export reads the lots in five components: ``portfolio.fifo_summary``,
``broker.fifo_summary``, ``portfolio.fifo_lots``, ``broker.fifo_lots`` and ``asset.lot_detail``. When the lots analysis
of an asset is FAILED (its replay hit a code of ``_QUANTITATIVE_FAILURE_CODES``), every lot figure of that asset is
wrong; J-12 (``test_financial/test_lots_failed_analysis_withholding.py``) makes the service withhold them. The AI Export
says so instead (journal of J, «J-12 — backend e AI Export», 17/10 11:55–11:58, shape and versions approved):

- the four multi-asset components carry ``failed_reconstruction_asset_count`` (always present, 0 included) and
  ``failed_lot_reconstructions``, one row per FAILED asset with its identity and ``failure_codes`` only — exactly
  ``asset_id``, ``asset_name``, ``asset_ticker``, ``failure_codes``, so no figure can slip in later. ``failure_codes``:
  the sorted unique codes of the analysis' issues that carry ``fails_analysis``. The FAILED asset has no row in
  ``assets`` and no lot row;
- a FAILED asset's figures are null wherever they appear, never wrong numbers. In both ``*.fifo_summary`` the scope
  totals follow the payload's own rule («a summed amount with an unknown part is None, never a partial sum»): with a
  failed asset ``total_residual_cost_basis``, ``total_open_lots``, ``total_partial_lots`` and ``total_closed_lots`` are
  None; ``asset_count`` stays the number of rows (the reliable assets). With no failed asset nothing changes (GUARD).
  In ``*.fifo_lots`` ``lot_count`` and ``unavailable_amount_lot_count`` stay counts of the exported rows;
- ``asset.lot_detail`` carries ``lot_reconstruction_status`` (COMPLETE / DEGRADED / FAILED) and ``failure_codes``;
  FAILED: no lot, ``omitted_degraded_lot_count`` and ``unavailable_amount_lot_count`` 0;
- versions, at most +1 over the released ``v1.2.1`` (``ai-export-version-bump-once-per-release``): both
  ``*.fifo_summary`` stay 3 (already moved in this cycle by J-17), both ``*.fifo_lots`` go 2 → 3, ``asset.lot_detail``
  3 → 4. The pins on spec and catalog placeholder: ``TestFifoComponentVersion``
  (``test_ai_export_components_portfolio_broker_financial.py``) and
  ``test_lot_detail_component_is_versioned_v4_in_registry_and_placeholder`` (``test_ai_export_components_asset.py``).

TODAY (base ``2f4ef68e6``) none of the new fields exists, ``*.fifo_lots`` is version 2 and ``asset.lot_detail`` version 3,
and the FAILED asset is exported like any other, with the figures of its unreliable replay: a row in ``assets``, its lots
in ``lots``, its part in the scope totals. Each red says what it read.

As T8 of J-47, every test runs the real components on the real lots analysis over rows of its own
(``_scope_boundary_books.py`` helpers, uuid4 names), written into the session and rolled back. EUR only, dates in 2025.

THE BOOK. U owns broker A; quotes 100 on 3 Feb 2025, 105 on 6 Feb, 110 on 10 Feb, 112 on 13 Feb (each asset its own rows):
- X, COMPLETE: A buys 10 at 100 on 3 Feb;
- Y, FAILED: A buys 5 at 100 on 3 Feb, sells 8 at 110 on 10 Feb — 3 beyond what it holds — and buys 4 at 112 on 12 Feb.
  Today's replay leaves one lot of 4 open, while the account holds 1: wrong figures;
- Z, DEGRADED (A4 only): A receives 5 with a cost of 100 on 3 Feb, and Z has no quote at all.
Period 1–14 Feb 2025.
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

from backend.app.db.models import Asset, Broker, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.services.ai_export.components.asset_resources import ASSET_LOTS_RESOURCE
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.resources import BROKER_LOTS_RESULTS_RESOURCE, PORTFOLIO_LOTS_RESULTS_RESOURCE
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.test_scripts.test_services._scope_boundary_books import add_prices, asset_row, new_asset, new_broker, new_user

D = Decimal
PERIOD_START = date(2025, 2, 1)
PERIOD_END = date(2025, 2, 14)
BUY_DAY = date(2025, 2, 3)
SALE_DAY = date(2025, 2, 10)
REBUY_DAY = date(2025, 2, 12)
PRICES = {date(2025, 2, 3): "100", date(2025, 2, 6): "105", date(2025, 2, 10): "110", date(2025, 2, 13): "112"}
FAILED_ROW_KEYS = ["asset_id", "asset_name", "asset_ticker", "failure_codes"]
SCOPE_TOTALS = ("total_open_lots", "total_partial_lots", "total_closed_lots", "total_residual_cost_basis")
ABSENT = "<absent>"
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
    complete: Asset  # X
    failed: Asset | None  # Y
    degraded: Asset | None  # Z


async def seed(session: AsyncSession, *, failed: bool = True, degraded: bool = False) -> Book:
    owner = await new_user(session, "j12_ai")
    broker = await new_broker(session, "J12 AI A", owner)
    x = await new_asset(session, "J12 X complete")
    add_prices(session, x, PRICES)
    session.add(asset_row(broker, x, TransactionType.BUY, BUY_DAY, "10", amount="-1000"))
    y = z = None
    if failed:
        y = await new_asset(session, "J12 Y failed")
        add_prices(session, y, PRICES)
        session.add_all(
            [
                asset_row(broker, y, TransactionType.BUY, BUY_DAY, "5", amount="-500"),
                asset_row(broker, y, TransactionType.SELL, SALE_DAY, "-8", amount="880"),
                asset_row(broker, y, TransactionType.BUY, REBUY_DAY, "4", amount="-448"),
            ]
        )
    if degraded:
        z = await new_asset(session, "J12 Z degraded")
        session.add(asset_row(broker, z, TransactionType.ADJUSTMENT, BUY_DAY, "5", cost="100"))
    await session.flush()
    return Book(owner, broker, x, y, z)


def _scope(book: Book, domain: str, *, asset: Asset | None = None) -> BuildScope:
    common = {"request_id": f"j12-{domain}-{uuid4().hex}", "user_id": book.owner.id, "detail_level": DetailLevel.STANDARD, "period_start": PERIOD_START, "period_end": PERIOD_END, "target_currency": "EUR"}
    if domain == "broker":
        return BuildScope(domain=Domain.BROKER, broker_id=book.broker.id, broker_scope=(book.broker.id,), **common)
    if domain == "asset":
        return BuildScope(domain=Domain.ASSET, asset_id=asset.id, **common)
    return BuildScope(domain=Domain.PORTFOLIO, **common)


def _context(session: AsyncSession, scope: BuildScope) -> BuildContext:
    return BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)


def _loaded_by_the_component(_session: AsyncSession):
    raise AssertionError("the component should have loaded its lots: the resource is memoized per request")


async def _statuses_read(context: BuildContext, domain: str) -> dict[int, str]:
    """The lots analyses the component read, by asset: its own memoized resource, never a second load."""
    resource = {"broker": BROKER_LOTS_RESULTS_RESOURCE, "portfolio": PORTFOLIO_LOTS_RESULTS_RESOURCE}[domain]
    lots_read = await context.db_resource(resource, _loaded_by_the_component)
    return {asset_id: response.calculation_status for asset_id, response in lots_read.by_asset_id.items()}


def _money(value: object) -> object:
    return None if value is None else (value["code"], D(str(value["amount"])))


def _failed_row(asset: Asset) -> dict:
    return {"asset_id": asset.id, "asset_name": asset.display_name, "asset_ticker": asset.identifier_ticker, "failure_codes": ["FIFO_SOURCE_QUANTITY_MISSING"]}


def _complete_asset_row(payload: dict, book: Book) -> dict | None:
    """X's row in ``assets``, by what it holds — today's figures, which J-12 does not change."""
    row = next((row for row in payload["assets"] if row["asset_id"] == book.complete.id), None)
    if row is None:
        return None
    return {
        "open_lot_count": row["open_lot_count"],
        "open_quantity": D(str(row["open_quantity"])),
        "residual_cost_basis": _money(row["residual_cost_basis"]),
        "open_value": _money(row["open_value"]),
    }


X_ROW = {"open_lot_count": 1, "open_quantity": D("10"), "residual_cost_basis": ("EUR", D("1000")), "open_value": ("EUR", D("1120"))}


# --------------------------------------------------------------------------- #
# A1, A2 — broker.fifo_summary, portfolio.fifo_summary
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", MULTI_ASSET_DOMAINS)
async def test_a1_a2_fifo_summary_declares_the_failed_asset_and_nulls_the_scope_totals(session, domain):
    """A1 (broker) / A2 (portfolio): X COMPLETE and Y FAILED. Y has no row in ``assets`` and one row, identity and codes
    only, in ``failed_lot_reconstructions``; the count says 1; the scope totals, which would include Y's unknown part,
    are None; ``asset_count`` counts X's row alone, and X's row is unchanged.

    Today: no count, no list; Y has its row in ``assets`` (``asset_count`` 2) and its part in the totals — 2 open lots
    (X's and Y's lot of 4), 1 closed (Y's first lot), residual cost basis 1448 EUR (1000 + Y's 448). X's row is as
    expected: 1 open lot of 10, residual 1000, worth 1120.
    """
    book = await seed(session)
    context = _context(session, _scope(book, domain))

    payload = (await context.resolve(f"{domain}.fifo_summary", required=True)).payload

    # Precondition, green today and after: the component read both analyses, X COMPLETE and Y FAILED.
    assert await _statuses_read(context, domain) == {book.complete.id: "COMPLETE", book.failed.id: "FAILED"}
    failed_rows = payload.get("failed_lot_reconstructions", ABSENT)
    observed = {
        "failed_reconstruction_asset_count": payload.get("failed_reconstruction_asset_count", ABSENT),
        "failed_lot_reconstructions": failed_rows,
        "failed row key sets": ABSENT if failed_rows == ABSENT else [sorted(row) for row in failed_rows],
        "asset rows": sorted(row["asset_id"] for row in payload["assets"]),
        "asset_count": payload["asset_count"],
        **{name: payload[name] for name in SCOPE_TOTALS},
        "X row": _complete_asset_row(payload, book),
    }
    assert observed == {
        "failed_reconstruction_asset_count": 1,
        "failed_lot_reconstructions": [_failed_row(book.failed)],
        "failed row key sets": [FAILED_ROW_KEYS],
        "asset rows": [book.complete.id],
        "asset_count": 1,
        **dict.fromkeys(SCOPE_TOTALS),
        "X row": X_ROW,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", MULTI_ASSET_DOMAINS)
async def test_a1_a2_fifo_summary_with_no_failed_asset_says_zero(session, domain):
    """A1 / A2, no failed asset (X alone): ``failed_reconstruction_asset_count`` 0 and ``failed_lot_reconstructions``
    empty — both always present, so a reader never has to infer the absence.

    Today: both fields absent.
    """
    book = await seed(session, failed=False)

    payload = (await _context(session, _scope(book, domain)).resolve(f"{domain}.fifo_summary", required=True)).payload

    observed = {name: payload.get(name, ABSENT) for name in ("failed_reconstruction_asset_count", "failed_lot_reconstructions")}
    assert observed == {"failed_reconstruction_asset_count": 0, "failed_lot_reconstructions": []}


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", MULTI_ASSET_DOMAINS)
async def test_a1_a2_guard_fifo_summary_with_no_failed_asset_keeps_its_totals(session, domain):
    """GUARD (green today and after): with no failed asset the scope totals are today's — X's one open lot of 10 at 1000."""
    book = await seed(session, failed=False)

    payload = (await _context(session, _scope(book, domain)).resolve(f"{domain}.fifo_summary", required=True)).payload

    observed = {"asset_count": payload["asset_count"], **{name: payload[name] for name in SCOPE_TOTALS[:3]}, "total_residual_cost_basis": _money(payload["total_residual_cost_basis"]), "X row": _complete_asset_row(payload, book)}
    assert observed == {"asset_count": 1, "total_open_lots": 1, "total_partial_lots": 0, "total_closed_lots": 0, "total_residual_cost_basis": ("EUR", D("1000")), "X row": X_ROW}


# --------------------------------------------------------------------------- #
# A3 — broker.fifo_lots, portfolio.fifo_lots (v3)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", MULTI_ASSET_DOMAINS)
async def test_a3_fifo_lots_v3_declares_the_failed_asset_and_exports_no_lot_of_it(session, domain):
    """A3: ``{domain}.fifo_lots`` is version 3; it declares Y as the summary does and exports no lot row of it. Its counts
    stay counts of the exported rows: X's one lot, every amount known.

    Today: version 2, no count, no list, and Y's two lots exported beside X's (its closed lot of 5 and the lot of 4):
    ``lot_count`` 3.
    """
    book = await seed(session)
    context = _context(session, _scope(book, domain))

    envelope = await context.resolve(f"{domain}.fifo_lots", required=True)
    payload = envelope.payload

    assert await _statuses_read(context, domain) == {book.complete.id: "COMPLETE", book.failed.id: "FAILED"}
    observed = {
        "component_version": envelope.component_version,
        "failed_reconstruction_asset_count": payload.get("failed_reconstruction_asset_count", ABSENT),
        "failed_lot_reconstructions": payload.get("failed_lot_reconstructions", ABSENT),
        "assets of the lot rows": sorted(row["asset_id"] for row in payload["lots"]),
        "lot_count": payload["lot_count"],
        "unavailable_amount_lot_count": payload["unavailable_amount_lot_count"],
    }
    assert observed == {
        "component_version": 3,
        "failed_reconstruction_asset_count": 1,
        "failed_lot_reconstructions": [_failed_row(book.failed)],
        "assets of the lot rows": [book.complete.id],
        "lot_count": 1,
        "unavailable_amount_lot_count": 0,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", MULTI_ASSET_DOMAINS)
async def test_a3_fifo_lots_with_no_failed_asset_says_zero(session, domain):
    """A3, no failed asset: count 0, list empty, both present; X's lot exported as today.

    Today: version 2, both fields absent; X's lot exported (green part).
    """
    book = await seed(session, failed=False)

    envelope = await _context(session, _scope(book, domain)).resolve(f"{domain}.fifo_lots", required=True)
    payload = envelope.payload

    observed = {
        "component_version": envelope.component_version,
        **{name: payload.get(name, ABSENT) for name in ("failed_reconstruction_asset_count", "failed_lot_reconstructions")},
        "assets of the lot rows": sorted(row["asset_id"] for row in payload["lots"]),
        "lot_count": payload["lot_count"],
    }
    assert observed == {"component_version": 3, "failed_reconstruction_asset_count": 0, "failed_lot_reconstructions": [], "assets of the lot rows": [book.complete.id], "lot_count": 1}


# --------------------------------------------------------------------------- #
# A4 — asset.lot_detail (v4)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("which", "status", "codes", "lot_count"),
    [("failed", "FAILED", ["FIFO_SOURCE_QUANTITY_MISSING"], 0), ("complete", "COMPLETE", [], 1), ("degraded", "DEGRADED", [], 1)],
    ids=["failed", "complete", "degraded"],
)
async def test_a4_lot_detail_v4_states_the_reconstruction_status(session, which, status, codes, lot_count):
    """A4: ``asset.lot_detail`` is version 4 and states ``lot_reconstruction_status`` and ``failure_codes``. FAILED (Y): no
    lot, both counters 0. COMPLETE (X) and DEGRADED (Z: a lot opened by an ADJUSTMENT, no reference price): their lots, no
    failure code.

    Today: version 3, neither field; the FAILED asset exports its 2 lots (the closed lot of 5, the lot of 4), the other two
    their 1 lot each (green part).
    """
    book = await seed(session, degraded=True)
    asset = {"failed": book.failed, "complete": book.complete, "degraded": book.degraded}[which]
    context = _context(session, _scope(book, "asset", asset=asset))

    envelope = await context.resolve("asset.lot_detail", required=True)
    payload = envelope.payload

    # Precondition, green today and after: the analysis the component read has the status this case is about.
    assert (await context.db_resource(ASSET_LOTS_RESOURCE, _loaded_by_the_component)).calculation_status == status
    observed = {
        "component_version": envelope.component_version,
        "lot_reconstruction_status": payload.get("lot_reconstruction_status", ABSENT),
        "failure_codes": payload.get("failure_codes", ABSENT),
        "lots": len(payload["lots"]),
        "omitted_degraded_lot_count": payload["omitted_degraded_lot_count"],
        "unavailable_amount_lot_count": payload["unavailable_amount_lot_count"],
    }
    assert observed == {
        "component_version": 4,
        "lot_reconstruction_status": status,
        "failure_codes": codes,
        "lots": lot_count,
        "omitted_degraded_lot_count": 0,
        "unavailable_amount_lot_count": 0,
    }
