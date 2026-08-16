"""
CLI: argument parsers, dispatch, main entry point.
"""

import argparse
import contextlib
import os
import re
import sys
import traceback
from pathlib import Path

import argcomplete

from scripts.coverage_analysis import register_subparser as register_cov_parser
from scripts.coverage_analysis import run_analysis as run_coverage_analysis

# Import common module to set its globals
from . import _common
from ._backend_external import _get_external_extra_args
from ._common import (
    Colors,
    print_error,
    print_header,
    print_info,
    print_section,
    print_success,
    print_warning,
)
from ._coverage import _clean_js_coverage_dirs, _finalize_coverage, _finalize_js_coverage, _handle_coverage_command
from ._frontend_common import BACKEND_TEST_PATHS, _list_front_tests, _list_pytest_tests
from ._registry import TEST_REGISTRY
from ._run_cache import clear_all as _cache_clear_all
from ._run_cache import show_status as _cache_show_status
from ._suites import (
    _BACKEND_CATEGORIES,
    _FRONTEND_CATEGORIES,
    _clean_coverage_dirs,
    run_all_backend_tests,
    run_all_frontend_tests,
    run_all_tests,
)


def get_category_choices(category: str) -> list[str]:
    """Get list of valid actions for a category from TEST_REGISTRY."""
    if category not in TEST_REGISTRY:
        return []
    return [k for k in TEST_REGISTRY[category].keys() if k != "_meta"]


def generate_epilog(category: str) -> str:
    """Generate epilog text for a category parser from TEST_REGISTRY."""
    if category not in TEST_REGISTRY:
        return ""

    cat_data = TEST_REGISTRY[category]
    lines = []

    if "_meta" in cat_data:
        lines.append(cat_data["_meta"].get("description", ""))
        lines.append("\nTest commands:")

    for action, info in cat_data.items():
        if action == "_meta":
            continue
        name = info.get("name", action)
        desc = info.get("desc", "")
        accepts_names = info.get("test_names", False)
        names_hint = " [TEST_NAME]" if accepts_names else ""
        lines.append(f"  {action:20}{names_hint:14} {desc}")
        if info.get("prereq"):
            lines.append(f"  {'':34} Prereq: {info['prereq']}")

    return "\n".join(lines)


def run_test_from_registry(category: str, action: str, verbose: bool = False, test_names: list = None, **kwargs) -> bool:
    """Run a test from the registry."""
    import inspect

    if category not in TEST_REGISTRY:
        print_error(f"Unknown category: {category}")
        return False

    if action not in TEST_REGISTRY[category]:
        print_error(f"Unknown action '{action}' for category '{category}'")
        return False

    info = TEST_REGISTRY[category][action]
    test_func = info["func"]
    accepts_test_names = info.get("test_names", False)

    # Special: db category actions with extra params
    if category == "db" and action == "populate":
        force = kwargs.get("force", False)
        clean = kwargs.get("clean", False)
        with_static = kwargs.get("with_static", False)
        with_reports = kwargs.get("with_reports", False)
        return test_func(verbose=verbose, force=force, clean=clean, with_static=with_static, with_reports=with_reports)

    # Handle --list for any category
    list_tests = kwargs.get("list_tests", False)
    if list_tests:
        if category in _FRONTEND_CATEGORIES:
            return _list_front_tests(category, action)
        elif category in BACKEND_TEST_PATHS:
            return _list_pytest_tests(category, action)
        else:
            print_error(f"--list not supported for category '{category}'")
            return True

    # Frontend categories (have ui, headed, debug flags + test_names)
    if category in _FRONTEND_CATEGORIES:
        ui = kwargs.get("ui", False)
        headed = kwargs.get("headed", False)
        debug = kwargs.get("debug", False)
        coverage = kwargs.get("coverage", False) or _common._COVERAGE_MODE
        if accepts_test_names and test_names:
            return test_func(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)
        return test_func(verbose=verbose, ui=ui, headed=headed, debug=debug, coverage=coverage)

    # External category (has --providers / --exclude-providers)
    if category == "external":
        providers = kwargs.get("providers", None)
        exclude_providers = kwargs.get("exclude_providers", None)
        func_params = inspect.signature(test_func).parameters
        call_kwargs = {"verbose": verbose}
        if "providers" in func_params:
            call_kwargs["providers"] = providers
            call_kwargs["exclude_providers"] = exclude_providers
        if accepts_test_names and test_names and "test_names" in func_params:
            call_kwargs["test_names"] = test_names
        return test_func(**call_kwargs)

    # Standard backend test
    if accepts_test_names and test_names:
        return test_func(verbose=verbose, test_names=test_names)
    return test_func(verbose=verbose)


# Backend suite directories, mapped to the runner module that registers them.
# Shared by the orphan check and the reachability check so the two cannot drift.
# test_*.py files at the root of test_scripts/ are shared helpers, not suites.
from ._inventory import BACKEND_SUITE_DIRS as _BACKEND_SUITE_DIRS

# Per-unit logs are on by default. Playwright wipes `test-results/` on the next run and
# a failing worker's pytest output scrolls past in a suite this size, so a red diagnosed
# after the fact used to depend on having remembered a flag beforehand. Evidence should
# not be opt-in: pass `--log-dir ""` to turn it off.
DEFAULT_LOG_DIR = ".testLog"


