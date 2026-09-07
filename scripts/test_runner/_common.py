"""
Common utilities shared across all test_runner submodules.

Contains: globals, _run_test_suite, run_command, _build_pytest_cmd, helpers.
"""

import inspect
import os
import shutil
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Setup test database configuration
from backend.test_scripts.test_db_config import TEST_DATABASE_URL, TEST_DB_PATH, setup_test_database

# Import test utilities
from backend.test_scripts.test_utils import Colors, print_error, print_header, print_info, print_section, print_success, print_warning
from scripts.cli_base import pipenv_prefix

from ._run_cache import clear_suite, is_passed, load_cache, mark_failed, mark_passed

#: Directory holding the ``sitecustomize.py`` that starts coverage inside
#: ``multiprocessing`` **spawn** children (``risk/quant/spawn_worker.py``).
#: Spawned interpreters inherit the environment but no tracer, so without this
#: they measure nothing — see the file itself for the full rationale (P1-13).
COVERAGE_SITECUSTOMIZE_DIR = PROJECT_ROOT / "backend" / "test_scripts" / "_coverage_sitecustomize"


def apply_subprocess_coverage_env(env: dict) -> dict:
    """Wire ``COVERAGE_PROCESS_START`` + ``PYTHONPATH`` into a child environment.

    coverage.py's documented subprocess recipe: the child finds the repo
    ``.coveragerc`` (which has ``parallel = true``), starts its own tracer via
    the sitecustomize on the prepended PYTHONPATH entry, and writes
    ``{COVERAGE_FILE|.coverage}.<host>.<pid>.<rand>`` next to the parent's data
    file — where the existing combine steps already collect it. Call this for
    every process the runner spawns *while coverage is on* (pytest workers, the
    shared backend, Playwright → its webServer).
    """
    env["COVERAGE_PROCESS_START"] = str(PROJECT_ROOT / ".coveragerc")
    site_dir = str(COVERAGE_SITECUSTOMIZE_DIR)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = site_dir if not existing else site_dir + os.pathsep + existing
    return env


# Global flag for coverage mode (set by main())
# Holds the requested language: "py", "js", "all" — or False when disabled.
_COVERAGE_MODE = False
# Languages actually collected, derived from _COVERAGE_MODE and from what the
# selected suite is able to measure (a backend suite cannot produce JS data).
_COVERAGE_PY = False
_COVERAGE_JS = False
# Coverage source: "backend", "frontend", or None (auto-detect)
_COVERAGE_SOURCE = None
# Browser workers for Playwright, resolved from --workers by main(). The
# frontend used to read E2E_WORKERS straight from the ambient environment, so
# `--workers 4` sped up the backend and left the browser serial: the same flag
# meant two different things on the two halves of the suite.
_E2E_WORKERS = 1
# Global flag for resume mode (set by main())
_RESUME_MODE = False
# (category, action) pairs a parallel pre-pass has already executed. The serial
# pass skips them, which is how the two passes divide the work without either
# of them needing to know the other exists.
_SKIP_ACTIONS: set = set()
# Actions the consolidated (or parallel) pre-pass ran and found red. Kept apart from
# _SKIP_ACTIONS because the two answer different questions: "was it already run?" and
# "did it pass?". Conflating them is how a red becomes a green summary.
_FAILED_ACTIONS: set = set()
# Whether a failing action stops the suite. Off by default: a red is worth more when
# you can see how wide the damage is, because nine failures in one worker are usually
# nine symptoms of one cause, and stopping at the first hides that. `--fail-fast` opts
# back in. Kept as module state rather than a parameter because _run_test_suite is
# called from ~15 `*_all` functions that have no business knowing about it.
_FAIL_FAST = False

# Destination for per-unit logs, or None when --log-dir was not requested.
_LOG_DIR = None
_LOG_CATEGORY = "run"


