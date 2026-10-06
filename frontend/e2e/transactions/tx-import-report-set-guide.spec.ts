/**
 * Import guide — its step on "Align with the bank" (report sets, phase C3 of the Danske Bank
 * workstream, issue 26; scenario R9 of the plan's C3.0).
 *
 * The import guide follows the wizard by itself: a wizard step `X` brings the guide step
 * `import.X`, started by the wizard when no guide is active and the step is due. The new step
 * `gapFix` therefore brings `import.gapFix` — between `import.review` and `import.bulk` —
 * anchored on the step's Continue (`import.action.gapFix` on
 * `import-wizard-gapfix-continue`). This spec proves the anchoring on a real walk, on desktop and
 * on mobile: the action runs both projects, while `tx-import-report-set` runs on desktop only.
 *
 * The account. Onboarding progress is per user and a guide walk moves it, so the test registers a
 * disposable account (fixtures/onboarding-accounts.ts), takes it through the welcome, skips every
 * other flow, and completes over the API the import-guide steps before `import.gapFix`: only
 * `import.gapFix` and `import.bulk` are left due — read back, not inferred — so nothing competes
 * for the overlay and the walk meets no coachmark before the gap-fix step. The account owns its
 * broker, uploads the repository's synthetic Danske set, never saves, and afterEach deletes it
 * with its broker (which takes the broker's BRIM files along).
 *
 * The walk is R5's (tx-import-report-set.spec.ts), helpers copied rather than imported from a
 * spec file: both exports in one step-1 session → one complete set → its combined file parsed →
 * notices read past → every charge kept → review → only the 5 cash rows of the history selected
 * (nothing to resolve, nothing created) → Import. On a fresh broker the opening deposit of
 * 2699.50 EUR is always proposed, so the step always opens.
 */

import {expect, test, type Locator, type Page, type Response} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';
import path from 'path';
import {fileURLToPath} from 'url';

const API = '/api/v1';
const UPLOAD_PATH = `${API}/brokers/import/upload`;
const SPEC_DIR = path.dirname(fileURLToPath(import.meta.url));
const SAMPLES = path.resolve(SPEC_DIR, '../../../backend/app/services/brim_providers/sample_reports');
const CUSTODY_XLSX = path.join(SAMPLES, 'danske_bank-custody.xlsx');
const CASH_CSV = path.join(SAMPLES, 'danske_bank-cash.csv');
const DANSKE = 'broker_danske_bank';
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** The facts of the main set on a fresh broker (backend phase B). */
const MAIN_SET = {trades: 11, cashRowsInHistory: 5} as const;

/** Budget of the first C3 element: before the implementation it is the one that fails. */
const C3_FIRST = 8_000;

type UploadedInfo = {file_id: string; filename: string; batch_id?: string | null};
type ImportGuideProgress = {current_version: number; steps?: Array<{step_id: string; status: string; version: number; current_version: number}>};

// ---------------------------------------------------------------------------
// The account and what it owns
// ---------------------------------------------------------------------------

async function readImportGuide(page: Page): Promise<ImportGuideProgress> {
    const response = await page.request.get(`${API}/settings/onboarding`);
    expect(response.ok(), `read the onboarding progress: HTTP ${response.status()}`).toBe(true);
    const flows = ((await response.json()) as {flows: Array<ImportGuideProgress & {flow: string}>}).flows;
    const flow = flows.find((candidate) => candidate.flow === 'import_guide');
    if (!flow) throw new Error('the account has no progress for import_guide');
    return flow;
}

/**
 * Complete over the API every import-guide step before `import.gapFix`, then read back that only
 * `import.gapFix` and `import.bulk` are due. The step list comes from the server: the guide's own
 * order, never a copy of it.
 */
async function completeImportStepsBeforeGapFix(page: Page): Promise<void> {
    const flow = await readImportGuide(page);
    const stepIds = (flow.steps ?? []).map((step) => step.step_id);
    const gapFixAt = stepIds.indexOf('import.gapFix');
    expect(gapFixAt, `the import guide has the step import.gapFix (phase C3); its steps: ${JSON.stringify(stepIds)}`).toBeGreaterThan(0);
    expect(stepIds.slice(gapFixAt - 1), 'import.gapFix sits between the review and the editor hand-off').toEqual(['import.review', 'import.gapFix', 'import.bulk']);
    for (const stepId of stepIds.slice(0, gapFixAt)) {
        const completed = await page.request.post(`${API}/settings/onboarding/import_guide/steps/${stepId}/complete`, {data: {expected_version: flow.current_version}});
        expect(completed.ok(), `complete ${stepId}: HTTP ${completed.status()} ${await completed.text()}`).toBe(true);
    }
    const due = ((await readImportGuide(page)).steps ?? []).filter((step) => step.status === 'pending' || step.version < step.current_version).map((step) => step.step_id);
    expect(due, 'only the gap-fix step and the editor hand-off are left to show').toEqual(['import.gapFix', 'import.bulk']);
}

