"""X-R44 (workstream X): a test-only provider is served outside test mode.

Measured before the cure (read at 2ea54ff76). ``test_only = True`` marks the provider doubles the image ships with the
application (the Dockerfile copies ``backend/``, ``.dockerignore`` leaves out only ``backend/test_scripts/``): ``mockprov``
(``asset_source_providers/mockprov/plugin.py``: 100 USD every day, a fixed description and distribution, any query
answered), ``MOCKFX`` (``fx_providers/mockfx/plugin.py``: 1.2345 for every day and every currency) and ``MOCKFX_FAIL`` (a
simulated failure). The flag only hides them from the lists a user reads: ``GET /assets/provider``
(``api/v1/assets/providers.py``), ``GET /fx/providers`` (``api/v1/fx/providers.py``), a search that names no provider
(``_default_search_codes``, ``services/assets/search.py``) and the plugin settings catalogue asked for every plugin. The
registries (``services/provider_registry.py``: ``get_plugin``, ``get_plugin_instance`` / ``get_provider_instance``,
``list_plugin_codes``, ``list_providers``) serve them whatever the mode, and so does everything built on them: a search
that names ``mockprov``; ``POST /assets/provider``, whose ``FAProviderConfigBase.validate_provider_params_with_plugin``
only checks that the code is registered; the probe; the refresh, the current price and the metadata, through
``core.configured_provider``; the plugin settings catalogue asked for the plugin by name; a conversion route naming
``MOCKFX`` (``POST /fx/providers/routes`` checks the codes of ``list_providers()``), synced through
``configured_fx_provider``. On a production instance any user can give a global asset, shared by every user, a fake
series at 100 USD a day, or fill the FX rates every conversion reads with 1.2345.

The cure's contract (X-R44), in the registry base (``provider_registry.py``):

* outside test mode (``is_test_mode()`` false) a plugin class whose ``test_only`` is ``True`` does not exist:
  ``get_plugin(code)`` is ``None``, and so are ``get_plugin_instance`` and ``get_provider_instance``;
  ``list_plugin_codes()`` and ``list_providers()`` leave it out;
* in test mode nothing changes: the suites keep their doubles;
* a class without ``test_only``, or with it false, is never affected, in any family.

Its consequences, with no more code: ``core.configured_provider("mockprov")`` and ``configured_fx_provider("MOCKFX")``
are ``None``, as for a code no registry knows (a search skips the code, a refresh answers «Provider not found», a sync
«Unknown provider»); ``FAProviderAssignmentItem`` and ``FAProviderProbeRequest`` naming ``mockprov`` are refused «Unknown
provider code: mockprov», a 422 at the route, exactly as an unknown code is.

Reds («Red today», what a user of a production instance faces before the cure), outside test mode: each double
(``mockprov``, ``MOCKFX``, ``MOCKFX_FAIL``) is answered by none of the doors of its registry; its family runtime
configures no provider for it; an assignment and a probe naming ``mockprov`` are refused as an unknown code is; in a
registry of the base of this file's own, a class flagged ``test_only`` does not exist. Guards («Guard: green today and
after»): in test mode, every double is served, configured and validated as today; outside test mode, a real provider
(``yfinance``, ``justetf``, the FX ``ECB``) is served through every door and configured, and its assignment and probe
validate; the signal registry, a family without the flag, serves the same codes and classes as in test mode; a class
without the flag, or with it false, is served by the registry of this file's own in both modes.

X-R44c, a guard (green today and after): only an asset or an FX plugin may be flagged ``test_only``. Their registries
serve a plugin only through the base doors, which ask ``_withheld``; the other families also serve theirs through doors of
their own that never ask it (read at 9e8f6e8dc): ``BRIMProviderRegistry``'s ``auto_detect_plugin``,
``get_compatible_plugins`` and ``list_plugin_info`` walk ``_providers``, ``SignalPluginRegistry.list_definitions()`` and
``RiskAnalyticRegistry.list_definitions()`` walk ``_plugins``, ``ToolPluginRegistry`` serves its own snapshot
(``get_snapshot``, ``get_definition``, its own ``get_plugin_instance``). Flagged there — their bases do not inherit the
mixin that declares the flag, but the base doors read it on any class — a plugin would vanish from the base doors and still
be served, on a production instance, through those: whoever flags one covers its family's doors first. The rule is read in
test mode, through the base doors, over every registry of the base the application defines (each family's
``registry.py`` imported, the subclasses of ``AbstractPluginRegistry`` walked), so a seventh family is checked with no
edit here; a second guard proves that the check reads the flag and the registry, on the registry of the base of this
file's own.

The simulation. The runner runs every pytest process with ``LIBREFOLIO_TEST_MODE=1``, and ``is_test_mode()`` reads the
variable at each call. Each test sets it to ``1`` through ``monkeypatch``, as every run does, with a barrier that
``is_test_mode()`` reads it; where it needs a production instance it enters a block (``monkeypatch.context()``) that sets
``LIBREFOLIO_TEST_MODE=0``, with a barrier that ``is_test_mode()`` is false, and that puts the variable back on leaving
it, whatever happens inside. The first lookup of every test is made in test mode, so the plugins are discovered there,
as the application discovers them, once per process. An absence is asserted only after a presence: a red first proves,
in test mode, that its code names the double through every door (the FX registry looks a code up as written:
``MOCKFX``, never ``mockfx``) and that the double carries the flag, or that its body validates.

Isolation: PURE, in process. Nothing here reaches the lane server, the database or the network. The application's
registries are only read; the registry of the base built here is a subclass of its own, with its own storage and a
plugin folder that does not exist. The binding of the plugin settings (``configure_instance``) reads the database — the
production one, outside test mode, when the engine is not built yet — so it is replaced through ``monkeypatch``, in both
family runtimes and at its source, by a recorder: these tests ask whether a provider is handed out at all, never what it
is bound to.
"""

