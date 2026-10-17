"""J-47 — T8: ``portfolio.fifo_summary`` shows the units of a transfer still in transit on the period's last day.

Workstream J «Numeri e analisi», release 1.3. The Portfolio-domain FIFO summary asks the lots analysis for the lots of
every broker the user can access, up to the period's end (``payloads/portfolio_broker.py``, ``load_lots_results``:
``broker_ids`` = the accessible brokers, ``date_to`` = ``snapshot_as_of``). A TRANSFER that departed on or before that
day and arrives after it loses its arriving leg in that analysis (``LotsAnalysisService._load_transactions`` cuts at
``date_to``): TRANSFER_PAIR_MISSING, FAILED, and the units read as still at the sending broker. J-47: the late leg goes
to the engine only, which replays until ``date_to``; the units stay IN_TRANSIT. In the AI Export the contract and its
version do not change, only the values.

As R13 of J-10 (``test_ai_export_broker_fifo_summary_scope_boundary.py``), this test runs the real component on the real
lots analysis over rows of its own (``_scope_boundary_books.py``, ledger L2), written into the session and rolled back.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_engine
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.resources import PORTFOLIO_LOTS_RESULTS_RESOURCE
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.test_scripts.test_services._scope_boundary_books import L2_DATE_TO, seed_l2

D = Decimal


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


def _loaded_by_the_component(_session: AsyncSession):
    raise AssertionError("portfolio.fifo_summary should have loaded its lots: the resource is memoized per request")


@pytest.mark.asyncio
async def test_t8_portfolio_fifo_summary_shows_the_units_in_transit_on_the_periods_last_day(session):
    """T8 — ``portfolio.fifo_summary`` for U (A and B) on ledger L2, period 1–14 Jan 2025, EUR: on 14 Jan the 10 units
    sent from A on 12 Jan have not arrived at B (16 Jan). The asset's lots analysis is COMPLETE and its row says so: 10 open,
    custody IN_TRANSIT only (``has_in_transit_custody`` true), the lot states IN_TRANSIT, LONG, OPEN, the only broker named
    the opening one, A (an in-transit slice names none), still worth 10 × 130 = 1300.

    Today: the asset's lots analysis is FAILED (TRANSFER_PAIR_MISSING: B's leg cut at 14 Jan) and its row reads the units
    as still at A — 10 open, ``has_in_transit_custody`` false, custody types [BROKER], states [LONG, OPEN], broker ids
    [A], worth 1300 (the precondition, the asset discovered and analysed, is green).
    """
    book = await seed_l2(session)
    scope = BuildScope(
        request_id=f"j47-t8-{uuid4().hex}",
        user_id=book.owner.id,
        domain=Domain.PORTFOLIO,
        detail_level=DetailLevel.STANDARD,
        period_start=date(2025, 1, 1),
        period_end=L2_DATE_TO,
        target_currency="EUR",
    )
    context = BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)

    envelope = await context.resolve("portfolio.fifo_summary", required=True)
    lots_read = await context.db_resource(PORTFOLIO_LOTS_RESULTS_RESOURCE, _loaded_by_the_component)

    # Precondition, green today and after: the component found the asset and analysed it — the red is its content.
    assert book.asset.id in lots_read.by_asset_id, sorted(lots_read.by_asset_id)
    row = next((row for row in envelope.payload["assets"] if row["asset_id"] == book.asset.id), None)
    observed_row = (
        None
        if row is None
        else {
            "open_quantity": D(str(row["open_quantity"])),
            "has_in_transit_custody": row["has_in_transit_custody"],
            "custody_types": row["custody_types"],
            "states": row["states"],
            "broker_ids": row["broker_ids"],
            "open_value": None if row["open_value"] is None else (row["open_value"]["code"], D(str(row["open_value"]["amount"]))),
        }
    )
    assert {"lots analysis of the asset": lots_read.by_asset_id[book.asset.id].calculation_status, "asset row": observed_row} == {
        "lots analysis of the asset": "COMPLETE",
        "asset row": {
            "open_quantity": D("10"),
            "has_in_transit_custody": True,
            "custody_types": ["IN_TRANSIT"],
            "states": ["IN_TRANSIT", "LONG", "OPEN"],
            "broker_ids": [book.broker_a.id],
            "open_value": ("EUR", D("1300")),
        },
    }
