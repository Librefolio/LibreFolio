/**
 * eventSaveError — unit test (Vitest, node). Release 1.3, decisions 20–23 (workstream W, lot E1b).
 *
 * A refused `POST /assets/events` writes nothing and says why and where: `detail = {error_code,
 * message, params}` (400, or 409 for EVENT_EXISTS), or a validation list (422) whose `loc` names
 * the event. This module turns that into one sentence in the interface language, naming the event
 * at fault, and hands «+ New event» the events already on its date and type.
 *
 * What is pinned, per refusal: the catalogue key and the values it is given — the row's date and
 * type, through the caller's labels; for a currency mismatch the first mismatched event plus how
 * many more; for a 422 on a type, the value sent and the date of the row it names
 * (`sent[index]`). Everything that is not a structured refusal (a string detail, a network error,
 * nothing at all) is the generic sentence. Never `[object Object]`, never the raw code.
 *
 * The deletions an item carries (`delete_ids`, E1b) have two refusals of their own: EVENT_IN_USE
 * (409) names the first event in use — its date and type, how many transactions it carries (`n`) —
 * and how many more; EVENT_NOT_DELETABLE (400) has its own sentence. Neither is an EVENT_EXISTS:
 * an in-use refusal is a 409 too, and lists events too, but «+ New event» must not offer them.
 *
 * `existingAmountText` is how a stored amount reads in the EVENT_EXISTS panel and in the form
 * «Edit this» opens: as written, with at least two decimals.
 *
 * C-97b: EVENT_TOO_MANY_DIGITS (400, C-97a) — a value with more digits than an event keeps — gets a
 * sentence of its own, `events.saveError.tooManyDigits`, naming the first event at fault, how many
 * more, and the decimal places a value keeps (`max`). Every other code keeps its sentence.
 *
 * X-R47, W's review (LOW): the ratio of a refused split is written in the interface locale
 * (`formatExactDecimal`), from the string the server echoes and never through a float: «-0,5» in Italian,
 * French and Spanish. Red before the cure for it/fr/es; the English case, and a ratio of 0, are guards.
 *
 * `t` is a stand-in for svelte-i18n's `$t`: it records the key and the values and renders them the
 * way a template does (`String(value)`), so an object passed as a value would show as
 * `[object Object]` here exactly as it would on screen.
 *
 * Before E1b `eventSaveError.ts` does not exist: this file fails to load. Against the first draft
 * (no deletions, no `existingAmountText`) it fails to load too: the import names a missing export.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {eventRefusal, eventSaveErrorMessage, existingAmountText, existingEvents, type ExistingEvent} from './eventSaveError';

type Values = Record<string, string | number>;
type Call = {key: string; values: Values | undefined};

function fakeT() {
    const calls: Call[] = [];
    const t = (key: string, options?: {values?: Values}): string => {
        calls.push({key, values: options?.values});
        const rendered = Object.entries(options?.values ?? {}).map(([name, value]) => `${name}=${String(value)}`);
        return [key, ...rendered].join(' | ');
    };
    return {t, calls};
}

/** The error a zodios (axios) call throws for an HTTP answer carrying `detail`. */
function apiError(status: number, detail: unknown): Error & {response: {status: number; data: {detail: unknown}}} {
    return Object.assign(new Error(`Request failed with status code ${status}`), {response: {status, data: {detail}}});
}

/** A structured refusal, as the endpoint answers it since E1a. */
function refusal(status: number, code: string, params: Record<string, unknown>, message = `${code}: the server's own sentence`) {
    return apiError(status, {error_code: code, message, params});
}

const typeLabel = (type: string) => `T<${type}>`;
const dateLabel = (iso: string) => `D<${iso}>`;

/** The one translation a message is built from. */
function onlyCall(calls: Call[]): Call {
    expect(calls, 'one message, one translation').toHaveLength(1);
    return calls[0];
}

/** What every user-facing sentence must never carry. */
function expectReadable(message: string, code?: string) {
    expect(message).not.toContain('[object Object]');
    expect(message).not.toContain("the server's own sentence");
    if (code) expect(message).not.toContain(code);
}

