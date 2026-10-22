// @vitest-environment jsdom
/**
 * RestoreFlowController — restoring the instance from an archive, from the file chosen to the server started again
 * (restoreFlow.svelte.ts, workstream B, lot B5b). Written red first, against `b5b-contract.md` §0 (the developer's P8 and
 * P7 decisions, which override the rest), §1, §2, §2b and §2c: the module does not exist yet. Lot B5c (the outcome read
 * with a one-time ticket, and B-17) was written red first in its turn, against its approved contract.
 *
 * The contract under test:
 *   - the words of the confirmation (§0.4): `confirmationWords(text)` keeps the words of the list matching
 *     `^[a-z]{6,10}$`, in order, without duplicates; `pickConfirmationWord(words, random = Math.random)` is
 *     `words[Math.floor(random() * words.length)]`, and an empty list falls back to the translated
 *     `backup.restore.confirm.word`; `confirmationMatches(typed, word)`: equal once both are trimmed and lower-cased,
 *     nothing else (no accent folding, inner spaces kept), and the empty string never matches;
 *   - `restoreNavigation.toSignIn()` is how a success leaves the page (§0.2); `AFTER_RESTORE_PATH` is gone (§0.6);
 *   - `load()`: `loading` (busy) while `GET /restore/status` is out; then what the status says — `pending` (its `waiting`,
 *     `instance_blocked` included, in `status`), `in_progress`, or `idle` with the status kept (the card decides what to
 *     show of a last result); nothing else read, nothing announced; `limitMb` is the status's `upload_limit_mb` (0: no
 *     limit, null: unknown); a status read with no usable answer → `failed`, failure `status`; `retry()`, from `failed`
 *     only, reads it again with the error cleared, and announces a failure;
 *   - the pick-up: a check this tab followed (`sessionStorage`, `librefolio.backup.restore.stage`) is read after the
 *     status — still running: `checking`, polled, its end announced (`staged`: a check seen running here); done:
 *     `report`, the stage still remembered; gone (404): forgotten silently — `idle`, no error, no event; failed:
 *     `failed` with its `error_code`, failure `check`, forgotten; no answer: `failed`, `network`, failure `check`, the
 *     stage kept;
 *   - `upload(file)`: any file name; a file larger than `limitMb` megabytes — 1024 × 1024 bytes each, as the server counts
 *     — is refused at once when the limit is above 0: `failed`, `backup_too_large`, `errorLimitMb` the limit, failure
 *     `upload`, nothing sent, announced; a limit of 0 or null sends it, and so does a file of exactly the limit; a second
 *     `upload()` while one is out is ignored;
 *   - the PUT: `uploading` (busy), `uploadedBytes`/`totalBytes` following its `onProgress`, an AbortSignal handed to it;
 *     `abortUpload()` aborts it and comes back to `idle` with nothing announced, an answer that comes after is dropped,
 *     and outside an upload it does nothing; a refusal → `failed` (`upload`) with its code, and `backup_too_large` takes
 *     the server's `limit_mb` as `errorLimitMb`; then `uploaded {upload_id, size}` and `POST /stage` with the upload id,
 *     whose refusal is `failed` (`check`);
 *   - `checking` (busy): the stage, remembered in the storage, read every `pollMs` and not before, its phase and bytes in
 *     `stage`, `report` null; done → `report`, not busy, `report` the stage's report, the stage still remembered,
 *     `staged {stage_id, restorable, action}` once, never read again — an archive that cannot be restored included;
 *     failed → `failed` (`check`) with its `error_code`, forgotten, announced; gone (404) → `failed` (`check`) with
 *     `restore_stage_not_found`, forgotten, announced; reads with no answer → in the end `failed` (`check`) with
 *     `network`, announced, the stage kept, no timer left;
 *   - `dropCheck()`: from `report`, `DELETE /stage/{id}`, then `idle` with nothing followed and `cancelled {what:
 *     'check'}`; a check already gone (404) ends the same way; while the check runs, the `409 restore_stage_running` keeps
 *     the polling going and the check is dropped by a second DELETE once it has ended — never shown as a report, no
 *     `staged`, no failure; any other refusal → `failed` (`cancel`), the stage still remembered, announced;
 *   - `confirm()` (§0.1), from a restorable `report` only: `confirming` (busy) while `POST …/confirm` is out, then at once
 *     `POST /restore/restart`: `restarting` (busy), and once accepted `outcome` `waiting`; `confirmed {stage_id}` then
 *     `restart.requested {}`; the stage forgotten, the confirm's answer kept as `status`. A refused confirm → `failed`
 *     (`confirm`), nothing restarted. A restart refused with `409 restore_not_pending` — the restore no longer exists,
 *     cancelled from the command line meanwhile — → `failed` (`restart`), the error announced, `outcome` null, nothing
 *     probed, the status read again only by `retry()` (the developer's decision of 11:47); any other refusal →
 *     `pending` with the error (`failure` `restart`): the restore stays confirmed, and nothing is probed;
 *   - a restore found pending at load: `restartNow()` does the same restart, and a refusal ends the same two ways;
 *     `cancelPending()` is `cancelling` (busy) while `DELETE /pending` is out; once it is accepted, the status read
 *     again, `cancelled {what: 'pending'}` once. The checked copy goes with the restore on the server, as the command
 *     line's `backup pending --cancel` does (B-17): the controller never sends a `DELETE /stage` of its own — not after
 *     an accepted cancel, whatever the status held says of the copy (its `stage_id`, null, or none), and not after any
 *     refusal. A `404 restore_not_pending` (the restore became something else, a start applying it maybe) reads the
 *     status again without failing; another refusal → `pending` with the error (`failure` `cancel`), as B-32 decided;
 *   - the probe: `probeServer()` every `pollMs` once the restart is accepted; seen `down` then `up` → `restoreOutcome()`
 *     once, with the restart's ticket (below): `signed_out`, or a `committed` status → `restored`, `restored {}`,
 *     `restoreNavigation.toSignIn()` once (no message, §0.2); a `rolled_back` status → `rolled_back`, `outcomeStatus`,
 *     `rolled_back {reason}`; a `pending` status → `still_pending`, `outcomeStatus` with its `waiting`, nothing
 *     announced (§0.3); `blocked` — the hosting provider blocked the instance, and the status route answers 423 with
 *     every restore route — → `still_pending` as well (P8: the failure on the same screen, with the reason),
 *     `outcomeStatus` exactly `{state: 'pending', waiting: 'instance_blocked'}`, built by the page because the server
 *     cannot be read (a blocked instance leaves the restore waiting for the unblock, P7), nothing announced, no sign-in.
 *     Up all along → the outcome is not read before `fastRestartMs`, then read anyway: `signed_out` → `restored`,
 *     `pending` → keep waiting and probing, `rolled_back` → `rolled_back`, `blocked` → `still_pending` at once (no start
 *     applies a restore while the instance is blocked). Down all along → `slow` only after `slowAfterMs`, and the
 *     probing goes on. Once the outcome is known nothing is probed again and no timer is left; `load()` (back to the
 *     tab) clears `outcome` and `slow`;
 *   - the outcome ticket (B5c): an accepted restart answers the status and a one-time `outcome_ticket`, which reads its
 *     outcome without a session (`RestoreApi.restoreOutcome(ticket)`). The controller holds it in memory, for that
 *     restart only: every `restoreOutcome()` of the restart is called with it — after a stop seen, at the fast read, and
 *     at every read after that —; a new restart (`restartNow()` after a refusal, or after the tab is back) reads with its
 *     own ticket, an older one never, and an accepted restart answered after a newer one brings no ticket in; a refused
 *     restart leaves none, and a read without a ticket passes `null`; `load()` and `dispose()` forget it. It is never
 *     written to a storage — the one given, `sessionStorage`, `localStorage` — and never in the detail of an event;
 *   - `busy` holds in `loading`, `uploading`, `checking`, `confirming`, `cancelling` and `restarting` only;
 *   - `dispose()` drops every answer still on its way and stops every timer; an answer of an older generation never
 *     changes the state;
 *   - a storage that throws, or none (`storage: null`), never breaks the flow; the default storage is `sessionStorage`,
 *     the default api the functions of backupApi.ts, the default `pollMs` 1000.
 *
 * Choices of this file where the contract is silent, each one place to change: the check is first read `pollMs` after it
 * started, as backupJob.svelte.ts does; `staged` is announced for a check seen running here (B5a's decision 2); a refused
 * drop is `failed` with failure `cancel`; the polling that gets no answer gives up within thirty pauses; a refused
 * `restartNow()` is `pending` with the error, like the restart after a confirm (§0.1: «a restart that failed» shows the
 * pending block), `restore_not_pending` aside, as decided since; so is a refused `cancelPending()`, failure `cancel`,
 * `restore_not_pending` aside (B-32 §1: the restore still waits, and the failed screen would offer an archive whose
 * confirmation the server refuses); the fast read maps a rolled-back status to `rolled_back`; `load()` ends a restart
 * episode. Left open on purpose: whether the pick-up of a check already done is announced, whether a status read that
 * fails at mount is announced (B5a's pick-up is silent; a `retry()` that fails must be), the state while the DELETE of
 * `dropCheck()` is out, whether the status is read again after an aborted upload, `outcome` while the restart request is
 * still out, and the state once the outcome is known.
 *
 * What of the ticket cannot be seen, and how this file sees the rest. Nothing reads after `dispose()`, so its forgetting
 * has no case. A read happens only after an accepted restart, which carries its own ticket, and every way from an
 * accepted restart back to `pending` goes through `load()`: so «a refused restart leaves none» is seen together with
 * `load()` forgetting, through a restart answered without a ticket (the type requires one; the fake casts), whose reads
 * pass `null` — never the ticket before. Every absence (no storage, no event) is asserted after its presence barrier:
 * the reads carried the ticket, so the controller did hold it.
 *
 * The outcome `blocked` and the copy dropped by `cancelPending()` came after the first green, decided by the workstream
 * to honour P7 and P8, and were written red first in their turn. With B5c the copy left the page (B-17): the server
 * drops it with the cancel, and the cases of B5b that expected `cancelPending()` to drop it now expect no drop at all.
 *
 * Every test injects a fake api — a call it does not expect rejects, naming the call — and an in-memory storage, and runs
 * on fake timers; `pollMs`, `fastRestartMs` and `slowAfterMs` are not the defaults, so a controller that ignored them
 * would be seen, and the defaults have their own cases. One gap in that net: a call the controller sends and swallows
 * rejects unseen — the best-effort drop of B5b did exactly that —, so every case of `cancelPending()` says
 * `not.toHaveBeenCalled()` of `dropCheck()`, whatever the fake would have answered. The server of a restart is a box
 * the test flips between `up` and `down`: `probeServer()` answers what it holds whenever it is asked, so no case depends
 * on when the first probe goes out. `restoreNavigation.toSignIn` is replaced by a spy before every controller is built,
 * so nothing navigates. `$lib/i18n` is a translator that answers `⟦key⟧`, so the fallback word is proven to be the
 * translation of its key without naming a language. `$lib/api` is mocked with the five aliases the default api reaches
 * here, which only the last group (no `api` option) uses. `sessionStorage` is the environment's own. Not `localStorage`:
 * Node 26 ships a global one that is unavailable without `--localstorage-file`, and it hides jsdom's (`undefined` here),
 * so the case that inspects it owns an in-memory one, installed with `vi.stubGlobal` before the controller exists — a
 * write of the controller lands where the case reads it back —, and every case ends with `vi.unstubAllGlobals()`.
 *
 * The module is loaded through `import.meta.glob`, not imported: while it does not exist each case fails on its own and
 * names it, instead of the whole file failing at collection, and the type check does not wait for it. The types below
 * are the contract's (§2b, and B5c's), written out for the same reason.
 *
 * jsdom, not node: `busy`, `report` and `limitMb` are `$derived`, which the node environment leaves stale (see
 * `$test/runes.svelte`); `assertEffectsRun()` fails the whole file loudly if the docblock above is ever lost.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import type {z} from 'zod';
import type {schemas} from '$lib/api';
import {assertEffectsRun} from '$test/runes.svelte';
import {restoreErrorKey} from './restoreText';

const zodios = vi.hoisted(() => ({
    get_restore_status_api_v1_backup_restore_status_get: vi.fn(),
    upload_restore_archive_api_v1_backup_restore_upload_put: vi.fn(),
    start_restore_check_api_v1_backup_restore_stage_post: vi.fn(),
    get_restore_check_api_v1_backup_restore_stage__stage_id__get: vi.fn(),
    delete_restore_check_api_v1_backup_restore_stage__stage_id__delete: vi.fn(),
}));
vi.mock('$lib/api', () => ({zodiosApi: zodios, schemas: {}}));

// The translator answers `⟦key⟧`: the fallback word of an empty list is proven to be the translation of its key.
vi.mock('$lib/i18n', async () => {
    const {readable, writable} = await import('svelte/store');
    const translate = (key: string) => `⟦${key}⟧`;
    return {
        _: readable(translate),
        t: readable(translate),
        locale: writable('en'),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it', 'fr', 'es'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano', fr: 'Français', es: 'Español'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT', fr: 'FR', es: 'ES'},
        LANGUAGE_OPTIONS: [{code: 'en', name: 'English', flag: 'EN'}],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

// --- The contract (§0, §2b), written out ------------------------------------------------------------------------------

type RestoreStatus = z.infer<typeof schemas.RestoreStatus>;
type RestoreStage = z.infer<typeof schemas.RestoreStage>;
type RestoreStageReport = z.infer<typeof schemas.RestoreStageReport>;
type RestoreUpload = z.infer<typeof schemas.RestoreUpload>;
type RollbackReason = NonNullable<RestoreStatus['reason']>;
/** The waiting reasons of §0.5: the generated client does not know `instance_blocked` yet (P7). */
type WaitingReason = NonNullable<RestoreStatus['waiting']> | 'instance_blocked';

type RestoreFlowState = 'loading' | 'idle' | 'uploading' | 'checking' | 'report' | 'confirming' | 'pending' | 'in_progress' | 'cancelling' | 'restarting' | 'failed';
type RestoreFailure = 'status' | 'upload' | 'check' | 'confirm' | 'cancel' | 'restart';
/** `state_unreadable` and `unreadable` (SEC-3/4/5 wave, «the status 500»): the server cannot read the state of the restore. */
type RestartOutcome = 'waiting' | 'restored' | 'rolled_back' | 'still_pending' | 'state_unreadable';
type RestoreOutcomeAnswer = {kind: 'signed_out'} | {kind: 'status'; status: RestoreStatus} | {kind: 'blocked'} | {kind: 'unreadable'; reason: string | null} | {kind: 'down'};
type UploadOptions = {onProgress?: (loaded: number, total: number) => void; signal?: AbortSignal};
/** The answer of an accepted restart (B5c): the status, and the one-time ticket that reads its outcome. Not generated yet. */
type RestoreRestartAccepted = RestoreStatus & {outcome_ticket: string};

interface RestoreApi {
    status(): Promise<RestoreStatus>;
    upload(file: File, options?: UploadOptions): Promise<RestoreUpload>;
    startCheck(uploadId: string): Promise<RestoreStage>;
    getCheck(stageId: string): Promise<RestoreStage>;
    dropCheck(stageId: string): Promise<void>;
    confirm(stageId: string): Promise<RestoreStatus>;
    cancelPending(): Promise<void>;
    restart(): Promise<RestoreRestartAccepted>;
    probeServer(): Promise<'up' | 'down'>;
    restoreOutcome(ticket: string | null): Promise<RestoreOutcomeAnswer>;
}

interface RestoreFlowOptions {
    api?: RestoreApi;
    storage?: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'> | null;
    pollMs?: number;
    fastRestartMs?: number;
    slowAfterMs?: number;
    onEvent?: (name: string, detail: Record<string, unknown>) => void;
}

interface RestoreFlowController {
    readonly state: RestoreFlowState;
    readonly status: RestoreStatus | null;
    readonly stage: RestoreStage | null;
    readonly report: RestoreStageReport | null;
    readonly errorCode: string | null;
    readonly failure: RestoreFailure | null;
    readonly errorLimitMb: number | null;
    readonly uploadedBytes: number;
    readonly totalBytes: number;
    readonly limitMb: number | null;
    readonly busy: boolean;
    readonly outcome: RestartOutcome | null;
    readonly slow: boolean;
    readonly outcomeStatus: RestoreStatus | null;
    load(): Promise<void>;
    upload(file: File): Promise<void>;
    abortUpload(): void;
    dropCheck(): Promise<void>;
    confirm(): Promise<void>;
    cancelPending(): Promise<void>;
    restartNow(): Promise<void>;
    retry(): Promise<void>;
    dispose(): void;
}

interface RestoreFlowModule {
    RestoreFlowController: new (options?: RestoreFlowOptions) => RestoreFlowController;
    RESTORE_STAGE_STORAGE_KEY: string;
    restoreNavigation: {toSignIn(): void};
    confirmationWords: (text: string) => string[];
    pickConfirmationWord: (words: string[], random?: () => number) => string;
    confirmationMatches: (typed: string, word: string) => boolean;
}

const FLOW_MODULES = import.meta.glob<Partial<RestoreFlowModule>>('./restoreFlow.svelte.ts');

/** restoreFlow.svelte.ts, or a failure that names what is missing. */
async function loadFlow(): Promise<RestoreFlowModule> {
    const load = FLOW_MODULES['./restoreFlow.svelte.ts'];
    if (!load) throw new Error('src/lib/features/backup/restoreFlow.svelte.ts does not exist yet: the restore card has no controller (B5b contract §2b)');
    const module = await load();
    for (const name of ['RestoreFlowController', 'confirmationWords', 'pickConfirmationWord', 'confirmationMatches'] as const) {
        expect(typeof module[name], `restoreFlow.svelte.ts exports no ${name}`).toBe('function');
    }
    expect(typeof module.RESTORE_STAGE_STORAGE_KEY, 'restoreFlow.svelte.ts exports no RESTORE_STAGE_STORAGE_KEY').toBe('string');
    expect(typeof module.restoreNavigation?.toSignIn, 'restoreFlow.svelte.ts exports no restoreNavigation.toSignIn() (§0.2)').toBe('function');
    return module as RestoreFlowModule;
}

// --- Fixtures ---------------------------------------------------------------------------------------------------------

const UPLOAD_ID = '0123456789abcdef0123456789abcdef';
const STAGE_ID = 'fedcba9876543210fedcba9876543210';
const OTHER_STAGE_ID = '00112233445566778899aabbccddeeff';
/** The key of §2b, written out: the storage is checked against the contract, not against the export. */
const KEY = 'librefolio.backup.restore.stage';
/** A megabyte as the server counts it (`_MEGABYTE` in backend/app/api/v1/backup/restore.py). */
const MIB = 1024 * 1024;
/** Not the default pause (1000 ms): a controller that ignored the option would be seen. */
const POLL_MS = 200;
/** Not the defaults (30 000 and 60 000 ms), in the same proportion. */
const FAST_MS = 3_000;
const SLOW_MS = 6_000;

const REASONS: RollbackReason[] = ['first_start_failed', 'swap_interrupted', 'swap_failed', 'stage_missing'];
const WAITINGS: WaitingReason[] = ['backup_running', 'other_data_directory', 'server_running', 'instance_blocked'];

type StatusFields = Omit<Partial<RestoreStatus>, 'waiting'> & {waiting?: WaitingReason | null};

function restoreStatus(overrides: StatusFields = {}): RestoreStatus {
    return {state: 'none', stage_id: null, confirmed_at: null, confirmed_by: null, backup_created_at: null, backup_app_version: null, action: null, finished_at: null, reason: null, waiting: null, upload_limit_mb: 500, ...overrides} as RestoreStatus;
}

const none = (overrides: StatusFields = {}) => restoreStatus({state: 'none', ...overrides});

const confirmedFields: StatusFields = {stage_id: STAGE_ID, confirmed_at: '2026-10-16T11:20:00Z', confirmed_by: 'admin', backup_created_at: '2026-10-15T12:00:00Z', backup_app_version: '0.9.0', action: 'same'};

