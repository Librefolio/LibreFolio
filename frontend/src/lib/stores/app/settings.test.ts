/**
 * defaultDisplayCurrency — the currency a page starts in (R2 / N).
 *
 * Written RED-FIRST, before the store exists. The developer's decision («Dalla Default Currency dell'utente: è un
 * difetto»): a page that opens on a display currency takes the Default Currency of the user
 * (`userSettings.base_currency`), the instance setting (`globalSettings.default_currency`, «Default currency for new
 * users») only when the user has none, and EUR when neither names one. The Dashboard, both broker pages, the assets
 * risk panel and the FX AI Export will all read it from one derived store exported by `settings.ts`: this file pins the
 * store's rule, `e2e/portfolio/default-currency.spec.ts` the pages that read it.
 *
 * The two stores are driven through their own synchronous surface only (`setDirect`, `reset`, `clear`), never through a
 * load: `$lib/api` is replaced by a client whose every call fails, so a case that reached the network would say so
 * instead of waiting on it. `$app/environment` stays the shared mock (`browser: false`), which keeps both stores off
 * `localStorage`, and both are reset around every case: no case inherits a neighbour's settings.
 *
 * The second describe is the one place this file loads. It used to pin how `globalSettings.load()` read
 * `enable_registration` (K, step 22), the bool the login page followed to offer «Register here». Accounts lot A5a
 * replaced that setting with `registration_mode` (`open`, `invite`, `disabled`), and A5b moved the login page onto the
 * public instance configuration (`instanceConfig.config.accounts.registration_mode`, which also knows when
 * `LIBREFOLIO_REGISTRATION` pins the mode). So the describe now pins the store's new truth: `enable_registration` is
 * gone from it — not in its defaults, not after a load — and `registration_mode`, read by nobody through this store,
 * arrives as the plain string the server sent, like the other string settings. `GET /settings/global` is answered one
 * call at a time (`mockResolvedValueOnce`); the client fails again right after.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {get, type Readable} from 'svelte/store';

vi.mock('$lib/api', () => {
    function offline(operation: string) {
        return vi.fn(async () => {
            throw new Error(`settings.test.ts drives the stores without the network, yet ${operation} was called`);
        });
    }
    return {
        zodiosApi: {
            get_user_settings_endpoint_api_v1_settings_user_get: offline('GET /settings/user'),
            update_user_settings_endpoint_api_v1_settings_user_put: offline('PUT /settings/user'),
            list_global_settings_api_v1_settings_global_get: offline('GET /settings/global'),
            bulk_update_global_settings_api_v1_settings_global_bulk_patch: offline('PATCH /settings/global/bulk'),
        },
        ApiError: class ApiError extends Error {},
        axiosInstance: {},
    };
});

import {zodiosApi} from '$lib/api';
import {defaultDisplayCurrency, userSettings, type UserSettings} from '$lib/stores/app/settings';
import {globalSettings} from '$lib/stores/app/globalSettings';

/** User settings naming this Default Currency, everything else at what a new account gets. */
function settingsWith(base_currency: string): UserSettings {
    return {language: 'en', base_currency, theme: 'auto', avatar_url: null};
}

/**
 * The store under test. Read through here so that, while `settings.ts` does not export it, every case fails on a
 * message naming the export: `get(undefined)` would answer `undefined` without a word.
 */
function displayCurrency(): Readable<string> {
    expect(typeof (defaultDisplayCurrency as Readable<string> | undefined)?.subscribe, 'settings.ts exports defaultDisplayCurrency, a readable store of the currency a page starts in').toBe('function');
    return defaultDisplayCurrency;
}

function resetStores(): void {
    userSettings.reset();
    globalSettings.clear();
}

describe('defaultDisplayCurrency — the Default Currency of the user first, the instance setting only as a fallback', () => {
    beforeEach(resetStores);
    afterEach(resetStores);

    it('is the Default Currency of the user when there is one, whatever the instance says', () => {
        globalSettings.setDirect({default_currency: 'GBP'});
        userSettings.setDirect(settingsWith('USD'));

        expect(get(displayCurrency())).toBe('USD');
    });

    it('is the instance setting while no user settings are loaded', () => {
        globalSettings.setDirect({default_currency: 'GBP'});

        expect(userSettings.get(), 'premise: no user settings are loaded').toBeNull();
        expect(get(displayCurrency())).toBe('GBP');
    });

    it('reads an empty Default Currency as none, and falls back to the instance setting', () => {
        globalSettings.setDirect({default_currency: 'GBP'});
        userSettings.setDirect(settingsWith(''));

        expect(get(displayCurrency())).toBe('GBP');
    });

    it('is EUR when neither the user nor the instance names a currency', () => {
        // Emptied rather than cleared: the store's own instance default is EUR too, and the EUR below could come from it.
        globalSettings.setDirect({default_currency: ''});
        userSettings.setDirect(settingsWith(''));

        expect(get(displayCurrency())).toBe('EUR');

        userSettings.reset();
        expect(get(displayCurrency()), 'and with no user settings at all').toBe('EUR');
    });

    it('moves a subscriber to the Default Currency of the user when the user settings arrive after the instance ones', () => {
        globalSettings.setDirect({default_currency: 'GBP'});
        const seen: string[] = [];
        const unsubscribe = displayCurrency().subscribe((currency) => seen.push(currency));
        try {
            expect(seen, 'before the user settings: the instance setting').toEqual(['GBP']);

            userSettings.setDirect(settingsWith('USD'));

            expect(seen, 'once they arrive: the Default Currency of the user, on the same subscription').toEqual(['GBP', 'USD']);
        } finally {
            unsubscribe();
        }
    });
});

