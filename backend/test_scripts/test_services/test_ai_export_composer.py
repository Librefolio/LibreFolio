"""Focused tests for the AI Export composer (workstream D).

Covers dataset/analysis composition ordering, cross-dataset component
deduplication, required-failure fail-closed propagation, optional-failure
isolation, detail-level enforcement, dataset/analysis version-mismatch fail
closed, memoization end-to-end through the composer, and end-to-end payload
JSON-safety.
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, ConfigDict

from backend.app.services.ai_export.analyses.catalog import build_analysis_registry
from backend.app.services.ai_export.analyses.spec import AnalysisSpec
from backend.app.services.ai_export.components.catalog import (
    ALL_FOUNDATION_COMPONENTS,
    ComponentNotImplementedError,
    FoundationComponentPayload,
    build_component_registry,
)
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import ALL_DETAIL_LEVELS, DetailLevel, Domain, PeriodBehavior
from backend.app.services.ai_export.composer import (
    AnalysisVersionMismatchError,
    Composer,
    DatasetVersionMismatchError,
    UnsupportedDetailLevelError,
)
from backend.app.services.ai_export.datasets.catalog import build_dataset_registry
from backend.app.services.ai_export.datasets.spec import DatasetRegistry, DatasetSpec, build_all_data_dataset
from backend.app.services.ai_export.dependencies import BuildContext, RequiredComponentBuildError


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int


class _ListPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[int]


def _component(component_id: str, *, dependencies: tuple[str, ...] = (), builder=None, domain: Domain = Domain.PORTFOLIO, output_model: type[BaseModel] = _Payload) -> ComponentSpec:
    def _default_builder(context, deps):
        return output_model(value=1) if output_model is _Payload else output_model()

    return ComponentSpec(
        component_id=component_id,
        version=1,
        domains=frozenset({domain}),
        output_model=output_model,
        builder=builder or _default_builder,
        dependencies=dependencies,
    )


def _dataset(dataset_id: str, *, required: tuple[str, ...], optional: tuple[str, ...] = (), domain: Domain = Domain.PORTFOLIO, detail_levels: frozenset[DetailLevel] = ALL_DETAIL_LEVELS) -> DatasetSpec:
    return DatasetSpec(
        dataset_id=dataset_id,
        version=1,
        domain=domain,
        display_i18n_key="k.display",
        description_i18n_key="k.description",
        icon="icon",
        applicability_code="test.always_applicable",
        applicable_pages=("dashboard",),
        required_component_ids=required,
        optional_component_ids=optional,
        section_order=(*required, *optional),
        technical_requirements=(),
        period_semantics=PeriodBehavior.AS_OF,
        supported_detail_levels=detail_levels,
    )


def _analysis(analysis_id: str, *, required: tuple[str, ...], optional: tuple[str, ...] = (), domain: Domain = Domain.PORTFOLIO, version: int = 1) -> AnalysisSpec:
    return AnalysisSpec(
        analysis_id=analysis_id,
        version=version,
        domain=domain,
        display_i18n_key="test.analysis.display",
        description_i18n_key="test.analysis.description",
        icon="icon",
        applicability_code="test.always_applicable",
        applicable_pages=("dashboard",),
        required_dataset_ids=required,
        optional_dataset_ids=optional,
        instruction_template_id="t",
        instruction_template_version=1,
        response_contract_id="r",
        response_contract_version=1,
    )


class TestComposeDataset:
    @pytest.mark.asyncio
    async def test_sections_follow_declared_section_order(self):
        registry = ComponentRegistry([_component("portfolio.a"), _component("portfolio.b"), _component("portfolio.c")])
        dataset = _dataset("portfolio.ds", required=("portfolio.b", "portfolio.a"), optional=("portfolio.c",))
        context = BuildContext(registry, request_id="req-1")
        composition = await Composer().compose_dataset(dataset, context, detail_level=DetailLevel.STANDARD)
        assert [section.component_id for section in composition.sections] == ["portfolio.b", "portfolio.a", "portfolio.c"]

    @pytest.mark.asyncio
    async def test_required_component_returning_empty_payload_stays_included_as_success(self):
        # Binding semantics: a required component with genuinely empty (but
        # successfully built) data - e.g. fx.direct_exposure with no foreign
        # currency positions - is a valid success and remains a section; it is
        # not "not-applicable" at this layer (that decision belongs to a future,
        # higher-level applicability check, not the composer).
        def _empty(context, deps):
            return _ListPayload(items=[])

        registry = ComponentRegistry([_component("fx.direct_exposure", builder=_empty, domain=Domain.FX, output_model=_ListPayload)])
        dataset = _dataset("fx.ds", required=("fx.direct_exposure",), domain=Domain.FX)
        context = BuildContext(registry, request_id="req-1")
        composition = await Composer().compose_dataset(dataset, context, detail_level=DetailLevel.STANDARD)
        assert [section.component_id for section in composition.sections] == ["fx.direct_exposure"]
        assert composition.sections[0].payload == {"items": []}
        assert context.diagnostics == []

    @pytest.mark.asyncio
    async def test_optional_component_failure_is_omitted_not_fatal(self):
        def _failing(context, deps):
            raise RuntimeError("no data")

        registry = ComponentRegistry([_component("portfolio.a"), _component("portfolio.opt", builder=_failing)])
        dataset = _dataset("portfolio.ds", required=("portfolio.a",), optional=("portfolio.opt",))
        context = BuildContext(registry, request_id="req-1")
        composition = await Composer().compose_dataset(dataset, context, detail_level=DetailLevel.STANDARD)
        assert [section.component_id for section in composition.sections] == ["portfolio.a"]
        assert any(diag.component_id == "portfolio.opt" for diag in context.diagnostics)

    @pytest.mark.asyncio
    async def test_required_component_failure_propagates(self):
        def _failing(context, deps):
            raise RuntimeError("no data")

        registry = ComponentRegistry([_component("portfolio.a", builder=_failing)])
        dataset = _dataset("portfolio.ds", required=("portfolio.a",))
        context = BuildContext(registry, request_id="req-1")
        with pytest.raises(RequiredComponentBuildError):
            await Composer().compose_dataset(dataset, context, detail_level=DetailLevel.STANDARD)

    @pytest.mark.asyncio
    async def test_unsupported_detail_level_raises(self):
        registry = ComponentRegistry([_component("portfolio.a")])
        dataset = _dataset("portfolio.ds", required=("portfolio.a",), detail_levels=frozenset({DetailLevel.FULL}))
        context = BuildContext(registry, request_id="req-1")
        with pytest.raises(UnsupportedDetailLevelError):
            await Composer().compose_dataset(dataset, context, detail_level=DetailLevel.COMPACT)

    @pytest.mark.asyncio
    async def test_dataset_version_mismatch_raises(self):
        registry = ComponentRegistry([_component("portfolio.a")])
        dataset = _dataset("portfolio.ds", required=("portfolio.a",))
        context = BuildContext(registry, request_id="req-1")
        with pytest.raises(DatasetVersionMismatchError):
            await Composer().compose_dataset(dataset, context, detail_level=DetailLevel.STANDARD, expected_version=2)

    @pytest.mark.asyncio
    async def test_payload_is_json_safe(self):
        registry = ComponentRegistry([_component("portfolio.a")])
        dataset = _dataset("portfolio.ds", required=("portfolio.a",))
        context = BuildContext(registry, request_id="req-1")
        composition = await Composer().compose_dataset(dataset, context, detail_level=DetailLevel.STANDARD)
        section = composition.sections[0]
        assert section.payload == {"value": 1}
        # round-trips through stdlib json without a custom encoder: proves JSON safety
        assert json.loads(json.dumps(section.payload)) == section.payload


class TestComposeAnalysis:
    @pytest.mark.asyncio
    async def test_required_datasets_are_always_included(self):
        registry = ComponentRegistry([_component("portfolio.a"), _component("portfolio.b")])
        dataset_a = _dataset("portfolio.a_ds", required=("portfolio.a",))
        dataset_b = _dataset("portfolio.b_ds", required=("portfolio.b",))
        dataset_registry = DatasetRegistry([dataset_a, dataset_b], component_registry=registry)
        analysis = _analysis("portfolio.combo", required=("portfolio.a_ds", "portfolio.b_ds"), optional=())
        context = BuildContext(registry, request_id="req-1")
        composition = await Composer().compose_analysis(analysis, dataset_registry, context, detail_level=DetailLevel.STANDARD)
        assert composition.dataset_ids == ("portfolio.a_ds", "portfolio.b_ds")
        assert {section.component_id for section in composition.sections} == {"portfolio.a", "portfolio.b"}

    @pytest.mark.asyncio
    async def test_required_dataset_failure_propagates_fail_closed(self):
        def _failing(context, deps):
            raise RuntimeError("no data")

        registry = ComponentRegistry([_component("portfolio.a", builder=_failing)])
        dataset_a = _dataset("portfolio.a_ds", required=("portfolio.a",))
        dataset_registry = DatasetRegistry([dataset_a], component_registry=registry)
        analysis = _analysis("portfolio.combo", required=("portfolio.a_ds",), optional=())
        context = BuildContext(registry, request_id="req-1")
        with pytest.raises(RequiredComponentBuildError):
            await Composer().compose_analysis(analysis, dataset_registry, context, detail_level=DetailLevel.STANDARD)

    @pytest.mark.asyncio
    async def test_optional_dataset_failure_is_skipped_whole_not_partial(self):
        def _failing(context, deps):
            raise RuntimeError("no data")

        registry = ComponentRegistry([_component("portfolio.a"), _component("portfolio.opt_ok"), _component("portfolio.opt_broken", builder=_failing)])
        required_dataset = _dataset("portfolio.required_ds", required=("portfolio.a",))
        optional_dataset = _dataset("portfolio.optional_ds", required=("portfolio.opt_ok", "portfolio.opt_broken"))
        dataset_registry = DatasetRegistry([required_dataset, optional_dataset], component_registry=registry)
        analysis = _analysis("portfolio.combo", required=("portfolio.required_ds",), optional=("portfolio.optional_ds",))
        context = BuildContext(registry, request_id="req-1")
        composition = await Composer().compose_analysis(analysis, dataset_registry, context, detail_level=DetailLevel.STANDARD)
        # the whole optional dataset is omitted (not partially included) because one of its required components failed
        assert composition.dataset_ids == ("portfolio.required_ds",)
        assert {section.component_id for section in composition.sections} == {"portfolio.a"}

    @pytest.mark.asyncio
    async def test_optional_dataset_unsupported_detail_level_is_skipped(self):
        registry = ComponentRegistry([_component("portfolio.a"), _component("portfolio.b")])
        required_dataset = _dataset("portfolio.required_ds", required=("portfolio.a",))
        optional_dataset = _dataset("portfolio.optional_ds", required=("portfolio.b",), detail_levels=frozenset({DetailLevel.FULL}))
        dataset_registry = DatasetRegistry([required_dataset, optional_dataset], component_registry=registry)
        analysis = _analysis("portfolio.combo", required=("portfolio.required_ds",), optional=("portfolio.optional_ds",))
        context = BuildContext(registry, request_id="req-1")
        composition = await Composer().compose_analysis(analysis, dataset_registry, context, detail_level=DetailLevel.COMPACT)
        assert composition.dataset_ids == ("portfolio.required_ds",)

    @pytest.mark.asyncio
    async def test_shared_component_across_datasets_is_deduplicated_and_built_once(self):
        registry = ComponentRegistry([_component("portfolio.shared"), _component("portfolio.only_a"), _component("portfolio.only_b")])
        dataset_a = _dataset("portfolio.a_ds", required=("portfolio.shared", "portfolio.only_a"))
        dataset_b = _dataset("portfolio.b_ds", required=("portfolio.shared", "portfolio.only_b"))
        dataset_registry = DatasetRegistry([dataset_a, dataset_b], component_registry=registry)
        analysis = _analysis("portfolio.combo", required=("portfolio.a_ds", "portfolio.b_ds"), optional=())
        context = BuildContext(registry, request_id="req-1")
        composition = await Composer().compose_analysis(analysis, dataset_registry, context, detail_level=DetailLevel.STANDARD)
        component_ids = [section.component_id for section in composition.sections]
        assert component_ids.count("portfolio.shared") == 1
        assert set(component_ids) == {"portfolio.shared", "portfolio.only_a", "portfolio.only_b"}
        assert context.build_count("portfolio.shared") == 1

    @pytest.mark.asyncio
    async def test_analysis_version_mismatch_raises(self):
        registry = ComponentRegistry([_component("portfolio.a")])
        dataset_a = _dataset("portfolio.a_ds", required=("portfolio.a",))
        dataset_registry = DatasetRegistry([dataset_a], component_registry=registry)
        analysis = _analysis("portfolio.combo", required=("portfolio.a_ds",), optional=())
        context = BuildContext(registry, request_id="req-1")
        with pytest.raises(AnalysisVersionMismatchError):
            await Composer().compose_analysis(analysis, dataset_registry, context, detail_level=DetailLevel.STANDARD, expected_version=99)


@pytest.fixture(scope="module")
def foundation_component_registry() -> ComponentRegistry:
    return ComponentRegistry(ALL_FOUNDATION_COMPONENTS)


@pytest.fixture(scope="module")
def foundation_dataset_registry(
    foundation_component_registry: ComponentRegistry,
) -> DatasetRegistry:
    return build_dataset_registry(foundation_component_registry)


@pytest.fixture(scope="module")
def foundation_analysis_registry(
    foundation_dataset_registry: DatasetRegistry,
):
    return build_analysis_registry(foundation_dataset_registry)


class TestFoundationCatalogComposition:
    """The retained placeholder baseline remains fail-closed for metadata tests.

    Production `build_component_registry()` is now fully real; these checks
    explicitly construct a registry from `ALL_FOUNDATION_COMPONENTS`.
    """

    @staticmethod
    def _root_cause(exc: RequiredComponentBuildError) -> BaseException:
        cause = exc.cause
        while isinstance(cause, RequiredComponentBuildError):
            cause = cause.cause
        return cause

    @pytest.mark.asyncio
    async def test_compose_all_25_datasets_fail_closed_on_unimplemented_builders(
        self,
        foundation_component_registry: ComponentRegistry,
        foundation_dataset_registry: DatasetRegistry,
    ):
        composer = Composer()
        for dataset in foundation_dataset_registry:
            for detail_level in DetailLevel:
                context = BuildContext(
                    foundation_component_registry,
                    request_id=f"{dataset.dataset_id}-{detail_level.value}",
                )
                with pytest.raises(RequiredComponentBuildError) as exc_info:
                    await composer.compose_dataset(dataset, context, detail_level=detail_level)
                assert isinstance(self._root_cause(exc_info.value), ComponentNotImplementedError), f"{dataset.dataset_id} did not fail closed with ComponentNotImplementedError"

    @pytest.mark.asyncio
    async def test_compose_all_17_analyses_fail_closed_on_unimplemented_builders(
        self,
        foundation_component_registry: ComponentRegistry,
        foundation_dataset_registry: DatasetRegistry,
        foundation_analysis_registry,
    ):
        composer = Composer()
        for analysis in foundation_analysis_registry:
            context = BuildContext(
                foundation_component_registry,
                request_id=analysis.analysis_id,
            )
            with pytest.raises(RequiredComponentBuildError) as exc_info:
                await composer.compose_analysis(
                    analysis,
                    foundation_dataset_registry,
                    context,
                    detail_level=DetailLevel.STANDARD,
                )
            assert isinstance(self._root_cause(exc_info.value), ComponentNotImplementedError), f"{analysis.analysis_id} did not fail closed with ComponentNotImplementedError"

    @pytest.mark.asyncio
    async def test_foundation_registries_still_report_expected_counts(
        self,
        foundation_dataset_registry: DatasetRegistry,
        foundation_analysis_registry,
    ):
        assert len(foundation_dataset_registry) == 32
        assert len(foundation_analysis_registry) == 17


def test_production_component_registry_contains_only_real_specs():
    registry = build_component_registry()

    assert len(registry) == 65
    assert registry.canonical_order == tuple(spec.component_id for spec in ALL_FOUNDATION_COMPONENTS)
    assert all(registry.get(component_id).output_model is not FoundationComponentPayload for component_id in registry.canonical_order)


class TestAllDataRequirednessPreservationEndToEnd:
    """Item 2 (architecture review round 2): `all_data` composition preserves
    per-component requiredness end-to-end through the composer - an optional
    component that fails to build is omitted without failing the whole
    `all_data` export, while a required component that fails still fails
    closed."""

    @pytest.mark.asyncio
    async def test_optional_component_failure_within_all_data_is_omitted_not_fatal(self):
        def _ok(context, deps):
            return _Payload(value=1)

        def _failing(context, deps):
            raise RuntimeError("optional source unavailable")

        registry = ComponentRegistry(
            [
                _component("portfolio.required_a", builder=_ok),
                _component("portfolio.required_b", builder=_ok),
                _component("portfolio.optional_only", builder=_failing),
            ]
        )
        source_required_only = _dataset("portfolio.required_ds", required=("portfolio.required_a",))
        source_mixed = _dataset("portfolio.mixed_ds", required=("portfolio.required_b",), optional=("portfolio.optional_only",))
        all_data = build_all_data_dataset(
            dataset_id="portfolio.all_data",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="k.display",
            description_i18n_key="k.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            technical_requirements=(),
            period_semantics=PeriodBehavior.AS_OF,
            supported_detail_levels=ALL_DETAIL_LEVELS,
            source_specs=(source_required_only, source_mixed),
            component_registry=registry,
        )
        assert all_data.required_component_ids == ("portfolio.required_a", "portfolio.required_b")
        assert all_data.optional_component_ids == ("portfolio.optional_only",)
        context = BuildContext(registry, request_id="req-1")
        composition = await Composer().compose_dataset(all_data, context, detail_level=DetailLevel.STANDARD)
        # the whole all_data export still succeeds; only the failing optional
        # component is omitted, with a diagnostic recorded (not a fatal error)
        component_ids = {section.component_id for section in composition.sections}
        assert component_ids == {"portfolio.required_a", "portfolio.required_b"}
        assert any(diag.component_id == "portfolio.optional_only" for diag in context.diagnostics)

    @pytest.mark.asyncio
    async def test_required_component_failure_within_all_data_fails_the_whole_export(self):
        def _failing(context, deps):
            raise RuntimeError("required source unavailable")

        registry = ComponentRegistry([_component("portfolio.required_broken", builder=_failing)])
        source = _dataset("portfolio.required_ds", required=("portfolio.required_broken",))
        all_data = build_all_data_dataset(
            dataset_id="portfolio.all_data",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="k.display",
            description_i18n_key="k.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            technical_requirements=(),
            period_semantics=PeriodBehavior.AS_OF,
            supported_detail_levels=ALL_DETAIL_LEVELS,
            source_specs=(source,),
            component_registry=registry,
        )
        context = BuildContext(registry, request_id="req-1")
        with pytest.raises(RequiredComponentBuildError):
            await Composer().compose_dataset(all_data, context, detail_level=DetailLevel.STANDARD)


class TestOptionalDiagnosticDedupAcrossDatasets:
    """Item 6 (architecture review round 2): the same cached optional-component
    failure resolved through two different datasets composed within a single
    `BuildContext` records exactly one diagnostic, deterministically."""

    @pytest.mark.asyncio
    async def test_shared_failing_optional_component_across_two_datasets_yields_one_diagnostic(self):
        calls = {"count": 0}

        def _failing(context, deps):
            calls["count"] += 1
            raise RuntimeError("shared optional source unavailable")

        registry = ComponentRegistry(
            [
                _component("portfolio.required_a"),
                _component("portfolio.required_b"),
                _component("portfolio.shared_optional", builder=_failing),
            ]
        )
        dataset_a = _dataset("portfolio.a_ds", required=("portfolio.required_a",), optional=("portfolio.shared_optional",))
        dataset_b = _dataset("portfolio.b_ds", required=("portfolio.required_b",), optional=("portfolio.shared_optional",))
        context = BuildContext(registry, request_id="req-1")
        composition_a = await Composer().compose_dataset(dataset_a, context, detail_level=DetailLevel.STANDARD)
        composition_b = await Composer().compose_dataset(dataset_b, context, detail_level=DetailLevel.STANDARD)
        assert {section.component_id for section in composition_a.sections} == {"portfolio.required_a"}
        assert {section.component_id for section in composition_b.sections} == {"portfolio.required_b"}
        assert calls["count"] == 1
        assert len([diag for diag in context.diagnostics if diag.component_id == "portfolio.shared_optional"]) == 1
