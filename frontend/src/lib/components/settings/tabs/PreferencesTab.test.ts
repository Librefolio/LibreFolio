// @vitest-environment jsdom
/**
 * PreferencesTab — component test (Vitest + jsdom).
 *
 * The user's own three preferences: language, base currency, theme. It takes no
 * props at all, so everything that decides its behaviour arrives from two GETs
 * (`/settings/global` for the defaults, `/settings/user` for the current values)
 * and leaves through one PUT — all three fully controllable from here.
 *
 * Why a component test and not an E2E. The happy path is already covered by
 * `front-utility settings`; what is not covered is everything that happens when
 * the server says no. Reaching the error ladder through Playwright means making
 * the real backend reject a settings write on command, and reaching the
 * `loadGlobalDefaults` failure means making it reject *only* the global GET —
 * neither is something a live server offers. The other half of the contract is
 * the PUT body, which is the whole point of a per-field save (`{language}` and
 * nothing else) and is never visible on screen.
 *
 * On not asserting translated text. `$lib/i18n` is mocked with an identity
 * translator, so every label renders as its own i18n *key*. The three per-row
 * action buttons are addressed by `title="common.save" | "common.undo" |
 * "common.reset"` — a key, stable across EN/IT/FR/ES, not a sentence. The theme
 * radios are likewise `settings.themeLight|Dark|Auto`. Nothing here reads a CSS
 * class: "this row is modified" is asserted through the *presence of the save
 * button*, which is what the user can actually act on.
 *
 * What it deliberately does NOT assert:
 *   - the internals of `SettingSelect` / `SettingCurrency` / `SettingTheme` and
 *     of `SettingsLayout`. They are a sibling lane's components; here they are
 *     only the surface through which the tab is driven.
 *   - the currency dropdown's own list. `CurrencySearchSelect` fetches it from
 *     the reference stores, which are stubbed empty — the currency path is
 *     exercised through `saveField('default_currency')` instead, which is the
 *     part PreferencesTab owns.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import {fireEvent, render, screen, waitFor, within} from '$test/component';

// --- Mocks --------------------------------------------------------------

// The identity translator: components render i18n keys verbatim, so an
// assertion can name the message without naming any one language. The two
// language options are the ones this file supplies, so addressing them by name
// is addressing the wiring, not a catalogue entry.
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

// zodiosApi has dozens of methods; a Proxy lazily mints (and caches) a spy per
// property, so `vi.mocked(zodiosApi.foo)` retrieves the same fn to program.
vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
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

const applyTheme = vi.fn();
vi.mock('$lib/stores/app/themeStore', () => ({
    applyTheme: (...args: unknown[]) => applyTheme(...args),
    getStoredThemePreference: () => 'auto',
    getCurrentResolvedTheme: () => 'light',
}));

const setLanguage = vi.fn();
vi.mock('$lib/stores/app/language', () => {
    const store = writable('en');
    return {
        currentLanguage: {subscribe: store.subscribe, set: (v: string) => setLanguage(v)},
        // The real module re-exports LANGUAGE_OPTIONS as availableLanguages.
        availableLanguages: [
            {code: 'en', name: 'English', flag: 'EN'},
            {code: 'it', name: 'Italiano', flag: 'IT'},
        ],
    };
});

const setDirect = vi.fn();
vi.mock('$lib/stores/app/settings', () => ({userSettings: {setDirect: (...a: unknown[]) => setDirect(...a), get: () => null}}));

// The currency dropdown fetches its own catalogue; stub it with two entries so
// the row is drivable without any network, and inert everywhere else.
vi.mock('$lib/stores/reference/currencyStore', () => ({
    currencyStoreVersion: writable(0),
    ensureCurrenciesLoaded: vi.fn(async () => undefined),
    getAllCurrencies: () => [
        {code: 'EUR', name: 'Euro', symbol: '\u20AC', flag_emoji: '', country_codes: [], country_names: []},
        {code: 'USD', name: 'US Dollar', symbol: '$', flag_emoji: '', country_codes: [], country_names: []},
    ],
    getCurrencyInfo: (code: string) => ({code, name: code, symbol: code, flag_emoji: '', country_codes: [], country_names: []}),
    isCurrenciesLoaded: () => true,
}));
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({
    fxRoutesVersion: writable(0),
    ensureFxRoutesLoaded: vi.fn(async () => undefined),
    getConfiguredCurrencySet: () => new Set<string>(),
    getConfiguredPairSlugs: () => new Set<string>(),
    invalidateFxRoutes: vi.fn(),
}));

import PreferencesTab from './PreferencesTab.svelte';
import {zodiosApi} from '$lib/api';

// --- Helpers ------------------------------------------------------------

const globalGet = () => vi.mocked(zodiosApi.list_global_settings_api_v1_settings_global_get as never) as ReturnType<typeof vi.fn>;
const userGet = () => vi.mocked(zodiosApi.get_user_settings_endpoint_api_v1_settings_user_get as never) as ReturnType<typeof vi.fn>;
const userPut = () => vi.mocked(zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put as never) as ReturnType<typeof vi.fn>;

/** The server's global-defaults shape: a flat list of key/value strings. */
function globalItems(over: Record<string, string> = {}) {
    return {items: Object.entries({default_language: 'en', default_currency: 'EUR', default_theme: 'auto', ...over}).map(([key, value]) => ({key, value}))};
}

