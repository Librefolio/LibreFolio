"""
Backend consolidation: one pytest invocation per category instead of one per unit.

## Why

Every backend unit is its own `pipenv run python -m pytest <file>`. Measured, the
fixed cost of that invocation — pipenv resolution, interpreter start, importing
the whole FastAPI app, SQLModel and every provider — is **2.6 s**, while
collecting all 47 `test_api` files at once costs **3.7 s** in total. So `api all`
spends roughly two minutes of its seven doing nothing but starting Python 47
times, and `services`, with 85 units, pays more still.

Measured end to end on `test_api`: 47 invocations took 458 s, one invocation ran
the same 564 tests in 367 s. Twenty per cent of the category, recovered without
touching a single test.

## What this does

`./dev.py test api all` runs every registered pytest unit of the category in
**one** invocation. `./dev.py test api auth` is untouched — a single action still
means a single file, exactly as before.

## Why per-unit outcomes come with it, not after it

Consolidation alone would report "the category passed" instead of naming the file
that failed, and would coarsen `--resume` from a unit to a whole category. So the
junit report is read back and folded into a per-file verdict, exactly as the
frontend pass does with Playwright's and vitest's JSON reports. The per-action
summary the runner prints stays as detailed as it was.

## What is deliberately not consolidated

- **`db`** is a lifecycle, not a batch: its actions create the schema, validate
  it and populate it, in that order, and some of them *are* the side effect. It
  keeps its 1:1 shape.
- **`external`** filters its units by provider (`--providers`, `--exclude-providers`).
  One invocation would silently ignore that filter.
- **Units already claimed by the parallel pre-pass**, which runs first: they have
  been executed, and re-running them here would double both the time and the
  coverage.

## The precondition

One invocation means one pytest session, so the session-scoped fixtures in
`conftest.py` — notably the settings seeding — run once instead of once per unit.
That is only safe when no unit destroys shared state that a later one needs. It
was verified rather than assumed: all 47 serial `test_api` units in a single
session gave 564 passed, 3 skipped, 0 failed.
"""

import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from . import _common
from ._common import Colors, print_error, print_info, print_success, print_warning
from ._inventory import PROJECT_ROOT

#: Order matters and is the suite's, not the alphabet's: `services` recreates the
#: database empty and `api` reseeds it, so consolidating them out of order would
#: hand `api` an empty database.
CONSOLIDATABLE = ("services", "utils", "schemas", "api", "e2e")


def group_backend_units(scope: str | None, skip: set | None = None) -> list:
    """Collect, per consolidatable category, the pytest units to run together.

    ``scope`` is a single category name, or ``None`` for every consolidatable
    category. ``skip`` is the set of ``(category, action)`` pairs an earlier
    pre-pass already ran. Returns ``[(category, {path: [actions]})]`` in suite
    order.

    A path can belong to several actions — an alias re-launching the same file —
    so every claimant is recorded, and each gets a verdict from the one run.
    """
    from ._inventory import collect_launches

    skip = skip or set()
    launches, errors = collect_launches()
    if errors:
        return []

    by_category: dict = {}
    for (category, action), units in launches.items():
        if category not in CONSOLIDATABLE:
            continue
        if scope is not None and category != scope:
            continue
        if (category, action) in skip:
            continue
        for kind, path, _project in units:
            if kind != "pytest":
                continue
            by_category.setdefault(category, {}).setdefault(path, []).append(action)

    return [(c, by_category[c]) for c in CONSOLIDATABLE if c in by_category]


def _junit_results(report: Path, known: list) -> dict:
    """Read a pytest junit report into ``{unit path: passed}``.

    pytest leaves ``file`` empty but fills ``classname`` with the dotted module,
    so walking back from the class to the module maps a test case onto the unit
    that owns it. A unit passes only when every one of its cases did; a unit that
    produced no case at all is *not* silently green — a file that collects
    nothing is a defect, not a pass.
    """
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError):
        return {}

    # Units can be directories, which own every module underneath them.
    dirs = [k for k in known if k.endswith("/")]
    outcome: dict = {}
    for case in root.iter("testcase"):
        parts = (case.get("classname") or "").split(".")
        if parts[:2] == ["backend", "test_scripts"]:
            parts = parts[2:]
        module = None
        walk = list(parts)
        while walk:
            candidate = "/".join(walk) + ".py"
            if candidate in known:
                module = candidate
                break
            walk = walk[:-1]
        if module is None:
            dotted = "/".join(parts)
            module = next((d for d in dirs if dotted.startswith(d.rstrip("/"))), None)
        if module is None:
            continue
        # error/failure children mark a red; skipped is not one.
        red = case.find("failure") is not None or case.find("error") is not None
        outcome[module] = outcome.get(module, True) and not red
    return outcome


def _pytest_cmd(paths: list, coverage: bool, junit: Path, verbose: bool) -> list:
    from scripts.cli_base import pipenv_prefix

    cmd = [*pipenv_prefix(), "python", "-m", "pytest"]
    if verbose:
        cmd.append("-s")
    cmd += [*paths, "-v", "--no-header", f"--junit-xml={junit}"]
    if coverage:
        html_dir = "htmlcov-backend" if _common._COVERAGE_SOURCE != "frontend" else "htmlcov-backend-e2e"
        cmd += [
            "--cov=backend/app",
            "--cov-append",
            f"--cov-report=html:{html_dir}",
            "--cov-report=term-missing:skip-covered",
        ]
    return cmd


