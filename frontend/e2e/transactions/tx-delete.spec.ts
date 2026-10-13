/**
 * Transaction Delete E2E Tests — Phase 07 · Part 4 · Round 6 · Plan B23
 *
 * T4 (2026-09): the dedicated TransactionDeleteModal no longer exists. A
 * single-row delete now routes through the bulk workspace
 * (`bulkIntent = {action: 'delete', txIds: [row.id]}`), which:
 *   - pre-marks the staged row(s) for deletion (the row's status cell,
 *     `tx-bulk-row-status` with `data-status="delete"`),
 *   - auto-includes a linked partner when it is in the store
 *     (resolveInitialRows) and collapses the pair into one row,
 *   - shows the split hint (`tx-bulk-split-hint`) when a paired delete is
 *     staged,
 *   - surfaces a refused commit inline (`tx-bulk-error` + `tx-bulk-issues`),
 *     including the backend linked-pair guard `pairDeleteIncomplete`
 *     (localized via `transactions.errors.pairDeleteIncomplete`).
 *
 * Coverage vs Test Walk (plan-phase07-transaction-Part4_Round6_PlanB_TestWalkPhase2),
 * re-mapped onto the bulk workspace:
 *
 * Part A — single-row delete through the bulk workspace:
 *   A1 (standalone open/cancel)   → deleteStandalone*
 *   A2 (paired, collapsed + hint) → deletePaired*
 *   A4 (Layout C viewer blocked)  → deleteGuardViewer
 *   A5 (Layout C hidden blocked)  → deleteGuardHidden
 *   A6 (Bulk delete)              → bulkDelete*
 *   committed:false error banner  → deleteFailure
 *
 * Part B — TransactionPickerModal:
 *   B1-B4 (Picker guard)          → pickerDisabled*
 *
 * Part C — Action visibility:
 *   C1-C2 (Context menu + actions)→ actionVisibility*
 *
 * Part D — Regressions:
 *   D1-D8 covered by tx-broker-access.spec.ts + transactions-table.spec.ts
 *
 * Prerequisites: backend test mode (port 6041), mock data populated.
 * Mock data contract — read here, never written: populate_mock_data.py creates
 *   - "delete-safe" tagged TX: the DEPOSIT on IB and the TRANSFER ETH IB↔Coinbase pair,
 *     which A1 and A2 stage for deletion and cancel. The pair must survive: A2 asserts
 *     it does, and tx-bulk-suggest-ux / tx-crud-full / tx-split-promote all read it.
 *   - "access-test" tagged TX: Asym-a (IB↔Directa), Asym-b (IB↔Coinbase),
 *     Asym-c (IB↔DEGIRO=viewer), Asym-d (IB↔Hidden)
 *
 * The three tests that commit touch no mock row and leave nothing behind:
 *   - A1-confirm and A2-confirm delete rows of their own — a funded FEE, a linked
 *     TRANSFER pair — on a disposable account (brokers it owns; the seeded Ethereum,
 *     only read), and delete the account afterwards, its brokers and every row on
 *     them included. They used to consume the seed's "[delete-safe] Platform fee"
 *     FEE and its "delete-consume" pair, so the database never returned to the seed;
 *     nothing here reads those rows any more.
 *   - A1-error refuses a delete on a broker and an asset of its own (TEST_USER), and
 *     deletes its rows, then the broker, then the asset, by id.
 */
