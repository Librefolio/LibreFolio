"""
Gate of plugin translation ownership (workstream U, step U-3): a plugin's keys live in its own fragment.

A plugin's fragment is ``backend/app/services/<family>/<plugin>/i18n/<lang>.json``, one of the sources
``scripts/i18n_catalog.py`` merges into the frontend catalogue (``utils gate-i18n-catalog``). A plugin is its folder,
``<family>/<folder>``, read from the module its class is loaded from, ``backend.app.services.<family>.<folder>.plugin``:
the name ``i18n_catalog`` gives its fragment. Each plugin has a **space**, read from the metadata its registry
publishes, never from its source text:

- BRIM (``BRIMProviderRegistry``): ``brimPlugins.<code>``, the key the UI builds (``brimPlugins.${plugin.code}.name``);
  and the code is the folder;
- asset (``AssetProviderRegistry``): ``assets.providerParams.<provider code>``;
- signal (``SignalPluginRegistry``, every registered plugin, in the catalogue or not): the parent of
  ``display_name_key``;
- risk (``RiskAnalyticRegistry``): the parent of ``name_i18n_key``;
- tool (``ToolPluginRegistry``): exactly the keys ``name_i18n_key`` and ``description_i18n_key``, whose namespace a
  subsystem shares;
- FX (``FXProviderRegistry``): none.

A space is **exclusive** when exactly one plugin has it: ``signals.riskRollingReturn``, the space of two signal
plugins, is not. The keys a plugin **declares** are those its metadata names: the BRIM ``name`` and, when it has one,
``description`` it publishes (``brimPlugins.<code>.name`` and ``.description``), ``display_name_key``,
``description_key``, ``name_i18n_key``, ``description_i18n_key``, the outputs', reference levels' and value regions'
``label_key`` and ``description_key``, and the params' ``x-i18n-key`` and ``x-tooltip-key``.

R1. Every key in a plugin's fragment lies in that plugin's space.
R2. Every key a plugin declares in its exclusive space lives in its fragment.
R3. No key in a fragment lies in another plugin's space, or is declared by another plugin.
R4. Every catalogue key under an exclusive space lives in that plugin's fragment; tools aside, whose two keys R2 holds.

What plugins share (a shared space, a key several plugins declare, a key outside every space) belongs to a subsystem
or to ``base``, where its prefix says. Every message names the key, where it is, and where it belongs.

Each detector first proves on synthetic metadata and trees under ``tmp_path`` what it reports and what it leaves
alone; then the repository: the metadata the six registries publish against the sources ``i18n_catalog`` reads, with a
sentinel that fails on a published field named like a key that the collector does not read.

PURE: importing the registries discovers and instantiates the plugins, and the gate reads what they publish; nothing
runs a plugin. No database, no server, no network; the synthetic trees live under ``tmp_path``.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.risk.registry import RiskAnalyticRegistry
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.services.tools.registry import ToolPluginRegistry
from scripts import i18n_catalog as catalog

REPO_ROOT = Path(__file__).resolve().parents[3]

BRIM_FAMILY = "brim_providers"
ASSET_FAMILY = "asset_source_providers"
FX_FAMILY = "fx_providers"
SIGNAL_FAMILY = "signal_plugins"
RISK_FAMILY = "risk_plugins"
TOOL_FAMILY = "tool_plugins"
# The families whose plugins have a space; FX plugins have none.
SPACED_FAMILIES = (BRIM_FAMILY, ASSET_FAMILY, SIGNAL_FAMILY, RISK_FAMILY, TOOL_FAMILY)
BRIM_SPACE = "brimPlugins"
ASSET_SPACE = "assets.providerParams"

# The module discovery loads a plugin folder's code from: backend.app.services.<family>.<folder>.plugin.
SERVICES_PACKAGE = ("backend", "app", "services")
PLUGIN_MODULE = "plugin"

# The fields of a published definition that hold a translation key. A new one belongs here: the sentinel fails on
# a field named like a key (``*_key``, ``x-*-key``) that is not listed.
I18N_FIELDS = frozenset({"display_name_key", "description_key", "label_key", "name_i18n_key", "description_i18n_key", "x-i18n-key", "x-tooltip-key"})
KEY_FIELD = re.compile(r"[_-]key$")
# Values, not metadata: the parameters' defaults and the parameter matches of the AI Export rules.
VALUE_FIELDS = frozenset({"default_params", "parameter_match"})

BASE_PLACE = (catalog.I18N_RELATIVE / catalog.BASE_NAME).as_posix()


# =============================================================================
# The model: spaces, plugins, places
# =============================================================================


@dataclass(frozen=True)
class Area:
    """A part of a plugin's space: the branch under ``path`` (whole segments), or the one key ``path`` when ``exact``."""

    path: str
    exact: bool = False

    def holds(self, key: str) -> bool:
        return key == self.path if self.exact else catalog.under(key, self.path)

    def __str__(self) -> str:
        return self.path if self.exact else f"{self.path}.*"


