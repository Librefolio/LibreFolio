"""Focused contract tests for the immutable AI Export profile catalog."""

from __future__ import annotations

import inspect
import re
from collections import Counter
from dataclasses import FrozenInstanceError

import pytest

from backend.app.schemas.ai_export import AiExportBrokerTask, AiExportCatalogResponse, AiExportDetailLevel, AiExportDomain, AiExportPortfolioTask, AiExportTask
from backend.app.services.ai_export import models as ai_export_models
from backend.app.services.ai_export.models import (
    BandComponent,
    SignalEligibility,
    SignalOutputMode,
    TechnicalDepth,
    UnsupportedAiExportProfileError,
    build_resolved_profiles,
)
from backend.app.services.ai_export.profiles import (
    ASSET_BUNDLES,
    ASSET_COMPACT_BUNDLE,
    ASSET_FULL_BUNDLE,
    ASSET_STANDARD_BUNDLE,
    DETAIL_OVERLAYS,
    FX_BUNDLES,
    FX_COMPACT_BUNDLE,
    FX_FULL_BUNDLE,
    FX_STANDARD_BUNDLE,
    TASK_SPECS,
)
from backend.app.services.ai_export.resolver import ALL_PROFILES, SUPPORTED_PROFILE_IDS, resolve_profile, to_catalog_response
from backend.app.services.provider_registry import SignalPluginRegistry

EXPECTED_TASK_IDS = (
    "portfolio.pac_planning",
    "portfolio.rebalancing",
    "portfolio.performance_attribution",
    "portfolio.income_review",
    "portfolio.technical_breadth",
    "portfolio.portfolio_description",
    "asset.asset_snapshot",
    "asset.asset_trend_analysis",
    "asset.position_review",
    "asset.asset_pac_timing_context",
    "asset.drawdown_recovery",
    "fx.fx_trend_review",
    "fx.fx_exposure_impact",
    "fx.fx_conversion_timing_context",
    "broker.broker_review",
    "broker.broker_cost_efficiency",
    "broker.broker_concentration_context",
    "broker.broker_fifo_lot_review",
)

EXPECTED_METADATA = {
    "portfolio.pac_planning": ("largest_nav_and_smallest_non_zero_position", 12, "portfolio_accessible", True, True),
    "portfolio.rebalancing": ("largest_nav", 12, "portfolio_accessible", True, True),
    "portfolio.performance_attribution": ("period_pnl_positive_and_negative", 10, "selected_range_has_data", True, False),
    "portfolio.income_review": ("largest_period_income", 10, "portfolio_accessible", True, False),
    "portfolio.technical_breadth": ("recent_events_weighted_by_nav", 10, "portfolio_accessible_technical_optional", False, True),
    "portfolio.portfolio_description": ("largest_nav", 10, "portfolio_accessible", True, False),
    "asset.asset_snapshot": ("single_entity", 1, "asset_exists", True, True),
    "asset.asset_trend_analysis": ("single_entity", 1, "asset_exists_technical_optional", True, True),
    "asset.position_review": ("single_entity", 1, "positive_open_quantity_in_scope", True, False),
    "asset.asset_pac_timing_context": ("single_entity", 1, "asset_exists", True, True),
    "asset.drawdown_recovery": ("single_entity", 1, "two_observations_and_prior_maximum_available", True, True),
    "fx.fx_trend_review": ("single_entity", 1, "valid_iso_pair", True, True),
    "fx.fx_exposure_impact": ("single_entity", 1, "linked_cash_or_position_available", True, True),
    "fx.fx_conversion_timing_context": ("single_entity", 1, "valid_iso_pair", True, True),
    "broker.broker_review": ("largest_nav", 10, "broker_accessible_via_broker_user_access", True, False),
    "broker.broker_cost_efficiency": ("largest_absolute_period_fees_taxes", 10, "broker_accessible_via_broker_user_access", True, False),
    "broker.broker_concentration_context": ("largest_nav", 10, "broker_accessible_via_broker_user_access", True, False),
    "broker.broker_fifo_lot_review": ("largest_residual_cost_basis", 10, "broker_accessible_via_broker_user_access", True, False),
}

