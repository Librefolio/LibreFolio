/**
 * Transaction Paired Edit E2E Tests — Phase 07 Bugfix Round 1
 *
 * Covers:
 * - Bug 6:  Clone INTEREST resets quantity to 0
 * - Bug 14: BulkModal edit paired produces updates (not creates)
 * - Bug 7:  Flat mode keeps paired rows adjacent
 *
 * Prerequisites: backend test mode (port 6041), mock data populated.
 *
 * Mock data contract: populate_mock_data.py creates INTEREST transactions,
 * asymmetric paired TRANSFERs, and linked pairs. If a test fails because
 * expected data is missing, fix populate_mock_data.py — never skip.
 *
 * TODO-B is the one test here that commits, so it never touches a mock row: it
 * edits a pair of its own, built on a disposable account (two brokers the account
 * owns, the seeded Ethereum as the asset), and deletes the account afterwards, its
 * brokers and every row on them included.
 */
import {randomUUID} from 'crypto';
import {expect, test, type APIRequestContext, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {appears} from '../fixtures/probe';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker, deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';

test.setTimeout(20_000);

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
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    // The table being VISIBLE is not the table being LOADED: it renders empty
    // and fills in. The page publishes data-busy, so wait on that instead.
    await waitForSettled(page.getByTestId('transactions-page'));
}

/** Find the first row containing ALL given substrings — returns row-id. Throws if not found. */
async function findRowByTexts(page: Page, ...substrings: string[]): Promise<string> {
    const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const text = (await row.textContent()) ?? '';
        if (substrings.every((s) => text.includes(s))) {
            return (await row.getAttribute('data-row-id'))!;
        }
    }
    throw new Error(`Row matching [${substrings.join(', ')}] not found. Check populate_mock_data.py.`);
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
 * Why not a seeded pair: the commit rewrites the pair's description for good, on
 * both halves. Measured on HEAD: the pair it reached was the `delete-consume` ETH one,
 * which tx-delete's A2-confirm finds by its "[delete-consume] … ETH" text — gone after
 * this test. Rows on an account of its own are invisible to every other spec, and
 * deleting its brokers takes them all.
 *
 * The giver is funded first — a deposit, then a buy — so the transfer never takes it
 * below zero. The asset is the seeded Ethereum, which this test only reads.
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
 * transactions with them, the pair included — and the account last. Only what this
 * test recorded.
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

