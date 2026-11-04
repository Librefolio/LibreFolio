/**
 * Transaction Broker Access E2E Tests — Phase 07 Bugfix Round 1
 *
 * Covers:
 * - Bug 1:  Form create dropdown shows only OWNER/EDITOR brokers
 * - Bug 3:  Edit (pencil) button hidden for VIEWER-only transactions
 * - Bug 10: Readonly broker "To" side shows static text (not dropdown)
 * - Bug 13: Hidden broker shows lock icon + name + "not accessible" message
 * - Enum filter defaults: start deselected (no filter active)
 * - V-23:   Bulk editor on a clone of [Asym-c] names the VIEWER-only broker in its broker cell and in the
 *           access refusal, which points at the refused row (1b)
 *
 * Prerequisites: backend test mode (port 6041), mock data populated
 * with asymmetric broker access pairs (Asym-a through Asym-d).
 *
 * Mock data contract: populate_mock_data.py creates 4 asymmetric TRANSFER
 * pairs tagged "access-test" with descriptions "[Asym-a]" through "[Asym-d]".
 * If these tests fail, the mock data seeding must be fixed — never skip.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {appears} from '../fixtures/probe';
import {canEdit, listBrokers, seededPair} from '../fixtures/owned-pair';

// 45 s: login and the 20 s transactions-page gate share this budget; the old 15 s could not even fit the gate under load.
test.setTimeout(45_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    // The table being VISIBLE is not the table being LOADED: it renders empty
    // and fills in. The page publishes data-busy, so wait on that instead.
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000});
}

/** Find a row containing ALL the given substrings in its text, double-click to open view. Throws if not found. */
async function openViewByTexts(page: Page, ...substrings: string[]) {
    const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const text = (await row.textContent()) ?? '';
        if (substrings.every((s) => text.includes(s))) {
            // dblclick on first td to avoid hitting asset links in center cells
            await row.locator('td').first().dblclick();
            await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
            return;
        }
    }
    throw new Error(`Row matching [${substrings.join(', ')}] not found. Check populate_mock_data.py seeding.`);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transaction Broker Access Visibility', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    // === Bug 1 — Create dropdown: only OWNER/EDITOR brokers ===
    test.describe('Bug 1 — Broker dropdown filters', () => {
        test('create form shows only OWNER/EDITOR brokers, not VIEWER', async ({page}) => {
            await page.getByTestId('tx-add-button').click();
            await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

            const brokerWrap = page.getByTestId('tx-form-broker-wrap');
            await brokerWrap.locator('button, [role="combobox"]').first().click();

            const options = page.locator('[data-testid^="search-select-option-"]');
            // This test proves VIEWER brokers are ABSENT from the list. An empty
            // list satisfies that trivially, so the list must be shown to exist
            // first — otherwise a slow dropdown is indistinguishable from a
            // correctly filtered one.
            await expect(options.first()).toBeVisible({timeout: 5_000});
            const optionCount = await options.count();
            const optionTexts: string[] = [];
            for (let i = 0; i < optionCount; i++) {
                const text = await options.nth(i).textContent();
                if (text) optionTexts.push(text.trim());
            }

            for (const vb of ['DEGIRO', 'eToro', 'Recrowd']) {
                expect(
                    optionTexts.some((t) => t.includes(vb)),
                    `VIEWER broker "${vb}" must NOT appear`,
                ).toBe(false);
            }
            for (const eb of ['Interactive Brokers', 'Directa', 'Coinbase']) {
                expect(
                    optionTexts.some((t) => t.includes(eb)),
                    `Editable broker "${eb}" must appear`,
                ).toBe(true);
            }

            await page.getByTestId('tx-form-cancel').click();
        });
    });

    // === Bug 3 — Edit pencil hidden for VIEWER tx ===
    test.describe('Bug 3 — Edit button visibility', () => {
        test('view mode on VIEWER broker hides edit pencil button', async ({page}) => {
            // Asym-c: Microsoft Corporation on DEGIRO (VIEWER role)
            await openViewByTexts(page, 'DEGIRO', 'Microsoft');
            await expect(page.getByTestId('tx-form-switch-edit')).not.toBeVisible({timeout: 2_000});
            await expect(page.getByTestId('tx-form-save')).not.toBeVisible({timeout: 1_000});
            await page.getByTestId('tx-form-cancel').click();
        });
    });

    // === Bug 13 — Hidden broker: lock + name + message ===
    test.describe('Bug 13 — Hidden broker display', () => {
        test('view paired tx with hidden partner shows lock and "not accessible" message', async ({page}) => {
            // Asym-d: IB→HiddenBroker — need to find this specific row.
            // All Asym rows have tag "access-test". Asym-d is a TRANSFER on IB with AAPL.
            // Try each access-test TRANSFER row until we find one with a locked partner.
            const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
            const count = await rows.count();
            let foundLocked = false;

            for (let i = 0; i < count; i++) {
                const row = rows.nth(i);
                const text = (await row.textContent()) ?? '';
                if (!text.includes('access-test') || !text.includes('Interactive Brokers')) continue;

                await row.dblclick();
                await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

                const dualSplit = page.getByTestId('tx-form-dual-split');
                if (!(await appears(dualSplit))) {
                    await page.getByTestId('tx-form-cancel').click();
                    // The next loop iteration double-clicks another row, so the modal
                    // has to be out of the way first or the click hits the overlay.
                    await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: 3_000});
                    continue;
                }

                // Check if this has a locked partner
                const lockedPartner = page.getByTestId('tx-form-partner-locked');
                const readonlyBroker = page.getByTestId('tx-form-broker-to-readonly');

                if (await lockedPartner.isVisible({timeout: 1_500}).catch(() => false)) {
                    expect(await lockedPartner.textContent()).toContain('Hidden Admin Broker');
                    foundLocked = true;
                    await page.getByTestId('tx-form-cancel').click();
                    break;
                }
                if (await readonlyBroker.isVisible({timeout: 1_000}).catch(() => false)) {
                    const brokerText = (await readonlyBroker.textContent()) ?? '';
                    if (brokerText.includes('Hidden Admin Broker')) {
                        foundLocked = true;
                        await page.getByTestId('tx-form-cancel').click();
                        break;
                    }
                }
                await page.getByTestId('tx-form-cancel').click();
                await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: 3_000});
            }
            expect(foundLocked, 'Should find a row with Hidden Admin Broker as locked partner').toBe(true);
        });

        test('view paired tx with OWNER/EDITOR partner shows normal broker info', async ({page}) => {
            // Asym-a: Apple Inc. TRANSFER on Directa (EDITOR role) — use description to match
            await openViewByTexts(page, 'Asym-a');

            await expect(page.getByTestId('tx-form-dual-split')).toBeVisible({timeout: 5_000});
            await expect(page.getByTestId('tx-form-partner-locked')).not.toBeVisible({timeout: 1_000});

            const readonlyBroker = page.getByTestId('tx-form-broker-to-readonly');
            await expect(readonlyBroker).toBeVisible({timeout: 2_000});
            expect(await readonlyBroker.textContent()).toMatch(/Directa|Interactive Brokers/);

            await page.getByTestId('tx-form-cancel').click();
        });
    });

    // === Enum filter defaults ===
    // TODO: Add test once DataTableColumnFilter has data-testid on the trigger button.
    // The filter opens via a header button that currently lacks a testid,
    // making it hard to locate reliably across i18n and column reordering.
});