@dataclass(frozen=True)
class PluginI18n:
    """What one plugin folder publishes about its translations: its space and the keys its metadata names."""

    name: str
    areas: tuple[Area, ...] = ()
    declared: tuple[str, ...] = ()

    @property
    def family(self) -> str:
        return self.name.split("/", 1)[0]

    @property
    def fragment(self) -> str:
        return (catalog.SERVICES_RELATIVE / self.name / catalog.PLUGIN_I18N_DIR).as_posix()

    @property
    def space(self) -> str:
        return ", ".join(str(area) for area in self.areas) or "none"


def place(source: catalog.Source) -> str:
    """The folder of a source, as the messages show it: a plugin's ``i18n/``, a subsystem's folder, or base's."""
    if source.kind == "plugin":
        return (catalog.SERVICES_RELATIVE / source.name / catalog.PLUGIN_I18N_DIR).as_posix()
    return (catalog.I18N_RELATIVE / source.name).as_posix()


def in_fragment(owner: catalog.Source | None, plugin: PluginI18n) -> bool:
    return owner is not None and owner.kind == "plugin" and owner.name == plugin.name


def fold(entries: Iterable[PluginI18n]) -> tuple[PluginI18n, ...]:
    """One entry per folder: a folder registering several classes has the spaces and the keys of them all."""
    areas: dict[str, dict[Area, None]] = {}
    declared: dict[str, dict[str, None]] = {}
    for entry in entries:
        areas.setdefault(entry.name, {}).update(dict.fromkeys(entry.areas))
        declared.setdefault(entry.name, {}).update(dict.fromkeys(entry.declared))
    return tuple(PluginI18n(name, tuple(areas[name]), tuple(declared[name])) for name in areas)


class Ownership:
    """The plugins' spaces against the catalogue's owners: what the four rules read."""

    def __init__(self, plugins: Iterable[PluginI18n], sources: Iterable[catalog.Source], owners: Mapping[str, catalog.Source]):
        self.plugins = {plugin.name: plugin for plugin in plugins}
        self.sources = list(sources)
        self.owners = dict(owners)
        self.holders: dict[str, set[str]] = defaultdict(set)
        for plugin in self.plugins.values():
            for area in plugin.areas:
                self.holders[area.path].add(plugin.name)

    def fragments(self) -> list[catalog.Source]:
        return [source for source in self.sources if source.kind == "plugin"]

    def keys_of(self, source: catalog.Source) -> list[str]:
        return [key for key, owner in self.owners.items() if owner is source]

    def exclusive_area(self, plugin: PluginI18n, key: str) -> Area | None:
        """The area of ``plugin``'s space that holds ``key``, when no other plugin has it."""
        return next((area for area in plugin.areas if area.holds(key) and self.holders[area.path] == {plugin.name}), None)

    def home(self, key: str) -> str:
        """Where ``key`` belongs: the fragment of the one plugin whose exclusive space holds it, when no other plugin
        declares it; otherwise the subsystem its prefix names, or base, and out of that space if one holds it."""
        holding = [plugin for plugin in self.plugins.values() if any(area.holds(key) for area in plugin.areas)]
        owner = catalog.declared_owner(key, self.sources)
        shared = place(owner) if owner else BASE_PLACE
        area = self.exclusive_area(holding[0], key) if len(holding) == 1 else None
        if area is None:
            return shared
        if {plugin.name for plugin in self.plugins.values() if key in plugin.declared} <= {holding[0].name}:
            return holding[0].fragment
        return f"{shared}, renamed out of {area}"


def r1_problems(own: Ownership) -> list[str]:
    """R1: every key in a plugin's fragment lies in that plugin's space."""
    problems = []
    for fragment in own.fragments():
        plugin = own.plugins.get(fragment.name)
        for key in own.keys_of(fragment):
            if plugin is None:
                problems.append(f"{key}: in {place(fragment)}, but no registered plugin is {fragment.name}; expected in {own.home(key)}")
            elif not any(area.holds(key) for area in plugin.areas):
                problems.append(f"{key}: in {place(fragment)}, outside the space of {plugin.name} ({plugin.space}); expected in {own.home(key)}")
    return problems


def r2_problems(own: Ownership) -> list[str]:
    """R2: every key a plugin declares in its exclusive space lives in its fragment."""
    problems = []
    for plugin in own.plugins.values():
        for key in plugin.declared:
            area = own.exclusive_area(plugin, key)
            owner = own.owners.get(key)
            if area is None or in_fragment(owner, plugin):
                continue
            found = f"lives in {place(owner)}" if owner else "is in no catalogue"
            problems.append(f"{key}: declared by {plugin.name} in its space ({area}), but {found}; expected in {plugin.fragment}")
    return problems


def r3_problems(own: Ownership) -> list[str]:
    """R3: no key in a fragment lies in another plugin's space, or is declared by another plugin."""
    problems = []
    for fragment in own.fragments():
        others = [plugin for name, plugin in own.plugins.items() if name != fragment.name]
        for key in own.keys_of(fragment):
            reasons = [f"it lies in the space of {other.name} ({area})" for other in others for area in other.areas if area.holds(key)]
            reasons += [f"{other.name} declares it too" for other in others if key in other.declared and not any(area.holds(key) for area in other.areas)]
            if reasons:
                problems.append(f"{key}: in {place(fragment)}, but {' and '.join(reasons)}; expected in {own.home(key)}")
    return problems


