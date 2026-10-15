/**
 * Settings › Backup (workstream B, lot B5a): the backup of the whole instance, from an administrator's browser.
 *
 * The Backup tab of Settings is for administrators only (`settingsTabs.ts`: `visible: (ctx) => ctx.isSuperuser`): the
 * archive holds every user's data. Its card (`BackupDownloadCard.svelte`) starts a backup on the server
 * (`POST /api/v1/backup/instance`, 202 and a job), follows the job until its archive is written, then offers it through a
 * plain `<a href="…/jobs/<id>/file" download>` the browser streams to disk, and a delete. It publishes its state on
 * `backup-download-card` (`data-state`, `data-error-code`, `data-busy`) and its outcomes as events (`backup.created`,
 * `backup.deleted`, `backup.download.started`); the job it follows survives a reload in `sessionStorage`.
 *
 * Covered, through the real page and the lane's real backend, on the desktop project (the tab's mobile rendering is the
 * gallery's to cover):
 *   - FBKP-001: a regular user has no Backup tab, and `?tab=backup` opens the first tab instead;
 *   - FBKP-001b: an administrator has it, and it opens the backup card, idle;
 *   - FBKP-002: the whole flow from `?tab=backup`: started, followed to `done`, `backup.created` naming the job, the card
 *     naming the archive, a link to that very job's file, and the download itself — under the archive's name, a zip, as
 *     many bytes as the job reported — with `backup.download.started`;
 *   - FBKP-003: the delete: the card back to idle, `backup.deleted`, and the job gone from the server (404
 *     `backup_job_not_found`), not only from the card;
 *   - FBKP-004: a reload picks the finished job up again — the same link — without announcing it a second time.
 * Not here: the controller's states one by one (a running job's phases and progress, a failed job, a refused start, a
 * failed delete, a lost connection, a recheck), which backupJob.test.ts and BackupDownloadCard.test.ts drive with a faked
 * API: the lane's backend does not fail on cue.
 *
 * Serial, and here is what is shared: the instance builds ONE backup at a time — a second start is refused, 409
 * `backup_busy` — so the tests run one after the other, each one waiting its job out and deleting it before the next one
 * begins. Desktop only, like every other serial spec: `mode: 'serial'` orders the tests of one project, not two.
 *
 * Ownership. Every job a test starts is recorded from the server's answer the moment it arrives. After the test, red or
 * green, each one is waited out if it still runs and deleted through `page.request` — the administrator's cookies — and
 * the `sessionStorage` key the card follows it by is cleared: a finished job would otherwise stay on the server for an
 * hour. Nothing reads a list it did not fill, and no setting is changed.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `backup` of front-utility.
 */
import {open, stat} from 'node:fs/promises';
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {eventSeq, waitForEvent} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';

const BACKUP_API = '/api/v1/backup/instance';
/** Where the card keeps the id of the job it follows: `BACKUP_JOB_STORAGE_KEY` of `backupJob.svelte.ts`. */
const FOLLOWED_JOB_KEY = 'librefolio.backup.job';
const JOB_ID = /^[0-9a-f]{32}$/;
/** The archive's name, `librefolio-backup-YYYYMMDD-HHMMSS.zip` (`archive_name()` of jobs.py), with room for a numbered twin. */
const ARCHIVE_NAME = /^librefolio-backup-\d{8}-\d{6}(-\d+)?\.zip$/;
/** A zip archive opens with a local file header: `PK\x03\x04`, in hex. */
const ZIP_MAGIC = '504b0304';

// A page after a navigation or a reload: the budget navigateTo() gives the app's hydration. A deadline, never a delay.
const PAGE_MS = 15_000;
// A backup of the populated lane takes seconds; the card reads its job once a second until the archive is written.
const BACKUP_MS = 60_000;
// Sign-in and navigation, the backup and the download, each on its own budget.
const BACKUP_TEST_MS = 120_000;