const STORED: ExistingEvent = {id: 41, date: '2026-03-16', type: 'DIVIDEND', value: {code: 'USD', amount: '0.123456'}, notes: 'Q1 payout', is_auto: false, linked_transactions: 2};
const FROM_PROVIDER: ExistingEvent = {id: 42, date: '2026-03-16', type: 'DIVIDEND', value: {code: 'USD', amount: '1.500000'}, notes: null, is_auto: true, linked_transactions: 0};

describe('eventRefusal', () => {
    it('reads the code, the message and the params of a structured refusal, with its status', () => {
        const params = {asset_id: 7, item_index: 0, date: '2026-03-15', type: 'INTEREST'};
        expect(eventRefusal(refusal(400, 'EVENT_KEY_CONFLICT', params, 'conflict on 2026-03-15'))).toEqual({status: 400, code: 'EVENT_KEY_CONFLICT', message: 'conflict on 2026-03-15', params});
    });

    it.each([
        ['a string detail', apiError(500, 'Internal Server Error')],
        ['a 422 validation list', apiError(422, [{type: 'value_error', loc: ['body', 0, 'events', 0, 'type'], msg: 'unknown type', input: 'bonus'}])],
        ['an object detail without a code', apiError(400, {reason: 'no code here'})],
        ['an answer without a detail', apiError(502, undefined)],
        ['an error with no response', new Error('Network Error')],
        ['nothing at all', undefined],
    ])('is null for %s', (_label, err) => {
        expect(eventRefusal(err)).toBeNull();
    });

    it('takes params that are not an object as empty', () => {
        expect(eventRefusal(apiError(400, {error_code: 'EVENT_NOT_EDITABLE', message: 'x', params: 'oops'}))?.params).toEqual({});
    });
});

describe('existingEvents', () => {
    it('hands back the events already on the date and type of a create (EVENT_EXISTS)', () => {
        const err = refusal(409, 'EVENT_EXISTS', {asset_id: 7, item_index: 0, existing: [STORED, FROM_PROVIDER]});
        expect(existingEvents(err)).toEqual([STORED, FROM_PROVIDER]);
    });

    it.each([
        ['EVENT_KEY_CONFLICT', refusal(400, 'EVENT_KEY_CONFLICT', {asset_id: 7, item_index: 0, date: '2026-03-16', type: 'DIVIDEND'})],
        ['EVENT_NOT_EDITABLE', refusal(400, 'EVENT_NOT_EDITABLE', {asset_id: 7, item_index: 0, ids: [41]})],
        ['EVENT_CURRENCY_MISMATCH', refusal(400, 'EVENT_CURRENCY_MISMATCH', {asset_id: 7, item_index: 0, expected: 'USD', events: []})],
        ['EVENT_ASSET_NOT_FOUND', refusal(400, 'EVENT_ASSET_NOT_FOUND', {asset_id: 7, item_index: 0})],
        ['EVENT_EXISTS with no event listed', refusal(409, 'EVENT_EXISTS', {asset_id: 7, item_index: 0, existing: []})],
        // A 409 listing events too: the events it cannot delete, not the ones a create would duplicate.
        ['EVENT_IN_USE', refusal(409, 'EVENT_IN_USE', {asset_id: 7, item_index: 0, events: [{id: 41, date: '2026-03-16', type: 'DIVIDEND', linked_transactions: 2}]})],
        ['EVENT_NOT_DELETABLE', refusal(400, 'EVENT_NOT_DELETABLE', {asset_id: 7, item_index: 0, ids: [41]})],
        // C-97b guard: a 400 listing events too, the ones whose value has too many digits.
        ['EVENT_TOO_MANY_DIGITS', refusal(400, 'EVENT_TOO_MANY_DIGITS', {asset_id: 7, item_index: 0, max_decimal_places: 6, max_significant_digits: 15, events: [{event_index: 0, date: '2026-01-15', type: 'DIVIDEND'}]})],
        ['a string detail', apiError(409, 'Conflict')],
        ['an error with no response', new Error('Network Error')],
    ])('is null for %s', (_label, err) => {
        expect(existingEvents(err)).toBeNull();
    });
});

