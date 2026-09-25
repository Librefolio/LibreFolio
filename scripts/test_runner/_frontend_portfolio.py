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



def front_portfolio_risk_benchmark_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Risk benchmark store unit tests."""
    print(f"\n{Colors.BLUE}Running: Risk benchmark store Vitest unit tests{Colors.NC}")
    result = subprocess.run(
        ["npx", "vitest", "run", "src/lib/stores/risk/riskBenchmarkStore.test.ts"],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Risk benchmark store Vitest unit tests - PASSED")
        return True

    print_error(f"Risk benchmark store Vitest unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
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


def front_portfolio_risk_request_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Risk request-builder unit tests."""
    print(f"\n{Colors.BLUE}Running: Risk request builder Vitest unit tests{Colors.NC}")
    result = subprocess.run(
        ["npx", "vitest", "run", "src/lib/risk/simulationParameters.test.ts", "src/lib/risk/stressBuckets.test.ts"],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Risk request builder Vitest unit tests - PASSED")
        return True

    print_error(f"Risk request builder Vitest unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_portfolio_allocation_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run allocation chart colour-hierarchy unit tests (Vitest)."""
    print(f"\n{Colors.BLUE}Running: Allocation colour hierarchy Vitest unit tests{Colors.NC}")
    result = subprocess.run(
        ["npx", "vitest", "run", "src/lib/utils/__tests__/colors.test.ts", "src/lib/components/charts/__tests__/allocationHierarchy.test.ts", "src/lib/components/charts/__tests__/allocationRings.test.ts", "src/lib/components/charts/__tests__/allocationFamily.test.ts"],
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


def front_portfolio_risk_levels_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the four-level risk UI pure-logic unit tests."""
    print(f"\n{Colors.BLUE}Running: Risk levels Vitest unit tests{Colors.NC}")
    result = subprocess.run(
        ["npx", "vitest", "run", "src/lib/components/risk/levels/levelHelpers.test.ts", "src/lib/components/risk/levels/levelMetadata.test.ts", "src/lib/components/risk/levels/l1/l1Helpers.test.ts", "src/lib/components/risk/levels/l3Helpers.test.ts", "src/lib/components/risk/levels/simulationProvenance.test.ts", "src/lib/components/risk/levels/l4/simulationModes.test.ts", "src/lib/components/risk/levels/l4/driftUncertainty.test.ts", "src/lib/components/risk/levels/l4/scenarioHelpers.test.ts", "src/lib/components/risk/levels/partialNotice.test.ts"],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Risk levels Vitest unit tests - PASSED")
        return True

    print_error(f"Risk levels Vitest unit tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_portfolio_risk_levels_component(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the four-level risk UI component tests (Vitest + jsdom mount)."""
    print(f"\n{Colors.BLUE}Running: Risk levels component Vitest tests{Colors.NC}")
    result = subprocess.run(
        ["npx", "vitest", "run", "src/lib/components/risk/levels/l4/L4Replay.test.ts", "src/lib/components/risk/levels/RiskPartialNotice.test.ts"],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Risk levels component Vitest tests - PASSED")
        return True

    print_error(f"Risk levels component Vitest tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_portfolio_risk_frame_component(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the legacy risk result frame component tests (Vitest + jsdom mount)."""
    print(f"\n{Colors.BLUE}Running: Risk result frame component Vitest tests{Colors.NC}")
    result = subprocess.run(
        ["npx", "vitest", "run", "src/lib/components/risk/RiskResultFrame.test.ts"],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Risk result frame component Vitest tests - PASSED")
        return True

    print_error(f"Risk result frame component Vitest tests - FAILED (exit code: {result.returncode})")
    if not verbose:
        print(result.stdout.decode() if result.stdout else "")
        print(result.stderr.decode() if result.stderr else "")
    return False


def front_portfolio_risk_controller_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Risk panel controller unit tests."""
    print(f"\n{Colors.BLUE}Running: Risk panel controller Vitest unit tests{Colors.NC}")
    result = subprocess.run(
        ["npx", "vitest", "run", "src/lib/stores/risk/riskPanelController.test.ts"],
        cwd="frontend",
        capture_output=not verbose,
    )
    if result.returncode == 0:
        print_success("Risk panel controller Vitest unit tests - PASSED")
        return True

    print_error(f"Risk panel controller Vitest unit tests - FAILED (exit code: {result.returncode})")
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
    add_test(cat, "risk-request-unit", front_portfolio_risk_request_unit, test_names=False, name="Risk Request Builder Unit Tests", desc="What the request actually carries: the simulation process is chosen by the caller rather than hard-coded, each mode carries its own seed field and forbids the other one, and the legacy aliases keep their documented geometric-Brownian default; the stress editor and the uniform shock cover every AssetType the backend knows, derived from the enum rather than listed by hand", tests="src/lib/risk/simulationParameters.test.ts, src/lib/risk/stressBuckets.test.ts")
    add_test(cat, "risk-benchmark-unit", front_portfolio_risk_benchmark_unit, test_names=False, name="Risk Benchmark Store Unit Tests", desc="One benchmark shared by every scope: user scoping, reload survival, corrupt-value rejection", tests="src/lib/stores/risk/riskBenchmarkStore.test.ts")
    add_test(cat, "risk-controller-unit", front_portfolio_risk_controller_unit, test_names=False, name="Risk Panel Controller Unit Tests", desc="Signature invalidation with in-flight preservation, generation guards, catalog error vs pending", tests="src/lib/stores/risk/riskPanelController.test.ts")
    add_test(cat, "risk-levels-component", front_portfolio_risk_levels_component, test_names=False, name="Risk Levels Component Tests", desc="L4 historical replay mounted in jsdom over a real panel controller: the composition total is withheld rather than degraded to a dash when the scope carries no aggregate return (and is still stated when a weighted replay came out flat at 0.0), and the audit sentence names the treatment the payload actually carries — the omitted-from-replay wording as soon as one exclusion was omitted, the carried-at-zero-return wording when every exclusion was a zero-return residual, when nothing was excluded, and when the payload carries no excluded list at all. Which of the two keys was selected is proved by resolving both from the shipped catalogue instead of pinning a translated sentence; the one partial notice above the levels, mounted in jsdom: nothing when there is nothing to disclose, the partial title when something came back partial and the notes title when only warnings on whole results are left (both keys guarded in the four catalogues), each measurement named by its label, else its catalogue name, else its raw code, joined by a middle dot, each reason once with its arity, and never a key on screen", tests="src/lib/components/risk/levels/l4/L4Replay.test.ts, src/lib/components/risk/levels/RiskPartialNotice.test.ts")
    add_test(cat, "risk-frame-component", front_portfolio_risk_frame_component, test_names=False, name="Risk Result Frame Component Tests", desc="The legacy result frame Asset Detail mounts once per analytic, rendered in jsdom: each warning is worded through its own i18n key formatted with the names, counts, dimension and covered share it carries — never the raw ICU source a code-named key printed when it was called without values, never the generic sentence when the backend sent a reason key such as assets_excluded_missing_price — a warning without a key, or with a key this build does not ship, shows the backend sentence instead of a raw key, the generic sentence is kept only for a warning with neither, and across every risk.warnings sentence with arguments (read off en.json at test time, values built from each sentence's own ICU arguments) a warning is worded through its key once its values arrive and shows the backend sentence when they do not, never a brace or a key; the error branch still words its code through risk.errors.<code> with the state sentence as fallback. Expected sentences are resolved from the shipped catalogue through the same formatter instead of pinned", tests="src/lib/components/risk/RiskResultFrame.test.ts")
    add_test(cat, "risk-levels-unit", front_portfolio_risk_levels_unit, test_names=False, name="Risk Levels Unit Tests", desc="Four-level pure logic: L1 scale of harm (CVaR leads, omission never zero-fill, required-recovery asymmetry), L1 tail readings (underwater curve pre-scaled to percent because the chart converts nothing, VaR cut located by half-open inequality and kept when it is exactly zero, worst-realization null honoured as a refusal rather than zero-filled), L2 weight-vs-contribution divergence ordering with negative contributions, L3 figure collection plus the perimeter choice (current composition preferred, historical fallback, perimeter read from the payload even when it contradicts the wave) and the risk/return points (portfolio sized as the whole, assets by un-renormalized weight, cash never plotted), L4 simulation modes with the seed each one carries, L4 drift uncertainty applied to the median and the band it is compared against, L4 simulation provenance read from the payload instead of asserted in a translation string, L4 scenario presets and tornado ordering by signed damage, level provenance collapsed by agreement so a disagreement about the window splits instead of being represented by one analytic, and catalogue values degraded to the backend token rather than to a printed i18n key; backend warnings worded through their own i18n key and params (the catalogue sentence when it formats, the backend sentence otherwise — never the key, never raw ICU braces from a missing value, checked for every risk.warnings sentence with arguments read off en.json at test time, with plausible values and without them; a list the backend did not join reads like one it did, any other non-scalar value is left out rather than printed) and reasons deduplicated by the worded sentence, while the one-argument call keeps its verbatim output byte for byte; the one partial notice above L1–L3 (decision of 24/09): one entry per instance with the first one kept, so historical_kpi read by L1 and L3 is counted once and its warning once, only partial results named (per instance, the two VaR horizons told apart by their labels), warnings deduplicated by sentence with their arity, level health reduced to what did not come back at all, and analytic names keyed by the camelCase rule for every name the catalogue ships", tests="src/lib/components/risk/levels/levelHelpers.test.ts, src/lib/components/risk/levels/levelMetadata.test.ts, src/lib/components/risk/levels/l1/l1Helpers.test.ts, src/lib/components/risk/levels/l3Helpers.test.ts, src/lib/components/risk/levels/simulationProvenance.test.ts, src/lib/components/risk/levels/l4/simulationModes.test.ts, src/lib/components/risk/levels/l4/driftUncertainty.test.ts, src/lib/components/risk/levels/l4/scenarioHelpers.test.ts, src/lib/components/risk/levels/partialNotice.test.ts")
    add_test(cat, "store-unit", front_portfolio_store_unit, test_names=False, name="Portfolio Store Unit Tests", desc="portfolioStore + portfolioMutation vitest units", tests="src/lib/stores/portfolio/portfolioStore.test.ts")
    add_test(cat, "allocation-unit", front_portfolio_allocation_unit, test_names=False, name="Allocation Colour Hierarchy Unit Tests", desc="hexToHsl round-trip on the real palettes, subtype grouping/ordering, measured shade contrast, legacy ordering pin; two-ring type donut: each subtype inside the base type it contains, a lone subtype shaded by rank, rings aligned by construction, fast path refreshing both series; families by vehicle (every ETF subtype in the ETF family), a legend click hiding a family on both rings, the composite tooltip icon", tests="src/lib/components/charts/__tests__/allocationHierarchy.test.ts, src/lib/components/charts/__tests__/allocationRings.test.ts, src/lib/components/charts/__tests__/allocationFamily.test.ts")
    add_test(cat, "risk", front_portfolio_risk, name="Risk Analysis Tests", desc="Portfolio-level risk on Dashboard and Broker Detail", tests="portfolio/risk-analysis.spec.ts")
    add_test(cat, "risk-lab", front_portfolio_risk_lab, name="Asset Global Risk Lab Tests", desc="Asset-set laboratory: the no-money rule asserted by stubbing money in, D19 opening selection by branch rather than by size, bulk actions against filtered candidates, filters that keep their own option clickable, correlation pairs keyed by asset id and matrix ordering", tests="portfolio/risk-lab.spec.ts")
    add_test(cat, "risk-asset-detail", front_portfolio_risk_asset_detail, name="Risk Asset Detail Net", desc="Asset Detail is parked and must stay identical — these two tests are the proof, not a maintenance chore", tests="portfolio/risk-asset-detail.spec.ts")
    add_test(cat, "all", front_portfolio_all, test_names=False, name="All Portfolio Tests", desc="Run all Portfolio frontend tests")
    registry["front-portfolio"] = cat