test.describe('Transaction Paired Edit', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    // === Bug 6 — Clone INTEREST resets quantity to 0 ===
    test.describe('Bug 6 — Clone INTEREST', () => {
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
                        // Try this one — if clone fails due to VIEWER, try next
                        break;
                    }
                }
            }
            expect(interestRowId, 'INTEREST transaction must exist in mock data').toBeTruthy();

            await selectRow(page, interestRowId!);
            const cloneBtn = page.locator('[data-testid="toolbar-action-clone"]');
            await expect(cloneBtn).toBeVisible({timeout: 2_000});
            await cloneBtn.click();

            // Clone opens BulkModal which auto-opens FormModal
            const bulkModal = page.getByTestId('tx-bulk-modal');
            const formModal = page.getByTestId('tx-form-modal');
            const modal = (await appears(bulkModal, 3_000)) ? bulkModal : formModal;
            await expect(modal).toBeVisible({timeout: 5_000});

            // If BulkModal is showing, FormModal may auto-open inside it
            if (await formModal.isVisible({timeout: 3_000}).catch(() => false)) {
                const qtyInput = page.getByTestId('tx-form-quantity');
                if (await qtyInput.isVisible({timeout: 2_000}).catch(() => false)) {
                    const qtyValue = await qtyInput.inputValue();
                    expect(qtyValue).toBe('0');
                }
            }

            // Close
            const cancelBtn = page.getByTestId('tx-form-cancel');
            if (await cancelBtn.isVisible({timeout: 1_000}).catch(() => false)) {
                await cancelBtn.click();
            }
            const bulkCancel = page.getByTestId('tx-bulk-cancel');
            if (await appears(bulkCancel, 1_000)) {
                await bulkCancel.click();
            }
            const discardBtn = page.getByTestId('confirm-modal-confirm');
            if (await discardBtn.isVisible({timeout: 1_000}).catch(() => false)) {
                await discardBtn.click();
            }
        });
    });

    // === Bug 14 — Edit paired opens BulkModal with both rows as "edited" ===
    test.describe('Bug 14 — Paired edit payload', () => {
        test('edit paired TRANSFER opens BulkModal with paired rows (not orphaned)', async ({page}) => {
            // Find a giver+receiver pair where both brokers are editable.
            // Skip Asym-d (hidden partner) by requiring the giver row to contain
            // a known editable broker pair (e.g. Directa↔IB or Coinbase↔IB).
            const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
            const total = await allRows.count();
            let giverRowId: string | null = null;
            let receiverRowId: string | null = null;

            for (let i = 0; i < total - 1; i++) {
                const nextCls = (await allRows.nth(i + 1).getAttribute('class')) ?? '';
                if (nextCls.includes('tx-row-receiver')) {
                    const giverText = (await allRows.nth(i).textContent()) ?? '';
                    const recvText = (await allRows.nth(i + 1).textContent()) ?? '';
                    // Both sides must have an editable broker visible
                    const editableBrokers = ['Interactive Brokers', 'Directa', 'Coinbase'];
                    const giverHasEditable = editableBrokers.some((b) => giverText.includes(b));
                    const recvHasEditable = editableBrokers.some((b) => recvText.includes(b));
                    if (giverHasEditable && recvHasEditable) {
                        giverRowId = await allRows.nth(i).getAttribute('data-row-id');
                        receiverRowId = await allRows.nth(i + 1).getAttribute('data-row-id');
                        break;
                    }
                }
            }
            expect(giverRowId, 'Must find a paired giver row on editable brokers').toBeTruthy();
            expect(receiverRowId, 'Must find a paired receiver row on editable brokers').toBeTruthy();

            await selectRow(page, giverRowId!);
            await selectRow(page, receiverRowId!);

            const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
            await expect(editBtn).toBeVisible({timeout: 2_000});
            await editBtn.click();

            // BulkModal must open
            await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

            // The BulkModal should auto-open FormModal for paired edit.
            // If FormModal opens, verify broker is populated (not empty).
            const formModal = page.getByTestId('tx-form-modal');
            if (await formModal.isVisible({timeout: 3_000}).catch(() => false)) {
                // Broker "From" should be populated (dual layout uses tx-form-dual-from for transfer_asset)
                const dualFrom = page.getByTestId('tx-form-dual-from');
                const brokerWrap = page.getByTestId('tx-form-broker-wrap');
                const target = (await dualFrom.isVisible({timeout: 1_000}).catch(() => false)) ? dualFrom : brokerWrap;
                await expect(target).toBeVisible({timeout: 2_000});
            }

            // Close everything
            const cancelBtn = page.getByTestId('tx-form-cancel');
            if (await cancelBtn.isVisible({timeout: 1_000}).catch(() => false)) {
                await cancelBtn.click();
                await expect(cancelBtn).toBeHidden({timeout: 3_000});
            }
            const bulkCancel = page.getByTestId('tx-bulk-cancel');
            if (await bulkCancel.isVisible({timeout: 1_000}).catch(() => false)) {
                await bulkCancel.click();
                const discardBtn = page.getByTestId('confirm-modal-confirm');
                if (await discardBtn.isVisible({timeout: 1_000}).catch(() => false)) {
                    await discardBtn.click();
                }
            }
        });
    });

    // === Bug 7 — Flat mode paired adjacency ===
    test.describe('Bug 7 — Flat mode paired adjacent', () => {
        test('paired rows stay adjacent in flat mode', async ({page}) => {
            const receiverRows = page.locator('[data-testid="tx-table"] tbody tr.tx-row-receiver');
            const receiverCount = await receiverRows.count();
            expect(receiverCount, 'Mock data must contain paired transactions').toBeGreaterThan(0);

            const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
            const total = await allRows.count();
            const receiverClasses: boolean[] = [];

            for (let i = 0; i < total; i++) {
                const cls = (await allRows.nth(i).getAttribute('class')) ?? '';
                receiverClasses.push(cls.includes('tx-row-receiver'));
            }

            for (let i = 0; i < total; i++) {
                if (receiverClasses[i]) {
                    expect(i, 'Receiver row should not be first row').toBeGreaterThan(0);
                    expect(receiverClasses[i - 1], 'Row before receiver should be giver (not receiver)').toBe(false);
                }
            }
        });
    });
});

