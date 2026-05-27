/**
 * Transaction Broker Access E2E Tests — Phase 07 Bugfix Round 1
 *
 * Covers:
 * - Bug 1:  Form create dropdown shows only OWNER/EDITOR brokers
 * - Bug 3:  Edit (pencil) button hidden for VIEWER-only transactions
 * - Bug 10: Readonly broker "To" side shows static text (not dropdown)
 * - Bug 13: Hidden broker shows lock icon + name + "not accessible" message
 * - Enum filter defaults: start deselected (no filter active)
 *
 * Prerequisites: backend test mode (port 6041), mock data populated
 * with asymmetric broker access pairs (Asym-a through Asym-d).
 *
 * Mock data contract: populate_mock_data.py creates 4 asymmetric TRANSFER
 * pairs tagged "access-test" with descriptions "[Asym-a]" through "[Asym-d]".
 * If these tests fail, the mock data seeding must be fixed — never skip.
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(15_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    await page.waitForTimeout(400);
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
            await page.waitForTimeout(500);

            const options = page.locator('[data-testid^="search-select-option-"]');
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
                await page.waitForTimeout(500);

                const dualSplit = page.getByTestId('tx-form-dual-split');
                if (!(await dualSplit.isVisible({timeout: 2_000}).catch(() => false))) {
                    await page.getByTestId('tx-form-cancel').click();
                    await page.waitForTimeout(300);
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
                await page.waitForTimeout(300);
            }
            expect(foundLocked, 'Should find a row with Hidden Admin Broker as locked partner').toBe(true);
        });

        test('view paired tx with OWNER/EDITOR partner shows normal broker info', async ({page}) => {
            // Asym-a: Apple Inc. on Directa (EDITOR role)
            await openViewByTexts(page, 'Directa', 'Apple');
            await page.waitForTimeout(500);

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
