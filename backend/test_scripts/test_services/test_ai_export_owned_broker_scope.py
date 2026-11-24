"""78 L10b — an export that names no broker reads the brokers the user owns, each at the user's share.

WHAT. Decision D13 of the developer, (a) + (c1):
- an Asset or FX export without a broker list counts only the brokers the user owns (role owner, share above zero, the
  Dashboard's rule), each for the user's share; a broker only shared with the user (viewer, editor) is someone else's;
- the broker-vs-portfolio comparison compares the broker with the brokers the user owns, each whole (R11);
- an empty scope means no broker, never «every accessible broker». A user who owns none gets the market-only
  selections, and a typed refusal (`no_owned_brokers`) for every selection that reads positions, exposure or a
  portfolio (the coordinator's choice R, 24/11/2026).

WHY. Before L10b `prepare_request` filled a request without brokers with every accessible broker, so an asset export
counted the positions in brokers only shared with the user, and the comparison measured the broker against them.

THE BOOK, on a private SQLite file under ``tmp_path``. Everything is in EUR at 100 a unit, except a USD cash balance
in every broker:
- user U: B1 owner at share 1, B2 owner at share 0.5, B3 owner at share 0 (counts nothing: not U's), B4 viewer, B5
  editor. Owned: B1 and B2.
- user S: B3 owner at share 0, B4 viewer, B5 editor. S owns no broker.
- every broker: DEPOSIT 10 000 EUR, DEPOSIT 1 000 USD, BUY 10 ``ASSET_X`` for 1 000 EUR. B4 alone also buys 5
  ``ASSET_Y``: an asset held only in a broker shared with U.
- ``ASSET_X`` and ``ASSET_Y`` close at 100 on every weekday from January 2023 to the period end; USD/EUR is 0.9.

The cases:
- OS-01: U's asset export without a list → scope (B1, B2), source OWNED; the position counts B1 whole and B2 at half
  (10 + 5 = 15), no shared broker in the legs; the label is OWNED_BROKERS.
- OS-02: an asset held only in a shared broker has no position for U (quantity 0, no leg).
- OS-03: an explicit list (B1, B4) is the user's choice: REQUESTED_BROKERS, and B4 counts.
- OS-04: U's FX exposure without a list → only B1 and B2, the USD cash 1 000 + 500.
- OS-05: the comparison on an owned broker: B1 whole over B1 + B2 whole = 50 %, the shared brokers left out.
- OS-06: the comparison on a shared broker: unavailable, `broker_not_owned`.
- OS-07: S's selections that read brokers are refused with `no_owned_brokers`, before any build.
- OS-08: S's market-only selections stay available, with an empty scope, and an analysis lists the suggested datasets
  S cannot select (`unavailable_dataset_ids`).
- OS-09: each of S's four market-only selections builds whole and names no broker: none in the entity directory,
  none anywhere in the response; the two analyses list the datasets S cannot select.

Isolation: PURE with respect to the lane. The real ``AiExportSnapshotService``, ``PortfolioService`` and the asset/FX
loaders run in process on the private file (NullPool, the engine disposed at teardown). The portfolio caches are
process-global and every private book's user has small ids: they are emptied before and after each test. The market
holiday table is an empty one. No lane database, no server, no network, no sleep.

Runs in ``./dev.py test services ai-export``; alone:
``pipenv run python -m pytest -q backend/test_scripts/test_services/test_ai_export_owned_broker_scope.py``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.base import SQLModel  # every model, for create_all
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.schemas.ai_export_runtime import (
    AI_EXPORT_CATALOG_VERSION,
    AiExportAnalysisSelection,
    AiExportAssetSnapshotRequest,
    AiExportBrokerSnapshotRequest,
    AiExportDatasetSelection,
    AiExportDetailLevel,
    AiExportFxSnapshotRequest,
    AiExportPortfolioSnapshotRequest,
)
from backend.app.services.ai_export.components.broker_concentration_context import REASON_BROKER_NOT_OWNED
from backend.app.services.ai_export.components.broker_scope import REASON_NO_OWNED_BROKERS
from backend.app.services.ai_export.components.types import BrokerScopeSource
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.app.services.ai_export.runtime_service import AiExportSelectionNotApplicableError, AiExportSnapshotService
from backend.app.services.assets import price_query
from backend.app.services.portfolio import report as report_module
from backend.app.services.portfolio import wac as wac_module

EUR = "EUR"
USD = "USD"
PERIOD_START = date(2024, 4, 1)
PERIOD_END = date(2024, 6, 28)  # a Friday
CLOSES_FROM = date(2023, 1, 2)
DEPOSIT_DAY = date(2024, 1, 15)
BUY_DAY = date(2024, 1, 16)
USD_EUR = Decimal("0.9")

# (label, role, share) of U and of S
_U_ACCESSES = (
    ("B1", UserRole.OWNER, Decimal("1")),
    ("B2", UserRole.OWNER, Decimal("0.5")),
    ("B3", UserRole.OWNER, Decimal("0")),
    ("B4", UserRole.VIEWER, Decimal("0")),
    ("B5", UserRole.EDITOR, Decimal("0")),
)
_S_ACCESSES = (
    ("B3", UserRole.OWNER, Decimal("0")),
    ("B4", UserRole.VIEWER, Decimal("0")),
    ("B5", UserRole.EDITOR, Decimal("0")),
)

# The selections that read the scope's brokers, and the ones that read market data only (78 L10b classification)
_BROKER_READING = (
    ("asset", "asset.position_and_history"),
    ("asset", "asset.position_review"),
    ("fx", "fx.market_and_exposure"),
    ("fx", "fx.exposure_impact"),
    ("portfolio", "portfolio.overview_and_history"),
)
_MARKET_ONLY = (
    ("asset", "asset.market_history"),
    ("asset", "asset.market_analysis"),
    ("fx", "fx.market_history"),
    ("fx", "fx.pair_analysis"),
)


@dataclass(frozen=True)
class _Book:
    engine: AsyncEngine
    u_id: int
    s_id: int
    brokers: dict[str, int]
    broker_names: dict[str, str]
    assets: dict[str, int]


def _weekdays() -> list[date]:
    days = (CLOSES_FROM + timedelta(days=offset) for offset in range((PERIOD_END - CLOSES_FROM).days + 1))
    return [day for day in days if day.weekday() < 5]


async def _seed(engine: AsyncEngine) -> _Book:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        u = User(username="l10b_owned_u", email="l10b_owned_u@test.com", hashed_password="fakehash", is_active=True)
        s = User(username="l10b_owned_s", email="l10b_owned_s@test.com", hashed_password="fakehash", is_active=True)
        brokers = {label: Broker(name=f"L10b owned scope {label}") for label in ("B1", "B2", "B3", "B4", "B5")}
        assets = {
            "ASSET_X": Asset(display_name="L10b ASSET_X", currency=EUR, asset_type=AssetType.ETF),
            "ASSET_Y": Asset(display_name="L10b ASSET_Y", currency=EUR, asset_type=AssetType.STOCK),
        }
        session.add_all([u, s, *brokers.values(), *assets.values()])
        await session.flush()
        session.add_all(BrokerUserAccess(broker_id=brokers[label].id, user_id=u.id, role=role, share_percentage=share) for label, role, share in _U_ACCESSES)
        session.add_all(BrokerUserAccess(broker_id=brokers[label].id, user_id=s.id, role=role, share_percentage=share) for label, role, share in _S_ACCESSES)

        def cash(broker: Broker, currency: str, amount: str) -> Transaction:
            return Transaction(broker_id=broker.id, asset_id=None, type=TransactionType.DEPOSIT, date=DEPOSIT_DAY, quantity=Decimal("0"), amount=Decimal(amount), currency=currency)

        def buy(broker: Broker, asset: str, quantity: int) -> Transaction:
            return Transaction(broker_id=broker.id, asset_id=assets[asset].id, type=TransactionType.BUY, date=BUY_DAY, quantity=Decimal(quantity), amount=Decimal(-100 * quantity), currency=EUR)

        for broker in brokers.values():
            session.add_all([cash(broker, EUR, "10000"), cash(broker, USD, "1000"), buy(broker, "ASSET_X", 10)])
        session.add(buy(brokers["B4"], "ASSET_Y", 5))
        for asset in assets.values():
            session.add_all(PriceHistory(asset_id=asset.id, date=day, open=Decimal("100"), high=Decimal("100"), low=Decimal("100"), close=Decimal("100"), currency=EUR, source_plugin_key="MANUAL") for day in _weekdays())
        # FxRate stores the alphabetical pair: EUR/USD = 1 / 0.9
        session.add_all(FxRate(date=day, base=EUR, quote=USD, rate=Decimal(1) / USD_EUR, source="ECB") for day in [date(1990, 1, 1), *_weekdays()])
        await session.commit()
        return _Book(
            engine=engine,
            u_id=u.id,
            s_id=s.id,
            brokers={label: broker.id for label, broker in brokers.items()},
            broker_names={label: broker.name for label, broker in brokers.items()},
            assets={label: asset.id for label, asset in assets.items()},
        )


# =============================================================================
# REQUESTS
# =============================================================================


def _selection(service: AiExportSnapshotService, selection_id: str):
    try:
        dataset = service.dataset_registry.get(selection_id)
    except Exception:  # noqa: BLE001 — not a dataset: it is an analysis
        analysis = service.analysis_registry.get(selection_id)
        return AiExportAnalysisSelection(
            kind="analysis",
            id=analysis.analysis_id,
            version=analysis.version,
            instruction_template_id=analysis.instruction_template_id,
            instruction_template_version=analysis.instruction_template_version,
            response_contract_id=analysis.response_contract_id,
            response_contract_version=analysis.response_contract_version,
        )
    return AiExportDatasetSelection(kind="dataset", id=dataset.dataset_id, version=dataset.version)


def _request(service: AiExportSnapshotService, book: _Book, domain: str, selection_id: str, *broker_labels: str):
    common = {
        "selection": _selection(service, selection_id),
        "detail_level": AiExportDetailLevel.STANDARD,
        "period": {"start": PERIOD_START, "end": PERIOD_END},
        "target_currency": EUR,
        "expected_catalog_version": AI_EXPORT_CATALOG_VERSION,
    }
    brokers = {"broker_ids": [book.brokers[label] for label in broker_labels]} if broker_labels else {}
    if domain == "asset":
        return AiExportAssetSnapshotRequest(domain="asset", asset_id=book.assets["ASSET_X"], **brokers, **common)
    if domain == "fx":
        return AiExportFxSnapshotRequest(domain="fx", base_currency=USD, quote_currency=EUR, **brokers, **common)
    if domain == "portfolio":
        return AiExportPortfolioSnapshotRequest(domain="portfolio", **brokers, **common)
    raise AssertionError(domain)


async def _resolve(book: _Book, user_id: int, request, component_id: str):
    """`prepare_request` as the API runs it, then one component (with its dependencies) on the prepared scope."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        service = AiExportSnapshotService(session)
        prepared = await service.prepare_request(user_id, request)
        scope = prepared.scope
        context = BuildContext(service.component_registry, request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)
        section = await context.resolve(component_id, required=True)
        return scope, section.payload


