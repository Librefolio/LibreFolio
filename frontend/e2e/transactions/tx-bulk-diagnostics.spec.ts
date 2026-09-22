/**
 * Transaction Bulk Diagnostics E2E Tests — E7/E8.
 *
 * E7: a real Generic CSV import lands in BulkModal, validates a real
 * balanceCashNegative issue for one broker/date/currency, and highlights all
 * four contributors without replacing destructive selection. Issue navigation
 * follows the current DATE sort across pages, not payload order.
 * E8: the same import path with out-of-order CSV dates proves that parse /
 * validate payload order stays in file order while the BulkModal DATE sort
 * only reorders the UI and never advances validateRuns.
 *
 * Every test owns its broker and uploaded file, uses the real import API,
 * and leaves nothing committed behind.
 */

import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForParseVerdict, waitForSettled, validateRuns} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const UI_TIMEOUT = 10_000;

type HttpResponse = {
    ok(): boolean;
    status(): number;
    text(): Promise<string>;
    json(): Promise<unknown>;
};

type Owned = {
    brokerIds: number[];
    fileIds: string[];
};

type ParseResponse = {
    file_id: string;
    broker_id: number;
    plugin_code: string;
    transactions: Array<{
        description: string;
        type: string;
        asset_id: number | null;
        quantity: number | string;
        cash: {code: string; amount: number | string} | null;
    }>;
    asset_mappings: unknown[];
    warnings: unknown[];
    field_todos: unknown[];
    validation_issues: unknown[];
};

type ValidateRequest = {
    creates?: Array<{
        description?: string;
        date?: string;
        type?: string;
        broker_id?: number;
        cash?: {code: string; amount: string | number} | null;
        link_uuid?: string | null;
    }>;
    updates?: unknown[];
    deletes?: unknown[];
};

type ValidateResponse = {
    committed?: boolean;
    issues?: Array<{code?: string; params?: Record<string, unknown>}>;
};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

async function goToTransactions(page: Page): Promise<void> {
    await navigateTo(page, '/transactions?page_size=200');
    await expect(page.getByTestId('tx-table')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('transactions-page'));
}

async function createOwnedBroker(page: Page, label: string): Promise<number> {
    const brokerName = `TX Bulk Diagnostics ${label} ${uniqueSuffix()}`;
    const response = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: [{name: brokerName, opened_at: '2020-01-01', default_import_plugin: 'broker_generic_csv'}]}), 'create owned broker');
    const created = response.results.find((item) => item.name === brokerName);
    if (!created?.success || typeof created.broker_id !== 'number') {
        throw new Error(`Broker creation failed: ${JSON.stringify(response)}`);
    }
    return created.broker_id;
}

async function uploadOwnedCsv(page: Page, brokerId: number, fileName: string, csv: string): Promise<string> {
    const upload = await jsonFrom<{file_id: string; target_broker_id: number}>(
        await page.request.post(`${API}/brokers/import/upload`, {
            multipart: {broker_id: String(brokerId), file: {name: fileName, mimeType: 'text/csv', buffer: Buffer.from(csv, 'utf8')}},
        }),
        'upload owned CSV',
    );
    expect(upload.target_broker_id).toBe(brokerId);
    return upload.file_id;
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
    for (const fileId of owned.fileIds) {
        await attempt(`file ${fileId}`, async () => {
            const result = await jsonFrom<{success: boolean; file_id: string}>(await page.request.delete(`${API}/brokers/import/files/${fileId}`), 'delete owned CSV');
            expect(result).toMatchObject({success: true, file_id: fileId});
        });
    }
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete owned broker');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
}

async function withOwnedCsv<T>(page: Page, label: string, csvFactory: (suffix: string) => string, run: (owned: {brokerId: number; fileId: string; fileName: string; suffix: string}) => Promise<T>): Promise<T> {
    const suffix = uniqueSuffix();
    const brokerId = await createOwnedBroker(page, label);
    const fileName = `tx-bulk-diagnostics-${label}-${suffix}.csv`;
    const owned: Owned = {brokerIds: [brokerId], fileIds: []};
    try {
        const fileId = await uploadOwnedCsv(page, brokerId, fileName, csvFactory(suffix));
        owned.fileIds.push(fileId);
        return await run({brokerId, fileId, fileName, suffix});
    } finally {
        await cleanupOwned(page, owned);
    }
}

async function openImportWizard(page: Page): Promise<void> {
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-step1')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('import-wizard-step1'));
}

