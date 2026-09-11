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
 * review and never click Import), and it carries a unique name so it is invisible to other
 * specs' name-filtered selections. The upload response's owned file id is recorded and deleted
 * in afterEach; cleanup never infers ownership from a global before/after delta.
 *
 * State handles added to the product for this spec (they publish states a user also benefits
 * from — see frontend-testing.instructions.md rule 4):
 *   import-wizard-view-all / import-wizard-reparse   — analyze aggregate actions
 *   import-wizard-select-all / import-wizard-deselect-all — review selection toolbar
 *   parse-detail-close                                — ParseDetailModal close button
 *   data-selected-count / data-total-count on step4   — the review selection count
 */

import {expect, test as base, type Page, type Request} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {uniqueSuffix} from '../fixtures/unique';
import {TEST_USER} from '../fixtures/test-users';

const test = base;
test.setTimeout(90_000);

const API = '/api/v1';
const ownedFileIds = new WeakMap<Page, Set<string>>();

function rememberOwnedFile(page: Page, fileId: string): void {
    const ids = ownedFileIds.get(page) ?? new Set<string>();
    ids.add(fileId);
    ownedFileIds.set(page, ids);
}

async function cleanupOwnedFiles(page: Page): Promise<void> {
    const ids = ownedFileIds.get(page) ?? new Set<string>();
    ownedFileIds.delete(page);
    if (ids.size === 0) return;

    // Unmount the wizard before removing files it may still have open.
    await page.goto('about:blank');
    const failures: string[] = [];
    for (const fileId of ids) {
        try {
            const response = await page.request.delete(`${API}/brokers/import/files/${fileId}`);
            if (!response.ok()) {
                failures.push(`${fileId}: HTTP ${response.status()} ${await response.text()}`);
                continue;
            }
            const result = (await response.json()) as {success?: boolean; file_id?: string};
            if (result.success !== true || result.file_id !== fileId) {
                failures.push(`${fileId}: ${JSON.stringify(result)}`);
            }
        } catch (error) {
            failures.push(`${fileId}: ${String(error)}`);
        }
    }
    expect(failures, 'Cleanup must delete every upload id owned by this test').toEqual([]);
}

test.afterEach(async ({page}) => {
    await cleanupOwnedFiles(page);
});

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
async function reachAnalyze(page: Page, onGuideStep?: (stepId: string) => Promise<void>): Promise<string> {
    const file = csv(uniqueSuffix());
    await onGuideStep?.('import.upload');

    // Step 1: upload this test's own file, assign a broker, advance.
    const input = page.getByTestId('import-wizard-step1').locator('[data-testid="file-input"]');
    await input.setInputFiles(file);
    await expect(page.getByTestId('import-wizard-step1').locator('tbody tr[data-row-id]')).toHaveCount(1);
    await assignBroker(page);
    await expect(page.getByTestId('import-wizard-next')).toBeEnabled({timeout: 5_000});
    const uploadResponsePromise = page.waitForResponse((response) => {
        const request = response.request();
        return request.method() === 'POST' && new URL(response.url()).pathname === `${API}/brokers/import/upload`;
    });
    await page.getByTestId('import-wizard-next').click();
    const uploadResponse = await uploadResponsePromise;
    expect(uploadResponse.ok(), `Owned upload ${file.name} failed with HTTP ${uploadResponse.status()}`).toBe(true);
    const uploaded = (await uploadResponse.json()) as {file_id?: string};
    if (!uploaded.file_id) throw new Error(`Owned upload ${file.name} returned no file_id`);
    rememberOwnedFile(page, uploaded.file_id);

    // Step 2: the just-uploaded file is listed for the chosen broker — select it and parse.
    const step2 = page.getByTestId('import-wizard-step2');
    await step2.waitFor({state: 'visible', timeout: 5_000});
    await waitForSettled(step2, 20_000);
    await onGuideStep?.('import.select');

    const fileRow = step2.locator('tr[data-row-id]').filter({hasText: file.name}).first();
    await expect(fileRow, `Owned upload ${file.name} must be visible in its assigned broker panel`).toBeVisible({timeout: 10_000});

    // The file uploaded in step 1 arrives PRE-SELECTED in step 2 ("Files from Step 1 are
    // pre-selected"). Ensure it is checked without clicking blind — a blind click would
    // DESELECT it (rule 13: on a toggle, assert the end state, never click blind).
    const checkbox = fileRow.locator('button[data-state]').first();
    await checkbox.scrollIntoViewIfNeeded();
    if ((await checkbox.getAttribute('data-state')) !== 'checked') {
        await checkbox.click();
    }
    await expect(checkbox).toHaveAttribute('data-state', 'checked', {timeout: 3_000});
    await expect(page.getByTestId('import-wizard-parse')).toBeEnabled({timeout: 3_000});

    // Step 3: parse and wait for the verdict.
    await page.getByTestId('import-wizard-parse').click();
    await page.getByTestId('import-wizard-step3').waitFor({state: 'visible', timeout: 10_000});
    await waitForParseVerdict(page);
    await onGuideStep?.('import.analyze');
    return file.name;
}

