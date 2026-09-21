import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {showChartTooltip} from '../fixtures/charts';
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

/**
 * GrowthChart — P&L mode (phase I70).
 *
 * The rule that shapes every assertion below, measured before a line was written:
 * **with the P&L feature completely broken, in all three submodes, the canvas
 * still exists and is still 641×360.** `expect(canvas).toBeVisible()` passes
 * against the broken build — the broken and the healthy world produce the same
 * DOM. So nothing here asserts presence of the chart. Every case asserts one of:
 *
 *   1. the network the action causes — the `/portfolio/report` body and its
 *      response, read through `recordReports()`;
 *   2. a count of something data-derived — candle points, tooltip value rows,
 *      the resolution the bucket counts resolve to;
 *   3. `aria-pressed`, and only for the submode toggle, where the attribute *is*
 *      the mutual-exclusion contract.
 *
 * The resolution badge deserves a word, because it does the heavy lifting twice.
 * `ResolutionBadge` renders only when the chart is NOT at daily resolution, and
 * the resolution is a pure function of (visible bucket count, plot width,
 * grammar). Since the plot width never moves inside a test, the badge is a live
 * read of "how many days are visible, under which grammar" — i.e. real data,
 * not decoration. It is how the candle grammar (case: candles coarser than
 * lines) and the zoom-window selector (case: operative in all three submodes)
 * are observed without inventing a product hook.
 *
 * What is deliberately NOT asserted: the literal length of ECharts' `series`
 * array. `echarts` is not global in the bundle, `getInstanceByDom` is
 * unreachable from `page.evaluate`, and the DOM carries only an instance *id*.
 * Where a series count matters (per-broker overlay, income bars) these tests
 * assert the data that feeds it and the rows the chart's own tooltip formatter
 * renders from it — which is as close as the app lets a test get without a
 * diagnostic hook nobody decided to ship.
 *
 * Earned parallel: these tests write nothing. They read the shared report,
 * derive their expectations from the response they were served, and hold state
 * only in their own browser context — so they run under the file's existing
 * `mode: 'parallel'` declaration rather than adding an exception to it.
 */

type PnlSubmode = 'line' | 'candles' | 'income';

const PNL_SUBMODES: readonly PnlSubmode[] = ['line', 'candles', 'income'];
const ZOOM_WINDOWS = ['1w', '1m', '1y', 'all'] as const;

/** `EUR 1,234.56` / `EUR -12.30` — an unsigned tooltip amount (the OHLC rows). */
const PLAIN_AMOUNT = /^[A-Z]{3}\s-?[\d.,]+$/;
/** `+EUR 359.04` / `−EUR 12.00` — a signed tooltip amount (P&L rows; U+2212). */
const SIGNED_AMOUNT = /^[+\u2212][A-Z]{3}\s[\d.,]+$/;

/** One `/portfolio/report` exchange: what was asked for, and what came back. */
interface ReportCall {
    body: Record<string, unknown> & {broker_ids?: number[]};
    json: Record<string, any> | null;
}

/**
 * Record every portfolio report this page issues, request body *and* response.
 *
 * Install it before navigating. The tests read their expectations out of what
 * the backend actually returned rather than hard-coding a fixture, so a seeded
 * portfolio that changes shape produces a meaningful failure instead of a stale
 * constant.
 */
async function recordReports(page: Page): Promise<ReportCall[]> {
    const calls: ReportCall[] = [];
    await page.route(/\/api\/v1\/portfolio\/report(\?.*)?$/, async (route) => {
        const body = route.request().postDataJSON();
        const response = await route.fetch();
        const json = await response.json().catch(() => null);
        calls.push({body, json});
        await route.fulfill({response});
    });
    return calls;
}

/** The element GrowthChart publishes `data-chart-ready`/`data-chart-renders` on. */
function growthHost(chart: Locator): Locator {
    return chart.locator('[data-chart-ready]');
}

