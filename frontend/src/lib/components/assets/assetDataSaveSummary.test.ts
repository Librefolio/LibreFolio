/**
 * assetDataSaveSummary — pure unit tests (O-8, workstream X; Vitest, node env).
 *
 * Why. The asset data editor (`AssetDataEditorSection.svelte`, `handleSave`) tells the user what a save did in
 * English whatever the interface language — «Asset data: 12 prices saved, 1 skipped (invalid)» — with one translated
 * part (`events.deleteSuccess`) in the middle of it. The message moves into this pure function over the catalogue;
 * the component passes it as the toast of `notify({name: 'assets.data.saved', …})`. That wiring is pinned by the E2E
 * (`e2e/assets/asset-data-editor.spec.ts`), on the event and never on the toast's words.
 *
 * Contract. One part per non-zero count, in this order: prices saved (`assets.dataEditor.pricesSaved`, value
 * `count`), prices the server refused (`assets.dataEditor.pricesRefused`, `count`; X-R46, below), prices deleted
 * (`assets.dataEditor.pricesDeleted`, `count`), prices skipped as invalid (`assets.dataEditor.pricesSkipped`,
 * `count`), events deleted (the existing `events.deleteSuccess`, `n`), events saved (`assets.dataEditor.eventsSaved`,
 * `count`). The parts are joined by «, » inside `assets.dataEditor.saved` (`details`). Nothing to report → null, and
 * the catalogue is not even asked.
 *
 * X-R46 (release 1.3, workstream X). A price save the server takes in part — a 200 whose `results[0].rejected` lists
 * the days it left out: an impossible OHLC, a day out of range, a value it cannot store — was counted whole, every row
 * sent announced as saved. The editor now counts as saved what the server kept, and the rest in `pricesRefused`, a new
 * optional count of `AssetDataSaveCounts`: a counts object without it reads as before. Above 0 it is a part of its
 * own, right after prices saved and before prices deleted; absent (or undefined) or 0, no part. Alone it still makes a
 * summary, never null: a save that kept nothing has something to tell. The summary counts the days refused; it does
 * not name them.
 *
 * How. Twice.
 *   - A recording catalogue pins the lookups — keys, values, order — and the assembly: it answers each lookup with a
 *     token naming it, so the result itself shows which key every piece came from and what it was given. The fields
 *     of the counts are passed in the reverse of the contract's order, so walking the object is not enough.
 *   - The real catalogue (svelte-i18n with the generated `<lang>.json`, as the app formats it), in English and in
 *     Italian: the new keys exist, O-8's five and X-R46's `assets.dataEditor.pricesRefused` (svelte-i18n echoes a
 *     missing key, so a message is one that is not its key), and the Italian ones are not the English fallback; the
 *     counting parts — five since X-R46 — are ICU plurals on `count` (the count is written, no raw ICU is left, and 1
 *     is not 2 with its digit changed); a summary is the catalogue's own words for each key, assembled — never a
 *     literal of this file. svelte-i18n caches a formatter by its text alone (devpy-i18n, rule 5), so each language's
 *     texts are formatted while that language is the current one.
 * Inputs are frozen, so a summary that writes into them throws (ES modules run in strict mode).
 *
 * Expected, O-8. Red before O-8 in every case but the two guards on `events.deleteSuccess` (one per language): the
 * function threw «not implemented», and none of the five `assets.dataEditor.*` keys was in the catalogue. Green once
 * the function and the keys (four languages, `src/lib/i18n/assets/<lang>.json`) were in. The guards are green before
 * and after: they pin that the reused key still writes the `n` the summary passes it.
 *
 * Expected, X-R46. Red before X-R46, for two reasons. The function ignores `pricesRefused`: red, every case with a
 * `pricesRefused` above 0 — alone, among all six counts, between prices saved and prices deleted. And
 * `assets.dataEditor.pricesRefused` is in no catalogue: red, in English and in Italian, the key's presence and its
 * ICU plural; the two summaries through the real catalogue are red for both reasons. Green once the function writes
 * the part and the key is in the four catalogues. Green before and after: all of O-8, and the guards of the new rule —
 * a `pricesRefused` absent, undefined or 0 is no part, and with nothing else to report the summary is still null.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit` (action
 * `core-unit`), next to `assetSearchReport.test.ts`.
 */
