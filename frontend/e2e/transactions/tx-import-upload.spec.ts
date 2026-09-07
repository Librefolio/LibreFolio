/**
 * Import Wizard — Upload step (step 1) E2E tests
 *
 * The wizard's entry step is where a user drops files, the client validates them, and a
 * broker is assigned before anything is sent to the server. None of it touched the server:
 * files are only POSTed to /brokers/import/upload when "Next" is clicked, and these tests
 * never leave step 1, so they perform ZERO backend writes and need no cleanup.
 *
 * That also makes the whole file safe to run fully in parallel: each test opens its own
 * wizard instance (per page/context) which starts with an empty pending-file list, so the
 * pending table is owned entirely by the test that populated it — no shared state, no
 * `mode: 'serial'`.
 *
 * Covered (all client-side in ImportWizardModal.svelte):
 *   - validateExtension → an allowed-but-wrong extension (.txt) becomes an error row
 *   - FileUploader blocked extension (.exe) → error banner, nothing added
 *   - FileUploader size guard (> 10 MB) → error banner, nothing added
 *   - step1CanProceed: empty vs error row vs unassigned broker vs assigned
 *   - onGlobalBrokerChange: "assign all" fills every unassigned file
 *   - dropZoneExpanded: collapses after an add, re-expands after clear
 *   - clearAllPendingFiles + the "upload more" re-expand toggle
 *   - handleClose / confirmDiscard: the unsaved-work discard guard (both branches)
 *
 * Entry point: the transactions toolbar "Import" button (`tx-import-button`) sets
 * bulkIntent={action:'import'}, and the BulkModal auto-opens the wizard on that intent —
 * a clean entry that never selects a table row by position.
 */

import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {uniqueSuffix} from '../fixtures/unique';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(30_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** Open the wizard via the toolbar Import button; wait until step 1 has settled. */
async function openImportWizard(page: Page) {
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: 8_000});
    const step1 = page.getByTestId('import-wizard-step1');
    await step1.waitFor({state: 'visible', timeout: 5_000});
    await waitForSettled(step1, 15_000);
    return step1;
}

/** setInputFiles on the (hidden) file input inside the expanded drop zone. */
async function dropFiles(page: Page, files: {name: string; mimeType: string; buffer: Buffer}[]) {
    const input = page.getByTestId('import-wizard-step1').locator('[data-testid="file-input"]');
    await input.setInputFiles(files);
}

const csv = (name: string, body = 'Date,Type,Amount\n2024-01-01,DEPOSIT,100\n') => ({
    name,
    mimeType: 'text/csv',
    buffer: Buffer.from(body),
});

/** The pending-file rows in the (owned) step-1 table. */
function pendingRows(page: Page) {
    return page.getByTestId('import-wizard-step1').locator('tbody tr[data-row-id]');
}

/** Open the "assign all" global broker dropdown and wait until it has loaded. */
async function openGlobalBrokerDropdown(page: Page) {
    await page.getByTestId('import-wizard-step1-broker-select').locator('[role="combobox"]').click();
    const listbox = page.locator('[role="listbox"]').first();
    await expect(listbox).toBeVisible({timeout: 5_000});
    await expect(listbox).toHaveAttribute('aria-busy', 'false', {timeout: 8_000});
}

