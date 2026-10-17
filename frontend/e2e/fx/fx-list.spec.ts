/**
 * FX List Page — E2E Tests
 *
 * Tests the FX list page: card rendering, filtering, navigation, and basic actions.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test, type Locator, type Page, type Request} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {maximisePageSize} from '../fixtures/paging';
import {goToFxPage} from './fx-helpers';

test.describe('FX List Page', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Navigation to FX page
    // ========================================================================
    test('can navigate to FX page', async ({page}) => {
        await goToFxPage(page);
        await expect(page.getByTestId('fx-page')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Cards with mock data are visible
    // ========================================================================
    test('cards with mock data are visible', async ({page}) => {
        await goToFxPage(page);
        const cards = page.locator('[data-testid^="fx-card-"]');
        const count = await cards.count();
        expect(count).toBeGreaterThan(0);
    });

    // ========================================================================
    // Test 3: Badge with pair count matches card count
    // ========================================================================
    test('pair count badge matches card count', async ({page}) => {
        await goToFxPage(page);
        // Count only card containers (not their children — pair-label, swap-btn etc.)
        const cards = page.locator('[data-testid^="fx-card-"]').filter({
            has: page.locator('[data-testid="fx-pair-label"]'),
        });
        const cardCount = await cards.count();

        // The badge shows the count of configured pairs
        const badge = page.getByTestId('fx-pair-count-badge');
        await expect(badge).toBeVisible();
        const badgeText = await badge.textContent();
        expect(badgeText).toContain(String(cardCount));
    });

    // ========================================================================
    // Test 4: Filter by single currency
    // ========================================================================
    test('filter by single currency shows matching cards', async ({page}) => {
        await goToFxPage(page);
        const allCards = page.locator('[data-testid^="fx-card-"]');
        const totalBefore = await allCards.count();

        // Currency filter containers should exist
        const filterContainers = page.locator('[data-testid="fx-currency-filter"]');
        await expect(filterContainers.first()).toBeVisible();

        const firstFilter = filterContainers.first();
        await firstFilter.locator('[role="combobox"]').click();
        const searchInput = firstFilter.locator('input[type="text"]');
        await searchInput.fill('EUR');

        // SearchSelect uses <button> inside [role="listbox"], not [role="option"]
        const listbox = page.locator('[role="listbox"]');
        await expect(listbox).toBeVisible();
        await expect(listbox).toHaveAttribute('aria-busy', 'false', {timeout: 10_000});
        const option = listbox.locator('button').filter({hasText: 'EUR'}).first();
        await option.click();
        await expect(listbox).toHaveCount(0, {timeout: 10_000});

        // All visible cards should contain "EUR"
        const filtered = page.locator('[data-testid^="fx-card-"]');
        const filteredCount = await filtered.count();
        expect(filteredCount).toBeGreaterThan(0);
        expect(filteredCount).toBeLessThanOrEqual(totalBefore);
    });

    // ========================================================================
    // Test 7: Reset filters restores all cards
    // ========================================================================
    test('reset filters restores all cards', async ({page}) => {
        await goToFxPage(page);
        const allCards = page.locator('[data-testid^="fx-card-"]');
        const totalBefore = await allCards.count();

        // Apply a EUR filter first
        const filterContainers = page.locator('[data-testid="fx-currency-filter"]');
        const firstFilter = filterContainers.first();
        await firstFilter.locator('[role="combobox"]').click();
        const searchInput = firstFilter.locator('input[type="text"]');
        await searchInput.fill('EUR');

        // SearchSelect uses <button> inside [role="listbox"], not [role="option"]
        const listbox = page.locator('[role="listbox"]');
        await expect(listbox).toHaveAttribute('aria-busy', 'false', {timeout: 10_000});
        const option = listbox.locator('button').filter({hasText: 'EUR'}).first();
        await option.click();
        await expect(listbox).toHaveCount(0, {timeout: 10_000});

        // Click reset filters button
        const resetBtn = page.getByTestId('fx-reset-filters');
        await expect(resetBtn).toBeVisible();
        await resetBtn.click();

        // All cards should be restored
        await expect(allCards).toHaveCount(totalBefore, {timeout: 10_000});
    });

    test('column menu stays compact and lists daily delta after rate', async ({page}) => {
        await goToFxPage(page);
        await page.getByTestId('view-mode-list').click();

        await page.getByTestId('column-visibility-toggle').click();
        const dropdown = page.getByTestId('column-visibility-dropdown');
        await expect(dropdown).toBeVisible();
        const box = await dropdown.boundingBox();
        const viewport = page.viewportSize();
        if (!box || !viewport) throw new Error('Column visibility dropdown must have measurable viewport bounds.');
        expect(box.width).toBeLessThan(320);
        expect(box.x).toBeGreaterThanOrEqual(7);
        expect(box.x + box.width).toBeLessThanOrEqual(viewport.width - 7);

        const rateItem = page.getByTestId('column-visibility-item-rate');
        const dailyItem = page.getByTestId('column-visibility-item-delta_1D');
        await expect(dailyItem).toBeVisible();
        expect(await rateItem.evaluate((element) => element.compareDocumentPosition(document.querySelector('[data-testid="column-visibility-item-delta_1D"]')!) & Node.DOCUMENT_POSITION_FOLLOWING)).toBeTruthy();
    });

    // ========================================================================
    // Test 8: DateRangePicker preset changes date
    // ========================================================================
    test('DateRangePicker preset changes date display', async ({page}) => {
        await goToFxPage(page);
        const datePicker = page.getByTestId('fx-date-range-picker');
        await expect(datePicker).toBeVisible();

        // Click "1Y" preset button
        const yearPreset = datePicker.getByRole('button', {name: /1Y/});
        await expect(yearPreset).toBeVisible();
        await yearPreset.click();

        // After clicking 1Y, the preset should be active
        // Verify the 1Y button is marked active — the state it publishes, not the colour it draws
        await expect(yearPreset).toHaveAttribute('data-active', 'true');
    });

    // ========================================================================
    // Test 10: Invert card pair swaps display
    // ========================================================================
    test('invert card pair swaps base/quote display', async ({page}) => {
        await goToFxPage(page);
        const firstCard = page.locator('[data-testid^="fx-card-"]').first();
        await expect(firstCard).toBeVisible();

        // Get the initial pair label
        const pairLabel = firstCard.locator('[data-testid$="-pair-label"]');
        await expect(pairLabel).toBeVisible();
        const labelBefore = await pairLabel.textContent();

        // Click swap button on the card
        const swapBtn = firstCard.locator('[data-testid$="-swap-btn"]');
        await expect(swapBtn).toBeVisible();
        await swapBtn.click();

        // Labels should differ after swap — the retrying assertion *is* the wait
        await expect(pairLabel).not.toHaveText(labelBefore ?? '', {timeout: 10_000});
    });

    // ========================================================================
    // Test 11: Navigate to detail page by clicking card
    // ========================================================================
    test('clicking card navigates to detail page', async ({page}) => {
        await goToFxPage(page);
        const firstCard = page.locator('[data-testid^="fx-card-"]').first();
        await expect(firstCard).toBeVisible();

        // Click the navigate area of the card (the card link/button)
        const navLink = firstCard.locator('a, [data-testid$="-navigate"]').first();
        if (await navLink.isVisible()) {
            await navLink.click();
        } else {
            // Fallback: click the card itself
            await firstCard.click();
        }
        // URL should contain /fx/ followed by a pair slug
        await expect(page).toHaveURL(/\/fx\/[A-Z]+-[A-Z]+/, {timeout: 10_000});
    });

    // ========================================================================
    // Test 13: Add Pair button is visible
    // ========================================================================
    test('Add Pair button is visible', async ({page}) => {
        await goToFxPage(page);
        await expect(page.getByTestId('fx-add-pair-button')).toBeVisible();
    });

    // ========================================================================
    // Test 14: Sync All button is visible
    // ========================================================================
    test('Sync All button is visible', async ({page}) => {
        await goToFxPage(page);
        const syncBtn = page.getByTestId('fx-sync-all-button');
        await expect(syncBtn).toBeVisible();
    });

    test('loads all FX cards through exactly one bulk conversion request', async ({page}) => {
        const bulkRequests: Array<{postData: unknown}> = [];
        page.on('request', (request) => {
            if (request.method() !== 'POST') return;
            if (new URL(request.url()).pathname !== '/api/v1/fx/currencies/convert') return;
            bulkRequests.push({postData: request.postDataJSON()});
        });

        await goToFxPage(page);
        await expect(page.getByTestId('fx-page')).toBeVisible({timeout: 8_000});
        await page.waitForLoadState('networkidle');

        expect(bulkRequests).toHaveLength(1);
        expect(Array.isArray(bulkRequests[0].postData)).toBe(true);
        expect((bulkRequests[0].postData as unknown[]).length).toBeGreaterThan(0);
    });
});

// ============================================================================
// The Δ columns are the backend's period changes (workstream X, lot X-R53)
// ============================================================================

/** The FX period changes, whatever their query string. */
const FX_PERIOD_CHANGES = /\/api\/v1\/fx\/currencies\/period-changes(\?.*)?$/;

