"""Frontend Transaction E2E tests."""

import subprocess

from . import _common
from ._common import PROJECT_ROOT, Colors, _get_category_tests_for_all, _run_test_suite, print_error, print_section, print_success
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright, reset_setup_scope


def front_tx_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Transaction unit tests (Vitest), including URL/filter state."""
    print_section("Frontend TX Unit Tests (Vitest)")
    cmd = ["npx", "vitest", "run",
           "src/lib/utils/__tests__/txPayloadHelpers.test.ts",
           "src/lib/utils/__tests__/txCommitApi.test.ts",
           "src/lib/utils/__tests__/promoteHelpers.test.ts",
           "src/lib/utils/transactions/splitRowCharges.test.ts",
           "src/lib/utils/transactions/fixRowLifecycle.test.ts",
           "src/lib/utils/transactions/duplicateRecheckPayload.test.ts",
           "src/lib/utils/transactions/bulkDisplay.test.ts",
           "src/lib/utils/transactions/importReportSets.test.ts",
           "src/lib/utils/transactions/importPairs.test.ts",
           "src/lib/utils/transactions/promoteSuggest.test.ts",
           "src/lib/utils/brim/defaultPluginCheck.test.ts",
           "src/lib/utils/brim/pluginText.test.ts",
           "src/lib/utils/brim/pluginKind.test.ts",
           "src/lib/components/transactions/modals/ImportBrokerMismatchModal.test.ts",
           "src/lib/components/transactions/modals/PromoteAllModal.test.ts",
           "src/lib/utils/transactions/gapFixModel.test.ts",
           "src/lib/components/transactions/import/GapFixStep.test.ts",
           "src/lib/components/transactions/import/ReportSetCard.test.ts",
           "src/lib/components/transactions/modals/ParseDetailModal.test.ts",
           "src/lib/utils/transactions/bulkTodos.test.ts",
           "src/routes/(app)/transactions/filterState.test.ts"]
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


def front_tx_bulk_promote_exec(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run BulkModal promote-execution + restore-and-edit E2E tests (D2 coverage)."""
    print_section("Frontend TX Bulk Promote Execution Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-bulk-promote-exec.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_bulk_promote_cost_basis(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run BulkModal promote → receiver without cost basis E2E tests (new/saved receiver, Merge all)."""
    print_section("Frontend TX Bulk Promote Cost Basis Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-bulk-promote-cost-basis.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


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


def front_tx_wac_unit_toggle(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run TX Cost Basis Total/Per-unit toggle E2E tests."""
    print_section("Frontend TX WAC Unit Toggle Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-wac-unit-toggle.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


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


def front_tx_ca_contract(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the plugin -> frontend contract E2E tests (CA fixture as the message)."""
    print_section("Frontend TX Import Plugin Contract Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-ca-contract.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_asset_identity(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the asset identity E2E tests (unification step, dual-ISIN bonds)."""
    print_section("Frontend TX Import Asset Identity Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-asset-identity.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


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


def front_tx_import_upload(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Import Wizard upload-step E2E tests (client-side validation, broker assign, discard guard)."""
    print_section("Frontend TX Import Upload Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-upload.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_import_report_set(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Import Wizard report-set E2E tests (Danske Bank sets through steps 1-4; each test owns its broker and uploads).

    Desktop and mobile: a test tagged @mobile runs on the mobile project only, every other test on desktop only.
    """
    print_section("Frontend TX Import Report Set Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-report-set.spec.ts", ui=ui, headed=headed, debug=debug, project="", test_names=test_names, coverage=coverage)


def front_tx_import_degiro(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Import Wizard DEGIRO E2E tests (Account Statement in English; currency conversions as linked pairs in review and editor)."""
    print_section("Frontend TX Import DEGIRO Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-degiro.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_import_broker_mismatch(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Import Wizard broker-mismatch E2E tests (a file its broker's default import plugin cannot read: Move, no question, Remove)."""
    print_section("Frontend TX Import Broker Mismatch Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-broker-mismatch.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_import_scalable_transfers(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Import Wizard + bulk editor Scalable transfer E2E tests (new + new and new + saved internal transfers merged into Cash Transfers)."""
    print_section("Frontend TX Import Scalable Transfers Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-scalable-transfers.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_import_report_set_guide(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the import guide's gap-fix step on desktop and mobile (report sets C3, R9; a disposable account per test)."""
    print_section("Frontend TX Import Report Set Guide Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-report-set-guide.spec.ts", ui=ui, headed=headed, debug=debug, project="", test_names=test_names, coverage=coverage)


def front_tx_import_asset_inspector(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Group E inspector metadata persistence and nested-dialog E2E regressions."""
    print_section("Frontend TX Import Asset Inspector Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-asset-inspector.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_fx_completeness(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run paired FX readiness, local staging and real commit regressions."""
    print_section("Frontend TX FX Completeness Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-fx-completeness.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_import_matching(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run independent BRIM matching contract checks."""
    print_section("Frontend TX Import Matching Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-matching.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_import_duplicate_precedence(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run cross-file duplicate keeper vs DB/editor collision regressions."""
    print_section("Frontend TX Import Duplicate Precedence Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-duplicate-precedence.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_bulk_diagnostics(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run balance contributor and chronological workspace regressions."""
    print_section("Frontend TX Bulk Diagnostics Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-bulk-diagnostics.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_bulk_import_handoff(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the bulk editor after an import hand-over (F1: one validation per import, todo banners that lead to their rows)."""
    print_section("Frontend TX Bulk Import Handoff Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-bulk-import-handoff.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_import_file_selection(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run owned-file pagination, selection and uploaded-broker folding regressions."""
    print_section("Frontend TX Import File Selection Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-file-selection.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_import_flow(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Import Wizard analyze-step + navigation + review-controls E2E tests."""
    print_section("Frontend TX Import Flow Tests")
    if not _ensure_frontend_build():
        return False
    # Parses the seeded generic_simple.csv report → needs --with-reports.
    from ._backend_db import db_populate
    if not db_populate(verbose=verbose, force=True, with_reports=True):
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-import-flow.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_broker_icon_hydration(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the at-most-one broker detail request per cache generation checks (C3)."""
    print_section("Frontend TX Broker Icon Hydration Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-broker-icon-hydration.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_bulk_row_order(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the BulkModal same-date creation-order E2E test (C4: E-order)."""
    print_section("Frontend TX Bulk Row Order Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-bulk-row-order.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tx_selection_after_bulk(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the Transactions page selection-after-operation E2E tests (K step 12a)."""
    print_section("Frontend TX Selection After Bulk Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("transactions/tx-selection-after-bulk.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_transaction_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all Transaction E2E tests."""
    if _common.nothing_left_to_run("front-transaction"):
        return _common.consolidated_verdict("front-transaction")
    reset_setup_scope()
    return _run_test_suite(
        suite_name="All Transaction Tests (E2E)",
        tests=_get_category_tests_for_all("front-transaction", verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage),
        verbose=verbose,
        header_msg="All Transaction Tests (E2E)",
        summary_title="Transaction Test Summary",
        success_msg="All Transaction tests passed! 🎉",
        resume=_common._RESUME_MODE,
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
    add_test(cat, "tx-delete", front_tx_delete, name="TX Delete Tests", desc="Single-row delete through the bulk workspace (T4): pre-marked rows, pair auto-include + collapse, split hint, committed:false inline error, PickerModal guard", tests="transactions/tx-delete.spec.ts")
    add_test(cat, "tx-picker-pagination", front_tx_picker_pagination, name="TX Picker Pagination Tests", desc="PickerModal pagination, reset on reopen, tooltip richness, validation banners", tests="transactions/tx-picker-pagination.spec.ts")
    add_test(cat, "tx-clone", front_tx_clone, name="TX Clone Tests", desc="Clone standalone, paired, qty=0, commit pair, viewer guard", tests="transactions/tx-clone.spec.ts")
    add_test(cat, "tx-bulk-operations", front_tx_bulk_operations, name="TX Bulk Operations Tests", desc="Mixed commit, reset, picker guard, pair validation, mark delete", tests="transactions/tx-bulk-operations.spec.ts")
    add_test(cat, "tx-split-promote", front_tx_split_promote, name="TX Split & Promote Tests", desc="Split paired, promote standalone, merge modal, guards, non-regression", tests="transactions/tx-split-promote.spec.ts")
    add_test(cat, "tx-crud-full", front_tx_crud_full, name="TX CRUD Full Lifecycle Tests", desc="Full CRUD lifecycle: standalone, paired, split, promote, bulk, suggest, cash sign", tests="transactions/tx-crud-full.spec.ts")
    add_test(cat, "tx-commit-all-types", front_tx_commit_all_types, name="TX Commit All Types Tests", desc="End-to-end commit for every TX type: standalone + paired create, edit, delete", tests="transactions/tx-commit-all-types.spec.ts")
    add_test(cat, "tx-bulk-suggest-ux", front_tx_bulk_suggest_ux, name="TX Bulk Suggest UX Tests", desc="Split badge, type preview, undo split, suggest banner, ActionModal AFTER rows", tests="transactions/tx-bulk-suggest-ux.spec.ts")
    add_test(cat, "tx-bulk-promote-exec", front_tx_bulk_promote_exec, name="TX Bulk Promote Execution Tests", desc="Promote execution: edit+edit/create+create/mixed, merge modal confirm/cancel, banner link, restore-and-edit", tests="transactions/tx-bulk-promote-exec.spec.ts")
    add_test(
        cat,
        "tx-bulk-promote-cost-basis",
        front_tx_bulk_promote_cost_basis,
        name="TX Bulk Promote Cost Basis Tests",
        desc="d7c148564 in the bulk editor, owned asset and brokers: a promoted TRANSFER receiver without a cost basis refuses the whole batch with costBasisRequired — PC1 new receiver (Manual, empty) + saved sender via the selection toolbar → create issue; PC2 saved receiver (SPLIT-linked, Auto: stored without a cost basis) + new sender via the banner link → promote issue with ref_id; PC3 «Merge all» with a valid cash pair → the one create issue; each checks the commit answer against the sent request, that nothing was written, and that the refused-save issue jumps to the pair's row only; PC4 the banner offers a new +5 only the saved −5 it cancels, never the saved −3 beside it (nothing saved)",
        tests="transactions/tx-bulk-promote-cost-basis.spec.ts",
    )
    add_test(cat, "tx-fx-implied-rate", front_tx_fx_implied_rate, name="TX FX Implied Rate Tests", desc="FX implied rate in banner suffix + FormModal marker + semantic ordering", tests="transactions/tx-fx-implied-rate.spec.ts")
    add_test(cat, "tx-wac", front_tx_wac, name="TX WAC Preview Tests", desc="WAC preview toggle, auto/manual, recalculate, qualifying TXs, missing FX", tests="transactions/tx-wac.spec.ts")
    add_test(cat, "tx-wac-bulk", front_tx_wac_bulk, name="TX WAC BulkModal Tests", desc="BulkModal WAC cell rendering: auto value, manual propagation, DB rows, clone link_uuid", tests="transactions/tx-wac-bulk.spec.ts")
    add_test(cat, "tx-wac-formmodal", front_tx_wac_formmodal, name="TX WAC FormModal Tests", desc="FormModal WAC payload: cost_basis_mode propagation, auto/manual toggle, partner rows", tests="transactions/tx-wac-formmodal.spec.ts")
    add_test(cat, "tx-wac-fx", front_tx_wac_fx, name="TX WAC FX Tests", desc="WAC FX sync modal, qualifying table cross-currency arrow, tooltip format, stale banner", tests="transactions/tx-wac-fx.spec.ts")
    add_test(cat, "tx-wac-mode", front_tx_wac_mode, name="TX WAC Mode Tests", desc="WAC auto/manual toggle, blur-without-change stays auto, placeholder with validate hint", tests="transactions/tx-wac-mode.spec.ts")
    add_test(cat, "tx-wac-unit-toggle", front_tx_wac_unit_toggle, name="TX WAC Unit Toggle Tests", desc="Cost basis Total/Per-unit display toggle, round-trip conversion, commit payload stays per-unit, localStorage persistence", tests="transactions/tx-wac-unit-toggle.spec.ts")
    add_test(cat, "tx-event-picker", front_tx_event_picker, name="TX Event Picker Tests", desc="Event picker card-style dropdown, delta, slider range, type visibility", tests="transactions/tx-event-picker.spec.ts")
    add_test(cat, "tx-brim-import", front_tx_brim_import, name="TX BRIM Import Wizard Tests", desc="Import Wizard flow: open, select file, parse, resolve assets, import to BulkModal", tests="transactions/tx-brim-import.spec.ts")
    add_test(cat, "tx-ca-contract", front_tx_ca_contract, name="TX Import Plugin Contract Tests", desc="plugin->frontend channels: notices, evidence, field todos, split hints, asset notices", tests="transactions/tx-import-ca-contract.spec.ts")
    add_test(cat, "tx-asset-identity", front_tx_asset_identity, name="TX Import Asset Identity Tests", desc="Unification step: certain/proposed/lone states, merge, split, rename, primary ISIN election", tests="transactions/tx-import-asset-identity.spec.ts")
    add_test(cat, "tx-import-resolution", front_tx_import_resolution, name="TX Import Resolution Tests", desc="Advanced resolve flow: resolve section, AssetSelect, identifier prompt, create asset, full E2E", tests="transactions/tx-import-resolution.spec.ts")
    add_test(cat, "tx-import-upload", front_tx_import_upload, name="TX Import Upload Tests", desc="Upload step: extension/size validation, error banner, broker assign, drop-zone collapse, discard guard", tests="transactions/tx-import-upload.spec.ts")
    add_test(
        cat,
        "tx-import-report-set",
        front_tx_import_report_set,
        name="TX Import Report Set Tests",
        desc="Report sets (C2): step-1 missing-export warning, step-2 set card (complete, incomplete, upload missing, exclude), the set as one analysis row with its pairing detail, review hiding the rows before H0; (C3) the gap-fix step after Import (R5 opening deposit selected by default, a new request on Back + Import, gap_fix rows in the editor; R6 none selected; R7 a single generic CSV never asks it) and the FilesTable set badges in the broker's import files (R8); on mobile (tests tagged @mobile), the set card's header and timeline fit a phone",
        tests="transactions/tx-import-report-set.spec.ts",
    )
    add_test(
        cat,
        "tx-import-report-set-guide",
        front_tx_import_report_set_guide,
        name="TX Import Report Set Guide Tests",
        desc="Report sets (C3, R9) on desktop and mobile: the import guide's step on the gap-fix (import.gapFix, between review and bulk) anchored on the step's Continue, with a disposable account whose earlier import-guide steps are completed over the API",
        tests="transactions/tx-import-report-set-guide.spec.ts",
    )
    add_test(
        cat,
        "tx-import-degiro",
        front_tx_import_degiro,
        name="TX Import DEGIRO Tests",
        desc="DEGIRO Account Statement in English: currency conversions as one row per linked pair in review (From/To, implied rate, one tick for both legs), handed to the editor as pairs that validate",
        tests="transactions/tx-import-degiro.spec.ts",
    )
    add_test(
        cat,
        "tx-import-broker-mismatch",
        front_tx_import_broker_mismatch,
        name="TX Import Broker Mismatch Tests",
        desc="Step 1 upload vs the broker's default import plugin (Scalable Capital): M1 on a disposable account, the overnight account's file on the broker account (broker_scalable) raises the mismatch modal with the plugin-check reason and one target, the overnight account (its generic-CSV broker dropped by the fallback rule), Continue disabled while it is open; Move re-uploads the file there in the same batch, deletes the old copy and step 2 lists it under the target; M2 on its own default broker no question and no plugin check; M3 Remove deletes the file, Continue is released and the wizard stays on step 1",
        tests="transactions/tx-import-broker-mismatch.spec.ts",
    )
    add_test(
        cat,
        "tx-import-scalable-transfers",
        front_tx_import_scalable_transfers,
        name="TX Import Scalable Transfers Tests",
        desc="Scalable Capital internal transfers (plan 37 step 11), each test on a disposable account with its two brokers (broker_scalable, broker_scalable_deposit): S1 both exports in one wizard run, new rows asked to promote-suggest under negative ids, the banner proposes exactly the two transfers (identified by the merge dialog's joined text), one merged and saved as a linked CASH_TRANSFER pair; S2 the broker account's cash rows saved over the API first, the overnight export imported, the 💡 (toolbar and row menu of the new transfer legs only) offers the saved sides, one added, the new + saved pair merged and saved as a linked CASH_TRANSFER through the mixed promote",
        tests="transactions/tx-import-scalable-transfers.spec.ts",
    )
    add_test(
        cat,
        "tx-import-asset-inspector",
        front_tx_import_asset_inspector,
        name="TX Import Asset Inspector Tests",
        desc="Group E: real metadata PATCH/GET/reopen, inactive assets, offline Ask Provider, currency wipe and comparison overlay hit-testing",
        tests="transactions/tx-import-asset-inspector.spec.ts",
    )
    add_test(cat, "tx-fx-completeness", front_tx_fx_completeness, name="TX FX Completeness Tests", desc="Broker-before-type readiness, precise local FX drafts, independent leg dates, funded commit and insufficient-funds rejection", tests="transactions/tx-fx-completeness.spec.ts")
    add_test(cat, "tx-import-matching", front_tx_import_matching, name="TX Import Matching Tests", desc="Independent primary/alternate identifier, inactive-asset, ambiguity and catalog refresh contract checks", tests="transactions/tx-import-matching.spec.ts")
    add_test(
        cat,
        "tx-import-duplicate-precedence",
        front_tx_import_duplicate_precedence,
        name="TX Import Duplicate Precedence Tests",
        desc="Cross-file duplicate keeper vs DB/editor collisions, badge compare target, resolver choices across the final recheck",
        tests="transactions/tx-import-duplicate-precedence.spec.ts",
    )
    add_test(cat, "tx-bulk-diagnostics", front_tx_bulk_diagnostics, name="TX Bulk Diagnostics Tests", desc="Complete balance-group rows, chronological display-only sorting, and stable payload identity", tests="transactions/tx-bulk-diagnostics.spec.ts")
    add_test(
        cat,
        "tx-bulk-import-handoff",
        front_tx_bulk_import_handoff,
        name="TX Bulk Import Handoff Tests",
        desc="F1 (D5) every import hand-over runs ONE validation, above the 50-row threshold too, an edit above it none, the next import one more; (D4) every entry of the todo banners (blockers and warnings) is a tx-bulk-todo-goto that pages the grid to its row and highlights it; owned broker, synthetic cash-only CSVs, nothing saved",
        tests="transactions/tx-bulk-import-handoff.spec.ts",
    )
    add_test(cat, "tx-import-file-selection", front_tx_import_file_selection, name="TX Import File Selection Tests", desc="Owned broker files: five-row pagination, cross-page selection and upload-only panel expansion", tests="transactions/tx-import-file-selection.spec.ts")
    add_test(cat, "tx-import-flow", front_tx_import_flow, name="TX Import Flow Tests", desc="Analyze step (detail modal, view-all, re-parse), step navigation, review selection toolbar + discard guard", tests="transactions/tx-import-flow.spec.ts")
    add_test(
        cat,
        "tx-broker-icon-hydration",
        front_tx_broker_icon_hydration,
        name="TX Broker Icon Hydration Tests",
        desc="C3: an owned broker without icon fields is asked for (GET /brokers/{id}) at most once per cache generation, across a Refresh round trip; portal_url control never asked",
        tests="transactions/tx-broker-icon-hydration.spec.ts",
    )
    add_test(cat, "tx-bulk-row-order", front_tx_bulk_row_order, name="TX Bulk Row Order Tests", desc="C4 E-order: five new same-date rows keep their creation order in the BulkModal grid, read by owned description; editor discarded, nothing saved", tests="transactions/tx-bulk-row-order.spec.ts")
    add_test(
        cat,
        "tx-selection-after-bulk",
        front_tx_selection_after_bulk,
        name="TX Selection After Bulk Tests",
        desc="Step 12a: after an executed edit, clone, delete, add, link or unlink the toolbar and the table checkboxes are empty and one click selects one row; after a cancelled editor, link or unlink both are unchanged",
        tests="transactions/tx-selection-after-bulk.spec.ts",
    )
    add_test(cat, "tx-unit", front_tx_unit, test_names=False, name="TX Unit Tests (Vitest)", desc="Pure unit tests: txPayloadHelpers + txCommitApi + promoteHelpers + splitRowCharges + fixRowLifecycle + duplicateRecheckPayload + importReportSets + gapFixModel + GapFixStep (jsdom)", tests="vitest")
    add_test(cat, "all", front_transaction_all, test_names=False, name="All Transaction Tests", desc="Run all Transaction E2E tests")
    registry["front-transaction"] = cat
