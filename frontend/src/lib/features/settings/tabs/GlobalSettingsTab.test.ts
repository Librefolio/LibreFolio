// @vitest-environment jsdom
/**
 * GlobalSettingsTab — component test (Vitest + jsdom).
 *
 * The administrator surface: the instance-wide settings, behind a lock, behind an
 * `canEdit` capability, saved one at a time or in bulk through a single bulk
 * PATCH.
 *
 * Why a component test and not an E2E. Three of the four things this tab exists to
 * do are only visible when something goes wrong or when the caller is not an
 * administrator: the 403 → "admin required" translation, the lock's confirm-then-
 * discard, and the difference between the read-only badge and the lock button.
 * Reaching those from a browser means logging in as two different users and
 * getting the server to refuse a PATCH on cue; here `canEdit` is a prop and the
 * refusal is one `mockRejectedValue`. The list itself is server-driven — the tab
 * renders whatever `list_global_settings` returns — so a component test can also
 * choose the *shape* of that list, which is how the `value_type` dispatch and the
 * scheduler-key hiding become testable at all.
 *
 * On the translator. `$lib/i18n` is mocked with a *dictionary*, not the identity
 * used elsewhere in this suite, because four helpers here are built on
 * `localized !== key ? localized : fallback`: with a pure identity translator only
 * the fallback arm could ever run, and the tab's whole labelling story would go
 * untested. The dictionary is owned by this file and deliberately partial, so both
 * arms are reachable. Assertions therefore name either a key (untranslated) or a
 * value this file put in the dictionary — never a phrase from the product
 * catalogue. One block reads the real catalogues, for whether a key is there and
 * never for its wording: "every row it renders is named in the four catalogues".
 *
 * What it deliberately does NOT assert:
 *   - `SettingToggle` / `SettingNumber` internals — another lane owns them; here
 *     they are driven through their public affordances (the switch, the number
 *     box) and only the tab's reaction is asserted.
 *   - the scheduler modals' contents. Opening them is asserted, their behaviour is
 *     their own.
 *   - clickOutside's detection algorithm. The Runes cases below exercise only
 *     this tab's listener lifetime and its bound mobile dropdown reference.
 *
 * Accounts lot A5b (plan A5b.1). A5a replaced the bool `enable_registration`
 * with `registration_mode` — `open`, `invite` or `disabled`, a string setting —
 * and the security category now holds it: the rows that used the old key as
 * "a bool of the security category" moved to `scheduler_enabled` (a bool) or to
 * `registration_mode` (the security row). Its own describe pins the row: a
 * `SettingSelect` of the three modes in `global-setting-registration_mode`, and
 * the case where `LIBREFOLIO_REGISTRATION` pins the mode on the server
 * (`instanceConfig.config.accounts.registration_locked`): the control locked on
 * the mode in force, the hint `settings.lockedByEnv`, `data-locked="true"` on
 * the row, «reset all» passing it by, the 409 `SETTING_LOCKED_BY_ENV` worded by
 * that key with its variable, and `instanceConfig.load({force: true})` after a
 * save that wrote the mode. `$lib/features/instance/instanceConfig.svelte` is a
 * fake with the real store's shape — enumerable getters over `$state`
 * (`reactiveBox`) and a `load` spy — unpinned and open before every test.
 * Accounts lot A6d (decision 36) moves the mode's default to `invite`, the
 * backend's for a new install: the row's reset and «reset all» propose it, and
 * the cases that need a row off the default store `open`.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {get, readable, writable, type Writable} from 'svelte/store';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

// --- Mocks --------------------------------------------------------------

/**
 * A partial catalogue. A key that is present translates; a key that is absent
 * comes back unchanged, which is exactly what the `localized !== key` helpers
 * treat as "no translation, use the fallback".
 */
const DICT: Record<string, string> = {
    'settings.globalSettingNames.scheduler_enabled': 'Market data sync',
    'settings.globalSettingNames.session_ttl_hours': 'Session lifetime',
    'settings.globalSettingDescriptions.session_ttl_hours': 'How long a login lasts',
    'settings.globalSettingUnits.session_ttl_hours': 'hours',
    'settings.globalSettingCategories.session': 'Session',
    'settings.defaultCurrency': 'Default currency',
    'settings.security': 'Security',
    'settings.all': 'All',
    'common.other': 'Other',
};

vi.mock('$lib/i18n', () => {
    const dictionary = writable((key: string) => DICT[key] ?? key);
    return {
        _: dictionary,
        t: dictionary,
        locale: writable('en'),
        date: readable((v: unknown) => String(v)),
        time: readable((v: unknown) => String(v)),
        number: readable((v: unknown) => String(v)),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT'},
        LANGUAGE_OPTIONS: [
            {code: 'en', name: 'English', flag: 'EN'},
            {code: 'it', name: 'Italiano', flag: 'IT'},
        ],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

// Independent stores let a regression distinguish the explicit locale dependency
// from a translator replacement; changing both at once would hide either gap.
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));

const axiosGet = vi.fn(async (_url: string) => ({data: null}) as {data: unknown});
const axiosPatch = vi.fn(async (_url: string, _body?: unknown) => ({data: null}) as {data: unknown});
vi.mock('$lib/api', () => {
    const cache = new Map<string, unknown>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                // `axios` is not an endpoint: the tab reaches through it for the two
                // routes zodios does not generate a client for.
                if (prop === 'axios') return {get: (url: string) => axiosGet(url), patch: (url: string, body?: unknown) => axiosPatch(url, body)};
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

const notify = vi.fn();
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: (...args: unknown[]) => notify(...args)}));

const setGlobalDirect = vi.fn();
vi.mock('$lib/stores/app/globalSettings', () => ({globalSettings: {setDirect: (...a: unknown[]) => setGlobalDirect(...a), subscribe: (run: (v: unknown) => void) => (run(null), () => undefined)}}));

/**
 * The public configuration of the instance (`GET /system/instance`), held by the test: the accounts part says whether
 * `LIBREFOLIO_REGISTRATION` pins the registration mode, and which mode is in force. Getters over `$state`, as in the
 * real store, so the tab re-reads them; `load` is a spy, unpinned and open before every test.
 */
const instance = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const UNPINNED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
    return {
        UNPINNED,
        box: reactiveBox<{config: InstanceConfig}>({config: UNPINNED}),
        load: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
    };
});
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: instance.UNPINNED,
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
        load: instance.load,
    },
}));

vi.mock('$lib/stores/reference/currencyStore', () => ({
    ensureCurrenciesLoaded: async () => undefined,
    getAllCurrencies: () => [
        {code: 'EUR', name: 'Euro', symbol: '€'},
        {code: 'USD', name: 'US Dollar', symbol: '$'},
    ],
    currencyStore: {subscribe: (run: (v: unknown) => void) => (run({items: [], loaded: true}), () => undefined)},
}));

import GlobalSettingsTab from './GlobalSettingsTab.svelte';
import {zodiosApi} from '$lib/api';
import {_, locale, type SupportedLocale} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import * as clickOutside from '$lib/utils/core/clickOutside';
// The real catalogues, read only by the naming invariant below: the rest of the
// file keeps its own dictionary.
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

// --- Fixtures & helpers -------------------------------------------------

type Fixture = {key: string; value: string; value_type: string; updated_at?: string | null};

const listFn = () => vi.mocked(zodiosApi.list_global_settings_api_v1_settings_global_get as never) as ReturnType<typeof vi.fn>;

const setting = (key: string, value: string, value_type = 'string', extra: Partial<Fixture> = {}): Fixture => ({key, value, value_type, updated_at: null, ...extra});
const translator = _ as unknown as Writable<(key: string) => string>;
const SCHEDULER_STATE = '/api/v1/settings/scheduler/state';
const schedulerReads = () => axiosGet.mock.calls.filter(([url]) => url === SCHEDULER_STATE);

/** An axios-shaped rejection with a status. */
function axiosError(status: number, message = `Request failed with status code ${status}`): Error {
    return Object.assign(new Error(message), {isAxiosError: true, response: {status, data: {}}});
}

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** Mount with a chosen server list, and wait for the loading gate to lift. */
async function mount(items: Fixture[], props: {canEdit?: boolean} = {}) {
    // `saveSetting` writes the new value back onto the object it was handed, so a
    // shared fixture would carry one test's save into the next. Each mount gets a
    // copy of the rows it asked for.
    listFn().mockResolvedValue({items: items.map((item) => ({...item}))} as never);
    const utils = render(GlobalSettingsTab, {props: {canEdit: true, ...props}});
    await waitFor(() => expect(screen.getByTestId('global-settings-tab')).toHaveAttribute('data-busy', 'false'));
    await waitFor(() => expect(listFn()).toHaveBeenCalled());
    return utils;
}

const lockToggle = () => screen.getByTestId('settings-lock-toggle');

/** Mount, then unlock, so the edit affordances exist. */
async function mountUnlocked(items: Fixture[], props: {canEdit?: boolean} = {}) {
    const utils = await mount(items, props);
    await fireEvent.click(lockToggle());
    return utils;
}

const save = () => screen.getByTitle('common.save');
const undo = () => screen.getByTitle('common.undo');
const reset = () => screen.getByTitle('common.reset');
const saveAll = () => screen.getByTitle('common.saveAll');
const undoAll = () => screen.getByTitle('common.undoAll');
const resetAll = () => screen.getByTitle('common.resetAll');

/** The error banner. `InfoBanner variant="error"` publishes its variant as a testid. */
const errorBanner = () => screen.queryByTestId('info-banner-error');

/** The last argument the tab handed to the bulk PATCH. */
const lastPatchBody = () => axiosPatch.mock.calls.at(-1)?.[1] as {items: {key: string; value: string}[]};

const textInput = (key: string) => document.getElementById(key) as HTMLInputElement;

/** Text collapsed the way jest-dom collapses what it reads: Intl may separate with U+00A0 or U+202F. */
const squash = (text: string): string => text.replace(/\s+/g, ' ').trim();

beforeEach(() => {
    currentLanguage.set('en');
    locale.set('en');
    translator.set((key: string) => DICT[key] ?? key);
    vi.clearAllMocks();
    axiosGet.mockResolvedValue({data: {server_tz: 'Europe/Rome'}} as never);
    axiosPatch.mockResolvedValue({data: null} as never);
    instance.box.config = instance.UNPINNED;
    instance.load.mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
});

afterEach(() => {
    vi.restoreAllMocks();
});

// =========================================================================
describe('GlobalSettingsTab — who is allowed to touch it', () => {
    it('offers no lock at all to a non-administrator', async () => {
        await mount([setting('session_ttl_hours', '24', 'int')], {canEdit: false});

        expect(screen.queryByTestId('settings-lock-toggle')).toBeNull();
        // The number box is still shown — the values are readable — but frozen.
        expect(screen.getByRole('spinbutton')).toBeDisabled();
    });

    it('never offers the bulk actions to a non-administrator', async () => {
        // There is no path to a change for a read-only visitor, so the whole
        // header group collapses to the read-only badge.
        await mount([setting('session_ttl_hours', '24', 'int')], {canEdit: false});

        expect(screen.queryByTitle('common.saveAll')).toBeNull();
        expect(screen.queryByTitle('common.undoAll')).toBeNull();
        expect(screen.queryByTitle('common.resetAll')).toBeNull();
    });

    it('gives an administrator a lock that starts closed', async () => {
        await mount([setting('session_ttl_hours', '24', 'int')]);

        expect(lockToggle()).toBeInTheDocument();
        expect(screen.getByRole('spinbutton')).toBeDisabled();
    });

    it('warns as soon as the lock is opened', async () => {
        await mountUnlocked([setting('session_ttl_hours', '24', 'int')]);

        await waitFor(() => expect(screen.queryByTestId('info-banner-warning')).not.toBeNull());
        expect(screen.getByRole('spinbutton')).toBeEnabled();
    });
});