import {randomUUID} from 'crypto';
import {expect, test, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {appears} from '../fixtures/probe';
import {maximisePageSize} from '../fixtures/paging';
import {uniqueSuffix} from '../fixtures/unique';
import {daysAgoIso} from '../fixtures/dates';
import {createOwnedBroker, deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';

test.setTimeout(25_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions?page_size=200');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    // The table being VISIBLE is not the table being LOADED: it renders empty
    // and fills in. The page publishes data-busy, so wait on that instead.
    await waitForSettled(page.getByTestId('transactions-page'));
}

/** Find a row whose text content contains ALL given substrings. Returns null if not found. */
async function findRow(page: Page, ...substrings: string[]): Promise<Locator | null> {
    const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const text = (await row.textContent()) ?? '';
        if (substrings.every((s) => text.includes(s))) return row;
    }
    return null;
}

/** Click the delete action (kebab menu → "Remove"/delete item) on a row. */
async function clickDeleteOnRow(row: Locator) {
    const page = row.page();
    await row.hover();
    const kebabBtn = row.getByTestId(/^row-actions-/);
    await expect(kebabBtn).toBeVisible({timeout: 3_000});
    await kebabBtn.click();
    await page.getByTestId('context-menu-action-delete').click();
}

/**
 * T4: a single-row delete opens the bulk workspace (`tx-bulk-modal`) with the
 * row already staged as a delete. Returns the modal, settled (the workspace
 * validates on open; sampling it mid-validation is a race).
 */
async function openDeleteWorkspace(row: Locator): Promise<Locator> {
    const page = row.page();
    await clickDeleteOnRow(row);
    const modal = page.getByTestId('tx-bulk-modal');
    await expect(modal).toBeVisible({timeout: 5_000});
    await waitForSettled(modal.getByTestId('tx-bulk-modal-root'));
    return modal;
}

/** The rows staged in the open bulk workspace. */
function bulkRows(page: Page): Locator {
    return page.locator('[data-testid="tx-bulk-body"] tr[data-row-id]');
}

/**
 * The staged rows that are marked for deletion, read from the state each row publishes
 * in its status cell — never from the tint class that paints it.
 */
function bulkDeletedRows(page: Page): Locator {
    return bulkRows(page).filter({has: page.locator('[data-testid="tx-bulk-row-status"][data-status="delete"]')});
}

/**
 * Commit the open bulk workspace and return the wire payload + committed flag.
 * The commit endpoint (POST /transactions/commit) is the only write channel —
 * there is no DELETE call to intercept anymore (T4).
 */
async function commitDeleteWorkspace(page: Page): Promise<{payload: {deletes?: number[]}; committed: boolean}> {
    const commitBtn = page.getByTestId('tx-bulk-commit');
    await expect(commitBtn).toBeEnabled({timeout: 8_000});

    const requestPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});

    await commitBtn.click();

    const request = await requestPromise;
    const payload = request.postDataJSON() as {deletes?: number[]};
    const body = (await (await responsePromise).json()) as {committed?: boolean};
    return {payload, committed: body.committed === true};
}

/** Count visible row actions by opening the kebab's context menu (hover first to reveal the kebab). */
async function countVisibleActions(row: Locator): Promise<number> {
    const page = row.page();
    await row.hover();
    const kebabBtn = row.getByTestId(/^row-actions-/);
    if (!(await appears(kebabBtn))) return 0;
    await kebabBtn.click();
    const menu = page.locator('[data-testid="context-menu"]');
    await expect(menu).toBeVisible({timeout: 3_000});
    const count = await menu.locator('[data-testid^="context-menu-action-"]').count();
    await page.keyboard.press('Escape');
    return count;
}

// ---------------------------------------------------------------------------
// Owned data — for the three tests that commit
// ---------------------------------------------------------------------------

const API = '/api/v1';

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type CommitBody = {committed: boolean; issues?: unknown[]; results?: Array<{operation: string; index: number; ids: number[]}>};
type TxRead = {id: number; related_transaction_id?: number | null};
/** What a -confirm test created, recorded the moment it exists so the cleanup finds all of it. */
type OwnedAccount = {user: DisposableUser | null; brokerIds: number[]};
/** A standalone FEE and the deposit that funds it, on the account's one broker. */
type OwnedFee = {feeId: number; depositId: number};
/** A saved asset TRANSFER between the account's two brokers (`fromId` sends), and the rows that funded the sender. */
type OwnedPair = {fromId: number; toId: number; fundingIds: number[]};
/** What A1-error creates as TEST_USER — its rows, its broker, its asset — recorded the moment each id exists. */
type OwnedRows = {transactionIds: number[]; brokerIds: number[]; assetIds: number[]};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    return (await response.json()) as T;
}

/** Commit `creates` as one batch; returns the id of each create, in request order. */
async function commitCreates(page: Page, creates: Array<Record<string, unknown>>, purpose: string): Promise<number[]> {
    const body = await jsonFrom<CommitBody>(await page.request.post(`${API}/transactions/commit`, {data: {creates}}), purpose);
    expect(body.committed, `${purpose}: rolled back — ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    return creates.map((_, index) => {
        const id = body.results?.find((item) => item.operation === 'create' && item.index === index)?.ids[0];
        if (typeof id !== 'number') throw new Error(`${purpose}: the commit returned no id for create #${index} — ${JSON.stringify(body.results)}`);
        return id;
    });
}

/** The transactions among `ids` that the server still has — asked by id, never counted by text. */
async function readTransactions(page: Page, ids: number[]): Promise<TxRead[]> {
    return jsonFrom<TxRead[]>(await page.request.get(`${API}/transactions?${ids.map((id) => `ids=${id}`).join('&')}`), `read transactions ${ids.join(', ')}`);
}

function sortedIds(ids: number[]): number[] {
    return [...ids].sort((a, b) => a - b);
}

/** The seeded asset with this exact ticker — read, never assumed. */
async function seededAssetId(page: Page, ticker: string): Promise<number> {
    const assets = await jsonFrom<Array<{id: number}>>(await page.request.get(`${API}/assets/query?ticker=${encodeURIComponent(ticker)}`), `look up the ${ticker} asset`);
    if (assets.length !== 1) throw new Error(`Expected exactly one asset with ticker ${ticker}, found ${assets.length} — check populate_mock_data.py`);
    return assets[0].id;
}

