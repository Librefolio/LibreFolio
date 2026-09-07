"""Tests for the autonomous SignalPlugin contract and strict registry."""

from __future__ import annotations

import inspect
import shutil
import sys
from datetime import date
from importlib.machinery import ModuleSpec
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import DEFAULT_TEST_DATA_DIR
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAiExportTemporalRule,
    SignalAxisRole,
    SignalAxisSpec,
    SignalCategory,
    SignalComputation,
    SignalDomain,
    SignalExecutionContext,
    SignalInputRequirements,
    SignalLineSeries,
    SignalOutputSpec,
    SignalPriceField,
    SignalSeriesKind,
    SignalTemporalClass,
    SignalUnit,
    SignalValuePoint,
    SignalWarmupRequirement,
)
from backend.app.services import provider_registry as registry_module
from backend.app.services.provider_registry import (
    DuplicatePluginCodeError,
    PluginDiscoveryError,
    SignalPluginRegistry,
    register_plugin,
)
from backend.app.services.signal_plugins.base import SignalPlugin


class DemoParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length: int = Field(
        20,
        ge=2,
        le=500,
        json_schema_extra={
            "x-i18n-key": "signals.params.length",
            "x-control-order": 1,
            "x-step": 1,
        },
    )
    required_mode: str


class ComparisonParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comparison_asset_id: int = Field(..., gt=0)


class DemoSignalPlugin(SignalPlugin):
    signal_code = "DEMO"
    implementation_version = "1.0.0"
    category = SignalCategory.TREND
    display_name_key = "signals.demo.name"
    description_key = "signals.demo.description"
    semantic_id = "demo_signal"
    semantic_description = "Test signal used by registry contracts."
    icon = "activity"
    docs_path = "signals/demo/"
    params_model = DemoParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="demo",
            label_key="signals.demo.output",
            semantic_id="demo_signal.value",
            semantic_description="Test signal output value.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.PRICE,
            axis=SignalAxisSpec(key="price", role=SignalAxisRole.PRICE),
        ),
    )
    compatible_domains = (SignalDomain.ASSET, SignalDomain.FX)

    @classmethod
    def warmup_requirement(cls, params, context):
        return SignalWarmupRequirement(
            minimum_points=params.length,
            stabilization_points=0,
            total_points=params.length,
        )

    def compute(self, price_points, event_points, params, context):
        return SignalComputation(
            series=[
                SignalLineSeries(
                    key="demo",
                    label_key="signals.demo.output",
                    semantic_id="demo_signal.value",
                    semantic_description="Test signal output value.",
                    unit=SignalUnit.PRICE,
                    axis=SignalAxisSpec(key="price", role=SignalAxisRole.PRICE),
                    points=[SignalValuePoint(date=point.date, value=float(point.close)) for point in price_points],
                )
            ]
        )


class InlineSignalRegistry(SignalPluginRegistry):
    @classmethod
    def _get_plugin_folder(cls) -> str:
        return "inline_signal_registry_unused"


class BrokenSignalRegistry(SignalPluginRegistry):
    @classmethod
    def _get_plugin_folder(cls) -> str:
        return "broken_signal_registry"


@pytest.fixture(autouse=True)
def reset_signal_registries():
    for registry in (InlineSignalRegistry, BrokenSignalRegistry):
        registry._plugins = {}
        registry._discovery_done = False
        registry._discovery_errors = ()


@pytest.fixture
def discovery_root():
    root = DEFAULT_TEST_DATA_DIR / f"signal_registry_{uuid4().hex}"
    folder = root / "backend" / "app" / "services" / BrokenSignalRegistry._get_plugin_folder()
    folder.mkdir(parents=True, exist_ok=True)
    yield root
    module_prefix = f"backend.app.services.{BrokenSignalRegistry._get_plugin_folder()}."
    for module_name in tuple(sys.modules):
        if module_name.startswith(module_prefix):
            sys.modules.pop(module_name, None)
    shutil.rmtree(root, ignore_errors=True)


