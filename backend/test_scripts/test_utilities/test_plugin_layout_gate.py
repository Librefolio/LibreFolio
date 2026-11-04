"""
Gate of the plugin layout (workstream U, step U-1): every first-party plugin is a folder.

Families under guard, in ``backend/app/services/``: ``brim_providers``, ``asset_source_providers``, ``fx_providers``,
``risk_plugins``, ``signal_plugins`` and ``tool_plugins`` — the folders the application's registries discover, which
this gate reads back from their declarations.

A plugin is the folder ``<family>/<name>/``. Its ``__init__.py`` is its docstring and nothing else; its code is in
``plugin.py``, which discovery loads as ``backend.app.services.<family>.<name>.plugin`` once the package is loaded; a
helper private to it sits beside it as ``_*.py``, one shared by the family at the family root, as ``_*.py`` too.
Discovery still loads a single ``<name>.py`` module, for test fixtures and test registries: this gate is what keeps the
first-party families off it. Three rules:

(a) Convention, per family: no top-level ``*.py`` besides ``__init__.py`` and the ``_*.py`` helpers (a contract lives
    in its family's runtime package, as ``services/signals/base.py`` does); every folder discovery loads — not ``_``-prefixed, holding ``__init__.py`` or
    ``plugin.py`` — holds both; every plugin ``__init__.py`` is its docstring and nothing else; and the family has at
    least one plugin folder. A folder holding neither file is data (``static/``, ``sample_reports/``).
(b) Imports, over ``backend/app``, ``backend/test_scripts``, ``scripts`` and ``dev.py``: nothing imports a plugin's
    package for what it holds, since it holds nothing. ``from backend.app.services.<family> import <plugin>``,
    ``import backend.app.services.<family>.<plugin>`` and ``from backend.app.services.<family>.<plugin> import X`` are
    rejected, unless ``X`` is ``plugin`` or a ``_helper``. Relative forms resolve as the interpreter resolves them, and
    an import inside a function or under ``if TYPE_CHECKING:`` counts like a top-level one.
(c) Strings, same scope: no string constant names ``backend.app.services.<family>.<plugin>`` unless ``.plugin`` or a
    ``._helper`` follows — a ``patch()`` target, a logger name, a ``__module__`` assertion, an ``import_module``
    argument, a docstring.

Pure: the sources are parsed with ``ast`` and read from the filesystem, never imported — no database, no server, no
network; the control cases build their trees under ``tmp_path``. Every rule asserts an absence, so each detector first
proves on synthetic input that it sees a presence and leaves the allowed shapes alone, and the scans must reach every
family and every root (an empty parametrization would be skipped, never red). The control cases name a family no real
one is called, ``gate_probe_plugins``: this file is scanned too, and must never name a real plugin package.
"""

from __future__ import annotations

import ast
import functools
import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.util import resolve_name
from pathlib import Path

import pytest

from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICES_DIR = REPO_ROOT / "backend" / "app" / "services"
SERVICES_PACKAGE = "backend.app.services"
PROVIDER_REGISTRY = SERVICES_DIR / "provider_registry.py"

PLUGIN_FAMILIES = ("brim_providers", "asset_source_providers", "fx_providers", "risk_plugins", "signal_plugins", "tool_plugins")
# The module of a plugin folder that holds its code: provider_registry.PLUGIN_MODULE_NAME, read back from its source.
PLUGIN_MODULE = "plugin"
PLUGIN_FILE = f"{PLUGIN_MODULE}.py"
PACKAGE_FILE = "__init__.py"
# Top-level modules a family keeps besides __init__.py and its _*.py helpers: none. The signal plugins' contract left
# their folder for services/signals/base.py (CP-10b), so a base.py back in a plugin folder is a stray module.
ROOT_MODULES: dict[str, frozenset[str]] = {}
# The classmethods through which a registry names the family folder it discovers.
FAMILY_DECLARATIONS = frozenset({"_get_plugin_folder", "_get_provider_folder"})

# (b) and (c): everything that could import or name a plugin.
SCAN_ROOTS = ("backend/app", "backend/test_scripts", "scripts", "dev.py")


# =============================================================================
# Detectors
# =============================================================================