def r4_problems(own: Ownership) -> list[str]:
    """R4: every catalogue key under an exclusive space lives in that plugin's fragment; tools aside (R2 holds theirs)."""
    problems = []
    spaced = [plugin for plugin in own.plugins.values() if plugin.family != TOOL_FAMILY]
    for key, owner in own.owners.items():
        for plugin in spaced:
            area = own.exclusive_area(plugin, key)
            if area is not None and not in_fragment(owner, plugin):
                problems.append(f"{key}: under {area}, the space of {plugin.name} alone, but lives in {place(owner)}; expected in {plugin.fragment}")
    return problems


def space_problems(plugins: Iterable[PluginI18n]) -> list[str]:
    """Every plugin of a family with a space has one; an FX plugin has none; no plugin is of another family."""
    problems = []
    for plugin in plugins:
        if plugin.family in SPACED_FAMILIES and not plugin.areas:
            problems.append(f"{plugin.name}: publishes no i18n space")
        elif plugin.family == FX_FAMILY and plugin.areas:
            problems.append(f"{plugin.name}: an FX plugin has no i18n space, yet publishes {plugin.space}")
        elif plugin.family not in (*SPACED_FAMILIES, FX_FAMILY):
            problems.append(f"{plugin.name}: not a plugin family this gate knows")
    return problems


def brim_folder_problems(plugins: Iterable[PluginI18n]) -> list[str]:
    """A BRIM plugin's code is its folder: the UI reads ``brimPlugins.<code>``, the fragment is the folder's."""
    problems = []
    for plugin in plugins:
        if plugin.family != BRIM_FAMILY:
            continue
        folder = plugin.name.split("/", 1)[1]
        codes = [area.path.removeprefix(f"{BRIM_SPACE}.") for area in plugin.areas]
        if codes != [folder]:
            problems.append(f"{plugin.name}: BRIM code {', '.join(codes) or 'none'}, folder {folder}; the code must be the folder")
    return problems


# =============================================================================
# What the registries publish
# =============================================================================


def plugin_folder(module: str) -> str:
    """``<family>/<folder>`` of a class discovery loaded from ``backend.app.services.<family>.<folder>.plugin``."""
    parts = tuple(module.split("."))
    if len(parts) != 6 or parts[:3] != SERVICES_PACKAGE or parts[5] != PLUGIN_MODULE:
        raise ValueError(f"{module}: not the module of a plugin folder (backend.app.services.<family>.<folder>.plugin)")
    return f"{parts[3]}/{parts[4]}"


def parent(key: str) -> str | None:
    return key.rsplit(".", 1)[0] if "." in key else None


def published_keys(dump: object) -> tuple[tuple[str, ...], frozenset[str]]:
    """The translation keys a definition's JSON dump names (``I18N_FIELDS``, at any depth), and the fields named like
    a key that it holds besides: what the collector would miss."""
    keys: dict[str, None] = {}
    unread: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        for field, value in node.items():
            if field in VALUE_FIELDS:
                continue
            if not isinstance(value, str):
                walk(value)
            elif field in I18N_FIELDS:
                keys[value] = None
            elif KEY_FIELD.search(field):
                unread.add(field)

    walk(dump)
    return tuple(keys), frozenset(unread)


def from_definition(name: str, dump: Mapping[str, object], space_field: str) -> PluginI18n:
    """A signal or risk plugin from its published definition: the space is the parent of ``space_field``'s key."""
    keys, _unread = published_keys(dump)
    space = parent(str(dump[space_field]))
    return PluginI18n(name, (Area(space),) if space else (), keys)


def signal_definitions() -> list[tuple[str, dict]]:
    """``(folder, published definition)`` of every registered signal plugin, in the catalogue or not."""
    found = []
    for code in SignalPluginRegistry.list_plugin_codes():
        plugin_class = SignalPluginRegistry.get_plugin(code)
        found.append((plugin_folder(plugin_class.__module__), plugin_class.catalog_definition().model_dump(mode="json")))
    return found


def risk_definitions() -> list[tuple[str, dict]]:
    """``(folder, published definition)`` of every registered risk analytic."""
    return [(plugin_folder(RiskAnalyticRegistry.get_plugin(definition.analytic_code).__module__), definition.model_dump(mode="json")) for definition in RiskAnalyticRegistry.list_definitions()]


def brim_plugins() -> list[PluginI18n]:
    found = []
    for code in BRIMProviderRegistry.list_plugin_codes():
        info = BRIMProviderRegistry.get_plugin_instance(code).to_plugin_info()
        space = f"{BRIM_SPACE}.{info.code}"
        declared = (f"{space}.name", *((f"{space}.description",) if info.description else ()))
        found.append(PluginI18n(plugin_folder(BRIMProviderRegistry.get_plugin(code).__module__), (Area(space),), declared))
    return found


def asset_plugins() -> list[PluginI18n]:
    return [PluginI18n(plugin_folder(AssetProviderRegistry.get_plugin(code).__module__), (Area(f"{ASSET_SPACE}.{code}"),)) for code in AssetProviderRegistry.list_plugin_codes()]


