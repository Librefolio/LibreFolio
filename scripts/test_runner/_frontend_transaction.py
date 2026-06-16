"""Frontend Transaction E2E tests."""

import subprocess

from ._common import _RESUME_MODE, PROJECT_ROOT, Colors, _run_test_suite, print_error, print_section, print_success
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright


def front_tx_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction unit tests (Vitest) — txPayloadHelpers + txCommitApi."""
    print_section("Frontend TX Unit Tests (Vitest)")
    cmd = ["npx", "vitest", "run", "src/lib/utils/__tests__/txPayloadHelpers.test.ts", "src/lib/utils/__tests__/txCommitApi.test.ts"]
    print(f"\n{Colors.BLUE}Running: TX Vitest unit tests{Colors.NC}")
    print(f"Command:\n└─▶ $ cd frontend && {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", text=True)
        if result.returncode == 0:
            print_success("TX Vitest unit tests - PASSED")
            return True
        else:
            print_error(f"TX Vitest unit tests - FAILED (exit code: {result.returncode})")
            return False
    except Exception as e:
        print_error(f"Vitest error: {e}")
        return False


def front_transactions_modals(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction E2E tests."""
    print_section("Frontend Transaction Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/transactions-modals.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_transactions_table(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run TransactionsTable (main read-view) E2E tests."""
    print_section("Frontend TransactionsTable Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/transactions-table.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_broker_access(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Broker Access E2E tests (Bug 1,3,10,13 + enum filters)."""
    print_section("Frontend TX Broker Access Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-broker-access.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_paired_edit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Paired Edit E2E tests (Bug 2,6,7,14)."""
    print_section("Frontend TX Paired Edit Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-paired-edit.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_tooltips(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Tooltip E2E tests (Bug 8 + Enhancement)."""
    print_section("Frontend TX Tooltip Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-tooltips.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_delete(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Delete E2E tests (DeleteModal, BulkDelete, PickerModal guard)."""
    print_section("Frontend TX Delete Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-delete.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_picker_pagination(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run PickerModal Pagination E2E tests (pagination, reset, tooltip, validation banners)."""
    print_section("Frontend TX Picker Pagination Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-picker-pagination.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_clone(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Clone E2E tests (standalone, paired, qty=0, commit, viewer guard)."""
    print_section("Frontend TX Clone Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-clone.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_bulk_operations(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Bulk Operations E2E tests (mixed commit, reset, picker guard, validation)."""
    print_section("Frontend TX Bulk Operations Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-bulk-operations.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_split_promote(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction Split & Promote E2E tests (split, promote, merge modal, guards)."""
    print_section("Frontend TX Split & Promote Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-split-promote.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_crud_full(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Full CRUD lifecycle E2E tests for transactions."""
    print_section("Frontend TX CRUD Full Lifecycle Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-crud-full.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_commit_all_types(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run commit-to-API E2E tests for every transaction type (standalone + paired + edit + delete)."""
    print_section("Frontend TX Commit All Types Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-commit-all-types.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_bulk_suggest_ux(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run BulkModal Suggest UX E2E tests (split badge, type preview, undo, suggest banner, ActionModal rows)."""
    print_section("Frontend TX Bulk Suggest UX Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-bulk-suggest-ux.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_fx_implied_rate(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX Implied Rate & Spread E2E tests (banner suffix, FormModal marker, semantic ordering)."""
    print_section("Frontend TX FX Implied Rate Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-fx-implied-rate.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_wac(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run TX WAC Preview E2E tests."""
    print_section("Frontend TX WAC Preview Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-wac.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_wac_bulk(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run TX WAC BulkModal Cell Rendering E2E tests (Bug 9, 10, 11 + link_uuid fix)."""
    print_section("Frontend TX WAC BulkModal Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-wac-bulk.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_wac_formmodal(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run TX WAC FormModal Payload E2E tests (FM1-FM9: cost_basis_mode propagation)."""
    print_section("Frontend TX WAC FormModal Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-wac-formmodal.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_wac_fx(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run TX WAC FX Sync E2E tests (sync modal, qualifying table cross-FX, tooltip)."""
    print_section("Frontend TX WAC FX Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-wac-fx.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_wac_mode(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run TX WAC Mode Toggle E2E tests (auto/manual, blur, placeholder)."""
    print_section("Frontend TX WAC Mode Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-wac-mode.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_event_picker(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run TX Event Picker E2E tests (card-style dropdown, delta, slider, visibility)."""
    print_section("Frontend TX Event Picker Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-event-picker.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_brim_import(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run BRIM Import Wizard E2E tests (wizard flow, parse, resolve, import to BulkModal)."""
    print_section("Frontend TX BRIM Import Wizard Tests")
    if not _ensure_frontend_build():
        return False
    # Populate DB with broker report files (--with-reports flag)
    from ._backend_db import db_populate
    if not db_populate(verbose=verbose, force=True, with_reports=True):
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-brim-import.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_import_resolution(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Import Wizard Resolution E2E tests (resolve section, identifier prompt, create asset)."""
    print_section("Frontend TX Import Resolution Tests")
    if not _ensure_frontend_build():
        return False
    # Populate DB with broker report files (--with-reports flag for generic_simple.csv)
    from ._backend_db import db_populate
    if not db_populate(verbose=verbose, force=True, with_reports=True):
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-resolution.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


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
            ("TX Commit All Types", lambda: front_tx_commit_all_types(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX Bulk Suggest UX", lambda: front_tx_bulk_suggest_ux(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX FX Implied Rate", lambda: front_tx_fx_implied_rate(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX WAC Preview", lambda: front_tx_wac(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX WAC BulkModal", lambda: front_tx_wac_bulk(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX WAC FormModal", lambda: front_tx_wac_formmodal(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX WAC FX", lambda: front_tx_wac_fx(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX WAC Mode", lambda: front_tx_wac_mode(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX Event Picker", lambda: front_tx_event_picker(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX BRIM Import", lambda: front_tx_brim_import(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("TX Import Resolution", lambda: front_tx_import_resolution(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
        ],
        verbose=verbose,
        header_msg="All Transaction Tests (E2E)",
        summary_title="Transaction Test Summary",
        success_msg="All Transaction tests passed! 🎉",
        resume=_RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all frontend transaction test entries."""
    from ._common import add_test, make_category

    cat = make_category(help_text="Frontend Transaction E2E tests (bulk modal, form, paired, type swap, table read-view, broker access, tooltips)", description="""Frontend Transaction Tests\n\nOptions: --ui, --headed, --debug""")
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
    add_test(cat, "tx-commit-all-types", front_tx_commit_all_types, name="TX Commit All Types Tests", desc="End-to-end commit for every TX type: standalone + paired create, edit, delete", tests="transactions/tx-commit-all-types.spec.ts")
    add_test(cat, "tx-bulk-suggest-ux", front_tx_bulk_suggest_ux, name="TX Bulk Suggest UX Tests", desc="Split badge, type preview, undo split, suggest banner, ActionModal AFTER rows", tests="transactions/tx-bulk-suggest-ux.spec.ts")
    add_test(cat, "tx-fx-implied-rate", front_tx_fx_implied_rate, name="TX FX Implied Rate Tests", desc="FX implied rate in banner suffix + FormModal marker + semantic ordering", tests="transactions/tx-fx-implied-rate.spec.ts")
    add_test(cat, "tx-wac", front_tx_wac, name="TX WAC Preview Tests", desc="WAC preview toggle, auto/manual, recalculate, qualifying TXs, missing FX", tests="transactions/tx-wac.spec.ts")
    add_test(cat, "tx-wac-bulk", front_tx_wac_bulk, name="TX WAC BulkModal Tests", desc="BulkModal WAC cell rendering: auto value, manual propagation, DB rows, clone link_uuid", tests="transactions/tx-wac-bulk.spec.ts")
    add_test(cat, "tx-wac-formmodal", front_tx_wac_formmodal, name="TX WAC FormModal Tests", desc="FormModal WAC payload: cost_basis_mode propagation, auto/manual toggle, partner rows", tests="transactions/tx-wac-formmodal.spec.ts")
    add_test(cat, "tx-wac-fx", front_tx_wac_fx, name="TX WAC FX Tests", desc="WAC FX sync modal, qualifying table cross-currency arrow, tooltip format, stale banner", tests="transactions/tx-wac-fx.spec.ts")
    add_test(cat, "tx-wac-mode", front_tx_wac_mode, name="TX WAC Mode Tests", desc="WAC auto/manual toggle, blur-without-change stays auto, placeholder with validate hint", tests="transactions/tx-wac-mode.spec.ts")
    add_test(cat, "tx-event-picker", front_tx_event_picker, name="TX Event Picker Tests", desc="Event picker card-style dropdown, delta, slider range, type visibility", tests="transactions/tx-event-picker.spec.ts")
    add_test(cat, "tx-brim-import", front_tx_brim_import, name="TX BRIM Import Wizard Tests", desc="Import Wizard flow: open, select file, parse, resolve assets, import to BulkModal", tests="transactions/tx-brim-import.spec.ts")
    add_test(cat, "tx-import-resolution", front_tx_import_resolution, name="TX Import Resolution Tests", desc="Advanced resolve flow: resolve section, AssetSelect, identifier prompt, create asset, full E2E", tests="transactions/tx-import-resolution.spec.ts")
    add_test(cat, "tx-unit", front_tx_unit, test_names=False, name="TX Unit Tests (Vitest)", desc="Pure unit tests: txPayloadHelpers + txCommitApi", tests="vitest")
    add_test(cat, "all", front_transaction_all, test_names=False, name="All Transaction Tests", desc="Run all Transaction E2E tests")
    registry["front-transaction"] = cat
