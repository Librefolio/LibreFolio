/**
 * Files › the storage bar (lot FB-29): how much room the instance takes, drawn above the tabs of the Files page, for
 * administrators only.
 *
 * `storage-bar` is mounted by the Files page for an administrator, above the tab bar, so it is on screen on all three
 * tabs (`static`, `brim`, `backup`). It reads `GET /api/v1/backup/instance/storage` when it mounts and every time the page
 * reads its files again (the refresh button). Its root publishes `data-state` (`loading|ready|error`) and `data-mode`
 * (`limit|volume|data`); each non-empty part of LibreFolio's data is a `storage-segment-<id>` carrying `data-bytes`, and
 * the limit is edited in place (`storage-limit-mb`, `storage-limit-save`; event `storage.limit.saved` `{limit_mb}`).
 *
 * Covered, through the real page and the lane's real backend, on the desktop project:
 *   - FST-001: an administrator has the bar, `ready`, in a recognised mode, above the tab bar, on every tab;
 *   - FST-002: a regular user does not have it;
 *   - FST-003: a backup made through the API makes the `backups` segment grow when the page's refresh button reads again
 *     (`data-bytes` larger than before, and at least the size of the archive the server lists);
 *   - FST-004: the limit editor round trip: the field holds what the server holds; a limit saved is announced, held by
 *     the server and turns the bar into `limit` mode; taking it away (0) leaves that mode; the original is put back.
 *
 * Nothing here asserts on translated text. The limit "pinned by the environment" (`LIBREFOLIO_STORAGE_LIMIT_MB`) is the
 * component test's: a lane started with that variable cannot run FST-004, and says so instead of passing.
 *
 * Serial, and here is what is shared. The instance builds ONE backup at a time (a second start is refused, 409
 * `backup_busy`) — a start that meets another backup waits for it with a bounded retry, never a pause —, the size of
 * `backups/` is one number every test of the file reads before and after, and `storage_limit_mb` is ONE global row: the
 * test that writes it restores it in a `finally`, and nothing else here writes it while it runs.
 *
 * Ownership. Every backup a test starts is recorded from the server's answer at once; after the test, red or green, each
 * one is waited out if it still runs and deleted through the administrator's session. The administrator's remembered
 * Files tab is put back to `static` after every test.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `files-storage` of front-utility.
 */
import {expect, test, type APIRequestContext, type Locator, type Page} from './fixtures/playwright';
import {login, navigateTo} from './fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from './fixtures/app-events';
import {TEST_ADMIN, TEST_USER} from './fixtures/test-users';

const API = '/api/v1';
const BACKUP_API = `${API}/backup/instance`;
const STORAGE_API = `${BACKUP_API}/storage`;
const SETTINGS_API = `${API}/settings/global`;
const LIMIT_KEY = 'storage_limit_mb';
/** Where the Files page remembers its tab: a user-scoped localStorage key ending with this name. */
const ACTIVE_TAB_KEY = 'filesPage_activeTab';
const JOB_ID = /^[0-9a-f]{32}$/;
const MODE = /^(limit|volume|data)$/;

// A page after a navigation: the budget navigateTo() gives the app's hydration. A deadline, never a delay.
const PAGE_MS = 15_000;
// A backup of the populated lane takes seconds; another spec's backup may come first, and it takes seconds too.
const BACKUP_MS = 90_000;
const BACKUP_TEST_MS = 150_000;

// Serial: one backup at a time on the instance, the size of backups/ read before and after, one global setting written.
test.describe.configure({mode: 'serial'});

// ---------------------------------------------------------------------------
// The storage route, the limit setting
// ---------------------------------------------------------------------------

interface Storage {
    backups_bytes: number;
    data_bytes: number;
    limit_mb: number | null;
    limit_locked: boolean;
}

/** The measurement the server makes, as an administrator reads it. */
async function readStorage(api: APIRequestContext): Promise<Storage> {
    const response = await api.get(STORAGE_API);
    expect(response.status(), `GET ${STORAGE_API}`).toBe(200);
    return (await response.json()) as Storage;
}

/** The `storage_limit_mb` global setting as the settings route lists it (the value in force), a string. */
async function readLimitSetting(api: APIRequestContext): Promise<string> {
    const response = await api.get(SETTINGS_API);
    expect(response.status(), `GET ${SETTINGS_API}`).toBe(200);
    const items = ((await response.json()) as {items: Array<{key: string; value: string}>}).items;
    const found = items.find((item) => item.key === LIMIT_KEY);
    expect(found, `${LIMIT_KEY} is among the global settings`).toBeDefined();
    return String(found?.value);
}