describe('eventSaveErrorMessage — the refusals of decision 22', () => {
    it('EVENT_KEY_CONFLICT names the date and the type the edit would take', () => {
        const {t, calls} = fakeT();
        const message = eventSaveErrorMessage(refusal(400, 'EVENT_KEY_CONFLICT', {asset_id: 7, item_index: 0, date: '2026-03-15', type: 'INTEREST'}), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.keyConflict', values: {date: 'D<2026-03-15>', type: 'T<INTEREST>'}});
        expectReadable(message, 'EVENT_KEY_CONFLICT');
    });

    it('EVENT_CURRENCY_MISMATCH names the first mismatched event, the currencies, and how many more', () => {
        const {t, calls} = fakeT();
        const events = [
            {event_index: 0, date: '2026-01-10', type: 'DIVIDEND', currency: 'EUR'},
            {event_index: 2, date: '2026-02-10', type: 'SPLIT', currency: 'GBP'},
            {event_index: 4, date: '2026-03-10', type: 'INTEREST', currency: 'CHF'},
        ];
        const message = eventSaveErrorMessage(refusal(400, 'EVENT_CURRENCY_MISMATCH', {asset_id: 7, item_index: 1, expected: 'USD', events}), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.currencyMismatch', values: {date: 'D<2026-01-10>', type: 'T<DIVIDEND>', currency: 'EUR', expected: 'USD', more: 2}});
        expectReadable(message, 'EVENT_CURRENCY_MISMATCH');
    });

    it('EVENT_CURRENCY_MISMATCH with a single event has no more', () => {
        const {t, calls} = fakeT();
        eventSaveErrorMessage(refusal(400, 'EVENT_CURRENCY_MISMATCH', {asset_id: 7, item_index: 0, expected: 'USD', events: [{event_index: 1, date: '2026-01-10', type: 'DIVIDEND', currency: 'EUR'}]}), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls).values).toMatchObject({currency: 'EUR', expected: 'USD', more: 0});
    });

    it('EVENT_NOT_EDITABLE has its own sentence', () => {
        const {t, calls} = fakeT();
        const message = eventSaveErrorMessage(refusal(400, 'EVENT_NOT_EDITABLE', {asset_id: 7, item_index: 0, ids: [41]}), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls).key).toBe('events.saveError.notEditable');
        expectReadable(message, 'EVENT_NOT_EDITABLE');
    });

    it('EVENT_ASSET_NOT_FOUND has its own sentence', () => {
        const {t, calls} = fakeT();
        const message = eventSaveErrorMessage(refusal(400, 'EVENT_ASSET_NOT_FOUND', {asset_id: 7, item_index: 0}), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls).key).toBe('events.saveError.assetNotFound');
        expectReadable(message, 'EVENT_ASSET_NOT_FOUND');
    });

    // X-R47: a manual SPLIT whose ratio (its value) is not a number above 0 is refused, 400 EVENT_INVALID_SPLIT_RATIO, with
    // params.events = [{event_index, date, type: 'SPLIT', ratio}, …], the ratio a string as sent.
    it('EVENT_INVALID_SPLIT_RATIO names the first split whose ratio is not above 0, its ratio as sent, and how many more', () => {
        const {t, calls} = fakeT();
        const events = [
            {event_index: 1, date: '2026-02-10', type: 'SPLIT', ratio: '0'},
            {event_index: 3, date: '2026-04-10', type: 'SPLIT', ratio: '-2'},
        ];
        const message = eventSaveErrorMessage(refusal(400, 'EVENT_INVALID_SPLIT_RATIO', {asset_id: 7, item_index: 0, events}), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.invalidSplitRatio', values: {date: 'D<2026-02-10>', type: 'T<SPLIT>', ratio: '0', more: 1}});
        expectReadable(message, 'EVENT_INVALID_SPLIT_RATIO');
    });

    it('without labels, the date and the type are passed as the server wrote them', () => {
        const {t, calls} = fakeT();
        eventSaveErrorMessage(refusal(400, 'EVENT_KEY_CONFLICT', {asset_id: 7, item_index: 0, date: '2026-03-15', type: 'INTEREST'}), t);

        expect(onlyCall(calls).values).toEqual({date: '2026-03-15', type: 'INTEREST'});
    });

    it('a code it does not know falls back to the generic sentence, with a readable message', () => {
        const {t, calls} = fakeT();
        const message = eventSaveErrorMessage(refusal(400, 'EVENT_SOMETHING_NEW', {asset_id: 7, item_index: 0}, 'something new happened'), t);

        const call = onlyCall(calls);
        expect(call.key).toBe('events.saveError.generic');
        expect(typeof call.values?.message).toBe('string');
        expect(message).not.toContain('[object Object]');
    });
});

