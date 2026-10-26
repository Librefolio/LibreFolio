/**
 * MISSING_COST_BASIS from rows an older version left behind — release checklist item 22 (issue #32).
 *
 * «Quote entrate senza costo di carico: un trasferimento o una rettifica senza costo compare nel banner
 * giallo, con l'asset da sistemare.» Units that arrive without a cost basis count at zero cost, so neither
 * their average cost nor their P&L can be known: the dashboard has to say so, and name the asset to fix.
 *
 * Why a Python helper writes the rows. Today the app refuses to save a TRANSFER, or an ADJUSTMENT adding
 * quantity, without `cost_basis_override` (COST_BASIS_REQUIRED: `transactions/batch_costs.py`), so such rows
 * exist only in data written by older versions. The last path the
 * app left — P-10, an ADJUSTMENT linked to a SPLIT, saved in Auto without a cost, whose event was then retyped —
 * is closed too: the retype is refused while the row has no cost (EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST, pinned by
 * E2 of `data-quality-real.spec.ts`). Here `backend/test_scripts/test_db/legacy_cost_rows.py` writes the rows
 * straight into the lane's test database, the way an old version stored them: a TRANSFER pair linked both
 * ways and an ADJUSTMENT, with no cost basis and no cash. The helper accepts only this lane's test database
 * (TEST_PORT and LIBREFOLIO_TEST_DATA_DIR, exported by playwright.config.ts and inherited by the child
 * process) and only brokers the given account owns as OWNER; every row carries this test's marker. The
 * backend half of the same shapes is proven by `test_portfolio_cost_currency.py` (S7 paired, L4).
 *
 * The contract exercised end to end, on data this test created:
 *   1. the summary report carries one MISSING_COST_BASIS warning naming both assets (ids ascending, as the
 *      backend sorts them) with a navigate_asset CTA; the units that reached broker B have no average cost
 *      and no P&L, while A keeps what it paid — 6 units at 20, worth 6 × 30, so +60;
 *   2. the yellow banner shows that row with exactly one link per asset, each carrying the asset's name;
 *   3. the positions table shows «—» for P&L, P&L % and average cost on both rows at B, digits on A;
 *   4. the lots panel of the transferred asset, opened from the URL, raises the same warning;
 *   5. the adjusted asset's link opens that asset's page;
 *   6. the page of broker B shows the same «—» on both of its rows;
 *   7. an explicit cost of 0 per unit on the ADJUSTMENT takes its asset off the warning, which then names the
 *      transferred asset alone: the adjusted units have an average cost of 0 and a P&L of 5 × 40, digits in
 *      the positions — and still no P&L %, since a cost of 0 is no base for one (`gain_loss_ratio`).
 *
 * Ownership. A disposable account owns the whole dashboard — brokers A and B, the DEPOSIT and the BUY, the
 * helper's three rows — so no neighbour's data enters any count asserted here. Assets and prices are global
 * rows: unique names, deleted by the teardown. Every id is recorded before it is checked; the teardown
 * deletes the brokers with force (their transactions go with them, the helper's rows included), then the
 * assets with their prices, then the account. Nothing is routed or mocked: every response read is real.
 */