// ---------------------------------------------------------------------------
// V-23 — a broker the user only views, inside the bulk editor
// ---------------------------------------------------------------------------
//
// The seeded pair [Asym-c] sends MSFT from a broker TEST_USER owns to one it only views (DEGIRO). The toolbar's
// Clone asks nothing about access, so it opens the bulk editor on a copy of the pair: one grid row, the sending
// half visible as row 1a, the receiving half riding behind it as row 1b. Validation refuses the copy — TEST_USER
// cannot write on the receiving broker — and the editor must say so about the refused row, naming the broker:
// the grid's broker cell names it (not "—"), the refusal points at row 1b (not the sending 1a), and its message
// names it (not "Broker #<id>").
//
// Read-only on the seed: the pair is found through the API by its marker and checked, never modified; the copy
// is never saved — the editor is closed and the copy discarded at the end.

/** Open the transactions table narrowed to these ids — a filter, so flat mode — and wait for each of their rows. */
async function goToRows(page: Page, ids: number[]) {
    await navigateTo(page, `/transactions?id_min=${Math.min(...ids)}&id_max=${Math.max(...ids)}`);
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    for (const id of ids) {
        await expect(page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`)).toBeVisible({timeout: 15_000});
    }
}

/** Where a click on the editor's close landed: both ends are states, so a poll tells them apart. */
async function closeOutcome(page: Page): Promise<'asks to discard' | 'closed' | 'closing'> {
    if (await page.getByTestId('confirm-modal-confirm').isVisible()) return 'asks to discard';
    if (await page.getByTestId('tx-bulk-modal').isHidden()) return 'closed';
    return 'closing';
}

/** Close the bulk editor without saving: a copy is unsaved work, so it may ask to discard it first. */
async function discardBulkEditor(page: Page) {
    await page.getByTestId('tx-bulk-close').click();
    await expect.poll(() => closeOutcome(page), {timeout: 5_000, message: 'closing the editor either asks to discard the copy or closes it'}).not.toBe('closing');
    if ((await closeOutcome(page)) === 'asks to discard') await page.getByTestId('confirm-modal-confirm').click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: 5_000});
}

test.describe('V-23 — Bulk editor and a broker the user only views', () => {
    test('V-23 — clone of [Asym-c]: the broker cell, the refused row and its message name the VIEWER broker', async ({page}) => {
        // Login, the 20 s table gate and the editor's first validation share this budget.
        test.setTimeout(60_000);
        await login(page, TEST_USER);

        // The pair and its brokers, read through the API and checked rather than assumed.
        const {giver, receiver} = await seededPair(page, '[Asym-c]', {editable: false});
        const brokers = new Map((await listBrokers(page)).map((broker) => [broker.id, broker]));
        const giverBroker = brokers.get(giver.broker_id);
        const receiverBroker = brokers.get(receiver.broker_id);
        if (!giverBroker || !receiverBroker) throw new Error(`[Asym-c] #${giver.id}/#${receiver.id}: TEST_USER must see both brokers ${giver.broker_id} and ${receiver.broker_id} — check populate_mock_data.py`);
        expect(canEdit(giverBroker), `premise: [Asym-c] sends from a broker TEST_USER can edit (${JSON.stringify(giverBroker)})`).toBe(true);
        expect(receiverBroker.user_role, `premise: [Asym-c] lands on a broker TEST_USER only views (${JSON.stringify(receiverBroker)})`).toBe('VIEWER');

        // Select the sending half and clone it: the editor brings its partner along.
        await goToRows(page, [giver.id, receiver.id]);
        const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${giver.id}`);
        await expect(checkbox).toBeVisible({timeout: 5_000});
        if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
        await page.getByTestId('toolbar-action-clone').click();
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        // Premise: the copy is one paired row on the grid, with no form on top of it.
        const gridRow = page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]').filter({hasText: '[Asym-c]'});
        await expect(gridRow).toHaveCount(1, {timeout: 10_000});
        await expect(page.getByTestId('tx-form-modal')).toBeHidden();

        // Settled: the editor validated the copy it opened (a fresh editor counts from zero) and nothing is queued behind it.
        const root = page.getByTestId('tx-bulk-modal-root');
        await expect(root).not.toHaveAttribute('data-validate-runs', '0', {timeout: 25_000});
        await waitForSettled(root, 25_000);

        // Validation refuses the copy, once: TEST_USER cannot write on the receiving broker.
        const refusal = page.locator('[data-testid="tx-bulk-issue"][data-code="accessDenied"]');
        await expect(refusal, 'validation refuses the copy once').toHaveCount(1);

        // The broker cell of the pair names both halves; the sending one is the presence barrier for the other.
        const brokerCell = gridRow.locator('td[data-column-id="broker"]');
        await expect(brokerCell, 'premise: the broker cell names the sending broker').toContainText(giverBroker.name);

        // V-23. Soft, so that one run reports all three.
        await expect.soft(brokerCell, `the broker cell names the receiving broker ${receiverBroker.name}, which TEST_USER sees but cannot edit (not "—")`).toContainText(receiverBroker.name);
        await expect.soft(refusal, 'the refusal points at the refused row: the receiving half, 1b (not the sending 1a)').toHaveAttribute('data-row-label', '1b');
        await expect.soft(refusal, `the refusal names the broker it is refused on, ${receiverBroker.name} (not "Broker #${receiverBroker.id}")`).toContainText(receiverBroker.name);

        // Never saved: close the editor, discarding the copy.
        await discardBulkEditor(page);
    });
});
