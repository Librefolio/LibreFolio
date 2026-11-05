// @vitest-environment jsdom
/**
 * StorageBar — component test (Vitest + jsdom), lot FB-29, written red first against `B6r-fb29-interface.md` §5.
 *
 * The bar of the Files page that tells an administrator how much room the instance takes: with a limit, the space used
 * against it; without one, LibreFolio's parts against the disk (the other files of the disk in grey, the rest free); with
 * neither, the parts against the data folder. The component takes no props; the page mounts it for administrators.
 *
 * What this file pins:
 *   - the root `storage-bar`: `data-state` (`loading|ready|error`), `data-busy`/`aria-busy`, `data-mode`
 *     (`limit|volume|data`, read off the usage by the same rules as `storageBarModel`, whose numbers `storageBarModel.test.ts`
 *     owns); it reads at mount once, and again at every change of `backupListSignal.version`;
 *   - the track `storage-bar-track` and one `storage-segment-<id>` per NON-EMPTY part, in the model's order, each with
 *     `data-bytes` and a width in % (`database`, `uploads`, `brokerReports`, `backups`, `dataOther`, and `disk` in volume
 *     mode); the free space is `storage-segment-free`;
 *   - the legend: a `storage-legend-<id>` row per drawn segment and for the free space, named by the key
 *     `storage.parts.<id>` and showing the size through `formatBytes`;
 *   - the summary `storage-summary`: `storage.summary.limit` / `.volume` / `.data` by mode, filled with the used size
 *     (and the limit, and the disk size, in the placeholders `{used}`, `{limit}`, `{total}` the catalogues name);
 *   - `storage-over-limit` (`storage.overLimit`) only when the data folder is bigger than the limit;
 *   - a read that fails: `data-state="error"`, `storage-error` with `data-error-code`, and `storage-retry`;
 *   - the limit editor: `storage-limit-mb` (starts at the limit in force, 0 when there is none), `storage-limit-save`
 *     (off while nothing differs, while the value is not a whole number ≥ 0, and while a save is out), the save through
 *     `saveStorageLimit(mb)` once, the event `storage.limit.saved` `{limit_mb}`, the bar read again; a refused save is
 *     `storage-limit-error` with `data-error-code` and the key `storage.limit.errors.<invalid|forbidden|locked|network|
 *     unexpected>`; when the environment pins the limit (`limit_locked`) the field is disabled and `storage-limit-locked`
 *     says so.
 *
 * The seams. `$lib/i18n` is a translator that prints the key, and the `values` it is given after it (as JSON), so the
 * summary’s placeholders can be read without translated text. `./backupApi` keeps its real `storageLimitSaveCode` and
 * swaps the two requests for `vi.fn`; `$lib/api` throws on any request. The component is loaded inside each case, so
 * that while it does not exist each case fails on its own.
 *
 * What it deliberately does not assert: the translated sentences, the colours of the segments (design-system roles),
 * how long anything stays on screen, and any CSS class.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

// --- Mocks ----------------------------------------------------------------------------------------------------------

vi.mock('$lib/i18n', () => {
    const translate = (key: string, options?: {values?: Record<string, unknown>}) => (options?.values ? `${key} ${JSON.stringify(options.values)}` : key);
    const translator = readable(translate);
    return {
        _: translator,
        t: translator,
        locale: writable('en'),
        date: readable((v: unknown) => String(v)),
        time: readable((v: unknown) => String(v)),
        number: readable((v: unknown) => String(v)),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano', fr: 'Français', es: 'Español'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT'},
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
                          throw new Error(`StorageBar.test: a request went through zodiosApi.${alias}`);
                      },
        },
    );
    return {zodiosApi, schemas: {}, axiosInstance: {}, ApiError: class ApiError extends Error {}};
});

vi.mock('$lib/features/backup/backupApi', async () => {
    const actual = await vi.importActual<typeof import('$lib/features/backup/backupApi')>('$lib/features/backup/backupApi');
    return {...actual, getInstanceStorage: vi.fn(), saveStorageLimit: vi.fn()};
});

vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));

import {getInstanceStorage, saveStorageLimit} from '$lib/features/backup/backupApi';
import type {InstanceStorage} from '$lib/features/backup/backupApi';
import {notifyBackupListChanged} from '$lib/features/backup/backupList.svelte';
import {notify} from '$lib/stores/app/notify.svelte';
import {formatBytes} from '$lib/utils/files/upload';

// A literal path would fail the whole file at transform time while the module is missing; a variable path fails each case alone.
const MODULES = {bar: './StorageBar.svelte'};
const loadBar = async () => (await import(/* @vite-ignore */ MODULES.bar)).default;

