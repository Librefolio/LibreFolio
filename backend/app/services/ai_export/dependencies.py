"""Request-scoped build context: resolves and memoizes AI Export components.

`BuildContext` is the dependency resolver/memoization seam described by the Phase 0
AI Export refinement plan (workstream D, point 2): it guarantees a component (and
each of its dependencies) is built **at most once per request**, supports both sync
and async builders transparently, isolates optional-component unavailability
(catching any exception and recording an internal diagnostic instead of failing the
whole request), and propagates required-component failures explicitly so callers
can fail closed.

Binding success/failure semantics (per architecture review):
- A builder that *returns normally* - even with an empty payload (e.g. an empty
  list, zero totals, no rows) - is a **valid success**. Emptiness is a property of
  the data, not a build outcome, and this module never inspects payload content to
  decide success/failure.
- A builder that *raises* is the **only** thing that constitutes a failure here.
- Whether a required dataset/analysis with genuinely empty (but successfully
  built) data should be considered "not applicable" for a given analysis (e.g. a
  future HTTP 422) is a separate, higher-level applicability concern that this
  runtime deliberately does not decide - it belongs to the API/analysis-selection
  layer built on top of this module, once emptiness-vs-error semantics from real
  domain builders (workstreams E1/E2) are in place.
- A cached failure resolved as "optional" through more than one dataset/analysis
  sharing the same component within a request records **at most one**
  `ComponentDiagnostic` per `component_id` (deterministic, not one-per-call).

No real domain I/O happens here: this module only orchestrates already-registered
`ComponentSpec` builders through `ComponentRegistry`.

Workstream D2 (domain build context) extends `BuildContext` with the foundations
domain builders (E1/E2) need to load real data without depending on the legacy
`TaskSpec`/profile model or re-running I/O:
- an optional, validated `BuildScope` + matching temporal `BucketPlan`, threaded
  together (never one without the other) and cross-checked for consistency;
- an optional per-request `AsyncSession` boundary;
- a typed, request-scoped raw resource cache (`resource`/`db_resource`), kept
  strictly separate from the `SectionEnvelope` component cache above: raw
  resources (e.g. a `PortfolioReport`, price series, FIFO lots) are shared
  in-process objects, never serialized or exposed as a section.

**Concurrency invariant - shared `AsyncSession`**: component resolution
(`resolve`) stays concurrently memoized as before, but this context holds only
**one** `AsyncSession` for its entire lifetime, and SQLite/SQLAlchemy async
sessions are not safe for concurrent statement execution. Every `db_resource`
call - regardless of which key it loads - is therefore serialized through one
request-scoped `asyncio.Lock` (see `db_resource`); callers MUST route all
shared-session I/O through `db_resource` rather than touching `context.session`
directly and unprotected.

**Reentrancy invariant - nested `db_resource` calls from the same task**: a
`db_resource` loader is allowed to itself call `db_resource` again for a
*different* key (e.g. one DB-backed resource loading another as a
dependency) from within the *same* task. A plain `asyncio.Lock` is not
reentrant, so acquiring it again from inside the loader that already holds it
would deadlock that task against itself forever. `db_resource` therefore
tracks which task currently owns the DB lock (`_db_lock_owner`) and how many
nested frames it holds it for (`_db_lock_depth`, see `_db_serialized`):
- the *first* `db_resource` call from a task acquires the real lock and
  becomes the owner;
- further nested calls from *that same task* detect they already own the
  lock and skip re-acquiring it, only bumping the depth counter;
- only the outermost frame (the one that actually acquired the lock) ever
  releases it and clears ownership, in a `finally` so this happens even if a
  nested loader raises or the task is cancelled;
- a **different** (sibling/concurrent) task attempting `db_resource` while
  another task owns the lock still blocks on the real `asyncio.Lock`, so
  cross-task DB concurrency remains exactly 1.
Same-key recursion (a loader resolving its own key again) is a distinct,
already-guarded case - see `ResourceRecursionError` - and continues to raise
explicitly rather than being treated as ordinary cross-key reentrancy.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.signals import SignalTemporalClass
from backend.app.services.ai_export.components.envelope import SectionEnvelope, build_envelope
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, ResourceKey
from backend.app.services.ai_export.temporal.plan import BucketPlan
from backend.app.services.ai_export.temporal.policy import BucketDetailLevel, BucketingPolicy

T = TypeVar("T")

# =============================================================================
# DetailLevel <-> BucketDetailLevel mapping (workstream D2, point 2)
# =============================================================================
#
# `DetailLevel` (this package's runtime/API-facing detail enum) and
# `BucketDetailLevel` (the temporal engine's, workstream C) happen to share the
# same string values today, but they are two independently-owned enums - relying
# on that coincidence (e.g. `BucketDetailLevel(detail_level.value)`) would let a
# future divergence between the two silently miscompute a `BucketPlan`. This
# explicit, total mapping is the single seam where the two are reconciled.

_DETAIL_LEVEL_TO_BUCKET_DETAIL_LEVEL: Mapping[DetailLevel, BucketDetailLevel] = {
    DetailLevel.COMPACT: BucketDetailLevel.COMPACT,
    DetailLevel.STANDARD: BucketDetailLevel.STANDARD,
    DetailLevel.FULL: BucketDetailLevel.FULL,
}

# Fails loudly at import time (not silently at runtime) if either enum ever
# gains/loses a member without updating the mapping above.
assert set(_DETAIL_LEVEL_TO_BUCKET_DETAIL_LEVEL) == set(DetailLevel), "DETAIL_LEVEL_TO_BUCKET_DETAIL_LEVEL mapping must cover every DetailLevel member"
assert set(_DETAIL_LEVEL_TO_BUCKET_DETAIL_LEVEL.values()) == set(BucketDetailLevel), "DETAIL_LEVEL_TO_BUCKET_DETAIL_LEVEL mapping must cover every BucketDetailLevel member"


def map_detail_level_to_bucket_detail_level(detail_level: DetailLevel) -> BucketDetailLevel:
    """Explicit, total mapping from the runtime `DetailLevel` to the temporal engine's `BucketDetailLevel`."""
    if not isinstance(detail_level, DetailLevel):
        raise TypeError(f"detail_level must be a DetailLevel member, got {detail_level!r}")
    return _DETAIL_LEVEL_TO_BUCKET_DETAIL_LEVEL[detail_level]