def resolve_e2e_workers(requested: int) -> int:
    """Cap browser workers at what the machine can actually drive.

    A backend unit is a Python process mostly waiting on SQLite; a Playwright
    worker is a full Chromium *plus* its share of a uvicorn pool sized at
    ``ceil(workers/2)``. The two do not scale alike, and past the machine's
    ceiling the browser half does not merely stop getting faster — it gets
    slower and starts failing on its own timeouts.

    Measured on a 10-core machine, front-utility with coverage:

        4 workers → 165/165 in 3.3 min
        5 workers → 165/165 in 3.5 min
        8 workers →  20 failed in 5.8 min   (7 of them: login past 20s)

    So ``--workers 8`` is honoured for the backend, where it pays (services:
    80 units, 8 workers, green), and capped here, where it does not. Half the
    logical cores is Playwright's own default heuristic and lands on 5 above.
    Setting ``E2E_WORKERS`` in the environment overrides the cap for probes.
    """
    ceiling = max(1, (os.cpu_count() or 4) // 2)
    return min(requested, ceiling)


def apply_e2e_workers(env: dict) -> dict:
    """
    Put the runner's `--workers` into a Playwright child's environment.

    There are two places that launch Playwright — the per-unit path in
    `_frontend_common._run_playwright` and the consolidated path in
    `_consolidate._run_playwright_batch` — and wiring only one of them is a
    silent bug: the run stays green and simply takes three times as long, which
    nothing reports. Both call this.

    An `E2E_WORKERS` already present in the environment wins, so a probe can
    override a single run without going through the runner.
    """
    requested = getattr(sys.modules[__name__], "_E2E_WORKERS", 1)
    workers = resolve_e2e_workers(requested)
    if workers > 1 and "E2E_WORKERS" not in os.environ:
        env["E2E_WORKERS"] = str(workers)
        capped = f" (capped from {requested}: {os.cpu_count()} logical cores)" if workers < requested else ""
        print(f"{Colors.YELLOW}🧵 Playwright workers: {workers}{capped}{Colors.NC}")
    return env


def set_log_dir(path, category: str = "run") -> None:
    """Enable per-unit logging into ``path`` (already prepared by the caller)."""
    global _LOG_DIR, _LOG_CATEGORY
    _LOG_DIR = Path(path) if path else None
    _LOG_CATEGORY = category or "run"


def get_log_dir():
    return _LOG_DIR


def get_log_category() -> str:
    return _LOG_CATEGORY


def set_fail_fast(enabled: bool) -> None:
    global _FAIL_FAST
    _FAIL_FAST = enabled


@contextmanager
def tee_output(log_path):
    """
    Tee ALL output written to the stdout/stderr file descriptors (fd 1 & 2) to a
    log file, while still printing to the console.

    Unlike a plain ``sys.stdout`` redirect, this works at the OS file-descriptor
    level, so it also captures output from child processes launched with
    ``capture_output=False`` (e.g. ``npm run build``, ``pytest``, ``playwright``),
    which inherit fd 1/2. This is what lets a CI artifact contain the *full* log
    (including the vite build error) and not just the high-level summary.

    ANSI color codes are preserved verbatim in the log file.
    """
    log_path = Path(log_path)
    if log_path.parent and not log_path.parent.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Flush Python-level buffers before swapping the underlying fds.
    sys.stdout.flush()
    sys.stderr.flush()

    log_fh = open(log_path, "wb")
    saved_out = os.dup(1)
    saved_err = os.dup(2)
    out_r, out_w = os.pipe()
    err_r, err_w = os.pipe()

    def _pump(read_fd, console_fd):
        try:
            while True:
                data = os.read(read_fd, 65536)
                if not data:
                    break
                os.write(console_fd, data)
                log_fh.write(data)
                log_fh.flush()
        except OSError:
            pass

    threads = [
        threading.Thread(target=_pump, args=(out_r, saved_out), daemon=True),
        threading.Thread(target=_pump, args=(err_r, saved_err), daemon=True),
    ]

    # Point fd 1/2 at the pipe write ends; children inherit these.
    os.dup2(out_w, 1)
    os.dup2(err_w, 2)
    for t in threads:
        t.start()

    try:
        yield log_path
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        # Restore the real console fds.
        os.dup2(saved_out, 1)
        os.dup2(saved_err, 2)
        # Close the pipe write ends so the pump threads see EOF and drain.
        os.close(out_w)
        os.close(err_w)
        for t in threads:
            t.join(timeout=5)
        os.close(out_r)
        os.close(err_r)
        os.close(saved_out)
        os.close(saved_err)
        log_fh.close()


def _run_test_suite(  # noqa: C901 — flat test-run loop + summary printing, no nested logic
    suite_name: str,
    tests: list[tuple[str, Callable]],
    verbose: bool = False,
    header_msg: str = None,
    info_msgs: list[str] = None,
    summary_title: str = None,
    success_msg: str = None,
    combine_coverage: bool = False,
    resume: bool = False,
) -> bool:
    """
    Generic function to run a suite of tests with consistent output format.

    Args:
        suite_name: Name of the test suite (e.g., "API Tests", "Database Tests")
        tests: List of (test_name, test_function) tuples
        verbose: Pass to test functions
        header_msg: Optional custom header message (default: "LibreFolio {suite_name}")
        info_msgs: Optional list of info messages to print before tests
        summary_title: Optional custom summary section title (default: "{suite_name} Summary")
        success_msg: Optional custom success message (default: "All {suite_name.lower()} passed! 🎉")
        combine_coverage: If True, combine coverage data after tests (for API/E2E tests)
        resume: If True, skip tests already cached as passed

    Returns:
        bool: True if all tests passed
    """
    suite_key = suite_name  # Use suite_name as cache key

    # Print header (unless None to skip)
    if header_msg is not None or header_msg != "":
        print_header(header_msg or f"LibreFolio {suite_name}")

    # Print info messages
    if info_msgs:
        for msg in info_msgs:
            print_info(msg)

    if resume:
        cached = load_cache(suite_key)
        cached_passed = cached.get("passed", [])
        if cached_passed:
            print_info(f"🔄 Resuming: {len(cached_passed)} test(s) already passed, skipping them")

    total_tests = len(tests)
    results = {}

    # Initialize all as pending
    for test_name, _ in tests:
        results[test_name] = None

    # Run tests
    for test_name, test_func in tests:
        # Skip if already passed in cache (resume mode)
        if resume and is_passed(suite_key, test_name):
            results[test_name] = True
            print(f"{Colors.CYAN}⏩ SKIP (cached pass){Colors.NC} - {test_name}")
            continue

        success = test_func()
        results[test_name] = success

        if success:
            mark_passed(suite_key, test_name)
        else:
            mark_failed(suite_key, test_name)
            print_error(f"Test failed: {test_name}")
            if not _FAIL_FAST:
                print_warning("Continuing to the end (use --fail-fast to stop here)")
                continue
            print_warning(f"Stopping {suite_name.lower()} execution")
            if resume:
                print_info("💡 Fix the issue and re-run with --resume to continue from here")
            break

    # Summary
    print_section(summary_title or f"{suite_name} Summary")
    passed = sum(1 for success in results.values() if success is True)
    failed = sum(1 for success in results.values() if success is False)
    pending = sum(1 for success in results.values() if success is None)

    for test_name, _ in tests:
        success = results[test_name]
        if success is True:
            status = f"{Colors.GREEN}✅ PASS{Colors.NC}"
        elif success is False:
            status = f"{Colors.RED}❌ FAIL{Colors.NC}"
        else:
            status = f"{Colors.YELLOW}⏳ PENDING{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total_tests} tests passed")
    if pending > 0:
        print(f"{Colors.YELLOW}⏳ {pending} test(s) not run (stopped early){Colors.NC}")

    # Combine coverage if requested
    if combine_coverage and _COVERAGE_PY:
        print_section("Combining Coverage Data")
        print_info("Merging coverage from test server subprocess...")
        try:
            result = subprocess.run(["coverage", "combine", "--keep"], capture_output=True, text=True, cwd=PROJECT_ROOT)
            if result.returncode == 0:
                print_success("Coverage data combined successfully")
            else:
                print_warning(f"Coverage combine had warnings: {result.stderr}")
        except Exception as e:
            print_warning(f"Could not combine coverage: {e}")

    if passed == total_tests:
        # Full suite passed — clear cache for this suite (cycle complete)
        clear_suite(suite_key)
        print_success(success_msg or f"All {suite_name.lower()} passed! 🎉")
        return True
    else:
        if failed > 0:
            print_error(f"{failed} test(s) failed")
        return False


