import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

/**
 * Dashboard charts & view matrix.
 *
 * The dashboard aggregates GLOBAL data (holdings, period P&L, allocation) that
 * every other spec is free to mutate in parallel, so nothing here asserts a
 * count or a position — only *which component* a given toggle combination
 * mounts, and that its ECharts canvas actually finished drawing.
 *
 * Why this file exists: `PositionsPanel` hides two of its four sub-views behind
 * `visualMode === 'map'`, and no prior spec ever clicked `positions-toggle-map`.
 * `PerformanceChart` and `ExposureTreemap` were therefore never mounted by any
 * test (0% coverage). Walking the full 2×2 matrix is what brings them to life.
 *
 * The matrix (semantic × visual):
 *   holdings   × table → ExposureTable        (data-testid="exposure-table")
 *   holdings   × map   → ExposureTreemap      (data-testid="exposure-treemap")
 *   performance× table → ContributionTable    (data-testid="contribution-table")
 *   performance× map   → PerformanceChart     (data-testid="performance-chart")
 *
 * Two branches swallow the map views before the chart mounts — `showHoldingsEmpty`
 * / `showPerformanceEmpty` (panel level) and the chart's own empty state. We never
 * assert on the translated "no data" text; instead we wait for `data-chart-ready`
 * on the canvas, which only appears once ECharts has really drawn real data. A
 * period with no P&L would render a message and no `[data-chart-ready]` ever, so
 * the wait fails loudly instead of the test passing on an empty state.
 *
 * onAnalyze is intentionally NOT covered here: both charts forward it through an
 * ECharts *canvas* context-menu (right-click a tile/bar), and a canvas is not a
 * navigable DOM — there is no honest, stable way to hit a specific slice by
 * coordinates. Per the testing rules, we say so rather than click coordinates.
 *
 * Earned parallel: every block below owns nothing but its own browser context
 * (localStorage prefs, an intercepted response) and waits on published state
 * (`data-busy`, `data-chart-ready`), so it shares the one backend with its
 * neighbours instead of queueing behind them.
 */
test.describe.configure({mode: 'parallel'});

/** Open the Positions tab and wait for the panel to finish its load wave. */
async function openPositionsTab(page: Page): Promise<void> {
    await page.goto('/dashboard?tab=posizioni');
    await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
    await expect(page.getByTestId('positions-panel')).toBeVisible({timeout: 15_000});
    // The report runs FIFO at runtime, so under a loaded backend it is far slower
    // than a default assertion timeout — wait on the panel's own busy flag, not a
    // bigger number. (broker-icons.spec.ts leans on the same 30s budget.)
    await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
}

/** The renders counter a chart container publishes; monotonic, 0 before first draw. */
async function chartRenders(chart: Locator): Promise<number> {
    return Number((await chart.getAttribute('data-chart-renders')) ?? '0');
}