from __future__ import annotations

import importlib
from collections.abc import Awaitable, Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from backend.app.config import PROJECT_ROOT, is_test_mode
from backend.app.schemas.provider import FAProviderAssignmentItem, FAProviderConfigBase, FAProviderProbeRequest
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets import core as asset_core
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.fx import runtime as fx_runtime
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx_providers.mockfx.plugin import MockFXFailProvider, MockFXProvider
from backend.app.services.plugin_settings import runtime as settings_runtime
from backend.app.services.provider_registry import AbstractPluginRegistry, AbstractProviderRegistry
from backend.app.services.risk.registry import RiskAnalyticRegistry
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.services.tools.registry import ToolPluginRegistry

TEST_MODE_VARIABLE = "LIBREFOLIO_TEST_MODE"
#: A code no registry knows: what the contract makes a test-only code look like outside test mode.
UNKNOWN_CODE = "x_r44_no_such_provider"
#: The plugin folder of the registry of the base built here: it must not exist (``_probe_registry``).
PROBE_FOLDER = "x_r44_probe_registry_without_folder"
#: Codes the application's signal registry holds: a floor proving it is that registry, its plugins discovered.
SIGNAL_FLOOR = frozenset({"EMA", "SMA", "RSI", "MACD", "BOLLINGER"})


# ─────────────────────────────────────────────────────────────────────────────
# The providers, the routes and the registry of the base addressed here
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Provider:
    """A provider as these tests address it: its family, its registry, its code and the family runtime that configures it.
    For a double, ``plugin`` is its class and ``faces`` what a production instance does with it before the cure."""

    family: str
    registry: type[AbstractProviderRegistry]
    code: str
    configure: Callable[[str], Awaitable[object]]
    plugin: type | None = None
    faces: str = ""


MOCKPROV = _Provider(
    "asset",
    AssetProviderRegistry,
    "mockprov",
    asset_core.configured_provider,
    MockProvider,
    "On a production instance, which ships the double, any user can name it in a search, assign it to an asset (POST /api/v1/assets/provider) and probe it (POST /api/v1/assets/provider/probe); the asset, global and shared by every user, is then refreshed, priced and described by it: a fake series at 100 USD a day.",
)
MOCKFX = _Provider(
    "fx",
    FXProviderRegistry,
    "MOCKFX",
    fx_runtime.configured_fx_provider,
    MockFXProvider,
    "On a production instance, which ships the double, a conversion route naming MOCKFX is accepted (POST /api/v1/fx/providers/routes checks the codes of list_providers()) and every sync of it writes 1.2345, for every day and every currency, into the FX rates every user's conversions read.",
)
MOCKFX_FAIL = _Provider(
    "fx",
    FXProviderRegistry,
    "MOCKFX_FAIL",
    fx_runtime.configured_fx_provider,
    MockFXFailProvider,
    "On a production instance, which ships the double, a conversion route naming MOCKFX_FAIL is accepted (POST /api/v1/fx/providers/routes checks the codes of list_providers()) and every sync of it fails with a simulated provider error.",
)
DOUBLES = (MOCKPROV, MOCKFX, MOCKFX_FAIL)
#: Real providers: ``test_only`` false, the default of their family base (``PluginSettingsMixin``).
REAL_PROVIDERS = (
    _Provider("asset", AssetProviderRegistry, "yfinance", asset_core.configured_provider),
    _Provider("asset", AssetProviderRegistry, "justetf", asset_core.configured_provider),
    _Provider("fx", FXProviderRegistry, "ECB", fx_runtime.configured_fx_provider),
)
#: A valid configuration of each real asset provider: (code, identifier, identifier type).
REAL_CONFIGURATIONS = (("yfinance", "AAPL", "TICKER"), ("justetf", "IE00B4L5Y983", "ISIN"))


def _provider_id(provider: _Provider) -> str:
    return f"{provider.family}-{provider.code}"


@dataclass(frozen=True)
class _Route:
    """A route whose body carries a provider configuration (``FAProviderConfigBase``), validated as the route validates it:
    ``rest`` gives the other fields of the body, valid."""

    name: str
    model: type[FAProviderConfigBase]
    path: str
    rest: Callable[[], dict[str, object]]

    def body(self, code: str, identifier: str = "X", identifier_type: str = "TICKER") -> dict[str, object]:
        """A body valid in every field but, perhaps, its provider."""
        return {**self.rest(), "provider_code": code, "identifier": identifier, "identifier_type": identifier_type, "provider_params": None}


