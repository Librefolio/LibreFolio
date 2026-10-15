"""Plugin settings, the guards: what no declaration and no module around the plugin settings may let through (plan 03, CP10).

The contract pinned here, over the plugins actually registered (``service.FAMILY_REGISTRIES``, every family that may
declare settings) and the sources of ``backend/app/``:

1. **Documented**: every variable that can set a ``system`` field of a shipped plugin (one that is not ``test_only``) —
   its derived name and its alias — has a variable line in ``.env.example``: an option nobody can find is no option.
   No shipped plugin declares a field today, so the guard first proves on a synthetic declaration that it flags an
   undocumented variable, skips a test-only plugin, and that the parser reads the real file.
2. **One owner per variable**: across every registered plugin of every family, test-only ones included, the derived
   names and the aliases are pairwise distinct (``foo_bar``/``baz`` and ``foo``/``bar_baz`` would meet), and each is
   claimed at registration by its own plugin (``claimed_env_variables``, the runtime half of this rule). Every
   registered declaration validates for its family, the families with rules are exactly the families with a registry,
   and no discovery error is a refused declaration.
3. **No alias is a variable LibreFolio reads itself** (the static half of the collision finding of the security
   review): an alias ``LIBREFOLIO_INSTANCE_KEY`` passes ``validate_declaration`` and no other plugin claims it, yet it
   would hand the instance key to a plugin as its own secret. The variables read are those read with a literal name
   anywhere under ``backend/app/`` — the AST detector of ``test_env_example.py``, forwarders such as ``env_secret``
   included — and the fields of ``Settings``; an alias and its ``_FILE`` form are both checked. The derived namespace
   ``LIBREFOLIO_PLUGIN_`` belongs to the derived names: the application reads no variable of it with a literal name.
4. **AI Export never reads the plugin settings**: no module under ``services/ai_export/`` imports
   ``services.plugin_settings`` (absolute, relative or through ``importlib``), ``PluginSystemSetting`` or
   ``PluginUserSetting`` (by name, by attribute or by a star import), or names their tables.

Pure: the sources and ``.env.example`` are read as text, the real registries are only read (their discovery is the
application's own), and the synthetic declarations are never registered. Every guard asserts an absence, so each one
first proves on synthetic input that it sees a presence.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

import pytest

from backend.app.config import Settings
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.fx_providers.mockfx.plugin import MockFXProvider
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.fields import (
    ENV_PREFIX,
    FAMILY_RULES,
    PluginSettingField,
    SettingOption,
    SettingScope,
    SettingsDeclarationError,
    SettingType,
    claimed_env_variables,
    env_name,
    env_variables,
    validate_declaration,
)
from backend.app.services.plugin_settings.service import FAMILY_REGISTRIES
from backend.test_scripts.test_services.test_env_example import ENV_EXAMPLE, _application_reads, _variable_lines, environment_reads
from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "backend" / "app"
AI_EXPORT_ROOT = APP_ROOT / "services" / "ai_export"

#: (family, plugin code, plugin class)
Plugin = tuple[str, str, type]


def _declaration(name: str, fields: tuple[PluginSettingField, ...], *, test_only: bool = False) -> type:
    """A synthetic plugin class: never registered, only handed to the guards."""
    return type(name, (PluginSettingsMixin,), {"settings_fields": fields, "test_only": test_only})


def _secret(key: str, alias: str | None = None) -> PluginSettingField:
    return PluginSettingField(key=key, type=SettingType.STRING, scope=SettingScope.SYSTEM, label=key, secret=True, env=alias)


def _plain(key: str, scope: SettingScope = SettingScope.SYSTEM) -> PluginSettingField:
    return PluginSettingField(key=key, type=SettingType.SELECT, scope=scope, label=key, default="a", options=(SettingOption("a", "A"),))


def _registered() -> list[Plugin]:
    """Every plugin the registries of the settings families hold, after their discovery."""
    return [(family, code, registry.get_plugin(code)) for family, registry in FAMILY_REGISTRIES.items() for code in registry.list_plugin_codes()]


def _variables(plugins: Iterable[Plugin], *, shipped_only: bool = False) -> Iterable[tuple[str, str, PluginSettingField, str]]:
    """``(family, code, field, variable)`` for every variable of every system field of ``plugins``."""
    for family, code, plugin_class in plugins:
        if shipped_only and getattr(plugin_class, "test_only", False):
            continue
        for declared in getattr(plugin_class, "settings_fields", ()):
            for variable in env_variables(family, code, declared):
                yield family, code, declared, variable


# =============================================================================
# THE GUARDS, AS FUNCTIONS: each one proven on synthetic input before it judges the real one
# =============================================================================


def undocumented(plugins: Iterable[Plugin], documented: set[str]) -> list[str]:
    """The variables of the shipped plugins' system fields that ``.env.example`` does not list."""
    return [f"{family}/{code}/{declared.key}: {variable}" for family, code, declared, variable in _variables(plugins, shipped_only=True) if variable not in documented]