def test_register_plugin_decorator_and_catalog_definition():
    @register_plugin(InlineSignalRegistry)
    class DecoratedSignal(DemoSignalPlugin):
        signal_code = "DECORATED"

    assert InlineSignalRegistry.get_plugin("DECORATED") is DecoratedSignal
    assert isinstance(InlineSignalRegistry.get_plugin_instance("DECORATED"), DecoratedSignal)
    definition = InlineSignalRegistry.list_definitions()[0]
    assert definition.signal_code == "DECORATED"
    assert definition.default_params == {"length": 20}
    assert definition.semantic_id == "demo_signal"
    assert definition.semantic_description == "Test signal used by registry contracts."
    assert definition.output_specs[0].semantic_id == "demo_signal.value"
    assert definition.params_schema["required"] == ["required_mode"]
    assert definition.params_schema["properties"]["length"]["x-i18n-key"] == "signals.params.length"
    assert InlineSignalRegistry.get_plugin(" decorated ") is DecoratedSignal


def test_official_ai_export_temporal_rules_serialize_in_catalog():
    plugin_class = SignalPluginRegistry.get_plugin("EMA")
    definition = plugin_class.catalog_definition()

    assert definition.model_dump(mode="json")["ai_export_temporal_rules"] == [
        {"temporal_class": "medium", "parameter_match": {"period": 20}},
        {"temporal_class": "slow", "parameter_match": {"period": 50}},
        {"temporal_class": "very_slow", "parameter_match": {"period": 200}},
    ]
    definition.ai_export_temporal_rules[0].parameter_match["period"] = 999
    assert plugin_class.ai_export_temporal_rules[0].parameter_match == {"period": 20}


@pytest.mark.parametrize(
    ("signal_code", "expected"),
    [
        ("STOCH_RSI", SignalTemporalClass.VERY_FAST),
        ("RSI", SignalTemporalClass.VERY_FAST),
        ("MFI", SignalTemporalClass.VERY_FAST),
        ("CCI", SignalTemporalClass.FAST),
        ("ROC", SignalTemporalClass.FAST),
        ("ATR", SignalTemporalClass.FAST),
        ("NATR", SignalTemporalClass.FAST),
        ("MACD", SignalTemporalClass.MEDIUM_FAST),
        ("PPO", SignalTemporalClass.MEDIUM_FAST),
        ("BOLLINGER", SignalTemporalClass.MEDIUM_FAST),
        ("DONCHIAN", SignalTemporalClass.MEDIUM_FAST),
        ("KAMA", SignalTemporalClass.MEDIUM),
        ("AROON", SignalTemporalClass.MEDIUM),
        ("ADX", SignalTemporalClass.MEDIUM),
        ("OBV", SignalTemporalClass.MEDIUM),
    ],
)
def test_fixed_ai_export_temporal_rules_resolve(signal_code, expected):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)

    assert plugin_class.resolve_ai_export_temporal_class({}) == expected
    assert plugin_class.ai_export_temporal_rules[0].parameter_match == {}


@pytest.mark.parametrize(
    ("signal_code", "params", "expected"),
    [
        ("EMA", {"period": 20, "offset": 7.5}, SignalTemporalClass.MEDIUM),
        ("EMA", {"period": 50, "offset": -2.0}, SignalTemporalClass.SLOW),
        ("EMA", {"period": 200, "offset": 0.0}, SignalTemporalClass.VERY_SLOW),
        ("SMA", {"period": 50}, SignalTemporalClass.SLOW),
        ("SMA", {"period": 200}, SignalTemporalClass.VERY_SLOW),
    ],
)
def test_period_specific_ai_export_temporal_rules_resolve(signal_code, params, expected):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    validated_params = plugin_class.validate_params(params)

    assert plugin_class.resolve_ai_export_temporal_class(validated_params) == expected


@pytest.mark.parametrize(
    ("signal_code", "params"),
    [
        ("EMA", {"period": 21}),
        ("SMA", {"period": 20}),
    ],
)
def test_unknown_period_has_no_ai_export_temporal_fallback(signal_code, params):
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)

    with pytest.raises(ValueError, match="found 0"):
        plugin_class.resolve_ai_export_temporal_class(params)