async function parseOwnedFile(page: Page, fileId: string): Promise<ParseResponse> {
    await page.getByTestId('import-wizard-next').click();
    const step2 = page.getByTestId('import-wizard-step2');
    await expect(step2).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step2);

    const checkbox = page.getByTestId(`dt-row-checkbox-${fileId}`);
    await expect(checkbox, 'uploaded file must appear in the broker file table').toBeVisible({timeout: UI_TIMEOUT});
    await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked', {timeout: UI_TIMEOUT});
    await expect(page.getByTestId('import-wizard-parse')).toBeEnabled({timeout: UI_TIMEOUT});

    const parseResponsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === `${API}/brokers/import/files/${fileId}/parse` && response.request().method() === 'POST', {timeout: 30_000});
    await page.getByTestId('import-wizard-parse').click();
    const parseResponse = await parseResponsePromise;
    const parsed = await jsonFrom<ParseResponse>(parseResponse, 'parse owned CSV');
    await waitForParseVerdict(page);
    return parsed;
}

async function validateBulkNow(page: Page, root: Locator): Promise<{request: ValidateRequest; response: ValidateResponse}> {
    // FormModal sends the bulk context too. Arm only after it has closed and
    // BulkModal has settled, otherwise a form request can impersonate this one.
    await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: UI_TIMEOUT});
    await waitForSettled(root, 20_000);
    const before = await validateRuns(root);
    const requestPromise = page.waitForRequest((req) => new URL(req.url()).pathname === `${API}/transactions/validate` && req.method() === 'POST', {timeout: 15_000});
    await root.getByTestId('tx-bulk-validate-now').click();
    const sent = await requestPromise;
    const received = await sent.response();
    if (!received) throw new Error('Explicit bulk validation completed without an HTTP response');
    const response = await jsonFrom<ValidateResponse>(received, 'explicitly validate imported batch');
    await expect.poll(() => validateRuns(root), {timeout: 20_000}).toBeGreaterThan(before);
    await waitForSettled(root, 20_000);
    return {request: sent.postDataJSON() as ValidateRequest, response};
}

async function continueReviewAndImport(page: Page, parsed: ParseResponse): Promise<{root: Locator; request: ValidateRequest; response: ValidateResponse}> {
    // These synthetic cash-only files need neither asset resolution nor field
    // repair. Their owned empty broker cannot contain duplicate transactions.
    expect(parsed.asset_mappings).toEqual([]);
    expect(parsed.field_todos).toEqual([]);
    await page.getByTestId('import-wizard-continue').click();

    // The parsed response, not an instantaneous DOM probe, determines this gate.
    if (parsed.warnings.length > 0) {
        const warningConfirm = page.getByTestId('import-wizard-warning-confirm');
        await expect(warningConfirm).toBeVisible({timeout: UI_TIMEOUT});
        await warningConfirm.click();
        await expect(warningConfirm).toBeHidden({timeout: UI_TIMEOUT});
    }

    const step4 = page.getByTestId('import-wizard-step4');
    await expect(step4).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step4, 20_000);

    const importBtn = page.getByTestId('import-wizard-import');
    await expect(importBtn).toBeEnabled({timeout: UI_TIMEOUT});
    await importBtn.click();

    const root = page.getByTestId('tx-bulk-modal-root');
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 10_000});
    await expect(step4).toBeHidden({timeout: UI_TIMEOUT});
    await expect.poll(() => validateRuns(root), {timeout: 20_000}).toBeGreaterThan(0);
    const {request, response} = await validateBulkNow(page, root);
    return {root, request, response};
}

async function bulkRowDates(page: Page): Promise<string[]> {
    return page
        .getByTestId('tx-bulk-body')
        .getByTestId('tx-bulk-date')
        .evaluateAll((cells) =>
            cells.map((cell) => {
                const date = cell.getAttribute('data-date');
                if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new Error('Workspace date cell has no canonical date');
                return date;
            }),
        );
}

async function bulkRowIds(body: Locator): Promise<string[]> {
    return body.getByTestId('tx-bulk-date').evaluateAll((cells) =>
        cells.map((cell) => {
            const id = cell.getAttribute('data-row-id');
            if (!id) throw new Error('Workspace date cell has no stable row id');
            return id;
        }),
    );
}

function bulkRow(body: Locator, id: string): Locator {
    return body.locator(`tr[data-row-id="${id}"]`);
}

