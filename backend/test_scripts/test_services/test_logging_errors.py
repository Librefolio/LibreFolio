"""
Readable errors (workstream H, lot H-60): the error helpers and the log, contract §0 and §2.

§0. ``backend/app/utils/runtime/errors.py``, new, imported by each test that needs it.

- ``visible_causes(error)``: ``error``, then step by step the exception in a ``cause`` attribute when it holds one (the AI
  Export wrappers ``RequiredComponentBuildError`` and ``ResourceLoadError`` carry their cause there, without
  ``__cause__``), else ``__cause__``, else ``__context__`` unless suppressed. It stops at ``None`` or at an exception
  already listed, and lists 50 at most. ``root_cause`` is its last entry. ``shown_error`` is its last entry reached
  through a ``cause`` attribute, ``error`` itself when there is none: Python renders ``__cause__`` and ``__context__`` in
  a traceback, never a ``cause`` attribute. ``reason_code_of`` is the first non-empty ``str`` ``reason_code`` along it.
- ``linked_errors(error)``: ``error`` and every exception linked through ``cause``, ``__cause__`` and ``__context__``,
  suppressed contexts included, without repeats, 50 at most.
- ``mark_reported`` marks that one object and never raises: an exception that refuses attributes stays unmarked.
  ``is_reported`` reads the mark of that object, ``chain_reported`` the marks along ``linked_errors``.

§2. ``backend/app/logging_config.py``.

- structlog's wrapper is ``LibreFolioBoundLogger``, a ``structlog.stdlib.BoundLogger``, from the import-time bootstrap and
  from ``configure_logging()``. Its ``exception()`` logs at error with ``exc_info``: one JSON line, ``"level": "ERROR"``,
  the traceback once, inside the JSON. Today the stdlib ``Logger.exception`` adds ``exc_info`` again: the traceback comes
  a second time, in plain text after the line, and the level is ``EXCEPTION``.
- A call at warning or above, on a logger enabled for its level, marks as reported the exception its ``exc_info`` names,
  or with none the exception being handled. Info and debug mark nothing. The wrapper marks, not a processor, so
  ``capture_logs()`` changes nothing.
- ``add_log_level`` writes ``ERROR`` for ``exception``.
- ``configure_logging()`` puts one more filter on ``uvicorn.error``, once however many calls: it drops a record whose
  ``exc_info`` holds a reported exception (uvicorn's «Exception in ASGI application» for a failure the app already
  wrote) and lets every other record through.

Pure: no server, no database, no network, no file written outside ``tmp_path``. The tests that call
``configure_logging()`` (file logging off) put every logger, the root handlers pytest attached for the test and
structlog's configuration back before they end. The bootstrap is read in a fresh interpreter, which writes no bytecode.
Every exception is built here, and no message holds a real value.
"""

from __future__ import annotations

import contextlib
import importlib
import inspect
import io
import itertools
import json
import logging
import os
import subprocess
import sys
import textwrap
import traceback
from collections.abc import Iterator
from dataclasses import FrozenInstanceError, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import structlog
from structlog.testing import capture_logs
from uvicorn.logging import DefaultFormatter
from uvicorn.protocols.http import h11_impl

from backend.app import logging_config
from backend.app.logging_config import _QUERY_CREDENTIAL_FILTER, add_log_level, configure_logging, get_logger
from backend.test_scripts.test_utils import print_section, print_success

#: The helpers of contract §0: a new module, imported by each test, so that each fails on its own while it is missing.
ERRORS_MODULE = "backend.app.utils.runtime.errors"
#: The most exceptions a chain the helpers walk lists.
CHAIN_CAP = 50
#: The logger the tests write with: a top-level name, so no ancestor's level, handler or filter acts on it.
LOGGER_NAME = "librefolio_test_logging_errors"
#: The event of the call under test, and of the call that proves the setup marks.
EVENT = "boom"
CANARY_EVENT = "canary"
#: The message of the failure the tests log: a placeholder.
CAUSE = "the cause of boom"
#: The line Python writes at the head of every traceback.
TRACEBACK_HEADER = "Traceback (most recent call last)"
#: The logger uvicorn writes a crash of the ASGI app on, and its message (``uvicorn/protocols/http/h11_impl.py``).
UVICORN_ERROR = "uvicorn.error"
UVICORN_ASGI_EXCEPTION = "Exception in ASGI application\n"
#: Where the probe's lines go: through ``configure_logging()``'s processors to the console, or into ``capture_logs()``.
RENDERED, CAPTURED = "rendered", "captured"
#: The project root: the working directory and first import path of the fresh interpreter.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRESH_INTERPRETER_TIMEOUT_SECONDS = 300


# ── §0 the exceptions of the tests ───────────────────────────────────────────


class _Failure(Exception):
    """An ordinary failure: its message names it, nothing else."""


class _ComponentFailure(RuntimeError):
    """Shaped like the AI Export wrappers ``RequiredComponentBuildError`` and ``ResourceLoadError``: the cause in ``cause``, no ``__cause__``."""

    def __init__(self, component_id: str, cause: BaseException) -> None:
        self.component_id = component_id
        self.cause = cause
        super().__init__(f"component {component_id!r} failed: {cause}")


class _TextCause(Exception):
    """A failure whose ``cause`` attribute is a text, not an exception: its chain goes on through ``__cause__``."""

    def __init__(self, message: str) -> None:
        self.cause = "a timeout, in words"
        super().__init__(message)


class _Coded(Exception):
    """A failure with a ``reason_code`` attribute, of any type."""

    def __init__(self, message: str, reason_code: object) -> None:
        self.reason_code = reason_code
        super().__init__(message)


class _Refusing(Exception):
    """An exception that refuses every new attribute, the way a frozen dataclass does.

    ``__slots__`` alone cannot refuse one: ``BaseException`` carries its own ``__dict__``. ``__setattr__`` refuses, raising
    ``refusal``.
    """

    __slots__ = ()
    refusal: type[Exception] = FrozenInstanceError

    def __setattr__(self, name: str, value: object) -> None:
        raise self.refusal(f"{type(self).__name__} refuses the attribute {name!r}")


