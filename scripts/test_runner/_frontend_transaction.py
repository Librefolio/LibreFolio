"""Frontend Transaction E2E tests."""

from ._common import _run_test_suite, print_section
from ._frontend_common import _ensure_frontend_build, _ensure_db_populated, _ensure_test_users, _run_playwright


def front_transactions_modals(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction E2E tests."""
    print_section("Frontend Transaction Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/transactions-modals.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_transactions_table(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run TransactionsTable (main read-view) E2E tests."""
    print_section("Frontend TransactionsTable Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/transactions-table.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_broker_access(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Broker Access E2E tests (Bug 1,3,10,13 + enum filters)."""
    print_section("Frontend TX Broker Access Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/tx-broker-access.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_paired_edit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Paired Edit E2E tests (Bug 2,6,7,14)."""
    print_section("Frontend TX Paired Edit Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/tx-paired-edit.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_tooltips(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Tooltip E2E tests (Bug 8 + Enhancement)."""
    print_section("Frontend TX Tooltip Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/tx-tooltips.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_delete(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Delete E2E tests (DeleteModal, BulkDelete, PickerModal guard)."""
    print_section("Frontend TX Delete Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/tx-delete.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_picker_pagination(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run PickerModal Pagination E2E tests (pagination, reset, tooltip, validation banners)."""
    print_section("Frontend TX Picker Pagination Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/tx-picker-pagination.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_clone(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Clone E2E tests (standalone, paired, qty=0, commit, viewer guard)."""
    print_section("Frontend TX Clone Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/tx-clone.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_bulk_operations(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Bulk Operations E2E tests (mixed commit, reset, picker guard, validation)."""
    print_section("Frontend TX Bulk Operations Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/tx-bulk-operations.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_split_promote(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Split & Promote E2E tests (split, promote, merge modal, guards)."""
    print_section("Frontend TX Split & Promote Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/tx-split-promote.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_crud_full(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Full CRUD lifecycle E2E tests for transactions."""
    print_section("Frontend TX CRUD Full Lifecycle Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("transactions/tx-crud-full.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_transaction_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all Transaction E2E tests."""
    return _run_test_suite(
        suite_name="All Transaction Tests (E2E)",
        tests=[
            ("Transactions", lambda: front_transactions_modals(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TransactionsTable", lambda: front_transactions_table(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX Broker Access", lambda: front_tx_broker_access(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX Paired Edit", lambda: front_tx_paired_edit(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX Tooltips", lambda: front_tx_tooltips(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX Delete", lambda: front_tx_delete(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX Picker Pagination", lambda: front_tx_picker_pagination(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX Clone", lambda: front_tx_clone(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX Bulk Operations", lambda: front_tx_bulk_operations(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX Split & Promote", lambda: front_tx_split_promote(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX CRUD Full", lambda: front_tx_crud_full(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
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
        help_text="Frontend Transaction E2E tests (bulk modal, form, paired, type swap, table read-view, broker access, tooltips)",
        description="""Frontend Transaction Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "transactions-modals", front_transactions_modals, name="Transaction Modal Tests", desc="BulkModal, FormModal, paired rows, type swap, i18n, CRUD", tests="transactions/transactions-modals.spec.ts")
    add_test(cat, "transactions-table", front_transactions_table, name="TransactionsTable Tests", desc="Main read-view table: pairs, ghost rows, GoTo, actions, selection", tests="transactions/transactions-table.spec.ts")
    add_test(cat, "tx-broker-access", front_tx_broker_access, name="TX Broker Access Tests", desc="Broker dropdown filtering, hidden broker lock, edit button visibility, enum filters", tests="transactions/tx-broker-access.spec.ts")
    add_test(cat, "tx-paired-edit", front_tx_paired_edit, name="TX Paired Edit Tests", desc="Clone INTEREST qty=0, paired edit payload, flat mode adjacency", tests="transactions/tx-paired-edit.spec.ts")
    add_test(cat, "tx-tooltips", front_tx_tooltips, name="TX Tooltip Tests", desc="Linked pair tooltip: favicon, bold name, SVG role icon, hidden broker", tests="transactions/tx-tooltips.spec.ts")
    add_test(cat, "tx-delete", front_tx_delete, name="TX Delete Tests", desc="DeleteModal layouts, bulk delete, committed:false error, PickerModal guard", tests="transactions/tx-delete.spec.ts")
    add_test(cat, "tx-picker-pagination", front_tx_picker_pagination, name="TX Picker Pagination Tests", desc="PickerModal pagination, reset on reopen, tooltip richness, validation banners", tests="transactions/tx-picker-pagination.spec.ts")
    add_test(cat, "tx-clone", front_tx_clone, name="TX Clone Tests", desc="Clone standalone, paired, qty=0, commit pair, viewer guard", tests="transactions/tx-clone.spec.ts")
    add_test(cat, "tx-bulk-operations", front_tx_bulk_operations, name="TX Bulk Operations Tests", desc="Mixed commit, reset, picker guard, pair validation, mark delete", tests="transactions/tx-bulk-operations.spec.ts")
    add_test(cat, "tx-split-promote", front_tx_split_promote, name="TX Split & Promote Tests", desc="Split paired, promote standalone, merge modal, guards, non-regression", tests="transactions/tx-split-promote.spec.ts")
    add_test(cat, "tx-crud-full", front_tx_crud_full, name="TX CRUD Full Lifecycle Tests", desc="Full CRUD lifecycle: standalone, paired, split, promote, bulk, suggest, cash sign", tests="transactions/tx-crud-full.spec.ts")
    add_test(cat, "all", front_transaction_all, test_names=False, name="All Transaction Tests", desc="Run all Transaction E2E tests")
    registry["front-transaction"] = cat