const pending = (overrides: StatusFields = {}) => restoreStatus({state: 'pending', ...confirmedFields, ...overrides});

const inProgress = () => restoreStatus({state: 'in_progress', ...confirmedFields});

const committed = () => restoreStatus({state: 'committed', ...confirmedFields, finished_at: '2026-10-16T11:21:00Z'});

const rolledBack = (reason: RollbackReason) => restoreStatus({state: 'rolled_back', ...confirmedFields, finished_at: '2026-10-16T11:21:00Z', reason});

/** Tickets as the server makes them (`secrets.token_urlsafe(32)`), one per accepted restart (B5c). */
const TICKET = 'kq8Z3vR-wT0yN5mB_xH2cL7pJ4sF9dG1eA6uK0iO3rY';
const OTHER_TICKET = 'Pz4_hW9nQe2bX7-vM1tS8cJ5kD0gR3yL6aU9fN2oEi7';

/** What an accepted restart answers (B5c): the restore still pending, and the ticket that reads its outcome. */
const accepted = (ticket: string = TICKET): RestoreRestartAccepted => ({...pending(), outcome_ticket: ticket});

/** What the outcome route answers (B5c): its three fields, nothing else — no name, no date, no version. */
const outcomeOf = (state: RestoreStatus['state'], reason: RollbackReason | null = null, waiting: WaitingReason | null = null) => ({state, reason, waiting}) as RestoreStatus;

/** B4 (§5): what a report says of the archive's encryption and of the plugin secrets. Written out until the client is generated again. */
type ReportB4Fields = {encrypted: boolean; secrets_unreadable: {system: number; user: number}; secrets_rekeyed: number};
/** B4 (§5): an upload says what was stored, a zip or an envelope. Written out until the client is generated again. */
type Upload = RestoreUpload & {kind: 'zip' | 'envelope'};

function report(overrides: Partial<RestoreStageReport & ReportB4Fields> = {}): RestoreStageReport & ReportB4Fields {
    return {
        backup_created_at: '2026-10-15T12:00:00Z',
        backup_app_version: '0.9.0',
        backup_origin: 'ui',
        backup_revision: 'c0ffee000001',
        app_version: '0.9.0',
        head_revision: 'c0ffee000001',
        action: 'same',
        migrations: [],
        post_migration_fixes: [],
        tables: {asset: {before: 12, after: 12}},
        foreign_key_violations_before: 0,
        foreign_key_violations_after: 0,
        files: 3,
        files_size: 2048,
        database_size: MIB,
        instance_key_included: false,
        administrators: ['admin'],
        warnings: [],
        blockers: [],
        control_totals: 'same',
        control_totals_differences: [],
        control_totals_differences_count: 0,
        restorable: true,
        expires_at: '2026-10-16T12:00:00Z',
        encrypted: false,
        secrets_unreadable: {system: 0, user: 0},
        secrets_rekeyed: 0,
        ...overrides,
    };
}

function stage(overrides: Partial<RestoreStage> = {}): RestoreStage {
    return {stage_id: STAGE_ID, status: 'running', phase: 'checking', done_bytes: 0, total_bytes: 0, created_at: '2026-10-16T09:00:00Z', finished_at: null, error_code: null, report: null, ...overrides};
}

const runningStage = (overrides: Partial<RestoreStage> = {}) => stage({status: 'running', ...overrides});

const doneStage = (answer: RestoreStageReport = report(), overrides: Partial<RestoreStage> = {}) => stage({status: 'done', phase: null, done_bytes: 4096, total_bytes: 4096, finished_at: '2026-10-16T09:01:00Z', report: answer, ...overrides});

const failedStage = (code: string) => stage({status: 'failed', phase: null, finished_at: '2026-10-16T09:01:00Z', error_code: code as RestoreStage['error_code']});

const uploaded = (overrides: Partial<Upload> = {}): Upload => ({upload_id: UPLOAD_ID, size: 4096, kind: 'zip', ...overrides});

/** An archive of `size` bytes: the size is set on the File, so a large one costs no memory. */
function archive(size = 4096, name = 'librefolio-backup-20261015-120000.zip'): File {
    const file = new File(['PK\u0003\u0004'], name, {type: 'application/zip'});
    Object.defineProperty(file, 'size', {value: size});
    return file;
}

/** A refusal as the backup routes word it, raised by axios: `detail: {code, message, …}`. */
function refusal(status: number, code: string, extra: Record<string, unknown> = {}) {
    return {isAxiosError: true, message: `Request failed with status code ${status}`, response: {status, data: {detail: {code, message: `refused: ${code}`, ...extra}}}};
}

/** No answer came (down, unreachable, timed out): axios rejects with no `response`. */
const noAnswer = () => ({isAxiosError: true, message: 'Network Error', code: 'ERR_NETWORK', response: undefined});

/** An answer without a code: FastAPI's default 500. */
const codelessAnswer = () => ({isAxiosError: true, message: 'Request failed with status code 500', response: {status: 500, data: {detail: 'Internal Server Error'}}});

/** What axios rejects with when the request's AbortSignal fires. */
const canceled = () => ({isAxiosError: true, name: 'CanceledError', message: 'canceled', code: 'ERR_CANCELED', __CANCEL__: true, response: undefined});

interface Deferred<T> {
    promise: Promise<T>;
    resolve: (value: T) => void;
    reject: (reason: unknown) => void;
}

function deferred<T>(): Deferred<T> {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** A Web Storage stand-in the test can read back: the storage given to the controller, or a global the case owns (`vi.stubGlobal`). */
function memoryStorage(initial: Record<string, string> = {}) {
    const items = new Map<string, string>(Object.entries(initial));
    return {
        items,
        get length() {
            return items.size;
        },
        key: vi.fn((index: number) => [...items.keys()][index] ?? null),
        getItem: vi.fn((key: string) => items.get(key) ?? null),
        setItem: vi.fn((key: string, value: string) => {
            items.set(key, String(value));
        }),
        removeItem: vi.fn((key: string) => {
            items.delete(key);
        }),
        clear: vi.fn(() => {
            items.clear();
        }),
    };
}

/** Every call of the api rejects, naming itself, unless the test answered it. */
function fakeApi() {
    const unexpected = (name: string) => (): Promise<never> => Promise.reject(new Error(`api.${name}(): a call this test did not expect`));
    return {
        status: vi.fn<RestoreApi['status']>(unexpected('status')),
        upload: vi.fn<RestoreApi['upload']>(unexpected('upload')),
        startCheck: vi.fn<RestoreApi['startCheck']>(unexpected('startCheck')),
        getCheck: vi.fn<RestoreApi['getCheck']>(unexpected('getCheck')),
        dropCheck: vi.fn<RestoreApi['dropCheck']>(unexpected('dropCheck')),
        confirm: vi.fn<RestoreApi['confirm']>(unexpected('confirm')),
        cancelPending: vi.fn<RestoreApi['cancelPending']>(unexpected('cancelPending')),
        restart: vi.fn<RestoreApi['restart']>(unexpected('restart')),
        probeServer: vi.fn<RestoreApi['probeServer']>(unexpected('probeServer')),
        restoreOutcome: vi.fn<RestoreApi['restoreOutcome']>(unexpected('restoreOutcome')),
    };
}

const controllers: RestoreFlowController[] = [];

/** A controller over a fake api and an in-memory storage; `stored` is the stage id a previous page left in it. */
async function setup(options: RestoreFlowOptions & {stored?: string} = {}) {
    const {RestoreFlowController, restoreNavigation} = await loadFlow();
    const {stored, ...overrides} = options;
    const api = fakeApi();
    const storage = memoryStorage(stored === undefined ? {} : {[KEY]: stored});
    const onEvent = vi.fn<NonNullable<RestoreFlowOptions['onEvent']>>();
    // Before the controller exists, so that one keeping a reference at construction holds the spy too; nothing navigates.
    const toSignIn: MockInstance<() => void> = vi.isMockFunction(restoreNavigation.toSignIn) ? vi.mocked(restoreNavigation.toSignIn) : vi.spyOn(restoreNavigation, 'toSignIn').mockImplementation(() => undefined);
    const controller = new RestoreFlowController({api, storage, pollMs: POLL_MS, fastRestartMs: FAST_MS, slowAfterMs: SLOW_MS, onEvent, ...overrides});
    controllers.push(controller);
    /** What the controller announced, in order, as [name, detail]. */
    const events = () => onEvent.mock.calls.map(([name, detail]) => [name, detail]);
    /** The names it announced, in order. */
    const names = () => onEvent.mock.calls.map(([name]) => name);
    return {controller, api, storage, onEvent, events, names, toSignIn};
}

type Context = Awaited<ReturnType<typeof setup>>;

/**
 * Let every answer already given reach the controller (no time passes). The cases that leave a polling running never
 * await the action that started it: the contract does not say whether `load()`, `upload()`, `dropCheck()`, `confirm()`
 * or `restartNow()` settle before the polling they start, or after it.
 */
const flush = () => vi.advanceTimersByTimeAsync(0);

/** `load()`, its status read answered with `answer`. */
async function loaded(context: Context, answer: RestoreStatus = none()): Promise<void> {
    context.api.status.mockResolvedValueOnce(answer);
    void context.controller.load();
    await flush();
}

/** A controller in `idle`, its status read (`none` with these fields), nothing followed. */
async function idle(overrides: StatusFields = {}, options: RestoreFlowOptions = {}) {
    const context = await setup(options);
    await loaded(context, none(overrides));
    expect(context.controller.state, 'precondition: idle').toBe('idle');
    return context;
}

/** An archive uploaded and its check started: `checking`, its first read due in `pollMs`, nothing announced so far. */
async function checking() {
    const context = await idle();
    context.api.upload.mockResolvedValueOnce(uploaded());
    context.api.startCheck.mockResolvedValueOnce(runningStage());
    void context.controller.upload(archive());
    await flush();
    expect(context.controller.state, 'precondition: the check runs').toBe('checking');
    context.onEvent.mockClear();
    return context;
}

/** The check ended with `answer`: `report`, nothing announced so far. */
async function reportShown(answer: RestoreStageReport = report()) {
    const context = await checking();
    context.api.getCheck.mockResolvedValueOnce(doneStage(answer));
    await vi.advanceTimersByTimeAsync(POLL_MS);
    expect(context.controller.state, 'precondition: the report is shown').toBe('report');
    context.onEvent.mockClear();
    return context;
}

/** A restore found pending at load. */
async function pendingRestore(overrides: StatusFields = {}, options: RestoreFlowOptions = {}) {
    const context = await setup(options);
    await loaded(context, pending(overrides));
    expect(context.controller.state, 'precondition: a restore is pending').toBe('pending');
    return context;
}

type Server = {state: 'up' | 'down'};

/** `probeServer()` answers what `server.state` holds, whenever it is asked. */
function serve(context: Context, initial: 'up' | 'down'): Server {
    const server: Server = {state: initial};
    context.api.probeServer.mockImplementation(() => Promise.resolve(server.state));
    return server;
}

/** A restore pending, its restart asked and accepted with `TICKET`: `outcome` waiting over a server the test flips, nothing announced so far. */
async function restartAccepted(initial: 'up' | 'down', options: RestoreFlowOptions = {}) {
    const context = await pendingRestore({}, options);
    const server = serve(context, initial);
    context.api.restart.mockResolvedValueOnce(accepted());
    void context.controller.restartNow();
    await flush();
    expect(context.controller.outcome, 'precondition: the restart was accepted').toBe('waiting');
    context.onEvent.mockClear();
    return {...context, server};
}

/** The restart seen happening: down for three pauses, then up for two. */
async function serverRestarts(server: Server): Promise<void> {
    server.state = 'down';
    await vi.advanceTimersByTimeAsync(3 * POLL_MS);
    server.state = 'up';
    await vi.advanceTimersByTimeAsync(2 * POLL_MS);
}

beforeAll(() => {
    assertEffectsRun();
});

beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(0);
    for (const fn of Object.values(zodios)) fn.mockReset();
});

afterEach(() => {
    for (const controller of controllers.splice(0)) controller.dispose();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    sessionStorage.clear();
});

// =====================================================================================================================
describe('the exports of §0 and §2b', () => {
    it('RESTORE_STAGE_STORAGE_KEY is librefolio.backup.restore.stage', async () => {
        const {RESTORE_STAGE_STORAGE_KEY} = await loadFlow();
        expect(RESTORE_STAGE_STORAGE_KEY).toBe(KEY);
    });

    it('AFTER_RESTORE_PATH is gone: a success leaves through restoreNavigation, to the plain sign-in page (§0.2, §0.6)', async () => {
        const module = (await loadFlow()) as unknown as Record<string, unknown>;
        expect(module).not.toHaveProperty('AFTER_RESTORE_PATH');
    });
});

describe('confirmationMatches — trimmed and lower-cased, nothing else (§0.4)', () => {
    it.each<[string, string, string]>([
        ['the word as shown', 'garden', 'garden'],
        ['spaces around it', '  garden ', 'garden'],
        ['a tab and a newline around it', '\tgarden\n', 'garden'],
        ['upper case', 'GARDEN', 'garden'],
        ['mixed case', 'GaRdEn', 'garden'],
        ['the word itself with spaces and capitals: both sides are normalized', 'garden', ' Garden '],
    ])('%s: %j matches %j', async (_case, typed, word) => {
        const {confirmationMatches} = await loadFlow();
        expect(confirmationMatches(typed, word)).toBe(true);
    });

    it.each<[string, string, string]>([
        ['nothing typed', '', 'garden'],
        ['only spaces typed', '   ', 'garden'],
        ['an empty word, nothing typed: the empty string never matches', '', ''],
        ['an empty word, spaces typed', '  ', ''],
        ['a word of spaces, nothing typed', '', '   '],
        ['an empty word, something typed', 'garden', ''],
        ['an accent the word does not have: no accent folding', 'gardén', 'garden'],
        ['the word without an accent it has', 'jardin', 'jardín'],
        ['a space inside the word: only the ends are trimmed', 'gar den', 'garden'],
        ['part of the word', 'garde', 'garden'],
        ['more than the word', 'gardens', 'garden'],
        ['another word', 'ribbon', 'garden'],
    ])('%s: %j does not match %j', async (_case, typed, word) => {
        const {confirmationMatches} = await loadFlow();
        expect(confirmationMatches(typed, word)).toBe(false);
    });
});

describe('confirmationWords — the words of the list a user can type (§0.4)', () => {
    it.each<[string, string, string[]]>([
        ['words separated by spaces, in their order', 'garden ribbon violet', ['garden', 'ribbon', 'violet']],
        ['spaces around and between them', '  garden   ribbon  ', ['garden', 'ribbon']],
        ['six and ten letters are kept', 'ribbon playground', ['ribbon', 'playground']],
        ['five and eleven letters are dropped', 'apple garden backgrounds', ['garden']],
        ['a capital is dropped, not lowered', 'Garden GARDENS ribbon', ['ribbon']],
        ['an accent is dropped', 'jardín ribbon cañada', ['ribbon']],
        ['a digit, a hyphen, an apostrophe or a comma is dropped', "garden1 well-being l'orange garden, ribbon", ['ribbon']],
        ['a duplicate is kept once, where it first came', 'garden ribbon garden violet ribbon', ['garden', 'ribbon', 'violet']],
        ['nothing', '', []],
        ['only spaces', '    ', []],
        ['nothing a user can type', 'Garden apple jardín', []],
    ])('%s', async (_case, text, expected) => {
        const {confirmationWords} = await loadFlow();
        expect(confirmationWords(text)).toEqual(expected);
    });
});

describe('pickConfirmationWord — words[Math.floor(random() × length)] (§0.4)', () => {
    const WORDS = ['garden', 'ribbon', 'violet', 'window'];

    it.each<[number, string]>([
        [0, 'garden'],
        [0.24, 'garden'],
        [0.25, 'ribbon'],
        [0.5, 'violet'],
        [0.74, 'violet'],
        [0.999, 'window'],
    ])('random() = %s → %s, random() asked once', async (value, expected) => {
        const {pickConfirmationWord} = await loadFlow();
        const random = vi.fn(() => value);
        expect(pickConfirmationWord(WORDS, random)).toBe(expected);
        expect(random).toHaveBeenCalledTimes(1);
    });

    it('random defaults to Math.random', async () => {
        const {pickConfirmationWord} = await loadFlow();
        const random = vi.spyOn(Math, 'random').mockReturnValue(0.8);
        expect(pickConfirmationWord(WORDS)).toBe('window');
        expect(random).toHaveBeenCalledTimes(1);
    });

    it('a list of one word: that word, whatever random() says', async () => {
        const {pickConfirmationWord} = await loadFlow();
        expect(pickConfirmationWord(['violet'], () => 0)).toBe('violet');
        expect(pickConfirmationWord(['violet'], () => 0.999)).toBe('violet');
    });

    it('an empty list falls back to the translation of backup.restore.confirm.word', async () => {
        const {pickConfirmationWord} = await loadFlow();
        expect(pickConfirmationWord([], () => 0.5)).toBe('⟦backup.restore.confirm.word⟧');
    });
});

// =====================================================================================================================
describe('load(): the status, then what it says', () => {
    it('loading and busy while the status is read; then idle, the status kept, nothing else read, nothing announced', async () => {
        const {controller, api, events} = await setup();
        const answer = deferred<RestoreStatus>();
        api.status.mockReturnValueOnce(answer.promise);

        const loading = controller.load();
        expect(controller.state).toBe('loading');
        expect(controller.busy).toBe(true);
        await flush();
        expect(api.status).toHaveBeenCalledTimes(1);

        answer.resolve(none());
        await loading;
        await flush();

        expect(controller.state).toBe('idle');
        expect(controller.busy).toBe(false);
        expect(controller.status).toEqual(none());
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(controller.stage).toBeNull();
        expect(controller.report).toBeNull();
        expect(controller.outcome).toBeNull();
        expect(controller.slow).toBe(false);
        expect(api.getCheck, 'no check was followed: none to read').not.toHaveBeenCalled();
        expect(events()).toEqual([]);
        expect(vi.getTimerCount(), 'idle reads nothing again').toBe(0);
    });

    it.each<[string, number | null]>([
        ['a limit', 500],
        ['no limit', 0],
        ['a limit that cannot be read', null],
    ])('limitMb is the upload_limit_mb of the status — %s: %s', async (_case, limit) => {
        const {controller} = await idle({upload_limit_mb: limit});
        expect(controller.limitMb).toBe(limit);
    });

    it.each<[string, RestoreStatus]>([['committed', committed()], ...REASONS.map((reason): [string, RestoreStatus] => [`rolled back, ${reason}`, rolledBack(reason)])])('the last restore %s: idle, its status kept for the card to read', async (_case, answer) => {
        const context = await setup();
        await loaded(context, answer);
        expect(context.controller.state).toBe('idle');
        expect(context.controller.busy).toBe(false);
        expect(context.controller.status).toEqual(answer);
        expect(context.controller.outcome, 'a last result read at load is not the outcome of a restart').toBeNull();
        expect(context.events()).toEqual([]);
    });

    it.each<[string, WaitingReason | null]>([['nothing', null], ...WAITINGS.map((waiting): [string, WaitingReason] => [waiting, waiting])])('a restore pending, waiting for %s: pending, not busy, the stored check not read (§0.5)', async (_case, waiting) => {
        const context = await setup({stored: OTHER_STAGE_ID});
        await loaded(context, pending({waiting}));
        expect(context.controller.state).toBe('pending');
        expect(context.controller.busy).toBe(false);
        expect(context.controller.status?.waiting ?? null).toBe(waiting);
        expect(context.controller.errorCode).toBeNull();
        expect(context.controller.outcome).toBeNull();
        expect(context.api.getCheck, 'a pending restore comes first: the check this tab followed is not read').not.toHaveBeenCalled();
        expect(context.events()).toEqual([]);
    });

    it('a restore being applied: in_progress, not busy, the stored check not read', async () => {
        const context = await setup({stored: OTHER_STAGE_ID});
        await loaded(context, inProgress());
        expect(context.controller.state).toBe('in_progress');
        expect(context.controller.busy).toBe(false);
        expect(context.api.getCheck).not.toHaveBeenCalled();
        expect(context.events()).toEqual([]);
    });

    it.each<[string, () => unknown, string]>([
        ['no answer', noAnswer, 'network'],
        ['an answer without a code', codelessAnswer, 'unexpected'],
    ])('a status read with %s: failed, failure status, not busy, the stored check kept and not read', async (_case, refused, code) => {
        const context = await setup({stored: STAGE_ID});
        context.api.status.mockRejectedValueOnce(refused());
        await context.controller.load();
        await flush();
        expect(context.controller.state).toBe('failed');
        expect(context.controller.errorCode).toBe(code);
        expect(context.controller.failure).toBe('status');
        expect(context.controller.busy).toBe(false);
        expect(context.api.getCheck).not.toHaveBeenCalled();
        expect(context.storage.items.get(KEY)).toBe(STAGE_ID);
    });
});

