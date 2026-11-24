"""End-to-end integration tests for the Asset/FX domain fragment (Phase 0 AI
Export refinement, `ai-refinement-asset-fx` domain integration gate).

Covers `backend.app.services.ai_export.components.asset_fx_registry`:
placeholder-vs-real metadata validation, real `ComponentRegistry`/
`DatasetRegistry`/`AnalysisRegistry` construction (merged with the untouched
Portfolio/Broker placeholders from the frozen central catalog), and full
`Composer`-driven end-to-end composition of every Asset and FX dataset/
analysis - never against `components.catalog` itself (that file is
intentionally left untouched here; wiring real builders into it is owned by
the later `ai-refinement-component-registry-integration` serial gate).

Unlike the sibling `test_ai_export_components_portfolio_broker_integration.py`
(fully mocked, no real DB), this file exercises a REAL test database (same
convention as `test_ai_export_components_fx.py`): every Asset/FX raw resource
loader touched here (`asset_resources.load_asset_metadata`/`load_asset_report`/
`load_asset_lots`, `fx_core._load_asset_facts`/`_load_exposure_report`) runs a
genuine SQL query, so a tableless in-memory session would not satisfy them.
`AssetSourceManager.get_prices_bulk`/`backend.app.services.fx.conversion.convert_bulk`
are never monkeypatched either - both already read directly from the real
`PriceHistory`/`FxRate` tables (see `test_ai_export_components_fx.py`'s
`_seed_warmup_anchor` convention, reused here): a single very old anchor row
per (asset)/(currency pair) gives unlimited backward-fill a value for every
day of the warm-up window, so each loaded series is calendar-complete. Those
copies are carried points, not sessions: indicators count quote days
(developer's decision of 30/09/2026), so the warm-up they actually use is the
genuine rows and rates the scenario seeds around the period.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

import backend.app.services.ai_export.components.technical_shared as technical_shared_module
from backend.app.db.models import Asset, AssetProfileUpdate, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio.lots import LotAnalysisType
from backend.app.services.ai_export.analyses.catalog import EXPECTED_ANALYSIS_COUNT
from backend.app.services.ai_export.components.asset_fx_registry import (
    ASSET_FX_COMPONENTS,
    ASSET_REAL_COMPONENT_COUNT,
    ASSET_REAL_COMPONENT_IDS,
    FX_REAL_COMPONENT_COUNT,
    FX_REAL_COMPONENT_IDS,
    DuplicateReplacementComponentIdError,
    MissingPlaceholderComponentError,
    PlaceholderMetadataMismatchError,
    build_asset_fx_analysis_registry,
    build_asset_fx_component_registry,
    build_asset_fx_dataset_registry,
    validate_replacements_against_placeholders,
)
from backend.app.services.ai_export.components.catalog import (
    ALL_FOUNDATION_COMPONENTS,
    build_component_registry,
)
from backend.app.services.ai_export.components.fx_payloads import FxExposureConversionBasis, FxExposureKind
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.composer import Composer
from backend.app.services.ai_export.datasets.catalog import (
    EXPECTED_DATASET_COUNT,
    build_dataset_registry,
)
from backend.app.services.ai_export.dependencies import (
    BuildContext,
    RequiredComponentBuildError,
    build_bucket_plan_for_scope,
)
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.profile import store as profile_store
from backend.app.services.assets.profile.catalogue import CATALOGUE, normalize_value
from backend.app.services.portfolio.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio.portfolio_service import PortfolioService
from backend.app.services.portfolio.report import _portfolio_l2_cache
from backend.app.services.portfolio.wac import _wac_cache
from backend.app.utils.datetime_utils import utcnow

CURRENCY = "EUR"  # Asset/FX scope target_currency throughout - both native currencies
# used below (USD/JPY) differ from it, exercising automatic FX resolution.

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    _wac_cache.clear()
    _portfolio_l2_cache.clear()
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def test_user(session) -> User:
    user = User(
        username=f"assetfxint_{utcnow().timestamp()}",
        email=f"assetfxint_{utcnow().timestamp()}@test.com",
        hashed_password="fakehash",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


# =============================================================================
# Generic construction helpers
# =============================================================================


def _full_registry() -> ComponentRegistry:
    return build_component_registry()


def _asset_scope(*, user_id: int, asset_id: int, start: date, end: date, target: str = CURRENCY, detail_level: DetailLevel = DetailLevel.STANDARD, broker_scope: tuple[int, ...] = ()) -> BuildScope:
    return BuildScope(
        request_id=f"req-asset-{user_id}-{asset_id}-{end.isoformat()}-{detail_level.value}",
        user_id=user_id,
        domain=Domain.ASSET,
        detail_level=detail_level,
        period_start=start,
        period_end=end,
        target_currency=target,
        broker_scope=broker_scope,
        asset_id=asset_id,
    )


def _fx_scope(*, user_id: int, base: str, quote: str, start: date, end: date, target: str = CURRENCY, detail_level: DetailLevel = DetailLevel.STANDARD, broker_scope: tuple[int, ...] = ()) -> BuildScope:
    return BuildScope(
        request_id=f"req-fx-{user_id}-{base}-{quote}-{end.isoformat()}-{detail_level.value}",
        user_id=user_id,
        domain=Domain.FX,
        detail_level=detail_level,
        period_start=start,
        period_end=end,
        target_currency=target,
        broker_scope=broker_scope,
        base_currency=base,
        quote_currency=quote,
    )


def _portfolio_scope(
    *,
    user_id: int,
    start: date,
    end: date,
    broker_scope: tuple[int, ...],
    target: str = CURRENCY,
    detail_level: DetailLevel = DetailLevel.STANDARD,
) -> BuildScope:
    return BuildScope(
        request_id=f"req-portfolio-{user_id}-{end.isoformat()}-{detail_level.value}",
        user_id=user_id,
        domain=Domain.PORTFOLIO,
        detail_level=detail_level,
        period_start=start,
        period_end=end,
        target_currency=target,
        broker_scope=broker_scope,
    )


def _context(session: AsyncSession, scope: BuildScope) -> BuildContext:
    bucket_plan = build_bucket_plan_for_scope(scope)
    return BuildContext(_full_registry(), request_id=scope.request_id, scope=scope, bucket_plan=bucket_plan, session=session)


async def _make_broker(session, user: User, *, name: str) -> Broker:
    broker = Broker(name=f"{name}_{utcnow().timestamp()}")
    session.add(broker)
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role="OWNER", share_percentage=Decimal("1.0")))
    await session.flush()
    return broker


async def _deposit(session, broker: Broker, *, amount: str, currency: str, day: date) -> None:
    session.add(Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=day, amount=Decimal(amount), currency=currency))
    await session.flush()


async def _make_asset(session, *, currency: str, ticker: str, asset_type: AssetType = AssetType.STOCK, quote_base_quantity: int = 1) -> Asset:
    asset = Asset(
        display_name=f"AssetFxIntg_{ticker}_{utcnow().timestamp()}",
        identifier_ticker=ticker,
        currency=currency,
        asset_type=asset_type,
        quote_base_quantity=quote_base_quantity,
    )
    session.add(asset)
    await session.flush()
    return asset


async def _buy(session, broker: Broker, asset: Asset, *, quantity: str, amount: str, currency: str, day: date) -> None:
    session.add(Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.BUY, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency))
    await session.flush()


async def _sell(session, broker: Broker, asset: Asset, *, quantity: str, amount: str, currency: str, day: date) -> None:
    session.add(Transaction(broker_id=broker.id, asset_id=asset.id, type=TransactionType.SELL, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency))
    await session.flush()


def _synthetic_close(asset_id: int, day: date) -> Decimal:
    ordinal = day.toordinal()
    base = 100 + (asset_id % 7) * 5
    wave = Decimal(str(round(5 * ((ordinal % 17) - 8), 4)))
    return Decimal(base) + wave


def _synthetic_volume(day: date) -> Decimal:
    ordinal = day.toordinal()
    return Decimal(1000 + (ordinal % 37) * 25)


async def _price(session, asset: Asset, *, day: date, close: str, currency: str, source_plugin_key: str = "manual_test", volume: str = "1") -> None:
    session.add(
        PriceHistory(
            asset_id=asset.id,
            date=day,
            open=Decimal(close),
            high=Decimal(close),
            low=Decimal(close),
            close=Decimal(close),
            volume=Decimal(volume),
            currency=currency,
            source_plugin_key=source_plugin_key,
        )
    )
    await session.flush()


async def _seed_asset_warmup_anchor(session, asset: Asset, *, close: str, currency: str, source_plugin_key: str = "yfinance") -> None:
    """One very old, genuinely-observed `PriceHistory` row.

    `AssetSourceManager.get_prices_bulk`'s unlimited backward-fill (see
    `_build_backward_filled_series`) copies this anchor onto every day of the
    warm-up window real `SignalService` plans load, so the series is
    calendar-complete from its first day - exactly like `_seed_warmup_anchor`
    does for FX rates in `test_ai_export_components_fx.py`. The copies are
    carried points, not sessions: they give the indicators no warm-up, which
    comes only from genuine rows such as `_seed_asset_visible_prices` seeds.
    """
    await _price(session, asset, day=date(2015, 1, 1), close=close, currency=currency, source_plugin_key=source_plugin_key, volume="500")


async def _seed_asset_visible_prices(session, asset: Asset, *, start: date, end: date, currency: str, source_plugin_key: str = "yfinance") -> None:
    """Seeds one genuinely-observed, day-varying `PriceHistory` row per day in `[start, end]`."""
    rows = []
    day = start
    while day <= end:
        rows.append(
            PriceHistory(
                asset_id=asset.id,
                date=day,
                open=_synthetic_close(asset.id, day),
                high=_synthetic_close(asset.id, day) + 1,
                low=_synthetic_close(asset.id, day) - 1,
                close=_synthetic_close(asset.id, day),
                volume=_synthetic_volume(day),
                currency=currency,
                source_plugin_key=source_plugin_key,
            )
        )
        day += timedelta(days=1)
    session.add_all(rows)
    await session.flush()


async def _seed_rate(session, *, base: str, quote: str, rate: str, day: date, source: str = "ECB") -> None:
    """Upserting `FxRate` seed - mirrors `test_ai_export_components_fx.py`'s `_seed_rate` exactly (shared test DB)."""
    stored_base, stored_quote = sorted((base, quote))
    stored_rate = Decimal(rate) if base == stored_base else Decimal(1) / Decimal(rate)
    existing = (await session.execute(select(FxRate).where(FxRate.date == day, FxRate.base == stored_base, FxRate.quote == stored_quote))).scalar_one_or_none()
    if existing is not None:
        existing.rate = stored_rate
        existing.source = source
        session.add(existing)
    else:
        session.add(FxRate(date=day, base=stored_base, quote=stored_quote, rate=stored_rate, source=source))
    await session.flush()