// =========================================================================
describe('GlobalSettingsTab — closing the lock over pending edits', () => {
    const discardHeader = () => screen.getByTestId('global-settings-discard-confirm');
    const editedNumber = () => within(screen.getByTestId('global-setting-session_ttl_hours')).getByRole('spinbutton');

    async function requestDiscard() {
        await fireEvent.click(lockToggle());
        const header = await screen.findByTestId('global-settings-discard-confirm');
        const dialog = header.closest<HTMLElement>('[role="dialog"]');
        expect(dialog).not.toBeNull();
        expect(window.confirm).not.toHaveBeenCalled();
        return dialog!;
    }

    it('closes without asking when nothing was changed', async () => {
        await mountUnlocked([setting('session_ttl_hours', '24', 'int')]);
        expect(editedNumber()).toBeEnabled();
        expect(screen.queryByTestId('global-settings-discard-confirm')).not.toBeInTheDocument();

        await fireEvent.click(lockToggle());

        await waitFor(() => expect(editedNumber()).toBeDisabled());
        expect(screen.queryByTestId('global-settings-discard-confirm')).not.toBeInTheDocument();
        await fireEvent.click(lockToggle());
        expect(editedNumber()).toBeEnabled();
        expect(editedNumber()).toHaveValue(24);
        expect(screen.queryByTestId('global-settings-discard-confirm')).not.toBeInTheDocument();
        expect(window.confirm).not.toHaveBeenCalled();
        expect(axiosPatch).not.toHaveBeenCalled();
    });

    it('asks in the amber modal and discards all edits only after confirmation', async () => {
        await mountUnlocked([setting('session_ttl_hours', '24', 'int'), setting('max_file_upload_mb', '10', 'int')]);
        const uploadLimit = within(screen.getByTestId('global-setting-max_file_upload_mb')).getByRole('spinbutton');
        await fireEvent.input(editedNumber(), {target: {value: '48'}});
        await fireEvent.input(uploadLimit, {target: {value: '20'}});
        expect(screen.getByTestId('settings-save-all')).toBeEnabled();

        const dialog = await requestDiscard();
        const confirm = within(dialog).getByTestId('confirm-modal-confirm');
        // These are keys from this file's mock translator, not catalogue text.
        expect(discardHeader()).toHaveTextContent('common.discardChanges');
        expect(within(dialog).getByTestId('confirm-modal-message')).toHaveTextContent('settings.discardChangesConfirm');
        expect(within(dialog).getByTestId('confirm-modal-cancel')).toHaveTextContent('common.cancel');
        expect(confirm).toHaveTextContent('common.discard');
        // Approved feature assertion: selection uses testid; amber is the subject.
        expect(confirm).toHaveClass('btn-warning');
        expect(confirm).not.toHaveClass('btn-danger');
        expect(confirm).not.toHaveClass('btn-primary');
        expect(editedNumber()).toHaveValue(48);
        expect(uploadLimit).toHaveValue(20);
        expect(editedNumber()).toBeEnabled();
        expect(axiosPatch).not.toHaveBeenCalled();

        await fireEvent.click(confirm);
        await waitFor(() => expect(screen.queryByTestId('global-settings-discard-confirm')).not.toBeInTheDocument());
        expect(editedNumber()).toHaveValue(24);
        expect(uploadLimit).toHaveValue(10);
        expect(editedNumber()).toBeDisabled();
        expect(uploadLimit).toBeDisabled();
        expect(screen.queryByTestId('settings-save-all')).not.toBeInTheDocument();
        expect(window.confirm).not.toHaveBeenCalled();
        expect(axiosPatch).not.toHaveBeenCalled();
        expect(setGlobalDirect).not.toHaveBeenCalled();

        // Undo restored the baseline, rather than merely hiding dirty controls.
        await fireEvent.click(lockToggle());
        expect(editedNumber()).toBeEnabled();
        expect(editedNumber()).toHaveValue(24);
        expect(uploadLimit).toHaveValue(10);
        expect(screen.queryByTestId('settings-save-all')).not.toBeInTheDocument();
    });

    it.each(['cancel', 'escape', 'dismiss', 'backdrop'] as const)('keeps the edit and stays unlocked on modal %s', async (action) => {
        await mountUnlocked([setting('session_ttl_hours', '24', 'int')]);
        await fireEvent.input(editedNumber(), {target: {value: '48'}});
        expect(screen.getByTestId('settings-save-all')).toBeEnabled();

        const dialog = await requestDiscard();
        if (action === 'cancel') {
            await fireEvent.click(within(dialog).getByTestId('confirm-modal-cancel'));
        } else if (action === 'escape') {
            await fireEvent.keyDown(dialog, {key: 'Escape'});
        } else if (action === 'dismiss') {
            // The testid identifies this confirmation's header; its sole button
            // is the close control, independent of its accessible translation.
            await fireEvent.click(within(discardHeader()).getByRole('button'));
        } else {
            // ModalBase requires both press and release to start on the backdrop.
            await fireEvent.mouseDown(dialog);
            await fireEvent.click(dialog);
        }

        await waitFor(() => expect(screen.queryByTestId('global-settings-discard-confirm')).not.toBeInTheDocument());
        expect(editedNumber()).toHaveValue(48);
        expect(editedNumber()).toBeEnabled();
        expect(screen.getByTestId('settings-save-all')).toBeEnabled();
        expect(window.confirm).not.toHaveBeenCalled();
        expect(axiosPatch).not.toHaveBeenCalled();
        expect(setGlobalDirect).not.toHaveBeenCalled();

        // The next lock request must still see that same unsaved draft.
        const reopened = await requestDiscard();
        expect(editedNumber()).toHaveValue(48);
        await fireEvent.click(within(reopened).getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('global-settings-discard-confirm')).not.toBeInTheDocument());
        expect(editedNumber()).toBeEnabled();
        expect(editedNumber()).toHaveValue(48);
        expect(axiosPatch).not.toHaveBeenCalled();
    });
});

// =========================================================================
describe('GlobalSettingsTab — loading the list', () => {
    it('says so when the instance exposes nothing', async () => {
        await mount([]);

        expect(screen.getByText('settings.noGlobalSettings')).toBeInTheDocument();
    });

    it('treats a body with no items array as an empty instance', async () => {
        listFn().mockResolvedValue({} as never);
        render(GlobalSettingsTab, {props: {canEdit: true}});

        await waitFor(() => expect(screen.queryByText('settings.noGlobalSettings')).not.toBeNull());
    });

    it("repeats the transport's own words when the list cannot be fetched", async () => {
        listFn().mockRejectedValue(axiosError(500, 'Request failed with status code 500'));
        render(GlobalSettingsTab, {props: {canEdit: true}});

        await waitFor(() => expect(errorBanner()).not.toBeNull());
        expect(errorBanner()!).toHaveTextContent('Request failed with status code 500');
    });

    it('falls back to a fixed message when the failure never reached axios', async () => {
        listFn().mockRejectedValue(new Error('boom'));
        render(GlobalSettingsTab, {props: {canEdit: true}});

        await waitFor(() => expect(errorBanner()).not.toBeNull());
        expect(errorBanner()!).toHaveTextContent('Failed to load settings');
    });

    it('hides the keys the scheduler modal owns', async () => {
        // These five are edited through SchedulerConfigModal only; showing them as
        // raw fields would offer two contradictory ways to set the same thing.
        await mount([setting('session_ttl_hours', '24', 'int'), setting('scheduler_history_sync_times', '06:00,23:00'), setting('scheduler_timezone', 'Europe/Rome'), setting('scheduler_history_sync_days', 'mon,tue')]);

        expect(screen.getByRole('spinbutton')).toBeInTheDocument();
        expect(textInput('scheduler_history_sync_times')).toBeNull();
        expect(textInput('scheduler_timezone')).toBeNull();
        expect(textInput('scheduler_history_sync_days')).toBeNull();
    });
});

// =========================================================================
describe('GlobalSettingsTab — how a value type chooses its control', () => {
    it('renders a bool as a switch, labelled by the setting', async () => {
        await mount([setting('scheduler_enabled', 'true', 'bool')]);

        // The label comes from the dictionary, so the switch is addressable by a
        // name this file owns.
        expect(screen.getByRole('switch', {name: 'Toggle Market data sync'})).toBeInTheDocument();
    });

    it('renders an int and a float as number boxes', async () => {
        await mount([setting('session_ttl_hours', '24', 'int'), setting('some_ratio', '1.5', 'float')]);

        expect(screen.getAllByRole('spinbutton')).toHaveLength(2);
    });

    it('renders an unknown value type as a plain text box tied to its label', async () => {
        await mount([setting('custom_banner', 'hello', 'string')]);

        expect(textInput('custom_banner')).toHaveValue('hello');
    });

    it('renders the three well-known defaults as pickers, not text boxes', async () => {
        await mount([setting('default_language', 'en'), setting('default_currency', 'EUR'), setting('default_theme', 'auto')]);

        expect(textInput('default_language')).toBeNull();
        expect(textInput('default_currency')).toBeNull();
        expect(textInput('default_theme')).toBeNull();
        // Language and currency are dropdowns; the theme row is the same
        // segmented control PreferencesTab uses (SettingTheme) — three option
        // buttons, one per theme, so no third combobox.
        expect(screen.getAllByRole('combobox')).toHaveLength(2);
        expect(screen.getByRole('button', {name: 'settings.themeLight'})).toBeInTheDocument();
        expect(screen.getByRole('button', {name: 'settings.themeDark'})).toBeInTheDocument();
        expect(screen.getByRole('button', {name: 'settings.themeAuto'})).toBeInTheDocument();
    });

    it('shows when a setting was last written — common.updated, then the date in the interface locale — and stays quiet when it never was', async () => {
        const UPDATED_AT = '2024-06-01T08:00:00Z';
        await mount([setting('custom_banner', 'hello', 'string', {updated_at: UPDATED_AT}), setting('other_banner', 'hi', 'string')]);

        // M-17, M-18 CP2: no more hard-coded "Last updated:". This file's dictionary has no `common.updated`, so
        // the key reads as itself; the English UI on jsdom's en-US browser writes the date en-US.
        expect(screen.getByTestId('global-setting-custom_banner')).toHaveTextContent(squash(`common.updated: ${new Date(UPDATED_AT).toLocaleString('en-US')}`));
        expect(screen.getByTestId('global-setting-other_banner')).not.toHaveTextContent('common.updated');
    });
});