def fx_plugins() -> list[PluginI18n]:
    return [PluginI18n(plugin_folder(FXProviderRegistry.get_plugin(code).__module__)) for code in FXProviderRegistry.list_plugin_codes()]


def tool_plugins() -> list[PluginI18n]:
    found = []
    for definition in ToolPluginRegistry.get_snapshot().definitions.values():
        keys = tuple(key for key in (definition.descriptor.name_i18n_key, definition.descriptor.description_i18n_key) if key)
        found.append(PluginI18n(plugin_folder(definition.plugin_class.__module__), tuple(Area(key, exact=True) for key in keys), keys))
    return found


def registry_plugins() -> tuple[PluginI18n, ...]:
    """Every plugin of the six registries, one per folder."""
    signals = [from_definition(name, dump, "display_name_key") for name, dump in signal_definitions()]
    risks = [from_definition(name, dump, "name_i18n_key") for name, dump in risk_definitions()]
    return fold([*brim_plugins(), *asset_plugins(), *fx_plugins(), *signals, *risks, *tool_plugins()])


# =============================================================================
# The synthetic plugins and tree
# =============================================================================

BROKER = PluginI18n("brim_providers/probe_broker", (Area("brimPlugins.probe_broker"),), ("brimPlugins.probe_broker.name", "brimPlugins.probe_broker.description"))
SOURCE = PluginI18n("asset_source_providers/probe_source", (Area("assets.providerParams.probe_source"),))
RATES = PluginI18n("fx_providers/probe_rates")
ALPHA = PluginI18n("signal_plugins/probe_alpha", (Area("signals.probeAlpha"),), ("signals.probeAlpha.name", "signals.probeAlpha.output", "signals.reference.zero", "chartSettings.params.period"))
BETA = PluginI18n("signal_plugins/probe_beta", (Area("signals.probeBeta"),), ("signals.probeBeta.name", "signals.reference.zero"))
# Two plugins sharing one space: neither has it alone, so its keys are a subsystem's.
TWIN_A = PluginI18n("signal_plugins/probe_twin_a", (Area("signals.probeTwin"),), ("signals.probeTwin.name", "signals.probeTwin.output"))
TWIN_B = PluginI18n("signal_plugins/probe_twin_b", (Area("signals.probeTwin"),), ("signals.probeTwin.name", "signals.probeTwin.output"))
VAR = PluginI18n("risk_plugins/probe_var", (Area("risk.analytics.probeVar"),), ("risk.analytics.probeVar.name", "risk.analytics.probeVar.description", "risk.params.confidence"))
TOOL = PluginI18n("tool_plugins/probe_tool", (Area("tools.probeTool.name", exact=True), Area("tools.probeTool.description", exact=True)), ("tools.probeTool.name", "tools.probeTool.description"))
PLUGINS = (BROKER, SOURCE, RATES, ALPHA, BETA, TWIN_A, TWIN_B, VAR, TOOL)

# The subsystems and their prefixes; a subsystem without keys keeps its folder and prefixes.
PREFIXES = {"charts": ("signals", "chartSettings"), "risk": ("risk",), "tools": ("tools",)}

# The sources of a tree that keeps every rule, in English: base, the subsystems, the plugins' fragments.
HEALTHY = {
    "base": {"common.ok": "OK"},
    "charts": {"signals.reference.zero": "Zero", "signals.probeTwin.name": "Twin", "signals.probeTwin.output": "Twin line", "chartSettings.params.period": "Period"},
    "risk": {"risk.analytics.title": "Analytics", "risk.params.confidence": "Confidence"},
    "tools": {"tools.probeTool.ui.title": "Calculator"},
    BROKER.name: {"brimPlugins.probe_broker.name": "Probe Broker", "brimPlugins.probe_broker.description": "Reads probe statements"},
    SOURCE.name: {"assets.providerParams.probe_source.label.region": "Region"},
    ALPHA.name: {"signals.probeAlpha.name": "Alpha", "signals.probeAlpha.output": "Alpha line", "signals.probeAlpha.hint": "Undeclared, in its space"},
    BETA.name: {"signals.probeBeta.name": "Beta"},
    VAR.name: {"risk.analytics.probeVar.name": "VaR", "risk.analytics.probeVar.description": "Value at risk"},
    TOOL.name: {"tools.probeTool.name": "Calculator", "tools.probeTool.description": "Computes"},
}


def write_json(path: Path, keys: Mapping[str, str]) -> None:
    nested: dict = {}
    for key, text in keys.items():
        catalog.set_nested(nested, key, text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nested, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_tree(root: Path, layout: Mapping[str, Mapping[str, str]]) -> Path:
    """Write ``layout``'s sources under ``root``: ``base``, the subsystems of ``PREFIXES``, a plugin (``<family>/
    <folder>``, with its ``plugin.py``) and its fragment when it has keys."""
    write_json(root / catalog.I18N_RELATIVE / catalog.BASE_NAME / "en.json", layout.get(catalog.BASE_NAME, {}))
    for name, prefixes in PREFIXES.items():
        folder = root / catalog.I18N_RELATIVE / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / catalog.PREFIXES_FILE).write_text("\n".join(prefixes) + "\n", encoding="utf-8")
        if layout.get(name):
            write_json(folder / "en.json", layout[name])
    for name, keys in layout.items():
        if "/" not in name or not keys:
            continue
        folder = root / catalog.SERVICES_RELATIVE / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "__init__.py").write_text('"""A synthetic plugin."""\n', encoding="utf-8")
        (folder / "plugin.py").write_text("", encoding="utf-8")
        write_json(folder / catalog.PLUGIN_I18N_DIR / "en.json", keys)
    return root


