"""Frontend Transaction E2E tests."""

from ._common import _run_test_suite, print_section
from ._frontend_common import _ensure_frontend_build, _ensure_db_populated, _ensure_test_users, _run_playwright


def front_transactions(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction E2E tests."""
    print_section("Frontend Transaction Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/transactions.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_transaction_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all Transaction E2E tests."""
    return _run_test_suite(
        suite_name="All Transaction Tests (E2E)",
        tests=[
            ("Transactions", lambda: front_transactions(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
        ],
        verbose=verbose,
        header_msg="All Transaction Tests (E2E)",
        summary_title="Transaction Test Summary",
        success_msg="All Transaction tests passed! 🎉",
    )


def populate_registry(registry: dict) -> None:
    """Register all frontend transaction test entries."""
    from ._common import make_category, add_test
    cat = make_category(
        help_text="Frontend Transaction E2E tests (bulk modal, form, paired, type swap)",
        description="""Frontend Transaction Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "transactions", front_transactions, name="Transaction Tests", desc="Transaction list, bulk modal, form modal, paired rows", tests="transactions/transactions.spec.ts")
    add_test(cat, "all", front_transaction_all, test_names=False, name="All Transaction Tests", desc="Run all Transaction E2E tests")
    registry["front-transaction"] = cat