// =========================================================================
describe('GlobalSettingsTab — how a setting is labelled', () => {
    it('uses the catalogue name when the key has one', async () => {
        await mount([setting('session_ttl_hours', '24', 'int')]);

        expect(screen.getByText('Session lifetime')).toBeInTheDocument();
    });

    it('invents a readable name from the key when the catalogue has none', async () => {
        // `max_file_upload_mb` → `Max File Upload Mb`: not a translation, a
        // last-resort de-slugging, and the reason a new backend key is never shown
        // as a raw identifier.
        await mount([setting('max_file_upload_mb', '10', 'int')]);

        expect(screen.getByText('Max File Upload Mb')).toBeInTheDocument();
    });

    it('prefers the override when one key already has a name elsewhere', async () => {
        // `default_currency` would otherwise pick up a second, duplicate string.
        await mount([setting('default_currency', 'EUR')]);

        expect(screen.getByText('Default currency')).toBeInTheDocument();
    });

    it('shows a hint and a unit only for keys that have them', async () => {
        await mount([setting('session_ttl_hours', '24', 'int'), setting('max_file_upload_mb', '10', 'int')]);

        expect(screen.getByText('How long a login lasts')).toBeInTheDocument();
        expect(screen.getByText('hours')).toBeInTheDocument();
        // The second key is in neither the descriptions nor the units catalogue and
        // renders nothing rather than its own key.
        expect(screen.queryByText('settings.globalSettingUnits.max_file_upload_mb')).toBeNull();
        expect(screen.queryByText('settings.globalSettingDescriptions.max_file_upload_mb')).toBeNull();
    });

    it('labels the categories from the catalogue, the overrides, and the key itself', async () => {
        await mount([setting('session_ttl_hours', '24', 'int')]);

        // override
        expect(screen.getByTestId('global-settings-category-security')).toHaveTextContent('Security');
        // catalogue
        expect(screen.getByTestId('global-settings-category-session')).toHaveTextContent('Session');
        // neither: the id, capitalised
        expect(screen.getByTestId('global-settings-category-sync')).toHaveTextContent('Sync');
        expect(screen.getByTestId('global-settings-category-defaults')).toHaveTextContent('Defaults');
    });
});

// =========================================================================
/**
 * Every row the tab renders is named in the four catalogues (O, step 21, finding 6).
 *
 * `getSettingLabel` names a row from `SETTING_LABEL_OVERRIDES` (today only
 * `default_currency`, whose name already lives at `settings.defaultCurrency`),
 * else from `settings.globalSettingNames.<key>`; when the catalogue has neither it
 * de-slugs the key, in English, whatever the language. That last resort is meant
 * for a key the frontend does not know yet. `scheduler_enabled`, the row of the
 * Sync category, had no name in any catalogue: every administrator read
 * "Scheduler Enabled".
 *
 * The invariant: no setting row the tab renders falls back to its humanized key —
 * every rendered row is in the label override map, or has
 * `settings.globalSettingNames.<key>` in en, it, fr and es.
 *
 * How it is observed, without copying the override map or the de-slugging here.
 * For these cases the file's dictionary gives way to the real catalogues, seen
 * through a translator that records every key it is asked for: a key present in
 * all four comes back marked, `⟦key⟧`; a key missing from any comes back
 * unchanged, which is how the tab learns there is no translation. The tab asks
 * for `settings.globalSettingNames.<key>` exactly for the rows it renders outside
 * the override map; a name it asked for that a catalogue lacks is a row that falls
 * back.
 *
 * The first case is the control, in both halves: a named row passes and shows its
 * name, the override row and a key the tab hides are exempt, a key no catalogue
 * names is reported. Red today: `scheduler_enabled`, absent from all four
 * catalogues.
 */
describe('GlobalSettingsTab — every row it renders is named in the four catalogues', () => {
    const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};
    const NAME = 'settings.globalSettingNames.';
    /** A key no catalogue will ever name: the row the control must see reported. */
    const UNNAMED = 'lf_test_setting_with_no_name';
    /** What the instance sends: every key of the backend's `GLOBAL_SETTINGS_DEFAULTS` (`schemas/settings.py`), at its default. */
    const SERVER_LIST: Fixture[] = [
        setting('session_ttl_hours', '24', 'int'),
        // invite since A6d (decision 36): the default of a new install, open before.
        setting('registration_mode', 'invite', 'string'),
        setting('require_email_verification', 'false', 'bool'),
        setting('max_file_upload_mb', '10', 'int'),
        setting('scheduler_enabled', 'true', 'bool'),
        setting('scheduler_current_price_frequency_minutes', '10', 'int'),
        setting('scheduler_history_sync_times', '06:00,23:00', 'str'),
        setting('scheduler_history_sync_days', 'mon,tue,wed,thu,fri,sat', 'str'),
        setting('scheduler_history_sync_horizon_days', '14', 'int'),
        setting('scheduler_timezone', 'UTC', 'str'),
        setting('default_currency', 'EUR', 'str'),
        setting('default_language', 'en', 'str'),
        setting('default_theme', 'auto', 'str'),
    ];

    /** The leaf behind a dotted key, read from the catalogue file itself. */
    const leaf = (catalogue: unknown, key: string): unknown => key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    /** The catalogues that have no sentence for `key`. */
    const missingFrom = (key: string): string[] =>
        Object.entries(CATALOGUES)
            .filter(([, catalogue]) => typeof leaf(catalogue, key) !== 'string')
            .map(([lang]) => lang);
    const marked = (key: string): string => `⟦${key}⟧`;

    /** Every key the tab asked the translator for, in this case. */
    let asked: Set<string>;

    beforeEach(() => {
        asked = new Set();
        translator.set((key: string) => {
            asked.add(key);
            return missingFrom(key).length === 0 ? marked(key) : key;
        });
    });

    /** The rows the tab named by the catalogue convention: every row it renders outside the override map. */
    const conventionRows = (): string[] => [...asked].filter((key) => key.startsWith(NAME)).map((key) => key.slice(NAME.length));
    /** Those of them whose name a catalogue lacks, with the catalogues that lack it: the rows that fall back to their humanized key. */
    function fallingBack(): {row: string; missingFrom: string[]}[] {
        const rows = conventionRows().map((row) => ({row, missingFrom: missingFrom(NAME + row)}));
        return rows.filter((entry) => entry.missingFrom.length > 0);
    }

    it('the check, in both halves: a named row passes, the override row and a hidden key are exempt, a row no catalogue names is reported', async () => {
        await mount([setting('session_ttl_hours', '24', 'int'), setting('default_currency', 'EUR', 'str'), setting('scheduler_timezone', 'UTC', 'str'), setting(UNNAMED, 'x', 'str')]);

        expect(screen.getByText(marked(`${NAME}session_ttl_hours`)), 'a row named in all four catalogues shows that name').toBeInTheDocument();
        expect(screen.getByText(marked('settings.defaultCurrency')), 'the override row shows the name it borrows').toBeInTheDocument();
        expect(conventionRows(), 'the tab asks the catalogue name of every row it renders outside the override map').toEqual(expect.arrayContaining(['session_ttl_hours', UNNAMED]));
        expect(conventionRows(), 'the override row is never asked for by the convention').not.toContain('default_currency');
        expect(conventionRows(), 'a key the scheduler modal owns is no row of the tab, so it is never asked for (nor does any catalogue name it)').not.toContain('scheduler_timezone');
        expect(fallingBack(), 'only the row no catalogue names is reported, from all four catalogues').toEqual([{row: UNNAMED, missingFrom: ['en', 'it', 'fr', 'es']}]);
    });

    it('names every row of the instance’s full list in all four catalogues — the Sync row scheduler_enabled included', async () => {
        await mount(SERVER_LIST);

        expect(conventionRows(), 'premise: the scheduler_enabled row (category Sync) is rendered and named by the catalogue convention').toContain('scheduler_enabled');
        expect(fallingBack(), 'no setting row the tab renders falls back to its humanized key: every rendered row is in the label override map or has settings.globalSettingNames.<key> in en, it, fr and es').toEqual([]);
    });

    it('shows the scheduler switch of the Sync category under its catalogue name', async () => {
        await mount(SERVER_LIST);

        await fireEvent.click(screen.getByTestId('global-settings-category-sync'));

        // The Sync category claims one setting, `scheduler_enabled`: its switch is the only one left.
        await waitFor(() => expect(screen.getAllByTestId('setting-toggle-switch'), 'premise: the Sync category shows one setting switch, scheduler_enabled').toHaveLength(1));
        expect(screen.queryByText(marked(`${NAME}scheduler_enabled`)), 'the Sync row is named from the catalogue, not de-slugged from its key').not.toBeNull();
    });
});

// =========================================================================
describe('GlobalSettingsTab — saving one setting', () => {
    const ITEMS = [setting('session_ttl_hours', '24', 'int')];

    it('offers nothing until the value differs', async () => {
        await mountUnlocked(ITEMS);

        expect(screen.queryByTitle('common.save')).toBeNull();
        expect(screen.queryByTitle('common.undo')).toBeNull();
    });

    it('sends the one changed key through the bulk route', async () => {
        await mountUnlocked(ITEMS);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});

        await fireEvent.click(save());

        await waitFor(() => expect(axiosPatch).toHaveBeenCalledTimes(1));
        expect(axiosPatch.mock.calls[0][0]).toBe('/api/v1/settings/global/bulk');
        expect(lastPatchBody()).toEqual({items: [{key: 'session_ttl_hours', value: '48'}]});
    });

    it('publishes what it saved, since a saved global setting looks like nothing', async () => {
        await mountUnlocked(ITEMS);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});

        await fireEvent.click(save());

        await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
        const event = notify.mock.calls[0][0];
        expect(event.name).toBe('settings.global.saved');
        expect(event.detail).toEqual({keys: ['session_ttl_hours'], count: 1});
        expect(event.toast.variant).toBe('success');
    });

    it('adopts the new value as the stored one, so the row stops looking modified', async () => {
        await mountUnlocked(ITEMS);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});

        await fireEvent.click(save());

        await waitFor(() => expect(screen.queryByTitle('common.save')).toBeNull());
        expect(screen.getByRole('spinbutton')).toHaveValue(48);
    });

    it('pushes the whole set into the store, not just the key it wrote', async () => {
        // Other components read the store, not this tab, so a partial update would
        // leave them on stale defaults.
        await mountUnlocked([setting('session_ttl_hours', '24', 'int'), setting('scheduler_enabled', 'true', 'bool')]);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});

        await fireEvent.click(save());

        await waitFor(() => expect(setGlobalDirect).toHaveBeenCalledTimes(1));
        expect(setGlobalDirect.mock.calls[0][0]).toMatchObject({session_ttl_hours: 48, scheduler_enabled: true});
    });

    it('fills the store gaps with the house defaults when the server omits a key', async () => {
        await mountUnlocked([setting('session_ttl_hours', '24', 'int')]);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});

        await fireEvent.click(save());

        await waitFor(() => expect(setGlobalDirect).toHaveBeenCalled());
        expect(setGlobalDirect.mock.calls[0][0]).toMatchObject({
            default_language: 'en',
            default_currency: 'EUR',
            default_theme: 'auto',
            max_file_upload_mb: 10,
            scheduler_enabled: false,
            scheduler_history_sync_times: '06:00,23:00',
            scheduler_history_sync_days: 'mon,tue,wed,thu,fri,sat',
            scheduler_history_sync_horizon_days: 14,
        });
    });

    it('puts the stored value back on undo, without asking the server', async () => {
        await mountUnlocked(ITEMS);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});

        await fireEvent.click(undo());

        await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(24));
        expect(axiosPatch).not.toHaveBeenCalled();
    });

    it('offers a reset only while the value differs from the house default', async () => {
        await mountUnlocked([setting('session_ttl_hours', '48', 'int')]);
        expect(screen.queryByTitle('common.reset')).not.toBeNull();

        await fireEvent.click(reset());

        await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(24));
        expect(screen.queryByTitle('common.reset')).toBeNull();
        // Reset only proposes: it leaves the row modified and unsaved.
        expect(screen.queryByTitle('common.save')).not.toBeNull();
    });

    it('leaves a key it has no default for alone', async () => {
        // `resetSettingToDefault` is guarded on the defaults map, and an unknown
        // key never gets a reset button in the first place.
        await mountUnlocked([setting('custom_banner', 'hello', 'string')]);

        expect(screen.queryByTitle('common.reset')).toBeNull();
    });

    it('locks the save button while the request is in flight', async () => {
        const pending = deferred<{data: null}>();
        axiosPatch.mockReturnValue(pending.promise as never);
        await mountUnlocked(ITEMS);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});

        await fireEvent.click(save());

        await waitFor(() => expect(save()).toBeDisabled());
        pending.resolve({data: null});
        await waitFor(() => expect(screen.queryByTitle('common.save')).toBeNull());
    });
});

