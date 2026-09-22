"""Independent-reference oracle for LibreFolio's hand-written risk mathematics.

This module pins :mod:`backend.app.services.risk.metrics` against references that
share none of its code: riskfolio-lib, NumPy and SciPy. It exists so the planned
migration of ``metrics.py`` from pure-Python ``math.fsum`` loops to NumPy cannot
silently change a published number. The assertions are about **values and
semantics**, never about implementation, so the whole file must survive a rewrite
of every function body it covers.

⚠️ ARCHITECTURAL BOUNDARY — riskfolio is imported HERE and ONLY here.
``LibreFolio_devWiki/wiki/decisions/risk-quant-engine-process-boundary.md`` forbids
the FastAPI web process from importing riskfolio or QuantLib: those engines run in
isolated spawn workers. This is a test-only oracle. **Never move an import from
this file into ``metrics.py`` or anything it reaches** — doing so drags a ~340 MB
native dependency into the web process and breaks the decision.

Isolation: PURE. No database, no server, no network, no filesystem. Every sample
is drawn from a fixed ``np.random.default_rng`` seed, so every number below is
reproducible.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
import riskfolio.src.RiskFunctions as rk
from pydantic import ValidationError
from riskfolio.src.AuxFunctions import numBins
from scipy.stats import kurtosis as scipy_excess_kurtosis

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio import DataQualityReport
from backend.app.schemas.risk import RiskKpiOutput, RiskMode, RiskReturnBasis, RiskScopeKind
from backend.app.schemas.signals import SignalWarningCode
from backend.app.services.risk.base import RiskExecutionContext
from backend.app.services.risk.metrics import (
    ZERO_TOLERANCE,
    ReturnHistogram,
    annualized_sharpe,
    annualized_sortino,
    annualized_volatility,
    beta,
    compounded_return,
    correlation_matrix,
    covariance_matrix,
    daily_risk_free_rate,
    drawdown_episodes,
    historical_var_cvar,
    pairwise_correlation,
    pairwise_correlation_matrix,
    pearson_correlation,
    return_distribution_histogram,
    risk_contributions_from_covariance,
    sample_covariance,
    sample_standard_deviation,
    sample_variance,
    summarize_drawdown,
    wealth_index,
)
from backend.app.services.risk.signal_helpers import (
    rolling_annualized_sharpe_values,
    rolling_annualized_volatility_values,
    rolling_beta_values,
    rolling_compounded_return_values,
    rolling_pair_values,
    rolling_single_values,
    undefined_window_warnings,
)
from backend.app.services.risk_plugins.historical_var import (
    HistoricalVarAnalytic,
    HistoricalVarParams,
)

# --------------------------------------------------------------------------- #
# Deterministic sample builders
# --------------------------------------------------------------------------- #

_SEED = 42
_SAMPLE_SIZE = 750
_ANNUALIZATION = 252.0
_CONFIDENCE_LEVEL = 0.95
# riskfolio's ``alpha`` is the TAIL probability, not the confidence level.
#
# ⚠️ Written as ``1.0 - _CONFIDENCE_LEVEL`` this is 0.050000000000000044, and that is
# not a cosmetic difference: riskfolio multiplies alpha by T and takes a ``ceil``, so
# at T = 740 it reads 37.00000000000003 and climbs to the 38th worst loss — the exact
# off-by-one M2 exists to remove. Handed the subtracted value, **the oracle reproduces
# the defect it is supposed to arbitrate**. Spell the tail probability exactly.
_TAIL_ALPHA = 0.05
_BASELINE = date(2020, 1, 1)


def _daily_returns() -> list[float]:
    """Return the canonical seeded daily-return sample every reference was measured on."""
    generator = np.random.default_rng(_SEED)
    return [float(value) for value in generator.normal(0.0004, 0.011, _SAMPLE_SIZE)]


def _column(sample: Sequence[float]) -> np.ndarray:
    """Return the 2-D single-column layout riskfolio's risk functions require."""
    return np.asarray(sample, dtype=float).reshape(-1, 1)


def _observation_dates(count: int) -> list[date]:
    """Return strictly increasing observation dates after :data:`_BASELINE`."""
    return [_BASELINE + timedelta(days=index + 1) for index in range(count)]


def _multi_series(count: int = 5, observations: int = 260) -> list[list[float]]:
    """Return several return series sharing one common observation calendar."""
    generator = np.random.default_rng(2024)
    return [[float(value) for value in row] for row in generator.normal(0.0003, 0.010, size=(count, observations))]


def _correlated_pair() -> tuple[list[float], list[float]]:
    """Return an (asset, benchmark) pair with a known, non-degenerate beta."""
    benchmark = np.random.default_rng(7).normal(0.0003, 0.009, 300)
    asset = 0.8 * benchmark + np.random.default_rng(8).normal(0.0, 0.004, 300)
    return [float(value) for value in asset], [float(value) for value in benchmark]


# --------------------------------------------------------------------------- #
# Sample identity guard
# --------------------------------------------------------------------------- #


def test_the_seeded_oracle_sample_is_the_one_every_reference_value_was_measured_on():
    """Guard the sample builder: the literal constants below depend on this exact draw.

    Several tests in this file quote measured magnitudes (the riskfolio kurtosis,
    the Freedman-Diaconis bin count, the sign of the Sortino divergence). They are
    only meaningful for this seed, size, location and scale, so changing the builder
    must fail HERE and loudly rather than silently elsewhere.
    """
    returns = _daily_returns()

    assert len(returns) == _SAMPLE_SIZE
    assert sample_standard_deviation(returns) == pytest.approx(0.01083137396364685, rel=1e-12)
    assert math.fsum(returns) / len(returns) == pytest.approx(-9.857022404440485e-05, rel=1e-9)
    # Excess kurtosis is affine-invariant, so it identifies the underlying draw shape.
    assert float(scipy_excess_kurtosis(np.asarray(returns), fisher=True)) == pytest.approx(-0.074997379363833, rel=1e-9)


# --------------------------------------------------------------------------- #
# Block (a) — Case A: functions that already agree with the reference.
#
# These are the real safety net for the migration. They are asserted with an
# explicit tight tolerance and must stay green through every step of it. A red
# here means a published number moved.
# --------------------------------------------------------------------------- #


def test_annualized_sharpe_matches_riskfolio_per_period_sharpe_scaled_by_the_annualization_root():
    """Ours equals riskfolio's per-period Sharpe times sqrt(factor), to 1e-9 relative.

    ``annualized_sharpe`` subtracts ``daily_risk_free_rate(0.0, factor)``, which is
    exactly ``0.0`` for every positive factor, and divides by the ddof=1 sample
    deviation — which is what riskfolio's ``rm="MV"`` risk measure computes for a
    single column.
    """
    returns = _daily_returns()
    reference = float(rk.Sharpe(_column(returns), rf=0, alpha=_TAIL_ALPHA, rm="MV")) * math.sqrt(_ANNUALIZATION)

    assert annualized_sharpe(returns, _ANNUALIZATION) == pytest.approx(reference, rel=1e-9)


def test_sample_standard_deviation_and_annualized_volatility_match_numpy_with_one_degree_of_freedom():
    """Both scalar dispersion functions use the unbiased (ddof=1) convention."""
    returns = _daily_returns()
    array = np.asarray(returns, dtype=float)

    assert sample_standard_deviation(returns) == pytest.approx(float(np.std(array, ddof=1)), rel=1e-12)
    assert sample_variance(returns) == pytest.approx(float(np.var(array, ddof=1)), rel=1e-12)
    assert annualized_volatility(returns, _ANNUALIZATION) == pytest.approx(float(np.std(array, ddof=1)) * math.sqrt(_ANNUALIZATION), rel=1e-12)


def test_covariance_and_correlation_matrices_match_numpy_covariance_and_correlation():
    """The matrix builders reproduce ``np.cov(ddof=1)`` and ``np.corrcoef`` entry by entry."""
    rows = _multi_series()
    array = np.asarray(rows, dtype=float)
    covariance = covariance_matrix(rows)
    correlation = correlation_matrix(rows)
    reference_covariance = np.cov(array, ddof=1)
    reference_correlation = np.corrcoef(array)

    for index, row in enumerate(covariance):
        assert row == pytest.approx(list(reference_covariance[index]), rel=1e-12)
    for index, row in enumerate(correlation):
        assert row == pytest.approx(list(reference_correlation[index]), abs=1e-12)


def test_pearson_correlation_and_beta_match_numpy_with_the_unbiased_variance_convention():
    """Beta is ddof=1 covariance over ddof=1 benchmark variance, as the source computes it."""
    asset, benchmark = _correlated_pair()
    asset_array = np.asarray(asset, dtype=float)
    benchmark_array = np.asarray(benchmark, dtype=float)

    assert pearson_correlation(asset, benchmark) == pytest.approx(float(np.corrcoef(asset_array, benchmark_array)[0, 1]), abs=1e-12)
    reference_beta = float(np.cov(asset_array, benchmark_array, ddof=1)[0, 1] / np.var(benchmark_array, ddof=1))
    assert beta(asset, benchmark) == pytest.approx(reference_beta, rel=1e-12)


def test_wealth_index_and_compounded_return_match_an_independent_scalar_accumulation():
    """The wealth grid carries the pre-return baseline and compounds exactly once per observation.

    THE REFERENCE IS DELIBERATELY NOT ``np.cumprod``. ``wealth_index`` is itself
    implemented on ``np.cumprod``, so a NumPy reference would compare the library
    against itself and hold no matter what the source did — it would pass a source
    that dropped the baseline, or one that compounded the wrong direction, as long as
    it kept calling the same primitive. The reference below is a plain Python
    accumulation: the textbook definition of a wealth index, and the exact semantics
    the source carried before M6 vectorized it. KEEP IT SCALAR.
    """
    returns = _daily_returns()
    reference_wealth = [1.0]
    for value in returns:
        reference_wealth.append(reference_wealth[-1] * (1.0 + value))

    index = wealth_index(returns)

    assert len(index) == len(returns) + 1
    assert index[0] == 1.0
    # EXACT, not approximate. ``np.cumprod`` is a sequential scan, so it performs the
    # same multiplications in the same order as the accumulation above and re-associates
    # nothing; the vectorized source is bit-identical to the scalar definition rather
    # than merely close to it. A tolerance here would hide a real drift if that ever
    # stopped being true.
    assert index == reference_wealth
    # ``compounded_return`` is NOT vectorized — it keeps its own scalar loop — so
    # ``np.prod`` remains an independent cross-check of the same compounding.
    assert compounded_return(returns) == pytest.approx(float(np.prod(np.asarray(returns, dtype=float) + 1.0) - 1.0), rel=1e-12)


def test_risk_contributions_match_a_direct_numpy_euler_decomposition_of_portfolio_volatility():
    """MCTR/CCTR/PCTR mirror the source's own definition, expressed in NumPy.

    Source semantics: the covariance is scaled by the annualization factor first,
    ``marginal = (Sigma w) / sigma``, ``component = w * marginal`` and
    ``percentage = component / sigma`` (so the percentages sum to one).
    """
    rows = _multi_series(count=4)
    covariance = covariance_matrix(rows)
    weights = [0.4, 0.3, 0.2, 0.1]
    summary = risk_contributions_from_covariance(covariance, weights, annualization_factor=_ANNUALIZATION)

    annual = np.asarray(covariance, dtype=float) * _ANNUALIZATION
    weight_array = np.asarray(weights, dtype=float)
    sigma_weights = annual @ weight_array
    volatility = math.sqrt(float(weight_array @ sigma_weights))

    assert summary.portfolio_volatility == pytest.approx(volatility, rel=1e-12)
    assert list(summary.marginal) == pytest.approx(list(sigma_weights / volatility), rel=1e-12)
    assert list(summary.component) == pytest.approx(list(weight_array * (sigma_weights / volatility)), rel=1e-12)
    assert list(summary.percentage) == pytest.approx(list(weight_array * (sigma_weights / volatility) / volatility), rel=1e-12)
    assert math.fsum(summary.percentage) == pytest.approx(1.0, rel=1e-12)


# --------------------------------------------------------------------------- #
# Block (b) — Case B: composites the oracle WATCHES but does not replace.
# --------------------------------------------------------------------------- #


def test_summarize_drawdown_matches_riskfolio_relative_maximum_drawdown():
    """Our max drawdown is riskfolio's RELATIVE (compounded) drawdown, negated."""
    returns = _daily_returns()
    reference = -float(rk.MDD_Rel(_column(returns)))

    assert summarize_drawdown(returns).max_drawdown == pytest.approx(reference, rel=1e-12)


def test_drawdown_episodes_report_the_same_relative_maximum_drawdown_as_riskfolio():
    """The dated episode state machine reports the same depth as the undated summary."""
    returns = _daily_returns()
    reference = -float(rk.MDD_Rel(_column(returns)))
    report = drawdown_episodes(returns, dates=_observation_dates(len(returns)), baseline_date=_BASELINE)

    assert report.maximum_drawdown == pytest.approx(reference, rel=1e-12)
    assert report.maximum_drawdown == pytest.approx(summarize_drawdown(returns).max_drawdown, rel=1e-12)
    assert report.n_observations == len(returns)


def test_historical_var_cvar_matches_the_coherent_estimator_after_m2():
    """M2 landed: our tail risk now IS riskfolio's, to machine precision.

    This test replaces ``..._currently_diverges_from_the_coherent_estimator``, which
    pinned the pre-M2 plug-in estimator and went red the moment the migration landed —
    which is exactly what it was written to do.

    ``historical_var_cvar`` now uses Acerbi-Tasche / Rockafellar-Uryasev: with losses
    sorted worst-first and a nominal tail of ``m = (1 - confidence) * T`` observations,
    the boundary observation is counted for the *fraction* of it that falls inside the
    tail. The old estimator counted it whole, and because it is the smallest loss in
    the tail that dragged the average down by a measured -0.27 %, on 2000 samples out
    of 2000.

    The zero floor is deliberately KEPT: ``backend/app/schemas/risk.py`` declares both
    fields ``Field(..., ge=0)``, so these are loss magnitudes, never signed returns.
    At the usual confidence levels it never binds on the tail.
    """
    returns = _daily_returns()
    column = _column(returns)
    tail = historical_var_cvar(returns, confidence_level=_CONFIDENCE_LEVEL)

    assert tail.conditional_value_at_risk == pytest.approx(float(rk.CVaR_Hist(column, alpha=_TAIL_ALPHA)), abs=1e-15)
    assert tail.value_at_risk == pytest.approx(float(rk.VaR_Hist(column, alpha=_TAIL_ALPHA)), abs=1e-15)

    # Re-derive the coherent estimator here rather than trusting the library twice.
    losses = np.sort(np.maximum(-np.asarray(returns, dtype=float), 0.0))[::-1]
    nominal = (1.0 - _CONFIDENCE_LEVEL) * len(losses)
    whole = math.floor(nominal)
    expected_cvar = (math.fsum(losses[:whole].tolist()) + (nominal - whole) * losses[whole]) / nominal
    assert tail.conditional_value_at_risk == pytest.approx(expected_cvar, rel=1e-12)

    # The two hand-checkable cases, now answering what riskfolio answers.
    five_day = historical_var_cvar([-0.1, -0.05, 0.0, 0.02, 0.03], confidence_level=0.8)
    assert five_day.value_at_risk == pytest.approx(0.10)
    assert five_day.conditional_value_at_risk == pytest.approx(0.10)

    two_day = historical_var_cvar([-0.1, 0.0, -0.2], confidence_level=0.5, horizon_days=2)
    assert two_day.value_at_risk == pytest.approx(0.20)
    assert two_day.conditional_value_at_risk == pytest.approx(0.20)

    for result in (tail, five_day, two_day):
        assert result.conditional_value_at_risk >= result.value_at_risk >= 0


@pytest.mark.parametrize("observations", [740, 760, 800, 1000])
def test_historical_var_survives_the_float_that_reinstates_the_off_by_one(observations):
    """Guard the integer-``alpha*T`` case, where the fix is right in exact arithmetic
    and was wrong in floating point.

    ``1.0 - 0.95`` is ``0.050000000000000044``, so at T = 740 the nominal tail is
    computed as ``37.00000000000003`` and ``ceil`` climbs to 38 — silently
    reinstating the very off-by-one M2 exists to remove. CVaR barely notices, because
    the boundary weight is ~3e-14; VaR is a *step function* of that index, so it moves
    by a whole order statistic: measured -1.31e-04 at T = 740 before the snap.

    riskfolio arbitrates this ONLY when handed the exact tail probability — see the
    note on ``_TAIL_ALPHA``. Fed the subtracted value it lands on the same wrong index,
    which is how this test failed on its first run.
    """
    returns = list(np.random.default_rng(observations).normal(0.0004, 0.011, observations))
    column = _column(returns)
    tail = historical_var_cvar(returns, confidence_level=_CONFIDENCE_LEVEL)

    # The artefact itself, demonstrated rather than described.
    assert 1.0 - _CONFIDENCE_LEVEL != _TAIL_ALPHA
    assert math.ceil((1.0 - _CONFIDENCE_LEVEL) * observations) > math.ceil(_TAIL_ALPHA * observations)

    assert tail.value_at_risk == pytest.approx(float(rk.VaR_Hist(column, alpha=_TAIL_ALPHA)), abs=1e-15)
    assert tail.conditional_value_at_risk == pytest.approx(float(rk.CVaR_Hist(column, alpha=_TAIL_ALPHA)), abs=1e-15)


def test_historical_tail_risk_horizon_returns_compound_the_requested_observation_window():
    """``horizon_returns`` is the signed, overlapping, compounded series — not the floored losses."""
    returns = _daily_returns()
    horizon = 5
    tail = historical_var_cvar(returns, confidence_level=_CONFIDENCE_LEVEL, horizon_days=horizon)
    array = np.asarray(returns, dtype=float)
    reference = [float(np.prod(1.0 + array[start : start + horizon]) - 1.0) for start in range(len(array) - horizon + 1)]

    assert len(tail.horizon_returns) == len(returns) - horizon + 1
    assert list(tail.horizon_returns) == pytest.approx(reference, rel=1e-12)
    assert min(tail.horizon_returns) < 0.0  # signed, so the floor lives in VaR/CVaR only


# --------------------------------------------------------------------------- #
# Block (c) — the four name/magnitude traps.
#
# Each test FAILS if a future migration substitutes the similarly named riskfolio
# function whose definition differs. They are the reason this oracle can be trusted
# as a reference at all.
# --------------------------------------------------------------------------- #


def test_absolute_maximum_drawdown_is_not_the_relative_maximum_drawdown_we_report():
    """``MDD_Abs`` walks the uncompounded sum path; we report ``MDD_Rel``.

    The gap between the two is data-dependent, so this asserts a clear separation,
    never a ratio: quoting a magnitude here would make the test a seed artefact.
    """
    returns = _daily_returns()
    column = _column(returns)
    absolute = float(rk.MDD_Abs(column))
    relative = float(rk.MDD_Rel(column))
    ours = summarize_drawdown(returns).max_drawdown

    assert ours == pytest.approx(-relative, rel=1e-12)
    assert abs(absolute - relative) > 1e-3
    assert ours != pytest.approx(-absolute, rel=1e-6)


def test_riskfolio_kurtosis_is_the_fourth_root_moment_and_not_scipy_excess_kurtosis():
    """``rk.Kurtosis`` is ``sqrt(E[(r - mean)^4])``: not excess, not standardised.

    It carries the units of a squared return, so it is roughly 1e-4 here, while
    SciPy's Fisher kurtosis is a dimensionless shape number near zero. Substituting
    one for the other would be a silent unit error, not a rounding difference.
    """
    returns = _daily_returns()
    array = np.asarray(returns, dtype=float)
    riskfolio_value = float(rk.Kurtosis(_column(returns)))
    fourth_root_moment = float(np.sqrt(np.mean((array - array.mean()) ** 4)))
    excess = float(scipy_excess_kurtosis(array, fisher=True))

    assert riskfolio_value == pytest.approx(fourth_root_moment, rel=1e-12)
    assert riskfolio_value == pytest.approx(0.00020038, rel=1e-4)
    assert excess == pytest.approx(-0.0750, rel=1e-3)
    assert abs(riskfolio_value - excess) > 0.01


def test_sortino_is_not_the_mean_over_riskfolio_semideviation():
    """Our Sortino uses a POPULATION downside deviation against an explicit MAR.

    ``annualized_sortino`` divides by ``sqrt(mean(min(r - MAR, 0)^2))`` — a one-sided
    dispersion around the minimum acceptable return, with the full sample in the
    denominator. ``rk.SemiDeviation`` divides by ``n - 1`` and measures dispersion
    around the portfolio's OWN sample mean, so it answers a different question: not
    "how far short of the target did this fall?" but "how uneven was it around whatever
    it happened to return?".

    ⚠️ The separation asserted below is SMALL, and that smallness is a property of THIS
    sample, not a measure of the hazard. The seeded series has a mean sitting close to
    the MAR, which is the one regime where the two statistics nearly coincide; all that
    is left between them there is the ``n`` versus ``n - 1`` divisor, worth
    ``sqrt(750/749)``. Quoting that millesimal next to the reference-point difference
    would suggest they are comparable quantities. They are not: the reference point is
    unbounded. The four tests that follow move the mean away from the MAR and reach a
    factor of three, and then a series on which ``rk.SemiDeviation`` is exactly zero and
    the substituted ratio has no finite value at all. The campaign-wide PROHIBITION on
    substituting ``rk.SemiDeviation`` for our downside deviation rests on those.
    """
    returns = _daily_returns()
    array = np.asarray(returns, dtype=float)
    minimum_acceptable = daily_risk_free_rate(0.0, _ANNUALIZATION)
    downside_deviation = float(np.sqrt(np.mean(np.minimum(array - minimum_acceptable, 0.0) ** 2)))
    expected = float(array.mean() - minimum_acceptable) / downside_deviation * math.sqrt(_ANNUALIZATION)
    naive = float(array.mean()) / float(rk.SemiDeviation(_column(returns))) * math.sqrt(_ANNUALIZATION)

    assert minimum_acceptable == 0.0
    assert annualized_sortino(returns, _ANNUALIZATION) == pytest.approx(expected, rel=1e-12)
    assert annualized_sortino(returns, _ANNUALIZATION) != pytest.approx(naive, rel=1e-4)
    assert abs(expected - naive) > 1e-4


