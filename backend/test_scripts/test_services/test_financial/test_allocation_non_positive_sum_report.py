"""MF-C2 — the report's allocations on a day whose slices add up to zero or less: ``value`` null, the amounts kept.

Developer's decision (ondata 6; backlog ``BACKLOG_POST_1.2.md`` «MF-C2»): when a day's allocation slices add up to zero
or less, every slice's ``value`` is null («—», the chart shows empty with a notice) and the amounts stay. The pure rule
(``weights.slice_percents``, ``DerivedViewsBuilder``) is tested in ``test_financial_math/test_weights.py`` and
``test_financial_math/test_allocation_non_positive_sum.py``; here, the wiring through ``PortfolioService``:
``get_summary`` (``allocation_by_type/sector/geography/asset``) and ``get_report`` with ``include_allocation_history``
(the allocation history; ``get_history`` returns the value series only, no allocation). The response validates
(``AllocationItem``, ``AllocationHistoryPoint``) and serialises the value as JSON null.

Two books (each a private SQLite file, the app schema; one user owning 100 % of one broker; EUR, no FX rate):

* **emptied** — 1000 deposited on D0, 10 X bought for 1000 on D1 (close 100), sold for 1000 on D2, 1000 withdrawn on
  D3. From D3 the portfolio holds nothing: type and sector are ``{Liquidity: 0}``, the asset dimension is Liquidity 0.
  On D1 (X 1000, Liquidity 0) the slices are 100 % / 0 %, unchanged.
* **overdraft** — no deposit; 10 X bought for 500 on D1 (close 50): stocks 500, cash −500, sum 0 from D1 on.

RED on the tree of 2026-10-28 (HEAD ed2f59268): the emptied book's last allocation reads ``Decimal('0.00')`` and the
overdraft's ``Decimal('50000.00')`` / ``Decimal('-50000.00')`` where None is expected (``AssertionError``); neither raises
a ``ValidationError`` today, since ``AllocationItem.value`` has no bound.

Isolation: PURE with respect to the lane — a private SQLite file under ``tmp_path`` (``SQLModel.metadata.create_all``,
NullPool, disposed at teardown), as ``test_asset_allocation_report.py``: no lane database, no server, no network. The
report, WAC and engine blob caches are emptied before and after each test.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery
from backend.app.services.financial_math.series_steps import value_at
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio import wac as wac_module
from backend.app.services.portfolio.portfolio_service import PortfolioService

EUR = "EUR"
D0, D1, D2, D3 = date(2025, 9, 1), date(2025, 9, 3), date(2025, 9, 8), date(2025, 9, 10)
END = date(2025, 9, 15)
ZERO = Decimal("0")


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    x_id: int
    x_name: str


def _clear_portfolio_caches() -> None:
    report_module._portfolio_l2_cache.clear()
    wac_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio():
    _clear_portfolio_caches()
    yield
    _clear_portfolio_caches()


def _close(asset_id: int, day: date, value: str) -> PriceHistory:
    price = Decimal(value)
    return PriceHistory(asset_id=asset_id, date=day, open=price, high=price, low=price, close=price, volume=Decimal("1"), currency=EUR, source_plugin_key="mf_c2_allocation_test")


def _emptied(broker_id: int, x_id: int) -> list:
    return [
        Transaction(broker_id=broker_id, asset_id=None, type=TransactionType.DEPOSIT, date=D0, quantity=ZERO, amount=Decimal("1000"), currency=EUR),
        Transaction(broker_id=broker_id, asset_id=x_id, type=TransactionType.BUY, date=D1, quantity=Decimal("10"), amount=Decimal("-1000"), currency=EUR),
        Transaction(broker_id=broker_id, asset_id=x_id, type=TransactionType.SELL, date=D2, quantity=Decimal("-10"), amount=Decimal("1000"), currency=EUR),
        Transaction(broker_id=broker_id, asset_id=None, type=TransactionType.WITHDRAWAL, date=D3, quantity=ZERO, amount=Decimal("-1000"), currency=EUR),
        _close(x_id, D1, "100"),
    ]


def _overdraft(broker_id: int, x_id: int) -> list:
    return [
        Transaction(broker_id=broker_id, asset_id=x_id, type=TransactionType.BUY, date=D1, quantity=Decimal("10"), amount=Decimal("-500"), currency=EUR),
        _close(x_id, D1, "50"),
    ]


@asynccontextmanager
async def _private_book(directory: Path, rows) -> AsyncIterator[_Book]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'mf_c2_allocation.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        tag = uuid4().hex[:12]
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(username=f"mf_c2_{tag}", email=f"mf_c2_{tag}@test.com", hashed_password="fakehash", is_active=True)
            broker = Broker(name=f"MF-C2 allocation {tag}")
            x = Asset(display_name=f"MF-C2 alloc X {tag}", currency=EUR, asset_type=AssetType.STOCK)
            session.add_all([user, broker, x])
            await session.flush()
            session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
            session.add_all(rows(broker.id, x.id))
            await session.commit()
            book = _Book(engine=engine, user_id=user.id, x_id=x.id, x_name=x.display_name)
        yield book
    finally:
        await engine.dispose()


async def _summary(book: _Book):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_summary(book.user_id, target_currency_override=EUR, date_from=D0, date_to=END)


async def _report(book: _Book):
    query = PortfolioReportQuery(
        date_range=OpenDateRangeModel(start=D0, end=END),
        target_currency=EUR,
        include_summary=True,
        include_history=False,
        include_allocation_history=True,
    )
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioService(session).get_report(book.user_id, query)


def _shown(items: Sequence) -> list[tuple]:
    return [(item.name, item.value, item.amount) for item in items]


def _assert_no_value(items: Sequence, expected_amounts: list[tuple], *, where: str) -> None:
    """Every slice's value is None; names, amounts and order as given."""
    assert [(item.name, item.amount) for item in items] == expected_amounts, f"{where}: names, amounts or order changed: {_shown(items)}"
    assert [item.value for item in items] == [None] * len(items), f"{where}: expected every value None, got {_shown(items)}"


