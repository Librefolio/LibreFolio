"""Static FX technical bundles and task manifests."""

from __future__ import annotations

from backend.app.schemas.ai_export import AiExportDetailLevel, AiExportDomain, AiExportTask
from backend.app.services.ai_export.models import BandComponent, SignalOutputMode, TaskSpec, TechnicalBundleSpec, TechnicalDepth
from backend.app.services.ai_export.profiles.base import (
    compact_selection,
    line_crossover,
    price_source,
    signal,
    signal_source,
    technical_detail,
    technical_matrix,
    threshold_crossing,
)


def _ema(period: int, mode: SignalOutputMode):
    return signal(
        f"ema_{period}",
        "EMA",
        {"period": period, "offset": 0.0},
        ("ema",),
        mode,
    )


def _sma(period: int, mode: SignalOutputMode):
    return signal(
        f"sma_{period}",
        "SMA",
        {"period": period},
        ("sma",),
        mode,
    )


def _fx_annotations(*, include_standard: bool):
    annotations = [
        line_crossover(
            "rate_ema_20",
            "ema_20",
            price_source(),
            signal_source("ema_20", "ema"),
        ),
        line_crossover(
            "ema_20_ema_50",
            "ema_20",
            signal_source("ema_20", "ema"),
            signal_source("ema_50", "ema"),
        ),
        line_crossover(
            "ema_50_ema_200",
            "ema_50",
            signal_source("ema_50", "ema"),
            signal_source("ema_200", "ema"),
        ),
        threshold_crossing(
            "rsi_14_oversold_30",
            "rsi_14",
            signal_source("rsi_14", "rsi"),
            30,
        ),
        threshold_crossing(
            "rsi_14_overbought_70",
            "rsi_14",
            signal_source("rsi_14", "rsi"),
            70,
        ),
        line_crossover(
            "ppo_signal",
            "ppo_12_26_9",
            signal_source("ppo_12_26_9", "ppo"),
            signal_source("ppo_12_26_9", "signal"),
        ),
        threshold_crossing(
            "ppo_histogram_zero",
            "ppo_12_26_9",
            signal_source("ppo_12_26_9", "histogram"),
            0,
        ),
        line_crossover(
            "rate_bollinger_lower",
            "bollinger_20_2",
            price_source(),
            signal_source(
                "bollinger_20_2",
                "bands",
                band_component=BandComponent.LOWER,
            ),
        ),
        line_crossover(
            "rate_bollinger_middle",
            "bollinger_20_2",
            price_source(),
            signal_source(
                "bollinger_20_2",
                "bands",
                band_component=BandComponent.MIDDLE,
            ),
        ),
        line_crossover(
            "rate_bollinger_upper",
            "bollinger_20_2",
            price_source(),
            signal_source(
                "bollinger_20_2",
                "bands",
                band_component=BandComponent.UPPER,
            ),
        ),
    ]
    if include_standard:
        annotations.extend(
            [
                threshold_crossing(
                    "roc_20_zero",
                    "roc_20",
                    signal_source("roc_20", "roc"),
                    0,
                ),
                line_crossover(
                    "stoch_rsi_k_d",
                    "stoch_rsi_14_3",
                    signal_source("stoch_rsi_14_3", "k"),
                    signal_source("stoch_rsi_14_3", "d"),
                ),
                threshold_crossing(
                    "stoch_rsi_k_oversold_20",
                    "stoch_rsi_14_3",
                    signal_source("stoch_rsi_14_3", "k"),
                    20,
                ),
                threshold_crossing(
                    "stoch_rsi_k_overbought_80",
                    "stoch_rsi_14_3",
                    signal_source("stoch_rsi_14_3", "k"),
                    80,
                ),
            ]
        )
    return tuple(annotations)


FX_COMPACT_BUNDLE = TechnicalBundleSpec(
    bundle_id="fx.compact",
    detail_level=AiExportDetailLevel.COMPACT,
    target_domain=AiExportDomain.FX,
    signals=(
        _ema(20, SignalOutputMode.LATEST),
        _ema(50, SignalOutputMode.LATEST),
        _ema(200, SignalOutputMode.LATEST),
        signal(
            "rsi_14",
            "RSI",
            {"period": 14, "overbought": 70, "oversold": 30},
            ("rsi",),
            SignalOutputMode.LATEST,
        ),
        signal(
            "ppo_12_26_9",
            "PPO",
            {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9},
            ("ppo", "signal", "histogram"),
            SignalOutputMode.LATEST,
        ),
        signal(
            "bollinger_20_2",
            "BOLLINGER",
            {"period": 20, "multiplier": 2.0},
            ("bands",),
            SignalOutputMode.LATEST,
        ),
    ),
    annotations=_fx_annotations(include_standard=False),
)

