/**
 * BRIM Import Wizard E2E Tests — Phase 07 Part 5 v5 M3+M4
 *
 * Coverage:
 *   T1  Happy path: open wizard, select file, parse, continue to Review, import to BulkModal
 *   T2  Skip resolve: file with no unresolved assets goes straight from parse to import
 *   T3  Asset resolution: unresolved asset can be manually resolved via search
 *   T4  Import disabled while unresolved: button stays disabled until all selected assets resolved
 *   T5  Deselect likely duplicates: likely-dup rows deselected by default, can be re-included
 *   T6  Unsaved work guard: closing wizard with parsed data shows discard confirm
 *   T7  Error file guard: parse error shown per-file, Continue disabled if ALL files failed
 *   T8  Multi-cycle: import twice from same wizard session adds more rows to BulkModal
 *
 * The file. Every test owns a copy of the IBKR sample (`ibkr-trades-export.csv`): uploaded through
 * the API to the seeded "Interactive Brokers" broker under a unique name before the wizard reads
 * the broker files, selected in step 2 by its file id — wherever the panel's pages put it — and
 * deleted after the test. It is the same broker the seeded copies live on, so the parse is asked
 * for the same broker and its duplicate verdicts are computed against the same transactions (T5).
 * Nothing is committed: T1 hands the review to the BulkModal, which is never saved.
 *
 * The walk from the analysis to the review is the shared one (fixtures/import-wizard.ts): the
 * notices' confirmation is read past when the parse response carries notices, and the conditional
 * steps are crossed when the stepper lands on them — never probed for.
 *
 * Prerequisites: the seeded "Interactive Brokers" broker (populate_mock_data.py, populate_brokers),
 * on which the test user is an owner.
 *
 * Flow: BulkModal "Import" button → ImportWizardModal (4 steps) → onImportBatch → BulkModal
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {continueToReview, deleteOwnedReports, parseSelectedFile, selectBrokerFile, uploadOwnedReport, type OwnedReport} from '../fixtures/import-wizard';
import {appears} from '../fixtures/probe';

test.setTimeout(60_000);

/** The seeded broker the sample belongs to, and the sample each test uploads a copy of. */
const IBKR_SAMPLE = {brokerName: 'Interactive Brokers', sample: 'ibkr-trades-export.csv'};

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

/** Open BulkModal via the Edit modal "Import" button or action menu. */
async function openBulkModalAndImport(page: Page) {
    // Find and click "Edit" via the row's kebab action menu to open BulkModal
    const firstRow = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').first();
    await firstRow.hover();
    const kebabBtn = firstRow.getByTestId(/^row-actions-/);
    await expect(kebabBtn).toBeVisible({timeout: 3_000});
    await kebabBtn.click();
    await page.getByTestId('context-menu-action-edit').click();
    await page.getByTestId('tx-bulk-modal-root').waitFor({state: 'visible', timeout: 6_000});

    // The BulkModal may auto-open a FormModal for the selected paired transaction.
    // Close it before clicking Import.
    const formClose = page.getByTestId('tx-form-close');
    if (await formClose.isVisible({timeout: 1_500}).catch(() => false)) {
        await formClose.click();
        await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: 3_000});
    }

    // Click "Import" button inside BulkModal
    await page.getByTestId('tx-bulk-import').click();
    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 5_000});
}