ROUTES = (
    _Route("assignment", FAProviderAssignmentItem, "POST /api/v1/assets/provider (one assignment of its list)", lambda: {"asset_id": 1}),
    _Route("probe", FAProviderProbeRequest, "POST /api/v1/assets/provider/probe", lambda: {"operations": ["current_price"]}),
)


def _route_id(route: _Route) -> str:
    return route.name


@dataclass(frozen=True)
class _Probe:
    """A registry of the base of this file's own and its three classes, one per state of the flag."""

    registry: type[AbstractPluginRegistry]
    without_flag: type
    flag_false: type
    flag_true: type


def _probe_registry() -> _Probe:
    """A new registry of the base, declared as every family declares one (a subclass: its own storage,
    ``__init_subclass__``), whose plugin folder does not exist: its discovery finds nothing, so it holds the three classes
    registered here and nothing else. Never one of the application's registries."""

    class ProbeRegistry(AbstractPluginRegistry):
        @classmethod
        def _get_plugin_folder(cls) -> str:
            return PROBE_FOLDER

    class WithoutFlag:
        plugin_code = "WITHOUT_FLAG"

    class FlagFalse:
        plugin_code = "FLAG_FALSE"
        test_only = False

    class FlagTrue:
        plugin_code = "FLAG_TRUE"
        test_only = True

    folder = ProbeRegistry._get_plugin_directory()
    assert not folder.exists(), f"barrier: {folder} exists: the discovery of the probe registry would import what is there, and the registry would hold more than its three classes"
    for plugin_class in (WithoutFlag, FlagFalse, FlagTrue):
        ProbeRegistry.register(plugin_class)
    return _Probe(ProbeRegistry, WithoutFlag, FlagFalse, FlagTrue)


# ─────────────────────────────────────────────────────────────────────────────
# The two modes, the doors of a registry, the binding of the settings
# ─────────────────────────────────────────────────────────────────────────────


def _test_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test mode for the whole test, as the runner runs every pytest process; the barrier proves ``is_test_mode()`` reads it."""
    monkeypatch.setenv(TEST_MODE_VARIABLE, "1")
    assert is_test_mode() is True, f"barrier: with {TEST_MODE_VARIABLE}=1 is_test_mode() is false: the test cannot stand for a test run, where the doubles stay"


@contextmanager
def _production(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A production instance for the length of the block: ``LIBREFOLIO_TEST_MODE=0``, put back on leaving it, whatever
    happens inside."""
    with monkeypatch.context() as patch:
        patch.setenv(TEST_MODE_VARIABLE, "0")
        assert is_test_mode() is False, f"barrier: with {TEST_MODE_VARIABLE}=0 is_test_mode() is still true: the block does not stand for a production instance, and the cure keys on is_test_mode()"
        yield


def _class_of(instance: object) -> type | None:
    return None if instance is None else type(instance)


def _doors(registry: type[AbstractPluginRegistry], code: str) -> dict[str, object]:
    """What every way into ``registry`` answers for ``code``: the class it looks up and the class of the instance it makes
    (``None``: nothing), and whether each listing holds the code; ``get_provider_instance`` and ``list_providers()`` for a
    provider registry."""
    doors: dict[str, object] = {
        "get_plugin": registry.get_plugin(code),
        "get_plugin_instance": _class_of(registry.get_plugin_instance(code)),
        "list_plugin_codes": code in registry.list_plugin_codes(),
    }
    if issubclass(registry, AbstractProviderRegistry):
        doors["get_provider_instance"] = _class_of(registry.get_provider_instance(code))
        doors["list_providers"] = code in [entry["code"] for entry in registry.list_providers()]
    return doors


def _expected(registry: type[AbstractPluginRegistry], plugin: type | None) -> dict[str, object]:
    """``_doors`` of a code that names ``plugin`` through every door or, for ``None``, through none."""
    named = plugin is not None
    expected: dict[str, object] = {"get_plugin": plugin, "get_plugin_instance": plugin, "list_plugin_codes": named}
    if issubclass(registry, AbstractProviderRegistry):
        expected["get_provider_instance"] = plugin
        expected["list_providers"] = named
    return expected


def _render(doors: dict[str, object]) -> str:
    """The answers of the doors, a class by its name."""
    return ", ".join(f"{door}: {getattr(answer, '__name__', answer)}" for door, answer in doors.items())


def _barrier_the_double_is_registered(double: _Provider) -> None:
    """In test mode the code names the double through every door, and the double carries the flag: an absence outside test
    mode is then the cure's doing, never a misspelt code."""
    assert double.plugin is not None and getattr(double.plugin, "test_only", None) is True, f"barrier: {double.plugin!r} is not flagged test_only = True: the contract would not hide it"
    doors = _doors(double.registry, double.code)
    assert doors == _expected(double.registry, double.plugin), f"barrier: in test mode {double.registry.__name__} answers {_render(doors)} for {double.code!r}, not {double.plugin.__name__} through every door: its absence outside test mode would mean nothing"


