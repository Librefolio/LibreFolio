/**
 * R1 Step2 file pagination and folding. Every case owns two brokers and seven
 * inline synthetic Generic CSV reports. No parse/import/commit, shared fixture
 * mutation, global row count, real financial snapshot, or external provider I/O.
 *
 * Two entry paths: existing files expand both owned brokers; successful Step1
 * uploads expand only their broker and preselect those uploads. Individual row
 * selection must survive paging and destruction/recreation of the folded table.
 */
import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const TEST_PORT = process.env.TEST_PORT || '6041';
const UI_TIMEOUT = 10_000;
type OwnedFile = {file_id: string; filename: string; target_broker_id: number};
type Owned = {suffix: string; brokerIds: number[]; fileIds: Set<string>};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

async function listOwnedFiles(page: Page, owned: Owned): Promise<OwnedFile[]> {
    if (owned.brokerIds.length === 0) return [];
    const query = new URLSearchParams();
    // FastAPI expects repeated broker_ids, not a comma-joined value.
    for (const id of owned.brokerIds) query.append('broker_ids', String(id));
    const files = await jsonFrom<OwnedFile[]>(await page.request.get(`${API}/brokers/import/files?${query}`), 'list files on owned brokers');
    expect(Array.isArray(files), 'BRIM list response is an array').toBe(true);
    for (const file of files) {
        expect(owned.brokerIds).toContain(file.target_broker_id);
        owned.fileIds.add(file.file_id);
    }
    return files;
}

async function cleanupOwned(page: Page, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    await attempt('unmount wizard', async () => {
        await page.goto('about:blank');
    });
    // Also recover Step1 uploads if a UI assertion failed before ids were read.
    // These brokers were created by this test, not discovered from a global delta.
    await attempt('discover owned uploads', async () => {
        await listOwnedFiles(page, owned);
    });
    for (const id of owned.fileIds) {
        await attempt(`delete file ${id}`, async () => {
            const result = await jsonFrom<{success: boolean; file_id: string}>(await page.request.delete(`${API}/brokers/import/files/${id}`), 'delete owned report');
            expect(result).toMatchObject({success: true, file_id: id});
        });
    }
    for (const id of owned.brokerIds) {
        await attempt(`delete broker ${id}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${id}&force=true`), 'delete owned broker');
            expect(result.results.find((item) => item.id === id)?.success).toBe(true);
        });
    }
    expect(failures, 'cleanup attempts every owned entity even if an earlier deletion failed').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use, testInfo) => {
        const baseURL = testInfo.project.use.baseURL;
        if (!baseURL || new URL(baseURL).port !== TEST_PORT || !['localhost', '127.0.0.1'].includes(new URL(baseURL).hostname)) {
            throw new Error(`File-selection regressions require the shared local test backend on port ${TEST_PORT}`);
        }
        const origin = new URL(baseURL).origin;
        await page.route('**/*', async (route) => {
            const url = new URL(route.request().url());
            if (['http:', 'https:'].includes(url.protocol) && url.origin !== origin) {
                await route.abort('blockedbyclient');
                return;
            }
            await route.fallback();
        });
        const owned: Owned = {suffix: `w${testInfo.workerIndex}-${uniqueSuffix()}`, brokerIds: [], fileIds: new Set()};
        try {
            await login(page, TEST_USER);
            await use(owned);
        } finally {
            await cleanupOwned(page, owned);
        }
    },
});

test.setTimeout(90_000);