/** A disposable account, through the real welcome, with no guide left due to compete for the overlay. */
async function openAccount(page: Page, request: APIRequestContext, owned: OwnedAccount, tag: string): Promise<void> {
    owned.user = await registerDisposableUser(request, tag);
    await prepareOnboardingAccount(page, owned.user, []);
}

/**
 * A disposable account holding one standalone FEE on a broker it owns.
 *
 * Why not the seeded "[delete-safe] Platform fee": a committed delete is final — no API
 * call brings a row back with its id — so the seed's FEE was single-use, and after every
 * run the database no longer matched the seed. Rows on an account of its own are
 * invisible to every other spec, and deleting its broker takes them all.
 *
 * The broker is funded first, so neither creating the FEE nor deleting it goes anywhere
 * near a balance limit.
 */
async function openAccountWithFee(page: Page, request: APIRequestContext, owned: OwnedAccount, tag: string): Promise<OwnedFee> {
    await openAccount(page, request, owned, tag);
    const broker = await createOwnedBroker(page, tag, owned.brokerIds);
    const [depositId, feeId] = await commitCreates(
        page,
        [
            {broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(3), cash: {code: 'EUR', amount: '100'}, description: `Funding ${tag}`},
            {broker_id: broker.id, type: 'FEE', date: daysAgoIso(2), cash: {code: 'EUR', amount: '-5.50'}, description: `Platform fee ${tag}`},
        ],
        'commit the funded FEE',
    );

    // The premise, read back rather than inferred: the FEE is saved, and stands alone.
    const saved = (await readTransactions(page, [feeId])).map((tx) => [tx.id, tx.related_transaction_id ?? null]);
    expect(saved, 'premise: A1-confirm is about a standalone row').toEqual([[feeId, null]]);
    return {feeId, depositId};
}

/**
 * A disposable account holding one saved asset TRANSFER between two brokers it owns.
 *
 * Why not the seeded "delete-consume" pair: same reason as the FEE above — it was
 * single-use by construction, and the database never returned to the seed.
 *
 * The sender is funded first — a deposit, then a buy — so neither the transfer nor its
 * deletion takes a balance below zero. The asset is the seeded Ethereum, which this test
 * only reads.
 */
async function openAccountWithPair(page: Page, request: APIRequestContext, owned: OwnedAccount, tag: string): Promise<OwnedPair> {
    await openAccount(page, request, owned, tag);
    const giver = await createOwnedBroker(page, `${tag}-from`, owned.brokerIds);
    const receiver = await createOwnedBroker(page, `${tag}-to`, owned.brokerIds);
    const assetId = await seededAssetId(page, 'ETH-USD');

    const fundingIds = await commitCreates(
        page,
        [
            {broker_id: giver.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '100'}},
            {broker_id: giver.id, asset_id: assetId, type: 'BUY', date: daysAgoIso(9), quantity: '0.01', cash: {code: 'USD', amount: '-30'}},
        ],
        'fund the giver broker',
    );

    const linkUuid = randomUUID();
    const description = `Owned pair ${tag}`;
    const [fromId, toId] = await commitCreates(
        page,
        [
            {broker_id: giver.id, asset_id: assetId, type: 'TRANSFER', date: daysAgoIso(5), quantity: '-0.001', link_uuid: linkUuid, description},
            {broker_id: receiver.id, asset_id: assetId, type: 'TRANSFER', date: daysAgoIso(5), quantity: '0.001', link_uuid: linkUuid, description, cost_basis_mode: 'auto'},
        ],
        'commit the owned TRANSFER pair',
    );

    // The premise, read back rather than inferred: the two halves point at each other.
    const halves = await readTransactions(page, [fromId, toId]);
    const linkOf = new Map(halves.map((tx) => [tx.id, tx.related_transaction_id ?? null] as const));
    expect([linkOf.get(fromId), linkOf.get(toId)], 'premise: the two halves of the owned pair are linked to each other').toEqual([toId, fromId]);
    return {fromId, toId, fundingIds};
}

/**
 * Leave the page, then delete the account: its brokers first — `force` takes their
 * transactions with them, whatever the test left of them — and the account last.
 * Only what this test recorded.
 */
async function cleanupAccount(page: Page, request: APIRequestContext, owned: OwnedAccount): Promise<void> {
    const user = owned.user;
    if (!user) return; // nothing was created: brokers only ever exist under the account
    try {
        // Unmount the page first, so nothing on it reloads the rows while they go.
        await page.goto('about:blank');
    } finally {
        await deleteDisposableUser(request, user, owned.brokerIds);
    }
}

function noOwnedRows(): OwnedRows {
    return {transactionIds: [], brokerIds: [], assetIds: []};
}

