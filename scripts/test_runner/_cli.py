"""
CLI: argument parsers, dispatch, main entry point.
"""

import argparse
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
    parser.add_argument("--cov-clean-backend", action="store_true", help="Clean backend coverage data", default=False)
    parser.add_argument("--cov-clean-frontend", action="store_true", help="Clean frontend coverage data", default=False)
    parser.add_argument("--resume", action="store_true", help="Resume from last failure (skip already-passed tests)", default=False)
    parser.add_argument("--fresh-run", action="store_true", dest="fresh_run", help="Clear test run cache before starting", default=False)
    parser.add_argument("--run-status", action="store_true", dest="run_status", help="Show test run cache status and exit", default=False)
    parser.add_argument("--log-file", dest="log_file", metavar="PATH", help="Tee the full run output (incl. build/pytest/playwright) to this file", default=None)

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
    test_parser.add_argument("--cov-clean-backend", action="store_true", help="Clean backend coverage data", default=False)
    test_parser.add_argument("--cov-clean-frontend", action="store_true", help="Clean frontend coverage data", default=False)
    test_parser.add_argument("--resume", action="store_true", help="Resume from last failure (skip already-passed tests)", default=False)
    test_parser.add_argument("--fresh-run", action="store_true", dest="fresh_run", help="Clear test run cache before starting", default=False)
    test_parser.add_argument("--run-status", action="store_true", dest="run_status", help="Show test run cache status and exit", default=False)
    test_parser.add_argument("--log-file", dest="log_file", metavar="PATH", help="Tee the full run output (incl. build/pytest/playwright) to this file", default=None)

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
            rc = _dispatch_test_command_body(args)
            print_info(f"📝 Full run log saved to {log_file}")
        return rc
    return _dispatch_test_command_body(args)


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
        _clean_js_coverage_dirs()
    return True


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

    if not _apply_coverage_mode(args, coverage, resume, cov_clean_be, cov_clean_fe):
        return 1

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
            rc = _main_body(parser, args)
            print_info(f"📝 Full run log saved to {log_file}")
        return rc
    return _main_body(parser, args)


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
    cov_clean_fe = getattr(args, "cov_clean_frontend", False)
    resume = getattr(args, "resume", False)
    fresh_run = getattr(args, "fresh_run", False)

    # Handle --fresh-run with category (clear then run)
    if fresh_run:
        _cache_clear_all()
        print_info("🧹 Test run cache cleared. Starting fresh.")

    if not _apply_coverage_mode(args, coverage, resume, cov_clean_be, cov_clean_fe):
        return 1

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
        if _common._COVERAGE_PY:
            _finalize_coverage(is_front, is_all)
        if _common._COVERAGE_JS:
            _finalize_js_coverage()

    return 0 if success else 1