EXPECTED_ASSET_SIGNALS = {
    AiExportDetailLevel.COMPACT: (
        ("ema_20", "EMA", {"period": 20, "offset": 0.0}, ("ema",), SignalEligibility.ALWAYS),
        ("ema_50", "EMA", {"period": 50, "offset": 0.0}, ("ema",), SignalEligibility.ALWAYS),
        ("ema_200", "EMA", {"period": 200, "offset": 0.0}, ("ema",), SignalEligibility.ALWAYS),
        ("rsi_14", "RSI", {"period": 14, "overbought": 70, "oversold": 30}, ("rsi",), SignalEligibility.ALWAYS),
        ("macd_12_26_9", "MACD", {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}, ("macd", "signal", "histogram"), SignalEligibility.ALWAYS),
        ("bollinger_20_2", "BOLLINGER", {"period": 20, "multiplier": 2.0}, ("bands",), SignalEligibility.ALWAYS),
        ("natr_14", "NATR", {"period": 14}, ("natr",), SignalEligibility.ALWAYS),
        ("mfi_14", "MFI", {"period": 14, "overbought": 80, "oversold": 20}, ("mfi",), SignalEligibility.VOLUME_REQUIRED),
    ),
    AiExportDetailLevel.STANDARD: (
        ("ema_20", "EMA", {"period": 20, "offset": 0.0}, ("ema",), SignalEligibility.ALWAYS),
        ("ema_50", "EMA", {"period": 50, "offset": 0.0}, ("ema",), SignalEligibility.ALWAYS),
        ("ema_200", "EMA", {"period": 200, "offset": 0.0}, ("ema",), SignalEligibility.ALWAYS),
        ("adx_14", "ADX", {"period": 14}, ("adx", "plus_di", "minus_di"), SignalEligibility.ALWAYS),
        ("donchian_20", "DONCHIAN", {"period": 20}, ("channels",), SignalEligibility.ALWAYS),
        ("rsi_14", "RSI", {"period": 14, "overbought": 70, "oversold": 30}, ("rsi",), SignalEligibility.ALWAYS),
        ("macd_12_26_9", "MACD", {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}, ("macd", "signal", "histogram"), SignalEligibility.ALWAYS),
        ("stoch_rsi_14_3", "STOCH_RSI", {"period": 14, "dPeriod": 3, "overbought": 80, "oversold": 20}, ("k", "d"), SignalEligibility.ALWAYS),
        ("bollinger_20_2", "BOLLINGER", {"period": 20, "multiplier": 2.0}, ("bands",), SignalEligibility.ALWAYS),
        ("natr_14", "NATR", {"period": 14}, ("natr",), SignalEligibility.ALWAYS),
        ("mfi_14", "MFI", {"period": 14, "overbought": 80, "oversold": 20}, ("mfi",), SignalEligibility.VOLUME_REQUIRED),
        ("obv", "OBV", {}, ("obv",), SignalEligibility.VOLUME_REQUIRED),
    ),
    AiExportDetailLevel.FULL: (
        ("ema_20", "EMA", {"period": 20, "offset": 0.0}, ("ema",), SignalEligibility.ALWAYS),
        ("ema_50", "EMA", {"period": 50, "offset": 0.0}, ("ema",), SignalEligibility.ALWAYS),
        ("ema_200", "EMA", {"period": 200, "offset": 0.0}, ("ema",), SignalEligibility.ALWAYS),
        ("sma_50", "SMA", {"period": 50}, ("sma",), SignalEligibility.ALWAYS),
        ("sma_200", "SMA", {"period": 200}, ("sma",), SignalEligibility.ALWAYS),
        ("kama_20", "KAMA", {"period": 20}, ("kama",), SignalEligibility.ALWAYS),
        ("aroon_25", "AROON", {"period": 25}, ("up", "down", "oscillator"), SignalEligibility.ALWAYS),
        ("adx_14", "ADX", {"period": 14}, ("adx", "plus_di", "minus_di"), SignalEligibility.ALWAYS),
        ("donchian_20", "DONCHIAN", {"period": 20}, ("channels",), SignalEligibility.ALWAYS),
        ("rsi_14", "RSI", {"period": 14, "overbought": 70, "oversold": 30}, ("rsi",), SignalEligibility.ALWAYS),
        ("macd_12_26_9", "MACD", {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}, ("macd", "signal", "histogram"), SignalEligibility.ALWAYS),
        ("ppo_12_26_9", "PPO", {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}, ("ppo", "signal", "histogram"), SignalEligibility.ALWAYS),
        ("roc_20", "ROC", {"period": 20}, ("roc",), SignalEligibility.ALWAYS),
        ("stoch_rsi_14_3", "STOCH_RSI", {"period": 14, "dPeriod": 3, "overbought": 80, "oversold": 20}, ("k", "d"), SignalEligibility.ALWAYS),
        ("cci_20", "CCI", {"period": 20}, ("cci",), SignalEligibility.ALWAYS),
        ("bollinger_20_2", "BOLLINGER", {"period": 20, "multiplier": 2.0}, ("bands",), SignalEligibility.ALWAYS),
        ("atr_14", "ATR", {"period": 14}, ("atr",), SignalEligibility.ALWAYS),
        ("natr_14", "NATR", {"period": 14}, ("natr",), SignalEligibility.ALWAYS),
        ("mfi_14", "MFI", {"period": 14, "overbought": 80, "oversold": 20}, ("mfi",), SignalEligibility.VOLUME_REQUIRED),
        ("obv", "OBV", {}, ("obv",), SignalEligibility.VOLUME_REQUIRED),
    ),
}

