/**
 * FX Detail Page — the rolling return (lot X5-F1)
 *
 * The asset detail page has two primary modes, prices and the calendar rolling return, with the window controls of the
 * latter. The FX pair page now has them too, under its own test ids (`fx-chart-primary-*`, `fx-calendar-window-*`):
 *
 * - the chart card `fx-detail-chart` publishes `data-primary-mode` (`price` | `calendar-return`) and, in the rolling return,
 *   `data-window-days`, `data-series-state` and, per state, the `fx-pair` signals it compares
 *   (`data-calendar-comparison-ready` / `-partial` / `-unavailable` / `-error`, config ids comma-joined);
 * - switching to the rolling return sends ONE `POST /api/v1/fx/currencies/convert` with an item for the pair and one more
 *   per saved `fx-pair` signal, each with a single signal `{instance_id, signal_code, params: {window_days}}`; a preset sends
 *   a new request with its window; going back to prices sends nothing (the rates are in the store);
 * - the mode is saved with the pair's chart settings (`primaryView`), so a reload, or a pair saved in the rolling return,
 *   opens in it.
 *
 * Every spec runs against the seeded EUR-USD (years of daily rates) and, for the comparison, EUR-GBP. Nothing shared is
 * written: the chart settings live in this browser context's localStorage, which Playwright gives each test of its own.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force); EUR-USD and EUR-GBP must exist.
 */

import type {Page, Request} from '@playwright/test';
import {expect, test} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
import {pairComparison, type SavedComparison} from '../fixtures/chartComparisons';
import {expectPairLineDrawn} from '../fixtures/pairLine';
import {daysAgoIso} from '../fixtures/dates';
import {TEST_USER} from '../fixtures/test-users';

const CONVERT_PATH = '/api/v1/fx/currencies/convert';
const CHART = 'fx-detail-chart';
/** The page's pair (canonical, so the chart settings are keyed by it) and the pair its saved comparison draws. */
const OWN = 'EUR-USD';
const OTHER = 'EUR-GBP';
/** What the page asks for: the detail's instance id and the backend's code for the calendar rolling return (`priceChartHelpers.ts`; a spec cannot import `$lib`). */
const CALENDAR_INSTANCE_ID = 'asset-calendar-return';
const CALENDAR_SIGNAL_CODE = 'ASSET_CALENDAR_ROLLING_RETURN';
/** A period of 179 days ending yesterday: the largest preset that fits it is 3 months (90 days), the window the page starts on. */
const range = () => ({start: daysAgoIso(180), end: daysAgoIso(1)});
const DEFAULT_WINDOW_DAYS = 90;
/** The states of a rolling return that carry data: the seeded pair may have a day with no reference, which the backend answers `partial`. */
const DATA_STATES = /^(ready|partial)$/;

type ConvertItem = {
    from_amount?: {code?: string; amount?: string};
    to?: string;
    date_range?: {start?: string; end?: string | null};
    signals?: Array<{instance_id?: string; signal_code?: string; params?: {window_days?: number}}>;
    key?: unknown;
    max_points?: unknown;
    sample_like?: unknown;
};

/** The items of a `POST /fx/currencies/convert`, or none when the body is not a JSON array. */
function convertItems(request: Request): ConvertItem[] {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== CONVERT_PATH) return [];
    try {
        const body: unknown = request.postDataJSON();
        return Array.isArray(body) ? body.filter((item): item is ConvertItem => item !== null && typeof item === 'object') : [];
    } catch {
        return [];
    }
}

/** A convert request one of whose items asks the calendar rolling return over `windowDays` (any window when omitted). */
function asksCalendarReturn(request: Request, windowDays?: number): boolean {
    return convertItems(request).some((item) => (item.signals ?? []).some((signal) => signal.signal_code === CALENDAR_SIGNAL_CODE && (windowDays === undefined || signal.params?.window_days === windowDays)));
}

/** The settings key of the signed-in user: the chart settings live in `localStorage` under it. */
async function chartSettingsKey(page: Page): Promise<string> {
    const me = await page.request.get('/api/v1/auth/me');
    expect(me.ok(), `GET /api/v1/auth/me answered HTTP ${me.status()}`).toBe(true);
    const userId = ((await me.json()) as {user?: {id?: unknown}}).user?.id;
    if (typeof userId !== 'number' || !Number.isSafeInteger(userId)) throw new Error(`GET /api/v1/auth/me gave no user id (${String(userId)}): the chart settings are stored under it`);
    return `lf_${userId}_chartSettingsStore`;
}