async function createBroker(page: Page, owned: Owned, label: string): Promise<number> {
    const name = `File selection ${label} ${owned.suffix}`;
    const result = await jsonFrom<{results: Array<{name: string; broker_id: number | null; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2020-01-01', default_import_plugin: 'broker_generic_csv'}]}), 'create owned broker');
    const broker = result.results.find((item) => item.name === name);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Owned broker creation failed: ${JSON.stringify(result)}`);
    return broker.broker_id;
}

function csvFile(owned: Owned, label: string) {
    return {
        name: `file-selection-${label}-${owned.suffix}.csv`,
        mimeType: 'text/csv',
        buffer: Buffer.from(['date,type,quantity,amount,currency,asset,description', `2024-01-02,DEPOSIT,0,10,EUR,,Synthetic selection ${label} ${owned.suffix}`, ''].join('\n'), 'utf8'),
    };
}

async function uploadFile(page: Page, owned: Owned, brokerId: number, label: string): Promise<OwnedFile> {
    const file = csvFile(owned, label);
    const uploaded = await jsonFrom<OwnedFile>(await page.request.post(`${API}/brokers/import/upload`, {multipart: {broker_id: String(brokerId), file}}), 'upload owned synthetic CSV');
    owned.fileIds.add(uploaded.file_id);
    expect(uploaded).toMatchObject({filename: file.name, target_broker_id: brokerId});
    return uploaded;
}

async function openWizard(page: Page): Promise<Locator> {
    await navigateTo(page, '/transactions');
    await expect(page.getByTestId('transactions-page')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('transactions-page'));
    await page.getByTestId('tx-import-button').click();
    const step1 = page.getByTestId('import-wizard-step1');
    await expect(step1).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step1);
    return step1;
}

async function enterStep2(page: Page): Promise<Locator> {
    await expect(page.getByTestId('import-wizard-next')).toBeEnabled({timeout: UI_TIMEOUT});
    await page.getByTestId('import-wizard-next').click();
    const step2 = page.getByTestId('import-wizard-step2');
    await expect(step2).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step2);
    return step2;
}

function brokerPanel(step2: Locator, id: number): Locator {
    return step2.getByTestId(`import-wizard-broker-files-${id}`);
}

async function setExpanded(panel: Locator, brokerId: number, expanded: boolean) {
    const toggle = panel.getByTestId(`import-wizard-broker-toggle-${brokerId}`);
    await expect(toggle).toBeVisible({timeout: UI_TIMEOUT});
    if ((await toggle.getAttribute('aria-expanded')) !== String(expanded)) await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', String(expanded), {timeout: UI_TIMEOUT});
    if (expanded) {
        await expect(panel.getByRole('table')).toBeVisible({timeout: UI_TIMEOUT});
    } else {
        await expect(panel.getByRole('table')).toBeHidden({timeout: UI_TIMEOUT});
    }
}

/**
 * Six files => two pages of 5 and 1. Counts concern this owned broker only.
 * Row ids, not filename sorting or upload completion order, identify the files.
 * Called on a fresh/reopened table: DataTable initializes pageIndex to zero.
 */
async function walkOwnedPages(panel: Locator, files: OwnedFile[], visit: (checkbox: Locator, fileId: string) => Promise<void>) {
    const knownIds = new Set(files.map((file) => file.file_id));
    const seen = new Set<string>();
    const pagination = panel.getByTestId('data-table-pagination');
    await expect(pagination).toBeVisible({timeout: UI_TIMEOUT});
    await expect(pagination.getByTestId('pagination-prev')).toBeDisabled();
    const pages = Math.ceil(files.length / 5);
    for (let pageIndex = 0; pageIndex < pages; pageIndex++) {
        const rows = panel.locator('tbody tr[data-row-id]');
        await expect(rows).toHaveCount(Math.min(5, files.length - pageIndex * 5), {timeout: UI_TIMEOUT});
        const ids = await rows.evaluateAll((elements) => elements.map((row) => row.getAttribute('data-row-id')));
        for (const id of ids) {
            if (id === null || !knownIds.has(id) || seen.has(id)) throw new Error(`Unexpected/repeated owned row ${id} on page ${pageIndex + 1}`);
            seen.add(id);
            const checkbox = panel.getByTestId(`dt-row-checkbox-${id}`);
            await expect(checkbox).toBeVisible({timeout: UI_TIMEOUT});
            await visit(checkbox, id);
        }
        const next = pagination.getByTestId('pagination-next');
        if (pageIndex + 1 < pages) {
            await expect(next).toBeEnabled();
            await next.click();
            await expect(pagination.getByTestId('pagination-prev')).toBeEnabled();
        } else {
            await expect(next).toBeDisabled();
        }
    }
    expect([...seen].sort(), `owned file not found in ${pages} pages`).toEqual([...knownIds].sort());
}

test('existing files: both brokers expand and cross-page selection survives folding independently', async ({page, owned}) => {
    const mainId = await createBroker(page, owned, 'main');
    const controlId = await createBroker(page, owned, 'control');
    const files: OwnedFile[] = [];
    for (const label of ['a', 'b', 'c', 'd', 'e', 'f']) files.push(await uploadFile(page, owned, mainId, label));
    const controlFile = await uploadFile(page, owned, controlId, 'control');
    await openWizard(page);
    const step2 = await enterStep2(page);
    const main = brokerPanel(step2, mainId);
    const control = brokerPanel(step2, controlId);
    await expect(main.getByTestId(`import-wizard-broker-toggle-${mainId}`)).toHaveAttribute('aria-expanded', 'true');
    await expect(control.getByTestId(`import-wizard-broker-toggle-${controlId}`)).toHaveAttribute('aria-expanded', 'true');
    const controlCheckbox = control.getByTestId(`dt-row-checkbox-${controlFile.file_id}`);
    await expect(controlCheckbox).toBeVisible({timeout: UI_TIMEOUT});
    await expect(control.locator('tbody tr[data-row-id]')).toHaveCount(1);
    await expect(control.getByTestId('data-table-pagination')).toHaveCount(0);
    await expect(controlCheckbox).toHaveAttribute('data-state', 'unchecked');
    await controlCheckbox.click();
    await expect(controlCheckbox).toHaveAttribute('data-state', 'checked');

    await walkOwnedPages(main, files, async (checkbox) => {
        await expect(checkbox).toHaveAttribute('data-state', 'unchecked');
        await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    });
    await setExpanded(main, mainId, false);
    await expect(controlCheckbox).toHaveAttribute('data-state', 'checked');
    await setExpanded(main, mainId, true);
    await walkOwnedPages(main, files, async (checkbox) => {
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    });
    await setExpanded(control, controlId, false);
    await setExpanded(control, controlId, true);
    await expect(controlCheckbox).toHaveAttribute('data-state', 'checked');
    await expect(page.getByTestId('import-wizard-parse')).toBeEnabled();
});

test('Step1 uploads: only their broker expands and a partial selection survives two pages and reopen', async ({page, owned}) => {
    const mainId = await createBroker(page, owned, 'uploaded');
    const controlId = await createBroker(page, owned, 'existing-control');
    const controlFile = await uploadFile(page, owned, controlId, 'control');
    const uploads = ['a', 'b', 'c', 'd', 'e', 'f'].map((label) => csvFile(owned, label));
    const step1 = await openWizard(page);
    await step1.getByTestId('file-input').setInputFiles(uploads);
    await expect(step1.locator('tbody tr[data-row-id]')).toHaveCount(uploads.length, {timeout: UI_TIMEOUT});
    await optionsClosed(page);
    await step1.getByTestId('import-wizard-step1-broker-select').getByRole('combobox').click();
    const option = page.getByTestId(`search-select-option-${mainId}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    const step2 = await enterStep2(page);
    const files = (await listOwnedFiles(page, owned)).filter((file) => file.target_broker_id === mainId);
    expect(files.map((file) => file.filename).sort()).toEqual(uploads.map((file) => file.name).sort());
    const main = brokerPanel(step2, mainId);
    const control = brokerPanel(step2, controlId);
    await expect(main.getByTestId(`import-wizard-broker-toggle-${mainId}`)).toHaveAttribute('aria-expanded', 'true');
    await expect(control.getByTestId(`import-wizard-broker-toggle-${controlId}`)).toBeVisible();
    await expect(control.getByTestId(`import-wizard-broker-toggle-${controlId}`)).toHaveAttribute('aria-expanded', 'false');
    await expect(control.getByTestId(`dt-row-checkbox-${controlFile.file_id}`)).toBeHidden();
    await setExpanded(control, controlId, true);
    await expect(control.getByTestId(`dt-row-checkbox-${controlFile.file_id}`)).toHaveAttribute('data-state', 'unchecked');

    const deselected = files.find((file) => file.filename === csvFile(owned, 'a').name);
    if (!deselected) throw new Error('Owned Step1 file a is missing from its broker');
    await walkOwnedPages(main, files, async (checkbox, id) => {
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
        if (id === deselected.file_id) {
            await checkbox.click();
            await expect(checkbox).toHaveAttribute('data-state', 'unchecked');
        }
    });
    await setExpanded(main, mainId, false);
    await setExpanded(main, mainId, true);
    await walkOwnedPages(main, files, async (checkbox, id) => {
        await expect(checkbox).toHaveAttribute('data-state', id === deselected.file_id ? 'unchecked' : 'checked');
    });
    await expect(control.getByTestId(`dt-row-checkbox-${controlFile.file_id}`)).toHaveAttribute('data-state', 'unchecked');
    await expect(page.getByTestId('import-wizard-parse')).toBeEnabled();
});
