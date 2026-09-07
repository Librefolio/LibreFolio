/**
 * Import Wizard — analyze step + navigation + review controls E2E tests
 *
 * The two existing import specs traverse the select and analyze steps only as a corridor to
 * reach the resolution work in step 4 — they never exercise the analyze step's own controls
 * (the per-file detail modal, the aggregate "view all", re-parse) nor the step-to-step
 * navigation, nor the review-step selection toolbar. This spec covers exactly that gap.
 *
 * File under test: each test UPLOADS its OWN unique CSV (upload → assign broker → Next →
 * select → parse). This is deliberate. Selecting the shared seeded generic_simple.csv and
 * parsing it from many tests at once trips a backend race (documented in the report): the
 * first parse renames the file uploaded/ → parsed/, and a sibling parse that resolved the old
 * path then fails its `can_parse` guard with a spurious "cannot parse file". Giving every test
 * its own file means no two parses ever contend for the same path, so the corridor is
 * race-free by construction — and it covers the upload→commit→select path as a bonus.
 *
 * The uploaded file is a filesystem artifact only (no `Transaction` rows — these tests stop at
 * review and never click Import), it carries a unique name so it is invisible to other specs'
 * name-filtered selections, and `db populate --with-reports` wipes broker_reports/{uploaded,
 * parsed}/ before seeding, so nothing accumulates across runs. No DB cleanup is needed.
 *
 * State handles added to the product for this spec (they publish states a user also benefits
 * from — see frontend-testing.instructions.md rule 4):
 *   import-wizard-view-all / import-wizard-reparse   — analyze aggregate actions
 *   import-wizard-select-all / import-wizard-deselect-all — review selection toolbar
 *   parse-detail-close                                — ParseDetailModal close button
 *   data-selected-count / data-total-count on step4   — the review selection count
 */

import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {uniqueSuffix} from '../fixtures/unique';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(90_000);

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
}

/**
 * A minimal, valid generic CSV: three cash movements, no asset column, so the parse resolves
 * cleanly (no unresolved assets, no corrections) and walks analyze → review directly. The
 * marker keeps the descriptions unique to this file/run.
 */
function csv(marker: string): {name: string; mimeType: string; buffer: Buffer} {
    const body = 'date,type,quantity,amount,currency,asset,description\n' + `2025-03-01,DEPOSIT,0,10000.00,EUR,,Funding ${marker}\n` + `2025-03-02,WITHDRAWAL,0,-250.00,EUR,,Cash out ${marker}\n` + `2025-03-03,DEPOSIT,0,175.50,EUR,,Top up ${marker}\n`;
    return {name: `flow-${marker}.csv`, mimeType: 'text/csv', buffer: Buffer.from(body)};
}

/**
 * Assign the uploaded file(s) to a broker the test user owns (Interactive Brokers), via the
 * step-1 "assign all" dropdown. Picking a *named* broker keeps the choice deterministic and
 * independent of dropdown ordering or brokers a concurrent test may add — and Interactive
 * Brokers is seeded OWNER for TEST_USER, so it is always in the (EDITOR+) upload dropdown.
 */
async function assignBroker(page: Page) {
    await page.getByTestId('import-wizard-step1-broker-select').locator('[role="combobox"]').click();
    const option = page.locator('[data-testid^="search-select-option-"]').filter({hasText: 'Interactive Brokers'});
    await expect(option.first()).toBeVisible({timeout: 8_000});
    await option.first().click();
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 8_000});
}

/**
 * Full corridor from a freshly opened wizard to the settled analyze step, using a file this
 * test owns. Returns the file's unique name for row-scoped assertions.
 */