// =========================================================================
describe('GlobalSettingsTab — when the server refuses a save', () => {
    const ITEMS = [setting('session_ttl_hours', '24', 'int')];

    const editAndSave = async () => {
        await mountUnlocked(ITEMS);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});
        await fireEvent.click(save());
    };

    it('translates a 403 into "you are not an administrator"', async () => {
        // The one error this tab does not repeat verbatim: "Forbidden" would tell
        // the user nothing about *why*.
        axiosPatch.mockRejectedValue(axiosError(403));
        await editAndSave();

        await waitFor(() => expect(errorBanner()).not.toBeNull());
        expect(errorBanner()!).toHaveTextContent('settings.adminRequired');
    });

    it('repeats the transport message for any other status', async () => {
        axiosPatch.mockRejectedValue(axiosError(500, 'Request failed with status code 500'));
        await editAndSave();

        await waitFor(() => expect(errorBanner()).not.toBeNull());
        expect(errorBanner()!).toHaveTextContent('Request failed with status code 500');
    });

    it('falls back to a translated message when the failure never reached axios', async () => {
        axiosPatch.mockRejectedValue(new Error('Network Error'));
        await editAndSave();

        await waitFor(() => expect(errorBanner()).not.toBeNull());
        expect(errorBanner()!).toHaveTextContent('settings.saveFailed');
    });

    it('keeps the edit on screen and says nothing to the rest of the app', async () => {
        axiosPatch.mockRejectedValue(axiosError(403));
        await editAndSave();

        await waitFor(() => expect(errorBanner()).not.toBeNull());
        expect(screen.getByRole('spinbutton')).toHaveValue(48);
        expect(screen.queryByTitle('common.save')).not.toBeNull();
        expect(notify).not.toHaveBeenCalled();
        expect(setGlobalDirect).not.toHaveBeenCalled();
    });

    it('clears the previous complaint when the retry succeeds', async () => {
        axiosPatch.mockRejectedValueOnce(axiosError(403));
        await editAndSave();
        await waitFor(() => expect(errorBanner()).not.toBeNull());

        await fireEvent.click(save());

        await waitFor(() => expect(errorBanner()).toBeNull());
    });
});

// =========================================================================
describe('GlobalSettingsTab — saving everything at once', () => {
    const ITEMS = [setting('session_ttl_hours', '24', 'int'), setting('scheduler_enabled', 'true', 'bool'), setting('custom_banner', 'hello', 'string')];

    it('offers no bulk save while the tab is clean', async () => {
        await mountUnlocked(ITEMS);

        expect(screen.queryByTitle('common.saveAll')).toBeNull();
        expect(screen.queryByTitle('common.undoAll')).toBeNull();
    });

    it('sends every changed key in a single request', async () => {
        await mountUnlocked(ITEMS);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});
        await fireEvent.input(textInput('custom_banner'), {target: {value: 'bye'}});

        await fireEvent.click(saveAll());

        await waitFor(() => expect(axiosPatch).toHaveBeenCalledTimes(1));
        expect(lastPatchBody().items).toEqual([
            {key: 'session_ttl_hours', value: '48'},
            {key: 'custom_banner', value: 'bye'},
        ]);
    });

    it('leaves the untouched keys out of the payload', async () => {
        await mountUnlocked(ITEMS);
        await fireEvent.click(screen.getByRole('switch', {name: 'Toggle Market data sync'}));

        await fireEvent.click(saveAll());

        await waitFor(() => expect(axiosPatch).toHaveBeenCalled());
        expect(lastPatchBody().items).toEqual([{key: 'scheduler_enabled', value: 'false'}]);
    });

    it('names every key it persisted in the event', async () => {
        await mountUnlocked(ITEMS);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});
        await fireEvent.input(textInput('custom_banner'), {target: {value: 'bye'}});

        await fireEvent.click(saveAll());

        await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
        const event = notify.mock.calls[0][0];
        expect(event.name).toBe('settings.global.saved');
        expect(event.detail).toEqual({keys: ['session_ttl_hours', 'custom_banner'], count: 2});
    });

    it('publishes a failure event carrying the reason, with no toast', async () => {
        // The bulk path is the only one that reports its failure as an event as
        // well as a banner, so an observer can tell a refused write from a slow one.
        axiosPatch.mockRejectedValue(axiosError(403));
        await mountUnlocked(ITEMS);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});

        await fireEvent.click(saveAll());

        await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
        expect(notify.mock.calls[0][0]).toEqual({name: 'settings.global.save.failed', detail: {reason: 'settings.adminRequired'}});
        expect(setGlobalDirect).not.toHaveBeenCalled();
    });

    it('puts every edit back on undo all', async () => {
        await mountUnlocked(ITEMS);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});
        await fireEvent.input(textInput('custom_banner'), {target: {value: 'bye'}});

        await fireEvent.click(undoAll());

        await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(24));
        expect(textInput('custom_banner')).toHaveValue('hello');
        expect(screen.queryByTitle('common.saveAll')).toBeNull();
    });

    it('offers reset all only when something is off the house defaults', async () => {
        await mountUnlocked([setting('session_ttl_hours', '24', 'int')]);

        expect(screen.queryByTitle('common.resetAll')).toBeNull();
    });

    it('moves every known key to its default and leaves the unknown ones alone', async () => {
        await mountUnlocked([setting('session_ttl_hours', '48', 'int'), setting('custom_banner', 'hello', 'string')]);

        await fireEvent.click(resetAll());

        await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(24));
        expect(textInput('custom_banner')).toHaveValue('hello');
    });
});

// =========================================================================
describe('GlobalSettingsTab — the three picker rows', () => {
    /** The row a given key lives in: found through the label the tab gives it, then up to the `global-setting-{key}` wrapper every setting row publishes. */
    const pickerRow = (label: string) => screen.getByText(label).closest('[data-testid^="global-setting-"]') as HTMLElement;

    it('gives the language row its own save and undo', async () => {
        await mountUnlocked([setting('default_language', 'en')]);
        const row = pickerRow('Default Language');
        expect(within(row).queryByTitle('common.save')).toBeNull();

        await fireEvent.click(within(row).getByRole('combobox'));
        await fireEvent.click(await within(row).findByRole('option', {name: /Italiano/}));

        await waitFor(() => expect(within(row).queryByTitle('common.save')).not.toBeNull());
        await fireEvent.click(within(row).getByTitle('common.save'));

        await waitFor(() => expect(axiosPatch).toHaveBeenCalledTimes(1));
        expect(lastPatchBody()).toEqual({items: [{key: 'default_language', value: 'it'}]});
    });

    it('gives the currency row its own save', async () => {
        await mountUnlocked([setting('default_currency', 'EUR')]);
        const row = pickerRow('Default currency');

        await fireEvent.click(within(row).getByRole('combobox'));
        await fireEvent.click(await within(row).findByTestId('search-select-option-USD'));

        await waitFor(() => expect(within(row).queryByTitle('common.save')).not.toBeNull());
        await fireEvent.click(within(row).getByTitle('common.save'));

        await waitFor(() => expect(axiosPatch).toHaveBeenCalledTimes(1));
        expect(lastPatchBody()).toEqual({items: [{key: 'default_currency', value: 'USD'}]});
    });

    it('offers a reset on a picker row that is off the house default', async () => {
        // `default_theme` ships as `auto`; a server holding `light` is off-default
        // from the first render, before the user has touched anything.
        await mountUnlocked([setting('default_theme', 'light')]);
        const row = pickerRow('Default Theme');

        expect(within(row).queryByTitle('common.reset')).not.toBeNull();
        expect(within(row).queryByTitle('common.save')).toBeNull();

        await fireEvent.click(within(row).getByTitle('common.reset'));

        await waitFor(() => expect(within(row).queryByTitle('common.save')).not.toBeNull());
        expect(within(row).queryByTitle('common.reset')).toBeNull();
    });

    it('puts a picker back where it was on undo', async () => {
        await mountUnlocked([setting('default_language', 'en')]);
        const row = pickerRow('Default Language');
        await fireEvent.click(within(row).getByRole('combobox'));
        await fireEvent.click(await within(row).findByRole('option', {name: /Italiano/}));
        await waitFor(() => expect(within(row).queryByTitle('common.undo')).not.toBeNull());

        await fireEvent.click(within(row).getByTitle('common.undo'));

        await waitFor(() => expect(within(row).queryByTitle('common.undo')).toBeNull());
        expect(axiosPatch).not.toHaveBeenCalled();
    });

    it('freezes all three pickers while the tab is locked', async () => {
        // Asserted behaviourally rather than on the `disabled` attribute on purpose:
        // `SimpleSelect` renders a real disabled <button>, while `SearchSelect` (the
        // currency one) renders a <div role="combobox">, which cannot carry it and
        // announces the state through `aria-disabled` instead. What both genuinely
        // guarantee, and what this asserts, is that they do not open. The theme
        // picker is the shared segmented control: real buttons, so `disabled`
        // applies directly.
        await mount([setting('default_language', 'en'), setting('default_currency', 'EUR'), setting('default_theme', 'auto')]);

        const comboboxes = screen.getAllByRole('combobox');
        expect(comboboxes).toHaveLength(2);
        for (const combobox of comboboxes) {
            await fireEvent.click(combobox);
            expect(combobox).toHaveAttribute('aria-expanded', 'false');
        }
        expect(screen.queryByRole('listbox')).toBeNull();
        for (const name of ['settings.themeLight', 'settings.themeDark', 'settings.themeAuto']) {
            expect(screen.getByRole('button', {name})).toBeDisabled();
        }
        expect(screen.queryByTitle('common.save')).toBeNull();
    });

    it('leaves a locked currency picker out of the tab order, and announces it as disabled', async () => {
        // `SearchSelect` renders a <div role="combobox">, which cannot carry the
        // real `disabled` attribute — so the unavailable state is announced via
        // `aria-disabled`. Without it an assistive-technology user is told the
        // combobox is merely collapsed, on a control that will never open.
        await mount([setting('default_currency', 'EUR')]);

        const combobox = screen.getByRole('combobox');
        expect(combobox).toHaveAttribute('tabindex', '-1');
        expect(combobox).toHaveAttribute('aria-disabled', 'true');
        expect(combobox).toHaveAttribute('data-disabled', 'true');
    });
});