def test_ai_export_temporal_rule_declarations_reject_duplicates_and_ambiguity():
    catch_all = SignalAiExportTemporalRule(
        temporal_class=SignalTemporalClass.MEDIUM,
    )

    class DuplicateTemporalRules(DemoSignalPlugin):
        signal_code = "DUPLICATE_TEMPORAL_RULES"
        ai_export_temporal_rules = (catch_all, catch_all.model_copy(deep=True))

    class ListTemporalRules(DemoSignalPlugin):
        signal_code = "LIST_TEMPORAL_RULES"
        ai_export_temporal_rules = [catch_all]

    class AmbiguousTemporalRules(DemoSignalPlugin):
        signal_code = "AMBIGUOUS_TEMPORAL_RULES"
        ai_export_temporal_rules = (
            catch_all,
            SignalAiExportTemporalRule(
                temporal_class=SignalTemporalClass.SLOW,
                parameter_match={"length": 20},
            ),
        )

    with pytest.raises(ValueError, match="duplicate rules"):
        DuplicateTemporalRules.validate_definition()
    with pytest.raises(TypeError, match="must be a tuple"):
        ListTemporalRules.validate_definition()
    with pytest.raises(ValueError, match="ambiguous rules"):
        AmbiguousTemporalRules.validate_definition()
    with pytest.raises(ValueError, match="found 2"):
        AmbiguousTemporalRules.resolve_ai_export_temporal_class({"required_mode": "strict"})


def test_ai_export_temporal_rule_parses_enum_and_is_json_safe():
    assert SignalAiExportTemporalRule(temporal_class="fast").temporal_class == SignalTemporalClass.FAST
    with pytest.raises(ValueError, match="non-finite float"):
        SignalAiExportTemporalRule(
            temporal_class=SignalTemporalClass.FAST,
            parameter_match={"period": float("nan")},
        )


def test_ai_export_temporal_rule_keys_use_normalized_parameter_aliases():
    class AliasedParams(BaseModel):
        model_config = ConfigDict(extra="forbid", populate_by_name=True)

        internal_period: int = Field(20, alias="period")

    class AliasedTemporalRule(DemoSignalPlugin):
        signal_code = "ALIASED_TEMPORAL_RULE"
        params_model = AliasedParams
        ai_export_temporal_rules = (
            SignalAiExportTemporalRule(
                temporal_class=SignalTemporalClass.MEDIUM,
                parameter_match={"period": 20},
            ),
        )

    class InternalNameTemporalRule(AliasedTemporalRule):
        signal_code = "INTERNAL_NAME_TEMPORAL_RULE"
        ai_export_temporal_rules = (
            SignalAiExportTemporalRule(
                temporal_class=SignalTemporalClass.MEDIUM,
                parameter_match={"internal_period": 20},
            ),
        )

    AliasedTemporalRule.validate_definition()
    assert AliasedTemporalRule.resolve_ai_export_temporal_class({"period": 20}) == SignalTemporalClass.MEDIUM
    with pytest.raises(ValueError, match="unknown normalized params: internal_period"):
        InternalNameTemporalRule.validate_definition()


def test_non_ai_export_risk_plugin_does_not_require_temporal_rules():
    class NonAiExportRiskSignal(DemoSignalPlugin):
        signal_code = "NON_AI_EXPORT_RISK"
        category = SignalCategory.RISK

    NonAiExportRiskSignal.validate_definition()
    assert NonAiExportRiskSignal.catalog_definition().ai_export_temporal_rules == []
    with pytest.raises(ValueError, match="found 0"):
        NonAiExportRiskSignal.resolve_ai_export_temporal_class({"required_mode": "strict"})