# =============================================================================
# FIXTURES
# =============================================================================


def _clear_portfolio_caches() -> None:
    report_module._portfolio_l2_cache.clear()
    wac_module._wac_cache.clear()
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
    monkeypatch.setattr(price_query, "ensure_market_holidays", _no_market_holidays)


@pytest_asyncio.fixture
async def book(tmp_path: Path) -> AsyncIterator[_Book]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'l10b_owned_scope.sqlite'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield await _seed(engine)
    finally:
        await engine.dispose()


def _service_for_requests() -> AiExportSnapshotService:
    """A service only for its registries (selection identities); it never touches a session."""
    return AiExportSnapshotService(None)  # type: ignore[arg-type]


# =============================================================================
# U — owned brokers, at the user's share
# =============================================================================


@pytest.mark.asyncio
async def test_os01_an_asset_export_without_a_list_counts_the_owned_brokers_at_their_share(book):
    service = _service_for_requests()
    request = _request(service, book, "asset", "asset.position_and_history")

    scope, payload = await _resolve(book, book.u_id, request, "asset.position_scope")

    assert scope.broker_scope == tuple(sorted((book.brokers["B1"], book.brokers["B2"])))
    assert scope.broker_scope_source is BrokerScopeSource.OWNED
    legs = {leg["broker_id"]: Decimal(str(leg["quantity"])) for leg in payload["brokers"]}
    assert legs == {book.brokers["B1"]: Decimal("10"), book.brokers["B2"]: Decimal("5")}, "B1 whole, B2 at half; B3 (share 0), B4 and B5 (shared) out"
    assert Decimal(str(payload["total_quantity"])) == Decimal("15")
    assert payload["portfolio_role"]["broker_scope_mode"] == "OWNED_BROKERS"