def _assert_null_in_json(model, *, where: str) -> None:
    dumped = model.model_dump(mode="json")
    for dimension in ("allocation_by_type", "allocation_by_sector", "allocation_by_asset"):
        assert all(item["value"] is None for item in dumped[dimension]), f"{where}: {dimension} serialises {dumped[dimension]}"


class TestEmptiedPortfolio:
    @pytest.mark.asyncio
    async def test_the_summary_allocations_have_no_value(self, tmp_path):
        async with _private_book(tmp_path, _emptied) as book:
            summary = await _summary(book)
        assert summary.net_worth.amount == ZERO, f"precondition: the portfolio is emptied, NAV {summary.net_worth.amount}"
        _assert_no_value(summary.allocation_by_type, [("Liquidity", ZERO)], where="allocation_by_type")
        _assert_no_value(summary.allocation_by_sector, [("Liquidity", ZERO)], where="allocation_by_sector")
        _assert_no_value(summary.allocation_by_asset, [("Liquidity", ZERO)], where="allocation_by_asset")
        assert summary.allocation_by_geography == [], "geography carries no Liquidity: nothing left"
        _assert_null_in_json(summary, where="summary")

    @pytest.mark.asyncio
    async def test_the_last_allocation_history_step_has_no_value_the_held_days_are_unchanged(self, tmp_path):
        async with _private_book(tmp_path, _emptied) as book:
            report = await _report(book)
        for dimension in ("type", "sector", "asset"):
            points = getattr(report.allocation_history, dimension)
            assert points and points[-1].through == END, f"precondition: {dimension} reaches END"
            last = value_at(points, END)
            _assert_no_value(last.components, [("Liquidity", ZERO)], where=f"{dimension} on {END}")
            held = value_at(points, D1)
            values = {component.name: component.value for component in held.components}
            assert values.get("Liquidity") == Decimal("0.00"), f"{dimension} on {D1}: Liquidity 0 of a positive sum is 0.00, got {values}"
            assert sorted(value for name, value in values.items() if name != "Liquidity") == [Decimal("100.00")], f"{dimension} on {D1}: X is the whole, got {values}"
        report.model_dump(mode="json")  # serialises: no ValidationError on the way out


class TestOverdraft:
    @pytest.mark.asyncio
    async def test_the_summary_allocations_have_no_value(self, tmp_path):
        async with _private_book(tmp_path, _overdraft) as book:
            summary = await _summary(book)
            x_name = book.x_name
        assert summary.cash_total.amount == Decimal("-500"), f"precondition: cash −500, got {summary.cash_total.amount}"
        assert summary.market_value.amount == Decimal("500"), f"precondition: stocks 500, got {summary.market_value.amount}"
        _assert_no_value(summary.allocation_by_type, [("STOCK", Decimal("500")), ("Liquidity", Decimal("-500"))], where="allocation_by_type")
        _assert_no_value(summary.allocation_by_asset, [(x_name, Decimal("500")), ("Liquidity", Decimal("-500"))], where="allocation_by_asset")
        assert [item.value for item in summary.allocation_by_sector] == [None] * len(summary.allocation_by_sector), f"allocation_by_sector: {_shown(summary.allocation_by_sector)}"
        assert sum((item.amount for item in summary.allocation_by_sector), ZERO) == ZERO
        _assert_null_in_json(summary, where="summary")

    @pytest.mark.asyncio
    async def test_the_allocation_history_has_no_value_from_the_purchase_on(self, tmp_path):
        async with _private_book(tmp_path, _overdraft) as book:
            report = await _report(book)
        for dimension in ("type", "sector", "asset"):
            points = getattr(report.allocation_history, dimension)
            for day in (D1, END):
                step = value_at(points, day)
                assert step is not None, f"{dimension}: no step holding {day}"
                assert sum((component.amount for component in step.components), ZERO) == ZERO, f"precondition: {dimension} on {day} sums to 0"
                assert [component.value for component in step.components] == [None] * len(step.components), f"{dimension} on {day}: expected every value None, got {_shown(step.components)}"
        report.model_dump(mode="json")
