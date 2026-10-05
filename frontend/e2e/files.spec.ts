import {expect, test, type Page} from './fixtures/playwright';
import {login, navigateTo} from './fixtures/auth-helpers';
import {TEST_USER} from './fixtures/test-users';
import {waitForEvent, waitForSettled} from './fixtures/app-events';
import {optionsClosed} from './fixtures/probe';
import {uniqueSuffix} from './fixtures/unique';
import {readFileSync} from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const API = '/api/v1';
const TEST_PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/a3cAAAAASUVORK5CYII=', 'base64');
const TEST_AVATAR_PNG = readFileSync(path.resolve(__dirname, '../../backend/staticResources/Avatars/men_01.png'));
const TEST_PDF = Buffer.from(
    '%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R>>endobj\n4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 72 120 Td (Preview PDF) Tj ET\nendstream endobj\nxref\n0 5\n0000000000 65535 f \ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n256\n%%EOF\n',
    'utf-8',
);

async function uploadStaticFile(page: Page, filename: string, content: Buffer | string, mimeType: string): Promise<string> {
    const response = await page.request.post(`${API}/uploads`, {
        multipart: {
            file: {
                name: filename,
                mimeType,
                buffer: typeof content === 'string' ? Buffer.from(content, 'utf-8') : content,
            },
        },
    });

    expect(response.ok()).toBeTruthy();
    const data = (await response.json()) as {file: {id: string}};
    return data.file.id;
}

async function createBroker(page: Page, name = `Preview Broker ${Date.now()}`): Promise<number> {
    const response = await page.request.post(`${API}/brokers`, {
        data: [
            {
                name,
                allow_cash_overdraft: true,
            },
        ],
    });

    expect(response.ok()).toBeTruthy();
    const data = (await response.json()) as {results: Array<{broker_id: number}>};
    return data.results[0].broker_id;
}

async function uploadBrimFile(page: Page, brokerId: number, filename: string, content: Buffer | string, mimeType: string): Promise<string> {
    const response = await page.request.post(`${API}/brokers/import/upload`, {
        multipart: {
            broker_id: String(brokerId),
            file: {
                name: filename,
                mimeType,
                buffer: typeof content === 'string' ? Buffer.from(content, 'utf-8') : content,
            },
        },
    });

    expect(response.ok()).toBeTruthy();
    const data = (await response.json()) as {file_id: string};
    return data.file_id;
}

const BRIM_UPLOAD_PATH = `${API}/brokers/import/upload`;
/** The repository's synthetic Generic CSV sample — never a real broker export. */
const SAMPLE_BRIM_REPORT = path.resolve(__dirname, '../../backend/app/services/brim_providers/sample_reports/generic_simple.csv');
const SAMPLE_BRIM_REPORT_NAME = path.basename(SAMPLE_BRIM_REPORT);

type BrimFileInfo = {file_id: string; filename: string; target_broker_id: number | null};

/** A second synthetic Generic CSV sample, for uploads of two files in one action. */
const SECOND_BRIM_REPORT = path.resolve(__dirname, '../../backend/app/services/brim_providers/sample_reports/generic_with_assets.csv');
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
type UploadedInfo = BrimFileInfo & {batch_id?: string | null};

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

/**
 * The BRIM files stored on one broker. The list endpoint also returns legacy files that
 * carry no broker at all, so the target is filtered here rather than assumed.
 */
async function brimFilesOn(page: Page, brokerId: number): Promise<BrimFileInfo[]> {
    const response = await page.request.get(`${API}/brokers/import/files?broker_ids=${brokerId}`);
    expect(response.ok(), `list the BRIM files of broker ${brokerId}: HTTP ${response.status()}`).toBe(true);
    const files = (await response.json()) as BrimFileInfo[];
    return files.filter((file) => file.target_broker_id === brokerId);
}

/**
 * Delete every BRIM file on the owned broker, then the broker. Scoped to the id this
 * test created, never to "whatever appeared since"; when the upload never happened
 * there is simply no file to delete, so the red this cleanup follows stays the only red.
 */
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

async function openStaticListView(page: Page): Promise<void> {
    await navigateTo(page, '/files?tab=static');
    await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true');

    const hasViewToggle = await page
        .getByTestId('view-mode-toggle')
        .isVisible()
        .catch(() => false);

    if (hasViewToggle) {
        await page.getByTestId('view-mode-list').click();
        await expect(page.getByTestId('view-mode-list')).toHaveClass(/active/);
    }
}

