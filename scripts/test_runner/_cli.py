"""
CLI: argument parsers, dispatch, main entry point.
"""

import argparse
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
from ._coverage import _finalize_coverage, _handle_coverage_command
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


def _check_orphan_tests() -> int:
    """Find test files not registered in the test runner.

    Checks:
    - Backend: test_*.py files in each test directory vs registered in _backend_*.py
    - Frontend: *.spec.ts files in e2e/ vs referenced in _frontend_*.py

    Returns 0 if no orphans, 1 if orphans found.
    """

    project_root = Path(__file__).parent.parent.parent
    runner_dir = Path(__file__).parent
    orphans_found = False

    print(f"\n{Colors.CYAN}🔍 Checking for orphan test files...{Colors.NC}\n")

    # ── Backend: scan each test directory ──
    backend_dirs = {
        "test_api": "_backend_api.py",
        "test_services": "_backend_services.py",
        "test_e2e": "_backend_api.py",  # e2e is in _backend_api
        "test_schemas": "_backend_schemas.py",
        "test_utilities": "_backend_utils.py",
        "test_external": "_backend_external.py",
        "test_db": "_backend_db.py",
    }

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

    # ── Summary ──
    print()
    if orphans_found:
        print(f"  {Colors.YELLOW}⚠️  Orphan files found! Add them to the appropriate _backend_*.py or _frontend_*.py module.{Colors.NC}")
        return 1
    else:
        print(f"  {Colors.GREEN}✅ All test files are registered in the test runner.{Colors.NC}")
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
    lines.append("  dev.py test -v all              # All tests with verbose output")
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
  show backend     Open backend test coverage (htmlcov-backend/)
  show frontend    Open frontend E2E → backend coverage (htmlcov-frontend/)
  show combined    Combine all data + open merged report (htmlcov/)
  combine          Combine .coverage.* files without opening browser
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cov_sub = cov_parser.add_subparsers(dest="cov_action", metavar="action")

    show_parser = cov_sub.add_parser("show", help="Open coverage HTML report in browser")
    show_parser.add_argument(
        "target",
        choices=["backend", "frontend", "combined"],
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

    parser.add_argument("-v", "--verbose", action="store_true", help="Show full test output", default=False)
    parser.add_argument("--coverage", action="store_true", help="Run tests with code coverage tracking", default=False)
    parser.add_argument("--cov-clean-backend", action="store_true", help="Clean backend coverage data", default=False)
    parser.add_argument("--cov-clean-frontend", action="store_true", help="Clean frontend coverage data", default=False)
    parser.add_argument("--resume", action="store_true", help="Resume from last failure (skip already-passed tests)", default=False)
    parser.add_argument("--fresh-run", action="store_true", dest="fresh_run", help="Clear test run cache before starting", default=False)
    parser.add_argument("--run-status", action="store_true", dest="run_status", help="Show test run cache status and exit", default=False)

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

    test_parser.add_argument("-v", "--verbose", action="store_true", help="Show full test output", default=False)
    test_parser.add_argument("--coverage", action="store_true", help="Run tests with code coverage tracking", default=False)
    test_parser.add_argument("--cov-clean-backend", action="store_true", help="Clean backend coverage data", default=False)
    test_parser.add_argument("--cov-clean-frontend", action="store_true", help="Clean frontend coverage data", default=False)
    test_parser.add_argument("--resume", action="store_true", help="Resume from last failure (skip already-passed tests)", default=False)
    test_parser.add_argument("--fresh-run", action="store_true", dest="fresh_run", help="Clear test run cache before starting", default=False)
    test_parser.add_argument("--run-status", action="store_true", dest="run_status", help="Show test run cache status and exit", default=False)

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


def dispatch_to_category(category: str, test_names, verbose: bool, args) -> int:
    """Dispatch to the appropriate test handler. Returns 0 on success, 1 on failure."""
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
        return _check_orphan_tests()
    elif category == "coverage-report":
        cov_args = argparse.Namespace(
            input=getattr(args, "input", "/tmp/cov_report.json"),
            priority=getattr(args, "priority", None),
            category=getattr(args, "category", None),
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
    """Dispatch test command from dev.py."""
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

    verbose = getattr(args, "verbose", False)
    test_names = getattr(args, "test_names", None)
    coverage = getattr(args, "coverage", False)
    cov_clean_be = getattr(args, "cov_clean_backend", False)
    cov_clean_fe = getattr(args, "cov_clean_frontend", False)
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

    _common._COVERAGE_MODE = coverage
    _common._RESUME_MODE = resume
    if args.category and args.category.startswith("front-"):
        _common._COVERAGE_SOURCE = "frontend"
    elif args.category == "all-frontend":
        _common._COVERAGE_SOURCE = "frontend"
    elif args.category and args.category not in ("all", "all-backend", "coverage-report", "coverage"):
        _common._COVERAGE_SOURCE = "backend"
    else:
        _common._COVERAGE_SOURCE = None

    if coverage:
        print_header("LibreFolio Test Suite - Coverage Mode")
        print(f"{Colors.YELLOW}📊 Running tests with code coverage tracking{Colors.NC}")
        print(f"{Colors.BLUE}Coverage will accumulate across all test runs{Colors.NC}")
        print(f"{Colors.BLUE}Final report: htmlcov/index.html{Colors.NC}")
        print()
        _clean_coverage_dirs(cov_clean_be, cov_clean_fe)

    result = dispatch_to_category(args.category, test_names, verbose, args)
    success = result == 0

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
        _finalize_coverage(is_front, is_all)

    return 0 if success else 1


def main():
    """Main entry point."""
    parser = create_parser()

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

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

    verbose = getattr(args, "verbose", False)
    test_names = getattr(args, "test_names", None)
    coverage = getattr(args, "coverage", False)
    cov_clean_be = getattr(args, "cov_clean_backend", False)
    cov_clean_fe = getattr(args, "cov_clean_frontend", False)
    resume = getattr(args, "resume", False)
    fresh_run = getattr(args, "fresh_run", False)

    # Handle --fresh-run with category (clear then run)
    if fresh_run:
        _cache_clear_all()
        print_info("🧹 Test run cache cleared. Starting fresh.")

    _common._COVERAGE_MODE = coverage
    _common._RESUME_MODE = resume
    if args.category and args.category.startswith("front-"):
        _common._COVERAGE_SOURCE = "frontend"
    elif args.category == "all-frontend":
        _common._COVERAGE_SOURCE = "frontend"
    elif args.category and args.category not in ("all", "all-backend", "coverage-report", "coverage"):
        _common._COVERAGE_SOURCE = "backend"
    else:
        _common._COVERAGE_SOURCE = None

    if coverage:
        print_header("LibreFolio Test Suite - Coverage Mode")
        print(f"{Colors.YELLOW}📊 Running tests with code coverage tracking{Colors.NC}")
        print(f"{Colors.BLUE}Coverage will accumulate across all test runs{Colors.NC}")
        print(f"{Colors.BLUE}Final report: htmlcov/index.html{Colors.NC}")
        print()
        _clean_coverage_dirs(cov_clean_be, cov_clean_fe)

    result = dispatch_to_category(args.category, test_names, verbose, args)
    success = result == 0

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
        _finalize_coverage(is_front, is_all)

    return 0 if success else 1
