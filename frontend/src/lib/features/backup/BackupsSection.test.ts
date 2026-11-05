// @vitest-environment jsdom
/**
 * BackupsSection — component test (Vitest + jsdom), lot FB-24, written red first against
 * `B6r-fb24-frontend-interface.md` §5.
 *
 * The section that holds what the instance keeps of its backups: a warning, the table (`BackupList`) and the clean-up
 * settings (`BackupCleanupPanel`). The Backup tab of Settings mounts it foldable, under the backup card; the Files page
 * mounts it whole, as the content of its Backups tab.
 *
 * What this file pins:
 *   - the root `backups-section` publishes `data-open="true|false"`;
 *   - `collapsible` (the default) gives a button `backups-section-toggle` with `aria-expanded` that opens and closes the
 *     body; closed, the body is NOT in the DOM (so the list is not even read);
 *   - the body, once open: `backup-same-disk-notice` (`backup.list.sameDisk` — a copy on the same disk as the data is
 *     no backup: download the file and keep it elsewhere), then the list (`backup-list`) and the clean-up settings
 *     (`backup-cleanup`);
 *   - `defaultOpen` (default `true`) is the state of a section that has never been folded or opened;
 *   - the state is remembered in the user's storage under `backupsSection_open` (`setUserStorage`), read when the section
 *     mounts: a section closed by the user is closed on the next visit;
 *   - `collapsible={false}` has no toggle and is always open — whatever the storage remembers of a foldable one.
 *
 * The seams. `$lib/i18n` is an identity translator. `./backupApi` swaps the requests of the children for `vi.fn` (an
 * empty list, a clean-up of 0 and 0), `$lib/api` throws on any request. `$lib/utils/storage` is an in-memory store of
 * its own, emptied around every case, so that «remembered» is a round trip (fold, leave, come back) and the format of the
 * stored value is not part of the contract. The children are the real ones: the section is asserted through their root
 * test ids.
 *
 * Each case loads the component inside itself, so that while it does not exist each case fails on its own.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';

// --- Mocks ----------------------------------------------------------------------------------------------------------

vi.mock('$lib/i18n', () => {
    const identity = readable((key: string) => key);
    return {
        _: identity,
        t: identity,
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
                          throw new Error(`BackupsSection.test: a request went through zodiosApi.${alias}`);
                      },
        },
    );
    return {zodiosApi, schemas: {}, axiosInstance: {}, ApiError: class ApiError extends Error {}};
});

vi.mock('./backupApi', async () => {
    const actual = await vi.importActual<typeof import('./backupApi')>('./backupApi');
    return {
        ...actual,
        listInstanceBackups: vi.fn(() => Promise.resolve([])),
        deleteInstanceBackupJob: vi.fn(() => Promise.resolve()),
        getCleanupSettings: vi.fn(() => Promise.resolve({maxMb: 0, maxDays: 0})),
        saveCleanupSettings: vi.fn(() => Promise.resolve()),
    };
});

vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));
vi.mock('$lib/utils/clipboard', () => ({writeTextToClipboard: vi.fn(() => Promise.resolve())}));

/** The user's storage, in memory: key → value, emptied around every case. */
const storage = vi.hoisted(() => {
    const store = new Map<string, string>();
    return {
        store,
        get: vi.fn((key: string, fallback: string) => store.get(key) ?? fallback),
        set: vi.fn((key: string, value: string) => void store.set(key, value)),
    };
});
vi.mock('$lib/utils/storage', () => ({
    getUserStorageKey: (key: string) => `backups-section-test-${key}`,
    getUserStorage: storage.get,
    setUserStorage: storage.set,
}));

const instance = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
    return {SELFHOSTED, box: reactiveBox<{config: InstanceConfig}>({config: SELFHOSTED})};
});
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: instance.SELFHOSTED,
    instanceConfig: {
        get config() {
            return instance.box.config;
        },
        get loaded() {
            return true;
        },
        get failed() {
            return false;
        },
        load: vi.fn(() => Promise.resolve()),
    },
}));

import {listInstanceBackups} from './backupApi';

// A literal path would fail the whole file at transform time while the module is missing; a variable path fails each case alone.
const MODULES = {section: './BackupsSection.svelte'};
const loadSection = async () => (await import(/* @vite-ignore */ MODULES.section)).default;

// --- Helpers --------------------------------------------------------------------------------------------------------

const section = () => screen.getByTestId('backups-section');
const toggle = () => screen.getByTestId('backups-section-toggle');

/** Every test id of the body, which a closed section must not have in the DOM. */
const BODY = ['backup-same-disk-notice', 'backup-list', 'backup-cleanup'] as const;

function expectBody(present: boolean) {
    for (const testId of BODY) {
        if (present) expect(screen.getByTestId(testId), `${testId} in an open section`).toBeInTheDocument();
        else expect(screen.queryByTestId(testId), `${testId} in a closed section`).toBeNull();
    }
}

type Props = {collapsible?: boolean; defaultOpen?: boolean};

async function mount(props: Props = {}) {
    const Section = await loadSection();
    return render(Section, {props});
}

