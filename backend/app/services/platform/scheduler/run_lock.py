"""The scheduler's lock across processes: one run of the jobs at a time for one data directory (Z-11, decision N71).

Owner: workstream Z (release 1.3). With several uvicorn workers (``dev.py server --workers``) each worker has its own
scheduler loop. A run takes ``<data_dir>/.scheduler.lock`` with ``flock`` before it reads the state, so any worker may
run the jobs: one that comes second waits, reads the state the first one saved, and finds the jobs not due. The kernel
releases the lock when its process dies, so no lock outlives a crash. The file stays: deleting a lock file in use
would let another process lock a new file of the same name.

Where ``fcntl`` is missing (Windows), runs are serialised per process only, and the scheduler falls back on the leader
election (``leader.py``). The lock follows the pattern of the backup runs (``instance_backup/jobs.py``, ``_RunLock``).
"""

import asyncio
import contextlib
import os
from collections.abc import AsyncIterator
from pathlib import Path

from backend.app.config import get_data_dir

try:
    import fcntl
except ImportError:  # pragma: no cover - not POSIX: the scheduler falls back on the leader election
    fcntl = None  # type: ignore[assignment]

#: The lock file, in the data directory beside ``scheduler_state.json``.
LOCK_FILE_NAME = ".scheduler.lock"
#: Seconds between two attempts while another process holds the lock.
POLL_SECONDS = 0.2


def cross_process_lock_available() -> bool:
    """Whether runs can be serialised across processes here (``fcntl``); otherwise only the leader worker runs them."""
    return fcntl is not None


def run_lock_path() -> Path:
    """The lock file of the current data directory."""
    return Path(get_data_dir()) / LOCK_FILE_NAME


def _try_acquire(path: Path) -> int | None:
    """Open the lock file and take the lock without waiting: its descriptor, or None while another process holds it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    except BaseException:
        os.close(fd)
        raise
    return fd


def _release(fd: int) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _release_if_taken(attempt: asyncio.Future) -> None:
    """Done callback of an attempt whose waiter was cancelled: a lock it took all the same is released, in a thread."""
    if attempt.cancelled() or attempt.exception() is not None:
        return
    fd = attempt.result()
    if fd is not None:
        attempt.get_loop().run_in_executor(None, _release, fd)


@contextlib.asynccontextmanager
async def scheduler_run_lock(path: Path | None = None) -> AsyncIterator[None]:
    """Hold the scheduler's lock across processes for the block; wait for it while another process holds it.

    Each attempt opens the file and tries the lock in a thread: the event loop never touches the file. The wait polls
    every ``POLL_SECONDS`` and can be cancelled; an attempt still in flight then releases the lock if it took it. A
    symlink at the path raises ``OSError`` (``O_NOFOLLOW``). Only where ``cross_process_lock_available()``.
    """
    target = run_lock_path() if path is None else path
    fd: int | None = None
    while fd is None:
        attempt = asyncio.ensure_future(asyncio.to_thread(_try_acquire, target))
        try:
            fd = await asyncio.shield(attempt)
        except asyncio.CancelledError:
            attempt.add_done_callback(_release_if_taken)
            raise
        if fd is None:
            await asyncio.sleep(POLL_SECONDS)
    try:
        yield
    finally:
        await asyncio.to_thread(_release, fd)
