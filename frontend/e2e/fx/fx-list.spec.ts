/**
 * FX List Page — E2E Tests
 *
 * Tests the FX list page: card rendering, filtering, navigation, and basic actions.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {IntlMessageFormat} from 'intl-messageformat';
import {expect, test, type Locator, type Page, type Request} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {t as catalogueText} from '../fixtures/i18n-data';
import {maximisePageSize} from '../fixtures/paging';
import {pageLanguage} from '../fixtures/sync-overwrite';
import {goToFxPage} from './fx-helpers';
import {assetComparison, assetIdByName, pairComparison, seedChartComparisons} from '../fixtures/chartComparisons';

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

    /**
     * Y-40, FX — the top bar's three views: the list opens on absolute rates; in the rolling-return view each card asks its
     * pair's rolling return (a sampled conversion named `fx:<slug>`, with ASSET_CALENDAR_ROLLING_RETURN) and settles
     * (`data-calendar-state`: ready, partial or unavailable, never stuck loading nor in error).
     */
    test('the top bar’s three views update every FX card, opening on Abs, and the rolling return is asked and drawn', async ({page}) => {
        const asked: unknown[] = [];
        page.on('request', (request) => {
            if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/fx/currencies/convert') return;
            asked.push(...((request.postDataJSON() as unknown[]) ?? []));
        });
        await goToFxPage(page);
        await waitForSettled(page.getByTestId('fx-page'), 20_000);
        const cards = page.locator('[data-testid^="fx-card-"][data-view-mode]');
        await expect.poll(() => cards.count(), {timeout: 10_000}).toBeGreaterThan(0);
        const everyCardUses = async (mode: 'absolute' | 'percentage' | 'calendar-return') => cards.evaluateAll((nodes, expected) => nodes.length > 0 && nodes.every((node) => (node as HTMLElement).dataset.viewMode === expected), mode);

        await expect.poll(() => everyCardUses('absolute'), {message: 'the FX list opens on absolute rates', timeout: 5_000}).toBe(true);
        await expect(page.getByTestId('fx-global-view-absolute')).toHaveAttribute('aria-pressed', 'true');

        await page.getByTestId('fx-global-view-calendar-return').click();
        await expect.poll(() => everyCardUses('calendar-return'), {timeout: 5_000}).toBe(true);
        await waitForSettled(page.getByTestId('fx-page'), 20_000);
        const states = await cards.evaluateAll((nodes) => nodes.map((node) => (node as HTMLElement).dataset.calendarState));
        expect(
            states.filter((state) => !['ready', 'partial', 'unavailable'].includes(String(state))),
            'every card settles its rolling return: ready, partial or unavailable',
        ).toEqual([]);
        expect(states, 'the seeded pairs have the history for a rolling return').toContain('ready');
        const calendarItems = asked.filter((item) => ((item as {signals?: Array<{signal_code?: string}>}).signals ?? []).some((signal) => signal.signal_code === 'ASSET_CALENDAR_ROLLING_RETURN'));
        expect(calendarItems.length, 'the cards asked their rolling return').toBeGreaterThan(0);
        expect(
            calendarItems.every((item) => /^fx:[A-Z]{3}-[A-Z]{3}$/.test(String((item as {key?: string}).key)) || typeof (item as {sample_like?: string}).sample_like === 'string'),
            'each card’s conversion is named for its compared pairs',
        ).toBe(true);

        await page.getByTestId('fx-global-view-percentage').click();
        await expect.poll(() => everyCardUses('percentage'), {timeout: 5_000}).toBe(true);
    });

    /** Y-40, FX (V-1 a, V-3 a) — a card's button turns percent → rolling return → absolute; the card keeps its view across a reload until the top bar changes. */
    test('one FX card turns its own view, keeps it across a reload, until a later global change', async ({page}) => {
        await goToFxPage(page);
        await waitForSettled(page.getByTestId('fx-page'), 20_000);
        const cards = page.locator('[data-testid^="fx-card-"][data-view-mode]');
        await expect.poll(() => cards.count(), {timeout: 10_000}).toBeGreaterThan(1);
        const chosenTestId = await cards.evaluateAll(
            (nodes) =>
                nodes
                    .map((node) => node.getAttribute('data-testid'))
                    .filter(Boolean)
                    .sort()[0],
        );
        if (!chosenTestId) throw new Error('the seeded FX list must show at least two cards');
        const chosen = page.getByTestId(chosenTestId);
        const everyOtherCardUses = async (mode: string) =>
            cards.evaluateAll(
                (nodes, expected) => {
                    const others = nodes.filter((node) => node.getAttribute('data-testid') !== expected.chosenTestId);
                    return others.length > 0 && others.every((node) => (node as HTMLElement).dataset.viewMode === expected.mode);
                },
                {chosenTestId, mode},
            );

        await page.getByTestId('fx-global-view-percentage').click();
        await expect.poll(() => everyOtherCardUses('percentage'), {timeout: 5_000}).toBe(true);
        await expect(chosen).toHaveAttribute('data-view-mode', 'percentage');

        const toggle = chosen.getByTestId('fx-card-view-toggle');
        await expect(toggle).toHaveAttribute('data-next-view', 'calendar-return');
        await toggle.click();
        await expect(chosen).toHaveAttribute('data-view-mode', 'calendar-return');
        await expect(chosen).toHaveAttribute('data-calendar-state', /^(ready|partial|unavailable)$/, {timeout: 15_000});
        await toggle.click();
        await expect(chosen).toHaveAttribute('data-view-mode', 'absolute');
        await expect.poll(() => everyOtherCardUses('percentage'), {timeout: 5_000}).toBe(true);

        await page.reload();
        await waitForSettled(page.getByTestId('fx-page'), 20_000);
        await expect(page.getByTestId(chosenTestId), 'the card’s view is saved (V-1 a)').toHaveAttribute('data-view-mode', 'absolute', {timeout: 10_000});
        await expect.poll(() => everyOtherCardUses('percentage'), {timeout: 5_000}).toBe(true);

        await page.getByTestId('fx-global-view-calendar-return').click();
        await expect(page.getByTestId(chosenTestId), 'the top bar resets every card (V-3 a)').toHaveAttribute('data-view-mode', 'calendar-return');
        await page.getByTestId('fx-global-view-absolute').click();
        await expect(page.getByTestId(chosenTestId)).toHaveAttribute('data-view-mode', 'absolute');
        await expect.poll(() => everyOtherCardUses('absolute'), {timeout: 5_000}).toBe(true);
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

// ============================================================================
// The Δ over the range is the backend's, both ways (workstream Y, lot X-R59 A)
// ============================================================================

/** One pair of a period-changes request (`FXPeriodChangesRequest`), with the first day of the range it asks the Δ over. */
type FxRangeChangesQuery = FxPeriodChangesQuery & {range_start?: string | null};

/** A pair's Δ over the range as a stub answers it (`FXRangeChange`): decimal strings, null where the backend has none. */
type FxRangeChange = {change_abs: string | null; change_ratio: string | null; inverse_change_abs: string | null; inverse_change_ratio: string | null};

/**
 * +42.42 % and +0.1234 as configured; −21.21 % and −0.0567 inverted, which are neither the inversion of the first
 * (−29.79 %) nor its negation, so a swapped pair shows them only by reading the inverse fields. No seeded rate moves 42 %
 * in two months: a figure on screen comes from the answer.
 */
const STUBBED_RANGE_CHANGE: FxRangeChange = {change_abs: '0.1234', change_ratio: '0.4242', inverse_change_abs: '-0.0567', inverse_change_ratio: '-0.2121'};

/** A Δ over the range the backend could not compute: every field null, both ways. */
const NO_RANGE_CHANGE: FxRangeChange = {change_abs: null, change_ratio: null, inverse_change_abs: null, inverse_change_ratio: null};

/** What `routeFxRangeChanges` saw: every pair asked, what went wrong, how many requests it answered. */
type FxRangeChangesLog = {asked: FxRangeChangesQuery[]; failures: string[]; answered: number};

/**
 * The FX period changes, routed through the backend: every request is recorded, and each answer goes back with the
 * `range_change` of the pairs `stubs` names replaced, every other item as the backend gave it. A non-OK answer is a
 * failure, passed on as it came.
 */
async function routeFxRangeChanges(page: Page, stubs: ReadonlyArray<readonly [{base: string; quote: string}, FxRangeChange]>): Promise<FxRangeChangesLog> {
    const log: FxRangeChangesLog = {asked: [], failures: [], answered: 0};
    await page.route(FX_PERIOD_CHANGES, async (route) => {
        try {
            log.asked.push(...((route.request().postDataJSON() as FxRangeChangesQuery[] | null) ?? []));
            const response = await route.fetch();
            if (!response.ok()) {
                log.failures.push(`HTTP ${response.status()}: ${await response.text()}`);
                await route.fulfill({response});
                return;
            }
            const answer = (await response.json()) as {items?: Array<{base: string; quote: string; range_change?: Record<string, unknown> | null}>};
            const items = (answer.items ?? []).map((item) => {
                const stub = stubs.find(([pair]) => pair.base === item.base && pair.quote === item.quote)?.[1];
                return stub ? {...item, range_change: {...(item.range_change ?? {}), ...stub}} : item;
            });
            await route.fulfill({response, json: {...answer, items}});
        } catch (error) {
            // Nobody awaits a route callback, so what it throws would land on whatever runs next: recorded, and the
            // request let through, for the test to fail on its own assertions.
            log.failures.push(String(error));
            await route.continue().catch(() => undefined);
        } finally {
            log.answered += 1;
        }
    });
    return log;
}

/** A row's Δ over the range, by the column ids DataTable publishes on each cell: the absolute change and the percentage. */
function rangeCells(row: Locator): {abs: Locator; pct: Locator} {
    return {abs: row.locator('td[data-column-id="deltaAbs"]'), pct: row.locator('td[data-column-id="deltaPct"]')};
}

/** A Δ Abs cell as any of the four languages writes it, matched whole: the signed figure with four decimals and either mark; a minus may be `-` or `−`. */
function amountCell(figure: string): RegExp {
    const parts = /^([+-])(\d+)\.(\d{4})$/.exec(figure);
    if (!parts) throw new Error(`amountCell: ${figure} is not a signed decimal with four digits such as +0.1234`);
    return new RegExp(`^\\s*${parts[1] === '+' ? '\\+' : '[-\\u2212]'}${parts[2]}[.,]${parts[3]}\\s*$`);
}

/** A card's Δ as any of the four languages writes it, matched whole: the arrow of its sign (▲, ▼), then the percentage as `percentCell` reads it. */
function arrowedPercent(figure: string): RegExp {
    return new RegExp(`^\\s*${figure.startsWith('-') ? '▼' : '▲'}${percentCell(figure).source.slice(1)}`);
}

/**
 * The FX list shows each pair's Δ over the range on screen (X-R59, lot A) — the table's Δ Abs and Δ % columns, the
 * card's Δ: the change from the first to the last day of the range, which the backend computes both ways, the
 * `range_change` of `POST /fx/currencies/period-changes`, asked with the first day of the range (`range_start`) in every
 * item, as it is (the backend takes any day from the year 1, D-P4). A pair shown as
 * configured reads `change_abs` and `change_ratio`; swapped, `inverse_change_abs` and `inverse_change_ratio`; where the
 * backend has none, the table shows its empty marker and the card no Δ. The browser computes none, though it holds the
 * rates.
 *
 * The pairs are the seeded EUR/USD and, as a witness, EUR/GBP: read and never written, as in X-R53. The real answer is
 * fetched and only their items are changed in it, with figures their rates do not give over these days; a swapped row
 * or card is this browser's state (`fxCardInversionStore`), never the database's. The range before 1900 has its rates
 * answered in the browser, empty, so no conversion is walked back over a century for every pair; its period changes
 * still reach the backend, which says whether it takes the first day asked, as it is.
 *
 * Red before the cure of lot A: the request asks no `range_start`, and the table and the card compute their Δ from the
 * rates they loaded.
 */
test.describe('FX list — the Δ over the range is the backend’s, both ways (X-R59)', () => {
    // A ceiling, never a delay: the list loads its waves — pairs, rates, period changes — for every configured pair, and
    // loads the rates again once a pair is swapped.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('every pair asks the first day of the range on screen; the row shows the answer’s Δ Abs and Δ %, the inverse ones once swapped', async ({page}) => {
        // About two months ending on a known day in the past.
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        try {
            const log = await routeFxRangeChanges(page, [[PAIR, STUBBED_RANGE_CHANGE]]);
            const {fxPage, row} = await openPairRow(page, range);

            // Asked and answered — the page holds `data-busy` until the period changes are in; the poll is a deadline.
            await expect.poll(() => log.answered, {message: 'the FX list never asked POST /fx/currencies/period-changes', timeout: 10_000}).toBeGreaterThan(0);
            expect(log.failures, 'the period changes reached the page').toEqual([]);
            expect(log.asked, 'the pair asks its Δ from the first day of the range on screen to the last').toContainEqual(expect.objectContaining({...PAIR, as_of: range.end, range_start: range.start}));
            expect([...new Set(log.asked.map((item) => item.range_start))], 'every pair asks its Δ from the first day of the range on screen').toEqual([range.start]);

            // As configured, EUR → USD: change_abs and change_ratio.
            const cells = rangeCells(row);
            await expect(cells.pct, 'Δ %: change_ratio 0.4242').toHaveText(percentCell('+42.42'), {timeout: 10_000});
            await expect(cells.abs, 'Δ Abs: change_abs 0.1234').toHaveText(amountCell('+0.1234'));

            // Swapped through the row's own action, USD → EUR: inverse_change_abs and inverse_change_ratio.
            await rowAction(page, SLUG, 'swap');
            await expect(row.locator('td[data-column-id="pair"]'), 'the row is swapped: USD → EUR').toHaveText(/USD.*EUR/);
            await waitForSettled(fxPage, 20_000);
            await expect(cells.pct, 'Δ % swapped: inverse_change_ratio -0.2121').toHaveText(percentCell('-21.21'), {timeout: 10_000});
            await expect(cells.abs, 'Δ Abs swapped: inverse_change_abs -0.0567').toHaveText(amountCell('-0.0567'));
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('the card shows the answer’s Δ over the range, the inverse one once swapped', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        try {
            const log = await routeFxRangeChanges(page, [[PAIR, STUBBED_RANGE_CHANGE]]);
            await goToFxPage(page, range);
            const fxPage = page.getByTestId('fx-page');
            await page.getByTestId('view-mode-grid').click();
            await waitForSettled(fxPage, 20_000);
            const card = page.getByTestId(`fx-card-${SLUG}`);
            await expect(card, `${SLUG} is not in the FX list — check its ECB route in populate_mock_data.py`).toBeVisible({timeout: 10_000});
            const label = card.getByTestId('fx-pair-label');
            await expect(label, 'premise: the card shows the pair as configured, EUR → USD').toHaveText(/EUR[\s\S]*USD/);

            await expect.poll(() => log.answered, {message: 'the FX list never asked POST /fx/currencies/period-changes', timeout: 10_000}).toBeGreaterThan(0);
            expect(log.failures, 'the period changes reached the page').toEqual([]);
            expect(log.asked, 'the pair asks its Δ from the first day of the range on screen to the last').toContainEqual(expect.objectContaining({...PAIR, as_of: range.end, range_start: range.start}));

            const delta = card.getByTestId('fx-range-delta');
            await expect(delta, 'as configured: change_ratio 0.4242').toHaveText(arrowedPercent('+42.42'), {timeout: 10_000});

            // Swapped through the card's own button, USD → EUR: inverse_change_ratio, from the answer already in.
            await card.getByTestId('fx-swap-btn').click();
            await expect(label, 'the card is swapped: USD → EUR').toHaveText(/USD[\s\S]*EUR/);
            await waitForSettled(fxPage, 20_000);
            await expect(delta, 'swapped: inverse_change_ratio -0.2121').toHaveText(arrowedPercent('-21.21'), {timeout: 10_000});
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('an answer with every field null leaves the row’s Δ Abs and Δ % empty and draws no Δ on the card, though the pair has rates', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        try {
            // The pair is answered with no Δ; the witness with the stub, so its figures on screen say the answer reached the
            // page — both are in the same answer.
            const log = await routeFxRangeChanges(page, [
                [PAIR, NO_RANGE_CHANGE],
                [WITNESS, STUBBED_RANGE_CHANGE],
            ]);
            const {fxPage, row} = await openPairRow(page, range);
            const witnessRow = page.locator(`tbody tr[data-row-id="${WITNESS_SLUG}"]`);
            await expect(witnessRow, `${WITNESS_SLUG} is not in the FX list — check its ECB route in populate_mock_data.py`).toBeVisible();

            // Presence first: the answer reached the table, and the pair has rates over the range — a browser that still
            // computed the Δ would have them to compute it from.
            await expect(rangeCells(witnessRow).pct, 'the witness shows the answer’s change_ratio 0.4242').toHaveText(percentCell('+42.42'), {timeout: 10_000});
            await expect(row.locator('td[data-column-id="rate"]'), 'premise: the pair has rates over the range — check populate_fx_rates in populate_mock_data.py').toHaveText(RATE_FIGURE);
            await waitForSettled(fxPage, 20_000);
            expect(log.failures, 'the period changes reached the page').toEqual([]);
            expect(log.asked, 'premise: the pair asks its Δ over the range on screen').toContainEqual(expect.objectContaining({...PAIR, as_of: range.end, range_start: range.start}));

            const cells = rangeCells(row);
            await expect(cells.abs, 'every field of range_change is null: Δ Abs shows the empty marker').toHaveText(EMPTY_CELL);
            await expect(cells.pct, 'every field of range_change is null: Δ % shows the empty marker').toHaveText(EMPTY_CELL);

            // The same answer, as cards: the witness shows its Δ, the pair its rate and no Δ.
            await page.getByTestId('view-mode-grid').click();
            const card = page.getByTestId(`fx-card-${SLUG}`);
            await expect(page.getByTestId(`fx-card-${WITNESS_SLUG}`).getByTestId('fx-range-delta'), 'the witness card shows the answer’s change_ratio 0.4242').toHaveText(arrowedPercent('+42.42'), {timeout: 10_000});
            await expect(card, 'premise: the card shows the pair’s rate').toContainText(RATE_FIGURE);
            await expect(card.getByTestId('fx-range-delta'), 'every field of range_change is null: no Δ on the card').toHaveCount(0);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('a range that starts before 1900 asks every Δ from its first day, as it is, which the backend takes', async ({page}) => {
        // A month before 1900: the backend takes any day from the year 1 (D-P4), so the first day goes as it is.
        const range = {start: '1899-12-01', end: daysAgoIso(10)};
        try {
            // The rates answered in the browser, empty: no conversion is walked back over a century for every pair.
            await page.route(FX_CONVERT, async (route) => {
                await route.fulfill({json: {results: [], success_count: 0, errors: []}});
            });
            const log = await routeFxRangeChanges(page, [[PAIR, STUBBED_RANGE_CHANGE]]);
            const {row} = await openPairRow(page, range);

            await expect.poll(() => log.answered, {message: 'the FX list never asked POST /fx/currencies/period-changes', timeout: 10_000}).toBeGreaterThan(0);
            expect(log.failures, 'the backend took every request: it takes any day from the year 1').toEqual([]);
            expect(log.asked, `the pair asks its Δ from ${range.start} to the last day of the range`).toContainEqual(expect.objectContaining({...PAIR, as_of: range.end, range_start: range.start}));
            expect([...new Set(log.asked.map((item) => item.range_start))], `every pair asks its Δ from ${range.start}, never raised`).toEqual([range.start]);
            await expect(rangeCells(row).pct, 'the Δ over the range still reaches the row').toHaveText(percentCell('+42.42'), {timeout: 10_000});
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });
});

// ============================================================================
// A bulk rate request refused as too large says so (workstream X, lot X-R58)
// ============================================================================

/** The catalogue's sentence for a bulk request refused for its days (`bulk_too_many_days`, Z-25). */
const BULK_TOO_MANY_DAYS_KEY = 'common.bulkRefusal.tooManyDays';

/**
 * The numbers the stubbed refusal carries: the backend's budget of item-days, and a count past it. Seven digits are
 * grouped in the four languages whatever the CLDR data of the runtime, so the browser and Node write the budget alike.
 */
const REFUSED_DAYS = {max_item_days: 1_000_000, item_days: 1_234_567} as const;

/** The 422 of a convert past the budget, worded as the backend words it for the FX convert: its count is «at least». */
const REFUSED_DAYS_DETAIL = {code: 'bulk_too_many_days', message: `A bulk request may build at most ${REFUSED_DAYS.max_item_days} per-day points, and this one would build at least ${REFUSED_DAYS.item_days}`, ...REFUSED_DAYS};

/** One conversion of a convert request (`FXConversionRequest`), as far as these tests read it. */
type FxConversionQuery = {from_amount?: {code?: string}; to?: string};

/** The pair a conversion asks, whichever way its card shows it: `BASE-QUOTE`, sorted as the slugs are. */
function conversionSlug(item: FxConversionQuery): string {
    return [item.from_amount?.code ?? '', item.to ?? ''].sort().join('-');
}

/**
 * `key` as the `lang` catalogue words it, formatted with `values` by `intl-messageformat`, the formatter svelte-i18n
 * compiles messages with — the reading of `overwriteWarningSentence` (`fixtures/sync-overwrite.ts`) for any message.
 * A catalogue without the message fails here, by name: a key that resolved to itself would let a toast printing the
 * key pass.
 */
function catalogueSentence(lang: string, key: string, values: Record<string, number>): string {
    const message = catalogueText(lang, key);
    expect(message, `the "${lang}" catalogue has a message for ${key}`).not.toBe(key);
    return String(new IntlMessageFormat(message, lang).format(values));
}

/**
 * A bulk rate request the backend refuses as too large reaches the user (X-R58). Since Z-25 `POST /fx/currencies/convert`
 * refuses a request past its caps with a coded 422 (`backend/app/utils/date_range_limits.py`); the list sends its rates
 * through `sendBulkBatches` (Z-27), which splits a batch refused for its days and fails on the first part it cannot
 * split — a single pair, or the last level. The list then says so in an error toast: the catalogue's
 * `common.bulkRefusal.tooManyDays`, with the budget the refusal carries and no count (the convert's may be a bound) —
 * whether the whole list was loading (`fetchAllPairSeries`) or one pair (`fetchPairSeries`, the row's own refresh).
 * Any other failure stays as it was: logged, the cards falling back to what is cached, and no toast.
 *
 * Observed through the network: the refusals and the plain failure are the stubs'. The list is loaded over about two
 * months ending on a known day in the past, as in X-R53; a fresh page holds no rate, so every pair is asked, the seeded
 * EUR/USD among them — read, never written. The sentence is the catalogue's, formatted for the page's language: never a
 * translation written here.
 *
 * Red today: `loadFxRatesAndSignalsBulk` throws the refusal on, and both catches of the page only log it. The guard is
 * red with them: its first step is the refused load's toast, the proof that the page's error toasts are observed at all.
 */
test.describe('FX list — a bulk rate request refused as too large says so (X-R58)', () => {
    // A ceiling, never a delay: each test loads the list's waves — pairs, rates refused or not, period changes — and the
    // last two ask for rates once more.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('a load refused for its days, down to a part it cannot split, shows the catalogue’s sentence in an error toast', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const asked: FxConversionQuery[] = [];
        const sizes: number[] = [];
        const failures: string[] = [];
        try {
            // Every conversion request is refused for its days: the list splits its batch again and again, and gives up on
            // the first part it cannot split.
            await page.route(FX_CONVERT, async (route) => {
                try {
                    const body = (route.request().postDataJSON() as FxConversionQuery[] | null) ?? [];
                    asked.push(...body);
                    sizes.push(body.length);
                    await route.fulfill({status: 422, json: {detail: REFUSED_DAYS_DETAIL}});
                } catch (error) {
                    // Nobody awaits a route callback, so what it throws would land on whatever runs next: recorded, and the
                    // request let through, for the test to fail on its own assertions.
                    failures.push(String(error));
                    await route.continue().catch(() => undefined);
                }
            });

            // The list over the range; `goToFxPage` returns once `data-busy` says the load is over, refusals included.
            await goToFxPage(page, range);
            expect(failures, 'the refusals reached the page').toEqual([]);
            expect(asked.map(conversionSlug), `premise: the list asked the rates of ${SLUG} — check its ECB route in populate_mock_data.py`).toContain(SLUG);

            // One load, given up once: one error toast, and its words are the catalogue's.
            const errorToasts = page.getByTestId('toast-error');
            await expect(errorToasts, `the refused load (requests of ${sizes.join(' → ')} pairs) must say so in an error toast — the list only logged it`).toHaveCount(1, {timeout: 10_000});
            const sentence = catalogueSentence(await pageLanguage(page), BULK_TOO_MANY_DAYS_KEY, {max: REFUSED_DAYS.max_item_days});
            await expect(errorToasts, 'the catalogue’s sentence, with the budget of the refusal').toHaveText(sentence);
            await expect(errorToasts).toBeVisible();
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('a pair’s own refresh refused for its days shows the same sentence in an error toast', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const failures: string[] = [];
        let refused = 0;
        try {
            // The list loads as it is, the pair's row on screen.
            await openPairRow(page, range);
            const errorToasts = page.getByTestId('toast-error');
            await expect(errorToasts, 'premise: the load raised no error toast').toHaveCount(0);

            // From here on, a request for the pair alone — its own refresh — is refused for its days; any other goes through.
            await page.route(FX_CONVERT, async (route) => {
                try {
                    const body = (route.request().postDataJSON() as FxConversionQuery[] | null) ?? [];
                    if (body.length === 0 || !body.every((item) => conversionSlug(item) === SLUG)) {
                        await route.continue();
                        return;
                    }
                    await route.fulfill({status: 422, json: {detail: REFUSED_DAYS_DETAIL}});
                    refused += 1;
                } catch (error) {
                    failures.push(String(error));
                    await route.continue().catch(() => undefined);
                }
            });

            await rowAction(page, SLUG, 'refresh');
            await expect.poll(() => refused, {message: 'the pair’s refresh never asked its own rates', timeout: 10_000}).toBeGreaterThan(0);
            await expect(errorToasts, 'the refused refresh must say so in an error toast — the page only logged it').toHaveCount(1, {timeout: 10_000});
            const sentence = catalogueSentence(await pageLanguage(page), BULK_TOO_MANY_DAYS_KEY, {max: REFUSED_DAYS.max_item_days});
            await expect(errorToasts, 'the catalogue’s sentence, with the budget of the refusal').toHaveText(sentence);
            expect(failures, 'the refusal reached the page').toEqual([]);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('a plain 500 on the same request shows no error toast: any other failure stays as it was', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const failures: string[] = [];
        let answer: 'refusal' | 'server error' = 'refusal';
        let serverErrors = 0;
        try {
            // The load is refused for its days; once `answer` turns, every conversion request fails with a plain 500.
            await page.route(FX_CONVERT, async (route) => {
                try {
                    if (answer === 'refusal') {
                        await route.fulfill({status: 422, json: {detail: REFUSED_DAYS_DETAIL}});
                        return;
                    }
                    await route.fulfill({status: 500, json: {detail: 'synthetic: the conversions are unavailable (X-R58)'}});
                    serverErrors += 1;
                } catch (error) {
                    failures.push(String(error));
                    await route.continue().catch(() => undefined);
                }
            });
            await goToFxPage(page, range);
            const fxPage = page.getByTestId('fx-page');
            const errorToasts = page.getByTestId('toast-error');

            // Presence first: the refused load's toast proves that the page's error toasts are observed here, so the absence
            // at the end is the page's doing, not a slot nobody reads. Dismissed, it leaves none.
            await expect(errorToasts, 'the refused load must say so in an error toast — the list only logged it').toHaveCount(1, {timeout: 10_000});
            await errorToasts.getByTestId('toast-dismiss').click();
            await expect(errorToasts, 'the toast is dismissed: no error toast is left').toHaveCount(0);

            // The same request now fails with a plain 500: the page's refresh asks every pair again.
            answer = 'server error';
            const refreshAll = page.getByTestId('fx-refresh-all-button');
            await expect(refreshAll).toBeEnabled();
            await refreshAll.click();
            await expect.poll(() => serverErrors, {message: 'the refresh never asked the rates again', timeout: 10_000}).toBeGreaterThan(0);
            // The refresh is over: whatever the page does with the failure, it has done — an error toast lasts 15 s.
            await expect(refreshAll, 'the refresh is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            await waitForSettled(fxPage, 20_000);
            expect(failures, 'the refusal and the failure reached the page').toEqual([]);

            await expect(errorToasts, 'a plain 500 is no refusal: the page logs it and shows no toast, as before X-R58').toHaveCount(0);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });
});

/**
 * FX list — a card draws its saved comparisons (lot Y-41).
 *
 * The FX list asked no asset prices, so a card with a comparison with an asset drew nothing of it, while the settings
 * offered it. Since Y-41 the list loads the daily series of the assets the cards compare, and only those: one request
 * for all of them, none when no card has such a comparison. The comparison with another FX pair, which the list always
 * drew, keeps drawing. A card publishes how many overlay lines it draws (`data-overlay-count`).
 *
 * The comparison is seeded in this browser's storage (`seedChartComparisons`): nothing shared is written. Asset prices
 * are the seeded mock data's.
 *
 * Red today: the card draws the pair and not the asset (1 line, not 2), and no asset prices are asked.
 */
test.describe('FX list — a card draws its saved comparisons (Y-41)', () => {
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    /** The requests for asset prices the page makes, by their items: the assets each asked. */
    function recordAssetPriceRequests(page: import('@playwright/test').Page): number[][] {
        const asked: number[][] = [];
        page.on('request', (request) => {
            if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return;
            const items = (request.postDataJSON() as Array<{asset_id?: number}> | null) ?? [];
            asked.push(items.map((item) => Number(item.asset_id)));
        });
        return asked;
    }

    test('a card with a comparison with an asset and one with a pair draws both, and the list asks that asset’s prices once', async ({page}) => {
        const asked = recordAssetPriceRequests(page);
        await goToFxPage(page);
        const appleId = await assetIdByName(page, 'Apple Inc.');
        await seedChartComparisons(page, [['EUR-USD', [assetComparison('e2e-y41-asset', appleId), pairComparison('e2e-y41-pair', 'EUR-GBP')]]]);
        asked.length = 0;

        await goToFxPage(page);

        const card = page.getByTestId('fx-card-EUR-USD');
        await expect(card, 'both comparisons are drawn: the asset and the pair').toHaveAttribute('data-overlay-count', '2', {timeout: 15_000});
        expect(asked, 'one request, for the one asset compared').toEqual([[appleId]]);
    });

    test('guard: with no comparison with an asset the list asks no asset prices, and the pair comparison draws as before', async ({page}) => {
        const asked = recordAssetPriceRequests(page);
        await goToFxPage(page);
        await seedChartComparisons(page, [['EUR-USD', [pairComparison('e2e-y41-pair', 'EUR-GBP')]]]);
        asked.length = 0;

        await goToFxPage(page);

        await expect(page.getByTestId('fx-card-EUR-USD')).toHaveAttribute('data-overlay-count', '1', {timeout: 15_000});
        expect(asked, 'no asset price is asked').toEqual([]);
    });
});

/**
 * FX list — the grid toolbar: an icon for the absolute view, a tooltip on settings, sync all and refresh all (Y5-F1).
 *
 * The first button of the cards' view group (`fx-global-view-absolute`) draws the price-line icon and no text, with an
 * `aria-label`; the percentage one stays text. The three action buttons are each wrapped in the shared Tooltip (it opens
 * after a rest of 500 ms of plain hover). Nothing here asserts the translated text: the tooltip must be non-empty and
 * not a raw catalogue key. Sync all and refresh all are never clicked; nothing shared is written.
 *
 * Red today: the Absolute button is text, and the three buttons carry no tooltip wrapper.
 */
test.describe('FX list — the grid toolbar: the Absolute icon and the action tooltips (Y5-F1)', () => {
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    /** A key looks like `area.sub.name`: dotted, no space. A rendered sentence is never one. */
    const looksLikeRawKey = (text: string) => /^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)+$/.test(text.trim());

    test('in the card view the Absolute button is an icon with an aria-label and no text, and still turns the view', async ({page}) => {
        await goToFxPage(page);
        await page.getByTestId('view-mode-grid').click();
        await waitForSettled(page.getByTestId('fx-page'), 20_000);

        const group = page.getByTestId('fx-global-view');
        const absolute = page.getByTestId('fx-global-view-absolute');
        const percentage = page.getByTestId('fx-global-view-percentage');
        await expect(absolute).toBeVisible({timeout: 10_000});

        await expect(absolute.locator('svg'), 'the Absolute button draws an icon').toHaveCount(1);
        await expect(absolute, 'and no text').toHaveText(/^\s*$/);
        const label = await absolute.getAttribute('aria-label');
        expect(label?.trim() ?? '', 'an accessible name stands in for the text').not.toBe('');
        expect(looksLikeRawKey(label ?? ''), `the aria-label is a rendered name, not the key "${label}"`).toBe(false);
        await expect(percentage, 'the percentage button stays text').toHaveText('%');

        // Click % first, then Absolute: whatever the page opened on, the end states are known.
        await percentage.click();
        await expect(group).toHaveAttribute('data-view', 'percentage');
        await expect(percentage).toHaveAttribute('aria-pressed', 'true');
        await absolute.click();
        await expect(group).toHaveAttribute('data-view', 'absolute');
        await expect(absolute).toHaveAttribute('aria-pressed', 'true');
        await expect(percentage).toHaveAttribute('aria-pressed', 'false');
    });

    for (const action of [
        {name: 'settings', wrapper: 'fx-chart-settings-tooltip', button: 'fx-chart-settings-button'},
        {name: 'sync all', wrapper: 'fx-sync-all-tooltip', button: 'fx-sync-all-button'},
        {name: 'refresh all', wrapper: 'fx-refresh-tooltip', button: 'fx-refresh-all-button'},
    ]) {
        test(`the ${action.name} button is wrapped in a tooltip that opens on hover with a rendered text`, async ({page}) => {
            await goToFxPage(page);
            await page.getByTestId('view-mode-grid').click();
            await waitForSettled(page.getByTestId('fx-page'), 20_000);

            const wrapper = page.getByTestId(action.wrapper);
            const button = wrapper.getByTestId(action.button);
            await expect(button, `the ${action.name} button sits inside ${action.wrapper}`).toBeVisible({timeout: 10_000});

            // No tooltip of another control is open when this one is hovered.
            await page.mouse.move(0, 0);
            await expect(page.getByRole('tooltip')).toHaveCount(0, {timeout: 5_000});

            await button.hover();
            const tooltip = page.getByRole('tooltip');
            await expect(tooltip, 'a rest of the pointer opens the tooltip').toBeVisible({timeout: 3_000});
            const text = ((await tooltip.textContent()) ?? '').trim();
            expect(text, 'the tooltip says something').not.toBe('');
            expect(text.startsWith('sharedResource.'), `the tooltip is a rendered text, not the key "${text}"`).toBe(false);
            expect(looksLikeRawKey(text), `the tooltip is a rendered text, not the key "${text}"`).toBe(false);
        });
    }

    test('a click on the settings button still opens the chart settings, and Escape closes them', async ({page}) => {
        await goToFxPage(page);
        await page.getByTestId('view-mode-grid').click();
        await waitForSettled(page.getByTestId('fx-page'), 20_000);

        const button = page.getByTestId('fx-chart-settings-tooltip').getByTestId('fx-chart-settings-button');
        await expect(button).toBeVisible({timeout: 10_000});
        await button.hover();
        await button.click();

        const modal = page.getByTestId('chart-settings-modal');
        await expect(modal, 'the tooltip does not swallow the click').toBeVisible({timeout: 5_000});
        await expect(modal.getByTestId('chart-settings-apply')).toBeEnabled();

        await page.keyboard.press('Escape');
        await expect(modal, 'the modal closes, nothing left over it').toBeHidden({timeout: 5_000});
    });
});