/**
 * Delete exactly what was recorded, in the only order the backend accepts: the rows
 * first (the +5 and the −5 net to zero, so the batch is legal), then the broker
 * (`force` takes whatever a failed run left on it), then the asset, which the backend
 * refuses to delete while a transaction still points at it. Every step is tried
 * whatever the previous one did, and every failure is named.
 */
async function cleanupOwnedRows(page: Page, owned: OwnedRows): Promise<void> {
    if (owned.transactionIds.length + owned.brokerIds.length + owned.assetIds.length === 0) return;
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    // Leave the page first: a workspace still open on the rows goes with it, unsaved.
    await attempt('leave the page', async () => {
        await page.goto('about:blank');
    });
    if (owned.transactionIds.length > 0) {
        await attempt(`transactions ${owned.transactionIds.join(', ')}`, async () => {
            const body = await jsonFrom<CommitBody>(await page.request.post(`${API}/transactions/commit`, {data: {deletes: owned.transactionIds}}), 'delete the owned rows');
            expect(body.committed, `the owned rows must delete together: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
        });
    }
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const body = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete the owned broker');
            expect(body.results.find((item) => item.id === brokerId)?.success, `broker ${brokerId}: ${JSON.stringify(body.results)}`).toBe(true);
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const body = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete the owned asset');
            expect(body.results.find((item) => item.asset_id === assetId)?.success, `asset ${assetId}: ${JSON.stringify(body.results)}`).toBe(true);
        });
    }
    expect(failures, 'cleanup must delete every row, broker and asset this test created').toEqual([]);
}

// ---------------------------------------------------------------------------
// Part A — single-row delete through the bulk workspace (T4)
// ---------------------------------------------------------------------------

test.describe('Single-row delete via bulk workspace (T4)', () => {
    // Only A1-error writes in this block; the others read the seed and record nothing.
    let ownedRows: OwnedRows = noOwnedRows();

    test.beforeEach(async ({page}) => {
        ownedRows = noOwnedRows();
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    // afterEach, not `finally`: it runs after a timeout too, while the page can still
    // reach the API, and an error of its own is reported beside the test's instead of
    // replacing it.
    test.afterEach(async ({page}) => {
        await cleanupOwnedRows(page, ownedRows);
    });

    // === A1: standalone delete ===

    test('A1: standalone delete — workspace opens with the row pre-marked, cancel keeps row', async ({page}) => {
        const row = await findRow(page, 'delete-safe', 'Small deposit');
        expect(row, 'delete-safe DEPOSIT row not found — run ./dev.py db create-clean — check populate_mock_data.py').toBeTruthy();

        await openDeleteWorkspace(row!);

        // Exactly the one row we picked is staged, and it is staged as a DELETE.
        // (Row ids in the workspace are fresh client-side tempIds, so identity is
        // asserted by count + row status, not by cross-referencing the tx id.)
        await expect(bulkRows(page)).toHaveCount(1);
        await expect(bulkDeletedRows(page)).toHaveCount(1);
        // No linked partner on this row → no split hint.
        await expect(page.getByTestId('tx-bulk-split-hint')).toHaveCount(0);

        // Cancel keeps the row. Nothing was edited in the workspace, so the
        // discard-confirmation does not interpose.
        await page.getByTestId('tx-bulk-cancel').click();
        await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 5_000});
        const rowStill = await findRow(page, 'delete-safe', 'Small deposit');
        expect(rowStill).not.toBeNull();
    });

    // === A2: paired delete — partner auto-included, pair collapsed ===

    test('A2: paired delete — one collapsed row staged as delete, split hint shown, cancel keeps both', async ({page}) => {
        const row = await findRow(page, 'delete-safe', 'ETH');
        expect(row, 'delete-safe TRANSFER ETH row not found — check populate_mock_data.py').toBeTruthy();

        await openDeleteWorkspace(row!);

        // The partner half is in the store (the page loads it), so the workspace
        // auto-includes it and collapses the pair: ONE staged row, delete-marked.
        await expect(bulkRows(page)).toHaveCount(1);
        await expect(bulkDeletedRows(page)).toHaveCount(1);

        // A paired delete stages the split hint (transactions.bulk.splitHint,
        // moved here from the deleted DeleteModal's keys).
        await expect(page.getByTestId('tx-bulk-split-hint')).toBeVisible();

        // Cancel keeps both halves.
        await page.getByTestId('tx-bulk-cancel').click();
        await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 5_000});
        const rowStill = await findRow(page, 'delete-safe', 'ETH');
        expect(rowStill).not.toBeNull();
    });

    // === A4/A5: Guard — delete hidden on VIEWER/hidden broker paired ===

    test('A4: delete button hidden on VIEWER paired rows (Asym-c)', async ({page}) => {
        const row = await findRow(page, 'Asym-c');
        expect(row, 'Asym-c row not found — check populate_mock_data.py').toBeTruthy();

        await row!.hover();
        const kebabBtn = row!.getByTestId(/^row-actions-/);
        if (!(await appears(kebabBtn))) return; // no actions at all — delete is a fortiori hidden
        await kebabBtn.click();
        const menu = page.locator('[data-testid="context-menu"]');
        await expect(menu).toBeVisible({timeout: 3_000});
        await expect(menu.locator('[data-testid="context-menu-action-delete"]')).toHaveCount(0);
        await page.keyboard.press('Escape');
    });

    test('A5: delete button hidden on hidden broker paired rows (Asym-d)', async ({page}) => {
        const row = await findRow(page, 'Asym-d');
        expect(row, 'Asym-d row not found — check populate_mock_data.py').toBeTruthy();

        await row!.hover();
        const kebabBtn = row!.getByTestId(/^row-actions-/);
        if (!(await appears(kebabBtn))) return; // no actions at all — delete is a fortiori hidden
        await kebabBtn.click();
        const menu = page.locator('[data-testid="context-menu"]');
        await expect(menu).toBeVisible({timeout: 3_000});
        await expect(menu.locator('[data-testid="context-menu-action-delete"]')).toHaveCount(0);
        await page.keyboard.press('Escape');
    });

    // === committed:false → inline error banner ===

    test('A1-error: refused delete keeps the workspace open and shows the issue inline', async ({page}) => {
        // Own the data: a refusal needs a delete that makes a balance negative,
        // and borrowing a mock row for that (the pre-T4 test used the shared MSFT
        // BUY) reads a position every neighbour is allowed to change. Instead:
        // a fresh broker (no shorting) + a fresh asset + an ADJUSTMENT pair
        // (+5 then −5, net zero). Deleting the +5 alone drives the asset balance
        // to −5, which the backend refuses — deterministically, whoever else runs.
        //
        // Each id is recorded the moment it exists, and the afterEach deletes exactly
        // those — the rows, then the broker, then the asset — whatever happens here.
        const suffix = uniqueSuffix();
        const marker = `T4-delref-${suffix}`;
        const brokers = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(`${API}/brokers`, {data: [{name: marker}]}), 'broker setup');
        const broker = brokers.results.find((item) => item.name === marker);
        if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`broker setup refused: ${broker?.message ?? JSON.stringify(brokers.results)}`);
        const brokerId = broker.broker_id;
        ownedRows.brokerIds.push(brokerId);

        // POST /assets is bulk-only: a list in, per-item results out (201).
        const assetName = `T4-delref-asset-${suffix}`;
        const assetResp = await page.request.post(`${API}/assets`, {data: [{display_name: assetName, asset_type: 'STOCK', currency: 'EUR'}]});
        expect(assetResp.status(), `asset setup failed (HTTP ${assetResp.status()})`).toBe(201);
        const assetResults = (await assetResp.json()).results as Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>;
        const asset = assetResults.find((item) => item.display_name === assetName);
        if (!asset?.success || typeof asset.asset_id !== 'number') throw new Error(`asset setup refused: ${asset?.message ?? JSON.stringify(assetResults)}`);
        const assetId = asset.asset_id;
        ownedRows.assetIds.push(assetId);

        const [plusId, minusId] = await commitCreates(
            page,
            [
                // ADJUSTMENT with qty>0 requires an explicit cost basis.
                {broker_id: brokerId, asset_id: assetId, type: 'ADJUSTMENT', date: '2025-01-10', quantity: '5', cost_basis_override: {code: 'EUR', amount: '10'}, description: marker},
                // The counterpart's description must NOT contain the marker —
                // findRow matches by inclusion, and the row under test is the +5.
                {broker_id: brokerId, asset_id: assetId, type: 'ADJUSTMENT', date: '2025-01-11', quantity: '-5', description: `counterpart-${suffix}`},
            ],
            'create the +5/−5 ADJUSTMENTs',
        );
        ownedRows.transactionIds.push(plusId, minusId);

        // Re-navigate with an id filter — navigating to the URL the page is
        // already on is a client-side no-op that reloads nothing, and the two
        // rows were created AFTER the page first loaded. The id filter makes
        // the URL (and the fetched set) genuinely new.
        await navigateTo(page, `/transactions?page_size=200&id_min=${plusId}&id_max=${plusId}`);
        await waitForSettled(page.getByTestId('transactions-page'));
        // Address the row by its own id, not by text: the broker and asset
        // names carry the suffix too, so a text search matches the
        // counterpart row as well (and date order would pick the −5 — whose
        // deletion is legal — every time).
        const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="tx-${plusId}"]`);
        await expect(row, 'the +5 ADJUSTMENT this test just created is not in the table').toBeVisible({timeout: 8_000});

        const modal = await openDeleteWorkspace(row);
        // Exactly the row we picked is staged (the page loaded nothing else), and it
        // is staged as a DELETE; the wire below says which row that is.
        await expect(bulkRows(page)).toHaveCount(1);
        await expect(bulkDeletedRows(page)).toHaveCount(1);

        // Commit → the server refuses (asset balance would go negative) → the
        // workspace stays open and reports the issue inline. Assert the
        // banner and that it carries at least one issue — never its text,
        // which is localized.
        const {payload, committed} = await commitDeleteWorkspace(page);
        expect(payload.deletes ?? [], 'the wire must name the +5 row, not its counterpart').toEqual([plusId]);
        expect(committed, 'a delete that would drive the asset balance negative must roll back').toBe(false);

        await expect(modal).toBeVisible();
        const banner = modal.getByTestId('tx-bulk-error');
        await expect(banner).toBeVisible({timeout: 5_000});
        // The refusal is a balance issue (`balanceAssetNegative`), and balance
        // issues render as items of their own inside the banner: one of them
        // proves the refusal was itemized, not just announced.
        await expect(banner.getByTestId('tx-bulk-balance-issue').first(), 'the refusal must be itemized inline, not just a bare banner').toBeVisible();

        // Cancel closes (the staged delete is the *initial* state here, so no
        // discard confirmation interposes).
        await modal.getByTestId('tx-bulk-cancel').click();
        await expect(modal).not.toBeVisible({timeout: 5_000});
    });
});

