// @vitest-environment jsdom
/**
 * providerImpact — unit tests (Vitest). Workstream X, lot X5-1 (C-65a, W-B2, X-R69).
 *
 * Why. «Change the provider or its parameters» and «remove the provider» follow ONE rule: before saving, a modal
 * tells how many prices, provider events and linked transactions (that lose the link, and are kept) the change will
 * delete; on confirm both go on. The numbers come from the server's dry run, `POST /assets/provider/impact`
 * (zodios alias `provider_change_impact_api_v1_assets_provider_impact_post`). This module is the asset modal's half:
 * it asks, decides whether there is anything to say, and words the numbers; the modal itself is
 * `AssetModal.providerLifecycle.test.ts`'s.
 *
 * Contract.
 *   - `loadProviderImpact(assetId, change)` calls the alias ONCE, with `{assignments: [item], removals: []}` for
 *     `{action: 'assign', item}` and `{assignments: [], removals: [assetId]}` for `{action: 'remove'}`, and reads the
 *     result of THAT asset. It resolves `null` (the save then goes on with no dialog, the server judges) when the reason
 *     is `none`; when prices, events and unlinked transactions are all 0; when `blocking_splits` is not empty (the real
 *     call will be refused and said inline); when the request fails in any way (never thrown, a console warning); and
 *     when the answer has no result for the asset. Otherwise `{kind, pricesDeleted, eventsDeleted, transactionsUnlinked}`,
 *     the kind from the reason: params_changed → regenerate, provider_changed → switch, provider_removed → remove.
 *   - `impactValues(impact, t, locale)` gives `{what, unlinked}`: `what` the non-zero parts of prices and events joined
 *     with `Intl.ListFormat(locale, {style: 'long', type: 'conjunction'})`, each part from the catalogue keys
 *     `assets.modal.providerImpact.pricesPart` / `.eventsPart` (`{n}`); `unlinked` the key `.unlinkedSentence` (`{n}`)
 *     when transactions are unlinked, else the empty string.
 *   - `IMPACT_DIALOG` maps each kind to the whole-literal keys of its dialog and the testId of its ConfirmModal.
 *
 * How. The API facade is replaced (offline, nothing is requested). Expected sentences are computed with the real
 * catalogue through the same keys, never as literals; the language is changed in place (en, it) to prove that the
 * locale handed over, and not a constant, formats the list.
 *
 * Expected. Red before the cure, by absence: `providerImpact.ts` does not exist, so the file fails to load.
 * Registered in `scripts/test_runner/_frontend_utility.py` (Vitest list of `front_component_unit`/`front_utility_unit`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {locale} from 'svelte-i18n';
import {setupI18n} from '$test/component';
import {_, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

const mocks = vi.hoisted(() => ({
    api: {provider_change_impact_api_v1_assets_provider_impact_post: vi.fn()},
}));
vi.mock('$lib/api', () => ({zodiosApi: mocks.api}));

import {IMPACT_DIALOG, impactValues, loadProviderImpact, type ProviderChange, type ProviderImpact, type ProviderImpactKind} from './providerImpact';

const ASSET = 7101;
const impactCall = mocks.api.provider_change_impact_api_v1_assets_provider_impact_post;

type Reason = 'none' | 'params_changed' | 'provider_changed' | 'provider_removed';
type Split = {event_id: number; date: string; transaction_ids: number[]; hidden_transactions_count: number};

/** The assignment item as the modal builds it (buildProviderAssignItem), written out: an oracle of its own. */
function assignChange(assetId = ASSET): Extract<ProviderChange, {action: 'assign'}> {
    return {
        action: 'assign',
        item: {asset_id: assetId, provider_code: 'synthetic_atlas', identifier: 'SYN-ATLAS', identifier_type: 'TICKER', provider_params: {note: 'new note'}},
    };
}

/** One result of the server's answer. */
function result(overrides: Partial<{asset_id: number; action: 'assign' | 'remove'; reason: Reason; prices_deleted: number; events_deleted: number; transactions_unlinked: number; blocking_splits: Split[]}> = {}) {
    return {asset_id: ASSET, action: 'assign' as const, reason: 'params_changed' as Reason, prices_deleted: 12, events_deleted: 3, transactions_unlinked: 2, blocking_splits: [] as Split[], ...overrides};
}

function answer(...results: ReturnType<typeof result>[]) {
    impactCall.mockResolvedValue({results});
}

