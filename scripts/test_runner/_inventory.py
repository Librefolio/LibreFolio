"""Derived inventory of what the test runner can actually run.

The runner has no notion of "a test unit": each action function reports,
prepares the environment and spawns its own process, so nothing outside the
action knows what it will launch until it launches it. That is what makes the
``all`` lists drift, the orphan check unable to prove reachability, and any
scheduling impossible.

This module derives that missing object. The action functions are near-pure
command producers, so replacing the few launch points with collectors lets us
invoke them and record *what they would run* without paying the cost of running
it. Everything else — reachability checks, ``all`` lists, scheduling — is then
a projection of the inventory rather than a hand-written list.
"""

import contextlib
import io
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Isolation classes: what a test unit may share with a concurrently running one.
#
# Only UserSettings and BrokerUserAccess carry a user_id in the data model;
# Asset, Transaction, PriceHistory, FxRate, Broker and the settings tables are
# global. Transaction has no user_id at all — it hangs off broker_id and is
# scoped at service level. So "writes only its own data" is a much narrower
# category than it first appears, and the safe default is the strictest class.
PURE = "pure"  # no DB, no server: shares anything
READ = "read"  # reads shared data, writes nothing: shares a backend
WRITE_SCOPED = "write-scoped"  # writes only its own user/broker rows
WRITE_GLOBAL = "write-global"  # writes shared surfaces: shares nothing

# Playwright project selector recorded per unit. An action that passes
# ``project=None`` runs every configured project (desktop *and* mobile), which
# is twice the work and must not be silently narrowed when units are grouped.
ALL_PROJECTS = "*"

# Backend suite directories, mapped to the runner module that registers them.
# test_*.py files at the root of test_scripts/ are shared helpers, not suites.
BACKEND_SUITE_DIRS = {
    "test_api": "_backend_api.py",
    "test_services": "_backend_services.py",
    "test_e2e": "_backend_api.py",  # e2e is in _backend_api
    "test_schemas": "_backend_schemas.py",
    "test_utilities": "_backend_utils.py",
    "test_external": "_backend_external.py",
    "test_db": "_backend_db.py",
}

# gallery.spec.ts is a docs tool (./dev.py mkdocs gallery), not a test.
EXCLUDED_SPECS = {"gallery.spec.ts"}

# Actions that do real work instead of merely composing a command: they mutate
# the filesystem or the test database directly, so the dry run must never call
# them. None of them executes a test file, so skipping them loses nothing.
SIDE_EFFECTING = {
    ("db", "create"),
    ("db", "populate"),
}

# Symbols that prove a backend test needs the shared database or the shared
# test server. Deliberately broad: a false "pure" produces flaky parallel runs,
# while a false "write-global" only costs speed.
_IMPURE_MARKERS = (
    "test_server_helper",
    "TEST_PORT",
    "BASE_URL",
    "requests.",
    "httpx",
    "get_async_engine",
    "AsyncSession",
    "create_engine",
    "sqlmodel",
    "app.db",
)


@dataclass(frozen=True)
class TestUnit:
    """One runnable unit of test: a spec file, a pytest path, a vitest file."""

    path: str
    engine: str  # "playwright" | "pytest" | "vitest"
    category: str
    action: str
    isolation: str
    #: Why this unit stays WRITE_GLOBAL on purpose. Empty means "nobody has
    #: looked yet", which is not the same claim and must not be treated as one.
    exclusive_because: str = ""

    @property
    def key(self) -> str:
        return f"{self.engine}:{self.path}"


class _FakeCompletedProcess:
    returncode = 0
    stdout = ""
    stderr = ""


