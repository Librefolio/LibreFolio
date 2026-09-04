"""Frontend user E2E tests: multi-user isolation, broker sharing."""

import subprocess

from . import _common
from ._common import Colors, _get_category_tests_for_all, _run_test_suite, print_error, print_header, print_section, print_success
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright, reset_setup_scope


def front_user_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run user/session store unit tests (Vitest)."""
    print(f"\n{Colors.BLUE}Running: User store Vitest unit tests{Colors.NC}")
    result = subprocess.run(
        ["npx", "vitest", "run", "src/lib/stores/app/auth.test.ts", "src/lib/stores/app/clientSession.test.ts"],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("User store Vitest unit tests - PASSED")
        return True

    print_error(f"User store Vitest unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_multi_user(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run multi-user isolation tests."""
    print_section("Frontend Multi-User Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("brokers/multi-user.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_broker_sharing(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run broker sharing E2E tests."""
    print_section("Frontend Broker Sharing Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("brokers/broker-sharing.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_user_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, coverage: bool = False) -> bool:
    """Run all frontend user E2E tests (multi-user, sharing)."""
    print_header("Frontend User Tests (Playwright)")
    if _common.nothing_left_to_run("front-user"):
        return _common.consolidated_verdict("front-user")
    reset_setup_scope()
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_test_suite(
        suite_name="Frontend User Tests",
        tests=_get_category_tests_for_all("front-user", verbose, ui=ui, headed=headed, debug=debug, coverage=coverage),
        verbose=verbose,
        header_msg=None,
        summary_title="Frontend User Test Summary",
        success_msg="All frontend user tests passed! 🎉",
        resume=_common._RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all frontend user test entries."""
    from ._common import add_test, make_category
    cat = make_category(
        help_text="Frontend user E2E tests (multi-user isolation, broker sharing)",
        description="""Frontend User Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "multi-user", front_multi_user, name="Multi-User Tests", desc="Data isolation between users", prereq="Multiple test users", tests="brokers/multi-user.spec.ts")
    add_test(cat, "user-unit", front_user_unit, test_names=False, name="User Store Unit Tests", desc="auth + clientSession vitest units", tests="src/lib/stores/app/auth.test.ts")
    add_test(cat, "broker-sharing", front_broker_sharing, name="Broker Sharing Tests", desc="BrokerSharingModal, ownership chart", prereq="Login working, brokers exist", tests="brokers/broker-sharing.spec.ts")
    add_test(cat, "all", front_user_all, test_names=False, name="All User Tests", desc="Run all user E2E tests")
    registry["front-user"] = cat
