/**
 * One instance backup, followed from its start to its download: the state the backup card draws.
 *
 * The job lives on the server, which keeps a finished archive for an hour. Its id stays in `sessionStorage`, so leaving
 * the tab or reloading the page picks the same job up again instead of losing track of the archive.
 *
 * - `idle`: no job.
 * - `loading`: reading a job this tab followed before (`resume()`, `recheck()`).
 * - `starting`: the request that starts a backup is out.
 * - `running`: the server is building the archive; the job is read again every `pollMs`.
 * - `done`: the archive is ready to download. `errorCode` may be set all the same: a new start or the delete failed,
 *   and the archive stays on offer.
 * - `deleting`: the request that deletes the archive is out.
 * - `failed`: there is no archive to offer: the job failed, or a request was refused or got no answer.
 *
 * `errorCode` says why (a job's `error_code`, a refusal's `detail.code`, `network` when no answer came, `unexpected` for
 * an answer without a code), and `failure` what failed. The end of a job is announced (`onDone`, or `onFailed` with
 * `job`) once, and only for a job this controller started or saw running: an archive picked up already finished, or
 * read again, is not news.
 *
 * A start refused because another backup runs never names that backup on the card (developer, 19/10): the card says
 * only that one runs, or follows it when the Backup tab started it (B-8). The browser console names it — its id, its
 * origin and its state — with one `console.warn`, whatever the log level, for whoever has to find it.
 *
 * Only a clear start follows such a backup, and offers it only if it ends clear (defect of the review, 19/10). A job
 * records no user: a secure start cannot know whether that backup carries its password, so it says «busy»; and a backup
 * followed for a clear start that ends secure is someone else's, sealed with a password this tab never had — «busy»
 * too. The adoption is kept across a reload (`BACKUP_ADOPTED_STORAGE_KEY`), so `resume()` applies the same check.
 */
import {backupBusyJob, backupErrorCode, backupFailureCode, deleteInstanceBackupJob, getInstanceBackupJob, startInstanceBackup, type InstanceBackupJob} from './backupApi';

export type BackupJobState = 'idle' | 'loading' | 'starting' | 'running' | 'done' | 'deleting' | 'failed';

/** What failed: the request that starts a backup, a read of the job, the delete, or the job itself on the server. */
export type BackupFailure = 'start' | 'read' | 'remove' | 'job';

export interface BackupJobApi {
    /** `password`: a secure backup (lot B4). */
    start(password?: string): Promise<InstanceBackupJob>;
    get(jobId: string): Promise<InstanceBackupJob>;
    remove(jobId: string): Promise<void>;
}

export type BackupJobStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

export interface BackupJobOptions {
    api?: BackupJobApi;
    /** Where the job id survives a reload; `null` keeps it in memory only. Default: `sessionStorage`, when there is one. */
    storage?: BackupJobStorage | null;
    /** Pause between two reads of a running job, in milliseconds. */
    pollMs?: number;
    /** Failed reads in a row before the card stops and offers to check again. */
    maxPollFailures?: number;
    /** A job started here, or seen running here, has just finished with its archive. Called once per job. */
    onDone?: (job: InstanceBackupJob) => void;
    /** A request made here failed, or a job started or seen running here failed (`job`). Never called by `resume()`. */
    onFailed?: (code: string, what: BackupFailure, job: InstanceBackupJob | null) => void;
}

export const BACKUP_JOB_STORAGE_KEY = 'librefolio.backup.job';
/** The job followed from a 409 for a clear start (B-8), kept across reloads: offered only if it ends clear. */
export const BACKUP_ADOPTED_STORAGE_KEY = 'librefolio.backup.adopted';

const JOB_ID = /^[0-9a-f]{32}$/;
const MAX_BACKOFF_STEPS = 5;

const SERVER_API: BackupJobApi = {start: startInstanceBackup, get: getInstanceBackupJob, remove: deleteInstanceBackupJob};

function defaultStorage(): BackupJobStorage | null {
    try {
        return typeof sessionStorage === 'undefined' ? null : sessionStorage;
    } catch {
        return null;
    }
}

/** Share of the archive written, from 0 to 1; `null` while the size is not known yet. */
export function backupProgress(job: InstanceBackupJob | null): number | null {
    if (job === null || job.total_bytes <= 0) return null;
    return Math.min(1, Math.max(0, job.done_bytes / job.total_bytes));
}

export class BackupJobController {
    state = $state<BackupJobState>('idle');
    job = $state<InstanceBackupJob | null>(null);
    errorCode = $state<string | null>(null);
    /** What failed, while `errorCode` is set. */
    failure = $state<BackupFailure | null>(null);
    /** The job this tab follows, kept across reloads: the one a new read or `recheck()` asks for. */
    followedJobId = $state<string | null>(null);
    /** A request is out or a job is running: the card offers no action. */
    busy = $derived(this.state === 'loading' || this.state === 'starting' || this.state === 'running' || this.state === 'deleting');
    progress = $derived(backupProgress(this.job));
    /**
     * Reading the followed job again may still tell its fate: its reads got no usable answer, or a new start failed
     * while it was still followed (refused as busy, most likely because that very job is still running).
     */
    canRecheck = $derived(this.state === 'failed' && (this.job !== null || this.followedJobId !== null) && (this.failure === 'start' || (this.failure === 'read' && (this.errorCode === 'network' || this.errorCode === 'unexpected'))));

