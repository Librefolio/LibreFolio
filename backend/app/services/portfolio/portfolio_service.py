"""
Portfolio Service for LibreFolio.

``PortfolioService`` is the orchestrator for portfolio-level aggregation and reporting. It is composed of one mixin per
theme, each in its own module of this package: ``data_access`` (brokers, transactions, assets, the engine run),
``summary``, ``history``, ``positions`` and ``report``. The WAC cost basis (``compute_wac_iterative``, ``wac_pool_holding``)
is in ``wac``, the small shared pieces in ``engine_facts``. The package re-exports nothing: import a name from the module
that defines it.

PortfolioService uses:
- the portfolio engine for valuation, cost basis (financial_math.average_cost) and realized sales
- financial_math.returns for TWRR/MWRR/Simple ROI
- FX service for currency conversion
- Transaction, Broker, Asset, PriceHistory DB models
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.portfolio.data_access import PortfolioDataMixin
from backend.app.services.portfolio.history import PortfolioHistoryMixin
from backend.app.services.portfolio.positions import PortfolioPositionsMixin
from backend.app.services.portfolio.report import PortfolioReportMixin
from backend.app.services.portfolio.summary import PortfolioSummaryMixin


class PortfolioService(PortfolioDataMixin, PortfolioSummaryMixin, PortfolioHistoryMixin, PortfolioPositionsMixin, PortfolioReportMixin):
    """Orchestrator for portfolio-level calculations.

    Aggregates WAC, prices, allocations, ROI metrics (TWRR/MWRR) and FIFO lots
    across brokers, applying share_percentage before cross-broker aggregation.

    Event loop safety:
    - All sync CPU-heavy calls (scipy) are wrapped in asyncio.to_thread().
    - All DB I/O uses AsyncSession.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