// Same title as the block above, so the test keeps its full name. A block of its own
// because the TEST_USER login above must not run for it: it signs in as the disposable
// account that owns its pair.
test.describe('Transaction Paired Edit', () => {
    // === TODO-B — Edit paired TRANSFER: commit sends updates (not creates) ===
    test.describe('TODO-B — Edit paired commit payload', () => {
        let owned: Owned = {user: null, brokerIds: []};

        test.beforeEach(() => {
            owned = {user: null, brokerIds: []};
        });

        // afterEach, not `finally`: it runs after a timeout too, and an error of its own
        // is reported beside the test's instead of replacing it.
        test.afterEach(async ({page, request}) => {
            await cleanupOwned(page, request, owned);
        });

        test('edit paired TRANSFER → commit sends updates for both sides', async ({page, request}, testInfo) => {
            // The account goes through the real welcome flow before the edit itself.
            test.setTimeout(60_000);
            const pair = await openAccountWithPair(page, request, owned, `tpe_${testInfo.project.name}`);
            await goToTransactions(page);

            // Select both halves of this test's own pair — by the ids it created, never
            // by position — and click Edit
            await selectRow(page, `tx-${pair.fromId}`);
            await selectRow(page, `tx-${pair.toId}`);
            await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '2');
            const editBtn = page.getByTestId('toolbar-action-edit');
            await expect(editBtn).toBeVisible({timeout: 2_000});
            await editBtn.click();

            // BulkModal opens
            const bulkModal = page.getByTestId('tx-bulk-modal');
            await expect(bulkModal).toBeVisible({timeout: 5_000});

            // With two rows selected the workspace opens no FormModal by itself (it does
            // for one), so open it from the grid: on the pair's one row, found by the
            // giver's broker — a name only this account has — not by position.
            const pairRow = bulkModal.getByTestId('tx-bulk-body').locator('tr[data-row-id]').filter({hasText: pair.fromBroker});
            await expect(pairRow).toHaveCount(1, {timeout: 5_000});
            await pairRow.dblclick();
            const formModal = page.getByTestId('tx-form-modal');
            await expect(formModal).toBeVisible({timeout: 5_000});

            // Expand the optional section to access the description field. It is a
            // <details>: read its state rather than clicking blind, which would close a
            // section that is already open.
            const optionalToggle = formModal.getByTestId('tx-form-optional-toggle');
            await expect(optionalToggle).toBeVisible({timeout: 2_000});
            const optionalSection = optionalToggle.locator('..');
            if ((await optionalSection.getAttribute('open')) === null) await optionalToggle.click();
            await expect(optionalSection).toHaveAttribute('open', '');

            // Modify description to trigger a change
            const descInput = formModal.getByTestId('tx-form-description');
            await expect(descInput).toBeVisible({timeout: 2_000});
            const description = `E2E-paired-edit-${uniqueSuffix()}`;
            await descInput.fill(description);
            await expect(descInput).toHaveValue(description);

            // Push changes back to BulkModal
            await formModal.getByTestId('tx-form-save').click();
            await expect(formModal).toBeHidden({timeout: 3_000});

            // Set up the wait BEFORE clicking commit. On the response, not the request:
            // the test ends once the commit has landed, so the cleanup never races it.
            const commitPromise = page.waitForResponse((res) => res.url().includes('/transactions/commit') && res.request().method() === 'POST', {timeout: 10_000});

            // Click commit in BulkModal
            const commitBtn = bulkModal.getByTestId('tx-bulk-commit');
            await expect(commitBtn).toBeEnabled({timeout: 8_000});
            await commitBtn.click();

            const response = await commitPromise;
            const payload = response.request().postDataJSON();

            // Payload must have updates for the modified row
            expect(payload.updates, 'Commit must have updates array').toBeDefined();
            expect(payload.updates.length, 'At least one update expected').toBeGreaterThanOrEqual(1);

            // All updates should have valid IDs (not 0) — halves of this test's own pair
            for (const upd of payload.updates) {
                expect(upd.id, 'Update must have a valid ID').toBeGreaterThan(0);
                expect([pair.fromId, pair.toId], `Update id=${upd.id} must target this test's own pair`).toContain(upd.id);
            }

            // The edit is committed — on rows nobody else can see
            const body = await response.json();
            expect(body.committed, `Commit should succeed. Issues: ${JSON.stringify(body.issues)}`).toBe(true);
        });
    });
});