/** Put the limit setting back, as the bar saves it: one bulk request. */
async function writeLimitSetting(api: APIRequestContext, value: string): Promise<void> {
    const response = await api.patch(`${SETTINGS_API}/bulk`, {data: {items: [{key: LIMIT_KEY, value}]}});
    expect(response.status(), `PATCH ${SETTINGS_API}/bulk restoring ${LIMIT_KEY}`).toBe(200);
}

// ---------------------------------------------------------------------------
// Backups: started through the API, recorded, deleted after the test
// ---------------------------------------------------------------------------

/** The jobs the running test started, for the clean-up. */
let owned: string[] = [];

function jobUrl(jobId: string): string {
    return `${BACKUP_API}/jobs/${jobId}`;
}

/** A job's status as the server tells it: `gone` once there is no such job, `HTTP <n>` for an answer that is no job. */
async function jobStatus(api: APIRequestContext, jobId: string): Promise<string> {
    const response = await api.get(jobUrl(jobId));
    if (response.status() === 404) return 'gone';
    if (!response.ok()) return `HTTP ${response.status()}`;
    return String(((await response.json()) as {status?: unknown}).status);
}

/**
 * Start a clear backup as the administrator the page is signed in as, and follow it to its archive. A start another
 * backup refuses (409 `backup_busy`) is asked again until it is accepted (202) or the budget ends.
 */
async function makeBackup(api: APIRequestContext): Promise<string> {
    let jobId = '';
    await expect
        .poll(
            async () => {
                const response = await api.post(BACKUP_API);
                if (response.status() === 202) {
                    jobId = String(((await response.json()) as {job_id?: unknown}).job_id);
                    owned.push(jobId);
                }
                return response.status();
            },
            {message: 'POST /backup/instance is accepted (202); 409 backup_busy means another backup runs, and is asked again', timeout: BACKUP_MS, intervals: [250, 500, 1000, 2000]},
        )
        .toBe(202);
    expect(jobId, 'the accepted start names its job').toMatch(JOB_ID);
    await expect.poll(() => jobStatus(api, jobId), {message: `backup job ${jobId} has ended`, timeout: BACKUP_MS}).toMatch(/^(done|failed)$/);
    expect(await jobStatus(api, jobId), `backup job ${jobId} ended with its archive`).toBe('done');
    return jobId;
}

/** The size of the archive of a kept backup, as the list route tells it: the entry of that job id, never a position. */
async function fileSizeOf(api: APIRequestContext, jobId: string): Promise<number> {
    const response = await api.get(`${BACKUP_API}/jobs`);
    expect(response.status(), `GET ${BACKUP_API}/jobs`).toBe(200);
    const items = ((await response.json()) as {items: Array<{job_id: string; file_size?: number | null}>}).items;
    const found = items.find((item) => item.job_id === jobId);
    expect(found, `the list of kept backups holds the job ${jobId} (${items.length} listed)`).toBeDefined();
    const size = Number(found?.file_size);
    expect(size, 'a kept backup carries the size of its archive').toBeGreaterThan(0);
    return size;
}

/** Delete a job this test started, waiting it out first if it still runs: a running job refuses the delete (409). */
async function discardJob(api: APIRequestContext, jobId: string): Promise<void> {
    let status = '';
    await expect
        .poll(
            async () => {
                status = await jobStatus(api, jobId);
                return status;
            },
            {message: `backup job ${jobId} has ended, so the clean-up can delete it`, timeout: BACKUP_MS},
        )
        .toMatch(/^(gone|done|failed)$/);
    if (status !== 'gone') {
        const deleted = await api.delete(jobUrl(jobId));
        expect(deleted.status(), `DELETE ${jobUrl(jobId)}`).toBe(204);
    }
    expect(await jobStatus(api, jobId), `backup job ${jobId} is gone from the server`).toBe('gone');
}

// ---------------------------------------------------------------------------
// The page
// ---------------------------------------------------------------------------

/** The Files page as `route`, signed in as `user`, loaded: the page publishes `data-busy` once every wave is in. */
async function openFiles(page: Page, user: typeof TEST_ADMIN, route: string): Promise<void> {
    await login(page, user);
    await navigateTo(page, route);
    await waitForSettled(page.getByTestId('files-page'));
}

