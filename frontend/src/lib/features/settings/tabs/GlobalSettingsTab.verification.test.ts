// @vitest-environment jsdom
/**
 * GlobalSettingsTab and email verification (lot E5b, developer decision 44): the switch of `require_email_verification`.
 *
 * The contract under test:
 *   - the row is a real switch now: no «coming soon» badge (`settings.comingSoon`) any more;
 *   - the rule reads the SAVED value (`settings[].value`), never the edited one: saved off, and `GET /system/instance`
 *     saying `email.links` is not true, the switch is turned off, with the hint `email.verification.settingNeedsEmail`
 *     in place of the setting's own;
 *   - saved off with `email.links` true: usable, and its own hint;
 *   - saved on: usable both ways until the save, even without an email with a link able to go out — off, on again,
 *     off — and turning it off is always possible; once off is saved, the rule applies again: turned off, the hint;
 *   - the bulk save refused with 409 `EMAIL_VERIFICATION_UNAVAILABLE` (email stopped working meanwhile): the error
 *     banner says `email.verification.settingUnavailable`.
 *
 * Mocks, as in workstream A's `GlobalSettingsTab.test.ts` (left to A), whose blocks are repeated here: a partial
 * dictionary (an absent key comes back as itself), the generated client as a proxy of spies with the tab's two axios
 * routes, `notify`, the global settings store, the instance configuration (getters over `$state`, set per test) and
 * the currency store. Red until E5b is applied (`GlobalSettingsTab.svelte`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable, type Writable} from 'svelte/store';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {fireEvent, render, screen, waitFor, within} from '$test/component';

const DICT: Record<string, string> = {
    'settings.globalSettingNames.scheduler_enabled': 'Market data sync',
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
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));

const axiosGet = vi.fn(async (_url: string) => ({data: null}) as {data: unknown});
const axiosPatch = vi.fn(async (_url: string, _body?: unknown) => ({data: null}) as {data: unknown});
vi.mock('$lib/api', () => {
    const cache = new Map<string, unknown>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
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
vi.mock('$lib/stores/app/globalSettings', () => ({globalSettings: {setDirect: vi.fn(), subscribe: (run: (v: unknown) => void) => (run(null), () => undefined)}}));

const instance = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const BASE: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
    return {
        BASE,
        box: reactiveBox<{config: InstanceConfig}>({config: BASE}),
        load: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
    };
});
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: instance.BASE,
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
    getAllCurrencies: () => [{code: 'EUR', name: 'Euro', symbol: '€'}],
    currencyStore: {subscribe: (run: (v: unknown) => void) => (run({items: [], loaded: true}), () => undefined)},
}));

import GlobalSettingsTab from './GlobalSettingsTab.svelte';
import {zodiosApi} from '$lib/api';
import {_} from '$lib/i18n';

type Fixture = {key: string; value: string; value_type: string; updated_at?: string | null};

const KEY = 'require_email_verification';
const listFn = () => vi.mocked(zodiosApi.list_global_settings_api_v1_settings_global_get as never) as ReturnType<typeof vi.fn>;
const setting = (key: string, value: string, value_type = 'string'): Fixture => ({key, value, value_type, updated_at: null});
const translator = _ as unknown as Writable<(key: string) => string>;

/** The instance configuration with its email part: `links` as given, `available` with it. */
function withEmailLinks(links: boolean | undefined): InstanceConfig {
    return links === undefined ? instance.BASE : ({...instance.BASE, email: {available: links, links}} as InstanceConfig);
}

/** Mount with the option at `value`, wait for the loading gate, and unlock: the switches are editable only then. */
async function mountUnlocked(value: 'true' | 'false'): Promise<void> {
    listFn().mockResolvedValue({items: [setting(KEY, value, 'bool'), setting('scheduler_enabled', 'true', 'bool')]} as never);
    render(GlobalSettingsTab, {props: {canEdit: true}});
    await waitFor(() => expect(screen.getByTestId('global-settings-tab')).toHaveAttribute('data-busy', 'false'));
    await fireEvent.click(screen.getByTestId('settings-lock-toggle'));
}

