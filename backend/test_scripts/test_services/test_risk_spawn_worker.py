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

# Every submit on a cold lane spawns a fresh interpreter, and this suite runs on
# a machine already busy with 8 parallel workers. A budget is only ever waited
# out on the *failure* path, so making it generous costs nothing on the success
# path these tests exercise — while 2 s, comfortable when idle, turned red under
# load for a reason that has nothing to do with what the tests are about.
#
# The one test that *measures* the timeout must keep a tight budget: see
# TIGHT_TIMEOUT_S.
COLD_START_TIMEOUT_S = 30.0

# Deliberately smaller than the job it submits (2 s), so the timeout fires by
# construction rather than by machine speed: a slower machine only makes it
# fire more surely. This is the one place where the number is the subject.
TIGHT_TIMEOUT_S = 0.75


async def wait_until(predicate, *, timeout: float = 10.0) -> None:
    """Wait for a state change. Same reasoning as COLD_START_TIMEOUT_S: this is a
    success-path wait, so a generous ceiling costs nothing and only bounds how
    long a genuine failure takes to report."""
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError("condition was not met before timeout")
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_spawn_worker_is_lazy_and_persistent() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=1,
        timeout_seconds=COLD_START_TIMEOUT_S,
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
async def test_spawn_worker_reaps_idle_lane_and_restarts_lazily() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=0,
        timeout_seconds=COLD_START_TIMEOUT_S,
        idle_timeout_seconds=0.1,
    )
    try:
        first = await pool.submit(
            {"action": "echo", "value": "first"},
        )
        assert pool.process_ids == (first.worker_pid,)

        await wait_until(lambda: pool.process_ids == ())

        restarted = await pool.submit(
            {"action": "echo", "value": "restarted"},
        )
        assert restarted.payload["value"] == "restarted"
        assert restarted.cold_start is True
        assert restarted.worker_pid != first.worker_pid
    finally:
        await pool.shutdown()

    assert pool.process_ids == ()


@pytest.mark.asyncio
async def test_spawn_worker_never_reaps_queued_or_inflight_jobs() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=1,
        timeout_seconds=COLD_START_TIMEOUT_S,
        idle_timeout_seconds=0.05,
    )
    try:
        first = asyncio.create_task(
            pool.submit({"action": "sleep", "seconds": 0.2}),
        )
        await wait_until(lambda: len(pool.process_ids) == 1)
        active_pid = pool.process_ids[0]
        second = asyncio.create_task(
            pool.submit({"action": "sleep", "seconds": 0.15}),
        )

        await asyncio.sleep(0.12)
        assert pool.process_ids == (active_pid,)

        await first
        await second
        await wait_until(lambda: pool.process_ids == ())
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_spawn_worker_repeats_idle_restart_cycles_without_orphans() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=0,
        timeout_seconds=COLD_START_TIMEOUT_S,
        idle_timeout_seconds=0.05,
    )
    seen_pids = []
    try:
        for cycle in range(3):
            result = await pool.submit(
                {"action": "echo", "value": cycle},
            )
            seen_pids.append(result.worker_pid)
            await wait_until(lambda: pool.process_ids == ())
    finally:
        await pool.shutdown()
        await pool.shutdown()

    assert len(set(seen_pids)) == 3
    assert pool.process_ids == ()


@pytest.mark.asyncio
async def test_spawn_worker_reaps_and_restarts_every_lane() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=2,
        queue_capacity=0,
        timeout_seconds=COLD_START_TIMEOUT_S,
        idle_timeout_seconds=0.05,
    )
    try:
        first_cycle = await asyncio.gather(
            pool.submit({"action": "sleep", "seconds": 0.05}),
            pool.submit({"action": "sleep", "seconds": 0.05}),
        )
        first_pids = {result.worker_pid for result in first_cycle}
        assert len(first_pids) == 2

        await wait_until(lambda: pool.process_ids == ())

        second_cycle = await asyncio.gather(
            pool.submit({"action": "sleep", "seconds": 0.05}),
            pool.submit({"action": "sleep", "seconds": 0.05}),
        )
        second_pids = {result.worker_pid for result in second_cycle}
        assert len(second_pids) == 2
        assert first_pids.isdisjoint(second_pids)
        assert all(result.cold_start for result in second_cycle)
    finally:
        await pool.shutdown()

    assert pool.process_ids == ()


@pytest.mark.asyncio
async def test_spawn_worker_shutdown_cancels_pending_idle_reap() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=0,
        timeout_seconds=COLD_START_TIMEOUT_S,
        idle_timeout_seconds=0.2,
    )
    await pool.submit({"action": "echo", "value": "done"})

    await pool.shutdown()
    await asyncio.sleep(0.25)

    assert pool.process_ids == ()


@pytest.mark.asyncio
async def test_spawn_worker_remote_error_recycles_lane() -> None:
    pool = SpawnWorkerPool(
        name="fixture",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=0,
        timeout_seconds=COLD_START_TIMEOUT_S,
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
        timeout_seconds=TIGHT_TIMEOUT_S,
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

        pool.timeout_seconds = COLD_START_TIMEOUT_S
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
        timeout_seconds=COLD_START_TIMEOUT_S,
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
        timeout_seconds=COLD_START_TIMEOUT_S,
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
        timeout_seconds=COLD_START_TIMEOUT_S,
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