/** The backend's fixed periods, in display order: the `key` and `days` of `FXPeriodChange`. */
const PERIOD_DAYS: ReadonlyArray<readonly [string, number]> = [
    ['1D', 1],
    ['1W', 7],
    ['1M', 30],
    ['3M', 91],
    ['6M', 182],
    ['1Y', 365],
    ['2Y', 730],
    ['3Y', 1095],
    ['5Y', 1825],
];

/**
 * What the stub answers for the pair, per period: `[change_ratio, inverse_change_ratio]`. +1.25 % and −25 % as
 * configured; −4 % and +50 % inverted, which are neither the inversion of the first two (−1.23 %, +33.33 %) nor their
 * negation, so a swapped cell shows them only by reading `inverse_change_ratio`. Null — no figure — over every longer
 * period, either way.
 */
const STUBBED_RATIOS: Readonly<Record<string, readonly [string, string]>> = {'1D': ['0.0125', '-0.04'], '1W': ['-0.25', '0.5']};

/** One pair of a period-changes request (`FXPeriodChangesRequest`). */
type FxPeriodChangesQuery = {base: string; quote: string; as_of: string};

/** The pair this test reads: seeded with an ECB route, configured EUR first as the list shows it. */
const PAIR = {base: 'EUR', quote: 'USD'} as const;
const SLUG = `${PAIR.base}-${PAIR.quote}`;