// --- Fixtures -------------------------------------------------------------------------------------------------------

const MiB = 1024 * 1024;
const GiB = 1024 * MiB;

type Parts = {database?: number; uploads?: number; brokerReports?: number; backups?: number; other?: number};

/** A measurement: the data folder is the sum of its parts; no volume and no limit unless asked. */
function usage(parts: Parts = {}, extra: Partial<InstanceStorage> = {}): InstanceStorage {
    const database_bytes = parts.database ?? 0;
    const uploads_bytes = parts.uploads ?? 0;
    const broker_reports_bytes = parts.brokerReports ?? 0;
    const backups_bytes = parts.backups ?? 0;
    const other_bytes = parts.other ?? 0;
    return {
        database_bytes,
        uploads_bytes,
        broker_reports_bytes,
        backups_bytes,
        other_bytes,
        data_bytes: database_bytes + uploads_bytes + broker_reports_bytes + backups_bytes + other_bytes,
        volume_total_bytes: null,
        volume_used_bytes: null,
        volume_free_bytes: null,
        limit_mb: null,
        limit_locked: false,
        ...extra,
    } as InstanceStorage;
}

const disk = (total: number, used: number): Partial<InstanceStorage> => ({volume_total_bytes: total, volume_used_bytes: used, volume_free_bytes: total - used});

/** 1 GiB limit, 896 MiB used (a quarter, an eighth and half of the bar): 128 MiB free. No broker reports, no other files. */
const LIMIT_USAGE = () => usage({database: 256 * MiB, uploads: 128 * MiB, backups: 512 * MiB}, {limit_mb: 1024});
/** A 10 GiB disk, 6 GiB taken: LibreFolio's 3.5 GiB, 2.5 GiB of other files, 4 GiB free. */
const VOLUME_USAGE = () => usage({database: 1024 * MiB, uploads: 512 * MiB, backups: 2048 * MiB}, disk(10 * GiB, 6 * GiB));
/** No limit and no volume: only the data folder is known. */
const DATA_USAGE = () => usage({database: 25 * MiB, uploads: 25 * MiB, backups: 50 * MiB});
/** 150 MiB in a 100 MiB limit. */
const OVER_USAGE = () => usage({database: 90 * MiB, backups: 60 * MiB}, {limit_mb: 100});

/** A request the server answered with an error status: axios rejects with the response. */
function answered(status: number, data: unknown) {
    return {isAxiosError: true, name: 'AxiosError', message: `Request failed with status code ${status}`, response: {status, data}};
}
const noAnswer = () => ({isAxiosError: true, name: 'AxiosError', message: 'Network Error', code: 'ERR_NETWORK', response: undefined});
const lockedByEnv = () => answered(409, {detail: {error_code: 'SETTING_LOCKED_BY_ENV', message: 'pinned', key: 'storage_limit_mb', variable: 'LIBREFOLIO_STORAGE_LIMIT_MB'}});

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

const api = {
    get: vi.mocked(getInstanceStorage),
    save: vi.mocked(saveStorageLimit),
};

// --- Helpers --------------------------------------------------------------------------------------------------------

const bar = () => screen.getByTestId('storage-bar');
const segment = (id: string) => screen.queryByTestId(`storage-segment-${id}`);
const legend = (id: string) => screen.queryByTestId(`storage-legend-${id}`);
const saveButton = () => screen.getByTestId('storage-limit-save') as HTMLButtonElement;

