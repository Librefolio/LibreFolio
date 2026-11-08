// @vitest-environment jsdom
/**
 * RestoreKeptModal — «Restore» on a row of the kept backups, in a modal of its own (A10, T-15; component test, Vitest +
 * jsdom). The developer, on the 1.3 testlist: the row filled the restore card in; they expected a modal with the report,
 * the password check and the confirmation, the card keeping only «Resume» and «Discard» for a check left for later.
 *
 * What this file pins:
 *   - mounted, the modal reads the restore's status, then takes the kept backup as the archive
 *     (`restoreFromKeptBackup(jobId)`) and checks it (`startRestoreCheck(uploadId)`): the progress shows in the modal
 *     (`restore-kept-check-progress`), never in a card; the root `restore-kept` publishes `data-state` and `data-busy`;
 *   - the check done, the report's modal (`restore-report`) opens in its place;
 *   - a secure backup asks its password in the modal (`restore-kept-password-form`), then checks with it;
 *   - closing the report leaves the check for later: the status is read again, `onClose` is called once and the card is
 *     told (`restoreSignal.version` grows), which then lists the check to resume or discard;
 *   - a restore already waiting for the next start: `restore-kept-already-waiting`, and nothing is started;
 *   - a refusal shows `restore-kept-error` with its code, and `restore-kept-retry` takes the backup again;
 *   - the close button during the password step: `onClose`, the card told, nothing sent.
 *
 * The seams, as in RestoreCard.test.ts: `$lib/i18n` renders every key as itself, `./backupApi` swaps the restore
 * functions for `vi.fn` (a call a case did not expect rejects), `$lib/api` throws on any request, `notify` is a spy. The
 * clock is fake (the controller polls every second).
 */
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import {readable, writable} from 'svelte/store';
import {tick} from 'svelte';
import type {z} from 'zod';
import type {schemas} from '$lib/api';
import {cleanup, fireEvent, render, screen} from '$test/component';