async function setDateSort(body: Locator, direction: 'asc' | 'desc'): Promise<void> {
    const header = body.getByTestId('dt-header-date');
    await expect(header).toBeVisible({timeout: UI_TIMEOUT});
    // DataTable cycles none → asc → desc → none. Read the declared state
    // instead of relying on two blind clicks or on BulkModal's default order.
    for (let attempt = 0; attempt < 3; attempt++) {
        const before = await header.getAttribute('data-sort');
        if (before === direction) break;
        await body.getByTestId('dt-sort-date').click();
        await expect(header).not.toHaveAttribute('data-sort', before ?? '');
    }
    await expect(header).toHaveAttribute('data-sort', direction);
}

async function goToBulkPage(body: Locator, pageNumber: number, expectedIds: string[]): Promise<void> {
    const input = body.getByTestId('data-table-pagination').getByRole('textbox');
    await expect(input).toBeVisible({timeout: UI_TIMEOUT});
    await input.fill(String(pageNumber));
    await input.press('Enter');
    await expect(input).toHaveValue(String(pageNumber));
    await expect.poll(() => bulkRowIds(body), {timeout: UI_TIMEOUT}).toEqual(expectedIds);
}

async function expectActionsScrollWithTable(body: Locator, rowId: string): Promise<void> {
    const action = body.getByTestId(`row-actions-${rowId}`);
    await expect(action).toBeAttached({timeout: UI_TIMEOUT});
    // The action header has no testid. Resolve its column from the published
    // action button of our OWN row, using native table cellIndex rather than a
    // CSS class, translated header, or "last header" guess.
    const geometry = async () =>
        action.evaluate((button) => {
            const cell = button.closest('td');
            const table = cell?.closest('table');
            const header = cell && table?.tHead?.rows.item(0)?.cells.item(cell.cellIndex);
            const scroller = table?.parentElement;
            if (!cell || !header || !scroller) throw new Error('Owned row action is missing its table/header/scroll container');
            return {
                headerLeft: header.getBoundingClientRect().left,
                cellLeft: cell.getBoundingClientRect().left,
                scrollLeft: scroller.scrollLeft,
                maxScroll: scroller.scrollWidth - scroller.clientWidth,
            };
        });
    const scroll = async (edge: 'start' | 'end') =>
        action.evaluate((button, target) => {
            const scroller = button.closest('table')?.parentElement;
            if (!scroller) throw new Error('Owned row action has no table scroll container');
            scroller.scrollLeft = target === 'start' ? 0 : scroller.scrollWidth - scroller.clientWidth;
        }, edge);

    await scroll('start');
    await expect.poll(async () => (await geometry()).scrollLeft).toBe(0);
    const start = await geometry();
    expect(start.maxScroll, 'real-browser regression requires horizontal overflow').toBeGreaterThan(100);
    await expect
        .poll(async () => {
            const current = await geometry();
            return Math.abs(current.headerLeft - current.cellLeft);
        })
        .toBeLessThan(1);
    await scroll('end');
    await expect
        .poll(async () => {
            const current = await geometry();
            return Math.abs(current.scrollLeft - current.maxScroll);
        })
        .toBeLessThan(1);
    await expect
        .poll(async () => {
            const current = await geometry();
            return Math.abs(current.headerLeft - current.cellLeft);
        })
        .toBeLessThan(1);
    const end = await geometry();
    expect(Math.abs(start.headerLeft - end.headerLeft - (end.scrollLeft - start.scrollLeft)), 'stickyActions=false: header moves with its action cells, not with the viewport edge').toBeLessThan(1);
    await scroll('start');
    await expect.poll(async () => (await geometry()).scrollLeft).toBe(0);
}

test.setTimeout(120_000);