def collisions(plugins: Iterable[Plugin]) -> dict[str, list[str]]:
    """The variables more than one field reads: ``{variable: ["family/code/key", ...]}``."""
    readers: dict[str, list[str]] = defaultdict(list)
    for family, code, declared, variable in _variables(plugins):
        readers[variable].append(f"{family}/{code}/{declared.key}")
    return {variable: fields for variable, fields in readers.items() if len(fields) > 1}


def aliases_read_by_the_application(plugins: Iterable[Plugin], read: set[str]) -> list[str]:
    """The aliases (or their ``_FILE`` forms) that are variables the application reads for itself."""
    return [f"{family}/{code}/{declared.key}: {name}" for family, code, plugin_class in plugins for declared in getattr(plugin_class, "settings_fields", ()) if declared.env is not None for name in (declared.env, declared.env + "_FILE") if name in read]


def _documented() -> set[str]:
    return {line.name for line in _variable_lines(ENV_EXAMPLE.read_text(encoding="utf-8"))}


def _application_variables() -> set[str]:
    """The variables LibreFolio reads for itself: with a literal name under ``backend/app/``, and the ``Settings`` fields."""
    return set(_application_reads()) | {name.upper() for name in Settings.model_fields}


# =============================================================================
# 1. DOCUMENTED
# =============================================================================


def test_the_documentation_guard_flags_an_undocumented_field_and_skips_a_test_only_plugin():
    """1, barrier: a shipped declaration's derived names and alias are flagged until documented; a user field has none."""
    print_section("1: the documentation guard on a synthetic declaration")
    shipped = _declaration("LabShipped", (_secret("api_key", "LIBREFOLIO_LAB_API_KEY"), _plain("region"), _plain("limit", SettingScope.USER)))
    variables = {env_name("asset", "lab_doc", "api_key"), "LIBREFOLIO_LAB_API_KEY", env_name("asset", "lab_doc", "region")}

    flagged = undocumented([("asset", "lab_doc", shipped)], set())

    assert flagged == ["asset/lab_doc/api_key: LIBREFOLIO_PLUGIN_ASSET_LAB_DOC_API_KEY", "asset/lab_doc/api_key: LIBREFOLIO_LAB_API_KEY", "asset/lab_doc/region: LIBREFOLIO_PLUGIN_ASSET_LAB_DOC_REGION"]
    assert undocumented([("asset", "lab_doc", shipped)], variables) == []
    assert undocumented([("asset", "lab_doc", _declaration("LabTestOnly", shipped.settings_fields, test_only=True))], set()) == []
    print_success(f"{len(flagged)} variables flagged, none once documented, none for a test-only plugin")


def test_the_parser_reads_the_variable_lines_of_env_example():
    """1, barrier: the real file's variable lines, commented or not, are what the guard compares with."""
    documented = _documented()
    assert {"LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_INSTANCE_KEY_FILE", "LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT", "PORT"} <= documented