def relocated(key: str, to: str | None, layout: Mapping[str, Mapping[str, str]] = HEALTHY) -> dict[str, dict[str, str]]:
    """``layout`` with ``key`` taken from wherever it is and put in ``to``; dropped when ``to`` is None."""
    result = {name: dict(keys) for name, keys in layout.items()}
    text = "Text"
    for keys in result.values():
        if key in keys:
            text = keys.pop(key)
    if to is not None:
        result.setdefault(to, {})[key] = text
    return result


def ownership(root: Path, plugins: Iterable[PluginI18n] = PLUGINS) -> Ownership:
    """What the rules read from a tree: its sources and owners through ``i18n_catalog``, against ``plugins``."""
    langs, sources = catalog.load(root)
    return Ownership(plugins, sources, catalog.merge(langs, sources, root=root).owners)


def without(*names: str) -> tuple[PluginI18n, ...]:
    return tuple(plugin for plugin in PLUGINS if plugin.name not in names)


CHARTS = (catalog.I18N_RELATIVE / "charts").as_posix()
TOOLS = (catalog.I18N_RELATIVE / "tools").as_posix()


# =============================================================================
# 1. The model: folders, areas, published keys, exclusivity
# =============================================================================


@pytest.mark.parametrize(
    ("module", "folder"),
    [
        pytest.param("backend.app.services.brim_providers.probe_broker.plugin", "brim_providers/probe_broker", id="a-brim-plugin"),
        pytest.param("backend.app.services.signal_plugins.probe_alpha.plugin", "signal_plugins/probe_alpha", id="a-signal-plugin"),
    ],
)
def test_plugin_folder_is_the_family_and_folder_of_a_plugin_module(module, folder):
    assert plugin_folder(module) == folder


@pytest.mark.parametrize(
    "module",
    [
        pytest.param("backend.app.services.signal_plugins.probe_single", id="a-single-module-plugin"),
        pytest.param("backend.app.services.signal_plugins.probe_alpha.plugin.inner", id="deeper-than-the-plugin-module"),
        pytest.param("backend.app.services.signal_plugins.probe_alpha.helpers", id="not-the-plugin-module"),
        pytest.param("backend.test_scripts.test_utilities.probe_alpha.plugin", id="outside-the-services"),
    ],
)
def test_plugin_folder_refuses_a_module_that_is_not_a_plugin_folder(module):
    with pytest.raises(ValueError) as refused:
        plugin_folder(module)

    assert str(refused.value) == f"{module}: not the module of a plugin folder (backend.app.services.<family>.<folder>.plugin)"


def test_an_area_holds_its_branch_by_whole_segments_or_its_one_key():
    branch = Area("signals.probeAlpha")
    exact = Area("tools.probeTool.name", exact=True)

    assert [branch.holds(key) for key in ("signals.probeAlpha", "signals.probeAlpha.name", "signals.probeAlpha.a.b")] == [True, True, True]
    assert [branch.holds(key) for key in ("signals.probeAlphabet.name", "signals.probe", "signals")] == [False, False, False]
    assert [exact.holds(key) for key in ("tools.probeTool.name", "tools.probeTool.name.x", "tools.probeTool")] == [True, False, False]
    assert (str(branch), str(exact)) == ("signals.probeAlpha.*", "tools.probeTool.name")


def test_fold_gives_a_folder_the_spaces_and_keys_of_all_its_classes():
    first = PluginI18n("signal_plugins/probe_pair", (Area("signals.probePair"),), ("signals.probePair.name", "signals.reference.zero"))
    second = PluginI18n("signal_plugins/probe_pair", (Area("signals.probePairSlow"), Area("signals.probePair")), ("signals.probePairSlow.name", "signals.reference.zero"))

    assert fold([first, BETA, second]) == (
        PluginI18n("signal_plugins/probe_pair", (Area("signals.probePair"), Area("signals.probePairSlow")), ("signals.probePair.name", "signals.reference.zero", "signals.probePairSlow.name")),
        BETA,
    )


