"""Hand-derived tests for deterministic risk mathematics."""

from __future__ import annotations

import math

import pytest

from backend.app.services.risk.metrics import (
    annualized_sortino,
    comparison_summary,
    correlation_matrix,
    covariance_matrix,
    current_buy_and_hold_returns,
    historical_var_cvar,
    hypothetical_stress_return,
    pairwise_correlation,
    period_returns_from_cumulative,
    risk_contributions_from_covariance,
    summarize_drawdown,
)


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
