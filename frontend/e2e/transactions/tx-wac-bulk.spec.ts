/**
 * tx-wac-bulk.spec.ts — BulkModal WAC Cell Rendering E2E Tests
 *
 * Covers Bug 9, 10, 11 from plan-ReactiveWacBulkModal (Piano v7):
 * - WB1: TRANSFER auto shows calculated WAC value in cell (Bug 9)
 * - WB2: Manual override propagates from FormModal to BulkModal cell (Bug 10)
 * - WB3: Toggle manual→auto restores calculated value (Bug 10 reverse)
 * - WB4: DB rows with saved cost_basis show manual value (Bug 11)
 * - WB5: Clone paired from DB — WAC auto cell appears (inline validate)
 *
 * Prerequisites: backend test mode, mock data populated.
 * Mock data contract: e2e_test_user has OWNER/EDITOR on Interactive Brokers + Directa SIM.
 * Apple (AAPL) is a known asset with price history.
 */
import {expect, test, type Page, type Request} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {appears} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';
import {randomUUID} from 'crypto';

test.setTimeout(60_000);

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BROKER_FROM = 'Interactive Brokers';
const BROKER_TO = 'Directa SIM';
const ASSET_NAME = 'Apple';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions?page_size=200');
    // The previous version raced two waits and swallowed the failure with
    // `.catch(() => {})`, then slept 500 ms. Under load it returned with an
    // empty table, and every "scan the rows" loop below found nothing and
    // reported a missing fixture instead of a slow one.
    await expect(page.locator('[data-testid="transactions-page"][data-busy="false"]')).toBeVisible({timeout: 20_000});
    await expect(page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').first()).toBeVisible({timeout: 15_000});
}

/** Open the table narrowed to the given IDs — the rows this test owns. */
async function goToTransactionsByIds(page: Page, ids: number[]) {
    const min = Math.min(...ids);
    const max = Math.max(...ids);
    await navigateTo(page, `/transactions?page_size=200&id_min=${min}&id_max=${max}`);
    await expect(page.locator('[data-testid="transactions-page"][data-busy="false"]')).toBeVisible({timeout: 20_000});
    await expect(page.locator(`tr[data-row-id="tx-${ids[0]}"]`)).toBeVisible({timeout: 15_000});
}

async function openCreateFlow(page: Page) {
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

/**
 * A SearchSelect has no "I committed" event, but its option list is torn down
 * when a choice lands. Waiting for that instead of sleeping also covers the
 * field cascade the choice triggers, because the re-render happens first.
 */
async function optionListClosed(page: Page) {
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 5_000});
}

async function selectType(page: Page, typeCode: string) {
    const typeButton = page.getByTestId('tx-form-type');
    await typeButton.click();
    await page.getByTestId(`search-select-option-${typeCode}`).click();
    await optionListClosed(page);
}

async function pickFirstBroker(page: Page) {
    const brokerWrap = page.getByTestId('tx-form-broker-wrap');
    await brokerWrap.locator('button, [role="combobox"]').first().click();
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: BROKER_FROM});
    await expect(option.first()).toBeVisible({timeout: 3_000});
    await option.first().click();
    await optionListClosed(page);
}

async function pickBrokerInPanel(page: Page, panelTestid: string, brokerName: string) {
    const panel = page.getByTestId(panelTestid);
    const trigger = panel.locator('[role="combobox"]').first();
    await expect(trigger).toBeVisible({timeout: 3_000});
    await trigger.click();
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: brokerName});
    await expect(option.first()).toBeVisible({timeout: 3_000});
    await option.first().click();
    await optionListClosed(page);
}

async function pickAssetByName(page: Page, name: string) {
    const assetWrap = page.getByTestId('tx-form-asset-wrap');
    await assetWrap.locator('button, [role="combobox"]').first().click();
    const searchInput = page.locator('[data-testid="tx-form-asset-wrap"] input[type="text"], [data-testid="tx-form-asset-wrap"] input[role="combobox"]').first();
    if (await searchInput.isVisible({timeout: 1_000}).catch(() => false)) {
        await searchInput.fill(name);
        // The list is debounced; the named entry arriving *is* the settle.
        await expect(page.locator('[data-testid^="search-select-option-"]', {hasText: name}).first()).toBeVisible({timeout: 5_000});
    }
    const option = page.locator('[data-testid^="search-select-option-"]').first();
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionListClosed(page);
}

async function fillQuantity(page: Page, qty: string) {
    const qtyInput = page.getByTestId('tx-form-quantity');
    await expect(qtyInput).toBeVisible({timeout: 2_000});
    await qtyInput.fill(qty);
    await qtyInput.blur();
    await expect(qtyInput).not.toHaveValue('');
}