EXPECTED_FX_SIGNALS = {
    AiExportDetailLevel.COMPACT: (
        ("ema_20", "EMA", {"period": 20, "offset": 0.0}, ("ema",)),
        ("ema_50", "EMA", {"period": 50, "offset": 0.0}, ("ema",)),
        ("ema_200", "EMA", {"period": 200, "offset": 0.0}, ("ema",)),
        ("rsi_14", "RSI", {"period": 14, "overbought": 70, "oversold": 30}, ("rsi",)),
        ("ppo_12_26_9", "PPO", {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}, ("ppo", "signal", "histogram")),
        ("bollinger_20_2", "BOLLINGER", {"period": 20, "multiplier": 2.0}, ("bands",)),
    ),
    AiExportDetailLevel.STANDARD: (
        ("ema_20", "EMA", {"period": 20, "offset": 0.0}, ("ema",)),
        ("ema_50", "EMA", {"period": 50, "offset": 0.0}, ("ema",)),
        ("ema_200", "EMA", {"period": 200, "offset": 0.0}, ("ema",)),
        ("rsi_14", "RSI", {"period": 14, "overbought": 70, "oversold": 30}, ("rsi",)),
        ("ppo_12_26_9", "PPO", {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}, ("ppo", "signal", "histogram")),
        ("bollinger_20_2", "BOLLINGER", {"period": 20, "multiplier": 2.0}, ("bands",)),
        ("roc_20", "ROC", {"period": 20}, ("roc",)),
        ("stoch_rsi_14_3", "STOCH_RSI", {"period": 14, "dPeriod": 3, "overbought": 80, "oversold": 20}, ("k", "d")),
        ("kama_20", "KAMA", {"period": 20}, ("kama",)),
    ),
    AiExportDetailLevel.FULL: (
        ("ema_20", "EMA", {"period": 20, "offset": 0.0}, ("ema",)),
        ("ema_50", "EMA", {"period": 50, "offset": 0.0}, ("ema",)),
        ("ema_200", "EMA", {"period": 200, "offset": 0.0}, ("ema",)),
        ("sma_50", "SMA", {"period": 50}, ("sma",)),
        ("sma_200", "SMA", {"period": 200}, ("sma",)),
        ("kama_20", "KAMA", {"period": 20}, ("kama",)),
        ("rsi_14", "RSI", {"period": 14, "overbought": 70, "oversold": 30}, ("rsi",)),
        ("macd_12_26_9", "MACD", {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}, ("macd", "signal", "histogram")),
        ("ppo_12_26_9", "PPO", {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9}, ("ppo", "signal", "histogram")),
        ("roc_20", "ROC", {"period": 20}, ("roc",)),
        ("stoch_rsi_14_3", "STOCH_RSI", {"period": 14, "dPeriod": 3, "overbought": 80, "oversold": 20}, ("k", "d")),
        ("bollinger_20_2", "BOLLINGER", {"period": 20, "multiplier": 2.0}, ("bands",)),
    ),
}