/**
 * X-R47, W's review (LOW) — the ratio of a refused split, written the way the interface writes numbers.
 *
 * EVENT_INVALID_SPLIT_RATIO names each refused split with its ratio as the request sent it: a decimal
 * string with at most six decimals, the scale of the event's value (`"-0.5"`, `"0"`, `"-0.000001"`).
 * Handed to `t` as it is, an Italian, French or Spanish user reads «-0.5» in a sentence where every other
 * figure of the app reads «-0,5». The cure writes it with `formatExactDecimal`: the digits of
 * `formatDecimalForDisplay` (nothing rounded, trailing zeros dropped), written by Intl from the string and
 * never from a float (`toLocaleString` on a float prints `-0.000001` as «-0»), in `uiLocale()`. The date
 * and the type still come from the caller's labels, and `more` is unchanged.
 *
 * The browser. Node's `navigator.language` follows the host's ICU locale (uiLocale.test.ts): an `it_CH`
 * host would write the Italian ratio «-0.5», an `en_DE` one the English «-0,5». So this block runs with no
 * navigator, as on the server, where each language takes its own default (en-GB, it, fr, es), and every
 * test checks that locale before it reads the sentence.
 *
 * Red before the cure: Italian, French and Spanish, which read the ratio as sent. Guards, green before and
 * after: English, which already read «-0.5», and a ratio of 0, with nothing to localize in any language.
 * The expectations are typed, as this runtime's Intl writes them: a decimal comma and the ASCII minus
 * (U+002D). A runtime without the locale's data would fall back to English and turn them red, never green.
 */