@pytest.mark.asyncio
async def test_os02_an_asset_held_only_in_a_shared_broker_has_no_position(book):
    service = _service_for_requests()
    request = _request(service, book, "asset", "asset.position_and_history").model_copy(update={"asset_id": book.assets["ASSET_Y"]})

    _scope, payload = await _resolve(book, book.u_id, request, "asset.position_scope")

    assert payload["brokers"] == []
    assert payload["broker_count"] == 0
    assert Decimal(str(payload["total_quantity"])) == Decimal("0")


@pytest.mark.asyncio
async def test_os03_an_explicit_list_is_the_users_choice_and_may_hold_a_shared_broker(book):
    service = _service_for_requests()
    request = _request(service, book, "asset", "asset.position_and_history", "B1", "B4")

    scope, payload = await _resolve(book, book.u_id, request, "asset.position_scope")

    assert scope.broker_scope_source is BrokerScopeSource.REQUESTED
    assert {leg["broker_id"] for leg in payload["brokers"]} == {book.brokers["B1"], book.brokers["B4"]}
    assert payload["portfolio_role"]["broker_scope_mode"] == "REQUESTED_BROKERS"


@pytest.mark.asyncio
async def test_os04_an_fx_export_without_a_list_reads_the_owned_brokers_only(book):
    service = _service_for_requests()
    request = _request(service, book, "fx", "fx.market_and_exposure")

    _scope, payload = await _resolve(book, book.u_id, request, "fx.exposure_base_quote")

    owned = {book.brokers["B1"], book.brokers["B2"]}
    cash_rows = [row for row in payload["rows"] if row["kind"] == "cash"]
    assert cash_rows, payload["rows"]
    assert {row["broker_id"] for row in payload["rows"] if row["broker_id"] is not None} <= owned

    def cash(currency: str) -> Decimal:
        return sum((Decimal(str(row["native_amount"])) for row in cash_rows if row["linked_currency"] == currency), start=Decimal("0"))

    assert cash(USD) == Decimal("1500"), "USD cash: B1 1 000 whole, B2 1 000 at half; the shared brokers' 3 000 out"
    assert cash(EUR) == Decimal("13500"), "EUR cash after the buy: B1 9 000 whole, B2 9 000 at half"
    assert tuple(payload["broker_scope"]) == tuple(sorted(owned))