import {expect, test as base, type APIRequestContext, type Locator, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {writeLegacyRows} from '../fixtures/legacy-cost-rows';
import type {LegacyRows} from '../fixtures/legacy-cost-rows';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const REPORT_PATH = `${API}/portfolio/report`;
const LOTS_PATH = `${API}/portfolio/lots/analysis`;
/** d0: the deposit; d1: the purchase, priced at its cost; d2: the legacy rows, and the last price. */
const DEPOSIT_DAYS_AGO = 60;
const BUY_DAYS_AGO = 50;
const LEGACY_DAYS_AGO = 30;
const TRANSFER_QTY = 4;
const ADJUSTMENT_QTY = 5;
/** What a figure that cannot be known shows — a dash, never a zero. A symbol, not a translation. */
const UNKNOWN = '—';
/** The positions columns that need a known cost: P&L, P&L % and the average cost per unit (PMC). */
const COST_COLUMNS = ['pnl', 'pnl-percent', 'pmc'] as const;

type Owned = {user: DisposableUser | null; brokerIds: number[]; assetIds: number[]};
type Seeded = {brokerA: number; brokerB: number; assetT: number; assetJ: number; nameT: string; nameJ: string};
type Decimalish = string | number | null | undefined;
type ReportIssue = {code: string; severity: string; cta_action?: string | null; message_params?: Record<string, unknown> | null; affected_asset_ids?: number[]; affected_asset_names?: string[]};
type ReportHolding = {asset_id: number; broker_id: number | null; quantity: Decimalish; wac_per_unit?: Decimalish; gain_loss?: Decimalish; gain_loss_percent?: Decimalish};
type ReportRequestBody = {include_summary?: boolean; date_range?: {start?: string; end?: string}};
type ReportBody = {summary?: {net_worth?: {code: string}; holdings?: ReportHolding[]; data_quality?: {issues?: ReportIssue[]} | null} | null};
type LotsRequestBody = {asset_id?: number; requested_analyses?: string[]};
type LotsBody = {lots?: Array<{lot_id: number}> | null; data_quality?: {issues?: ReportIssue[]} | null; calculation_status?: string | null};
type TxRead = {id: number; broker_id: number; asset_id?: number | null; type: string; date: string; quantity: string; cash?: unknown; related_transaction_id?: number | null; description?: string | null; cost_basis_override?: unknown; asset_event_id?: number | null};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** The dashboard's own report load: the one request that carries the summary. */
function isSummaryReport(req: Request): boolean {
    if (req.method() !== 'POST' || new URL(req.url()).pathname !== REPORT_PATH) return false;
    return (req.postDataJSON() as ReportRequestBody | null)?.include_summary === true;
}

/** The lots panel's main load for `assetId`: the request that asks for the lot summary. */
function isLotsMainFor(req: Request, assetId: number): boolean {
    if (req.method() !== 'POST' || new URL(req.url()).pathname !== LOTS_PATH) return false;
    const body = req.postDataJSON() as LotsRequestBody | null;
    return body?.asset_id === assetId && (body.requested_analyses ?? []).includes('LOT_SUMMARY');
}

/**
 * Delete in dependency order, each step scoped to an id this test recorded.
 *
 * Nothing is routed, but routes are detached first all the same, as in the other owned-account specs.
 * The page is then unmounted so no in-flight reload reads rows while they go. Brokers go first, with
 * force: a broker's transactions — the helper's legacy rows included — are deleted with it, and an asset
 * with transactions cannot be deleted. Brokers and assets are deleted by the account that owns them
 * (`page.request` shares the browser's session); the account itself through the standalone `request`
 * context it was registered with, which signs in on its own.
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
    await attempt('detach routes', async () => {
        await page.unrouteAll({behavior: 'ignoreErrors'});
    });
    await attempt('unmount the app', async () => {
        await page.goto('about:blank');
    });
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean; transactions_deleted?: number | null}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete owned broker and its transactions');
            const deleted = result.results.find((item) => item.id === brokerId);
            expect(deleted?.success).toBe(true);
            console.log(`owned broker #${brokerId} deleted with its ${deleted?.transactions_deleted ?? 0} transactions`);
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete owned asset and its prices');
            expect(result.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
            console.log(`owned asset #${assetId} deleted`);
        });
    }
    const user = owned.user;
    if (user) {
        await attempt(`account ${user.username}`, async () => {
            await deleteDisposableUser(request, user);
            console.log(`account ${user.username} (#${user.id}) deleted`);
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

test.setTimeout(180_000);

/** A broker owned by the signed-in account; its id is recorded for cleanup before it is checked. */
async function createOwnedBroker(page: Page, owned: Owned, name: string): Promise<number> {
    const created = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: daysAgoIso(400)}]}), `create owned broker ${name}`);
    const result = created.results.find((item) => item.name === name);
    if (typeof result?.broker_id === 'number') owned.brokerIds.push(result.broker_id);
    if (!result?.success || typeof result.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(created)}`);
    return result.broker_id;
}

/** A manual EUR asset — no provider, so nothing ever rewrites its prices — with its closes seeded. */
async function createManualAsset(page: Page, owned: Owned, name: string, closes: ReadonlyArray<readonly [string, number]>): Promise<number> {
    const item = {display_name: name, currency: 'EUR', asset_type: 'STOCK', quote_base_quantity: 1, active: true};
    schemas.FAAssetCreateItem.parse(item);
    const created = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>}>(await page.request.post(`${API}/assets`, {data: [item]}), `create owned asset ${name}`);
    const result = created.results.find((entry) => entry.display_name === name);
    if (typeof result?.asset_id === 'number') owned.assetIds.push(result.asset_id);
    if (!result?.success || typeof result.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(created)}`);
    const assetId = result.asset_id;

    const prices = closes.map(([date, close]) => ({date, close, currency: 'EUR'}));
    const seeded = await jsonFrom<{results: Array<{asset_id: number; count: number}>}>(await page.request.post(`${API}/assets/prices`, {data: [{asset_id: assetId, prices}]}), `seed the manual prices of ${name}`);
    expect(seeded.results.find((entry) => entry.asset_id === assetId)?.count).toBe(prices.length);
    return assetId;
}