@contextlib.contextmanager
def _collecting(sink):
    """Run action functions with every launch point replaced by a collector.

    ``sink`` receives ``(engine, path)`` pairs for whatever would be launched.
    """
    from . import _common, _frontend_common
    from ._registry import TEST_REGISTRY

    def fake_playwright(spec_file=None, **kwargs):
        if isinstance(spec_file, list):
            found = spec_file
        elif spec_file:
            found = [spec_file]
        else:
            found = []
        # ``project=None`` means "every configured project", i.e. desktop *and*
        # mobile. Recording it matters: consolidating those specs under a single
        # ``--project=desktop`` would drop the mobile half without failing.
        project = kwargs.get("project", "desktop") or ALL_PROJECTS
        for spec in found:
            sink("playwright", str(spec), project)
        return True

    def record_paths(parts: list) -> None:
        for raw in parts:
            token = str(raw)
            if ".test.ts" in token:
                idx = token.find("src/")
                if idx != -1:
                    sink("vitest", token[idx:], "")
            elif "test_scripts/" in token:
                # Backend suites are invoked both per file and per directory
                # (e.g. test_services/test_financial/), so keep directories:
                # they stand for everything underneath.
                tail = token.split("test_scripts/", 1)[1]
                if tail.endswith(".py") or tail.endswith("/"):
                    sink("pytest", tail, "")

    def fake_run_command(cmd, description="", **kwargs):
        record_paths(list(cmd) if isinstance(cmd, (list, tuple)) else [cmd])
        return True

    def fake_subprocess_run(cmd, *args, **kwargs):
        record_paths(list(cmd) if isinstance(cmd, (list, tuple)) else [cmd])
        return _FakeCompletedProcess()

    stub_true = lambda *a, **k: True  # noqa: E731
    patches = {
        "_run_playwright": fake_playwright,
        "_ensure_frontend_build": stub_true,
        "_ensure_db_populated": stub_true,
        "_ensure_test_users": stub_true,
        "run_command": fake_run_command,
    }

    # Modules import these symbols by value, so patching the defining module is
    # not enough: every module that already bound them must be patched too.
    targets = [_common, _frontend_common] + [
        mod
        for name, mod in sys.modules.items()
        if name.startswith("scripts.test_runner._") or name.startswith("test_runner._")
    ]

    saved: list = []
    real_sp_run = subprocess.run
    real_unlink = Path.unlink

    def guarded_unlink(self, *args, **kwargs):
        raise RuntimeError(
            f"dry-run collection tried to delete {self}. "
            "Add the owning action to SIDE_EFFECTING in _inventory.py."
        )

    try:
        Path.unlink = guarded_unlink
        for mod in targets:
            if mod is None:
                continue
            for attr, value in patches.items():
                if hasattr(mod, attr):
                    saved.append((mod, attr, getattr(mod, attr)))
                    setattr(mod, attr, value)
        subprocess.run = fake_subprocess_run

        # Neutralise the side-effecting actions in the registry (suites hold a
        # direct reference to the function object) and in their defining module
        # (some suites resolve them by name at call time).
        for cat, action in SIDE_EFFECTING:
            entry = TEST_REGISTRY.get(cat, {}).get(action)
            if entry and "func" in entry:
                name = entry["func"].__name__
                saved.append((entry, "func", entry["func"]))
                entry["func"] = stub_true
                for mod in targets:
                    if mod is not None and hasattr(mod, name):
                        saved.append((mod, name, getattr(mod, name)))
                        setattr(mod, name, stub_true)
        yield
    finally:
        subprocess.run = real_sp_run
        Path.unlink = real_unlink
        for holder, attr, value in reversed(saved):
            if isinstance(holder, dict):
                holder[attr] = value
            else:
                setattr(holder, attr, value)


