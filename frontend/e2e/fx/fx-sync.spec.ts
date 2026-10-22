/**
 * FX Sync Modal — E2E Tests
 *
 * The sync modal from both entry points: the list page's «Sync all», opened and closed but never started, and the
 * pair detail page's sync button, started and followed to its verdict (Test 7). The last block reads the list dialog's
 * warning before a sync that replaces stored rates (C-66): opened over a period chosen by data, never started.
 *
 * Test 7 is end to end on the real backend — route table, provider registry, rate store and modal are the
 * application's own — but it never reaches the network and never touches a row another test reads. It used to sync the
 * seeded EUR-USD through the ECB: offline it still passed (the summary appears on failure too), and online it rewrote
 * 65 seeded EUR-USD rates with live fixings for every category that runs after this one in the same invocation. So it
 * brings a pair of its own and removes it:
 *
 *   · EUR-TTD on the desktop project, EUR-JMD on mobile — currencies no seed, spec or other test uses, sorting after
 *     EUR so the pair is stored, listed and synced as EUR-X;
 *   · routed through MOCKFX alone, a registered test provider (hidden from the public provider list) that answers
 *     every calendar day with 1.2345, so the sync runs offline and every number of the verdict is exact;
 *   · opened on an explicit period, the 10 days before today — never a day the backend could call the future;
 *   · leftovers of an interrupted run deleted and the empty pair verified before the route is created; rates and
 *     route deleted, and the pair verified empty again, in the teardown of the `ownedFxQuotes` fixture.
 *
 * Created and removed within one test, the pair is also out of reach of the 1-worker recovery net, whose
 * `populate_mock_data --force` truncates the routes: that net runs only between tests, and not at all above one
 * worker.
 */

import {expect, test as base, type Locator, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {daysAgoIso, localIso, todayIso} from '../fixtures/dates';
import {describeShown, overwriteCounts, overwriteWarningSentence, pageLanguage, recordSyncRequests, storedFxRates} from '../fixtures/sync-overwrite';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxPage} from './fx-helpers';

const API = '/api/v1';
const FX_SYNC_PATH = `${API}/fx/currencies/sync`;
const FX_RATE_PATH = `${API}/fx/currencies/rate`;
const FX_CONVERT_PATH = `${API}/fx/currencies/convert`;
const FX_ROUTES_PATH = `${API}/fx/providers/routes`;

/** What MOCKFX stores for every calendar day: 1 EUR = 1.2345 of the quote (`MOCKFX_FIXED_RATE` in the backend). */
const MOCKFX_RATE = 1.2345;

/** Days in the period the detail page is opened on: the ten days before today. */
const SYNC_PERIOD_DAYS = 10;

/**
 * The quote currency of Test 7's pair, one per Playwright project, because FX routes and rates are global rows. Each
 * sorts after EUR, so the pair is stored as EUR-X and the MOCKFX rate is kept as is, with no inversion; none is used
 * by any seed, spec or other test (grep of the whole worktree). The runner runs the desktop project only; the mobile
 * code keeps a manual two-project run from sharing a pair.
 */
const RESERVED_QUOTE: Readonly<Record<string, string>> = {desktop: 'TTD', mobile: 'JMD'};

type SyncPeriod = {start: string; end: string};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type PairResults = {results: Array<{base: string; quote: string; success: boolean}>};

/**
 * The EUR-X pairs a test registers here are deleted, and verified gone, after it — whatever happened in between.
 *
 * A fixture rather than a `finally` in the test body: a test that times out is abandoned together with its page,
 * while a fixture that depends on `page` is torn down before it, with the session still signed in.
 */
const test = base.extend<{ownedFxQuotes: string[]}>({
    ownedFxQuotes: async ({page}, use) => {
        const quotes: string[] = [];
        try {
            await use(quotes);
        } finally {
            for (const quote of quotes) await resetReservedPair(page, quote, 'cleanup');
        }
    },
});

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** A wait armed before the action and awaited after it: a failure in between leaves no rejection unobserved. */
function armed<T>(wait: Promise<T>): Promise<T> {
    wait.catch(() => undefined);
    return wait;
}

function isFxSync(req: Request): boolean {
    return req.method() === 'POST' && new URL(req.url()).pathname === FX_SYNC_PATH;
}