describe('globalSettings.load() — enable_registration is gone, registration_mode arrives as a plain string (A5b)', () => {
    const listGlobalSettings = vi.mocked(zodiosApi.list_global_settings_api_v1_settings_global_get);

    /**
     * The store as these cases read it: every key it holds, typed `unknown` on purpose — `enable_registration` must not
     * be there at all, and `registration_mode` is no field of the `GlobalSettings` interface — with `default_currency`,
     * the witness that a load took its answer.
     */
    function observed(): Record<string, unknown> & {default_currency: string} {
        return globalSettings.get() as unknown as Record<string, unknown> & {default_currency: string};
    }

    /** One row of `GET /settings/global`, as the backend sends it. */
    function row(key: string, value: string, value_type: 'bool' | 'int' | 'string' | 'str') {
        return {key, value, value_type};
    }

    /**
     * What the server sends today, `default_currency` aside (the witness adds it): every key of the backend's
     * `GLOBAL_SETTINGS_DEFAULTS` (`schemas/settings.py`) at its default — `registration_mode` among them, no
     * `enable_registration`.
     */
    const SERVER_ROWS = [
        row('session_ttl_hours', '24', 'int'),
        row('registration_mode', 'open', 'string'),
        row('require_email_verification', 'false', 'bool'),
        row('max_file_upload_mb', '10', 'int'),
        row('scheduler_enabled', 'true', 'bool'),
        row('scheduler_current_price_frequency_minutes', '10', 'int'),
        row('scheduler_history_sync_times', '06:00,23:00', 'str'),
        row('scheduler_history_sync_days', 'mon,tue,wed,thu,fri,sat', 'str'),
        row('scheduler_history_sync_horizon_days', '14', 'int'),
        row('scheduler_timezone', 'UTC', 'str'),
        row('default_language', 'en', 'str'),
        row('default_theme', 'auto', 'str'),
    ];

    /**
     * `globalSettings.load()`, with `GET /settings/global` answering `rows` for this one call, plus a `default_currency`
     * row set to `witness`. A load that fails keeps the old values without a word, and what the store held could pass
     * for a parse, so every case first proves that the store took its answer.
     */
    async function loadAnswering(rows: ReturnType<typeof row>[], witness: string): Promise<void> {
        expect(observed().default_currency, 'premise: the witness is not in the store yet').not.toBe(witness);
        listGlobalSettings.mockResolvedValueOnce({items: [row('default_currency', witness, 'string'), ...rows]});
        await globalSettings.load();
        expect(observed().default_currency, 'the store took this answer: a failed load keeps the old values silently').toBe(witness);
    }

    // `clear()` is the whole reset. It puts the singleton back on its defaults and, in a browser, drops the
    // `global_settings` localStorage cache with them; the store reads that cache only when its module loads, never
    // between cases. Here `browser` is false anyway (the shared mock), and Vitest's node environment has no
    // localStorage. `mockReset()` empties the queue of answers and puts the failing client back.
    function reset(): void {
        globalSettings.clear();
        listGlobalSettings.mockReset();
    }
    beforeEach(reset);
    afterEach(reset);

    it('holds no enable_registration at rest: the defaults no longer carry the key A5a removed', () => {
        expect(Object.keys(observed())).not.toContain('enable_registration');
    });

    it('holds no enable_registration after loading what the server sends today', async () => {
        await loadAnswering(SERVER_ROWS, 'GBP');

        expect(Object.keys(observed()), 'premise: the answer was read, registration_mode included').toContain('registration_mode');
        expect(Object.keys(observed())).not.toContain('enable_registration');
    });

    it.each(['open', 'invite', 'disabled'])('takes registration_mode %j as the plain string the server sent, like the other string settings', async (mode) => {
        await loadAnswering([row('registration_mode', mode, 'string')], 'GBP');

        expect(observed().registration_mode).toBe(mode);
    });

    it('keeps what it held when a load fails', async () => {
        // A guard, green before A5b and after it: the catch in `load()` keeps the current values.
        await loadAnswering([row('registration_mode', 'invite', 'string')], 'GBP');
        const held = {...globalSettings.get()};

        listGlobalSettings.mockRejectedValueOnce(new Error('GET /settings/global: the server did not answer'));
        // `load()` reports the failure on the console: silenced here, where the failure is the point.
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
        try {
            await globalSettings.load();
        } finally {
            consoleError.mockRestore();
        }

        expect(listGlobalSettings, 'the second read was asked, and failed').toHaveBeenCalledTimes(2);
        expect(observed().registration_mode, 'registration_mode: still what the last answer said').toBe('invite');
        expect(globalSettings.get(), 'and nothing else moved').toEqual(held);
    });
});