def test_every_variable_of_a_shipped_system_field_is_documented():
    """1: over every registered plugin of every settings family."""
    plugins = _registered()
    owners = {(family, code) for family, code, _plugin in plugins}
    assert {("asset", "mockprov"), ("fx", "MOCKFX")} <= owners, f"barrier: the registries were not walked: {sorted(owners)}"

    missing = undocumented(plugins, _documented())

    assert not missing, f"document these variables in {ENV_EXAMPLE.name} (section «Plugins»): {missing}"
    shipped = sum(1 for _family, _code, plugin in plugins if not plugin.test_only and plugin.settings_fields)
    print_success(f"{len(plugins)} plugins registered, {shipped} shipped with fields, nothing undocumented")


# =============================================================================
# 2. ONE OWNER PER VARIABLE
# =============================================================================


def test_the_collision_guard_flags_two_fields_on_one_variable():
    """2, barrier: ``foo_bar``/``baz`` and ``foo``/``bar_baz`` derive one name; two families sharing an alias; a family alone is fine."""
    foo_bar = _declaration("LabFooBar", (_plain("baz"),))
    foo = _declaration("LabFoo", (_plain("bar_baz"),))
    with_alias = _declaration("LabAlias", (_secret("api_key", "LIBREFOLIO_LAB_SHARED"),))

    found = collisions([("asset", "lab_foo_bar", foo_bar), ("asset", "lab_foo", foo), ("asset", "lab_a", with_alias), ("fx", "lab_b", with_alias), ("fx", "lab_foo", foo)])

    assert found == {
        "LIBREFOLIO_PLUGIN_ASSET_LAB_FOO_BAR_BAZ": ["asset/lab_foo_bar/baz", "asset/lab_foo/bar_baz"],
        "LIBREFOLIO_LAB_SHARED": ["asset/lab_a/api_key", "fx/lab_b/api_key"],
    }


def test_no_two_fields_of_the_registered_plugins_read_one_variable():
    """2: test-only plugins included: a test double's variable is a variable all the same."""
    found = collisions(_registered())
    assert not found, f"variables read by more than one field: {found}"


def test_every_variable_of_a_registered_plugin_is_claimed_by_that_plugin():
    """2: registration claimed them (``claim_env_variables``): the runtime half of the rule is in force."""
    print_section("2: the claims of the registered plugins")
    plugins = _registered()
    claims = claimed_env_variables()
    assert claims.get("LIBREFOLIO_MOCKPROV_API_KEY") == ("asset", "mockprov"), "barrier: mockprov's alias is claimed by mockprov"
    assert claims.get(env_name("fx", "MOCKFX", "decimals")) == ("fx", "MOCKFX"), "barrier: MOCKFX's derived names are claimed by MOCKFX"

    wrong = {variable: claims.get(variable) for family, code, _declared, variable in _variables(plugins) if claims.get(variable) != (family, code)}

    assert not wrong, f"variables not claimed by their own plugin: {wrong}"
    print_success(f"{sum(1 for _ in _variables(plugins))} variables, each claimed by its plugin")


def test_the_settings_families_their_registries_and_the_declarations_agree():
    """2: one registry per family with rules, naming that family; every registered declaration valid; no refused one in discovery."""
    assert set(FAMILY_REGISTRIES) == set(FAMILY_RULES)
    assert {family: registry.settings_family() for family, registry in FAMILY_REGISTRIES.items()} == {family: family for family in FAMILY_REGISTRIES}
    for family, _code, plugin_class in _registered():
        if plugin_class.settings_fields:
            validate_declaration(plugin_class.settings_fields, family=family)
    refused = [failure for registry in FAMILY_REGISTRIES.values() for failure in registry.get_discovery_errors() if failure.error_type == SettingsDeclarationError.__name__]
    assert not refused, f"plugins refused for their declaration: {refused}"
    assert MockProvider in (plugin for _family, _code, plugin in _registered()) and MockFXProvider in (plugin for _family, _code, plugin in _registered())


# =============================================================================
# 3. NO ALIAS IS A VARIABLE LIBREFOLIO READS ITSELF
# =============================================================================


