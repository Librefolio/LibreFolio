/**
 * Settings › Backup (workstream B): the backup of the whole instance (lot B5a) and its restore (lots B5b and B5c), from an
 * administrator's browser.
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
 * The restore, under it (`RestoreCard.svelte`, driven by `RestoreFlowController` of restoreFlow.svelte.ts): an archive is
 * uploaded, checked by the server on a copy, and its report opens (`RestoreReportModal.svelte`); once the word the report
 * shows is typed, the restore is confirmed and the server asked to restart at once, so that its next start applies it
 * (developer decision P8). The page then waits over everything (`RestartOverlay.svelte`) for the server to come back, and
 * reads what became of the restore with the restart's one-time ticket (lot B5c). Published: `restore-card` (`data-state`,
 * `data-error-code`, `data-busy`), `restart-overlay` (`data-outcome`, `data-reason`, `data-waiting`, `data-slow`), and
 * the steps as `backup.restore.*` events.
 *
 * Never restarted. `POST /backup/restore/restart` stops the server that answers it: here the lane's own, under every other
 * spec of the run. A fixture of every restore case answers it in the page (`page.route`, set before the first navigation):
 * 202, the restore waiting and a one-time ticket of the case's own; it is never sent on. The rest of the restart is played
 * on the same page: the probe of the server (`GET /system/ready`, which nothing else of the app reads) refused, then
 * answered; the outcome (`GET /backup/restore/outcome`) answered as the case needs, each read checked for the ticket in
 * `X-Restore-Ticket` and nowhere else; the end of every session that a kept restore brings, by clearing the page's
 * cookies. The app's offline-fallback service worker is blocked there, so that every request meets those routes.
 *   - FBKP-101: an archive over the upload limit (a small one, on a faked status) is refused before anything is sent;
 *   - FBKP-102: the confirmation word cannot be pasted — a real ControlOrMeta+V, its paste seen reaching the field and
 *     refused — only typed (the upload and the check faked: nothing reaches the server);
 *   - FBKP-103: rolled back (`first_start_failed`): the overlay says why, `restart-back` reads the status again, and the
 *     card shows the last result;
 *   - FBKP-104: still waiting, the instance blocked by its hosting provider: the overlay `still_pending` with
 *     `instance_blocked`; back, the restore still waits, and the card says why;
 *   - FBKP-105: the outcome route no longer knows the ticket (404): the status read with the session answers 401, so the
 *     restore was kept, and the page goes to the sign-in page;
 *   - FBKP-106: a restore confirmed through the API, found waiting at load: offered to restart or to cancel; cancelled from
 *     the card, and the server dropped its checked copy with it (B-17): confirming that check again answers 404
 *     `restore_stage_not_found`;
 *   - FBKP-107: the whole path, real but for the restart: the instance's own backup uploaded, checked (`checking`, its
 *     first read held for as long as the test looks at it), reported, the word typed key by key, the restore confirmed on
 *     the lane's server; then restarted, the server down and up, the outcome `committed` read with the ticket, and the
 *     page on the sign-in page, saying nothing;
 *   - FBKP-108: a secure backup (lot B4, decision 39) from the card: «secure», its password typed twice under the rules of
 *     `GET /backup/instance/options` (one character short refused), followed to done, the card and the job saying
 *     `encrypted`; its `.lfbk` downloaded (`LFBK`), then chosen in the restore card: the password asked before anything is
 *     sent, the envelope sent once and checked on the lane's server (`decrypting` first), the report as the server's,
 *     dropped; the password kept nowhere a script of the page could read;
 *   - FBKP-109: a wrong password: the case's own secure archive, made with the page's session through the API, chosen in
 *     the restore card; a wrong password refused (400 `wrong_password`) and asked again, the right one checking the same
 *     upload — one `PUT` of the archive, two `POST`s of its check —; dropped, the check and the upload gone.
 * FBKP-103 to FBKP-105 restart a restore found waiting on a faked status: none of them confirms anything on the server,
 * nor do FBKP-108 and FBKP-109, which drop what they check.
 * Not here either: the restore's states one by one, which restoreFlow.test.ts, RestoreCard.test.ts,
 * RestoreReportModal.test.ts and RestartOverlay.test.ts drive with a faked API.
 *
 * Serial, and here is what is shared: the instance builds ONE backup at a time — a second start is refused, 409
 * `backup_busy` —, checks one archive at a time (409 `restore_busy`) and keeps one restore waiting (409
 * `restore_already_pending`), so the tests run one after the other, each one ending what it started before the next one
 * begins. Desktop only, like every other serial spec: `mode: 'serial'` orders the tests of one project, not two.
 *
 * Ownership. Every job a test starts is recorded from the server's answer the moment it arrives. After the test, red or
 * green, each one is waited out if it still runs and deleted through `page.request` — the administrator's cookies — and
 * the `sessionStorage` key the card follows it by is cleared: a finished job would otherwise stay on the server for an
 * hour. Nothing reads a list it did not fill, and no setting is changed. A restore case owns the administrator's own API
 * session, apart from the page's cookies (two cases clear them): after it, red or green, whatever waits for the next
 * start of the lane's server is cancelled (`DELETE /backup/restore/pending`, 404 `restore_not_pending` the usual answer) —
 * a restore left confirmed there would be applied at that start —, and every check it started is waited out and dropped,
 * or found gone with the cancel (B-17). The archive FBKP-106 and FBKP-107 upload is the instance's own backup, made through
 * the API the first time one of them needs it, its job deleted at once, its file removed after the block. FBKP-108 and
 * FBKP-109 each make a secure one of their own, kept in the test's output folder; its job is the test's like any other.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `backup` of front-utility.
 */
import {randomBytes} from 'node:crypto';
import {mkdtemp, open, readFile, rm, stat, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {schemas} from '../../src/lib/api/generated';
import {expect, test, type APIRequestContext, type Locator, type Page, type Request as PageRequest} from '../fixtures/playwright';
import {eventSeq, waitForEvent} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {openSettingsTab} from '../fixtures/settings-tabs';
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
async function jobStatus(api: APIRequestContext, jobId: string): Promise<string> {
    const response = await api.get(jobUrl(jobId));
    if (response.status() === 404) return 'gone';
    if (!response.ok()) return `HTTP ${response.status()}`;
    return String(((await response.json()) as {status?: unknown}).status);
}

/**
 * Delete a job this test started, through an administrator's session (`page.request`, or a session of its own), waiting
 * it out first if it still runs: a running job refuses the delete (409).
 */
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
    for (const jobId of owned.jobs) await discardJob(page.request, jobId);
    if (onApp) await page.evaluate((key) => sessionStorage.removeItem(key), FOLLOWED_JOB_KEY);
});

