/**
 * Transaction Split & Promote E2E Tests — Plan D2 Step F14
 *
 * Covers:
 * 1. Split from Main Table → confirm modal appears
 * 2. Guard: split hidden on standalone
 * 3. Guard: promote hidden on paired
 * 4. Promote from Main Table → select 2 promote-test rows
 * 5. BulkModal open after page refresh (NR-1 non-regression for F6)
 * 6. C3: split + edit in the BulkModal → commit payload (on a pair the test owns)
 *
 * Prerequisites: backend test mode (port 6041), mock data populated.
 * Mock data contract: populate_mock_data.py creates tagged transactions:
 * - "promote-test" tag on standalone DEPOSIT/WITHDRAWAL for promote candidates
 *   (Coinbase/EDITOR + IB/OWNER — both editable by e2e_test_user)
 * - "promote-test-access-fail" tag on DEPOSIT/WITHDRAWAL where one broker is VIEWER
 * - "delete-safe" tag on pairs suitable for split tests
 *
 * Tests 1-5 only read mock data. C3 commits — a real split and a real edit — so it never
 * touches a mock row: it builds its own pair on a disposable account (two brokers the
 * account owns, the seeded Ethereum as the asset) and deletes the account afterwards,
 * its brokers and every row on them included.
 *
 * DOM patterns (DataTable + TransactionsTable):
 * - Table wrapper: [data-testid="tx-table"]
 * - Row: tr[data-row-id="tx-{id}"] or tr[data-row-id="ghost-{id}"]
 * - Checkbox: [data-testid="dt-row-checkbox-{row-id}"], data-state checked|unchecked
 * - Link indicator: button.tx-link-icon[data-tx-link="{id}"]
 * - Row actions: kebab button [data-testid^="row-actions-"] → opens context menu with
 *   items at [data-testid="context-menu-action-{id}"] (e.g. "split", "edit", "view").
 */