def test_the_scan_sees_the_variables_the_application_reads():
    """3, barrier: a key read through ``env_secret``, its ``_FILE``, and a ``Settings`` field are all seen."""
    read = _application_variables()
    assert {"LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_INSTANCE_KEY_FILE", "JWT_SECRET", "LIBREFOLIO_PROFILE"} <= read


@pytest.mark.parametrize("alias", ["LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_PROFILE", "LIBREFOLIO_WEB_LINK_FINDER_API_KEY"])
def test_an_alias_naming_a_variable_of_the_application_is_flagged(alias):
    """3, barrier: valid as a declaration and claimed by nobody else, so only this guard stops it."""
    print_section(f"3: an alias {alias}")
    declaration = _declaration("LabGreedy", (_secret("api_key", alias),))
    validate_declaration(declaration.settings_fields, family="asset")

    flagged = aliases_read_by_the_application([("asset", "lab_greedy", declaration)], _application_variables())

    assert flagged and flagged[0] == f"asset/lab_greedy/api_key: {alias}", flagged
    print_success(f"flagged: {flagged}")


def test_an_alias_of_its_own_is_not_flagged():
    declaration = _declaration("LabOwn", (_secret("api_key", "LIBREFOLIO_LAB_ONLY_MINE"),))
    assert aliases_read_by_the_application([("asset", "lab_own", declaration)], _application_variables()) == []


def test_no_alias_of_a_registered_plugin_is_a_variable_of_the_application():
    """3: every registered plugin, test-only ones included."""
    plugins = _registered()
    assert any(declared.env for _family, _code, plugin in plugins for declared in plugin.settings_fields), "barrier: at least one registered alias is checked (mockprov's)"

    flagged = aliases_read_by_the_application(plugins, _application_variables())

    assert not flagged, f"aliases that name a variable LibreFolio reads itself: {flagged}"


def test_the_derived_namespace_belongs_to_the_derived_names():
    """3: the application reads no ``LIBREFOLIO_PLUGIN_…`` variable with a literal name; the detector would see one."""
    synthetic = environment_reads({"synthetic.py": 'import os\nos.environ.get("LIBREFOLIO_PLUGIN_ASSET_X_KEY")\n'})
    assert [name for name in synthetic if name.startswith(ENV_PREFIX)] == ["LIBREFOLIO_PLUGIN_ASSET_X_KEY"], "barrier: the detector sees such a read"

    taken = sorted(name for name in _application_reads() if name.startswith(ENV_PREFIX))

    assert not taken, f"the application reads variables of the derived namespace: {taken}"


# =============================================================================
# 4. AI EXPORT NEVER READS THE PLUGIN SETTINGS
# =============================================================================

_SETTINGS_PACKAGE = "backend.app.services.plugin_settings"
_MODELS = frozenset({"PluginSystemSetting", "PluginUserSetting"})
_TABLES = ("plugin_system_settings", "plugin_user_settings")


def _absolute(module: str | None, level: int, package: str) -> str:
    """The module a ``from … import`` names, relative ones resolved against ``package``."""
    if level == 0:
        return module or ""
    parts = package.split(".")
    base = parts[: len(parts) - (level - 1)]
    return ".".join([*base, module] if module else base)


def _in_package(module: str) -> bool:
    return module == _SETTINGS_PACKAGE or module.startswith(_SETTINGS_PACKAGE + ".")