import {afterAll, beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';
import {setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import {assetDataSaveSummary, type AssetDataSaveCounts, type Translate} from './assetDataSaveSummary';

const SAVED = 'assets.dataEditor.saved';
const PRICES_SAVED = 'assets.dataEditor.pricesSaved';
/** X-R46: the prices the server left out of a save it took in part. */
const PRICES_REFUSED = 'assets.dataEditor.pricesRefused';
const PRICES_DELETED = 'assets.dataEditor.pricesDeleted';
const PRICES_SKIPPED = 'assets.dataEditor.pricesSkipped';
const EVENTS_SAVED = 'assets.dataEditor.eventsSaved';
/** Reused, not new: the editor already writes it for the events a save deleted, with `n`. */
const EVENTS_DELETED = 'events.deleteSuccess';

/** The keys the contract adds to the catalogue: O-8's five, and X-R46's prices refused. */
const NEW_KEYS = [SAVED, PRICES_SAVED, PRICES_REFUSED, PRICES_DELETED, PRICES_SKIPPED, EVENTS_SAVED];
/** The new keys that count something: ICU plurals on `count`. */
const COUNTING_KEYS = [PRICES_SAVED, PRICES_REFUSED, PRICES_DELETED, PRICES_SKIPPED, EVENTS_SAVED];

/** One part of a summary: the count it reads, its key, the name of the value it passes. */
type Part = {field: keyof AssetDataSaveCounts; key: string; value: 'count' | 'n'};

/** The parts in the order the contract writes them: the prices the server refused right after those it saved (X-R46). */
const PARTS: readonly Part[] = [
    {field: 'pricesSaved', key: PRICES_SAVED, value: 'count'},
    {field: 'pricesRefused', key: PRICES_REFUSED, value: 'count'},
    {field: 'pricesDeleted', key: PRICES_DELETED, value: 'count'},
    {field: 'pricesSkipped', key: PRICES_SKIPPED, value: 'count'},
    {field: 'eventsDeleted', key: EVENTS_DELETED, value: 'n'},
    {field: 'eventsSaved', key: EVENTS_SAVED, value: 'count'},
];

/** A save that did nothing — written as before X-R46, without `pricesRefused`: an absent count is nothing too. */
const NOTHING: AssetDataSaveCounts = {pricesSaved: 0, pricesDeleted: 0, pricesSkipped: 0, eventsDeleted: 0, eventsSaved: 0};

/** A frozen copy of `counts`, its fields in the order given. */
function frozen(counts: AssetDataSaveCounts): AssetDataSaveCounts {
    return Object.freeze({...counts});
}

// =============================================================================
// The recording catalogue
// =============================================================================

/** One lookup the summary made: the key, and a copy of the values it passed, taken at the call. */
type Lookup = {key: string; values?: Record<string, string | number>};

/**
 * A catalogue that records every lookup and answers it with a token naming it — `⟨assets.dataEditor.pricesSaved
 * count=12⟩`, `⟨assets.dataEditor.saved details=…⟩` — so the result shows where each piece came from.
 */
function recordingCatalogue(): {translate: Translate; lookups: Lookup[]} {
    const lookups: Lookup[] = [];
    const translate: Translate = (key, options) => {
        lookups.push(options === undefined ? {key} : {key, values: {...options.values}});
        const values = Object.entries(options?.values ?? {})
            .map(([name, value]) => ` ${name}=${value}`)
            .join('');
        return `⟨${key}${values}⟩`;
    };
    return {translate, lookups};
}

/** The token the recording catalogue answers for `key` looked up with the one value `name` = `value`. */
function token(key: string, name: string, value: string | number): string {
    return `⟨${key} ${name}=${value}⟩`;
}

describe('assetDataSaveSummary — what it asks the catalogue, and how it puts the answers together', () => {
    it('a save with nothing to report is null, and the catalogue is not even asked', () => {
        const {translate, lookups} = recordingCatalogue();

        expect(assetDataSaveSummary(frozen(NOTHING), translate), 'nothing saved, deleted or skipped: no message').toBeNull();
        expect(lookups, 'not even the wrapper: an empty «Asset data:» is the toast the editor refuses to show').toEqual([]);
    });

    it.each(PARTS)('only $field: its one part — $key with {$value} — inside assets.dataEditor.saved, with no separator', ({field, key, value}) => {
        const {translate, lookups} = recordingCatalogue();

        const summary = assetDataSaveSummary(frozen({...NOTHING, [field]: 7}), translate);

        expect(lookups, 'the part, then the wrapper given that part as its details').toEqual([
            {key, values: {[value]: 7}},
            {key: SAVED, values: {details: token(key, value, 7)}},
        ]);
        expect(summary).toBe(token(SAVED, 'details', token(key, value, 7)));
    });

    it('every count: six parts in the contract’s order — not the order of the fields — joined by «, » inside assets.dataEditor.saved', () => {
        const {translate, lookups} = recordingCatalogue();
        // The fields in the reverse of the contract's order: a summary that walks the object writes them backwards.
        const counts = frozen({eventsSaved: 5, eventsDeleted: 1, pricesSkipped: 2, pricesDeleted: 3, pricesRefused: 4, pricesSaved: 12});
        const details = '⟨assets.dataEditor.pricesSaved count=12⟩, ⟨assets.dataEditor.pricesRefused count=4⟩, ⟨assets.dataEditor.pricesDeleted count=3⟩, ⟨assets.dataEditor.pricesSkipped count=2⟩, ⟨events.deleteSuccess n=1⟩, ⟨assets.dataEditor.eventsSaved count=5⟩';

        const summary = assetDataSaveSummary(counts, translate);

        expect(lookups, 'each count looked up under its own key and value name, in order, then the wrapper').toEqual([
            {key: PRICES_SAVED, values: {count: 12}},
            {key: PRICES_REFUSED, values: {count: 4}},
            {key: PRICES_DELETED, values: {count: 3}},
            {key: PRICES_SKIPPED, values: {count: 2}},
            {key: EVENTS_DELETED, values: {n: 1}},
            {key: EVENTS_SAVED, values: {count: 5}},
            {key: SAVED, values: {details}},
        ]);
        expect(summary).toBe(`⟨assets.dataEditor.saved details=${details}⟩`);
    });

    it('two counts of five — the example of the contract, «12 prices saved, 1 event deleted»: the zero ones leave no part and no stray separator', () => {
        const {translate, lookups} = recordingCatalogue();

        const summary = assetDataSaveSummary(frozen({...NOTHING, pricesSaved: 12, eventsDeleted: 1}), translate);

        expect(lookups.map(({key}) => key)).toEqual([PRICES_SAVED, EVENTS_DELETED, SAVED]);
        expect(summary).toBe('⟨assets.dataEditor.saved details=⟨assets.dataEditor.pricesSaved count=12⟩, ⟨events.deleteSuccess n=1⟩⟩');
    });
});

describe('assetDataSaveSummary — the prices the server refused (X-R46)', () => {
    /** O-8's five counts, every one above 0, in the reverse of the contract's order — and no `pricesRefused` at all. */
    const EVERY_O8_COUNT: AssetDataSaveCounts = {eventsSaved: 5, eventsDeleted: 1, pricesSkipped: 2, pricesDeleted: 3, pricesSaved: 12};
    /** What the recording catalogue makes of them: their five parts, in the contract's order. */
    const EVERY_O8_DETAILS = '⟨assets.dataEditor.pricesSaved count=12⟩, ⟨assets.dataEditor.pricesDeleted count=3⟩, ⟨assets.dataEditor.pricesSkipped count=2⟩, ⟨events.deleteSuccess n=1⟩, ⟨assets.dataEditor.eventsSaved count=5⟩';

    it('a save the server took in part: prices refused right after prices saved, before prices deleted — the three given the other way round — and the zero counts leave no part and no stray separator', () => {
        const {translate, lookups} = recordingCatalogue();
        // Every field written, in the reverse of the contract's order: a summary that walks the object writes them backwards.
        const counts = frozen({eventsSaved: 0, eventsDeleted: 0, pricesSkipped: 0, pricesDeleted: 3, pricesRefused: 2, pricesSaved: 12});
        const details = '⟨assets.dataEditor.pricesSaved count=12⟩, ⟨assets.dataEditor.pricesRefused count=2⟩, ⟨assets.dataEditor.pricesDeleted count=3⟩';

        const summary = assetDataSaveSummary(counts, translate);

        expect(lookups, 'prices saved, then prices refused with their own count, then prices deleted, then the wrapper').toEqual([
            {key: PRICES_SAVED, values: {count: 12}},
            {key: PRICES_REFUSED, values: {count: 2}},
            {key: PRICES_DELETED, values: {count: 3}},
            {key: SAVED, values: {details}},
        ]);
        expect(summary).toBe(`⟨assets.dataEditor.saved details=${details}⟩`);
    });

    it.each<[string, AssetDataSaveCounts]>([
        ['absent — a counts object written as before X-R46', EVERY_O8_COUNT],
        ['undefined', {...EVERY_O8_COUNT, pricesRefused: undefined}],
        ['0', {...EVERY_O8_COUNT, pricesRefused: 0}],
    ])('guard: pricesRefused %s is no part — O-8’s five counts read as they did', (_label, counts) => {
        const {translate, lookups} = recordingCatalogue();

        const summary = assetDataSaveSummary(frozen(counts), translate);

        expect(
            lookups.map(({key}) => key),
            `never a lookup of ${PRICES_REFUSED}`,
        ).toEqual([PRICES_SAVED, PRICES_DELETED, PRICES_SKIPPED, EVENTS_DELETED, EVENTS_SAVED, SAVED]);
        expect(summary).toBe(`⟨assets.dataEditor.saved details=${EVERY_O8_DETAILS}⟩`);
    });

    it.each<[string, AssetDataSaveCounts]>([
        ['undefined', {...NOTHING, pricesRefused: undefined}],
        ['0', {...NOTHING, pricesRefused: 0}],
    ])('guard: pricesRefused %s, with every other count 0, is still nothing to report — null, and the catalogue is not even asked', (_label, counts) => {
        const {translate, lookups} = recordingCatalogue();

        expect(assetDataSaveSummary(frozen(counts), translate)).toBeNull();
        expect(lookups).toEqual([]);
    });
});

// =============================================================================
// The real catalogue
// =============================================================================

/** A message of the catalogue as the app formats it: svelte-i18n, in the current interface language unless `locale`. */
function catalogue(key: string, values?: Record<string, string | number>, locale?: string): string {
    return get(_)(key, {values, locale});
}

/** Whether `text` writes the number `n` on its own: `2`, not the 2 of `12`. */
function writes(text: string, n: number): boolean {
    return new RegExp(`(?<!\\d)${n}(?!\\d)`).test(text);
}

/** Values every new key can be formatted with: each reads the one it names and ignores the other. */
const ANY_VALUES = {count: 2, details: '·'};

/** The cases each language must pass. `lang` is the current interface language while they run. */
function catalogueCases(lang: 'en' | 'it'): void {
    it.each(NEW_KEYS)(`%s is a message of the ${lang} catalogue — not its key echoed back${lang === 'en' ? '' : ', nor the English fallback'}`, (key) => {
        const text = catalogue(key, ANY_VALUES);

        expect(text, `svelte-i18n echoes a missing key: the ${lang} catalogue has no ${key}`).not.toBe(key);
        // A language that is not the fallback must have words of its own: a key missing there renders the English text.
        if (lang !== 'en') expect(text, `the ${lang} catalogue has no ${key} of its own: this is the English fallback`).not.toBe(catalogue(key, ANY_VALUES, 'en'));
    });

    it.each(COUNTING_KEYS)(`%s is an ICU plural on count in ${lang}: the count is written, and 1 is not 2 with its 2 written as 1`, (key) => {
        const one = catalogue(key, {count: 1});
        const two = catalogue(key, {count: 2});

        expect(two, `premise: the ${lang} catalogue has ${key}`).not.toBe(key);
        // A placeholder the summary does not pass makes svelte-i18n give up and return the raw message, braces and all.
        expect(one, `no raw ICU left: the value ${key} reads is named count`).not.toMatch(/[{}]/);
        expect(two, `no raw ICU left: the value ${key} reads is named count`).not.toMatch(/[{}]/);
        expect(writes(two, 2), `«${two}» writes its count`).toBe(true);
        expect(one, `1 must not read as the plural «${two}» with its 2 written as 1`).not.toBe(two.replace(/(?<!\d)2(?!\d)/, '1'));
    });

    // Every count, pricesRefused included (X-R46) — `Required`, so each part of PARTS has its count — and every
    // counting key read at 1 in one case and at 2 in the other.
    it.each<[string, Required<AssetDataSaveCounts>]>([
        ['1, 2, 2, 1 prices and 2, 1 events', {pricesSaved: 1, pricesRefused: 2, pricesDeleted: 2, pricesSkipped: 1, eventsDeleted: 2, eventsSaved: 1}],
        ['2, 1, 1, 2 prices and 1, 2 events', {pricesSaved: 2, pricesRefused: 1, pricesDeleted: 1, pricesSkipped: 2, eventsDeleted: 1, eventsSaved: 2}],
    ])(`${lang}: a save of %s reads as the catalogue’s own words for each part, joined by «, » inside assets.dataEditor.saved`, (_label, counts) => {
        const mark = '⟨details⟩';
        const wrapped = catalogue(SAVED, {details: mark});
        expect(wrapped, `premise: the ${lang} catalogue has ${SAVED}`).not.toBe(SAVED);
        expect(wrapped, `premise: ${SAVED} writes its details — the value it reads is named details`).toContain(mark);
        expect(wrapped, `premise: ${SAVED} puts words of its own around them`).not.toBe(mark);
        const details = PARTS.map(({field, key, value}) => catalogue(key, {[value]: counts[field]})).join(', ');

        expect(assetDataSaveSummary(frozen(counts), get(_))).toBe(catalogue(SAVED, {details}));
    });

    it(`guard: the reused ${EVENTS_DELETED} still writes the n the summary passes it, in ${lang}`, () => {
        const text = catalogue(EVENTS_DELETED, {n: 2});

        expect(text, `the ${lang} catalogue has ${EVENTS_DELETED}`).not.toBe(EVENTS_DELETED);
        expect(text, `no raw ICU left: the value ${EVENTS_DELETED} reads is named n`).not.toMatch(/[{}]/);
        expect(writes(text, 2), `«${text}» writes its n`).toBe(true);
    });
}

describe('assetDataSaveSummary — the English catalogue', () => {
    beforeAll(async () => {
        await setupI18n('en');
    });

    catalogueCases('en');
});

describe('assetDataSaveSummary — the Italian catalogue', () => {
    beforeAll(async () => {
        // In place, as the language selector switches it: the Italian texts compile with the Italian plural rules.
        await setupI18n('it');
    });

    afterAll(async () => {
        // The language is module-level state shared by every case of the file.
        await setupI18n('en');
    });

    catalogueCases('it');
});
