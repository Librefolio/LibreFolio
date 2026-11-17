"""Hand-derived tests for deterministic risk mathematics."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from backend.app.services.financial_math.returns import calendar_days_to_observations
from backend.app.services.risk import metrics as risk_metrics_module
from backend.app.services.risk.acquired import average_drawdown, best_realization, best_realization_index
from backend.app.services.risk.metrics import (
    annualized_downside_deviation,
    annualized_expected_return,
    annualized_sharpe,
    annualized_sortino,
    annualized_volatility,
    best_horizon_window,
    comparison_summary,
    compounded_return,
    correlation_matrix,
    covariance_matrix,
    current_buy_and_hold_returns,
    daily_risk_free_rate,
    drawdown_episodes,
    extreme_day_ratio,
    gain_threshold,
    historical_var_cvar,
    hypothetical_stress_return,
    largest_rally,
    longest_positive_run,
    mean_negative_return,
    mean_positive_return,
    omega_ratio,
    pairwise_correlation,
    period_returns_from_cumulative,
    positive_observation_share,
    return_distribution_histogram,
    return_shape,
    risk_contributions_from_covariance,
    summarize_drawdown,
    wealth_index,
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


def test_annualized_expected_return_makes_the_line_through_the_intercept_the_sharpe_ratio():
    """The identity the arithmetic convention exists for.

    ``(mean * f) / (stdev * sqrt(f))`` is ``(mean / stdev) * sqrt(f)``, which is
    exactly what :func:`annualized_sharpe` returns at a zero risk-free rate. So a
    Capital Market Line drawn from the intercept through ``(volatility, expected
    return)`` has the Sharpe ratio as its slope, and "above the line" means "better
    paid for the risk taken". A compounded annualization keeps the point and tilts
    the line, which is a chart that stays plausible and stops being true.

    The factor is varied because the identity is what survives the choice of one:
    it holds because ``f / sqrt(f) == sqrt(f)``, not because 365 is special.
    """
    returns = [round(0.006 * math.sin(index * 0.7) + 0.0015, 12) for index in range(24)]
    mean = math.fsum(returns) / len(returns)

    for annualization in (12.0, 252.0, 365.0):
        expected = annualized_expected_return(returns, annualization)
        volatility = annualized_volatility(returns, annualization)
        sharpe = annualized_sharpe(returns, annualization, annual_risk_free_rate=0.0)

        assert sharpe is not None
        assert expected == pytest.approx(mean * annualization, rel=1e-12)
        assert expected / volatility == pytest.approx(sharpe, rel=1e-12)


def test_annualized_expected_return_is_arithmetic_and_leaves_the_volatility_drag_visible():
    """Zero expected return, guaranteed loss — the gap the label must respect.

    A ±10% alternation has an arithmetic mean of exactly zero, so this function
    reports exactly zero, while compounding the same days loses 1% per pair. Both
    answer their own question correctly; only one of them is "what it returned".
    The gap is the volatility drag, and it is zero exactly when the dispersion is.
    """
    alternating = [0.10, -0.10] * 10
    annualization = float(len(alternating))  # the window is exactly one year long

    assert annualized_expected_return(alternating, annualization) == pytest.approx(0.0, abs=1e-15)
    assert compounded_return(alternating) == pytest.approx(0.99**10 - 1, rel=1e-12)

    geometric_mean = (1.0 + compounded_return(alternating)) ** (1 / len(alternating)) - 1.0
    assert geometric_mean < 0.0
    # Same series, same factor: the arithmetic figure sits ten points above the
    # compounded one, which is why substituting either for the other moves a chart.
    assert annualized_expected_return(alternating, annualization) - geometric_mean * annualization > 0.09

    flat = [0.002] * 20
    flat_geometric = (1.0 + compounded_return(flat)) ** (1 / len(flat)) - 1.0
    assert annualized_expected_return(flat, 20.0) == pytest.approx(flat_geometric * 20.0, rel=1e-12)


def test_annualized_expected_return_refuses_input_no_mean_can_be_taken_of():
    with pytest.raises(ValueError, match="at least one observation"):
        annualized_expected_return([], 365.0)
    with pytest.raises(ValueError, match="returns must be finite"):
        annualized_expected_return([0.01, math.nan], 365.0)
    with pytest.raises(ValueError, match="returns must be finite"):
        annualized_expected_return([0.01, math.inf], 365.0)
    with pytest.raises(ValueError, match="annualization_factor must be finite and positive"):
        annualized_expected_return([0.01, 0.02], 0.0)
    with pytest.raises(ValueError, match="annualization_factor must be finite and positive"):
        annualized_expected_return([0.01, 0.02], -365.0)

    # One observation is a mean; it is not a dispersion. The asymmetry is the
    # reason `asset_risk_return` drops single-point assets instead of pairing a
    # defined return with a volatility it never measured.
    assert annualized_expected_return([0.01], 365.0) == pytest.approx(3.65)
    with pytest.raises(ValueError, match="at least two observations"):
        annualized_volatility([0.01], 365.0)


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
    """Coherent (Acerbi-Tasche) tail risk on loss magnitudes — see M2.

    The nominal tail is ``m = (1 - confidence) * T`` observations; the boundary
    observation counts for the fraction of it that falls inside the tail. Values
    updated from the pre-M2 plug-in estimator, which counted it whole and understated
    CVaR by a measured 0.27 %.
    """
    tail = historical_var_cvar(
        [-0.1, -0.05, 0.0, 0.02, 0.03],
        confidence_level=0.8,
    )
    # m = 0.2 * 5 = 1 exactly: the tail is the single worst loss, so VaR == CVaR.
    assert tail.value_at_risk == pytest.approx(0.10)
    assert tail.conditional_value_at_risk == pytest.approx(0.10)
    assert tail.conditional_value_at_risk >= tail.value_at_risk >= 0

    two_day = historical_var_cvar(
        [-0.1, 0.0, -0.2],
        confidence_level=0.5,
        horizon_observations=2,
    )
    # m = 0.5 * 2 = 1: again the single worst two-day loss.
    assert two_day.horizon_returns == pytest.approx((-0.1, -0.2))
    assert two_day.value_at_risk == pytest.approx(0.2)
    assert two_day.conditional_value_at_risk == pytest.approx(0.2)


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
    # P19: no trough, no climb back.
    assert report.maximum_drawdown_trough_to_peak_ratio == 0.0


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
    # P19: the trough is 0.9**3 of the peak, so the climb back is 1 / 0.9**3 - 1. The episode ends on its trough,
    # so the climb from the worst trough and the gain still owed from the current value are the same number.
    assert report.maximum_drawdown_trough_to_peak_ratio == pytest.approx(1.0 / 0.9**3 - 1.0)
    assert report.remaining_to_peak_ratio == pytest.approx(1.0 / 0.9**3 - 1.0)


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
    # P19: recovered, and the depth is still the depth. From the trough, 0.8 * 0.9 of the peak, the climb back took
    # 1 / 0.72 - 1: the ratio describes how deep the episode went, not whether it is over.
    assert report.maximum_drawdown_trough_to_peak_ratio == pytest.approx(1.0 / (0.8 * 0.9) - 1.0)


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
    # P19: the climb from the deeper trough, 0.7 * 0.95 of the higher peak, not from the first one (0.95 of the lower
    # peak, 1 / 0.95 - 1). Still open but off its trough: what it still owes is measured from the current value,
    # 0.7 * 0.95 * 1.05 of the same peak, and is a smaller number.
    assert report.maximum_drawdown_trough_to_peak_ratio == pytest.approx(1.0 / (0.7 * 0.95) - 1.0)
    assert report.remaining_to_peak_ratio == pytest.approx(1.0 / (0.7 * 0.95 * 1.05) - 1.0)


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
    # P19: each ratio follows its own drawdown. The climb from the worst trough, 0.7 of its peak, and the gain the
    # still-open shallow episode owes from the current value, 0.95 * 0.98 of the new peak.
    assert report.maximum_drawdown_trough_to_peak_ratio == pytest.approx(1.0 / 0.7 - 1.0)
    assert report.remaining_to_peak_ratio == pytest.approx(1.0 / (0.95 * 0.98) - 1.0)


# P19 (workstream J, CP-13a): the gain that recovers a drawdown, ``-d / (1 + d)``, comes from its one home,
# ``financial_math.returns.required_recovery_return``. ``remaining_to_peak_ratio`` is that gain from the current value;
# ``maximum_drawdown_trough_to_peak_ratio`` is that gain from the worst trough back to the peak before it, whether the
# episode is still open or has recovered: it describes the depth, not the recovery state. A total loss has no finite
# gain, so both are None. As below, the home function is reached through the module while a test runs, never imported
# here: until it exists each pin fails on its own instead of breaking the collection of the whole risk suite.


def test_drawdown_episodes_report_a_twenty_percent_fall_needs_a_twenty_five_percent_climb():
    report = drawdown_episodes([0.25, -0.2], dates=_regular_dates(2), baseline_date=_BASELINE)

    assert report.maximum_drawdown_recovery_status == "open"
    assert report.maximum_drawdown == pytest.approx(-0.2)
    assert report.maximum_drawdown_trough_to_peak_ratio == pytest.approx(0.25)
    assert report.remaining_to_peak_ratio == pytest.approx(0.25)


def test_drawdown_episodes_report_the_climb_from_the_trough_once_recovered():
    report = drawdown_episodes([0.25, -0.2, 0.25], dates=_regular_dates(3), baseline_date=_BASELINE)

    assert report.maximum_drawdown_recovery_status == "recovered"
    assert report.maximum_drawdown_trough_to_peak_ratio == pytest.approx(0.25)
    assert report.current_drawdown == 0.0
    assert report.remaining_to_peak_ratio == 0.0


def test_drawdown_episodes_report_no_gain_for_a_dip_within_the_zero_tolerance():
    # One ulp below the peak is a floating-point artefact, not a drawdown: both gains stay exactly 0.0, rather than
    # the 1e-16 the home function would compute from it.
    report = drawdown_episodes([0.0, -(2.0**-53)], dates=_regular_dates(2), baseline_date=_BASELINE)

    assert -risk_metrics_module.ZERO_TOLERANCE < report.current_drawdown < 0.0
    assert report.maximum_drawdown_recovery_status == "no_drawdown"
    assert report.remaining_to_peak_ratio == 0.0
    assert report.maximum_drawdown_trough_to_peak_ratio == 0.0


def test_drawdown_episodes_report_a_total_loss_in_floating_point_without_dividing_by_zero():
    returns = [-0.9999999999, -0.9999999999]
    # The precondition, verified rather than assumed: about 1e-20 of the wealth is left, still positive, so the
    # underwater curve accepts it; and 1e-20 / 1 - 1 rounds to exactly -1.0, the drawdown at which -d / (1 + d)
    # divides by zero.
    wealth = risk_metrics_module.wealth_index(returns)
    assert 0.0 < wealth[-1] < 1e-15
    assert risk_metrics_module.underwater_drawdown(wealth)[-1] == -1.0

    report = drawdown_episodes(returns, dates=_regular_dates(2), baseline_date=_BASELINE)

    assert report.current_drawdown == -1.0
    assert report.maximum_drawdown == -1.0
    assert report.maximum_drawdown_recovery_status == "open"
    assert report.maximum_drawdown_recovered_ratio == 0.0
    # No finite gain climbs back from nothing: both ratios say so with None, never with a number.
    assert report.remaining_to_peak_ratio is None
    assert report.maximum_drawdown_trough_to_peak_ratio is None


def test_drawdown_episodes_take_both_gains_from_the_financial_math_home(monkeypatch):
    # The series statistics read the home function from their own module namespace, so a stub put there must reach
    # both ratios: a formula kept in metrics.py would ignore it.
    sentinel = 0.123
    asked: list[float] = []

    def stub(drawdown: float) -> float:
        asked.append(drawdown)
        return sentinel

    monkeypatch.setattr(risk_metrics_module, "required_recovery_return", stub)
    # Open and off its trough: the worst trough is 0.8 of the peak, the current value 0.88 of it.
    report = drawdown_episodes([0.25, -0.2, 0.1], dates=_regular_dates(3), baseline_date=_BASELINE)

    assert report.maximum_drawdown_recovery_status == "open"
    assert report.maximum_drawdown_trough_to_peak_ratio == sentinel
    assert report.remaining_to_peak_ratio == sentinel
    # Each ratio asked the home about its own drawdown.
    assert report.maximum_drawdown == pytest.approx(-0.2)
    assert report.current_drawdown == pytest.approx(-0.12)
    assert any(drawdown == pytest.approx(report.maximum_drawdown) for drawdown in asked)
    assert any(drawdown == pytest.approx(report.current_drawdown) for drawdown in asked)


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


# One conversion from calendar days to the observations a series holds, shared by the VaR horizons,
# the simulation's drift and block guard and the resampler's steps, blocks and regimes (developer's
# decision of 30/09/2026). Its home is financial_math/returns.py since J-1, beside its inverse.


@pytest.mark.parametrize(
    ("calendar_days", "per_year", "observations"),
    [
        pytest.param(30, 252.0, 21, id="a-month-of-a-252-a-year-series"),
        pytest.param(30, 365.0, 30, id="a-month-of-a-series-quoted-every-day"),
        pytest.param(1, 252.0, 1, id="a-day-of-a-252-a-year-series"),
        pytest.param(1, 100.0, 1, id="never-fewer-than-one"),
        pytest.param(426, 252.0, 294, id="the-prolonged-crisis-in-252-a-year-steps"),
        pytest.param(5, 252.0, 3, id="a-five-day-block-in-252-a-year-steps"),
    ],
)
def test_calendar_days_convert_to_the_observations_a_series_holds(calendar_days, per_year, observations):
    converted = calendar_days_to_observations(calendar_days, per_year)

    assert converted == observations
    assert isinstance(converted, int)


# --------------------------------------------------------------------------- #
# RN-14 — the positive measures and the shape of the days (domande-RISK.md, «Le misure, fissate», 12/11/2026).
# Each measure has one definition, shared by the card, the lab column and the future rolling signal: these are hand
# derivations of that definition; the library oracles are in test_risk_metrics_oracle.py.
# --------------------------------------------------------------------------- #

_SHAPE_RETURNS = [0.02, -0.01, 0.03, -0.02]


def test_the_downside_deviation_is_the_sortino_denominator_annualized_over_t():
    period = math.sqrt((0.01**2 + 0.02**2) / 4)

    assert annualized_downside_deviation(_SHAPE_RETURNS, 252.0) == pytest.approx(period * math.sqrt(252.0), rel=1e-12)
    # The Sortino is the annualized excess return over the same deviation: one function, not a copy.
    excess_mean = math.fsum(_SHAPE_RETURNS) / 4
    assert annualized_sortino(_SHAPE_RETURNS, 252.0) == pytest.approx(excess_mean * 252.0 / annualized_downside_deviation(_SHAPE_RETURNS, 252.0), rel=1e-12)
    assert annualized_downside_deviation([0.01, 0.02], 252.0) == 0.0


def test_omega_sums_the_gains_over_the_losses_against_the_sortino_threshold():
    assert omega_ratio(_SHAPE_RETURNS, 252.0) == pytest.approx(0.05 / 0.03, rel=1e-12)
    # A threshold above zero moves both sums: the same daily target the Sortino charges.
    target = daily_risk_free_rate(0.05, 252.0)
    gains = math.fsum(max(value - target, 0.0) for value in _SHAPE_RETURNS)
    losses = math.fsum(max(target - value, 0.0) for value in _SHAPE_RETURNS)
    assert omega_ratio(_SHAPE_RETURNS, 252.0, annual_target_return=0.05) == pytest.approx(gains / losses, rel=1e-12)


@pytest.mark.parametrize("returns", [[0.01, 0.02], [0.0, 0.0, 0.0], [0.01, 0.0]], ids=["only-gains", "flat", "gains-and-a-flat-day"])
def test_omega_is_undefined_exactly_when_the_sortino_is(returns):
    """No day below the threshold: nothing to divide by. One condition, so never a None beside a huge ratio."""
    assert omega_ratio(returns, 252.0) is None
    assert annualized_sortino(returns, 252.0) is None


def test_a_flat_day_is_not_a_positive_day():
    assert positive_observation_share([0.01, 0.0, -0.01, 0.02]) == pytest.approx(0.5)
    assert positive_observation_share([-0.01, 0.0]) == 0.0


def test_the_average_up_day_and_down_day_leave_the_flat_days_out():
    returns = [0.01, 0.0, -0.01, 0.02, -0.03]

    assert mean_positive_return(returns) == pytest.approx(0.015)
    assert mean_negative_return(returns) == pytest.approx(-0.02)
    assert mean_positive_return([-0.01, 0.0]) is None
    assert mean_negative_return([0.01, 0.0]) is None


def test_the_longest_positive_run_keeps_the_earliest_of_equal_runs_and_a_flat_day_breaks_it():
    run = longest_positive_run([0.01, 0.02, -0.01, 0.01, 0.01, 0.0, 0.03])

    assert (run.length, run.start_index, run.end_index) == (2, 0, 1)
    longer = longest_positive_run([-0.01, 0.01, 0.01, 0.01])
    assert (longer.length, longer.start_index, longer.end_index) == (3, 1, 3)
    assert longest_positive_run([-0.01, 0.0]) is None


def test_the_extreme_day_ratio_is_the_pearson_kurtosis_over_the_bell_curves_three():
    # ±1 % alternating: the second moment is 1e-4, the fourth 1e-8, so the kurtosis is exactly 1.
    assert extreme_day_ratio([0.01, -0.01, 0.01, -0.01]) == pytest.approx(1.0 / 3.0, rel=1e-12)
    assert extreme_day_ratio([0.01, 0.01, 0.01]) is None


def test_the_best_horizon_window_is_the_twin_of_the_worst():
    window = best_horizon_window([-0.0102, -0.02, 0.03, 0.03], 2)

    assert (window.compounded_return, window.start_index, window.end_index) == (0.03, 2, 3)
    assert best_horizon_window([], 2) is None
    with pytest.raises(ValueError):
        best_horizon_window([0.01], 0)


def test_the_largest_rally_climbs_from_the_lowest_point_before_its_peak():
    rally = largest_rally(wealth_index([-0.5, 1.0, -0.1, 0.5]))

    assert rally.gain == pytest.approx(1.7)
    assert (rally.trough_index, rally.peak_index) == (1, 4)
    # From the baseline: index 0 is the value before the first return.
    from_baseline = largest_rally(wealth_index([0.5, -1.0]))
    assert from_baseline.gain == pytest.approx(0.5)
    assert (from_baseline.trough_index, from_baseline.peak_index) == (0, 1)


@pytest.mark.parametrize("returns", [[-0.1, -0.1], [-1.0, 0.5], []], ids=["only-falls", "after-a-total-loss", "no-return"])
def test_no_rise_is_no_rally_a_zero_with_no_dates(returns):
    """The twin of ``no_drawdown``: nothing to climb from (a value of zero cannot be a trough)."""
    rally = largest_rally(wealth_index(returns))

    assert (rally.gain, rally.trough_index, rally.peak_index) == (0.0, None, None)


def test_the_best_day_is_the_twin_of_the_worst_and_keeps_the_earliest():
    assert best_realization([-0.01, 0.03, 0.03]) == 0.03
    assert best_realization_index([-0.01, 0.03, 0.03]) == 1
    with pytest.raises(ValueError):
        best_realization([])


def test_the_average_drawdown_is_the_mean_of_the_underwater_curve_over_the_returns():
    # The baseline point (always 0) is in the curve; the divisor is the number of returns, as for the Ulcer index.
    assert average_drawdown([0.0, -0.1, -0.2, 0.0]) == pytest.approx(-0.1)
    assert average_drawdown([0.0, 0.0]) == 0.0
    with pytest.raises(ValueError):
        average_drawdown([0.0])


def test_the_return_shape_bundles_the_same_functions_the_cards_read():
    returns = [0.01, 0.0, -0.01, 0.02, -0.03, 0.02, 0.02]
    shape = return_shape(returns, 252.0, annual_target_return=0.02)

    assert shape.best_realization == best_realization(returns)
    assert shape.best_realization_index == best_realization_index(returns)
    assert shape.positive_observation_share == positive_observation_share(returns)
    assert shape.mean_positive_return == mean_positive_return(returns)
    assert shape.mean_negative_return == mean_negative_return(returns)
    assert shape.longest_positive_run == longest_positive_run(returns)
    assert shape.omega_ratio == omega_ratio(returns, 252.0, annual_target_return=0.02)
    assert shape.downside_deviation == annualized_downside_deviation(returns, 252.0, annual_target_return=0.02)
    assert shape.extreme_day_ratio == extreme_day_ratio(returns)


def test_a_series_without_a_gain_has_no_best_day_in_its_shape():
    shape = return_shape([-0.01, 0.0, -0.02], 252.0)

    assert (shape.best_realization, shape.best_realization_index, shape.mean_positive_return, shape.longest_positive_run) == (None, None, None, None)
    assert shape.positive_observation_share == 0.0


# --------------------------------------------------------------------------- #
# RN-14 — the green tail: its threshold is the mirror of the VaR, and the histogram pins both cuts (consultant,
# 16/11/2026, option A): the bar width becomes the distance between the two cuts over the whole number of bars nearest
# to the Freedman-Diaconis width, so each tail is a whole number of bars. When that cannot hold — no Freedman-Diaconis
# width, no threshold above the VaR cut, or a grid past the bar ceiling — the grid is today's, pinned on the VaR alone.
# --------------------------------------------------------------------------- #


def test_the_gain_threshold_is_the_value_at_risk_of_the_mirrored_series():
    """One estimator for both tails: the same order statistic, read on the other side."""
    returns = [0.012, -0.004, 0.031, -0.022, 0.007, 0.018, -0.011, 0.026, -0.015, 0.003] * 4
    # 40 returns at 85 %: a tail of 6, so the 6th best gain — past the four 3.1 % days, the second 2.6 % day.
    mirrored = historical_var_cvar([-value for value in returns], confidence_level=0.85).value_at_risk

    assert gain_threshold(returns, confidence_level=0.85) == mirrored
    assert gain_threshold(returns, confidence_level=0.85) == pytest.approx(0.026)
    # The same zero floor as the VaR: a window with no gain has a threshold of zero, never a loss.
    assert gain_threshold([-0.01, -0.02, -0.005], confidence_level=0.9) == 0.0


def _pin_sample() -> list[float]:
    return [0.011 * math.sin(index * 0.77) + 0.0004 * (index % 7) - 0.001 for index in range(400)]


def test_both_cuts_land_exactly_on_a_bar_edge_of_a_uniform_grid():
    sample = _pin_sample()
    var_edge = -historical_var_cvar(sample, confidence_level=0.95).value_at_risk
    green = gain_threshold(sample, confidence_level=0.95)

    histogram = return_distribution_histogram(sample, pinned_edge=var_edge, gain_edge=green)
    widths = [upper - lower for lower, upper in zip(histogram.edges, histogram.edges[1:], strict=False)]

    assert var_edge in histogram.edges and green in histogram.edges
    assert histogram.gain_edge == green
    assert max(widths) - min(widths) < 1e-12
    # Between the two cuts sits a whole number of bars, the one nearest to the Freedman-Diaconis width.
    plain = return_distribution_histogram(sample, pinned_edge=var_edge)
    plain_width = plain.edges[1] - plain.edges[0]
    bars_between = round((green - var_edge) / widths[0])
    assert bars_between == max(1, round((green - var_edge) / plain_width))
    assert sum(histogram.counts) == len(sample)


def test_two_cuts_closer_than_one_bar_still_get_one_bar_between_them():
    sample = _pin_sample()
    histogram = return_distribution_histogram(sample, pinned_edge=-0.0004, gain_edge=0.0003)

    assert -0.0004 in histogram.edges and 0.0003 in histogram.edges
    assert histogram.edges.index(0.0003) - histogram.edges.index(-0.0004) >= 1
    assert len(histogram.counts) <= 200


@pytest.mark.parametrize(
    ("sample", "var_edge", "green"),
    [
        pytest.param([0.0] * 30 + [0.01, -0.01, 0.02], -0.01, 0.01, id="no-freedman-diaconis-width"),
        pytest.param(_pin_sample(), -0.01, -0.01, id="threshold-not-above-the-var-cut"),
        pytest.param(_pin_sample(), -0.010, -0.010 + 1e-9, id="one-bar-would-break-the-ceiling"),
    ],
)
def test_the_grid_falls_back_to_the_var_pin_alone_and_names_the_first_bar_of_the_green_tail(sample, var_edge, green):
    histogram = return_distribution_histogram(sample, pinned_edge=var_edge, gain_edge=green)
    today = return_distribution_histogram(sample, pinned_edge=var_edge)

    assert histogram.edges == today.edges
    assert histogram.counts == today.counts
    # The green tail starts at the first edge at or past its threshold: whole bars only, never half a bar.
    assert histogram.gain_edge == min(edge for edge in histogram.edges if edge >= green)
    assert len(histogram.counts) <= 200


def test_without_a_gain_edge_the_histogram_is_exactly_today():
    sample = _pin_sample()
    histogram = return_distribution_histogram(sample, pinned_edge=-0.01)

    assert histogram.gain_edge is None


def test_a_window_without_a_gain_pins_the_green_tail_at_zero_with_no_bar_in_it():
    """The threshold's zero floor sits above every return: the grid reaches it, and the bars past the data are empty.

    The same picture the VaR's floor already draws on a series of pure gains: what is reported, not a defect.
    """
    falling = [-0.001 - 0.004 * abs(math.sin(index * 0.9)) for index in range(120)]
    var_edge = -historical_var_cvar(falling, confidence_level=0.95).value_at_risk
    green = gain_threshold(falling, confidence_level=0.95)
    histogram = return_distribution_histogram(falling, pinned_edge=var_edge, gain_edge=green)

    assert green == 0.0
    assert histogram.gain_edge == 0.0 and 0.0 in histogram.edges
    assert histogram.edges[-1] >= 0.0
    green_bars = [count for lower, count in zip(histogram.edges, histogram.counts, strict=False) if lower >= 0.0]
    assert sum(green_bars) == 0
    assert sum(histogram.counts) == len(falling)
