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

import {expect, test as base, type APIRequestContext, type Page, type Request} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {uniqueSuffix} from '../fixtures/unique';
import {TEST_USER} from '../fixtures/test-users';

const test = base;
test.setTimeout(90_000);

const API = '/api/v1';
const TERMINAL_ONBOARDING_AT = '2026-01-01T00:00:00Z';
const TERMINAL_ONBOARDING_FLOW_STEPS = [
    {flow: 'welcome', steps: []},
    {
        flow: 'intro_tour',
        steps: ['intro.scene', 'intro.navigation', 'intro.dashboard', 'intro.transactions_nav', 'intro.brokers_nav', 'intro.fx_nav', 'intro.assets_nav', 'intro.tools_nav', 'intro.settings_nav'],
    },
    {flow: 'transactions_page_guide', steps: ['transactions.page.overview', 'transactions.page.add', 'transactions.page.import', 'transactions.page.columns']},
    {flow: 'transaction_create_guide', steps: ['transaction.create.basics', 'transaction.create.amounts', 'transaction.create.details', 'transaction.create.save']},
    {flow: 'transaction_bulk_guide', steps: ['transaction.bulk.workspace', 'transaction.bulk.validation', 'transaction.bulk.selection', 'transaction.bulk.save']},
    {flow: 'import_guide', steps: ['import.upload', 'import.select', 'import.analyze', 'import.assets', 'import.fix', 'import.duplicates', 'import.review', 'import.bulk']},
    {flow: 'broker_page_guide', steps: ['broker.page.overview', 'broker.page.currency', 'broker.page.views', 'broker.page.add']},
    {flow: 'broker_guide', steps: ['broker.overview', 'broker.plugin', 'broker.icon']},
    {flow: 'broker_detail_guide', steps: ['broker.detail.header', 'broker.detail.overview', 'broker.detail.positions', 'broker.detail.transactions', 'broker.detail.info']},
    {flow: 'fx_page_guide', steps: ['fx.page.overview', 'fx.page.filters', 'fx.page.sync', 'fx.page.add']},
    {flow: 'fx_guide', steps: ['fx.currencies', 'fx.providers']},
    {flow: 'fx_detail_guide', steps: ['fx.detail.header', 'fx.detail.provider', 'fx.detail.chart', 'fx.detail.editor']},
    {flow: 'asset_page_guide', steps: ['asset.page.overview', 'asset.page.filters', 'asset.page.sync', 'asset.page.add']},
    {flow: 'asset_guide', steps: ['asset.search', 'asset.identity', 'asset.provider']},
    {flow: 'asset_detail_guide', steps: ['asset.detail.header', 'asset.detail.chart', 'asset.detail.editor', 'asset.detail.metadata', 'asset.detail.risk']},
] as const;
const TERMINAL_ONBOARDING_PROGRESS = {
    flows: TERMINAL_ONBOARDING_FLOW_STEPS.map(({flow, steps}) => ({
        flow,
        status: 'completed',
        version: 1,
        current_version: 1,
        update_available: false,
        created_at: TERMINAL_ONBOARDING_AT,
        updated_at: TERMINAL_ONBOARDING_AT,
        completed_at: TERMINAL_ONBOARDING_AT,
        ...(steps.length > 0
            ? {
                  steps: steps.map((stepId) => ({
                      step_id: stepId,
                      status: 'completed',
                      version: 1,
                      current_version: 1,
                      update_available: false,
                      created_at: TERMINAL_ONBOARDING_AT,
                      updated_at: TERMINAL_ONBOARDING_AT,
                      completed_at: TERMINAL_ONBOARDING_AT,
                  })),
              }
            : {}),
    })),
} as const;
const ownedFileIds = new WeakMap<Page, Set<string>>();
type DisposableUser = {id: number; username: string; email: string; password: string};
type ImportScrollState = {
    initialWindowY: number;
    initialWizardScrollTop: number | null;
    windowEvents: number[];
    wizardScrollEvents: number[];
    scrollIntoViewTargets: string[];
};
type ImportScrollHarness = {
    state: ImportScrollState;
    originalScrollIntoView: typeof Element.prototype.scrollIntoView;
    onWindowScroll: () => void;
    onElementScroll: (event: Event) => void;
    observer: MutationObserver;
};
type CoachmarkGeometryHarness = {
    states: string[];
    observer: MutationObserver;
};
type ImportScrollWindow = Window & {
    __lfImportGuideScroll?: ImportScrollHarness;
    __lfCoachmarkGeometry?: CoachmarkGeometryHarness;
};