async function reachAnalyze(page: Page): Promise<string> {
    const file = csv(uniqueSuffix());

    // Step 1: upload this test's own file, assign a broker, advance.
    const input = page.getByTestId('import-wizard-step1').locator('[data-testid="file-input"]');
    await input.setInputFiles(file);
    await expect(page.getByTestId('import-wizard-step1').locator('tbody tr[data-row-id]')).toHaveCount(1);
    await assignBroker(page);
    await expect(page.getByTestId('import-wizard-next')).toBeEnabled({timeout: 5_000});
    await page.getByTestId('import-wizard-next').click();

    // Step 2: the just-uploaded file is listed for the chosen broker — select it and parse.
    const step2 = page.getByTestId('import-wizard-step2');
    await step2.waitFor({state: 'visible', timeout: 5_000});
    await waitForSettled(step2, 20_000);
    await page.keyboard.press('Escape');

    const fileRow = step2.locator('tr[data-row-id]').filter({hasText: file.name}).first();
    if (!(await fileRow.isVisible({timeout: 3_000}).catch(() => false))) {
        const brokerHeaders = step2.locator('.rounded-lg > button');
        const count = await brokerHeaders.count();
        for (let i = 0; i < count; i++) {
            await brokerHeaders.nth(i).click();
            if (await fileRow.isVisible({timeout: 1_000}).catch(() => false)) break;
        }
    }
    await expect(fileRow).toBeVisible({timeout: 5_000});

    // The file uploaded in step 1 arrives PRE-SELECTED in step 2 ("Files from Step 1 are
    // pre-selected"). Ensure it is checked without clicking blind — a blind click would
    // DESELECT it (rule 13: on a toggle, assert the end state, never click blind).
    const checkbox = fileRow.locator('td.td-select button.checkbox-btn');
    await checkbox.scrollIntoViewIfNeeded();
    await page.keyboard.press('Escape');
    if ((await checkbox.getAttribute('data-state')) !== 'checked') {
        await checkbox.click();
    }
    await expect(checkbox).toHaveAttribute('data-state', 'checked', {timeout: 3_000});
    await expect(page.getByTestId('import-wizard-parse')).toBeEnabled({timeout: 3_000});

    // Step 3: parse and wait for the verdict.
    await page.getByTestId('import-wizard-parse').click();
    await page.getByTestId('import-wizard-step3').waitFor({state: 'visible', timeout: 10_000});
    await waitForParseVerdict(page);
    return file.name;
}

/** Click a step's Continue-like button only if that (conditional) step is on screen. */
async function skipStepIfPresent(page: Page, testid: string) {
    const button = page.getByTestId(testid);
    if (await button.isVisible({timeout: 1_500}).catch(() => false)) {
        await button.click();
        await expect(button).toHaveCount(0, {timeout: 5_000});
    }
}