def _task_id(spec) -> str:
    return f"{spec.domain.value}.{spec.task.value}"


def _signal_signature(signal_spec):
    return (
        signal_spec.instance_id,
        signal_spec.signal_code,
        dict(signal_spec.params),
        signal_spec.requested_components,
        signal_spec.eligibility,
    )


def test_catalog_has_exact_frozen_counts_and_domain_distribution():
    assert len(TASK_SPECS) == 18
    assert len(DETAIL_OVERLAYS) == 3
    assert len(ALL_PROFILES) == 54
    assert Counter(profile.domain for profile in ALL_PROFILES) == {
        AiExportDomain.PORTFOLIO: 18,
        AiExportDomain.ASSET: 15,
        AiExportDomain.FX: 9,
        AiExportDomain.BROKER: 12,
    }


def test_catalog_order_and_ids_are_deterministic():
    expected_ids = tuple(f"{task_id}.{detail.value}" for task_id in EXPECTED_TASK_IDS for detail in AiExportDetailLevel)
    assert tuple(_task_id(spec) for spec in TASK_SPECS) == EXPECTED_TASK_IDS
    assert SUPPORTED_PROFILE_IDS == expected_ids
    assert tuple(profile.profile_id for profile in ALL_PROFILES) == expected_ids
    assert all(profile.profile_version == 1 and profile.schema_version == 1 for profile in ALL_PROFILES)


def test_every_task_detail_resolves_exactly():
    for task_spec in TASK_SPECS:
        for detail_level in AiExportDetailLevel:
            profile = resolve_profile(task_spec.domain, task_spec.task, detail_level)
            assert profile.task_spec is task_spec
            assert profile.detail_level == detail_level
            assert profile.profile_id == f"{task_spec.domain.value}.{task_spec.task.value}.{detail_level.value}"
            assert profile.frontend_response_contract_id == f"{task_spec.domain.value}.{task_spec.task.value}"
            assert profile.frontend_response_contract_version == 1


def test_unsupported_lookup_raises_typed_error_with_request_and_supported_ids():
    with pytest.raises(UnsupportedAiExportProfileError) as caught:
        resolve_profile("asset", "not_a_task", "compact")
    assert caught.value.request.domain == "asset"
    assert caught.value.request.task == "not_a_task"
    assert caught.value.request.detail_level == "compact"
    assert caught.value.supported_profile_ids == SUPPORTED_PROFILE_IDS


def test_internal_catalog_objects_are_deeply_immutable():
    profile = ALL_PROFILES[0]
    signal_spec = ASSET_COMPACT_BUNDLE.signals[0]
    with pytest.raises(FrozenInstanceError):
        profile.profile_id = "changed"
    with pytest.raises(TypeError):
        signal_spec.params["period"] = 99
    with pytest.raises(TypeError):
        profile.task_spec.technical_by_detail[AiExportDetailLevel.COMPACT] = profile.technical


def test_all_bundles_have_unique_instances_and_canonical_signal_codes():
    for bundle in (*ASSET_BUNDLES, *FX_BUNDLES):
        instance_ids = [item.instance_id for item in bundle.signals]
        assert len(instance_ids) == len(set(instance_ids))
        assert all(item.signal_code == item.signal_code.upper() for item in bundle.signals)
        assert all(re.fullmatch(r"[A-Z][A-Z0-9_]*", item.signal_code) for item in bundle.signals)