def _barrier_a_real_provider(provider: _Provider) -> type:
    """In test mode the code names one class through every door, a class whose ``test_only`` is false; returned."""
    doors = _doors(provider.registry, provider.code)
    plugin = doors["get_plugin"]
    assert isinstance(plugin, type) and getattr(plugin, "test_only", False) is False and doors == _expected(provider.registry, plugin), f"barrier: in test mode {provider.registry.__name__} answers {_render(doors)} for {provider.code!r}: not a provider served through every door with test_only false"
    return plugin


class _Binding:
    """Stands for ``configure_instance``: records each call as (the instance's class, the family, the user) and hands the
    instance back as it came, with no database read."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int | None]] = []

    async def __call__(self, instance: object, family: str, *, user_id: int | None = None) -> object:
        self.calls.append((type(instance).__name__, family, user_id))
        return instance


@pytest.fixture
def binding(monkeypatch: pytest.MonkeyPatch) -> _Binding:
    """``configure_instance`` replaced by a recorder in both family runtimes (``assets/core.py``, ``fx/runtime.py``) and at
    its source (``plugin_settings/runtime.py``), for a caller that would reach it through its module."""
    recorder = _Binding()
    for module in (asset_core, fx_runtime, settings_runtime):
        monkeypatch.setattr(module, "configure_instance", recorder)
    return recorder


def _refusal(route: _Route, body: dict[str, object]) -> list[tuple[str, tuple, str]] | None:
    """What the model of ``route`` refuses ``body`` with, as (type, location, message) per error; ``None`` when it validates."""
    try:
        route.model.model_validate(body)
    except ValidationError as error:
        return [(entry["type"], tuple(entry["loc"]), entry["msg"]) for entry in error.errors()]
    return None


def _as_the_unknown_code(refusal: list[tuple[str, tuple, str]] | None, code: str) -> list[tuple[str, tuple, str]]:
    """The refusal of the unknown code with ``code`` in its place: what the contract refuses ``code`` with. Barrier: the
    unknown code is refused, as an unknown provider."""
    assert refusal is not None and any(f"Unknown provider code: {UNKNOWN_CODE}" in message for _kind, _location, message in refusal), f"barrier: a body naming the unknown code {UNKNOWN_CODE!r} is refused with {refusal}, not «Unknown provider code»: the comparison would mean nothing"
    return [(kind, location, message.replace(UNKNOWN_CODE, code)) for kind, location, message in refusal]


# ─────────────────────────────────────────────────────────────────────────────
# Reds: outside test mode, a class flagged test_only does not exist
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("double", DOUBLES, ids=_provider_id)
def test_outside_test_mode_the_registry_does_not_serve_the_test_double(monkeypatch: pytest.MonkeyPatch, double: _Provider) -> None:
    """Red today (X-R44): outside test mode the registry serves the double through every door, as in test mode — the
    class, an instance, both listings — so a production instance takes it as a source: ``mockprov`` for an asset,
    ``MOCKFX`` or ``MOCKFX_FAIL`` for a conversion route.

    Contract: outside test mode ``get_plugin``, ``get_plugin_instance`` and ``get_provider_instance`` are ``None`` for its
    code, and neither ``list_plugin_codes()`` nor ``list_providers()`` holds it. Barrier: in test mode the code names the
    double through every door, and the double carries the flag.
    """
    _test_mode(monkeypatch)
    _barrier_the_double_is_registered(double)
    with _production(monkeypatch):
        doors = _doors(double.registry, double.code)
    expected = _expected(double.registry, None)
    assert doors == expected, f"Red today (X-R44): outside test mode {double.registry.__name__} still serves the test double {double.code!r} ({_render(doors)}). {double.faces} The contract: a class flagged test_only does not exist there ({_render(expected)})."


@pytest.mark.asyncio
@pytest.mark.parametrize("double", DOUBLES, ids=_provider_id)
async def test_outside_test_mode_the_family_runtime_configures_no_test_double(monkeypatch: pytest.MonkeyPatch, binding: _Binding, double: _Provider) -> None:
    """Red today (X-R44): outside test mode ``core.configured_provider`` and ``configured_fx_provider`` hand the double out,
    its settings bound, to every caller that asks for it by code: a search that names it, the probe, the refresh, the
    current price, the metadata, the sync of a conversion route.

    Contract: ``None``, as for a code no registry knows, and no binding of its plugin settings. Barriers: in test mode
    the code names the double; outside test mode the unknown code gives ``None``, with no binding.
    """
    _test_mode(monkeypatch)
    _barrier_the_double_is_registered(double)
    with _production(monkeypatch):
        unknown = await double.configure(UNKNOWN_CODE)
        bound_for_the_unknown_code = list(binding.calls)
        configured = await double.configure(double.code)
    runtime = double.configure.__name__
    assert unknown is None and bound_for_the_unknown_code == [], f"barrier: outside test mode {runtime}({UNKNOWN_CODE!r}) gives {unknown!r}, the binding called as {bound_for_the_unknown_code}: an unknown code does not give None, the comparison would mean nothing"
    assert (
        configured is None and binding.calls == []
    ), f"Red today (X-R44): outside test mode {runtime}({double.code!r}) hands out a {type(configured).__name__}, its plugin settings bound ({binding.calls}). {double.faces} The contract: None, as for the unknown code {UNKNOWN_CODE!r}, with no binding."


@pytest.mark.parametrize("route", ROUTES, ids=_route_id)
def test_outside_test_mode_a_mockprov_configuration_is_refused_as_an_unknown_provider(monkeypatch: pytest.MonkeyPatch, route: _Route) -> None:
    """Red today (X-R44): outside test mode the body validates — the schema only checks that the code is registered — so
    any user of a production instance assigns the double to a global asset, or probes it.

    Contract: refused exactly as a body naming a code no registry knows, «Unknown provider code: mockprov» (a 422 at the
    route). Barriers: in test mode the same body validates, so it is valid in every field but its provider; the unknown
    code is refused as an unknown provider.
    """
    _test_mode(monkeypatch)
    body = route.body(MOCKPROV.code)
    in_test_mode = _refusal(route, body)
    assert in_test_mode is None, f"barrier: in test mode {route.model.__name__} refuses {body} with {in_test_mode}: the body is not valid apart from its provider, a refusal outside test mode would not be the provider's doing"
    with _production(monkeypatch):
        unknown = _refusal(route, route.body(UNKNOWN_CODE))
        refusal = _refusal(route, body)
    expected = _as_the_unknown_code(unknown, MOCKPROV.code)
    assert refusal is not None, f"Red today (X-R44): outside test mode {route.path} accepts {body}. {MOCKPROV.faces} The contract: refused as a code no registry knows, {expected} (a 422 at the route)."
    assert refusal == expected, f"outside test mode {route.path} refuses {body}, but not as a code no registry knows: {refusal}, not {expected}"


def test_outside_test_mode_a_class_flagged_test_only_does_not_exist_in_a_registry_of_the_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """Red today (X-R44): the flag hides nothing in the registry base: a class flagged ``test_only`` is served outside test
    mode as in test mode, and a test double of any family — a signal, an analytic, a tool — would reach a production
    instance as the provider doubles do.

    Contract: outside test mode it does not exist, in any registry of the base: ``get_plugin`` and
    ``get_plugin_instance`` ``None``, ``list_plugin_codes()`` without its code. Barrier: in test mode the registry serves
    it through every door.
    """
    _test_mode(monkeypatch)
    probe = _probe_registry()
    code = probe.flag_true.plugin_code
    in_test_mode = _doors(probe.registry, code)
    assert in_test_mode == _expected(probe.registry, probe.flag_true), f"barrier: in test mode the probe registry answers {_render(in_test_mode)} for {code!r}, not {probe.flag_true.__name__} through every door: its absence outside test mode would mean nothing"
    with _production(monkeypatch):
        outside = _doors(probe.registry, code)
    expected = _expected(probe.registry, None)
    assert (
        outside == expected
    ), f"Red today (X-R44): outside test mode a registry of the base still serves {probe.flag_true.__name__}, flagged test_only = True ({_render(outside)}): the flag hides nothing in the base, and a test double of any family would reach a production instance as the provider doubles do. The contract: it does not exist there ({_render(expected)})."


# ─────────────────────────────────────────────────────────────────────────────
# Guards: green before and after the cure
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("double", DOUBLES, ids=_provider_id)
def test_guard_in_test_mode_the_registry_serves_the_test_double(monkeypatch: pytest.MonkeyPatch, double: _Provider) -> None:
    """Guard: green today and after. In test mode, as every run, the registry serves the double through every door: the
    suites keep the doubles they run on."""
    _test_mode(monkeypatch)
    doors = _doors(double.registry, double.code)
    expected = _expected(double.registry, double.plugin)
    assert doors == expected, f"in test mode {double.registry.__name__} answers {_render(doors)} for {double.code!r}, not {_render(expected)}: the suites lose the double they run on"


@pytest.mark.asyncio
@pytest.mark.parametrize("double", DOUBLES, ids=_provider_id)
async def test_guard_in_test_mode_the_family_runtime_configures_the_test_double(monkeypatch: pytest.MonkeyPatch, binding: _Binding, double: _Provider) -> None:
    """Guard: green today and after. In test mode the family runtime hands out a new instance of the double, bound once,
    for its family and no user."""
    _test_mode(monkeypatch)
    configured = await double.configure(double.code)
    expected_calls = [(double.plugin.__name__, double.family, None)]
    assert type(configured) is double.plugin and binding.calls == expected_calls, f"in test mode {double.configure.__name__}({double.code!r}) hands out {configured!r}, the binding called as {binding.calls}: not a {double.plugin.__name__} bound as {expected_calls}"


@pytest.mark.parametrize("route", ROUTES, ids=_route_id)
def test_guard_in_test_mode_a_mockprov_configuration_validates(monkeypatch: pytest.MonkeyPatch, route: _Route) -> None:
    """Guard: green today and after. In test mode an assignment and a probe naming ``mockprov`` validate, as the suites send
    them."""
    _test_mode(monkeypatch)
    body = route.body(MOCKPROV.code)
    refusal = _refusal(route, body)
    assert refusal is None, f"in test mode {route.path} refuses {body} with {refusal}: the suites send it, and it validates today"


@pytest.mark.parametrize("provider", REAL_PROVIDERS, ids=_provider_id)
def test_guard_outside_test_mode_the_registry_serves_a_real_provider(monkeypatch: pytest.MonkeyPatch, provider: _Provider) -> None:
    """Guard: green today and after. Outside test mode a real provider, its ``test_only`` false, is served through every
    door, as in test mode."""
    _test_mode(monkeypatch)
    plugin = _barrier_a_real_provider(provider)
    with _production(monkeypatch):
        doors = _doors(provider.registry, provider.code)
    expected = _expected(provider.registry, plugin)
    assert doors == expected, f"outside test mode {provider.registry.__name__} answers {_render(doors)} for the real provider {provider.code!r}, not {_render(expected)}: a production instance loses it"


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", REAL_PROVIDERS, ids=_provider_id)
async def test_guard_outside_test_mode_the_family_runtime_configures_a_real_provider(monkeypatch: pytest.MonkeyPatch, binding: _Binding, provider: _Provider) -> None:
    """Guard: green today and after. Outside test mode the family runtime hands out a new instance of a real provider,
    bound once, for its family and no user."""
    _test_mode(monkeypatch)
    plugin = _barrier_a_real_provider(provider)
    with _production(monkeypatch):
        configured = await provider.configure(provider.code)
    expected_calls = [(plugin.__name__, provider.family, None)]
    assert type(configured) is plugin and binding.calls == expected_calls, f"outside test mode {provider.configure.__name__}({provider.code!r}) hands out {configured!r}, the binding called as {binding.calls}: not a {plugin.__name__} bound as {expected_calls}"


@pytest.mark.parametrize(("code", "identifier", "identifier_type"), REAL_CONFIGURATIONS, ids=[configuration[0] for configuration in REAL_CONFIGURATIONS])
@pytest.mark.parametrize("route", ROUTES, ids=_route_id)
def test_guard_outside_test_mode_a_real_provider_configuration_validates(monkeypatch: pytest.MonkeyPatch, route: _Route, code: str, identifier: str, identifier_type: str) -> None:
    """Guard: green today and after. Outside test mode an assignment and a probe naming a real provider validate, as in
    test mode."""
    _test_mode(monkeypatch)
    body = route.body(code, identifier, identifier_type)
    in_test_mode = _refusal(route, body)
    assert in_test_mode is None, f"barrier: in test mode {route.path} refuses {body} with {in_test_mode}: the body is not valid, its validation outside test mode would mean nothing"
    with _production(monkeypatch):
        refusal = _refusal(route, body)
    assert refusal is None, f"outside test mode {route.path} refuses {body} with {refusal}: a production instance can no longer assign or probe the real provider {code!r}"


def test_guard_outside_test_mode_the_signal_registry_serves_what_it_serves_in_test_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard: green today and after. The signal registry, a family whose plugins carry no ``test_only``, lists the same
    codes, in the same order, and looks up the same classes outside test mode as in test mode."""
    _test_mode(monkeypatch)
    codes = SignalPluginRegistry.list_plugin_codes()
    plugins = {code: SignalPluginRegistry.get_plugin(code) for code in codes}
    assert SIGNAL_FLOOR <= set(codes) and None not in plugins.values(), f"barrier: in test mode the signal registry lists {codes} and looks them up as {plugins}: not the application's registry, its plugins discovered"
    flagged = sorted(code for code, plugin in plugins.items() if getattr(plugin, "test_only", False))
    assert flagged == [], f"barrier: the signal plugins {flagged} carry test_only: the family is not one without the flag"
    with _production(monkeypatch):
        codes_outside = SignalPluginRegistry.list_plugin_codes()
        plugins_outside = {code: SignalPluginRegistry.get_plugin(code) for code in codes}
    assert codes_outside == codes, f"outside test mode the signal registry lists {codes_outside}, in test mode {codes}: a family without the flag is affected"
    assert plugins_outside == plugins, f"outside test mode the signal registry looks the codes up as {plugins_outside}, in test mode as {plugins}: a family without the flag is affected"