describe('retry(): from failed, the status read again', () => {
    it('loading with the error cleared while it reads; a failure the user retried is announced; then what the status says', async () => {
        const context = await setup();
        context.api.status.mockRejectedValueOnce(noAnswer());
        await context.controller.load();
        await flush();
        expect(context.controller.state, 'precondition: failed').toBe('failed');
        context.onEvent.mockClear();

        const answer = deferred<RestoreStatus>();
        context.api.status.mockReturnValueOnce(answer.promise);
        const retrying = context.controller.retry();
        await flush();
        expect(context.controller.state).toBe('loading');
        expect(context.controller.errorCode).toBeNull();
        expect(context.controller.failure).toBeNull();
        answer.reject(codelessAnswer());
        await retrying;
        await flush();
        expect(context.controller.state).toBe('failed');
        expect(context.controller.errorCode).toBe('unexpected');
        expect(context.events()).toEqual([['backup.restore.failed', {code: 'unexpected', what: 'status'}]]);

        context.api.status.mockResolvedValueOnce(none());
        await context.controller.retry();
        await flush();
        expect(context.controller.state).toBe('idle');
        expect(context.controller.errorCode).toBeNull();
        expect(context.api.status).toHaveBeenCalledTimes(3);
    });

    it.each<[string, () => Promise<Context>]>([
        ['idle', () => idle()],
        ['pending', () => pendingRestore()],
    ])('outside failed (%s) it reads nothing', async (_case, arrive) => {
        const context = await arrive();
        await context.controller.retry();
        await flush();
        expect(context.api.status).toHaveBeenCalledTimes(1);
    });
});

// =====================================================================================================================
describe('the check this tab followed, picked up after a reload (sessionStorage)', () => {
    it('still running: checking, read every pollMs, and its end shown as the report and announced (seen running here)', async () => {
        const context = await setup({stored: STAGE_ID});
        context.api.getCheck.mockResolvedValueOnce(runningStage({phase: 'unpacking', done_bytes: 1024, total_bytes: 4096})).mockResolvedValueOnce(doneStage());

        await loaded(context);

        expect(context.api.getCheck.mock.calls).toEqual([[STAGE_ID]]);
        expect(context.controller.state).toBe('checking');
        expect(context.controller.busy).toBe(true);
        expect(context.controller.stage?.phase).toBe('unpacking');
        expect(context.storage.items.get(KEY)).toBe(STAGE_ID);

        await vi.advanceTimersByTimeAsync(POLL_MS - 1);
        expect(context.api.getCheck, 'read again before pollMs').toHaveBeenCalledTimes(1);
        await vi.advanceTimersByTimeAsync(1);
        expect(context.api.getCheck).toHaveBeenCalledTimes(2);
        expect(context.controller.state).toBe('report');
        expect(context.controller.report).toEqual(report());
        expect(context.events()).toEqual([['backup.restore.staged', {stage_id: STAGE_ID, restorable: true, action: 'same'}]]);
    });

    it('already done: the report at once, the stage still remembered, never read again', async () => {
        const context = await setup({stored: STAGE_ID});
        context.api.getCheck.mockResolvedValueOnce(doneStage(report({action: 'upgrade'})));

        await loaded(context);

        expect(context.api.getCheck.mock.calls).toEqual([[STAGE_ID]]);
        expect(context.controller.state).toBe('report');
        expect(context.controller.busy).toBe(false);
        expect(context.controller.report).toEqual(report({action: 'upgrade'}));
        expect(context.storage.items.get(KEY), 'the report must survive another reload').toBe(STAGE_ID);
        await vi.advanceTimersByTimeAsync(20 * POLL_MS);
        expect(context.api.getCheck).toHaveBeenCalledTimes(1);
        expect(context.names()).not.toContain('backup.restore.failed');
    });

    it('gone from the server (404): forgotten silently — idle, no error, no event, the status kept', async () => {
        const context = await setup({stored: STAGE_ID});
        context.api.getCheck.mockRejectedValueOnce(refusal(404, 'restore_stage_not_found'));

        await loaded(context, rolledBack('swap_failed'));

        expect(context.controller.state).toBe('idle');
        expect(context.controller.errorCode).toBeNull();
        expect(context.controller.failure).toBeNull();
        expect(context.controller.stage).toBeNull();
        expect(context.controller.status).toEqual(rolledBack('swap_failed'));
        expect(context.storage.items.has(KEY)).toBe(false);
        expect(context.events()).toEqual([]);
    });

    it.each(['not_a_backup', 'archive_damaged', 'restore_interrupted'])('ended in failure (%s): failed with its code, failure check, forgotten', async (code) => {
        const context = await setup({stored: STAGE_ID});
        context.api.getCheck.mockResolvedValueOnce(failedStage(code));

        await loaded(context);

        expect(context.controller.state).toBe('failed');
        expect(context.controller.errorCode).toBe(code);
        expect(context.controller.failure).toBe('check');
        expect(context.controller.busy).toBe(false);
        expect(context.storage.items.has(KEY)).toBe(false);
    });

    it('no answer: failed, network, failure check, the stage kept; retry() picks it up again', async () => {
        const context = await setup({stored: STAGE_ID});
        context.api.getCheck.mockRejectedValueOnce(noAnswer()).mockResolvedValueOnce(doneStage());

        await loaded(context);

        expect(context.controller.state).toBe('failed');
        expect(context.controller.errorCode).toBe('network');
        expect(context.controller.failure).toBe('check');
        expect(context.storage.items.get(KEY), 'the check may still be there: kept for a retry').toBe(STAGE_ID);

        context.api.status.mockResolvedValueOnce(none());
        await context.controller.retry();
        await flush();

        expect(context.api.getCheck.mock.calls).toEqual([[STAGE_ID], [STAGE_ID]]);
        expect(context.controller.state).toBe('report');
    });
});

// =====================================================================================================================
describe('upload(): the size checked against upload_limit_mb before anything is sent', () => {
    it.each<[string, number, number]>([
        ['one byte over a limit of 1 MB (1024 × 1024 bytes, as the server counts)', 1, MIB + 1],
        ['600 MB over a limit of 500 MB', 500, 600 * MIB],
    ])('%s: refused at once as backup_too_large with the limit, nothing sent, announced', async (_case, limit, size) => {
        const {controller, api, storage, events} = await idle({upload_limit_mb: limit});

        await controller.upload(archive(size));
        await flush();

        expect(api.upload, 'a file over the limit was sent').not.toHaveBeenCalled();
        expect(api.startCheck).not.toHaveBeenCalled();
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('backup_too_large');
        expect(controller.errorLimitMb).toBe(limit);
        expect(controller.failure).toBe('upload');
        expect(controller.busy).toBe(false);
        expect(storage.setItem).not.toHaveBeenCalled();
        expect(events()).toEqual([['backup.restore.failed', {code: 'backup_too_large', what: 'upload'}]]);
    });

    it.each<[string, number | null, number]>([
        ['exactly the limit: the server refuses only what is larger', 1, MIB],
        ['no limit (0), an archive of 5 GB', 0, 5 * 1024 * MIB],
        ['a limit that cannot be read (null), an archive of 5 GB: the server decides', null, 5 * 1024 * MIB],
    ])('%s: sent', async (_case, limit, size) => {
        const {controller, api} = await idle({upload_limit_mb: limit});
        const file = archive(size);
        api.upload.mockResolvedValueOnce(uploaded({size}));
        api.startCheck.mockResolvedValueOnce(runningStage());

        void controller.upload(file);
        await flush();

        expect(api.upload).toHaveBeenCalledTimes(1);
        expect(api.upload.mock.calls[0][0], 'the File itself is sent').toBe(file);
        expect(controller.errorCode).toBeNull();
        expect(controller.errorLimitMb).toBeNull();
        expect(controller.state).toBe('checking');
    });

    it.each(['archive.tar', 'backup', 'BACKUP.ZIP', 'librefolio.zip.part'])('any file name is sent, the server recognises the archive: %s', async (name) => {
        const {controller, api} = await idle();
        api.upload.mockResolvedValueOnce(uploaded());
        api.startCheck.mockResolvedValueOnce(runningStage());

        void controller.upload(archive(4096, name));
        await flush();

        expect(api.upload).toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('checking');
    });

    it('a second upload() while the first is out is ignored: one PUT', async () => {
        const {controller, api} = await idle();
        const answer = deferred<RestoreUpload>();
        api.upload.mockReturnValueOnce(answer.promise);
        void controller.upload(archive());
        await flush();
        expect(controller.state, 'precondition: the upload is out').toBe('uploading');

        await controller.upload(archive(1024, 'another.zip'));
        await flush();

        expect(api.upload).toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('uploading');
    });
});

describe('upload(): the PUT, its progress, abortUpload()', () => {
    it('uploading and busy while the PUT is out; onProgress moves uploadedBytes and totalBytes; then the check, started with the upload id', async () => {
        const {controller, api, events} = await idle();
        const answer = deferred<RestoreUpload>();
        let options: UploadOptions | undefined;
        api.upload.mockImplementationOnce((_file, given) => {
            options = given;
            return answer.promise;
        });
        api.startCheck.mockResolvedValueOnce(runningStage());

        void controller.upload(archive(2048));
        await flush();

        expect(controller.state).toBe('uploading');
        expect(controller.busy).toBe(true);
        expect(controller.uploadedBytes).toBe(0);
        expect(options?.onProgress, 'the PUT was given no onProgress').toBeTypeOf('function');
        expect(options?.signal?.aborted, 'the PUT was given no AbortSignal: it could not be cancelled').toBe(false);

        options?.onProgress?.(512, 2048);
        expect(controller.uploadedBytes).toBe(512);
        expect(controller.totalBytes).toBe(2048);
        options?.onProgress?.(2048, 2048);
        expect(controller.uploadedBytes).toBe(2048);
        expect(controller.state, 'every byte sent is not the answer yet').toBe('uploading');
        expect(api.startCheck).not.toHaveBeenCalled();

        answer.resolve(uploaded({size: 2048}));
        await flush();

        expect(api.startCheck.mock.calls).toEqual([[UPLOAD_ID]]);
        expect(controller.state).toBe('checking');
        expect(events()).toEqual([['backup.restore.uploaded', {upload_id: UPLOAD_ID, size: 2048}]]);
    });

    it('abortUpload(): the PUT aborted, back to idle, nothing announced, no check started, nothing remembered', async () => {
        const {controller, api, storage, events} = await idle();
        api.status.mockResolvedValue(none());
        let signal: AbortSignal | undefined;
        api.upload.mockImplementationOnce((_file, options) => {
            signal = options?.signal;
            return new Promise<RestoreUpload>((_resolve, reject) => {
                signal?.addEventListener('abort', () => reject(canceled()));
            });
        });
        void controller.upload(archive());
        await flush();
        expect(controller.state, 'precondition: the upload is out').toBe('uploading');

        controller.abortUpload();
        await flush();

        expect(signal?.aborted, 'the PUT was not aborted').toBe(true);
        expect(controller.state).toBe('idle');
        expect(controller.busy).toBe(false);
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(api.startCheck).not.toHaveBeenCalled();
        expect(storage.setItem).not.toHaveBeenCalled();
        expect(events(), 'a cancel the user asked for is neither news nor a failure').toEqual([]);
    });

    it('an upload answered after abortUpload() is dropped: no check started, nothing announced', async () => {
        const {controller, api, events} = await idle();
        api.status.mockResolvedValue(none());
        const answer = deferred<RestoreUpload>();
        api.upload.mockReturnValueOnce(answer.promise);
        void controller.upload(archive());
        await flush();

        controller.abortUpload();
        answer.resolve(uploaded());
        await flush();

        expect(controller.state).toBe('idle');
        expect(api.startCheck, 'an upload the user cancelled was checked').not.toHaveBeenCalled();
        expect(events()).toEqual([]);
    });

    it('abortUpload() outside an upload does nothing: the check goes on', async () => {
        const {controller, api} = await checking();
        api.getCheck.mockResolvedValueOnce(runningStage({phase: 'verifying'}));

        controller.abortUpload();
        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(controller.state).toBe('checking');
        expect(api.dropCheck).not.toHaveBeenCalled();
        expect(api.getCheck).toHaveBeenCalledTimes(1);
    });
});

describe('upload(): a refused PUT, or a check that cannot start', () => {
    it.each<[string, () => unknown, string, number | null]>([
        ['400 backup_upload_empty', () => refusal(400, 'backup_upload_empty'), 'backup_upload_empty', null],
        ['400 backup_upload_incomplete', () => refusal(400, 'backup_upload_incomplete'), 'backup_upload_incomplete', null],
        ['413 backup_too_large, with the limit the server names', () => refusal(413, 'backup_too_large', {limit_mb: 250}), 'backup_too_large', 250],
        ['500 restore_folder_unusable', () => refusal(500, 'restore_folder_unusable'), 'restore_folder_unusable', null],
        ['500 backup_upload_failed', () => refusal(500, 'backup_upload_failed'), 'backup_upload_failed', null],
        ['503 backup_upload_unavailable', () => refusal(503, 'backup_upload_unavailable'), 'backup_upload_unavailable', null],
        ['507 backup_no_space', () => refusal(507, 'backup_no_space'), 'backup_no_space', null],
        ['no answer', noAnswer, 'network', null],
        ['an answer without a code', codelessAnswer, 'unexpected', null],
    ])('%s: failed (upload) with its code, announced once, no check started, nothing remembered', async (_case, refused, code, limit) => {
        const {controller, api, storage, events} = await idle({upload_limit_mb: null});
        api.upload.mockRejectedValueOnce(refused());

        await controller.upload(archive());
        await flush();

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('upload');
        expect(controller.errorLimitMb).toBe(limit);
        expect(controller.busy).toBe(false);
        expect(api.startCheck).not.toHaveBeenCalled();
        expect(storage.setItem).not.toHaveBeenCalled();
        expect(events()).toEqual([['backup.restore.failed', {code, what: 'upload'}]]);
    });

    it.each<[string, () => unknown, string]>([
        ['404 backup_upload_not_found', () => refusal(404, 'backup_upload_not_found'), 'backup_upload_not_found'],
        ['409 restore_busy: another archive is being checked', () => refusal(409, 'restore_busy'), 'restore_busy'],
        ['500 restore_folder_unusable', () => refusal(500, 'restore_folder_unusable'), 'restore_folder_unusable'],
        ['no answer', noAnswer, 'network'],
    ])('the check refused to start, %s: failed (check), the upload announced first, then the failure', async (_case, refused, code) => {
        const {controller, api, storage, events} = await idle();
        api.upload.mockResolvedValueOnce(uploaded());
        api.startCheck.mockRejectedValueOnce(refused());

        await controller.upload(archive());
        await flush();

        expect(api.startCheck.mock.calls).toEqual([[UPLOAD_ID]]);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('check');
        expect(storage.setItem, 'no check exists to remember').not.toHaveBeenCalled();
        expect(events()).toEqual([
            ['backup.restore.uploaded', {upload_id: UPLOAD_ID, size: 4096}],
            ['backup.restore.failed', {code, what: 'check'}],
        ]);
    });
});

// =====================================================================================================================
// B-30 — a check that cannot start: a full disk (507), its folders or its state unwritable (500) — guards
// =====================================================================================================================

/*
 * After B-30, `POST /backup/restore/stage` refuses on a full disk with 507 `no_space` (the check's own code), and on any
 * other failure to write the check's folders or state with 500 `stage_failed`, both before any check exists (B-30 brief
 * §1). No frontend change: the code is read off `detail.code` whatever the status, and restoreText.ts words both. These
 * guards pin what the flow does today with them — exactly what any check that cannot start does (the case above) — and
 * the sentence the card shows (`restoreErrorKey`, as RestoreCard.svelte resolves it). Green from the start.
 */
describe('B-30 — a check that cannot start on a full disk, or with its folders unwritable', () => {
    it.each<[string, number, string]>([
        ['507 no_space: not enough free space to check the archive', 507, 'no_space'],
        ['500 stage_failed: its folders or its state could not be written', 500, 'stage_failed'],
    ])('%s: failed (check) as any check that cannot start, worded by backup.restore.errors.<code>', async (_case, status, code) => {
        const {controller, api, storage, events} = await idle();
        api.upload.mockResolvedValueOnce(uploaded());
        api.startCheck.mockRejectedValueOnce(refusal(status, code));

        await controller.upload(archive());
        await flush();

        expect(api.startCheck.mock.calls).toEqual([[UPLOAD_ID]]);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('check');
        expect(controller.busy).toBe(false);
        expect(controller.stage, 'no check exists').toBeNull();
        expect(storage.setItem, 'no check exists to remember').not.toHaveBeenCalled();
        expect(events()).toEqual([
            ['backup.restore.uploaded', {upload_id: UPLOAD_ID, size: 4096}],
            ['backup.restore.failed', {code, what: 'check'}],
        ]);
        expect(restoreErrorKey(controller.errorCode), 'the sentence the card shows').toBe(`backup.restore.errors.${code}`);
    });
});

// =====================================================================================================================
// B-35 — an archive too large once unpacked; a restore limit the server cannot read (written red first)
// =====================================================================================================================

/*
 * After B-35 the check refuses an archive whose declared total, unpacked, is above the instance's cap: it ends `failed`
 * with `unpacked_too_large` (B-35 §2), as any check that fails. `POST /backup/restore/stage` answers 503
 * `backup_restore_unavailable` when that cap cannot be read (§3: no check started, the upload kept on the server), as
 * any check that cannot start. The flow is today's for each, pinned as the cases around pin it, and the sentence is the
 * one the card shows (`restoreErrorKey`, as RestoreCard.svelte resolves it).
 *
 * Red today: `restoreErrorKey` knows neither code and gives `backup.restore.errors.unexpected`.
 */
describe('B-35 — an archive too large once unpacked; a restore limit the server cannot read', () => {
    it('a check that fails with unpacked_too_large: failed (check) as any check that fails, forgotten, announced once, never read again, worded by backup.restore.errors.unpacked_too_large', async () => {
        const {controller, api, storage, events} = await checking();
        api.getCheck.mockResolvedValueOnce(failedStage('unpacked_too_large'));

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('unpacked_too_large');
        expect(controller.failure).toBe('check');
        expect(controller.busy).toBe(false);
        expect(storage.items.has(KEY), 'an ended check is forgotten').toBe(false);
        expect(events()).toEqual([['backup.restore.failed', {code: 'unpacked_too_large', what: 'check'}]]);
        await vi.advanceTimersByTimeAsync(20 * POLL_MS);
        expect(api.getCheck, 'an ended check was read again').toHaveBeenCalledTimes(1);
        expect(vi.getTimerCount()).toBe(0);
        expect(restoreErrorKey(controller.errorCode), 'the sentence the card shows').toBe('backup.restore.errors.unpacked_too_large');
    });

    it('the check refused to start — 503 backup_restore_unavailable: failed (check) as any check that cannot start, the upload announced first, worded by backup.restore.errors.backup_restore_unavailable', async () => {
        const {controller, api, storage, events} = await idle();
        api.upload.mockResolvedValueOnce(uploaded());
        api.startCheck.mockRejectedValueOnce(refusal(503, 'backup_restore_unavailable'));

        await controller.upload(archive());
        await flush();

        expect(api.startCheck.mock.calls).toEqual([[UPLOAD_ID]]);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('backup_restore_unavailable');
        expect(controller.failure).toBe('check');
        expect(controller.busy).toBe(false);
        expect(controller.stage, 'no check exists').toBeNull();
        expect(storage.setItem, 'no check exists to remember').not.toHaveBeenCalled();
        expect(events()).toEqual([
            ['backup.restore.uploaded', {upload_id: UPLOAD_ID, size: 4096}],
            ['backup.restore.failed', {code: 'backup_restore_unavailable', what: 'check'}],
        ]);
        expect(restoreErrorKey(controller.errorCode), 'the sentence the card shows').toBe('backup.restore.errors.backup_restore_unavailable');
    });
});