function reservedQuote(): string {
    const project = test.info().project.name;
    const quote = RESERVED_QUOTE[project];
    if (!quote) throw new Error(`No currency is reserved for project "${project}": reserve one that sorts after EUR and that no seed, spec or test uses`);
    return quote;
}

/** The `count` calendar days before today, oldest first, on the local calendar the application uses. */
function daysBeforeToday(count: number): string[] {
    const today = new Date();
    return Array.from({length: count}, (_, index) => {
        const day = new Date(today);
        day.setDate(today.getDate() - (count - index));
        return localIso(day);
    });
}

/** Delete every rate and every route of EUR-`quote`; on an empty pair both succeed with nothing to delete. */
async function deleteReservedPair(page: Page, quote: string): Promise<void> {
    const rates = await jsonFrom<PairResults>(await page.request.delete(FX_RATE_PATH, {data: [{from: 'EUR', to: quote, delete_all: true}]}), `delete every EUR-${quote} rate`);
    expect(rates.results.find((item) => item.base === 'EUR' && item.quote === quote)?.success, `delete every EUR-${quote} rate`).toBe(true);
    const routes = await jsonFrom<PairResults>(await page.request.delete(FX_ROUTES_PATH, {data: [{base: 'EUR', quote}]}), `delete the EUR-${quote} routes`);
    expect(routes.results.find((item) => item.base === 'EUR' && item.quote === quote)?.success, `delete the EUR-${quote} routes`).toBe(true);
}

/** Delete what EUR-`quote` holds, then verify — not infer — that no route and no rate is left. */
async function resetReservedPair(page: Page, quote: string, moment: 'precondition' | 'cleanup'): Promise<void> {
    await deleteReservedPair(page, quote);
    const routes = await jsonFrom<{items?: Array<{base: string; quote: string}>}>(await page.request.get(FX_ROUTES_PATH), 'list the FX routes');
    expect(
        (routes.items ?? []).filter((route) => route.base === 'EUR' && route.quote === quote),
        `${moment}: no EUR-${quote} route is configured`,
    ).toEqual([]);
    // Backward fill is unlimited: a single stored rate on or before today would answer, so a 404 means none is left.
    const probe = await page.request.post(FX_CONVERT_PATH, {data: [{from_amount: {code: quote, amount: '1'}, to: 'EUR', date_range: {start: todayIso()}}]});
    expect(probe.status(), `${moment}: no EUR-${quote} rate is stored, so converting ${quote} today must fail — got ${await probe.text()}`).toBe(404);
}

/** EUR-`quote` served by MOCKFX alone: a provider other than MANUAL, so the detail page offers to sync the pair. */
async function createMockFxRoute(page: Page, quote: string): Promise<void> {
    const route = {base: 'EUR', quote, priority: 1, chain_steps: [{from: 'EUR', to: quote, provider: 'MOCKFX'}]};
    schemas.FXConversionRouteItem.parse(route);
    const response = await page.request.post(FX_ROUTES_PATH, {data: [route]});
    expect(response.status(), `create the EUR-${quote} MOCKFX route: ${await response.text()}`).toBe(201);
    const body = (await response.json()) as PairResults;
    expect(body.results.find((item) => item.base === 'EUR' && item.quote === quote)?.success, `the EUR-${quote} route is stored`).toBe(true);
}

/**
 * The detail page of `pair` on `period`, ended once the page says it has stopped loading. Opened by URL: on a full
 * load the query is what seeds the page's period.
 */
async function openDetailOn(page: Page, pair: string, period: SyncPeriod): Promise<Locator> {
    await navigateTo(page, `/fx/${pair}?start=${period.start}&end=${period.end}`);
    const detail = page.getByTestId('fx-detail-page');
    await expect(detail).toBeVisible({timeout: 15_000});
    await waitForSettled(detail, 20_000);
    return detail;
}

