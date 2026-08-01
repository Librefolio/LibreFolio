"""Hand-derived tests for deterministic risk mathematics."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from backend.app.services.risk.metrics import (
    annualized_sortino,
    comparison_summary,
    correlation_matrix,
    covariance_matrix,
    current_buy_and_hold_returns,
    drawdown_episodes,
    historical_var_cvar,
    hypothetical_stress_return,
    pairwise_correlation,
    period_returns_from_cumulative,
    risk_contributions_from_covariance,
    summarize_drawdown,
)

_BASELINE = date(2026, 1, 1)


def _regular_dates(count: int) -> list[date]:
    return [_BASELINE + timedelta(days=index + 1) for index in range(count)]


def test_period_returns_and_drawdown_are_derived_from_exact_wealth():
    assert period_returns_from_cumulative([0.0, 0.1, 0.045]) == pytest.approx([0.1, -0.05])

    summary = summarize_drawdown(
        [0.1, -0.2, 0.1, 0.15],
        elapsed_units=[0, 1, 2, 3, 4],
    )
    assert summary.wealth_index == pytest.approx((1.0, 1.1, 0.88, 0.968, 1.1132))
    assert summary.drawdowns == pytest.approx((0.0, 0.0, -0.2, -0.12, 0.0))
    assert summary.max_drawdown == pytest.approx(-0.2)
    assert summary.max_duration == 3


def test_sortino_uses_population_downside_deviation_against_explicit_mar():
    returns = [-0.01, 0.02, 0.03]
    annualization = 365.0
    downside_deviation = math.sqrt((0.01**2) / 3)
    expected = (sum(returns) / 3) / downside_deviation * math.sqrt(annualization)

    assert annualized_sortino(returns, annualization) == pytest.approx(expected)
    assert annualized_sortino([0.01, 0.02], annualization) is None


def test_covariance_correlation_and_pairwise_coverage_are_explicit():
    left = [-1.0, 0.0, 1.0]
    right = [1.0, 0.0, -1.0]

    covariance = covariance_matrix([left, right])
    correlation = correlation_matrix([left, right])
    assert covariance[0] == pytest.approx([1.0, -1.0])
    assert covariance[1] == pytest.approx([-1.0, 1.0])
    assert correlation[0] == pytest.approx([1.0, -1.0])
    assert correlation[1] == pytest.approx([-1.0, 1.0])

    value, observations, coverage = pairwise_correlation(
        [1.0, None, 3.0, 4.0],
        [2.0, 2.0, None, 8.0],
        expected_observations=4,
    )
    assert value == pytest.approx(1.0)
    assert observations == 2
    assert coverage == pytest.approx(0.5)


def test_pctr_is_additive_and_preserves_negative_diversification():
    # Valid covariance matrix: variances 4% and 1%, correlation -0.75.
    summary = risk_contributions_from_covariance(
        [
            [0.04, -0.015],
            [-0.015, 0.01],
        ],
        [0.5, 0.5],
    )

    expected_sigma = math.sqrt(0.005)
    assert summary.portfolio_volatility == pytest.approx(expected_sigma)
    assert sum(summary.component) == pytest.approx(expected_sigma)
    assert summary.percentage == pytest.approx((1.25, -0.25))
    assert sum(summary.percentage) == pytest.approx(1.0)

    zero = risk_contributions_from_covariance(
        [
            [0.0, 0.0],
            [0.0, 0.0],
        ],
        [0.75, 0.0],
    )
    assert zero.portfolio_volatility == 0
    assert zero.marginal == (0.0, 0.0)
    assert zero.component == (0.0, 0.0)
    assert zero.percentage == (0.0, 0.0)


def test_current_buy_and_hold_drifts_weights_and_keeps_cash_flat():
    returns = current_buy_and_hold_returns(
        {
            1: [0.1, 0.0],
            2: [0.0, 0.1],
        },
        {
            1: 0.5,
            2: 0.25,
        },
        cash_weight=0.25,
    )

    assert returns == pytest.approx([0.05, 1.075 / 1.05 - 1])
    assert math.prod(1 + value for value in returns) - 1 == pytest.approx(0.075)

    stressed, contributions = hypothetical_stress_return(
        {1: -0.2, 2: 0.1},
        {1: 0.5, 2: 0.25},
    )
    assert contributions == pytest.approx({1: -0.1, 2: 0.025})
    assert stressed == pytest.approx(-0.075)


def test_comparison_identity_has_zero_te_ir_and_unit_beta():
    returns = [0.1, -0.05, 0.02]
    summary = comparison_summary(returns, returns, 365.0)

    assert summary.active_return == pytest.approx(0.0)
    assert summary.tracking_error == pytest.approx(0.0)
    assert summary.information_ratio is None
    assert summary.correlation == pytest.approx(1.0)
    assert summary.beta == pytest.approx(1.0)
    assert summary.primary_cumulative == pytest.approx(summary.comparison_cumulative)
    assert summary.primary_drawdowns == pytest.approx(summary.comparison_drawdowns)


def test_historical_var_cvar_uses_positive_observed_loss_magnitudes():
    tail = historical_var_cvar(
        [-0.1, -0.05, 0.0, 0.02, 0.03],
        confidence_level=0.8,
    )
    assert tail.value_at_risk == pytest.approx(0.05)
    assert tail.conditional_value_at_risk == pytest.approx(0.075)
    assert tail.conditional_value_at_risk >= tail.value_at_risk >= 0

    two_day = historical_var_cvar(
        [-0.1, 0.0, -0.2],
        confidence_level=0.5,
        horizon_days=2,
    )
    assert two_day.horizon_returns == pytest.approx((-0.1, -0.2))
    assert two_day.value_at_risk == pytest.approx(0.1)
    assert two_day.conditional_value_at_risk == pytest.approx(0.15)


def test_drawdown_episodes_report_no_drawdown_for_monotonic_growth():
    report = drawdown_episodes(
        [0.01, 0.02, 0.015, 0.03],
        dates=_regular_dates(4),
        baseline_date=_BASELINE,
    )
    assert report.maximum_drawdown_recovery_status == "no_drawdown"
    assert report.maximum_drawdown == 0.0
    assert report.maximum_drawdown_peak_date is None
    assert report.maximum_drawdown_trough_date is None
    assert report.maximum_drawdown_recovery_date is None
    assert report.maximum_drawdown_recovered_ratio is None
    assert report.maximum_drawdown_duration_days == 0
    assert report.current_drawdown == 0.0
    assert report.current_drawdown_duration_days == 0
    assert report.remaining_to_peak_ratio == 0.0
    assert report.current_peak_date == _regular_dates(4)[-1]
    assert report.available_start == _regular_dates(4)[0]
    assert report.available_end == _regular_dates(4)[-1]
    assert report.n_observations == 4


def test_drawdown_episodes_report_open_episode_uses_available_end():
    dates = _regular_dates(5)
    report = drawdown_episodes(
        [0.1, 0.1, -0.1, -0.1, -0.1],
        dates=dates,
        baseline_date=_BASELINE,
    )
    assert report.maximum_drawdown_recovery_status == "open"
    assert report.maximum_drawdown == pytest.approx(1.21 * 0.9**3 / 1.21 - 1.0)
    assert report.maximum_drawdown_peak_date == dates[1]
    assert report.maximum_drawdown_trough_date == dates[4]
    assert report.maximum_drawdown_recovery_date is None
    assert report.maximum_drawdown_recovered_ratio == 0.0
    assert report.maximum_drawdown_duration_days == (dates[4] - dates[1]).days
    assert report.current_drawdown == report.maximum_drawdown
    assert report.current_drawdown_duration_days == (dates[4] - dates[1]).days
    assert report.remaining_to_peak_ratio > 0.0


def test_drawdown_episodes_report_recovered_episode_reports_recovery_date():
    dates = _regular_dates(4)
    report = drawdown_episodes(
        [0.1, -0.2, -0.1, 0.6],
        dates=dates,
        baseline_date=_BASELINE,
    )
    assert report.maximum_drawdown_recovery_status == "recovered"
    assert report.maximum_drawdown_peak_date == dates[0]
    assert report.maximum_drawdown_trough_date == dates[2]
    assert report.maximum_drawdown_recovery_date == dates[3]
    assert report.maximum_drawdown_recovered_ratio == 1.0
    assert report.maximum_drawdown_duration_days == (dates[3] - dates[0]).days
    assert report.current_drawdown == 0.0
    assert report.remaining_to_peak_ratio == 0.0


def test_drawdown_episodes_report_selects_deepest_of_multiple_episodes():
    dates = _regular_dates(7)
    report = drawdown_episodes(
        [0.05, -0.05, 0.10, 0.20, -0.30, -0.05, 0.05],
        dates=dates,
        baseline_date=_BASELINE,
    )
    # The second decline (from the higher peak) is deeper than the first.
    assert report.maximum_drawdown_peak_date == dates[3]
    assert report.maximum_drawdown_trough_date == dates[5]
    assert report.maximum_drawdown_recovery_status == "open"


def test_drawdown_episodes_report_breaks_equal_depth_ties_chronologically():
    dates = _regular_dates(6)
    # Two disjoint episodes with identical -50% depth (exact floats); earliest peak wins.
    report = drawdown_episodes(
        [-0.5, 1.0, -0.5, 1.0, 0.0, 0.0],
        dates=dates,
        baseline_date=_BASELINE,
    )
    assert report.maximum_drawdown == pytest.approx(-0.5)
    assert report.maximum_drawdown_peak_date == _BASELINE
    assert report.maximum_drawdown_trough_date == dates[0]


def test_drawdown_episodes_report_supports_irregular_dates():
    dates = [
        _BASELINE + timedelta(days=3),
        _BASELINE + timedelta(days=10),
        _BASELINE + timedelta(days=40),
    ]
    report = drawdown_episodes(
        [0.1, -0.2, -0.05],
        dates=dates,
        baseline_date=_BASELINE,
    )
    assert report.maximum_drawdown_recovery_status == "open"
    assert report.maximum_drawdown_peak_date == dates[0]
    assert report.maximum_drawdown_trough_date == dates[2]
    assert report.maximum_drawdown_duration_days == (dates[2] - dates[0]).days
    assert report.current_drawdown_duration_days == (dates[2] - dates[0]).days


def test_drawdown_episodes_report_current_and_maximum_can_differ():
    dates = _regular_dates(6)
    report = drawdown_episodes(
        [0.1, -0.3, 0.6, 0.0, -0.05, -0.02],
        dates=dates,
        baseline_date=_BASELINE,
    )
    # Maximum episode recovered early; a distinct shallow episode is still open.
    assert report.maximum_drawdown_recovery_status == "recovered"
    assert report.maximum_drawdown < report.current_drawdown < 0.0
    assert report.current_peak_date == dates[3]


def test_drawdown_episodes_rejects_misaligned_dates():
    with pytest.raises(ValueError, match="align"):
        drawdown_episodes([0.1, -0.1], dates=_regular_dates(3), baseline_date=_BASELINE)


def test_drawdown_episodes_rejects_non_increasing_dates():
    with pytest.raises(ValueError, match="strictly increasing"):
        drawdown_episodes(
            [0.1, -0.1],
            dates=[_BASELINE + timedelta(days=2), _BASELINE + timedelta(days=1)],
            baseline_date=_BASELINE,
        )


def test_drawdown_episodes_rejects_baseline_not_before_first_date():
    with pytest.raises(ValueError, match="strictly increasing"):
        drawdown_episodes([0.1], dates=[_BASELINE], baseline_date=_BASELINE)


def test_drawdown_episodes_requires_at_least_one_return():
    with pytest.raises(ValueError, match="at least one return"):
        drawdown_episodes([], dates=[], baseline_date=_BASELINE)
