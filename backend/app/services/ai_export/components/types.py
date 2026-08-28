"""Shared primitive types for the AI Export component/dataset/analysis runtime.

This module is independent from the public Pydantic wire schemas. It is the
single source of truth for component/dataset/analysis runtime primitives,
including `BuildScope` (the validated immutable request scope) and `ResourceKey`
(the typed identity for `BuildContext`'s internal resource cache).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as Date
from enum import StrEnum

from .._int_validation import require_positive_int


class Domain(StrEnum):
    """AI Export domain a component/dataset/analysis belongs to or applies to."""

    PORTFOLIO = "portfolio"
    BROKER = "broker"
    ASSET = "asset"
    FX = "fx"


class DetailLevel(StrEnum):
    """Snapshot detail level requested by the caller."""

    COMPACT = "compact"
    STANDARD = "standard"
    FULL = "full"


ALL_DETAIL_LEVELS: frozenset[DetailLevel] = frozenset(DetailLevel)

# Shared "stable code identifier" pattern reused by every catalog layer (component
# aggregator kind, dataset/analysis applicability_code, scope/technical requirement
# codes): lowercase, dot/underscore-segmented, never free-form human text.
CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")

# Shared "page/scope slug" pattern for `applicable_pages`-style tuples: lowercase
# kebab-case route/scope identifiers (e.g. "dashboard", "asset-detail").
PAGE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")

_CODE_PATTERN = CODE_PATTERN


class PeriodBehavior(StrEnum):
    """Declares how a component's output relates to the AI Export period.

    This is metadata only: the runtime foundation does not implement period
    arithmetic or bucket aggregation. That logic is owned by the temporal engine
    workstream (`backend.app.services.ai_export.temporal`) and will be threaded
    through `BuildContext` by the domain assembler workstreams (E1/E2) without
    changing this catalog/component runtime.
    """

    NONE = "none"  # point-in-time, independent of the requested period
    AS_OF = "as_of"  # snapshot valid at snapshot_as_of, no history
    WINDOWED = "windowed"  # spans the inclusive [period.start, snapshot_as_of] range
    AGGREGATED = "aggregated"  # windowed and reduced through a temporal aggregator


@dataclass(frozen=True, slots=True)
class TemporalAggregatorSpec:
    """Metadata describing the temporal aggregator a component declares it needs.

    Kept intentionally opaque (kind + description): the actual bucket/aggregation
    algorithms belong to the temporal engine workstream. A real aggregator
    implementation is wired in later through `BuildContext` without changing this
    metadata shape. `kind` must be a stable lowercase code identifier (e.g.
    `"ohlc_bucket"`), never free-form/human text.
    """

    kind: str
    description: str = ""

    def __post_init__(self) -> None:
        if not self.kind:
            raise ValueError("aggregator kind must not be empty")
        if not _CODE_PATTERN.fullmatch(self.kind):
            raise ValueError(f"aggregator kind must be a stable lowercase code identifier, not free text: {self.kind!r}")


# =============================================================================
# BuildScope (workstream D2 — domain build context)
# =============================================================================


class BuildScopeError(ValueError):
    """Raised when a `BuildScope` declaration is internally inconsistent."""


_CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")


def normalize_currency_code(value: object) -> str:
    """Validates/normalizes a canonical uppercase ISO-like 3-letter currency code.

    This is intentionally a lightweight *structural* check (3 uppercase
    letters), not a full ISO 4217 registry lookup like
    `backend.app.schemas.common.Currency.validate_code`: the component runtime
    only needs a stable canonical shape to key on.
    """
    if not isinstance(value, str):
        raise BuildScopeError(f"currency code must be a string, got {type(value).__name__}")
    code = value.strip().upper()
    if not _CURRENCY_CODE_PATTERN.fullmatch(code):
        raise BuildScopeError(f"currency code must be a canonical 3-letter ISO-like code, got {value!r}")
    return code


def _normalize_broker_scope(values: object) -> tuple[int, ...]:
    """Normalizes any iterable of broker IDs into a sorted, deduplicated tuple."""
    if isinstance(values, (str, bytes)) or not hasattr(values, "__iter__"):
        raise BuildScopeError(f"broker_scope must be an iterable of positive ints, got {type(values).__name__}")
    seen: set[int] = set()
    normalized: list[int] = []
    for raw in values:
        broker_id = require_positive_int(raw, "broker_scope entries", error_cls=BuildScopeError)
        if broker_id not in seen:
            seen.add(broker_id)
            normalized.append(broker_id)
    normalized.sort()
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class BuildScope:
    """Immutable, validated request scope threaded through every domain builder.

    Carries everything a domain builder needs to resolve its data without
    depending on the legacy `TaskSpec`/profile model (`backend.app.services.
    ai_export.models`): caller identity, the requested `Domain`/`DetailLevel`,
    the inclusive AI Export period, the target presentation currency, the
    broker access scope and the domain-specific entity target.

    `request_id` is expected to be a caller-supplied unique identifier (e.g. a
    UUID); this value object only validates its *shape* (non-empty string) -
    it cannot enforce global uniqueness across requests by itself, that is the
    caller's responsibility (e.g. one fresh UUID per HTTP request).

    `snapshot_as_of` is always exactly `period_end`: the AI Export period is
    `[period_start, period_end]` inclusive, and the snapshot instant is its
    upper bound - there is no separate "as of" field to keep out of sync.

    Domain-specific entity/broker-scope invariants (enforced in
    `__post_init__`, see the workstream D2 plan section):
    - `PORTFOLIO`: no entity target - `asset_id`/`broker_id`/`base_currency`/
      `quote_currency` must all be `None`. `broker_scope` may be empty (whole
      portfolio, every accessible broker) or a non-empty subset of broker IDs.
    - `BROKER`: `broker_id` is required and `broker_scope` must be *exactly*
      `(broker_id,)` - a Broker-domain scope can never mix in other brokers.
    - `ASSET`: `asset_id` is required (positive int); `broker_id`/
      `base_currency`/`quote_currency` must be `None`. `broker_scope` may be
      empty or non-empty (position scoping across brokers).
    - `FX`: `base_currency` and `quote_currency` are required and must be
      distinct; `asset_id`/`broker_id` must be `None`. `broker_scope` may be
      empty or non-empty (exposure scoping across brokers).
    """

    request_id: str
    user_id: int
    domain: Domain
    detail_level: DetailLevel
    period_start: Date
    period_end: Date
    target_currency: str
    broker_scope: tuple[int, ...] = ()
    asset_id: int | None = None
    broker_id: int | None = None
    base_currency: str | None = None
    quote_currency: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise BuildScopeError("request_id must be a non-empty string")
        object.__setattr__(self, "user_id", require_positive_int(self.user_id, "user_id", error_cls=BuildScopeError))
        if not isinstance(self.domain, Domain):
            raise BuildScopeError(f"domain must be a Domain member, got {self.domain!r}")
        if not isinstance(self.detail_level, DetailLevel):
            raise BuildScopeError(f"detail_level must be a DetailLevel member, got {self.detail_level!r}")
        if type(self.period_start) is not Date or type(self.period_end) is not Date:
            raise BuildScopeError("period_start and period_end must be datetime.date instances")
        if self.period_start > self.period_end:
            raise BuildScopeError("period_start must not be after period_end")
        object.__setattr__(self, "target_currency", normalize_currency_code(self.target_currency))
        object.__setattr__(self, "broker_scope", _normalize_broker_scope(self.broker_scope))

        if self.asset_id is not None:
            object.__setattr__(self, "asset_id", require_positive_int(self.asset_id, "asset_id", error_cls=BuildScopeError))
        if self.broker_id is not None:
            object.__setattr__(self, "broker_id", require_positive_int(self.broker_id, "broker_id", error_cls=BuildScopeError))
        if self.base_currency is not None:
            object.__setattr__(self, "base_currency", normalize_currency_code(self.base_currency))
        if self.quote_currency is not None:
            object.__setattr__(self, "quote_currency", normalize_currency_code(self.quote_currency))

        if self.domain == Domain.PORTFOLIO:
            _validate_portfolio_target(self)
        elif self.domain == Domain.BROKER:
            _validate_broker_target(self)
        elif self.domain == Domain.ASSET:
            _validate_asset_target(self)
        elif self.domain == Domain.FX:
            _validate_fx_target(self)
        else:  # pragma: no cover - exhaustive over Domain, guards future additions
            raise BuildScopeError(f"unsupported domain: {self.domain!r}")

    @property
    def snapshot_as_of(self) -> Date:
        """Snapshot instant: always exactly `period_end` (inclusive period upper bound)."""
        return self.period_end


def _validate_portfolio_target(scope: BuildScope) -> None:
    if scope.asset_id is not None or scope.broker_id is not None or scope.base_currency is not None or scope.quote_currency is not None:
        raise BuildScopeError("PORTFOLIO scope must not declare an entity target (asset_id/broker_id/base_currency/quote_currency)")


def _validate_broker_target(scope: BuildScope) -> None:
    if scope.broker_id is None:
        raise BuildScopeError("BROKER scope requires broker_id")
    if scope.asset_id is not None or scope.base_currency is not None or scope.quote_currency is not None:
        raise BuildScopeError("BROKER scope must not declare asset_id/base_currency/quote_currency")
    if scope.broker_scope != (scope.broker_id,):
        raise BuildScopeError(f"BROKER scope requires broker_scope == (broker_id,), got broker_id={scope.broker_id!r} broker_scope={scope.broker_scope!r}")


def _validate_asset_target(scope: BuildScope) -> None:
    if scope.asset_id is None:
        raise BuildScopeError("ASSET scope requires asset_id")
    if scope.broker_id is not None or scope.base_currency is not None or scope.quote_currency is not None:
        raise BuildScopeError("ASSET scope must not declare broker_id/base_currency/quote_currency")


def _validate_fx_target(scope: BuildScope) -> None:
    if scope.base_currency is None or scope.quote_currency is None:
        raise BuildScopeError("FX scope requires base_currency and quote_currency")
    if scope.asset_id is not None or scope.broker_id is not None:
        raise BuildScopeError("FX scope must not declare asset_id/broker_id")
    if scope.base_currency == scope.quote_currency:
        raise BuildScopeError(f"FX scope requires distinct base_currency/quote_currency, got {scope.base_currency!r} twice")


# =============================================================================
# ResourceKey (workstream D2 — typed request-scoped raw resource cache)
# =============================================================================


@dataclass(frozen=True)
class ResourceKey[T]:
    """Stable, type-safe identity for an entry in `BuildContext`'s raw resource cache.

    Two `ResourceKey` instances identify the *same cache slot* purely by
    `name` (a stable string identifier, e.g. `"portfolio_report"`) - this lets
    `BuildContext` detect when the same stable key is reused with a
    conflicting `expected_type` or loader mode (a programming error) instead
    of silently letting two incompatible callers share one cache slot.
    `expected_type` validates the *value* a loader produces; it deliberately
    does not participate in key equality/hashing (see above).

    This is an internal-only primitive: raw resources cached under a
    `ResourceKey` are never converted to a `SectionEnvelope` or serialized -
    see `backend.app.services.ai_export.dependencies.BuildContext.resource`.
    """

    name: str
    expected_type: type[T]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("ResourceKey.name must be a non-empty string")
        if not isinstance(self.expected_type, type):
            raise TypeError(f"ResourceKey.expected_type must be a type, got {self.expected_type!r}")

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ResourceKey):
            return NotImplemented
        return self.name == other.name