async function fillCash(page: Page, amount: string) {
    const cashWrap = page.getByTestId('tx-form-cash-wrap');
    await expect(cashWrap).toBeVisible({timeout: 2_000});
    const cashInput = cashWrap.locator('input[data-testid$="-amount"]').first();
    await expect(cashInput).toBeVisible({timeout: 1_000});
    await cashInput.fill(amount);
    await cashInput.blur();
    await expect(cashInput).not.toHaveValue('');
}

async function applyFormModal(page: Page) {
    const saveBtn = page.getByTestId('tx-form-save');
    await expect(saveBtn).toBeVisible({timeout: 3_000});
    await expect(saveBtn).toBeEnabled({timeout: 5_000});
    await saveBtn.click();
    await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 10_000});
}

/** Wait for WAC cell to resolve (not showing "…" placeholder). */
async function waitForWacResolved(page: Page) {
    const root = page.getByTestId('tx-bulk-modal-root');
    // The value arrives with the validate response. Waiting on `data-busy`
    // alone is not enough: before the debounce arms, nothing is queued and
    // nothing is in flight, so the modal looks settled while the cell still
    // holds its placeholder. `data-validate-runs` is monotonic, so "at least
    // one run has completed" is a *state* — reading it late costs nothing,
    // which is exactly what a 4-worker run needs.
    await expect(root).not.toHaveAttribute('data-validate-runs', '0', {timeout: 25_000});
    await waitForSettled(root, 25_000);
    // Presenza e stato vanno chiesti separatamente. In modalità auto la cella
    // esiste sempre e pubblica tre stati: 'pending' (in calcolo), 'ready'
    // (valore proposto), 'empty' (calcolato, e non c'è nulla da proporre).
    // Il selettore composto [data-state="ready"] li collassava tutti in
    // «element(s) not found» — un errore che non distingue «ancora lento» da
    // «questa riga un WAC non ce l'ha», cioè le due diagnosi opposte.
    const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"]').first();
    await expect(autoCell).toBeVisible({timeout: 20_000});
    await expect(autoCell).toHaveAttribute('data-state', 'ready', {timeout: 20_000});
}

/**
 * Stamp the draft in the FormModal with a description only this test knows.
 *
 * The BulkModal orders rows of one date by a tie-break the test does not control,
 * so "the TRANSFER is the last row" was a coin toss (C4). The marker is identity:
 * user-entered content, never translated, shared by both legs of a TRANSFER, and
 * carried through every re-edit. It lives in the collapsible optional `<details>`:
 * read its real `open` state rather than clicking blind, which would close it.
 */
async function fillDescription(page: Page, text: string) {
    const details = page.locator('details:has([data-testid="tx-form-optional-toggle"])');
    await expect(details).toBeVisible({timeout: 3_000});
    if (!(await details.evaluate((el) => (el as HTMLDetailsElement).open))) await page.getByTestId('tx-form-optional-toggle').click();
    await expect(details).toHaveAttribute('open', '');
    const description = page.getByTestId('tx-form-description');
    await description.fill(text);
    await expect(description).toHaveValue(text);
}

/** Double-click the one BulkModal row that carries `marker` to open it in the FormModal. */
async function dblClickBulkRow(page: Page, marker: string) {
    const row = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]').filter({hasText: marker});
    await expect(row).toHaveCount(1, {timeout: 5_000});
    await row.dblclick();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

/**
 * Save the editor and return the ids the backend assigned. With `owned`, the ids are also
 * recorded there the moment the response reports them, before anything else is checked:
 * a red after the commit still deletes what it saved.
 */
