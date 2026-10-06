"""
Small coverage tests for provider registries.

The last section pins the thread-safety contract of plugin discovery and catalogue iteration (V1).
"""

from __future__ import annotations

import shutil
import sys
import threading
import traceback
import types
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from importlib.machinery import ModuleSpec
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.config import DEFAULT_TEST_DATA_DIR
from backend.app.services import provider_registry as registry_module
from backend.app.services.provider_registry import AbstractProviderRegistry, BRIMProviderRegistry, register_provider


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


# ============================================================================
# THREAD SAFETY OF DISCOVERY AND ITERATION (V1)
# plan-phase00BrimDanskeBankStep4Implementation, §19.3 (diagnosis) and §19.6 (contract)
# ============================================================================

# Every wait below is bounded by this: a regression fails the test, it never hangs the suite.
_WAIT_SECONDS = 30.0

# How long the race test lets the second caller try to reach the catalogue before concluding that it is waiting for
# the discovery in progress. It only bounds the chance the DEFECT gets to show itself (an unguarded caller needs a few
# milliseconds of uncontended work to get there); it never decides the verdict on a fixed registry, where the second
# caller is parked on the lock, the grace always runs out, and the caller is then released onto the complete
# catalogue whatever the value. The price is paid once per run, on the green path only.
_LATE_CALLER_GRACE_SECONDS = 2.0

# Prepended to every lab plugin module: the real plugins' registration path, plus the harness through which the
# module reaches its throw-away registry and the test's gates.
_PLUGIN_HEADER = """\
import threading

from backend.app.services.provider_registry import register_provider

import {harness} as harness

"""

# Imported first (discovery goes in sorted order). When the second caller instantiates it while walking the
# catalogue, can_parse holds that caller until plugin_b has registered: a live iteration is then bound to see the
# catalogue change size under it.
_RACE_PLUGIN_A = """
@register_provider(harness.registry)
class RacePluginA:
    provider_code = "race_a"
    provider_name = "Race plugin A"
    detection_priority = 200

    def can_parse(self, file_path) -> bool:
        gates = harness.gates
        if threading.current_thread() is gates.late_caller:
            gates.late_caller_iterating.set()
            gates.b_registered.wait(timeout=harness.WAIT_SECONDS)
        return True


harness.gates.a_registered.set()
"""

# The slow plugin: the discovering thread stays inside this module (already in sys.modules, not yet registered)
# until the test releases it.
_RACE_PLUGIN_B = """
harness.gates.b_import_started.set()
harness.gates.release_b.wait(timeout=harness.WAIT_SECONDS)


@register_provider(harness.registry)
class RacePluginB:
    provider_code = "race_b"
    provider_name = "Race plugin B"
    detection_priority = 100

    def can_parse(self, file_path) -> bool:
        return True


harness.gates.b_registered.set()
"""

# Imported first: registers, then, still inside discovery and on the discovering thread, asks the registry that is
# importing it for its catalogue.
_REENTRANT_PLUGIN = """
@register_provider(harness.registry)
class ReentrantPlugin:
    provider_code = "reentrant"
    provider_name = "Re-entrant plugin"


harness.seen_by_callback = harness.registry.list_plugin_codes()
"""

_PLUGIN_AFTER_REENTRANT = """
@register_provider(harness.registry)
class AfterReentrantPlugin:
    provider_code = "after_reentrant"
    provider_name = "Plugin imported after the re-entrant one"
"""


@dataclass
class _RaceGates:
    """The events the race test shares with its plugin modules, through the harness module."""

    a_registered: threading.Event = field(default_factory=threading.Event)
    b_import_started: threading.Event = field(default_factory=threading.Event)
    release_b: threading.Event = field(default_factory=threading.Event)
    b_registered: threading.Event = field(default_factory=threading.Event)
    late_caller_iterating: threading.Event = field(default_factory=threading.Event)
    late_caller: threading.Thread | None = None

    def release_everything(self) -> None:
        """Never leave a thread parked on a gate, whatever happened to the test."""
        self.release_b.set()
        self.b_registered.set()


class _ThreadedCall:
    """One registry call on its own daemon thread, keeping what it returned or raised."""

    def __init__(self, name: str, call: Callable[[], object]):
        self._call = call
        self.result: object = None
        self.error: Exception | None = None
        self.trace = ""
        self.thread = threading.Thread(target=self._run, name=name, daemon=True)

    def _run(self) -> None:
        try:
            self.result = self._call()
        except Exception as exc:  # what the call raised is exactly what the test asserts on
            self.error = exc
            self.trace = traceback.format_exc()

    def start(self) -> _ThreadedCall:
        self.thread.start()
        return self

    def finish(self, hung: str = "the registry call hung") -> None:
        """Join with a bound: a stuck call fails the test instead of hanging the suite (the thread is a daemon)."""
        self.thread.join(timeout=_WAIT_SECONDS)
        assert not self.thread.is_alive(), f"{self.thread.name} still running after {_WAIT_SECONDS}s: {hung}"

    @property
    def outcome(self) -> tuple[str, object]:
        if self.error is not None:
            return ("raised", f"{type(self.error).__name__}: {self.error}")
        return ("returned", self.result)