import {randomUUID} from 'crypto';
import {expect, test, type APIRequestContext, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {appears} from '../fixtures/probe';
import {daysAgoIso} from '../fixtures/dates';
import {createOwnedBroker, deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';

test.setTimeout(30_000);

const API = '/api/v1';

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type CommitBody = {committed: boolean; issues?: unknown[]; results?: Array<{operation: string; index: number; ids: number[]}>};
/** What the committing test created, recorded the moment it exists so the cleanup finds all of it. */
type Owned = {user: DisposableUser | null; brokerIds: number[]};
/** A saved asset TRANSFER between the account's two brokers: `fromId` sends from `fromBroker`, `toId` receives. */
type OwnedPair = {fromId: number; toId: number; fromBroker: string};

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

/** Find the first row matching ALL substrings (and NOT matching any excludes). Returns data-row-id or null. */
async function findRowId(page: Page, includes: string[], excludes: string[] = []): Promise<string | null> {
    const rows = page.locator('[data-testid="tx-table"] tr[data-row-id]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const text = (await row.textContent()) ?? '';
        if (includes.every((s) => text.includes(s)) && excludes.every((s) => !text.includes(s))) {
            return await row.getAttribute('data-row-id');
        }
    }
    return null;
}

/** Select a row by its row-id checkbox. */
async function selectRow(page: Page, rowId: string) {
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-${rowId}`);
    await expect(checkbox).toBeVisible({timeout: 2_000});
    await checkbox.click();
    // The checkbox publishes its own state: the row is selected, not merely clicked.
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    // The toolbar publishes how many rows it holds. A paired row selects both
    // halves, so the count is not always 1 — what matters is that the selection
    // registered at all before the caller reaches for a toolbar action.
    await expect(page.getByTestId('selection-toolbar')).not.toHaveAttribute('data-selected-count', '0');
}

/** Find a paired row (has link icon). Returns row-id or null. */
async function findPairedRowId(page: Page): Promise<string | null> {
    const rows = page.locator('[data-testid="tx-table"] tr[data-row-id^="tx-"]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const link = row.locator('.tx-link-icon');
        if ((await link.count()) > 0) {
            return await row.getAttribute('data-row-id');
        }
    }
    return null;
}

/** Find a standalone row (no link icon). Returns row-id or null. */
async function findStandaloneRowId(page: Page): Promise<string | null> {
    const rows = page.locator('[data-testid="tx-table"] tr[data-row-id^="tx-"]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const link = row.locator('.tx-link-icon');
        if ((await link.count()) === 0) {
            return await row.getAttribute('data-row-id');
        }
    }
    return null;
}

/**
 * Find a row that actually offers the split action, trying rows matching
 * `prefer` first and then any paired row.
 *
 * Picking a paired row and assuming it can be split is precisely the
 * assumption that broke: a neighbouring spec had already split the row this
 * one reached for, and the menu opened without the entry. Being paired is a
 * necessary condition, not a sufficient one — the only way to know a row is
 * splittable is to open its menu and look.
 */
async function findSplittableRowId(page: Page, prefer: string[] = []): Promise<string | null> {
    const rows = page.locator('[data-testid="tx-table"] tr[data-row-id^="tx-"]');
    const count = await rows.count();
    const menu = page.locator('[data-testid="context-menu"]');

    for (const includes of prefer.length ? [prefer, []] : [[]]) {
        for (let i = 0; i < count; i++) {
            const row = rows.nth(i);
            if (includes.length) {
                const text = (await row.textContent()) ?? '';
                if (!includes.every((s) => text.includes(s))) continue;
            }
            if ((await row.locator('.tx-link-icon').count()) === 0) continue;

            const kebab = row.getByTestId(/^row-actions-/);
            if ((await kebab.count()) === 0) continue;

            await row.hover();
            await kebab.first().click();
            await expect(menu).toBeVisible({timeout: 3_000});
            const hasSplit = (await menu.locator('[data-testid="context-menu-action-split"]').count()) > 0;
            await page.keyboard.press('Escape');
            await expect(menu).toBeHidden({timeout: 2_000});

            if (hasSplit) return await row.getAttribute('data-row-id');
        }
    }
    return null;
}

// ---------------------------------------------------------------------------
// Owned pair — for the one test here that commits
// ---------------------------------------------------------------------------

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

/** The seeded asset with this exact ticker — read, never assumed. */
async function seededAssetId(page: Page, ticker: string): Promise<number> {
    const assets = await jsonFrom<Array<{id: number}>>(await page.request.get(`${API}/assets/query?ticker=${encodeURIComponent(ticker)}`), `look up the ${ticker} asset`);
    if (assets.length !== 1) throw new Error(`Expected exactly one asset with ticker ${ticker}, found ${assets.length} — check populate_mock_data.py`);
    return assets[0].id;
}

/**
 * A disposable account holding one saved asset TRANSFER between two brokers it owns.
 *
 * Why not the seeded `delete-safe` pair: a committed split rewrites both rows in place —
 * same ids, new types, no link — so nothing short of a repopulate puts them back (the
 * tx-hygiene net drops new ids, or repopulates when an id is missing: neither happens
 * here), and other specs look that pair up afterwards (tx-bulk-suggest-ux, tx-delete,
 * tx-crud-full). Rows on an account of its own are invisible to every other spec, and
 * deleting its brokers takes them all.
 *
 * The giver is funded first — a deposit, then a buy — so neither the transfer nor the
 * split's edited quantity takes it below zero. The asset is the seeded Ethereum, which
 * this test only reads.
 */
async function openAccountWithPair(page: Page, request: APIRequestContext, owned: Owned, tag: string): Promise<OwnedPair> {
    owned.user = await registerDisposableUser(request, tag);
    await prepareOnboardingAccount(page, owned.user, []);
    const giver = await createOwnedBroker(page, `${tag}-from`, owned.brokerIds);
    const receiver = await createOwnedBroker(page, `${tag}-to`, owned.brokerIds);
    const assetId = await seededAssetId(page, 'ETH-USD');

    const funding = [
        {broker_id: giver.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '100'}},
        {broker_id: giver.id, asset_id: assetId, type: 'BUY', date: daysAgoIso(9), quantity: '0.01', cash: {code: 'USD', amount: '-30'}},
    ];
    await commitCreates(page, funding, 'fund the giver broker');

    const linkUuid = randomUUID();
    const description = `Owned pair ${tag}`;
    const transfer = [
        {broker_id: giver.id, asset_id: assetId, type: 'TRANSFER', date: daysAgoIso(5), quantity: '-0.001', link_uuid: linkUuid, description},
        {broker_id: receiver.id, asset_id: assetId, type: 'TRANSFER', date: daysAgoIso(5), quantity: '0.001', link_uuid: linkUuid, description, cost_basis_mode: 'auto'},
    ];
    const [fromId, toId] = await commitCreates(page, transfer, 'commit the owned TRANSFER pair');

    // The premise, read back rather than inferred: the two halves point at each other.
    const halves = await jsonFrom<Array<{id: number; related_transaction_id?: number | null}>>(await page.request.get(`${API}/transactions?ids=${fromId}&ids=${toId}`), 'read the owned pair back');
    const linkOf = new Map(halves.map((tx) => [tx.id, tx.related_transaction_id ?? null] as const));
    expect([linkOf.get(fromId), linkOf.get(toId)], 'premise: the two halves of the owned pair are linked to each other').toEqual([toId, fromId]);
    return {fromId, toId, fromBroker: giver.name};
}

/**
 * Leave the page, then delete the account: its brokers first — `force` takes their
 * transactions with them, the pair and whatever the test made of it — and the account
 * last. Only what this test recorded.
 */
async function cleanupOwned(page: Page, request: APIRequestContext, owned: Owned): Promise<void> {
    const user = owned.user;
    if (!user) return; // nothing was created: brokers only ever exist under the account
    try {
        // Unmount the page first, so nothing on it reloads the rows while they go.
        await page.goto('about:blank');
    } finally {
        await deleteDisposableUser(request, user, owned.brokerIds);
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Split & Promote', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // -----------------------------------------------------------------------
    // SPLIT TESTS
    // -----------------------------------------------------------------------

    test('Guard: split action hidden on standalone TX', async ({page}) => {
        await goToTransactions(page);
        const standaloneRowId = await findStandaloneRowId(page);
        expect(standaloneRowId, 'Need at least 1 standalone TX in mock data').toBeTruthy();

        // Hover row to make actions visible
        const row = page.locator(`[data-testid="tx-table"] tr[data-row-id="${standaloneRowId}"]`);
        await row.hover();

        // Split action should NOT be visible (visible function filters paired-only) —
        // check via kebab menu since actions are no longer inline buttons
        const kebabBtn = row.getByTestId(/^row-actions-/);
        if (!(await appears(kebabBtn))) return; // no actions at all — split is a fortiori hidden
        await kebabBtn.click();
        const menu = page.locator('[data-testid="context-menu"]');
        await expect(menu).toBeVisible({timeout: 3_000});
        await expect(menu.locator('[data-testid="context-menu-action-split"]')).toHaveCount(0);
        await page.keyboard.press('Escape');
    });

    test('Split from Main Table → confirm modal appears', async ({page}) => {
        await goToTransactions(page);

        // Find a row that offers the split action — verified, not assumed.
        const pairedRowId = await findSplittableRowId(page, ['delete-safe']);
        expect(pairedRowId, 'Need at least 1 splittable TX for split test').toBeTruthy();

        // Hover to show actions, click split
        const row = page.locator(`[data-testid="tx-table"] tr[data-row-id="${pairedRowId}"]`);
        await row.hover();

        const splitAction = row.getByTestId(/^row-actions-/);
        await expect(splitAction).toBeVisible({timeout: 2_000});
        await splitAction.click();
        await page.getByTestId('context-menu-action-split').click();

        // A confirmation modal should appear (TransactionActionModal testId="tx-action-modal")
        const modal = page.locator('[data-testid="tx-action-modal"]');
        await expect(modal.first()).toBeVisible({timeout: 3_000});

        // Verify sticky structure: header, scrollable body, footer all visible
        const content = modal.first().getByTestId('tx-action-modal-content');
        await expect(content).toBeVisible();

        // Footer buttons always visible (sticky)
        const confirmBtn = modal.first().getByTestId('tx-action-modal-confirm');
        const cancelBtn = modal.first().getByTestId('tx-action-modal-cancel');
        await expect(confirmBtn).toBeVisible();
        await expect(cancelBtn).toBeVisible();

        // Quantity cells should contain emoji (📈 or 📉) or — for zero
        const beforeTable = modal.first().getByTestId('tx-action-before');
        const qtyText = await beforeTable.textContent();
        const hasQtyIndicator = qtyText?.includes('📈') || qtyText?.includes('📉') || qtyText?.includes('—');
        expect(hasQtyIndicator, 'Quantity should show emoji or — for zero').toBeTruthy();

        // Tag badges should be colored (have style with --badge-bg)
        const tagBadges = modal.first().locator('.action-tag-badge');
        const tagCount = await tagBadges.count();
        if (tagCount > 0) {
            const style = await tagBadges.first().getAttribute('style');
            expect(style, 'Tag badge should have badge-bg CSS variable').toContain('--badge-bg');
        }
    });

    // -----------------------------------------------------------------------
    // PROMOTE TESTS
    // -----------------------------------------------------------------------

    test('Guard: promote toolbar hidden when paired row is selected', async ({page}) => {
        await goToTransactions(page);
        const pairedId = await findPairedRowId(page);
        expect(pairedId, 'Paired TX must exist — check populate_mock_data.py').toBeTruthy();
        await selectRow(page, pairedId!);
        // Absence is only a fact once the toolbar has actually rendered FOR THIS
        // selection. Without this barrier the next assertion is satisfied by
        // "the toolbar hasn't caught up yet", which is not what the test claims.
        await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '1');
        // The promote/link button should NOT appear for paired rows
        await expect(page.locator('[data-testid="toolbar-action-promote"]')).toHaveCount(0);
    });

    // -----------------------------------------------------------------------
    // BULKMODAL NON-REGRESSION (F6 / NR-1)
    // -----------------------------------------------------------------------

    test('NR-1: BulkModal renders correctly after page refresh', async ({page}) => {
        await goToTransactions(page);
        const rows = page.locator('[data-testid="tx-table"] tr[data-row-id^="tx-"]');
        await expect(rows.first()).toBeVisible({timeout: 8_000});
        const firstRowId = await rows.first().getAttribute('data-row-id');
        expect(firstRowId).toBeTruthy();

        // Refresh the page
        await page.reload();
        await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});

        // Try row action: hover + click edit or view. The table being visible does not
        // mean THIS row has been re-rendered into it after the reload.
        const row = page.locator(`[data-testid="tx-table"] tr[data-row-id="${firstRowId}"]`);
        await expect(row).toBeVisible({timeout: 8_000});
        await row.hover();

        const kebabBtn = row.getByTestId(/^row-actions-/);
        await expect(kebabBtn).toBeVisible({timeout: 2_000});
        await kebabBtn.click();
        const menu = page.locator('[data-testid="context-menu"]');
        await expect(menu).toBeVisible({timeout: 2_000});
        const editAction = menu.locator('[data-testid="context-menu-action-edit"]');
        const viewAction = menu.locator('[data-testid="context-menu-action-view"]');
        const editVisible = await editAction.isVisible({timeout: 1_000}).catch(() => false);
        const viewVisible = await viewAction.isVisible({timeout: 1_000}).catch(() => false);
        expect(editVisible || viewVisible, 'First row must have edit or view action — check populate_mock_data.py').toBeTruthy();
        if (editVisible) {
            await editAction.click();
        } else {
            await viewAction.click();
        }

        // A modal should open (BulkModal or FormModal)
        const anyModal = page.locator('[data-testid="tx-bulk-modal"], [data-testid="tx-form-modal"], .modal-base');
        await expect(anyModal.first()).toBeVisible({timeout: 3_000});
    });

    // -----------------------------------------------------------------------
    // PROMOTE from promote-test MOCK DATA
    // -----------------------------------------------------------------------

    test('Promote: select 2 promote-test WITHDRAWAL+DEPOSIT rows → toolbar shows link button', async ({page}) => {
        await goToTransactions(page);
        // Find promote-test WITHDRAWAL and DEPOSIT rows (exclude access-fail)
        // These should be: Coinbase(EDITOR) WITHDRAWAL -500 EUR + IB(OWNER) DEPOSIT +500 EUR
        const withdrawalRowId = await findRowId(page, ['promote-test', 'Withdrawal'], ['access-fail']);
        const depositRowId = await findRowId(page, ['promote-test', 'Deposit'], ['access-fail']);

        if (!withdrawalRowId || !depositRowId) {
            throw new Error(`Need promote-test WITHDRAWAL+DEPOSIT rows (found W=${withdrawalRowId}, D=${depositRowId}) — check populate_mock_data.py`);
        }

        // Select both
        await selectRow(page, withdrawalRowId);
        await selectRow(page, depositRowId);

        // The toolbar should show the promote/link button
        const promoteBtn = page.locator('[data-testid="toolbar-action-promote"]');
        await expect(promoteBtn).toBeVisible({timeout: 3_000});
    });
});

// ---------------------------------------------------------------------------
// C3 — the one test here that commits, on a pair of its own
// ---------------------------------------------------------------------------

// Same title as the block above, so the test keeps its full name. A block of its own
// because the TEST_USER login above must not run for it: it signs in as the disposable
// account that owns its pair.
test.describe('Split & Promote', () => {
    let owned: Owned = {user: null, brokerIds: []};

    test.beforeEach(() => {
        owned = {user: null, brokerIds: []};
    });

    // afterEach, not `finally`: it runs after a timeout too, and an error of its own is
    // reported beside the test's instead of replacing it.
    test.afterEach(async ({page, request}) => {
        await cleanupOwned(page, request, owned);
    });

    // -----------------------------------------------------------------------
    // C3 REGRESSION: Split + Edit → commit includes splits AND updates (no type in update)
    // -----------------------------------------------------------------------

    test('C3: Split + edit quantity → commit payload has splits + updates without type', async ({page, request}, testInfo) => {
        // The account goes through the real welcome flow before the split itself.
        test.setTimeout(60_000);
        const pair = await openAccountWithPair(page, request, owned, `c3_${testInfo.project.name}`);
        await goToTransactions(page);

        // Select both halves of this test's own pair — by the ids it created, never by
        // position — and open the BulkModal via the Edit toolbar. With two rows selected
        // the workspace opens no FormModal by itself (with one it does, and may open it
        // again after it has been dismissed), so the grid is reachable directly.
        await selectRow(page, `tx-${pair.fromId}`);
        await selectRow(page, `tx-${pair.toId}`);
        await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '2');
        const editBtn = page.getByTestId('toolbar-action-edit');
        await expect(editBtn).toBeVisible({timeout: 2_000});
        await editBtn.click();

        // BulkModal should be open
        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 3_000});

        // The pair arrives as one row, its receiver hidden behind it. Found by the giver's
        // broker — a name only this account has — not by position: before the split and
        // after it, that row is the giver's.
        const giverRow = bulkModal.getByTestId('tx-bulk-body').locator('tr[data-row-id]').filter({hasText: pair.fromBroker});
        await expect(giverRow).toHaveCount(1, {timeout: 5_000});

        // Click Split on the row — need to hover to reveal row actions
        await giverRow.hover();
        const rowActions = giverRow.getByTestId(/^row-actions-/);
        await expect(rowActions).toBeVisible({timeout: 2_000});
        await rowActions.click();
        await page.getByTestId('context-menu-action-split').click();

        // Verify split-queued badge appears in the header summary
        const splitBadge = bulkModal.getByTestId('split-queued-badge');
        await expect(splitBadge).toBeVisible({timeout: 2_000});

        // Double-click the giver row to open FormModal (triggers handleEditRowClick)
        await giverRow.dblclick();

        // FormModal should open
        const formModal = page.getByTestId('tx-form-modal');
        await expect(formModal).toBeVisible({timeout: 3_000});

        // Change quantity value in the FormModal (keep negative to preserve TRANSFER 'from' side)
        const qtyInput = formModal.getByTestId('tx-form-quantity');
        await expect(qtyInput).toBeVisible({timeout: 2_000});
        await qtyInput.fill('-0.002');
        await expect(qtyInput).toHaveValue('-0.002');

        // Save the FormModal
        await formModal.getByTestId('tx-form-save').click();

        // FormModal should close
        await expect(formModal).not.toBeVisible({timeout: 2_000});

        // Now intercept the commit request and verify payload
        const commitPromise = page.waitForResponse((res) => res.url().includes('/api/v1/transactions/commit') && res.request().method() === 'POST', {timeout: 10_000});

        // Click Commit
        const commitBtn = bulkModal.getByTestId('tx-bulk-commit');
        await expect(commitBtn).toBeVisible({timeout: 2_000});
        await commitBtn.click();

        const response = await commitPromise;
        const requestBody = JSON.parse(response.request().postData() ?? '{}');
        const responseBody = await response.json();

        // CRITICAL ASSERTIONS:
        // 1. Payload must include splits
        expect(requestBody.splits, 'Payload must include splits[]').toBeDefined();
        expect(requestBody.splits.length).toBeGreaterThan(0);

        // 2. Payload must include updates with description change
        expect(requestBody.updates, 'Payload must include updates[]').toBeDefined();
        expect(requestBody.updates.length).toBeGreaterThan(0);

        // 3. Updates must NOT include 'type' field (split handles type change)
        for (const upd of requestBody.updates) {
            expect(upd.type, `Update for id=${upd.id} must NOT have type — split handles it`).toBeUndefined();
        }

        // 4. Update should contain the quantity we set
        const qtyUpdate = requestBody.updates.find((u: any) => u.quantity != null);
        expect(qtyUpdate, 'Should find our quantity update').toBeTruthy();

        // 5. Backend should accept it (no type error, no balance error on the funded giver)
        expect(responseBody.committed, `Commit should succeed. Issues: ${JSON.stringify(responseBody.issues)}`).toBe(true);

        // 6. ...and all of it is about this test's own pair: the split is that pair, the edit its giver
        const ownPair = [pair.fromId, pair.toId].sort((a, b) => a - b);
        const splitPairs = requestBody.splits.map((s: {id_a: number; id_b: number}) => [s.id_a, s.id_b].sort((a, b) => a - b));
        expect(splitPairs, 'The split must be this test’s own pair').toEqual([ownPair]);
        expect(qtyUpdate.id, 'The quantity edit must land on the giver this test double-clicked').toBe(pair.fromId);
    });
});