async def _seed_rate_warmup_anchor(session, *, base: str, quote: str, rate: str) -> None:
    """One 1990 rate every warm-up day resolves to by backward-fill: carried days, not published ones."""
    await _seed_rate(session, base=base, quote=quote, rate=rate, day=date(1990, 1, 1), source="ECB")


def registry_placeholder(component_id: str):
    return next(spec for spec in ALL_FOUNDATION_COMPONENTS if spec.component_id == component_id)


EXPECTED_ASSET_IDS = frozenset(
    {
        "asset.identity",
        # D5 (plan 68): the profile of the asset, its voices as steps of the window
        "asset.profile",
        "asset.market_snapshot",
        "asset.position_scope",
        "asset.provenance",
        "asset.positions_by_broker",
        "asset.cost_value_pl",
        "asset.performance",
        "asset.lot_detail",
        "asset.ohlc_returns",
        "asset.indicators",
        "asset.states_events",
        # V2 context components
        "asset.technical_coverage",
        "asset.position_market_context",
        # V1 drawdown context component
        "asset.drawdown_summary",
    }
)
EXPECTED_FX_IDS = frozenset(
    {
        "fx.pair_identity",
        "fx.current_rate",
        "fx.conversion_provenance",
        "fx.exposure_base_quote",
        "fx.exposure_provenance",
        "fx.rate_ohlc",
        "fx.returns_volatility",
        "fx.indicators",
        "fx.states_events",
        # V2 context components
        "fx.technical_coverage",
        "fx.market_summary",
        # AI adequacy remediation: conversion timing context
        "fx.timing_context",
    }
)


# =============================================================================
# 1. Fragment sanity: exact ID counts, no overlap, requirement (1) placeholder match
# =============================================================================


class TestFragmentSanity:
    def test_exact_asset_and_fx_id_counts(self):
        # D5 (plan 68): asset.profile joins the Asset components (before D5: 14 Asset, 26 in all)
        assert ASSET_REAL_COMPONENT_COUNT == 15
        assert FX_REAL_COMPONENT_COUNT == 12
        assert len(ASSET_FX_COMPONENTS) == 27
        assert set(ASSET_REAL_COMPONENT_IDS) == EXPECTED_ASSET_IDS
        assert set(FX_REAL_COMPONENT_IDS) == EXPECTED_FX_IDS
        assert not (set(ASSET_REAL_COMPONENT_IDS) & set(FX_REAL_COMPONENT_IDS))

    def test_all_replacements_validate_cleanly_against_placeholders(self):
        # Must not raise: every real spec's id/version/domains/dependencies/period_behavior/aggregator
        # exactly matches its frozen placeholder counterpart (requirement 1).
        validate_replacements_against_placeholders(ASSET_FX_COMPONENTS)

    def test_every_replacement_metadata_exactly_matches_its_placeholder(self):
        for replacement in ASSET_FX_COMPONENTS:
            placeholder = registry_placeholder(replacement.component_id)
            assert replacement.component_id == placeholder.component_id
            assert replacement.version == placeholder.version
            assert replacement.domains == placeholder.domains
            assert replacement.dependencies == placeholder.dependencies
            assert replacement.period_behavior == placeholder.period_behavior
            assert replacement.aggregator == placeholder.aggregator

    def test_duplicate_replacement_id_detected(self):
        dup = (ASSET_FX_COMPONENTS[0], ASSET_FX_COMPONENTS[0])
        with pytest.raises(DuplicateReplacementComponentIdError):
            validate_replacements_against_placeholders(dup)

    def test_missing_placeholder_detected(self):
        fake = replace_component_id(ASSET_FX_COMPONENTS[0], "asset.does_not_exist")
        with pytest.raises(MissingPlaceholderComponentError):
            validate_replacements_against_placeholders((fake,))

    def test_metadata_mismatch_detected(self):
        real = ASSET_FX_COMPONENTS[0]
        drifted = replace_component_version(real, real.version + 1)
        with pytest.raises(PlaceholderMetadataMismatchError):
            validate_replacements_against_placeholders((drifted,))


def replace_component_id(spec, new_id: str):
    return dataclasses.replace(spec, component_id=new_id)


def replace_component_version(spec, new_version: int):
    return dataclasses.replace(spec, version=new_version)


# =============================================================================
# 2. Component registry construction (real Asset/FX + untouched other placeholders)
# =============================================================================


class TestComponentRegistryConstruction:
    def test_merged_registry_has_all_45_components_canonical_order_preserved(self):
        registry = build_asset_fx_component_registry()
        assert len(ALL_FOUNDATION_COMPONENTS) == len(registry.canonical_order)
        # Canonical order must exactly mirror the frozen catalog's own order.
        assert tuple(registry.canonical_order) == tuple(spec.component_id for spec in ALL_FOUNDATION_COMPONENTS)

    def test_non_asset_fx_placeholders_are_untouched_and_still_fail_closed(self):
        registry = build_asset_fx_component_registry()
        non_asset_fx_ids = {spec.component_id for spec in ALL_FOUNDATION_COMPONENTS if spec.component_id not in set(ASSET_REAL_COMPONENT_IDS) | set(FX_REAL_COMPONENT_IDS)}
        assert non_asset_fx_ids, "expected at least one non-Asset/FX placeholder (Portfolio/Broker) still present"
        sample_id = next(iter(sorted(non_asset_fx_ids)))
        placeholder_spec = registry_placeholder(sample_id)
        registry_spec = registry.get(sample_id)
        assert registry_spec.builder is placeholder_spec.builder

    def test_asset_and_fx_component_ids_resolve_to_real_specs(self):
        registry = build_asset_fx_component_registry()
        real_by_id = {spec.component_id: spec for spec in ASSET_FX_COMPONENTS}
        for component_id in set(ASSET_REAL_COMPONENT_IDS) | set(FX_REAL_COMPONENT_IDS):
            assert registry.get(component_id).builder is real_by_id[component_id].builder

    def test_catalog_module_itself_is_never_mutated(self):
        before = tuple(ALL_FOUNDATION_COMPONENTS)
        build_asset_fx_component_registry()
        after = tuple(ALL_FOUNDATION_COMPONENTS)
        assert before == after


# =============================================================================
# 3. Dataset / analysis registry construction (requirement 2)
# =============================================================================


class TestDatasetAnalysisRegistryConstruction:
    def test_dataset_registry_totals_and_asset_fx_subsets(self):
        registry = build_asset_fx_dataset_registry()
        assert len(registry) == EXPECTED_DATASET_COUNT == 41
        asset_datasets = {d.dataset_id for d in registry.for_domain(Domain.ASSET)}
        fx_datasets = {d.dataset_id for d in registry.for_domain(Domain.FX)}
        assert asset_datasets == {
            "asset.overview",
            "asset.position_performance",
            "asset.market_technical",
            "asset.all_data",
            "asset.position_context",
            "asset.drawdown_context",
            "asset.position_and_history",
            "asset.market_history",
        }
        assert fx_datasets == {
            "fx.overview",
            "fx.market_technical",
            "fx.direct_exposure",
            "fx.all_data",
            "fx.market_context",
            "fx.conversion_timing_context",
            "fx.market_and_exposure",
            "fx.market_history",
        }

    def test_analysis_registry_totals_and_asset_fx_subsets(self):
        registry = build_asset_fx_analysis_registry()
        assert len(registry) == EXPECTED_ANALYSIS_COUNT == 12
        asset_analyses = {a.analysis_id for a in registry.for_domain(Domain.ASSET)}
        fx_analyses = {a.analysis_id for a in registry.for_domain(Domain.FX)}
        assert asset_analyses == {"asset.position_review", "asset.market_analysis"}
        assert fx_analyses == {"fx.exposure_impact", "fx.pair_analysis"}

    def test_dataset_registry_builds_over_supplied_component_registry(self):
        component_registry = build_asset_fx_component_registry()
        dataset_registry = build_asset_fx_dataset_registry(component_registry)
        assert len(dataset_registry) == 41

    def test_analysis_registry_builds_over_supplied_dataset_registry(self):
        dataset_registry = build_asset_fx_dataset_registry()
        analysis_registry = build_asset_fx_analysis_registry(dataset_registry)
        assert len(analysis_registry) == 12


# =============================================================================
# Shared real-DB scenario fixture
#
# usd_asset: USD, held in broker1 (BUY then partial SELL -> FIFO) and broker2
#            (BUY only), target_currency=EUR forces automatic FX conversion.
# jpy_asset: JPY, held only in broker1 - a "no-look-through" negative case for
#            the EUR/USD FX exposure pair (neither leg matches JPY).
# empty_asset: never transacted by anyone - "no position overview valid" case.
# =============================================================================

PERIOD_START = date(2025, 9, 1)
PERIOD_END = date(2025, 9, 10)