# A published definition, shaped like a signal's: the keys at every depth, the values that only look like keys.
DEFINITION = {
    "signal_code": "PROBE",
    "display_name_key": "signals.probe.name",
    "description_key": "signals.probe.description",
    "icon": "activity",
    "params_schema": {
        "properties": {
            "period": {"type": "integer", "default": 14, "x-i18n-key": "chartSettings.params.period", "x-tooltip-key": "signals.tooltips.period", "x-suffix": "sessions"},
            "label_key": {"type": "string", "default": "a.default.value"},
        },
    },
    "default_params": {"label_key": "a.parameter.value"},
    "output_specs": [
        {
            "key": "probe",
            "label_key": "signals.probe.output",
            "description_key": None,
            "default_reference_levels": [{"key": "zero", "label_key": "signals.reference.zero", "value": 0}],
            "default_value_regions": [{"key": "high", "label_key": "signals.probe.high", "description_key": "signals.regions.highDescription"}],
        },
    ],
    "ai_export_temporal_rules": [{"temporal_class": "event", "parameter_match": {"label_key": "a.matched.value"}}],
}


def test_published_keys_reads_the_key_fields_at_any_depth_and_leaves_values_alone():
    keys, unread = published_keys(DEFINITION)

    assert keys == (
        "signals.probe.name",
        "signals.probe.description",
        "chartSettings.params.period",
        "signals.tooltips.period",
        "signals.probe.output",
        "signals.reference.zero",
        "signals.probe.high",
        "signals.regions.highDescription",
    )
    assert unread == frozenset()


def test_published_keys_names_a_key_field_it_does_not_read():
    dump = {"display_name_key": "signals.probe.name", "hint_key": "signals.probe.hint", "params_schema": {"properties": {"period": {"x-help-key": "signals.help.period"}}}}

    assert published_keys(dump) == (("signals.probe.name",), frozenset({"hint_key", "x-help-key"}))


@pytest.mark.parametrize(
    ("dump", "space_field", "expected"),
    [
        pytest.param(DEFINITION, "display_name_key", PluginI18n("probe_plugins/probe", (Area("signals.probe"),), published_keys(DEFINITION)[0]), id="a-signal"),
        pytest.param(
            {"name_i18n_key": "risk.analytics.probeVar.name", "description_i18n_key": "risk.analytics.probeVar.description"},
            "name_i18n_key",
            PluginI18n("probe_plugins/probe", (Area("risk.analytics.probeVar"),), ("risk.analytics.probeVar.name", "risk.analytics.probeVar.description")),
            id="a-risk-analytic",
        ),
        pytest.param({"display_name_key": "probe"}, "display_name_key", PluginI18n("probe_plugins/probe", (), ("probe",)), id="a-key-without-a-parent-gives-no-space"),
    ],
)
def test_a_definition_gives_the_space_its_key_names(dump, space_field, expected):
    assert from_definition("probe_plugins/probe", dump, space_field) == expected


def test_a_space_is_exclusive_only_to_its_one_plugin(tmp_path):
    own = ownership(build_tree(tmp_path, HEALTHY))

    assert own.exclusive_area(ALPHA, "signals.probeAlpha.name") == Area("signals.probeAlpha")
    assert own.exclusive_area(ALPHA, "signals.probeBeta.name") is None
    assert own.exclusive_area(TWIN_A, "signals.probeTwin.name") is None
    assert own.exclusive_area(TOOL, "tools.probeTool.name") == Area("tools.probeTool.name", exact=True)
    assert own.exclusive_area(TOOL, "tools.probeTool.ui.title") is None
    assert ownership(tmp_path, without(TWIN_B.name)).exclusive_area(TWIN_A, "signals.probeTwin.name") == Area("signals.probeTwin")


# =============================================================================
# 2. The rules on synthetic trees: what each reports, what each leaves alone
# =============================================================================


def test_the_healthy_tree_keeps_every_rule(tmp_path):
    """Shared spaces and shared keys in a subsystem, an undeclared key inside its own space, a tool whose namespace a
    subsystem holds, a plugin without a space and without a fragment: none is a breach."""
    own = ownership(build_tree(tmp_path, HEALTHY))

    assert [place(fragment) for fragment in own.fragments()] == [plugin.fragment for plugin in (SOURCE, BROKER, VAR, ALPHA, BETA, TOOL)]
    assert (r1_problems(own), r2_problems(own), r3_problems(own), r4_problems(own)) == ([], [], [], [])


@pytest.mark.parametrize(
    ("layout", "problem"),
    [
        pytest.param(relocated("signals.reference.zero", ALPHA.name), f"signals.reference.zero: in {ALPHA.fragment}, outside the space of {ALPHA.name} (signals.probeAlpha.*); expected in {CHARTS}", id="a-key-of-a-subsystem"),
        pytest.param(relocated("common.ok", ALPHA.name), f"common.ok: in {ALPHA.fragment}, outside the space of {ALPHA.name} (signals.probeAlpha.*); expected in {BASE_PLACE}", id="a-key-of-base"),
        pytest.param(relocated("signals.probeBeta.name", ALPHA.name), f"signals.probeBeta.name: in {ALPHA.fragment}, outside the space of {ALPHA.name} (signals.probeAlpha.*); expected in {BETA.fragment}", id="a-key-of-another-plugin"),
        pytest.param(relocated("signals.probeAlphabet.name", ALPHA.name), f"signals.probeAlphabet.name: in {ALPHA.fragment}, outside the space of {ALPHA.name} (signals.probeAlpha.*); expected in {CHARTS}", id="whole-segments-only"),
        pytest.param(relocated("tools.probeTool.ui.title", TOOL.name), f"tools.probeTool.ui.title: in {TOOL.fragment}, outside the space of {TOOL.name} (tools.probeTool.name, tools.probeTool.description); expected in {TOOLS}", id="a-tool-key-beside-its-two"),
        pytest.param(relocated("common.rates", RATES.name), f"common.rates: in {RATES.fragment}, outside the space of {RATES.name} (none); expected in {BASE_PLACE}", id="a-plugin-without-a-space"),
        pytest.param(relocated("signals.probeGhost.name", "signal_plugins/probe_ghost"), f"signals.probeGhost.name: in {PluginI18n('signal_plugins/probe_ghost').fragment}, but no registered plugin is signal_plugins/probe_ghost; expected in {CHARTS}", id="a-folder-no-registry-knows"),
    ],
)
def test_r1_refuses_a_fragment_key_outside_its_plugin_space(tmp_path, layout, problem):
    assert r1_problems(ownership(build_tree(tmp_path, layout))) == [problem]