/** The administrator on the Files page, the storage bar read: its locator. */
async function openWithBar(page: Page, route = '/files?tab=static'): Promise<Locator> {
    await openFiles(page, TEST_ADMIN, route);
    const bar = page.getByTestId('storage-bar');
    await expect(bar, 'the Files page has exactly one storage bar').toHaveCount(1, {timeout: PAGE_MS});
    await expect(bar).toHaveAttribute('data-state', 'ready', {timeout: PAGE_MS});
    return bar;
}

/** The `<input>` of the limit field: its test id sits on the input itself or on the wrapper around it. */
function inputOf(scope: Locator, testId: string): Locator {
    return scope.getByTestId(testId).locator('xpath=self::input | descendant::input');
}

/** What the `backups` segment of the bar says it holds, in bytes; 0 when the folder is empty and nothing is drawn; -1 while it is being redrawn. */
async function backupsSegmentBytes(bar: Locator): Promise<number> {
    try {
        const segment = bar.getByTestId('storage-segment-backups');
        if ((await segment.count()) === 0) return 0;
        return Number(await segment.getAttribute('data-bytes', {timeout: 1_000}));
    } catch {
        return -1;
    }
}

test.beforeEach(() => {
    owned = [];
});

test.afterEach(async ({page, baseURL}) => {
    for (const jobId of owned) await discardJob(page.request, jobId);
    // The administrator's remembered Files tab is shared with every other spec that opens /files: back to `static`.
    if (baseURL !== undefined && page.url().startsWith(baseURL)) {
        await page.evaluate((suffix) => {
            for (let index = 0; index < localStorage.length; index++) {
                const key = localStorage.key(index);
                if (key !== null && key.endsWith(suffix) && localStorage.getItem(key) !== 'static') localStorage.setItem(key, 'static');
            }
        }, ACTIVE_TAB_KEY);
    }
});

// ---------------------------------------------------------------------------
// The tests
// ---------------------------------------------------------------------------

test.describe('Files › storage bar — who gets it', () => {
    test('FST-001: an administrator has the bar, read, above the tab bar, on every tab', async ({page}) => {
        const bar = await openWithBar(page, '/files?tab=static');

        for (const tab of ['static', 'brim', 'backup']) {
            await page.getByTestId(`files-tab-${tab}`).click();
            await expect(page.getByTestId(`files-tab-${tab}`)).toHaveAttribute('aria-selected', 'true', {timeout: PAGE_MS});
            await expect(bar, `the bar is on the ${tab} tab`).toBeVisible();
            await expect(bar, `the bar of the ${tab} tab is read`).toHaveAttribute('data-state', 'ready', {timeout: PAGE_MS});
            await expect(bar).toHaveAttribute('data-mode', MODE);
            await expect(page.getByTestId('storage-bar-track')).toBeVisible();
            await expect(page.getByTestId('storage-summary')).toBeVisible();
        }
        // The Backups tab is open: its panel and the bar are both there.
        await expect(page.getByTestId('files-backup-panel')).toBeVisible();

        // Above the tab bar: the bar ends where the tabs begin.
        const barBox = await bar.boundingBox();
        const tabBox = await page.getByTestId('files-tab-static').boundingBox();
        expect(barBox, 'the bar has a box on screen').not.toBeNull();
        expect(tabBox, 'the tab has a box on screen').not.toBeNull();
        expect(barBox!.y + barBox!.height, 'the bar ends above the tab bar').toBeLessThanOrEqual(tabBox!.y + 1);
    });

    test('FST-001b: the mode the bar shows is the one the server’s numbers call for', async ({page}) => {
        const bar = await openWithBar(page);
        const storage = await readStorage(page.request);

        // A limit in force is the limit mode; otherwise the disk or, without it, the data folder.
        if (storage.limit_mb !== null && storage.limit_mb > 0) await expect(bar).toHaveAttribute('data-mode', 'limit');
        else await expect(bar).toHaveAttribute('data-mode', /^(volume|data)$/);
    });

    test('FST-002: a regular user does not have the bar', async ({page}) => {
        await openFiles(page, TEST_USER, '/files');

        // Presence first: the page is drawn up to the tabs everyone has...
        await expect(page.getByTestId('files-tab-static')).toBeVisible({timeout: PAGE_MS});
        await expect(page.getByTestId('files-tab-brim')).toBeVisible();
        // ...then the absence.
        await expect(page.getByTestId('storage-bar')).toHaveCount(0);
        await expect(page.getByTestId('storage-limit-mb')).toHaveCount(0);
    });
});

