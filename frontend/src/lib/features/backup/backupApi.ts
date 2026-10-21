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
import type {PasswordRule} from '$lib/features/auth/passwordRules';

export type InstanceBackupJob = z.infer<typeof schemas.InstanceBackupJob>;
export type BackupPhase = NonNullable<InstanceBackupJob['phase']>;
export type BackupWarning = InstanceBackupJob['warnings'][number];

/** Start a backup; with `password`, a secure one (an `.lfbk` envelope, lot B4). The password goes in this request only. */
export function startInstanceBackup(password?: string): Promise<InstanceBackupJob> {
    // No body (`null`, as the generated client types an optional body): a clear backup, the request of before.
    return zodiosApi.start_instance_backup_api_v1_backup_instance_post(password === undefined ? null : {password});
}

export interface InstanceBackupOptions {
    /** The rules of a secure backup's password: the accounts' rules, with a longer minimum (P12). */
    password_rules: PasswordRule[];
}

/** What a secure backup asks of its password (`GET /backup/instance/options`): the server's rules, drawn as they come. */
export function getInstanceBackupOptions(): Promise<InstanceBackupOptions> {
    // The client's explicit type widens `value` to `number | null | Array<…>`, a branch its zod schema never lets through:
    // the answer, once checked, is cast as it is (see `Unwidened` below).
    return zodiosApi.get_instance_backup_options_api_v1_backup_instance_options_get() as Promise<InstanceBackupOptions>;
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

/**
 * What to tell about a failed upload of an archive (B-15): as `backupFailureCode`, and a 413 that is not LibreFolio's —
 * no `detail.code`, so a proxy in front of it refused the body (nginx's `client_max_body_size`, a hosting proxy, a CDN)
 * — is `proxy_too_large`: the server's log knows nothing of it. LibreFolio's own 413 keeps its code (`backup_too_large`).
 */
export function uploadFailureCode(error: unknown): string {
    const code = backupFailureCode(error);
    return code === 'unexpected' && isAxiosError(error) && error.response?.status === 413 ? 'proxy_too_large' : code;
}

/** The running backup a `backup_busy` refusal names (B-8): its job id and where it was started; `null` without one. */
export function backupBusyJob(error: unknown): {jobId: string; origin: string} | null {
    if (backupErrorCode(error) !== 'backup_busy' || !isAxiosError(error)) return null;
    const detail = error.response?.data?.detail as {job_id?: unknown; origin?: unknown};
    const {job_id: jobId, origin} = detail;
    return typeof jobId === 'string' && /^[0-9a-f]{32}$/.test(jobId) && typeof origin === 'string' && origin !== '' ? {jobId, origin} : null;
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
/** The restart accepted: the restore waiting, and the one-time ticket of its outcome (lot B5c). */
export type RestoreRestartAccepted = z.infer<typeof schemas.RestoreRestartAccepted>;
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

/** Check an upload on a copy; a secure backup with its `password`, which the server checks at once (lot B4). */
export function startRestoreCheck(uploadId: string, password?: string): Promise<RestoreStage> {
    const body = password === undefined ? {upload_id: uploadId} : {upload_id: uploadId, password};
    return zodiosApi.start_restore_check_api_v1_backup_restore_stage_post(body) as Promise<RestoreStage>;
}

/** The first bytes of a secure backup (an `.lfbk` envelope): «LFBK». */
const ENVELOPE_MAGIC = [0x4c, 0x46, 0x42, 0x4b];

/** Whether `file` is a secure backup, by its first four bytes, whatever its name. */
export async function isEnvelopeFile(file: Blob): Promise<boolean> {
    const head = new Uint8Array(await file.slice(0, ENVELOPE_MAGIC.length).arrayBuffer());
    return head.length === ENVELOPE_MAGIC.length && ENVELOPE_MAGIC.every((byte, index) => head[index] === byte);
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

export function requestRestart(): Promise<RestoreRestartAccepted> {
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

/** The header that carries the restart's one-time ticket to `GET /backup/restore/outcome`: never the URL, which access logs keep. */
export const RESTORE_TICKET_HEADER = 'X-Restore-Ticket';

/**
 * What the restarted server says of the restore. With the restart's one-time ticket (lot B5c) the outcome route
 * answers without a session, which a restore ends, and without `JWT_SECRET` every start too. A 404 there (a ticket
 * expired or used up), or a 401 or a 423 (the route out of reach for this caller), falls back to the status read with
 * the session, where a 401 means the session ended. Any other answer is the server still on its way: `down`.
 */
export async function restoreOutcome(ticket: string | null = null): Promise<RestoreOutcomeRead> {
    if (ticket !== null) {
        try {
            const response = await fetch('/api/v1/backup/restore/outcome', {
                credentials: 'same-origin',
                cache: 'no-store',
                headers: {Accept: 'application/json', [RESTORE_TICKET_HEADER]: ticket},
            });
            if (response.status === 200) {
                const parsed = schemas.RestoreOutcome.safeParse(await response.json());
                if (!parsed.success) return {kind: 'down'};
                const {state, reason, waiting} = parsed.data;
                return {kind: 'status', status: {state, reason: reason ?? null, waiting: waiting ?? null}};
            }
            if (response.status !== 404 && response.status !== 401 && response.status !== 423) return {kind: 'down'};
        } catch {
            return {kind: 'down'};
        }
    }
    return readStatusWithSession();
}

/** The status read with the session: 401 when it ended (the restore was kept, or LibreFolio runs without `JWT_SECRET`). */
async function readStatusWithSession(): Promise<RestoreOutcomeRead> {
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