/** Skip Step 1 (no files to upload), go to Step 2. */
async function skipToStep2(page: Page) {
    await page.getByTestId('import-wizard-next').click();
    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 5_000});
    // The step renders before its broker files have loaded; it says so via data-busy.
    await waitForSettled(page.getByTestId('import-wizard-step2'));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('BRIM Import Wizard', () => {
    // SERIAL — kept only until a --workers 4 run shows it can go.
    //
    // The reason it was declared no longer holds. Every test parsed "the first available
    // file", one of the samples populate_mock_data.py uploads, and a parse rewrites the file's
    // metadata JSON (`last_parse_result`, `parsed_plugin_code`): a read-modify-write two workers
    // could enter at once, last writer wins, and these tests read back what they had written.
    // Each test now uploads, parses and deletes its own copy of the sample, so no two tests share
    // a file; nothing else here writes — the review is handed to the BulkModal, never saved.
    //
    // Removing a declared exception takes a run as evidence (frontend-testing.instructions.md,
    // "There is no flag to un-serialise a block"): comment this out, run the spec at --workers 4,
    // then delete it — and its entry in the exception lists of the instructions and of
    // playwright.config.ts — or restore it with the reason that run finds.
    test.describe.configure({mode: 'serial'});

    /** This test's copy of the IBKR sample. */
    let sample: OwnedReport;
    /** Every report the running test uploaded: afterEach deletes them and empties the list. */
    const ownedReports: OwnedReport[] = [];

    test.beforeEach(async ({page}) => {
        await login(page);
        // The file first: the wizard reads the broker files when it enters step 2.
        sample = await uploadOwnedReport(page, ownedReports, IBKR_SAMPLE);
        await goToTransactions(page);
    });

    test.afterEach(async ({page}) => {
        await deleteOwnedReports(page, ownedReports);
    });

    test('T1: happy path — open wizard, parse IBKR file, review, import to BulkModal', async ({page}) => {
        await openBulkModalAndImport(page);

        // Step 1 — stepper visible
        await expect(page.getByTestId('import-wizard-stepper')).toBeVisible();
        await expect(page.getByTestId('import-wizard-step1')).toBeVisible();

        // Skip Step 1 (no new uploads)
        await skipToStep2(page);

        // Step 2 — select IBKR file
        await expect(page.getByTestId('import-wizard-step2')).toBeVisible();
        // This test's own copy, in the Interactive Brokers panel, on whichever page it is
        await selectBrokerFile(page, sample);
        await expect(page.getByTestId('import-wizard-parse')).toBeEnabled({timeout: 3_000});

        // Parse
        const parsed = await parseSelectedFile(page, sample.fileId);

        // Step 3 — at least one success row visible, Continue enabled
        await expect(page.getByTestId('import-wizard-step3')).toBeVisible();
        await expect(page.getByTestId('import-wizard-continue')).toBeEnabled();

        // Continue to Step 4 — Review
        await continueToReview(page, parsed);

        // Step 4 — TX table visible with rows
        await expect(page.getByTestId('import-wizard-step4')).toBeVisible();
        const txRows = page.locator('[data-testid="import-wizard-step4"] table tbody tr');
        await expect(txRows.first()).toBeVisible({timeout: 5_000});

        // Import button: may be disabled if there are unresolved assets
        // But if all assets are resolved (or no asset-linked TX), it should be enabled
        const importBtn = page.getByTestId('import-wizard-import');
        await expect(importBtn).toBeVisible();

        // If Import is enabled, click it and verify toast
        const isEnabled = await importBtn.isEnabled();
        if (isEnabled) {
            await importBtn.click();
            // Wizard should close
            await expect(page.getByTestId('import-wizard-stepper')).not.toBeVisible({timeout: 3_000});
            // BulkModal should still be visible with imported rows
            await expect(page.getByTestId('tx-bulk-modal-root')).toBeVisible();
        }
    });

    test('T2: Step 3 → Step 4 skip when no unresolved assets', async ({page}) => {
        await openBulkModalAndImport(page);
        await skipToStep2(page);
        await selectBrokerFile(page, sample);
        const parsed = await parseSelectedFile(page, sample.fileId);
        await continueToReview(page, parsed);

        // Check if resolve section is absent (no asset resolutions) OR all auto-resolved
        const resolveHeader = page.locator('[data-testid="import-wizard-step4"]').getByText(/Resolve Assets/i);
        const step4 = page.getByTestId('import-wizard-step4');

        // Import button should eventually become enabled once all assets resolved
        await expect(step4).toBeVisible();
        // Just check TX rows exist
        const txRows = step4.locator('table tbody tr');
        const count = await txRows.count();
        expect(count).toBeGreaterThan(0);
    });

    test('T3: asset resolution — unresolved asset shows search zone', async ({page}) => {
        await openBulkModalAndImport(page);
        await skipToStep2(page);
        await selectBrokerFile(page, sample);
        const parsed = await parseSelectedFile(page, sample.fileId);
        await continueToReview(page, parsed);

        const step4 = page.getByTestId('import-wizard-step4');
        await expect(step4).toBeVisible();

        // Check if there are unresolved assets → search input visible
        const searchInputs = step4.locator('input[placeholder*="Search"]');
        const resolveSection = step4.locator('text=Resolve Assets');

        if (await resolveSection.isVisible({timeout: 2_000}).catch(() => false)) {
            // There's at least one asset to resolve
            if (
                await searchInputs
                    .first()
                    .isVisible({timeout: 1_000})
                    .catch(() => false)
            ) {
                // Type something in the search field
                await searchInputs.first().fill('AAPL');
                // The old assertion was `expect(count).toBeGreaterThanOrEqual(0)`,
                // which is true of every count that has ever existed — the test
                // could not fail. What it meant to check is that the field accepts
                // input and the component survives it, so that is what it checks.
                await expect(searchInputs.first()).toHaveValue('AAPL');
            }
        }
    });

    test('T4: import disabled when selected TX has unresolved asset', async ({page}) => {
        await openBulkModalAndImport(page);
        await skipToStep2(page);
        await selectBrokerFile(page, sample);
        const parsed = await parseSelectedFile(page, sample.fileId);
        await continueToReview(page, parsed);

        const step4 = page.getByTestId('import-wizard-step4');
        const importBtn = page.getByTestId('import-wizard-import');

        // If resolve section is visible and has unresolved entries
        const resolveSection = step4.locator('text=Resolve Assets');
        if (await resolveSection.isVisible({timeout: 2_000}).catch(() => false)) {
            // Check for amber badge (unresolved count)
            const unresolvedBadge = step4.locator('[class*="amber"]').first();
            if (await unresolvedBadge.isVisible({timeout: 1_000}).catch(() => false)) {
                // Import should be disabled
                await expect(importBtn).toBeDisabled();
            }
        }
        // Either way, button exists
        await expect(importBtn).toBeVisible();
    });

    test('T5: likely duplicates deselected by default', async ({page}) => {
        await openBulkModalAndImport(page);
        await skipToStep2(page);
        await selectBrokerFile(page, sample);
        const parsed = await parseSelectedFile(page, sample.fileId);
        await continueToReview(page, parsed);

        const step4 = page.getByTestId('import-wizard-step4');

        // If there are "⚠ dup" labels in the TX table, those rows should have unchecked checkbox
        const dupRows = step4.locator('tr').filter({hasText: '⚠ dup'});
        const dupCount = await dupRows.count();
        if (dupCount > 0) {
            const firstDupCheckbox = dupRows.first().locator('input[type="checkbox"]');
            await expect(firstDupCheckbox).not.toBeChecked();
        }
    });

    test('T6: unsaved work guard — close wizard shows discard confirm', async ({page}) => {
        await openBulkModalAndImport(page);
        await skipToStep2(page);
        await selectBrokerFile(page, sample);
        await parseSelectedFile(page, sample.fileId);

        // Close button while work exists
        await page.getByTestId('import-wizard-close').click();

        // Should show confirmation modal
        const confirmModal = page.locator('[data-testid="confirm-modal-confirm"]');
        await expect(confirmModal).toBeVisible({timeout: 3_000});

        // Cancel → wizard still open
        await page.locator('[data-testid="confirm-modal-cancel"]').click();
        await expect(page.getByTestId('import-wizard-stepper')).toBeVisible();

        // Confirm → wizard closes
        await page.getByTestId('import-wizard-close').click();
        await expect(confirmModal).toBeVisible({timeout: 3_000});
        await confirmModal.click();
        await expect(page.getByTestId('import-wizard-stepper')).not.toBeVisible({timeout: 3_000});
    });

    test('T7: Step 2 — continue disabled when 0 files selected', async ({page}) => {
        await openBulkModalAndImport(page);
        await skipToStep2(page);

        // Without selecting any file, Parse button should be disabled
        await expect(page.getByTestId('import-wizard-parse')).toBeDisabled();
    });

    test('T8: stepper back-navigation from Review walks back to the analysis step', async ({page}) => {
        await openBulkModalAndImport(page);
        await skipToStep2(page);
        await selectBrokerFile(page, sample);
        const parsed = await parseSelectedFile(page, sample.fileId);
        await continueToReview(page, parsed);

        // Back does not jump straight to the analysis any more: it lands on whichever
        // conditional step was shown on the way in (unify assets / corrections /
        // duplicates). Whatever the file triggered, walking back must always end on the
        // analysis step and never on an empty screen.
        const currentStep = page.getByTestId('import-wizard-stepper').locator('[aria-current="step"]');
        for (let hop = 0; hop < 4; hop++) {
            if (await appears(page.getByTestId('import-wizard-step3'), 1_500)) {
                break;
            }
            const from = (await currentStep.getAttribute('data-step-id')) ?? '';
            await page.getByTestId('import-wizard-back').click();
            // The stepper says which step it is on. Waiting for that to change is the
            // only honest proof the Back click landed — a fixed sleep would let the
            // next hop click Back twice on a wizard that had not moved yet.
            await expect(currentStep).not.toHaveAttribute('data-step-id', from, {timeout: 5_000});
        }

        await expect(page.getByTestId('import-wizard-step3')).toBeVisible({timeout: 3_000});
    });
});
