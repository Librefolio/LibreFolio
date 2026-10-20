"""MF-E2 — a short position in the lots' performance history, through the service: the developer's worked example.

Workstream MF, lot E2: the service-level red, through ``lots_analysis_service.get_lots_analysis`` with
``PERFORMANCE_HISTORY`` alone. The builder's contract is pinned purely in
``test_lots_analysis_pure.py::TestShortPositionsInThePerformanceHistory`` (its section header states it).

THE DEFECT. ``build_performance_history`` reads a short as if owned: its fragment, stored with a positive quantity, counts
+q·p; the sale that opens it is no flow, so the line starts on the buy-back, a deposit. A short that gained 200 on 1 000
reads ROI −100% and TWRR −180%.

THE RULE (developer, option (b), convention (1) «gross exposure», E2-Q1). An open short counts −q·p; its opening proceeds
are a flow out of the position on its opening date; TWRR compounds each day's change over the previous day's gross
exposure (Σ |value|); ROI reads the gain over the capital, the long leg's net deposits plus the short sales' cumulative
proceeds.

THE BOOK. U owns broker S, which allows shorting, and broker L. An EUR asset, its own rows: S sells 10 short at 100 on
Sunday 5 Jan 2025 (proceeds 1 000) and buys them back at 80 on Wednesday 8 Jan (pays 800); L buys 3 at 100 on 5 Jan;
quotes 100, 90, 80 and 80 from 5 to 8 Jan. Read on 8 Jan with ``broker_ids=[S]``: U can see L too, so the performance
history is replayed over both brokers and read for S alone — the path a filtered page takes. L's lot is in the replay,
out of the scope: the series is S's short alone.

Rows written into the test's session with uuid4 names (``_scope_boundary_books.py``) and rolled back. EUR only: no rate is
asked.
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

SHORT_SALE_DAY = date(2025, 1, 5)
BUY_BACK_DAY = date(2025, 1, 8)
PRICES = {date(2025, 1, 5): "100", date(2025, 1, 6): "90", date(2025, 1, 7): "80", date(2025, 1, 8): "80"}


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest.mark.asyncio
async def test_the_worked_example_shows_the_shorts_gain(session):
    """(date, ROI, TWRR) from 5 to 8 Jan: (0, —), (10%, 10%), (20%, 22.2222%), (20%, 22.2222%) — the approved figures. NAV
    −1 000, −900, −800, 0; flows +1 000 on 5 Jan and −800 on 8 Jan; capital 1 000; TWRR 1.1 × (1 + 100 / 900) − 1.

    Today (read 20/10/2026): no point on 5–7 Jan, and on 8 Jan ROI −1 and TWRR −1.8.
    """
    owner = await new_user(session, "e2")
    short_broker = await new_broker(session, "E2 S", owner)
    short_broker.allow_asset_shorting = True
    long_broker = await new_broker(session, "E2 L", owner)
    asset = await new_asset(session, "E2 short")
    add_prices(session, asset, PRICES)
    session.add_all(
        [
            asset_row(short_broker, asset, TransactionType.SELL, SHORT_SALE_DAY, "-10", amount="1000"),
            asset_row(short_broker, asset, TransactionType.BUY, BUY_BACK_DAY, "10", amount="-800"),
            asset_row(long_broker, asset, TransactionType.BUY, SHORT_SALE_DAY, "3", amount="-300"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=owner.id,
        asset_id=asset.id,
        broker_ids=[short_broker.id],
        date_from=None,
        date_to=BUY_BACK_DAY,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=[LotAnalysisType.PERFORMANCE_HISTORY],
    )

    # Precondition, green today and after: the replay is not FAILED, so the performance history is given (J-12).
    assert result.performance_history is not None, (result.calculation_status, result.data_quality)
    observed = [(point.date, point.roi, point.twrr) for point in result.performance_history]
    assert observed == [
        (date(2025, 1, 5), Decimal("0"), None),
        (date(2025, 1, 6), Decimal("0.1"), Decimal("0.1")),
        (date(2025, 1, 7), Decimal("0.2"), Decimal("0.222222")),
        (date(2025, 1, 8), Decimal("0.2"), Decimal("0.222222")),
    ]