// ---------------------------------------------------------------------------
// A1-confirm and A2-confirm — the deletes that commit, on rows of their own
// ---------------------------------------------------------------------------

// Same title as the block above, so the tests keep their full names. A block of its own
// because the TEST_USER login above must not run for them: each signs in as the
// disposable account that owns its rows.
test.describe('Single-row delete via bulk workspace (T4)', () => {
    let owned: OwnedAccount = {user: null, brokerIds: []};

    test.beforeEach(() => {
        owned = {user: null, brokerIds: []};
    });

    // afterEach, not `finally`: it runs after a timeout too, and an error of its own is
    // reported beside the test's instead of replacing it.
    test.afterEach(async ({page, request}) => {
        await cleanupAccount(page, request, owned);
    });

    // === A1-confirm: standalone delete, committed ===

    test('A1-confirm: standalone delete — commit removes the row', async ({page, request}, testInfo) => {
        // The account goes through the real welcome flow before the delete itself.
        test.setTimeout(60_000);
        const fee = await openAccountWithFee(page, request, owned, `txdel_a1_${testInfo.project.name}`);
        await goToTransactions(page);

        // The row under test, by the id this test created: not by text, not by position.
        const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="tx-${fee.feeId}"]`);
        await expect(row, 'the FEE this test just created is not in the table').toBeVisible({timeout: 8_000});

        await openDeleteWorkspace(row);
        // Exactly the one row we picked is staged — a standalone row brings no
        // partner — and it is staged as a DELETE.
        await expect(bulkRows(page)).toHaveCount(1);
        await expect(bulkDeletedRows(page)).toHaveCount(1);

        const {payload, committed} = await commitDeleteWorkspace(page);
        expect(committed, 'the delete commit must not roll back').toBe(true);
        // The wire carries exactly the transaction we picked.
        expect(payload.deletes ?? []).toEqual([fee.feeId]);

        await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});

        // Row gone, asserted on its own id: toHaveCount retries, is exact, and does not
        // re-read every row in the table.
        await expect(row).toHaveCount(0, {timeout: 8_000});

        // And gone on the server — that row and no other: the deposit that funds it was
        // staged by nobody, and must still be there.
        const left = (await readTransactions(page, [fee.depositId, fee.feeId])).map((tx) => tx.id);
        expect(left, 'the commit deletes the FEE and nothing else').toEqual([fee.depositId]);
    });

    // === A2-confirm: paired delete, committed ===

    test('A2-confirm: paired delete — commit removes both halves', async ({page, request}, testInfo) => {
        // The account goes through the real welcome flow before the delete itself.
        test.setTimeout(60_000);
        const pair = await openAccountWithPair(page, request, owned, `txdel_a2_${testInfo.project.name}`);
        await goToTransactions(page);

        // The row under test is the sending half, by id. The workspace auto-includes a
        // partner only when the page has loaded it, so the receiving half must be there too.
        const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="tx-${pair.fromId}"]`);
        await expect(row, 'the sending half of the pair this test just created is not in the table').toBeVisible({timeout: 8_000});
        await expect(page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="tx-${pair.toId}"]`), 'premise: the receiving half is loaded too').toBeVisible();

        await openDeleteWorkspace(row);
        // The partner is auto-included and the pair collapses: ONE staged row,
        // staged as a DELETE.
        await expect(bulkRows(page)).toHaveCount(1);
        await expect(bulkDeletedRows(page)).toHaveCount(1);

        // Both halves staged through one collapsed row: the commit payload must
        // name BOTH transaction ids, or the backend pair guard
        // (pairDeleteIncomplete) would refuse the batch.
        const {payload, committed} = await commitDeleteWorkspace(page);
        expect(committed, `the paired delete commit must not roll back (deletes=${JSON.stringify(payload.deletes ?? [])})`).toBe(true);
        expect(sortedIds(payload.deletes ?? [])).toEqual(sortedIds([pair.fromId, pair.toId]));

        await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});

        // Both halves gone from the table, in either form a half can take there
        // (`ghost-` is a partner rendered outside the loaded set).
        for (const id of [pair.fromId, pair.toId]) {
            await expect(page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="tx-${id}"], [data-testid="tx-table"] tbody tr[data-row-id="ghost-${id}"]`)).toHaveCount(0, {timeout: 8_000});
        }

        // And on the server, asked about these ids: both halves gone, and the rows that
        // funded the sender — staged by nobody — still there.
        const left = (await readTransactions(page, [...pair.fundingIds, pair.fromId, pair.toId])).map((tx) => tx.id);
        expect(sortedIds(left), 'the commit deletes the pair and nothing else').toEqual(sortedIds(pair.fundingIds));
    });
});

