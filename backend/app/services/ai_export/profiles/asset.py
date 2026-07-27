"""Static Asset technical bundles and task manifests."""

from __future__ import annotations

from backend.app.schemas.ai_export import AiExportDetailLevel, AiExportDomain, AiExportTask
from backend.app.services.ai_export.models import (
    BandComponent,
    SignalEligibility,
    SignalOutputMode,
    TaskSpec,
    TechnicalBundleSpec,
    TechnicalDepth,
)
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


def _asset_annotations(*, include_standard: bool):
    annotations = [
        line_crossover(
            "price_ema_20",
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
            "macd_signal",
            "macd_12_26_9",
            signal_source("macd_12_26_9", "macd"),
            signal_source("macd_12_26_9", "signal"),
        ),
        threshold_crossing(
            "macd_histogram_zero",
            "macd_12_26_9",
            signal_source("macd_12_26_9", "histogram"),
            0,
        ),
        threshold_crossing(
            "mfi_14_oversold_20",
            "mfi_14",
            signal_source("mfi_14", "mfi"),
            20,
        ),
        threshold_crossing(
            "mfi_14_overbought_80",
            "mfi_14",
            signal_source("mfi_14", "mfi"),
            80,
        ),
        line_crossover(
            "price_bollinger_lower",
            "bollinger_20_2",
            price_source(),
            signal_source(
                "bollinger_20_2",
                "bands",
                band_component=BandComponent.LOWER,
            ),
        ),
        line_crossover(
            "price_bollinger_middle",
            "bollinger_20_2",
            price_source(),
            signal_source(
                "bollinger_20_2",
                "bands",
                band_component=BandComponent.MIDDLE,
            ),
        ),
        line_crossover(
            "price_bollinger_upper",
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
                    "adx_14_trend_25",
                    "adx_14",
                    signal_source("adx_14", "adx"),
                    25,
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
                line_crossover(
                    "price_donchian_lower",
                    "donchian_20",
                    price_source(),
                    signal_source(
                        "donchian_20",
                        "channels",
                        band_component=BandComponent.LOWER,
                    ),
                ),
                line_crossover(
                    "price_donchian_middle",
                    "donchian_20",
                    price_source(),
                    signal_source(
                        "donchian_20",
                        "channels",
                        band_component=BandComponent.MIDDLE,
                    ),
                ),
                line_crossover(
                    "price_donchian_upper",
                    "donchian_20",
                    price_source(),
                    signal_source(
                        "donchian_20",
                        "channels",
                        band_component=BandComponent.UPPER,
                    ),
                ),
            ]
        )
    return tuple(annotations)


ASSET_COMPACT_BUNDLE = TechnicalBundleSpec(
    bundle_id="asset.compact",
    detail_level=AiExportDetailLevel.COMPACT,
    target_domain=AiExportDomain.ASSET,
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
            "macd_12_26_9",
            "MACD",
            {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9},
            ("macd", "signal", "histogram"),
            SignalOutputMode.LATEST,
        ),
        signal(
            "bollinger_20_2",
            "BOLLINGER",
            {"period": 20, "multiplier": 2.0},
            ("bands",),
            SignalOutputMode.LATEST,
        ),
        signal(
            "natr_14",
            "NATR",
            {"period": 14},
            ("natr",),
            SignalOutputMode.LATEST,
        ),
        signal(
            "mfi_14",
            "MFI",
            {"period": 14, "overbought": 80, "oversold": 20},
            ("mfi",),
            SignalOutputMode.LATEST,
            eligibility=SignalEligibility.VOLUME_REQUIRED,
        ),
    ),
    annotations=_asset_annotations(include_standard=False),
)

ASSET_STANDARD_BUNDLE = TechnicalBundleSpec(
    bundle_id="asset.standard",
    detail_level=AiExportDetailLevel.STANDARD,
    target_domain=AiExportDomain.ASSET,
    signals=(
        _ema(20, SignalOutputMode.SAMPLED),
        _ema(50, SignalOutputMode.SAMPLED),
        _ema(200, SignalOutputMode.SAMPLED),
        signal(
            "adx_14",
            "ADX",
            {"period": 14},
            ("adx", "plus_di", "minus_di"),
            SignalOutputMode.SAMPLED,
        ),
        signal(
            "donchian_20",
            "DONCHIAN",
            {"period": 20},
            ("channels",),
            SignalOutputMode.SAMPLED,
        ),
        signal(
            "rsi_14",
            "RSI",
            {"period": 14, "overbought": 70, "oversold": 30},
            ("rsi",),
            SignalOutputMode.SAMPLED,
        ),
        signal(
            "macd_12_26_9",
            "MACD",
            {"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9},
            ("macd", "signal", "histogram"),
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
            "bollinger_20_2",
            "BOLLINGER",
            {"period": 20, "multiplier": 2.0},
            ("bands",),
            SignalOutputMode.SAMPLED,
        ),
        signal(
            "natr_14",
            "NATR",
            {"period": 14},
            ("natr",),
            SignalOutputMode.SAMPLED,
        ),
        signal(
            "mfi_14",
            "MFI",
            {"period": 14, "overbought": 80, "oversold": 20},
            ("mfi",),
            SignalOutputMode.SAMPLED,
            eligibility=SignalEligibility.VOLUME_REQUIRED,
        ),
        signal(
            "obv",
            "OBV",
            {},
            ("obv",),
            SignalOutputMode.STATE_EVENT_ONLY,
            eligibility=SignalEligibility.VOLUME_REQUIRED,
        ),
    ),
    annotations=_asset_annotations(include_standard=True),
)

ASSET_FULL_BUNDLE = TechnicalBundleSpec(
    bundle_id="asset.full",
    detail_level=AiExportDetailLevel.FULL,
    target_domain=AiExportDomain.ASSET,
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
            "aroon_25",
            "AROON",
            {"period": 25},
            ("up", "down", "oscillator"),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "adx_14",
            "ADX",
            {"period": 14},
            ("adx", "plus_di", "minus_di"),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "donchian_20",
            "DONCHIAN",
            {"period": 20},
            ("channels",),
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
            "cci_20",
            "CCI",
            {"period": 20},
            ("cci",),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "bollinger_20_2",
            "BOLLINGER",
            {"period": 20, "multiplier": 2.0},
            ("bands",),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "atr_14",
            "ATR",
            {"period": 14},
            ("atr",),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "natr_14",
            "NATR",
            {"period": 14},
            ("natr",),
            SignalOutputMode.FULL_WINDOW,
        ),
        signal(
            "mfi_14",
            "MFI",
            {"period": 14, "overbought": 80, "oversold": 20},
            ("mfi",),
            SignalOutputMode.FULL_WINDOW,
            eligibility=SignalEligibility.VOLUME_REQUIRED,
        ),
        signal(
            "obv",
            "OBV",
            {},
            ("obv",),
            SignalOutputMode.FULL_WINDOW,
            eligibility=SignalEligibility.VOLUME_REQUIRED,
        ),
    ),
    annotations=_asset_annotations(include_standard=True),
)

