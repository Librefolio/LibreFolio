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


def front_portfolio_stale_price_banner(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the STALE_PRICE dashboard banner E2E test (D8) on the desktop project, the runner default."""
    print_section("Frontend Portfolio Stale Price Banner Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("portfolio/stale-price-banner.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_portfolio_broker_filter_label(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the dashboard broker-filter label E2E test (K step 15, item b) on the desktop project, the runner default."""
    print_section("Frontend Portfolio Broker Filter Label Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("portfolio/dashboard-broker-filter-label.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


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


def front_portfolio_privacy_masking(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the privacy-masking E2E tests on desktop and mobile — the header toggle exists on both."""
    print_section("Frontend Portfolio Privacy Masking Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("portfolio/privacy-masking.spec.ts", ui=ui, headed=headed, debug=debug, project="", test_names=test_names, coverage=coverage)


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
        ["npx", "vitest", "run", "src/lib/utils/__tests__/colors.test.ts", "src/lib/components/charts/__tests__/allocationHierarchy.test.ts", "src/lib/components/charts/__tests__/allocationRings.test.ts", "src/lib/components/charts/AllocationPieChart.test.ts", "src/__tests__/sourcePalettes.test.ts", "src/lib/components/dashboard/AllocationHistoryChart.test.ts"],
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
        ["npx", "vitest", "run", "src/lib/components/risk/levels/levelHelpers.test.ts", "src/lib/components/risk/levels/levelMetadata.test.ts", "src/lib/components/risk/levels/l1/l1Helpers.test.ts", "src/lib/components/risk/levels/l3Helpers.test.ts", "src/lib/components/risk/levels/simulationProvenance.test.ts", "src/lib/components/risk/levels/l4/simulationModes.test.ts", "src/lib/components/risk/levels/l4/driftUncertainty.test.ts", "src/lib/components/risk/levels/l4/scenarioHelpers.test.ts", "src/lib/components/risk/levels/partialNotice.test.ts", "src/lib/components/risk/levels/shareFormat.test.ts", "src/lib/components/risk/riskReturnLevel.test.ts"],
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
        ["npx", "vitest", "run", "src/lib/components/risk/levels/l4/L4Replay.test.ts", "src/lib/components/risk/levels/RiskPartialNotice.test.ts", "src/lib/components/risk/levels/RiskLevelSection.test.ts", "src/lib/components/risk/levels/L2Diversification.test.ts", "src/lib/components/risk/BenchmarkSelect.test.ts", "src/lib/components/risk/levels/L3RiskAdjusted.test.ts"],
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


def front_portfolio_risk_benchmark_shared(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """
    Run the shared-benchmark tests on the asset page's Risk tab.

    One benchmark for every page, kept only in user-scoped localStorage: each
    Playwright context starts with none, and nothing is written to the server.
    """
    print_section("Frontend Risk Shared Benchmark Tests")
    if not _ensure_frontend_build(): return False
    if not _ensure_db_populated(): return False
    if not _ensure_test_users(): return False
    return _run_playwright("portfolio/risk-benchmark-shared.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


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
    add_test(
        cat,
        "stale-price-banner",
        front_portfolio_stale_price_banner,
        name="Stale Price Banner Tests",
        desc="STALE_PRICE (D8): a provider-priced holding last quoted 10 days ago raises the dashboard warning, and its sync CTA posts one item per affected asset over the dashboard range, stays busy while the sync runs, then reloads the report — on a disposable account, with the provider sync intercepted",
        tests="portfolio/stale-price-banner.spec.ts",
    )
    add_test(
        cat,
        "broker-filter-label",
        front_portfolio_broker_filter_label,
        name="Broker Filter Label Tests",
        desc="Dashboard broker filter scoped to one long-named broker (owned by the test: created for the E2E user, deleted by id): at the 320 px layout (viewport 320 + the scrollbar gutter measured at load, a 254 px bar on every host) the trigger and the visible part of its label stay inside the bar card and the page does not scroll sideways, the label staying the whole name in the DOM and in the accessible name; at 2560 px (oneRow, room to spare) the whole name is shown unclipped, on arrival and after a trip to the 320 px layout — each absence with its positive control",
        tests="portfolio/dashboard-broker-filter-label.spec.ts",
    )
    add_test(cat, "broker-icons", front_portfolio_broker_icons, name="Broker Icon Tests", desc="Dashboard positions broker fallback chain", tests="portfolio/broker-icons.spec.ts")
    add_test(cat, "dashboard", front_portfolio_dashboard, name="Dashboard Chart Tests", desc="PositionsPanel 2x2 view matrix (treemap + perf chart), toggle persistence, AllocationPanel now/history, loading state", tests="portfolio/dashboard.spec.ts")
    add_test(
        cat,
        "privacy-masking",
        front_portfolio_privacy_masking,
        name="Privacy Masking Tests",
        desc="Header privacy toggle, in place both ways, desktop and mobile: dashboard KPIs, cash and positions, broker cards (R20), broker detail balances, positions and FIFO lots (partial lot ••• (NN%)), lot custody modal and transactions hide the number and keep currency and sign; held quantities hide in positions and lots, while unit prices, WAC, opening prices, percentages, counts, absent values and transaction quantities stay readable; a route mounted with privacy on is masked and the preference survives a reload",
        tests="portfolio/privacy-masking.spec.ts",
    )
    add_test(cat, "risk-unit", front_portfolio_risk_unit, test_names=False, name="Risk Store Unit Tests", desc="Request-key cache, account isolation, invalidation and capability checks", tests="src/lib/stores/risk/riskStore.test.ts")
    add_test(cat, "risk-request-unit", front_portfolio_risk_request_unit, test_names=False, name="Risk Request Builder Unit Tests", desc="What the request actually carries: the simulation process is chosen by the caller rather than hard-coded, each mode carries its own seed field and forbids the other one, and the legacy aliases keep their documented geometric-Brownian default; the stress editor and the uniform shock cover every AssetType the backend knows, derived from the enum rather than listed by hand", tests="src/lib/risk/simulationParameters.test.ts, src/lib/risk/stressBuckets.test.ts")
    add_test(cat, "risk-benchmark-unit", front_portfolio_risk_benchmark_unit, test_names=False, name="Risk Benchmark Store Unit Tests", desc="One benchmark shared by every scope: user scoping, reload survival, corrupt-value rejection", tests="src/lib/stores/risk/riskBenchmarkStore.test.ts")
    add_test(cat, "risk-controller-unit", front_portfolio_risk_controller_unit, test_names=False, name="Risk Panel Controller Unit Tests", desc="Signature invalidation with in-flight preservation, generation guards, catalog error vs pending", tests="src/lib/stores/risk/riskPanelController.test.ts")
    add_test(cat, "risk-levels-component", front_portfolio_risk_levels_component, test_names=False, name="Risk Levels Component Tests", desc="L4 historical replay mounted in jsdom over a real panel controller: the composition total is withheld rather than degraded to a dash when the scope carries no aggregate return (and is still stated when a weighted replay came out flat at 0.0), and the audit sentence names the treatment the payload actually carries — the omitted-from-replay wording as soon as one exclusion was omitted, the carried-at-zero-return wording when every exclusion was a zero-return residual, when nothing was excluded, and when the payload carries no excluded list at all. Which of the two keys was selected is proved by resolving both from the shipped catalogue instead of pinning a translated sentence; the one partial notice above the levels, mounted in jsdom: nothing when there is nothing to disclose; the causes first, then the measurements they affected; its tone informative only when every cause states a holding with no price source, amber for anything else, a cause nobody stated included; its title naming that cause when the tone is informative and something came back partial, else the partial title, else the notes title when only warnings on whole results are left (the three keys guarded in the four catalogues); each measurement a chip named by its label, else its catalogue name, else its raw code, grouped under the question of the level that renders it, in page order, with the unplaced ones last and never dropped; each reason once with its arity, and never a key on screen; the uncovered card of L2, mounted alone: there with an ok or a partial contribution, and absent, with its residual line and its card grid, when the contribution is missing, unavailable or failed, never a zero standing in for an unknown; and the frame around one level, mounted alone: a measurement that did not come back whole is named in its health line by its label when it has one, else by its catalogue name found through the shared camelCase rule (historical_var as risk.analytics.historicalVar.name, never the raw code a key built without the rule falls back to); and the one benchmark picker every Risk surface mounts: it opens on the shared choice (a stored id it cannot confirm — a deleted asset or a list that did not load — reads as unknown and stays stored), publishes its resolution state (none, pending, set, unknown) with the resolved id and whether the page measures it, leaves out only what the page measures while keeping the current choice listed and flagged by risk.benchmark.measuredHere, lists benchmarks first, writes the shared store before value and onchange, and never lets a late check overwrite a choice made meanwhile; and the portfolio's L3 mounted alone over a payload: the table in place of the four cards, titled with the question and the perimeter it read, the portfolio's row first and marked as itself, a benchmark nobody holds added second, or the held one moved up second keeping its holding's cells with beta and correlation not applicable, each figure from its own part of the payload (the dot's pair, the drawn KPI's ratios, the comparison's beta and correlation), a ratio the payload does not carry a plain dash with no tooltip, the weight column always and beta and correlation only with a measured benchmark, the return's short title with the full name opening its tooltip and listed in the column menu, every figure column as wide as its title, one selection shared by a row and its dot, and the notes under the chart in reading order", tests="src/lib/components/risk/levels/l4/L4Replay.test.ts, src/lib/components/risk/levels/RiskPartialNotice.test.ts, src/lib/components/risk/levels/RiskLevelSection.test.ts, src/lib/components/risk/levels/L2Diversification.test.ts, src/lib/components/risk/BenchmarkSelect.test.ts, src/lib/components/risk/levels/L3RiskAdjusted.test.ts")
    add_test(cat, "risk-frame-component", front_portfolio_risk_frame_component, test_names=False, name="Risk Result Frame Component Tests", desc="The legacy result frame Asset Detail mounts once per analytic, rendered in jsdom: each warning is worded through its own i18n key formatted with the names, counts, dimension and covered share it carries — never the raw ICU source a code-named key printed when it was called without values, never the generic sentence when the backend sent a reason key such as assets_excluded_missing_price — a warning without a key, or with a key this build does not ship, shows the backend sentence instead of a raw key, the generic sentence is kept only for a warning with neither, and across every risk.warnings sentence with arguments (read off en.json at test time, values built from each sentence's own ICU arguments) a warning is worded through its key once its values arrive and shows the backend sentence when they do not, never a brace or a key; the error branch still words its code through risk.errors.<code> with the state sentence as fallback. Expected sentences are resolved from the shipped catalogue through the same formatter instead of pinned", tests="src/lib/components/risk/RiskResultFrame.test.ts")
    add_test(cat, "risk-levels-unit", front_portfolio_risk_levels_unit, test_names=False, name="Risk Levels Unit Tests", desc="Four-level pure logic: L1 scale of harm (CVaR leads, omission never zero-fill, required-recovery asymmetry), L1 tail readings (underwater curve pre-scaled to percent because the chart converts nothing, VaR cut located by half-open inequality and kept when it is exactly zero, worst-realization null honoured as a refusal rather than zero-filled), L2 weight-vs-contribution divergence ordering with negative contributions, L3 figure collection plus the perimeter choice (current composition preferred, historical fallback, perimeter read from the payload even when it contradicts the wave) and the risk/return points (portfolio sized as the whole, assets by un-renormalized weight, cash never plotted), L4 simulation modes with the seed each one carries, L4 drift uncertainty applied to the median and the band it is compared against, L4 simulation provenance read from the payload instead of asserted in a translation string, L4 scenario presets and tornado ordering by signed damage, level provenance collapsed by agreement so a disagreement about the window splits instead of being represented by one analytic, and catalogue values degraded to the backend token rather than to a printed i18n key; backend warnings worded through their own i18n key and params (the catalogue sentence when it formats, the backend sentence otherwise — never the key, never raw ICU braces from a missing value, checked for every risk.warnings sentence with arguments read off en.json at test time, with plausible values and without them; a list the backend did not join reads like one it did, any other non-scalar value is left out rather than printed) and reasons deduplicated by the worded sentence, while the one-argument call keeps its verbatim output byte for byte; the one partial notice above L1–L3 (decision of 24/09): one entry per instance with the first one kept, so historical_kpi read by L1 and L3 is counted once and its warning once, only partial results named (per instance, the two VaR horizons told apart by their labels), warnings deduplicated by sentence with their arity, level health reduced to what did not come back at all, and analytic names keyed by the camelCase rule for every name the catalogue ships; and a share of the portfolio worded by its size, so a small one is never printed as zero: from 1% up the caller's own decimals, below it one decimal, below 0.1% two, «< 0.01%» (or «> -0.01%») where two would still read zero, joined by a no-break space, and only a true zero as zero; and the shared L3 table's pure rules: a figure column as wide as its title as DataTable draws it (upper-case, letter-spaced, with its padding and sort icon, rounded up) and no wider, one id per row and per dot (the portfolio and a benchmark nobody holds added as ref-portfolio and ref-<id>, a held benchmark keeping its holding's ids, a dot without a row selecting nothing), the portfolio then the benchmark opening the table with every other row in the page's order, and the notes under the chart in reading order, each only where it applies and never describing a line that is not drawn", tests="src/lib/components/risk/levels/levelHelpers.test.ts, src/lib/components/risk/levels/levelMetadata.test.ts, src/lib/components/risk/levels/l1/l1Helpers.test.ts, src/lib/components/risk/levels/l3Helpers.test.ts, src/lib/components/risk/levels/simulationProvenance.test.ts, src/lib/components/risk/levels/l4/simulationModes.test.ts, src/lib/components/risk/levels/l4/driftUncertainty.test.ts, src/lib/components/risk/levels/l4/scenarioHelpers.test.ts, src/lib/components/risk/levels/partialNotice.test.ts, src/lib/components/risk/levels/shareFormat.test.ts, src/lib/components/risk/riskReturnLevel.test.ts")
    add_test(cat, "store-unit", front_portfolio_store_unit, test_names=False, name="Portfolio Store Unit Tests", desc="portfolioStore + portfolioMutation vitest units", tests="src/lib/stores/portfolio/portfolioStore.test.ts")
    add_test(cat, "allocation-unit", front_portfolio_allocation_unit, test_names=False, name="Allocation Colour Hierarchy Unit Tests", desc="hexToHsl round-trip on the real palettes, subtype grouping/ordering, measured shade contrast, legacy ordering pin; measured contrast across a whole family on the palettes of the chart that draws it (REAL_ESTATE holding ETF_REAL_ESTATE and CROWDFUND_REAL_ESTATE by content in primaryAssetType, which no chart uses since D15; the pie's ETF family by vehicle, up to seven members, spread on both sides of its colour with alternating saturation, every pair at least as far apart in CIEDE2000 as today's closest pair, and groups of up to three byte-identical to before), with the K2 stub checked against primaryAssetType; two-ring type donut: each subtype inside the base type it contains, a lone subtype shaded by rank, rings aligned by construction, fast path refreshing both series, families resolved through K's own assetTypeFamily and primaryAssetType; the mounted pie (jsdom, ECharts recorded) draws every asset type in the family assetTypeFamily gives it — every ETF subtype in ETF, real-estate crowdfunding in Crowdfund, the cash bucket on its own — with each family's generic member captioned as the generic one and a legend entry hiding a family on both rings, and titles every arc's tooltip with exactly one icon, the type's own, a subtype's being a composite distinct from its family's; the four palettes are read from the two components that declare them, by name, never copied: each is 14 distinct #rrggbb colours and light and dark are paired slot by slot, and the reader refuses a missing, repeated, non-literal, empty or non-hex declaration with the file and the constant named; the mounted history chart (jsdom, ECharts recorded) draws one area per family assetTypeFamily gives, as the pie groups them (I's D15, D375): every ETF subtype summed into ETF, real-estate crowdfunding into Crowdfund, each family on its own base colour with no shade and its subtypes nested under it in the tooltip, and the stack cleared before a redraw whose series order moved", tests="src/lib/components/charts/__tests__/allocationHierarchy.test.ts, src/lib/components/charts/__tests__/allocationRings.test.ts, src/lib/components/charts/AllocationPieChart.test.ts, src/__tests__/sourcePalettes.test.ts, src/lib/components/dashboard/AllocationHistoryChart.test.ts")
    add_test(cat, "risk", front_portfolio_risk, name="Risk Analysis Tests", desc="Portfolio-level risk on Dashboard and Broker Detail", tests="portfolio/risk-analysis.spec.ts")
    add_test(cat, "risk-lab", front_portfolio_risk_lab, name="Asset Global Risk Lab Tests", desc="Asset-set laboratory: the no-money rule asserted by stubbing money in, D19 opening selection by branch rather than by size, bulk actions against the eligible candidates with ineligible assets parked, the \"+\" picker's filter menus that keep their own option clickable, correlation pairs keyed by asset id and matrix ordering, the holdings command loading exactly what is held with no amount crossing, and the price-and-rate sync and the reload in the page toolbar", tests="portfolio/risk-lab.spec.ts")
    add_test(cat, "risk-asset-detail", front_portfolio_risk_asset_detail, name="Risk Asset Detail Net", desc="Asset Detail is parked and must stay identical — these two tests are the proof, not a maintenance chore", tests="portfolio/risk-asset-detail.spec.ts")
    add_test(cat, "risk-benchmark-shared", front_portfolio_risk_benchmark_shared, name="Risk Shared Benchmark Tests", desc="Asset page Risk tab on the one shared benchmark: the picker opens on the stored choice and Run compares against it, a stored benchmark that is the asset itself stays shown and flagged while nothing is compared, a choice made there (a held asset) becomes the reader's shared key, and with nothing stored the picker is empty and Run waits for a choice — the choice lives only in user-scoped localStorage", tests="portfolio/risk-benchmark-shared.spec.ts")
    add_test(cat, "all", front_portfolio_all, test_names=False, name="All Portfolio Tests", desc="Run all Portfolio frontend tests")
    registry["front-portfolio"] = cat