const REASON_TO_KIND: [Reason, ProviderImpactKind][] = [
    ['params_changed', 'regenerate'],
    ['provider_changed', 'switch'],
    ['provider_removed', 'remove'],
];

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    impactCall.mockReset();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(async () => {
    vi.restoreAllMocks();
    await locale.set('en');
});

describe('loadProviderImpact: the request', () => {
    it('assign: one call, the item alone in the assignments, no removals', async () => {
        answer(result());
        const change = assignChange();
        await loadProviderImpact(ASSET, change);

        expect(impactCall.mock.calls, 'exactly one dry-run request, handed the body alone').toStrictEqual([[{assignments: [change.item], removals: []}]]);
    });

    it('remove: one call, the asset alone in the removals, no assignments', async () => {
        answer(result({action: 'remove', reason: 'provider_removed'}));
        await loadProviderImpact(ASSET, {action: 'remove'});

        expect(impactCall.mock.calls).toStrictEqual([[{assignments: [], removals: [ASSET]}]]);
    });
});

describe('loadProviderImpact: the impact', () => {
    it.each(REASON_TO_KIND)('reason %s is the kind %s, with the numbers of the answer', async (reason, kind) => {
        const action = reason === 'provider_removed' ? 'remove' : 'assign';
        answer(result({action, reason, prices_deleted: 12, events_deleted: 3, transactions_unlinked: 2}));
        const impact = await loadProviderImpact(ASSET, action === 'remove' ? {action: 'remove'} : assignChange());

        expect(impact).toStrictEqual({kind, pricesDeleted: 12, eventsDeleted: 3, transactionsUnlinked: 2} satisfies ProviderImpact);
    });

    it.each([
        ['prices alone', {prices_deleted: 5, events_deleted: 0, transactions_unlinked: 0}, {pricesDeleted: 5, eventsDeleted: 0, transactionsUnlinked: 0}],
        ['events alone', {prices_deleted: 0, events_deleted: 4, transactions_unlinked: 0}, {pricesDeleted: 0, eventsDeleted: 4, transactionsUnlinked: 0}],
        ['unlinked transactions alone', {prices_deleted: 0, events_deleted: 0, transactions_unlinked: 6}, {pricesDeleted: 0, eventsDeleted: 0, transactionsUnlinked: 6}],
    ])('%s are enough to say something', async (_label, counts, expected) => {
        answer(result({reason: 'provider_changed', ...counts}));
        const impact = await loadProviderImpact(ASSET, assignChange());

        expect(impact).toStrictEqual({kind: 'switch', ...expected});
    });

    it('an empty blocking_splits list does not silence the dialog', async () => {
        answer(result({blocking_splits: []}));
        expect(await loadProviderImpact(ASSET, assignChange())).not.toBeNull();
    });

    it('reads the result of its own asset, whatever its place in the answer', async () => {
        answer(result({asset_id: ASSET + 1, reason: 'provider_changed', prices_deleted: 99, events_deleted: 99, transactions_unlinked: 99}), result({asset_id: ASSET, reason: 'params_changed', prices_deleted: 1, events_deleted: 2, transactions_unlinked: 3}));
        const impact = await loadProviderImpact(ASSET, assignChange());

        expect(impact).toStrictEqual({kind: 'regenerate', pricesDeleted: 1, eventsDeleted: 2, transactionsUnlinked: 3});
    });
});

