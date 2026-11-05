/**
 * Files › Backups (lot FB-24): the backups an instance keeps, seen and cleaned from the Files page, by administrators only.
 *
 * The Files page gets a third tab, `files-tab-backup`, for administrators only (the archives hold every user's data). It
 * holds `files-backup-panel`: a `BackupsSection` that does not fold (`backups-section`, always open), with the table of
 * the backups the server keeps (`backup-list`, a row per job, `tr[data-row-id=<job_id>]`) and the settings of their
 * automatic clean-up (`backup-cleanup`). Nothing of the two other tabs follows it there: no Upload button, no grid/list
 * toggle. The page's refresh button reads the list again. The Backup tab of Settings mounts the same section, folded
 * open under the backup card; Settings is `settings/backup.spec.ts`'s.
 *
 * Covered, through the real page and the lane's real backend, on the desktop project:
 *   - FBKF-001: an administrator has the tab; opening it shows the panel, the section open with no fold button, the list
 *     read, the clean-up settings, and none of the controls of the static tab; `?tab=backup` opens it; the tab is
 *     remembered for the next visit;
 *   - FBKF-002: a regular user has no tab, `?tab=backup` opens the static tab instead, and a remembered `backup` tab in
 *     the user's storage is not honoured either;
 *   - FBKF-003: a backup made through the API shows up as a row of its job id with the first twelve characters of its
 *     SHA-256 when the page's refresh button is pressed; deleted from the row (kebab, confirmation), the row is gone,
 *     `backup.deleted` names the job and the server no longer has it;
 *   - FBKF-004: the row's download hands the browser the archive of that job (`backup.download.started`);
 *   - FBKF-005: the clean-up settings: the fields hold what the server holds; a change is saved by one request, the panel
 *     says `saved`, `backup.cleanup.saved` carries the values, and the server holds them; restored in a `finally`.
 *
 * Serial, and here is what is shared. The instance builds ONE backup at a time (a second start is refused, 409
 * `backup_busy`) — a start that meets another spec's backup waits for it with a bounded retry, never a pause —, and the
 * clean-up settings are two GLOBAL rows every spec and every user of the lane reads: the test that writes them changes
 * them to a value that deletes nothing (a rule of ten years, or the stored one plus one day) and puts the originals
 * back, and nothing else here writes them while it runs.
 *
 * Ownership. Every backup a test starts is recorded from the server's answer at once; after the test, red or green, each
 * one is waited out if it still runs and deleted through the administrator's session. Nothing here reads a list it did
 * not fill: rows are found by the job id this test started, never by position or by count. The newest backup is the first
 * row of the table (date, newest first), so a row this test made is on its first page whatever else the server keeps. The
 * administrator's remembered Files tab is put back to `static` after every test.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `files-backup` of front-utility.
 */
import {expect, test, type APIRequestContext, type Locator, type Page} from './fixtures/playwright';
import {login, navigateTo} from './fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from './fixtures/app-events';
import {TEST_ADMIN, TEST_USER} from './fixtures/test-users';

const API = '/api/v1';
const BACKUP_API = `${API}/backup/instance`;
const SETTINGS_API = `${API}/settings/global`;
const MAX_MB = 'backup_cleanup_max_mb';
const MAX_DAYS = 'backup_cleanup_max_days';
/** Where the Files page remembers its tab: a user-scoped localStorage key ending with this name. */
const ACTIVE_TAB_KEY = 'filesPage_activeTab';
const JOB_ID = /^[0-9a-f]{32}$/;
const SHA256 = /^[0-9a-f]{64}$/;

// A page after a navigation: the budget navigateTo() gives the app's hydration. A deadline, never a delay.
const PAGE_MS = 15_000;
// A backup of the populated lane takes seconds; another spec's backup may come first, and it takes seconds too.
const BACKUP_MS = 90_000;
const BACKUP_TEST_MS = 150_000;

// Serial: one backup at a time on the instance, and two global settings written by one test (see «Serial» above).
test.describe.configure({mode: 'serial'});

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
 * backup refuses (409 `backup_busy`) is asked again until it is accepted (202) or the budget ends: the poll reads the
 * status the server answered with, so a refusal that is not a busy instance fails with its status.
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

