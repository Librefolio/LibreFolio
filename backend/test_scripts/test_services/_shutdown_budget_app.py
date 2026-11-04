"""The server of ``test_shutdown_budget_process.py``: the real shutdown pieces under the uvicorn CLI, with steps the test switches on.

Never collected by pytest (its name does not start with ``test_``) and never imported by the test process: it configures
logging at import. The test starts it as ``python -m uvicorn backend.test_scripts.test_services._shutdown_budget_app:app
--uds <socket> --lifespan on``. It mirrors ``backend/app/services/platform/app_lifespan.py`` with the real pieces:

- ``lifecycle.run_startup_steps(STARTUP_STEPS)``, the watchdog step first, as ``app_lifespan`` wires it:
  ``Step("shutdown-watchdog", lambda: install_shutdown_watchdog())``;
- in the lifespan's ``finally``, ``shutdown_deadline()`` once, its value passed to ``lifecycle.run_shutdown_steps`` for
  ``FINALLY_STEPS`` (in place of the tool executor) and then for ``SHUTDOWN_STEPS``, which end with
  ``child_processes_step()``.

The steps the test chooses, through the environment (``Z6B_APP_*``):

- ``Z6B_APP_DIR`` (required): an existing absolute directory, the only one this app writes to;
- ``Z6B_APP_HANGING_STEP=1``: a shutdown step that never ends, ``z6b-hanging-step``: its ``run`` returns
  ``asyncio.sleep(3600)``;
- ``Z6B_APP_SLEEP_STEP_SECONDS=<n>``: a shutdown step, ``z6b-sleep-step``, that sleeps n seconds, then writes
  ``sleep-step-finished``;
- ``Z6B_APP_BLOCKED_THREAD=1``: a startup step that starts a non-daemon thread, ``z6b-blocked-thread``, blocked forever:
  the interpreter would wait for it at exit;
- ``Z6B_APP_STUBBORN_CHILD=1``: a startup step that starts a child process ignoring SIGTERM, waits until it says so, and
  writes its pid to ``child.pid``. The child sleeps two minutes at most: it ends by itself even if both the server and
  the test fail to end it.

``GET /ping`` answers the server's pid, the budget it read, whether a watchdog is installed — ``shutdown_budget._watchdog``,
read here, the module having no function that returns it (N58) — and the names of its live threads. ``GET /slow`` writes
``slow-started``, sleeps 30 s, then writes ``slow-finished`` — or ``slow-cancelled`` when it is cancelled. Logging goes
to the console only (stdout, one JSON line per event, file logging off): the test reads it.

Red until H's CP2b brings ``backend/app/services/platform/lifecycle.py``: this module does not import.
"""

import asyncio
import os
import signal
import subprocess
import sys
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from backend.app.logging_config import configure_logging
from backend.app.services.platform import lifecycle, shutdown_budget
from backend.app.services.platform.shutdown_budget import (
    child_processes_step,
    install_shutdown_watchdog,
    shutdown_budget_seconds,
    shutdown_deadline,
)

PREFIX = "Z6B_APP_"
FINALLY_STEP = "z6b-finally"
HANGING_STEP = "z6b-hanging-step"
SLEEP_STEP = "z6b-sleep-step"
BLOCKED_THREAD = "z6b-blocked-thread"
STUBBORN_CHILD_STEP = "z6b-stubborn-child"
SLOW_SECONDS = 30
HANGING_SECONDS = 3600
#: Ignores SIGTERM, says so once it does, then sleeps two minutes at most.
STUBBORN_CHILD = "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\nprint('ready', flush=True)\ntime.sleep(120)\n"


def _restore_inherited_signals() -> None:
    """Undo a SIGINT or SIGTERM ignored, or blocked, by whoever started the test process: the readings must not depend on it.

    uvicorn imports this module before it runs the server, so before ``asyncio`` and uvicorn look at the handlers in
    place. An ignored SIGTERM, put back by uvicorn at the end and raised again, would end the server with status 0; an
    ignored SIGINT would leave ``asyncio`` without its handler. A handler already installed — coverage's, in a measured
    run — is left alone.
    """
    if signal.getsignal(signal.SIGTERM) is signal.SIG_IGN:
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
    if signal.getsignal(signal.SIGINT) is signal.SIG_IGN:
        signal.signal(signal.SIGINT, signal.default_int_handler)
    if hasattr(signal, "pthread_sigmask"):
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT, signal.SIGTERM})


