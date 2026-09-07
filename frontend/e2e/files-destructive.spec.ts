/**
 * Files page — the destructive routes.
 *
 * `files/+page.svelte` has two delete paths that write to shared, global state:
 * `deleteFile` (single, static + BRIM) and `handleBulkDeleteFiles` (the page-level
 * SelectionBar), plus the `file.delete.failed` error branch. Uploaded files live
 * in the shared uploads dir and every files spec reads them, so a spec that
 * deletes a *mock* file becomes the cause of a red somewhere else entirely. These
 * were deliberately left uncovered until they could be done safely.
 *
 * The strategy here is disposable rows, never mock rows: each test uploads its own
 * file(s) (unique marker) and deletes *those*. The mock baseline is never touched,
 * so nothing needs resurrecting and the database is left exactly as found. The
 * `afterAll` repopulate is a net, not the plan — see `fixtures/mock-restore.ts`.
 */
import {expect, test, type APIRequestContext, type Page} from './fixtures/playwright';
import {login, navigateTo} from './fixtures/auth-helpers';
import {TEST_USER} from './fixtures/test-users';
import {eventSeq, waitForEvent, waitForSettled} from './fixtures/app-events';
import {uniqueSuffix} from './fixtures/unique';
import {apiLogin, REPOPULATE_ALLOWED, repopulateMockData} from './fixtures/mock-restore';

// ─────────────────────────────────────────────────────────────────────────────
// Serial, and here is exactly what is shared — the frontend twin of the backend's
// `exclusive_because`. This file uploads disposable files and creates disposable
// brokers, then walks the delete routes on them. Files are a *global* resource
// (shared uploads dir + a BRIM list with no per-test scoping), and the tests hand
// their disposable rows down the sequence — upload here, assert the delete there.
// The file owns those rows start to finish; a sibling deleting one mid-assertion,
// or the `afterAll` net firing while another worker is mid-test, would corrupt the
// run. That is the whole reason it opts out of `fullyParallel`.
// ─────────────────────────────────────────────────────────────────────────────
test.describe.configure({mode: 'serial'});

const API = '/api/v1';
const TEST_PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/a3cAAAAASUVORK5CYII=', 'base64');
const TEST_CSV = 'Date,Description,Amount\n2024-01-02,Disposable BRIM row,10.00\n';

/** Every disposable id this file created, deleted idempotently in `afterAll`. */
const createdStatic: string[] = [];
const createdBrim: string[] = [];
const createdBrokers: number[] = [];

/** Mock static-file ids present before any test ran — the net's baseline. */
let mockStaticBaseline: string[] = [];

async function uploadStaticFile(page: Page, label: string): Promise<string> {
    const res = await page.request.post(`${API}/uploads`, {
        multipart: {file: {name: `p3-static-${label}.png`, mimeType: 'image/png', buffer: TEST_PNG}},
    });
    expect(res.ok(), `upload static ${label}: ${res.status()}`).toBeTruthy();
    const id = ((await res.json()) as {file: {id: string}}).file.id;
    createdStatic.push(id);
    return id;
}

async function createBroker(page: Page, label: string): Promise<number> {
    const res = await page.request.post(`${API}/brokers`, {
        data: [{name: `P3 Broker ${label}`, allow_cash_overdraft: true}],
    });
    expect(res.ok(), `create broker ${label}: ${res.status()}`).toBeTruthy();
    const id = ((await res.json()) as {results: Array<{broker_id: number}>}).results[0].broker_id;
    createdBrokers.push(id);
    return id;
}

async function uploadBrimFile(page: Page, brokerId: number, label: string): Promise<string> {
    const res = await page.request.post(`${API}/brokers/import/upload`, {
        multipart: {broker_id: String(brokerId), file: {name: `p3-brim-${label}.csv`, mimeType: 'text/csv', buffer: Buffer.from(TEST_CSV, 'utf-8')}},
    });
    expect(res.ok(), `upload brim ${label}: ${res.status()}`).toBeTruthy();
    const id = ((await res.json()) as {file_id: string}).file_id;
    createdBrim.push(id);
    return id;
}

