/**
 * Which case of the common «to configure» window a provider is in (project 76, N3a): the pure rule the window, the
 * search chip, the provider select and the FX routes all read, from the provider list's own fields
 * (`configured`, `missing_settings`, `missing_reason`, `invalid_variables`, N1/N2b) and the viewer's role.
 *
 * The case table, the consultant's texts (mock section 1.4) completed with section 2.4's:
 *
 * | reason                   | variables named            | administrator      | other user        |
 * |--------------------------|----------------------------|--------------------|-------------------|
 * | missing_fields (or none) | —                          | missing_admin (A)  | missing_member (B)|
 * | invalid_locked_setting   | a call-limit variable      | invalid_limit_admin| invalid_member    |
 * | invalid_locked_setting   | another variable           | invalid_admin (C)  | invalid_member    |
 * | invalid_locked_setting   | none (the managed profile) | managed (D)        | managed (D)       |
 *
 * D is read from the data alone: outside the managed profile the server names the invalid variable, in it never.
 */
import {describe, expect, it} from 'vitest';

import {isCallLimitVariable, needsSetup, notConfiguredCase, type ProviderReadiness} from './notConfigured';

const missing: ProviderReadiness = {configured: false, missing_settings: ['api_key'], missing_reason: 'missing_fields', invalid_variables: []};
const invalidKey: ProviderReadiness = {configured: false, missing_settings: ['api_key'], missing_reason: 'invalid_locked_setting', invalid_variables: ['LIBREFOLIO_PLUGIN_GROUP_COINGECKO_API_KEY']};
const invalidLimit: ProviderReadiness = {configured: false, missing_settings: ['call_limit_day'], missing_reason: 'invalid_locked_setting', invalid_variables: ['LIBREFOLIO_PLUGIN_ASSET_YFINANCE_CALL_LIMIT_DAY']};
const managed: ProviderReadiness = {configured: false, missing_settings: [], missing_reason: 'invalid_locked_setting', invalid_variables: []};

describe('needsSetup: only a provider the server says is not configured', () => {
    it('is true for configured false, false for true and for a list without the field (an older server)', () => {
        expect(needsSetup(missing)).toBe(true);
        expect(needsSetup({configured: true})).toBe(false);
        expect(needsSetup({})).toBe(false);
        expect(needsSetup(null)).toBe(false);
        expect(needsSetup(undefined)).toBe(false);
    });
});

describe('notConfiguredCase: the case table', () => {
    it('missing fields: A for an administrator, B for another user', () => {
        expect(notConfiguredCase(missing, true)).toBe('missing_admin');
        expect(notConfiguredCase(missing, false)).toBe('missing_member');
    });

    it('a not-configured provider with no reason (an older server) reads as missing fields', () => {
        expect(notConfiguredCase({configured: false}, true)).toBe('missing_admin');
        expect(notConfiguredCase({configured: false, missing_reason: null}, false)).toBe('missing_member');
    });

    it('an invalid variable outside managed: C for an administrator, the limit text for a call-limit variable, the «stopped» text for another user', () => {
        expect(notConfiguredCase(invalidKey, true)).toBe('invalid_admin');
        expect(notConfiguredCase(invalidLimit, true)).toBe('invalid_limit_admin');
        expect(notConfiguredCase(invalidKey, false)).toBe('invalid_member');
        expect(notConfiguredCase(invalidLimit, false)).toBe('invalid_member');
    });

    it('an invalid variable that the server does not name is the managed profile: D for everyone', () => {
        expect(notConfiguredCase(managed, true)).toBe('managed');
        expect(notConfiguredCase(managed, false)).toBe('managed');
        expect(notConfiguredCase({...managed, invalid_variables: undefined}, true)).toBe('managed');
    });

    it('a limit variable among several makes it the limit text only when every variable named is a limit', () => {
        const mixed = {...invalidLimit, invalid_variables: ['LIBREFOLIO_PLUGIN_ASSET_YFINANCE_CALL_LIMIT_DAY', 'LIBREFOLIO_PLUGIN_ASSET_YFINANCE_API_KEY']};
        expect(notConfiguredCase(mixed, true)).toBe('invalid_admin');
    });
});

describe('isCallLimitVariable: the five windows of the core limits', () => {
    it('reads the suffix of the derived name', () => {
        for (const window of ['MINUTE', 'HOUR', 'DAY', 'WEEK', 'MONTH']) expect(isCallLimitVariable(`LIBREFOLIO_PLUGIN_FX_ECB_CALL_LIMIT_${window}`)).toBe(true);
        expect(isCallLimitVariable('LIBREFOLIO_PLUGIN_FX_ECB_CALL_LIMIT_YEAR')).toBe(false);
        expect(isCallLimitVariable('LIBREFOLIO_PLUGIN_GROUP_COINGECKO_API_KEY')).toBe(false);
        expect(isCallLimitVariable('LIBREFOLIO_PLUGIN_ASSET_YFINANCE_CALL_LIMIT_DAY_FILE')).toBe(false);
    });
});

describe('the window texts, through the real catalogue', () => {
    it('the missing-fields messages agree with the count, in every language', async () => {
        const {setupI18n} = await import('$test/component');
        const {get} = await import('svelte/store');
        const {_, locale} = await import('$lib/i18n');
        await setupI18n('en');
        for (const language of ['en', 'it', 'fr', 'es']) {
            locale.set(language);
            const {waitLocale} = await import('svelte-i18n');
            await waitLocale(language);
            const t = get(_);
            for (const key of ['pluginSettings.notConfigured.missingAdmin', 'pluginSettings.notConfigured.missingMember']) {
                const one = t(key, {values: {provider: 'CoinGecko', count: 1, fields: 'API key'}});
                const two = t(key, {values: {provider: 'CoinGecko', count: 2, fields: 'API key, Plan'}});
                expect(one, `${language} ${key}`).toContain('CoinGecko');
                expect(one).toContain('API key');
                expect(two).toContain('API key, Plan');
                expect(one, `${language} ${key}: the plural picks a different form`).not.toEqual(two.replace('API key, Plan', 'API key'));
                expect(one).not.toContain('{');
            }
        }
        locale.set('en');
    });
});
