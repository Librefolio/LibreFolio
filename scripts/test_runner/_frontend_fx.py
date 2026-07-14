"""Frontend FX E2E & unit tests: list, detail, add-pair, editor, sync, API, settings."""

import subprocess

from . import _common
from ._common import PROJECT_ROOT, Colors, _run_test_suite, print_error, print_section, print_success
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright


def front_fx_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX/store unit tests (Vitest)."""
    print_section("Frontend FX Unit Tests (Vitest)")
    cmd = [
        "npx",
        "vitest",
        "run",
        "src/lib/stores/__tests__/EditBuffer.test.ts",
        "src/lib/stores/__tests__/TimeSeriesStore.test.ts",
        "src/lib/stores/__tests__/fxStoreRegistry.test.ts",
    ]
    print(f"\n{Colors.BLUE}Running: FX/store Vitest unit tests{Colors.NC}")
    print(f"Command:\n└─▶ $ cd frontend && {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", text=True)
        if result.returncode == 0:
            print_success("FX/store Vitest unit tests - PASSED")
            return True
        else:
            print_error(f"FX/store Vitest unit tests - FAILED (exit code: {result.returncode})")
            return False
    except Exception as e:
        print_error(f"Vitest error: {e}")
        return False


def front_fx_list(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX list page E2E tests."""
    print_section("Frontend FX List Page Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("fx/fx-list.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_detail(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX detail page E2E tests."""
    print_section("Frontend FX Detail Page Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("fx/fx-detail.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_add_pair(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX add pair modal E2E tests."""
    print_section("Frontend FX Add Pair Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("fx/fx-add-pair.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_editor(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX data editor E2E tests."""
    print_section("Frontend FX Data Editor Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("fx/fx-data-editor.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_csv_import(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX CSV import modal E2E tests."""
    print_section("Frontend FX CSV Import Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("fx/fx-csv-import.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_sync(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX sync modal E2E tests."""
    print_section("Frontend FX Sync Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("fx/fx-sync.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_api(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX API route E2E tests."""
    print_section("Frontend FX API Route Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("fx/fx-api.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_settings(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX chart settings E2E tests."""
    print_section("Frontend FX Chart Settings Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("fx/fx-chart-settings.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all FX tests (unit + E2E)."""
    return _run_test_suite(
        suite_name="All FX Tests (Unit + E2E)",
        tests=[
            ("FX Unit (Vitest)", lambda: front_fx_unit(verbose=verbose)),
            ("FX List Page", lambda: front_fx_list(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX Add Pair Modal", lambda: front_fx_add_pair(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX Detail Page", lambda: front_fx_detail(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX Data Editor", lambda: front_fx_editor(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX Sync Modal", lambda: front_fx_sync(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX API Routes", lambda: front_fx_api(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX Chart Settings", lambda: front_fx_settings(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
        ],
        verbose=verbose,
        header_msg="All FX Tests (Unit + E2E)",
        summary_title="FX Test Summary",
        success_msg="All FX tests passed! 🎉",
        resume=_common._RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all frontend FX test entries."""
    from ._common import add_test, make_category
    cat = make_category(
        help_text="Frontend FX E2E & unit tests",
        description="""Frontend FX Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "fx-unit", front_fx_unit, test_names=False, name="FX Unit Tests", desc="Vitest unit tests: EditBuffer, TimeSeriesStore, fxStoreRegistry", tests="vitest")
    add_test(cat, "fx-list", front_fx_list, name="FX List Page", desc="List page navigation, cards, filters", tests="fx/fx-list.spec.ts")
    add_test(cat, "fx-detail", front_fx_detail, name="FX Detail Page", desc="Detail page chart, panels, swap", tests="fx/fx-detail.spec.ts")
    add_test(cat, "fx-add-pair", front_fx_add_pair, name="FX Add Pair", desc="Add pair modal, validation", tests="fx/fx-add-pair.spec.ts")
    add_test(cat, "fx-editor", front_fx_editor, name="FX Data Editor", desc="Inline editing, save, cancel", tests="fx/fx-data-editor.spec.ts")
    add_test(cat, "fx-csv-import", front_fx_csv_import, name="FX CSV Import", desc="CSV upload, preview, import", tests="fx/fx-csv-import.spec.ts")
    add_test(cat, "fx-sync", front_fx_sync, name="FX Sync Modal", desc="Sync modal, providers, results", tests="fx/fx-sync.spec.ts")
    add_test(cat, "fx-api", front_fx_api, name="FX API Routes", desc="API routes via Playwright", tests="fx/fx-api.spec.ts")
    add_test(cat, "fx-settings", front_fx_settings, name="FX Chart Settings", desc="Chart interval, granularity", tests="fx/fx-chart-settings.spec.ts")
    add_test(cat, "all", front_fx, test_names=False, name="All FX Tests", desc="Run all FX tests (unit + E2E)")
    registry["front-fx"] = cat
