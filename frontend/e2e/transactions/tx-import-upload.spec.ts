/**
 * Import Wizard — Upload step (step 1) E2E tests
 *
 * The wizard's entry step is where a user drops files, the client validates them, and a
 * broker is assigned before anything is sent to the server. None of it touched the server:
 * files are only POSTed to /brokers/import/upload when "Next" is clicked, and the tests of
 * the first block never leave step 1, so they perform ZERO backend writes and need no cleanup.
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
 * The last block ("upload batch", C1 of the report-set plan) is the one exception: it clicks
 * "Next", so it creates its own broker, uploads two synthetic sample reports to it, and
 * deletes the files and the broker afterwards. It checks that the files of one step-1
 * session reach the server with one shared `batch_id`.
 *
 * Entry point: the transactions toolbar "Import" button (`tx-import-button`) sets
 * bulkIntent={action:'import'}, and the BulkModal auto-opens the wizard on that intent —
 * a clean entry that never selects a table row by position.
 */

import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';
import {TEST_USER} from '../fixtures/test-users';
import path from 'path';
import {fileURLToPath} from 'url';

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

// ---------------------------------------------------------------------------
// C1 — the upload batch (the one block of this file that writes, and cleans up)
// ---------------------------------------------------------------------------

const API = '/api/v1';
const BRIM_UPLOAD_PATH = `${API}/brokers/import/upload`;
const SPEC_DIR = path.dirname(fileURLToPath(import.meta.url));
/** The repository's synthetic Generic CSV samples — never a real broker export. */
const SAMPLE_REPORTS = ['generic_simple.csv', 'generic_with_assets.csv'].map((name) => path.resolve(SPEC_DIR, '../../../backend/app/services/brim_providers/sample_reports', name));
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type UploadedInfo = {file_id: string; filename: string; target_broker_id: number | null; batch_id?: string | null};

/** A broker this test owns. The name goes through `uniqueSuffix()`: `brokers.name` is uniquely indexed. */
async function createOwnedBroker(page: Page, name: string): Promise<number> {
    const response = await page.request.post(`${API}/brokers`, {data: [{name, allow_cash_overdraft: true}]});
    expect(response.ok(), `create owned broker: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null}>};
    const created = results.find((result) => result.name === name);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`Owned broker "${name}" was not created: ${JSON.stringify(results)}`);
    return created.broker_id;
}

/** The BRIM files stored on one broker; the list also returns legacy files with no broker, so the target is filtered. */
async function brimFilesOn(page: Page, brokerId: number): Promise<UploadedInfo[]> {
    const response = await page.request.get(`${API}/brokers/import/files?broker_ids=${brokerId}`);
    expect(response.ok(), `list the BRIM files of broker ${brokerId}: HTTP ${response.status()}`).toBe(true);
    const files = (await response.json()) as UploadedInfo[];
    return files.filter((file) => file.target_broker_id === brokerId);
}

/** Delete every BRIM file on the owned broker, then the broker: scoped to the id this test created. */
async function deleteOwnedBrokerAndFiles(page: Page, brokerId: number): Promise<void> {
    const failures: string[] = [];
    try {
        for (const file of await brimFilesOn(page, brokerId)) {
            const response = await page.request.delete(`${API}/brokers/import/files/${file.file_id}`);
            if (!response.ok()) failures.push(`BRIM file ${file.file_id}: HTTP ${response.status()}`);
        }
    } catch (error) {
        failures.push(`list the BRIM files of broker ${brokerId}: ${String(error)}`);
    }
    try {
        const response = await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`);
        const body = (await response.json().catch(() => null)) as {results?: Array<{id: number; success: boolean}>} | null;
        if (!response.ok() || !body?.results?.find((result) => result.id === brokerId)?.success) failures.push(`broker ${brokerId}: HTTP ${response.status()} ${JSON.stringify(body)}`);
    } catch (error) {
        failures.push(`broker ${brokerId}: ${String(error)}`);
    }
    expect(failures, 'cleanup removes the BRIM files and the broker this test created').toEqual([]);
}

/** The upload responses `action` produces on this page: exactly `expected` of them, each a 200. */
async function uploadsDuring(page: Page, expected: number, action: () => Promise<void>): Promise<UploadedInfo[]> {
    const replies: Array<Promise<{status: number; body: string}>> = [];
    const listener = (response: Awaited<ReturnType<Page['waitForResponse']>>) => {
        if (response.request().method() === 'POST' && new URL(response.url()).pathname === BRIM_UPLOAD_PATH) replies.push(response.text().then((body) => ({status: response.status(), body})));
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
    for (const {status, body} of settled) expect(status, `POST ${BRIM_UPLOAD_PATH}: ${body}`).toBe(200);
    return settled.map(({body}) => JSON.parse(body) as UploadedInfo);
}

function expectUuid(value: string | null | undefined, what: string): string {
    expect(typeof value === 'string' && UUID_PATTERN.test(value), `${what}: ${JSON.stringify(value)} must be a UUID`).toBe(true);
    return value as string;
}

test.describe('Import Wizard — upload batch', () => {
    let ownedBrokerId: number | undefined;

    test.beforeEach(async ({page}) => {
        ownedBrokerId = undefined;
        await login(page, TEST_USER);
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the
    // assertion error it follows, and that assertion is the point of this block.
    test.afterEach(async ({page}) => {
        if (ownedBrokerId === undefined) return;
        // Unmount the wizard first, so nothing on the page reacts while its files go away.
        await page.goto('about:blank');
        await deleteOwnedBrokerAndFiles(page, ownedBrokerId);
    });

    test('C1 files uploaded together in step 1 share one batch id', async ({page}) => {
        test.setTimeout(60_000);
        const brokerName = `Upload batch wizard ${uniqueSuffix()}`;
        const brokerId = await createOwnedBroker(page, brokerName);
        ownedBrokerId = brokerId;
        // Created before the page loads, so the wizard's broker list includes it.
        await goToTransactions(page);
        const step1 = await openImportWizard(page);

        await step1.getByTestId('file-input').setInputFiles(SAMPLE_REPORTS);
        await expect(pendingRows(page)).toHaveCount(SAMPLE_REPORTS.length);
        await optionsClosed(page);
        await step1.getByTestId('import-wizard-step1-broker-select').getByRole('combobox').click();
        const option = page.getByTestId(`search-select-option-${brokerId}`);
        await expect(option, `owned broker ${brokerName} must be offered by the "assign all" select`).toBeVisible({timeout: 8_000});
        await option.click();
        await optionsClosed(page);
        const next = page.getByTestId('import-wizard-next');
        await expect(next).toBeEnabled({timeout: 5_000});

        const uploaded = await uploadsDuring(page, SAMPLE_REPORTS.length, async () => {
            await next.click();
            // goNext moves on to step 2 only once every upload has settled.
            await expect(page.getByTestId('import-wizard-step2')).toBeVisible({timeout: 15_000});
        });

        expect(
            uploaded.map((file) => file.target_broker_id),
            'every file goes to the broker assigned in step 1',
        ).toEqual([brokerId, brokerId]);
        const batchIds = uploaded.map((file) => file.batch_id);
        const batchId = expectUuid(batchIds[0], 'batch_id of this step-1 session');
        expect(batchIds, 'the files of one step-1 session share one batch_id').toEqual([batchId, batchId]);
    });
});