@pytest.mark.parametrize(
    ("layout", "problem"),
    [
        pytest.param(relocated("signals.probeAlpha.output", "charts"), f"signals.probeAlpha.output: declared by {ALPHA.name} in its space (signals.probeAlpha.*), but lives in {CHARTS}; expected in {ALPHA.fragment}", id="in-a-subsystem"),
        pytest.param(relocated("brimPlugins.probe_broker.name", "base"), f"brimPlugins.probe_broker.name: declared by {BROKER.name} in its space (brimPlugins.probe_broker.*), but lives in {BASE_PLACE}; expected in {BROKER.fragment}", id="in-base"),
        pytest.param(relocated("risk.analytics.probeVar.name", ALPHA.name), f"risk.analytics.probeVar.name: declared by {VAR.name} in its space (risk.analytics.probeVar.*), but lives in {ALPHA.fragment}; expected in {VAR.fragment}", id="in-another-plugin-fragment"),
        pytest.param(relocated("brimPlugins.probe_broker.description", None), f"brimPlugins.probe_broker.description: declared by {BROKER.name} in its space (brimPlugins.probe_broker.*), but is in no catalogue; expected in {BROKER.fragment}", id="in-no-catalogue"),
        pytest.param(relocated("tools.probeTool.name", "tools"), f"tools.probeTool.name: declared by {TOOL.name} in its space (tools.probeTool.name), but lives in {TOOLS}; expected in {TOOL.fragment}", id="a-tool-key-in-its-subsystem"),
    ],
)
def test_r2_refuses_a_declared_key_of_an_exclusive_space_outside_its_fragment(tmp_path, layout, problem):
    assert r2_problems(ownership(build_tree(tmp_path, layout))) == [problem]


ALPHA_OUTPUT_TOO = PluginI18n(BETA.name, BETA.areas, (*BETA.declared, "signals.probeAlpha.output"))


@pytest.mark.parametrize(
    ("layout", "plugins", "problem"),
    [
        pytest.param(relocated("signals.probeBeta.name", ALPHA.name), PLUGINS, f"signals.probeBeta.name: in {ALPHA.fragment}, but it lies in the space of {BETA.name} (signals.probeBeta.*); expected in {BETA.fragment}", id="another-plugin-space"),
        pytest.param(relocated("signals.probeTwin.name", TWIN_A.name), PLUGINS, f"signals.probeTwin.name: in {TWIN_A.fragment}, but it lies in the space of {TWIN_B.name} (signals.probeTwin.*); expected in {CHARTS}", id="a-shared-space"),
        pytest.param(relocated("tools.probeTool.name", ALPHA.name), PLUGINS, f"tools.probeTool.name: in {ALPHA.fragment}, but it lies in the space of {TOOL.name} (tools.probeTool.name); expected in {TOOL.fragment}", id="a-tool-key"),
        pytest.param(HEALTHY, (*without(BETA.name), ALPHA_OUTPUT_TOO), f"signals.probeAlpha.output: in {ALPHA.fragment}, but {BETA.name} declares it too; expected in {CHARTS}, renamed out of signals.probeAlpha.*", id="a-key-another-plugin-declares"),
    ],
)
def test_r3_refuses_a_fragment_key_another_plugin_claims(tmp_path, layout, plugins, problem):
    assert r3_problems(ownership(build_tree(tmp_path, layout), plugins)) == [problem]


@pytest.mark.parametrize(
    ("layout", "problem"),
    [
        pytest.param(relocated("signals.probeAlpha.extra", "charts"), f"signals.probeAlpha.extra: under signals.probeAlpha.*, the space of {ALPHA.name} alone, but lives in {CHARTS}; expected in {ALPHA.fragment}", id="an-undeclared-key-in-a-subsystem"),
        pytest.param(
            relocated("assets.providerParams.probe_source.label.region", "base"), f"assets.providerParams.probe_source.label.region: under assets.providerParams.probe_source.*, the space of {SOURCE.name} alone, but lives in {BASE_PLACE}; expected in {SOURCE.fragment}", id="a-provider-param-in-base"
        ),
        pytest.param(relocated("risk.analytics.probeVar.description", ALPHA.name), f"risk.analytics.probeVar.description: under risk.analytics.probeVar.*, the space of {VAR.name} alone, but lives in {ALPHA.fragment}; expected in {VAR.fragment}", id="in-another-plugin-fragment"),
    ],
)
def test_r4_refuses_a_key_under_an_exclusive_space_outside_its_fragment(tmp_path, layout, problem):
    assert r4_problems(ownership(build_tree(tmp_path, layout))) == [problem]


