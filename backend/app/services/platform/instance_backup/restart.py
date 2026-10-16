"""Stopping the server so that a confirmed restore is applied (lot B3).

A restore is applied at a start, never while the server serves (``apply.py``). ``POST /backup/restore/restart`` asks the
server to stop: SIGTERM to its root process — uvicorn's master when it runs workers (it stops them), otherwise the
server's own process — and the shutdown budget of workstream Z does the rest (``shutdown_budget.py``). What starts it
again is outside LibreFolio: Docker with ``restart: unless-stopped`` (both compose files), systemd with
``Restart=always``, a hosting provider. Without one, the server stays stopped until someone starts it, and the restore is
applied then.
"""

from __future__ import annotations

import multiprocessing
import os
import signal
from collections.abc import Callable

from backend.app.logging_config import get_logger

logger = get_logger(__name__)

#: How the signal is sent, looked up at each call: the tests replace it, and never stop a real server.
send_signal: Callable[[int, int], None] = os.kill


def server_pid() -> int:
    """The server's root process: the parent that started this one through ``multiprocessing`` (uvicorn's master with
    ``--workers N``, or its reloader) while it is alive, otherwise this process. A worker whose master died is its own
    server: the pid its master had may since belong to another process."""
    parent = multiprocessing.parent_process()
    if parent is not None and parent.pid is not None and parent.is_alive():
        return parent.pid
    return os.getpid()


def request_restart(*, pid: int | None = None) -> int:
    """Send SIGTERM to the server's root process (or to ``pid``), and return the pid it went to."""
    target = server_pid() if pid is None else pid
    logger.warning("Stopping the server to apply a restore: whatever supervises it starts it again", pid=target)
    send_signal(target, signal.SIGTERM)
    return target
