"""
Guard: no test leaves behind an open aiosqlite connection it created (J-6).

A shared helper, not a suite — no ``test_*`` function lives here. ``backend/test_scripts/conftest.py`` installs it
when it is imported and runs a leak window around every test (``_aiosqlite_leak_guard``);
``test_utilities/test_aiosqlite_leak_gate.py`` (utils action ``gate-aiosqlite-leak``) proves it sees what it claims.

Why — C-93. An ``aiosqlite.Connection`` still open when the garbage collector reclaims it is stopped by its
``__del__``, and ``stop()`` binds its future with ``asyncio.get_event_loop()``. If the collection runs in a thread
whose current loop is closed, the connection's worker thread calls ``call_soon_threadsafe`` on that loop
(``aiosqlite/core.py:66``, then ``:75``) and dies: pytest reports a ``PytestUnhandledThreadExceptionWarning``
("Event loop is closed") on whatever test happens to be running, never on the one that leaked. SQLAlchemy's
garbage-collector cleanup of a checked-out aiosqlite connection ends in the same ``stop()``. C-93 had to find its
seven leaks by hand; this guard turns the next one into an ERROR at the teardown of the test that caused it.

What it tracks. ``install()`` wraps ``aiosqlite.core.Connection.__init__`` once. The tracker lives on the wrapper
itself, not in this module: pytest can import this file under a second module name (``test_scripts.…`` beside
``backend.test_scripts.…``), and both must find the same state. A connection constructed in the main thread
while a window is open is registered with a weak reference — the guard never keeps a connection alive, so it never
moves the moment the collector runs —, the nodeid of the innermost open window, and its creation stack: the
innermost repository frames, followed past the bottom of SQLAlchemy's greenlet into the coroutine that awaited it.
Inside that greenlet the stack ends in SQLAlchemy's sync ``Session.execute`` and never reaches the test.

What it leaves alone, on purpose:

- connections born in another thread — the in-process uvicorn of ``_TestingServerManager``, an executor thread:
  they live on that thread's loop, not on the test's;
- connections born while no window is open (collection, a higher-scoped fixture's setup): no check would ever
  read them, so they are not registered at all;
- a connection already reclaimed when its window is checked: its weak reference is dead and there is nothing left
  to report — aiosqlite's own ``__del__`` stopped it, most likely while the test's loop still ran. An engine is
  different: it holds its connections in reference cycles that outlive the test until some later cyclic
  collection — the C-93 case — and that is exactly what the check sees.

The rule (``find_leaks``). A tracked connection still open at the check — aiosqlite 0.22.1's private
``_connection`` is not ``None`` — and not covered by ``AIOSQLITE_LEAK_EXCEPTIONS`` is a leak. A tracked object with
no ``_connection`` at all means aiosqlite changed under the guard: the check raises ``AiosqliteGuardOutdated``
instead of passing, because a guard that cannot tell open from closed is green about nothing.

Report only. The guard never closes or stops a leaked connection: ``stop()`` called from a synchronous teardown
binds its future to whatever ``get_event_loop()`` returns there — possibly a closed loop, the very failure the
guard exists to prevent.

Cost. One append per connection created (beside the thread every aiosqlite connection starts, noise), and a check
that scans only what its own window tracked.
"""

from __future__ import annotations

import contextlib
import functools
import linecache
import os
import sys
import threading
import weakref
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from types import FrameType
from typing import NamedTuple

import aiosqlite.core

AIOSQLITE_LEAK_EXCEPTIONS: tuple[tuple[str, str], ...] = ()
"""Tests allowed to leave an aiosqlite connection open past their teardown: ``(nodeid prefix, one-line reason)``.

Empty, and meant to stay that way. An entry is legitimate only for a connection that must outlive the test that
created it *by design* — e.g. a module-scoped engine whose pooled connection the module's first test opens lazily,
disposed at module teardown. A connection that is merely not closed yet is a leak with a missing fixture, and the
fix the report prints applies to it.

Every entry needs its written reason, saying what owns the connection and when that owner closes it — «it is
easier» is not one. ``find_leaks`` refuses an entry whose prefix or reason is blank. A prefix matches at a nodeid
boundary — the whole nodeid, a directory, a module, a class, or a test with its parametrisations — never in the
middle of a name: ``…::test_a`` does not excuse ``…::test_ab``.
"""

# How many repository frames a creation stack keeps: the innermost ones, enough to reach the test from app code.
_STACK_FRAMES = 6

_THIS_FILE = os.path.abspath(__file__)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_FILE)))
_REPO_PREFIX = _REPO_ROOT + os.sep

# Where the installed wrapper keeps its tracker: the state travels with the patch, not with this module.
_TRACKER_ATTRIBUTE = "_librefolio_aiosqlite_leak_tracker"

# aiosqlite 0.22.1: the sqlite3 connection, None until connected and None again once closed.
_OPEN_ATTRIBUTE = "_connection"
_MISSING = object()


