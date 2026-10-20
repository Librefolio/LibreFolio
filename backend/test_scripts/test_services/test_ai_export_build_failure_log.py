"""H-60 · TA-1 and H-60r · TA-R3 — the line ``BuildContext._build`` writes when an AI Export component fails.

H-60 (TA-1: its contract's §1, with §0's meanings). A component that failed to build used to leave no trace: ``_build``
turns the exception into a cached failed outcome (a ``ComponentDiagnostic`` for an optional caller, a
``RequiredComponentBuildError`` for a required one) and wrote nothing, so an export that came back short never said why.
H-60 gives ``backend.app.services.ai_export.dependencies`` a module logger, ``get_logger(__name__)``, and one **warning**
per failed component per ``BuildContext``, written in the ``except Exception`` of ``_build``:

- the exception is a ``RequiredComponentBuildError`` (a dependency failed, declared or resolved as required by the
  builder, and that failure has its own line where it was built) → ``"AI Export component not built: a dependency
  failed"`` with ``component_id`` and ``dependency_id`` (``exc.component_id``), no ``exc_info``;
- otherwise → ``"AI Export component failed to build"`` with ``component_id``; ``error_type``, the class name of the
  root of the visible chain (the ``cause`` attribute the AI Export wrappers carry, else ``__cause__``, else an
  unsuppressed ``__context__``); ``reason_code``, the first non-empty one along that chain, the key absent without one;
  ``exc_info``, the exception whose traceback says the most: the last one reached through a ``cause`` attribute (Python
  never renders that link), the raised one otherwise.

Nothing else changes: same outcome, same exception object, same diagnostics; a cached failure is not written again;
``asyncio.CancelledError`` is not caught and writes nothing. No payload value goes in the line (ids, a class name, a
reason code): the message reaches the log only inside the traceback.

H-60r (TA-R3: its contract's §3, with §0/§1 for the mark): one traceback per failed resource. In one request
``BuildContext`` memoizes a failed resource as one ``ResourceLoadError`` and raises that same object to every component
that reads the key; across requests, a loader awaiting a shared build (the portfolio engine's, MF-J45b/d) raises the
build's own exception, the same object, in each. The ``failed to build`` warning stays one per component per request,
with the keys above; only the traceback changes, written with the first line about it:

- ``traceback_reported(shown_error(exc))`` false → ``exc_info`` = ``shown_error(exc)``, as above;
- true, because a line already wrote that traceback (another component's, in this request or another, or the loader's
  own, logged before it raised) → no ``exc_info`` key, and ``logged_with_request_id`` =
  ``traceback_reporting_request(shown_error(exc))``, the request whose line holds it (possibly this very one); the key is
  absent when that line was written outside any request.

The mark is set by the logger (§1): a warning written with ``exc_info`` records on the exception the request it was
written in, for ``_build`` the ``request_id`` bound in structlog's contextvars, as ``RequestIdMiddleware`` binds it for
each HTTP request; not ``BuildContext.request_id``, the snapshot's own id (a fresh uuid in ``runtime_service.py``), so the
tests keep the two apart. The capture below has no ``merge_contextvars``: ``request_id`` is in no captured line, and a
test that needs a request binds one with ``structlog.contextvars.bound_contextvars`` around its resolves. Outcomes,
diagnostics, exceptions, build counts and the «a dependency failed» line do not change, and every H-60 test keeps
holding: each of its failures has an exception of its own.

The log is read with ``structlog.testing.capture_logs`` for the whole test, ``add_logger_name`` naming each event's
logger, behind a barrier: a probe logged under the module's logger name reaches the capture before anything is built
(this works before the module has a logger; capture_logs swaps the processors inside the configured list, so a logger
cached on it still reaches the capture: test_post_migration.py, section 13). Every expected line is compared whole, keys
included; an exception compares by identity, so ``exc_info`` is pinned to the very object. An absence (a successful
build, a cancellation, a traceback not written twice) is asserted beside a presence in the same capture: a failing
sibling's line, or the line that does hold the traceback; without it the absence would hold just as well with no logging
at all.

Pure: in-memory registries and builders, as in test_ai_export_component_runtime.py; no database, no server, no file.

Red today (HEAD 2c7fc7b8d). The H-60 tests pin what bf16865ed implemented: their «Red today» notes date from before that
commit, when ``_build`` wrote nothing. The H-60r tests are red: ``_build`` passes ``exc_info`` on every ``failed to
build`` line, so the second component, or the second request, to fail on one loader exception, and a component whose
loader already logged its failure with the traceback, write that traceback again, and no line has
``logged_with_request_id``. Their preconditions (one load per request, the same exception objects, H-60's mark on the
loader's exception, the loader's own line, the behaviour unchanged) hold today.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from collections.abc import Awaitable, Callable, Iterator, Mapping
from contextlib import AbstractContextManager, nullcontext
from typing import Any, NoReturn

import pytest
import structlog
from pydantic import BaseModel, ConfigDict
from structlog.testing import capture_logs

from backend.app.logging_config import get_logger
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import Domain, ResourceKey
from backend.app.services.ai_export.dependencies import BuildContext, RequiredComponentBuildError, ResourceLoadError
from backend.app.utils.runtime.errors import is_reported

#: The structlog name of the module's logger (contract §1: ``get_logger(__name__)``).
MODULE_LOGGER = "backend.app.services.ai_export.dependencies"
FAILED_EVENT = "AI Export component failed to build"
DEPENDENCY_EVENT = "AI Export component not built: a dependency failed"
#: Every key a line may hold: ids, a class name, a reason code, the exception or, when another line already holds its
#: traceback, that line's request (H-60r §3), and what the capture adds (``logger``, ``log_level``). Nothing that could
#: carry a payload value.
FAILED_KEYS = frozenset({"event", "log_level", "logger", "component_id", "error_type", "reason_code", "exc_info", "logged_with_request_id"})
DEPENDENCY_KEYS = frozenset({"event", "log_level", "logger", "component_id", "dependency_id"})

SOURCE = "portfolio.h60_source"
DEPENDENT = "portfolio.h60_dependent"
TOP = "portfolio.h60_top"
RESOURCE_USER = "portfolio.h60_resource_user"
INVALID_PAYLOAD = "portfolio.h60_invalid_payload"
BARRIER = "portfolio.h60_presence_barrier"
#: H-60r: two components reading one resource in one request.
FIRST_READER = "portfolio.h60r_first_reader"
SECOND_READER = "portfolio.h60r_second_reader"
#: H-60r: the resource both readers read, and the one a build shared by two requests stands behind.
ROWS = ResourceKey("h60r.rows", int)
PORTFOLIO_BUILD = ResourceKey("h60r.portfolio_build", int)
#: H-60r: the logger of a test's own loader, which logs its failure with the traceback before raising it, and that line.
LOADER_LOGGER = "backend.test_scripts.test_services.h60r_loader"
LOADER_EVENT = "H-60r test loader could not read the rows"


# =============================================================================
# In-memory components (mirroring test_ai_export_component_runtime.py)
# =============================================================================


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int


class _RateHistoryError(RuntimeError):
    """Shaped like AI Export's ``FxRateHistoryError``: a stable reason code beside a message that names the data."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(message)