test.describe('FX Sync', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Open Sync All modal from list
    // ========================================================================
    test('can open Sync All modal from list page', async ({page}) => {
        await goToFxPage(page);
        const syncBtn = page.getByTestId('fx-sync-all-button');
        await syncBtn.click();

        // FxSyncModal should be visible
        const modal = page.getByTestId('fx-sync-modal');
        await expect(modal).toBeVisible({timeout: 3000});
    });

    // ========================================================================
    // Test 6: Close sync modal
    // ========================================================================
    test('can close sync modal', async ({page}) => {
        await goToFxPage(page);
        const syncBtn = page.getByTestId('fx-sync-all-button');
        await syncBtn.click();

        const modal = page.getByTestId('fx-sync-modal');
        await expect(modal).toBeVisible({timeout: 3000});

        // Close via Escape or close button
        await page.keyboard.press('Escape');
        await expect(modal).not.toBeVisible();
    });

    // ========================================================================
    // Test 7: Sync from the detail page — end to end, offline, on its own pair
    // ========================================================================
    // Proves that the detail page's sync button opens the page sync modal scoped to this pair alone; that starting
    // it syncs exactly this pair over the page's period; that the verdict counts what the server did, day by day;
    // that the chart reloads onto the synced rates and the rates are stored; and that the button is usable again.
    // Its own MOCKFX pair, not the seeded EUR-USD: see the header for what the shared pair cost.
    test('sync from detail page triggers action', async ({page, ownedFxQuotes}) => {
        // Localhost and an offline provider: the budget covers sign-in, setup, the page, the sync and the teardown.
        test.setTimeout(60_000);
        const quote = reservedQuote();
        const pair = `EUR-${quote}`;
        const days = daysBeforeToday(SYNC_PERIOD_DAYS);
        const period = {start: days[0], end: days[days.length - 1]};

        await test.step(`setup: ${pair} routed through MOCKFX alone, with no rate`, async () => {
            // Registered before it exists: the teardown deletes whatever this step got to create.
            ownedFxQuotes.push(quote);
            await resetReservedPair(page, quote, 'precondition');
            await createMockFxRoute(page, quote);
        });

        const detail = await openDetailOn(page, pair, period);
        await expect(detail, 'the page shows the pair this test created').toHaveAttribute('data-chart-pair', pair);
        await expect(detail, 'precondition: the page has no rate to show').toHaveAttribute('data-chart-last-rate', '');
        // Enabled once the page has loaded a provider other than MANUAL for the pair — the MOCKFX route.
        const syncBtn = page.getByTestId('fx-detail-sync-btn');
        await expect(syncBtn).toBeEnabled({timeout: 10_000});
        await syncBtn.click();

        // The detail page opens the *page* sync modal (assets + FX for this page); `fx-sync-modal` is the list
        // page's. It announces one section with one item — this pair, nothing else — and has run nothing yet.
        const modal = page.getByTestId('page-sync-modal');
        await expect(modal).toBeVisible({timeout: 10_000});
        const scope = modal.getByTestId('sync-modal-count');
        await expect(scope).toHaveAttribute('data-section-count', '1');
        await expect(scope).toHaveAttribute('data-item-count', '1');
        await expect(modal.getByTestId('sync-modal-results')).toHaveCount(0);

        // Armed before the click. The request is part of the subject: it must name this pair over this period, and
        // the answer must come from MOCKFX — which is what keeps the network out.
        const syncRequest = armed(page.waitForRequest(isFxSync, {timeout: 10_000}));
        const syncResponse = armed(page.waitForResponse((response) => isFxSync(response.request()), {timeout: 20_000}));
        await modal.getByTestId('sync-modal-start').click();
        expect((await syncRequest).postDataJSON(), 'the page syncs its own pair over its own period').toEqual({pairs: [pair], start: period.start, end: period.end});
        const answer = schemas.FXSyncBulkResponse.parse(await jsonFrom(await syncResponse, 'the sync answer'));
        const expected = {pair, status: 'ok', provider_used: 'MOCKFX', points_fetched: days.length, points_changed: days.length};
        expect(answer.results, 'one result, for this pair, served by MOCKFX for every day of the period').toMatchObject([expected]);

        // The summary banner is the modal's verdict — it raises no toast — and its tallies are read from the data-*
        // attributes SyncModalBase publishes, never from the translated sentence. Changed = fetched: the pair was empty.
        const results = modal.getByTestId('sync-modal-results');
        await expect(results).toBeVisible({timeout: 10_000});
        const tallies = {'data-total': 1, 'data-success': 1, 'data-failed': 0, 'data-fetched': days.length, 'data-changed': days.length};
        for (const [name, value] of Object.entries(tallies)) await expect(results, name).toHaveAttribute(name, String(value));
        await expect(modal.locator(`[data-testid="sync-result-row"][data-row-id="${pair}"]`)).toHaveAttribute('data-status', 'ok');

        await modal.getByTestId('sync-modal-close').click();
        await expect(modal).toBeHidden();
        await expect(syncBtn).toBeEnabled();
        // A completed sync reloads the chart, which now ends on the rate MOCKFX stored.
        await expect(detail, 'the chart shows the synced rate').toHaveAttribute('data-chart-last-rate', String(MOCKFX_RATE), {timeout: 10_000});

        // Read back through the API: every day of the period has a rate of its own, 1 EUR = 1.2345.
        const readBack = await page.request.post(FX_CONVERT_PATH, {data: [{from_amount: {code: 'EUR', amount: '1'}, to: quote, date_range: period}]});
        const conversion = schemas.FXConvertResponse.parse(await jsonFrom(readBack, `convert 1 EUR to ${quote} over the period`));
        expect(
            conversion.results.map((item) => ({day: item.conversion_date, rate: Number(item.rate), backfilled: item.backward_fill_info ?? null})),
            'one stored rate per day of the period, none carried from another day',
        ).toEqual(days.map((day) => ({day, rate: MOCKFX_RATE, backfilled: null})));
    });
});