class AiosqliteGuardOutdated(RuntimeError):
    """aiosqlite no longer has the private attribute the guard reads: the guard must be updated, never silenced."""


class CreationFrame(NamedTuple):
    """One repository frame of a connection's creation stack."""

    filename: str
    lineno: int
    function: str


@dataclass(frozen=True)
class TrackedConnection:
    """An aiosqlite connection born in the main thread while a leak window was open."""

    reference: weakref.ReferenceType
    #: The innermost window open at creation: the test that created the connection.
    nodeid: str
    #: Repository frames, outermost first.
    stack: tuple[CreationFrame, ...]

    @property
    def connection(self) -> aiosqlite.core.Connection | None:
        """The connection, or ``None`` once the garbage collector has reclaimed it."""
        return self.reference()


@dataclass(eq=False)
class LeakWindow:
    """One test's span: every main-thread aiosqlite connection created while it is open is tracked in it."""

    nodeid: str
    tracked: list[TrackedConnection] = field(default_factory=list)


class _Tracker:
    """What the wrapped ``__init__`` feeds: the windows open right now, innermost last."""

    def __init__(self) -> None:
        self.windows: list[LeakWindow] = []

    def register(self, connection: aiosqlite.core.Connection) -> None:
        if threading.current_thread() is not threading.main_thread() or not self.windows:
            return
        entry = TrackedConnection(weakref.ref(connection), self.windows[-1].nodeid, _creation_stack())
        for window in self.windows:
            window.tracked.append(entry)


def _tracking_init(original: Callable[..., None], tracker: _Tracker) -> Callable[..., None]:
    @functools.wraps(original)
    def tracking_init(self, *args, **kwargs) -> None:
        original(self, *args, **kwargs)
        tracker.register(self)

    setattr(tracking_init, _TRACKER_ATTRIBUTE, tracker)
    return tracking_init


def _tracker() -> _Tracker:
    """The tracker behind the installed wrapper, installing the wrapper on first use."""
    connection_class = aiosqlite.core.Connection
    tracker = getattr(connection_class.__init__, _TRACKER_ATTRIBUTE, None)
    if tracker is None:
        tracker = _Tracker()
        connection_class.__init__ = _tracking_init(connection_class.__init__, tracker)
    return tracker


def install() -> None:
    """Wrap ``aiosqlite.core.Connection.__init__`` so that connections are tracked. Idempotent."""
    _tracker()


def active_leak_windows() -> tuple[LeakWindow, ...]:
    """The windows open right now, outermost first."""
    return tuple(_tracker().windows)


@contextlib.contextmanager
def leak_window(nodeid: str) -> Iterator[LeakWindow]:
    """Track every main-thread aiosqlite connection created until the block exits, attributed to ``nodeid``.

    Windows nest — the gate's self-tests open theirs inside the conftest's — and a connection is tracked by every
    window open when it is created. Leaving a window also closes any window opened inside it and left open, so a
    misused inner window can never keep collecting after its owner is gone.
    """
    tracker = _tracker()
    window = LeakWindow(nodeid)
    tracker.windows.append(window)
    try:
        yield window
    finally:
        for index, candidate in enumerate(tracker.windows):
            if candidate is window:
                del tracker.windows[index:]
                break


def find_leaks(window: LeakWindow, *, exceptions: Sequence[tuple[str, str]] | None = None) -> list[TrackedConnection]:
    """The connections ``window`` tracked that are still open and not excused, in creation order.

    ``exceptions`` defaults to ``AIOSQLITE_LEAK_EXCEPTIONS``. Raises ``ValueError`` on a malformed exception entry,
    and ``AiosqliteGuardOutdated`` when a tracked connection no longer has aiosqlite's ``_connection``.
    """
    allowed = _checked_exceptions(AIOSQLITE_LEAK_EXCEPTIONS if exceptions is None else exceptions)
    leaks = []
    for entry in window.tracked:
        connection = entry.connection
        if connection is not None and _is_open(connection) and not _excused(entry.nodeid, allowed):
            leaks.append(entry)
    return leaks


def format_leak_report(window: LeakWindow, leaks: Sequence[TrackedConnection]) -> str:
    """The teardown failure: the rule, each leaked connection with its creation stack, the fix."""
    count = len(leaks)
    lines = [
        f"aiosqlite leak guard: {window.nodeid} left {count} aiosqlite connection(s) open at its teardown.",
        "",
        "Rule: no test may leave behind an open aiosqlite connection it created.",
        "Why: an open connection that outlives its test is closed later by the garbage collector, whose stop() can bind to a closed event loop; the connection's worker thread then dies with 'Event loop is closed', reported on whichever unrelated test runs at that moment.",
    ]
    for number, entry in enumerate(leaks, start=1):
        lines += ["", f"Connection {number} of {count}{_database_note(entry.connection)}, created at:", *_stack_lines(entry.stack)]
    lines += [
        "",
        "Fix: close the session and dispose its engine — `async with`, or a fixture with `finally: await engine.dispose()` — so the garbage collector never closes a live aiosqlite connection against a dead event loop.",
        "",
        f"Exception: only a connection that must outlive its test by design may be excused instead, by an entry with its written reason in AIOSQLITE_LEAK_EXCEPTIONS ({_relative(_THIS_FILE)}).",
    ]
    return "\n".join(lines)