const CONDITIONAL_STEPS = {
    assets: {container: 'import-wizard-step-assets', advance: 'import-wizard-assets-continue'},
    fix: {container: 'import-wizard-step-fix', advance: 'import-wizard-fix-continue'},
    duplicates: {container: 'import-wizard-step-duplicates', advance: 'import-wizard-duplicates-continue'},
} as const;

/**
 * Follow the stepper's actual semantic state instead of probing optional DOM nodes.
 * A conditional branch is exercised only when the parser really emitted it; this
 * helper never fabricates assets/fix/duplicates merely to make the guide advance.
 */
async function advanceConditionalStepsToReview(page: Page, onGuideStep?: (stepId: string) => Promise<void>) {
    const currentStep = page.getByTestId('import-wizard-stepper').locator('[aria-current="step"]');
    for (let hop = 0; hop <= Object.keys(CONDITIONAL_STEPS).length; hop++) {
        await expect(currentStep).toHaveAttribute('data-step-id', /^(assets|fix|duplicates|review)$/, {timeout: 10_000});
        const stepId = await currentStep.getAttribute('data-step-id');
        if (stepId === 'review') return;

        if (!stepId || !(stepId in CONDITIONAL_STEPS)) {
            throw new Error(`Import wizard reached unsupported semantic step ${String(stepId)}`);
        }
        const step = CONDITIONAL_STEPS[stepId as keyof typeof CONDITIONAL_STEPS];
        await expect(page.getByTestId(step.container)).toBeVisible({timeout: 5_000});
        await onGuideStep?.(`import.${stepId}`);
        await page.getByTestId(step.advance).click();
        await expect(currentStep).not.toHaveAttribute('data-step-id', stepId, {timeout: 5_000});
    }
    throw new Error('Import wizard did not reach review after every emitted conditional step');
}

/** From a freshly opened wizard, parse then cross whichever conditional steps this parse raised into review. */
async function walkToReview(page: Page) {
    await reachAnalyze(page);
    await page.getByTestId('import-wizard-continue').click();
    await advanceConditionalStepsToReview(page);
    const step4 = page.getByTestId('import-wizard-step4');
    await step4.waitFor({state: 'visible', timeout: 5_000});
    await waitForSettled(step4, 20_000);
    return step4;
}

/**
 * Import wizard steps use the wizard's own navigation. The shared guide chrome is
 * therefore exactly permanent Skip + X: no legacy Pause, Back, progress, or duplicate
 * Next. Only `import.bulk` gains the guide's final Next/Finish action.
 */