/** Seeds the settings of the pair `OWN` alone, in `primaryView` and with `signals`; the next page load reads them. Run it on a page that holds the origin. */
async function seedPairSettings(page: Page, primaryView: 'absolute' | 'percentage' | 'calendar-return', signals: readonly SavedComparison[] = []): Promise<void> {
    const storageKey = await chartSettingsKey(page);
    await page.evaluate(
        ({key, slug, view, saved}) => {
            const base = {colorByBaseline: true, areaFill: true, gridLines: true, staleGradient: true, axisScales: {absolute: {mode: 'auto'}, percentage: {mode: 'include0'}, secondary: {}}, primaryView: 'absolute', signals: [] as unknown[]};
            localStorage.setItem(key, JSON.stringify({version: 3, globalSettings: base, pairOverrides: [[slug, {...base, primaryView: view, signals: saved}]]}));
        },
        {key: storageKey, slug: OWN, view: primaryView, saved: [...signals]},
    );
}

/** The `primaryView` the chart settings hold for `OWN` right now (the store saves after a short debounce), or null while none is saved. */
async function savedPrimaryView(page: Page): Promise<string | null> {
    const storageKey = await chartSettingsKey(page);
    return page.evaluate(
        ({key, slug}) => {
            const raw = localStorage.getItem(key);
            if (!raw) return null;
            const stored = JSON.parse(raw) as {pairOverrides?: Array<[string, {primaryView?: unknown}]>};
            const entry = (stored.pairOverrides ?? []).find(([name]) => name === slug);
            return typeof entry?.[1]?.primaryView === 'string' ? entry[1].primaryView : null;
        },
        {key: storageKey, slug: OWN},
    );
}

/** Opens the pair over the period and waits until the page says every load wave is in. */
async function openOwnPair(page: Page, period = range()) {
    await navigateTo(page, `/fx/${OWN}?start=${period.start}&end=${period.end}`);
    const root = page.getByTestId('fx-detail-page');
    await expect(root).toBeVisible({timeout: 15_000});
    await waitForSettled(root, 20_000);
    return {root, chart: page.getByTestId(CHART)};
}

/** Clicks the rolling-return button and returns the convert request that asked it (armed before the click, so it cannot be missed). */
async function switchToRollingReturn(page: Page): Promise<Request> {
    const asked = page.waitForRequest((request) => asksCalendarReturn(request), {timeout: 15_000});
    await page.getByTestId('fx-chart-primary-calendar-return').click();
    return asked;
}