/** An axios-shaped rejection, recognised by `isAxiosError`. */
function axiosError(message: string): Error {
    return Object.assign(new Error(message), {isAxiosError: true, response: {status: 500, data: {}}});
}

/** A promise this test resolves by hand, so "in flight" is a state we control. */
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** Mount and wait for the loading spinner to give way to the three rows. */
async function mount() {
    const utils = render(PreferencesTab);
    await waitFor(() => expect(screen.queryByTestId('preference-language')).not.toBeNull());
    return utils;
}

const languageRow = () => screen.getByTestId('preference-language');
const currencyRow = () => screen.getByTestId('preference-currency');
const themeRow = () => screen.getByTestId('preference-theme');

/**
 * Pick a language through the `SimpleSelect` combobox. The option label is one
 * of the two this file put into the mocked `LANGUAGE_OPTIONS`, so naming it is
 * naming a value the test supplied, not a catalogue string.
 */
async function chooseLanguage(name: string) {
    await fireEvent.click(within(languageRow()).getByRole('combobox'));
    // The option renders "<flag> <label>", so the accessible name contains the
    // label rather than equalling it.
    await fireEvent.click(await within(languageRow()).findByRole('option', {name: new RegExp(name)}));
}

/** Pick a theme through the radio group — addressed by i18n key, not by label. */
async function chooseTheme(theme: 'light' | 'dark' | 'auto') {
    const key = {light: 'settings.themeLight', dark: 'settings.themeDark', auto: 'settings.themeAuto'}[theme];
    await fireEvent.click(within(themeRow()).getByRole('button', {name: key}));
}

/**
 * Pick a currency through `CurrencySearchSelect`. The two codes come from the
 * stubbed currency store above, so the option label is a value this file
 * supplied rather than anything the catalogue decides.
 */
async function chooseCurrency(code: string) {
    await fireEvent.click(within(currencyRow()).getByRole('combobox'));
    await fireEvent.click(await within(currencyRow()).findByTestId(`search-select-option-${code}`));
}

/** The per-row action buttons, keyed by their (untranslated) title key. */
function rowButton(row: HTMLElement, action: 'save' | 'undo' | 'reset'): HTMLElement | null {
    return within(row).queryByTitle(`common.${action}`);
}

/** The error banner, or null while there is nothing to report. */
function banner(): HTMLElement | null {
    return screen.queryByTestId('info-banner-error');
}

beforeEach(() => {
    vi.clearAllMocks();
    globalGet().mockResolvedValue(globalItems() as never);
    userGet().mockResolvedValue({language: 'en', base_currency: 'EUR', theme: 'auto'} as never);
    userPut().mockResolvedValue({} as never);
});