/** What a test started on the server, for the clean-up. */
type Owned = {
    /** Jobs started from this page: the server's answers to `POST /backup/instance`. */
    jobs: Set<string>;
    /** Those answers still being read: the clean-up waits for them, so a job started just before a failure is not missed. */
    reading: Promise<void>[];
};

let owned: Owned = {jobs: new Set(), reading: []};

// ---------------------------------------------------------------------------
// Jobs: recorded as they start, deleted after the test
// ---------------------------------------------------------------------------

function jobUrl(jobId: string): string {
    return `${BACKUP_API}/jobs/${jobId}`;
}

/** Record every job this page starts, from the server's answer, whatever the test does next. */
function recordStartedJobs(page: Page): void {
    const into = owned;
    page.on('response', (response) => {
        if (response.request().method() !== 'POST' || new URL(response.url()).pathname !== BACKUP_API) return;
        into.reading.push(
            response.json().then(
                (body: {job_id?: unknown} | null) => {
                    if (typeof body?.job_id === 'string') into.jobs.add(body.job_id);
                },
                // An answer that cannot be read: the card still follows its job, and the clean-up finds it in sessionStorage.
                () => undefined,
            ),
        );
    });
}

/** A job's status as the server tells it: `gone` once there is no such job, `HTTP <n>` for an answer that is no job. */
async function jobStatus(page: Page, jobId: string): Promise<string> {
    const response = await page.request.get(jobUrl(jobId));
    if (response.status() === 404) return 'gone';
    if (!response.ok()) return `HTTP ${response.status()}`;
    return String(((await response.json()) as {status?: unknown}).status);
}

/** Delete a job this test started, waiting it out first if it still runs: a running job refuses the delete (409). */
async function discardJob(page: Page, jobId: string): Promise<void> {
    let status = '';
    await expect
        .poll(
            async () => {
                status = await jobStatus(page, jobId);
                return status;
            },
            {message: `backup job ${jobId} has ended, so the clean-up can delete it`, timeout: BACKUP_MS},
        )
        .toMatch(/^(gone|done|failed)$/);
    if (status !== 'gone') {
        const deleted = await page.request.delete(jobUrl(jobId));
        expect(deleted.status(), `DELETE ${jobUrl(jobId)}`).toBe(204);
    }
    expect(await jobStatus(page, jobId), `backup job ${jobId} is gone from the server`).toBe('gone');
}

// ---------------------------------------------------------------------------
// The page
// ---------------------------------------------------------------------------

/** Sign the administrator in and open Settings › Backup through `?tab=backup`: the backup card, once drawn. */
async function openBackupTab(page: Page): Promise<Locator> {
    await login(page, TEST_ADMIN);
    await navigateTo(page, '/settings?tab=backup');
    await expect(page.getByTestId('settings-tab-backup'), '?tab=backup opens the Backup tab').toHaveAttribute('aria-selected', 'true', {timeout: PAGE_MS});
    const card = page.getByTestId('backup-download-card');
    await expect(card).toBeVisible({timeout: PAGE_MS});
    return card;
}

/**
 * Start a backup from an idle card and follow it to its archive: the job's id and the archive's size, as `backup.created`
 * announces them.
 */
async function createBackup(page: Page, card: Locator): Promise<{jobId: string; fileSize: number}> {
    await expect(card, 'precondition: a new tab follows no backup, so the card offers to start one').toHaveAttribute('data-state', 'idle');
    const since = await eventSeq(page);
    await page.getByTestId('backup-create').click();

    // Started, then followed: the card reads the job every second until it ends, with its archive or without.
    await expect(card).toHaveAttribute('data-state', /^(done|failed)$/, {timeout: BACKUP_MS});
    // The reason before the state: a backup that failed reds with its code (backup_busy, backup_no_space, …).
    await expect(card, 'the backup ended without an error').toHaveAttribute('data-error-code', '');
    await expect(card).toHaveAttribute('data-state', 'done');

    const created = await waitForEvent(page, 'backup.created', {since});
    const jobId = String(created.detail?.job_id);
    expect(jobId, 'backup.created names the job by its id').toMatch(JOB_ID);
    await Promise.all(owned.reading);
    expect([...owned.jobs], 'the job the card announces is the one the server started for this click').toEqual([jobId]);
    return {jobId, fileSize: Number(created.detail?.file_size)};
}