/** A broker of the account, with no opening date (the synthetic set is dated 2019–2020); its id is recorded for cleanup first. */
async function createOwnedBroker(page: Page, tag: string, ownedBrokerIds: number[]): Promise<number> {
    const name = `r9-${tag}-${uniqueSuffix()}`;
    const response = await page.request.post(`${API}/brokers`, {data: [{name, allow_cash_overdraft: true}]});
    expect(response.ok(), `create owned broker: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null}>};
    const created = results.find((result) => result.name === name);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`Owned broker "${name}" was not created: ${JSON.stringify(results)}`);
    ownedBrokerIds.push(created.broker_id);
    return created.broker_id;
}

// ---------------------------------------------------------------------------
// The walk (copied from tx-import-report-set.spec.ts)
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

async function openImportWizard(page: Page) {
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: 8_000});
    const step1 = page.getByTestId('import-wizard-step1');
    await step1.waitFor({state: 'visible', timeout: 5_000});
    await waitForSettled(step1, 15_000);
}

function currentStep(page: Page): Locator {
    return page.getByTestId('import-wizard-stepper').locator('[aria-current="step"]');
}

/** The upload responses `action` produces on this page: exactly `expected` of them, each a 200. */
async function uploadsDuring(page: Page, expected: number, action: () => Promise<void>): Promise<UploadedInfo[]> {
    const replies: Array<Promise<{status: number; body: string}>> = [];
    const listener = (response: Response) => {
        if (response.request().method() === 'POST' && new URL(response.url()).pathname === UPLOAD_PATH) replies.push(response.text().then((body) => ({status: response.status(), body})));
    };
    // Armed before the action: a response is an edge, not a state.
    page.on('response', listener);
    try {
        await action();
        await expect.poll(() => replies.length, {message: `${expected} upload response(s) from one action`, timeout: 15_000}).toBe(expected);
    } finally {
        page.off('response', listener);
    }
    const settled = await Promise.all(replies);
    for (const {status, body} of settled) expect(status, `POST ${UPLOAD_PATH}: ${body}`).toBe(200);
    return settled.map(({body}) => JSON.parse(body) as UploadedInfo);
}

/** Drop files on step 1, unfolding the drop zone first when it has folded (asked, not clicked blind). */
async function dropFiles(page: Page, files: string[]) {
    const step1 = page.getByTestId('import-wizard-step1');
    const uploader = step1.getByTestId('file-uploader');
    const uploadMore = page.getByTestId('import-wizard-upload-more');
    await expect(uploader.or(uploadMore)).toBeVisible({timeout: 5_000});
    if (!(await uploader.isVisible())) await uploadMore.click();
    await expect(uploader).toBeVisible({timeout: 5_000});
    await uploader.getByTestId('file-input').setInputFiles(files);
}

async function assignOwnedBroker(page: Page, brokerId: number) {
    await optionsClosed(page);
    await page.getByTestId('import-wizard-step1-broker-select').getByRole('combobox').click();
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option, `owned broker ${brokerId} must be offered by the "assign all" select`).toBeVisible({timeout: 8_000});
    await option.click();
    await optionsClosed(page);
    await expect(page.getByTestId('import-wizard-next')).toBeEnabled({timeout: 5_000});
}

/** Both exports in one session → the complete set → its combined parse → the corrections → the review. */
async function walkMainSetToReview(page: Page, brokerId: number): Promise<Locator> {
    await dropFiles(page, [CUSTODY_XLSX, CASH_CSV]);
    await expect(page.getByTestId('import-wizard-step1').locator('tbody tr[data-row-id]')).toHaveCount(2);
    await assignOwnedBroker(page, brokerId);
    const uploaded = await uploadsDuring(page, 2, async () => {
        await page.getByTestId('import-wizard-next').click();
        await expect(page.getByTestId('import-wizard-step2')).toBeVisible({timeout: 30_000});
    });
    const batches = [...new Set(uploaded.map((file) => file.batch_id))];
    expect(batches, 'the two exports of one step-1 session share its batch').toHaveLength(1);
    const batchId = batches[0];
    expect(typeof batchId === 'string' && UUID_PATTERN.test(batchId), `batch_id ${JSON.stringify(batchId)} must be a UUID`).toBe(true);

    const step2 = page.getByTestId('import-wizard-step2');
    await waitForSettled(step2, 20_000);
    const card = step2.locator(`[data-testid="report-set-card"][data-set-key="set:${brokerId}:${DANSKE}:${batchId}"]`);
    await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
    await expect(card).toHaveAttribute('data-selected', 'all');
    const parse = page.getByTestId('import-wizard-parse');
    await expect(parse).toBeEnabled({timeout: 5_000});
    await parse.click();
    await expect(page.getByTestId('import-wizard-step3')).toBeVisible({timeout: 10_000});
    await waitForParseVerdict(page, 60_000);

    await page.getByTestId('import-wizard-continue').click();
    const confirm = page.getByTestId('import-wizard-warning-confirm');
    await expect(confirm).toBeVisible({timeout: 5_000});
    await confirm.click();
    await expect(currentStep(page)).toHaveAttribute('data-step-id', 'fix', {timeout: 30_000});
    await expect(page.getByTestId('fix-step-row')).toHaveCount(MAIN_SET.trades, {timeout: 10_000});
    await page.getByTestId('fix-step-accept-all').click();
    await expect(page.locator('[data-testid="fix-step-row"][data-decision="pending"]')).toHaveCount(0, {timeout: 10_000});
    await page.getByTestId('import-wizard-fix-continue').click();
    await expect(currentStep(page)).toHaveAttribute('data-step-id', 'review', {timeout: 30_000});
    const step4 = page.getByTestId('import-wizard-step4');
    await waitForSettled(step4, 30_000);
    return step4;
}

/** Only the review rows without an asset stay selected: Import needs no resolution, whatever the lane holds. */
async function selectOnlyCashRows(page: Page, step4: Locator) {
    await page.getByTestId('import-wizard-deselect-all').click();
    await expect(step4).toHaveAttribute('data-selected-count', '0', {timeout: 5_000});
    const trigger = step4.getByTestId('col-filter-trigger-asset');
    await trigger.click();
    const filter = step4.getByTestId('dt-header-asset').getByTestId('column-filter');
    await expect(filter).toBeVisible({timeout: 5_000});
    const noAsset = filter.getByTestId('filter-enum-option-__null__');
    await expect(noAsset).toHaveAttribute('data-checked', 'false');
    await noAsset.click();
    await expect(noAsset).toHaveAttribute('data-checked', 'true');
    await trigger.click();
    await expect(filter).toBeHidden({timeout: 5_000});
    await expect(step4.locator('tbody tr[data-row-id]')).toHaveCount(MAIN_SET.cashRowsInHistory, {timeout: 5_000});
    await page.getByTestId('import-wizard-select-visible').click();
    await expect(step4).toHaveAttribute('data-selected-count', String(MAIN_SET.cashRowsInHistory), {timeout: 5_000});
    await expect(page.getByTestId('import-wizard-import')).toBeEnabled({timeout: 15_000});
}

// ---------------------------------------------------------------------------
// Test
// ---------------------------------------------------------------------------

test.describe('Import guide — the gap-fix step (R9)', () => {
    let user: DisposableUser | undefined;
    let ownedBrokerIds: number[] = [];

    test.beforeEach(() => {
        user = undefined;
        ownedBrokerIds = [];
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the assertion error
    // it follows. The page leaves first, so the wizard does not react while its files go away.
    test.afterEach(async ({page, request}) => {
        if (!user) return;
        await page.goto('about:blank');
        await deleteDisposableUser(request, user, ownedBrokerIds);
    });

    test('R9: the import guide shows its gap-fix step anchored on the step’s Continue', async ({page, request}, testInfo) => {
        test.setTimeout(180_000);
        user = await registerDisposableUser(request, `r9_${testInfo.project.name}`);
        await prepareOnboardingAccount(page, user, ['import_guide']);
        await completeImportStepsBeforeGapFix(page);
        const brokerId = await createOwnedBroker(page, testInfo.project.name, ownedBrokerIds);

        // A full load: the app reads the progress just written.
        await goToTransactions(page);
        await openImportWizard(page);
        const step4 = await walkMainSetToReview(page, brokerId);
        await selectOnlyCashRows(page, step4);
        await page.getByTestId('import-wizard-import').click();

        await expect(currentStep(page), 'Import on a report set opens the gap-fix step').toHaveAttribute('data-step-id', 'gapFix', {timeout: C3_FIRST});
        const continueButton = page.getByTestId('import-wizard-gapfix-continue');
        await expect(continueButton).toBeVisible({timeout: 5_000});

        const coachmark = page.getByTestId('onboarding-coachmark');
        await expect(coachmark, 'the wizard starts the guide step of its current step').toHaveAttribute('data-step-id', 'import.gapFix', {timeout: 15_000});
        await expect(coachmark).toHaveAttribute('data-guide-state', 'anchored', {timeout: 15_000});
        await expect(coachmark).toHaveAttribute('data-geometry-state', 'stable', {timeout: 15_000});
        await expect(coachmark).toHaveAttribute('data-target-stable', 'true');
        await expect(coachmark).toHaveAttribute('data-pointer', 'cursor');
        await expect(coachmark).toHaveAttribute('data-panel-placement', 'top');
        await expect(page.getByTestId('onboarding-coachmark-pointer')).toBeVisible();
        // Anchored, not merely co-located: the coachmark stamps its description on the exact element it targets.
        await expect(continueButton).toHaveAttribute('aria-describedby', 'onboarding-coachmark-description');
    });
});