class _RefusingWithTypeError(_Refusing):
    """The same refusal, raising a ``TypeError``: ``mark_reported`` never raises, whatever the refusal."""

    __slots__ = ()
    refusal = TypeError


def _errors() -> ModuleType:
    """The helpers of contract §0, imported when a test needs them."""
    return importlib.import_module(ERRORS_MODULE)


def _raised_failure(message: str) -> _Failure:
    """A ``_Failure`` raised and caught: it carries a traceback, and is no longer being handled."""
    try:
        raise _Failure(message)
    except _Failure as error:
        return error


# ── §0 the chains, and what the helpers give for each ────────────────────────


@dataclass(frozen=True)
class _Chain:
    """Linked exceptions, as the code under test meets them: ``error`` is the one handed to the helpers, ``named`` holds them all."""

    error: BaseException
    named: dict[str, BaseException]

    def names(self, exceptions: list[BaseException]) -> list[str]:
        """The name of each of ``exceptions``, found by identity; one outside the chain shows as its repr."""
        by_identity = {id(exception): name for name, exception in self.named.items()}
        return [by_identity.get(id(exception), repr(exception)) for exception in exceptions]


@dataclass(frozen=True)
class _Expected:
    """What the helpers give for a chain, by the names of its exceptions: ``linked`` in any order."""

    visible: str
    linked: str
    root: str
    shown: str


def _lone() -> _Chain:
    """``raise A``."""
    a = _Failure("A")
    with contextlib.suppress(_Failure):
        raise a
    return _Chain(a, {"A": a})


def _raise_from() -> _Chain:
    """``raise B from A`` while handling A."""
    a, b = _Failure("A"), _Failure("B")
    with contextlib.suppress(_Failure):
        try:
            raise a
        except _Failure:
            raise b from a
    return _Chain(b, {"A": a, "B": b})


def _implicit_context() -> _Chain:
    """``raise B`` while handling A, without ``from``: A is B's context."""
    a, b = _Failure("A"), _Failure("B")
    with contextlib.suppress(_Failure):
        try:
            raise a
        except _Failure:
            raise b  # noqa: B904 — the implicit context is the case
    return _Chain(b, {"A": a, "B": b})


def _raise_from_none() -> _Chain:
    """``raise B from None`` while handling A: A is B's context, suppressed."""
    a, b = _Failure("A"), _Failure("B")
    with contextlib.suppress(_Failure):
        try:
            raise a
        except _Failure:
            raise b from None
    return _Chain(b, {"A": a, "B": b})


def _cause_over_a_context() -> _Chain:
    """``raise B from A`` while handling X: the explicit cause suppresses the context X."""
    x, a, b = _Failure("X"), _Failure("A"), _Failure("B")
    with contextlib.suppress(_Failure):
        try:
            raise x
        except _Failure:
            raise b from a
    return _Chain(b, {"X": x, "A": a, "B": b})


def _wrapper() -> _Chain:
    """An AI Export wrapper W whose cause C was raised from R."""
    r, c = _Failure("R"), _Failure("C")
    with contextlib.suppress(_Failure):
        try:
            raise r
        except _Failure:
            raise c from r
    w = _ComponentFailure("component.w", c)
    return _Chain(w, {"W": w, "C": c, "R": r})


def _wrapper_over_a_context() -> _Chain:
    """W, wrapping C, raised while handling X without ``from``: the ``cause`` attribute comes before the context."""
    x, c = _Failure("X"), _Failure("C")
    w = _ComponentFailure("component.w", c)
    with contextlib.suppress(_ComponentFailure):
        try:
            raise x
        except _Failure:
            raise w  # noqa: B904 — the implicit context is the case
    return _Chain(w, {"W": w, "C": c, "X": x})


def _two_wrappers() -> _Chain:
    """W1 wrapping W2, wrapping C, raised from R: a required component whose resource failed to load."""
    r, c = _Failure("R"), _Failure("C")
    c.__cause__ = r
    w2 = _ComponentFailure("component.w2", c)
    w1 = _ComponentFailure("component.w1", w2)
    return _Chain(w1, {"W1": w1, "W2": w2, "C": c, "R": r})


def _wrapper_under_a_cause() -> _Chain:
    """E raised from W, wrapping C: an error raised from an AI Export wrapper."""
    c = _Failure("C")
    w = _ComponentFailure("component.w", c)
    e = _Failure("E")
    e.__cause__ = w
    return _Chain(e, {"E": e, "W": w, "C": c})


def _text_cause() -> _Chain:
    """N, whose ``cause`` attribute is a text, raised from A."""
    a, n = _Failure("A"), _TextCause("N")
    n.__cause__ = a
    return _Chain(n, {"N": n, "A": a})


def _cycle_of_causes() -> _Chain:
    """A caused by B, B caused by A."""
    a, b = _Failure("A"), _Failure("B")
    a.__cause__, b.__cause__ = b, a
    return _Chain(a, {"A": a, "B": b})


def _cycle_through_a_cause_attribute() -> _Chain:
    """W wrapping C, whose context is W."""
    c = _Failure("C")
    w = _ComponentFailure("component.w", c)
    c.__context__ = w
    return _Chain(w, {"W": w, "C": c})


def _own_cause() -> _Chain:
    """A caused by itself."""
    a = _Failure("A")
    a.__cause__ = a
    return _Chain(a, {"A": a})