@pytest.mark.parametrize(
    ("bundle", "detail_level", "expected_mode"),
    (
        (ASSET_COMPACT_BUNDLE, AiExportDetailLevel.COMPACT, SignalOutputMode.LATEST),
        (ASSET_STANDARD_BUNDLE, AiExportDetailLevel.STANDARD, SignalOutputMode.SAMPLED),
        (ASSET_FULL_BUNDLE, AiExportDetailLevel.FULL, SignalOutputMode.FULL_WINDOW),
    ),
)
def test_asset_bundle_contents_params_components_and_modes(bundle, detail_level, expected_mode):
    assert tuple(_signal_signature(item) for item in bundle.signals) == EXPECTED_ASSET_SIGNALS[detail_level]
    for item in bundle.signals:
        if detail_level == AiExportDetailLevel.STANDARD and item.instance_id == "obv":
            assert item.mode == SignalOutputMode.STATE_EVENT_ONLY
        else:
            assert item.mode == expected_mode


@pytest.mark.parametrize(
    ("bundle", "detail_level", "expected_mode"),
    (
        (FX_COMPACT_BUNDLE, AiExportDetailLevel.COMPACT, SignalOutputMode.LATEST),
        (FX_STANDARD_BUNDLE, AiExportDetailLevel.STANDARD, SignalOutputMode.SAMPLED),
        (FX_FULL_BUNDLE, AiExportDetailLevel.FULL, SignalOutputMode.FULL_WINDOW),
    ),
)
def test_fx_bundle_contents_params_components_and_modes(bundle, detail_level, expected_mode):
    signatures = tuple((item.instance_id, item.signal_code, dict(item.params), item.requested_components) for item in bundle.signals)
    assert signatures == EXPECTED_FX_SIGNALS[detail_level]
    assert all(item.mode == expected_mode for item in bundle.signals)
    assert all(item.eligibility == SignalEligibility.ALWAYS for item in bundle.signals)


def test_band_annotation_sources_encode_lower_middle_upper_without_signal_schema_dependency():
    asset_band_sources = {source.band_component for annotation in ASSET_STANDARD_BUNDLE.annotations for source in (annotation.left, annotation.right, annotation.source) if source is not None and source.band_component is not None}
    fx_band_sources = {source.band_component for annotation in FX_FULL_BUNDLE.annotations for source in (annotation.left, annotation.right, annotation.source) if source is not None and source.band_component is not None}
    assert asset_band_sources == set(BandComponent)
    assert fx_band_sources == set(BandComponent)

    assert "backend.app.schemas.signals" not in inspect.getsource(ai_export_models)


def test_compact_selectors_and_task_metadata_match_contract():
    for task_spec in TASK_SPECS:
        expected_rule, expected_limit, expected_applicability, expected_notes, expected_web = EXPECTED_METADATA[_task_id(task_spec)]
        assert task_spec.compact_selection.rule == expected_rule
        assert task_spec.compact_selection.entity_limit == expected_limit
        assert task_spec.applicability_code == expected_applicability
        assert task_spec.supports_user_notes is expected_notes
        assert task_spec.supports_web_research is expected_web
        assert task_spec.frontend_response_contract_id == _task_id(task_spec)
        assert task_spec.frontend_response_contract_version == 1

    pac = resolve_profile(AiExportDomain.PORTFOLIO, AiExportTask.PAC_PLANNING, AiExportDetailLevel.COMPACT).compact_selection
    attribution = resolve_profile(AiExportDomain.PORTFOLIO, AiExportTask.PERFORMANCE_ATTRIBUTION, AiExportDetailLevel.COMPACT).compact_selection
    breadth = resolve_profile(AiExportDomain.PORTFOLIO, AiExportTask.TECHNICAL_BREADTH, AiExportDetailLevel.COMPACT)
    assert dict(pac.parameters) == {"metric": "nav", "largest_count": 6, "smallest_count": 6, "non_zero_only": True, "deduplicate_union": True}
    assert dict(attribution.parameters) == {"metric": "period_pnl_amount", "positive_count": 5, "negative_count": 5, "deduplicate_union": True}
    assert breadth.technical.event_limit_override == 10
    assert breadth.compact_selection.parameters["aggregate_scope"] == "all_eligible_entities"


