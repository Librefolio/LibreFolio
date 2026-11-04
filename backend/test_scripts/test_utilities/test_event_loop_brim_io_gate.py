"""
Gate: no synchronous BRIM file-store call runs on the event loop (L5).

``backend/app/services/brim/brim_provider.py`` is the BRIM file store. Its module-level functions read and write
``broker_reports/`` — data files, metadata sidecars, the per-broker ``flock`` under ``.locks/`` — synchronously;
the coroutines among them (asset search, duplicate detection) are the exception, and are awaited. An
``async def`` handler that calls one of the synchronous ones directly runs that I/O on uvicorn's single event
loop, and every other request waits for it. The project rule
(``LibreFolio_devWiki/wiki/problems/event-loop-blocking.md``): in an ``async def``, sync I/O goes through
``await asyncio.to_thread(fn, ...)``. The BRIM routes of ``api/v1/brokers.py`` follow it almost everywhere; this
gate makes the exceptions visible and keeps new ones out.

What it reads, with ``ast`` only — nothing is imported:

- the module's synchronous functions: its top-level ``def`` (not ``async def``), and the module-level aliases of
  one (``broker_metadata_lock = _broker_metadata_lock``);
- in every ``backend/app/api/v1/**/*.py``, the names bound to the module (``from backend.app.services.brim import
  brim_provider [as x]``, ``import backend.app.services.brim.brim_provider [as x]``, the relative forms) and the
  synchronous functions imported from it by name;
- inside every ``async def``, each call to one of them: ``<alias>.<fn>(...)``, or ``<fn>(...)`` for a function
  imported by name.

A reference is not a call: ``await asyncio.to_thread(brim_provider.fn, ...)`` hands the function to a worker
thread, which is the rule. The body of a nested ``def`` or ``lambda`` runs wherever it is called — handed to
``to_thread``, on a thread — so it is not part of the handler's own body; a nested ``async def`` is scanned on its
own. A synchronous handler (``def``) runs in FastAPI's threadpool and is never flagged.

Pure: source text and ``ast`` — no database, no server, no network, no writes. The gate asserts an absence, so
the detector first proves on in-memory sources that it sees a presence and leaves the allowed shapes alone, and the
scan must reach an API file that imports the module: an empty scan would be green about nothing.
"""

from __future__ import annotations

import ast
import functools
from dataclasses import dataclass, field
from importlib.util import resolve_name
from pathlib import Path

import pytest

from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]
# The guarded module, by path: if it moves, the gate fails loudly instead of scanning for nothing.
BRIM_PROVIDER = REPO_ROOT / "backend" / "app" / "services" / "brim" / "brim_provider.py"
BRIM_PROVIDER_MODULE = "backend.app.services.brim.brim_provider"
API_DIR = REPO_ROOT / "backend" / "app" / "api" / "v1"
# The package of the API modules, for the relative imports of the control cases.
API_PACKAGE = "backend.app.api.v1"


# =============================================================================
# Detector
# =============================================================================


def sync_functions(source: str) -> frozenset[str]:
    """Names of a module's synchronous functions: its top-level ``def``s, and the top-level aliases of one."""
    tree = ast.parse(source)
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id in names:
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return frozenset(names)


def package_of(path: Path) -> str:
    """The package a source file belongs to, as the interpreter resolves its relative imports."""
    return ".".join(path.relative_to(REPO_ROOT).with_suffix("").parts[:-1])


@dataclass(frozen=True)
class Bindings:
    """How one source file reaches the module."""

    # Dotted names that denote the module itself: "brim_provider", "store", "backend.app.services.brim.brim_provider".
    modules: frozenset[str]
    # Local name → function name, for the module's synchronous functions imported by name.
    functions: dict[str, str] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.modules or self.functions)


def bindings(tree: ast.Module, package: str, sync_names: frozenset[str], module: str = BRIM_PROVIDER_MODULE) -> Bindings:
    """Every way ``tree`` binds ``module`` or one of its synchronous functions, lazy imports included."""
    parent, _, leaf = module.rpartition(".")
    modules: set[str] = set()
    functions: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.asname or module for alias in node.names if alias.name == module)
        elif isinstance(node, ast.ImportFrom):
            try:
                source = resolve_name("." * node.level + (node.module or ""), package) if node.level else node.module
            except (ImportError, ValueError):
                continue
            for alias in node.names:
                if source == parent and alias.name == leaf:
                    modules.add(alias.asname or leaf)
                elif source == module and alias.name in sync_names:
                    functions[alias.asname or alias.name] = alias.name
    return Bindings(frozenset(modules), functions)