ASSET_BUNDLES = (
    ASSET_COMPACT_BUNDLE,
    ASSET_STANDARD_BUNDLE,
    ASSET_FULL_BUNDLE,
)

_SINGLE_ASSET = compact_selection(
    "single_entity",
    1,
    entity_kind="asset",
)


def _asset_technical(
    compact_depth: TechnicalDepth,
    standard_depth: TechnicalDepth,
    full_depth: TechnicalDepth = TechnicalDepth.FULL,
):
    return technical_matrix(
        technical_detail(
            AiExportDetailLevel.COMPACT,
            compact_depth,
            ASSET_COMPACT_BUNDLE,
        ),
        technical_detail(
            AiExportDetailLevel.STANDARD,
            standard_depth,
            ASSET_STANDARD_BUNDLE,
        ),
        technical_detail(
            AiExportDetailLevel.FULL,
            full_depth,
            ASSET_FULL_BUNDLE,
        ),
    )


ASSET_TASK_SPECS = (
    TaskSpec(
        domain=AiExportDomain.ASSET,
        task=AiExportTask.ASSET_SNAPSHOT,
        required_sections=("facts.identity", "coverage", "semantics"),
        optional_sections=("facts.market", "states", "technical", "events", "domain_notes"),
        applicability_code="asset_exists",
        frontend_response_contract_id="asset.asset_snapshot",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=True,
        compact_selection=_SINGLE_ASSET,
        technical_by_detail=_asset_technical(
            TechnicalDepth.LATEST_STATES,
            TechnicalDepth.STANDARD,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.ASSET,
        task=AiExportTask.ASSET_TREND_ANALYSIS,
        required_sections=("facts.identity", "coverage", "semantics"),
        optional_sections=("facts.market", "facts.normalized_return", "states", "technical", "events", "domain_notes"),
        applicability_code="asset_exists_technical_optional",
        frontend_response_contract_id="asset.asset_trend_analysis",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=True,
        compact_selection=_SINGLE_ASSET,
        technical_by_detail=_asset_technical(
            TechnicalDepth.LATEST_TREND_MOMENTUM_VOLATILITY,
            TechnicalDepth.STANDARD_WITH_SERIES,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.ASSET,
        task=AiExportTask.POSITION_REVIEW,
        required_sections=("facts.identity", "facts.current_position", "coverage", "semantics"),
        optional_sections=("facts.market", "facts.lot_summary", "facts.valuation_reference", "states", "technical", "events", "domain_notes"),
        applicability_code="positive_open_quantity_in_scope",
        frontend_response_contract_id="asset.position_review",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=False,
        compact_selection=_SINGLE_ASSET,
        technical_by_detail=_asset_technical(
            TechnicalDepth.LATEST_STATES,
            TechnicalDepth.STANDARD,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.ASSET,
        task=AiExportTask.ASSET_PAC_TIMING_CONTEXT,
        required_sections=("facts.identity", "coverage", "semantics"),
        optional_sections=("facts.market", "facts.normalized_return", "states", "technical", "events", "domain_notes"),
        applicability_code="asset_exists",
        frontend_response_contract_id="asset.asset_pac_timing_context",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=True,
        compact_selection=_SINGLE_ASSET,
        technical_by_detail=_asset_technical(
            TechnicalDepth.LATEST_NEUTRAL_CONTEXT,
            TechnicalDepth.STANDARD_WITH_SAMPLING,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.ASSET,
        task=AiExportTask.DRAWDOWN_RECOVERY,
        required_sections=("facts.identity", "facts.market", "coverage", "semantics"),
        optional_sections=("facts.normalized_return", "states", "technical", "events", "domain_notes"),
        applicability_code="two_observations_and_prior_maximum_available",
        frontend_response_contract_id="asset.drawdown_recovery",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=True,
        compact_selection=_SINGLE_ASSET,
        technical_by_detail=_asset_technical(
            TechnicalDepth.LATEST_DRAWDOWN_CONTEXT,
            TechnicalDepth.STANDARD_WITH_RECOVERY_EVENTS,
        ),
    ),
)
