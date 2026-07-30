"""Frontend AI Export unit and hard-cutover E2E tests."""

import subprocess

from . import _common
from ._common import PROJECT_ROOT, Colors, _run_test_suite, add_test, make_category, print_error, print_section, print_success
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright

AI_EXPORT_UNIT_TEST_PATHS = (
    "src/lib/features/ai-export/__tests__/aiExportClient.test.ts",
    "src/lib/features/ai-export/__tests__/aiExportClipboard.test.ts",
    "src/lib/features/ai-export/__tests__/aiExportMemory.test.ts",
    "src/lib/features/ai-export/__tests__/aiExportOptions.test.ts",
    "src/lib/features/ai-export/__tests__/aiExportUi.test.ts",
    "src/lib/features/ai-export/__tests__/backendCatalogCompatibility.test.ts",
    "src/lib/features/ai-export/__tests__/catalogCompatibility.test.ts",
    "src/lib/features/ai-export/__tests__/promptRenderer.test.ts",
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


def front_ai_export_cutover(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the focused cross-domain AI Export cutover E2E test."""
    print_section("Frontend AI Export Cutover Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("ai-export.spec.ts", ui=ui, headed=headed, debug=debug, project=None, test_names=test_names, coverage=coverage)


def front_ai_export_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all AI Export frontend tests."""
    return _run_test_suite(
        suite_name="All AI Export Tests (Unit + Cross-Domain E2E)",
        tests=[
            ("AI Export + Signal Unit (Vitest)", lambda: front_ai_export_unit(verbose=verbose)),
            ("AI Export Cross-Domain E2E", lambda: front_ai_export_cutover(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
        ],
        verbose=verbose,
        summary_title="AI Export Test Summary",
        success_msg="All AI Export tests passed! 🎉",
        resume=_common._RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register frontend AI Export test entries."""
    cat = make_category(
        help_text="Frontend AI Export unit and cross-domain cutover E2E tests",
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
        "cutover",
        front_ai_export_cutover,
        name="AI Export Cutover Tests",
        desc="Live dashboard, asset, FX, and broker snapshot/copy contract",
        tests="ai-export.spec.ts",
    )
    add_test(cat, "all", front_ai_export_all, test_names=False, name="All AI Export Tests", desc="Run unit tests, then cross-domain E2E")
    registry["front-ai-export"] = cat