// ---------------------------------------------------------------------------
// Part A6 — Bulk delete via BulkModal
// ---------------------------------------------------------------------------

test.describe('Bulk delete via BulkModal', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    test('A6: toolbar 🗑 opens BulkModal with pre-delete rows', async ({page}) => {
        const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        const count = await rows.count();
        expect(count, 'Need at least 2 rows — check populate_mock_data.py').toBeGreaterThanOrEqual(2);

        // Select first two selectable rows
        const selectedIds: string[] = [];
        for (let i = 0; i < count && selectedIds.length < 2; i++) {
            const checkbox = rows.nth(i).locator('.checkbox-btn');
            if ((await checkbox.count()) > 0) {
                await checkbox.click();
                selectedIds.push((await rows.nth(i).getAttribute('data-row-id')) ?? '');
            }
        }
        const selected = selectedIds.length;
        expect(selected, 'Need 2 selectable rows — check populate_mock_data.py').toBeGreaterThanOrEqual(2);

        // Click bulk delete in toolbar
        const bulkDelBtn = page.getByTestId('toolbar-action-delete');
        await expect(bulkDelBtn).toBeVisible({timeout: 3_000});
        await bulkDelBtn.click();

        // BulkModal opens
        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});

        // The name of this test promises "with pre-delete rows", so that is what it
        // must check. It used to sleep 500ms and then re-assert the modal visible —
        // the same assertion twice with no action in between, which cannot fail for
        // any reason the first one wouldn't have caught.
        //
        // The count is deliberately NOT asserted to equal the selection: if the two
        // rows picked happen to be the two halves of one pair, the modal collapses
        // them into a single entry, and that is correct. The invariant that holds
        // either way is that the modal staged something, and staged nothing that was
        // not selected.
        const bulkRows = page.locator('[data-testid="tx-bulk-body"] tr[data-row-id]');
        await expect(bulkRows.first()).toBeVisible({timeout: 5_000});
        // The modal keys its rows by PENDING-OP id (a fresh uuid), not by transaction
        // id, so the staged ids cannot be cross-referenced with the selected ones.
        // What can be checked is the shape: it staged something, and never more than
        // was selected.
        const staged = await bulkRows.count();
        expect(staged, 'BulkModal opened with no rows staged').toBeGreaterThan(0);
        expect(staged, 'BulkModal staged more rows than were selected').toBeLessThanOrEqual(selected);
    });
});

