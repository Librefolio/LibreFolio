/**
 * Yield on Cost in the holdings, on real data — release 1.2, E2E gap 4 (plan 46, §12.4).
 *
 * `ExposureTable.test.ts` covers how the Holdings table renders a YOC result it is handed; `test_yield_on_cost.py`
 * covers the calculation. Nothing covered the path between them. Here every result comes from the engine, on a ledger
 * the test writes through the API, and the assertions follow it from the report to the screen.
 *
 *   Y1 — per (asset, broker), anchored at the report end. One asset is held at two brokers, each with its own cost and
 *        its own dividend, paid before the dashboard period starts but inside [T−364, T]. The report gives each row its
 *        own YOC, exactly the oracle's, and so does the screen, on the Dashboard and on the broker page. A YOC computed
 *        per asset would read 2.10% on both rows; one that counted only the report period would find no income at all.
 *   Y2 — no cost, no YOC. An acquisition without a purchase cost leaves the average cost unknown. The app can no
 *        longer save one: an ADJUSTMENT adding quantity needs a cost (COST_BASIS_REQUIRED), and the last path, P-10 —
 *        an ADJUSTMENT linked to a SPLIT, saved in Auto, whose event is then retyped — is closed too (the retype is
 *        refused with EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST, pinned by E2 of `data-quality-real.spec.ts`). Such rows
 *        exist only in data an older version left behind, so the test writes one the way `data-quality-legacy.spec.ts`
 *        does: `backend/test_scripts/test_db/legacy_cost_rows.py`, run against this lane's test database only, adds an
 *        ADJUSTMENT-in with no cost to the position (plus the TRANSFER pair the helper always writes, on a second owned
 *        broker and asset that nothing here asserts on). The position has a dividend in the window, so the dash means
 *        «unknown cost», not «no income»: the report answers unavailable / missing_wac and the cell shows the dash
 *        with its info icon, never a figure. An explicit cost of 0 per unit turns it into a figure, the oracle's.
 *
 * The oracle is the backend contract restated independently (`_oracle_yoc` in `test_yield_on_cost.py`):
 *
 *     YOC(a, b, T) = Σ_j I_j / q_j / s_j  ÷  WAC(a, b, T)
 *
 * over the asset-linked DIVIDEND/INTEREST rows of the pair dated inside [T−364, T]; q_j is the pair's quantity at the
 * end of the day before payment, s_j the product of the linked splits from the payment on, WAC the residual average
 * cost per unit. Every number is chosen so the fraction is exact in decimal: the API value is compared with `toBe`,
 * the screen by its digits (two decimals of the percentage, whatever the locale's separators) and by its sign (none).
 *
 * Ownership. Each test registers its own account, which owns the whole dashboard under test: every row asserted on is
 * one the test created. Brokers (with their transactions), assets (with their prices and events) and the account are
 * deleted by id in the fixture teardown, whatever the outcome. Every amount is in EUR, the account's report currency:
 * no FX rate is read or written.
 *
 * Offline. The assets are manual, with no provider, so nothing prices them but the quotes stored here; nothing is
 * routed or mocked, and every response read is the application's own.
 */

