"""MF5-1b — ``PortfolioCalculationEngine.calculate(include_positions=...)``: the engine hands back the position frames,
and the flag is part of the blob-cache key.

The builder's contract (``PositionFrame``, ``compute_position_frames``, the frames' rules) is tested on hand-fed books
in ``test_financial_math/test_position_frames.py``. What only the engine can show:

- ``calculate`` takes ``include_positions: bool = False``; with it, ``result.position_frames`` is a tuple of
  ``PositionFrame`` that obeys the bit parity on the engine's real pipeline (``Decimal("0")`` + the non-None market
  values of the frames covering a day, in tuple order, is that day's ``market_value``); without it, None;
- the flag is part of the blob-cache key, like ``include_candles``: the blob cache answers a request whose range matches
  a cached blob, so a run without positions must never answer a request with them (it would hand back None), nor the
  reverse (it would hand back frames nobody asked for, paid by the cache). The four orders are run one after the other
  on the same book, without clearing the cache in between.

The book (a private SQLite file, the app schema; one user owning 100 % of one broker; EUR): a deposit, two buys, a
quote, a partial sale. No FX rate is read.

Isolation: PURE with respect to the lane — a private SQLite file under ``tmp_path`` (``SQLModel.metadata.create_all``,
NullPool, disposed at teardown), no lane database, no server, no network. The report, WAC and engine blob caches are
emptied before and after each test.

RED on HEAD 5dc68b650, by absence: ``PositionFrame`` does not exist (``ImportError`` at collection). After a cure that
adds the type but not the engine flag, ``calculate`` raises ``TypeError``; after one that forgets the cache key, the
second run of ``test_the_flag_is_part_of_the_blob_cache_key`` gets the first run's blob.

Runs in ``./dev.py test services roi-fifo-utils`` (the runner collects the whole ``test_financial/`` directory).
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.portfolio.models import PortfolioCalculationResult, PositionFrame

EUR = "EUR"
D0, D1, D2, D3 = date(2025, 6, 2), date(2025, 6, 3), date(2025, 6, 9), date(2025, 6, 16)
END = date(2025, 6, 30)


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    broker_id: int
    asset_ids: tuple[int, int]


def _clear_portfolio_caches() -> None:
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio():
    _clear_portfolio_caches()
    yield
    _clear_portfolio_caches()


@asynccontextmanager
async def _private_book(directory: Path) -> AsyncIterator[_Book]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'mf5_position_frames.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        tag = uuid4().hex[:12]
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(username=f"mf5_pf_{tag}", email=f"mf5_pf_{tag}@test.com", hashed_password="fakehash", is_active=True)
            broker = Broker(name=f"MF5 position frames {tag}")
            x = Asset(display_name=f"MF5 frames X {tag}", currency=EUR, asset_type=AssetType.STOCK)
            y = Asset(display_name=f"MF5 frames Y {tag}", currency=EUR, asset_type=AssetType.ETF)
            session.add_all([user, broker, x, y])
            await session.flush()
            session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
            session.add_all(
                [
                    Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=D0, quantity=Decimal("0"), amount=Decimal("5000"), currency=EUR),
                    Transaction(broker_id=broker.id, asset_id=x.id, type=TransactionType.BUY, date=D1, quantity=Decimal("10"), amount=Decimal("-1000"), currency=EUR),
                    Transaction(broker_id=broker.id, asset_id=y.id, type=TransactionType.BUY, date=D1, quantity=Decimal("4"), amount=Decimal("-400"), currency=EUR),
                    Transaction(broker_id=broker.id, asset_id=x.id, type=TransactionType.SELL, date=D3, quantity=Decimal("-3"), amount=Decimal("330"), currency=EUR),
                    PriceHistory(asset_id=x.id, date=D2, open=Decimal("105"), high=Decimal("105"), low=Decimal("105"), close=Decimal("105"), volume=Decimal("1"), currency=EUR, source_plugin_key="mf5_frames_test"),
                ]
            )
            await session.commit()
            book = _Book(engine=engine, user_id=user.id, broker_id=broker.id, asset_ids=(x.id, y.id))
        yield book
    finally:
        await engine.dispose()


async def _calculate(book: _Book, **kwargs) -> PortfolioCalculationResult:
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioCalculationEngine(session).calculate(user_id=book.user_id, date_to=END, target_currency=EUR, **kwargs)


def _assert_frames(result: PortfolioCalculationResult, book: _Book) -> None:
    frames = result.position_frames
    assert isinstance(frames, tuple) and frames, f"position_frames is {frames!r}"
    assert all(isinstance(frame, PositionFrame) for frame in frames)
    assert {(frame.broker_id, frame.asset_id) for frame in frames} == {(book.broker_id, asset_id) for asset_id in book.asset_ids}
    day = result.daily_states.first_date
    while day <= result.daily_states.last_date:
        total = Decimal("0")
        for frame in frames:
            if frame.start <= day <= frame.end and frame.market_value is not None:
                total += frame.market_value
        market_value = result.daily_states.state_on(day).market_value
        assert total == market_value and total.as_tuple() == market_value.as_tuple(), f"{day}: frames {total!r}, state {market_value!r}"
        day += timedelta(days=1)


class TestTheEngineFlag:
    def test_calculate_takes_include_positions_off_by_default(self):
        parameter = inspect.signature(PortfolioCalculationEngine.calculate).parameters.get("include_positions")
        assert parameter is not None, "calculate() has no include_positions"
        assert parameter.default is False

    @pytest.mark.asyncio
    async def test_asked_the_engine_returns_frames_with_bit_parity(self, tmp_path):
        async with _private_book(tmp_path) as book:
            result = await _calculate(book, include_positions=True)
            _assert_frames(result, book)

    @pytest.mark.asyncio
    async def test_not_asked_there_are_none(self, tmp_path):
        async with _private_book(tmp_path) as book:
            assert (await _calculate(book)).position_frames is None
            _clear_portfolio_caches()
            assert (await _calculate(book, include_positions=False)).position_frames is None

    @pytest.mark.asyncio
    async def test_the_flag_is_part_of_the_blob_cache_key(self, tmp_path):
        """Same book, same range, the cache never cleared: off → on → off → on. Each answer is its own flag's."""
        async with _private_book(tmp_path) as book:
            first_off = await _calculate(book)
            assert first_off.position_frames is None
            first_on = await _calculate(book, include_positions=True)
            _assert_frames(first_on, book)
            assert first_on is not first_off, "a run with positions was answered by the cached run without them"
            again_off = await _calculate(book)
            assert again_off.position_frames is None, "a run without positions was answered by the cached run with them"
            again_on = await _calculate(book, include_positions=True)
            _assert_frames(again_on, book)
            assert again_on is first_on, "precondition of the key test: an identical request is a cache hit"
