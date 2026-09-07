"""Lazy persistent spawn workers for native quantitative engines."""

from __future__ import annotations

import asyncio
import importlib
import logging
import multiprocessing
import os
import pickle
import queue
import resource
import sys
import time
import traceback
import uuid
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class SpawnWorkerError(RuntimeError):
    """Base failure raised by the spawned quantitative boundary."""


class SpawnWorkerQueueFullError(SpawnWorkerError):
    """The bounded pool has no capacity for another job."""


class SpawnWorkerTimeoutError(SpawnWorkerError):
    """A native job exceeded its hard execution timeout."""


class SpawnWorkerCrashedError(SpawnWorkerError):
    """The child process exited before returning a result."""


class SpawnWorkerRemoteError(SpawnWorkerError):
    """The child handler raised a serialized exception."""

    def __init__(
        self,
        message: str,
        *,
        remote_type: str,
        remote_traceback: str,
    ) -> None:
        super().__init__(message)
        self.remote_type = remote_type
        self.remote_traceback = remote_traceback


@dataclass(frozen=True, slots=True)
class SpawnWorkerResult:
    """One child result plus process-boundary timings."""

    payload: Any
    worker_pid: int
    cold_start: bool
    queue_wait_seconds: float
    execution_seconds: float
    round_trip_seconds: float
    peak_rss_bytes: int


def _peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def _resolve_handler(handler_path: str):
    module_name, separator, attribute_name = handler_path.partition(":")
    if not separator or not module_name or not attribute_name:
        raise ValueError(
            "worker handler path must use 'module:attribute'",
        )
    module = importlib.import_module(module_name)
    handler = getattr(module, attribute_name)
    if not callable(handler):
        raise TypeError(
            f"worker handler '{handler_path}' is not callable",
        )
    return handler


def _worker_main(
    handler_path: str,
    request_queue,
    response_connection,
) -> None:
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"
    handler = _resolve_handler(handler_path)
    try:
        while True:
            message = request_queue.get()
            if message is None:
                return
            job_id, payload = message
            started = time.perf_counter()
            try:
                result = handler(payload)
                pickle.dumps(result)
                response = {
                    "job_id": job_id,
                    "ok": True,
                    "payload": result,
                    "worker_pid": os.getpid(),
                    "execution_seconds": (time.perf_counter() - started),
                    "peak_rss_bytes": _peak_rss_bytes(),
                }
            except Exception as exc:
                response = {
                    "job_id": job_id,
                    "ok": False,
                    "error_type": (f"{type(exc).__module__}." f"{type(exc).__qualname__}"),
                    "error_message": str(exc),
                    "traceback": traceback.format_exc(),
                    "worker_pid": os.getpid(),
                    "execution_seconds": (time.perf_counter() - started),
                    "peak_rss_bytes": _peak_rss_bytes(),
                }
            response_connection.send(response)
    except (BrokenPipeError, EOFError, OSError):
        return
    finally:
        response_connection.close()


