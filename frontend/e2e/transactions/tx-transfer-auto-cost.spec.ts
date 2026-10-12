/**
 * An asset TRANSFER saved from the app in *Auto* keeps the cost of the units it moves — CHANGELOG 1.2.
 *
 * «Moving a whole position to another broker with the cost basis in *Auto* gave the receiving broker a cost of 0, so
 * the shares' whole value counted as gain […] The receiving side now takes the sending broker's average cost at the
 * moment the shares left; partial transfers keep the value they had.»
 *
 * The rule is pinned in the backend (`test_wac_inline.py` P30–P35, `test_average_cost.py` U13,
 * `test_broker_internal_flows.py` 15a, `test_portfolio_cost_currency.py` S7); the E2E specs drove only the Auto/Manual
 * toggle and the preview on seed data. Here a user saves the TRANSFER through the app — the editor and its form, the
 * cost basis never touched — on a ledger whose average is known exactly, and the result is followed to the Dashboard.
 *
 * The ledger, on broker A: 3000 EUR in, 10 units bought at 100 and 10 at 200 — 20 units at an average of
 * (10 × 100 + 10 × 200) / 20 = 150 EUR; the asset is last quoted 180. Broker B holds nothing.
 *
 *   T1 — the whole position, 20 units, A → B. Before 1.2 the receiving side averaged A *after* the outgoing leg of the
 *        same transfer: an empty pool, a cost of 0, and B's 20 × 180 = 3600 EUR all read as gain. Now B costs 150 per
 *        unit and gains 20 × (180 − 150) = 600; A has nothing left.
 *   T2 — a partial transfer, 8 of the 20. The 8 arrive at 150 (gain 240); the 12 left on A keep 150 (gain 360).
 *
 * Each test proves, on its own data: the form proposes 150 while the user looks at it; the editor's cell proposes
 * 150 before saving; the commit sends the receiving side in Auto and the server answers that it averaged broker A at
 * 150; the saved receiving row costs 150; the Dashboard report and its Positions table (the average-cost column shown
 * through the column menu) give B — and, in T2, A — exactly the figures above.
 *
 * Ownership. Each test registers its own account, which owns the whole Dashboard: every position asserted on is one
 * this test created. The asset (a manual one, priced only by the quotes stored here), the two brokers and every row
 * are created through the API or the app and deleted by id at the end, whatever the outcome: the saved pair by the
 * ids the commit answered, the brokers with whatever is still on them, then the asset and the account. No global row
 * is read or written, so the tests run in parallel with anything.
 *
 * Waits are states, never the clock: `data-busy` on the pages, the editor's `data-validate-runs` sampled before the
 * draft is applied, the cell's `data-state`, and the commit and report requests — which are the subject here: the
 * commit is what is being tested, and a full page load always asks the report (the report cache lives in memory).
 * Assertions read test ids, ARIA state, ids, ISO dates and digits — never translated text.
 */