@dataclass
class _PluginLab:
    """A cold throw-away BRIM registry discovering plugin modules from its own folder, under its own namespace."""

    registry: type[BRIMProviderRegistry]
    plugin_dir: Path
    harness: types.ModuleType

    def write_plugin(self, stem: str, source: str) -> None:
        """Write a plugin module that registers itself through @register_provider, as the real plugins do."""
        (self.plugin_dir / f"{stem}.py").write_text(_PLUGIN_HEADER.format(harness=self.harness.__name__) + source, encoding="utf-8")


@pytest.fixture
def plugin_lab(tmp_path: Path) -> Iterator[_PluginLab]:
    """A cold BRIM registry over `tmp_path`; the real registries and their sys.modules entries are never touched.

    It subclasses BRIMProviderRegistry because that is where the live failure happened: `get_compatible_plugins`
    (from `save_uploaded_file`, in `asyncio.to_thread`) instantiates every plugin inside its loop and calls
    `can_parse`, which is what lets a test hold a caller exactly mid-iteration. The class is created per test, so
    `__init_subclass__` gives it empty storage and a cold discovery flag (and, once V1 is fixed, its own lock).
    Plugin modules reach it, and the test's gates, through a harness module named after the same unique namespace;
    every module under that namespace leaves sys.modules at teardown.
    """
    namespace = f"lf_registry_lab_{uuid4().hex}"
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()

    class LabBRIMRegistry(BRIMProviderRegistry):
        @classmethod
        def _get_provider_folder(cls) -> str:
            return "registry_lab_unused"

        @classmethod
        def _get_plugin_directory(cls) -> Path:
            return plugin_dir

        @classmethod
        def _get_module_namespace(cls) -> str:
            return namespace

    harness = types.ModuleType(f"{namespace}_harness")
    harness.registry = LabBRIMRegistry
    harness.WAIT_SECONDS = _WAIT_SECONDS
    sys.modules[harness.__name__] = harness
    try:
        yield _PluginLab(registry=LabBRIMRegistry, plugin_dir=plugin_dir, harness=harness)
    finally:
        for module_name in list(sys.modules):
            if module_name.startswith(namespace):
                sys.modules.pop(module_name, None)


def _race_diagnosis(lab: _PluginLab, calls: list[_ThreadedCall], iterated_mid_discovery: bool) -> str:
    """Why the race test failed: whether the second caller waited, what discovery reported, every traceback."""
    if iterated_mid_discovery:
        verdict = "the second caller walked the catalogue while the first was still importing plugin_b: it did not wait for the discovery in progress"
    else:
        verdict = f"the second caller did not reach the catalogue within {_LATE_CALLER_GRACE_SECONDS}s: it waited for the discovery in progress"
    lines = [verdict, f"discovery errors: {lab.registry.get_discovery_errors()!r}"]
    lines += [f"{call.thread.name} raised:\n{call.trace}" for call in calls if call.error is not None]
    return "\n".join(lines)


def test_concurrent_caller_during_cold_discovery_waits_for_the_full_catalogue(plugin_lab, tmp_path):
    """V1: a caller arriving while another thread is still discovering waits, then sees every plugin.

    The live HTTP 500: two parallel uploads right after server start, on a cold BRIM catalogue. Here the first
    caller is inside plugin_b's import (parked on a gate, after plugin_a registered) when the second calls in.
    Unguarded, the second skips every module already in sys.modules (each is inserted before it runs), declares
    discovery done and walks the live catalogue while the first is still registering: `RuntimeError: dictionary
    changed size during iteration` (the 500), or, silently, a partial catalogue (an upload then keeps an incomplete
    `compatible_plugins` for good). Fixed, it waits on the registry lock and both callers see [A, B].
    """
    lab = plugin_lab
    gates = lab.harness.gates = _RaceGates()
    lab.write_plugin("plugin_a", _RACE_PLUGIN_A)
    lab.write_plugin("plugin_b", _RACE_PLUGIN_B)
    statement = tmp_path / "statement.xlsx"
    statement.write_bytes(b"never read: every race plugin accepts any file")
    first = _ThreadedCall("registry-race-first", lambda: lab.registry.get_compatible_plugins(statement))
    second = _ThreadedCall("registry-race-second", lambda: lab.registry.get_compatible_plugins(statement))
    gates.late_caller = second.thread
    try:
        first.start()
        assert gates.b_import_started.wait(_WAIT_SECONDS), "the first caller never reached plugin_b: discovery did not run"
        # Verified, not inferred: discovery is mid-flight, plugin_a registered and plugin_b still importing.
        assert gates.a_registered.is_set(), "plugin_b is importing but plugin_a never registered"
        assert not gates.b_registered.is_set(), "plugin_b registered before the test released it"
        second.start()
        # Release plugin_b as soon as the second caller is walking the catalogue (the defect), or once the grace runs
        # out without it getting there (the fix: it is waiting for the discovery in progress).
        iterated_mid_discovery = gates.late_caller_iterating.wait(timeout=_LATE_CALLER_GRACE_SECONDS)
        gates.release_b.set()
        first.finish()
        second.finish()
    finally:
        gates.release_everything()

    full_catalogue = ["race_a", "race_b"]  # get_compatible_plugins orders by detection_priority, descending: 200, 100
    outcomes = {"first": first.outcome, "second": second.outcome}
    expected = {"first": ("returned", full_catalogue), "second": ("returned", full_catalogue)}
    assert outcomes == expected, _race_diagnosis(lab, [first, second], iterated_mid_discovery)