def _app_dir() -> Path:
    raw = os.environ.get(f"{PREFIX}DIR", "")
    directory = Path(raw)
    if not raw or not directory.is_absolute() or not directory.is_dir():
        raise RuntimeError(f"{PREFIX}DIR must name an existing absolute directory: every file this app writes goes there, never elsewhere")
    return directory


def _switched_on(name: str) -> bool:
    return os.environ.get(f"{PREFIX}{name}") == "1"


configure_logging("INFO", enable_file_logging=False)
_restore_inherited_signals()
APP_DIR = _app_dir()
#: Never set: the blocked thread waits on it forever.
_NEVER = threading.Event()
#: The children this server started, kept so that nothing collects their ``Popen``.
_CHILDREN: list[subprocess.Popen[str]] = []


def _mark(name: str, text: str = "") -> None:
    (APP_DIR / name).write_text(text, encoding="utf-8")


def _start_blocked_thread() -> None:
    threading.Thread(target=_NEVER.wait, name=BLOCKED_THREAD, daemon=False).start()


def _start_stubborn_child() -> None:
    child = subprocess.Popen([sys.executable, "-I", "-c", STUBBORN_CHILD], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    _CHILDREN.append(child)
    said = child.stdout.readline().strip() if child.stdout is not None else ""
    if said != "ready":
        raise RuntimeError(f"the child that ignores SIGTERM did not start: {said!r}")
    _mark("child.pid", str(child.pid))


async def _sleep_then_mark(seconds: float) -> None:
    await asyncio.sleep(seconds)
    _mark("sleep-step-finished")


def _nothing() -> None:
    return None


def _startup_steps() -> tuple[lifecycle.Step, ...]:
    steps = [lifecycle.Step("shutdown-watchdog", lambda: install_shutdown_watchdog())]
    if _switched_on("BLOCKED_THREAD"):
        steps.append(lifecycle.Step(BLOCKED_THREAD, _start_blocked_thread))
    if _switched_on("STUBBORN_CHILD"):
        steps.append(lifecycle.Step(STUBBORN_CHILD_STEP, _start_stubborn_child))
    return tuple(steps)


def _shutdown_steps() -> tuple[lifecycle.Step, ...]:
    steps = []
    if _switched_on("HANGING_STEP"):
        steps.append(lifecycle.Step(HANGING_STEP, lambda: asyncio.sleep(HANGING_SECONDS)))
    sleep_seconds = os.environ.get(f"{PREFIX}SLEEP_STEP_SECONDS", "").strip()
    if sleep_seconds:
        seconds = float(sleep_seconds)
        steps.append(lifecycle.Step(SLEEP_STEP, lambda: _sleep_then_mark(seconds)))
    steps.append(child_processes_step())
    return tuple(steps)


STARTUP_STEPS = _startup_steps()
FINALLY_STEPS = (lifecycle.Step(FINALLY_STEP, _nothing),)
SHUTDOWN_STEPS = _shutdown_steps()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await lifecycle.run_startup_steps(STARTUP_STEPS)
    try:
        yield
    finally:
        deadline = shutdown_deadline()
        await lifecycle.run_shutdown_steps(FINALLY_STEPS, deadline)
        await lifecycle.run_shutdown_steps(SHUTDOWN_STEPS, deadline)


app = FastAPI(lifespan=lifespan)


@app.get("/ping")
async def ping() -> dict[str, Any]:
    return {
        "pid": os.getpid(),
        "budget_seconds": shutdown_budget_seconds(),
        "watchdog": shutdown_budget._watchdog is not None,
        "threads": sorted(thread.name for thread in threading.enumerate()),
    }


@app.get("/slow")
async def slow() -> dict[str, Any]:
    _mark("slow-started")
    try:
        await asyncio.sleep(SLOW_SECONDS)
    except asyncio.CancelledError:
        _mark("slow-cancelled")
        raise
    _mark("slow-finished")
    return {"slow": "finished"}