def _is_plugin_folder(entry: Path) -> bool:
    """What discovery loads as a plugin: a folder, not ``_``-prefixed, holding ``__init__.py`` or ``plugin.py``."""
    return entry.is_dir() and not entry.name.startswith("_") and ((entry / PACKAGE_FILE).exists() or (entry / PLUGIN_FILE).exists())


def plugin_folders(family_dir: Path) -> list[Path]:
    return sorted(entry for entry in family_dir.iterdir() if _is_plugin_folder(entry))


def stray_root_modules(family_dir: Path, allowed: frozenset[str] = frozenset()) -> list[str]:
    """The family's top-level ``*.py`` neither ``_``-prefixed (``__init__.py``, the helpers) nor allowed: plugins
    written as a single module."""
    return sorted(path.name for path in family_dir.glob("*.py") if path.is_file() and not path.name.startswith("_") and path.name not in allowed)


def incomplete_plugin_folders(family_dir: Path) -> list[str]:
    """``<name>/ has no <file>`` for every plugin folder that lacks its ``__init__.py`` or its ``plugin.py``."""
    return [f"{folder.name}/ has no {required}" for folder in plugin_folders(family_dir) for required in (PACKAGE_FILE, PLUGIN_FILE) if not (folder / required).is_file()]


def _has_docstring(tree: ast.Module) -> bool:
    first = tree.body[0] if tree.body else None
    return isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)


def init_offenders(source: str) -> list[str]:
    """What an ``__init__.py`` holds besides its docstring, after ``no docstring`` when it has none."""
    tree = ast.parse(source)
    documented = _has_docstring(tree)
    found = [f"line {statement.lineno}: {ast.get_source_segment(source, statement)}" for statement in (tree.body[1:] if documented else tree.body)]
    return found if documented else ["no docstring", *found]


def plugin_init_offenders(family_dir: Path) -> list[str]:
    """``<name>/__init__.py: <what>`` for every plugin package that is anything but its docstring."""
    return [f"{folder.name}/{PACKAGE_FILE}: {what}" for folder in plugin_folders(family_dir) if (folder / PACKAGE_FILE).is_file() for what in init_offenders((folder / PACKAGE_FILE).read_text(encoding="utf-8"))]


def plugin_index(services_dir: Path, families: tuple[str, ...]) -> dict[str, frozenset[str]]:
    """Each family's plugin folder names: what an import or a string may reach only through ``.plugin``."""
    return {family: frozenset(folder.name for folder in plugin_folders(services_dir / family)) if (services_dir / family).is_dir() else frozenset() for family in families}


def names_a_plugin_package(dotted: str, index: Mapping[str, frozenset[str]]) -> bool:
    """True when ``dotted`` stops at a plugin's package, or goes on past it to anything but ``plugin`` or a ``_helper``."""
    prefix = SERVICES_PACKAGE + "."
    if not dotted.startswith(prefix):
        return False
    family, _, rest = dotted.removeprefix(prefix).partition(".")
    name, _, inside = rest.partition(".")
    if name not in index.get(family, frozenset()):
        return False
    head = inside.partition(".")[0]
    return head != PLUGIN_MODULE and not head.startswith("_")


def plugin_package_imports(tree: ast.AST, package: str, index: Mapping[str, frozenset[str]]) -> list[tuple[int, str]]:
    """``(line, what)`` for every import in ``tree`` that reaches a plugin's package instead of its module.

    ``import a.b`` reaches ``a.b``; ``from a import b`` reaches ``a.b``, whether ``b`` is a submodule or a name of
    ``a``: from a package that re-exports nothing, a name is a defect too. Relative forms resolve against ``package``,
    as the interpreter does; ``ast.walk`` visits every node, so an import inside a function or under
    ``if TYPE_CHECKING:`` counts like a top-level one.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names if names_a_plugin_package(alias.name, index))
        elif isinstance(node, ast.ImportFrom):
            try:
                base = resolve_name("." * node.level + (node.module or ""), package)
            except ImportError:
                continue  # above the top-level package: it fails at import time, and it names no plugin
            found.extend((node.lineno, f"{base}.{alias.name}") for alias in node.names if names_a_plugin_package(f"{base}.{alias.name}", index))
    return sorted(found)


# A dotted name under backend.app.services, whole: never the tail of a longer dotted name.
_DOTTED_NAME = re.compile(r"(?<![\w.])backend\.app\.services(?:\.[A-Za-z_][A-Za-z0-9_]*)+")


def plugin_package_strings(tree: ast.AST, index: Mapping[str, frozenset[str]]) -> list[tuple[int, str]]:
    """``(line, name)`` for every dotted name in a string constant of ``tree`` that names a plugin's package.

    Every ``str`` constant counts: a docstring, a ``patch()`` target, a logger name, the literal parts of an f-string.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.extend((node.lineno, match.group(0)) for match in _DOTTED_NAME.finditer(node.value) if names_a_plugin_package(match.group(0), index))
    return sorted(found)