const row = () => screen.getByTestId(`global-setting-${KEY}`);
const toggle = () => within(row()).getByRole('switch');

beforeEach(() => {
    translator.set((key: string) => DICT[key] ?? key);
    vi.clearAllMocks();
    axiosGet.mockResolvedValue({data: {server_tz: 'Europe/Rome'}} as never);
    axiosPatch.mockResolvedValue({data: null} as never);
    instance.box.config = instance.BASE;
    instance.load.mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('GlobalSettingsTab — require_email_verification', () => {
    it.each([
        ['email.links false', false],
        ['no email part (an older server)', undefined],
    ])('GVR-01: off, %s → the switch turned off, with the hint that it needs email; no «coming soon» badge', async (_label, links) => {
        instance.box.config = withEmailLinks(links);
        await mountUnlocked('false');

        expect(toggle()).toBeDisabled();
        expect(within(row()).getByText('email.verification.settingNeedsEmail')).toBeInTheDocument();
        expect(within(row()).queryByText('settings.comingSoon')).toBeNull();
    });

    it('GVR-02: off with email.links true → usable, its own hint, no «coming soon» badge', async () => {
        instance.box.config = withEmailLinks(true);
        await mountUnlocked('false');

        expect(toggle()).toBeEnabled();
        expect(within(row()).queryByText('email.verification.settingNeedsEmail')).toBeNull();
        expect(within(row()).queryByText('settings.comingSoon')).toBeNull();
    });

    it('GVR-03: saved on, even without email → usable: turning it off always works', async () => {
        instance.box.config = withEmailLinks(false);
        await mountUnlocked('true');

        expect(toggle()).toBeEnabled();
        expect(within(row()).queryByText('email.verification.settingNeedsEmail')).toBeNull();
    });

    it('GVR-05: saved on, email broken — off, on again, off: usable throughout (the saved value decides, not the edited one); once off is saved, turned off with the hint', async () => {
        instance.box.config = withEmailLinks(false);
        await mountUnlocked('true');

        for (const step of ['off', 'on again', 'off'] as const) {
            await fireEvent.click(toggle());
            expect(toggle(), `after «${step}»: still usable before the save`).toBeEnabled();
            expect(within(row()).queryByText('email.verification.settingNeedsEmail'), `after «${step}»: no needs-email hint before the save`).toBeNull();
        }
        await fireEvent.click(within(row()).getByTitle('common.save'));

        await waitFor(() => expect(axiosPatch).toHaveBeenCalledTimes(1));
        expect(axiosPatch.mock.calls[0][1]).toEqual({items: [{key: KEY, value: 'false'}]});
        await waitFor(() => expect(toggle(), 'saved off, no email.links: it cannot go on').toBeDisabled());
        expect(within(row()).getByText('email.verification.settingNeedsEmail')).toBeInTheDocument();
    });

    it('GVR-04: the save refused with 409 EMAIL_VERIFICATION_UNAVAILABLE → the banner says email.verification.settingUnavailable', async () => {
        instance.box.config = withEmailLinks(true);
        axiosPatch.mockRejectedValueOnce(
            Object.assign(new Error('Request failed with status code 409'), {
                isAxiosError: true,
                response: {status: 409, data: {detail: {error_code: 'EMAIL_VERIFICATION_UNAVAILABLE', message: "Setting 'require_email_verification' cannot be turned on now", key: KEY}}},
            }),
        );
        await mountUnlocked('false');

        await fireEvent.click(toggle());
        await fireEvent.click(within(row()).getByTitle('common.save'));

        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toHaveTextContent('email.verification.settingUnavailable'));
        expect(axiosPatch).toHaveBeenCalledTimes(1);
        expect(axiosPatch.mock.calls[0][1]).toEqual({items: [{key: KEY, value: 'true'}]});
    });
});
