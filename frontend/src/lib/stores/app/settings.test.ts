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