#: Each chain, and what the helpers give for it.
CHAINS = [
    pytest.param(_lone, _Expected(visible="A", linked="A", root="A", shown="A"), id="lone"),
    pytest.param(_raise_from, _Expected(visible="B A", linked="B A", root="A", shown="B"), id="raise-from"),
    pytest.param(_implicit_context, _Expected(visible="B A", linked="B A", root="A", shown="B"), id="implicit-context"),
    pytest.param(_raise_from_none, _Expected(visible="B", linked="B A", root="B", shown="B"), id="raise-from-none"),
    pytest.param(_cause_over_a_context, _Expected(visible="B A", linked="B A X", root="A", shown="B"), id="raise-from-while-handling-another"),
    pytest.param(_wrapper, _Expected(visible="W C R", linked="W C R", root="R", shown="C"), id="cause-attribute"),
    pytest.param(_wrapper_over_a_context, _Expected(visible="W C", linked="W C X", root="C", shown="C"), id="cause-attribute-over-a-context"),
    pytest.param(_two_wrappers, _Expected(visible="W1 W2 C R", linked="W1 W2 C R", root="R", shown="C"), id="two-cause-attributes"),
    pytest.param(_wrapper_under_a_cause, _Expected(visible="E W C", linked="E W C", root="C", shown="C"), id="cause-attribute-under-raise-from"),
    pytest.param(_text_cause, _Expected(visible="N A", linked="N A", root="A", shown="N"), id="cause-attribute-not-an-exception"),
    pytest.param(_cycle_of_causes, _Expected(visible="A B", linked="A B", root="B", shown="A"), id="cycle-of-causes"),
    pytest.param(_cycle_through_a_cause_attribute, _Expected(visible="W C", linked="W C", root="C", shown="C"), id="cycle-through-a-cause-attribute"),
    pytest.param(_own_cause, _Expected(visible="A", linked="A", root="A", shown="A"), id="own-cause"),
]


@pytest.mark.parametrize(("build", "expected"), CHAINS)
def test_visible_causes_follows_the_cause_attribute_then_the_cause_then_an_unsuppressed_context(build, expected):
    errors = _errors()
    chain = build()

    visible = errors.visible_causes(chain.error)

    assert isinstance(visible, list), f"visible_causes returns a list, not a {type(visible).__name__}"
    assert chain.names(visible) == expected.visible.split()


@pytest.mark.parametrize(("build", "expected"), CHAINS)
def test_root_cause_is_the_last_visible_cause(build, expected):
    errors = _errors()
    chain = build()

    assert chain.names([errors.root_cause(chain.error)]) == [expected.root]


@pytest.mark.parametrize(("build", "expected"), CHAINS)
def test_shown_error_is_the_last_visible_cause_reached_through_a_cause_attribute(build, expected):
    errors = _errors()
    chain = build()

    assert chain.names([errors.shown_error(chain.error)]) == [expected.shown]


@pytest.mark.parametrize(("build", "expected"), CHAINS)
def test_linked_errors_follows_every_link_suppressed_contexts_included_once_each(build, expected):
    errors = _errors()
    chain = build()

    linked = errors.linked_errors(chain.error)

    assert isinstance(linked, list), f"linked_errors returns a list, not a {type(linked).__name__}"
    assert sorted(chain.names(linked)) == sorted(expected.linked.split()), "every linked exception once, the error included"


def test_a_chain_longer_than_the_cap_is_cut_at_fifty():
    errors = _errors()
    links = [_Coded(f"link {index}", None) for index in range(CHAIN_CAP + 10)]
    for outer, inner in itertools.pairwise(links):
        outer.__cause__ = inner
    links[CHAIN_CAP].reason_code = "beyond_the_cap"
    index_of = {id(link): index for index, link in enumerate(links)}

    visible = errors.visible_causes(links[0])
    linked = errors.linked_errors(links[0])

    assert [index_of.get(id(error)) for error in visible] == list(range(CHAIN_CAP)), "visible_causes lists the first fifty, in order"
    assert index_of.get(id(errors.root_cause(links[0]))) == CHAIN_CAP - 1, "root_cause is the fiftieth"
    assert errors.shown_error(links[0]) is links[0], "no cause attribute along the chain: the error itself is shown"
    assert len(linked) == CHAIN_CAP, f"linked_errors lists fifty exceptions at most, not {len(linked)}"
    assert len({id(error) for error in linked}) == CHAIN_CAP and {index_of.get(id(error)) for error in linked} <= set(range(len(links))), "linked_errors lists fifty different exceptions of the chain"
    assert errors.reason_code_of(links[1]) == "beyond_the_cap", "barrier: one link further in, the coded exception is the fiftieth and its code is found"
    assert errors.reason_code_of(links[0]) is None, "a code past the fiftieth exception is not along the visible chain"


# ── §0 reason_code_of ────────────────────────────────────────────────────────


def _code_on_the_cause() -> BaseException:
    """B raised from A, the code on A."""
    b = _Failure("B")
    b.__cause__ = _Coded("A", "a_code")
    return b


def _code_behind_a_cause_attribute() -> BaseException:
    """W wrapping C, raised from R, the code on R: an AI Export failure under its wrapper."""
    c = _Failure("C")
    c.__cause__ = _Coded("R", "r_code")
    return _ComponentFailure("component.w", c)


def _codes_on_the_error_and_its_cause() -> BaseException:
    """B raised from A, a code on both: B's comes first."""
    b = _Coded("B", "b_code")
    b.__cause__ = _Coded("A", "a_code")
    return b


def _codes_that_are_no_text() -> BaseException:
    """An empty code, a number and None along the chain, then a code."""
    chain = [_Coded("empty", ""), _Coded("number", 42), _Coded("none", None), _Coded("text", "i_code")]
    for outer, inner in itertools.pairwise(chain):
        outer.__cause__ = inner
    return chain[0]


def _code_on_a_suppressed_context() -> BaseException:
    """``raise B from None`` while handling A, the code on A: A is linked to B, not visible."""
    a, b = _Coded("A", "a_code"), _Failure("B")
    with contextlib.suppress(_Failure):
        try:
            raise a
        except _Coded:
            raise b from None
    return b


#: Each chain, and the code reason_code_of finds along it.
REASON_CODES = [
    pytest.param(lambda: _raise_from().error, None, id="none-along-the-chain"),
    pytest.param(_code_on_the_cause, "a_code", id="on-the-cause"),
    pytest.param(_code_behind_a_cause_attribute, "r_code", id="behind-a-cause-attribute"),
    pytest.param(_codes_on_the_error_and_its_cause, "b_code", id="the-first-along-the-chain"),
    pytest.param(_codes_that_are_no_text, "i_code", id="empty-or-not-a-string-skipped"),
    pytest.param(_code_on_a_suppressed_context, None, id="not-on-a-suppressed-context"),
]