test.describe('Transaction bulk diagnostics', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('E7: balanceCashNegative highlights all four contributors and navigates by current sort across pages without selecting them', async ({page}) => {
        // Only the original four USD rows contribute to the issue. Positive
        // EUR rows on either side force its roots across pages 2 and 3 in BOTH
        // directions, and give selection an unrelated row to preserve.
        const padding = [...Array.from({length: 8}, (_, i) => ({date: `2023-12-${24 + i}`, description: `Earlier EUR ${i}`})), ...Array.from({length: 8}, (_, i) => ({date: `2024-01-${String(6 + i).padStart(2, '0')}`, description: `Later EUR ${i}`}))];
        await withOwnedCsv(
            page,
            'cash-negative',
            (suffix) =>
                [
                    'date,type,quantity,amount,currency,asset,description',
                    `2024-01-04,WITHDRAWAL,0,-60,USD,,Withdrawal 60 ${suffix}`,
                    `2024-01-04,FEE,0,-10,USD,,Fee 10 ${suffix}`,
                    `2024-01-04,TAX,0,-5,USD,,Tax 5 ${suffix}`,
                    `2024-01-04,DEPOSIT,0,70,USD,,Deposit 70 ${suffix}`,
                    ...padding.map((row) => `${row.date},DEPOSIT,0,1,EUR,,${row.description} ${suffix}`),
                    '',
                ].join('\n'),
            async ({brokerId, fileId, suffix}) => {
                await goToTransactions(page);
                await openImportWizard(page);

                const parsed = await parseOwnedFile(page, fileId);
                expect(parsed.file_id).toBe(fileId);
                expect(parsed.broker_id).toBe(brokerId);
                expect(parsed.plugin_code).toBe('broker_generic_csv');
                const descriptions = [`Withdrawal 60 ${suffix}`, `Fee 10 ${suffix}`, `Tax 5 ${suffix}`, `Deposit 70 ${suffix}`, ...padding.map((row) => `${row.description} ${suffix}`)];
                expect(parsed.transactions).toHaveLength(descriptions.length);
                expect(parsed.transactions.map((tx) => tx.description)).toEqual(descriptions);
                const cashContributors = parsed.transactions.filter((tx) => tx.cash?.code === 'USD');
                expect(cashContributors).toHaveLength(4);
                expect(cashContributors.map((tx) => Number(tx.cash?.amount ?? NaN))).toEqual([-60, -10, -5, 70]);

                const {root, request, response} = await continueReviewAndImport(page, parsed);
                expect(response.committed).toBe(false);
                const balanceIssue = response.issues?.find((issue) => issue.code === 'balanceCashNegative');
                expect(balanceIssue, 'the validate response must report the cash-negative issue').toBeTruthy();
                expect(balanceIssue?.params).toMatchObject({brokerId, date: '2024-01-04', currency: 'USD'});

                expect(request.creates?.map((row) => row.description)).toEqual(descriptions);
                const payloadDates = ['2024-01-04', '2024-01-04', '2024-01-04', '2024-01-04', ...padding.map((row) => row.date)];
                expect(request.creates?.map((row) => row.date)).toEqual(payloadDates);

                const body = root.getByTestId('tx-bulk-body');
                await expect(body.getByTestId('tx-bulk-date')).toHaveCount(descriptions.length);
                await setDateSort(body, 'asc');
                await expect.poll(() => bulkRowDates(page)).toEqual([...payloadDates].sort());

                const idsByDescription = new Map<string, string>();
                for (const description of descriptions) {
                    const row = body.locator('tr[data-row-id]').filter({hasText: description});
                    await expect(row).toHaveCount(1);
                    const id = await row.getAttribute('data-row-id');
                    if (!id) throw new Error(`Missing stable workspace id for owned row ${description}`);
                    idsByDescription.set(description, id);
                    await expect(row.getByTestId('tx-bulk-date')).toHaveAttribute('data-row-id', id);
                    await expect(row.getByTestId('tx-bulk-date')).toHaveAttribute('data-partner-date', '');
                    await expect(row.getByTestId('tx-bulk-row-label')).toHaveAttribute('data-issue-highlighted', 'false');
                }
                const idFor = (description: string): string => {
                    const id = idsByDescription.get(description);
                    if (!id) throw new Error(`Owned row was not found before pagination: ${description}`);
                    return id;
                };
                const affectedIds = cashContributors.map((tx) => idFor(tx.description));
                const ascIds = await bulkRowIds(body);
                expect(new Set(ascIds)).toEqual(new Set(idsByDescription.values()));
                const selectedAffectedId = [...ascIds].reverse().find((id) => affectedIds.includes(id));
                if (!selectedAffectedId) throw new Error('No owned cash contributor available for selection');
                const unrelatedId = idFor(`Earlier EUR 0 ${suffix}`);
                const selectedIds = [unrelatedId, selectedAffectedId];
                for (const id of selectedIds) {
                    const checkbox = body.getByTestId(`dt-row-checkbox-${id}`);
                    await expect(checkbox).toHaveAttribute('data-state', 'unchecked');
                    await checkbox.click();
                    await expect(checkbox).toHaveAttribute('data-state', 'checked');
                }
                const beforeRuns = await validateRuns(root);
                const pagination = body.getByTestId('data-table-pagination');
                // Fresh browser context + this modal's defaultPageSize=25. Numeric
                // page-size labels are not translations; 20 owned roots fit one page.
                await pagination.getByTestId('pagination-size-trigger').click({timeout: UI_TIMEOUT});
                await pagination.getByTestId('pagination-size-option-5').click({timeout: UI_TIMEOUT});
                await expect(pagination.getByTestId('pagination-size-menu')).toBeHidden();
                await expect.poll(() => bulkRowIds(body)).toEqual(ascIds.slice(0, 5));

                const issueButton = root.getByTestId('tx-bulk-balance-rows');
                await expect(issueButton).toHaveCount(1);
                await expect(issueButton).toBeEnabled();
                for (const direction of ['asc', 'desc'] as const) {
                    await setDateSort(body, direction);
                    const orderedIds = direction === 'asc' ? ascIds : [...ascIds].reverse();
                    const firstAffected = orderedIds.find((id) => affectedIds.includes(id));
                    if (!firstAffected) throw new Error('No affected root in the owned workspace');
                    const targetPage = Math.floor(orderedIds.indexOf(firstAffected) / 5) + 1;
                    expect(targetPage, 'fixture must require off-page issue navigation').toBe(2);
                    await goToBulkPage(body, 1, orderedIds.slice(0, 5));
                    await expect(body.locator('[data-testid="tx-bulk-date"][data-date="2024-01-04"]')).toHaveCount(0);
                    await issueButton.click();
                    await expect(pagination.getByRole('textbox')).toHaveValue(String(targetPage));
                    await expect.poll(() => bulkRowIds(body)).toEqual(orderedIds.slice(5, 10));
                    await expect(bulkRow(body, firstAffected)).toHaveAttribute('data-highlighted', 'true');
                    await expect(bulkRow(body, firstAffected).getByTestId('tx-bulk-row-label')).toHaveAttribute('data-issue-highlighted', 'true');
                    // The mounted grid and highlighted target give this absence
                    // assertion a presence barrier: no replacement detail drawer.
                    await expect(root.getByTestId('tx-bulk-issue-focus')).toHaveCount(0);

                    const highlighted: string[] = [];
                    const selected: string[] = [];
                    const visited: string[] = [];
                    for (let pageNumber = 1; pageNumber <= 4; pageNumber++) {
                        const pageIds = orderedIds.slice((pageNumber - 1) * 5, pageNumber * 5);
                        await goToBulkPage(body, pageNumber, pageIds);
                        for (const id of pageIds) {
                            const row = bulkRow(body, id);
                            const label = row.getByTestId('tx-bulk-row-label');
                            await expect(label).toHaveAttribute('data-row-id', id);
                            await expect(label).toHaveText(String(orderedIds.indexOf(id) + 1));
                            await expect(label).toHaveAttribute('data-issue-highlighted', String(affectedIds.includes(id)));
                            await expect(row).toHaveAttribute('data-selected', String(selectedIds.includes(id)));
                            await expect(row.getByTestId(`dt-row-checkbox-${id}`)).toHaveAttribute('data-state', selectedIds.includes(id) ? 'checked' : 'unchecked');
                            visited.push(id);
                        }
                        highlighted.push(...(await body.locator('[data-testid="tx-bulk-row-label"][data-issue-highlighted="true"]').evaluateAll((labels) => labels.map((label) => label.getAttribute('data-row-id')!))));
                        selected.push(...(await body.locator('tr[data-row-id][data-selected="true"]').evaluateAll((rows) => rows.map((row) => row.getAttribute('data-row-id')!))));
                    }
                    expect(visited, 'all owned roots must be found in 4 pages').toEqual(orderedIds);
                    expect(new Set(highlighted), 'complete issue group survives page changes').toEqual(new Set(affectedIds));
                    expect(new Set(selected), 'diagnostics must never replace destructive selection').toEqual(new Set(selectedIds));
                    await expect(root).toHaveAttribute('data-busy', 'false');
                    expect(await validateRuns(root), 'sorting, issue navigation and selection do not validate').toBe(beforeRuns);
                }

                // The selected contributor is LAST in ASC among the four, not the
                // first diagnostic row. Current filtered order must win.
                await setDateSort(body, 'asc');
                await goToBulkPage(body, 1, ascIds.slice(0, 5));
                const selectedOnly = body.getByTestId('dt-show-selected-only');
                await expect(selectedOnly).toHaveAttribute('data-state', 'off');
                await selectedOnly.click();
                await expect(selectedOnly).toHaveAttribute('data-state', 'on');
                await expect.poll(() => bulkRowIds(body)).toEqual([unrelatedId, selectedAffectedId]);
                await issueButton.click();
                await expect(bulkRow(body, selectedAffectedId)).toHaveAttribute('data-highlighted', 'true');
                await expect(bulkRow(body, selectedAffectedId).getByTestId('tx-bulk-row-label')).toHaveAttribute('data-issue-highlighted', 'true');
                await expect(bulkRow(body, unrelatedId).getByTestId('tx-bulk-row-label')).toHaveAttribute('data-issue-highlighted', 'false');
                await expect(selectedOnly).toHaveAttribute('data-state', 'on');

                // Hide every contributor by deselecting only the owned affected
                // row. Keep the unrelated selection, so the filter stays active.
                await body.getByTestId(`dt-row-checkbox-${selectedAffectedId}`).click();
                await expect.poll(() => bulkRowIds(body)).toEqual([unrelatedId]);
                await expect(selectedOnly).toHaveAttribute('data-state', 'on');
                const since = await eventSeq(page);
                await issueButton.click();
                const hidden = await waitForEvent(page, 'tx.bulk.issue.rows-hidden', {since});
                expect(hidden.detail?.code).toBe('balanceCashNegative');
                expect(new Set(hidden.detail?.rowIds as string[])).toEqual(new Set(affectedIds));
                await expect(page.getByTestId('toast-warning')).toBeVisible({timeout: UI_TIMEOUT});
                await expect(selectedOnly).toHaveAttribute('data-state', 'on');
                await expect.poll(() => bulkRowIds(body)).toEqual([unrelatedId]);
                await expect(bulkRow(body, unrelatedId)).toHaveAttribute('data-selected', 'true');
                await expect(root.getByTestId('tx-bulk-issue-focus')).toHaveCount(0);

                await selectedOnly.click();
                await expect(selectedOnly).toHaveAttribute('data-state', 'off');
                for (let pageNumber = 1; pageNumber <= 4; pageNumber++) {
                    const pageIds = ascIds.slice((pageNumber - 1) * 5, pageNumber * 5);
                    await goToBulkPage(body, pageNumber, pageIds);
                    for (const id of pageIds) {
                        const row = bulkRow(body, id);
                        await expect(row.getByTestId('tx-bulk-row-label')).toHaveAttribute('data-issue-highlighted', String(affectedIds.includes(id)));
                        await expect(row).toHaveAttribute('data-selected', String(id === unrelatedId));
                    }
                }
                const revalidated = await validateBulkNow(page, root);
                expect(revalidated.request).toEqual(request);
                expect(revalidated.response.committed).toBe(false);
            },
        );
    });

    test('E8: DATE sort reorders only the UI, not the payload', async ({page}) => {
        const csvRows = [
            {date: '2024-01-05', amount: '5', description: 'Later deposit'},
            {date: '2024-01-02', amount: '2', description: 'Early deposit'},
            {date: '2024-01-04', amount: '4', description: 'Middle deposit'},
            {date: '2024-01-03', amount: '3', description: 'Near deposit'},
        ];
        const expectedParseOrder = csvRows.map((row) => row.description);
        const expectedAscDates = [...csvRows.map((row) => row.date)].sort();
        const expectedDescDates = [...expectedAscDates].reverse();
        const manualDate = '2024-01-01';

        await withOwnedCsv(
            page,
            'sort-order',
            (suffix) => ['date,type,quantity,amount,currency,asset,description', ...csvRows.map((row) => `${row.date},DEPOSIT,0,${row.amount},USD,,${row.description} ${suffix}`), ''].join('\n'),
            async ({brokerId, fileId, suffix}) => {
                await goToTransactions(page);
                await openImportWizard(page);

                const parsed = await parseOwnedFile(page, fileId);
                expect(parsed.file_id).toBe(fileId);
                expect(parsed.broker_id).toBe(brokerId);
                expect(parsed.transactions.map((tx) => tx.description)).toEqual(expectedParseOrder.map((text) => `${text} ${suffix}`));

                const {root, request, response} = await continueReviewAndImport(page, parsed);
                expect(response.committed).toBe(false);
                expect(request.creates?.map((row) => row.description)).toEqual(expectedParseOrder.map((text) => `${text} ${suffix}`));
                expect(request.creates?.map((row) => row.date)).toEqual(csvRows.map((row) => row.date));

                await expect.poll(() => bulkRowDates(page)).toEqual(expectedAscDates);
                const body = root.getByTestId('tx-bulk-body');
                const originalIds = await bulkRowIds(body);
                const selectedDeposit = body.locator('tr[data-row-id]').filter({hasText: `Early deposit ${suffix}`});
                await expect(selectedDeposit).toHaveCount(1);
                const selectedDepositId = await selectedDeposit.getAttribute('data-row-id');
                if (!selectedDepositId) throw new Error('Owned early deposit has no stable workspace id');
                await expectActionsScrollWithTable(body, selectedDepositId);
                const selectedCheckbox = body.getByTestId(`dt-row-checkbox-${selectedDepositId}`);
                await expect(selectedCheckbox).toHaveAttribute('data-state', 'unchecked');
                await selectedCheckbox.click();
                await expect(selectedCheckbox).toHaveAttribute('data-state', 'checked');
                const beforeRuns = await validateRuns(root);
                expect(beforeRuns).toBeGreaterThan(0);

                await setDateSort(body, 'desc');
                await expect.poll(() => bulkRowDates(page)).toEqual(expectedDescDates);
                await expect.poll(() => bulkRowIds(body)).toEqual([...originalIds].reverse());
                await expect(selectedCheckbox).toHaveAttribute('data-state', 'checked');
                expect(await validateRuns(root)).toBe(beforeRuns);

                await setDateSort(body, 'asc');
                await expect.poll(() => bulkRowDates(page)).toEqual(expectedAscDates);
                await expect.poll(() => bulkRowIds(body)).toEqual(originalIds);
                await expect(selectedCheckbox).toHaveAttribute('data-state', 'checked');
                expect(await validateRuns(root)).toBe(beforeRuns);
                await expect(root).toHaveAttribute('data-busy', 'false');

                const formModal = page.getByTestId('tx-form-modal');
                const bulkDates = page.getByTestId('tx-bulk-body').getByTestId('tx-bulk-date');
                const openSearchSelect = async (trigger: Locator): Promise<void> => {
                    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
                    await expect(trigger).toHaveAttribute('aria-expanded', 'true');
                };
                const optionsClosed = async (): Promise<void> => {
                    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: UI_TIMEOUT});
                };
                const selectCurrency = async (cashTestid: string, code: string): Promise<void> => {
                    const wrap = page.getByTestId(cashTestid);
                    await openSearchSelect(wrap.getByRole('combobox'));
                    const listbox = page.getByRole('listbox');
                    await expect(listbox).toBeVisible({timeout: UI_TIMEOUT});
                    await expect(listbox).toHaveAttribute('aria-busy', 'false', {timeout: UI_TIMEOUT});
                    const searchInput = wrap.getByRole('combobox').getByRole('textbox');
                    await expect(searchInput).toBeVisible({timeout: UI_TIMEOUT});
                    await searchInput.fill(code);
                    const option = page.getByTestId(`search-select-option-${code}`);
                    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
                    await option.click();
                    await optionsClosed();
                };
                const setDualDate = async (panel: Locator, iso: string): Promise<void> => {
                    const input = panel.getByTestId('single-date-picker-root').getByRole('textbox');
                    await expect(input).toBeVisible({timeout: UI_TIMEOUT});
                    await input.fill(iso);
                    await input.press('Enter');
                    await expect(input).toHaveValue(iso);
                };

                await page.getByTestId('tx-bulk-add-row').click();
                await expect(formModal).toBeVisible({timeout: UI_TIMEOUT});
                await openSearchSelect(page.getByTestId('tx-form-broker-wrap').getByRole('combobox'));
                await expect(page.getByTestId(`search-select-option-${brokerId}`)).toBeVisible({timeout: UI_TIMEOUT});
                await page.getByTestId(`search-select-option-${brokerId}`).click();
                await optionsClosed();
                await openSearchSelect(page.getByTestId('tx-form-type').getByRole('combobox'));
                await expect(page.getByTestId('search-select-option-FX_CONVERSION')).toBeVisible({timeout: UI_TIMEOUT});
                await page.getByTestId('search-select-option-FX_CONVERSION').click();
                await optionsClosed();

                await selectCurrency('tx-form-cash-from', 'EUR');
                await selectCurrency('tx-form-cash-to', 'USD');

                const cashFromAmount = page.getByTestId('tx-form-cash-from-amount');
                const cashToAmount = page.getByTestId('tx-form-cash-to-amount');
                await expect(cashFromAmount).toBeVisible({timeout: UI_TIMEOUT});
                await expect(cashToAmount).toBeVisible({timeout: UI_TIMEOUT});
                await cashFromAmount.fill('1');
                await cashFromAmount.press('Tab');
                await cashToAmount.fill('1.1');
                await cashToAmount.press('Tab');
                await expect(cashFromAmount).toHaveValue('1');
                await expect(cashToAmount).toHaveValue('1.1');

                await setDualDate(page.getByTestId('tx-form-dual-from'), manualDate);
                await setDualDate(page.getByTestId('tx-form-dual-to'), manualDate);

                await expect(page.getByTestId('tx-form-save')).toBeEnabled({timeout: UI_TIMEOUT});
                await page.getByTestId('tx-form-save').click();
                await expect(formModal).not.toBeVisible({timeout: UI_TIMEOUT});
                await waitForSettled(root, 20_000);

                const {request: appendedValidate, response: appendedResponse} = await validateBulkNow(page, root);
                expect(appendedResponse.committed).toBe(false);
                expect(appendedValidate.creates).toHaveLength(6);
                expect(appendedValidate.creates?.slice(0, 4)).toEqual(request.creates);
                const pairPayload = appendedValidate.creates?.slice(-2);
                expect(pairPayload?.map((row) => row.date)).toEqual([manualDate, manualDate]);
                expect(pairPayload?.map((row) => row.type)).toEqual(['FX_CONVERSION', 'FX_CONVERSION']);
                expect(pairPayload?.map((row) => row.broker_id)).toEqual([brokerId, brokerId]);
                expect(pairPayload?.map((row) => row.cash?.code)).toEqual(['EUR', 'USD']);
                expect(pairPayload?.map((row) => Number(row.cash?.amount))).toEqual([-1, 1.1]);
                const linkIds = pairPayload?.map((row) => row.link_uuid);
                expect(linkIds?.every((id) => typeof id === 'string' && id.length > 0)).toBe(true);
                expect(new Set(linkIds).size, 'both payload legs retain a single shared pair identity').toBe(1);
                expect(appendedResponse.issues?.find((issue) => issue.code === 'balanceCashNegative' && issue.params?.currency === 'EUR')?.params).toMatchObject({
                    brokerId,
                    currency: 'EUR',
                    date: manualDate,
                });

                await expect(bulkDates).toHaveCount(5, {timeout: UI_TIMEOUT});
                await expect.poll(() => bulkRowDates(page)).toEqual([manualDate, ...expectedAscDates]);
                // Identify the pair by the two dates just entered, never by an
                // unfiltered first row. Two wire legs must stay one workspace root.
                const pairDate = body.locator(`[data-testid="tx-bulk-date"][data-date="${manualDate}"][data-partner-date="${manualDate}"]`);
                await expect(pairDate).toHaveCount(1);
                const pairId = await pairDate.getAttribute('data-row-id');
                if (!pairId) throw new Error('Backdated FX pair has no stable workspace root id');
                const pairRow = bulkRow(body, pairId);
                const pairLabel = pairRow.getByTestId('tx-bulk-row-label');
                const afterAppendRuns = await validateRuns(root);
                const issueButton = root.getByTestId('tx-bulk-balance-rows');
                await expect(issueButton).toHaveCount(1);
                await expect(issueButton).toBeEnabled();

                for (const direction of ['desc', 'asc'] as const) {
                    await setDateSort(body, direction);
                    const expectedIds = direction === 'asc' ? [pairId, ...originalIds] : [...originalIds].reverse().concat(pairId);
                    await expect.poll(() => bulkRowIds(body)).toEqual(expectedIds);
                    await expect.poll(() => bulkRowDates(page)).toEqual(direction === 'asc' ? [manualDate, ...expectedAscDates] : [...expectedDescDates, manualDate]);
                    const position = direction === 'asc' ? 1 : 5;
                    // Only numeric workspace labels are asserted: the surrounding
                    // From/To copy is translated. a/b remain visual, not payload ids.
                    await expect(pairLabel).toContainText(`${position}a`);
                    await expect(pairLabel).toContainText(`${position}b`);
                    await issueButton.click();
                    await expect(pairRow).toHaveAttribute('data-highlighted', 'true');
                    await expect(pairLabel).toHaveAttribute('data-issue-highlighted', 'true');
                    await expect(pairDate).toHaveAttribute('data-row-id', pairId);
                    await expect(pairDate).toHaveAttribute('data-date', manualDate);
                    await expect(pairDate).toHaveAttribute('data-partner-date', manualDate);
                    await expect(root.getByTestId('tx-bulk-issue-focus')).toHaveCount(0);
                    for (const id of expectedIds) {
                        const row = bulkRow(body, id);
                        await expect(row).toHaveAttribute('data-selected', String(id === selectedDepositId));
                        await expect(row.getByTestId('tx-bulk-row-label')).toHaveAttribute('data-issue-highlighted', String(id === pairId));
                    }
                    expect(await validateRuns(root), 'pair sorting and diagnostics do not revalidate the draft').toBe(afterAppendRuns);
                }
                const revalidated = await validateBulkNow(page, root);
                expect(revalidated.request, 'visual a/b labels, diagnostics and selection cannot reorder or unpair wire operations').toEqual(appendedValidate);
                expect(revalidated.response.committed).toBe(false);
                await expect(root).toHaveAttribute('data-busy', 'false');
            },
        );
    });
});