// ============================================================================
// The list dialog's warning before it replaces stored rates (C-66, F-094)
// ============================================================================

/**
 * «Sync all» syncs every pair with a route but a lone MANUAL one over the page's period, and a sync replaces the rates
 * stored in that period with the provider's, manual edits included. Before the start the dialog says so, in one warning
 * for its one section: `fx-sync-modal-overwrite-warning`, `data-existing` of its `data-total` pairs storing a rate in
 * the period. A day the page shows filled backward from an earlier rate — a weekend, a holiday, a day still to come —
 * is not a stored row of the period, so it is never counted.
 *
 * Both periods are chosen by data, read through the endpoint the page reads its rates from (`storedFxRates`), never
 * assumed from the seed:
 *   · the 30 days up to yesterday, where some pair the dialog syncs stores rates — verified;
 *   · a past weekend where no pair the dialog syncs stores a rate while some pair shows its Friday's rate carried
 *     forward — filled backward (the seed stores weekdays only: populate_mock_data.py, populate_fx_rates). The page
 *     shows rates in that period and must not count them: the negative is the rule, not an empty period. Chosen by
 *     data among the weekends from two weeks back (`pastWeekendFilledBackward`), never a period still to come: since
 *     X-R55 (17/10) a conversion range ends at tomorrow, so a week from now shows nothing at all.
 *
 * Neither test starts the dialog — no sync request may leave the page — and neither writes anything: the list does not
 * poll live rates, and every request here is a read.
 */
/** How many past weekends `pastWeekendFilledBackward` looks at, from two weeks back. */
const WEEKENDS_PROBED = 8;

/**
 * The most recent weekend, from two weeks back, where no pair «Sync all» syncs stores a rate and some pair shows one
 * filled backward — read through `storedFxRates`, the endpoint the page reads its rates from — with what each pair shows
 * of it; null when none of the `WEEKENDS_PROBED` weekends is one (the failure message then lists what each showed).
 */
async function pastWeekendFilledBackward(page: Page): Promise<{period: SyncPeriod; targets: Awaited<ReturnType<typeof storedFxRates>>} | {period: null; seen: string[]}> {
    // Fourteen days back is today's weekday again; `getDay()` days further back (Sunday 0 … Saturday 6) is a Sunday.
    const firstSundayBack = 14 + new Date().getDay();
    const seen: string[] = [];
    for (let weekend = 0; weekend < WEEKENDS_PROBED; weekend += 1) {
        const sundayBack = firstSundayBack + 7 * weekend;
        const period: SyncPeriod = {start: daysAgoIso(sundayBack + 1), end: daysAgoIso(sundayBack)};
        const targets = await storedFxRates(page, period);
        if (targets.every((target) => target.stored === 0) && targets.some((target) => target.shown > 0)) return {period, targets};
        seen.push(`${period.start} → ${period.end}: ${describeShown(targets)}`);
    }
    return {period: null, seen};
}