async function registerDisposableUser(request: APIRequestContext, tag: string): Promise<DisposableUser> {
    const suffix = uniqueSuffix();
    const user = {
        username: `import_guide_${tag}_${suffix}`,
        email: `import_guide_${tag}_${suffix}@example.com`,
        password: `Import9!_${suffix}`,
    };
    const response = await request.post(`${API}/auth/register`, {data: user});
    expect(response.status(), 'Disposable-account registration must be enabled; this spec never rewrites global settings').toBe(201);
    const created = (await response.json()) as {user: {id: number}};
    return {...user, id: created.user.id};
}

async function deleteDisposableUser(request: APIRequestContext, user: DisposableUser, brokerIds: readonly number[]): Promise<void> {
    const loggedIn = await request.post(`${API}/auth/login`, {
        data: {username: user.username, password: user.password},
    });
    expect(loggedIn.ok(), 'Cleanup must authenticate as the disposable account').toBe(true);
    const body = (await loggedIn.json()) as {user: {id: number}};
    expect(body.user.id, 'Cleanup must remain scoped to this test user').toBe(user.id);
    try {
        for (const brokerId of brokerIds) {
            const deleted = await request.delete(`${API}/brokers?ids=${brokerId}&force=true`);
            expect(deleted.ok(), `Cleanup must delete owned broker ${brokerId}`).toBe(true);
            const result = ((await deleted.json()) as {results: Array<{id: number; success: boolean}>}).results.find((candidate) => candidate.id === brokerId);
            expect(result?.success, `Cleanup must cascade-delete data for owned broker ${brokerId}`).toBe(true);
        }
    } finally {
        const removed = await request.delete(`${API}/auth/users/me`);
        expect(removed.ok(), 'Cleanup must delete the disposable onboarding account').toBe(true);
    }
}

async function prepareDisposableImportAccount(page: Page): Promise<void> {
    await expect(page).toHaveURL(/\/welcome(?:[/?#]|$)/, {timeout: 15_000});
    await expect(page.getByTestId('welcome-form')).toBeVisible({timeout: 10_000});
    await expect(page.getByTestId('welcome-continue')).toBeEnabled({timeout: 10_000});
    await page.getByTestId('welcome-continue').click();
    await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/, {timeout: 15_000});
    await expect(page.getByTestId('onboarding-intro-scene')).toHaveAttribute('data-state', 'intro-scene', {timeout: 10_000});

    const introSkip = page.waitForResponse((response) => new URL(response.url()).pathname === `${API}/settings/onboarding/intro_tour/skip` && response.request().method() === 'POST');
    await page.getByTestId('onboarding-intro-close').click();
    expect((await introSkip).ok(), 'Closing the owned intro must persist its terminal skip').toBe(true);
    await expect(page.getByTestId('onboarding-intro-scene')).toHaveCount(0, {timeout: 10_000});

    const progressResponse = await page.request.get(`${API}/settings/onboarding`);
    expect(progressResponse.ok(), `Owned onboarding setup failed (HTTP ${progressResponse.status()})`).toBe(true);
    const progress = (await progressResponse.json()) as {
        flows: Array<{flow: string; status: string; current_version: number}>;
    };
    for (const flow of progress.flows) {
        if (flow.flow === 'welcome' || flow.flow === 'intro_tour') continue;
        if (flow.status !== 'pending') continue;
        const skipped = await page.request.post(`${API}/settings/onboarding/${flow.flow}/skip`, {
            data: {expected_version: flow.current_version},
        });
        expect(skipped.ok(), `Disposable account could not skip ${flow.flow} (HTTP ${skipped.status()})`).toBe(true);
    }
}

async function createOwnedBroker(page: Page, tag: string): Promise<{id: number; name: string}> {
    const name = `import-guide-${tag}-${uniqueSuffix()}`;
    const response = await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2025-01-01'}]});
    expect(response.ok(), `Owned broker setup failed (HTTP ${response.status()})`).toBe(true);
    const body = (await response.json()) as {
        results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>;
    };
    const result = body.results.find((candidate) => candidate.name === name);
    if (!result?.success || typeof result.broker_id !== 'number') {
        throw new Error(`Owned broker setup returned no id for ${name}: ${result?.message ?? 'missing result'}`);
    }
    return {id: result.broker_id, name};
}

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

/**
 * Analyze/review specs exercise Import, not onboarding. Give their page-scoped
 * bootstrap a fully terminal final-contract view without mutating the canonical user's rows.
 */
async function installTerminalOnboardingProgress(page: Page): Promise<void> {
    await page.route(
        (url) => url.pathname === `${API}/settings/onboarding` && url.search === '',
        async (route) => {
            if (route.request().method() !== 'GET') {
                await route.continue();
                return;
            }
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                json: TERMINAL_ONBOARDING_PROGRESS,
            });
        },
    );
}

