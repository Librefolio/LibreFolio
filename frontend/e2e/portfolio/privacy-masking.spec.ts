import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {findAcrossPages} from '../fixtures/paging';
import {TEST_USER} from '../fixtures/test-users';

/**
 * Privacy masking — the header toggle, end to end (privacy plan, round 2, step 9).
 *
 * The rules pinned here are the product owner's, not this file's:
 *
 * - privacy hides the NUMBER, never the currency; the sign stays outside the mask (D8);
 * - wealth is masked: values, P&L, cash, broker NAV and gain/loss, lot and position totals;
 * - a quantity the user holds is masked where it sits next to a price — positions and lots —
 *   and stays readable in transactions (D5′), and a partial lot reads `••• (NN%)` (Q8);
 * - unit prices, WAC, opening prices, percentages, counts stay readable (D5′-c, D6): masking
 *   them is a defect too, so every test carries negative controls beside its masked cells;
 * - an absent value stays `—`;
 * - a route mounted with privacy already on is masked, and the preference survives a reload.
 *
 * Every surface is toggled IN PLACE, in both directions. That is the regression this file
 * exists for (R20): components written in legacy mode froze the state they mounted with, so
 * a card turned on in place stayed in the clear, and one mounted masked stayed masked.
 *
 * Isolation: the toggle is client-side — a bare localStorage key, one per browser context
 * (`privacyStore.svelte.ts`) — and every test reads the populated mock data as TEST_USER
 * and writes nothing. The data each test needs (which broker owns a priced position, which
 * lot is partially closed, which transaction has no cash) is read through the API first,
 * never assumed from a row position. Parallel by default, like every spec.
 *
 * Digits, the placeholder and currency codes are data, not translations, so the assertions
 * below read them; nothing reads a translated label. Charts are canvases, not DOM text, and
 * their formatters are unit-tested: they are not asserted here.
 */

/**
 * `PRIVACY_PLACEHOLDER` in `src/lib/utils/privacy/maskable.ts`. Copied rather than imported:
 * that module imports the runes privacy store, which Playwright's loader cannot compile. A
 * changed placeholder is a visible product change, so this file is meant to go red with it.
 */
const PLACEHOLDER = '•••';

