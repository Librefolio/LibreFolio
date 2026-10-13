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
 * - C5a: two SINGLE rows of one type cloned → two independent rows, never one pair
 * - C5b: a pair and a single cloned together → the pair stays a pair, the single stays single
 *
 * T3 (2026-09): cloning is the correction workflow — duplicating a
 * misclassified historical row and editing the copy. Resetting the date to
 * today destroyed exactly the field being corrected, so every clone path
 * (resolveInitialRows / createOpFromClone / cloneRow) now preserves it.
 *
 * Prerequisites: backend test mode (port 6041), mock data populated.
 * Mock data contract: populate_mock_data.py creates the "[Asym-a]" TRANSFER pair
 * (IB OWNER ↔ Directa EDITOR), the standalone "Initial EUR funding from bank" DEPOSIT on
 * IB (OWNER), and rows on DEGIRO, where e2e_test_user is a VIEWER.
 *
 * The tests that only open the clone editor borrow those seeded rows — found through the API
 * by their marker and checked, then reached with the table narrowed to their ids, never by
 * position. Every test that commits works on rows of its own: a broker it creates, or an
 * account of its own (fixtures/owned-pair.ts), deleted afterwards with everything on it.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {trackTransactionWrites, type TransactionWriteTracker} from '../fixtures/db-cleanup';
import {todayIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {cleanupOwnedAccount, emptyOwnedAccount, listBrokers, openAccountWithPair, readTransactions, seededPair, seededRow} from '../fixtures/owned-pair';

test.setTimeout(25_000);

/** The seeded pair and standalone row the editor-only tests clone: e2e_test_user can edit them, and neither is dated today. */
const CLONE_PAIR = '[Asym-a]';
const CLONE_STANDALONE = 'Initial EUR funding from bank';
/** The seeded broker on which e2e_test_user is a VIEWER. */
const VIEWER_BROKER = 'DEGIRO';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page, query = '') {
    await navigateTo(page, `/transactions${query}`);
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    // The table being VISIBLE is not the table being LOADED: it renders empty
    // and fills in. The page publishes data-busy, so wait on that instead.
    await waitForSettled(page.getByTestId('transactions-page'));
}

/** The table row of transaction `id`. */
function txRow(page: Page, id: number): Locator {
    return page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`);
}

/**
 * Open the table narrowed to these transactions (`id_min`/`id_max`) and wait for each of their
 * rows. The narrowed table holds nothing but that range, so no neighbour's row moves them and
 * no page boundary hides them. A fresh navigation, too: re-navigating to the URL the page is
 * already on would be a client-side no-op that leaves a freshly seeded row out of the table.
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

// ---------------------------------------------------------------------------
// C5 — which clones get linked: owned rows on an owned broker
// ---------------------------------------------------------------------------
//
// The clone editor hands a `link_uuid` to the rows it should keep together: two
// creates sharing one are folded into a single paired grid row, and the backend
// links them (`resolve_create_links`) when their type, description and tags agree.
// So the link must follow the pairs that exist in the database — never the count
// or the type of the selected rows. Every row here is the test's own: a broker
// nobody else uses, rows with descriptions only this test knows, found by content
// and read back from the server.

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;
/** Not today: the clones keep their source's date (T3), so it stays apart from a neighbour's fresh rows. */
const C5_DATE = '2023-05-17';
/** C5b's single row funds the EUR leg of its conversion the day before, so no balance goes negative. */
const C5_FUND_DATE = '2023-05-16';
/** The INTEREST test's own source row: any date after its broker opened. */
const INTEREST_DATE = '2023-06-21';

type OwnedTx = {id: number; type: string; description?: string | null; related_transaction_id?: number | null};
type CommitBody = {committed?: boolean; issues?: unknown[]; results?: Array<{operation: string; index?: number; status?: string; ids?: number[]}>};
type SourceRow = {type: 'DEPOSIT' | 'FX_CONVERSION' | 'INTEREST'; date: string; cash: {code: string; amount: string}; description: string; link_uuid?: string};
type OwnedBroker = {brokerId: number; suffix: string; sourceIds: number[]};

/** A broker only this test uses. Its name sorts after every seeded broker, so no neighbour taking "the first broker" lands on it. */
async function createOwnedBroker(page: Page, name: string): Promise<number> {
    const response = await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2020-01-01'}]});
    expect(response.ok(), `create owned broker: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null}>};
    const created = results.find((result) => result.name === name);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`Owned broker "${name}" was not created: ${JSON.stringify(results)}`);
    return created.broker_id;
}

