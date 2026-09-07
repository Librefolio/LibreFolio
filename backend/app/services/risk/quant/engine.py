"""Parent-side cache and process boundary for QuantLib simulation."""

from __future__ import annotations

import asyncio
import threading

from backend.app.services.risk.quant.models import (
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
from backend.app.utils.cache_utils import get_ttl_cache

MAX_PORTFOLIO_CELLS = 20_000_000
MAX_STOCHASTIC_CELLS = 200_000_000

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


__all__ = [
    "MAX_PORTFOLIO_CELLS",
    "MAX_STOCHASTIC_CELLS",
    "SimulationResourceLimitError",
    "clear_simulation_cache",
    "run_simulation",
    "validate_resource_budget",
]
