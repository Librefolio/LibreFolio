"""Frontend utility & component E2E tests: auth, settings, files, select, image-crop, utilities."""

import subprocess

from . import _common
from ._common import Colors, _get_category_tests_for_all, _run_test_suite, print_error, print_section, print_success
from ._frontend_common import _ensure_frontend_build, _ensure_test_users, _run_playwright, reset_setup_scope


def front_utility_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run core store + shared input/select primitive unit tests (Vitest)."""
    print(f"\n{Colors.BLUE}Running: Core store Vitest unit tests{Colors.NC}")
    result = subprocess.run(
        [
            "npx",
            "vitest",
            "run",
            "src/lib/stores/core/entityStore.test.ts",
            "src/lib/components/ui/select/optionFilter.test.ts",
            "src/lib/utils/__tests__/dateArrowStep.test.ts",
            "src/lib/utils/__tests__/dateOnly.test.ts",
            "src/lib/utils/__tests__/parseDecimalInput.test.ts",
            "src/lib/utils/__tests__/parseTypedDate.test.ts",
            "src/lib/utils/__tests__/requestConcurrency.test.ts",
            "src/lib/utils/__tests__/urlFilters.test.ts",
            "src/lib/utils/sync/__tests__/syncToastHelpers.test.ts",
            "src/lib/utils/core/__tests__/formatDecimal.test.ts",
            "src/lib/utils/core/__tests__/escapeHtml.test.ts",
            "src/lib/utils/core/__tests__/translateOr.test.ts",
            "src/lib/utils/core/__tests__/formatPercent.test.ts",
            "src/lib/utils/core/__tests__/positionKey.test.ts",
            "src/lib/utils/core/__tests__/finiteNumber.test.ts",
            "src/lib/utils/core/__tests__/formatAxisDate.test.ts",
            "src/lib/utils/core/__tests__/resizeWatcher.test.ts",
            "src/lib/utils/core/__tests__/clickOutside.test.ts",
            "src/lib/utils/core/__tests__/formatDateTime.test.ts",
            "src/lib/utils/core/__tests__/clearTimer.test.ts",
            "src/lib/utils/__tests__/text.test.ts",
            "src/lib/types/__tests__/safeAccessors.test.ts",
            "src/lib/utils/transactions/importDedup.test.ts",
            "src/lib/utils/transactions/importMerge.test.ts",
            "src/lib/utils/transactions/importCompare.test.ts",
            "src/lib/utils/transactions/resolveValidationMessage.test.ts",
            "src/lib/utils/transactions/resolveBrimNotice.test.ts",
            "src/lib/utils/transactions/eventTypes.test.ts",
            "src/lib/utils/transactions/signHintColor.test.ts",
            "src/lib/utils/transactions/importResolutionHelpers.test.ts",
            "src/lib/utils/transactions/importRowState.test.ts",
            "src/lib/utils/transactions/importDuplicateResolver.test.ts",
            "src/lib/utils/transactions/txFormFields.test.ts",
            "src/lib/components/charts/echartsTooltipHelpers.test.ts",
            "src/lib/components/charts/echartsAnimationConfig.test.ts",
            "src/lib/components/charts/echartsZoomPan.test.ts",
            "src/lib/components/charts/geographyMapHelpers.test.ts",
            "src/lib/components/charts/priceChartHelpers.test.ts",
            "src/lib/components/charts/candlestickChartHelpers.test.ts",
            "src/lib/components/charts/chartSignalsHelpers.test.ts",
            "src/lib/components/risk/riskAnalysisHelpers.test.ts",
            "src/lib/components/assets/providerProbe.test.ts",
            "src/lib/components/assets/assetIdentifiers.test.ts",
            "src/lib/components/assets/currencyBlocker.test.ts",
            "src/lib/components/assets/assetPayload.test.ts",
            "src/lib/components/assets/assetFormState.test.ts",
            "src/lib/components/assets/scheduleSerialization.test.ts",
            "src/lib/components/table/dataTableLogic.test.ts",
            "src/lib/components/brokers/lots/lotChartShared.test.ts",
            "src/lib/components/brokers/lots/lotWacPriceChartHelpers.test.ts",
            "src/lib/components/brokers/lots/lotComparisonChartHelpers.test.ts",
            "src/lib/components/brokers/lots/lotGanttChartHelpers.test.ts",
            "src/lib/components/brokers/lots/lotStateVisual.test.ts",
            "src/lib/components/brokers/lots/unifiedLotsTableHelpers.test.ts",
            "src/lib/components/brokers/lots/lotCustodyModalHelpers.test.ts",
            "src/lib/components/brokers/lots/lotsAnalysisHelpers.test.ts",
            "src/lib/components/brokers/lots/lotDataQualityHelpers.test.ts",
        ],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Core store Vitest unit tests - PASSED")
        return True

    print_error(f"Core store Vitest unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_component_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Svelte component unit tests (Vitest + jsdom).

    Kept separate from ``core-unit`` on purpose. These mount real ``.svelte``
    components in a simulated DOM, so they need the jsdom environment and the
    testing-library harness, and they cover a surface — the UI primitives — that
    E2E reaches only incidentally, if at all. Splitting them also means the two
    families can be run, timed and parallelised independently.
    """
    print(f"\n{Colors.BLUE}Running: Svelte component unit tests (jsdom){Colors.NC}")
    result = subprocess.run(
        [
            "npx",
            "vitest",
            "run",
            "src/lib/components/ui/date/CalendarMonth.test.ts",
            "src/lib/components/ui/date/SingleDatePicker.test.ts",
            "src/lib/components/ui/date/DateRangePicker.test.ts",
            "src/lib/components/ui/input/TagInput.test.ts",
            "src/lib/components/ui/select/SimpleSelect.test.ts",
            "src/lib/components/ui/select/SearchSelect.test.ts",
            "src/lib/components/ui/select/FxProviderSelect.test.ts",
            "src/lib/components/ui/data-editor/DataEditor.test.ts",
            "src/lib/components/ui/media/AssetPickerModal.test.ts",
            "src/lib/components/ui/media/ImageEditModal.test.ts",
            "src/lib/components/ui/modals/SyncModalBase.test.ts",
            "src/lib/components/ui/modals/PageSyncModal.test.ts",
            "src/lib/components/table/DataTableColumnFilter.test.ts",
            "src/lib/components/table/DataTable.test.ts",
            "src/lib/components/table/DataTablePagination.test.ts",
            "src/lib/components/assets/ScheduledInvestmentEditor.test.ts",
            "src/lib/components/assets/AssetModal.test.ts",
            "src/lib/components/assets/AssetSearchAutocomplete.test.ts",
            "src/lib/components/assets/AssetCurrencyChangeModal.test.ts",
            "src/lib/components/assets/ProviderComparisonModal.test.ts",
            "src/lib/components/assets/CellDateRange.test.ts",
            "src/lib/components/assets/ProviderAssignmentSection.test.ts",
            "src/lib/components/assets/AssetSyncModal.test.ts",
            "src/lib/components/fx/FxSyncModal.test.ts",
            "src/lib/components/files/FilePreviewModal.test.ts",
            "src/lib/components/transactions/modals/ImportWizardModal.test.ts",
            "src/lib/components/charts/MeasurePanel.test.ts",
        ],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Svelte component unit tests - PASSED")
        return True

    print_error(f"Svelte component unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_auth(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run auth E2E tests."""
    print_section("Frontend Auth Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("auth.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_settings(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run settings E2E tests."""
    print_section("Frontend Settings Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("settings.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_files(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run files E2E tests."""
    print_section("Frontend Files Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("files.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_files_destructive(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run files destructive-route E2E tests (single/bulk delete, failure, BRIM)."""
    print_section("Frontend Files Destructive Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("files-destructive.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_select(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run select components E2E tests."""
    print_section("Frontend Select Components Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("select-components.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_image_crop(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run image crop & media components E2E tests."""
    print_section("Frontend Image Crop & Media Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("image-crop.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_utilities(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run utilities API E2E tests."""
    print_section("Frontend Utilities API Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("utilities.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_tooltip(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run shared Tooltip component E2E tests (pinned hover/click model)."""
    print_section("Frontend Tooltip Component Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("tooltip-component.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_scheduler(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run scheduler settings E2E tests (admin: config modal, log modal, regression)."""
    print_section("Frontend Scheduler Settings Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("settings/scheduler.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_utility_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, coverage: bool = False) -> bool:
    """Run all frontend utility/component E2E tests."""
    from ._common import print_header
    print_header("Frontend Utility Tests (Playwright)")
    if _common.nothing_left_to_run("front-utility"):
        return _common.consolidated_verdict("front-utility")
    reset_setup_scope()
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    return _run_test_suite(
        suite_name="Frontend Utility Tests",
        tests=_get_category_tests_for_all("front-utility", verbose, ui=ui, headed=headed, debug=debug, coverage=coverage),
        verbose=verbose,
        header_msg=None,
        summary_title="Frontend Utility Test Summary",
        success_msg="All frontend utility tests passed! 🎉",
        resume=_common._RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all frontend utility test entries."""
    from ._common import add_test, make_category
    cat = make_category(
        help_text="Frontend utility & component E2E tests (auth, settings, files, select, image-crop)",
        description="""Frontend Utility & Component Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "auth", front_auth, name="Auth Tests", desc="Login, register, logout, language change", prereq="Test users created", tests="auth.spec.ts")
    add_test(cat, "core-unit", front_utility_unit, test_names=False, name="Core Store Unit Tests", desc="entityStore, option filter, date/decimal parsing, request concurrency, HTML escaping for hand-built markup, safe accessors for widened API unions, import-wizard dedup/merge/compare pure logic, URL filter round trip for DataTable deep links, sync toast variants for asset/FX results, chart helpers (echarts tooltip/animation/zoom-pan, geography map, price-chart & candlestick series/scale arithmetic, signal-problem formatting)", tests="src/lib/stores/core/entityStore.test.ts")
    add_test(cat, "component-unit", front_component_unit, test_names=False, name="Svelte Component Unit Tests", desc="UI primitives mounted in jsdom: CalendarMonth grid/states, SingleDatePicker typed/calendar seam, TagInput keyboard model, SimpleSelect keyboard/unavailable states, FxProviderSelect route picker, DataTableColumnFilter filter modes, DataTable sorting/paging/selection/row actions, ScheduledInvestmentEditor schedule payload round trip, ImportWizardModal shell/open-gating/close, MeasurePanel measure add/preview/summary table", tests="src/lib/components/ui/date/CalendarMonth.test.ts")
    add_test(cat, "settings", front_settings, name="Settings Tests", desc="User preferences, global settings (admin)", prereq="Login working", tests="settings.spec.ts")
    add_test(cat, "files", front_files, name="Files Tests", desc="Files page, tabs, URL filters", prereq="Login working", tests="files.spec.ts")
    add_test(cat, "files-destructive", front_files_destructive, name="Files Destructive Tests", desc="Single + bulk file delete, confirm/cancel, delete failure, BRIM delete + empty state (disposable rows, self-restoring)", prereq="Login working", tests="files-destructive.spec.ts")
    add_test(cat, "select", front_select, name="Select Components Tests", desc="SimpleSelect, SearchSelect, keyboard nav", prereq="Login working", tests="select-components.spec.ts")
    add_test(cat, "image-crop", front_image_crop, name="Image Crop & Media Tests", desc="ImageEditModal, AssetPicker, FileGrid, avatar", prereq="Login working", tests="image-crop.spec.ts")
    add_test(cat, "utilities", front_utilities, name="Utilities API E2E", desc="Currencies, countries, sectors API", prereq="Login working", tests="utilities.spec.ts")
    add_test(cat, "tooltip", front_tooltip, name="Tooltip Component Tests", desc="Pinned hover/click model: hover-only, click-to-pin, grace dismiss, click-outside", prereq="Login working", tests="tooltip-component.spec.ts")
    add_test(cat, "scheduler", front_scheduler, name="Scheduler Settings E2E", desc="ConfigModal, LogModal, status row, fetch_interval regression", prereq="Admin user + populated DB", tests="settings/scheduler.spec.ts")
    add_test(cat, "all", front_utility_all, test_names=False, name="All Frontend Utility Tests", desc="Run all utility/component E2E tests")
    registry["front-utility"] = cat