/** Commit the source rows in one batch, through the API; their ids come back in the order given and are recorded for cleanup. */
async function commitSources(page: Page, owned: OwnedBroker, rows: SourceRow[]): Promise<number[]> {
    const response = await page.request.post(COMMIT_PATH, {data: {creates: rows.map((row) => ({broker_id: owned.brokerId, ...row}))}});
    expect(response.ok(), `commit the source rows: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const body = (await response.json()) as CommitBody;
    expect(body.committed, `the source rows rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    const ids = rows.map((_, index) => body.results?.find((result) => result.operation === 'create' && result.index === index && result.status === 'success')?.ids?.[0]);
    owned.sourceIds.push(...ids.filter((id): id is number => typeof id === 'number'));
    if (ids.some((id) => typeof id !== 'number')) throw new Error(`A source row got no id: ${JSON.stringify(body.results)}`);
    return ids as number[];
}

/** Every row on the owned broker, as the server has it. */
async function brokerRows(page: Page, brokerId: number): Promise<OwnedTx[]> {
    const response = await page.request.get(`${API}/transactions`, {params: {broker_id: brokerId}});
    expect(response.ok(), `GET ${API}/transactions?broker_id=${brokerId}: HTTP ${response.status()}`).toBe(true);
    return (await response.json()) as OwnedTx[];
}

/** `{id: related_transaction_id}` per row — `null` for a row linked to nothing. */
function linksOf(rows: OwnedTx[]): Record<number, number | null> {
    return Object.fromEntries(rows.map((row) => [row.id, row.related_transaction_id ?? null]));
}

/**
 * Select the owned rows in the transactions table, then press the toolbar's Clone.
 *
 * The table is filtered to the owned broker, and each group of rows is found by the
 * description only this test wrote — never by position — and must be exactly the rows the
 * test created before any of them is ticked. A checkbox is a toggle, so its state is read
 * and only an unticked one is clicked; the toolbar's count then proves nothing else is
 * selected.
 */
async function cloneFromTable(page: Page, brokerId: number, groups: Array<{description: string; ids: number[]}>): Promise<void> {
    await navigateTo(page, `/transactions?broker_id=${brokerId}`);
    await waitForSettled(page.getByTestId('transactions-page'));
    const table = page.getByTestId('tx-table');
    for (const {description, ids} of groups) {
        const rows = table.locator('tbody tr[data-row-id]').filter({hasText: description});
        await expect.poll(() => rows.evaluateAll((trs) => trs.map((tr) => tr.getAttribute('data-row-id') ?? '').sort()), {message: `the rows described "${description}" are exactly the ones this test created`, timeout: 10_000}).toEqual(ids.map((id) => `tx-${id}`).sort());
        for (const id of ids) {
            const checkbox = table.getByTestId(`dt-row-checkbox-tx-${id}`);
            if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
            await expect(checkbox).toHaveAttribute('data-state', 'checked');
        }
    }
    const selected = groups.reduce((sum, group) => sum + group.ids.length, 0);
    await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', String(selected));
    await page.getByTestId('toolbar-action-clone').click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
}

/**
 * Wait until the clone editor holds its rows: one for every source description on screen,
 * and the editor idle. On this page the types are cached before a row can be selected, so
 * the editor assigns all its rows in one go: one present means all present.
 */
async function bulkRowsLoaded(page: Page, descriptions: string[]): Promise<void> {
    const rows = page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
    for (const description of descriptions) await expect(rows.filter({hasText: description}).first()).toBeVisible({timeout: 5_000});
    await waitForSettled(page.getByTestId('tx-bulk-modal-root'));
}

/**
 * One entry per visible grid row: `''` for an independent row, the hidden partner's date
 * for a paired one (`tx-bulk-date[data-partner-date]`). Read once, after {@link bulkRowsLoaded}.
 */
async function bulkPartnerDates(page: Page): Promise<string[]> {
    return page
        .getByTestId('tx-bulk-body')
        .getByTestId('tx-bulk-date')
        .evaluateAll((cells) => cells.map((cell) => cell.getAttribute('data-partner-date') ?? ''));
}

/** Press Save all and return the commit's answer, read from the wire. */
async function commitBulk(page: Page): Promise<CommitBody> {
    const commitButton = page.getByTestId('tx-bulk-commit');
    await expect(commitButton).toBeEnabled({timeout: 8_000});
    // Armed before the click: a response is an edge, not a state.
    const answer = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === COMMIT_PATH, {timeout: 15_000});
    await commitButton.click();
    return (await (await answer).json()) as CommitBody;
}

