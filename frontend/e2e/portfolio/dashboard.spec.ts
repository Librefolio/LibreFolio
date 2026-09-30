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
        // that hidden/visible flip is exactly the now-vs-history contract. The view
        // persists per user now (S4), so "now" is selected, not assumed: a default
        // is a fact about an empty storage, not about this context.
        const history = page.getByTestId('allocation-history-chart');
        const now = page.getByTestId('allocation-view-now');
        await now.click();
        await expect(now).toHaveAttribute('aria-pressed', 'true');
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

    test('Allocation panel remembers its view and dimension across a reload', async ({page}) => {
        // S4: the view (now/history) and the dimension (type/sector/geo) are the
        // user's choice and persist in user-scoped storage, written on click. Both
        // are driven AWAY from their defaults (now, type) first — a default that
        // "came back" after a reload proves nothing about persistence.
        await page.goto('/dashboard');
        await expect(page.getByTestId('dashboard-page')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(page.getByTestId('allocation-panel')).toBeVisible({timeout: 15_000});

        const history = page.getByTestId('allocation-history-chart');
        await page.getByTestId('allocation-view-history').click();
        await expect(page.getByTestId('allocation-view-history')).toHaveAttribute('aria-pressed', 'true');
        await expect(history).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});
        await page.getByTestId('allocation-tab-sector').click();
        await expect(page.getByTestId('allocation-tab-sector')).toHaveAttribute('aria-pressed', 'true');

        await page.reload();
        await expect(page.getByTestId('dashboard-page')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(page.getByTestId('allocation-panel')).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('allocation-view-history'), 'the history view came back').toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('allocation-tab-sector'), 'and so did the sector dimension').toHaveAttribute('aria-pressed', 'true');
        // …and the view is not only highlighted but mounted: the history chart drew.
        await expect(history).toBeVisible({timeout: 15_000});
        await expect(history).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});
    });

    test('Allocation by type carries a per-slice colour derived from its primary type', async ({page}) => {
        // ECharts draws to a canvas, so a colour has no DOM to assert on. The
        // component exposes its instance as `__lfChart` (same hook as
        // PriceChartFull); reading the option is the only way to observe that the
        // hierarchy actually reached the chart rather than merely compiling.
        await page.goto('/dashboard');
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('dashboard-page')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});

        const panel = page.getByTestId('allocation-panel');
        await expect(panel).toBeVisible({timeout: 15_000});
        // Never assume the default tab — select it.
        await page.getByTestId('allocation-tab-type').click();

        type Slice = {rawName: string; value: number; color: string | null; groupSize: number | null; primaryKey: string | null; primaryTotal: number | null};
        const read = async (): Promise<{palette: unknown; slices: Slice[]} | null> =>
            panel.evaluate((root) => {
                for (const node of Array.from(root.querySelectorAll('*'))) {
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    const chart = (node as any).__lfChart;
                    if (!chart) continue;
                    const option = chart.getOption();
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    const series = ((option.series as any[]) ?? [])[0];
                    if (series?.type !== 'pie') continue; // the history chart lives here too
                    return {
                        palette: option.color,
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        slices: ((series.data as any[]) ?? []).map((d) => ({
                            rawName: String(d?.rawName ?? ''),
                            value: Number(d?.value ?? 0),
                            color: d?.itemStyle?.color ?? null,
                            groupSize: d?.groupSize ?? null,
                            primaryKey: d?.primaryKey ?? null,
                            primaryTotal: d?.primaryTotal ?? null,
                        })),
                    };
                }
                return null;
            });

        // Poll rather than sleep: the pie mounts when the tab flips, so the first
        // read can legitimately land before the instance exists.
        await expect.poll(async () => (await read())?.slices.length ?? 0, {timeout: 15_000}).toBeGreaterThan(0);
        const option = (await read())!;

        // Option-level palette, grown to 14 so 13 possible primaries cannot wrap.
        expect(Array.isArray(option.palette)).toBe(true);
        expect((option.palette as string[]).length).toBe(14);

        for (const slice of option.slices) {
            // Per-datum colour: proves buildAllocationHierarchy ran. Before this
            // change slices had no itemStyle at all and inherited the palette by index.
            expect(slice.color, `slice ${slice.rawName} has no own colour`).toMatch(/^#[0-9a-f]{6}$/i);
            expect(slice.groupSize).toBeGreaterThanOrEqual(1);
            // A group total can never be smaller than one of its members.
            expect(slice.primaryTotal).toBeGreaterThanOrEqual(slice.value - 0.01);
        }

        // No two categories may share a colour — the failure mode the 12-entry
        // palette produced by wrapping with `% 12`.
        const colors = option.slices.map((s) => String(s.color).toLowerCase());
        expect(new Set(colors).size).toBe(colors.length);

        // Members of one primary must be contiguous, otherwise a shared hue reads
        // as coincidence rather than kinship. Holds trivially while every group is
        // a singleton, and becomes load-bearing as soon as subtypes exist in the data.
        // Non-decreasing first-occurrence indices is exactly contiguity: an
        // interleaving like [A, A, B, C, B] breaks the order, and is caught.
        const primaries = option.slices.map((s) => s.primaryKey);
        const firstSeen = primaries.map((p) => primaries.indexOf(p));
        expect(firstSeen).toEqual([...firstSeen].sort((a, b) => a - b));

        // Legacy pin, observed end to end: with no subtype present every group is a
        // singleton, so the result must still be the plain value-descending order
        // painted with the palette in order — exactly what shipped before.
        if (option.slices.every((s) => s.groupSize === 1)) {
            const values = option.slices.map((s) => s.value);
            expect(values).toEqual([...values].sort((a, b) => b - a));
            expect(colors).toEqual((option.palette as string[]).slice(0, colors.length).map((c) => c.toLowerCase()));
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
 *   3. `aria-pressed`, and only on the controls where the attribute *is* the
 *      mutual-exclusion contract: the submode toggle and the candle-width ladder.
 *
 * The bucket width deserves a word, because two different controls publish it
 * and each lives where the width is decided. In Value, % and the P&L line the
 * density cascade decides FOR the user, and `ResolutionBadge` renders only when
 * that decision is NOT daily — a pure function of (visible day count, plot
 * width, grammar), so its absence is a live read of "this window is drawn one
 * point per day", i.e. real data, not decoration. In Candles and Income the user
 * decides: the candle-width ladder (`growth-candle-width-*`) offers only the
 * rungs the geometry can draw, marks the one in force with `aria-pressed`, and
 * the badge is not mounted under it. The ladder is how the candle grammar (case:
 * candles coarser than the line at the very same window) is observed. There is
 * no zoom-window selector any more: the period is the dashboard's date-range
 * picker, and a rung changes how many days one body covers, never which days
 * are shown.
 *
 * What is deliberately NOT asserted: the literal length of ECharts' `series`
 * array — the P&L line alone is drawn as two sign halves, a dashed reference
 * and one line per broker, which is construction, not contract. The chart does
 * publish its ECharts instance as `__lfChart` on the container (the same hook
 * as PriceChartFull), so where a count has to be read off the canvas itself —
 * how many points a line kept, how many bodies the candles drew, what an axis
 * label prints — it is read through `getOption()`. Where a count is about the
 * data (per-broker overlay, income bars), these tests assert the data that
 * feeds it and the rows the chart's own tooltip formatter renders from it.
 *
 * Earned parallel: these tests write nothing. They read the shared report,
 * derive their expectations from the response they were served, and hold state
 * only in their own browser context — so they run under the file's existing
 * `mode: 'parallel'` declaration rather than adding an exception to it.
 */

type PnlSubmode = 'line' | 'candles' | 'income';

const PNL_SUBMODES: readonly PnlSubmode[] = ['line', 'candles', 'income'];

/**
 * `EUR 1,234.56` / `EUR -12.30` — an unsigned tooltip amount (the OHLC rows). The
 * minus is the browser locale's own (D23): ASCII in English, U+2212 in Swedish.
 */
const PLAIN_AMOUNT = /^[A-Z]{3}\s[-\u2212]?[\d.,]+$/;
/**
 * `EUR +359.04` / `EUR -12.00` / `EUR 0.00` — a P&L or income tooltip amount.
 * One form for every signed row (D23b): the sign after the currency, the minus
 * the locale's own, ASCII or U+2212 (D23). The sign is optional because a zero
 * carries none, by design: a green zero read as a gain. A signed-only pattern
 * therefore stops counting a row on the day its value happens to be zero, which
 * is a calendar, not a contract.
 */
const PNL_AMOUNT = /^[A-Z]{3}\s[+\-\u2212]?[\d.,]+$/;
/** A P&L line tooltip value: an amount as above, or `—` for a broker with no value that day. */
const PNL_LINE_VALUE = /^(?:[A-Z]{3}\s[+\-\u2212]?[\d.,]+|—)$/;
/** The ISO date every tooltip header carries, whatever the bucket width. */
const TOOLTIP_DATE = /\d{4}-\d{2}-\d{2}/;
/** GrowthChart's `LADDER_MIN_BODY_PX`: the narrowest candle body the ladder offers. */
const LADDER_MIN_BODY_PX = 2.5;

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

/** Select a growth mode (Abs / % / P&L) and wait for the redraw it causes — same rule as above. */
async function selectGrowthMode(chart: Locator, mode: 'eur' | 'pct' | 'pnl'): Promise<void> {
    const button = chart.getByTestId(`growth-toggle-${mode}`);
    await expect(button).toBeVisible({timeout: 10_000});

    if ((await button.getAttribute('aria-pressed')) !== 'true') {
        const host = growthHost(chart);
        const before = await chartRenders(host);
        await button.click();
        await expect.poll(() => chartRenders(host), {timeout: 15_000}).toBeGreaterThan(before);
    }
    await expect(button).toHaveAttribute('aria-pressed', 'true');
}

/**
 * The value cells of the GrowthChart tooltip, one per row.
 *
 * Every value row the formatter writes — `buildTooltipRow`, the line's `pnlRow`,
 * the candles' `ohlcRow` and broker rows, the income `signedRow` — is a `div`
 * whose children are exactly `<span>label</span><b>value</b>`. The headers are
 * plain `div`s; a bold label (`<b>Total</b>`) sits INSIDE its label span, never
 * directly under the row; and nothing else in the card has a `<b>`. So this is
 * "one cell per row" whatever the value looks like — signed, unsigned, zero or
 * `—` — which is what a count of rows has to be, instead of a count of signs.
 */
function tooltipValues(chart: Locator): Locator {
    return chart.locator('div > span + b');
}

/** The tooltip rows themselves: the parent of each value cell, so a value can be paired with its label. */
function tooltipRows(chart: Locator): Locator {
    return tooltipValues(chart).locator('xpath=..');
}

/**
 * The tooltip rows whose label is none of `names`.
 *
 * Broker names come out of the served `broker_pnl_history` — data, not
 * translated text — so "not a broker's row" is decidable without reading a
 * label the UI translates (Total, Open, Close…).
 */
function rowsNotLabelledBy(page: Page, rows: Locator, names: string[]): Locator {
    return names.reduce((remaining, name) => remaining.filter({hasNot: page.getByText(name, {exact: true})}), rows);
}

/** One summary per series GrowthChart handed ECharts: its type, its points, and the points that are not the `'-'` gap sentinel. */
async function growthSeries(host: Locator): Promise<Array<{type: string; points: number; bodies: number}>> {
    return host.evaluate((node) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const series = (((node as any).__lfChart?.getOption?.()?.series as any[]) ?? []).filter(Boolean);
        return series.map((s) => {
            const data: unknown[] = Array.isArray(s.data) ? s.data : [];
            return {type: String(s.type), points: data.length, bodies: data.filter((d) => d != null && d !== '-').length};
        });
    });
}

/**
 * Points per bucket of the P&L line, read off the chart: the smallest `line`
 * series. The Total's two sign halves also carry their interpolated zero
 * crossings, while the reference and per-broker lines carry exactly one point
 * per bucket — so the minimum is the bucket count. 0 while no line is drawn.
 */
async function lineBuckets(host: Locator): Promise<number> {
    const lines = (await growthSeries(host)).filter((s) => s.type === 'line');
    return lines.length > 0 ? Math.min(...lines.map((s) => s.points)) : 0;
}

/** The candlestick series as drawn: its bucket count and how many of them carry a real body. */
async function candleSeries(host: Locator): Promise<{points: number; bodies: number}> {
    const candles = (await growthSeries(host)).find((s) => s.type === 'candlestick');
    return {points: candles?.points ?? 0, bodies: candles?.bodies ?? 0};
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
        // inferred from "the dashboard usually has a few". The latest overview is
        // the one the chart is drawing.
        const overview = reports.filter((call) => call.body.include_broker_pnl_history === true).at(-1);
        expect(overview, 'the dashboard requests broker_pnl_history whenever its scope has ≥2 brokers').toBeTruthy();

        const brokers: Array<{broker_id: number; broker_name: string}> = overview?.json?.broker_pnl_history ?? [];
        expect(brokers.length, 'this case needs a multi-broker scope — the E2E user must own ≥2 brokers').toBeGreaterThan(1);
        const brokerNames = brokers.map((broker) => broker.broker_name);

        await chart.getByTestId('growth-toggle-pnl').click();
        await selectSubmode(chart, 'line');

        // Counted by ROW, never by sign. The line formatter writes the Total row
        // and then one `pnlRow` per broker it was handed, and nothing else: a zero
        // prints with no sign and a broker with no value that day prints `—`, so
        // counting signed amounts measured which day the pointer landed on. Names
        // come out of the response, so the chart is checked against the data it
        // was handed — not against a hard-coded broker that another spec may
        // rename or a seeding change may drop.
        const values = tooltipValues(chart);
        const rows = tooltipRows(chart);
        await showChartTooltip(page, chart, values, 10_000, 1);
        for (const name of brokerNames) {
            const row = rows.filter({has: page.getByText(name, {exact: true})});
            await expect(row, `${name} has its own overlay line — exactly one row of the P&L tooltip`).toHaveCount(1);
            await expect(row).toBeVisible();
        }
        // The Total label is translated, so it is found as what it is: the one
        // value row that no broker's name labels.
        await expect(rowsNotLabelledBy(page, rows, brokerNames), 'exactly one row is not a broker — the Total').toHaveCount(1);

        // Total + one row per broker: more series than the single total line the
        // submode would draw without the G1a overlay — each an amount or `—`.
        await expect(values, 'Total + one value per broker, each an amount (sign optional) or —').toHaveText(new Array(brokers.length + 1).fill(PNL_LINE_VALUE));
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

        // …and the chart consumed them. The barrier is on the chart itself: until
        // the candle report is applied every bucket is the `'-'` gap sentinel, and a
        // tooltip raised then would honestly say "no data" about a chart that was
        // merely early.
        await expect.poll(async () => (await candleSeries(growthHost(chart))).bodies, {timeout: 15_000, message: 'the candle report reached the chart: its candlestick series carries real bodies'}).toBeGreaterThan(0);

        // The OHLC quad is recognised BY ROW, never by the absence of a sign: a
        // broker row whose value is zero prints unsigned too, so "unsigned" counted
        // brokers on the day the pointer landed on a flat one. A row is a broker's
        // iff its label is a broker name the report served (broker rows exist only
        // for a non-null value); every other value row is OHLC.
        const overview = reports.filter((call) => call.body.include_broker_pnl_history === true).at(-1);
        const brokerNames: string[] = (overview?.json?.broker_pnl_history ?? []).map((broker: {broker_name: string}) => broker.broker_name);
        const ohlcRows = rowsNotLabelledBy(page, tooltipRows(chart), brokerNames);

        // Raised on the header, not on the rows: a bucket without a candle prints the
        // no-data line instead of the quad, and that case must fail below with its
        // own name rather than as a tooltip that "never appeared".
        await showChartTooltip(page, chart, chart.getByText(TOOLTIP_DATE), 10_000, 1);
        await expect(ohlcRows, 'no candle under the pointer — the formatter printed its no-data line in place of the OHLC quad').not.toHaveCount(0);
        await expect(ohlcRows, 'open, close, high and low — exactly one OHLC quad').toHaveCount(4);
        await expect(ohlcRows.locator('xpath=./b'), 'each of the four is a real amount').toHaveText([PLAIN_AMOUNT, PLAIN_AMOUNT, PLAIN_AMOUNT, PLAIN_AMOUNT]);
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
        // happened to land on. The sign is optional for the same reason: the three
        // floor rows are always written, but on a week with no dividend and no
        // interest they are all zero, and a zero carries no sign.
        const amounts = chart.getByText(PNL_AMOUNT);
        await showChartTooltip(page, chart, amounts, 10_000, 3);
        await expect.poll(() => amounts.count(), {message: 'dividend, interest and their total are always in the income tooltip, zero or not'}).toBeGreaterThanOrEqual(3);
    });

    test('candles aggregate coarser than the line at the very same window', async ({page}) => {
        // A window change, a lazy candle fetch and three redraws, each against a
        // backend that runs FIFO at report time: more than one interaction's budget.
        test.setTimeout(60_000);
        const reports = await recordReports(page);
        const chart = await openGrowthChart(page);
        const host = growthHost(chart);
        const ladder = chart.getByTestId('growth-candle-width');
        const pressedRung = ladder.locator('[data-testid^="growth-candle-width-"][aria-pressed="true"]');
        // Scoped to the card: the badge belongs to whichever chart decided its own
        // resolution, and other charts on the page may carry theirs.
        const badge = chart.getByTestId('chart-resolution-badge');
        const overviews = () => reports.filter((call) => call.body.include_income_history === true);

        await selectGrowthMode(chart, 'pnl');
        await selectSubmode(chart, 'line');

        // Pin the window explicitly, through the control that owns it — the
        // date-range picker; the chart has no window selector of its own. The
        // comparison needs a window long enough for the two grammars to disagree:
        // the ladder counts the days the dashboard SERVED for the range, and at
        // the default 3M a daily body is wide enough to draw, so candles honestly
        // open at 1D there. 1Y is where it no longer is.
        const oneYear = page.getByTestId('date-preset-1y');
        await expect(oneYear).toHaveAttribute('data-active', 'false');
        const callsBefore = overviews().length;
        const rendersBefore = await chartRenders(host);
        await oneYear.click();
        await expect(oneYear).toHaveAttribute('data-active', 'true');
        await expect.poll(() => overviews().length, {timeout: 30_000, message: 'picking 1Y re-requests the overview report'}).toBeGreaterThan(callsBefore);
        await expect(page.getByTestId('dashboard-page')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(host).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});
        await expect.poll(() => chartRenders(host), {timeout: 15_000}).toBeGreaterThan(rendersBefore);

        const servedDays: number = overviews().at(-1)?.json?.history?.length ?? 0;
        expect(servedDays, 'the 1Y overview serves a daily history').toBeGreaterThan(0);

        // The two bounds the claim lives between: the line stays daily while it
        // has at most 1.3 buckets per pixel (a vertex survives sub-pixel density),
        // a candle needs a body of at least LADDER_MIN_BODY_PX. The canvas is wider
        // than the plot, so if the served days do not fit at that floor even across
        // the whole canvas, a 1D body cannot fit at any gutter size. Derived, never
        // hard-coded: a seed with fewer days would make the rest of this case true
        // for no reason, and must say so instead.
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const canvasWidth = await host.evaluate((node) => Number((node as any).__lfChart?.getWidth?.() ?? 0));
        expect(canvasWidth, 'the chart reports its canvas width').toBeGreaterThan(0);
        expect(servedDays * LADDER_MIN_BODY_PX, 'the seed no longer gives the 1Y window enough days for the 1D body floor').toBeGreaterThan(canvasWidth);

        // The line: one point per served day, read off the chart (the positive
        // statement), then no ladder and no badge (the badge renders only when the
        // resolution is not daily, so its absence is the UI saying "daily").
        await expect.poll(() => lineBuckets(host), {timeout: 15_000, message: 'the P&L line draws the 1Y window one point per served day'}).toBe(servedDays);
        await expect(ladder, 'the line has no candle-width ladder').toHaveCount(0);
        await expect(badge, 'the line at 1Y is daily, so no resolution badge').toHaveCount(0);

        // The candles, same window, same data, same plot: the ladder is in charge,
        // and the rung the geometry cannot draw is not offered.
        await selectSubmode(chart, 'candles');
        await expect(ladder).toBeVisible({timeout: 10_000});
        await expect(pressedRung, 'exactly one candle width is in force').toHaveCount(1);
        await expect(
            ladder.getByTestId('growth-candle-width-1d'),
            `${servedDays} daily bodies do not fit ${LADDER_MIN_BODY_PX}px each in a ${canvasWidth}px canvas, so 1D must not be offered — ` + 'if it is, the seeded history or the plot width moved, or the ladder fell back to its lone floor rung because no width fits at all',
        ).toHaveCount(0, {timeout: 10_000});
        await expect(pressedRung).not.toHaveAttribute('data-testid', 'growth-candle-width-1d');

        // …and the title's claim, measured on the chart itself: once the candle
        // report is drawn, the same window holds fewer bodies than the line had points.
        await expect.poll(async () => (await candleSeries(host)).bodies, {timeout: 20_000, message: 'the candle report reached the chart'}).toBeGreaterThan(0);
        await expect.poll(async () => (await candleSeries(host)).bodies, {message: 'candles group the served days coarser than the line draws them'}).toBeLessThan(servedDays);

        // And back — proving the grammar drove it, not a one-way drift that would
        // have made the middle assertions true for the wrong reason.
        await selectSubmode(chart, 'line');
        await expect.poll(() => lineBuckets(host), {timeout: 15_000, message: 'back on the line, one point per served day again'}).toBe(servedDays);
        await expect(ladder).toHaveCount(0);
        await expect(badge).toHaveCount(0);
    });

    test('the candle-width ladder is offered in candles and income, not in the line, and a rung regroups the candles', async ({page}) => {
        // Covered by nothing since the ladder replaced the zoom-window selector. The
        // ladder is the user's own choice of bucket width, so what matters is that it
        // exists exactly where a width can be chosen, that `aria-pressed` names the
        // one in force, and that choosing another one really regroups the chart.
        test.setTimeout(60_000);
        const chart = await openGrowthChart(page);
        const host = growthHost(chart);
        const ladder = chart.getByTestId('growth-candle-width');
        const rungs = ladder.locator('[data-testid^="growth-candle-width-"]');
        const pressedRung = ladder.locator('[data-testid^="growth-candle-width-"][aria-pressed="true"]');

        // Presence barrier for the negative: the line is pressed and drawn.
        await selectGrowthMode(chart, 'pnl');
        await selectSubmode(chart, 'line');
        await expect(host).toHaveAttribute('data-chart-ready', 'true');
        await expect(ladder, 'the line has no bucket width to choose').toHaveCount(0);

        await selectSubmode(chart, 'candles');
        await expect(ladder).toBeVisible({timeout: 10_000});
        // Read the offer only once the candle report is drawn: the rungs are a
        // function of the served days and the measured plot, both settled by then.
        await expect.poll(async () => (await candleSeries(host)).bodies, {timeout: 20_000, message: 'the candle report reached the chart'}).toBeGreaterThan(0);
        await expect(pressedRung, 'exactly one candle width is in force').toHaveCount(1);

        // The target comes from the offer as rendered, never from a hard-coded width:
        // which rungs exist is the geometry's call, not the test's.
        const offered = await rungs.evaluateAll((nodes) => nodes.map((node) => ({testId: node.getAttribute('data-testid') ?? '', pressed: node.getAttribute('aria-pressed') === 'true'})));
        expect(offered.length, 'precondition: the seeded window offers at least two candle widths, otherwise there is nothing to switch to').toBeGreaterThanOrEqual(2);
        const previousIndex = offered.findIndex((rung) => rung.pressed);
        const targetIndex = offered.findIndex((rung) => !rung.pressed);
        const previous = ladder.getByTestId(offered[previousIndex].testId);
        const target = ladder.getByTestId(offered[targetIndex].testId);

        const bucketsBefore = (await candleSeries(host)).points;
        const rendersBefore = await chartRenders(host);
        await target.click();
        await expect(target).toHaveAttribute('aria-pressed', 'true');
        await expect(previous).toHaveAttribute('aria-pressed', 'false');
        await expect(pressedRung, 'still exactly one width in force').toHaveCount(1);
        await expect.poll(() => chartRenders(host), {timeout: 15_000, message: 'choosing a width redraws the chart'}).toBeGreaterThan(rendersBefore);

        // A highlighted button would only prove the button. The consequence is the
        // bucket count: the offer is ordered from the finest width up, so a rung to
        // the right groups the same days into fewer candles, one to the left into more.
        const regrouped = expect.poll(async () => (await candleSeries(host)).points, {message: `${offered[targetIndex].testId} regroups the candles`});
        if (targetIndex > previousIndex) await regrouped.toBeLessThan(bucketsBefore);
        else await regrouped.toBeGreaterThan(bucketsBefore);

        // Income sizes its bars on the same ladder, from 1W up: a single day of
        // personal cash flow is almost always empty, so 1D and 3D are never offered.
        await selectSubmode(chart, 'income');
        await expect(ladder).toBeVisible({timeout: 10_000});
        await expect(pressedRung, 'exactly one bar width is in force').toHaveCount(1);
        await expect(ladder.getByTestId('growth-candle-width-1d')).toHaveCount(0);
        await expect(ladder.getByTestId('growth-candle-width-3d')).toHaveCount(0);
    });

    test('the P&L mode and submode survive an in-app navigation away and back', async ({page}) => {
        // S5: an in-app navigation unmounts the dashboard and remounts the chart on
        // the way back, which is where the choice used to be lost. A reload re-reads
        // the same storage from scratch and is a different path, so it does not prove
        // this one.
        test.setTimeout(60_000);
        const chart = await openGrowthChart(page);
        await selectGrowthMode(chart, 'pnl');
        await selectSubmode(chart, 'income');

        await page.getByTestId('nav-assets').click();
        await expect(page).toHaveURL(/\/assets(?:[/?#]|$)/);
        const assets = page.getByTestId('assets-page');
        await expect(assets).toBeVisible({timeout: 15_000});
        await expect(assets).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(page.getByTestId('dashboard-page'), 'the dashboard really unmounted — otherwise nothing is remounted on the way back').toHaveCount(0);

        await page.getByTestId('nav-dashboard').click();
        await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/);
        await expect(page.getByTestId('dashboard-page')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        const remounted = page.getByTestId('growth-chart');
        await expect(growthHost(remounted)).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});
        await expect(remounted.getByTestId('growth-toggle-pnl'), 'the P&L mode came back').toHaveAttribute('aria-pressed', 'true');
        await expect(remounted.getByTestId('growth-pnl-submode-income'), 'and so did the income submode').toHaveAttribute('aria-pressed', 'true');
    });
});