// =====================================================================================================================
describe('checking: the stage read every pollMs until it ends', () => {
    it('remembered, read every pollMs and not before, through its phases and bytes; done → the report, announced once, never read again', async () => {
        const {controller, api, storage, events} = await idle();
        api.upload.mockResolvedValueOnce(uploaded());
        api.startCheck.mockResolvedValueOnce(runningStage({phase: 'checking'}));
        api.getCheck.mockResolvedValueOnce(runningStage({phase: 'unpacking', done_bytes: 1024, total_bytes: 4096}));
        api.getCheck.mockResolvedValueOnce(runningStage({phase: 'upgrading', done_bytes: 4096, total_bytes: 4096}));
        api.getCheck.mockResolvedValueOnce(runningStage({phase: 'verifying', done_bytes: 4096, total_bytes: 4096}));
        api.getCheck.mockResolvedValueOnce(doneStage(report({action: 'upgrade'})));

        void controller.upload(archive());
        await flush();

        expect(controller.state).toBe('checking');
        expect(controller.busy).toBe(true);
        expect(controller.stage?.phase).toBe('checking');
        expect(controller.report, 'no report while the check runs').toBeNull();
        expect(storage.items.get(KEY), 'a reload must find the check again').toBe(STAGE_ID);

        await vi.advanceTimersByTimeAsync(POLL_MS - 1);
        expect(api.getCheck, 'the check was read before pollMs').not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(1);
        expect(api.getCheck.mock.calls).toEqual([[STAGE_ID]]);
        expect(controller.stage?.phase).toBe('unpacking');
        expect(controller.stage?.done_bytes).toBe(1024);
        expect(controller.stage?.total_bytes).toBe(4096);

        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(controller.stage?.phase).toBe('upgrading');
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(controller.stage?.phase).toBe('verifying');
        expect(controller.state).toBe('checking');

        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(api.getCheck).toHaveBeenCalledTimes(4);
        expect(controller.state).toBe('report');
        expect(controller.busy).toBe(false);
        expect(controller.report).toEqual(report({action: 'upgrade'}));
        expect(controller.errorCode).toBeNull();
        expect(storage.items.get(KEY), 'the report must survive a reload').toBe(STAGE_ID);
        expect(events()).toEqual([
            ['backup.restore.uploaded', {upload_id: UPLOAD_ID, size: 4096}],
            ['backup.restore.staged', {stage_id: STAGE_ID, restorable: true, action: 'upgrade'}],
        ]);

        await vi.advanceTimersByTimeAsync(20 * POLL_MS);
        expect(api.getCheck, 'an ended check was read again').toHaveBeenCalledTimes(4);
    });

    it('an archive that cannot be restored still ends in the report: staged with restorable false', async () => {
        const {controller, api, events} = await checking();
        api.getCheck.mockResolvedValueOnce(doneStage(report({restorable: false, blockers: ['no_administrator']})));

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(controller.state).toBe('report');
        expect(controller.report?.restorable).toBe(false);
        expect(events()).toEqual([['backup.restore.staged', {stage_id: STAGE_ID, restorable: false, action: 'same'}]]);
    });

    it.each(['not_a_backup', 'manifest_newer_format', 'checksum_mismatch', 'no_space', 'upgrade_failed', 'post_migration_failed'])('a check that fails (%s): failed (check) with its code, forgotten, announced once, never read again', async (code) => {
        const {controller, api, storage, events} = await checking();
        api.getCheck.mockResolvedValueOnce(failedStage(code));

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('check');
        expect(controller.busy).toBe(false);
        expect(storage.items.has(KEY)).toBe(false);
        expect(events()).toEqual([['backup.restore.failed', {code, what: 'check'}]]);
        await vi.advanceTimersByTimeAsync(20 * POLL_MS);
        expect(api.getCheck).toHaveBeenCalledTimes(1);
        expect(vi.getTimerCount()).toBe(0);
    });

    it('a check the server lost while it ran (404): failed (check) with restore_stage_not_found, forgotten, announced', async () => {
        const {controller, api, storage, events} = await checking();
        api.getCheck.mockRejectedValueOnce(refusal(404, 'restore_stage_not_found'));

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('restore_stage_not_found');
        expect(controller.failure).toBe('check');
        expect(storage.items.has(KEY)).toBe(false);
        expect(events()).toEqual([['backup.restore.failed', {code: 'restore_stage_not_found', what: 'check'}]]);
    });

    it('reads that get no answer: in the end failed (check) with network, announced once, the stage kept for a retry, no timer left', async () => {
        const {controller, api, storage, events} = await checking();
        api.getCheck.mockRejectedValue(noAnswer());

        await vi.advanceTimersByTimeAsync(30 * POLL_MS);

        expect(api.getCheck).toHaveBeenCalled();
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('network');
        expect(controller.failure).toBe('check');
        expect(storage.items.get(KEY)).toBe(STAGE_ID);
        expect(events()).toEqual([['backup.restore.failed', {code: 'network', what: 'check'}]]);
        expect(vi.getTimerCount(), 'the polling went on after it gave up').toBe(0);
    });
});

describe('dropCheck(): the check dropped from the server (§2c)', () => {
    it('from the report: DELETE /stage/{id}, then idle, nothing followed, cancelled {what: check}', async () => {
        const {controller, api, storage, events} = await reportShown();
        api.dropCheck.mockResolvedValueOnce(undefined);
        api.status.mockResolvedValue(none());

        await controller.dropCheck();
        await flush();

        expect(api.dropCheck.mock.calls).toEqual([[STAGE_ID]]);
        expect(controller.state).toBe('idle');
        expect(controller.busy).toBe(false);
        expect(controller.stage).toBeNull();
        expect(controller.report).toBeNull();
        expect(controller.errorCode).toBeNull();
        expect(storage.items.has(KEY)).toBe(false);
        expect(events()).toEqual([['backup.restore.cancelled', {what: 'check'}]]);
    });

    it('from the report, a check already gone (404): dropped all the same', async () => {
        const {controller, api, storage, events} = await reportShown();
        api.dropCheck.mockRejectedValueOnce(refusal(404, 'restore_stage_not_found'));
        api.status.mockResolvedValue(none());

        await controller.dropCheck();
        await flush();

        expect(controller.state).toBe('idle');
        expect(controller.errorCode).toBeNull();
        expect(storage.items.has(KEY)).toBe(false);
        expect(events()).toEqual([['backup.restore.cancelled', {what: 'check'}]]);
    });

    it.each<[string, () => RestoreStage]>([
        ['done', () => doneStage()],
        ['failed', () => failedStage('upgrade_failed')],
    ])('while the check runs: the 409 restore_stage_running keeps the polling going, and the check, once %s, is dropped by a second DELETE — no report, no failure', async (_case, ended) => {
        const {controller, api, storage, events} = await checking();
        api.dropCheck.mockRejectedValueOnce(refusal(409, 'restore_stage_running')).mockResolvedValueOnce(undefined);
        api.getCheck.mockResolvedValueOnce(runningStage({phase: 'verifying', done_bytes: 4096, total_bytes: 4096})).mockResolvedValueOnce(ended());
        api.status.mockResolvedValue(none());

        void controller.dropCheck();
        await flush();

        expect(api.dropCheck.mock.calls, 'the cancel sends its DELETE at once').toEqual([[STAGE_ID]]);
        expect(controller.state, 'a check that still runs is no failure').not.toBe('failed');
        expect(controller.busy, 'the check still runs: nothing else may start').toBe(true);
        expect(controller.errorCode).toBeNull();

        await vi.advanceTimersByTimeAsync(4 * POLL_MS);

        expect(api.getCheck, 'the polling went on until the check ended').toHaveBeenCalledTimes(2);
        expect(api.dropCheck.mock.calls, 'the ended check is dropped').toEqual([[STAGE_ID], [STAGE_ID]]);
        expect(controller.state).toBe('idle');
        expect(controller.stage).toBeNull();
        expect(controller.report).toBeNull();
        expect(controller.errorCode).toBeNull();
        expect(storage.items.has(KEY)).toBe(false);
        expect(events(), 'a check marked to drop opens no report and fails nothing').toEqual([['backup.restore.cancelled', {what: 'check'}]]);
        expect(vi.getTimerCount()).toBe(0);
    });

    it('while the check runs, a DELETE accepted at once (the check had just ended): idle, never read again', async () => {
        const {controller, api, storage, events} = await checking();
        api.dropCheck.mockResolvedValueOnce(undefined);
        api.status.mockResolvedValue(none());

        await controller.dropCheck();
        await flush();

        expect(controller.state).toBe('idle');
        expect(storage.items.has(KEY)).toBe(false);
        expect(events()).toEqual([['backup.restore.cancelled', {what: 'check'}]]);
        await vi.advanceTimersByTimeAsync(10 * POLL_MS);
        expect(api.getCheck, 'a dropped check was read again').not.toHaveBeenCalled();
    });

    it.each<[string, () => unknown, string]>([
        ['no answer', noAnswer, 'network'],
        ['409 restore_pending: a restore waits to apply this copy', () => refusal(409, 'restore_pending'), 'restore_pending'],
    ])('from the report, a DELETE refused — %s: failed (cancel), announced', async (_case, refused, code) => {
        const {controller, api, events} = await reportShown();
        api.dropCheck.mockRejectedValueOnce(refused());

        await controller.dropCheck();
        await flush();

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('cancel');
        expect(controller.busy).toBe(false);
        expect(events()).toEqual([['backup.restore.failed', {code, what: 'cancel'}]]);
    });

    it('from the report, a DELETE with no answer keeps the stage remembered: the check may still be there', async () => {
        const {controller, api, storage} = await reportShown();
        api.dropCheck.mockRejectedValueOnce(noAnswer());

        await controller.dropCheck();
        await flush();

        expect(storage.items.get(KEY)).toBe(STAGE_ID);
    });
});

// =====================================================================================================================
describe('confirm(): the restore confirmed, then the server restarted at once (§0.1)', () => {
    it('confirming while POST confirm is out; then POST restart at once, restarting; accepted: outcome waiting, confirmed then restart.requested', async () => {
        const {controller, api, storage, events} = await reportShown();
        const confirmation = deferred<RestoreStatus>();
        const restart = deferred<RestoreRestartAccepted>();
        api.confirm.mockReturnValueOnce(confirmation.promise);
        api.restart.mockReturnValueOnce(restart.promise);
        api.probeServer.mockResolvedValue('down');

        void controller.confirm();
        await flush();

        expect(api.confirm.mock.calls).toEqual([[STAGE_ID]]);
        expect(controller.state).toBe('confirming');
        expect(controller.busy).toBe(true);
        expect(api.restart, 'the restart waits for the confirmation').not.toHaveBeenCalled();

        confirmation.resolve(pending());
        await flush();

        expect(api.restart, 'no «Restart now» step: the restart follows the confirmation at once').toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('restarting');
        expect(controller.busy).toBe(true);
        expect(controller.status, 'the answer of the confirmation is the status').toEqual(pending());
        expect(storage.items.has(KEY), 'a confirmed check is no longer followed').toBe(false);
        expect(api.probeServer, 'the server is probed only once the restart is accepted').not.toHaveBeenCalled();

        restart.resolve(accepted());
        await flush();

        expect(controller.state).toBe('restarting');
        expect(controller.busy).toBe(true);
        expect(controller.outcome).toBe('waiting');
        expect(controller.slow).toBe(false);
        expect(controller.errorCode).toBeNull();
        expect(events()).toEqual([
            ['backup.restore.confirmed', {stage_id: STAGE_ID}],
            ['backup.restore.restart.requested', {}],
        ]);
    });

    it.each<[string, () => unknown, string]>([
        ['404 restore_stage_not_found', () => refusal(404, 'restore_stage_not_found'), 'restore_stage_not_found'],
        ['409 restore_stage_running', () => refusal(409, 'restore_stage_running'), 'restore_stage_running'],
        ['409 restore_not_restorable', () => refusal(409, 'restore_not_restorable'), 'restore_not_restorable'],
        ['409 restore_stage_outdated: LibreFolio was updated since the check', () => refusal(409, 'restore_stage_outdated'), 'restore_stage_outdated'],
        ['409 restore_already_pending', () => refusal(409, 'restore_already_pending'), 'restore_already_pending'],
        ['410 restore_stage_expired', () => refusal(410, 'restore_stage_expired'), 'restore_stage_expired'],
        ['500 restore_folder_unusable', () => refusal(500, 'restore_folder_unusable'), 'restore_folder_unusable'],
        ['no answer', noAnswer, 'network'],
    ])('a confirmation refused — %s: failed (confirm), announced, nothing restarted', async (_case, refused, code) => {
        const {controller, api, events} = await reportShown();
        api.confirm.mockRejectedValueOnce(refused());

        await controller.confirm();
        await flush();

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('confirm');
        expect(controller.busy).toBe(false);
        expect(controller.outcome).toBeNull();
        expect(api.restart, 'a restore that was not confirmed is not restarted').not.toHaveBeenCalled();
        expect(events()).toEqual([['backup.restore.failed', {code, what: 'confirm'}]]);
    });

    it.each<[string, () => unknown, string]>([
        ['no answer', noAnswer, 'network'],
        ['an answer without a code', codelessAnswer, 'unexpected'],
    ])('the restart refused after the confirmation — %s: pending with the error (failure restart), the restore still confirmed, nothing probed', async (_case, refused, code) => {
        const {controller, api, storage, events} = await reportShown();
        api.confirm.mockResolvedValueOnce(pending());
        api.restart.mockRejectedValueOnce(refused());

        await controller.confirm();
        await flush();
        await vi.advanceTimersByTimeAsync(10 * POLL_MS);

        expect(controller.state).toBe('pending');
        expect(controller.busy).toBe(false);
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('restart');
        expect(controller.status, 'the restore stays confirmed').toEqual(pending());
        expect(controller.outcome, 'no overlay for a restart that was refused').toBeNull();
        expect(storage.items.has(KEY)).toBe(false);
        expect(api.probeServer).not.toHaveBeenCalled();
        expect(events()).toEqual([
            ['backup.restore.confirmed', {stage_id: STAGE_ID}],
            ['backup.restore.failed', {code, what: 'restart'}],
        ]);
    });

    it('the restart refused after the confirmation with 409 restore_not_pending — the restore no longer exists: failed (restart), announced, outcome null, nothing probed (the decision of 11:47)', async () => {
        const {controller, api, storage, events} = await reportShown();
        api.confirm.mockResolvedValueOnce(pending());
        api.restart.mockRejectedValueOnce(refusal(409, 'restore_not_pending'));

        await controller.confirm();
        await flush();
        await vi.advanceTimersByTimeAsync(10 * POLL_MS);

        expect(api.status, 'the status is read again only when the user tries again (retry())').toHaveBeenCalledTimes(1);
        expect(controller.state, 'a restore that no longer exists must not be shown as pending').toBe('failed');
        expect(controller.busy).toBe(false);
        expect(controller.errorCode).toBe('restore_not_pending');
        expect(controller.failure).toBe('restart');
        expect(controller.outcome, 'no overlay for a restart that was refused').toBeNull();
        expect(storage.items.has(KEY), 'the confirmed check is no longer followed').toBe(false);
        expect(api.probeServer).not.toHaveBeenCalled();
        expect(events()).toEqual([
            ['backup.restore.confirmed', {stage_id: STAGE_ID}],
            ['backup.restore.failed', {code: 'restore_not_pending', what: 'restart'}],
        ]);
    });

    it('after a refused restart, restartNow() tries again: restarting with the error cleared, then waiting', async () => {
        const {controller, api} = await reportShown();
        api.confirm.mockResolvedValueOnce(pending());
        api.restart.mockRejectedValueOnce(noAnswer());
        await controller.confirm();
        await flush();
        expect(controller.failure, 'precondition: the restart was refused').toBe('restart');
        const restart = deferred<RestoreRestartAccepted>();
        api.restart.mockReturnValueOnce(restart.promise);
        api.probeServer.mockResolvedValue('down');

        void controller.restartNow();
        await flush();

        expect(api.restart).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('restarting');
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        restart.resolve(accepted());
        await flush();
        expect(controller.outcome).toBe('waiting');
    });

    it('after a refused restart, cancelPending() cancels the restore just confirmed: DELETE /pending, then the status read again, idle — and no DELETE /stage of its own: the server drops the checked copy with the cancel (B-17)', async () => {
        const {controller, api, events} = await reportShown();
        api.confirm.mockResolvedValueOnce(pending());
        api.restart.mockRejectedValueOnce(noAnswer());
        await controller.confirm();
        await flush();
        expect(controller.state, 'precondition: the restore stays confirmed after the refused restart').toBe('pending');
        api.cancelPending.mockResolvedValueOnce(undefined);
        api.status.mockResolvedValueOnce(none());

        await controller.cancelPending();
        await flush();

        expect(api.cancelPending).toHaveBeenCalledTimes(1);
        expect(api.status, 'the status is read again').toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('idle');
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(events()).toEqual([
            ['backup.restore.confirmed', {stage_id: STAGE_ID}],
            ['backup.restore.failed', {code: 'network', what: 'restart'}],
            ['backup.restore.cancelled', {what: 'pending'}],
        ]);
        expect(api.dropCheck, 'the copy of the confirmed check was dropped by the page: since B-17 the cancel drops it on the server').not.toHaveBeenCalled();
    });

    it.each<[string, () => Promise<Context>]>([
        ['an archive that cannot be restored', () => reportShown(report({restorable: false, blockers: ['no_administrator']}))],
        ['a check that still runs', () => checking()],
        ['nothing checked', () => idle()],
    ])('confirm() sends nothing for %s', async (_case, arrive) => {
        const context = await arrive();
        const state = context.controller.state;

        await context.controller.confirm();
        await flush();

        expect(context.api.confirm).not.toHaveBeenCalled();
        expect(context.api.restart).not.toHaveBeenCalled();
        expect(context.controller.state).toBe(state);
    });
});