// The first import of the section pulls in the whole DataTable: slower than a case's own 5 s on a loaded machine. It is done once, here.
beforeAll(async () => {
    await loadSection();
}, 120_000);

beforeEach(() => {
    storage.store.clear();
    storage.get.mockClear();
    storage.set.mockClear();
    vi.mocked(listInstanceBackups).mockClear();
});

afterEach(() => {
    cleanup();
});

// =====================================================================================================================
describe('BackupsSection — foldable (the default)', () => {
    it('starts open: the toggle says so, and the body is the warning, the list and the clean-up settings', async () => {
        await mount();

        expect(section()).toHaveAttribute('data-open', 'true');
        expect(toggle()).toHaveAttribute('aria-expanded', 'true');
        expectBody(true);
        expect(screen.getByTestId('backup-same-disk-notice')).toHaveTextContent('backup.list.sameDisk');
        // K-9: a reminder, not a warning: the info colours.
        expect(screen.getByTestId('backup-same-disk-notice')).toHaveAttribute('data-variant', 'info');
        expect(screen.getByTestId('backup-same-disk-notice').className).toContain('bg-lf-info-soft');
        expect(screen.getByTestId('backup-same-disk-notice').className).not.toContain('warning');
    });

    it('the toggle is a button', async () => {
        await mount();

        expect(toggle().tagName).toBe('BUTTON');
    });

    it('the toggle closes it: data-open false, aria-expanded false, the body gone from the DOM, the toggle still there', async () => {
        await mount();

        await fireEvent.click(toggle());

        expect(section()).toHaveAttribute('data-open', 'false');
        expect(toggle()).toHaveAttribute('aria-expanded', 'false');
        expectBody(false);
    });

    it('the toggle opens it again: the body is back', async () => {
        await mount();
        await fireEvent.click(toggle());
        expectBody(false);

        await fireEvent.click(toggle());

        expect(section()).toHaveAttribute('data-open', 'true');
        expect(toggle()).toHaveAttribute('aria-expanded', 'true');
        expectBody(true);
    });

    it('the list is read while the section is open', async () => {
        await mount();

        await waitFor(() => expect(listInstanceBackups).toHaveBeenCalled());
    });
});

// =====================================================================================================================
describe('BackupsSection — remembered', () => {
    it('folding stores the state under backupsSection_open', async () => {
        await mount();

        await fireEvent.click(toggle());

        expect(storage.set).toHaveBeenCalled();
        expect(storage.set.mock.calls.every(([key]) => key === 'backupsSection_open')).toBe(true);
    });

    it('a section the user closed is closed on the next visit, and its list is not even read', async () => {
        const first = await mount();
        await fireEvent.click(toggle());
        first.unmount();
        vi.mocked(listInstanceBackups).mockClear();

        await mount();

        await waitFor(() => expect(section()).toHaveAttribute('data-open', 'false'));
        expect(toggle()).toHaveAttribute('aria-expanded', 'false');
        expectBody(false);
        expect(listInstanceBackups, 'a closed section has no list to read').not.toHaveBeenCalled();
        expect(storage.get).toHaveBeenCalledWith('backupsSection_open', expect.anything());
    });

    it('a section the user closed and opened again is open on the next visit', async () => {
        const first = await mount();
        await fireEvent.click(toggle());
        await fireEvent.click(toggle());
        first.unmount();

        await mount();

        await waitFor(() => expect(section()).toHaveAttribute('data-open', 'true'));
        expectBody(true);
    });

    it('defaultOpen={false} is the state of a section nobody ever opened: closed', async () => {
        await mount({defaultOpen: false});

        expect(section()).toHaveAttribute('data-open', 'false');
        expect(toggle()).toHaveAttribute('aria-expanded', 'false');
        expectBody(false);
    });

    it('defaultOpen={false}: opened by the user, it is open on the next visit (the user’s choice wins)', async () => {
        const first = await mount({defaultOpen: false});
        await fireEvent.click(toggle());
        expectBody(true);
        first.unmount();

        await mount({defaultOpen: false});

        await waitFor(() => expect(section()).toHaveAttribute('data-open', 'true'));
        expectBody(true);
    });
});

// =====================================================================================================================
describe('BackupsSection — not foldable', () => {
    it('collapsible={false}: always open, no toggle, the whole body', async () => {
        await mount({collapsible: false});

        expect(section()).toHaveAttribute('data-open', 'true');
        expect(screen.queryByTestId('backups-section-toggle')).toBeNull();
        expectBody(true);
        expect(screen.getByTestId('backup-same-disk-notice')).toHaveTextContent('backup.list.sameDisk');
    });

    it('collapsible={false} stays open whatever a foldable section was left as', async () => {
        const foldable = await mount();
        await fireEvent.click(toggle());
        expectBody(false);
        foldable.unmount();

        await mount({collapsible: false});

        expect(section()).toHaveAttribute('data-open', 'true');
        expect(screen.queryByTestId('backups-section-toggle')).toBeNull();
        expectBody(true);
    });
});
