"""Focused tests for the AI Export component runtime foundations (workstream D)
and the domain build context foundations (workstream D2).

Covers `ComponentSpec` validation, `ComponentRegistry` collection-level validation
(duplicate IDs, unknown dependencies, cycle detection, canonical order), the
`SectionEnvelope`/`build_envelope` payload validation and JSON-safety guarantee,
the `BuildContext` request-scoped resolver/memoization seam (sync/async
builders, "built at most once", required-failure propagation, optional-failure
isolation), `BuildScope` validation, the `DetailLevel`/`BucketDetailLevel`
mapping, `BuildContext`'s `BuildScope`/`BucketPlan`/`AsyncSession` wiring, and
the typed raw resource cache (`resource`/`db_resource`).
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.schemas.portfolio import LotsAnalysisResponse
from backend.app.schemas.prices import FAPriceQueryResult
from backend.app.services.ai_export.components.envelope import (
    ComponentPayloadValidationError,
    SectionEnvelope,
    build_envelope,
)
from backend.app.services.ai_export.components.resources import (
    FxRateObservation,
    FxRateSeriesResource,
    LotsResultsResource,
    PriceResultsResource,
)
from backend.app.services.ai_export.components.registry import (
    ComponentDependencyCycleError,
    ComponentRegistry,
    DuplicateComponentIdError,
    UnknownComponentError,
)
from backend.app.services.ai_export.components.spec import ComponentSpec, ComponentSpecError
from backend.app.services.ai_export.components.types import (
    BuildScope,
    BuildScopeError,
    DetailLevel,
    Domain,
    PeriodBehavior,
    ResourceKey,
    TemporalAggregatorSpec,
)
from backend.app.services.ai_export.dependencies import (
    BuildContext,
    BuildContextScopeError,
    RequiredComponentBuildError,
    ResourceKeyConflictError,
    ResourceLoadError,
    ResourceRecursionError,
    build_bucket_plan_for_scope,
    map_detail_level_to_bucket_detail_level,
)
from backend.app.services.ai_export.temporal.plan import BucketPlan
from backend.app.services.ai_export.temporal.policy import BucketDetailLevel, BucketingPolicy


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int
    label: str = ""


class _ListPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[int]


def _spec(component_id: str, *, dependencies: tuple[str, ...] = (), builder=None) -> ComponentSpec:
    def _default_builder(context, dependencies_map):
        return _Payload(value=1, label=component_id)

    return ComponentSpec(
        component_id=component_id,
        version=1,
        domains=frozenset({Domain.PORTFOLIO}),
        output_model=_Payload,
        builder=builder or _default_builder,
        dependencies=dependencies,
    )


class TestComponentSpecValidation:
    def test_rejects_invalid_id_format(self):
        with pytest.raises(ComponentSpecError):
            _spec("NoDots")

    def test_rejects_single_segment_id(self):
        with pytest.raises(ComponentSpecError):
            _spec("summary")

    def test_rejects_self_dependency(self):
        with pytest.raises(ComponentSpecError):
            _spec("portfolio.summary", dependencies=("portfolio.summary",))

    def test_rejects_duplicate_dependencies(self):
        with pytest.raises(ComponentSpecError):
            _spec("portfolio.summary", dependencies=("portfolio.a", "portfolio.a"))

    def test_rejects_non_basemodel_output_model(self):
        with pytest.raises(ComponentSpecError):
            ComponentSpec(
                component_id="portfolio.summary",
                version=1,
                domains=frozenset({Domain.PORTFOLIO}),
                output_model=dict,  # type: ignore[arg-type]
                builder=lambda context, deps: {},
            )

    def test_rejects_empty_domains(self):
        with pytest.raises(ComponentSpecError):
            ComponentSpec(
                component_id="portfolio.summary",
                version=1,
                domains=frozenset(),
                output_model=_Payload,
                builder=lambda context, deps: _Payload(value=1),
            )

    def test_aggregated_period_behavior_requires_aggregator(self):
        with pytest.raises(ComponentSpecError):
            ComponentSpec(
                component_id="portfolio.prices",
                version=1,
                domains=frozenset({Domain.PORTFOLIO}),
                output_model=_Payload,
                builder=lambda context, deps: _Payload(value=1),
                period_behavior=PeriodBehavior.AGGREGATED,
            )

    def test_aggregator_requires_aggregated_period_behavior(self):
        with pytest.raises(ComponentSpecError):
            ComponentSpec(
                component_id="portfolio.prices",
                version=1,
                domains=frozenset({Domain.PORTFOLIO}),
                output_model=_Payload,
                builder=lambda context, deps: _Payload(value=1),
                period_behavior=PeriodBehavior.WINDOWED,
                aggregator=TemporalAggregatorSpec(kind="ohlc_bucket"),
            )

    def test_schema_id_defaults_to_component_id(self):
        spec = _spec("portfolio.summary")
        assert spec.schema_id == "portfolio.summary"

    def test_rejects_bool_version(self):
        # bool is a subclass of int in Python; version=True/False must never
        # silently satisfy the int version field.
        with pytest.raises(ComponentSpecError):
            ComponentSpec(
                component_id="portfolio.summary",
                version=True,  # type: ignore[arg-type]
                domains=frozenset({Domain.PORTFOLIO}),
                output_model=_Payload,
                builder=lambda context, deps: _Payload(value=1),
            )

    def test_rejects_non_int_version(self):
        with pytest.raises(ComponentSpecError):
            ComponentSpec(
                component_id="portfolio.summary",
                version="1",  # type: ignore[arg-type]
                domains=frozenset({Domain.PORTFOLIO}),
                output_model=_Payload,
                builder=lambda context, deps: _Payload(value=1),
            )

    def test_rejects_bool_schema_version(self):
        with pytest.raises(ComponentSpecError):
            ComponentSpec(
                component_id="portfolio.summary",
                version=1,
                domains=frozenset({Domain.PORTFOLIO}),
                output_model=_Payload,
                builder=lambda context, deps: _Payload(value=1),
                schema_version=True,  # type: ignore[arg-type]
            )

    def test_rejects_raw_string_domain_member(self):
        # Domain is a StrEnum, so "portfolio" == Domain.PORTFOLIO but is not an
        # instance of Domain - equality-based validation must not let this pass.
        with pytest.raises(ComponentSpecError):
            ComponentSpec(
                component_id="portfolio.summary",
                version=1,
                domains=frozenset({"portfolio"}),  # type: ignore[arg-type]
                output_model=_Payload,
                builder=lambda context, deps: _Payload(value=1),
            )

    def test_rejects_raw_string_period_behavior(self):
        with pytest.raises(ComponentSpecError):
            ComponentSpec(
                component_id="portfolio.summary",
                version=1,
                domains=frozenset({Domain.PORTFOLIO}),
                output_model=_Payload,
                builder=lambda context, deps: _Payload(value=1),
                period_behavior="windowed",  # type: ignore[arg-type]
            )

    def test_rejects_non_code_aggregator_kind(self):
        with pytest.raises((ComponentSpecError, ValueError)):
            TemporalAggregatorSpec(kind="Not A Stable Code!")


class TestComponentRegistry:
    def test_duplicate_component_id_raises(self):
        with pytest.raises(DuplicateComponentIdError):
            ComponentRegistry([_spec("portfolio.summary"), _spec("portfolio.summary")])

    def test_unknown_dependency_raises(self):
        with pytest.raises(UnknownComponentError):
            ComponentRegistry([_spec("portfolio.summary", dependencies=("portfolio.missing",))])

    def test_two_node_cycle_raises(self):
        with pytest.raises(ComponentDependencyCycleError):
            ComponentRegistry(
                [
                    _spec("portfolio.a", dependencies=("portfolio.b",)),
                    _spec("portfolio.b", dependencies=("portfolio.a",)),
                ]
            )

    def test_three_node_cycle_raises(self):
        with pytest.raises(ComponentDependencyCycleError):
            ComponentRegistry(
                [
                    _spec("portfolio.a", dependencies=("portfolio.b",)),
                    _spec("portfolio.b", dependencies=("portfolio.c",)),
                    _spec("portfolio.c", dependencies=("portfolio.a",)),
                ]
            )

    def test_acyclic_dependency_chain_registers_successfully(self):
        registry = ComponentRegistry(
            [
                _spec("portfolio.a"),
                _spec("portfolio.b", dependencies=("portfolio.a",)),
                _spec("portfolio.c", dependencies=("portfolio.b",)),
            ]
        )
        assert len(registry) == 3
        assert "portfolio.a" in registry
        assert registry.transitive_dependencies("portfolio.c") == ("portfolio.a", "portfolio.b")

    def test_canonical_order_preserves_registration_order(self):
        registry = ComponentRegistry([_spec("portfolio.c"), _spec("portfolio.a"), _spec("portfolio.b")])
        assert registry.canonical_order == ("portfolio.c", "portfolio.a", "portfolio.b")

    def test_get_unknown_component_raises(self):
        registry = ComponentRegistry([_spec("portfolio.a")])
        with pytest.raises(UnknownComponentError):
            registry.get("portfolio.missing")


class TestSectionEnvelope:
    def test_build_envelope_validates_mapping_payload(self):
        spec = _spec("portfolio.summary", builder=lambda context, deps: {"value": 5, "label": "x"})
        envelope = build_envelope(spec, {"value": 5, "label": "x"})
        assert envelope.component_id == "portfolio.summary"
        assert envelope.component_version == 1
        assert envelope.schema_id == "portfolio.summary"
        assert envelope.schema_version == 1
        assert envelope.payload == {"value": 5, "label": "x"}

    def test_build_envelope_accepts_model_instance(self):
        spec = _spec("portfolio.summary")
        envelope = build_envelope(spec, _Payload(value=7, label="y"))
        assert envelope.payload == {"value": 7, "label": "y"}

    def test_build_envelope_rejects_invalid_mapping(self):
        spec = _spec("portfolio.summary")
        with pytest.raises(ComponentPayloadValidationError):
            build_envelope(spec, {"value": "not-an-int"})

    def test_build_envelope_rejects_unsupported_type(self):
        spec = _spec("portfolio.summary")
        with pytest.raises(ComponentPayloadValidationError):
            build_envelope(spec, object())

    def test_envelope_is_frozen(self):
        spec = _spec("portfolio.summary")
        envelope = build_envelope(spec, _Payload(value=1))
        with pytest.raises(ValidationError):
            envelope.component_id = "portfolio.other"

    def test_envelope_payload_rejects_non_json_values(self):
        with pytest.raises(ValidationError):
            SectionEnvelope(component_id="portfolio.summary", component_version=1, schema_id="portfolio.summary", schema_version=1, payload={"bad": {1, 2, 3}})


class TestBuildContext:
    @pytest.mark.asyncio
    async def test_resolves_sync_builder(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        envelope = await context.resolve("portfolio.summary", required=True)
        assert envelope is not None
        assert envelope.payload["label"] == "portfolio.summary"

    @pytest.mark.asyncio
    async def test_resolves_async_builder(self):
        async def _async_builder(context, deps):
            await asyncio.sleep(0)
            return _Payload(value=2, label="async")

        registry = ComponentRegistry([_spec("portfolio.summary", builder=_async_builder)])
        context = BuildContext(registry, request_id="req-1")
        envelope = await context.resolve("portfolio.summary", required=True)
        assert envelope is not None
        assert envelope.payload == {"value": 2, "label": "async"}

    @pytest.mark.asyncio
    async def test_memoizes_component_build_at_most_once(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        first = await context.resolve("portfolio.summary", required=True)
        second = await context.resolve("portfolio.summary", required=True)
        assert first is second
        assert context.build_count("portfolio.summary") == 1

    @pytest.mark.asyncio
    async def test_memoizes_under_concurrent_resolution(self):
        calls = {"count": 0}

        async def _slow_builder(context, deps):
            calls["count"] += 1
            await asyncio.sleep(0.01)
            return _Payload(value=1)

        registry = ComponentRegistry([_spec("portfolio.summary", builder=_slow_builder)])
        context = BuildContext(registry, request_id="req-1")
        results = await asyncio.gather(*(context.resolve("portfolio.summary", required=True) for _ in range(5)))
        assert all(result is results[0] for result in results)
        assert calls["count"] == 1
        assert context.build_count("portfolio.summary") == 1

    @pytest.mark.asyncio
    async def test_dependency_is_built_once_when_shared_by_two_dependents(self):
        registry = ComponentRegistry(
            [
                _spec("portfolio.shared"),
                _spec("portfolio.a", dependencies=("portfolio.shared",)),
                _spec("portfolio.b", dependencies=("portfolio.shared",)),
            ]
        )
        context = BuildContext(registry, request_id="req-1")
        await context.resolve("portfolio.a", required=True)
        await context.resolve("portfolio.b", required=True)
        assert context.build_count("portfolio.shared") == 1

    @pytest.mark.asyncio
    async def test_required_component_failure_propagates(self):
        def _failing_builder(context, deps):
            raise RuntimeError("boom")

        registry = ComponentRegistry([_spec("portfolio.summary", builder=_failing_builder)])
        context = BuildContext(registry, request_id="req-1")
        with pytest.raises(RequiredComponentBuildError) as exc_info:
            await context.resolve("portfolio.summary", required=True)
        assert exc_info.value.component_id == "portfolio.summary"
        assert isinstance(exc_info.value.cause, RuntimeError)

    @pytest.mark.asyncio
    async def test_optional_component_failure_is_isolated(self):
        def _failing_builder(context, deps):
            raise RuntimeError("unavailable")

        registry = ComponentRegistry([_spec("portfolio.summary", builder=_failing_builder)])
        context = BuildContext(registry, request_id="req-1")
        envelope = await context.resolve("portfolio.summary", required=False)
        assert envelope is None
        assert len(context.diagnostics) == 1
        assert context.diagnostics[0].component_id == "portfolio.summary"

    @pytest.mark.asyncio
    async def test_required_component_returning_empty_payload_is_a_valid_success(self):
        # Binding semantics: emptiness is a property of the data, not the build
        # outcome. A required component whose builder returns normally - even with
        # an empty payload (e.g. no FX exposure) - must succeed, not be treated as
        # unavailable/failed.
        def _empty_builder(context, deps):
            return _ListPayload(items=[])

        registry = ComponentRegistry([ComponentSpec(component_id="fx.direct_exposure", version=1, domains=frozenset({Domain.FX}), output_model=_ListPayload, builder=_empty_builder)])
        context = BuildContext(registry, request_id="req-1")
        envelope = await context.resolve("fx.direct_exposure", required=True)
        assert envelope is not None
        assert envelope.payload == {"items": []}
        assert context.build_count("fx.direct_exposure") == 1
        assert context.diagnostics == []

    @pytest.mark.asyncio
    async def test_required_component_raising_is_a_failure_not_empty_success(self):
        # Contrast case for the test above: an exception - not an empty payload -
        # is the only thing that constitutes a build failure.
        def _raising_builder(context, deps):
            raise RuntimeError("provider unavailable")

        registry = ComponentRegistry([ComponentSpec(component_id="fx.direct_exposure", version=1, domains=frozenset({Domain.FX}), output_model=_ListPayload, builder=_raising_builder)])
        context = BuildContext(registry, request_id="req-1")
        with pytest.raises(RequiredComponentBuildError) as exc_info:
            await context.resolve("fx.direct_exposure", required=True)
        assert isinstance(exc_info.value.cause, RuntimeError)

    @pytest.mark.asyncio
    async def test_required_dependency_failure_cascades_to_dependent(self):
        def _failing_builder(context, deps):
            raise RuntimeError("boom")

        registry = ComponentRegistry(
            [
                _spec("portfolio.broken", builder=_failing_builder),
                _spec("portfolio.dependent", dependencies=("portfolio.broken",)),
            ]
        )
        context = BuildContext(registry, request_id="req-1")
        with pytest.raises(RequiredComponentBuildError):
            await context.resolve("portfolio.dependent", required=True)
        # the failing dependency itself was only attempted once
        assert context.build_count("portfolio.broken") == 1

    @pytest.mark.asyncio
    async def test_dependent_can_be_optional_even_if_dependency_is_required_internally(self):
        def _failing_builder(context, deps):
            raise RuntimeError("boom")

        registry = ComponentRegistry(
            [
                _spec("portfolio.broken", builder=_failing_builder),
                _spec("portfolio.dependent", dependencies=("portfolio.broken",)),
            ]
        )
        context = BuildContext(registry, request_id="req-1")
        envelope = await context.resolve("portfolio.dependent", required=False)
        assert envelope is None
        assert any(diag.component_id == "portfolio.dependent" for diag in context.diagnostics)

    @pytest.mark.asyncio
    async def test_same_failing_optional_component_resolved_twice_records_one_diagnostic(self):
        # Item 6 (architecture review round 2): the same cached failure resolved
        # as "optional" through more than one caller within a single request (e.g.
        # two datasets sharing a failing optional component) must record exactly
        # one deterministic ComponentDiagnostic, not one per resolve() call.
        calls = {"count": 0}

        def _failing_builder(context, deps):
            calls["count"] += 1
            raise RuntimeError("unavailable")

        registry = ComponentRegistry([_spec("portfolio.shared_optional", builder=_failing_builder)])
        context = BuildContext(registry, request_id="req-1")
        first = await context.resolve("portfolio.shared_optional", required=False)
        second = await context.resolve("portfolio.shared_optional", required=False)
        assert first is None
        assert second is None
        assert calls["count"] == 1
        assert len(context.diagnostics) == 1
        assert context.diagnostics[0].component_id == "portfolio.shared_optional"


# =============================================================================
# BuildScope (workstream D2)
# =============================================================================


def _scope(**overrides) -> BuildScope:
    defaults = {
        "request_id": "req-1",
        "user_id": 1,
        "domain": Domain.PORTFOLIO,
        "detail_level": DetailLevel.STANDARD,
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 3, 31),
        "target_currency": "usd",
        "broker_scope": (),
    }
    defaults.update(overrides)
    return BuildScope(**defaults)


class TestBuildScope:
    def test_builds_portfolio_scope_with_empty_broker_scope(self):
        scope = _scope()
        assert scope.domain is Domain.PORTFOLIO
        assert scope.broker_scope == ()
        assert scope.asset_id is None
        assert scope.snapshot_as_of == scope.period_end

    def test_normalizes_target_currency_to_canonical_uppercase(self):
        scope = _scope(target_currency="  eur ")
        assert scope.target_currency == "EUR"

    def test_rejects_non_iso_like_currency(self):
        with pytest.raises(BuildScopeError):
            _scope(target_currency="US")

    def test_rejects_non_string_currency(self):
        with pytest.raises(BuildScopeError):
            _scope(target_currency=123)  # type: ignore[arg-type]

    def test_normalizes_broker_scope_sorted_and_deduplicated(self):
        scope = _scope(broker_scope=(3, 1, 2, 1, 3))
        assert scope.broker_scope == (1, 2, 3)

    def test_rejects_non_positive_broker_scope_entry(self):
        with pytest.raises(BuildScopeError):
            _scope(broker_scope=(1, 0))

    def test_rejects_bool_broker_scope_entry(self):
        with pytest.raises(BuildScopeError):
            _scope(broker_scope=(True,))

    def test_rejects_non_positive_user_id(self):
        with pytest.raises(BuildScopeError):
            _scope(user_id=0)

    def test_rejects_bool_user_id(self):
        with pytest.raises(BuildScopeError):
            _scope(user_id=True)  # type: ignore[arg-type]

    def test_rejects_blank_request_id(self):
        with pytest.raises(BuildScopeError):
            _scope(request_id="  ")

    def test_rejects_non_domain_member(self):
        with pytest.raises(BuildScopeError):
            _scope(domain="portfolio")  # type: ignore[arg-type]

    def test_rejects_non_detail_level_member(self):
        with pytest.raises(BuildScopeError):
            _scope(detail_level="standard")  # type: ignore[arg-type]

    def test_rejects_period_start_after_period_end(self):
        with pytest.raises(BuildScopeError):
            _scope(period_start=date(2026, 3, 31), period_end=date(2026, 1, 1))

    def test_rejects_datetime_instead_of_date(self):
        with pytest.raises(BuildScopeError):
            _scope(period_start=datetime(2026, 1, 1))  # type: ignore[arg-type]

    def test_portfolio_scope_rejects_entity_target(self):
        with pytest.raises(BuildScopeError):
            _scope(domain=Domain.PORTFOLIO, asset_id=1)

    def test_broker_scope_requires_broker_id(self):
        with pytest.raises(BuildScopeError):
            _scope(domain=Domain.BROKER)

    def test_broker_scope_builds_with_matching_broker_scope_tuple(self):
        scope = _scope(domain=Domain.BROKER, broker_id=7, broker_scope=(7,))
        assert scope.broker_id == 7
        assert scope.broker_scope == (7,)

    def test_broker_scope_rejects_mismatched_broker_scope_tuple(self):
        with pytest.raises(BuildScopeError):
            _scope(domain=Domain.BROKER, broker_id=7, broker_scope=(7, 8))

    def test_broker_scope_rejects_empty_broker_scope(self):
        with pytest.raises(BuildScopeError):
            _scope(domain=Domain.BROKER, broker_id=7, broker_scope=())

    def test_broker_scope_rejects_asset_id(self):
        with pytest.raises(BuildScopeError):
            _scope(domain=Domain.BROKER, broker_id=7, broker_scope=(7,), asset_id=1)

    def test_asset_scope_requires_asset_id(self):
        with pytest.raises(BuildScopeError):
            _scope(domain=Domain.ASSET)

    def test_asset_scope_builds_with_positive_asset_id_and_arbitrary_broker_scope(self):
        scope = _scope(domain=Domain.ASSET, asset_id=42, broker_scope=(1, 5))
        assert scope.asset_id == 42
        assert scope.broker_scope == (1, 5)

    def test_asset_scope_rejects_non_positive_asset_id(self):
        with pytest.raises(BuildScopeError):
            _scope(domain=Domain.ASSET, asset_id=0)

    def test_asset_scope_rejects_broker_id(self):
        with pytest.raises(BuildScopeError):
            _scope(domain=Domain.ASSET, asset_id=1, broker_id=1)

    def test_fx_scope_requires_base_and_quote_currency(self):
        with pytest.raises(BuildScopeError):
            _scope(domain=Domain.FX, base_currency="USD")

    def test_fx_scope_builds_with_distinct_currencies(self):
        scope = _scope(domain=Domain.FX, base_currency="usd", quote_currency="eur")
        assert scope.base_currency == "USD"
        assert scope.quote_currency == "EUR"

    def test_fx_scope_rejects_identical_base_and_quote_currency(self):
        with pytest.raises(BuildScopeError):
            _scope(domain=Domain.FX, base_currency="USD", quote_currency="usd")

    def test_fx_scope_rejects_asset_or_broker_target(self):
        with pytest.raises(BuildScopeError):
            _scope(domain=Domain.FX, base_currency="USD", quote_currency="EUR", asset_id=1)

    def test_build_scope_is_immutable(self):
        scope = _scope()
        with pytest.raises(AttributeError):
            scope.target_currency = "EUR"  # type: ignore[misc]


# =============================================================================
# DetailLevel <-> BucketDetailLevel mapping (workstream D2, point 2)
# =============================================================================


class TestDetailLevelMapping:
    @pytest.mark.parametrize(
        ("detail_level", "expected"),
        [
            (DetailLevel.COMPACT, BucketDetailLevel.COMPACT),
            (DetailLevel.STANDARD, BucketDetailLevel.STANDARD),
            (DetailLevel.FULL, BucketDetailLevel.FULL),
        ],
    )
    def test_maps_every_detail_level_member(self, detail_level, expected):
        assert map_detail_level_to_bucket_detail_level(detail_level) is expected

    def test_mapping_is_exhaustive_over_detail_level(self):
        # Guards the "total mapping" requirement: every current DetailLevel member
        # must resolve without error, independent of the parametrized cases above.
        for level in DetailLevel:
            assert isinstance(map_detail_level_to_bucket_detail_level(level), BucketDetailLevel)

    def test_rejects_non_detail_level_input(self):
        with pytest.raises(TypeError):
            map_detail_level_to_bucket_detail_level("standard")  # type: ignore[arg-type]

    def test_build_bucket_plan_for_scope_matches_scope_period_and_policy(self):
        scope = _scope(detail_level=DetailLevel.FULL, period_start=date(2026, 1, 1), period_end=date(2026, 3, 31))
        plan = build_bucket_plan_for_scope(scope)
        assert plan.start == scope.period_start
        assert plan.end == scope.period_end
        assert plan.policy == BucketingPolicy.for_detail_level(BucketDetailLevel.FULL)


# =============================================================================
# BuildContext BuildScope/BucketPlan/AsyncSession wiring (workstream D2)
# =============================================================================


class TestBuildContextScopeWiring:
    def test_plain_registry_only_context_still_works_without_scope(self):
        # Backward compatibility: every pre-D2 call site constructs BuildContext
        # with only registry/request_id; scope/bucket_plan/session must stay optional.
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        assert context.scope is None
        assert context.bucket_plan is None
        assert context.session is None

    def test_accepts_matching_scope_and_bucket_plan(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        scope = _scope()
        plan = build_bucket_plan_for_scope(scope)
        context = BuildContext(registry, request_id="req-1", scope=scope, bucket_plan=plan)
        assert context.scope is scope
        assert context.bucket_plan is plan

    def test_rejects_scope_without_bucket_plan(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        scope = _scope()
        with pytest.raises(BuildContextScopeError):
            BuildContext(registry, request_id="req-1", scope=scope)

    def test_rejects_bucket_plan_without_scope(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        scope = _scope()
        plan = build_bucket_plan_for_scope(scope)
        with pytest.raises(BuildContextScopeError):
            BuildContext(registry, request_id="req-1", bucket_plan=plan)

    def test_rejects_bucket_plan_with_mismatched_period(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        scope = _scope(period_start=date(2026, 1, 1), period_end=date(2026, 3, 31))
        other_scope = _scope(period_start=date(2026, 1, 2), period_end=date(2026, 3, 31))
        mismatched_plan = build_bucket_plan_for_scope(other_scope)
        with pytest.raises(BuildContextScopeError):
            BuildContext(registry, request_id="req-1", scope=scope, bucket_plan=mismatched_plan)

    def test_rejects_bucket_plan_with_mismatched_policy(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        scope = _scope(detail_level=DetailLevel.STANDARD)
        wrong_policy_plan = BucketPlan.build(scope.period_start, scope.period_end, BucketingPolicy.for_detail_level(BucketDetailLevel.FULL))
        with pytest.raises(BuildContextScopeError):
            BuildContext(registry, request_id="req-1", scope=scope, bucket_plan=wrong_policy_plan)

    def test_rejects_wrong_type_scope(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        with pytest.raises(TypeError):
            BuildContext(registry, request_id="req-1", scope=object(), bucket_plan=build_bucket_plan_for_scope(_scope()))  # type: ignore[arg-type]

    def test_rejects_wrong_type_session(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        with pytest.raises(TypeError):
            BuildContext(registry, request_id="req-1", session=object())  # type: ignore[arg-type]


# =============================================================================
# Typed request-scoped raw resource cache (workstream D2, point 4)
# =============================================================================


class _PortfolioReport:
    """Stand-in domain object: identity must be preserved, never JSON round-tripped."""

    def __init__(self, total: Decimal):
        self.total = total


class TestResourceCache:
    @pytest.mark.asyncio
    async def test_resolves_sync_loader(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        key = ResourceKey("value", int)
        result = await context.resource(key, lambda: 42)
        assert result == 42

    @pytest.mark.asyncio
    async def test_resolves_async_loader(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        key = ResourceKey("value", int)

        async def _loader():
            await asyncio.sleep(0)
            return 7

        result = await context.resource(key, _loader)
        assert result == 7

    @pytest.mark.asyncio
    async def test_memoizes_at_most_once_per_key(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        key = ResourceKey("value", int)
        calls = {"count": 0}

        def _loader():
            calls["count"] += 1
            return 1

        first = await context.resource(key, _loader)
        second = await context.resource(key, _loader)
        assert first == second == 1
        assert calls["count"] == 1

    @pytest.mark.asyncio
    async def test_memoizes_under_concurrent_resolution(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        key = ResourceKey("value", int)
        calls = {"count": 0}

        async def _loader():
            calls["count"] += 1
            await asyncio.sleep(0.01)
            return 99

        results = await asyncio.gather(*(context.resource(key, _loader) for _ in range(5)))
        assert results == [99] * 5
        assert calls["count"] == 1

    @pytest.mark.asyncio
    async def test_raw_object_identity_preserved_not_json_round_tripped(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")

        report = _PortfolioReport(total=Decimal("123.456789"))
        report_key = ResourceKey("portfolio_report", _PortfolioReport)
        resolved_report = await context.resource(report_key, lambda: report)
        assert resolved_report is report
        assert resolved_report.total is report.total

        today = date(2026, 3, 31)
        date_key = ResourceKey("as_of_date", date)
        resolved_date = await context.resource(date_key, lambda: today)
        assert resolved_date is today

        amount_key = ResourceKey("amount", Decimal)
        amount = Decimal("42.5")
        resolved_amount = await context.resource(amount_key, lambda: amount)
        assert resolved_amount is amount

    @pytest.mark.asyncio
    async def test_type_mismatch_raises_wrapped_resource_load_error(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        key = ResourceKey("value", int)
        with pytest.raises(ResourceLoadError) as exc_info:
            await context.resource(key, lambda: "not-an-int")
        assert isinstance(exc_info.value.cause, TypeError)

    @pytest.mark.asyncio
    async def test_loader_exception_raises_wrapped_resource_load_error_preserving_cause(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        key = ResourceKey("value", int)

        def _failing():
            raise RuntimeError("boom")

        with pytest.raises(ResourceLoadError) as exc_info:
            await context.resource(key, _failing)
        assert isinstance(exc_info.value.cause, RuntimeError)
        assert str(exc_info.value.cause) == "boom"

    @pytest.mark.asyncio
    async def test_cached_error_is_deterministic_across_repeated_callers(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        key = ResourceKey("value", int)
        calls = {"count": 0}

        def _failing():
            calls["count"] += 1
            raise RuntimeError("boom")

        with pytest.raises(ResourceLoadError) as first_exc:
            await context.resource(key, _failing)
        with pytest.raises(ResourceLoadError) as second_exc:
            await context.resource(key, _failing)
        assert calls["count"] == 1
        assert first_exc.value is second_exc.value
        assert first_exc.value.cause is second_exc.value.cause

    @pytest.mark.asyncio
    async def test_resource_error_is_caught_by_component_optional_semantics(self):
        # Requirement: a resource loader error raised from within a component
        # builder must be caught by the existing required/optional isolation in
        # BuildContext._build/resolve, exactly like any other builder exception.
        key = ResourceKey("value", int)

        def _failing():
            raise RuntimeError("resource unavailable")

        async def _builder(context, deps):
            value = await context.resource(key, _failing)
            return _Payload(value=value)

        registry = ComponentRegistry([_spec("portfolio.summary", builder=_builder)])
        context = BuildContext(registry, request_id="req-1")
        envelope = await context.resolve("portfolio.summary", required=False)
        assert envelope is None
        assert len(context.diagnostics) == 1

        with pytest.raises(RequiredComponentBuildError) as exc_info:
            context2 = BuildContext(registry, request_id="req-2")
            await context2.resolve("portfolio.summary", required=True)
        assert isinstance(exc_info.value.cause, ResourceLoadError)

    @pytest.mark.asyncio
    async def test_cancellation_is_not_cached_as_a_resource_error(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        key = ResourceKey("value", int)
        started = asyncio.Event()

        async def _slow_loader():
            started.set()
            await asyncio.sleep(10)
            return 1

        task = asyncio.ensure_future(context.resource(key, _slow_loader))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # A later, non-cancelled attempt for the same key must retry cleanly,
        # rather than raise a memoized/cached cancellation-derived error.
        result = await context.resource(key, lambda: 55)
        assert result == 55

    @pytest.mark.asyncio
    async def test_conflicting_expected_type_for_same_key_name_is_rejected(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        await context.resource(ResourceKey("value", int), lambda: 1)
        with pytest.raises(ResourceKeyConflictError):
            await context.resource(ResourceKey("value", str), lambda: "x")

    @pytest.mark.asyncio
    async def test_conflicting_loader_mode_for_same_key_name_is_rejected(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1", session=_make_async_session())
        await context.resource(ResourceKey("value", int), lambda: 1)
        with pytest.raises(ResourceKeyConflictError):
            await context.db_resource(ResourceKey("value", int), lambda session: 2)
        await context.session.close()

    @pytest.mark.asyncio
    async def test_recursive_same_key_resolution_fails_explicitly_instead_of_deadlocking(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        key = ResourceKey("value", int)

        async def _recursive_loader():
            return await context.resource(key, _recursive_loader)

        # The recursive re-entry raises ResourceRecursionError from inside the
        # outer loader invocation, which - like any other loader failure - is
        # wrapped deterministically as ResourceLoadError(cause=...); the
        # important guarantee under test is that this resolves promptly
        # (explicit failure) rather than hanging on the non-reentrant per-key
        # lock.
        with pytest.raises(ResourceLoadError) as exc_info:
            await asyncio.wait_for(context.resource(key, _recursive_loader), timeout=5)
        assert isinstance(exc_info.value.cause, ResourceRecursionError)


# =============================================================================
# DB-backed resource cache: AsyncSession boundary + serialization (workstream D2)
# =============================================================================


def _make_async_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    return AsyncSession(engine)


class TestDbResourceCache:
    @pytest.mark.asyncio
    async def test_db_resource_requires_a_session(self):
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1")
        with pytest.raises(BuildContextScopeError):
            await context.db_resource(ResourceKey("value", int), lambda session: 1)

    @pytest.mark.asyncio
    async def test_db_resource_receives_the_context_session_and_supports_sync_and_async_loaders(self):
        session = _make_async_session()
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1", session=session)

        def _sync_loader(loader_session):
            assert loader_session is session
            return 3

        result = await context.db_resource(ResourceKey("sync_value", int), _sync_loader)
        assert result == 3

        async def _async_loader(loader_session):
            assert loader_session is session
            await asyncio.sleep(0)
            return 4

        result = await context.db_resource(ResourceKey("async_value", int), _async_loader)
        assert result == 4
        await session.close()

    @pytest.mark.asyncio
    async def test_db_resource_memoizes_at_most_once_per_key(self):
        session = _make_async_session()
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1", session=session)
        calls = {"count": 0}

        def _loader(loader_session):
            calls["count"] += 1
            return 1

        key = ResourceKey("value", int)
        first = await context.db_resource(key, _loader)
        second = await context.db_resource(key, _loader)
        assert first == second == 1
        assert calls["count"] == 1
        await session.close()

    @pytest.mark.asyncio
    async def test_db_resource_serializes_across_keys_max_concurrency_is_one(self):
        # Proves the request-scoped DB lock invariant: even though these two
        # loaders target *different* keys (so their per-key memoization locks
        # don't contend), db_resource must still serialize them - the shared
        # AsyncSession must never be used concurrently.
        session = _make_async_session()
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1", session=session)

        concurrent = {"current": 0, "max": 0}

        async def _make_loader(value):
            async def _loader(loader_session):
                concurrent["current"] += 1
                concurrent["max"] = max(concurrent["max"], concurrent["current"])
                await asyncio.sleep(0.02)
                concurrent["current"] -= 1
                return value

            return _loader

        loader_a = await _make_loader(1)
        loader_b = await _make_loader(2)
        loader_c = await _make_loader(3)

        results = await asyncio.gather(
            context.db_resource(ResourceKey("key_a", int), loader_a),
            context.db_resource(ResourceKey("key_b", int), loader_b),
            context.db_resource(ResourceKey("key_c", int), loader_c),
        )
        assert sorted(results) == [1, 2, 3]
        assert concurrent["max"] == 1
        await session.close()

    @pytest.mark.asyncio
    async def test_db_resource_error_is_memoized_and_deterministic(self):
        session = _make_async_session()
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1", session=session)
        key = ResourceKey("value", int)
        calls = {"count": 0}

        def _failing(loader_session):
            calls["count"] += 1
            raise RuntimeError("db unavailable")

        with pytest.raises(ResourceLoadError) as first_exc:
            await context.db_resource(key, _failing)
        with pytest.raises(ResourceLoadError) as second_exc:
            await context.db_resource(key, _failing)
        assert calls["count"] == 1
        assert first_exc.value is second_exc.value
        await session.close()

    def _assert_db_lock_pristine(self, context: BuildContext) -> None:
        """Asserts the reentrant DB-lock bookkeeping is back to its baseline state.

        Used after every test below that exercises nested/cross-task
        `db_resource` calls, to prove no owner/depth is ever leaked -
        regardless of whether the exercised scenario succeeded, raised, or
        was cancelled.
        """
        assert context._db_lock_owner is None
        assert context._db_lock_depth == 0
        assert not context._db_lock.locked()

    @pytest.mark.asyncio
    async def test_nested_cross_key_db_resource_from_same_task_succeeds(self):
        # A loader resolving key_a itself calls db_resource for a *different*
        # key (key_b) from within the same task/coroutine stack. This must
        # not deadlock on the non-reentrant asyncio.Lock backing db_resource
        # serialization - the outer call already holds it.
        session = _make_async_session()
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1", session=session)
        key_a = ResourceKey("key_a", int)
        key_b = ResourceKey("key_b", int)

        async def _loader_b(loader_session):
            return 2

        async def _loader_a(loader_session):
            nested = await context.db_resource(key_b, _loader_b)
            return 1 + nested

        result = await asyncio.wait_for(context.db_resource(key_a, _loader_a), timeout=5)
        assert result == 3
        assert await context.db_resource(key_b, _loader_b) == 2
        self._assert_db_lock_pristine(context)
        await session.close()

    @pytest.mark.asyncio
    async def test_nested_cross_key_db_resource_two_levels_deep_succeeds(self):
        # Same as above but three keys deep (key_a -> key_b -> key_c), proving
        # the reentrancy depth tracking (not just a single extra level) works.
        session = _make_async_session()
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1", session=session)
        key_a = ResourceKey("key_a", int)
        key_b = ResourceKey("key_b", int)
        key_c = ResourceKey("key_c", int)

        def _loader_c(loader_session):
            return 3

        async def _loader_b(loader_session):
            return 10 + await context.db_resource(key_c, _loader_c)

        async def _loader_a(loader_session):
            return 100 + await context.db_resource(key_b, _loader_b)

        result = await asyncio.wait_for(context.db_resource(key_a, _loader_a), timeout=5)
        assert result == 113
        self._assert_db_lock_pristine(context)
        await session.close()

    @pytest.mark.asyncio
    async def test_concurrent_outsider_task_blocks_until_owner_task_exits(self):
        # A second, unrelated task requesting a db_resource while the first
        # task is mid-nesting (holds db_lock via key_a, currently resolving
        # nested key_b) must block on the real lock until the *outermost*
        # frame of the owning task fully exits - proving nested reentrancy
        # from the owner never weakens cross-task serialization.
        session = _make_async_session()
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1", session=session)
        key_a = ResourceKey("key_a", int)
        key_b = ResourceKey("key_b", int)
        key_c = ResourceKey("key_c", int)

        owner_in_nested_section = asyncio.Event()
        events: list[str] = []

        async def _loader_b(loader_session):
            events.append("owner_nested_start")
            owner_in_nested_section.set()
            # Give the outsider task a chance to attempt (and block on) the lock.
            await asyncio.sleep(0.05)
            events.append("owner_nested_end")
            return 2

        async def _loader_a(loader_session):
            events.append("owner_outer_start")
            nested = await context.db_resource(key_b, _loader_b)
            events.append("owner_outer_end")
            return 1 + nested

        async def _outsider_loader(loader_session):
            events.append("outsider_start")
            return 99

        owner_task = asyncio.ensure_future(context.db_resource(key_a, _loader_a))
        await owner_in_nested_section.wait()

        outsider_task = asyncio.ensure_future(context.db_resource(key_c, _outsider_loader))
        # The outsider must not be able to start its loader (i.e. acquire the
        # lock) while the owner task still holds it, even though the owner is
        # deep in a nested call for a completely different key.
        await asyncio.sleep(0.02)
        assert "outsider_start" not in events

        owner_result, outsider_result = await asyncio.wait_for(asyncio.gather(owner_task, outsider_task), timeout=5)
        assert owner_result == 3
        assert outsider_result == 99
        assert events.index("owner_outer_end") < events.index("outsider_start")
        self._assert_db_lock_pristine(context)
        await session.close()

    @pytest.mark.asyncio
    async def test_nested_loader_exception_releases_db_lock_and_owner(self):
        # A nested (cross-key) loader raising must not leak db_lock ownership
        # or leave depth non-zero - the outer frame's `finally` must still run.
        session = _make_async_session()
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1", session=session)
        key_a = ResourceKey("key_a", int)
        key_b = ResourceKey("key_b", int)
        key_c = ResourceKey("key_c", int)

        def _failing_nested_loader(loader_session):
            raise RuntimeError("nested db failure")

        async def _outer_loader(loader_session):
            return await context.db_resource(key_b, _failing_nested_loader)

        with pytest.raises(ResourceLoadError) as exc_info:
            await asyncio.wait_for(context.db_resource(key_a, _outer_loader), timeout=5)
        assert isinstance(exc_info.value.cause, ResourceLoadError)
        assert isinstance(exc_info.value.cause.cause, RuntimeError)
        self._assert_db_lock_pristine(context)

        # A subsequent, unrelated db_resource call must work normally - proving
        # the lock/owner bookkeeping was fully restored, not left corrupted.
        result = await asyncio.wait_for(context.db_resource(key_c, lambda loader_session: 7), timeout=5)
        assert result == 7
        self._assert_db_lock_pristine(context)
        await session.close()

    @pytest.mark.asyncio
    async def test_nested_loader_cancellation_releases_db_lock_and_owner(self):
        # Cancelling the task while it is inside a *nested* db_resource call
        # must still release the outer frame's lock/ownership cleanly (via
        # the `_db_serialized` finally blocks unwinding), leaving the context
        # usable for a later, non-cancelled attempt.
        session = _make_async_session()
        registry = ComponentRegistry([_spec("portfolio.summary")])
        context = BuildContext(registry, request_id="req-1", session=session)
        key_a = ResourceKey("key_a", int)
        key_b = ResourceKey("key_b", int)
        key_c = ResourceKey("key_c", int)
        nested_started = asyncio.Event()

        async def _slow_nested_loader(loader_session):
            nested_started.set()
            await asyncio.sleep(10)
            return 2

        async def _outer_loader(loader_session):
            return await context.db_resource(key_b, _slow_nested_loader)

        task = asyncio.ensure_future(context.db_resource(key_a, _outer_loader))
        await nested_started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        self._assert_db_lock_pristine(context)

        result = await asyncio.wait_for(context.db_resource(key_c, lambda loader_session: 42), timeout=5)
        assert result == 42
        self._assert_db_lock_pristine(context)
        await session.close()


class TestDomainResourceContracts:
    def test_price_results_are_indexed_and_reject_duplicate_asset_ids(self):
        first = FAPriceQueryResult(asset_id=1)
        second = FAPriceQueryResult(asset_id=2)

        resource = PriceResultsResource.from_results((first, second))

        assert resource.results == (first, second)
        assert resource.by_asset_id == {1: first, 2: second}
        with pytest.raises(ValueError, match="unique asset IDs"):
            PriceResultsResource.from_results((first, first.model_copy()))

    def test_lots_results_validate_mapping_identity(self):
        response = LotsAnalysisResponse.model_construct(asset_id=7)

        resource = LotsResultsResource.from_mapping({7: response})

        assert resource.by_asset_id[7] is response
        with pytest.raises(ValueError, match="must match response.asset_id"):
            LotsResultsResource.from_mapping({8: response})

    def test_fx_rate_series_preserves_decimal_provenance_and_order(self):
        first = FxRateObservation(
            requested_date=date(2026, 1, 1),
            actual_date=date(2025, 12, 31),
            rate=Decimal("1.123456"),
            backward_filled=True,
        )
        second = FxRateObservation(
            requested_date=date(2026, 1, 2),
            actual_date=date(2026, 1, 2),
            rate=Decimal("1.125"),
            backward_filled=False,
        )

        resource = FxRateSeriesResource.from_observations((first, second))

        assert resource.observations == (first, second)
        assert resource.observations[0].rate == Decimal("1.123456")
        with pytest.raises(ValueError, match="strictly increasing"):
            FxRateSeriesResource.from_observations((second, first))