describe('a restore found pending at load: restartNow() and cancelPending()', () => {
    it('restartNow(): restarting and busy while the POST is out; accepted: outcome waiting, restart.requested, the server probed every pollMs', async () => {
        const {controller, api, events} = await pendingRestore({waiting: 'server_running'});
        api.probeServer.mockResolvedValue('down');
        const answer = deferred<RestoreRestartAccepted>();
        api.restart.mockReturnValueOnce(answer.promise);

        void controller.restartNow();
        await flush();

        expect(api.restart).toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('restarting');
        expect(controller.busy).toBe(true);
        expect(api.probeServer, 'the server is probed only once the restart is accepted').not.toHaveBeenCalled();

        answer.resolve(accepted());
        await flush();

        expect(controller.state).toBe('restarting');
        expect(controller.outcome).toBe('waiting');
        expect(events()).toEqual([['backup.restore.restart.requested', {}]]);

        const probes = api.probeServer.mock.calls.length;
        await vi.advanceTimersByTimeAsync(5 * POLL_MS);
        expect(api.probeServer.mock.calls.length - probes, 'probed once per pollMs').toBe(5);
        expect(api.restoreOutcome, 'the server is down: nothing to read yet').not.toHaveBeenCalled();
    });

    it.each<[string, () => unknown, string]>([
        ['no answer', noAnswer, 'network'],
        ['an answer without a code', codelessAnswer, 'unexpected'],
    ])('restartNow() refused — %s: pending again with the error (failure restart), announced, nothing probed', async (_case, refused, code) => {
        const {controller, api, events} = await pendingRestore();
        api.restart.mockRejectedValueOnce(refused());

        await controller.restartNow();
        await flush();
        await vi.advanceTimersByTimeAsync(10 * POLL_MS);

        expect(controller.state).toBe('pending');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('restart');
        expect(controller.busy).toBe(false);
        expect(controller.outcome).toBeNull();
        expect(api.probeServer).not.toHaveBeenCalled();
        expect(events()).toEqual([['backup.restore.failed', {code, what: 'restart'}]]);
    });

    it('restartNow() refused with 409 restore_not_pending — cancelled from the command line meanwhile: failed (restart), announced, outcome null, nothing probed (the decision of 11:47)', async () => {
        const {controller, api, events} = await pendingRestore();
        api.restart.mockRejectedValueOnce(refusal(409, 'restore_not_pending'));

        await controller.restartNow();
        await flush();
        await vi.advanceTimersByTimeAsync(10 * POLL_MS);

        expect(api.status, 'the status is read again only when the user tries again (retry())').toHaveBeenCalledTimes(1);
        expect(controller.state, 'a restore that no longer exists must not be shown as pending').toBe('failed');
        expect(controller.errorCode).toBe('restore_not_pending');
        expect(controller.failure).toBe('restart');
        expect(controller.busy).toBe(false);
        expect(controller.outcome).toBeNull();
        expect(api.probeServer).not.toHaveBeenCalled();
        expect(events()).toEqual([['backup.restore.failed', {code: 'restore_not_pending', what: 'restart'}]]);
    });

    it('cancelPending(): cancelling and busy while DELETE /pending is out; accepted, the status read again: idle, cancelled {what: pending} once — and no DELETE /stage: the server drops the checked copy with the cancel, as backup pending --cancel does (B-17)', async () => {
        const {controller, api, events} = await pendingRestore();
        const answer = deferred<void>();
        api.cancelPending.mockReturnValueOnce(answer.promise);
        api.status.mockResolvedValueOnce(none());

        void controller.cancelPending();
        await flush();

        expect(api.cancelPending).toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('cancelling');
        expect(controller.busy).toBe(true);
        expect(api.status, 'the status is read again only once the cancel is accepted').toHaveBeenCalledTimes(1);
        expect(events()).toEqual([]);

        answer.resolve();
        await flush();

        expect(api.status, 'the status is read again').toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('idle');
        expect(controller.busy).toBe(false);
        expect(controller.status).toEqual(none());
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(events()).toEqual([['backup.restore.cancelled', {what: 'pending'}]]);
        expect(api.dropCheck, 'the copy of the cancelled restore was dropped by the page: since B-17 the cancel drops it on the server').not.toHaveBeenCalled();
    });

    it.each<[string, (api: Context['api']) => void]>([
        ['accepted', (api) => api.dropCheck.mockResolvedValue(undefined)],
        ['refused 404 restore_stage_not_found', (api) => api.dropCheck.mockRejectedValue(refusal(404, 'restore_stage_not_found'))],
        ['refused 409 restore_pending', (api) => api.dropCheck.mockRejectedValue(refusal(409, 'restore_pending'))],
        ['with no answer', (api) => api.dropCheck.mockRejectedValue(noAnswer())],
        ['with an answer without a code', (api) => api.dropCheck.mockRejectedValue(codelessAnswer())],
    ])('cancelPending() sends no DELETE /stage of its own — the fake would have answered it %s, leaving no trace in the state or the events: only its record tells (B-17)', async (_case, arm) => {
        const {controller, api, events} = await pendingRestore();
        arm(api);
        api.cancelPending.mockResolvedValueOnce(undefined);
        api.status.mockResolvedValueOnce(none());

        await controller.cancelPending();
        await flush();

        expect(api.cancelPending).toHaveBeenCalledTimes(1);
        expect(api.status, 'the status is read again').toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('idle');
        expect(controller.busy).toBe(false);
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(events()).toEqual([['backup.restore.cancelled', {what: 'pending'}]]);
        expect(api.dropCheck, 'the copy of the cancelled restore was dropped by the page: since B-17 the cancel drops it on the server').not.toHaveBeenCalled();
    });

    it.each<[string, () => RestoreStatus]>([
        ['null', () => pending({stage_id: null})],
        [
            'absent',
            () => {
                const status = pending();
                delete status.stage_id;
                return status;
            },
        ],
    ])('cancelPending(): a pending status whose stage_id is %s — DELETE /pending alone, as for any other, then the status read again, cancelled {what: pending}', async (_case, held) => {
        const context = await setup();
        await loaded(context, held());
        const {controller, api, events} = context;
        expect(controller.state, 'precondition: a restore is pending').toBe('pending');
        api.cancelPending.mockResolvedValueOnce(undefined);
        api.status.mockResolvedValueOnce(none());

        await controller.cancelPending();
        await flush();

        expect(api.cancelPending).toHaveBeenCalledTimes(1);
        expect(api.dropCheck, 'a copy was dropped by the page').not.toHaveBeenCalled();
        expect(api.status, 'the status is read again').toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('idle');
        expect(events()).toEqual([['backup.restore.cancelled', {what: 'pending'}]]);
    });

    it('cancelPending(): a restore no longer pending (404 restore_not_pending) is no failure: no copy dropped, the status read again shows what it became', async () => {
        const {controller, api, names} = await pendingRestore();
        api.cancelPending.mockRejectedValueOnce(refusal(404, 'restore_not_pending'));
        api.status.mockResolvedValueOnce(inProgress());

        await controller.cancelPending();
        await flush();

        expect(api.dropCheck, 'the copy of a restore a start may be applying was dropped').not.toHaveBeenCalled();
        expect(api.status).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('in_progress');
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(names()).not.toContain('backup.restore.failed');
    });

    it.each<[string, () => unknown, string]>([
        ['no answer', noAnswer, 'network'],
        ['an answer without a code', codelessAnswer, 'unexpected'],
        ['423 instance_blocked: the hosting provider blocked the instance, every restore route with it', () => refusal(423, 'instance_blocked'), 'instance_blocked'],
    ])('cancelPending() refused — %s: pending with the error (failure cancel), the restore still waiting, announced, no copy dropped (B-32 §1)', async (_case, refused, code) => {
        const {controller, api, events} = await pendingRestore();
        api.cancelPending.mockRejectedValueOnce(refused());

        await controller.cancelPending();
        await flush();

        expect(controller.state).toBe('pending');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('cancel');
        expect(controller.busy).toBe(false);
        expect(controller.status, 'the restore still waits').toEqual(pending());
        expect(api.status, 'the status is not read again').toHaveBeenCalledTimes(1);
        expect(api.dropCheck, 'the copy of a restore still pending was dropped').not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
        expect(events()).toEqual([['backup.restore.failed', {code, what: 'cancel'}]]);
    });
});

// =====================================================================================================================
// B-31 — a confirmation, a cancellation or a restart the server could not carry out (written red first)
// =====================================================================================================================

/*
 * After B-31 the server words three failures of its own (B-31 brief §1): the confirmation `restore_confirm_failed`
 * (500), the cancellation `restore_cancel_failed` (500) and the restart `restore_restart_failed` (500, answered
 * already today), each with its sentence in restoreText.ts; a confirmation on a full disk is 507 `backup_no_space`,
 * worded as for the upload. The flow each one ends is today's for a refusal of that request — pinned as the cases
 * above pin it —, and the sentence is the one the card shows (`restoreErrorKey`, as RestoreCard.svelte resolves it).
 *
 * Red today: `restoreErrorKey` knows none of the three codes and gives `backup.restore.errors.unexpected`. The case of
 * 507 `backup_no_space` is a guard, green today.
 *
 * B-32 (§1) changed the cancel's ending: a refused cancel leaves the restore `pending` with the error, as a refused
 * restart does. Its case below says so, for the server's own code and for no answer at all; red until B-32 lands.
 */
describe('B-31 — a confirmation, a cancellation or a restart the server could not carry out', () => {
    it.each<[string, number, string]>([
        ['500 restore_confirm_failed: the server could not confirm it', 500, 'restore_confirm_failed'],
        ['507 backup_no_space: not enough free space to confirm it (green today: the guard)', 507, 'backup_no_space'],
    ])('a confirmation refused — %s: failed (confirm) as any refused confirmation, nothing restarted, worded by backup.restore.errors.<code>', async (_case, status, code) => {
        const {controller, api, events} = await reportShown();
        api.confirm.mockRejectedValueOnce(refusal(status, code));

        await controller.confirm();
        await flush();

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('confirm');
        expect(controller.busy).toBe(false);
        expect(controller.outcome).toBeNull();
        expect(api.restart, 'a restore that was not confirmed is not restarted').not.toHaveBeenCalled();
        expect(events()).toEqual([['backup.restore.failed', {code, what: 'confirm'}]]);
        expect(restoreErrorKey(controller.errorCode), 'the sentence the card shows').toBe(`backup.restore.errors.${code}`);
    });

    it.each<[string, () => unknown, string]>([
        ['500 restore_cancel_failed', () => refusal(500, 'restore_cancel_failed'), 'restore_cancel_failed'],
        ['no answer', noAnswer, 'network'],
    ])('cancelPending() refused — %s: pending with the error (failure cancel), the restore still waiting, no copy dropped, no status read, worded by backup.restore.errors.<code> (B-32 §1)', async (_case, refused, code) => {
        const {controller, api, events} = await pendingRestore();
        api.cancelPending.mockRejectedValueOnce(refused());

        await controller.cancelPending();
        await flush();

        expect(controller.state, 'the restore still waits: the pending block, with the error').toBe('pending');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('cancel');
        expect(controller.busy).toBe(false);
        expect(controller.status, 'the status held is still the pending one').toEqual(pending());
        expect(api.status, 'the status is not read again').toHaveBeenCalledTimes(1);
        expect(api.dropCheck, 'the copy of a restore still pending was dropped').not.toHaveBeenCalled();
        expect(vi.getTimerCount(), 'nothing scheduled').toBe(0);
        expect(events()).toEqual([['backup.restore.failed', {code, what: 'cancel'}]]);
        expect(restoreErrorKey(controller.errorCode), 'the sentence the card shows').toBe(`backup.restore.errors.${code}`);
    });

    it('the restart refused after the confirmation — 500 restore_restart_failed: pending with the error (failure restart), the restore still confirmed, nothing probed, worded by backup.restore.errors.restore_restart_failed', async () => {
        const {controller, api, storage, events} = await reportShown();
        api.confirm.mockResolvedValueOnce(pending());
        api.restart.mockRejectedValueOnce(refusal(500, 'restore_restart_failed'));

        await controller.confirm();
        await flush();
        await vi.advanceTimersByTimeAsync(10 * POLL_MS);

        expect(controller.state).toBe('pending');
        expect(controller.busy).toBe(false);
        expect(controller.errorCode).toBe('restore_restart_failed');
        expect(controller.failure).toBe('restart');
        expect(controller.status, 'the restore stays confirmed').toEqual(pending());
        expect(controller.outcome, 'no overlay for a restart that was refused').toBeNull();
        expect(storage.items.has(KEY)).toBe(false);
        expect(api.probeServer).not.toHaveBeenCalled();
        expect(events()).toEqual([
            ['backup.restore.confirmed', {stage_id: STAGE_ID}],
            ['backup.restore.failed', {code: 'restore_restart_failed', what: 'restart'}],
        ]);
        expect(restoreErrorKey(controller.errorCode), 'the sentence the card shows').toBe('backup.restore.errors.restore_restart_failed');
    });
});

// =====================================================================================================================
// B-32 — after a refused cancel, the restore still waits; a state the server cannot read (written red first)
// =====================================================================================================================

/*
 * B-32 §1: a refused cancel of a pending restore leaves the controller `pending` with the error (the cases above), so
 * the card's pending block stays and its two actions work again: `cancelPending()` once more, and `restartNow()`.
 * §3 and §4: `GET /backup/restore/status` answers 500 `restore_state_unreadable` when the server cannot read the state
 * of the restore; `load()` takes it as any status read that fails (`failed`, failure `status`), worded by its own
 * sentence. Red today: a refused cancel ends `failed`, where neither action does anything; `restoreErrorKey` does not
 * know `restore_state_unreadable` and gives `backup.restore.errors.unexpected`.
 */

/** A restore found pending at load, whose cancel the server refused with 500 `restore_cancel_failed`: still pending, with the error. */
async function cancelRefused() {
    const context = await pendingRestore();
    context.api.cancelPending.mockRejectedValueOnce(refusal(500, 'restore_cancel_failed'));
    await context.controller.cancelPending();
    await flush();
    expect(context.controller.state, 'precondition: a refused cancel leaves the restore pending (B-32 §1)').toBe('pending');
    expect(context.controller.errorCode).toBe('restore_cancel_failed');
    context.onEvent.mockClear();
    return context;
}

describe('B-32 — after a refused cancel, the pending restore can be cancelled again or restarted', () => {
    it('cancelPending() again, accepted: the status read again, idle, the error cleared, cancelled {what: pending} once, no copy dropped', async () => {
        const {controller, api, events} = await cancelRefused();
        api.cancelPending.mockResolvedValueOnce(undefined);
        api.status.mockResolvedValueOnce(none());

        await controller.cancelPending();
        await flush();

        expect(api.cancelPending, 'the second DELETE /pending').toHaveBeenCalledTimes(2);
        expect(api.status, 'the status read again').toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('idle');
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(api.dropCheck, 'the server drops the copy with the cancel (B-17)').not.toHaveBeenCalled();
        expect(events()).toEqual([['backup.restore.cancelled', {what: 'pending'}]]);
    });

    it('restartNow(): the restart requested — restarting, the error cleared, waiting, restart.requested', async () => {
        const context = await cancelRefused();
        const {controller, api, events} = context;
        serve(context, 'down');
        api.restart.mockResolvedValueOnce(accepted());

        void controller.restartNow();
        await flush();

        expect(api.restart).toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('restarting');
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(controller.outcome).toBe('waiting');
        expect(events()).toEqual([['backup.restore.restart.requested', {}]]);
    });
});

describe('B-32 — a state of the restore the server cannot read', () => {
    it('load() refused with 500 restore_state_unreadable: failed, failure status, not busy, worded by backup.restore.errors.restore_state_unreadable', async () => {
        const context = await setup();
        context.api.status.mockRejectedValueOnce(refusal(500, 'restore_state_unreadable'));

        await context.controller.load();
        await flush();

        expect(context.controller.state).toBe('failed');
        expect(context.controller.errorCode).toBe('restore_state_unreadable');
        expect(context.controller.failure).toBe('status');
        expect(context.controller.busy).toBe(false);
        expect(restoreErrorKey(context.controller.errorCode), 'the sentence the card shows').toBe('backup.restore.errors.restore_state_unreadable');
    });
});

// =====================================================================================================================
describe('the restart: the server probed until the outcome is known (§0.2, §0.3)', () => {
    it('seen down, then up: the outcome read once — signed out is restored: no message, toSignIn() once, restored announced, nothing probed after', async () => {
        const {controller, api, server, events, toSignIn} = await restartAccepted('down');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'signed_out'});

        await vi.advanceTimersByTimeAsync(5 * POLL_MS);
        expect(api.probeServer).toHaveBeenCalled();
        expect(api.restoreOutcome, 'the server is down: nothing to read yet').not.toHaveBeenCalled();
        expect(controller.outcome).toBe('waiting');
        expect(toSignIn).not.toHaveBeenCalled();

        server.state = 'up';
        await vi.advanceTimersByTimeAsync(2 * POLL_MS);

        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(controller.outcome).toBe('restored');
        expect(controller.outcomeStatus).toBeNull();
        expect(toSignIn, 'a success goes straight to the sign-in page').toHaveBeenCalledTimes(1);
        expect(events()).toEqual([['backup.restore.restored', {}]]);

        const probes = api.probeServer.mock.calls.length;
        await vi.advanceTimersByTimeAsync(20 * POLL_MS);
        expect(api.probeServer.mock.calls.length, 'the server was probed after the outcome').toBe(probes);
        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(toSignIn).toHaveBeenCalledTimes(1);
        expect(vi.getTimerCount(), 'a timer outlived the outcome').toBe(0);
    });

    it('seen down, then up, the status committed: restored as well — toSignIn() once', async () => {
        const {controller, api, server, events, toSignIn} = await restartAccepted('down');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: committed()});

        await serverRestarts(server);

        expect(controller.outcome).toBe('restored');
        expect(toSignIn).toHaveBeenCalledTimes(1);
        expect(events()).toEqual([['backup.restore.restored', {}]]);
    });

    it.each(REASONS)('seen down, then up, the restore rolled back (%s): rolled_back, its status kept, announced with the reason, no sign-in', async (reason) => {
        const {controller, api, server, events, toSignIn} = await restartAccepted('down');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: rolledBack(reason)});

        await serverRestarts(server);

        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(controller.outcome).toBe('rolled_back');
        expect(controller.outcomeStatus).toEqual(rolledBack(reason));
        expect(toSignIn, 'a restore that did not go through stays on the same screen').not.toHaveBeenCalled();
        expect(events()).toEqual([['backup.restore.rolled_back', {reason}]]);
        expect(vi.getTimerCount()).toBe(0);
    });

    it.each(WAITINGS)('seen down, then up, the restore still pending (%s): still_pending with its waiting, nothing announced, no sign-in', async (waiting) => {
        const {controller, api, server, events, toSignIn} = await restartAccepted('down');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: pending({waiting})});

        await serverRestarts(server);

        expect(controller.outcome).toBe('still_pending');
        expect(controller.outcomeStatus?.waiting).toBe(waiting);
        expect(toSignIn).not.toHaveBeenCalled();
        expect(events()).toEqual([]);
        expect(vi.getTimerCount()).toBe(0);
    });

    it('seen down, then up, the status refused because the hosting provider blocked the instance (blocked, P8): still_pending, waiting for the unblock (P7), nothing announced, no sign-in, nothing probed after', async () => {
        const {controller, api, server, events, toSignIn} = await restartAccepted('down');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'blocked'});

        await serverRestarts(server);

        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(controller.outcome, 'a restart that came back on a blocked instance is a failure on the same screen').toBe('still_pending');
        expect(controller.outcomeStatus, 'the status route is refused too: the page builds the status, and only that').toStrictEqual({state: 'pending', waiting: 'instance_blocked'});
        expect(toSignIn, 'a restore that did not go through stays on the same screen').not.toHaveBeenCalled();
        expect(events(), 'still_pending is announced by nobody (§0.3)').toEqual([]);

        const probes = api.probeServer.mock.calls.length;
        await vi.advanceTimersByTimeAsync(20 * POLL_MS);
        expect(api.probeServer.mock.calls.length, 'the server was probed after the outcome').toBe(probes);
        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(vi.getTimerCount(), 'a timer outlived the outcome').toBe(0);
    });

    it('up all along: the outcome is not read before fastRestartMs, then read anyway — signed out: restored', async () => {
        const {controller, api, toSignIn} = await restartAccepted('up');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'signed_out'});

        await vi.advanceTimersByTimeAsync(FAST_MS - 1);
        expect(api.probeServer).toHaveBeenCalled();
        expect(api.restoreOutcome, 'read before fastRestartMs').not.toHaveBeenCalled();
        expect(controller.outcome).toBe('waiting');

        await vi.advanceTimersByTimeAsync(2 * POLL_MS + 1);
        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(controller.outcome).toBe('restored');
        expect(toSignIn).toHaveBeenCalledTimes(1);
    });

    it('up all along, the restore still pending at the fast read: keep waiting and probing; a later down then up gives the outcome', async () => {
        const {controller, api, server, events, toSignIn} = await restartAccepted('up');
        api.restoreOutcome.mockResolvedValue({kind: 'status', status: pending()});

        await vi.advanceTimersByTimeAsync(FAST_MS + 2 * POLL_MS);
        expect(api.restoreOutcome, 'precondition: the outcome was read anyway').toHaveBeenCalled();
        expect(controller.outcome, 'pending at a fast read is not still_pending: the start may not have happened yet').toBe('waiting');
        const probes = api.probeServer.mock.calls.length;
        await vi.advanceTimersByTimeAsync(5 * POLL_MS);
        expect(api.probeServer.mock.calls.length, 'the probing stopped').toBeGreaterThan(probes);
        expect(controller.outcome).toBe('waiting');

        api.restoreOutcome.mockResolvedValue({kind: 'signed_out'});
        await serverRestarts(server);

        expect(controller.outcome).toBe('restored');
        expect(toSignIn).toHaveBeenCalledTimes(1);
        expect(events()).toEqual([['backup.restore.restored', {}]]);
    });

    it('up all along, the restore rolled back meanwhile: rolled_back with its reason at the fast read', async () => {
        const {controller, api, toSignIn} = await restartAccepted('up');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: rolledBack('first_start_failed')});

        await vi.advanceTimersByTimeAsync(FAST_MS + 2 * POLL_MS);

        expect(controller.outcome).toBe('rolled_back');
        expect(controller.outcomeStatus?.reason).toBe('first_start_failed');
        expect(toSignIn).not.toHaveBeenCalled();
    });

    it('up all along, the status refused at the fast read because the hosting provider blocked the instance (blocked): still_pending at once, waiting for the unblock, nothing announced, no sign-in, nothing probed after', async () => {
        const {controller, api, events, toSignIn} = await restartAccepted('up');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'blocked'});

        await vi.advanceTimersByTimeAsync(FAST_MS - 1);
        expect(api.restoreOutcome, 'read before fastRestartMs').not.toHaveBeenCalled();
        expect(controller.outcome).toBe('waiting');

        await vi.advanceTimersByTimeAsync(2 * POLL_MS + 1);

        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(controller.outcome, 'blocked at the fast read is already the outcome: no start applies a restore while the instance is blocked (P7)').toBe('still_pending');
        expect(controller.outcomeStatus).toStrictEqual({state: 'pending', waiting: 'instance_blocked'});
        expect(toSignIn).not.toHaveBeenCalled();
        expect(events()).toEqual([]);

        const probes = api.probeServer.mock.calls.length;
        await vi.advanceTimersByTimeAsync(20 * POLL_MS);
        expect(api.probeServer.mock.calls.length, 'the server was probed after the outcome').toBe(probes);
        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(vi.getTimerCount(), 'a timer outlived the outcome').toBe(0);
    });

    it('down all along: slow only after slowAfterMs, the probing goes on, and the outcome still comes when the server is back', async () => {
        const {controller, api, server} = await restartAccepted('down');

        await vi.advanceTimersByTimeAsync(SLOW_MS - 1);
        expect(controller.slow).toBe(false);
        expect(controller.outcome).toBe('waiting');
        await vi.advanceTimersByTimeAsync(2 * POLL_MS + 1);
        expect(controller.slow).toBe(true);
        expect(controller.outcome).toBe('waiting');

        const probes = api.probeServer.mock.calls.length;
        await vi.advanceTimersByTimeAsync(5 * POLL_MS);
        expect(api.probeServer.mock.calls.length, 'the probing stopped once slow').toBeGreaterThan(probes);
        expect(api.restoreOutcome).not.toHaveBeenCalled();

        api.restoreOutcome.mockResolvedValueOnce({kind: 'signed_out'});
        server.state = 'up';
        await vi.advanceTimersByTimeAsync(2 * POLL_MS);
        expect(controller.outcome).toBe('restored');
    });

    it.each<[string, RestoreOutcomeAnswer, RestartOutcome, RestoreStatus]>([
        ['rolled_back', {kind: 'status', status: rolledBack('swap_interrupted')}, 'rolled_back', rolledBack('swap_interrupted')],
        ['still_pending', {kind: 'status', status: pending({waiting: 'instance_blocked'})}, 'still_pending', pending({waiting: 'instance_blocked'})],
        ['still_pending, the status refused on a blocked instance (blocked)', {kind: 'blocked'}, 'still_pending', pending({waiting: 'instance_blocked'})],
    ])('back to the tab after %s: load() clears the outcome and slow, and shows what the status says', async (_case, answer, outcome, status) => {
        const {controller, api, server} = await restartAccepted('down');
        api.restoreOutcome.mockResolvedValueOnce(answer);
        await vi.advanceTimersByTimeAsync(SLOW_MS + 2 * POLL_MS);
        server.state = 'up';
        await vi.advanceTimersByTimeAsync(2 * POLL_MS);
        expect(controller.outcome, 'precondition: the outcome is known').toBe(outcome);

        api.status.mockResolvedValueOnce(status);
        await controller.load();
        await flush();

        expect(controller.outcome).toBeNull();
        expect(controller.slow).toBe(false);
        expect(controller.state).toBe(status.state === 'pending' ? 'pending' : 'idle');
    });
});

