// @vitest-environment node
/**
 * currencyChangeErrors — unit test (Vitest, node). Workstream X, lot X-R48.
 *
 * Why. A currency change that market data blocks goes through `AssetCurrencyChangeModal`: its confirm wipes the
 * asset's prices and events (`POST /assets/{id}/market-data/wipe`), then patches the currency. Since X-R48 the wipe
 * refuses, before writing anything, when a SPLIT of the asset has linked incoming adjustments without a purchase cost:
 * deleting the split would turn those units into purchases of unknown cost. The answer is 409 with
 * `detail = {error_code: 'MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST', message, params: {splits: [{event_id, date,
 * transaction_ids, hidden_transactions_count}, …]}}`, one entry per such split, by date: `transaction_ids` are the
 * adjustments the user can see, `hidden_transactions_count` counts the others. `message` is the server's English, totals
 * only — today the modal toasts «<failed>: <that English>» whatever the interface language.
 *
 * Contract. `wipeRefusalMessage(err, t, dateLabel = identity)` reads `err.response.data.detail` (a zodios call throws
 * the axios error as it is: the response interceptor of `zodios-client.ts` re-rejects it) and, for that code, returns
 * `t('assetDetail.currencyChange.splitAdjustmentsWithoutCost', {values: {date, n, hidden, more}})` — the first split
 * (`params.splits[0]`) by its date through `dateLabel`; `n` its adjustments without a cost, the ones in sight (the length
 * of `transaction_ids`) plus the hidden ones; `hidden` those; `more` how many other splits. A missing or malformed piece
 * counts as 0 or '': a hidden count that is not a whole number from 0, ids that are not a list, a date that is not a
 * string, a split that is not an object, splits that are not a list (and `more` is never -1). It never throws and never
 * hands `t` an object. Anything else — another code (the events save's EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST included),
 * a string detail, a 422 list, no detail, no response, nothing — is `null`, and the catalogue is not even asked: the
 * caller keeps its generic sentence.
 *
 * How. First a fake `t`, as in `eventSaveError.test.ts`: it records the key and the values and renders them the way a
 * template does (`String(value)`), so an object handed over would read `[object Object]` here exactly as on screen.
 * Then the real catalogues: the generated `<lang>.json` that Vitest's global setup builds from the sources
 * (`scripts/i18n_catalog.py`, which fills a key a language lacks with the English text — so «in Italian» means «not the
 * English text»). Each text is read as the runtime parses it, never with a regex: it names exactly `date`, `n`,
 * `hidden` and `more` (a name the module does not pass leaves the raw text on screen; one it passes and the text drops
 * is a figure lost), and counts `n`, `hidden` and `more` with ICU plurals. Last, the module through svelte-i18n, as the
 * app passes `$t`, each language formatted while it is the current one (devpy-i18n, rule 5): every value written, no
 * ICU syntax left, and no figure 0 — with nothing hidden and no other split, the sentence says nothing of either. No
 * assertion reads the wording.
 *
 * Expected. Red before the cure, by absence: `currencyChangeErrors.ts` does not exist, so this file fails to load. With
 * the module but not the key, the catalogue cases stay red (the key echoed back, or the English text in it/fr/es).
 * Green once the module and the key in the four sources (`src/lib/i18n/assets/<lang>.json`) are in. The parse control
 * is green as soon as the file loads.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit` (action
 * `core-unit`), next to `currencyBlocker.test.ts`.
 */
