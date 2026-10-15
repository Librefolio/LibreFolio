"""
Guard of the PAC/Rebalancer engine's data boundary (decision D-J18).

Engine under guard: every ``.py`` file under ``backend/app/services/pac_allocator/``, recursively, except the
``source/`` subpackage (``planner``, ``solver``, ``compiler``, ``constraints``, ``objectives``, ``normalize``,
``proof``, ``planner_report``, ``ledger``, ``numeric``, ``models``, ``issues``, ``wire_numbers``, the package
``__init__`` and the ``evaluation/`` subpackage), plus every ``.py`` file of the Tool plugin that runs it,
``backend/app/services/tool_plugins/pac_allocator/``.

The rule, approved by the release coordinator on the developer's delegation: the engine is pure computation over
the request it is handed; it never touches the database and never imports the planner source. Reading the
database is the job of ``pac_allocator/source/``, the authenticated, read-only snapshot behind the planner's copy
actions, where the owner check and the selected scope live; it legitimately imports ``sqlalchemy`` and
``backend.app.db.models``. Concretely, no engine module imports one of these modules or anything below it:

* ``backend.app.services.pac_allocator.source`` — the planner source;
* ``sqlalchemy``;
* ``sqlmodel``;
* ``backend.app.db`` — models, sessions and the rest of the database package.

The decision names ``pac_allocator.source``, ``sqlalchemy`` and ``db.models``. ``sqlmodel`` and the whole
``backend.app.db`` package widen it on purpose, as the same rule stated at package level: a session is the
database as much as a model is, and the engine imports none of them today. The match stops at dotted boundaries
(the name is the module, or starts with the module and a dot), so ``sqlalchemy_utils`` and a sibling module named
``sources_extra`` are other modules, not modules below a forbidden one.

Every ``import`` and ``from ... import`` node counts, wherever it sits: module level, a function-level lazy import,
under ``if TYPE_CHECKING:``, inside ``try``. Relative imports resolve against the module's package as the
interpreter resolves them, and ``from X import Y`` reaches ``X`` and, when ``Y`` is a submodule, ``X.Y``: so
``from backend.app import db`` and ``from backend.app.services.pac_allocator import source`` are caught too.

What it protects: a plan computed from its request alone. Database facts reach the engine only through the
request; the source reads them, behind its owner check, for the request to carry. So the engine, Tool plugin
included, runs and is tested with no session to open and no rows to seed, and a database read slipped into it
would make a plan depend on whatever the tables hold when it runs: outside the request that describes the
scenario, and outside the owner check.

Pure: the sources are parsed with ``ast``, never imported — no database, no server, no network. Every rule asserts
an absence, so each detector first proves it sees a presence: the import matcher flags every forbidden shape of a
synthetic source and nothing allowed; the engine selection, run on a scratch tree, drops ``source/`` and nothing
else; the real scan reaches the engine's known modules and none of the source's (an empty parametrization would be
skipped, never red); the same matcher reports ``sqlalchemy`` and ``backend.app.db.models`` in the real planner
source, so leaving ``source/`` out is what keeps the engine scan green; and the guard goes red, naming file, line
and module, on a tampered in-memory copy of an engine module.
"""

from __future__ import annotations

import ast
from importlib.util import resolve_name
from pathlib import Path

import pytest

from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]
PAC_ROOT = REPO_ROOT / "backend" / "app" / "services" / "pac_allocator"
TOOL_PLUGIN_ROOT = REPO_ROOT / "backend" / "app" / "services" / "tool_plugins" / "pac_allocator"
SOURCE_PREFIX = "backend/app/services/pac_allocator/source/"

# What the engine never imports: each module and everything below it, matched on dotted boundaries.
FORBIDDEN_MODULES = (
    "backend.app.services.pac_allocator.source",
    "sqlalchemy",
    "sqlmodel",
    "backend.app.db",
)

# Presence barrier: engine files the scan must reach, relative to the repository root.
KNOWN_ENGINE_MODULES = (
    "backend/app/services/pac_allocator/__init__.py",
    "backend/app/services/pac_allocator/planner.py",
    "backend/app/services/pac_allocator/solver.py",
    "backend/app/services/pac_allocator/normalize.py",
    "backend/app/services/pac_allocator/evaluation/__init__.py",
    "backend/app/services/pac_allocator/evaluation/evaluator.py",
    "backend/app/services/pac_allocator/evaluation/economics.py",
    "backend/app/services/tool_plugins/pac_allocator/plugin.py",
)

# Positive control: planner source modules that read the database, so the matcher must report it in them.
DATABASE_READING_SOURCE_MODULES = (
    "backend/app/services/pac_allocator/source/loaders.py",
    "backend/app/services/pac_allocator/source/fx_quotes.py",
)


# =============================================================================
# Detectors
# =============================================================================


def _python_files(root: Path) -> list[Path]:
    """Every ``.py`` file under ``root``, recursively, outside bytecode caches."""
    return [path for path in root.rglob("*.py") if "__pycache__" not in path.relative_to(root).parts]