/** The SHA-256 of a kept backup, as the list route tells it: the entry of that job id, never a position. */
async function shaOf(api: APIRequestContext, jobId: string): Promise<string> {
    const response = await api.get(`${BACKUP_API}/jobs`);
    expect(response.status(), `GET ${BACKUP_API}/jobs`).toBe(200);
    const items = ((await response.json()) as {items: Array<{job_id: string; file_sha256?: string | null}>}).items;
    const found = items.find((item) => item.job_id === jobId);
    expect(found, `the list of kept backups holds the job ${jobId} (${items.length} listed)`).toBeDefined();
    const sha = String(found?.file_sha256);
    expect(sha, 'a kept backup carries its SHA-256').toMatch(SHA256);
    return sha;
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

/** The administrator on the Backups tab, through the tab itself: the panel and the list, both read. */
async function openBackupTab(page: Page, route = '/files?tab=static'): Promise<Locator> {
    await openFiles(page, TEST_ADMIN, route);
    await page.getByTestId('files-tab-backup').click();
    await expect(page.getByTestId('files-tab-backup')).toHaveAttribute('aria-selected', 'true', {timeout: PAGE_MS});
    const panel = page.getByTestId('files-backup-panel');
    await expect(panel).toBeVisible({timeout: PAGE_MS});
    await expect(panel.getByTestId('backup-list'), 'the list has been read').toHaveAttribute('data-state', 'ready', {timeout: PAGE_MS});
    return panel;
}

/** The `<input>` of a field of the clean-up panel: its test id sits on the input itself or on the wrapper around it. */
function inputOf(panel: Locator, testId: string): Locator {
    return panel.getByTestId(testId).locator('xpath=self::input | descendant::input');
}

/** The two clean-up settings as the server holds them. */
async function readCleanup(api: APIRequestContext): Promise<{maxMb: string; maxDays: string}> {
    const response = await api.get(SETTINGS_API);
    expect(response.status(), `GET ${SETTINGS_API}`).toBe(200);
    const items = ((await response.json()) as {items: Array<{key: string; value: string}>}).items;
    const valueOf = (key: string): string => {
        const found = items.find((item) => item.key === key);
        expect(found, `${key} is among the global settings`).toBeDefined();
        return String(found?.value);
    };
    return {maxMb: valueOf(MAX_MB), maxDays: valueOf(MAX_DAYS)};
}

/** Put the two clean-up settings back, in one request, as the panel saves them. */
async function writeCleanup(api: APIRequestContext, values: {maxMb: string; maxDays: string}): Promise<void> {
    const response = await api.patch(`${SETTINGS_API}/bulk`, {
        data: {
            items: [
                {key: MAX_MB, value: values.maxMb},
                {key: MAX_DAYS, value: values.maxDays},
            ],
        },
    });
    expect(response.status(), `PATCH ${SETTINGS_API}/bulk restoring the clean-up settings`).toBe(200);
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
                if (key !== null && key.endsWith(suffix) && localStorage.getItem(key) === 'backup') localStorage.setItem(key, 'static');
            }
        }, ACTIVE_TAB_KEY);
    }
});

// ---------------------------------------------------------------------------
// The tests
// ---------------------------------------------------------------------------