import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';
import {getMessageFormatter, init, waitLocale} from 'svelte-i18n';
import {_, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {wipeRefusalMessage} from './currencyChangeErrors';

const CODE = 'MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST';
const KEY = 'assetDetail.currencyChange.splitAdjustmentsWithoutCost';

type Values = Record<string, string | number>;
type Call = {key: string; values: Values | undefined};

/** A stand-in for svelte-i18n's `$t`: it records each key and its values, and renders them as a template would. */
function fakeT() {
    const calls: Call[] = [];
    const outputs: string[] = [];
    const t = (key: string, options?: {values?: Values}): string => {
        calls.push({key, values: options?.values});
        const rendered = Object.entries(options?.values ?? {}).map(([name, value]) => `${name}=${String(value)}`);
        const output = [key, ...rendered].join(' | ');
        outputs.push(output);
        return output;
    };
    return {t, calls, outputs};
}

/** The error a zodios (axios) call throws for an HTTP answer carrying `detail`. */
function apiError(status: number, detail: unknown): Error & {response: {status: number; data: {detail: unknown}}} {
    return Object.assign(new Error(`Request failed with status code ${status}`), {response: {status, data: {detail}}});
}

/** The server's own sentence, English and totals only: the user must never read it. */
const SERVER_SENTENCE = "Market data not wiped: the server's own sentence";

/** The wipe's refusal, 409, with its params as given. */
function wipeRefused(params: unknown) {
    return apiError(409, {error_code: CODE, message: SERVER_SENTENCE, params});
}

/** One split as the refusal lists it: its date, the adjustments the user can see, and how many others. */
function split(date: string, transactionIds: unknown[], hidden: number, eventId = 12) {
    return {event_id: eventId, date, transaction_ids: transactionIds, hidden_transactions_count: hidden};
}

const dateLabel = (iso: string) => `D<${iso}>`;

/** The one translation a message is built from. */
function onlyCall(calls: Call[]): Call {
    expect(calls, 'one message, one translation').toHaveLength(1);
    return calls[0];
}

/** What a sentence for the user never carries. */
function expectReadable(message: string) {
    expect(message).not.toContain('[object Object]');
    expect(message).not.toContain("the server's own sentence");
    expect(message).not.toContain(CODE);
}

describe('wipeRefusalMessage — a split whose adjustments have no purchase cost (X-R48)', () => {
    it('one split, one adjustment in sight and none hidden: its date as the server wrote it, n 1, hidden 0, more 0', () => {
        const {t, calls, outputs} = fakeT();
        const message = wipeRefusalMessage(wipeRefused({splits: [split('2026-02-10', [5], 0)]}), t);

        expect(onlyCall(calls)).toEqual({key: KEY, values: {date: '2026-02-10', n: 1, hidden: 0, more: 0}});
        expect(message, 'the sentence is the translation, as t wrote it').toBe(outputs[0]);
        expectReadable(String(message));
    });

    it('fail-closed, none in sight: no id listed and two hidden — n 2, hidden 2', () => {
        const {t, calls, outputs} = fakeT();
        const message = wipeRefusalMessage(wipeRefused({splits: [split('2026-02-10', [], 2)]}), t);

        expect(onlyCall(calls)).toEqual({key: KEY, values: {date: '2026-02-10', n: 2, hidden: 2, more: 0}});
        expect(message).toBe(outputs[0]);
        expectReadable(String(message));
    });

    it('two splits: the first is named — its date, its adjustments — and the second is only counted in more', () => {
        const {t, calls} = fakeT();
        // The second split differs from the first in every value: a sum, or the last split, reads otherwise.
        const splits = [split('2026-02-10', [5], 1, 12), split('2026-05-04', [7, 8, 9], 4, 15)];
        const message = wipeRefusalMessage(wipeRefused({splits}), t);

        expect(onlyCall(calls)).toEqual({key: KEY, values: {date: '2026-02-10', n: 2, hidden: 1, more: 1}});
        expectReadable(String(message));
    });

    it("the date label is applied to the first split's date", () => {
        const {t, calls} = fakeT();
        const splits = [split('2026-02-10', [5, 6], 0, 12), split('2026-05-04', [7], 0, 15)];
        wipeRefusalMessage(wipeRefused({splits}), t, dateLabel);

        expect(onlyCall(calls)).toEqual({key: KEY, values: {date: 'D<2026-02-10>', n: 2, hidden: 0, more: 1}});
    });

    it.each<[string, unknown, Values]>([
        ['params missing', undefined, {date: '', n: 0, hidden: 0, more: 0}],
        ['params null', null, {date: '', n: 0, hidden: 0, more: 0}],
        ['params without splits', {}, {date: '', n: 0, hidden: 0, more: 0}],
        ['splits an empty list (more is never -1)', {splits: []}, {date: '', n: 0, hidden: 0, more: 0}],
        ['splits not a list: an object with a length', {splits: {0: split('2026-02-10', [5], 1), length: 1}}, {date: '', n: 0, hidden: 0, more: 0}],
        ['splits not a list: a string', {splits: '2026-02-10'}, {date: '', n: 0, hidden: 0, more: 0}],
        ['a split that is not an object', {splits: [null]}, {date: '', n: 0, hidden: 0, more: 0}],
        ['a split without transaction_ids', {splits: [{event_id: 12, date: '2026-02-10', hidden_transactions_count: 0}]}, {date: '2026-02-10', n: 0, hidden: 0, more: 0}],
    ])('%s: no throw — each missing piece is 0 or the empty string', (_label, params, values) => {
        const {t, calls} = fakeT();
        const message = wipeRefusalMessage(wipeRefused(params), t);

        expect(onlyCall(calls)).toEqual({key: KEY, values});
        expectReadable(String(message));
    });

    it.each<[string, Record<string, unknown>, number, number]>([
        ['hidden_transactions_count missing', {transaction_ids: [5, 6]}, 2, 0],
        ["hidden_transactions_count 'x'", {transaction_ids: [5, 6], hidden_transactions_count: 'x'}, 2, 0],
        ['hidden_transactions_count null', {transaction_ids: [5, 6], hidden_transactions_count: null}, 2, 0],
        ['hidden_transactions_count -1', {transaction_ids: [5, 6], hidden_transactions_count: -1}, 2, 0],
        ['hidden_transactions_count 1.5', {transaction_ids: [5, 6], hidden_transactions_count: 1.5}, 2, 0],
        // Not a list: no id in sight, whatever a length says.
        ["transaction_ids a string, '5,6'", {transaction_ids: '5,6', hidden_transactions_count: 1}, 1, 1],
        ['transaction_ids an object with a length', {transaction_ids: {0: 5, 1: 6, length: 2}, hidden_transactions_count: 1}, 1, 1],
        ['transaction_ids null', {transaction_ids: null, hidden_transactions_count: 1}, 1, 1],
    ])('%s: hidden is a whole number from 0, n the ids listed plus the hidden ones — never NaN', (_label, adjustments, n, hidden) => {
        const {t, calls} = fakeT();
        wipeRefusalMessage(wipeRefused({splits: [{event_id: 12, date: '2026-02-10', ...adjustments}]}), t);

        expect(onlyCall(calls)).toEqual({key: KEY, values: {date: '2026-02-10', n, hidden, more: 0}});
    });

    it.each<[string, unknown]>([
        ['an object', {year: 2026, month: 2, day: 10}],
        ['null', null],
        ['missing', undefined],
    ])('a date that is not a string (%s) is the empty string — never [object Object]', (_label, date) => {
        const {t, calls} = fakeT();
        const message = wipeRefusalMessage(wipeRefused({splits: [{event_id: 12, date, transaction_ids: [5], hidden_transactions_count: 0}]}), t);

        expect(onlyCall(calls)).toEqual({key: KEY, values: {date: '', n: 1, hidden: 0, more: 0}});
        expectReadable(String(message));
    });
});

describe('wipeRefusalMessage — anything else is null, and the catalogue is not asked', () => {
    const SPLITS = {splits: [split('2026-02-10', [5], 1)]};

    it.each<[string, unknown]>([
        // A near miss: the events save refuses a split's retype for the same reason, with params of the same kind.
        [
            "the events save's refusal of a split (EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST)",
            apiError(409, {error_code: 'EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST', message: SERVER_SENTENCE, params: {asset_id: 7, item_index: 0, event_id: 12, date: '2026-02-10', transaction_ids: [5], hidden_transactions_count: 1}}),
        ],
        ['another code, with the same splits', apiError(409, {error_code: 'MARKET_DATA_SOMETHING_NEW', message: SERVER_SENTENCE, params: SPLITS})],
        ['a structured detail without a code', apiError(409, {message: SERVER_SENTENCE, params: SPLITS})],
        ['a string detail', apiError(404, 'Asset not found')],
        ['a 422 validation list', apiError(422, [{type: 'int_parsing', loc: ['path', 'asset_id'], msg: 'Input should be a valid integer', input: 'x'}])],
        ['an answer without a detail', apiError(502, undefined)],
        ['an error without a response', new Error('Network Error')],
        ['null', null],
        ['undefined', undefined],
    ])('%s', (_label, err) => {
        const {t, calls} = fakeT();

        expect(wipeRefusalMessage(err, t)).toBeNull();
        expect(calls, 'the caller keeps its generic sentence: nothing is asked of the catalogue').toEqual([]);
    });
});

// =============================================================================
// The real catalogues
// =============================================================================

/** The four generated catalogues, typed on the app's locale list: a fifth locale without its catalogue here fails `front check`. */
const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

/** The message at a dotted key of a nested catalogue, or undefined. */
function messageAt(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

type RuntimeFormatter = ReturnType<typeof getMessageFormatter>;
type Ast = ReturnType<RuntimeFormatter['getAst']>;
type AstElement = Ast[number];
type RuntimeFormatterClass = new (message: string, locales?: string, overrideFormats?: undefined, options?: {ignoreTag?: boolean}) => RuntimeFormatter;

/** The class svelte-i18n compiles a message with, read from one of its formatters: built directly, no parse enters its text-keyed cache. */
const RuntimeMessageFormat = getMessageFormatter('⟨currencyChangeErrors probe⟩', 'en').constructor as unknown as RuntimeFormatterClass;

/** A message as the runtime parses it, with svelte-i18n's `ignoreTag`, which the app keeps. */
function parse(message: string): Ast {
    return new RuntimeMessageFormat(message, 'en', undefined, {ignoreTag: true}).getAst();
}

/** Every element of an AST, at any depth: the options of a plural or a select, the children of a tag. */
function elementsOf(ast: Ast): AstElement[] {
    return ast.flatMap((element) => {
        const options = 'options' in element ? Object.values(element.options).flatMap((option) => elementsOf(option.value)) : [];
        const children = 'children' in element ? elementsOf(element.children) : [];
        return [element, ...options, ...children];
    });
}

// Read from parses rather than imported: the `TYPE` enum lives in another transitive package.
const LITERAL_TYPE = parse('text')[0]?.type;
const PLURAL_TYPE = parse('{n, plural, other {#}}')[0]?.type;

/** The names a message needs a value for, at any depth, sorted: every element but a literal carries one, except a `#`. */
function argumentNames(message: string): string[] {
    const names = elementsOf(parse(message)).flatMap((element) => (element.type !== LITERAL_TYPE && 'value' in element && typeof element.value === 'string' ? [element.value] : []));
    return [...new Set(names)].sort();
}

/** The names a message counts with a cardinal plural, at any depth, sorted. */
function cardinalPlurals(message: string): string[] {
    const names = elementsOf(parse(message)).flatMap((element) => (element.type === PLURAL_TYPE && 'pluralType' in element && element.pluralType === 'cardinal' ? [element.value] : []));
    return [...new Set(names)].sort();
}

/** Change the UI language in place, as the language selector does; its catalogue is loaded before the next step. */
async function uiLanguage(lang: SupportedLocale): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
}

/** The figures a sentence writes, its date labels aside. */
function figures(message: string): string[] {
    return message.replace(/D<[^>]*>/g, '').match(/\d+/g) ?? [];
}

describe('the sentence in the four generated catalogues (X-R48)', () => {
    beforeAll(async () => {
        init({fallbackLocale: 'en', initialLocale: 'en'});
        await waitLocale('en');
    });

    afterEach(async () => {
        // The language is module-level state shared by every case of the file.
        await uiLanguage('en');
    });

    it('control: the parse reads a name at any depth, tells a count from a plain argument, and takes no name from a # or a literal', () => {
        const sample = '{date}: {n, plural, one {# item} other {# items{hidden, plural, =0 {} other { (# hidden)}}}}{more, select, other {}} n, hidden';

        expect(argumentNames(sample)).toEqual(['date', 'hidden', 'more', 'n']);
        expect(cardinalPlurals(sample)).toEqual(['hidden', 'n']);
        expect(cardinalPlurals('{n, selectordinal, one {#st} other {#th}}'), 'an ordinal is not a count').toEqual([]);
    });

    it.each(SUPPORTED_LOCALES)('%s: the generated catalogue has the key, in words of its own', (lang) => {
        const text = messageAt(CATALOGUES[lang], KEY);

        expect(typeof text, `the generated ${lang} catalogue has no ${KEY}`).toBe('string');
        if (lang !== 'en') expect(text, `the ${lang} source has no ${KEY}: this is the English text the build fills it with`).not.toBe(messageAt(CATALOGUES.en, KEY));
    });

    it.each(SUPPORTED_LOCALES)('%s: its text names exactly date, n, hidden and more — the values the module passes — and counts n, hidden and more with ICU plurals', (lang) => {
        const text = messageAt(CATALOGUES[lang], KEY);
        expect(typeof text, `premise: the generated ${lang} catalogue has ${KEY}`).toBe('string');

        expect(argumentNames(String(text)), 'a name the module does not pass leaves the raw text on screen; one it passes and the text drops is a figure lost').toEqual(['date', 'hidden', 'more', 'n']);
        expect(cardinalPlurals(String(text)), 'n, hidden and more are counts: ICU plurals').toEqual(['hidden', 'more', 'n']);
    });

    it.each(SUPPORTED_LOCALES)('%s: through the module and svelte-i18n, every value is written, no ICU syntax is left, and a 0 says nothing', async (lang) => {
        await uiLanguage(lang);
        // n 5 (3 in sight, 2 hidden), hidden 2, more 3: three figures above 1, which every language writes as digits.
        const several = wipeRefusalMessage(wipeRefused({splits: [split('2026-02-10', [5, 6, 7], 2, 12), split('2026-03-11', [8], 0, 13), split('2026-04-12', [], 1, 14), split('2026-05-13', [9], 0, 15)]}), get(_), dateLabel);
        // n 1, hidden 0, more 0: nothing hidden and no other split.
        const one = wipeRefusalMessage(wipeRefused({splits: [split('2026-02-10', [5], 0)]}), get(_), dateLabel);

        for (const message of [several, one]) {
            expect(message, `control: the ${lang} catalogue has the message, not the bare key`).not.toBe(KEY);
            expectReadable(String(message));
            expect(message, 'the first split, by its date label').toContain('D<2026-02-10>');
            expect(message, 'every argument and plural formatted: a name the text needs and the module does not pass leaves the raw text').not.toMatch(/[{}]/);
            expect(figures(String(message)), 'no figure 0: with nothing hidden and no other split, the sentence says nothing of either').not.toContain('0');
        }
        expect(figures(String(several)), 'n = 5, hidden = 2 and more = 3 are written').toEqual(expect.arrayContaining(['5', '2', '3']));
    });
});
