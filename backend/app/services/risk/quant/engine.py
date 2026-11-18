"""Parent-side cache and process boundary for QuantLib simulation."""

from __future__ import annotations

import asyncio
import threading

from backend.app.services.risk.quant.models import (
    MAX_HISTORY_OBSERVATIONS,
    SimulationEngineRequest,
    SimulationEngineResult,
    simulation_cache_key,
)
from backend.app.services.risk.quant.spawn_worker import (
    SpawnWorkerResult,
)
from backend.app.services.risk.quant.workers import (
    get_simulation_worker_pool,
)
from backend.app.utils.runtime.cache import get_ttl_cache

MAX_PORTFOLIO_CELLS = 20_000_000
MAX_STOCHASTIC_CELLS = 200_000_000
MAX_HISTORY_CELLS = 250_000
# The fewest paths a simulation falls to before it is «too large» (developer's Q5 a, 16/11/2026, «per ora»).
MIN_SIMULATION_PATHS = 1024

_simulation_cache = get_ttl_cache(
    "risk_simulation",
    maxsize=32,
    ttl=1800,
)
_inflight_lock = threading.Lock()
_inflight: dict[
    str,
    asyncio.Future[SimulationEngineResult],
] = {}


class SimulationResourceLimitError(ValueError):
    """The requested simulation exceeds a conservative resource budget."""

    def __init__(
        self,
        message: str,
        *,
        metric: str,
        actual: int,
        limit: int,
    ) -> None:
        super().__init__(message)
        self.metric = metric
        self.actual = actual
        self.limit = limit


async def run_simulation(
    request: SimulationEngineRequest,
    *,
    algorithm_version: str,
) -> tuple[
    SimulationEngineResult,
    bool,
    SpawnWorkerResult | None,
]:
    """Run or retrieve one content-keyed QuantLib result."""
    validate_resource_budget(request)
    key = simulation_cache_key(
        request,
        algorithm_version=algorithm_version,
    )
    cached, found = _simulation_cache.get(key)
    if found:
        return cached.model_copy(deep=True), True, None

    leader = False
    with _inflight_lock:
        cached, found = _simulation_cache.get(key)
        if found:
            return cached.model_copy(deep=True), True, None
        future = _inflight.get(key)
        if future is None:
            future = asyncio.get_running_loop().create_future()
            _inflight[key] = future
            leader = True

    if not leader:
        result = await asyncio.shield(future)
        return result.model_copy(deep=True), True, None

    try:
        worker_result = await get_simulation_worker_pool().submit(
            request.model_dump(mode="json"),
        )
        result = SimulationEngineResult.model_validate(
            worker_result.payload,
        )
        _simulation_cache.set(
            key,
            result.model_copy(deep=True),
        )
        if not future.done():
            future.set_result(result.model_copy(deep=True))
        return result, False, worker_result
    except asyncio.CancelledError:
        if not future.done():
            future.cancel()
        raise
    except Exception as exc:
        if not future.done():
            future.set_exception(exc)
            future.exception()
        raise
    finally:
        with _inflight_lock:
            _inflight.pop(key, None)


def clear_simulation_cache() -> None:
    """Clear only the content-keyed simulation cache."""
    _simulation_cache.clear()


def history_observation_cap(asset_count: int) -> int:
    """The most observations a bootstrap history may carry across the process boundary for ``asset_count`` positions.

    Both ceilings at once: ``MAX_HISTORY_OBSERVATIONS`` rows, and ``MAX_HISTORY_CELLS`` rows × positions. A longer
    history keeps its most recent observations up to this count (RN-16, developer's Q4 c with Q5's rule).
    """
    return min(MAX_HISTORY_OBSERVATIONS, MAX_HISTORY_CELLS // max(asset_count, 1))


def fit_path_count(requested: int, *, horizon_days: int, asset_count: int) -> int | None:
    """The path count a simulation runs: ``requested`` when it fits the budgets, otherwise the largest power of two
    below it that does, never under ``MIN_SIMULATION_PATHS`` — None when not even those fit (RN-16, developer's Q5 a).

    The budgets are :func:`validate_resource_budget`'s two path budgets: the percentile matrix (paths × days + 1) and
    the stochastic workload (paths × days × positions). A request that fits stays as asked, power of two or not.
    """

    def fits(paths: int) -> bool:
        return paths * (horizon_days + 1) <= MAX_PORTFOLIO_CELLS and paths * horizon_days * asset_count <= MAX_STOCHASTIC_CELLS

    if fits(requested):
        return requested
    paths = 1 << (requested.bit_length() - 1)
    if paths == requested:
        paths //= 2
    while paths >= MIN_SIMULATION_PATHS:
        if fits(paths):
            return paths
        paths //= 2
    return None


def validate_resource_budget(
    request: SimulationEngineRequest,
) -> None:
    """Reject path matrices that exceed self-hosted limits."""
    portfolio_cells = request.path_count * (request.horizon_days + 1)
    if portfolio_cells > MAX_PORTFOLIO_CELLS:
        raise SimulationResourceLimitError(
            "Simulation percentile matrix exceeds the memory budget",
            metric="portfolio_cells",
            actual=portfolio_cells,
            limit=MAX_PORTFOLIO_CELLS,
        )
    stochastic_cells = request.path_count * request.horizon_days * len(request.asset_ids)
    if stochastic_cells > MAX_STOCHASTIC_CELLS:
        raise SimulationResourceLimitError(
            "Simulation stochastic workload exceeds the compute budget",
            metric="stochastic_cells",
            actual=stochastic_cells,
            limit=MAX_STOCHASTIC_CELLS,
        )
    if request.historical_returns is None:
        return
    history_cells = len(request.historical_returns) * len(request.asset_ids)
    if history_cells > MAX_HISTORY_CELLS:
        raise SimulationResourceLimitError(
            "Simulation history exceeds the process-boundary budget",
            metric="history_cells",
            actual=history_cells,
            limit=MAX_HISTORY_CELLS,
        )


__all__ = [
    "MAX_HISTORY_CELLS",
    "MAX_PORTFOLIO_CELLS",
    "MAX_STOCHASTIC_CELLS",
    "MIN_SIMULATION_PATHS",
    "SimulationResourceLimitError",
    "clear_simulation_cache",
    "fit_path_count",
    "history_observation_cap",
    "run_simulation",
    "validate_resource_budget",
]