const DIGIT = /\d/;
/** A number as the app writes it: digits joined by the locale's group and decimal marks. */
const NUMBER = /\d(?:[\d.,'’\u00a0\u202f]*\d)?/;
/** An element whose whole text is one number — the digits of a rendered amount. */
const NUMBER_ONLY = /^\s*[+\-\u2212]?\d(?:[\d.,'’\u00a0\u202f]*\d)?\s*$/;
/** An element whose whole text is the placeholder, with the sign D8 keeps outside it. */
const MASK_ONLY = new RegExp(`^\\s*[+\\-\\u2212]?${PLACEHOLDER}\\s*$`);
/** The gain/loss share a broker card prints next to its amount, e.g. `(12.34%)`. */
const PERCENT_IN_PARENS = /^\s*\([+\-]?\d+\.\d{2}%\)\s*$/;
/** An ISO currency code, which a masked amount must still carry. */
const CURRENCY_CODE = /\b[A-Z]{3}\b/;

// ---------------------------------------------------------------------------
// What masked means
// ---------------------------------------------------------------------------

/** The masked form of a clear text: its (first) number becomes the placeholder, nothing else moves. */
function maskedForm(clear: string): string {
    return clear.replace(NUMBER, PLACEHOLDER);
}

function escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Read a cell's clear text, once it shows digits — the positive control every masked assertion is measured against. */
async function readClear(cell: Locator, what: string): Promise<string> {
    await expect(cell, `${what} must show a number while privacy is off`).toHaveText(DIGIT);
    await expect(cell).not.toContainText(PLACEHOLDER);
    return (await cell.textContent()) ?? '';
}

/** Read a cell holding one number and nothing else numeric (a quantity), so that its masked form is exact. */
async function readQuantity(cell: Locator, what: string): Promise<string> {
    const clear = await readClear(cell, what);
    expect(maskedForm(clear), `${what} must hold one number and nothing else numeric: "${clear}"`).not.toMatch(DIGIT);
    return clear;
}

/**
 * A formatted amount, in the shape the D8 formatters (`formatCurrencyAmountPlain`/`Html`)
 * write it: `[sign]number [symbol] [flag] CODE`, and after it, in `rest`, whatever the cell
 * prints beside the amount — the ROI percentage next to a P&L, for one.
 */
type Amount = {sign: string; number: string; code: string; rest: string};

const AMOUNT_SHAPE = /^\s*([+\-\u2212]?)(\d(?:[\d.,'’\u00a0\u202f]*\d)?)(?:\s+[^\s\d]+)*?\s+([A-Z]{3})((?:\s+\S+)*)\s*$/;

async function readAmount(cell: Locator, what: string, {alone = true}: {alone?: boolean} = {}): Promise<Amount> {
    const text = await readClear(cell, what);
    const match = AMOUNT_SHAPE.exec(text);
    if (!match) throw new Error(`${what} is not a formatted amount: "${text}"`);
    const [, sign, number, code, rest] = match;
    if (alone) expect(rest.trim(), `${what} must hold one amount and nothing else: "${text}"`).toBe('');
    return {sign, number, code, rest: rest.trim()};
}

/**
 * The amount as a pattern: its own number, or the placeholder in its place. The sign, the
 * currency code and whatever follows the amount must all be there. The currency's symbol and
 * flag may or may not be: they come from the currency catalogue, and a table cell drawn before
 * the catalogue lands shows the bare code until its next render — which the toggle is. That
 * staleness is not privacy, so it is tolerated here rather than tested.
 *
 * `tweened` is for amounts drawn through `TweenedValue` (the KPI cards): they animate towards
 * their value after the report lands, so the clear text read may be a frame of the animation,
 * and the first frame (`0.00`) has no sign yet. D8's sign is pinned on the untweened cells.
 */
function amountPattern(amount: Amount, {masked, tweened = false}: {masked: boolean; tweened?: boolean}): RegExp {
    const sign = tweened ? '[+\\-\\u2212]?' : escapeRegExp(amount.sign);
    const number = masked ? PLACEHOLDER : tweened ? NUMBER.source : escapeRegExp(amount.number);
    const rest = amount.rest ? `\\s+${amount.rest.split(/\s+/).map(escapeRegExp).join('\\s+')}` : '';
    return new RegExp(`^\\s*${sign}${number}(?:\\s+[^\\s\\d]+)*?\\s+${amount.code}${rest}\\s*$`);
}

/** A masked amount seen on arrival, without a clear text to compare with: placeholder, no digit, currency kept. */
async function expectMaskedOnArrival(cell: Locator, what: string): Promise<void> {
    await expect(cell, `${what} must mount masked`).toContainText(PLACEHOLDER);
    await expect(cell, `${what} must not show a digit`).not.toHaveText(DIGIT);
    await expect(cell, `${what} must keep its currency`).toHaveText(CURRENCY_CODE);
}

/**
 * The amounts inside a container that has no per-amount test ids (a broker card, a row of
 * cash chips). The D8 formatter renders each amount's digits in an element of their own, so
 * the elements whose whole text is a number are exactly the amounts — the currency, flag and
 * code sit in their siblings, and a percentage or a count carries a unit that excludes it.
 */
async function readClearAmounts(scope: Locator, what: string): Promise<string[]> {
    const numbers = scope.getByText(NUMBER_ONLY);
    await expect(numbers.first(), `${what} must show amounts while privacy is off`).toBeVisible();
    await expect(scope.getByText(MASK_ONLY)).toHaveCount(0);
    return numbers.allTextContents();
}

/** Every amount masked, in order, with its own sign — and not one number left. */
async function expectAmountsMasked(scope: Locator, clear: string[], what: string): Promise<void> {
    await expect(scope.getByText(MASK_ONLY), `${what}: every amount masked, sign kept`).toHaveText(clear.map(maskedForm));
    await expect(scope.getByText(NUMBER_ONLY), `${what}: no amount left in the clear`).toHaveCount(0);
}

async function expectAmountsClear(scope: Locator, clear: string[], what: string): Promise<void> {
    await expect(scope.getByText(NUMBER_ONLY), `${what}: every amount back in the clear`).toHaveText(clear);
    await expect(scope.getByText(MASK_ONLY)).toHaveCount(0);
}

// ---------------------------------------------------------------------------
// The toggle
// ---------------------------------------------------------------------------

/**
 * Flip privacy from the header, asserting the state before and after.
 *
 * The header slides away on scroll (`Header.svelte`), and pages scroll themselves — the lots
 * panel scrolls into view once it has drawn. A focused header control pins the header in
 * place (`handleFocusIn`), so the click cannot land where the toggle *was*.
 */
async function flipPrivacy(page: Page, on: boolean): Promise<void> {
    const toggle = page.getByTestId('privacy-toggle');
    await expect(toggle, 'privacy must start from the opposite state').toHaveAttribute('aria-pressed', String(!on));
    await toggle.focus();
    await expect(page.getByTestId('app-header')).toHaveAttribute('data-scroll-state', 'pinned');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-pressed', String(on));
}

/** Follow a sidebar link, through the burger menu where the layout has one. */
async function followNav(page: Page, navTestId: string, url: RegExp): Promise<void> {
    const burger = page.getByTestId('mobile-menu-toggle');
    // Layout, not timing: the burger is rendered below the lg breakpoint only, and the page
    // has hydrated by the time this runs.
    if (await burger.isVisible()) {
        await burger.focus();
        await expect(page.getByTestId('app-header')).toHaveAttribute('data-scroll-state', 'pinned');
        await burger.click();
        await expect(page.getByTestId('app-header')).toHaveAttribute('data-sidebar-open', 'true');
    }
    await page.getByTestId(navTestId).click();
    await expect(page).toHaveURL(url);
}

// ---------------------------------------------------------------------------
// Pages and tables
// ---------------------------------------------------------------------------

/** The report runs FIFO at runtime: under load it takes longer than a default assertion. */
const REPORT_TIMEOUT = 30_000;

async function openDashboard(page: Page, route: string): Promise<void> {
    await navigateTo(page, route);
    await expect(page.getByTestId('dashboard-page')).toHaveAttribute('data-busy', 'false', {timeout: REPORT_TIMEOUT});
}

async function openBrokerDetail(page: Page, route: string): Promise<void> {
    await navigateTo(page, route);
    await expect(page.getByTestId('broker-detail-page')).toBeVisible();
    // Disabled while the broker summary or its report is loading — the page's busy state.
    await expect(page.getByTestId('broker-refresh')).toBeEnabled({timeout: REPORT_TIMEOUT});
}

async function openBrokers(page: Page): Promise<void> {
    await navigateTo(page, '/brokers');
    await expect(page.getByTestId('brokers-page')).toHaveAttribute('data-busy', 'false', {timeout: REPORT_TIMEOUT});
}

/** The positions panel in its holdings × table view, loaded. Both controls are setters, not toggles. */
async function holdingsTable(scope: Locator): Promise<Locator> {
    const panel = scope.getByTestId('positions-panel');
    await expect(panel).toHaveAttribute('data-busy', 'false', {timeout: REPORT_TIMEOUT});
    await scope.getByTestId('positions-toggle-holdings').click();
    await scope.getByTestId('positions-toggle-table').click();
    const table = scope.getByTestId('exposure-table');
    await expect(table.getByTestId('dt-header-value')).toBeVisible();
    return table;
}

function rowIn(table: Locator, rowId: string): Locator {
    return table.locator(`tbody tr[data-row-id="${rowId}"]`);
}

/** Walk the table's pages until the row is on screen; fail naming it if no page has it. */
async function showRow(table: Locator, rowId: string, what: string): Promise<void> {
    const found = await findAcrossPages(table, async () => (await rowIn(table, rowId).count()) > 0);
    expect(found, `${what} (row ${rowId}) is in no page of the table — check populate_mock_data.py`).not.toBeNull();
    await expect(rowIn(table, rowId)).toBeVisible();
}

/**
 * The cell of a row under a column. The index is read from the column's own header, not
 * guessed: it counts the selection column and whichever columns this context shows. Read it
 * after revealing columns, since revealing one shifts the rest.
 */
async function cellIn(table: Locator, rowId: string, columnId: string): Promise<Locator> {
    const header = table.getByTestId(`dt-header-${columnId}`);
    await expect(header, `column "${columnId}" must be on screen`).toBeAttached();
    const index = await header.evaluate((element) => (element as HTMLTableCellElement).cellIndex);
    return rowIn(table, rowId).locator(':scope > td').nth(index);
}

/**
 * Show columns a table hides by default (unit prices are among them) through its own column
 * menu — a fresh context always starts from the defaults, so the header's absence is the
 * state to change, and its presence the proof it changed.
 */
async function revealColumns(page: Page, menuScope: Locator, table: Locator, columnIds: string[]): Promise<void> {
    const hidden: string[] = [];
    for (const columnId of columnIds) {
        if ((await table.getByTestId(`dt-header-${columnId}`).count()) === 0) hidden.push(columnId);
    }
    if (hidden.length === 0) return;
    await menuScope.getByTestId('column-visibility-toggle').click();
    const menu = page.getByTestId('column-visibility-dropdown');
    await expect(menu).toBeVisible();
    for (const columnId of hidden) {
        await menu.getByTestId(`column-visibility-item-${columnId}`).click();
        await expect(table.getByTestId(`dt-header-${columnId}`)).toBeAttached();
    }
    // The menu closes on a click outside it, which lands on its own full-screen backdrop.
    // `updatePosition` keeps it at least 8px from every edge, so the corner is always outside.
    await page.mouse.click(2, 2);
    await expect(menu).toBeHidden();
}

// ---------------------------------------------------------------------------
// The data, read through the API rather than assumed
// ---------------------------------------------------------------------------

type Money = {code: string; amount: string | number};
type BrokerListItem = {id: number; name: string; user_role?: string | null; user_share_percentage?: string | number | null};
type BrokerHolding = {asset_id: number; asset_name: string; quantity: string | number; current_price?: string | number | null};
type BrokerSummary = {holdings: BrokerHolding[]};
type LotSummary = {lot_id: number; states: string[]; open_quantity: string | number; original_quantity: string | number};
type TxRead = {id: number; asset_id: number | null; type: string; quantity: string | number; cash: Money | null};
type Position = {brokerId: number; brokerName: string; assetId: number; assetName: string};

async function getJson<T>(page: Page, url: string): Promise<T> {
    const response = await page.request.get(url);
    expect(response.ok(), `GET ${url} → HTTP ${response.status()}`).toBe(true);
    return (await response.json()) as T;
}

async function postJson<T>(page: Page, url: string, data: unknown): Promise<T> {
    const response = await page.request.post(url, {data});
    expect(response.ok(), `POST ${url} → HTTP ${response.status()}`).toBe(true);
    return (await response.json()) as T;
}

/** The brokers the dashboard counts as the user's own: OWNER with a share above zero (`getOwnedBrokers`). */
async function ownedBrokers(page: Page): Promise<BrokerListItem[]> {
    const list = await getJson<{items: BrokerListItem[]}>(page, '/api/v1/brokers');
    return list.items.filter((broker) => broker.user_role === 'OWNER' && (broker.user_share_percentage == null || Number(broker.user_share_percentage) > 0));
}

async function pricedPositions(page: Page): Promise<Position[]> {
    const positions: Position[] = [];
    for (const broker of await ownedBrokers(page)) {
        const summary = await getJson<BrokerSummary>(page, `/api/v1/brokers/${broker.id}/summary`);
        for (const holding of summary.holdings) {
            if (Number(holding.quantity) > 0 && holding.current_price != null) {
                positions.push({brokerId: broker.id, brokerName: broker.name, assetId: holding.asset_id, assetName: holding.asset_name});
            }
        }
    }
    return positions;
}

/** A priced open position in a broker TEST_USER owns. */
async function pickPosition(page: Page): Promise<Position> {
    const [position] = await pricedPositions(page);
    if (!position) throw new Error('TEST_USER owns no broker with a priced open position — check populate_mock_data.py');
    return position;
}

/** A priced position whose FIFO lots, scoped to its broker as the broker page scopes them, include a partially closed one. */
async function pickPartialLot(page: Page): Promise<{position: Position; lot: LotSummary}> {
    for (const position of await pricedPositions(page)) {
        const analysis = await postJson<{lots: LotSummary[]}>(page, '/api/v1/portfolio/lots/analysis', {
            asset_id: position.assetId,
            broker_ids: [position.brokerId],
            requested_analyses: ['LOT_SUMMARY'],
        });
        const lot = analysis.lots.find((candidate) => candidate.states.includes('PARTIALLY_CLOSED') && Number(candidate.original_quantity) > 0);
        if (lot) return {position, lot};
    }
    throw new Error('No partially closed lot in any priced position TEST_USER owns — check populate_mock_data.py');
}

/** A BUY (cash out, so its amount is signed) and a transaction with no cash at all, both on one position. */
async function pickTransactions(page: Page, position: Position): Promise<{buy: TxRead; withoutCash: TxRead}> {
    const rows = await getJson<TxRead[]>(page, `/api/v1/transactions?broker_id=${position.brokerId}`);
    const onPosition = rows.filter((row) => row.asset_id === position.assetId);
    const buy = onPosition.find((row) => row.type === 'BUY' && Number(row.quantity) > 0 && row.cash != null && Number(row.cash.amount) < 0);
    const withoutCash = onPosition.find((row) => row.cash == null && Number(row.quantity) !== 0);
    if (!buy || !withoutCash) throw new Error(`${position.assetName} @ ${position.brokerName} needs a BUY and a cash-less transaction — check populate_mock_data.py`);
    return {buy, withoutCash};
}

// ---------------------------------------------------------------------------
// The tests
// ---------------------------------------------------------------------------

test.describe('Privacy masking', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('dashboard summary: net worth, P&L and cash hide their number in place and come back; returns stay readable', async ({page}) => {
        await openDashboard(page, '/dashboard');
        const netWorth = page.getByTestId('kpi-net-worth').getByTestId('kpi-value');
        const periodPnl = page.getByTestId('kpi-period-pnl').getByTestId('kpi-value');
        const totalPnl = page.getByTestId('kpi-total-pnl-delta');
        const cash = page.getByTestId('dashboard-cash-balances');
        const returns = page.getByTestId('kpi-returns');

        const netWorthClear = await readAmount(netWorth, 'net worth');
        const periodPnlClear = await readAmount(periodPnl, 'period P&L');
        // The total P&L prints its ROI percentage after the amount.
        const totalPnlClear = await readAmount(totalPnl, 'total P&L', {alone: false});
        const cashClear = await readClearAmounts(cash, 'cash balances');
        await readClear(returns, 'returns');

        await flipPrivacy(page, true);
        await expect(netWorth).toHaveText(amountPattern(netWorthClear, {masked: true, tweened: true}));
        await expect(periodPnl).toHaveText(amountPattern(periodPnlClear, {masked: true, tweened: true}));
        await expect(totalPnl, 'the amount hides, the ROI percentage beside it does not (D6)').toHaveText(amountPattern(totalPnlClear, {masked: true, tweened: true}));
        await expectAmountsMasked(cash, cashClear, 'cash balances');
        await expect(returns, 'a card of percentages only: nothing in it may be masked').not.toContainText(PLACEHOLDER);
        await expect(returns).toHaveText(DIGIT);

        await flipPrivacy(page, false);
        await expect(netWorth).toHaveText(amountPattern(netWorthClear, {masked: false, tweened: true}));
        await expect(periodPnl).toHaveText(amountPattern(periodPnlClear, {masked: false, tweened: true}));
        await expect(totalPnl).toHaveText(amountPattern(totalPnlClear, {masked: false, tweened: true}));
        await expectAmountsClear(cash, cashClear, 'cash balances');
    });

    test('dashboard positions: value, P&L and held quantity hide in place; price, WAC and weight stay readable', async ({page}) => {
        const position = await pickPosition(page);
        const rowId = `${position.assetId}-${position.brokerId}`;
        await openDashboard(page, '/dashboard?tab=posizioni');
        const tab = page.getByTestId('dashboard-positions-tab');
        const table = await holdingsTable(tab);
        await revealColumns(page, tab.getByTestId('positions-column-visibility-toggle'), table, ['price', 'pmc']);
        await showRow(table, rowId, `${position.assetName} @ ${position.brokerName}`);

        const valueCell = await cellIn(table, rowId, 'value');
        const pnlCell = await cellIn(table, rowId, 'pnl');
        const quantityCell = await cellIn(table, rowId, 'quantity');
        const priceCell = await cellIn(table, rowId, 'price');
        const pmcCell = await cellIn(table, rowId, 'pmc');
        const weightCell = await cellIn(table, rowId, 'weight');
        const pnlPercentCell = await cellIn(table, rowId, 'pnl-percent');

        const value = await readAmount(valueCell, 'position value');
        const pnl = await readAmount(pnlCell, 'position P&L');
        const quantity = await readQuantity(quantityCell, 'held quantity');
        const price = await readAmount(priceCell, 'unit price');
        const pmc = await readAmount(pmcCell, 'WAC');
        const weight = await readClear(weightCell, 'weight');
        const pnlPercent = await readClear(pnlPercentCell, 'P&L %');

        await flipPrivacy(page, true);
        await expect(valueCell, 'the value hides, its currency stays').toHaveText(amountPattern(value, {masked: true}));
        await expect(pnlCell, 'the P&L hides, its sign and currency stay (D8)').toHaveText(amountPattern(pnl, {masked: true}));
        await expect(quantityCell, 'a held quantity beside a price is masked (D5′)').toHaveText(maskedForm(quantity));
        await expect(priceCell, 'a market price is not wealth').toHaveText(amountPattern(price, {masked: false}));
        await expect(pmcCell, 'the WAC per unit is not wealth (D5′-c)').toHaveText(amountPattern(pmc, {masked: false}));
        await expect(weightCell, 'a percentage stays readable (D6)').toHaveText(weight);
        await expect(pnlPercentCell).toHaveText(pnlPercent);

        await flipPrivacy(page, false);
        await expect(valueCell).toHaveText(amountPattern(value, {masked: false}));
        await expect(pnlCell).toHaveText(amountPattern(pnl, {masked: false}));
        await expect(quantityCell).toHaveText(quantity);
        await expect(priceCell).toHaveText(amountPattern(price, {masked: false}));
        await expect(pmcCell).toHaveText(amountPattern(pmc, {masked: false}));
        await expect(weightCell).toHaveText(weight);
        await expect(pnlPercentCell).toHaveText(pnlPercent);
    });

    test("brokers list (R20): a card's NAV, gain/loss and cash follow the toggle in place, both ways", async ({page}) => {
        const position = await pickPosition(page);
        await openBrokers(page);
        const card = page.getByTestId(`broker-card-${position.brokerId}`);
        const clear = await readClearAmounts(card, `${position.brokerName} card`);
        expect(clear.length, 'the card prints at least its NAV and its gain/loss').toBeGreaterThanOrEqual(2);
        const share = card.getByText(PERCENT_IN_PARENS);
        await expect(share).toHaveCount(1);
        const shareClear = await readClear(share, 'gain/loss percentage');

        await flipPrivacy(page, true);
        await expectAmountsMasked(card, clear, `${position.brokerName} card`);
        await expect(share, 'the percentage beside the masked gain/loss stays readable').toHaveText(shareClear);

        await flipPrivacy(page, false);
        await expectAmountsClear(card, clear, `${position.brokerName} card`);
        await expect(share).toHaveText(shareClear);
    });

    test('broker detail (R20): net worth and cash balances follow the toggle in place, both ways; the share stays', async ({page}) => {
        const position = await pickPosition(page);
        await openBrokerDetail(page, `/brokers/${position.brokerId}`);
        const netWorth = page.getByTestId('kpi-net-worth').getByTestId('kpi-value');
        const cash = page.getByTestId('broker-cash-balances');
        const quota = page.getByTestId('broker-quota-badge');

        const netWorthClear = await readAmount(netWorth, 'broker net worth');
        // The cash chips are one of the page's two legacy-parent amounts (R20). The other, the
        // Info tab's total value, never renders: no backend code fills `total_value_base_currency`.
        const cashClear = await readClearAmounts(cash, 'broker cash balances');
        const quotaClear = await readClear(quota, 'ownership share');

        await flipPrivacy(page, true);
        await expect(netWorth).toHaveText(amountPattern(netWorthClear, {masked: true, tweened: true}));
        await expectAmountsMasked(cash, cashClear, 'broker cash balances');
        await expect(quota, 'the ownership share is a percentage and stays readable').toHaveText(quotaClear);

        await flipPrivacy(page, false);
        await expect(netWorth).toHaveText(amountPattern(netWorthClear, {masked: false, tweened: true}));
        await expectAmountsClear(cash, cashClear, 'broker cash balances');
        await expect(quota).toHaveText(quotaClear);
    });

    test('broker positions and lots: quantities and totals hide in place, prices stay, a partial lot reads ••• (NN%)', async ({page}) => {
        const {position, lot} = await pickPartialLot(page);
        const rowId = `${position.assetId}-${position.brokerId}`;
        const lotRow = String(lot.lot_id);
        await openBrokerDetail(page, `/brokers/${position.brokerId}?tab=posizioni`);
        const holdings = page.getByTestId('broker-holdings');
        const exposure = await holdingsTable(holdings);
        await revealColumns(page, holdings.getByTestId('positions-column-visibility-toggle'), exposure, ['price', 'pmc']);
        await showRow(exposure, rowId, `${position.assetName} @ ${position.brokerName}`);

        // Open the lots the way a user does: the position's row actions.
        await rowIn(exposure, rowId).getByTestId(`row-actions-${rowId}`).click();
        await page.getByTestId('context-menu-action-analyze-lots').click();
        const lots = page.getByTestId('unified-lots-table');
        await expect(lots.getByTestId('dt-header-open-quantity')).toBeVisible({timeout: REPORT_TIMEOUT});
        await showRow(lots, lotRow, `partially closed lot ${lotRow}`);
        await revealColumns(page, lots, lots, ['opening-price']);

        const hiddenAmounts = new Map<string, Locator>([
            ['position value', await cellIn(exposure, rowId, 'value')],
            ['lot value', await cellIn(lots, lotRow, 'current-value')],
            ['lot P&L', await cellIn(lots, lotRow, 'total-pnl')],
            ['lots total value', lots.getByTestId('dt-footer-current-value')],
            ['lots total P&L', lots.getByTestId('dt-footer-total-pnl')],
        ]);
        const hiddenQuantities = new Map<string, Locator>([
            ['position quantity', await cellIn(exposure, rowId, 'quantity')],
            ['lots total quantity', lots.getByTestId('dt-footer-open-quantity')],
        ]);
        const shownAmounts = new Map<string, Locator>([
            ['position price', await cellIn(exposure, rowId, 'price')],
            ['position WAC', await cellIn(exposure, rowId, 'pmc')],
            ['lot opening price', await cellIn(lots, lotRow, 'opening-price')],
            ['lots average opening price', lots.getByTestId('dt-footer-opening-price')],
        ]);
        const shownPercentages = new Map<string, Locator>([
            ['lot return', await cellIn(lots, lotRow, 'total-return')],
            ['lots total return', lots.getByTestId('dt-footer-total-return')],
        ]);
        const partial = await cellIn(lots, lotRow, 'open-quantity');

        const clearAmount = new Map<string, Amount>();
        for (const [what, cell] of [...hiddenAmounts, ...shownAmounts]) clearAmount.set(what, await readAmount(cell, what));
        const clearText = new Map<string, string>();
        for (const [what, cell] of hiddenQuantities) clearText.set(what, await readQuantity(cell, what));
        for (const [what, cell] of shownPercentages) clearText.set(what, await readClear(cell, what));
        // Clear, a partially closed lot reads `open / original`.
        await expect(partial, 'the partial lot shows open / original while privacy is off').toHaveText(/^\s*\S*\d\S*\s+\/\s+\S*\d\S*\s*$/);
        const partialClear = (await partial.textContent()) ?? '';
        // Masked, it keeps its reading key as the open share, which discloses no quantity (Q8).
        const openShare = ((Number(lot.open_quantity) / Number(lot.original_quantity)) * 100).toFixed(0);

        await flipPrivacy(page, true);
        for (const [what, cell] of hiddenAmounts) await expect(cell, `${what} hides, sign and currency stay`).toHaveText(amountPattern(clearAmount.get(what)!, {masked: true}));
        for (const [what, cell] of hiddenQuantities) await expect(cell, `${what} is a held quantity and hides (D5′)`).toHaveText(maskedForm(clearText.get(what)!));
        for (const [what, cell] of shownAmounts) await expect(cell, `${what} is a unit price and stays readable (D5′-c)`).toHaveText(amountPattern(clearAmount.get(what)!, {masked: false}));
        for (const [what, cell] of shownPercentages) await expect(cell, `${what} is a percentage and stays readable (D6)`).toHaveText(clearText.get(what)!);
        await expect(partial, 'a partial lot reads ••• (NN%) under privacy').toHaveText(`${PLACEHOLDER} (${openShare}%)`);

        await flipPrivacy(page, false);
        for (const [what, cell] of [...hiddenAmounts, ...shownAmounts]) await expect(cell, `${what} back in the clear`).toHaveText(amountPattern(clearAmount.get(what)!, {masked: false}));
        for (const [what, cell] of [...hiddenQuantities, ...shownPercentages]) await expect(cell, `${what} back in the clear`).toHaveText(clearText.get(what)!);
        await expect(partial).toHaveText(partialClear);
    });

    test('lot custody modal mounts masked under privacy: quantities and P&L hide, return and lot id stay', async ({page}) => {
        const {position, lot} = await pickPartialLot(page);
        const lotRow = String(lot.lot_id);
        // Deep link to the open lots panel: `?asset=` is its bookmarkable state.
        await openBrokerDetail(page, `/brokers/${position.brokerId}?tab=posizioni&asset=${position.assetId}`);
        const lots = page.getByTestId('unified-lots-table');
        await expect(lots.getByTestId('dt-header-open-quantity')).toBeVisible({timeout: REPORT_TIMEOUT});
        await showRow(lots, lotRow, `partially closed lot ${lotRow}`);

        const modal = page.getByTestId('lot-custody-modal');
        const totalPnl = page.getByTestId('lot-custody-modal-total-pnl');
        const totalReturn = page.getByTestId('lot-custody-modal-total-return');
        const lotId = page.getByTestId('lot-custody-modal-lot-id');
        const custodyRows = modal.locator('[data-testid^="lot-custody-modal-custody-summary-row-"]');

        // The modal covers the header, so it cannot be toggled in place: it is opened once
        // with privacy off and once with privacy on, and must render each state at mount.
        await page.getByTestId(`unified-lots-custody-${lotRow}`).click();
        await expect(modal).toBeVisible();
        const totalPnlClear = await readAmount(totalPnl, 'lot total P&L');
        const totalReturnClear = await readClear(totalReturn, 'lot total return');
        const lotIdClear = await readClear(lotId, 'lot id');
        await expect(custodyRows.first(), 'a partial lot is still held somewhere').toBeVisible();
        const custodyClear = await custodyRows.allTextContents();
        for (const text of custodyClear) {
            expect(maskedForm(text), `a custody row holds one number, its quantity: "${text}"`).not.toMatch(DIGIT);
        }
        await page.getByTestId('lot-custody-modal-close').click();
        await expect(modal).toBeHidden();

        await flipPrivacy(page, true);
        await page.getByTestId(`unified-lots-custody-${lotRow}`).click();
        await expect(modal).toBeVisible();
        await expect(totalPnl, 'the lot P&L is masked with its sign and currency').toHaveText(amountPattern(totalPnlClear, {masked: true}));
        await expect(custodyRows, 'every custody quantity is masked (D5′)').toHaveText(custodyClear.map(maskedForm));
        await expect(totalReturn, 'the lot return is a percentage and stays readable').toHaveText(totalReturnClear);
        await expect(lotId, 'the lot id is not wealth').toHaveText(lotIdClear);
        await page.getByTestId('lot-custody-modal-close').click();
        await expect(modal).toBeHidden();
    });

    test('transactions: amounts hide with currency and sign in place; quantities, absent cash and the count stay', async ({page}) => {
        const position = await pickPosition(page);
        const {buy, withoutCash} = await pickTransactions(page, position);
        // The position's own transactions, deep-linked the way broker detail links them.
        await navigateTo(page, `/transactions?broker_id=${position.brokerId}&asset_id=${position.assetId}`);
        await expect(page.getByTestId('transactions-page')).toHaveAttribute('data-busy', 'false', {timeout: REPORT_TIMEOUT});
        const table = page.getByTestId('tx-table');
        await showRow(table, `tx-${buy.id}`, `BUY ${buy.id}`);
        await expect(rowIn(table, `tx-${withoutCash.id}`), 'both transactions of the position fit one page').toBeVisible();

        const buyCash = page.getByTestId(`tx-cash-cell-${buy.id}`);
        const buyQuantity = await cellIn(table, `tx-${buy.id}`, 'quantity');
        const noCash = await cellIn(table, `tx-${withoutCash.id}`, 'cash');
        const noCashQuantity = await cellIn(table, `tx-${withoutCash.id}`, 'quantity');
        const count = page.getByTestId('tx-count-badge');

        const buyCashClear = await readAmount(buyCash, 'BUY cash');
        expect(buyCashClear.sign, 'a BUY moves cash out, so its amount carries a minus sign').toMatch(/^[-\u2212]$/);
        const buyQuantityClear = await readClear(buyQuantity, 'BUY quantity');
        const noCashQuantityClear = await readClear(noCashQuantity, 'cash-less quantity');
        await expect(noCash, 'a transaction without cash shows an em dash').toHaveText('—');
        const countClear = await readClear(count, 'transaction count');

        await flipPrivacy(page, true);
        await expect(buyCash, 'the amount hides, its minus sign and currency stay (D8)').toHaveText(amountPattern(buyCashClear, {masked: true}));
        await expect(buyQuantity, 'a quantity in a transaction stays readable (D5′)').toHaveText(buyQuantityClear);
        await expect(noCashQuantity).toHaveText(noCashQuantityClear);
        await expect(noCash, 'an absent amount is not masked').toHaveText('—');
        await expect(count, 'a count is not wealth').toHaveText(countClear);

        await flipPrivacy(page, false);
        await expect(buyCash).toHaveText(amountPattern(buyCashClear, {masked: false}));
        await expect(buyQuantity).toHaveText(buyQuantityClear);
        await expect(noCash).toHaveText('—');
    });

    test('navigation with privacy on: each route mounts masked, and transaction quantities stay readable', async ({page}) => {
        const position = await pickPosition(page);
        const {buy} = await pickTransactions(page, position);

        await openDashboard(page, '/dashboard');
        const dashboardNetWorth = page.getByTestId('kpi-net-worth').getByTestId('kpi-value');
        const dashboardNetWorthClear = await readAmount(dashboardNetWorth, 'net worth');
        await flipPrivacy(page, true);
        await expect(dashboardNetWorth).toHaveText(amountPattern(dashboardNetWorthClear, {masked: true, tweened: true}));

        await followNav(page, 'nav-brokers', /\/brokers$/);
        await expect(page.getByTestId('brokers-page')).toHaveAttribute('data-busy', 'false', {timeout: REPORT_TIMEOUT});
        await expect(page.getByTestId('privacy-toggle')).toHaveAttribute('aria-pressed', 'true');
        const card = page.getByTestId(`broker-card-${position.brokerId}`);
        await expect(card.getByText(MASK_ONLY).first(), `${position.brokerName} card must mount masked`).toBeVisible();
        await expect(card.getByText(NUMBER_ONLY), 'no card amount in the clear').toHaveCount(0);

        await card.click();
        await expect(page).toHaveURL(new RegExp(`/brokers/${position.brokerId}(?:[?#]|$)`));
        await expect(page.getByTestId('broker-refresh')).toBeEnabled({timeout: REPORT_TIMEOUT});
        await expectMaskedOnArrival(page.getByTestId('kpi-net-worth').getByTestId('kpi-value'), 'broker net worth');
        const brokerCash = page.getByTestId('broker-cash-balances');
        await expect(brokerCash.getByText(MASK_ONLY).first(), 'broker cash must mount masked').toBeVisible();
        await expect(brokerCash.getByText(NUMBER_ONLY)).toHaveCount(0);

        await followNav(page, 'nav-transactions', /\/transactions(?:[?#]|$)/);
        await expect(page.getByTestId('transactions-page')).toHaveAttribute('data-busy', 'false', {timeout: REPORT_TIMEOUT});
        const table = page.getByTestId('tx-table');
        await showRow(table, `tx-${buy.id}`, `BUY ${buy.id}`);
        await expectMaskedOnArrival(page.getByTestId(`tx-cash-cell-${buy.id}`), 'BUY cash');
        const quantity = await cellIn(table, `tx-${buy.id}`, 'quantity');
        await expect(quantity, 'a transaction quantity stays readable under privacy (D5′)').toHaveText(DIGIT);
        await expect(quantity).not.toContainText(PLACEHOLDER);
    });

    test('reload with privacy on: the preference survives, and a card mounted masked turns clear in place (R20)', async ({page}) => {
        const position = await pickPosition(page);
        await openBrokers(page);
        const card = page.getByTestId(`broker-card-${position.brokerId}`);
        const clear = await readClearAmounts(card, `${position.brokerName} card`);
        await flipPrivacy(page, true);
        await expectAmountsMasked(card, clear, `${position.brokerName} card`);

        await page.reload();
        await page.waitForSelector('html[data-i18n-ready="true"]', {timeout: 15_000});
        await expect(page.getByTestId('brokers-page')).toHaveAttribute('data-busy', 'false', {timeout: REPORT_TIMEOUT});
        await expect(page.getByTestId('privacy-toggle'), 'the preference is persisted for this browser').toHaveAttribute('aria-pressed', 'true');
        // Re-fetched, so counted rather than compared: the same amounts, all masked.
        await expect(card.getByText(MASK_ONLY), 'the card mounts masked after the reload').toHaveCount(clear.length);
        await expect(card.getByText(NUMBER_ONLY)).toHaveCount(0);

        await flipPrivacy(page, false);
        await expect(card.getByText(NUMBER_ONLY), 'a card mounted masked comes back in the clear in place').toHaveCount(clear.length);
        await expect(card.getByText(MASK_ONLY)).toHaveCount(0);
    });
});
