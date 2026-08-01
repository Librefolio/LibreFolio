"""Focused tests for AI Export coverage and weighted breadth."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from backend.app.services.ai_export.coverage import (
    CANONICAL_BREADTH_METRICS,
    CANONICAL_BREADTH_QUALIFYING_STATES,
    CANONICAL_BREADTH_STATE_KEYS,
    BreadthStateCode,
    TargetCoverage,
    aggregate_coverage,
)


def _record(
    key: str,
    weight: str,
    *,
    eligible: bool = True,
    analyzed: bool = True,
    volume_eligible: bool = False,
    volume_analyzed: bool = False,
    states: dict[str, str] | None = None,
) -> TargetCoverage:
    return TargetCoverage(
        target_key=key,
        eligible=eligible,
        analyzed=analyzed,
        nav_weight_pct=Decimal(weight),
        volume_eligible=volume_eligible,
        volume_analyzed=volume_analyzed,
        derived_states=states or {},
    )


def _metrics_by_code(coverage):
    return {metric.code: metric for metric in coverage.weighted_breadth.metrics}


def test_target_coverage_is_immutable_and_deeply_freezes_states():
    record = _record(
        "asset:1",
        "25",
        states={BreadthStateCode.PRICE_VS_EMA200: "above"},
    )

    assert record.derived_states == {"price_vs_ema200": "above"}
    with pytest.raises(FrozenInstanceError):
        record.eligible = False  # type: ignore[misc]
    with pytest.raises(TypeError):
        record.derived_states["price_vs_ema200"] = "below"  # type: ignore[index]


@pytest.mark.parametrize("weight", (Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity")))
def test_target_coverage_rejects_invalid_nav_weight(weight):
    with pytest.raises(ValueError):
        TargetCoverage(target_key="asset:1", eligible=True, analyzed=True, nav_weight_pct=weight)


def test_target_coverage_validates_eligibility_implications():
    with pytest.raises(ValueError, match="must be eligible"):
        _record("asset:1", "10", eligible=False, analyzed=True)
    with pytest.raises(ValueError, match="volume eligible"):
        _record("asset:1", "10", volume_eligible=False, volume_analyzed=True)


def test_canonical_metrics_have_explicit_qualifying_states():
    assert CANONICAL_BREADTH_METRICS == (
        "price_above_ema200",
        "price_below_ema200",
        "ema20_above_ema50",
        "ema20_below_ema50",
        "adx_strong_trend",
        "adx_weak_trend",
        "rsi_overbought",
        "rsi_oversold",
        "macd_or_ppo_positive",
        "macd_or_ppo_negative",
    )
    assert CANONICAL_BREADTH_QUALIFYING_STATES == {
        "price_above_ema200": frozenset({"above"}),
        "price_below_ema200": frozenset({"below"}),
        "ema20_above_ema50": frozenset({"above"}),
        "ema20_below_ema50": frozenset({"below"}),
        "adx_strong_trend": frozenset({"strong_trend"}),
        "adx_weak_trend": frozenset({"weak_trend"}),
        "rsi_overbought": frozenset({"overbought"}),
        "rsi_oversold": frozenset({"oversold"}),
        "macd_or_ppo_positive": frozenset({"positive"}),
        "macd_or_ppo_negative": frozenset({"negative"}),
    }
    assert CANONICAL_BREADTH_STATE_KEYS["rsi_overbought"] == "rsi_state"
    assert CANONICAL_BREADTH_STATE_KEYS["rsi_oversold"] == "rsi_state"


def test_aggregate_coverage_counts_nav_volume_and_full_universe_breadth():
    records = (
        _record(
            "asset:1",
            "40",
            volume_eligible=True,
            volume_analyzed=True,
            states={
                "price_vs_ema200": "above",
                "ema20_vs_ema50": "above",
                "adx_strength": "strong_trend",
                "rsi_state": "overbought",
                "macd_or_ppo_histogram": "positive",
            },
        ),
        _record(
            "asset:2",
            "30",
            volume_eligible=True,
            volume_analyzed=False,
            states={
                "price_vs_ema200": "below",
                "ema20_vs_ema50": "below",
                "adx_strength": "weak_trend",
                "rsi_state": "neutral",
                "macd_or_ppo_histogram": "negative",
            },
        ),
        _record("asset:3", "20", eligible=False, analyzed=False),
        _record("asset:4", "10", eligible=True, analyzed=False, states={"price_vs_ema200": "above"}),
    )

    coverage = aggregate_coverage(records)
    metrics = _metrics_by_code(coverage)

    assert coverage.technical.portfolio_assets == 4
    assert coverage.technical.technically_eligible_assets == 3
    assert coverage.technical.technically_analyzed_assets == 2
    assert coverage.technical.analyzed_nav_weight_pct == Decimal("70.00")
    assert coverage.volume.eligible_assets == 2
    assert coverage.volume.analyzed_assets == 1
    assert coverage.volume.analyzed_nav_weight_pct == Decimal("40.00")
    assert coverage.weighted_breadth.eligible_assets == 3
    assert coverage.weighted_breadth.eligible_nav_weight_pct == Decimal("80.00")

    above_ema200 = metrics["price_above_ema200"]
    assert above_ema200.asset_count == 1
    assert above_ema200.eligible_asset_count == 3
    assert above_ema200.portfolio_nav_weight_pct == Decimal("40.00")
    assert above_ema200.eligible_nav_weight_pct == Decimal("50.00")
    assert metrics["price_below_ema200"].asset_count == 1
    assert metrics["rsi_overbought"].asset_count == 1
    assert metrics["rsi_oversold"].asset_count == 0
    assert metrics["macd_or_ppo_positive"].asset_count == 1
    assert metrics["macd_or_ppo_negative"].asset_count == 1
    assert all(metric.eligible_asset_count == 3 for metric in metrics.values())


def test_unanalyzed_targets_are_neutral_but_stay_in_breadth_denominator():
    coverage = aggregate_coverage(
        (
            _record("asset:1", "20", states={"price_vs_ema200": "above"}),
            _record("asset:2", "30", analyzed=False, states={"price_vs_ema200": "above"}),
            _record("asset:3", "50", states={"price_vs_ema200": "below"}),
        )
    )

    metric = _metrics_by_code(coverage)["price_above_ema200"]
    assert metric.asset_count == 1
    assert metric.eligible_asset_count == 3
    assert metric.portfolio_nav_weight_pct == Decimal("20.00")
    assert metric.eligible_nav_weight_pct == Decimal("20.00")


def test_gross_exposure_coverage_can_exceed_portfolio_nav():
    coverage = aggregate_coverage(
        (
            _record(
                "asset:1",
                "80",
                volume_eligible=True,
                volume_analyzed=True,
                states={"price_vs_ema200": "above"},
            ),
            _record(
                "asset:2",
                "70",
                volume_eligible=True,
                volume_analyzed=True,
                states={"price_vs_ema200": "below"},
            ),
        )
    )
    metrics = _metrics_by_code(coverage)

    assert coverage.technical.analyzed_nav_weight_pct == Decimal("150.00")
    assert coverage.volume.analyzed_nav_weight_pct == Decimal("150.00")
    assert coverage.weighted_breadth.eligible_nav_weight_pct == Decimal("150.00")
    assert metrics["price_above_ema200"].portfolio_nav_weight_pct == Decimal("80.00")
    assert metrics["price_above_ema200"].eligible_nav_weight_pct == Decimal("53.33")
    assert metrics["price_below_ema200"].portfolio_nav_weight_pct == Decimal("70.00")
    assert metrics["price_below_ema200"].eligible_nav_weight_pct == Decimal("46.67")


def test_zero_nav_and_zero_eligible_denominators_are_safe():
    zero_nav = aggregate_coverage((_record("asset:1", "0", states={"rsi_state": "oversold"}),))
    no_eligible = aggregate_coverage((_record("asset:1", "0", eligible=False, analyzed=False),))

    zero_metric = _metrics_by_code(zero_nav)["rsi_oversold"]
    assert zero_metric.asset_count == 1
    assert zero_metric.portfolio_nav_weight_pct == Decimal("0.00")
    assert zero_metric.eligible_nav_weight_pct == Decimal("0.00")
    assert no_eligible.weighted_breadth.eligible_assets == 0
    assert no_eligible.weighted_breadth.eligible_nav_weight_pct == Decimal("0.00")
    assert all(metric.eligible_asset_count == 0 and metric.eligible_nav_weight_pct == Decimal("0.00") for metric in no_eligible.weighted_breadth.metrics)


def test_empty_universe_returns_complete_zero_coverage():
    coverage = aggregate_coverage(())

    assert coverage.technical.portfolio_assets == 0
    assert coverage.volume.eligible_assets == 0
    assert coverage.weighted_breadth.eligible_assets == 0
    assert [metric.code for metric in coverage.weighted_breadth.metrics] == list(CANONICAL_BREADTH_METRICS)


def test_aggregate_rejects_duplicate_targets():
    with pytest.raises(ValueError, match="unique"):
        aggregate_coverage((_record("asset:1", "20"), _record("asset:1", "30")))


def test_custom_qualifying_states_must_cover_every_canonical_metric():
    with pytest.raises(ValueError, match="every canonical"):
        aggregate_coverage(
            (_record("asset:1", "10"),),
            qualifying_states={"price_above_ema200": {"below"}},
        )