/**
 * Chart axes under privacy (S2a GrowthChart, S2b PerformanceChart).
 *
 * An axis label is canvas text: no DOM carries it. What reaches the canvas is
 * the formatter the chart handed ECharts, so these tests call that very function
 * — read through `__lfChart.getOption()` — on three fixed amounts: a positive
 * large enough for the compact suffix, a negative, and zero. `getOption()` is
 * read again on every call: a mask change re-applies the full option, so a
 * reference taken before the toggle is stale by design.
 *
 * The contract is D8: the magnitude is replaced whole, compact suffix included
 * (`•••k` would still disclose the order of magnitude); the sign stays outside
 * the mask. The minus is pinned as "a leading minus, then the placeholder,
 * nothing else", ASCII or U+2212: the glyph is the locale's business, "masked,
 * sign kept" is the contract.
 *
 * Parallel-safe: the preference lives in this context's localStorage only
 * (`librefolio-privacy`) and has no server-side twin. Whoever switches it on
 * switches it off, in `finally`.
 */
const AXIS_CLEAR = [expect.stringMatching(/^\d/), expect.stringMatching(/^[-\u2212]\d/), expect.stringMatching(/^\d/)];
const AXIS_MASKED = [expect.stringMatching(/^•••$/), expect.stringMatching(/^[-\u2212]•••$/), expect.stringMatching(/^•••$/)];
const AXIS_PERCENT = [expect.stringMatching(/^\d[\d.,]*%$/), expect.stringMatching(/^[-\u2212]\d[\d.,]*%$/), expect.stringMatching(/^\d[\d.,]*%$/)];