@dataclass(frozen=True, order=True)
class BlockingCall:
    """A call of one of the module's synchronous functions, made on the event loop."""

    path: str
    line: int
    function: str
    target: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line} {self.function} -> brim_provider.{self.target} — use await asyncio.to_thread(...)"


def _dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return None if base is None else f"{base}.{node.attr}"
    return None


def _called_function(func: ast.AST, found: Bindings, sync_names: frozenset[str]) -> str | None:
    """The module's synchronous function that a call target denotes, if it denotes one."""
    if isinstance(func, ast.Attribute) and func.attr in sync_names and _dotted(func.value) in found.modules:
        return func.attr
    if isinstance(func, ast.Name):
        return found.functions.get(func.id)
    return None


def _calls_in_own_body(handler: ast.AsyncFunctionDef, found: Bindings, sync_names: frozenset[str]) -> list[tuple[int, str]]:
    """(line, function) of each call in ``handler``'s own body — not inside a nested def, lambda or async def."""
    hits: list[tuple[int, str]] = []
    pending: list[ast.AST] = list(handler.body)
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        if isinstance(node, ast.Call):
            target = _called_function(node.func, found, sync_names)
            if target is not None:
                hits.append((node.lineno, target))
        pending.extend(ast.iter_child_nodes(node))
    return hits


def blocking_calls(source: str, path: str, package: str, sync_names: frozenset[str]) -> list[BlockingCall]:
    """Every call of the module's synchronous functions inside an ``async def`` of ``source``, in line order."""
    tree = ast.parse(source, filename=path)
    found = bindings(tree, package, sync_names)
    if not found:
        return []
    return sorted(BlockingCall(path, line, node.name, target) for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) for line, target in _calls_in_own_body(node, found, sync_names))


# =============================================================================
# The repository
# =============================================================================


@functools.cache
def _store_sync_functions() -> frozenset[str]:
    assert BRIM_PROVIDER.is_file(), f"{BRIM_PROVIDER.relative_to(REPO_ROOT)} is gone: point the gate at the BRIM file store again, never let it scan for nothing"
    return sync_functions(BRIM_PROVIDER.read_text(encoding="utf-8"))


def _api_sources() -> list[Path]:
    sources = sorted(API_DIR.rglob("*.py"))
    assert sources, f"no Python file under {API_DIR.relative_to(REPO_ROOT)}"
    return sources


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


# =============================================================================
# Control cases: the detector sees a presence, and leaves the allowed shapes alone
# =============================================================================

# A file store of the same shape as the real one: sync functions, an alias of one, a coroutine, a class.
STORE_SOURCE = """
def get_file_path(file_id):
    return None


def _broker_lock(broker_id):
    return None


broker_lock = _broker_lock


async def search_asset_candidates(query):
    return []


class BRIMProvider:
    def parse(self, path):
        return None
"""

DIRECT_CALL = """
from backend.app.services.brim import brim_provider


async def preview(file_id):
    path = brim_provider.get_file_path(file_id)
    return path
"""

ALLOWED_SHAPES = """
import asyncio

from backend.app.services.brim import brim_provider, brim_report_sets


async def preview(file_id):
    path = await asyncio.to_thread(brim_provider.get_file_path, file_id)

    def work():
        return brim_provider.get_file_path(file_id)

    other = await asyncio.to_thread(work)
    third = await asyncio.to_thread(lambda: brim_provider.get_file_path(file_id))
    found = await brim_provider.search_asset_candidates("x")
    unrelated = brim_report_sets.get_file_path(file_id)
    return path, other, third, found, unrelated


def sync_route(file_id):
    return brim_provider.get_file_path(file_id)
"""

# Every way to reach the module or a sync function of it; each source makes exactly one call on the loop.
IMPORT_FORMS = {
    "from-import as": ("from backend.app.services.brim import brim_provider as store\n\n\nasync def h(f):\n    return store.get_file_path(f)\n", "h", "get_file_path"),
    "import as": ("import backend.app.services.brim.brim_provider as store\n\n\nasync def h(f):\n    return store.get_file_path(f)\n", "h", "get_file_path"),
    "plain import": ("import backend.app.services.brim.brim_provider\n\n\nasync def h(f):\n    return backend.app.services.brim.brim_provider.get_file_path(f)\n", "h", "get_file_path"),
    "relative import": ("from ...services.brim import brim_provider\n\n\nasync def h(f):\n    return brim_provider.get_file_path(f)\n", "h", "get_file_path"),
    "function by name": ("from backend.app.services.brim.brim_provider import get_file_path as locate\n\n\nasync def h(f):\n    return locate(f)\n", "h", "get_file_path"),
    "lazy import": ("async def h(f):\n    from backend.app.services.brim import brim_provider\n\n    return brim_provider.get_file_path(f)\n", "h", "get_file_path"),
    "alias of a function": ("from backend.app.services.brim import brim_provider\n\n\nasync def h(b):\n    with brim_provider.broker_lock(b):\n        return b\n", "h", "broker_lock"),
    "nested async def": ("from backend.app.services.brim import brim_provider\n\n\ndef outer():\n    async def inner(f):\n        return brim_provider.get_file_path(f)\n\n    return inner\n", "inner", "get_file_path"),
    "async method": ("from backend.app.services.brim import brim_provider\n\n\nclass Routes:\n    async def h(self, f):\n        return brim_provider.get_file_path(f)\n", "h", "get_file_path"),
}


