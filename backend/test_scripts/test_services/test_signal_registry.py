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


class DemoSignalPlugin(SignalPlugin):
    signal_code = "DEMO"
    implementation_version = "1.0.0"
    category = SignalCategory.TREND
    display_name_key = "signals.demo.name"
    description_key = "signals.demo.description"
    icon = "activity"
    docs_path = "signals/demo/"
    params_model = DemoParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="demo",
            label_key="signals.demo.output",
            kind=SignalSeriesKind.LINE,
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
    assert definition.params_schema["required"] == ["required_mode"]
    assert definition.params_schema["properties"]["length"]["x-i18n-key"] == "signals.params.length"
    assert InlineSignalRegistry.get_plugin(" decorated ") is DecoratedSignal


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