/**
 * Everything the app still accepts, through its API: brokers A and B, the asset T that will be
 * transferred (20 on d1, 30 on d2) and the asset J that will be adjusted (40 on both days), a DEPOSIT of
 * 1000 EUR at A on d0 and a BUY of 10 T at A for 200 EUR on d1 — a cost basis of 20 per unit.
 */
async function seedThroughTheApi(page: Page, owned: Owned, suffix: string): Promise<Seeded> {
    const brokerA = await createOwnedBroker(page, owned, `legacy-cost-A-${suffix}`);
    const brokerB = await createOwnedBroker(page, owned, `legacy-cost-B-${suffix}`);
    const d1 = daysAgoIso(BUY_DAYS_AGO);
    const d2 = daysAgoIso(LEGACY_DAYS_AGO);
    const nameT = `Legacy transferred E2E ${suffix}`;
    const nameJ = `Legacy adjusted E2E ${suffix}`;
    const assetT = await createManualAsset(page, owned, nameT, [
        [d1, 20],
        [d2, 30],
    ]);
    const assetJ = await createManualAsset(page, owned, nameJ, [
        [d1, 40],
        [d2, 40],
    ]);

    const committed = await jsonFrom<{committed: boolean; issues?: unknown[]}>(
        await page.request.post(`${API}/transactions/commit`, {
            data: {
                creates: [
                    {broker_id: brokerA, type: 'DEPOSIT', date: daysAgoIso(DEPOSIT_DAYS_AGO), cash: {code: 'EUR', amount: '1000'}, description: `legacy-cost funding ${suffix}`},
                    {broker_id: brokerA, asset_id: assetT, type: 'BUY', date: d1, quantity: '10', cash: {code: 'EUR', amount: '-200'}, description: `legacy-cost purchase ${suffix}`},
                ],
            },
        }),
        'commit the owned DEPOSIT and BUY',
    );
    expect(committed.committed, `the owned transactions were rolled back: ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
    return {brokerA, brokerB, assetT, assetJ, nameT, nameJ};
}

/**
 * The precondition, read back through the app rather than taken on the helper's word: the three rows are
 * the legacy shape the app now refuses — no cost basis, no cash, no asset event, the pair linked both
 * ways — at the brokers and on the date asked, and they carry this test's marker.
 */
async function expectLegacyShape(page: Page, rows: LegacyRows, seeded: Seeded, date: string, marker: string): Promise<void> {
    const ids = [rows.transfer_out, rows.transfer_in, rows.adjustment_in];
    const query = new URLSearchParams(ids.map((id) => ['ids', String(id)]));
    const read = await jsonFrom<TxRead[]>(await page.request.get(`${API}/transactions?${query.toString()}`), 'read the legacy rows back');
    const shape = read.map((tx) => ({
        id: tx.id,
        type: tx.type,
        broker_id: tx.broker_id,
        asset_id: tx.asset_id ?? null,
        date: tx.date,
        quantity: Number(tx.quantity),
        cash: tx.cash ?? null,
        cost_basis_override: tx.cost_basis_override ?? null,
        asset_event_id: tx.asset_event_id ?? null,
        related_transaction_id: tx.related_transaction_id ?? null,
        marked: (tx.description ?? '').includes(marker),
    }));
    const legacy = {date, cash: null, cost_basis_override: null, asset_event_id: null, marked: true};
    expect(shape, 'precondition: the helper wrote the legacy shape, and the app reads it back as such').toEqual([
        {...legacy, id: rows.transfer_out, type: 'TRANSFER', broker_id: seeded.brokerA, asset_id: seeded.assetT, quantity: -TRANSFER_QTY, related_transaction_id: rows.transfer_in},
        {...legacy, id: rows.transfer_in, type: 'TRANSFER', broker_id: seeded.brokerB, asset_id: seeded.assetT, quantity: TRANSFER_QTY, related_transaction_id: rows.transfer_out},
        {...legacy, id: rows.adjustment_in, type: 'ADJUSTMENT', broker_id: seeded.brokerB, asset_id: seeded.assetJ, quantity: ADJUSTMENT_QTY, related_transaction_id: null},
    ]);
}

/** The holding of `assetId` at `brokerId`: exactly one, since the account owns the whole dashboard. */
function holdingAt(holdings: ReportHolding[], assetId: number, brokerId: number): ReportHolding {
    const rows = holdings.filter((holding) => holding.asset_id === assetId && holding.broker_id === brokerId);
    expect(rows, `one holding of asset ${assetId} at broker ${brokerId}`).toHaveLength(1);
    return rows[0];
}

/** The figures of a holding as numbers — Decimals travel as strings — with null kept as null. */
function figures(holding: ReportHolding) {
    const asNumber = (value: Decimalish): number | null => (value == null ? null : Number(value));
    return {quantity: asNumber(holding.quantity), wac_per_unit: asNumber(holding.wac_per_unit), gain_loss: asNumber(holding.gain_loss), gain_loss_percent: asNumber(holding.gain_loss_percent)};
}

/**
 * Open a collapsed-by-default issue list and make sure it *stays* open.
 *
 * The owner re-renders when its data lands, so a single click can land on a header that is about to be
 * replaced. Toggle only when collapsed, until `aria-expanded` sticks — never a blind click.
 */
async function expandStrict(toggle: Locator): Promise<void> {
    await expect(toggle).toBeVisible({timeout: 20_000});
    await expect(async () => {
        if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
        expect(await toggle.getAttribute('aria-expanded')).toBe('true');
    }).toPass({timeout: 15_000});
}

/**
 * Show a column the holdings table hides by default (the PMC is one) through the panel's own column menu.
 * The menu item is a toggle, so the column's absence is read first — on a header row already proven drawn
 * — and the item is clicked only then; the header's presence is the proof either way.
 */
async function revealColumn(page: Page, panel: Locator, table: Locator, columnId: string): Promise<void> {
    const header = table.getByTestId(`dt-header-${columnId}`);
    if ((await header.count()) === 0) {
        await panel.getByTestId('positions-column-visibility-toggle').getByTestId('column-visibility-toggle').click();
        const menu = page.getByTestId('column-visibility-dropdown');
        await expect(menu).toBeVisible();
        await menu.getByTestId(`column-visibility-item-${columnId}`).click();
        await expect(header).toBeVisible();
        // The menu closes on a click outside it, which lands on its own full-screen backdrop; the menu keeps
        // at least 8px from every edge, so the corner is always outside it.
        await page.mouse.click(2, 2);
        await expect(menu).toBeHidden();
    }
    await expect(header).toBeVisible();
}

test.describe('MISSING_COST_BASIS from legacy rows — dashboard (item 22)', () => {
    test('a TRANSFER pair and an ADJUSTMENT stored without cost basis by an older version reach the banner, the positions, the lots panel and the broker page — and a cost of 0 takes the ADJUSTMENT off the banner', async ({page, request, owned}) => {
        // The account owns the whole dashboard; its guides are skipped so no overlay covers the banner.
        const user = await registerDisposableUser(request, 'legacy');
        owned.user = user;
        await prepareOnboardingAccount(page, user, []);
        const suffix = uniqueSuffix();
        const seeded = await seedThroughTheApi(page, owned, suffix);
        const {brokerA, brokerB, assetT, assetJ, nameT, nameJ} = seeded;

        // What the app no longer accepts, written as an old version left it.
        const legacyDate = daysAgoIso(LEGACY_DAYS_AGO);
        const marker = `legacy-cost-rows ${suffix}`;
        const legacy = writeLegacyRows({userId: user.id, sourceBroker: brokerA, destBroker: brokerB, transferAsset: assetT, adjustmentAsset: assetJ, date: legacyDate, transferQty: TRANSFER_QTY, adjustmentQty: ADJUSTMENT_QTY, marker});
        await expectLegacyShape(page, legacy, seeded, legacyDate, marker);

        // Full load: a fresh document, so neither the report nor the lots analysis can come from a client
        // cache; the backend's caches are keyed on the transactions themselves, the helper's rows included.
        // The dashboard left open by the onboarding is unmounted first, so every response awaited below
        // belongs to the new document — none can predate the legacy rows.
        await page.goto('about:blank');
        const reportWait = page.waitForResponse((response) => isSummaryReport(response.request()), {timeout: 30_000});
        const lotsWait = page.waitForResponse((response) => isLotsMainFor(response.request(), assetT), {timeout: 30_000});
        await page.goto(`/dashboard?tab=posizioni&asset=${assetT}&start=${daysAgoIso(90)}&end=${todayIso()}`);
        const [reportResponse, lotsResponse] = await Promise.all([reportWait, lotsWait]);
        expect((reportResponse.request().postDataJSON() as ReportRequestBody).date_range?.end, 'precondition: the dashboard range ends today').toBe(todayIso());
        const summary = (await jsonFrom<ReportBody>(reportResponse, 'dashboard report')).summary;
        expect(summary?.net_worth?.code, 'precondition: the dashboard reports in EUR, the currency of every amount written').toBe('EUR');

        // 1. The report: one warning naming both assets, ids ascending as the backend sorts them.
        const issues = summary?.data_quality?.issues ?? [];
        const costIssues = issues.filter((issue) => issue.code === 'MISSING_COST_BASIS');
        // The account owns the whole dashboard, so "one issue" is a count this test created.
        expect(costIssues, `item 22: the report must carry one MISSING_COST_BASIS issue; it carries ${JSON.stringify(issues.map((issue) => issue.code))}`).toHaveLength(1);
        const affected = [
            {id: assetT, name: nameT},
            {id: assetJ, name: nameJ},
        ].sort((left, right) => left.id - right.id);
        expect(costIssues[0]).toMatchObject({severity: 'warning', cta_action: 'navigate_asset', affected_asset_ids: affected.map((asset) => asset.id), affected_asset_names: affected.map((asset) => asset.name)});
        expect(costIssues[0].message_params).toEqual({count: 2});

        const holdings = summary?.holdings ?? [];
        expect(figures(holdingAt(holdings, assetT, brokerA)), 'A keeps what it paid: 6 units at 20, worth 6 × 30').toEqual({quantity: 6, wac_per_unit: 20, gain_loss: 60, gain_loss_percent: 0.5});
        expect(figures(holdingAt(holdings, assetT, brokerB)), 'the 4 units transferred to B have no known cost').toEqual({quantity: TRANSFER_QTY, wac_per_unit: null, gain_loss: null, gain_loss_percent: null});
        expect(figures(holdingAt(holdings, assetJ, brokerB)), 'the 5 units adjusted in at B have no known cost').toEqual({quantity: ADJUSTMENT_QTY, wac_per_unit: null, gain_loss: null, gain_loss_percent: null});

        // 2. The yellow banner: the issue row, with one link per asset to fix.
        const dashboard = page.getByTestId('dashboard-page');
        await waitForSettled(dashboard, 25_000);
        const banner = page.getByTestId('data-quality-banner');
        await expandStrict(banner.getByTestId('data-quality-toggle'));
        const row = banner.getByTestId('data-quality-issue-MISSING_COST_BASIS');
        await expect(row).toBeVisible({timeout: 10_000});
        await expect(row).toHaveAttribute('data-severity', 'warning');
        // One link per affected asset, and the dashboard is this test's own: two is a count it created.
        const links = row.getByTestId('data-quality-nav-assets-MISSING_COST_BASIS').locator('[data-testid^="data-quality-nav-asset-"]');
        await expect(links).toHaveCount(2);
        await expect(row.getByTestId(`data-quality-nav-asset-${assetT}`)).toHaveText(nameT);
        await expect(row.getByTestId(`data-quality-nav-asset-${assetJ}`)).toHaveText(nameJ);

        // 4. The lots panel of T, opened by the `asset` parameter: the same warning, from the same rows. The URL opens
        //    the lot detail alone (Y5-2): the positions panel is not on the page until «← Portfolio» is pressed (step 3).
        const lotsPanel = page.getByTestId('lots-analysis-panel');
        const panel = page.getByTestId('positions-panel');
        await expect(lotsPanel).toBeVisible({timeout: 15_000});
        await expect(panel, 'the lot detail replaces the portfolio view: no positions panel beside it').toHaveCount(0);
        const lots = await jsonFrom<LotsBody>(lotsResponse, 'lots analysis of the transferred asset');
        const lotIssues = (lots.data_quality?.issues ?? []).filter((issue) => issue.code === 'MISSING_COST_BASIS');
        // The analysis covers one asset of this test's own: one issue is a count it created.
        expect(lotIssues, `the lots analysis must carry MISSING_COST_BASIS; it carries ${JSON.stringify((lots.data_quality?.issues ?? []).map((issue) => issue.code))}`).toHaveLength(1);
        expect(lotIssues[0]).toMatchObject({severity: 'warning', affected_asset_ids: [assetT]});
        // L4: an unknown cost in the average-cost lines is isolable — DEGRADED, never FAILED.
        expect(lots.calculation_status).toBe('DEGRADED');
        // The witness: the lots of this very response are on screen, so the panel is showing its answer.
        const lotIds = (lots.lots ?? []).map((lot) => lot.lot_id);
        expect(lotIds.length, 'precondition: the BUY opened at least one lot').toBeGreaterThan(0);
        for (const lotId of lotIds) {
            await expect(lotsPanel.getByTestId('unified-lots-table').locator(`tbody tr[data-row-id="${lotId}"]`)).toBeVisible({timeout: 15_000});
        }
        const lotBanner = lotsPanel.getByTestId('lot-data-quality-banner');
        await expandStrict(lotBanner.getByTestId('lot-data-quality-toggle'));
        await expect(lotBanner.getByTestId('lot-data-quality-issue-MISSING_COST_BASIS')).toBeVisible();

        // 3. The positions, holdings × table (both controls are setters, not toggles). The lot detail replaced the
        //    portfolio view (Y5-2): «← Portfolio» brings the positions panel back, and the lots panel goes.
        await page.getByTestId('positions-back-to-portfolio').click();
        await expect(lotsPanel).toBeHidden({timeout: 15_000});
        await expect(panel).toBeVisible({timeout: 15_000});
        await expect(panel).toHaveAttribute('data-busy', 'false', {timeout: 25_000});
        await panel.getByTestId('positions-toggle-holdings').click();
        await panel.getByTestId('positions-toggle-table').click();
        const table = panel.getByTestId('exposure-table');
        await expect(table.getByTestId('dt-header-pnl')).toBeVisible({timeout: 10_000});
        await revealColumn(page, panel, table, 'pmc');
        const cell = (assetId: number, brokerId: number, columnId: string) => table.locator(`tbody tr[data-row-id="${assetId}-${brokerId}"] td[data-column-id="${columnId}"]`);
        for (const columnId of COST_COLUMNS) {
            await expect(cell(assetT, brokerB, columnId), `${columnId} of the units transferred to B`).toHaveText(UNKNOWN);
            await expect(cell(assetJ, brokerB, columnId), `${columnId} of the units adjusted in at B`).toHaveText(UNKNOWN);
            await expect(cell(assetT, brokerA, columnId), `${columnId} of the units A paid for`).toHaveText(/\d/);
        }

        // 5. The adjusted asset's link opens its page.
        await expandStrict(banner.getByTestId('data-quality-toggle'));
        await row.getByTestId(`data-quality-nav-asset-${assetJ}`).click();
        await expect(page).toHaveURL(new RegExp(`/assets/${assetJ}(?:[/?#]|$)`), {timeout: 15_000});
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 15_000});

        // 6. The page of broker B: the same «—» on both of its rows, in the positions panel of its own holdings.
        await page.goto(`/brokers/${brokerB}?tab=posizioni`);
        await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 15_000});
        // Disabled while the broker or its report is loading: the page's busy state.
        await expect(page.getByTestId('broker-refresh')).toBeEnabled({timeout: 25_000});
        const brokerPanel = page.getByTestId('broker-holdings').getByTestId('positions-panel');
        await expect(brokerPanel).toHaveAttribute('data-busy', 'false', {timeout: 25_000});
        await brokerPanel.getByTestId('positions-toggle-holdings').click();
        await brokerPanel.getByTestId('positions-toggle-table').click();
        const brokerTable = brokerPanel.getByTestId('exposure-table');
        await expect(brokerTable.getByTestId('dt-header-pnl')).toBeVisible({timeout: 10_000});
        await revealColumn(page, brokerPanel, brokerTable, 'pmc');
        const brokerCell = (assetId: number, columnId: string) => brokerTable.locator(`tbody tr[data-row-id="${assetId}-${brokerB}"] td[data-column-id="${columnId}"]`);
        for (const columnId of COST_COLUMNS) {
            await expect(brokerCell(assetT, columnId), `broker page, ${columnId} of the units transferred to B`).toHaveText(UNKNOWN);
            await expect(brokerCell(assetJ, columnId), `broker page, ${columnId} of the units adjusted in at B`).toHaveText(UNKNOWN);
        }

        // 7. The fix the banner asks for: an explicit cost of 0 per unit on the ADJUSTMENT. J leaves the warning,
        //    which then names T alone; J's units get an average cost (0) and a P&L (5 × 40), and still no P&L %:
        //    a cost of 0 is no base for one (`gain_loss_ratio`), so that cell keeps its «—».
        const fix = await jsonFrom<{committed: boolean; issues?: unknown[]}>(
            await page.request.post(`${API}/transactions/commit`, {data: {updates: [{id: legacy.adjustment_in, cost_basis_override: {code: 'EUR', amount: '0'}, cost_basis_mode: 'manual'}]}}),
            'set a purchase cost of 0 per unit on the legacy ADJUSTMENT',
        );
        expect(fix.committed, `the cost of 0 was rolled back: ${JSON.stringify(fix.issues ?? [])}`).toBe(true);
        const fixedRows = await jsonFrom<TxRead[]>(await page.request.get(`${API}/transactions?ids=${legacy.adjustment_in}`), 'read the legacy ADJUSTMENT back');
        const storedCost = fixedRows.find((tx) => tx.id === legacy.adjustment_in)?.cost_basis_override as {code?: string; amount?: string} | null | undefined;
        expect({code: storedCost?.code, amount: storedCost?.amount == null ? null : Number(storedCost.amount)}, 'precondition: the cost is stored, and it is zero').toEqual({code: 'EUR', amount: 0});

        // A fresh document again: no response awaited below can predate the cost.
        await page.goto('about:blank');
        const fixedReportWait = page.waitForResponse((response) => isSummaryReport(response.request()), {timeout: 30_000});
        await page.goto(`/dashboard?tab=posizioni&start=${daysAgoIso(90)}&end=${todayIso()}`);
        const fixedSummary = (await jsonFrom<ReportBody>(await fixedReportWait, 'dashboard report after the cost of 0')).summary;
        const fixedIssues = fixedSummary?.data_quality?.issues ?? [];
        const fixedCostIssues = fixedIssues.filter((issue) => issue.code === 'MISSING_COST_BASIS');
        // Still the account's own dashboard: one issue is a count this test created.
        expect(fixedCostIssues, `the report must still carry one MISSING_COST_BASIS issue, for T; it carries ${JSON.stringify(fixedIssues.map((issue) => issue.code))}`).toHaveLength(1);
        expect(fixedCostIssues[0]).toMatchObject({severity: 'warning', cta_action: 'navigate_asset', affected_asset_ids: [assetT], affected_asset_names: [nameT]});
        expect(fixedCostIssues[0].message_params).toEqual({count: 1});
        const fixedHoldings = fixedSummary?.holdings ?? [];
        expect(figures(holdingAt(fixedHoldings, assetJ, brokerB)), 'the 5 units adjusted in at B cost 0 now: an average of 0, a P&L of 5 × 40, no P&L % on a base of 0').toEqual({quantity: ADJUSTMENT_QTY, wac_per_unit: 0, gain_loss: 200, gain_loss_percent: null});
        expect(figures(holdingAt(fixedHoldings, assetT, brokerB)), 'the 4 units transferred to B are still of unknown cost').toEqual({quantity: TRANSFER_QTY, wac_per_unit: null, gain_loss: null, gain_loss_percent: null});

        // The banner: the same row, with T's link alone.
        await waitForSettled(dashboard, 25_000);
        await expandStrict(banner.getByTestId('data-quality-toggle'));
        await expect(row).toBeVisible({timeout: 10_000});
        await expect(links).toHaveCount(1);
        await expect(row.getByTestId(`data-quality-nav-asset-${assetT}`)).toHaveText(nameT);
        // The positions: J's average cost and P&L are figures, its P&L % still «—»; T's three still «—».
        await expect(panel).toHaveAttribute('data-busy', 'false', {timeout: 25_000});
        await panel.getByTestId('positions-toggle-holdings').click();
        await panel.getByTestId('positions-toggle-table').click();
        await expect(table.getByTestId('dt-header-pnl')).toBeVisible({timeout: 10_000});
        await revealColumn(page, panel, table, 'pmc');
        await expect(cell(assetJ, brokerB, 'pmc'), 'the average cost of the units adjusted in at B: 0, a figure').toHaveText(/\d/);
        await expect(cell(assetJ, brokerB, 'pnl'), 'the P&L of the units adjusted in at B: a figure').toHaveText(/\d/);
        await expect(cell(assetJ, brokerB, 'pnl-percent'), 'the P&L % of the units adjusted in at B: no base on a cost of 0').toHaveText(UNKNOWN);
        for (const columnId of COST_COLUMNS) await expect(cell(assetT, brokerB, columnId), `${columnId} of the units transferred to B: still unknown`).toHaveText(UNKNOWN);
    });
});