/** Open the dashboard overview and wait until the GrowthChart has really drawn. */
async function openGrowthChart(page: Page): Promise<Locator> {
    await page.goto('/dashboard');
    await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
    await expect(page.getByTestId('dashboard-page')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});

    const chart = page.getByTestId('growth-chart');
    // `renderChart` bails out while `history` is empty, so `data-chart-ready`
    // flipping to true is the app saying "real data arrived and ECharts drew it".
    await expect(growthHost(chart)).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});
    return chart;
}

/**
 * Select a P&L submode and wait for the redraw it causes.
 *
 * The counter is sampled *before* the click (a monotonic counter read as an
 * absolute value is the same bet as a sleep). Re-selecting the submode already
 * active writes the same value, so Svelte never re-renders and there would be no
 * delta to wait for — hence the state read first, which is the attribute that
 * defines the toggle rather than a guess about it.
 */
async function selectSubmode(chart: Locator, submode: PnlSubmode): Promise<void> {
    const button = chart.getByTestId(`growth-pnl-submode-${submode}`);
    await expect(button).toBeVisible({timeout: 10_000});

    if ((await button.getAttribute('aria-pressed')) !== 'true') {
        const host = growthHost(chart);
        const before = await chartRenders(host);
        await button.click();
        await expect.poll(() => chartRenders(host), {timeout: 15_000}).toBeGreaterThan(before);
    }
    await expect(button).toHaveAttribute('aria-pressed', 'true');
}

/** Pick a zoom-window preset and wait for the redraw it causes. */
async function selectZoomWindow(chart: Locator, window: (typeof ZOOM_WINDOWS)[number]): Promise<void> {
    const host = growthHost(chart);
    const before = await chartRenders(host);
    await chart.getByTestId(`growth-zoom-window-${window}`).click();
    await expect.poll(() => chartRenders(host), {timeout: 15_000}).toBeGreaterThan(before);
}

/**
 * Re-run the resolution cascade under the **candle** grammar, and leave the
 * badge as the answer.
 *
 * This is the only read the app offers of "how wide is the visible window", and
 * it exists because the cascade runs on a grammar *change*: parking on the line
 * grammar first guarantees that entering candles flips it and re-cascades, so
 * the badge that follows describes the window as it is now, not as it was.
 *
 * The caller then asserts the badge — visible means the window is wide enough
 * for the candle grammar to coarsen past daily, absent means it is not.
 */
async function recascadeUnderCandleGrammar(page: Page, chart: Locator): Promise<void> {
    await selectSubmode(chart, 'line');
    await selectSubmode(chart, 'candles');
}