/** The first `count` bytes of a file, in hex. */
async function leadingBytes(path: string, count: number): Promise<string> {
    const file = await open(path, 'r');
    try {
        const buffer = Buffer.alloc(count);
        const {bytesRead} = await file.read(buffer, 0, count, 0);
        return buffer.subarray(0, bytesRead).toString('hex');
    } finally {
        await file.close();
    }
}

/** The names in the page's event ring, oldest first; null when the page publishes no ring. */
async function eventNames(page: Page): Promise<string[] | null> {
    return page.evaluate(() => (window as unknown as {__lf?: {events?: Array<{name: string}>}}).__lf?.events?.map((event) => event.name) ?? null);
}

// ---------------------------------------------------------------------------
// The tests
// ---------------------------------------------------------------------------

// Serial: one backup at a time on the instance (see «Serial» above).
test.describe.configure({mode: 'serial'});

test.beforeEach(async ({page}) => {
    owned = {jobs: new Set(), reading: []};
    recordStartedJobs(page);
});

test.afterEach(async ({page, baseURL}) => {
    await Promise.all(owned.reading);
    // The page is still on the app when the test got that far: the job its card follows is one of this test's too.
    const onApp = baseURL !== undefined && page.url().startsWith(baseURL);
    if (onApp) {
        const followed = await page.evaluate((key) => sessionStorage.getItem(key), FOLLOWED_JOB_KEY);
        if (followed !== null) owned.jobs.add(followed);
    }
    for (const jobId of owned.jobs) await discardJob(page, jobId);
    if (onApp) await page.evaluate((key) => sessionStorage.removeItem(key), FOLLOWED_JOB_KEY);
});

test.describe('Settings › Backup — who gets the tab', () => {
    test('FBKP-001: a regular user has no Backup tab, and ?tab=backup opens the first tab instead', async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/settings?tab=backup');

        // Presence first: the bar is drawn up to its last tab everyone sees, and the page has chosen the tab it opens...
        await expect(page.getByTestId('settings-tab-admin')).toBeVisible({timeout: PAGE_MS});
        await expect(page.getByTestId('settings-tab-profile'), '?tab=backup names no tab of this user: the first one opens').toHaveAttribute('aria-selected', 'true');
        await expect(page.getByTestId('profile-tab')).toBeVisible();

        // ...then the absence: the tab is left out of the bar, not hidden in it, and no backup body is drawn.
        await expect(page.getByTestId('settings-tab-backup')).toHaveCount(0);
        await expect(page.getByTestId('backup-tab')).toHaveCount(0);
    });

    test('FBKP-001b: an administrator has the Backup tab, and it opens the backup card', async ({page}) => {
        await login(page, TEST_ADMIN);
        await navigateTo(page, '/settings');

        const tab = page.getByTestId('settings-tab-backup');
        await expect(tab).toBeVisible({timeout: PAGE_MS});
        await expect(tab, 'precondition: /settings opens on its first tab').toHaveAttribute('aria-selected', 'false');

        await tab.click();
        await expect(tab).toHaveAttribute('aria-selected', 'true');
        await expect(page.getByTestId('backup-tab')).toBeVisible();
        await expect(page.getByTestId('backup-download-card'), 'a new tab follows no backup').toHaveAttribute('data-state', 'idle');
        await expect(page.getByTestId('backup-privacy-notice')).toBeVisible();
        await expect(page.getByTestId('backup-create')).toBeEnabled();
    });
});