test.afterEach(async ({page}) => {
    await cleanupOwnedFiles(page);
});

async function installImportScrollObservation(page: Page): Promise<void> {
    await page.evaluate(() => {
        const host = window as ImportScrollWindow;
        if (host.__lfImportGuideScroll) throw new Error('Import guide scroll observation is already installed');

        const state: ImportScrollState = {
            initialWindowY: window.scrollY,
            initialWizardScrollTop: null,
            windowEvents: [],
            wizardScrollEvents: [],
            scrollIntoViewTargets: [],
        };
        const captureInitialWizardScroll = () => {
            if (state.initialWizardScrollTop !== null) return;
            const content = document.querySelector<HTMLElement>('[data-testid="import-wizard-content"]');
            if (content) state.initialWizardScrollTop = content.scrollTop;
        };
        const onWindowScroll = () => state.windowEvents.push(window.scrollY);
        const onElementScroll = (event: Event) => {
            const target = event.target;
            if (target instanceof HTMLElement && target.dataset.testid === 'import-wizard-content') {
                state.wizardScrollEvents.push(target.scrollTop);
            }
        };
        const observer = new MutationObserver(captureInitialWizardScroll);
        captureInitialWizardScroll();
        observer.observe(document.documentElement, {childList: true, subtree: true});

        const originalScrollIntoView = Element.prototype.scrollIntoView;
        Element.prototype.scrollIntoView = function (this: Element, arg?: boolean | ScrollIntoViewOptions): void {
            const element = this as HTMLElement;
            state.scrollIntoViewTargets.push(element.dataset.testid ?? element.id ?? element.tagName.toLowerCase());
            Reflect.apply(originalScrollIntoView, this, arg === undefined ? [] : [arg]);
        };
        window.addEventListener('scroll', onWindowScroll, {passive: true});
        document.addEventListener('scroll', onElementScroll, true);
        host.__lfImportGuideScroll = {
            state,
            originalScrollIntoView,
            onWindowScroll,
            onElementScroll,
            observer,
        };
    });
}

async function resetImportScrollObservation(page: Page): Promise<void> {
    await page.evaluate(() => {
        const harness = (window as ImportScrollWindow).__lfImportGuideScroll;
        if (!harness) throw new Error('Import guide scroll observation was not installed');
        const content = document.querySelector<HTMLElement>('[data-testid="import-wizard-content"]');
        if (!content) throw new Error('Import wizard content was not mounted before the observation reset');
        harness.state.initialWindowY = window.scrollY;
        harness.state.initialWizardScrollTop = content.scrollTop;
        harness.state.windowEvents = [];
        harness.state.wizardScrollEvents = [];
        harness.state.scrollIntoViewTargets = [];
    });
}