test.describe('Settings › Backup — who gets the tab', () => {
    test('FBKP-001: a regular user has no Backup tab, and ?tab=backup opens the first tab instead', async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/settings?tab=backup');

        // Presence first: the bar is drawn up to its last tab everyone sees, and the page has chosen the tab it opens...
        await expect(page.getByTestId('settings-tab-about'), 'the bar is drawn, up to About, the last tab everyone sees').toBeVisible({timeout: PAGE_MS});
        await expect(page.getByTestId('settings-tab-profile'), '?tab=backup names no tab of this user: the first one opens').toHaveAttribute('aria-selected', 'true');
        await expect(page.getByTestId('profile-tab')).toBeVisible();

        // ...then the absence: the tab is left out of the bar, not hidden in it, and no backup body is drawn.
        // A regular user has no «Administration» at all (N69-2, decision D4 a): no group, no second bar, no member tab.
        await expect(page.getByTestId('settings-tab-administration')).toHaveCount(0);
        await expect(page.getByTestId('settings-tab-admin')).toHaveCount(0);
        await expect(page.getByTestId('settings-tab-backup')).toHaveCount(0);
        await expect(page.getByTestId('backup-tab')).toHaveCount(0);
    });

    test('FBKP-001b: an administrator has the Backup tab, and it opens the backup card', async ({page}) => {
        await login(page, TEST_ADMIN);
        await navigateTo(page, '/settings');

        await expect(page.getByTestId('settings-tab-profile'), 'precondition: /settings opens on its first tab').toHaveAttribute('aria-selected', 'true', {timeout: PAGE_MS});

        // Backup is a member of «Administration» (decision P13 b): opened through the group, in its second bar.
        await openSettingsTab(page, 'backup');
        const tab = page.getByTestId('settings-tab-backup');
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

// =====================================================================================================================
// The restore (lots B5b, B5c)
// =====================================================================================================================

const RESTORE_API = '/api/v1/backup/restore';
const RESTORE_STATUS = `${RESTORE_API}/status`;
const RESTORE_UPLOAD = `${RESTORE_API}/upload`;
const RESTORE_STAGE = `${RESTORE_API}/stage`;
const RESTORE_PENDING = `${RESTORE_API}/pending`;
/** Stops the server that answers it: never sent from this file (see «Never restarted» above). */
const RESTORE_RESTART = `${RESTORE_API}/restart`;
const RESTORE_OUTCOME = `${RESTORE_API}/outcome`;
/** What the page probes while the server restarts (`probeServer()` of backupApi.ts); nothing else of the app reads it. */
const SERVER_READY = '/api/v1/system/ready';
/** `RESTORE_TICKET_HEADER` of backupApi.ts, the way Playwright names request headers: lower-cased. */
const TICKET_HEADER = 'x-restore-ticket';
/** A check, read or dropped: `/backup/restore/stage/<stage id>`, not its `/confirm`. */
const CHECK_PATH = /^\/api\/v1\/backup\/restore\/stage\/[0-9a-f]{32}$/;
/** The phases of a running check (`RestoreStage.phase`). */
const CHECK_PHASES = /^(checking|unpacking|upgrading|verifying)$/;
/** The check of a faked restore: a well-formed id that the lane's server never gave. */
const FAKED_STAGE_ID = '5e2b7c9d1f3a48e6b0c4d2a19e7f3b86';
const MEGABYTE = 1024 * 1024;

// The archive goes to the lane's server from the page, in one request.
const UPLOAD_MS = 60_000;
// The server checks the archive on a copy: unpacked, brought to this LibreFolio's schema, verified.
const CHECK_MS = 90_000;
// The restart as the page lives it: one probe a second (`pollMs` of restoreFlow.svelte.ts), the outcome read at the first
// one answered. A deadline, never a delay.
const RESTART_MS = 15_000;
// A restore case, at worst: an archive of the instance, its upload and its check, then the restart.
const RESTORE_TEST_MS = 240_000;
// The fixture of a restore case, on a budget of its own: the administrator's sign-in, then the clean-up, which may wait
// out a check still running.
const LANE_MS = CHECK_MS + 60_000;

type RestoreStatus = ReturnType<typeof schemas.RestoreStatus.parse>;
type ApiResponse = Awaited<ReturnType<APIRequestContext['get']>>;
/** What a route answers in the server's place. */
type Answer = {status: number; json: unknown};
/** An archive to choose: a file on disk, or bytes made by the case. */
type ArchiveFile = string | {name: string; mimeType: string; buffer: Buffer};
/** The instance's own backup, on disk. */
type InstanceArchive = {path: string; size: number};
/** What makes API sessions: the `request` of the `playwright` fixture. */
type ApiSessions = {newContext(options?: {baseURL?: string}): Promise<APIRequestContext>};

/** What one restore case owns, and how the page under it is answered in the server's place. */
type RestoreLane = {
    /** The administrator's own API session, apart from the page's cookies (two cases clear them): the server's side of the asserts, and the clean-up. */
    admin: APIRequestContext;
    /** The case confirms a restore on the lane's server (FBKP-106, FBKP-107); every other one fakes it. */
    realConfirm: boolean;
    /** Checks the case started on the lane's server, from the server's answers: dropped after it. */
    checks: Set<string>;
    /** Those answers still being read: the clean-up waits for them. */
    reading: Promise<void>[];
    /** The one-time ticket that the restart answered here hands out: the case's own. */
    ticket: string;
    /** Restart requests answered here; none is ever sent on. */
    restarts: number;
    /** The server the page probes: it refuses connections until the case brings it up. */
    serverUp: boolean;
    probesDown: number;
    probesUp: number;
    /** What `GET /backup/restore/outcome` answers once the server is up; `null` until the case says. */
    outcome: Answer | null;
    /** What `GET /backup/restore/status` answers; `null`: the lane's server answers it. */
    status: Answer | null;
    /** Every read of the outcome, and every faked read of the status, in order, with the ticket each one carried. */
    reads: Array<{what: 'outcome' | 'status'; url: string; ticket: string | null}>;
    /** Every request but the outcome's that carried the ticket. */
    ticketLeaks: string[];
    /** An answer that could not be given here: its request was refused, never sent on. */
    faults: string[];
};

function checkUrl(stageId: string): string {
    return `${RESTORE_STAGE}/${stageId}`;
}

/** The stable `detail.code` of a refusal. */
async function errorCode(response: ApiResponse): Promise<unknown> {
    return ((await response.json()) as {detail?: {code?: unknown}}).detail?.code;
}

/** The restore's status as the lane's server tells it, checked against the generated client's schema. */
async function readStatus(api: APIRequestContext): Promise<RestoreStatus> {
    const response = await api.get(RESTORE_STATUS);
    expect(response.status(), `GET ${RESTORE_STATUS}`).toBe(200);
    return schemas.RestoreStatus.parse(await response.json());
}

/** A check as the lane's server tells it, checked against the schema: what the cases read of it. */
async function readCheck(api: APIRequestContext, stageId: string): Promise<{status: string; errorCode: unknown; restorable: unknown}> {
    const response = await api.get(checkUrl(stageId));
    expect(response.status(), `GET ${checkUrl(stageId)}`).toBe(200);
    const body: unknown = await response.json();
    schemas.RestoreStage.parse(body);
    const check = body as {status: string; error_code?: unknown; report?: {restorable?: unknown} | null};
    return {status: check.status, errorCode: check.error_code ?? null, restorable: check.report?.restorable ?? null};
}

/** A check's status as the lane's server tells it: `gone` once there is no such check, `HTTP <n>` for an answer that is no check. */
async function checkStatus(api: APIRequestContext, stageId: string): Promise<string> {
    const response = await api.get(checkUrl(stageId));
    if (response.status() === 404) return 'gone';
    if (!response.ok()) return `HTTP ${response.status()}`;
    return String(((await response.json()) as {status?: unknown}).status);
}

/** Drop a check this case started, waiting it out first if it still runs: a running check refuses the drop (409). */
async function discardCheck(api: APIRequestContext, stageId: string): Promise<void> {
    let status = '';
    await expect
        .poll(
            async () => {
                status = await checkStatus(api, stageId);
                return status;
            },
            {message: `restore check ${stageId} has ended, so the clean-up can drop it`, timeout: CHECK_MS},
        )
        .toMatch(/^(gone|done|failed)$/);
    if (status !== 'gone') {
        const dropped = await api.delete(checkUrl(stageId));
        expect(dropped.status(), `DELETE ${checkUrl(stageId)}`).toBe(204);
    }
    expect(await checkStatus(api, stageId), `restore check ${stageId} is gone from the server`).toBe('gone');
}

/**
 * Cancel the restore waiting for the next start of the lane's server, if one waits: 204 when one did, 404
 * `restore_not_pending` otherwise. Tried again on a transient failure: this is the clean-up that must not be missed.
 */
async function cancelWhateverWaits(api: APIRequestContext): Promise<number> {
    let answered = 0;
    await expect(async () => {
        const response = await api.delete(RESTORE_PENDING);
        answered = response.status();
        if (answered === 204) return;
        expect(answered, `DELETE ${RESTORE_PENDING}`).toBe(404);
        expect(await errorCode(response), `DELETE ${RESTORE_PENDING}: nothing waits`).toBe('restore_not_pending');
    }, "the clean-up cancels whatever waits for the next start of the lane's server").toPass({timeout: PAGE_MS});
    return answered;
}

/** An API session of the administrator's own, signed in the way the page signs in. */
async function signedInAdministrator(sessions: ApiSessions, baseURL: string | undefined): Promise<APIRequestContext> {
    const api = await sessions.newContext({baseURL});
    const response = await api.post('/api/v1/auth/login', {data: {username: TEST_ADMIN.username, password: TEST_ADMIN.password}});
    if (response.status() !== 200) {
        await api.dispose();
        throw new Error(`The administrator's API session: POST /api/v1/auth/login answered ${response.status()}`);
    }
    return api;
}

/**
 * The status of a faked restore: by default one the administrator confirmed, waiting for the next start. Checked against
 * the generated client's schema when built, so that a contract that moved fails the case here, with Zod's own message.
 */
function fakedRestore(fields: Partial<RestoreStatus> = {}): RestoreStatus {
    return schemas.RestoreStatus.parse({
        state: 'pending',
        stage_id: FAKED_STAGE_ID,
        confirmed_at: '2026-10-15T09:45:03Z',
        confirmed_by: TEST_ADMIN.username,
        backup_created_at: '2026-10-15T09:41:12Z',
        backup_app_version: '0.0.0-e2e',
        action: 'same',
        finished_at: null,
        reason: null,
        waiting: null,
        upload_limit_mb: 0,
        ...fields,
    });
}

/** What the outcome route answers, 200 and the restore's state, checked against the schema. */
function outcomeAnswer(fields: Record<string, unknown>): Answer {
    return {status: 200, json: schemas.RestoreOutcome.parse(fields)};
}

// ---------------------------------------------------------------------------
// The server's part, played in the page
// ---------------------------------------------------------------------------

/**
 * Answer `POST /backup/restore/restart` here, always: 202, the restore waiting (the case's faked status, or the lane's
 * own) and the case's one-time ticket. Never sent on — the real one stops the lane's server —, not even when the answer
 * cannot be built: then it is refused here, and recorded as a fault.
 */
async function routeTheRestart(page: Page, lane: RestoreLane): Promise<void> {
    await page.route(
        // A trailing slash too: no spelling of the path may slip past to the server.
        (url) => url.pathname.replace(/\/+$/, '') === RESTORE_RESTART,
        async (route) => {
            lane.restarts += 1;
            let accepted: unknown;
            try {
                const waiting = lane.status?.status === 200 ? lane.status.json : await readStatus(lane.admin);
                accepted = schemas.RestoreRestartAccepted.parse({...(waiting as RestoreStatus), outcome_ticket: lane.ticket});
            } catch (error) {
                lane.faults.push(`${RESTORE_RESTART}: ${String(error)}`);
                await route.abort('failed');
                return;
            }
            await route.fulfill({status: 202, json: accepted});
        },
    );
}

/** The server the page probes while it restarts: refused (connection refused) until the case brings it up, then ready. */
async function routeTheServer(page: Page, lane: RestoreLane): Promise<void> {
    const ready = schemas.ReadinessResponse.parse({status: 'ready', checks: {database: 'ok', migrations: 'ok'}});
    await page.route(
        (url) => url.pathname === SERVER_READY,
        async (route) => {
            if (!lane.serverUp) {
                lane.probesDown += 1;
                await route.abort('connectionrefused');
                return;
            }
            lane.probesUp += 1;
            await route.fulfill({json: ready});
        },
    );
}

/** `GET /backup/restore/outcome`, answered here as the case sets it once the server is up; every read recorded with the ticket it carried. */
async function routeTheOutcome(page: Page, lane: RestoreLane): Promise<void> {
    await page.route(
        (url) => url.pathname === RESTORE_OUTCOME,
        async (route) => {
            const request = route.request();
            lane.reads.push({what: 'outcome', url: request.url(), ticket: await request.headerValue(TICKET_HEADER)});
            if (!lane.serverUp || lane.outcome === null) {
                await route.abort('connectionrefused');
                return;
            }
            await route.fulfill(lane.outcome);
        },
    );
}

/** `GET /backup/restore/status`: the lane's own unless the case fakes it; a faked read recorded with the ticket it carried. */
async function routeTheStatus(page: Page, lane: RestoreLane): Promise<void> {
    await page.route(
        (url) => url.pathname === RESTORE_STATUS,
        async (route) => {
            const request = route.request();
            if (lane.status === null || request.method() !== 'GET') {
                await route.fallback();
                return;
            }
            lane.reads.push({what: 'status', url: request.url(), ticket: await request.headerValue(TICKET_HEADER)});
            await route.fulfill(lane.status);
        },
    );
}

/** Record every request but the outcome's that carries the ticket: in its URL, or in the header that is the outcome's alone. */
function watchTheTicket(page: Page, lane: RestoreLane): void {
    page.on('request', (request) => {
        const url = request.url();
        const header = request.headers()[TICKET_HEADER];
        const toOutcome = new URL(url).pathname === RESTORE_OUTCOME;
        if (url.includes(lane.ticket) || (header !== undefined && !toOutcome)) lane.ticketLeaks.push(`${request.method()} ${url}`);
    });
}

/**
 * Answer the upload and the check of one archive in the server's place, so that its report opens without the lane's
 * server ever seeing the archive: `PUT /upload` 201, `POST /stage` 202 and running, the check's first read done with a
 * restorable report, its drop 204. Anything else under `/stage` — a confirmation above all — is refused here, recorded.
 */
async function fakeTheCheck(page: Page, size: number): Promise<{calls: string[]}> {
    const uploadId = randomBytes(16).toString('hex');
    const stageId = randomBytes(16).toString('hex');
    const createdAt = '2026-10-15T09:41:20Z';
    const upload = schemas.RestoreUpload.parse({upload_id: uploadId, size, kind: 'zip'});
    const running = schemas.RestoreStage.parse({stage_id: stageId, status: 'running', phase: 'checking', done_bytes: 0, total_bytes: 0, created_at: createdAt, finished_at: null, error_code: null, report: null});
    const done = schemas.RestoreStage.parse({
        stage_id: stageId,
        status: 'done',
        phase: null,
        done_bytes: size,
        total_bytes: size,
        created_at: createdAt,
        finished_at: '2026-10-15T09:41:31Z',
        error_code: null,
        report: {
            backup_created_at: '2026-10-15T09:41:12Z',
            backup_app_version: '0.0.0-e2e',
            backup_origin: 'ui',
            backup_revision: 'e2e000000001',
            app_version: '0.0.0-e2e',
            head_revision: 'e2e000000001',
            action: 'same',
            migrations: [],
            post_migration_fixes: [],
            tables: {users: {before: 9, after: 9}},
            foreign_key_violations_before: 0,
            foreign_key_violations_after: 0,
            files: 4,
            files_size: 2_097_152,
            database_size: 1_048_576,
            instance_key_included: true,
            encrypted: false,
            secrets_rekeyed: 0,
            secrets_unreadable: {system: 0, user: 0},
            administrators: [TEST_ADMIN.username],
            warnings: [],
            blockers: [],
            control_totals: 'same',
            control_totals_differences: [],
            control_totals_differences_count: 0,
            restorable: true,
            expires_at: '2026-10-16T09:41:31Z',
        },
    });
    const calls: string[] = [];
    await page.route(
        (url) => url.pathname === RESTORE_UPLOAD || url.pathname === RESTORE_STAGE || url.pathname.startsWith(`${RESTORE_STAGE}/`),
        async (route) => {
            const request = route.request();
            const call = `${request.method()} ${new URL(request.url()).pathname}`;
            calls.push(call);
            if (call === `PUT ${RESTORE_UPLOAD}`) return route.fulfill({status: 201, json: upload});
            if (call === `POST ${RESTORE_STAGE}`) return route.fulfill({status: 202, json: running});
            if (call === `GET ${checkUrl(stageId)}`) return route.fulfill({json: done});
            if (call === `DELETE ${checkUrl(stageId)}`) return route.fulfill({status: 204});
            return route.fulfill({status: 404, json: {detail: {code: 'restore_stage_not_found', message: 'No check has this id'}}});
        },
    );
    return {calls};
}

/**
 * Hold the page's reads of a check until the returned `release()`: the check runs on the server meanwhile, and the card
 * stays `checking` for as long as the test looks at it. Once released, every read goes on to the server.
 */
async function holdCheckReads(page: Page): Promise<() => void> {
    let release: () => void = () => undefined;
    const released = new Promise<void>((resolve) => {
        release = () => resolve();
    });
    await page.route(
        (url) => CHECK_PATH.test(url.pathname),
        async (route) => {
            if (route.request().method() === 'GET') await released;
            await route.fallback();
        },
    );
    return () => release();
}

/** Record every check the page starts on the lane's server, from the server's answer, whatever the case does next. */
function recordStartedChecks(page: Page, lane: RestoreLane): void {
    page.on('response', (response) => {
        if (response.request().method() !== 'POST' || new URL(response.url()).pathname !== RESTORE_STAGE) return;
        lane.reading.push(
            response.json().then(
                (body: {stage_id?: unknown} | null) => {
                    if (typeof body?.stage_id === 'string') lane.checks.add(body.stage_id);
                },
                // An answer that cannot be read started no check this case could drop.
                () => undefined,
            ),
        );
    });
}

// ---------------------------------------------------------------------------
// The archive, and a restore made through the API
// ---------------------------------------------------------------------------

/** Where the instance's archive waits on disk between the cases that upload it; removed after the block. */
let archiveDir: string | null = null;
let archiveMade: Promise<InstanceArchive> | null = null;

/** The instance's own backup, as an administrator downloads it: made the first time a case needs it, once for the block. */
function instanceArchive(api: APIRequestContext): Promise<InstanceArchive> {
    archiveMade ??= makeInstanceArchive(api);
    return archiveMade;
}

async function makeInstanceArchive(api: APIRequestContext): Promise<InstanceArchive> {
    const started = await api.post(BACKUP_API);
    expect(started.status(), `POST ${BACKUP_API}`).toBe(202);
    const jobId = schemas.InstanceBackupJob.parse(await started.json()).job_id;
    try {
        await expect.poll(() => jobStatus(api, jobId), {message: `backup job ${jobId} has ended`, timeout: BACKUP_MS}).toMatch(/^(gone|done|failed)$/);
        expect(await jobStatus(api, jobId), 'the backup of the instance wrote its archive').toBe('done');
        const file = await api.get(`${jobUrl(jobId)}/file`, {timeout: BACKUP_MS});
        expect(file.status(), `GET ${jobUrl(jobId)}/file`).toBe(200);
        const body = await file.body();
        expect(body.subarray(0, 4).toString('hex'), 'a zip archive: it opens with a local file header').toBe(ZIP_MAGIC);
        archiveDir ??= await mkdtemp(join(tmpdir(), 'librefolio-restore-e2e-'));
        const path = join(archiveDir, 'instance-backup.zip');
        await writeFile(path, body);
        return {path, size: body.length};
    } finally {
        // The archive is on disk now: its job need not stay on the server for its hour.
        await discardJob(api, jobId);
    }
}

/** Upload the archive and check it through the API, as the card does, up to its report: the check's id, the case's from the server's answer. */
async function checkThroughApi(lane: RestoreLane, archive: InstanceArchive): Promise<string> {
    const uploaded = await lane.admin.put(RESTORE_UPLOAD, {data: await readFile(archive.path), headers: {'Content-Type': 'application/octet-stream'}, timeout: UPLOAD_MS});
    expect(uploaded.status(), `PUT ${RESTORE_UPLOAD}`).toBe(201);
    const upload = schemas.RestoreUpload.parse(await uploaded.json());
    expect(upload.size, 'the server received the whole archive').toBe(archive.size);

    const started = await lane.admin.post(RESTORE_STAGE, {data: {upload_id: upload.upload_id}});
    expect(started.status(), `POST ${RESTORE_STAGE}`).toBe(202);
    const stageId = schemas.RestoreStage.parse(await started.json()).stage_id;
    lane.checks.add(stageId);

    await expect.poll(() => checkStatus(lane.admin, stageId), {message: `restore check ${stageId} has ended`, timeout: CHECK_MS}).not.toBe('running');
    const check = await readCheck(lane.admin, stageId);
    expect(check.errorCode, 'the check accepted the archive').toBeNull();
    expect(check.status).toBe('done');
    expect(check.restorable, "the instance's own archive can be restored").toBe(true);
    return stageId;
}

/** Confirm the restore of a checked archive through the API: from now on, the next start of the lane's server would apply it. */
async function confirmThroughApi(lane: RestoreLane, stageId: string): Promise<void> {
    lane.realConfirm = true;
    const confirmed = await lane.admin.post(`${checkUrl(stageId)}/confirm`);
    expect(confirmed.status(), `POST ${checkUrl(stageId)}/confirm`).toBe(202);
    const waiting = schemas.RestoreStatus.parse(await confirmed.json());
    expect(waiting.state, 'the restore waits for the next start').toBe('pending');
    expect(waiting.stage_id).toBe(stageId);
}

// ---------------------------------------------------------------------------
// A secure backup (lot B4): its password, its envelope, and what the page sends of it
// ---------------------------------------------------------------------------

/** What a secure backup's password must meet: the accounts' rules, with a longer minimum (P12). */
const BACKUP_OPTIONS = `${BACKUP_API}/options`;
/** A secure backup's archive: `archive_name(created_at, encrypted=True)` of jobs.py. */
const ENVELOPE_NAME = /^librefolio-backup-\d{8}-\d{6}\.lfbk$/;
/** An envelope opens with `LFBK` (`MAGIC` of envelope.py), in hex. */
const ENVELOPE_MAGIC = '4c46424b';
/** P12: a backup's password has at least this many characters (`ARCHIVE_PASSWORD_MIN_LENGTH` of secure.py). */
const ARCHIVE_MIN_LENGTH = 12;
/**
 * The row of the strength meter's checklist that draws each rule, by the rule's code: `password-rule-<key>` of
 * PasswordStrength.svelte (`RULE_UI_KEYS` of passwordRules.ts), written out here: the test id is the contract.
 */
const RULE_ROWS: Readonly<Record<string, string>> = {min_length: 'minLength', uppercase: 'hasUppercase', lowercase: 'hasLowercase', digit: 'hasNumber', special: 'hasSpecial'};
/** The archive sent to the server, and the start of its check: the requests a restore of an envelope is counted by. */
const UPLOAD_CALL = `PUT ${RESTORE_UPLOAD}`;
const CHECK_CALL = `POST ${RESTORE_STAGE}`;

type PasswordRule = {code: string; value: number | null};
/** One request the page sent: what, its JSON body (a start of a check's), and what the server answered, once it did. */
type SentRequest = {call: string; body: unknown; answer: Promise<{status: number; json: unknown} | null>};

/** The rules of a secure backup's password, as the server gives them, checked against the generated client's schema. */
async function archivePasswordRules(api: APIRequestContext): Promise<PasswordRule[]> {
    const response = await api.get(BACKUP_OPTIONS);
    expect(response.status(), `GET ${BACKUP_OPTIONS}`).toBe(200);
    // The client's explicit type widens `value` to an array branch its schema never lets through: narrowed here.
    return schemas.InstanceBackupOptions.parse(await response.json()).password_rules.map(({code, value}) => ({code, value: typeof value === 'number' ? value : null}));
}

/**
 * The length those rules ask for, once each of them is known to be a rule `passwordOf()` meets: a rule this case does
 * not know fails it here, by its code, rather than as a backup refused further on.
 */
function minLengthOf(rules: PasswordRule[]): number {
    expect(
        rules.map(({code}) => code).filter((code) => !Object.hasOwn(RULE_ROWS, code)),
        'the options name a rule the passwords of this case are not built for',
    ).toEqual([]);
    const minimum = rules.find(({code}) => code === 'min_length')?.value ?? null;
    expect(minimum, `the options ask a backup's password for at least ${ARCHIVE_MIN_LENGTH} characters (P12)`).toBeGreaterThanOrEqual(ARCHIVE_MIN_LENGTH);
    return minimum ?? ARCHIVE_MIN_LENGTH;
}

/**
 * A password of `length` characters: an upper-case letter, a lower-case one, a digit and a symbol — every class a rule
 * can ask for —, the rest random, so that nothing on a page could hold it by chance.
 */
function passwordOf(length: number): string {
    return `Aa1!${randomBytes(length).toString('hex')}`.slice(0, length);
}

/**
 * A secure backup made through the API, with the session of `api`, followed to done: its envelope saved as
 * `outputPath(<its name>)`, then its job deleted. The job is the test's from the server's first answer: the afterEach
 * deletes it too, whatever happens here.
 */
async function secureArchiveThroughApi(api: APIRequestContext, password: string, outputPath: (name: string) => string): Promise<InstanceArchive> {
    const started = await api.post(BACKUP_API, {data: {password}});
    expect(started.status(), `POST ${BACKUP_API} with a password`).toBe(202);
    const jobId = schemas.InstanceBackupJob.parse(await started.json()).job_id;
    owned.jobs.add(jobId);
    try {
        await expect.poll(() => jobStatus(api, jobId), {message: `secure backup job ${jobId} has ended`, timeout: BACKUP_MS}).toMatch(/^(gone|done|failed)$/);
        const read = await api.get(jobUrl(jobId));
        expect(read.status(), `GET ${jobUrl(jobId)}`).toBe(200);
        const job = schemas.InstanceBackupJob.parse(await read.json());
        // The reason before the state: a backup that failed reds with its code.
        expect(job.error_code ?? null, 'the secure backup ended without an error').toBeNull();
        expect(job.status).toBe('done');
        expect(job.encrypted, 'the job of a secure backup says its archive is encrypted').toBe(true);
        const name = job.file_name ?? '';
        expect(name).toMatch(ENVELOPE_NAME);

        const file = await api.get(`${jobUrl(jobId)}/file`, {timeout: BACKUP_MS});
        expect(file.status(), `GET ${jobUrl(jobId)}/file`).toBe(200);
        expect(file.headers()['content-type'], 'an envelope is not served as a zip').toMatch(/^application\/octet-stream/);
        const body = await file.body();
        expect(body.length, 'the whole envelope: as many bytes as the job reported').toBe(job.file_size);
        expect(body.subarray(0, 4).toString('hex'), 'an envelope: it opens with LFBK').toBe(ENVELOPE_MAGIC);
        const path = outputPath(name);
        await writeFile(path, body);
        return {path, size: body.length};
    } finally {
        // The envelope is on disk now: its job need not stay on the server for its hour.
        await discardJob(api, jobId);
    }
}

/** What the server answered a request of the page, once it did: its status and its JSON (`null` when it had none). */
async function answerOf(request: PageRequest): Promise<{status: number; json: unknown} | null> {
    const response = await request.response().catch(() => null);
    if (response === null) return null;
    return {status: response.status(), json: await response.json().catch(() => null)};
}

/**
 * Record, in the order the page sends them, every upload of an archive and every start of its check — the requests
 * themselves, not the card's account of them —, with the body of each start, and each answer once it comes.
 */
function watchUploadsAndChecks(page: Page): SentRequest[] {
    const sent: SentRequest[] = [];
    page.on('request', (request) => {
        const call = `${request.method()} ${new URL(request.url()).pathname}`;
        if (call !== UPLOAD_CALL && call !== CHECK_CALL) return;
        // The upload's body is the archive itself, not read; a start's is JSON.
        let body: unknown = null;
        if (call === CHECK_CALL) {
            try {
                body = request.postDataJSON();
            } catch {
                body = request.postData();
            }
        }
        sent.push({call, body, answer: answerOf(request)});
    });
    return sent;
}

/** The server's report of a check, checked against the schema. */
async function readReport(api: APIRequestContext, stageId: string): Promise<ReturnType<typeof schemas.RestoreStageReport.parse>> {
    const response = await api.get(checkUrl(stageId));
    expect(response.status(), `GET ${checkUrl(stageId)}`).toBe(200);
    return schemas.RestoreStageReport.parse(schemas.RestoreStage.parse(await response.json()).report);
}

// ---------------------------------------------------------------------------
// The page
// ---------------------------------------------------------------------------

/** Sign the administrator in, open Settings › Backup, and wait for the restore card to have read the restore's status. */
async function openRestoreCard(page: Page): Promise<Locator> {
    await openBackupTab(page);
    const card = page.getByTestId('restore-card');
    await expect(card).toBeVisible();
    // Busy from its first render until the status is read.
    await expect(card, "the card has read the restore's status").toHaveAttribute('data-busy', 'false', {timeout: PAGE_MS});
    return card;
}

/** Choose an archive through the card's own button, as the administrator does: the picker it opens takes one archive. */
async function chooseArchive(page: Page, archive: ArchiveFile): Promise<void> {
    const choosing = page.waitForEvent('filechooser', {timeout: PAGE_MS});
    await page.getByTestId('restore-choose').click();
    const chooser = await choosing;
    expect(chooser.isMultiple(), 'the picker takes one archive').toBe(false);
    await expect(page.getByTestId('restore-file-input'), 'the picker suggests zip archives').toHaveAttribute('accept', /\.zip/);
    await chooser.setFiles(archive);
}

/** The word the report asks for, as the page shows it: picked at random in the list of the interface language (P8). */
async function confirmationWord(page: Page): Promise<string> {
    const shown = page.getByTestId('restore-confirm-word');
    await expect(shown, 'the report shows a word to type').toHaveText(/^\s*\S+\s*$/);
    return ((await shown.textContent()) ?? '').trim();
}

/** Choose a secure backup's envelope in the restore card: its password is asked first, and nothing is sent before it. */
async function chooseEnvelope(page: Page, card: Locator, path: string, sent: SentRequest[]): Promise<void> {
    await expect(page.getByTestId('restore-file-input'), 'the picker suggests secure backups too').toHaveAttribute('accept', /\.lfbk/);
    await chooseArchive(page, path);
    await expect(card, 'a secure backup: its password first').toHaveAttribute('data-state', 'password', {timeout: PAGE_MS});
    await expect(card, 'the card waits for the administrator, not for the server').toHaveAttribute('data-busy', 'false');
    await expect(card.getByTestId('restore-password-form')).toBeVisible();
    await expect(card.getByTestId('restore-password-error'), 'no password tried yet: no error').toHaveCount(0);
    expect(
        sent.map(({call}) => call),
        'nothing is sent before the password',
    ).toEqual([]);
}

/** Type a secure backup's password in the restore card, and send it. */
async function submitRestorePassword(card: Locator, password: string): Promise<void> {
    const field = card.getByTestId('restore-password');
    await field.fill(password);
    await expect(field).toHaveValue(password);
    await card.getByTestId('restore-password-submit').click();
}

/** Drop the checked archive from its report, as the administrator does: the card idle again, the check gone from the server, nothing restored. */
async function dropTheReport(page: Page, card: Locator, lane: RestoreLane, stageId: string): Promise<void> {
    const since = await eventSeq(page);
    await page.getByTestId('restore-drop').click();
    await expect(card).toHaveAttribute('data-state', 'idle', {timeout: PAGE_MS});
    const cancelled = await waitForEvent(page, 'backup.restore.cancelled', {since});
    expect(cancelled.detail).toEqual({what: 'check'});
    const gone = await lane.admin.get(checkUrl(stageId));
    expect(gone.status(), `GET ${checkUrl(stageId)} after the drop`).toBe(404);
    expect(await errorCode(gone)).toBe('restore_stage_not_found');
    expect((await readStatus(lane.admin)).state, 'nothing restored: no restore waits for the next start').not.toBe('pending');
    expect(lane.restarts, 'nothing restarted').toBe(0);
}

/**
 * From a restore found waiting at load (the case fakes the status): restart it from the card. The restart is answered
 * here, and the overlay waits for the server. The event count before the click, for the restart's events.
 */
async function restartFromPending(page: Page, lane: RestoreLane): Promise<number> {
    const card = await openRestoreCard(page);
    await expect(card, 'precondition: the faked status shows a restore waiting').toHaveAttribute('data-state', 'pending');
    const since = await eventSeq(page);
    await page.getByTestId('restore-restart').click();
    await waitForEvent(page, 'backup.restore.restart.requested', {since});
    expect(lane.restarts, 'one restart asked, and answered here').toBe(1);
    await expect(card).toHaveAttribute('data-state', 'restarting');
    await expect(page.getByTestId('restart-overlay')).toHaveAttribute('data-outcome', 'waiting');
    return since;
}

/**
 * The server restarts under the page: its probes refused until the page has seen it gone — the overlay waiting, nothing
 * read of the outcome —, then `beforeUp` (what the restart changed meanwhile), then answered again. Returns once the page
 * has found it back.
 */
async function serverComesBack(page: Page, lane: RestoreLane, beforeUp?: () => Promise<void>): Promise<void> {
    const overlay = page.getByTestId('restart-overlay');
    await expect.poll(() => lane.probesDown, {message: 'the page probes the restarting server, refused while it is down', timeout: RESTART_MS}).toBeGreaterThan(0);
    await expect(overlay, 'the server is down: the overlay waits').toHaveAttribute('data-outcome', 'waiting');
    await expect(overlay, 'and is not slow yet').toHaveAttribute('data-slow', 'false');
    expect(
        lane.reads.filter((read) => read.what === 'outcome'),
        'nothing is read of the outcome while the server is down',
    ).toEqual([]);
    if (beforeUp) await beforeUp();
    lane.serverUp = true;
    await expect.poll(() => lane.probesUp, {message: 'the page probes the server again, and it answers', timeout: RESTART_MS}).toBeGreaterThan(0);
}

/** Every read of the outcome carried the restart's ticket in `X-Restore-Ticket`, never in its URL; no other request carried it. */
function expectTicketInItsHeaderOnly(lane: RestoreLane): void {
    const reads = lane.reads.filter((read) => read.what === 'outcome');
    expect(reads.length, 'the outcome was read').toBeGreaterThan(0);
    for (const read of reads) {
        expect(read.ticket, `GET ${RESTORE_OUTCOME} carries the ticket of the restart in X-Restore-Ticket`).toBe(lane.ticket);
        expect(read.url, 'the ticket never travels in the URL').not.toContain(lane.ticket);
    }
    expect(lane.ticketLeaks, 'no other request carries the ticket').toEqual([]);
}

/** The page went to the sign-in page, saying nothing (P8): `/` with no page to come back to, the form, and no message. */
async function expectSignInPage(page: Page): Promise<void> {
    await expect(page, 'on to the sign-in page, with no page to come back to').toHaveURL((url) => url.pathname === '/' && url.search === '', {timeout: PAGE_MS});
    await expect(page.getByTestId('login-page')).toBeVisible({timeout: PAGE_MS});
    await expect(page.getByTestId('login-form'), 'the sign-in form, drawn').toBeVisible();
    // Absences, read once the form is drawn: nothing is said of the restore.
    await expect(page.getByTestId('login-success'), 'no message on the sign-in page').toHaveCount(0);
    await expect(page.getByTestId('login-error')).toHaveCount(0);
    await expect(page.getByTestId('toast-success'), 'no success toast').toHaveCount(0);
    await expect(page.getByTestId('restart-overlay'), 'a new page: the overlay went with the old one').toHaveCount(0);
}

/** All that a script of the page could read later: its event ring, its storages and its cookies, as one text. */
async function pageKeeps(page: Page): Promise<string> {
    return page.evaluate(() => {
        const stored = (store: Storage) => Array.from({length: store.length}, (_, index) => `${store.key(index)}=${store.getItem(store.key(index) ?? '')}`);
        const ring = (window as unknown as {__lf?: {events?: unknown[]}}).__lf?.events ?? [];
        return [JSON.stringify(ring), ...stored(sessionStorage), ...stored(localStorage), document.cookie].join('\n');
    });
}

/** The names of the page's events recorded after `since`, oldest first. */
async function eventNamesSince(page: Page, since: number): Promise<string[]> {
    return page.evaluate((after) => ((window as unknown as {__lf?: {events?: Array<{seq: number; name: string}>}}).__lf?.events ?? []).filter((event) => event.seq > after).map((event) => event.name), since);
}

type PasteSeen = {prevented: boolean; text: string};

/**
 * Record every paste that reaches the confirmation field, as the page left it: on the window, in the bubbling phase,
 * after every handler of the page has had its say — refused or not, and what it carried.
 */
async function watchPastes(page: Page): Promise<void> {
    await page.evaluate(() => {
        const seen: Array<{prevented: boolean; text: string}> = [];
        (window as unknown as {__restorePastes?: typeof seen}).__restorePastes = seen;
        window.addEventListener('paste', (event) => {
            if ((event.target as Element | null)?.getAttribute?.('data-testid') !== 'restore-confirm-input') return;
            seen.push({prevented: event.defaultPrevented, text: event.clipboardData?.getData('text/plain') ?? ''});
        });
    });
}

async function pastesSeen(page: Page): Promise<PasteSeen[]> {
    return page.evaluate(() => (window as unknown as {__restorePastes?: Array<{prevented: boolean; text: string}>}).__restorePastes ?? []);
}

// ---------------------------------------------------------------------------
// The cases
// ---------------------------------------------------------------------------

/**
 * After a restore case, red or green: nothing waits for the next start of the lane's server — a restore left confirmed
 * there would be applied at that start —, every check the case started is waited out and dropped, and every answer the
 * case gave in the server's place was given.
 */
async function cleanUpRestore(lane: RestoreLane): Promise<void> {
    await Promise.all(lane.reading);
    const cancelled = await cancelWhateverWaits(lane.admin);
    for (const stageId of lane.checks) await discardCheck(lane.admin, stageId);
    expect((await readStatus(lane.admin)).state, "after the case, no restore waits for the next start of the lane's server").not.toBe('pending');
    if (!lane.realConfirm) expect(cancelled, "a restore waited on the lane's server, though this case confirms none there (cancelled now)").toBe(404);
    expect(lane.faults, "every request the case answers in the server's place was answered").toEqual([]);
    expect(lane.ticketLeaks, "no request but the outcome's carried the ticket").toEqual([]);
}

const restoreTest = test.extend<{lane: RestoreLane}>({
    lane: [
        async ({page, playwright, baseURL}, use) => {
            const admin = await signedInAdministrator(playwright.request, baseURL);
            const lane: RestoreLane = {
                admin,
                realConfirm: false,
                checks: new Set(),
                reading: [],
                ticket: randomBytes(32).toString('base64url'),
                restarts: 0,
                serverUp: false,
                probesDown: 0,
                probesUp: 0,
                outcome: null,
                status: null,
                reads: [],
                ticketLeaks: [],
                faults: [],
            };
            try {
                // Before the first navigation: no request of the page goes round them.
                await routeTheRestart(page, lane);
                await routeTheServer(page, lane);
                await routeTheOutcome(page, lane);
                await routeTheStatus(page, lane);
                watchTheTicket(page, lane);
                await use(lane);
            } finally {
                try {
                    await cleanUpRestore(lane);
                } finally {
                    await admin.dispose();
                }
            }
        },
        {timeout: LANE_MS},
    ],
});

restoreTest.describe('Settings › Backup — a restore of the instance', () => {
    // Serial: one check at a time on a server (409 `restore_busy`) and one restore waiting (409 `restore_already_pending`):
    // FBKP-106 to FBKP-109 take turns on the lane's server, each one cancelling and dropping what it left before the
    // next one begins; FBKP-108 and FBKP-109 also make a backup each, one at a time on the instance (409 `backup_busy`).
    // The faked cases come first, so that a broken real path cannot hide them.
    restoreTest.describe.configure({mode: 'serial', timeout: RESTORE_TEST_MS});
    // The app's offline-fallback service worker blocked, as in default-currency.spec.ts: every request of these cases
    // meets `page.route` — above all the restart, which must never reach the lane's server. Local to this block.
    restoreTest.use({serviceWorkers: 'block'});

    restoreTest.afterAll(async () => {
        archiveMade = null;
        if (archiveDir !== null) await rm(archiveDir, {recursive: true, force: true});
        archiveDir = null;
    });

    restoreTest('FBKP-101: an archive over the upload limit is refused before anything is sent', async ({page, lane}) => {
        const limitMb = 1;
        lane.status = {status: 200, json: schemas.RestoreStatus.parse({state: 'none', upload_limit_mb: limitMb})};
        const uploads: string[] = [];
        await page.route(
            (url) => url.pathname === RESTORE_UPLOAD,
            async (route) => {
                uploads.push(route.request().method());
                // Recorded and stopped here: the case is that nothing is sent.
                await route.abort('blockedbyclient');
            },
        );

        const card = await openRestoreCard(page);
        await expect(card, 'precondition: nothing waits, the card takes an archive').toHaveAttribute('data-state', 'idle');
        await expect(page.getByTestId('restore-limit'), 'the card gives the limit the status sets').toHaveAttribute('data-limit-mb', String(limitMb));

        const since = await eventSeq(page);
        await chooseArchive(page, {name: 'librefolio-backup-too-large.zip', mimeType: 'application/zip', buffer: Buffer.alloc(limitMb * MEGABYTE + 1)});

        // The reason before the state: an upload that went out anyway would fail with another code.
        await expect(card).toHaveAttribute('data-error-code', 'backup_too_large');
        await expect(card).toHaveAttribute('data-state', 'failed');
        await expect(page.getByTestId('restore-error')).toHaveAttribute('data-error-code', 'backup_too_large');
        const failed = await waitForEvent(page, 'backup.restore.failed', {since});
        expect(failed.detail).toEqual({code: 'backup_too_large', what: 'upload'});
        await expect(page.getByTestId('toast-error'), 'a refusal is said').toBeVisible();
        await expect(page.getByTestId('restore-retry'), 'and the card offers to try again').toBeVisible();
        expect(uploads, 'refused before sending: no upload left the page').toEqual([]);
        expect(lane.restarts).toBe(0);
    });

    restoreTest('FBKP-102: the confirmation word cannot be pasted — refused, the field empty, the confirm disabled — only typed', async ({page, lane}) => {
        const archive = {name: 'librefolio-backup-e2e.zip', mimeType: 'application/zip', buffer: Buffer.from('PK\u0003\u0004 checked by the faked check')};
        const check = await fakeTheCheck(page, archive.buffer.length);
        const card = await openRestoreCard(page);
        await expect(card, "precondition: nothing waits on the lane's server, the card takes an archive").toHaveAttribute('data-state', 'idle');

        const since = await eventSeq(page);
        await chooseArchive(page, archive);
        await expect(card).toHaveAttribute('data-state', 'report', {timeout: PAGE_MS});
        const staged = await waitForEvent(page, 'backup.restore.staged', {since});
        expect(staged.detail?.restorable, 'precondition: the report lets the restore be confirmed').toBe(true);
        await expect(page.getByTestId('restore-report')).toBeVisible();

        const input = page.getByTestId('restore-confirm-input');
        const confirm = page.getByTestId('restore-confirm');
        await expect(input).toBeEnabled();
        await expect(input).toHaveValue('');
        await expect(confirm, 'nothing typed: nothing to confirm').toBeDisabled();
        const word = await confirmationWord(page);

        // The very word on the clipboard, pasted into the field the way a user pastes.
        await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
        await page.evaluate((text) => navigator.clipboard.writeText(text), word);
        await watchPastes(page);
        await input.press('ControlOrMeta+V');

        // The paste did reach the field, the word in hand — else the empty field below would prove nothing —, and was refused.
        await expect.poll(async () => (await pastesSeen(page)).length, {message: 'ControlOrMeta+V pastes into the field'}).toBeGreaterThan(0);
        expect(await pastesSeen(page), 'one paste, carrying the word, refused by the field').toEqual([{prevented: true, text: word}]);
        await expect(input, 'nothing pasted').toHaveValue('');
        await expect(confirm, 'still nothing to confirm').toBeDisabled();

        // Typed key by key, the same word is taken.
        await input.pressSequentially(word);
        await expect(input).toHaveValue(word);
        await expect(confirm, 'the word typed: the restore can be confirmed').toBeEnabled();

        // Dropped rather than confirmed: the faked check goes, and the card reads the lane's status again.
        const dropping = await eventSeq(page);
        await page.getByTestId('restore-drop').click();
        await expect(card).toHaveAttribute('data-state', 'idle', {timeout: PAGE_MS});
        const cancelled = await waitForEvent(page, 'backup.restore.cancelled', {since: dropping});
        expect(cancelled.detail).toEqual({what: 'check'});
        expect(
            check.calls.filter((call) => call.endsWith('/confirm')),
            'nothing was confirmed',
        ).toEqual([]);
        expect(lane.restarts).toBe(0);
    });

    restoreTest('FBKP-103: rolled back (first_start_failed): the overlay says why; restart-back reads the status again, and the card shows the last result', async ({page, lane}) => {
        lane.status = {status: 200, json: fakedRestore()};
        lane.outcome = outcomeAnswer({state: 'rolled_back', reason: 'first_start_failed'});
        const since = await restartFromPending(page, lane);
        await serverComesBack(page, lane);

        const overlay = page.getByTestId('restart-overlay');
        await expect(overlay).toHaveAttribute('data-outcome', 'rolled_back', {timeout: RESTART_MS});
        await expect(overlay).toHaveAttribute('data-reason', 'first_start_failed');
        await expect(overlay).toHaveAttribute('data-waiting', '');
        await expect(page.getByTestId('restart-detail')).toBeVisible();
        await expect(page.getByTestId('restart-back')).toBeVisible();
        const rolledBack = await waitForEvent(page, 'backup.restore.rolled_back', {since});
        expect(rolledBack.detail).toEqual({reason: 'first_start_failed'});
        await expect(page, 'a restore rolled back keeps the page: no sign-in').toHaveURL((url) => url.pathname === '/settings');
        expectTicketInItsHeaderOnly(lane);

        // Back to the tab: the status read again, as the restarted server tells it.
        const statusReads = lane.reads.filter((read) => read.what === 'status').length;
        lane.status = {status: 200, json: fakedRestore({state: 'rolled_back', reason: 'first_start_failed', finished_at: '2026-10-15T09:46:40Z'})};
        await page.getByTestId('restart-back').click();
        await expect(overlay).toBeHidden();
        const card = page.getByTestId('restore-card');
        await expect(card).toHaveAttribute('data-state', 'idle', {timeout: PAGE_MS});
        await expect(card).toHaveAttribute('data-error-code', '');
        const last = page.getByTestId('restore-last-result');
        await expect(last).toHaveAttribute('data-result', 'rolled_back');
        await expect(last).toHaveAttribute('data-reason', 'first_start_failed');
        expect(lane.reads.filter((read) => read.what === 'status').length, 'back to the tab reads the status again').toBeGreaterThan(statusReads);
    });

    restoreTest('FBKP-104: still waiting, the instance blocked by its hosting provider: the overlay says so; back, the restore still waits, and the card says why', async ({page, lane}) => {
        lane.status = {status: 200, json: fakedRestore()};
        lane.outcome = outcomeAnswer({state: 'pending', waiting: 'instance_blocked'});
        const since = await restartFromPending(page, lane);
        await serverComesBack(page, lane);

        const overlay = page.getByTestId('restart-overlay');
        await expect(overlay).toHaveAttribute('data-outcome', 'still_pending', {timeout: RESTART_MS});
        await expect(overlay).toHaveAttribute('data-waiting', 'instance_blocked');
        await expect(overlay).toHaveAttribute('data-reason', '');
        await expect(page.getByTestId('restart-back')).toBeVisible();
        await expect(page, 'not applied: the page stays, no sign-in').toHaveURL((url) => url.pathname === '/settings');
        // Read once the overlay says it: a restore not applied is told by the overlay alone, as no failure.
        expect(await eventNamesSince(page, since), 'no failure announced').not.toContain('backup.restore.failed');
        expectTicketInItsHeaderOnly(lane);

        lane.status = {status: 200, json: fakedRestore({waiting: 'instance_blocked'})};
        await page.getByTestId('restart-back').click();
        await expect(overlay).toBeHidden();
        const card = page.getByTestId('restore-card');
        await expect(card, 'the restore still waits').toHaveAttribute('data-state', 'pending', {timeout: PAGE_MS});
        await expect(page.getByTestId('restore-pending')).toHaveAttribute('data-waiting', 'instance_blocked');
        await expect(page.getByTestId('restore-waiting'), 'the card says why it waits').toBeVisible();
        await expect(page.getByTestId('restore-restart')).toBeVisible();
    });

    restoreTest('FBKP-105: the ticket no longer known (404): the status read with the session answers 401, so the restore was kept: the sign-in page', async ({page, lane}) => {
        lane.status = {status: 200, json: fakedRestore()};
        lane.outcome = {status: 404, json: {detail: {code: 'restore_outcome_not_found', message: 'No restore outcome for this ticket'}}};
        await restartFromPending(page, lane);
        await serverComesBack(page, lane, async () => {
            // The restarted server knows no session of before: the status read with this one answers 401.
            lane.status = {status: 401, json: {detail: 'Session expired or invalid'}};
            await page.context().clearCookies();
        });

        await expectSignInPage(page);
        expectTicketInItsHeaderOnly(lane);
        const fromOutcome = lane.reads.slice(lane.reads.findIndex((read) => read.what === 'outcome'));
        expect(
            fromOutcome.map(({what, ticket}) => ({what, ticket})),
            'the ticket refused, the status read next, with the session and without the ticket',
        ).toContainEqual({what: 'status', ticket: null});
    });

    restoreTest('FBKP-106: a restore found waiting at load is offered to restart or cancel; cancelled, the server dropped its checked copy too (B-17)', async ({page, lane}) => {
        const archive = await instanceArchive(lane.admin);
        const stageId = await checkThroughApi(lane, archive);
        await confirmThroughApi(lane, stageId);
        const drops: string[] = [];
        page.on('request', (request) => {
            if (request.method() === 'DELETE' && new URL(request.url()).pathname.startsWith(`${RESTORE_STAGE}/`)) drops.push(request.url());
        });

        const card = await openRestoreCard(page);
        await expect(card, 'the restore confirmed through the API waits: the card shows it').toHaveAttribute('data-state', 'pending');
        const pending = page.getByTestId('restore-pending');
        await expect(pending).toBeVisible();
        await expect(pending, 'nothing holds it back: it waits for a restart').toHaveAttribute('data-waiting', '');
        await expect(pending, 'who confirmed it').toContainText(TEST_ADMIN.username);
        await expect(page.getByTestId('restore-restart')).toBeEnabled();
        await expect(page.getByTestId('restore-cancel-pending')).toBeEnabled();
        await expect(page.getByTestId('restore-waiting')).toHaveCount(0);
        await expect(page.getByTestId('restore-choose'), 'no other archive while one waits').toHaveCount(0);

        const since = await eventSeq(page);
        await page.getByTestId('restore-cancel-pending').click();
        // Not `pending`, the state before the click: the cancel ends `idle`, or `failed` with its reason.
        await expect(card).toHaveAttribute('data-state', /^(idle|failed)$/, {timeout: PAGE_MS});
        await expect(card, 'the cancel went through').toHaveAttribute('data-error-code', '');
        await expect(card).toHaveAttribute('data-state', 'idle');
        const cancelled = await waitForEvent(page, 'backup.restore.cancelled', {since});
        expect(cancelled.detail).toEqual({what: 'pending'});
        await expect(page.getByTestId('restore-pending')).toHaveCount(0);

        // On the server: nothing waits any more, and the checked copy went with the restore (B-17), dropped by the server.
        expect((await readStatus(lane.admin)).state, 'the restore is cancelled on the server').toBe('none');
        const read = await lane.admin.get(checkUrl(stageId));
        expect(read.status(), `GET ${checkUrl(stageId)} after the cancel`).toBe(404);
        expect(await errorCode(read)).toBe('restore_stage_not_found');
        const again = await lane.admin.post(`${checkUrl(stageId)}/confirm`);
        expect(again.status(), "confirming the cancelled restore's check again: its copy is gone").toBe(404);
        expect(await errorCode(again)).toBe('restore_stage_not_found');
        expect(drops, 'the page dropped nothing itself: the server dropped the copy with the cancel').toEqual([]);
        expect(lane.restarts, 'the card restarts nothing by itself').toBe(0);
    });

    restoreTest('FBKP-107: the whole restore — uploaded, checked, reported, the word typed, confirmed; restarted, the outcome read with the ticket: the sign-in page, nothing said', async ({page, lane}) => {
        const archive = await instanceArchive(lane.admin);
        lane.realConfirm = true;
        lane.outcome = outcomeAnswer({state: 'committed'});
        recordStartedChecks(page, lane);

        const card = await openRestoreCard(page);
        await expect(card, "precondition: nothing waits on the lane's server, the card takes an archive").toHaveAttribute('data-state', 'idle');

        const since = await eventSeq(page);
        const releaseChecks = await holdCheckReads(page);
        try {
            await chooseArchive(page, archive.path);
            // Sent, then checked on a copy: the card follows the check, its first read held while the test looks at it.
            await expect(card).toHaveAttribute('data-state', /^(checking|failed)$/, {timeout: UPLOAD_MS});
            await expect(card, 'the archive was received and its check started').toHaveAttribute('data-error-code', '');
            await expect(card).toHaveAttribute('data-state', 'checking');
            await expect(card).toHaveAttribute('data-busy', 'true');
            await expect(page.getByTestId('restore-check-progress')).toHaveAttribute('data-phase', CHECK_PHASES);
            await expect(page.getByTestId('restore-cancel-check'), 'a running check can be dropped').toBeVisible();
        } finally {
            releaseChecks();
        }
        const uploaded = await waitForEvent(page, 'backup.restore.uploaded', {since});
        expect(String(uploaded.detail?.upload_id)).toMatch(JOB_ID);
        expect(uploaded.detail?.size, 'the whole archive reached the server').toBe(archive.size);

        // The report: the reason before the state, as for the backup.
        await expect(card).toHaveAttribute('data-state', /^(report|failed)$/, {timeout: CHECK_MS});
        await expect(card, 'the check accepted the archive').toHaveAttribute('data-error-code', '');
        await expect(card).toHaveAttribute('data-state', 'report');
        const staged = await waitForEvent(page, 'backup.restore.staged', {since});
        const stageId = String(staged.detail?.stage_id);
        expect(staged.detail, "the instance's own archive: restorable, of this very version").toEqual({stage_id: stageId, restorable: true, action: 'same'});
        await Promise.all(lane.reading);
        expect([...lane.checks], 'the check the card announces is the one the server started for this archive').toEqual([stageId]);

        const report = page.getByTestId('restore-report');
        await expect(report, 'the report opens by itself').toBeVisible();
        await expect(page.getByTestId('restore-report-ready')).toHaveAttribute('data-restorable', 'true');
        await expect(report.locator('[data-restorable][data-action]'), 'nothing to upgrade').toHaveAttribute('data-action', 'same');
        await expect(page.getByTestId('restore-report-migrations')).toHaveAttribute('data-count', '0');
        await expect(page.getByTestId('restore-report-admins'), "the archive's administrators, who will sign in again").toContainText(TEST_ADMIN.username);
        await expect(page.getByTestId('restore-report-blocker')).toHaveCount(0);

        // The word, key by key: the confirm stays disabled until its last letter.
        const input = page.getByTestId('restore-confirm-input');
        const confirm = page.getByTestId('restore-confirm');
        await expect(input).toBeEnabled();
        await expect(input).toHaveValue('');
        await expect(confirm, 'nothing typed: nothing to confirm').toBeDisabled();
        const word = await confirmationWord(page);
        await input.pressSequentially(word.slice(0, -1));
        await expect(input).toHaveValue(word.slice(0, -1));
        await expect(confirm, 'the word not finished: still nothing to confirm').toBeDisabled();
        await input.pressSequentially(word.slice(-1));
        await expect(input).toHaveValue(word);
        await expect(confirm, 'the word typed: the restore can be confirmed').toBeEnabled();

        // Confirmed on the lane's server, then the restart asked at once (P8), answered here.
        const confirming = await eventSeq(page);
        await confirm.click();
        await expect(card).toHaveAttribute('data-state', /^(restarting|pending|failed)$/, {timeout: PAGE_MS});
        await expect(card, 'the confirmation and the restart went through').toHaveAttribute('data-error-code', '');
        await expect(card).toHaveAttribute('data-state', 'restarting');
        await expect(report, 'the report closes with the confirmation').toBeHidden();
        const confirmed = await waitForEvent(page, 'backup.restore.confirmed', {since: confirming});
        expect(confirmed.detail).toEqual({stage_id: stageId});
        const requested = await waitForEvent(page, 'backup.restore.restart.requested', {since: confirming});
        expect(requested.detail ?? {}, 'the restart is announced without its ticket').toEqual({});
        expect(lane.restarts, "one restart asked, answered here: the lane's server keeps running").toBe(1);
        const overlay = page.getByTestId('restart-overlay');
        await expect(overlay).toHaveAttribute('data-outcome', 'waiting');
        await expect(page.getByTestId('restart-back'), 'nothing to go back to while the server restarts').toHaveCount(0);

        const waiting = await readStatus(lane.admin);
        expect(waiting.state, "the confirmation was real: the restore waits on the lane's server").toBe('pending');
        expect(waiting.stage_id).toBe(stageId);
        expect(waiting.confirmed_by).toBe(TEST_ADMIN.username);
        expect(await pageKeeps(page), 'the ticket is kept nowhere a script of the page could read it later').not.toContain(lane.ticket);

        // The server goes down, then comes back with the restore kept: every session of before ended with it.
        await serverComesBack(page, lane, () => page.context().clearCookies());
        await expectSignInPage(page);
        expectTicketInItsHeaderOnly(lane);
        expect(lane.restarts, 'still one restart, never sent on').toBe(1);
        expect((await readStatus(lane.admin)).state, "the restart never reached the lane's server: the restore still waits there, for the clean-up to cancel").toBe('pending');
    });

    restoreTest('FBKP-108: a secure backup from the card, its password typed twice under the rules of the options; its .lfbk downloaded and chosen in the restore card: the password asked first, the envelope checked, then dropped; the password kept nowhere', async ({page, lane}, testInfo) => {
        recordStartedChecks(page, lane);
        const sent = watchUploadsAndChecks(page);
        const card = await openRestoreCard(page);
        await expect(card, "precondition: nothing waits on the lane's server, the card takes an archive").toHaveAttribute('data-state', 'idle');
        const backupCard = page.getByTestId('backup-download-card');

        // The password, built from the rules the server gives a backup's password.
        const rules = await archivePasswordRules(page.request);
        const minLength = minLengthOf(rules);
        const password = passwordOf(minLength + 4);
        const oneShort = passwordOf(minLength - 1);

        // «Secure»: the password asked twice, under the strength meter. A backup is clear until the administrator chooses.
        await expect(backupCard.getByTestId('backup-mode-clear')).toBeChecked();
        await backupCard.getByTestId('backup-mode-secure').check();
        await expect(backupCard.getByTestId('backup-mode')).toHaveAttribute('data-mode', 'secure');
        const create = backupCard.getByTestId('backup-create');
        await expect(create, 'no password yet: nothing to start').toBeDisabled();
        const first = backupCard.getByTestId('backup-password');
        const second = backupCard.getByTestId('backup-password-confirm');
        await expect(first).toHaveAttribute('type', 'password');
        await expect(second).toHaveAttribute('type', 'password');

        // One character short of the options' minimum, every class in it, typed twice alike: the meter holds it to the
        // options' rules — once they are in: the accounts' own ask fewer characters —, and the backup cannot start.
        await first.fill(oneShort);
        await second.fill(oneShort);
        await expect(backupCard.getByTestId('password-rule-minLength'), `${minLength - 1} characters: one short of the options' minimum`).toHaveAttribute('data-passed', 'false', {timeout: PAGE_MS});
        await expect(create).toBeDisabled();

        await first.fill(password);
        await second.fill(password);
        for (const {code} of rules) {
            await expect(backupCard.getByTestId(`password-rule-${RULE_ROWS[code]}`), `the rule ${code} holds`).toHaveAttribute('data-passed', 'true');
        }
        await expect(backupCard.getByTestId('backup-password-mismatch')).toHaveCount(0);
        await expect(create, 'a valid password, typed twice alike: the backup can start').toBeEnabled();

        // Started and followed to done, as FBKP-002 does: the archive is the secure one.
        const creating = await eventSeq(page);
        const {jobId, fileSize} = await createBackup(page, backupCard);
        const created = await waitForEvent(page, 'backup.created', {since: creating});
        expect(created.detail?.encrypted, 'backup.created says the archive is encrypted').toBe(true);
        // The password left its fields as the job started; «secure» is still the choice.
        await expect(backupCard.getByTestId('backup-mode')).toHaveAttribute('data-mode', 'secure');
        await expect(first, 'the password left its field').toHaveValue('');
        await expect(second, 'and its repetition').toHaveValue('');

        // The job, by its id, as the server tells it; and the card's encrypted ready state.
        const read = await page.request.get(jobUrl(jobId));
        expect(read.status(), `GET ${jobUrl(jobId)}`).toBe(200);
        const job = schemas.InstanceBackupJob.parse(await read.json());
        expect(job.encrypted, 'the job of a secure backup says its archive is encrypted').toBe(true);
        expect(job.file_size, 'the job and backup.created give the same size').toBe(fileSize);
        await expect(backupCard.getByTestId('backup-ready')).toBeVisible();
        await expect(backupCard.getByTestId('backup-encrypted-note'), 'the card says its archive is encrypted').toBeVisible();
        const link = backupCard.getByTestId('backup-download-link');
        await expect(link).toHaveAttribute('href', new RegExp(`/jobs/${jobId}/file$`));
        await expect(link).toHaveAttribute('download', ENVELOPE_NAME);
        const name = (await link.getAttribute('download')) ?? '';
        expect(job.file_name, 'the link names the envelope of this very job').toBe(name);

        // Downloaded as FBKP-002 does, then kept under its own name in the test's output folder, to be chosen below.
        const downloading = page.waitForEvent('download', {timeout: PAGE_MS});
        await link.click();
        const download = await downloading;
        expect(download.suggestedFilename(), 'the browser saves the envelope under the name the link gives').toBe(name);
        expect(await download.failure(), 'the download completes').toBeNull();
        const saved = testInfo.outputPath(name);
        await download.saveAs(saved);
        expect((await stat(saved)).size, 'the whole envelope arrived: as many bytes as the job reported').toBe(fileSize);
        expect(await leadingBytes(saved, 4), 'an envelope: it opens with LFBK').toBe(ENVELOPE_MAGIC);

        // Chosen in the restore card: its password first, nothing sent.
        await chooseEnvelope(page, card, saved, sent);

        // Its password: the envelope sent once, then checked — decrypted first, the page's reads of the check held while
        // the test looks at it.
        const submitted = await eventSeq(page);
        const releaseChecks = await holdCheckReads(page);
        try {
            await submitRestorePassword(card, password);
            await expect(card).toHaveAttribute('data-state', /^(checking|failed)$/, {timeout: UPLOAD_MS});
            await expect(card, 'the envelope was received and its check started').toHaveAttribute('data-error-code', '');
            await expect(card).toHaveAttribute('data-state', 'checking');
            await expect(card.getByTestId('restore-check-progress'), 'an envelope is decrypted first').toHaveAttribute('data-phase', 'decrypting');
        } finally {
            releaseChecks();
        }
        await expect(card).toHaveAttribute('data-state', /^(report|failed)$/, {timeout: CHECK_MS});
        await expect(card, 'the check opened the envelope and accepted its archive').toHaveAttribute('data-error-code', '');
        await expect(card).toHaveAttribute('data-state', 'report');
        const staged = await waitForEvent(page, 'backup.restore.staged', {since: submitted});
        const stageId = String(staged.detail?.stage_id);
        expect(staged.detail, "the instance's own archive: restorable, of this very version").toEqual({stage_id: stageId, restorable: true, action: 'same'});
        await Promise.all(lane.reading);
        expect([...lane.checks], 'the check the card announces is the one the server started for this envelope').toEqual([stageId]);

        // What the page sent: the envelope once, then its check, with the password.
        expect(
            sent.map(({call}) => call),
            'the envelope sent once, then its check started once',
        ).toEqual([UPLOAD_CALL, CHECK_CALL]);
        const [upload, check] = await Promise.all(sent.map(({answer}) => answer));
        expect(upload?.status, UPLOAD_CALL).toBe(201);
        // Playwright cannot read the body answering a large XHR upload, while the page did: the id is the check's own.
        const uploadId = String((sent[1].body as {upload_id?: unknown} | null)?.upload_id);
        expect(uploadId, 'the check names an upload').toMatch(JOB_ID);
        expect(check?.status, CHECK_CALL).toBe(202);
        expect(sent[1].body, 'the check asked of that upload, with the password').toEqual({upload_id: uploadId, password});

        // The report: a secure archive by the server's report of this very check — the modal publishes no handle for it —,
        // and what the modal shows of the key and of the secrets is what that report says, whatever the lane's secrets are.
        const serverReport = await readReport(lane.admin, stageId);
        expect(serverReport.encrypted, "the server's report of this check: a secure archive").toBe(true);
        const report = page.getByTestId('restore-report');
        await expect(report, 'the report opens by itself').toBeVisible();
        await expect(report.getByTestId('restore-report-key'), 'the instance key, as the report says').toHaveAttribute('data-included', String(serverReport.instance_key_included));
        const rekeyed = report.getByTestId('restore-report-secrets-rekeyed');
        await expect(rekeyed, 'the line of the secrets re-encrypted: there exactly when the report counts some').toHaveCount(serverReport.secrets_rekeyed > 0 ? 1 : 0);
        if (serverReport.secrets_rekeyed > 0) await expect(rekeyed).toHaveAttribute('data-count', String(serverReport.secrets_rekeyed));
        const unreadable = serverReport.secrets_unreadable.system + serverReport.secrets_unreadable.user;
        const unreadableLine = report.getByTestId('restore-report-secrets-unreadable');
        await expect(unreadableLine, 'the line of the secrets this LibreFolio cannot read: there exactly when the report counts some').toHaveCount(unreadable > 0 ? 1 : 0);
        if (unreadable > 0) await expect(unreadableLine).toHaveAttribute('data-count', String(unreadable));

        // Dropped, as FBKP-102 does: nothing restored, the check gone.
        await dropTheReport(page, card, lane, stageId);

        // Never kept: what a script of the page could read later holds the backup the page follows, and neither password.
        const kept = await pageKeeps(page);
        expect(kept, 'precondition: what the page keeps is read — the backup it follows').toContain(jobId);
        for (const typed of [password, oneShort]) expect(kept, 'a password typed is kept where a script of the page could read it').not.toContain(typed);
    });

    restoreTest('FBKP-109: a wrong password is refused and asked again, the envelope not sent again: the right one checks the same upload — one PUT, two POSTs of the check —, and the archive is dropped', async ({page, lane}, testInfo) => {
        recordStartedChecks(page, lane);
        const sent = watchUploadsAndChecks(page);
        // Signed in first: the archive is made with the page's own session.
        const card = await openRestoreCard(page);
        await expect(card, "precondition: nothing waits on the lane's server, the card takes an archive").toHaveAttribute('data-state', 'idle');
        const length = minLengthOf(await archivePasswordRules(page.request)) + 4;
        const password = passwordOf(length);
        const wrong = passwordOf(length);
        expect(wrong, 'precondition: two passwords').not.toBe(password);
        const archive = await secureArchiveThroughApi(page.request, password, (name) => testInfo.outputPath(name));

        await chooseEnvelope(page, card, archive.path, sent);

        // A wrong password: the envelope sent, its check refused, the password asked again.
        await submitRestorePassword(card, wrong);
        // The reason first: the card was on the password already before the server answered.
        await expect(card.getByTestId('restore-password-error'), 'the wrong password is said, by its code').toHaveAttribute('data-error-code', 'wrong_password', {timeout: UPLOAD_MS});
        await expect(card).toHaveAttribute('data-error-code', 'wrong_password');
        await expect(card, 'still on the password').toHaveAttribute('data-state', 'password');
        await expect(card).toHaveAttribute('data-busy', 'false');
        await expect(card.getByTestId('restore-password'), 'the field empty again, for the next try').toHaveValue('');
        expect(
            sent.map(({call}) => call),
            'the envelope sent once, its check asked once',
        ).toEqual([UPLOAD_CALL, CHECK_CALL]);

        // The right one: the same upload checked, nothing sent again.
        const submitted = await eventSeq(page);
        await submitRestorePassword(card, password);
        await expect(card, 'the check started').toHaveAttribute('data-state', /^(checking|report|failed)$/, {timeout: PAGE_MS});
        await expect(card).toHaveAttribute('data-state', /^(report|failed)$/, {timeout: CHECK_MS});
        await expect(card, 'the right password opened the envelope').toHaveAttribute('data-error-code', '');
        await expect(card).toHaveAttribute('data-state', 'report');
        await expect(page.getByTestId('restore-report')).toBeVisible();
        const staged = await waitForEvent(page, 'backup.restore.staged', {since: submitted});
        const stageId = String(staged.detail?.stage_id);
        await Promise.all(lane.reading);
        expect([...lane.checks], 'the check the card announces is the one the server started for this envelope').toEqual([stageId]);

        // What the page sent across both tries: the envelope once, its check twice — the first refused.
        expect(
            sent.map(({call}) => call),
            'one upload across both tries, and two starts of its check',
        ).toEqual([UPLOAD_CALL, CHECK_CALL, CHECK_CALL]);
        const [upload, refused, accepted] = await Promise.all(sent.map(({answer}) => answer));
        expect(upload?.status, UPLOAD_CALL).toBe(201);
        // Playwright cannot read the body answering a large XHR upload, while the page did: the id is the first check's.
        const uploadId = String((sent[1].body as {upload_id?: unknown} | null)?.upload_id);
        expect(uploadId, 'the first check names an upload').toMatch(JOB_ID);
        expect(refused?.status, `the first ${CHECK_CALL}`).toBe(400);
        expect((refused?.json as {detail?: {code?: unknown}} | null)?.detail?.code).toBe('wrong_password');
        expect(accepted?.status, `the second ${CHECK_CALL}`).toBe(202);
        expect(
            sent.filter(({call}) => call === CHECK_CALL).map(({body}) => body),
            'both checks asked of the same upload: the wrong password, then the right one',
        ).toEqual([
            {upload_id: uploadId, password: wrong},
            {upload_id: uploadId, password},
        ]);

        // Dropped: the check gone, and the upload went with it — nothing of the archive is left on the server.
        await dropTheReport(page, card, lane, stageId);
        const again = await lane.admin.post(RESTORE_STAGE, {data: {upload_id: uploadId, password}});
        // A check this would start after all is the case's own: dropped after it.
        if (again.status() === 202) lane.checks.add(schemas.RestoreStage.parse(await again.json()).stage_id);
        expect(again.status(), `${CHECK_CALL} of that upload again`).toBe(404);
        expect(await errorCode(again), 'the upload went with its check').toBe('backup_upload_not_found');
    });
});