def _is_open(connection: aiosqlite.core.Connection) -> bool:
    state = getattr(connection, _OPEN_ATTRIBUTE, _MISSING)
    if state is _MISSING:
        kind = type(connection)
        raise AiosqliteGuardOutdated(
            f"aiosqlite leak guard: a tracked {kind.__module__}.{kind.__qualname__} has no {_OPEN_ATTRIBUTE!r} attribute. "
            f"The guard tells an open aiosqlite connection from a closed one by that private attribute of aiosqlite 0.22.1 "
            f"(installed: {getattr(aiosqlite, '__version__', 'unknown')}); without it the guard is blind. "
            f"The guard must be updated: teach {_relative(_THIS_FILE)} the installed aiosqlite's internals — never make it pass by skipping the check."
        )
    return state is not None


def _checked_exceptions(exceptions: Sequence[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    """The exceptions list, refused whole if any entry is not a non-blank (nodeid prefix, reason) pair."""
    for entry in exceptions:
        if not (isinstance(entry, tuple | list) and len(entry) == 2 and _is_written(entry[0]) and _is_written(entry[1])):
            raise ValueError(f"aiosqlite leak guard: exception entry {entry!r} must be (nodeid prefix, one-line reason), both non-blank. The reason says what owns the connection and when that owner closes it; «it is easier» is not one.")
    return tuple(exceptions)


def _is_written(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _excused(nodeid: str, exceptions: tuple[tuple[str, str], ...]) -> bool:
    return any(_within(nodeid, prefix) for prefix, _reason in exceptions)


def _within(nodeid: str, prefix: str) -> bool:
    """Whether ``prefix`` is ``nodeid`` or one of its parents: a directory, a module, a class, a test's cases."""
    if not nodeid.startswith(prefix):
        return False
    rest = nodeid[len(prefix) :]
    return not rest or prefix.endswith(("/", "::")) or rest.startswith(("/", "::", "["))


def _creation_stack() -> tuple[CreationFrame, ...]:
    """The innermost repository frames that led to the connection being created, outermost first."""
    frames: list[CreationFrame] = []
    for frame in _callers_across_greenlets(sys._getframe(1)):
        filename = frame.f_code.co_filename
        if filename.startswith(_REPO_PREFIX) and filename != _THIS_FILE and "site-packages" not in filename:
            frames.append(CreationFrame(filename, frame.f_lineno, frame.f_code.co_name))
            if len(frames) == _STACK_FRAMES:
                break
    frames.reverse()
    return tuple(frames)


def _callers_across_greenlets(frame: FrameType | None) -> Iterator[FrameType]:
    """``frame`` and its callers; past the bottom of a greenlet, the frames of the greenlet that switched to it.

    SQLAlchemy's asyncio layer runs the sync ORM in a greenlet spawned by the awaiting coroutine. That greenlet's own
    stack ends at the function ``greenlet_spawn`` handed it; the test is only reachable from the parent greenlet's
    suspended frame, ``gr_frame``. Looked up through ``sys.modules``: without greenlet imported there is no greenlet.
    """
    module = sys.modules.get("greenlet")
    current = module.getcurrent() if module is not None else None
    while frame is not None:
        yield frame
        frame = frame.f_back
        if frame is None and current is not None and current.parent is not None:
            current = current.parent
            frame = current.gr_frame


def _stack_lines(stack: tuple[CreationFrame, ...]) -> list[str]:
    if not stack:
        return ["    (no repository frame on its creation stack)"]
    lines = []
    for frame in stack:
        lines.append(f"    {_relative(frame.filename)}:{frame.lineno} in {frame.function}")
        source = linecache.getline(frame.filename, frame.lineno).strip()
        if source:
            lines.append(f"        {source}")
    return lines


def _database_note(connection: aiosqlite.core.Connection | None) -> str:
    """Which database the connection opens, read from ``aiosqlite.connect()``'s connector closure; informational only."""
    connector = getattr(connection, "_connector", None)
    names = getattr(getattr(connector, "__code__", None), "co_freevars", ())
    cells = getattr(connector, "__closure__", None) or ()
    for name, cell in zip(names, cells, strict=False):
        if name == "database":
            with contextlib.suppress(ValueError):
                return f" (database {cell.cell_contents!r})"
    return ""


def _relative(filename: str) -> str:
    return os.path.relpath(filename, _REPO_ROOT) if filename.startswith(_REPO_PREFIX) else filename