def test_plugin_definition_rejects_implicit_aggregation_profile():
    class ImplicitAggregationPlugin(DemoSignalPlugin):
        signal_code = "IMPLICIT_AGGREGATION"
        output_specs = (
            SignalOutputSpec(
                key="implicit",
                label_key="signals.implicit.output",
                semantic_id="implicit_aggregation.value",
                semantic_description="Test output with an omitted aggregation profile.",
                kind=SignalSeriesKind.LINE,
                unit=SignalUnit.PRICE,
                axis=SignalAxisSpec(key="price", role=SignalAxisRole.PRICE),
            ),
        )

    with pytest.raises(ValueError, match="declare aggregation_profile explicitly"):
        ImplicitAggregationPlugin.validate_definition()


def test_catalog_definition_default_ai_description_derives_from_catalog_metadata():
    """describe_for_ai() default derives outputs/semantics purely from
    existing plugin-owned metadata — no per-plugin AI boilerplate needed."""

    @register_plugin(InlineSignalRegistry)
    class AiDescribedSignal(DemoSignalPlugin):
        signal_code = "AI_DESCRIBED"

    definition = InlineSignalRegistry.list_definitions()[0]

    assert definition.ai_description is not None
    assert definition.ai_description.signal_code == "AI_DESCRIBED"
    assert definition.ai_description.semantic_id == AiDescribedSignal.semantic_id
    assert definition.ai_description.semantic_description == AiDescribedSignal.semantic_description
    assert definition.ai_description.category == AiDescribedSignal.category
    assert len(definition.ai_description.outputs) == 1
    assert definition.ai_description.outputs[0].semantic_id == "demo_signal.value"
    assert definition.ai_description.outputs[0].semantic_description == "Test signal output value."
    assert definition.ai_events == []


def test_describe_events_for_ai_default_derives_one_entry_per_event_type():
    """A plugin declaring requires_events with explicit event_types gets one
    describe_events_for_ai() entry per type by default, with no override."""

    class EventAwareParams(BaseModel):
        model_config = ConfigDict(extra="forbid")

    class EventAwareSignal(DemoSignalPlugin):
        signal_code = "EVENT_AWARE"
        params_model = EventAwareParams
        input_requirements = SignalInputRequirements(
            requires_events=True,
            event_types=["DIVIDEND", "SPLIT"],
        )

    events = EventAwareSignal.describe_events_for_ai()

    assert len(events) == 2
    assert {event.event_type for event in events} == {"DIVIDEND", "SPLIT"}
    assert all(event.semantic_description == EventAwareSignal.semantic_description for event in events)
    assert all(event.deduplicate is True for event in events)


def test_validate_input_and_validate_output_hooks_default_to_no_op():
    """Default validate_input/validate_output hooks are no-ops that never
    raise, so plugins that don't override them are unaffected."""
    params = DemoSignalPlugin.validate_params({"length": 20, "required_mode": "loose"})
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(start=date(2026, 1, 1)),
        source_reference="asset:1",
    )

    assert DemoSignalPlugin.validate_input([], [], params, context) is None
    computation = SignalComputation(
        series=[
            SignalLineSeries(
                key="demo",
                label_key="signals.demo.output",
                semantic_id="demo_signal.value",
                semantic_description="Test signal output value.",
                unit=SignalUnit.PRICE,
                axis=SignalAxisSpec(key="price", role=SignalAxisRole.PRICE),
                points=[SignalValuePoint(date=date(2026, 1, 1), value=1.0)],
            )
        ]
    )
    assert DemoSignalPlugin.validate_output(computation, [], [], params, context) is None


def test_plugin_validates_and_normalizes_params():
    params = DemoSignalPlugin.validate_params({"length": 30, "required_mode": "strict"})
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(start=date(2026, 1, 1)),
        source_reference="asset:1",
    )

    requirement = DemoSignalPlugin.warmup_requirement(params, context)

    assert params.length == 30
    assert requirement.total_points == 30
    with pytest.raises(ValueError):
        DemoSignalPlugin.validate_params({"length": 30, "required_mode": "strict", "unknown": True})


def test_duplicate_signal_code_is_rejected():
    class FirstSignal(DemoSignalPlugin):
        signal_code = "DUPLICATE"

    class SecondSignal(DemoSignalPlugin):
        signal_code = "DUPLICATE"

    InlineSignalRegistry.register(FirstSignal)

    with pytest.raises(DuplicatePluginCodeError, match="DUPLICATE"):
        InlineSignalRegistry.register(SecondSignal)