async function expectNoImportGuideScroll(page: Page, label: string, expectedInitialWizardScrollTop?: number): Promise<void> {
    const observation = await page.evaluate(() => {
        const harness = (window as ImportScrollWindow).__lfImportGuideScroll;
        if (!harness) throw new Error('Import guide scroll observation was not installed');
        const content = document.querySelector<HTMLElement>('[data-testid="import-wizard-content"]');
        return {
            initialWindowY: harness.state.initialWindowY,
            initialWizardScrollTop: harness.state.initialWizardScrollTop,
            windowEvents: [...harness.state.windowEvents],
            wizardScrollEvents: [...harness.state.wizardScrollEvents],
            scrollIntoViewTargets: [...harness.state.scrollIntoViewTargets],
            currentWindowY: window.scrollY,
            currentWizardScrollTop: content?.scrollTop ?? null,
        };
    });
    expect(observation.initialWizardScrollTop, `${label} must observe the wizard from its first mounted scroll state`).not.toBeNull();
    if (expectedInitialWizardScrollTop !== undefined) {
        expect(observation.initialWizardScrollTop, `${label} must begin at the declared scroll origin`).toBe(expectedInitialWizardScrollTop);
    }
    expect(observation.scrollIntoViewTargets, `${label} must not call scrollIntoView`).toEqual([]);
    expect(observation.windowEvents, `${label} must not emit a window scroll`).toEqual([]);
    expect(observation.currentWindowY, `${label} must preserve window.scrollY`).toBe(observation.initialWindowY);
    expect(observation.wizardScrollEvents, `${label} must not scroll the wizard content`).toEqual([]);
    expect(observation.currentWizardScrollTop, `${label} must preserve the wizard content scrollTop`).toBe(observation.initialWizardScrollTop);
}

async function restoreImportScrollObservation(page: Page): Promise<void> {
    await page.evaluate(() => {
        const host = window as ImportScrollWindow;
        const harness = host.__lfImportGuideScroll;
        if (!harness) return;
        Element.prototype.scrollIntoView = harness.originalScrollIntoView;
        window.removeEventListener('scroll', harness.onWindowScroll);
        document.removeEventListener('scroll', harness.onElementScroll, true);
        harness.observer.disconnect();
        delete host.__lfImportGuideScroll;
    });
}

async function installCoachmarkGeometryObservation(page: Page): Promise<void> {
    await page.evaluate(() => {
        const host = window as ImportScrollWindow;
        if (host.__lfCoachmarkGeometry) throw new Error('Coachmark geometry observation is already installed');
        const states: string[] = [];
        const capture = () => {
            const state = document.querySelector<HTMLElement>('[data-testid="onboarding-coachmark"]')?.dataset.geometryState;
            if (state && states.at(-1) !== state) states.push(state);
        };
        const observer = new MutationObserver(capture);
        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ['data-geometry-state'],
            childList: true,
            subtree: true,
        });
        capture();
        host.__lfCoachmarkGeometry = {states, observer};
    });
}

async function readAndRestoreCoachmarkGeometryObservation(page: Page): Promise<string[]> {
    return page.evaluate(() => {
        const host = window as ImportScrollWindow;
        const harness = host.__lfCoachmarkGeometry;
        if (!harness) throw new Error('Coachmark geometry observation was not installed');
        harness.observer.disconnect();
        delete host.__lfCoachmarkGeometry;
        return [...harness.states];
    });
}

async function restoreCoachmarkGeometryObservation(page: Page): Promise<void> {
    await page.evaluate(() => {
        const host = window as ImportScrollWindow;
        host.__lfCoachmarkGeometry?.observer.disconnect();
        delete host.__lfCoachmarkGeometry;
    });
}

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
 * Assign the uploaded file(s) to a specifically named owned broker via the step-1
 * "assign all" dropdown. Existing analyze/review cases use their seeded broker; the
 * onboarding cases pass the unique broker owned by their disposable account.
 */
async function assignBroker(page: Page, brokerName = 'Interactive Brokers') {
    await page.getByTestId('import-wizard-step1-broker-select').locator('[role="combobox"]').click();
    const option = page.locator('[data-testid^="search-select-option-"]').filter({hasText: brokerName});
    await expect(option, `Owned broker ${brokerName} must be the unique matching option`).toHaveCount(1, {timeout: 8_000});
    await option.click();
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 8_000});
}

/**
 * Full corridor from a freshly opened wizard to the settled analyze step, using a file this
 * test owns. Returns the file's unique name for row-scoped assertions.
 */
