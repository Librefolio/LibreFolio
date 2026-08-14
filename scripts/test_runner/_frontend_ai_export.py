"""Frontend AI Export unit and concern-based E2E tests."""

import subprocess

from . import _common
from ._common import PROJECT_ROOT, Colors, _get_category_tests_for_all, _run_test_suite, add_test, make_category, print_error, print_section, print_success
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright, reset_setup_scope

AI_EXPORT_UNIT_TEST_PATHS = (
    "src/lib/features/ai-export/__tests__/aiExportClient.test.ts",
    "src/lib/features/ai-export/__tests__/aiExportClipboard.test.ts",
    "src/lib/features/ai-export/__tests__/aiExportMemory.test.ts",
    "src/lib/features/ai-export/__tests__/aiExportOptions.test.ts",
    "src/lib/features/ai-export/__tests__/aiExportUi.test.ts",
    "src/lib/features/ai-export/__tests__/backendCatalogCompatibility.test.ts",
    "src/lib/features/ai-export/__tests__/catalogCompatibility.test.ts",
    "src/lib/features/ai-export/__tests__/drawdownContextCatalog.test.ts",
    "src/lib/features/ai-export/__tests__/promptRenderer.test.ts",
    "src/lib/features/ai-export/__tests__/publicCatalogContract.test.ts",
    "src/lib/features/ai-export/__tests__/snapshotDataRenderer.test.ts",
    "src/lib/features/ai-export/__tests__/safeSerialization.test.ts",
    "src/lib/components/charts/__tests__/timeSeriesAggregation.test.ts",
    "src/lib/components/charts/chartCoreHelpers.test.ts",
    "src/lib/charts/signals/__tests__/backendRenderer.test.ts",
    "src/lib/charts/signals/__tests__/backendTypes.test.ts",
    "src/lib/charts/signals/__tests__/catalogMapper.test.ts",
    "src/lib/charts/signals/__tests__/localSignalRegression.test.ts",
    "src/lib/charts/signals/__tests__/previewPolicy.test.ts",
    "src/lib/charts/signals/__tests__/requestResultMapper.test.ts",
    "src/lib/charts/signals/__tests__/schemaMapper.test.ts",
    "src/lib/charts/signals/__tests__/signalProblem.test.ts",
)

AI_EXPORT_E2E_SPECS = (
    "ai-export/ai-export-panel.spec.ts",
    "ai-export/ai-export-catalog.spec.ts",
    "ai-export/ai-export-memory.spec.ts",
    "ai-export/ai-export-contract.spec.ts",
)


def front_ai_export_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all AI Export and current signal Vitest files."""
    print_section("Frontend AI Export + Signal Unit Tests (Vitest)")
    cmd = ["npx", "vitest", "run", *AI_EXPORT_UNIT_TEST_PATHS]
    print(f"\n{Colors.BLUE}Running: AI Export + signal Vitest unit tests{Colors.NC}")
    print(f"Command:\n└─▶ $ cd frontend && {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", text=True)
        if result.returncode == 0:
            print_success("AI Export + signal Vitest unit tests - PASSED")
            return True
        print_error(f"AI Export + signal Vitest unit tests - FAILED (exit code: {result.returncode})")
        return False
    except Exception as exc:
        print_error(f"Vitest error: {exc}")
        return False


def _run_ai_export_e2e(specs: str | list[str], section: str, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run one or more concern-based AI Export Playwright specs."""
    print_section(section)
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    # Desktop only, like every other frontend category. These four specs were the single
    # exception, and it was an omission rather than a decision: `project=None` runs them on
    # desktop *and* mobile, doubling the work to verify a layout that is checked by hand.
    return _run_playwright(specs, ui=ui, headed=headed, debug=debug, project="desktop", test_names=test_names, coverage=coverage)


def front_ai_export_panel(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run AI Export panel behavior E2E tests."""
    return _run_ai_export_e2e(AI_EXPORT_E2E_SPECS[0], "Frontend AI Export Panel Tests", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_ai_export_catalog(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run AI Export catalog E2E tests."""
    return _run_ai_export_e2e(AI_EXPORT_E2E_SPECS[1], "Frontend AI Export Catalog Tests", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_ai_export_memory(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run AI Export contextual memory E2E tests."""
    return _run_ai_export_e2e(AI_EXPORT_E2E_SPECS[2], "Frontend AI Export Memory Tests", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_ai_export_contract(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run AI Export request and clipboard contract E2E tests."""
    return _run_ai_export_e2e(AI_EXPORT_E2E_SPECS[3], "Frontend AI Export Contract Tests", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_ai_export_cutover(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Compatibility alias: run all four AI Export E2E concerns."""
    return _run_ai_export_e2e(list(AI_EXPORT_E2E_SPECS), "Frontend AI Export Cutover Tests", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_ai_export_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all AI Export frontend tests."""
    if _common.nothing_left_to_run("front-ai-export"):
        return _common.consolidated_verdict("front-ai-export")
    reset_setup_scope()
    return _run_test_suite(
        suite_name="All AI Export Tests (Unit + Concern-Based E2E)",
        tests=_get_category_tests_for_all("front-ai-export", verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage),
        verbose=verbose,
        summary_title="AI Export Test Summary",
        success_msg="All AI Export tests passed! 🎉",
        resume=_common._RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register frontend AI Export test entries."""
    cat = make_category(
        help_text="Frontend AI Export unit and concern-based E2E tests",
        description="""Frontend AI Export Tests\n\nOptions: --ui, --headed, --debug""",
    )
    add_test(
        cat,
        "unit",
        front_ai_export_unit,
        test_names=False,
        name="AI Export + Signal Unit Tests",
        desc="AI Export runtime, serialization, and Signal Vitest files",
        tests="explicit Vitest files",
    )
    add_test(
        cat,
        "panel",
        front_ai_export_panel,
        name="AI Export Panel Tests",
        desc="Panel selectors, focus, close behavior, portal, layout, help, and warning flow",
        tests=AI_EXPORT_E2E_SPECS[0],
        in_all=False,  # run by "cutover" in a single Playwright invocation
    )
    add_test(
        cat,
        "catalog",
        front_ai_export_catalog,
        name="AI Export Catalog Tests",
        desc="Exact V1 Dataset/Analysis IDs, domain visibility, labels, and icons",
        tests=AI_EXPORT_E2E_SPECS[1],
        in_all=False,  # run by "cutover" in a single Playwright invocation
    )
    add_test(
        cat,
        "memory",
        front_ai_export_memory,
        name="AI Export Memory Tests",
        desc="10-minute session drafts, login reset, canonical FX, periods, detail, and notes",
        tests=AI_EXPORT_E2E_SPECS[2],
        in_all=False,  # run by "cutover" in a single Playwright invocation
    )
    add_test(
        cat,
        "contract",
        front_ai_export_contract,
        name="AI Export Contract Tests",
        desc="V1 public contracts and Dataset/Analysis clipboard boundaries",
        tests=AI_EXPORT_E2E_SPECS[3],
        in_all=False,  # run by "cutover" in a single Playwright invocation
    )
    add_test(
        cat,
        "cutover",
        front_ai_export_cutover,
        name="AI Export Cutover Tests",
        desc="Compatibility alias running panel, catalog, memory, and contract E2E specs",
        tests=", ".join(AI_EXPORT_E2E_SPECS),
    )
    add_test(cat, "all", front_ai_export_all, test_names=False, name="All AI Export Tests", desc="Run unit tests, then all four E2E concerns")
    registry["front-ai-export"] = cat
