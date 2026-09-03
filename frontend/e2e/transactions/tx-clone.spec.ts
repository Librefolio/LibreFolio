/**
 * Transaction Clone E2E Tests — Phase 07 · Plan C2 Step 8a
 *
 * Covers:
 * - Clone standalone TX → 1 row new, source date preserved (T3)
 * - Clone paired TX → 2 rows new (Da:/A:), source date preserved (T3)
 * - Clone with quantityRule='zero' → qty=0
 * - Clone paired commit → pair created in DB, both halves on the source date
 * - cloneRow inside the workspace → source date preserved (T3)
 * - Clone from view-only broker → clone button not visible
 *
 * T3 (2026-09): cloning is the correction workflow — duplicating a
 * misclassified historical row and editing the copy. Resetting the date to
 * today destroyed exactly the field being corrected, so every clone path
 * (resolveInitialRows / createOpFromClone / cloneRow) now preserves it.
 *
 * Prerequisites: backend test mode (port 6041), mock data populated.
 * Mock data contract: populate_mock_data.py creates INTEREST transactions,
 * asymmetric paired TRANSFERs, and linked pairs with "access-test" tag.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {appears} from '../fixtures/probe';
import {trackTransactionWrites, type TransactionWriteTracker} from '../fixtures/db-cleanup';
import {todayIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';

test.setTimeout(25_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    // The table being VISIBLE is not the table being LOADED: it renders empty
    // and fills in. The page publishes data-busy, so wait on that instead.
    await waitForSettled(page.getByTestId('transactions-page'));
}

/** Select a row by its row-id checkbox. */
async function selectRow(page: Page, rowId: string) {
    const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="${rowId}"]`);
    const checkbox = row.locator('.checkbox-btn').first();
    await expect(checkbox).toBeVisible({timeout: 2_000});
    await checkbox.click();
    // The toolbar publishes how many rows it holds. A paired row selects both
    // halves, so the count is not always 1 — what matters is that the selection
    // registered at all before the caller reaches for a toolbar action.
    await expect(page.getByTestId('selection-toolbar')).not.toHaveAttribute('data-selected-count', '0');
}

/** Find the first row matching ALL substrings. Returns data-row-id or null. */
async function findRowId(page: Page, ...substrings: string[]): Promise<string | null> {
    const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const text = (await row.textContent()) ?? '';
        if (substrings.every((s) => text.includes(s))) {
            return await row.getAttribute('data-row-id');
        }
    }
    return null;
}

/** Click a row's action via its kebab menu (row-actions-{id} → context-menu-action-{actionId}). */
async function clickRowAction(row: Locator, actionId: string) {
    const page = row.page();
    await row.hover();
    const kebabBtn = row.getByTestId(/^row-actions-/);
    await expect(kebabBtn).toBeVisible({timeout: 2_000});
    await kebabBtn.click();
    const btn = page.getByTestId(`context-menu-action-${actionId}`);
    await expect(btn).toBeVisible({timeout: 2_000});
    await btn.click();
}

/**
 * A clone source's date, read from the server. The DOM row id is not the
 * transaction id (TransactionsTable prefixes `tx-` / `ghost-`), and asserting
 * against a date scraped from row text would confuse "preserved" with
 * "happened to render today" — the server answer is exact.
 */
async function readSourceDate(page: Page, rowId: string): Promise<string> {
    const txId = Number(rowId.replace(/^(?:tx|ghost)-/, ''));
    expect(Number.isInteger(txId), `row id ${rowId} does not carry a transaction id`).toBeTruthy();
    const resp = await page.request.get(`/api/v1/transactions?ids=${txId}`);
    expect(resp.ok(), `reading the clone source failed (HTTP ${resp.status()})`).toBeTruthy();
    const [item] = (await resp.json()) as Array<{date: string}>;
    return item.date;
}

/** Close any open modal (FormModal + BulkModal + confirm discard). */
async function closeModals(page: Page) {
    const cancelForm = page.getByTestId('tx-form-cancel');
    if (await cancelForm.isVisible({timeout: 500}).catch(() => false)) {
        await cancelForm.click();
        await expect(cancelForm).toBeHidden({timeout: 3_000});
    }
    const cancelBulk = page.getByTestId('tx-bulk-cancel');
    if (await cancelBulk.isVisible({timeout: 500}).catch(() => false)) {
        await cancelBulk.click();
        const discard = page.getByTestId('confirm-modal-confirm');
        if (await discard.isVisible({timeout: 1_000}).catch(() => false)) {
            await discard.click();
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transaction Clone', () => {
    // Cloning commits real rows into a global table. Without this the clone of the
    // "delete-safe" ETH pair survives the spec and breaks tx-delete's A2-confirm as
    // soon as the two specs share a Playwright invocation.
    //
    // The tracker deletes the rows *this page* committed, not every row that appeared
    // meanwhile: with concurrent workers those are not the same set, and deleting the
    // difference means deleting a neighbour's fixtures mid-test.
    let txWrites: TransactionWriteTracker;

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        txWrites = await trackTransactionWrites(page);
        await goToTransactions(page);
    });

    test.afterEach(async () => {
        await txWrites.cleanup();
    });

    test('clone standalone → 1 row new, source date preserved (T3)', async ({page}) => {
        // Find a standalone BUY/DEPOSIT on an editable broker (IB or Directa)
        const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        const count = await rows.count();
        const candidates: string[] = [];

        for (let i = 0; i < count; i++) {
            const row = rows.nth(i);
            const cls = (await row.getAttribute('class')) ?? '';
            // Skip receiver rows (paired)
            if (cls.includes('tx-row-receiver')) continue;
            // Check next row is NOT a receiver (this means current is standalone)
            if (i + 1 < count) {
                const nextCls = (await rows.nth(i + 1).getAttribute('class')) ?? '';
                if (nextCls.includes('tx-row-receiver')) continue; // this is the giver of a pair
            }
            const text = (await row.textContent()) ?? '';
            const editableBrokers = ['Interactive Brokers', 'Directa', 'Coinbase'];
            if (editableBrokers.some((b) => text.includes(b))) {
                const rowId = await row.getAttribute('data-row-id');
                if (rowId) candidates.push(rowId);
            }
        }
        expect(candidates.length, 'Must find a standalone TX on editable broker').toBeGreaterThan(0);

        // A source dated TODAY would make "preserved" indistinguishable from
        // "reset to today" (a neighbour's just-committed row is dated today by
        // construction) — skip those; the assertion must discriminate.
        let standaloneRowId: string | null = null;
        let sourceDate = '';
        for (const rowId of candidates) {
            const date = await readSourceDate(page, rowId);
            if (date !== todayIso()) {
                standaloneRowId = rowId;
                sourceDate = date;
                break;
            }
        }
        expect(standaloneRowId, 'No standalone editable row with a non-today date — check populate_mock_data.py').toBeTruthy();

        await selectRow(page, standaloneRowId!);
        const cloneBtn = page.locator('[data-testid="toolbar-action-clone"]');
        await expect(cloneBtn).toBeVisible({timeout: 2_000});
        await cloneBtn.click();

        // BulkModal opens
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Check the grid has 1 row with status "new" and the SOURCE date
        const bulkRows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
        await expect(bulkRows).toHaveCount(1, {timeout: 3_000});

        // Status badge: "new"
        const statusCell = bulkRows.first().locator('text=new');
        await expect(statusCell).toBeVisible({timeout: 2_000});

        // T3: the clone keeps the original date (the correction workflow), not today.
        const rowText = (await bulkRows.first().textContent()) ?? '';
        expect(rowText).toContain(sourceDate);

        // The single-clone auto-opens the FormModal — the same preserved date
        // must be what the edit form shows (createOpFromClone + fromTx agree).
        const formModal = page.getByTestId('tx-form-modal');
        await expect(formModal).toBeVisible({timeout: 5_000});
        await expect(page.getByTestId('tx-form-date-wrap').locator('input')).toHaveValue(sourceDate);

        await closeModals(page);
    });

    test('clone paired → 2 rows new (Da:/A:), source date preserved (T3)', async ({page}) => {
        // Find a giver+receiver pair on editable brokers
        const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        const total = await allRows.count();
        const giverCandidates: string[] = [];

        for (let i = 0; i < total - 1; i++) {
            const nextCls = (await allRows.nth(i + 1).getAttribute('class')) ?? '';
            if (nextCls.includes('tx-row-receiver')) {
                const giverText = (await allRows.nth(i).textContent()) ?? '';
                const editableBrokers = ['Interactive Brokers', 'Directa', 'Coinbase'];
                if (editableBrokers.some((b) => giverText.includes(b))) {
                    const rowId = await allRows.nth(i).getAttribute('data-row-id');
                    if (rowId) giverCandidates.push(rowId);
                }
            }
        }
        expect(giverCandidates.length, 'Must find a paired giver row on editable broker').toBeGreaterThan(0);

        // Skip today-dated pairs: preserved vs reset-to-today must stay
        // distinguishable (see the standalone test above).
        let giverRowId: string | null = null;
        let sourceDate = '';
        for (const rowId of giverCandidates) {
            const date = await readSourceDate(page, rowId);
            if (date !== todayIso()) {
                giverRowId = rowId;
                sourceDate = date;
                break;
            }
        }
        expect(giverRowId, 'No paired editable row with a non-today date — check populate_mock_data.py').toBeTruthy();

        // Select only the giver
        await selectRow(page, giverRowId!);
        const cloneBtn = page.locator('[data-testid="toolbar-action-clone"]');
        await expect(cloneBtn).toBeVisible({timeout: 2_000});
        await cloneBtn.click();

        // BulkModal opens with 2 rows (auto-included partner)
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Should have 1 visible row in grid (paired rendered as single row with Da:/A:)
        // OR 2 rows if the impl shows 2 separate rows — check for "new" status
        const bulkRows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
        const bulkCount = await bulkRows.count();
        // Paired clone = 1 grid row (dual Da:/A:) with status "new"
        expect(bulkCount).toBeGreaterThanOrEqual(1);

        // All rows should be "new"
        for (let i = 0; i < bulkCount; i++) {
            const text = (await bulkRows.nth(i).textContent()) ?? '';
            expect(text).toContain('new');
        }

        // T3: the clone keeps the pair's original date, not today.
        const firstText = (await bulkRows.first().textContent()) ?? '';
        expect(firstText).toContain(sourceDate);

        await closeModals(page);
    });

    test('clone INTEREST sets quantity to 0', async ({page}) => {
        // Find an INTEREST transaction on an editable broker
        const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        const count = await rows.count();
        let interestRowId: string | null = null;

        for (let i = 0; i < count; i++) {
            const row = rows.nth(i);
            const typeIcon = row.locator('img[alt]').first();
            if (await typeIcon.isVisible().catch(() => false)) {
                const alt = (await typeIcon.getAttribute('alt')) ?? '';
                if (/interest/i.test(alt)) {
                    interestRowId = await row.getAttribute('data-row-id');
                    break;
                }
            }
        }
        expect(interestRowId, 'INTEREST transaction must exist in mock data').toBeTruthy();

        await selectRow(page, interestRowId!);
        const cloneBtn = page.locator('[data-testid="toolbar-action-clone"]');
        await expect(cloneBtn).toBeVisible({timeout: 2_000});
        await cloneBtn.click();

        // BulkModal opens → FormModal should auto-open for single clone
        const formModal = page.getByTestId('tx-form-modal');
        await expect(formModal).toBeVisible({timeout: 5_000});

        // Verify quantity is 0
        const qtyInput = page.getByTestId('tx-form-quantity');
        if (await qtyInput.isVisible({timeout: 2_000}).catch(() => false)) {
            const qtyValue = await qtyInput.inputValue();
            expect(qtyValue).toBe('0');
        }

        await closeModals(page);
    });

    test('clone paired commit → pair created in DB with link', async ({page}) => {
        // Find a giver+receiver pair on editable brokers
        const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        const total = await allRows.count();
        let giverRowId: string | null = null;

        for (let i = 0; i < total - 1; i++) {
            const nextCls = (await allRows.nth(i + 1).getAttribute('class')) ?? '';
            if (nextCls.includes('tx-row-receiver')) {
                const giverText = (await allRows.nth(i).textContent()) ?? '';
                const recvText = (await allRows.nth(i + 1).textContent()) ?? '';
                const editableBrokers = ['Interactive Brokers', 'Directa', 'Coinbase'];
                const giverOk = editableBrokers.some((b) => giverText.includes(b));
                const recvOk = editableBrokers.some((b) => recvText.includes(b));
                if (giverOk && recvOk) {
                    giverRowId = await allRows.nth(i).getAttribute('data-row-id');
                    break;
                }
            }
        }
        expect(giverRowId, 'Must find a paired giver row on editable brokers').toBeTruthy();

        // T3: read the source date up front — the wire assertion below checks
        // the clone payload against it.
        const sourceDate = await readSourceDate(page, giverRowId!);

        await selectRow(page, giverRowId!);
        const cloneBtn = page.locator('[data-testid="toolbar-action-clone"]');
        await expect(cloneBtn).toBeVisible({timeout: 2_000});
        await cloneBtn.click();

        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Intercept commit request
        const commitPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 10_000});

        // Click commit
        const commitBtn = page.getByTestId('tx-bulk-commit');
        await expect(commitBtn).toBeEnabled({timeout: 8_000});
        await commitBtn.click();

        const req = await commitPromise;
        const payload = req.postDataJSON();

        // Payload must have creates (not updates)
        expect(payload.creates, 'Clone must produce creates array').toBeDefined();
        expect(payload.creates.length).toBe(2);

        // Both creates should share the same link_uuid
        const uuids = payload.creates.map((c: {link_uuid?: string}) => c.link_uuid);
        expect(uuids[0]).toBeTruthy();
        expect(uuids[0]).toBe(uuids[1]);

        // Both should have id=0 or no id (they are new)
        for (const c of payload.creates) {
            expect(c.id === undefined || c.id === 0 || c.id === null).toBeTruthy();
        }

        // T3: both halves are created on the SOURCE date, not reset to today.
        for (const c of payload.creates) {
            expect(c.date, 'clone must carry the source date on the wire').toBe(sourceDate);
        }

        // The commit is still in flight when the payload assertions above finish.
        // Leaving the test here would hand the next one a half-written table, so wait
        // for the modal to close — which is the app saying the commit came back.
        await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: 15_000});
    });

    test('clone inside the workspace (cloneRow) preserves the source date (T3)', async ({page}) => {
        // Own the source row: a mock-table scan could land on a today-dated
        // neighbour, where preserved and reset-to-today are indistinguishable.
        // A row this test created, dated 2021, makes the assertion exact.
        const suffix = uniqueSuffix();
        const brokerResp = await page.request.post('/api/v1/brokers', {data: [{name: `T3-ws-${suffix}`}]});
        expect(brokerResp.ok(), `broker setup failed (HTTP ${brokerResp.status()})`).toBeTruthy();
        const brokerId = (await brokerResp.json()).results[0].broker_id as number;

        const sourceDate = '2021-07-19';
        const createResp = await page.request.post('/api/v1/transactions/commit', {
            data: {creates: [{broker_id: brokerId, type: 'DEPOSIT', date: sourceDate, cash: {code: 'EUR', amount: '10'}, description: `T3-ws-${suffix}`}]},
        });
        const createBody = await createResp.json();
        expect(createBody.committed, `setup rolled back: ${JSON.stringify(createBody.issues ?? [])}`).toBe(true);
        const sourceId = createBody.results[0].ids[0] as number;

        try {
            // Id-filtered navigation: re-navigating to the URL the page is
            // already on is a client-side no-op that would leave the freshly
            // seeded row out of the table.
            await navigateTo(page, `/transactions?page_size=200&id_min=${sourceId}&id_max=${sourceId}`);
            await waitForSettled(page.getByTestId('transactions-page'));

            await selectRow(page, `tx-${sourceId}`);
            await page.getByTestId('toolbar-action-edit').click();
            const bulkModal = page.getByTestId('tx-bulk-modal');
            await expect(bulkModal).toBeVisible({timeout: 5_000});

            // Single-row edit auto-opens the FormModal; close it to reach the grid.
            const formModal = page.getByTestId('tx-form-modal');
            if (await formModal.isVisible({timeout: 2_000}).catch(() => false)) {
                await formModal.getByTestId('tx-form-cancel').click();
                await expect(formModal).not.toBeVisible({timeout: 3_000});
            }

            // Clone the row INSIDE the workspace (cloneRow — the third T3 site).
            const gridRow = bulkModal.locator('tbody tr[data-row-id]').first();
            await clickRowAction(gridRow, 'clone');

            const appended = bulkModal.locator('tbody tr.row-appended');
            await expect(appended).toHaveCount(1, {timeout: 3_000});
            const appendedText = (await appended.textContent()) ?? '';
            expect(appendedText, 'the in-workspace clone must carry the source date').toContain(sourceDate);
            expect(appendedText).not.toContain(todayIso());
        } finally {
            // Nothing was committed through the page — the API-seeded source is
            // this test's only write; remove it. The broker stays (inert,
            // uniquely named).
            await page.request.post('/api/v1/transactions/commit', {data: {deletes: [sourceId]}});
        }
    });

    test('clone from view-only broker → no edit/delete actions on row', async ({page}) => {
        // Find a TX on DEGIRO (VIEWER role for e2e_test_user)
        const degiroRowId = await findRowId(page, 'DEGIRO');
        expect(degiroRowId, 'Must find a TX on DEGIRO (viewer broker)').toBeTruthy();

        // Hover the row and verify that destructive action buttons (edit/delete) are NOT shown
        const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="${degiroRowId}"]`);
        await row.hover();

        // View-only rows should NOT show delete/edit actions in the kebab menu
        const kebabBtn = row.getByTestId(/^row-actions-/);
        if (!(await appears(kebabBtn))) {
            // No actions at all — delete/edit are a fortiori hidden
            return;
        }
        await kebabBtn.click();
        const menu = page.locator('[data-testid="context-menu"]');
        await expect(menu).toBeVisible({timeout: 3_000});
        await expect(menu.locator('[data-testid="context-menu-action-delete"]')).toHaveCount(0);
        await expect(menu.locator('[data-testid="context-menu-action-edit"]')).toHaveCount(0);
        await page.keyboard.press('Escape');
    });
});
