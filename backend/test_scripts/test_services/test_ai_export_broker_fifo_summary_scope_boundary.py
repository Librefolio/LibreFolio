"""J-10, decision N76 — R13: ``broker.fifo_summary`` reads a TRANSFER from outside the broker at the boundary.

Workstream J «Numeri e analisi», release 1.3. The Broker-domain FIFO summary asks the lots analysis for the lots of ONE
broker (``payloads/portfolio_broker.py``, ``load_lots_results``: ``broker_ids=[broker]``), so every TRANSFER that
crosses into or out of that broker sends its asset into FAILED today (TRANSFER_PAIR_MISSING), and the asset loses its
lots in the export. Decision N76: the leg is read at the boundary of the scope (``financial_math/lots/
scope_boundary.py``); in the AI Export the contract and its version do not change, only the values.

Unlike the sibling ``broker.fifo_summary`` tests, which double ``LotsAnalysisService``, this one runs the real component
on the real lots analysis over rows of its own (``_scope_boundary_books.py``, ledger L1), written into the session and
rolled back: the subject is the analysis the component reads.
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
from backend.app.services.ai_export.components.resources import BROKER_LOTS_RESULTS_RESOURCE
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.test_scripts.test_services._scope_boundary_books import L1_DATE_TO, seed_l1

D = Decimal


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


def _money(value: object) -> tuple[str, Decimal] | None:
    return None if value is None else (value["code"], D(str(value["amount"])))


def _loaded_by_the_component(_session: AsyncSession):
    raise AssertionError("broker.fifo_summary should have loaded its lots: the resource is memoized per request")


@pytest.mark.asyncio
async def test_r13_broker_fifo_summary_of_the_receiver_carries_the_arrival_read_at_the_boundary(session):
    """R13 — ``broker.fifo_summary`` for B on ledger L1 (U, period 1–16 Jan 2025, EUR). B's arrival reads as an
    ADJUSTMENT-in at its own cost basis, so the asset's lots analysis for B is COMPLETE and the asset row carries R1's
    lot: 10 received at 100 (original cost 1000), 4 sold at 150 (realized 200), 6 open whose residual cost basis is
    6 × 100 = 600.

    Today: no row for the asset — the component does discover and analyse it for B alone (the precondition below), but
    that analysis is FAILED (TRANSFER_PAIR_MISSING, FIFO_SOURCE_QUANTITY_MISSING) with no lot, so the summary lists no
    asset.
    """
    book = await seed_l1(session)
    broker_id = book.broker_b.id
    scope = BuildScope(
        request_id=f"j10-r13-{uuid4().hex}",
        user_id=book.owner.id,
        domain=Domain.BROKER,
        detail_level=DetailLevel.STANDARD,
        period_start=date(2025, 1, 1),
        period_end=L1_DATE_TO,
        target_currency="EUR",
        broker_scope=(broker_id,),
        broker_id=broker_id,
    )
    context = BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)

    envelope = await context.resolve("broker.fifo_summary", required=True)
    lots_read = await context.db_resource(BROKER_LOTS_RESULTS_RESOURCE, _loaded_by_the_component)

    # Precondition, green today and after: the component found the asset at B and analysed it — the red is its content.
    assert book.asset.id in lots_read.by_asset_id, sorted(lots_read.by_asset_id)
    row = next((row for row in envelope.payload["assets"] if row["asset_id"] == book.asset.id), None)
    observed_row = (
        None
        if row is None
        else {
            "realized_pnl": _money(row["realized_pnl"]),
            "open_quantity": D(str(row["open_quantity"])),
            "original_quantity": D(str(row["original_quantity"])),
            "original_cost": _money(row["original_cost"]),
            "residual_cost_basis": _money(row["residual_cost_basis"]),
        }
    )
    assert {"lots analysis of the asset for B": lots_read.by_asset_id[book.asset.id].calculation_status, "asset row": observed_row} == {
        "lots analysis of the asset for B": "COMPLETE",
        "asset row": {
            "realized_pnl": ("EUR", D("200")),
            "open_quantity": D("6"),
            "original_quantity": D("10"),
            "original_cost": ("EUR", D("1000")),
            "residual_cost_basis": ("EUR", D("600")),
        },
    }