// =========================================================================
describe('PreferencesTab — loading', () => {
    it('shows nothing editable until both GETs have answered', async () => {
        const pending = deferred<unknown>();
        userGet().mockReturnValue(pending.promise as never);
        render(PreferencesTab);

        // isLoading gates the whole body: no row exists yet to be edited.
        expect(screen.queryByTestId('preference-language')).toBeNull();

        pending.resolve({language: 'en', base_currency: 'EUR', theme: 'auto'});
        await waitFor(() => expect(screen.queryByTestId('preference-language')).not.toBeNull());
    });

    it('shows all three rows once loaded', async () => {
        await mount();

        expect(languageRow()).toBeInTheDocument();
        expect(currencyRow()).toBeInTheDocument();
        expect(themeRow()).toBeInTheDocument();
    });

    it('still becomes usable when the user GET fails, rather than spinning forever', async () => {
        // `loadSettings` swallows the error and only clears isLoading in `finally`.
        // The user keeps the fallback values, which is a usable page, not a dead one.
        userGet().mockRejectedValue(axiosError('boom'));
        await mount();

        expect(themeRow()).toBeInTheDocument();
        // Nothing looks modified, because edited and original were both left at the fallback.
        expect(rowButton(themeRow(), 'save')).toBeNull();
    });

    it('falls back to the hardcoded defaults when the global GET fails', async () => {
        // FALLBACK_DEFAULTS is language=en, currency=EUR, theme=auto. The user's own
        // values are 'it'/'USD'/'dark', so every row is non-default and offers Reset.
        globalGet().mockRejectedValue(new Error('offline'));
        userGet().mockResolvedValue({language: 'it', base_currency: 'USD', theme: 'dark'} as never);
        await mount();

        expect(rowButton(languageRow(), 'reset')).not.toBeNull();
        expect(rowButton(currencyRow(), 'reset')).not.toBeNull();
        expect(rowButton(themeRow(), 'reset')).not.toBeNull();
    });

    it('treats an empty global-settings list as no override at all', async () => {
        // `items: []` leaves every lookup undefined, so the `||` fallbacks decide —
        // the same outcome as a failed request, reached by a different branch.
        globalGet().mockResolvedValue({items: []} as never);
        userGet().mockResolvedValue({language: 'en', base_currency: 'EUR', theme: 'auto'} as never);
        await mount();

        expect(rowButton(themeRow(), 'reset')).toBeNull();
    });

    it('uses the server global defaults when they disagree with the hardcoded ones', async () => {
        // Server says the house default theme is 'dark' and the user is on 'dark':
        // nothing is non-default, so no Reset is offered anywhere.
        globalGet().mockResolvedValue(globalItems({default_theme: 'dark'}) as never);
        userGet().mockResolvedValue({language: 'en', base_currency: 'EUR', theme: 'dark'} as never);
        await mount();

        expect(rowButton(themeRow(), 'reset')).toBeNull();
    });

    it('falls back to the stored theme preference when the server sends none', async () => {
        // `response.theme || getStoredThemePreference()` — the mocked store says 'auto',
        // which equals the global default, so the row is neither modified nor non-default.
        userGet().mockResolvedValue({language: 'en', base_currency: 'EUR', theme: null} as never);
        await mount();

        expect(rowButton(themeRow(), 'save')).toBeNull();
        expect(rowButton(themeRow(), 'reset')).toBeNull();
    });

    it('falls back to the app locale and to EUR when the server sends neither', async () => {
        // The other two `||` fallbacks in `loadSettings`: `$currentLanguage` (mocked
        // to 'en') and the literal 'EUR'. Both land on the house defaults, so no row
        // reports itself as non-default.
        userGet().mockResolvedValue({language: null, base_currency: null, theme: 'auto'} as never);
        await mount();

        expect(rowButton(languageRow(), 'reset')).toBeNull();
        expect(rowButton(currencyRow(), 'reset')).toBeNull();
    });
});

// =========================================================================
describe('PreferencesTab — a modified row offers save and undo', () => {
    it('offers neither until something changes', async () => {
        await mount();

        expect(rowButton(themeRow(), 'save')).toBeNull();
        expect(rowButton(themeRow(), 'undo')).toBeNull();
    });

    it('offers both as soon as the theme is changed', async () => {
        await mount();
        await chooseTheme('dark');

        expect(rowButton(themeRow(), 'save')).not.toBeNull();
        expect(rowButton(themeRow(), 'undo')).not.toBeNull();
    });

    it('puts the previous value back on undo, without touching the server', async () => {
        await mount();
        await chooseTheme('dark');

        await fireEvent.click(rowButton(themeRow(), 'undo')!);

        await waitFor(() => expect(rowButton(themeRow(), 'save')).toBeNull());
        expect(userPut()).not.toHaveBeenCalled();
    });

    it('moves the row to the house default on reset, and that becomes a change to save', async () => {
        // User is on 'dark', the house default is 'auto': the row starts non-default
        // (Reset offered) and after Reset it is modified (Save offered).
        userGet().mockResolvedValue({language: 'en', base_currency: 'EUR', theme: 'dark'} as never);
        await mount();

        await fireEvent.click(rowButton(themeRow(), 'reset')!);

        await waitFor(() => expect(rowButton(themeRow(), 'save')).not.toBeNull());
        expect(userPut()).not.toHaveBeenCalled();
    });
});

