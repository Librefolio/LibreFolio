"""Historical parameter estimation for the first GBM simulation model."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

_NORMAL_95_PERCENT = 1.959963984540054


@dataclass(frozen=True, slots=True)
class GbmParameterEstimates:
    """Annual GBM parameters estimated from aligned simple returns."""

    asset_ids: tuple[int, ...]
    annual_drifts: tuple[float, ...]
    annual_covariance: tuple[tuple[float, ...], ...]
    observations: int


def estimate_gbm_parameters(
    returns_by_asset: Mapping[int, Sequence[float]],
    *,
    annualization_factor: float,
) -> GbmParameterEstimates:
    """Estimate annual GBM drift and covariance from aligned simple returns."""
    asset_ids = tuple(returns_by_asset)
    if not asset_ids:
        raise ValueError("GBM estimation requires at least one asset")
    if not np.isfinite(annualization_factor) or annualization_factor <= 0:
        raise ValueError("GBM estimation requires a positive annualization factor")

    rows = [np.asarray(returns_by_asset[asset_id], dtype=float) for asset_id in asset_ids]
    observations = len(rows[0])
    if observations < 2 or any(len(row) != observations for row in rows):
        raise ValueError("GBM estimation requires aligned return series with at least two observations")
    simple_returns = np.column_stack(rows)
    if not np.isfinite(simple_returns).all() or np.any(simple_returns <= -1):
        raise ValueError("GBM estimation requires finite simple returns greater than -1")

    log_returns = np.log1p(simple_returns)
    covariance = np.atleast_2d(
        np.cov(
            log_returns,
            rowvar=False,
            ddof=1,
        )
    )
    annual_covariance = 0.5 * (covariance + covariance.T) * annualization_factor
    annual_drifts = log_returns.mean(axis=0) * annualization_factor + 0.5 * np.diag(annual_covariance)
    if not np.isfinite(annual_drifts).all() or not np.isfinite(annual_covariance).all():
        raise ValueError("GBM estimation produced non-finite parameters")

    return GbmParameterEstimates(
        asset_ids=asset_ids,
        annual_drifts=tuple(float(value) for value in annual_drifts),
        annual_covariance=tuple(tuple(float(value) for value in row) for row in annual_covariance),
        observations=observations,
    )


def align_simple_returns(
    returns_by_asset: Mapping[int, Sequence[float]],
    asset_ids: Sequence[int],
) -> np.ndarray:
    """Stack aligned per-asset simple returns into an observation-by-asset matrix.

    Resampling needs the raw matrix rather than estimated parameters: rows are
    drawn whole, so the columns must line up in time exactly as they do here.
    """
    if not asset_ids:
        raise ValueError("return alignment requires at least one asset")
    rows = [np.asarray(returns_by_asset[asset_id], dtype=float) for asset_id in asset_ids]
    observations = len(rows[0])
    if observations < 2 or any(len(row) != observations for row in rows):
        raise ValueError("return alignment requires aligned series with at least two observations")
    matrix = np.column_stack(rows)
    if not np.isfinite(matrix).all() or np.any(matrix <= -1):
        raise ValueError("return alignment requires finite simple returns greater than -1")
    return matrix


def estimate_drift_uncertainty(
    returns_by_asset: Mapping[int, Sequence[float]],
    asset_ids: Sequence[int],
    weights: Sequence[float],
    *,
    horizon_days: int,
    z_score: float = _NORMAL_95_PERCENT,
) -> tuple[float, int]:
    """Return the 95% confidence factor on the portfolio drift, and its sample size.

    A simulated band is dispersion *conditional on* the estimated drift. The drift
    is itself a sample mean, so it carries a standard error of sigma/sqrt(n), and
    over the horizon that error compounds along with everything else. A band drawn
    without it reads as the whole uncertainty while being only part of it.

    The result is a multiplicative factor because the quantity it qualifies is
    compounded: over a horizon an additive margin would be false.

    Weights are the portfolio's own, so cash enters as the weight that is missing
    from their sum and correctly damps the estimate. Renormalising onto the risky
    sleeve instead would answer a question about a portfolio the user does not hold.
    """
    if horizon_days <= 0:
        raise ValueError("drift uncertainty requires a positive horizon")
    matrix = align_simple_returns(returns_by_asset, asset_ids)
    weight_vector = np.asarray(weights, dtype=float)
    if weight_vector.shape != (matrix.shape[1],):
        raise ValueError("drift uncertainty requires one weight per aligned asset")
    portfolio_simple = matrix @ weight_vector
    if np.any(portfolio_simple <= -1):
        raise ValueError("drift uncertainty requires portfolio returns greater than -1")

    log_returns = np.log1p(portfolio_simple)
    observations = int(log_returns.size)
    sigma = float(log_returns.std(ddof=1))
    if not np.isfinite(sigma):
        raise ValueError("drift uncertainty produced a non-finite dispersion")
    standard_error = horizon_days * sigma / math.sqrt(observations)
    return math.exp(z_score * standard_error), observations


__all__ = [
    "GbmParameterEstimates",
    "align_simple_returns",
    "estimate_drift_uncertainty",
    "estimate_gbm_parameters",
]