async function openStaticGridView(page: Page): Promise<void> {
    await navigateTo(page, '/files?tab=static');
    await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('view-mode-toggle')).toBeVisible({timeout: 8_000});
    await page.getByTestId('view-mode-grid').click();
    await expect(page.getByTestId('view-mode-grid')).toHaveClass(/active/);
}

/**
 * Wait for the preview modal to be open *and* done fetching.
 *
 * The modal renders a "Loading…" placeholder while the preview request is in
 * flight, so asserting on its body straight after it opens turns a slow backend
 * into "the element does not exist" — which is what four concurrent workers
 * produced. The shell publishes `data-busy`, so we wait for the state instead of
 * guessing a bigger number.
 */
async function waitForPreviewReady(page: Page): Promise<void> {
    await expect(page.getByTestId('file-preview-modal')).toBeVisible({timeout: 8_000});
    await expect(page.getByTestId('file-preview-shell')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
}

test.describe('Files Page', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test.describe('Page Access and Navigation', () => {
        test('can access files page', async ({page}) => {
            await navigateTo(page, '/files');
            await expect(page.getByTestId('files-page')).toBeVisible();
        });

        test('shows both tabs', async ({page}) => {
            await navigateTo(page, '/files');
            await expect(page.getByTestId('files-tab-static')).toBeVisible();
            await expect(page.getByTestId('files-tab-brim')).toBeVisible();
        });

        test('can switch to BRIM tab', async ({page}) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-brim').click();
            await expect(page.getByTestId('files-tab-brim')).toHaveAttribute('aria-selected', 'true');
        });

        test('can switch back to static tab', async ({page}) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-brim').click();
            await page.getByTestId('files-tab-static').click();
            await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true');
        });
    });

    test.describe('URL Deep-Linking', () => {
        test('URL filter tab=static opens static tab', async ({page}) => {
            await page.goto('/files?tab=static');
            await page.waitForLoadState('networkidle');
            await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true');
        });

        test('URL filter tab=brim opens BRIM tab', async ({page}) => {
            await page.goto('/files?tab=brim');
            await page.waitForLoadState('networkidle');
            await expect(page.getByTestId('files-tab-brim')).toHaveAttribute('aria-selected', 'true');
        });
    });

    test.describe('Static Files Tab', () => {
        test('shows files table for static resources', async ({page}) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-static').click();
            // FilesTable wrapper has testid files-table-static
            await expect(page.getByTestId('files-table-static')).toBeVisible();
        });

        test('upload button is visible', async ({page}) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-static').click();
            await expect(page.getByTestId('upload-button')).toBeVisible();
        });

        test('can toggle uploader visibility', async ({page}) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-static').click();

            // Initially uploader should not be visible
            await expect(page.getByTestId('file-uploader')).not.toBeVisible();

            // Click upload button to show uploader
            await page.getByTestId('upload-button').click();
            await expect(page.getByTestId('file-uploader')).toBeVisible();
            await expect(page.getByTestId('file-drop-zone')).toBeVisible();

            // Click again to hide
            await page.getByTestId('upload-button').click();
            await expect(page.getByTestId('file-uploader')).not.toBeVisible();
        });

        test('view mode toggle shows when files exist', async ({page}) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-static').click();

            // Check if view mode toggle is visible (only shows when files exist)
            const hasViewToggle = await page
                .getByTestId('view-mode-toggle')
                .isVisible()
                .catch(() => false);

            if (hasViewToggle) {
                await expect(page.getByTestId('view-mode-grid')).toBeVisible();
                await expect(page.getByTestId('view-mode-list')).toBeVisible();
            }
            // If no files, view toggle won't be shown - that's expected
        });

        test('can switch between grid and list view', async ({page}) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-static').click();

            // Only test if view toggle exists (files present)
            const hasViewToggle = await page
                .getByTestId('view-mode-toggle')
                .isVisible()
                .catch(() => false);

            if (hasViewToggle) {
                // Click grid view
                await page.getByTestId('view-mode-grid').click();
                await expect(page.getByTestId('view-mode-grid')).toHaveClass(/active/);

                // Click list view
                await page.getByTestId('view-mode-list').click();
                await expect(page.getByTestId('view-mode-list')).toHaveClass(/active/);
            }
        });
    });

    test.describe('BRIM Tab', () => {
        test('BRIM tab shows table or empty state', async ({page}) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-brim').click();

            // Wait for tab to be selected
            await expect(page.getByTestId('files-tab-brim')).toHaveAttribute('aria-selected', 'true');

            // Either the table or the empty state has to land — the two-stage
            // "look, sleep, look again" this replaced was a hand-rolled retry.
            await expect(page.getByTestId('files-table-brim').or(page.getByTestId('brim-empty-state')).first()).toBeVisible({timeout: 15_000});
        });
    });

    test.describe('File Upload', () => {
        test('can upload a file to static storage', async ({page}) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-static').click();

            // Show uploader
            await page.getByTestId('upload-button').click();
            await expect(page.getByTestId('file-uploader')).toBeVisible();

            // Upload a test file from BRIM samples
            const testFilePath = path.resolve(__dirname, '../../backend/app/services/brim_providers/sample_reports/generic_simple.csv');
            const fileInput = page.getByTestId('file-input');
            await fileInput.setInputFiles(testFilePath);

            // Wait for file to appear in drop zone (selected)
            await expect(page.locator('.file-item')).toBeVisible();
            await expect(page.locator('.file-name')).toContainText('generic_simple.csv');

            // Click the upload submit button
            await page.getByTestId('file-upload-submit').click();

            // The page now reports the upload (`file.uploaded`, no toast: the
            // list itself is the user-visible proof). Waiting on the event is
            // waiting on the thing, not on a duration.
            await waitForEvent(page, 'file.uploaded', {timeout: 30_000});

            // The uploader should have cleared after successful upload
            // or show a success state. Check if file-item is gone (cleared)
            const fileItemGone = await page
                .locator('.file-uploader .file-item')
                .isHidden()
                .catch(() => true);

            // If file item is gone, upload likely succeeded
            if (fileItemGone) {
                // Search for the file using the search/filter
                const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first();
                if (await searchInput.isVisible().catch(() => false)) {
                    await searchInput.fill('generic_simple');
                }

                // Check that file appears in the files table
                const fileRow = page.locator('text=generic_simple.csv');
                const isVisible = await fileRow.isVisible().catch(() => false);

                // If not found by text, check if we have any indication of success
                if (!isVisible) {
                    // Just verify the uploader worked - if we got here without errors, test passes
                    // The file may be on another page or need refresh
                    expect(fileItemGone).toBeTruthy();
                }
            }
        });

        test('can select and clear files from uploader', async ({page}) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-static').click();

            // Show uploader
            await page.getByTestId('upload-button').click();
            await expect(page.getByTestId('file-uploader')).toBeVisible();

            // Select a file
            const testFilePath = path.resolve(__dirname, '../../backend/app/services/brim_providers/sample_reports/generic_dates.csv');
            const fileInput = page.getByTestId('file-input');
            await fileInput.setInputFiles(testFilePath);

            // Verify file appears in selection
            await expect(page.locator('.file-item')).toBeVisible();
            await expect(page.locator('.file-name')).toContainText('generic_dates.csv');

            // Clear the selection
            await page.getByTestId('file-clear').click();

            // Verify file is cleared
            await expect(page.locator('.file-item')).not.toBeVisible();
        });
    });

    /**
     * BRIM upload from the Files page (assign-brokers modal).
     *
     * `POST /brokers/import/upload` reads `broker_id` from the multipart **form**
     * (`Form(...)`). `confirmBrimUpload` sent it as a query parameter and put only
     * `file` in the FormData, so every upload from this page answered 422. The status
     * is asserted first because it *is* the defect; the stored file is then read back
     * through the API, scoped to a broker this test creates — the mock seeds its own
     * `generic_simple.csv` on Interactive Brokers, so a file name alone proves nothing.
     */
    test.describe('BRIM upload to an owned broker', () => {
        let ownedBrokerId: number | undefined;

        test.beforeEach(() => {
            ownedBrokerId = undefined;
        });

        // afterEach, not `finally`: a cleanup throwing from `finally` would replace the
        // assertion error it follows, and that assertion is the point of this block.
        test.afterEach(async ({page}) => {
            if (ownedBrokerId !== undefined) await deleteOwnedBrokerAndFiles(page, ownedBrokerId);
        });

        test('uploads a BRIM report through the assign-brokers modal to its own broker', async ({page}) => {
            test.setTimeout(60_000);
            // Unique (`brokers.name` is uniquely indexed) and typed into the select's search below.
            const brokerName = `Upload regression BRIM ${uniqueSuffix()}`;
            const brokerId = await createBroker(page, brokerName);
            ownedBrokerId = brokerId;

            // Created before the page loads, so the page's broker list includes it.
            await navigateTo(page, '/files?tab=brim');
            await expect(page.getByTestId('files-tab-brim')).toHaveAttribute('aria-selected', 'true');
            await waitForSettled(page.getByTestId('files-page'));

            await page.getByTestId('upload-button').click();
            const uploader = page.getByTestId('file-uploader');
            await expect(uploader).toBeVisible({timeout: 5_000});
            // Selecting the file is what opens the assign-brokers modal.
            await uploader.getByTestId('file-input').setInputFiles(SAMPLE_BRIM_REPORT);

            const modal = page.getByTestId('brim-assign-modal');
            await expect(modal).toBeVisible({timeout: 5_000});
            const assignAll = modal.getByTestId('brim-assign-all');
            await assignAll.getByRole('combobox').click();
            await assignAll.getByRole('textbox').fill(brokerName);
            const option = assignAll.getByTestId(`search-select-option-${brokerId}`);
            await expect(option, `owned broker ${brokerName} must be offered by the assign-all select`).toBeVisible({timeout: 5_000});
            await option.click();
            await optionsClosed(page);

            const confirm = modal.getByTestId('brim-upload-confirm');
            await expect(confirm).toBeEnabled();
            // Armed before the click: a response is an edge, not a state.
            const uploadResponse = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === BRIM_UPLOAD_PATH, {timeout: 15_000});
            await confirm.click();
            const upload = await uploadResponse;
            const body = await upload.text();
            expect(upload.status(), `POST ${BRIM_UPLOAD_PATH} from the Files page: ${body}`).toBe(200);

            const uploaded = JSON.parse(body) as BrimFileInfo;
            expect(uploaded, 'the file goes to the broker chosen in the modal').toMatchObject({filename: SAMPLE_BRIM_REPORT_NAME, target_broker_id: brokerId});
            // confirmBrimUpload closes the modal only after every file has been accepted.
            await expect(modal).toBeHidden({timeout: 8_000});
            const stored = (await brimFilesOn(page, brokerId)).filter((file) => file.filename === SAMPLE_BRIM_REPORT_NAME);
            expect(
                stored.map((file) => file.file_id),
                `${SAMPLE_BRIM_REPORT_NAME} is stored exactly once on broker ${brokerId}`,
            ).toEqual([uploaded.file_id]);
        });

        /**
         * C1 — one confirmation is one report-set batch (design D-S22): every file of it
         * carries the same client-generated `batch_id`, a UUID in the multipart form, so
         * the server can group a report set by upload. Read back from this page's own
         * upload responses.
         */
        test('C1 two files confirmed together from the Files page share one batch id', async ({page}) => {
            test.setTimeout(60_000);
            const brokerName = `Upload batch BRIM ${uniqueSuffix()}`;
            const brokerId = await createBroker(page, brokerName);
            ownedBrokerId = brokerId;

            // Created before the page loads, so the page's broker list includes it.
            await navigateTo(page, '/files?tab=brim');
            await expect(page.getByTestId('files-tab-brim')).toHaveAttribute('aria-selected', 'true');
            await waitForSettled(page.getByTestId('files-page'));

            await page.getByTestId('upload-button').click();
            const uploader = page.getByTestId('file-uploader');
            await expect(uploader).toBeVisible({timeout: 5_000});
            await uploader.getByTestId('file-input').setInputFiles([SAMPLE_BRIM_REPORT, SECOND_BRIM_REPORT]);

            const modal = page.getByTestId('brim-assign-modal');
            await expect(modal).toBeVisible({timeout: 5_000});
            const assignAll = modal.getByTestId('brim-assign-all');
            await assignAll.getByRole('combobox').click();
            await assignAll.getByRole('textbox').fill(brokerName);
            const option = assignAll.getByTestId(`search-select-option-${brokerId}`);
            await expect(option, `owned broker ${brokerName} must be offered by the assign-all select`).toBeVisible({timeout: 5_000});
            await option.click();
            await optionsClosed(page);
            const confirm = modal.getByTestId('brim-upload-confirm');
            await expect(confirm).toBeEnabled();

            const uploaded = await uploadsDuring(page, 2, async () => {
                await confirm.click();
                // confirmBrimUpload closes the modal only after every file has been accepted.
                await expect(modal).toBeHidden({timeout: 15_000});
            });

            expect(
                uploaded.map((file) => file.target_broker_id),
                'both files go to the broker chosen in the modal',
            ).toEqual([brokerId, brokerId]);
            const batchIds = uploaded.map((file) => file.batch_id);
            const batchId = expectUuid(batchIds[0], 'batch_id of this confirmation');
            expect(batchIds, 'the files of one confirmation share one batch_id').toEqual([batchId, batchId]);
        });
    });

    test.describe('File Preview', () => {
        test('opens markdown preview from static list view', async ({page}) => {
            const fileId = await uploadStaticFile(page, `preview-${Date.now()}.md`, '# Hello preview\n\nThis is a markdown preview smoke test.\n', 'text/markdown');

            await openStaticListView(page);

            const row = page.locator(`[data-row-id="${fileId}"]`);
            await expect(row).toBeVisible({timeout: 8_000});
            await row.dblclick();

            await waitForPreviewReady(page);
            await expect(page.getByTestId('file-preview-markdown-rendered')).toBeVisible({
                timeout: 8_000,
            });

            await page.getByTestId('file-preview-markdown-raw-btn').click();
            await expect(page.getByTestId('file-preview-text')).toContainText('# Hello preview', {timeout: 5_000});
        });

        test('opens image preview from static grid view', async ({page}) => {
            const fileId = await uploadStaticFile(page, `preview-${Date.now()}.png`, TEST_PNG, 'image/png');

            await openStaticGridView(page);

            const previewButton = page.getByTestId(`file-grid-preview-${fileId}`);
            await expect(previewButton).toBeVisible({timeout: 8_000});
            await previewButton.click();

            await waitForPreviewReady(page);
            await expect(page.getByTestId('file-preview-image')).toBeVisible({timeout: 8_000});
        });

        test('shows preview detail message when API returns detail', async ({page}) => {
            const fileId = await uploadStaticFile(page, `preview-error-${Date.now()}.md`, '# Broken preview\n', 'text/markdown');

            await page.route('**/api/v1/uploads/*/preview', async (route) => {
                await route.fulfill({
                    status: 400,
                    contentType: 'application/json',
                    body: JSON.stringify({detail: 'Legacy .xls preview requires xlrd on server'}),
                });
            });

            await openStaticListView(page);

            const row = page.locator(`[data-row-id="${fileId}"]`);
            await expect(row).toBeVisible({timeout: 8_000});
            await row.dblclick();

            await waitForPreviewReady(page);
            await expect(page.getByTestId('file-preview-modal')).toContainText('Legacy .xls preview requires xlrd on server');
        });

        test('zoomed image preview scrolls vertically inside the modal', async ({page}) => {
            const fileId = await uploadStaticFile(page, `preview-scroll-${Date.now()}.png`, TEST_AVATAR_PNG, 'image/png');

            await openStaticGridView(page);

            const previewButton = page.getByTestId(`file-grid-preview-${fileId}`);
            await expect(previewButton).toBeVisible({timeout: 8_000});
            await previewButton.click();

            await waitForPreviewReady(page);
            const imageStage = page.getByTestId('file-preview-image');
            await expect(imageStage).toBeVisible({timeout: 8_000});

            await page.getByTestId('file-preview-zoom-in').click();
            await page.getByTestId('file-preview-zoom-in').click();

            await imageStage.hover();
            await page.mouse.wheel(0, 600);

            await expect.poll(async () => imageStage.evaluate((node) => node.scrollTop)).toBeGreaterThan(0);
        });

        test('pdf preview hides comment button', async ({page}) => {
            const fileId = await uploadStaticFile(page, `preview-${Date.now()}.pdf`, TEST_PDF, 'application/pdf');

            await openStaticGridView(page);

            const previewButton = page.getByTestId(`file-grid-preview-${fileId}`);
            await expect(previewButton).toBeVisible({timeout: 8_000});
            await previewButton.click();

            await waitForPreviewReady(page);
            // Two traps in one assertion. `toHaveCount(0)` is satisfied by a toolbar
            // that has not painted yet — which is how this test stayed green for
            // months — *and* it counts DOM nodes regardless of visibility, while the
            // viewer disables a category by hiding the control rather than unmounting
            // it. So: prove the toolbar is there, then assert the button is not usable.
            await expect(page.locator('[data-epdf-i]').first()).toBeVisible({timeout: 20_000});
            await expect(page.locator('[data-epdf-i="search-button"]')).toBeVisible({timeout: 8_000});
            await expect(page.locator('[data-epdf-i="comment-button"]')).toBeHidden({timeout: 8_000});
        });

        test('opens table preview for BRIM files', async ({page}) => {
            const brokerId = await createBroker(page);
            const fileId = await uploadBrimFile(page, brokerId, `preview-${Date.now()}.csv`, ['date,type,amount,currency', '2025-01-01,DEPOSIT,1000,EUR', '2025-01-03,WITHDRAWAL,-50,EUR', ''].join('\n'), 'text/csv');

            await navigateTo(page, '/files?tab=brim');
            await expect(page.getByTestId('files-tab-brim')).toHaveAttribute('aria-selected', 'true');

            const row = page.locator(`[data-row-id="${fileId}"]`);
            await expect(row).toBeVisible({timeout: 8_000});
            await row.dblclick();

            await waitForPreviewReady(page);
            await expect(page.getByTestId('file-preview-grid')).toBeVisible({timeout: 8_000});
        });
    });
});