def _check_orphan_tests() -> int:
    """Find test files not registered in the test runner.

    Checks:
    - Backend: test_*.py files in each test directory vs registered in _backend_*.py
    - Frontend: *.spec.ts files in e2e/ vs referenced in _frontend_*.py
    - Frontend unit: src/**/*.test.ts vs explicit Vitest paths referenced in _frontend_*.py

    Returns 0 if no orphans, 1 if orphans found.
    """

    project_root = Path(__file__).parent.parent.parent
    runner_dir = Path(__file__).parent
    orphans_found = False

    print(f"\n{Colors.CYAN}🔍 Checking for orphan test files...{Colors.NC}\n")

    # ── Backend: scan each test directory ──
    backend_dirs = {d: _BACKEND_SUITE_DIRS[d] for d in _BACKEND_SUITE_DIRS}
    # Collect all registered paths from ALL runner files (some tests cross-reference)
    all_runner_files = list(runner_dir.glob("_backend_*.py"))
    all_registered_paths = set()
    for rf in all_runner_files:
        content = rf.read_text()
        # Match patterns like: "backend/test_scripts/test_api/test_foo.py"
        for m in re.finditer(r'test_scripts/([^"\']+\.py)', content):
            all_registered_paths.add(m.group(1))

    for test_dir, runner_file in backend_dirs.items():
        dir_path = project_root / "backend" / "test_scripts" / test_dir
        if not dir_path.exists():
            continue

        actual_files = sorted(f.name for f in dir_path.glob("test_*.py"))
        orphan_files = [f for f in actual_files if f"{test_dir}/{f}" not in all_registered_paths]

        if orphan_files:
            orphans_found = True
            print(f"  {Colors.RED}❌ {test_dir}/{Colors.NC}  ({len(orphan_files)} orphan{'s' if len(orphan_files) > 1 else ''})")
            for f in orphan_files:
                print(f"     • {f}")
        else:
            print(f"  {Colors.GREEN}✓ {test_dir}/{Colors.NC}  (all {len(actual_files)} files registered)")

    # ── Frontend: scan e2e spec files ──
    print()
    e2e_dir = project_root / "frontend" / "e2e"
    # gallery.spec.ts is a docs tool (./dev.py mkdocs gallery), not a test
    frontend_excluded = {"gallery.spec.ts"}
    if e2e_dir.exists():
        actual_specs = sorted(f.name for f in e2e_dir.rglob("*.spec.ts") if f.name not in frontend_excluded)

        # Collect referenced specs from all frontend runner files
        frontend_runner_files = list(runner_dir.glob("_frontend_*.py"))
        registered_specs = set()
        for rf in frontend_runner_files:
            content = rf.read_text()
            for m in re.finditer(r"([a-z_-]+\.spec\.ts)", content):
                registered_specs.add(m.group(1))

        orphan_specs = [s for s in actual_specs if s not in registered_specs]

        if orphan_specs:
            orphans_found = True
            print(f"  {Colors.RED}❌ frontend/e2e/{Colors.NC}  ({len(orphan_specs)} orphan{'s' if len(orphan_specs) > 1 else ''})")
            for s in orphan_specs:
                print(f"     • {s}")
        else:
            print(f"  {Colors.GREEN}✓ frontend/e2e/{Colors.NC}  (all {len(actual_specs)} specs registered)")

    # ── Frontend unit: scan src/**/*.test.ts ──
    frontend_src_dir = project_root / "frontend" / "src"
    if frontend_src_dir.exists():
        actual_unit_tests = sorted(str(f.relative_to(project_root / "frontend")).replace("\\", "/") for f in frontend_src_dir.rglob("*.test.ts"))

        # Collect explicit Vitest paths from frontend runner files.
        # We intentionally require concrete file-path wiring here; generic
        # `vitest run` / `npm run test:unit` commands are not enough to prove a
        # specific unit test has been consciously registered in the CLI.
        frontend_runner_files = list(runner_dir.glob("_frontend_*.py"))
        registered_unit_tests = set()
        for rf in frontend_runner_files:
            content = rf.read_text()
            for m in re.finditer(r"(src/[^\"']+\.test\.ts)", content):
                registered_unit_tests.add(m.group(1))

        orphan_unit_tests = [t for t in actual_unit_tests if t not in registered_unit_tests]

        if orphan_unit_tests:
            orphans_found = True
            print(f"  {Colors.RED}❌ frontend/src/**/*.test.ts{Colors.NC}  ({len(orphan_unit_tests)} orphan{'s' if len(orphan_unit_tests) > 1 else ''})")
            for t in orphan_unit_tests:
                print(f"     • {t}")
        else:
            print(f"  {Colors.GREEN}✓ frontend/src/**/*.test.ts{Colors.NC}  (all {len(actual_unit_tests)} unit tests registered)")

    # ── Summary ──
    print()
    if orphans_found:
        print(f"  {Colors.YELLOW}⚠️  Orphan files found! Add them to the appropriate _backend_*.py or _frontend_*.py module.{Colors.NC}")
        return 1
    else:
        print(f"  {Colors.GREEN}✅ All test files are registered in the test runner.{Colors.NC}")
        return 0


def _check_unreachable_tests() -> int:
    """Find test files that are registered but no ``all`` action ever runs.

    Registration and reachability are different guarantees: a spec named in a
    runner module passes the orphan check even when no ``all`` action reaches
    it, so it silently stops running. This closes that gap by asking the
    inventory what the ``all`` actions would launch, without launching anything.

    Returns 0 if everything registered is reachable, 1 otherwise.
    """
    from ._inventory import is_covered, on_disk, reachable_paths

    unreachable_found = False

    print(f"\n{Colors.CYAN}🔍 Checking that every test is reachable from an 'all' action...{Colors.NC}\n")

    reached, errors = reachable_paths()
    actual = on_disk()

    if errors:
        print(f"  {Colors.YELLOW}⚠️  Could not collect some categories:{Colors.NC}")
        for cat, err in sorted(errors.items()):
            print(f"     • {cat}: {err}")
        print()

    labels = {
        "playwright": "frontend/e2e/",
        "vitest": "frontend/src/**/*.test.ts",
        "pytest": "backend/test_scripts/",
    }

    for engine, label in labels.items():
        files = actual[engine]
        if not files:
            continue
        missing = [t for t in files if not is_covered(t, reached[engine])]
        if missing:
            unreachable_found = True
            print(f"  {Colors.RED}❌ {label}{Colors.NC}  ({len(missing)} unreachable)")
            for t in missing:
                print(f"     • {t}")
        else:
            print(f"  {Colors.GREEN}✓ {label}{Colors.NC}  (all {len(files)} reachable from 'all')")

    print()
    if unreachable_found:
        print(f"  {Colors.YELLOW}⚠️  Registered but never executed! Add them to the category's 'all' action.{Colors.NC}")
        return 1
    print(f"  {Colors.GREEN}✅ Every registered test is reachable from an 'all' action.{Colors.NC}")
    return 0


