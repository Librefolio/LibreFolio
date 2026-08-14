"""
Frontend consolidation: one invocation per category instead of one per action.

## Why

A frontend action pays, before it tries anything: a database populate, eight user
creations, a Playwright `globalSetup` that populates and creates users *again*, and
a webServer start/stop. Roughly eleven cold Python starts per spec file. Measured
on `front-fx`: seven Playwright invocations run 42 tests in 502.6 s, while a single
invocation runs *those same 42 tests plus 21 more* — 63 in all — in 218.6 s.

So the largest cost in the frontend suite is not the tests: it is invoking them.

## What this does

`./dev.py test front-transaction all` runs every Playwright spec of the category in
**one** invocation, and every vitest file in **one** more. `./dev.py test
front-transaction tx-delete` is untouched — a single action still means a single
spec, exactly as before.

## Why per-unit outcomes come with it, not after it

Consolidation alone would make the runner report "the category passed" instead of
naming which spec failed, and would coarsen `--resume` from a spec to a whole
category. That is a regression, so the reporters are read back here: Playwright
writes a JSON report, vitest writes one too, and each is folded back into a
per-spec verdict. The action-level summary the runner prints stays exactly as
detailed as it was.

## The precondition

Consolidation makes specs share a database, which is only safe once every spec
cleans up what it commits. That rule — and the `db-cleanup.ts` helper that
implements it for E2E — is documented in `runner_architecture.md`. It is a real
precondition: `tx-clone` committing a clone of the `delete-safe` ETH pair broke
`tx-delete` the first time these two shared an invocation.
"""

import contextlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from . import _common
from ._archive import log_file_for
from ._common import PROJECT_ROOT, Colors, print_error, print_info, print_success, print_warning

FRONTEND_DIR = PROJECT_ROOT / "frontend"


def _norm_spec(path: str) -> str:
    """Normalise a spec path to the form the inventory uses (relative to e2e/)."""
    p = path.replace("\\", "/")
    if "e2e/" in p:
        p = p.split("e2e/", 1)[1]
    return p


def group_frontend_units(scope: str | None) -> dict:
    """Collect, per frontend category, the Playwright and vitest units to consolidate.

    ``scope`` is a single category name, or ``None`` for every frontend category.
    Returns::

        {category: {"playwright": {project: {path: [actions]}},
                    "vitest": {path: [actions]}}}

    Two things this shape gets right that a flat ``{path: action}`` did not:

    - **Playwright units are grouped by project.** ``front-ai-export`` runs its
      specs on desktop *and* mobile; folding them into the desktop group would
      halve what runs, silently.
    - **A path can belong to several actions.** ``ai-export cutover`` is an alias
      that re-launches the same four specs the individual actions own. Recording
      every claimant means each action gets a verdict from the one run, instead
      of one action winning the spec and the other being re-run serially.
    """
    from ._inventory import ALL_PROJECTS, collect_launches

    launches, errors = collect_launches()
    if errors:
        return {}

    groups: dict = {}
    for (category, action), units in launches.items():
        if not category.startswith("front"):
            continue
        if scope is not None and category != scope:
            continue
        for kind, path, project in units:
            if kind not in ("playwright", "vitest"):
                continue
            slot = groups.setdefault(category, {"playwright": {}, "vitest": {}})
            if kind == "playwright":
                bucket = slot["playwright"].setdefault(project or ALL_PROJECTS, {})
                bucket.setdefault(_norm_spec(path), []).append(action)
            else:
                slot["vitest"].setdefault(path, []).append(action)
    return groups


# ---------------------------------------------------------------------------
# Playwright
# ---------------------------------------------------------------------------


def _playwright_results(report_path: Path) -> dict[str, bool]:
    """Read a Playwright JSON report into ``{spec path: passed}``.

    A spec counts as passed only when every test in it ended in a passing or
    skipped state, so a single red anywhere marks its own spec and nothing else.
    """
    try:
        data = json.loads(report_path.read_text())
    except Exception:
        return {}

    outcome: dict[str, bool] = {}

    def walk(suite: dict, inherited: str = "") -> None:
        file_name = suite.get("file") or inherited
        for spec in suite.get("specs", []):
            path = _norm_spec(spec.get("file") or file_name)
            ok = all(t.get("status") in ("expected", "skipped") for t in spec.get("tests", []))
            outcome[path] = outcome.get(path, True) and ok
        for child in suite.get("suites", []):
            walk(child, file_name)

    for suite in data.get("suites", []):
        walk(suite)
    return outcome