def test_plugin_calling_back_into_its_registry_during_discovery_does_not_deadlock(plugin_lab):
    """Guard for V1: discovery stays re-entrant on its own thread (green before the fix and after it).

    A plugin module that queries its own registry while discovery is importing it re-enters `auto_discover` on the
    discovering thread. Unlocked, that just works; under a per-registry lock it works only if the lock is re-entrant.
    Discovery runs on a daemon thread with a bounded join, so a regression fails here instead of hanging the suite.
    """
    lab = plugin_lab
    lab.harness.seen_by_callback = None
    lab.write_plugin("plugin_a_reentrant", _REENTRANT_PLUGIN)
    lab.write_plugin("plugin_b_after", _PLUGIN_AFTER_REENTRANT)

    discovery = _ThreadedCall("registry-reentrant-discovery", lab.registry.list_plugin_codes).start()
    discovery.finish(hung="discovery deadlocked: a plugin calling back into its own registry while being imported never got an answer")

    assert discovery.error is None, discovery.trace
    errors = lab.registry.get_discovery_errors()
    assert errors == (), f"a plugin module failed to import: {errors!r}"
    assert sorted(discovery.result) == ["after_reentrant", "reentrant"]
    assert "reentrant" in lab.harness.seen_by_callback


class _CataloguePlugin:
    """A plain plugin answering whatever the five catalogue iterations ask of one."""

    provider_code = "unset"
    provider_name = "unset"
    detection_priority = 100

    def can_parse(self, file_path: Path) -> bool:
        return True

    def to_plugin_info(self) -> DummyPluginInfo:
        return DummyPluginInfo(code=self.provider_code, name=self.provider_name)

    def shutdown(self) -> None:
        """Nothing to release."""


# The five places that walk a registry's catalogue (§19.6); each instantiates every plugin inside its loop.
_CATALOGUE_ITERATIONS: dict[str, Callable[[type[BRIMProviderRegistry], Path], object]] = {
    "list_providers": lambda registry, statement: registry.list_providers(),
    "shutdown_all_providers": lambda registry, statement: registry.shutdown_all_providers(),
    "auto_detect_plugin": lambda registry, statement: registry.auto_detect_plugin(statement),
    "get_compatible_plugins": lambda registry, statement: registry.get_compatible_plugins(statement),
    "list_plugin_info": lambda registry, statement: registry.list_plugin_info(),
}


@pytest.mark.parametrize("site", list(_CATALOGUE_ITERATIONS))
def test_catalogue_iteration_survives_a_registration_on_another_thread(plugin_lab, tmp_path, site):
    """V1, the snapshot half: every site that walks the catalogue walks a copy of it.

    After discovery, a plugin registered on another thread while `site` is mid-loop must not break that loop. Today
    the five sites walk the live storage dict and raise `RuntimeError: dictionary changed size during iteration`.
    The re-detection of changed plugins chosen in §19.5 will make such a late registration an ordinary event.
    """
    lab = plugin_lab
    lab.registry.auto_discover()  # the plugin folder is empty: discovery is over before the catalogue fills
    iterating, late_registered = threading.Event(), threading.Event()
    statement = tmp_path / "statement.csv"
    iterator = _ThreadedCall(f"registry-iteration-{site}", lambda: _CATALOGUE_ITERATIONS[site](lab.registry, statement))

    @register_provider(lab.registry)
    class HeldPlugin(_CataloguePlugin):
        provider_code = "held"
        provider_name = "Plugin the iteration is holding"

        def __init__(self):
            # The five sites instantiate each plugin inside their loop: hold the iterating thread right there, once,
            # until the late plugin has registered (registration instantiates it too, on the test's own thread).
            if threading.current_thread() is iterator.thread and not iterating.is_set():
                iterating.set()
                late_registered.wait(timeout=_WAIT_SECONDS)

    class LatePlugin(_CataloguePlugin):
        provider_code = "late"
        provider_name = "Plugin registered mid-iteration"

    try:
        iterator.start()
        assert iterating.wait(_WAIT_SECONDS), f"{site} never instantiated a plugin on its own thread"
        register_provider(lab.registry)(LatePlugin)
    finally:
        late_registered.set()
    iterator.finish()

    assert iterator.error is None, f"{site} walked the live catalogue, and a registration on another thread broke it: {iterator.outcome}\n{iterator.trace}"
    assert sorted(lab.registry.list_plugin_codes()) == ["held", "late"]