// =====================================================================================================================
// B-16 — a server that never stops: notStopping (written red first)
// =====================================================================================================================

/*
 * After «Restore and restart», a server that never goes down (a lost signal, a process that does not exit) leaves the
 * restore pending: the page reads the outcome after `fastRestartMs`, finds it pending, and keeps probing, while `slow`
 * fires only for a server seen DOWN. B-16 (brief §1): `notStopping`, true once a probe finds the server UP while the
 * restart is followed, the server never seen down since the restart was asked, and at least `slowAfterMs` elapsed since
 * then — counted from the restart, not from the fast read; cleared by `load()`, by a new restart, by every outcome that
 * settles, and by a probe that finds the server down. The probing goes on while it holds, a late stop proceeds as
 * today, and `slow` and `notStopping` are never both true.
 *
 * This file's timings: `pollMs` 200, `fastRestartMs` 3 000, `slowAfterMs` 6 000. The restart is accepted at once, at 0,
 * so «since the restart was asked» and «since its request» are one instant here. The pinned case «up all along, the
 * restore still pending at the fast read» above stays as it is: its server goes down before `slowAfterMs`.
 *
 * Red today: the controller publishes no `notStopping`, and every case fails on the helper below, which names it.
 */

/** `notStopping` (B-16 §1), or a failure that names it while the controller publishes none. */
function notStoppingOf(controller: RestoreFlowController): boolean {
    const value = (controller as unknown as {notStopping?: unknown}).notStopping;
    expect(typeof value, 'restoreFlow.svelte.ts: the controller publishes no notStopping (B-16 §1)').toBe('boolean');
    return value as boolean;
}

/** A restart accepted at 0 over a server up all along, the restore pending at every read, followed until `notStopping` holds. */
async function notStoppingShown() {
    const context = await restartAccepted('up');
    context.api.restoreOutcome.mockResolvedValue({kind: 'status', status: pending()});
    await vi.advanceTimersByTimeAsync(SLOW_MS + 2 * POLL_MS);
    expect(notStoppingOf(context.controller), 'precondition: the server never stopped').toBe(true);
    return context;
}

describe('B-16 — a server that never stops: notStopping', () => {
    it('up all along, the restore pending at every read: false until slowAfterMs after the restart, true after — counted from the restart, not from the fast read —; outcome still waiting, the probing and the reads go on', async () => {
        const {controller, api} = await restartAccepted('up');
        api.restoreOutcome.mockResolvedValue({kind: 'status', status: pending()});

        await vi.advanceTimersByTimeAsync(SLOW_MS - 1);
        expect(api.restoreOutcome, 'precondition: read since fastRestartMs, pending').toHaveBeenCalled();
        expect(notStoppingOf(controller), 'not before slowAfterMs after the restart').toBe(false);
        expect(controller.outcome).toBe('waiting');

        await vi.advanceTimersByTimeAsync(2 * POLL_MS + 1);
        expect(notStoppingOf(controller), 'slowAfterMs after the restart, never seen down: the server has not stopped').toBe(true);
        expect(controller.outcome, 'still waiting: a late stop may come yet').toBe('waiting');
        expect(controller.state).toBe('restarting');
        expect(controller.slow, 'never seen down: not slow').toBe(false);

        const probes = api.probeServer.mock.calls.length;
        const reads = api.restoreOutcome.mock.calls.length;
        await vi.advanceTimersByTimeAsync(5 * POLL_MS);
        expect(api.probeServer.mock.calls.length, 'the probing goes on').toBeGreaterThan(probes);
        expect(api.restoreOutcome.mock.calls.length, 'and so do the reads of the outcome').toBeGreaterThan(reads);
        expect(notStoppingOf(controller)).toBe(true);
        expect(controller.outcome).toBe('waiting');
    });

    it('then the server goes down: false at once, slow only slowAfterMs after it went down (as today), never both; then up, signed out: restored, toSignIn() once — the late stop proceeds as today', async () => {
        const {controller, api, server, events, toSignIn} = await notStoppingShown();

        server.state = 'down';
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(notStoppingOf(controller), 'seen down: the server is stopping after all').toBe(false);
        expect(controller.slow, 'just gone down: not slow yet').toBe(false);
        expect(controller.outcome).toBe('waiting');

        await vi.advanceTimersByTimeAsync(SLOW_MS - 1);
        expect(controller.slow, 'not before slowAfterMs down').toBe(false);
        expect(notStoppingOf(controller)).toBe(false);
        await vi.advanceTimersByTimeAsync(2 * POLL_MS + 1);
        expect(controller.slow, 'slowAfterMs down: slow, as today').toBe(true);
        expect(notStoppingOf(controller), 'never both').toBe(false);

        api.restoreOutcome.mockResolvedValue({kind: 'signed_out'});
        server.state = 'up';
        await vi.advanceTimersByTimeAsync(2 * POLL_MS);

        expect(controller.outcome).toBe('restored');
        expect(toSignIn).toHaveBeenCalledTimes(1);
        expect(events()).toEqual([['backup.restore.restored', {}]]);
        expect(notStoppingOf(controller)).toBe(false);
        expect(controller.slow).toBe(false);
    });

    it.each<[string, RestoreOutcomeAnswer, RestartOutcome]>([
        ['signed out: restored', {kind: 'signed_out'}, 'restored'],
        ['committed: restored', {kind: 'status', status: committed()}, 'restored'],
        ['rolled back', {kind: 'status', status: rolledBack('first_start_failed')}, 'rolled_back'],
        ['blocked: still_pending', {kind: 'blocked'}, 'still_pending'],
    ])('a read that settles the outcome while the server never stopped (%s): false', async (_case, answer, outcome) => {
        const {controller, api} = await notStoppingShown();
        api.restoreOutcome.mockResolvedValue(answer);

        await vi.advanceTimersByTimeAsync(2 * POLL_MS);

        expect(controller.outcome, 'precondition: the outcome is known').toBe(outcome);
        expect(notStoppingOf(controller), 'an outcome known: nothing left to say of the stop').toBe(false);
    });

    it('load() clears it, and nothing is probed after it', async () => {
        const {controller, api} = await notStoppingShown();
        api.status.mockResolvedValueOnce(pending());

        await controller.load();
        await flush();

        expect(notStoppingOf(controller)).toBe(false);
        expect(controller.state, 'back to the tab: the restore still waits').toBe('pending');
        expect(controller.outcome).toBeNull();
        const probes = api.probeServer.mock.calls.length;
        const reads = api.restoreOutcome.mock.calls.length;
        await vi.advanceTimersByTimeAsync(20 * POLL_MS);
        expect(api.probeServer.mock.calls.length, 'a probe of the restart load() ended').toBe(probes);
        expect(api.restoreOutcome.mock.calls.length).toBe(reads);
        expect(notStoppingOf(controller)).toBe(false);
    });

    it('restartNow() after load(): starts with it false, and counts slowAfterMs from its own restart', async () => {
        const {controller, api} = await notStoppingShown();
        api.status.mockResolvedValueOnce(pending());
        await controller.load();
        await flush();
        expect(controller.state, 'precondition: the restore waits').toBe('pending');

        api.restart.mockResolvedValueOnce(accepted(OTHER_TICKET));
        void controller.restartNow();
        await flush();
        expect(controller.outcome, 'precondition: the new restart was accepted').toBe('waiting');
        expect(notStoppingOf(controller), 'a new restart starts afresh').toBe(false);

        await vi.advanceTimersByTimeAsync(SLOW_MS - 1);
        expect(notStoppingOf(controller), 'not before slowAfterMs after this restart').toBe(false);
        await vi.advanceTimersByTimeAsync(2 * POLL_MS + 1);
        expect(notStoppingOf(controller), 'slowAfterMs after this restart').toBe(true);
    });

    it('never once the server was seen down: down past slowAfterMs, then up with the restore pending — still_pending as today, false all along', async () => {
        const {controller, api, server} = await restartAccepted('down');

        await vi.advanceTimersByTimeAsync(SLOW_MS + 2 * POLL_MS);
        expect(controller.slow, 'precondition: down for slowAfterMs').toBe(true);
        expect(notStoppingOf(controller)).toBe(false);

        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: pending()});
        server.state = 'up';
        await vi.advanceTimersByTimeAsync(2 * POLL_MS);

        expect(controller.outcome, 'pending after a stop seen: not applied, as today').toBe('still_pending');
        expect(notStoppingOf(controller)).toBe(false);
        expect(controller.slow).toBe(false);
    });

    it('never once the server was seen down, even up long after: seen down at once, then up with a start applying the restore at every read — the probing goes on, false past slowAfterMs', async () => {
        const {controller, api, server} = await restartAccepted('down');
        api.restoreOutcome.mockResolvedValue({kind: 'status', status: inProgress()});

        await vi.advanceTimersByTimeAsync(3 * POLL_MS);
        server.state = 'up';
        await vi.advanceTimersByTimeAsync(SLOW_MS + 5 * POLL_MS);

        expect(api.restoreOutcome, 'precondition: read since the server came back').toHaveBeenCalled();
        expect(controller.outcome, 'a start applies the restore: still waiting').toBe('waiting');
        expect(notStoppingOf(controller), 'the server was seen down: it did stop').toBe(false);
        const probes = api.probeServer.mock.calls.length;
        await vi.advanceTimersByTimeAsync(5 * POLL_MS);
        expect(api.probeServer.mock.calls.length, 'the probing goes on').toBeGreaterThan(probes);
        expect(notStoppingOf(controller)).toBe(false);
    });

    it('never while the restart request is out: nothing probed, false past slowAfterMs, the server up all along', async () => {
        const context = await pendingRestore();
        const {controller, api} = context;
        serve(context, 'up');
        const request = deferred<RestoreRestartAccepted>();
        api.restart.mockReturnValueOnce(request.promise);
        void controller.restartNow();
        await flush();
        expect(controller.state, 'precondition: the restart request is out').toBe('restarting');

        await vi.advanceTimersByTimeAsync(SLOW_MS + 5 * POLL_MS);

        expect(api.probeServer, 'nothing is probed before the restart is accepted').not.toHaveBeenCalled();
        expect(notStoppingOf(controller)).toBe(false);
    });

    it('never after a refused restart: the restore pending with the error, nothing probed, false past slowAfterMs', async () => {
        const context = await pendingRestore();
        const {controller, api} = context;
        serve(context, 'up');
        api.restart.mockRejectedValueOnce(noAnswer());
        void controller.restartNow();
        await flush();
        expect(controller.state, 'precondition: refused, the restore still waits').toBe('pending');
        expect(controller.failure).toBe('restart');

        await vi.advanceTimersByTimeAsync(SLOW_MS + 5 * POLL_MS);

        expect(api.probeServer).not.toHaveBeenCalled();
        expect(notStoppingOf(controller)).toBe(false);
    });
});

// =====================================================================================================================
// The status 500 — a state of the restore the server cannot read, met while the restart is followed (written red first)
// =====================================================================================================================

/*
 * SEC-3/4/5 wave, «the status 500»: `restoreOutcome()` reads `{kind: 'unreadable', reason}` when the status route answers
 * `500 restore_state_unreadable`. Waiting will not make that state readable (the administrator must run
 * `./dev.py backup pending` on the server), so the probing stops at once: `outcome` `state_unreadable`, the new public
 * field `unreadableReason` (`string | null`, the reason as read), `slow` and `notStopping` false, nothing announced, no
 * sign-in, and no probe nor read after it — whether the server was seen down first, or never stopped.
 *
 * Red today: `#settle` knows no `unreadable`; it reads `read.status.state` of an answer without a status, the probe
 * throws, and the outcome stays `waiting`.
 */

const STATE_REASONS = ['io', 'not_a_file', 'invalid'] as const;

/** `unreadableReason` (the status 500), or a failure that names it while the controller publishes none. */
function unreadableReasonOf(controller: RestoreFlowController): string | null {
    expect('unreadableReason' in controller, 'restoreFlow.svelte.ts: the controller publishes no unreadableReason (the status 500)').toBe(true);
    return (controller as unknown as {unreadableReason: string | null}).unreadableReason;
}

/** Nothing probed nor read once the outcome is known, and no timer left behind. */
async function expectPollingStopped(context: Context): Promise<void> {
    const probes = context.api.probeServer.mock.calls.length;
    const reads = context.api.restoreOutcome.mock.calls.length;
    await vi.advanceTimersByTimeAsync(20 * POLL_MS);
    expect(context.api.probeServer.mock.calls.length, 'the server was probed after the outcome').toBe(probes);
    expect(context.api.restoreOutcome.mock.calls.length, 'the outcome was read again after it was known').toBe(reads);
    expect(vi.getTimerCount(), 'a timer outlived the outcome').toBe(0);
}

describe('the status 500 — a state of the restore the server cannot read, while the restart is followed', () => {
    it.each(STATE_REASONS)('seen down, then up, the status unreadable (%s): state_unreadable with its reason, slow and notStopping false, nothing announced, no sign-in, nothing probed nor read after', async (reason) => {
        const context = await restartAccepted('down');
        const {controller, api, server, events, toSignIn} = context;
        api.restoreOutcome.mockResolvedValueOnce({kind: 'unreadable', reason});

        await serverRestarts(server);

        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(controller.outcome, 'an unreadable state ends the wait: no start will make it readable').toBe('state_unreadable');
        expect(unreadableReasonOf(controller)).toBe(reason);
        expect(controller.slow).toBe(false);
        expect(notStoppingOf(controller)).toBe(false);
        expect(toSignIn, 'a restore whose state cannot be read stays on the same screen').not.toHaveBeenCalled();
        expect(events(), 'the unreadable state announces nothing new').toEqual([]);

        await expectPollingStopped(context);
    });

    it('seen down, then up, the status unreadable without a reason: state_unreadable, unreadableReason null, polling stopped', async () => {
        const context = await restartAccepted('down');
        const {controller, api, server} = context;
        api.restoreOutcome.mockResolvedValueOnce({kind: 'unreadable', reason: null});

        await serverRestarts(server);

        expect(controller.outcome).toBe('state_unreadable');
        expect(unreadableReasonOf(controller)).toBeNull();
        await expectPollingStopped(context);
    });

    it('down past slowAfterMs, then up, the status unreadable: slow cleared, state_unreadable, polling stopped', async () => {
        const context = await restartAccepted('down');
        const {controller, api, server} = context;
        await vi.advanceTimersByTimeAsync(SLOW_MS + 2 * POLL_MS);
        expect(controller.slow, 'precondition: the server has been away for a while').toBe(true);
        expect(api.restoreOutcome, 'precondition: nothing read while down').not.toHaveBeenCalled();

        api.restoreOutcome.mockResolvedValueOnce({kind: 'unreadable', reason: 'invalid'});
        server.state = 'up';
        await vi.advanceTimersByTimeAsync(2 * POLL_MS);

        expect(controller.outcome).toBe('state_unreadable');
        expect(unreadableReasonOf(controller)).toBe('invalid');
        expect(controller.slow, 'an outcome known: nothing left to say of the wait').toBe(false);
        await expectPollingStopped(context);
    });

    it('up all along, the status unreadable at the fast read: state_unreadable at once — not taken for a restart that has not happened yet —, polling stopped', async () => {
        const context = await restartAccepted('up');
        const {controller, api, events, toSignIn} = context;
        api.restoreOutcome.mockResolvedValueOnce({kind: 'unreadable', reason: 'not_a_file'});

        await vi.advanceTimersByTimeAsync(FAST_MS - 1);
        expect(api.restoreOutcome, 'read before fastRestartMs').not.toHaveBeenCalled();
        expect(controller.outcome).toBe('waiting');

        await vi.advanceTimersByTimeAsync(2 * POLL_MS + 1);

        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(controller.outcome).toBe('state_unreadable');
        expect(unreadableReasonOf(controller)).toBe('not_a_file');
        expect(notStoppingOf(controller)).toBe(false);
        expect(toSignIn).not.toHaveBeenCalled();
        expect(events()).toEqual([]);
        await expectPollingStopped(context);
    });

    it('a server that never stopped (notStopping), then the status unreadable: notStopping cleared, state_unreadable, polling stopped', async () => {
        const context = await notStoppingShown();
        const {controller, api} = context;
        api.restoreOutcome.mockResolvedValue({kind: 'unreadable', reason: 'io'});

        await vi.advanceTimersByTimeAsync(2 * POLL_MS);

        expect(controller.outcome).toBe('state_unreadable');
        expect(unreadableReasonOf(controller)).toBe('io');
        expect(notStoppingOf(controller), 'an outcome known: nothing left to say of the stop').toBe(false);
        expect(controller.slow).toBe(false);
        await expectPollingStopped(context);
    });
});