// ---------------------------------------------------------------------------
// Part C — Action visibility by broker access level
// ---------------------------------------------------------------------------

test.describe('Action visibility by access level', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    test('C1.1: standalone OWNER row shows 4 actions', async ({page}) => {
        const row = await findRow(page, 'Initial EUR funding');
        expect(row, 'IB DEPOSIT row not found — check populate_mock_data.py').toBeTruthy();
        const cnt = await countVisibleActions(row!);
        expect(cnt).toBe(4);
    });

    test('C1.2: standalone VIEWER row shows only view action', async ({page}) => {
        const row = await findRow(page, 'P2P lending capital');
        expect(row, 'Recrowd DEPOSIT row not found — check populate_mock_data.py').toBeTruthy();
        const cnt = await countVisibleActions(row!);
        expect(cnt).toBe(1);
    });

    test('C1.3: paired full-access row (Asym-a) shows 5 actions (view, edit, clone, split, delete)', async ({page}) => {
        const row = await findRow(page, 'Asym-a');
        expect(row, 'Asym-a row not found — check populate_mock_data.py').toBeTruthy();
        const cnt = await countVisibleActions(row!);
        expect(cnt).toBe(5);
    });

    test('C1.4: paired viewer row (Asym-c) shows only view', async ({page}) => {
        const row = await findRow(page, 'Asym-c');
        expect(row, 'Asym-c row not found — check populate_mock_data.py').toBeTruthy();
        const cnt = await countVisibleActions(row!);
        expect(cnt).toBe(1);
    });

    test('C2.1: context menu on OWNER row has 4 items', async ({page}) => {
        const row = await findRow(page, 'Initial EUR funding');
        expect(row, 'IB DEPOSIT row not found — check populate_mock_data.py').toBeTruthy();

        await row!.click({button: 'right'});
        const menu = page.locator('[data-testid="context-menu"]');
        await expect(menu).toBeVisible({timeout: 3_000});
        const items = menu.locator('[data-testid^="context-menu-action-"]');
        expect(await items.count()).toBe(4);
        await page.keyboard.press('Escape');
    });

    test('C2.2: context menu on VIEWER row has 1 item', async ({page}) => {
        const row = await findRow(page, 'P2P lending capital');
        expect(row, 'Recrowd row not found — check populate_mock_data.py').toBeTruthy();

        await row!.click({button: 'right'});
        const menu = page.locator('[data-testid="context-menu"]');
        await expect(menu).toBeVisible({timeout: 3_000});
        const items = menu.locator('[data-testid^="context-menu-action-"]');
        expect(await items.count()).toBe(1);
        await page.keyboard.press('Escape');
    });
});

