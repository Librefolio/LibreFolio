"""Joint block bootstrap resampling of real historical returns.

Why this module exists
----------------------
The archived decision ``risk-quant-engine-process-boundary`` states that NumPy
is *not a fallback production simulation engine*. This module is a deliberate,
declared departure from that sentence, not a quiet one.

A bootstrap is **resampling**, not stochastic evolution: it draws real observed
rows out of the user's own history. QuantLib has no such sampler, so there is
nothing to fall back *from*. NumPy here is the primary and only sampling path,
and it is chosen because it is more honest than the alternative: a Gaussian
process assumes a shape the data does not have, and systematically
underestimates the tails that a risk tool exists to show.

What "joint" buys
-----------------
Whole rows of the asset-by-time matrix are resampled together, so the
cross-sectional dependence between assets is carried along **by construction**.
No covariance is estimated, none is inverted, and no positive-semidefinite
check can fail — the class of errors that the parametric path raises as
``INVALID_COVARIANCE`` is unreachable here.

Regimes
-------
A regime is a *declared* hypothesis, never an estimated one. Only two
transformations are exact on a joint resample: scaling the dispersion of log
returns and shifting their level. Both leave the correlation matrix
mathematically invariant, which is precisely why the user-facing text says that
correlations stay those of their own history instead of claiming a number the
code does not produce.
"""

from __future__ import annotations

import time

import numpy as np

from backend.app.schemas.risk import RiskSimulationRegime
from backend.app.services.risk.quant.models import (
    SimulationEngineRequest,
    historical_returns_digest,
)

_CELL_BUDGET = 4_000_000
_CALM_DISPERSION_SCALE = 0.7
_CRISIS_DISPERSION_SCALE = 2.5
_CRISIS_ANNUAL_GROSS_FACTOR = 0.8
_SHOCK_GROSS_FACTOR = 0.65
_SIMULATED_DAYS_PER_YEAR = 365.0
_MINIMUM_PORTFOLIO_RETURN = -1.0 + 1e-12

_REGIME_DECLARED_DAYS: dict[RiskSimulationRegime, int | None] = {
    RiskSimulationRegime.CALM: None,
    RiskSimulationRegime.PROLONGED_CRISIS: 426,
    RiskSimulationRegime.SHOCK_RECOVERY: 61,
}


def resolve_block_length(observations: int, override: int | None = None) -> int:
    """Pick the block length that preserves short-range dependence.

    The moving-block rule of thumb is a block proportional to the cube root of
    the sample: long enough to carry volatility clustering across the join,
    short enough to still produce many distinct paths.
    """
    if override is not None:
        return max(1, min(override, observations))
    return max(2, min(observations, round(observations ** (1.0 / 3.0))))


def resolve_regime_days(regime: RiskSimulationRegime, horizon_days: int) -> tuple[int | None, int | None]:
    """Return the declared and effectively applied duration of a regime.

    They differ when the requested horizon is shorter than the hypothesis. The
    caller must disclose both: a fourteen-month crisis silently squeezed into a
    thirty-day horizon would be a different hypothesis wearing the same label.
    """
    if regime == RiskSimulationRegime.NONE:
        return None, None
    declared = _REGIME_DECLARED_DAYS[regime]
    if declared is None:
        return horizon_days, horizon_days
    return declared, min(declared, horizon_days)