# =============================================================================
# The broker comparison (c1): owned brokers, whole
# =============================================================================


def _broker_request(service: AiExportSnapshotService, book: _Book, label: str) -> AiExportBrokerSnapshotRequest:
    dataset = next(spec for spec in service.dataset_registry if spec.domain.value == "broker" and "broker.concentration_comparison" in (*spec.required_component_ids, *spec.optional_component_ids))
    return AiExportBrokerSnapshotRequest(
        domain="broker",
        broker_id=book.brokers[label],
        selection=AiExportDatasetSelection(kind="dataset", id=dataset.dataset_id, version=dataset.version),
        detail_level=AiExportDetailLevel.STANDARD,
        period={"start": PERIOD_START, "end": PERIOD_END},
        target_currency=EUR,
        expected_catalog_version=AI_EXPORT_CATALOG_VERSION,
    )


@pytest.mark.asyncio
async def test_os05_the_comparison_of_an_owned_broker_is_against_the_owned_brokers_whole(book):
    service = _service_for_requests()

    _scope, payload = await _resolve(book, book.u_id, _broker_request(service, book, "B1"), "broker.concentration_comparison")

    assert payload["status"] == "ok", payload
    assert payload["amounts_basis"] == "owned_brokers_whole"
    # B1 whole (1 000) over B1 + B2 whole (2 000). Every accessible broker would read 1 000 / 5 500; B2 at its share
    # 1 000 / 1 500.
    assert Decimal(str(payload["broker_share_of_portfolio_market_value_percent"])).quantize(Decimal("0.01")) == Decimal("50.00")