@pytest.mark.parametrize(("build", "expected"), REASON_CODES)
def test_reason_code_of_is_the_first_text_code_along_the_visible_chain(build, expected):
    errors = _errors()

    assert errors.reason_code_of(build()) == expected


# ── §0 the mark ──────────────────────────────────────────────────────────────


def test_mark_reported_marks_that_object_only_and_changes_nothing_it_shows():
    errors = _errors()
    marked, twin = _raised_failure("same message"), _raised_failure("same message")
    shown_before = traceback.format_exception(marked)
    assert errors.is_reported(marked) is False and errors.is_reported(twin) is False, "precondition: a new exception is unmarked"

    assert errors.mark_reported(marked) is None

    assert errors.is_reported(marked) is True
    assert errors.is_reported(twin) is False, "the mark is on the object: an exception of the same class and message stays unmarked"
    assert traceback.format_exception(marked) == shown_before, "the mark must not show in the traceback"
    assert marked.args == ("same message",) and str(marked) == "same message"


#: A chain, and the name of the one exception of it that gets marked.
CHAIN_MARKS = [
    pytest.param(_lone, "A", id="the-error-itself"),
    pytest.param(_raise_from, "A", id="its-cause"),
    pytest.param(_implicit_context, "A", id="its-context"),
    pytest.param(_raise_from_none, "A", id="a-suppressed-context"),
    pytest.param(_cause_over_a_context, "X", id="the-context-an-explicit-cause-suppresses"),
    pytest.param(_wrapper, "C", id="behind-a-cause-attribute"),
    pytest.param(_wrapper, "R", id="the-cause-behind-a-cause-attribute"),
    pytest.param(_wrapper_over_a_context, "X", id="the-context-of-a-wrapper"),
    pytest.param(_cycle_of_causes, "B", id="in-a-cycle"),
]


@pytest.mark.parametrize(("build", "marked"), CHAIN_MARKS)
def test_chain_reported_finds_the_mark_of_any_linked_exception(build, marked):
    errors = _errors()
    chain = build()
    assert errors.chain_reported(chain.error) is False, "precondition: nothing in the chain is marked yet"

    errors.mark_reported(chain.named[marked])

    assert errors.chain_reported(chain.error) is True, f"{marked} is marked and linked to the error"
    assert errors.is_reported(chain.error) is (chain.named[marked] is chain.error), "is_reported reads the mark of that one object"


def test_chain_reported_ignores_a_mark_outside_the_chain():
    errors = _errors()
    chain, elsewhere = _wrapper_over_a_context(), _raised_failure("elsewhere")

    errors.mark_reported(elsewhere)

    assert errors.is_reported(elsewhere) is True, "barrier: the mark is set"
    assert errors.chain_reported(chain.error) is False


@pytest.mark.parametrize("refusing_class", [_Refusing, _RefusingWithTypeError], ids=["frozen-instance-error", "type-error"])
def test_mark_reported_leaves_an_exception_that_refuses_attributes_unmarked_and_never_raises(refusing_class):
    errors = _errors()
    error = refusing_class("refuses attributes")
    with pytest.raises(refusing_class.refusal):
        error.any_attribute = True

    errors.mark_reported(error)

    assert errors.is_reported(error) is False
    assert errors.chain_reported(error) is False


# ── §2 the logging state, saved and put back ─────────────────────────────────


@dataclass(frozen=True)
class _LoggerState:
    """What ``configure_logging()`` and these tests can change on a logger."""

    level: int
    handlers: tuple[logging.Handler, ...]
    filters: tuple[Any, ...]
    propagate: bool
    disabled: bool

    @classmethod
    def of(cls, logger: logging.Logger) -> _LoggerState:
        return cls(logger.level, tuple(logger.handlers), tuple(logger.filters), logger.propagate, logger.disabled)

    def restore(self, logger: logging.Logger) -> None:
        logger.handlers[:] = self.handlers
        logger.filters[:] = self.filters
        logger.propagate, logger.disabled = self.propagate, self.disabled
        # setLevel, not an assignment: it also clears the cached answers of isEnabledFor.
        logger.setLevel(self.level)


#: A logger as ``logging.getLogger`` creates it.
_NEW_LOGGER = _LoggerState(logging.NOTSET, (), (), True, False)


def _every_logger() -> dict[str, logging.Logger]:
    """The root logger, under ``""``, and every logger registered by name."""
    registered = {name: logger for name, logger in list(logging.Logger.manager.loggerDict.items()) if isinstance(logger, logging.Logger)}
    return {"": logging.getLogger(), **registered}


@contextlib.contextmanager
def _logging_state_restored() -> Iterator[None]:
    """Every logger and structlog's configuration put back, on the way out, as they were when the block began.

    ``configure_logging()`` replaces the root handlers, sets levels, adds filters and reconfigures structlog. Used in a
    test body, so the root handlers put back are the ones pytest attached for that very phase. A logger the block created
    goes back to the state of a new one; a handler the block left attached, and no logger held before, is closed.
    structlog gets back the same configuration, its processor list the very same object.
    """
    before = {name: _LoggerState.of(logger) for name, logger in _every_logger().items()}
    held_before = {handler for state in before.values() for handler in state.handlers}
    structlog_configured, structlog_config = structlog.is_configured(), structlog.get_config()
    try:
        yield
    finally:
        left_attached = set()
        for name, logger in _every_logger().items():
            state = before.get(name, _NEW_LOGGER)
            left_attached.update(handler for handler in logger.handlers if handler not in held_before)
            state.restore(logger)
        for handler in left_attached:
            handler.close()
        if structlog_configured:
            structlog.configure(**structlog_config)
        else:
            structlog.reset_defaults()


def _json_lines(text: str) -> list[dict[str, Any]]:
    """The lines of ``text`` that are JSON objects, parsed; any other line is left out."""
    parsed: list[dict[str, Any]] = []
    for line in text.splitlines():
        with contextlib.suppress(ValueError):
            value = json.loads(line)
            if isinstance(value, dict):
                parsed.append(value)
    return parsed