class Scenario:
    def __init__(self, broker1, broker2, usd_asset, jpy_asset, empty_asset):
        self.broker1 = broker1
        self.broker2 = broker2
        self.usd_asset = usd_asset
        self.jpy_asset = jpy_asset
        self.empty_asset = empty_asset


@pytest_asyncio.fixture
async def scenario(session, test_user) -> Scenario:
    broker1 = await _make_broker(session, test_user, name="AssetFxBroker1")
    broker2 = await _make_broker(session, test_user, name="AssetFxBroker2")

    await _deposit(session, broker1, amount="5000", currency="EUR", day=PERIOD_START)
    await _deposit(session, broker2, amount="5000", currency="EUR", day=PERIOD_START)

    usd_asset = await _make_asset(session, currency="USD", ticker="AFIUSDA")
    await _buy(session, broker1, usd_asset, quantity="10", amount="-900", currency="EUR", day=PERIOD_START)
    await _sell(session, broker1, usd_asset, quantity="-4", amount="410", currency="EUR", day=date(2025, 9, 5))
    await _buy(session, broker2, usd_asset, quantity="5", amount="-480", currency="EUR", day=date(2025, 9, 2))

    await _seed_asset_warmup_anchor(session, usd_asset, close="85", currency="USD")
    # Extends 30 days before period_start (real, non-backward-filled, non-null volume). These 41 rows
    # are the only sessions the asset's indicators count - the 2015 anchor's copies are carried - which
    # is enough for the short windows (RSI, MFI, MACD, Bollinger...); the 50- and 200-session averages
    # stay unavailable here, and no test below depends on them.
    await _seed_asset_visible_prices(session, usd_asset, start=PERIOD_START - timedelta(days=30), end=PERIOD_END, currency="USD")

    jpy_asset = await _make_asset(session, currency="JPY", ticker="AFIJPYA")
    await _buy(session, broker1, jpy_asset, quantity="5", amount="-100", currency="EUR", day=PERIOD_START)
    await _price(session, jpy_asset, day=PERIOD_END, close="1000", currency="JPY", source_plugin_key="yfinance", volume="10")

    empty_asset = await _make_asset(session, currency="USD", ticker="AFIEMPTYA")

    await _seed_rate_warmup_anchor(session, base="EUR", quote="USD", rate="1.08")
    await _seed_rate_warmup_anchor(session, base="EUR", quote="JPY", rate="155")
    # Nine weeks of weekday EUR/USD fixings before the period, as ECB publishes them: the FX
    # indicators count published days, and the 1990 anchor's carried copies are none. Without
    # them every FX indicator of the curated bundle would be unavailable.
    fx_warmup_start = PERIOD_START - timedelta(days=63)
    fx_warmup_days = [fx_warmup_start + timedelta(days=offset) for offset in range(63) if (fx_warmup_start + timedelta(days=offset)).weekday() < 5]
    for index, day in enumerate(fx_warmup_days):
        await _seed_rate(session, base="EUR", quote="USD", rate=str(Decimal("1.08") + Decimal(index % 9) / Decimal(400)), day=day)
    for offset in range(0, (PERIOD_END - PERIOD_START).days + 1):
        day = PERIOD_START + timedelta(days=offset)
        await _seed_rate(session, base="EUR", quote="USD", rate=str(Decimal("1.10") + Decimal(offset) / Decimal(200)), day=day)
    await _seed_rate(session, base="EUR", quote="JPY", rate="160", day=PERIOD_END)

    return Scenario(broker1, broker2, usd_asset, jpy_asset, empty_asset)


def _asset_context(session, scenario: Scenario, *, asset_id: int, broker_scope: tuple[int, ...] = (), detail_level: DetailLevel = DetailLevel.STANDARD, user_id: int) -> BuildContext:
    scope = _asset_scope(user_id=user_id, asset_id=asset_id, start=PERIOD_START, end=PERIOD_END, detail_level=detail_level, broker_scope=broker_scope)
    return _context(session, scope)


def _asset_fx_context(session, *, user_id: int, base: str = "EUR", quote: str = "USD", detail_level: DetailLevel = DetailLevel.STANDARD, broker_scope: tuple[int, ...] = ()) -> BuildContext:
    scope = _fx_scope(user_id=user_id, base=base, quote=quote, start=PERIOD_START, end=PERIOD_END, detail_level=detail_level, broker_scope=broker_scope)
    return _context(session, scope)


# =============================================================================
# 4. Resource sharing / memoization (requirement 4)
# =============================================================================


class TestResourceSharingAsset:
    @pytest.mark.asyncio
    async def test_market_snapshot_and_technical_use_separate_currency_coherent_loads(
        self,
        session,
        test_user,
        scenario,
    ):
        real_get_prices_bulk = AssetSourceManager.get_prices_bulk
        calls = []

        @staticmethod
        async def _counting(*args, **kwargs):
            calls.append(tuple((request.target_currency, len(request.signals)) for request in args[0]))
            return await real_get_prices_bulk(*args, **kwargs)

        AssetSourceManager.get_prices_bulk = _counting
        try:
            context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
            registry = build_asset_fx_dataset_registry()
            composer = Composer()
            overview = await composer.compose_dataset(
                registry.get("asset.overview"),
                context,
                detail_level=DetailLevel.STANDARD,
            )
            technical = await composer.compose_dataset(
                registry.get("asset.market_technical"),
                context,
                detail_level=DetailLevel.STANDARD,
            )
        finally:
            AssetSourceManager.get_prices_bulk = real_get_prices_bulk

        assert calls == [((CURRENCY, 0),), ((None, 20),)]
        market_snapshot = next(section.payload for section in overview.sections if section.component_id == "asset.market_snapshot")
        ohlc = next(section.payload for section in technical.sections if section.component_id == "asset.ohlc_returns")
        assert market_snapshot["converted_price"]["code"] == CURRENCY
        assert ohlc["currency"] == scenario.usd_asset.currency

    @pytest.mark.asyncio
    async def test_one_report_call_shared_across_positions_cost_performance_lots(self, session, test_user, scenario):
        real_get_report = PortfolioService.get_report
        calls = []

        async def _counting(self, *args, **kwargs):
            calls.append(1)
            return await real_get_report(self, *args, **kwargs)

        PortfolioService.get_report = _counting
        try:
            context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
            registry = build_asset_fx_dataset_registry()
            composer = Composer()
            await composer.compose_dataset(registry.get("asset.position_performance"), context, detail_level=DetailLevel.STANDARD)
        finally:
            PortfolioService.get_report = real_get_report
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_one_lots_call_for_lot_detail(self, session, test_user, scenario):
        real_get_lots = LotsAnalysisService.get_lots_analysis
        calls = []

        async def _counting(self, *args, **kwargs):
            calls.append(1)
            return await real_get_lots(self, *args, **kwargs)

        LotsAnalysisService.get_lots_analysis = _counting
        try:
            context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
            registry = build_asset_fx_dataset_registry()
            composer = Composer()
            await composer.compose_dataset(registry.get("asset.position_performance"), context, detail_level=DetailLevel.STANDARD)
        finally:
            LotsAnalysisService.get_lots_analysis = real_get_lots
        assert len(calls) == 1


class TestResourceSharingFx:
    @pytest.mark.asyncio
    async def test_one_rate_series_call_shared_across_current_rate_provenance_and_technical(self, session, test_user, scenario):
        real_convert_bulk = technical_shared_module.convert_bulk
        calls = []

        async def _counting(*args, **kwargs):
            calls.append(1)
            return await real_convert_bulk(*args, **kwargs)

        technical_shared_module.convert_bulk = _counting
        try:
            context = _asset_fx_context(session, user_id=test_user.id)
            registry = build_asset_fx_dataset_registry()
            composer = Composer()
            await composer.compose_dataset(registry.get("fx.overview"), context, detail_level=DetailLevel.STANDARD)
            await composer.compose_dataset(registry.get("fx.market_technical"), context, detail_level=DetailLevel.STANDARD)
        finally:
            technical_shared_module.convert_bulk = real_convert_bulk
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_one_exposure_report_call_shared_across_exposure_components(
        self,
        session,
        test_user,
        scenario,
    ):
        real_get_report = PortfolioService.get_report
        calls = []

        async def _counting(self, *args, **kwargs):
            calls.append(1)
            return await real_get_report(self, *args, **kwargs)

        PortfolioService.get_report = _counting
        try:
            context = _asset_fx_context(session, user_id=test_user.id)
            registry = build_asset_fx_dataset_registry()
            composer = Composer()
            await composer.compose_dataset(
                registry.get("fx.direct_exposure"),
                context,
                detail_level=DetailLevel.STANDARD,
            )
        finally:
            PortfolioService.get_report = real_get_report
        assert len(calls) == 1