import {expect, test as base, type APIRequestContext, type Locator, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {validateRuns, waitForSettled, waitForValidateRun} from '../fixtures/app-events';
import {navigateTo} from '../fixtures/auth-helpers';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;
const REPORT_PATH = `${API}/portfolio/report`;
const WAC_PATH = `${API}/portfolio/wac`;
const UI_TIMEOUT = 15_000;
/** The dashboard period: it starts before the first movement and ends today. */
const PERIOD_START_DAYS_AGO = 90;

/** Broker A's ledger: the cash comes in first, then two purchases that leave it at zero. */
const FUNDING = {daysAgo: 40, amount: '3000'};
const PURCHASES = [
    {daysAgo: 30, quantity: '10', cash: '-1000', close: 100},
    {daysAgo: 20, quantity: '10', cash: '-2000', close: 200},
] as const;
/** The asset's last quote, after both purchases: what every position is valued at. */
const LAST_QUOTE = {daysAgo: 5, close: 180};
/** (10 × 100 + 10 × 200) / 20. */
const SENDER_AVERAGE = 150;

type Position = {quantity: number; wac_per_unit: number; current_value: number; gain_loss: number};
type Scenario = {
    /** Short: it goes into the account's username, capped at 50 characters. */
    tag: string;
    title: string;
    /** The quantity typed in the form. */
    moved: string;
    /** Broker B after the transfer. */
    receiving: Position;
    /** Broker A after the transfer; null when nothing is left on it. */
    remaining: Position | null;
};

const SCENARIOS: readonly Scenario[] = [
    {
        tag: 'tacw',
        title: 'T1 — the whole position moved in Auto: the receiving broker takes the sender’s average, 150, not 0',
        moved: '20',
        // 20 × 180 = 3600 EUR, of which 20 × (180 − 150) = 600 is gain. Before 1.2: a cost of 0, a gain of 3600.
        receiving: {quantity: 20, wac_per_unit: 150, current_value: 3600, gain_loss: 600},
        remaining: null,
    },
    {
        tag: 'tacp',
        title: 'T2 — a partial transfer in Auto: the 8 units moved arrive at 150, the 12 left on the sender keep 150',
        moved: '8',
        // B: 8 × 180 = 1440, gain 8 × 30 = 240. A: 12 × 180 = 2160, gain 12 × 30 = 360.
        receiving: {quantity: 8, wac_per_unit: 150, current_value: 1440, gain_loss: 240},
        remaining: {quantity: 12, wac_per_unit: 150, current_value: 2160, gain_loss: 360},
    },
];

type Money = {code: string; amount: string};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type Broker = {id: number; name: string};
type Asset = {id: number; name: string};
type Owned = {user: DisposableUser | null; brokerIds: number[]; assetIds: number[]; transactionIds: number[]};
type CommitBody = {
    committed: boolean;
    issues?: unknown[];
    results?: Array<{operation: string; index: number; ids?: number[]; status?: string}>;
    wac_results?: Array<{operation?: string | null; index?: number | null; source_broker_id?: number | null; wac?: Money | null}> | null;
};
type SentCreate = Record<string, unknown>;
type TransactionRead = {id: number; broker_id: number; asset_id?: number | null; type: string; date: string; quantity: string; related_transaction_id?: number | null; cost_basis_override?: Money | null};
type WacBody = {results: Array<{broker_id: number; asset_id: number; currency: string; series: Array<{date: string; wac: string; pool_qty: string}>}>};
type ReportHolding = {asset_id: number; broker_id?: number | null; quantity: string; wac_per_unit?: string | null; current_value?: string | null; gain_loss?: string | null};
type ReportBody = {metadata?: {target_currency?: string} | null; summary?: {holdings?: ReportHolding[]} | null};
type ReportRequestBody = {include_summary?: boolean; date_range?: {start?: string; end?: string} | null};

/**
 * A wait armed before the action and awaited later. If the test fails in between, the pending wait would reject
 * unobserved when the page closes; awaiting the returned promise still throws as usual.
 */
function armed<T>(wait: Promise<T>): Promise<T> {
    wait.catch(() => undefined);
    return wait;
}

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

function numberOrNull(value: string | number | null | undefined): number | null {
    return value == null ? null : Number(value);
}

function digitsOf(text: string | null): string {
    return (text ?? '').replace(/\D/g, '');
}

/** The digits of an amount rendered with two decimals, whatever the locale's separators: 150 → "15000". */
function amountDigits(value: number): string {
    return value.toFixed(2).replace(/\D/g, '');
}

function isCommit(req: Request): boolean {
    return req.method() === 'POST' && new URL(req.url()).pathname === COMMIT_PATH;
}

/** The dashboard's own report load: the one request that carries the summary. */
function isSummaryReport(req: Request): boolean {
    if (req.method() !== 'POST' || new URL(req.url()).pathname !== REPORT_PATH) return false;
    return (req.postDataJSON() as ReportRequestBody | null)?.include_summary === true;
}

/** The app's `todayIso()`, computed where the app computes it: in the browser. */
async function browserToday(page: Page): Promise<string> {
    return page.evaluate(() => {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    });
}

// ---------------------------------------------------------------------------
// Owned rows: seeding and cleanup
// ---------------------------------------------------------------------------

/** Both brokers in one call; every id is recorded for cleanup before any is checked. */
async function createBrokers(page: Page, owned: Owned, names: [string, string]): Promise<[Broker, Broker]> {
    const body = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null}>}>(await page.request.post(`${API}/brokers`, {data: names.map((name) => ({name, opened_at: daysAgoIso(400)}))}), 'create the owned brokers');
    for (const item of body.results) if (item.success && typeof item.broker_id === 'number' && names.includes(item.name)) owned.brokerIds.push(item.broker_id);
    const [from, to] = names.map((name): Broker => {
        const id = body.results.find((item) => item.name === name && item.success)?.broker_id;
        if (typeof id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(body)}`);
        return {id, name};
    });
    return [from, to];
}

/** A manual asset: no provider, so nothing ever prices it but the quotes this test stores. */
async function createManualAsset(page: Page, owned: Owned, name: string): Promise<Asset> {
    const item = {display_name: name, currency: 'EUR', asset_type: 'ETF', quote_base_quantity: 1, active: true};
    schemas.FAAssetCreateItem.parse(item);
    const body = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [item]}), 'create the owned asset');
    const created = body.results.find((result) => result.display_name === name);
    if (typeof created?.asset_id === 'number') owned.assetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(body)}`);
    return {id: created.asset_id, name};
}