def declared_families(tree: ast.AST) -> set[str]:
    """The family folders a module's registries declare: the literals ``_get_plugin_folder`` / ``_get_provider_folder``
    return."""
    return {statement.value.value for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in FAMILY_DECLARATIONS for statement in node.body if isinstance(statement, ast.Return) and isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str)}


def module_constant(tree: ast.Module, name: str) -> object:
    """The literal a module binds to ``name`` at its top level."""
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in statement.targets):
            return ast.literal_eval(statement.value)
    raise LookupError(f"no top-level assignment to {name}")


# =============================================================================
# The repository
# =============================================================================


def _python_files(root: str) -> list[Path]:
    """Every ``.py`` of a scan root, bytecode caches aside; a root that is a file is itself."""
    path = REPO_ROOT / root
    if path.is_file():
        return [path]
    return sorted(file for file in path.rglob("*.py") if "__pycache__" not in file.relative_to(path).parts)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _package_of(path: Path) -> str:
    """The package a file's relative imports resolve against: its folder, dotted from the repository root."""
    return ".".join(path.relative_to(REPO_ROOT).parts[:-1])


@dataclass(frozen=True)
class _RootScan:
    """What one scan root holds for (b) and (c), and the families its registries declare."""

    files: tuple[str, ...]
    imports: tuple[str, ...]
    strings: tuple[str, ...]
    families: frozenset[str]


@functools.cache
def _scan(root: str) -> _RootScan:
    """Each file of ``root`` parsed once, its tree dropped as soon as it is read: kept, the trees of the four roots would
    weigh hundreds of megabytes. Only the findings are cached, once per process."""
    index = plugin_index(SERVICES_DIR, PLUGIN_FAMILIES)
    files: list[str] = []
    imports: list[str] = []
    strings: list[str] = []
    families: set[str] = set()
    for path in _python_files(root):
        relative = path.relative_to(REPO_ROOT).as_posix()
        tree = _parse(path)
        files.append(relative)
        imports.extend(f"{relative}:{line} reaches {target}" for line, target in plugin_package_imports(tree, _package_of(path), index))
        strings.extend(f"{relative}:{line} names {name}" for line, name in plugin_package_strings(tree, index))
        families.update(declared_families(tree))
    return _RootScan(tuple(files), tuple(imports), tuple(strings), frozenset(families))