def _get_category_tests_for_all(category: str, verbose: bool, **passthrough) -> list:
    """
    Generate list of (name, lambda) tuples for a category's all test.

    Automatically excludes the 'all' action itself and uses registry
    as single source of truth: an action that is registered is, by
    construction, executed by its category's ``all``.

    ``passthrough`` carries the frontend options (ui, headed, debug, coverage)
    and is filtered per action, because the registered functions do not all
    accept the same keywords.

    NOTE: Uses lazy import of TEST_REGISTRY to avoid circular imports.
    """
    from ._registry import TEST_REGISTRY

    if category not in TEST_REGISTRY:
        return []

    tests = []
    for action, info in TEST_REGISTRY[category].items():
        if action == "_meta" or action == "all":
            continue
        if not info.get("in_all", True):
            continue
        if (category, action) in _SKIP_ACTIONS:
            continue
        func = info["func"]
        name = info.get("name", action)
        try:
            params = inspect.signature(func).parameters
        except (TypeError, ValueError):
            params = {}
        kwargs = {"verbose": verbose}
        kwargs.update({k: v for k, v in passthrough.items() if k in params})
        tests.append((name, lambda f=func, kw=kwargs: f(**kw)))
    return tests


def nothing_left_to_run(category: str) -> bool:
    """True when the consolidated pass already ran every action of this category.

    Without this guard the serial suite still builds the frontend, repopulates the
    database and creates the E2E users before discovering it has nothing to execute
    — about ten seconds per category, and a "Populating test DB" line that reads as
    if work were still pending. It is also misleading in a way that matters: the
    repopulation happens *after* the consolidated pass, so anyone reading the log
    top-down sees the database wiped after the tests that used it.
    """
    from ._registry import TEST_REGISTRY

    actions = TEST_REGISTRY.get(category)
    if not actions:
        return False
    runnable = [
        a
        for a, info in actions.items()
        if a not in ("_meta", "all") and info.get("in_all", True)
    ]
    if not runnable:
        return False
    return all((category, a) in _SKIP_ACTIONS for a in runnable)