@pytest.mark.asyncio
async def test_os06_the_comparison_of_a_shared_broker_is_unavailable(book):
    service = _service_for_requests()

    _scope, payload = await _resolve(book, book.u_id, _broker_request(service, book, "B4"), "broker.concentration_comparison")

    assert payload["status"] == "unavailable"
    assert payload["reason_code"] == REASON_BROKER_NOT_OWNED
    assert payload["portfolio_market_value"] is None


# =============================================================================
# S — owns no broker
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("domain", "selection_id"), _BROKER_READING)
async def test_os07_a_selection_that_reads_brokers_is_refused_when_the_user_owns_none(book, domain, selection_id):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        service = AiExportSnapshotService(session)
        with pytest.raises(AiExportSelectionNotApplicableError) as raised:
            await service.prepare_request(book.s_id, _request(service, book, domain, selection_id))
    assert raised.value.reason_code == REASON_NO_OWNED_BROKERS


@pytest.mark.asyncio
@pytest.mark.parametrize(("domain", "selection_id"), _MARKET_ONLY)
async def test_os08_a_market_only_selection_stays_available_with_no_broker(book, domain, selection_id):
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        service = AiExportSnapshotService(session)
        prepared = await service.prepare_request(book.s_id, _request(service, book, domain, selection_id))
        unavailable = service._unavailable_dataset_ids(prepared)
    assert prepared.scope.broker_scope == ()
    assert prepared.scope.broker_scope_source is BrokerScopeSource.OWNED
    expected = {"asset.market_analysis": ("asset.position_and_history",), "fx.pair_analysis": ("fx.market_and_exposure",)}.get(selection_id, ())
    assert unavailable == expected


@pytest.mark.asyncio
async def test_os08b_an_owner_gets_every_suggestion(book):
    """U owns brokers: nothing is unavailable, the analysis suggests its datasets as before."""
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        service = AiExportSnapshotService(session)
        prepared = await service.prepare_request(book.u_id, _request(service, book, "asset", "asset.market_analysis"))
        assert service._unavailable_dataset_ids(prepared) == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(("domain", "selection_id"), _MARKET_ONLY)
async def test_os09_a_market_only_export_builds_and_names_no_broker(book, domain, selection_id):
    """Every market-only selection builds whole for a user who owns no broker: no component reads the empty scope.

    A broker reader missing from the classification would not be refused: it would fail the build (503).
    """
    async with AsyncSession(book.engine, expire_on_commit=False) as session:
        service = AiExportSnapshotService(session)
        response = await service.build_snapshot(book.s_id, _request(service, book, domain, selection_id))

    assert response.sections, f"{selection_id}: no section built"
    assert response.entity_directory.brokers == ()
    expected = {"asset.market_analysis": ("asset.position_and_history",), "fx.pair_analysis": ("fx.market_and_exposure",)}.get(selection_id, ())
    assert response.unavailable_dataset_ids == expected
    text = json.dumps(response.model_dump(mode="json"))
    for name in book.broker_names.values():
        assert name not in text, f"{name} appears in a market-only export of a user who owns no broker"