async function expectImportGuideChrome(page: Page, stepId: string, options: {finish?: boolean} = {}) {
    const coachmark = page.getByTestId('onboarding-coachmark');
    await expect(coachmark).toHaveAttribute('data-step-id', stepId, {timeout: 10_000});
    await expect(coachmark).toHaveAttribute('data-guide-state', 'anchored', {timeout: 10_000});
    await expect(page.getByTestId('onboarding-coachmark-skip')).toBeVisible();
    await expect(page.getByTestId('onboarding-coachmark-close')).toBeVisible();
    await expect(page.getByTestId('onboarding-coachmark-pause')).toHaveCount(0);
    await expect(page.getByTestId('onboarding-coachmark-back')).toHaveCount(0);
    await expect(page.getByTestId('onboarding-coachmark-progress')).toHaveCount(0);
    if (options.finish) {
        await expect(page.getByTestId('onboarding-coachmark-next')).toBeVisible();
    } else {
        await expect(page.getByTestId('onboarding-coachmark-next')).toHaveCount(0);
    }
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

// ---------------------------------------------------------------------------
// Onboarding — the import guide's real wizard → Bulk handoff
// ---------------------------------------------------------------------------
//
// TEST_USER is a canonical, grandfathered account (see populate_mock_data's
// `_grandfather_onboarding_for_test_users`): every onboarding flow already reads
// `completed`, so nothing here is ever *forced*. The guide is armed the same way a
// real user would revisit it — the "Replay" control on Settings' Preferences tab
// (`onboarding-replay-import_guide`), which only writes a client-side sessionStorage
// flag (`onboardingGuide.startImportReplay`). No onboarding endpoint is called to arm
// it, and each Playwright test owns an isolated browser context, so this never
// leaks to a sibling test sharing the same account.
//
// Manual-only seam, stated rather than faked: this suite's owned race-free CSV has no
// asset column or duplicate rows, so it normally emits no assets/fix/duplicates step.
// `advanceConditionalStepsToReview()` follows and verifies any conditional step the
// real parser does emit, but deliberately does not manufacture one. Dedicated
// parser-owned fixtures plus the duplicate-bounce path remain in the manual runbook.
test.describe('Import Wizard — onboarding guide handoff', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    /**
     * Arms the import guide replay the same way a real user would revisit it — the
     * "Replay" control on Settings' Preferences tab — never a fabricated internal flag.
     * Shared verbatim by G1 and G2, both of which need the guide armed before they ever
     * touch the wizard.
     */
    async function armImportGuideReplay(page: Page) {
        await navigateTo(page, '/settings');
        await page.getByTestId('settings-tab-preferences').click();
        await expect(page.getByTestId('onboarding-flow-import_guide')).toBeVisible({timeout: 10_000});
        await page.getByTestId('onboarding-replay-import_guide').click();
        await expect(page.getByTestId('onboarding-flow-import_guide-armed')).toBeVisible({timeout: 5_000});
    }

    test('G1: terminal import replay tracks the wizard, suspends for ParseDetail, and exits without committing or rewriting status', async ({page}) => {
        await armImportGuideReplay(page);

        const commitRequests: string[] = [];
        const terminalGuideRequests: string[] = [];
        const recordRequest = (req: Request) => {
            if (req.method() !== 'POST') return;
            const path = new URL(req.url()).pathname;
            if (path === '/api/v1/transactions/commit') commitRequests.push(req.url());
            if (/^\/api\/v1\/settings\/onboarding\/import_guide\/(?:complete|skip)$/.test(path)) terminalGuideRequests.push(path);
        };
        page.on('request', recordRequest);

        try {
            await goToTransactions(page);
            await openImportWizard(page);

            const coachmark = page.getByTestId('onboarding-coachmark');
            // Never send Escape while the guide is under test: X is the approved
            // suspension gesture, and Escape deliberately routes through the same path.
            const fileName = await reachAnalyze(page, (stepId) => expectImportGuideChrome(page, stepId));

            // TransactionBulk + ImportWizard already occupy the two supported modal
            // depths. ParseDetail is depth 3, so its presence intentionally suspends
            // the coachmark until that third modal closes.
            const row = page.getByTestId('import-wizard-step3').locator('tbody tr[data-row-id]').filter({hasText: fileName}).first();
            await row.dblclick();
            await expect(page.getByTestId('parse-detail-modal')).toBeVisible({timeout: 5_000});
            await expect(coachmark).toHaveCount(0, {timeout: 5_000});
            await page.getByTestId('parse-detail-close').click();
            await expect(page.getByTestId('parse-detail-modal')).toHaveCount(0, {timeout: 5_000});
            // Returning to supported depth 2 restores the same anchored semantic step.
            await expectImportGuideChrome(page, 'import.analyze');

            await page.getByTestId('import-wizard-continue').click();
            await advanceConditionalStepsToReview(page, (stepId) => expectImportGuideChrome(page, stepId));
            const step4 = page.getByTestId('import-wizard-step4');
            await step4.waitFor({state: 'visible', timeout: 5_000});
            await waitForSettled(step4, 20_000);
            await expectImportGuideChrome(page, 'import.review');

            await expect(page.getByTestId('import-wizard-import')).toBeEnabled({timeout: 5_000});
            expect(commitRequests, 'Reaching review must not commit anything').toEqual([]);
            await page.getByTestId('import-wizard-import').click();

            // The wizard hands off and closes; the Bulk modal underneath takes over.
            await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 10_000});
            const bulkRoot = page.getByTestId('tx-bulk-modal-root');
            await expect(bulkRoot).toBeVisible({timeout: 10_000});
            await waitForSettled(bulkRoot, 20_000);
            await expectImportGuideChrome(page, 'import.bulk', {finish: true});

            const commitButton = page.getByTestId('tx-bulk-commit');
            await expect(commitButton).toBeVisible();
            // Anchored, not merely co-located: the coachmark's effect stamps its own
            // description id onto the exact element it targets.
            await expect(commitButton).toHaveAttribute('aria-describedby', 'onboarding-coachmark-description');

            expect(commitRequests, 'No commit must happen before the user explicitly clicks Save All').toEqual([]);
            const draftRows = page.getByTestId('tx-bulk-row-label');
            await expect.poll(() => draftRows.count(), {timeout: 5_000}).toBeGreaterThan(0);
            const draftRowsBefore = await draftRows.count();
            expect(terminalGuideRequests, 'Wizard navigation and handoff must not rewrite terminal replay status').toEqual([]);

            // Never click Save All — Finish exits this session replay only.
            await page.getByTestId('onboarding-coachmark-next').click();
            await expect(coachmark).toHaveCount(0, {timeout: 5_000});
            await expect(bulkRoot).toBeVisible();
            await expect(draftRows).toHaveCount(draftRowsBefore);
            expect(terminalGuideRequests, 'Replay Finish must call neither onboarding complete nor skip').toEqual([]);
            expect(commitRequests, 'Exiting replay with Finish must never commit').toEqual([]);
        } finally {
            page.off('request', recordRequest);
            // The browser context owns the in-memory draft and is torn down after this
            // test. No Transaction row was written, so server-side cleanup is empty.
        }
    });

    test('G2: closing the Bulk handoff without Save All suspends the guide and resets it to import.upload on the next open', async ({page}) => {
        // Same real owned-CSV corridor as G1 (armImportGuideReplay, then upload -> assign
        // -> select -> parse -> review -> handoff), walked without G1's nested-modal
        // detour: this test is about what happens when the handoff *closes*, not about
        // re-proving the per-step tracking G1 already covers. Never send Escape anywhere
        // in this walk — it is the guide's approved suspension gesture and would end
        // the test before it reaches the handoff under test.
        await armImportGuideReplay(page);

        const commitRequests: string[] = [];
        const terminalGuideRequests: string[] = [];
        const recordRequest = (req: Request) => {
            if (req.method() !== 'POST') return;
            const path = new URL(req.url()).pathname;
            if (path === '/api/v1/transactions/commit') commitRequests.push(req.url());
            if (/^\/api\/v1\/settings\/onboarding\/import_guide\/(?:complete|skip)$/.test(path)) terminalGuideRequests.push(path);
        };
        page.on('request', recordRequest);

        try {
            await goToTransactions(page);
            await openImportWizard(page);

            const coachmark = page.getByTestId('onboarding-coachmark');
            await reachAnalyze(page, (stepId) => expectImportGuideChrome(page, stepId));

            await page.getByTestId('import-wizard-continue').click();
            await advanceConditionalStepsToReview(page, (stepId) => expectImportGuideChrome(page, stepId));
            const step4 = page.getByTestId('import-wizard-step4');
            await step4.waitFor({state: 'visible', timeout: 5_000});
            await waitForSettled(step4, 20_000);
            await expectImportGuideChrome(page, 'import.review');

            await expect(page.getByTestId('import-wizard-import')).toBeEnabled({timeout: 5_000});
            expect(commitRequests, 'Reaching review must not commit anything').toEqual([]);
            await page.getByTestId('import-wizard-import').click();

            // Bulk handoff: the wizard closes and the Bulk modal takes over the guide.
            await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 10_000});
            const bulkRoot = page.getByTestId('tx-bulk-modal-root');
            await expect(bulkRoot).toBeVisible({timeout: 10_000});
            await waitForSettled(bulkRoot, 20_000);
            await expectImportGuideChrome(page, 'import.bulk', {finish: true});
            await expect.poll(() => page.getByTestId('tx-bulk-row-label').count(), {timeout: 5_000}).toBeGreaterThan(0);

            // Never click guide Finish, never click Save All: close the handoff instead.
            // The draft carried rows in from import, so TransactionBulkModal's
            // requestClose()/hasUnsavedChanges() always opens the discard confirm here —
            // assert its presence rather than probing for it defensively.
            await page.getByTestId('tx-bulk-close').click();
            await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: 5_000});
            await page.getByTestId('confirm-modal-confirm').click();
            await expect(bulkRoot).toHaveCount(0, {timeout: 10_000});

            // TransactionBulkModal's isOpen effect calls onboardingGuide.suspend({resetImport:
            // true}) the moment it closes while the guide is on import.bulk — suspension,
            // not finish()/skip(), so the replay flag survives. Prove the coachmark is gone
            // now that its host (bulkRoot) is provably gone too (rule 17: an absence
            // assertion needs a presence barrier), and that nothing was committed.
            await expect(coachmark).toHaveCount(0, {timeout: 5_000});
            expect(commitRequests, 'Closing the handoff must never commit').toEqual([]);

            // Reopen Transactions -> Import Wizard. Still on /transactions — the Bulk
            // modal was an overlay on it, never a navigation — so re-opening the wizard
            // is enough to prove the realignment: suspend({resetImport: true}) reset the
            // persisted replay step back to import.upload, and ImportWizardModal's own
            // mount effect (startImportAt) re-activates the guide there because the
            // replay flag itself was never cleared (only finish()/skip() do that).
            await openImportWizard(page);
            await expectImportGuideChrome(page, 'import.upload');

            // X suspends only the guide: it must leave the wizard open, preserve the
            // replay token, and issue no terminal transition or transaction commit.
            await page.getByTestId('onboarding-coachmark-close').click();
            await expect(coachmark).toHaveCount(0, {timeout: 5_000});
            await expect(page.getByTestId('import-wizard-stepper')).toBeVisible();
            expect(commitRequests, 'Guide X must never commit').toEqual([]);
            expect(terminalGuideRequests, 'Guide X is suspension, never Finish or Skip').toEqual([]);

            // Nothing was uploaded on this second open, so closing it needs no confirm.
            await page.getByTestId('import-wizard-close').click();
            await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 5_000});

            // Closing the inner wizard returns to its still-open TransactionBulk
            // workspace. Reopen through that owned parent, not the page toolbar behind it.
            await expect(bulkRoot).toBeVisible();
            await bulkRoot.getByTestId('tx-bulk-import').click();
            await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: 8_000});
            await expectImportGuideChrome(page, 'import.upload');
            await page.getByTestId('import-wizard-close').click();
            await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 5_000});
            expect(commitRequests, 'Suspending and reopening the guide must never commit').toEqual([]);
            expect(terminalGuideRequests, 'Closing the handoff and guide X are suspension, never Finish or Skip').toEqual([]);
        } finally {
            page.off('request', recordRequest);
        }
    });
});