test.describe('X5-F1 FX detail: the rolling return', () => {
    // A ceiling, never a delay: a sign-in, a page load and the round trips each test waits for by name.
    test.describe.configure({timeout: 90_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('X5-F1 (a) the mode toggle opens on prices; the rolling return asks the pair’s daily return over the default window and draws it', async ({page}) => {
        const period = range();
        const {chart} = await openOwnPair(page, period);

        const priceButton = page.getByTestId('fx-chart-primary-price');
        const calendarButton = page.getByTestId('fx-chart-primary-calendar-return');
        await expect(page.getByTestId('fx-chart-primary-controls')).toBeVisible();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect(chart).toHaveAttribute('data-series-state', 'ready');
        await expect(priceButton).toHaveAttribute('aria-pressed', 'true');
        await expect(calendarButton).toHaveAttribute('aria-pressed', 'false');
        await expect(page.getByTestId('fx-calendar-window-controls'), 'the window belongs to the rolling return').toHaveCount(0);

        const request = await switchToRollingReturn(page);

        // The request: ONE item for the pair, 1 unit of the base into the quote, the daily return (no key, no reduction).
        const items = convertItems(request);
        expect(items, 'one item: no comparison is saved').toHaveLength(1);
        const [own] = items;
        expect(own.from_amount).toEqual({code: 'EUR', amount: '1'});
        expect(own.to).toBe('USD');
        expect(own.date_range?.end).toBe(period.end);
        expect(own.date_range?.start && own.date_range.start <= period.start, `the range starts at ${period.start} or earlier`).toBe(true);
        expect(own.signals).toEqual([{instance_id: CALENDAR_INSTANCE_ID, signal_code: CALENDAR_SIGNAL_CODE, params: {window_days: DEFAULT_WINDOW_DAYS}}]);
        expect(own.key, 'the detail names no conversion').toBeUndefined();
        expect(own.max_points, 'the detail reduces nothing').toBeUndefined();
        expect(own.sample_like, 'the detail samples like no card').toBeUndefined();

        // The page: in the rolling return, with its window, its controls and a plot.
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', String(DEFAULT_WINDOW_DAYS));
        await expect(chart).toHaveAttribute('data-series-state', DATA_STATES, {timeout: 20_000});
        await expect(calendarButton).toHaveAttribute('aria-pressed', 'true');
        await expect(priceButton).toHaveAttribute('aria-pressed', 'false');
        await expect(page.getByTestId('fx-calendar-window-controls')).toBeVisible();
        await expect(page.getByTestId('fx-calendar-window-3m')).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('fx-calendar-return-loading')).toHaveCount(0);
        await expect(page.getByTestId('fx-calendar-return-unavailable')).toHaveCount(0);
        await expect(page.getByTestId('fx-calendar-return-error')).toHaveCount(0);
        await expectChartCanvas(page, CHART);
    });

    test('X5-F1 (b) a window preset asks the return again over its window', async ({page}) => {
        const {chart} = await openOwnPair(page);
        await switchToRollingReturn(page);
        await expect(chart).toHaveAttribute('data-series-state', DATA_STATES, {timeout: 20_000});
        await expect(chart).toHaveAttribute('data-window-days', String(DEFAULT_WINDOW_DAYS));

        const asked = page.waitForRequest((request) => asksCalendarReturn(request, 30), {timeout: 15_000});
        await page.getByTestId('fx-calendar-window-1m').click();
        const items = convertItems(await asked);

        expect(items).toHaveLength(1);
        expect(items[0].signals).toEqual([{instance_id: CALENDAR_INSTANCE_ID, signal_code: CALENDAR_SIGNAL_CODE, params: {window_days: 30}}]);
        await expect(chart).toHaveAttribute('data-window-days', '30');
        await expect(page.getByTestId('fx-calendar-window-1m')).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('fx-calendar-window-3m')).toHaveAttribute('aria-pressed', 'false');
        await expect(chart).toHaveAttribute('data-series-state', DATA_STATES, {timeout: 20_000});

        // A window the user chose stays: it is no longer the largest preset that fits the period.
        const weekAsked = page.waitForRequest((request) => asksCalendarReturn(request, 7), {timeout: 15_000});
        await page.getByTestId('fx-calendar-window-1w').click();
        await weekAsked;
        await expect(chart).toHaveAttribute('data-window-days', '7');
        await expect(page.getByTestId('fx-calendar-window-1w')).toHaveAttribute('aria-pressed', 'true');
    });

    test('X5-F1 (c) going back to prices shows the prices and asks nothing', async ({page}) => {
        const {root, chart} = await openOwnPair(page);
        await switchToRollingReturn(page);
        await expect(chart).toHaveAttribute('data-series-state', DATA_STATES, {timeout: 20_000});

        // Armed before the click, removed after the page is settled on the prices: a request it sent would be caught.
        const sent: Request[] = [];
        const onRequest = (request: Request) => {
            if (request.method() === 'POST' && new URL(request.url()).pathname === CONVERT_PATH) sent.push(request);
        };
        page.on('request', onRequest);
        try {
            await page.getByTestId('fx-chart-primary-price').click();
            await expect(chart).toHaveAttribute('data-primary-mode', 'price');
            await expect(chart).toHaveAttribute('data-series-state', 'ready');
            await expect(page.getByTestId('fx-chart-primary-price')).toHaveAttribute('aria-pressed', 'true');
            await expect(page.getByTestId('fx-calendar-window-controls')).toHaveCount(0);
            await waitForSettled(root, 20_000);
            await expectChartCanvas(page, CHART);
        } finally {
            page.off('request', onRequest);
        }

        expect(
            sent.map((request) => request.postData()),
            'the rates are in the store: no conversion is asked',
        ).toEqual([]);
        await expect(chart).not.toHaveAttribute('data-window-days', /.*/);
    });

    test('X5-F1 (d) the mode is saved with the pair’s chart settings, and a reload opens in it', async ({page}) => {
        const {chart} = await openOwnPair(page);
        await switchToRollingReturn(page);
        await expect(chart).toHaveAttribute('data-series-state', DATA_STATES, {timeout: 20_000});
        await expect.poll(() => savedPrimaryView(page), {message: 'the rolling return is saved as the pair’s primary view', timeout: 10_000}).toBe('calendar-return');

        await page.reload();
        await expect(page.getByTestId('fx-detail-page')).toBeVisible({timeout: 15_000});
        await waitForSettled(page.getByTestId('fx-detail-page'), 20_000);

        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', String(DEFAULT_WINDOW_DAYS));
        await expect(chart).toHaveAttribute('data-series-state', DATA_STATES, {timeout: 20_000});
        await expect(page.getByTestId('fx-chart-primary-calendar-return')).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('fx-calendar-window-controls')).toBeVisible();

        // And going back saves the price view in its place.
        await page.getByTestId('fx-chart-primary-price').click();
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');
        await expect.poll(() => savedPrimaryView(page), {message: 'the price view replaces the rolling return', timeout: 10_000}).toMatch(/^(absolute|percentage)$/);
    });

    test('X5-F1 (e) a saved fx-pair comparison is asked in the same request and drawn with its own return', async ({page}) => {
        const comparisonId = 'e2e-x5f1-fx-pair';
        await seedPairSettings(page, 'percentage', [pairComparison(comparisonId, OTHER)]);
        const {chart} = await openOwnPair(page);
        await expect(chart).toHaveAttribute('data-primary-mode', 'price');

        const request = await switchToRollingReturn(page);

        const items = convertItems(request);
        expect(items, 'one item for the pair and one for the compared pair').toHaveLength(2);
        expect(items.map((item) => [item.from_amount?.code, item.from_amount?.amount, item.to])).toEqual([
            ['EUR', '1', 'USD'],
            ['EUR', '1', 'GBP'],
        ]);
        for (const item of items) {
            expect(item.signals, 'each item asks one signal: the calendar rolling return').toEqual([{instance_id: CALENDAR_INSTANCE_ID, signal_code: CALENDAR_SIGNAL_CODE, params: {window_days: DEFAULT_WINDOW_DAYS}}]);
            expect(item.date_range).toEqual(items[0].date_range);
        }

        // The compared pair's return is told by the config id of its signal, in the list of its state: ready, or partial when a day lacks its reference.
        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-series-state', DATA_STATES, {timeout: 20_000});
        await expect
            .poll(
                async () => {
                    const withReturn = [await chart.getAttribute('data-calendar-comparison-ready'), await chart.getAttribute('data-calendar-comparison-partial')];
                    return withReturn.some((ids) => (ids ?? '').split(',').includes(comparisonId));
                },
                {message: `${comparisonId} is among the compared pairs with a return`, timeout: 20_000},
            )
            .toBe(true);
        await expect(chart).toHaveAttribute('data-calendar-comparison-unavailable', '');
        await expect(chart).toHaveAttribute('data-calendar-comparison-error', '');
        await expectPairLineDrawn(page, CHART, OTHER, `the ${OTHER} return is drawn beside the ${OWN} one`);
    });

    test('X5-F1 (f) a pair saved in the rolling return opens in it', async ({page}) => {
        await seedPairSettings(page, 'calendar-return');
        const asked = page.waitForRequest((request) => asksCalendarReturn(request, DEFAULT_WINDOW_DAYS), {timeout: 20_000});
        const {chart} = await openOwnPair(page);
        await asked;

        await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
        await expect(chart).toHaveAttribute('data-window-days', String(DEFAULT_WINDOW_DAYS));
        await expect(chart).toHaveAttribute('data-series-state', DATA_STATES, {timeout: 20_000});
        await expect(page.getByTestId('fx-chart-primary-calendar-return')).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('fx-chart-primary-price')).toHaveAttribute('aria-pressed', 'false');
        await expect(page.getByTestId('fx-calendar-window-controls')).toBeVisible();
    });
});