# Consolidation trades process count for process lifetime, and under JS coverage
# the second one has a ceiling. Measured: 8 specs / 163 tests / 7.8 min completes
# with room to spare, 25 specs / 215 tests / 20 min dies of heap exhaustion — the
# growth tracks how long the worker lives, not what any single spec does. Chunking
# bounds the lifetime without giving up the win: a category still pays setup a
# handful of times instead of once per spec.
_JS_COVERAGE_CHUNK = 8


def _chunk(specs: list[str], size: int) -> list[list[str]]:
    return [specs[i : i + size] for i in range(0, len(specs), size)]


def _group_log(category: str | None, unit: str):
    """
    Tee this consolidated run into ``--log-dir`` when one was requested.

    The frontend groups run through ``subprocess.run``, so without an explicit
    tee the log dir captured only the Python-side steps — that is, everything
    except the output a CI artifact is collected for. ``tee_output`` works at the
    file-descriptor level, so the npx child's stdout lands in the file too.
    """
    log_dir = _common.get_log_dir()
    if log_dir is None:
        return contextlib.nullcontext()
    try:
        return _common.tee_output(log_file_for(log_dir, category or _common.get_log_category(), unit))
    except Exception:
        return contextlib.nullcontext()


def run_playwright_group(specs: list[str], coverage: bool, project: str | None = "desktop", category: str | None = None) -> dict[str, bool]:
    """Run several specs in one Playwright invocation; return the per-spec verdict.

    ``project=None`` runs every configured project, which is what the AI Export
    actions do — narrowing them to desktop would halve what runs.

    A spec missing from the report is reported as failed: silence must never read
    as success — that is exactly how a run can lose units without anything going
    red.
    """
    report = Path(tempfile.mkdtemp(prefix="lf_pw_")) / "report.json"

    cmd = ["npx", "playwright", "test", *specs]
    if project:
        cmd.extend(["--project", project])
    cmd.append("--reporter=list,json")

    env = os.environ.copy()
    env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(report)
    _common.apply_e2e_workers(env)
    # Specs now share one database, so each test must start from the transaction
    # set populate_mock_data produced. See the fixture in e2e/fixtures/playwright.ts.
    env["LF_TX_HYGIENE"] = "1"
    if coverage and _common._COVERAGE_PY:
        env["COVERAGE_BACKEND"] = "1"
    if coverage and _common._COVERAGE_JS:
        env["COVERAGE_JS"] = "1"
        # A consolidated worker keeps one V8-coverage accumulator alive across every
        # spec of the category instead of throwing it away with the process after
        # each file. The per-worker monocart instance keeps that bounded, but the
        # raw entries still carry the full source of every script the run touched,
        # so the peak is genuinely higher than it used to be. Node's default old
        # space is not sized for it, and running out shows up as an unrelated test
        # dying with SIGABRT — a failure that names the victim, never the cause.
        node_opts = env.get("NODE_OPTIONS", "")
        if "max-old-space-size" not in node_opts:
            env["NODE_OPTIONS"] = f"{node_opts} --max-old-space-size=8192".strip()
    else:
        env.pop("COVERAGE_JS", None)

    print(f"{Colors.BLUE}Running: Playwright — {len(specs)} spec(s) in one invocation{Colors.NC}")
    print(f"Command:\n└─▶ $ cd frontend && {' '.join(cmd[:4])} … ({len(specs)} specs)")

    try:
        with _group_log(category, f"e2e-{project or 'all-projects'}"):
            subprocess.run(cmd, cwd=FRONTEND_DIR, text=True, env=env)
    except Exception as exc:
        print_error(f"Playwright error: {exc}")
        return {s: False for s in specs}

    results = _playwright_results(report)
    return {s: results.get(s, False) for s in specs}


# ---------------------------------------------------------------------------
# vitest
# ---------------------------------------------------------------------------


def _vitest_results(report_path: Path, known: list[str]) -> dict[str, bool]:
    """Read a vitest JSON report into ``{file path: passed}``."""
    try:
        data = json.loads(report_path.read_text())
    except Exception:
        return {}

    outcome: dict[str, bool] = {}
    for result in data.get("testResults", []):
        name = (result.get("name") or "").replace("\\", "/")
        match = next((k for k in known if name.endswith(k)), None)
        if match is None:
            continue
        ok = result.get("status") == "passed" and all(a.get("status") in ("passed", "pending", "todo") for a in result.get("assertionResults", []))
        outcome[match] = outcome.get(match, True) and ok
    return outcome