describe('loadProviderImpact: no dialog (null), the save goes on and the server judges', () => {
    it('reason none, even with numbers in the answer', async () => {
        answer(result({reason: 'none'}));
        expect(await loadProviderImpact(ASSET, assignChange())).toBeNull();
    });

    it.each(REASON_TO_KIND)('reason %s with nothing to delete (no prices, no events, no transactions)', async (reason) => {
        const action = reason === 'provider_removed' ? 'remove' : 'assign';
        answer(result({action, reason, prices_deleted: 0, events_deleted: 0, transactions_unlinked: 0}));
        expect(await loadProviderImpact(ASSET, action === 'remove' ? {action: 'remove'} : assignChange())).toBeNull();
    });

    it('a blocking split: the real call will be refused and said inline, a dialog would only mislead', async () => {
        answer(result({blocking_splits: [{event_id: 31, date: '2026-02-10', transaction_ids: [5], hidden_transactions_count: 1}]}));
        expect(await loadProviderImpact(ASSET, assignChange())).toBeNull();
    });

    it('a blocking split on a removal too', async () => {
        answer(result({action: 'remove', reason: 'provider_removed', blocking_splits: [{event_id: 31, date: '2026-02-10', transaction_ids: [], hidden_transactions_count: 2}]}));
        expect(await loadProviderImpact(ASSET, {action: 'remove'})).toBeNull();
    });

    it('a rejected request: never thrown, one console warning', async () => {
        impactCall.mockRejectedValue(Object.assign(new Error('Request failed with status code 500'), {response: {status: 500, data: {detail: 'boom'}}}));
        await expect(loadProviderImpact(ASSET, assignChange())).resolves.toBeNull();
        expect(console.warn).toHaveBeenCalledTimes(1);
    });

    it('a call that throws at once, before any promise: never thrown either', async () => {
        impactCall.mockImplementation(() => {
            throw new Error('synchronous failure');
        });
        await expect(loadProviderImpact(ASSET, {action: 'remove'})).resolves.toBeNull();
        expect(console.warn).toHaveBeenCalledTimes(1);
    });

    it.each([
        ['an empty list', {results: []}],
        ['the result of another asset only', {results: [result({asset_id: ASSET + 1})]}],
        ['no list at all', {}],
        ['no answer body', undefined],
    ])('the answer has no result for the asset: %s', async (_label, body) => {
        impactCall.mockResolvedValue(body);
        await expect(loadProviderImpact(ASSET, assignChange())).resolves.toBeNull();
    });
});

/** The catalogue's text of a key in the current language, as the app words it. */
function words(key: string, values: Record<string, string | number> = {}): string {
    return get(_)(key, {values});
}

const PRICES = 'assets.modal.providerImpact.pricesPart';
const EVENTS = 'assets.modal.providerImpact.eventsPart';
const UNLINKED = 'assets.modal.providerImpact.unlinkedSentence';

function impactOf(pricesDeleted: number, eventsDeleted: number, transactionsUnlinked: number, kind: ProviderImpactKind = 'regenerate'): ProviderImpact {
    return {kind, pricesDeleted, eventsDeleted, transactionsUnlinked};
}

function list(lang: string, parts: string[]): string {
    return new Intl.ListFormat(lang, {style: 'long', type: 'conjunction'}).format(parts);
}

describe('impactValues', () => {
    it('premise: the parts and the sentence are in the catalogue as sentences, not as their keys', () => {
        for (const key of [PRICES, EVENTS, UNLINKED]) expect(words(key, {n: 2}), key).not.toBe(key);
    });

    it('both parts, joined as the interface language joins a list; the unlinked sentence beside them', () => {
        const values = impactValues(impactOf(12, 3, 2), get(_), 'en');

        expect(values.what).toBe(list('en', [words(PRICES, {n: 12}), words(EVENTS, {n: 3})]));
        expect(values.unlinked).toBe(words(UNLINKED, {n: 2}));
        expect(values.what, 'the two parts, each with its own figure').toContain('12');
        expect(values.what).toContain('3');
    });

    it('prices alone: no events part, no joiner', () => {
        const values = impactValues(impactOf(8, 0, 0), get(_), 'en');

        expect(values.what).toBe(words(PRICES, {n: 8}));
        expect(values.unlinked, 'nothing unlinked, nothing said').toBe('');
    });

    it('events alone: no prices part', () => {
        const values = impactValues(impactOf(0, 5, 0), get(_), 'en');

        expect(values.what).toBe(words(EVENTS, {n: 5}));
        expect(values.unlinked).toBe('');
    });

    it('transactions alone: the sentence is there, and what is the empty string, not a stray joiner', () => {
        const values = impactValues(impactOf(0, 0, 4), get(_), 'en');

        expect(values.what).toBe('');
        expect(values.unlinked).toBe(words(UNLINKED, {n: 4}));
    });

    it('the singular is the catalogue’s plural rule, not the module’s: n goes through as the number', () => {
        const values = impactValues(impactOf(1, 1, 1), get(_), 'en');

        expect(values.what).toBe(list('en', [words(PRICES, {n: 1}), words(EVENTS, {n: 1})]));
        expect(values.unlinked).toBe(words(UNLINKED, {n: 1}));
        expect(words(PRICES, {n: 1}), 'premise: one and many are worded differently').not.toBe(words(PRICES, {n: 2}));
    });

    it('the kind changes nothing of the values', () => {
        const kinds: ProviderImpactKind[] = ['regenerate', 'switch', 'remove'];
        const [first, ...others] = kinds.map((kind) => impactValues(impactOf(2, 2, 2, kind), get(_), 'en'));
        for (const other of others) expect(other).toStrictEqual(first);
    });

    it.each<SupportedLocale>(['en', 'it'])('in %s: the list is formatted with the locale handed over and the parts are that language’s', async (lang) => {
        await locale.set(lang);
        const parts = [words(PRICES, {n: 12}), words(EVENTS, {n: 3})];
        const values = impactValues(impactOf(12, 3, 2), get(_), lang);

        expect(values.what).toBe(list(lang, parts));
        expect(values.unlinked).toBe(words(UNLINKED, {n: 2}));
        expect(parts[0], `premise: the ${lang} catalogue has the parts`).not.toBe(PRICES);
        // The joiner is the one Intl writes for the language: a constant «, » or «and» would not survive the Italian one.
        expect(values.what).toBe(`${parts[0]} ${lang === 'it' ? 'e' : 'and'} ${parts[1]}`);
    });

    it('the locale argument decides the joiner, not the interface language', async () => {
        await locale.set('en');
        const parts = [words(PRICES, {n: 2}), words(EVENTS, {n: 2})];

        expect(impactValues(impactOf(2, 2, 0), get(_), 'it').what).toBe(list('it', parts));
        expect(list('it', parts), 'premise: the two languages join differently').not.toBe(list('en', parts));
    });
});

