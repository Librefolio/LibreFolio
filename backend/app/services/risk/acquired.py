"""Risk measures acquired from the riskfolio catalogue, in project conventions.

These are *acquisitions*: measures the product did not have, re-implemented here
rather than delegated to ``riskfolio`` at runtime. The reason is architectural,
not stylistic — ``riskfolio`` is imported only inside the spawned worker pool
(``risk/quant/riskfolio_worker.py``), while the analytics that consume these
measures implement the synchronous ``RiskAnalytic.compute()``. The library is the
*test oracle*, never a runtime dependency.

Two conventions are load-bearing and differ from the library:

* **Sign.** ``riskfolio`` returns positive magnitudes. ``RiskKpiOutput`` states
  losses as negatives (``max_drawdown`` is ``Field(..., le=0)``). Everything here
  returns the project convention: drawdowns and returns are negative, dispersions
  are non-negative.
* **Baseline.** The underwater series produced by ``summarize_drawdown`` carries
  the pre-return baseline as its first element. ``MDD`` and ``UCI`` consume it;
  ``DaR`` and ``CDaR`` must not. See ``_tail_without_baseline``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

_ZERO_TOLERANCE = 1e-15


def _finite(values: Sequence[float], *, name: str) -> tuple[float, ...]:
    normalized = tuple(float(value) for value in values)
    if any(not math.isfinite(value) for value in normalized):
        raise ValueError(f"{name} must be finite")
    return normalized


def _significance(confidence_level: float) -> float:
    level = float(confidence_level)
    if not math.isfinite(level) or not 0 < level < 1:
        raise ValueError("confidence_level must be finite and between 0 and 1")
    return 1.0 - level


def _tail_without_baseline(drawdowns: Sequence[float]) -> tuple[float, ...]:
    """Drop the pre-return baseline point from an underwater series.

    ``summarize_drawdown`` returns ``T + 1`` points because ``wealth_index``
    prepends the unit baseline, whose drawdown is always ``0``. ``MDD_Rel`` and
    ``UCI_Rel`` iterate that whole array, but ``DaR_Rel`` and ``CDaR_Rel`` delete
    the first element before sorting, so their quantile index and their
    ``alpha * T`` denominator are computed over ``T`` points, not ``T + 1``.

    Using the wrong length is a silent error: the extra ``0.0`` sorts to the top
    of the array, so the quantile itself often still matches, while CDaR's
    denominator shifts by one observation.
    """
    series = _finite(drawdowns, name="drawdown series")
    if not series:
        raise ValueError("drawdown series must not be empty")
    return series[1:]


def worst_realization(returns: Sequence[float]) -> float:
    """The worst single observed return.

    ``riskfolio.WR`` returns ``-min(X)``; the project states realized losses as
    negatives, so this returns ``min(X)`` itself.

    ⚠️ No floor is applied. A window in which every return is positive yields a
    *positive* worst realization, which is the truth: the worst day was a gain.
    ``RiskKpiOutput.worst_realization`` is constrained to ``le=0``, so adapting
    that degenerate case to the contract is the caller's job — see
    ``historical_kpi``. Flooring it here would pair a value of ``0.0`` with a date
    pointing at a profitable day.
    """
    values = _finite(returns, name="returns")
    if not values:
        raise ValueError("returns must not be empty")
    return min(values)


def worst_realization_index(returns: Sequence[float]) -> int:
    """Position of the worst observed return, resolving ties to the earliest."""
    values = _finite(returns, name="returns")
    if not values:
        raise ValueError("returns must not be empty")
    return min(range(len(values)), key=values.__getitem__)


def maximum_drawdown(drawdowns: Sequence[float]) -> float:
    """Deepest peak-relative decline, as a non-positive number.

    Equivalent to ``-riskfolio.MDD_Rel``. Consumes the baseline-inclusive series.
    """
    series = _finite(drawdowns, name="drawdown series")
    if not series:
        raise ValueError("drawdown series must not be empty")
    return min(series)


def drawdown_at_risk(
    drawdowns: Sequence[float],
    *,
    confidence_level: float = 0.95,
) -> float:
    """Drawdown quantile, as a non-positive number.

    Equivalent to ``-riskfolio.DaR_Rel(alpha=1 - confidence_level)``: the
    drawdown exceeded only ``1 - confidence_level`` of the time.
    """
    alpha = _significance(confidence_level)
    tail = _tail_without_baseline(drawdowns)
    if not tail:
        raise ValueError("drawdown at risk requires at least one observation")
    ordered = sorted(tail)
    index = max(0, math.ceil(alpha * len(ordered)) - 1)
    return ordered[index]


def conditional_drawdown_at_risk(
    drawdowns: Sequence[float],
    *,
    confidence_level: float = 0.95,
) -> float:
    """Mean of the drawdowns beyond the quantile, as a non-positive number.

    Equivalent to ``-riskfolio.CDaR_Rel(alpha=1 - confidence_level)``.

    ⚠️ This is **not** the arithmetic mean of the worst ``alpha`` share of
    observations. It is the Rockafellar-Uryasev form, whose tail integral is
    normalized by ``alpha * T`` rather than by the number of observations in the
    tail. Writing the naive mean here reproduces exactly the historical CVaR
    defect this subsystem is being corrected for: a plausible number, wrong by a
    fraction of a percent, that no test notices.
    """
    alpha = _significance(confidence_level)
    tail = _tail_without_baseline(drawdowns)
    if not tail:
        raise ValueError("conditional drawdown at risk requires at least one observation")
    ordered = sorted(tail)
    index = max(0, math.ceil(alpha * len(ordered)) - 1)
    quantile = ordered[index]
    excess = math.fsum(ordered[position] - quantile for position in range(index + 1))
    return quantile + excess / (alpha * len(ordered))


def ulcer_index(drawdowns: Sequence[float]) -> float:
    """Root-mean-square drawdown: depth and duration in one non-negative number.

    Equivalent to ``riskfolio.UCI_Rel``, and the one measure here whose sign is
    positive — it is a dispersion, and a square root cannot be negative.

    ⚠️ The divisor is the number of *returns*, not the number of points in the
    baseline-inclusive series and not a Bessel-corrected ``T - 1``. riskfolio
    writes ``sqrt(value / (n - 1))`` where ``n`` counts the inserted baseline, so
    ``n - 1`` is ``T``. Reading that as a sample standard deviation and dividing
    by ``T - 1`` is wrong by ``sqrt(T / (T - 1))``.

    riskfolio additionally guards the accumulation with ``if DD > 0``. That guard
    is omitted here because it cannot change the result: the only values it
    excludes are exactly zero, and zero squared contributes nothing.
    """
    series = _finite(drawdowns, name="drawdown series")
    if len(series) < 2:
        raise ValueError("ulcer index requires at least one return observation")
    squared = math.fsum(value * value for value in series)
    return math.sqrt(squared / (len(series) - 1))


def effective_number_of_assets(weights: Sequence[float]) -> float | None:
    """Inverse Herfindahl over the supplied weights: equivalent position count.

    The unit is a *number of positions*, never a percentage: ``0.5, 0.3, 0.15,
    0.05`` yields ``2.74``, meaning the portfolio behaves like roughly two and
    three-quarter equal positions.

    The weights are consumed as given. Risk weights are already
    ``position value / net worth`` — the same denominator AI Export uses for
    ``nav_weight_percent`` — so passing them unmodified reproduces AI Export's
    cash semantics: cash sits in the denominator but is never a term. Any
    renormalization here would silently make the product state two different
    numbers for one portfolio's concentration.

    Returns ``None`` when no weight carries value, which is a fully liquid
    scope rather than a zero-concentration one.
    """
    values = _finite(weights, name="weights")
    if any(value < 0 for value in values):
        raise ValueError("negative weights are outside the first-wave contract")
    herfindahl = math.fsum(value * value for value in values)
    if herfindahl <= _ZERO_TOLERANCE:
        return None
    return 1.0 / herfindahl


def diversification_ratio(
    covariance: Sequence[Sequence[float]],
    weights: Sequence[float],
    *,
    portfolio_volatility: float,
) -> float | None:
    """Weighted mean of standalone volatilities over portfolio volatility.

    ``1`` means correlation is doing nothing for the holder; higher means the
    holdings genuinely offset one another. It is the measure that sees what the
    effective number of assets cannot: ten equally weighted assets score the same
    on that count whether they are independent or move as one.

    Invariant to both scale and annualization — scaling every weight by ``k``
    scales numerator and denominator alike, and the annualization factor enters
    as ``sqrt(af)`` on both sides. It is therefore the one concentration measure
    that compares across portfolios holding different amounts of cash.

    ``portfolio_volatility`` is supplied rather than recomputed so that the ratio
    is guaranteed consistent with the contribution figures published alongside
    it.

    Returns ``None`` when portfolio volatility is zero and the ratio is undefined.
    """
    values = _finite(weights, name="weights")
    size = len(values)
    matrix = [_finite(row, name="covariance row") for row in covariance]
    if len(matrix) != size or any(len(row) != size for row in matrix):
        raise ValueError("covariance matrix dimensions must match weights")
    if any(value < 0 for value in values):
        raise ValueError("negative weights are outside the first-wave contract")
    volatility = float(portfolio_volatility)
    if not math.isfinite(volatility) or volatility < 0:
        raise ValueError("portfolio_volatility must be finite and non-negative")
    if volatility <= _ZERO_TOLERANCE:
        return None
    if any(matrix[index][index] < 0 for index in range(size)):
        raise ValueError("covariance diagonal must be non-negative")
    weighted = math.fsum(values[index] * math.sqrt(matrix[index][index]) for index in range(size))
    return weighted / volatility


__all__ = [
    "conditional_drawdown_at_risk",
    "diversification_ratio",
    "drawdown_at_risk",
    "effective_number_of_assets",
    "maximum_drawdown",
    "ulcer_index",
    "worst_realization",
    "worst_realization_index",
]
