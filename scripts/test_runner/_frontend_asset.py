"""Frontend Asset E2E & unit tests: list, detail, modal, data editor, classification."""

import subprocess

from . import _common
from ._common import _get_category_tests_for_all, Colors, _run_test_suite, print_error, print_section, print_success
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright, reset_setup_scope


def front_asset_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset unit tests (Vitest) — price store, price/chart derived-state, local
    signal regression, chart aggregation, and worker-pool infra."""
    cmd = [
        "npx",
        "vitest",
        "run",
        "src/lib/stores/__tests__/assetPriceStoreRegistry.test.ts",
        "src/lib/utils/__tests__/assetPriceDerived.test.ts",
        "src/lib/components/charts/__tests__/timeSeriesAggregation.test.ts",
        "src/lib/components/charts/__tests__/lineChartHelpers.test.ts",
        "src/lib/components/charts/chartCoreHelpers.test.ts",
        "src/lib/charts/signals/__tests__/backendRenderer.test.ts",
        "src/lib/charts/signals/__tests__/catalogMapper.test.ts",
        "src/lib/charts/signals/__tests__/localSignalRegression.test.ts",
        "src/lib/workers/__tests__/workerPool.test.ts",
        "src/lib/workers/__tests__/priceProcessingPool.test.ts",
        "src/lib/workers/__tests__/priceProcessing.worker.test.ts",
        "src/lib/stores/signalCatalogStore.test.ts",
        "src/lib/utils/__tests__/assetSimilarity.test.ts",
        "src/lib/utils/__tests__/assetGrouping.test.ts",
        "src/lib/utils/__tests__/assetIdentifiers.test.ts",
    ]
    print(f"\n{Colors.BLUE}Running: Asset Vitest unit tests{Colors.NC}")
    result = subprocess.run(cmd, cwd="frontend", capture_output=not verbose)
    if result.returncode == 0:
        print_success("Asset Vitest unit tests - PASSED")
        return True
    else:
        print_error(f"Asset Vitest unit tests - FAILED (exit code: {result.returncode})")
        if not verbose:
            print(result.stdout.decode() if result.stdout else "")
            print(result.stderr.decode() if result.stderr else "")
        return False


def front_asset_list(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset list page E2E tests."""
    print_section("Frontend Asset List Page Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("assets/asset-list.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_detail(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset detail page E2E tests."""
    print_section("Frontend Asset Detail Page Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("assets/asset-detail.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_modal(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset modal E2E tests."""
    print_section("Frontend Asset Modal Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("assets/asset-modal.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_data_editor(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset data editor E2E tests."""
    print_section("Frontend Asset Data Editor Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("assets/asset-data-editor.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_classification(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset classification round-trip E2E tests."""
    print_section("Frontend Asset Classification Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("assets/asset-classification.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_merge(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset merge E2E tests (dry-run preview, confirm, identifier inheritance)."""
    print_section("Frontend Asset Merge Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("assets/asset-merge.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_event_delete(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset event delete E2E tests."""
    print_section("Frontend Asset Event Delete Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("assets/asset-event-delete.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all Asset tests (unit + E2E)."""
    if _common.nothing_left_to_run("front-asset"):
        return _common.consolidated_verdict("front-asset")
    reset_setup_scope()
    return _run_test_suite(
        suite_name="All Asset Tests (Unit + E2E)",
        tests=_get_category_tests_for_all("front-asset", verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage),
        verbose=verbose,
        header_msg="All Asset Tests (Unit + E2E)",
        summary_title="Asset Test Summary",
        success_msg="All Asset tests passed! 🎉",
        resume=_common._RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all frontend asset test entries."""
    from ._common import add_test, make_category
    cat = make_category(
        help_text="Frontend Asset E2E & unit tests (list, detail, modal, classification)",
        description="""Frontend Asset Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "asset-unit", front_asset_unit, test_names=False, name="Asset Unit Tests (Vitest)", desc="Unit tests: price store, derived-state, chart aggregation, local signals, worker pool, asset identity engine", tests="vitest")
    add_test(cat, "asset-list", front_asset_list, name="Asset List Page", desc="List page navigation, cards/table, filters", tests="assets/asset-list.spec.ts")
    add_test(cat, "asset-detail", front_asset_detail, name="Asset Detail Page", desc="Detail chart, panels, sync, edit", tests="assets/asset-detail.spec.ts")
    add_test(cat, "asset-merge", front_asset_merge, name="Asset Merge", desc="Merge duplicate assets: dry-run preview counts, confirm, ISIN inheritance", tests="assets/asset-merge.spec.ts")
    add_test(cat, "asset-modal", front_asset_modal, name="Asset Modal", desc="Create/edit modal, provider, distributions", tests="assets/asset-modal.spec.ts")
    add_test(cat, "asset-data-editor", front_asset_data_editor, name="Asset Data Editor", desc="Prices/Events tabs, CSV import", tests="assets/asset-data-editor.spec.ts")
    add_test(cat, "asset-classification", front_asset_classification, name="Asset Classification", desc="Distribution editors round-trip (geo, sector)", tests="assets/asset-classification.spec.ts")
    add_test(cat, "asset-event-delete", front_asset_event_delete, name="Asset Event Delete", desc="Delete asset events flow", tests="assets/asset-event-delete.spec.ts")
    add_test(cat, "all", front_asset_all, test_names=False, name="All Asset Tests", desc="Run all Asset tests (unit + E2E)")
    registry["front-asset"] = cat
