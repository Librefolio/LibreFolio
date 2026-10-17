"""J-33 — the lots' performance history counts the days at cost: ROI and TWRR start on the day the lot opens.

Workstream J «Numeri e analisi», release 1.3: the service-level red of the lot, through
``lots_analysis_service.get_lots_analysis`` with ``PERFORMANCE_HISTORY`` alone. The builder's rules are pinned purely in
``test_lots_analysis_pure.py::TestPerformanceHistoryAtCost``.

THE DEFECT. ``build_performance_history`` values a day only when it has a price mark; it never receives
``at_cost_until``, the last day with no observation on or before it, which the value and return histories already value
at cost (J-17 decision (a), CP-7b). So the flows before the first mark are carried onto it, and the TWRR series, based on
the first NAV, leaves out the jump from cost to the first price that ROI includes.

THE RULE (coordinator, 17/10; the fix follows this red). Up to ``at_cost_until`` a day without a mark gets a NAV at cost —
the residual cost of the in-scope fragments open that day — so ROI and TWRR start on the day the lot opens, and with a
single inflow they agree on the last day.

THE BOOK. U owns broker A. A EUR asset, its own rows: an ADJUSTMENT-in of 10 at a cost of 100 EUR a unit on Monday 3 Feb
2025, before any quote; quotes of 110 on Thursday 6 Feb, 115 on Friday 7 Feb and 121 on Monday 10 Feb, read on the 10th.
The analysis values 3–5 Feb at cost (1 000), 6 Feb at 1 100, 7–9 Feb at 1 150 (the 7th carried over the weekend) and 10
Feb at 1 210, the 1 000 flowing in on 3 Feb.

Rows written into the test's session with uuid4 names (``_scope_boundary_books.py``) and rolled back. EUR only.
"""

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import LotAnalysisType
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.test_scripts.test_services._scope_boundary_books import add_prices, asset_row, new_asset, new_broker, new_user

ADJUSTMENT_DAY = date(2025, 2, 3)
DATE_TO = date(2025, 2, 10)
PRICES = {date(2025, 2, 6): "110", date(2025, 2, 7): "115", date(2025, 2, 10): "121"}


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest.mark.asyncio
async def test_the_performance_history_starts_on_the_adjustment_day_and_twrr_meets_roi(session):
    """The performance history of a lot adjusted in before the asset's first quote: points from the adjustment day, 3 Feb
    (ROI 0 at cost), and on the last day ROI and TWRR both 1 210 / 1 000 − 1 = 21% — one inflow, so the time-weighted and
    the simple return agree.

    Today (read 17/10/2026): the first point is on 6 Feb, the first quote — 3–5 Feb have no NAV, and the 1 000 is carried
    onto the 6th; on the last day ROI is 21% but TWRR, based on the 6th, only 1 210 / 1 100 − 1 = 10%.
    """
    owner = await new_user(session, "j33")
    broker = await new_broker(session, "J33 A", owner)
    asset = await new_asset(session, "J33 at cost")
    add_prices(session, asset, PRICES)
    session.add(asset_row(broker, asset, TransactionType.ADJUSTMENT, ADJUSTMENT_DAY, "10", cost="100"))
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=owner.id,
        asset_id=asset.id,
        broker_ids=None,
        date_from=None,
        date_to=DATE_TO,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=[LotAnalysisType.PERFORMANCE_HISTORY],
    )

    # Precondition, green today and after: the analysis is not FAILED, so its performance history is given (J-12).
    assert result.performance_history is not None, (result.calculation_status, result.data_quality)
    points = {point.date: point for point in result.performance_history}
    first_point = min((day for day, point in points.items() if point.roi is not None), default=None)
    last = points[DATE_TO]
    observed = {"first day with a point": first_point, "last day (ROI, TWRR)": (last.roi, last.twrr)}
    assert observed == {"first day with a point": ADJUSTMENT_DAY, "last day (ROI, TWRR)": (Decimal("0.21"), Decimal("0.21"))}