async function seedPrices(page: Page, asset: Asset, prices: Array<{date: string; close: number}>): Promise<void> {
    const body = await jsonFrom<{results: Array<{asset_id: number; count: number}>}>(await page.request.post(`${API}/assets/prices`, {data: [{asset_id: asset.id, prices: prices.map((price) => ({...price, currency: 'EUR'}))}]}), 'store the asset quotes');
    expect(body.results.find((item) => item.asset_id === asset.id)?.count, 'every quote is stored').toBe(prices.length);
}

/** The funding and the purchases on broker A, in one batch, each create checked against the contract first. */
async function commitLedger(page: Page, from: Broker, asset: Asset, marker: string): Promise<void> {
    const creates = [
        {broker_id: from.id, type: 'DEPOSIT', date: daysAgoIso(FUNDING.daysAgo), cash: {code: 'EUR', amount: FUNDING.amount}, description: `${marker} funding`},
        ...PURCHASES.map((buy) => ({broker_id: from.id, asset_id: asset.id, type: 'BUY', date: daysAgoIso(buy.daysAgo), quantity: buy.quantity, cash: {code: 'EUR', amount: buy.cash}, description: `${marker} purchase`})),
    ];
    for (const create of creates) schemas.TXCreateItem_Input.parse(create);
    const body = await jsonFrom<CommitBody>(await page.request.post(COMMIT_PATH, {data: {creates}}), 'commit the ledger of broker A');
    expect(body.committed, `the ledger of broker A rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
}

/** The average-cost series of `broker` for `asset`, one point per movement: date, average and units after it. */
async function averageSeries(page: Page, broker: Broker, asset: Asset): Promise<Array<{date: string; wac: number; pool_qty: number}>> {
    const query = {queries: [{broker_id: broker.id, asset_id: asset.id}]};
    schemas.WACAnalyticsRequest.parse(query);
    const body = await jsonFrom<WacBody>(await page.request.post(WAC_PATH, {data: query}), `the average cost of ${broker.name}`);
    const result = body.results.find((item) => item.broker_id === broker.id && item.asset_id === asset.id);
    if (!result) throw new Error(`POST /portfolio/wac answered nothing for broker ${broker.id}: ${JSON.stringify(body)}`);
    expect(result.currency, 'the average is in the asset currency').toBe('EUR');
    return result.series.map((point) => ({date: point.date, wac: Number(point.wac), pool_qty: Number(point.pool_qty)}));
}

async function ledgerOf(page: Page, broker: Broker): Promise<TransactionRead[]> {
    return jsonFrom<TransactionRead[]>(await page.request.get(`${API}/transactions`, {params: {broker_id: broker.id}}), `read the rows of ${broker.name}`);
}

async function readTransactions(page: Page, ids: number[]): Promise<TransactionRead[]> {
    const query = ids.map((id) => `ids=${id}`).join('&');
    return jsonFrom<TransactionRead[]>(await page.request.get(`${API}/transactions?${query}`), `read transactions ${ids.join(', ')}`);
}

/**
 * Delete in dependency order, each step scoped to an id this test recorded. The page is unmounted first, so nothing
 * reloads while the rows go. The pair saved through the app goes by the ids its commit answered; the brokers then go
 * with `force`, which takes whatever is still on them; the asset (with its quotes) after them; the account last,
 * through the standalone `request` context it was registered with, which signs in on its own.
 */
async function cleanupOwned(page: Page, request: APIRequestContext, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    await attempt('unmount the page', async () => {
        await page.goto('about:blank');
    });
    if (owned.transactionIds.length > 0) {
        await attempt(`transactions ${owned.transactionIds.join(', ')}`, async () => {
            const body = await jsonFrom<CommitBody>(await page.request.post(COMMIT_PATH, {data: {creates: [], updates: [], deletes: owned.transactionIds}}), 'delete the pair saved through the app');
            expect(body.committed, `the deletion rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
        });
    }
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const body = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete an owned broker and its rows');
            expect(body.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const body = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete the owned asset and its quotes');
            expect(body.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
        });
    }
    const user = owned.user;
    if (user) {
        await attempt(`account ${user.username}`, async () => {
            await deleteDisposableUser(request, user);
        });
    }
    expect(failures, 'every cleanup step is scoped to rows this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page, request}, use) => {
        const owned: Owned = {user: null, brokerIds: [], assetIds: [], transactionIds: []};
        try {
            await use(owned);
        } finally {
            await cleanupOwned(page, request, owned);
        }
    },
});

