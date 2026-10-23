/**
 * One restore of the instance, followed from the archive chosen to the server's restart: the state the restore card
 * draws (lot B5b).
 *
 * The archive is uploaded, then checked on a copy by the server (`checking`), which reports what a restore would do
 * (`report`). Confirmed, the server is asked to stop at once, and its next start applies the restore (developer decision
 * P8). The page then waits for the server to come back (`restarting`) and reads what happened (`outcome`): the restore
 * kept, and the page goes to the sign-in page without a message (every session ended); rolled back, with why; or not
 * applied, with why. A restore found waiting (`pending`: confirmed from the command line, or a restart that did not go)
 * offers `restartNow()`.
 *
 * - `loading`: reading the restore's status, then the check this tab followed before a reload.
 * - `idle`: nothing in hand; the last restore's result shows when the status has one.
 * - `uploading`: the archive is being sent (`uploadedBytes` of `totalBytes`).
 * - `checking`: the server checks it on a copy; read again every `pollMs`.
 * - `report`: the check ended: its report, restorable or not.
 * - `confirming`, `cancelling`: the request is out.
 * - `pending`: a restore waits for the next start of the server; `errorCode` set when the restart or the cancel failed.
 * - `in_progress`: a start of the server is applying it.
 * - `restarting`: the server was asked to stop; `outcome` says what the page knows.
 * - `failed`: a request was refused or got no answer: `errorCode`, `failure`.
 *
 * Every action starts a new generation: an answer that arrives for an older one is dropped.
 */
import {get} from 'svelte/store';
import {_} from '$lib/i18n';
import {loginUrl} from '$lib/utils/internalPath';
import {
    backupErrorCode,
    backupErrorLimitMb,
    backupFailureCode,
    cancelPendingRestore,
    confirmRestore,
    deleteRestoreCheck,
    getRestoreCheck,
    getRestoreStatus,
    isEnvelopeFile,
    probeServer,
    requestRestart,
    restoreOutcome,
    startRestoreCheck,
    uploadFailureCode,
    uploadRestoreArchive,
    type RestoreOutcomeRead,
    type RestoreRestartAccepted,
    type RestoreStage,
    type RestoreStatus,
    type RestoreUpload,
    type RestoreUploadOptions,
} from './backupApi';

export type RestoreFlowState = 'loading' | 'idle' | 'password' | 'uploading' | 'checking' | 'report' | 'confirming' | 'pending' | 'in_progress' | 'cancelling' | 'restarting' | 'failed';
export type RestoreFailure = 'status' | 'upload' | 'check' | 'confirm' | 'cancel' | 'restart';
export type RestartOutcome = 'waiting' | 'restored' | 'rolled_back' | 'still_pending' | 'state_unreadable';
export type RestoreEventName = 'backup.restore.uploaded' | 'backup.restore.staged' | 'backup.restore.confirmed' | 'backup.restore.cancelled' | 'backup.restore.restart.requested' | 'backup.restore.failed' | 'backup.restore.restored' | 'backup.restore.rolled_back';

export const RESTORE_STAGE_STORAGE_KEY = 'librefolio.backup.restore.stage';

/**
 * Developer decision P8: once the restore is kept, no message: the page goes to the sign-in page (every session has
 * ended), and from there to the usual first page, where the restored data shows. A full page load: every view of the
 * page still holds the data of before. An object, so that a test replaces it.
 */
export const restoreNavigation = {
    toSignIn(): void {
        window.location.assign(loginUrl(null));
    },
};

/** The confirmation word, typed without regard to case or surrounding spaces. */
export function confirmationMatches(typed: string, word: string): boolean {
    const expected = word.trim().toLocaleLowerCase();
    return expected !== '' && typed.trim().toLocaleLowerCase() === expected;
}

const CONFIRMATION_WORD = /^[a-z]{6,10}$/;

