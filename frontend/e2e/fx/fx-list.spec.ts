/**
 * FX List Page — E2E Tests
 *
 * Tests the FX list page: card rendering, filtering, navigation, and basic actions.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test, type Locator} from '../fixtures/playwright';
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