// =====================================================================================================================
describe('the outcome ticket (B5c): the ticket of the accepted restart goes with every read of its outcome, held in memory only', () => {
    it('seen down, then up: the outcome read with the ticket the accepted restart answered, and settled as it is answered', async () => {
        const {controller, api, server, events, toSignIn} = await restartAccepted('down');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: outcomeOf('rolled_back', 'swap_failed')});

        await serverRestarts(server);

        expect(api.restoreOutcome.mock.calls, 'the outcome was read without the ticket of the restart').toEqual([[TICKET]]);
        expect(controller.outcome).toBe('rolled_back');
        expect(controller.outcomeStatus).toEqual(outcomeOf('rolled_back', 'swap_failed'));
        expect(toSignIn).not.toHaveBeenCalled();
        expect(events()).toEqual([['backup.restore.rolled_back', {reason: 'swap_failed'}]]);
        expect(vi.getTimerCount()).toBe(0);
    });

    it('up all along: the fast read carries the ticket, and so does every read after it until the outcome', async () => {
        const {controller, api, toSignIn} = await restartAccepted('up');
        api.restoreOutcome.mockResolvedValue({kind: 'status', status: outcomeOf('pending')});

        await vi.advanceTimersByTimeAsync(FAST_MS + 3 * POLL_MS);
        expect(api.restoreOutcome.mock.calls.length, 'precondition: read at the fast read, and again after it').toBeGreaterThanOrEqual(2);
        expect(controller.outcome, 'pending, waiting for nothing, at the fast read: keep waiting').toBe('waiting');

        api.restoreOutcome.mockResolvedValue({kind: 'status', status: outcomeOf('committed')});
        await vi.advanceTimersByTimeAsync(2 * POLL_MS);

        expect(controller.outcome).toBe('restored');
        expect(toSignIn).toHaveBeenCalledTimes(1);
        const reads = api.restoreOutcome.mock.calls;
        expect(reads, 'a read of this restart went without its ticket').toEqual(reads.map(() => [TICKET]));
    });

    it('a new restart reads with its own ticket, never the one before: back to the tab after a restore left pending, then restartNow() again', async () => {
        const {controller, api, server} = await restartAccepted('down');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: outcomeOf('pending', null, 'server_running')});
        await serverRestarts(server);
        expect(controller.outcome, 'precondition: the first restart left the restore pending').toBe('still_pending');

        api.status.mockResolvedValueOnce(pending({waiting: 'server_running'}));
        await controller.load();
        await flush();
        expect(controller.state, 'precondition: back to the tab, the restore pending').toBe('pending');

        api.restart.mockResolvedValueOnce(accepted(OTHER_TICKET));
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: outcomeOf('rolled_back', 'first_start_failed')});
        void controller.restartNow();
        await flush();
        expect(controller.outcome, 'precondition: the second restart was accepted').toBe('waiting');
        await serverRestarts(server);

        expect(api.restoreOutcome.mock.calls).toEqual([[TICKET], [OTHER_TICKET]]);
        expect(controller.outcome).toBe('rolled_back');
    });

    it('confirmed, the restart refused, then restartNow() accepted: the reads carry the ticket of the restart that was accepted', async () => {
        const context = await reportShown();
        const {controller, api} = context;
        api.confirm.mockResolvedValueOnce(pending());
        api.restart.mockRejectedValueOnce(noAnswer());
        await controller.confirm();
        await flush();
        expect(controller.failure, 'precondition: the restart was refused').toBe('restart');

        const server = serve(context, 'down');
        api.restart.mockResolvedValueOnce(accepted(OTHER_TICKET));
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: outcomeOf('committed')});
        void controller.restartNow();
        await flush();
        await serverRestarts(server);

        expect(api.restoreOutcome.mock.calls).toEqual([[OTHER_TICKET]]);
        expect(controller.outcome).toBe('restored');
    });

    it('no ticket outlives its restart: back to the tab, a restart refused, then one answered without a ticket — its read passes null, never the ticket before', async () => {
        const {controller, api, server} = await restartAccepted('down');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: outcomeOf('pending', null, 'backup_running')});
        await serverRestarts(server);
        expect(controller.outcome, 'precondition: the first restart left the restore pending').toBe('still_pending');

        api.status.mockResolvedValueOnce(pending({waiting: 'backup_running'}));
        await controller.load();
        await flush();
        api.restart.mockRejectedValueOnce(noAnswer());
        await controller.restartNow();
        await flush();
        expect(controller.failure, 'precondition: the second restart was refused').toBe('restart');

        // Answered without a ticket (the type requires one): nothing the controller held before may stand in for it.
        api.restart.mockResolvedValueOnce(pending() as RestoreRestartAccepted);
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: outcomeOf('rolled_back', 'stage_missing')});
        void controller.restartNow();
        await flush();
        await serverRestarts(server);

        expect(api.restoreOutcome.mock.calls, 'a read without a ticket passes null, and an older ticket is never reused').toEqual([[TICKET], [null]]);
        expect(controller.outcome).toBe('rolled_back');
    });

    it('a restart accepted after a newer one was asked (an answer of an older generation): its ticket is dropped with it — the reads carry the newer ticket', async () => {
        const context = await pendingRestore();
        const {controller, api} = context;
        const server = serve(context, 'down');
        const first = deferred<RestoreRestartAccepted>();
        api.restart.mockReturnValueOnce(first.promise);
        void controller.restartNow();
        await flush();
        api.status.mockResolvedValueOnce(pending());
        await controller.load();
        await flush();
        expect(controller.state, 'precondition: back to pending, the first restart request still out').toBe('pending');

        api.restart.mockResolvedValueOnce(accepted(OTHER_TICKET));
        void controller.restartNow();
        await flush();
        expect(controller.outcome, 'precondition: the second restart was accepted').toBe('waiting');
        first.resolve(accepted(TICKET));
        await flush();

        api.restoreOutcome.mockResolvedValueOnce({kind: 'signed_out'});
        await serverRestarts(server);

        expect(api.restoreOutcome.mock.calls).toEqual([[OTHER_TICKET]]);
        expect(controller.outcome).toBe('restored');
    });

    it('in memory only: the reads carry the ticket, while no storage — the one given, sessionStorage, localStorage — and no event detail ever holds it', async () => {
        // Owned by the case, before the controller exists: a write to localStorage lands where it is read back below.
        const local = memoryStorage();
        vi.stubGlobal('localStorage', local);
        const context = await reportShown();
        const {controller, api, storage, onEvent} = context;
        const server = serve(context, 'down');
        api.confirm.mockResolvedValueOnce(pending());
        api.restart.mockResolvedValueOnce(accepted());
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: outcomeOf('rolled_back', 'swap_interrupted')});

        void controller.confirm();
        await flush();
        await serverRestarts(server);

        // The presence barrier: the controller held the ticket, and used it.
        expect(api.restoreOutcome.mock.calls).toEqual([[TICKET]]);
        expect(controller.outcome).toBe('rolled_back');

        const holding = (values: Iterable<string | null>) => [...values].filter((value) => value?.includes(TICKET));
        expect(holding(storage.setItem.mock.calls.map(([, value]) => value)), 'the ticket was written to the storage given').toEqual([]);
        expect(holding(storage.items.values())).toEqual([]);
        expect(localStorage, 'precondition: the localStorage read back is the one the case owns').toBe(local);
        expect(holding(local.setItem.mock.calls.flat()), 'the ticket was written to localStorage').toEqual([]);
        for (const [name, store] of [
            ['sessionStorage', sessionStorage],
            ['localStorage', localStorage],
        ] as const) {
            const values = Array.from({length: store.length}, (_, index) => store.getItem(store.key(index) ?? ''));
            expect(holding(values), `the ticket was written to ${name}`).toEqual([]);
        }
        expect(
            onEvent.mock.calls.map(([name]) => name),
            'precondition: the restart was announced',
        ).toContain('backup.restore.restart.requested');
        expect(
            onEvent.mock.calls.filter(([, detail]) => JSON.stringify(detail).includes(TICKET)),
            'an event told the ticket',
        ).toEqual([]);
    });
});

// =====================================================================================================================
describe('the events of the whole flow', () => {
    it('upload, check, confirm, restart, restored: each step announced once, in order, with the details of §2b', async () => {
        const context = await idle();
        const {controller, api, events, toSignIn} = context;
        const server = serve(context, 'down');
        api.upload.mockResolvedValueOnce(uploaded({size: 8192}));
        api.startCheck.mockResolvedValueOnce(runningStage());
        api.getCheck.mockResolvedValueOnce(doneStage(report({action: 'upgrade'})));
        api.confirm.mockResolvedValueOnce(pending());
        api.restart.mockResolvedValueOnce(accepted());
        api.restoreOutcome.mockResolvedValueOnce({kind: 'signed_out'});

        void controller.upload(archive(8192));
        await flush();
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(controller.state, 'precondition: the report').toBe('report');
        void controller.confirm();
        await flush();
        expect(controller.outcome, 'precondition: the restart was accepted').toBe('waiting');
        await serverRestarts(server);

        expect(controller.outcome).toBe('restored');
        expect(toSignIn).toHaveBeenCalledTimes(1);
        expect(events()).toEqual([
            ['backup.restore.uploaded', {upload_id: UPLOAD_ID, size: 8192}],
            ['backup.restore.staged', {stage_id: STAGE_ID, restorable: true, action: 'upgrade'}],
            ['backup.restore.confirmed', {stage_id: STAGE_ID}],
            ['backup.restore.restart.requested', {}],
            ['backup.restore.restored', {}],
        ]);
    });
});

describe('dispose() and stale answers: an answer of an older generation changes nothing', () => {
    it('dispose() during load(): the status answered after it changes nothing, no check read', async () => {
        const context = await setup({stored: STAGE_ID});
        const answer = deferred<RestoreStatus>();
        context.api.status.mockReturnValueOnce(answer.promise);

        void context.controller.load();
        context.controller.dispose();
        answer.resolve(none());
        await flush();

        expect(context.controller.state).toBe('loading');
        expect(context.api.getCheck).not.toHaveBeenCalled();
        expect(context.events()).toEqual([]);
    });

    it('dispose() while uploading: the answer of the PUT changes nothing, no check started', async () => {
        const {controller, api, events} = await idle();
        const answer = deferred<RestoreUpload>();
        api.upload.mockReturnValueOnce(answer.promise);
        void controller.upload(archive());
        await flush();

        controller.dispose();
        answer.resolve(uploaded());
        await flush();

        expect(controller.state).toBe('uploading');
        expect(api.startCheck).not.toHaveBeenCalled();
        expect(events()).toEqual([]);
    });

    it('dispose() while checking: no more reads, no timer left', async () => {
        const {controller, api} = await checking();

        controller.dispose();

        expect(vi.getTimerCount()).toBe(0);
        await vi.advanceTimersByTimeAsync(20 * POLL_MS);
        expect(api.getCheck).not.toHaveBeenCalled();
        expect(controller.state).toBe('checking');
    });

    it.each<[string, (read: Deferred<RestoreStage>) => void]>([
        ['the check done', (read) => read.resolve(doneStage())],
        ['the check failed', (read) => read.resolve(failedStage('not_a_backup'))],
        ['the check gone', (read) => read.reject(refusal(404, 'restore_stage_not_found'))],
    ])('dispose() with a read out, answered after it — %s: no state change, nothing announced, nothing forgotten', async (_case, answer) => {
        const {controller, api, storage, events} = await checking();
        const read = deferred<RestoreStage>();
        api.getCheck.mockReturnValueOnce(read.promise);
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(api.getCheck, 'precondition: a read is out').toHaveBeenCalledTimes(1);

        controller.dispose();
        answer(read);
        await flush();

        expect(controller.state).toBe('checking');
        expect(controller.report).toBeNull();
        expect(storage.items.get(KEY)).toBe(STAGE_ID);
        expect(events()).toEqual([]);
    });

    it('a read of the check answered after dropCheck() dropped it: no report, no staged', async () => {
        const {controller, api, storage, names} = await checking();
        const read = deferred<RestoreStage>();
        api.getCheck.mockReturnValueOnce(read.promise);
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(api.getCheck, 'precondition: a read is out').toHaveBeenCalledTimes(1);
        api.dropCheck.mockResolvedValueOnce(undefined);
        api.status.mockResolvedValue(none());
        void controller.dropCheck();
        await flush();
        expect(controller.state, 'precondition: dropped').toBe('idle');

        read.resolve(doneStage());
        await flush();

        expect(controller.state).toBe('idle');
        expect(controller.report).toBeNull();
        expect(storage.items.has(KEY)).toBe(false);
        expect(names()).not.toContain('backup.restore.staged');
    });

    it('dispose() while confirming: its answer changes nothing, nothing restarted', async () => {
        const {controller, api, storage, events} = await reportShown();
        const answer = deferred<RestoreStatus>();
        api.confirm.mockReturnValueOnce(answer.promise);
        void controller.confirm();
        await flush();

        controller.dispose();
        answer.resolve(pending());
        await flush();

        expect(controller.state).toBe('confirming');
        expect(api.restart).not.toHaveBeenCalled();
        expect(storage.items.get(KEY)).toBe(STAGE_ID);
        expect(events()).toEqual([]);
    });

    it('dispose() while the server is probed: no more probes, a probe answered after it changes nothing, no timer left', async () => {
        const {controller, api, toSignIn} = await restartAccepted('down');
        const probe = deferred<'up' | 'down'>();
        api.probeServer.mockReturnValueOnce(probe.promise);
        api.restoreOutcome.mockResolvedValue({kind: 'signed_out'});
        await vi.advanceTimersByTimeAsync(2 * POLL_MS);

        controller.dispose();
        const probes = api.probeServer.mock.calls.length;
        probe.resolve('up');
        await vi.advanceTimersByTimeAsync(20 * POLL_MS);

        expect(api.probeServer.mock.calls.length, 'probed after dispose()').toBe(probes);
        expect(api.restoreOutcome).not.toHaveBeenCalled();
        expect(controller.outcome).toBe('waiting');
        expect(toSignIn).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });
});

describe('the storage', () => {
    /** Upload, check, report, drop: the whole life of a followed check. */
    async function wholeCheck(context: Context): Promise<void> {
        const {controller, api} = context;
        api.upload.mockResolvedValueOnce(uploaded());
        api.startCheck.mockResolvedValueOnce(runningStage());
        api.getCheck.mockResolvedValueOnce(doneStage());
        api.dropCheck.mockResolvedValueOnce(undefined);
        api.status.mockResolvedValue(none());

        void controller.upload(archive());
        await flush();
        expect(controller.state).toBe('checking');
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(controller.state).toBe('report');
        await controller.dropCheck();
        await flush();
        expect(controller.state).toBe('idle');
    }

    it('a storage that throws on every call never breaks the flow', async () => {
        const insecure = () => new DOMException('The operation is insecure.', 'SecurityError');
        const storage = {
            getItem: vi.fn((_key: string): string | null => {
                throw insecure();
            }),
            setItem: vi.fn((_key: string, _value: string): void => {
                throw new DOMException('The quota has been exceeded.', 'QuotaExceededError');
            }),
            removeItem: vi.fn((_key: string): void => {
                throw insecure();
            }),
        };
        const context = await setup({storage});
        await loaded(context);
        expect(context.controller.state).toBe('idle');

        await wholeCheck(context);

        expect(storage.getItem).toHaveBeenCalledWith(KEY);
        expect(storage.setItem).toHaveBeenCalled();
        expect(storage.removeItem).toHaveBeenCalled();
    });

    it('storage: null keeps the check in memory only and leaves sessionStorage alone', async () => {
        sessionStorage.setItem(KEY, OTHER_STAGE_ID);
        const context = await setup({storage: null});
        await loaded(context);
        expect(context.api.getCheck, 'storage: null must not read sessionStorage').not.toHaveBeenCalled();

        await wholeCheck(context);

        expect(sessionStorage.getItem(KEY)).toBe(OTHER_STAGE_ID);
    });

    it('without a storage option the check goes to sessionStorage, where the next page picks it up', async () => {
        const first = await setup({storage: undefined});
        await loaded(first);
        first.api.upload.mockResolvedValueOnce(uploaded());
        first.api.startCheck.mockResolvedValueOnce(runningStage());
        void first.controller.upload(archive());
        await flush();
        expect(sessionStorage.getItem(KEY)).toBe(STAGE_ID);
        first.controller.dispose();

        const reloaded = await setup({storage: undefined});
        reloaded.api.getCheck.mockResolvedValueOnce(runningStage({phase: 'verifying'}));
        await loaded(reloaded);

        expect(reloaded.api.getCheck.mock.calls).toEqual([[STAGE_ID]]);
        expect(reloaded.controller.state).toBe('checking');
    });
});

describe('the defaults', () => {
    it('without an api option: the status, the upload and the check through the backup aliases; the check read every second', async () => {
        const {RestoreFlowController} = await loadFlow();
        zodios.get_restore_status_api_v1_backup_restore_status_get.mockResolvedValue(none());
        zodios.upload_restore_archive_api_v1_backup_restore_upload_put.mockResolvedValue(uploaded());
        zodios.start_restore_check_api_v1_backup_restore_stage_post.mockResolvedValue(runningStage());
        zodios.get_restore_check_api_v1_backup_restore_stage__stage_id__get.mockResolvedValue(doneStage());
        const controller = new RestoreFlowController({storage: null});
        controllers.push(controller);
        const file = archive();

        void controller.load();
        await flush();
        expect(zodios.get_restore_status_api_v1_backup_restore_status_get).toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('idle');

        void controller.upload(file);
        await flush();
        expect(zodios.upload_restore_archive_api_v1_backup_restore_upload_put.mock.calls[0][0], 'the archive is the raw body').toBe(file);
        expect(zodios.start_restore_check_api_v1_backup_restore_stage_post.mock.calls[0][0]).toEqual({upload_id: UPLOAD_ID});
        expect(controller.state).toBe('checking');

        await vi.advanceTimersByTimeAsync(999);
        expect(zodios.get_restore_check_api_v1_backup_restore_stage__stage_id__get, 'the default pause is one second').not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(1);
        expect(zodios.get_restore_check_api_v1_backup_restore_stage__stage_id__get.mock.calls).toEqual([[{params: {stage_id: STAGE_ID}}]]);
        expect(controller.state).toBe('report');
    });

    it('fastRestartMs 30 s: up all along, the outcome is read only after half a minute', async () => {
        const {controller, api} = await restartAccepted('up', {pollMs: undefined, fastRestartMs: undefined, slowAfterMs: undefined});
        api.restoreOutcome.mockResolvedValueOnce({kind: 'signed_out'});

        await vi.advanceTimersByTimeAsync(30_000 - 1);
        expect(api.restoreOutcome).not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(2_001);

        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(controller.outcome).toBe('restored');
    });

    it('pollMs 1 s and slowAfterMs 60 s: down all along, probed once a second, slow only after a minute', async () => {
        const {controller, api} = await restartAccepted('down', {pollMs: undefined, fastRestartMs: undefined, slowAfterMs: undefined});
        const probes = api.probeServer.mock.calls.length;

        await vi.advanceTimersByTimeAsync(10_000);
        expect(api.probeServer.mock.calls.length - probes, 'probed once a second').toBe(10);
        await vi.advanceTimersByTimeAsync(60_000 - 10_000 - 1);
        expect(controller.slow).toBe(false);
        await vi.advanceTimersByTimeAsync(2_001);

        expect(controller.slow).toBe(true);
    });
});

