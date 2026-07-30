"""Focused tests for the frozen 18-dataset / 17-analysis AI Export catalog (workstream D).

Covers exact dataset/analysis IDs and counts, the frozen analysis-to-dataset
mapping, registry uniqueness/reference/domain validation, and the declarative
`*.all_data` expansion/dedup/canonical-order behaviour.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from backend.app.services.ai_export.analyses.catalog import ALL_ANALYSES, EXPECTED_ANALYSIS_COUNT, build_analysis_registry
from backend.app.services.ai_export.analyses.spec import (
    AnalysisDatasetDomainMismatchError,
    AnalysisRegistry,
    AnalysisSpec,
    AnalysisSpecError,
    DuplicateAnalysisIdError,
    UnknownAnalysisDatasetError,
    UnknownAnalysisError,
)
from backend.app.services.ai_export.components.catalog import (
    ALL_COMPONENTS,
    ALL_FOUNDATION_COMPONENTS,
    ALL_REAL_COMPONENTS,
    FoundationComponentPayload,
    build_component_registry,
)
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import ALL_DETAIL_LEVELS, Domain, PeriodBehavior
from backend.app.services.ai_export.datasets.catalog import EXPECTED_DATASET_COUNT, build_dataset_registry
from backend.app.services.ai_export.datasets.spec import (
    DatasetComponentDomainMismatchError,
    DatasetRegistry,
    DatasetSpec,
    DatasetSpecError,
    DuplicateDatasetIdError,
    UnknownDatasetComponentError,
    UnknownDatasetError,
    build_all_data_dataset,
)

EXPECTED_DATASET_IDS = (
    "portfolio.overview",
    "portfolio.performance_flows",
    "portfolio.technical",
    "portfolio.fifo",
    "portfolio.all_data",
    "broker.overview",
    "broker.performance_flows",
    "broker.technical",
    "broker.fifo",
    "broker.all_data",
    "asset.overview",
    "asset.position_performance",
    "asset.market_technical",
    "asset.all_data",
    "fx.overview",
    "fx.market_technical",
    "fx.direct_exposure",
    "fx.all_data",
)

EXPECTED_ANALYSIS_MAPPING = {
    "portfolio.pac_planning": (("portfolio.overview", "portfolio.performance_flows"), ()),
    "portfolio.rebalancing": (("portfolio.overview",), ("portfolio.performance_flows", "portfolio.technical")),
    "portfolio.performance_attribution": (("portfolio.overview", "portfolio.performance_flows"), ()),
    "portfolio.income_review": (("portfolio.overview", "portfolio.performance_flows"), ()),
    "portfolio.fifo_review": (("portfolio.overview", "portfolio.fifo"), ()),
    "portfolio.technical_breadth": (("portfolio.overview", "portfolio.technical"), ()),
    "portfolio.description": (("portfolio.overview",), ("portfolio.performance_flows", "portfolio.technical")),
    "broker.review": (("broker.overview", "broker.performance_flows"), ("broker.technical", "broker.fifo")),
    "broker.cost_efficiency": (("broker.overview", "broker.performance_flows"), ()),
    "broker.concentration_context": (("broker.overview",), ("broker.technical",)),
    "broker.fifo_review": (("broker.overview", "broker.fifo"), ()),
    "asset.trend_analysis": (("asset.overview", "asset.market_technical"), ()),
    "asset.position_review": (("asset.overview", "asset.position_performance"), ("asset.market_technical",)),
    "asset.drawdown_recovery": (("asset.overview", "asset.market_technical"), ("asset.position_performance",)),
    "fx.trend_review": (("fx.overview", "fx.market_technical"), ()),
    "fx.conversion_timing": (("fx.overview", "fx.market_technical"), ("fx.direct_exposure",)),
    "fx.exposure_impact": (("fx.overview", "fx.direct_exposure"), ("fx.market_technical",)),
}


def _dummy_model():
    class _M(BaseModel):
        pass

    return _M


@pytest.fixture(scope="module")
def component_registry() -> ComponentRegistry:
    return build_component_registry()


@pytest.fixture(scope="module")
def dataset_registry(component_registry: ComponentRegistry) -> DatasetRegistry:
    return build_dataset_registry(component_registry)


@pytest.fixture(scope="module")
def analysis_registry(dataset_registry: DatasetRegistry) -> AnalysisRegistry:
    return build_analysis_registry(dataset_registry)


class TestDatasetCatalog:
    def test_expected_dataset_count_is_18(self):
        assert EXPECTED_DATASET_COUNT == 18

    def test_dataset_registry_has_exactly_18_entries(self, dataset_registry: DatasetRegistry):
        assert len(dataset_registry) == 18

    def test_dataset_ids_match_frozen_catalog_exactly(self, dataset_registry: DatasetRegistry):
        actual_ids = {spec.dataset_id for spec in dataset_registry}
        assert actual_ids == set(EXPECTED_DATASET_IDS)
        assert len(EXPECTED_DATASET_IDS) == len(set(EXPECTED_DATASET_IDS))

    def test_every_dataset_supports_all_three_detail_levels(self, dataset_registry: DatasetRegistry):
        for spec in dataset_registry:
            assert spec.supported_detail_levels == ALL_DETAIL_LEVELS, f"{spec.dataset_id} does not support Compact/Standard/Full"

    def test_all_data_datasets_are_present_per_domain(self, dataset_registry: DatasetRegistry):
        for domain in Domain:
            assert f"{domain.value}.all_data" in dataset_registry

    def test_schema_and_selection_versions_are_1(self, dataset_registry: DatasetRegistry):
        for spec in dataset_registry:
            assert spec.version == 1


class TestIntegratedComponentCatalog:
    def test_production_registry_has_all_45_real_components_in_frozen_order(
        self,
        component_registry: ComponentRegistry,
    ):
        expected_order = tuple(spec.component_id for spec in ALL_FOUNDATION_COMPONENTS)

        assert len(ALL_FOUNDATION_COMPONENTS) == 45
        assert len(ALL_REAL_COMPONENTS) == 45
        assert len(ALL_COMPONENTS) == 45
        assert component_registry.canonical_order == expected_order
        assert tuple(spec.component_id for spec in ALL_COMPONENTS) == expected_order
        assert all(spec.output_model is not FoundationComponentPayload for spec in component_registry)

    def test_integrated_components_preserve_frozen_metadata(
        self,
        component_registry: ComponentRegistry,
    ):
        placeholders = {spec.component_id: spec for spec in ALL_FOUNDATION_COMPONENTS}

        for real in component_registry:
            placeholder = placeholders[real.component_id]
            assert real.version == placeholder.version
            assert real.domains == placeholder.domains
            assert real.dependencies == placeholder.dependencies
            assert real.period_behavior == placeholder.period_behavior
            assert real.aggregator == placeholder.aggregator
            assert real.builder is not placeholder.builder


class TestAnalysisCatalog:
    def test_expected_analysis_count_is_17(self):
        assert EXPECTED_ANALYSIS_COUNT == 17
        assert len(ALL_ANALYSES) == 17

    def test_analysis_registry_has_exactly_17_entries(self, analysis_registry: AnalysisRegistry):
        assert len(analysis_registry) == 17

    def test_analysis_ids_match_frozen_mapping_exactly(self, analysis_registry: AnalysisRegistry):
        actual_ids = {spec.analysis_id for spec in analysis_registry}
        assert actual_ids == set(EXPECTED_ANALYSIS_MAPPING)

    def test_required_optional_mapping_matches_frozen_catalog(self, analysis_registry: AnalysisRegistry):
        for analysis_id, (expected_required, expected_optional) in EXPECTED_ANALYSIS_MAPPING.items():
            spec = analysis_registry.get(analysis_id)
            assert spec.required_dataset_ids == expected_required, analysis_id
            assert spec.optional_dataset_ids == expected_optional, analysis_id

    def test_all_versions_are_1(self, analysis_registry: AnalysisRegistry):
        for spec in analysis_registry:
            assert spec.version == 1
            assert spec.instruction_template_version == 1
            assert spec.response_contract_version == 1

    def test_no_required_optional_overlap_in_any_analysis(self, analysis_registry: AnalysisRegistry):
        for spec in analysis_registry:
            assert not (set(spec.required_dataset_ids) & set(spec.optional_dataset_ids))

    def test_dataset_order_is_deterministic_required_then_optional(self, analysis_registry: AnalysisRegistry):
        spec = analysis_registry.get("broker.review")
        assert spec.dataset_order == ("broker.overview", "broker.performance_flows", "broker.technical", "broker.fifo")


class TestRegistryValidationErrors:
    def test_duplicate_dataset_id_raises(self, component_registry: ComponentRegistry):
        spec = DatasetSpec(
            dataset_id="portfolio.overview",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="k.display",
            description_i18n_key="k.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_component_ids=("portfolio.summary",),
            optional_component_ids=(),
            section_order=("portfolio.summary",),
            technical_requirements=(),
            period_semantics=PeriodBehavior.AS_OF,
            supported_detail_levels=ALL_DETAIL_LEVELS,
        )
        with pytest.raises(DuplicateDatasetIdError):
            DatasetRegistry([spec, spec], component_registry=component_registry)

    def test_unknown_component_reference_raises(self, component_registry: ComponentRegistry):
        spec = DatasetSpec(
            dataset_id="portfolio.custom",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="k.display",
            description_i18n_key="k.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_component_ids=("portfolio.does_not_exist",),
            optional_component_ids=(),
            section_order=("portfolio.does_not_exist",),
            technical_requirements=(),
            period_semantics=PeriodBehavior.AS_OF,
            supported_detail_levels=ALL_DETAIL_LEVELS,
        )
        with pytest.raises(UnknownDatasetComponentError):
            DatasetRegistry([spec], component_registry=component_registry)

    def test_domain_mismatch_between_dataset_and_component_raises(self):
        registry = ComponentRegistry(
            [
                ComponentSpec(
                    component_id="broker.summary",
                    version=1,
                    domains=frozenset({Domain.BROKER}),
                    output_model=_dummy_model(),
                    builder=lambda context, deps: {},
                )
            ]
        )
        spec = DatasetSpec(
            dataset_id="portfolio.mismatch",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="k.display",
            description_i18n_key="k.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_component_ids=("broker.summary",),
            optional_component_ids=(),
            section_order=("broker.summary",),
            technical_requirements=(),
            period_semantics=PeriodBehavior.AS_OF,
            supported_detail_levels=ALL_DETAIL_LEVELS,
        )
        with pytest.raises(DatasetComponentDomainMismatchError):
            DatasetRegistry([spec], component_registry=registry)

    def test_dataset_spec_rejects_incomplete_section_order(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(
                dataset_id="portfolio.bad_order",
                version=1,
                domain=Domain.PORTFOLIO,
                display_i18n_key="k.display",
                description_i18n_key="k.description",
                icon="icon",
                applicability_code="test.always_applicable",
                applicable_pages=("dashboard",),
                required_component_ids=("portfolio.summary", "portfolio.positions"),
                optional_component_ids=(),
                section_order=("portfolio.summary",),  # missing portfolio.positions
                technical_requirements=(),
                period_semantics=PeriodBehavior.AS_OF,
                supported_detail_levels=ALL_DETAIL_LEVELS,
            )

    def test_dataset_spec_rejects_literal_text_as_display_i18n_key(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(
                dataset_id="portfolio.bad_i18n",
                version=1,
                domain=Domain.PORTFOLIO,
                display_i18n_key="Portfolio Overview",  # literal text, not a dotted i18n key
                description_i18n_key="k.description",
                icon="icon",
                applicability_code="test.always_applicable",
                applicable_pages=("dashboard",),
                required_component_ids=("portfolio.summary",),
                optional_component_ids=(),
                section_order=("portfolio.summary",),
                technical_requirements=(),
                period_semantics=PeriodBehavior.AS_OF,
                supported_detail_levels=ALL_DETAIL_LEVELS,
            )

    def test_dataset_spec_rejects_literal_text_as_description_i18n_key(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(
                dataset_id="portfolio.bad_i18n",
                version=1,
                domain=Domain.PORTFOLIO,
                display_i18n_key="k.display",
                description_i18n_key="A human readable sentence.",
                icon="icon",
                applicability_code="test.always_applicable",
                applicable_pages=("dashboard",),
                required_component_ids=("portfolio.summary",),
                optional_component_ids=(),
                section_order=("portfolio.summary",),
                technical_requirements=(),
                period_semantics=PeriodBehavior.AS_OF,
                supported_detail_levels=ALL_DETAIL_LEVELS,
            )

    def test_real_catalog_i18n_keys_are_dotted_keys_not_literal_text(self, dataset_registry: DatasetRegistry):
        # Binding clarification: the catalog must expose i18n keys only, never literal
        # human-readable text, for every one of the 18 frozen datasets.
        for dataset in dataset_registry:
            assert " " not in dataset.display_i18n_key, dataset.dataset_id
            assert " " not in dataset.description_i18n_key, dataset.dataset_id
            assert "." in dataset.display_i18n_key, dataset.dataset_id
            assert "." in dataset.description_i18n_key, dataset.dataset_id

    def test_get_unknown_dataset_raises(self, dataset_registry: DatasetRegistry):
        with pytest.raises(UnknownDatasetError):
            dataset_registry.get("portfolio.does_not_exist")

    def test_duplicate_analysis_id_raises(self, dataset_registry: DatasetRegistry):
        spec = AnalysisSpec(
            analysis_id="portfolio.pac_planning",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="test.analysis.display",
            description_i18n_key="test.analysis.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_dataset_ids=("portfolio.overview",),
            optional_dataset_ids=(),
            instruction_template_id="t",
            instruction_template_version=1,
            response_contract_id="r",
            response_contract_version=1,
        )
        with pytest.raises(DuplicateAnalysisIdError):
            AnalysisRegistry([spec, spec], dataset_registry=dataset_registry)

    def test_unknown_analysis_dataset_reference_raises(self, dataset_registry: DatasetRegistry):
        spec = AnalysisSpec(
            analysis_id="portfolio.custom_analysis",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="test.analysis.display",
            description_i18n_key="test.analysis.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_dataset_ids=("portfolio.does_not_exist",),
            optional_dataset_ids=(),
            instruction_template_id="t",
            instruction_template_version=1,
            response_contract_id="r",
            response_contract_version=1,
        )
        with pytest.raises(UnknownAnalysisDatasetError):
            AnalysisRegistry([spec], dataset_registry=dataset_registry)

    def test_analysis_domain_mismatch_raises(self, dataset_registry: DatasetRegistry):
        spec = AnalysisSpec(
            analysis_id="portfolio.wrong_domain",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="test.analysis.display",
            description_i18n_key="test.analysis.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_dataset_ids=("broker.overview",),
            optional_dataset_ids=(),
            instruction_template_id="t",
            instruction_template_version=1,
            response_contract_id="r",
            response_contract_version=1,
        )
        with pytest.raises(AnalysisDatasetDomainMismatchError):
            AnalysisRegistry([spec], dataset_registry=dataset_registry)

    def test_get_unknown_analysis_raises(self, analysis_registry: AnalysisRegistry):
        with pytest.raises(UnknownAnalysisError):
            analysis_registry.get("portfolio.does_not_exist")

    def test_analysis_spec_rejects_required_optional_overlap(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(
                analysis_id="portfolio.overlap",
                version=1,
                domain=Domain.PORTFOLIO,
                display_i18n_key="test.analysis.display",
                description_i18n_key="test.analysis.description",
                icon="icon",
                applicability_code="test.always_applicable",
                applicable_pages=("dashboard",),
                required_dataset_ids=("portfolio.overview",),
                optional_dataset_ids=("portfolio.overview",),
                instruction_template_id="t",
                instruction_template_version=1,
                response_contract_id="r",
                response_contract_version=1,
            )


class TestAllDataExpansion:
    def test_expands_deduplicates_and_orders_by_canonical_registration_order(self):
        registry = ComponentRegistry(
            [
                ComponentSpec(component_id="portfolio.c1", version=1, domains=frozenset({Domain.PORTFOLIO}), output_model=_dummy_model(), builder=lambda context, deps: {}),
                ComponentSpec(component_id="portfolio.c2", version=1, domains=frozenset({Domain.PORTFOLIO}), output_model=_dummy_model(), builder=lambda context, deps: {}),
                ComponentSpec(component_id="portfolio.c3", version=1, domains=frozenset({Domain.PORTFOLIO}), output_model=_dummy_model(), builder=lambda context, deps: {}),
            ]
        )
        dataset_a = DatasetSpec(
            dataset_id="portfolio.a",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="k.display",
            description_i18n_key="k.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_component_ids=("portfolio.c2", "portfolio.c1"),  # declared out of canonical order
            optional_component_ids=(),
            section_order=("portfolio.c2", "portfolio.c1"),
            technical_requirements=(),
            period_semantics=PeriodBehavior.AS_OF,
            supported_detail_levels=ALL_DETAIL_LEVELS,
        )
        dataset_b = DatasetSpec(
            dataset_id="portfolio.b",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="k.display",
            description_i18n_key="k.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_component_ids=("portfolio.c1",),  # overlaps with dataset_a -> must be deduped
            optional_component_ids=("portfolio.c3",),
            section_order=("portfolio.c1", "portfolio.c3"),
            technical_requirements=(),
            period_semantics=PeriodBehavior.AS_OF,
            supported_detail_levels=ALL_DETAIL_LEVELS,
        )
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
            source_specs=(dataset_a, dataset_b),
            component_registry=registry,
        )
        # canonical registration order is c1, c2, c3 - regardless of dataset declaration order.
        # requiredness is preserved, not promoted: c1/c2 are required by dataset_a (or dataset_b),
        # c3 is only ever optional (in dataset_b) so it stays optional in the union.
        assert all_data.required_component_ids == ("portfolio.c1", "portfolio.c2")
        assert all_data.optional_component_ids == ("portfolio.c3",)
        assert all_data.section_order == ("portfolio.c1", "portfolio.c2", "portfolio.c3")
        # dedup: c1 appears in both source datasets but only once in the union
        assert len(all_data.required_component_ids) == len(set(all_data.required_component_ids))

    def test_component_required_by_any_source_is_required_in_union(self):
        # A component that is optional in one source dataset but required in another
        # must be promoted to required in the union (never demoted).
        registry = ComponentRegistry(
            [
                ComponentSpec(component_id="portfolio.c1", version=1, domains=frozenset({Domain.PORTFOLIO}), output_model=_dummy_model(), builder=lambda context, deps: {}),
                ComponentSpec(component_id="portfolio.c2", version=1, domains=frozenset({Domain.PORTFOLIO}), output_model=_dummy_model(), builder=lambda context, deps: {}),
            ]
        )
        dataset_a = DatasetSpec(
            dataset_id="portfolio.a",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="k.display",
            description_i18n_key="k.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_component_ids=(),
            optional_component_ids=("portfolio.c1",),
            section_order=("portfolio.c1",),
            technical_requirements=(),
            period_semantics=PeriodBehavior.AS_OF,
            supported_detail_levels=ALL_DETAIL_LEVELS,
        )
        dataset_b = DatasetSpec(
            dataset_id="portfolio.b",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="k.display",
            description_i18n_key="k.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_component_ids=("portfolio.c1", "portfolio.c2"),
            optional_component_ids=(),
            section_order=("portfolio.c1", "portfolio.c2"),
            technical_requirements=(),
            period_semantics=PeriodBehavior.AS_OF,
            supported_detail_levels=ALL_DETAIL_LEVELS,
        )
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
            source_specs=(dataset_a, dataset_b),
            component_registry=registry,
        )
        assert all_data.required_component_ids == ("portfolio.c1", "portfolio.c2")
        assert all_data.optional_component_ids == ()

    def test_rejects_self_as_source(self, component_registry: ComponentRegistry):
        overview = DatasetSpec(
            dataset_id="portfolio.overview",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="k.display",
            description_i18n_key="k.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_component_ids=("portfolio.summary",),
            optional_component_ids=(),
            section_order=("portfolio.summary",),
            technical_requirements=(),
            period_semantics=PeriodBehavior.AS_OF,
            supported_detail_levels=ALL_DETAIL_LEVELS,
        )
        with pytest.raises(DatasetSpecError):
            build_all_data_dataset(
                dataset_id="portfolio.overview",
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
                source_specs=(overview,),
                component_registry=component_registry,
            )

    def test_rejects_another_all_data_as_source(self, component_registry: ComponentRegistry):
        nested_all_data = DatasetSpec(
            dataset_id="portfolio.all_data",
            version=1,
            domain=Domain.PORTFOLIO,
            display_i18n_key="k.display",
            description_i18n_key="k.description",
            icon="icon",
            applicability_code="test.always_applicable",
            applicable_pages=("dashboard",),
            required_component_ids=("portfolio.summary",),
            optional_component_ids=(),
            section_order=("portfolio.summary",),
            technical_requirements=(),
            period_semantics=PeriodBehavior.AS_OF,
            supported_detail_levels=ALL_DETAIL_LEVELS,
        )
        with pytest.raises(DatasetSpecError):
            build_all_data_dataset(
                dataset_id="portfolio.all_data_v2",
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
                source_specs=(nested_all_data,),
                component_registry=component_registry,
            )

    def test_real_catalog_all_data_matches_union_of_siblings(self, component_registry: ComponentRegistry, dataset_registry: DatasetRegistry):
        for domain in Domain:
            all_data = dataset_registry.get(f"{domain.value}.all_data")
            siblings = [spec for spec in dataset_registry.for_domain(domain) if spec.dataset_id != all_data.dataset_id]
            expected_required: set[str] = set()
            expected_optional_all: set[str] = set()
            for sibling in siblings:
                expected_required.update(sibling.required_component_ids)
                expected_optional_all.update(sibling.optional_component_ids)
            expected_optional_only = expected_optional_all - expected_required
            # requiredness is preserved (not promoted): a component required by any
            # sibling stays required; a component that is only ever optional across
            # every sibling stays optional in the all_data union.
            assert set(all_data.required_component_ids) == expected_required
            assert set(all_data.optional_component_ids) == expected_optional_only
            assert len(all_data.required_component_ids) == len(set(all_data.required_component_ids))
            assert len(all_data.optional_component_ids) == len(set(all_data.optional_component_ids))
            assert set(all_data.section_order) == expected_required | expected_optional_only
            # order follows canonical component registration order, for both partitions
            required_positions = [component_registry.canonical_order.index(cid) for cid in all_data.required_component_ids]
            assert required_positions == sorted(required_positions)
            optional_positions = [component_registry.canonical_order.index(cid) for cid in all_data.optional_component_ids]
            assert optional_positions == sorted(optional_positions)
            section_order_positions = [component_registry.canonical_order.index(cid) for cid in all_data.section_order]
            assert section_order_positions == sorted(section_order_positions)

    def test_real_catalog_asset_lot_detail_is_the_sole_optional_component(self, dataset_registry: DatasetRegistry):
        # Architecture review: after flipping provenance/reconciliation/technical
        # breadth/states_events/exposure_provenance to required, asset.lot_detail is
        # the only deliberately-optional component left in the entire catalog.
        all_optional_ids: set[str] = set()
        for spec in dataset_registry:
            if spec.dataset_id.endswith(".all_data"):
                continue
            all_optional_ids.update(spec.optional_component_ids)
        assert all_optional_ids == {"asset.lot_detail"}


class TestCatalogPresentationFields:
    """Item 4 (architecture review round 2): datasets/analyses expose catalog
    presentation/applicability fields the API/UI needs, populated for every
    frozen entry, i18n-keys-only (never literal text)."""

    def test_every_dataset_has_a_populated_applicability_code(self, dataset_registry: DatasetRegistry):
        for spec in dataset_registry:
            assert spec.applicability_code, spec.dataset_id
            assert " " not in spec.applicability_code, spec.dataset_id

    def test_every_dataset_has_non_empty_applicable_pages_and_icon(self, dataset_registry: DatasetRegistry):
        for spec in dataset_registry:
            assert spec.applicable_pages, spec.dataset_id
            assert spec.icon, spec.dataset_id

    def test_every_analysis_has_populated_presentation_fields(self, analysis_registry: AnalysisRegistry):
        for spec in analysis_registry:
            assert spec.display_i18n_key, spec.analysis_id
            assert "." in spec.display_i18n_key, spec.analysis_id
            assert " " not in spec.display_i18n_key, spec.analysis_id
            assert spec.description_i18n_key, spec.analysis_id
            assert "." in spec.description_i18n_key, spec.analysis_id
            assert " " not in spec.description_i18n_key, spec.analysis_id
            assert spec.icon, spec.analysis_id
            assert spec.applicable_pages, spec.analysis_id
            assert spec.applicability_code, spec.analysis_id
            assert " " not in spec.applicability_code, spec.analysis_id


class TestInvalidTypeValidationDatasetSpec:
    """Item 5 (architecture review round 2): hardened validation must reject
    bool/non-int versions and raw strings passed where enum members are
    required - equality with a StrEnum member is not sufficient."""

    def _kwargs(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "dataset_id": "portfolio.invalid",
            "version": 1,
            "domain": Domain.PORTFOLIO,
            "display_i18n_key": "k.display",
            "description_i18n_key": "k.description",
            "icon": "icon",
            "applicability_code": "test.always_applicable",
            "applicable_pages": ("dashboard",),
            "required_component_ids": ("portfolio.summary",),
            "optional_component_ids": (),
            "section_order": ("portfolio.summary",),
            "technical_requirements": (),
            "period_semantics": PeriodBehavior.AS_OF,
            "supported_detail_levels": ALL_DETAIL_LEVELS,
        }
        base.update(overrides)
        return base

    def test_rejects_bool_version(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(version=True))

    def test_rejects_non_int_version(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(version="1"))

    def test_rejects_raw_string_domain(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(domain="portfolio"))

    def test_rejects_raw_string_period_semantics(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(period_semantics="as_of"))

    def test_rejects_non_detail_level_member_in_supported_detail_levels(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(supported_detail_levels=frozenset({"standard"})))

    def test_rejects_empty_applicability_code(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(applicability_code=""))

    def test_rejects_literal_text_applicability_code(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(applicability_code="Always applicable!"))

    def test_rejects_duplicate_applicable_pages(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(applicable_pages=("dashboard", "dashboard")))

    def test_rejects_invalid_page_slug_format(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(applicable_pages=("Dashboard Page",)))

    def test_rejects_duplicate_technical_requirements(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(technical_requirements=("requires_price_history", "requires_price_history")))

    def test_rejects_invalid_technical_requirement_format(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(technical_requirements=("Requires Price History!",)))

    def test_rejects_invalid_scope_requirement_code_format(self):
        with pytest.raises(DatasetSpecError):
            DatasetSpec(**self._kwargs(scope_requirement_codes=("Not A Code",)))

    def test_accepts_empty_scope_requirement_codes_by_default(self):
        spec = DatasetSpec(**self._kwargs())
        assert spec.scope_requirement_codes == ()


class TestInvalidTypeValidationAnalysisSpec:
    """Item 5 (architecture review round 2): equivalent hardening for AnalysisSpec."""

    def _kwargs(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "analysis_id": "portfolio.invalid",
            "version": 1,
            "domain": Domain.PORTFOLIO,
            "display_i18n_key": "test.analysis.display",
            "description_i18n_key": "test.analysis.description",
            "icon": "icon",
            "applicability_code": "test.always_applicable",
            "applicable_pages": ("dashboard",),
            "required_dataset_ids": ("portfolio.overview",),
            "optional_dataset_ids": (),
            "instruction_template_id": "t",
            "instruction_template_version": 1,
            "response_contract_id": "r",
            "response_contract_version": 1,
        }
        base.update(overrides)
        return base

    def test_rejects_bool_version(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(**self._kwargs(version=True))

    def test_rejects_non_int_instruction_template_version(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(**self._kwargs(instruction_template_version="1"))

    def test_rejects_bool_response_contract_version(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(**self._kwargs(response_contract_version=True))

    def test_rejects_raw_string_domain(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(**self._kwargs(domain="portfolio"))

    def test_rejects_literal_text_display_i18n_key(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(**self._kwargs(display_i18n_key="Portfolio Analysis"))

    def test_rejects_literal_text_description_i18n_key(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(**self._kwargs(description_i18n_key="A human readable sentence."))

    def test_rejects_empty_applicability_code(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(**self._kwargs(applicability_code=""))

    def test_rejects_literal_text_applicability_code(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(**self._kwargs(applicability_code="Always applicable!"))

    def test_rejects_duplicate_applicable_pages(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(**self._kwargs(applicable_pages=("dashboard", "dashboard")))

    def test_rejects_empty_applicable_pages(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(**self._kwargs(applicable_pages=()))

    def test_rejects_invalid_page_slug_format(self):
        with pytest.raises(AnalysisSpecError):
            AnalysisSpec(**self._kwargs(applicable_pages=("Dashboard Page",)))