def build_bucket_plan_for_scope(scope: BuildScope) -> BucketPlan:
    """Builds the single `BucketPlan` matching `scope`'s period and detail level.

    This is the canonical (and only sanctioned) way to build the `BucketPlan`
    passed to `BuildContext.__init__`: it guarantees the plan always matches
    `scope`, so `BuildContext`'s own consistency check (see
    `_ensure_bucket_plan_matches_scope`) never rejects it.
    """
    policy = BucketingPolicy.for_detail_level(map_detail_level_to_bucket_detail_level(scope.detail_level))
    return BucketPlan.build(scope.period_start, scope.period_end, policy)


def build_indicator_bucket_plan_for_scope(
    scope: BuildScope,
    temporal_class: SignalTemporalClass,
) -> BucketPlan:
    """Build one indicator-specific plan without changing the scope price plan."""
    policy = BucketingPolicy.for_indicator(
        map_detail_level_to_bucket_detail_level(scope.detail_level),
        temporal_class,
    )
    return BucketPlan.build(scope.period_start, scope.period_end, policy)


class BuildContextScopeError(ValueError):
    """Raised when `BuildContext`'s `BuildScope`/`BucketPlan`/session wiring is missing or inconsistent."""


def _ensure_bucket_plan_matches_scope(scope: BuildScope, bucket_plan: BucketPlan) -> None:
    if bucket_plan.start != scope.period_start or bucket_plan.end != scope.period_end:
        raise BuildContextScopeError(f"bucket_plan period [{bucket_plan.start}, {bucket_plan.end}] does not match scope period [{scope.period_start}, {scope.period_end}]")
    expected_policy = BucketingPolicy.for_detail_level(map_detail_level_to_bucket_detail_level(scope.detail_level))
    if bucket_plan.policy != expected_policy:
        raise BuildContextScopeError(f"bucket_plan.policy {bucket_plan.policy!r} does not match the policy for scope.detail_level={scope.detail_level!r} (expected {expected_policy!r})")