def plugin_settings_uses(source: str, module_name: str, *, is_package: bool = False) -> list[str]:
    """Every way ``source`` reaches the plugin settings: imports, the two models, their tables, a dynamic import."""
    package = module_name if is_package else module_name.rpartition(".")[0]
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend(f"line {node.lineno}: import {alias.name}" for alias in node.names if _in_package(alias.name))
        elif isinstance(node, ast.ImportFrom):
            target = _absolute(node.module, node.level, package)
            names = {alias.name for alias in node.names}
            if _in_package(target) or (target == "backend.app.services" and "plugin_settings" in names):
                found.append(f"line {node.lineno}: from {target} import {sorted(names)}")
            elif target.startswith("backend.app.db") and names & (_MODELS | {"*"}):
                found.append(f"line {node.lineno}: from {target} import {sorted(names & (_MODELS | {'*'}))}")
        elif isinstance(node, ast.Attribute) and node.attr in _MODELS:
            found.append(f"line {node.lineno}: .{node.attr}")
        elif isinstance(node, ast.Name) and node.id in _MODELS:
            found.append(f"line {node.lineno}: {node.id}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and (any(table in node.value for table in _TABLES) or "services.plugin_settings" in node.value):
            found.append(f"line {node.lineno}: {node.value[:60]!r}")
    return found


def imported_modules(source: str, module_name: str, *, is_package: bool = False) -> set[str]:
    """The modules ``source`` imports, relative ones resolved: the presence barrier of the scan."""
    package = module_name if is_package else module_name.rpartition(".")[0]
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(_absolute(node.module, node.level, package))
    return modules


_INSIDE = "backend.app.services.ai_export.components.lab"


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("import backend.app.services.plugin_settings.crypto\n", id="import"),
        pytest.param("from backend.app.services.plugin_settings.service import read_catalogue\n", id="from-a-module"),
        pytest.param("from backend.app.services import plugin_settings\n", id="from-the-services-package"),
        pytest.param("from ...plugin_settings import fields\n", id="relative"),
        pytest.param("from backend.app.db.models import Asset, PluginUserSetting\n", id="a-model-by-name"),
        pytest.param("from backend.app.db.models import *\n", id="star-import"),
        pytest.param("from backend.app.db import models\nrows = models.PluginSystemSetting\n", id="a-model-by-attribute"),
        pytest.param('from sqlalchemy import text\nquery = text("SELECT * FROM plugin_user_settings")\n', id="a-table-in-sql"),
        pytest.param('import importlib\nimportlib.import_module("backend.app.services.plugin_settings.crypto")\n', id="importlib"),
    ],
)
def test_the_ai_export_guard_sees_every_way_in(source):
    """4, barrier: each shape alone in a synthetic module of ``ai_export/components/``."""
    assert plugin_settings_uses(source, _INSIDE), f"not flagged: {source!r}"


def test_the_ai_export_guard_flags_nothing_in_a_clean_module():
    source = "import json\nfrom backend.app.db.models import Asset, Broker\nfrom .._int_validation import require_positive_int\nfrom .spec import X\n"
    assert plugin_settings_uses(source, _INSIDE) == []
    assert imported_modules(source, _INSIDE) == {"json", "backend.app.db.models", "backend.app.services.ai_export._int_validation", "backend.app.services.ai_export.components.spec"}


def test_nothing_under_ai_export_reaches_the_plugin_settings():
    """4: every module of ``services/ai_export/``; the scan must reach them, and see their real imports."""
    print_section("4: services/ai_export/ and the plugin settings")
    files = sorted(AI_EXPORT_ROOT.rglob("*.py"))
    found: dict[str, list[str]] = {}
    imports: set[str] = set()
    for path in files:
        relative = path.relative_to(REPO_ROOT).with_suffix("")
        is_package = path.name == "__init__.py"
        module_name = ".".join(relative.parent.parts if is_package else relative.parts)
        source = path.read_text(encoding="utf-8")
        imports |= imported_modules(source, module_name, is_package=is_package)
        if uses := plugin_settings_uses(source, module_name, is_package=is_package):
            found[path.relative_to(APP_ROOT).as_posix()] = uses

    assert len(files) >= 40, f"barrier: the scan reached {len(files)} modules of {AI_EXPORT_ROOT}"
    assert {"backend.app.db.models", "backend.app.services.ai_export._int_validation"} <= imports, "barrier: the scan sees the real imports, absolute and relative"
    assert not found, f"AI Export reaches the plugin settings: {found}"
    print_success(f"{len(files)} modules, none reaches the plugin settings")