// =========================================================================
describe('PreferencesTab — what a single-field save puts on the wire', () => {
    it('sends the theme alone, and applies it locally only after the request succeeds', async () => {
        const pending = deferred<unknown>();
        userPut().mockReturnValue(pending.promise as never);
        await mount();
        await chooseTheme('dark');

        await fireEvent.click(rowButton(themeRow(), 'save')!);

        await waitFor(() => expect(userPut()).toHaveBeenCalledTimes(1));
        // One key, not the whole settings object: a per-field save must not
        // resubmit the two fields the user did not touch.
        expect(userPut()).toHaveBeenCalledWith({theme: 'dark'});
        expect(applyTheme).not.toHaveBeenCalled();

        pending.resolve({});

        await waitFor(() => expect(applyTheme).toHaveBeenCalledWith('dark'));
    });

    it('sends the language alone, and switches the app locale only after the request succeeds', async () => {
        const pending = deferred<unknown>();
        userPut().mockReturnValue(pending.promise as never);
        await mount();
        await chooseLanguage('Italiano');

        await fireEvent.click(rowButton(languageRow(), 'save')!);

        await waitFor(() => expect(userPut()).toHaveBeenCalledTimes(1));
        expect(userPut()).toHaveBeenCalledWith({language: 'it'});
        expect(setLanguage).not.toHaveBeenCalled();

        pending.resolve({});

        await waitFor(() => expect(setLanguage).toHaveBeenCalledWith('it'));
    });

    it('applies the theme locally after a successful request', async () => {
        await mount();
        await chooseTheme('dark');

        await fireEvent.click(rowButton(themeRow(), 'save')!);

        await waitFor(() => expect(userPut()).toHaveBeenCalledTimes(1));
        expect(applyTheme).toHaveBeenCalledWith('dark');
    });

    it('switches the app locale after a successful request', async () => {
        await mount();
        await chooseLanguage('Italiano');

        await fireEvent.click(rowButton(languageRow(), 'save')!);

        await waitFor(() => expect(userPut()).toHaveBeenCalledTimes(1));
        expect(userPut()).toHaveBeenCalledWith({language: 'it'});
        expect(setLanguage).toHaveBeenCalledWith('it');
    });

    it('sends the base currency alone, and mirrors it into the settings store', async () => {
        await mount();
        await chooseCurrency('USD');

        await fireEvent.click(rowButton(currencyRow(), 'save')!);

        await waitFor(() => expect(userPut()).toHaveBeenCalledTimes(1));
        expect(userPut()).toHaveBeenCalledWith({base_currency: 'USD'});
        // The base-currency change is the one the app caches from login, so the
        // store copy is what stops the rest of the UI showing the old currency.
        expect(setDirect).toHaveBeenCalledWith({language: 'en', base_currency: 'USD', theme: 'auto'});
        expect(applyTheme).not.toHaveBeenCalled();
    });

    it('mirrors the whole triple into the settings store, so the rest of the app sees it', async () => {
        await mount();
        await chooseTheme('dark');
        await fireEvent.click(rowButton(themeRow(), 'save')!);

        await waitFor(() => expect(setDirect).toHaveBeenCalledTimes(1));
        // The PUT carries one field; the store carries all three, because a
        // sidebar reading a stale base currency is the bug this exists to avoid.
        expect(setDirect).toHaveBeenCalledWith({language: 'en', base_currency: 'EUR', theme: 'dark'});
    });

    it('publishes a saved event naming the field, and a success toast', async () => {
        await mount();
        await chooseTheme('light');
        await fireEvent.click(rowButton(themeRow(), 'save')!);

        await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
        const event = notify.mock.calls[0][0];
        expect(event.name).toBe('settings.preferences.saved');
        expect(event.detail).toEqual({fields: 1, field: 'theme', value: 'light'});
        // The variant is the contract; the message is a translated sentence.
        expect(event.toast.variant).toBe('success');
    });

    it('stops offering save once the value has landed', async () => {
        await mount();
        await chooseTheme('dark');
        await fireEvent.click(rowButton(themeRow(), 'save')!);

        // originalValues moves to the saved value, so the row is no longer modified.
        await waitFor(() => expect(rowButton(themeRow(), 'save')).toBeNull());
    });
});

