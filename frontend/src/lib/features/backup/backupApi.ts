/**
 * The instance backup endpoints, for the Backup tab of Settings (administrators only).
 *
 * A backup runs on the server in the background: `startInstanceBackup` returns its job, `getInstanceBackupJob` reads its
 * progress, and once the job is done the archive downloads from `instanceBackupFileUrl` through a plain link. The browser
 * then streams it to disk: an archive of several hundred megabytes never sits in the page's memory, unlike the
 * Blob download of `lib/api/backupDownload.ts`, which suits the small per-asset exports.
 */
import {isAxiosError} from 'axios';
import type {z} from 'zod';
import {schemas, zodiosApi} from '$lib/api';

export type InstanceBackupJob = z.infer<typeof schemas.InstanceBackupJob>;
export type BackupPhase = NonNullable<InstanceBackupJob['phase']>;
export type BackupWarning = InstanceBackupJob['warnings'][number];

export function startInstanceBackup(): Promise<InstanceBackupJob> {
    return zodiosApi.start_instance_backup_api_v1_backup_instance_post(undefined);
}

export function getInstanceBackupJob(jobId: string): Promise<InstanceBackupJob> {
    return zodiosApi.get_instance_backup_job_api_v1_backup_instance_jobs__job_id__get({params: {job_id: jobId}});
}

export async function deleteInstanceBackupJob(jobId: string): Promise<void> {
    await zodiosApi.delete_instance_backup_job_api_v1_backup_instance_jobs__job_id__delete(undefined, {params: {job_id: jobId}});
}

/** Where the archive of a finished job downloads from: same origin, so the session cookie goes with the link. */
export function instanceBackupFileUrl(jobId: string): string {
    return `/api/v1/backup/instance/jobs/${encodeURIComponent(jobId)}/file`;
}

/**
 * The stable `detail.code` of a refused request (`backup_busy`, `backup_job_not_found`, …).
 *
 * `null` when there is none: a network failure, a proxy page, or a response that is not the backend's.
 */
export function backupErrorCode(error: unknown): string | null {
    if (!isAxiosError(error)) return null;
    const detail: unknown = error.response?.data?.detail;
    if (detail === null || typeof detail !== 'object') return null;
    const code = (detail as {code?: unknown}).code;
    return typeof code === 'string' && code !== '' ? code : null;
}

/** What to tell about a failed request: its `detail.code`; `network` when no answer came; `unexpected` otherwise. */
export function backupFailureCode(error: unknown): string {
    const code = backupErrorCode(error);
    if (code !== null) return code;
    return isAxiosError(error) && !error.response ? 'network' : 'unexpected';
}