/** Developer decision P8: the words a confirmation may ask for, from the list of the interface language (6 to 10 letters). */
export function confirmationWords(text: string): string[] {
    return [...new Set(text.split(/\s+/).filter((word) => CONFIRMATION_WORD.test(word)))];
}

/** One of `words`, at random; the translated fixed word (`backup.restore.confirm.word`) when there is none. */
export function pickConfirmationWord(words: string[], random: () => number = Math.random): string {
    if (words.length === 0) return get(_)('backup.restore.confirm.word');
    const index = Math.min(words.length - 1, Math.max(0, Math.floor(random() * words.length)));
    return words[index];
}

export interface RestoreApi {
    status(): Promise<RestoreStatus>;
    upload(file: File, options?: RestoreUploadOptions): Promise<RestoreUpload>;
    /** `password`: a secure backup's (lot B4). */
    startCheck(uploadId: string, password?: string): Promise<RestoreStage>;
    getCheck(stageId: string): Promise<RestoreStage>;
    dropCheck(stageId: string): Promise<void>;
    confirm(stageId: string): Promise<RestoreStatus>;
    cancelPending(): Promise<void>;
    restart(): Promise<RestoreRestartAccepted>;
    probeServer(): Promise<'up' | 'down'>;
    restoreOutcome(ticket: string | null): Promise<RestoreOutcomeRead>;
}

export type RestoreStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

export interface RestoreFlowOptions {
    api?: RestoreApi;
    /** Where the followed check's id survives a reload; `null` keeps it in memory only. Default: `sessionStorage`. */
    storage?: RestoreStorage | null;
    /** Pause between two reads of a running check, or two probes of a restarting server, in milliseconds. */
    pollMs?: number;
    /** A server never seen down for this long after the restart was asked: its outcome is read anyway. */
    fastRestartMs?: number;
    /** A server down for this long: `slow`, and the page says to start it again. Up all along, never down, this long
     * after the restart was asked with the restore still waiting: `notStopping`, and the page says to restart it (B-16). */
    slowAfterMs?: number;
    onEvent?: (name: RestoreEventName, detail: Record<string, unknown>) => void;
}

const STAGE_ID = /^[0-9a-f]{32}$/;
const MEGABYTE = 1024 * 1024;
const MAX_POLL_FAILURES = 5;
const MAX_BACKOFF_STEPS = 5;
// A secure backup's check refused with one of these codes asks for its password again; the upload stays on the server.
const PASSWORD_AGAIN = new Set(['wrong_password', 'password_required']);
// A confirmation refused with one of these codes leaves nothing to confirm: the check is forgotten.
const CHECK_GONE = new Set(['restore_stage_not_found', 'restore_stage_expired', 'restore_stage_outdated', 'restore_not_restorable']);

const SERVER_API: RestoreApi = {
    status: getRestoreStatus,
    upload: uploadRestoreArchive,
    startCheck: startRestoreCheck,
    getCheck: getRestoreCheck,
    dropCheck: deleteRestoreCheck,
    confirm: confirmRestore,
    cancelPending: cancelPendingRestore,
    restart: requestRestart,
    probeServer,
    restoreOutcome,
};

function defaultStorage(): RestoreStorage | null {
    try {
        return typeof sessionStorage === 'undefined' ? null : sessionStorage;
    } catch {
        return null;
    }
}

export class RestoreFlowController {
    state = $state<RestoreFlowState>('loading');
    /** The last status read from the server. */
    status = $state<RestoreStatus | null>(null);
    /** The check followed: running, or ended with its report. */
    stage = $state<RestoreStage | null>(null);
    errorCode = $state<string | null>(null);
    failure = $state<RestoreFailure | null>(null);
    /** With `backup_too_large`: the limit, in megabytes. */
    errorLimitMb = $state<number | null>(null);
    uploadedBytes = $state(0);
    totalBytes = $state(0);
    /** A running check the administrator dropped: it is removed once it ends. */
    dropRequested = $state(false);
    outcome = $state<RestartOutcome | null>(null);
    /** Why the restarted server cannot read the state of the restore (`state_unreadable`, B-33). */
    unreadableReason = $state<string | null>(null);
    slow = $state(false);
    /** The server never went down after the restart was asked, and the restore still waits, past `slowAfterMs` (B-16). */
    notStopping = $state(false);
    /** The status read once the server came back, for `rolled_back` and `still_pending`. */
    outcomeStatus = $state<RestoreStatus | null>(null);
    /** A secure backup's password is out to the server: the form waits for its answer. */
    submitting = $state(false);

