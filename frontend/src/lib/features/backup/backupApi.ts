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

// =============================================================================
// The restore (lot B5b): upload an archive, check it on a copy, confirm, restart
// =============================================================================

export type RestoreStatus = z.infer<typeof schemas.RestoreStatus>;

/**
 * The client's explicit types of a check (`RestoreStage`, which embeds `RestoreStageReport`) widen every nullable field
 * to `T | null | (T | null)[]`, a branch their zod schemas never let through (the quirk `safeScalar` of
 * `$lib/types/common` unwraps at run time elsewhere). These types drop it, so the card reads each field as the server
 * sends it; the two functions that return a check cast once, after the schema has checked the answer. A field that is
 * only an array stays one: no field of either schema is an array that may also be null.
 */
type WithoutArrayBranch<T> = [Exclude<T, readonly unknown[]>] extends [never] ? T : Exclude<T, readonly unknown[]>;
type Unwidened<T> = T extends readonly (infer E)[] ? Unwidened<E>[] : T extends object ? {[K in keyof T]: Unwidened<WithoutArrayBranch<T[K]>>} : T;

/** The rows of one table before and after the check's update. */
type RestoreTableRows = Unwidened<z.infer<typeof schemas.RestoreTableRows>>;
/** `tables` is a record of rows per table (`z.record`), which the explicit type writes as `{}`. */
export type RestoreStageReport = Omit<Unwidened<z.infer<typeof schemas.RestoreStageReport>>, 'tables'> & {tables: Record<string, RestoreTableRows>};
export type RestoreStage = Omit<Unwidened<z.infer<typeof schemas.RestoreStage>>, 'report'> & {report?: RestoreStageReport | null};
export type RestoreUpload = z.infer<typeof schemas.RestoreUpload>;
export type RestorePhase = NonNullable<RestoreStage['phase']>;

export function getRestoreStatus(): Promise<RestoreStatus> {
    return zodiosApi.get_restore_status_api_v1_backup_restore_status_get();
}

export interface RestoreUploadOptions {
    /** Bytes sent so far, of the file's size. */
    onProgress?: (loaded: number, total: number) => void;
    signal?: AbortSignal;
}

/** Send an archive as the raw request body: the browser streams the file from disk, never into the page's memory. */
export function uploadRestoreArchive(file: File, options: RestoreUploadOptions = {}): Promise<RestoreUpload> {
    return zodiosApi.upload_restore_archive_api_v1_backup_restore_upload_put(file, {
        headers: {'Content-Type': 'application/octet-stream'},
        signal: options.signal,
        onUploadProgress: (event) => options.onProgress?.(event.loaded, event.total ?? file.size),
    });
}

export function startRestoreCheck(uploadId: string): Promise<RestoreStage> {
    return zodiosApi.start_restore_check_api_v1_backup_restore_stage_post({upload_id: uploadId}) as Promise<RestoreStage>;
}

export function getRestoreCheck(stageId: string): Promise<RestoreStage> {
    return zodiosApi.get_restore_check_api_v1_backup_restore_stage__stage_id__get({params: {stage_id: stageId}}) as Promise<RestoreStage>;
}

export async function deleteRestoreCheck(stageId: string): Promise<void> {
    await zodiosApi.delete_restore_check_api_v1_backup_restore_stage__stage_id__delete(undefined, {params: {stage_id: stageId}});
}

export function confirmRestore(stageId: string): Promise<RestoreStatus> {
    return zodiosApi.confirm_restore_check_api_v1_backup_restore_stage__stage_id__confirm_post(undefined, {params: {stage_id: stageId}});
}

export async function cancelPendingRestore(): Promise<void> {
    await zodiosApi.cancel_pending_restore_api_v1_backup_restore_pending_delete(undefined);
}

export function requestRestart(): Promise<RestoreStatus> {
    return zodiosApi.restart_for_restore_api_v1_backup_restore_restart_post(undefined);
}

/** The limit a `backup_too_large` refusal carries (`detail.limit_mb`), in megabytes; `null` without one. */
export function backupErrorLimitMb(error: unknown): number | null {
    if (!isAxiosError(error)) return null;
    const detail: unknown = error.response?.data?.detail;
    if (detail === null || typeof detail !== 'object') return null;
    const limit = (detail as {limit_mb?: unknown}).limit_mb;
    return typeof limit === 'number' && Number.isFinite(limit) ? limit : null;
}

/**
 * Whether the server answers and is ready, while it restarts for a restore. Through `fetch`, never the API client: the
 * client's interceptor turns a 401 into a navigation to the login, and the restore ends every session.
 */
export async function probeServer(): Promise<'up' | 'down'> {
    try {
        const response = await fetch('/api/v1/system/ready', {credentials: 'same-origin', cache: 'no-store'});
        return response.status === 200 ? 'up' : 'down';
    } catch {
        return 'down';
    }
}

/**
 * What the restarted server says of the restore: `signed_out` when the session ended (the restore was kept); `blocked`
 * when its hosting provider blocked the instance, whose restore routes then answer 423 `instance_blocked`: the restore
 * waits for the unblock (developer decision P7).
 */
export type RestoreOutcomeRead = {kind: 'signed_out'} | {kind: 'blocked'} | {kind: 'status'; status: RestoreStatus} | {kind: 'down'};

/** Whether a 423 is the instance block (`detail.code` `instance_blocked`), and not another lock. */
async function refusedForTheBlock(response: Response): Promise<boolean> {
    try {
        const body: unknown = await response.json();
        const detail = body !== null && typeof body === 'object' ? (body as {detail?: unknown}).detail : null;
        return detail !== null && typeof detail === 'object' && (detail as {code?: unknown}).code === 'instance_blocked';
    } catch {
        return false;
    }
}

export async function restoreOutcome(): Promise<RestoreOutcomeRead> {
    try {
        const response = await fetch('/api/v1/backup/restore/status', {credentials: 'same-origin', cache: 'no-store', headers: {Accept: 'application/json'}});
        if (response.status === 401) return {kind: 'signed_out'};
        if (response.status === 423) return (await refusedForTheBlock(response)) ? {kind: 'blocked'} : {kind: 'down'};
        if (response.status !== 200) return {kind: 'down'};
        const parsed = schemas.RestoreStatus.safeParse(await response.json());
        return parsed.success ? {kind: 'status', status: parsed.data} : {kind: 'down'};
    } catch {
        return {kind: 'down'};
    }
}