test.describe('Dashboard charts and view matrix', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('Holdings view mounts ExposureTable (table) and ExposureTreemap (map)', async ({page}) => {
        await openPositionsTab(page);

        // Holdings is the default semantic, but assert it explicitly so the test
        // does not depend on a pref another run left in this context.
        await page.getByTestId('positions-toggle-holdings').click();

        // holdings × table
        await page.getByTestId('positions-toggle-table').click();
        await expect(page.getByTestId('exposure-table')).toBeVisible({timeout: 15_000});

        // holdings × map → ExposureTreemap. The treemap container *is* the chart
        // canvas, so data-chart-ready lands on the same element.
        await page.getByTestId('positions-toggle-map').click();
        const treemap = page.getByTestId('exposure-treemap');
        await expect(treemap).toBeVisible({timeout: 15_000});
        await expect(treemap).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});
    });

    test('Performance view mounts ContributionTable (table) and PerformanceChart (map)', async ({page}) => {
        await openPositionsTab(page);

        // Switching to Performance lazy-loads the contribution report; the panel
        // republishes data-busy for that wave, so wait it out rather than guess.
        await page.getByTestId('positions-toggle-performance').click();
        await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});

        // performance × table
        await page.getByTestId('positions-toggle-table').click();
        await expect(page.getByTestId('contribution-table')).toBeVisible({timeout: 15_000});

        // performance × map → PerformanceChart. The testid is the wrapper; its
        // canvas descendant carries data-chart-ready. If the period had no P&L the
        // component would render a message and no [data-chart-ready] would exist,
        // so this assertion fails loudly instead of green-on-empty.
        await page.getByTestId('positions-toggle-map').click();
        const chart = page.getByTestId('performance-chart');
        await expect(chart).toBeVisible({timeout: 15_000});
        await expect(chart.locator('[data-chart-ready]')).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});
    });

    test('Visual and semantic toggles persist across a reload', async ({page}) => {
        await openPositionsTab(page);

        // Drive both toggles away from their defaults: holdings/table → holdings/map → performance/map.
        await page.getByTestId('positions-toggle-map').click();
        await expect(page.getByTestId('exposure-treemap')).toBeVisible({timeout: 15_000});

        await page.getByTestId('positions-toggle-performance').click();
        await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(page.getByTestId('performance-chart')).toBeVisible({timeout: 15_000});

        // The panel persists visualMode + semanticMode in user-scoped localStorage
        // (getUserStorageKey). A full reload re-reads them at component init, so the
        // performance/map view must come back — which uniquely proves BOTH keys
        // survived (performance ⟺ semantic, map ⟺ visual).
        await page.reload();
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});

        const chart = page.getByTestId('performance-chart');
        await expect(chart).toBeVisible({timeout: 15_000});
        await expect(chart.locator('[data-chart-ready]')).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});
    });

    test('Allocation panel toggles now/history and cycles the dimension tabs', async ({page}) => {
        await page.goto('/dashboard'); // default "panoramica" (overview) tab
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('dashboard-page')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});

        await expect(page.getByTestId('allocation-panel')).toBeVisible({timeout: 15_000});

        // The AllocationHistoryChart is always mounted but hidden in the "now" view;
        // that hidden/visible flip is exactly the now-vs-history contract.
        const history = page.getByTestId('allocation-history-chart');
        await expect(history).toBeHidden();

        await page.getByTestId('allocation-view-history').click();
        await expect(history).toBeVisible({timeout: 15_000});
        await expect(history).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});

        // Each dimension re-derives its series from the already-loaded report and
        // redraws; data-chart-renders is monotonic, so a delta proves a fresh pass
        // (a stale "ready === true" cannot let the assertion through early).
        for (const dim of ['sector', 'geo', 'type'] as const) {
            const before = await chartRenders(history);
            await page.getByTestId(`allocation-tab-${dim}`).click();
            await expect.poll(() => chartRenders(history), {timeout: 15_000}).toBeGreaterThan(before);
            await expect(history).toBeVisible();
        }
    });

    test('Positions panel publishes its loading state through data-busy', async ({page}) => {
        // Hold the FIRST portfolio report so the busy state is observable, then
        // release it. Synchronisation is on data-busy, never on the clock: the gate
        // is a promise the test resolves the instant it has seen "true". Only the
        // first request is held — any later report call (e.g. a re-fetch) passes
        // straight through so it cannot deadlock the page.
        let release: () => void = () => {};
        const held = new Promise<void>((resolve) => (release = resolve));
        let firstHeld = false;
        await page.route(/\/api\/v1\/portfolio\/report(\?.*)?$/, async (route) => {
            if (!firstHeld) {
                firstHeld = true;
                await held;
            }
            await route.continue();
        });

        await page.goto('/dashboard?tab=posizioni');
        const panel = page.getByTestId('positions-panel');
        await expect(panel).toBeVisible({timeout: 15_000});
        await expect(panel).toHaveAttribute('data-busy', 'true', {timeout: 15_000});

        release();

        await expect(panel).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(page.getByTestId('exposure-table')).toBeVisible({timeout: 15_000});
    });
});

/**
 * F1 guard — the AI export trigger at mobile width.
 *
 * Beta feedback: the dashboard's AiExportMenu disappeared at mobile viewport,
 * then recovered, with the cause never isolated. That is exactly the failure
 * shape a regression guard exists for: the mechanism is unknown, so the
 * assertion is on the OUTCOME — the trigger is on screen at phone width.
 *
 * `setViewportSize` is called inside the test (rather than relying on the
 * `mobile` project) so the guard is deterministic on every project it runs
 * under. The button may be *disabled* while the catalog probe is in flight —
 * disabled is a state, absent/invisible is the regression.
 */
test.describe('Dashboard toolbar — AI export at mobile viewport (F1 guard)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('the AI export trigger stays visible at phone width', async ({page}) => {
        await page.setViewportSize({width: 375, height: 800});
        await page.goto('/dashboard');
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});

        await expect(page.getByTestId('ai-export-button')).toBeVisible({timeout: 15_000});
    });
});