test.describe('Files › Backups — who gets the tab', () => {
    test('FBKF-001: an administrator has the Backups tab, and it opens the section with the list and the clean-up settings', async ({page}) => {
        await openFiles(page, TEST_ADMIN, '/files');
        await expect(page.getByTestId('files-tab-static'), 'the bar is drawn').toBeVisible({timeout: PAGE_MS});
        await expect(page.getByTestId('files-tab-backup')).toBeVisible();
        await expect(page.getByTestId('files-backup-panel'), 'the panel is the tab’s own: not drawn on the static tab').toHaveCount(0);

        await page.getByTestId('files-tab-backup').click();

        await expect(page.getByTestId('files-tab-backup')).toHaveAttribute('aria-selected', 'true', {timeout: PAGE_MS});
        await expect(page).toHaveURL(/[?&]tab=backup(&|$)/);
        const panel = page.getByTestId('files-backup-panel');
        await expect(panel).toBeVisible();
        const section = panel.getByTestId('backups-section');
        await expect(section).toHaveAttribute('data-open', 'true');
        await expect(section.getByTestId('backups-section-toggle'), 'on the Files page the section does not fold').toHaveCount(0);
        await expect(section.getByTestId('backup-same-disk-warning')).toBeVisible();
        await expect(section.getByTestId('backup-list')).toHaveAttribute('data-state', 'ready', {timeout: PAGE_MS});
        await expect(section.getByTestId('backup-cleanup')).toBeVisible();
        await expect(section.getByTestId('backup-cleanup')).toHaveAttribute('data-state', /^(idle|saved)$/, {timeout: PAGE_MS});

        // Nothing of the file tabs follows it: with the panel and its sibling controls on screen, these are the absences.
        await expect(page.getByTestId('upload-button')).toHaveCount(0);
        await expect(page.getByTestId('view-mode-toggle')).toHaveCount(0);
        await expect(page.getByTestId('files-table-static')).toHaveCount(0);
        await expect(page.getByTestId('files-table-brim')).toHaveCount(0);
        await expect(page.getByTestId('files-refresh-button'), 'the refresh button stays: it reads the list too').toBeVisible();
    });

    test('FBKF-001b: ?tab=backup opens the tab for an administrator, and the tab is remembered for the next visit', async ({page}) => {
        await openFiles(page, TEST_ADMIN, '/files?tab=backup');

        await expect(page.getByTestId('files-tab-backup')).toHaveAttribute('aria-selected', 'true', {timeout: PAGE_MS});
        await expect(page.getByTestId('files-backup-panel')).toBeVisible();

        // Remembered: a click saves the tab; the next visit with no tab in the address opens it.
        await page.getByTestId('files-tab-static').click();
        await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true');
        await page.getByTestId('files-tab-backup').click();
        await expect(page.getByTestId('files-tab-backup')).toHaveAttribute('aria-selected', 'true');
        await navigateTo(page, '/files');
        await waitForSettled(page.getByTestId('files-page'));
        await expect(page.getByTestId('files-tab-backup')).toHaveAttribute('aria-selected', 'true', {timeout: PAGE_MS});
        await expect(page.getByTestId('files-backup-panel')).toBeVisible();
    });

    test('FBKF-002: a regular user has no Backups tab, and ?tab=backup opens the static tab instead', async ({page}) => {
        await openFiles(page, TEST_USER, '/files?tab=backup');

        // Presence first: the bar is drawn, up to the tabs everyone has, and the page has chosen the tab it opens...
        await expect(page.getByTestId('files-tab-static')).toBeVisible({timeout: PAGE_MS});
        await expect(page.getByTestId('files-tab-brim')).toBeVisible();
        await expect(page.getByTestId('files-tab-static'), '?tab=backup names no tab of this user: the static tab opens').toHaveAttribute('aria-selected', 'true');
        // ...then the absence: the tab is left out of the bar, and no backup body is drawn.
        await expect(page.getByTestId('files-tab-backup')).toHaveCount(0);
        await expect(page.getByTestId('files-backup-panel')).toHaveCount(0);
        await expect(page.getByTestId('backup-list')).toHaveCount(0);
    });

    test('FBKF-002b: a Backups tab remembered in a regular user’s storage is not honoured', async ({page}) => {
        await login(page, TEST_USER);
        const me = await page.request.get(`${API}/auth/me`);
        expect(me.status(), 'GET /auth/me through the browser session').toBe(200);
        const userId = String(((await me.json()) as {id: number}).id);
        await navigateTo(page, '/files');
        // The storage key is the page's own: lf_<user id>_filesPage_activeTab.
        await page.evaluate(([key]) => localStorage.setItem(key, 'backup'), [`lf_${userId}_${ACTIVE_TAB_KEY}`]);

        await navigateTo(page, '/files');
        await waitForSettled(page.getByTestId('files-page'));

        await expect(page.getByTestId('files-tab-static')).toBeVisible({timeout: PAGE_MS});
        await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true');
        await expect(page.getByTestId('files-tab-backup')).toHaveCount(0);
        await expect(page.getByTestId('files-backup-panel')).toHaveCount(0);

        // Whoever writes, cleans up: the remembered tab goes back to what a new user has.
        await page.evaluate(([key]) => localStorage.removeItem(key), [`lf_${userId}_${ACTIVE_TAB_KEY}`]);
    });
});