def consolidated_verdict(category: str) -> bool:
    """Report the consolidated outcome in place of the skipped serial suite.

    Returns what the category's ``all`` must return, so a unit that failed in the
    consolidated pass still turns its category red. Without this the pre-pass would
    print ``✘`` and the suite summary would then print "ALL TESTS PASSED" a few
    lines below — the exit code was already correct, but a summary that contradicts
    it is worse than no summary at all.
    """
    failed = sorted(a for (c, a) in _FAILED_ACTIONS if c == category)
    if not failed:
        print_info("Already covered by the consolidated pass")
        return True
    print_error(f"Failed in the consolidated pass: {', '.join(failed)}")
    return False


def _build_pytest_cmd(test_path: str, test_names: list = None) -> list:
    """
    Build pytest command with optional test name filter.

    Args:
        test_path: Path to test file or directory
        test_names: Optional list of test names to filter (uses -k flag)

    Returns:
        List of command parts for run_command
    """
    cmd = [*pipenv_prefix(), "python", "-m", "pytest", test_path, "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])
    return cmd


# TODO: riscrivere in maniera sensata questa funzione affinchè per i test si prenda solo il path e aggiunga tutto lei
def run_command(cmd: list[str], description: str, verbose: bool = False, timeout: int = 600) -> bool:
    """
    Run a command and return True if successful.

    When ``--log-dir`` is active every invocation also lands in its own file, so
    a failure can be read afterwards without re-running it. The tee works at the
    file-descriptor level, so it captures the child's output too.
    """
    if _LOG_DIR is None:
        return _run_command_body(cmd, description, verbose, timeout)

    from ._archive import log_file_for

    try:
        log_path = log_file_for(_LOG_DIR, _LOG_CATEGORY, description)
    except Exception:
        return _run_command_body(cmd, description, verbose, timeout)

    with tee_output(log_path):
        return _run_command_body(cmd, description, verbose, timeout)


def _run_command_body(cmd: list[str], description: str, verbose: bool = False, timeout: int = 600) -> bool:  # noqa: C901 — flat command/env flag plumbing + error handling, no nested logic
    """
    Run a command and return True if successful.

    Args:
        cmd: Command parts to run
        description: Human-readable description for output
        verbose: If True, stream stdout/stderr live
        timeout: Max seconds per command (default 300s). Use 600 for E2E/frontend.

    If _COVERAGE_PY is set and the command is a pytest test, automatically
    adds coverage tracking flags and updates the cumulative coverage database.
    """
    # Check if this is a pytest command and coverage is enabled
    is_pytest = "pytest" in " ".join(cmd)
    use_coverage = _COVERAGE_PY and is_pytest

    # If coverage mode, enhance pytest command
    if is_pytest:
        pytest_idx = next((i for i, c in enumerate(cmd) if "pytest" in c), None)
        if pytest_idx is not None:
            flags_to_add = []
            if verbose:
                flags_to_add.append("-s")
            if use_coverage:
                html_dir = "htmlcov-backend" if _COVERAGE_SOURCE != "frontend" else "htmlcov-backend-e2e"
                flags_to_add.extend(
                    [
                        "--cov=backend/app",
                        "--cov-append",
                        f"--cov-report=html:{html_dir}",
                        "--cov-report=term-missing:skip-covered",
                    ]
                )
            if flags_to_add:
                cmd = cmd[: pytest_idx + 1] + flags_to_add + cmd[pytest_idx + 1 :]
                if use_coverage:
                    print(f"{Colors.YELLOW}📊 Coverage tracking enabled (appending to .coverage){Colors.NC}")
    print(f"\n{Colors.BLUE}Running: {description}{Colors.NC}")
    print(f"Command:\n└─▶ $ {' '.join(cmd)}")

    # --- Coverage isolation: swap-in the correct accumulated DB ---
    if use_coverage:
        cwd_p = Path(os.getcwd())
        data_dir = cwd_p / ".coverage_data"
        data_dir.mkdir(exist_ok=True)
        source = _COVERAGE_SOURCE or "backend"
        accumulated_db = data_dir / source
        main_cov = cwd_p / ".coverage"
        if accumulated_db.exists():
            shutil.copy2(str(accumulated_db), str(main_cov))

    try:
        env = None
        try:
            if any("backend.test_scripts" in c or c.endswith(".py") and "backend/test_scripts" in c for c in cmd):
                env = os.environ.copy()
                env["LIBREFOLIO_TEST_MODE"] = "1"
                env["DATABASE_URL"] = TEST_DATABASE_URL
                if use_coverage:
                    env["COVERAGE_RUN"] = "1"
                    # Let multiprocessing spawn children (spawn_worker.py) start
                    # their own tracer; their data files land next to .coverage,
                    # which pytest-cov combines at session finish.
                    apply_subprocess_coverage_env(env)
        except Exception:
            env = None
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=not verbose, text=True, env=env, timeout=timeout)

        if result.returncode == 0:
            print_success(f"{description} - PASSED")
            if use_coverage:
                print(f"{Colors.GREEN}✅ Coverage data appended to .coverage database{Colors.NC}")
            return True
        else:
            print_error(f"{description} - FAILED (exit code: {result.returncode})")
            # Print captured output so the pytest summary/traceback is visible
            if not verbose and result.stdout:
                print(result.stdout)
            if not verbose and result.stderr:
                print(result.stderr, end="")
            if use_coverage:
                print(f"{Colors.YELLOW}⚠️  Coverage data still appended despite test failure{Colors.NC}")
            return False

    except Exception as e:
        print_error(f"{description} - ERROR: {e}")
        return False

    finally:
        if use_coverage:
            cwd_p = Path(os.getcwd())
            main_cov = cwd_p / ".coverage"
            if main_cov.exists():
                data_dir = cwd_p / ".coverage_data"
                source = _COVERAGE_SOURCE or "backend"
                shutil.copy2(str(main_cov), str(data_dir / source))