def test_noncanonical_signal_code_is_rejected():
    class LowercaseSignal(DemoSignalPlugin):
        signal_code = "lowercase"

    with pytest.raises(ValueError, match="canonical uppercase"):
        InlineSignalRegistry.register(LowercaseSignal)


def test_invalid_or_prescriptive_semantics_are_rejected():
    class InvalidSemanticIdSignal(DemoSignalPlugin):
        signal_code = "INVALID_SEMANTIC_ID"
        semantic_id = "Invalid Semantic"

    class PrescriptiveSemanticSignal(DemoSignalPlugin):
        signal_code = "PRESCRIPTIVE_SEMANTIC"
        semantic_description = "Indicates when to buy."

    with pytest.raises(ValueError, match="semantic_id"):
        InlineSignalRegistry.register(InvalidSemanticIdSignal)
    with pytest.raises(ValueError, match="neutral and non-prescriptive"):
        InlineSignalRegistry.register(PrescriptiveSemanticSignal)


def test_duplicate_output_semantic_ids_are_rejected():
    duplicate = DemoSignalPlugin.output_specs[0].model_copy(
        update={
            "key": "duplicate",
            "label_key": "signals.demo.duplicate",
        }
    )

    class DuplicateOutputSemanticSignal(DemoSignalPlugin):
        signal_code = "DUPLICATE_OUTPUT_SEMANTIC"
        output_specs = (
            DemoSignalPlugin.output_specs[0],
            duplicate,
        )

    with pytest.raises(ValueError, match="output semantic_ids"):
        InlineSignalRegistry.register(DuplicateOutputSemanticSignal)

    class SignalOutputSemanticCollision(DemoSignalPlugin):
        signal_code = "SIGNAL_OUTPUT_SEMANTIC_COLLISION"
        semantic_id = DemoSignalPlugin.output_specs[0].semantic_id

    with pytest.raises(ValueError, match="signal and output semantic_ids"):
        InlineSignalRegistry.register(SignalOutputSemanticCollision)


def test_registry_rejects_non_signal_classes_and_abstract_base():
    class NotASignal:
        signal_code = "NOT_A_SIGNAL"

    with pytest.raises(TypeError, match="extend SignalPlugin"):
        InlineSignalRegistry.register(NotASignal)
    with pytest.raises(TypeError, match="concrete"):
        InlineSignalRegistry.register(SignalPlugin)


def test_registry_rejects_plugins_with_required_constructor_args():
    class StatefulSignal(DemoSignalPlugin):
        signal_code = "STATEFUL"

        def __init__(self, dependency):
            self.dependency = dependency

    with pytest.raises(TypeError, match="without arguments"):
        InlineSignalRegistry.register(StatefulSignal)


def test_registry_rejects_params_models_that_allow_extra_fields():
    class UnsafeParams(BaseModel):
        value: int = 1

    class UnsafeSignal(DemoSignalPlugin):
        signal_code = "UNSAFE"
        params_model = UnsafeParams

    with pytest.raises(ValueError, match="extra='forbid'"):
        InlineSignalRegistry.register(UnsafeSignal)


def test_comparison_asset_requirement_references_declared_param():
    class MissingComparisonParamSignal(DemoSignalPlugin):
        signal_code = "MISSING_COMPARISON_PARAM"
        input_requirements = SignalInputRequirements(
            price_fields=[SignalPriceField.CLOSE],
            uses_prepared_asset_series=True,
            comparison_asset_param="comparison_asset_id",
        )

    class ComparisonSignal(MissingComparisonParamSignal):
        signal_code = "COMPARISON"
        params_model = ComparisonParams

    with pytest.raises(
        ValueError,
        match="declared plugin parameter",
    ):
        InlineSignalRegistry.register(MissingComparisonParamSignal)

    InlineSignalRegistry.register(ComparisonSignal)
    definition = InlineSignalRegistry.list_definitions()[0]
    assert definition.input_requirements.comparison_asset_param == "comparison_asset_id"