FX_STANDARD_BUNDLE = TechnicalBundleSpec(
    bundle_id="fx.standard",
    detail_level=AiExportDetailLevel.STANDARD,
    target_domain=AiExportDomain.FX,
    signals=(
        _ema(20, SignalOutputMode.SAMPLED),
        _ema(50, SignalOutputMode.SAMPLED),
        _ema(200, SignalOutputMode.SAMPLED),
        signal(
            "rsi_14",
            "RSI",
            {"period": 14, "overbought": 70, "oversold": 30},
            ("rsi",),
            SignalOutputMode.SAMPLED,
        ),
        signal(
            "ppo_12_26_9",
            "PPO",
            {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9},
            ("ppo", "signal", "histogram"),
            SignalOutputMode.SAMPLED,
        ),
        signal(
            "bollinger_20_2",
            "BOLLINGER",
            {"period": 20, "multiplier": 2.0},
            ("bands",),
            SignalOutputMode.SAMPLED,
        ),
        signal(
            "roc_20",
            "ROC",
            {"period": 20},
            ("roc",),
            SignalOutputMode.SAMPLED,
        ),
        signal(
            "stoch_rsi_14_3",
            "STOCH_RSI",
            {"period": 14, "dPeriod": 3, "overbought": 80, "oversold": 20},
            ("k", "d"),
            SignalOutputMode.SAMPLED,
        ),
        signal(
            "kama_20",
            "KAMA",
            {"period": 20},
            ("kama",),
            SignalOutputMode.SAMPLED,
        ),
    ),
    annotations=_fx_annotations(include_standard=True),
)

FX_FULL_BUNDLE = TechnicalBundleSpec(
    bundle_id="fx.full",
    detail_level=AiExportDetailLevel.FULL,
    target_domain=AiExportDomain.FX,
    signals=(
        _ema(20, SignalOutputMode.FULL_WINDOW),
        _ema(50, SignalOutputMode.FULL_WINDOW),
        _ema(200, SignalOutputMode.FULL_WINDOW),
        _sma(50, SignalOutputMode.FULL_WINDOW),
        _sma(200, SignalOutputMode.FULL_WINDOW),
        signal(
            "kama_20",
            "KAMA",
            {"period": 20},
            ("kama",),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "rsi_14",
            "RSI",
            {"period": 14, "overbought": 70, "oversold": 30},
            ("rsi",),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "macd_12_26_9",
            "MACD",
            {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9},
            ("macd", "signal", "histogram"),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "ppo_12_26_9",
            "PPO",
            {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9},
            ("ppo", "signal", "histogram"),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "roc_20",
            "ROC",
            {"period": 20},
            ("roc",),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "stoch_rsi_14_3",
            "STOCH_RSI",
            {"period": 14, "dPeriod": 3, "overbought": 80, "oversold": 20},
            ("k", "d"),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "bollinger_20_2",
            "BOLLINGER",
            {"period": 20, "multiplier": 2.0},
            ("bands",),
            SignalOutputMode.FULL_WINDOW,
        ),
    ),
    annotations=_fx_annotations(include_standard=True),
)

FX_BUNDLES = (
    FX_COMPACT_BUNDLE,
    FX_STANDARD_BUNDLE,
    FX_FULL_BUNDLE,
)

_SINGLE_FX_PAIR = compact_selection(
    "single_entity",
    1,
    entity_kind="fx_pair",
)


def _fx_technical(
    compact_depth: TechnicalDepth,
    standard_depth: TechnicalDepth,
):
    return technical_matrix(
        technical_detail(
            AiExportDetailLevel.COMPACT,
            compact_depth,
            FX_COMPACT_BUNDLE,
        ),
        technical_detail(
            AiExportDetailLevel.STANDARD,
            standard_depth,
            FX_STANDARD_BUNDLE,
        ),
        technical_detail(
            AiExportDetailLevel.FULL,
            TechnicalDepth.FULL,
            FX_FULL_BUNDLE,
        ),
    )


FX_TASK_SPECS = (
    TaskSpec(
        domain=AiExportDomain.FX,
        task=AiExportTask.FX_TREND_REVIEW,
        required_sections=("facts.identity", "facts.current_rate", "coverage", "semantics"),
        optional_sections=("facts.sampled_rates", "facts.extrema", "facts.volatility", "facts.normalized_return", "states", "technical", "events", "domain_notes"),
        applicability_code="valid_iso_pair",
        frontend_response_contract_id="fx.fx_trend_review",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=True,
        compact_selection=_SINGLE_FX_PAIR,
        technical_by_detail=_fx_technical(
            TechnicalDepth.LATEST_RATE_AND_STATES,
            TechnicalDepth.STANDARD,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.FX,
        task=AiExportTask.FX_EXPOSURE_IMPACT,
        required_sections=("facts.identity", "facts.current_rate", "facts.exposure_links", "coverage", "semantics"),
        optional_sections=("facts.sampled_rates", "facts.extrema", "facts.volatility", "facts.normalized_return", "states", "technical", "events", "domain_notes"),
        applicability_code="linked_cash_or_position_available",
        frontend_response_contract_id="fx.fx_exposure_impact",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=True,
        compact_selection=_SINGLE_FX_PAIR,
        technical_by_detail=_fx_technical(
            TechnicalDepth.LATEST_EXPOSURE_AND_STATES,
            TechnicalDepth.STANDARD,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.FX,
        task=AiExportTask.FX_CONVERSION_TIMING_CONTEXT,
        required_sections=("facts.identity", "facts.current_rate", "coverage", "semantics"),
        optional_sections=("facts.sampled_rates", "facts.extrema", "facts.volatility", "facts.normalized_return", "states", "technical", "events", "domain_notes"),
        applicability_code="valid_iso_pair",
        frontend_response_contract_id="fx.fx_conversion_timing_context",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=True,
        compact_selection=_SINGLE_FX_PAIR,
        technical_by_detail=_fx_technical(
            TechnicalDepth.LATEST_TREND_AND_VOLATILITY,
            TechnicalDepth.STANDARD_WITH_SAMPLING,
        ),
    ),
)