/** A Δ cell of a table row, by the column id DataTable publishes on each cell. */
function deltaCell(row: Locator, key: string): Locator {
    return row.locator(`td[data-column-id="delta_${key}"]`);
}

/**
 * A Δ cell's percentage as any of the four languages writes it, matched whole: `+1.25%` (English), `+1,25%`
 * (Italian), `+1,25 %` (French, Spanish: a no-break space before the sign); a minus may be `-` or `−`. The figure is
 * read, never a translation.
 */
function percentCell(figure: string): RegExp {
    const parts = /^([+-])(\d+)\.(\d+)$/.exec(figure);
    if (!parts) throw new Error(`percentCell: ${figure} is not a signed decimal such as +1.25`);
    return new RegExp(`^\\s*${parts[1] === '+' ? '\\+' : '[-\\u2212]'}${parts[2]}[.,]${parts[3]}\\s?%\\s*$`);
}

/** The empty marker of a Δ cell: a change the backend could not compute (`null`). */
const EMPTY_CELL = /^\s*—\s*$/;

/**
 * The Δ columns of the table — the fixed 1D, and the periods the range holds (1W … 5Y) — are the backend's (MF-P2):
 * the list asks `POST /fx/currencies/period-changes` for every configured pair, base and quote as configured, up to the
 * end of the range on screen (`as_of`); it shows each `change_ratio` × 100, each `inverse_change_ratio` × 100 once the
 * row is swapped, and the empty marker for a change the backend could not compute (`null`). The browser computes none.
 *
 * The pair is the seeded EUR/USD, read and never written. A pair of the test's own would live in the shared, user-less
 * FX tables, whose routes a repopulate truncates wholesale (`fx-sync-mock.spec.ts` tells how that went), and this test
 * needs no row of its own: the figures come from the stub, and a swapped row is the browser's state
 * (`fxCardInversionStore`), never the database's. The real answer is fetched and only the pair's item is changed in it,
 * with figures its rates do not give on these days.
 *
 * Red today: the list never asks the endpoint — the route never fires — and computes its Δ from the rates it loaded.
 */
test.describe('FX list — the Δ columns are the backend’s period changes (X-R53)', () => {
    // A ceiling, never a delay: the list loads its waves — pairs, rates, period changes — for every configured pair,
    // and loads them again once the row is swapped.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('the pair shows each change ratio × 100, and each inverse ratio × 100 once swapped', async ({page}) => {
        // About two months ending on a known day in the past: 1W and 1M fit the range, 3M does not.
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const asked: FxPeriodChangesQuery[] = [];
        const failures: string[] = [];
        let answered = 0;
        await page.route(FX_PERIOD_CHANGES, async (route) => {
            try {
                asked.push(...((route.request().postDataJSON() as FxPeriodChangesQuery[] | null) ?? []));
                const response = await route.fetch();
                if (!response.ok()) {
                    failures.push(`HTTP ${response.status()}: ${await response.text()}`);
                    await route.fulfill({response});
                    return;
                }
                const answer = (await response.json()) as {items?: Array<{base: string; quote: string}>};
                const periods = PERIOD_DAYS.map(([key, days]) => ({key, days, change_ratio: STUBBED_RATIOS[key]?.[0] ?? null, inverse_change_ratio: STUBBED_RATIOS[key]?.[1] ?? null}));
                const items = (answer.items ?? []).map((item) => (item.base === PAIR.base && item.quote === PAIR.quote ? {...item, periods, errors: []} : item));
                await route.fulfill({response, json: {...answer, items}});
            } catch (error) {
                // Nobody awaits a route callback, so what it throws would land on whatever runs next: recorded, and the
                // request let through, for the test to fail on its own assertions.
                failures.push(String(error));
                await route.continue().catch(() => undefined);
            } finally {
                answered += 1;
            }
        });
        try {
            await goToFxPage(page, range);
            const fxPage = page.getByTestId('fx-page');
            await page.getByTestId('view-mode-list').click();
            await waitForSettled(fxPage, 20_000);
            // The list pages over every configured pair, and how many there are depends on the neighbours mid-test.
            await maximisePageSize(page, fxPage);
            const row = page.locator(`tbody tr[data-row-id="${SLUG}"]`);
            await expect(row, `${SLUG} is not in the FX list — check its ECB route in populate_mock_data.py`).toBeVisible({timeout: 10_000});
            const pairCell = row.locator('td[data-column-id="pair"]');
            await expect(pairCell, 'premise: the pair is shown as configured, EUR → USD').toHaveText(/EUR.*USD/);

            // Asked and answered — the page holds `data-busy` until the period changes are in; the poll is a deadline.
            await expect.poll(() => answered, {message: 'the FX list never asked POST /fx/currencies/period-changes: its Δ columns are still computed in the browser', timeout: 10_000}).toBeGreaterThan(0);
            expect(failures, 'the period changes reached the page').toEqual([]);
            expect(asked, 'the pair is asked as configured, up to the end of the range on screen').toContainEqual(expect.objectContaining({base: PAIR.base, quote: PAIR.quote, as_of: range.end}));
            expect([...new Set(asked.map((item) => item.as_of))], 'every pair is asked up to the end of the range on screen').toEqual([range.end]);

            // The period columns of the range: about two months hold 1M (30 days), not 3M (91).
            const table = page.getByTestId('dt-scroll').filter({has: row});
            await expect(table.getByTestId('dt-header-delta_1M'), 'the 1M column, drawn from the periods of the answer').toHaveCount(1, {timeout: 10_000});
            await expect(table.getByTestId('dt-header-delta_3M')).toHaveCount(0);

            // As configured, EUR → USD: change_ratio.
            await expect(deltaCell(row, '1D'), '1D: change_ratio 0.0125').toHaveText(percentCell('+1.25'));
            await expect(deltaCell(row, '1W'), '1W: change_ratio -0.25').toHaveText(percentCell('-25.00'));
            await expect(deltaCell(row, '1M'), '1M: change_ratio null').toHaveText(EMPTY_CELL);

            // Swapped through the row's own action, USD → EUR: inverse_change_ratio.
            await page.getByTestId(`row-actions-${SLUG}`).click();
            await expect(page.getByTestId('context-menu')).toBeVisible();
            await page.getByTestId('context-menu-action-swap').click();
            await expect(pairCell, 'the row is swapped: USD → EUR').toHaveText(/USD.*EUR/);
            await waitForSettled(fxPage, 20_000);

            await expect(deltaCell(row, '1D'), '1D swapped: inverse_change_ratio -0.04').toHaveText(percentCell('-4.00'), {timeout: 10_000});
            await expect(deltaCell(row, '1W'), '1W swapped: inverse_change_ratio 0.5').toHaveText(percentCell('+50.00'), {timeout: 10_000});
            await expect(deltaCell(row, '1M'), '1M swapped: inverse_change_ratio null').toHaveText(EMPTY_CELL, {timeout: 10_000});
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });
});

