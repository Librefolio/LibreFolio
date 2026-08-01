"""Parent-side cache and process boundary for Riskfolio optimization."""

from __future__ import annotations

import asyncio
import threading

from backend.app.services.risk.quant.optimization_models import (
    OptimizationEngineRequest,
    OptimizationEngineResult,
    optimization_cache_key,
)
from backend.app.services.risk.quant.spawn_worker import (
    SpawnWorkerResult,
)
from backend.app.services.risk.quant.workers import (
    get_optimization_worker_pool,
)
from backend.app.utils.cache_utils import get_ttl_cache

MAX_OPTIMIZATION_CELLS = 2_000_000

_optimization_cache = get_ttl_cache(
    "risk_optimization",
    maxsize=32,
    ttl=1800,
)
_inflight_lock = threading.Lock()
_inflight: dict[
    str,
    asyncio.Future[OptimizationEngineResult],
] = {}


class OptimizationResourceLimitError(ValueError):
    """The aligned return matrix exceeds the worker budget."""

    def __init__(
        self,
        actual: int,
        limit: int,
    ) -> None:
        super().__init__(
            "Optimization return matrix exceeds the resource budget",
        )
        self.actual = actual
        self.limit = limit


async def run_optimization(
    request: OptimizationEngineRequest,
    *,
    algorithm_version: str,
) -> tuple[
    OptimizationEngineResult,
    bool,
    SpawnWorkerResult | None,
]:
    cells = len(request.returns) * len(request.asset_ids)
    if cells > MAX_OPTIMIZATION_CELLS:
        raise OptimizationResourceLimitError(
            cells,
            MAX_OPTIMIZATION_CELLS,
        )
    key = optimization_cache_key(
        request,
        algorithm_version=algorithm_version,
    )
    cached, found = _optimization_cache.get(key)
    if found:
        return cached.model_copy(deep=True), True, None

    leader = False
    with _inflight_lock:
        cached, found = _optimization_cache.get(key)
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
        worker_result = await get_optimization_worker_pool().submit(
            request.model_dump(mode="json"),
        )
        result = OptimizationEngineResult.model_validate(
            worker_result.payload,
        )
        _optimization_cache.set(
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


def clear_optimization_cache() -> None:
    _optimization_cache.clear()


__all__ = [
    "MAX_OPTIMIZATION_CELLS",
    "OptimizationResourceLimitError",
    "clear_optimization_cache",
    "run_optimization",
]