/** What the chart's own axis formatter prints for `values`, read fresh from `getOption()`. */
async function axisLabels(host: Locator, axis: 'xAxis' | 'yAxis', values: number[]): Promise<string[]> {
    return host.evaluate(
        (node, {axis, values}) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const formatter = (node as any).__lfChart?.getOption?.()?.[axis]?.[0]?.axisLabel?.formatter;
            return typeof formatter === 'function' ? values.map((value) => String(formatter(value))) : [];
        },
        {axis, values},
    );
}

/**
 * Flip the header's privacy toggle and wait for `host` to redraw under it.
 *
 * House style from privacy-masking.spec.ts: the header hides on scroll, so the
 * toggle is focused and the header proven pinned before the click; the state is
 * asserted on both sides. The renders counter is sampled before the click.
 */
async function setPrivacy(page: Page, on: boolean, host: Locator): Promise<void> {
    const toggle = page.getByTestId('privacy-toggle');
    await expect(toggle, 'privacy must start from the opposite state').toHaveAttribute('aria-pressed', String(!on));
    const before = await chartRenders(host);
    await toggle.focus();
    await expect(page.getByTestId('app-header')).toHaveAttribute('data-scroll-state', 'pinned');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-pressed', String(on));
    await expect.poll(() => chartRenders(host), {timeout: 15_000, message: 'the chart redraws when privacy flips'}).toBeGreaterThan(before);
}