test.describe('GrowthChart P&L mode — dashboard', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('P&L exposes exactly three submodes and exactly one is pressed', async ({page}) => {
        const chart = await openGrowthChart(page);
        await chart.getByTestId('growth-toggle-pnl').click();

        const submodeButtons = chart.locator('[data-testid^="growth-pnl-submode-"]');
        await expect(submodeButtons).toHaveCount(3);

        for (const active of PNL_SUBMODES) {
            await selectSubmode(chart, active);
            for (const other of PNL_SUBMODES) {
                await expect(chart.getByTestId(`growth-pnl-submode-${other}`)).toHaveAttribute('aria-pressed', String(other === active));
            }
            // The same fact from the other side: not "line is on", but "nothing
            // else is". A per-button check passes on three independent booleans;
            // this one is the exclusivity itself.
            await expect(chart.locator('[data-testid^="growth-pnl-submode-"][aria-pressed="true"]')).toHaveCount(1);
        }

        // The picker belongs to P&L: leaving the mode retires it. The negative
        // needs a barrier, so the toggle row is asserted alive in the same breath
        // — "no submode buttons" must not also be true of an unmounted chart.
        await chart.getByTestId('growth-toggle-eur').click();
        await expect(chart.getByTestId('growth-toggle-pnl')).toBeVisible();
        await expect(submodeButtons).toHaveCount(0);
    });

    test('the line submode draws one P&L series per broker in scope', async ({page}) => {
        const reports = await recordReports(page);
        const chart = await openGrowthChart(page);

        // The dashboard asks for broker_pnl_history only when its scope holds ≥2
        // brokers, so this is the precondition the case needs — verified, not
        // inferred from "the dashboard usually has a few".
        const overview = reports.find((call) => call.body.include_broker_pnl_history === true);
        expect(overview, 'the dashboard requests broker_pnl_history whenever its scope has ≥2 brokers').toBeTruthy();

        const brokers: Array<{broker_id: number; broker_name: string}> = overview?.json?.broker_pnl_history ?? [];
        expect(brokers.length, 'this case needs a multi-broker scope — the E2E user must own ≥2 brokers').toBeGreaterThan(1);

        await chart.getByTestId('growth-toggle-pnl').click();
        await selectSubmode(chart, 'line');

        // Names come out of the response, so the chart is checked against the data
        // it was handed — not against a hard-coded broker that another spec may
        // rename or a seeding change may drop.
        await showChartTooltip(page, chart, chart.getByText(SIGNED_AMOUNT), 10_000, brokers.length + 1);
        for (const broker of brokers) {
            await expect(chart.getByText(broker.broker_name, {exact: true}), `${broker.broker_name} has its own overlay line in the P&L tooltip`).toBeVisible();
        }

        // Total + one row per broker: more series than the single total line the
        // submode would draw without the G1a overlay.
        await expect(chart.getByText(SIGNED_AMOUNT)).toHaveCount(brokers.length + 1);
    });

    test('the candles submode fetches the candle series lazily and receives real points', async ({page}) => {
        const reports = await recordReports(page);
        const chart = await openGrowthChart(page);

        // Laziness is half the contract: the ordinary load must not pay for OHLC.
        expect(reports.length, 'the dashboard loads at least one report').toBeGreaterThan(0);
        expect(
            reports.filter((call) => call.body.include_pnl_candles === true),
            'no report asks for candles before the submode is ever opened',
        ).toHaveLength(0);

        await chart.getByTestId('growth-toggle-pnl').click();
        await selectSubmode(chart, 'candles');

        await expect.poll(() => reports.filter((call) => call.body.include_pnl_candles === true).length, {timeout: 20_000}).toBeGreaterThan(0);
        const candleCall = reports.find((call) => call.body.include_pnl_candles === true);
        const series = candleCall?.json?.pnl_candles;

        expect(series?.hypothetical, 'the series always declares itself synthetic — the label depends on it').toBe(true);
        const points: Array<Record<string, {amount: string} | undefined>> = series?.points ?? [];
        expect(points.length, 'the seeded window has candles').toBeGreaterThan(0);

        const amount = (value?: {amount: string}) => Number(value?.amount);
        const holed = points.filter((point) => ['open', 'high', 'low', 'close'].some((key) => !Number.isFinite(amount(point[key]))));
        expect(holed, 'every candle carries four real numbers — an unavailable day is omitted, never nulled').toHaveLength(0);
        expect(
            points.some((point) => amount(point.close) !== 0),
            'the seeded portfolio moves somewhere in the window — an all-zero series would draw flat and prove nothing',
        ).toBe(true);
        const inverted = points.filter((point) => amount(point.high) < Math.max(amount(point.open), amount(point.close)) || amount(point.low) > Math.min(amount(point.open), amount(point.close)));
        expect(inverted, 'high bounds the body above and low below').toHaveLength(0);

        // …and the chart consumed them: its tooltip reads back a full OHLC quad.
        await showChartTooltip(page, chart, chart.getByText(PLAIN_AMOUNT), 10_000, 4);
        await expect(chart.getByText(PLAIN_AMOUNT)).toHaveCount(4);
        await expect(chart.getByTestId('growth-pnl-candles-hypothetical-label')).toBeVisible();
    });

    test('the income submode receives all six of the channels it plots', async ({page}) => {
        const reports = await recordReports(page);
        const chart = await openGrowthChart(page);

        const overview = reports.find((call) => call.body.include_income_history === true);
        expect(overview, 'the dashboard requests the sparse income family on every ordinary load').toBeTruthy();
        expect({
            income: overview?.body.include_income_history,
            cost: overview?.body.include_cost_history,
            deposit: overview?.body.include_deposit_history,
            acquisition: overview?.body.include_acquisition_funding,
        }).toEqual({income: true, cost: true, deposit: true, acquisition: true});

        // The six bars are six payload channels; count the points that carry each
        // one rather than trusting that a non-null section implies content.
        const json = overview?.json ?? {};
        const has = (points: any[] | undefined, field: string) => (points ?? []).filter((point) => point?.[field]?.amount != null).length;
        const channels = {
            dividend: has(json.income_history?.points, 'dividend'),
            interest: has(json.income_history?.points, 'interest'),
            cost: has(json.cost_history?.points, 'cost'),
            deposit: has(json.deposit_history?.points, 'deposit'),
            acqNewCapital: has(json.acquisition_funding?.points, 'from_new_capital'),
            acqReinvested: has(json.acquisition_funding?.points, 'from_reinvested'),
        };
        for (const [name, count] of Object.entries(channels)) {
            expect(count, `${name} feeds one of the income submode's six bars`).toBeGreaterThan(0);
        }

        await chart.getByTestId('growth-toggle-pnl').click();
        await selectSubmode(chart, 'income');

        // Bound, not merely fetched: the submode's tooltip reads the personal
        // income block back out of the chart (dividend, interest and their total).
        // Three is the floor, not the count — the batch-2 rows (costs, deposit,
        // acquisition) are sparse by design and only join on a day that had that
        // activity, so pinning an exact number would pin which day the pointer
        // happened to land on.
        await showChartTooltip(page, chart, chart.getByText(SIGNED_AMOUNT), 10_000, 3);
        await expect(chart.getByText(SIGNED_AMOUNT).first()).toBeVisible();
    });

    for (const submode of PNL_SUBMODES) {
        test(`the zoom-window selector is present and operative in the ${submode} submode`, async ({page}) => {
            // Six cascade re-runs, each one a real redraw; the default 15s budget
            // is for a single interaction, not for a windowing matrix.
            test.setTimeout(90_000);
            const chart = await openGrowthChart(page);
            await chart.getByTestId('growth-toggle-pnl').click();
            await selectSubmode(chart, submode);

            for (const window of ZOOM_WINDOWS) {
                await expect(chart.getByTestId(`growth-zoom-window-${window}`), `the ${window.toUpperCase()} preset is offered in the ${submode} submode`).toBeVisible();
            }

            const badge = page.getByTestId('chart-resolution-badge');

            // Present is not the same as operative, and "the button highlighted
            // itself" would only prove the button. What is asserted instead is the
            // consequence: the visible window really moved, read back through the
            // candle grammar's own resolution cascade.
            await selectSubmode(chart, submode);
            await selectZoomWindow(chart, 'all');
            await recascadeUnderCandleGrammar(page, chart);
            await expect(badge, 'the whole seeded window is far too wide for daily candles').toBeVisible({timeout: 10_000});

            await selectSubmode(chart, submode);
            await selectZoomWindow(chart, '1w');
            await recascadeUnderCandleGrammar(page, chart);
            await expect(badge, 'one week of candles fits at daily resolution — so the 1W press really narrowed the window').toHaveCount(0);
        });
    }

    test('candles aggregate coarser than the line at the very same window', async ({page}) => {
        const chart = await openGrowthChart(page);
        await chart.getByTestId('growth-toggle-pnl').click();
        await selectSubmode(chart, 'line');

        // Pin the window explicitly: the comparison is only meaningful if the two
        // grammars are asked about the same number of days.
        await selectZoomWindow(chart, 'all');

        const badge = page.getByTestId('chart-resolution-badge');
        // A line vertex survives sub-pixel density, so the full window stays daily…
        await expect(badge).toHaveCount(0);

        // …while a candle needs a body, two edges and a gap, so the same window
        // has to coarsen. Nothing else moved: same data, same plot width.
        await selectSubmode(chart, 'candles');
        await expect(badge, 'the candle grammar must escalate where the line grammar does not').toBeVisible({timeout: 10_000});

        // And back — proving the grammar drove it, not a one-way drift that would
        // have made the middle assertion true for the wrong reason.
        await selectSubmode(chart, 'line');
        await expect(badge).toHaveCount(0);
    });
});