def _configured_with_console_in_a_buffer(log_level: str) -> io.StringIO:
    """``configure_logging(log_level)`` without the file handler, called while stdout is a buffer: its console writes there."""
    console = io.StringIO()
    with contextlib.redirect_stdout(console):
        configure_logging(log_level, enable_file_logging=False)
    streams = [getattr(handler, "stream", None) for handler in logging.getLogger().handlers]
    assert streams == [console], f"setup: configure_logging() must leave one handler on the root, its console on stdout: {logging.getLogger().handlers}"
    return console


def _new_probe_logger() -> logging.Logger:
    """The stdlib logger behind the probe, as ``logging.getLogger`` creates one: no level, handler or filter of its own."""
    logger = logging.getLogger(LOGGER_NAME)
    _NEW_LOGGER.restore(logger)
    return logger


@dataclass(frozen=True)
class _Probe:
    """The structlog logger the tests write with, its stdlib logger, and where its lines go."""

    logger: Any
    stdlib: logging.Logger
    console: io.StringIO
    captured: list[dict[str, Any]] | None

    def wrote(self, event: str) -> bool:
        """Whether a line of ``event`` reached the capture (captured mode) or the console, as JSON (rendered mode)."""
        lines = self.captured if self.captured is not None else _json_lines(self.console.getvalue())
        return any(line.get("event") == event for line in lines)


@contextlib.contextmanager
def _probe(log_level: str, capture_mode: str) -> Iterator[_Probe]:
    """``configure_logging(log_level)``, its console in a buffer, the probe's stdlib logger a new one; under ``capture_logs()`` in captured mode.

    Every logger and structlog's configuration are put back on the way out.
    """
    with _logging_state_restored():
        console = _configured_with_console_in_a_buffer(log_level)
        stdlib = _new_probe_logger()
        if capture_mode == CAPTURED:
            with capture_logs() as captured:
                yield _Probe(get_logger(LOGGER_NAME), stdlib, console, captured)
        else:
            yield _Probe(get_logger(LOGGER_NAME), stdlib, console, None)


@pytest.fixture(params=[RENDERED, CAPTURED])
def capture_mode(request: pytest.FixtureRequest) -> str:
    """Where the probe's lines go: through ``configure_logging()``'s processors to the console, or into ``capture_logs()``."""
    return request.param


# ── §2 the wrapper ───────────────────────────────────────────────────────────


def test_add_log_level_writes_error_for_the_exception_method():
    assert add_log_level(None, "error", {}) == {"level": "ERROR"}, "barrier: an error is ERROR"
    assert add_log_level(None, "warn", {}) == {"level": "WARNING"}, "barrier: warn is WARNING"

    assert add_log_level(None, "exception", {}) == {"level": "ERROR"}, "a logged exception is an error"


def test_configure_logging_makes_every_structlog_logger_a_librefolio_bound_logger():
    print_section("§2: configure_logging() installs LibreFolioBoundLogger")
    wrapper_class = getattr(logging_config, "LibreFolioBoundLogger", None)
    assert wrapper_class is not None, "backend.app.logging_config has no LibreFolioBoundLogger"
    assert issubclass(wrapper_class, structlog.stdlib.BoundLogger), f"{wrapper_class!r} must subclass structlog.stdlib.BoundLogger"

    with _logging_state_restored():
        configure_logging("INFO", enable_file_logging=False)
        configured = structlog.get_config()["wrapper_class"]
        bound = get_logger(LOGGER_NAME).bind()

    assert configured is wrapper_class, f"configure_logging() configures {configured!r} as structlog's wrapper"
    assert isinstance(bound, wrapper_class), f"get_logger() gives a {type(bound).__name__}"
    print_success("✓ configure_logging() configures LibreFolioBoundLogger, a structlog.stdlib.BoundLogger")


#: The prefix of the one line the fresh interpreter writes for the test.
BOOTSTRAP_MARKER = "BOOTSTRAP "
#: Run by a fresh interpreter: structlog unconfigured before ``logging_config`` is imported, and the wrapper the import leaves.
BOOTSTRAP_PROBE = textwrap.dedent("""
    import json

    import structlog

    configured_before = structlog.is_configured()

    from backend.app import logging_config

    wrapper_class = structlog.get_config()["wrapper_class"]
    report = {
        "configured_before": configured_before,
        "wrapper_class": f"{wrapper_class.__module__}.{wrapper_class.__qualname__}",
        "is_librefolio_bound_logger": wrapper_class is getattr(logging_config, "LibreFolioBoundLogger", None),
        "is_stdlib_bound_logger": issubclass(wrapper_class, structlog.stdlib.BoundLogger),
    }
    print("BOOTSTRAP " + json.dumps(report))
    """)


def _fresh_environment(tmp_path: Path) -> dict[str, str]:
    """This process's environment for a fresh interpreter: test mode, its data directory in ``tmp_path``, no bytecode written, the project root importable."""
    environment = dict(os.environ)
    environment["LIBREFOLIO_TEST_MODE"] = "1"
    environment["LIBREFOLIO_TEST_DATA_DIR"] = str(tmp_path / "data")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, [str(PROJECT_ROOT), environment.get("PYTHONPATH")]))
    return environment


def test_the_import_time_bootstrap_installs_the_librefolio_bound_logger(tmp_path):
    print_section("§2: the import-time bootstrap, in a fresh interpreter")

    completed = subprocess.run([sys.executable, "-c", BOOTSTRAP_PROBE], cwd=PROJECT_ROOT, env=_fresh_environment(tmp_path), capture_output=True, text=True, timeout=FRESH_INTERPRETER_TIMEOUT_SECONDS, check=False)

    assert completed.returncode == 0, f"importing logging_config in a fresh interpreter failed with {completed.returncode}:\n{completed.stderr[-4000:]}"
    reports = [line.removeprefix(BOOTSTRAP_MARKER) for line in completed.stdout.splitlines() if line.startswith(BOOTSTRAP_MARKER)]
    assert len(reports) == 1, f"the fresh interpreter must report once: {completed.stdout[-4000:]}"
    report = json.loads(reports[0])
    assert report["configured_before"] is False, "barrier: structlog is not configured before logging_config is imported, so its bootstrap runs"
    assert report["is_librefolio_bound_logger"] is True, f"the import-time bootstrap configures {report['wrapper_class']}, not logging_config.LibreFolioBoundLogger"
    assert report["is_stdlib_bound_logger"] is True, f"{report['wrapper_class']} is not a structlog.stdlib.BoundLogger"
    print_success("✓ Importing logging_config configures LibreFolioBoundLogger")