async function commitBulkModal(page: Page, owned?: number[]): Promise<number[]> {
    const commitBtn = page.getByTestId('tx-bulk-commit');
    await expect(commitBtn).toBeEnabled({timeout: 8_000});

    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commitBtn.click();
    const resp = await responsePromise;
    const body = (await resp.json()) as {
        committed: boolean;
        issues?: Array<{error: string}>;
        results?: Array<{operation: string; ids?: number[]; status?: string}>;
    };
    // The ids the backend assigned — the only way for the test to know which
    // rows it owns rather than scanning the table and hoping. A rolled-back
    // commit created nothing, so it reports nothing to own.
    const ids = body.committed === true ? (body.results ?? []).filter((r) => r.operation === 'create' && r.status === 'success').flatMap((r) => r.ids ?? []) : [];
    owned?.push(...ids);
    expect(body.committed, `commit was rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);

    // Wait for BulkModal to close
    await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});
    return ids;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('BulkModal WAC Cell Rendering', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    test('WB1 — TRANSFER auto shows WAC value (Bug 9)', async ({page}) => {
        // Step 1: Create a BUY 10@1000 on broker_A
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '10');
        await fillCash(page, '1000');
        await applyFormModal(page);

        // BulkModal should be visible
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Step 2: Create a TRANSFER from broker_A → broker_B, same asset, qty=5
        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'TRANSFER');

        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await applyFormModal(page);

        // Step 3: Wait for WAC to resolve
        await waitForWacResolved(page);

        // Step 4: Assert cell shows 💡 + a number
        const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"][data-state="ready"]').first();
        const cellText = await autoCell.textContent();
        expect(cellText).toMatch(/💡\s*[\d.,]+/);
    });

    test('WB2 — Manual override propagates to cell (Bug 10)', async ({page}) => {
        const transferMarker = `WB2 transfer ${uniqueSuffix()}`;
        // Setup: same as WB1
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '10');
        await fillCash(page, '1000');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'TRANSFER');
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await fillDescription(page, transferMarker);
        await applyFormModal(page);
        await waitForWacResolved(page);

        // Open the TRANSFER row in FormModal — by its marker, not as "the last row":
        // BUY and TRANSFER share a date and their order is not ours to assume.
        await dblClickBulkRow(page, transferMarker);

        // Toggle to manual
        const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
        if (await manualToggle.isVisible({timeout: 2_000}).catch(() => false)) {
            await manualToggle.click();
            await expect(manualToggle).toHaveAttribute('aria-pressed', 'true');
        }

        // Type 150 in cost basis input
        const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(amountInput).toBeVisible({timeout: 2_000});
        await amountInput.fill('150');
        await amountInput.blur();
        await expect(amountInput).not.toHaveValue('');

        await applyFormModal(page);
        await waitForSettled(page.getByTestId('tx-bulk-modal-root'));

        // Assert: manual cell shows value containing "150"
        const manualCell = page.locator('[data-testid="tx-bulk-cost-basis-manual"]').first();
        await expect(manualCell).toBeVisible({timeout: 5_000});
        const text = await manualCell.textContent();
        expect(text).toContain('150');
    });

    test('WB3 — Toggle manual→auto restores calculated value (Bug 10 reverse)', async ({page}) => {
        const transferMarker = `WB3 transfer ${uniqueSuffix()}`;
        // Setup: BUY + TRANSFER with manual override
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '10');
        await fillCash(page, '1000');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'TRANSFER');
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await fillDescription(page, transferMarker);
        await applyFormModal(page);
        await waitForWacResolved(page);

        // Set manual override (the TRANSFER row, found by its marker)
        await dblClickBulkRow(page, transferMarker);

        const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
        if (await manualToggle.isVisible({timeout: 2_000}).catch(() => false)) {
            await manualToggle.click();
            await expect(manualToggle).toHaveAttribute('aria-pressed', 'true');
        }
        const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(amountInput).toBeVisible({timeout: 2_000});
        await amountInput.fill('150');
        await applyFormModal(page);

        // Now reopen the same TRANSFER row and switch back to auto
        await dblClickBulkRow(page, transferMarker);

        const autoToggle = page.getByTestId('tx-form-cost-basis-toggle-auto');
        if (await autoToggle.isVisible({timeout: 2_000}).catch(() => false)) {
            await autoToggle.click();
            await expect(autoToggle).toHaveAttribute('aria-pressed', 'true');
        }
        await applyFormModal(page);

        // Wait for auto to resolve
        await waitForWacResolved(page);

        // Assert: back to auto cell with calculated value
        const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"][data-state="ready"]').first();
        const cellText = await autoCell.textContent();
        expect(cellText).toMatch(/💡\s*[\d.,]+/);
    });

    test('WB4 — DB rows with saved cost_basis show manual (Bug 11)', async ({page}) => {
        // Whoever commits, cleans up. The BUY and the TRANSFER land on shared brokers, where
        // every later test would read them: their ids are recorded the moment the commit
        // reports them, and deleted after the test whatever its outcome.
        await withOwned(page, 'WB4', async (owned) => {
            // Create BUY + TRANSFER with auto WAC, then commit
            await openCreateFlow(page);
            await selectType(page, 'BUY');
            await pickFirstBroker(page);
            await pickAssetByName(page, ASSET_NAME);
            await fillQuantity(page, '10');
            await fillCash(page, '1000');
            await applyFormModal(page);
            await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

            await page.getByTestId('tx-bulk-add-row').click();
            await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
            await selectType(page, 'TRANSFER');
            await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
            await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
            await pickAssetByName(page, ASSET_NAME);
            await fillQuantity(page, '5');
            await applyFormModal(page);
            await waitForWacResolved(page);

            // Commit
            const createdIds = await commitBulkModal(page, owned.transactionIds);
            expect(createdIds.length, 'the commit must report the rows it created').toBeGreaterThan(0);

            // Open the table narrowed to the rows we just created. Scanning the
            // whole table for "a paired row with this asset and broker" could land
            // on a neighbour's row, which has no saved cost_basis and would fail
            // the assertion below for the wrong reason.
            await goToTransactionsByIds(page, createdIds);

            // Among our own rows, find the giver of the pair (the row followed by a receiver)
            const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
            let giverRowId: string | null = null;
            const count = await allRows.count();
            for (let i = 0; i < count - 1; i++) {
                const nextCls = (await allRows.nth(i + 1).getAttribute('class')) ?? '';
                if (nextCls.includes('tx-row-receiver')) {
                    giverRowId = await allRows.nth(i).getAttribute('data-row-id');
                    break;
                }
            }
            expect(giverRowId, 'the committed TRANSFER must render as a giver + receiver pair').toBeTruthy();

            // Select and open in BulkModal (Edit)
            const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="${giverRowId}"]`);
            await row.locator('.checkbox-btn').first().click();

            const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
            await expect(editBtn).toBeEnabled({timeout: 5_000});
            await editBtn.click();
            await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

            // Assert: cost_basis cell shows manual value (DB-saved = manual)
            const manualCell = page.locator('[data-testid="tx-bulk-cost-basis-manual"]').first();
            await expect(manualCell).toBeVisible({timeout: 10_000});
        });
    });

    test('WB5 — Clone paired from DB, WAC auto cell appears (inline validate)', async ({page}) => {
        // The saved pair is the test's own, and so is its arithmetic (createOwnedTransferPair).
        // It used to be "the first paired row sent from IB or Directa" — on the seed, the
        // view-only pair whose receiver the test user cannot write, which by contract gets
        // no cost proposed; it went green only on a pair another test had left behind.
        await withOwned(page, 'WB5', async (owned) => {
            const pair = await createOwnedTransferPair(page, owned);
            await goToTransactionsByIds(page, [pair.giverId, pair.receiverId]);

            // Premise, by id: the sending half is shown directly above its receiving half.
            const table = page.getByTestId('tx-table');
            await expect(table.locator(`tbody tr[data-row-id="tx-${pair.giverId}"] + tr[data-row-id="tx-${pair.receiverId}"]`)).toBeVisible({timeout: 10_000});

            // Select the sending half and clone: the editor brings its partner along.
            const checkbox = table.getByTestId(`dt-row-checkbox-tx-${pair.giverId}`);
            await checkbox.click();
            await expect(checkbox).toHaveAttribute('data-state', 'checked');
            const cloneBtn = page.getByTestId('toolbar-action-clone');
            await expect(cloneBtn).toBeVisible({timeout: 5_000});
            await cloneBtn.click();
            await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

            // Premise: the clone is one paired row on the grid, with no form on top of it.
            const gridRow = page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]').filter({hasText: pair.description});
            await expect(gridRow).toHaveCount(1, {timeout: 5_000});
            await expect(page.getByTestId('tx-form-modal')).toBeHidden();

            // Il WAC arriva dalla risposta di validate (niente /wac-preview separato).
            //
            // Qui stava il difetto: WB5 era l'unico test del file che, dopo il clone,
            // scommetteva 8 s sull'**esito** senza prima aspettare la barriera che il
            // prodotto pubblica — `data-validate-runs` che lascia lo zero, poi
            // `data-busy` che torna false. Con il debounce di 1 s davanti e un backend
            // strumentato due volte (coverage Python + JS) sotto la run completa, quel
            // budget cadeva dentro la coda della distribuzione e il test si arrendeva
            // mentre la cella era ancora 'pending'. Aumentare il numero avrebbe
            // spostato la scommessa, non tolta: `waitForWacResolved` aspetta lo stato,
            // che è ciò che gli altri nove test di questo file fanno da sempre.
            await waitForWacResolved(page);

            // The proposal is the sending broker's average, 150.00 EUR per unit — not the 175
            // saved on the source row. The cell publishes no raw amount, so read its digits,
            // never its words.
            const autoCell = gridRow.getByTestId('tx-bulk-cost-basis-auto');
            await expect(autoCell).toHaveAttribute('data-state', 'ready');
            await expect.poll(async () => ((await autoCell.textContent()) ?? '').replace(/\D/g, ''), {message: 'the clone proposes the average of the owned lots, 150.00 EUR per unit', timeout: 5_000}).toBe('15000');
        });
    });

    test('WB6 — WAC value stable after debounce (no feedback loop)', async ({page}) => {
        // Create BUY 10@1000
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '10');
        await fillCash(page, '1000');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Create TRANSFER 5
        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'TRANSFER');
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await applyFormModal(page);

        // Wait for WAC to resolve
        await waitForWacResolved(page);

        // Capture value
        const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"][data-state="ready"]').first();
        const value1 = await autoCell.textContent();
        expect(value1).toMatch(/💡\s*[\d.,]+/);

        // Deliberate: this proves the value does *not* drift. A retrying assertion
        // would confirm the first reading instantly and never open the window in
        // which a feedback loop could show itself.
        await page.waitForTimeout(2_500);

        // Capture again — must be identical (stable, no feedback loop)
        const value2 = await autoCell.textContent();
        expect(value2).toBe(value1); // Stable — no feedback loop
    });

    test('WB7 — Multiple pending BUYs affect WAC correctly', async ({page}) => {
        // Create BUY 10@100
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '10');
        await fillCash(page, '100');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Create BUY 5@200
        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await fillCash(page, '200');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Create TRANSFER 3
        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'TRANSFER');
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '3');
        await applyFormModal(page);

        // Wait for WAC to resolve
        await waitForWacResolved(page);

        // Assert WAC contains a number (the exact value depends on existing DB data
        // but with pending BUYs 10@100 + 5@200 the contribution should be around 133)
        const autoCell = page.locator('[data-testid="tx-bulk-cost-basis-auto"][data-state="ready"]').first();
        const cellText = await autoCell.textContent();
        expect(cellText).toMatch(/💡\s*[\d.,]+/);
    });

    test('WB8 — Mode persistence: manual stays manual on re-edit', async ({page}) => {
        const transferMarker = `WB8 transfer ${uniqueSuffix()}`;
        // Create BUY + TRANSFER pair
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '10');
        await fillCash(page, '1000');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'TRANSFER');
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await fillDescription(page, transferMarker);
        await applyFormModal(page);
        await waitForWacResolved(page);

        // Set manual 150 on the TRANSFER row (found by its marker)
        await dblClickBulkRow(page, transferMarker);

        const manualBtn = page.getByTestId('tx-form-cost-basis-toggle-manual');
        await manualBtn.click();
        await expect(manualBtn).toHaveAttribute('aria-pressed', 'true');
        const amountInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await amountInput.fill('150');
        await applyFormModal(page);
        await waitForSettled(page.getByTestId('tx-bulk-modal-root'));

        // Re-edit the same TRANSFER row — should still show manual
        await dblClickBulkRow(page, transferMarker);

        // Assert: manual toggle is active (has font-medium)
        const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
        await expect(manualToggle).toBeVisible({timeout: 3_000});
        await expect(manualToggle).toHaveClass(/font-medium/);

        // Assert: input still has 150
        const input = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(input).toHaveValue('150');
    });

    test('WB9 — Mode persistence: auto stays auto on re-edit', async ({page}) => {
        const transferMarker = `WB9 transfer ${uniqueSuffix()}`;
        // Create BUY + TRANSFER pair (auto mode — default)
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '10');
        await fillCash(page, '1000');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'TRANSFER');
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await fillDescription(page, transferMarker);
        await applyFormModal(page);
        await waitForWacResolved(page);

        // Re-edit the TRANSFER row (found by its marker) without changing mode — should still be auto
        await dblClickBulkRow(page, transferMarker);

        // Assert: auto toggle is active
        const autoToggle = page.getByTestId('tx-form-cost-basis-toggle-auto');
        await expect(autoToggle).toBeVisible({timeout: 3_000});
        await expect(autoToggle).toHaveClass(/font-medium/);

        // Assert: manual toggle is NOT active
        const manualToggle = page.getByTestId('tx-form-cost-basis-toggle-manual');
        await expect(manualToggle).not.toHaveClass(/font-medium/);
    });

    test('WB10 — Pending indicator ● in qualifying table', async ({page}) => {
        const transferMarker = `WB10 transfer ${uniqueSuffix()}`;
        // Create BUY (this will be a pending tx visible in qualifying table)
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickFirstBroker(page);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '10');
        await fillCash(page, '1000');
        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Create TRANSFER pair
        await page.getByTestId('tx-bulk-add-row').click();
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
        await selectType(page, 'TRANSFER');
        await pickBrokerInPanel(page, 'tx-form-dual-from', BROKER_FROM);
        await pickBrokerInPanel(page, 'tx-form-dual-to', BROKER_TO);
        await pickAssetByName(page, ASSET_NAME);
        await fillQuantity(page, '5');
        await fillDescription(page, transferMarker);
        await applyFormModal(page);
        await waitForWacResolved(page);

        // Open the TRANSFER row (found by its marker)
        await dblClickBulkRow(page, transferMarker);

        // Expand qualifying table
        const showBtn = page.getByTestId('tx-form-cost-basis-show-qualifying');
        await expect(showBtn).toBeVisible({timeout: 5_000});
        await showBtn.click();

        // Assert: qualifying table has at least one row with ● (pending indicator)
        const qualTable = page.getByTestId('tx-form-cost-basis-qualifying-table');
        await expect(qualTable).toBeVisible({timeout: 3_000});
        const pendingDots = qualTable.getByTestId('tx-form-cost-basis-pending-dot');
        await expect(pendingDots.first()).toBeVisible({timeout: 5_000});
        expect(await pendingDots.count()).toBeGreaterThan(0);
        const dotText = await pendingDots.first().textContent();
        expect(dotText?.trim()).toBe('●');
    });
});

