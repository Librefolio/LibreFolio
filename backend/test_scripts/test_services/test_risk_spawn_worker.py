"""Tests for isolated lazy quantitative workers."""

from __future__ import annotations

import asyncio
import os
import signal

import pytest

from backend.app.services.risk.quant.spawn_worker import (
    SpawnWorkerCrashedError,
    SpawnWorkerPool,
    SpawnWorkerQueueFullError,
    SpawnWorkerRemoteError,
    SpawnWorkerTimeoutError,
)

HANDLER_PATH = "backend.test_scripts.test_services.worker_handlers:" "dispatch_worker_fixture"


@pytest.mark.asyncio
async def test_spawn_worker_is_lazy_and_persistent() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=1,
        timeout_seconds=2,
    )
    try:
        assert pool.process_ids == ()

        first = await pool.submit(
            {"action": "echo", "value": "first"},
        )
        second = await pool.submit(
            {"action": "echo", "value": "second"},
        )

        assert first.payload["value"] == "first"
        assert second.payload["value"] == "second"
        assert first.worker_pid == second.worker_pid
        assert first.cold_start is True
        assert second.cold_start is False
        assert pool.process_ids == (first.worker_pid,)
    finally:
        await pool.shutdown()

    assert pool.process_ids == ()


@pytest.mark.asyncio
async def test_spawn_worker_remote_error_recycles_lane() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=0,
        timeout_seconds=2,
    )
    try:
        with pytest.raises(SpawnWorkerRemoteError) as exc_info:
            await pool.submit({"action": "fail"})
        assert exc_info.value.remote_type.endswith("ValueError")

        recovered = await pool.submit(
            {"action": "echo", "value": "recovered"},
        )
        assert recovered.payload["value"] == "recovered"
        assert recovered.cold_start is True
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_spawn_worker_timeout_does_not_block_event_loop() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=0,
        timeout_seconds=0.75,
    )
    ticks = 0

    async def tick() -> None:
        nonlocal ticks
        while ticks < 5:
            await asyncio.sleep(0.02)
            ticks += 1

    try:
        ticker = asyncio.create_task(tick())
        with pytest.raises(SpawnWorkerTimeoutError):
            await pool.submit(
                {"action": "sleep", "seconds": 2},
            )
        await ticker
        assert ticks == 5

        pool.timeout_seconds = 3
        recovered = await pool.submit(
            {"action": "echo", "value": "recovered"},
        )
        assert recovered.cold_start is True
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_spawn_worker_crash_recycles_lane(tmp_path) -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=0,
        timeout_seconds=2,
    )
    try:
        marker = tmp_path / "worker-started"
        crashed = asyncio.create_task(
            pool.submit(
                {
                    "action": "mark_and_sleep",
                    "marker": str(marker),
                    "seconds": 2,
                },
            ),
        )
        while not marker.exists():
            await asyncio.sleep(0.01)
        crashed_pid = pool.process_ids[0]
        os.kill(crashed_pid, signal.SIGKILL)
        with pytest.raises(SpawnWorkerCrashedError):
            await crashed

        recovered = await pool.submit(
            {"action": "echo", "value": "recovered"},
        )
        assert recovered.cold_start is True
        assert recovered.worker_pid != crashed_pid
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_spawn_worker_rejects_jobs_beyond_capacity() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=1,
        timeout_seconds=2,
    )
    try:
        first = asyncio.create_task(
            pool.submit({"action": "sleep", "seconds": 0.3}),
        )
        await asyncio.sleep(0.02)
        second = asyncio.create_task(
            pool.submit({"action": "sleep", "seconds": 0.1}),
        )
        await asyncio.sleep(0.02)

        with pytest.raises(SpawnWorkerQueueFullError):
            await pool.submit(
                {"action": "echo", "value": "rejected"},
            )

        await first
        await second
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_spawn_worker_cancellation_does_not_reuse_busy_lane() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=0,
        timeout_seconds=3,
    )
    try:
        job = asyncio.create_task(
            pool.submit({"action": "sleep", "seconds": 0.3}),
        )
        await asyncio.sleep(0.05)
        job.cancel()
        with pytest.raises(asyncio.CancelledError):
            await job

        recovered = await pool.submit(
            {"action": "echo", "value": "recovered"},
        )
        assert recovered.payload["value"] == "recovered"
        assert recovered.cold_start is False
    finally:
        await pool.shutdown()