test.describe('FX Sync — the list dialog warns before replacing stored rates (C-66)', () => {
    // A ceiling, never a delay: each test converts every syncable pair over its period before loading the list's two
    // waves, and a describe's timeout also covers the sign-in below. Only the timeout is set: the file's parallel mode
    // is inherited unchanged.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('sync all over a period holding stored rates warns once, counting among the pairs it syncs', async ({page}) => {
        const period: SyncPeriod = {start: daysAgoIso(30), end: daysAgoIso(1)};
        const targets = await storedFxRates(page, period);
        if (!targets.some((target) => target.stored > 0)) {
            throw new Error(`precondition: no pair «Sync all» syncs stores a rate between ${period.start} and ${period.end} (${describeShown(targets)}) — check populate_mock_data.py (populate_fx_rates, populate_fx_currency_pair_sources)`);
        }

        const syncRequests = recordSyncRequests(page);
        await goToFxPage(page, period);
        await page.getByTestId('fx-sync-all-button').click();

        const modal = page.getByTestId('fx-sync-modal');
        await expect(modal).toBeVisible();
        const scope = modal.getByTestId('sync-modal-count');
        // The dialog syncs the page's period: the one the targets were read over.
        await expect(scope).toContainText(period.start);
        await expect(scope).toContainText(period.end);
        await expect(scope).toHaveAttribute('data-section-count', '1');

        const warning = modal.getByTestId('fx-sync-modal-overwrite-warning');
        await expect(warning, 'one warning: the dialog has one section').toHaveCount(1);
        const {section, existing, total} = await overwriteCounts(warning);
        expect(section).toBe('fx');
        expect(total, 'counted out of every pair the dialog syncs').toBe(Number(await scope.getAttribute('data-item-count')));
        expect(existing, 'some pair the dialog syncs stores a rate in the period').toBeGreaterThanOrEqual(1);
        expect(existing, 'only pairs the dialog syncs are counted').toBeLessThanOrEqual(total);
        // One section: the sentence alone — the catalogue's, for these counts, in the page's language.
        await expect(warning).toHaveText(overwriteWarningSentence(await pageLanguage(page), existing, total));

        // Still before the start, and closed from there: the dialog is never started.
        await expect(modal.getByTestId('sync-modal-start')).toBeEnabled();
        await expect(modal.getByTestId('sync-modal-results')).toHaveCount(0);
        await modal.getByTestId('sync-modal-close').click();
        await expect(modal).toBeHidden();
        expect(syncRequests, 'no sync request left the page: no provider was called').toEqual([]);
    });

    test('sync all over a period whose rates are all filled backward does not warn', async ({page}) => {
        // A past weekend, chosen by data: nothing stored, some rate shown filled backward from the Friday.
        const probe = await pastWeekendFilledBackward(page);
        if (probe.period === null) {
            throw new Error(
                `precondition: none of the last ${WEEKENDS_PROBED} weekends from two weeks back has every pair «Sync all» syncs without a stored rate and some pair showing one filled backward (${probe.seen.join(' | ')}) — check populate_mock_data.py (populate_fx_rates stores weekdays only): this test is about rates shown but not stored, not about an empty period`,
            );
        }
        const {period, targets} = probe;
        expect(
            targets.filter((target) => target.stored > 0).map((target) => target.name),
            'precondition: no pair stores a rate on the weekend',
        ).toEqual([]);

        const syncRequests = recordSyncRequests(page);
        await goToFxPage(page, period);
        await page.getByTestId('fx-sync-all-button').click();

        const modal = page.getByTestId('fx-sync-modal');
        await expect(modal).toBeVisible();
        // Presence barrier: the dialog has drawn its body before the start — this period, pairs to sync, the controls a
        // start needs — so the absence below is the rule's, not a dialog still on its way.
        const scope = modal.getByTestId('sync-modal-count');
        await expect(scope).toContainText(period.start);
        await expect(scope).toContainText(period.end);
        expect(Number(await scope.getAttribute('data-item-count')), 'the dialog has pairs to sync').toBeGreaterThanOrEqual(1);
        await expect(modal.getByTestId('sync-modal-timeout')).toBeVisible();
        await expect(modal.getByTestId('sync-modal-start')).toBeEnabled();
        await expect(modal.getByTestId('fx-sync-modal-overwrite-warning'), 'a rate filled backward is not a stored row: the sync would replace nothing in the period').toHaveCount(0);

        await modal.getByTestId('sync-modal-close').click();
        await expect(modal).toBeHidden();
        expect(syncRequests, 'no sync request left the page: no provider was called').toEqual([]);
    });
});
