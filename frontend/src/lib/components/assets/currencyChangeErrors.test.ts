// @vitest-environment node
/**
 * currencyChangeErrors — unit test (Vitest, node). Workstream X, lots X-R48, X-R49 and X-R62 (the last written by H, for X).
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
 * X-R49. The same refusal has a second door. The provider assignment (`POST /assets/provider`) regenerates the plan of
 * a parametric provider whose params change, or that the asset leaves, and deleting the plan deletes its splits: it
 * refuses, writing nothing, with 409 `detail = {error_code: 'PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST', message,
 * params: {asset_id, item_index, splits: [{event_id, date, transaction_ids, hidden_transactions_count}, …]}}`, the
 * splits listed as the wipe lists them. The asset modal words it through this module, with a key of its own:
 * `t('assets.modal.planSplitAdjustmentsWithoutCost', {values: {date, n, hidden, more}})`, the values read from
 * `params.splits` exactly as for the wipe, which keeps its key. A code is looked up among the module's own codes only:
 * `constructor`, `toString`, `__proto__` and the other names every object inherits are not codes, and neither is a
 * list holding one (JSON can carry a list) — `null`, and the catalogue is not asked. The new key is read in the four
 * catalogues as the first one is (in words of its own, and not the currency change's sentence either; the four names
 * and the three plurals; through svelte-i18n with nothing left raw), and its French counts carry the CLDR `many`
 * branch, as the first one's do.
 *
 * Expected (X-R49). Red before the cure: the module answers `null` to the plan's code and asks nothing, so every case
 * of its describe is red, the side-by-side case included; the catalogue cases of the new key stay red until the key is
 * in the four sources (`src/lib/i18n/assets/<lang>.json`). Green before the cure and after it: the inherited names, the
 * list and the near miss `PROVIDER_SOMETHING_NEW` — guards against a lookup that reads what an object inherits.
 *
 * X-R62. A third door, on the events this time. Removing the provider (`DELETE /assets/provider`, «No provider» in the
 * asset modal) deletes the events it generated, so it refuses, writing nothing, while transactions are linked to one of
 * them: 409 `detail = {error_code: 'PROVIDER_REMOVAL_LINKED_TRANSACTIONS', message, params: {asset_id, item_index,
 * events: [{event_id, date, type, transaction_ids, hidden_transactions_count}, …]}}`, the events by date — or 409
 * `PROVIDER_REMOVAL_CONFLICT`, `params = {}`, when a link appeared between the check and the delete. The module words
 * each with a key of its own. The first: `t('assets.modal.providerRemovalLinkedTransactions', {values: {type, date, n,
 * hidden, more}})`, its list read from `params.events` (the wipe and the plan keep reading `params.splits`), the first
 * event counted as a split is, and named by its type: `type` is what `t('assetDetail.eventType.<TYPE>')` gives back, the
 * key asked alone — the fake catalogue answers it with a name of its own, so the sentence is read with what came back —
 * and, for a type that is not a string (missing, null, a number, an object, a list), the empty string, no name asked.
 * The second: `t('assets.modal.providerRemovalConflict')` with no values, whatever the params carry: it names nothing.
 * Both keys are read in the four catalogues as the others are: in words of their own; the first names exactly `date`,
 * `hidden`, `more`, `n` and `type`, counts the three with ICU plurals, and carries the French `many` branch; the second
 * names nothing; through svelte-i18n nothing is left raw, and the type is written by its name in the interface language.
 *
 * X5-1 (lot X5-1, developer decision). The removal no longer refuses for linked transactions — it disconnects them, and the
 * asset modal tells how many in a dialog first — so `PROVIDER_REMOVAL_LINKED_TRANSACTIONS`, its `params.events`/`type` branch
 * and its catalogue key `assets.modal.providerRemovalLinkedTransactions` are REMOVED: the code is now unknown (`null`, the
 * catalogue not asked). The removal's remaining 409s are `PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST` (the assignment's
 * code, key and `params.splits`, for both operations) and `PROVIDER_REMOVAL_CONFLICT` (unchanged). The X-R62 text below
 * is history for those two.
 *
 * Expected (X-R62). Red before the cure: the module answers `null` to both codes and asks nothing, so every case of
 * their two describes is red, the side-by-side case included; the catalogue cases stay red until both keys are in the
 * four sources (`src/lib/i18n/assets/<lang>.json`). Green before the cure and after it: the near misses — another code
 * of the removal, a code in a list, a detail without a code or that is not an object.
 *
 * N68 (lot X5-3, developer decision 19/10/2026). Changing a currency is no longer blocked: `PATCH /assets/patch` deletes the
 * prices and the non-SPLIT events itself and KEEPS the splits and their transactions, so the market-data wipe — the only
 * thing that could refuse with `MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST` — is no longer called by the interface (the
 * confirm modal sends one PATCH). The X-R48 branch therefore DISAPPEARS: that code is now an unknown code (`null`, the
 * catalogue not asked), and its sentence `assetDetail.currencyChange.splitAdjustmentsWithoutCost` leaves the four catalogues.
 * The X-R48 cases below are rewritten as those absences; the X-R49 / X5-1 / X-R62 branches (`PROVIDER_*`) stay untouched, and
 * so do their catalogue cases, which no longer lean on the X-R48 sentence for their controls.
 *
 * Expected (N68). Red before the cure: the module still words `MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST` (so the
 * «unknown code» cases fail: they get a sentence and a catalogue call) and the catalogues still hold the key. Green before and
 * after: every `PROVIDER_*` case.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit` (action
 * `core-unit`), next to `currencyImpact.test.ts` (the place `currencyBlocker.test.ts` had).
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

/** N68: the wipe's refusal and its sentence's key — GONE (the interface no longer wipes); kept here to prove they are unknown now. */
const CODE = 'MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST';
const KEY = 'assetDetail.currencyChange.splitAdjustmentsWithoutCost';
/** X-R49: the provider assignment's refusal, and the key it is worded by. */
const PLAN_CODE = 'PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST';
const PLAN_KEY = 'assets.modal.planSplitAdjustmentsWithoutCost';
/** X-R62, trimmed by X5-1: the provider removal's refusal that stays, and the key it is worded by. */
const CONFLICT_CODE = 'PROVIDER_REMOVAL_CONFLICT';
const CONFLICT_KEY = 'assets.modal.providerRemovalConflict';
/** X5-1: the code the removal no longer has (it disconnects the linked transactions instead), and the key that worded it. */
const GONE_CODE = 'PROVIDER_REMOVAL_LINKED_TRANSACTIONS';
const GONE_KEY = 'assets.modal.providerRemovalLinkedTransactions';

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