def _engine_files(pac_root: Path, plugin_root: Path) -> list[Path]:
    """The engine: the planner package without its ``source`` subpackage, plus the Tool plugin package."""
    source_root = pac_root / "source"
    return [path for root in (pac_root, plugin_root) for path in _python_files(root) if not path.is_relative_to(source_root)]


def _package_of(module: str) -> str:
    """The package a repository-relative module's relative imports resolve against: its directory (an ``__init__`` is its own package)."""
    return ".".join(Path(module).parts[:-1])


def _is_forbidden(name: str) -> bool:
    """``name`` is a forbidden module or lies below one: ``sqlalchemy.orm`` does, ``sqlalchemy_utils`` does not."""
    return any(name == forbidden or name.startswith(f"{forbidden}.") for forbidden in FORBIDDEN_MODULES)


def _forbidden_imports(source: str, package: str) -> list[tuple[int, str]]:
    """``(line, module)`` for every import in ``source`` that binds a forbidden module.

    ``import a.b`` binds ``a.b``; ``from a import b`` binds ``a`` and may bind the submodule ``a.b`` —
    ``from backend.app import db`` and ``from backend.app.services.pac_allocator import source`` are exactly that
    shape. Relative forms resolve against ``package``, as the interpreter does. ``ast.walk`` visits every node, so an
    import inside a function, under ``if TYPE_CHECKING:`` or in a ``try`` counts like a top-level one.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names if _is_forbidden(alias.name))
        elif isinstance(node, ast.ImportFrom):
            base = resolve_name("." * node.level + (node.module or ""), package)
            if _is_forbidden(base):
                found.append((node.lineno, base))
            else:
                found.extend((node.lineno, f"{base}.{alias.name}") for alias in node.names if _is_forbidden(f"{base}.{alias.name}"))
    return sorted(found)


def _offenders(module: str, source: str) -> list[str]:
    """The guard's report on one engine module: ``path:line imports module`` for every forbidden import."""
    return [f"{module}:{line} imports {target}" for line, target in _forbidden_imports(source, _package_of(module))]


# One parametrized case per file, so a failure names the file; the ids are repository-relative paths.
ENGINE_MODULES = sorted(path.relative_to(REPO_ROOT).as_posix() for path in _engine_files(PAC_ROOT, TOOL_PLUGIN_ROOT))
SOURCE_MODULES = sorted(path.relative_to(REPO_ROOT).as_posix() for path in _python_files(PAC_ROOT / "source"))


# =============================================================================
# The detectors see what they look for
# =============================================================================

# Synthetic sources are read as if they sat in this engine module, so relative forms resolve inside ``evaluation``.
SYNTHETIC_MODULE = "backend/app/services/pac_allocator/evaluation/synthetic.py"

# Every shape the guard must reject: (source, line, module it binds).
_FORBIDDEN_SHAPES = (
    ("import sqlalchemy", 1, "sqlalchemy"),
    ("import sqlalchemy.ext.asyncio as x", 1, "sqlalchemy.ext.asyncio"),
    ("import decimal, sqlalchemy.orm", 1, "sqlalchemy.orm"),
    ("from sqlalchemy import select", 1, "sqlalchemy"),
    ("import sqlmodel", 1, "sqlmodel"),
    ("from backend.app.db.models import Asset", 1, "backend.app.db.models"),
    ("from backend.app.db import models", 1, "backend.app.db"),
    ("from backend.app import db", 1, "backend.app.db"),
    ("import backend.app.db.session", 1, "backend.app.db.session"),
    ("from backend.app.services.pac_allocator.source.loaders import load_holding_rows", 1, "backend.app.services.pac_allocator.source.loaders"),
    ("from backend.app.services.pac_allocator import source", 1, "backend.app.services.pac_allocator.source"),
    ("from ..source import keys", 1, "backend.app.services.pac_allocator.source"),
    ("from .. import planner, source", 1, "backend.app.services.pac_allocator.source"),
    ("async def copy_facts(session):\n    from backend.app.services.pac_allocator.source.portfolio_allocation_source import build_portfolio_planner_source\n", 2, "backend.app.services.pac_allocator.source.portfolio_allocation_source"),
    ("from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from sqlalchemy.ext.asyncio import AsyncSession\n", 4, "sqlalchemy.ext.asyncio"),
    ("try:\n    import sqlmodel\nexcept ImportError:\n    sqlmodel = None\n", 2, "sqlmodel"),
)

# What the engine may import, from the same module: none of it may be flagged.
_ALLOWED_SHAPES = (
    "from backend.app.services.pac_allocator.evaluation.keys import fx_debit_key",
    "from .keys import fx_debit_key",
    "from backend.app.services.pac_allocator import planner",
    "from .. import planner",
    "from backend.app.schemas.pac_allocator.request import PacPlannerRequest",
    "import pyscipopt",
    "from backend.app.services.pac_allocator import sources_extra",  # a sibling of the source package, not below it
    "import sqlalchemy_utils",  # deliberate: same spelling, no dotted boundary, so another module than sqlalchemy
)

