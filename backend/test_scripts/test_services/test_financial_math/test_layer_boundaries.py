"""
Guard of the financial math layer's boundaries (workstream T, lot T-1, step g).

Layer under guard: ``backend/app/services/financial_math/`` — every ``.py`` file, recursively
(``average_cost``, ``native_cash``, ``returns``, ``valuation``, ``price_marks``, ``yield_on_cost``,
``fifo/``, ``portfolio/``, ``lots/``).

What the layer owes the rest of the backend, in one line: engines, services and API handlers call
the layer and the layer depends on none of them; it re-exports nothing, and the homes its
calculations left are not coming back. Three rules, approved by the developer:

(a) No module of the layer imports an orchestration service (``portfolio_service``,
    ``broker_service``, ``transaction_service``, ``lots_analysis_service``), the API, AI Export,
    risk, PAC or signals. Every ``import`` and ``from ... import`` node counts, wherever it sits: a
    function-level lazy import, or one under ``if TYPE_CHECKING:``, binds the same dependency. The
    infrastructure a calculation needs stays allowed (``fx``, ``settings_service``,
    ``data_quality_thresholds``, ``utils``, ``db``, ``schemas``), and so do the layer's own modules.
(b) No re-exports: every ``__init__.py`` of the layer is its module docstring and nothing else, so
    a name is imported from the module that defines it and a test patches the object the code
    actually reads.
(c) The old homes (``portfolio_engine.py``, ``fifo_lot_engine.py``, ``price_resolver.py`` and
    ``yield_on_cost.py`` under ``services/``, and ``utils/financial/``) stay gone, so merging a
    branch that still has them cannot bring a second implementation back. A ``__pycache__`` that
    git leaves behind after deleting a module does not count: a merge cannot bring it back.

Pure: the sources are parsed with ``ast``, never imported — no database, no server, no network.
Every rule asserts an absence, so each detector first proves it sees a presence: the import matcher
flags every forbidden shape of a synthetic source and nothing allowed, the ``__init__`` check flags
a re-export, the old-home check flags a re-created module, and the scans must reach the layer's
known modules (an empty parametrization would be skipped, never red).
"""

from __future__ import annotations

import ast
from importlib.util import resolve_name
from pathlib import Path

import pytest

from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[4]
LAYER_ROOT = REPO_ROOT / "backend" / "app" / "services" / "financial_math"
LAYER_PACKAGE = "backend.app.services.financial_math"

# (a) What the layer never imports, as plain string prefixes of the fully-qualified module:
# "...services.risk" also covers "risk_plugins", and "...services.signal" covers "signal_plugins",
# "signal_runtime", "signal_service" and every other "signal_*" module.
FORBIDDEN_PREFIXES = (
    "backend.app.services.portfolio_service",
    "backend.app.services.brokers",
    "backend.app.services.transactions",
    "backend.app.services.lots_analysis_service",
    "backend.app.api",
    "backend.app.services.ai_export",
    "backend.app.services.risk",
    "backend.app.services.pac_allocator",
    "backend.app.services.portfolio_allocation_source",
    "backend.app.services.signal",
)

# (c) Where the layer's calculations lived before they moved into it.
OLD_HOMES = (
    "backend/app/services/portfolio_engine.py",
    "backend/app/services/fifo_lot_engine.py",
    "backend/app/services/price_resolver.py",
    "backend/app/services/yield_on_cost.py",
    "backend/app/utils/financial",
)

# Presence barrier: files the scans must reach, relative to the layer root.
KNOWN_PACKAGES = ("__init__.py", "fifo/__init__.py", "portfolio/__init__.py", "lots/__init__.py")
KNOWN_MODULES = (*KNOWN_PACKAGES, "average_cost.py", "native_cash.py", "returns.py", "valuation.py", "price_marks.py", "yield_on_cost.py", "fifo/engine.py", "portfolio/engine.py", "lots/histories.py")

# One parametrized case per file, so a failure names the file.
LAYER_MODULES = sorted(path.relative_to(LAYER_ROOT).as_posix() for path in LAYER_ROOT.rglob("*.py"))
LAYER_PACKAGES = [module for module in LAYER_MODULES if Path(module).name == "__init__.py"]


# =============================================================================
# Detectors
# =============================================================================


def _package_of(module: str) -> str:
    """The package a layer module's relative imports resolve against: its directory (an ``__init__`` is its own package)."""
    return ".".join((LAYER_PACKAGE, *Path(module).parts[:-1]))


def _is_forbidden(target: str) -> bool:
    return target.startswith(FORBIDDEN_PREFIXES)