# ── §2 one failure, one line ─────────────────────────────────────────────────


def _exception_while_handling(logger: Any) -> None:
    """``logger.exception()`` in the ``except`` that caught the failure, its common form."""
    try:
        raise _Failure(CAUSE)
    except _Failure:
        logger.exception(EVENT)


def _exception_naming_its_exception(logger: Any) -> None:
    """``logger.exception(..., exc_info=error)`` outside any ``except``: the exception given is the one written."""
    logger.exception(EVENT, exc_info=_raised_failure(CAUSE))


def _error_with_exc_info_while_handling(logger: Any) -> None:
    """``logger.error(..., exc_info=True)`` in the ``except``: one line already, the guard."""
    try:
        raise _Failure(CAUSE)
    except _Failure:
        logger.error(EVENT, exc_info=True)


@pytest.mark.parametrize(
    "log_a_failure",
    [
        pytest.param(_exception_while_handling, id="exception-while-handling"),
        pytest.param(_exception_naming_its_exception, id="exception-exc_info-outside-except"),
        pytest.param(_error_with_exc_info_while_handling, id="error-exc_info-true-guard"),
    ],
)
def test_a_logged_failure_is_one_json_line_at_error_with_its_traceback_inside(log_a_failure):
    print_section(f"§2: {log_a_failure.__name__}, one JSON line")
    with _logging_state_restored():
        console = _configured_with_console_in_a_buffer("INFO")
        _new_probe_logger()
        log_a_failure(get_logger(LOGGER_NAME))
        output = console.getvalue()

    written = [line for line in _json_lines(output) if line.get("logger") == LOGGER_NAME]
    assert len(written) == 1 and written[0].get("event") == EVENT and f"_Failure: {CAUSE}" in written[0].get("exception", ""), f"barrier: the call wrote its JSON line, the traceback inside: {output}"
    assert output.count(TRACEBACK_HEADER) == 1, f"the traceback must be written once, inside the JSON, not again in plain text: {output.count(TRACEBACK_HEADER)} times in\n{output}"
    assert len(output.splitlines()) == 1, f"one failure logged, one line: {len(output.splitlines())} lines in\n{output}"
    assert written[0].get("level") == "ERROR", f"a logged exception is an error, not {written[0].get('level')!r}"
    print_success("✓ One JSON line at ERROR, the traceback once, inside it")


# ── §2 the mark a report leaves ──────────────────────────────────────────────

#: The calls that report (contract §2): warning and above, ``exception()``, and ``log()`` at such a level.
REPORTING_CALLS = [
    pytest.param(lambda logger: logger.warning(EVENT), id="warning"),
    pytest.param(lambda logger: logger.warning(EVENT, exc_info=True), id="warning-exc_info-true"),
    pytest.param(lambda logger: logger.error(EVENT), id="error"),
    pytest.param(lambda logger: logger.critical(EVENT), id="critical"),
    pytest.param(lambda logger: logger.exception(EVENT), id="exception"),
    pytest.param(lambda logger: logger.log(logging.WARNING, EVENT), id="log-at-warning"),
    pytest.param(lambda logger: logger.log(logging.ERROR, EVENT), id="log-at-error"),
]
#: The calls that never report: info, debug, and ``log()`` at INFO; each made with and without ``exc_info``.
SILENT_CALLS = [
    pytest.param(lambda logger, **kw: logger.info(EVENT, **kw), id="info"),
    pytest.param(lambda logger, **kw: logger.debug(EVENT, **kw), id="debug"),
    pytest.param(lambda logger, **kw: logger.log(logging.INFO, EVENT, **kw), id="log-at-info"),
]
#: The forms of ``exc_info`` that name an exception.
EXC_INFO_FORMS = [
    pytest.param(lambda error: error, id="the-exception"),
    pytest.param(lambda error: (type(error), error, error.__traceback__), id="a-type-value-traceback-tuple"),
]
#: Reports made while no exception is being handled.
OUTSIDE_CALLS = [
    pytest.param(lambda logger: logger.warning(EVENT), id="warning"),
    pytest.param(lambda logger: logger.warning(EVENT, exc_info=True), id="warning-exc_info-true"),
    pytest.param(lambda logger: logger.exception(EVENT), id="exception"),
]


@pytest.mark.parametrize("call", REPORTING_CALLS)
def test_a_report_while_handling_an_exception_marks_it(call, capture_mode):
    errors = _errors()
    handled = _Failure("handled")
    with _probe("INFO", capture_mode) as probe:
        try:
            raise handled
        except _Failure:
            assert errors.is_reported(handled) is False, "precondition: a new exception is unmarked"
            call(probe.logger)
        assert probe.wrote(EVENT), "barrier: the call reached the console or the capture"

    assert errors.is_reported(handled) is True, "a line at warning or above, written while handling the exception, reports it"


@pytest.mark.parametrize("form", EXC_INFO_FORMS)
def test_exc_info_marks_the_exception_it_names_not_the_one_being_handled(form, capture_mode):
    errors = _errors()
    named, handled = _raised_failure("named"), _Failure("handled")
    with _probe("INFO", capture_mode) as probe:
        try:
            raise handled
        except _Failure:
            probe.logger.warning(EVENT, exc_info=form(named))
        assert probe.wrote(EVENT), "barrier: the call reached the console or the capture"

    assert errors.is_reported(named) is True, "the line reports the exception its exc_info names"
    assert errors.is_reported(handled) is False, "exc_info names the exception the line reports: the one being handled is not in it"