# ── Registry builder helpers ────────────────────────────────────────────


def make_category(help_text: str, description: str, setup=None, setup_exclusive: bool = False, default_isolation: str = None) -> dict:
    """Create the _meta entry for a registry category.

    ``setup`` is what the category must do to its environment before any of its
    units runs — ``services`` recreates the database empty, ``api`` reseeds it.
    It used to live inline inside the ``all`` action, which was fine while that
    action was the only entry point. It no longer is: the consolidated pass runs
    the same units without going through it, and a second copy of "populate
    first" would be a copy free to drift. Declaring it here gives both callers
    one definition.

    ``setup_exclusive`` marks a setup that cannot run while the shared backend
    holds the database file. ``services`` deletes the SQLite file and rebuilds it
    from the migrations: with a server attached to the old inode, the migration
    is refused and the run continues against a database with no tables. Such a
    setup is hoisted to before the server starts. ``api``'s is not exclusive — it
    only inserts rows, and concurrent writers on WAL are fine.

    ``default_isolation`` states what is true of the category as a whole, so the
    exceptions are the only thing written down. ``api`` is ``write-scoped``
    because its units create their own user and their own rows and address them
    by id — the property is a *convention of the category*, and declaring it
    fifty times would hide the two units that do not have it behind the
    forty-eight that do. Overriding it per unit still works, and an
    ``exclusive_because`` still wins.
    """
    meta = {"help": help_text, "description": description}
    if setup is not None:
        meta["setup"] = setup
        meta["setup_exclusive"] = setup_exclusive
    if default_isolation:
        meta["default_isolation"] = default_isolation
    return {"_meta": meta}


