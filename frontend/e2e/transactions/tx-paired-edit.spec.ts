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
 * Mock data contract: populate_mock_data.py creates the asymmetric TRANSFER pairs
 * "[Asym-a]" (IB OWNER ↔ Directa EDITOR), "[Asym-b]" (IB OWNER ↔ Coinbase EDITOR) and
 * "[Asym-c]" (IB OWNER ↔ DEGIRO VIEWER). If a test fails because expected data is missing,
 * fix populate_mock_data.py — never skip.
 *
 * Bug 14 and Bug 7 only read those pairs, found through the API by their marker and checked
 * (linked to each other, editable where it matters), with the table narrowed to their ids —
 * never scanned by position or by CSS class. Bug 6 and TODO-B commit, so they never touch a
 * mock row: each works on an account of its own (fixtures/owned-pair.ts) — Bug 6 on an
 * INTEREST it books there, TODO-B on a pair between two brokers the account owns — and
 * deletes the account afterwards, its brokers and every row on them included.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, listBrokers, openAccountWithPair, openOwnedAccount, readTransactions, seededPair, type SeededPair} from '../fixtures/owned-pair';

// 45 s: login and the 20 s transactions-page gate share this budget; the old 20 s left the test no time under load.
test.setTimeout(45_000);

const COMMIT_PATH = '/api/v1/transactions/commit';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page, query = '') {
    await navigateTo(page, `/transactions${query}`);
    // The table being VISIBLE is not the table being LOADED: it renders empty
    // and fills in. The page publishes data-busy, so wait on that instead.
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000});
}

/** The table row of transaction `id`. */
function txRow(page: Page, id: number): Locator {
    return page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`);
}

/**
 * Open the table narrowed to these transactions (`id_min`/`id_max`) and wait for each of their
 * rows. A narrowed table holds nothing but that range, so no neighbour's row moves them and no
 * page boundary hides them — and, being filtered, it is in flat mode.
 */
async function goToRows(page: Page, ids: number[]) {
    await goToTransactions(page, `?id_min=${Math.min(...ids)}&id_max=${Math.max(...ids)}`);
    for (const id of ids) await expect(txRow(page, id), `transaction ${id} is in the narrowed table`).toBeVisible({timeout: 8_000});
}

/**
 * Tick a row's checkbox and wait for the state it publishes. Each row toggles on its own —
 * ticking one half of a pair leaves its partner as it was — so a caller that needs an exact
 * selection asserts the toolbar's count itself.
 */
async function selectRow(page: Page, rowId: string) {
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-${rowId}`);
    await expect(checkbox).toBeVisible({timeout: 2_000});
    // A checkbox is a toggle: read its state, and click only an unticked one.
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    // The toolbar is drawn only while something is selected, and publishes how many rows it holds.
    await expect(page.getByTestId('selection-toolbar')).not.toHaveAttribute('data-selected-count', '0');
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transaction Paired Edit', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // === Bug 14 — Edit paired opens BulkModal with both rows as "edited" ===
    test.describe('Bug 14 — Paired edit payload', () => {
        test('edit paired TRANSFER opens BulkModal with paired rows (not orphaned)', async ({page}) => {
            // A giver+receiver pair where both brokers are editable (Asym-a: IB ↔ Directa),
            // checked through the API — the Asym-d pair, whose partner is hidden, never qualifies.
            const {giver, receiver} = await seededPair(page, '[Asym-a]');
            const giverBroker = (await listBrokers(page)).find((broker) => broker.id === giver.broker_id);
            if (!giverBroker) throw new Error(`The broker of giver #${giver.id} is not visible to this user — check populate_mock_data.py`);
            await goToRows(page, [giver.id, receiver.id]);

            await selectRow(page, `tx-${giver.id}`);
            await selectRow(page, `tx-${receiver.id}`);
            await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '2');

            const editBtn = page.getByTestId('toolbar-action-edit');
            await expect(editBtn).toBeVisible({timeout: 2_000});
            await editBtn.click();

            // BulkModal must open
            const bulkModal = page.getByTestId('tx-bulk-modal');
            await expect(bulkModal).toBeVisible({timeout: 5_000});

            // Not orphaned: the pair arrives as ONE grid row, its receiver held behind it — the
            // row's date cell names the partner's date. The workspace holds exactly this
            // selection, so one row is a count the test made.
            const pairRow = bulkModal.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
            await expect(pairRow).toHaveCount(1, {timeout: 5_000});
            await expect(pairRow.getByTestId('tx-bulk-date')).toHaveAttribute('data-partner-date', receiver.date);

            // With two rows selected the workspace opens no FormModal by itself (it does for
            // one), so open it from the grid, on the pair's row.
            await pairRow.dblclick();
            const formModal = page.getByTestId('tx-form-modal');
            await expect(formModal).toBeVisible({timeout: 5_000});

            // A TRANSFER pair edits in the dual layout, and its From side is populated (not
            // empty): it names the giver's broker.
            const dualFrom = formModal.getByTestId('tx-form-dual-from');
            await expect(dualFrom).toBeVisible({timeout: 2_000});
            await expect(dualFrom.getByRole('combobox')).toContainText(giverBroker.name);
        });
    });

    // === Bug 7 — Flat mode paired adjacency ===
    test.describe('Bug 7 — Flat mode paired adjacent', () => {
        test('paired rows stay adjacent in flat mode', async ({page}) => {
            // Three seeded pairs, linked and visible to this user (Asym-c's receiver sits on a
            // broker it only views: adjacency is not about editing).
            const pairs: SeededPair[] = [];
            for (const marker of ['[Asym-a]', '[Asym-b]', '[Asym-c]']) pairs.push(await seededPair(page, marker, {editable: false}));

            // Narrowing the table by id is a filter, and any filter puts it in flat mode: every
            // row independent, a pair kept together only because the table keeps it so.
            await goToRows(
                page,
                pairs.flatMap(({giver, receiver}) => [giver.id, receiver.id]),
            );

            // Each receiver sits right below its own giver — a structural relation between two
            // known rows, not a scan of positions.
            const table = page.getByTestId('tx-table');
            for (const {giver, receiver} of pairs) {
                await expect(table.locator(`tbody tr[data-row-id="tx-${giver.id}"] + tr[data-row-id="tx-${receiver.id}"]`), `receiver #${receiver.id} sits right below its giver #${giver.id}`).toHaveCount(1);
            }
        });
    });
});