// =========================================================================
describe('PreferencesTab — when the save fails', () => {
    it("shows the transport's own message for an axios failure", async () => {
        userPut().mockRejectedValue(axiosError('Request failed with status code 500'));
        await mount();
        await chooseTheme('dark');

        await fireEvent.click(rowButton(themeRow(), 'save')!);

        await waitFor(() => expect(banner()).not.toBeNull());
        expect(banner()!).toHaveTextContent('Request failed with status code 500');
    });

    it('falls back to a translated failure for anything that is not an axios error', async () => {
        userPut().mockRejectedValue(new TypeError('boom'));
        await mount();
        await chooseTheme('dark');

        await fireEvent.click(rowButton(themeRow(), 'save')!);

        await waitFor(() => expect(banner()).not.toBeNull());
        expect(banner()!).toHaveTextContent('settings.saveFailed');
    });

    it('keeps the edit on screen so the user can retry, and says nothing succeeded', async () => {
        userPut().mockRejectedValue(axiosError('nope'));
        await mount();
        await chooseTheme('dark');

        await fireEvent.click(rowButton(themeRow(), 'save')!);

        await waitFor(() => expect(banner()).not.toBeNull());
        expect(rowButton(themeRow(), 'save')).not.toBeNull();
        expect(notify).toHaveBeenCalledWith(
            expect.objectContaining({
                name: 'settings.preferences.save.failed',
                detail: {field: 'theme', reason: 'nope'},
                toast: expect.objectContaining({variant: 'error'}),
            }),
        );
    });

    it('lets the user dismiss the banner without losing the edit', async () => {
        userPut().mockRejectedValue(axiosError('nope'));
        await mount();
        await chooseTheme('dark');
        await fireEvent.click(rowButton(themeRow(), 'save')!);
        await waitFor(() => expect(banner()).not.toBeNull());

        await fireEvent.click(within(banner()!).getByRole('button', {name: 'Dismiss'}));

        await waitFor(() => expect(banner()).toBeNull());
        expect(rowButton(themeRow(), 'save')).not.toBeNull();
    });

    it('clears the previous error when a new attempt begins', async () => {
        userPut().mockRejectedValueOnce(axiosError('first'));
        await mount();
        await chooseTheme('dark');
        await fireEvent.click(rowButton(themeRow(), 'save')!);
        await waitFor(() => expect(banner()).not.toBeNull());

        await fireEvent.click(rowButton(themeRow(), 'save')!);

        await waitFor(() => expect(banner()).toBeNull());
    });

    it('does not apply the rejected theme locally, and raises an error toast', async () => {
        userPut().mockRejectedValue(axiosError('nope'));
        await mount();
        await chooseTheme('dark');

        await fireEvent.click(rowButton(themeRow(), 'save')!);

        await waitFor(() => expect(banner()).not.toBeNull());
        expect(applyTheme).not.toHaveBeenCalled();
        expect(notify).toHaveBeenCalledWith(
            expect.objectContaining({
                name: 'settings.preferences.save.failed',
                detail: {field: 'theme', reason: 'nope'},
                toast: expect.objectContaining({variant: 'error'}),
            }),
        );
    });

    it('does not switch to the rejected language locally', async () => {
        userPut().mockRejectedValue(axiosError('nope'));
        await mount();
        await chooseLanguage('Italiano');

        await fireEvent.click(rowButton(languageRow(), 'save')!);

        await waitFor(() => expect(banner()).not.toBeNull());
        expect(setLanguage).not.toHaveBeenCalled();
    });
});

