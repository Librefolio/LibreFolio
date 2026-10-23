"""Named steps for the app's startup and shutdown, and the runner that executes them in order.

Owner: workstream H (platform), CP2b. The app's own steps are listed in ``app_lifespan.py``. This module only runs steps
and imports nothing of the app, so a platform module (the shutdown watchdog) can import ``Step`` and ``current_step``
from it without an import cycle.

- A ``Step`` has a ``name`` and a ``run`` callable. ``run()`` returns ``None`` or an awaitable (a coroutine, a
  ``Task``), which the runner awaits. ``blocking=True`` marks a synchronous call that may block for a while: under a
  shutdown deadline ``run()`` is called in a worker thread, so the deadline holds; otherwise on the event loop. What it
  returns is awaited all the same.
- ``run_startup_steps(steps)`` runs the steps in order, each to its end; ``blocking`` changes nothing there. An
  exception stops the startup.
- ``run_shutdown_steps(steps, deadline)`` runs the steps in order. ``deadline`` is an instant on ``time.monotonic()``,
  or ``None`` for no limit. Under a deadline each step gets the time left, never less than ``MIN_STEP_SECONDS``, so the
  short steps still run after an overrun. A step past its time is cut and logged as a warning: an awaited ``Task`` is
  cancelled; a thread cannot be stopped, and the sequence moves on without it. A step that raises is logged as an
  error, and the next step runs. One ``StepOutcome`` per step is returned.
- ``current_step()`` names the step running now, ``"startup:<name>"`` or ``"shutdown:<name>"``; ``None`` between steps
  and while the app serves. A watchdog thread may read it.
"""

import asyncio
import inspect
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from backend.app.logging_config import get_logger

logger = get_logger(__name__)

#: The least time a shutdown step gets under a deadline, even past it: the short steps (registries, caches) still run.
MIN_STEP_SECONDS = 0.2

_current_step: str | None = None


@dataclass(frozen=True)
class Step:
    """One startup or shutdown step: a name for the log and the watchdog, and the call that does the work.

    ``skip_when``, on a startup step: asked when the step comes, the step is not run while it answers True (H-62: the
    steps an instance awaiting its restore must not run).
    """

    name: str
    run: Callable[[], object]
    blocking: bool = False
    skip_when: Callable[[], bool] | None = None


@dataclass(frozen=True)
class StepOutcome:
    """How a shutdown step ended: ``finished`` is False when the deadline cut it; ``error`` is set when it raised."""

    name: str
    finished: bool
    seconds: float
    error: str | None = None


def current_step() -> str | None:
    """The step running now, ``"startup:<name>"`` or ``"shutdown:<name>"``; ``None`` between steps."""
    return _current_step


async def run_startup_steps(steps: Sequence[Step]) -> None:
    """Run the startup steps in order, each to its end. An exception stops the startup."""
    global _current_step
    for step in steps:
        if step.skip_when is not None and step.skip_when():
            logger.info("Startup step skipped", step=step.name)
            continue
        _current_step = f"startup:{step.name}"
        try:
            await _completed(step.run())
        finally:
            _current_step = None


async def run_shutdown_steps(steps: Sequence[Step], deadline: float | None = None) -> list[StepOutcome]:
    """Run the shutdown steps in order, within ``deadline`` (``time.monotonic()``) when given; return their outcomes."""
    global _current_step
    outcomes: list[StepOutcome] = []
    for step in steps:
        _current_step = f"shutdown:{step.name}"
        started = time.monotonic()
        finished, error = True, None
        try:
            if deadline is None:
                await _completed(step.run())
            else:
                finished = await _run_within(step, max(deadline - started, MIN_STEP_SECONDS))
        except Exception as exc:  # noqa: BLE001 — a step that fails must not skip the rest of the shutdown
            error = repr(exc)
            logger.exception("Shutdown step failed", step=step.name)
        finally:
            _current_step = None
        seconds = time.monotonic() - started
        if not finished:
            logger.warning("Shutdown step cut by the deadline", step=step.name, seconds=round(seconds, 3))
        outcomes.append(StepOutcome(step.name, finished, seconds, error))
    return outcomes


async def _completed(result: object) -> None:
    """Await what a step's ``run()`` returned, when it is awaitable."""
    if inspect.isawaitable(result):
        await result


async def _run_within(step: Step, seconds: float) -> bool:
    """Run one shutdown step for at most ``seconds``; False when the time ran out first."""
    scope = asyncio.timeout(seconds)
    try:
        async with scope:
            await _completed(await asyncio.to_thread(step.run) if step.blocking else step.run())
    except TimeoutError:
        if not scope.expired():
            raise
    return not scope.expired()