/** Land on the static tab in list view — the only view where rows carry row
 *  actions and the SelectionBar renders. `view-mode-list` is idempotent
 *  (`setViewMode('list')`), not a flip, so clicking it is safe even if already
 *  active; we still assert the end state per the toggle rule. */
async function openStaticListView(page: Page): Promise<void> {
    await navigateTo(page, '/files?tab=static');
    await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true');
    await waitForSettled(page.getByTestId('files-page'));
    const listBtn = page.getByTestId('view-mode-list');
    await expect(listBtn).toBeVisible({timeout: 8_000});
    await listBtn.click();
    await expect(listBtn).toHaveClass(/active/);
}

async function openBrimListView(page: Page): Promise<void> {
    await navigateTo(page, '/files?tab=brim');
    await expect(page.getByTestId('files-tab-brim')).toHaveAttribute('aria-selected', 'true');
    await waitForSettled(page.getByTestId('files-page'));
}

/** Open a row's kebab menu and fire an action, scoped to the given row id. */
async function rowAction(page: Page, fileId: string, actionId: string): Promise<void> {
    const kebab = page.getByTestId(`row-actions-${fileId}`);
    await expect(kebab).toBeVisible({timeout: 5_000});
    await kebab.click();
    await expect(page.getByTestId('context-menu')).toBeVisible({timeout: 5_000});
    await page.getByTestId(`context-menu-action-${actionId}`).click();
}

test.beforeEach(async ({page}) => {
    await login(page, TEST_USER);
});

test.beforeAll(async () => {
    const api = await apiLogin();
    if (!api) return;
    try {
        const res = await api.get(`${API}/uploads`);
        if (res.ok()) {
            mockStaticBaseline = ((await res.json()) as {items: Array<{id: string}>}).items.map((f) => f.id);
        }
    } finally {
        await api.dispose();
    }
});

test('static single delete — confirm removes exactly the target row', async ({page}) => {
    const id = await uploadStaticFile(page, uniqueSuffix());
    await openStaticListView(page);

    const row = page.locator(`[data-row-id="${id}"]`);
    await expect(row).toHaveCount(1);

    await rowAction(page, id, 'delete');
    await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: 5_000});

    const since = await eventSeq(page);
    await page.getByTestId('confirm-modal-confirm').click();

    const ev = await waitForEvent(page, 'file.deleted', {since});
    expect(ev.detail).toMatchObject({fileId: id, isBrim: false});
    await expect(row).toHaveCount(0);
});

test('static single delete — cancel keeps the row', async ({page}) => {
    const id = await uploadStaticFile(page, uniqueSuffix());
    await openStaticListView(page);

    const row = page.locator(`[data-row-id="${id}"]`);
    await expect(row).toHaveCount(1);

    await rowAction(page, id, 'delete');
    const cancel = page.getByTestId('confirm-modal-cancel');
    await expect(cancel).toBeVisible({timeout: 5_000});
    await cancel.click();

    // The modal is gone and the row survived — the cancel branch of the confirm.
    await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);
    await expect(row).toHaveCount(1);
});

test('static bulk delete — SelectionBar emits file.deleted.bulk for the selected rows', async ({page}) => {
    const ids = [await uploadStaticFile(page, uniqueSuffix()), await uploadStaticFile(page, uniqueSuffix()), await uploadStaticFile(page, uniqueSuffix())];
    await openStaticListView(page);

    for (const id of ids) {
        await expect(page.locator(`[data-row-id="${id}"]`)).toHaveCount(1);
        await page.getByTestId(`dt-row-checkbox-${id}`).click();
    }

    // The page SelectionBar only renders once something is selected; its delete
    // button is the sole reachable entry point to `handleBulkDeleteFiles`.
    const bulkDelete = page.getByTestId('selection-bar-action-delete');
    await expect(bulkDelete).toBeVisible({timeout: 5_000});

    const since = await eventSeq(page);
    await bulkDelete.click();

    const ev = await waitForEvent(page, 'file.deleted.bulk', {since});
    expect(ev.detail).toMatchObject({count: ids.length, isBrim: false});
    for (const id of ids) {
        await expect(page.locator(`[data-row-id="${id}"]`)).toHaveCount(0);
    }
});