vi.mock('$lib/i18n', () => {
    const translate = (key: string, options?: {values?: Record<string, unknown>}) => {
        if (key === 'backup.restore.confirm.words' || key === 'backup.restore.confirm.word') return 'violet';
        return options?.values ? `${key} ${JSON.stringify(options.values)}` : key;
    };
    const translator = readable(translate);
    return {
        _: translator,
        t: translator,
        locale: writable('en'),
        date: readable((value: unknown) => String(value)),
        time: readable((value: unknown) => String(value)),
        number: readable((value: unknown) => String(value)),
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

vi.mock('$lib/api', () => {
    const zodiosApi = new Proxy(
        {},
        {
            get: (_target, alias) =>
                typeof alias !== 'string' || alias === 'then'
                    ? undefined
                    : () => {
                          throw new Error(`RestoreKeptModal.test: a request went through zodiosApi.${alias}`);
                      },
        },
    );
    return {zodiosApi, schemas: {}, axiosInstance: {}, ApiError: class ApiError extends Error {}};
});

vi.mock('./backupApi', async () => {
    const actual = await vi.importActual<Record<string, unknown>>('./backupApi');
    return {
        ...actual,
        getRestoreStatus: vi.fn(),
        uploadRestoreArchive: vi.fn(),
        startRestoreCheck: vi.fn(),
        getRestoreCheck: vi.fn(),
        deleteRestoreCheck: vi.fn(),
        confirmRestore: vi.fn(),
        cancelPendingRestore: vi.fn(),
        requestRestart: vi.fn(),
        probeServer: vi.fn(),
        restoreOutcome: vi.fn(),
        listWaitingRestoreChecks: vi.fn(),
        restoreFromKeptBackup: vi.fn(),
        verifyRestorePassword: vi.fn(),
    };
});

vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));

import * as backupApi from './backupApi';
import RestoreKeptModal from './RestoreKeptModal.svelte';
import {restoreSignal} from './restoreSignal.svelte';

type RestoreStatus = z.infer<typeof schemas.RestoreStatus>;
type RestoreStage = z.infer<typeof schemas.RestoreStage>;
type RestoreStageReport = z.infer<typeof schemas.RestoreStageReport>;

const FUNCTIONS = [
    'getRestoreStatus',
    'uploadRestoreArchive',
    'startRestoreCheck',
    'getRestoreCheck',
    'deleteRestoreCheck',
    'confirmRestore',
    'cancelPendingRestore',
    'requestRestart',
    'probeServer',
    'restoreOutcome',
    'listWaitingRestoreChecks',
    'restoreFromKeptBackup',
    'verifyRestorePassword',
] as const;
const api = backupApi as unknown as Record<(typeof FUNCTIONS)[number], Mock<(...args: unknown[]) => Promise<unknown>>>;

const JOB_ID = 'aa112233445566778899aabbccddeeff';
const UPLOAD_ID = '0123456789abcdef0123456789abcdef';
const STAGE_ID = 'fedcba9876543210fedcba9876543210';
const POLL_MS = 1000;

function status(overrides: Partial<RestoreStatus> = {}): RestoreStatus {
    return {state: 'none', stage_id: null, confirmed_at: null, confirmed_by: null, backup_created_at: null, backup_app_version: null, action: null, finished_at: null, reason: null, waiting: null, upload_limit_mb: 500, ...overrides} as RestoreStatus;
}

function report(): RestoreStageReport {
    return {
        backup_created_at: '2026-11-07T12:00:00Z',
        backup_app_version: '1.3.0',
        backup_origin: 'ui',
        backup_revision: 'c0ffee000001',
        app_version: '1.3.0',
        head_revision: 'c0ffee000001',
        action: 'same',
        migrations: [],
        post_migration_fixes: [],
        tables: {asset: {before: 12, after: 12}},
        foreign_key_violations_before: 0,
        foreign_key_violations_after: 0,
        files: 3,
        files_size: 2048,
        database_size: 1024 * 1024,
        instance_key_included: false,
        encrypted: false,
        secrets_rekeyed: 0,
        secrets_unreadable: {system: 0, user: 0},
        administrators: ['giulia.bianchi'],
        warnings: [],
        blockers: [],
        control_totals: 'same',
        control_totals_differences: [],
        control_totals_differences_count: 0,
        restorable: true,
        expires_at: '2026-11-08T12:00:00Z',
    } as unknown as RestoreStageReport;
}

function stage(overrides: Partial<RestoreStage> = {}): RestoreStage {
    return {stage_id: STAGE_ID, status: 'running', phase: 'checking', done_bytes: 0, total_bytes: 0, created_at: '2026-11-08T09:00:00Z', finished_at: null, error_code: null, report: null, ...overrides};
}

const doneStage = () => stage({status: 'done', phase: null, done_bytes: 4096, total_bytes: 4096, finished_at: '2026-11-08T09:01:00Z', report: report()});

function refusal(code: string, httpStatus = 409) {
    return {isAxiosError: true, message: `Request failed with status code ${httpStatus}`, response: {status: httpStatus, data: {detail: {code, message: `refused: ${code}`}}}};
}

async function settle(): Promise<void> {
    await vi.advanceTimersByTimeAsync(0);
    await tick();
}

const root = () => screen.getByTestId('restore-kept');

async function mount(first: RestoreStatus = status()) {
    api.getRestoreStatus.mockResolvedValueOnce(first);
    api.listWaitingRestoreChecks.mockResolvedValue([]);
    const onClose = vi.fn();
    render(RestoreKeptModal, {props: {jobId: JOB_ID, createdAt: '2026-11-07T12:00:00Z', onClose}});
    await settle();
    return onClose;
}

beforeEach(() => {
    vi.useFakeTimers();
    sessionStorage.clear();
    for (const name of FUNCTIONS) {
        api[name].mockReset();
        api[name].mockImplementation(() => Promise.reject(new Error(`${name}(): a request this case did not expect`)));
    }
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.useRealTimers();
    sessionStorage.clear();
});

describe('A10 — RestoreKeptModal: a kept backup restored in its own modal', () => {
    it('takes the kept backup and checks it in the modal, then opens the report in its place', async () => {
        api.restoreFromKeptBackup.mockResolvedValueOnce({upload_id: UPLOAD_ID, size: 4096, kind: 'zip'});
        api.startRestoreCheck.mockResolvedValueOnce(stage());
        await mount();

        expect(api.restoreFromKeptBackup).toHaveBeenCalledWith(JOB_ID);
        expect(api.startRestoreCheck).toHaveBeenCalledWith(UPLOAD_ID);
        expect(api.uploadRestoreArchive, 'nothing uploaded from the computer').not.toHaveBeenCalled();
        expect(root()).toHaveAttribute('data-state', 'checking');
        expect(root()).toHaveAttribute('data-busy', 'true');
        expect(screen.getByTestId('restore-kept-check-progress')).toBeInTheDocument();
        expect(screen.queryByTestId('restore-card'), 'no card involved').toBeNull();
        expect(sessionStorage.length, 'the modal remembers nothing across a reload: the card lists the check').toBe(0);

        api.getRestoreCheck.mockResolvedValueOnce(doneStage());
        await vi.advanceTimersByTimeAsync(POLL_MS);
        await settle();

        expect(screen.getByTestId('restore-report')).toBeInTheDocument();
        expect(screen.queryByTestId('restore-kept')).toBeNull();
    });

    it('a secure backup asks its password in the modal, then checks with it', async () => {
        api.restoreFromKeptBackup.mockResolvedValueOnce({upload_id: UPLOAD_ID, size: 4096, kind: 'envelope'});
        await mount();

        expect(root()).toHaveAttribute('data-state', 'password');
        expect(screen.getByTestId('restore-kept-password-form')).toBeInTheDocument();
        api.startRestoreCheck.mockResolvedValueOnce(stage());
        await fireEvent.input(screen.getByTestId('restore-kept-password'), {target: {value: 'Backup-Pass-1!'}});
        await fireEvent.click(screen.getByTestId('restore-kept-password-submit'));
        await settle();

        expect(api.startRestoreCheck).toHaveBeenCalledWith(UPLOAD_ID, 'Backup-Pass-1!');
        expect(root()).toHaveAttribute('data-state', 'checking');
    });

    it('closing the report leaves the check for later: the status read again, onClose once, the card told', async () => {
        api.restoreFromKeptBackup.mockResolvedValueOnce({upload_id: UPLOAD_ID, size: 4096, kind: 'zip'});
        api.startRestoreCheck.mockResolvedValueOnce(doneStage());
        const onClose = await mount();
        expect(screen.getByTestId('restore-report')).toBeInTheDocument();
        const before = restoreSignal.version;

        api.getRestoreStatus.mockResolvedValueOnce(status());
        await fireEvent.click(screen.getByTestId('restore-report-close'));
        await settle();

        expect(api.deleteRestoreCheck, 'left for later, not dropped').not.toHaveBeenCalled();
        expect(onClose).toHaveBeenCalledTimes(1);
        expect(restoreSignal.version).toBe(before + 1);
    });

    it('a restore already waiting for the next start is said, and nothing is started', async () => {
        await mount(status({state: 'pending', stage_id: STAGE_ID, confirmed_at: '2026-11-08T09:00:00Z', confirmed_by: 'admin'}));

        expect(screen.getByTestId('restore-kept-already-waiting')).toBeInTheDocument();
        expect(api.restoreFromKeptBackup).not.toHaveBeenCalled();
    });

    it('a refusal shows its code; «Try again» takes the backup again', async () => {
        api.restoreFromKeptBackup.mockRejectedValueOnce(refusal('backup_no_space', 507));
        await mount();

        expect(root()).toHaveAttribute('data-state', 'failed');
        expect(screen.getByTestId('restore-kept-error')).toHaveAttribute('data-error-code', 'backup_no_space');

        api.restoreFromKeptBackup.mockResolvedValueOnce({upload_id: UPLOAD_ID, size: 4096, kind: 'zip'});
        api.startRestoreCheck.mockResolvedValueOnce(stage());
        await fireEvent.click(screen.getByTestId('restore-kept-retry'));
        await settle();

        expect(api.restoreFromKeptBackup).toHaveBeenCalledTimes(2);
        expect(root()).toHaveAttribute('data-state', 'checking');
    });

    it('closed at the password step: onClose, the card told, nothing checked', async () => {
        api.restoreFromKeptBackup.mockResolvedValueOnce({upload_id: UPLOAD_ID, size: 4096, kind: 'envelope'});
        const onClose = await mount();
        const before = restoreSignal.version;

        await fireEvent.click(screen.getByTestId('restore-kept-close'));
        await settle();

        expect(onClose).toHaveBeenCalledTimes(1);
        expect(restoreSignal.version).toBe(before + 1);
        expect(api.startRestoreCheck).not.toHaveBeenCalled();
    });
});