def test_r4_leaves_a_tool_key_to_r2(tmp_path):
    own = ownership(build_tree(tmp_path, relocated("tools.probeTool.description", "tools")))

    assert r4_problems(own) == []
    assert r2_problems(own) == [f"tools.probeTool.description: declared by {TOOL.name} in its space (tools.probeTool.description), but lives in {TOOLS}; expected in {TOOL.fragment}"]


def test_r2_and_r4_hold_a_space_once_no_other_plugin_shares_it(tmp_path):
    """The twins' keys stay in ``charts`` while two plugins share their space; with one plugin left, they are its."""
    own = ownership(build_tree(tmp_path, HEALTHY), without(TWIN_B.name))

    assert r2_problems(own) == [f"signals.probeTwin.{field}: declared by {TWIN_A.name} in its space (signals.probeTwin.*), but lives in {CHARTS}; expected in {TWIN_A.fragment}" for field in ("name", "output")]
    assert r4_problems(own) == [f"signals.probeTwin.{field}: under signals.probeTwin.*, the space of {TWIN_A.name} alone, but lives in {CHARTS}; expected in {TWIN_A.fragment}" for field in ("name", "output")]


def test_the_space_check_flags_a_plugin_without_a_space_and_an_fx_plugin_with_one():
    plugins = (*PLUGINS, PluginI18n("signal_plugins/probe_blank"), PluginI18n("fx_providers/probe_named", (Area("fx.probeNamed"),)), PluginI18n("probe_widgets/probe_odd"))

    assert space_problems(PLUGINS) == []
    assert space_problems(plugins) == [
        "signal_plugins/probe_blank: publishes no i18n space",
        "fx_providers/probe_named: an FX plugin has no i18n space, yet publishes fx.probeNamed.*",
        "probe_widgets/probe_odd: not a plugin family this gate knows",
    ]


def test_the_brim_check_flags_a_code_that_is_not_its_folder():
    plugins = (*PLUGINS, PluginI18n("brim_providers/probe_folder", (Area("brimPlugins.probe_code"),)), PluginI18n("brim_providers/probe_twice", (Area("brimPlugins.probe_twice"), Area("brimPlugins.probe_again"))))

    assert brim_folder_problems(PLUGINS) == []
    assert brim_folder_problems(plugins) == [
        "brim_providers/probe_folder: BRIM code probe_code, folder probe_folder; the code must be the folder",
        "brim_providers/probe_twice: BRIM code probe_twice, probe_again, folder probe_twice; the code must be the folder",
    ]


# =============================================================================
# 3. The repository: what the registries publish, against the catalogue's sources
# =============================================================================


@pytest.fixture(scope="module")
def published() -> tuple[PluginI18n, ...]:
    return registry_plugins()


@pytest.fixture(scope="module")
def repository(published) -> Ownership:
    langs, sources = catalog.load(REPO_ROOT)
    return Ownership(published, sources, catalog.merge(langs, sources, root=REPO_ROOT).owners)


def report(problems: list[str]) -> str:
    return f"{len(problems)} problem(s):\n" + "\n".join(problems)


def test_every_registry_publishes_its_plugins_each_with_a_space(published):
    families = {plugin.family for plugin in published}

    assert families == {*SPACED_FAMILIES, FX_FAMILY}, "a registry published no plugin, or one of a family this gate does not know"
    assert space_problems(published) == []


def test_every_brim_plugin_code_is_its_folder(published):
    assert brim_folder_problems(published) == []


def test_the_published_definitions_hold_no_key_field_the_gate_does_not_read():
    unread = {name: sorted(published_keys(dump)[1]) for name, dump in (*signal_definitions(), *risk_definitions())}

    assert {name: fields for name, fields in unread.items() if fields} == {}


def test_r1_every_fragment_key_lies_in_its_plugin_space(repository):
    assert repository.fragments(), "no plugin fragment in the repository: nothing for R1 to read"
    problems = r1_problems(repository)

    assert not problems, report(problems)


def test_r2_every_declared_key_of_an_exclusive_space_lives_in_its_fragment(repository):
    assert any(repository.exclusive_area(plugin, key) for plugin in repository.plugins.values() for key in plugin.declared), "no plugin declares a key of its exclusive space: nothing for R2 to read"
    problems = r2_problems(repository)

    assert not problems, report(problems)


def test_r3_no_fragment_key_lies_in_another_plugin_space_or_is_declared_by_another_plugin(repository):
    assert repository.fragments(), "no plugin fragment in the repository: nothing for R3 to read"
    problems = r3_problems(repository)

    assert not problems, report(problems)


def test_r4_every_key_under_an_exclusive_space_lives_in_its_fragment(repository):
    problems = r4_problems(repository)

    assert not problems, report(problems)