class TestRealMultiBrokerTechnicalUniverse:
    @pytest.mark.asyncio
    async def test_same_asset_in_two_brokers_is_aggregated_once(
        self,
        session,
        test_user,
        scenario,
    ):
        scope = _portfolio_scope(
            user_id=test_user.id,
            start=PERIOD_START,
            end=PERIOD_END,
            broker_scope=(scenario.broker1.id, scenario.broker2.id),
        )
        context = _context(session, scope)
        composition = await Composer().compose_dataset(
            build_dataset_registry().get("portfolio.technical"),
            context,
            detail_level=DetailLevel.STANDARD,
        )
        sections = {section.component_id: section.payload for section in composition.sections}
        universe = await technical_shared_module.load_technical_universe_bundle(
            context,
            **technical_shared_module.PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS,
        )

        assert len(universe.positions) == 3
        assert universe.asset_ids == tuple(sorted((scenario.usd_asset.id, scenario.jpy_asset.id)))
        assert len(universe.price_results.results) == 2
        expected_weights = technical_shared_module.compute_nav_weights(universe.positions)
        assert universe.weights == expected_weights
        assert sum(universe.weights.values(), Decimal(0)) == Decimal(1)

        prices = sections["portfolio.technical_prices"]
        indicators = sections["portfolio.technical_indicators"]
        breadth = sections["portfolio.technical_breadth"]
        events = sections["portfolio.technical_events"]
        expected_asset_ids = list(universe.asset_ids)

        assert prices["period_position_leg_count"] == 3
        assert prices["period_contributor_asset_count"] == 2
        assert prices["eligible_asset_count"] == 2
        assert [asset["asset_id"] for asset in prices["assets"]] == expected_asset_ids
        assert [asset["asset_id"] for asset in indicators["assets"]] == expected_asset_ids
        assert breadth["period_position_leg_count"] == 3
        assert breadth["period_contributor_asset_count"] == 2
        assert breadth["eligible_asset_count"] == 2
        assert breadth["covered_asset_count"] <= 2
        assert breadth["eligible_portfolio_weight_ratio"] == pytest.approx(1.0)
        assert breadth["covered_portfolio_weight_ratio"] <= 1.0
        assert breadth["covered_weight_ratio"] == pytest.approx(breadth["covered_portfolio_weight_ratio"])

        flat_events = [event for bucket in events["buckets"] for event in bucket["events"]]
        event_identities = {
            (
                event["date"],
                event["key"],
                event["signal_code"],
                event["asset_id"],
                event["direction"],
                tuple(sorted(event["values"].items())),
            )
            for event in flat_events
        }
        assert len(flat_events) == len(event_identities)


# =============================================================================
# 5. Dataset composition - all 4 Asset + 4 FX datasets, real payloads (requirement 2/3)
# =============================================================================


class TestAssetDatasetComposition:
    @pytest.mark.asyncio
    async def test_asset_overview_composes_with_correct_section_order(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("asset.overview"), context, detail_level=DetailLevel.STANDARD)
        # D5 (plan 68): asset.profile is required, right after asset.identity (before D5: not in the dataset)
        assert [e.component_id for e in composition.sections] == ["asset.identity", "asset.profile", "asset.market_snapshot", "asset.position_scope", "asset.provenance"]
        for envelope in composition.sections:
            assert envelope.payload  # real payload, never ComponentNotImplementedError

    @pytest.mark.asyncio
    async def test_asset_position_performance_composes_including_optional_lot_detail(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("asset.position_performance"), context, detail_level=DetailLevel.STANDARD)
        assert [e.component_id for e in composition.sections] == ["asset.positions_by_broker", "asset.cost_value_pl", "asset.performance", "asset.lot_detail"]

    @pytest.mark.asyncio
    async def test_asset_market_technical_composes_with_real_signals(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("asset.market_technical"), context, detail_level=DetailLevel.STANDARD)
        assert [e.component_id for e in composition.sections] == ["asset.technical_coverage", "asset.ohlc_returns", "asset.indicators", "asset.states_events"]
        indicators_section = next(e for e in composition.sections if e.component_id == "asset.indicators")
        assert len(indicators_section.payload["indicators"]) > 0

    @pytest.mark.asyncio
    async def test_asset_all_data_is_deduplicated_union_in_canonical_order(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("asset.all_data"), context, detail_level=DetailLevel.STANDARD)
        ids = [e.component_id for e in composition.sections]
        assert len(ids) == len(set(ids)), "asset.all_data must be deduplicated"
        assert set(ids) == set(ASSET_REAL_COMPONENT_IDS) - {"asset.position_market_context", "asset.drawdown_summary"}
        component_registry = build_asset_fx_component_registry()
        canonical = [cid for cid in component_registry.canonical_order if cid in ids]
        assert ids == canonical


class TestFxDatasetComposition:
    @pytest.mark.asyncio
    async def test_fx_overview_composes_with_correct_section_order(self, session, test_user, scenario):
        context = _asset_fx_context(session, user_id=test_user.id)
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("fx.overview"), context, detail_level=DetailLevel.STANDARD)
        assert [e.component_id for e in composition.sections] == ["fx.pair_identity", "fx.current_rate", "fx.conversion_provenance"]

    @pytest.mark.asyncio
    async def test_fx_market_technical_composes_with_real_signals(self, session, test_user, scenario):
        context = _asset_fx_context(session, user_id=test_user.id)
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("fx.market_technical"), context, detail_level=DetailLevel.STANDARD)
        assert [e.component_id for e in composition.sections] == ["fx.technical_coverage", "fx.rate_ohlc", "fx.returns_volatility", "fx.indicators", "fx.states_events"]
        indicators_section = next(e for e in composition.sections if e.component_id == "fx.indicators")
        assert len(indicators_section.payload["indicators"]) > 0

    @pytest.mark.asyncio
    async def test_fx_direct_exposure_composes_with_no_optional_components(self, session, test_user, scenario):
        context = _asset_fx_context(session, user_id=test_user.id)
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("fx.direct_exposure"), context, detail_level=DetailLevel.STANDARD)
        assert [e.component_id for e in composition.sections] == ["fx.exposure_base_quote", "fx.exposure_provenance"]

    @pytest.mark.asyncio
    async def test_fx_all_data_is_deduplicated_union_in_canonical_order(self, session, test_user, scenario):
        context = _asset_fx_context(session, user_id=test_user.id)
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("fx.all_data"), context, detail_level=DetailLevel.STANDARD)
        ids = [e.component_id for e in composition.sections]
        assert len(ids) == len(set(ids))
        assert set(ids) == set(FX_REAL_COMPONENT_IDS) - {"fx.market_summary", "fx.timing_context"}


# =============================================================================
# 6. Analysis composition - 2 Asset + 2 FX public analyses
# =============================================================================


class TestAnalysisComposition:
    @pytest.mark.asyncio
    async def test_asset_analyses_compose_with_expected_datasets(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        dataset_registry = build_asset_fx_dataset_registry()
        analysis_registry = build_asset_fx_analysis_registry(dataset_registry)
        composer = Composer()

        review = await composer.compose_analysis(analysis_registry.get("asset.position_review"), dataset_registry, context, detail_level=DetailLevel.STANDARD)
        assert review.dataset_ids == ("asset.position_and_history",)

        market = await composer.compose_analysis(analysis_registry.get("asset.market_analysis"), dataset_registry, context, detail_level=DetailLevel.STANDARD)
        assert market.dataset_ids == ("asset.market_history",)

    @pytest.mark.asyncio
    async def test_fx_analyses_compose_with_expected_datasets(self, session, test_user, scenario):
        context = _asset_fx_context(session, user_id=test_user.id)
        dataset_registry = build_asset_fx_dataset_registry()
        analysis_registry = build_asset_fx_analysis_registry(dataset_registry)
        composer = Composer()

        exposure_impact = await composer.compose_analysis(analysis_registry.get("fx.exposure_impact"), dataset_registry, context, detail_level=DetailLevel.STANDARD)
        assert exposure_impact.dataset_ids == ("fx.market_and_exposure",)

        pair_analysis = await composer.compose_analysis(analysis_registry.get("fx.pair_analysis"), dataset_registry, context, detail_level=DetailLevel.STANDARD)
        assert pair_analysis.dataset_ids == ("fx.market_history",)

    @pytest.mark.asyncio
    async def test_asset_indicators_and_events_cardinality_identical_across_detail_levels_only_buckets_differ(self, session, test_user, scenario):
        registry = build_asset_fx_dataset_registry()
        composer = Composer()

        compact_context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id, detail_level=DetailLevel.COMPACT)
        full_context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id, detail_level=DetailLevel.FULL)

        compact = await composer.compose_dataset(registry.get("asset.market_technical"), compact_context, detail_level=DetailLevel.COMPACT)
        full = await composer.compose_dataset(registry.get("asset.market_technical"), full_context, detail_level=DetailLevel.FULL)

        compact_indicators = next(e for e in compact.sections if e.component_id == "asset.indicators")
        full_indicators = next(e for e in full.sections if e.component_id == "asset.indicators")
        compact_keys = {ind["instance_id"] for ind in compact_indicators.payload["indicators"]}
        full_keys = {ind["instance_id"] for ind in full_indicators.payload["indicators"]}
        assert compact_keys, "presence barrier: two empty sets would compare equal and prove nothing"
        assert compact_keys == full_keys, "same signal cardinality across detail levels - only bucket granularity should differ"

        compact_events = next(e for e in compact.sections if e.component_id == "asset.states_events")
        full_events = next(e for e in full.sections if e.component_id == "asset.states_events")
        assert full_events.payload["detected_event_count"] > 0, "presence barrier: zero against zero would prove nothing"
        assert compact_events.payload["detected_event_count"] == full_events.payload["detected_event_count"], "detected event total must not depend on bucket granularity"
        assert compact_events.payload["exported_event_count"] <= full_events.payload["exported_event_count"], "detail may reduce exported events without changing detection"

    @pytest.mark.asyncio
    async def test_fx_indicators_cardinality_identical_across_detail_levels(self, session, test_user, scenario):
        registry = build_asset_fx_dataset_registry()
        composer = Composer()

        compact_context = _asset_fx_context(session, user_id=test_user.id, detail_level=DetailLevel.COMPACT)
        full_context = _asset_fx_context(session, user_id=test_user.id, detail_level=DetailLevel.FULL)

        compact = await composer.compose_dataset(registry.get("fx.market_technical"), compact_context, detail_level=DetailLevel.COMPACT)
        full = await composer.compose_dataset(registry.get("fx.market_technical"), full_context, detail_level=DetailLevel.FULL)

        compact_indicators = next(e for e in compact.sections if e.component_id == "fx.indicators")
        full_indicators = next(e for e in full.sections if e.component_id == "fx.indicators")
        compact_keys = {ind["instance_id"] for ind in compact_indicators.payload["indicators"]}
        full_keys = {ind["instance_id"] for ind in full_indicators.payload["indicators"]}
        assert compact_keys, "presence barrier: two empty sets would compare equal and prove nothing"
        assert compact_keys == full_keys