// ============================================================================
// Which period changes the list keeps, and when it asks them (workstream X, lot X-R60)
// ============================================================================

/** The FX rates and backend signals of the list, asked in bulk. */
const FX_CONVERT = /\/api\/v1\/fx\/currencies\/convert(\?.*)?$/;
/** The FX signal catalogue: read as the page mounts, and again by the signals' retry. */
const FX_SIGNAL_CATALOG = /\/api\/v1\/fx\/currencies\/signals(\?.*)?$/;

/** A pair's figures per period: `[change_ratio, inverse_change_ratio]`. */
type PairRatios = Readonly<Record<string, readonly [string, string]>>;

/** What the pair's own request answers, a refresh having just run: the X-R53 figures, +1.25 % and −25 % as configured. */
const FRESH_RATIOS: PairRatios = STUBBED_RATIOS;
/** What a reload of every pair, begun before that refresh, answers for the same pair: −50 % and +12.50 % as configured. */
const STALE_RATIOS: PairRatios = {'1D': ['-0.5', '1'], '1W': ['0.125', '-0.1111']};

/**
 * A second seeded pair, ECB-routed like the first, read and never written: what a reload answers for it (+3.21 % over a
 * day) is the sign that the reload's answer reached the table.
 */
const WITNESS = {base: 'EUR', quote: 'GBP'} as const;
const WITNESS_SLUG = `${WITNESS.base}-${WITNESS.quote}`;
const WITNESS_RATIOS: PairRatios = {'1D': ['0.0321', '-0.0311']};

/** A rate as the rate column writes it, four decimals with either mark; a pair with no rate shows a marker instead. */
const RATE_FIGURE = /\d[.,]\d{4}/;

/** An answer of `POST /fx/currencies/period-changes`, as far as these tests read it. */
type FxPeriodChangesAnswer = {items?: Array<{base: string; quote: string}>};

/**
 * The answer with the periods of each stubbed pair replaced — every period of the backend, its ratios from the stub or
 * null — and every other item as the backend gave it.
 */
function withPairRatios(answer: FxPeriodChangesAnswer, stubs: ReadonlyArray<readonly [{base: string; quote: string}, PairRatios]>): FxPeriodChangesAnswer {
    return {
        ...answer,
        items: (answer.items ?? []).map((item) => {
            const stub = stubs.find(([pair]) => pair.base === item.base && pair.quote === item.quote);
            if (!stub) return item;
            const periods = PERIOD_DAYS.map(([key, days]) => ({key, days, change_ratio: stub[1][key]?.[0] ?? null, inverse_change_ratio: stub[1][key]?.[1] ?? null}));
            return {...item, periods, errors: []};
        }),
    };
}