// =========================================================================
describe('PreferencesTab — save all', () => {
    /** The layout's header buttons, addressed by their (untranslated) title key. */
    const bulk = (action: 'saveAll' | 'undoAll' | 'resetAll') => screen.queryByTitle(`common.${action}`);

    it('offers no bulk action while nothing is modified', async () => {
        await mount();

        expect(bulk('saveAll')).toBeNull();
        expect(bulk('undoAll')).toBeNull();
        expect(bulk('resetAll')).toBeNull();
    });

    it('offers reset all when at least one persisted value differs from the global default', async () => {
        userGet().mockResolvedValue({language: 'it', base_currency: 'EUR', theme: 'auto'} as never);
        await mount();

        expect(rowButton(languageRow(), 'reset')).not.toBeNull();
        expect(bulk('resetAll')).not.toBeNull();
    });

    it('does not offer reset all when every persisted value already matches the global defaults', async () => {
        await mount();

        expect(rowButton(languageRow(), 'reset')).toBeNull();
        expect(rowButton(currencyRow(), 'reset')).toBeNull();
        expect(rowButton(themeRow(), 'reset')).toBeNull();
        expect(bulk('resetAll')).toBeNull();
    });

    it('sends one request per modified field and none for the untouched ones', async () => {
        await mount();
        await chooseTheme('dark');

        await fireEvent.click(bulk('saveAll')!);

        await waitFor(() => expect(userPut()).toHaveBeenCalledTimes(1));
        expect(userPut()).toHaveBeenCalledWith({theme: 'dark'});
    });

    it('sends both when two fields changed, one request each', async () => {
        await mount();
        await chooseTheme('dark');
        await chooseLanguage('Italiano');

        await fireEvent.click(bulk('saveAll')!);

        await waitFor(() => expect(userPut()).toHaveBeenCalledTimes(2));
        expect(userPut()).toHaveBeenCalledWith({language: 'it'});
        expect(userPut()).toHaveBeenCalledWith({theme: 'dark'});
    });

    it('sends only the currency when only the currency changed', async () => {
        // The bulk path is three independent `if`s, not a loop: the theme leg must
        // stay untaken, and in particular `applyTheme` must not fire for an
        // unchanged theme.
        await mount();
        await chooseCurrency('USD');

        await fireEvent.click(bulk('saveAll')!);

        await waitFor(() => expect(userPut()).toHaveBeenCalledTimes(1));
        expect(userPut()).toHaveBeenCalledWith({base_currency: 'USD'});
        expect(applyTheme).not.toHaveBeenCalled();
        expect(setLanguage).not.toHaveBeenCalled();
    });

    it('sends all three, in the fixed order language, currency, theme', async () => {
        await mount();
        await chooseTheme('dark');
        await chooseLanguage('Italiano');
        await chooseCurrency('USD');

        await fireEvent.click(bulk('saveAll')!);

        await waitFor(() => expect(userPut()).toHaveBeenCalledTimes(3));
        expect(userPut().mock.calls.map((c) => c[0])).toEqual([{language: 'it'}, {base_currency: 'USD'}, {theme: 'dark'}]);
        const event = notify.mock.calls[0][0];
        expect(event.detail).toMatchObject({fields: 3, saved: ['language', 'default_currency', 'theme'], failed: [], language: 'it', currency: 'USD', theme: 'dark'});
    });

    it('falls back to a translated failure when the bulk save trips on a non-axios error', async () => {
        userPut().mockRejectedValue(new TypeError('boom'));
        await mount();
        await chooseTheme('dark');

        await fireEvent.click(bulk('saveAll')!);

        await waitFor(() => expect(banner()).not.toBeNull());
        expect(banner()!).toHaveTextContent('settings.saveFailed');
        expect(notify).toHaveBeenCalledWith(
            expect.objectContaining({
                name: 'settings.preferences.save.failed',
                detail: expect.objectContaining({fields: 0, saved: [], failed: ['theme']}),
                toast: expect.objectContaining({variant: 'error'}),
            }),
        );
    });

    it('reports how many fields were actually persisted', async () => {
        await mount();
        await chooseTheme('dark');

        await fireEvent.click(bulk('saveAll')!);

        await waitFor(() => expect(notify).toHaveBeenCalledTimes(1));
        const event = notify.mock.calls[0][0];
        expect(event.name).toBe('settings.preferences.saved');
        expect(event.detail).toMatchObject({fields: 1, saved: ['theme'], failed: [], theme: 'dark'});
        expect(event.toast.variant).toBe('success');
    });

    it('says nothing at all when the bulk save had nothing to save', async () => {
        // `saveAll` is reachable with no changes — SettingsLayout hides the button,
        // but undoAll() between click and handler, or a second click, gets here.
        // The guard is `saved.length > 0`: no request, no event, no toast.
        await mount();
        await chooseTheme('dark');
        await fireEvent.click(bulk('undoAll')!);
        await waitFor(() => expect(bulk('saveAll')).toBeNull());

        expect(userPut()).not.toHaveBeenCalled();
        expect(notify).not.toHaveBeenCalled();
    });

    it('continues after a rejection and reports saved versus failed fields', async () => {
        userPut()
            .mockRejectedValueOnce(axiosError('down'))
            .mockResolvedValueOnce({} as never);
        await mount();
        await chooseTheme('dark');
        await chooseLanguage('Italiano');

        await fireEvent.click(bulk('saveAll')!);

        await waitFor(() => expect(banner()).not.toBeNull());
        expect(userPut()).toHaveBeenCalledTimes(2);
        expect(userPut().mock.calls.map((c) => c[0])).toEqual([{language: 'it'}, {theme: 'dark'}]);
        expect(setLanguage).not.toHaveBeenCalled();
        expect(applyTheme).toHaveBeenCalledWith('dark');
        expect(rowButton(languageRow(), 'save')).not.toBeNull();
        expect(rowButton(themeRow(), 'save')).toBeNull();
        const event = notify.mock.calls[0][0];
        expect(event.name).toBe('settings.preferences.save.partial');
        expect(event.detail).toMatchObject({fields: 1, saved: ['theme'], failed: ['language'], reasons: {language: 'down'}});
        expect(event.toast.variant).toBe('warning');
    });

    it('puts every row back on undo all', async () => {
        await mount();
        await chooseTheme('dark');

        await fireEvent.click(bulk('undoAll')!);

        await waitFor(() => expect(rowButton(themeRow(), 'save')).toBeNull());
        expect(bulk('saveAll')).toBeNull();
    });

    it('moves every row to the house defaults on reset all', async () => {
        // Every value differs from the global default, so resetting all of them
        // makes all three modified at once.
        globalGet().mockResolvedValue(globalItems({default_theme: 'light', default_language: 'it', default_currency: 'USD'}) as never);
        userGet().mockResolvedValue({language: 'en', base_currency: 'EUR', theme: 'dark'} as never);
        await mount();

        expect(bulk('resetAll')).not.toBeNull();
        await fireEvent.click(bulk('resetAll')!);

        await waitFor(() => expect(rowButton(themeRow(), 'save')).not.toBeNull());
        expect(rowButton(languageRow(), 'save')).not.toBeNull();
        expect(rowButton(currencyRow(), 'save')).not.toBeNull();
    });
});