test.describe('Settings › Backup — an archive of the instance', () => {
    test.describe.configure({timeout: BACKUP_TEST_MS});

    test('FBKP-002: from ?tab=backup a backup is created, followed to done, and its archive downloaded', async ({page}) => {
        const card = await openBackupTab(page);
        const {jobId, fileSize} = await createBackup(page, card);
        expect(fileSize, 'backup.created gives the size of the archive').toBeGreaterThan(0);

        const link = page.getByTestId('backup-download-link');
        // The archive of this very job, from the same origin: the session cookie goes with the link.
        await expect(link).toHaveAttribute('href', new RegExp(`/jobs/${jobId}/file$`));
        // `download` names the file, and keeps SvelteKit's router from taking the click for a change of page.
        await expect(link).toHaveAttribute('download', ARCHIVE_NAME);
        const name = (await link.getAttribute('download')) ?? '';
        // The card names the archive it offers: a value inside a translated sentence, the same in every language.
        await expect(page.getByTestId('backup-file-details')).toContainText(name);

        const since = await eventSeq(page);
        const downloading = page.waitForEvent('download', {timeout: PAGE_MS});
        await link.click();
        const download = await downloading;
        expect(download.suggestedFilename()).toMatch(ARCHIVE_NAME);
        expect(download.suggestedFilename(), 'the browser saves the archive under the name the link gives').toBe(name);
        expect(await download.failure(), 'the download completes').toBeNull();
        const saved = await download.path();
        expect((await stat(saved)).size, 'the whole archive arrived: as many bytes as the job reported').toBe(fileSize);
        expect(await leadingBytes(saved, 4), 'a zip archive: it opens with a local file header').toBe(ZIP_MAGIC);

        const started = await waitForEvent(page, 'backup.download.started', {since});
        expect(started.detail?.job_id, 'backup.download.started names the job').toBe(jobId);
    });

    test('FBKP-003: deleting the archive empties the card and removes the job from the server', async ({page}) => {
        const card = await openBackupTab(page);
        const {jobId} = await createBackup(page, card);

        const since = await eventSeq(page);
        await page.getByTestId('backup-delete').click();
        await expect(card, 'the archive is deleted: the card offers a new backup').toHaveAttribute('data-state', 'idle', {timeout: PAGE_MS});
        const deleted = await waitForEvent(page, 'backup.deleted', {since});
        expect(deleted.detail?.job_id, 'backup.deleted names the job').toBe(jobId);

        // Gone from the server, not only from the card.
        const response = await page.request.get(jobUrl(jobId));
        expect(response.status(), `GET ${jobUrl(jobId)} after the delete`).toBe(404);
        expect(((await response.json()) as {detail?: {code?: unknown}}).detail?.code).toBe('backup_job_not_found');
    });

    test('FBKP-004: a reload picks the finished backup up again, without announcing it twice', async ({page}) => {
        const card = await openBackupTab(page);
        const {jobId} = await createBackup(page, card);
        const link = page.getByTestId('backup-download-link');
        await expect(link).toHaveAttribute('href', new RegExp(`/jobs/${jobId}/file$`));
        const href = (await link.getAttribute('href')) ?? '';
        // What the pick-up rests on: the tab keeps the id of the job it follows.
        expect(await page.evaluate((key) => sessionStorage.getItem(key), FOLLOWED_JOB_KEY), `sessionStorage['${FOLLOWED_JOB_KEY}'] holds the job`).toBe(jobId);

        await page.reload();
        // A new page, started from scratch: hydrated (the barrier navigateTo() waits on), then its card reads the job it
        // followed (`loading`) and offers its archive again.
        await page.waitForSelector('html[data-i18n-ready="true"]', {timeout: PAGE_MS});
        await expect(card).toHaveAttribute('data-state', 'done', {timeout: PAGE_MS});
        await expect(link).toHaveAttribute('href', href);

        // An archive picked up is not news. Read once the card is done: had the pick-up announced it, the event would be
        // in the ring by then. The ring is the new page's own, since a reload starts it again.
        const names = await eventNames(page);
        expect(names, 'the new page keeps an event ring').not.toBeNull();
        expect(names, 'no backup.created for a job picked up after a reload').not.toContain('backup.created');
    });
});