def test_catalog_generation_deep_copies_plugin_metadata():
    InlineSignalRegistry.register(DemoSignalPlugin)

    definition = InlineSignalRegistry.list_definitions()[0]
    definition.input_requirements.price_fields.append(SignalPriceField.HIGH)
    definition.output_specs[0].label_key = "changed"

    assert DemoSignalPlugin.input_requirements.price_fields == [SignalPriceField.CLOSE]
    assert DemoSignalPlugin.output_specs[0].label_key == "signals.demo.output"


def test_strict_discovery_exposes_and_repeats_broken_module_error(monkeypatch, discovery_root):
    plugin_file = discovery_root / "backend" / "app" / "services" / BrokenSignalRegistry._get_plugin_folder() / "broken.py"
    plugin_file.write_text("raise RuntimeError('broken signal plugin')\n", encoding="utf-8")
    monkeypatch.setattr(registry_module, "PROJECT_ROOT", discovery_root)

    with pytest.raises(PluginDiscoveryError, match="broken signal plugin"):
        BrokenSignalRegistry.auto_discover()

    failures = BrokenSignalRegistry.get_discovery_errors()
    assert len(failures) == 1
    assert failures[0].module_name.endswith(".broken")
    assert failures[0].error_type == "RuntimeError"

    with pytest.raises(PluginDiscoveryError, match="broken signal plugin"):
        BrokenSignalRegistry.auto_discover()


def test_discovery_imports_each_signal_module_once(monkeypatch, discovery_root):
    plugin_file = discovery_root / "backend" / "app" / "services" / BrokenSignalRegistry._get_plugin_folder() / "demo.py"
    plugin_file.write_text("# loaded by dummy loader\n", encoding="utf-8")
    load_calls: list[str] = []

    class DummyLoader:
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            load_calls.append(module.__name__)
            BrokenSignalRegistry.register(DemoSignalPlugin)

    monkeypatch.setattr(registry_module, "PROJECT_ROOT", discovery_root)
    monkeypatch.setattr(
        registry_module.importlib.util,
        "spec_from_file_location",
        lambda module_name, _path: ModuleSpec(module_name, DummyLoader()),
    )

    BrokenSignalRegistry.auto_discover()
    BrokenSignalRegistry.auto_discover()

    assert load_calls == [f"backend.app.services.{BrokenSignalRegistry._get_plugin_folder()}.demo"]
    assert BrokenSignalRegistry.list_plugin_codes() == ["DEMO"]


def test_real_module_discovery_supports_nested_forward_ref_params(monkeypatch, discovery_root):
    plugin_file = discovery_root / "backend" / "app" / "services" / BrokenSignalRegistry._get_plugin_folder() / "nested.py"
    plugin_file.write_text(
        f"""
from pydantic import BaseModel, ConfigDict
from {__name__} import BrokenSignalRegistry, DemoSignalPlugin

class Container:
    class Settings(BaseModel):
        value: int = 1

class NestedParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    settings: "Container.Settings" = Container.Settings()

class NestedSignal(DemoSignalPlugin):
    signal_code = "NESTED"
    params_model = NestedParams

BrokenSignalRegistry.register(NestedSignal)
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(registry_module, "PROJECT_ROOT", discovery_root)

    BrokenSignalRegistry.auto_discover()

    plugin_class = BrokenSignalRegistry.get_plugin("NESTED")
    assert plugin_class is not None
    assert plugin_class.catalog_definition().params_schema["properties"]["settings"]


def test_signal_base_and_registry_do_not_import_indicator_functions():
    base_source = inspect.getsource(registry_module.SignalPlugin)
    registry_source = inspect.getsource(registry_module.SignalPluginRegistry)

    for forbidden in ("pandas_ta_classic", "from talib import", "import talib"):
        assert forbidden not in base_source
        assert forbidden not in registry_source
    assert SignalPluginRegistry._ignored_module_stems() == frozenset({"base"})