async function reachAnalyze(page: Page, onGuideStep?: (stepId: string) => Promise<void>, brokerName?: string): Promise<string> {
    const file = csv(uniqueSuffix());
    if (onGuideStep) {
        await onGuideStep('import.upload');
        await expectNoImportGuideScroll(page, 'First-mount Upload guide activation', 0);
        await expect(page.getByTestId('import-wizard-back')).toHaveCount(0);
    }

    // Step 1: upload this test's own file, assign a broker, advance.
    const input = page.getByTestId('import-wizard-step1').locator('[data-testid="file-input"]');
    await input.setInputFiles(file);
    await expect(page.getByTestId('import-wizard-step1').locator('tbody tr[data-row-id]')).toHaveCount(1);
    await assignBroker(page, brokerName);
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
    if (onGuideStep) await resetImportScrollObservation(page);
    await page.getByTestId('import-wizard-parse').click();
    await page.getByTestId('import-wizard-step3').waitFor({state: 'visible', timeout: 10_000});
    await waitForParseVerdict(page);
    if (onGuideStep) {
        await onGuideStep('import.analyze');
        await expectNoImportGuideScroll(page, 'Analyze guide activation');
    }
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

const IMPORT_GUIDE_TARGETS: Record<string, string> = {
    'import.upload': 'import-wizard-next',
    'import.select': 'import-wizard-parse',
    'import.analyze': 'import-wizard-continue',
    'import.assets': 'import-wizard-assets-continue',
    'import.fix': 'import-wizard-fix-continue',
    'import.duplicates': 'import-wizard-duplicates-continue',
    'import.review': 'import-wizard-import',
    'import.bulk': 'tx-bulk-commit',
};

async function expectGuideGeometry(page: Page, targetTestId: string): Promise<void> {
    await expect
        .poll(
            () =>
                page.evaluate((testId) => {
                    const coachmarks = document.querySelectorAll<HTMLElement>('[data-testid="onboarding-coachmark"]');
                    const panels = document.querySelectorAll<HTMLElement>('[data-testid="onboarding-coachmark-panel"]');
                    const targets = document.querySelectorAll<HTMLElement>(`[data-testid="${CSS.escape(testId)}"]`);
                    const coachmark = coachmarks.length === 1 ? coachmarks[0] : null;
                    const panel = panels.length === 1 ? panels[0] : null;
                    const target = targets.length === 1 ? targets[0] : null;
                    const hotspotXRaw = coachmark?.dataset.pointerHotspotX ?? '';
                    const hotspotYRaw = coachmark?.dataset.pointerHotspotY ?? '';
                    const hotspotAttrsReady = hotspotXRaw !== '' && hotspotYRaw !== '';
                    const hotspotX = hotspotAttrsReady ? Number(hotspotXRaw) : null;
                    const hotspotY = hotspotAttrsReady ? Number(hotspotYRaw) : null;
                    const hotspotFinite = hotspotX !== null && hotspotY !== null && Number.isFinite(hotspotX) && Number.isFinite(hotspotY);
                    const panelRect = panel?.getBoundingClientRect() ?? null;
                    const targetRect = target?.getBoundingClientRect() ?? null;
                    const viewportRect = {left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight};
                    const panelRectReady = panelRect !== null && panelRect.width > 0 && panelRect.height > 0;
                    const targetRectReady = targetRect !== null && targetRect.width > 0 && targetRect.height > 0;
                    const viewportRectReady = viewportRect.right > viewportRect.left && viewportRect.bottom > viewportRect.top;
                    let panelInViewport = false;
                    let overlapArea: number | null = null;
                    let hotspotInTarget = false;

                    if (panelRect && targetRect && panelRectReady && targetRectReady && viewportRectReady) {
                        panelInViewport = panelRect.left >= viewportRect.left && panelRect.top >= viewportRect.top && panelRect.right <= viewportRect.right && panelRect.bottom <= viewportRect.bottom;
                        const overlapWidth = Math.max(0, Math.min(panelRect.right, targetRect.right) - Math.max(panelRect.left, targetRect.left));
                        const overlapHeight = Math.max(0, Math.min(panelRect.bottom, targetRect.bottom) - Math.max(panelRect.top, targetRect.top));
                        overlapArea = overlapWidth * overlapHeight;
                    }
                    if (targetRect && targetRectReady && hotspotFinite && hotspotX !== null && hotspotY !== null) {
                        hotspotInTarget = hotspotX >= targetRect.left - 2 && hotspotX <= targetRect.right + 2 && hotspotY >= targetRect.top - 2 && hotspotY <= targetRect.bottom + 2;
                    }

                    return {
                        coachmarkCount: coachmarks.length,
                        panelCount: panels.length,
                        targetCount: targets.length,
                        guideState: coachmark?.dataset.guideState ?? null,
                        targetStable: coachmark?.dataset.targetStable ?? null,
                        pointer: coachmark?.dataset.pointer ?? null,
                        hotspotAttrsReady,
                        hotspotFinite,
                        panelRectReady,
                        targetRectReady,
                        viewportRectReady,
                        panelInViewport,
                        overlapArea,
                        hotspotInTarget,
                    };
                }, targetTestId),
            {timeout: 10_000, message: `Guide geometry never settled for ${targetTestId}`},
        )
        .toEqual({
            coachmarkCount: 1,
            panelCount: 1,
            targetCount: 1,
            guideState: 'anchored',
            targetStable: 'true',
            pointer: 'cursor',
            hotspotAttrsReady: true,
            hotspotFinite: true,
            panelRectReady: true,
            targetRectReady: true,
            viewportRectReady: true,
            panelInViewport: true,
            overlapArea: 0,
            hotspotInTarget: true,
        });
}

/**
 * Import wizard steps use the wizard's own navigation. The shared guide chrome
 * therefore has one X exit, no Back and no duplicate Next. Only `import.bulk`
 * gains the guide's final Next/Finish action.
 */
async function expectImportGuideChrome(page: Page, stepId: string, options: {finish?: boolean} = {}) {
    const coachmark = page.getByTestId('onboarding-coachmark');
    await expect(coachmark).toHaveAttribute('data-step-id', stepId, {timeout: 10_000});
    await expect(coachmark).toHaveAttribute('data-guide-state', 'anchored', {timeout: 10_000});
    await expect(coachmark).toHaveAttribute('data-geometry-state', 'stable', {timeout: 10_000});
    await expect(coachmark).toHaveAttribute('data-target-stable', 'true');
    await expect(coachmark).toHaveAttribute('data-pointer', 'cursor');
    await expect(coachmark).toHaveAttribute('data-highlight', 'none');
    await expect(coachmark).toHaveAttribute('data-panel-placement', 'top');
    await expect(page.getByTestId('onboarding-coachmark-pointer')).toBeVisible();
    await expect(page.getByTestId('onboarding-coachmark-skip')).toHaveCount(0);
    await expect(page.getByTestId('onboarding-coachmark-close')).toBeVisible();
    await expect(page.getByTestId('onboarding-coachmark-pause')).toHaveCount(0);
    await expect(page.getByTestId('onboarding-coachmark-back')).toHaveCount(0);
    await expect(page.getByTestId('onboarding-coachmark-progress')).toBeVisible();
    await expect(page.getByTestId('onboarding-spotlight-top')).toHaveCount(0);
    await expect(page.getByTestId('onboarding-coachmark-backdrop')).toHaveCount(0);
    await expect(coachmark.locator('[data-testid="onboarding-coachmark-pointer-line"]')).toHaveCount(0);
    const targetTestId = IMPORT_GUIDE_TARGETS[stepId];
    if (!targetTestId) throw new Error(`No real Import action target declared for ${stepId}`);
    await expect(page.getByTestId(targetTestId)).toHaveAttribute('aria-describedby', 'onboarding-coachmark-description');
    await expectGuideGeometry(page, targetTestId);
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
        await installTerminalOnboardingProgress(page);
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
        await installTerminalOnboardingProgress(page);
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
// Each guide case owns a disposable account and broker, terminally skips that
// account's setup flows, then arms Import through the real Replay control. Its
// upload and in-memory Bulk draft therefore share no canonical account state,
// mutable fixture broker, or transaction row with a neighbouring worker.
//
// Manual-only seam, stated rather than faked: this suite's owned race-free CSV has no
// asset column or duplicate rows, so it normally emits no assets/fix/duplicates step.
// `advanceConditionalStepsToReview()` follows and verifies any conditional step the
// real parser does emit, but deliberately does not manufacture one. Dedicated
// parser-owned fixtures plus the duplicate-bounce path remain in the manual runbook.
test.describe('Import Wizard — onboarding guide handoff', () => {
    /**
     * Arms the import guide replay the same way a real user would revisit it — the
     * "Replay" control on Settings' Preferences tab — never a fabricated internal flag.
     * Shared verbatim by G1 and G2, both of which need the guide armed before they ever
     * touch the wizard.
     */
    async function armImportGuideReplay(page: Page) {
        await navigateTo(page, '/settings');
        await page.getByTestId('settings-tab-preferences').click();
        await page.getByTestId('onboarding-group-transactions').evaluate((element) => {
            (element as HTMLDetailsElement).open = true;
        });
        await expect(page.getByTestId('onboarding-flow-import_guide')).toBeVisible({timeout: 10_000});
        await page.getByTestId('onboarding-replay-import_guide').click();
        await expect(page.getByTestId('onboarding-flow-import_guide-armed')).toBeVisible({timeout: 5_000});
    }

    test('G1: terminal import replay tracks the wizard, suspends for ParseDetail, and exits without committing or rewriting status', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, `g1_${testInfo.project.name}`);
        const ownedBrokerIds: number[] = [];
        const commitRequests: string[] = [];
        const terminalGuideRequests: string[] = [];
        const recordRequest = (req: Request) => {
            if (req.method() !== 'POST') return;
            const path = new URL(req.url()).pathname;
            if (path === '/api/v1/transactions/commit') commitRequests.push(req.url());
            if (/^\/api\/v1\/settings\/onboarding\/import_guide\/(?:(?:complete|skip)|steps\/[^/]+\/(?:complete|skip))$/.test(path)) terminalGuideRequests.push(path);
        };
        let scrollObservationInstalled = false;
        let geometryObservationInstalled = false;

        try {
            await login(page, user);
            await prepareDisposableImportAccount(page);
            const broker = await createOwnedBroker(page, `g1-${testInfo.project.name}`);
            ownedBrokerIds.push(broker.id);
            await armImportGuideReplay(page);
            page.on('request', recordRequest);

            await goToTransactions(page);
            await installImportScrollObservation(page);
            scrollObservationInstalled = true;
            await openImportWizard(page);

            const coachmark = page.getByTestId('onboarding-coachmark');
            // Never send Escape while the replay is under test: Escape and X both
            // consume the current replay step, so either would change this walk.
            const fileName = await reachAnalyze(page, (stepId) => expectImportGuideChrome(page, stepId), broker.name);
            await restoreImportScrollObservation(page);
            scrollObservationInstalled = false;

            // TransactionBulk + ImportWizard already occupy the two supported modal
            // depths. ParseDetail is depth 3, so its presence intentionally suspends
            // the coachmark until that third modal closes.
            const row = page.getByTestId('import-wizard-step3').locator('tbody tr[data-row-id]').filter({hasText: fileName}).first();
            await row.dblclick();
            await expect(page.getByTestId('parse-detail-modal')).toBeVisible({timeout: 5_000});
            await expect(coachmark).toHaveCount(1, {timeout: 5_000});
            await expect(coachmark).toHaveAttribute('data-step-id', 'import.analyze');
            await expect(coachmark).toHaveAttribute('aria-hidden', 'true');
            await expect(coachmark).toBeHidden();
            await installCoachmarkGeometryObservation(page);
            geometryObservationInstalled = true;
            await page.getByTestId('parse-detail-close').click();
            await expect(page.getByTestId('parse-detail-modal')).toHaveCount(0, {timeout: 5_000});
            // Returning to supported depth 2 restores the same anchored semantic step.
            await expectImportGuideChrome(page, 'import.analyze');
            const resumeGeometryStates = await readAndRestoreCoachmarkGeometryObservation(page);
            geometryObservationInstalled = false;
            expect(resumeGeometryStates, 'ParseDetail resume must publish a stable coachmark').toContain('stable');
            expect(resumeGeometryStates, 'ParseDetail resume must retain prior geometry without a waiting-label flash').not.toContain('waiting');

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
            if (scrollObservationInstalled) await restoreImportScrollObservation(page);
            if (geometryObservationInstalled) await restoreCoachmarkGeometryObservation(page);
            page.off('request', recordRequest);
            try {
                await cleanupOwnedFiles(page);
            } finally {
                await deleteDisposableUser(request, user, ownedBrokerIds);
            }
        }
    });

    test('G2: closing the Bulk handoff preserves remaining replay steps without restarting completed upload', async ({page, request}, testInfo) => {
        // Same real owned-CSV corridor as G1 (armImportGuideReplay, then upload -> assign
        // -> select -> parse -> review -> handoff), walked without G1's nested-modal
        // detour: this test is about what happens when the handoff *closes*, not about
        // re-proving the per-step tracking G1 already covers. Never send Escape anywhere
        // in this walk — it shares X's current-step exit policy and would end
        // the test before it reaches the handoff under test.
        const user = await registerDisposableUser(request, `g2_${testInfo.project.name}`);
        const ownedBrokerIds: number[] = [];
        const commitRequests: string[] = [];
        const terminalGuideRequests: string[] = [];
        const recordRequest = (req: Request) => {
            if (req.method() !== 'POST') return;
            const path = new URL(req.url()).pathname;
            if (path === '/api/v1/transactions/commit') commitRequests.push(req.url());
            if (/^\/api\/v1\/settings\/onboarding\/import_guide\/(?:(?:complete|skip)|steps\/[^/]+\/(?:complete|skip))$/.test(path)) terminalGuideRequests.push(path);
        };
        let scrollObservationInstalled = false;

        try {
            await login(page, user);
            await prepareDisposableImportAccount(page);
            const broker = await createOwnedBroker(page, `g2-${testInfo.project.name}`);
            ownedBrokerIds.push(broker.id);
            await armImportGuideReplay(page);
            page.on('request', recordRequest);

            await goToTransactions(page);
            await installImportScrollObservation(page);
            scrollObservationInstalled = true;
            await openImportWizard(page);

            const coachmark = page.getByTestId('onboarding-coachmark');
            await reachAnalyze(page, (stepId) => expectImportGuideChrome(page, stepId), broker.name);
            await restoreImportScrollObservation(page);
            scrollObservationInstalled = false;

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

            // TransactionBulkModal's isOpen effect calls
            // onboardingGuide.dismissHost({restartAtFirst: true}) the moment it closes
            // while the guide is on import.bulk. Step-managed replay ignores the
            // restart hint, so its remaining-step set survives. Prove the coachmark is gone
            // now that its host (bulkRoot) is provably gone too (rule 17: an absence
            // assertion needs a presence barrier), and that nothing was committed.
            await expect(coachmark).toHaveCount(0, {timeout: 5_000});
            expect(commitRequests, 'Closing the handoff must never commit').toEqual([]);

            // Reopening the wizard starts at Upload, but Upload was already consumed
            // from this replay. Step-managed replay must therefore stay quiet here
            // instead of repeating a terminal step; the still-unseen optional steps
            // and Bulk handoff remain armed for a future matching host.
            await openImportWizard(page);
            await expect(coachmark).toHaveCount(0, {timeout: 5_000});
            await expect(page.getByTestId('import-wizard-stepper')).toBeVisible();
            expect(commitRequests, 'Reopening at a completed step must never commit').toEqual([]);
            expect(terminalGuideRequests, 'Replay-only navigation must never persist step or flow status').toEqual([]);

            // Nothing was uploaded on this second open, so closing it needs no confirm.
            await page.getByTestId('import-wizard-close').click();
            await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 5_000});

            await navigateTo(page, '/settings');
            await page.getByTestId('settings-tab-preferences').click();
            await page.getByTestId('onboarding-group-transactions').evaluate((element) => {
                (element as HTMLDetailsElement).open = true;
            });
            await expect(page.getByTestId('onboarding-flow-import_guide-armed')).toBeVisible({timeout: 5_000});
            await page.getByTestId('onboarding-replay-import_guide').click();
            await expect(page.getByTestId('onboarding-flow-import_guide-armed')).toHaveCount(0, {timeout: 5_000});
            expect(commitRequests, 'Closing and cancelling replay must never commit').toEqual([]);
            expect(terminalGuideRequests, 'Cancelling a replay must never persist Finish or Skip').toEqual([]);
        } finally {
            if (scrollObservationInstalled) await restoreImportScrollObservation(page);
            page.off('request', recordRequest);
            try {
                await cleanupOwnedFiles(page);
            } finally {
                await deleteDisposableUser(request, user, ownedBrokerIds);
            }
        }
    });
});