def _regime_profile(
    regime: RiskSimulationRegime,
    horizon_days: int,
    applied_days: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Build the per-day dispersion scale and level shift of a regime."""
    scale = np.ones(horizon_days, dtype=np.float64)
    shift = np.zeros(horizon_days, dtype=np.float64)
    window = slice(0, applied_days)
    if regime == RiskSimulationRegime.CALM:
        scale[window] = _CALM_DISPERSION_SCALE
    elif regime == RiskSimulationRegime.PROLONGED_CRISIS:
        scale[window] = _CRISIS_DISPERSION_SCALE
        shift[window] = np.log(_CRISIS_ANNUAL_GROSS_FACTOR) / _SIMULATED_DAYS_PER_YEAR
    elif regime == RiskSimulationRegime.SHOCK_RECOVERY:
        shift[window] = np.log(_SHOCK_GROSS_FACTOR) / applied_days
    return scale, shift


def _draw_block_starts(
    rng: np.random.Generator,
    *,
    observations: int,
    path_count: int,
    block_count: int,
) -> np.ndarray:
    """Draw every block origin up front so chunking cannot move the seed.

    Reproducibility must not depend on how the work is sliced for memory, or a
    machine with a different chunk size would produce a different simulation
    from the same seed.
    """
    return rng.integers(0, observations, size=(path_count, block_count), dtype=np.int64)


def run_block_bootstrap(
    request: SimulationEngineRequest,
) -> tuple[np.ndarray, np.ndarray, dict[str, float], dict[str, int | None]]:
    """Resample the portfolio forward from the investor's own history."""
    assert request.historical_returns is not None
    assert request.historical_digest is not None
    assert request.bootstrap_seed is not None

    simple_returns = np.asarray(request.historical_returns, dtype=np.float64)
    recomputed = historical_returns_digest(simple_returns)
    if recomputed != request.historical_digest:
        raise ValueError("historical returns do not match the digest used to key this simulation")

    log_returns = np.log1p(simple_returns)
    if not np.isfinite(log_returns).all():
        raise ValueError("historical simple returns must be finite and greater than -1")

    observations, asset_count = log_returns.shape
    horizon_days = request.horizon_days
    path_count = request.path_count
    block_length = resolve_block_length(observations, request.block_length_days)
    block_count = -(-horizon_days // block_length)
    declared_days, applied_days = resolve_regime_days(request.regime, horizon_days)

    rng = np.random.default_rng(request.bootstrap_seed)
    sampling_started = time.perf_counter()
    starts = _draw_block_starts(
        rng,
        observations=observations,
        path_count=path_count,
        block_count=block_count,
    )
    sampling_seconds = time.perf_counter() - sampling_started

    asset_means = log_returns.mean(axis=0)
    scale, shift = (None, None)
    if request.regime != RiskSimulationRegime.NONE:
        assert applied_days is not None
        scale, shift = _regime_profile(request.regime, horizon_days, applied_days)

    weights = np.asarray(request.weights, dtype=np.float64)
    portfolio_returns = np.empty((path_count, horizon_days + 1), dtype=np.float64)
    portfolio_returns[:, 0] = 0.0
    terminal_log_returns = np.empty((path_count, asset_count), dtype=np.float64)

    offsets = np.arange(block_length, dtype=np.int64)
    chunk_size = max(1, _CELL_BUDGET // max(1, horizon_days * asset_count))
    resampling_seconds = 0.0
    aggregation_seconds = 0.0
    for start in range(0, path_count, chunk_size):
        stop = min(start + chunk_size, path_count)
        stage_started = time.perf_counter()
        indices = (starts[start:stop, :, None] + offsets) % observations
        indices = indices.reshape(stop - start, block_count * block_length)[:, :horizon_days]
        draws = log_returns[indices]
        if scale is not None:
            draws = asset_means + scale[None, :, None] * (draws - asset_means) + shift[None, :, None]
        resampling_seconds += time.perf_counter() - stage_started

        stage_started = time.perf_counter()
        cumulative_log = np.cumsum(draws, axis=1)
        growth = np.exp(cumulative_log)
        portfolio_returns[start:stop, 1:] = request.cash_weight + growth @ weights - 1.0
        terminal_log_returns[start:stop] = cumulative_log[:, -1, :]
        aggregation_seconds += time.perf_counter() - stage_started

    np.maximum(portfolio_returns, _MINIMUM_PORTFOLIO_RETURN, out=portfolio_returns)

    disclosure: dict[str, int | None] = {
        "block_length_days": block_length,
        "regime_declared_days": declared_days,
        "regime_applied_days": applied_days,
    }
    timings = {
        "rng_seconds": sampling_seconds,
        "process_evolution_seconds": resampling_seconds,
        "generation_evolution_seconds": 0.0,
        "path_aggregation_seconds": aggregation_seconds,
    }
    return portfolio_returns, terminal_log_returns, timings, disclosure


__all__ = [
    "resolve_block_length",
    "resolve_regime_days",
    "run_block_bootstrap",
]