# =============================================================================
# Typed request-scoped raw resource cache (workstream D2, point 4)
# =============================================================================


class ResourceKeyConflictError(ValueError):
    """Raised when the same stable `ResourceKey.name` is reused with a conflicting expected type or loader mode."""


class ResourceLoadError(RuntimeError):
    """Deterministic wrapped error memoized when a resource loader fails or returns a mistyped value.

    Every caller resolving the same failed key within a request receives this
    *exact same* exception instance, with `cause` preserving the original
    loader exception (or a `TypeError` describing an expected/actual type
    mismatch). `asyncio.CancelledError` is never wrapped/memoized here - it
    always propagates immediately (see `BuildContext._resolve_resource`).
    """

    def __init__(self, key_name: str, cause: BaseException):
        self.key_name = key_name
        self.cause = cause
        super().__init__(f"resource {key_name!r} failed to load: {cause}")


class ResourceRecursionError(RuntimeError):
    """Raised when a resource loader recursively resolves its own key from within the same task.

    `BuildContext`'s per-key resolution lock is a plain `asyncio.Lock`, which
    is not reentrant: without this explicit check, a loader that (directly or
    transitively) calls `context.resource`/`context.db_resource` again for the
    *same* key from the *same* task would deadlock the event loop instead of
    failing. Like any other loader failure, this typically reaches the
    original caller wrapped as `ResourceLoadError.cause` (the outer key is
    memoized as failed too - the loader that recursed on itself is broken by
    construction).
    """


@dataclass(slots=True)
class _ResourceOutcome:
    value: object
    error: BaseException | None


class ComponentBuildError(RuntimeError):
    """Base error raised while resolving a component within a `BuildContext`."""


class RequiredComponentBuildError(ComponentBuildError):
    """Raised when a component requested as required could not be built.

    Carries the originating `component_id` and the underlying cause so callers can
    surface a fail-closed error (e.g. an HTTP 503) without losing the root cause.
    """

    def __init__(self, component_id: str, cause: BaseException):
        self.component_id = component_id
        self.cause = cause
        super().__init__(f"required component {component_id!r} failed to build: {cause}")


@dataclass(frozen=True, slots=True)
class ComponentDiagnostic:
    """Internal-only record explaining why an optional component was omitted.

    Never exposed to API callers; purely for internal logging/debugging.
    """

    component_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class PriceSamplingDiagnostic:
    detail_level: DetailLevel
    exponent: int
    half_life_offset: int
    max_bucket_days: int
    bucket_count: int


@dataclass(frozen=True, slots=True)
class IndicatorSamplingDiagnostic:
    signal_instance_id: str
    signal_code: str
    temporal_class: SignalTemporalClass
    detail_level: DetailLevel
    exponent: int
    half_life_offset: int
    max_bucket_days: int
    bucket_count: int


@dataclass(slots=True)
class _ComponentOutcome:
    envelope: SectionEnvelope | None
    error: BaseException | None