// =========================================================================
describe('GlobalSettingsTab — the category filter', () => {
    // `registration_mode` is the row of the security category (A5b): the old bool `enable_registration` played that part.
    const ITEMS = [setting('session_ttl_hours', '24', 'int'), setting('registration_mode', 'open', 'string'), setting('custom_banner', 'hello', 'string')];
    /** The registration row, or null while the filter hides it. */
    const registrationRow = () => screen.queryByTestId('global-setting-registration_mode');

    it('shows everything the server sent by default, with no duplicate rows', async () => {
        await mount(ITEMS);

        expect(screen.getByRole('spinbutton')).toBeInTheDocument();
        expect(registrationRow()).toBeInTheDocument();
        expect(textInput('custom_banner')).toBeInTheDocument();
        expect(document.querySelectorAll('#custom_banner')).toHaveLength(1);
        expect(screen.getAllByTestId('global-setting-registration_mode')).toHaveLength(1);
    });

    it('narrows to the keys a category claims', async () => {
        await mount(ITEMS);

        await fireEvent.click(screen.getByTestId('global-settings-category-session'));

        await waitFor(() => expect(registrationRow()).toBeNull());
        expect(screen.getByRole('spinbutton')).toBeInTheDocument();
        expect(textInput('custom_banner')).toBeNull();
    });

    it('collects a key no claimed category owns under Other', async () => {
        await mount(ITEMS);

        expect(screen.getByTestId('global-settings-category-other')).toHaveTextContent('Other');

        await fireEvent.click(screen.getByTestId('global-settings-category-security'));

        await waitFor(() => expect(screen.queryByRole('spinbutton')).toBeNull());
        expect(registrationRow(), 'the security category holds registration_mode').toBeInTheDocument();
        expect(textInput('custom_banner')).toBeNull();

        await fireEvent.click(screen.getByTestId('global-settings-category-other'));

        await waitFor(() => expect(textInput('custom_banner')).toBeInTheDocument());
        expect(screen.queryByRole('spinbutton')).toBeNull();
        expect(registrationRow()).toBeNull();
    });

    it('hides the Other category when every visible key is already claimed', async () => {
        await mount([setting('session_ttl_hours', '24', 'int'), setting('registration_mode', 'open', 'string')]);

        expect(screen.queryByTestId('global-settings-category-other'), 'registration_mode is claimed by security, not left to Other').toBeNull();

        await fireEvent.click(screen.getByTestId('global-settings-category-security'));

        await waitFor(() => expect(screen.queryByRole('spinbutton')).toBeNull());
        expect(registrationRow()).toBeInTheDocument();
    });

    it('restores the full list when All is chosen again', async () => {
        await mount(ITEMS);
        await fireEvent.click(screen.getByTestId('global-settings-category-session'));
        await waitFor(() => expect(registrationRow()).toBeNull());

        await fireEvent.click(screen.getByRole('button', {name: /^All/}));

        await waitFor(() => expect(registrationRow()).not.toBeNull());
    });

    it('carries a pending edit through a filter round-trip', async () => {
        await mountUnlocked(ITEMS);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});

        await fireEvent.click(screen.getByTestId('global-settings-category-security'));
        await waitFor(() => expect(screen.queryByRole('spinbutton')).toBeNull());
        await fireEvent.click(screen.getByTestId('global-settings-category-session'));

        await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(48));
        expect(screen.queryByTitle('common.save')).not.toBeNull();
    });
});

// =========================================================================
/**
 * Who may create an account: `registration_mode` (accounts lot A5b, plan A5b.1).
 *
 * A5a made the mode a string setting — `open`, `invite`, `disabled` — and let the operator pin it with
 * `LIBREFOLIO_REGISTRATION`: then the database row is not what is in force, saving it answers 409
 * `SETTING_LOCKED_BY_ENV`, and `GET /system/instance` says `registration_locked: true` with the mode in force. Its
 * default, the backend's for a new install and the tab's `SETTING_DEFAULTS`, is `invite` since A6d (decision 36; it was
 * `open`): an unpinned row off it offers a reset that proposes `invite`, and «reset all» sends `invite` for it. The
 * cases below therefore store `open` where the row must be off the default — the pinned ones too, so that the pin, not
 * the default, is what leaves the row alone. The row:
 *   - a `SettingSelect` of the three modes (`setting-select-option-<mode>`, labelled `settings.registrationModes.*`) in
 *     `global-setting-registration_mode`, the security category's;
 *   - pinned: the control locked on the mode in force, not on the row's value; the hint `settings.lockedByEnv`;
 *     `data-locked="true"` on the row (`"false"` otherwise); no save, undo or reset; «reset all» passes it by;
 *   - a 409 `SETTING_LOCKED_BY_ENV` (the pin arrived after the page read the configuration) worded by
 *     `settings.lockedByEnv` with its variable, not by the transport's sentence;
 *   - after a save that wrote the mode, `instanceConfig.load({force: true})`, so the login page and the link pages of
 *     this tab's session read the new mode — and only after the write landed.
 *
 * The mode labels are keys (this file's dictionary has none of them), so the select's trigger reads the key of the mode
 * it shows.
 */
describe('GlobalSettingsTab — registration_mode, who may create an account (A5b)', () => {
    const MODES = ['open', 'invite', 'disabled'] as const;
    type Mode = (typeof MODES)[number];

    const mode = (value: Mode) => setting('registration_mode', value, 'string');
    const row = () => screen.getByTestId('global-setting-registration_mode');
    const modeSelect = () => within(row()).getByRole('combobox');
    const option = (value: Mode) => `setting-select-option-${value}`;
    const label = (value: Mode) => `settings.registrationModes.${value}`;
    /** The forced reloads of the instance configuration the tab asked for. */
    const forcedReloads = () => instance.load.mock.calls.filter(([options]) => options?.force === true);

    /** The server pins the mode with LIBREFOLIO_REGISTRATION, and `value` is the one in force. */
    function pinnedOnServer(value: Mode): void {
        instance.box.config = {profile: 'selfhosted', accounts: {registration_mode: value, registration_locked: true}};
    }

    /** Opens the select of an unlocked, unpinned row and picks `value`. */
    async function pick(value: Mode): Promise<void> {
        await fireEvent.click(modeSelect());
        await fireEvent.click(await within(row()).findByTestId(option(value)));
        await waitFor(() => expect(within(row()).queryByTitle('common.save'), 'premise: the pick made the row modified').not.toBeNull());
    }

    /** A 409 the bulk route answers when LIBREFOLIO_REGISTRATION pins the mode. */
    function lockedByEnv(): Error {
        return Object.assign(new Error('Request failed with status code 409'), {
            isAxiosError: true,
            response: {
                status: 409,
                data: {detail: {error_code: 'SETTING_LOCKED_BY_ENV', message: 'An English sentence the administrator must not read', key: 'registration_mode', variable: 'LIBREFOLIO_REGISTRATION'}},
            },
        });
    }

    /** The file's dictionary, which also prints the values a message is given: `key value…`. */
    const withValues = ((input: string | {id: string; values?: Record<string, unknown>}, options?: {values?: Record<string, unknown>}) => {
        const id = typeof input === 'string' ? input : input.id;
        const values = typeof input === 'string' ? options?.values : input.values;
        const base = DICT[id] ?? id;
        return values ? `${base} ${Object.values(values).join(' ')}` : base;
    }) as unknown as (key: string) => string;

    it('is a select of the three modes, not a text box', async () => {
        await mountUnlocked([mode('open')]);

        expect(textInput('registration_mode'), 'not the generic text row').toBeNull();
        await fireEvent.click(modeSelect());
        await waitFor(() => expect(within(row()).queryByTestId(option('open'))).not.toBeNull());

        const offered = Array.from(row().querySelectorAll('[data-testid^="setting-select-option-"]'), (el) => el.getAttribute('data-testid'));
        expect(offered.sort()).toEqual(MODES.map(option).sort());
        for (const value of MODES) expect(within(row()).getByTestId(option(value))).toHaveTextContent(label(value));
    });

    it('is an ordinary row while the server does not pin the mode: unlocked, the stored mode, a reset off the default', async () => {
        await mountUnlocked([mode('open')]);

        expect(row()).toHaveAttribute('data-locked', 'false');
        expect(modeSelect()).toBeEnabled();
        expect(modeSelect()).toHaveTextContent(label('open'));
        expect(row()).not.toHaveTextContent('settings.lockedByEnv');
        expect(within(row()).queryByTestId('setting-reset'), 'open is off the default, invite (A6d): the row offers a reset').not.toBeNull();
    });

    it('proposes invite on the reset of a mode the server does not pin: the default of a new install (A6d)', async () => {
        await mountUnlocked([mode('open')]);
        expect(within(row()).queryByTestId('setting-reset'), 'open is off the default, invite (A6d): the row offers a reset').not.toBeNull();

        await fireEvent.click(within(row()).getByTestId('setting-reset'));

        await waitFor(() => expect(modeSelect(), 'the reset proposes the default').toHaveTextContent(label('invite')));
        // Reset only proposes: the row is modified, and its own save sends the default.
        await fireEvent.click(await within(row()).findByTitle('common.save'));
        await waitFor(() => expect(axiosPatch).toHaveBeenCalledTimes(1));
        expect(lastPatchBody()).toEqual({items: [{key: 'registration_mode', value: 'invite'}]});
    });

    it('saves a new mode through the bulk route, then reloads the instance configuration, forced, once the save landed', async () => {
        const flight = deferred<{data: null}>();
        // Not a `…Once`: a once-value left unconsumed by a red would leak into the next test (`clearAllMocks` keeps it);
        // the file's `beforeEach` replaces this implementation.
        axiosPatch.mockImplementation(() => flight.promise as never);
        await mountUnlocked([mode('open')]);
        await pick('invite');

        await fireEvent.click(within(row()).getByTitle('common.save'));

        expect(axiosPatch).toHaveBeenCalledTimes(1);
        expect(lastPatchBody()).toEqual({items: [{key: 'registration_mode', value: 'invite'}]});
        expect(forcedReloads(), 'not while the write is in flight').toEqual([]);

        flight.resolve({data: null});

        await waitFor(() => expect(forcedReloads()).toHaveLength(1));
    });

    it('reloads it too after a save all that wrote the mode', async () => {
        await mountUnlocked([setting('session_ttl_hours', '24', 'int'), mode('open')]);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});
        await pick('disabled');

        await fireEvent.click(saveAll());

        await waitFor(() => expect(axiosPatch).toHaveBeenCalledTimes(1));
        expect(lastPatchBody().items).toEqual([
            {key: 'session_ttl_hours', value: '48'},
            {key: 'registration_mode', value: 'disabled'},
        ]);
        await waitFor(() => expect(forcedReloads()).toHaveLength(1));
    });

    it('does not reload it after a save that left the mode alone', async () => {
        await mountUnlocked([setting('session_ttl_hours', '24', 'int'), mode('open')]);
        await fireEvent.input(screen.getByRole('spinbutton'), {target: {value: '48'}});

        await fireEvent.click(within(screen.getByTestId('global-setting-session_ttl_hours')).getByTitle('common.save'));

        // The barrier: the save landed and was announced.
        await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
        expect(forcedReloads()).toEqual([]);
    });

    it('is locked while the server pins the mode: the mode in force, the hint, data-locked, no actions', async () => {
        // The row stores open, off the default (invite, A6d), so that unpinned it would offer a reset;
        // LIBREFOLIO_REGISTRATION=disabled is what is in force.
        pinnedOnServer('disabled');
        await mountUnlocked([setting('session_ttl_hours', '24', 'int'), mode('open')]);

        expect(screen.getByRole('spinbutton'), 'premise: the tab itself is unlocked').toBeEnabled();
        expect(row()).toHaveAttribute('data-locked', 'true');
        expect(modeSelect(), 'the control is locked').toBeDisabled();
        expect(modeSelect(), 'it shows the mode in force, from /system/instance').toHaveTextContent(label('disabled'));
        expect(modeSelect(), 'not the stored row').not.toHaveTextContent(label('open'));
        expect(row()).toHaveTextContent('settings.lockedByEnv');
        for (const action of ['setting-save', 'setting-undo', 'setting-reset']) {
            expect(within(row()).queryByTestId(action), `${action}: nothing to do on a pinned mode`).toBeNull();
        }
    });

    it('control: reset all moves a mode the server does not pin to invite, the default of a new install (A6d)', async () => {
        // The row stores open, the default until A6d: reset all must now move it, to invite.
        await mountUnlocked([setting('session_ttl_hours', '48', 'int'), mode('open')]);

        await fireEvent.click(resetAll());
        await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(24));
        await fireEvent.click(saveAll());

        await waitFor(() => expect(axiosPatch).toHaveBeenCalledTimes(1));
        expect(lastPatchBody().items).toEqual([
            {key: 'session_ttl_hours', value: '24'},
            {key: 'registration_mode', value: 'invite'},
        ]);
    });

    it('reset all passes a pinned mode by', async () => {
        // Green against a tab with no default for the mode, for the wrong reason: the control above is the half that
        // proves reset all reaches the mode at all. The same stored row as there, open, off the default (invite, A6d):
        // the pin, not the default, is what leaves it alone.
        pinnedOnServer('disabled');
        await mountUnlocked([setting('session_ttl_hours', '48', 'int'), mode('open')]);

        await fireEvent.click(resetAll());
        await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(24));
        await fireEvent.click(saveAll());

        await waitFor(() => expect(axiosPatch).toHaveBeenCalledTimes(1));
        expect(lastPatchBody().items).toEqual([{key: 'session_ttl_hours', value: '24'}]);
    });

    it.each(['the row', 'save all'] as const)('words a 409 SETTING_LOCKED_BY_ENV on a save from %s by settings.lockedByEnv and its variable', async (path) => {
        translator.set(withValues);
        axiosPatch.mockRejectedValue(lockedByEnv());
        await mountUnlocked([mode('open')]);
        await pick('invite');

        await fireEvent.click(path === 'the row' ? within(row()).getByTitle('common.save') : saveAll());

        await waitFor(() => expect(errorBanner()).not.toBeNull());
        expect(errorBanner()!).toHaveTextContent('settings.lockedByEnv');
        expect(errorBanner()!, 'the variable to change, from the answer').toHaveTextContent('LIBREFOLIO_REGISTRATION');
        expect(errorBanner()!, 'not the transport sentence').not.toHaveTextContent('Request failed with status code 409');
    });
});