/** Whether a period-changes request asks one pair alone — that pair's own refresh — rather than every pair of the list. */
function asksPairAlone(body: readonly FxPeriodChangesQuery[], pair: {base: string; quote: string}): boolean {
    return body.length === 1 && body[0].base === pair.base && body[0].quote === pair.quote;
}

/** A gate a route handler waits on: the answer it holds goes through once the test calls `open()`. */
function gate(): {opened: Promise<void>; open: () => void} {
    let open: () => void = () => undefined;
    const opened = new Promise<void>((resolve) => {
        open = resolve;
    });
    return {opened, open};
}

/**
 * The list over `range`, as a table on one page, the pair's row on screen as configured (EUR → USD). The list pages over
 * every configured pair, and how many there are depends on the neighbours mid-test.
 */
async function openPairRow(page: Page, range: {start: string; end: string}): Promise<{fxPage: Locator; row: Locator}> {
    await goToFxPage(page, range);
    const fxPage = page.getByTestId('fx-page');
    await page.getByTestId('view-mode-list').click();
    await waitForSettled(fxPage, 20_000);
    await maximisePageSize(page, fxPage);
    const row = page.locator(`tbody tr[data-row-id="${SLUG}"]`);
    await expect(row, `${SLUG} is not in the FX list — check its ECB route in populate_mock_data.py`).toBeVisible({timeout: 10_000});
    await expect(row.locator('td[data-column-id="pair"]'), 'premise: the pair is shown as configured, EUR → USD').toHaveText(/EUR.*USD/);
    return {fxPage, row};
}

/** A row's own action, through the row's menu. */
async function rowAction(page: Page, slug: string, action: 'refresh' | 'swap'): Promise<void> {
    await page.getByTestId(`row-actions-${slug}`).click();
    await expect(page.getByTestId('context-menu')).toBeVisible();
    await page.getByTestId(`context-menu-action-${action}`).click();
}

/** A backend signal (`SMA`, offered in both domains) as the chart settings keep it. */
function smaSignal(id: string, period: number, color: string) {
    return {id, signalType: 'sma', params: {period}, style: {color, lineWidth: 1, lineType: 'dotted', markerStart: null, markerEnd: null}};
}

/** The signal a settings save keeps, and the one it drops: two backend signal requests before, one after. */
const KEPT_SIGNAL = smaSignal('e2e-xr60-sma-5', 5, '#2563eb');
const DROPPED_SIGNAL = smaSignal('e2e-xr60-sma-10', 10, '#dc2626');

/**
 * The FX chart settings (`__global_fx__`) seeded with `signals` for the signed-in user. They live in this test's browser
 * storage (`chartSettingsStore`, under the user's id): nothing shared is written, and the next page load reads them.
 */
async function seedFxSignals(page: Page, signals: ReadonlyArray<ReturnType<typeof smaSignal>>): Promise<void> {
    const me = await page.request.get('/api/v1/auth/me');
    expect(me.ok(), `GET /api/v1/auth/me answered HTTP ${me.status()}`).toBe(true);
    const userId = ((await me.json()) as {user?: {id?: unknown}}).user?.id;
    if (typeof userId !== 'number' || !Number.isSafeInteger(userId)) throw new Error(`GET /api/v1/auth/me gave no user id (${String(userId)}): the chart settings are stored under it`);
    await page.evaluate(
        ({storageKey, seeded}) => {
            const settings = {colorByBaseline: true, areaFill: true, gridLines: true, staleGradient: true, axisScales: {absolute: {mode: 'auto'}, percentage: {mode: 'include0'}, secondary: {}}, signals: [] as unknown[]};
            localStorage.setItem(storageKey, JSON.stringify({version: 3, globalSettings: settings, pairOverrides: [['__global_fx__', {...settings, signals: seeded}]]}));
        },
        {storageKey: `lf_${userId}_chartSettingsStore`, seeded: signals},
    );
}

/** Whether a bulk request asks, for some item, the backend signal `instanceId` alone: the reload after a save that dropped the others. */
function asksOnlySignal(request: Request, instanceId: string): boolean {
    try {
        const body = request.postDataJSON() as Array<{signals?: Array<{instance_id?: string}>}> | null;
        return Array.isArray(body) && body.some((item) => item.signals?.length === 1 && item.signals[0]?.instance_id === instanceId);
    } catch {
        return false;
    }
}

/**
 * Which period changes the FX list keeps, and when it asks them (MF-P2, after X-R53).
 *
 * The list asks the period changes of every pair as it loads or reloads, and of one pair alone after that pair's refresh
 * or sync. Several requests may be in flight at once and land in any order: the page keeps the answers through
 * `PeriodChangesLedger` (`periodChanges.ts`, its rules pinned in `periodChanges.test.ts`). Observed and held through the
 * network:
 *   · a pair refreshed during a reload of the whole list keeps its own Δ when the older reload answers last — the full
 *     and the one-pair requests told apart by their body, every pair or that one alone;
 *   · the page stays busy (`data-busy`) while a pair's own Δ are in flight, its rates already in;
 *   · what the Δ do not depend on asks none: a swap (the answer holds both orientations), a settings save that changes
 *     the signals, the retry of the signal catalogue. Each counter is proven by the load first, and read once the page
 *     has settled after the action.
 *
 * The pairs are the seeded EUR/USD and, as a witness, EUR/GBP: read and never written, as in X-R53. The figures come
 * from stubs over the real answers; a swapped row and the chart settings are this browser's state, never the
 * database's.
 *
 * Red today: a pair's own request has no part in the page's order — a reload begun before it overwrites its answer, and
 * the page reads idle while it is in flight; a swap, a settings save and the signals' retry reload the period changes
 * along with the rates.
 */
