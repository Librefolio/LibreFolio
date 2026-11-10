/**
 * Gallery, Files (`files/backups`, `files/storage-bar`): what the administrators' Files page reads about the backups and the
 * space the instance takes, answered from fixtures — no archive of the lane is listed, and the sizes of its data folder never
 * reach a picture.
 *
 * - `GET /api/v1/backup/instance/jobs` (the Backups tab's list, `backupApi.ts` `listInstanceBackups`): {@link GALLERY_BACKUP_LIST},
 *   four kept backups in the shape the backend sends (`InstanceBackupEntry`), the newest first — a clear one made in the app, a
 *   password-protected one made by the command line, one the instance took before a restore, a failed one (no space left) —,
 *   each checked against the generated client's Zod schema once, at registration: a contract that moved fails the test there.
 *   Their dates, sizes and SHA-256 are written out here; the table draws the dates in the browser's time zone, which the
 *   gallery leaves to the machine, as it does for the other dates of the Files page. No archive is ever requested: the shot
 *   presses neither a download nor a delete.
 * - `GET /api/v1/backup/instance/storage` (the space bar, `getInstanceStorage`): {@link GALLERY_STORAGE}, the instance's data
 *   folder in its five parts against a limit of 2 GB set by the administrator, the way the bar shows its parts in its
 *   «limit» mode.
 * Both answer `GET` on their exact path only; any other method falls back to the routes registered before (the gallery's
 * offline guard), then to the backend. The cleanup settings of the panel are read from the lane's own settings as they are.
 * Registered inside the test, after the sign-in; the gallery's outer afterEach drops the routes once the page has left.
 */
import {schemas} from '../../src/lib/api/generated';
import type {Page} from './playwright';

const BACKUP_API = '/api/v1/backup/instance';

const MB = 1024 * 1024;

/** What `GET /backup/instance/jobs` answers, as the generated client types it. */
type InstanceBackupList = ReturnType<typeof schemas.InstanceBackupList.parse>;

export const GALLERY_BACKUP_LIST = {
    items: [
        {
            job_id: '5c9e2f1a7b3d48e6a0f4c2d19b7e3a85',
            status: 'done',
            phase: null,
            done_bytes: 46 * MB,
            total_bytes: 46 * MB,
            created_at: '2026-10-15T09:41:12Z',
            finished_at: '2026-10-15T09:41:19Z',
            file_name: 'librefolio-backup-20261015-094112.zip',
            file_size: 46 * MB,
            file_sha256: '3f7a9c1e5b20d84c6a19e07f2b5d8c40a1e6937b4d2f08c5a7e1b3946d0f8a2c',
            warnings: [],
            error_code: null,
            encrypted: false,
            instance_key_included: false,
            sealed: false,
            sealed_recipients: [],
            origin: 'ui',
        },
        {
            job_id: 'a41d7e90c35b4f28b6e1d0937c5a2f64',
            status: 'done',
            phase: null,
            done_bytes: 31 * MB,
            total_bytes: 31 * MB,
            created_at: '2026-10-08T22:00:03Z',
            finished_at: '2026-10-08T22:00:09Z',
            file_name: 'librefolio-backup-20261008-220003.lfbk',
            file_size: 31 * MB,
            file_sha256: 'b86e2d4a09c7f13e5a8d6b0c42e9f7a1d35c8e60b9a4f27d1c3e5a08b7d6942f',
            warnings: [],
            error_code: null,
            encrypted: true,
            instance_key_included: true,
            sealed: false,
            sealed_recipients: [],
            origin: 'cli',
        },
        {
            job_id: '0e8b3a6d1f594c27a9d5e3b8c1f7062a',
            status: 'done',
            phase: null,
            done_bytes: 29 * MB,
            total_bytes: 29 * MB,
            created_at: '2026-09-30T14:12:41Z',
            finished_at: '2026-09-30T14:12:46Z',
            file_name: 'librefolio-backup-20260930-141241.zip',
            file_size: 29 * MB,
            file_sha256: '19d5c8f2a6b04e7d3c91a5f80e2b6d47c3a9e1f50d8b7264a0c5e3f91b2d7a68',
            warnings: [],
            error_code: null,
            encrypted: false,
            instance_key_included: false,
            sealed: false,
            sealed_recipients: [],
            origin: 'pre-restore',
        },
        {
            job_id: 'd7c25f8a4e1b4960a3b8e5c1f9072d3b',
            status: 'failed',
            phase: null,
            done_bytes: 12 * MB,
            total_bytes: 52 * MB,
            created_at: '2026-09-22T03:30:00Z',
            finished_at: '2026-09-22T03:30:05Z',
            file_name: null,
            file_size: null,
            file_sha256: null,
            warnings: [],
            error_code: 'backup_no_space',
            encrypted: false,
            instance_key_included: false,
            sealed: false,
            sealed_recipients: [],
            origin: 'ui',
        },
    ],
} satisfies InstanceBackupList;

/** The five parts of the data folder, in bytes, against a limit of 2048 MB: the `limit` mode of the space bar. */
export const GALLERY_STORAGE = {
    database_bytes: 38 * MB,
    uploads_bytes: 212 * MB,
    broker_reports_bytes: 64 * MB,
    backups_bytes: 106 * MB,
    other_bytes: 9 * MB,
    data_bytes: (38 + 212 + 64 + 106 + 9) * MB,
    volume_total_bytes: 64 * 1024 * MB,
    volume_used_bytes: 21 * 1024 * MB,
    volume_free_bytes: 43 * 1024 * MB,
    limit_mb: 2048,
    limit_locked: false,
};

/** Answer the space bar's read of the page with {@link GALLERY_STORAGE}; before the first navigation. */
export async function serveGalleryStorage(page: Page): Promise<void> {
    const body = schemas.InstanceStorage.parse(GALLERY_STORAGE);
    await page.route(
        (url) => url.pathname === `${BACKUP_API}/storage`,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            await route.fulfill({json: body});
        },
    );
}

/** Answer the Backups tab's list with {@link GALLERY_BACKUP_LIST}; before the first navigation. */
export async function serveGalleryBackupList(page: Page): Promise<void> {
    const body = schemas.InstanceBackupList.parse(GALLERY_BACKUP_LIST);
    await page.route(
        (url) => url.pathname === `${BACKUP_API}/jobs`,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            await route.fulfill({json: body});
        },
    );
}