test('static delete failure — emits file.delete.failed and keeps the row', async ({page}) => {
    const id = await uploadStaticFile(page, uniqueSuffix());
    await openStaticListView(page);

    const row = page.locator(`[data-row-id="${id}"]`);
    await expect(row).toHaveCount(1);

    // Force the DELETE to fail *at the network*, so the row is never actually
    // removed on the backend — the catch branch runs, the file stays, and
    // `afterAll` still deletes it for real once the route is torn down. Anchored
    // regex: matches only this exact file's URL (± query), never `/{id}/preview`.
    const escaped = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const delRoute = new RegExp(`/api/v1/uploads/${escaped}(\\?.*)?$`);
    await page.route(delRoute, (route) => (route.request().method() === 'DELETE' ? route.fulfill({status: 500, contentType: 'application/json', body: '{"detail":"boom"}'}) : route.continue()));

    await rowAction(page, id, 'delete');
    await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: 5_000});
    const since = await eventSeq(page);
    await page.getByTestId('confirm-modal-confirm').click();

    const ev = await waitForEvent(page, 'file.delete.failed', {since});
    expect(ev.detail).toMatchObject({fileId: id, isBrim: false});

    await page.unroute(delRoute);
    await expect(row).toHaveCount(1);
});

test('BRIM single delete — the isBrim path removes the report', async ({page}) => {
    const brokerId = await createBroker(page, uniqueSuffix());
    const fileId = await uploadBrimFile(page, brokerId, uniqueSuffix());
    await openBrimListView(page);

    const row = page.locator(`[data-row-id="${fileId}"]`);
    await expect(row).toHaveCount(1);

    await rowAction(page, fileId, 'delete');
    await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: 5_000});
    const since = await eventSeq(page);
    await page.getByTestId('confirm-modal-confirm').click();

    const ev = await waitForEvent(page, 'file.deleted', {since});
    expect(ev.detail).toMatchObject({fileId, isBrim: true});
    await expect(row).toHaveCount(0);
});

test('BRIM empty state renders when the report list is empty', async ({page}) => {
    // Force emptiness deterministically instead of depending on global BRIM state
    // (the mock seeds reports, and a sibling worker may add more). This exercises
    // the `{#if brimFiles.length === 0}` branch and the empty-state render without
    // touching any real data. Anchored so it matches the list, not `/files/{id}`.
    const brimListRoute = /\/api\/v1\/brokers\/import\/files(\?.*)?$/;
    await page.route(brimListRoute, (route) => (route.request().method() === 'GET' ? route.fulfill({status: 200, contentType: 'application/json', body: '[]'}) : route.continue()));

    await navigateTo(page, '/files?tab=brim');
    await expect(page.getByTestId('files-tab-brim')).toHaveAttribute('aria-selected', 'true');
    await waitForSettled(page.getByTestId('files-page'));

    await expect(page.getByTestId('brim-empty-state')).toBeVisible({timeout: 8_000});
    await page.unroute(brimListRoute);
});

test.afterAll(async () => {
    const api: APIRequestContext | null = await apiLogin();
    if (!api) return;
    try {
        // 1. Precise cleanup: delete only what this file created. Idempotent —
        //    a row a test already removed answers 404, which we ignore.
        for (const id of createdStatic) await api.delete(`${API}/uploads/${id}`).catch(() => {});
        for (const id of createdBrim) await api.delete(`${API}/brokers/import/files/${id}`).catch(() => {});
        for (const id of createdBrokers) await api.delete(`${API}/brokers?ids=${id}&force=true`).catch(() => {});

        // 2. The net. Only if a *mock* baseline file vanished (it never should —
        //    we only ever delete disposables) and only when no sibling worker
        //    could be mid-test, because `--force` unlinks the whole database.
        if (REPOPULATE_ALLOWED && mockStaticBaseline.length > 0) {
            const res = await api.get(`${API}/uploads`);
            if (res.ok()) {
                const now = new Set(((await res.json()) as {items: Array<{id: string}>}).items.map((f) => f.id));
                const destroyed = mockStaticBaseline.some((id) => !now.has(id));
                if (destroyed) {
                    await api.dispose();
                    await repopulateMockData();
                    return;
                }
            }
        }
    } finally {
        await api.dispose().catch(() => {});
    }
});