// =========================================================================
describe('GlobalSettingsTab — the scheduler rows', () => {
    const ITEMS = [setting('session_ttl_hours', '24', 'int')];

    it('shows both rows under All and under the sync category', async () => {
        await mount(ITEMS);
        expect(screen.getByTestId('scheduler-status-row')).toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('global-settings-category-sync'));

        await waitFor(() => expect(screen.queryByTestId('scheduler-config-row')).not.toBeNull());
    });

    it('hides both rows under an unrelated category', async () => {
        await mount(ITEMS);

        await fireEvent.click(screen.getByTestId('global-settings-category-session'));

        await waitFor(() => expect(screen.queryByTestId('scheduler-status-row')).toBeNull());
        expect(screen.queryByTestId('scheduler-config-row')).toBeNull();
    });

    it('says the scheduler has never run when the state says nothing', async () => {
        axiosGet.mockResolvedValue({data: {server_tz: 'Europe/Rome'}} as never);
        await mount(ITEMS);

        expect(screen.getByTestId('scheduler-status-row')).toHaveTextContent('settings.global.scheduler.status.neverRun');
    });

    it('reports the last run when there was one', async () => {
        axiosGet.mockResolvedValue({data: {server_tz: 'Europe/Rome', current_price: {last_run_at: '2024-06-01T08:00:00Z', last_status: 'ok'}}} as never);
        await mount(ITEMS);

        await waitFor(() => expect(screen.getByTestId('scheduler-status-row')).toHaveTextContent('settings.global.scheduler.status.lastRun'));
        expect(screen.getByTestId('scheduler-status-row')).not.toHaveTextContent('neverRun');
    });

    it('survives the scheduler state call failing', async () => {
        // A scheduler whose state cannot be read still has a configurable schedule,
        // so the rows stay and only the status text degrades.
        axiosGet.mockRejectedValue(new Error('offline'));
        await mount(ITEMS);

        expect(screen.getByTestId('scheduler-status-row')).toHaveTextContent('settings.global.scheduler.status.neverRun');
        expect(screen.getByTestId('scheduler-config-btn')).toBeInTheDocument();
    });

    it('keeps the configure button shut while the tab is locked', async () => {
        await mount(ITEMS);

        expect(screen.getByTestId('scheduler-config-btn')).toBeDisabled();
    });

    it('opens the configuration modal once unlocked', async () => {
        await mountUnlocked(ITEMS);
        await waitFor(() => expect(screen.getByTestId('scheduler-config-btn')).toBeEnabled());

        await fireEvent.click(screen.getByTestId('scheduler-config-btn'));

        await waitFor(() => expect(screen.queryByTestId('scheduler-config-modal')).not.toBeNull());
    });

    it('opens the log modal from the status row, locked or not', async () => {
        await mount(ITEMS);

        await fireEvent.click(screen.getByTestId('scheduler-status-row'));

        await waitFor(() => expect(screen.queryByTestId('scheduler-log-modal')).not.toBeNull());
    });

    it('opens the log modal from the keyboard too', async () => {
        await mount(ITEMS);

        await fireEvent.keyDown(screen.getByTestId('scheduler-status-row'), {key: 'Enter'});

        await waitFor(() => expect(screen.queryByTestId('scheduler-log-modal')).not.toBeNull());
    });

    it('ignores other keys on the status row', async () => {
        await mount(ITEMS);

        await fireEvent.keyDown(screen.getByTestId('scheduler-status-row'), {key: 'a'});

        expect(screen.queryByTestId('scheduler-log-modal')).toBeNull();
    });

    it('summarises the schedule from the values it holds, defaults included', async () => {
        await mount([setting('session_ttl_hours', '24', 'int'), setting('scheduler_current_price_frequency_minutes', '30')]);

        // The summary is a parametrised message; with the test dictionary the key
        // comes through untranslated, which is enough to pin that the row renders
        // it rather than crashing on a missing value.
        expect(screen.getByTestId('scheduler-config-row')).toHaveTextContent('settings.global.scheduler.status.configSummary');
    });
});

// =========================================================================
/**
 * Lot Z7c-2 — a pending retry of the price job, on the status row.
 *
 * Lot Z7b gave each job of the scheduler's state a `retry_at` (the items a provider's pause deferred are retried then)
 * and a `next_attempt_at` (after a run that raised, no run before it). The status row publishes ONE element for the
 * price job's pending retry, `scheduler-status-retry`: `data-kind="failure"` while `next_attempt_at` is in the future —
 * it wins over `retry_at` —, otherwise `data-kind="deferred"` while `retry_at` is in the future, and none when both are
 * null or past. The history job's retries do not show there.
 *
 * "The future" is the browser's clock: `Date` is fixed at NOW with `vi.setSystemTime` — the timers stay real, so
 * `waitFor` still polls — and put back after each case. The element's text is a parametrised message
 * (`settings.global.scheduler.status.retryAt` or `nextAttemptAt`, with `{time}`) and is never read: its presence and its
 * `data-kind` are the contract. An absence is asserted only after a control mount has shown the element for a pending
 * failure in this very setup, and after a barrier proving the state has landed: the last run's label, which a row with
 * nothing pending shows as before.
 */
