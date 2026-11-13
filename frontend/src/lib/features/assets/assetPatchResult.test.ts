// @vitest-environment node
/**
 * assetPatchResult — unit test (Vitest, node). Lane 65, lot F1.
 *
 * Contract. `PATCH /assets` is all or nothing and answers 200 either way, with `committed`, `issues` and `warnings`.
 * `assertPatchCommitted(answer, t, fallback)` returns the answer when `committed` is true, and otherwise throws an
 * `AssetPatchRefused` whose message is the sentence of the first issue (`patchIssueMessage`) or `fallback` when the answer
 * has no issue: an answer that does not say `committed` is not a save. `patchIssueMessage(issue, t)` asks the catalogue
 * for `assets.patchIssue.<code>` with the values its params carry (`name`, `count` from `tx_count`, `from`, `to`, `id`);
 * an unknown code, a prototype name included, keeps the issue's own English message and asks nothing.
 *
 * How. A fake `t` records key and values (as `currencyChangeErrors.test.ts`). The catalogues are the generated
 * `<lang>.json`: each key holds in the four languages, in words of its own, naming exactly the values the module passes
 * for it; through svelte-i18n, with every value written and no ICU syntax left. No assertion reads the wording.
 */
import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';
import {init, waitLocale} from 'svelte-i18n';
import {_, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {assertPatchCommitted, AssetPatchRefused, patchIssueMessage, type AssetPatchIssue} from './assetPatchResult';

type Values = Record<string, string | number>;

function fakeT() {
    const calls: {key: string; values: Values | undefined}[] = [];
    const t = (key: string, options?: {values?: Values}): string => {
        calls.push({key, values: options?.values});
        return `${key}|${Object.entries(options?.values ?? {})
            .map(([name, value]) => `${name}=${String(value)}`)
            .join('|')}`;
    };
    return {t, calls};
}

const issue = (code: string, params: Record<string, unknown> | null = null, assetId = 5): AssetPatchIssue => ({asset_id: assetId, index: 0, code, message: `English ${code}`, params});

/** Each code's key and the values the module hands over for it. */
const CASES: {code: string; key: string; params: Record<string, unknown> | null; values: Values; names: string[]}[] = [
    {code: 'assetNotFound', key: 'assets.patchIssue.assetNotFound', params: null, values: {name: '', count: 0, from: '', to: '', id: 5}, names: []},
    {code: 'indexWithTransactions', key: 'assets.patchIssue.indexWithTransactions', params: {tx_count: 12}, values: {name: '', count: 12, from: '', to: '', id: 5}, names: ['count']},
    {code: 'assetNameTaken', key: 'assets.patchIssue.assetNameTaken', params: {name: 'Acme Corp'}, values: {name: 'Acme Corp', count: 0, from: '', to: '', id: 5}, names: ['name']},
    {code: 'assetFamilyChange', key: 'assets.patchIssue.assetFamilyChange', params: {from: 'STOCK', to: 'BOND'}, values: {name: '', count: 0, from: 'STOCK', to: 'BOND', id: 5}, names: ['from', 'to']},
    {code: 'patchFailed', key: 'assets.patchIssue.patchFailed', params: null, values: {name: '', count: 0, from: '', to: '', id: 5}, names: []},
];

describe('patchIssueMessage', () => {
    it.each(CASES)('$code asks $key with the values of its params', ({code, key, params, values}) => {
        const {t, calls} = fakeT();
        const out = patchIssueMessage(issue(code, params), t);
        expect(calls).toEqual([{key, values}]);
        expect(out.startsWith(`${key}|`)).toBe(true);
    });

    it.each(['somethingNew', 'constructor', 'toString', '__proto__'])('the unknown code %s keeps the backend message and asks nothing', (code) => {
        const {t, calls} = fakeT();
        expect(patchIssueMessage(issue(code), t)).toBe(`English ${code}`);
        expect(calls).toEqual([]);
    });

    it('a malformed param is 0 or empty, never an object handed to the catalogue', () => {
        const {t, calls} = fakeT();
        patchIssueMessage(issue('indexWithTransactions', {tx_count: {no: 1}}), t);
        patchIssueMessage(issue('assetNameTaken', {name: {no: 1}}), t);
        expect(calls[0].values).toMatchObject({count: 0});
        expect(calls[1].values).toMatchObject({name: ''});
    });
});

describe('assertPatchCommitted', () => {
    it('returns the answer when committed is true', () => {
        const {t} = fakeT();
        const answer = {committed: true, issues: [], warnings: [issue('assetFamilyChange', {from: 'STOCK', to: 'BOND'})]};
        expect(assertPatchCommitted(answer, t, 'fallback')).toBe(answer);
    });

    it('throws AssetPatchRefused with the sentence of the first issue and all the issues attached', () => {
        const {t} = fakeT();
        const first = issue('indexWithTransactions', {tx_count: 3}, 8);
        const second = issue('assetNotFound', null, 9);
        let thrown: unknown;
        try {
            assertPatchCommitted({committed: false, issues: [first, second]}, t, 'fallback');
        } catch (err) {
            thrown = err;
        }
        expect(thrown).toBeInstanceOf(AssetPatchRefused);
        expect((thrown as AssetPatchRefused).message.startsWith('assets.patchIssue.indexWithTransactions|')).toBe(true);
        expect((thrown as AssetPatchRefused).issues).toEqual([first, second]);
    });

    it.each([{committed: false, issues: []}, {committed: false}, {}, {committed: undefined, issues: undefined}])('%j has no committed=true: throws the fallback', (answer) => {
        const {t} = fakeT();
        expect(() => assertPatchCommitted(answer, t, 'fallback')).toThrow('fallback');
    });

    it('an old answer with results only (no committed) is not taken for a save', () => {
        const {t} = fakeT();
        expect(() => assertPatchCommitted({results: [{success: true}]} as never, t, 'fallback')).toThrow('fallback');
    });
});

const CATALOGUES: Record<SupportedLocale, Record<string, unknown>> = {en, it: itCatalogue, fr, es};

describe('catalogue — assets.patchIssue.*', () => {
    beforeAll(async () => {
        init({fallbackLocale: 'en', initialLocale: 'en'});
        await waitLocale('en');
    });

    afterEach(async () => {
        currentLanguage.set('en');
        await waitLocale('en');
    });

    const textOf = (locale: SupportedLocale, key: string): string => {
        const value = key.split('.').reduce<unknown>((node, part) => (node && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), CATALOGUES[locale]);
        expect(typeof value, `${key} in ${locale}`).toBe('string');
        return value as string;
    };

    it.each(CASES)('$key holds in the four languages, in words of its own, naming exactly its values', ({key, names}) => {
        for (const locale of SUPPORTED_LOCALES) {
            const text = textOf(locale, key);
            expect(text.length).toBeGreaterThan(0);
            const used = [...new Set([...text.matchAll(/\{\s*(\w+)\s*[,}]/g)].map((m) => m[1]))].sort();
            expect(used, `${key} in ${locale}`).toEqual([...names].sort());
            if (locale !== 'en') expect(text, `${key} is translated in ${locale}`).not.toBe(textOf('en', key));
        }
    });

    it.each(CASES)('$key formats through svelte-i18n with every value written and no ICU syntax left', async ({key, values}) => {
        const filled: Values = {...values, name: values.name || 'Some Name', from: values.from || 'STOCK', to: values.to || 'BOND'};
        for (const locale of SUPPORTED_LOCALES) {
            currentLanguage.set(locale);
            await waitLocale(locale);
            const out = get(_)(key, {values: filled});
            expect(out, `${key} in ${locale}`).not.toMatch(/[{}]|plural/);
            for (const [name, value] of Object.entries(filled)) {
                if (['name', 'count', 'from', 'to'].includes(name) && textOf(locale, key).includes(`{${name}`)) expect(out, `${name} in ${locale}`).toContain(String(value));
            }
        }
    });
});