class BuildContext:
    """Request-scoped resolver/memoization seam over a `ComponentRegistry`.

    One instance MUST be created per AI Export request (never shared/reused across
    requests): memoization correctness and the "built at most once" guarantee rely
    on the context's lifetime matching a single request.

    `scope`/`bucket_plan`/`session` are all optional and independent of the
    component resolver above (existing callers that only need `resolve()` keep
    working unchanged): they are workstream D2's domain build context
    foundations, consumed by domain builders (workstreams E1/E2) and by the
    typed resource cache (`resource`/`db_resource`) below.
    - `scope` and `bucket_plan` must be provided **together** (both or
      neither): `bucket_plan` must exactly match `scope`'s period and detail
      level (see `build_bucket_plan_for_scope`), or construction raises
      `BuildContextScopeError`.
    - `session`, if provided, must be an `AsyncSession`; see the module
      docstring for the DB-serialization invariant enforced by `db_resource`.
    """

    def __init__(
        self,
        registry: ComponentRegistry,
        *,
        request_id: str,
        scope: BuildScope | None = None,
        bucket_plan: BucketPlan | None = None,
        session: AsyncSession | None = None,
    ):
        self._registry = registry
        self.request_id = request_id
        self._results: dict[str, _ComponentOutcome] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._build_counts: dict[str, int] = {}
        self._diagnosed: set[str] = set()
        self.diagnostics: list[ComponentDiagnostic] = []
        self._price_sampling: PriceSamplingDiagnostic | None = None
        self._indicator_sampling: dict[str, IndicatorSamplingDiagnostic] = {}
        self._event_selection_used = False

        if (scope is None) != (bucket_plan is None):
            raise BuildContextScopeError("scope and bucket_plan must be provided together, or not at all")
        if scope is not None:
            if not isinstance(scope, BuildScope):
                raise TypeError(f"scope must be a BuildScope instance, got {type(scope).__name__}")
            if not isinstance(bucket_plan, BucketPlan):
                raise TypeError(f"bucket_plan must be a BucketPlan instance, got {type(bucket_plan).__name__}")
            _ensure_bucket_plan_matches_scope(scope, bucket_plan)
        if session is not None and not isinstance(session, AsyncSession):
            raise TypeError(f"session must be an AsyncSession instance, got {type(session).__name__}")

        self.scope = scope
        self.bucket_plan = bucket_plan
        self._session = session

        # Request-scoped DB serialization lock: see the module docstring's
        # "Concurrency invariant" - every `db_resource` call is serialized
        # through this single lock, regardless of which key it loads.
        self._db_lock = asyncio.Lock()
        # Reentrancy bookkeeping for the lock above - see the module
        # docstring's "Reentrancy invariant" and `_db_serialized`. `_db_lock_owner`
        # is the task currently holding `_db_lock` (via `db_resource`), or `None`
        # if nobody holds it; `_db_lock_depth` is how many nested `db_resource`
        # frames that owner task currently has open. Both must return to
        # `(None, 0)` once the outermost frame exits, including on error/cancellation.
        self._db_lock_owner: asyncio.Task | None = None
        self._db_lock_depth: int = 0

        # Typed raw resource cache, deliberately separate from `_results`
        # above: values here are arbitrary in-process Python objects (never
        # `SectionEnvelope`s), keyed by `ResourceKey.name`.
        self._resource_meta: dict[str, tuple[type, str]] = {}
        self._resource_results: dict[str, _ResourceOutcome] = {}
        self._resource_locks: dict[str, asyncio.Lock] = {}
        self._resolving_resources: dict[str, asyncio.Task | None] = {}

    @property
    def registry(self) -> ComponentRegistry:
        return self._registry

    @property
    def session(self) -> AsyncSession | None:
        """The request-scoped `AsyncSession`, or `None` if this context was built without one.

        Callers MUST NOT issue statements on this session concurrently with
        another coroutine; prefer `db_resource`, which serializes access for
        you. Direct use (if ever needed) must be wrapped in
        `async with context.db_lock:`.
        """
        return self._session

    @property
    def db_lock(self) -> asyncio.Lock:
        """The request-scoped lock serializing every `db_resource` invocation.

        Exposed for introspection/tests only - production callers must go
        through `db_resource` (or `async with context._db_serialized():` if a
        future caller genuinely needs the reentrancy-aware boundary directly),
        never `db_lock` itself, since acquiring it directly bypasses the
        owner/depth bookkeeping that makes nested same-task `db_resource`
        calls safe (see the module docstring's "Reentrancy invariant").
        """
        return self._db_lock

    def build_count(self, component_id: str) -> int:
        """Number of times `component_id`'s builder actually ran (test/diagnostic seam).

        Used to assert the "at most once per request" memoization guarantee.
        """
        return self._build_counts.get(component_id, 0)

    @property
    def price_sampling(self) -> PriceSamplingDiagnostic | None:
        return self._price_sampling

    @property
    def indicator_sampling(
        self,
    ) -> tuple[IndicatorSamplingDiagnostic, ...]:
        return tuple(self._indicator_sampling[instance_id] for instance_id in sorted(self._indicator_sampling))

    @property
    def event_selection_used(self) -> bool:
        return self._event_selection_used

    def register_price_sampling(self) -> None:
        if self.scope is None or self.bucket_plan is None:
            raise BuildContextScopeError("price sampling registration requires scope and bucket_plan")
        policy = self.bucket_plan.policy
        diagnostic = PriceSamplingDiagnostic(
            detail_level=self.scope.detail_level,
            exponent=policy.exponent,
            half_life_offset=policy.half_life_offset,
            max_bucket_days=policy.max_bucket_days,
            bucket_count=len(self.bucket_plan.buckets),
        )
        if self._price_sampling is not None and self._price_sampling != diagnostic:
            raise BuildContextScopeError("conflicting price sampling diagnostics in one request")
        self._price_sampling = diagnostic

    def register_indicator_sampling(
        self,
        *,
        signal_instance_id: str,
        signal_code: str,
        temporal_class: SignalTemporalClass,
        bucket_plan: BucketPlan,
    ) -> None:
        if self.scope is None:
            raise BuildContextScopeError("indicator sampling registration requires scope")
        diagnostic = IndicatorSamplingDiagnostic(
            signal_instance_id=signal_instance_id,
            signal_code=signal_code,
            temporal_class=temporal_class,
            detail_level=self.scope.detail_level,
            exponent=bucket_plan.policy.exponent,
            half_life_offset=bucket_plan.policy.half_life_offset,
            max_bucket_days=bucket_plan.policy.max_bucket_days,
            bucket_count=len(bucket_plan.buckets),
        )
        existing = self._indicator_sampling.get(signal_instance_id)
        if existing is not None and existing != diagnostic:
            raise BuildContextScopeError("conflicting indicator sampling diagnostics for " f"{signal_instance_id!r}")
        self._indicator_sampling[signal_instance_id] = diagnostic

    def register_event_selection(self) -> None:
        self._event_selection_used = True

    async def resolve(self, component_id: str, *, required: bool) -> SectionEnvelope | None:
        """Resolves `component_id`, memoized for the lifetime of this context.

        Returns the built `SectionEnvelope`, or `None` if the component is optional
        and unavailable (an internal `ComponentDiagnostic` is recorded in that case).
        Raises `RequiredComponentBuildError` if `required=True` and the build failed
        (directly, or transitively through one of its dependencies).
        """
        outcome = self._results.get(component_id)
        if outcome is None:
            lock = self._locks.setdefault(component_id, asyncio.Lock())
            async with lock:
                outcome = self._results.get(component_id)
                if outcome is None:
                    outcome = await self._build(component_id)
                    self._results[component_id] = outcome
        if outcome.error is not None:
            if required:
                raise RequiredComponentBuildError(component_id, outcome.error)
            # The same cached failure can be resolved as "optional" through more than
            # one dataset/analysis sharing this component within the same request; a
            # diagnostic is recorded at most once per component_id (deterministic,
            # single entry) rather than once per resolve() call.
            if component_id not in self._diagnosed:
                self._diagnosed.add(component_id)
                self.diagnostics.append(ComponentDiagnostic(component_id=component_id, reason=str(outcome.error)))
            return None
        return outcome.envelope

    async def _build(self, component_id: str) -> _ComponentOutcome:
        self._build_counts[component_id] = self._build_counts.get(component_id, 0) + 1
        spec = self._registry.get(component_id)
        try:
            dependency_envelopes: dict[str, SectionEnvelope] = {}
            for dep_id in spec.dependencies:
                # A component's own declared dependencies are always required for
                # *it* to build meaningfully; whether the failure is ultimately
                # tolerated is decided by the top-level caller's `required` flag.
                dependency_envelopes[dep_id] = await self.resolve(dep_id, required=True)  # type: ignore[assignment]
            raw = spec.builder(self, dependency_envelopes)
            if inspect.isawaitable(raw):
                raw = await raw
            envelope = build_envelope(spec, raw)
            return _ComponentOutcome(envelope=envelope, error=None)
        except Exception as exc:  # noqa: BLE001 - intentional isolation boundary, re-raised explicitly for required callers via resolve()
            return _ComponentOutcome(envelope=None, error=exc)

    # =========================================================================
    # Typed request-scoped raw resource cache (workstream D2, point 4)
    # =========================================================================

    async def resource(self, key: ResourceKey[T], loader: Callable[[], T | Awaitable[T]]) -> T:
        """Resolves a request-scoped raw resource, memoized (success or error) for this context's lifetime.

        `loader` is a zero-argument callable, sync or async - `BuildContext`
        awaits it transparently either way. At most one invocation happens per
        `key.name` per request, even under concurrent callers. A loader that
        raises, or whose return value fails `isinstance(value, key.expected_type)`,
        is memoized as a `ResourceLoadError` (preserving the original cause) and
        re-raised identically to every subsequent caller; a raised
        `ResourceLoadError` propagates through the same `try`/`except` that
        already isolates required/optional component builder failures (see
        `resolve`/`_build` above) when called from within a component builder.
        `asyncio.CancelledError` is never memoized - it always propagates
        immediately, uncached.
        """

        async def _run() -> object:
            raw = loader()
            if inspect.isawaitable(raw):
                raw = await raw
            return raw

        return await self._resolve_resource(key, mode="resource", run_loader=_run)

    async def db_resource(self, key: ResourceKey[T], loader: Callable[[AsyncSession], T | Awaitable[T]]) -> T:
        """Resolves a DB-backed raw resource using this context's shared `AsyncSession`.

        `loader` receives the context's `AsyncSession` and may be sync or
        async. Every `db_resource` call in this context - regardless of
        `key` - is serialized through one request-scoped lock (`db_lock`):
        the shared `AsyncSession` must never execute statements concurrently.
        A loader is allowed to itself call `db_resource` again for a
        *different* key from within the same task (e.g. to load a
        dependency): see the module docstring's "Reentrancy invariant" and
        `_db_serialized` - this does not deadlock and does not weaken
        cross-task serialization (sibling tasks still see DB concurrency 1).
        Resolving the *same* key recursively is a distinct case that still
        raises `ResourceRecursionError` (see `_resolve_resource`).
        Memoization/error/cancellation semantics match `resource` above.
        Raises `BuildContextScopeError` if this context has no `session`.
        """
        if self._session is None:
            raise BuildContextScopeError("db_resource requires BuildContext to be constructed with a session")
        session = self._session

        async def _run() -> object:
            async with self._db_serialized():
                raw = loader(session)
                if inspect.isawaitable(raw):
                    raw = await raw
                return raw

        return await self._resolve_resource(key, mode="db_resource", run_loader=_run)

    @asynccontextmanager
    async def _db_serialized(self) -> AsyncIterator[None]:
        """Reentrant-per-task boundary around the shared `AsyncSession`.

        See the module docstring's "Reentrancy invariant". The *first* call
        from a given task acquires `_db_lock` for real and records itself as
        `_db_lock_owner`; nested calls from that same task detect they
        already own the lock and skip re-acquiring it (which would deadlock,
        since `asyncio.Lock` is not reentrant), only bumping `_db_lock_depth`.
        A different task calling this while the lock is held still blocks on
        `_db_lock` normally, so cross-task DB concurrency stays at 1. The
        `finally` below always restores `_db_lock_owner`/`_db_lock_depth` and
        releases the lock on the way out of the outermost frame, even if the
        wrapped loader raises or the task is cancelled.
        """
        current_task = asyncio.current_task()
        is_nested_reentry = current_task is not None and self._db_lock_owner is current_task
        if not is_nested_reentry:
            await self._db_lock.acquire()
            self._db_lock_owner = current_task
        self._db_lock_depth += 1
        try:
            yield
        finally:
            self._db_lock_depth -= 1
            if not is_nested_reentry:
                # Only the outermost frame for this task ever clears ownership
                # and releases the lock - nested frames never touch either.
                self._db_lock_owner = None
                self._db_lock.release()

    def _register_or_check_resource_key(self, key: ResourceKey, mode: str) -> None:
        existing = self._resource_meta.get(key.name)
        if existing is None:
            self._resource_meta[key.name] = (key.expected_type, mode)
            return
        expected_type, existing_mode = existing
        if expected_type is not key.expected_type or existing_mode != mode:
            raise ResourceKeyConflictError(f"resource key {key.name!r} already registered as (type={expected_type.__name__!r}, mode={existing_mode!r}); " f"got conflicting (type={key.expected_type.__name__!r}, mode={mode!r})")

    async def _resolve_resource(self, key: ResourceKey[T], *, mode: str, run_loader: Callable[[], Awaitable[object]]) -> T:
        if not isinstance(key, ResourceKey):
            raise TypeError(f"key must be a ResourceKey instance, got {type(key).__name__}")
        self._register_or_check_resource_key(key, mode)

        outcome = self._resource_results.get(key.name)
        if outcome is not None:
            return self._unwrap_resource(outcome)

        current_task = asyncio.current_task()
        if current_task is not None and self._resolving_resources.get(key.name) is current_task:
            # The same task is already mid-load for this exact key: this call is a
            # (direct or transitive) recursive re-entry, not ordinary concurrent
            # access from a different task/coroutine. Acquiring the (non-reentrant)
            # per-key lock below would deadlock the event loop, so fail explicitly.
            raise ResourceRecursionError(f"resource {key.name!r} is already being resolved by this same task (recursive same-key resolution would deadlock)")

        lock = self._resource_locks.setdefault(key.name, asyncio.Lock())
        async with lock:
            outcome = self._resource_results.get(key.name)
            if outcome is None:
                self._resolving_resources[key.name] = current_task
                try:
                    try:
                        raw = await run_loader()
                    except asyncio.CancelledError:
                        # Cancellation is never a resource "failure": propagate it
                        # immediately and leave the key unresolved for a future
                        # (non-cancelled) attempt to retry cleanly.
                        raise
                    except Exception as exc:  # noqa: BLE001 - intentional isolation boundary, wrapped deterministically below
                        outcome = _ResourceOutcome(value=None, error=ResourceLoadError(key.name, exc))
                    else:
                        if not isinstance(raw, key.expected_type):
                            type_error = TypeError(f"resource {key.name!r}: loader returned {type(raw).__name__}, expected {key.expected_type.__name__}")
                            outcome = _ResourceOutcome(value=None, error=ResourceLoadError(key.name, type_error))
                        else:
                            outcome = _ResourceOutcome(value=raw, error=None)
                    self._resource_results[key.name] = outcome
                finally:
                    del self._resolving_resources[key.name]
        return self._unwrap_resource(outcome)

    @staticmethod
    def _unwrap_resource(outcome: _ResourceOutcome) -> T:
        if outcome.error is not None:
            raise outcome.error
        return outcome.value  # type: ignore[return-value]
