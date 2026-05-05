"""Frontend broker E2E tests: broker list/CRUD + broker detail page."""

from ._common import _run_test_suite, print_header, print_section
from ._frontend_common import _ensure_frontend_build, _ensure_test_users, _run_playwright


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
    """Run all frontend broker E2E tests (single Playwright invocation)."""
    print_header("Frontend Broker Tests (Playwright)")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    # Run both specs in a single Playwright call so the web server stays running
    # and the broker created by brokers.spec.ts persists for brokers-detail.spec.ts
    return _run_playwright(["brokers/brokers.spec.ts", "brokers/brokers-detail.spec.ts"], ui=ui, headed=headed, debug=debug, coverage=coverage)


def populate_registry(registry: dict) -> None:
    """Register all frontend broker test entries."""
    from ._common import make_category, add_test
    cat = make_category(
        help_text="Frontend broker E2E tests (list, CRUD, detail page)",
        description="""Frontend Broker Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "list", front_broker_list, name="Broker List & CRUD Tests", desc="Broker list page, create/edit/delete", prereq="Login working", tests="brokers/brokers.spec.ts")
    add_test(cat, "detail", front_broker_detail, name="Broker Detail Tests", desc="Detail page sections, edit/import modals", prereq="Login working, brokers exist", tests="brokers/brokers-detail.spec.ts")
    add_test(cat, "all", front_broker_all, test_names=False, name="All Broker Tests", desc="Run all broker E2E tests")
    registry["front-broker"] = cat



