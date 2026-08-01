"""Pure AI Export coverage and weighted-breadth aggregation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import AbstractSet

from backend.app.schemas.ai_export import (
    AiExportBreadthMetric,
    AiExportCoverage,
    AiExportTechnicalCoverage,
    AiExportVolumeSignalCoverage,
    AiExportWeightedBreadth,
)
from backend.app.services.ai_export.sampling import round_percentage


class BreadthStateCode(StrEnum):
    PRICE_VS_EMA200 = "price_vs_ema200"
    EMA20_VS_EMA50 = "ema20_vs_ema50"
    ADX_STRENGTH = "adx_strength"
    RSI_STATE = "rsi_state"
    MACD_OR_PPO_HISTOGRAM = "macd_or_ppo_histogram"


class BreadthMetricCode(StrEnum):
    PRICE_ABOVE_EMA200 = "price_above_ema200"
    PRICE_BELOW_EMA200 = "price_below_ema200"
    EMA20_ABOVE_EMA50 = "ema20_above_ema50"
    EMA20_BELOW_EMA50 = "ema20_below_ema50"
    ADX_STRONG_TREND = "adx_strong_trend"
    ADX_WEAK_TREND = "adx_weak_trend"
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"
    MACD_OR_PPO_POSITIVE = "macd_or_ppo_positive"
    MACD_OR_PPO_NEGATIVE = "macd_or_ppo_negative"


CANONICAL_BREADTH_METRICS = tuple(metric.value for metric in BreadthMetricCode)
CANONICAL_BREADTH_STATE_KEYS: Mapping[str, str] = MappingProxyType(
    {
        BreadthMetricCode.PRICE_ABOVE_EMA200.value: BreadthStateCode.PRICE_VS_EMA200.value,
        BreadthMetricCode.PRICE_BELOW_EMA200.value: BreadthStateCode.PRICE_VS_EMA200.value,
        BreadthMetricCode.EMA20_ABOVE_EMA50.value: BreadthStateCode.EMA20_VS_EMA50.value,
        BreadthMetricCode.EMA20_BELOW_EMA50.value: BreadthStateCode.EMA20_VS_EMA50.value,
        BreadthMetricCode.ADX_STRONG_TREND.value: BreadthStateCode.ADX_STRENGTH.value,
        BreadthMetricCode.ADX_WEAK_TREND.value: BreadthStateCode.ADX_STRENGTH.value,
        BreadthMetricCode.RSI_OVERBOUGHT.value: BreadthStateCode.RSI_STATE.value,
        BreadthMetricCode.RSI_OVERSOLD.value: BreadthStateCode.RSI_STATE.value,
        BreadthMetricCode.MACD_OR_PPO_POSITIVE.value: BreadthStateCode.MACD_OR_PPO_HISTOGRAM.value,
        BreadthMetricCode.MACD_OR_PPO_NEGATIVE.value: BreadthStateCode.MACD_OR_PPO_HISTOGRAM.value,
    }
)
CANONICAL_BREADTH_QUALIFYING_STATES: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        BreadthMetricCode.PRICE_ABOVE_EMA200.value: frozenset({"above"}),
        BreadthMetricCode.PRICE_BELOW_EMA200.value: frozenset({"below"}),
        BreadthMetricCode.EMA20_ABOVE_EMA50.value: frozenset({"above"}),
        BreadthMetricCode.EMA20_BELOW_EMA50.value: frozenset({"below"}),
        BreadthMetricCode.ADX_STRONG_TREND.value: frozenset({"strong_trend"}),
        BreadthMetricCode.ADX_WEAK_TREND.value: frozenset({"weak_trend"}),
        BreadthMetricCode.RSI_OVERBOUGHT.value: frozenset({"overbought"}),
        BreadthMetricCode.RSI_OVERSOLD.value: frozenset({"oversold"}),
        BreadthMetricCode.MACD_OR_PPO_POSITIVE.value: frozenset({"positive"}),
        BreadthMetricCode.MACD_OR_PPO_NEGATIVE.value: frozenset({"negative"}),
    }
)


def _validated_nav_weight(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError("nav_weight_pct must be a Decimal")
    if not value.is_finite():
        raise ValueError("nav_weight_pct must be finite")
    if value < 0:
        raise ValueError("nav_weight_pct must be non-negative")
    return value


@dataclass(frozen=True, slots=True)
class TargetCoverage:
    """Coverage and neutral breadth state using gross absolute NAV exposure."""

    target_key: str
    eligible: bool
    analyzed: bool
    nav_weight_pct: Decimal
    volume_eligible: bool = False
    volume_analyzed: bool = False
    derived_states: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.target_key, str) or not self.target_key.strip():
            raise ValueError("target_key must be a non-empty string")
        for name in ("eligible", "analyzed", "volume_eligible", "volume_analyzed"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a bool")
        _validated_nav_weight(self.nav_weight_pct)
        if self.analyzed and not self.eligible:
            raise ValueError("analyzed target must be eligible")
        if self.volume_analyzed and not self.volume_eligible:
            raise ValueError("volume-analyzed target must be volume eligible")

        frozen_states: dict[str, str] = {}
        for metric_code, state in self.derived_states.items():
            code = metric_code.value if isinstance(metric_code, BreadthMetricCode) else metric_code
            if not isinstance(code, str) or not code.strip():
                raise ValueError("derived state metric codes must be non-empty strings")
            if not isinstance(state, str) or not state.strip():
                raise ValueError("derived state values must be non-empty strings")
            frozen_states[code] = state
        object.__setattr__(self, "derived_states", MappingProxyType(frozen_states))


TargetCoverageRecord = TargetCoverage


def _sum_nav(records: Iterable[TargetCoverage]) -> Decimal:
    return sum((record.nav_weight_pct for record in records), start=Decimal("0"))


def _validated_qualifying_states(qualifying_states: Mapping[str, AbstractSet[str]]) -> Mapping[str, frozenset[str]]:
    if set(qualifying_states) != set(CANONICAL_BREADTH_METRICS):
        raise ValueError("qualifying_states must define every canonical breadth metric")
    normalized: dict[str, frozenset[str]] = {}
    for metric_code in CANONICAL_BREADTH_METRICS:
        states = qualifying_states[metric_code]
        if any(not isinstance(state, str) or not state for state in states):
            raise ValueError("qualifying state values must be non-empty strings")
        normalized[metric_code] = frozenset(states)
    return MappingProxyType(normalized)


def aggregate_coverage(
    records: Iterable[TargetCoverage],
    *,
    qualifying_states: Mapping[str, AbstractSet[str]] = CANONICAL_BREADTH_QUALIFYING_STATES,
) -> AiExportCoverage:
    """Aggregate full-universe gross exposure coverage and breadth."""

    targets = tuple(records)
    if any(not isinstance(record, TargetCoverage) for record in targets):
        raise TypeError("records must contain TargetCoverage values")
    target_keys = [record.target_key for record in targets]
    if len(target_keys) != len(set(target_keys)):
        raise ValueError("target_key values must be unique")

    metric_states = _validated_qualifying_states(qualifying_states)
    eligible = tuple(record for record in targets if record.eligible)
    analyzed = tuple(record for record in eligible if record.analyzed)
    volume_eligible = tuple(record for record in targets if record.volume_eligible)
    volume_analyzed = tuple(record for record in volume_eligible if record.volume_analyzed)
    eligible_nav = _sum_nav(eligible)

    metrics: list[AiExportBreadthMetric] = []
    for metric_code in CANONICAL_BREADTH_METRICS:
        state_key = CANONICAL_BREADTH_STATE_KEYS[metric_code]
        qualifying = tuple(record for record in eligible if record.analyzed and record.derived_states.get(state_key) in metric_states[metric_code])
        qualifying_nav = _sum_nav(qualifying)
        eligible_weight = Decimal("0") if eligible_nav == 0 else qualifying_nav / eligible_nav * Decimal("100")
        metrics.append(
            AiExportBreadthMetric(
                code=metric_code,
                asset_count=len(qualifying),
                eligible_asset_count=len(eligible),
                portfolio_nav_weight_pct=round_percentage(qualifying_nav),
                eligible_nav_weight_pct=round_percentage(eligible_weight),
            )
        )

    return AiExportCoverage(
        technical=AiExportTechnicalCoverage(
            portfolio_assets=len(targets),
            technically_eligible_assets=len(eligible),
            technically_analyzed_assets=len(analyzed),
            analyzed_nav_weight_pct=round_percentage(_sum_nav(analyzed)),
        ),
        volume=AiExportVolumeSignalCoverage(
            eligible_assets=len(volume_eligible),
            analyzed_assets=len(volume_analyzed),
            analyzed_nav_weight_pct=round_percentage(_sum_nav(volume_analyzed)),
        ),
        weighted_breadth=AiExportWeightedBreadth(
            eligible_assets=len(eligible),
            eligible_nav_weight_pct=round_percentage(eligible_nav),
            metrics=metrics,
        ),
    )


build_coverage = aggregate_coverage