/** The `<input>` of the limit: the test id may sit on the input itself or on the wrapper around it. */
function limitField(): HTMLInputElement {
    const element = screen.getByTestId('storage-limit-mb');
    const input = element instanceof HTMLInputElement ? element : element.querySelector('input');
    if (!input) throw new Error('storage-limit-mb holds no input');
    return input;
}

async function typeLimit(value: string) {
    await fireEvent.input(limitField(), {target: {value}});
}

/** The ids of the drawn segments, in document order, free space left out. */
function drawnIds(): string[] {
    return [...bar().querySelectorAll('[data-testid^="storage-segment-"]')].map((element) => element.getAttribute('data-testid')!.slice('storage-segment-'.length)).filter((id) => id !== 'free');
}

/** What `notify()` recorded, in order; only the events called `name` when it is given. */
function events(name?: string) {
    return vi
        .mocked(notify)
        .mock.calls.map(([options]) => options)
        .filter((options) => name === undefined || options.name === name);
}

/** Mount the bar with the server answering `answer`, and wait for the read to land. */
async function mountReady(answer: InstanceStorage) {
    api.get.mockResolvedValueOnce(answer);
    const StorageBar = await loadBar();
    const view = render(StorageBar);
    await waitFor(() => expect(bar()).toHaveAttribute('data-state', 'ready'));
    return view;
}

// The first import of the component is slower than a case's own 5 s on a loaded machine. It is done once, here.
// A component that does not exist yet must fail each case on its own, not the warm-up: the error is left to the cases.
beforeAll(async () => {
    await loadBar().catch(() => undefined);
}, 120_000);

beforeEach(() => {
    api.get.mockReset();
    api.save.mockReset();
    vi.mocked(notify).mockReset();
});

afterEach(() => {
    cleanup();
});

// =====================================================================================================================
describe('StorageBar — reading', () => {
    it('loading: busy, no segment yet; ready with the usage once the read lands', async () => {
        const answer = deferred<InstanceStorage>();
        api.get.mockReturnValueOnce(answer.promise);
        const StorageBar = await loadBar();
        render(StorageBar);

        expect(bar()).toHaveAttribute('data-state', 'loading');
        expect(bar()).toHaveAttribute('data-busy', 'true');
        expect(bar()).toHaveAttribute('aria-busy', 'true');
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(drawnIds()).toEqual([]);
        expect(screen.queryByTestId('storage-error')).toBeNull();

        answer.resolve(LIMIT_USAGE());
        await waitFor(() => expect(bar()).toHaveAttribute('data-state', 'ready'));

        expect(bar()).toHaveAttribute('data-busy', 'false');
        expect(bar()).toHaveAttribute('aria-busy', 'false');
        expect(drawnIds()).toEqual(['database', 'uploads', 'backups']);
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.save).not.toHaveBeenCalled();
    });

    it.each<[string, () => InstanceStorage, string]>([
        ['a limit', LIMIT_USAGE, 'limit'],
        ['no limit and a known disk', VOLUME_USAGE, 'volume'],
        ['no limit and no disk', DATA_USAGE, 'data'],
    ])('%s: data-mode %s', async (_case, make, mode) => {
        await mountReady(make());

        expect(bar()).toHaveAttribute('data-mode', mode);
    });

    it('has a track that holds the segments', async () => {
        await mountReady(LIMIT_USAGE());

        const track = screen.getByTestId('storage-bar-track');
        for (const id of ['database', 'uploads', 'backups']) expect(within(track).getByTestId(`storage-segment-${id}`)).toBeInTheDocument();
    });
});

