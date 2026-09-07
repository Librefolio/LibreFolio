/**
 * Transaction Delete E2E Tests — Phase 07 · Part 4 · Round 6 · Plan B23
 *
 * T4 (2026-09): the dedicated TransactionDeleteModal no longer exists. A
 * single-row delete now routes through the bulk workspace
 * (`bulkIntent = {action: 'delete', txIds: [row.id]}`), which:
 *   - pre-marks the staged row(s) for deletion (`tr.row-deleted`),
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
 * Mock data contract: populate_mock_data.py creates:
 *   - "delete-safe" tagged TX: DEPOSIT on IB, FEE on Directa, TRANSFER ETH IB↔Coinbase
 *   - "delete-consume" tagged TX: a SECOND paired TRANSFER ETH IB↔Coinbase, single-use,
 *     which A2-confirm destroys. The "delete-safe" pair must survive: A2 asserts it does,
 *     and tx-bulk-suggest-ux / tx-crud-full / tx-split-promote all read it.
 *   - "access-test" tagged TX: Asym-a (IB↔Directa), Asym-b (IB↔Coinbase),
 *     Asym-c (IB↔DEGIRO=viewer), Asym-d (IB↔Hidden)
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {appears} from '../fixtures/probe';
import {maximisePageSize} from '../fixtures/paging';
import {uniqueSuffix} from '../fixtures/unique';

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

/** The staged rows that are marked for deletion. */
function bulkDeletedRows(page: Page): Locator {
    return page.locator('[data-testid="tx-bulk-body"] tr.row-deleted');
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
// Part A — single-row delete through the bulk workspace (T4)
// ---------------------------------------------------------------------------

test.describe('Single-row delete via bulk workspace (T4)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    // === A1: standalone delete ===

    test('A1: standalone delete — workspace opens with the row pre-marked, cancel keeps row', async ({page}) => {
        const row = await findRow(page, 'delete-safe', 'Small deposit');
        expect(row, 'delete-safe DEPOSIT row not found — run ./dev.py db create-clean — check populate_mock_data.py').toBeTruthy();

        await openDeleteWorkspace(row!);

        // Exactly the one row we picked is staged, and it is staged as a DELETE.
        // (Row ids in the workspace are fresh client-side tempIds, so identity is
        // asserted by count + status class, not by cross-referencing the tx id.)
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

    test('A1-confirm: standalone delete — commit removes the row', async ({page}) => {
        // Use the delete-safe FEE (won't cause balance issues)
        const row = await findRow(page, 'delete-safe', 'Platform fee');
        expect(row, 'delete-safe FEE row not found — check populate_mock_data.py').toBeTruthy();
        const rowId = await row!.getAttribute('data-row-id');

        await openDeleteWorkspace(row!);
        await expect(bulkDeletedRows(page)).toHaveCount(1);

        const {payload, committed} = await commitDeleteWorkspace(page);
        expect(committed, 'the delete commit must not roll back').toBe(true);
        // The wire carries exactly the transaction we picked — the DOM row id is
        // `tx-<id>`, the payload speaks transaction ids.
        const txId = Number(rowId!.replace(/^(?:tx|ghost)-/, ''));
        expect(payload.deletes ?? []).toEqual([txId]);

        await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});

        // Row gone. Asserting on findRow()'s result directly is asserting "not there
        // YET": it scans once and does not retry. Assert on the row's own id instead —
        // toHaveCount retries, is exact, and does not re-read every row in the table.
        await expect(page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="${rowId}"]`)).toHaveCount(0);
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

    test('A2-confirm: paired delete — commit removes both halves', async ({page}) => {
        // Deliberately NOT the "delete-safe" pair A2 uses. This one is destructive, and
        // the mock ships a second pair for exactly that: tagged `delete-consume`, single
        // use, described without the "delete-safe" substring so the finders elsewhere
        // never land on it. Sharing one pair with A2 meant racing it under fullyParallel
        // and leaving every later spec without a paired row.
        const row = await findRow(page, 'delete-consume', 'ETH');
        expect(row, 'delete-consume TRANSFER ETH row not found — run ./dev.py test db populate --force --clean; it is single-use and A2-confirm eats it').toBeTruthy();
        const rowId = await row!.getAttribute('data-row-id');

        // The table does not publish the link between two halves, so the sibling is read
        // from the server before acting: `related_transaction_id` is bidirectional (see
        // TXReadItem), so one GET names both halves of *this* pair. The DOM id is not the
        // transaction id — TransactionsTable prefixes it (`tx-` / `ghost-` for the
        // receiver half) to keep the two id-spaces apart in DataTable's selection state.
        const txId = Number(rowId!.replace(/^(?:tx|ghost)-/, ''));
        expect(Number.isInteger(txId), `row id ${rowId} does not carry a transaction id`).toBeTruthy();
        const before = await page.request.get(`/api/v1/transactions?ids=${txId}`);
        expect(before.ok(), `the row under test must be readable before it is deleted (HTTP ${before.status()})`).toBeTruthy();
        const [item] = (await before.json()) as Array<{id: number; related_transaction_id: number | null}>;
        expect(item?.related_transaction_id, 'A2-confirm is about a *paired* row; this one is not linked').toBeTruthy();
        const pairQuery = `ids=${item.id}&ids=${item.related_transaction_id}`;

        await openDeleteWorkspace(row!);

        // Both halves staged through one collapsed row: the commit payload must
        // name BOTH transaction ids, or the backend pair guard
        // (pairDeleteIncomplete) would refuse the batch.
        const {payload, committed} = await commitDeleteWorkspace(page);
        expect(committed, `the paired delete commit must not roll back (deletes=${JSON.stringify(payload.deletes ?? [])})`).toBe(true);
        expect(new Set(payload.deletes ?? [])).toEqual(new Set([item.id, item.related_transaction_id]));

        await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});

        // Both halves gone from the table — see the note above on why this asserts
        // on the id.
        await expect(page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="${rowId}"]`)).toHaveCount(0);

        // Asked of the server, about these two ids, instead of counting every row whose
        // text matches. That count was a global total this test never created: it read
        // "no row in the world says delete-safe ETH", and `tx-clone` legitimately commits
        // a clone of that pair and removes it in its own afterEach — so between those two
        // moments the shared table holds two extra matching rows. The poll sampled inside
        // that window and failed with 2 received, in a run where the delete had worked
        // perfectly. Neighbours are allowed to add rows; the subject here is the pair this
        // test deleted, and only the server can answer that without guessing.
        await expect
            .poll(async () => ((await (await page.request.get(`/api/v1/transactions?${pairQuery}`)).json()) as unknown[]).length, {
                message: 'both halves of the deleted pair must be gone from the server',
                timeout: 8_000,
            })
            .toBe(0);
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
        const suffix = uniqueSuffix();
        const brokerResp = await page.request.post('/api/v1/brokers', {data: [{name: `T4-delref-${suffix}`}]});
        expect(brokerResp.ok(), `broker setup failed (HTTP ${brokerResp.status()})`).toBeTruthy();
        const brokerId = (await brokerResp.json()).results[0].broker_id as number;

        // POST /assets is bulk-only: a list in, per-item results out (201).
        const assetResp = await page.request.post('/api/v1/assets', {
            data: [{display_name: `T4-delref-asset-${suffix}`, asset_type: 'STOCK', currency: 'EUR'}],
        });
        expect(assetResp.status(), `asset setup failed (HTTP ${assetResp.status()})`).toBe(201);
        const assetResults = (await assetResp.json()).results as Array<{asset_id: number; success: boolean; message?: string}>;
        expect(assetResults[0]?.success, `asset setup refused: ${assetResults[0]?.message ?? 'unknown'}`).toBe(true);
        const assetId = assetResults[0].asset_id;

        const marker = `T4-delref-${suffix}`;
        const createResp = await page.request.post('/api/v1/transactions/commit', {
            data: {
                creates: [
                    // ADJUSTMENT with qty>0 requires an explicit cost basis.
                    {broker_id: brokerId, asset_id: assetId, type: 'ADJUSTMENT', date: '2025-01-10', quantity: '5', cost_basis_override: {code: 'EUR', amount: '10'}, description: marker},
                    // The counterpart's description must NOT contain the marker —
                    // findRow matches by inclusion, and the row under test is the +5.
                    {broker_id: brokerId, asset_id: assetId, type: 'ADJUSTMENT', date: '2025-01-11', quantity: '-5', description: `counterpart-${suffix}`},
                ],
            },
        });
        expect(createResp.ok(), `transaction setup failed (HTTP ${createResp.status()})`).toBeTruthy();
        const createBody = await createResp.json();
        expect(createBody.committed, `setup commit rolled back: ${JSON.stringify(createBody.issues ?? [])}`).toBe(true);
        const createdIds = (createBody.results as Array<{ids?: number[]}>).flatMap((r) => r.ids ?? []);
        expect(createdIds).toHaveLength(2);

        try {
            // Re-navigate with an id filter — navigating to the URL the page is
            // already on is a client-side no-op that reloads nothing, and the two
            // rows were created AFTER the page first loaded. The id filter makes
            // the URL (and the fetched set) genuinely new.
            await navigateTo(page, `/transactions?page_size=200&id_min=${createdIds[0]}&id_max=${createdIds[0]}`);
            await waitForSettled(page.getByTestId('transactions-page'));
            // Address the row by its own id, not by text: the broker and asset
            // names carry the suffix too, so a text search matches the
            // counterpart row as well (and date order would pick the −5 — whose
            // deletion is legal — every time).
            const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="tx-${createdIds[0]}"]`);
            await expect(row, 'the +5 ADJUSTMENT this test just created is not in the table').toBeVisible({timeout: 8_000});

            const modal = await openDeleteWorkspace(row);
            await expect(bulkDeletedRows(page)).toHaveCount(1);

            // Commit → the server refuses (asset balance would go negative) → the
            // workspace stays open and reports the issue inline. Assert the
            // banner and that it carries at least one issue — never its text,
            // which is localized.
            const {payload, committed} = await commitDeleteWorkspace(page);
            expect(payload.deletes ?? [], 'the wire must name the +5 row, not its counterpart').toEqual([createdIds[0]]);
            expect(committed, 'a delete that would drive the asset balance negative must roll back').toBe(false);

            await expect(modal).toBeVisible();
            const banner = modal.getByTestId('tx-bulk-error');
            await expect(banner).toBeVisible({timeout: 5_000});
            // The refusal is a balance issue, and balance issues render in their
            // own list inside the banner (no per-item testid — the banner is the
            // testid anchor; the <li> proves an issue actually rendered).
            await expect(banner.locator('ul li').first(), 'the refusal must be itemized inline, not just a bare banner').toBeVisible();

            // Cancel closes (the staged delete is the *initial* state here, so no
            // discard confirmation interposes).
            await modal.getByTestId('tx-bulk-cancel').click();
            await expect(modal).not.toBeVisible({timeout: 5_000});
        } finally {
            // Restore what this test wrote: both ADJUSTMENTs together net to zero,
            // so the batch delete is legal. The empty broker and the asset stay —
            // inert reference data with a unique name, as every API-level test
            // leaves them.
            await page.request.post('/api/v1/transactions/commit', {data: {deletes: createdIds}});
        }
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
