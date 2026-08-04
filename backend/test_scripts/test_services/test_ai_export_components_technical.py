"""Focused tests for the real Portfolio/Broker/Asset/FX AI Export "technical wave"
`ComponentSpec` builders (Phase 0 AI Export refinement, "shared technical wave").

Covers `backend.app.services.ai_export.components.technical_shared`,
`portfolio_broker_technical` and `asset_fx_technical`: the one curated
plugin bundle reused unchanged across every Asset-like target, warm-up-aware
loading via `AssetSourceManager.get_prices_bulk`/`backend.app.services.fx.
convert_bulk`, strict period slicing (warm-up never emitted), multi-output OHLC
row bucketing with dated cells, detail-owned event density, full portfolio/broker universe
analysis with weighted/unweighted breadth, partial-success isolation,
authoritative-vs-unavailable volume gating, FX no-volume gating, resource
memoization and deterministic ordering.

Mirrors `test_ai_export_components_portfolio_broker_financial.py`'s lightweight
pattern: no real database schema (a tableless in-memory `AsyncSession` only
satisfies `BuildContext`'s `isinstance` check). `AssetSourceManager.
get_prices_bulk`/`PortfolioService.get_report`/`technical_shared.convert_bulk`
are monkeypatched with deterministic synthetic data, but every monkeypatch
still drives the **real** `SignalService.compute`/`AssetSourceManager.
derive_signal_source_capability` so indicator/warm-up/volume-gating behavior
is genuinely exercised, not stubbed away.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.schemas.common import BackwardFillInfo, Currency
from backend.app.schemas.portfolio import (
    AssetPeriodContribution,
    PortfolioReportMetadata,
    PortfolioReportResponse,
    PositionsContribution,
)
from backend.app.schemas.prices import FAPricePoint, FAPriceQueryResult
from backend.app.schemas.signals import (
    SignalBandComponent,
    SignalBandPoint,
    SignalBandSeries,
    SignalBandValueSource,
    SignalCadence,
    SignalDomain,
    SignalExecutionContext,
    SignalLineCrossoverRequest,
    SignalOutputValueSource,
    SignalPricePoint,
    SignalPriceValueSource,
    SignalReferenceLevel,
    SignalStatus,
    SignalTemporalClass,
    SignalThresholdCrossingRequest,
)
from backend.app.services.ai_export.components import asset_fx_technical, portfolio_broker_technical, technical_context, technical_shared
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.resources import (
    FxRateObservation,
    FxRateSeriesResource,
    PriceResultsResource,
)
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.technical_context import (
    ASSET_TECHNICAL_CONTEXT_COMPONENTS,
    BROKER_TECHNICAL_CONTEXT_COMPONENTS,
    FX_TECHNICAL_CONTEXT_COMPONENTS,
    PORTFOLIO_TECHNICAL_CONTEXT_COMPONENTS,
)
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain, PeriodBehavior
from backend.app.services.ai_export.dependencies import (
    BuildContext,
    build_bucket_plan_for_scope,
    build_indicator_bucket_plan_for_scope,
)
from backend.app.services.ai_export.temporal import (
    Bucket,
    BucketingPolicy,
    BucketPlan,
    DiscreteEvent,
)
from backend.app.services.ai_export.temporal.points import ContinuousMultiOutputPoint
from backend.app.services.ai_export.temporal.policy import (
    BucketDetailLevel,
    EventSelectionPolicy,
    indicator_history_row_limit,
)
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.portfolio_service import PortfolioService
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.app.services.signal_plugins.drawdown import DrawdownParams, DrawdownPlugin
from backend.app.services.signal_service import SignalService

#: Exact replica of legacy `ASSET_FULL_BUNDLE`'s 20 signal instance IDs
#: (`backend/app/services/ai_export/profiles/asset.py` lines 320-437).
ASSET_BUNDLE_INSTANCE_IDS = frozenset(
    {
        "ema_20",
        "ema_50",
        "ema_200",
        "sma_50",
        "sma_200",
        "kama_20",
        "aroon_25",
        "adx_14",
        "donchian_20",
        "rsi_14",
        "macd_12_26_9",
        "ppo_12_26_9",
        "roc_20",
        "stoch_rsi_14_3",
        "cci_20",
        "bollinger_20_2",
        "atr_14",
        "natr_14",
        "mfi_14",
        "obv",
    }
)

#: Exact replica of legacy `FX_FULL_BUNDLE`'s 12 signal instance IDs
#: (`backend/app/services/ai_export/profiles/fx.py` lines 233-292).
FX_BUNDLE_INSTANCE_IDS = frozenset(
    {
        "ema_20",
        "ema_50",
        "ema_200",
        "sma_50",
        "sma_200",
        "kama_20",
        "rsi_14",
        "macd_12_26_9",
        "ppo_12_26_9",
        "roc_20",
        "stoch_rsi_14_3",
        "bollinger_20_2",
    }
)

ASSET_TEMPORAL_CLASS_BY_INSTANCE = {
    "ema_20": SignalTemporalClass.MEDIUM,
    "ema_50": SignalTemporalClass.SLOW,
    "ema_200": SignalTemporalClass.VERY_SLOW,
    "sma_50": SignalTemporalClass.SLOW,
    "sma_200": SignalTemporalClass.VERY_SLOW,
    "kama_20": SignalTemporalClass.MEDIUM,
    "aroon_25": SignalTemporalClass.MEDIUM,
    "adx_14": SignalTemporalClass.MEDIUM,
    "donchian_20": SignalTemporalClass.MEDIUM_FAST,
    "rsi_14": SignalTemporalClass.VERY_FAST,
    "macd_12_26_9": SignalTemporalClass.MEDIUM_FAST,
    "ppo_12_26_9": SignalTemporalClass.MEDIUM_FAST,
    "roc_20": SignalTemporalClass.FAST,
    "stoch_rsi_14_3": SignalTemporalClass.VERY_FAST,
    "cci_20": SignalTemporalClass.FAST,
    "bollinger_20_2": SignalTemporalClass.MEDIUM_FAST,
    "atr_14": SignalTemporalClass.FAST,
    "natr_14": SignalTemporalClass.FAST,
    "mfi_14": SignalTemporalClass.VERY_FAST,
    "obv": SignalTemporalClass.MEDIUM,
}

#: Exact replica of legacy `_asset_annotations(include_standard=True)`'s 19 annotation keys.
ASSET_BUNDLE_ANNOTATION_KEYS = frozenset(
    {
        "price_ema_20",
        "ema_20_ema_50",
        "ema_50_ema_200",
        "rsi_14_oversold_30",
        "rsi_14_overbought_70",
        "macd_signal",
        "macd_histogram_zero",
        "mfi_14_oversold_20",
        "mfi_14_overbought_80",
        "price_bollinger_lower",
        "price_bollinger_middle",
        "price_bollinger_upper",
        "adx_14_trend_25",
        "stoch_rsi_k_d",
        "stoch_rsi_k_oversold_20",
        "stoch_rsi_k_overbought_80",
        "price_donchian_lower",
        "price_donchian_middle",
        "price_donchian_upper",
    }
)

#: Exact replica of legacy `_fx_annotations(include_standard=True)`'s 14 annotation keys.
FX_BUNDLE_ANNOTATION_KEYS = frozenset(
    {
        "rate_ema_20",
        "ema_20_ema_50",
        "ema_50_ema_200",
        "rsi_14_oversold_30",
        "rsi_14_overbought_70",
        "ppo_signal",
        "ppo_histogram_zero",
        "rate_bollinger_lower",
        "rate_bollinger_middle",
        "rate_bollinger_upper",
        "roc_20_zero",
        "stoch_rsi_k_d",
        "stoch_rsi_k_oversold_20",
        "stoch_rsi_k_overbought_80",
    }
)

CURRENCY = "USD"

# =============================================================================
# Local, DB-free stub ComponentSpecs for `asset.identity`/`fx.pair_identity`
# =============================================================================
#
# The real `ASSET_IDENTITY_SPEC` (`asset_core.py`) / `fx.pair_identity`
# (`fx_core.py`) builders issue real DB queries against `Asset`/other tables -
# incompatible with this test file's tableless in-memory session (matching
# `test_ai_export_components_portfolio_broker_financial.py`'s own approach of
# never touching a live DB). These stubs satisfy `ComponentRegistry`'s
# dependency-resolution requirement only; the technical wave's own builders
# never read their payload.


class _StubIdentityPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool = True


async def _build_stub_identity(context, dependencies):  # noqa: ARG001
    return _StubIdentityPayload()


ASSET_IDENTITY_STUB = ComponentSpec(
    component_id="asset.identity",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=_StubIdentityPayload,
    builder=_build_stub_identity,
    period_behavior=PeriodBehavior.NONE,
)

FX_PAIR_IDENTITY_STUB = ComponentSpec(
    component_id="fx.pair_identity",
    version=1,
    domains=frozenset({Domain.FX}),
    output_model=_StubIdentityPayload,
    builder=_build_stub_identity,
    period_behavior=PeriodBehavior.NONE,
)


def _registry() -> ComponentRegistry:
    return ComponentRegistry(
        (
            *portfolio_broker_technical.PORTFOLIO_BROKER_TECHNICAL_COMPONENTS,
            *asset_fx_technical.ASSET_FX_TECHNICAL_COMPONENTS,
            ASSET_IDENTITY_STUB,
            FX_PAIR_IDENTITY_STUB,
        )
    )


# =============================================================================
# Scope/context construction helpers
# =============================================================================


def _scope(**overrides) -> BuildScope:
    defaults = {
        "request_id": "req-1",
        "user_id": 1,
        "domain": Domain.PORTFOLIO,
        "detail_level": DetailLevel.STANDARD,
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 2, 28),
        "target_currency": CURRENCY,
        "broker_scope": (),
    }
    defaults.update(overrides)
    return BuildScope(**defaults)


def _asset_scope(asset_id: int = 1, **overrides) -> BuildScope:
    return _scope(domain=Domain.ASSET, asset_id=asset_id, **overrides)


def _fx_scope(base: str = "USD", quote: str = "EUR", **overrides) -> BuildScope:
    overrides.setdefault("target_currency", quote)
    return _scope(domain=Domain.FX, base_currency=base, quote_currency=quote, **overrides)


def _broker_scope(broker_id: int = 1, **overrides) -> BuildScope:
    return _scope(domain=Domain.BROKER, broker_id=broker_id, broker_scope=(broker_id,), **overrides)


def _make_async_session() -> AsyncSession:
    """Tableless in-memory `AsyncSession`: only satisfies `BuildContext`'s isinstance check."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    return AsyncSession(engine)


def _make_context(scope: BuildScope, session: AsyncSession | None = None) -> BuildContext:
    bucket_plan = build_bucket_plan_for_scope(scope)
    return BuildContext(_registry(), request_id=scope.request_id, scope=scope, bucket_plan=bucket_plan, session=(session if session is not None else _make_async_session()))


# =============================================================================
# Deterministic synthetic price/rate generation
# =============================================================================


def _synthetic_close(asset_id: int, day: date) -> Decimal:
    ordinal = day.toordinal()
    base = 100 + asset_id * 5
    wave = 10 * math.sin(ordinal / 7.0)
    drift = (ordinal % 30) * 0.05
    return Decimal(str(round(base + wave + drift, 4)))


def _synthetic_volume(asset_id: int, day: date) -> Decimal:
    ordinal = day.toordinal()
    return Decimal(1000 + asset_id * 10 + (ordinal % 50) * 10)


def _fa_price_point(asset_id: int, day: date, *, source_plugin_key: str | None = "yfinance", with_volume: bool = True) -> FAPricePoint:
    close = _synthetic_close(asset_id, day)
    return FAPricePoint(
        date=day,
        open=close,
        high=close * Decimal("1.01"),
        low=close * Decimal("0.99"),
        close=close,
        volume=(_synthetic_volume(asset_id, day) if with_volume else None),
        currency=CURRENCY,
        source_plugin_key=source_plugin_key,
        backward_fill_info=None,
    )


def _daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _make_fake_get_prices_bulk(*, source_plugin_key: str | None = "yfinance", with_volume: bool = True):
    """Builds a fake `AssetSourceManager.get_prices_bulk` driving the real signal engine.

    For each `FAPriceQueryItem`, computes the real warm-up plan (via
    `SignalService.prepare_plan`), generates synthetic deterministic OHLCV
    prices over `[visible_start - warmup, visible_end]`, derives capability via
    the real `AssetSourceManager.derive_signal_source_capability`, computes
    real signals over the full (warm-up-inclusive) series, then slices
    `result.prices` to the visible period only - exactly mirroring the
    production `get_prices_bulk` contract (see `asset_source.py`'s own
    "Signal computation and response slicing" section).
    """
    calls: list[int] = []

    async def _fake(requests, session):  # noqa: ARG001
        calls.append(len(requests))
        signal_service = SignalService()
        results: list[FAPriceQueryResult] = []
        for req in requests:
            visible_start = req.date_range.start
            visible_end = req.date_range.end or visible_start
            signal_context = SignalExecutionContext(
                domain=SignalDomain.ASSET,
                requested_range=req.date_range,
                cadence=SignalCadence.DAILY,
                source_reference=f"asset:{req.asset_id}",
            )
            plan = signal_service.prepare_plan(req.signals, signal_context, req.annotation_requests)
            warmup_days = min(plan.max_history_points_before_visible, (visible_start - date.min).days)
            load_start = visible_start - timedelta(days=warmup_days)

            fa_points = [_fa_price_point(req.asset_id, day, source_plugin_key=source_plugin_key, with_volume=with_volume) for day in _daterange(load_start, visible_end)]
            signal_points = [SignalPricePoint(date=p.date, open=p.open, high=p.high, low=p.low, close=p.close, volume=p.volume) for p in fa_points]
            capability = AssetSourceManager.derive_signal_source_capability(fa_points)
            signals = await signal_service.compute(
                req.signals,
                signal_points,
                signal_context,
                annotation_requests=req.annotation_requests,
                source_capability=capability,
            )
            visible_prices = [p for p in fa_points if visible_start <= p.date <= visible_end] if req.include_price else []
            results.append(FAPriceQueryResult(asset_id=req.asset_id, prices=visible_prices, events=[], errors=[], signals=signals))
        return results

    return _fake, calls