import {execFileSync} from 'child_process';
import * as path from 'path';
import {fileURLToPath} from 'url';
import {expect, test as base, type APIRequestContext, type Locator, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const REPORT_PATH = `${API}/portfolio/report`;
/** The dashboard period of every test starts this many days ago and ends today. */
const PERIOD_START_DAYS_AGO = 60;
/** YOC's window is [T−364, T]: 365 calendar dates ending at the report end T. */
const WINDOW_START_DAYS_BEFORE_END = 364;
/** The YOC column, as `DataTable` publishes it on its header (`dt-header-…`) and on every cell (`data-column-id`). */
const YOC_COLUMN = 'yield-on-cost';
const PROJECT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
/** Writes acquisitions without a cost the way an older version stored them (see Y2 above). */
const LEGACY_HELPER_MODULE = 'backend.test_scripts.test_db.legacy_cost_rows';

type Money = {code: string; amount: string};
type Period = {start: string; end: string};
type YieldOnCost = {
    status: string;
    value?: string | null;
    reason?: string | null;
    provenance: {
        window_start: string;
        window_end: string;
        first_pair_transaction_date?: string | null;
        gross_income_transaction_count?: number;
        gross_income_per_unit?: Money | null;
        net_zero?: boolean;
        fx?: unknown[];
    };
};
type ReportHolding = {asset_id: number; broker_id?: number | null; quantity: string; wac_per_unit?: string | null; yield_on_cost: YieldOnCost};
type ReportRequestBody = {include_summary?: boolean; date_range?: {start?: string; end?: string} | null};
type ReportBody = {metadata?: {target_currency?: string} | null; summary?: {holdings?: unknown[]} | null};
type CommitBody = {committed: boolean; issues?: unknown[]; results?: Array<{operation: string; index: number; ids: number[]}>};
type TransactionRead = {id: number; broker_id: number; asset_id?: number | null; type: string; date: string; quantity: string; cash?: unknown; description?: string | null; asset_event_id?: number | null; cost_basis_override?: Money | null};
type LegacyRows = {transfer_out: number; transfer_in: number; adjustment_in: number};
type LegacyRequest = {userId: number; sourceBroker: number; destBroker: number; transferAsset: number; adjustmentAsset: number; date: string; transferQty: number; adjustmentQty: number; marker: string};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type Owned = {user: DisposableUser | null; brokerIds: number[]; assetIds: number[]};

/** One asset-linked DIVIDEND/INTEREST row of the pair inside the window, as the definition reads it. */
type Income = {amount: number; eligibleQuantity: number; laterSplitRatio: number};
type Oracle = {grossPerUnit: number; value: number; digits: string};

/**
 * The contract, restated without the code under test: gross income per eligible unit (each amount over the pair's
 * quantity at the end of the day before payment, over the linked splits from the payment on) divided by the residual
 * average cost per unit. `digits` is what the Holdings cell shows once separators and the percent sign are dropped:
 * the percentage at two decimals.
 */
function yieldOnCostOracle(incomes: readonly Income[], wacPerUnit: number): Oracle {
    const grossPerUnit = incomes.reduce((sum, income) => sum + income.amount / income.eligibleQuantity / income.laterSplitRatio, 0);
    const value = grossPerUnit / wacPerUnit;
    return {grossPerUnit, value, digits: (value * 100).toFixed(2).replace(/\D/g, '')};
}

/**
 * A wait armed before the action and awaited later. If the test fails in between, the pending wait would reject
 * unobserved when the page closes, and that noise would be reported beside the real failure; awaiting the returned
 * promise still throws as usual.
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

// ---------------------------------------------------------------------------
// Owned rows: seeding and cleanup
// ---------------------------------------------------------------------------

/** Every id is recorded for cleanup before it is checked. */
async function createBroker(page: Page, owned: Owned, name: string): Promise<number> {
    const brokers = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: daysAgoIso(400)}]}), 'create an owned broker');
    const broker = brokers.results.find((item) => item.name === name);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(brokers)}`);
    return broker.broker_id;
}

/** A manual asset: no provider, so nothing ever prices it but the quotes this test stores. */
async function createManualAsset(page: Page, owned: Owned, name: string): Promise<number> {
    const item = {display_name: name, currency: 'EUR', asset_type: 'ETF', quote_base_quantity: 1, active: true};
    schemas.FAAssetCreateItem.parse(item);
    const assets = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>}>(await page.request.post(`${API}/assets`, {data: [item]}), 'create an owned asset');
    const asset = assets.results.find((result) => result.display_name === name);
    if (typeof asset?.asset_id === 'number') owned.assetIds.push(asset.asset_id);
    if (!asset?.success || typeof asset.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(assets)}`);
    return asset.asset_id;
}

async function seedPrices(page: Page, assetId: number, prices: Array<{date: string; close: number}>): Promise<void> {
    const rows = prices.map((price) => ({...price, currency: 'EUR'}));
    const seeded = await jsonFrom<{results: Array<{asset_id: number; count: number}>}>(await page.request.post(`${API}/assets/prices`, {data: [{asset_id: assetId, prices: rows}]}), 'seed the asset prices');
    expect(seeded.results.find((item) => item.asset_id === assetId)?.count, 'every price is stored').toBe(rows.length);
}