def test_guard_a_class_without_the_flag_or_with_it_false_is_served_in_both_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard: green today and after. In a registry of the base, a class without ``test_only`` and a class whose
    ``test_only`` is false are served through every door, in test mode and outside it."""
    _test_mode(monkeypatch)
    probe = _probe_registry()
    expected = {plugin.plugin_code: _expected(probe.registry, plugin) for plugin in (probe.without_flag, probe.flag_false)}
    in_test_mode = {code: _doors(probe.registry, code) for code in expected}
    with _production(monkeypatch):
        outside = {code: _doors(probe.registry, code) for code in expected}
    assert in_test_mode == expected, f"in test mode the probe registry answers {in_test_mode}, not {expected}"
    assert outside == expected, f"outside test mode the probe registry answers {outside}, not {expected}: a class without the flag, or with it false, is affected"


# ─────────────────────────────────────────────────────────────────────────────
# X-R44c: a plugin is flagged test_only only where every door withholds it
# ─────────────────────────────────────────────────────────────────────────────

#: Where each family keeps its registry: ``services/<family>/registry.py`` (developer decision D-P1, ``provider_registry.py``).
SERVICES_PACKAGE = "backend.app.services"
SERVICES_DIRECTORY = PROJECT_ROOT / "backend" / "app" / "services"
REGISTRY_MODULE = "registry"
#: The registries of the base the application defines today: the walk finds at least these.
KNOWN_REGISTRIES: tuple[type[AbstractPluginRegistry], ...] = (AssetProviderRegistry, FXProviderRegistry, BRIMProviderRegistry, SignalPluginRegistry, RiskAnalyticRegistry, ToolPluginRegistry)
#: The families whose plugins may be flagged ``test_only``: their registries serve a plugin only through the base doors,
#: which ask ``_withheld``.
TEST_ONLY_FAMILIES: tuple[type[AbstractPluginRegistry], ...] = (AssetProviderRegistry, FXProviderRegistry)
#: The doors of the other families that serve a plugin without asking ``_withheld`` (read at 9e8f6e8dc).
UNGUARDED_DOORS: dict[type[AbstractPluginRegistry], str] = {
    BRIMProviderRegistry: "auto_detect_plugin, get_compatible_plugins and list_plugin_info walk _providers",
    SignalPluginRegistry: "list_definitions() walks _plugins",
    RiskAnalyticRegistry: "list_definitions() walks _plugins",
    ToolPluginRegistry: "get_snapshot, get_definition and its own get_plugin_instance serve the registry's own snapshot",
}


@dataclass(frozen=True)
class _Flagged:
    """A class flagged ``test_only`` as a registry serves it: the registry, the code it is served under, the class."""

    registry: type[AbstractPluginRegistry]
    code: str
    plugin: type


def _names_its_folder(registry: type[AbstractPluginRegistry]) -> bool:
    """Whether ``registry`` is a family's: it names the folder its plugins are discovered from. A base names none
    (``_get_plugin_folder`` raises ``NotImplementedError``), and no door of it can run."""
    try:
        registry._get_plugin_folder()
    except NotImplementedError:
        return False
    return True


def _first_party_registries() -> list[type[AbstractPluginRegistry]]:
    """Every registry of the base the application defines: each family's ``registry.py`` imported, then the subclasses
    of ``AbstractPluginRegistry`` walked to the last, keeping those defined under ``backend.app.services`` that name
    their plugin folder. Left out: the bases (``AbstractProviderRegistry``) and every registry of test code — this file's
    own, the labs and fixtures of the other suites a process may hold. A seventh family is found with no edit here."""
    for module_file in sorted(SERVICES_DIRECTORY.glob(f"*/{REGISTRY_MODULE}.py")):
        importlib.import_module(f"{SERVICES_PACKAGE}.{module_file.parent.name}.{REGISTRY_MODULE}")
    walked: set[type[AbstractPluginRegistry]] = set()
    pending: list[type[AbstractPluginRegistry]] = [AbstractPluginRegistry]
    while pending:
        for subclass in pending.pop().__subclasses__():
            if subclass not in walked:
                walked.add(subclass)
                pending.append(subclass)
    first_party = [registry for registry in walked if registry.__module__.startswith(f"{SERVICES_PACKAGE}.") and _names_its_folder(registry)]
    return sorted(first_party, key=lambda registry: (registry.__module__, registry.__qualname__))


def _served(registry: type[AbstractPluginRegistry]) -> dict[str, type]:
    """What ``registry`` serves through its own base doors: every code ``list_plugin_codes()`` lists, and the class
    ``get_plugin`` looks it up as. Barriers: read in test mode, where nothing is withheld; each listed code is a class."""
    assert is_test_mode() is True, f"barrier: {registry.__name__} read outside test mode, where its base doors withhold every class flagged test_only: the rule would see none"
    served = {code: registry.get_plugin(code) for code in registry.list_plugin_codes()}
    unread = {code: plugin for code, plugin in served.items() if not isinstance(plugin, type)}
    assert not unread, f"barrier: {registry.__name__} lists {sorted(unread)} but get_plugin looks them up as {unread}: the rule would read no class for them"
    return served


def _flagged_test_only(registries: Iterable[type[AbstractPluginRegistry]]) -> list[_Flagged]:
    """Every class flagged ``test_only`` the registries serve (``_served``), the flag read as ``_withheld`` reads it: an
    attribute any class may set, true when truthy, false when absent."""
    return [_Flagged(registry, code, plugin) for registry in registries for code, plugin in _served(registry).items() if getattr(plugin, "test_only", False)]


def _breaches(flagged: Iterable[_Flagged], allowed: tuple[type[AbstractPluginRegistry], ...] = TEST_ONLY_FAMILIES) -> list[_Flagged]:
    """The rule of X-R44c: the flagged classes served by a registry that is not one of ``allowed``."""
    return [entry for entry in flagged if entry.registry not in allowed]


def _render_breach(breach: _Flagged) -> str:
    """A breach as the guard tells it: the registry, the code, the class, and why the flag cannot stay there."""
    registry = breach.registry.__name__
    doors = UNGUARDED_DOORS.get(breach.registry)
    why = (
        f"{registry} has doors that do not withhold a test-only plugin — {doors}, never asking _withheld — and would still serve it on a production instance. Cover those doors first"
        if doors
        else f"{registry} is a family whose doors were never checked against X-R44: a door of its own may read its storage, or a snapshot, without asking _withheld, and serve it on a production instance. Check every door of the family first"
    )
    return f"{registry} serves {breach.code!r} as {breach.plugin.__module__}.{breach.plugin.__qualname__}, flagged test_only = True, but only an asset or an FX plugin may be (X-R44c). {why} (each must ask _withheld, as the base doors do), then add {registry} to TEST_ONLY_FAMILIES."


def test_guard_only_asset_and_fx_plugins_are_flagged_test_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard: green today and after. X-R44c: in test mode, where every plugin is served, no registry of the application
    but the asset and the FX ones serves a class flagged ``test_only``; every other family has doors that would still
    serve it on a production instance (``UNGUARDED_DOORS``). A seventh family is checked with no edit here.

    Barriers: the walk finds the six registries known today, and neither a base nor a registry of test code; each of the
    six serves a class; the flag is read where it lives: ``mockprov``, ``MOCKFX`` and ``MOCKFX_FAIL`` are found flagged
    (not as the only ones: a new asset or FX double is allowed).
    """
    _test_mode(monkeypatch)
    probe = _probe_registry()
    registries = _first_party_registries()
    missing = [registry.__name__ for registry in KNOWN_REGISTRIES if registry not in registries]
    assert not missing, f"barrier: the walk of the subclasses of AbstractPluginRegistry finds {[registry.__name__ for registry in registries]}, without {missing}: the rule would skip a family"
    strays = [registry.__name__ for registry in (AbstractProviderRegistry, probe.registry) if registry in registries]
    assert not strays, f"barrier: the walk takes in {strays}: a base, or a registry of test code, read as a family of the application"
    empty = [registry.__name__ for registry in KNOWN_REGISTRIES if not _served(registry)]
    assert not empty, f"barrier: in test mode {empty} serve no class through their doors: the rule would read nothing for their family"
    flagged = _flagged_test_only(registries)
    unseen = [double.code for double in DOUBLES if _Flagged(double.registry, double.code, double.plugin) not in flagged]
    assert not unseen, f"barrier: the rule does not find {unseen} flagged test_only, where the flag lives (it finds {flagged}): it does not read the attribute it guards"
    breaches = _breaches(flagged)
    assert breaches == [], "\n".join(_render_breach(breach) for breach in breaches)


