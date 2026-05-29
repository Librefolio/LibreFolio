"""
Common utilities shared across all test_runner submodules.

Contains: globals, _run_test_suite, run_command, _build_pytest_cmd, helpers.
"""

import inspect
import os
import shutil
import subprocess
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

# Global flag for coverage mode (set by main())
_COVERAGE_MODE = False
# Coverage source: "backend", "frontend", or None (auto-detect)
_COVERAGE_SOURCE = None
# Global flag for resume mode (set by main())
_RESUME_MODE = False


def _run_test_suite(
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
    if combine_coverage and _COVERAGE_MODE:
        print_section("Combining Coverage Data")
        print_info("Merging coverage from test server subprocess...")
        try:
            result = subprocess.run(["coverage", "combine", "--keep"], capture_output=True, text=True, cwd=Path(__file__).parent)
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


def _get_category_tests_for_all(category: str, verbose: bool) -> list:
    """
    Generate list of (name, lambda) tuples for a category's all test.

    Automatically excludes the 'all' action itself and uses registry
    as single source of truth.

    NOTE: Uses lazy import of TEST_REGISTRY to avoid circular imports.
    """
    from ._registry import TEST_REGISTRY

    if category not in TEST_REGISTRY:
        return []

    tests = []
    for action, info in TEST_REGISTRY[category].items():
        if action == "_meta" or action == "all":
            continue
        func = info["func"]
        name = info.get("name", action)
        tests.append((name, lambda f=func, v=verbose: f(verbose=v)))
    return tests


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

    Args:
        cmd: Command parts to run
        description: Human-readable description for output
        verbose: If True, stream stdout/stderr live
        timeout: Max seconds per command (default 300s). Use 600 for E2E/frontend.

    If _COVERAGE_MODE is True and the command is a pytest test, automatically
    adds coverage tracking flags and updates the cumulative coverage database.
    """
    # Check if this is a pytest command and coverage is enabled
    is_pytest = "pytest" in " ".join(cmd)
    use_coverage = _COVERAGE_MODE and is_pytest

    # If coverage mode, enhance pytest command
    if is_pytest:
        pytest_idx = next((i for i, c in enumerate(cmd) if "pytest" in c), None)
        if pytest_idx is not None:
            flags_to_add = []
            if verbose:
                flags_to_add.append("-s")
            if use_coverage:
                html_dir = "htmlcov-backend" if _COVERAGE_SOURCE != "frontend" else "htmlcov-frontend"
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


def make_category(help_text: str, description: str) -> dict:
    """Create the _meta entry for a registry category."""
    return {"_meta": {"help": help_text, "description": description}}


def add_test(category: dict, action: str, func, *, test_names: bool = True, name: str, desc: str, prereq: str = None, tests: str = None, note: str = None) -> None:
    """Add a single test entry to a category dict."""
    entry = {"func": func, "test_names": test_names, "name": name, "desc": desc}
    if prereq:
        entry["prereq"] = prereq
    if tests:
        entry["tests"] = tests
    if note:
        entry["note"] = note
    category[action] = entry