/**
 * Remove what the test wrote, scoped to its own ids: the rows the page committed through
 * the describe's tracker, the API-made sources by id (the tracker does not see `page.request`),
 * then the broker — with `force` as the net for anything still on it. Failures are collected,
 * not thrown, so the caller decides what they mean.
 */
async function cleanupOwnedBroker(page: Page, tracker: TransactionWriteTracker, owned: OwnedBroker): Promise<string[]> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    // Leave the page first: an editor still open on these rows goes with it, unsaved.
    await attempt('leave the page', async () => {
        await page.goto('about:blank');
    });
    await attempt('rows the page committed', async () => {
        await tracker.cleanup();
    });
    if (owned.sourceIds.length > 0) {
        await attempt(`source rows ${owned.sourceIds.join(', ')}`, async () => {
            // One batch: both halves of a linked pair go together.
            const response = await page.request.post(COMMIT_PATH, {data: {creates: [], updates: [], deletes: owned.sourceIds}});
            const body = (await response.json().catch(() => null)) as CommitBody | null;
            if (!response.ok() || body?.committed !== true) throw new Error(`HTTP ${response.status()} ${JSON.stringify(body)}`);
        });
    }
    await attempt(`broker ${owned.brokerId}`, async () => {
        const response = await page.request.delete(`${API}/brokers?ids=${owned.brokerId}&force=true`);
        const body = (await response.json().catch(() => null)) as {results?: Array<{id: number; success: boolean}>} | null;
        if (!response.ok() || !body?.results?.find((result) => result.id === owned.brokerId)?.success) throw new Error(`HTTP ${response.status()} ${JSON.stringify(body)}`);
    });
    return failures;
}