@pytest.mark.parametrize("call", SILENT_CALLS)
def test_info_and_debug_mark_nothing(call, capture_mode):
    errors = _errors()
    canary, handled, named = _Failure("canary"), _Failure("handled"), _raised_failure("named")
    with _probe("DEBUG", capture_mode) as probe:
        try:
            raise canary
        except _Failure:
            probe.logger.warning(CANARY_EVENT)
        assert errors.is_reported(canary) is True, "barrier: in this very setup a warning marks, so what follows is not a setup that marks nothing"
        try:
            raise handled
        except _Failure:
            call(probe.logger)
            call(probe.logger, exc_info=named)
        assert probe.wrote(EVENT), "barrier: the logger is enabled for the call, which reached the console or the capture"

    assert errors.is_reported(handled) is False, "info and debug do not report the exception being handled"
    assert errors.is_reported(named) is False, "info and debug do not report the exception exc_info names"


@pytest.mark.parametrize("call", OUTSIDE_CALLS)
def test_a_report_outside_any_except_marks_nothing_and_does_not_fail(call, capture_mode):
    errors = _errors()
    canary = _Failure("canary")
    with _probe("INFO", capture_mode) as probe:
        try:
            raise canary
        except _Failure:
            probe.logger.warning(CANARY_EVENT)
        assert errors.is_reported(canary) is True, "barrier: in this very setup a warning marks"
        earlier = _raised_failure("handled earlier")
        assert sys.exc_info() == (None, None, None), "precondition: no exception is being handled"

        call(probe.logger)

        assert probe.wrote(EVENT), "the call went through, without failing"

    assert errors.is_reported(earlier) is False, "an exception handled earlier, and done with, is not the one a later line reports"


def test_a_warning_on_a_logger_disabled_for_warning_marks_nothing(capture_mode):
    errors = _errors()
    canary, handled, named = _Failure("canary"), _Failure("handled"), _raised_failure("named")
    with _probe("ERROR", capture_mode) as probe:
        assert probe.stdlib.isEnabledFor(logging.ERROR) and not probe.stdlib.isEnabledFor(logging.WARNING), "precondition: with the root at ERROR the logger is enabled for errors only"
        try:
            raise canary
        except _Failure:
            probe.logger.error(CANARY_EVENT)
        assert errors.is_reported(canary) is True, "barrier: an error, which the logger is enabled for, marks"
        try:
            raise handled
        except _Failure:
            probe.logger.warning(EVENT)
            probe.logger.warning(EVENT, exc_info=named)

    assert errors.is_reported(handled) is False, "a warning the logger is disabled for is no report: the exception being handled stays unmarked"
    assert errors.is_reported(named) is False, "a warning the logger is disabled for is no report: the exception exc_info names stays unmarked"


@pytest.mark.parametrize("refusing_class", [_Refusing, _RefusingWithTypeError], ids=["frozen-instance-error", "type-error"])
def test_a_report_while_handling_an_exception_that_refuses_attributes_does_not_fail(refusing_class, capture_mode):
    errors = _errors()
    canary, refusing = _Failure("canary"), refusing_class("refuses attributes")
    with _probe("INFO", capture_mode) as probe:
        try:
            raise canary
        except _Failure:
            probe.logger.warning(CANARY_EVENT)
        assert errors.is_reported(canary) is True, "barrier: the wrapper marks in this setup, so it tries to mark the exception below too"
        try:
            raise refusing
        except _Refusing:
            probe.logger.warning(EVENT)
            probe.logger.exception(EVENT)
        assert probe.wrote(EVENT), "the calls went through, without failing"

    assert errors.is_reported(refusing) is False, "an exception that refuses attributes stays unmarked"


# ── §2 uvicorn.error and a failure the app already wrote ─────────────────────


class _Records(logging.Handler):
    """Keeps every record it handles."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def asgi_exceptions(self) -> list[BaseException | None]:
        """The exception of each record of uvicorn's ASGI message that came through, ``None`` for a record without one."""
        return [record.exc_info[1] if record.exc_info else None for record in self.records if record.msg == UVICORN_ASGI_EXCEPTION]


def _uvicorn_logs_http(error: BaseException) -> None:
    """What uvicorn's HTTP protocols (h11, httptools) do when the ASGI app raises ``error``."""
    logging.getLogger(UVICORN_ERROR).error(UVICORN_ASGI_EXCEPTION, exc_info=error)


def _uvicorn_logs_websocket(error: _Failure) -> None:
    """What uvicorn's WebSocket protocols do: ``logger.exception()`` while handling the exception the app raised."""
    try:
        raise error
    except _Failure:
        logging.getLogger(UVICORN_ERROR).exception(UVICORN_ASGI_EXCEPTION)


@contextlib.contextmanager
def _uvicorn_error_configured(handler: logging.Handler) -> Iterator[io.StringIO]:
    """``configure_logging()``, its console in a buffer (yielded), then uvicorn's ``uvicorn.error`` writing to ``handler`` only, at INFO.

    The logger starts without filters, so it holds exactly the ones ``configure_logging()`` puts on it. Everything is put
    back on the way out.
    """
    with _logging_state_restored():
        error_logger = logging.getLogger(UVICORN_ERROR)
        error_logger.filters[:] = []
        console = _configured_with_console_in_a_buffer("INFO")
        error_logger.handlers[:] = [handler]
        error_logger.propagate, error_logger.disabled = False, False
        error_logger.setLevel(logging.INFO)
        yield console


def _other_filters(logger: logging.Logger) -> list[Any]:
    """The filters on ``logger`` but the query-credential one."""
    return [log_filter for log_filter in logger.filters if log_filter is not _QUERY_CREDENTIAL_FILTER]


def test_configure_logging_twice_leaves_one_more_filter_on_uvicorn_error():
    print_section("§2: configure_logging() twice, one more filter on uvicorn.error")
    error_logger = logging.getLogger(UVICORN_ERROR)
    with _logging_state_restored():
        error_logger.filters[:] = []
        configure_logging("INFO", enable_file_logging=False)
        after_one = _other_filters(error_logger)
        configure_logging("INFO", enable_file_logging=False)
        after_two = _other_filters(error_logger)
        credential = [log_filter for log_filter in error_logger.filters if log_filter is _QUERY_CREDENTIAL_FILTER]

    assert len(credential) == 1, f"barrier: configure_logging() ran on uvicorn.error, its query-credential filter there once: {credential}"
    assert len(after_one) == 1, f"configure_logging() must put one filter on uvicorn.error next to the query-credential one: {after_one}"
    assert len(after_two) == 1, f"called twice, configure_logging() must leave that filter there once: {after_two}"
    print_success("✓ uvicorn.error holds the query-credential filter and one more, once each, after two calls")


