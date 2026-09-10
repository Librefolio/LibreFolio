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
 * catalogue.
 *
 * What it deliberately does NOT assert:
 *   - `SettingToggle` / `SettingNumber` internals — another lane owns them; here
 *     they are driven through their public affordances (the switch, the number
 *     box) and only the tab's reaction is asserted.
 *   - the scheduler modals' contents. Opening them is asserted, their behaviour is
 *     their own.
 *   - clickOutside's detection algorithm. The Runes cases below exercise only
 *     this tab's listener lifetime and its bound mobile dropdown reference.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {get, readable, writable, type Writable} from 'svelte/store';
import {fireEvent, render, screen, waitFor, within} from '$test/component';

// --- Mocks --------------------------------------------------------------

/**
 * A partial catalogue. A key that is present translates; a key that is absent
 * comes back unchanged, which is exactly what the `localized !== key` helpers
 * treat as "no translation, use the fallback".
 */
const DICT: Record<string, string> = {
    'settings.globalSettingNames.enable_registration': 'Registration open',
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
import {_, locale} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import * as clickOutside from '$lib/utils/core/clickOutside';

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

beforeEach(() => {
    currentLanguage.set('en');
    locale.set('en');
    translator.set((key: string) => DICT[key] ?? key);
    vi.clearAllMocks();
    axiosGet.mockResolvedValue({data: {server_tz: 'Europe/Rome'}} as never);
    axiosPatch.mockResolvedValue({data: null} as never);
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
        await mount([setting('enable_registration', 'true', 'bool')]);

        // The label comes from the dictionary, so the switch is addressable by a
        // name this file owns.
        expect(screen.getByRole('switch', {name: 'Toggle Registration open'})).toBeInTheDocument();
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

    it('shows when a setting was last written, and stays quiet when it never was', async () => {
        await mount([setting('custom_banner', 'hello', 'string', {updated_at: '2024-06-01T08:00:00Z'}), setting('other_banner', 'hi', 'string')]);

        expect(textInput('custom_banner').closest('div.bg-gray-50')).toHaveTextContent('Last updated:');
        expect(textInput('other_banner').closest('div.bg-gray-50')).not.toHaveTextContent('Last updated:');
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
    const ITEMS = [setting('session_ttl_hours', '24', 'int'), setting('enable_registration', 'true', 'bool'), setting('custom_banner', 'hello', 'string')];

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
        await fireEvent.click(screen.getByRole('switch', {name: 'Toggle Registration open'}));

        await fireEvent.click(saveAll());

        await waitFor(() => expect(axiosPatch).toHaveBeenCalled());
        expect(lastPatchBody().items).toEqual([{key: 'enable_registration', value: 'false'}]);
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
    /** The row a given key lives in, found through the label the dictionary gives it. */
    const pickerRow = (label: string) => screen.getByText(label).closest('div.bg-gray-50') as HTMLElement;

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
    const ITEMS = [setting('session_ttl_hours', '24', 'int'), setting('enable_registration', 'true', 'bool'), setting('custom_banner', 'hello', 'string')];

    it('shows everything the server sent by default, with no duplicate rows', async () => {
        await mount(ITEMS);

        expect(screen.getByRole('spinbutton')).toBeInTheDocument();
        expect(screen.getByRole('switch', {name: 'Toggle Registration open'})).toBeInTheDocument();
        expect(textInput('custom_banner')).toBeInTheDocument();
        expect(document.querySelectorAll('#custom_banner')).toHaveLength(1);
    });

    it('narrows to the keys a category claims', async () => {
        await mount(ITEMS);

        await fireEvent.click(screen.getByTestId('global-settings-category-session'));

        await waitFor(() => expect(screen.queryByRole('switch', {name: 'Toggle Registration open'})).toBeNull());
        expect(screen.getByRole('spinbutton')).toBeInTheDocument();
        expect(textInput('custom_banner')).toBeNull();
    });

    it('collects a key no claimed category owns under Other', async () => {
        await mount(ITEMS);

        expect(screen.getByTestId('global-settings-category-other')).toHaveTextContent('Other');

        await fireEvent.click(screen.getByTestId('global-settings-category-security'));

        await waitFor(() => expect(screen.queryByRole('spinbutton')).toBeNull());
        expect(screen.getByRole('switch', {name: 'Toggle Registration open'})).toBeInTheDocument();
        expect(textInput('custom_banner')).toBeNull();

        await fireEvent.click(screen.getByTestId('global-settings-category-other'));

        await waitFor(() => expect(textInput('custom_banner')).toBeInTheDocument());
        expect(screen.queryByRole('spinbutton')).toBeNull();
        expect(screen.queryByRole('switch', {name: 'Toggle Registration open'})).toBeNull();
    });

    it('hides the Other category when every visible key is already claimed', async () => {
        await mount([setting('session_ttl_hours', '24', 'int'), setting('enable_registration', 'true', 'bool')]);

        expect(screen.queryByTestId('global-settings-category-other')).toBeNull();

        await fireEvent.click(screen.getByTestId('global-settings-category-security'));

        await waitFor(() => expect(screen.queryByRole('spinbutton')).toBeNull());
        expect(screen.getByRole('switch', {name: 'Toggle Registration open'})).toBeInTheDocument();
    });

    it('restores the full list when All is chosen again', async () => {
        await mount(ITEMS);
        await fireEvent.click(screen.getByTestId('global-settings-category-session'));
        await waitFor(() => expect(screen.queryByRole('switch', {name: 'Toggle Registration open'})).toBeNull());

        await fireEvent.click(screen.getByRole('button', {name: /^All/}));

        await waitFor(() => expect(screen.queryByRole('switch', {name: 'Toggle Registration open'})).not.toBeNull());
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
describe('GlobalSettingsTab — the mobile category dropdown', () => {
    const ITEMS = [setting('session_ttl_hours', '24', 'int'), setting('enable_registration', 'true', 'bool')];

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
