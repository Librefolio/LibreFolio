import {expect, test, type Locator, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {focusHeaderControlByKeyboard} from '../fixtures/headerKeyboardFocus';
import {TEST_USER} from '../fixtures/test-users';

/**
 * The allocation pie of an overdrawn portfolio: the negative cash note (backlog 54-1 and Y-6, developer decision 49;
 * workstream Y, lot Y10).
 *
 * ## What it protects
 *
 * With the cash below zero the backend, which decision 49 leaves untouched, sends the summary's `allocation_by_type`
 * and `allocation_by_sector` with the cash as a `Liquidity` row whose `value` (a share of the NET total) and `amount`
 * are negative, and positive shares adding up past 100; `allocation_by_geography` never holds the cash. Decision 49 and
 * its night decisions («Y10 — analisi», points 1–6, `plan-phase01DashboardCharts.prompt.md`), on the pie's side:
 *
 * - the pie keeps only the positive shares, as it does today;
 * - a caption under the pie, `allocation-negative-cash-note`, on the type tab and on the sector tab, states the
 *   backend's `Liquidity.amount` as the panel writes its other amounts (`formatCurrencyAmountPlain`);
 * - with privacy on, its digits are masked and the minus stays outside the mask (D8: `-••• € 🇪🇺 EUR`), and it follows
 *   the header toggle in place, both ways, like every amount of the dashboard (R20);
 * - no note when the cash is not negative.
 *
 * The history chart's axis, below 0 and past 100, is pinned by `AllocationHistoryChart.negativeCash.test.ts`: nothing
 * here reads a canvas for it. `AllocationPanel.negativeCash.test.ts` pins the same note on the component, Y-6 included;
 * this spec checks it through the real page, the real report and the real header toggle.
 *
 * ## Why it is red today
 *
 * Y10 is not implemented: the panel renders no note. The two tests that read it fail at their first assertion on it,
 * once every precondition and barrier before it has passed, so the red is the missing note and nothing else. The other
 * two are guards, green today and to stay green: the pie draws no arc for the cash, and a portfolio without negative
 * cash shows no note.
 *
 * ## The overdraft: intercepted, never written
 *
 * No populated portfolio is overdrawn (`populate_mock_data.py` gives every broker `allow_cash_overdraft: False`) and
 * none is made here (night decision 5: the shared seed stays as it is). The panel reads the `summary` block of
 * `POST /api/v1/portfolio/report` (`portfolioStore.fetchReport`, applied by the Dashboard's `applyReport`; there is no
 * `/portfolio/summary` route). A page-scoped `page.route` fetches the real response and rewrites only the two lists that
 * carry the cash, as `_alloc` (`derived_views.py`) would write them with the cash at minus a sixth of the positions P:
 * the position rows as served, one `Liquidity` row at −P/6, every share taken again on the new net total, 5P/6. The
 * positives add up to about 120 and the cash is −20: the Vitest's `OVERDRAWN` picture, on TEST_USER's real positions.
 * The geography list is left as served: it holds no cash, and its shares are on the positions alone. Everything else
 * in the response is the backend's, and the rewritten summary is checked against the schema the generated client
 * validates the report with. Nothing is written anywhere: the route lives in this test's page and privacy in this
 * context's localStorage, so the tests are parallel-safe by construction.
 *
 * ## How it is read
 *
 * - The note by its test id, inside the panel. Its amount by locale-proof parts: the minus (ASCII as the formatter
 *   writes it, or U+2212), the digits of the served cash with whatever group and decimal marks the interface locale
 *   puts between them, and the ISO code of the currency the page asked its report in. The symbol and the flag are
 *   optional, since the currency catalogue may land after the first render (`privacy-masking.spec.ts` tolerates the
 *   same); the sentence around the amount is not read: it is translated, and its wording is not settled.
 * - Every assertion under the pie stands on a barrier: the pie of the tab has finished drawing (`data-chart-ready`)
 *   and is on screen. The pie is read through its `__lfChart` hook, as `dashboard.spec.ts` reads its colours, and its
 *   shares must add up past 100: proof that it was drawn from the rewritten report.
 * - The legend is drawn on the canvas: there is no legend DOM, so the legend is not read. What is read instead is the
 *   option ECharts was handed, the arcs a pie's legend takes its entries from (the pie sets no `legend.data`).
 * - Privacy is flipped from the header as `privacy-masking.spec.ts` flips it, the toggle reached by keyboard so the
 *   header is pinned (`headerKeyboardFocus.ts`).
 *
 * It runs in an E2E slot of its own.
 */

// ============================================================================
// Constants and shapes
// ============================================================================

/** The Dashboard's report, whose `summary` block AllocationPanel reads: `POST /api/v1/portfolio/report`. */
const REPORT_URL = /\/api\/v1\/portfolio\/report(?:\?.*)?$/;

/** The row the backend writes the cash into, by type and by sector (`daily_state.py`, step 4h). */
const LIQUIDITY = 'Liquidity';

/** The caption decision 49 adds under the pie. */
const NOTE_TESTID = 'allocation-negative-cash-note';

/**
 * `PRIVACY_PLACEHOLDER` of `src/lib/utils/privacy/maskable.ts`, copied as `privacy-masking.spec.ts` copies it: that
 * module imports the runes privacy store, which Playwright's loader cannot compile.
 */
const PLACEHOLDER = '•••';

/** The two tabs whose lists carry the cash: the two the note goes under. */
const PIE_TABS = ['type', 'sector'] as const;

type PieTab = (typeof PIE_TABS)[number];

/**
 * The pie's container: the element of the panel that publishes a finished first render, other than the history chart,
 * which is always mounted and hidden in the «now» view.
 */
const PIE_HOST = '[data-chart-ready="true"]:not([data-testid="allocation-history-chart"])';

/** The report runs FIFO at runtime: under load the Dashboard settles later than a default assertion waits. */
const REPORT_TIMEOUT = 30_000;
/** From the summary on screen to the pie's first finished render, its animation included. */
const CHART_TIMEOUT = 15_000;
/** What is left once the Dashboard has its report: a re-render, never a round trip. */
const UI_TIMEOUT = 5_000;
/**
 * A funded portfolio's shares add up to 100 and the rewritten ones to about 120: a pie whose shares add up past 105
 * was drawn from the rewritten report, whatever the rounding.
 */
const OVERDRAWN_SHARE_FLOOR = 105;

/** One `AllocationItem` as the backend serialises it (`schemas/portfolio.py`): the share and the amount are decimal strings. */
type AllocationItem = {name: string; value: string; amount: string; emoji?: string | null};

/** The part of a report's `summary` this spec reads and rewrites. */
type ReportSummary = {net_worth?: {code?: string}; allocation_by_type?: AllocationItem[]; allocation_by_sector?: AllocationItem[]};

/** A `/portfolio/report` body, as far as this spec opens it. */
type ReportBody = {summary?: ReportSummary | null};

/** What the stub wrote into one report. */
interface Overdraft {
    /** The cash of both rewritten lists, as the backend writes an amount: a signed decimal string. */
    cash: string;
    /** The currency of the report's amounts: the one the page asked for, which is the one it displays them in. */
    currency: string;
    /** The signed total the rewritten type list takes its shares on: the overdrawn net worth. */
    netByType: number;
    /** The same total, for the sector list. */
    netBySector: number;
    /** Why the rewritten summary fails the schema the generated client validates the report with; null when it passes. */
    schemaError: string | null;
}

/** The part of the pie's ECharts instance this spec reads: the option the pie handed it. */
type PieDatum = {name?: unknown; rawName?: unknown; primaryKey?: unknown; value?: unknown};
type PieSeries = {type?: unknown; id?: unknown; data?: PieDatum[]};
type ChartHook = {isDisposed?: () => boolean; getOption: () => {series?: PieSeries[]}};

/** One arc as the pie handed it to ECharts: the backend's key, the family it is filed under on the type pie, its share. */
type PieArc = {rawName: string; primaryKey: string | null; value: number};

/** The pie on screen: the dimension it draws, every arc of every ring, and the shares of its base ring added up. */
type PieDrawing = {mode: PieTab; arcs: PieArc[]; shareSum: number};

// ============================================================================
// The overdraft: the report, rewritten in this page only
// ============================================================================

type RouteHandler = Parameters<Page['route']>[1];

/**
 * `page.route` with a callback that absorbs its own failure (`routeQuietly` of `default-currency.spec.ts`, itself
 * copied from `risk-lab.spec.ts`). Nobody awaits a route callback, so what it throws is an unhandled rejection pinned on
 * whatever the worker runs next, and `route.fetch()` rejects once the context closes under it. Absorbed, not hidden:
 * the request is left unanswered, and the test that needed it fails on its own barrier (`servedOverdraft`, the pie).
 */
async function routeQuietly(page: Page, url: RegExp, handler: RouteHandler): Promise<void> {
    await page.route(url, async (route, request) => {
        try {
            await handler(route, request);
        } catch (error) {
            console.warn(`[allocation-negative-cash] left ${request.method()} ${request.url()} unanswered: its route callback failed with ${String(error)}`);
        }
    });
}

/** The positions of an allocation list: every row but the cash. */
function positionsOf(items: AllocationItem[]): AllocationItem[] {
    return items.filter(({name}) => name !== LIQUIDITY);
}

/** What rows add up to: the signed total `_alloc` takes every share on. */
function totalOf(items: AllocationItem[]): number {
    return items.reduce((sum, {amount}) => sum + Number(amount), 0);
}

/**
 * `items` as `_alloc` (`derived_views.py`) would write them with `cash` in the account: the position rows as served,
 * the cash as one `Liquidity` row, and every share taken again on the new signed total (amount over the sum of the
 * list, ×100, two decimals). With a negative cash the positives add up past 100 and the cash goes below zero. The
 * backend sorts by amount, so the positions keep their order and the cash goes last; its emoji is the backend's own.
 */
function withCash(items: AllocationItem[], cash: number): AllocationItem[] {
    const positions = positionsOf(items);
    const total = totalOf(positions) + cash;
    const share = (amount: number) => ((amount / total) * 100).toFixed(2);
    const emoji = items.find(({name}) => name === LIQUIDITY)?.emoji ?? null;
    return [...positions.map((item) => ({...item, value: share(Number(item.amount))})), {name: LIQUIDITY, value: share(cash), amount: cash.toFixed(2), emoji}];
}

/** A Zod failure in one line: where, and why, issue by issue. */
function describeIssues(issues: ReadonlyArray<{path: ReadonlyArray<string | number>; message: string}>): string {
    return issues.map(({path, message}) => `${path.join('.')}: ${message}`).join('; ');
}

/**
 * Answers every portfolio report of this page with the backend's own response, overdrawn: the cash at minus a sixth of
 * the positions, written into the type and the sector list (`withCash`), one cash for both as the backend has one. A
 * response that is not a summary with both lists (an error, a report asked without a summary) passes untouched.
 * Installed after the sign-in and before the Dashboard is loaded as a fresh document, so every report that document
 * asks for goes through it. Returns the live tally of what was written, one entry per rewritten report.
 */
async function serveOverdrawnReport(page: Page): Promise<Overdraft[]> {
    const served: Overdraft[] = [];
    await routeQuietly(page, REPORT_URL, async (route, request) => {
        if (request.method() !== 'POST') {
            await route.fallback();
            return;
        }
        const response = await route.fetch();
        const body = response.ok() ? ((await response.json()) as ReportBody | null) : null;
        const summary = body?.summary;
        if (!summary?.allocation_by_type || !summary.allocation_by_sector) {
            await route.fulfill({response});
            return;
        }
        const positions = {type: totalOf(positionsOf(summary.allocation_by_type)), sector: totalOf(positionsOf(summary.allocation_by_sector))};
        const cash = -Math.round((positions.type / 6) * 100) / 100;
        summary.allocation_by_type = withCash(summary.allocation_by_type, cash);
        summary.allocation_by_sector = withCash(summary.allocation_by_sector, cash);
        const check = schemas.PortfolioSummary.safeParse(summary);
        const asked = (request.postDataJSON() as {target_currency?: unknown} | null)?.target_currency;
        const currency = typeof asked === 'string' && asked !== '' ? asked : summary.net_worth?.code;
        served.push({
            cash: cash.toFixed(2),
            currency: currency ?? '',
            netByType: positions.type + cash,
            netBySector: positions.sector + cash,
            schemaError: check.success ? null : describeIssues(check.error.issues),
        });
        await route.fulfill({response, json: body});
    });
    return served;
}

/**
 * The overdraft this page was served, checked before anything is asserted on it: the Dashboard asked for its report
 * and the stub rewrote it; every rewrite passes the schema the client validates the report with; all of them carry one
 * cash in one currency, so whichever the panel shows, it shows that one; the cash is below zero, and the net worth the
 * shares are taken on is still above zero: an overdrawn portfolio, not an insolvent one.
 */
async function servedOverdraft(served: Overdraft[]): Promise<Overdraft> {
    await expect.poll(() => served.length, {message: 'the Dashboard asked for its report, and the stub rewrote one carrying both lists', timeout: UI_TIMEOUT}).toBeGreaterThan(0);
    expect(
        served.map(({schemaError}) => schemaError).filter((error) => error !== null),
        'the rewritten summary fails the schema the generated client validates the report with',
    ).toEqual([]);
    expect([...new Set(served.map(({cash, currency}) => `${cash} ${currency}`))], 'every report of this page was rewritten to one cash, in one currency').toHaveLength(1);
    // Every entry is that one overdraft, by the assertion above.
    const [overdraft] = served;
    expect(Number(overdraft.cash), 'the cash written is below zero: it is minus a sixth of the positions TEST_USER holds (check populate_mock_data.py)').toBeLessThan(0);
    expect(overdraft.currency, 'the currency the page asked its report in').toMatch(/^[A-Z]{3}$/);
    expect(
        served.filter(({netByType, netBySector}) => !(netByType > 0 && netBySector > 0)),
        'a rewrite whose net worth is not above zero: insolvent, not overdrawn',
    ).toEqual([]);
    return overdraft;
}

// ============================================================================
// The served report, observed without interception
// ============================================================================

/** The summary of a finished report request; nothing when its body is no longer there to read. */
async function summaryOf(request: Request): Promise<ReportSummary | null> {
    try {
        const response = await request.response();
        return ((await response?.json()) as ReportBody | null | undefined)?.summary ?? null;
    } catch {
        return null;
    }
}

/**
 * Every report summary this page is served, read off the wire once its request has finished: observation only, so
 * nothing is routed and nothing is answered differently. `requestfinished` rather than `response`: a request a
 * navigation cuts short ends in `requestfailed` and is never read. Armed before the load; each call awaits the reads
 * so far.
 */
function observeReportSummaries(page: Page): () => Promise<ReportSummary[]> {
    const reads: Array<Promise<ReportSummary | null>> = [];
    page.on('requestfinished', (request) => {
        if (request.method() === 'POST' && REPORT_URL.test(request.url())) reads.push(summaryOf(request));
    });
    return async () => (await Promise.all(reads)).filter((summary): summary is ReportSummary => summary !== null);
}

/** The cash rows below zero in what the page was served: the type and the sector list, the two that carry the cash. */
function negativeCashIn(summaries: ReportSummary[]): AllocationItem[] {
    return summaries.flatMap(({allocation_by_type = [], allocation_by_sector = []}) => [...allocation_by_type, ...allocation_by_sector]).filter(({name, amount}) => name === LIQUIDITY && Number(amount) < 0);
}

// ============================================================================
// The panel and its pie
// ============================================================================

/** Opens the Dashboard as a fresh document and waits for its report: the panel on screen, its summary in. */
async function openAllocationPanel(page: Page): Promise<Locator> {
    await navigateTo(page, '/dashboard');
    await expect(page.getByTestId('dashboard-page'), 'the Dashboard has its report').toHaveAttribute('data-busy', 'false', {timeout: REPORT_TIMEOUT});
    const panel = page.getByTestId('allocation-panel');
    await expect(panel).toBeVisible();
    return panel;
}

/**
 * The «now» view on `tab`. Both controls are setters, so a click on the selected one keeps it selected, and both
 * persist per user (S4): they are selected, never assumed, and `aria-pressed` is the state each one publishes.
 */
async function showNow(panel: Locator, tab: PieTab): Promise<void> {
    const now = panel.getByTestId('allocation-view-now');
    await now.click();
    await expect(now).toHaveAttribute('aria-pressed', 'true');
    const dimension = panel.getByTestId(`allocation-tab-${tab}`);
    await dimension.click();
    await expect(dimension).toHaveAttribute('aria-pressed', 'true');
}

/**
 * The pie of the «now» view as it was handed to ECharts, read through its test hook (`__lfChart`, set by
 * AllocationPieChart as by PriceChartFull), or null while none has finished drawing. A type pie files every arc under a
 * family (`primaryKey`), a sector pie files none: `dashboard.spec.ts` tells them apart the same way. It never throws,
 * because `expect.poll` stops at the first throw instead of polling on.
 */
async function readPie(panel: Locator): Promise<PieDrawing | null> {
    return panel.evaluate((root, selector): PieDrawing | null => {
        for (const host of Array.from(root.querySelectorAll(selector))) {
            try {
                const chart = (host as Element & {__lfChart?: ChartHook}).__lfChart;
                if (!chart || chart.isDisposed?.()) continue;
                const series = (chart.getOption().series ?? []).filter((entry) => entry?.type === 'pie');
                const arcsOf = (entry: PieSeries): PieArc[] => (entry.data ?? []).map((datum) => ({rawName: String(datum?.rawName ?? datum?.name ?? ''), primaryKey: typeof datum?.primaryKey === 'string' ? datum.primaryKey : null, value: Number(datum?.value)}));
                const arcs = series.flatMap(arcsOf);
                if (arcs.length === 0) continue;
                // The base ring when the type pie draws two (D72); otherwise the one pie series there is.
                const base = series.find((entry) => entry.id === 'alloc-base') ?? series[0];
                return {mode: arcs.every(({primaryKey}) => primaryKey !== null) ? 'type' : 'sector', arcs, shareSum: arcsOf(base).reduce((sum, {value}) => sum + value, 0)};
            } catch {
                continue;
            }
        }
        return null;
    }, PIE_HOST);
}

/**
 * Barrier: the pie of `tab` has finished its first render (`data-chart-ready`, set on ECharts' `finished`) and is on
 * screen, so the summary is in and the «now» view around the pie has rendered. Returns what the pie drew.
 */
async function drawnPie(panel: Locator, tab: PieTab): Promise<PieDrawing> {
    await expect.poll(async () => (await readPie(panel))?.mode ?? 'no pie drawn', {message: `the ${tab} pie finishes drawing`, timeout: CHART_TIMEOUT}).toBe(tab);
    await expect(panel.locator(PIE_HOST), `the ${tab} pie is on screen`).toBeVisible();
    const pie = await readPie(panel);
    if (!pie || pie.mode !== tab) throw new Error(`the ${tab} pie finished drawing, then left the panel`);
    return pie;
}

/** The pie of `tab`, drawn from the rewritten report: its shares, taken on the overdrawn net worth, add up past 100. */
async function drawnOverdrawnPie(panel: Locator, tab: PieTab): Promise<PieDrawing> {
    const pie = await drawnPie(panel, tab);
    expect(pie.shareSum, `the ${tab} pie was drawn from the rewritten report: its shares add up to about 120, not 100`).toBeGreaterThan(OVERDRAWN_SHARE_FLOOR);
    return pie;
}

/** The cash under either key the pie may carry it: `Liquidity` as the backend names the row, `LIQUIDITY` as the type pie files its family. */
function isLiquidity(key: string | null): boolean {
    return key?.toUpperCase() === LIQUIDITY.toUpperCase();
}

// ============================================================================
// Privacy, and the amount as it must read
// ============================================================================

/**
 * Flips privacy from the header, asserting the state before and after (`flipPrivacy` of `privacy-masking.spec.ts`).
 * The header slides away on scroll, and the panel's controls scroll the page: a header control reached by keyboard
 * pins the header (`headerKeyboardFocus.ts`), so the click lands on the toggle and not where it was.
 */
async function flipPrivacy(page: Page, on: boolean): Promise<void> {
    const header = page.getByTestId('app-header');
    const toggle = header.getByTestId('privacy-toggle');
    await expect(toggle, `privacy starts ${on ? 'off' : 'on'}`).toHaveAttribute('aria-pressed', String(!on));
    await focusHeaderControlByKeyboard(page, 'privacy-toggle');
    await expect(header).toHaveAttribute('data-scroll-state', 'pinned');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-pressed', String(on));
}

function escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * A group mark between two digits, as the interface locales write one: `,` (en), `.` (it, es), a narrow no-break space
 * (fr), an apostrophe (Swiss regions), or none (es leaves four digits ungrouped).
 */
const GROUP_MARK = `(?:[.,'’]|\\s)?`;

/** The digits of the served cash, its sign aside, with any interface locale's marks: `8,333.33`, `8.333,33`, `8 333,33`, `8333,33`. */
function cashDigitsSource({cash}: Overdraft): string {
    const [integer, fraction] = cash.replace(/^-/, '').split('.');
    return `${integer.split('').join(GROUP_MARK)}[.,]${fraction}`;
}

/**
 * What follows the number in an amount `formatCurrencyAmountPlain` writes (`number symbol flag CODE`): the symbol and
 * the flag once the currency catalogue has landed, the bare code before it (`privacy-masking.spec.ts` tolerates the
 * same, for the same reason), then the ISO code.
 */
function currencyTail(code: string): string {
    return `(?:\\s+[^\\s\\d]+)*?\\s+${escapeRegExp(code)}(?![A-Za-z])`;
}

/** The served cash in the clear: the minus (ASCII as the formatter writes it, or U+2212) against its digits, then the currency. */
function clearCash(overdraft: Overdraft): RegExp {
    return new RegExp(`[-\\u2212]${cashDigitsSource(overdraft)}${currencyTail(overdraft.currency)}`);
}

/** The served cash masked (D8): the minus outside the mask, the placeholder where the digits were, the currency kept. */
function maskedCash(overdraft: Overdraft): RegExp {
    return new RegExp(`[-\\u2212]${escapeRegExp(PLACEHOLDER)}${currencyTail(overdraft.currency)}`);
}

/** The digits of the served cash, wherever they would stand: what the mask must leave nowhere in the note. */
function cashDigits(overdraft: Overdraft): RegExp {
    return new RegExp(cashDigitsSource(overdraft));
}

// ============================================================================
// The tests
// ============================================================================

test.describe('Allocation pie of an overdrawn portfolio: the negative cash note (decision 49)', () => {
    // A sign-in, a fresh Dashboard whose report runs FIFO at runtime, and up to two pies drawn: more than the 30 s
    // default on a loaded lane, as dashboard.spec.ts allows its heavier cases.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('type and sector tabs: the note states the served negative cash, signed, in the currency on screen', async ({page}) => {
        // CONTRACT: decision 49. The overdraft the pie cannot draw is stated under it, on both tabs whose lists carry
        // the cash, as the panel writes its amounts. RED TODAY: the panel renders no note; `toAllocEntries` drops the
        // negative row and nothing takes its place.
        const served = await serveOverdrawnReport(page);
        const panel = await openAllocationPanel(page);
        const overdraft = await servedOverdraft(served);
        const note = panel.getByTestId(NOTE_TESTID);

        for (const tab of PIE_TABS) {
            await showNow(panel, tab);
            await drawnOverdrawnPie(panel, tab);
            await expect(note, `${tab} tab: the negative cash note`).toBeVisible({timeout: UI_TIMEOUT});
            await expect(note, `${tab} tab: ${overdraft.cash} ${overdraft.currency}, signed, in its currency`).toHaveText(clearCash(overdraft));
        }
    });

    test('privacy on: the digits of the note hide in place, the minus and the currency stay (D8); off again, they come back', async ({page}) => {
        // CONTRACT: decision 49 and D8. The note's amount is the user's money: privacy puts the placeholder where its
        // digits were, keeps the minus outside it and the currency after it, and the note follows the header toggle in
        // place, both ways, like every amount of the dashboard (R20: a formatter call frozen at mount would not).
        // RED TODAY: there is no note.
        const served = await serveOverdrawnReport(page);
        const panel = await openAllocationPanel(page);
        const overdraft = await servedOverdraft(served);
        await showNow(panel, 'type');
        await drawnOverdrawnPie(panel, 'type');
        const note = panel.getByTestId(NOTE_TESTID);

        // The positive control the masked form is measured against: the amount in the clear.
        await expect(note, 'privacy off: the negative cash note').toBeVisible({timeout: UI_TIMEOUT});
        await expect(note, 'privacy off: the amount in the clear').toHaveText(clearCash(overdraft));

        await flipPrivacy(page, true);
        await expect(note, 'privacy on: the minus outside the mask, the placeholder, the currency (D8)').toHaveText(maskedCash(overdraft), {timeout: UI_TIMEOUT});
        await expect(note, 'privacy on: no digit of the cash is left').not.toHaveText(cashDigits(overdraft));

        await flipPrivacy(page, false);
        await expect(note, 'privacy off again: the amount is back in the clear, in place').toHaveText(clearCash(overdraft), {timeout: UI_TIMEOUT});
        await expect(note).not.toContainText(PLACEHOLDER);
    });

    test('the pie keeps only the positive shares: no arc for the cash, on the type tab nor on the sector tab (green today, must stay green)', async ({page}) => {
        // CONTRACT: decision 49 keeps the pie to the positive shares: an arc cannot be negative, and the cash goes to
        // the note. Guards `toAllocEntries` (drops `value <= 0`) and the pie's own `> 0` filter against a fix that lets
        // the cash through. The legend is canvas-only and is not read; the arcs are, the entries a pie's legend is made
        // of (the pie sets no `legend.data`). GREEN TODAY.
        const served = await serveOverdrawnReport(page);
        const panel = await openAllocationPanel(page);
        await servedOverdraft(served);

        for (const tab of PIE_TABS) {
            await showNow(panel, tab);
            const pie = await drawnOverdrawnPie(panel, tab);
            expect(
                pie.arcs.filter(({rawName, primaryKey}) => isLiquidity(rawName) || isLiquidity(primaryKey)),
                `${tab} pie: arcs drawn for the cash`,
            ).toEqual([]);
            expect(
                pie.arcs.filter(({value}) => !(value > 0)),
                `${tab} pie: arcs that are not a positive share`,
            ).toEqual([]);
        }
    });

    test('no negative cash: no note under the type pie nor under the sector pie (green today, must stay green)', async ({page}) => {
        // CONTRACT: decision 49. The note states an overdraft; a portfolio whose cash is not negative has none to
        // state. Nothing is routed here: the page reads the backend's own report. GREEN TODAY: there is no note at all.
        const summaries = observeReportSummaries(page);
        const panel = await openAllocationPanel(page);

        // Precondition, read off what this page was served rather than inferred from the seed: no negative cash.
        await expect.poll(async () => (await summaries()).length, {message: 'the Dashboard was served its report', timeout: UI_TIMEOUT}).toBeGreaterThan(0);
        expect(negativeCashIn(await summaries()), 'TEST_USER’s report carries no overdraft: every seeded broker has allow_cash_overdraft False (populate_mock_data.py)').toEqual([]);

        for (const tab of PIE_TABS) {
            await showNow(panel, tab);
            // Presence barrier: the pie of this tab has drawn and is on screen, so the view a note would sit in has
            // rendered, and the absence below is not a matter of time. The question is what the user sees, so the
            // matcher is visibility: no note, absent or hidden alike (the component test pins the DOM absence).
            await drawnPie(panel, tab);
            await expect(panel.getByTestId(NOTE_TESTID), `${tab} tab: a note with no overdraft to state`).toBeHidden();
        }
    });
});
