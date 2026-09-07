"""Historical parameter estimation for the first GBM simulation model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np


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


__all__ = [
    "GbmParameterEstimates",
    "estimate_gbm_parameters",
]