// =====================================================================================================================
describe('StorageBar — the segments', () => {
    it('limit mode: one segment per non-empty part, in order, each with its bytes and its share of the bar as a width', async () => {
        await mountReady(LIMIT_USAGE());

        expect(drawnIds()).toEqual(['database', 'uploads', 'backups']);
        expect(segment('database')).toHaveAttribute('data-bytes', String(256 * MiB));
        expect(segment('uploads')).toHaveAttribute('data-bytes', String(128 * MiB));
        expect(segment('backups')).toHaveAttribute('data-bytes', String(512 * MiB));
        expect((segment('database') as HTMLElement).style.width).toBe('25%');
        expect((segment('uploads') as HTMLElement).style.width).toBe('12.5%');
        expect((segment('backups') as HTMLElement).style.width).toBe('50%');
    });

    it('a part of 0 bytes has no segment, and no disk is drawn against a limit', async () => {
        await mountReady({...LIMIT_USAGE(), ...disk(10 * GiB, 6 * GiB)});

        expect(segment('brokerReports')).toBeNull();
        expect(segment('dataOther')).toBeNull();
        expect(segment('disk')).toBeNull();
    });

    it('the five parts of a full folder come out in the order database, uploads, brokerReports, backups, dataOther', async () => {
        await mountReady(usage({database: 100 * MiB, uploads: 50 * MiB, brokerReports: 20 * MiB, backups: 70 * MiB, other: 10 * MiB}, {limit_mb: 1024}));

        expect(drawnIds()).toEqual(['database', 'uploads', 'brokerReports', 'backups', 'dataOther']);
        expect(segment('dataOther')).toHaveAttribute('data-bytes', String(10 * MiB));
    });

    it('volume mode: the parts, then the other files of the disk', async () => {
        await mountReady(VOLUME_USAGE());

        expect(drawnIds()).toEqual(['database', 'uploads', 'backups', 'disk']);
        expect(segment('disk')).toHaveAttribute('data-bytes', String(2560 * MiB));
        expect((segment('database') as HTMLElement).style.width).toBe('10%');
        expect((segment('disk') as HTMLElement).style.width).toBe('25%');
    });

    it('data mode: the parts against the data folder, no disk', async () => {
        await mountReady(DATA_USAGE());

        expect(drawnIds()).toEqual(['database', 'uploads', 'backups']);
        expect(segment('disk')).toBeNull();
        expect((segment('backups') as HTMLElement).style.width).toBe('50%');
    });

    it('the free space is a segment of its own, after the parts', async () => {
        await mountReady(LIMIT_USAGE());

        const free = screen.getByTestId('storage-segment-free');
        const last = segment('backups') as HTMLElement;
        expect(free.compareDocumentPosition(last) & Node.DOCUMENT_POSITION_PRECEDING, 'free comes after the last part').toBeTruthy();
    });

    it('the free space carries its bytes: what is left of the limit', async () => {
        await mountReady(LIMIT_USAGE());

        expect(screen.getByTestId('storage-segment-free')).toHaveAttribute('data-bytes', String(128 * MiB));
    });

    it('the free space of a disk carries what the volume reports free', async () => {
        await mountReady(VOLUME_USAGE());

        expect(screen.getByTestId('storage-segment-free')).toHaveAttribute('data-bytes', String(4 * GiB));
    });
});