/** Run `body` on an owned broker, then remove everything it holds. A red keeps its own error; on a green, a failed cleanup is a red of its own. */
async function withOwnedBroker(page: Page, tracker: TransactionWriteTracker, label: string, body: (owned: OwnedBroker) => Promise<void>): Promise<void> {
    const suffix = uniqueSuffix();
    const owned: OwnedBroker = {brokerId: await createOwnedBroker(page, `Tx clone ${label} ${suffix}`), suffix, sourceIds: []};
    let passed = false;
    try {
        await body(owned);
        passed = true;
    } finally {
        const failures = await cleanupOwnedBroker(page, tracker, owned);
        if (passed) expect(failures, 'every cleanup operation is scoped to what this test created').toEqual([]);
        else if (failures.length > 0) console.warn(`[${label}] cleanup after a failure left behind: ${failures.join('; ')}`);
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transaction Clone', () => {
    // Cloning commits real rows into a global table. The tests here that commit do it on a
    // broker they create (withOwnedBroker), and the paired commit runs below on an account of
    // its own (fixtures/owned-pair.ts); the seeded rows the others borrow are only opened in
    // the clone editor, never committed.
    //
    // The tracker deletes the rows *this page* committed, not every row that appeared
    // meanwhile: with concurrent workers those are not the same set, and deleting the
    // difference means deleting a neighbour's fixtures mid-test.
    let txWrites: TransactionWriteTracker;

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        txWrites = await trackTransactionWrites(page);
    });

    test.afterEach(async () => {
        await txWrites.cleanup();
    });

    test('clone standalone → 1 row new, source date preserved (T3)', async ({page}) => {
        // A standalone row on a broker this user can edit, read and checked through the API.
        // A source dated TODAY would make "preserved" indistinguishable from "reset to today"
        // (a neighbour's just-committed row is dated today by construction): the assertion
        // must discriminate, so the premise says so.
        const source = await seededRow(page, CLONE_STANDALONE);
        expect(source.date, `premise: "${CLONE_STANDALONE}" is not dated today — check populate_mock_data.py`).not.toBe(todayIso());
        await goToRows(page, [source.id]);

        await selectRow(page, `tx-${source.id}`);
        await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '1');
        const cloneBtn = page.getByTestId('toolbar-action-clone');
        await expect(cloneBtn).toBeVisible({timeout: 2_000});
        await cloneBtn.click();

        // BulkModal opens
        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});

        // The grid holds the clone of this one selection: 1 row, a count the test made.
        const bulkRow = bulkModal.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
        await expect(bulkRow).toHaveCount(1, {timeout: 3_000});

        // Status badge: "new" — the variant the cell publishes, not its literal.
        await expect(bulkRow.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'new');

        // T3: the clone keeps the original date (the correction workflow), not today.
        await expect(bulkRow.getByTestId('tx-bulk-date')).toHaveAttribute('data-date', source.date);

        // The single-clone auto-opens the FormModal — the same preserved date
        // must be what the edit form shows (createOpFromClone + fromTx agree).
        const formModal = page.getByTestId('tx-form-modal');
        await expect(formModal).toBeVisible({timeout: 5_000});
        await expect(page.getByTestId('tx-form-date-wrap').locator('input')).toHaveValue(source.date);
    });

    test('clone paired → 2 rows new (Da:/A:), source date preserved (T3)', async ({page}) => {
        // A pair on brokers this user can edit, read and checked through the API; not dated
        // today, for the reason the standalone test gives.
        const {giver, receiver} = await seededPair(page, CLONE_PAIR);
        expect(giver.date, `premise: ${CLONE_PAIR} is not dated today — check populate_mock_data.py`).not.toBe(todayIso());
        await goToRows(page, [giver.id, receiver.id]);

        // Select only the giver: the clone takes its partner along.
        await selectRow(page, `tx-${giver.id}`);
        await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '1');
        const cloneBtn = page.getByTestId('toolbar-action-clone');
        await expect(cloneBtn).toBeVisible({timeout: 2_000});
        await cloneBtn.click();

        // BulkModal opens with 2 rows (auto-included partner)
        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});

        // ...rendered as one grid row (dual Da:/A:), the partner held behind it: the row's date
        // cell names the partner's date. The grid holds this one selection, so 1 is a count
        // the test made.
        const bulkRow = bulkModal.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
        await expect(bulkRow).toHaveCount(1, {timeout: 3_000});

        // Status "new" — the variant the cell publishes, not its literal.
        await expect(bulkRow.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'new');

        // T3: the clone keeps the pair's original date, not today — on both halves.
        const dateCell = bulkRow.getByTestId('tx-bulk-date');
        await expect(dateCell).toHaveAttribute('data-date', giver.date);
        await expect(dateCell).toHaveAttribute('data-partner-date', receiver.date);
    });

    test('clone INTEREST sets quantity to 0', async ({page}) => {
        test.setTimeout(60_000);
        await withOwnedBroker(page, txWrites, 'INTEREST', async (owned) => {
            // An INTEREST of this test's own, on its own broker: the seeded one sits on a broker
            // e2e_test_user only views, where a clone could never be committed.
            const description = `INTEREST clone ${owned.suffix}`;
            const [sourceId] = await commitSources(page, owned, [{type: 'INTEREST', date: INTEREST_DATE, cash: {code: 'EUR', amount: '7.50'}, description}]);
            await goToRows(page, [sourceId]);

            await selectRow(page, `tx-${sourceId}`);
            await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '1');
            const cloneBtn = page.getByTestId('toolbar-action-clone');
            await expect(cloneBtn).toBeVisible({timeout: 2_000});
            await cloneBtn.click();

            // BulkModal opens → FormModal auto-opens for a single clone
            const bulkModal = page.getByTestId('tx-bulk-modal');
            const formModal = page.getByTestId('tx-form-modal');
            await expect(bulkModal).toBeVisible({timeout: 5_000});
            await expect(formModal).toBeVisible({timeout: 5_000});

            // INTEREST forbids a quantity, so no field shows one — the form has no quantity
            // input to read. The clone's quantity exists in what it sends: back to the grid.
            await formModal.getByTestId('tx-form-cancel').click();
            await expect(formModal).toBeHidden({timeout: 3_000});

            const commitButton = bulkModal.getByTestId('tx-bulk-commit');
            await expect(commitButton).toBeEnabled({timeout: 8_000});
            // Armed before the click: a response is an edge, not a state.
            const answer = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === COMMIT_PATH, {timeout: 15_000});
            await commitButton.click();
            const response = await answer;

            const sent = response.request().postDataJSON() as {creates?: Array<{type?: string; quantity?: string}>};
            expect(
                (sent.creates ?? []).map((create) => create.type),
                'the commit creates the one clone',
            ).toEqual(['INTEREST']);
            expect(Number(sent.creates?.[0]?.quantity), `the clone is sent with quantity 0 (sent: ${JSON.stringify(sent.creates?.[0]?.quantity)})`).toBe(0);
            const commit = (await response.json()) as CommitBody;
            expect(commit.committed, `the clone commit was refused: ${JSON.stringify(commit.issues ?? [])}`).toBe(true);
            // The editor closing is the app saying the commit came back.
            await expect(bulkModal).toBeHidden({timeout: 10_000});

            // ...and the server holds it so.
            const clones = (await readTransactions(page, {broker_id: owned.brokerId})).filter((row) => row.description === description && row.id !== sourceId);
            expect(
                clones.map((row) => [row.type, Number(row.quantity)]),
                'one INTEREST clone, saved with quantity 0',
            ).toEqual([['INTEREST', 0]]);
        });
    });

    test('clone inside the workspace (cloneRow) preserves the source date (T3)', async ({page}) => {
        // Own the source row: a mock-table scan could land on a today-dated
        // neighbour, where preserved and reset-to-today are indistinguishable.
        // A row this test created, dated 2021, makes the assertion exact. The
        // broker it sits on is the test's too: withOwnedBroker deletes, by id,
        // the row and then the broker, after a red as well.
        await withOwnedBroker(page, txWrites, 'T3-ws', async (owned) => {
            const sourceDate = '2021-07-19';
            const [sourceId] = await commitSources(page, owned, [{type: 'DEPOSIT', date: sourceDate, cash: {code: 'EUR', amount: '10'}, description: `T3-ws-${owned.suffix}`}]);

            // Id-filtered navigation: re-navigating to the URL the page is
            // already on is a client-side no-op that would leave the freshly
            // seeded row out of the table.
            await goToRows(page, [sourceId]);

            await selectRow(page, `tx-${sourceId}`);
            await page.getByTestId('toolbar-action-edit').click();
            const bulkModal = page.getByTestId('tx-bulk-modal');
            await expect(bulkModal).toBeVisible({timeout: 5_000});

            // A single-row edit always auto-opens the FormModal (TransactionBulkModal,
            // autoForm 'edit'); close it to reach the grid. Asserted, not probed: a
            // probe that answers before the form has opened lets the click below
            // land behind it.
            const formModal = page.getByTestId('tx-form-modal');
            await expect(formModal).toBeVisible({timeout: 5_000});
            await formModal.getByTestId('tx-form-cancel').click();
            await expect(formModal).not.toBeVisible({timeout: 3_000});

            // Clone the row INSIDE the workspace (cloneRow — the third T3 site). The grid holds
            // the one row this test opened it on, and that row's own id is what tells the
            // clone apart afterwards — no position, no class.
            const gridRows = bulkModal.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
            await expect(gridRows).toHaveCount(1, {timeout: 3_000});
            const sourceRowId = await gridRows.getAttribute('data-row-id');
            expect(sourceRowId, 'the grid row carries its id').toBeTruthy();
            await clickRowAction(gridRows, 'clone');

            // The clone is the row that was not there before — a new one — and it carries the source date.
            await expect(gridRows).toHaveCount(2, {timeout: 3_000});
            const appended = bulkModal.getByTestId('tx-bulk-body').locator(`tbody tr[data-row-id]:not([data-row-id="${sourceRowId}"])`);
            await expect(appended).toHaveCount(1);
            await expect(appended.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'new');
            await expect(appended.getByTestId('tx-bulk-date'), 'the in-workspace clone must carry the source date').toHaveAttribute('data-date', sourceDate);
        });
    });

    test('clone from view-only broker → no edit/delete actions on row', async ({page}) => {
        // A row on DEGIRO, where e2e_test_user is a VIEWER — the role read from the API, not
        // assumed. Any row there will do: the oldest, so the choice is the same on every run.
        const brokers = (await listBrokers(page)).filter((broker) => broker.name === VIEWER_BROKER);
        expect(
            brokers.map((broker) => broker.user_role),
            `premise: one broker named ${VIEWER_BROKER}, which this user only views — check populate_mock_data.py`,
        ).toEqual(['VIEWER']);
        const rows = await readTransactions(page, {broker_id: brokers[0].id});
        if (rows.length === 0) throw new Error(`${VIEWER_BROKER} holds no transaction visible to this user — check populate_mock_data.py`);
        const viewOnly = rows.reduce((oldest, row) => (row.id < oldest.id ? row : oldest));
        await goToRows(page, [viewOnly.id]);

        // Every row offers "view", so every row has its kebab: asserted, not probed.
        const row = txRow(page, viewOnly.id);
        await row.hover();
        const kebabBtn = row.getByTestId(`row-actions-tx-${viewOnly.id}`);
        await expect(kebabBtn).toBeVisible({timeout: 2_000});
        await kebabBtn.click();
        const menu = page.getByTestId('context-menu');
        await expect(menu).toBeVisible({timeout: 3_000});

        // The menu is drawn and offers what a viewer may do, so the absences below are facts
        // about this row, not about a menu still on its way. View-only rows should NOT show
        // delete/edit actions in the kebab menu.
        await expect(menu.getByTestId('context-menu-action-view')).toBeVisible();
        await expect(menu.getByTestId('context-menu-action-delete')).toHaveCount(0);
        await expect(menu.getByTestId('context-menu-action-edit')).toHaveCount(0);
    });

    test('C5a two single rows of one type clone into two independent rows, never one pair', async ({page}) => {
        test.setTimeout(60_000);
        await withOwnedBroker(page, txWrites, 'C5a', async (owned) => {
            // Two single DEPOSITs sharing one description. A link_uuid shared by mistake folds
            // them into one grid row; the wire drops it for a type that is not a pair
            // (buildCreatePayload), and the server check below guards that it stays dropped —
            // the backend itself would accept the link, since type, description and tags agree.
            const description = `C5a single ${owned.suffix}`;
            const sources = await commitSources(page, owned, [
                {type: 'DEPOSIT', date: C5_DATE, cash: {code: 'EUR', amount: '100'}, description},
                {type: 'DEPOSIT', date: C5_DATE, cash: {code: 'EUR', amount: '200'}, description},
            ]);
            expect(linksOf(await brokerRows(page, owned.brokerId)), 'premise: two single rows, neither linked to anything').toEqual({[sources[0]]: null, [sources[1]]: null});

            await cloneFromTable(page, owned.brokerId, [{description, ids: sources}]);

            // The editor holds the clones of this selection and nothing else, so its row count
            // is the subject: two sources, two independent rows. Soft, so that the commit below
            // still runs and the server's verdict on the same rows is reported too.
            await bulkRowsLoaded(page, [description]);
            expect.soft(await bulkPartnerDates(page), 'two single sources clone into two independent grid rows; a partner date means the editor merged them into one pair').toEqual(['', '']);

            const commit = await commitBulk(page);
            expect(commit.committed, `the clone commit was refused: ${JSON.stringify(commit.issues ?? [])}`).toBe(true);
            // The editor closing is the app saying the commit came back.
            await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: 10_000});

            const rows = (await brokerRows(page, owned.brokerId)).filter((row) => row.description === description);
            const clones = rows.filter((row) => !sources.includes(row.id));
            expect(
                clones.map((row) => row.type),
                'the commit created exactly the two clones',
            ).toEqual(['DEPOSIT', 'DEPOSIT']);
            expect(linksOf(rows), 'no single row is linked to another: sources and clones alike stay unlinked').toEqual(Object.fromEntries(rows.map((row) => [row.id, null])));
        });
    });

    test('C5b a pair cloned beside a single row stays a pair, and the single stays single', async ({page}) => {
        test.setTimeout(60_000);
        await withOwnedBroker(page, txWrites, 'C5b', async (owned) => {
            // A real pair — an FX_CONVERSION, which may sit on one broker, its two legs sharing
            // a link_uuid and a description — plus a single DEPOSIT that funds the EUR leg the
            // day before. Three rows selected: more than two, with a pair inside.
            const pairDescription = `C5b pair ${owned.suffix}`;
            const singleDescription = `C5b single ${owned.suffix}`;
            const linkUuid = `c5b-${owned.suffix}`;
            const sources = await commitSources(page, owned, [
                {type: 'FX_CONVERSION', date: C5_DATE, cash: {code: 'EUR', amount: '-100'}, description: pairDescription, link_uuid: linkUuid},
                {type: 'FX_CONVERSION', date: C5_DATE, cash: {code: 'USD', amount: '110'}, description: pairDescription, link_uuid: linkUuid},
                {type: 'DEPOSIT', date: C5_FUND_DATE, cash: {code: 'EUR', amount: '500'}, description: singleDescription},
            ]);
            const [legFrom, legTo, single] = sources;
            expect(linksOf(await brokerRows(page, owned.brokerId)), 'premise: the conversion is one linked pair, the deposit a single row').toEqual({[legFrom]: legTo, [legTo]: legFrom, [single]: null});

            await cloneFromTable(page, owned.brokerId, [
                {description: pairDescription, ids: [legFrom, legTo]},
                {description: singleDescription, ids: [single]},
            ]);

            // What the user sees, soft so the commit below still reports the server's verdict:
            // the cloned pair is one grid row (its partner hidden behind it), the single its own.
            await bulkRowsLoaded(page, [pairDescription, singleDescription]);
            expect.soft((await bulkPartnerDates(page)).sort(), 'the cloned pair arrives as one paired row and the cloned single as an independent one').toEqual(['', C5_DATE]);

            const commit = await commitBulk(page);
            expect(commit.committed, `the clone commit was refused: ${JSON.stringify(commit.issues ?? [])}`).toBe(true);
            await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: 10_000});

            const rows = await brokerRows(page, owned.brokerId);
            const pairClones = rows.filter((row) => row.description === pairDescription && !sources.includes(row.id));
            const singleClones = rows.filter((row) => row.description === singleDescription && !sources.includes(row.id));
            expect(
                pairClones.map((row) => row.type),
                'the pair was cloned once: two FX_CONVERSION legs',
            ).toEqual(['FX_CONVERSION', 'FX_CONVERSION']);
            expect(
                singleClones.map((row) => row.type),
                'the single was cloned once',
            ).toEqual(['DEPOSIT']);
            const [cloneA, cloneB] = pairClones;
            expect(linksOf(rows), 'the two cloned legs are linked to each other, the cloned single to nothing, and the sources keep their own link').toEqual({
                [legFrom]: legTo,
                [legTo]: legFrom,
                [single]: null,
                [cloneA.id]: cloneB.id,
                [cloneB.id]: cloneA.id,
                [singleClones[0].id]: null,
            });
        });
    });
});