def _forbidden_imports(source: str, package: str) -> list[tuple[int, str]]:
    """``(line, module)`` for every import in ``source`` that binds a forbidden module.

    ``import a.b`` binds ``a.b``; ``from a import b`` binds ``a`` and may bind the submodule ``a.b``
    — ``from backend.app.services import risk`` is exactly that shape. Relative forms resolve against
    ``package``, as the interpreter does. ``ast.walk`` visits every node, so an import inside a
    function or under ``if TYPE_CHECKING:`` counts like a top-level one.
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


def _has_docstring(tree: ast.Module) -> bool:
    first = tree.body[0] if tree.body else None
    return isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)


def _statements_besides_the_docstring(tree: ast.Module) -> list[ast.stmt]:
    return tree.body[1:] if _has_docstring(tree) else list(tree.body)


def _files_at(path: Path) -> list[Path]:
    """What an old home still holds: itself if it is a file; inside a directory, every file outside a bytecode cache.

    Deleting a module that had been imported leaves its ``__pycache__`` behind: git ignores it, so a
    checkout never removes it and a merge can never bring it back, and Python does not import a
    module from a cached file whose source is gone. It does not count; any other file does.
    """
    if path.is_dir():
        return sorted(file for file in path.rglob("*") if file.is_file() and "__pycache__" not in file.relative_to(path).parts)
    return [path] if path.exists() else []


# =============================================================================
# The detectors see what they look for
# =============================================================================

# Every shape (a) must reject, written from inside ``financial_math.lots``: (source, line, module it binds).
_FORBIDDEN_SHAPES = (
    ("import backend.app.services.portfolio_service", 1, "backend.app.services.portfolio_service"),
    ("import backend.app.services.brokers.broker_service as brokers", 1, "backend.app.services.brokers.broker_service"),
    ("import backend.app.services.fx, backend.app.services.transactions.transaction_service", 1, "backend.app.services.transactions.transaction_service"),
    ("from backend.app.services.lots_analysis_service import LotsAnalysisService", 1, "backend.app.services.lots_analysis_service"),
    ("from backend.app.api.v1 import portfolio", 1, "backend.app.api.v1"),
    ("from backend.app import api", 1, "backend.app.api"),
    ("from backend.app.services.ai_export.components import fx_core", 1, "backend.app.services.ai_export.components"),
    ("from backend.app.services.risk.service import RiskService", 1, "backend.app.services.risk.service"),
    ("from backend.app.services import fx, risk_plugins", 1, "backend.app.services.risk_plugins"),
    ("from backend.app.services.pac_allocator.planner import plan", 1, "backend.app.services.pac_allocator.planner"),
    ("from backend.app.services.portfolio_allocation_source import build_snapshot", 1, "backend.app.services.portfolio_allocation_source"),
    ("from backend.app.services.signal_service import SignalService", 1, "backend.app.services.signal_service"),
    ("from backend.app.services.signal_plugins import base", 1, "backend.app.services.signal_plugins"),
    ("import backend.app.services.signal_runtime", 1, "backend.app.services.signal_runtime"),
    ("from ...portfolio_service import PortfolioService", 1, "backend.app.services.portfolio_service"),
    ("from ... import risk", 1, "backend.app.services.risk"),
    ("def load():\n    from backend.app.services.portfolio_service import PortfolioService\n", 2, "backend.app.services.portfolio_service"),
    ("from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from backend.app.services.brokers.broker_service import BrokerService\n", 4, "backend.app.services.brokers.broker_service"),
)

# What the layer may import, from the same package: none of it may be flagged.
_ALLOWED_SHAPES = (
    "from backend.app.services.fx import convert_bulk",
    "from backend.app.services import fx",
    "from backend.app.services.accounts.settings_service import get_effective_base_currency",
    "from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD",
    "import backend.app.utils.runtime.cache",
    "from backend.app.db.models import Transaction",
    "from backend.app.schemas.portfolio import LotAnalysisType",
    "from backend.app.services.financial_math.fifo.models import FifoLot",
    "from backend.app.services.financial_math import portfolio",
    "from .prices import PriceHistoryLookup",
    "from .. import average_cost",
    "import signal",  # the standard library's, not backend.app.services.signal*
)

# ``__init__.py`` sources and the statements (b) must report in each: (source, their types).
_INIT_SHAPES = (
    ('"""Doc."""\n', []),
    ('"""Doc."""\nfrom .models import FifoLot\n', [ast.ImportFrom]),
    ('"""Doc."""\nimport backend.app.services.financial_math.fifo.engine as engine\n', [ast.Import]),
    ('"""Doc."""\n__all__ = ["run_fifo_lot_engine"]\n', [ast.Assign]),
    ('"""Doc."""\n__all__: list[str] = []\n', [ast.AnnAssign]),
    ('"""Doc."""\n"""A second string is a statement, not the docstring."""\n', [ast.Expr]),
    ("from .models import FifoLot\n", [ast.ImportFrom]),
)


def test_the_import_matcher_flags_every_forbidden_shape_and_nothing_allowed():
    print_section("Layer boundaries: the import matcher")
    package = f"{LAYER_PACKAGE}.lots"
    for source, line, module in _FORBIDDEN_SHAPES:
        assert _forbidden_imports(source, package) == [(line, module)], source
    assert _forbidden_imports("\n".join(_ALLOWED_SHAPES), package) == []
    print_success(f"{len(_FORBIDDEN_SHAPES)} forbidden shapes flagged, {len(_ALLOWED_SHAPES)} allowed ones left alone")


def test_the_init_check_reports_anything_besides_the_docstring():
    print_section("Layer boundaries: the __init__ check")
    assert _has_docstring(ast.parse('"""Doc."""\n'))
    assert not _has_docstring(ast.parse(""))
    assert not _has_docstring(ast.parse("from .models import FifoLot\n"))
    for source, kinds in _INIT_SHAPES:
        assert [type(statement) for statement in _statements_besides_the_docstring(ast.parse(source))] == kinds, source
    print_success("an import, an assignment, __all__ and a second string are all reported")


def test_the_old_home_check_ignores_only_bytecode_caches(tmp_path):
    print_section("Layer boundaries: the old-home check")
    folder = tmp_path / "financial"
    module = tmp_path / "portfolio_engine.py"
    assert _files_at(folder) == []
    assert _files_at(module) == []

    (folder / "__pycache__").mkdir(parents=True)
    (folder / "__pycache__" / "returns.cpython-313.pyc").write_bytes(b"")
    assert _files_at(folder) == [], "a stale bytecode cache is what git leaves behind, not a module"

    (folder / "returns.py").write_text("")
    module.write_text("")
    assert _files_at(folder) == [folder / "returns.py"]
    assert _files_at(module) == [module]
    print_success("a re-created module is reported, a stale __pycache__ is not")


def test_the_scans_reach_the_whole_layer():
    print_section("Layer boundaries: the scans reach the layer")
    assert LAYER_ROOT.is_dir(), f"{LAYER_ROOT} does not exist: the repository root derived from this file is wrong"
    missing = sorted(set(KNOWN_MODULES) - set(LAYER_MODULES))
    assert not missing, f"the scan of {LAYER_ROOT} missed layer modules: {missing}"
    assert set(KNOWN_PACKAGES) <= set(LAYER_PACKAGES)
    assert (_package_of("__init__.py"), _package_of("fifo/__init__.py"), _package_of("lots/conversions.py")) == (LAYER_PACKAGE, f"{LAYER_PACKAGE}.fifo", f"{LAYER_PACKAGE}.lots")
    print_success(f"{len(LAYER_MODULES)} modules scanned, {len(LAYER_PACKAGES)} of them package __init__ files")


# =============================================================================
# The rules
# =============================================================================


@pytest.mark.parametrize("module", LAYER_MODULES)
def test_a_layer_module_imports_no_orchestration_service_api_or_feature(module):
    """(a) Services, the API, AI Export, risk, PAC and signals call the layer; it never imports them."""
    found = _forbidden_imports((LAYER_ROOT / module).read_text(encoding="utf-8"), _package_of(module))
    offenders = [f"financial_math/{module}:{line} imports {target}" for line, target in found]
    assert not offenders, "the financial math layer must not import orchestration services, the API, AI Export, risk, PAC or signals:\n" + "\n".join(offenders)
    print_success(f"financial_math/{module}: no forbidden import")


@pytest.mark.parametrize("package_init", LAYER_PACKAGES)
def test_a_package_init_is_only_its_docstring(package_init):
    """(b) A package of the layer re-exports nothing: a name is imported from the module that defines it."""
    source = (LAYER_ROOT / package_init).read_text(encoding="utf-8")
    tree = ast.parse(source)
    extra = [f"financial_math/{package_init}:{statement.lineno} {ast.get_source_segment(source, statement)}" for statement in _statements_besides_the_docstring(tree)]
    assert not extra, "a package __init__ of the financial math layer holds its docstring and nothing else (no imports, assignments or __all__):\n" + "\n".join(extra)
    assert _has_docstring(tree), f"financial_math/{package_init} has no module docstring: a package __init__ of the layer is exactly its docstring"
    print_success(f"financial_math/{package_init}: docstring only")


@pytest.mark.parametrize("old_home", OLD_HOMES)
def test_an_old_home_of_the_layer_stays_gone(old_home):
    """(c) A merge from a branch older than the move must not bring back a second implementation."""
    path = REPO_ROOT / old_home
    assert path.parent.is_dir(), f"{path.parent} does not exist: the repository root is wrong, so the absence of {old_home} proves nothing"
    leftovers = [file.relative_to(REPO_ROOT).as_posix() for file in _files_at(path)]
    assert not leftovers, f"{old_home} was a home of the calculations now in financial_math and must stay gone:\n" + "\n".join(leftovers)
    print_success(f"{old_home}: gone")