// =====================================================================================================================
// B4 — an envelope (.lfbk): its password asked before anything is sent (B4 brief §5, §7; written red first)
// =====================================================================================================================

/*
 * The contract under test:
 *   - `upload(file)` of an envelope — its first four bytes `LFBK`, told by `isEnvelopeFile` of backupApi.ts — enters the
 *     state `password`: not busy, nothing sent, nothing to announce yet;
 *   - `submitPassword(password)`: the envelope sent if it was not yet (the same File), then
 *     `startCheck(uploadId, password)`; `wrong_password` or `password_required` → back to `password` with `errorCode`
 *     set and the upload id kept: the next `submitPassword` checks the same upload, the archive is not sent again; any
 *     other refusal fails as today (`failed`, failure `check`, announced);
 *   - `cancelPassword()`: `idle`, the error cleared, the file and the upload id forgotten — the next envelope is asked
 *     for and sent from scratch, under its own upload id;
 *   - a zip takes today's path: sent at once, then `startCheck(uploadId)` with the upload id alone;
 *   - the password goes to `startCheck` and nowhere else: no storage — the one given, `sessionStorage`, `localStorage` —
 *     and no event detail holds it; without an api option it is the body of `POST /restore/stage`,
 *     `{upload_id, password}`.
 *
 * Choices of this file where the contract is silent: `password` is not busy (the existing list of busy states is
 * unchanged), and `idle` after `cancelPassword()` holds no error code.
 *
 * Red today: an envelope is sent at once like a zip (the fake api rejects that unexpected call), the state `password`
 * does not exist, and the controller has neither `submitPassword()` nor `cancelPassword()`. The zip case is the guard of
 * «a zip, as today», green today. The controller's B4 members are reached through `secureFlow()`, written out like the
 * rest of the contract above, so the type check does not wait for them.
 */

/** B4: the state that asks for the password of an envelope. */
type SecureState = RestoreFlowState | 'password';

/** The controller as B4 makes it (§7). */
interface SecureFlow extends Omit<RestoreFlowController, 'state'> {
    readonly state: SecureState;
    submitPassword(password: string): Promise<void>;
    cancelPassword(): void;
}

/** The controller with B4's members, or a failure that names the one missing. */
function secureFlow(controller: RestoreFlowController): SecureFlow {
    const flow = controller as unknown as SecureFlow;
    for (const name of ['submitPassword', 'cancelPassword'] as const) {
        expect(typeof flow[name], `restoreFlow.svelte.ts: the controller has no ${name}() (B4 §7)`).toBe('function');
    }
    return flow;
}

/** An envelope as the server writes it (B4 §1): `LFBK`, then the rest of its header — version 1, scrypt, log2(n) 15, r 8, p 1. */
function envelope(name = 'librefolio-backup-20261016-230000.lfbk'): File {
    return new File(['LFBK\u0001\u0001\u000f\u0008\u0001'], name, {type: 'application/octet-stream'});
}

const PASSWORD = 'Correct-Horse-Battery-9';
const OTHER_PASSWORD = 'Staple-Battery-Horse-7';
const OTHER_UPLOAD_ID = 'abcdef0123456789abcdef0123456789';
/** B4's first phase of the check of an envelope: the generated client does not know it yet. */
const DECRYPTING = 'decrypting' as string as NonNullable<RestoreStage['phase']>;

/** A controller in `idle` that was given `file`, an envelope: the password is asked. */
async function passwordAsked(file: File = envelope()) {
    const context = await idle();
    await context.controller.upload(file);
    await flush();
    expect(context.controller.state as SecureState, 'precondition: the password of the envelope is asked').toBe('password');
    return {...context, flow: secureFlow(context.controller), file};
}

describe('B4 — an envelope: the password asked before anything is sent', () => {
    it('upload(envelope): the state password, not busy, nothing sent, nothing announced', async () => {
        const {controller, api, names} = await idle();

        await controller.upload(envelope());
        await flush();

        expect(api.upload, 'the envelope was sent before its password was asked').not.toHaveBeenCalled();
        expect(api.startCheck).not.toHaveBeenCalled();
        expect(controller.state as SecureState).toBe('password');
        expect(controller.busy, 'the card waits for the user, not for the server').toBe(false);
        expect(controller.errorCode).toBeNull();
        expect(names()).toEqual([]);
    });

    it('submitPassword(password): the envelope sent once, the File itself, then its check started with the upload id and the password', async () => {
        const {flow, api, events, file} = await passwordAsked();
        api.upload.mockResolvedValueOnce(uploaded({kind: 'envelope', size: file.size}));
        api.startCheck.mockResolvedValueOnce(runningStage({phase: DECRYPTING}));

        void flow.submitPassword(PASSWORD);
        await flush();

        expect(api.upload).toHaveBeenCalledTimes(1);
        expect(api.upload.mock.calls[0][0], 'the File chosen is sent').toBe(file);
        expect(api.startCheck.mock.calls).toEqual([[UPLOAD_ID, PASSWORD]]);
        expect(flow.state).toBe('checking');
        expect(flow.errorCode).toBeNull();
        expect(events()).toContainEqual(['backup.restore.uploaded', {upload_id: UPLOAD_ID, size: file.size}]);
    });

    it.each<[string, number]>([
        ['wrong_password', 400],
        ['password_required', 400],
    ])('a check refused as %s: back to password with the code, not busy; the next password checks the same upload — the archive is not sent again', async (code, status) => {
        const {flow, api, file} = await passwordAsked();
        api.upload.mockResolvedValueOnce(uploaded({kind: 'envelope', size: file.size}));
        api.startCheck.mockRejectedValueOnce(refusal(status, code));

        void flow.submitPassword(PASSWORD);
        await flush();

        expect(api.startCheck.mock.calls, 'precondition: the check was asked with the password').toEqual([[UPLOAD_ID, PASSWORD]]);
        expect(flow.state).toBe('password');
        expect(flow.errorCode).toBe(code);
        expect(flow.busy).toBe(false);

        api.startCheck.mockResolvedValueOnce(runningStage({phase: DECRYPTING}));
        void flow.submitPassword(OTHER_PASSWORD);
        await flush();

        expect(api.upload, 'the archive was sent again: the upload id was not kept').toHaveBeenCalledTimes(1);
        expect(api.startCheck.mock.calls).toEqual([
            [UPLOAD_ID, PASSWORD],
            [UPLOAD_ID, OTHER_PASSWORD],
        ]);
        expect(flow.state).toBe('checking');
        expect(flow.errorCode).toBeNull();
    });

    it.each<[string, number]>([
        ['envelope_damaged', 400],
        ['envelope_unsupported', 409],
        ['restore_busy', 409],
    ])('a check refused as %s: failed (check) with the code, announced, as any check that cannot start', async (code, status) => {
        const {flow, api, events, file} = await passwordAsked();
        api.upload.mockResolvedValueOnce(uploaded({kind: 'envelope', size: file.size}));
        api.startCheck.mockRejectedValueOnce(refusal(status, code));

        void flow.submitPassword(PASSWORD);
        await flush();

        expect(flow.state).toBe('failed');
        expect(flow.errorCode).toBe(code);
        expect(flow.failure).toBe('check');
        expect(events()).toContainEqual(['backup.restore.failed', {code, what: 'check'}]);
    });

    it('cancelPassword() before anything was sent: idle, nothing sent; the next envelope is asked for, and the File sent is that one', async () => {
        const {flow, api} = await passwordAsked(envelope('first.lfbk'));

        flow.cancelPassword();
        await flush();

        expect(flow.state).toBe('idle');
        expect(flow.errorCode).toBeNull();
        expect(api.upload).not.toHaveBeenCalled();

        const second = envelope('second.lfbk');
        await flow.upload(second);
        await flush();
        expect(flow.state, 'the next envelope asks for its own password').toBe('password');
        api.upload.mockResolvedValueOnce(uploaded({kind: 'envelope', size: second.size}));
        api.startCheck.mockResolvedValueOnce(runningStage());

        void flow.submitPassword(PASSWORD);
        await flush();

        expect(api.upload).toHaveBeenCalledTimes(1);
        expect(api.upload.mock.calls[0][0], 'the File sent is the one chosen last').toBe(second);
    });

    it('cancelPassword() after a wrong password: idle, the error gone, the upload forgotten — the next envelope is sent again and checked under its own upload id', async () => {
        const {flow, api, file} = await passwordAsked(envelope('first.lfbk'));
        api.upload.mockResolvedValueOnce(uploaded({kind: 'envelope', size: file.size}));
        api.startCheck.mockRejectedValueOnce(refusal(400, 'wrong_password'));
        void flow.submitPassword(PASSWORD);
        await flush();
        expect(flow.errorCode, 'precondition: the password was wrong').toBe('wrong_password');

        flow.cancelPassword();
        await flush();

        expect(flow.state).toBe('idle');
        expect(flow.errorCode).toBeNull();

        const second = envelope('second.lfbk');
        await flow.upload(second);
        await flush();
        api.upload.mockResolvedValueOnce(uploaded({upload_id: OTHER_UPLOAD_ID, kind: 'envelope', size: second.size}));
        api.startCheck.mockResolvedValueOnce(runningStage());
        void flow.submitPassword(PASSWORD);
        await flush();

        expect(api.upload, 'the next envelope must be sent: the server keeps an upload only for a while').toHaveBeenCalledTimes(2);
        expect(api.upload.mock.calls[1][0]).toBe(second);
        expect(api.startCheck.mock.calls, 'the forgotten upload id was checked again').toEqual([
            [UPLOAD_ID, PASSWORD],
            [OTHER_UPLOAD_ID, PASSWORD],
        ]);
        expect(flow.state).toBe('checking');
    });

    it("a zip: today's path — sent at once, then checked with the upload id alone; no password asked (green today: the guard)", async () => {
        const {controller, api} = await idle();
        api.upload.mockResolvedValueOnce(uploaded());
        api.startCheck.mockResolvedValueOnce(runningStage());

        void controller.upload(archive());
        await flush();

        expect(api.upload).toHaveBeenCalledTimes(1);
        expect(api.startCheck.mock.calls, 'a zip is checked with the upload id alone').toEqual([[UPLOAD_ID]]);
        expect(controller.state).toBe('checking');
    });

    it('the password goes to the check and nowhere else: no storage — the one given, sessionStorage, localStorage — and no event detail holds it', async () => {
        // Owned by the case, before the controller exists: a write to localStorage lands where it is read back below.
        const local = memoryStorage();
        vi.stubGlobal('localStorage', local);
        const {flow, api, storage, onEvent, file} = await passwordAsked();
        api.upload.mockResolvedValueOnce(uploaded({kind: 'envelope', size: file.size}));
        api.startCheck.mockRejectedValueOnce(refusal(400, 'wrong_password')).mockResolvedValueOnce(runningStage());

        void flow.submitPassword(PASSWORD);
        await flush();
        void flow.submitPassword(OTHER_PASSWORD);
        await flush();

        // The presence barrier: the controller held both passwords, and used them.
        expect(api.startCheck.mock.calls).toEqual([
            [UPLOAD_ID, PASSWORD],
            [UPLOAD_ID, OTHER_PASSWORD],
        ]);
        expect(storage.setItem, 'precondition: the check was remembered').toHaveBeenCalled();
        const holding = (values: Iterable<unknown>) => [...values].filter((value) => typeof value === 'string' && (value.includes(PASSWORD) || value.includes(OTHER_PASSWORD)));
        expect(holding(storage.setItem.mock.calls.flat()), 'a password was written to the storage given').toEqual([]);
        expect(localStorage, 'precondition: the localStorage read back is the one the case owns').toBe(local);
        expect(holding(local.setItem.mock.calls.flat()), 'a password was written to localStorage').toEqual([]);
        const sessionValues = Array.from({length: sessionStorage.length}, (_, index) => sessionStorage.getItem(sessionStorage.key(index) ?? ''));
        expect(holding(sessionValues), 'a password was written to sessionStorage').toEqual([]);
        expect(
            onEvent.mock.calls.filter(([, detail]) => holding([JSON.stringify(detail)]).length > 0),
            'an event told a password',
        ).toEqual([]);
    });

    it('without an api option: nothing sent before the password; then the envelope, and POST /restore/stage with the body {upload_id, password}', async () => {
        const {RestoreFlowController} = await loadFlow();
        zodios.get_restore_status_api_v1_backup_restore_status_get.mockResolvedValue(none());
        zodios.upload_restore_archive_api_v1_backup_restore_upload_put.mockResolvedValue(uploaded({kind: 'envelope'}));
        zodios.start_restore_check_api_v1_backup_restore_stage_post.mockResolvedValue(runningStage({phase: DECRYPTING}));
        const controller = new RestoreFlowController({storage: null});
        controllers.push(controller);
        const file = envelope();

        void controller.load();
        await flush();
        expect(controller.state, 'precondition: idle').toBe('idle');
        await controller.upload(file);
        await flush();

        expect(zodios.upload_restore_archive_api_v1_backup_restore_upload_put, 'the envelope was sent before its password was asked').not.toHaveBeenCalled();
        void secureFlow(controller).submitPassword(PASSWORD);
        await flush();

        expect(zodios.upload_restore_archive_api_v1_backup_restore_upload_put.mock.calls[0][0], 'the archive is the raw body').toBe(file);
        expect(zodios.start_restore_check_api_v1_backup_restore_stage_post.mock.calls[0][0], 'the body of POST /restore/stage').toStrictEqual({upload_id: UPLOAD_ID, password: PASSWORD});
    });
});

// =====================================================================================================================
// B-15 — a proxy's 413 on the upload of the archive says so (written red first)
// =====================================================================================================================

/*
 * The contract under test (the B-15 + B-8 contract, B-15): the PUT of the archive answered 413 with no LibreFolio code —
 * the page of a proxy in front of LibreFolio (nginx's `client_max_body_size`, Fly, a CDN), an empty body, JSON without
 * `detail.code` — fails as any refused upload, with the code `proxy_too_large` (`uploadFailureCode` of backupApi.ts):
 * `failed`, failure `upload`, no limit (`errorLimitMb` null: the proxy's is not known), nothing checked nor remembered,
 * `backup.restore.failed {code: 'proxy_too_large', what: 'upload'}` once (the event whose code words the card's toast),
 * and the sentence the card shows is `backup.restore.errors.proxy_too_large` (`restoreErrorKey`, as RestoreCard.svelte
 * resolves it). The envelope of a secure backup, sent once its password is given, is the same upload.
 * LibreFolio's own 413 keeps `backup_too_large` and its `limit_mb`; a proxy page of another status stays `unexpected`;
 * a proxy that drops the connection stays `network`. The upload is the one request read this way: the start of the
 * check, refused 413 without a code, stays `unexpected`.
 *
 * The archive of these cases is under the limit the server announces, as it is when a proxy refuses what LibreFolio
 * would take.
 *
 * Red today: the upload reads such a 413 as `unexpected`, and `restoreErrorKey` knows no `proxy_too_large`. Green today,
 * and to stay so: LibreFolio's own 413, a 502 page, no answer, and the start of the check.
 */

/** What nginx answers an upload over its `client_max_body_size`: its own HTML page, nothing of LibreFolio's. */
const NGINX_413 = '<html>\r\n<head><title>413 Request Entity Too Large</title></head>\r\n<body>\r\n<center><h1>413 Request Entity Too Large</h1></center>\r\n<hr><center>nginx</center>\r\n</body>\r\n</html>\r\n';

/** An answer of `status` whose body is `data`, raised by axios: a refusal of LibreFolio's only when `data` is one. */
function answered(status: number, data: unknown) {
    return {isAxiosError: true, message: `Request failed with status code ${status}`, response: {status, data}};
}

/** The limit the server announces, and an archive under it. */
const LIMIT_MB = 500;
const UNDER_THE_LIMIT = 200 * MIB;

describe('B-15 — a proxy refused the archive: proxy_too_large', () => {
    it.each<[string, () => unknown]>([
        ["nginx's page (client_max_body_size)", () => answered(413, NGINX_413)],
        ['an empty body', () => answered(413, '')],
        ['JSON without detail.code (an API gateway)', () => answered(413, {message: 'Request Too Long'})],
    ])('a 413 with %s: failed (upload) with proxy_too_large, no limit, announced once, nothing checked nor remembered, worded by backup.restore.errors.proxy_too_large', async (_case, refused) => {
        const {controller, api, storage, events} = await idle({upload_limit_mb: LIMIT_MB});
        api.upload.mockRejectedValueOnce(refused());

        await controller.upload(archive(UNDER_THE_LIMIT));
        await flush();

        expect(api.upload, 'precondition: under the limit the server announces, the archive was sent').toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('proxy_too_large');
        expect(controller.failure).toBe('upload');
        expect(controller.errorLimitMb, "the proxy's limit is not known").toBeNull();
        expect(controller.busy).toBe(false);
        expect(api.startCheck).not.toHaveBeenCalled();
        expect(storage.setItem).not.toHaveBeenCalled();
        expect(events()).toEqual([['backup.restore.failed', {code: 'proxy_too_large', what: 'upload'}]]);
        expect(restoreErrorKey(controller.errorCode), 'the sentence the card shows').toBe('backup.restore.errors.proxy_too_large');
    });

    it.each<[string, () => unknown, string, number | null]>([
        ["LibreFolio's own 413: backup_too_large, with the limit it names", () => refusal(413, 'backup_too_large', {limit_mb: 250}), 'backup_too_large', 250],
        ['a proxy page of another status (502): unexpected', () => answered(502, '<html><body>Bad Gateway</body></html>'), 'unexpected', null],
        ['a proxy that drops the connection, no answer: network', noAnswer, 'network', null],
    ])('%s, as before (green today: the guard)', async (_case, refused, code, limit) => {
        const {controller, api, events} = await idle({upload_limit_mb: LIMIT_MB});
        api.upload.mockRejectedValueOnce(refused());

        await controller.upload(archive(UNDER_THE_LIMIT));
        await flush();

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('upload');
        expect(controller.errorLimitMb).toBe(limit);
        expect(events()).toEqual([['backup.restore.failed', {code, what: 'upload'}]]);
        expect(restoreErrorKey(controller.errorCode), 'the sentence the card shows').toBe(`backup.restore.errors.${code}`);
    });

    it("the envelope of a secure backup, sent once its password is given, refused with nginx's 413: failed (upload) with proxy_too_large, no limit, announced once", async () => {
        const {flow, api, events} = await passwordAsked();
        api.upload.mockRejectedValueOnce(answered(413, NGINX_413));

        void flow.submitPassword(PASSWORD);
        await flush();

        expect(api.upload, 'precondition: the envelope was sent').toHaveBeenCalledTimes(1);
        expect(api.startCheck).not.toHaveBeenCalled();
        expect(flow.state).toBe('failed');
        expect(flow.errorCode).toBe('proxy_too_large');
        expect(flow.failure).toBe('upload');
        expect(flow.errorLimitMb).toBeNull();
        expect(events()).toEqual([['backup.restore.failed', {code: 'proxy_too_large', what: 'upload'}]]);
    });

    it("the start of the check, not the upload, refused with nginx's 413: unexpected, as before (green today: the guard)", async () => {
        const {controller, api, events} = await idle();
        api.upload.mockResolvedValueOnce(uploaded());
        api.startCheck.mockRejectedValueOnce(answered(413, NGINX_413));

        await controller.upload(archive());
        await flush();

        expect(api.startCheck.mock.calls).toEqual([[UPLOAD_ID]]);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('unexpected');
        expect(controller.failure).toBe('check');
        expect(events()).toEqual([
            ['backup.restore.uploaded', {upload_id: UPLOAD_ID, size: 4096}],
            ['backup.restore.failed', {code: 'unexpected', what: 'check'}],
        ]);
    });
});
