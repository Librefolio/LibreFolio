"""Separate lazy process pools for simulation and optimization."""

from __future__ import annotations

import asyncio
import threading

from backend.app.config import get_settings
from backend.app.services.risk.quant.spawn_worker import (
    SpawnWorkerPool,
)

_pool_lock = threading.Lock()
_simulation_pool: SpawnWorkerPool | None = None
_optimization_pool: SpawnWorkerPool | None = None


def get_simulation_worker_pool() -> SpawnWorkerPool:
    global _simulation_pool
    with _pool_lock:
        if _simulation_pool is None:
            settings = get_settings()
            _simulation_pool = SpawnWorkerPool(
                name="risk-simulation",
                handler_path=("backend.app.services.risk.quant." "quantlib_worker:execute_simulation_job"),
                workers=settings.RISK_SIMULATION_WORKERS,
                queue_capacity=(settings.RISK_SIMULATION_QUEUE_CAPACITY),
                timeout_seconds=(settings.RISK_SIMULATION_TIMEOUT_SECONDS),
                idle_timeout_seconds=(settings.RISK_SIMULATION_IDLE_TIMEOUT_SECONDS),
            )
        return _simulation_pool


def get_optimization_worker_pool() -> SpawnWorkerPool:
    global _optimization_pool
    with _pool_lock:
        if _optimization_pool is None:
            settings = get_settings()
            _optimization_pool = SpawnWorkerPool(
                name="risk-optimization",
                handler_path=("backend.app.services.risk.quant." "riskfolio_worker:execute_optimization_job"),
                workers=settings.RISK_OPTIMIZATION_WORKERS,
                queue_capacity=(settings.RISK_OPTIMIZATION_QUEUE_CAPACITY),
                timeout_seconds=(settings.RISK_OPTIMIZATION_TIMEOUT_SECONDS),
                idle_timeout_seconds=(settings.RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS),
            )
        return _optimization_pool


async def shutdown_quant_worker_pools() -> None:
    global _optimization_pool
    global _simulation_pool
    with _pool_lock:
        pools = tuple(
            pool
            for pool in (
                _simulation_pool,
                _optimization_pool,
            )
            if pool is not None
        )
        _simulation_pool = None
        _optimization_pool = None
    if pools:
        await asyncio.gather(
            *(pool.shutdown() for pool in pools),
        )


__all__ = [
    "get_optimization_worker_pool",
    "get_simulation_worker_pool",
    "shutdown_quant_worker_pools",
]