test.describe('FX list — which period changes the list keeps, and when it asks them (X-R60)', () => {
    // A ceiling, never a delay: each test loads the list's waves — pairs, rates, period changes — and reloads some.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('a pair refreshed while the whole list reloads keeps its own Δ when the older reload answers last', async ({page}) => {
        // About two months ending on a known day in the past: 1W fits the range.
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const failures: string[] = [];
        const reloads: FxPeriodChangesQuery[][] = [];
        const reloadGate = gate();
        let pairAnswered = 0;
        let reloadAnswered = 0;
        try {
            const {fxPage, row} = await openPairRow(page, range);
            const witness = page.locator(`tbody tr[data-row-id="${WITNESS_SLUG}"]`);
            await expect(witness, `${WITNESS_SLUG} is not in the FX list — check its ECB route in populate_mock_data.py`).toBeVisible();
            await expect(witness.locator('td[data-column-id="pair"]'), 'premise: the witness is shown as configured, EUR → GBP').toHaveText(/EUR.*GBP/);

            // From here on, the pair's own request is answered at once with fresh figures, while a request for every pair is
            // held until the gate opens, then answered with older figures for the pair and a marker figure for the witness.
            await page.route(FX_PERIOD_CHANGES, async (route) => {
                try {
                    const body = (route.request().postDataJSON() as FxPeriodChangesQuery[] | null) ?? [];
                    const alone = asksPairAlone(body, PAIR);
                    if (!alone) reloads.push(body);
                    const response = await route.fetch();
                    if (!response.ok()) {
                        failures.push(`HTTP ${response.status()}: ${await response.text()}`);
                        await route.fulfill({response});
                        return;
                    }
                    const answer = (await response.json()) as FxPeriodChangesAnswer;
                    if (alone) {
                        await route.fulfill({response, json: withPairRatios(answer, [[PAIR, FRESH_RATIOS]])});
                        pairAnswered += 1;
                        return;
                    }
                    await reloadGate.opened;
                    await route.fulfill({
                        response,
                        json: withPairRatios(answer, [
                            [PAIR, STALE_RATIOS],
                            [WITNESS, WITNESS_RATIOS],
                        ]),
                    });
                    reloadAnswered += 1;
                } catch (error) {
                    // Nobody awaits a route callback, so what it throws would land on whatever runs next: recorded, and the
                    // request let through, for the test to fail on its own assertions.
                    failures.push(String(error));
                    await route.continue().catch(() => undefined);
                }
            });

            // The reload of every pair, its period changes held.
            const refreshAll = page.getByTestId('fx-refresh-all-button');
            await expect(refreshAll).toBeEnabled();
            await refreshAll.click();
            await expect.poll(() => reloads.length, {message: 'the reload of the list never asked the period changes of its pairs', timeout: 10_000}).toBeGreaterThan(0);
            expect(reloads[0], 'premise: the reload asks every pair — the pair and the witness among them — up to the end of the range').toEqual(expect.arrayContaining([expect.objectContaining({...PAIR, as_of: range.end}), expect.objectContaining({...WITNESS, as_of: range.end})]));
            // Its rates are back, the row drawing a rate again: only its period changes are still held.
            await expect(row.locator('td[data-column-id="rate"]'), 'the reload’s rates reached the row').toHaveText(RATE_FIGURE, {timeout: 15_000});

            // The pair's own refresh, begun after the reload: its answer lands first.
            await rowAction(page, SLUG, 'refresh');
            await expect.poll(() => pairAnswered, {message: 'the pair’s refresh never asked its own period changes', timeout: 10_000}).toBeGreaterThan(0);
            await expect(deltaCell(row, '1D'), 'the pair’s own answer is shown as it lands: change_ratio 0.0125').toHaveText(percentCell('+1.25'), {timeout: 10_000});
            expect(reloadAnswered, 'premise: the reload is still held').toBe(0);

            // Then the reload answers, last, with older figures for the pair.
            reloadGate.open();
            await expect.poll(() => reloadAnswered, {message: 'the held reload was never answered', timeout: 10_000}).toBeGreaterThan(0);
            // Presence first: the reload's answer reached the table.
            await expect(deltaCell(witness, '1D'), 'the reload’s answer is applied to the pairs only it asked: change_ratio 0.0321').toHaveText(percentCell('+3.21'), {timeout: 10_000});
            await waitForSettled(fxPage, 20_000);
            expect(failures, 'the period changes reached the page').toEqual([]);

            // The reload began before the pair's own refresh: its older figures must not replace the pair's.
            await expect(deltaCell(row, '1D'), 'the pair keeps its own +1.25 %, not the older reload’s −50 %').toHaveText(percentCell('+1.25'));
            await expect(deltaCell(row, '1W'), 'the pair keeps its own −25 %, not the older reload’s +12.50 %').toHaveText(percentCell('-25.00'));
        } finally {
            reloadGate.open();
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('the page stays busy while a pair’s own Δ are in flight, its rates already in', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const failures: string[] = [];
        const pairGate = gate();
        let pairAsked = 0;
        let pairAnswered = 0;
        let ratesEmptied = 0;
        try {
            const {fxPage, row} = await openPairRow(page, range);
            const rateCell = row.locator('td[data-column-id="rate"]');
            // The marker below says the pair's rates are in only if the pair shows a rate before.
            await expect(rateCell, 'premise: the pair has rates over the range — check populate_fx_rates in populate_mock_data.py').toHaveText(RATE_FIGURE);

            // From here on, the pair's own period changes are held until the gate opens; any other request goes through.
            await page.route(FX_PERIOD_CHANGES, async (route) => {
                try {
                    const body = (route.request().postDataJSON() as FxPeriodChangesQuery[] | null) ?? [];
                    if (!asksPairAlone(body, PAIR)) {
                        await route.continue();
                        return;
                    }
                    pairAsked += 1;
                    const response = await route.fetch();
                    if (!response.ok()) {
                        failures.push(`HTTP ${response.status()}: ${await response.text()}`);
                        await route.fulfill({response});
                        return;
                    }
                    const answer = (await response.json()) as FxPeriodChangesAnswer;
                    await pairGate.opened;
                    await route.fulfill({response, json: withPairRatios(answer, [[PAIR, FRESH_RATIOS]])});
                    pairAnswered += 1;
                } catch (error) {
                    failures.push(String(error));
                    await route.continue().catch(() => undefined);
                }
            });
            // The pair's own rates are answered at once, with no point in the range: the row then draws the missing-rate
            // marker, the sign that the rates are in and the pair no longer loading.
            await page.route(FX_CONVERT, async (route) => {
                try {
                    const body = (route.request().postDataJSON() as Array<{from_amount?: {code?: string}; to?: string}> | null) ?? [];
                    if (!(body.length === 1 && body[0].from_amount?.code === PAIR.base && body[0].to === PAIR.quote)) {
                        await route.continue();
                        return;
                    }
                    const response = await route.fetch();
                    if (!response.ok()) {
                        failures.push(`HTTP ${response.status()}: ${await response.text()}`);
                        await route.fulfill({response});
                        return;
                    }
                    const answer = (await response.json()) as Record<string, unknown>;
                    await route.fulfill({response, json: {...answer, results: [], success_count: 0}});
                    ratesEmptied += 1;
                } catch (error) {
                    failures.push(String(error));
                    await route.continue().catch(() => undefined);
                }
            });

            await rowAction(page, SLUG, 'refresh');
            await expect.poll(() => pairAsked, {message: 'the pair’s refresh never asked its own period changes', timeout: 10_000}).toBeGreaterThan(0);
            await expect.poll(() => ratesEmptied, {message: 'the pair’s refresh never asked its own rates', timeout: 10_000}).toBeGreaterThan(0);
            await expect(rateCell.locator('[data-fx-rate-state="missing"]'), 'the pair’s rates are in: an empty answer, drawn as the missing-rate marker').toBeVisible({timeout: 10_000});
            expect(pairAnswered, 'premise: the pair’s Δ are still held').toBe(0);
            await expect(fxPage, 'the pair’s Δ are still in flight: the page must say it is busy').toHaveAttribute('data-busy', 'true');

            pairGate.open();
            await expect.poll(() => pairAnswered, {message: 'the held answer was never delivered', timeout: 10_000}).toBeGreaterThan(0);
            await expect(deltaCell(row, '1D'), 'the pair’s own Δ once they land: change_ratio 0.0125').toHaveText(percentCell('+1.25'), {timeout: 10_000});
            await expect(fxPage, 'every request is over: the page is no longer busy').toHaveAttribute('data-busy', 'false', {timeout: 10_000});
            expect(failures, 'the rates and the period changes reached the page').toEqual([]);
        } finally {
            pairGate.open();
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('swapping a pair asks no period changes: the list holds them both ways', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const failures: string[] = [];
        let asked = 0;
        try {
            await page.route(FX_PERIOD_CHANGES, async (route) => {
                // Counted on arrival, before any answer can reach the page: a page that has settled has been counted.
                asked += 1;
                try {
                    const response = await route.fetch();
                    if (!response.ok()) {
                        failures.push(`HTTP ${response.status()}: ${await response.text()}`);
                        await route.fulfill({response});
                        return;
                    }
                    const answer = (await response.json()) as FxPeriodChangesAnswer;
                    await route.fulfill({response, json: withPairRatios(answer, [[PAIR, STUBBED_RATIOS]])});
                } catch (error) {
                    failures.push(String(error));
                    await route.continue().catch(() => undefined);
                }
            });
            const {fxPage, row} = await openPairRow(page, range);
            expect(asked, 'premise: the list asks the period changes as it loads — the counter counts').toBeGreaterThan(0);
            await expect(deltaCell(row, '1D'), 'as configured: change_ratio 0.0125').toHaveText(percentCell('+1.25'), {timeout: 10_000});
            const askedBefore = asked;

            await rowAction(page, SLUG, 'swap');
            await expect(row.locator('td[data-column-id="pair"]'), 'the row is swapped: USD → EUR').toHaveText(/USD.*EUR/);
            await waitForSettled(fxPage, 20_000);
            // The swapped figures are those of the answer already in: inverse_change_ratio.
            await expect(deltaCell(row, '1D'), '1D swapped: inverse_change_ratio -0.04').toHaveText(percentCell('-4.00'));
            await expect(deltaCell(row, '1W'), '1W swapped: inverse_change_ratio 0.5').toHaveText(percentCell('+50.00'));
            expect(failures, 'the period changes reached the page').toEqual([]);

            expect(asked, 'the swap asked the period changes again, though the list already holds them both ways').toBe(askedBefore);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('a settings save that changes the signals asks no period changes', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        let asked = 0;
        try {
            await seedFxSignals(page, [KEPT_SIGNAL, DROPPED_SIGNAL]);
            await page.route(FX_PERIOD_CHANGES, async (route) => {
                // Counted on arrival, before any answer can reach the page: a page that has settled has been counted.
                asked += 1;
                await route.continue();
            });
            await goToFxPage(page, range);
            const fxPage = page.getByTestId('fx-page');
            await page.getByTestId('view-mode-list').click();
            await waitForSettled(fxPage, 20_000);
            expect(asked, 'premise: the list asks the period changes as it loads — the counter counts').toBeGreaterThan(0);

            await page.getByTestId('fx-chart-settings-button').click();
            const modal = page.getByTestId('chart-settings-modal');
            await expect(modal).toBeVisible();
            const kept = modal.getByTestId(`signal-card-${KEPT_SIGNAL.id}`);
            const dropped = modal.getByTestId(`signal-card-${DROPPED_SIGNAL.id}`);
            await expect(kept, 'premise: the seeded signals are the list’s — check the chart settings storage key').toBeVisible();
            await expect(dropped).toBeVisible();
            await modal.getByTestId(`signal-remove-${DROPPED_SIGNAL.id}`).click();
            await expect(dropped).toHaveCount(0);
            await expect(kept).toBeVisible();

            const askedBefore = asked;
            const signalsReloaded = page.waitForResponse((response) => FX_CONVERT.test(response.url()) && asksOnlySignal(response.request(), KEPT_SIGNAL.id), {timeout: 20_000});
            await page.getByTestId('chart-settings-apply').click();
            await expect(modal).toBeHidden();
            // Presence first: the save reloaded the rates and signals, the one signal left.
            expect((await signalsReloaded).ok(), 'the rates and signals, asked again with the signal left').toBe(true);
            await expect(page.getByTestId('fx-refresh-all-button'), 'the reload the save started is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            await waitForSettled(fxPage, 20_000);

            expect(asked, 'the save asked the period changes again, though they do not depend on the signals').toBe(askedBefore);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('the retry of the signal catalogue asks no period changes', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        let asked = 0;
        let catalogAsked = 0;
        let catalogDown = true;
        try {
            // The signal catalogue fails as the list loads, so the settings dialog offers its retry.
            await page.route(FX_SIGNAL_CATALOG, async (route) => {
                catalogAsked += 1;
                if (catalogDown) await route.fulfill({status: 500, json: {detail: 'synthetic: the FX signal catalogue is unavailable (X-R60)'}});
                else await route.continue();
            });
            await page.route(FX_PERIOD_CHANGES, async (route) => {
                // Counted on arrival, before any answer can reach the page: a page that has settled has been counted.
                asked += 1;
                await route.continue();
            });
            await goToFxPage(page, range);
            const fxPage = page.getByTestId('fx-page');
            expect(catalogAsked, 'premise: the list asked the signal catalogue as it loaded').toBeGreaterThan(0);
            expect(asked, 'premise: the list asks the period changes as it loads — the counter counts').toBeGreaterThan(0);

            await page.getByTestId('fx-chart-settings-button').click();
            const modal = page.getByTestId('chart-settings-modal');
            await expect(modal).toBeVisible();
            const unavailable = modal.getByTestId('signal-backend-error');
            await expect(unavailable, 'the catalogue failed: the dialog says so, and offers its retry').toBeVisible();

            catalogDown = false;
            const askedBefore = asked;
            const catalogAskedBefore = catalogAsked;
            // The notice's one button is its retry.
            await unavailable.getByRole('button').click();
            await expect(unavailable, 'the retry read the catalogue again').toBeHidden({timeout: 10_000});
            expect(catalogAsked, 'the retry asked the catalogue').toBeGreaterThan(catalogAskedBefore);
            await expect(page.getByTestId('fx-refresh-all-button'), 'the retry is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            await waitForSettled(fxPage, 20_000);

            expect(asked, 'the retry asked the period changes again, though they do not depend on the signals').toBe(askedBefore);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });
});