// =========================================================================
describe('PreferencesTab — the category filter', () => {
    /** The desktop category nav renders one button per category, labelled by key. */
    const navButton = (key: string) => screen.getAllByRole('button', {name: key})[0];

    it('shows all three rows under the default (no category selected)', async () => {
        await mount();

        expect(screen.queryByTestId('preference-language')).not.toBeNull();
        expect(screen.queryByTestId('preference-currency')).not.toBeNull();
        expect(screen.queryByTestId('preference-theme')).not.toBeNull();
    });

    it.each([
        ['settings.categoryDisplay', 'preference-language'],
        ['settings.categoryCurrency', 'preference-currency'],
        ['settings.categoryAppearance', 'preference-theme'],
    ])('narrows to a single row under %s', async (categoryKey, kept) => {
        await mount();

        await fireEvent.click(navButton(categoryKey));

        await waitFor(() => expect(screen.queryByTestId(kept)).not.toBeNull());
        for (const other of ['preference-language', 'preference-currency', 'preference-theme'].filter((t) => t !== kept)) {
            expect(screen.queryByTestId(other)).toBeNull();
        }
    });

    it('brings the other rows back when the filter is cleared', async () => {
        await mount();
        await fireEvent.click(navButton('settings.categoryDisplay'));
        await waitFor(() => expect(screen.queryByTestId('preference-theme')).toBeNull());

        await fireEvent.click(navButton('settings.all'));

        await waitFor(() => expect(screen.queryByTestId('preference-theme')).not.toBeNull());
    });

    it('keeps an edit made under one category when the filter moves away and back', async () => {
        await mount();
        await chooseTheme('dark');
        await fireEvent.click(navButton('settings.categoryDisplay'));
        await waitFor(() => expect(screen.queryByTestId('preference-theme')).toBeNull());

        await fireEvent.click(navButton('settings.categoryAppearance'));

        // editedValues is not rebuilt by the filter: the pending change survives.
        await waitFor(() => expect(screen.queryByTestId('preference-theme')).not.toBeNull());
        expect(rowButton(themeRow(), 'save')).not.toBeNull();
    });
});