/** Pick the first editable broker (the option set is materialised = filtered by construction). */
async function pickFirstBrokerOption(page: Page) {
    const options = page.locator('[data-testid^="search-select-option-"]');
    await expect(options.first()).toBeVisible({timeout: 5_000});
    await options.first().click();
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 8_000});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Import Wizard — upload step', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
        await openImportWizard(page);
    });

    test('U1: allowed-but-wrong extension (.txt) becomes an error row and blocks Next', async ({page}) => {
        await dropFiles(page, [{name: `notes-${uniqueSuffix()}.txt`, mimeType: 'text/plain', buffer: Buffer.from('hello')}]);

        const rows = pendingRows(page);
        await expect(rows).toHaveCount(1);
        // The status cell is a semantic badge; assert the variant, never the (translated) text.
        await expect(rows.first().locator('[data-badge-variant="error"]')).toBeVisible({timeout: 5_000});

        // An error file cannot proceed even though a broker default may be set.
        await expect(page.getByTestId('import-wizard-next')).toBeDisabled();
    });

    test('U2: blocked extension (.exe) raises the error banner and adds nothing', async ({page}) => {
        await dropFiles(page, [{name: `payload-${uniqueSuffix()}.exe`, mimeType: 'application/octet-stream', buffer: Buffer.from('MZ')}]);

        await expect(page.getByTestId('info-banner-error')).toBeVisible({timeout: 5_000});
        // Rejected by the uploader before it ever reached the pending list.
        await expect(pendingRows(page)).toHaveCount(0);
        // With no pending files, step 1 is skippable, so Next stays enabled.
        await expect(page.getByTestId('import-wizard-next')).toBeEnabled();
    });

    test('U3: an oversize file (> 10 MB) raises the error banner and adds nothing', async ({page}) => {
        const tooBig = Buffer.alloc(11 * 1024 * 1024, 97); // 11 MB of 'a'
        await dropFiles(page, [{name: `huge-${uniqueSuffix()}.csv`, mimeType: 'text/csv', buffer: tooBig}]);

        await expect(page.getByTestId('info-banner-error')).toBeVisible({timeout: 5_000});
        await expect(pendingRows(page)).toHaveCount(0);
    });

    test('U4: a valid file with no broker blocks Next until a broker is assigned', async ({page}) => {
        await dropFiles(page, [csv(`import-${uniqueSuffix()}.csv`)]);

        const rows = pendingRows(page);
        await expect(rows).toHaveCount(1);
        // "Ready" state renders the default badge variant.
        await expect(rows.first().locator('[data-badge-variant="default"]')).toBeVisible({timeout: 5_000});
        // No broker yet → cannot proceed.
        await expect(page.getByTestId('import-wizard-next')).toBeDisabled();

        await openGlobalBrokerDropdown(page);
        await pickFirstBrokerOption(page);

        // Assigning a broker to the only file unblocks Next.
        await expect(page.getByTestId('import-wizard-next')).toBeEnabled({timeout: 5_000});
    });

    test('U5: adding a file collapses the drop zone; Clear removes it and re-expands', async ({page}) => {
        // Drop zone starts expanded (the uploader is visible).
        await expect(page.getByTestId('import-wizard-step1').locator('[data-testid="file-uploader"]')).toBeVisible();

        await dropFiles(page, [csv(`clearme-${uniqueSuffix()}.csv`)]);
        await expect(pendingRows(page)).toHaveCount(1);

        // After an add the zone collapses to the "upload more" affordance.
        await expect(page.getByTestId('import-wizard-upload-more')).toBeVisible({timeout: 5_000});
        await expect(page.getByTestId('import-wizard-step1').locator('[data-testid="file-uploader"]')).toHaveCount(0);

        // Clear all from the collapsed state → table gone, drop zone re-expands, "upload more" disappears.
        await page.getByTestId('import-wizard-clear').click();
        await expect(pendingRows(page)).toHaveCount(0);
        await expect(page.getByTestId('import-wizard-upload-more')).toHaveCount(0);
        await expect(page.getByTestId('import-wizard-step1').locator('[data-testid="file-uploader"]')).toBeVisible({timeout: 5_000});
    });

    test('U5b: "upload more" re-expands the collapsed drop zone', async ({page}) => {
        await dropFiles(page, [csv(`expandme-${uniqueSuffix()}.csv`)]);
        await expect(pendingRows(page)).toHaveCount(1);

        // Collapsed: uploader hidden, "upload more" shown.
        const uploader = page.getByTestId('import-wizard-step1').locator('[data-testid="file-uploader"]');
        await expect(page.getByTestId('import-wizard-upload-more')).toBeVisible({timeout: 5_000});
        await expect(uploader).toHaveCount(0);

        // Re-expand via the affordance → uploader visible again, file still pending.
        await page.getByTestId('import-wizard-upload-more').click();
        await expect(uploader).toBeVisible({timeout: 5_000});
        await expect(pendingRows(page)).toHaveCount(1);
    });

    test('U6: two valid files, "assign all" broker fills both and unblocks Next', async ({page}) => {
        await dropFiles(page, [csv(`multi-a-${uniqueSuffix()}.csv`), csv(`multi-b-${uniqueSuffix()}.csv`)]);

        await expect(pendingRows(page)).toHaveCount(2);
        // Two unassigned files → Next disabled.
        await expect(page.getByTestId('import-wizard-next')).toBeDisabled();

        await openGlobalBrokerDropdown(page);
        await pickFirstBrokerOption(page);

        // The global broker fills every unassigned file at once.
        await expect(pendingRows(page)).toHaveCount(2);
        await expect(page.getByTestId('import-wizard-next')).toBeEnabled({timeout: 5_000});
    });

    test('U7: closing with unsaved files prompts a discard guard (cancel keeps, confirm discards)', async ({page}) => {
        await dropFiles(page, [csv(`discard-${uniqueSuffix()}.csv`)]);
        await expect(pendingRows(page)).toHaveCount(1);

        // Close → discard confirmation (there is unsaved work).
        await page.getByTestId('import-wizard-close').click();
        await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: 5_000});

        // Cancel keeps the wizard open on step 1.
        await page.getByTestId('confirm-modal-cancel').click();
        await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0, {timeout: 5_000});
        await expect(page.getByTestId('import-wizard-step1')).toBeVisible();

        // Close again and confirm → the wizard tears down.
        await page.getByTestId('import-wizard-close').click();
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 5_000});
    });
});
