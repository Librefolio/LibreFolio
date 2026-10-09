/**
 * Import Wizard — a file its broker's default import plugin cannot read (Scalable Capital, workstream 37).
 *
 * A broker that sets a default import plugin says what its files are. Scalable Capital's two accounts
 * are two brokers whose default plugins refuse each other's export: `broker_scalable` (the broker
 * account) refuses the overnight account's file with the code `scalable_deposit_file`, which
 * `broker_scalable_deposit` reads. Right after step 1's Continue has uploaded the files, every file
 * whose broker's default plugin is not among the upload's `compatible_plugins` opens
 * `ImportBrokerMismatchModal`, one at a time: the wizard asks the default plugin why
 * (`GET /brokers/import/files/{file_id}/plugin-check?plugin_code=<default>`), shows that reason and
 * the other brokers whose default plugin reads the file, and offers Move, Keep or Remove. A broker
 * without a default plugin is never questioned, nor is a file a report-set plugin reads (decision
 * A18: it is read through its set). The targets come best plugin first, and the brokers of a
 * fallback plugin (the generic CSV) are offered only when no broker of a specific one is there.
 * Continue stays disabled from its click until every file has been reviewed.
 *
 *   M1 the overnight account's file assigned to the broker account, on an account that also has a
 *      broker importing with the generic CSV — which reads the file too: Continue is disabled while
 *      the prompt shows the reason and one target, the overnight account (the generic-CSV broker is
 *      dropped). Move uploads the same file there, in the same step-1 batch, and deletes the copy on
 *      the broker account; the wizard goes on to step 2, where the file is listed — selected — under
 *      the overnight account and nowhere else, as the server says too.
 *   M2 the same file assigned to the overnight account, whose default plugin reads it: no plugin is
 *      asked anything, no prompt, straight on to step 2.
 *   M3 Remove, with Continue disabled while the prompt is open: the file is deleted on the server and
 *      leaves the step-1 list; the review over, Continue is enabled again, and with no file left the
 *      wizard stays on the upload step, its drop zone open again.
 *
 * Why M1 runs on a disposable account. The fallback rule drops the generic-CSV brokers once a broker
 * of a specific plugin is offered, but *every* broker whose specific default plugin reads the file is
 * still a target. On the shared E2E user that includes M2's own overnight account whenever the two
 * tests run at once — and the brokers of any spec that imports Scalable files one day — so "one
 * target" would depend on the schedule. The account is registered by the test
 * (fixtures/onboarding-accounts.ts, every onboarding flow skipped over the API so no guide covers the
 * wizard), owns exactly the three brokers it creates — read back before the walk — and is deleted
 * with them. M2 and M3 assert nothing about the targets, so they run on the shared E2E user.
 *
 * Data. Every test creates its own brokers (unique names: `brokers.name` is uniquely indexed) before
 * the page loads, since the wizard reads the broker list once per session, and uploads a copy of
 * `scalable-deposit-export.csv` under a unique name. The cleanup leaves the page, deletes the BRIM
 * files on the test's own brokers, then the brokers (and the disposable account) — never anything
 * this test did not create. Nothing is parsed, nothing is imported.
 *
 * Key data-testids: tx-import-button · import-wizard-stepper [aria-current="step"][data-step-id] ·
 * import-wizard-step1 / file-uploader / file-input / import-wizard-step1-broker-select /
 * search-select-option-<brokerId> / import-wizard-next [disabled] · import-broker-mismatch-modal / -intro /
 * -reason / -target / -targets / -no-target / -no-reader / -counter / -move / -remove ·
 * import-wizard-step2 [data-busy] / import-wizard-broker-files-<brokerId> /
 * import-wizard-broker-toggle-<brokerId> / dt-row-checkbox-<fileId> [data-state].
 */

import {expect, test, type APIRequestContext, type Locator, type Page, type Request, type Response} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {optionsClosed} from '../fixtures/probe';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {readFileSync} from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';