// ---------------------------------------------------------------------------
// Part B — PickerModal disabled rows
// ---------------------------------------------------------------------------

test.describe('PickerModal disabled rows', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    test('B3-guard: picker shows ⊘ for VIEWER broker rows, select-all skips them', async ({page}) => {
        // Need 2+ rows selected to get edit-many mode → BulkModal → Picker
        const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        const count = await rows.count();
        expect(count, 'Need at least 2 rows — check populate_mock_data.py').toBeGreaterThanOrEqual(2);

        // Select first two selectable rows
        const selectedIds: string[] = [];
        for (let i = 0; i < count && selectedIds.length < 2; i++) {
            const checkbox = rows.nth(i).locator('.checkbox-btn');
            if ((await checkbox.count()) > 0) {
                await checkbox.click();
                selectedIds.push((await rows.nth(i).getAttribute('data-row-id')) ?? '');
            }
        }
        const selected = selectedIds.length;
        expect(selected, 'Need 2 selectable rows — check populate_mock_data.py').toBeGreaterThanOrEqual(2);

        const editBtn = page.getByTestId('toolbar-action-edit');
        await expect(editBtn).toBeVisible({timeout: 3_000});
        await editBtn.click();

        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});

        // C2-fix may auto-open FormModal when guardViewerOnly reduces to 1 row.
        // If so, close it first so it stops intercepting pointer events.
        const formModal = page.getByTestId('tx-form-modal');
        if (await formModal.isVisible({timeout: 1_000}).catch(() => false)) {
            await formModal.getByTestId('tx-form-cancel').click();
            await expect(formModal).not.toBeVisible({timeout: 3_000});
        }

        // Open picker
        const searchAddBtn = bulkModal.getByTestId('tx-bulk-picker');
        await expect(searchAddBtn).toBeVisible({timeout: 3_000});
        await searchAddBtn.click();

        const picker = page.getByTestId('tx-picker-modal');
        await expect(picker).toBeVisible({timeout: 5_000});

        // ⊘ icons should exist for VIEWER broker rows (DEGIRO, eToro, Recrowd).
        // The picker paginates at 20 over every transaction in the database, so
        // "they are on the first page" stops being true as soon as a neighbour
        // adds rows. Show them all instead of guessing.
        await maximisePageSize(page, picker);
        const disabledIcons = picker.locator('.disabled-select-icon');
        await expect(disabledIcons.first(), 'VIEWER broker rows must exist — check populate_mock_data.py').toBeVisible({timeout: 5_000});

        // Select-all should skip disabled rows
        const selectAllBtn = picker.locator('th .checkbox-btn');
        expect(await selectAllBtn.count(), 'the picker header must offer select-all').toBeGreaterThan(0);
        await selectAllBtn.click();

        // "Add N selected" should have fewer than total rows
        const addBtn = picker.getByTestId('tx-picker-add');
        const totalRows = await picker.locator('tbody tr[data-row-id]').count();
        await expect
            .poll(
                async () => {
                    const match = ((await addBtn.textContent()) ?? '').match(/(\d+)/);
                    return match ? parseInt(match[1]) : -1;
                },
                {timeout: 5_000},
            )
            .toBeGreaterThan(0);
        const selectedCount = parseInt(((await addBtn.textContent()) ?? '').match(/(\d+)/)![1]);
        expect(selectedCount, 'select-all must skip the disabled rows').toBeLessThan(totalRows);

        // Close
        await picker.getByTestId('tx-picker-cancel').click();
        await expect(picker).not.toBeVisible();
    });
});
