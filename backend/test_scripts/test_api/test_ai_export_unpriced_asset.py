"""E-AI503 — an AI Export snapshot over a held asset with no stored price is built, not refused with a 503.

Workstream E, release 1.3. What the developer saw on the nightly: AI Export → Export data → «Portfolio asset history»
(``portfolio.asset_history``, compact, 3 months, brokers [1, 2]) answered 503 ``snapshot_source_failure`` on
``portfolio.technical_prices``, with no ``reason_code``, while broker [1] alone answered 200. Broker 2 held a CROWDFUND
with no price row, no provider and one BUY.

TODAY (HEAD ``70ad4cec1``). The valuation gives a held asset with no stored price a value (its trade mark, or its book
cost), so the asset belongs to the eligible technical universe: not fully sold, a non-zero end value.
``AssetSourceManager.get_prices_bulk`` answers it ``FAPriceQueryResult(prices=[])`` — not ``None`` — and the builders of
``portfolio.technical_prices``, ``broker.technical_prices`` and ``asset.ohlc_returns`` write
``coherent_price_currency(result)``, ``None`` for an empty or mixed-currency series, into a required ``CurrencyCode``:
a ValidationError, a ``RequiredComponentBuildError``, the 503. Trying again never helps.

THE CONTRACT (plan, «E-AI503.5»). Portfolio and broker: the asset leaves ``assets`` for ``uncovered_assets``
(``asset_id``, ``portfolio_weight_ratio``, ``reason_code``; ordered by id), counted in ``eligible_asset_count`` and not
in ``covered_asset_count``. Single asset: ``asset.ohlc_returns`` has a null ``currency`` and a ``reason_code``. The three
components go from version 1 to 2.

THE RULE (developer, 19/10/2026): the criterion is ALWAYS the points the price history returns, NEVER the asset type.
A CROWDFUND without prices is one case among many: any asset may have none. So the book holds an ETF and a CROWDFUND on
each side, priced and unpriced, and the single-asset case runs for both types.

THE BOOK, on a private SQLite file under ``tmp_path``: one user, OWNER of brokers B1 and B2 (share 1). Every asset and
every amount is in EUR: no exchange rate is involved.

- On B1, ``ETF_PRICED`` (ETF) and ``CROWD_PRICED`` (CROWDFUND), with a close on every weekday from January 2017 to the
  period end: well before the asset bundle's longest warm-up (EMA 200, 1200 sessions: about 2400 calendar days).
- On B2, ``ETF_UNPRICED`` (ETF) and ``CROWD_UNPRICED`` (CROWDFUND): no price row, no provider.
- Each asset is held through one EUR deposit and one BUY in January 2024. The period is 1 April – 30 June 2024, in EUR,
  at the compact detail level.

The cases:

- UPA-01, precondition (green today): both unpriced assets are eligible in the report the AI Export reads, and the
  price history holds no row for them.
- UPA-02, barrier (green today): ``portfolio.asset_history`` on B1 alone is 200.
- UPA-03, red until E-AI503: on B1 and B2 it is 200, the unpriced assets uncovered with ``no_stored_price``.
- UPA-04, red until E-AI503: ``broker.asset_history`` on B2 is 200, every asset uncovered.
- UPA-05, red until E-AI503, for the ETF and the CROWDFUND: ``asset.market_history`` is 200, ``asset.ohlc_returns``
  with a null currency.

E-23 (plan, «E-23.2»): an asset with prices stored in one currency but none inside the period — the price history
returns only carries of its last close — is uncovered as ``no_price_in_period``. Today (HEAD ``1ef19d8dc``) it passes as
covered: it stays in ``assets`` with every bucket empty, and ``asset.ohlc_returns`` gives no reason. The contract:
portfolio and broker move it from ``assets`` to ``uncovered_assets`` with ``currency``, ``last_close`` and
``last_close_date`` (the last close stored before the period), three fields null for the other two reasons; counted
eligible, not covered. Single asset: ``asset.ohlc_returns`` keeps the currency, says ``no_price_in_period``, and its
``price_gaps`` is one gap over the whole period after that close. Again on the points, never on the type. THE STALE BOOK
(fixture ``stale_book``): the book plus B3, owned by the same user, holding ``ETF_STALE`` (ETF) and ``CROWD_STALE``
(CROWDFUND), each with a close on every weekday from January 2017 to Friday 15 March 2024 — two weeks before the period,
none inside it — and the same EUR deposit and BUY in January 2024.

- UPA-06, red until E-23: ``portfolio.asset_history`` on B1, B2 and B3 is 200, the stale pair uncovered as
  ``no_price_in_period`` with the close of 15 March 2024, the unpriced pair as ``no_stored_price`` with nulls.
- UPA-07, red until E-23, for the ETF and the CROWDFUND: ``asset.market_history`` on a stale asset is 200, its
  ``asset.ohlc_returns`` in EUR with ``no_price_in_period`` and one gap over the whole period.

Isolation: PURE with respect to the lane. The real AI Export router runs in process (httpx ``ASGITransport``) on an app
of the test's own, with the real ``AiExportSnapshotService``, ``PortfolioService`` and ``get_prices_bulk``. The session
dependency opens sessions on the private file (the app schema by ``create_all``, NullPool, the engine disposed at
teardown) and the current user is the book's. The portfolio L2, WAC and engine blob caches are process-global, and every
private book's user has the same id: they are emptied before and after each test. The market holiday table is an empty
one (built for real it takes a QuantLib process). No lane database, no server, no network, no sleep.

Runs in ``./dev.py test api ai-export-unpriced-asset``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.api.v1.ai_export import router
from backend.app.api.v1.auth import get_current_user
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_session_generator
from backend.app.schemas.ai_export_runtime import (
    AI_EXPORT_CATALOG_VERSION,
    AiExportAssetSnapshotRequest,
    AiExportBrokerSnapshotRequest,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportPortfolioSnapshotRequest,
)
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PortfolioReportQuery
from backend.app.services import portfolio_service as portfolio_service_module
from backend.app.services.ai_export.components import technical_shared
from backend.app.services.ai_export.datasets.catalog import build_dataset_registry
from backend.app.services.assets import price_query
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.risk import service as risk_service_module

EUR = "EUR"
PERIOD_START = date(2024, 4, 1)
PERIOD_END = date(2024, 6, 30)
CLOSES_FROM = date(2017, 1, 2)
DEPOSIT_DAY = date(2024, 1, 15)
BUY_DAY = date(2024, 1, 16)
TIMEOUT = 120.0
DATASETS = build_dataset_registry()

# (label, broker, asset type, has closes, quantity bought, EUR paid; the same EUR deposited the day before)
_HOLDINGS = (
    ("ETF_PRICED", "B1", AssetType.ETF, True, "10", "1000"),
    ("CROWD_PRICED", "B1", AssetType.CROWDFUND, True, "20", "2000"),
    ("ETF_UNPRICED", "B2", AssetType.ETF, False, "30", "3000"),
    ("CROWD_UNPRICED", "B2", AssetType.CROWDFUND, False, "40", "4000"),
)
PRICED = ("ETF_PRICED", "CROWD_PRICED")
UNPRICED = ("ETF_UNPRICED", "CROWD_UNPRICED")

# E-23: the last close stored for the stale assets, a Friday two weeks before the period
STALE_LAST_CLOSE = date(2024, 3, 15)

# E-23: (label, asset type, quantity bought, EUR paid; the same EUR deposited the day before), all on B3, each with a close
# on every weekday from CLOSES_FROM to STALE_LAST_CLOSE and none after
_STALE_HOLDINGS = (
    ("ETF_STALE", AssetType.ETF, "50", "5000"),
    ("CROWD_STALE", AssetType.CROWDFUND, "60", "6000"),
)
STALE = ("ETF_STALE", "CROWD_STALE")


# =============================================================================
# THE BOOK — a private SQLite file
# =============================================================================


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    user_id: int
    broker_ids: dict[str, int]
    asset_ids: dict[str, int]


def _weekday_closes() -> list[tuple[date, Decimal]]:
    """(day, close) on every weekday from CLOSES_FROM to PERIOD_END, a different close each day, around the BUY price."""
    days = (CLOSES_FROM + timedelta(days=offset) for offset in range((PERIOD_END - CLOSES_FROM).days + 1))
    return [(day, Decimal("100") + Decimal(index % 9) / 4) for index, day in enumerate(day for day in days if day.weekday() < 5)]


async def _seed(engine: AsyncEngine) -> _Book:
    """The book, owned by a new user, committed to the private file."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username="e_ai503_unpriced", email="e_ai503_unpriced@test.com", hashed_password="fakehash", is_active=True)
        brokers = {label: Broker(name=f"E-AI503 unpriced asset {label}") for label in ("B1", "B2")}
        assets = {label: Asset(display_name=f"E-AI503 {label}", currency=EUR, asset_type=asset_type) for label, _broker, asset_type, _priced, _quantity, _paid in _HOLDINGS}
        session.add_all([user, *brokers.values(), *assets.values()])
        await session.flush()
        session.add_all([BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")) for broker in brokers.values()])
        for label, broker, _asset_type, priced, quantity, paid in _HOLDINGS:
            asset_id, broker_id = assets[label].id, brokers[broker].id
            session.add(Transaction(broker_id=broker_id, asset_id=None, type=TransactionType.DEPOSIT, date=DEPOSIT_DAY, quantity=Decimal("0"), amount=Decimal(paid), currency=EUR))
            session.add(Transaction(broker_id=broker_id, asset_id=asset_id, type=TransactionType.BUY, date=BUY_DAY, quantity=Decimal(quantity), amount=-Decimal(paid), currency=EUR))
            if priced:
                session.add_all(PriceHistory(asset_id=asset_id, date=day, open=close, high=close, low=close, close=close, currency=EUR, source_plugin_key="MANUAL") for day, close in _weekday_closes())
        await session.commit()
        return _Book(engine=engine, user_id=user.id, broker_ids={label: broker.id for label, broker in brokers.items()}, asset_ids={label: asset.id for label, asset in assets.items()})


def _ids(book: _Book, labels: tuple[str, ...]) -> list[int]:
    """The asset ids of ``labels`` in id order, the order the payloads list them in."""
    return sorted(book.asset_ids[label] for label in labels)


def _stale_closes() -> list[tuple[date, Decimal]]:
    """E-23: a stale asset's closes, `_weekday_closes` up to STALE_LAST_CLOSE: none inside the period."""
    return [(day, close) for day, close in _weekday_closes() if day <= STALE_LAST_CLOSE]


async def _seed_stale(book: _Book) -> _Book:
    """E-23: B3, owned by the book's user, holding the two stale assets, committed to the book's file; the book with them."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        broker = Broker(name="E-23 stale prices B3")
        assets = {label: Asset(display_name=f"E-23 {label}", currency=EUR, asset_type=asset_type) for label, asset_type, _quantity, _paid in _STALE_HOLDINGS}
        session.add_all([broker, *assets.values()])
        await session.flush()
        session.add(BrokerUserAccess(broker_id=broker.id, user_id=book.user_id, role=UserRole.OWNER, share_percentage=Decimal("1")))
        for label, _asset_type, quantity, paid in _STALE_HOLDINGS:
            asset_id = assets[label].id
            session.add(Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=DEPOSIT_DAY, quantity=Decimal("0"), amount=Decimal(paid), currency=EUR))
            session.add(Transaction(broker_id=broker.id, asset_id=asset_id, type=TransactionType.BUY, date=BUY_DAY, quantity=Decimal(quantity), amount=-Decimal(paid), currency=EUR))
            session.add_all(PriceHistory(asset_id=asset_id, date=day, open=close, high=close, low=close, close=close, currency=EUR, source_plugin_key="MANUAL") for day, close in _stale_closes())
        await session.commit()
        return _Book(
            engine=book.engine,
            user_id=book.user_id,
            broker_ids={**book.broker_ids, "B3": broker.id},
            asset_ids={**book.asset_ids, **{label: asset.id for label, asset in assets.items()}},
        )


# =============================================================================
# THE ROUTE — the real AI Export router, in process
# =============================================================================


def _app(book: _Book) -> FastAPI:
    """The real AI Export router mounted under /api/v1, its sessions on the book's file, its current user the book's."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(book.engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=book.user_id)
    return app


async def _post_snapshot(book: _Book, request: AiExportPortfolioSnapshotRequest | AiExportBrokerSnapshotRequest | AiExportAssetSnapshotRequest) -> httpx.Response:
    """``POST /api/v1/ai-export/snapshot`` with the typed request as JSON.

    A field the request leaves unset stays off the wire (``exclude_unset``), as the frontend omits an empty broker scope:
    ``broker_ids: []`` would be a 422.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app(book)), base_url="http://e-ai503.test", timeout=TIMEOUT) as client:
        return await client.post("/api/v1/ai-export/snapshot", json=request.model_dump(mode="json", exclude_unset=True))


def _common(dataset_id: str) -> dict:
    """The fields every domain's request shares: the dataset at its catalog version, compact, the period, EUR."""
    return {
        "selection": AiExportDatasetSelection(kind="dataset", id=dataset_id, version=DATASETS.get(dataset_id).version),
        "detail_level": AiExportDetailLevel.COMPACT,
        "period": {"start": PERIOD_START, "end": PERIOD_END},
        "target_currency": EUR,
        "expected_catalog_version": AI_EXPORT_CATALOG_VERSION,
    }


def _portfolio_request(book: _Book, *broker_labels: str) -> AiExportPortfolioSnapshotRequest:
    return AiExportPortfolioSnapshotRequest(domain="portfolio", broker_ids=[book.broker_ids[label] for label in broker_labels], **_common("portfolio.asset_history"))


def _broker_request(book: _Book, broker_label: str) -> AiExportBrokerSnapshotRequest:
    return AiExportBrokerSnapshotRequest(domain="broker", broker_id=book.broker_ids[broker_label], **_common("broker.asset_history"))


def _asset_request(book: _Book, asset_label: str) -> AiExportAssetSnapshotRequest:
    return AiExportAssetSnapshotRequest(domain="asset", asset_id=book.asset_ids[asset_label], **_common("asset.market_history"))


def _answered(response: httpx.Response) -> str:
    return f"POST /ai-export/snapshot answered {response.status_code}: {response.text}"


def _section(response: httpx.Response, component_id: str) -> dict:
    """The section of ``component_id`` in a snapshot, found by its id."""
    sections = {section["component_id"]: section for section in response.json()["sections"]}
    assert component_id in sections, f"no {component_id} section among {sorted(sections)}"
    return sections[component_id]


# =============================================================================
# FIXTURES
# =============================================================================


def _clear_portfolio_caches() -> None:
    """Empty the report (layer 2), WAC and engine blob caches."""
    portfolio_service_module._portfolio_l2_cache.clear()
    portfolio_service_module._wac_cache.clear()
    portfolio_engine_module._portfolio_blob_cache.clear()


async def _no_market_holidays() -> frozenset[date]:
    return frozenset()


@pytest.fixture(autouse=True)
def no_cached_portfolio(request: pytest.FixtureRequest) -> None:
    """No report, WAC or engine blob crosses into or out of a test: a cached one would answer for another book."""
    _clear_portfolio_caches()
    request.addfinalizer(_clear_portfolio_caches)


@pytest.fixture(autouse=True)
def no_market_holidays(monkeypatch: pytest.MonkeyPatch) -> None:
    """The market holiday table, empty, wherever a snapshot awaits it: the prices' signals, the drawdown's risk run.

    From E-23 the gaps of the technical price series read it too, through ``technical_shared.ensure_market_holidays``, a
    name that module has only from E-23 on: ``raising=False`` until then. Without it, every snapshot of this file with a
    run of empty buckets to judge (a weekend in the daily buckets is one) would build the real table, in a QuantLib
    process.
    """
    monkeypatch.setattr(price_query, "ensure_market_holidays", _no_market_holidays)
    monkeypatch.setattr(risk_service_module, "ensure_market_holidays", _no_market_holidays)
    monkeypatch.setattr(technical_shared, "ensure_market_holidays", _no_market_holidays, raising=False)


@pytest_asyncio.fixture
async def book(tmp_path: Path) -> AsyncIterator[_Book]:
    """The book on a private SQLite file under tmp_path, with the whole ORM schema; the engine disposed after."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'e_ai503_unpriced_asset.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def stale_book(book: _Book) -> _Book:
    """E-23: the book plus B3 and its two stale assets, on the same private file, disposed with it."""
    return await _seed_stale(book)


# =============================================================================
# THE CASES
# =============================================================================


@pytest.mark.asyncio
async def test_upa01_precondition_the_unpriced_assets_are_held_valued_and_have_no_stored_price(book):
    """UPA-01 — precondition, green today: the bug's own.

    In the report the AI Export reads (both brokers; summary, history, breakdown and period contribution, as its loader
    asks), each unpriced asset is eligible for the technical universe: not fully sold, an end value neither None nor 0.
    The price history holds no row for either; it does for the priced ones.
    """
    query = PortfolioReportQuery(
        broker_ids=[book.broker_ids["B1"], book.broker_ids["B2"]],
        date_range=OpenDateRangeModel(start=PERIOD_START, end=PERIOD_END),
        target_currency=EUR,
        include_summary=True,
        include_history=True,
        include_allocation_history=False,
        include_breakdown=True,
        include_positions_contribution=True,
    )
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        report = await PortfolioService(session).get_report(book.user_id, query)
        stored = {label: await session.scalar(select(func.count()).select_from(PriceHistory).where(PriceHistory.asset_id == asset_id)) for label, asset_id in book.asset_ids.items()}

    assert report.positions_contribution is not None, "the report has no period contribution"
    for label in UNPRICED:
        legs = [leg for leg in report.positions_contribution.positions if leg.asset_id == book.asset_ids[label]]
        assert legs, f"{label}: no period contribution"
        assert all(not leg.is_fully_sold and leg.end_value is not None and leg.end_value != 0 for leg in legs), f"{label} is not eligible: {[(leg.is_fully_sold, leg.end_value) for leg in legs]}"
    assert {label: stored[label] for label in UNPRICED} == dict.fromkeys(UNPRICED, 0)
    assert all(stored[label] > 0 for label in PRICED), stored


@pytest.mark.asyncio
async def test_upa02_barrier_the_priced_broker_alone_builds_the_portfolio_asset_history(book):
    """UPA-02 — barrier, green today: as the developer saw, ``portfolio.asset_history`` on B1 alone is 200.

    Both of B1's assets are priced: they are the ``assets`` of ``portfolio.technical_prices``, 2 covered of 2 eligible.
    Only today's fields are read.
    """
    response = await _post_snapshot(book, _portfolio_request(book, "B1"))

    assert response.status_code == 200, _answered(response)
    payload = _section(response, "portfolio.technical_prices")["payload"]
    assert [asset["asset_id"] for asset in payload["assets"]] == _ids(book, PRICED)
    assert (payload["eligible_asset_count"], payload["covered_asset_count"]) == (2, 2)


@pytest.mark.asyncio
async def test_upa03_both_brokers_build_with_the_unpriced_assets_listed_as_uncovered(book):
    """UPA-03 — red until E-AI503: ``portfolio.asset_history`` on B1 and B2 is 200.

    Today it is the developer's 503 ``snapshot_source_failure`` on ``portfolio.technical_prices``. Its section, at
    version 2, keeps the priced ETF and CROWDFUND in ``assets`` and lists the unpriced ETF and CROWDFUND in
    ``uncovered_assets``, in id order, each ``no_stored_price``: 4 eligible, 2 covered. Each entry of both lists carries
    its NAV weight, so together they weigh the whole universe.
    """
    response = await _post_snapshot(book, _portfolio_request(book, "B1", "B2"))

    assert response.status_code == 200, _answered(response)
    section = _section(response, "portfolio.technical_prices")
    payload = section["payload"]
    assert section["component_version"] == 2
    assert [asset["asset_id"] for asset in payload["assets"]] == _ids(book, PRICED)
    assert [(gap["asset_id"], gap["reason_code"]) for gap in payload["uncovered_assets"]] == [(asset_id, "no_stored_price") for asset_id in _ids(book, UNPRICED)]
    assert (payload["eligible_asset_count"], payload["covered_asset_count"]) == (4, 2)
    assert sum(entry["portfolio_weight_ratio"] for entry in (*payload["assets"], *payload["uncovered_assets"])) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_upa04_the_unpriced_broker_builds_with_every_asset_uncovered(book):
    """UPA-04 — red until E-AI503: ``broker.asset_history`` on B2, both of whose assets have no stored price, is 200.

    Its ``broker.technical_prices``, at version 2, has no series and both assets uncovered, in id order, each
    ``no_stored_price``: 0 covered of 2 eligible.
    """
    response = await _post_snapshot(book, _broker_request(book, "B2"))

    assert response.status_code == 200, _answered(response)
    section = _section(response, "broker.technical_prices")
    payload = section["payload"]
    assert section["component_version"] == 2
    assert payload["assets"] == []
    assert [(gap["asset_id"], gap["reason_code"]) for gap in payload["uncovered_assets"]] == [(asset_id, "no_stored_price") for asset_id in _ids(book, UNPRICED)]
    assert (payload["eligible_asset_count"], payload["covered_asset_count"]) == (2, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("label", [pytest.param("ETF_UNPRICED", id="etf"), pytest.param("CROWD_UNPRICED", id="crowdfund")])
async def test_upa05_an_unpriced_asset_market_history_builds_with_a_null_currency_whatever_its_type(book, label):
    """UPA-05 — red until E-AI503, for an ETF and a CROWDFUND alike: the points decide, never the type.

    ``asset.market_history`` on the unpriced asset is 200, not today's 503 ``snapshot_source_failure``. Its
    ``asset.ohlc_returns``, at version 2, has a null ``currency`` and the reason ``no_stored_price``.
    """
    response = await _post_snapshot(book, _asset_request(book, label))

    assert response.status_code == 200, _answered(response)
    section = _section(response, "asset.ohlc_returns")
    assert section["component_version"] == 2
    assert (section["payload"]["currency"], section["payload"]["reason_code"]) == (None, "no_stored_price")


# red until E-23
@pytest.mark.asyncio
async def test_upa06_the_stale_assets_are_uncovered_with_no_price_in_period_and_their_last_close(stale_book):
    """UPA-06 — red until E-23: ``portfolio.asset_history`` on B1, B2 and B3 is 200, the stale assets uncovered.

    The stale ETF and CROWDFUND have closes stored up to 15 March 2024 and none in the period: inside it the price
    history returns only carries of that close. Pins, in ``portfolio.technical_prices``: the priced pair keeps its
    series; ``uncovered_assets`` lists, in id order, the unpriced pair as ``no_stored_price`` with ``currency``,
    ``last_close`` and ``last_close_date`` present and null, and the stale pair as ``no_price_in_period`` in EUR with the
    close of 15 March 2024 and its date; 6 eligible, 2 covered; together the two lists still weigh the whole universe.
    Red until E-23: today the stale pair stays in ``assets``, covered, with every bucket empty.
    """
    last_day, last_close = _stale_closes()[-1]
    assert last_day == STALE_LAST_CLOSE, "premise: the stale closes end on STALE_LAST_CLOSE"
    expected = {stale_book.asset_ids[label]: ("no_stored_price", None, None, None) for label in UNPRICED} | {stale_book.asset_ids[label]: ("no_price_in_period", EUR, pytest.approx(float(last_close)), last_day.isoformat()) for label in STALE}

    response = await _post_snapshot(stale_book, _portfolio_request(stale_book, "B1", "B2", "B3"))

    assert response.status_code == 200, _answered(response)
    payload = _section(response, "portfolio.technical_prices")["payload"]
    assert [asset["asset_id"] for asset in payload["assets"]] == _ids(stale_book, PRICED)
    assert [gap["asset_id"] for gap in payload["uncovered_assets"]] == sorted(expected)
    assert {gap["asset_id"]: (gap["reason_code"], *(gap.get(key, "<absent>") for key in ("currency", "last_close", "last_close_date"))) for gap in payload["uncovered_assets"]} == expected
    assert (payload["eligible_asset_count"], payload["covered_asset_count"]) == (6, 2)
    assert sum(entry["portfolio_weight_ratio"] for entry in (*payload["assets"], *payload["uncovered_assets"])) == pytest.approx(1.0)


# red until E-23
@pytest.mark.asyncio
@pytest.mark.parametrize("label", [pytest.param("ETF_STALE", id="etf"), pytest.param("CROWD_STALE", id="crowdfund")])
async def test_upa07_a_stale_asset_market_history_says_no_price_in_period_whatever_its_type(stale_book, label):
    """UPA-07 — red until E-23, for an ETF and a CROWDFUND alike: the points decide, never the type.

    ``asset.market_history`` on a stale asset is 200. Pins, in its ``asset.ohlc_returns`` (version 2): the currency
    stays, EUR, with the reason ``no_price_in_period``; every bucket empty and no latest close or date; ``price_gaps``
    is one gap over the whole period, 1 April - 30 June 2024, after the close stored on 15 March 2024. Red until E-23:
    today the reason is null and there is no ``price_gaps``.
    """
    last_day, last_close = _stale_closes()[-1]
    assert last_day == STALE_LAST_CLOSE, "premise: the stale closes end on STALE_LAST_CLOSE"

    response = await _post_snapshot(stale_book, _asset_request(stale_book, label))

    assert response.status_code == 200, _answered(response)
    section = _section(response, "asset.ohlc_returns")
    payload = section["payload"]
    assert section["component_version"] == 2
    assert (payload["currency"], payload["reason_code"]) == (EUR, "no_price_in_period")
    assert payload["buckets"], "the bucket plan still covers the period"
    assert all(bucket["observation_count"] == 0 for bucket in payload["buckets"])
    assert (payload["latest_close"], payload["latest_date"]) == (None, None)
    assert payload.get("price_gaps") == [
        {
            "start_date": PERIOD_START.isoformat(),
            "end_date": PERIOD_END.isoformat(),
            "calendar_days": (PERIOD_END - PERIOD_START).days + 1,
            "last_value": pytest.approx(float(last_close)),
            "last_value_date": last_day.isoformat(),
        }
    ]