def _write_tree(root: Path, files: Mapping[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


# =============================================================================
# The detectors see what they look for
# =============================================================================

_PROBE_FAMILY = "gate_probe_plugins"
_PROBE = f"{SERVICES_PACKAGE}.{_PROBE_FAMILY}"
# Two plugin folders whose names share a prefix: a match must take a whole name, never a prefix of one.
_PROBE_INDEX = {_PROBE_FAMILY: frozenset({"alpha", "alpha_deposit"})}
# Where the relative forms are written from: the plugin module of alpha/.
_PROBE_PACKAGE = f"{_PROBE}.alpha"

# Every import shape (b) must reject, written from alpha/plugin.py: (source, line, what it reaches).
_FORBIDDEN_IMPORTS = (
    ("from backend.app.services.gate_probe_plugins import alpha", 1, f"{_PROBE}.alpha"),
    ("from backend.app.services.gate_probe_plugins import _shared, alpha_deposit", 1, f"{_PROBE}.alpha_deposit"),
    ("from backend.app.services import gate_probe_plugins\nfrom backend.app.services.gate_probe_plugins import alpha as a\n", 2, f"{_PROBE}.alpha"),
    ("import backend.app.services.gate_probe_plugins.alpha", 1, f"{_PROBE}.alpha"),
    ("import os, backend.app.services.gate_probe_plugins.alpha_deposit as deposit", 1, f"{_PROBE}.alpha_deposit"),
    ("from backend.app.services.gate_probe_plugins.alpha import AlphaProvider", 1, f"{_PROBE}.alpha.AlphaProvider"),
    ("from backend.app.services.gate_probe_plugins.alpha import *", 1, f"{_PROBE}.alpha.*"),
    ("from backend.app.services.gate_probe_plugins.alpha.parsers import parse", 1, f"{_PROBE}.alpha.parsers.parse"),
    ("from . import AlphaProvider", 1, f"{_PROBE}.alpha.AlphaProvider"),
    ("from .. import alpha_deposit", 1, f"{_PROBE}.alpha_deposit"),
    ("from ..alpha_deposit import DepositProvider", 1, f"{_PROBE}.alpha_deposit.DepositProvider"),
    ("def load():\n    import backend.app.services.gate_probe_plugins.alpha\n", 2, f"{_PROBE}.alpha"),
    ("from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from backend.app.services.gate_probe_plugins import alpha\n", 4, f"{_PROBE}.alpha"),
)

# What (b) leaves alone, from the same module: none of it may be flagged.
_ALLOWED_IMPORTS = (
    "from backend.app.services.gate_probe_plugins.alpha import plugin",
    "from backend.app.services.gate_probe_plugins.alpha import plugin as alpha_module",
    "from backend.app.services.gate_probe_plugins.alpha.plugin import AlphaProvider",
    "import backend.app.services.gate_probe_plugins.alpha.plugin",
    "import backend.app.services.gate_probe_plugins.alpha_deposit.plugin as deposit_module",
    "from backend.app.services.gate_probe_plugins.alpha._parsers import parse",
    "from backend.app.services.gate_probe_plugins.alpha import _parsers",
    "from backend.app.services.gate_probe_plugins import _shared",
    "from backend.app.services.gate_probe_plugins import ProbeBase",  # a name of the family package, no plugin
    "from backend.app.services.gate_probe_plugins import alphabet",  # a whole name: alpha is not alphabet
    "from backend.app.services import gate_probe_plugins",
    "import backend.app.services.gate_probe_plugins",
    "from backend.app.services.other_plugins import alpha",  # another family, where alpha is no plugin
    "from . import plugin",
    "from ._parsers import parse",
    "from .. import _shared",
    "from ..alpha_deposit import plugin",
    "from ..alpha_deposit.plugin import DepositProvider",
)

# Every string shape (c) must reject: (source, line, the name it flags).
_FORBIDDEN_STRINGS = (
    ('patch("backend.app.services.gate_probe_plugins.alpha.httpx.AsyncClient")', 1, f"{_PROBE}.alpha.httpx.AsyncClient"),
    ('caplog.set_level("INFO", logger="backend.app.services.gate_probe_plugins.alpha_deposit")', 1, f"{_PROBE}.alpha_deposit"),
    ('assert AlphaProvider.__module__ == "backend.app.services.gate_probe_plugins.alpha"', 1, f"{_PROBE}.alpha"),
    ('importlib.import_module("backend.app.services.gate_probe_plugins.alpha")', 1, f"{_PROBE}.alpha"),
    ('"""See backend.app.services.gate_probe_plugins.alpha_deposit for the rules."""', 1, f"{_PROBE}.alpha_deposit"),
    ('target = f"{root}:backend.app.services.gate_probe_plugins.alpha:AlphaProvider"', 1, f"{_PROBE}.alpha"),
    ('TARGETS = (\n    "backend.app.services.gate_probe_plugins.alpha.plugin",\n    "backend.app.services.gate_probe_plugins.alpha_deposit.parsers",\n)\n', 3, f"{_PROBE}.alpha_deposit.parsers"),
)

# What (c) leaves alone: none of it may be flagged.
_ALLOWED_STRINGS = (
    'patch("backend.app.services.gate_probe_plugins.alpha.plugin.httpx.AsyncClient")',
    'caplog.set_level("INFO", logger="backend.app.services.gate_probe_plugins.alpha_deposit.plugin")',
    'PARSERS = "backend.app.services.gate_probe_plugins.alpha._parsers"',
    'FAMILY = "backend.app.services.gate_probe_plugins"',
    'SHARED = "backend.app.services.gate_probe_plugins._shared"',
    'BASE = "backend.app.services.gate_probe_plugins.ProbeBase"',
    'OTHER = "backend.app.services.gate_probe_plugins.alphabet"',
    'PATH = "backend/app/services/gate_probe_plugins/alpha/plugin.py"',  # a path, not a module name
    'LONGER = "vendor.backend.app.services.gate_probe_plugins.alpha"',  # the tail of another dotted name
    "TEMPLATE = 'backend.app.services.gate_probe_plugins.{name}'",
)

# ``__init__.py`` sources and what (a) must report in each.
_INIT_SHAPES = (
    ('"""Plugin alpha: the code is in plugin.py."""\n', []),
    ("", ["no docstring"]),
    ("# a comment is not a docstring\n", ["no docstring"]),
    ('"""Doc."""\nfrom .plugin import AlphaProvider\n', ["line 2: from .plugin import AlphaProvider"]),
    ('"""Doc."""\nfrom . import plugin\n', ["line 2: from . import plugin"]),
    ('"""Doc."""\n__all__ = ["AlphaProvider"]\n', ['line 2: __all__ = ["AlphaProvider"]']),
    ('"""Doc."""\n"""A second string is a statement, not the docstring."""\n', ['line 2: """A second string is a statement, not the docstring."""']),
    ("import os\n", ["no docstring", "line 1: import os"]),
)

# A family breaking each rule of (a) once, beside what (a) accepts.
_BROKEN_FAMILY = {
    "__init__.py": '"""The family package may re-export its base: it is no plugin."""\nfrom .base import ProbeBase\n',
    "base.py": "class ProbeBase: ...\n",
    "_shared.py": "",
    "loose.py": "",  # a plugin written as a single module
    "good/__init__.py": '"""Good."""\n',
    "good/plugin.py": "",
    "good/_parsers.py": "",
    "no_module/__init__.py": '"""No module."""\n',
    "no_package/plugin.py": "",
    "reexport/__init__.py": '"""Re-exports."""\nfrom .plugin import AlphaProvider\n',
    "reexport/plugin.py": "",
    "bare/__init__.py": "",
    "bare/plugin.py": "",
    "static/logo.svg": "<svg/>\n",  # data
    "sample_reports/make_sample.py": "",  # data, a module among its files
    "_private/plugin.py": "",  # private: no plugin
}

# The same family once repaired: (a) finds nothing.
_CLEAN_FAMILY = {
    "__init__.py": '"""The family."""\n',
    "_shared.py": "",
    "good/__init__.py": '"""Good."""\n',
    "good/plugin.py": "",
    "good/_parsers.py": "",
    "static/logo.svg": "<svg/>\n",
}


def test_the_import_matcher_flags_every_forbidden_shape_and_nothing_allowed():
    print_section("Plugin layout: the import matcher")
    for source, line, target in _FORBIDDEN_IMPORTS:
        assert plugin_package_imports(ast.parse(source), _PROBE_PACKAGE, _PROBE_INDEX) == [(line, target)], source
    assert plugin_package_imports(ast.parse("\n".join(_ALLOWED_IMPORTS)), _PROBE_PACKAGE, _PROBE_INDEX) == []
    print_success(f"{len(_FORBIDDEN_IMPORTS)} forbidden shapes flagged, {len(_ALLOWED_IMPORTS)} allowed ones left alone")


def test_the_string_matcher_flags_a_plugin_package_and_leaves_its_module_alone():
    print_section("Plugin layout: the string matcher")
    for source, line, name in _FORBIDDEN_STRINGS:
        assert plugin_package_strings(ast.parse(source), _PROBE_INDEX) == [(line, name)], source
    assert plugin_package_strings(ast.parse("\n".join(_ALLOWED_STRINGS)), _PROBE_INDEX) == []
    print_success(f"{len(_FORBIDDEN_STRINGS)} forbidden strings flagged, {len(_ALLOWED_STRINGS)} allowed ones left alone")


def test_the_init_check_reports_anything_besides_the_docstring():
    print_section("Plugin layout: the __init__ check")
    for source, expected in _INIT_SHAPES:
        assert init_offenders(source) == expected, source
    print_success("an import, an assignment, __all__, a second string and a missing docstring are all reported")


def test_the_family_checks_flag_every_breach_of_a_synthetic_family_and_nothing_once_repaired(tmp_path):
    print_section("Plugin layout: the family checks")
    broken, clean = tmp_path / "broken_plugins", tmp_path / "clean_plugins"
    _write_tree(broken, _BROKEN_FAMILY)
    _write_tree(clean, _CLEAN_FAMILY)

    assert [folder.name for folder in plugin_folders(broken)] == ["bare", "good", "no_module", "no_package", "reexport"]
    assert stray_root_modules(broken) == ["base.py", "loose.py"]
    assert stray_root_modules(broken, frozenset({"base.py"})) == ["loose.py"]
    assert incomplete_plugin_folders(broken) == ["no_module/ has no plugin.py", "no_package/ has no __init__.py"]
    assert plugin_init_offenders(broken) == ["bare/__init__.py: no docstring", "reexport/__init__.py: line 2: from .plugin import AlphaProvider"]
    assert plugin_index(tmp_path, ("broken_plugins", "absent_plugins")) == {"broken_plugins": frozenset({"bare", "good", "no_module", "no_package", "reexport"}), "absent_plugins": frozenset()}

    assert [folder.name for folder in plugin_folders(clean)] == ["good"]
    assert (stray_root_modules(clean), incomplete_plugin_folders(clean), plugin_init_offenders(clean)) == ([], [], [])
    print_success("a single-module plugin, a folder missing either file and a package beyond its docstring are reported; data and private folders are not")


def test_the_registry_readers_find_the_declared_families_and_the_plugin_module():
    print_section("Plugin layout: the registry readers")
    source = (
        "class Registry:\n"
        "    @classmethod\n"
        "    def _get_plugin_folder(cls) -> str:\n"
        '        """Docstring."""\n'
        '        return "gate_probe_plugins"\n'
        "class Providers(Registry):\n"
        "    @classmethod\n"
        "    def _get_provider_folder(cls) -> str:\n"
        '        return "gate_probe_providers"\n'
        "class Abstract:\n"
        "    @classmethod\n"
        "    def _get_plugin_folder(cls) -> str:\n"
        "        return cls._get_provider_folder()\n"
        "    def _get_other_folder(cls) -> str:\n"
        '        return "not_a_family"\n'
        'PLUGIN_MODULE_NAME = "plugin"\n'
    )
    tree = ast.parse(source)
    assert declared_families(tree) == {"gate_probe_plugins", "gate_probe_providers"}
    assert module_constant(tree, "PLUGIN_MODULE_NAME") == "plugin"
    with pytest.raises(LookupError):
        module_constant(tree, "ABSENT")
    print_success("a literal family is read, a computed one and any other method are not; the module constant is read")


def test_the_scans_reach_every_family_and_every_root():
    print_section("Plugin layout: the scans reach the tree")
    missing = [family for family in PLUGIN_FAMILIES if not (SERVICES_DIR / family).is_dir()]
    assert not missing, f"no such family under {SERVICES_DIR}: {missing}. The repository root derived from this file is wrong, or a family moved"
    empty_roots = [root for root in SCAN_ROOTS if not _scan(root).files]
    assert not empty_roots, f"no Python file under {empty_roots}: the import and string scans would pass on nothing"
    scanned = {relative for root in SCAN_ROOTS for relative in _scan(root).files}
    anchors = {"dev.py", PROVIDER_REGISTRY.relative_to(REPO_ROOT).as_posix(), "scripts/test_runner/_backend_utils.py", Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()}
    assert anchors <= scanned, f"the scans missed {sorted(anchors - scanned)}"
    assert (_package_of(REPO_ROOT / "dev.py"), _package_of(SERVICES_DIR / _PROBE_FAMILY / "alpha" / PLUGIN_FILE)) == ("", _PROBE_PACKAGE)
    print_success(f"{len(PLUGIN_FAMILIES)} families, {len(scanned)} files under {len(SCAN_ROOTS)} roots")


def test_the_gate_guards_what_discovery_loads():
    """The families are those the application's registries declare, and ``plugin`` is the module discovery loads."""
    print_section("Plugin layout: the gate follows discovery")
    declared = _scan("backend/app").families
    assert declared == set(PLUGIN_FAMILIES), f"the registries of backend/app discover {sorted(declared)}, the gate guards {sorted(PLUGIN_FAMILIES)}: a family is unguarded, or no longer exists"
    assert module_constant(_parse(PROVIDER_REGISTRY), "PLUGIN_MODULE_NAME") == PLUGIN_MODULE, "discovery loads a plugin folder's code from another module than the one this gate checks"
    print_success(f"{len(declared)} families declared and guarded; discovery loads <name>/{PLUGIN_FILE}")


# =============================================================================
# The rules
# =============================================================================


@pytest.mark.parametrize("family", PLUGIN_FAMILIES)
def test_a_family_keeps_every_plugin_in_a_folder(family):
    """(a) No first-party plugin is a single module; and the family has a plugin, or the checks pass on nothing."""
    family_dir = SERVICES_DIR / family
    stray = stray_root_modules(family_dir, ROOT_MODULES.get(family, frozenset()))
    assert not stray, f"{family} keeps plugins as single modules: move each into <name>/plugin.py beside an <name>/__init__.py holding its docstring (a helper shared by the family is named _<name>.py):\n" + "\n".join(f"{family}/{name}" for name in stray)
    assert plugin_folders(family_dir), f"{family} has no plugin folder: the convention checks of this family would pass on nothing"
    print_success(f"{family}: {len(plugin_folders(family_dir))} plugin folders, no single-module plugin")


@pytest.mark.parametrize("family", PLUGIN_FAMILIES)
def test_a_plugin_folder_holds_its_package_and_its_plugin_module(family):
    """(a) Discovery loads a folder holding either file, and fails on it unless it holds both."""
    missing = incomplete_plugin_folders(SERVICES_DIR / family)
    assert not missing, "a plugin folder holds __init__.py (its docstring) and plugin.py (its code), and discovery fails on one lacking either:\n" + "\n".join(f"{family}/{entry}" for entry in missing)
    print_success(f"{family}: every plugin folder holds {PACKAGE_FILE} and {PLUGIN_FILE}")


@pytest.mark.parametrize("family", PLUGIN_FAMILIES)
def test_a_plugin_package_is_only_its_docstring(family):
    """(a) A plugin's package re-exports nothing: its code is reached through ``<name>.plugin``, and only that way."""
    offenders = plugin_init_offenders(SERVICES_DIR / family)
    assert not offenders, "a plugin's __init__.py holds its docstring and nothing else (no import, assignment or __all__):\n" + "\n".join(f"{family}/{offender}" for offender in offenders)
    print_success(f"{family}: every plugin package is its docstring")


@pytest.mark.parametrize("root", SCAN_ROOTS)
def test_no_import_reaches_a_plugin_package_instead_of_its_module(root):
    """(b) Import a plugin's module — ``….<family>.<name>.plugin`` or ``from ….<family>.<name> import plugin`` — never its package."""
    offenders = _scan(root).imports
    assert not offenders, "a plugin's package re-exports nothing: import from its plugin module (<family>.<name>.plugin) or a _helper beside it:\n" + "\n".join(offenders)
    print_success(f"{root}: no import reaches a plugin package")


@pytest.mark.parametrize("root", SCAN_ROOTS)
def test_no_string_names_a_plugin_package_instead_of_its_module(root):
    """(c) A ``patch()`` target, a logger name or a ``__module__`` names the plugin module, which holds the code."""
    offenders = _scan(root).strings
    assert not offenders, "a string names a plugin's package, which holds no code: name its plugin module (<family>.<name>.plugin) instead:\n" + "\n".join(offenders)
    print_success(f"{root}: no string names a plugin package")