// =====================================================================================================================
describe('StorageBar — the legend and the summary', () => {
    it('a row per drawn segment and one for the free space, named by key and sized through formatBytes', async () => {
        await mountReady(LIMIT_USAGE());

        const sizes: Record<string, number> = {database: 256 * MiB, uploads: 128 * MiB, backups: 512 * MiB, free: 128 * MiB};
        for (const [id, bytes] of Object.entries(sizes)) {
            const row = screen.getByTestId(`storage-legend-${id}`);
            expect(row, `the row of ${id}`).toHaveTextContent(`storage.parts.${id}`);
            expect(row, `the size of ${id}`).toHaveTextContent(formatBytes(bytes));
        }
    });

    it('no row for a part that is not drawn', async () => {
        await mountReady(LIMIT_USAGE());

        expect(legend('brokerReports')).toBeNull();
        expect(legend('dataOther')).toBeNull();
        expect(legend('disk')).toBeNull();
    });

    it('volume mode: a row for the other files of the disk', async () => {
        await mountReady(VOLUME_USAGE());

        expect(screen.getByTestId('storage-legend-disk')).toHaveTextContent('storage.parts.disk');
        expect(screen.getByTestId('storage-legend-disk')).toHaveTextContent(formatBytes(2560 * MiB));
        expect(screen.getByTestId('storage-legend-free')).toHaveTextContent(formatBytes(4 * GiB));
    });

    it('limit mode: the summary is storage.summary.limit, with the used size and the limit', async () => {
        await mountReady(LIMIT_USAGE());

        const summary = screen.getByTestId('storage-summary');
        expect(summary).toHaveTextContent('storage.summary.limit');
        expect(summary).not.toHaveTextContent('storage.summary.volume');
        expect(summary).not.toHaveTextContent('storage.summary.data');
        expect(summary).toHaveTextContent(formatBytes(896 * MiB));
        expect(summary).toHaveTextContent(formatBytes(GiB));
    });

    it('volume mode: the summary is storage.summary.volume, with the size of LibreFolio’s files and the size of the disk', async () => {
        await mountReady(VOLUME_USAGE());

        const summary = screen.getByTestId('storage-summary');
        expect(summary).toHaveTextContent('storage.summary.volume');
        expect(summary).not.toHaveTextContent('storage.summary.limit');
        expect(summary).not.toHaveTextContent('storage.summary.data');
        // LibreFolio's own files: the data folder (3584 MiB), not the whole used part of the disk.
        expect(summary).toHaveTextContent(formatBytes(3584 * MiB));
        expect(summary).toHaveTextContent(formatBytes(10 * GiB));
    });

    it('data mode: the summary is storage.summary.data, with the size of the data folder', async () => {
        await mountReady(DATA_USAGE());

        const summary = screen.getByTestId('storage-summary');
        expect(summary).toHaveTextContent('storage.summary.data');
        expect(summary).not.toHaveTextContent('storage.summary.limit');
        expect(summary).not.toHaveTextContent('storage.summary.volume');
        expect(summary).toHaveTextContent(formatBytes(100 * MiB));
    });
});

// =====================================================================================================================
describe('StorageBar — over the limit', () => {
    it('the data folder bigger than the limit: the warning is shown, by key', async () => {
        await mountReady(OVER_USAGE());

        expect(bar()).toHaveAttribute('data-mode', 'limit');
        expect(screen.getByTestId('storage-over-limit')).toHaveTextContent('storage.overLimit');
    });

    it.each<[string, () => InstanceStorage]>([
        ['under the limit', LIMIT_USAGE],
        ['exactly at the limit', () => usage({database: 60 * MiB, backups: 40 * MiB}, {limit_mb: 100})],
        ['a lot of data and no limit (volume mode)', () => usage({database: 8 * GiB}, disk(10 * GiB, 9 * GiB))],
        ['a lot of data and no limit (data mode)', () => usage({database: 8 * GiB})],
    ])('%s: no warning', async (_case, make) => {
        await mountReady(make());

        expect(screen.queryByTestId('storage-over-limit')).toBeNull();
    });
});

// =====================================================================================================================
describe('StorageBar — a read that fails', () => {
    it.each<[string, string, () => unknown]>([
        ['no answer', 'network', noAnswer],
        ['a 500 with no code', 'unexpected', () => answered(500, {detail: 'Internal Server Error'})],
    ])('%s: error state, the code on storage-error, a retry; nothing drawn', async (_case, code, failure) => {
        api.get.mockRejectedValueOnce(failure());
        const StorageBar = await loadBar();
        render(StorageBar);

        await waitFor(() => expect(bar()).toHaveAttribute('data-state', 'error'));

        expect(bar()).toHaveAttribute('data-busy', 'false');
        const error = screen.getByTestId('storage-error');
        expect(error).toHaveAttribute('data-error-code', code);
        expect(error).toHaveTextContent('storage.errors.load');
        expect(screen.getByTestId('storage-retry')).toBeEnabled();
        expect(drawnIds()).toEqual([]);
    });

    it('retry reads again; the usage that comes is drawn and the error is gone', async () => {
        api.get.mockRejectedValueOnce(noAnswer());
        const StorageBar = await loadBar();
        render(StorageBar);
        await waitFor(() => expect(bar()).toHaveAttribute('data-state', 'error'));
        api.get.mockResolvedValueOnce(LIMIT_USAGE());

        await fireEvent.click(screen.getByTestId('storage-retry'));

        await waitFor(() => expect(bar()).toHaveAttribute('data-state', 'ready'));
        expect(api.get).toHaveBeenCalledTimes(2);
        expect(screen.queryByTestId('storage-error')).toBeNull();
        expect(screen.queryByTestId('storage-retry')).toBeNull();
        expect(drawnIds()).toEqual(['database', 'uploads', 'backups']);
    });
});