def create_subparser_from_registry(subparsers, category: str, extra_args: list = None):
    """Create a subparser for a category from TEST_REGISTRY."""
    if category not in TEST_REGISTRY:
        raise ValueError(f"Unknown category: {category}")

    meta = TEST_REGISTRY[category].get("_meta", {})

    parser = subparsers.add_parser(category, help=meta.get("help", f"{category} tests"), description=generate_epilog(category), formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("action", choices=get_category_choices(category), help=f"{category.capitalize()} test to run")

    parser.add_argument("test_names", nargs="*", help="Optional: specific test names to run")

    if extra_args:
        for arg_name, arg_kwargs in extra_args:
            parser.add_argument(arg_name, **arg_kwargs)

    return parser


def _generate_main_epilog() -> str:
    """Generate main parser epilog from TEST_REGISTRY."""
    lines = ["\nTest Categories:\n"]

    for category in TEST_REGISTRY.keys():
        meta = TEST_REGISTRY[category].get("_meta", {})
        help_text = meta.get("help", f"{category} tests")
        lines.append(f"  {category:20} - {help_text}")

    lines.append(f"  {'all':20} - Run ALL tests in optimal order")
    lines.append(f"  {'coverage-report':20} - Analyse coverage: find uncovered function bodies")
    lines.append("")
    lines.append("Examples:")
    lines.append("  dev.py test all                 # All tests (optimal order)")
    lines.append("  dev.py test -q all              # All tests with quiet output (no details)")
    lines.append("  dev.py test api auth            # Only auth API tests")
    lines.append("  dev.py test db create           # Create database")
    lines.append("")

    return "\n".join(lines)


def _register_coverage_subparser(subparsers):
    """Register the 'coverage' sub-command."""
    cov_parser = subparsers.add_parser(
        "coverage",
        help="📊 View or combine coverage reports (backend/frontend/combined)",
        description="""
Coverage Report Management

View differentiated coverage reports:
Python (what the backend executed):
  show backend     Backend test coverage (htmlcov-backend/)
  show frontend    Frontend E2E → backend coverage (htmlcov-backend-e2e/)
  show combined    Combine all data + open merged report (htmlcov/)

JS/Svelte (what the frontend executed):
  show js          Unit + E2E combined (frontend/coverage-js/combined/)
  show js-unit     vitest only (frontend/coverage-js/unit-combined/)
  show js-e2e      Playwright only (frontend/coverage-js/e2e/)

  combine          Combine .coverage.* files without opening browser
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cov_sub = cov_parser.add_subparsers(dest="cov_action", metavar="action")

    show_parser = cov_sub.add_parser("show", help="Open coverage HTML report in browser")
    show_parser.add_argument(
        "target",
        choices=["backend", "frontend", "combined", "js", "js-unit", "js-e2e"],
        help="Which coverage report to show",
    )

    cov_sub.add_parser("combine", help="Combine .coverage.* files into single .coverage")

    return cov_parser


def _build_extra_args(category: str) -> list:
    """Build extra args list for a category."""
    extra_args = []
    extra_args.append(
        (
            "--list",
            {
                "action": "store_true",
                "dest": "list_tests",
                "help": "List available test names without running them",
                "default": False,
            },
        )
    )
    if category == "db":
        extra_args.append(("--force", {"action": "store_true", "help": "[populate only] Recreate from scratch", "default": False}))
        extra_args.append(("--clean", {"action": "store_true", "help": "[populate only] Clean custom-uploads and broker_reports dirs", "default": False}))
        extra_args.append(("--with-static", {"action": "store_true", "dest": "with_static", "help": "[populate only] Upload static resources", "default": False}))
        extra_args.append(("--with-reports", {"action": "store_true", "dest": "with_reports", "help": "[populate only] Upload sample broker report files", "default": False}))
    elif category == "external":
        extra_args.extend(_get_external_extra_args())
    elif category in _FRONTEND_CATEGORIES:
        extra_args.extend(
            [
                ("--ui", {"action": "store_true", "help": "Run with Playwright interactive UI", "default": False}),
                ("--headed", {"action": "store_true", "help": "Run with visible browser window", "default": False}),
                ("--debug", {"action": "store_true", "help": "Run with step-by-step debugging (includes --headed)", "default": False}),
            ]
        )
    return extra_args


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser using TEST_REGISTRY."""
    parser = argparse.ArgumentParser(description="LibreFolio Test Runner - Organized test execution", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=_generate_main_epilog())

    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress detailed test output (default: verbose)", default=False)
    parser.add_argument("--coverage", nargs="?", const="all", choices=["py", "js", "all"], metavar="LANG", help=_COVERAGE_HELP, default=None)
    parser.add_argument("--cov-clean-backend", action="store_true", help="Clean Python coverage from backend tests", default=False)
    # The E2E bucket holds Python coverage collected while Playwright drives the
    # backend. It was called "frontend" before the JS coverage of P7 existed;
    # the old spelling stays as a deprecated alias so scripts keep working.
    parser.add_argument("--cov-clean-backend-e2e", "--cov-clean-frontend", action="store_true", dest="cov_clean_backend_e2e", help="Clean Python coverage collected during E2E runs", default=False)
    parser.add_argument("--cov-clean-js", action="store_true", help="Clean JS/Svelte coverage (raw V8 data and reports)", default=False)
    parser.add_argument("--workers", metavar="N", default="1", help="Parallel workers for isolation-safe units (N or 'auto'; default 1 = serial)")
    parser.add_argument("--fail-fast", dest="fail_fast", action="store_true", help="Stop at the first failing action instead of running everything", default=False)
    parser.add_argument("--no-consolidate", action="store_true", help="Run one invocation per action instead of one per category (backend and frontend)", default=False)
    parser.add_argument("--resume", action="store_true", help="Resume from last failure (skip already-passed tests)", default=False)
    parser.add_argument("--fresh-run", action="store_true", dest="fresh_run", help="Clear test run cache before starting", default=False)
    parser.add_argument("--run-status", action="store_true", dest="run_status", help="Show test run cache status and exit", default=False)
    parser.add_argument("--log-file", dest="log_file", metavar="PATH", help="Tee the full run output (incl. build/pytest/playwright) to this file", default=None)
    parser.add_argument("--log-dir", dest="log_dir", metavar="PATH", help="Write one log file per test unit into this directory (previous logs are archived). Defaults to .testLog; pass an empty string to disable", default=DEFAULT_LOG_DIR)
    parser.add_argument("--no-shared-server", dest="no_shared_server", action="store_true", help="Let each test module start its own backend (slower; escape hatch)", default=False)
    parser.add_argument("--assume-scoped", dest="assume_scoped", action="store_true", help="Experiment: run every server-backed unit in parallel, whatever the catalogue says. The reds are the work list, not a regression", default=False)

    subparsers = parser.add_subparsers(dest="category", help="Test category to run", required=False)

    for category in TEST_REGISTRY.keys():
        create_subparser_from_registry(subparsers, category, _build_extra_args(category))

    # Special "all" category
    all_parser = subparsers.add_parser("all", help="Run ALL tests in optimal order")
    for arg_name, arg_kwargs in _get_external_extra_args():
        all_parser.add_argument(arg_name, **arg_kwargs)

    all_be_parser = subparsers.add_parser("all-backend", help="Run all backend tests")
    for arg_name, arg_kwargs in _get_external_extra_args():
        all_be_parser.add_argument(arg_name, **arg_kwargs)

    subparsers.add_parser("all-frontend", help="Run all frontend tests")

    subparsers.add_parser("check-orphans", help="🔍 Find test files not registered in the test runner")

    register_cov_parser(subparsers)
    _register_coverage_subparser(subparsers)

    return parser


def register_subparser(parent_subparsers):
    """Register test commands as a subparser of dev.py."""
    test_parser = parent_subparsers.add_parser("test", help="Run tests (api, db, external, schemas, services, utils, e2e, front-utility, front-broker, front-user, front-fx, front-transaction, all, all-backend, all-frontend)", description="LibreFolio Test Runner")

    test_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress detailed test output (default: verbose)", default=False)
    test_parser.add_argument("--coverage", nargs="?", const="all", choices=["py", "js", "all"], metavar="LANG", help=_COVERAGE_HELP, default=None)
    test_parser.add_argument("--cov-clean-backend", action="store_true", help="Clean Python coverage from backend tests", default=False)
    test_parser.add_argument("--cov-clean-backend-e2e", "--cov-clean-frontend", action="store_true", dest="cov_clean_backend_e2e", help="Clean Python coverage collected during E2E runs", default=False)
    test_parser.add_argument("--cov-clean-js", action="store_true", help="Clean JS/Svelte coverage (raw V8 data and reports)", default=False)
    test_parser.add_argument("--workers", metavar="N", default="1", help="Parallel workers for isolation-safe units (N or 'auto'; default 1 = serial)")
    test_parser.add_argument("--fail-fast", dest="fail_fast", action="store_true", help="Stop at the first failing action instead of running everything", default=False)
    test_parser.add_argument("--no-consolidate", action="store_true", help="Run one invocation per action instead of one per category (backend and frontend)", default=False)
    test_parser.add_argument("--resume", action="store_true", help="Resume from last failure (skip already-passed tests)", default=False)
    test_parser.add_argument("--fresh-run", action="store_true", dest="fresh_run", help="Clear test run cache before starting", default=False)
    test_parser.add_argument("--run-status", action="store_true", dest="run_status", help="Show test run cache status and exit", default=False)
    test_parser.add_argument("--log-file", dest="log_file", metavar="PATH", help="Tee the full run output (incl. build/pytest/playwright) to this file", default=None)
    test_parser.add_argument("--log-dir", dest="log_dir", metavar="PATH", help="Write one log file per test unit into this directory (previous logs are archived). Defaults to .testLog; pass an empty string to disable", default=DEFAULT_LOG_DIR)
    test_parser.add_argument("--no-shared-server", dest="no_shared_server", action="store_true", help="Let each test module start its own backend (slower; escape hatch)", default=False)
    test_parser.add_argument("--assume-scoped", dest="assume_scoped", action="store_true", help="Experiment: run every server-backed unit in parallel, whatever the catalogue says. The reds are the work list, not a regression", default=False)

    test_subparsers = test_parser.add_subparsers(dest="category", title="Test categories", metavar="")

    for category in TEST_REGISTRY.keys():
        create_subparser_from_registry(test_subparsers, category, _build_extra_args(category))

    all_parser = test_subparsers.add_parser("all", help="Run ALL tests in optimal order")
    for arg_name, arg_kwargs in _get_external_extra_args():
        all_parser.add_argument(arg_name, **arg_kwargs)

    all_be_parser = test_subparsers.add_parser("all-backend", help="Run all backend tests")
    for arg_name, arg_kwargs in _get_external_extra_args():
        all_be_parser.add_argument(arg_name, **arg_kwargs)

    test_subparsers.add_parser("all-frontend", help="Run all frontend tests")

    test_subparsers.add_parser("check-orphans", help="🔍 Find test files not registered in the test runner")

    register_cov_parser(test_subparsers)
    _register_coverage_subparser(test_subparsers)

    test_parser.set_defaults(func=_dispatch_test_command)

    return test_parser


#: Categories whose units talk HTTP to a running backend. They used to start one
#: uvicorn each; now the runner starts a single server around the whole category.
_SERVER_BACKED_CATEGORIES = {"api", "e2e", "all", "all-backend"}


@contextlib.contextmanager
def shared_backend_for(category: str, args):
    """One backend for everything this invocation runs — pre-passes included.

    The context has to open *before* the pre-passes, not just around the serial
    dispatch. The consolidated pass runs the api units itself, and a test module
    that does not see ``LIBREFOLIO_TEST_SHARED_SERVER`` in its environment
    force-kills whatever holds the port and starts its own uvicorn. Measured with
    the context opened too late: the consolidated api pass took 6m09 and started
    47 servers inside one pytest process, silently undoing the whole point of
    sharing one.
    """
    if category not in _SERVER_BACKED_CATEGORIES or getattr(args, "no_shared_server", False):
        yield
        return

    from ._scheduler import resolve_workers
    from ._server import SharedTestServer

    with SharedTestServer(
        coverage=bool(_common._COVERAGE_PY),
        client_workers=resolve_workers(getattr(args, "workers", "1")),
        verbose=False,
    ):
        yield


def _categories_in_scope(args) -> list:
    """The registry categories this invocation will actually run, in suite order."""
    from ._consolidate_backend import CONSOLIDATABLE

    category = args.category
    if category in ("all", "all-backend"):
        return list(CONSOLIDATABLE)
    return [category] if category in TEST_REGISTRY else []


def _run_exclusive_setups(args) -> bool:
    """Run the setups that own the database file, before the server ever starts.

    ``services`` deletes the SQLite file and rebuilds it from the migrations, and
    it is the first category the consolidated pass runs — so doing it here means
    the shared backend is started once, against the database it will actually
    serve, instead of being stopped and restarted five seconds into the run.

    This is an optimisation, not the safety net: ``db_create`` protects itself
    with ``database_file_owned_exclusively()`` wherever it is called from. What
    this adds is the knowledge of *which* setups are destructive, declared next to
    the category instead of discovered at the moment of damage.
    """
    for category in _categories_in_scope(args):
        if not _common.setup_is_exclusive(category):
            continue
        if not _common.run_category_setup(category):
            print_error(f"{category}: setup failed before the shared backend — aborting")
            return False
    return True


def dispatch_to_category(category: str, test_names, verbose: bool, args) -> int:
    """Dispatch to the appropriate test handler. Returns 0 on success, 1 on failure."""
    return _dispatch_to_category_body(category, test_names, verbose, args)


def _dispatch_to_category_body(category: str, test_names, verbose: bool, args) -> int:
    success = False

    if category == "all":
        providers = getattr(args, "providers", None)
        exclude_providers = getattr(args, "exclude_providers", None)
        success = run_all_tests(verbose=verbose, providers=providers, exclude_providers=exclude_providers, resume=_common._RESUME_MODE)
    elif category == "all-backend":
        providers = getattr(args, "providers", None)
        exclude_providers = getattr(args, "exclude_providers", None)
        success = run_all_backend_tests(verbose=verbose, providers=providers, exclude_providers=exclude_providers, resume=_common._RESUME_MODE)
    elif category == "all-frontend":
        success = run_all_frontend_tests(verbose=verbose, resume=_common._RESUME_MODE)
    elif category == "check-orphans":
        return _check_orphan_tests() or _check_unreachable_tests()
    elif category == "coverage-report":
        cov_args = argparse.Namespace(
            input=getattr(args, "input", None),
            lang=getattr(args, "lang", None),
            priority=getattr(args, "priority", None),
            category=getattr(args, "cov_category", None),
            threshold=getattr(args, "threshold", 0.0),
            json=getattr(args, "json_output", False),
            summary=getattr(args, "summary", False),
        )
        return run_coverage_analysis(cov_args)
    elif category == "coverage":
        return _handle_coverage_command(args)
    elif category in TEST_REGISTRY:
        action = getattr(args, "action", None)
        if action:
            kwargs = {}
            kwargs["list_tests"] = getattr(args, "list_tests", False)
            if category == "db":
                kwargs["force"] = getattr(args, "force", False)
                kwargs["clean"] = getattr(args, "clean", False)
                kwargs["with_static"] = getattr(args, "with_static", False)
                kwargs["with_reports"] = getattr(args, "with_reports", False)
            elif category == "external":
                kwargs["providers"] = getattr(args, "providers", None)
                kwargs["exclude_providers"] = getattr(args, "exclude_providers", None)
            elif category in _FRONTEND_CATEGORIES:
                kwargs["ui"] = getattr(args, "ui", False)
                kwargs["headed"] = getattr(args, "headed", False)
                kwargs["debug"] = getattr(args, "debug", False)
                kwargs["coverage"] = getattr(args, "coverage", False) or _common._COVERAGE_MODE

            success = run_test_from_registry(category=category, action=action, verbose=verbose, test_names=test_names, **kwargs)
        else:
            print_error(f"No action specified for category '{category}'")
            return 1
    else:
        print_error(f"Unknown category: {category}")
        return 1

    return 0 if success else 1


def _dispatch_test_command(args):
    """Dispatch test command from dev.py, optionally teeing the full log to a file."""
    log_file = getattr(args, "log_file", None)
    if log_file:
        with _common.tee_output(log_file):
            print_info(f"📝 Full run log → {log_file}")
            _activate_log_dir(args)
            try:
                rc = _dispatch_test_command_body(args)
            finally:
                _snapshot_log_dir_db()
            print_info(f"📝 Full run log saved to {log_file}")
        return rc
    _activate_log_dir(args)
    try:
        return _dispatch_test_command_body(args)
    finally:
        _snapshot_log_dir_db()


_COVERAGE_LANGS = ("py", "js", "all")

_COVERAGE_HELP = "Track code coverage: 'py' (Python), 'js' (JS/Svelte), 'all' (both, default when the value is omitted)"


def normalize_coverage_argv(argv: list, only_command: str | None = None) -> list:
    """Make the optional value of ``--coverage`` unambiguous.

    ``--coverage`` takes an optional language, but argparse's ``nargs='?'`` has
    no lookahead: it swallows whatever token comes next, so the long-standing
    ``./dev.py test --coverage api all`` would be read as language ``api`` on
    suite ``all``. Inserting the default here keeps every existing invocation
    working while still allowing ``--coverage js``.

    ``only_command`` restricts the rewrite to a single sub-command. It matters:
    ``./dev.py server --coverage`` is a plain boolean — a server can only ever
    measure Python — and must not grow a value.
    """
    if only_command is not None:
        command = next((t for t in argv if not t.startswith("-")), None)
        if command != only_command:
            return argv

    out = []
    for i, tok in enumerate(argv):
        out.append(tok)
        if tok == "--coverage":
            nxt = argv[i + 1] if i + 1 < len(argv) else None
            if nxt is None or nxt.startswith("-") or nxt not in _COVERAGE_LANGS:
                out.append("all")
    return out


def _coverage_capabilities(category: str | None) -> set:
    """Languages the given suite is able to measure.

    Only the suites that drive a browser produce JavaScript data: everything
    else runs Python and nothing else, so asking for ``js`` there is a mistake
    worth reporting rather than an empty report worth puzzling over.
    """
    if category and (category.startswith("front-") or category in ("all-frontend", "all")):
        return {"py", "js"}
    return {"py"}


def _apply_coverage_mode(args, coverage, resume, cov_clean_be, cov_clean_fe) -> bool:
    """Resolve the requested coverage languages and prime the runner globals.

    Returns False when the request cannot be honoured (e.g. ``--coverage js``
    on a backend-only suite), in which case the caller must abort.
    """
    _common._COVERAGE_MODE = coverage
    _common._RESUME_MODE = resume
    _common.set_fail_fast(getattr(args, "fail_fast", False))

    # --cov-clean-js is a manual utility: it works without --coverage, because
    # during a JS coverage run the cleanup happens by itself anyway.
    if getattr(args, "cov_clean_js", False):
        _clean_js_coverage_dirs()

    category = args.category
    if category and category.startswith("front-"):
        _common._COVERAGE_SOURCE = "frontend"
    elif category == "all-frontend":
        _common._COVERAGE_SOURCE = "frontend"
    elif category and category not in ("all", "all-backend", "coverage-report", "coverage"):
        _common._COVERAGE_SOURCE = "backend"
    else:
        _common._COVERAGE_SOURCE = None

    if not coverage:
        _common._COVERAGE_PY = False
        _common._COVERAGE_JS = False
        os.environ.pop("COVERAGE_JS", None)
        return True

    mode = coverage if isinstance(coverage, str) else "all"
    wanted = {"py", "js"} if mode == "all" else {mode}
    available = _coverage_capabilities(category)
    unavailable = wanted - available

    # Only an explicit request deserves an error: with 'all' the user asked for
    # "everything measurable here", so silently narrowing is the right answer.
    if unavailable and mode != "all":
        lang = ", ".join(sorted(unavailable))
        print_error(f"--coverage {mode}: the '{category}' suite cannot produce {lang} coverage.")
        print_info("JS/Svelte coverage requires a browser-driven suite: front-*, all-frontend or all.")
        return False

    _common._COVERAGE_PY = "py" in wanted
    _common._COVERAGE_JS = "js" in wanted and "js" in available

    if _common._COVERAGE_JS:
        # vitest is launched from 8 separate call sites; run_command passes
        # env=None for non-pytest commands, so every one of them inherits this.
        os.environ["COVERAGE_JS"] = "1"
    else:
        os.environ.pop("COVERAGE_JS", None)

    langs = []
    if _common._COVERAGE_PY:
        langs.append("Python")
    if _common._COVERAGE_JS:
        langs.append("JS/Svelte")

    print_header("LibreFolio Test Suite - Coverage Mode")
    print(f"{Colors.YELLOW}📊 Tracking coverage for: {' + '.join(langs)}{Colors.NC}")
    print(f"{Colors.BLUE}Coverage will accumulate across all test runs{Colors.NC}")
    if _common._COVERAGE_PY:
        print(f"{Colors.BLUE}Python report: htmlcov/index.html{Colors.NC}")
    if _common._COVERAGE_JS:
        print(f"{Colors.BLUE}JS report:     frontend/coverage-js/combined/index.html{Colors.NC}")
    print()
    _clean_coverage_dirs(cov_clean_be, cov_clean_fe)
    if _common._COVERAGE_JS:
        # JS coverage is raw V8 data whose byte offsets only mean anything for
        # the bundle that produced them, so it can never survive a rebuild:
        # cleaning it every run is the only safe policy, not an oversight.
        _clean_js_coverage_dirs()
    return True


def _parallel_classes(args, scope: str = None) -> tuple:
    """Which isolation classes the parallel pass may run for this invocation.

    PURE always: those units open no database and reach no server. READ and
    WRITE_SCOPED only when this invocation names **one backend category**, for a
    single reason: the database must already be in the shape that category's
    setup guarantees.

    Under ``all-backend`` it is not. The suite deliberately oscillates the file
    (``db`` populates → ``services`` empties → ``api`` repopulates), and each
    category's setup restores its own precondition just before it runs. A
    parallel pass that ran ``api`` units up front would meet the empty database
    ``services`` left behind. So the pre-pass runs the category's own setup
    first, which is only meaningful when there is exactly one category to set up.

    Server-backed categories additionally need the shared backend, but that is
    already guaranteed: ``shared_backend_for()`` opens before the pre-passes.

    Widening this to whole-suite scope means interleaving the parallel pass with
    the consolidated one, category by category, instead of hoisting it in front.
    """
    from ._inventory import PURE, READ, WRITE_SCOPED

    scope = scope or args.category
    backend = scope in TEST_REGISTRY and not scope.startswith("front")
    if backend and not getattr(args, "no_shared_server", False):
        return (PURE, READ, WRITE_SCOPED)
    return (PURE,)


def _run_parallel_prepass(args, workers: int, verbose: bool) -> tuple:
    """Run the isolation-safe units concurrently before the serial pass.

    Returns ``(ok, covered_actions)``. When nothing qualifies — a frontend
    category, or ``--workers 1`` — this is a no-op and the run takes exactly
    the path it takes today.
    """
    category = args.category
    if category in TEST_REGISTRY:
        # A single registry category: parallelise it only if it is a backend one.
        if category.startswith("front"):
            return True, set()
        return _parallel_for_scope(args, category, workers, verbose)
    if category in ("all", "all-backend"):
        # One scope per category, in suite order, each preceded by its own setup.
        # A single scope=None pass cannot work above PURE: the suite oscillates
        # the database on purpose (`db` populates → `services` empties → `api`
        # repopulates), so there is no one moment at which every category's
        # precondition holds. Walking the categories restores each in turn, which
        # is the same thing the consolidated pass does — and because
        # `run_category_setup` is once-per-invocation, it is not done twice.
        from ._consolidate_backend import CONSOLIDATABLE

        ok, covered = True, set()
        for cat in CONSOLIDATABLE:
            cat_ok, cat_covered = _parallel_for_scope(args, cat, workers, verbose)
            ok = ok and cat_ok
            covered |= cat_covered
            if not cat_ok and getattr(args, "fail_fast", False):
                break
        return ok, covered
    # all-frontend, coverage-report, check-orphans and friends: nothing here
    # is a pytest unit, and scope=None would wrongly sweep in the backend.
    return True, set()


def _parallel_for_scope(args, scope: str, workers: int, verbose: bool) -> tuple:
    """The parallel pass for one category. Returns ``(ok, covered_actions)``."""
    from ._executor import combine_coverage, read_failed_units, read_unit_durations, run_groups
    from ._scheduler import load_durations, plan, save_durations

    classes = _parallel_classes(args, scope)
    assume = bool(getattr(args, "assume_scoped", False)) and len(classes) > 1
    p = plan(scope, workers, classes=classes, assume_scoped=assume)
    if p["errors"]:
        print_warning(f"⚠️  Inventory incomplete, running serially: {sorted(p['errors'])}")
        return True, set()
    if len(p["groups"]) <= 1 or not p["parallel_paths"]:
        return True, set()

    if len(classes) > 1:  # noqa: SIM102 — server-backed scope needs its precondition
        # Server-backed units are about to run before the category's serial pass,
        # so nobody has yet guaranteed their precondition. Do it here — it is the
        # same setup the consolidated pass would run, and `run_category_setup`
        # is once-per-invocation, so this does not double it.
        from ._common import run_category_setup

        if not run_category_setup(scope):
            print_error(f"Setup for '{scope}' failed — skipping the parallel pass")
            return True, set()

    print_header(f"Parallel pass — {len(p['parallel_paths'])} isolation-safe unit(s) across {len(p['groups'])} worker(s)")
    outcome = run_groups(p["groups"], verbose=verbose, coverage=_common._COVERAGE_PY)

    if _common._COVERAGE_PY:
        combine_coverage(_common._COVERAGE_SOURCE or "backend")

    # Record what each unit cost so the next plan balances on measurement rather
    # than on a guess. The junit reports give exact per-unit times; a group's
    # wall time shared evenly would erase the very differences LPT needs.
    measured = read_unit_durations(set(p["parallel_paths"]))
    if measured:
        durations = load_durations()
        durations.update(measured)
        save_durations(durations)

    # Name the units that failed, so the serial pass — which skips them as
    # "already covered" — can still turn their category red. Without this the
    # summary prints ALL TESTS PASSED over a run whose exit code says otherwise.
    if not outcome["ok"]:
        failed_paths = read_failed_units(set(p["parallel_paths"]))
        by_action = p.get("by_action") or {}
        blamed = {key for key, paths in by_action.items() if key in p["covered_actions"] and any(path in failed_paths for path in paths)}
        if blamed:
            _common._FAILED_ACTIONS |= blamed
        else:
            # A worker died without leaving a junit report, so no unit can be
            # blamed individually. Fail every action it covered rather than none.
            _common._FAILED_ACTIONS |= set(p["covered_actions"])

    return outcome["ok"], p["covered_actions"]


def _backend_consolidation_scope(args) -> tuple:
    """Decide whether this invocation may consolidate backend units.

    Same rule as the frontend: consolidation applies when the user asked for a
    whole category or a whole suite. Naming a single action, or filtering by test
    name, keeps the 1:1 shape — `./dev.py test api auth` must stay one file.
    """
    if getattr(args, "no_consolidate", False):
        return False, None
    if getattr(args, "test_names", None):
        return False, None

    category = args.category
    action = getattr(args, "action", None)
    if category in TEST_REGISTRY and not category.startswith("front"):
        return (action in (None, "all")), category
    if category in ("all", "all-backend"):
        return True, None
    return False, None


def _run_backend_consolidation_prepass(args, verbose: bool, skip: set) -> tuple:
    """Run each backend category's units in one invocation instead of one each."""
    from ._consolidate_backend import run_backend_consolidated

    enabled, scope = _backend_consolidation_scope(args)
    if not enabled:
        return True, set()

    print_header("Consolidated backend pass — one invocation per category")
    ok, covered, outcome = run_backend_consolidated(
        scope,
        coverage=bool(_common._COVERAGE_PY),
        resume=bool(getattr(args, "resume", False)),
        verbose=verbose,
        skip=skip,
    )
    _common._FAILED_ACTIONS |= {unit for unit, passed in outcome.items() if not passed}
    return ok, covered


def _frontend_consolidation_scope(args) -> tuple:
    """Decide whether this invocation may consolidate frontend units.

    Returns ``(enabled, scope)``. Consolidation only applies when the user asked
    for a whole category or a whole frontend suite: a single named action still
    means a single invocation, so `./dev.py test front-fx fx-list` is untouched.
    """
    if getattr(args, "no_consolidate", False):
        return False, None
    # Naming one test by name, or driving the UI, must keep the 1:1 shape.
    if getattr(args, "test_names", None) or getattr(args, "ui", False) or getattr(args, "headed", False) or getattr(args, "debug", False):
        return False, None

    category = args.category
    action = getattr(args, "action", None)
    if category in TEST_REGISTRY and category.startswith("front"):
        return (action in (None, "all")), category
    if category in ("all", "all-frontend"):
        return True, None
    return False, None


def _run_consolidation_prepass(args, verbose: bool) -> tuple:
    """Run each frontend category in one invocation instead of one per action."""
    from ._consolidate import run_consolidated
    from . import _frontend_common

    enabled, scope = _frontend_consolidation_scope(args)
    if not enabled:
        return True, set()

    _frontend_common.reset_setup_scope()
    print_header("Consolidated frontend pass — one invocation per category")
    ok, covered, outcome = run_consolidated(
        scope,
        coverage=bool(getattr(args, "coverage", None)),
        resume=bool(getattr(args, "resume", False)),
    )
    _common._FAILED_ACTIONS |= {unit for unit, passed in outcome.items() if not passed}
    return ok, covered


def _run_passes(args, test_names, verbose: bool) -> tuple:
    """Run the pre-passes and the serial dispatch under one shared backend.

    Returns ``(result, parallel_ok, go_on)``. Both entry points go through here
    so the order — backend up, then pre-passes, then serial — cannot drift apart
    between them.
    """
    try:
        if not _run_exclusive_setups(args):
            return 1, False, False
        with shared_backend_for(args.category, args):
            parallel_ok, go_on = _apply_parallel(args, verbose)
            if not go_on:
                return 1, parallel_ok, False
            return dispatch_to_category(args.category, test_names, verbose, args), parallel_ok, True
    except RuntimeError as exc:
        print_error(str(exc))
        return 1, False, False


def _apply_parallel(args, verbose: bool) -> tuple:
    """Run the pre-passes if requested. Returns ``(ok, continue_serial)``."""
    from ._scheduler import resolve_workers

    covered: set = set()
    ok = True

    workers = resolve_workers(getattr(args, "workers", "1"))
    # `--workers` is one flag: it must mean the same thing to pytest and to
    # Playwright. The browser half reads it from here, not from the ambient
    # environment.
    _common._E2E_WORKERS = workers
    if workers > 1:
        ok, parallel_covered = _run_parallel_prepass(args, workers, verbose)
        covered |= parallel_covered
        if not ok and getattr(args, "fail_fast", False):
            # Fail-fast means "hand out no more work", not "abandon what ran": the
            # workers already running all finished and reported before we got here.
            _common._SKIP_ACTIONS = covered
            print_error("Parallel pass failed — stopping before the serial pass (--fail-fast)")
            return False, False

    # After the parallel pass, so the units it already ran are not run twice.
    back_ok, back_covered = _run_backend_consolidation_prepass(args, verbose, covered)
    covered |= back_covered
    ok = ok and back_ok
    if not ok and getattr(args, "fail_fast", False):
        _common._SKIP_ACTIONS = covered
        print_error("Consolidated backend pass failed — stopping before the serial pass (--fail-fast)")
        return False, False

    front_ok, front_covered = _run_consolidation_prepass(args, verbose)
    covered |= front_covered
    ok = ok and front_ok

    _common._SKIP_ACTIONS = covered
    if not ok and getattr(args, "fail_fast", False):
        print_error("A pre-pass failed — stopping before the serial pass (--fail-fast)")
        return False, False
    return ok, True


def _dispatch_test_command_body(args):
    if not args.category:
        # Handle --run-status without category
        if getattr(args, "run_status", False):
            print(_cache_show_status())
            return 0
        # Handle --fresh-run without category
        if getattr(args, "fresh_run", False):
            _cache_clear_all()
            print_info("🧹 Test run cache cleared. Starting fresh.")
            return 0
        print("Error: test category required. Use: ./dev.py test --help")
        return 1

    verbose = not getattr(args, "quiet", False)
    test_names = getattr(args, "test_names", None)
    coverage = getattr(args, "coverage", None)
    cov_clean_be = getattr(args, "cov_clean_backend", False)
    cov_clean_fe = getattr(args, "cov_clean_backend_e2e", False)
    resume = getattr(args, "resume", False)
    fresh_run = getattr(args, "fresh_run", False)
    run_status = getattr(args, "run_status", False)

    # Handle --run-status (show and exit)
    if run_status:
        print(_cache_show_status())
        return 0

    # Handle --fresh-run (clear cache before proceeding)
    if fresh_run:
        _cache_clear_all()
        print_info("🧹 Test run cache cleared. Starting fresh.")

    if not _apply_coverage_mode(args, coverage, resume, cov_clean_be, cov_clean_fe):
        return 1

    result, parallel_ok, go_on = _run_passes(args, test_names, verbose)
    if not go_on:
        return 1

    success = result == 0 and parallel_ok
    _common._SKIP_ACTIONS = set()
    _common._FAILED_ACTIONS = set()

    if _common._COVERAGE_MODE:
        print()
        print_header("Coverage Report Summary")
        if success:
            print_success("✅ All tests passed with coverage tracking!")
        else:
            print_warning("⚠️  Some tests failed, but coverage was still tracked")

        is_front = _common._COVERAGE_SOURCE == "frontend"
        is_all = _common._COVERAGE_SOURCE is None

        print()
        print(f"{Colors.GREEN}📊 Generating final coverage report...{Colors.NC}")
        print()
        if _common._COVERAGE_PY:
            _finalize_coverage(is_front, is_all)
        if _common._COVERAGE_JS:
            _finalize_js_coverage()

    return 0 if success else 1


def main():
    """Main entry point, optionally teeing the full log to a file."""
    parser = create_parser()

    argcomplete.autocomplete(parser)
    args = parser.parse_args(normalize_coverage_argv(sys.argv[1:]))

    log_file = getattr(args, "log_file", None)
    if log_file:
        with _common.tee_output(log_file):
            print_info(f"📝 Full run log → {log_file}")
            _activate_log_dir(args)
            rc = _main_body(parser, args)
            _snapshot_log_dir_db()
            print_info(f"📝 Full run log saved to {log_file}")
        return rc
    _activate_log_dir(args)
    try:
        return _main_body(parser, args)
    finally:
        _snapshot_log_dir_db()


def _snapshot_log_dir_db() -> None:
    """Freeze the test DB next to the logs, once the run is over."""
    log_dir = _common.get_log_dir()
    if not log_dir:
        return
    from ._archive import snapshot_test_db

    dest = snapshot_test_db(log_dir)
    if dest:
        print_info(f"🗄️  Test DB snapshot → {dest.parent.name}/{dest.name}")


def _activate_log_dir(args) -> None:
    """Prepare the per-unit log directory, archiving whatever a previous run left."""
    log_dir = getattr(args, "log_dir", None)
    if not log_dir:
        return
    from ._archive import prepare_log_dir

    try:
        prepared = prepare_log_dir(log_dir)
    except Exception as exc:  # never let logging break a run
        print_warning(f"Could not prepare --log-dir {log_dir}: {exc}")
        return
    _common.set_log_dir(prepared, getattr(args, "category", None) or "run")
    print_info(f"📂 Per-unit logs → {prepared}")


def _main_body(parser, args):
    """Actual main logic (wrapped by main() for optional log teeing)."""
    # Handle --run-status without category
    if getattr(args, "run_status", False):
        print(_cache_show_status())
        return 0

    # Handle --fresh-run without category
    if getattr(args, "fresh_run", False) and not args.category:
        _cache_clear_all()
        print_info("🧹 Test run cache cleared. Starting fresh.")
        return 0

    if not args.category:
        parser.print_help()
        return 1

    verbose = not getattr(args, "quiet", False)
    test_names = getattr(args, "test_names", None)
    coverage = getattr(args, "coverage", None)
    cov_clean_be = getattr(args, "cov_clean_backend", False)
    cov_clean_fe = getattr(args, "cov_clean_backend_e2e", False)
    resume = getattr(args, "resume", False)
    fresh_run = getattr(args, "fresh_run", False)

    # Handle --fresh-run with category (clear then run)
    if fresh_run:
        _cache_clear_all()
        print_info("🧹 Test run cache cleared. Starting fresh.")

    if not _apply_coverage_mode(args, coverage, resume, cov_clean_be, cov_clean_fe):
        return 1

    result, parallel_ok, go_on = _run_passes(args, test_names, verbose)
    if not go_on:
        return 1

    success = result == 0 and parallel_ok
    _common._SKIP_ACTIONS = set()
    _common._FAILED_ACTIONS = set()

    if _common._COVERAGE_MODE:
        print()
        print_header("Coverage Report Summary")
        if success:
            print_success("✅ All tests passed with coverage tracking!")
        else:
            print_warning("⚠️  Some tests failed, but coverage was still tracked")

        is_front = _common._COVERAGE_SOURCE == "frontend"
        is_all = _common._COVERAGE_SOURCE is None

        print()
        print(f"{Colors.GREEN}📊 Generating final coverage report...{Colors.NC}")
        print()
        if _common._COVERAGE_PY:
            _finalize_coverage(is_front, is_all)
        if _common._COVERAGE_JS:
            _finalize_js_coverage()

    return 0 if success else 1