def run_vitest_group(paths: list[str], coverage: bool, category: str | None = None) -> dict[str, bool]:
    """Run several vitest files in one invocation; return the per-file verdict.

    Coverage is *not* passed on the command line: ``vitest.config.ts`` reads
    ``COVERAGE_JS`` from the environment, which the CLI has already exported.
    Adding ``--coverage`` here would turn the custom monocart provider on in
    runs where that variable is absent, which is exactly the configuration it
    does not support.
    """
    report = Path(tempfile.mkdtemp(prefix="lf_vitest_")) / "report.json"

    cmd = ["npx", "vitest", "run", *paths, "--reporter=default", "--reporter=json", f"--outputFile.json={report}"]

    print(f"{Colors.BLUE}Running: vitest — {len(paths)} file(s) in one invocation{Colors.NC}")

    try:
        with _group_log(category, "vitest"):
            subprocess.run(cmd, cwd=FRONTEND_DIR, text=True)
    except Exception as exc:
        print_error(f"vitest error: {exc}")
        return {p: False for p in paths}

    results = _vitest_results(report, paths)
    return {p: results.get(p, False) for p in paths}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _cache_key(category: str) -> str:
    """Run-cache namespace for the consolidated pass of one category.

    Deliberately separate from the serial suites' keys. Those are indexed by the
    human suite title ("Frontend User Tests"), which is written by hand inside
    each ``*_all`` function and is not derivable from the registry. Borrowing it
    here would mean guessing; a namespace of our own is both exact and obviously
    ours when it shows up in ``--run-status``.
    """
    return f"consolidated:{category}"


def run_consolidated(scope: str | None, coverage: bool, resume: bool = False) -> tuple[bool, set, dict]:
    """Run every consolidatable frontend unit in scope.

    Returns ``(ok, covered_actions, per_action_outcome)``. ``covered_actions`` is
    what the serial pass must not run again — including units skipped because a
    previous run already passed them, which are covered precisely by not needing
    to run.
    """
    from . import _frontend_common
    from ._inventory import ALL_PROJECTS
    from ._run_cache import is_passed, mark_failed, mark_passed

    groups = group_frontend_units(scope)
    if not groups:
        return True, set(), {}

    if not _frontend_common._ensure_frontend_build():
        return False, set(), {}
    if not _frontend_common._ensure_db_populated():
        return False, set(), {}
    if not _frontend_common._ensure_test_users():
        return False, set(), {}

    covered: set = set()
    outcome: dict = {}
    skipped: set = set()
    ok = True

    def claim(category: str, actions: list, passed: bool) -> None:
        """Fold one unit's verdict into every action that launches it."""
        nonlocal ok
        for action in actions:
            key = (category, action)
            covered.add(key)
            # An action owning several units passes only if all of them do.
            outcome[key] = outcome.get(key, True) and passed
            ok = ok and passed

    def already_green(category: str, actions: list) -> bool:
        """True when every action owning this unit is a cached pass."""
        return resume and all(is_passed(_cache_key(category), a) for a in actions)

    for category, kinds in sorted(groups.items()):
        for project, specs_by_path in sorted(kinds["playwright"].items()):
            specs = sorted(p for p, actions in specs_by_path.items() if not already_green(category, actions))
            for path, actions in specs_by_path.items():
                if path not in specs:
                    skipped.add(path)
                    claim(category, actions, True)
            if not specs:
                continue
            label = "desktop + mobile" if project == ALL_PROJECTS else project
            proj = None if project == ALL_PROJECTS else project
            batches = _chunk(specs, _JS_COVERAGE_CHUNK) if (coverage and _common._COVERAGE_JS) else [specs]
            suffix = f" in {len(batches)} batches" if len(batches) > 1 else ""
            print_info(f"▸ {category}: {len(specs)} spec(s) in one Playwright run ({label}){suffix}")
            for batch in batches:
                verdict = run_playwright_group(batch, coverage, project=proj, category=category)
                for spec, passed in verdict.items():
                    claim(category, specs_by_path[spec], passed)

        files_by_path = kinds["vitest"]
        files = sorted(p for p, actions in files_by_path.items() if not already_green(category, actions))
        for path, actions in files_by_path.items():
            if path not in files:
                skipped.add(path)
                claim(category, actions, True)
        if files:
            print_info(f"▸ {category}: {len(files)} vitest file(s) in one run")
            verdict = run_vitest_group(files, coverage, category=category)
            for path, passed in verdict.items():
                claim(category, files_by_path[path], passed)

    if skipped:
        print_info(f"🔄 Resuming: {len(skipped)} unit(s) already passed, not re-run")

    for (category, action), passed in sorted(outcome.items()):
        if passed:
            print_success(f"  ✓ {category} {action}")
            mark_passed(_cache_key(category), action)
        else:
            print_error(f"  ✘ {category} {action}")
            mark_failed(_cache_key(category), action)

    if not ok:
        print_warning("Consolidated pass has failures — the serial pass will not repeat these units")
    return ok, covered, outcome