const API = '/api/v1';
const BROKERS_PATH = `${API}/brokers`;
const UPLOAD_PATH = `${API}/brokers/import/upload`;
const FILES_PATH = `${API}/brokers/import/files`;
const PLUGIN_CHECK_PATH = /^\/api\/v1\/brokers\/import\/files\/[^/]+\/plugin-check$/;
const SPEC_DIR = path.dirname(fileURLToPath(import.meta.url));
/** The LibreFolio exporter's overnight account file (synthetic): read by `broker_scalable_deposit` and the generic CSV, refused by `broker_scalable`. */
const DEPOSIT_SAMPLE = path.resolve(SPEC_DIR, '../../../backend/app/services/brim_providers/sample_reports/scalable-deposit-export.csv');
const SCALABLE_BROKER = 'broker_scalable';
const SCALABLE_DEPOSIT = 'broker_scalable_deposit';
/** A fallback plugin (detection priority 0): its brokers are offered only when no broker of a specific plugin is. */
const GENERIC_CSV = 'broker_generic_csv';
/** The code `broker_scalable` refuses the overnight account's file with (backend `_scalable.refusal`). */
const DEPOSIT_FILE_REFUSAL = 'scalable_deposit_file';
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const UI_TIMEOUT = 10_000;
/** An upload, a plugin check, a step change: each waits on the server. */
const STEP_TIMEOUT = 30_000;

// ---------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type UploadedInfo = {file_id: string; filename: string; target_broker_id: number | null; batch_id?: string | null; compatible_plugins?: string[] | null};
type PluginCheck = {plugin_code: string; can_parse: boolean; refusal?: {code?: string | null; message: string; context?: Record<string, unknown> | null} | null};
type DeleteResult = {success?: boolean; file_id?: string};
type OwnedBroker = {id: number; name: string};
/** What a test created, for its cleanup: its brokers, and the disposable account they belong to when it has one. */
type Owned = {brokerIds: number[]; user: DisposableUser | null};

// ---------------------------------------------------------------------------
// Owned data
// ---------------------------------------------------------------------------

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    return (await response.json()) as T;
}

const byNumber = (a: number, b: number) => a - b;

/**
 * Brokers of the signed-in account, each with its default import plugin, created in one request. Every id
 * the server returns is recorded for the cleanup before anything about the result is checked.
 */
async function createOwnedBrokers(page: Page, owned: Owned, specs: ReadonlyArray<{tag: string; defaultPlugin: string}>): Promise<OwnedBroker[]> {
    const items = specs.map(({tag, defaultPlugin}) => ({name: `Broker mismatch ${tag} ${uniqueSuffix()}`, default_import_plugin: defaultPlugin}));
    const body = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(BROKERS_PATH, {data: items}), `create the owned brokers ${items.map((item) => item.name).join(', ')}`);
    for (const result of body.results) {
        if (result.success && typeof result.broker_id === 'number') owned.brokerIds.push(result.broker_id);
    }
    return items.map(({name}) => {
        const result = body.results.find((candidate) => candidate.name === name);
        if (!result?.success || typeof result.broker_id !== 'number') throw new Error(`Owned broker "${name}" was not created: ${JSON.stringify(body.results)}`);
        return {id: result.broker_id, name};
    });
}

/** The BRIM files stored on one broker. The list also returns files with no broker, so the target is filtered. */
async function filesOn(page: Page, brokerId: number): Promise<UploadedInfo[]> {
    const files = await jsonFrom<UploadedInfo[]>(await page.request.get(`${FILES_PATH}?broker_ids=${brokerId}`), `list the BRIM files of broker ${brokerId}`);
    return files.filter((file) => file.target_broker_id === brokerId);
}

/**
 * Leave the page, delete the BRIM files on the brokers this test created, then the brokers — through the
 * disposable account's own cleanup when the test registered one, which deletes the account last. Scoped
 * to the test's own broker ids: the files the product already deleted (a moved copy, a removed file) are
 * simply no longer listed. Every step is attempted; the failures are reported together.
 */
