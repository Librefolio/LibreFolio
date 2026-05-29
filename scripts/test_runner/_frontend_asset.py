"""Frontend Asset E2E tests: list, detail, modal, data editor, classification."""

from ._common import _RESUME_MODE, _run_test_suite, print_section
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright


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


def front_asset_event_delete(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset event delete E2E tests."""
    print_section("Frontend Asset Event Delete Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("assets/asset-event-delete.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all Asset E2E tests."""
    return _run_test_suite(
        suite_name="All Asset Tests (E2E)",
        tests=[
            ("Asset List Page", lambda: front_asset_list(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("Asset Detail Page", lambda: front_asset_detail(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("Asset Modal", lambda: front_asset_modal(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("Asset Data Editor", lambda: front_asset_data_editor(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("Asset Classification", lambda: front_asset_classification(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("Asset Event Delete", lambda: front_asset_event_delete(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
        ],
        verbose=verbose,
        header_msg="All Asset Tests (E2E)",
        summary_title="Asset Test Summary",
        success_msg="All Asset tests passed! 🎉",
        resume=_RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all frontend asset test entries."""
    from ._common import add_test, make_category
    cat = make_category(
        help_text="Frontend Asset E2E tests (list, detail, modal, classification)",
        description="""Frontend Asset Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "asset-list", front_asset_list, name="Asset List Page", desc="List page navigation, cards/table, filters", tests="assets/asset-list.spec.ts")
    add_test(cat, "asset-detail", front_asset_detail, name="Asset Detail Page", desc="Detail chart, panels, sync, edit", tests="assets/asset-detail.spec.ts")
    add_test(cat, "asset-modal", front_asset_modal, name="Asset Modal", desc="Create/edit modal, provider, distributions", tests="assets/asset-modal.spec.ts")
    add_test(cat, "asset-data-editor", front_asset_data_editor, name="Asset Data Editor", desc="Prices/Events tabs, CSV import", tests="assets/asset-data-editor.spec.ts")
    add_test(cat, "asset-classification", front_asset_classification, name="Asset Classification", desc="Distribution editors round-trip (geo, sector)", tests="assets/asset-classification.spec.ts")
    add_test(cat, "asset-event-delete", front_asset_event_delete, name="Asset Event Delete", desc="Delete asset events flow", tests="assets/asset-event-delete.spec.ts")
    add_test(cat, "all", front_asset_all, test_names=False, name="All Asset Tests", desc="Run all Asset E2E tests")
    registry["front-asset"] = cat