/** The `finally` half: privacy ends OFF whatever happened — asked first, clicked only if needed. */
async function restorePrivacyOff(page: Page): Promise<void> {
    const toggle = page.getByTestId('privacy-toggle');
    if ((await toggle.getAttribute('aria-pressed')) === 'true') {
        await toggle.focus();
        await expect(page.getByTestId('app-header')).toHaveAttribute('data-scroll-state', 'pinned');
        await toggle.click();
    }
    await expect(toggle).toHaveAttribute('aria-pressed', 'false');
}

test.describe('Chart axes under privacy (S2a/S2b)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('GrowthChart masks its amount axis in Abs and P&L, keeps the sign, and leaves % readable', async ({page}) => {
        // Abs and P&L share the amount formatter, % has its own: the over-masking
        // control is as much the contract as the masking — a ratio discloses no
        // amount, and a chart that masked it would hide the one view privacy leaves.
        test.setTimeout(60_000);
        const chart = await openGrowthChart(page);
        const host = growthHost(chart);
        const yLabels = () => axisLabels(host, 'yAxis', [20_000, -5_000, 0]);

        try {
            await selectGrowthMode(chart, 'eur');
            await expect.poll(yLabels, {message: 'Abs, privacy off: the amount axis prints its digits'}).toEqual(AXIS_CLEAR);
            await selectGrowthMode(chart, 'pnl');
            await selectSubmode(chart, 'line');
            await expect.poll(yLabels, {message: 'P&L line, privacy off: digits'}).toEqual(AXIS_CLEAR);

            await setPrivacy(page, true, host);
            await expect.poll(yLabels, {message: 'P&L line, privacy on: magnitude and suffix masked, sign kept'}).toEqual(AXIS_MASKED);
            await selectGrowthMode(chart, 'eur');
            await expect.poll(yLabels, {message: 'Abs, privacy on: masked the same way'}).toEqual(AXIS_MASKED);

            // Only meaningful where the portfolio really has % data: the toggle is
            // disabled otherwise, and that has to fail as a precondition, not skip.
            await expect(chart.getByTestId('growth-toggle-pct'), 'precondition: the seeded portfolio has % data, so the % toggle is enabled').toBeEnabled();
            await selectGrowthMode(chart, 'pct');
            await expect.poll(yLabels, {message: '%, privacy on: still digits — a ratio is not an amount'}).toEqual(AXIS_PERCENT);

            await selectGrowthMode(chart, 'eur');
            await setPrivacy(page, false, host);
            await expect.poll(yLabels, {message: 'Abs, privacy off again: the digits are back'}).toEqual(AXIS_CLEAR);
        } finally {
            await restorePrivacyOff(page);
        }
    });

    test('PerformanceChart masks its amount axis under privacy, zero included, and unmasks it', async ({page}) => {
        // The zero is part of the contract: `axisTickAmount` masks it explicitly
        // instead of letting it through as "no amount", so every tick of a masked
        // axis reads the same. A regression that special-cased zero shows here.
        test.setTimeout(60_000);
        await openPositionsTab(page);
        await page.getByTestId('positions-toggle-performance').click();
        await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await page.getByTestId('positions-toggle-map').click();
        const chart = page.getByTestId('performance-chart');
        await expect(chart).toBeVisible({timeout: 15_000});
        const host = chart.locator('[data-chart-ready]');
        await expect(host).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});
        const xLabels = () => axisLabels(host, 'xAxis', [1_500, -1_500, 0]);

        try {
            await expect.poll(xLabels, {message: 'privacy off: the amount axis prints its digits'}).toEqual(AXIS_CLEAR);
            await setPrivacy(page, true, host);
            await expect.poll(xLabels, {message: 'privacy on: every tick masked, the zero included, the sign kept'}).toEqual(AXIS_MASKED);
            await setPrivacy(page, false, host);
            await expect.poll(xLabels, {message: 'privacy off again: the digits are back'}).toEqual(AXIS_CLEAR);
        } finally {
            await restorePrivacyOff(page);
        }
    });
});