// ---------------------------------------------------------------------------
// The paired commit — on a pair of its own
// ---------------------------------------------------------------------------

// Same title as the block above, so the test keeps its full name. A block of its own because
// the TEST_USER login above must not run for it: it signs in as the disposable account that
// owns its pair (fixtures/owned-pair.ts). Its clones are committed onto that account's
// brokers, where no other spec can see them — not beside a seeded pair other specs look up
// by its description — and deleting the account takes them with everything else.
test.describe('Transaction Clone', () => {
    let owned = emptyOwnedAccount();

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
    });

    // afterEach, not `finally`: it runs after a timeout too, and an error of its own is
    // reported beside the test's instead of replacing it.
    test.afterEach(async ({page, request}) => {
        await cleanupOwnedAccount(page, request, owned);
    });

    test('clone paired commit → pair created in DB with link', async ({page, request}, testInfo) => {
        // The account goes through the real welcome flow before the clone itself.
        test.setTimeout(60_000);
        const pair = await openAccountWithPair(page, request, owned, `clone_${testInfo.project.name}`);
        // T3: the pair's date is known up front — the wire assertion below checks the clone
        // payload against it, and it is not today.
        expect(pair.date, 'premise: the owned pair is not dated today').not.toBe(todayIso());
        await goToRows(page, [pair.fromId, pair.toId]);

        // Select only the giver: the clone takes its partner along.
        await selectRow(page, `tx-${pair.fromId}`);
        await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '1');
        const cloneBtn = page.getByTestId('toolbar-action-clone');
        await expect(cloneBtn).toBeVisible({timeout: 2_000});
        await cloneBtn.click();

        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});

        // Intercept the commit — on the response, armed before the click: the test ends once
        // the commit has landed, so the cleanup never races it.
        const commitPromise = page.waitForResponse((res) => res.request().method() === 'POST' && new URL(res.url()).pathname === COMMIT_PATH, {timeout: 15_000});

        // Click commit
        const commitBtn = bulkModal.getByTestId('tx-bulk-commit');
        await expect(commitBtn).toBeEnabled({timeout: 8_000});
        await commitBtn.click();

        const response = await commitPromise;
        const payload = response.request().postDataJSON();

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
            expect(c.date, 'clone must carry the source date on the wire').toBe(pair.date);
        }

        const body = (await response.json()) as CommitBody;
        expect(body.committed, `the clone commit was refused: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
        // The editor closing is the app saying the commit came back.
        await expect(bulkModal).toBeHidden({timeout: 15_000});

        // In the DB: two new TRANSFER rows beside the source pair, linked to each other.
        const clones = (await readTransactions(page)).filter((tx) => tx.description === pair.description && tx.id !== pair.fromId && tx.id !== pair.toId);
        expect(
            clones.map((tx) => tx.type),
            'the commit created the two halves of the cloned pair',
        ).toEqual(['TRANSFER', 'TRANSFER']);
        const [cloneA, cloneB] = clones;
        expect([cloneA.related_transaction_id, cloneB.related_transaction_id], 'the two clones are linked to each other').toEqual([cloneB.id, cloneA.id]);
    });
});