/** The assignment's own sentence (X-R49), English and totals only: the user must never read it either. */
const PLAN_SERVER_SENTENCE = "Provider not assigned: the server's own sentence";

/** The params of the assignment's refusal: the asset and the item of the request, beside the splits as given. */
function planParams(splits: unknown) {
    return {asset_id: 7, item_index: 0, splits};
}

/** The assignment's refusal (X-R49), 409, with its params as given. */
function planRefused(params: unknown) {
    return apiError(409, {error_code: PLAN_CODE, message: PLAN_SERVER_SENTENCE, params});
}

/** One split as the refusal lists it: its date, the adjustments the user can see, and how many others. */
function split(date: string, transactionIds: unknown[], hidden: number, eventId = 12) {
    return {event_id: eventId, date, transaction_ids: transactionIds, hidden_transactions_count: hidden};
}

/** The removal's own sentence (X-R62), English and totals only: the user must never read it either. */
const REMOVAL_SERVER_SENTENCE = "Provider not removed: the server's own sentence";

/** The removal's conflict (X-R62) — a link appeared between the check and the delete — 409, with its params as given: the server sends them empty. */
function removalConflict(params: unknown) {
    return apiError(409, {error_code: CONFLICT_CODE, message: REMOVAL_SERVER_SENTENCE, params});
}

/** The refusal the removal no longer sends: 409 with its old code and the events it listed. */
function goneRefusal(params: unknown) {
    return apiError(409, {error_code: GONE_CODE, message: REMOVAL_SERVER_SENTENCE, params});
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
    expect(message).not.toContain(PLAN_CODE);
    expect(message).not.toContain(GONE_CODE);
    expect(message).not.toContain(CONFLICT_CODE);
}