def test_asset_and_fx_compact_tasks_use_explicit_single_entity_limit_one():
    for task_spec in TASK_SPECS:
        if task_spec.domain in (AiExportDomain.ASSET, AiExportDomain.FX):
            assert task_spec.compact_selection.rule == "single_entity"
            assert task_spec.compact_selection.entity_limit == 1


def test_portfolio_and_broker_technical_profiles_reference_asset_bundle_by_detail():
    no_technical_compact = {
        AiExportTask.PERFORMANCE_ATTRIBUTION,
        AiExportTask.INCOME_REVIEW,
        AiExportTask.PORTFOLIO_DESCRIPTION,
        AiExportTask.BROKER_COST_EFFICIENCY,
        AiExportTask.BROKER_FIFO_LOT_REVIEW,
    }
    asset_bundle_by_detail = {
        AiExportDetailLevel.COMPACT: ASSET_COMPACT_BUNDLE,
        AiExportDetailLevel.STANDARD: ASSET_STANDARD_BUNDLE,
        AiExportDetailLevel.FULL: ASSET_FULL_BUNDLE,
    }
    for profile in ALL_PROFILES:
        if profile.domain not in (AiExportDomain.PORTFOLIO, AiExportDomain.BROKER):
            continue
        if profile.detail_level == AiExportDetailLevel.COMPACT and profile.task in no_technical_compact:
            assert profile.technical_depth == TechnicalDepth.NONE
            assert profile.technical_bundle is None
        else:
            assert profile.technical_bundle is asset_bundle_by_detail[profile.detail_level]

    assert resolve_profile("portfolio", "pac_planning", "compact").technical_depth == TechnicalDepth.LATEST_BREADTH
    assert resolve_profile("portfolio", "performance_attribution", "standard").technical_depth == TechnicalDepth.LATEST_STATES
    assert resolve_profile("portfolio", "performance_attribution", "full").technical_depth == TechnicalDepth.SAMPLED_STANDARD
    assert resolve_profile("broker", "broker_review", "compact").technical_depth == TechnicalDepth.BREADTH_ONLY


def test_detail_overlays_encode_sampling_and_cardinality_without_hidden_top_n():
    compact, standard, full = DETAIL_OVERLAYS
    assert compact.detail_level == AiExportDetailLevel.COMPACT
    assert compact.sampling.include_latest is True
    assert compact.sampling.include_aggregates is True
    assert compact.sampling.include_series is False
    assert compact.sampling.recent_daily_points == 0
    assert compact.sampling.preceding_weekly_points == 0
    assert compact.cardinality.requires_compact_selection is True
    assert compact.cardinality.complete_aggregates is True

    assert standard.detail_level == AiExportDetailLevel.STANDARD
    assert standard.sampling.recent_daily_points == 7
    assert standard.sampling.preceding_weekly_points == 8
    assert standard.sampling.weekly_across_technical_window is False
    assert standard.cardinality.all_positions is True
    assert standard.cardinality.all_entities is True
    assert standard.cardinality.all_contributions is True
    assert standard.cardinality.requires_compact_selection is False

    assert full.detail_level == AiExportDetailLevel.FULL
    assert full.sampling.recent_daily_points == 7
    assert full.sampling.preceding_weekly_points is None
    assert full.sampling.weekly_across_technical_window is True
    assert compact.event_limits.max_events == 10
    assert standard.event_limits.max_events == 40
    assert full.event_limits.max_events == 120
    assert full.cardinality.all_positions is True
    assert full.cardinality.all_entities is True
    assert full.cardinality.all_contributions is True
    assert full.cardinality.requires_compact_selection is False


def test_required_optional_sections_are_explicit_unique_and_disjoint():
    for task_spec in TASK_SPECS:
        assert task_spec.required_sections
        assert len(task_spec.required_sections) == len(set(task_spec.required_sections))
        assert len(task_spec.optional_sections) == len(set(task_spec.optional_sections))
        assert set(task_spec.required_sections).isdisjoint(task_spec.optional_sections)