def test_guard_the_test_only_rule_reports_a_flagged_class_outside_the_asset_and_fx_registries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard: green today and after. X-R44c: the check of the rule reads the flag and the registry. In a registry of the
    base of this file's own, neither the asset nor the FX one, it reports the class flagged ``test_only``, naming the
    registry, the code and the class, and neither the class without the flag nor the one with it false; with that
    registry counted among the allowed ones, it reports nothing. Without it, the rule could be green by reading nothing.

    Barrier: the check reads the three classes of the registry.
    """
    _test_mode(monkeypatch)
    probe = _probe_registry()
    served = _served(probe.registry)
    three = {plugin.plugin_code: plugin for plugin in (probe.without_flag, probe.flag_false, probe.flag_true)}
    assert served == three, f"barrier: the check reads {served} from the probe registry, not its three classes {three}: a class it leaves unreported would mean nothing"
    flagged = _flagged_test_only([probe.registry])
    expected = [_Flagged(probe.registry, probe.flag_true.plugin_code, probe.flag_true)]
    assert flagged == expected, f"the check finds {flagged} flagged test_only in the probe registry, not {expected}: it does not read the flag as _withheld does"
    breaches = _breaches(flagged)
    assert breaches == expected, f"outside the asset and FX registries the check reports {breaches}, not {expected}: a class flagged test_only would pass in a family whose doors do not withhold it"
    told = _render_breach(breaches[0])
    unnamed = [name for name in (probe.registry.__name__, repr(probe.flag_true.plugin_code), f"{probe.flag_true.__module__}.{probe.flag_true.__qualname__}") if name not in told]
    assert not unnamed, f"the breach is told as {told!r}, without {unnamed}: whoever meets it cannot find the plugin"
    allowed = _breaches(flagged, (*TEST_ONLY_FAMILIES, probe.registry))
    assert allowed == [], f"with the probe registry among the allowed ones the check still reports {allowed}: it does not read the registry, and would refuse the asset and FX doubles too"