# --------------------------------------------------------------------------- #
# Block (c-bis) — the SemiDeviation PROHIBITION, sized honestly.
#
# The campaign forbids substituting ``rk.SemiDeviation`` for LibreFolio's downside
# deviation anywhere. riskfolio computes
#
#     mu = np.mean(a, axis=0); value = mu - a
#     value = np.sum(np.power(value[np.where(value >= 0)], 2)) / (T - 1)
#
# so its reference point is the portfolio's OWN sample mean, while ours is an explicit
# minimum acceptable return. Two differences follow, and they are NOT the same size:
#
#   * the divisor, ``T`` versus ``T - 1``: a fixed factor of sqrt(T / (T - 1)), 1.002
#     at T = 250. Millesimal, and the only difference left when the mean sits on the MAR.
#   * the reference point: unbounded. It is zero when the series is constant, whatever
#     that constant is, and it grows with the distance between the mean and the MAR.
#
# The four tests below are ordered by how visible the damage is, ending with the one
# that is invisible. Every expectation is derived from NumPy or in closed form; none
# consults ``metrics.py`` for the number it then checks ``metrics.py`` against.
#
# Series are deterministic and carry no RNG at all, so the magnitudes quoted in the
# docstrings are exact and reproducible on any machine.
# --------------------------------------------------------------------------- #

_PROHIBITION_OBSERVATIONS = 250


def _steady_daily_change(daily: float) -> list[float]:
    """Return a constant series: the identical simple return on every observation."""
    return [daily] * _PROHIBITION_OBSERVATIONS


