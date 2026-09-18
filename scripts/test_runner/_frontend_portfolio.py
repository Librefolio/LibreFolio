"""Frontend Portfolio tests: data quality, broker icons, and risk analysis."""

import subprocess

from . import _common
from ._common import Colors, _get_category_tests_for_all, _run_test_suite, print_error, print_section, print_success
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


def front_portfolio_dashboard(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run dashboard chart + view-matrix E2E tests (PositionsPanel 2x2, AllocationPanel)."""
    print_section("Frontend Portfolio Dashboard Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("portfolio/dashboard.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


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


def front_portfolio_allocation_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run allocation chart colour-hierarchy unit tests (Vitest)."""
    print(f"\n{Colors.BLUE}Running: Allocation colour hierarchy Vitest unit tests{Colors.NC}")
    result = subprocess.run(
        ["npx", "vitest", "run", "src/lib/utils/__tests__/colors.test.ts", "src/lib/components/charts/__tests__/allocationHierarchy.test.ts"],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Allocation colour hierarchy Vitest unit tests - PASSED")
        return True

    print_error(f"Allocation colour hierarchy Vitest unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_portfolio_risk(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run portfolio-level Risk analysis E2E tests (Dashboard + Broker Detail)."""
    print_section("Frontend Risk Analysis Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("portfolio/risk-analysis.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_portfolio_risk_lab(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset Global risk laboratory E2E tests."""
    print_section("Frontend Asset Global Risk Lab Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("portfolio/risk-lab.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_portfolio_risk_asset_detail(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """
    Run the Asset Detail risk net.

    Asset Detail is parked and must survive the risk redesign unchanged: these
    two tests are what proves it. A red here means the page moved — investigate
    the page, never the assertion.
    """
    print_section("Frontend Risk Asset Detail Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("portfolio/risk-asset-detail.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


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
    add_test(cat, "dashboard", front_portfolio_dashboard, name="Dashboard Chart Tests", desc="PositionsPanel 2x2 view matrix (treemap + perf chart), toggle persistence, AllocationPanel now/history, loading state", tests="portfolio/dashboard.spec.ts")
    add_test(cat, "risk-unit", front_portfolio_risk_unit, test_names=False, name="Risk Store Unit Tests", desc="Request-key cache, account isolation, invalidation and capability checks", tests="src/lib/stores/risk/riskStore.test.ts")
    add_test(cat, "store-unit", front_portfolio_store_unit, test_names=False, name="Portfolio Store Unit Tests", desc="portfolioStore + portfolioMutation vitest units", tests="src/lib/stores/portfolio/portfolioStore.test.ts")
    add_test(cat, "allocation-unit", front_portfolio_allocation_unit, test_names=False, name="Allocation Colour Hierarchy Unit Tests", desc="hexToHsl round-trip on the real palettes, subtype grouping/ordering, measured shade contrast, legacy ordering pin", tests="src/lib/components/charts/__tests__/allocationHierarchy.test.ts")
    add_test(cat, "risk", front_portfolio_risk, name="Risk Analysis Tests", desc="Portfolio-level risk on Dashboard and Broker Detail", tests="portfolio/risk-analysis.spec.ts")
    add_test(cat, "risk-lab", front_portfolio_risk_lab, name="Asset Global Risk Lab Tests", desc="Asset-set laboratory: the no-money rule asserted by stubbing money in, D19 opening selection by branch rather than by size, bulk actions against filtered candidates, filters that keep their own option clickable, correlation pairs keyed by asset id and matrix ordering", tests="portfolio/risk-lab.spec.ts")
    add_test(cat, "risk-asset-detail", front_portfolio_risk_asset_detail, name="Risk Asset Detail Net", desc="Asset Detail is parked and must stay identical — these two tests are the proof, not a maintenance chore", tests="portfolio/risk-asset-detail.spec.ts")
    add_test(cat, "all", front_portfolio_all, test_names=False, name="All Portfolio Tests", desc="Run all Portfolio frontend tests")
    registry["front-portfolio"] = cat