# =============================================================================
# 7. Asset domain validations (requirement 5)
# =============================================================================


class TestAssetDomainValidations:
    @pytest.mark.asyncio
    async def test_no_position_overview_is_valid_not_an_error(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.empty_asset.id, user_id=test_user.id)
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("asset.overview"), context, detail_level=DetailLevel.STANDARD)
        # Never a build failure: every required section still resolves, with an empty position scope.
        assert {e.component_id for e in composition.sections} == {"asset.identity", "asset.profile", "asset.market_snapshot", "asset.position_scope", "asset.provenance"}
        scope_envelope = next(e for e in composition.sections if e.component_id == "asset.position_scope")
        assert scope_envelope.payload["brokers"] == []
        assert scope_envelope.payload["broker_count"] == 0

    @pytest.mark.asyncio
    async def test_all_broker_rows_present_for_multi_broker_asset(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        envelope = await context.resolve("asset.positions_by_broker", required=True)
        broker_ids = {row["broker_id"] for row in envelope.payload["positions"]}
        assert broker_ids == {scenario.broker1.id, scenario.broker2.id}

    @pytest.mark.asyncio
    async def test_aggregate_coverage_is_complete_when_all_brokers_valued(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        envelope = await context.resolve("asset.cost_value_pl", required=True)
        coverage = envelope.payload["coverage"]
        assert coverage["total_broker_count"] == 2
        assert coverage["valued_broker_count"] == 2
        assert coverage["is_complete"] is True
        assert coverage["omitted"] == []

    @pytest.mark.asyncio
    async def test_lot_detail_optional_failure_is_omitted_not_propagated(self, session, test_user, scenario):
        real_get_lots = LotsAnalysisService.get_lots_analysis

        async def _raising(self, *args, **kwargs):
            raise RuntimeError("simulated lots failure")

        LotsAnalysisService.get_lots_analysis = _raising
        try:
            context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
            registry = build_asset_fx_dataset_registry()
            composition = await Composer().compose_dataset(registry.get("asset.position_performance"), context, detail_level=DetailLevel.STANDARD)
        finally:
            LotsAnalysisService.get_lots_analysis = real_get_lots
        ids = [e.component_id for e in composition.sections]
        assert "asset.lot_detail" not in ids
        assert set(ids) == {"asset.positions_by_broker", "asset.cost_value_pl", "asset.performance"}

    @pytest.mark.asyncio
    async def test_lot_detail_never_a_standalone_full_fifo_export(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        envelope = await context.resolve("asset.lot_detail", required=True)
        for row in envelope.payload["lots"]:
            # No-ID contract: never exposes lot/transaction identifiers.
            assert "lot_id" not in row
            assert "transaction_id" not in row
            assert "opening_transaction_id" not in row
        # Independently re-derive via a direct LotsAnalysisService call and cross-check quantities line up
        # (never a bespoke/standalone FIFO computation of its own).
        direct = await LotsAnalysisService(session).get_lots_analysis(
            user_id=test_user.id,
            asset_id=scenario.usd_asset.id,
            broker_ids=None,
            date_from=None,
            date_to=PERIOD_END,
            target_currency=CURRENCY,
            selected_lot_ids=None,
            requested_analyses=[LotAnalysisType.LOT_SUMMARY],
        )
        direct_open_quantities = sorted(str(lot.open_quantity) for lot in (direct.lots or []) if lot.open_quantity != 0)
        component_open_quantities = sorted(row["open_quantity"] for row in envelope.payload["lots"] if Decimal(row["open_quantity"]) != 0)
        assert direct_open_quantities == component_open_quantities


# =============================================================================
# 8. FX domain validations (requirement 5)
# =============================================================================


class TestFxDomainValidations:
    @pytest.mark.asyncio
    async def test_empty_exposure_is_valid_not_an_error(self, session, test_user):
        """A pair with no matching cash/position rows at all composes a valid, empty exposure."""
        empty_user = User(username=f"assetfxint_empty_{utcnow().timestamp()}", email=f"assetfxint_empty_{utcnow().timestamp()}@test.com", hashed_password="fakehash", is_active=True)
        session.add(empty_user)
        await session.flush()
        context = _asset_fx_context(session, user_id=empty_user.id, base="EUR", quote="GBP")
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("fx.direct_exposure"), context, detail_level=DetailLevel.STANDARD)
        base_quote = next(e for e in composition.sections if e.component_id == "fx.exposure_base_quote")
        provenance = next(e for e in composition.sections if e.component_id == "fx.exposure_provenance")
        assert base_quote.payload["rows"] == []
        assert provenance.payload["conversions"] == []

    @pytest.mark.asyncio
    async def test_direct_exposure_rows_have_correct_native_target_provenance(self, session, test_user, scenario):
        context = _asset_fx_context(session, user_id=test_user.id, base="EUR", quote="USD")
        envelope = await context.resolve("fx.exposure_base_quote", required=True)
        rows = envelope.payload["rows"]
        assert rows, "expected at least the EUR cash + USD position rows"
        for row in rows:
            assert row["linked_currency"] in ("EUR", "USD")
            assert row["target_amount"] is not None
            conversion = row["conversion"]
            if conversion["basis"] != FxExposureConversionBasis.ENGINE_VALUATION.value:
                assert row["native_amount"] is not None
            else:
                assert row["native_amount"] is None
            if row["kind"] == FxExposureKind.CASH.value:
                assert row["valuation_source"] is None
            else:
                assert row["valuation_source"] is not None

        provenance_envelope = await context.resolve("fx.exposure_provenance", required=True)
        conversions = provenance_envelope.payload["conversions"]
        # Every non-ENGINE_VALUATION linked currency present in rows has a provenance entry.
        non_engine_currencies = {row["linked_currency"] for row in rows if row["conversion"]["basis"] != FxExposureConversionBasis.ENGINE_VALUATION.value}
        provenance_currencies = {c["linked_currency"] for c in conversions}
        assert non_engine_currencies <= provenance_currencies

    @pytest.mark.asyncio
    async def test_no_look_through_jpy_position_excluded_from_eur_usd_pair(self, session, test_user, scenario):
        context = _asset_fx_context(session, user_id=test_user.id, base="EUR", quote="USD")
        envelope = await context.resolve("fx.exposure_base_quote", required=True)
        rows = envelope.payload["rows"]
        jpy_rows = [row for row in rows if row.get("asset_id") == scenario.jpy_asset.id]
        assert jpy_rows == [], "JPY-denominated position must never be look-through-included in an EUR/USD pair"
        currencies = {row["linked_currency"] for row in rows}
        assert "JPY" not in currencies

    @pytest.mark.asyncio
    async def test_no_top_n_truncation_every_row_preserved(self, session, test_user, scenario):
        context = _asset_fx_context(session, user_id=test_user.id, base="EUR", quote="USD")
        envelope = await context.resolve("fx.exposure_base_quote", required=True)
        rows = envelope.payload["rows"]
        # 2 brokers each with EUR cash + a USD position = at least 4 rows expected, well beyond any
        # legacy top-N (7/10/etc) cap - every one must be present, none summarized away.
        assert len(rows) >= 4
        broker_ids_seen = {row["broker_id"] for row in rows}
        assert broker_ids_seen == {scenario.broker1.id, scenario.broker2.id}


# =============================================================================
# 9. Automatic FX/prices, warm-up exclusion, exact BucketPlan, volume capability (requirement 6)
# =============================================================================


class TestAutomaticFxAndTechnicalCoverage:
    @pytest.mark.asyncio
    async def test_automatic_fx_conversion_applied_for_usd_asset_target_eur(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        envelope = await context.resolve("asset.market_snapshot", required=True)
        assert envelope.payload["target_currency"] == "EUR"
        assert envelope.payload["observed"]["native_price"]["code"] == "USD"
        assert envelope.payload["converted_price"]["code"] == "EUR"
        assert envelope.payload["conversion"] is not None

        cvpl_envelope = await context.resolve("asset.cost_value_pl", required=True)
        assert cvpl_envelope.payload["target_currency"] == "EUR"

    @pytest.mark.asyncio
    async def test_market_snapshot_uses_latest_observed_not_backward_filled_point(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        envelope = await context.resolve("asset.market_snapshot", required=True)
        assert envelope.payload["observed"]["date"] == PERIOD_END.isoformat()

    @pytest.mark.asyncio
    async def test_warmup_dates_excluded_and_bucket_plan_exactly_matches_scope_period(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        assert context.bucket_plan.start == PERIOD_START
        assert context.bucket_plan.end == PERIOD_END

        envelope = await context.resolve("asset.ohlc_returns", required=True)
        for bucket in envelope.payload["buckets"]:
            assert PERIOD_START.isoformat() <= bucket["start_date"] <= PERIOD_END.isoformat()
            assert PERIOD_START.isoformat() <= bucket["end_date"] <= PERIOD_END.isoformat()

    @pytest.mark.asyncio
    async def test_fx_warmup_dates_excluded_and_bucket_plan_exactly_matches_scope_period(self, session, test_user, scenario):
        context = _asset_fx_context(session, user_id=test_user.id)
        assert context.bucket_plan.start == PERIOD_START
        assert context.bucket_plan.end == PERIOD_END

        envelope = await context.resolve("fx.rate_ohlc", required=True)
        for bucket in envelope.payload["buckets"]:
            assert PERIOD_START.isoformat() <= bucket["start_date"] <= PERIOD_END.isoformat()
            assert PERIOD_START.isoformat() <= bucket["end_date"] <= PERIOD_END.isoformat()

    @pytest.mark.asyncio
    async def test_volume_capability_grants_mfi_indicator_from_yfinance_sourced_prices(self, session, test_user, scenario):
        # MFI's shared volume-coverage gate (`validate_meaningful_volume_input`)
        # requires a sufficient *directly observed* (non-backward-filled)
        # fraction of the points MFI computes on - the sessions the service
        # hands it (see `signals/base.py`). A native-currency asset
        # (matching the scope's `target_currency`) avoids the FX-conversion
        # pass, whose converted quotes carry a backward-fill record whenever
        # the FX rate itself was carried: still sessions, but not "directly
        # observed" volume (a distinct, legitimate staleness source, exercised
        # separately by the FX domain validations above) - isolating this test
        # to volume/price coverage only.
        mfi_asset = await _make_asset(session, currency=CURRENCY, ticker="AFIMFIVOL")
        await _seed_asset_visible_prices(
            session,
            mfi_asset,
            start=PERIOD_START - timedelta(days=1220),
            end=PERIOD_END,
            currency=CURRENCY,
        )
        context = _asset_context(session, scenario, asset_id=mfi_asset.id, user_id=test_user.id)
        envelope = await context.resolve("asset.indicators", required=True)
        instance_ids = {ind["instance_id"] for ind in envelope.payload["indicators"]}
        assert "mfi_14" in instance_ids, "yfinance-sourced, non-backward-filled volume must grant MFI capability"


# =============================================================================
# 10. Malicious text passthrough + JSON safety (requirement 6)
# =============================================================================


class TestMaliciousTextAndJsonSafety:
    @pytest.mark.asyncio
    async def test_malicious_profile_description_passed_through_verbatim_never_executed(self, session, test_user, scenario):
        """D5 (plan 68): the free-text description is the profile voice `description` now, exported by
        `asset.profile` in its `values` table — verbatim, as inert data, never interpreted or templated.

        Before D5: the same text came from `classification_params` through `asset.identity`
        (`payload["classification"]["short_description"]`)."""
        text = "<script>alert(1)</script> normal text \u00e9\u00e8 \u2603"
        await _profile_row(session, scenario.usd_asset, "description", text, day=PERIOD_START, source="user")
        payload = await _resolve_profile(session, test_user, scenario.usd_asset, PERIOD_START, PERIOD_END)

        description = [row for row in payload["values"] if row["voice"] == "description"]
        assert [row["value"] for row in description] == [text]
        # Round-trips through JSON safely as inert text, never interpreted.
        reloaded = json.loads(json.dumps(payload))
        assert [row["value"] for row in reloaded["values"] if row["voice"] == "description"] == [text]

    @pytest.mark.asyncio
    async def test_asset_all_data_is_fully_json_safe(self, session, test_user, scenario):
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("asset.all_data"), context, detail_level=DetailLevel.STANDARD)
        for envelope in composition.sections:
            dumped = json.dumps(envelope.payload)
            assert json.loads(dumped) == envelope.payload

    @pytest.mark.asyncio
    async def test_fx_all_data_is_fully_json_safe(self, session, test_user, scenario):
        context = _asset_fx_context(session, user_id=test_user.id)
        registry = build_asset_fx_dataset_registry()
        composition = await Composer().compose_dataset(registry.get("fx.all_data"), context, detail_level=DetailLevel.STANDARD)
        for envelope in composition.sections:
            dumped = json.dumps(envelope.payload)
            assert json.loads(dumped) == envelope.payload


# =============================================================================
# D5 (plan 68): asset.identity v2 (no classification) and asset.profile v1
#
# Every profile row is seeded by hand as an `AssetProfileUpdate` with a chosen `read_on` (its value in the catalogue's
# stored form, `normalize_value` + `json.dumps`), on an asset of the test's own, inside the rolled-back session. Each
# test first checks its seeding through the store (`read_steps`, the very read the component makes), then resolves
# `asset.profile` from the production registry.
# =============================================================================

WINDOW_START = date(2025, 9, 1)
WINDOW_END = date(2025, 9, 30)

#: The tables of `asset.profile` built from the steps, each one a flat list of rows. `freshness` (D1d) is not one of
#: them: it follows «now», and is asserted where a test is about it.
PROFILE_TABLES = ("percentages", "amounts", "values", "weights", "coupon_schedule", "emptied", "thinned")
STEP_KEYS = {"voice", "date", "through", "source"}


async def _profile_row(session, asset: Asset, key: str, value, *, day: date, source: str = "justetf") -> None:
    stored = normalize_value(key, value)
    session.add(AssetProfileUpdate(asset_id=asset.id, key=key, value=None if stored is None else json.dumps(stored), source=source, read_on=day))
    await session.flush()


async def _profile_asset(session, ticker: str) -> Asset:
    return await _make_asset(session, currency="EUR", ticker=ticker, asset_type=AssetType.ETF)


async def _steps_in_window(session, asset: Asset, start: date = WINDOW_START, end: date = WINDOW_END) -> dict[str, int]:
    """The number of steps of each voice in the window, as the store reads them (no carry-back): the precondition."""
    steps = await profile_store.read_steps(session, [asset.id], DateRangeModel(start=start, end=end), keys=None, carry_back=False)
    return {key: len(voice_steps) for key, voice_steps in steps.get(asset.id, {}).items()}


async def _resolve_profile(session, user: User, asset: Asset, start: date = WINDOW_START, end: date = WINDOW_END) -> dict:
    registry = _full_registry()
    assert "asset.profile" in registry, "asset.profile is not registered in the production component registry (D5)"
    scope = _asset_scope(user_id=user.id, asset_id=asset.id, start=start, end=end)
    context = BuildContext(registry, request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope), session=session)
    envelope = await context.resolve("asset.profile", required=True)
    assert (envelope.component_id, envelope.component_version) == ("asset.profile", 1)
    return envelope.payload


def _table(payload: dict, name: str, extra_keys: set[str]) -> list[dict]:
    rows = payload[name]
    for row in rows:
        assert set(row) == STEP_KEYS | extra_keys, f"{name}: a flat row has exactly {sorted(STEP_KEYS | extra_keys)}, got {sorted(row)}"
    return rows


def _percentages(payload: dict) -> list[tuple]:
    return [(r["voice"], r["date"], r["through"], r["source"], Decimal(r["value_ratio"])) for r in _table(payload, "percentages", {"value_ratio"})]


def _amounts(payload: dict) -> list[tuple]:
    return [(r["voice"], r["date"], r["through"], r["source"], Decimal(r["amount"]), r["currency"]) for r in _table(payload, "amounts", {"amount", "currency"})]


def _values(payload: dict) -> list[tuple]:
    return [(r["voice"], r["date"], r["through"], r["source"], r["value"], r["unit"]) for r in _table(payload, "values", {"value", "unit"})]


def _weights(payload: dict) -> list[tuple]:
    return [(r["voice"], r["date"], r["through"], r["source"], r["key"], Decimal(r["weight"])) for r in _table(payload, "weights", {"key", "weight"})]


def _emptied(payload: dict) -> list[tuple]:
    return [(r["voice"], r["date"], r["through"], r["source"]) for r in _table(payload, "emptied", set())]


def _thinned(payload: dict) -> dict[str, int]:
    for row in payload["thinned"]:
        assert set(row) == {"voice", "changes_in_window"}, sorted(row)
    return {row["voice"]: row["changes_in_window"] for row in payload["thinned"]}


def _weight_rows(voice: str, value: dict, first: str, through: str, source: str = "justetf") -> list[tuple]:
    """The weight rows one map step gives: one per key, keys sorted, weights as the catalogue stores them."""
    stored = normalize_value(voice, value)
    return [(voice, first, through, source, key, Decimal(weight)) for key, weight in sorted(stored.items())]


def _assert_only_tables(payload: dict, *filled: str) -> None:
    """Every table not named is empty."""
    for name in PROFILE_TABLES:
        if name not in filled:
            assert payload[name] == [], f"{name} should be empty, got {payload[name]}"


class TestAssetIdentityV2:
    @pytest.mark.asyncio
    async def test_identity_is_version_2_without_classification(self, session, test_user, scenario):
        """The scenario's USD asset has no profile row: identity v2 builds, with every identity field and no
        `classification` (before D5: version 1 with the classification, from the old column)."""
        context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        envelope = await context.resolve("asset.identity", required=True)

        assert envelope.component_version == 2
        assert "classification" not in envelope.payload
        assert envelope.payload["asset_id"] == scenario.usd_asset.id
        assert envelope.payload["identifiers"]["ticker"] == "AFIUSDA"


class TestAssetProfileComponent:
    @staticmethod
    def _assert_source_semantics(payload: dict) -> None:
        semantics = payload["source_semantics"]
        assert isinstance(semantics, str) and semantics.strip()
        assert "legacy" in semantics and "user" in semantics

    @pytest.mark.asyncio
    async def test_a_stored_value_the_catalogue_no_longer_reads_is_a_value_row_never_a_failure(self, session, test_user):
        """A row written before a catalogue rule was tightened comes back from the store as its own text (``store._value``
        never refuses it). The component is REQUIRED in three datasets, so it never fails on such a row: the step is a
        ``values`` row with the stored text, whatever the voice's shape (a percentage, a map)."""
        asset = await _profile_asset(session, "AFIPRAW")
        session.add(AssetProfileUpdate(asset_id=asset.id, key="ter", value=json.dumps("not a number"), source="legacy", read_on=date(2025, 9, 3)))
        session.add(AssetProfileUpdate(asset_id=asset.id, key="geography", value=json.dumps([1, 2]), source="legacy", read_on=date(2025, 9, 3)))
        await session.flush()

        payload = await _resolve_profile(session, test_user, asset)

        assert _values(payload) == [
            ("geography", "2025-09-03", "2025-09-30", "legacy", "[1, 2]", None),
            ("ter", "2025-09-03", "2025-09-30", "legacy", "not a number", None),
        ]
        _assert_only_tables(payload, "values")

    @pytest.mark.asyncio
    async def test_percentage_voice_read_on_two_days_gives_two_rows_as_ratios(self, session, test_user):
        asset = await _profile_asset(session, "AFIPTER")
        await _profile_row(session, asset, "ter", "0.0022", day=date(2025, 9, 3))
        await _profile_row(session, asset, "ter", "0.0019", day=date(2025, 9, 15), source="user")
        assert await _steps_in_window(session, asset) == {"ter": 2}

        payload = await _resolve_profile(session, test_user, asset)

        assert payload["asset_id"] == asset.id
        assert payload["no_profile_data"] is False
        assert payload["history_starts_on"] == "2025-09-03"
        self._assert_source_semantics(payload)
        assert _percentages(payload) == [
            ("ter", "2025-09-03", "2025-09-14", "justetf", Decimal("0.0022")),
            ("ter", "2025-09-15", "2025-09-30", "user", Decimal("0.0019")),
        ]
        _assert_only_tables(payload, "percentages")

    @pytest.mark.asyncio
    async def test_map_voice_gives_one_weight_row_per_key_in_sorted_order(self, session, test_user):
        asset = await _profile_asset(session, "AFIPGEO")
        geography = {"USA": "0.6", "JPN": "0.3", "DEU": "0.1"}
        await _profile_row(session, asset, "geography", geography, day=date(2025, 9, 4))
        assert await _steps_in_window(session, asset) == {"geography": 1}

        payload = await _resolve_profile(session, test_user, asset)

        assert _weights(payload) == _weight_rows("geography", geography, "2025-09-04", "2025-09-30")
        assert [row["key"] for row in payload["weights"]] == ["DEU", "JPN", "USA"]
        _assert_only_tables(payload, "weights")

    @pytest.mark.asyncio
    async def test_amount_voice_gives_an_amount_row_with_its_currency(self, session, test_user):
        asset = await _profile_asset(session, "AFIPAMT")
        await _profile_row(session, asset, "outstanding_amount", {"amount": "1500000.50", "currency": "EUR"}, day=date(2025, 9, 8))
        assert await _steps_in_window(session, asset) == {"outstanding_amount": 1}

        payload = await _resolve_profile(session, test_user, asset)

        assert _amounts(payload) == [("outstanding_amount", "2025-09-08", "2025-09-30", "justetf", Decimal("1500000.5"), "EUR")]
        _assert_only_tables(payload, "amounts")

    @pytest.mark.asyncio
    async def test_number_date_text_choice_country_and_currency_voices_are_values_with_their_unit(self, session, test_user):
        """Shapes number, date, text, choice, country and currency go to `values`: the stored form as text, and the
        catalogue voice's unit (`years` for the modified duration) or None. Seeded in the reverse of the catalogue
        order: the rows come out in catalogue order."""
        asset = await _profile_asset(session, "AFIPVAL")
        seeded = [
            ("min_lot", "1000"),
            ("fund_currency", "USD"),
            ("fund_domicile", "IRL"),
            ("distribution_policy", "accumulating"),
            ("maturity_date", "2030-01-15"),
            ("modified_duration", "6.210"),
            ("description", "A world equity index fund"),
        ]
        for key, value in seeded:
            await _profile_row(session, asset, key, value, day=date(2025, 9, 2))
        assert await _steps_in_window(session, asset) == dict.fromkeys((key for key, _ in seeded), 1)

        payload = await _resolve_profile(session, test_user, asset)

        assert _values(payload) == [
            ("description", "2025-09-02", "2025-09-30", "justetf", "A world equity index fund", None),
            ("modified_duration", "2025-09-02", "2025-09-30", "justetf", "6.21", "years"),
            ("maturity_date", "2025-09-02", "2025-09-30", "justetf", "2030-01-15", None),
            ("distribution_policy", "2025-09-02", "2025-09-30", "justetf", "accumulating", None),
            ("fund_domicile", "2025-09-02", "2025-09-30", "justetf", "IRL", None),
            ("fund_currency", "2025-09-02", "2025-09-30", "justetf", "USD", None),
            ("min_lot", "2025-09-02", "2025-09-30", "justetf", "1000", None),
        ]
        # modified_duration is volatile, but one step drops nothing and is not thinned
        assert _thinned(payload) == {}
        _assert_only_tables(payload, "values")

    @pytest.mark.asyncio
    async def test_coupon_schedule_gives_one_row_per_schedule_row(self, session, test_user):
        asset = await _profile_asset(session, "AFIPCPN")
        schedule = [{"from": "2025-07-01", "to": "2025-12-31", "rate": "0.0350"}, {"from": "2025-01-01", "to": "2025-06-30", "rate": "0.03"}]
        await _profile_row(session, asset, "coupon_schedule", schedule, day=date(2025, 9, 10))
        assert await _steps_in_window(session, asset) == {"coupon_schedule": 1}

        payload = await _resolve_profile(session, test_user, asset)

        rows = _table(payload, "coupon_schedule", {"from_date", "to_date", "rate_ratio"})
        assert [(r["voice"], r["date"], r["through"], r["source"], r["from_date"], r["to_date"], Decimal(r["rate_ratio"])) for r in rows] == [
            ("coupon_schedule", "2025-09-10", "2025-09-30", "justetf", "2025-01-01", "2025-06-30", Decimal("0.03")),
            ("coupon_schedule", "2025-09-10", "2025-09-30", "justetf", "2025-07-01", "2025-12-31", Decimal("0.035")),
        ]
        _assert_only_tables(payload, "coupon_schedule")

    @pytest.mark.asyncio
    async def test_a_voice_emptied_on_purpose_appears_only_in_emptied(self, session, test_user):
        asset = await _profile_asset(session, "AFIPEMP")
        await _profile_row(session, asset, "ter", "0.0022", day=date(2025, 9, 3))
        await _profile_row(session, asset, "ter", None, day=date(2025, 9, 20), source="user")
        await _profile_row(session, asset, "description", "Old text", day=date(2025, 9, 2))
        await _profile_row(session, asset, "description", None, day=date(2025, 9, 10), source="user")
        await _profile_row(session, asset, "geography", None, day=date(2025, 9, 5), source="user")
        assert await _steps_in_window(session, asset) == {"ter": 2, "description": 2, "geography": 1}

        payload = await _resolve_profile(session, test_user, asset)

        assert _percentages(payload) == [("ter", "2025-09-03", "2025-09-19", "justetf", Decimal("0.0022"))]
        assert _values(payload) == [("description", "2025-09-02", "2025-09-09", "justetf", "Old text", None)]
        assert _emptied(payload) == [
            ("geography", "2025-09-05", "2025-09-30", "user"),
            ("description", "2025-09-10", "2025-09-30", "user"),
            ("ter", "2025-09-20", "2025-09-30", "user"),
        ]
        _assert_only_tables(payload, "percentages", "values", "emptied")

    @pytest.mark.asyncio
    async def test_a_window_holding_now_says_how_fresh_it_is_for_the_volatile_voices(self, session, test_user):
        """D1d: a gross yield read 100 then 40 days ago (no enricher state: confirmed the day of «now») is stale, a fund
        size read 5 days ago is not, a TER carries no signal. A window ending yesterday still holds «now»; one that ends
        before «now» was read says nothing. Days from the test's UTC today; the profile's today may differ by one day."""
        today = datetime.now(UTC).date()
        asset = await _profile_asset(session, "AFIPFRS")
        await _profile_row(session, asset, "yield_gross", "0.0352", day=today - timedelta(days=100))
        await _profile_row(session, asset, "yield_gross", "0.0361", day=today - timedelta(days=40))
        await _profile_row(session, asset, "fund_size", {"amount": "5000000", "currency": "EUR"}, day=today - timedelta(days=5))
        await _profile_row(session, asset, "ter", "0.0022", day=today - timedelta(days=400))

        payload = await _resolve_profile(session, test_user, asset, start=today - timedelta(days=120), end=today - timedelta(days=1))
        before = await _resolve_profile(session, test_user, asset, start=today - timedelta(days=120), end=today - timedelta(days=60))

        assert sorted((row["voice"], row["confirmed_on"], row["stale"]) for row in payload["freshness"]) == [
            ("fund_size", (today - timedelta(days=5)).isoformat(), False),
            ("yield_gross", (today - timedelta(days=40)).isoformat(), True),
        ], payload["freshness"]
        assert before["freshness"] == [], "a window that ends before «now» was read says nothing"

    @pytest.mark.asyncio
    async def test_a_volatile_voice_with_four_steps_keeps_its_first_and_last_and_is_thinned(self, session, test_user):
        """yield_gross is volatile: of its 4 steps in the window only the first and the last are rows, and `thinned`
        says 3 changes. ter (not volatile, not a map) keeps all of its 4 steps and is never thinned."""
        asset = await _profile_asset(session, "AFIPVOL")
        for day, value in ((2, "0.031"), (9, "0.032"), (16, "0.033"), (23, "0.034")):
            await _profile_row(session, asset, "yield_gross", value, day=date(2025, 9, day))
        for day, value in ((2, "0.0020"), (9, "0.0021"), (16, "0.0022"), (23, "0.0023")):
            await _profile_row(session, asset, "ter", value, day=date(2025, 9, day))
        assert await _steps_in_window(session, asset) == {"yield_gross": 4, "ter": 4}

        payload = await _resolve_profile(session, test_user, asset)

        assert _percentages(payload) == [
            ("ter", "2025-09-02", "2025-09-08", "justetf", Decimal("0.0020")),
            ("ter", "2025-09-09", "2025-09-15", "justetf", Decimal("0.0021")),
            ("ter", "2025-09-16", "2025-09-22", "justetf", Decimal("0.0022")),
            ("ter", "2025-09-23", "2025-09-30", "justetf", Decimal("0.0023")),
            ("yield_gross", "2025-09-02", "2025-09-08", "justetf", Decimal("0.031")),
            ("yield_gross", "2025-09-23", "2025-09-30", "justetf", Decimal("0.034")),
        ]
        assert _thinned(payload) == {"yield_gross": 3}
        _assert_only_tables(payload, "percentages", "thinned")

    @pytest.mark.asyncio
    async def test_a_volatile_voice_with_one_or_two_steps_drops_nothing_and_is_not_thinned(self, session, test_user):
        asset = await _profile_asset(session, "AFIPVL2")
        await _profile_row(session, asset, "fund_size", {"amount": "5000000", "currency": "EUR"}, day=date(2025, 9, 6))
        await _profile_row(session, asset, "market_cap", {"amount": "100", "currency": "USD"}, day=date(2025, 9, 3))
        await _profile_row(session, asset, "market_cap", {"amount": "120", "currency": "USD"}, day=date(2025, 9, 17))
        assert await _steps_in_window(session, asset) == {"fund_size": 1, "market_cap": 2}

        payload = await _resolve_profile(session, test_user, asset)

        assert _amounts(payload) == [
            ("fund_size", "2025-09-06", "2025-09-30", "justetf", Decimal("5000000"), "EUR"),
            ("market_cap", "2025-09-03", "2025-09-16", "justetf", Decimal("100"), "USD"),
            ("market_cap", "2025-09-17", "2025-09-30", "justetf", Decimal("120"), "USD"),
        ]
        assert _thinned(payload) == {}
        _assert_only_tables(payload, "amounts")

    @pytest.mark.asyncio
    async def test_a_map_voice_with_three_steps_keeps_its_first_and_last_and_is_thinned(self, session, test_user):
        """geography is not volatile, but a map is thinned too: of 3 steps only the first and the last give weight
        rows, and `thinned` says 2 changes."""
        asset = await _profile_asset(session, "AFIPMAP")
        first, middle, last = {"USA": "0.6", "JPN": "0.4"}, {"USA": "0.5", "JPN": "0.5"}, {"USA": "0.7", "JPN": "0.3"}
        await _profile_row(session, asset, "geography", first, day=date(2025, 9, 2))
        await _profile_row(session, asset, "geography", middle, day=date(2025, 9, 10))
        await _profile_row(session, asset, "geography", last, day=date(2025, 9, 20))
        assert await _steps_in_window(session, asset) == {"geography": 3}

        payload = await _resolve_profile(session, test_user, asset)

        assert _weights(payload) == _weight_rows("geography", first, "2025-09-02", "2025-09-09") + _weight_rows("geography", last, "2025-09-20", "2025-09-30")
        assert _thinned(payload) == {"geography": 2}
        _assert_only_tables(payload, "weights", "thinned")

    @pytest.mark.asyncio
    async def test_a_window_before_the_first_row_shows_nothing_and_says_where_history_starts(self, session, test_user):
        asset = await _profile_asset(session, "AFIPLATE")
        await _profile_row(session, asset, "ter", "0.0022", day=date(2025, 10, 5))
        await _profile_row(session, asset, "geography", {"USA": "1"}, day=date(2025, 10, 8))
        assert await _steps_in_window(session, asset) == {}

        payload = await _resolve_profile(session, test_user, asset)

        assert payload["no_profile_data"] is False
        assert payload["history_starts_on"] == "2025-10-05"
        self._assert_source_semantics(payload)
        _assert_only_tables(payload)

    @pytest.mark.asyncio
    async def test_an_asset_without_profile_rows_has_no_profile_data_and_is_not_an_error(self, session, test_user):
        asset = await _profile_asset(session, "AFIPNONE")

        payload = await _resolve_profile(session, test_user, asset)

        assert payload["asset_id"] == asset.id
        assert payload["no_profile_data"] is True
        assert payload["history_starts_on"] is None
        self._assert_source_semantics(payload)
        _assert_only_tables(payload)

    @pytest.mark.asyncio
    async def test_rows_outside_the_window_are_not_reported(self, session, test_user):
        """A row superseded before the window and a row after it are not reported. The row in force when the window
        opens is: the store's step holding the window's first day starts on it (no carry-back: a voice whose history
        begins inside the window starts where it begins, as in the other tests)."""
        asset = await _profile_asset(session, "AFIPOUT")
        await _profile_row(session, asset, "ter", "0.0030", day=date(2025, 7, 1))
        await _profile_row(session, asset, "ter", "0.0025", day=date(2025, 8, 1))
        await _profile_row(session, asset, "ter", "0.0020", day=date(2025, 9, 15))
        await _profile_row(session, asset, "ter", "0.0010", day=date(2025, 10, 10))
        await _profile_row(session, asset, "fund_provider", "Late Provider", day=date(2025, 10, 1))
        assert await _steps_in_window(session, asset) == {"ter": 2}

        payload = await _resolve_profile(session, test_user, asset)

        assert payload["history_starts_on"] == "2025-07-01"
        assert _percentages(payload) == [
            ("ter", "2025-09-01", "2025-09-14", "justetf", Decimal("0.0025")),
            ("ter", "2025-09-15", "2025-09-30", "justetf", Decimal("0.0020")),
        ]
        assert "Late Provider" not in json.dumps(payload)
        _assert_only_tables(payload, "percentages")

    @pytest.mark.asyncio
    async def test_rows_follow_catalogue_order_then_date(self, session, test_user):
        """Seeded latest-first and voice by voice against the catalogue: the rows come out by catalogue order of the
        voice, then by date."""
        asset = await _profile_asset(session, "AFIPORD")
        await _profile_row(session, asset, "yield_gross", "0.041", day=date(2025, 9, 20))
        await _profile_row(session, asset, "ter", "0.0019", day=date(2025, 9, 25))
        await _profile_row(session, asset, "withholding_tax", "0.15", day=date(2025, 9, 12))
        await _profile_row(session, asset, "yield_gross", "0.040", day=date(2025, 9, 5))
        await _profile_row(session, asset, "ter", "0.0022", day=date(2025, 9, 4))
        assert await _steps_in_window(session, asset) == {"yield_gross": 2, "ter": 2, "withholding_tax": 1}
        catalogue_order = list(CATALOGUE)
        assert catalogue_order.index("withholding_tax") < catalogue_order.index("ter") < catalogue_order.index("yield_gross")

        payload = await _resolve_profile(session, test_user, asset)

        assert _percentages(payload) == [
            ("withholding_tax", "2025-09-12", "2025-09-30", "justetf", Decimal("0.15")),
            ("ter", "2025-09-04", "2025-09-24", "justetf", Decimal("0.0022")),
            ("ter", "2025-09-25", "2025-09-30", "justetf", Decimal("0.0019")),
            ("yield_gross", "2025-09-05", "2025-09-19", "justetf", Decimal("0.040")),
            ("yield_gross", "2025-09-20", "2025-09-30", "justetf", Decimal("0.041")),
        ]
        assert _thinned(payload) == {}


# =============================================================================
# 11. Required/optional failure propagation (requirement 3/6)
# =============================================================================


class TestRequiredOptionalFailurePropagation:
    @pytest.mark.asyncio
    async def test_required_component_build_failure_propagates_as_required_component_build_error(self, session, test_user, scenario):
        real_get_report = PortfolioService.get_report

        async def _raising(self, *args, **kwargs):
            raise RuntimeError("simulated report failure")

        PortfolioService.get_report = _raising
        try:
            context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
            registry = build_asset_fx_dataset_registry()
            with pytest.raises(RequiredComponentBuildError):
                await Composer().compose_dataset(registry.get("asset.position_performance"), context, detail_level=DetailLevel.STANDARD)
        finally:
            PortfolioService.get_report = real_get_report

    @pytest.mark.asyncio
    async def test_optional_dataset_omitted_from_analysis_when_its_required_component_fails(self, session, test_user, scenario):
        real_get_lots = LotsAnalysisService.get_lots_analysis

        async def _raising(self, *args, **kwargs):
            raise RuntimeError("simulated lots failure")

        LotsAnalysisService.get_lots_analysis = _raising
        try:
            context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
            dataset_registry = build_asset_fx_dataset_registry()
            analysis_registry = build_asset_fx_analysis_registry(dataset_registry)
            # asset.position_review requires the autonomous position_and_history dataset;
            # lot_detail failing (optional within that dataset) must not fail the dataset itself,
            # nor the analysis - it must simply omit that one section.
            composition = await Composer().compose_analysis(analysis_registry.get("asset.position_review"), dataset_registry, context, detail_level=DetailLevel.STANDARD)
        finally:
            LotsAnalysisService.get_lots_analysis = real_get_lots
        assert composition.dataset_ids == ("asset.position_and_history",)
        assert "asset.lot_detail" not in {e.component_id for e in composition.sections}


# =============================================================================
# 12. Concurrent composition - no DB deadlock / resource conflict (requirement 6)
# =============================================================================


class TestConcurrentComposition:
    @pytest.mark.asyncio
    async def test_concurrent_asset_and_fx_dataset_composition_no_deadlock(self, session, test_user, scenario):
        registry = build_asset_fx_dataset_registry()
        composer = Composer()
        asset_context = _asset_context(session, scenario, asset_id=scenario.usd_asset.id, user_id=test_user.id)
        fx_context = _asset_fx_context(session, user_id=test_user.id)

        async def _run():
            return await asyncio.gather(
                composer.compose_dataset(registry.get("asset.overview"), asset_context, detail_level=DetailLevel.STANDARD),
                composer.compose_dataset(registry.get("asset.position_performance"), asset_context, detail_level=DetailLevel.STANDARD),
                composer.compose_dataset(registry.get("asset.market_technical"), asset_context, detail_level=DetailLevel.STANDARD),
                composer.compose_dataset(registry.get("fx.overview"), fx_context, detail_level=DetailLevel.STANDARD),
                composer.compose_dataset(registry.get("fx.market_technical"), fx_context, detail_level=DetailLevel.STANDARD),
                composer.compose_dataset(registry.get("fx.direct_exposure"), fx_context, detail_level=DetailLevel.STANDARD),
            )

        results = await asyncio.wait_for(_run(), timeout=30)
        assert len(results) == 6
        for composition in results:
            assert composition.sections