test.setTimeout(150_000);

// ---------------------------------------------------------------------------
// The editor and its form
// ---------------------------------------------------------------------------

/** «+» on the transactions page opens the editor with a new row's form on top: the user's way in. */
async function openNewTransactionForm(page: Page): Promise<Locator> {
    await navigateTo(page, '/transactions');
    const transactionsPage = page.getByTestId('transactions-page');
    await expect(transactionsPage).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(transactionsPage, 20_000);
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-bulk-modal'), 'the editor opens').toBeVisible({timeout: UI_TIMEOUT});
    const form = page.getByTestId('tx-form-modal');
    await expect(form, 'with the form of a new row on top of it').toBeVisible({timeout: UI_TIMEOUT});
    return form;
}

/** The SearchSelect trigger inside `scope`: the one element with an explicit combobox role that opens a listbox. */
function selectTrigger(scope: Locator): Locator {
    return scope.locator('[role="combobox"][aria-haspopup="listbox"]');
}

/** Open a SearchSelect only if it is closed — never a blind click on a toggle. */
async function openSelect(trigger: Locator): Promise<void> {
    await expect(trigger).toBeVisible({timeout: UI_TIMEOUT});
    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');
}

async function chooseTransfer(page: Page, form: Locator): Promise<void> {
    const select = form.getByTestId('tx-form-type');
    await openSelect(selectTrigger(select));
    const option = select.getByTestId('search-select-option-TRANSFER');
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(form.getByTestId('tx-form-dual-from'), 'a TRANSFER is entered as a pair: from one broker…').toBeVisible({timeout: UI_TIMEOUT});
    await expect(form.getByTestId('tx-form-dual-to'), '…to another').toBeVisible();
}