#: Categories whose setup already ran in this invocation. A setup is declared
#: once but reachable from three callers (the ``all`` action, the consolidated
#: pass, the hoist before the shared server); it must still happen exactly once.
_SETUP_DONE: set = set()


def setup_is_exclusive(category: str) -> bool:
    """True when this category's setup needs the database file to itself."""
    from ._registry import TEST_REGISTRY

    meta = TEST_REGISTRY.get(category, {}).get("_meta", {})
    return bool(meta.get("setup") and meta.get("setup_exclusive"))


def run_category_setup(category: str) -> bool:
    """Run a category's declared setup, once per invocation. True when it is fine."""
    from ._registry import TEST_REGISTRY

    setup = TEST_REGISTRY.get(category, {}).get("_meta", {}).get("setup")
    if setup is None or category in _SETUP_DONE:
        return True
    _SETUP_DONE.add(category)
    return bool(setup())


def add_test(category: dict, action: str, func, *, test_names: bool = True, name: str, desc: str, prereq: str = None, tests: str = None, note: str = None, in_all: bool = True, isolation: str = None, exclusive_because: str = None) -> None:
    """Add a single test entry to a category dict.

    ``in_all=False`` marks an action whose tests another action already runs —
    an aggregate alias, or a concern folded into one consolidated invocation.
    The derived ``all`` skips it to avoid executing the same spec twice; the
    reachability check is unaffected, because it reasons about launched paths
    rather than actions.

    ``isolation`` overrides the classifier, which defaults every pytest unit that
    touches a database to ``write-global``. Declaring ``read`` or
    ``write-scoped`` is a claim that has to be **earned by a passing parallel
    run**, not asserted: a wrong ``write-global`` costs seconds, a wrong ``read``
    costs an intermittent red that will be blamed on something else.

    ``exclusive_because`` is the one line the catalogue requires from a unit that
    stays ``write-global`` on purpose. It must name what the unit mutates that
    cannot be scoped — "it rewrites `global_settings`, a single row shared by
    every user" — not that sharing would be inconvenient.
    """
    entry = {"func": func, "test_names": test_names, "name": name, "desc": desc, "in_all": in_all}
    if prereq:
        entry["prereq"] = prereq
    if tests:
        entry["tests"] = tests
    if note:
        entry["note"] = note
    if isolation:
        entry["isolation"] = isolation
    if exclusive_because:
        entry["exclusive_because"] = exclusive_because
    category[action] = entry
