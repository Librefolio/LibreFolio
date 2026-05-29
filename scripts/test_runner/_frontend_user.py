"""Frontend user E2E tests: multi-user isolation, broker sharing."""

from ._common import _RESUME_MODE, _run_test_suite, print_header, print_section
from ._frontend_common import _ensure_frontend_build, _ensure_db_populated, _ensure_test_users, _run_playwright


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
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    specs = ["brokers/multi-user.spec.ts", "brokers/broker-sharing.spec.ts"]
    return _run_test_suite(
        suite_name="Frontend User Tests",
        tests=[(spec.replace('.spec.ts', '').title(), lambda s=spec: _run_playwright(s, ui=ui, headed=headed, debug=debug, coverage=coverage)) for spec in specs],
        verbose=verbose,
        header_msg=None,
        summary_title="Frontend User Test Summary",
        success_msg="All frontend user tests passed! 🎉",
        resume=_RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all frontend user test entries."""
    from ._common import make_category, add_test
    cat = make_category(
        help_text="Frontend user E2E tests (multi-user isolation, broker sharing)",
        description="""Frontend User Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "multi-user", front_multi_user, name="Multi-User Tests", desc="Data isolation between users", prereq="Multiple test users", tests="brokers/multi-user.spec.ts")
    add_test(cat, "broker-sharing", front_broker_sharing, name="Broker Sharing Tests", desc="BrokerSharingModal, ownership chart", prereq="Login working, brokers exist", tests="brokers/broker-sharing.spec.ts")
    add_test(cat, "all", front_user_all, test_names=False, name="All User Tests", desc="Run all user E2E tests")
    registry["front-user"] = cat