describe('eventSaveErrorMessage — the ratio of a refused split, in the interface language (X-R47, W review)', () => {
    /** The interface locale of each language when no browser lends it a region: the language's own default. */
    const LOCALE_OF = {en: 'en-GB', it: 'it', fr: 'fr', es: 'es'} as const;
    type UiLanguage = keyof typeof LOCALE_OF;

    /** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
    async function uiLanguage(lang: UiLanguage): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
    }

    /** Switch the interface to `lang`, then check the locale its figures are written in. */
    async function interfaceIn(lang: UiLanguage): Promise<void> {
        await uiLanguage(lang);
        expect(uiLocale(), `control: a ${lang} interface with no browser to lend a region writes ${LOCALE_OF[lang]}`).toBe(LOCALE_OF[lang]);
    }

    /** A refused save naming each split by its ratio, as the request sent it; the sentence names the first, of 2026-02-10. */
    function invalidSplitRatio(...ratios: string[]) {
        const events = ratios.map((ratio, i) => ({event_index: 2 * i + 1, date: `2026-02-${10 + i}`, type: 'SPLIT', ratio}));
        return refusal(400, 'EVENT_INVALID_SPLIT_RATIO', {asset_id: 7, item_index: 0, events});
    }

    beforeEach(() => {
        vi.stubGlobal('navigator', undefined);
    });

    afterEach(async () => {
        // The language is module-level state and the navigator a global: both go back for the rest of the file.
        await uiLanguage('en');
        vi.unstubAllGlobals();
    });

    it.each(['it', 'fr', 'es'] as const)('EVENT_INVALID_SPLIT_RATIO writes the ratio the way the interface language writes numbers (%s): -0,5', async (lang) => {
        await interfaceIn(lang);
        const {t, calls} = fakeT();
        const message = eventSaveErrorMessage(invalidSplitRatio('-0.5', '-0.000001'), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.invalidSplitRatio', values: {date: 'D<2026-02-10>', type: 'T<SPLIT>', ratio: '-0,5', more: 1}});
        expectReadable(message, 'EVENT_INVALID_SPLIT_RATIO');
    });

    it.each(['it', 'fr', 'es'] as const)('EVENT_INVALID_SPLIT_RATIO keeps the six decimals of the ratio, through no float and no rounding (%s): -0,000001', async (lang) => {
        await interfaceIn(lang);
        const {t, calls} = fakeT();
        eventSaveErrorMessage(invalidSplitRatio('-0.000001'), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.invalidSplitRatio', values: {date: 'D<2026-02-10>', type: 'T<SPLIT>', ratio: '-0,000001', more: 0}});
    });

    it('with the interface in English the ratio reads as it always has: -0.5, and -0.000001 with its six decimals', async () => {
        await interfaceIn('en');
        const half = fakeT();
        eventSaveErrorMessage(invalidSplitRatio('-0.5', '-0.000001'), half.t, [], typeLabel, dateLabel);
        const tiny = fakeT();
        eventSaveErrorMessage(invalidSplitRatio('-0.000001'), tiny.t, [], typeLabel, dateLabel);

        expect(onlyCall(half.calls)).toEqual({key: 'events.saveError.invalidSplitRatio', values: {date: 'D<2026-02-10>', type: 'T<SPLIT>', ratio: '-0.5', more: 1}});
        expect(onlyCall(tiny.calls)).toEqual({key: 'events.saveError.invalidSplitRatio', values: {date: 'D<2026-02-10>', type: 'T<SPLIT>', ratio: '-0.000001', more: 0}});
    });

    it.each(['en', 'it', 'fr', 'es'] as const)('a ratio of 0 reads 0 in every language, with nothing to localize (%s)', async (lang) => {
        await interfaceIn(lang);
        const {t, calls} = fakeT();
        eventSaveErrorMessage(invalidSplitRatio('0', '-2'), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.invalidSplitRatio', values: {date: 'D<2026-02-10>', type: 'T<SPLIT>', ratio: '0', more: 1}});
    });
});

describe('eventSaveErrorMessage — the refusals of the deletions (E1b)', () => {
    it('EVENT_IN_USE names the first event in use, how many transactions it carries, and how many more', () => {
        const {t, calls} = fakeT();
        const events = [
            {id: 41, date: '2026-03-16', type: 'DIVIDEND', linked_transactions: 2},
            {id: 43, date: '2026-04-01', type: 'INTEREST', linked_transactions: 1},
            {id: 44, date: '2026-05-04', type: 'DIVIDEND', linked_transactions: 5},
        ];
        const message = eventSaveErrorMessage(refusal(409, 'EVENT_IN_USE', {asset_id: 7, item_index: 0, events}), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.inUse', values: {date: 'D<2026-03-16>', type: 'T<DIVIDEND>', n: 2, more: 2}});
        expectReadable(message, 'EVENT_IN_USE');
    });

    it('EVENT_IN_USE with a single event has no more', () => {
        const {t, calls} = fakeT();
        eventSaveErrorMessage(refusal(409, 'EVENT_IN_USE', {asset_id: 7, item_index: 1, events: [{id: 43, date: '2026-04-01', type: 'INTEREST', linked_transactions: 1}]}), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.inUse', values: {date: 'D<2026-04-01>', type: 'T<INTEREST>', n: 1, more: 0}});
    });

    it('EVENT_NOT_DELETABLE has its own sentence', () => {
        const {t, calls} = fakeT();
        const message = eventSaveErrorMessage(refusal(400, 'EVENT_NOT_DELETABLE', {asset_id: 7, item_index: 0, ids: [41, 99]}), t, [], typeLabel, dateLabel);

        expect(onlyCall(calls).key).toBe('events.saveError.notDeletable');
        expectReadable(message, 'EVENT_NOT_DELETABLE');
    });
});

/**
 * C-97b — a value with more digits than an event keeps. C-97a refuses an event value over what
 * `AssetEvent.value` keeps — 6 decimal places, 15 significant digits — with 400
 * EVENT_TOO_MANY_DIGITS and rounds nothing (`event_store._reject_too_many_digits`):
 * `params = {asset_id, item_index, max_decimal_places, max_significant_digits, events: [{event_index,
 * date, type}, …]}`.
 *
 * The sentence has a key of its own, `events.saveError.tooManyDigits`, and names — like the file's
 * other per-event refusals — the first event at fault by its date and type label and how many more
 * (`more`), plus the decimal places a value keeps (`max`, the name
 * `transactions.errors.decimalPlacesExceeded` already gives the same maximum), read from the params.
 * The values are matched, not equated: the sentence may name `max_significant_digits` too.
 *
 * Red today: the code has no branch, so the user reads `events.saveError.generic` carrying the
 * server's English sentence.
 */
describe('eventSaveErrorMessage — a value with more digits than an event keeps (C-97b)', () => {
    function tooManyDigits(events: Array<Record<string, unknown>>, maxDecimalPlaces = 6) {
        return refusal(400, 'EVENT_TOO_MANY_DIGITS', {asset_id: 7, item_index: 0, max_decimal_places: maxDecimalPlaces, max_significant_digits: 15, events});
    }

    it('EVENT_TOO_MANY_DIGITS has its own sentence: the first event at fault, how many more, and the decimal places a value keeps', () => {
        const {t, calls} = fakeT();
        const events = [
            {event_index: 0, date: '2026-01-15', type: 'DIVIDEND'},
            {event_index: 2, date: '2026-02-16', type: 'INTEREST'},
            {event_index: 3, date: '2026-03-17', type: 'DIVIDEND'},
        ];
        const message = eventSaveErrorMessage(tooManyDigits(events), t, [], typeLabel, dateLabel);

        const call = onlyCall(calls);
        expect(call.key, 'a sentence of its own, not the generic one carrying the server text').toBe('events.saveError.tooManyDigits');
        expect(call.values, 'the first event at fault, by its labels, and how many more').toMatchObject({date: 'D<2026-01-15>', type: 'T<DIVIDEND>', more: 2});
        expect(String(call.values?.max), 'the sentence names the decimal places an event value keeps').toBe('6');
        expectReadable(message, 'EVENT_TOO_MANY_DIGITS');
    });

    it('EVENT_TOO_MANY_DIGITS with a single event has no more', () => {
        const {t, calls} = fakeT();
        eventSaveErrorMessage(tooManyDigits([{event_index: 1, date: '2026-01-15', type: 'INTEREST'}]), t, [], typeLabel, dateLabel);

        const call = onlyCall(calls);
        expect(call.key).toBe('events.saveError.tooManyDigits');
        expect(call.values).toMatchObject({date: 'D<2026-01-15>', type: 'T<INTEREST>', more: 0});
    });

    it('EVENT_TOO_MANY_DIGITS names the maximum the server sends, not a constant', () => {
        const {t, calls} = fakeT();
        eventSaveErrorMessage(tooManyDigits([{event_index: 0, date: '2026-01-15', type: 'DIVIDEND'}], 4), t, [], typeLabel, dateLabel);

        const call = onlyCall(calls);
        expect(call.key).toBe('events.saveError.tooManyDigits');
        expect(String(call.values?.max), 'max is read from params.max_decimal_places').toBe('4');
    });
});

/** C-97b guard: green today. The new branch changes no other refusal's key or values. */
describe('eventSaveErrorMessage — the refusals that had a sentence keep it (C-97b guard)', () => {
    it.each([
        ['EVENT_KEY_CONFLICT', refusal(400, 'EVENT_KEY_CONFLICT', {asset_id: 7, item_index: 0, date: '2026-03-15', type: 'INTEREST'}), {key: 'events.saveError.keyConflict', values: {date: 'D<2026-03-15>', type: 'T<INTEREST>'}}],
        [
            'EVENT_CURRENCY_MISMATCH',
            refusal(400, 'EVENT_CURRENCY_MISMATCH', {asset_id: 7, item_index: 0, expected: 'USD', events: [{event_index: 0, date: '2026-01-10', type: 'DIVIDEND', currency: 'EUR'}]}),
            {key: 'events.saveError.currencyMismatch', values: {date: 'D<2026-01-10>', type: 'T<DIVIDEND>', currency: 'EUR', expected: 'USD', more: 0}},
        ],
        ['EVENT_NOT_EDITABLE', refusal(400, 'EVENT_NOT_EDITABLE', {asset_id: 7, item_index: 0, ids: [41]}), {key: 'events.saveError.notEditable', values: undefined}],
        ['EVENT_NOT_DELETABLE', refusal(400, 'EVENT_NOT_DELETABLE', {asset_id: 7, item_index: 0, ids: [41]}), {key: 'events.saveError.notDeletable', values: undefined}],
        ['EVENT_ASSET_NOT_FOUND', refusal(400, 'EVENT_ASSET_NOT_FOUND', {asset_id: 7, item_index: 0}), {key: 'events.saveError.assetNotFound', values: undefined}],
        ['EVENT_IN_USE', refusal(409, 'EVENT_IN_USE', {asset_id: 7, item_index: 0, events: [{id: 41, date: '2026-03-16', type: 'DIVIDEND', linked_transactions: 2}]}), {key: 'events.saveError.inUse', values: {date: 'D<2026-03-16>', type: 'T<DIVIDEND>', n: 2, more: 0}}],
        ['a code it does not know', refusal(400, 'EVENT_SOMETHING_NEW', {asset_id: 7, item_index: 0}, 'something new happened'), {key: 'events.saveError.generic', values: {message: 'something new happened'}}],
    ])('%s: the same key, the same values', (_label, err, expected) => {
        const {t, calls} = fakeT();
        eventSaveErrorMessage(err, t, [], typeLabel, dateLabel);

        expect(onlyCall(calls)).toEqual(expected);
    });
});

describe('eventSaveErrorMessage — a 422 on the type (decision 23)', () => {
    const sent = [
        {date: '2026-01-05', type: 'DIVIDEND'},
        {date: '2026-02-06', type: 'bonus'},
    ];

    it('names the value sent and the date of the row the error points at (sent[index])', () => {
        const {t, calls} = fakeT();
        const err = apiError(422, [{type: 'value_error', loc: ['body', 0, 'events', 1, 'type'], msg: 'Value error, unknown event type', input: 'bonus'}]);
        const message = eventSaveErrorMessage(err, t, sent, typeLabel, dateLabel);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.unknownType', values: {value: 'bonus', date: 'D<2026-02-06>'}});
        expectReadable(message);
    });

    it('a 422 on another field is the generic sentence, never the raw list', () => {
        const {t, calls} = fakeT();
        const err = apiError(422, [{type: 'decimal_parsing', loc: ['body', 0, 'events', 0, 'value', 'amount'], msg: 'Input should be a valid decimal', input: 'abc'}]);
        const message = eventSaveErrorMessage(err, t, sent, typeLabel, dateLabel);

        const call = onlyCall(calls);
        expect(call.key).toBe('events.saveError.generic');
        expect(typeof call.values?.message).toBe('string');
        expect(message).not.toContain('[object Object]');
    });
});

describe('eventSaveErrorMessage — everything that is not a structured refusal', () => {
    it('a string detail is the generic sentence carrying it', () => {
        const {t, calls} = fakeT();
        eventSaveErrorMessage(apiError(500, 'Internal Server Error'), t);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.generic', values: {message: 'Internal Server Error'}});
    });

    it('a network error is the generic sentence carrying its message', () => {
        const {t, calls} = fakeT();
        eventSaveErrorMessage(new Error('Network Error'), t);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.generic', values: {message: 'Network Error'}});
    });

    it('an object detail without a code is the generic sentence with the error message, not the object', () => {
        const {t, calls} = fakeT();
        const message = eventSaveErrorMessage(apiError(400, {reason: 'no code here'}), t);

        expect(onlyCall(calls)).toEqual({key: 'events.saveError.generic', values: {message: 'Request failed with status code 400'}});
        expect(message).not.toContain('[object Object]');
    });

    it('nothing at all is still a sentence', () => {
        const {t, calls} = fakeT();
        const message = eventSaveErrorMessage(undefined, t);

        const call = onlyCall(calls);
        expect(call.key).toBe('events.saveError.generic');
        expect(String(call.values?.message ?? '')).not.toBe('');
        expect(message).not.toContain('[object Object]');
    });
});

describe('eventSaveErrorMessage — never [object Object]', () => {
    const shapes: Array<[string, unknown]> = [
        ['EVENT_KEY_CONFLICT', refusal(400, 'EVENT_KEY_CONFLICT', {asset_id: 7, item_index: 0, date: '2026-03-15', type: 'INTEREST'})],
        ['EVENT_CURRENCY_MISMATCH', refusal(400, 'EVENT_CURRENCY_MISMATCH', {asset_id: 7, item_index: 0, expected: 'USD', events: [{event_index: 0, date: '2026-01-10', type: 'DIVIDEND', currency: 'EUR'}]})],
        ['EVENT_CURRENCY_MISMATCH with no events', refusal(400, 'EVENT_CURRENCY_MISMATCH', {asset_id: 7, item_index: 0, expected: 'USD'})],
        ['EVENT_NOT_EDITABLE', refusal(400, 'EVENT_NOT_EDITABLE', {asset_id: 7, item_index: 0, ids: [41]})],
        ['EVENT_ASSET_NOT_FOUND', refusal(400, 'EVENT_ASSET_NOT_FOUND', {asset_id: 7, item_index: 0})],
        ['EVENT_EXISTS', refusal(409, 'EVENT_EXISTS', {asset_id: 7, item_index: 0, existing: [STORED]})],
        ['EVENT_IN_USE', refusal(409, 'EVENT_IN_USE', {asset_id: 7, item_index: 0, events: [{id: 41, date: '2026-03-16', type: 'DIVIDEND', linked_transactions: 2}]})],
        ['EVENT_IN_USE with no events', refusal(409, 'EVENT_IN_USE', {asset_id: 7, item_index: 0})],
        ['EVENT_NOT_DELETABLE', refusal(400, 'EVENT_NOT_DELETABLE', {asset_id: 7, item_index: 0, ids: [41]})],
        // C-97b guard: green today (the generic sentence carries a string), and after the cure too.
        ['EVENT_TOO_MANY_DIGITS', refusal(400, 'EVENT_TOO_MANY_DIGITS', {asset_id: 7, item_index: 0, max_decimal_places: 6, max_significant_digits: 15, events: [{event_index: 0, date: '2026-01-15', type: 'DIVIDEND'}]})],
        ['EVENT_TOO_MANY_DIGITS with no events', refusal(400, 'EVENT_TOO_MANY_DIGITS', {asset_id: 7, item_index: 0, max_decimal_places: 6, max_significant_digits: 15})],
        ['a refusal whose message is not a string', apiError(400, {error_code: 'EVENT_SOMETHING_NEW', message: {nested: true}, params: {}})],
        ['a 422 on the type', apiError(422, [{loc: ['body', 0, 'events', 0, 'type'], msg: 'unknown', input: 'bonus'}])],
        ['a 422 on the type of a row that was not sent', apiError(422, [{loc: ['body', 0, 'events', 5, 'type'], msg: 'unknown', input: 'bonus'}])],
        ['a string detail', apiError(500, 'Internal Server Error')],
        ['an object detail without a code', apiError(400, {reason: 'no code here'})],
        ['a network error', new Error('Network Error')],
        ['null', null],
    ];

    it.each(shapes)('%s: every value handed to the translation is a string or a number, and the sentence carries no object', (_label, err) => {
        const {t, calls} = fakeT();
        const message = eventSaveErrorMessage(err, t, [{date: '2026-01-05', type: 'DIVIDEND'}], typeLabel, dateLabel);

        const call = onlyCall(calls);
        for (const value of Object.values(call.values ?? {})) expect(['string', 'number']).toContain(typeof value);
        expect(message).not.toContain('[object Object]');
    });
});

describe('existingAmountText — a stored amount as the panel and «Edit this» show it', () => {
    // The server writes amounts with six decimals (`1.500000`). As written: no rounding, no
    // grouping, no locale; trailing zeros go, down to two decimals.
    it.each([
        ['1.500000', '1.50'],
        ['0.123456', '0.123456'],
        ['1', '1.00'],
        ['2.000000', '2.00'],
        ['12.340000', '12.34'],
        ['-0.500000', '-0.50'],
        ['1234.500000', '1234.50'],
    ])('%s reads %s', (stored, shown) => {
        expect(existingAmountText(stored)).toBe(shown);
    });
});