def _run_group(category: str, paths: list, coverage: bool, verbose: bool) -> dict:
    """Run one category's units in a single invocation; return per-path verdicts.

    Output is streamed, not captured. The parallel pre-pass has to capture,
    because several workers cannot share one terminal — here there is exactly one
    process, so the live pytest progress the suite has always shown is kept.
    """
    import os
    import shutil

    from backend.test_scripts.test_db_config import TEST_DATABASE_URL

    report = Path(tempfile.mkdtemp(prefix="lf_junit_")) / "report.xml"
    full = [f"backend/test_scripts/{p}" for p in paths]
    cmd = _pytest_cmd(full, coverage, report, verbose)

    print(f"\n{Colors.BLUE}Running: {category} — {len(paths)} unit(s) in one invocation{Colors.NC}")
    # The paths themselves are the noisy part and the unit list is already
    # printed above by the plan; show the flags, which are what actually differ.
    flags = [c for c in cmd if not c.startswith("backend/test_scripts/")]
    print(f"Command:\n└─▶ $ {' '.join(flags)}  ({len(full)} paths)")

    env = os.environ.copy()
    env["LIBREFOLIO_TEST_MODE"] = "1"
    env["DATABASE_URL"] = TEST_DATABASE_URL

    # Same copy-in/copy-out of the accumulated database that run_command does:
    # pytest-cov appends to ./.coverage, and the per-source accumulation lives
    # in .coverage_data/<source>.
    data_dir = PROJECT_ROOT / ".coverage_data"
    source = _common._COVERAGE_SOURCE or "backend"
    accumulated = data_dir / source
    main_cov = PROJECT_ROOT / ".coverage"
    if coverage:
        env["COVERAGE_RUN"] = "1"
        data_dir.mkdir(exist_ok=True)
        if accumulated.exists():
            shutil.copy2(str(accumulated), str(main_cov))

    log_path = None
    log_dir = _common.get_log_dir()
    if log_dir:
        from ._archive import log_file_for

        log_path = log_file_for(log_dir, category, "consolidated")

    try:
        if log_path is not None:
            with open(log_path, "w", encoding="utf-8") as fh:
                proc = subprocess.Popen(cmd, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
                for line in proc.stdout:
                    print(line, end="")
                    fh.write(line)
                proc.wait()
        else:
            proc = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)
    except Exception as exc:
        print_error(f"{category} consolidated run error: {exc}")
        return dict.fromkeys(paths, False)
    finally:
        # The copy *out* is as load-bearing as the copy in, and its absence would
        # not fail: pytest-cov would write .coverage, the next reader would find
        # only the stale .coverage_data/<source>, and the whole category's
        # measurement would vanish without a single red. Mirrors run_command().
        if coverage and main_cov.exists():
            shutil.copy2(str(main_cov), str(accumulated))

    verdicts = _junit_results(report, paths)
    missing = [p for p in paths if p not in verdicts]
    if missing:
        print_warning(f"{category}: {len(missing)} unit(s) produced no test case — treated as failures")
    return {p: verdicts.get(p, False) for p in paths}


def run_backend_consolidated(scope: str | None, coverage: bool, resume: bool = False, verbose: bool = False, skip: set | None = None) -> tuple:
    """Run every consolidatable backend unit in scope, one invocation per category.

    Returns ``(ok, covered_actions, per_action_outcome)``.
    """
    from ._run_cache import is_passed, mark_failed, mark_passed

    groups = group_backend_units(scope, skip=skip)
    if not groups:
        return True, set(), {}

    covered: set = set()
    outcome: dict = {}
    skipped: set = set()
    ok = True

    def claim(category: str, actions: list, passed: bool) -> None:
        nonlocal ok
        for action in actions:
            key = (category, action)
            covered.add(key)
            outcome[key] = outcome.get(key, True) and passed
            ok = ok and passed

    def cache_key(category: str) -> str:
        return f"consolidated:{category}"

    for category, paths_by_unit in groups:
        todo = sorted(p for p, actions in paths_by_unit.items() if not (resume and all(is_passed(cache_key(category), a) for a in actions)))
        for path, actions in paths_by_unit.items():
            if path not in todo:
                skipped.add(path)
                claim(category, actions, True)
        if not todo:
            continue

        # The category's own precondition, declared once in its registry _meta.
        # A failed setup is fatal for the category: `services` failing to recreate
        # the database produced 116 `no such table` errors that named every test
        # except the one thing that had actually gone wrong. Better to say so once.
        if not _common.run_category_setup(category):
            print_error(f"{category}: setup failed — its units are not run, they would only report the consequence")
            for path, actions in paths_by_unit.items():
                claim(category, actions, False)
            continue

        verdict = _run_group(category, todo, coverage, verbose)
        for path, passed in verdict.items():
            claim(category, paths_by_unit[path], passed)

    if skipped:
        print_info(f"🔄 Resuming: {len(skipped)} unit(s) already passed, not re-run")

    for (category, action), passed in sorted(outcome.items()):
        if passed:
            print_success(f"  ✓ {category} {action}")
            mark_passed(f"consolidated:{category}", action)
        else:
            print_error(f"  ✘ {category} {action}")
            mark_failed(f"consolidated:{category}", action)

    if not ok:
        print_warning("Consolidated backend pass has failures — the serial pass will not repeat these units")
    return ok, covered, outcome