def _bleeding_returns() -> list[float]:
    """Return a series that loses 0.2% a day on average, alternating -0.1% / -0.3%.

    Deterministic on purpose: mean, downside deviation and semideviation all have
    closed forms, so nothing below is a seed artefact.
    """
    return [-0.001, -0.003] * (_PROHIBITION_OBSERVATIONS // 2)


def _mar_centred_returns() -> list[float]:
    """Return a +/-0.9% swing around a +0.02%/day drift: a series centred on the MAR."""
    return [0.0092, -0.0088] * (_PROHIBITION_OBSERVATIONS // 2)


def _symmetric_returns(swing: float = 0.009) -> list[float]:
    """Return a perfectly symmetric +/-``swing`` series whose sample mean is exactly zero."""
    return [swing, -swing] * (_PROHIBITION_OBSERVATIONS // 2)


def _downside_deviation_against_mar(sample: Sequence[float], minimum_acceptable: float = 0.0) -> float:
    """Return OUR statistic, re-derived in NumPy: RMS shortfall below an explicit MAR, over T."""
    array = np.asarray(sample, dtype=float)
    return float(np.sqrt(np.mean(np.minimum(array - minimum_acceptable, 0.0) ** 2)))


def _semideviation_around_the_sample_mean(sample: Sequence[float]) -> float:
    """Return RISKFOLIO's statistic, re-derived in NumPy: RMS deviation below the sample MEAN, over T - 1."""
    array = np.asarray(sample, dtype=float)
    below = array[array <= array.mean()] - array.mean()
    return float(np.sqrt(np.sum(below**2) / (array.size - 1)))


def _sortino_with_semideviation_substituted(sample: Sequence[float]) -> float:
    """Return the PROHIBITED form: annualized mean over ``rk.SemiDeviation``.

    Raises ``ZeroDivisionError`` when the substituted denominator vanishes, which is
    exactly what the free-fall test below pins.
    """
    array = np.asarray(sample, dtype=float)
    return float(array.mean()) / float(rk.SemiDeviation(_column(sample))) * math.sqrt(_ANNUALIZATION)


def test_riskfolio_semideviation_is_exactly_zero_for_both_the_best_and_the_worst_constant_series():
    """A constant series never deviates from its own mean, whatever that mean is.

    So ``rk.SemiDeviation`` scores a portfolio that loses 0.5% on every one of 250 days
    EXACTLY the same as one that gains 0.5% every day: ``0.0``, bit for bit. It cannot
    tell the worst series in this file from the best, because it was never asked about a
    target — only about evenness.

    Our downside deviation is measured against an explicit MAR, so it separates them by
    the full loss magnitude: ``0.005`` against ``0.0``. That gap is the reference point,
    and no divisor correction reaches it.
    """
    daily_loss = -0.005
    losing = _steady_daily_change(daily_loss)
    gaining = _steady_daily_change(-daily_loss)

    # The zero below is a theorem about the statistic, but reading it out of floating
    # point needs ``np.mean`` to return the constant bit for bit — which is true for
    # this constant at this length, and not universally. Assert the precondition, so a
    # future NumPy summation change fails HERE, legibly, instead of at the `== 0.0`.
    assert float(np.mean(np.asarray(losing, dtype=float))) == daily_loss
    assert float(np.mean(np.asarray(gaining, dtype=float))) == -daily_loss

    assert float(rk.SemiDeviation(_column(losing))) == 0.0
    assert float(rk.SemiDeviation(_column(gaining))) == 0.0
    assert float(rk.SemiDeviation(_column(losing))) == float(rk.SemiDeviation(_column(gaining)))
    # The NumPy re-derivation agrees bit for bit, so the zero is riskfolio's definition
    # and not an artefact of how riskfolio happens to sum.
    assert _semideviation_around_the_sample_mean(losing) == 0.0
    assert _semideviation_around_the_sample_mean(gaining) == 0.0

    minimum_acceptable = daily_risk_free_rate(0.0, _ANNUALIZATION)
    assert minimum_acceptable == 0.0
    assert _downside_deviation_against_mar(losing) == pytest.approx(-daily_loss, rel=1e-9, abs=1e-12)
    assert _downside_deviation_against_mar(gaining) == 0.0
    assert _downside_deviation_against_mar(losing) > _downside_deviation_against_mar(gaining)

    # And the consequence in the published figure: ours reports a number for the falling
    # series and ``None`` for the rising one, which is the correct way round. A
    # substitution inverts that — see the next test.
    assert annualized_sortino(losing, _ANNUALIZATION) is not None
    assert annualized_sortino(gaining, _ANNUALIZATION) is None


def test_substituting_semideviation_leaves_a_free_falling_portfolio_with_no_finite_sortino_at_all():
    """Ours reports -sqrt(252) = -15.87. The substitution has no value to report.

    The expectation is a CLOSED FORM, not a measurement: on a constant series the excess
    mean and the downside deviation are the same magnitude with opposite signs, so the
    ratio is exactly -1 and the annualized Sortino is exactly ``-sqrt(252)``. Nothing in
    ``metrics.py`` is consulted to obtain it.

    The prohibited form divides by zero. Which of its three faces you get depends only on
    where the substitution is made, and none of them is the truth:

      * a plain-float expression raises ``ZeroDivisionError``;
      * the NumPy form yields ``-inf`` — note it is MINUS infinity, because the negative
        sample mean carries its sign through the division, and ``RiskKpiOutput.sortino``
        is a ``FiniteFloat``, so the whole KPI payload is then rejected at the API
        boundary rather than reporting -15.87;
      * a substitution that kept the existing zero guard returns ``None`` — "no Sortino
        available" — for the worst-behaved series in this file.

    Only the rising constant series divides into ``+inf``, and there an unbounded Sortino
    is at least arguable: that portfolio never once fell below the MAR.
    """
    losing = _steady_daily_change(-0.005)
    expected = -math.sqrt(_ANNUALIZATION)

    assert annualized_sortino(losing, _ANNUALIZATION) == pytest.approx(expected, rel=1e-9, abs=1e-12)
    assert annualized_sortino(losing, _ANNUALIZATION) < -15.0
    assert RiskKpiOutput(volatility=0.0, max_drawdown=-1 + math.exp(-1.25), max_drawdown_duration_days=250, sortino=expected).sortino == pytest.approx(expected, rel=1e-9, abs=1e-12)

    # Face 1: the expression raises rather than returning anything.
    with pytest.raises(ZeroDivisionError):
        _sortino_with_semideviation_substituted(losing)

    # Face 2: under NumPy semantics it is -inf, and the contract refuses to publish it.
    with np.errstate(divide="ignore", invalid="ignore"):
        displayed = float(np.float64(float(np.mean(losing))) / np.float64(float(rk.SemiDeviation(_column(losing)))))
    assert math.isinf(displayed)
    assert displayed < 0
    with pytest.raises(ValidationError, match="finite number"):
        RiskKpiOutput(volatility=0.0, max_drawdown=-1 + math.exp(-1.25), max_drawdown_duration_days=250, sortino=displayed)

    # Face 3: the zero guard that ``annualized_sortino`` already carries would fire on
    # the substituted denominator, turning a catastrophe into a blank cell.
    assert math.isclose(float(rk.SemiDeviation(_column(losing))), 0.0, rel_tol=0.0, abs_tol=ZERO_TOLERANCE)
    assert not math.isclose(_downside_deviation_against_mar(losing), 0.0, rel_tol=0.0, abs_tol=ZERO_TOLERANCE)


def test_substituting_semideviation_silently_triples_the_sortino_of_a_steadily_bleeding_portfolio():
    """The quiet case, and the one a human reviewer would never catch.

    A portfolio alternating -0.1% and -0.3% loses 0.2% a day. Its true Sortino is
    -14.1986; substituting ``rk.SemiDeviation`` reports -44.8100. No infinity, no
    exception, no ``None`` — a plausible-looking number, wrong by the ratio of the two
    denominators, which here is 3.1559.

    The direction is worth stating precisely, because the obvious guess is wrong. The
    substitution does not flatter this portfolio, it ALARMS about it: with a negative
    sample mean, riskfolio's threshold sits below zero, so its denominator is smaller
    than ours and the already-negative ratio is pushed further from zero. Measured over
    4000 random (drift, sigma) draws the substituted figure read better than the truth
    in 20 of them, by at most 3e-5 Sortino points — so the bias is effectively one-way,
    toward panic, and it would make a slow bleed read like a free fall.
    """
    bleeding = _bleeding_returns()
    array = np.asarray(bleeding, dtype=float)

    ours = _downside_deviation_against_mar(bleeding)
    theirs = float(rk.SemiDeviation(_column(bleeding)))
    assert theirs == pytest.approx(_semideviation_around_the_sample_mean(bleeding), rel=1e-9, abs=1e-12)

    # Closed forms, so the two denominators are pinned independently of NumPy as well.
    assert float(array.mean()) == pytest.approx(-0.002, rel=1e-9, abs=1e-12)
    assert ours == pytest.approx(math.sqrt((0.001**2 + 0.003**2) / 2.0), rel=1e-9, abs=1e-12)
    assert theirs == pytest.approx(math.sqrt(_PROHIBITION_OBSERVATIONS / 2 * 0.001**2 / (_PROHIBITION_OBSERVATIONS - 1)), rel=1e-9, abs=1e-12)

    expected = float(array.mean()) / ours * math.sqrt(_ANNUALIZATION)
    substituted = _sortino_with_semideviation_substituted(bleeding)

    assert annualized_sortino(bleeding, _ANNUALIZATION) == pytest.approx(expected, rel=1e-9, abs=1e-12)
    assert expected == pytest.approx(-14.198591, rel=1e-6)
    assert substituted == pytest.approx(-44.809999, rel=1e-6)

    # Nothing here is undefined: this is the failure mode that leaves no trace.
    assert math.isfinite(substituted)
    assert substituted < expected < 0
    assert abs(substituted) > 3.0 * abs(expected)
    # The whole error is the ratio of the denominators — no other term contributes.
    assert substituted == pytest.approx(expected * ours / theirs, rel=1e-9, abs=1e-12)


def test_semideviation_and_our_downside_deviation_differ_only_by_the_divisor_on_mar_centred_data():
    """Why a substitution survives review: on data centred at the MAR it is invisible.

    On a perfectly symmetric +/-0.9% series the two denominators differ by EXACTLY
    ``sqrt(T / (T - 1))`` — the whole reference-point difference has collapsed, because
    the sample mean IS the MAR — and the published Sortino is ``0.0`` from both, bit for
    bit. No assertion on the published number can see the substitution there.

    Nudge the drift to +0.02% a day and the two Sortinos are 0.5102 against 0.4979: a
    2.4% gap. A test written with any tolerance looser than that passes under
    substitution, which is exactly how the prohibited form reaches production.

    Read this closeness as the trap, not as reassurance: it is the regime where the two
    statistics agree, and it tells you nothing about the regimes in the three tests
    above, where they disagree by a factor of three and then by everything.
    """
    symmetric = _symmetric_returns()
    ours_symmetric = _downside_deviation_against_mar(symmetric)
    theirs_symmetric = float(rk.SemiDeviation(_column(symmetric)))
    divisor_ratio = math.sqrt(_PROHIBITION_OBSERVATIONS / (_PROHIBITION_OBSERVATIONS - 1))

    assert theirs_symmetric / ours_symmetric == pytest.approx(divisor_ratio, rel=1e-9, abs=1e-12)
    assert divisor_ratio == pytest.approx(1.002006, rel=1e-6)
    # Same sample mean, so the published figures are identical and the difference above
    # is completely hidden by the ratio.
    assert float(np.mean(np.asarray(symmetric, dtype=float))) == 0.0
    assert annualized_sortino(symmetric, _ANNUALIZATION) == 0.0
    assert _sortino_with_semideviation_substituted(symmetric) == 0.0

    centred = _mar_centred_returns()
    array = np.asarray(centred, dtype=float)
    ours = _downside_deviation_against_mar(centred)
    theirs = float(rk.SemiDeviation(_column(centred)))
    expected = float(array.mean()) / ours * math.sqrt(_ANNUALIZATION)
    substituted = _sortino_with_semideviation_substituted(centred)

    assert annualized_sortino(centred, _ANNUALIZATION) == pytest.approx(expected, rel=1e-9, abs=1e-12)
    assert theirs / ours == pytest.approx(1.0, rel=0.05)
    # The gap is real but tiny: big enough that the oracle's 1e-9 sees it, small enough
    # that a 10% tolerance does not. That inequality IS the trap, asserted both ways.
    assert abs(substituted - expected) > 1e-9 * abs(expected)
    assert abs(substituted - expected) < 0.10 * abs(expected)
    assert expected == pytest.approx(0.510226, rel=1e-6)
    assert substituted == pytest.approx(0.497889, rel=1e-6)


def test_riskfolio_numbins_is_not_the_freedman_diaconis_bin_count():
    """``numBins`` is an entropy-oriented heuristic in the sample SIZE alone.

    It cannot see the data, so it cannot be swapped for the Freedman-Diaconis rule,
    which is driven by the interquartile range. On this sample they disagree by 8 bins.
    """
    returns = _daily_returns()
    riskfolio_bins = int(numBins(len(returns)))
    freedman_diaconis_bins = len(np.histogram_bin_edges(np.asarray(returns, dtype=float), bins="fd")) - 1

    assert riskfolio_bins == 13
    assert freedman_diaconis_bins == 21
    assert riskfolio_bins != freedman_diaconis_bins


# --------------------------------------------------------------------------- #
# Block (d) — ``undefined_windows`` semantics.
#
# Load-bearing, and written BEFORE the rolling helpers are vectorised because it is
# the only thing that will catch a semantic regression there.
# ``backend/app/services/signal_service.py:845`` derives ``has_undefined_window``
# from this count and uses it to pick the RESULT STATUS (UNAVAILABLE / partial), not
# merely to emit a warning. Losing or inflating the count silently changes the API.
# --------------------------------------------------------------------------- #


def test_degenerate_metrics_return_none_and_never_nan():
    """The ``None`` convention is deliberate: it is what makes an undefined window countable.

    A ``nan`` would flow through arithmetic, serialise as a number and be indistinguishable
    from a computed value. The migration must keep returning ``None``.
    """
    flat = [0.0, 0.0, 0.0]

    assert annualized_sharpe(flat, _ANNUALIZATION) is None
    assert annualized_sortino(flat, _ANNUALIZATION) is None
    assert beta([0.01, -0.02, 0.03], flat) is None
    assert pearson_correlation([0.01, -0.02, 0.03], flat) is None

    value, observations, coverage = pairwise_correlation([1.0, None, None], [2.0, 2.0, None], expected_observations=3)
    assert value is None
    assert observations == 1
    assert coverage == pytest.approx(1.0 / 3.0)


def test_rolling_single_values_keep_the_baseline_alignment_and_never_count_warm_up_as_undefined():
    """The output leads with one ``None`` for the valuation baseline, and warm-up is free.

    ``len(values) == len(returns) + 1`` is the contract ``build_line_computation``
    relies on when it zips values against price points.
    """
    returns = [0.01, -0.02, 0.03, -0.01, 0.02, -0.03]
    window = 3
    values, undefined_windows = rolling_single_values(returns, window, lambda sample: annualized_sharpe(sample, _ANNUALIZATION))

    assert len(values) == len(returns) + 1
    assert values[0] is None
    # Positions 1..window-1 are warm-up: no full window exists yet.
    assert [value is None for value in values[1:window]] == [True] * (window - 1)
    assert all(value is not None for value in values[window:])
    assert undefined_windows == 0


def test_rolling_single_values_count_a_full_window_whose_metric_is_undefined():
    """Warm-up ``None`` and undefined ``None`` look identical in the list and must NOT be conflated.

    Here two windows are warm-up and two full windows are genuinely undefined (an
    all-zero window has zero sample deviation, so ``annualized_sharpe`` returns
    ``None``). The list holds five ``None`` entries — baseline, two warm-up, two
    undefined — while the count must be exactly two.
    """
    assert annualized_sharpe([0.0, 0.0, 0.0], _ANNUALIZATION) is None

    returns = [0.01, -0.02, 0.0, 0.0, 0.0, 0.0, 0.02]
    window = 3
    values, undefined_windows = rolling_single_values(returns, window, lambda sample: annualized_sharpe(sample, _ANNUALIZATION))

    assert len(values) == len(returns) + 1
    assert [value is None for value in values] == [True, True, True, False, False, True, True, False]
    assert undefined_windows == 2


def test_rolling_pair_values_apply_the_same_warm_up_and_undefined_contract_to_two_series():
    """The paired helper slices both series over the identical index range and counts the same way."""
    primary = [0.01, -0.02, 0.03, -0.01, 0.02, -0.03, 0.01]
    comparison = [0.02, -0.01, 0.0, 0.0, 0.0, 0.0, 0.015]
    window = 3
    seen: list[tuple[tuple[float, ...], tuple[float, ...]]] = []

    def _recording_metric(left: Sequence[float], right: Sequence[float]) -> float | None:
        seen.append((tuple(left), tuple(right)))
        return pearson_correlation(left, right)

    values, undefined_windows = rolling_pair_values(primary, comparison, window, _recording_metric)

    assert len(values) == len(primary) + 1
    assert [value is None for value in values] == [True, True, True, False, False, True, True, False]
    assert undefined_windows == 2
    # Both slices cover the same closed window, in order, with no drift.
    expected_slices = [(tuple(primary[end - window + 1 : end + 1]), tuple(comparison[end - window + 1 : end + 1])) for end in range(window - 1, len(primary))]
    assert seen == expected_slices


def test_rolling_pair_values_reject_series_that_are_not_on_one_joint_calendar():
    """A length mismatch is a programming error, not a silently truncated zip."""
    with pytest.raises(ValueError, match="aligned"):
        rolling_pair_values([0.01, 0.02, 0.03], [0.01, 0.02], 2, pearson_correlation)


def test_undefined_window_warnings_describe_the_count_and_stay_silent_at_zero():
    """The warning payload is the machine-readable half signal_service reads back."""
    assert undefined_window_warnings(0) == []

    warnings = undefined_window_warnings(3)
    assert len(warnings) == 1
    assert warnings[0].code == SignalWarningCode.UNDEFINED_METRIC_WINDOW
    assert warnings[0].details == {"undefined_windows": 3}


def test_pandas_rolling_cannot_distinguish_warm_up_from_undefined_windows():
    """Executable record of WHY the rolling helpers cannot be replaced by pandas naively.

    ``Series.rolling`` emits ``NaN`` for a warm-up cell and ``NaN`` for a cell whose
    statistic is undefined (here 0/0 over an all-zero window). The two are the same
    float, so the undefined count that drives ``SignalStatus`` cannot be recovered
    from the output. Our helper returns ``None`` in both places but counts only the
    second, which is the distinction that must be preserved by any vectorisation.
    """
    returns = [0.01, -0.02, 0.0, 0.0, 0.0, 0.0, 0.02]
    window = 3
    ratio = pd.Series(returns).rolling(window).mean() / pd.Series(returns).rolling(window).std(ddof=1)

    # Positions 0-1 are warm-up; positions 4-5 are mathematically undefined.
    assert ratio.isna().tolist() == [True, True, False, False, True, True, False]
    assert math.isnan(float(ratio.iloc[1]))
    assert math.isnan(float(ratio.iloc[4]))
    assert float(ratio.iloc[1]) != float(ratio.iloc[1])  # NaN != NaN: no identity to compare
    assert int(ratio.isna().sum()) == 4  # 2 warm-up + 2 undefined, indistinguishable

    # Our helper separates them: same data, same window, an exact undefined count.
    _, undefined_windows = rolling_single_values(returns, window, lambda sample: annualized_sharpe(sample, _ANNUALIZATION))
    assert undefined_windows == 2


# --------------------------------------------------------------------------- #
# Block (e) — internal consistency between the matrix and scalar paths.
#
# The migration moves the matrix bodies to NumPy while the scalar functions keep
# ``math.fsum``. Nothing else in the module prevents the two from drifting apart.
# --------------------------------------------------------------------------- #


def test_covariance_matrix_entries_equal_the_scalar_sample_covariance_path():
    """Every entry of the matrix is the scalar definition applied to the same two rows."""
    rows = _multi_series(count=4, observations=180)
    matrix = covariance_matrix(rows)

    assert len(matrix) == len(rows)
    for i, left in enumerate(rows):
        assert len(matrix[i]) == len(rows)
        for j, right in enumerate(rows):
            assert matrix[i][j] == pytest.approx(sample_covariance(left, right), rel=1e-12)


def test_correlation_matrix_entries_equal_the_scalar_pearson_correlation_path():
    """Every entry of the matrix is the scalar Pearson definition on the same two rows."""
    rows = _multi_series(count=4, observations=180)
    matrix = correlation_matrix(rows)

    assert len(matrix) == len(rows)
    for i, left in enumerate(rows):
        assert len(matrix[i]) == len(rows)
        for j, right in enumerate(rows):
            assert matrix[i][j] == pytest.approx(pearson_correlation(left, right), rel=1e-12)


def test_matrix_diagonals_and_symmetry_follow_the_scalar_definitions():
    """The covariance diagonal is the scalar variance; the correlation diagonal is unit.

    The correlation diagonal is ``cov(x, x) / (sd * sd)`` and ``sqrt(v) * sqrt(v)`` is
    not bit-identically ``v``, so it is 1.0 only to floating-point precision — the
    clamp in ``pearson_correlation`` caps above 1.0 but cannot lift it back to it.
    """
    rows = _multi_series(count=5, observations=180)
    covariance = covariance_matrix(rows)
    correlation = correlation_matrix(rows)

    for index, row in enumerate(rows):
        assert covariance[index][index] == pytest.approx(sample_variance(row), rel=1e-12)
        assert correlation[index][index] == pytest.approx(1.0, rel=1e-12)

    for i in range(len(rows)):
        for j in range(len(rows)):
            assert covariance[i][j] == pytest.approx(covariance[j][i], rel=1e-12)
            assert correlation[i][j] == pytest.approx(correlation[j][i], rel=1e-12)


# --------------------------------------------------------------------------- #
# Block (f) — ``return_distribution_histogram``: the VaR-pinned Freedman-Diaconis grid.
#
# Decision D21: the return-distribution chart must draw the VaR cut ON a bin edge, so
# the shaded loss area is exactly the tail probability instead of a bar sliced through
# its middle. The technique (project doc 06 §7.2) is to take the Freedman-Diaconis
# width and TRANSLATE the uniform grid until one edge lands on the cut. Every edge is
# then ``pinned + k * width``, the widths stay uniform, and the picture stays an
# honest density rather than a hand-tuned one.
#
# ⚠️ SIGN CONVENTION. ``returns`` here are SIGNED, so a loss is negative and sits on
# the left, while ``HistoricalTailRisk.value_at_risk`` is a POSITIVE loss magnitude
# (``backend/app/schemas/risk.py`` declares it ``ge=0``). The producer therefore pins
# at ``-value_at_risk``. Inverting that sign would shade the GAIN tail and still look
# entirely plausible on screen, which is why the tests below assert the sign of the
# pin rather than only its magnitude.
# --------------------------------------------------------------------------- #

# Mirrors the private ``_MAX_HISTOGRAM_BINS`` guard in ``metrics.py``. Kept as a
# literal rather than imported on purpose: raising that guard changes every clamped
# histogram the API publishes, and this oracle is supposed to go red when it moves.
_MAX_HISTOGRAM_BINS = 200


def _gain_only_series() -> list[float]:
    """Return a strictly positive ramp — the series that makes the VaR zero floor bite."""
    return [float(value) for value in np.linspace(0.0005, 0.0020, 400)]


def _clamp_stress_series() -> list[float]:
    """Return a sample extreme enough to force the bin-count clamp at any pin position.

    Freedman-Diaconis sizes the bin from the INTERQUARTILE range, so 600 observations
    clustered inside ±1e-6 set a microscopic width while two outliers at ±0.4 set a
    0.8-wide span. Unclamped the rule would ask for over 2.6 million bins, which is
    what makes this the right sample for testing a ceiling.
    """
    core = np.random.default_rng(7).normal(0.0, 1e-6, 600)
    return [float(value) for value in np.concatenate([core, [-0.4, 0.4]])]


def _observed_bin_width(histogram: ReturnHistogram) -> float:
    """Return the bin width read back off the published grid.

    This is ``edges[1] - edges[0]``, which is NOT bit-identical to the width the
    function computed internally: both edges are themselves ``pinned + k * width``, so
    the subtraction re-rounds. Measured worst case across this block: 2.3e-15 relative.
    Every comparison against this value therefore carries a relative tolerance.
    """
    return histogram.edges[1] - histogram.edges[0]


def _freedman_diaconis_width(sample: Sequence[float]) -> float:
    """Return the bin width ``np.histogram_bin_edges(..., bins='fd')`` lays down.

    NumPy rounds the textbook ``2 * IQR / n**(1/3)`` rule UP to a whole number of bins
    spanning ``[min, max]``, which rounds the width DOWN, so this is the realised
    spacing and not the raw rule. On the canonical sample the rule gives 0.003171 and
    the realised spacing is 0.003079.
    """
    return float(np.diff(np.histogram_bin_edges(np.asarray(sample, dtype=float), bins="fd")).max())


def _var_execution_context(returns: Sequence[float]) -> RiskExecutionContext:
    """Return the minimal DB-free context ``HistoricalVarAnalytic`` actually reads.

    ``require_primary_returns`` consumes only ``primary_return_dates`` and
    ``primary_returns``, so ``prepared_series`` stays ``None`` and nothing here touches
    a database, a server or a valuation series. That is what keeps the producer test
    inside this file's PURE isolation class.
    """
    dates = tuple(_observation_dates(len(returns)))
    return RiskExecutionContext(
        scope_kind=RiskScopeKind.ASSET,
        scope_reference="asset",
        requested_range=DateRangeModel(start=dates[0], end=dates[-1]),
        target_currency="EUR",
        mode=RiskMode.HISTORICAL,
        composition_policy=None,
        scope_asset_ids=(1,),
        prepared_series=None,
        primary_baseline_date=_BASELINE,
        primary_return_dates=dates,
        primary_returns=tuple(float(value) for value in returns),
        primary_return_basis=RiskReturnBasis.PRICE_ONLY,
        annualization_factor=_ANNUALIZATION,
        calendar_days=len(returns),
        coverage=1.0,
        data_quality=DataQualityReport(),
    )


def test_the_pinned_edge_is_always_exactly_one_of_the_published_edges():
    """The reason the function exists: the VaR cut IS an edge, never a point inside a bar.

    Asserted with exact equality on purpose. ``pytest.approx`` would happily accept a
    grid that merely lands near the cut, and a near miss is exactly the defect D21
    removes — the renderer shades whole bars, so an edge one ulp away from the VaR
    puts a slice of the tail in the wrong colour and misstates the shaded probability.
    """
    canonical = _daily_returns()
    tail = historical_var_cvar(canonical, confidence_level=_CONFIDENCE_LEVEL)
    gains = _gain_only_series()

    cases: list[tuple[Sequence[float], float]] = [
        (canonical, -tail.value_at_risk),
        (canonical, 0.0),
        (canonical, min(canonical)),
        (canonical, max(canonical)),
        (canonical, -0.5),  # pin far outside the observed range
        (gains, -historical_var_cvar(gains, confidence_level=_CONFIDENCE_LEVEL).value_at_risk),
        ([0.0123], -0.004),
        ([0.001] * 50, 0.0005),
        (_clamp_stress_series(), -0.0002),
    ]

    for sample, pinned in cases:
        histogram = return_distribution_histogram(sample, pinned_edge=pinned)
        assert min(abs(edge - pinned) for edge in histogram.edges) == 0.0
        assert histogram.pinned_edge == pinned


def test_every_edge_is_the_pinned_edge_plus_a_whole_number_of_bin_widths():
    """The grid is a translated lattice, so no edge can drift off it and stay uniform.

    Tolerance: the lattice index is recovered here as ``(edge - pinned) / width``,
    which costs one multiply-add inside the function and one divide here. The worst
    deviation measured across every sample in this block is 4.6e-14, while a genuinely
    off-lattice edge misses an integer by at least 0.5. 1e-9 therefore sits more than
    eight orders of magnitude below a real violation and four orders above the float
    noise, so it cannot be satisfied by an accident in either direction.
    """
    canonical = _daily_returns()
    tail = historical_var_cvar(canonical, confidence_level=_CONFIDENCE_LEVEL)

    for sample, pinned in ((canonical, -tail.value_at_risk), (canonical, max(canonical)), (_gain_only_series(), 0.0), (_multi_series(count=1, observations=200)[0], -0.01)):
        histogram = return_distribution_histogram(sample, pinned_edge=pinned)
        width = _observed_bin_width(histogram)
        for edge in histogram.edges:
            index = (edge - pinned) / width
            assert abs(index - round(index)) < 1e-9


def test_the_published_grid_is_strictly_ascending_with_one_more_edge_than_count():
    """``ReturnHistogram``'s own docstring contract: uniform widths, ``len(edges) == len(counts) + 1``.

    ``np.allclose`` is called with ``rtol=1e-12`` instead of its 1e-5 default: the
    measured spread of ``np.diff(edges)`` around the width is 2.3e-15 relative (the
    float re-rounding of ``pinned + k * width``), so 1e-12 leaves three orders of
    headroom while staying seven orders tighter than a default that would accept a
    visibly ragged grid.
    """
    canonical = _daily_returns()
    tail = historical_var_cvar(canonical, confidence_level=_CONFIDENCE_LEVEL)
    histogram = return_distribution_histogram(tail.horizon_returns, pinned_edge=-tail.value_at_risk)
    width = _observed_bin_width(histogram)

    assert len(histogram.edges) == len(histogram.counts) + 1
    # Deliberately not strict: the two operands differ in length by one by
    # construction, which is what makes this the adjacent-pairs idiom.
    assert all(right > left for left, right in zip(histogram.edges, histogram.edges[1:], strict=False))
    assert np.allclose(np.diff(np.asarray(histogram.edges)), width, rtol=1e-12, atol=0.0)


def test_no_observation_is_dropped_even_when_an_extreme_lands_exactly_on_an_edge():
    """Total coverage is the property a translated grid can most easily lose.

    ``np.histogram`` discards anything outside ``[edges[0], edges[-1]]``, so shifting
    the lattice onto the pin has to EXTEND the grid outward rather than round an
    endpoint. Pinning on the sample minimum and then on the sample maximum forces both
    boundary conditions: the minimum sits on a left edge (half-open, included) and the
    maximum sits on the final right edge (closed, also included).
    """
    canonical = _daily_returns()
    tail = historical_var_cvar(canonical, confidence_level=_CONFIDENCE_LEVEL)

    for sample, pinned in ((canonical, -tail.value_at_risk), (canonical, min(canonical)), (canonical, max(canonical)), (canonical, -0.5), (_gain_only_series(), 0.0)):
        histogram = return_distribution_histogram(sample, pinned_edge=pinned)
        assert sum(histogram.counts) == len(sample)
        assert histogram.edges[0] <= min(sample)
        assert histogram.edges[-1] >= max(sample)


def test_the_bin_width_is_the_freedman_diaconis_width_numpy_would_have_chosen():
    """Pinning moves the grid, it does not resize the bins.

    The tolerance is ``rel=1e-12`` because the comparison is against
    ``edges[1] - edges[0]``, which re-rounds two lattice points (see
    :func:`_observed_bin_width`); the measured disagreement is at most 2.3e-15
    relative. A width chosen by any other rule would differ in the third digit, not
    the fifteenth — on the canonical sample the entropy-style ``numBins`` heuristic
    pinned in block (c) gives 13 bins where Freedman-Diaconis gives 21.
    """
    canonical = _daily_returns()
    tail = historical_var_cvar(canonical, confidence_level=_CONFIDENCE_LEVEL)

    for sample, pinned in ((canonical, -tail.value_at_risk), (tail.horizon_returns, -tail.value_at_risk), (canonical, 0.0), (_gain_only_series(), 0.0)):
        histogram = return_distribution_histogram(sample, pinned_edge=pinned)
        assert _observed_bin_width(histogram) == pytest.approx(_freedman_diaconis_width(sample), rel=1e-12)


def test_the_counts_are_a_plain_numpy_histogram_over_the_published_edges():
    """The function CHOOSES a grid; it must never reimplement the binning itself.

    A hand-rolled loop is where the half-open convention gets lost — the last bin is
    closed on the right and every other bin is not, and only ``np.histogram`` gets
    that free. Exact integer equality: counts are not approximate.
    """
    canonical = _daily_returns()
    tail = historical_var_cvar(canonical, confidence_level=_CONFIDENCE_LEVEL)

    for sample, pinned in ((canonical, -tail.value_at_risk), (canonical, max(canonical)), (_gain_only_series(), 0.0), (_clamp_stress_series(), -0.0002)):
        histogram = return_distribution_histogram(sample, pinned_edge=pinned)
        reference, _ = np.histogram(np.asarray(sample, dtype=float), bins=np.asarray(histogram.edges, dtype=float))
        assert tuple(int(count) for count in reference) == histogram.counts


def test_the_bars_left_of_the_pinned_edge_hold_the_confidence_tail_of_the_sample():
    """The shaded area is a whole number of bars AND it is the tail, not a bar boundary artefact.

    The sample is fed as ``tail.horizon_returns`` because that is what the producer
    bins, and at ``horizon_days=1`` those are ``(1 + r) - 1`` rather than ``r`` — a
    last-ulp difference on 740 of these 750 observations, which is enough to move an
    observation across a cut placed exactly on one of them.

    The fraction cannot be exactly 5%. The empirical quantile lands ON a data point:
    ``ceil(0.95 * 750) = 713`` selects the 713th smallest loss, leaving 37 strictly
    worse observations where ``0.05 * 750 = 37.5`` would want 37.5 of them. Hence
    ``37 / 750 = 0.0493``. A band is asserted rather than an equality so the test
    survives migration step M2's replacement of the estimator; the band is ±1
    observation (1/750 = 0.0013) widened to 0.01 to absorb a different but still
    reasonable quantile convention.
    """
    canonical = _daily_returns()
    tail = historical_var_cvar(canonical, confidence_level=_CONFIDENCE_LEVEL)
    pinned = -tail.value_at_risk
    histogram = return_distribution_histogram(tail.horizon_returns, pinned_edge=pinned)

    assert pinned < 0.0  # the cut is a LOSS, so it lives left of zero
    strictly_below = sum(1 for value in tail.horizon_returns if value < pinned)
    assert strictly_below / len(tail.horizon_returns) == pytest.approx(_TAIL_ALPHA, abs=0.01)

    # The bars to the left of the cut are exactly those observations: bins are
    # ``[lower, upper)``, so an observation sitting ON the cut belongs to the bin to
    # its RIGHT and is correctly excluded from the shaded loss area.
    pin_index = histogram.edges.index(pinned)
    assert sum(histogram.counts[:pin_index]) == strictly_below


def test_an_empty_return_series_yields_an_empty_histogram_and_keeps_the_requested_pin():
    """No data is not an error: a scope with no returns must still render an empty chart."""
    histogram = return_distribution_histogram([], pinned_edge=-0.02)

    assert histogram.edges == ()
    assert histogram.counts == ()
    assert histogram.pinned_edge == -0.02


def test_a_zero_spread_series_uses_the_documented_fallback_width_and_never_numpys_unit_padding():
    """A constant or single-observation series is binned at ``max(|highest|, |pinned|, 1.0) * 1e-3``.

    WHY THE GUARD IS ``if highest > lowest`` AND NOT A CHECK ON THE RETURNED WIDTH.
    Freedman-Diaconis has no interquartile range to work from here, but NumPy does not
    answer with zero: ``_get_outer_edges`` pads a zero-range sample to
    ``[min - 0.5, max + 0.5]`` and emits a single bin, so ``np.diff(...).max()`` comes
    back as **1.0** — positive and finite, which sails straight past a ``width <= 0.0``
    test and publishes one bar a hundred percentage points wide for a series of decimal
    returns. That is the regression this test exists to prevent, which is why the width
    is asserted to be far NARROWER than 1.0 as well as equal to the fallback: the
    equality alone would still pass if the fallback formula were ever retuned upward,
    and the unit-wide bar is the SHAPE of the bug, not its exact value.
    """
    constant = [0.001] * 50
    fallback = max(abs(max(constant)), abs(0.0), 1.0) * 1e-3
    histogram = return_distribution_histogram(constant, pinned_edge=0.0)

    assert fallback == pytest.approx(0.001, rel=1e-12)
    assert _observed_bin_width(histogram) == pytest.approx(fallback, rel=1e-12)
    assert _observed_bin_width(histogram) < 0.01  # NumPy's padded 1.0 is 1000x the fallback
    assert len(histogram.counts) == 1
    assert sum(histogram.counts) == len(constant)
    assert min(abs(edge) for edge in histogram.edges) == 0.0

    # A single observation takes the same branch. The grid has to span the pin as well
    # as the lone value, so a pin sitting ~3 widths to its left buys 4 bins, not 1.
    single = return_distribution_histogram([0.0031], pinned_edge=-0.0)
    assert _observed_bin_width(single) == pytest.approx(max(0.0031, 0.0, 1.0) * 1e-3, rel=1e-12)
    assert _observed_bin_width(single) < 0.01
    assert len(single.counts) == 4
    assert sum(single.counts) == 1
    assert min(abs(edge - single.pinned_edge) for edge in single.edges) == 0.0

    # ``last_index <= first_index``: pinning on the only value there is leaves a zero
    # span, and the grid must still publish one real bin rather than an empty tuple.
    degenerate = return_distribution_histogram([0.0123], pinned_edge=0.0123)
    assert degenerate.counts == (1,)
    assert degenerate.edges[0] == 0.0123
    assert _observed_bin_width(degenerate) == pytest.approx(0.001, rel=1e-12)


def test_the_var_zero_floor_puts_the_cut_on_zero_and_the_grid_still_spans_the_whole_distribution():
    """A series that only ever gained reports ``value_at_risk == 0`` and pins the cut OUTSIDE the data.

    ``historical_var_cvar`` floors every loss at zero, so a gain-only series has a VaR
    of exactly 0.0 and the producer pins at ``-0.0`` — to the LEFT of every
    observation. The grid is deliberately extended to span the pin as well as the
    data, so the cut stays exactly an edge and the chart shows the whole distribution
    sitting to the right of zero, with empty bars in between.

    NOTE: in this case the VaR line is on zero rather than on a quantile of the data.
    That is a true picture of what is being REPORTED (a floored, ``ge=0`` loss
    magnitude), not a defect of the histogram.

    The bin count 11 is re-derivable: NumPy's Freedman-Diaconis spacing on this ramp
    is 0.0015 / 8 = 0.0001875, and the span from the pin at 0.0 to the maximum 0.0020
    is 10.67 widths, rounded outward to 11.
    """
    gains = _gain_only_series()
    summary = historical_var_cvar(gains, confidence_level=_CONFIDENCE_LEVEL)
    pinned = -summary.value_at_risk

    assert summary.value_at_risk == 0.0
    assert pinned == 0.0
    # ``-0.0``: a negative zero, because the producer negates a positive-zero magnitude.
    assert math.copysign(1.0, pinned) < 0.0

    histogram = return_distribution_histogram(summary.horizon_returns, pinned_edge=pinned)

    assert min(abs(edge - pinned) for edge in histogram.edges) == 0.0
    assert sum(histogram.counts) == len(gains)
    assert min(histogram.edges) <= 0.0 <= max(histogram.edges)
    assert len(histogram.counts) == 11
    # The pinned edge is reconstructed as ``pinned + 0 * width``, which turns the
    # negative zero back into a positive one. They still compare equal, so a renderer
    # matching the cut by value is safe — one matching it by repr or by sign is not.
    assert histogram.edges[0] == pinned
    assert math.copysign(1.0, histogram.edges[0]) > 0.0
    # The distribution really does sit entirely to the right of the cut.
    assert histogram.counts[0] == 0
    assert min(gains) > pinned


def test_a_non_finite_pinned_edge_is_always_rejected_even_with_nothing_to_bin():
    """The pin is validated BEFORE the empty-input shortcut, so no NaN can reach a caller.

    Ordering is the entire content of this test. While the empty guard ran first, an
    empty series answered ``ReturnHistogram(edges=(), counts=(), pinned_edge=nan)``
    instead of raising — and ``RiskVarCvarOutput.var_bin_edge`` is a ``FiniteFloat``,
    so the payload would have blown up one layer further out, where the cause is far
    harder to read than a ``ValueError`` from the function that was handed the NaN.
    All six combinations of {nan, inf, -inf} x {empty, non-empty} must raise.
    """
    for bad in (float("nan"), float("inf"), float("-inf")):
        for sample in ([], [0.01, -0.02, 0.03]):
            with pytest.raises(ValueError, match="pinned_edge must be finite"):
                return_distribution_histogram(sample, pinned_edge=bad)

    # Moving the guard must not have cost the empty shortcut itself.
    empty = return_distribution_histogram([], pinned_edge=-0.02)
    assert empty.edges == ()
    assert empty.counts == ()
    assert empty.pinned_edge == -0.02


def test_a_non_finite_observation_is_rejected_by_the_shared_finite_values_guard():
    """``_finite_values`` RAISES on a NaN or an infinity — it does not silently drop it.

    Dropping would be the dangerous contract here: the counts would still sum to fewer
    observations than the caller passed, and ``sum(counts) == n`` — the invariant every
    other test in this block leans on — would become unprovable from the outside.
    """
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="returns must be finite"):
            return_distribution_histogram([0.01, bad, 0.03], pinned_edge=-0.01)


def test_the_bin_count_guard_is_a_true_ceiling_at_every_pin_position():
    """``_MAX_HISTOGRAM_BINS`` really caps the grid, whatever the pin does to the alignment.

    The clamp divides the span by ``_MAX_HISTOGRAM_BINS - 2``, and the ``- 2`` is
    load-bearing. The grid is aligned to the PIN, not to the span, so ``first_index``
    is rounded down and ``last_index`` up, and each rounding can add a bin:
    ``ceil(b) - floor(a)`` reaches ``divisor + 1`` whenever the pin is not a span
    endpoint, and the second bin of margin absorbs the float case where
    ``span / (span / divisor)`` evaluates a hair above ``divisor`` and is rounded
    outward too. Dividing by the bare constant therefore overshot it.

    SWEPT RATHER THAN SPOT-CHECKED ON PURPOSE: the overshoot is position-dependent, so
    one pin proves nothing. On this sample the pin at ``0.0`` yields 198 bins while the
    pin at ``-0.0002`` yields 199 — a single-pin test could have picked either, and the
    original defect was found only because several positions were tried.
    """
    sample = _clamp_stress_series()
    unclamped_bins = len(np.histogram_bin_edges(np.asarray(sample, dtype=float), bins="fd")) - 1
    assert unclamped_bins > _MAX_HISTOGRAM_BINS  # the clamp genuinely has work to do

    pins = [float(value) for value in np.linspace(-0.6, 0.6, 101)]
    pins += [min(sample), max(sample), 0.0, -0.0]
    observed: list[int] = []
    for pinned in pins:
        histogram = return_distribution_histogram(sample, pinned_edge=pinned)
        assert len(histogram.counts) <= _MAX_HISTOGRAM_BINS
        assert sum(histogram.counts) == len(sample)
        assert min(abs(edge - pinned) for edge in histogram.edges) == 0.0
        observed.append(len(histogram.counts))

    # The margin is USED, not decorative: at least one pin needs more bins than the
    # divisor, which is exactly what dividing by the bare constant used to overflow.
    # Asserted as an inequality rather than as the measured maximum, which is this
    # sample's own business and would be brittle for the wrong reason.
    assert max(observed) > _MAX_HISTOGRAM_BINS - 2
    assert max(observed) <= _MAX_HISTOGRAM_BINS


def test_the_historical_var_analytic_publishes_contiguous_bins_cut_exactly_on_the_var_edge():
    """The plugin re-packs the primitive's grid and adds no arithmetic of its own.

    ``RiskVarCvarBin`` lives in signed-return space while ``value_at_risk`` is a
    positive magnitude, so ``var_bin_edge`` is the negated VaR and is the only thing
    that lets a renderer cross between the two conventions in one payload. Everything
    asserted here is exact equality: the producer must not round, re-bin or re-derive.

    PURE: the context carries only the primary return series, which is all
    ``require_primary_returns`` reads. No database, no server, no prepared series.
    """
    returns = _daily_returns()
    output = HistoricalVarAnalytic().compute(HistoricalVarParams(confidence_level=_CONFIDENCE_LEVEL), _var_execution_context(returns)).output
    bins = output.return_bins

    assert bins
    assert output.observations == len(returns)
    # Contiguous tiling: no gap and no overlap between neighbouring bars.
    assert all(bins[index].upper_bound == bins[index + 1].lower_bound for index in range(len(bins) - 1))
    assert sum(item.count for item in bins) == output.observations
    assert output.var_bin_edge == -output.value_at_risk
    assert output.var_bin_edge <= 0.0  # a loss magnitude negated back into return space
    boundaries = [item.lower_bound for item in bins] + [bins[-1].upper_bound]
    assert min(abs(boundary - output.var_bin_edge) for boundary in boundaries) == 0.0

    # The plugin is a re-packer: bounds and counts are the primitive's, bit for bit.
    summary = historical_var_cvar(returns, confidence_level=_CONFIDENCE_LEVEL)
    histogram = return_distribution_histogram(summary.horizon_returns, pinned_edge=-summary.value_at_risk)
    assert [item.lower_bound for item in bins] == list(histogram.edges[:-1])
    assert [item.upper_bound for item in bins] == list(histogram.edges[1:])
    assert tuple(item.count for item in bins) == histogram.counts

    # A multi-day horizon bins the COMPOUNDED series, so the observation count is the
    # overlapping-window count and the bins must still tile it completely.
    horizon = 5
    multi_day = HistoricalVarAnalytic().compute(HistoricalVarParams(confidence_level=_CONFIDENCE_LEVEL, horizon_days=horizon), _var_execution_context(returns)).output
    assert multi_day.observations == len(returns) - horizon + 1
    assert sum(item.count for item in multi_day.return_bins) == multi_day.observations
    assert multi_day.var_bin_edge == -multi_day.value_at_risk
    assert all(multi_day.return_bins[index].upper_bound == multi_day.return_bins[index + 1].lower_bound for index in range(len(multi_day.return_bins) - 1))


# --------------------------------------------------------------------------- #
# Block (g) — M1: the vectorised rolling signals must reproduce the loop exactly.
#
# Step M1 of the mathematics migration replaced four pure-Python rolling loops with
# vectorised pandas passes. The defining property of the migration is that NOTHING
# about the published numbers changes, so ``rolling_single_values`` and
# ``rolling_pair_values`` are kept in the source as the executable reference semantics
# and every test below drives both paths over the same sample. The four call sites are
# the differential contract:
#
#   rolling_return.py:122      rolling_single_values(r, W, lambda w: compounded_return(w) * 100)
#                           -> rolling_compounded_return_values(r, W, scale=100.0)
#   rolling_volatility.py:115  rolling_single_values(r, W, lambda w: annualized_volatility(w, f) * 100)
#                           -> rolling_annualized_volatility_values(r, W, f, scale=100.0)
#   rolling_sharpe.py:140      rolling_single_values(r, W, lambda w: annualized_sharpe(w, f, annual_risk_free_rate=rf))
#                           -> rolling_annualized_sharpe_values(r, W, f, annual_risk_free_rate=rf)
#   rolling_beta.py:145        rolling_pair_values(p, c, W, beta)
#                           -> rolling_beta_values(p, c, W)
#
# 🔴 THE REGRESSION THESE TESTS EXIST TO MAKE IMPOSSIBLE.
# ``Series.rolling`` emits ``NaN`` for a warm-up cell AND for a cell whose statistic is
# undefined — the same float, as block (d) demonstrates. An implementation that recovers
# "undefined" by reading ``NaN`` back out of the pandas output is therefore wrong in BOTH
# directions at once: it counts warm-up cells that were never undefined, and it misses
# the undefined windows that divide a non-zero mean by a zero deviation, because those
# come out as ``inf`` rather than ``NaN``. The count is not cosmetic — ``signal_service``
# turns it into ``SignalWarningCode.UNDEFINED_METRIC_WINDOW`` and, when every window is
# undefined, into ``SignalUnavailableError``. A value-only comparison notices none of it,
# so EVERY differential assertion below compares the ``None`` mask and the count as well
# as the numbers.
#
# Windows: 30 is the shipped default of rolling_return/rolling_volatility and 90 of
# rolling_sharpe/rolling_beta, so both defaults are exercised, plus a short window that
# leaves far more full windows per sample and moves the warm-up boundary somewhere else.
# --------------------------------------------------------------------------- #

# Tolerance for every loop-versus-vectorised comparison in this block, and the reason it
# is neither tighter nor looser.
#
# The scalar metrics sum with ``math.fsum`` (exactly rounded); pandas sums incrementally.
# The two are NOT bit-identical and cannot be made so. The worst relative divergence
# measured while the migration was being made is 6.9e-12, on
# ``rolling_compounded_return_values`` — its ``expm1(log1p(x).rolling(W).sum())`` form
# adds a log/exp round trip the scalar product does not have.
#
# ``rel=1e-9`` leaves ~150x headroom over that worst case while staying 1000x tighter
# than pytest's default ``rel=1e-6``, so it is still a real constraint: a semantic change
# moves a rolling value by very much more than a part per billion. ``abs=1e-12`` is
# REQUIRED rather than belt-and-braces, because rolling returns and rolling betas cross
# zero and a purely relative tolerance is meaningless against an expected value of 1e-15.
# ``pytest.approx`` takes the LARGER of the two, so the absolute floor only ever applies
# where the relative one has stopped meaning anything.
#
# DO NOT TIGHTEN: a tighter bound produces a red that is float noise, not a defect.
# DO NOT LOOSEN: a looser bound stops proving the migration preserved the numbers.
_ROLLING_REL_TOLERANCE = 1e-9
_ROLLING_ABS_TOLERANCE = 1e-12

_ROLLING_SEEDS = (5, 43, 1301)
_ROLLING_WINDOWS = (7, 30, 90)
_ROLLING_SAMPLE_SIZE = 260

# Flat-run samples. The run is long enough to contain several full windows at the short
# window sizes and shorter than the longest one, so the same fixture also covers the
# "the hole is smaller than the window, therefore nothing is undefined" case.
_FLAT_SEED = 314
_FLAT_SAMPLE_SIZE = 60
_FLAT_RUN_LENGTH = 15
_FLAT_RUN_VALUE = 0.004
_FLAT_WINDOWS = (5, 10, 15, 20)
_FLAT_RUN_STARTS = {"head": 0, "middle": (_FLAT_SAMPLE_SIZE - _FLAT_RUN_LENGTH) // 2, "tail": _FLAT_SAMPLE_SIZE - _FLAT_RUN_LENGTH}


def _rolling_sample(seed: int) -> list[float]:
    """Return one healthy daily-return series for the differential comparison."""
    generator = np.random.default_rng(seed)
    return [float(value) for value in generator.normal(0.0004, 0.011, _ROLLING_SAMPLE_SIZE)]


def _rolling_pair(seed: int) -> tuple[list[float], list[float]]:
    """Return an (asset, benchmark) pair on one joint calendar with a non-degenerate beta."""
    generator = np.random.default_rng(seed)
    benchmark = generator.normal(0.0003, 0.009, _ROLLING_SAMPLE_SIZE)
    asset = 0.8 * benchmark + generator.normal(0.0, 0.004, _ROLLING_SAMPLE_SIZE)
    return [float(value) for value in asset], [float(value) for value in benchmark]


def _healthy_short_sample() -> list[float]:
    """Return a short healthy series: the primary partner for the flat-comparison cases."""
    generator = np.random.default_rng(_FLAT_SEED + 1)
    return [float(value) for value in generator.normal(0.0004, 0.011, _FLAT_SAMPLE_SIZE)]


def _flat_run_sample(position: str) -> list[float]:
    """Return a healthy series with one flat run of ``_FLAT_RUN_LENGTH`` spliced in."""
    generator = np.random.default_rng(_FLAT_SEED)
    values = [float(value) for value in generator.normal(0.0004, 0.011, _FLAT_SAMPLE_SIZE)]
    start = _FLAT_RUN_STARTS[position]
    values[start : start + _FLAT_RUN_LENGTH] = [_FLAT_RUN_VALUE] * _FLAT_RUN_LENGTH
    return values


def _windows_inside_a_flat_run(run_length: int, window: int) -> int:
    """Return how many full windows fit ENTIRELY inside a flat run — the undefined ones.

    A window is degenerate only when every observation in it is the same number, so the
    undefined windows are exactly those that start no earlier than the run and end no
    later than it: ``max(0, run_length - window + 1)`` of them, wherever the run sits.
    This closed form is what the tests assert against, and its validity rests on the
    sample-identity test below: no window OUTSIDE the run may be accidentally flat.
    """
    return max(0, run_length - window + 1)


def _loop_compounded_return(returns: Sequence[float], window: int, *, scale: float = 1.0) -> tuple[list[float | None], int]:
    """Return the pre-M1 rolling compounded return, exactly as ``rolling_return.py`` called it."""
    return rolling_single_values(returns, window, lambda sample: compounded_return(sample) * scale)


def _loop_annualized_volatility(returns: Sequence[float], window: int, factor: float, *, scale: float = 1.0) -> tuple[list[float | None], int]:
    """Return the pre-M1 rolling volatility, exactly as ``rolling_volatility.py`` called it."""
    return rolling_single_values(returns, window, lambda sample: annualized_volatility(sample, factor) * scale)


def _loop_annualized_sharpe(returns: Sequence[float], window: int, factor: float, *, annual_risk_free_rate: float = 0.0) -> tuple[list[float | None], int]:
    """Return the pre-M1 rolling Sharpe, exactly as ``rolling_sharpe.py`` called it."""
    return rolling_single_values(returns, window, lambda sample: annualized_sharpe(sample, factor, annual_risk_free_rate=annual_risk_free_rate))


def _loop_beta(primary: Sequence[float], comparison: Sequence[float], window: int) -> tuple[list[float | None], int]:
    """Return the pre-M1 rolling beta, exactly as ``rolling_beta.py`` called it."""
    return rolling_pair_values(primary, comparison, window, beta)


def _assert_rolling_paths_agree(
    vectorised: tuple[list[float | None], int],
    loop: tuple[list[float | None], int],
    *,
    observations: int,
    label: str,
) -> None:
    """Assert the vectorised pass reproduces the reference loop on every axis that matters.

    Five separate claims, deliberately not collapsed into one comparison, because each
    one fails differently:

    1. LENGTH against ``observations + 1``. The leading ``None`` is the valuation
       baseline; ``build_line_computation`` zips values against price points and raises
       if the alignment is lost, so a length change is an API-level break.
    2. The ``None`` MASK, position by position. Comparing sets or counts of ``None``
       would accept a warm-up boundary that moved by one, which is the single most
       likely off-by-one in a rewrite that decides warm-up by index.
    3. The undefined COUNT. This is the number that becomes a user-visible warning and,
       at saturation, a ``SignalUnavailableError``. It cannot be derived from the mask,
       which is precisely the point of the whole block.
    4. The VALUES, within the migration tolerance documented above.
    5. That every published value is FINITE. ``inf`` is what a zero denominator produces
       when the numerator is not zero, and it would serialise into the payload as a
       number no chart can draw. The undefined test is what keeps it out.
    """
    values, undefined_windows = vectorised
    expected_values, expected_undefined = loop

    assert len(values) == observations + 1, f"{label}: the valuation baseline alignment is lost"
    assert len(values) == len(expected_values), f"{label}: length differs from the reference loop"
    assert [value is None for value in values] == [value is None for value in expected_values], f"{label}: the None positions differ from the reference loop"
    assert undefined_windows == expected_undefined, f"{label}: undefined window count differs from the reference loop"
    assert all(value is None or math.isfinite(value) for value in values), f"{label}: a non-finite value reached the payload"

    defined = [value for value in values if value is not None]
    expected_defined = [value for value in expected_values if value is not None]
    assert defined == pytest.approx(expected_defined, rel=_ROLLING_REL_TOLERANCE, abs=_ROLLING_ABS_TOLERANCE), f"{label}: values differ beyond the migration tolerance"


def _migrated_signal_paths(returns: Sequence[float], window: int) -> list[tuple[str, tuple[list[float | None], int], tuple[list[float | None], int]]]:
    """Return ``(label, vectorised, loop)`` for all four migrated signals on one sample.

    Used by the edge-case tests, where the interesting behaviour is shared by all four
    helpers and writing it out four times would hide the one that eventually differs.
    The comparison series is an affine transform of the primary, so its variance is
    non-zero whenever the primary's is and beta stays defined by construction.
    """
    comparison = [value * 0.7 + 0.0001 for value in returns]
    return [
        ("compounded return", rolling_compounded_return_values(returns, window, scale=100.0), _loop_compounded_return(returns, window, scale=100.0)),
        ("annualized volatility", rolling_annualized_volatility_values(returns, window, _ANNUALIZATION, scale=100.0), _loop_annualized_volatility(returns, window, _ANNUALIZATION, scale=100.0)),
        ("annualized sharpe", rolling_annualized_sharpe_values(returns, window, _ANNUALIZATION), _loop_annualized_sharpe(returns, window, _ANNUALIZATION)),
        ("beta", rolling_beta_values(returns, comparison, window), _loop_beta(returns, comparison, window)),
    ]


def test_the_rolling_migration_samples_carry_exactly_the_flat_runs_the_expected_counts_are_derived_from():
    """Guard the generators: every undefined count in this block is DERIVED, not measured.

    The counts come from one closed form — a window is undefined only when it lies
    entirely inside a flat run, so there are ``max(0, run - window + 1)`` of them. That
    derivation is valid only while two things hold: the flat runs are exactly where and
    as long as they are declared, and no OTHER window is accidentally flat. The second
    holds because every remaining observation is distinct, which a continuous generator
    guarantees with probability one — this is a statement about the draw, not a hope. If
    either ever stops being true the expected counts become wrong everywhere at once, so
    it has to fail HERE, loudly, instead of as four confusing reds elsewhere.
    """
    for position, start in _FLAT_RUN_STARTS.items():
        sample = _flat_run_sample(position)
        assert len(sample) == _FLAT_SAMPLE_SIZE
        assert sample[start : start + _FLAT_RUN_LENGTH] == [_FLAT_RUN_VALUE] * _FLAT_RUN_LENGTH
        # One value repeated _FLAT_RUN_LENGTH times, every other observation unique.
        assert len(set(sample)) == _FLAT_SAMPLE_SIZE - _FLAT_RUN_LENGTH + 1

    # The healthy samples must carry no flat run at all, or the "count is zero" half of
    # the differential tests would be asserting the wrong thing for the right reason.
    assert len(set(_healthy_short_sample())) == _FLAT_SAMPLE_SIZE
    for seed in _ROLLING_SEEDS:
        assert len(set(_rolling_sample(seed))) == _ROLLING_SAMPLE_SIZE
        primary, comparison = _rolling_pair(seed)
        assert len(primary) == len(comparison) == _ROLLING_SAMPLE_SIZE
        assert len(set(comparison)) == _ROLLING_SAMPLE_SIZE


@pytest.mark.parametrize("seed", _ROLLING_SEEDS)
@pytest.mark.parametrize("window", _ROLLING_WINDOWS)
def test_the_vectorised_rolling_compounded_return_reproduces_the_reference_loop(window, seed):
    """``expm1(log1p(r).rolling(W).sum())`` must equal the running product, scale included.

    This is the helper carrying the largest legitimate divergence, because it is the only
    one that goes through a logarithm and back. It is also the only one that can never be
    undefined: compounding is defined for every finite window, so the count is a constant
    zero and any other answer means the undefined machinery has started firing on data
    that is merely degenerate.
    """
    returns = _rolling_sample(seed)
    vectorised = rolling_compounded_return_values(returns, window, scale=100.0)

    _assert_rolling_paths_agree(vectorised, _loop_compounded_return(returns, window, scale=100.0), observations=len(returns), label=f"compounded return, window={window}, seed={seed}")
    assert vectorised[1] == 0


@pytest.mark.parametrize("seed", _ROLLING_SEEDS)
@pytest.mark.parametrize("window", _ROLLING_WINDOWS)
def test_the_vectorised_rolling_annualized_volatility_reproduces_the_reference_loop(window, seed):
    """``rolling().std(ddof=1)`` must equal the scalar unbiased deviation, annualized and scaled.

    ``ddof`` is the thing to watch: pandas defaults to 1 and NumPy to 0, so a rewrite
    that dropped the explicit argument would divide by ``n`` instead of ``n - 1`` and
    publish a volatility that is quietly ~2 % low at a 30-day window — small enough to
    look like a rounding difference and large enough to be wrong.
    """
    returns = _rolling_sample(seed)
    vectorised = rolling_annualized_volatility_values(returns, window, _ANNUALIZATION, scale=100.0)

    _assert_rolling_paths_agree(vectorised, _loop_annualized_volatility(returns, window, _ANNUALIZATION, scale=100.0), observations=len(returns), label=f"volatility, window={window}, seed={seed}")
    assert vectorised[1] == 0


@pytest.mark.parametrize("seed", _ROLLING_SEEDS)
@pytest.mark.parametrize("window", _ROLLING_WINDOWS)
def test_the_vectorised_rolling_annualized_sharpe_reproduces_the_reference_loop(window, seed):
    """The ratio path must agree window by window, and report nothing undefined on healthy data.

    The count assertion is the load-bearing one here. On a sample with no flat window
    there is nothing to warn about, so a count above zero means the implementation has
    started reading warm-up cells as undefined — the exact regression this block exists
    to prevent, and the one that shows up as a warning the user cannot explain.
    """
    returns = _rolling_sample(seed)
    vectorised = rolling_annualized_sharpe_values(returns, window, _ANNUALIZATION)

    _assert_rolling_paths_agree(vectorised, _loop_annualized_sharpe(returns, window, _ANNUALIZATION), observations=len(returns), label=f"sharpe, window={window}, seed={seed}")
    assert vectorised[1] == 0


@pytest.mark.parametrize("seed", _ROLLING_SEEDS)
@pytest.mark.parametrize("window", _ROLLING_WINDOWS)
def test_the_vectorised_rolling_beta_reproduces_the_reference_loop(window, seed):
    """Rolling covariance over rolling variance must equal the scalar two-pass definition.

    pandas computes the covariance as ``E[XY] - E[X]E[Y]``, a one-pass form the scalar
    path deliberately does not use: ``sample_covariance`` centres first and sums with
    ``math.fsum``. The two agree here because daily returns are small and the means are
    tiny, which is exactly the regime the signal runs in — but it is an assumption worth
    pinning, because it is the one that would break first on a differently scaled series.
    """
    primary, comparison = _rolling_pair(seed)
    vectorised = rolling_beta_values(primary, comparison, window)

    _assert_rolling_paths_agree(vectorised, _loop_beta(primary, comparison, window), observations=len(primary), label=f"beta, window={window}, seed={seed}")
    assert vectorised[1] == 0


@pytest.mark.parametrize("window", _FLAT_WINDOWS)
@pytest.mark.parametrize("position", ("head", "middle", "tail"))
def test_the_vectorised_rolling_sharpe_counts_the_same_undefined_windows_as_the_loop_around_a_flat_run(position, window):
    """Real holes, in all three places they can sit, counted to the unit.

    A flat run gives the subject series zero dispersion, so every window inside it
    divides by zero and the Sharpe is genuinely undefined there. The three positions are
    not decoration: a run at the HEAD produces an undefined window immediately after
    warm-up ends, which is where an implementation that decides warm-up by value rather
    than by index goes wrong first; a run at the TAIL leaves the series ending on
    ``None``; a run in the MIDDLE is the only one with defined windows on both sides.

    The expected count is asserted against the reference loop first, so the closed form
    is proven on the path that was never rewritten before it is used to judge the new one.
    """
    returns = _flat_run_sample(position)
    expected_undefined = _windows_inside_a_flat_run(_FLAT_RUN_LENGTH, window)
    loop = _loop_annualized_sharpe(returns, window, _ANNUALIZATION)

    assert loop[1] == expected_undefined
    _assert_rolling_paths_agree(rolling_annualized_sharpe_values(returns, window, _ANNUALIZATION), loop, observations=len(returns), label=f"sharpe, flat run at the {position}, window={window}")


@pytest.mark.parametrize("window", _FLAT_WINDOWS)
@pytest.mark.parametrize("position", ("head", "middle", "tail"))
def test_the_vectorised_rolling_beta_counts_the_same_undefined_windows_as_the_loop_when_the_comparison_flattens(position, window):
    """Beta's hole belongs to the COMPARISON series, and it is counted the same way.

    The primary moves normally throughout: what makes these windows undefined is that
    the benchmark did not move at all, so there is no variance to regress against. Same
    three positions, same closed form, same count — and the warning the user sees says
    the same thing whichever of the two series went flat.
    """
    primary = _healthy_short_sample()
    comparison = _flat_run_sample(position)
    expected_undefined = _windows_inside_a_flat_run(_FLAT_RUN_LENGTH, window)
    loop = _loop_beta(primary, comparison, window)

    assert loop[1] == expected_undefined
    _assert_rolling_paths_agree(rolling_beta_values(primary, comparison, window), loop, observations=len(primary), label=f"beta, flat comparison run at the {position}, window={window}")


@pytest.mark.parametrize("window", (5, 20))
@pytest.mark.parametrize("constant", (0.0, _FLAT_RUN_VALUE))
def test_a_wholly_flat_series_leaves_every_full_sharpe_and_beta_window_undefined(constant, window):
    """Saturation: when EVERY full window is undefined the plugin stops publishing entirely.

    ``rolling_sharpe.py:146`` and ``rolling_beta.py:150`` both read
    ``if undefined_windows and all(value is None for value in values)`` and raise
    ``SignalUnavailableError``. That branch is reachable only when the count and the mask
    agree with each other on a degenerate series, so this test pins the precise state
    that triggers it — an all-zero series (nothing moved) and an all-constant one (it
    moved by the same amount every day, which is the same statistical statement).
    """
    returns = [constant] * _FLAT_SAMPLE_SIZE
    primary = _healthy_short_sample()
    full_windows = _FLAT_SAMPLE_SIZE - window + 1

    sharpe = rolling_annualized_sharpe_values(returns, window, _ANNUALIZATION)
    _assert_rolling_paths_agree(sharpe, _loop_annualized_sharpe(returns, window, _ANNUALIZATION), observations=len(returns), label=f"sharpe, wholly flat at {constant}, window={window}")
    assert sharpe[1] == full_windows
    assert all(value is None for value in sharpe[0])

    rolling_beta = rolling_beta_values(primary, returns, window)
    _assert_rolling_paths_agree(rolling_beta, _loop_beta(primary, returns, window), observations=len(primary), label=f"beta, wholly flat comparison at {constant}, window={window}")
    assert rolling_beta[1] == full_windows
    assert all(value is None for value in rolling_beta[0])


@pytest.mark.parametrize("window", (5, 20))
@pytest.mark.parametrize("constant", (0.0, _FLAT_RUN_VALUE))
def test_a_wholly_flat_series_stays_perfectly_defined_for_the_compounded_return_and_the_volatility(constant, window):
    """Undefined-ness is a property of the STATISTIC, never of the data looking degenerate.

    The same series that makes the Sharpe and the beta undefined is completely ordinary
    for the other two signals: a flat window compounds to a real number, and its
    volatility is zero — which is an answer, not the absence of one. Only the ratios that
    divide BY that zero lose their meaning. If the vectorised pass ever started flagging
    flat windows generically, every quiet stretch of a price series would raise a warning
    the user can neither act on nor get rid of.
    """
    returns = [constant] * _FLAT_SAMPLE_SIZE

    compounded = rolling_compounded_return_values(returns, window, scale=100.0)
    _assert_rolling_paths_agree(compounded, _loop_compounded_return(returns, window, scale=100.0), observations=len(returns), label=f"compounded return, wholly flat at {constant}, window={window}")
    assert compounded[1] == 0

    volatility = rolling_annualized_volatility_values(returns, window, _ANNUALIZATION, scale=100.0)
    _assert_rolling_paths_agree(volatility, _loop_annualized_volatility(returns, window, _ANNUALIZATION, scale=100.0), observations=len(returns), label=f"volatility, wholly flat at {constant}, window={window}")
    assert volatility[1] == 0

    volatility_values = volatility[0]
    assert all(value is not None for value in volatility_values[window:])
    assert volatility_values[window:] == pytest.approx([0.0] * (_FLAT_SAMPLE_SIZE - window + 1), abs=_ROLLING_ABS_TOLERANCE)


@pytest.mark.parametrize("window", (5, 20))
def test_a_flat_primary_leaves_the_beta_defined_because_only_the_comparison_variance_can_vanish(window):
    """The degeneracy is one-sided, and swapping the operands would be invisible in the values.

    Beta divides by the variance of the COMPARISON series. An asset that did not move
    against a benchmark that did has a beta of zero — a real, reportable answer, and the
    chart should draw a flat line at zero rather than a gap. Testing the wrong operand
    would blank exactly those windows while leaving every other case identical, so the
    only way to catch it is to assert the asymmetry directly.
    """
    primary = [_FLAT_RUN_VALUE] * _FLAT_SAMPLE_SIZE
    comparison = _healthy_short_sample()
    vectorised = rolling_beta_values(primary, comparison, window)

    _assert_rolling_paths_agree(vectorised, _loop_beta(primary, comparison, window), observations=len(primary), label=f"beta, flat primary, window={window}")
    assert vectorised[1] == 0
    # Mathematically exactly zero; numerically it is the residue of two nearly equal
    # means, divided by a variance of ~1.2e-4. The worst case that survives a
    # non-compensated rolling accumulator is ~4e-13, so the shared 1e-12 floor is the
    # right order of magnitude here — do not swap it for an exact `== 0.0`.
    assert vectorised[0][window:] == pytest.approx([0.0] * (_FLAT_SAMPLE_SIZE - window + 1), abs=_ROLLING_ABS_TOLERANCE)


# Two holes of different kinds in one short series, so both halves of the NaN-reading
# regression are observable at once. Indices 3-5 are an all-zero run (mean 0 over
# deviation 0, which pandas answers with NaN) and indices 7-11 a constant non-zero run
# (mean 0.004 over deviation 0, which pandas answers with +inf). Window 3.
_DOUBLE_HOLE_RETURNS = [0.01, -0.02, 0.015, 0.0, 0.0, 0.0, 0.012, 0.004, 0.004, 0.004, 0.004, 0.004, -0.01]
_DOUBLE_HOLE_WINDOW = 3


def test_warm_up_is_decided_by_index_while_undefined_is_decided_by_the_denominator():
    """THE test of this block: the two kinds of ``None`` are counted differently, on purpose.

    The published list holds seven ``None`` entries — one valuation baseline, two warm-up
    cells and four genuinely undefined windows — and the count must be exactly four. The
    hand-derived expectations below are checkable by eye from the sample above: with
    window 3 the flat runs at indices 3-5 and 7-11 contain one and three full windows
    respectively.

    Then the same data is pushed through the naive pandas expression an unwary rewrite
    would use, to show that reading ``NaN`` out of the output is wrong in BOTH directions
    simultaneously. It reports three undefined windows where there are four, and the
    three it reports are not the same three: two of them are warm-up cells that were
    never undefined, and the three windows it misses come out as ``+inf``, which would be
    published as a VALUE. The totals are close enough to be mistaken for an off-by-one,
    which is precisely why the masks are compared and not just the counts.

    This also pins the pandas behaviour the vectorised implementation depends on: a
    window of repeated identical values yields a deviation of exactly ``0.0``, which is
    what makes the ``abs(deviation) <= ZERO_TOLERANCE`` test decisive rather than
    approximate. If a future pandas returned float dust there instead, both the ``inf``
    assertion here and the counts above would move together, and the red would be real.
    """
    values, undefined_windows = rolling_annualized_sharpe_values(_DOUBLE_HOLE_RETURNS, _DOUBLE_HOLE_WINDOW, _ANNUALIZATION)

    assert len(values) == len(_DOUBLE_HOLE_RETURNS) + 1
    assert [value is None for value in values] == [True, True, True, False, False, False, True, False, False, False, True, True, True, False]
    assert sum(value is None for value in values) == 7
    assert undefined_windows == 4
    assert values[0] is None

    # The reference loop agrees, mask and count, on exactly the same sample.
    _assert_rolling_paths_agree((values, undefined_windows), _loop_annualized_sharpe(_DOUBLE_HOLE_RETURNS, _DOUBLE_HOLE_WINDOW, _ANNUALIZATION), observations=len(_DOUBLE_HOLE_RETURNS), label="double-holed sharpe")

    # What a NaN-reading implementation would have seen instead.
    rolling = pd.Series(_DOUBLE_HOLE_RETURNS, dtype="float64").rolling(_DOUBLE_HOLE_WINDOW)
    naive = rolling.mean() / rolling.std(ddof=1)

    assert naive.isna().tolist() == [True, True, False, False, False, True, False, False, False, False, False, False, False]
    assert int(naive.isna().sum()) == 3
    # Two of those three are warm-up, which is not an undefined window at all...
    assert naive.isna().tolist()[: _DOUBLE_HOLE_WINDOW - 1] == [True, True]
    # ...and the three windows inside the constant run are +inf, so NaN never sees them.
    assert np.isinf(naive.to_numpy()).tolist() == [False, False, False, False, False, False, False, False, False, True, True, True, False]

    # None of that infinity reaches the payload: the undefined test intercepts it first.
    assert all(value is None or math.isfinite(value) for value in values)


# A five-observation series whose every full window at width 3 is a permutation of
# ``[0.0, 0.0, spike]``, so each has variance ``spike ** 2 / 3`` exactly.
#
# Deliberately ALL on the spike's own scale. An incremental rolling statistic carries its
# accumulator across windows, so a microscopic window preceded by ordinary ~1e-2 returns
# is dominated by the residue of the values already removed from it — an inherent limit
# of any online algorithm, not something the migration could fix or should be blamed for.
# Keeping the whole sample on one scale isolates the only question this test asks: WHERE
# the undefined boundary sits.
_BOUNDARY_WINDOW = 3
_BOUNDARY_SAMPLE_SIZE = 5
_BOUNDARY_FULL_WINDOWS = _BOUNDARY_SAMPLE_SIZE - _BOUNDARY_WINDOW + 1
_BOUNDARY_PRIMARY = [0.01, -0.02, 0.015, 0.012, -0.008]


def _boundary_sample(spike: float) -> list[float]:
    """Return the five-observation probe series built around one ``spike``."""
    return [0.0, 0.0, spike, 0.0, 0.0]


def test_the_undefined_boundary_is_the_shared_zero_tolerance_and_not_an_exact_equality_with_zero():
    """Both paths cut at ``abs(denominator) <= ZERO_TOLERANCE``, and they cut on different quantities.

    The scalar metrics test ``math.isclose(x, 0.0, rel_tol=0.0, abs_tol=ZERO_TOLERANCE)``,
    which is ``abs(x) <= ZERO_TOLERANCE``; the vectorised pass tests the rolling
    denominator with the same constant, now exported from ``metrics.py`` so the two can
    never drift apart. Testing ``== 0.0`` instead would be a different boundary, and the
    windows between the two would flip from warning to value without anything else moving.

    The second half is the subtle one. The Sharpe's denominator is the DEVIATION and
    beta's is the VARIANCE — a squared scale. A comparison series whose deviation is
    5.8e-10, more than six hundred thousand times the tolerance, still has a variance of
    3.3e-19 and is correctly undefined. An implementation that tested beta's deviation
    (or the Sharpe's variance) would move the boundary by half its exponent and silently
    change which windows warn. Each precondition below is PROVEN with the scalar
    functions rather than asserted from arithmetic done in a docstring.
    """
    for spike, expected_undefined in ((ZERO_TOLERANCE / 10.0, _BOUNDARY_FULL_WINDOWS), (ZERO_TOLERANCE * 100.0, 0)):
        returns = _boundary_sample(spike)
        assert len(returns) == _BOUNDARY_SAMPLE_SIZE  # the expected counts below are derived from this width
        probe = returns[:_BOUNDARY_WINDOW]
        assert sample_standard_deviation(probe) > 0.0  # dispersion exists; the only question is whether it counts
        assert (sample_standard_deviation(probe) <= ZERO_TOLERANCE) == (expected_undefined > 0)

        loop = _loop_annualized_sharpe(returns, _BOUNDARY_WINDOW, _ANNUALIZATION)
        assert loop[1] == expected_undefined
        _assert_rolling_paths_agree(rolling_annualized_sharpe_values(returns, _BOUNDARY_WINDOW, _ANNUALIZATION), loop, observations=len(returns), label=f"sharpe boundary, spike={spike}")

    # Beta cuts on the variance, so in deviation terms its boundary sits at the square
    # root of the tolerance: 1e-9 gives a variance of 3.3e-19 (undefined) while 1e-6
    # gives 3.3e-13 (defined), and the deviations of both are enormous next to 1e-15.
    for spike, expected_undefined in ((1e-9, _BOUNDARY_FULL_WINDOWS), (1e-6, 0)):
        comparison = _boundary_sample(spike)
        assert len(comparison) == len(_BOUNDARY_PRIMARY) == _BOUNDARY_SAMPLE_SIZE
        probe = comparison[:_BOUNDARY_WINDOW]
        assert sample_standard_deviation(probe) > ZERO_TOLERANCE  # not degenerate on the deviation scale...
        assert (sample_variance(probe) <= ZERO_TOLERANCE) == (expected_undefined > 0)  # ...but this is the scale that decides

        loop = _loop_beta(_BOUNDARY_PRIMARY, comparison, _BOUNDARY_WINDOW)
        assert loop[1] == expected_undefined
        _assert_rolling_paths_agree(rolling_beta_values(_BOUNDARY_PRIMARY, comparison, _BOUNDARY_WINDOW), loop, observations=len(_BOUNDARY_PRIMARY), label=f"beta boundary, spike={spike}")


@pytest.mark.parametrize("window", (5, 30, 90))
def test_a_series_shorter_than_its_window_publishes_only_the_baseline_and_warm_up(window):
    """Not enough history is not an error, and it is not an undefined window either.

    ``signal_service`` reads the count to decide the result STATUS, so a helper that
    returned ``window - 1`` here would report a chart full of undefined windows for the
    ordinary case of a young asset. All four helpers short-circuit, and the shape they
    return has to be the same shape the loop produces by simply never entering its body.
    """
    returns = _rolling_sample(5)[: window - 1]

    for label, vectorised, loop in _migrated_signal_paths(returns, window):
        _assert_rolling_paths_agree(vectorised, loop, observations=len(returns), label=f"{label}, window={window} on {len(returns)} observations")
        assert vectorised[0] == [None] * window  # the baseline plus window - 1 warm-up cells
        assert vectorised[1] == 0


@pytest.mark.parametrize("window", (2, 5, 30, 90))
def test_a_series_exactly_as_long_as_its_window_publishes_exactly_one_value(window):
    """The boundary between "no full window" and "one full window" is off by one on both sides.

    This is the case that catches a ``<`` written as ``<=`` in either the short-circuit or
    the warm-up range: one observation fewer and the whole series is warm-up, one more and
    the final cell carries the first real value. ``window=2`` is included because it is the
    smallest width the ``ddof=1`` metrics accept at all.
    """
    returns = _rolling_sample(43)[:window]

    for label, vectorised, loop in _migrated_signal_paths(returns, window):
        _assert_rolling_paths_agree(vectorised, loop, observations=len(returns), label=f"{label}, window={window} on {len(returns)} observations")
        values, undefined_windows = vectorised
        assert len(values) == window + 1
        assert values[:window] == [None] * window
        assert values[window] is not None
        assert undefined_windows == 0


def test_an_empty_series_publishes_the_baseline_alone_on_both_paths():
    """A scope with no returns still has a valuation baseline, so the output is ``[None]``.

    Not ``[]``: ``build_line_computation`` zips the values against the price points and
    raises when the lengths differ, so the empty case still owes the caller exactly one
    entry per price point.
    """
    for label, vectorised, loop in _migrated_signal_paths([], 30):
        _assert_rolling_paths_agree(vectorised, loop, observations=0, label=f"{label}, empty series")
        assert vectorised == ([None], 0)


def test_a_window_of_one_refuses_a_dispersion_statistic_on_both_paths():
    """A window of one has no ``ddof=1`` dispersion, and both paths now say so.

    This started life as a FINDING: the loop asked the scalar metric, ``sample_variance``
    REFUSED — "sample variance requires at least two observations" — and the caller got a
    ``ValueError``; the vectorised pass asked pandas, whose ``calc_var`` requires
    ``nobs > ddof`` and therefore answered ``NaN`` for every cell. ``NaN`` is not what the
    undefined test inspects — it tests the denominator, which is the correct design — so
    every cell was published as a VALUE with an undefined count of zero.

    It was not reachable through the API, because ``rolling_volatility``,
    ``rolling_sharpe`` and ``rolling_beta`` all declare ``window: int = Field(..., ge=2)``.
    It was closed anyway, for two reasons. The migration's whole contract is that
    behaviour does not change, and a silent ``NaN`` where the old code raised is a change.
    And the ``NaN`` did not stay silent for long: ``SignalValuePoint.value`` is
    ``Optional[FiniteFloat]``, so it would have surfaced as a Pydantic failure during
    output construction — far from the cause, and unreadable.

    ``rolling_return`` legitimately allows ``ge=1``, and the compounded return IS defined
    on a single observation. That agreement is pinned here too, so closing the dispersion
    case cannot accidentally close the one window of one that must keep working.
    """
    returns = _rolling_sample(5)[:12]
    comparison = [value * 0.7 + 0.0001 for value in returns]

    # The one signal whose window may legitimately be 1, and the two paths agree on it.
    _assert_rolling_paths_agree(rolling_compounded_return_values(returns, 1, scale=100.0), _loop_compounded_return(returns, 1, scale=100.0), observations=len(returns), label="compounded return, window=1")

    # The three dispersion signals refuse, with the same message, on both paths.
    for label, loop_call, vectorised_call in (
        (
            "annualized volatility",
            lambda: _loop_annualized_volatility(returns, 1, _ANNUALIZATION, scale=100.0),
            lambda: rolling_annualized_volatility_values(returns, 1, _ANNUALIZATION, scale=100.0),
        ),
        (
            "annualized sharpe",
            lambda: _loop_annualized_sharpe(returns, 1, _ANNUALIZATION),
            lambda: rolling_annualized_sharpe_values(returns, 1, _ANNUALIZATION),
        ),
        (
            "beta",
            lambda: _loop_beta(returns, comparison, 1),
            lambda: rolling_beta_values(returns, comparison, 1),
        ),
    ):
        with pytest.raises(ValueError, match="at least two observations") as loop_error:
            loop_call()
        with pytest.raises(ValueError, match="at least two observations") as vectorised_error:
            vectorised_call()
        # Same refusal, not merely a matching pattern: the caller cannot tell the paths apart.
        assert str(vectorised_error.value) == str(loop_error.value), label

    # A series too short to hold even one window still short-circuits instead of raising,
    # on both paths: the loop never enters its body, so it never reaches the refusal.
    _assert_rolling_paths_agree(rolling_annualized_sharpe_values([], 1, _ANNUALIZATION), _loop_annualized_sharpe([], 1, _ANNUALIZATION), observations=0, label="annualized sharpe, empty series, window=1")


def test_the_vectorised_compounded_return_refuses_a_total_loss_the_scalar_metric_tolerates():
    """A deliberate, documented narrowing — the one place the two paths part company.

    ``compounded_return`` accepts a return of exactly ``-1`` and answers ``-1``: the
    wealth factor reaches zero and the holding period is a total loss. The vectorised form
    cannot follow it there. ``log1p(-1)`` is ``-inf``, and a rolling accumulator that adds
    then removes ``-inf`` is left with ``NaN`` for every subsequent window — so a single
    wipeout would corrupt values long after the window that contained it had passed.

    Refusing is therefore strictly better than answering, and it costs nothing in
    practice: ``AssetReturnPoint.value`` is declared ``FiniteFloat`` with ``gt=-1``, so a
    prepared series cannot carry ``-1`` in the first place. The guard exists for direct
    callers, and this test exists so that the asymmetry is recorded rather than
    rediscovered.
    """
    wipeout = [0.01, -1.0, 0.02, 0.03]

    # The scalar path compounds it to a total loss without complaint.
    assert compounded_return(wipeout[:2]) == pytest.approx(-1.0)

    with pytest.raises(ValueError, match="finite and greater than -1"):
        rolling_compounded_return_values(wipeout, 2)

    # Non-finite input is refused by both paths, with no disagreement to record.
    with pytest.raises(ValueError):
        rolling_compounded_return_values([0.01, float("nan"), 0.02], 2)
    with pytest.raises(ValueError):
        rolling_compounded_return_values([0.01, float("inf"), 0.02], 2)


def test_the_vectorised_rolling_beta_rejects_series_that_are_not_on_one_joint_calendar():
    """Same guard and same message as ``rolling_pair_values``, and it fires first.

    A length mismatch is a programming error upstream, never something to absorb: a
    silently truncated zip would regress an asset against a benchmark shifted by a day
    and produce an entirely plausible number. The third case is the ordering one — the
    check must not hide behind the ``observations < window`` short-circuit, or a
    misalignment would go unreported for exactly the short series where it is hardest
    to notice.
    """
    with pytest.raises(ValueError, match="aligned"):
        rolling_beta_values([0.01, 0.02, 0.03], [0.01, 0.02], 2)
    with pytest.raises(ValueError, match="aligned"):
        rolling_pair_values([0.01, 0.02, 0.03], [0.01, 0.02], 2, beta)
    with pytest.raises(ValueError, match="aligned"):
        rolling_beta_values([0.01], [0.01, 0.02], 90)


@pytest.mark.parametrize("window", (7, 30))
def test_the_scale_factor_is_applied_inside_the_vectorised_pass_for_both_percent_valued_signals(window):
    """``* 100`` is the entire reason ``scale`` exists, and it must not change anything else.

    ``rolling_return`` and ``rolling_volatility`` publish PERCENT, and since M1 they get
    there by handing the factor to the helper instead of multiplying the returned list.
    Three claims: the scaled result is the unscaled one times a hundred; the default is
    genuinely 1.0 rather than "whatever the plugins happen to pass"; and the factor
    changes neither the ``None`` mask nor the count, which it would if it were applied
    before the undefined test instead of to the result.
    """
    returns = _rolling_sample(1301)

    for label, scaled, unscaled, loop in (
        ("compounded return", rolling_compounded_return_values(returns, window, scale=100.0), rolling_compounded_return_values(returns, window), _loop_compounded_return(returns, window)),
        ("annualized volatility", rolling_annualized_volatility_values(returns, window, _ANNUALIZATION, scale=100.0), rolling_annualized_volatility_values(returns, window, _ANNUALIZATION), _loop_annualized_volatility(returns, window, _ANNUALIZATION)),
    ):
        _assert_rolling_paths_agree(unscaled, loop, observations=len(returns), label=f"{label} at the default scale, window={window}")

        scaled_values, scaled_undefined = scaled
        unscaled_values, unscaled_undefined = unscaled
        assert scaled_undefined == unscaled_undefined == 0
        assert [value is None for value in scaled_values] == [value is None for value in unscaled_values]
        assert [value for value in scaled_values if value is not None] == pytest.approx([value * 100.0 for value in unscaled_values if value is not None], rel=_ROLLING_REL_TOLERANCE, abs=_ROLLING_ABS_TOLERANCE)


@pytest.mark.parametrize("annual_rate", (0.03, 0.0175))
def test_the_risk_free_rate_reaches_the_vectorised_sharpe_and_shifts_every_window_by_the_derivable_amount(annual_rate):
    """The rate must arrive, and it must arrive in the right place — two different claims.

    The first is the differential: with a non-zero rate the vectorised pass still matches
    the loop, so the parameter is not silently dropped on the way into pandas. On its own
    that would also pass if the rate were subtracted twice, or applied to the denominator.

    The second closes that hole algebraically. Subtracting a constant ``rf_daily`` from
    every observation moves the window mean by ``rf_daily`` and leaves the deviation
    untouched, so

        sharpe(0) - sharpe(rf) == rf_daily * sqrt(factor) / deviation
                               == rf_daily * factor / annualized_volatility

    which ties this helper to ``rolling_annualized_volatility_values`` and pins the SIGN
    as well as the magnitude of the shift, window by window.

    HISTORICAL NOTE, kept because it is the record of a blind spot: this docstring used
    to declare the conversion out of scope, saying ``daily_risk_free_rate`` "divides the
    log by 365 while the series is annualized by an observed trading-day factor" and
    calling it "a separately tracked defect". That defect is now fixed — the period count
    is a required argument. What the note got wrong is *why* this test could not see it:
    not the factor, but the phrasing. Every expectation here is written in terms of
    ``daily_risk_free_rate`` itself, so both the defective and the repaired engine satisfy
    them identically. Block (i) sources its expectations from an independent
    pow-based conversion for exactly this reason.
    """
    returns = _rolling_sample(43)
    window = 30
    loop = _loop_annualized_sharpe(returns, window, _ANNUALIZATION, annual_risk_free_rate=annual_rate)
    charged_values, charged_undefined = rolling_annualized_sharpe_values(returns, window, _ANNUALIZATION, annual_risk_free_rate=annual_rate)

    _assert_rolling_paths_agree((charged_values, charged_undefined), loop, observations=len(returns), label=f"sharpe at rf={annual_rate}")

    free_values, _ = rolling_annualized_sharpe_values(returns, window, _ANNUALIZATION)
    volatility_values, _ = rolling_annualized_volatility_values(returns, window, _ANNUALIZATION)
    period_rate = daily_risk_free_rate(annual_rate, _ANNUALIZATION)
    assert period_rate > 0.0

    observed = [free - charged for free, charged in zip(free_values[window:], charged_values[window:], strict=True)]
    expected = [period_rate * _ANNUALIZATION / volatility for volatility in volatility_values[window:]]

    assert observed == pytest.approx(expected, rel=_ROLLING_REL_TOLERANCE, abs=_ROLLING_ABS_TOLERANCE)
    # The rate genuinely moves the signal: at these magnitudes the shift is ~0.07-0.12
    # Sharpe points, so an rf that had been dropped on the way in could not hide here.
    assert min(expected) > 1e-3


# --------------------------------------------------------------------------- #
# Block (h) — M3: the vectorised correlation and covariance matrices.
#
# M3 replaces three ``N x N`` Python loops with three NumPy calls. ``covariance_matrix``
# now delegates to ``np.cov(ddof=1)``, ``correlation_matrix`` to the new private
# ``_vectorised_pearson_matrix``, and the ``correlation`` plugin's own N² loop over
# ``pairwise_correlation`` to the new ``pairwise_correlation_matrix``. The scalar
# functions — ``sample_covariance``, ``pearson_correlation``, ``pairwise_correlation`` —
# are UNCHANGED and remain the executable definition of what the published numbers mean,
# so every test below is differential: the loop body that used to be there, written out
# verbatim, against the call that replaced it, on the same rows.
#
# ⚠️ THE TRAP, and the reason this block exists at all. The undefined test is made on the
# DENOMINATOR — the per-asset sample deviations against ``ZERO_TOLERANCE`` — and NEVER by
# reading ``nan`` back out of ``np.corrcoef``. On an EXACTLY flat series the two readings
# agree, because ``0/0`` is ``nan``, and that agreement is precisely what makes the
# difference so easy to miss. They part company on a series whose dispersion is merely
# NEGLIGIBLE: at ~1e-17 ``np.corrcoef`` divides two perfectly ordinary floats and returns
# a finite, plausible, entirely meaningless number — measured at -0.0201 on one probe —
# where ``pearson_correlation`` returns ``None``. A ``nan``-reading implementation would
# publish that number as a correlation and nothing downstream could tell, because
# ``RiskMatrixCell.value`` is simply ``Optional[float]``: a number is a number. The test
# that documents this is the first one in the block and the most important one in it.
#
# UNIFORMITY IS A THEOREM here, not an optimistic assumption. ``pairwise_correlation_matrix``
# returns ONE observation count and ONE coverage for the whole block instead of one per
# cell, and it is entitled to because the block is dense and rectangular: every pair then
# sees the same observations by construction. The density is not hoped for either —
# ``PreparedAssetSeriesSet`` refuses a set whose members disagree, with "every asset series
# must use the same joint calendar and target currency". The tests still PROVE the
# uniformity cell by cell rather than assuming it, because the day the input stops being
# dense is the day one returned coverage becomes a lie repeated N² times.
#
# GUARD CLAUSES ARE NOT UNIFORM ACROSS THE THREE, ON PURPOSE. A block too short to carry a
# ``ddof=1`` dispersion makes ``covariance_matrix`` and ``correlation_matrix`` RAISE, while
# ``pairwise_correlation_matrix`` RETURNS a matrix of ``None`` — because it mirrors
# ``pairwise_correlation``, whose whole job is to answer "undefined, on this many
# observations, at this coverage" for a pair that is too thin. The plugin then turns that
# into ``RiskValueStatus.INSUFFICIENT`` instead of an error page. That asymmetry is
# deliberate and is pinned below so a later tidy-up cannot "harmonise" it away.
# --------------------------------------------------------------------------- #

# Tolerance for every loop-versus-vectorised comparison in this block, and the reason it
# is neither tighter nor looser.
#
# The scalar path sums with ``math.fsum`` (exactly rounded); NumPy accumulates
# incrementally inside a BLAS product. The two are NOT bit-identical and cannot be made
# so. The worst relative divergence measured while M3 was being made is 1.185e-13, on a
# 20-asset covariance block, and 1.11e-16 absolute on the correlation cells.
#
# ``rel=1e-9`` leaves ~8000x of headroom over that worst case while staying 1000x tighter
# than pytest's default ``rel=1e-6``, so it remains a real constraint: any semantic change
# — ``ddof=0`` instead of 1, a population deviation in the denominator, a transposed
# block — moves a cell by very much more than a part per billion. ``abs=1e-12`` is the
# floor for cells that sit ON zero, where a purely relative bound has stopped meaning
# anything; ``pytest.approx`` takes the LARGER of the two, so on covariance entries of
# ~1e-4 the absolute floor is what actually binds.
#
# DO NOT TIGHTEN: a tighter bound produces a red that is float noise, not a defect.
# DO NOT LOOSEN: a looser bound stops proving the migration preserved the numbers.
_M3_REL_TOLERANCE = 1e-9
_M3_ABS_TOLERANCE = 1e-12

_M3_SEED = 90210
_M3_ASSETS = 6
_M3_OBSERVATIONS = 120
# Deliberately larger than the block, so coverage is 0.8 and not the 1.0 that would hide a
# denominator taken from the wrong place. ``expected_observations`` is the joint calendar's
# length, which the plugin reads from ``prepared_series.n_observations``; the block's own
# width is what the pair actually sees. Equal values make the two indistinguishable.
_M3_EXPECTED_OBSERVATIONS = 150
_M3_NEAR_FLAT_MAGNITUDE = 1e-17
_M3_CONSTANT_VALUE = 0.004
_M3_FLAT_ROW = 1
_M3_SECOND_FLAT_ROW = 4

# The five shapes every differential test in this block runs over, and the row each one
# makes degenerate. "constant-non-zero" is the case people get wrong: a series that is
# 0.004 every single day has a sample deviation of zero exactly like an all-zero one, so
# its correlation with anything — including itself — is UNDEFINED, not 1.0.
_M3_DEGENERATE_ROWS: dict[str, dict[int, str]] = {
    "all-healthy": {},
    "one-exactly-flat": {_M3_FLAT_ROW: "exactly-flat"},
    "one-near-flat": {_M3_FLAT_ROW: "negligibly-dispersed"},
    "two-flat": {_M3_FLAT_ROW: "exactly-flat", _M3_SECOND_FLAT_ROW: "constant-non-zero"},
    "one-constant-non-zero": {_M3_SECOND_FLAT_ROW: "constant-non-zero"},
}
_M3_SCENARIOS = tuple(_M3_DEGENERATE_ROWS)


def _m3_healthy_block(*, count: int = _M3_ASSETS, observations: int = _M3_OBSERVATIONS, seed: int = _M3_SEED) -> list[list[float]]:
    """Return a dense ``(count, observations)`` block of healthy return series.

    One generator drawn once, so the rows of a block are the same rows whatever
    degenerate series is spliced into it afterwards — which is what lets the
    non-contamination tests compare two matrices for BIT equality rather than for
    approximate agreement.
    """
    generator = np.random.default_rng(seed)
    return [[float(value) for value in row] for row in generator.normal(0.0003, 0.010, size=(count, observations))]


def _m3_degenerate_series(kind: str, observations: int) -> list[float]:
    """Return one of the three degenerate series this block distinguishes between.

    ``exactly-flat`` and ``constant-non-zero`` have a sample deviation of zero and are
    undefined on BOTH paths. ``negligibly-dispersed`` is the trap: its deviation is real,
    positive and ~1e-17, which is undefined on the denominator test and a perfectly
    ordinary finite number to ``np.corrcoef``. The alternating sign matters — it keeps the
    mean at zero and gives the row a genuine (and genuinely meaningless) correlation with
    everything else, instead of a rounding artefact that might pass for one.
    """
    if kind == "exactly-flat":
        return [0.0] * observations
    if kind == "constant-non-zero":
        return [_M3_CONSTANT_VALUE] * observations
    if kind == "negligibly-dispersed":
        return [_M3_NEAR_FLAT_MAGNITUDE * (1.0 if index % 2 else -1.0) for index in range(observations)]
    raise ValueError(f"unknown degenerate series kind: {kind}")


def _m3_assert_degenerate_row_is_the_kind_it_claims(kind: str, row: Sequence[float], *, label: str) -> None:
    """Assert a spliced row is degenerate in the SPECIFIC way its name claims.

    The three kinds are not interchangeable, and telling them apart is the entire point of
    the block: two have a deviation of exactly zero, and one has a deviation that is real,
    positive and negligible. Only that third one catches a ``nan``-reading undefined test.
    A fixture that quietly drifted into "all three are basically flat" would leave the trap
    test passing for the wrong reason and nothing would say so, which is why each kind is
    pinned on its own terms here rather than by a shared "is it undefined" check.

    ⚠️ The near-flat deviation is compared with ``rel`` ONLY, deliberately. Its expected
    value is ~1.0042e-17, and ``pytest.approx`` takes the LARGER of the relative and
    absolute bounds — so the block's ``abs=1e-12`` floor would make the comparison accept
    literally any deviation, including zero, and the assertion would prove nothing.
    """
    deviation = sample_standard_deviation(row)
    if kind == "exactly-flat":
        assert deviation == 0.0, f"{label}: an all-zero series must have a deviation of exactly zero, not {deviation}"
        assert math.fsum(row) == 0.0
        return
    if kind == "constant-non-zero":
        # Flat does NOT mean zero. Every day returns 0.4%, the deviation is exactly zero,
        # and the correlation is undefined — this is the case that gets read as "perfectly
        # correlated with everything" by anyone who looks at the mean instead.
        assert deviation == 0.0, f"{label}: a constant series must have a deviation of exactly zero, not {deviation}"
        assert row[0] != 0.0
        assert math.fsum(row) / len(row) == pytest.approx(_M3_CONSTANT_VALUE, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)
        return
    # ±m alternating around a mean of exactly zero: the deviation is m * sqrt(T / (T - 1)),
    # ~1.0042e-17 at T = 120. Strictly positive — this is the row ``np.corrcoef`` answers
    # with an ordinary finite number — and twelve orders of magnitude below the boundary
    # that makes it undefined.
    assert kind == "negligibly-dispersed", f"{label}: unknown degenerate kind {kind}"
    assert deviation == pytest.approx(_M3_NEAR_FLAT_MAGNITUDE * math.sqrt(len(row) / (len(row) - 1)), rel=_M3_REL_TOLERANCE)
    assert 0.0 < deviation <= ZERO_TOLERANCE


def _m3_block(scenario: str, *, observations: int = _M3_OBSERVATIONS) -> list[list[float]]:
    """Return the healthy block with this scenario's rows replaced in place."""
    rows = _m3_healthy_block(observations=observations)
    for index, kind in _M3_DEGENERATE_ROWS[scenario].items():
        rows[index] = _m3_degenerate_series(kind, observations)
    return rows


def _m3_expected_none_cells(scenario: str, *, count: int = _M3_ASSETS) -> int:
    """Return how many cells a scenario must blank, from a closed form rather than a count.

    A flat asset blanks its whole row AND its whole column, so what survives is exactly the
    square sub-block of healthy assets: ``count² - (count - flats)²``. For six assets that
    is 11 cells for one flat asset and 20 for two — not 12 and 24, because the row and the
    column overlap. Deriving it rather than measuring it is the point: an implementation
    that blanked only the row would still produce "some Nones" and pass a laxer test.
    """
    return count**2 - (count - len(_M3_DEGENERATE_ROWS[scenario])) ** 2


def _loop_pairwise_correlation_matrix(rows: Sequence[Sequence[float]], *, expected_observations: int) -> tuple[list[list[float | None]], int, float]:
    """Return the N² loop over ``pairwise_correlation`` that ``pairwise_correlation_matrix`` replaced.

    This is ``correlation.py``'s old inner double loop, verbatim in behaviour: one scalar
    call per cell, each one re-deriving its own observation count and coverage from the two
    series it was handed.

    The collapse of those N² counts into one is asserted, not assumed. On a dense
    rectangular block every pair sees the same observations, so the sets below are
    singletons by arithmetic — and if they are ever not, the single count and coverage the
    new function returns would be a fiction, and this helper must fail before any test
    built on it can pass. Requires a non-empty block; the empty scope has its own test,
    since a loop over nothing cannot produce the count the contract still owes the caller.
    """
    matrix: list[list[float | None]] = []
    observed: set[int] = set()
    covered: set[float] = set()
    for left in rows:
        cells: list[float | None] = []
        for right in rows:
            value, observations, coverage = pairwise_correlation(left, right, expected_observations=expected_observations)
            cells.append(value)
            observed.add(observations)
            covered.add(coverage)
        matrix.append(cells)

    assert len(observed) == 1, f"the reference loop saw {sorted(observed)} observation counts on one dense block: it is not rectangular"
    assert len(covered) == 1, f"the reference loop saw {sorted(covered)} coverages on one dense block: it is not rectangular"
    return matrix, observed.pop(), covered.pop()


def _assert_correlation_matrices_agree(actual: Sequence[Sequence[float | None]], expected: Sequence[Sequence[float | None]], *, label: str) -> None:
    """Assert the vectorised matrix reproduces the reference loop on every axis that matters.

    Six separate claims, deliberately not collapsed into one comparison, because each one
    fails differently:

    1. SHAPE. Square, and the same size as the reference. A transposed or truncated block
       would still be "a matrix of plausible correlations".
    2. The ``None`` MASK, cell by cell. Comparing only the values, or only the COUNT of
       ``None``, would accept a matrix that blanked the right number of the wrong cells —
       which is exactly what a row-only or column-only undefined test produces.
    3. The VALUES, within the migration tolerance documented at the top of the block.
    4. FINITENESS of everything published. ``nan`` and ``inf`` are what a zero denominator
       produces, and ``RiskMatrixCell.value`` would serialise either as a number.
    5. The RANGE. Every published cell is inside ``[-1, 1]``: both paths clamp, and a
       correlation of 1.0000000000000002 in a payload is a support ticket.
    6. SYMMETRY, of the mask and of the values. A Pearson matrix that is not symmetric is
       not a Pearson matrix, and the asymmetry would point at an index swapped in the
       comprehension — the single most likely defect in a rewrite of a double loop.
    """
    assert len(actual) == len(expected), f"{label}: the matrix has {len(actual)} rows against the reference loop's {len(expected)}"
    for index, (actual_row, expected_row) in enumerate(zip(actual, expected, strict=True)):
        assert len(actual_row) == len(actual), f"{label}: row {index} is not square"
        assert len(actual_row) == len(expected_row), f"{label}: row {index} has {len(actual_row)} cells against the reference loop's {len(expected_row)}"
        assert [value is None for value in actual_row] == [value is None for value in expected_row], f"{label}: row {index} blanks different cells than the reference loop"

        published = [value for value in actual_row if value is not None]
        assert all(math.isfinite(value) for value in published), f"{label}: row {index} published a non-finite correlation"
        assert all(-1.0 <= value <= 1.0 for value in published), f"{label}: row {index} published a correlation outside [-1, 1]"
        assert published == pytest.approx([value for value in expected_row if value is not None], rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE), f"{label}: row {index} differs from the reference loop beyond the migration tolerance"

    for i in range(len(actual)):
        for j in range(len(actual)):
            assert (actual[i][j] is None) == (actual[j][i] is None), f"{label}: the undefined mask is not symmetric at ({i}, {j})"
            if actual[i][j] is not None:
                assert actual[i][j] == pytest.approx(actual[j][i], rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE), f"{label}: the matrix is not symmetric at ({i}, {j})"


def test_the_m3_matrix_block_carries_exactly_the_degenerate_rows_every_expectation_below_is_derived_from():
    """Guard the builders: every ``None`` count in this block is DERIVED, not measured.

    The closed form ``count² - (count - flats)²`` is only meaningful while two things hold.
    The rows declared degenerate really are degenerate — each in the specific way its name
    claims, since "flat" and "negligibly dispersed" are the two sides of the trap and must
    not be allowed to become the same fixture by accident. And no OTHER row is accidentally
    flat, which a continuous generator guarantees with probability one: this is a statement
    about the draw, not a hope, and the margin asserted below is twelve orders of magnitude
    away from the undefined boundary.

    The last assertion is the one the non-contamination tests rest on: splicing a degenerate
    row in leaves every other row bit-identical, so two matrices built from two scenarios
    differ by exactly one row of input and nothing else.
    """
    for scenario, degenerate in _M3_DEGENERATE_ROWS.items():
        rows = _m3_block(scenario)
        assert len(rows) == _M3_ASSETS
        assert all(len(row) == _M3_OBSERVATIONS for row in rows), f"{scenario}: the block is not rectangular"

        for index, row in enumerate(rows):
            deviation = sample_standard_deviation(row)
            if index in degenerate:
                assert deviation <= ZERO_TOLERANCE, f"{scenario}: row {index} was supposed to be undefined, its deviation is {deviation}"
                _m3_assert_degenerate_row_is_the_kind_it_claims(degenerate[index], row, label=f"{scenario} row {index}")
                continue
            # Healthy rows are drawn at scale 0.010, so this is a 10x margin on the sample
            # deviation and a 1e12 margin on the boundary that would make one undefined.
            assert deviation > 1e-3, f"{scenario}: healthy row {index} is degenerate at {deviation}"

    assert _m3_expected_none_cells("all-healthy") == 0
    assert _m3_expected_none_cells("one-exactly-flat") == _m3_expected_none_cells("one-near-flat") == _m3_expected_none_cells("one-constant-non-zero") == 11
    assert _m3_expected_none_cells("two-flat") == 20

    healthy = _m3_block("all-healthy")
    for scenario, degenerate in _M3_DEGENERATE_ROWS.items():
        rows = _m3_block(scenario)
        for index in range(_M3_ASSETS):
            if index not in degenerate:
                assert rows[index] == healthy[index], f"{scenario}: splicing moved healthy row {index}, so no two scenarios are comparable"


def test_a_negligibly_dispersed_series_is_undefined_because_the_denominator_says_so_and_not_because_numpy_said_nan():
    """THE test of this block: the vectorised path must not learn "undefined" from ``nan``.

    ``_vectorised_pearson_matrix`` tests the per-asset sample deviations against
    ``ZERO_TOLERANCE`` and blanks a row and column on that reading alone. It would have
    been shorter to call ``np.corrcoef`` and blank wherever the result is ``nan``, and on
    every fixture anybody would have written by hand the two are indistinguishable — an
    all-zero series produces ``0/0`` and ``nan`` falls out on its own.

    They are not the same test. A series of ±1e-17 has a dispersion that is REAL,
    positive and utterly negligible: ``np.corrcoef`` divides two perfectly normal floats
    (a variance of 1e-34 is nowhere near underflow) and returns a finite number of ordinary
    magnitude — ~0.02 to 0.2, the correlation of an alternating sign pattern with the other
    asset's returns. It is arithmetically correct and financially meaningless, and a
    ``nan``-reading implementation publishes it as a correlation, in a cell whose status
    says OK, next to five real ones.

    So this test asserts both halves: that the shipped path says ``None``, and that the
    naive one would NOT have — otherwise it would only be pinning an outcome, and the next
    person to simplify the function would find nothing standing in the way. The last block
    shows why the trap hides so well: on an exactly flat series the naive reading is right.
    """
    rows = _m3_block("one-near-flat")
    near_flat = rows[_M3_FLAT_ROW]
    survivors = [index for index in range(_M3_ASSETS) if index != _M3_FLAT_ROW]
    sample = np.asarray(rows, dtype="float64")

    # 1. The boundary. Dispersion EXISTS here; it is simply negligible — and the scalar and
    #    vectorised readings of it agree, which is the precondition for everything else.
    assert 0.0 < sample_standard_deviation(near_flat) <= ZERO_TOLERANCE
    assert 0.0 < float(sample.std(axis=1, ddof=1)[_M3_FLAT_ROW]) <= ZERO_TOLERANCE
    assert ZERO_TOLERANCE == 1e-15

    # 2. The scalar reference — unchanged by M3 — calls every pair undefined.
    for index in survivors:
        assert pearson_correlation(near_flat, rows[index]) is None
        assert pairwise_correlation(near_flat, rows[index], expected_observations=_M3_EXPECTED_OBSERVATIONS)[0] is None
    assert pearson_correlation(near_flat, near_flat) is None

    # 3. ...and so do both vectorised entry points, over the whole row and column.
    matrix, observations, coverage = pairwise_correlation_matrix(rows, expected_observations=_M3_EXPECTED_OBSERVATIONS)
    assert matrix[_M3_FLAT_ROW] == [None] * _M3_ASSETS
    assert [row[_M3_FLAT_ROW] for row in matrix] == [None] * _M3_ASSETS
    assert all(matrix[i][j] is not None for i in survivors for j in survivors)
    assert correlation_matrix(rows)[_M3_FLAT_ROW] == [None] * _M3_ASSETS
    # Not thin on data in any way: it is 120 observations of nothing at all.
    assert observations == _M3_OBSERVATIONS
    assert coverage == pytest.approx(_M3_OBSERVATIONS / _M3_EXPECTED_OBSERVATIONS, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)

    # 4. THE TRAP, executable. What a nan-reading implementation would have published.
    with np.errstate(invalid="ignore", divide="ignore"):
        naive = np.corrcoef(sample)
    nan_reader_row = [None if math.isnan(value) else float(value) for value in naive[_M3_FLAT_ROW]]
    assert None not in nan_reader_row, "np.corrcoef produced a nan for the near-flat row: the fixture no longer demonstrates the trap"
    assert all(math.isfinite(value) for value in nan_reader_row)
    # Not a rounding artefact either: at least one of these is a correlation a human would
    # read straight off the chart and believe. The measured probe value was -0.0201.
    assert max(abs(value) for index, value in enumerate(nan_reader_row) if index != _M3_FLAT_ROW) > 1e-3

    # 5. Why the trap hides: on an EXACTLY flat series the two readings DO agree, so every
    #    obvious fixture passes either way and only the 1e-17 case tells them apart.
    exactly_flat_rows = _m3_block("one-exactly-flat")
    with np.errstate(invalid="ignore", divide="ignore"):
        naive_flat = np.corrcoef(np.asarray(exactly_flat_rows, dtype="float64"))
    assert all(math.isnan(float(value)) for value in naive_flat[_M3_FLAT_ROW])
    assert correlation_matrix(exactly_flat_rows)[_M3_FLAT_ROW] == [None] * _M3_ASSETS


@pytest.mark.parametrize("scenario", _M3_SCENARIOS)
def test_pairwise_correlation_matrix_reproduces_the_pairwise_correlation_loop_cell_by_cell(scenario):
    """The new function against the N² loop it replaced in ``correlation.py``, on five shapes.

    This is the whole contract of M3 in one assertion set: same values, same ``None``
    placement, same observation count, same coverage. The loop is the semantics — it is
    built from ``pairwise_correlation``, which M3 did not touch — so any divergence here is
    a published number moving, not a difference of opinion.

    The five scenarios are not decoration. All-healthy proves the ordinary path; one
    exactly flat proves the ``nan`` case; one near-flat proves the 1e-17 case the ``nan``
    case hides; two flat proves that the row-and-column blanking composes rather than
    overlapping wrongly (20 cells, not 22); one constant non-zero proves that flat means
    zero DISPERSION and not zero VALUE.
    """
    rows = _m3_block(scenario)
    matrix, observations, coverage = pairwise_correlation_matrix(rows, expected_observations=_M3_EXPECTED_OBSERVATIONS)
    expected_matrix, expected_observations, expected_coverage = _loop_pairwise_correlation_matrix(rows, expected_observations=_M3_EXPECTED_OBSERVATIONS)

    _assert_correlation_matrices_agree(matrix, expected_matrix, label=f"pairwise matrix, {scenario}")
    assert sum(1 for row in matrix for value in row if value is None) == _m3_expected_none_cells(scenario), f"{scenario}: the blanked cells are not the row-and-column of the degenerate assets"

    # Identical to the loop's, and identical to the derived values: the second half matters
    # because the loop and the function could agree on a denominator both took from the
    # wrong place — the block's width instead of the joint calendar's, most plausibly.
    assert observations == expected_observations == _M3_OBSERVATIONS
    assert coverage == expected_coverage
    assert coverage == pytest.approx(_M3_OBSERVATIONS / _M3_EXPECTED_OBSERVATIONS, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)

    # The diagonal of a healthy asset is 1.0 to floating point and NEVER exactly 1.0 on
    # either path: it is ``cov(x, x) / (sd * sd)`` and ``sqrt(v) * sqrt(v)`` is not
    # bit-identically ``v``. Both paths clamp, so it can be below 1.0 but never above.
    for index in range(_M3_ASSETS):
        if matrix[index][index] is not None:
            assert matrix[index][index] <= 1.0
            assert matrix[index][index] == pytest.approx(1.0, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)


@pytest.mark.parametrize("scenario", _M3_SCENARIOS)
def test_correlation_matrix_reproduces_the_pearson_double_loop_it_replaced(scenario):
    """``correlation_matrix`` against its own former body, which is still importable.

    The body deleted by M3 was literally
    ``[[pearson_correlation(left, right) for right in rows] for left in rows]``, so the
    reference below is not a re-derivation of the mathematics — it IS the old
    implementation, and ``pearson_correlation`` is unchanged. A red here is a behaviour
    change, with no interpretation required.
    """
    rows = _m3_block(scenario)
    matrix = correlation_matrix(rows)
    expected = [[pearson_correlation(left, right) for right in rows] for left in rows]

    _assert_correlation_matrices_agree(matrix, expected, label=f"correlation matrix, {scenario}")
    assert sum(1 for row in matrix for value in row if value is None) == _m3_expected_none_cells(scenario)

    # The two vectorised entry points share ``_vectorised_pearson_matrix``, so they must not
    # be able to disagree — the plugin publishes one of them and every other caller the
    # other, and a divergence would show up as two different matrices for the same assets.
    pairwise_matrix, _, _ = pairwise_correlation_matrix(rows, expected_observations=_M3_EXPECTED_OBSERVATIONS)
    assert pairwise_matrix == matrix


def test_covariance_matrix_reproduces_the_sample_covariance_double_loop_it_replaced():
    """``np.cov(ddof=1)`` against the scalar loop, on a block that contains flat assets.

    Three claims, and the third is the one that separates covariance from correlation.

    The entries agree with ``sample_covariance`` within the migration tolerance — NOT
    exactly, and asserting equality here would be wrong: ``sample_covariance`` sums with
    ``math.fsum`` while ``np.cov`` accumulates inside a BLAS product. The worst relative
    divergence measured on a 20-asset block was 1.185e-13, which at these magnitudes
    (~1e-4) is ~1e-17 absolute, three orders inside the floor.

    The diagonal is the scalar variance, which is what makes the matrix usable as a risk
    model at all.

    And a flat asset contributes a row of ZEROS, not a row of ``None``. Covariance with a
    constant is genuinely zero — the quantity is defined, it just carries no information —
    whereas the CORRELATION is undefined because its denominator vanishes. Conflating the
    two would either blank a covariance row that ``risk_contributions_from_covariance``
    needs (it would then raise on a non-finite entry) or publish a correlation of 0.0 for a
    pair that has none, which reads as "these two are unrelated" instead of "we cannot say".
    """
    rows = _m3_block("two-flat")
    matrix = covariance_matrix(rows)
    expected = [[sample_covariance(left, right) for right in rows] for left in rows]

    assert len(matrix) == len(rows)
    for index, row in enumerate(matrix):
        assert len(row) == len(rows)
        assert all(math.isfinite(value) for value in row), f"row {index} published a non-finite covariance"
        assert row == pytest.approx(expected[index], rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)

    for index, row in enumerate(rows):
        assert matrix[index][index] == pytest.approx(sample_variance(row), rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)

    for index in (_M3_FLAT_ROW, _M3_SECOND_FLAT_ROW):
        assert matrix[index] == pytest.approx([0.0] * _M3_ASSETS, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)
        assert [row[index] for row in matrix] == pytest.approx([0.0] * _M3_ASSETS, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)
        assert all(value is not None for value in matrix[index])


def test_the_vectorised_covariance_matrix_still_passes_the_symmetry_gate_of_the_analytic_that_consumes_it():
    """Symmetry is not cosmetic here: the only consumer REFUSES a matrix that lacks it.

    ``risk_contribution.py`` hands ``covariance_matrix(rows)`` straight to
    ``risk_contributions_from_covariance``, which tests
    ``math.isclose(m[i][j], m[j][i], rel_tol=1e-12, abs_tol=1e-15)`` on every pair and
    raises "covariance matrix must be symmetric" if one fails. That gate is far tighter
    than this block's own tolerance — at entries of ~1e-4 it allows ~1e-16 — so the
    assertion below is written with the CONSUMER's constants rather than the migration's.
    Anything else would pass a matrix the analytic then rejects at runtime, and the failure
    would surface as an unavailable risk contribution with no hint of where it came from.
    """
    rows = _m3_block("two-flat")
    matrix = covariance_matrix(rows)

    for i in range(len(matrix)):
        for j in range(len(matrix)):
            assert math.isclose(matrix[i][j], matrix[j][i], rel_tol=1e-12, abs_tol=1e-15), f"({i}, {j}) breaks the symmetry gate: {matrix[i][j]!r} against {matrix[j][i]!r}"

    # And the gate really is reachable: the analytic accepts this exact matrix and produces
    # a decomposition, rather than raising on it.
    summary = risk_contributions_from_covariance(matrix, [1.0 / _M3_ASSETS] * _M3_ASSETS, annualization_factor=_ANNUALIZATION)
    assert summary.portfolio_volatility > 0.0
    assert len(summary.percentage) == _M3_ASSETS
    assert math.fsum(summary.percentage) == pytest.approx(1.0, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)
    # The two flat assets contribute exactly nothing, which is the honest answer for an
    # asset with no variance and no covariance — and not something the gate above can see.
    assert summary.component[_M3_FLAT_ROW] == pytest.approx(0.0, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)
    assert summary.component[_M3_SECOND_FLAT_ROW] == pytest.approx(0.0, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)


@pytest.mark.parametrize("scenario", ("one-exactly-flat", "one-near-flat", "one-constant-non-zero"))
def test_a_degenerate_asset_never_moves_a_correlation_between_the_assets_that_stayed_healthy(scenario):
    """A flat asset blanks its own row and column and touches NOTHING else — bit for bit.

    This is the property that makes a per-asset undefined mask safe. ``np.corrcoef``
    normalises each pair by its own two deviations, so a ``nan`` cannot propagate sideways;
    and the mask is applied cell by cell after the fact, so it cannot blank a neighbour
    either. Measured while M3 was being made: introducing a flat asset moved every other
    cell by EXACTLY 0.0, which is why the comparison below is ``==`` and not ``approx``.

    Both scenarios compared here are built from the same seeded block with one row replaced,
    so the matrices have identical dimensions and differ by exactly one row of input. That
    is deliberate: it removes the only other thing that could have moved a cell, and makes
    the exact comparison a statement about contamination instead of about BLAS.

    The near-flat scenario is the sharp one. There is no ``nan`` anywhere in that matrix —
    ``np.corrcoef`` returns six finite rows — so the confinement being tested is entirely
    the work of the deviation mask, not a side effect of how ``nan`` happens to spread.
    """
    baseline = correlation_matrix(_m3_block("all-healthy"))
    contaminated = correlation_matrix(_m3_block(scenario))
    (flat_row,) = _M3_DEGENERATE_ROWS[scenario]
    survivors = [index for index in range(_M3_ASSETS) if index != flat_row]

    assert all(value is not None for row in baseline for value in row), "the healthy baseline is already blanked somewhere: the comparison would be meaningless"
    assert contaminated[flat_row] == [None] * _M3_ASSETS
    assert [row[flat_row] for row in contaminated] == [None] * _M3_ASSETS

    drift = max(abs(contaminated[i][j] - baseline[i][j]) for i in survivors for j in survivors)
    assert drift == 0.0, f"{scenario}: a degenerate asset moved a healthy correlation by {drift}"


def test_adding_a_flat_asset_to_a_set_leaves_every_correlation_between_the_existing_assets_untouched():
    """The user-facing shape of the same claim: add an asset, the rest of the matrix holds still.

    Adding a money-market line whose NAV never moves is an ordinary thing to do, and if it
    silently shifted the other fifteen correlations in the panel the report would be
    unreproducible from one day to the next. The matrix here grows from 6x6 to 7x7, so this
    is the case the previous test deliberately does not cover: same rows, different block
    dimensions, and the existing sub-block must come out identical anyway.
    """
    healthy = _m3_block("all-healthy")
    baseline = correlation_matrix(healthy)
    extended = correlation_matrix([*healthy, _m3_degenerate_series("exactly-flat", _M3_OBSERVATIONS)])

    assert len(extended) == _M3_ASSETS + 1
    assert extended[_M3_ASSETS] == [None] * (_M3_ASSETS + 1)
    assert [row[_M3_ASSETS] for row in extended] == [None] * (_M3_ASSETS + 1)

    drift = max(abs(extended[i][j] - baseline[i][j]) for i in range(_M3_ASSETS) for j in range(_M3_ASSETS))
    assert drift == 0.0, f"a flat seventh asset moved an existing correlation by {drift}"


@pytest.mark.parametrize(("count", "observations", "expected"), ((2, 2, 2), (3, 45, 45), (6, 120, 150), (4, 30, 1000)))
def test_the_observation_count_and_the_coverage_are_uniform_over_a_dense_block_which_is_why_they_are_returned_once(count, observations, expected):
    """Returning one count for N² cells is only honest while the block is rectangular.

    The old loop asked ``pairwise_correlation`` per cell and got N² answers, of which the
    plugin wrote the same value into every ``RiskMatrixCell``. M3 computes it once. That is
    a theorem on a dense block — every pair sees every observation, so the count is the
    block's width and the coverage is that width over the joint calendar — but it is a
    theorem about the INPUT, and the input is what a future caller might change. So the N²
    answers are recomputed here and collapsed into a set: one element, equal to what the
    function returned once.

    The four shapes cover the boundaries that matter: the smallest block a ``ddof=1``
    statistic accepts at all (2 assets, 2 observations) where coverage is exactly 1.0, a
    full-coverage block of ordinary width, the partial-coverage block the rest of this
    section uses, and a deliberately sparse 3% coverage where a denominator taken from the
    block instead of the calendar would be off by a factor of thirty.
    """
    rows = _m3_healthy_block(count=count, observations=observations)
    matrix, returned_observations, returned_coverage = pairwise_correlation_matrix(rows, expected_observations=expected)

    per_cell = {pairwise_correlation(left, right, expected_observations=expected)[1:] for left in rows for right in rows}
    assert len(per_cell) == 1, f"the loop disagreed with itself across cells: {sorted(per_cell)}"
    assert per_cell.pop() == (returned_observations, returned_coverage)

    assert returned_observations == observations
    assert returned_coverage == observations / expected
    assert len(matrix) == count
    assert all(len(row) == count for row in matrix)


def test_an_empty_scope_is_answered_rather_than_refused_by_all_three_matrix_builders():
    """No assets is not an error, and the empty coverage is 0.0 rather than 1.0 or a crash.

    ``correlation.py`` reads the returned coverage before it knows whether the scope has
    any assets, and guards with ``bool(asset_ids) and coverage < min_coverage`` precisely
    because the empty answer is 0.0 and must not be reported as low coverage. The shape of
    the empty answer is therefore part of the contract, not an implementation detail: an
    empty LIST for the two matrix builders, and the full ``(matrix, observations, coverage)``
    triple for the pairwise one, so its caller can unpack it unconditionally.
    """
    assert covariance_matrix([]) == []
    assert correlation_matrix([]) == []
    assert pairwise_correlation_matrix([], expected_observations=_M3_EXPECTED_OBSERVATIONS) == ([], 0, 0.0)
    # Even with nothing to divide by, the empty case short-circuits before the coverage is
    # computed at all, so there is no ZeroDivisionError hiding behind a rare scope.
    assert pairwise_correlation_matrix([], expected_observations=0) == ([], 0, 0.0)


def test_the_three_matrix_builders_disagree_on_purpose_about_a_block_too_short_to_carry_a_dispersion():
    """One observation: two builders raise, the third answers ``None``. Both answers are right.

    ``covariance_matrix`` and ``correlation_matrix`` are primitives handed a block that
    cannot produce a ``ddof=1`` statistic; refusing is the only honest answer, and it is
    what they did before M3.

    ``pairwise_correlation_matrix`` mirrors ``pairwise_correlation`` instead, which answers
    ``(None, observations, coverage)`` for a pair that is too thin — because "we only have
    one day in common" is an ordinary data condition, not a programming error, and the
    plugin turns it into ``RiskValueStatus.INSUFFICIENT`` cells plus an
    ``insufficient_pair_history`` warning. Raising there would replace a legible, partially
    populated panel with an error.

    Note what is NOT skipped in the thin case: the count and the coverage still come back,
    because the plugin compares them against ``min_observations`` and ``min_coverage`` to
    choose the status. A short-circuit that returned zeros would silently mark every cell
    insufficient for the wrong reason.
    """
    rows = [[0.01], [0.02], [0.015]]

    with pytest.raises(ValueError, match="covariance matrix requires at least two observations"):
        covariance_matrix(rows)
    with pytest.raises(ValueError, match="correlation matrix requires at least two observations"):
        correlation_matrix(rows)

    matrix, observations, coverage = pairwise_correlation_matrix(rows, expected_observations=4)
    assert matrix == [[None] * 3 for _ in range(3)]
    assert observations == 1
    assert coverage == pytest.approx(0.25, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)
    # Exactly what the scalar it replaced answers for the same pair, triple for triple.
    assert pairwise_correlation(rows[0], rows[1], expected_observations=4) == (None, 1, coverage)

    # A block of empty series is the same case with nothing in it, and it must not divide.
    empty_rows, empty_observations, empty_coverage = pairwise_correlation_matrix([[], []], expected_observations=10)
    assert empty_rows == [[None, None], [None, None]]
    assert empty_observations == 0
    assert empty_coverage == 0.0
    assert pairwise_correlation([], [], expected_observations=10) == (None, 0, 0.0)
    with pytest.raises(ValueError, match="covariance matrix requires at least two observations"):
        covariance_matrix([[], []])


def test_every_matrix_builder_refuses_a_block_that_is_not_one_common_calendar():
    """A ragged block is a programming error upstream, never something to average over.

    All three builders index their rows positionally, so a shorter series would silently be
    correlated against a neighbour's returns shifted by however many days it is missing —
    and produce an entirely plausible number. ``PreparedAssetSeriesSet`` makes this
    unreachable through the API ("every asset series must use the same joint calendar and
    target currency"), which is exactly why the guard has to be tested here: nothing else
    exercises it.

    The second half pins an ordering the three do NOT share, and it is intentional in both
    directions. Handed a block that is ragged AND too short, ``covariance_matrix`` reports
    the width first, while ``pairwise_correlation_matrix`` checks the calendar first — it
    has to, because its answer to a short block is a matrix of ``None`` rather than an
    exception, so a raggedness left unchecked would be returned as a result instead of
    raised. Swapping those two lines turns a misalignment into a silently thin panel.
    """
    ragged = [[0.01, -0.02, 0.03], [0.01, -0.02]]

    with pytest.raises(ValueError, match="all return series must share one common calendar"):
        covariance_matrix(ragged)
    with pytest.raises(ValueError, match="all return series must share one common calendar"):
        correlation_matrix(ragged)
    with pytest.raises(ValueError, match="all return series must share one common calendar"):
        pairwise_correlation_matrix(ragged, expected_observations=3)

    ragged_and_short = [[0.01], [0.01, 0.02]]
    with pytest.raises(ValueError, match="covariance matrix requires at least two observations"):
        covariance_matrix(ragged_and_short)
    with pytest.raises(ValueError, match="all return series must share one common calendar"):
        pairwise_correlation_matrix(ragged_and_short, expected_observations=3)

    # And the finiteness guard is still the shared one, with the shared message.
    with pytest.raises(ValueError, match="return series must be finite"):
        pairwise_correlation_matrix([[0.01, float("nan")], [0.01, 0.02]], expected_observations=2)
    with pytest.raises(ValueError, match="return series must be finite"):
        covariance_matrix([[0.01, float("inf")], [0.01, 0.02]])


def test_expected_observations_is_validated_before_anything_else_and_a_zero_denominator_is_not_an_error():
    """The denominator is checked FIRST, and zero is a legal denominator meaning zero coverage.

    Order matters because the message is the only diagnostic the caller gets. The negative
    check is the first statement in the function, so a block that would also fail the
    finiteness and calendar guards still reports the denominator — the one thing the caller
    passed in themselves and can actually fix.

    Zero is a different case entirely and must NOT raise: an empty joint calendar is what a
    scope with no overlapping history has, and ``coverage = 0.0`` is the truthful answer.
    Dividing anyway would be a ZeroDivisionError on a data condition. The matrix is still
    computed and still published, because the cells are perfectly well defined — it is only
    their share of a calendar that has no length that is not.
    """
    rows = _m3_block("all-healthy")

    with pytest.raises(ValueError, match="expected_observations cannot be negative"):
        pairwise_correlation_matrix(rows, expected_observations=-1)
    with pytest.raises(ValueError, match="expected_observations cannot be negative"):
        pairwise_correlation_matrix([[float("nan"), 1.0], [1.0]], expected_observations=-1)
    with pytest.raises(ValueError, match="expected_observations cannot be negative"):
        pairwise_correlation(rows[0], rows[1], expected_observations=-1)

    matrix, observations, coverage = pairwise_correlation_matrix(rows, expected_observations=0)
    expected_matrix, expected_observations, expected_coverage = _loop_pairwise_correlation_matrix(rows, expected_observations=0)

    assert coverage == expected_coverage == 0.0
    assert observations == expected_observations == _M3_OBSERVATIONS
    _assert_correlation_matrices_agree(matrix, expected_matrix, label="pairwise matrix at zero expected observations")
    # The correlations are untouched by the denominator: same block, same cells.
    assert matrix == pairwise_correlation_matrix(rows, expected_observations=_M3_EXPECTED_OBSERVATIONS)[0]


def test_a_single_asset_block_survives_the_numpy_dimension_collapse_that_would_otherwise_lose_the_matrix():
    """N=1 is where NumPy stops returning a matrix, and ``np.atleast_2d`` is the whole defence.

    ``np.cov`` ends on ``return c.squeeze()``: handed one row it returns a 0-D array — a
    bare variance, not a 1x1 matrix. ``np.corrcoef`` then cannot take a diagonal of a 0-D
    array, catches the ``ValueError`` and returns ``c / c``, which is a 0-D 1.0 (or ``nan``
    for a flat series). Without ``atleast_2d``, ``.tolist()`` on either would produce a
    FLOAT where the caller expects ``list[list[float]]``, and the failure would land two
    layers away, inside a comprehension indexing a float.

    A single-asset scope is not exotic: ``supported_scopes`` includes ``ASSET_SET``, and a
    set of one is a legal selection in the UI. The assertions therefore pin both the shape
    (1x1, nested) and the content, and the last pair pins that the single-asset diagonal is
    still decided by the deviation — a lone flat asset is ``None``, not a confident 1.0.
    """
    row = _m3_healthy_block(count=1)[0]
    sample = np.asarray([row], dtype="float64")

    # The collapse is real. If either of these ever stops being 0-D, the ``atleast_2d``
    # calls become dead weight — but until then they are the only thing holding the shape.
    assert np.ndim(np.cov(sample, ddof=1)) == 0
    assert np.ndim(np.corrcoef(sample)) == 0
    assert float(np.corrcoef(sample)) == pytest.approx(1.0, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)

    covariance = covariance_matrix([row])
    assert len(covariance) == 1
    assert len(covariance[0]) == 1
    assert covariance[0][0] == pytest.approx(sample_variance(row), rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)

    correlation = correlation_matrix([row])
    assert len(correlation) == 1
    assert len(correlation[0]) == 1
    assert correlation[0][0] is not None
    assert correlation[0][0] <= 1.0
    assert correlation[0][0] == pytest.approx(1.0, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)

    matrix, observations, coverage = pairwise_correlation_matrix([row], expected_observations=_M3_EXPECTED_OBSERVATIONS)
    assert matrix == correlation
    assert observations == _M3_OBSERVATIONS
    assert coverage == pytest.approx(_M3_OBSERVATIONS / _M3_EXPECTED_OBSERVATIONS, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)
    assert pairwise_correlation(row, row, expected_observations=_M3_EXPECTED_OBSERVATIONS)[1:] == (observations, coverage)

    # One asset, no dispersion: the shape survives and the undefined test still decides.
    flat = _m3_degenerate_series("exactly-flat", _M3_OBSERVATIONS)
    assert correlation_matrix([flat]) == [[None]]
    assert pairwise_correlation_matrix([flat], expected_observations=_M3_EXPECTED_OBSERVATIONS)[0] == [[None]]
    flat_covariance = covariance_matrix([flat])
    assert len(flat_covariance) == 1
    assert len(flat_covariance[0]) == 1
    # Still a NUMBER, not a None: the covariance of a constant is zero, only its
    # correlation is undefined. The two degeneracies are not the same degeneracy.
    assert flat_covariance[0][0] == pytest.approx(0.0, rel=_M3_REL_TOLERANCE, abs=_M3_ABS_TOLERANCE)


# --------------------------------------------------------------------------- #
# Block (i) — the risk-free rate must be charged in the period the series is
# annualized over.
#
# ``daily_risk_free_rate`` used to divide the annual log by a hardcoded ``365.0`` while
# the returns series is annualized by an OBSERVED factor. Numerator and denominator then
# spoke of different periods: on a 261-trading-day year a user who typed 5% was charged
# 3.55%, and every Sharpe and Sortino computed with a non-zero rate came out flattered.
# The second parameter exists to make that mismatch unrepresentable.
#
# WHY THIS BLOCK HAD TO BE WRITTEN AT ALL. The defect was invisible to the entire suite:
# ``services risk-all`` was 292 passed both before and after the repair, not one test
# moved. Every pre-existing expectation is phrased in terms of ``daily_risk_free_rate``
# itself — including the rolling-Sharpe identity in block (g), whose docstring says out
# loud that the conversion is "OUT OF SCOPE" — and an expectation phrased with the
# function under test is satisfied by ANY conversion that function happens to implement,
# correct or not. Self-consistency is not correctness, and a suite that only ever checks
# self-consistency cannot see a units error.
#
# Hence the standing rule for everything below: NEVER phrase an expectation with
# ``daily_risk_free_rate``. Either compound the per-period rate back up and check it
# returns the annual rate the user asked for, or derive the charge from
# ``_compounding_period_rate``, which reaches the same number through ``pow`` and shares
# no code with the subject. Where a test needs to show what the old engine produced, it
# reconstructs it inline from ``_reverted_calendar_day_rate`` rather than trusting any
# remembered magnitude.
# --------------------------------------------------------------------------- #

_RF_CALENDAR_FACTOR = 365.0
_RF_TRADING_FACTOR = 261.0
# 261 and 252 are the two trading-day conventions LibreFolio actually annualizes with, 12
# is a monthly series, and 365 is the calendar case that must not move. 261 is used as
# the default probe precisely because it is NOT 365: at 365 the repaired and the reverted
# conversions are the same function, so a test written there proves nothing about either.
_RF_FACTORS = (_RF_CALENDAR_FACTOR, _RF_TRADING_FACTOR, 252.0, 12.0)
_RF_RATES = (0.01, 0.02, 0.05)

# Cross-implementation tolerance. ``(1 + r) ** (1 / f) - 1`` and ``expm1(log1p(r) / f)``
# are the same number in exact arithmetic and different code paths in floating point: the
# first subtracts near 1.0 and loses a few bits to cancellation. Measured worst relative
# separation over factors {4, 12, 52, 252, 261, 365} x rates {0.1% ... 25%} is 2.6e-11,
# and the round trip through ``pow`` lands within 2.0e-12 of the requested annual rate.
#
# DO NOT TIGHTEN to 1e-12: that is BELOW the measured separation and the red it produced
# would be float noise, not a defect. Nothing is lost by respecting this bound — the
# mis-conversion this block hunts is a ~28% error at 261, nine orders of magnitude away.
_RF_REL_TOLERANCE = 1e-9
_RF_ABS_TOLERANCE = 1e-12
# Same-library algebra: the helpers below replay the subject's own body with the subject's
# own arithmetic, so agreement is expected down to the last bits.
_RF_ALGEBRA_REL_TOLERANCE = 1e-12


def _reverted_calendar_day_rate(annual_rate: float) -> float:
    """Return the PRE-FIX conversion verbatim: the annual log spread over 365 calendar days.

    Kept as executable code rather than as a table of remembered constants, so the tests
    that contrast the two conversions state the old behaviour exactly instead of quoting
    a magnitude that could drift out of date. This is the formula every assertion in this
    block must be able to tell apart from the real one.
    """
    return math.expm1(math.log1p(annual_rate) / 365.0)


def _compounding_period_rate(annual_rate: float, periods_per_year: float) -> float:
    """Return the per-period rate that compounds to ``annual_rate``, derived independently.

    This is the definition of the thing ``daily_risk_free_rate`` computes, reached through
    ``pow`` instead of ``expm1``/``log1p``. It exists so an expectation can be written
    WITHOUT calling the subject: an identity phrased with the function under test holds
    whatever that function does, which is exactly how the units error survived 292 green
    tests. Agreement is to ``_RF_REL_TOLERANCE``, not to the bit — see the note there.
    """
    return (1.0 + annual_rate) ** (1.0 / periods_per_year) - 1.0


def _sharpe_charged_at(returns: Sequence[float], annualization_factor: float, period_rate: float) -> float:
    """Replay ``annualized_sharpe``'s body against an EXPLICIT per-period charge.

    Same operations in the same order as the subject, so handing it the subject's own rate
    reproduces the subject bit for bit; handing it ``_reverted_calendar_day_rate`` rebuilds
    the engine as it behaved before the repair. That is what lets a test measure the
    flattery the fix removed without depending on a recorded number.
    """
    excess_mean = math.fsum(value - period_rate for value in returns) / len(returns)
    return excess_mean / sample_standard_deviation(returns) * math.sqrt(annualization_factor)


def _sortino_charged_at(returns: Sequence[float], annualization_factor: float, target_rate: float) -> float:
    """Replay ``annualized_sortino``'s body against an EXPLICIT per-period target.

    Note where ``target_rate`` appears: once inside the downside variance and once in the
    excess mean. That double appearance is not a detail of this helper, it is the subject's
    structure, and it is the mechanism test below.
    """
    downside_deviation = math.sqrt(math.fsum(min(value - target_rate, 0.0) ** 2 for value in returns) / len(returns))
    excess_mean = math.fsum(value - target_rate for value in returns) / len(returns)
    return excess_mean / downside_deviation * math.sqrt(annualization_factor)


@pytest.mark.parametrize("annual_rate", _RF_RATES)
@pytest.mark.parametrize("periods_per_year", _RF_FACTORS)
def test_the_per_period_risk_free_rate_compounds_back_to_the_annual_rate_the_user_actually_asked_for(periods_per_year, annual_rate):
    """The round trip IS the definition: compound the charge over a year and get the rate back.

    Everything else in this block is a consequence of this one property. A per-period
    risk-free rate is meaningful only relative to a period count, and the only statement
    that fixes it is that ``periods_per_year`` of them compound to the annual figure the
    user typed. Written this way the assertion never mentions the subject's internals, so
    it holds across any reimplementation that is correct and fails every one that is not.

    The second half records what the pre-fix engine did with the same input, because "5%
    became 3.55%" is the sentence that makes this a user-facing defect rather than a
    rounding quibble. At 365 the two conversions coincide exactly — that is the regime the
    whole suite was written in, and the reason nobody noticed.
    """
    period_rate = daily_risk_free_rate(annual_rate, periods_per_year)
    assert (1.0 + period_rate) ** periods_per_year - 1.0 == pytest.approx(annual_rate, rel=_RF_REL_TOLERANCE, abs=_RF_ABS_TOLERANCE)

    reverted_round_trip = (1.0 + _reverted_calendar_day_rate(annual_rate)) ** periods_per_year - 1.0
    if periods_per_year == _RF_CALENDAR_FACTOR:
        # The calendar-day case: old and new are the same function, and must stay so.
        assert daily_risk_free_rate(annual_rate, periods_per_year) == _reverted_calendar_day_rate(annual_rate)
        assert reverted_round_trip == pytest.approx(annual_rate, rel=_RF_REL_TOLERANCE, abs=_RF_ABS_TOLERANCE)
    else:
        # Anywhere else the old charge falls materially short of what was requested. The
        # 0.9 is a floor, not a measurement: the real shortfalls are 29% at 261, 31% at
        # 252 and 97% at 12, so this cannot be satisfied by float noise.
        assert reverted_round_trip < annual_rate * 0.9


@pytest.mark.parametrize("periods_per_year", (*_RF_FACTORS, 52.0, 4.0, 1.0))
def test_a_zero_risk_free_rate_converts_to_exactly_zero_at_every_factor_which_is_why_the_mismatch_hid(periods_per_year):
    """Document the blind spot itself: at rf = 0 the two conversions are the same number.

    ``expm1(log1p(0) / x)`` is ``0.0`` for every finite positive ``x``, so the units error
    was strictly invisible to anyone leaving the rate at its default — which is the default
    in every scope that does not set one. This is not a curiosity, it is the explanation of
    how a 28% mis-charge shipped: the cheap smoke test cannot reach it, only a test that
    deliberately turns the rate on can.

    The exactness matters. ``pytest.approx`` here would accept a conversion that returns
    1e-18 for a zero rate, and a non-zero "zero" charge would push every rate-free Sharpe
    off its published value by a hair while looking fine.
    """
    assert daily_risk_free_rate(0.0, periods_per_year) == 0.0
    assert daily_risk_free_rate(0.0, periods_per_year) == _reverted_calendar_day_rate(0.0)

    # The other half of the documentation, and the half that discriminates: the moment the
    # rate is non-zero the two conversions part company at every factor but 365. Every
    # factor exercised here is coarser than a calendar day, so the correct per-period
    # charge is strictly the larger one — the old code always undercharged, never over.
    if periods_per_year != _RF_CALENDAR_FACTOR:
        assert daily_risk_free_rate(0.02, periods_per_year) > _reverted_calendar_day_rate(0.02)


def test_the_period_count_is_a_required_argument_so_the_period_mismatch_is_unrepresentable():
    """A missing period count is a ``TypeError``, not a silent fallback to calendar days.

    The point is stronger than "callers are encouraged to pass it". A default — any default
    — would let the original defect back in by omission, through a new call site that never
    thought about the question, and it would come back silently because the result is a
    plausible number rather than an error. Requiring the argument converts a wrong answer
    into a failure to start, which is the only version of this the reviewer can catch.

    The second half proves the argument is load-bearing rather than decorative: the same
    rate converted against two different period counts must give two different charges. A
    signature that accepts the parameter and ignores it would satisfy the first assertion
    and fail this one.
    """
    with pytest.raises(TypeError):
        daily_risk_free_rate(0.05)

    trading = daily_risk_free_rate(0.05, _RF_TRADING_FACTOR)
    calendar = daily_risk_free_rate(0.05, _RF_CALENDAR_FACTOR)
    assert trading != calendar
    assert trading > calendar
    # 261 calendar days' worth of charge has to be spread over 261 periods instead of 365,
    # so the ratio is the period ratio: ~1.3985, and flat in the rate.
    assert trading / calendar == pytest.approx(1.3985, rel=1e-4)


@pytest.mark.parametrize("periods_per_year", (0.0, -1.0, -261.0, float("inf"), float("nan")))
def test_a_period_count_that_cannot_annualize_is_rejected_instead_of_quietly_ignored(periods_per_year):
    """A factor that cannot describe a year must raise, not divide.

    Zero and negative counts have no meaning, and ``inf``/``nan`` arrive from an empty or
    malformed observation calendar where the factor is inferred rather than configured.
    Each one would otherwise produce a finite-looking charge (``expm1(x / inf)`` is a
    perfectly presentable ``0.0``) and publish a ratio nobody could distinguish from a
    real one.

    This also pins that the parameter reaches ``_positive_annualization_factor`` at all: a
    body that ignored it in favour of a constant would have nothing to validate, and these
    five inputs would sail through.
    """
    with pytest.raises(ValueError, match="annualization_factor must be finite and positive"):
        daily_risk_free_rate(0.05, periods_per_year)


@pytest.mark.parametrize("annual_rate", (float("nan"), float("inf"), float("-inf"), -1.0, -1.5))
def test_a_risk_free_rate_at_or_below_total_loss_is_still_rejected_after_the_signature_change(annual_rate):
    """The pre-existing rate guard must survive the repair that added the period count.

    ``log1p(-1)`` is ``-inf`` and anything at or below it is not a rate, it is a wiped-out
    principal; ``nan``/``inf`` propagate into every downstream ratio and serialise into the
    payload as a number no chart can draw. This guard predates the period-count fix, and it
    is asserted here because adding a parameter to a validating function is exactly the
    edit that drops the validation that was already there.
    """
    with pytest.raises(ValueError, match="annual risk-free rate must be finite and greater than -1"):
        daily_risk_free_rate(annual_rate, _RF_TRADING_FACTOR)


@pytest.mark.parametrize("annual_rate", _RF_RATES)
def test_sharpe_charges_the_risk_free_rate_in_the_same_periods_its_volatility_is_annualized_over(annual_rate):
    """Numerator and denominator must speak of one period, measured without asking the subject.

    Subtracting a constant per-period charge moves the mean by that charge and leaves the
    deviation alone, so the whole effect of the rate on Sharpe is

        sharpe(0) - sharpe(rf) == period_rate * factor / annualized_volatility

    Block (g) already asserts this shape for the rolling helper — and cannot see the units
    error, because it writes ``period_rate`` as ``daily_risk_free_rate(rf, factor)``. With
    the subject on both sides the identity is self-consistent and therefore silent: it held
    before the repair and holds after it, unchanged.

    The fix is to source ``period_rate`` from ``_compounding_period_rate``, which knows only
    what the rate MEANS. The identity then stops being a restatement of the implementation
    and becomes a claim about the published number, and the old engine misses it by 28%.
    """
    returns = _rolling_sample(43)
    factor = _RF_TRADING_FACTOR

    rate_free = annualized_sharpe(returns, factor)
    charged = annualized_sharpe(returns, factor, annual_risk_free_rate=annual_rate)
    assert rate_free is not None
    assert charged is not None

    volatility = annualized_volatility(returns, factor)
    expected_shift = _compounding_period_rate(annual_rate, factor) * factor / volatility
    assert rate_free - charged == pytest.approx(expected_shift, rel=_RF_REL_TOLERANCE, abs=_RF_ABS_TOLERANCE)

    # The shift is a real, readable movement in the ratio (~0.05-0.26 Sharpe points here),
    # not a rounding artefact, so a rate dropped on the way in could not hide inside it.
    assert expected_shift > 1e-2

    # And the old conversion is nowhere near: it charged a calendar-day rate against a
    # trading-day series and moved Sharpe by ~72% of what it should have.
    reverted_shift = _reverted_calendar_day_rate(annual_rate) * factor / volatility
    assert reverted_shift < expected_shift
    assert rate_free - charged != pytest.approx(reverted_shift, rel=1e-3)


@pytest.mark.parametrize("annual_rate", _RF_RATES)
def test_sortino_loses_more_flattery_than_sharpe_because_the_target_enters_the_ratio_twice(annual_rate):
    """Pin the MECHANISM: an understated target inflates Sortino's numerator and deflates its denominator.

    Sharpe uses the charge once, in the mean; its deviation does not know the rate exists.
    ``annualized_sortino`` uses ``target_daily`` in ``min(value - target, 0) ** 2`` as well
    as in the excess mean, so understating it does two things at once and both point the
    same way: fewer and smaller observations count as downside (denominator too small)
    while the excess mean is too large (numerator too big). The error therefore enters
    twice, compounding rather than cancelling, and Sortino was flattered harder than Sharpe
    at every non-zero rate.

    That ordering is the claim worth defending. It is not a magnitude anyone can eyeball
    from the code, it predicts which published number moved most when the fix landed, and
    it is the reason Sortino could not simply be assumed to behave "like Sharpe but on the
    downside" during the repair.
    """
    returns = _rolling_sample(43)
    factor = _RF_TRADING_FACTOR
    corrected_rate = daily_risk_free_rate(annual_rate, factor)
    reverted_rate = _reverted_calendar_day_rate(annual_rate)
    assert reverted_rate < corrected_rate

    sharpe_now = annualized_sharpe(returns, factor, annual_risk_free_rate=annual_rate)
    sortino_now = annualized_sortino(returns, factor, annual_target_return=annual_rate)
    assert sharpe_now is not None
    assert sortino_now is not None

    # The replay helpers are faithful to the subject's body: handed the subject's own rate
    # they reproduce the subject. Without this the "before" figures below would be measuring
    # the helpers rather than the fix.
    assert sharpe_now == pytest.approx(_sharpe_charged_at(returns, factor, corrected_rate), rel=_RF_ALGEBRA_REL_TOLERANCE, abs=_RF_ABS_TOLERANCE)
    assert sortino_now == pytest.approx(_sortino_charged_at(returns, factor, corrected_rate), rel=_RF_ALGEBRA_REL_TOLERANCE, abs=_RF_ABS_TOLERANCE)

    sharpe_flattery = _sharpe_charged_at(returns, factor, reverted_rate) - sharpe_now
    sortino_flattery = _sortino_charged_at(returns, factor, reverted_rate) - sortino_now
    assert sharpe_flattery > 0.0
    assert sortino_flattery > sharpe_flattery

    # The two halves of the double exposure, asserted rather than asserted-in-prose.
    observations = len(returns)
    downside_before = math.sqrt(math.fsum(min(value - reverted_rate, 0.0) ** 2 for value in returns) / observations)
    downside_now = math.sqrt(math.fsum(min(value - corrected_rate, 0.0) ** 2 for value in returns) / observations)
    assert downside_before < downside_now, "the understated target shrank the downside deviation"

    excess_before = math.fsum(value - reverted_rate for value in returns) / observations
    excess_now = math.fsum(value - corrected_rate for value in returns) / observations
    assert excess_before > excess_now, "the understated target inflated the excess mean"


@pytest.mark.parametrize("annual_rate", (0.01, 0.02, 0.05, 0.10))
def test_a_calendar_day_annualization_factor_leaves_sharpe_and_sortino_bit_for_bit_where_they_were(annual_rate):
    """The repair is surgical: at 365 nothing moves, and "nothing" means zero, not "small".

    A portfolio on a HISTORICAL basis annualizes over calendar days, so its factor IS 365
    and its published Sharpe and Sortino must be the same floats after the fix as before —
    otherwise the change is a silent restatement of live numbers rather than a bug fix, and
    it owes the user an explanation. ``pytest.approx`` would not settle that question: it
    would accept a last-bit drift and leave "did anything move?" unanswered. Equality does.

    The contrast half is what stops this test blessing the defect it is bracketing. On its
    own, "the calendar case is unchanged" is equally true of the broken engine. Paired with
    the trading-day case being materially different, it says the right thing: unchanged
    exactly where it should be, changed exactly where it should be.
    """
    returns = _rolling_sample(43)
    reverted_rate = _reverted_calendar_day_rate(annual_rate)

    assert daily_risk_free_rate(annual_rate, _RF_CALENDAR_FACTOR) == reverted_rate
    assert annualized_sharpe(returns, _RF_CALENDAR_FACTOR, annual_risk_free_rate=annual_rate) == _sharpe_charged_at(returns, _RF_CALENDAR_FACTOR, reverted_rate)
    assert annualized_sortino(returns, _RF_CALENDAR_FACTOR, annual_target_return=annual_rate) == _sortino_charged_at(returns, _RF_CALENDAR_FACTOR, reverted_rate)

    # Same comparison, one factor over: here the engines genuinely disagree. The 1e-3
    # relative bound is loose on purpose — the real separation is ~13% of the ratio — so
    # this fails only when the trading-day path has collapsed back onto calendar days.
    assert daily_risk_free_rate(annual_rate, _RF_TRADING_FACTOR) != reverted_rate
    assert annualized_sharpe(returns, _RF_TRADING_FACTOR, annual_risk_free_rate=annual_rate) != pytest.approx(_sharpe_charged_at(returns, _RF_TRADING_FACTOR, reverted_rate), rel=1e-3)
    assert annualized_sortino(returns, _RF_TRADING_FACTOR, annual_target_return=annual_rate) != pytest.approx(_sortino_charged_at(returns, _RF_TRADING_FACTOR, reverted_rate), rel=1e-3)


@pytest.mark.parametrize("annual_rate", (0.02, 0.05))
def test_the_rolling_sharpe_path_charges_the_same_trading_day_rate_as_the_scalar_metric(annual_rate):
    """The vectorised helper threads the observed factor into the rate, window by window.

    ``rolling_annualized_sharpe_values`` converts the rate ONCE, outside the rolling pass,
    and subtracts the constant from the series before ``rolling().mean()``. That is a third
    call site with its own opportunity to pass the wrong factor — and the one most likely to
    be missed, because it lives in ``signal_helpers`` rather than beside the scalar metric.

    Two claims, deliberately separate. The first is agreement with the scalar loop, reusing
    block (g)'s comparator so the ``None`` mask and the undefined count are covered too;
    note that this half is blind on its own, since both paths call the same conversion and
    would agree just as happily on a wrong one. The second is the identity from the scalar
    test above, sourced from ``_compounding_period_rate``, which is what actually decides
    whether the number charged is the number the user asked for.

    Run at 261, not at ``_ANNUALIZATION``: the module constant is 252.0, which would also
    have served, but 261 keeps this test aligned with the rest of the block and neither
    value is the calendar factor where the question disappears.
    """
    returns = _rolling_sample(43)
    window = 30
    factor = _RF_TRADING_FACTOR

    vectorised = rolling_annualized_sharpe_values(returns, window, factor, annual_risk_free_rate=annual_rate)
    loop = _loop_annualized_sharpe(returns, window, factor, annual_risk_free_rate=annual_rate)
    _assert_rolling_paths_agree(vectorised, loop, observations=len(returns), label=f"sharpe at rf={annual_rate} on a {factor:g}-period year")

    charged_values, _ = vectorised
    free_values, _ = rolling_annualized_sharpe_values(returns, window, factor)
    volatility_values, _ = rolling_annualized_volatility_values(returns, window, factor)

    period_rate = _compounding_period_rate(annual_rate, factor)
    observed = [rate_free - charged for rate_free, charged in zip(free_values[window:], charged_values[window:], strict=True)]
    expected = [period_rate * factor / volatility for volatility in volatility_values[window:]]
    assert observed == pytest.approx(expected, rel=_ROLLING_REL_TOLERANCE, abs=_ROLLING_ABS_TOLERANCE)

    # Window by window, never merely on aggregate: the rolling volatility varies enough
    # across the sample that comparing extremes could mask a wrong rate in one regime.
    reverted = [_reverted_calendar_day_rate(annual_rate) * factor / volatility for volatility in volatility_values[window:]]
    assert all(old < new for old, new in zip(reverted, expected, strict=True))
    assert min(expected) > 1e-2