class _WorkerLane:
    def __init__(
        self,
        *,
        context,
        pool_name: str,
        lane_index: int,
        handler_path: str,
    ) -> None:
        self._context = context
        self._pool_name = pool_name
        self._lane_index = lane_index
        self._handler_path = handler_path
        self._process = None
        self._request_queue = None
        self._response_connection = None
        self._jobs_completed = 0

    @property
    def process_id(self) -> int | None:
        if self._process is None:
            return None
        return self._process.pid

    def _start(self) -> None:
        if self._process is not None and self._process.is_alive():
            return
        self._close_channels()
        self._request_queue = self._context.Queue(maxsize=1)
        parent_response, child_response = self._context.Pipe(
            duplex=False,
        )
        self._response_connection = parent_response
        self._process = self._context.Process(
            target=_worker_main,
            args=(
                self._handler_path,
                self._request_queue,
                child_response,
            ),
            name=(f"{self._pool_name}-" f"{self._lane_index + 1}"),
            daemon=True,
        )
        try:
            self._process.start()
        except BaseException:
            child_response.close()
            self._process = None
            self._close_channels()
            raise
        child_response.close()
        self._jobs_completed = 0

    def _wait_response(
        self,
        *,
        job_id: str,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while True:
            process = self._process
            if process is None:
                raise SpawnWorkerCrashedError(
                    f"{self._pool_name} worker is not running",
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SpawnWorkerTimeoutError(
                    f"{self._pool_name} job exceeded " f"{timeout_seconds:g}s",
                )
            try:
                if not self._response_connection.poll(
                    min(0.1, remaining),
                ):
                    if not process.is_alive():
                        raise SpawnWorkerCrashedError(
                            f"{self._pool_name} worker exited " f"with code {process.exitcode}",
                        )
                    continue
                response = self._response_connection.recv()
            except SpawnWorkerCrashedError:
                raise
            except (EOFError, OSError) as exc:
                if not process.is_alive():
                    raise SpawnWorkerCrashedError(
                        f"{self._pool_name} worker exited " f"with code {process.exitcode}",
                    ) from exc
                raise SpawnWorkerCrashedError(
                    f"{self._pool_name} response channel failed",
                ) from exc
            if response.get("job_id") != job_id:
                raise SpawnWorkerCrashedError(
                    f"{self._pool_name} returned a mismatched job",
                )
            return response

    def run(
        self,
        payload: Any,
        *,
        timeout_seconds: float,
        queue_wait_seconds: float,
    ) -> SpawnWorkerResult:
        pickle.dumps(payload)
        self._start()
        job_id = uuid.uuid4().hex
        cold_start = self._jobs_completed == 0
        round_trip_started = time.perf_counter()
        try:
            self._request_queue.put(
                (job_id, payload),
                timeout=min(1.0, timeout_seconds),
            )
            response = self._wait_response(
                job_id=job_id,
                timeout_seconds=timeout_seconds,
            )
        except Exception:
            self.stop()
            raise
        if not response["ok"]:
            self.stop()
            raise SpawnWorkerRemoteError(
                response["error_message"],
                remote_type=response["error_type"],
                remote_traceback=response["traceback"],
            )
        self._jobs_completed += 1
        return SpawnWorkerResult(
            payload=response["payload"],
            worker_pid=response["worker_pid"],
            cold_start=cold_start,
            queue_wait_seconds=queue_wait_seconds,
            execution_seconds=response["execution_seconds"],
            round_trip_seconds=(time.perf_counter() - round_trip_started),
            peak_rss_bytes=response["peak_rss_bytes"],
        )

    def stop(self) -> None:
        process = self._process
        if process is not None:
            if process.is_alive():
                try:
                    self._request_queue.put_nowait(None)
                except (queue.Full, ValueError, OSError):
                    pass
                process.join(timeout=1.0)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2.0)
            if process.is_alive():
                process.kill()
                process.join(timeout=1.0)
            if not process.is_alive():
                process.close()
        self._process = None
        self._jobs_completed = 0
        self._close_channels()

    def _close_channels(self) -> None:
        if self._request_queue is not None:
            try:
                self._request_queue.close()
                self._request_queue.join_thread()
            except (ValueError, OSError):
                pass
        if self._response_connection is not None:
            try:
                self._response_connection.close()
            except OSError:
                pass
        self._request_queue = None
        self._response_connection = None


class SpawnWorkerPool:
    """Bounded lazy pool of persistent independent spawn workers."""

    def __init__(
        self,
        *,
        name: str,
        handler_path: str,
        workers: int,
        queue_capacity: int,
        timeout_seconds: float,
        idle_timeout_seconds: float = 0.0,
    ) -> None:
        if workers < 1:
            raise ValueError("spawn worker count must be positive")
        if queue_capacity < 0:
            raise ValueError(
                "spawn worker queue capacity cannot be negative",
            )
        if timeout_seconds <= 0:
            raise ValueError(
                "spawn worker timeout must be positive",
            )
        if idle_timeout_seconds < 0:
            raise ValueError(
                "spawn worker idle timeout cannot be negative",
            )
        self.name = name
        self.handler_path = handler_path
        self.workers = workers
        self.queue_capacity = queue_capacity
        self.timeout_seconds = timeout_seconds
        self.idle_timeout_seconds = idle_timeout_seconds
        context = multiprocessing.get_context("spawn")
        self._lanes = [
            _WorkerLane(
                context=context,
                pool_name=name,
                lane_index=index,
                handler_path=handler_path,
            )
            for index in range(workers)
        ]
        self._available: asyncio.Queue[int] = asyncio.Queue(
            maxsize=workers,
        )
        for index in range(workers):
            self._available.put_nowait(index)
        self._state_lock = asyncio.Lock()
        self._pending = 0
        self._closed = False
        self._idle_generation = 0
        self._idle_task: asyncio.Task[None] | None = None

    @property
    def process_ids(self) -> tuple[int, ...]:
        return tuple(process_id for lane in self._lanes if (process_id := lane.process_id) is not None)

    async def submit(self, payload: Any) -> SpawnWorkerResult:
        queued_at = time.perf_counter()
        async with self._state_lock:
            if self._closed:
                raise SpawnWorkerError(
                    f"{self.name} pool is closed",
                )
            self._cancel_idle_reap()
            capacity = self.workers + self.queue_capacity
            if self._pending >= capacity:
                raise SpawnWorkerQueueFullError(
                    f"{self.name} queue is full",
                )
            self._pending += 1
        lane_index: int | None = None
        try:
            lane_index = await self._available.get()
            queue_wait_seconds = time.perf_counter() - queued_at
            worker_task = asyncio.create_task(
                asyncio.to_thread(
                    self._lanes[lane_index].run,
                    payload,
                    timeout_seconds=self.timeout_seconds,
                    queue_wait_seconds=queue_wait_seconds,
                ),
            )
            try:
                return await asyncio.shield(worker_task)
            except asyncio.CancelledError:
                await asyncio.shield(worker_task)
                raise
        finally:
            if lane_index is not None:
                self._available.put_nowait(lane_index)
            async with self._state_lock:
                self._pending -= 1
                if self._pending == 0:
                    self._schedule_idle_reap()

    async def shutdown(self) -> None:
        idle_task: asyncio.Task[None] | None
        async with self._state_lock:
            if self._closed:
                return
            self._closed = True
            self._idle_generation += 1
            idle_task = self._idle_task
            self._idle_task = None
            if idle_task is not None and not idle_task.done():
                idle_task.cancel()
        if idle_task is not None:
            await asyncio.gather(idle_task, return_exceptions=True)
        await asyncio.gather(*(asyncio.to_thread(lane.stop) for lane in self._lanes))

    def _cancel_idle_reap(self) -> None:
        self._idle_generation += 1
        task = self._idle_task
        self._idle_task = None
        if task is not None and not task.done():
            task.cancel()

    def _schedule_idle_reap(self) -> None:
        if self.idle_timeout_seconds <= 0 or self._closed or not self.process_ids:
            return
        self._idle_generation += 1
        generation = self._idle_generation
        task = asyncio.create_task(
            self._reap_after_idle(generation),
            name=f"{self.name}-idle-reaper",
        )
        self._idle_task = task
        task.add_done_callback(self._idle_reap_done)

    def _idle_reap_done(self, task: asyncio.Task[None]) -> None:
        if self._idle_task is task:
            self._idle_task = None
        if task.cancelled():
            return
        exception = task.exception()
        if exception is not None:
            logger.error(
                "%s idle reaper failed",
                self.name,
                exc_info=exception,
            )

    async def _reap_after_idle(self, generation: int) -> None:
        await asyncio.sleep(self.idle_timeout_seconds)
        async with self._state_lock:
            if self._closed or self._pending != 0 or generation != self._idle_generation:
                return
            self._idle_task = None
            await asyncio.gather(*(asyncio.to_thread(lane.stop) for lane in self._lanes))


__all__ = [
    "SpawnWorkerCrashedError",
    "SpawnWorkerError",
    "SpawnWorkerPool",
    "SpawnWorkerQueueFullError",
    "SpawnWorkerRemoteError",
    "SpawnWorkerResult",
    "SpawnWorkerTimeoutError",
]
