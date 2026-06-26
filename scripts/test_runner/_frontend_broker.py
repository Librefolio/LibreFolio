"""Frontend broker E2E tests: broker list/CRUD + broker detail page."""

import subprocess

from ._common import _RESUME_MODE, PROJECT_ROOT, Colors, _run_test_suite, print_error, print_header, print_section, print_success
from ._frontend_common import _ensure_frontend_build, _ensure_test_users, _run_playwright


def front_broker_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Broker unit tests (Vitest) — brokerHelpers (getBrokerIconUrl fallback chain)."""
    print_section("Frontend Broker Unit Tests (Vitest)")
    cmd = ["npx", "vitest", "run", "src/lib/utils/__tests__/brokerHelpers.test.ts"]
    print(f"\n{Colors.BLUE}Running: Broker Vitest unit tests{Colors.NC}")
    print(f"Command:\n└─▶ $ cd frontend && {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", text=True)
        if result.returncode == 0:
            print_success("Broker Vitest unit tests - PASSED")
            return True
        else:
            print_error(f"Broker Vitest unit tests - FAILED (exit code: {result.returncode})")
            return False
    except Exception as e:
        print_error(f"Vitest error: {e}")
        return False


def front_broker_list(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run broker list & CRUD E2E tests."""
    print_section("Frontend Broker List & CRUD Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("brokers/brokers.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_broker_detail(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run broker detail page E2E tests."""
    print_section("Frontend Broker Detail Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("brokers/brokers-detail.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_broker_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, coverage: bool = False) -> bool:
    """Run all frontend broker tests (unit + E2E)."""
    print_header("Frontend Broker Tests (Unit + Playwright)")
    return _run_test_suite(
        suite_name="All Broker Tests (Unit + E2E)",
        tests=[
            ("Broker Unit (Vitest)", lambda: front_broker_unit(verbose=verbose)),
            ("Broker List & CRUD", lambda: _run_playwright("brokers/brokers.spec.ts", ui=ui, headed=headed, debug=debug, coverage=coverage) if _ensure_frontend_build() and _ensure_test_users() else False),
            ("Broker Detail", lambda: _run_playwright("brokers/brokers-detail.spec.ts", ui=ui, headed=headed, debug=debug, coverage=coverage) if _ensure_frontend_build() and _ensure_test_users() else False),
        ],
        verbose=verbose,
        header_msg=None,
        summary_title="Broker Test Summary",
        success_msg="All Broker tests passed! 🎉",
        resume=_RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all frontend broker test entries."""
    from ._common import make_category, add_test
    cat = make_category(
        help_text="Frontend broker tests: unit (brokerHelpers) + E2E (list, CRUD, detail page)",
        description="""Frontend Broker Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "broker-unit", front_broker_unit, test_names=False, name="Broker Unit Tests (Vitest)", desc="Unit tests: getBrokerIconUrl fallback chain", tests="vitest")
    add_test(cat, "list", front_broker_list, name="Broker List & CRUD Tests", desc="Broker list page, create/edit/delete", prereq="Login working", tests="brokers/brokers.spec.ts")
    add_test(cat, "detail", front_broker_detail, name="Broker Detail Tests", desc="Detail page sections, edit/import modals", prereq="Login working, brokers exist", tests="brokers/brokers-detail.spec.ts")
    add_test(cat, "all", front_broker_all, test_names=False, name="All Broker Tests", desc="Run all broker tests (unit + E2E)")
    registry["front-broker"] = cat