test.describe('Files › storage bar — it follows the backups', () => {
    test.describe.configure({timeout: BACKUP_TEST_MS});

    test('FST-003: a backup made through the API makes the backups segment grow when the page reads again', async ({page}) => {
        // Signed in first: the page's request context carries the administrator's session only after the login.
        const bar = await openWithBar(page);
        const before = await backupsSegmentBytes(bar);
        expect(before, 'the segment was readable before the backup').toBeGreaterThanOrEqual(0);

        const jobId = await makeBackup(page.request);
        const archive = await fileSizeOf(page.request, jobId);
        await page.getByTestId('files-refresh-button').click();

        // The segment holds the whole of backups/: more than before, and at least the archive this test made.
        await expect
            .poll(
                async () => {
                    const bytes = await backupsSegmentBytes(bar);
                    return bytes > before && bytes >= archive;
                },
                {message: `backups segment grew past ${before} bytes and holds the ${archive}-byte archive`, timeout: PAGE_MS},
            )
            .toBe(true);
        await expect(bar).toHaveAttribute('data-state', 'ready');
        await expect(bar.getByTestId('storage-legend-backups'), 'the legend names the part').toBeVisible();
    });
});

test.describe('Files › storage bar — the limit', () => {
    test('FST-004: the field holds the limit in force; a limit saved is announced and held; 0 takes it away; the original is put back', async ({page}) => {
        // Signed in first: the page's request context carries the administrator's session only after the login.
        const bar = await openWithBar(page);
        const storage = await readStorage(page.request);
        expect(storage.limit_locked, 'this lane pins the limit with LIBREFOLIO_STORAGE_LIMIT_MB: start it without the variable to run this test').toBe(false);
        const original = await readLimitSetting(page.request);
        const field = inputOf(bar, 'storage-limit-mb');
        const save = bar.getByTestId('storage-limit-save');
        try {
            await expect(field).toHaveValue(String(storage.limit_mb ?? 0));
            await expect(save, 'nothing differs from the server: nothing to save').toBeDisabled();
            await expect(bar.getByTestId('storage-limit-locked')).toHaveCount(0);

            // A limit far above anything the lane stores: the bar changes shape, nothing is deleted.
            const next = original === '4096' ? '8192' : '4096';
            await field.fill(next);
            await expect(save).toBeEnabled();
            let since = await eventSeq(page);
            await save.click();

            const saved = await waitForEvent(page, 'storage.limit.saved', {since});
            expect(saved.detail, 'storage.limit.saved carries the limit that was saved').toEqual({limit_mb: Number(next)});
            await expect(bar).toHaveAttribute('data-mode', 'limit', {timeout: PAGE_MS});
            await expect(bar).toHaveAttribute('data-state', 'ready');
            await expect(field).toHaveValue(next);
            await expect(save, 'saved: nothing left to save').toBeDisabled();
            expect((await readStorage(page.request)).limit_mb, 'the server holds the limit').toBe(Number(next));
            // The bar is a limit bar, far from full: its summary is there and the warning is not.
            await expect(bar.getByTestId('storage-summary')).toBeVisible();
            await expect(bar.getByTestId('storage-over-limit')).toHaveCount(0);

            // Taking it away is a save of 0.
            await field.fill('0');
            await expect(save).toBeEnabled();
            since = await eventSeq(page);
            await save.click();

            const cleared = await waitForEvent(page, 'storage.limit.saved', {since});
            expect(cleared.detail, 'storage.limit.saved carries the 0 that was saved').toEqual({limit_mb: 0});
            await expect(bar).not.toHaveAttribute('data-mode', 'limit', {timeout: PAGE_MS});
            await expect(bar).toHaveAttribute('data-mode', MODE);
            await expect(field).toHaveValue('0');
            expect((await readStorage(page.request)).limit_mb, 'the server holds no limit').toBeNull();
        } finally {
            await writeLimitSetting(page.request, original);
        }
        expect(await readLimitSetting(page.request), 'the original limit is back').toBe(original);
    });
});
