"""Frontend utility & component E2E tests: auth, settings, files, select, image-crop, utilities."""

import subprocess

from . import _common
from ._common import PROJECT_ROOT, Colors, _run_test_suite, print_error, print_section, print_success
from ._frontend_common import _ensure_frontend_build, _ensure_test_users, _run_playwright


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
    if not _ensure_frontend_build(): return False
    if not _ensure_test_users(): return False
    specs = ["auth.spec.ts", "settings.spec.ts", "files.spec.ts", "select-components.spec.ts", "image-crop.spec.ts", "settings/scheduler.spec.ts"]
    return _run_test_suite(
        suite_name="Frontend Utility Tests",
        tests=[(spec.replace('.spec.ts', '').title(), lambda s=spec: _run_playwright(s, ui=ui, headed=headed, debug=debug, coverage=coverage)) for spec in specs],
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
    add_test(cat, "settings", front_settings, name="Settings Tests", desc="User preferences, global settings (admin)", prereq="Login working", tests="settings.spec.ts")
    add_test(cat, "files", front_files, name="Files Tests", desc="Files page, tabs, URL filters", prereq="Login working", tests="files.spec.ts")
    add_test(cat, "select", front_select, name="Select Components Tests", desc="SimpleSelect, SearchSelect, keyboard nav", prereq="Login working", tests="select-components.spec.ts")
    add_test(cat, "image-crop", front_image_crop, name="Image Crop & Media Tests", desc="ImageEditModal, AssetPicker, FileGrid, avatar", prereq="Login working", tests="image-crop.spec.ts")
    add_test(cat, "utilities", front_utilities, name="Utilities API E2E", desc="Currencies, countries, sectors API", prereq="Login working", tests="utilities.spec.ts")
    add_test(cat, "scheduler", front_scheduler, name="Scheduler Settings E2E", desc="ConfigModal, LogModal, status row, fetch_interval regression", prereq="Admin user + populated DB", tests="settings/scheduler.spec.ts")
    add_test(cat, "all", front_utility_all, test_names=False, name="All Frontend Utility Tests", desc="Run all utility/component E2E tests")
    registry["front-utility"] = cat