    readonly #api: BackupJobApi;
    readonly #storage: BackupJobStorage | null;
    readonly #pollMs: number;
    readonly #maxPollFailures: number;
    readonly #onDone: BackupJobOptions['onDone'];
    readonly #onFailed: BackupJobOptions['onFailed'];
    #timer: ReturnType<typeof setTimeout> | null = null;
    #failures = 0;
    // The job whose end is news here: started by this controller, or seen running by it.
    #watched: string | null = null;
    // The job followed from a 409 for a clear start (B-8): offered only if it ends clear (defect of the review, 19/10).
    #adopted: string | null = null;
    // Every action starts a new generation: an answer that arrives for an older one is dropped.
    #generation = 0;
    #disposed = false;

    constructor(options: BackupJobOptions = {}) {
        this.#api = options.api ?? SERVER_API;
        this.#storage = options.storage === undefined ? defaultStorage() : options.storage;
        this.#pollMs = options.pollMs ?? 1000;
        this.#maxPollFailures = Math.max(1, options.maxPollFailures ?? 5);
        this.#onDone = options.onDone;
        this.#onFailed = options.onFailed;
        this.followedJobId = this.#remembered();
        this.#adopted = this.#rememberedAdoption(this.followedJobId);
    }

    /** Pick up the job this tab followed last, while the server still has it; silent when it is gone. */
    async resume(): Promise<void> {
        const jobId = this.followedJobId;
        if (jobId === null || this.state !== 'idle') return;
        const generation = this.#next();
        this.state = 'loading';
        await this.#read(jobId, generation, false);
    }

