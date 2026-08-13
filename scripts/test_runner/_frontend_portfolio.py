"""Frontend Portfolio tests: data quality, broker icons, and risk analysis."""

import subprocess

from . import _common
from ._common import _get_category_tests_for_all, Colors, _run_test_suite, print_error, print_section, print_success
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright, reset_setup_scope


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


def front_portfolio_store_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Portfolio store unit tests (Vitest)."""
    print(f"\n{Colors.BLUE}Running: Portfolio store Vitest unit tests{Colors.NC}")
    result = subprocess.run(
        ["npx", "vitest", "run", "src/lib/stores/portfolio/portfolioStore.test.ts", "src/lib/stores/portfolio/portfolioMutation.test.ts"],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Portfolio store Vitest unit tests - PASSED")
        return True

    print_error(f"Portfolio store Vitest unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_portfolio_risk_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Risk store unit tests."""
    print(f"\n{Colors.BLUE}Running: Risk store Vitest unit tests{Colors.NC}")
    result = subprocess.run(
        ["npx", "vitest", "run", "src/lib/stores/risk/riskStore.test.ts"],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Risk store Vitest unit tests - PASSED")
        return True

    print_error(f"Risk store Vitest unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_portfolio_risk(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Risk analysis functional E2E tests."""
    print_section("Frontend Risk Analysis Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("portfolio/risk-analysis.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_portfolio_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all Portfolio frontend tests."""
    if _common.nothing_left_to_run("front-portfolio"):
        return _common.consolidated_verdict("front-portfolio")
    reset_setup_scope()
    return _run_test_suite(
        suite_name="All Portfolio Frontend Tests",
        tests=_get_category_tests_for_all("front-portfolio", verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage),
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
    add_test(cat, "risk-unit", front_portfolio_risk_unit, test_names=False, name="Risk Store Unit Tests", desc="Request-key cache, account isolation, invalidation and capability checks", tests="src/lib/stores/risk/riskStore.test.ts")
    add_test(cat, "store-unit", front_portfolio_store_unit, test_names=False, name="Portfolio Store Unit Tests", desc="portfolioStore + portfolioMutation vitest units", tests="src/lib/stores/portfolio/portfolioStore.test.ts")
    add_test(cat, "risk", front_portfolio_risk, name="Risk Analysis Tests", desc="Asset, asset-set and portfolio Risk UI integration", tests="portfolio/risk-analysis.spec.ts")
    add_test(cat, "all", front_portfolio_all, test_names=False, name="All Portfolio Tests", desc="Run all Portfolio frontend tests")
    registry["front-portfolio"] = cat