describe('wipeRefusalMessage — the wipe’s refusal no longer exists: an unknown code (N68)', () => {
    it.each<[string, unknown]>([
        ['one split, one adjustment in sight and none hidden', wipeRefused({splits: [split('2026-02-10', [5], 0)]})],
        ['fail-closed, none in sight and two hidden', wipeRefused({splits: [split('2026-02-10', [], 2)]})],
        ['two splits', wipeRefused({splits: [split('2026-02-10', [5], 1, 12), split('2026-05-04', [7, 8, 9], 4, 15)]})],
        ['params missing', wipeRefused(undefined)],
        ['params null', wipeRefused(null)],
        ['params without splits', wipeRefused({})],
        ['splits not a list', wipeRefused({splits: '2026-02-10'})],
        ['the code with the plan’s params (asset, item, splits)', wipeRefused(planParams([split('2026-02-10', [5], 1)]))],
    ])('MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST, %s: null, and the catalogue is not asked — nothing words it any more', (_label, err) => {
        const {t, calls} = fakeT();

        expect(wipeRefusalMessage(err, t, dateLabel)).toBeNull();
        expect(calls, 'the caller keeps its generic sentence: nothing is asked of the catalogue, under the old key or any other').toEqual([]);
    });

    it('the old code is looked up like any unknown one: a list holding it is no code either', () => {
        const {t, calls} = fakeT();

        expect(wipeRefusalMessage(apiError(409, {error_code: [CODE], message: SERVER_SENTENCE, params: {splits: [split('2026-02-10', [5], 1)]}}), t)).toBeNull();
        expect(calls).toEqual([]);
    });

    it('the plan’s code keeps its own sentence beside it: removing the wipe’s branch did not take the provider’s', () => {
        const {t, calls} = fakeT();
        const message = wipeRefusalMessage(planRefused(planParams([split('2026-02-10', [5, 6], 1, 12)])), t, dateLabel);

        expect(onlyCall(calls)).toEqual({key: PLAN_KEY, values: {date: 'D<2026-02-10>', n: 3, hidden: 1, more: 0}});
        expectReadable(String(message));
    });
});