test.describe('Files › Backups — a backup the server keeps', () => {
    test.describe.configure({timeout: BACKUP_TEST_MS});

    test('FBKF-003: a backup made through the API shows up as a row on refresh, and deleting it from the row removes it', async ({page}) => {
        const panel = await openBackupTab(page);

        // The page was read before this backup existed: the row appears when the page's refresh button reads again.
        const jobId = await makeBackup(page.request);
        const sha = await shaOf(page.request, jobId);
        const row = panel.locator(`tr[data-row-id="${jobId}"]`);
        await expect(row, 'the page read its list before the backup existed').toHaveCount(0);
        await page.getByTestId('files-refresh-button').click();

        await expect(row).toBeVisible({timeout: PAGE_MS});
        const copy = row.getByTestId(`backup-sha-copy-${jobId}`);
        await expect(copy, 'the row shows the short form of its SHA-256').toContainText(sha.slice(0, 12));
        expect(await copy.textContent(), 'the whole hash is for the clipboard, not for the cell').not.toContain(sha);

        // Delete from the row: the kebab, then the confirmation.
        const since = await eventSeq(page);
        await row.getByTestId(`row-actions-${jobId}`).click();
        await page.getByTestId('context-menu-action-delete').click();
        await page.getByTestId('confirm-modal-confirm').click();

        await expect(panel.locator(`tr[data-row-id="${jobId}"]`)).toHaveCount(0, {timeout: PAGE_MS});
        const deleted = await waitForEvent(page, 'backup.deleted', {since});
        expect(deleted.detail?.job_id, 'backup.deleted names the job').toBe(jobId);
        expect(await jobStatus(page.request, jobId), 'the server no longer has the backup').toBe('gone');
    });

    test('FBKF-004: the download of a row hands the browser the archive of that backup', async ({page}) => {
        // Signed in first: the page's request context carries the administrator's session only after the login.
        const panel = await openBackupTab(page);
        const jobId = await makeBackup(page.request);
        await page.getByTestId('files-refresh-button').click();
        const row = panel.locator(`tr[data-row-id="${jobId}"]`);
        await expect(row).toBeVisible({timeout: PAGE_MS});

        const since = await eventSeq(page);
        const downloading = page.waitForEvent('download', {timeout: PAGE_MS});
        await row.getByTestId(`row-actions-${jobId}`).click();
        await page.getByTestId('context-menu-action-download').click();

        const download = await downloading;
        expect(download.url(), 'the archive of this very job').toContain(`/jobs/${jobId}/file`);
        expect(await download.failure(), 'the download completes').toBeNull();
        const started = await waitForEvent(page, 'backup.download.started', {since});
        expect(started.detail?.job_id, 'backup.download.started names the job').toBe(jobId);
    });
});

test.describe('Files › Backups — the clean-up settings', () => {
    test('FBKF-005: the fields hold what the server holds; a change is saved, announced, and held by the server', async ({page}) => {
        // Signed in first: the page's request context carries the administrator's session only after the login.
        const panel = await openBackupTab(page);
        const original = await readCleanup(page.request);
        try {
            const cleanup = panel.getByTestId('backup-cleanup');
            await expect(cleanup).toHaveAttribute('data-state', 'idle', {timeout: PAGE_MS});
            await expect(inputOf(cleanup, 'backup-cleanup-max-mb')).toHaveValue(original.maxMb);
            await expect(inputOf(cleanup, 'backup-cleanup-max-days')).toHaveValue(original.maxDays);
            await expect(cleanup.getByTestId('backup-cleanup-latest-kept')).toBeVisible();
            await expect(cleanup.getByTestId('backup-cleanup-save'), 'nothing differs from the server: nothing to save').toBeDisabled();

            // A value that deletes nothing: ten years when the rule was off, otherwise one day more than it was. The size
            // rule is left as it is (on a hosted instance it cannot be turned off).
            const days = original.maxDays === '0' ? '3650' : String(Number(original.maxDays) + 1);
            await inputOf(cleanup, 'backup-cleanup-max-days').fill(days);
            await expect(cleanup.getByTestId('backup-cleanup-save')).toBeEnabled();
            const since = await eventSeq(page);
            await cleanup.getByTestId('backup-cleanup-save').click();

            // The event first: `idle` is also the state before the click is handled, so the state alone proves nothing yet.
            const saved = await waitForEvent(page, 'backup.cleanup.saved', {since});
            await expect(cleanup).toHaveAttribute('data-state', /^(saved|idle)$/, {timeout: PAGE_MS});
            expect(saved.detail, 'backup.cleanup.saved carries the values that were saved').toEqual({max_mb: Number(original.maxMb), max_days: Number(days)});
            await expect(cleanup).toHaveAttribute('data-error-code', '');
            expect(await readCleanup(page.request), 'the server holds what was saved').toEqual({maxMb: original.maxMb, maxDays: days});
            await expect(cleanup.getByTestId('backup-cleanup-save'), 'saved: nothing left to save').toBeDisabled();
        } finally {
            await writeCleanup(page.request, original);
        }
        expect(await readCleanup(page.request), 'the originals are back').toEqual(original);
    });
});