def test_sync_functions_are_the_top_level_defs_and_their_aliases() -> None:
    """The collector keeps the synchronous functions and their aliases; a coroutine, a class or a method is not one."""
    print_section("Event loop gate: what counts as a synchronous store function")
    assert sync_functions(STORE_SOURCE) == {"get_file_path", "_broker_lock", "broker_lock"}
    # The same reading of the real module sees the function of the two known sites, and not its coroutines.
    real = _store_sync_functions()
    assert "get_file_path" in real, sorted(real)
    assert "search_asset_candidates" not in real and "detect_tx_duplicates" not in real, sorted(real)
    print_success(f"✓ {len(real)} synchronous functions read from {_relative(BRIM_PROVIDER)}")


def test_a_direct_call_in_an_async_handler_is_flagged() -> None:
    """Positive control: the shape of the defect is seen, with its line, its handler and its target."""
    print_section("Event loop gate: a direct call is flagged")
    calls = blocking_calls(DIRECT_CALL, "api/v1/sample.py", API_PACKAGE, sync_functions(STORE_SOURCE))
    assert [(call.function, call.target) for call in calls] == [("preview", "get_file_path")], calls
    (call,) = calls
    assert "brim_provider.get_file_path(" in DIRECT_CALL.splitlines()[call.line - 1], call
    assert str(call) == f"api/v1/sample.py:{call.line} preview -> brim_provider.get_file_path — use await asyncio.to_thread(...)"
    print_success("✓ Direct call flagged")


def test_to_thread_nested_sync_code_coroutines_and_sync_handlers_are_not_flagged() -> None:
    """The allowed shapes: a reference handed to to_thread, a nested def or lambda, an awaited coroutine, another module, a sync route."""
    print_section("Event loop gate: the allowed shapes stay green")
    assert blocking_calls(ALLOWED_SHAPES, "api/v1/sample.py", API_PACKAGE, sync_functions(STORE_SOURCE)) == []
    print_success("✓ Allowed shapes not flagged")


@pytest.mark.parametrize("form", sorted(IMPORT_FORMS))
def test_every_way_of_reaching_the_module_is_followed(form: str) -> None:
    """Each import form and handler shape yields exactly its one call on the loop."""
    source, handler, target = IMPORT_FORMS[form]
    calls = blocking_calls(source, "api/v1/sample.py", API_PACKAGE, sync_functions(STORE_SOURCE))
    assert [(call.function, call.target) for call in calls] == [(handler, target)], f"{form}: {calls}"


def test_the_scan_reaches_api_files_that_import_the_store() -> None:
    """Non-vacuity: at least one API module binds the store, so the gate below is about something."""
    print_section("Event loop gate: the scan is not empty")
    sync_names = _store_sync_functions()
    importers = [_relative(path) for path in _api_sources() if bindings(ast.parse(path.read_text(encoding="utf-8")), package_of(path), sync_names)]
    assert importers, f"no module under {_relative(API_DIR)} imports {BRIM_PROVIDER_MODULE}: the gate would be green about nothing — point it at the BRIM routes again"
    print_success(f"✓ API modules binding the store: {', '.join(importers)}")


def test_no_sync_brim_file_store_call_runs_on_the_event_loop() -> None:
    """The gate: no API ``async def`` calls a synchronous function of the BRIM file store directly."""
    print_section("Event loop gate: API async handlers vs the BRIM file store")
    sync_names = _store_sync_functions()
    calls = [call for path in _api_sources() for call in blocking_calls(path.read_text(encoding="utf-8"), _relative(path), package_of(path), sync_names)]
    assert not calls, "Synchronous BRIM file-store calls inside async handlers block the event loop:\n" + "\n".join(f"  {call}" for call in calls)
    print_success("✓ No synchronous BRIM file-store call on the event loop")