async function cleanupOwned(page: Page, request: APIRequestContext, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<unknown>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    // Unmount the wizard first, so nothing on the page reacts while its files go away.
    await attempt('leave the page', () => page.goto('about:blank'));
    for (const brokerId of owned.brokerIds) {
        await attempt(`the BRIM files of broker ${brokerId}`, async () => {
            for (const file of await filesOn(page, brokerId)) {
                const result = await jsonFrom<DeleteResult>(await page.request.delete(`${FILES_PATH}/${file.file_id}`), `delete BRIM file ${file.file_id}`);
                expect(result, `BRIM file ${file.file_id} is deleted`).toMatchObject({success: true, file_id: file.file_id});
            }
        });
    }
    const user = owned.user;
    if (user) {
        await attempt(`the disposable account ${user.username} and its brokers`, () => deleteDisposableUser(request, user, owned.brokerIds));
    } else {
        for (const brokerId of owned.brokerIds) {
            await attempt(`broker ${brokerId}`, async () => {
                const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${BROKERS_PATH}?ids=${brokerId}&force=true`), `delete broker ${brokerId}`);
                expect(result.results.find((item) => item.id === brokerId)?.success, `broker ${brokerId} is deleted`).toBe(true);
            });
        }
    }
    expect(failures, 'cleanup removes the files, the brokers and the account this test created — and nothing else').toEqual([]);
}

// ---------------------------------------------------------------------------
// The wizard
// ---------------------------------------------------------------------------

function isCall(method: string, pathname: string | RegExp): (response: Response) => boolean {
    return (response) => {
        if (response.request().method() !== method) return false;
        const actual = new URL(response.url()).pathname;
        return typeof pathname === 'string' ? actual === pathname : pathname.test(actual);
    };
}

/**
 * The response to `method pathname`, waited for from now on: call it *before* the action that sends the
 * request — a response is an edge, not a state. A request that never comes fails naming `what`.
 */
function responseTo(page: Page, method: string, pathname: string | RegExp, what: string): Promise<Response> {
    return page.waitForResponse(isCall(method, pathname), {timeout: STEP_TIMEOUT}).catch((error: unknown) => {
        throw new Error(`${what}: no answer to ${method} ${String(pathname)} within ${STEP_TIMEOUT} ms (${String(error)})`);
    });
}

async function goToTransactions(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** Open the wizard from the toolbar; return step 1 once it has settled (its broker list loaded). */
async function openImportWizard(page: Page): Promise<Locator> {
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: UI_TIMEOUT});
    const step1 = page.getByTestId('import-wizard-step1');
    await expect(step1).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step1, 15_000);
    return step1;
}

function currentStep(page: Page): Locator {
    return page.getByTestId('import-wizard-stepper').locator('[aria-current="step"]');
}

/** The rows of step 1's pending table: this wizard's own list, so counting them counts what this test dropped. */
function pendingRows(step1: Locator): Locator {
    return step1.locator('tbody tr[data-row-id]');
}

/** Drop a copy of the overnight account's sample under `fileName`, assign it to `brokerId` through "assign all", and leave Continue enabled. */
async function stageDepositFile(page: Page, step1: Locator, fileName: string, brokerId: number): Promise<void> {
    await expect(step1.getByTestId('file-uploader'), 'a fresh wizard opens with its drop zone unfolded').toBeVisible({timeout: UI_TIMEOUT});
    await step1.getByTestId('file-input').setInputFiles({name: fileName, mimeType: 'text/csv', buffer: readFileSync(DEPOSIT_SAMPLE)});
    await expect(pendingRows(step1), `${fileName} waits in the step-1 table`).toHaveCount(1, {timeout: UI_TIMEOUT});
    await optionsClosed(page);
    await step1.getByTestId('import-wizard-step1-broker-select').getByRole('combobox').click();
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option, `broker ${brokerId} is offered by "assign all"`).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(page.getByTestId('import-wizard-next'), 'a file with its broker lets step 1 go on').toBeEnabled({timeout: UI_TIMEOUT});
}

/** Click step 1's Continue and return the upload's answer: the file, its broker, its batch, the plugins that read it. */
async function continueAndUpload(page: Page, fileName: string, brokerId: number): Promise<UploadedInfo> {
    const [response] = await Promise.all([responseTo(page, 'POST', UPLOAD_PATH, `Continue uploads ${fileName}`), page.getByTestId('import-wizard-next').click()]);
    const uploaded = await jsonFrom<UploadedInfo>(response, `upload ${fileName}`);
    expect(uploaded, `${fileName} lands on broker ${brokerId} under its own name`).toMatchObject({filename: fileName, target_broker_id: brokerId});
    return uploaded;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Import Wizard — a file its broker’s default import plugin cannot read', () => {
    let owned: Owned = {brokerIds: [], user: null};

    test.beforeEach(() => {
        owned = {brokerIds: [], user: null};
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the assertion error it follows.
    test.afterEach(async ({page, request}) => {
        await cleanupOwned(page, request, owned);
    });

    test('M1: the overnight account’s file assigned to the broker account is offered to the overnight account alone, and Move takes it there', async ({page, request}, testInfo) => {
        test.setTimeout(120_000);
        owned.user = await registerDisposableUser(request, `bm_${testInfo.project.name}`);
        await prepareOnboardingAccount(page, owned.user, []);
        const [brokerAccount, overnightAccount, genericAccount] = await createOwnedBrokers(page, owned, [
            {tag: 'broker account', defaultPlugin: SCALABLE_BROKER},
            {tag: 'overnight account', defaultPlugin: SCALABLE_DEPOSIT},
            {tag: 'generic csv', defaultPlugin: GENERIC_CSV},
        ]);
        // The premise of "one target": the account sees no broker but these three. Read back, not inferred.
        const listed = await jsonFrom<{items: Array<{id: number}>}>(await page.request.get(BROKERS_PATH), 'list the account’s brokers');
        expect(listed.items.map((item) => item.id).sort(byNumber), 'premise: the account sees exactly the three brokers this test created').toEqual([brokerAccount.id, overnightAccount.id, genericAccount.id].sort(byNumber));

        // A full load once the brokers exist: the wizard reads the broker list once per session.
        await goToTransactions(page);
        const step1 = await openImportWizard(page);
        const fileName = `scalable-deposit-export-${uniqueSuffix()}.csv`;
        await stageDepositFile(page, step1, fileName, brokerAccount.id);

        // ① Continue uploads the file to the broker account, whose default plugin does not read it.
        const pluginCheck = responseTo(page, 'GET', PLUGIN_CHECK_PATH, 'the wizard asks the broker account’s default plugin why it refuses the file');
        // Awaited below, once the prompt is up; a failure before then must not surface as an unhandled rejection.
        pluginCheck.catch(() => undefined);
        const uploaded = await continueAndUpload(page, fileName, brokerAccount.id);
        expect(uploaded.compatible_plugins ?? [], 'premise: the overnight account’s plugin reads the file').toContain(SCALABLE_DEPOSIT);
        expect(uploaded.compatible_plugins ?? [], 'premise: the broker account’s plugin does not').not.toContain(SCALABLE_BROKER);
        // Without the fallback rule the generic-CSV broker would be a second target: the single one below means it was dropped.
        expect(uploaded.compatible_plugins ?? [], 'premise: the generic CSV reads the file too').toContain(GENERIC_CSV);
        expect(uploaded.batch_id ?? '', 'the step-1 session uploads under a batch').toMatch(UUID_PATTERN);

        // ② The prompt: the default plugin's reason, one broker to move the file to, and Move.
        const modal = page.getByTestId('import-broker-mismatch-modal');
        await expect(modal, 'a file its broker’s default plugin refuses is questioned').toBeVisible({timeout: STEP_TIMEOUT});
        const checkResponse = await pluginCheck;
        const checkUrl = new URL(checkResponse.url());
        expect([checkUrl.pathname, checkUrl.searchParams.get('plugin_code')], 'the question goes to the broker account’s default plugin, about the uploaded file').toEqual([`${FILES_PATH}/${uploaded.file_id}/plugin-check`, SCALABLE_BROKER]);
        const check = await jsonFrom<PluginCheck>(checkResponse, 'the plugin check');
        expect(check, 'broker_scalable refuses the overnight account’s file, with a code the UI translates').toMatchObject({plugin_code: SCALABLE_BROKER, can_parse: false, refusal: {code: DEPOSIT_FILE_REFUSAL}});

        await expect(modal.getByTestId('import-broker-mismatch-intro')).toBeVisible();
        await expect(page.getByTestId('import-wizard-next'), 'Continue waits for the answer: a second click would skip the review').toBeDisabled();
        await expect(modal.getByTestId('import-broker-mismatch-reason'), 'the refusal comes with its reason').toBeVisible();
        await expect(modal.getByTestId('import-broker-mismatch-target'), 'one broker of a specific plugin reads the file: a single target, the generic-CSV broker dropped').toBeVisible();
        // The other branches of the same block, absent while the single target is on screen.
        await expect(modal.getByTestId('import-broker-mismatch-targets')).toHaveCount(0);
        await expect(modal.getByTestId('import-broker-mismatch-no-target')).toHaveCount(0);
        await expect(modal.getByTestId('import-broker-mismatch-no-reader')).toHaveCount(0);
        await expect(modal.getByTestId('import-broker-mismatch-counter'), 'one file to review: no counter').toHaveCount(0);
        const move = modal.getByTestId('import-broker-mismatch-move');
        await expect(move, 'Move is offered for the single target').toBeEnabled();

        // ③ Move: the same file uploaded to the overnight account in the same batch, then the copy on the broker account deleted.
        const [moveResponse, deleteResponse] = await Promise.all([responseTo(page, 'POST', UPLOAD_PATH, 'Move uploads the file to the target'), responseTo(page, 'DELETE', `${FILES_PATH}/${uploaded.file_id}`, 'Move deletes the copy on the broker account'), move.click()]);
        const moved = await jsonFrom<UploadedInfo>(moveResponse, `move ${fileName}`);
        expect(moved, 'the file goes to the single target, under the same name, in the step-1 batch').toMatchObject({filename: fileName, target_broker_id: overnightAccount.id, batch_id: uploaded.batch_id});
        expect(moved.file_id, 'a new file on the target, not the old one').not.toBe(uploaded.file_id);
        expect(await jsonFrom<DeleteResult>(deleteResponse, 'delete the copy on the broker account'), 'the copy on the broker account is deleted').toMatchObject({success: true, file_id: uploaded.file_id});

        // ④ The prompt is answered and the wizard goes on: the file is listed, selected, under the overnight account only.
        await expect(modal, 'Move answers the question').toHaveCount(0, {timeout: UI_TIMEOUT});
        await expect(currentStep(page), 'the wizard goes on to the file selection').toHaveAttribute('data-step-id', 'select', {timeout: STEP_TIMEOUT});
        const step2 = page.getByTestId('import-wizard-step2');
        await expect(step2).toBeVisible({timeout: UI_TIMEOUT});
        await waitForSettled(step2, STEP_TIMEOUT);
        const overnightPanel = step2.getByTestId(`import-wizard-broker-files-${overnightAccount.id}`);
        await expect(overnightPanel.getByTestId(`import-wizard-broker-toggle-${overnightAccount.id}`), 'the panel of the broker holding the upload opens by itself').toHaveAttribute('aria-expanded', 'true', {timeout: UI_TIMEOUT});
        await expect(overnightPanel.getByTestId(`dt-row-checkbox-${moved.file_id}`), 'the moved file is listed under the overnight account, selected').toHaveAttribute('data-state', 'checked', {timeout: UI_TIMEOUT});
        await expect(step2.getByTestId(`import-wizard-broker-files-${brokerAccount.id}`), 'the broker account holds no file any more').toHaveCount(0);
        await expect(step2.getByTestId(`import-wizard-broker-files-${genericAccount.id}`), 'nothing went to the generic-CSV broker').toHaveCount(0);
        await expect(step2.getByTestId(`dt-row-checkbox-${uploaded.file_id}`), 'the deleted copy is listed nowhere').toHaveCount(0);

        // ⑤ The server agrees.
        expect((await page.request.get(`${FILES_PATH}/${uploaded.file_id}`)).status(), 'the copy on the broker account is gone').toBe(404);
        expect(
            (await filesOn(page, overnightAccount.id)).map((file) => file.file_id),
            'the overnight account holds the moved file',
        ).toEqual([moved.file_id]);
        expect(await filesOn(page, brokerAccount.id), 'the broker account holds nothing').toEqual([]);
        expect(await filesOn(page, genericAccount.id), 'the generic-CSV broker holds nothing').toEqual([]);
    });

    test('M2: the same file assigned to the overnight account, whose default plugin reads it, raises no question', async ({page}) => {
        test.setTimeout(60_000);
        await login(page, TEST_USER);
        const [overnightAccount] = await createOwnedBrokers(page, owned, [{tag: 'overnight account', defaultPlugin: SCALABLE_DEPOSIT}]);
        await goToTransactions(page);
        const step1 = await openImportWizard(page);
        const fileName = `scalable-deposit-export-${uniqueSuffix()}.csv`;
        await stageDepositFile(page, step1, fileName, overnightAccount.id);

        // Armed before Continue (a request is an edge): a plugin check would mean the file was questioned.
        const pluginChecks: string[] = [];
        const onRequest = (sent: Request) => {
            if (PLUGIN_CHECK_PATH.test(new URL(sent.url()).pathname)) pluginChecks.push(sent.url());
        };
        page.on('request', onRequest);
        try {
            const uploaded = await continueAndUpload(page, fileName, overnightAccount.id);
            expect(uploaded.compatible_plugins ?? [], 'premise: the overnight account’s default plugin reads the file').toContain(SCALABLE_DEPOSIT);

            // The barrier: step 2 opens only once the uploads have been reviewed — a question would hold the wizard on step 1.
            await expect(currentStep(page), 'the wizard goes straight on to the file selection').toHaveAttribute('data-step-id', 'select', {timeout: STEP_TIMEOUT});
            const step2 = page.getByTestId('import-wizard-step2');
            await expect(step2).toBeVisible({timeout: UI_TIMEOUT});
            await waitForSettled(step2, STEP_TIMEOUT);
            await expect(step2.getByTestId(`import-wizard-broker-files-${overnightAccount.id}`).getByTestId(`dt-row-checkbox-${uploaded.file_id}`), 'the file is listed under its own broker, selected').toHaveAttribute('data-state', 'checked', {timeout: UI_TIMEOUT});
            await expect(page.getByTestId('import-broker-mismatch-modal'), 'no question about a file its broker’s default plugin reads').toHaveCount(0);
        } finally {
            page.off('request', onRequest);
        }
        expect(pluginChecks, 'no plugin was asked why it refuses the file').toEqual([]);
    });

    test('M3: Remove deletes the uploaded file, and with no file left the wizard stays on the upload step', async ({page}) => {
        test.setTimeout(60_000);
        await login(page, TEST_USER);
        const [brokerAccount] = await createOwnedBrokers(page, owned, [{tag: 'broker account', defaultPlugin: SCALABLE_BROKER}]);
        await goToTransactions(page);
        const step1 = await openImportWizard(page);
        const fileName = `scalable-deposit-export-${uniqueSuffix()}.csv`;
        await stageDepositFile(page, step1, fileName, brokerAccount.id);

        const uploaded = await continueAndUpload(page, fileName, brokerAccount.id);
        expect(uploaded.compatible_plugins ?? [], 'premise: the broker account’s default plugin does not read the file').not.toContain(SCALABLE_BROKER);

        // The targets depend on what this shared user's other brokers read by default: Remove does not.
        const modal = page.getByTestId('import-broker-mismatch-modal');
        await expect(modal, 'the file is questioned').toBeVisible({timeout: STEP_TIMEOUT});
        const next = page.getByTestId('import-wizard-next');
        await expect(next, 'Continue waits for the answer').toBeDisabled();
        const remove = modal.getByTestId('import-broker-mismatch-remove');
        await expect(remove).toBeEnabled();
        const [deleteResponse] = await Promise.all([responseTo(page, 'DELETE', `${FILES_PATH}/${uploaded.file_id}`, 'Remove deletes the uploaded file'), remove.click()]);
        expect(await jsonFrom<DeleteResult>(deleteResponse, `remove ${fileName}`), 'the uploaded file is deleted').toMatchObject({success: true, file_id: uploaded.file_id});

        // The prompt is answered and the review is over — Continue is released with nothing left to upload —
        // and with no file left the wizard stays where new files can be dropped.
        await expect(modal, 'Remove answers the question').toHaveCount(0, {timeout: UI_TIMEOUT});
        await expect(pendingRows(step1), 'the removed file leaves the step-1 list').toHaveCount(0, {timeout: UI_TIMEOUT});
        await expect(next, 'the review is over: Continue is enabled again').toBeEnabled({timeout: UI_TIMEOUT});
        await expect(step1.getByTestId('file-uploader'), 'the drop zone unfolds again').toBeVisible({timeout: UI_TIMEOUT});
        await expect(currentStep(page), 'the wizard stays on the upload step').toHaveAttribute('data-step-id', 'upload');
        await expect(page.getByTestId('import-wizard-step2')).toHaveCount(0);

        expect((await page.request.get(`${FILES_PATH}/${uploaded.file_id}`)).status(), 'the file is gone from the server').toBe(404);
        expect(await filesOn(page, brokerAccount.id), 'the broker account holds nothing').toEqual([]);
    });
});