describe('GlobalSettingsTab — the price job’s pending retry on the status row (Z7c-2)', () => {
    const ITEMS = [setting('session_ttl_hours', '24', 'int')];
    const NOW = '2026-06-08T10:00:00Z';
    const SOON = '2026-06-08T10:02:00+00:00';
    const LATER = '2026-06-08T10:30:00+00:00';
    const EARLIER = '2026-06-08T09:58:00+00:00';
    const LONG_AGO = '2026-06-08T08:00:00+00:00';
    const LAST_RUN = 'settings.global.scheduler.status.lastRun';

    type Pending = {next_attempt_at: string | null; retry_at: string | null};
    const NOTHING: Pending = {next_attempt_at: null, retry_at: null};

    /** A job's state as the route answers it with lot Z7b's fields: it ran at 09:50, and `pending` says what waits. */
    const jobState = ({next_attempt_at, retry_at}: Pending) => ({
        last_run_at: '2026-06-08T09:50:00+00:00',
        last_duration_s: 2.5,
        last_status: next_attempt_at ? 'error' : retry_at ? 'partial' : 'ok',
        last_items_ok: 3,
        last_items_err: 0,
        last_items_deferred: retry_at ? 2 : 0,
        retry_at,
        consecutive_failures: next_attempt_at ? 1 : 0,
        next_attempt_at,
    });

    const statusRow = () => screen.getByTestId('scheduler-status-row');

    /** Mounts the tab on a scheduler state where `price` waits on the price job and `history` on the history job. */
    async function mountState(price: Pending, history: Pending = NOTHING): Promise<void> {
        axiosGet.mockResolvedValue({data: {server_tz: 'UTC', server_now_utc: '10:00', scheduler_timezone: 'UTC', current_price: jobState(price), history_sync: jobState(history)}} as never);
        await mount(ITEMS);
    }

    /** The one retry element of the status row, once the state has landed. */
    async function shownRetry(): Promise<HTMLElement> {
        return waitFor(() => {
            const found = within(statusRow()).getAllByTestId('scheduler-status-retry');
            expect(found, 'one retry element in the status row').toHaveLength(1);
            return found[0];
        });
    }

    beforeEach(() => {
        vi.setSystemTime(new Date(NOW));
    });

    afterEach(() => {
        // The real Date back, even after a case that failed half-way.
        vi.useRealTimers();
    });

    const pending: [string, 'failure' | 'deferred', Pending][] = [
        ['a run that raised waits for its next attempt', 'failure', {next_attempt_at: SOON, retry_at: null}],
        ['deferred items wait for the provider’s pause', 'deferred', {next_attempt_at: null, retry_at: SOON}],
        ['both wait, the deferred retry first: the failure wins', 'failure', {next_attempt_at: LATER, retry_at: SOON}],
        ['both wait, the next attempt first: the failure wins', 'failure', {next_attempt_at: SOON, retry_at: LATER}],
        ['the failure’s wait is over, the deferred retry’s is not', 'deferred', {next_attempt_at: EARLIER, retry_at: SOON}],
    ];

    it.each(pending)('%s → data-kind="%s"', async (_case, kind, price) => {
        await mountState(price);

        expect(await shownRetry()).toHaveAttribute('data-kind', kind);
        expect(screen.getAllByTestId('scheduler-status-retry'), 'nowhere else on the tab').toHaveLength(1);
    });

    const nothingPending: [string, Pending, Pending][] = [
        ['nothing waits', NOTHING, NOTHING],
        ['both are past', {next_attempt_at: EARLIER, retry_at: LONG_AGO}, NOTHING],
        ['only a past next attempt', {next_attempt_at: EARLIER, retry_at: null}, NOTHING],
        ['only a past deferred retry', {next_attempt_at: null, retry_at: EARLIER}, NOTHING],
        ['only the history job waits', NOTHING, {next_attempt_at: SOON, retry_at: SOON}],
    ];

    it.each(nothingPending)('%s → no retry element', async (_case, price, history) => {
        await mountState({next_attempt_at: SOON, retry_at: null});
        expect(await shownRetry(), 'control: in this setup a pending failure shows the element').toHaveAttribute('data-kind', 'failure');
        cleanup();

        await mountState(price, history);

        await waitFor(() => expect(statusRow(), 'premise: the scheduler state has landed').toHaveTextContent(LAST_RUN));
        expect(screen.queryAllByTestId('scheduler-status-retry')).toHaveLength(0);
    });
});

// =========================================================================
/**
 * M-17, M-18 CP2 — the tab's dates in the interface language.
 *
 * Two dates: when a setting was last written (inside `global-setting-{key}`: a hard-coded English
 * `Last updated:` and `toLocaleString()`), and when the scheduler last ran (`scheduler-status-row`:
 * `settings.global.scheduler.status.lastRun` and `toLocaleString()`). Both were written in the browser's
 * notation, the first with an English label in every language (M-17). The rule (the developer's,
 * 2026-10-12): every figure in the interface language. The cure: `common.updated` of the UI language, then
 * `: ` and the date in `uiLocale()`; the last run's date in `uiLocale()` too.
 *
 * The labels are read from the shipped catalogues: for these cases the translator is the catalogue of the
 * language the step sets, a plain message read as svelte-i18n's `$_` reads it, and replaced when the
 * language changes, as svelte-i18n replaces it. The dates are Intl's output for the interface locale,
 * never typed: jsdom's browser is en-US, so the English UI writes en-US. Both sides are collapsed the way
 * jest-dom collapses the text it reads. The scheduler's state arrives after the list: its label is the
 * barrier before its date is read.
 */
describe('GlobalSettingsTab — the dates in the interface language (M-17, M-18 CP2)', () => {
    type UiLanguage = 'en' | 'it';
    const CATALOGUES: Record<UiLanguage, unknown> = {en, it: itCatalogue};
    /** The interface locale of each language: jsdom's browser is en-US. */
    const LOCALE_OF: Record<UiLanguage, string> = {en: 'en-US', it: 'it'};
    const LAST_RUN = 'settings.global.scheduler.status.lastRun';
    const UPDATED_AT = '2024-06-01T08:00:00Z';
    const LAST_RUN_AT = '2024-06-02T16:30:00Z';

    const leaf = (catalogue: unknown, key: string): unknown => key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    /** `key` in the shipped catalogue of `lang`; the key itself where the catalogue has none, as svelte-i18n falls back. */
    const inCatalogue = (lang: UiLanguage, key: string): string => {
        const value = leaf(CATALOGUES[lang], key);
        return typeof value === 'string' ? value : key;
    };
    /** `label: date`, the label from the catalogue of `lang`, the date in its interface locale. */
    const dated = (lang: UiLanguage, key: string, instant: string): string => squash(`${inCatalogue(lang, key)}: ${new Date(instant).toLocaleString(LOCALE_OF[lang])}`);

    const settingRow = () => screen.getByTestId('global-setting-custom_banner');
    const schedulerRow = () => screen.getByTestId('scheduler-status-row');

    /** Change the UI language as the app does: the language, svelte-i18n's locale, and the translator it hands out. */
    async function useLanguage(lang: UiLanguage): Promise<void> {
        currentLanguage.set(lang);
        locale.set(lang);
        translator.set((key: string) => inCatalogue(lang, key));
        await tick();
    }

    /** One string setting written once, and a scheduler that ran: both dates on screen once the state has landed. */
    async function mountWithDates(lang: UiLanguage): Promise<void> {
        axiosGet.mockResolvedValue({data: {server_tz: 'Europe/Rome', current_price: {last_run_at: LAST_RUN_AT, last_status: 'ok'}}} as never);
        await mount([setting('custom_banner', 'hello', 'string', {updated_at: UPDATED_AT})]);
        await waitFor(() => expect(schedulerRow(), 'premise: the scheduler state has landed').toHaveTextContent(inCatalogue(lang, LAST_RUN)));
    }

    beforeEach(() => {
        // Controls: the catalogues have both labels, and Italian writes them and the dates otherwise than English.
        for (const key of ['common.updated', LAST_RUN]) {
            expect(inCatalogue('it', key), `control: the Italian catalogue has ${key}`).not.toBe(key);
            expect(inCatalogue('it', key), `control: ${key} reads otherwise in Italian`).not.toBe(inCatalogue('en', key));
        }
        expect(new Date(UPDATED_AT).toLocaleString('it'), 'control: Italian writes the date otherwise').not.toBe(new Date(UPDATED_AT).toLocaleString('en-US'));
    });

    afterEach(() => {
        // The language is module-level state shared by every test of the file (the translator is reset by the file's beforeEach).
        currentLanguage.set('en');
        locale.set('en');
    });

    it.each(['en', 'it'] as const)('a setting written once reads common.updated of the UI language, then its date in the interface locale (%s)', async (lang) => {
        await useLanguage(lang);

        await mountWithDates(lang);

        expect(settingRow()).toHaveTextContent(dated(lang, 'common.updated', UPDATED_AT));
    });

    it.each(['en', 'it'] as const)('the scheduler’s last run reads its date in the interface locale (%s)', async (lang) => {
        await useLanguage(lang);

        await mountWithDates(lang);

        expect(schedulerRow()).toHaveTextContent(dated(lang, LAST_RUN, LAST_RUN_AT));
    });

    it('follows an in-place switch of the UI language, en → it: both dates', async () => {
        await useLanguage('en');
        await mountWithDates('en');
        // Soft: a label still hard-coded at mount must not hide whether the dates follow the switch.
        expect.soft(settingRow(), 'en, mount').toHaveTextContent(dated('en', 'common.updated', UPDATED_AT));
        expect.soft(schedulerRow(), 'en, mount').toHaveTextContent(dated('en', LAST_RUN, LAST_RUN_AT));

        await useLanguage('it');

        await waitFor(() => expect(schedulerRow(), 'premise: the label followed the switch').toHaveTextContent(inCatalogue('it', LAST_RUN)));
        expect({updated: squash(settingRow().textContent ?? ''), lastRun: squash(schedulerRow().textContent ?? '')}).toEqual({
            updated: expect.stringContaining(dated('it', 'common.updated', UPDATED_AT)),
            lastRun: expect.stringContaining(dated('it', LAST_RUN, LAST_RUN_AT)),
        });
    });
});

// =========================================================================
describe('GlobalSettingsTab — the mobile category dropdown', () => {
    // Both keys claimed (registration_mode by security, A5b), so the list has no Other: All plus the five base categories.
    const ITEMS = [setting('session_ttl_hours', '24', 'int'), setting('registration_mode', 'open', 'string')];

    /** The whole `sm:hidden` block: its trigger, and the list when it is open. */
    const mobileSection = () => screen.getByText('settings.category').parentElement!;

    it('is closed to begin with', async () => {
        await mount(ITEMS);

        // Just the trigger: the list is not in the DOM at all until it is opened.
        expect(within(mobileSection()).getAllByRole('button')).toHaveLength(1);
    });

    it('offers All plus every category once opened', async () => {
        await mount(ITEMS);

        await fireEvent.click(within(mobileSection()).getByRole('button'));

        await waitFor(() => expect(within(mobileSection()).getAllByRole('button')).toHaveLength(7));
        expect(within(mobileSection()).getByRole('button', {name: /^Security/})).toBeInTheDocument();
    });

    it('filters and closes itself on a choice', async () => {
        await mount(ITEMS);
        await fireEvent.click(within(mobileSection()).getByRole('button'));
        await waitFor(() => expect(within(mobileSection()).getAllByRole('button')).toHaveLength(7));

        await fireEvent.click(within(mobileSection()).getByRole('button', {name: /^Security/}));

        await waitFor(() => expect(within(mobileSection()).getAllByRole('button')).toHaveLength(1));
        expect(screen.queryByRole('spinbutton')).toBeNull();
        // The trigger now names the choice, which is the only place the selection
        // is visible once the list has closed.
        expect(within(mobileSection()).getByRole('button')).toHaveTextContent('Security');
    });

    it('comes back to All from the list too', async () => {
        await mount(ITEMS);
        await fireEvent.click(within(mobileSection()).getByRole('button'));
        await fireEvent.click(within(mobileSection()).getByRole('button', {name: /^Security/}));
        await waitFor(() => expect(screen.queryByRole('spinbutton')).toBeNull());

        await fireEvent.click(within(mobileSection()).getByRole('button'));
        await fireEvent.click(within(mobileSection()).getByRole('button', {name: /^All/}));

        await waitFor(() => expect(screen.queryByRole('spinbutton')).not.toBeNull());
    });
});