    report = $derived(this.stage !== null && this.stage.status === 'done' ? (this.stage.report ?? null) : null);
    /** The largest archive the server takes, in megabytes: `0` for no limit, `null` when unknown. */
    limitMb = $derived(this.status?.upload_limit_mb ?? null);
    busy = $derived(this.state === 'loading' || this.state === 'uploading' || this.state === 'checking' || this.state === 'confirming' || this.state === 'cancelling' || this.state === 'restarting' || this.submitting);

    readonly #api: RestoreApi;
    readonly #storage: RestoreStorage | null;
    readonly #pollMs: number;
    readonly #fastRestartMs: number;
    readonly #slowAfterMs: number;
    readonly #onEvent: RestoreFlowOptions['onEvent'];
    #timer: ReturnType<typeof setTimeout> | null = null;
    #abort: AbortController | null = null;
    #failures = 0;
    #generation = 0;
    #disposed = false;
    // The check whose end is news here: started by this controller, or seen running by it.
    #watched: string | null = null;
    #restartAskedAt = 0;
    #downSince: number | null = null;
    #seenDown = false;
    // The one-time ticket of the restart under way (lot B5c): in memory only, never stored nor announced.
    #ticket: string | null = null;
    // The secure backup waiting for its password (lot B4): the file, and its upload once sent, kept for another try.
    #envelope: {file: File; uploadId: string | null} | null = null;

    constructor(options: RestoreFlowOptions = {}) {
        this.#api = options.api ?? SERVER_API;
        this.#storage = options.storage === undefined ? defaultStorage() : options.storage;
        this.#pollMs = options.pollMs ?? 1000;
        this.#fastRestartMs = options.fastRestartMs ?? 30_000;
        this.#slowAfterMs = options.slowAfterMs ?? 60_000;
        this.#onEvent = options.onEvent;
    }