def _patch_get_prices_bulk(monkeypatch: pytest.MonkeyPatch, *, source_plugin_key: str | None = "yfinance", with_volume: bool = True) -> list[int]:
    fake, calls = _make_fake_get_prices_bulk(source_plugin_key=source_plugin_key, with_volume=with_volume)
    monkeypatch.setattr(AssetSourceManager, "get_prices_bulk", staticmethod(fake))
    return calls


def _synthetic_fx_rate(day: date) -> Decimal:
    ordinal = day.toordinal()
    return Decimal(str(round(1.1 + (ordinal % 20) * 0.005 + 0.05 * math.sin(ordinal / 5.0), 6)))


def _patch_convert_bulk(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Monkeypatches `technical_shared.convert_bulk` with a deterministic synthetic FX rate function."""
    calls: list[int] = []

    async def _fake_convert_bulk(session, conversions, raise_on_error=True):  # noqa: ARG001
        calls.append(len(conversions))
        results = []
        for amount_currency, to_currency, as_of_date in conversions:
            rate = _synthetic_fx_rate(as_of_date)
            converted = Currency(code=to_currency, amount=amount_currency.amount * rate)
            results.append((converted, as_of_date, False))
        return results, []

    monkeypatch.setattr(technical_shared, "convert_bulk", _fake_convert_bulk)
    return calls


# =============================================================================
# Portfolio/Broker report fixtures
# =============================================================================


def _contribution(asset_id: int, *, end_value: object = 1000, is_fully_sold: bool = False, broker_id: int = 1) -> AssetPeriodContribution:
    return AssetPeriodContribution(
        asset_id=asset_id,
        asset_name=f"Asset {asset_id}",
        asset_type="EQUITY",
        broker_id=broker_id,
        broker_name=f"Broker {broker_id}",
        end_value=(Decimal(str(end_value)) if end_value is not None else None),
        is_fully_sold=is_fully_sold,
    )


def _report(scope: BuildScope, positions: list[AssetPeriodContribution]) -> PortfolioReportResponse:
    return PortfolioReportResponse(
        metadata=PortfolioReportMetadata(target_currency=scope.target_currency, generated_at=scope.snapshot_as_of),
        positions_contribution=PositionsContribution(positions=positions),
    )


def _patch_get_report(monkeypatch: pytest.MonkeyPatch, report: PortfolioReportResponse) -> list[int]:
    calls: list[int] = []

    async def _fake_get_report(self, user_id, query):  # noqa: ARG001
        calls.append(1)
        return report

    monkeypatch.setattr(PortfolioService, "get_report", _fake_get_report)
    return calls


def _envelope_payload(envelope: SectionEnvelope | None) -> dict:
    assert envelope is not None
    return envelope.payload


# =============================================================================
# 1. Curated bundle stability across detail levels (requirement 1, 8, 9)
# =============================================================================


class TestCuratedBundleAcrossDetailLevels:
    @pytest.mark.asyncio
    async def test_same_indicator_and_event_cardinality_across_detail_levels_asset(self, monkeypatch):
        payloads = {}
        for detail_level in (DetailLevel.COMPACT, DetailLevel.STANDARD, DetailLevel.FULL):
            _patch_get_prices_bulk(monkeypatch)
            scope = _asset_scope(detail_level=detail_level)
            context = _make_context(scope)
            indicators_envelope = await context.resolve("asset.indicators", required=True)
            events_envelope = await context.resolve("asset.states_events", required=True)
            payloads[detail_level] = (_envelope_payload(indicators_envelope), _envelope_payload(events_envelope), context)

        compact_ind, compact_events, compact_ctx = payloads[DetailLevel.COMPACT]
        standard_ind, standard_events, standard_ctx = payloads[DetailLevel.STANDARD]
        full_ind, full_events, full_ctx = payloads[DetailLevel.FULL]

        compact_keys = sorted((entry["instance_id"], column["column_key"]) for entry in compact_ind["indicators"] for column in entry["columns"])
        standard_keys = sorted((entry["instance_id"], column["column_key"]) for entry in standard_ind["indicators"] for column in entry["columns"])
        full_keys = sorted((entry["instance_id"], column["column_key"]) for entry in full_ind["indicators"] for column in entry["columns"])
        assert compact_keys == standard_keys == full_keys
        assert compact_keys  # non-empty: curated bundle actually produced output series
        assert len(compact_ind["indicators"]) == 20
        assert all(entry["result_status"] in {"ok", "partial"} for entry in compact_ind["indicators"])
        assert all((entry["partial_reason_code"] is not None) == (entry["result_status"] == "partial") for entry in compact_ind["indicators"])

        assert compact_events["detected_event_count"] == standard_events["detected_event_count"] == full_events["detected_event_count"]
        assert compact_events["exported_event_count"] <= standard_events["exported_event_count"] <= full_events["exported_event_count"]

        by_detail = {
            DetailLevel.COMPACT: (compact_ind, compact_ctx),
            DetailLevel.STANDARD: (standard_ind, standard_ctx),
            DetailLevel.FULL: (full_ind, full_ctx),
        }
        for detail_level, (payload, current_context) in by_detail.items():
            by_instance = {indicator["instance_id"]: indicator for indicator in payload["indicators"]}
            assert by_instance["rsi_14"]["temporal_class"] == "very_fast"
            assert by_instance["ema_20"]["temporal_class"] == "medium"
            rsi_limit = indicator_history_row_limit(BucketDetailLevel(detail_level.value))
            assert len(by_instance["rsi_14"]["rows"]) == min(
                by_instance["rsi_14"]["source_nonempty_row_count"],
                rsi_limit or by_instance["rsi_14"]["source_nonempty_row_count"],
            )
            assert by_instance["rsi_14"]["source_bucket_count"] == len(current_context.bucket_plan.buckets)
            expected_ema_plan = build_indicator_bucket_plan_for_scope(
                current_context.scope,
                SignalTemporalClass.MEDIUM,
            )
            assert by_instance["ema_20"]["source_bucket_count"] == len(expected_ema_plan.buckets)
            assert len(by_instance["ema_20"]["rows"]) == min(
                by_instance["ema_20"]["source_nonempty_row_count"],
                rsi_limit or by_instance["ema_20"]["source_nonempty_row_count"],
            )
            assert by_instance["ema_20"]["period_summary"]

        compact_by_id = {item["instance_id"]: item for item in compact_ind["indicators"]}
        full_by_id = {item["instance_id"]: item for item in full_ind["indicators"]}
        for instance_id in compact_by_id:
            assert compact_by_id[instance_id]["period_summary"] == full_by_id[instance_id]["period_summary"]
            assert compact_by_id[instance_id]["columns"] == full_by_id[instance_id]["columns"]


# =============================================================================
# 1b. Exact domain-specific fixed bundle composition/topology (requirement 1, 9)
# =============================================================================
#
# Parent product review rejected an earlier 8-plugin curation as an
# unapproved regression from legacy Full-detail behavior; these tests pin
# the new bundles to the *exact* legacy `ASSET_FULL_BUNDLE` (20 instances) /
# `FX_FULL_BUNDLE` (12 instances) signal sets and their exact annotation
# topology (never re-derived from `profiles/` at runtime - only replicated
# here) so a future regression back to a smaller curated set fails loudly.


class TestExactBundleComposition:
    def test_asset_bundle_has_exact_20_instance_set(self):
        signals = technical_shared.ASSET_CURATED_SIGNALS
        assert len(signals) == 20
        assert {spec.instance_id for spec in signals} == ASSET_BUNDLE_INSTANCE_IDS

    def test_fx_bundle_has_exact_12_instance_set(self):
        signals = technical_shared.FX_CURATED_SIGNALS
        assert len(signals) == 12
        assert {spec.instance_id for spec in signals} == FX_BUNDLE_INSTANCE_IDS

    @pytest.mark.parametrize(
        "specs",
        (
            technical_shared.ASSET_CURATED_SIGNALS,
            technical_shared.FX_CURATED_SIGNALS,
        ),
    )
    def test_every_curated_instance_resolves_plugin_owned_temporal_class(
        self,
        specs,
    ):
        for spec in specs:
            plugin_class = SignalPluginRegistry.get_plugin(spec.signal_code)
            assert plugin_class is not None
            assert plugin_class.resolve_ai_export_temporal_class(spec.params) == ASSET_TEMPORAL_CLASS_BY_INSTANCE[spec.instance_id]

    def test_asset_signal_requests_match_curated_spec_1_to_1(self):
        requests = technical_shared.build_asset_signal_requests()
        assert len(requests) == 20
        assert {request.instance_id for request in requests} == ASSET_BUNDLE_INSTANCE_IDS
        by_id = {request.instance_id: request for request in requests}
        assert by_id["rsi_14"].params == {"period": 14, "overbought": 70, "oversold": 30}
        assert by_id["mfi_14"].params == {"period": 14, "overbought": 80, "oversold": 20}
        assert by_id["macd_12_26_9"].params == {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}
        assert by_id["bollinger_20_2"].params == {"period": 20, "multiplier": 2.0}
        assert by_id["obv"].params == {}

    @pytest.mark.parametrize(
        "requests",
        (
            technical_shared.build_asset_annotation_requests(),
            technical_shared.build_fx_annotation_requests(),
        ),
    )
    def test_curated_annotations_are_observed_only_and_scale_aware(self, requests):
        assert requests
        assert all(request.observed_only for request in requests)
        assert all(request.epsilon == pytest.approx(1e-12) for request in requests)
        assert all(request.relative_epsilon == pytest.approx(1e-12) for request in requests)

    def test_fx_signal_requests_match_curated_spec_1_to_1(self):
        requests = technical_shared.build_fx_signal_requests()
        assert len(requests) == 12
        assert {request.instance_id for request in requests} == FX_BUNDLE_INSTANCE_IDS

    def test_asset_annotation_requests_have_exact_19_key_set(self):
        annotations = technical_shared.build_asset_annotation_requests()
        assert len(annotations) == 19
        assert {annotation.key for annotation in annotations} == ASSET_BUNDLE_ANNOTATION_KEYS

    def test_fx_annotation_requests_have_exact_14_key_set(self):
        annotations = technical_shared.build_fx_annotation_requests()
        assert len(annotations) == 14
        assert {annotation.key for annotation in annotations} == FX_BUNDLE_ANNOTATION_KEYS

    def test_asset_annotation_topology_matches_legacy_exactly(self):
        by_key = {annotation.key: annotation for annotation in technical_shared.build_asset_annotation_requests()}

        price_ema_20 = by_key["price_ema_20"]
        assert isinstance(price_ema_20, SignalLineCrossoverRequest)
        assert price_ema_20.attach_to_instance_id == "ema_20"
        assert isinstance(price_ema_20.left, SignalPriceValueSource)
        assert price_ema_20.right == SignalOutputValueSource(instance_id="ema_20", series_key="ema")

        ema_20_ema_50 = by_key["ema_20_ema_50"]
        assert ema_20_ema_50.attach_to_instance_id == "ema_20"
        assert ema_20_ema_50.left == SignalOutputValueSource(instance_id="ema_20", series_key="ema")
        assert ema_20_ema_50.right == SignalOutputValueSource(instance_id="ema_50", series_key="ema")

        ema_50_ema_200 = by_key["ema_50_ema_200"]
        assert ema_50_ema_200.attach_to_instance_id == "ema_50"
        assert ema_50_ema_200.left == SignalOutputValueSource(instance_id="ema_50", series_key="ema")
        assert ema_50_ema_200.right == SignalOutputValueSource(instance_id="ema_200", series_key="ema")

        rsi_oversold = by_key["rsi_14_oversold_30"]
        assert isinstance(rsi_oversold, SignalThresholdCrossingRequest)
        assert rsi_oversold.attach_to_instance_id == "rsi_14"
        assert rsi_oversold.source == SignalOutputValueSource(instance_id="rsi_14", series_key="rsi")
        assert rsi_oversold.threshold == 30
        assert by_key["rsi_14_overbought_70"].threshold == 70

        macd_signal = by_key["macd_signal"]
        assert macd_signal.attach_to_instance_id == "macd_12_26_9"
        assert macd_signal.left == SignalOutputValueSource(instance_id="macd_12_26_9", series_key="macd")
        assert macd_signal.right == SignalOutputValueSource(instance_id="macd_12_26_9", series_key="signal")

        macd_zero = by_key["macd_histogram_zero"]
        assert macd_zero.attach_to_instance_id == "macd_12_26_9"
        assert macd_zero.source == SignalOutputValueSource(instance_id="macd_12_26_9", series_key="histogram")
        assert macd_zero.threshold == 0

        assert by_key["mfi_14_oversold_20"].threshold == 20
        assert by_key["mfi_14_overbought_80"].threshold == 80
        assert by_key["mfi_14_oversold_20"].source == SignalOutputValueSource(instance_id="mfi_14", series_key="mfi")

        for suffix, component in (("lower", SignalBandComponent.LOWER), ("middle", SignalBandComponent.MIDDLE), ("upper", SignalBandComponent.UPPER)):
            bollinger = by_key[f"price_bollinger_{suffix}"]
            assert bollinger.attach_to_instance_id == "bollinger_20_2"
            assert isinstance(bollinger.left, SignalPriceValueSource)
            assert bollinger.right == SignalBandValueSource(instance_id="bollinger_20_2", series_key="bands", component=component)

            donchian = by_key[f"price_donchian_{suffix}"]
            assert donchian.attach_to_instance_id == "donchian_20"
            assert isinstance(donchian.left, SignalPriceValueSource)
            assert donchian.right == SignalBandValueSource(instance_id="donchian_20", series_key="channels", component=component)

        adx = by_key["adx_14_trend_25"]
        assert adx.attach_to_instance_id == "adx_14"
        assert adx.source == SignalOutputValueSource(instance_id="adx_14", series_key="adx")
        assert adx.threshold == 25

        stoch_kd = by_key["stoch_rsi_k_d"]
        assert stoch_kd.attach_to_instance_id == "stoch_rsi_14_3"
        assert stoch_kd.left == SignalOutputValueSource(instance_id="stoch_rsi_14_3", series_key="k")
        assert stoch_kd.right == SignalOutputValueSource(instance_id="stoch_rsi_14_3", series_key="d")
        assert by_key["stoch_rsi_k_oversold_20"].threshold == 20
        assert by_key["stoch_rsi_k_overbought_80"].threshold == 80
        assert by_key["stoch_rsi_k_oversold_20"].source == SignalOutputValueSource(instance_id="stoch_rsi_14_3", series_key="k")

    def test_fx_annotation_topology_matches_legacy_exactly(self):
        by_key = {annotation.key: annotation for annotation in technical_shared.build_fx_annotation_requests()}

        rate_ema_20 = by_key["rate_ema_20"]
        assert rate_ema_20.attach_to_instance_id == "ema_20"
        assert isinstance(rate_ema_20.left, SignalPriceValueSource)
        assert rate_ema_20.right == SignalOutputValueSource(instance_id="ema_20", series_key="ema")

        ppo_signal = by_key["ppo_signal"]
        assert ppo_signal.attach_to_instance_id == "ppo_12_26_9"
        assert ppo_signal.left == SignalOutputValueSource(instance_id="ppo_12_26_9", series_key="ppo")
        assert ppo_signal.right == SignalOutputValueSource(instance_id="ppo_12_26_9", series_key="signal")

        ppo_zero = by_key["ppo_histogram_zero"]
        assert ppo_zero.attach_to_instance_id == "ppo_12_26_9"
        assert ppo_zero.source == SignalOutputValueSource(instance_id="ppo_12_26_9", series_key="histogram")
        assert ppo_zero.threshold == 0

        roc_zero = by_key["roc_20_zero"]
        assert roc_zero.attach_to_instance_id == "roc_20"
        assert roc_zero.source == SignalOutputValueSource(instance_id="roc_20", series_key="roc")
        assert roc_zero.threshold == 0

        # No MACD-based annotation in the FX topology (unlike Asset) - FX uses
        # PPO for the line/hist-zero pair instead, exactly like legacy.
        assert not any(key.startswith("macd") for key in by_key)
        # No ADX/Donchian annotations in FX (neither signal is in the FX bundle).
        assert not any("adx" in key or "donchian" in key for key in by_key)

    @pytest.mark.asyncio
    async def test_portfolio_per_asset_technical_uses_the_exact_asset_bundle(self, monkeypatch):
        """Portfolio/Broker per-asset technical analysis shares the *same* fixed
        Asset bundle (20 instances) - not a separately-curated subset."""
        positions = [_contribution(1)]
        _patch_get_prices_bulk(monkeypatch)
        scope = _scope()
        report = _report(scope, positions)
        _patch_get_report(monkeypatch, report)
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("portfolio.technical_indicators", required=True))

        asset_entry = next(asset for asset in payload["assets"] if asset["asset_id"] == 1)
        instance_ids = {entry["instance_id"] for entry in asset_entry["indicators"]}
        assert instance_ids == ASSET_BUNDLE_INSTANCE_IDS


class TestBrokerTechnicalPriceRegistry:
    def test_prices_match_portfolio_metadata_and_precede_indicators(self):
        specs = portfolio_broker_technical.PORTFOLIO_BROKER_TECHNICAL_COMPONENTS
        by_id = {spec.component_id: spec for spec in specs}
        order = tuple(spec.component_id for spec in specs)
        portfolio_prices = by_id["portfolio.technical_prices"]
        broker_prices = by_id["broker.technical_prices"]
        broker_indicators = by_id["broker.technical_indicators"]

        assert len(specs) == 8
        assert broker_prices.domains == frozenset({Domain.BROKER})
        assert broker_prices.output_model is portfolio_prices.output_model
        assert broker_prices.period_behavior == portfolio_prices.period_behavior == PeriodBehavior.AGGREGATED
        assert broker_prices.aggregator == portfolio_prices.aggregator
        assert broker_indicators.dependencies == ("broker.technical_prices",)
        assert order.index("broker.technical_prices") + 1 == order.index("broker.technical_indicators")


# =============================================================================
# 2. Warm-up exclusion (requirement 2, 3)
# =============================================================================


class TestWarmupExclusion:
    @pytest.mark.asyncio
    async def test_asset_ohlc_returns_never_emits_before_scope_start(self, monkeypatch):
        _patch_get_prices_bulk(monkeypatch)
        scope = _asset_scope()
        context = _make_context(scope)
        envelope = await context.resolve("asset.ohlc_returns", required=True)
        payload = _envelope_payload(envelope)

        assert payload["price_basis"] == "observed_close"
        assert payload["buckets"][0]["start_date"] == scope.period_start.isoformat()
        assert payload["buckets"][-1]["end_date"] == scope.period_end.isoformat()
        for bucket in payload["buckets"]:
            assert date.fromisoformat(bucket["start_date"]) >= scope.period_start
            assert date.fromisoformat(bucket["end_date"]) <= scope.period_end

    @pytest.mark.asyncio
    async def test_indicator_series_never_emits_before_scope_start(self, monkeypatch):
        _patch_get_prices_bulk(monkeypatch)
        scope = _asset_scope()
        context = _make_context(scope)
        envelope = await context.resolve("asset.indicators", required=True)
        payload = _envelope_payload(envelope)

        assert payload["indicators"], "expected at least one curated indicator output"
        for indicator in payload["indicators"]:
            for row in indicator["rows"]:
                assert date.fromisoformat(row["start_date"]) >= scope.period_start
                assert date.fromisoformat(row["end_date"]) <= scope.period_end

    @pytest.mark.asyncio
    async def test_events_never_emit_before_scope_start(self, monkeypatch):
        _patch_get_prices_bulk(monkeypatch)
        scope = _asset_scope()
        context = _make_context(scope)
        envelope = await context.resolve("asset.states_events", required=True)
        payload = _envelope_payload(envelope)

        for bucket in payload["buckets"]:
            for event in bucket["events"]:
                assert date.fromisoformat(event["date"]) >= scope.period_start
                assert date.fromisoformat(event["date"]) <= scope.period_end


# =============================================================================
# 3. Multi-output OHLC (requirement 3)
# =============================================================================


class TestMultiOutputOhlc:
    @pytest.mark.asyncio
    async def test_price_buckets_carry_first_min_max_last_and_simple_return(self, monkeypatch):
        _patch_get_prices_bulk(monkeypatch)
        scope = _asset_scope()
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("asset.ohlc_returns", required=True))

        non_empty = [bucket for bucket in payload["buckets"] if bucket["observation_count"] > 0]
        assert non_empty
        previous_close = None
        for bucket in payload["buckets"]:
            if bucket["observation_count"] == 0:
                assert bucket["simple_return"] is None
                assert bucket["return_start_date"] is None
                continue
            assert bucket["calendar_days"] == (date.fromisoformat(bucket["end_date"]) - date.fromisoformat(bucket["start_date"])).days + 1
            assert set(bucket["first"]) == {"close"}
            assert set(bucket["last"]) == {"close"}
            assert set(bucket["minimum"]) == {"close"}
            assert set(bucket["maximum"]) == {"close"}
            assert bucket["minimum"]["close"] <= bucket["first"]["close"] <= bucket["maximum"]["close"]
            assert bucket["minimum"]["close"] <= bucket["last"]["close"] <= bucket["maximum"]["close"]
            assert bucket["minimum_date"] is not None
            assert bucket["maximum_date"] is not None
            if previous_close is None:
                assert bucket["simple_return"] is None
                assert bucket["return_start_date"] is None
            else:
                assert bucket["simple_return"] == pytest.approx(bucket["last"]["close"] / previous_close - 1)
                assert bucket["return_start_date"] is not None
            previous_close = bucket["last"]["close"]

    def test_price_return_skips_empty_buckets_and_uses_previous_observation(self):
        start = date(2026, 1, 1)
        plan = BucketPlan(
            start=start,
            end=start + timedelta(days=3),
            policy=BucketingPolicy(max_bucket_days=1),
            buckets=tuple(
                Bucket(
                    index=index,
                    start_date=start + timedelta(days=index),
                    end_date=start + timedelta(days=index),
                )
                for index in range(4)
            ),
        )
        points = (
            ContinuousMultiOutputPoint(
                date=start,
                values={"close": Decimal("100")},
            ),
            ContinuousMultiOutputPoint(
                date=start + timedelta(days=2),
                values={"close": Decimal("110")},
            ),
            ContinuousMultiOutputPoint(
                date=start + timedelta(days=3),
                values={"close": Decimal("121")},
            ),
        )

        buckets = technical_shared.build_price_buckets(points, plan)

        assert buckets[0].simple_return is None
        assert buckets[1].observation_count == 0
        assert buckets[1].simple_return is None
        assert buckets[2].return_start_date == start
        assert buckets[2].simple_return == pytest.approx(0.1)
        assert buckets[3].return_start_date == start + timedelta(days=2)
        assert buckets[3].simple_return == pytest.approx(0.1)

    def test_asset_price_points_exclude_calendar_backfill(self):
        start = date(2026, 1, 2)
        result = FAPriceQueryResult(
            asset_id=1,
            prices=[
                _fa_price_point(1, start),
                _fa_price_point(1, start + timedelta(days=1)).model_copy(
                    update={
                        "backward_fill_info": BackwardFillInfo(
                            actual_rate_date=start,
                            days_back=1,
                        )
                    }
                ),
                _fa_price_point(1, start + timedelta(days=2)).model_copy(
                    update={
                        "backward_fill_info": BackwardFillInfo(
                            actual_rate_date=start,
                            days_back=2,
                        )
                    }
                ),
                _fa_price_point(1, start + timedelta(days=3)),
            ],
            events=[],
            errors=[],
            signals=[],
        )

        points = technical_shared.price_result_to_close_points(
            result,
            start=start,
            end=start + timedelta(days=3),
        )

        assert [point.date for point in points] == [
            start,
            start + timedelta(days=3),
        ]

    @pytest.mark.asyncio
    async def test_bollinger_band_buckets_use_lower_middle_upper_keys(self, monkeypatch):
        _patch_get_prices_bulk(monkeypatch)
        scope = _asset_scope()
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("asset.indicators", required=True))

        band_entries = [entry for entry in payload["indicators"] if entry["signal_code"] == "BOLLINGER"]
        assert band_entries, "expected BOLLINGER outputs in the curated bundle"
        for entry in band_entries:
            assert [column["column_key"] for column in entry["columns"]] == [
                "bands.lower",
                "bands.middle",
                "bands.upper",
            ]
            assert {column["kind"] for column in entry["columns"]} == {"band"}
            assert {column["aggregation_profile"] for column in entry["columns"]} == {"band_envelope"}
            populated = [row for row in entry["rows"] if row["observation_count"] > 0]
            assert populated
            for row in populated:
                assert set(row["cells"]) == {
                    "bands.lower",
                    "bands.middle",
                    "bands.upper",
                }
            range_cells = [cell for row in populated for cell in row["cells"].values() if cell is not None and cell["kind"] == "range"]
            assert range_cells
            assert all(
                set(cell)
                == {
                    "kind",
                    "observation_count",
                    "first",
                    "min",
                    "max",
                    "last",
                }
                for cell in range_cells
            )

    @pytest.mark.asyncio
    async def test_macd_outputs_share_one_temporally_local_row_table(self, monkeypatch):
        _patch_get_prices_bulk(monkeypatch)
        context = _make_context(_asset_scope())
        payload = _envelope_payload(await context.resolve("asset.indicators", required=True))

        macd = next(entry for entry in payload["indicators"] if entry["instance_id"] == "macd_12_26_9")
        expected_columns = {"macd", "signal", "histogram"}
        assert {column["column_key"] for column in macd["columns"]} == expected_columns
        assert all(set(row["cells"]) == expected_columns for row in macd["rows"])
        assert all(row["calendar_days"] == (date.fromisoformat(row["end_date"]) - date.fromisoformat(row["start_date"])).days + 1 for row in macd["rows"])
        macd_cells = [row["cells"]["macd"] for row in macd["rows"] if row["cells"]["macd"] is not None]
        assert any(cell["kind"] == "single" for cell in macd_cells)
        assert any(cell["kind"] == "range" for cell in macd_cells)

    def test_band_columns_keep_independent_extrema_dates(self):
        scope = _asset_scope(
            period_start=date(2025, 1, 1),
            period_end=date(2026, 1, 3),
            detail_level=DetailLevel.FULL,
        )
        context = _make_context(scope)
        indicator_plan = build_indicator_bucket_plan_for_scope(
            scope,
            SignalTemporalClass.MEDIUM_FAST,
        )
        bucket = next(bucket for bucket in indicator_plan.buckets if bucket.day_count >= 3)
        start = bucket.start_date
        middle = start + timedelta(days=1)
        end = start + timedelta(days=2)
        plugin_class = SignalPluginRegistry.get_plugin("BOLLINGER")
        assert plugin_class is not None
        output = plugin_class.output_specs[0]
        series = SignalBandSeries(
            key=output.key,
            label_key=output.label_key,
            description_key=output.description_key,
            semantic_id=output.semantic_id,
            semantic_description=output.semantic_description,
            unit=output.unit,
            axis=output.axis.model_copy(deep=True),
            view_transform=output.view_transform,
            style=output.style.model_copy(deep=True),
            points=[
                SignalBandPoint(date=start, lower=8, middle=10, upper=12),
                SignalBandPoint(
                    date=middle,
                    lower=4,
                    middle=11,
                    upper=15,
                ),
                SignalBandPoint(date=end, lower=6, middle=9, upper=13),
            ],
        )
        result = SimpleNamespace(
            instance_id="bollinger",
            signal_code="BOLLINGER",
            status=SignalStatus.OK,
            series=(series,),
            normalized_params={"period": 20, "multiplier": 2.0},
        )
        table = technical_shared.build_indicator_table_payloads(
            (result,),
            context,
        )[
            0
        ].model_dump(mode="json")
        row = next(row for row in table["rows"] if row["start_date"] == bucket.start_date.isoformat() and row["end_date"] == bucket.end_date.isoformat())

        assert row["cells"]["bands.lower"]["min"]["date"] == middle.isoformat()
        assert row["cells"]["bands.middle"]["last"]["date"] == end.isoformat()
        assert row["cells"]["bands.upper"]["max"]["date"] == middle.isoformat()
        assert table["period_summary"]["bands.lower"]["min"]["date"] == middle.isoformat()

    def test_unclassified_drawdown_is_not_silently_exported(self):
        start = date(2026, 1, 1)
        end = date(2026, 1, 3)
        signal_context = SignalExecutionContext(
            domain=SignalDomain.ASSET,
            requested_range={"start": start, "end": end},
            cadence=SignalCadence.DAILY,
            source_reference="asset:1",
        )
        price_points = (
            SignalPricePoint(date=start, close=Decimal("100")),
            SignalPricePoint(date=start + timedelta(days=1), close=Decimal("80")),
            SignalPricePoint(date=end, close=Decimal("90")),
        )
        computation = DrawdownPlugin().compute(
            price_points,
            (),
            DrawdownParams(),
            signal_context,
        )
        result = SimpleNamespace(
            instance_id="drawdown",
            signal_code="RISK_DRAWDOWN",
            status=SignalStatus.OK,
            series=computation.series,
            normalized_params={},
        )
        context = _make_context(
            _asset_scope(
                period_start=start,
                period_end=end,
            )
        )

        with pytest.raises(
            ValueError,
            match="requires exactly one matching rule",
        ):
            technical_shared.build_indicator_table_payloads(
                (result,),
                context,
            )

    @pytest.mark.asyncio
    async def test_fx_rate_ohlc_uses_rate_key(self, monkeypatch):
        _patch_convert_bulk(monkeypatch)
        scope = _fx_scope()
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("fx.rate_ohlc", required=True))

        non_empty = [bucket for bucket in payload["buckets"] if bucket["observation_count"] > 0]
        assert non_empty
        previous_close = None
        for bucket in payload["buckets"]:
            if bucket["observation_count"] == 0:
                assert bucket["simple_return"] is None
                continue
            assert set(bucket["first"]) == {"rate"}
            assert bucket["first"]["rate"] > 0
            if previous_close is None:
                assert bucket["simple_return"] is None
            else:
                assert bucket["simple_return"] == pytest.approx(bucket["last"]["rate"] / previous_close - 1)
            previous_close = bucket["last"]["rate"]


# =============================================================================
# 4. Event selection
# =============================================================================


class TestEventSelection:
    @staticmethod
    def _events(
        *,
        total: int,
        recent: int,
        snapshot: date,
        entity_id: str = "asset:1",
        annotation_key: str = "test_cross",
    ) -> tuple[DiscreteEvent, ...]:
        events = []
        for index in range(total):
            if index < recent:
                event_date = snapshot - timedelta(days=index % 31)
            else:
                event_date = snapshot - timedelta(days=31 + index - recent)
            events.append(
                DiscreteEvent(
                    date=event_date,
                    dedup_key=(entity_id, annotation_key, index),
                    payload={
                        "entity_id": entity_id,
                        "key": annotation_key,
                        "annotation_type": "line_crossover",
                        "signal_code": "EMA",
                        "semantic_description": "Test event.",
                        "direction": "up" if index % 2 == 0 else "down",
                        "values": {"difference": float(index + 1)},
                    },
                )
            )
        return tuple(events)

    @pytest.mark.parametrize(
        ("total", "recent", "expected"),
        (
            (8, 3, 8),
            (30, 4, 20),
            (50, 12, 20),
            (50, 25, 25),
            (200, 40, 40),
            (20, 0, 20),
            (0, 0, 0),
        ),
    )
    def test_event_selection_examples(
        self,
        total: int,
        recent: int,
        expected: int,
    ):
        snapshot = date(2026, 7, 30)

        selection = technical_shared.select_technical_events(
            self._events(
                total=total,
                recent=recent,
                snapshot=snapshot,
            ),
            snapshot_as_of=snapshot,
        )

        assert len(selection.events) == expected
        if total == 0:
            assert selection.summaries == ()
        else:
            summary = selection.summaries[0]
            assert summary.detected_count == total
            assert summary.recent_window_count == recent
            assert summary.exported_count == expected
            assert summary.selection_applied == (expected < total)
        assert [event.date for event in selection.events] == sorted(event.date for event in selection.events)

    def test_event_on_30_day_boundary_is_recent(self):
        snapshot = date(2026, 7, 30)
        events = (
            *self._events(total=19, recent=19, snapshot=snapshot),
            DiscreteEvent(
                date=snapshot - timedelta(days=30),
                dedup_key=("asset:1", "test_cross", "boundary"),
                payload={
                    "entity_id": "asset:1",
                    "key": "test_cross",
                    "annotation_type": "threshold_crossing",
                    "signal_code": "RSI",
                    "semantic_description": "Boundary event.",
                    "direction": "up",
                    "values": {"difference": 1.0},
                },
            ),
            DiscreteEvent(
                date=snapshot - timedelta(days=31),
                dedup_key=("asset:1", "test_cross", "older"),
                payload={
                    "entity_id": "asset:1",
                    "key": "test_cross",
                    "annotation_type": "threshold_crossing",
                    "signal_code": "RSI",
                    "semantic_description": "Older event.",
                    "direction": "down",
                    "values": {"difference": -1.0},
                },
            ),
        )

        selection = technical_shared.select_technical_events(
            events,
            snapshot_as_of=snapshot,
        )

        summary = selection.summaries[0]
        assert summary.detected_count == 21
        assert summary.recent_window_count == 20
        assert summary.exported_count == 20
        assert snapshot - timedelta(days=30) in {event.date for event in selection.events}
        assert snapshot - timedelta(days=31) not in {event.date for event in selection.events}

    @pytest.mark.parametrize(
        ("detail_level", "expected_recent_days", "expected_minimum"),
        (
            (DetailLevel.COMPACT, 7, 3),
            (DetailLevel.STANDARD, 21, 10),
            (DetailLevel.FULL, 30, 20),
        ),
    )
    def test_event_selection_policy_is_detail_owned(
        self,
        detail_level: DetailLevel,
        expected_recent_days: int,
        expected_minimum: int,
    ):
        snapshot = date(2026, 7, 30)
        selection = technical_shared.select_technical_events(
            self._events(total=50, recent=25, snapshot=snapshot),
            snapshot_as_of=snapshot,
            detail_level=detail_level,
        )
        policy = EventSelectionPolicy.for_detail_level(BucketDetailLevel(detail_level.value))

        assert policy.complete_recent_window_days == expected_recent_days
        assert policy.minimum_latest_events_per_annotation == expected_minimum
        assert (
            len(selection.events)
            == {
                DetailLevel.COMPACT: 8,
                DetailLevel.STANDARD: 22,
                DetailLevel.FULL: 25,
            }[detail_level]
        )

    def test_event_selection_is_independent_per_entity_and_annotation(self):
        snapshot = date(2026, 7, 30)
        events = (
            *self._events(
                total=30,
                recent=4,
                snapshot=snapshot,
                entity_id="asset:1",
                annotation_key="same_key",
            ),
            *self._events(
                total=8,
                recent=3,
                snapshot=snapshot,
                entity_id="asset:2",
                annotation_key="same_key",
            ),
            *self._events(
                total=50,
                recent=25,
                snapshot=snapshot,
                entity_id="asset:1",
                annotation_key="other_key",
            ),
        )

        selection = technical_shared.select_technical_events(
            events,
            snapshot_as_of=snapshot,
        )

        assert {(summary.entity_id, summary.annotation_key): summary.exported_count for summary in selection.summaries} == {
            ("asset:1", "other_key"): 25,
            ("asset:1", "same_key"): 20,
            ("asset:2", "same_key"): 8,
        }

    @pytest.mark.asyncio
    async def test_detected_and_exported_events_reconcile(self, monkeypatch):
        _patch_get_prices_bulk(monkeypatch)
        scope = _asset_scope(period_start=date(2025, 1, 1), period_end=date(2026, 6, 30), detail_level=DetailLevel.FULL)
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("asset.states_events", required=True))

        total_from_buckets = sum(bucket["event_count"] for bucket in payload["buckets"])
        assert total_from_buckets == payload["exported_event_count"]
        assert payload["detected_event_count"] >= payload["exported_event_count"]
        assert sum(summary["detected_count"] for summary in payload["selection_summaries"]) == payload["detected_event_count"]
        assert sum(summary["exported_count"] for summary in payload["selection_summaries"]) == payload["exported_event_count"]
        assert any(summary["selection_applied"] for summary in payload["selection_summaries"])
        for summary in payload["selection_summaries"]:
            assert summary["exported_count"] == min(
                summary["detected_count"],
                max(
                    technical_shared.EVENT_SELECTION_MINIMUM_LATEST,
                    summary["recent_window_count"],
                ),
            )
        for bucket in payload["buckets"]:
            assert len(bucket["events"]) == bucket["event_count"]

    @pytest.mark.asyncio
    async def test_empty_event_list_is_a_valid_payload(self, monkeypatch):
        # A very short, flat period yields no crossovers at all - a valid
        # empty payload, never a placeholder/error.
        async def _flat_get_prices_bulk(requests, session):  # noqa: ARG001
            signal_service = SignalService()
            results = []
            for req in requests:
                visible_start = req.date_range.start
                visible_end = req.date_range.end or visible_start
                signal_context = SignalExecutionContext(domain=SignalDomain.ASSET, requested_range=req.date_range, cadence=SignalCadence.DAILY, source_reference=f"asset:{req.asset_id}")
                plan = signal_service.prepare_plan(req.signals, signal_context, req.annotation_requests)
                warmup_days = min(plan.max_history_points_before_visible, (visible_start - date.min).days)
                load_start = visible_start - timedelta(days=warmup_days)
                flat_close = Decimal("100")
                fa_points = [FAPricePoint(date=day, open=flat_close, high=flat_close, low=flat_close, close=flat_close, volume=Decimal(1000), currency=CURRENCY, source_plugin_key="yfinance", backward_fill_info=None) for day in _daterange(load_start, visible_end)]
                signal_points = [SignalPricePoint(date=p.date, open=p.open, high=p.high, low=p.low, close=p.close, volume=p.volume) for p in fa_points]
                capability = AssetSourceManager.derive_signal_source_capability(fa_points)
                signals = await signal_service.compute(req.signals, signal_points, signal_context, annotation_requests=req.annotation_requests, source_capability=capability)
                visible_prices = [p for p in fa_points if visible_start <= p.date <= visible_end]
                results.append(FAPriceQueryResult(asset_id=req.asset_id, prices=visible_prices, events=[], errors=[], signals=signals))
            return results

        monkeypatch.setattr(AssetSourceManager, "get_prices_bulk", staticmethod(_flat_get_prices_bulk))
        scope = _asset_scope()
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("asset.states_events", required=True))

        assert payload["detected_event_count"] == 0
        assert payload["exported_event_count"] == 0
        assert payload["selection_summaries"] == []
        assert all(bucket["event_count"] == 0 for bucket in payload["buckets"])
        assert all(bucket["events"] == () or bucket["events"] == [] for bucket in payload["buckets"])


# =============================================================================
# 4b. Latest-per-category event selection (category taxonomy, requirements 1-3)
# =============================================================================


class TestLatestCategoryEvents:
    """Unit coverage for ``technical_context._latest_category_events``.

    White-box: the selector filters by annotation ``key`` (allowlist) and derives
    the category exclusively from the plugin registry via the ``signal_code``, so
    these tests pair real plugin codes (EMA/ADX/KAMA -> trend, RSI/MACD -> momentum,
    NATR/ATR -> volatility) with an explicit key allowlist.
    """

    _ALLOWED = frozenset({"k_a", "k_b", "k_c"})

    @staticmethod
    def _event(entity_id: str, key: str, signal_code: str, day: date, *, direction: str = "up", value: float = 1.0) -> DiscreteEvent:
        return DiscreteEvent(
            date=day,
            dedup_key=(entity_id, signal_code, key, day.isoformat()),
            payload={
                "entity_id": entity_id,
                "key": key,
                "annotation_type": "line_crossover",
                "signal_code": signal_code,
                "semantic_description": f"{signal_code} {key}.",
                "direction": direction,
                "values": {"difference": value},
            },
        )

    def test_empty_input_yields_no_latest_rows(self):
        assert technical_context._latest_category_events((), allowed_keys=self._ALLOWED) == ()

    def test_single_category_returns_one_latest_row(self):
        day = date(2026, 7, 1)
        events = (
            self._event("asset:1", "k_a", "EMA", day - timedelta(days=5)),
            self._event("asset:1", "k_b", "EMA", day),
        )
        rows = technical_context._latest_category_events(events, allowed_keys=self._ALLOWED)
        assert len(rows) == 1
        assert rows[0].signal_category == "trend"
        assert rows[0].date == day
        assert rows[0].key == "k_b"

    def test_multiple_categories_each_get_their_own_latest(self):
        day = date(2026, 7, 1)
        events = (
            self._event("asset:1", "k_a", "EMA", day - timedelta(days=1)),
            self._event("asset:1", "k_b", "RSI", day - timedelta(days=2)),
            self._event("asset:1", "k_c", "NATR", day - timedelta(days=3)),
        )
        rows = technical_context._latest_category_events(events, allowed_keys=self._ALLOWED)
        assert len(rows) == 3
        # Deterministic ordering by (entity_id, signal_category).
        assert [row.signal_category for row in rows] == ["momentum", "trend", "volatility"]

    def test_multiple_events_same_category_select_the_single_latest(self):
        day = date(2026, 7, 1)
        events = (
            self._event("asset:1", "k_a", "EMA", day - timedelta(days=10)),
            self._event("asset:1", "k_b", "ADX", day),
            self._event("asset:1", "k_a", "KAMA", day - timedelta(days=3)),
        )
        rows = technical_context._latest_category_events(events, allowed_keys=self._ALLOWED)
        assert len(rows) == 1
        assert rows[0].signal_category == "trend"
        assert rows[0].date == day
        assert rows[0].signal_code == "ADX"

    def test_tie_break_is_deterministic_by_date_then_key_then_signal(self):
        day = date(2026, 7, 1)
        events = (
            self._event("asset:1", "k_a", "EMA", day),
            self._event("asset:1", "k_b", "ADX", day),
            self._event("asset:1", "k_b", "EMA", day),
        )
        rows = technical_context._latest_category_events(events, allowed_keys=self._ALLOWED)
        assert len(rows) == 1
        # Same date, same category -> max (date, key, signal_code): k_b beats k_a, then EMA beats ADX.
        assert rows[0].key == "k_b"
        assert rows[0].signal_code == "EMA"

    def test_absent_categories_are_omitted_never_null(self):
        day = date(2026, 7, 1)
        events = (self._event("asset:1", "k_a", "EMA", day),)
        rows = technical_context._latest_category_events(events, allowed_keys=self._ALLOWED)
        assert {row.signal_category for row in rows} == {"trend"}
        assert all(row is not None for row in rows)

    def test_events_with_keys_outside_allowlist_are_excluded(self):
        day = date(2026, 7, 1)
        events = (self._event("asset:1", "not_allowed", "EMA", day),)
        assert technical_context._latest_category_events(events, allowed_keys=self._ALLOWED) == ()

    def test_selection_is_independent_per_entity(self):
        day = date(2026, 7, 1)
        events = (
            self._event("asset:1", "k_a", "EMA", day),
            self._event("asset:2", "k_a", "EMA", day - timedelta(days=5)),
        )
        rows = technical_context._latest_category_events(events, allowed_keys=self._ALLOWED)
        assert {(row.entity_id, row.signal_category) for row in rows} == {("asset:1", "trend"), ("asset:2", "trend")}

    def test_unknown_plugin_signal_code_fails_loudly(self):
        day = date(2026, 7, 1)
        events = (self._event("asset:1", "k_a", "NOT_A_REAL_PLUGIN", day),)
        with pytest.raises(ValueError):
            technical_context._latest_category_events(events, allowed_keys=self._ALLOWED)


# =============================================================================
# 5. Plugin-owned descriptions (requirement 1)
# =============================================================================


class TestPluginOwnedDescriptions:
    @pytest.mark.asyncio
    async def test_semantic_metadata_matches_plugin_describe_for_ai(self, monkeypatch):
        _patch_get_prices_bulk(monkeypatch)
        scope = _asset_scope()
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("asset.indicators", required=True))

        assert payload["indicators"]
        for entry in payload["indicators"]:
            plugin_class = SignalPluginRegistry.get_plugin(entry["signal_code"])
            assert plugin_class is not None
            ai_description = plugin_class.describe_for_ai()
            assert entry["category"] == ai_description.category.value
            assert entry["semantic_id"] == ai_description.semantic_id
            assert entry["semantic_description"] == ai_description.semantic_description
            for column in entry["columns"]:
                output_description = next(output for output in ai_description.outputs if output.key == column["output_key"])
                assert column["semantic_id"] == output_description.semantic_id
                assert column["semantic_description"] == output_description.semantic_description
                assert column["unit"] == output_description.unit.value
                output_spec = next(output for output in plugin_class.output_specs if output.key == column["output_key"])
                assert column["minimum"] == output_spec.axis.minimum
                assert column["maximum"] == output_spec.axis.maximum


# =============================================================================
# 6. Partial success / unavailable isolation (requirement 7)
# =============================================================================


class TestUnavailableIsolation:
    @pytest.mark.asyncio
    async def test_insufficient_warmup_omits_only_the_affected_signal(self, monkeypatch):
        """`ema_50`/`sma_50` (50-period) and `ema_200`/`sma_200` (200-period) each
        need far more warm-up than a deliberately-short 45-day load window
        (35 warm-up + 10 visible) provides; every other curated instance
        (<=34-period warm-up requirement) still succeeds - proving sibling
        plugins are not affected by one instance's unavailability, and that
        the omission is a real "insufficient history -> UNAVAILABLE" capability
        outcome, never curation."""

        async def _short_history_get_prices_bulk(requests, session):  # noqa: ARG001
            signal_service = SignalService()
            results = []
            for req in requests:
                visible_start = req.date_range.start
                visible_end = req.date_range.end or visible_start
                signal_context = SignalExecutionContext(domain=SignalDomain.ASSET, requested_range=req.date_range, cadence=SignalCadence.DAILY, source_reference=f"asset:{req.asset_id}")
                # Only 35 days of warm-up regardless of what the plan actually
                # needs (the 50/200-period instances need far more) - simulates
                # a young/newly-listed asset.
                load_start = visible_start - timedelta(days=35)
                fa_points = [_fa_price_point(req.asset_id, day) for day in _daterange(load_start, visible_end)]
                signal_points = [SignalPricePoint(date=p.date, open=p.open, high=p.high, low=p.low, close=p.close, volume=p.volume) for p in fa_points]
                capability = AssetSourceManager.derive_signal_source_capability(fa_points)
                signals = await signal_service.compute(req.signals, signal_points, signal_context, annotation_requests=req.annotation_requests, source_capability=capability)
                visible_prices = [p for p in fa_points if visible_start <= p.date <= visible_end]
                results.append(FAPriceQueryResult(asset_id=req.asset_id, prices=visible_prices, events=[], errors=[], signals=signals))
            return results

        monkeypatch.setattr(AssetSourceManager, "get_prices_bulk", staticmethod(_short_history_get_prices_bulk))
        scope = _asset_scope(period_start=date(2026, 1, 1), period_end=date(2026, 1, 10))
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("asset.indicators", required=True))

        instance_ids = {entry["instance_id"] for entry in payload["indicators"]}
        excluded = {"ema_50", "sma_50", "ema_200", "sma_200"}
        assert instance_ids.isdisjoint(excluded), "50/200-period instances should be omitted (insufficient warm-up), not a placeholder"
        # Every other curated instance needs far less warm-up and should still succeed.
        assert instance_ids == ASSET_BUNDLE_INSTANCE_IDS - excluded

        # No error/placeholder entries - just fewer indicators than the full bundle.
        for entry in payload["indicators"]:
            assert entry["instance_id"] not in excluded


# =============================================================================
# 7. Volume capability gating (requirement 2, 7, 9)
# =============================================================================


class TestVolumeCapabilityGating:
    @pytest.mark.asyncio
    async def test_authoritative_volume_source_includes_mfi_and_obv(self, monkeypatch):
        _patch_get_prices_bulk(monkeypatch, source_plugin_key="yfinance", with_volume=True)
        scope = _asset_scope()
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("asset.indicators", required=True))

        signal_codes = {entry["signal_code"] for entry in payload["indicators"]}
        assert "MFI" in signal_codes
        assert "OBV" in signal_codes
        assert "ATR" in signal_codes

    @pytest.mark.asyncio
    async def test_manual_unregistered_source_excludes_mfi_and_obv(self, monkeypatch):
        _patch_get_prices_bulk(monkeypatch, source_plugin_key="MANUAL", with_volume=True)
        scope = _asset_scope()
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("asset.indicators", required=True))

        signal_codes = {entry["signal_code"] for entry in payload["indicators"]}
        assert "MFI" not in signal_codes
        assert "OBV" not in signal_codes
        # ATR only needs high/low/close (structural), not meaningful volume -
        # still present even from an unregistered/manual source.
        assert "ATR" in signal_codes
        # Non-volume plugins remain fully unaffected.
        assert "RSI" in signal_codes
        assert "SMA" in signal_codes


# =============================================================================
# 8. FX no-volume (requirement 6, 9)
# =============================================================================


class TestFxNoVolume:
    @pytest.mark.asyncio
    async def test_fx_indicators_never_include_volume_or_high_low_only_plugins(self, monkeypatch):
        _patch_convert_bulk(monkeypatch)
        scope = _fx_scope()
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("fx.indicators", required=True))

        signal_codes = {entry["signal_code"] for entry in payload["indicators"]}
        assert "MFI" not in signal_codes
        assert "OBV" not in signal_codes
        assert "ATR" not in signal_codes
        # Close-only plugins remain available.
        assert "RSI" in signal_codes
        assert "SMA" in signal_codes
        assert "EMA" in signal_codes
        assert "MACD" in signal_codes
        assert "BOLLINGER" in signal_codes

    @pytest.mark.asyncio
    async def test_fx_event_selection_uses_canonical_pair_entity(self, monkeypatch):
        _patch_convert_bulk(monkeypatch)
        scope = _fx_scope()
        context = _make_context(scope)

        payload = _envelope_payload(await context.resolve("fx.states_events", required=True))

        assert payload["detected_event_count"] > 0
        assert payload["exported_event_count"] <= payload["detected_event_count"]
        assert {summary["entity_id"] for summary in payload["selection_summaries"]} == {"fx:USD/EUR"}
        assert all(event["entity_id"] == "fx:USD/EUR" for bucket in payload["buckets"] for event in bucket["events"])

    @pytest.mark.asyncio
    async def test_fx_returns_volatility_computed_from_rate_series(self, monkeypatch):
        _patch_convert_bulk(monkeypatch)
        scope = _fx_scope()
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("fx.returns_volatility", required=True))

        populated = [bucket for bucket in payload["buckets"] if bucket["observation_count"] >= 2]
        assert populated
        assert any(bucket["volatility"] is not None for bucket in populated)

    def test_fx_carry_forward_is_excluded_from_returns_and_volatility(self):
        start = date(2026, 1, 2)
        series = FxRateSeriesResource.from_observations(
            (
                FxRateObservation(
                    requested_date=start,
                    actual_date=start,
                    rate=Decimal("1"),
                    backward_filled=False,
                ),
                FxRateObservation(
                    requested_date=start + timedelta(days=1),
                    actual_date=start,
                    rate=Decimal("1"),
                    backward_filled=True,
                ),
                FxRateObservation(
                    requested_date=start + timedelta(days=2),
                    actual_date=start,
                    rate=Decimal("1"),
                    backward_filled=True,
                ),
                FxRateObservation(
                    requested_date=start + timedelta(days=3),
                    actual_date=start + timedelta(days=3),
                    rate=Decimal("1.1"),
                    backward_filled=False,
                ),
            )
        )
        plan = BucketPlan(
            start=start,
            end=start + timedelta(days=3),
            policy=BucketingPolicy(max_bucket_days=1),
            buckets=tuple(
                Bucket(
                    index=index,
                    start_date=start + timedelta(days=index),
                    end_date=start + timedelta(days=index),
                )
                for index in range(4)
            ),
        )

        rate_points = technical_shared.observations_to_rate_points(
            series,
            start=start,
            end=start + timedelta(days=3),
        )
        return_points = asset_fx_technical._daily_return_points(
            series,
            start=start,
            end=start + timedelta(days=3),
        )
        rate_buckets = technical_shared.build_price_buckets(
            rate_points,
            plan,
            key="rate",
        )
        return_buckets = asset_fx_technical._build_return_volatility_buckets(
            return_points,
            plan,
        )

        assert [point.date for point in rate_points] == [
            start,
            start + timedelta(days=3),
        ]
        assert len(return_points) == 1
        assert return_points[0].date == start + timedelta(days=3)
        assert return_points[0].values["return"] == Decimal("0.1")
        assert rate_buckets[1].observation_count == 0
        assert rate_buckets[2].observation_count == 0
        assert rate_buckets[3].return_start_date == start
        assert rate_buckets[3].simple_return == pytest.approx(0.1)
        assert sum(bucket.observation_count for bucket in return_buckets) == 1
        assert all(bucket.volatility is None for bucket in return_buckets)


# =============================================================================
# 9. Full portfolio/broker universe analysis + breadth reconciliation (requirement 5, 9)
# =============================================================================


class TestClassifyReferenceLevelState:
    """Direct unit tests for `classify_reference_level_state`'s degenerate
    (single-level) vs region (2+-level) semantics - no hardcoded thresholds,
    only the plugin's own declared level key/value (requirement: breadth bugfix).
    """

    _ZERO = SignalReferenceLevel(key="zero", label_key="signals.reference.zero", semantic="zero", value=0)
    _OVERSOLD = SignalReferenceLevel(key="oversold", label_key="signals.reference.oversold", semantic="oversold", value=30)
    _OVERBOUGHT = SignalReferenceLevel(key="overbought", label_key="signals.reference.overbought", semantic="overbought", value=70)

    def test_single_level_negative_value_is_below(self):
        assert technical_shared.classify_reference_level_state(-12.5, [self._ZERO]) == "below_zero"

    def test_single_level_zero_value_is_at(self):
        assert technical_shared.classify_reference_level_state(0.0, [self._ZERO]) == "at_zero"

    def test_single_level_positive_value_is_above(self):
        assert technical_shared.classify_reference_level_state(12.5, [self._ZERO]) == "above_zero"

    def test_single_level_tiny_float_noise_still_classified_at(self):
        # Residual float noise from Decimal->float conversion must not flip
        # an economically-zero value into below/above.
        assert technical_shared.classify_reference_level_state(1e-12, [self._ZERO]) == "at_zero"
        assert technical_shared.classify_reference_level_state(-1e-12, [self._ZERO]) == "at_zero"

    def test_single_level_never_returns_neutral(self):
        for value in (-100.0, -0.001, 0.0, 0.001, 100.0):
            state = technical_shared.classify_reference_level_state(value, [self._ZERO])
            assert state != "neutral"
            assert state in {"below_zero", "at_zero", "above_zero"}

    def test_two_levels_region_semantics_preserved(self):
        levels = [self._OVERSOLD, self._OVERBOUGHT]
        assert technical_shared.classify_reference_level_state(20.0, levels) == "oversold"
        assert technical_shared.classify_reference_level_state(50.0, levels) == "neutral"
        assert technical_shared.classify_reference_level_state(80.0, levels) == "overbought"
        # Boundary values belong to the matching declared level, not "neutral".
        assert technical_shared.classify_reference_level_state(30.0, levels) == "oversold"
        assert technical_shared.classify_reference_level_state(70.0, levels) == "overbought"

    def test_no_levels_returns_none(self):
        assert technical_shared.classify_reference_level_state(42.0, []) is None


class TestPortfolioUniverseAndBreadth:
    @pytest.mark.asyncio
    async def test_all_held_assets_analyzed_no_compact_truncation(self, monkeypatch):
        positions = [_contribution(asset_id) for asset_id in (1, 2, 3, 4, 5)]
        for detail_level in (DetailLevel.COMPACT, DetailLevel.STANDARD, DetailLevel.FULL):
            _patch_get_prices_bulk(monkeypatch)
            scope = _scope(detail_level=detail_level)
            report = _report(scope, positions)
            _patch_get_report(monkeypatch, report)
            context = _make_context(scope)
            payload = _envelope_payload(await context.resolve("portfolio.technical_prices", required=True))

            assert payload["eligible_asset_count"] == 5
            assert payload["period_position_leg_count"] == 5
            assert payload["period_contributor_asset_count"] == 5
            assert len(payload["assets"]) == 5
            asset_ids = [asset["asset_id"] for asset in payload["assets"]]
            assert asset_ids == sorted(asset_ids), "assets must be deterministically ordered by asset_id"

    @pytest.mark.asyncio
    async def test_same_asset_across_brokers_is_loaded_and_counted_once(self, monkeypatch):
        positions = [
            _contribution(1, end_value=600, broker_id=1),
            _contribution(1, end_value=300, broker_id=2),
            _contribution(2, end_value=100, broker_id=2),
        ]
        price_calls = _patch_get_prices_bulk(monkeypatch)
        scope = _scope()
        _patch_get_report(monkeypatch, _report(scope, positions))
        context = _make_context(scope)

        prices = _envelope_payload(await context.resolve("portfolio.technical_prices", required=True))
        indicators = _envelope_payload(await context.resolve("portfolio.technical_indicators", required=True))
        breadth = _envelope_payload(await context.resolve("portfolio.technical_breadth", required=True))
        events = _envelope_payload(await context.resolve("portfolio.technical_events", required=True))

        assert prices["price_basis"] == "observed_close"
        assert price_calls == [2]
        assert prices["period_position_leg_count"] == 3
        assert prices["period_contributor_asset_count"] == 2
        assert prices["eligible_asset_count"] == 2
        # Same asset at two brokers: legs (3) exceed both the unique contributor
        # count (2) and the eligible universe (2); the shared asset is deduped.
        assert prices["period_position_leg_count"] > prices["period_contributor_asset_count"]
        assert prices["period_contributor_asset_count"] == prices["eligible_asset_count"]
        assert [asset["asset_id"] for asset in prices["assets"]] == [1, 2]
        assert [asset["portfolio_weight_ratio"] for asset in prices["assets"]] == pytest.approx([0.9, 0.1])
        assert [asset["asset_id"] for asset in indicators["assets"]] == [1, 2]
        assert sum(asset["portfolio_weight_ratio"] for asset in indicators["assets"]) == pytest.approx(1.0)
        covered_indicator_assets = [asset for asset in indicators["assets"] if asset["indicators"]]
        assert indicators["covered_asset_count"] == len(covered_indicator_assets)
        normalized_by_instance: dict[str, list[float]] = {}
        for asset in indicators["assets"]:
            for indicator in asset["indicators"]:
                assert indicator["portfolio_weight_ratio"] == pytest.approx(asset["portfolio_weight_ratio"])
                normalized_by_instance.setdefault(indicator["instance_id"], []).append(indicator["technical_normalized_weight_ratio"])
        assert normalized_by_instance
        assert all(sum(weights) == pytest.approx(1.0) for weights in normalized_by_instance.values())
        assert indicators["eligible_portfolio_weight_ratio"] == pytest.approx(1.0)
        assert indicators["covered_portfolio_weight_ratio"] == pytest.approx(sum(asset["portfolio_weight_ratio"] for asset in covered_indicator_assets))
        assert indicators["covered_weight_ratio"] == pytest.approx(indicators["covered_portfolio_weight_ratio"] / indicators["eligible_portfolio_weight_ratio"])
        assert breadth["period_position_leg_count"] == 3
        assert breadth["period_contributor_asset_count"] == 2
        assert breadth["eligible_asset_count"] == 2
        assert breadth["covered_asset_count"] <= 2
        assert breadth["eligible_portfolio_weight_ratio"] == pytest.approx(1.0)
        assert breadth["covered_portfolio_weight_ratio"] <= breadth["eligible_portfolio_weight_ratio"]
        assert breadth["covered_weight_ratio"] == pytest.approx(breadth["covered_portfolio_weight_ratio"] / breadth["eligible_portfolio_weight_ratio"])

        flat_events = [event for bucket in events["buckets"] for event in bucket["events"]]
        identities = {
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
        assert len(flat_events) == len(identities)
        summary_keys = {(summary["entity_id"], summary["annotation_key"]) for summary in events["selection_summaries"]}
        assert len(summary_keys) == len(events["selection_summaries"])
        assert {entity_id for entity_id, _key in summary_keys} <= {
            "asset:1",
            "asset:2",
        }
        assert sum(summary["detected_count"] for summary in events["selection_summaries"]) == events["detected_event_count"]
        assert sum(summary["exported_count"] for summary in events["selection_summaries"]) == events["exported_event_count"]

    @pytest.mark.asyncio
    async def test_empty_portfolio_yields_valid_empty_technical_payload(self, monkeypatch):
        _patch_get_prices_bulk(monkeypatch)
        scope = _scope()
        report = _report(scope, [])
        _patch_get_report(monkeypatch, report)
        context = _make_context(scope)

        prices_payload = _envelope_payload(await context.resolve("portfolio.technical_prices", required=True))
        indicators_payload = _envelope_payload(await context.resolve("portfolio.technical_indicators", required=True))
        breadth_payload = _envelope_payload(await context.resolve("portfolio.technical_breadth", required=True))
        events_payload = _envelope_payload(await context.resolve("portfolio.technical_events", required=True))

        assert prices_payload["assets"] == []
        assert prices_payload["eligible_asset_count"] == 0
        assert indicators_payload["assets"] == []
        assert breadth_payload["eligible_asset_count"] == 0
        assert breadth_payload["covered_asset_count"] == 0
        assert breadth_payload["eligible_portfolio_weight_ratio"] == 0
        assert breadth_payload["covered_portfolio_weight_ratio"] == 0
        assert breadth_payload["covered_weight_ratio"] == 0
        assert breadth_payload["states"] == []
        assert events_payload["detected_event_count"] == 0
        assert events_payload["exported_event_count"] == 0

    @pytest.mark.asyncio
    async def test_fully_sold_positions_excluded_from_eligible_universe(self, monkeypatch):
        positions = [_contribution(1, end_value=1000), _contribution(2, end_value=0, is_fully_sold=True)]
        _patch_get_prices_bulk(monkeypatch)
        scope = _scope()
        report = _report(scope, positions)
        _patch_get_report(monkeypatch, report)
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("portfolio.technical_prices", required=True))

        assert payload["eligible_asset_count"] == 1
        # Fully-sold-in-period asset 2 still counts as a period leg and a period
        # contributor, but is excluded from the currently-held eligible universe.
        assert payload["period_position_leg_count"] == 2
        assert payload["period_contributor_asset_count"] == 2
        assert payload["covered_asset_count"] == 1
        assert [asset["asset_id"] for asset in payload["assets"]] == [1]

    @pytest.mark.asyncio
    async def test_breadth_ratios_reconcile_to_one_weighted_and_unweighted(self, monkeypatch):
        # Two assets with equal NAV weight (500/500): a perfectly balanced
        # unweighted/weighted breadth split is easy to verify exactly.
        positions = [_contribution(1, end_value=500), _contribution(2, end_value=500)]
        _patch_get_prices_bulk(monkeypatch)
        scope = _scope()
        report = _report(scope, positions)
        _patch_get_report(monkeypatch, report)
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("portfolio.technical_breadth", required=True))

        assert payload["eligible_asset_count"] == 2
        assert payload["states"], "expected at least one reference-level breadth bucket (RSI/MFI)"

        by_indicator: dict[tuple[str, str], list[dict]] = {}
        for state in payload["states"]:
            by_indicator.setdefault((state["signal_code"], state["output_key"]), []).append(state)
        for _key, states in by_indicator.items():
            unweighted_total = sum(s["unweighted_ratio"] for s in states)
            weighted_total = sum(s["technical_normalized_weight_ratio"] for s in states)
            assert unweighted_total == pytest.approx(1.0)
            assert weighted_total == pytest.approx(1.0)
            assert all(s["covered_asset_count"] > 0 for s in states)
            assert len({s["covered_asset_count"] for s in states}) == 1
            assert len({s["covered_portfolio_weight_ratio"] for s in states}) == 1

    @pytest.mark.asyncio
    async def test_weighted_breadth_differs_from_unweighted_with_unequal_weights(self, monkeypatch):
        # Asset 1 dominates NAV (9000 vs 1000): if the two assets land in
        # different reference-level states, weighted and unweighted ratios
        # must diverge (proves weighting is real, not a no-op).
        positions = [_contribution(1, end_value=9000), _contribution(2, end_value=1000)]

        async def _divergent_get_prices_bulk(requests, session):  # noqa: ARG001
            signal_service = SignalService()
            results = []
            for req in requests:
                visible_start = req.date_range.start
                visible_end = req.date_range.end or visible_start
                signal_context = SignalExecutionContext(domain=SignalDomain.ASSET, requested_range=req.date_range, cadence=SignalCadence.DAILY, source_reference=f"asset:{req.asset_id}")
                plan = signal_service.prepare_plan(req.signals, signal_context, req.annotation_requests)
                warmup_days = min(plan.max_history_points_before_visible, (visible_start - date.min).days)
                load_start = visible_start - timedelta(days=warmup_days)
                fa_points = []
                for day in _daterange(load_start, visible_end):
                    # Asset 1: strong monotonic uptrend (drives RSI toward
                    # overbought). Asset 2: strong monotonic downtrend (drives
                    # RSI toward oversold) - deterministically divergent states.
                    ordinal = (day - load_start).days
                    if req.asset_id == 1:
                        close = Decimal(str(100 + ordinal * 2))
                    else:
                        close = Decimal(str(max(1, 500 - ordinal * 2)))
                    fa_points.append(FAPricePoint(date=day, open=close, high=close, low=close, close=close, volume=Decimal(1000), currency=CURRENCY, source_plugin_key="yfinance", backward_fill_info=None))
                signal_points = [SignalPricePoint(date=p.date, open=p.open, high=p.high, low=p.low, close=p.close, volume=p.volume) for p in fa_points]
                capability = AssetSourceManager.derive_signal_source_capability(fa_points)
                signals = await signal_service.compute(req.signals, signal_points, signal_context, annotation_requests=req.annotation_requests, source_capability=capability)
                visible_prices = [p for p in fa_points if visible_start <= p.date <= visible_end]
                results.append(FAPriceQueryResult(asset_id=req.asset_id, prices=visible_prices, events=[], errors=[], signals=signals))
            return results

        monkeypatch.setattr(AssetSourceManager, "get_prices_bulk", staticmethod(_divergent_get_prices_bulk))
        scope = _scope(period_start=date(2026, 1, 1), period_end=date(2026, 1, 20))
        report = _report(scope, positions)
        _patch_get_report(monkeypatch, report)
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("portfolio.technical_breadth", required=True))

        rsi_states = [s for s in payload["states"] if s["signal_code"] == "RSI"]
        assert rsi_states
        distinct_states = {s["state"] for s in rsi_states}
        if len(distinct_states) > 1:
            # Divergent states -> weighted (90/10) must differ from unweighted (50/50).
            assert any(s["technical_normalized_weight_ratio"] != pytest.approx(s["unweighted_ratio"]) for s in rsi_states)

    @pytest.mark.asyncio
    async def test_degenerate_single_level_breadth_is_informative_not_neutral(self, monkeypatch):
        # ROC declares exactly one reference level ("zero"): with assets on
        # both sides of it, breadth must classify each into below_zero/
        # above_zero - never collapse everything into a single "zero"/
        # "neutral" bucket (the bug this test guards against).
        positions = [_contribution(1, end_value=9000), _contribution(2, end_value=1000)]

        async def _divergent_get_prices_bulk(requests, session):  # noqa: ARG001
            signal_service = SignalService()
            results = []
            for req in requests:
                visible_start = req.date_range.start
                visible_end = req.date_range.end or visible_start
                signal_context = SignalExecutionContext(domain=SignalDomain.ASSET, requested_range=req.date_range, cadence=SignalCadence.DAILY, source_reference=f"asset:{req.asset_id}")
                plan = signal_service.prepare_plan(req.signals, signal_context, req.annotation_requests)
                warmup_days = min(plan.max_history_points_before_visible, (visible_start - date.min).days)
                load_start = visible_start - timedelta(days=warmup_days)
                fa_points = []
                for day in _daterange(load_start, visible_end):
                    # Asset 1: exponential uptrend (ROC stably positive ->
                    # above_zero). Asset 2: exponential decay (ROC stably
                    # negative -> below_zero) - deterministically on opposite
                    # sides of the single "zero" reference level, regardless
                    # of how far back EMA200's stabilization warm-up (6x
                    # period = 1200 calendar days) reaches - a linear ramp
                    # would eventually floor/saturate over such a long window.
                    ordinal = (day - load_start).days
                    if req.asset_id == 1:
                        close = Decimal(str(100 * (1.001**ordinal)))
                    else:
                        close = Decimal(str(500 * (0.999**ordinal)))
                    fa_points.append(FAPricePoint(date=day, open=close, high=close, low=close, close=close, volume=Decimal(1000), currency=CURRENCY, source_plugin_key="yfinance", backward_fill_info=None))
                signal_points = [SignalPricePoint(date=p.date, open=p.open, high=p.high, low=p.low, close=p.close, volume=p.volume) for p in fa_points]
                capability = AssetSourceManager.derive_signal_source_capability(fa_points)
                signals = await signal_service.compute(req.signals, signal_points, signal_context, annotation_requests=req.annotation_requests, source_capability=capability)
                visible_prices = [p for p in fa_points if visible_start <= p.date <= visible_end]
                results.append(FAPriceQueryResult(asset_id=req.asset_id, prices=visible_prices, events=[], errors=[], signals=signals))
            return results

        monkeypatch.setattr(AssetSourceManager, "get_prices_bulk", staticmethod(_divergent_get_prices_bulk))
        scope = _scope(period_start=date(2026, 1, 1), period_end=date(2026, 1, 20))
        report = _report(scope, positions)
        _patch_get_report(monkeypatch, report)
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("portfolio.technical_breadth", required=True))

        roc_states = [s for s in payload["states"] if s["signal_code"] == "ROC"]
        assert roc_states, "ROC declares a single 'zero' reference level and must appear in breadth"
        distinct_state_keys = {s["state"] for s in roc_states}
        # The bug under test collapsed every value to "zero"; the fix must
        # surface both sides and never a "neutral"/single-bucket collapse.
        assert distinct_state_keys == {"below_zero", "above_zero"}
        assert "neutral" not in distinct_state_keys
        assert "zero" not in distinct_state_keys

        unweighted_total = sum(s["unweighted_ratio"] for s in roc_states)
        weighted_total = sum(s["technical_normalized_weight_ratio"] for s in roc_states)
        assert unweighted_total == pytest.approx(1.0)
        assert weighted_total == pytest.approx(1.0)
        # Unequal NAV weights (90/10) with divergent states -> weighted must
        # diverge from unweighted (50/50).
        assert any(s["technical_normalized_weight_ratio"] != pytest.approx(s["unweighted_ratio"]) for s in roc_states)

    @pytest.mark.asyncio
    async def test_broker_raw_prices_preserve_scope_universe_observations_currency_and_weights(self, monkeypatch):
        positions = [
            _contribution(2, end_value=300, broker_id=7),
            _contribution(1, end_value=900, broker_id=7),
            _contribution(3, end_value=0, is_fully_sold=True, broker_id=7),
        ]
        fake_get_prices_bulk, price_calls = _make_fake_get_prices_bulk()
        price_requests = []

        async def _capturing_get_prices_bulk(requests, session):
            price_requests.extend(requests)
            return await fake_get_prices_bulk(requests, session)

        monkeypatch.setattr(AssetSourceManager, "get_prices_bulk", staticmethod(_capturing_get_prices_bulk))
        scope = _broker_scope(broker_id=7, detail_level=DetailLevel.COMPACT, target_currency="EUR")
        report = _report(scope, positions)
        report_queries = []

        async def _capturing_get_report(self, user_id, query):  # noqa: ARG001
            report_queries.append(query)
            return report

        monkeypatch.setattr(PortfolioService, "get_report", _capturing_get_report)
        context = _make_context(scope)

        envelope = await context.resolve("broker.technical_prices", required=True)
        payload = _envelope_payload(envelope)

        assert envelope is not None
        assert envelope.component_id == "broker.technical_prices"
        assert len(report_queries) == 1
        assert report_queries[0].broker_ids == [7]
        assert report_queries[0].target_currency == "EUR"
        assert price_calls == [2]
        assert [request.asset_id for request in price_requests] == [1, 2]
        assert all(request.target_currency is None for request in price_requests)

        assert payload["eligible_asset_count"] == 2
        assert payload["period_position_leg_count"] == 3
        assert payload["period_contributor_asset_count"] == 3
        assert payload["covered_asset_count"] == 2
        assert [asset["asset_id"] for asset in payload["assets"]] == [1, 2]
        assert [asset["portfolio_weight_ratio"] for asset in payload["assets"]] == pytest.approx([0.75, 0.25])
        assert [asset["currency"] for asset in payload["assets"]] == [CURRENCY, CURRENCY]

        for asset in payload["assets"]:
            expected_close = float(_synthetic_close(asset["asset_id"], scope.period_end))
            assert asset["latest_close"] == pytest.approx(expected_close)
            assert asset["latest_date"] == scope.period_end.isoformat()
            assert asset["buckets"][-1]["last"]["close"] == pytest.approx(expected_close)


# =============================================================================
# 10. Resource memoization (requirement 5)
# =============================================================================


class TestResourceMemoization:
    @pytest.mark.asyncio
    async def test_single_report_and_price_load_shared_across_all_portfolio_technical_components(self, monkeypatch):
        positions = [_contribution(1), _contribution(2)]
        price_calls = _patch_get_prices_bulk(monkeypatch)
        scope = _scope()
        report = _report(scope, positions)
        report_calls = _patch_get_report(monkeypatch, report)
        context = _make_context(scope)

        for component_id in ("portfolio.technical_prices", "portfolio.technical_indicators", "portfolio.technical_breadth", "portfolio.technical_events"):
            await context.resolve(component_id, required=True)

        assert len(report_calls) == 1
        # One `get_prices_bulk` call, batching every held asset in one request.
        assert len(price_calls) == 1
        assert price_calls[0] == len(positions)

    @pytest.mark.asyncio
    async def test_single_asset_price_load_shared_across_asset_components(self, monkeypatch):
        price_calls = _patch_get_prices_bulk(monkeypatch)
        scope = _asset_scope()
        context = _make_context(scope)

        for component_id in ("asset.ohlc_returns", "asset.indicators", "asset.states_events"):
            await context.resolve(component_id, required=True)

        assert len(price_calls) == 1

    @pytest.mark.asyncio
    async def test_single_fx_rate_load_shared_across_fx_components(self, monkeypatch):
        rate_calls = _patch_convert_bulk(monkeypatch)
        scope = _fx_scope()
        context = _make_context(scope)

        for component_id in ("fx.rate_ohlc", "fx.returns_volatility", "fx.indicators", "fx.states_events"):
            await context.resolve(component_id, required=True)

        # `convert_bulk` is called exactly once (the shared rate series load) -
        # every one of the four FX technical components reuses it.
        assert len(rate_calls) == 1


# =============================================================================
# 11. Deterministic ordering / JSON-safety (requirement 8)
# =============================================================================


class TestDeterministicOutput:
    @pytest.mark.asyncio
    async def test_asset_ids_sorted_in_universe_payloads(self, monkeypatch):
        positions = [_contribution(3), _contribution(1), _contribution(2)]
        _patch_get_prices_bulk(monkeypatch)
        scope = _scope()
        report = _report(scope, positions)
        _patch_get_report(monkeypatch, report)
        context = _make_context(scope)

        payload = _envelope_payload(await context.resolve("portfolio.technical_indicators", required=True))
        assert [asset["asset_id"] for asset in payload["assets"]] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_repeated_build_is_deterministic(self, monkeypatch):
        positions = [_contribution(1), _contribution(2)]
        scope = _scope()
        report = _report(scope, positions)

        payloads = []
        for _ in range(2):
            _patch_get_prices_bulk(monkeypatch)
            _patch_get_report(monkeypatch, report)
            context = _make_context(scope)
            payloads.append(_envelope_payload(await context.resolve("portfolio.technical_indicators", required=True)))

        assert payloads[0] == payloads[1]


# =============================================================================
# 12. Technical context components: coverage aggregates, market context rows,
#     compact V3 mini-history, restricted events and build memoization
# =============================================================================


def _context_registry() -> ComponentRegistry:
    """Registry with full technical wave + context components for TestTechnicalContextComponents."""
    return ComponentRegistry(
        (
            *portfolio_broker_technical.PORTFOLIO_BROKER_TECHNICAL_COMPONENTS,
            *asset_fx_technical.ASSET_FX_TECHNICAL_COMPONENTS,
            *PORTFOLIO_TECHNICAL_CONTEXT_COMPONENTS,
            *BROKER_TECHNICAL_CONTEXT_COMPONENTS,
            *ASSET_TECHNICAL_CONTEXT_COMPONENTS,
            *FX_TECHNICAL_CONTEXT_COMPONENTS,
            ASSET_IDENTITY_STUB,
            FX_PAIR_IDENTITY_STUB,
        )
    )


def _context_make_context(scope: BuildScope, session: AsyncSession | None = None) -> BuildContext:
    """Like _make_context but with context components included in the registry."""
    bucket_plan = build_bucket_plan_for_scope(scope)
    return BuildContext(_context_registry(), request_id=scope.request_id, scope=scope, bucket_plan=bucket_plan, session=(session if session is not None else _make_async_session()))


def _context_price_resource(
    asset_ids: tuple[int, ...],
    *,
    start: date,
    end: date,
    sparse_asset_id: int | None = None,
) -> PriceResultsResource:
    results = []
    for asset_id in asset_ids:
        observed_dates = tuple(_daterange(start, end))
        if asset_id == sparse_asset_id:
            observed_dates = (start, end)
        results.append(
            FAPriceQueryResult(
                asset_id=asset_id,
                prices=[_fa_price_point(asset_id, day) for day in observed_dates],
                events=[],
                errors=[],
                signals=[],
            )
        )
    return PriceResultsResource.from_results(results)


def _context_universe_bundle(
    asset_ids: tuple[int, ...],
    *,
    start: date,
    end: date,
    sparse_asset_id: int | None = None,
) -> technical_shared.TechnicalUniverseBundle:
    weight = Decimal(1) / Decimal(len(asset_ids))
    return technical_shared.TechnicalUniverseBundle(
        positions=tuple(_contribution(asset_id) for asset_id in asset_ids),
        asset_ids=asset_ids,
        current_position_asset_ids=asset_ids,
        excluded_current_assets={},
        current_scope_weights=dict.fromkeys(asset_ids, weight),
        current_unvalued_asset_ids=(),
        period_position_leg_count=len(asset_ids),
        period_contributor_asset_count=len(asset_ids),
        weights=dict.fromkeys(asset_ids, weight),
        price_results=_context_price_resource(
            asset_ids,
            start=start,
            end=end,
            sparse_asset_id=sparse_asset_id,
        ),
    )


def _patch_context_universe_bundle(
    monkeypatch: pytest.MonkeyPatch,
    bundle: technical_shared.TechnicalUniverseBundle,
) -> None:
    async def _fake_load(context, **kwargs):  # noqa: ARG001
        return bundle

    monkeypatch.setattr(technical_context, "load_technical_universe_bundle", _fake_load)


def _patch_context_asset_prices(
    monkeypatch: pytest.MonkeyPatch,
    resource: PriceResultsResource,
) -> None:
    async def _fake_load(context):  # noqa: ARG001
        return resource

    monkeypatch.setattr(technical_context, "load_asset_price_results", _fake_load)


def _patch_context_fx_bundle(
    monkeypatch: pytest.MonkeyPatch,
    *,
    start: date,
    end: date,
) -> None:
    observations = tuple(
        FxRateObservation(
            requested_date=day,
            actual_date=day,
            rate=Decimal("1") + Decimal((day - start).days) / Decimal("100"),
            backward_filled=False,
        )
        for day in _daterange(start, end)
    )
    bundle = technical_shared.FxTechnicalBundle(
        rate_series=FxRateSeriesResource.from_observations(observations),
        signal_results=(),
    )

    async def _fake_load(context):  # noqa: ARG001
        return bundle

    monkeypatch.setattr(technical_context, "load_fx_technical_bundle", _fake_load)


class TestTechnicalContextComponents:
    """Focused tests for the technical_context component builders.

    Uses the same lightweight monkeypatching pattern as the other test
    classes in this file: synthetic deterministic prices via _patch_get_prices_bulk,
    synthetic portfolio report via _patch_get_report.
    """

    @pytest.mark.asyncio
    async def test_portfolio_coverage_aggregates_span_all_requested_signals(self, monkeypatch):
        """TechnicalUniverseCoveragePayload.signals has one entry per signal instance."""
        positions = [_contribution(1), _contribution(2)]
        scope = _scope()
        report = _report(scope, positions)
        _patch_get_prices_bulk(monkeypatch)
        _patch_get_report(monkeypatch, report)
        context = _context_make_context(scope)

        envelope = await context.resolve("portfolio.technical_coverage", required=True)
        assert envelope is not None
        payload = _envelope_payload(envelope)
        assert len(payload["signals"]) > 0
        instance_ids = [sig["instance_id"] for sig in payload["signals"]]
        assert len(instance_ids) == len(set(instance_ids))
        assert payload["covered_asset_count"] <= payload["eligible_asset_count"] <= payload["period_contributor_asset_count"] <= payload["period_position_leg_count"]

    @pytest.mark.asyncio
    async def test_portfolio_coverage_names_current_assets_excluded_from_technical_eligibility(self, monkeypatch):
        scope = _scope()
        base = _context_universe_bundle((1,), start=scope.period_start, end=scope.period_end)
        bundle = technical_shared.TechnicalUniverseBundle(
            positions=base.positions,
            asset_ids=base.asset_ids,
            current_position_asset_ids=(1, 2),
            excluded_current_assets={2: "end_value_unavailable"},
            current_scope_weights={1: Decimal("0.75"), 2: Decimal("0.25")},
            current_unvalued_asset_ids=(),
            period_position_leg_count=2,
            period_contributor_asset_count=2,
            weights=base.weights,
            price_results=base.price_results,
        )
        _patch_context_universe_bundle(monkeypatch, bundle)
        context = _context_make_context(scope)

        payload = _envelope_payload(await context.resolve("portfolio.technical_coverage", required=True))

        assert payload["current_position_asset_count"] == 2
        assert payload["current_scope_valued_asset_count"] == 2
        assert payload["current_scope_unvalued_asset_count"] == 0
        assert payload["eligible_asset_count"] == 1
        assert payload["eligible_current_scope_weight_ratio"] == pytest.approx(0.75)
        assert payload["covered_current_scope_weight_ratio"] == pytest.approx(0.0)
        assert payload["excluded_current_scope_weight_ratio"] == pytest.approx(0.25)
        assert payload["excluded_current_asset_count"] == 1
        assert payload["excluded_current_entities"] == [{"entity_id": "asset:2", "reason_code": "end_value_unavailable"}]

    @pytest.mark.asyncio
    async def test_asset_market_context_row_has_ema_and_rsi_fields(self, monkeypatch):
        """TechnicalMarketContextRow for an asset has ema_20, ema_50, rsi_14 populated."""
        scope = _asset_scope(asset_id=1)
        _patch_get_prices_bulk(monkeypatch)
        context = _context_make_context(scope)

        envelope = await context.resolve("asset.position_market_context", required=True)
        assert envelope is not None
        payload = _envelope_payload(envelope)
        entities = payload["entities"]
        assert len(entities) == 1
        row = entities[0]
        assert "asset:1" in row["entity_id"] or str(scope.asset_id) in row["entity_id"]
        assert row["ema_20"] is not None or row["rsi_14"] is not None

    @pytest.mark.asyncio
    async def test_asset_context_events_restricted_to_7_allowed_keys(self, monkeypatch):
        """asset.position_market_context events only contain keys from _ASSET_CONTEXT_EVENT_KEYS."""
        allowed_keys = technical_context._ASSET_CONTEXT_EVENT_KEYS
        assert len(allowed_keys) == 7

        scope = _asset_scope(asset_id=1)
        _patch_get_prices_bulk(monkeypatch)
        context = _context_make_context(scope)

        envelope = await context.resolve("asset.position_market_context", required=True)
        payload = _envelope_payload(envelope)
        for event in payload.get("events", []):
            assert event["key"] in allowed_keys, f"unexpected event key: {event['key']!r}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("detail_level", "expected_history"),
        [
            (DetailLevel.COMPACT, 8),
            (DetailLevel.STANDARD, 16),
            (DetailLevel.FULL, 30),
        ],
    )
    async def test_asset_position_context_history_density_by_detail_level(self, monkeypatch, detail_level, expected_history):
        """Single-Asset context emits exact 8/16/30 observed-only mini-history rows."""
        scope = _asset_scope(asset_id=1, detail_level=detail_level)
        _patch_context_asset_prices(
            monkeypatch,
            _context_price_resource(
                (1,),
                start=scope.period_start,
                end=scope.period_end,
            ),
        )
        context = _context_make_context(scope)

        envelope = await context.resolve("asset.position_market_context", required=True)
        payload = _envelope_payload(envelope)
        assert payload["policy_code"] == "asset_position_context_v2"
        assert len(payload["history"]) == expected_history
        assert {row["entity_id"] for row in payload["history"]} == {"asset:1"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("detail_level", "expected_history"),
        [
            (DetailLevel.COMPACT, 8),
            (DetailLevel.STANDARD, 16),
            (DetailLevel.FULL, 30),
        ],
    )
    async def test_fx_market_summary_history_density_by_detail_level(self, monkeypatch, detail_level, expected_history):
        """Single-FX context emits exact 8/16/30 observed-only mini-history rows."""
        scope = _fx_scope(detail_level=detail_level)
        _patch_context_fx_bundle(
            monkeypatch,
            start=scope.period_start,
            end=scope.period_end,
        )
        context = _context_make_context(scope)

        envelope = await context.resolve("fx.market_summary", required=True)
        payload = _envelope_payload(envelope)
        assert payload["policy_code"] == "fx_market_context_v2"
        assert len(payload["history"]) == expected_history
        assert {row["entity_id"] for row in payload["history"]} == {"fx:USD/EUR"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("detail_level", "expected_history"),
        [
            (DetailLevel.COMPACT, 6),
            (DetailLevel.STANDARD, 12),
            (DetailLevel.FULL, 24),
        ],
    )
    @pytest.mark.parametrize("domain", [Domain.PORTFOLIO, Domain.BROKER])
    async def test_portfolio_and_broker_market_context_keep_all_assets_at_requested_density(
        self,
        monkeypatch,
        domain,
        detail_level,
        expected_history,
    ):
        """Portfolio/Broker never sample entities; each dense Asset gets 6/12/24 rows."""
        scope = _scope(detail_level=detail_level) if domain is Domain.PORTFOLIO else _broker_scope(detail_level=detail_level)
        asset_ids = (1, 2, 3, 4, 5)
        _patch_context_universe_bundle(
            monkeypatch,
            _context_universe_bundle(
                asset_ids,
                start=scope.period_start,
                end=scope.period_end,
            ),
        )
        context = _context_make_context(scope)
        component_id = "portfolio.asset_market_context" if domain is Domain.PORTFOLIO else "broker.asset_market_context"

        payload = _envelope_payload(await context.resolve(component_id, required=True))
        history_counts = Counter(row["entity_id"] for row in payload["history"])

        assert payload["policy_code"] == ("portfolio_asset_snapshot_v2" if domain is Domain.PORTFOLIO else "broker_asset_comparison_v2")
        assert [row["entity_id"] for row in payload["entities"]] == [f"asset:{asset_id}" for asset_id in asset_ids]
        assert history_counts == Counter({f"asset:{asset_id}": expected_history for asset_id in asset_ids})

    @pytest.mark.asyncio
    async def test_portfolio_market_context_retains_sparse_asset_without_fabricating_rows(self, monkeypatch):
        """Sparse source shortens only that Asset's history; entity is still retained."""
        scope = _scope(detail_level=DetailLevel.COMPACT)
        asset_ids = (1, 2, 3, 4, 5)
        _patch_context_universe_bundle(
            monkeypatch,
            _context_universe_bundle(
                asset_ids,
                start=scope.period_start,
                end=scope.period_end,
                sparse_asset_id=5,
            ),
        )
        context = _context_make_context(scope)

        payload = _envelope_payload(await context.resolve("portfolio.asset_market_context", required=True))
        history_counts = Counter(row["entity_id"] for row in payload["history"])

        assert [row["entity_id"] for row in payload["entities"]] == [f"asset:{asset_id}" for asset_id in asset_ids]
        assert history_counts == Counter(
            {
                "asset:1": 6,
                "asset:2": 6,
                "asset:3": 6,
                "asset:4": 6,
                "asset:5": 2,
            }
        )

    def test_uniform_history_spans_observed_range_and_preserves_path_facts(self):
        """Rows cover uniform calendar spans and retain the simple observed path."""
        start = date(2026, 1, 1)
        values = (100.0, 120.0, 90.0, 110.0, 80.0, 125.0)
        points = tuple((start + timedelta(days=index), value) for index, value in enumerate(values))
        rows = technical_context._history_rows(
            entity_id="asset:1",
            points=points,
            bucket_count=3,
        )
        reversed_rows = technical_context._history_rows(
            entity_id="asset:1",
            points=tuple(reversed(points)),
            bucket_count=3,
        )

        assert len(rows) == 3
        assert reversed_rows == rows
        assert rows[0].bucket_start == start
        assert rows[-1].bucket_end == start + timedelta(days=5)
        assert all(current.bucket_start == previous.bucket_end + timedelta(days=1) for previous, current in zip(rows, rows[1:], strict=False))
        assert {row.bucket_end - row.bucket_start for row in rows} == {timedelta(days=1)}
        assert (rows[0].observed_date, rows[0].current_value) == (start, 100.0)
        assert (rows[-1].observed_date, rows[-1].current_value) == (start + timedelta(days=5), 125.0)
        assert rows[0].normalized_index_base_100 == pytest.approx(100.0)
        assert rows[0].return_from_first_ratio == pytest.approx(0.0)
        assert rows[1].normalized_index_base_100 == pytest.approx(110.0)
        assert rows[1].return_from_first_ratio == pytest.approx(0.1)
        assert rows[-1].normalized_index_base_100 == pytest.approx(125.0)
        assert rows[-1].return_from_first_ratio == pytest.approx(0.25)
        assert set(rows[0].model_dump()) == {
            "entity_id",
            "bucket_start",
            "bucket_end",
            "observation_count",
            "observed_date",
            "current_value",
            "normalized_index_base_100",
            "return_from_first_ratio",
        }

    def test_partial_observed_range_excludes_backfill_and_future_without_fill(self):
        """History anchors to actual observations, never requested/future/fill dates."""
        period_start = date(2026, 1, 2)
        period_end = date(2026, 1, 8)
        result = FAPriceQueryResult(
            asset_id=1,
            prices=[
                _fa_price_point(1, period_start - timedelta(days=1)).model_copy(update={"close": Decimal("80")}),
                _fa_price_point(1, period_start).model_copy(update={"close": Decimal("100")}),
                _fa_price_point(1, period_start + timedelta(days=1)).model_copy(
                    update={
                        "close": Decimal("101"),
                        "backward_fill_info": BackwardFillInfo(
                            actual_rate_date=period_start,
                            days_back=1,
                        ),
                    }
                ),
                _fa_price_point(1, period_start + timedelta(days=4)).model_copy(update={"close": Decimal("130")}),
                _fa_price_point(1, period_end + timedelta(days=1)).model_copy(update={"close": Decimal("140")}),
            ],
            events=[],
            errors=[],
            signals=[],
        )

        points = technical_context._observed_asset_points(
            result,
            start=period_start,
            end=period_end,
        )
        rows = technical_context._history_rows(
            entity_id="asset:1",
            points=points,
            bucket_count=8,
        )

        assert points == (
            (period_start, 100.0),
            (period_start + timedelta(days=4), 130.0),
        )
        assert len(rows) == 2
        assert sum(row.observation_count for row in rows) == 2
        assert rows[0].bucket_start == rows[0].bucket_end == period_start
        assert rows[-1].bucket_start == rows[-1].bucket_end == period_start + timedelta(days=4)
        assert [row.observed_date for row in rows] == [period_start, period_start + timedelta(days=4)]
        assert rows[-1].bucket_end < period_end
        assert rows[-1].normalized_index_base_100 == pytest.approx(130.0)
        assert rows[-1].return_from_first_ratio == pytest.approx(0.3)

    @pytest.mark.asyncio
    async def test_coverage_and_market_context_share_one_price_load(self, monkeypatch):
        """portfolio.technical_coverage and portfolio.asset_market_context reuse the same memoized price resource."""
        positions = [_contribution(1), _contribution(2)]
        scope = _scope()
        report = _report(scope, positions)
        price_calls = _patch_get_prices_bulk(monkeypatch)
        _patch_get_report(monkeypatch, report)
        context = _context_make_context(scope)

        await context.resolve("portfolio.technical_coverage", required=True)
        await context.resolve("portfolio.asset_market_context", required=True)

        assert len(price_calls) == 1

    @pytest.mark.asyncio
    async def test_asset_coverage_payload_is_json_serializable(self, monkeypatch):
        """TechnicalSingleEntityCoveragePayload round-trips through JSON cleanly."""
        scope = _asset_scope(asset_id=1)
        _patch_get_prices_bulk(monkeypatch)
        context = _context_make_context(scope)

        envelope = await context.resolve("asset.technical_coverage", required=True)
        payload = _envelope_payload(envelope)
        serialized = json.dumps(payload)
        assert json.loads(serialized) == payload

    @pytest.mark.asyncio
    async def test_fx_technical_coverage_payload_is_json_serializable(self, monkeypatch):
        """FX TechnicalSingleEntityCoveragePayload round-trips through JSON cleanly."""
        scope = _fx_scope()
        _patch_convert_bulk(monkeypatch)
        context = _context_make_context(scope)

        envelope = await context.resolve("fx.technical_coverage", required=True)
        payload = _envelope_payload(envelope)
        serialized = json.dumps(payload)
        assert json.loads(serialized) == payload

    @pytest.mark.asyncio
    async def test_market_context_rows_drop_flat_latest_event_fields(self, monkeypatch):
        """The four flat latest_event_* fields are gone from every market context row."""
        scope = _asset_scope(asset_id=1)
        _patch_get_prices_bulk(monkeypatch)
        context = _context_make_context(scope)
        payload = _envelope_payload(await context.resolve("asset.position_market_context", required=True))
        row = payload["entities"][0]
        for legacy in ("latest_event_date", "latest_event_key", "latest_event_signal", "latest_event_direction"):
            assert legacy not in row

    @pytest.mark.asyncio
    async def test_asset_position_latest_events_are_top_level_category_rows(self, monkeypatch):
        """asset.position_market_context exposes latest_events (max one per (entity, category))
        with plugin-owned categories, while the detailed events list keeps its own 12 limit."""
        _patch_get_prices_bulk(monkeypatch)
        scope = _asset_scope(asset_id=1, period_start=date(2025, 1, 1), period_end=date(2026, 6, 30), detail_level=DetailLevel.FULL)
        context = _context_make_context(scope)
        payload = _envelope_payload(await context.resolve("asset.position_market_context", required=True))

        latest = payload["latest_events"]
        assert latest, "expected at least one latest-per-category event for a rich synthetic history"
        groups = [(event["entity_id"], event["signal_category"]) for event in latest]
        assert len(groups) == len(set(groups)), "at most one latest event per (entity, category)"
        for event in latest:
            plugin = SignalPluginRegistry.get_plugin(event["signal_code"])
            assert plugin is not None
            assert event["signal_category"] == plugin.category.value
            assert event["key"] in technical_context._ASSET_CONTEXT_EVENT_KEYS
            assert set(event) >= {"entity_id", "signal_category", "signal_code", "key", "date", "direction", "semantic_description", "values"}
        # Separate detailed events limit is preserved.
        assert len(payload["events"]) <= 12

    @pytest.mark.asyncio
    async def test_portfolio_market_context_latest_events_span_all_eligible_events(self, monkeypatch):
        """Portfolio latest category rows are selected across all eligible context events,
        not from a max-one-per-entity truncation, and rows carry no legacy latest_event_* fields."""
        positions = [_contribution(1), _contribution(2)]
        scope = _scope(period_start=date(2025, 1, 1), period_end=date(2026, 6, 30), detail_level=DetailLevel.FULL)
        report = _report(scope, positions)
        _patch_get_prices_bulk(monkeypatch)
        _patch_get_report(monkeypatch, report)
        context = _context_make_context(scope)

        payload = _envelope_payload(await context.resolve("portfolio.asset_market_context", required=True))
        latest = payload["latest_events"]
        groups = [(event["entity_id"], event["signal_category"]) for event in latest]
        assert len(groups) == len(set(groups))
        for event in latest:
            assert event["signal_category"] == SignalPluginRegistry.get_plugin(event["signal_code"]).category.value
        for row in payload["entities"]:
            assert "latest_event_date" not in row

    @pytest.mark.asyncio
    async def test_fx_market_summary_latest_events_are_category_rows(self, monkeypatch):
        """FX market summary emits latest-per-category rows while keeping its 8 detailed events limit."""
        _patch_convert_bulk(monkeypatch)
        scope = _fx_scope(period_start=date(2025, 1, 1), period_end=date(2026, 6, 30), detail_level=DetailLevel.FULL)
        context = _context_make_context(scope)
        payload = _envelope_payload(await context.resolve("fx.market_summary", required=True))

        latest = payload["latest_events"]
        groups = [(event["entity_id"], event["signal_category"]) for event in latest]
        assert len(groups) == len(set(groups))
        for event in latest:
            assert event["signal_category"] == SignalPluginRegistry.get_plugin(event["signal_code"]).category.value
            assert event["key"] in technical_context._FX_CONTEXT_EVENT_KEYS
        assert len(payload["events"]) <= 8

    @pytest.mark.asyncio
    async def test_event_digest_rows_carry_plugin_owned_category(self, monkeypatch):
        """portfolio.event_digest rows carry a plugin-owned signal_category and reconcile underlying counts."""
        positions = [_contribution(1), _contribution(2)]
        scope = _scope(period_start=date(2025, 1, 1), period_end=date(2026, 6, 30), detail_level=DetailLevel.FULL)
        report = _report(scope, positions)
        _patch_get_prices_bulk(monkeypatch)
        _patch_get_report(monkeypatch, report)
        context = _context_make_context(scope)

        payload = _envelope_payload(await context.resolve("portfolio.event_digest", required=True))
        rows = payload["rows"]
        for row in rows:
            plugin = SignalPluginRegistry.get_plugin(row["signal_code"])
            assert plugin is not None
            assert row["signal_category"] == plugin.category.value
        # Underlying event count reconciles the digest's own included_event_count.
        assert sum(row["event_count"] for row in rows) == payload["included_event_count"]

    @pytest.mark.asyncio
    async def test_full_technical_events_component_shape_is_unchanged(self, monkeypatch):
        """The full technical events (states_events) payload keeps its detected/exported/bucket shape
        and never gains latest_events or per-event signal_category from the category taxonomy work."""
        _patch_get_prices_bulk(monkeypatch)
        scope = _asset_scope(period_start=date(2025, 1, 1), period_end=date(2026, 6, 30), detail_level=DetailLevel.FULL)
        context = _make_context(scope)
        payload = _envelope_payload(await context.resolve("asset.states_events", required=True))

        assert "latest_events" not in payload
        assert set(payload) >= {"detected_event_count", "exported_event_count", "buckets"}
        for bucket in payload["buckets"]:
            for event in bucket["events"]:
                assert "signal_category" not in event