/** Pick an owned broker by id in one side of the pair; the side's only listbox trigger is its broker select. */
async function pickBroker(page: Page, side: Locator, broker: Broker): Promise<void> {
    const trigger = selectTrigger(side);
    await openSelect(trigger);
    const option = side.getByTestId(`search-select-option-${broker.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(trigger).toContainText(broker.name);
}

/** The asset select searches inline: narrow it to the owned asset's unique name, then pick it by id. */
async function pickAsset(page: Page, form: Locator, asset: Asset): Promise<void> {
    const trigger = form.getByTestId('tx-form-asset-trigger');
    await openSelect(trigger);
    const search = form.getByTestId('tx-form-asset-search');
    await expect(search).toBeVisible({timeout: UI_TIMEOUT});
    await search.fill(asset.name);
    const option = form.getByTestId('tx-form-asset').getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(trigger).toContainText(asset.name);
}

async function fillQuantity(form: Locator, quantity: string): Promise<void> {
    const input = form.getByTestId('tx-form-quantity');
    await expect(input).toBeVisible({timeout: UI_TIMEOUT});
    await input.fill(quantity);
    await input.blur();
    await expect(input, 'the form keeps the quantity typed').toHaveValue(quantity);
}

/** The description lives in the collapsible optional `<details>`: read its real `open` state, never click blind. */
async function fillDescription(form: Locator, text: string): Promise<void> {
    const details = form.locator('details:has([data-testid="tx-form-optional-toggle"])');
    await expect(details).toBeVisible({timeout: UI_TIMEOUT});
    if (!(await details.evaluate((element) => (element as HTMLDetailsElement).open))) await form.getByTestId('tx-form-optional-toggle').click();
    await expect(details).toHaveAttribute('open', '');
    const description = form.getByTestId('tx-form-description');
    await description.fill(text);
    await expect(description).toHaveValue(text);
}

/** Push the form's draft into the editor's grid. */
async function applyForm(form: Locator): Promise<void> {
    const apply = form.getByTestId('tx-form-save');
    await expect(apply).toBeEnabled({timeout: UI_TIMEOUT});
    await apply.click();
    await expect(form).toBeHidden({timeout: UI_TIMEOUT});
}

// ---------------------------------------------------------------------------
// The dashboard
// ---------------------------------------------------------------------------

function dashboardUrl(): string {
    const params = new URLSearchParams({tab: 'posizioni', start: daysAgoIso(PERIOD_START_DAYS_AGO), end: todayIso()});
    return `/dashboard?${params.toString()}`;
}

/** A full load of the dashboard, with the report it asked for: the application's own response, captured, never routed. */
async function openDashboard(page: Page): Promise<{range: ReportRequestBody['date_range']; report: ReportBody}> {
    const reportResponse = armed(page.waitForResponse((response) => isSummaryReport(response.request()), {timeout: 30_000}));
    await page.goto(dashboardUrl());
    const answer = await reportResponse;
    const range = (answer.request().postDataJSON() as ReportRequestBody).date_range;
    const report = await jsonFrom<ReportBody>(answer, 'dashboard report');
    return {range, report};
}

function holdingsOf(report: ReportBody, asset: Asset, broker: Broker): ReportHolding[] {
    return (report.summary?.holdings ?? []).filter((item) => item.asset_id === asset.id && item.broker_id === broker.id);
}

function positionFigures(holding: ReportHolding | undefined): Record<keyof Position, number | null> {
    return {
        quantity: numberOrNull(holding?.quantity),
        wac_per_unit: numberOrNull(holding?.wac_per_unit),
        current_value: numberOrNull(holding?.current_value),
        gain_loss: numberOrNull(holding?.gain_loss),
    };
}

/** The position's row in the holdings table of the positions panel inside `scope`. */
function positionRow(scope: Locator, asset: Asset, broker: Broker): Locator {
    return scope.getByTestId('positions-panel').getByTestId('exposure-table').locator(`tbody tr[data-row-id="${asset.id}-${broker.id}"]`);
}

function positionCell(row: Locator, columnId: 'pmc' | 'pnl' | 'quantity'): Locator {
    return row.locator(`td[data-column-id="${columnId}"]`);
}

/**
 * Show a column the holdings table hides by default (the average cost is one), through the panel's own column menu.
 * A fresh account starts from the defaults, but the layout is remembered: the header's absence — read once the table
 * is on screen, when the layout is settled — is the state to change, and its presence the proof it did.
 */
async function revealColumn(page: Page, panel: Locator, table: Locator, columnId: string): Promise<void> {
    const header = table.getByTestId(`dt-header-${columnId}`);
    if ((await header.count()) === 0) {
        const menuScope = panel.getByTestId('positions-column-visibility-toggle');
        await menuScope.getByTestId('column-visibility-toggle').click();
        const menu = menuScope.getByTestId('column-visibility-dropdown');
        await expect(menu).toBeVisible({timeout: UI_TIMEOUT});
        await menu.getByTestId(`column-visibility-item-${columnId}`).click();
        await expect(header).toBeVisible({timeout: UI_TIMEOUT});
        // The menu closes on a click outside it, which lands on its own full-screen backdrop; the menu keeps at least
        // 8px from every edge, so the corner is always outside it.
        await page.mouse.click(2, 2);
        await expect(menu).toBeHidden({timeout: UI_TIMEOUT});
    }
    await expect(header).toBeVisible();
}

/** The holdings × table view of the positions panel in `scope`, loaded, with `row` on screen and the average cost shown. */
async function showAverageCost(page: Page, scope: Locator, row: Locator): Promise<void> {
    const panel = scope.getByTestId('positions-panel');
    await waitForSettled(panel, 25_000);
    // Setters, not toggles: a click on the view already shown changes nothing.
    await panel.getByTestId('positions-toggle-holdings').click();
    await panel.getByTestId('positions-toggle-table').click();
    await expect(row, 'the position this test created is listed').toBeVisible({timeout: UI_TIMEOUT});
    await revealColumn(page, panel, panel.getByTestId('exposure-table'), 'pmc');
}

/** The row shows the position's quantity, average cost and unrealized gain, read as digits: no locale, no words. */
async function expectPositionOnScreen(row: Locator, position: Position, who: string): Promise<void> {
    const read = (columnId: 'pmc' | 'pnl' | 'quantity') => async () => digitsOf(await positionCell(row, columnId).textContent());
    await expect.poll(read('pmc'), {message: `${who}: average cost ${position.wac_per_unit} per unit`, timeout: UI_TIMEOUT}).toBe(amountDigits(position.wac_per_unit));
    await expect.poll(read('pnl'), {message: `${who}: unrealized gain ${position.gain_loss}`, timeout: UI_TIMEOUT}).toBe(amountDigits(position.gain_loss));
    await expect.poll(read('quantity'), {message: `${who}: ${position.quantity} units`, timeout: UI_TIMEOUT}).toBe(String(position.quantity));
}

// ---------------------------------------------------------------------------
// The scenario
// ---------------------------------------------------------------------------

async function transferInAuto(page: Page, request: APIRequestContext, owned: Owned, scenario: Scenario): Promise<void> {
    const moved = Number(scenario.moved);

    const {from, to, asset, marker} = await test.step('seed: an account with brokers A and B; A buys 10 at 100 and 10 at 200 — an average of 150', async () => {
        const user = await registerDisposableUser(request, scenario.tag);
        owned.user = user;
        await prepareOnboardingAccount(page, user, []);
        const suffix = uniqueSuffix();
        const marker = `tac ${scenario.tag} ${suffix}`;
        const [from, to] = await createBrokers(page, owned, [`tac-from-${suffix}`, `tac-to-${suffix}`]);
        const asset = await createManualAsset(page, owned, `TAC asset ${suffix}`);
        await seedPrices(page, asset, [...PURCHASES.map((buy) => ({date: daysAgoIso(buy.daysAgo), close: buy.close})), {date: daysAgoIso(LAST_QUOTE.daysAgo), close: LAST_QUOTE.close}]);
        await commitLedger(page, from, asset, marker);
        return {from, to, asset, marker};
    });

    await test.step('premise: A holds 20 units at an average of 150, B holds nothing', async () => {
        expect(await averageSeries(page, from, asset), 'the average of A after each purchase: 100 over 10 units, then 150 over 20').toEqual([
            {date: daysAgoIso(PURCHASES[0].daysAgo), wac: 100, pool_qty: 10},
            {date: daysAgoIso(PURCHASES[1].daysAgo), wac: SENDER_AVERAGE, pool_qty: 20},
        ]);
        expect(await ledgerOf(page, to), 'B starts empty: whatever it costs afterwards comes from the transfer').toEqual([]);
    });

    const form = await openNewTransactionForm(page);
    const today = await browserToday(page);

    await test.step(`the form: a TRANSFER of ${scenario.moved} from A to B, the cost basis left in Auto, proposes 150 per unit`, async () => {
        await chooseTransfer(page, form);
        await pickBroker(page, form.getByTestId('tx-form-dual-from'), from);
        await pickBroker(page, form.getByTestId('tx-form-dual-to'), to);
        await pickAsset(page, form, asset);
        await fillQuantity(form, scenario.moved);
        await fillDescription(form, marker);
        // The state under test: Auto, the default, never touched; the amount shown per unit.
        await expect(form.getByTestId('tx-form-cost-basis'), 'the transfer carries a cost basis').toBeVisible();
        await expect(form.getByTestId('tx-form-cost-basis-toggle-auto'), 'the cost basis is in Auto').toHaveAttribute('aria-pressed', 'true');
        await expect(form.getByTestId('tx-form-cost-basis-toggle-manual'), 'not in Manual').not.toHaveAttribute('aria-pressed', 'true');
        await expect(form.getByTestId('tx-form-cost-basis-unit-toggle-unit'), 'the amount is shown per unit').toHaveAttribute('aria-pressed', 'true');
        await expect(form.getByTestId('tx-form-cost-basis-suggestion'), 'the form validated the pair and has an Auto proposal').toBeVisible({timeout: 25_000});
        const amount = form.getByTestId('tx-form-cost-basis-input-amount');
        await expect.poll(async () => (await amount.inputValue()).trim(), {message: 'the form proposes the average of the sending broker, 150 per unit', timeout: 25_000}).toMatch(new RegExp(`^${SENDER_AVERAGE}(?:[.,]0+)?$`));
        await expect(form.getByTestId('tx-form-cost-basis-toggle-auto'), 'still in Auto: nothing was typed').toHaveAttribute('aria-pressed', 'true');
    });

    const editorRoot = page.getByTestId('tx-bulk-modal-root');
    const pairRow = page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]').filter({hasText: marker});

    await test.step('the editor: the pair is one row, and its cost-basis cell proposes 150 in Auto', async () => {
        // Sampled before the draft lands: the run awaited below is one that saw the pair.
        const runsBefore = await validateRuns(editorRoot);
        await applyForm(form);
        await waitForValidateRun(editorRoot, runsBefore, 30_000);
        await expect(pairRow, 'the pair this test entered is one row of the editor').toHaveCount(1, {timeout: UI_TIMEOUT});
        const proposal = pairRow.getByTestId('tx-bulk-cost-basis-auto');
        await expect(proposal, 'the cell is in Auto, with a computed proposal').toHaveAttribute('data-state', 'ready', {timeout: 25_000});
        await expect.poll(async () => digitsOf(await proposal.textContent()), {message: 'the cell proposes 150.00 per unit', timeout: UI_TIMEOUT}).toBe(amountDigits(SENDER_AVERAGE));
    });

    const {sent, answer} = await test.step('save: the commit sends the receiving side in Auto and is accepted', async () => {
        await expect(page.getByTestId('tx-bulk-valid'), 'the editor validated the batch it is about to save, with no issue').toBeVisible({timeout: 25_000});
        const save = page.getByTestId('tx-bulk-commit');
        await expect(save).toBeEnabled({timeout: UI_TIMEOUT});
        const sentRequest = armed(page.waitForRequest(isCommit, {timeout: 30_000}));
        const response = armed(page.waitForResponse((res) => isCommit(res.request()), {timeout: 60_000}));
        await save.click();
        const sent = ((await sentRequest).postDataJSON() as {creates?: SentCreate[]} | null)?.creates ?? [];
        const answer = await jsonFrom<CommitBody>(await response, 'the commit answer');
        // Recorded before anything is checked: a red after the save still deletes what it saved.
        if (answer.committed) owned.transactionIds.push(...new Set((answer.results ?? []).filter((item) => item.operation === 'create' && item.status === 'success').flatMap((item) => item.ids ?? [])));
        expect(answer.committed, `the save was rolled back: ${JSON.stringify(answer.issues ?? [])}`).toBe(true);
        await expect(page.getByTestId('tx-bulk-modal'), 'the editor closes on a successful save').toBeHidden({timeout: UI_TIMEOUT});
        return {sent, answer};
    });

    const receivingIndex = sent.findIndex((item) => item.broker_id === to.id);
    const sendingIndex = sent.findIndex((item) => item.broker_id === from.id);

    await test.step('the commit: the pair as typed, the receiving side in Auto; the server averaged broker A — 150', async () => {
        expect(sent, `the editor saves the one pair this test put in it: ${JSON.stringify(sent)}`).toHaveLength(2);
        expect(receivingIndex, 'one create is the receiving side, on broker B').toBeGreaterThanOrEqual(0);
        expect(sendingIndex, 'one create is the sending side, on broker A').toBeGreaterThanOrEqual(0);
        const leg = (item: SentCreate) => ({type: item.type, asset_id: item.asset_id, date: item.date, quantity: Number(item.quantity)});
        expect(leg(sent[sendingIndex]), 'the units leave A today').toEqual({type: 'TRANSFER', asset_id: asset.id, date: today, quantity: -moved});
        expect(leg(sent[receivingIndex]), 'and arrive on B today').toEqual({type: 'TRANSFER', asset_id: asset.id, date: today, quantity: moved});
        expect(sent[receivingIndex].link_uuid, 'the two sides are one pair').toBeTruthy();
        expect(sent[sendingIndex].link_uuid).toBe(sent[receivingIndex].link_uuid);
        expect(sent[receivingIndex].cost_basis_mode, 'the receiving side is sent in Auto: its cost is the server’s to compute').toBe('auto');

        const computed = (answer.wac_results ?? []).find((item) => item.operation === 'create' && item.index === receivingIndex);
        expect({source_broker_id: computed?.source_broker_id, code: computed?.wac?.code, amount: numberOrNull(computed?.wac?.amount)}, `the server averaged the sending broker, at the moment the units left — answered ${JSON.stringify(answer.wac_results)}`).toEqual({
            source_broker_id: from.id,
            code: 'EUR',
            amount: SENDER_AVERAGE,
        });
    });

    await test.step('the saved rows: a linked pair, and the receiving side costs 150 per unit', async () => {
        expect(owned.transactionIds, 'the commit answered an id for each side').toHaveLength(2);
        const saved = await readTransactions(page, owned.transactionIds);
        const giver = saved.find((item) => item.broker_id === from.id);
        const receiver = saved.find((item) => item.broker_id === to.id);
        if (!giver || !receiver) throw new Error(`The saved pair is missing a side: ${JSON.stringify(saved)}`);
        expect([giver.related_transaction_id, receiver.related_transaction_id], 'the two sides are linked to each other').toEqual([receiver.id, giver.id]);
        expect({type: giver.type, quantity: Number(giver.quantity)}, 'the sending side takes the units out of A').toEqual({type: 'TRANSFER', quantity: -moved});
        expect({type: receiver.type, quantity: Number(receiver.quantity), code: receiver.cost_basis_override?.code, amount: numberOrNull(receiver.cost_basis_override?.amount)}, 'the receiving side costs the sender’s average, 150 EUR per unit — not 0').toEqual({
            type: 'TRANSFER',
            quantity: moved,
            code: 'EUR',
            amount: SENDER_AVERAGE,
        });
    });

    const load = await openDashboard(page);

    await test.step('the report: B holds the units at 150, its gain is not their whole value; A as expected', async () => {
        expect(load.range, 'precondition: the URL sets the dashboard period').toMatchObject({start: daysAgoIso(PERIOD_START_DAYS_AGO), end: todayIso()});
        expect(load.report.metadata?.target_currency, 'precondition: the dashboard reports in EUR, the currency every figure here is in').toBe('EUR');
        const receiving = holdingsOf(load.report, asset, to);
        expect(receiving, `one position of the asset on B: ${JSON.stringify(load.report.summary?.holdings)}`).toHaveLength(1);
        const figures = positionFigures(receiving[0]);
        expect(figures, `B after the transfer: ${scenario.receiving.quantity} units at 150, valued 180`).toEqual(scenario.receiving);
        expect(figures.gain_loss, 'the gain is not the whole market value — the 1.1 symptom of a cost of 0').not.toBe(figures.current_value);
        const remaining = holdingsOf(load.report, asset, from);
        if (scenario.remaining) {
            expect(remaining, 'one position of the asset left on A').toHaveLength(1);
            expect(positionFigures(remaining[0]), `A after the transfer: ${scenario.remaining.quantity} units, still at 150`).toEqual(scenario.remaining);
        } else {
            expect(remaining, 'the whole position left A: no holding is listed there').toEqual([]);
        }
    });

    await test.step('the Dashboard: B’s average cost, gain and units in the Positions table — and A’s row as expected', async () => {
        const dashboard = page.getByTestId('dashboard-page');
        await waitForSettled(dashboard, 25_000);
        const receivingRow = positionRow(dashboard, asset, to);
        await showAverageCost(page, dashboard, receivingRow);
        await expectPositionOnScreen(receivingRow, scenario.receiving, 'B');
        const remainingRow = positionRow(dashboard, asset, from);
        if (scenario.remaining) {
            await expect(remainingRow, 'the units left on A are listed').toBeVisible();
            await expectPositionOnScreen(remainingRow, scenario.remaining, 'A');
        } else {
            // B's row above is the presence barrier: the table is drawn from the same holdings.
            await expect(remainingRow, 'nothing is left on A: no row').toHaveCount(0);
        }
    });
}

test.describe('Asset transfer in Auto keeps the cost of the units it moves (CHANGELOG 1.2)', () => {
    for (const scenario of SCENARIOS) {
        test(scenario.title, async ({page, request, owned}) => {
            await transferInAuto(page, request, owned, scenario);
        });
    }
});
