"""
Small coverage tests for provider registries.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from importlib.machinery import ModuleSpec
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.config import DEFAULT_TEST_DATA_DIR
from backend.app.services import provider_registry as registry_module
from backend.app.services.provider_registry import AbstractProviderRegistry, BRIMProviderRegistry


@dataclass
class DummyPluginInfo:
    code: str
    name: str


class InlineRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "inline_registry_unused"


class AutoDiscoveryRegistry(AbstractProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "auto_discovery_registry"


class DummyBRIMRegistry(BRIMProviderRegistry):
    @classmethod
    def _get_provider_folder(cls) -> str:
        return "brim_registry_unused"


@pytest.fixture(autouse=True)
def reset_test_registries():
    """Reset class-level registry state between tests."""
    InlineRegistry._providers = {}
    InlineRegistry._discovery_done = False
    AutoDiscoveryRegistry._providers = {}
    AutoDiscoveryRegistry._discovery_done = False
    DummyBRIMRegistry._providers = {}
    DummyBRIMRegistry._discovery_done = False


class PropertyProvider:
    provider_name = "Property Provider"

    def __init__(self, label: str = "default"):
        self.label = label

    @property
    def provider_code(self) -> str:
        return "property_provider"


class NoKwargProvider:
    provider_code = "no_kwarg_provider"
    provider_name = "No Kwarg Provider"

    def __init__(self):
        self.created = True


class PriorityHighPlugin:
    provider_code = "high_priority"
    detection_priority = 200

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix == ".csv"

    def to_plugin_info(self) -> DummyPluginInfo:
        return DummyPluginInfo(code=self.provider_code, name="High Priority")


class PriorityLowPlugin:
    provider_code = "low_priority"
    detection_priority = 10

    def can_parse(self, file_path: Path) -> bool:
        return True

    def to_plugin_info(self) -> DummyPluginInfo:
        return DummyPluginInfo(code=self.provider_code, name="Low Priority")


class DiscoveredProvider:
    provider_code = "discovered_provider"
    provider_name = "Discovered Provider"


@pytest.fixture
def discovery_root():
    """Use repo-local fake PROJECT_ROOT for auto-discovery."""
    root = DEFAULT_TEST_DATA_DIR / f"provider_registry_misc_{uuid4().hex}"
    (root / "backend" / "app" / "services" / AutoDiscoveryRegistry._get_provider_folder()).mkdir(
        parents=True,
        exist_ok=True,
    )
    yield root
    shutil.rmtree(root, ignore_errors=True)


def test_register_list_providers_and_get_provider_instance():
    """Inline registry supports register/list/get flow."""
    InlineRegistry.register(PropertyProvider)

    providers = InlineRegistry.list_providers()
    instance = InlineRegistry.get_provider_instance("property_provider", label="custom")

    assert providers == [{"code": "property_provider", "name": "Property Provider"}]
    assert instance is not None
    assert instance.label == "custom"
    assert InlineRegistry.get_provider_instance("missing") is None


def test_get_provider_instance_falls_back_to_no_arg_constructor():
    """Registry retries without kwargs on TypeError."""
    InlineRegistry.register(NoKwargProvider)

    instance = InlineRegistry.get_provider_instance("no_kwarg_provider", ignored="value")

    assert instance is not None
    assert isinstance(instance, NoKwargProvider)
    assert instance.created is True


def test_auto_discover_imports_provider_modules_once(monkeypatch, discovery_root):
    """auto_discover scans provider folder and marks discovery done."""
    provider_file = discovery_root / "backend" / "app" / "services" / AutoDiscoveryRegistry._get_provider_folder() / "sample_provider.py"
    provider_file.write_text("# loaded by dummy loader\n", encoding="utf-8")

    load_calls: list[str] = []

    class DummyLoader:
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            load_calls.append(module.__name__)
            AutoDiscoveryRegistry.register(DiscoveredProvider)

    monkeypatch.setattr(registry_module, "PROJECT_ROOT", discovery_root)
    monkeypatch.setattr(
        registry_module.importlib.util,
        "spec_from_file_location",
        lambda module_name, _path: ModuleSpec(module_name, DummyLoader()),
    )

    AutoDiscoveryRegistry.auto_discover()
    AutoDiscoveryRegistry.auto_discover()

    assert load_calls == [f"backend.app.services.{AutoDiscoveryRegistry._get_provider_folder()}.sample_provider"]
    assert AutoDiscoveryRegistry.list_providers() == [{"code": "discovered_provider", "name": "Discovered Provider"}]


def test_brim_auto_detect_plugin_returns_highest_priority_match():
    """BRIM auto-detect prefers highest priority compatible plugin."""
    DummyBRIMRegistry.register(PriorityLowPlugin)
    DummyBRIMRegistry.register(PriorityHighPlugin)

    detected = DummyBRIMRegistry.auto_detect_plugin(Path("statement.csv"))

    assert detected == "high_priority"


def test_brim_auto_detect_plugin_returns_none_when_no_plugin_matches():
    """BRIM auto-detect returns None when nothing can parse file."""

    class NoMatchPlugin:
        provider_code = "no_match"
        detection_priority = 50

        def can_parse(self, file_path: Path) -> bool:
            return file_path.suffix == ".never"

        def to_plugin_info(self) -> DummyPluginInfo:
            return DummyPluginInfo(code=self.provider_code, name="No Match")

    DummyBRIMRegistry.register(NoMatchPlugin)

    detected = DummyBRIMRegistry.auto_detect_plugin(Path("statement.csv"))

    assert detected is None


def test_brim_list_plugin_info_returns_all_registered_plugins():
    """BRIM plugin info list mirrors registered plugin metadata."""
    DummyBRIMRegistry.register(PriorityLowPlugin)
    DummyBRIMRegistry.register(PriorityHighPlugin)

    plugin_info = DummyBRIMRegistry.list_plugin_info()

    assert [(info.code, info.name) for info in plugin_info] == [
        ("low_priority", "Low Priority"),
        ("high_priority", "High Priority"),
    ]