/**
 * S9 — the synthetic-candles caption at phone width.
 *
 * The caption is the mandatory disclosure that the candles are synthetic. At
 * phone width it must neither wrap (one line, the short register) nor be cut
 * silently: it scrolls, and `scrollOnOverflow` publishes that it does with
 * `data-overflowing="true"`, reduced motion or not. The short caption is 70–80
 * characters in all four locales against ~294px available at 375px (measured
 * in S6: scrollWidth 408 > clientWidth 294), so it overflows in every language —
 * the assertion rests on geometry, not on a translated string.
 *
 * `setViewportSize` inside the test, as the F1 guard above does, so the case is
 * the same on every project it runs under.
 */
test.describe('GrowthChart candles caption at phone width (S9)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('the synthetic-candles caption stays on one line and scrolls where it does not fit', async ({page}) => {
        test.setTimeout(60_000);
        await page.setViewportSize({width: 375, height: 800});
        const chart = await openGrowthChart(page);
        await selectGrowthMode(chart, 'pnl');
        await selectSubmode(chart, 'candles');

        const caption = chart.getByTestId('growth-pnl-candles-hypothetical-label');
        await expect(caption).toBeVisible({timeout: 10_000});
        await expect(caption, 'one line: the caption never wraps').toHaveCSS('white-space', 'nowrap');
        await expect(caption, 'at 375px it does not fit, and says so').toHaveAttribute('data-overflowing', 'true', {timeout: 10_000});
    });
});
