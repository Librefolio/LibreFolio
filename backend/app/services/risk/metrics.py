"""Pure mathematical primitives shared by risk analytics."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

_ZERO_TOLERANCE = 1e-15

DRAWDOWN_RECOVERY_NO_DRAWDOWN = "no_drawdown"
DRAWDOWN_RECOVERY_RECOVERED = "recovered"
DRAWDOWN_RECOVERY_OPEN = "open"


@dataclass(frozen=True, slots=True)
class DrawdownSummary:
    max_drawdown: float
    max_duration: int
    wealth_index: tuple[float, ...]
    drawdowns: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class DrawdownEpisodeReport:
    """Deterministic dated current/maximum drawdown episode primitive.

    All magnitudes are decimal ratios (``-0.1`` means a 10% peak-relative
    decline); the presentation layer owns any percentage formatting.
    """

    current_drawdown: float
    current_peak_date: date
    current_drawdown_duration_days: int
    maximum_drawdown: float
    maximum_drawdown_peak_date: date | None
    maximum_drawdown_trough_date: date | None
    maximum_drawdown_recovery_status: str
    maximum_drawdown_recovery_date: date | None
    maximum_drawdown_duration_days: int
    maximum_drawdown_recovered_ratio: float | None
    remaining_to_peak_ratio: float
    available_start: date
    available_end: date
    n_observations: int


@dataclass(frozen=True, slots=True)
class ContributionSummary:
    portfolio_volatility: float
    marginal: tuple[float, ...]
    component: tuple[float, ...]
    percentage: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ComparisonSummary:
    active_return: float
    tracking_error: float
    information_ratio: float | None
    correlation: float | None
    beta: float | None
    primary_cumulative: tuple[float, ...]
    comparison_cumulative: tuple[float, ...]
    primary_drawdowns: tuple[float, ...]
    comparison_drawdowns: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class HistoricalTailRisk:
    value_at_risk: float
    conditional_value_at_risk: float
    horizon_returns: tuple[float, ...]


def _finite_values(
    values: Sequence[float],
    *,
    name: str = "values",
) -> tuple[float, ...]:
    normalized = tuple(float(value) for value in values)
    if any(not math.isfinite(value) for value in normalized):
        raise ValueError(f"{name} must be finite")
    return normalized


def _positive_annualization_factor(annualization_factor: float) -> float:
    normalized = float(annualization_factor)
    if normalized <= 0 or not math.isfinite(normalized):
        raise ValueError("annualization_factor must be finite and positive")
    return normalized


def compounded_return(returns: Sequence[float]) -> float:
    """Compound simple returns into one holding-period return."""
    wealth = 1.0
    for value in _finite_values(returns, name="simple returns"):
        if value < -1.0:
            raise ValueError("simple returns must be finite and greater than or equal to -1")
        wealth *= 1.0 + value
    return wealth - 1.0


def sample_variance(values: Sequence[float]) -> float:
    """Return unbiased sample variance (ddof=1)."""
    values = _finite_values(values)
    if len(values) < 2:
        raise ValueError("sample variance requires at least two observations")
    mean = math.fsum(values) / len(values)
    return math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1)


def sample_standard_deviation(values: Sequence[float]) -> float:
    """Return unbiased sample standard deviation (ddof=1)."""
    return math.sqrt(sample_variance(values))


def sample_covariance(left: Sequence[float], right: Sequence[float]) -> float:
    """Return unbiased sample covariance (ddof=1)."""
    left = _finite_values(left, name="left values")
    right = _finite_values(right, name="right values")
    if len(left) != len(right):
        raise ValueError("covariance inputs must have the same length")
    if len(left) < 2:
        raise ValueError("sample covariance requires at least two observations")
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    return math.fsum((left_value - left_mean) * (right_value - right_mean) for left_value, right_value in zip(left, right, strict=True)) / (len(left) - 1)


def annualized_volatility(
    returns: Sequence[float],
    annualization_factor: float,
) -> float:
    """Annualize sample volatility with the observed factor."""
    return sample_standard_deviation(returns) * math.sqrt(_positive_annualization_factor(annualization_factor))


def daily_risk_free_rate(annual_rate: float) -> float:
    """Convert an effective annual risk-free rate to an effective daily rate."""
    if not math.isfinite(annual_rate) or annual_rate <= -1.0:
        raise ValueError("annual risk-free rate must be finite and greater than -1")
    return math.expm1(math.log1p(annual_rate) / 365.0)


def annualized_sharpe(
    returns: Sequence[float],
    annualization_factor: float,
    *,
    annual_risk_free_rate: float = 0.0,
) -> float | None:
    """Return annualized Sharpe, or None when sample volatility is zero."""
    annualization_factor = _positive_annualization_factor(annualization_factor)
    volatility = sample_standard_deviation(returns)
    if math.isclose(volatility, 0.0, rel_tol=0.0, abs_tol=_ZERO_TOLERANCE):
        return None
    excess_mean = math.fsum(value - daily_risk_free_rate(annual_risk_free_rate) for value in returns) / len(returns)
    return excess_mean / volatility * math.sqrt(annualization_factor)


def annualized_sortino(
    returns: Sequence[float],
    annualization_factor: float,
    *,
    annual_target_return: float = 0.0,
) -> float | None:
    """Return annualized Sortino using downside deviation versus an explicit MAR."""
    values = _finite_values(returns, name="returns")
    if len(values) < 2:
        raise ValueError("Sortino requires at least two observations")
    annualization_factor = _positive_annualization_factor(annualization_factor)
    target_daily = daily_risk_free_rate(annual_target_return)
    downside_variance = math.fsum(min(value - target_daily, 0.0) ** 2 for value in values) / len(values)
    downside_deviation = math.sqrt(downside_variance)
    if math.isclose(downside_deviation, 0.0, rel_tol=0.0, abs_tol=_ZERO_TOLERANCE):
        return None
    excess_mean = math.fsum(value - target_daily for value in values) / len(values)
    return excess_mean / downside_deviation * math.sqrt(annualization_factor)


def beta(
    primary_returns: Sequence[float],
    comparison_returns: Sequence[float],
) -> float | None:
    """Return sample beta, or None when comparison variance is zero."""
    comparison_variance = sample_variance(comparison_returns)
    if math.isclose(comparison_variance, 0.0, rel_tol=0.0, abs_tol=_ZERO_TOLERANCE):
        return None
    return sample_covariance(primary_returns, comparison_returns) / comparison_variance


def underwater_drawdown(values: Sequence[float]) -> list[float]:
    """Return the running peak-relative drawdown series."""
    if not values:
        return []
    if any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("drawdown values must be finite and positive")

    peak = values[0]
    result: list[float] = []
    for value in values:
        peak = max(peak, value)
        result.append(value / peak - 1.0)
    return result


def wealth_index(returns: Sequence[float]) -> list[float]:
    """Return a unit wealth index including the pre-return baseline."""
    result = [1.0]
    for value in _finite_values(returns, name="returns"):
        if value < -1.0:
            raise ValueError("simple returns must be greater than or equal to -1")
        result.append(result[-1] * (1.0 + value))
    return result


def summarize_drawdown(
    returns: Sequence[float],
    *,
    elapsed_units: Sequence[int] | None = None,
) -> DrawdownSummary:
    """Return negative max drawdown and longest time below a prior peak."""
    wealth = wealth_index(returns)
    if elapsed_units is None:
        elapsed = tuple(range(len(wealth)))
    else:
        elapsed = tuple(elapsed_units)
        if len(elapsed) != len(wealth):
            raise ValueError("elapsed_units must include the wealth baseline")
        if elapsed != tuple(sorted(elapsed)) or len(elapsed) != len(set(elapsed)):
            raise ValueError("elapsed_units must be unique and ascending")

    drawdowns = tuple(underwater_drawdown(wealth))
    max_drawdown = min(drawdowns, default=0.0)
    peak_wealth = wealth[0]
    peak_index = 0
    underwater_peak_index: int | None = None
    longest_duration = 0
    for index, value in enumerate(wealth[1:], start=1):
        if value >= peak_wealth:
            if underwater_peak_index is not None:
                longest_duration = max(longest_duration, elapsed[index] - elapsed[underwater_peak_index])
                underwater_peak_index = None
            peak_wealth = value
            peak_index = index
            continue
        if underwater_peak_index is None:
            underwater_peak_index = peak_index
        longest_duration = max(longest_duration, elapsed[index] - elapsed[underwater_peak_index])
    return DrawdownSummary(
        max_drawdown=max_drawdown,
        max_duration=longest_duration,
        wealth_index=tuple(wealth),
        drawdowns=drawdowns,
    )


def drawdown_episodes(  # noqa: C901 — TODO(P2-refactor): episode state machine with recovery branching
    returns: Sequence[float],
    *,
    dates: Sequence[date],
    baseline_date: date,
) -> DrawdownEpisodeReport:
    """Return dated current and maximum peak-relative drawdown episodes.

    ``dates`` are the observation dates aligned with ``returns``; ``baseline_date``
    is the pre-return valuation date. The wealth grid therefore spans
    ``(baseline_date, *dates)`` and is reused via :func:`wealth_index` /
    :func:`underwater_drawdown` so no raw NAV is recomputed here.
    """
    normalized = _finite_values(returns, name="returns")
    if not normalized:
        raise ValueError("drawdown episodes require at least one return")
    observation_dates = tuple(dates)
    if len(observation_dates) != len(normalized):
        raise ValueError("dates must align with returns")
    grid_dates = (baseline_date, *observation_dates)
    if any(later <= earlier for earlier, later in zip(grid_dates[:-1], grid_dates[1:], strict=True)):
        raise ValueError("observation dates must be strictly increasing after the baseline")

    wealth = wealth_index(normalized)
    underwater = underwater_drawdown(wealth)
    last = len(wealth) - 1

    running_peak = wealth[0]
    peak_index = 0
    open_peak_index: int | None = None
    open_trough_index = 0
    open_trough_wealth = wealth[0]
    episodes: list[tuple[int, int, int | None]] = []
    for index in range(1, len(wealth)):
        value = wealth[index]
        if value >= running_peak:
            if open_peak_index is not None:
                episodes.append((open_peak_index, open_trough_index, index))
                open_peak_index = None
            running_peak = value
            peak_index = index
            continue
        if open_peak_index is None:
            open_peak_index = peak_index
            open_trough_index = index
            open_trough_wealth = value
        elif value < open_trough_wealth:
            open_trough_index = index
            open_trough_wealth = value
    if open_peak_index is not None:
        episodes.append((open_peak_index, open_trough_index, None))

    current_drawdown = min(0.0, underwater[last])
    current_underwater = current_drawdown < -_ZERO_TOLERANCE
    current_peak_date = grid_dates[peak_index]
    current_drawdown_duration_days = (grid_dates[last] - grid_dates[peak_index]).days if current_underwater else 0
    remaining_to_peak_ratio = max(0.0, -current_drawdown / (1.0 + current_drawdown)) if current_underwater else 0.0

    best: tuple[int, int, int | None] | None = None
    best_depth = 0.0
    for episode in episodes:
        depth = underwater[episode[1]]
        if depth < -_ZERO_TOLERANCE and depth < best_depth:
            best = episode
            best_depth = depth

    if best is None:
        return DrawdownEpisodeReport(
            current_drawdown=current_drawdown,
            current_peak_date=current_peak_date,
            current_drawdown_duration_days=current_drawdown_duration_days,
            maximum_drawdown=0.0,
            maximum_drawdown_peak_date=None,
            maximum_drawdown_trough_date=None,
            maximum_drawdown_recovery_status=DRAWDOWN_RECOVERY_NO_DRAWDOWN,
            maximum_drawdown_recovery_date=None,
            maximum_drawdown_duration_days=0,
            maximum_drawdown_recovered_ratio=None,
            remaining_to_peak_ratio=remaining_to_peak_ratio,
            available_start=observation_dates[0],
            available_end=observation_dates[-1],
            n_observations=len(normalized),
        )

    max_peak_index, max_trough_index, max_recovery_index = best
    maximum_drawdown = min(0.0, underwater[max_trough_index])
    peak_wealth = wealth[max_peak_index]
    trough_wealth = wealth[max_trough_index]
    recovered = max_recovery_index is not None
    reference_index = max_recovery_index if recovered else last
    denominator = peak_wealth - trough_wealth
    if denominator > _ZERO_TOLERANCE:
        recovered_ratio = (wealth[reference_index] - trough_wealth) / denominator
        recovered_ratio = max(0.0, min(1.0, recovered_ratio))
    else:
        recovered_ratio = 1.0
    if recovered:
        recovery_status = DRAWDOWN_RECOVERY_RECOVERED
        recovery_date = grid_dates[max_recovery_index]
        maximum_duration_days = (grid_dates[max_recovery_index] - grid_dates[max_peak_index]).days
    else:
        recovery_status = DRAWDOWN_RECOVERY_OPEN
        recovery_date = None
        maximum_duration_days = (grid_dates[last] - grid_dates[max_peak_index]).days

    return DrawdownEpisodeReport(
        current_drawdown=current_drawdown,
        current_peak_date=current_peak_date,
        current_drawdown_duration_days=current_drawdown_duration_days,
        maximum_drawdown=maximum_drawdown,
        maximum_drawdown_peak_date=grid_dates[max_peak_index],
        maximum_drawdown_trough_date=grid_dates[max_trough_index],
        maximum_drawdown_recovery_status=recovery_status,
        maximum_drawdown_recovery_date=recovery_date,
        maximum_drawdown_duration_days=maximum_duration_days,
        maximum_drawdown_recovered_ratio=recovered_ratio,
        remaining_to_peak_ratio=remaining_to_peak_ratio,
        available_start=observation_dates[0],
        available_end=observation_dates[-1],
        n_observations=len(normalized),
    )


def period_returns_from_cumulative(cumulative_returns: Sequence[float]) -> list[float]:
    """Recover period returns from an exact cumulative return series."""
    cumulative = _finite_values(cumulative_returns, name="cumulative returns")
    if len(cumulative) < 2:
        return []
    if any(value <= -1.0 for value in cumulative):
        raise ValueError("cumulative returns must be greater than -1")
    return [(1.0 + current) / (1.0 + previous) - 1.0 for previous, current in zip(cumulative[:-1], cumulative[1:], strict=True)]


def pearson_correlation(
    left: Sequence[float],
    right: Sequence[float],
) -> float | None:
    """Return Pearson correlation, or None when either sample is flat."""
    left_std = sample_standard_deviation(left)
    right_std = sample_standard_deviation(right)
    if math.isclose(left_std, 0.0, rel_tol=0.0, abs_tol=_ZERO_TOLERANCE) or math.isclose(right_std, 0.0, rel_tol=0.0, abs_tol=_ZERO_TOLERANCE):
        return None
    value = sample_covariance(left, right) / (left_std * right_std)
    return max(-1.0, min(1.0, value))


def pairwise_correlation(
    left: Sequence[float | None],
    right: Sequence[float | None],
    *,
    expected_observations: int | None = None,
) -> tuple[float | None, int, float]:
    """Return correlation, common observations, and common-sample coverage."""
    if len(left) != len(right):
        raise ValueError("correlation inputs must have the same length")
    pairs = [(float(a), float(b)) for a, b in zip(left, right, strict=True) if a is not None and b is not None]
    if any(not math.isfinite(a) or not math.isfinite(b) for a, b in pairs):
        raise ValueError("correlation inputs must be finite")
    denominator = expected_observations if expected_observations is not None else len(left)
    if denominator < 0:
        raise ValueError("expected_observations cannot be negative")
    observations = len(pairs)
    coverage = observations / denominator if denominator else 0.0
    if observations < 2:
        return None, observations, coverage
    return pearson_correlation([a for a, _ in pairs], [b for _, b in pairs]), observations, coverage


def covariance_matrix(series: Sequence[Sequence[float]]) -> list[list[float]]:
    """Return one sample covariance matrix over a common observation calendar."""
    rows = [tuple(_finite_values(values, name="return series")) for values in series]
    if not rows:
        return []
    observations = len(rows[0])
    if observations < 2:
        raise ValueError("covariance matrix requires at least two observations")
    if any(len(row) != observations for row in rows):
        raise ValueError("all return series must share one common calendar")
    return [[sample_covariance(left, right) for right in rows] for left in rows]


def correlation_matrix(series: Sequence[Sequence[float]]) -> list[list[float | None]]:
    """Return one Pearson matrix over the same common observation calendar."""
    rows = [tuple(_finite_values(values, name="return series")) for values in series]
    if not rows:
        return []
    observations = len(rows[0])
    if observations < 2:
        raise ValueError("correlation matrix requires at least two observations")
    if any(len(row) != observations for row in rows):
        raise ValueError("all return series must share one common calendar")
    return [[pearson_correlation(left, right) for right in rows] for left in rows]


def risk_contributions_from_covariance(
    covariance: Sequence[Sequence[float]],
    weights: Sequence[float],
    *,
    annualization_factor: float = 1.0,
) -> ContributionSummary:
    """Return MCTR, CCTR, and PCTR from one common covariance matrix."""
    annualization_factor = _positive_annualization_factor(annualization_factor)
    normalized_weights = _finite_values(weights, name="weights")
    size = len(normalized_weights)
    matrix = [tuple(_finite_values(row, name="covariance row")) for row in covariance]
    if len(matrix) != size or any(len(row) != size for row in matrix):
        raise ValueError("covariance matrix dimensions must match weights")
    if any(weight < 0 for weight in normalized_weights):
        raise ValueError("negative weights are outside the first-wave contract")
    if any(not math.isclose(matrix[i][j], matrix[j][i], rel_tol=1e-12, abs_tol=1e-15) for i in range(size) for j in range(size)):
        raise ValueError("covariance matrix must be symmetric")

    annual_matrix = [[value * annualization_factor for value in row] for row in matrix]
    sigma_weights = [math.fsum(annual_matrix[i][j] * normalized_weights[j] for j in range(size)) for i in range(size)]
    variance = math.fsum(normalized_weights[i] * sigma_weights[i] for i in range(size))
    if variance < -_ZERO_TOLERANCE:
        raise ValueError("covariance matrix produced negative portfolio variance")
    portfolio_volatility = math.sqrt(max(variance, 0.0))
    if math.isclose(portfolio_volatility, 0.0, rel_tol=0.0, abs_tol=_ZERO_TOLERANCE):
        zeros = tuple(0.0 for _ in range(size))
        return ContributionSummary(
            portfolio_volatility=0.0,
            marginal=zeros,
            component=zeros,
            percentage=zeros,
        )
    marginal = tuple(value / portfolio_volatility for value in sigma_weights)
    component = tuple(weight * value for weight, value in zip(normalized_weights, marginal, strict=True))
    percentage = tuple(value / portfolio_volatility for value in component)
    return ContributionSummary(
        portfolio_volatility=portfolio_volatility,
        marginal=marginal,
        component=component,
        percentage=percentage,
    )


def current_buy_and_hold_returns(  # noqa: C901 — sequential validation raises + wealth accumulation loop
    returns_by_asset: Mapping[int, Sequence[float]],
    weights: Mapping[int, float],
    *,
    cash_weight: float | None = None,
) -> list[float]:
    """Replay current weights without rebalancing; cash remains at zero return."""
    if set(returns_by_asset) != set(weights):
        raise ValueError("returns and weights must reference the same assets")
    if not returns_by_asset:
        return []
    normalized_weights = {asset_id: float(weight) for asset_id, weight in weights.items()}
    if any(not math.isfinite(weight) or weight < 0 for weight in normalized_weights.values()):
        raise ValueError("weights must be finite and non-negative")
    rows = {asset_id: _finite_values(values, name=f"asset {asset_id} returns") for asset_id, values in returns_by_asset.items()}
    observations = len(next(iter(rows.values())))
    if any(len(row) != observations for row in rows.values()):
        raise ValueError("all return series must share one common calendar")

    asset_weight = math.fsum(normalized_weights.values())
    if cash_weight is None:
        cash_weight = 1.0 - asset_weight
    cash_weight = float(cash_weight)
    if not math.isfinite(cash_weight) or cash_weight < -1e-12:
        raise ValueError("cash_weight must be finite and non-negative")
    if not math.isclose(asset_weight + cash_weight, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("asset and cash weights must sum to 1")

    asset_wealth = dict.fromkeys(rows, 1.0)
    previous_portfolio_wealth = 1.0
    portfolio_returns: list[float] = []
    for index in range(observations):
        for asset_id, values in rows.items():
            value = values[index]
            if value < -1.0:
                raise ValueError("simple returns must be greater than or equal to -1")
            asset_wealth[asset_id] *= 1.0 + value
        portfolio_wealth = cash_weight + math.fsum(normalized_weights[asset_id] * asset_wealth[asset_id] for asset_id in rows)
        portfolio_returns.append(portfolio_wealth / previous_portfolio_wealth - 1.0)
        previous_portfolio_wealth = portfolio_wealth
    return portfolio_returns


def hypothetical_stress_return(
    shocks: Mapping[int, float],
    weights: Mapping[int, float],
) -> tuple[float, dict[int, float]]:
    """Apply explicit asset shocks to current weights without hidden assumptions."""
    if set(shocks) != set(weights):
        raise ValueError("shocks and weights must reference the same assets")
    contributions: dict[int, float] = {}
    for asset_id, weight in weights.items():
        shock = float(shocks[asset_id])
        weight = float(weight)
        if not math.isfinite(shock) or shock < -1.0:
            raise ValueError("shocks must be finite and greater than or equal to -1")
        if not math.isfinite(weight) or weight < 0:
            raise ValueError("weights must be finite and non-negative")
        contributions[asset_id] = weight * shock
    return math.fsum(contributions.values()), contributions


def comparison_summary(
    primary_returns: Sequence[float],
    comparison_returns: Sequence[float],
    annualization_factor: float,
) -> ComparisonSummary:
    """Return relative-performance metrics and exact cumulative paths."""
    primary = _finite_values(primary_returns, name="primary returns")
    comparison = _finite_values(comparison_returns, name="comparison returns")
    if len(primary) != len(comparison):
        raise ValueError("comparison inputs must have the same length")
    if len(primary) < 2:
        raise ValueError("comparison requires at least two observations")
    annualization_factor = _positive_annualization_factor(annualization_factor)
    active = [left - right for left, right in zip(primary, comparison, strict=True)]
    active_std = sample_standard_deviation(active)
    tracking_error = active_std * math.sqrt(annualization_factor)
    information_ratio = None
    if not math.isclose(active_std, 0.0, rel_tol=0.0, abs_tol=_ZERO_TOLERANCE):
        information_ratio = (math.fsum(active) / len(active)) / active_std * math.sqrt(annualization_factor)

    primary_wealth = wealth_index(primary)
    comparison_wealth = wealth_index(comparison)
    primary_cumulative = tuple(value - 1.0 for value in primary_wealth[1:])
    comparison_cumulative = tuple(value - 1.0 for value in comparison_wealth[1:])
    return ComparisonSummary(
        active_return=compounded_return(primary) - compounded_return(comparison),
        tracking_error=tracking_error,
        information_ratio=information_ratio,
        correlation=pearson_correlation(primary, comparison),
        beta=beta(primary, comparison),
        primary_cumulative=primary_cumulative,
        comparison_cumulative=comparison_cumulative,
        primary_drawdowns=tuple(underwater_drawdown(primary_wealth)[1:]),
        comparison_drawdowns=tuple(underwater_drawdown(comparison_wealth)[1:]),
    )


def horizon_compounded_returns(
    returns: Sequence[float],
    horizon_days: int,
) -> list[float]:
    """Return overlapping compounded returns over an explicit observation horizon."""
    values = _finite_values(returns, name="returns")
    if isinstance(horizon_days, bool) or horizon_days <= 0:
        raise ValueError("horizon_days must be a positive integer")
    if horizon_days > len(values):
        return []
    return [compounded_return(values[start : start + horizon_days]) for start in range(len(values) - horizon_days + 1)]


def historical_var_cvar(
    returns: Sequence[float],
    *,
    confidence_level: float,
    horizon_days: int = 1,
) -> HistoricalTailRisk:
    """Return empirical VaR/CVaR using the auditable higher observed quantile."""
    confidence_level = float(confidence_level)
    if not 0 < confidence_level < 1 or not math.isfinite(confidence_level):
        raise ValueError("confidence_level must be finite and between 0 and 1")
    horizon_returns = horizon_compounded_returns(returns, horizon_days)
    if not horizon_returns:
        raise ValueError("insufficient returns for the requested horizon")
    losses = sorted(max(-value, 0.0) for value in horizon_returns)
    quantile_index = max(0, math.ceil(confidence_level * len(losses)) - 1)
    value_at_risk = losses[quantile_index]
    tail = [loss for loss in losses if loss >= value_at_risk]
    conditional_value_at_risk = math.fsum(tail) / len(tail)
    return HistoricalTailRisk(
        value_at_risk=value_at_risk,
        conditional_value_at_risk=conditional_value_at_risk,
        horizon_returns=tuple(horizon_returns),
    )


__all__ = [
    "ComparisonSummary",
    "ContributionSummary",
    "DrawdownSummary",
    "HistoricalTailRisk",
    "annualized_sharpe",
    "annualized_sortino",
    "annualized_volatility",
    "beta",
    "comparison_summary",
    "compounded_return",
    "correlation_matrix",
    "covariance_matrix",
    "current_buy_and_hold_returns",
    "daily_risk_free_rate",
    "historical_var_cvar",
    "horizon_compounded_returns",
    "hypothetical_stress_return",
    "pairwise_correlation",
    "pearson_correlation",
    "period_returns_from_cumulative",
    "risk_contributions_from_covariance",
    "sample_covariance",
    "sample_standard_deviation",
    "sample_variance",
    "summarize_drawdown",
    "underwater_drawdown",
    "wealth_index",
]
