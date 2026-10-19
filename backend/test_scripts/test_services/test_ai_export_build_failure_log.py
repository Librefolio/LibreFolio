"""H-60 · TA-1 — the line ``BuildContext._build`` writes when an AI Export component fails (contract §1, §0's meanings).

Today a component that fails to build leaves no trace: ``_build`` turns the exception into a cached failed outcome (a
``ComponentDiagnostic`` for an optional caller, a ``RequiredComponentBuildError`` for a required one) and writes nothing,
so an export that comes back short never says why. Contract §1 gives ``backend.app.services.ai_export.dependencies`` a
module logger, ``get_logger(__name__)``, and one **warning** per failed component per ``BuildContext``, written in the
``except Exception`` of ``_build``:

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

The log is read with ``structlog.testing.capture_logs`` for the whole test, ``add_logger_name`` naming each event's
logger, behind a barrier: a probe logged under the module's logger name reaches the capture before anything is built
(this works before the module has a logger; capture_logs swaps the processors inside the configured list, so a logger
cached on it still reaches the capture: test_post_migration.py, section 13). Every expected line is compared whole, keys
included; an exception compares by identity, so ``exc_info`` is pinned to the very object. An absence (a successful
build, a cancellation) is asserted beside a presence in the same request, a failing sibling's line: without it the
absence would hold just as well with no logging at all.

Pure: in-memory registries and builders, as in test_ai_export_component_runtime.py; no database, no server, no file.

Red today: ``_build`` writes nothing (the module has no logger), so every expected line is missing, the presence
barriers of the two absence tests included.
"""

from __future__ import annotations

import asyncio
import traceback
import uuid
from collections.abc import Callable, Iterator, Mapping
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

#: The structlog name of the module's logger (contract §1: ``get_logger(__name__)``).
MODULE_LOGGER = "backend.app.services.ai_export.dependencies"
FAILED_EVENT = "AI Export component failed to build"
DEPENDENCY_EVENT = "AI Export component not built: a dependency failed"
#: Every key a line may hold: ids, a class name, a reason code, the exception, and what the capture adds (``logger``,
#: ``log_level``). Nothing that could carry a payload value.
FAILED_KEYS = frozenset({"event", "log_level", "logger", "component_id", "error_type", "reason_code", "exc_info"})
DEPENDENCY_KEYS = frozenset({"event", "log_level", "logger", "component_id", "dependency_id"})

SOURCE = "portfolio.h60_source"
DEPENDENT = "portfolio.h60_dependent"
TOP = "portfolio.h60_top"
RESOURCE_USER = "portfolio.h60_resource_user"
INVALID_PAYLOAD = "portfolio.h60_invalid_payload"
BARRIER = "portfolio.h60_presence_barrier"


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


# =============================================================================
# Reading the log
# =============================================================================


class _ModuleLog:
    """The events the capture saw from the module's logger, in the order written, the barrier's probe left out."""

    def __init__(self, entries: list[dict[str, Any]], probe: str) -> None:
        self._entries = entries
        self._probe = probe

    def lines(self) -> list[dict[str, Any]]:
        return [entry for entry in self._entries if entry.get("logger") == MODULE_LOGGER and entry.get("event") != self._probe]


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
    """A whole ``failed to build`` line; its ``exc_info`` compares by identity (an exception has no ``__eq__``)."""
    line: dict[str, Any] = {"event": FAILED_EVENT, "log_level": "warning", "logger": MODULE_LOGGER, "component_id": component_id, "error_type": error_type, "exc_info": shown}
    if reason_code is not None:
        line["reason_code"] = reason_code
    return line


def _dependency_line(component_id: str, dependency_id: str) -> dict[str, Any]:
    """A whole ``not built: a dependency failed`` line: no ``exc_info``, no error field."""
    return {"event": DEPENDENCY_EVENT, "log_level": "warning", "logger": MODULE_LOGGER, "component_id": component_id, "dependency_id": dependency_id}


def _said(lines: list[dict[str, Any]]) -> list[tuple[Any, Any, Any]]:
    """What the module wrote, one ``(level, event, component_id)`` per line: for the assertion messages."""
    return [(line.get("log_level"), line.get("event"), line.get("component_id")) for line in lines]


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