# The package each kind of engine module resolves relative imports against: an ``__init__`` its own package, a plain
# module its parent package. The Tool plugin's ``plugin.py`` is a plain module like ``evaluator.py``, and is not listed:
# no string may name a plugin's package (``test_plugin_layout_gate.py``, rule (c)).
_EXPECTED_PACKAGES = {
    "backend/app/services/pac_allocator/__init__.py": "backend.app.services.pac_allocator",
    "backend/app/services/pac_allocator/evaluation/evaluator.py": "backend.app.services.pac_allocator.evaluation",
}


def test_the_import_matcher_flags_every_forbidden_shape_and_nothing_allowed():
    print_section("Engine boundaries: the import matcher")
    package = _package_of(SYNTHETIC_MODULE)
    assert package == "backend.app.services.pac_allocator.evaluation"
    for source, line, module in _FORBIDDEN_SHAPES:
        assert _forbidden_imports(source, package) == [(line, module)], source
    assert _forbidden_imports("\n".join(_ALLOWED_SHAPES), package) == []
    print_success(f"{len(_FORBIDDEN_SHAPES)} forbidden shapes flagged, {len(_ALLOWED_SHAPES)} allowed ones left alone")


def test_the_engine_selection_drops_the_source_subpackage_and_nothing_else(tmp_path):
    print_section("Engine boundaries: the engine selection")
    engine = ("pac_allocator/__init__.py", "pac_allocator/planner.py", "pac_allocator/sources_extra.py", "pac_allocator/evaluation/evaluator.py", "tool_plugins/pac_allocator/plugin.py")
    elsewhere = ("pac_allocator/source/__init__.py", "pac_allocator/source/loaders.py", "pac_allocator/__pycache__/planner.cpython-313.pyc")
    for name in (*engine, *elsewhere):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("")
    selected = sorted(path.relative_to(tmp_path).as_posix() for path in _engine_files(tmp_path / "pac_allocator", tmp_path / "tool_plugins" / "pac_allocator"))
    assert selected == sorted(engine)
    print_success("source/ and bytecode caches are left out; a sources_extra sibling, nested packages and the Tool plugin are kept")


def test_the_engine_scan_reaches_the_engine_and_none_of_the_source():
    print_section("Engine boundaries: the scan reaches the engine and stops at the source")
    assert PAC_ROOT.is_dir() and TOOL_PLUGIN_ROOT.is_dir(), f"{PAC_ROOT} or {TOOL_PLUGIN_ROOT} does not exist: the repository root derived from this file is wrong"
    missing = sorted(set(KNOWN_ENGINE_MODULES) - set(ENGINE_MODULES))
    assert not missing, f"the engine scan missed known engine modules: {missing}"
    leaked = [module for module in ENGINE_MODULES if module.startswith(SOURCE_PREFIX)]
    assert not leaked, f"the engine scan includes planner source modules: {leaked}"
    assert {module: _package_of(module) for module in _EXPECTED_PACKAGES} == _EXPECTED_PACKAGES
    print_success(f"{len(ENGINE_MODULES)} engine modules scanned, {len(SOURCE_MODULES)} planner source modules left out")


@pytest.mark.parametrize("module", DATABASE_READING_SOURCE_MODULES)
def test_the_matcher_reports_the_database_in_the_real_planner_source(module):
    """Positive control on this repository's code: leaving ``source/`` out is what keeps the engine scan green."""
    assert module in SOURCE_MODULES and module not in ENGINE_MODULES, f"{module} must be scanned as planner source and left out of the engine"
    found = sorted({target for _, target in _forbidden_imports((REPO_ROOT / module).read_text(encoding="utf-8"), _package_of(module))})
    assert {"sqlalchemy", "backend.app.db.models"} <= set(found), f"{module} reads the database, yet the matcher reports only {found}"
    print_success(f"{module}: reports {found}")


def test_the_guard_goes_red_on_a_tampered_copy_of_an_engine_module():
    print_section("Engine boundaries: the guard goes red")
    module = "backend/app/services/pac_allocator/evaluation/evaluator.py"
    tampered = (REPO_ROOT / module).read_text(encoding="utf-8") + "\n\ndef _snapshot():\n    from ..source.loaders import load_holding_rows\n"
    line = len(tampered.splitlines())
    assert _offenders(module, tampered) == [f"{module}:{line} imports backend.app.services.pac_allocator.source.loaders"]
    print_success(f"{module} with one lazy relative import appended, in memory only: reported at line {line}")


# =============================================================================
# The rule
# =============================================================================


@pytest.mark.parametrize("module", ENGINE_MODULES)
def test_an_engine_module_imports_neither_the_database_nor_the_planner_source(module):
    """D-J18: the engine computes over the request it is handed; reading the database is the planner source's job."""
    offenders = _offenders(module, (REPO_ROOT / module).read_text(encoding="utf-8"))
    assert not offenders, "D-J18: a PAC/Rebalancer engine module must not import the database (sqlalchemy, sqlmodel, backend.app.db) or the planner source (pac_allocator.source):\n" + "\n".join(offenders)
    print_success(f"{module}: no database or planner source import")