@pytest.mark.parametrize("detail", AiExportDetailLevel)
@pytest.mark.parametrize("task", AiExportPortfolioTask)
def test_portfolio_contribution_sections_are_profile_gated_for_every_task_and_detail(task, detail):
    profile = resolve_profile(AiExportDomain.PORTFOLIO, task, detail)
    contribution_sections = {
        "facts.contributions",
        "facts.unallocated_contributions",
        "facts.other_period_effects",
    }

    if task in {
        AiExportPortfolioTask.PAC_PLANNING,
        AiExportPortfolioTask.PERFORMANCE_ATTRIBUTION,
        AiExportPortfolioTask.INCOME_REVIEW,
    }:
        assert contribution_sections <= set(profile.required_sections)
        assert contribution_sections.isdisjoint(profile.optional_sections)
    elif task in {
        AiExportPortfolioTask.REBALANCING,
        AiExportPortfolioTask.PORTFOLIO_DESCRIPTION,
    }:
        assert contribution_sections <= set(profile.optional_sections)
        assert contribution_sections.isdisjoint(profile.required_sections)
    else:
        assert task == AiExportPortfolioTask.TECHNICAL_BREADTH
        assert contribution_sections.isdisjoint(profile.required_sections)
        assert contribution_sections.isdisjoint(profile.optional_sections)


@pytest.mark.parametrize("detail", AiExportDetailLevel)
@pytest.mark.parametrize("task", AiExportBrokerTask)
def test_broker_contribution_sections_are_profile_gated_for_every_task_and_detail(task, detail):
    profile = resolve_profile(AiExportDomain.BROKER, task, detail)
    contribution_sections = {
        "facts.contributions",
        "facts.unallocated_contributions",
        "facts.other_period_effects",
    }

    if task == AiExportBrokerTask.BROKER_COST_EFFICIENCY:
        assert contribution_sections <= set(profile.required_sections)
        assert contribution_sections.isdisjoint(profile.optional_sections)
    elif task == AiExportBrokerTask.BROKER_REVIEW:
        assert contribution_sections <= set(profile.optional_sections)
        assert contribution_sections.isdisjoint(profile.required_sections)
    else:
        assert contribution_sections.isdisjoint(profile.required_sections)
        assert contribution_sections.isdisjoint(profile.optional_sections)


def test_catalog_conversion_validates_through_schema_and_exposes_no_prompt_or_label_fields():
    response = to_catalog_response()
    validated = AiExportCatalogResponse.model_validate(response.model_dump(mode="json"))
    assert validated.schema_version == 1
    assert len(validated.entries) == 54
    assert [entry.profile_id for entry in validated.entries] == list(SUPPORTED_PROFILE_IDS)
    expected_entry_keys = {
        "domain",
        "task",
        "detail_level",
        "profile_id",
        "profile_version",
        "frontend_response_contract_id",
        "frontend_response_contract_version",
        "applicability_code",
        "supports_user_notes",
        "supports_web_research",
    }
    for entry in validated.entries:
        keys = set(entry.model_dump())
        assert keys == expected_entry_keys
        assert all("prompt" not in key and "label" not in key for key in keys)


def test_catalog_factory_is_isolated_from_signal_registry_and_discovery(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("AI Export profile construction must not access SignalPluginRegistry")

    monkeypatch.setattr(SignalPluginRegistry, "_plugins", {**SignalPluginRegistry._plugins, "UNRELATED_TEST_SIGNAL": object()})
    monkeypatch.setattr(SignalPluginRegistry, "auto_discover", classmethod(fail_if_called))
    monkeypatch.setattr(SignalPluginRegistry, "list_definitions", classmethod(fail_if_called))
    monkeypatch.setattr(SignalPluginRegistry, "_get_plugin_directory", classmethod(fail_if_called))

    rebuilt = build_resolved_profiles(TASK_SPECS, DETAIL_OVERLAYS)
    assert tuple(profile.profile_id for profile in rebuilt) == SUPPORTED_PROFILE_IDS
    assert to_catalog_response(rebuilt).model_dump(mode="json") == to_catalog_response().model_dump(mode="json")
