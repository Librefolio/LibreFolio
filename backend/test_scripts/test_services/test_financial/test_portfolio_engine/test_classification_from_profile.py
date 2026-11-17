"""Project 68, lot D2 — the portfolio engine reads each asset's countries and sectors from the asset profile, per day.

Today ``PortfolioCalculationEngine`` (``financial_math/portfolio/engine.py``, step 9) loads one dict per asset from
``Asset.classification_params`` and hands it to ``DailyStateBuilder``. The cure (contract):

- ``PortfolioCalculationEngine._load_asset_classifications(asset_ids, date_from, date_to)`` (async) reads
  ``store.read_steps(self.db, asset_ids, DateRangeModel(start=date_from, end=date_to), keys=["geography", "sector"],
  carry_back=True)`` and returns ``{asset_id: {voice: [ClassificationStep(date, through, weights)]}}``: every asset id
  asked is a key, an asset with no profile rows maps to ``None``; ``weights`` are the stored map's Decimals, or None for
  a row that emptied the voice;
- the engine no longer reads ``Asset.classification_params`` for allocations: an asset that has them but no profile
  rows is "Unknown" in both dimensions;
- ``calculate`` hands those steps to the builder: a geography that changes on a quiet day changes the allocation on that
  very day, in a segment of its own.

The builder's side (pure) is pinned in ``test_financial_math/test_asset_allocation.py`` (section 4).

The book (a private SQLite file, the app schema; one user owning 100 % of one broker; EUR, no FX): a deposit on D0; on
D1 P (an ETF with profile rows) bought 10 at 100 and C (a stock with ``classification_params`` only) 5 at 100, closes
P 110 and C 90 on D1. P's geography: all USA read on D1, 60 % USA and 40 % Japan read on CHANGE (no movement, no
quote that day); P's sector Technology read on D1; a TER row that the loader must not return. N has nothing at all; E
(not held) has Italy read on D1 and an emptied geography (NULL row) on CHANGE.

Isolation: PURE with respect to the lane — a private SQLite file under ``tmp_path`` (``SQLModel.metadata.create_all``,
NullPool, disposed at teardown), no lane database, no server, no network. The engine's blob cache is emptied before and
after each test: private files reuse ids. ``TestTheEngineCache`` pins that the blob's key reads the profile rows: a new
row and a forgotten one each give a new result.

RED on HEAD bfdd8ffa0: the loader tests by absence (``AttributeError``: no ``_load_asset_classifications``, no
``ClassificationStep``); the ``calculate`` tests by behaviour (C's ``classification_params`` still give USA and
Energy, P's profile is not read: its value is Unknown). The module collects.

Runs in ``./dev.py test services classification-from-profile`` (and in ``roi-fifo-utils``, which collects the whole
``test_financial/`` directory).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetProfileUpdate, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.app.services.financial_math.portfolio import daily_state as daily_state_module
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine

pytestmark = pytest.mark.asyncio

EUR = "EUR"
D0, D1, CHANGE, END = date(2025, 6, 2), date(2025, 6, 3), date(2025, 6, 10), date(2025, 6, 20)
P_VALUE, C_VALUE = Decimal("1100"), Decimal("450")  # 10 P at 110, 5 C at 90
LEGACY_CLASSIFICATION = '{"geographic_area":{"distribution":{"USA":"1.0"}},"sector_area":{"distribution":{"Energy":"1.0"}}}'


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    p_id: int
    c_id: int
    n_id: int
    e_id: int


def _clear_engine_cache() -> None:
    portfolio_engine_module._portfolio_blob_cache.clear()


@pytest.fixture(autouse=True)
def no_cached_portfolio():
    _clear_engine_cache()
    yield
    _clear_engine_cache()


def _close(asset_id: int, day: date, value: str) -> PriceHistory:
    price = Decimal(value)
    return PriceHistory(asset_id=asset_id, date=day, open=price, high=price, low=price, close=price, volume=Decimal("1"), currency=EUR, source_plugin_key="d2_classification_test")


def _profile_row(asset_id: int, key: str, value, read_on: date) -> AssetProfileUpdate:
    stored = None if value is None else json.dumps(normalize_value(key, value))
    return AssetProfileUpdate(asset_id=asset_id, key=key, value=stored, source="justetf", read_on=read_on)


@asynccontextmanager
async def _private_book(directory: Path) -> AsyncIterator[_Book]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{directory / 'd2_classification.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        tag = uuid4().hex[:12]
        async with AsyncSession(engine, expire_on_commit=False) as session:
            user = User(username=f"d2_cls_{tag}", email=f"d2_cls_{tag}@test.com", hashed_password="fakehash", is_active=True)
            broker = Broker(name=f"D2 classification {tag}")
            p = Asset(display_name=f"D2 P {tag}", currency=EUR, asset_type=AssetType.ETF)
            c = Asset(display_name=f"D2 C {tag}", currency=EUR, asset_type=AssetType.STOCK, classification_params=LEGACY_CLASSIFICATION)
            n = Asset(display_name=f"D2 N {tag}", currency=EUR, asset_type=AssetType.STOCK)
            e = Asset(display_name=f"D2 E {tag}", currency=EUR, asset_type=AssetType.ETF)
            session.add_all([user, broker, p, c, n, e])
            await session.flush()
            session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
            session.add_all(
                [
                    Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=D0, quantity=Decimal("0"), amount=Decimal("5000"), currency=EUR),
                    Transaction(broker_id=broker.id, asset_id=p.id, type=TransactionType.BUY, date=D1, quantity=Decimal("10"), amount=Decimal("-1000"), currency=EUR),
                    Transaction(broker_id=broker.id, asset_id=c.id, type=TransactionType.BUY, date=D1, quantity=Decimal("5"), amount=Decimal("-500"), currency=EUR),
                    _close(p.id, D1, "110"),
                    _close(c.id, D1, "90"),
                    _profile_row(p.id, "geography", {"USA": "1"}, D1),
                    _profile_row(p.id, "geography", {"USA": "0.6", "JPN": "0.4"}, CHANGE),
                    _profile_row(p.id, "sector", {"Technology": "1"}, D1),
                    _profile_row(p.id, "ter", "0.0022", D1),
                    _profile_row(e.id, "geography", {"ITA": "1"}, D1),
                    _profile_row(e.id, "geography", None, CHANGE),
                ]
            )
            await session.commit()
            book = _Book(engine=engine, user_id=user.id, p_id=p.id, c_id=c.id, n_id=n.id, e_id=e.id)
        yield book
    finally:
        await engine.dispose()


async def _load(book: _Book, asset_ids: list[int]):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioCalculationEngine(session)._load_asset_classifications(asset_ids, D0, END)


async def _calculate(book: _Book):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        return await PortfolioCalculationEngine(session).calculate(book.user_id, date_from=D0, date_to=END, target_currency=EUR)


def _spans(steps) -> list[tuple[date, date, dict[str, Decimal] | None]]:
    """The steps as (date, through, weights): each must be a ClassificationStep with Decimal weights."""
    step_type = daily_state_module.ClassificationStep
    spans = []
    for step in steps:
        assert isinstance(step, step_type), f"{step!r} is not a ClassificationStep"
        if step.weights is not None:
            assert all(isinstance(weight, Decimal) for weight in step.weights.values()), f"weights {step.weights!r} are not Decimals"
        spans.append((step.date, step.through, None if step.weights is None else dict(step.weights)))
    return spans


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


class TestTheLoader:
    async def test_every_asset_asked_is_a_key_and_one_without_rows_is_none(self, tmp_path):
        async with _private_book(tmp_path) as book:
            loaded = await _load(book, [book.p_id, book.c_id, book.n_id, book.e_id])
        assert set(loaded) == {book.p_id, book.c_id, book.n_id, book.e_id}
        assert loaded[book.n_id] is None, "no profile rows: None"
        assert loaded[book.c_id] is None, "classification_params alone are not read: None"

    async def test_two_geography_rows_are_two_steps_carried_back_to_date_from(self, tmp_path):
        async with _private_book(tmp_path) as book:
            loaded = await _load(book, [book.p_id])
        voices = loaded[book.p_id]
        assert set(voices) <= {"geography", "sector"}, f"only the two voices are read: {sorted(voices)}"
        assert _spans(voices["geography"]) == [
            (D0, CHANGE - timedelta(days=1), {"USA": Decimal("1")}),
            (CHANGE, END, {"USA": Decimal("0.6"), "JPN": Decimal("0.4")}),
        ], "the first row (D1) carried back to date_from (D0), the last holding to date_to"
        assert _spans(voices["sector"]) == [(D0, END, {"Technology": Decimal("1")})]

    async def test_an_emptied_voice_is_a_step_with_no_weights(self, tmp_path):
        async with _private_book(tmp_path) as book:
            loaded = await _load(book, [book.e_id])
        voices = loaded[book.e_id]
        assert _spans(voices["geography"]) == [(D0, CHANGE - timedelta(days=1), {"ITA": Decimal("1")}), (CHANGE, END, None)]
        assert not voices.get("sector"), "no sector row: the voice is absent (or empty)"


class TestTheEngineAllocation:
    async def test_classification_params_alone_are_unknown(self, tmp_path):
        """C has classification_params (USA, Energy) and no profile row: its value goes to Unknown in both dimensions."""
        async with _private_book(tmp_path) as book:
            result = await _calculate(book)
        for day in _days(D1, END):
            state = result.daily_states.state_on(day)
            assert state.by_asset.get(book.c_id) == C_VALUE, f"precondition {day}: C valued 450"
            assert state.by_geography.get("Unknown") == C_VALUE, f"{day}: by_geography {dict(state.by_geography)}"
            assert state.by_sector.get("Unknown") == C_VALUE and "Energy" not in state.by_sector, f"{day}: by_sector {dict(state.by_sector)}"

    async def test_the_profile_gives_the_countries_and_sectors_of_each_day(self, tmp_path):
        async with _private_book(tmp_path) as book:
            result = await _calculate(book)
        for day in _days(D1, END):
            state = result.daily_states.state_on(day)
            assert state.by_asset.get(book.p_id) == P_VALUE, f"precondition {day}: P valued 1100"
            if day < CHANGE:
                expected = {"USA": P_VALUE, "Unknown": C_VALUE}
            else:
                expected = {"USA": P_VALUE * Decimal("0.6"), "JPN": P_VALUE * Decimal("0.4"), "Unknown": C_VALUE}
            assert dict(state.by_geography) == expected, f"{day}: by_geography {dict(state.by_geography)}"
            assert {key: value for key, value in state.by_sector.items() if key != "Liquidity"} == {"Technology": P_VALUE, "Unknown": C_VALUE}, f"{day}"

    async def test_the_change_day_opens_a_segment(self, tmp_path):
        async with _private_book(tmp_path) as book:
            result = await _calculate(book)
        starts = [segment.start for segment in result.daily_states.segments]
        # Without D2 the segments start on D0, D1 and the day the prices turn stale (D1 + the threshold, after CHANGE).
        assert CHANGE in starts, f"the geography change on {CHANGE} (no movement, no quote) opens a segment: {starts}"


class TestTheEngineCache:
    """The engine keeps a whole result for 24 hours under a key of what it read (transactions, prices, rates, splits,
    access): the profile rows of the held assets' countries and sectors are part of it, so a new row, or a forgotten one,
    gives a new result at the next call, not the cached one."""

    async def test_a_new_profile_row_and_a_forgotten_one_give_a_new_result(self, tmp_path):
        async with _private_book(tmp_path) as book:
            first = await _calculate(book)
            assert dict(first.daily_states.state_on(END).by_geography) == {"USA": P_VALUE * Decimal("0.6"), "JPN": P_VALUE * Decimal("0.4"), "Unknown": C_VALUE}, "precondition"
            again = await _calculate(book)
            assert again is first, "precondition: the same reads give the cached result"

            async with AsyncSession(book.engine, expire_on_commit=False) as session:
                session.add(_profile_row(book.p_id, "geography", {"JPN": "1"}, END))
                await session.commit()
            after_write = await _calculate(book)
            assert dict(after_write.daily_states.state_on(END).by_geography) == {"JPN": P_VALUE, "Unknown": C_VALUE}, "a new row is read at the next call"

            async with AsyncSession(book.engine, expire_on_commit=False) as session:
                await session.execute(delete(AssetProfileUpdate).where(AssetProfileUpdate.asset_id == book.p_id, AssetProfileUpdate.key == "geography", AssetProfileUpdate.read_on >= CHANGE))
                await session.commit()
            after_forget = await _calculate(book)
            assert dict(after_forget.daily_states.state_on(END).by_geography) == {"USA": P_VALUE, "Unknown": C_VALUE}, "forgotten rows are forgotten at the next call"