// =====================================================================================================================
describe('StorageBar — reading again', () => {
    it('reads again at every change of the signal, and draws the new usage', async () => {
        await mountReady(LIMIT_USAGE());
        expect(api.get).toHaveBeenCalledTimes(1);
        // A backup has just been made: 64 MiB more of backups.
        api.get.mockResolvedValueOnce(usage({database: 256 * MiB, uploads: 128 * MiB, backups: 576 * MiB}, {limit_mb: 1024}));

        notifyBackupListChanged();

        await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
        await waitFor(() => expect(segment('backups')).toHaveAttribute('data-bytes', String(576 * MiB)));
        expect(bar()).toHaveAttribute('data-state', 'ready');
        expect(bar()).toHaveAttribute('data-busy', 'false');
    });

    it('a second change reads a second time', async () => {
        await mountReady(LIMIT_USAGE());
        api.get.mockResolvedValue(LIMIT_USAGE());

        notifyBackupListChanged();
        await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
        notifyBackupListChanged();
        await waitFor(() => expect(api.get).toHaveBeenCalledTimes(3));
    });

    it('the mode follows the new usage: a limit that appears turns a volume bar into a limit bar', async () => {
        await mountReady(VOLUME_USAGE());
        expect(bar()).toHaveAttribute('data-mode', 'volume');
        api.get.mockResolvedValueOnce({...VOLUME_USAGE(), limit_mb: 8192});

        notifyBackupListChanged();

        await waitFor(() => expect(bar()).toHaveAttribute('data-mode', 'limit'));
        expect(segment('disk')).toBeNull();
    });
});

// =====================================================================================================================
describe('StorageBar — the limit editor: reading and the save button', () => {
    it('the field starts at the limit in force, and there is nothing to save', async () => {
        await mountReady(LIMIT_USAGE());

        expect(limitField().value).toBe('1024');
        expect(limitField()).toBeEnabled();
        expect(saveButton()).toBeDisabled();
        expect(screen.queryByTestId('storage-limit-locked')).toBeNull();
        expect(screen.queryByTestId('storage-limit-error')).toBeNull();
    });

    it('no limit is shown as 0', async () => {
        await mountReady(VOLUME_USAGE());

        expect(limitField().value).toBe('0');
        expect(saveButton()).toBeDisabled();
    });

    it('is on after a change, off again when the change is undone', async () => {
        await mountReady(LIMIT_USAGE());

        await typeLimit('2048');
        expect(saveButton()).toBeEnabled();

        await typeLimit('1024');
        expect(saveButton()).toBeDisabled();
    });

    it.each<[string, string]>([
        ['an empty value', ''],
        ['a negative number', '-1'],
        ['a decimal number', '1.5'],
    ])('is off for %s, though it differs from the limit in force', async (_case, value) => {
        await mountReady(LIMIT_USAGE());

        await typeLimit(value);

        expect(saveButton()).toBeDisabled();
        await fireEvent.click(saveButton());
        expect(api.save).not.toHaveBeenCalled();
    });

    it('back to a valid value, it is on again', async () => {
        await mountReady(LIMIT_USAGE());
        await typeLimit('-1');
        expect(saveButton()).toBeDisabled();

        await typeLimit('4096');

        expect(saveButton()).toBeEnabled();
    });

    it('0 is a valid value: it is how the limit is taken away', async () => {
        await mountReady(LIMIT_USAGE());

        await typeLimit('0');

        expect(saveButton()).toBeEnabled();
    });
});