// Same title as the block above, so the tests keep their full names. A block of its own
// because the TEST_USER login above must not run for them: each signs in as the disposable
// account that owns its rows.
test.describe('Transaction Paired Edit', () => {
    let owned = emptyOwnedAccount();

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
    });

    // afterEach, not `finally`: it runs after a timeout too, and an error of its own
    // is reported beside the test's instead of replacing it.
    test.afterEach(async ({page, request}) => {
        await cleanupOwnedAccount(page, request, owned);
    });

    // === Bug 6 — Clone INTEREST resets quantity to 0 ===
    test.describe('Bug 6 — Clone INTEREST', () => {
        test('clone INTEREST sets quantity to 0', async ({page, request}, testInfo) => {
            // The account goes through the real welcome flow before the clone itself.
            test.setTimeout(60_000);

            // An INTEREST of this test's own, on a broker its account owns: the seeded one sits
            // on a broker e2e_test_user only views, where a clone could never be committed.
            await openOwnedAccount(page, request, owned, `int_${testInfo.project.name}`);
            const broker = await createOwnedBroker(page, 'interest', owned.brokerIds);
            const description = `Bug 6 INTEREST ${uniqueSuffix()}`;
            const [sourceId] = await commitCreates(page, [{broker_id: broker.id, type: 'INTEREST', date: daysAgoIso(20), cash: {code: 'EUR', amount: '7.50'}, description}], 'commit the INTEREST to clone');
            await goToRows(page, [sourceId]);

            await selectRow(page, `tx-${sourceId}`);
            await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '1');
            const cloneBtn = page.getByTestId('toolbar-action-clone');
            await expect(cloneBtn).toBeVisible({timeout: 2_000});
            await cloneBtn.click();

            // Cloning one row opens the BulkModal and auto-opens the FormModal on the clone.
            const bulkModal = page.getByTestId('tx-bulk-modal');
            const formModal = page.getByTestId('tx-form-modal');
            await expect(bulkModal).toBeVisible({timeout: 5_000});
            await expect(formModal).toBeVisible({timeout: 5_000});

            // INTEREST forbids a quantity, so the form shows no quantity field to read: the
            // quantity the clone carries exists only in what it sends. Back to the grid, then.
            await formModal.getByTestId('tx-form-cancel').click();
            await expect(formModal).toBeHidden({timeout: 3_000});

            const commitBtn = bulkModal.getByTestId('tx-bulk-commit');
            await expect(commitBtn).toBeEnabled({timeout: 8_000});
            // Armed before the click: a response is an edge, not a state.
            const commitPromise = page.waitForResponse((res) => res.request().method() === 'POST' && new URL(res.url()).pathname === COMMIT_PATH, {timeout: 15_000});
            await commitBtn.click();
            const response = await commitPromise;

            const payload = response.request().postDataJSON() as {creates?: Array<{type?: string; quantity?: string}>};
            expect(
                (payload.creates ?? []).map((create) => create.type),
                'the commit creates the one clone',
            ).toEqual(['INTEREST']);
            expect(Number(payload.creates?.[0]?.quantity), `the clone is sent with quantity 0 (sent: ${JSON.stringify(payload.creates?.[0]?.quantity)})`).toBe(0);
            const body = (await response.json()) as {committed?: boolean; issues?: unknown[]};
            expect(body.committed, `Commit should succeed. Issues: ${JSON.stringify(body.issues)}`).toBe(true);
            // The editor closing is the app saying the commit came back.
            await expect(bulkModal).toBeHidden({timeout: 10_000});

            // ...and the server holds it so.
            const clones = (await readTransactions(page, {broker_id: broker.id})).filter((tx) => tx.description === description && tx.id !== sourceId);
            expect(
                clones.map((tx) => [tx.type, Number(tx.quantity)]),
                'one INTEREST clone, saved with quantity 0',
            ).toEqual([['INTEREST', 0]]);
        });
    });

    // === TODO-B — Edit paired TRANSFER: commit sends updates (not creates) ===
    //
    // Why not a seeded pair: the commit rewrites the pair's description for good, on both
    // halves. Measured when it still edited one: the pair it reached was the `delete-consume`
    // ETH one, which tx-delete's A2-confirm then looked up by its "[delete-consume] … ETH" text
    // — gone after this test. A2-confirm deletes a pair of its own since V-25 (13/10), but a
    // seeded pair rewritten for good still changes what every later reader of it finds.
    test.describe('TODO-B — Edit paired commit payload', () => {
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
            const pairRow = bulkModal.getByTestId('tx-bulk-body').locator('tr[data-row-id]').filter({hasText: pair.giver.name});
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