@pytest.mark.parametrize("uvicorn_logs", [pytest.param(_uvicorn_logs_http, id="http-protocol"), pytest.param(_uvicorn_logs_websocket, id="websocket-protocol")])
def test_uvicorn_error_drops_its_record_of_an_exception_the_app_reported(uvicorn_logs):
    print_section(f"§2: uvicorn.error, {uvicorn_logs.__name__}")
    errors = _errors()
    assert "Exception in ASGI application" in inspect.getsource(h11_impl), "not uvicorn's message: the records below are not the ones uvicorn writes"
    unreported, reported = _raised_failure("never reported"), _raised_failure("reported by the app")
    errors.mark_reported(reported)
    records = _Records()
    with _uvicorn_error_configured(records):
        uvicorn_logs(unreported)
        canary = records.asgi_exceptions()
        uvicorn_logs(reported)
        passed = records.asgi_exceptions()

    assert canary == [unreported], f"barrier: uvicorn's record of an unreported exception reaches the handler, or the drop below proves nothing: {canary}"
    assert passed == [unreported], f"uvicorn's record of an exception the app already reported must be dropped by the filters of uvicorn.error: {passed}"
    print_success("✓ The record of a reported exception dropped, the one of an unreported exception kept")


def _an_unreported_exception(errors: ModuleType) -> BaseException | None:
    """uvicorn's record of an exception nobody reported."""
    error = _raised_failure("never reported")
    _uvicorn_logs_http(error)
    return error


def _an_exception_raised_from_a_reported_one(errors: ModuleType) -> BaseException | None:
    """uvicorn's record of a new exception raised from a reported one: the new one was never written."""
    cause, error = _raised_failure("reported cause"), _Failure("raised from it")
    errors.mark_reported(cause)
    with contextlib.suppress(_Failure):
        raise error from cause
    _uvicorn_logs_http(error)
    return error


def _no_exc_info(errors: ModuleType) -> BaseException | None:
    """uvicorn's message without ``exc_info``: the filter judges the exception, never the text."""
    logging.getLogger(UVICORN_ERROR).error(UVICORN_ASGI_EXCEPTION)
    return None


def _exc_info_without_an_exception(errors: ModuleType) -> BaseException | None:
    """``logger.exception()`` outside any ``except``: ``exc_info`` is ``(None, None, None)``."""
    logging.getLogger(UVICORN_ERROR).exception(UVICORN_ASGI_EXCEPTION)
    return None


#: Records of uvicorn's message the filter lets through: each builder logs one, and returns its exception.
OTHER_RECORDS = [
    pytest.param(_an_unreported_exception, id="an-unreported-exception"),
    pytest.param(_an_exception_raised_from_a_reported_one, id="an-unreported-exception-whose-cause-was-reported"),
    pytest.param(_no_exc_info, id="no-exc_info"),
    pytest.param(_exc_info_without_an_exception, id="exc_info-without-an-exception"),
]


@pytest.mark.parametrize("log_the_record", OTHER_RECORDS)
def test_uvicorn_error_lets_every_other_record_through(log_the_record):
    errors = _errors()
    reported = _raised_failure("reported by the app")
    errors.mark_reported(reported)
    records = _Records()
    with _uvicorn_error_configured(records):
        _uvicorn_logs_http(reported)
        dropped = records.asgi_exceptions()
        expected = log_the_record(errors)
        passed = records.asgi_exceptions()

    assert dropped == [], f"barrier: the filter is at work, uvicorn's record of a reported exception dropped, or letting the record below through proves nothing: {dropped}"
    assert passed == [expected], f"the filters of uvicorn.error dropped a record they must let through: {passed}"


def test_a_failure_the_app_wrote_is_not_written_again_by_uvicorn():
    print_section("§2: a failure the app wrote, then uvicorn's record of it")
    uvicorn_lines = io.StringIO()
    uvicorn_handler = logging.StreamHandler(uvicorn_lines)
    uvicorn_handler.setFormatter(DefaultFormatter("%(levelprefix)s %(message)s", use_colors=False))
    with _uvicorn_error_configured(uvicorn_handler) as app_console:
        _new_probe_logger()
        _uvicorn_logs_http(_raised_failure("never reported"))
        canary = uvicorn_lines.getvalue()
        uvicorn_lines.seek(0)
        uvicorn_lines.truncate()

        crash = _raised_failure(CAUSE)
        get_logger(LOGGER_NAME).error("Unhandled error", exc_info=crash)
        _uvicorn_logs_http(crash)
        app_output, uvicorn_output = app_console.getvalue(), uvicorn_lines.getvalue()

    assert "Exception in ASGI application" in canary and canary.count(TRACEBACK_HEADER) == 1, f"barrier: uvicorn's record of a failure nobody wrote reaches its handler, traceback and all: {canary}"
    app_lines = [line for line in _json_lines(app_output) if line.get("logger") == LOGGER_NAME]
    assert [line.get("event") for line in app_lines] == ["Unhandled error"] and f"_Failure: {CAUSE}" in app_lines[0].get("exception", ""), f"barrier: the app's line, JSON, its traceback inside: {app_output}"
    written = app_output.count(TRACEBACK_HEADER) + uvicorn_output.count(TRACEBACK_HEADER)
    assert written == 1, f"the app wrote the failure: its traceback must reach the log once, not again from uvicorn ({written} times):\n{app_output}{uvicorn_output}"
    assert "Exception in ASGI application" not in uvicorn_output, f"uvicorn wrote again a failure the app had written: {uvicorn_output}"
    print_success("✓ The app's line once, uvicorn's record of the same failure dropped")