// =====================================================================================================================
describe('StorageBar — the limit editor: saving', () => {
    it('one request with the number; no second while it is out; then the event, and the bar read again with the new limit', async () => {
        await mountReady(LIMIT_USAGE());
        const answer = deferred<void>();
        api.save.mockReturnValueOnce(answer.promise);
        api.get.mockResolvedValue(usage({database: 256 * MiB, uploads: 128 * MiB, backups: 512 * MiB}, {limit_mb: 2048}));
        await typeLimit('2048');

        await fireEvent.click(saveButton());

        expect(api.save).toHaveBeenCalledTimes(1);
        expect(api.save).toHaveBeenCalledWith(2048);
        await waitFor(() => expect(saveButton()).toBeDisabled());
        await fireEvent.click(saveButton());
        expect(api.save, 'a save in flight is not sent twice').toHaveBeenCalledTimes(1);
        expect(events('storage.limit.saved')).toEqual([]);

        answer.resolve();

        await waitFor(() => expect(events('storage.limit.saved')).toHaveLength(1));
        expect(events('storage.limit.saved')[0].detail).toEqual({limit_mb: 2048});
        await waitFor(() => expect(api.get.mock.calls.length).toBeGreaterThanOrEqual(2));
        await waitFor(() => expect(limitField().value).toBe('2048'));
        expect(bar()).toHaveAttribute('data-mode', 'limit');
        expect(saveButton(), 'the saved value is the limit in force: nothing differs').toBeDisabled();
        expect(screen.queryByTestId('storage-limit-error')).toBeNull();
    });

    it('taking the limit away is a save of 0, and the bar leaves limit mode', async () => {
        await mountReady(LIMIT_USAGE());
        api.save.mockResolvedValueOnce(undefined);
        api.get.mockResolvedValue(usage({database: 256 * MiB, uploads: 128 * MiB, backups: 512 * MiB}));
        await typeLimit('0');

        await fireEvent.click(saveButton());

        await waitFor(() => expect(api.save).toHaveBeenCalledWith(0));
        await waitFor(() => expect(events('storage.limit.saved')).toHaveLength(1));
        expect(events('storage.limit.saved')[0].detail).toEqual({limit_mb: 0});
        await waitFor(() => expect(bar()).toHaveAttribute('data-mode', 'data'));
        expect(limitField().value).toBe('0');
    });

    it('a new change after a save makes the button available again', async () => {
        await mountReady(LIMIT_USAGE());
        api.save.mockResolvedValueOnce(undefined);
        api.get.mockResolvedValue(usage({database: 256 * MiB}, {limit_mb: 2048}));
        await typeLimit('2048');
        await fireEvent.click(saveButton());
        await waitFor(() => expect(events('storage.limit.saved')).toHaveLength(1));
        await waitFor(() => expect(saveButton()).toBeDisabled());

        await typeLimit('4096');

        expect(saveButton()).toBeEnabled();
    });
});

// =====================================================================================================================
describe('StorageBar — the limit editor: a refused save', () => {
    it.each<[string, string, () => unknown]>([
        ['a 422', 'invalid', () => answered(422, {detail: 'Invalid value for storage_limit_mb'})],
        ['a 403', 'forbidden', () => answered(403, {detail: 'Admin required'})],
        ['a 409 SETTING_LOCKED_BY_ENV', 'locked', lockedByEnv],
        ['no answer', 'network', noAnswer],
        ['a 500', 'unexpected', () => answered(500, {detail: 'Internal Server Error'})],
    ])('%s: error %s on storage-limit-error, its sentence by key, nothing announced as saved, the value kept', async (_case, code, refused) => {
        await mountReady(LIMIT_USAGE());
        api.save.mockRejectedValueOnce(refused());
        await typeLimit('2048');

        await fireEvent.click(saveButton());

        const error = await screen.findByTestId('storage-limit-error');
        expect(error).toHaveAttribute('data-error-code', code);
        expect(error).toHaveTextContent(`storage.limit.errors.${code}`);
        expect(events('storage.limit.saved')).toEqual([]);
        expect(limitField().value, 'what the user typed stays').toBe('2048');
        expect(saveButton(), 'the value is still unsaved: it can be sent again').toBeEnabled();
        expect(screen.queryByTestId('storage-error'), 'a refused save is not a failed read').toBeNull();
        expect(bar(), 'the bar is still drawn').toHaveAttribute('data-mode', 'limit');
    });

    it('sent again after a refusal, it can succeed: the error is gone', async () => {
        await mountReady(LIMIT_USAGE());
        api.save.mockRejectedValueOnce(noAnswer());
        api.save.mockResolvedValueOnce(undefined);
        api.get.mockResolvedValue(usage({database: 256 * MiB}, {limit_mb: 2048}));
        await typeLimit('2048');
        await fireEvent.click(saveButton());
        await screen.findByTestId('storage-limit-error');

        await fireEvent.click(saveButton());

        await waitFor(() => expect(events('storage.limit.saved')).toHaveLength(1));
        await waitFor(() => expect(screen.queryByTestId('storage-limit-error')).toBeNull());
        expect(api.save).toHaveBeenCalledTimes(2);
    });
});

