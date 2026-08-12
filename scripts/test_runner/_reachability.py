"""Dry-run collection of what the ``all`` actions would actually launch.

Registration and reachability are two adjacent guarantees, and test files can
fall in the gap between them: a spec can be named in a runner module (so it
looks registered) while no ``all`` action ever reaches it, meaning it silently
stops running.

This module answers the second question. The action functions are near-pure
command producers, so replacing the few launch points with collectors lets us
invoke every ``all`` action and record *what it would run* without paying the
cost of running it.
"""

import contextlib
import io
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Actions that do real work instead of merely composing a command: they mutate
# the filesystem or the test database directly, so the dry run must never call
# them. None of them executes a test file, so skipping them loses no coverage
# of the reachability question.
_SIDE_EFFECTING = {
    ("db", "create"),
    ("db", "populate"),
}


class _FakeCompletedProcess:
    returncode = 0
    stdout = ""
    stderr = ""


def collect_reachable(categories: list = None) -> dict:
    """Invoke every ``all`` action with the launch points stubbed out.

    Returns a dict with the sets of test units each ``all`` action reaches:
    ``specs`` (Playwright spec filenames), ``unit_tests`` (Vitest ``src/...``
    paths) and ``pytest_paths`` (``test_scripts/...`` paths), plus ``errors``
    keyed by category for actions that could not be collected.
    """
    from . import _common, _frontend_common
    from ._registry import TEST_REGISTRY

    specs: set = set()
    unit_tests: set = set()
    pytest_paths: set = set()
    errors: dict = {}

    def fake_playwright(spec_file=None, **kwargs):
        if isinstance(spec_file, list):
            found = spec_file
        elif spec_file:
            found = [spec_file]
        else:
            found = []
        for s in found:
            specs.add(Path(str(s)).name)
        return True

    def _record_paths(parts: list) -> None:
        for raw in parts:
            token = str(raw)
            if ".test.ts" in token:
                idx = token.find("src/")
                if idx != -1:
                    unit_tests.add(token[idx:])
            elif "test_scripts/" in token:
                # Backend suites are invoked both per-file and per-directory
                # (e.g. test_services/test_financial/), so keep directories too:
                # they stand for everything underneath.
                tail = token.split("test_scripts/", 1)[1]
                if tail.endswith(".py") or tail.endswith("/"):
                    pytest_paths.add(tail)

    def fake_run_command(cmd, description="", **kwargs):
        _record_paths(list(cmd) if isinstance(cmd, (list, tuple)) else [cmd])
        return True

    def fake_subprocess_run(cmd, *args, **kwargs):
        _record_paths(list(cmd) if isinstance(cmd, (list, tuple)) else [cmd])
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
    saved: list = []
    targets = [_common, _frontend_common] + [
        mod
        for name, mod in sys.modules.items()
        if name.startswith("scripts.test_runner._") or name.startswith("test_runner._")
    ]
    real_sp_run = subprocess.run
    real_unlink = Path.unlink

    def guarded_unlink(self, *args, **kwargs):
        raise RuntimeError(
            f"dry-run collection tried to delete {self}. "
            "Add the owning action to _SIDE_EFFECTING in _reachability.py."
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
            if getattr(mod, "subprocess", None) is subprocess:
                saved.append((mod, "subprocess", subprocess))
        subprocess.run = fake_subprocess_run

        # Neutralise the side-effecting actions in the registry (the ``all``
        # suites hold direct references to the function objects) and in their
        # defining module (some suites resolve them by name at call time).
        for cat, action in _SIDE_EFFECTING:
            entry = TEST_REGISTRY.get(cat, {}).get(action)
            if entry and "func" in entry:
                name = entry["func"].__name__
                saved.append((entry, "func", entry["func"]))
                entry["func"] = stub_true
                for mod in targets:
                    if mod is not None and hasattr(mod, name):
                        saved.append((mod, name, getattr(mod, name)))
                        setattr(mod, name, stub_true)

        wanted = categories or sorted(TEST_REGISTRY)
        for cat in wanted:
            entry = TEST_REGISTRY.get(cat, {})
            if "all" not in entry:
                continue
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    entry["all"]["func"](verbose=False)
            except Exception as exc:  # collection must never mask a real failure
                errors[cat] = f"{type(exc).__name__}: {exc}"
    finally:
        subprocess.run = real_sp_run
        Path.unlink = real_unlink
        for holder, attr, value in reversed(saved):
            if isinstance(holder, dict):
                holder[attr] = value
            else:
                setattr(holder, attr, value)

    return {
        "specs": specs,
        "unit_tests": unit_tests,
        "pytest_paths": pytest_paths,
        "errors": errors,
    }