    /** Read the restore's status, then pick up the check this tab followed, while the server still has it. */
    async load(): Promise<void> {
        const generation = this.#next();
        this.state = 'loading';
        this.#setError(null, null);
        this.outcome = null;
        this.outcomeStatus = null;
        this.unreadableReason = null;
        this.slow = false;
        this.notStopping = false;
        this.#ticket = null;
        let status: RestoreStatus;
        try {
            status = await this.#api.status();
        } catch (error) {
            if (this.#stale(generation)) return;
            this.#fail(backupFailureCode(error), 'status');
            return;
        }
        if (this.#stale(generation)) return;
        this.status = status;
        if (status.state === 'pending' || status.state === 'in_progress') {
            this.#forget();
            this.stage = null;
            this.state = status.state;
            return;
        }
        const stageId = this.#remembered();
        if (stageId === null) {
            this.stage = null;
            this.state = 'idle';
            return;
        }
        try {
            const stage = await this.#api.getCheck(stageId);
            if (this.#stale(generation)) return;
            this.#follow(stage, generation, false);
        } catch (error) {
            if (this.#stale(generation)) return;
            if (backupErrorCode(error) === 'restore_stage_not_found') {
                this.#forget();
                this.stage = null;
                this.state = 'idle';
                return;
            }
            this.#fail(backupFailureCode(error), 'check');
        }
    }

    /**
     * Send an archive, then check it on a copy. Refused at once when it is larger than the server's limit. A secure
     * backup (an `.lfbk` envelope, lot B4) waits for its password first: state `password`, nothing sent yet.
     */
    async upload(file: File): Promise<void> {
        if (this.state !== 'idle' && this.state !== 'failed') return;
        const limit = this.limitMb;
        if (limit !== null && limit > 0 && file.size > limit * MEGABYTE) {
            this.#next();
            this.state = 'failed';
            this.errorLimitMb = limit;
            this.#setError('backup_too_large', 'upload');
            this.#emit('backup.restore.failed', {code: 'backup_too_large', what: 'upload'});
            return;
        }
        const generation = this.#next();
        const envelope = await isEnvelopeFile(file).catch(() => false);
        if (this.#stale(generation)) return;
        if (envelope) {
            this.#envelope = {file, uploadId: null};
            this.#setError(null, null);
            this.errorLimitMb = null;
            this.stage = null;
            this.state = 'password';
            return;
        }
        await this.#send(file, null);
    }

    /** Check the secure backup waiting for its password: sent first if it is not yet. A wrong password asks again, and
     * the archive is not sent again. */
    async submitPassword(password: string): Promise<void> {
        const envelope = this.#envelope;
        if (this.state !== 'password' || envelope === null || password === '' || this.submitting) return;
        if (envelope.uploadId === null) {
            await this.#send(envelope.file, password);
            return;
        }
        const generation = this.#next();
        this.submitting = true;
        this.#setError(null, null);
        await this.#check(envelope.uploadId, password, envelope.file, generation);
    }

    /** Leave the secure backup waiting for its password: back to `idle`, the file forgotten. */
    cancelPassword(): void {
        if (this.state !== 'password') return;
        this.#next();
        this.#envelope = null;
        this.submitting = false;
        this.#setError(null, null);
        this.state = 'idle';
    }

    async #send(file: File, password: string | null): Promise<void> {
        const generation = this.#next();
        const abort = new AbortController();
        this.#abort = abort;
        this.state = 'uploading';
        this.#setError(null, null);
        this.errorLimitMb = null;
        this.stage = null;
        this.dropRequested = false;
        this.uploadedBytes = 0;
        this.totalBytes = file.size;
        let upload: RestoreUpload;
        try {
            upload = await this.#api.upload(file, {
                signal: abort.signal,
                onProgress: (loaded, total) => {
                    if (this.#stale(generation)) return;
                    this.uploadedBytes = loaded;
                    this.totalBytes = total;
                },
            });
        } catch (error) {
            if (this.#stale(generation)) return;
            this.#abort = null;
            this.#envelope = null;
            // A proxy's 413 is `proxy_too_large` (B-15): the server never saw the archive.
            const code = uploadFailureCode(error);
            this.errorLimitMb = code === 'backup_too_large' ? backupErrorLimitMb(error) : null;
            this.#fail(code, 'upload');
            return;
        }
        this.#abort = null;
        if (this.#stale(generation)) return;
        this.uploadedBytes = upload.size;
        this.#emit('backup.restore.uploaded', {upload_id: upload.upload_id, size: upload.size});
        if (upload.kind === 'envelope' && password === null) {
            // A secure backup its first bytes did not reveal here: its password, then the same upload.
            this.#envelope = {file, uploadId: upload.upload_id};
            this.state = 'password';
            return;
        }
        await this.#check(upload.upload_id, password, file, generation);
    }

    async #check(uploadId: string, password: string | null, file: File, generation: number): Promise<void> {
        let stage: RestoreStage;
        try {
            stage = await (password === null ? this.#api.startCheck(uploadId) : this.#api.startCheck(uploadId, password));
        } catch (error) {
            if (this.#stale(generation)) return;
            this.submitting = false;
            const code = backupFailureCode(error);
            if (PASSWORD_AGAIN.has(code)) {
                this.#envelope = {file, uploadId};
                this.#setError(code, 'check');
                this.state = 'password';
                return;
            }
            this.#envelope = null;
            this.#fail(code, 'check');
            return;
        }
        if (this.#stale(generation)) return;
        this.submitting = false;
        this.#envelope = null;
        this.#watched = stage.stage_id;
        this.#follow(stage, generation, true);
    }

    /** Stop sending the archive: back to `idle`, nothing kept. */
    abortUpload(): void {
        if (this.state !== 'uploading') return;
        this.#abort?.abort();
        this.#abort = null;
        this.#envelope = null;
        this.#next();
        this.state = 'idle';
        this.uploadedBytes = 0;
        this.totalBytes = 0;
    }

    /** Drop the check and its copy: at once once it ended; a running one is dropped when it ends. */
    async dropCheck(): Promise<void> {
        const stage = this.stage;
        if (stage === null || (this.state !== 'checking' && this.state !== 'report')) return;
        if (this.state === 'checking') {
            this.dropRequested = true;
            const generation = this.#generation;
            try {
                await this.#api.dropCheck(stage.stage_id);
            } catch (error) {
                if (this.#stale(generation)) return;
                const code = backupErrorCode(error);
                // Still running: the polling drops it once it ends.
                if (code === 'restore_stage_running') return;
                if (code !== 'restore_stage_not_found') {
                    this.#fail(backupFailureCode(error), 'cancel');
                    return;
                }
            }
            if (this.#stale(generation)) return;
            await this.#dropped();
            return;
        }
        await this.#dropNow(stage.stage_id);
    }

    /** Confirm the restore of the checked archive, then ask the server to restart at once (developer decision P8). */
    async confirm(): Promise<void> {
        const stage = this.stage;
        if (this.state !== 'report' || stage === null || this.report?.restorable !== true) return;
        const generation = this.#next();
        this.state = 'confirming';
        this.#setError(null, null);
        try {
            const status = await this.#api.confirm(stage.stage_id);
            if (this.#stale(generation)) return;
            this.status = status;
            this.stage = null;
            this.#forget();
            this.state = 'pending';
            this.#emit('backup.restore.confirmed', {stage_id: stage.stage_id});
        } catch (error) {
            if (this.#stale(generation)) return;
            const code = backupFailureCode(error);
            if (CHECK_GONE.has(code)) {
                this.stage = null;
                this.#forget();
            }
            this.#fail(code, 'confirm');
            return;
        }
        await this.#restart(generation);
    }

    /** Drop the restore waiting for the next start: the server drops its checked copy too (B-17). */
    async cancelPending(): Promise<void> {
        if (this.state !== 'pending') return;
        const generation = this.#next();
        this.state = 'cancelling';
        this.#setError(null, null);
        try {
            await this.#api.cancelPending();
        } catch (error) {
            if (this.#stale(generation)) return;
            if (backupErrorCode(error) !== 'restore_not_pending') {
                // The restore still waits: the card shows it with the error, to cancel it again or to restart (B-32).
                const code = backupFailureCode(error);
                this.state = 'pending';
                this.#setError(code, 'cancel');
                this.#emit('backup.restore.failed', {code, what: 'cancel'});
                return;
            }
        }
        if (this.#stale(generation)) return;
        this.#emit('backup.restore.cancelled', {what: 'pending'});
        await this.load();
    }

    /** A restore found waiting: ask the server to stop so that its next start applies it, then wait for it to come back. */
    async restartNow(): Promise<void> {
        if (this.state !== 'pending') return;
        await this.#restart(this.#next());
    }

    async #restart(generation: number): Promise<void> {
        this.state = 'restarting';
        this.outcome = 'waiting';
        this.outcomeStatus = null;
        this.slow = false;
        this.notStopping = false;
        this.#ticket = null;
        this.#setError(null, null);
        let accepted: RestoreRestartAccepted;
        try {
            accepted = await this.#api.restart();
        } catch (error) {
            if (this.#stale(generation)) return;
            const code = backupFailureCode(error);
            this.outcome = null;
            if (code === 'restore_not_pending') {
                // The restore is gone (cancelled from the command line meanwhile): nothing to restart.
                this.#fail(code, 'restart');
                return;
            }
            // The restore stays confirmed: the card offers to restart again, or to cancel it.
            this.state = 'pending';
            this.#setError(code, 'restart');
            this.#emit('backup.restore.failed', {code, what: 'restart'});
            return;
        }
        if (this.#stale(generation)) return;
        this.#ticket = accepted.outcome_ticket ?? null;
        this.#emit('backup.restore.restart.requested', {});
        this.#restartAskedAt = Date.now();
        this.#downSince = null;
        this.#seenDown = false;
        this.#scheduleProbe(generation);
    }

    /** After a failure: read the status again. */
    async retry(): Promise<void> {
        if (this.state !== 'failed') return;
        await this.load();
    }

    /** Stop for good: no more reads, the upload aborted, and no answer still on its way changes the state. */
    dispose(): void {
        this.#disposed = true;
        this.#ticket = null;
        this.#envelope = null;
        this.#abort?.abort();
        this.#abort = null;
        this.#next();
    }

    #follow(stage: RestoreStage, generation: number, announce: boolean): void {
        this.stage = stage;
        if (stage.status === 'running') {
            this.state = 'checking';
            this.#watched = stage.stage_id;
            this.#remember(stage.stage_id);
            this.#schedulePoll(stage.stage_id, generation);
            return;
        }
        const news = announce && this.#watched === stage.stage_id;
        this.#watched = null;
        if (this.dropRequested) {
            void this.#dropNow(stage.stage_id);
            return;
        }
        if (stage.status === 'done') {
            this.state = 'report';
            this.#remember(stage.stage_id);
            if (news) this.#emit('backup.restore.staged', {stage_id: stage.stage_id, restorable: stage.report?.restorable ?? false, action: stage.report?.action ?? null});
            return;
        }
        this.#forget();
        this.#fail(stage.error_code ?? 'stage_failed', 'check', news);
    }

    async #dropNow(stageId: string): Promise<void> {
        const generation = this.#next();
        this.state = 'cancelling';
        this.#setError(null, null);
        try {
            await this.#api.dropCheck(stageId);
        } catch (error) {
            if (this.#stale(generation)) return;
            if (backupErrorCode(error) !== 'restore_stage_not_found') {
                this.dropRequested = false;
                this.#fail(backupFailureCode(error), 'cancel');
                return;
            }
        }
        if (this.#stale(generation)) return;
        await this.#dropped();
    }

    async #dropped(): Promise<void> {
        this.dropRequested = false;
        this.stage = null;
        this.#forget();
        this.#emit('backup.restore.cancelled', {what: 'check'});
        await this.load();
    }

    #schedulePoll(stageId: string, generation: number): void {
        this.#stopTimer();
        const delay = this.#pollMs * Math.min(1 + this.#failures, MAX_BACKOFF_STEPS);
        this.#timer = setTimeout(() => {
            this.#timer = null;
            if (!this.#stale(generation)) void this.#poll(stageId, generation);
        }, delay);
    }

    async #poll(stageId: string, generation: number): Promise<void> {
        try {
            const stage = await this.#api.getCheck(stageId);
            if (this.#stale(generation)) return;
            this.#failures = 0;
            this.#follow(stage, generation, true);
        } catch (error) {
            if (this.#stale(generation)) return;
            if (backupErrorCode(error) === 'restore_stage_not_found') {
                this.#forget();
                this.stage = null;
                this.#fail('restore_stage_not_found', 'check');
                return;
            }
            this.#failures += 1;
            if (this.#failures < MAX_POLL_FAILURES) {
                this.#schedulePoll(stageId, generation);
                return;
            }
            this.#fail(backupFailureCode(error), 'check');
        }
    }

    #scheduleProbe(generation: number): void {
        this.#stopTimer();
        this.#timer = setTimeout(() => {
            this.#timer = null;
            if (!this.#stale(generation)) void this.#probe(generation);
        }, this.#pollMs);
    }

    async #probe(generation: number): Promise<void> {
        const health = await this.#api.probeServer();
        if (this.#stale(generation)) return;
        const now = Date.now();
        if (health === 'down') {
            this.#seenDown = true;
            // Stopping after all: the late stop proceeds as any other.
            this.notStopping = false;
            this.#downSince ??= now;
            if (now - this.#downSince >= this.#slowAfterMs) this.slow = true;
            this.#scheduleProbe(generation);
            return;
        }
        this.#downSince = null;
        const fast = !this.#seenDown && now - this.#restartAskedAt >= this.#fastRestartMs;
        if (this.#seenDown || fast) {
            const read = await this.#api.restoreOutcome(this.#ticket);
            if (this.#stale(generation)) return;
            if (this.#settle(read, fast)) return;
        }
        // Up all along, read and still waiting: the server has not stopped. The page says so, and goes on probing (B-16).
        if (fast && now - this.#restartAskedAt >= this.#slowAfterMs) this.notStopping = true;
        this.#scheduleProbe(generation);
    }

    /** What the restarted server says; whether the wait is over. */
    #settle(read: RestoreOutcomeRead, fast: boolean): boolean {
        if (read.kind === 'down') return false;
        if (read.kind === 'unreadable') {
            // The server is up but cannot tell what became of the restore: asking again would never end (B-33).
            this.slow = false;
            this.notStopping = false;
            this.outcome = 'state_unreadable';
            this.unreadableReason = read.reason;
            return true;
        }
        if (read.kind === 'blocked') {
            // Never applied on a blocked instance (P7), which refuses the status route too: the page says why itself.
            this.slow = false;
            this.notStopping = false;
            this.outcome = 'still_pending';
            this.outcomeStatus = {state: 'pending', waiting: 'instance_blocked'};
            return true;
        }
        if (read.kind === 'signed_out' || read.status.state === 'committed') {
            this.slow = false;
            this.notStopping = false;
            this.outcome = 'restored';
            this.#emit('backup.restore.restored', {});
            restoreNavigation.toSignIn();
            return true;
        }
        const status = read.status;
        if (status.state === 'rolled_back') {
            this.slow = false;
            this.notStopping = false;
            this.outcome = 'rolled_back';
            this.outcomeStatus = status;
            this.#emit('backup.restore.rolled_back', {reason: status.reason ?? null});
            return true;
        }
        // Still pending after a stop seen: not applied (a start left it waiting). Never seen down: not restarted yet.
        if (status.state === 'in_progress' || (fast && status.state === 'pending')) return false;
        this.slow = false;
        this.notStopping = false;
        this.outcome = 'still_pending';
        this.outcomeStatus = status;
        return true;
    }

    #fail(code: string, what: RestoreFailure, announce = true): void {
        this.#stopTimer();
        this.state = 'failed';
        this.#setError(code, what);
        if (announce) this.#emit('backup.restore.failed', {code, what});
    }

    #setError(code: string | null, what: RestoreFailure | null): void {
        this.errorCode = code;
        this.failure = what;
    }

    #emit(name: RestoreEventName, detail: Record<string, unknown>): void {
        this.#onEvent?.(name, detail);
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

    #stopTimer(): void {
        if (this.#timer !== null) {
            clearTimeout(this.#timer);
            this.#timer = null;
        }
    }

    #remembered(): string | null {
        try {
            const stageId = this.#storage?.getItem(RESTORE_STAGE_STORAGE_KEY) ?? null;
            return stageId !== null && STAGE_ID.test(stageId) ? stageId : null;
        } catch {
            return null;
        }
    }

    #remember(stageId: string): void {
        try {
            this.#storage?.setItem(RESTORE_STAGE_STORAGE_KEY, stageId);
        } catch {
            // A full or disabled storage only loses the pick-up after a reload.
        }
    }

    #forget(): void {
        try {
            this.#storage?.removeItem(RESTORE_STAGE_STORAGE_KEY);
        } catch {
            // Same as above.
        }
    }
}