/** From a freshly opened wizard, parse then cross whichever conditional steps this parse raised into review. */
async function walkToReview(page: Page) {
    await reachAnalyze(page);
    await page.getByTestId('import-wizard-continue').click();
    for (const testid of ['import-wizard-assets-continue', 'import-wizard-fix-continue', 'import-wizard-duplicates-continue']) {
        await skipStepIfPresent(page, testid);
    }
    const step4 = page.getByTestId('import-wizard-step4');
    await step4.waitFor({state: 'visible', timeout: 5_000});
    await waitForSettled(step4, 20_000);
    return step4;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Import Wizard — analyze step', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
        await openImportWizard(page);
    });

    test('A1: parsing reaches an "ok" verdict with a done row and the aggregate summary', async ({page}) => {
        await reachAnalyze(page);

        const step3 = page.getByTestId('import-wizard-step3');
        await expect(step3).toHaveAttribute('data-parse-state', 'ok');
        // Exactly the one file we selected produced a row.
        await expect(step3.locator('tbody tr[data-row-id]')).toHaveCount(1);
        // The aggregate actions only render once parsing is done.
        await expect(page.getByTestId('import-wizard-view-all')).toBeVisible();
        await expect(page.getByTestId('import-wizard-reparse')).toBeVisible();
    });

    test('A2: double-clicking a parsed file opens (and closes) its detail modal', async ({page}) => {
        await reachAnalyze(page);

        const row = page.getByTestId('import-wizard-step3').locator('tbody tr[data-row-id]').first();
        await row.dblclick();
        await expect(page.getByTestId('parse-detail-modal')).toBeVisible({timeout: 5_000});

        await page.getByTestId('parse-detail-close').click();
        await expect(page.getByTestId('parse-detail-modal')).toHaveCount(0, {timeout: 5_000});
    });

    test('A3: "View all" opens the aggregate detail modal', async ({page}) => {
        await reachAnalyze(page);

        await page.getByTestId('import-wizard-view-all').click();
        await expect(page.getByTestId('parse-detail-modal')).toBeVisible({timeout: 5_000});

        await page.getByTestId('parse-detail-close').click();
        await expect(page.getByTestId('parse-detail-modal')).toHaveCount(0, {timeout: 5_000});
    });

    test('A4: re-parse re-runs the analysis and settles back to "ok"', async ({page}) => {
        await reachAnalyze(page);

        await page.getByTestId('import-wizard-reparse').click();
        // handleReparse resets every result to pending then re-parses; wait for the fresh verdict.
        await waitForParseVerdict(page);
        await expect(page.getByTestId('import-wizard-step3')).toHaveAttribute('data-parse-state', 'ok');
    });

    test('A5: Back walks analyze → select → upload, then Next returns to select', async ({page}) => {
        await reachAnalyze(page);

        await page.getByTestId('import-wizard-back').click();
        await expect(page.getByTestId('import-wizard-step2')).toBeVisible({timeout: 5_000});

        await page.getByTestId('import-wizard-back').click();
        await expect(page.getByTestId('import-wizard-step1')).toBeVisible({timeout: 5_000});

        // Forward again: the upload step is empty, so Next advances straight to select.
        await page.getByTestId('import-wizard-next').click();
        await expect(page.getByTestId('import-wizard-step2')).toBeVisible({timeout: 5_000});
    });
});

test.describe('Import Wizard — review step', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
        await openImportWizard(page);
    });

    test('R1: the review step lists transactions and the selection toolbar toggles the count', async ({page}) => {
        const step4 = await walkToReview(page);

        // The preview table has rows to review.
        await expect(step4.locator('tbody tr[data-row-id]').first()).toBeVisible({timeout: 5_000});

        // Deselect all → the published selected count drops to zero and Import is blocked.
        await page.getByTestId('import-wizard-deselect-all').click();
        await expect(step4).toHaveAttribute('data-selected-count', '0', {timeout: 5_000});
        await expect(page.getByTestId('import-wizard-import')).toBeDisabled();

        // Select the visible page → the count climbs back above zero.
        await page.getByTestId('import-wizard-select-visible').click();
        await expect(step4).toHaveAttribute('data-selected-count', /^[1-9][0-9]*$/, {timeout: 5_000});
    });

    test('R2: Select all then Deselect all move the count to the total and back to zero', async ({page}) => {
        const step4 = await walkToReview(page);

        // Select all: the selectable total is what ends up selected (both counts move together
        // because a resolved-away duplicate stops counting once it is selected), so poll the
        // pair until they agree on a non-zero value rather than reading each attribute once.
        await page.getByTestId('import-wizard-select-all').click();
        await expect
            .poll(
                async () => {
                    const sel = await step4.getAttribute('data-selected-count');
                    const tot = await step4.getAttribute('data-total-count');
                    return sel !== '0' && sel === tot;
                },
                {timeout: 5_000},
            )
            .toBe(true);

        await page.getByTestId('import-wizard-deselect-all').click();
        await expect(step4).toHaveAttribute('data-selected-count', '0', {timeout: 5_000});
    });

    test('R3: closing at review prompts the discard guard and tears the wizard down on confirm', async ({page}) => {
        await walkToReview(page);

        await page.getByTestId('import-wizard-close').click();
        await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: 5_000});
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 5_000});
    });
});