describe('IMPACT_DIALOG', () => {
    const TEST_IDS: Record<ProviderImpactKind, string> = {
        regenerate: 'asset-scheduled-regen-confirm',
        switch: 'asset-parametric-switch-confirm',
        remove: 'asset-provider-remove-confirm',
    };

    it('has the three kinds, nothing else', () => {
        expect(Object.keys(IMPACT_DIALOG).sort()).toEqual(['regenerate', 'remove', 'switch']);
    });

    it.each(Object.entries(TEST_IDS))('%s: the testId the E2E suite drives, and the whole-literal keys of its title, message and confirm', (kind, testId) => {
        const dialog = IMPACT_DIALOG[kind as ProviderImpactKind];

        expect(dialog.testId).toBe(testId);
        expect(dialog.title).toBe(`assets.modal.providerImpact.${kind}Title`);
        expect(dialog.message).toBe(`assets.modal.providerImpact.${kind}Message`);
        expect(dialog.confirm).toBe(`assets.modal.providerImpact.${kind}Confirm`);
    });

    it('the three testIds are different', () => {
        expect(new Set(Object.values(IMPACT_DIALOG).map((dialog) => dialog.testId)).size).toBe(3);
    });
});

/** A key at its path in a generated catalogue, or undefined. */
function lookup(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

describe('the catalogues carry what the dialogs say (the four languages)', () => {
    const keys = [PRICES, EVENTS, UNLINKED, ...Object.values(IMPACT_DIALOG).flatMap((dialog) => [dialog.title, dialog.message, dialog.confirm])];

    it.each(SUPPORTED_LOCALES)('%s has every key of the dialogs and of the values, as text', (lang) => {
        for (const key of keys) {
            const text = lookup(CATALOGUES[lang], key);
            expect(typeof text, `${lang}: ${key}`).toBe('string');
            expect((text as string).length, `${lang}: ${key} is not empty`).toBeGreaterThan(0);
        }
    });

    it.each(SUPPORTED_LOCALES)('%s: each message writes its values (what, unlinked, and for the switch from and to) and leaves no placeholder raw', async (lang) => {
        await locale.set(lang);
        const marks = {what: 'WHAT⁣MARK', unlinked: 'UNLINKED⁣MARK', from: 'FROM⁣MARK', to: 'TO⁣MARK'};
        for (const kind of ['regenerate', 'switch', 'remove'] as const) {
            const text = words(IMPACT_DIALOG[kind].message, marks);
            expect(text, `${lang} ${kind}: what`).toContain(marks.what);
            expect(text, `${lang} ${kind}: unlinked`).toContain(marks.unlinked);
            if (kind === 'switch') {
                expect(text, `${lang} switch: from`).toContain(marks.from);
                expect(text, `${lang} switch: to`).toContain(marks.to);
            } else {
                expect(text, `${lang} ${kind}: no provider names`).not.toContain(marks.from);
            }
            expect(text, `${lang} ${kind}: nothing left raw`).not.toMatch(/[{}]/);
        }
    });
});