def _spec(component_id: str, *, dependencies: tuple[str, ...] = (), builder: Callable[..., Any] | None = None) -> ComponentSpec:
    """A minimal component over ``_Payload``; the default builder succeeds."""

    def _default_builder(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> _Payload:
        return _Payload(value=1)

    return ComponentSpec(
        component_id=component_id,
        version=1,
        domains=frozenset({Domain.PORTFOLIO}),
        output_model=_Payload,
        builder=builder or _default_builder,
        dependencies=dependencies,
    )


def _context(*specs: ComponentSpec) -> BuildContext:
    """One request's ``BuildContext`` over an in-memory registry of ``specs``."""
    return BuildContext(ComponentRegistry(specs), request_id="req-h60-ta1")


def _raising(error: BaseException) -> Callable[..., NoReturn]:
    """A builder (two arguments) or a resource loader (none) that raises ``error``, that very object."""

    def _raise(*_arguments: object) -> NoReturn:
        raise error

    return _raise


def _counted(loader: Callable[[], object], runs: list[None]) -> Callable[[], object]:
    """``loader``, appending to ``runs`` each time it is called: how many times a resource was really loaded."""

    def _load() -> object:
        runs.append(None)
        return loader()

    return _load


def _reads(key: ResourceKey[int], loader: Callable[[], object]) -> Callable[[BuildContext, Mapping[str, SectionEnvelope]], Awaitable[_Payload]]:
    """A builder that reads the resource ``key`` through ``loader``: any number of components may read the same key."""

    async def _read(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> _Payload:
        return _Payload(value=await context.resource(key, loader))

    return _read


# =============================================================================
# Reading the log
# =============================================================================


class _ModuleLog:
    """The events the capture saw, by logger, in the order written, the barrier's probe left out: the module's
    (``lines``), or a test's own (``lines_of``)."""

    def __init__(self, entries: list[dict[str, Any]], probe: str) -> None:
        self._entries = entries
        self._probe = probe

    def lines(self) -> list[dict[str, Any]]:
        return self.lines_of(MODULE_LOGGER)

    def lines_of(self, logger_name: str) -> list[dict[str, Any]]:
        return [entry for entry in self._entries if entry.get("logger") == logger_name and entry.get("event") != self._probe]


@pytest.fixture
def module_log() -> Iterator[_ModuleLog]:
    """``capture_logs`` for the whole test, each event named after its logger; barrier first.

    The probe goes through ``get_logger`` (that is ``structlog.get_logger``) under the module's logger name, before
    anything is built: once it has arrived, an empty capture means "nothing was written", not "the capture was blind".
    On exit, pass or fail, capture_logs puts structlog's processors back into the same list.
    """
    probe = f"h60-ta1-capture-probe-{uuid.uuid4().hex}"
    with capture_logs(processors=[structlog.stdlib.add_logger_name]) as entries:
        get_logger(MODULE_LOGGER).info(probe)
        arrived = [(entry.get("logger"), entry.get("log_level")) for entry in entries if entry.get("event") == probe]
        assert arrived == [(MODULE_LOGGER, "info")], f"barrier: a probe logged as {MODULE_LOGGER!r} did not reach capture_logs (saw {arrived}), so nothing read from this capture would prove anything"
        yield _ModuleLog(entries, probe)


def _failed_line(component_id: str, error_type: str, shown: BaseException, *, reason_code: str | None = None) -> dict[str, Any]:
    """A whole ``failed to build`` line with the traceback; its ``exc_info`` compares by identity (an exception has no ``__eq__``)."""
    line = _failed_line_without_traceback(component_id, error_type, reason_code=reason_code)
    line["exc_info"] = shown
    return line


def _failed_line_without_traceback(component_id: str, error_type: str, *, reason_code: str | None = None, logged_with_request_id: str | None = None) -> dict[str, Any]:
    """A whole ``failed to build`` line whose traceback another line already wrote (H-60r §3): no ``exc_info`` key.

    ``logged_with_request_id`` names the request whose line holds that traceback; the key is absent when that line was
    written outside any request.
    """
    line: dict[str, Any] = {"event": FAILED_EVENT, "log_level": "warning", "logger": MODULE_LOGGER, "component_id": component_id, "error_type": error_type}
    if reason_code is not None:
        line["reason_code"] = reason_code
    if logged_with_request_id is not None:
        line["logged_with_request_id"] = logged_with_request_id
    return line


def _dependency_line(component_id: str, dependency_id: str) -> dict[str, Any]:
    """A whole ``not built: a dependency failed`` line: no ``exc_info``, no error field."""
    return {"event": DEPENDENCY_EVENT, "log_level": "warning", "logger": MODULE_LOGGER, "component_id": component_id, "dependency_id": dependency_id}


def _said(lines: list[dict[str, Any]]) -> list[tuple[Any, Any, Any]]:
    """What the module wrote, one ``(level, event, component_id)`` per line: for the assertion messages."""
    return [(line.get("log_level"), line.get("event"), line.get("component_id")) for line in lines]


def _said_with_traceback(lines: list[dict[str, Any]]) -> list[tuple[Any, Any, bool, Any]]:
    """What the module wrote, one ``(event, component_id, carries exc_info, logged_with_request_id)`` per line: for the
    H-60r assertion messages, where the question is which line carries the traceback."""
    return [(line.get("event"), line.get("component_id"), "exc_info" in line, line.get("logged_with_request_id")) for line in lines]


# =============================================================================
# A component that fails: one "failed to build" warning
# =============================================================================


@pytest.mark.asyncio
async def test_a_failing_builder_writes_one_warning_with_its_error_type_and_the_exception(module_log: _ModuleLog) -> None:
    """Brief 1: a builder raising ``KeyError`` → exactly one ``failed to build`` warning.

    ``component_id``, ``error_type`` ``"KeyError"``, ``exc_info`` that very exception, and no ``reason_code`` key: the
    exception carries none. Red today: no line.
    """
    key_error = KeyError("h60_missing_key")
    context = _context(_spec(SOURCE, builder=_raising(key_error)))

    assert await context.resolve(SOURCE, required=False) is None

    lines = module_log.lines()
    assert lines == [_failed_line(SOURCE, "KeyError", key_error)], f"one '{FAILED_EVENT}' warning for {SOURCE}, exc_info the KeyError itself; the module wrote {_said(lines)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("carrier", ["the-raised-exception", "its-explicit-cause", "a-resource-loaders-exception"])
async def test_the_reason_code_found_along_the_chain_goes_in_the_line(module_log: _ModuleLog, carrier: str) -> None:
    """Brief 2: an exception carrying ``reason_code = "fx_no_usable_rate"`` puts the key ``reason_code`` in the line.

    The code is the first one along the visible chain, so it is found on the raised exception, on its ``__cause__``, and
    behind a ``ResourceLoadError``: the AI Export FX case, where ``FxRateHistoryError("fx_no_usable_rate", …)`` raised by
    a resource loader reaches ``_build`` as the ``cause`` of the wrapper. ``error_type`` names the root; ``exc_info`` is
    the raised exception or, through the wrapper, the loader's own. Red today: no line.
    """
    rate_error = _RateHistoryError("fx_no_usable_rate", "no FX rate exists on or before the period end")
    valuation_error = RuntimeError("the position could not be valued")

    def _raises_from_it(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> NoReturn:
        raise valuation_error from rate_error

    async def _loads_it(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> _Payload:
        return _Payload(value=await context.resource(ResourceKey("h60.fx_rates", int), _raising(rate_error)))

    builder, shown = {
        "the-raised-exception": (_raising(rate_error), rate_error),
        "its-explicit-cause": (_raises_from_it, valuation_error),
        "a-resource-loaders-exception": (_loads_it, rate_error),
    }[carrier]
    context = _context(_spec(SOURCE, builder=builder))

    assert await context.resolve(SOURCE, required=False) is None

    lines = module_log.lines()
    expected = _failed_line(SOURCE, "_RateHistoryError", shown, reason_code="fx_no_usable_rate")
    assert lines == [expected], f"one '{FAILED_EVENT}' warning for {SOURCE} with reason_code 'fx_no_usable_rate'; the module wrote {_said(lines)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("link", ["explicit-cause", "implicit-context", "suppressed-context"])
async def test_error_type_names_the_root_cause_and_exc_info_is_the_raised_exception(module_log: _ModuleLog, link: str) -> None:
    """Brief 3: ``raise ValueError(…) from KeyError(…)`` → ``error_type`` ``"KeyError"``, the root; ``exc_info`` the ``ValueError``.

    The ``ValueError``'s rendered traceback shows both, which is why it is the one logged. The same for a ``ValueError``
    raised while handling the ``KeyError`` (an implicit ``__context__``); with ``from None`` the context is suppressed,
    nothing is visible below the ``ValueError``, and it is its own root. Red today: no line.
    """
    key_error = KeyError("h60_missing_row")
    value_error = ValueError("the row could not be read")

    def _from_it(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> NoReturn:
        raise value_error from key_error

    def _while_handling_it(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> NoReturn:
        try:
            raise key_error
        except KeyError:
            raise value_error  # noqa: B904 — the implicit __context__ link is the case under test

    def _from_none(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> NoReturn:
        try:
            raise key_error
        except KeyError:
            raise value_error from None

    builder, root, rendered = {
        "explicit-cause": (_from_it, key_error, (key_error, value_error)),
        "implicit-context": (_while_handling_it, key_error, (key_error, value_error)),
        "suppressed-context": (_from_none, value_error, (value_error,)),
    }[link]
    context = _context(_spec(SOURCE, builder=builder))

    assert await context.resolve(SOURCE, required=False) is None

    lines = module_log.lines()
    assert lines == [_failed_line(SOURCE, type(root).__name__, value_error)], f"one '{FAILED_EVENT}' warning for {SOURCE}: error_type {type(root).__name__!r}, exc_info the ValueError; the module wrote {_said(lines)}"
    rendering = "".join(traceback.format_exception(value_error))
    unseen = [type(error).__name__ for error in rendered if "".join(traceback.format_exception_only(error)) not in rendering]
    assert unseen == [], f"the traceback of exc_info must show the whole visible chain; it misses {unseen}"


@pytest.mark.asyncio
async def test_a_failed_resource_shows_the_loaders_exception_not_its_wrapper(module_log: _ModuleLog) -> None:
    """Brief 4: ``context.resource(key, loader)`` fails, the loader raising ``LookupError`` → that ``LookupError`` is logged.

    ``error_type`` ``"LookupError"`` and ``exc_info`` the ``LookupError``, unwrapped from ``ResourceLoadError.cause``:
    Python never renders a ``cause`` attribute, so the wrapper's traceback would hide the loader's frames and message.
    Precondition first, behaviour unchanged: the build failed on the wrapper. Red today: no line.
    """
    lookup_error = LookupError("no price row for the requested day")

    async def _loads_rows(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> _Payload:
        return _Payload(value=await context.resource(ResourceKey("h60.price_rows", int), _raising(lookup_error)))

    context = _context(_spec(RESOURCE_USER, builder=_loads_rows))

    with pytest.raises(RequiredComponentBuildError) as raised:
        await context.resolve(RESOURCE_USER, required=True)
    wrapper = raised.value.cause
    assert isinstance(wrapper, ResourceLoadError) and wrapper.cause is lookup_error, f"precondition: the builder must fail on a ResourceLoadError wrapping the loader's LookupError, got {wrapper!r}"

    lines = module_log.lines()
    assert lines == [_failed_line(RESOURCE_USER, "LookupError", lookup_error)], f"one '{FAILED_EVENT}' warning for {RESOURCE_USER}, exc_info the loader's LookupError (not the ResourceLoadError); the module wrote {_said(lines)}"


# =============================================================================
# A dependency that fails: written where it failed, pointed to from above
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("link", ["declared-dependency", "resolved-as-required-by-the-builder"])
async def test_a_failed_dependency_is_written_where_it_failed_and_pointed_to_by_its_dependent(module_log: _ModuleLog, link: str) -> None:
    """Brief 5: B depends on A, A fails → exactly two lines, in order: A's ``failed to build`` (with ``exc_info``), then B's.

    B's line is ``not built: a dependency failed`` with ``component_id`` B, ``dependency_id`` A, and no ``exc_info``
    key. The same when B's builder resolves A as required instead of declaring it. Red today: no line.
    """
    key_error = KeyError("h60_missing_row")

    async def _resolves_it(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> _Payload:
        await context.resolve(SOURCE, required=True)
        return _Payload(value=1)

    dependent = _spec(DEPENDENT, dependencies=(SOURCE,)) if link == "declared-dependency" else _spec(DEPENDENT, builder=_resolves_it)
    context = _context(_spec(SOURCE, builder=_raising(key_error)), dependent)

    assert await context.resolve(DEPENDENT, required=False) is None

    lines = module_log.lines()
    assert lines == [_failed_line(SOURCE, "KeyError", key_error), _dependency_line(DEPENDENT, SOURCE)], f"A's '{FAILED_EVENT}', then B's '{DEPENDENCY_EVENT}'; the module wrote {_said(lines)}"


@pytest.mark.asyncio
async def test_a_failure_two_levels_down_is_written_once_and_each_level_points_to_its_own_dependency(module_log: _ModuleLog) -> None:
    """§1, ``dependency_id`` is ``exc.component_id``: C → B → A, A fails → A's failure, B's pointer to A, C's pointer to B.

    In that order: the root failure is written once, where it happened, and each level names its own dependency, not
    the root. Red today: no line.
    """
    key_error = KeyError("h60_missing_row")
    context = _context(
        _spec(SOURCE, builder=_raising(key_error)),
        _spec(DEPENDENT, dependencies=(SOURCE,)),
        _spec(TOP, dependencies=(DEPENDENT,)),
    )

    assert await context.resolve(TOP, required=False) is None

    lines = module_log.lines()
    expected = [_failed_line(SOURCE, "KeyError", key_error), _dependency_line(DEPENDENT, SOURCE), _dependency_line(TOP, DEPENDENT)]
    assert lines == expected, f"one failure where it happened, one pointer per level above it; the module wrote {_said(lines)}"


# =============================================================================
# One line per component per request; behaviour unchanged
# =============================================================================


@pytest.mark.asyncio
async def test_a_failure_resolved_twice_in_one_request_is_written_once_and_behaves_as_before(module_log: _ModuleLog) -> None:
    """Brief 6: the same failed component resolved as required, then as optional, in one ``BuildContext`` → one line.

    Behaviour unchanged, checked first: the required call raises ``RequiredComponentBuildError`` whose ``cause`` is the
    original exception, the optional one returns None and records one diagnostic, the builder ran once. Red today: the
    behaviour holds, the line is missing.
    """
    runtime_error = RuntimeError("the source is unavailable")
    context = _context(_spec(SOURCE, builder=_raising(runtime_error)))

    with pytest.raises(RequiredComponentBuildError) as raised:
        await context.resolve(SOURCE, required=True)
    optional = await context.resolve(SOURCE, required=False)

    assert raised.value.component_id == SOURCE and raised.value.cause is runtime_error, f"the required caller must get the original exception as cause, got {raised.value.cause!r}"
    assert optional is None
    assert [diagnostic.component_id for diagnostic in context.diagnostics] == [SOURCE]
    assert context.build_count(SOURCE) == 1
    lines = module_log.lines()
    assert lines == [_failed_line(SOURCE, "RuntimeError", runtime_error)], f"a cached failure is written once per request; the module wrote {_said(lines)}"


@pytest.mark.asyncio
async def test_each_request_writes_its_own_line_for_the_same_failing_component(module_log: _ModuleLog) -> None:
    """§1, one line per component per ``BuildContext``: two requests over one registry, the component failing in each, two lines.

    Each line carries its own request's exception: a failure is never silenced because another request already had
    it. Red today: no line.
    """
    raised: list[RuntimeError] = []

    def _fails_afresh(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> NoReturn:
        error = RuntimeError("the source is unavailable")
        raised.append(error)
        raise error

    registry = ComponentRegistry([_spec(SOURCE, builder=_fails_afresh)])
    for request_id in ("req-h60-ta1-first", "req-h60-ta1-second"):
        assert await BuildContext(registry, request_id=request_id).resolve(SOURCE, required=False) is None

    assert len(raised) == 2, f"precondition: each request builds the component once, got {len(raised)} builds"
    lines = module_log.lines()
    assert lines == [_failed_line(SOURCE, "RuntimeError", error) for error in raised], f"one line per request; the module wrote {_said(lines)}"


# =============================================================================
# No line: a success, a cancellation (each beside a presence barrier)
# =============================================================================


@pytest.mark.asyncio
async def test_a_successful_build_writes_no_line(module_log: _ModuleLog) -> None:
    """Brief 7: components that build (sync, async on a dependency, through a resource) write no line at all.

    The absence needs a presence beside it: a sibling that fails in the same request writes its warning, so the module
    demonstrably logs here, and that line is the only one. Red today: the sibling's line is missing too.
    """
    barrier_error = KeyError("h60_presence_barrier")

    async def _builds_on_its_dependency(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> _Payload:
        return _Payload(value=dependencies_map[SOURCE].payload["value"] + 1)

    async def _loads_rows(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> _Payload:
        return _Payload(value=await context.resource(ResourceKey("h60.price_rows", int), lambda: 3))

    context = _context(
        _spec(SOURCE),
        _spec(DEPENDENT, dependencies=(SOURCE,), builder=_builds_on_its_dependency),
        _spec(RESOURCE_USER, builder=_loads_rows),
        _spec(BARRIER, builder=_raising(barrier_error)),
    )

    for component_id in (DEPENDENT, RESOURCE_USER):
        assert await context.resolve(component_id, required=True) is not None, f"precondition: {component_id} must build"
    assert await context.resolve(BARRIER, required=False) is None

    lines = module_log.lines()
    assert lines == [_failed_line(BARRIER, "KeyError", barrier_error)], f"only the failing sibling writes; the module wrote {_said(lines)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("how", ["raised-by-the-builder", "task-cancelled-mid-build"])
async def test_a_cancellation_propagates_and_writes_no_line(module_log: _ModuleLog, how: str) -> None:
    """Brief 8: ``asyncio.CancelledError`` from a builder is not caught: it reaches the caller, and writes nothing.

    Raised by the builder itself, or delivered by cancelling the request's task while the builder awaits. Presence
    barrier in the same request: a failing sibling, resolved after, writes its line, and it is the only one. Red today:
    the sibling's line is missing.
    """
    started = asyncio.Event()
    never = asyncio.Event()
    barrier_error = KeyError("h60_presence_barrier")

    async def _waits_until_cancelled(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> _Payload:
        started.set()
        await never.wait()
        return _Payload(value=1)

    builder = _raising(asyncio.CancelledError()) if how == "raised-by-the-builder" else _waits_until_cancelled
    context = _context(_spec(SOURCE, builder=builder), _spec(BARRIER, builder=_raising(barrier_error)))

    task = asyncio.create_task(context.resolve(SOURCE, required=False))
    if how == "task-cancelled-mid-build":
        await started.wait()
        task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled(), "the cancellation must reach the caller, never become a failed outcome"
    assert await context.resolve(BARRIER, required=False) is None

    lines = module_log.lines()
    assert lines == [_failed_line(BARRIER, "KeyError", barrier_error)], f"a cancellation writes nothing, the failing sibling does; the module wrote {_said(lines)}"


# =============================================================================
# Security: the message reaches the log only inside the traceback
# =============================================================================


@pytest.mark.asyncio
async def test_a_payload_value_in_a_message_reaches_the_log_only_inside_the_traceback(module_log: _ModuleLog) -> None:
    """Brief 9 (security): a canary in an exception's message is in no field of any line, only inside ``exc_info``.

    Four failures whose message carries data: a builder's own exception; the dependency pointer above it (the
    ``RequiredComponentBuildError`` message repeats its cause's); an FX-like loader error with a reason code; and a
    payload that fails validation, whose pydantic message quotes the value. Each line holds only the contract's keys,
    none holds the canary, and the traceback of each ``exc_info`` does: the message reaches the log there and nowhere
    else. Red today: no line.
    """
    canary = f"canary-payload-{uuid.uuid4().hex[:12]}"  # short enough for pydantic to quote the input whole
    builder_error = RuntimeError(f"cash balance {canary} could not be valued")
    rate_error = _RateHistoryError("fx_no_usable_rate", f"no FX rate for {canary} on or before the period end")

    async def _loads_rates(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> _Payload:
        return _Payload(value=await context.resource(ResourceKey("h60.fx_rates", int), _raising(rate_error)))

    def _returns_an_invalid_payload(context: BuildContext, dependencies_map: Mapping[str, SectionEnvelope]) -> dict[str, object]:
        return {"value": canary}

    context = _context(
        _spec(SOURCE, builder=_raising(builder_error)),
        _spec(DEPENDENT, dependencies=(SOURCE,)),
        _spec(RESOURCE_USER, builder=_loads_rates),
        _spec(INVALID_PAYLOAD, builder=_returns_an_invalid_payload),
    )
    for component_id in (DEPENDENT, RESOURCE_USER, INVALID_PAYLOAD):
        assert await context.resolve(component_id, required=False) is None

    lines = module_log.lines()
    written = [(line.get("event"), line.get("component_id")) for line in lines]
    assert written == [(FAILED_EVENT, SOURCE), (DEPENDENCY_EVENT, DEPENDENT), (FAILED_EVENT, RESOURCE_USER), (FAILED_EVENT, INVALID_PAYLOAD)], f"barrier: each failure must have its line before what the lines hold can be judged; the module wrote {_said(lines)}"
    for line in lines:
        allowed = FAILED_KEYS if line["event"] == FAILED_EVENT else DEPENDENCY_KEYS
        assert set(line) <= allowed, f"{line['component_id']}: keys outside the contract {sorted(set(line) - allowed)}"
        carrying = sorted(key for key, value in line.items() if key != "exc_info" and canary in repr(value))
        assert carrying == [], f"{line['component_id']}: the message's data leaked into {carrying}"
    for line in lines:
        if line["event"] == FAILED_EVENT:
            shown = line.get("exc_info")
            assert isinstance(shown, BaseException), f"{line['component_id']}: exc_info must be the exception, got {shown!r}"
            assert canary in "".join(traceback.format_exception(shown)), f"{line['component_id']}: the message must still reach the log, inside the traceback of exc_info"


# =============================================================================
# H-60r §3: a failed resource read twice, its traceback written once
# =============================================================================


def _in_request(request_id: str | None) -> AbstractContextManager[None]:
    """The HTTP request the resolves run in, bound in structlog's contextvars as ``RequestIdMiddleware`` binds it; with
    ``None``, outside any request: nothing is bound."""
    return structlog.contextvars.bound_contextvars(request_id=request_id) if request_id is not None else nullcontext()


def _no_request_bound() -> None:
    """Precondition of the H-60r tests: no request id leaked into the test's context, so the only request a line can
    name is one the test binds itself."""
    bound = structlog.contextvars.get_contextvars()
    assert "request_id" not in bound, f"precondition: no request may be bound around the test, found request_id {bound.get('request_id')!r}"


async def _failure_of(context: BuildContext, component_id: str) -> BaseException:
    """The exception ``component_id``'s cached outcome holds, as a required caller receives it: the ``cause`` of its
    ``RequiredComponentBuildError``. Read once the component has been built: it builds nothing and writes no line."""
    with pytest.raises(RequiredComponentBuildError) as raised:
        await context.resolve(component_id, required=True)
    assert raised.value.component_id == component_id, f"the required caller of {component_id} must be told its own component, got {raised.value.component_id!r}"
    return raised.value.cause


@pytest.mark.asyncio
@pytest.mark.parametrize("http_request_id", [None, "req-h60r-one"], ids=["outside-any-request", "in-a-request"])
async def test_two_components_reading_one_failed_resource_write_its_traceback_once(module_log: _ModuleLog, http_request_id: str | None) -> None:
    """Brief R3·1 and R3·2: two components read one failed resource in one request → its traceback in the first line only.

    Both builders read ``ROWS`` through one loader raising ``lookup_error``; both are resolved as optional in one
    ``BuildContext``, outside any request, then in one bound as ``RequestIdMiddleware`` binds it. Preconditions: the
    loader ran once, both outcomes failed on the same ``ResourceLoadError`` object (its ``cause`` ``lookup_error``), and
    the first line marked ``lookup_error`` (H-60's mark, which §3 reads). Lines, in order: the first reader's ``failed to
    build`` with ``exc_info`` ``lookup_error``; then the second reader's, with the same ``error_type``, no ``exc_info``
    key, and ``logged_with_request_id`` the request whose line holds the traceback, this very one; outside any request,
    no such key either. The context keeps its own id (``req-h60-ta1``), as a snapshot keeps its uuid in production: the
    line names the HTTP request. Red today: the second line carries ``exc_info`` again, the loader's traceback twice.
    """
    _no_request_bound()
    lookup_error = LookupError("no price row for the requested day")
    loads: list[None] = []
    loader = _counted(_raising(lookup_error), loads)
    context = _context(_spec(FIRST_READER, builder=_reads(ROWS, loader)), _spec(SECOND_READER, builder=_reads(ROWS, loader)))

    with _in_request(http_request_id):
        for component_id in (FIRST_READER, SECOND_READER):
            assert await context.resolve(component_id, required=False) is None, f"precondition: {component_id} must fail, reading the failed {ROWS.name!r}"

    first_failure = await _failure_of(context, FIRST_READER)
    second_failure = await _failure_of(context, SECOND_READER)
    assert len(loads) == 1, f"precondition: a failed resource is loaded once per request, then memoized; got {len(loads)} loads"
    assert isinstance(first_failure, ResourceLoadError) and first_failure.cause is lookup_error, f"precondition: the first reader must fail on a ResourceLoadError wrapping the loader's LookupError, got {first_failure!r}"
    assert second_failure is first_failure, f"precondition: both readers must fail on the same ResourceLoadError object, got {second_failure!r}"
    assert is_reported(lookup_error), "precondition: the first line marked the loader's exception as reported (H-60), the mark §3 reads"

    lines = module_log.lines()
    expected = [_failed_line(FIRST_READER, "LookupError", lookup_error), _failed_line_without_traceback(SECOND_READER, "LookupError", logged_with_request_id=http_request_id)]
    assert lines == expected, f"the loader's traceback goes with the first reader's line only, the second's points to it; the module wrote {_said_with_traceback(lines)}"


@pytest.mark.asyncio
async def test_a_loader_exception_two_requests_share_is_written_with_its_traceback_once(module_log: _ModuleLog) -> None:
    """Brief R3·3: two requests whose loaders raise the same exception object → its traceback in request one's line only.

    The portfolio engine runs one build per key (MF-J45b/d): a request that arrives while the build runs awaits it, and
    when the build fails every waiting request gets its exception, the same object. Here two ``BuildContext``s over one
    registry, each with its own id (a fresh uuid, as ``runtime_service.py`` gives a snapshot), resolved one after the
    other, each in its own HTTP request; the loader of each raises ``shared``, which carries a reason code so that the
    line without traceback is seen to keep it. Preconditions: each request loaded once and failed on its own
    ``ResourceLoadError``, both wrapping ``shared`` (what the requests share is the loader's exception, not the
    wrapper), and request one's line marked ``shared`` (H-60). Lines, in order: request one's with ``exc_info``
    ``shared``; request two's with the same ``error_type`` and ``reason_code``, no ``exc_info`` key, and
    ``logged_with_request_id`` request one's id. Red today: request two's line carries ``exc_info`` again.
    """
    _no_request_bound()
    shared = _RateHistoryError("fx_no_usable_rate", "no FX rate exists on or before the period end")
    loads: list[None] = []
    registry = ComponentRegistry([_spec(RESOURCE_USER, builder=_reads(PORTFOLIO_BUILD, _counted(_raising(shared), loads)))])
    first_request, second_request = "req-h60r-first", "req-h60r-second"

    failures: list[BaseException] = []
    for http_request_id in (first_request, second_request):
        context = BuildContext(registry, request_id=uuid.uuid4().hex)
        with _in_request(http_request_id):
            assert await context.resolve(RESOURCE_USER, required=False) is None, f"precondition: {RESOURCE_USER} must fail in {http_request_id}"
        failures.append(await _failure_of(context, RESOURCE_USER))

    first_failure, second_failure = failures
    assert len(loads) == 2, f"precondition: each request loads its resource once, got {len(loads)} loads for two requests"
    assert all(isinstance(failure, ResourceLoadError) and failure.cause is shared for failure in failures), f"precondition: each request must fail on a ResourceLoadError wrapping the shared exception, got {failures!r}"
    assert second_failure is not first_failure, "precondition: each request wraps the shared exception in a ResourceLoadError of its own"
    assert is_reported(shared), "precondition: request one's line marked the shared exception as reported (H-60), the mark §3 reads"

    lines = module_log.lines()
    expected = [
        _failed_line(RESOURCE_USER, "_RateHistoryError", shared, reason_code="fx_no_usable_rate"),
        _failed_line_without_traceback(RESOURCE_USER, "_RateHistoryError", reason_code="fx_no_usable_rate", logged_with_request_id=first_request),
    ]
    assert lines == expected, f"the shared exception's traceback goes with request one's line only, request two's points to it; the module wrote {_said_with_traceback(lines)}"


@pytest.mark.asyncio
async def test_a_resource_failure_two_components_share_behaves_as_before(module_log: _ModuleLog) -> None:
    """Brief R3·4, §3 «outcomes, diagnostics, exceptions and build counts do not change»: only the second traceback goes.

    One request: the first reader resolved as required, the second as optional, then each the other way. Checked first,
    as before the cure: each required caller gets a ``RequiredComponentBuildError`` naming its own component, whose
    ``cause`` is the request's one ``ResourceLoadError`` (key ``ROWS``, ``cause`` the loader's exception); each optional
    caller gets None and one diagnostic, its reason the wrapper's message, in the order they were resolved; each builder
    ran once, the loader once; the first line marked the loader's exception (H-60). Then the lines: the first reader's
    with the traceback, the second's pointing to this request. Red today: the behaviour holds, the second line carries
    ``exc_info`` again.
    """
    _no_request_bound()
    lookup_error = LookupError("no price row for the requested day")
    loads: list[None] = []
    loader = _counted(_raising(lookup_error), loads)
    context = _context(_spec(FIRST_READER, builder=_reads(ROWS, loader)), _spec(SECOND_READER, builder=_reads(ROWS, loader)))
    http_request_id = "req-h60r-behaviour"

    with _in_request(http_request_id):
        with pytest.raises(RequiredComponentBuildError) as first_required:
            await context.resolve(FIRST_READER, required=True)
        second_optional = await context.resolve(SECOND_READER, required=False)
        first_optional = await context.resolve(FIRST_READER, required=False)
        with pytest.raises(RequiredComponentBuildError) as second_required:
            await context.resolve(SECOND_READER, required=True)

    wrapper = first_required.value.cause
    assert (first_required.value.component_id, second_required.value.component_id) == (FIRST_READER, SECOND_READER), "each required caller must be told its own component"
    assert isinstance(wrapper, ResourceLoadError) and wrapper.key_name == ROWS.name and wrapper.cause is lookup_error, f"the required caller must get the ResourceLoadError wrapping the loader's exception as cause, got {wrapper!r}"
    assert second_required.value.cause is wrapper, f"both required callers must get the request's one ResourceLoadError as cause, got {second_required.value.cause!r}"
    assert first_optional is None and second_optional is None, "an optional caller of a failed component gets None"
    diagnostics = [(diagnostic.component_id, diagnostic.reason) for diagnostic in context.diagnostics]
    assert diagnostics == [(SECOND_READER, str(wrapper)), (FIRST_READER, str(wrapper))], f"one diagnostic per optional component, in the order resolved, its reason the wrapper's message; got {diagnostics}"
    assert (context.build_count(FIRST_READER), context.build_count(SECOND_READER), len(loads)) == (1, 1, 1), "each builder runs once per request, and the loader once"
    assert is_reported(lookup_error), "precondition: the first line marked the loader's exception as reported (H-60), the mark §3 reads"

    lines = module_log.lines()
    expected = [_failed_line(FIRST_READER, "LookupError", lookup_error), _failed_line_without_traceback(SECOND_READER, "LookupError", logged_with_request_id=http_request_id)]
    assert lines == expected, f"behaviour unchanged, and the loader's traceback written once, with the first reader's line; the module wrote {_said_with_traceback(lines)}"


@pytest.fixture
def loader_logger() -> Iterator[structlog.stdlib.BoundLogger]:
    """The logger of a test's own loader, writing warnings whatever the lane's level; its level put back on exit, pass or fail.

    ``LibreFolioBoundLogger`` marks an exception only when its stdlib logger is enabled for the line's level (§1, as
    H-60): a level inherited from a lane at ERROR would leave the loader's line unmarked, and ``_build`` would then be
    right to write the traceback. So the logger gets a level of its own, WARNING, and is checked to be enabled for it.
    """
    stdlib_logger = logging.getLogger(LOADER_LOGGER)
    previous_level = stdlib_logger.level
    # setLevel, not an assignment: it also clears the cached answers of isEnabledFor, both ways.
    stdlib_logger.setLevel(logging.WARNING)
    try:
        assert stdlib_logger.isEnabledFor(logging.WARNING), f"precondition: {LOADER_LOGGER!r} must write warnings at its own level; it is disabled, or logging.disable() covers WARNING in this process"
        yield get_logger(LOADER_LOGGER)
    finally:
        stdlib_logger.setLevel(previous_level)


@pytest.mark.asyncio
async def test_a_traceback_the_loader_already_logged_is_not_written_again_by_build(module_log: _ModuleLog, loader_logger: structlog.stdlib.BoundLogger) -> None:
    """§3, ``traceback_reported`` true because of any line: the loader's own, logged before it raised, in this request.

    Inside a bound request, the loader catches its failure, logs it on a logger of the test, ``warning(…,
    exc_info=error)`` (``loader_logger``: warnings whatever the lane's level), then raises it again. §1 marks ``error``
    as rendered in that request; ``_build`` meets it behind the ``ResourceLoadError`` as ``shown_error``, so its ``failed
    to build`` line has no ``exc_info`` key and ``logged_with_request_id`` the bound request. Preconditions, as before
    the cure: the loader ran once, its line marked ``error`` before ``_build`` wrote anything (H-60), and the component
    failed on a ``ResourceLoadError`` wrapping ``error``. Barrier before the absence: the loader's line was captured
    whole, its ``exc_info`` ``error`` itself, so the traceback is in the log. Red today: ``_build``'s line carries
    ``exc_info`` again, and no ``logged_with_request_id``.
    """
    _no_request_bound()
    error = LookupError("no price row for the requested day")
    reported_after_its_line: list[bool] = []

    def _logs_then_raises() -> NoReturn:
        try:
            raise error
        except LookupError:
            # The loader's own handling: its failure logged with the traceback, then raised again to the builder.
            loader_logger.warning(LOADER_EVENT, exc_info=error)
            reported_after_its_line.append(is_reported(error))
            raise

    context = _context(_spec(RESOURCE_USER, builder=_reads(ROWS, _logs_then_raises)))
    http_request_id = "req-h60r-loader"

    with _in_request(http_request_id):
        assert await context.resolve(RESOURCE_USER, required=False) is None, f"precondition: {RESOURCE_USER} must fail, its loader raising"

    failure = await _failure_of(context, RESOURCE_USER)
    assert reported_after_its_line == [True], f"precondition: the loader runs once, and its own line marks its exception as reported (H-60) before _build writes anything; got {reported_after_its_line}"
    assert isinstance(failure, ResourceLoadError) and failure.cause is error, f"precondition: the component must fail on a ResourceLoadError wrapping the loader's exception, got {failure!r}"

    loader_lines = module_log.lines_of(LOADER_LOGGER)
    expected_loader_line = {"event": LOADER_EVENT, "log_level": "warning", "logger": LOADER_LOGGER, "exc_info": error}
    assert loader_lines == [expected_loader_line], f"barrier: the loader's own line must be captured with its traceback, exc_info the very exception; the loader wrote {_said_with_traceback(loader_lines)}"

    lines = module_log.lines()
    expected = [_failed_line_without_traceback(RESOURCE_USER, "LookupError", logged_with_request_id=http_request_id)]
    assert lines == expected, f"the loader's line holds the traceback, so _build's line points to its request instead of writing it again; the module wrote {_said_with_traceback(lines)}"