    /**
     * Start a new backup; with `password`, a secure one, whose password goes to the server once and is never kept here.
     * Ignored while busy. When it cannot start, an archive already on offer stays on offer.
     */
    async start(password?: string): Promise<void> {
        if (this.busy) return;
        const offered = this.state === 'done' ? this.job : null;
        const generation = this.#next();
        this.state = 'starting';
        this.#setError(null, null);
        this.job = null;
        try {
            const job = await (password === undefined ? this.#api.start() : this.#api.start(password));
            if (this.#stale(generation)) return;
            this.#unadopt();
            this.#watched = job.job_id;
            this.#settle(job, generation, true);
        } catch (error) {
            if (this.#stale(generation)) return;
            // B-8: refused because a backup started from the Backup tab runs — this one, whose answer was lost, or one of
            // another tab: followed as if started here. One started from the command line or the hosting panel is not:
            // its archive goes elsewhere, or is the panel's. With an archive on offer, the offer stays (developer, 19/10).
            const running = backupBusyJob(error);
            // The card never names it; the console does, once per refusal, followed or not (developer, 19/10). The server
            // names a job only while its state says it runs.
            if (running !== null) console.warn('LibreFolio backup: another backup is running', {job_id: running.jobId, origin: running.origin, status: 'running'});
            // Only a clear start follows it (defect of the review, 19/10): a secure one cannot know whether that backup
            // carries its password — a job records no user — so it says «busy», as for the other origins.
            if (running !== null && running.origin === 'ui' && offered === null && password === undefined) {
                this.#watched = running.jobId;
                this.#adopt(running.jobId);
                // Remembered before its first read (developer, 19/10): when that read fails, «Check again» reads it.
                this.#remember(running.jobId);
                this.state = 'loading';
                await this.#read(running.jobId, generation, true);
                return;
            }
            const code = backupFailureCode(error);
            if (offered === null) {
                this.#fail(code, 'start', null, true);
                return;
            }
            this.state = 'done';
            this.job = offered;
            this.#setError(code, 'start');
            this.#onFailed?.(code, 'start', null);
        }
    }

    /** Read the followed job again, when `canRecheck` says it may tell its fate; ignored otherwise. */
    async recheck(): Promise<void> {
        const jobId = this.job?.job_id ?? this.followedJobId;
        if (jobId === null || !this.canRecheck) return;
        const generation = this.#next();
        this.state = 'loading';
        this.#setError(null, null);
        await this.#read(jobId, generation, true);
    }

    /** Delete the archive on offer from the server, then forget its job. When the delete fails, the archive stays. */
    async remove(): Promise<void> {
        const job = this.job;
        if (job === null || this.state !== 'done') return;
        const generation = this.#next();
        this.state = 'deleting';
        this.#setError(null, null);
        try {
            await this.#api.remove(job.job_id);
        } catch (error) {
            if (this.#stale(generation)) return;
            if (backupErrorCode(error) !== 'backup_job_not_found') {
                const code = backupFailureCode(error);
                this.state = 'done';
                this.#setError(code, 'remove');
                this.#onFailed?.(code, 'remove', job);
                return;
            }
        }
        if (this.#stale(generation)) return;
        this.reset();
    }

    /** Back to `idle`, forgetting the job; the server keeps it until it expires. */
    reset(): void {
        this.#next();
        this.state = 'idle';
        this.job = null;
        this.#setError(null, null);
        this.#watched = null;
        this.#forget();
    }

    /** Stop for good: no more reads, and no answer still on its way changes the state. */
    dispose(): void {
        this.#disposed = true;
        this.#next();
    }

    #next(): number {
        this.#stopTimer();
        this.#failures = 0;
        this.#generation += 1;
        return this.#generation;
    }

    #stale(generation: number): boolean {
        return this.#disposed || generation !== this.#generation;
    }

    async #read(jobId: string, generation: number, announce: boolean): Promise<void> {
        try {
            const job = await this.#api.get(jobId);
            if (this.#stale(generation)) return;
            this.#failures = 0;
            this.#settle(job, generation, announce);
        } catch (error) {
            if (this.#stale(generation)) return;
            const code = backupErrorCode(error);
            if (code === 'backup_job_not_found') {
                this.#forget();
                this.#watched = null;
                if (!announce) {
                    this.state = 'idle';
                    this.job = null;
                    return;
                }
                this.#fail(code, 'read', null, true);
                return;
            }
            if (this.state === 'running') {
                this.#failures += 1;
                if (this.#failures < this.#maxPollFailures) {
                    this.#schedule(jobId, generation);
                    return;
                }
            }
            this.#fail(backupFailureCode(error), 'read', this.job, announce);
        }
    }

    #settle(job: InstanceBackupJob, generation: number, announce: boolean): void {
        this.job = job;
        if (job.status === 'running') {
            this.state = 'running';
            this.#setError(null, null);
            this.#watched = job.job_id;
            this.#remember(job.job_id);
            this.#schedule(job.job_id, generation);
            return;
        }
        const news = announce && this.#watched === job.job_id;
        this.#watched = null;
        if (job.status === 'done') {
            if (job.job_id === this.#adopted && job.encrypted) {
                // Followed for a clear start, it ended secure: someone else's backup, sealed with a password this tab never
                // had. Not this request's result: «busy», as for the other origins, and forgotten (defect of the review).
                this.#forget();
                this.#fail('backup_busy', 'start', null, news);
                return;
            }
            this.state = 'done';
            this.#setError(null, null);
            this.#remember(job.job_id);
            if (news) this.#onDone?.(job);
            return;
        }
        this.#forget();
        this.#fail(job.error_code ?? 'backup_failed', 'job', job, news);
    }

    #fail(code: string, what: BackupFailure, job: InstanceBackupJob | null, announce: boolean): void {
        this.#stopTimer();
        this.state = 'failed';
        this.job = job;
        this.#setError(code, what);
        if (announce) this.#onFailed?.(code, what, job);
    }

    #setError(code: string | null, what: BackupFailure | null): void {
        this.errorCode = code;
        this.failure = what;
    }

    #schedule(jobId: string, generation: number): void {
        this.#stopTimer();
        const delay = this.#pollMs * Math.min(1 + this.#failures, MAX_BACKOFF_STEPS);
        this.#timer = setTimeout(() => {
            this.#timer = null;
            if (!this.#stale(generation)) void this.#read(jobId, generation, true);
        }, delay);
    }

    #stopTimer(): void {
        if (this.#timer !== null) {
            clearTimeout(this.#timer);
            this.#timer = null;
        }
    }

    #remembered(): string | null {
        try {
            const jobId = this.#storage?.getItem(BACKUP_JOB_STORAGE_KEY) ?? null;
            return jobId !== null && JOB_ID.test(jobId) ? jobId : null;
        } catch {
            return null;
        }
    }

    #remember(jobId: string): void {
        this.followedJobId = jobId;
        try {
            this.#storage?.setItem(BACKUP_JOB_STORAGE_KEY, jobId);
        } catch {
            // A full or disabled storage only loses the pick-up after a reload.
        }
    }

    #forget(): void {
        this.followedJobId = null;
        try {
            this.#storage?.removeItem(BACKUP_JOB_STORAGE_KEY);
        } catch {
            // Same as above.
        }
        this.#unadopt();
    }

    /** The adoption a previous page kept, when it names the job followed; any other is dropped. */
    #rememberedAdoption(followed: string | null): string | null {
        try {
            const adopted = this.#storage?.getItem(BACKUP_ADOPTED_STORAGE_KEY) ?? null;
            if (adopted === null) return null;
            if (adopted === followed) return adopted;
            this.#storage?.removeItem(BACKUP_ADOPTED_STORAGE_KEY);
        } catch {
            // Same as above.
        }
        return null;
    }

    #adopt(jobId: string): void {
        this.#adopted = jobId;
        try {
            this.#storage?.setItem(BACKUP_ADOPTED_STORAGE_KEY, jobId);
        } catch {
            // Same as above.
        }
    }

    // Storage is touched only when there is an adoption to drop: the other paths make no extra call.
    #unadopt(): void {
        if (this.#adopted === null) return;
        this.#adopted = null;
        try {
            this.#storage?.removeItem(BACKUP_ADOPTED_STORAGE_KEY);
        } catch {
            // Same as above.
        }
    }
}