def _invoke(func) -> str:
    """Call an action with output suppressed; return an error string or ''."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            func(verbose=False)
    except Exception as exc:  # collection must never mask a real failure
        return f"{type(exc).__name__}: {exc}"
    return ""


def collect_launches(only_all: bool = False) -> tuple:
    """Collect what each action would launch.

    Returns ``(launches, errors)`` where ``launches`` maps ``(category, action)``
    to a list of ``(engine, path, project)`` triples. ``project`` is only
    meaningful for Playwright: ``"desktop"``, or ``ALL_PROJECTS`` when the action
    runs every configured project.
    """
    from ._registry import TEST_REGISTRY

    launches: dict = {}
    errors: dict = {}
    current: list = []

    with _collecting(lambda engine, path, project="": current.append((engine, path, project))):
        for cat in sorted(TEST_REGISTRY):
            actions = TEST_REGISTRY[cat]
            for action in sorted(a for a in actions if not a.startswith("_")):
                if only_all and action != "all":
                    continue
                if not only_all and action == "all":
                    continue
                entry = actions[action]
                if not isinstance(entry, dict) or "func" not in entry:
                    continue
                current.clear()
                err = _invoke(entry["func"])
                if err:
                    errors[f"{cat}/{action}"] = err
                    continue
                if current:
                    launches[(cat, action)] = list(dict.fromkeys(current))

    return launches, errors


def _local_helpers(content: str) -> list:
    """Test-scripts helper modules a test file imports.

    Impurity is often transitive: a test looks clean but imports a helper that
    points at the shared database. One level of following is enough here — the
    helpers do not import each other.
    """
    found = []
    for helper in ("test_utils", "test_db_config", "test_server_helper"):
        if helper in content:
            found.append(PROJECT_ROOT / "backend" / "test_scripts" / f"{helper}.py")
    return found


def classify(engine: str, path: str, declared: str = None) -> str:
    """Assign an isolation class, defaulting to the strictest one.

    Classification is incremental by design: PURE is proven statically, and
    everything not proven is WRITE_GLOBAL. A wrong PURE causes flaky parallel
    runs; a wrong WRITE_GLOBAL only costs speed, so the asymmetry decides the
    default. READ and WRITE_SCOPED must be declared, because the textual
    heuristic tried for them was wrong often enough to be useless.
    """
    if declared:
        return declared
    if engine == "vitest":
        # Vitest runs in-process with no DB and no server, and already runs its
        # whole suite in seconds: pure by construction.
        return PURE
    if engine == "pytest":
        target = PROJECT_ROOT / "backend" / "test_scripts" / path
        files = []
        if target.is_dir():
            files = list(target.rglob("test_*.py"))
        elif target.is_file():
            files = [target]
        if not files:
            return WRITE_GLOBAL
        for f in files:
            try:
                content = f.read_text(errors="ignore")
            except OSError:
                return WRITE_GLOBAL
            if any(marker in content for marker in _IMPURE_MARKERS):
                return WRITE_GLOBAL
            for helper in _local_helpers(content):
                try:
                    helper_src = helper.read_text(errors="ignore")
                except OSError:
                    return WRITE_GLOBAL
                if any(marker in helper_src for marker in _IMPURE_MARKERS):
                    return WRITE_GLOBAL
        return PURE
    return WRITE_GLOBAL


def build_inventory() -> tuple:
    """Derive the full inventory of test units. Returns ``(units, errors)``."""
    from ._registry import TEST_REGISTRY

    launches, errors = collect_launches()
    units = []
    for (cat, action), items in sorted(launches.items()):
        entry = TEST_REGISTRY.get(cat, {}).get(action, {})
        # `exclusive_because` *is* the WRITE_GLOBAL declaration — the class and
        # its justification are one statement, not a flag with a comment beside
        # it. Written this way a category default cannot silently promote a unit
        # that somebody has already explained must not be promoted.
        if entry.get("exclusive_because"):
            declared = WRITE_GLOBAL
        else:
            declared = entry.get("isolation") or TEST_REGISTRY.get(cat, {}).get("_meta", {}).get("default_isolation")
        for engine, path, _project in items:
            units.append(
                TestUnit(
                    path=path,
                    engine=engine,
                    category=cat,
                    action=action,
                    isolation=classify(engine, path, declared),
                    exclusive_because=entry.get("exclusive_because", ""),
                )
            )
    return units, errors


def reachable_paths() -> tuple:
    """Paths reachable from the ``all`` actions, by engine. ``(reached, errors)``."""
    launches, errors = collect_launches(only_all=True)
    reached = {"playwright": set(), "pytest": set(), "vitest": set()}
    for items in launches.values():
        for engine, path, _project in items:
            if engine == "playwright":
                reached[engine].add(Path(path).name)
            else:
                reached[engine].add(path)
    return reached, errors


def on_disk() -> dict:
    """Every test file that exists, by engine, in the same shape as the units."""
    frontend = PROJECT_ROOT / "frontend"
    return {
        "playwright": sorted(
            f.name
            for f in (frontend / "e2e").rglob("*.spec.ts")
            if f.name not in EXCLUDED_SPECS
        ),
        "vitest": sorted(
            str(f.relative_to(frontend)).replace("\\", "/")
            for f in (frontend / "src").rglob("*.test.ts")
        ),
        "pytest": sorted(
            str(f.relative_to(PROJECT_ROOT / "backend" / "test_scripts")).replace("\\", "/")
            for d in BACKEND_SUITE_DIRS
            for f in (PROJECT_ROOT / "backend" / "test_scripts" / d).rglob("test_*.py")
        ),
    }


def is_covered(path: str, reached: set) -> bool:
    """A test is reached if launched directly or via a parent directory."""
    if path in reached:
        return True
    return any(entry.endswith("/") and path.startswith(entry) for entry in reached)