// =========================================================================
describe('GlobalSettingsTab — Runes reactive and lifecycle boundaries', () => {
    const mobileTrigger = () => screen.getByTestId('global-settings-mobile-category-trigger');
    const mobileMenu = () => screen.getByTestId('global-settings-mobile-category-menu');
    const mobileOption = (id: string) => within(mobileMenu()).getByTestId(`global-settings-mobile-category-${id}`);
    const row = (key: string) => screen.getByTestId(`global-setting-${key}`);

    it('updates desktop and open mobile labels on locale-only and translator-only changes without GETs', async () => {
        // The translator function stays identical during the first change.
        // Only the explicit $currentLanguage dependency can invalidate the map.
        translator.set((key: string) => `RUNES-${get(currentLanguage)}-${key}`);
        await mount([setting('session_ttl_hours', '24', 'int')]);
        await waitFor(() => expect(schedulerReads()).toEqual([[SCHEDULER_STATE]]));
        await fireEvent.click(screen.getByTestId('global-settings-category-session'));
        await fireEvent.click(mobileTrigger());
        expect(mobileMenu()).toBeInTheDocument();

        const expectLabels = (prefix: string) => {
            expect(screen.getByTestId('global-settings-category-session')).toHaveTextContent(`${prefix}-settings.globalSettingCategories.session`);
            expect(screen.getByTestId('global-settings-category-security')).toHaveTextContent(`${prefix}-settings.security`);
            expect(mobileTrigger()).toHaveTextContent(`${prefix}-settings.globalSettingCategories.session`);
            expect(mobileOption('session')).toHaveTextContent(`${prefix}-settings.globalSettingCategories.session`);
            expect(mobileOption('security')).toHaveTextContent(`${prefix}-settings.security`);
            expect(mobileOption('all')).toHaveTextContent(`${prefix}-settings.all`);
        };
        expectLabels('RUNES-en');
        const initialGets = axiosGet.mock.calls.map(([url]) => url);

        currentLanguage.set('it');
        locale.set('it');
        await tick();
        expectLabels('RUNES-it');
        expect(listFn().mock.calls).toEqual([[]]);
        expect(axiosGet.mock.calls.map(([url]) => url)).toEqual(initialGets);

        // Now replace only the translator. Locale and category do not change.
        translator.set((key: string) => `REPLACED-${key}`);
        await tick();
        expect(get(currentLanguage)).toBe('it');
        expectLabels('REPLACED');
        expect(listFn().mock.calls).toEqual([[]]);
        expect(axiosGet.mock.calls.map(([url]) => url)).toEqual(initialGets);
        expect(axiosPatch).not.toHaveBeenCalled();

        await fireEvent.click(mobileOption('security'));
        await waitFor(() => expect(screen.queryByTestId('global-settings-mobile-category-menu')).not.toBeInTheDocument());
        expect(mobileTrigger()).toHaveTextContent('REPLACED-settings.security');
        expect(listFn().mock.calls).toEqual([[]]);
        expect(axiosGet.mock.calls.map(([url]) => url)).toEqual(initialGets);
    });

    it('tracks nested draft edits independently and keeps bulk dirty until the last edited field is restored', async () => {
        await mountUnlocked([setting('session_ttl_hours', '24', 'int'), setting('default_language', 'en')]);
        await waitFor(() => expect(schedulerReads()).toEqual([[SCHEDULER_STATE]]));
        const initialGets = axiosGet.mock.calls.map(([url]) => url);
        const number = within(row('session_ttl_hours')).getByRole('spinbutton');
        const language = within(row('default_language')).getByRole('combobox');

        expect(screen.queryByTestId('settings-save-all')).not.toBeInTheDocument();
        expect(screen.queryByTestId('settings-reset-all')).not.toBeInTheDocument();
        await fireEvent.input(number, {target: {value: '48'}});
        expect(within(row('session_ttl_hours')).getByTestId('setting-save')).toBeEnabled();
        expect(screen.getByTestId('settings-reset-all')).toBeEnabled();

        await fireEvent.click(language);
        await fireEvent.click(await within(row('default_language')).findByRole('option', {name: /Italiano/}));
        expect(within(row('default_language')).getByTestId('setting-save')).toBeEnabled();

        // Editing back, not an undo helper, exercises two nested record writes.
        await fireEvent.input(number, {target: {value: '24'}});
        expect(number).toHaveValue(24);
        expect(within(row('session_ttl_hours')).queryByTestId('setting-save')).not.toBeInTheDocument();
        expect(screen.getByTestId('settings-save-all')).toBeEnabled();
        expect(screen.getByTestId('settings-reset-all')).toBeEnabled();

        await fireEvent.click(language);
        await fireEvent.click(await within(row('default_language')).findByRole('option', {name: /English/}));
        expect(language).toHaveTextContent('English');
        expect(within(row('default_language')).queryByTestId('setting-save')).not.toBeInTheDocument();
        expect(screen.queryByTestId('settings-save-all')).not.toBeInTheDocument();
        expect(screen.queryByTestId('settings-reset-all')).not.toBeInTheDocument();
        expect(listFn().mock.calls).toEqual([[]]);
        expect(axiosGet.mock.calls.map(([url]) => url)).toEqual(initialGets);
        expect(axiosPatch).not.toHaveBeenCalled();
    });

    it('owns one clickoutside listener per mount and removes it on destroy', async () => {
        const outside = vi.spyOn(clickOutside, 'isOutsideClick');
        // Empty settings exclude child picker/cache listeners from this test.
        const first = await mount([]);
        await fireEvent.click(mobileTrigger());
        expect(mobileMenu()).toBeInTheDocument();
        await fireEvent.click(mobileMenu());
        expect(mobileMenu()).toBeInTheDocument(); // bind:this recognises an inside click

        outside.mockClear();
        await fireEvent.click(document.body);
        expect(outside).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('global-settings-mobile-category-menu')).not.toBeInTheDocument();

        first.unmount();
        expect(screen.queryByTestId('global-settings-tab')).not.toBeInTheDocument();
        outside.mockClear();
        await fireEvent.click(document.body);
        expect(outside).not.toHaveBeenCalled();

        const second = await mount([]);
        await fireEvent.click(mobileTrigger());
        expect(mobileMenu()).toBeInTheDocument();
        outside.mockClear();
        await fireEvent.click(document.body);
        expect(outside).toHaveBeenCalledTimes(1); // no listener retained from mount one
        expect(screen.queryByTestId('global-settings-mobile-category-menu')).not.toBeInTheDocument();

        second.unmount();
        outside.mockClear();
        await fireEvent.click(document.body);
        expect(outside).not.toHaveBeenCalled();
    });

    it('waits for the initial settings read before requesting scheduler state', async () => {
        const settings = deferred<{items: Fixture[]}>();
        const scheduler = deferred<{data: unknown}>();
        const order: string[] = [];
        listFn().mockImplementation(() => {
            order.push('settings');
            return settings.promise;
        });
        axiosGet.mockImplementation(async (url: string) => {
            if (url === SCHEDULER_STATE) {
                order.push('scheduler');
                return scheduler.promise;
            }
            return {data: null};
        });
        render(GlobalSettingsTab, {canEdit: true});
        await tick();

        expect(screen.getByTestId('global-settings-tab')).toHaveAttribute('data-busy', 'true');
        expect(order).toEqual(['settings']);
        expect(schedulerReads()).toEqual([]);

        settings.resolve({items: [setting('session_ttl_hours', '24', 'int')]});
        await waitFor(() => expect(order).toEqual(['settings', 'scheduler']));
        expect(screen.getByTestId('global-settings-tab')).toHaveAttribute('data-busy', 'false');
        scheduler.resolve({data: {server_tz: 'UTC', current_price: {last_run_at: '2024-06-01T08:00:00Z', last_status: 'ok'}}});
        await waitFor(() => expect(screen.getByTestId('scheduler-status-row')).toHaveTextContent('settings.global.scheduler.status.lastRun'));
        expect(listFn().mock.calls).toEqual([[]]);
        expect(schedulerReads()).toEqual([[SCHEDULER_STATE]]);
    });

    it('reloads settings only after scheduler save succeeds, not on open, edit or cancel', async () => {
        const items = [setting('session_ttl_hours', '24', 'int'), setting('scheduler_current_price_frequency_minutes', '17')];
        await mountUnlocked(items);
        await waitFor(() => expect(schedulerReads()).toEqual([[SCHEDULER_STATE]]));
        await fireEvent.click(screen.getByTestId('scheduler-config-btn'));
        expect(await screen.findByTestId('scheduler-config-modal')).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('scheduler-config-cancel'));
        await waitFor(() => expect(screen.queryByTestId('scheduler-config-modal')).not.toBeInTheDocument());
        expect(listFn().mock.calls).toEqual([[]]);
        expect(schedulerReads()).toEqual([[SCHEDULER_STATE]]);

        await fireEvent.click(screen.getByTestId('scheduler-config-btn'));
        const frequency = within(await screen.findByTestId('scheduler-config-frequency')).getByRole('spinbutton');
        expect(frequency).toHaveValue(17);
        await fireEvent.input(frequency, {target: {value: '23'}});
        expect(frequency).toHaveValue(23);
        expect(listFn().mock.calls).toEqual([[]]);
        expect(screen.getByTestId('scheduler-config-save')).toBeEnabled();

        const saveFlight = deferred<{data: null}>();
        const reload = deferred<{items: Fixture[]}>();
        axiosPatch.mockReturnValueOnce(saveFlight.promise);
        listFn().mockReturnValueOnce(reload.promise);
        await fireEvent.click(screen.getByTestId('scheduler-config-save'));
        expect(axiosPatch).toHaveBeenCalledTimes(1);
        expect(lastPatchBody().items).toContainEqual({key: 'scheduler_current_price_frequency_minutes', value: '23'});
        expect(screen.getByTestId('scheduler-config-save')).toBeDisabled();
        expect(listFn().mock.calls).toEqual([[]]);
        expect(schedulerReads()).toEqual([[SCHEDULER_STATE]]);

        saveFlight.resolve({data: null});
        await waitFor(() => expect(listFn().mock.calls).toEqual([[], []]));
        await waitFor(() => expect(screen.queryByTestId('scheduler-config-modal')).not.toBeInTheDocument());
        expect(screen.getByTestId('global-settings-tab')).toHaveAttribute('data-busy', 'true');
        expect(setGlobalDirect).not.toHaveBeenCalled();
        // Baseline onsave calls loadSettings + syncGlobalSettingsStore, NOT
        // loadSchedulerState. Keep those explicit triggers distinct.
        expect(schedulerReads()).toEqual([[SCHEDULER_STATE]]);

        reload.resolve({items: [setting('session_ttl_hours', '24', 'int'), setting('scheduler_current_price_frequency_minutes', '23')]});
        await waitFor(() => expect(setGlobalDirect).toHaveBeenCalledWith(expect.objectContaining({scheduler_current_price_frequency_minutes: 23})));
        expect(screen.getByTestId('global-settings-tab')).toHaveAttribute('data-busy', 'false');
        await fireEvent.click(screen.getByTestId('scheduler-config-btn'));
        expect(within(await screen.findByTestId('scheduler-config-frequency')).getByRole('spinbutton')).toHaveValue(23);
        await fireEvent.click(screen.getByTestId('scheduler-config-cancel'));
        await waitFor(() => expect(screen.queryByTestId('scheduler-config-modal')).not.toBeInTheDocument());
        expect(listFn().mock.calls).toEqual([[], []]);
        expect(schedulerReads()).toEqual([[SCHEDULER_STATE]]);
    });
});
