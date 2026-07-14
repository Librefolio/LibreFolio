"""Frontend Portfolio E2E tests: dashboard banners, broker icons, asset detail, FX detail."""

from . import _common
from ._common import _run_test_suite, print_section
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright


def front_portfolio_banners(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run DataQualityBanner E2E tests (dashboard + asset detail + FX detail)."""
    print_section("Frontend Portfolio DataQualityBanner Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("portfolio/data-quality-banners.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_portfolio_broker_icons(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run dashboard broker icon fallback E2E tests."""
    print_section("Frontend Portfolio Broker Icon Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("portfolio/broker-icons.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_portfolio_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all Portfolio frontend tests."""
    return _run_test_suite(
        suite_name="All Portfolio Frontend Tests",
        tests=[
            ("DataQualityBanner", lambda: front_portfolio_banners(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("BrokerIcons", lambda: front_portfolio_broker_icons(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
        ],
        verbose=verbose,
        header_msg="All Portfolio Frontend Tests",
        summary_title="Portfolio Frontend Test Summary",
        success_msg="All Portfolio frontend tests passed! 🎉",
        resume=_common._RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all frontend portfolio test entries."""
    from ._common import add_test, make_category
    cat = make_category(
        help_text="Frontend Portfolio E2E tests (dashboard banners, broker icons, asset detail, FX detail)",
        description="""Frontend Portfolio Tests\n\nOptions: --ui, --headed, --debug""")
    add_test(cat, "banners", front_portfolio_banners, name="DataQualityBanner Tests", desc="Banner component: dashboard grouped, asset/FX flat mode", tests="portfolio/data-quality-banners.spec.ts")
    add_test(cat, "broker-icons", front_portfolio_broker_icons, name="Broker Icon Tests", desc="Dashboard positions broker fallback chain", tests="portfolio/broker-icons.spec.ts")
    add_test(cat, "all", front_portfolio_all, test_names=False, name="All Portfolio Tests", desc="Run all Portfolio frontend tests")
    registry["front-portfolio"] = cat