// ---------------------------------------------------------------------------
// WB11 — a saved manual cost basis is not a change
// ---------------------------------------------------------------------------
//
// A saved row with a cost basis opens in the editor in MANUAL mode, its cost basis
// rebuilt as a fresh object. Left untouched it is not a change: Save stays disabled
// and no validate or commit carries an update for it. Comparing that cost basis by
// reference instead of by value marks every such row edited — Save enabled on an
// editor nobody touched, and each row sent back as a no-op update.
//
// The rows are owned: a broker and an asset created here, two ADJUSTMENTs with a
// positive quantity (the side that carries a cost basis) committed through the API,
// all deleted at the end whatever the outcome. Two rows, so the editor opens on its
// grid without a form on top: every validation recorded is the editor's own.

const API = '/api/v1';

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
/** Every id the test created, recorded the moment it exists so cleanup never depends on an assertion. */
type Owned = {brokerIds: number[]; assetIds: number[]; transactionIds: number[]};
type CostBasis = {code: string; amount: string};
/** The saved rows under test: ids to select them in the table, descriptions only this test knows to find them in the grid. */
type OwnedManualRows = {brokerId: number; transactionIds: number[]; descriptions: string[]};
/** A `/transactions/validate` or `/transactions/commit` request, reduced to the updates it carried. */
type SentBatch = {path: string; updates: Array<Record<string, unknown>>};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/**
 * An owned broker and asset holding two saved ADJUSTMENTs, each with a cost basis.
 * The ledger is read back, so the premise — a saved cost basis on every row — is
 * checked rather than assumed.
 */