describe('wipeRefusalMessage — a split of the plan the provider assignment would delete (X-R49)', () => {
    it("one split, one adjustment in sight and none hidden: the plan's own key, its date as the server wrote it, n 1, hidden 0, more 0", () => {
        const {t, calls, outputs} = fakeT();
        const message = wipeRefusalMessage(planRefused(planParams([split('2026-02-10', [5], 0)])), t);

        expect(onlyCall(calls)).toEqual({key: PLAN_KEY, values: {date: '2026-02-10', n: 1, hidden: 0, more: 0}});
        expect(message, 'the sentence is the translation, as t wrote it').toBe(outputs[0]);
        expectReadable(String(message));
    });

    it('fail-closed, none in sight: no id listed and two hidden — n 2, hidden 2', () => {
        const {t, calls, outputs} = fakeT();
        const message = wipeRefusalMessage(planRefused(planParams([split('2026-02-10', [], 2)])), t);

        expect(onlyCall(calls)).toEqual({key: PLAN_KEY, values: {date: '2026-02-10', n: 2, hidden: 2, more: 0}});
        expect(message).toBe(outputs[0]);
        expectReadable(String(message));
    });

    it('two splits: the first is named — its date, its adjustments — and the second is only counted in more', () => {
        const {t, calls} = fakeT();
        // The second split differs from the first in every value: a sum, or the last split, reads otherwise.
        const splits = [split('2026-02-10', [5], 1, 12), split('2026-05-04', [7, 8, 9], 4, 15)];
        const message = wipeRefusalMessage(planRefused(planParams(splits)), t);

        expect(onlyCall(calls)).toEqual({key: PLAN_KEY, values: {date: '2026-02-10', n: 2, hidden: 1, more: 1}});
        expectReadable(String(message));
    });

    it("the date label is applied to the first split's date", () => {
        const {t, calls} = fakeT();
        const splits = [split('2026-02-10', [5, 6], 0, 12), split('2026-05-04', [7], 0, 15)];
        wipeRefusalMessage(planRefused(planParams(splits)), t, dateLabel);

        expect(onlyCall(calls)).toEqual({key: PLAN_KEY, values: {date: 'D<2026-02-10>', n: 2, hidden: 0, more: 1}});
    });

    it.each<[string, unknown, Values]>([
        ['params missing', undefined, {date: '', n: 0, hidden: 0, more: 0}],
        ['params null', null, {date: '', n: 0, hidden: 0, more: 0}],
        ['params with the asset and the item but no splits', {asset_id: 7, item_index: 0}, {date: '', n: 0, hidden: 0, more: 0}],
        ['splits an empty list (more is never -1)', planParams([]), {date: '', n: 0, hidden: 0, more: 0}],
        ['splits not a list: a string', planParams('2026-02-10'), {date: '', n: 0, hidden: 0, more: 0}],
        ['a split that is not an object', planParams([null]), {date: '', n: 0, hidden: 0, more: 0}],
        ['ids that are not a list and a hidden count of -1', planParams([{event_id: 12, date: '2026-02-10', transaction_ids: '5,6', hidden_transactions_count: -1}]), {date: '2026-02-10', n: 0, hidden: 0, more: 0}],
        ['a date that is not a string', planParams([{event_id: 12, date: {year: 2026, month: 2, day: 10}, transaction_ids: [5], hidden_transactions_count: 0}]), {date: '', n: 1, hidden: 0, more: 0}],
    ])('%s: no throw — each missing piece is 0 or the empty string', (_label, params, values) => {
        const {t, calls} = fakeT();
        const message = wipeRefusalMessage(planRefused(params), t);

        expect(onlyCall(calls)).toEqual({key: PLAN_KEY, values});
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
        // X-R49: a near miss of the assignment, with the plan's params.
        ['another code of the assignment, with the same splits', apiError(409, {error_code: 'PROVIDER_SOMETHING_NEW', message: PLAN_SERVER_SENTENCE, params: planParams(SPLITS.splits)})],
        // X-R49: a code is a string. JSON can carry a list, and a list of one code, used as a property name, is that code.
        ["a list holding the plan's code", apiError(409, {error_code: [PLAN_CODE], message: PLAN_SERVER_SENTENCE, params: planParams(SPLITS.splits)})],
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

    // X-R49: with two codes the module may look the code up; only its own codes are found, never what an object inherits.
    it.each(['constructor', 'toString', '__proto__', 'hasOwnProperty', 'valueOf'])('an error_code that names what every object inherits (%s) is no code: null, and t is not called', (code) => {
        const {t, calls} = fakeT();

        expect(wipeRefusalMessage(apiError(409, {error_code: code, message: PLAN_SERVER_SENTENCE, params: planParams(SPLITS.splits)}), t)).toBeNull();
        expect(calls, 'an inherited member is not a key of the catalogue').toEqual([]);
    });
});

describe('wipeRefusalMessage — the provider removal’s split refusal is the assignment’s (X5-1)', () => {
    it('DELETE /assets/provider refuses a split with adjustments without a cost with the same code and params as the assignment: the plan’s key, the same values', () => {
        // The removal's params as the server sends them: the asset, the item and the splits, like the assignment's.
        const params = {asset_id: 7, item_index: 0, splits: [split('2026-02-10', [5, 6], 1, 12), split('2026-05-04', [7], 0, 15)]};
        const removal = fakeT();
        const assignment = fakeT();
        const refusal = (message: string) => apiError(409, {error_code: PLAN_CODE, message, params});
        const removalMessage = wipeRefusalMessage(refusal('Provider not removed: the server’s own sentence'), removal.t, dateLabel);
        wipeRefusalMessage(planRefused(params), assignment.t, dateLabel);

        const values = {date: 'D<2026-02-10>', n: 3, hidden: 1, more: 1};
        expect(onlyCall(removal.calls), 'one sentence for both operations: its own key, never a removal-specific one').toEqual({key: PLAN_KEY, values});
        expect(onlyCall(assignment.calls)).toEqual(onlyCall(removal.calls));
        expect(removalMessage).toBe(removal.outputs[0]);
        expectReadable(String(removalMessage));
    });
});

describe('wipeRefusalMessage — a provider removal that met a link made meanwhile (X-R62)', () => {
    it.each<[string, unknown]>([
        ['its params empty, as the server sends them', {}],
        ['params missing', undefined],
        ['params carrying a list after all', {events: [{event_id: 21, date: '2026-03-02', type: 'DIVIDEND', transaction_ids: [5], hidden_transactions_count: 1}]}],
    ])("%s: the conflict's own key, asked with no values — its sentence names nothing", (_label, params) => {
        const {t, calls, outputs} = fakeT();
        const message = wipeRefusalMessage(removalConflict(params), t, dateLabel);

        expect(onlyCall(calls).key, 'one message, one translation: the conflict’s own').toBe(CONFLICT_KEY);
        expect(calls[0].values ?? {}, 'asked with no values: the sentence names nothing').toEqual({});
        expect(message, 'the sentence is the translation, as t wrote it').toBe(outputs[0]);
        expectReadable(String(message));
    });
});

describe('wipeRefusalMessage — the code the removal no longer has is an unknown code (X5-1)', () => {
    const EVENTS = {asset_id: 7, item_index: 0, events: [{event_id: 21, date: '2026-03-02', type: 'DIVIDEND', transaction_ids: [5], hidden_transactions_count: 1}]};

    it.each<[string, unknown]>([
        ['PROVIDER_REMOVAL_LINKED_TRANSACTIONS with the events it used to list', goneRefusal(EVENTS)],
        ['the same code with no params', goneRefusal(undefined)],
        ['the same code with splits, as if it were the plan’s', goneRefusal({splits: [split('2026-02-10', [5], 1)]})],
        ['another code of the removal, with the same events', apiError(409, {error_code: 'PROVIDER_REMOVAL_SOMETHING_NEW', message: REMOVAL_SERVER_SENTENCE, params: EVENTS})],
        // A code is a string. JSON can carry a list, and a list of one code, used as a property name, is that code.
        ["a list holding the conflict's code", apiError(409, {error_code: [CONFLICT_CODE], message: REMOVAL_SERVER_SENTENCE, params: {}})],
        ['a structured detail without a code, with the events', apiError(409, {message: REMOVAL_SERVER_SENTENCE, params: EVENTS})],
        ['a string detail naming the old code', apiError(409, GONE_CODE)],
        ['a list detail holding the old refusal', apiError(409, [{error_code: GONE_CODE, message: REMOVAL_SERVER_SENTENCE, params: EVENTS}])],
    ])('%s: null, and the catalogue is not asked — the caller keeps its generic sentence', (_label, err) => {
        const {t, calls} = fakeT();

        expect(wipeRefusalMessage(err, t)).toBeNull();
        expect(calls, 'nothing is asked of the catalogue').toEqual([]);
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

/** The names a message counts with a cardinal plural that has a CLDR `many` branch, at any depth, sorted. */
function pluralsWithMany(message: string): string[] {
    const names = elementsOf(parse(message)).flatMap((element) => (element.type === PLURAL_TYPE && 'pluralType' in element && element.pluralType === 'cardinal' && 'options' in element && 'many' in element.options ? [element.value] : []));
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

describe('the wipe’s sentence is gone from the four generated catalogues (N68)', () => {
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

    it.each(SUPPORTED_LOCALES)('%s: the key of the refusal that no longer exists is gone from the catalogue', (lang) => {
        expect(messageAt(CATALOGUES[lang], KEY), `the generated ${lang} catalogue still carries ${KEY}: MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST does not exist any more`).toBeUndefined();
    });

    it.each(SUPPORTED_LOCALES)('%s: the plan’s key, its sibling, is still there', (lang) => {
        expect(typeof messageAt(CATALOGUES[lang], PLAN_KEY), `the generated ${lang} catalogue lost ${PLAN_KEY} with the wipe’s key`).toBe('string');
    });
});

describe("the plan's sentence in the four generated catalogues (X-R49)", () => {
    beforeAll(async () => {
        init({fallbackLocale: 'en', initialLocale: 'en'});
        await waitLocale('en');
    });

    afterEach(async () => {
        // The language is module-level state shared by every case of the file.
        await uiLanguage('en');
    });

    it.each(SUPPORTED_LOCALES)('%s: the generated catalogue has the key, in words of its own — not the English', (lang) => {
        const text = messageAt(CATALOGUES[lang], PLAN_KEY);

        expect(typeof text, `the generated ${lang} catalogue has no ${PLAN_KEY}`).toBe('string');
        if (lang !== 'en') expect(text, `the ${lang} source has no ${PLAN_KEY}: this is the English text the build fills it with`).not.toBe(messageAt(CATALOGUES.en, PLAN_KEY));
    });

    it.each(SUPPORTED_LOCALES)('%s: its text names exactly date, n, hidden and more — the values the module passes — and counts n, hidden and more with ICU plurals', (lang) => {
        const text = messageAt(CATALOGUES[lang], PLAN_KEY);
        expect(typeof text, `premise: the generated ${lang} catalogue has ${PLAN_KEY}`).toBe('string');

        expect(argumentNames(String(text)), 'a name the module does not pass leaves the raw text on screen; one it passes and the text drops is a figure lost').toEqual(['date', 'hidden', 'more', 'n']);
        expect(cardinalPlurals(String(text)), 'n, hidden and more are counts: ICU plurals').toEqual(['hidden', 'more', 'n']);
    });

    it('fr: n, hidden and more each carry the CLDR many branch', () => {
        expect(pluralsWithMany('{n, plural, one {# item} other {# items}}'), 'control: a count without the branch').toEqual([]);
        expect(pluralsWithMany('{n, plural, one {# a} many {# b} other {# c}}{hidden, plural, one {# a} many {# b} other {# c}}{more, plural, one {# a} many {# b} other {# c}}'), 'control: a message with the branch in its three counts').toEqual(['hidden', 'more', 'n']);
        const text = messageAt(CATALOGUES.fr, PLAN_KEY);
        expect(typeof text, `premise: the generated fr catalogue has ${PLAN_KEY}`).toBe('string');

        expect(pluralsWithMany(String(text))).toEqual(['hidden', 'more', 'n']);
    });

    it.each(SUPPORTED_LOCALES)('%s: through the module and svelte-i18n, every value is written, no ICU syntax is left, and a 0 says nothing', async (lang) => {
        await uiLanguage(lang);
        // n 5 (3 in sight, 2 hidden), hidden 2, more 3: three figures above 1, which every language writes as digits.
        const several = wipeRefusalMessage(planRefused(planParams([split('2026-02-10', [5, 6, 7], 2, 12), split('2026-03-11', [8], 0, 13), split('2026-04-12', [], 1, 14), split('2026-05-13', [9], 0, 15)])), get(_), dateLabel);
        // n 1, hidden 0, more 0: nothing hidden and no other split.
        const one = wipeRefusalMessage(planRefused(planParams([split('2026-02-10', [5], 0)])), get(_), dateLabel);

        for (const message of [several, one]) {
            expect(message, "the module words the plan's refusal").not.toBeNull();
            expect(message, `control: the ${lang} catalogue has the message, not the bare key`).not.toBe(PLAN_KEY);
            expectReadable(String(message));
            expect(message, 'the first split, by its date label').toContain('D<2026-02-10>');
            expect(message, 'every argument and plural formatted: a name the text needs and the module does not pass leaves the raw text').not.toMatch(/[{}]/);
            expect(figures(String(message)), 'no figure 0: with nothing hidden and no other split, the sentence says nothing of either').not.toContain('0');
        }
        expect(figures(String(several)), 'n = 5, hidden = 2 and more = 3 are written').toEqual(expect.arrayContaining(['5', '2', '3']));
    });
});

describe("the provider removal's sentences in the four generated catalogues (X-R62, trimmed by X5-1)", () => {
    beforeAll(async () => {
        init({fallbackLocale: 'en', initialLocale: 'en'});
        await waitLocale('en');
    });

    afterEach(async () => {
        // The language is module-level state shared by every case of the file.
        await uiLanguage('en');
    });

    it.each(SUPPORTED_LOCALES)("%s: the conflict's key is in words of its own — not the English, not the plan's sentence", (lang) => {
        const conflict = messageAt(CATALOGUES[lang], CONFLICT_KEY);

        expect(typeof conflict, `the generated ${lang} catalogue has no ${CONFLICT_KEY}`).toBe('string');
        if (lang !== 'en') expect(conflict, `the ${lang} source has no ${CONFLICT_KEY}: this is the English text the build fills it with`).not.toBe(messageAt(CATALOGUES.en, CONFLICT_KEY));
        expect(conflict, 'two refusals, two sentences').not.toBe(messageAt(CATALOGUES[lang], PLAN_KEY));
    });

    it.each(SUPPORTED_LOCALES)('%s: the key of the refusal that no longer exists is gone from the catalogue', (lang) => {
        expect(messageAt(CATALOGUES[lang], GONE_KEY), `the generated ${lang} catalogue still carries ${GONE_KEY}: PROVIDER_REMOVAL_LINKED_TRANSACTIONS does not exist any more`).toBeUndefined();
    });

    it.each(SUPPORTED_LOCALES)('%s: the conflict sentence names nothing — the module passes it nothing', (lang) => {
        const text = messageAt(CATALOGUES[lang], CONFLICT_KEY);
        expect(typeof text, `premise: the generated ${lang} catalogue has ${CONFLICT_KEY}`).toBe('string');

        expect(argumentNames(String(text)), 'a name the text needs and no value fills leaves the raw text on screen').toEqual([]);
    });

    it.each(SUPPORTED_LOCALES)('%s: through the module and svelte-i18n, the conflict is written with no ICU syntax left', async (lang) => {
        await uiLanguage(lang);
        const conflict = wipeRefusalMessage(removalConflict({}), get(_), dateLabel);

        expect(conflict, "the module words the removal's conflict").not.toBeNull();
        expect(conflict, `control: the ${lang} catalogue has the message, not the bare key`).not.toBe(CONFLICT_KEY);
        expectReadable(String(conflict));
        expect(conflict, 'no ICU syntax left').not.toMatch(/[{}]/);
    });
});
