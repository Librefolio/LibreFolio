/**
 * Gallery, Settings › Backup (`settings/backup-ready`): the administrators' Backup tab with a finished backup on offer.
 *
 * The shot shows the backup card as an administrator finds it once an archive is written: ready, the archive's name, size
 * and date, its download link and the delete. Neither is ever pressed: nothing is downloaded, nothing is deleted. The
 * gallery's lane never runs a real backup to get there — the instance builds one at a time, and the archive holds every
 * user's data — so the finished job is simulated.
 *
 * The card follows the job whose id it keeps in `sessionStorage` (`features/backup/backupJob.svelte.ts`,
 * `BackupJobController`), and on load reads it with `GET /api/v1/backup/instance/jobs/{job_id}` (`backupApi.ts`,
 * `getInstanceBackupJob`). {@link serveGalleryBackupJob} writes {@link GALLERY_BACKUP_JOB_ID} there ahead of the app on
 * every load, and answers that read and nothing else: `GET` on that job's path. Any other method falls back to the routes
 * registered before it (the gallery's offline guard), then to the backend; nothing is continued by hand. The archive's
 * file, a new start and the delete are not routed: the shot presses nothing. The body is the shape the backend sends
 * (`backend/app/schemas/backup.py`, `InstanceBackupJob`), typed with the generated client's type and checked against its
 * Zod schema once, at registration: a contract that moved fails the test there, with Zod's own message, rather than as a
 * card left idle. Its data are fixed — no clock, no random value, no external URL — and the card says nothing relative to
 * the clock: its date is the job's `finished_at`, written out here. The card draws it in the browser's time zone, which
 * the gallery leaves to the machine (no `timezoneId`), as it does for the dates of the Files page.
 *
 * Registered before the first navigation, the stored id and the route stay with the page for the whole test — every load
 * of the tab reads the job — and the gallery's outer afterEach drops the route once the page has left
 * (`leaveGalleryPage`); the stored id goes with the page.
 */
import {schemas} from '../../src/lib/api/generated';
import {expect, type Page} from './playwright';

/** The job the card follows: fixed, in the shape the card accepts from its storage (32 lowercase hex digits). */
export const GALLERY_BACKUP_JOB_ID = '5c9e2f1a7b3d48e6a0f4c2d19b7e3a85';

/**
 * Where the card keeps the id of the job it follows: `BACKUP_JOB_STORAGE_KEY` of `features/backup/backupJob.svelte.ts`,
 * written out here because that module uses runes and is not imported from an e2e file.
 */
const FOLLOWED_JOB_KEY = 'librefolio.backup.job';

/** The path the card reads the job from (`features/backup/backupApi.ts`, `getInstanceBackupJob`). */
const BACKUP_JOB_PATH = `/api/v1/backup/instance/jobs/${GALLERY_BACKUP_JOB_ID}`;

/** Where the card's download link points (`backupApi.ts`, `instanceBackupFileUrl`): drawn, never requested. */
const BACKUP_FILE_PATH = `${BACKUP_JOB_PATH}/file`;

/** What `GET /api/v1/backup/instance/jobs/{job_id}` answers, as the generated client types it. */
type InstanceBackupJob = ReturnType<typeof schemas.InstanceBackupJob.parse>;

/** The archive's size in bytes: 46.0 MB on the card. */
const ARCHIVE_BYTES = 48_234_496;

/**
 * The job the shot shows: done seven seconds after it started, every byte read (`done_bytes` = `total_bytes`, as the
 * backend leaves a finished job), 46.0 MB, no warning. Its archive bears the name the backend gives one made at its
 * `created_at`: `librefolio-backup-YYYYMMDD-HHMMSS.zip`, in UTC (`jobs.py`, `archive_name`).
 */
export const GALLERY_BACKUP_JOB = {
    job_id: GALLERY_BACKUP_JOB_ID,
    status: 'done',
    phase: null,
    done_bytes: ARCHIVE_BYTES,
    total_bytes: ARCHIVE_BYTES,
    created_at: '2026-10-15T09:41:12Z',
    finished_at: '2026-10-15T09:41:19Z',
    file_name: 'librefolio-backup-20261015-094112.zip',
    file_size: ARCHIVE_BYTES,
    warnings: [],
    error_code: null,
    encrypted: false,
} satisfies InstanceBackupJob;

/**
 * Have the Backup tab find {@link GALLERY_BACKUP_JOB} on every load of the test: its id stored ahead of the app, and the
 * card's read of that job answered. Call it inside the test — after the gallery's outer beforeEach, so that the route is
 * tried before the offline guard — and before the first navigation.
 */
export async function serveGalleryBackupJob(page: Page): Promise<void> {
    // Checked once, here: a schema that moved fails the test now, with Zod's own message.
    const body = schemas.InstanceBackupJob.parse(GALLERY_BACKUP_JOB);
    // sessionStorage is the page's own, per tab and per origin: no storage state carries it, and before the first load
    // there is no document to write it into. An init script writes it ahead of the app's scripts on every document.
    await page.addInitScript(
        ({key, jobId}) => {
            try {
                window.sessionStorage.setItem(key, jobId);
            } catch {
                /* a document without storage of its own (about:blank, where the gallery leaves the page): no card reads it */
            }
        },
        {key: FOLLOWED_JOB_KEY, jobId: GALLERY_BACKUP_JOB_ID},
    );
    await page.route(
        (url) => url.pathname === BACKUP_JOB_PATH,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            await route.fulfill({json: body});
        },
    );
}

/**
 * The simulated job reached the page: the card done, the archive on offer with that job's own link, no warning, no error.
 * A route that stopped matching would let the lane's own answer through — no such job — and the card would forget the id
 * and stay idle, offering to create a backup; so would an id stored under a key the card no longer reads. The shot would
 * show that, in silence.
 */
export async function expectGalleryBackupReady(page: Page): Promise<void> {
    const card = page.getByTestId('backup-download-card');
    await expect(card, 'the simulated job is drawn: the card is done').toHaveAttribute('data-state', 'done');
    await expect(card.getByTestId('backup-ready'), 'the archive is on offer').toBeVisible();
    await expect(card.getByTestId('backup-download-link'), 'the link points at the archive of the simulated job').toHaveAttribute('href', BACKUP_FILE_PATH);
    await expect(card.getByTestId('backup-warnings'), 'no warning: the archive is complete').toHaveCount(0);
    await expect(card.getByTestId('backup-error'), 'no error on the card').toHaveCount(0);
}
