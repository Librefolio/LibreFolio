"""
Guard of the financial math layer's boundaries (workstream T, lot T-1, step g).

Layer under guard: ``backend/app/services/financial_math/`` — every ``.py`` file, recursively
(``average_cost``, ``native_cash``, ``returns``, ``valuation``, ``price_marks``, ``yield_on_cost``,
``interest`` from lot U10, ``fifo/``, ``portfolio/``, ``lots/``).

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

One rule looks the other way, from the whole backend at the layer (workstream MF, lot MF-I2):

(d) «Which rows are linked to a SPLIT asset event» is asked in one place,
    ``financial_math/splits.py`` (``load_split_links``, ``split_linked_ids``). In ``backend/app``,
    ``AssetEventType.SPLIT`` is named only there and in ``services/transactions/event_suggestions.py``,
    a UI mapping of event type to transaction type that loads nothing. Every shape that reaches the
    member counts — ``AssetEventType.SPLIT``, ``models.AssetEventType.SPLIT``, an alias bound by
    ``from ... import AssetEventType as X``, ``AssetEventType("SPLIT")``, ``AssetEventType["SPLIT"]``,
    ``getattr(AssetEventType, "SPLIT")`` — and nothing else does: a comment, a docstring, another
    enum's ``SPLIT`` member, the string ``"SPLIT"`` on its own. Before MF-I2 the WAC preview
    (``portfolio_service.py``), the broker summary (``brokers/summary.py``) and the auto cost
    (``transactions/auto_cost.py``) each wrote the join again.

And one more from the whole backend at the layer (workstream J, lot CP-14a, U10, decision D-8):

(e) The day-count conventions and simple interest are defined once, in ``financial_math/interest.py``:
    ``calculate_day_count_fraction``, its three helpers ``_calculate_act_fixed`` (ACT/365, ACT/360),
    ``_calculate_act_act`` and ``_calculate_30_360``, and ``calculate_simple_interest``. Every ``def``
    and ``async def`` of ``backend/app`` counts, at any nesting: a method, a function inside a function,
    a fallback under ``except ImportError`` is a second implementation as well. A call, an import or an
    alias bound with ``=`` defines nothing. Before U10 the five lived in the Scheduled Investment provider
    (``asset_source_providers/scheduled_investment/plugin.py``), the only one that reads them.

Pure: the sources are parsed with ``ast``, never imported — no database, no server, no network.
Every rule asserts an absence, so each detector first proves it sees a presence: the import matcher
flags every forbidden shape of a synthetic source and nothing allowed, the ``__init__`` check flags
a re-export, the old-home check flags a re-created module, the SPLIT matcher flags every shape of
the member and nothing else, the definition matcher flags every shape of a definition and nothing
else, and the scans must reach the layer's known modules (an empty parametrization would be skipped,
never red) and, for (d) and (e), the backend's known modules, with every allowed home of (d) still
naming the member and the one home of (e) defining each primitive.
"""

from __future__ import annotations

import ast
import functools
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
KNOWN_MODULES = (*KNOWN_PACKAGES, "average_cost.py", "native_cash.py", "returns.py", "valuation.py", "price_marks.py", "yield_on_cost.py", "interest.py", "fifo/engine.py", "portfolio/engine.py", "lots/histories.py")

# One parametrized case per file, so a failure names the file.
LAYER_MODULES = sorted(path.relative_to(LAYER_ROOT).as_posix() for path in LAYER_ROOT.rglob("*.py"))
LAYER_PACKAGES = [module for module in LAYER_MODULES if Path(module).name == "__init__.py"]

# (d) The whole backend, and the only files of it that may name AssetEventType.SPLIT, with the reason.
APP_ROOT = REPO_ROOT / "backend" / "app"
APP_MODULES = sorted(path.relative_to(APP_ROOT).as_posix() for path in APP_ROOT.rglob("*.py"))
SPLIT_EVENT_TYPE_HOMES = {
    "services/financial_math/splits.py": "the one loader of the rows linked to a SPLIT asset event",
    "services/transactions/event_suggestions.py": "a UI mapping of event type to transaction type, not a loader",
}
# Presence barrier of (d): files the backend scan must reach — the homes, the enum's definition, and
# the three readers that wrote the join themselves before MF-I2.
KNOWN_APP_MODULES = (
    *SPLIT_EVENT_TYPE_HOMES,
    "db/models.py",
    "services/portfolio_service.py",
    "services/brokers/summary.py",
    "services/transactions/auto_cost.py",
)