// =====================================================================================================================
describe('StorageBar — the limit editor: pinned by the environment', () => {
    it.each<[string, number | null]>([
        ['a limit', 512],
        ['no limit (the variable says 0)', null],
    ])('limit_locked with %s: the field is disabled, the line says who decides, nothing can be saved', async (_case, limit) => {
        await mountReady(usage({database: 100 * MiB}, {limit_mb: limit, limit_locked: true}));

        expect(limitField()).toBeDisabled();
        expect(limitField().value).toBe(String(limit ?? 0));
        expect(screen.getByTestId('storage-limit-locked')).toHaveTextContent('storage.limit.locked');
        expect(saveButton()).toBeDisabled();

        await typeLimit('9999');
        await fireEvent.click(saveButton());
        expect(api.save, 'a pinned limit is never sent').not.toHaveBeenCalled();
    });

    it('not pinned: the field is enabled and the line is not there', async () => {
        await mountReady(LIMIT_USAGE());

        expect(limitField()).toBeEnabled();
        expect(screen.queryByTestId('storage-limit-locked')).toBeNull();
    });

    it('the bar of a pinned limit is still drawn against it', async () => {
        await mountReady(usage({database: 100 * MiB}, {limit_mb: 512, limit_locked: true}));

        expect(bar()).toHaveAttribute('data-mode', 'limit');
        expect(segment('database')).toHaveAttribute('data-bytes', String(100 * MiB));
    });
});

// =====================================================================================================================
// K-2 (developer, 05/11) — pointing at the bar lights the legend row, and the other way round
// =====================================================================================================================
describe('StorageBar — the bar and its legend are linked (K-2)', () => {
    const active = (id: string) => [segment(id)?.getAttribute('data-active'), legend(id)?.getAttribute('data-active')];

    it('pointing at a segment lights its legend row and dims the other segments; leaving puts everything back', async () => {
        await mountReady(LIMIT_USAGE());
        expect(active('backups'), 'nothing lit before the pointer arrives').toEqual(['false', 'false']);

        await fireEvent.pointerEnter(segment('backups')!);
        expect(active('backups')).toEqual(['true', 'true']);
        expect(active('database'), 'the others stay unlit').toEqual(['false', 'false']);

        await fireEvent.pointerLeave(segment('backups')!);
        expect(active('backups')).toEqual(['false', 'false']);
    });

    it('pointing at a legend row lights its segment, the free space included', async () => {
        await mountReady(LIMIT_USAGE());

        await fireEvent.pointerEnter(legend('free')!);
        expect(active('free')).toEqual(['true', 'true']);
        await fireEvent.pointerLeave(legend('free')!);
        expect(active('free')).toEqual(['false', 'false']);
    });

    it('focus inside a legend row counts as pointing at it', async () => {
        await mountReady(LIMIT_USAGE());

        await fireEvent.focusIn(legend('uploads')!);
        expect(active('uploads')).toEqual(['true', 'true']);
        await fireEvent.focusOut(legend('uploads')!);
        expect(active('uploads')).toEqual(['false', 'false']);
    });
});