async function createOwnedManualRows(page: Page, owned: Owned): Promise<OwnedManualRows> {
    const suffix = uniqueSuffix();
    const brokerName = `WB11 broker ${suffix}`;
    const brokers = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: [{name: brokerName, opened_at: '2020-01-01'}]}), 'create owned broker');
    const broker = brokers.results.find((item) => item.name === brokerName);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(brokers)}`);
    const brokerId = broker.broker_id;
    owned.brokerIds.push(brokerId);

    const assetName = `WB11 asset ${suffix}`;
    const assets = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [{display_name: assetName, currency: 'EUR', asset_type: 'STOCK'}]}), 'create owned asset');
    const asset = assets.results.find((item) => item.display_name === assetName);
    if (!asset?.success || typeof asset.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(assets)}`);
    const assetId = asset.asset_id;
    owned.assetIds.push(assetId);

    const rows: Array<{description: string; date: string; quantity: string; cost_basis_override: CostBasis}> = [
        {description: `WB11 a ${suffix}`, date: '2024-01-02', quantity: '5', cost_basis_override: {code: 'EUR', amount: '10'}},
        {description: `WB11 b ${suffix}`, date: '2024-01-03', quantity: '3', cost_basis_override: {code: 'EUR', amount: '12.5'}},
    ];
    const creates = rows.map((row) => ({broker_id: brokerId, asset_id: assetId, type: 'ADJUSTMENT', ...row}));
    const committed = await jsonFrom<{committed: boolean; issues?: unknown; results: Array<{operation: string; ids?: number[]}>}>(await page.request.post(`${API}/transactions/commit`, {data: {creates}}), 'commit owned ADJUSTMENTs');
    const ids = committed.results.filter((result) => result.operation === 'create').flatMap((result) => result.ids ?? []);
    owned.transactionIds.push(...ids);
    expect(committed.committed, `owned ADJUSTMENTs rolled back: ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
    expect(ids, 'the commit created exactly the owned ADJUSTMENTs').toHaveLength(rows.length);

    const saved = await jsonFrom<Array<{id: number; description?: string | null; cost_basis_override?: CostBasis | null}>>(await page.request.get(`${API}/transactions?${ids.map((id) => `ids=${id}`).join('&')}`), 'read owned ADJUSTMENTs');
    for (const row of rows) {
        const tx = saved.find((item) => item.description === row.description);
        expect(tx?.cost_basis_override?.code, `premise: "${row.description}" is saved with its cost basis`).toBe(row.cost_basis_override.code);
        expect(Number(tx?.cost_basis_override?.amount), `premise: "${row.description}" is saved with its cost basis`).toBe(Number(row.cost_basis_override.amount));
    }
    return {brokerId, transactionIds: ids, descriptions: rows.map((row) => row.description)};
}

/** Delete exactly the ids this test created, and say what could not be deleted. */
async function cleanupOwned(page: Page, owned: Owned): Promise<string[]> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    // Leave the page first: an editor still open on the rows goes with it, unsaved.
    await attempt('leave the page', async () => {
        await page.goto('about:blank');
    });
    if (owned.transactionIds.length > 0) {
        await attempt(`transactions ${owned.transactionIds.join(', ')}`, async () => {
            const result = await jsonFrom<{committed: boolean}>(await page.request.post(`${API}/transactions/commit`, {data: {creates: [], updates: [], deletes: owned.transactionIds}}), 'delete owned transactions');
            expect(result.committed).toBe(true);
        });
    }
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete owned broker');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete owned asset');
            expect(result.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
        });
    }
    return failures;
}

/** Run `body` on owned saved rows with a manual cost basis, then delete them, the asset and the broker whatever the outcome. */
async function withOwnedManualRows(page: Page, body: (rows: OwnedManualRows) => Promise<void>): Promise<void> {
    const owned: Owned = {brokerIds: [], assetIds: [], transactionIds: []};
    let passed = false;
    try {
        await body(await createOwnedManualRows(page, owned));
        passed = true;
    } finally {
        const failures = await cleanupOwned(page, owned);
        // A red keeps its own error; on a green, a cleanup that failed is a red of its own.
        if (passed) expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
        else if (failures.length > 0) console.warn(`[WB11] cleanup after a failure left behind: ${failures.join('; ')}`);
    }
}

/**
 * Open the owned rows in the bulk editor the way a user does: select them in the
 * table narrowed to the owned broker, then the toolbar's Edit. More than one
 * selected row opens the editor on its grid, with no form on top.
 */
async function openRowsInBulkEditor(page: Page, rows: OwnedManualRows) {
    await navigateTo(page, `/transactions?broker_id=${rows.brokerId}`);
    const transactionsPage = page.getByTestId('transactions-page');
    await expect(transactionsPage).toBeVisible({timeout: 10_000});
    await waitForSettled(transactionsPage, 20_000);
    for (const id of rows.transactionIds) {
        const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
        await expect(checkbox).toBeVisible({timeout: 10_000});
        await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
    const edit = page.getByTestId('toolbar-action-edit');
    await expect(edit).toBeEnabled({timeout: 5_000});
    await edit.click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
}

test.describe('BulkModal saved manual cost basis', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('WB11 — saved rows with a manual cost basis open unchanged: Save stays disabled and no update is sent', async ({page}) => {
        await withOwnedManualRows(page, async (saved) => {
            // Every batch the page sends, armed before the editor opens: an untouched row belongs in none of them.
            const sent: SentBatch[] = [];
            const record = (request: Request) => {
                if (request.method() !== 'POST') return;
                const path = new URL(request.url()).pathname;
                if (path !== `${API}/transactions/validate` && path !== `${API}/transactions/commit`) return;
                sent.push({path, updates: ((request.postDataJSON() ?? {}) as {updates?: Array<Record<string, unknown>>}).updates ?? []});
            };
            const root = page.getByTestId('tx-bulk-modal-root');
            const gridRows = page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
            page.on('request', record);
            try {
                await openRowsInBulkEditor(page, saved);
                // Premise: the grid holds exactly the saved rows, each in MANUAL mode with its cost basis — the state under test.
                for (const description of saved.descriptions) {
                    const row = gridRows.filter({hasText: description});
                    await expect(row).toHaveCount(1, {timeout: 5_000});
                    await expect(row.getByTestId('tx-bulk-cost-basis-manual')).toBeVisible();
                }
                await expect(gridRows).toHaveCount(saved.descriptions.length);
                // Premise: the toolbar that would offer Reset all is on screen, and no form opened on top of the grid.
                await expect(page.getByTestId('tx-bulk-add-row')).toBeVisible();
                await expect(page.getByTestId('tx-form-modal')).toBeHidden();
                // Settled: the editor validated what it opened (a fresh editor counts from zero) and nothing is queued behind it.
                await expect(root).not.toHaveAttribute('data-validate-runs', '0', {timeout: 25_000});
                await waitForSettled(root, 25_000);
            } finally {
                page.off('request', record);
            }
            expect(sent.length, 'premise: the editor sent the validation it ran').toBeGreaterThan(0);

            // Nothing was edited: nothing to save, nothing to reset, no update on the wire.
            await expect.soft(page.getByTestId('tx-bulk-commit'), 'Save stays disabled once the editor has settled on untouched saved rows').toBeDisabled();
            await expect.soft(page.getByTestId('tx-bulk-reset-all'), 'no untouched saved row counts as edited').toBeHidden();
            const ownUpdates = sent.flatMap((batch) => batch.updates.filter((update) => saved.transactionIds.includes(update.id as number)).map((update) => ({path: batch.path, ...update})));
            expect.soft(ownUpdates, `no validate or commit carries an update for the untouched rows ${saved.transactionIds.join(', ')}`).toEqual([]);
        });
    });
});

// ---------------------------------------------------------------------------
// Owned data for WB4 and WB5
// ---------------------------------------------------------------------------
//
// Same toolkit as WB11 (`Owned`, `cleanupOwned`): every id recorded the moment it
// exists, everything deleted by id at the end whatever the outcome — never "what
// appeared since", which under four workers is also a neighbour's rows.

/** Run `body` with a record of what it creates, then delete exactly that, whatever the outcome. */
async function withOwned(page: Page, label: string, body: (owned: Owned) => Promise<void>): Promise<void> {
    const owned: Owned = {brokerIds: [], assetIds: [], transactionIds: []};
    let passed = false;
    try {
        await body(owned);
        passed = true;
    } finally {
        const failures = await cleanupOwned(page, owned);
        // A red keeps its own error; on a green, a cleanup that failed is a red of its own.
        if (passed) expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
        else if (failures.length > 0) console.warn(`[${label}] cleanup after a failure left behind: ${failures.join('; ')}`);
    }
}

/** A saved TRANSFER between two owned brokers: ids to find it in the table, the description that marks it on the grid. */
type OwnedTransferPair = {giverId: number; receiverId: number; description: string};

/**
 * Two owned brokers and an owned EUR asset. The sending broker holds two ADJUSTMENT lots,
 * +10 at 100 and +10 at 200 EUR per unit — an average of exactly 150 — and sends 4 units
 * to the receiving broker in a saved TRANSFER. The receiving half is saved with a MANUAL
 * cost of 175, so a clone that proposes 150 has computed it rather than copied the source.
 * Old fixed dates keep the rows at the bottom of every other test's table. The ledger is
 * read back, so the premise is checked rather than assumed.
 */
async function createOwnedTransferPair(page: Page, owned: Owned): Promise<OwnedTransferPair> {
    const suffix = uniqueSuffix();
    const brokerNames = [`WB5 from ${suffix}`, `WB5 to ${suffix}`];
    const brokers = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: brokerNames.map((name) => ({name, opened_at: '2020-01-01'}))}), 'create owned brokers');
    // Both ids are recorded before either is checked: a half-created setup still cleans up.
    for (const item of brokers.results) if (item.success && typeof item.broker_id === 'number') owned.brokerIds.push(item.broker_id);
    const [fromId, toId] = brokerNames.map((name) => brokers.results.find((item) => item.name === name && item.success)?.broker_id);
    if (typeof fromId !== 'number' || typeof toId !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(brokers)}`);

    const assetName = `WB5 asset ${suffix}`;
    const assets = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [{display_name: assetName, currency: 'EUR', asset_type: 'STOCK'}]}), 'create owned asset');
    const asset = assets.results.find((item) => item.display_name === assetName);
    if (!asset?.success || typeof asset.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(assets)}`);
    const assetId = asset.asset_id;
    owned.assetIds.push(assetId);

    const description = `WB5 transfer ${suffix}`;
    const linkUuid = randomUUID();
    const lot = (date: string, amount: string) => ({broker_id: fromId, asset_id: assetId, type: 'ADJUSTMENT', date, quantity: '10', cost_basis_override: {code: 'EUR', amount}, description: `WB5 lot ${amount} ${suffix}`});
    const creates = [
        lot('2024-01-02', '100'),
        lot('2024-01-03', '200'),
        {broker_id: fromId, asset_id: assetId, type: 'TRANSFER', date: '2024-01-04', quantity: '-4', link_uuid: linkUuid, description},
        {broker_id: toId, asset_id: assetId, type: 'TRANSFER', date: '2024-01-04', quantity: '4', link_uuid: linkUuid, description, cost_basis_override: {code: 'EUR', amount: '175'}},
    ];
    const committed = await jsonFrom<{committed: boolean; issues?: unknown; results: Array<{operation: string; ids?: number[]}>}>(await page.request.post(`${API}/transactions/commit`, {data: {creates}}), 'commit the owned lots and TRANSFER');
    const ids = committed.committed === true ? committed.results.filter((result) => result.operation === 'create').flatMap((result) => result.ids ?? []) : [];
    owned.transactionIds.push(...ids);
    expect(committed.committed, `owned rows rolled back: ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
    expect(ids, 'the commit created the two lots and both halves of the TRANSFER').toHaveLength(creates.length);

    const saved = await jsonFrom<Array<{id: number; type: string; broker_id: number; quantity: string; related_transaction_id?: number | null; cost_basis_override?: CostBasis | null}>>(await page.request.get(`${API}/transactions?${ids.map((id) => `ids=${id}`).join('&')}`), 'read the owned rows');
    const lots = saved
        .filter((tx) => tx.type === 'ADJUSTMENT')
        .map((tx) => Number(tx.cost_basis_override?.amount))
        .sort((a, b) => a - b);
    expect(lots, 'premise: the sending broker holds the two lots the average is made of').toEqual([100, 200]);
    const giver = saved.find((tx) => tx.type === 'TRANSFER' && tx.broker_id === fromId);
    const receiver = saved.find((tx) => tx.type === 'TRANSFER' && tx.broker_id === toId);
    if (!giver || !receiver) throw new Error(`The owned TRANSFER is missing a half: ${JSON.stringify(saved)}`);
    expect([giver.related_transaction_id, receiver.related_transaction_id], 'premise: the two halves are linked to each other').toEqual([receiver.id, giver.id]);
    expect(Number(giver.quantity), 'premise: the sending half takes 4 units out').toBe(-4);
    expect(receiver.cost_basis_override?.code, 'premise: the receiving half is saved with its manual cost').toBe('EUR');
    expect(Number(receiver.cost_basis_override?.amount), 'premise: the receiving half is saved with its manual cost').toBe(175);
    return {giverId: giver.id, receiverId: receiver.id, description};
}