# (e) The day-count conventions and simple interest, their one home, and where they lived before U10. The former home
# stays in the backend (it is the provider that reads them), so the scan must keep reaching it: a duplicate is likeliest
# there, and a scan that missed it would find no definition and prove nothing.
INTEREST_PRIMITIVES = ("calculate_day_count_fraction", "_calculate_act_fixed", "_calculate_act_act", "_calculate_30_360", "calculate_simple_interest")
INTEREST_HOME = "services/financial_math/interest.py"
INTEREST_FORMER_HOME = "services/asset_source_providers/scheduled_investment/plugin.py"


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


def _is_split_text(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value == "SPLIT"


def _is_asset_event_type(node: ast.expr, names: set[str]) -> bool:
    """``node`` is the AssetEventType enum: a bare name bound to it, or any ``<module>.AssetEventType``."""
    return (isinstance(node, ast.Name) and node.id in names) or (isinstance(node, ast.Attribute) and node.attr == "AssetEventType")


def _split_event_type_lines(source: str) -> list[int]:
    """The lines of ``source`` whose code reaches the SPLIT member of AssetEventType, each line once, in order.

    By attribute (``AssetEventType.SPLIT``, ``models.AssetEventType.SPLIT``, ``X.SPLIT`` where
    ``from ... import AssetEventType as X`` bound ``X``), by value (``AssetEventType("SPLIT")``), by
    name (``AssetEventType["SPLIT"]``, ``getattr(AssetEventType, "SPLIT")``). Comments and
    docstrings are not code, and another enum's ``SPLIT`` is another member.
    """
    tree = ast.parse(source)
    names = {"AssetEventType"} | {alias.asname for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names if alias.name == "AssetEventType" and alias.asname}
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "SPLIT" and _is_asset_event_type(node.value, names):
            lines.add(node.lineno)
        elif isinstance(node, ast.Subscript) and _is_asset_event_type(node.value, names) and _is_split_text(node.slice):
            lines.add(node.lineno)
        elif isinstance(node, ast.Call) and _is_asset_event_type(node.func, names) and node.args and _is_split_text(node.args[0]):
            lines.add(node.lineno)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr" and len(node.args) >= 2 and _is_asset_event_type(node.args[0], names) and _is_split_text(node.args[1]):
            lines.add(node.lineno)
    return sorted(lines)


@functools.cache
def _split_event_type_uses() -> dict[str, list[int]]:
    """Every module of ``backend/app`` that reaches ``AssetEventType.SPLIT`` → its lines; parsed once per session."""
    found: dict[str, list[int]] = {}
    for module in APP_MODULES:
        lines = _split_event_type_lines((APP_ROOT / module).read_text(encoding="utf-8"))
        if lines:
            found[module] = lines
    return found


def _function_definitions(source: str, names: tuple[str, ...]) -> list[tuple[int, str]]:
    """``(line, name)`` of every function ``source`` defines under one of ``names``, in line order.

    ``def`` and ``async def`` count at any nesting — module level, a method, a function inside a function, a branch of
    an ``if`` or a ``try`` — and a decorated one is reported at its ``def`` line. A call, an import, an alias bound with
    ``=``, a parameter, a docstring or a comment defines nothing, and neither does a function whose name only begins
    like one of ``names``.
    """
    return sorted((node.lineno, node.name) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name in names)


@functools.cache
def _interest_primitive_definitions() -> dict[str, list[tuple[str, int]]]:
    """Every definition of an interest primitive in ``backend/app``: name → its ``(module, line)`` places; scanned once per session.

    Only a module whose text spells one of the names is parsed: a definition always spells its own name.
    """
    found: dict[str, list[tuple[str, int]]] = {}
    for module in APP_MODULES:
        source = (APP_ROOT / module).read_text(encoding="utf-8")
        if any(name in source for name in INTEREST_PRIMITIVES):
            for line, name in _function_definitions(source, INTEREST_PRIMITIVES):
                found.setdefault(name, []).append((module, line))
    return found


# =============================================================================
# The detectors see what they look for
# =============================================================================

# Every shape (a) must reject, written from inside ``financial_math.lots``: (source, line, module it binds).
_FORBIDDEN_SHAPES = (
    ("import backend.app.services.portfolio_service", 1, "backend.app.services.portfolio_service"),
    ("import backend.app.services.brokers.broker_service as brokers", 1, "backend.app.services.brokers.broker_service"),
    ("import backend.app.services.fx.conversion, backend.app.services.transactions.transaction_service", 1, "backend.app.services.transactions.transaction_service"),
    ("from backend.app.services.lots_analysis_service import LotsAnalysisService", 1, "backend.app.services.lots_analysis_service"),
    ("from backend.app.api.v1 import portfolio", 1, "backend.app.api.v1"),
    ("from backend.app import api", 1, "backend.app.api"),
    ("from backend.app.services.ai_export.components import fx_core", 1, "backend.app.services.ai_export.components"),
    ("from backend.app.services.risk.service import RiskService", 1, "backend.app.services.risk.service"),
    ("from backend.app.services import fx, risk_plugins", 1, "backend.app.services.risk_plugins"),
    ("from backend.app.services.pac_allocator.planner import plan", 1, "backend.app.services.pac_allocator.planner"),
    ("from backend.app.services.pac_allocator.source.portfolio_allocation_source import build_snapshot", 1, "backend.app.services.pac_allocator.source.portfolio_allocation_source"),
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
    "from backend.app.services.fx.conversion import convert_bulk",
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


# Every shape (d) must flag: (source, the lines it reports).
_SPLIT_SHAPES = (
    ("AssetEventType.SPLIT", [1]),
    ("stmt = stmt.where(AssetEvent.type == AssetEventType.SPLIT)", [1]),
    ("AssetEventType.SPLIT.value", [1]),
    ("from backend.app.db import models\n\nkind = models.AssetEventType.SPLIT\n", [3]),
    ("import backend.app.db.models as m\nm.AssetEventType.SPLIT\n", [2]),
    ("from backend.app.db.models import AssetEventType as AET\n\nAET.SPLIT\n", [3]),
    ('AssetEventType("SPLIT")', [1]),
    ('AssetEventType["SPLIT"]', [1]),
    ('getattr(AssetEventType, "SPLIT")', [1]),
    ("def kinds():\n    return {AssetEventType.PRICE_ADJUSTMENT, AssetEventType.SPLIT}\n", [2]),
    ("first = AssetEventType.SPLIT\nsecond = 1\nthird = (AssetEventType.SPLIT, AssetEventType.SPLIT)\n", [1, 3]),
    ("if TYPE_CHECKING:\n    pass\nelse:\n    split = AssetEventType.SPLIT\n", [4]),
)

# What (d) must leave alone: none of it reaches the member.
_NOT_SPLIT_SHAPES = (
    '"""AssetEventType.SPLIT in a docstring."""',
    "x = 1  # AssetEventType.SPLIT in a comment",
    "CostMovementKind.SPLIT",
    "LotTimelineEventKind.SPLIT",
    "TXValidationCode.TYPE_CANNOT_SPLIT",
    "AssetEventType.PRICE_ADJUSTMENT",
    'AssetEventType("DIVIDEND")',
    'AssetEventType["DIVIDEND"]',
    'event.kind == "SPLIT"',
    'ProviderEvent(type="SPLIT")',
    'getattr(CostMovementKind, "SPLIT")',
    'class AssetEventType(StrEnum):\n    SPLIT = "SPLIT"\n',
    "from backend.app.services.financial_math.average_cost import CostMovementKind as AssetKind\n\nAssetKind.SPLIT\n",
)


def test_the_split_matcher_flags_every_shape_of_the_member_and_nothing_else():
    print_section("Layer boundaries: the AssetEventType.SPLIT matcher")
    for source, lines in _SPLIT_SHAPES:
        assert _split_event_type_lines(source) == lines, source
    for source in _NOT_SPLIT_SHAPES:
        assert _split_event_type_lines(source) == [], source
    print_success(f"{len(_SPLIT_SHAPES)} shapes of the member flagged, {len(_NOT_SPLIT_SHAPES)} others left alone")


def test_the_split_scan_reaches_the_backend_and_every_allowed_home_still_names_the_member():
    """The presence barrier of (d): the scan reads the backend, and finds the member where it is allowed.

    A home that no longer names it is a stale entry, to be removed: an allow-list that only grows
    stops guarding anything.
    """
    print_section("Layer boundaries: the AssetEventType.SPLIT scan reaches the backend")
    assert APP_ROOT.is_dir(), f"{APP_ROOT} does not exist: the repository root derived from this file is wrong"
    missing = sorted(set(KNOWN_APP_MODULES) - set(APP_MODULES))
    assert not missing, f"the scan of {APP_ROOT} missed backend modules: {missing}"
    uses = _split_event_type_uses()
    stale = sorted(home for home in SPLIT_EVENT_TYPE_HOMES if home not in uses)
    assert not stale, "these allowed homes of AssetEventType.SPLIT no longer name it — remove them from SPLIT_EVENT_TYPE_HOMES:\n" + "\n".join(f"backend/app/{home}" for home in stale)
    print_success(f"{len(APP_MODULES)} backend modules scanned; the member found in {', '.join(sorted(SPLIT_EVENT_TYPE_HOMES))}")


# Every shape (e) must count as a definition of a primitive: (source, the (line, name) pairs it reports).
_DEFINITION_SHAPES = (
    ("def calculate_simple_interest(principal, annual_rate, time_fraction):\n    return principal * annual_rate * time_fraction\n", [(1, "calculate_simple_interest")]),
    ("async def calculate_day_count_fraction(start_date, end_date, convention):\n    return 0\n", [(1, "calculate_day_count_fraction")]),
    ("import functools\n\n\n@functools.cache\ndef _calculate_act_fixed(start_date, end_date, denominator):\n    return 0\n", [(5, "_calculate_act_fixed")]),
    ("class ScheduledInvestmentProvider:\n    def _calculate_act_act(self, start_date, end_date):\n        return 0\n", [(2, "_calculate_act_act")]),
    ("def accrue(schedule):\n    def _calculate_30_360(start_date, end_date):\n        return 0\n\n    return _calculate_30_360\n", [(2, "_calculate_30_360")]),
    (
        "try:\n    from backend.app.services.financial_math.interest import calculate_simple_interest\nexcept ImportError:\n\n    def calculate_simple_interest(principal, annual_rate, time_fraction):\n        return principal * annual_rate * time_fraction\n",
        [(5, "calculate_simple_interest")],
    ),
    (
        "def calculate_day_count_fraction(start_date, end_date, convention):\n    return 0\n\n\ndef calculate_simple_interest(principal, annual_rate, time_fraction):\n    return 0\n\n\ndef calculate_day_count_fraction(start_date, end_date, convention):\n    return 1\n",
        [(1, "calculate_day_count_fraction"), (5, "calculate_simple_interest"), (9, "calculate_day_count_fraction")],
    ),
)

# What (e) must leave alone: none of it defines a primitive.
_NOT_DEFINITION_SHAPES = (
    "from backend.app.services.financial_math.interest import calculate_day_count_fraction, calculate_simple_interest",
    "from backend.app.services.financial_math import interest\n\nvalue = interest.calculate_simple_interest(principal, rate, fraction)\n",
    "fraction = calculate_day_count_fraction(start_date, end_date, convention)",
    "calculate_simple_interest = interest.calculate_simple_interest",
    "def accrue(calculate_simple_interest):\n    return calculate_simple_interest(1, 2, 3)\n",
    '"""def _calculate_act_act(start_date, end_date) in a docstring."""',
    "x = 1  # def _calculate_30_360(start_date, end_date) in a comment",
    "def calculate_simple_interest_rate(principal, annual_rate):\n    return principal * annual_rate\n",
    "def _calculate_act_act_fraction(start_date, end_date):\n    return 0\n",
    "def calculate_daily_interest(principal, annual_rate):\n    return principal * annual_rate / 365\n",
)


def test_the_definition_matcher_flags_every_shape_of_a_definition_and_nothing_else():
    print_section("Layer boundaries: the definition matcher of the interest primitives")
    for source, found in _DEFINITION_SHAPES:
        assert _function_definitions(source, INTEREST_PRIMITIVES) == found, source
    for source in _NOT_DEFINITION_SHAPES:
        assert _function_definitions(source, INTEREST_PRIMITIVES) == [], source
    print_success(f"{len(_DEFINITION_SHAPES)} shapes of a definition flagged, {len(_NOT_DEFINITION_SHAPES)} others left alone")


def test_the_interest_scan_reaches_the_former_home_of_the_primitives():
    """The presence barrier of (e): the backend scan reads the provider where the primitives lived before U10.

    A duplicate is likeliest there; a scan that missed the file would find no definition in it and prove nothing.
    """
    print_section("Layer boundaries: the interest primitive scan reaches the provider")
    assert INTEREST_FORMER_HOME in APP_MODULES, f"the scan of {APP_ROOT} missed backend/app/{INTEREST_FORMER_HOME}: if the provider moved, point INTEREST_FORMER_HOME at its new file"
    print_success(f"backend/app/{INTEREST_FORMER_HOME} is scanned")


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


def test_only_the_split_loader_names_the_split_event_type():
    """(d) The rows linked to a SPLIT asset event are read through ``financial_math.splits``, never by a join of one's own.

    Before MF-I2: red, naming ``services/portfolio_service.py``, ``services/brokers/summary.py`` and
    ``services/transactions/auto_cost.py``.
    """
    offenders = [f"backend/app/{module}:{line}" for module, lines in sorted(_split_event_type_uses().items()) if module not in SPLIT_EVENT_TYPE_HOMES for line in lines]
    assert not offenders, "AssetEventType.SPLIT is named outside the split loader: read the rows linked to a SPLIT event with financial_math.splits.split_linked_ids (or load_split_links when the ratio, the event or the dates matter):\n" + "\n".join(offenders)
    print_success(f"AssetEventType.SPLIT named only in {', '.join(sorted(SPLIT_EVENT_TYPE_HOMES))}")


def test_the_interest_primitives_are_defined_once_in_their_home():
    """(e) The day-count conventions and simple interest are defined once, in ``financial_math/interest.py`` (U10, D-8).

    Before U10: red — ``services/financial_math/interest.py`` does not exist, and each of the five primitives is defined
    in ``services/asset_source_providers/scheduled_investment/plugin.py`` instead (lines 74, 108, 114, 154 and 174).
    """
    definitions = _interest_primitive_definitions()
    problems = [] if INTEREST_HOME in APP_MODULES else [f"backend/app/{INTEREST_HOME} does not exist"]
    for name in INTEREST_PRIMITIVES:
        places = definitions.get(name, [])
        at_home = [line for module, line in places if module == INTEREST_HOME]
        if len(at_home) != 1:
            problems.append(f"{name}: defined {len(at_home)} times in backend/app/{INTEREST_HOME}, expected once" + (f" (lines {', '.join(str(line) for line in at_home)})" if at_home else ""))
        problems.extend(f"{name}: also defined at backend/app/{module}:{line}" for module, line in places if module != INTEREST_HOME)
    assert not problems, f"the day-count conventions and simple interest have one home, backend/app/{INTEREST_HOME} (lot U10, decision D-8): define each primitive there, once, and import it from there everywhere else:\n" + "\n".join(problems)
    print_success(f"{', '.join(INTEREST_PRIMITIVES)}: each defined once, in backend/app/{INTEREST_HOME}")