async function commitTransactions(page: Page, batch: {creates?: unknown[]; updates?: unknown[]}, purpose: string): Promise<CommitBody> {
    const committed = await jsonFrom<CommitBody>(await page.request.post(`${API}/transactions/commit`, {data: batch}), purpose);
    expect(committed.committed, `${purpose}: rolled back — ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
    return committed;
}

async function readTransaction(page: Page, id: number): Promise<TransactionRead> {
    const rows = await jsonFrom<TransactionRead[]>(await page.request.get(`${API}/transactions?ids=${id}`), `read transaction ${id}`);
    const row = rows.find((candidate) => candidate.id === id);
    if (!row) throw new Error(`GET /transactions?ids=${id} did not return the transaction: ${JSON.stringify(rows)}`);
    return row;
}

/**
 * Write acquisitions without a cost with `legacy_cost_rows.py`, as `data-quality-legacy.spec.ts` does (a minimal
 * copy of its `writeLegacyRows`, quantities as arguments; that spec exports nothing and no fixture holds it): from the
 * repo root, with this process's environment — TEST_PORT and LIBREFOLIO_TEST_DATA_DIR, exported by
 * playwright.config.ts, so the helper resolves this lane's database and nothing else, and refuses brokers the account
 * does not own. When the runner's `pipenv run` has already activated the environment (VIRTUAL_ENV), its interpreter is
 * called directly; otherwise `pipenv run python`. Arguments travel as an argv array, never through a shell. A non-zero
 * exit fails with the helper's own explanation.
 */
function writeLegacyRows(legacy: LegacyRequest): LegacyRows {
    const helperArgs = [
        '-m',
        LEGACY_HELPER_MODULE,
        '--user-id',
        String(legacy.userId),
        '--source-broker',
        String(legacy.sourceBroker),
        '--dest-broker',
        String(legacy.destBroker),
        '--transfer-asset',
        String(legacy.transferAsset),
        '--adjustment-asset',
        String(legacy.adjustmentAsset),
        '--date',
        legacy.date,
        '--transfer-qty',
        String(legacy.transferQty),
        '--adjustment-qty',
        String(legacy.adjustmentQty),
        '--marker',
        legacy.marker,
    ];
    const venv = process.env.VIRTUAL_ENV;
    const command = venv ? path.join(venv, 'bin', 'python') : 'pipenv';
    const argv = venv ? helperArgs : ['run', 'python', ...helperArgs];
    let stdout: string;
    try {
        stdout = execFileSync(command, argv, {cwd: PROJECT_ROOT, env: process.env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 90_000});
    } catch (error) {
        const failed = error as {status?: number | null; signal?: string | null; stdout?: string; stderr?: string; message?: string};
        throw new Error(`legacy_cost_rows (${command}) exited with ${failed.status ?? failed.signal ?? 'no status'}:\n${failed.stderr || failed.message || ''}\n${failed.stdout ?? ''}`);
    }
    // The helper's contract is one line of JSON on stdout; anything else is a failure worth reading.
    const lines = stdout.split('\n').filter((line) => line.trim() !== '');
    expect(lines, `legacy_cost_rows prints one line of JSON; it printed:\n${stdout}`).toHaveLength(1);
    const rows = JSON.parse(lines[0]) as LegacyRows;
    expect(rows, `legacy_cost_rows printed ${lines[0]}`).toEqual({transfer_out: expect.any(Number), transfer_in: expect.any(Number), adjustment_in: expect.any(Number)});
    return rows;
}

/**
 * Delete in dependency order, each step scoped to an id this test recorded.
 *
 * The page is unmounted first, so no reload of the dashboard reads rows while they go. Brokers go before assets (an
 * asset with transactions cannot be deleted; `force` takes the broker's transactions with it), the account last.
 * Brokers and assets are deleted by the account that created them (`page.request` shares the browser's session); the
 * account itself through the standalone `request` context it was registered with, which signs in on its own.
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
    await attempt('unmount the app', async () => {
        await page.goto('about:blank');
    });
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete an owned broker and its transactions');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete an owned asset, its prices and its events');
            expect(result.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
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
        const owned: Owned = {user: null, brokerIds: [], assetIds: []};
        try {
            await use(owned);
        } finally {
            await cleanupOwned(page, request, owned);
        }
    },
});

/**
 * A disposable account that owns the whole dashboard, its guides skipped so no overlay covers the table. Registered
 * through the standalone `request` context, like the guide specs: the browser signs in through the real login form.
 */
async function openAccount(page: Page, request: APIRequestContext, owned: Owned, tag: string): Promise<void> {
    const user = await registerDisposableUser(request, tag);
    owned.user = user;
    await prepareOnboardingAccount(page, user, []);
}

// ---------------------------------------------------------------------------
// The report
// ---------------------------------------------------------------------------

function dashboardPeriod(): Period {
    return {start: daysAgoIso(PERIOD_START_DAYS_AGO), end: todayIso()};
}

/** The dashboard's own report load for `period`: the one request that carries the summary. */
function isSummaryReportFor(req: Request, period: Period): boolean {
    if (req.method() !== 'POST' || new URL(req.url()).pathname !== REPORT_PATH) return false;
    const body = req.postDataJSON() as ReportRequestBody | null;
    return body?.include_summary === true && body.date_range?.start === period.start && body.date_range?.end === period.end;
}

/**
 * Open the dashboard on its Positions tab for `period` and return the report it asked for — the application's own
 * answer, captured, never routed. The current document is left first: whatever it still had in flight is cancelled
 * with it, so the answer awaited can only belong to the load this function starts. Matching the period of the URL is
 * also the precondition that the URL seeds the dashboard period.
 */
async function openDashboard(page: Page, period: Period): Promise<ReportBody> {
    await page.goto('about:blank');
    const answer = armed(page.waitForResponse((response) => isSummaryReportFor(response.request(), period), {timeout: 45_000}));
    await page.goto(`/dashboard?${new URLSearchParams({tab: 'posizioni', start: period.start, end: period.end}).toString()}`);
    const response = await answer.catch((error: unknown) => {
        throw new Error(`The dashboard answered no summary report for the period of its URL (${period.start} → ${period.end}): ${String(error)}`);
    });
    const report = await jsonFrom<ReportBody>(response, 'dashboard report');
    expect(report.metadata?.target_currency, 'precondition: the dashboard reports in EUR, the currency of every amount here').toBe('EUR');
    return report;
}

/** The holding of (asset, broker), validated against the generated schema the page parses it with. */
function holdingOf(report: ReportBody, assetId: number, brokerId: number): ReportHolding {
    const holdings = (report.summary?.holdings ?? []) as Array<{asset_id?: number; broker_id?: number | null}>;
    const raw = holdings.find((item) => item.asset_id === assetId && item.broker_id === brokerId);
    if (!raw) throw new Error(`The report lists no holding for asset ${assetId} on broker ${brokerId}; it lists ${JSON.stringify(holdings.map((item) => [item.asset_id, item.broker_id]))}`);
    schemas.PortfolioHolding.parse(raw);
    return raw as ReportHolding;
}

/** The cost base the oracle divides by: the quantity held and the residual average cost per unit. */
function costBase(holding: ReportHolding): {quantity: number; wac_per_unit: number | null} {
    return {quantity: Number(holding.quantity), wac_per_unit: numberOrNull(holding.wac_per_unit)};
}

/** A holding's YOC as plain numbers and strings, for one `toEqual` against what the oracle expects. */
function yieldOnCostFacts(holding: ReportHolding) {
    const yoc = holding.yield_on_cost;
    const perUnit = yoc.provenance.gross_income_per_unit ?? null;
    return {
        status: yoc.status,
        reason: yoc.reason ?? null,
        value: numberOrNull(yoc.value),
        window_start: yoc.provenance.window_start,
        window_end: yoc.provenance.window_end,
        first_pair_transaction_date: yoc.provenance.first_pair_transaction_date ?? null,
        gross_income_transaction_count: yoc.provenance.gross_income_transaction_count ?? 0,
        gross_income_per_unit: perUnit && {code: perUnit.code, amount: Number(perUnit.amount)},
        net_zero: yoc.provenance.net_zero ?? false,
        fx: yoc.provenance.fx ?? [],
    };
}

/** The YOC every available row of these tests must report: the oracle's value and per-unit income, over the window ending at `period.end`. */
function availableFacts(oracle: Oracle, period: Period, firstPairDay: string) {
    return {
        status: 'available',
        reason: null,
        value: oracle.value,
        window_start: daysAgoIso(WINDOW_START_DAYS_BEFORE_END),
        window_end: period.end,
        first_pair_transaction_date: firstPairDay,
        gross_income_transaction_count: 1,
        gross_income_per_unit: {code: 'EUR', amount: oracle.grossPerUnit},
        net_zero: false,
        // EUR income over an EUR cost, reported in EUR: no conversion, so no FX provenance.
        fx: [],
    };
}

// ---------------------------------------------------------------------------
// The screen
// ---------------------------------------------------------------------------

/** The position's row in the holdings table of the positions panel inside `scope` (the dashboard or a broker page). */
function positionRow(scope: Locator, assetId: number, brokerId: number): Locator {
    return scope.getByTestId('positions-panel').getByTestId('exposure-table').locator(`tbody tr[data-row-id="${assetId}-${brokerId}"]`);
}

function yieldOnCostCell(row: Locator): Locator {
    return row.locator(`td[data-column-id="${YOC_COLUMN}"]`);
}

/**
 * The Holdings × Table view of the positions panel inside `scope`, loaded, with `row` on screen. The YOC column is not
 * revealed through the column menu: it is shown by default, and this is a fresh account in a fresh browser context, so
 * a missing header is a red, not a state to repair.
 */
async function showHoldingsTable(scope: Locator, row: Locator): Promise<void> {
    const panel = scope.getByTestId('positions-panel');
    await waitForSettled(panel, 30_000);
    // Setters, not toggles: a click on the view already shown changes nothing.
    await panel.getByTestId('positions-toggle-holdings').click();
    await panel.getByTestId('positions-toggle-table').click();
    await expect(row, 'the position this test created is listed').toBeVisible({timeout: 20_000});
    await expect(panel.getByTestId('exposure-table').getByTestId(`dt-header-${YOC_COLUMN}`), 'the YOC column is shown by default').toBeVisible({timeout: 10_000});
}

/** The YOC cell of `row` shows the oracle's figure: its digits, no sign, and neither dash. */
async function expectYieldOnCostFigure(row: Locator, oracle: Oracle, label: string): Promise<void> {
    const cell = yieldOnCostCell(row);
    const figure = cell.getByTestId('yield-on-cost-value');
    await expect(figure, `${label}: the YOC cell shows a figure`).toBeVisible({timeout: 15_000});
    await expect.poll(async () => digitsOf(await figure.textContent()), {timeout: 10_000, message: `${label}: the YOC cell reads ${oracle.digits} once separators and % are dropped`}).toBe(oracle.digits);
    await expect(figure, `${label}: a yield on cost carries no sign`).not.toHaveText(/[+\-−]/);
    // The figure above is the presence barrier: these absences are about this cell, not about a slow page.
    await expect(cell.getByTestId('yield-on-cost-unavailable'), `${label}: not the unavailable dash`).toHaveCount(0);
    await expect(cell.getByTestId('yield-on-cost-no-income'), `${label}: not the no-income dash`).toHaveCount(0);
}

/** The YOC cell of `row` shows the unavailable dash with its info icon, and no figure — not even a zero. */
async function expectYieldOnCostUnavailable(row: Locator, label: string): Promise<void> {
    const cell = yieldOnCostCell(row);
    const dash = cell.getByTestId('yield-on-cost-unavailable');
    await expect(dash, `${label}: the YOC cell shows the unavailable state`).toBeVisible({timeout: 15_000});
    await expect(dash, `${label}: a dash, a symbol and not a translation`).toHaveText('-', {timeout: 10_000});
    await expect(cell.getByTestId('yield-on-cost-info'), `${label}: with the info icon of an unavailable value (a no-income dash has none)`).toBeVisible({timeout: 10_000});
    // The dash above is the presence barrier: these absences are about this cell, not about a slow page.
    await expect(cell.getByTestId('yield-on-cost-value'), `${label}: no figure`).toHaveCount(0);
    await expect(cell.getByTestId('yield-on-cost-no-income'), `${label}: not the no-income dash`).toHaveCount(0);
    await expect(cell, `${label}: no digit anywhere in the cell, not even a zero`).not.toHaveText(/\d/);
}

test.describe('Yield on Cost on real data — release 1.2, gap 4', () => {
    test('Y1 — per (asset, broker), anchored at the report end: one asset at two brokers shows two exact YOCs, on the Dashboard and on the broker page', async ({page, request, owned}) => {
        test.setTimeout(180_000);
        const depositDay = daysAgoIso(130);
        const buyDay = daysAgoIso(120);
        const dividendDay = daysAgoIso(100);
        const period = dashboardPeriod();
        expect(dividendDay < period.start && dividendDay >= daysAgoIso(WINDOW_START_DAYS_BEFORE_END), 'design: the dividends are inside the YOC window and before the dashboard period').toBe(true);
        // Broker A: 10 units for 1000 EUR (WAC 100) and a 30 EUR dividend, 30 / 10 / 100 = 3.00%.
        // Broker B:  8 units for 1000 EUR (WAC 125) and a 12 EUR dividend, 12 /  8 / 125 = 1.20%.
        // One YOC per asset would read (30 + 12) / 18 / (2000 / 18) = 2.10% on both rows.
        const oracleA = yieldOnCostOracle([{amount: 30, eligibleQuantity: 10, laterSplitRatio: 1}], 100);
        const oracleB = yieldOnCostOracle([{amount: 12, eligibleQuantity: 8, laterSplitRatio: 1}], 125);

        const {assetId, brokerA, brokerB} = await test.step('seed: one EUR asset bought at two brokers at different costs, each with its own dividend, before the dashboard period', async () => {
            await openAccount(page, request, owned, 'yoc1');
            const suffix = uniqueSuffix();
            const brokerA = await createBroker(page, owned, `yoc-a-broker-${suffix}`);
            const brokerB = await createBroker(page, owned, `yoc-b-broker-${suffix}`);
            const assetId = await createManualAsset(page, owned, `YOC two brokers ${suffix}`);
            await seedPrices(page, assetId, [
                {date: buyDay, close: 100},
                {date: daysAgoIso(5), close: 110},
            ]);
            await commitTransactions(
                page,
                {
                    creates: [
                        {broker_id: brokerA, type: 'DEPOSIT', date: depositDay, cash: {code: 'EUR', amount: '5000'}, description: `yoc-real funding A ${suffix}`},
                        {broker_id: brokerB, type: 'DEPOSIT', date: depositDay, cash: {code: 'EUR', amount: '5000'}, description: `yoc-real funding B ${suffix}`},
                        {broker_id: brokerA, asset_id: assetId, type: 'BUY', date: buyDay, quantity: '10', cash: {code: 'EUR', amount: '-1000'}, description: `yoc-real purchase A ${suffix}`},
                        {broker_id: brokerB, asset_id: assetId, type: 'BUY', date: buyDay, quantity: '8', cash: {code: 'EUR', amount: '-1000'}, description: `yoc-real purchase B ${suffix}`},
                        {broker_id: brokerA, asset_id: assetId, type: 'DIVIDEND', date: dividendDay, cash: {code: 'EUR', amount: '30'}, description: `yoc-real dividend A ${suffix}`},
                        {broker_id: brokerB, asset_id: assetId, type: 'DIVIDEND', date: dividendDay, cash: {code: 'EUR', amount: '12'}, description: `yoc-real dividend B ${suffix}`},
                    ],
                },
                'commit the funding, the two purchases and the two dividends',
            );
            return {assetId, brokerA, brokerB};
        });

        const report = await test.step('open the dashboard on a period that starts after the dividends', () => openDashboard(page, period));

        await test.step('the report: each (asset, broker) row has its own YOC, exactly the oracle, on a window ending at the report end', async () => {
            const holdingA = holdingOf(report, assetId, brokerA);
            const holdingB = holdingOf(report, assetId, brokerB);
            expect(costBase(holdingA), 'broker A: the cost base the oracle divides by').toEqual({quantity: 10, wac_per_unit: 100});
            expect(costBase(holdingB), 'broker B: the cost base the oracle divides by').toEqual({quantity: 8, wac_per_unit: 125});
            expect(yieldOnCostFacts(holdingA), 'broker A: 30 / 10 / 100').toEqual(availableFacts(oracleA, period, buyDay));
            expect(yieldOnCostFacts(holdingB), 'broker B: 12 / 8 / 125').toEqual(availableFacts(oracleB, period, buyDay));
        });

        const dashboard = page.getByTestId('dashboard-page');
        await test.step('the Dashboard holdings: each row reads its own YOC, in the YOC column', async () => {
            const rowA = positionRow(dashboard, assetId, brokerA);
            const rowB = positionRow(dashboard, assetId, brokerB);
            await showHoldingsTable(dashboard, rowA);
            await expect(rowB, 'the same asset at the second broker is a row of its own').toBeVisible({timeout: 10_000});
            await expectYieldOnCostFigure(rowA, oracleA, 'dashboard, broker A');
            await expectYieldOnCostFigure(rowB, oracleB, 'dashboard, broker B');
        });

        await test.step("the broker page: broker B's holdings read B's own YOC", async () => {
            await page.goto(`/brokers/${brokerB}?tab=posizioni`);
            await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 15_000});
            // Disabled while the broker or its report is loading: the page's busy state.
            await expect(page.getByTestId('broker-refresh')).toBeEnabled({timeout: 30_000});
            const holdings = page.getByTestId('broker-holdings');
            const row = positionRow(holdings, assetId, brokerB);
            await showHoldingsTable(holdings, row);
            await expectYieldOnCostFigure(row, oracleB, 'broker page, broker B');
        });
    });

    test('Y2 — no cost, no YOC (P-10): a position with a dividend but without a purchase cost shows the unavailable dash, never a figure, until its cost is known', async ({page, request, owned}) => {
        test.setTimeout(180_000);
        const d0 = daysAgoIso(60);
        const d1 = daysAgoIso(50);
        const d2 = daysAgoIso(30);
        const d3 = daysAgoIso(20);
        const period = dashboardPeriod();
        // 10 units bought for 1000 EUR, 10 more from a legacy ADJUSTMENT at an unknown cost, then a 40 EUR dividend on
        // 20 units. Once those 10 are given a cost of 0 per unit: WAC 1000 / 20 = 50, YOC 40 / 20 / 50 = 4.00%.
        const healed = yieldOnCostOracle([{amount: 40, eligibleQuantity: 20, laterSplitRatio: 1}], 50);

        const {brokerId, assetId, adjustmentId} = await test.step('seed: a purchase, a legacy ADJUSTMENT-in without a cost (written as an older version stored it), then a dividend', async () => {
            await openAccount(page, request, owned, 'yoc2');
            const user = owned.user;
            if (!user) throw new Error('openAccount registered no account');
            const suffix = uniqueSuffix();
            const brokerId = await createBroker(page, owned, `yoc-cost-broker-${suffix}`);
            const assetId = await createManualAsset(page, owned, `YOC unknown cost ${suffix}`);
            // The helper always writes a TRANSFER pair too: its own broker and asset, owned and deleted like the rest,
            // with a purchase at the source so the transfer out moves units that are there. Nothing asserts on them.
            const sideBroker = await createBroker(page, owned, `yoc-side-broker-${suffix}`);
            const sideAsset = await createManualAsset(page, owned, `YOC side transfer ${suffix}`);
            await seedPrices(page, assetId, [
                {date: d1, close: 100},
                {date: d2, close: 50},
            ]);
            await seedPrices(page, sideAsset, [{date: d1, close: 10}]);
            await commitTransactions(
                page,
                {
                    creates: [
                        {broker_id: brokerId, type: 'DEPOSIT', date: d0, cash: {code: 'EUR', amount: '10000'}, description: `yoc-real funding ${suffix}`},
                        {broker_id: brokerId, asset_id: assetId, type: 'BUY', date: d1, quantity: '10', cash: {code: 'EUR', amount: '-1000'}, description: `yoc-real purchase ${suffix}`},
                        {broker_id: brokerId, asset_id: assetId, type: 'DIVIDEND', date: d3, cash: {code: 'EUR', amount: '40'}, description: `yoc-real dividend ${suffix}`},
                        {broker_id: sideBroker, type: 'DEPOSIT', date: d0, cash: {code: 'EUR', amount: '100'}, description: `yoc-real side funding ${suffix}`},
                        {broker_id: sideBroker, asset_id: sideAsset, type: 'BUY', date: d1, quantity: '2', cash: {code: 'EUR', amount: '-20'}, description: `yoc-real side purchase ${suffix}`},
                    ],
                },
                'commit the funding, the purchases and the dividend',
            );

            const marker = `yoc-real legacy ${suffix}`;
            const legacy = writeLegacyRows({userId: user.id, sourceBroker: sideBroker, destBroker: brokerId, transferAsset: sideAsset, adjustmentAsset: assetId, date: d2, transferQty: 1, adjustmentQty: 10, marker});
            const adjustmentId = legacy.adjustment_in;
            // The precondition, read back through the app rather than taken on the helper's word.
            const saved = await readTransaction(page, adjustmentId);
            expect(
                {
                    type: saved.type,
                    broker_id: saved.broker_id,
                    asset_id: saved.asset_id ?? null,
                    date: saved.date,
                    quantity: Number(saved.quantity),
                    cash: saved.cash ?? null,
                    cost_basis_override: saved.cost_basis_override ?? null,
                    asset_event_id: saved.asset_event_id ?? null,
                    marked: (saved.description ?? '').includes(marker),
                },
                'precondition: an ADJUSTMENT-in of 10 units on this position, with no cost, no cash and no event — the legacy shape the app now refuses',
            ).toEqual({type: 'ADJUSTMENT', broker_id: brokerId, asset_id: assetId, date: d2, quantity: 10, cash: null, cost_basis_override: null, asset_event_id: null, marked: true});
            return {brokerId, assetId, adjustmentId};
        });

        const dashboard = page.getByTestId('dashboard-page');
        const row = positionRow(dashboard, assetId, brokerId);

        await test.step('unknown cost: the report says unavailable / missing_wac with the dividend counted, the cell shows the dash and its info icon', async () => {
            const report = await openDashboard(page, period);
            const holding = holdingOf(report, assetId, brokerId);
            expect(costBase(holding), 'precondition: units of unknown cost leave the average cost unknown').toEqual({quantity: 20, wac_per_unit: null});
            expect(yieldOnCostFacts(holding), 'no cost, no YOC: unavailable for the missing WAC, with the income in the window counted, so not «no income»').toEqual({
                status: 'unavailable',
                reason: 'missing_wac',
                value: null,
                window_start: daysAgoIso(WINDOW_START_DAYS_BEFORE_END),
                window_end: period.end,
                first_pair_transaction_date: d1,
                gross_income_transaction_count: 1,
                gross_income_per_unit: null,
                net_zero: false,
                fx: [],
            });
            await showHoldingsTable(dashboard, row);
            await expectYieldOnCostUnavailable(row, 'unknown cost');
        });

        await test.step('fix: an explicit cost of 0 per unit makes the average cost known, and the YOC the oracle figure', async () => {
            await commitTransactions(page, {updates: [{id: adjustmentId, cost_basis_override: {code: 'EUR', amount: '0'}, cost_basis_mode: 'manual'}]}, 'set a purchase cost of 0 per unit on the ADJUSTMENT');
            const saved = await readTransaction(page, adjustmentId);
            expect({code: saved.cost_basis_override?.code, amount: numberOrNull(saved.cost_basis_override?.amount)}, 'precondition: the cost is stored, and it is zero').toEqual({code: 'EUR', amount: 0});

            const report = await openDashboard(page, period);
            const holding = holdingOf(report, assetId, brokerId);
            expect(costBase(holding), '1000 EUR over 20 units').toEqual({quantity: 20, wac_per_unit: 50});
            expect(yieldOnCostFacts(holding), '40 / 20 / 50').toEqual(availableFacts(healed, period, d1));
            await showHoldingsTable(dashboard, row);
            await expectYieldOnCostFigure(row, healed, 'known cost');
        });
    });
});
