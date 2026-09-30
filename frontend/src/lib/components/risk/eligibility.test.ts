/**
 * @vitest-environment node
 *
 * eligibility — pure unit tests (node env, no jsdom).
 *
 * The verdict is Risk's (`POST /api/v1/risk/eligibility`) and is never computed
 * here: this module splits the request, merges the answers and words them. So
 * the fixtures are engine answers typed with the generated
 * `AssetEligibilityItem`, and every sentence is observed through a fake `t` that
 * writes down what it is asked — the key and its values — and answers with a
 * marker. Nothing here reads the catalogue's wording: what the module owns is
 * which key it asks for, with which values, and what it shows when the answer
 * is missing. The one real formatter, `dayFormatter`, is checked against `Intl`
 * itself, in zones chosen to catch the two ways of moving a day.
 *
 * **The reasons are read off the generated enum, never listed.** `reasonText`'s
 * switch is exhaustive over `RiskEligibilityReason`, which fails `front check`
 * when the engine grows a reason — but at run time an unworded reason is simply
 * `null`, and the level's label stands in for it. So every loop below iterates
 * `schemas.RiskEligibilityReason.options`: a reason the engine adds is in them the
 * day the client is regenerated, and they stay red until it is worded here, in
 * the code and in the four catalogues. The last block reads the catalogues
 * themselves — the one place this file does — for presence and for the arguments
 * each sentence asks for, never for its wording.
 *
 * **The period offer is read, not computed.** The engine suggests a period and names
 * the span every asset is quoted in; the module only reads the two ranges from a
 * single answer (`toDayRange`) and decides whom a suggestion brings back
 * (`fitPeriodOffer`). The cases below pin both halves: which answers a range may be
 * read from, and which selected assets count as recoverable.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

import {schemas} from '$lib/api';
import {SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import {icuArguments} from '$test/riskWarningCatalogue';

import {ELIGIBILITY_BATCH, EMPTY_VERDICTS, dayFormatter, describeEligibility, eligibilityBatches, fitPeriodOffer, isSelectable, mergeEligibilityAnswers, reasonText, toDayRange, type AssetEligibilityItem, type DayRange, type EligibilityReason, type EligibilityVerdicts} from './eligibility';

/** A verdict as the engine sends it: eligible, with nothing to say, unless told otherwise. */
function verdict(assetId: number, overrides: Partial<AssetEligibilityItem> = {}): AssetEligibilityItem {
    return {asset_id: assetId, level: 'eligible', reasons: [], first_quote: '2019-01-02', last_quote: '2024-12-31', quotes_in_period: 250, ...overrides};
}

/** The verdicts the laboratory holds, with the engine's two thresholds. */
function verdictsOf(items: readonly AssetEligibilityItem[], minQuotes = 60, staleDays = 7): EligibilityVerdicts {
    return {items: new Map(items.map((item) => [item.asset_id, item])), minQuotes, staleDays};
}

/** One engine answer, in the shape the endpoint returns it. */
function answer(items: readonly AssetEligibilityItem[], minQuotes = 60, staleDays = 7) {
    return {items, min_quotes: minQuotes, stale_days: staleDays};
}

type TranslateOptions = {values?: Record<string, string | number>};

/** What the fake `t` answers: never a string that starts like a key, so the module takes it as a sentence. */
const marker = (key: string): string => `<${key}>`;

/**
 * A `t` that writes down every key it is asked for, with its options, and
 * answers through `reply` — the marker by default; the key itself, or nothing,
 * to play a catalogue that lacks the sentence.
 */
function recordingT(reply: (key: string) => string = marker) {
    const calls: Array<[key: string, options: TranslateOptions | undefined]> = [];
    const t = (key: string, options?: TranslateOptions): string => {
        calls.push([key, options]);
        return reply(key);
    };
    return {t, calls};
}

/** Marks every date that went through the formatter, so a raw ISO day cannot pass for a formatted one. */
const formatDay = (isoDay: string): string => `day:${isoDay}`;

/** The thresholds the wording cases quote: distinct from each other and from every number in the items. */
const VERDICTS = verdictsOf([], 60, 7);

/** An asset whose every number and date differs from the others, so no value can stand in for another. */
const SUBJECT = verdict(4, {level: 'warning', quotes_in_period: 12, first_quote: '2023-03-15', last_quote: '2024-11-29'});

/** Every reason the engine can give, read off the generated enum rather than written down here. */
const GENERATED_REASONS: readonly EligibilityReason[] = schemas.RiskEligibilityReason.options;

/**
 * What each reason's sentence quotes for `SUBJECT`; `undefined` for one that quotes nothing.
 *
 * A `Record` over the generated enum, so a reason without an entry fails `front check`
 * here too. At run time the first `reasonText` case names it instead of letting it
 * default to "quotes nothing".
 */
const REASON_VALUES: Record<EligibilityReason, TranslateOptions | undefined> = {
    no_price_history: undefined,
    no_prices: undefined,
    too_few_quotes: {values: {minQuotes: 60, count: 12}},
    missing_fx: {values: {currency: 'CHF'}},
    starts_late: {values: {date: 'day:2023-03-15'}},
    stale_at_end: {values: {date: 'day:2024-11-29', days: 7}},
};

/** Every generated reason, with its full key and the values its sentence quotes for `SUBJECT`. */
const REASON_KEYS: ReadonlyArray<readonly [EligibilityReason, string, TranslateOptions | undefined]> = GENERATED_REASONS.map((reason) => [reason, `risk.eligibility.reasons.${reason}`, REASON_VALUES[reason]] as const);

/** A code no generated enum has: the fallback cases below play a reason newer than this client with it. */
const NEWER_REASON = 'halted_trading';

describe('isSelectable', () => {
    const verdicts = verdictsOf([verdict(1), verdict(2, {level: 'warning', reasons: ['starts_late']}), verdict(3, {level: 'ineligible', reasons: ['no_prices']})]);

    it('lets in an asset with no verdict: a missing answer never locks one out', () => {
        expect(isSelectable(verdicts, 99)).toBe(true);
        // Not asked yet, or the engine failed: the panel holds the empty verdicts,
        // and the asset ruled out above is selectable again.
        expect(isSelectable(EMPTY_VERDICTS, 3)).toBe(true);
    });

    it('lets in an asset that is eligible, or only warned about', () => {
        expect(isSelectable(verdicts, 1)).toBe(true);
        expect(isSelectable(verdicts, 2)).toBe(true);
    });

    it('keeps out an asset the engine rules ineligible', () => {
        expect(isSelectable(verdicts, 3)).toBe(false);
    });
});

describe('eligibilityBatches', () => {
    /** Descending ids, so "in the order given" cannot pass for "sorted". */
    const idsDown = (count: number): number[] => Array.from({length: count}, (_, index) => 10_000 - index);

    /**
     * `ids` behind a guard that throws once the list has been read far more often
     * than any split of it needs. The loop it protects is synchronous: a step that
     * never advanced would not fail, it would freeze the run until the heap gave out.
     */
    function stallGuard(ids: readonly number[]): readonly number[] {
        let reads = 0;
        return new Proxy(ids, {
            get(target, property, receiver) {
                reads += 1;
                if (reads > 1_000) throw new Error('eligibilityBatches is not advancing: the ids were read 1000 times');
                return Reflect.get(target, property, receiver);
            },
        });
    }

    it('batches at 500, the most the engine accepts in one request', () => {
        // `RiskEligibilityRequest.asset_ids` is `min_length=1, max_length=500` on the backend.
        expect(ELIGIBILITY_BATCH).toBe(500);
    });

    it('makes no request at all for no ids', () => {
        // An empty batch is one the engine would reject (`min_length=1`), so none is built.
        expect(eligibilityBatches([])).toEqual([]);
    });

    it('fits 500 ids in one batch, and needs a second for the 501st', () => {
        const full = idsDown(500);
        expect(eligibilityBatches(full)).toEqual([full]);
        expect(eligibilityBatches(idsDown(501)).map((batch) => batch.length)).toEqual([500, 1]);
    });

    it('splits 1001 ids into three batches, in the order given', () => {
        const ids = idsDown(1001);
        const batches = eligibilityBatches(ids);
        expect(batches.map((batch) => batch.length)).toEqual([500, 500, 1]);
        expect(batches.flat()).toEqual(ids);
    });

    it('never builds a batch the engine would refuse, whatever the count', () => {
        for (const count of [1, 499, 500, 501, 1000, 1001, 1500]) {
            const batches = eligibilityBatches(idsDown(count));
            expect(batches.length, `${count} ids`).toBe(Math.ceil(count / ELIGIBILITY_BATCH));
            expect(
                batches.every((batch) => batch.length >= 1 && batch.length <= ELIGIBILITY_BATCH),
                `${count} ids`,
            ).toBe(true);
        }
    });

    it('honours a custom size, the last batch taking the remainder', () => {
        expect(eligibilityBatches([7, 3, 9, 1, 5, 8, 2], 3)).toEqual([[7, 3, 9], [1, 5, 8], [2]]);
    });

    it('asks one id at a time for a size of zero or less, instead of never advancing', () => {
        expect(eligibilityBatches(stallGuard([1, 2, 3]), 0)).toEqual([[1], [2], [3]]);
        expect(eligibilityBatches(stallGuard([1, 2, 3]), -2)).toEqual([[1], [2], [3]]);
    });

    it('asks one id at a time for a size that is not a number, instead of one empty batch', () => {
        // `Math.max(1, NaN)` is NaN: a NaN step built `[[]]`, which asked for no id at
        // all and was the one request the engine rejects (`min_length=1`).
        expect(eligibilityBatches(stallGuard([1, 2, 3]), Number.NaN)).toEqual([[1], [2], [3]]);
    });
});

describe('mergeEligibilityAnswers', () => {
    it('answers the shared empty verdicts when there is nothing to merge', () => {
        expect(mergeEligibilityAnswers([])).toBe(EMPTY_VERDICTS);
        expect(EMPTY_VERDICTS.items.size).toBe(0);
    });

    it('gathers the items of every batch under their asset id', () => {
        const first = [verdict(3), verdict(1, {level: 'warning', reasons: ['stale_at_end']})];
        const second = [verdict(2, {level: 'ineligible', reasons: ['no_prices']})];
        const merged = mergeEligibilityAnswers([answer(first), answer(second)]);
        expect([...merged.items.keys()].sort((left, right) => left - right)).toEqual([1, 2, 3]);
        for (const item of [...first, ...second]) {
            expect(merged.items.get(item.asset_id)).toEqual(item);
        }
    });

    it('takes the thresholds from the first answer', () => {
        const merged = mergeEligibilityAnswers([answer([verdict(1)], 60, 7), answer([verdict(2)], 90, 14)]);
        expect([merged.minQuotes, merged.staleDays]).toEqual([60, 7]);
    });

    it("reads a single answer's two ranges as spans of days", () => {
        const merged = mergeEligibilityAnswers([{...answer([verdict(1)]), common_range: {start: '2023-03-15', end: '2024-11-29'}, suggested_range: {start: '2023-03-16', end: '2024-11-29'}}]);
        expect(merged.commonRange).toEqual({start: '2023-03-15', end: '2024-11-29'});
        expect(merged.suggestedRange).toEqual({start: '2023-03-16', end: '2024-11-29'});
    });

    it('reads the ranges through toDayRange: a list-wrapped range, and one without an end', () => {
        const merged = mergeEligibilityAnswers([{...answer([verdict(1)]), common_range: [{start: '2023-03-15', end: '2024-11-29'}], suggested_range: {start: '2024-11-29', end: null}}]);
        expect(merged.commonRange).toEqual({start: '2023-03-15', end: '2024-11-29'});
        expect(merged.suggestedRange).toEqual({start: '2024-11-29', end: '2024-11-29'});
    });

    it('has no range when the single answer names none', () => {
        const merged = mergeEligibilityAnswers([{...answer([verdict(1)]), common_range: null}]);
        expect(merged.commonRange).toBeNull();
        expect(merged.suggestedRange).toBeNull();
    });

    it('keeps no range from two batches or more: a span of the whole request cannot be merged here', () => {
        const ranged = {common_range: {start: '2023-03-15', end: '2024-11-29'}, suggested_range: {start: '2023-03-16', end: '2024-11-29'}};
        const merged = mergeEligibilityAnswers([
            {...answer([verdict(1)]), ...ranged},
            {...answer([verdict(2)]), ...ranged},
        ]);
        // The verdicts are merged as before; only the ranges are withheld.
        expect(merged.items.size).toBe(2);
        expect(merged.commonRange).toBeNull();
        expect(merged.suggestedRange).toBeNull();
    });
});

describe('toDayRange', () => {
    it('reads a range with both ends as it came', () => {
        expect(toDayRange({start: '2023-03-15', end: '2024-11-29'})).toEqual({start: '2023-03-15', end: '2024-11-29'});
    });

    it('reads a list-wrapped range through its first entry, and list-wrapped ends through theirs', () => {
        expect(toDayRange([{start: '2023-03-15', end: '2024-11-29'}])).toEqual({start: '2023-03-15', end: '2024-11-29'});
        expect(toDayRange({start: ['2023-03-15'], end: ['2024-11-29']})).toEqual({start: '2023-03-15', end: '2024-11-29'});
    });

    it.each([
        ['a missing end', {start: '2024-11-29'}],
        ['a null end', {start: '2024-11-29', end: null}],
        ['an empty list for an end', {start: '2024-11-29', end: []}],
        ['a list holding null for an end', {start: '2024-11-29', end: [null]}],
    ])('makes a single day of a range with %s', (_case, range) => {
        expect(toDayRange(range)).toEqual({start: '2024-11-29', end: '2024-11-29'});
    });

    it.each([
        ['nothing', undefined],
        ['null', null],
        ['an empty list', []],
        ['a range with no start', {end: '2024-11-29'}],
        ['a null start', {start: null, end: '2024-11-29'}],
        ['an empty start', {start: '', end: '2024-11-29'}],
        ['a start that is not a string', {start: 20241129, end: '2024-11-29'}],
    ])('is null for %s', (_case, range) => {
        expect(toDayRange(range)).toBeNull();
    });
});

describe('fitPeriodOffer', () => {
    const SUGGESTED: DayRange = {start: '2023-03-16', end: '2024-11-29'};
    // Distinct ids, listed against the selection's order below so that order is the selection's, not the map's.
    const WARNED = verdict(5, {level: 'warning', reasons: ['starts_late']});
    const RULED_OUT = verdict(7, {level: 'ineligible', reasons: ['no_prices']});
    const NEVER_QUOTED = verdict(9, {level: 'ineligible', reasons: ['no_price_history']});
    const ELIGIBLE_ONE = verdict(3);
    const NO_VERDICT = 11;
    const offered = (items: readonly AssetEligibilityItem[]): EligibilityVerdicts => ({...verdictsOf(items), suggestedRange: SUGGESTED});

    it('offers nothing without a suggested period, whoever the period leaves out', () => {
        const items = [WARNED, RULED_OUT];
        expect(fitPeriodOffer(verdictsOf(items), [5, 7])).toBeNull();
        expect(fitPeriodOffer({...verdictsOf(items), suggestedRange: null}, [5, 7])).toBeNull();
    });

    it('brings back the selected assets that are warned about or ruled out, in the order of the selection', () => {
        const verdicts = offered([ELIGIBLE_ONE, WARNED, RULED_OUT, NEVER_QUOTED]);
        expect(fitPeriodOffer(verdicts, [7, 3, 9, 5, NO_VERDICT])).toEqual({range: SUGGESTED, recoverable: [7, 5]});
    });

    it('leaves out an asset never quoted at all, an eligible one, and one with no verdict: no period helps them, or they need none', () => {
        const verdicts = offered([ELIGIBLE_ONE, NEVER_QUOTED]);
        // A suggestion is there, and it brings nobody back: that is not an offer.
        expect(fitPeriodOffer(verdicts, [3, 9, NO_VERDICT])).toBeNull();
    });

    it('asks only about the selection: an unselected asset the period leaves out brings no offer', () => {
        expect(fitPeriodOffer(offered([ELIGIBLE_ONE, WARNED]), [3])).toBeNull();
    });

    it('counts a verdict that is not eligible even when it lists no reason', () => {
        const unexplained: AssetEligibilityItem = {asset_id: 13, level: 'warning', quotes_in_period: 40};
        expect(fitPeriodOffer(offered([unexplained]), [13])).toEqual({range: SUGGESTED, recoverable: [13]});
    });
});

describe('dayFormatter', () => {
    afterEach(() => {
        vi.unstubAllEnvs();
    });

    /**
     * One zone on each side of Greenwich, as far out as zones go. Each catches a
     * different way of moving the day, and UTC catches neither — a suite run under
     * `TZ=UTC` would pass both mistakes:
     *
     *  - UTC+14: reading the day as a *local* midnight lands on the previous UTC day;
     *  - UTC−11: formatting its UTC midnight in *local* time shows the previous day.
     *
     * The offsets are `getTimezoneOffset()`'s, which counts west of Greenwich as positive.
     */
    const ZONES = [
        ['Pacific/Kiritimati', -840],
        ['Pacific/Pago_Pago', 660],
        ['UTC', 0],
    ] as const;

    /** A real calendar day as `locale` writes it, from `Intl` itself: what `dayFormatter` must answer for it. */
    const asWritten = (locale: string, year: number, month: number, day: number): string => new Intl.DateTimeFormat(locale, {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'}).format(Date.UTC(year, month - 1, day));

    it('writes a plain day as that same day in every timezone, the day being read as UTC', () => {
        for (const [zone, offset] of ZONES) {
            vi.stubEnv('TZ', zone);
            // Control: the zone really moved. Without it the loop could test one zone three times, and pass.
            expect(new Date(2024, 0, 1).getTimezoneOffset(), zone).toBe(offset);
            for (const locale of ['en', 'it']) {
                expect(dayFormatter(locale)('2024-01-01'), `${locale} in ${zone}`).toBe(asWritten(locale, 2024, 1, 1));
            }
        }
    });

    it("writes the day in the reader's language", () => {
        expect(dayFormatter('it')('2024-01-01')).not.toBe(dayFormatter('en')('2024-01-01'));
    });

    it('echoes back what it cannot read as a day', () => {
        const format = dayFormatter('en');
        for (const raw of ['not a day', '', '2024-13-01', '2024-03-01T10:00:00Z']) {
            expect(format(raw), JSON.stringify(raw)).toBe(raw);
        }
    });

    it('echoes back a day that does not exist, instead of the real day it rolls over to', () => {
        // `Date` reads 30 February as 1 March rather than refusing it, so the
        // invalid-date guard never fires: only the round trip catches it.
        const format = dayFormatter('en');
        for (const impossible of ['2024-02-30', '2023-02-29', '2024-04-31']) {
            expect(format(impossible), impossible).toBe(impossible);
        }
        // Control: the round trip does not refuse a real day at the same edge.
        expect(format('2024-02-29')).toBe(asWritten('en', 2024, 2, 29));
    });
});

describe('reasonText', () => {
    it('knows what every reason of the generated enum quotes, and nothing the enum does not have', () => {
        // Barrier: the list is the enum's, and it is not empty — every loop below would otherwise be about nothing.
        expect(GENERATED_REASONS, 'the generated enum lists no reason the engine is known to give').toContain('no_prices');
        expect(
            GENERATED_REASONS.filter((reason) => !Object.hasOwn(REASON_VALUES, reason)),
            'the engine gives a reason this file has no expectation for: word it in reasonText and in the four catalogues, then say here what its sentence quotes',
        ).toEqual([]);
        expect(
            Object.keys(REASON_VALUES).filter((reason) => !(GENERATED_REASONS as readonly string[]).includes(reason)),
            'an expectation for a reason the generated enum no longer has',
        ).toEqual([]);
        // The fallback cases play a code newer than this client: they are only about that while the enum lacks it.
        expect(GENERATED_REASONS as readonly string[]).not.toContain(NEWER_REASON);
    });

    it('asks for each reason by its full key, once, with the values its sentence quotes', () => {
        for (const [reason, key, options] of REASON_KEYS) {
            const {t, calls} = recordingT();
            expect(reasonText(reason, SUBJECT, VERDICTS, 'CHF', t, formatDay), reason).toBe(marker(key));
            expect(calls, reason).toEqual([[key, options]]);
        }
    });

    it('words an asset never quoted by a sentence of its own, not by the one for a period without quotes', () => {
        // The engine tells the two apart because only `no_prices` is mended by choosing another
        // period; a reader shown the same sentence for both would go looking for that period.
        const {t, calls} = recordingT();
        const neverQuoted = verdict(4, {level: 'ineligible', reasons: ['no_price_history'], first_quote: null, last_quote: null, quotes_in_period: 0});
        expect(reasonText('no_price_history', neverQuoted, VERDICTS, 'CHF', t, formatDay)).toBe(marker('risk.eligibility.reasons.no_price_history'));
        // No values: the sentence quotes nothing, since there is no date and no count to quote.
        expect(calls).toEqual([['risk.eligibility.reasons.no_price_history', undefined]]);
    });

    it('quotes a dash for a date the engine does not have, without asking the formatter', () => {
        for (const missing of [null, undefined]) {
            const format = vi.fn(formatDay);
            const undated = verdict(4, {first_quote: missing, last_quote: missing});
            const late = recordingT();
            const stale = recordingT();
            reasonText('starts_late', undated, VERDICTS, 'CHF', late.t, format);
            reasonText('stale_at_end', undated, VERDICTS, 'CHF', stale.t, format);
            expect(late.calls, String(missing)).toEqual([['risk.eligibility.reasons.starts_late', {values: {date: '—'}}]]);
            expect(stale.calls, String(missing)).toEqual([['risk.eligibility.reasons.stale_at_end', {values: {date: '—', days: 7}}]]);
            expect(format).not.toHaveBeenCalled();
        }
    });

    it('words nothing when the catalogue lacks the sentence, so a raw key never reaches the screen', () => {
        // svelte-i18n answers a key it does not know with the key itself; an empty answer is no sentence either.
        const lacking = [(key: string) => key, () => ''];
        for (const reply of lacking) {
            for (const [reason, key] of REASON_KEYS) {
                const {t, calls} = recordingT(reply);
                expect(reasonText(reason, SUBJECT, VERDICTS, 'CHF', t, formatDay), reason).toBeNull();
                // Control: the sentence was asked for, so the null is a refusal and not a skipped call.
                expect(calls.map(([asked]) => asked)).toEqual([key]);
            }
        }
    });
});

describe('describeEligibility', () => {
    const LEVEL_KEYS = {ineligible: 'risk.eligibility.levels.ineligible', warning: 'risk.eligibility.levels.warning'} as const;

    it('words each code, in the order the engine gave them', () => {
        const entry = verdict(4, {level: 'ineligible', reasons: ['stale_at_end', 'too_few_quotes', 'missing_fx'], quotes_in_period: 12, first_quote: '2023-03-15', last_quote: '2024-11-29'});
        const {t, calls} = recordingT();
        expect(describeEligibility(entry, VERDICTS, 'CHF', t, formatDay)).toEqual({
            level: 'ineligible',
            codes: ['stale_at_end', 'too_few_quotes', 'missing_fx'],
            texts: [marker('risk.eligibility.reasons.stale_at_end'), marker('risk.eligibility.reasons.too_few_quotes'), marker('risk.eligibility.reasons.missing_fx')],
        });
        // Each sentence got its values from the verdicts, the item and the currency,
        // and with every code worded the level's own label was not asked for.
        expect(calls).toEqual([
            ['risk.eligibility.reasons.stale_at_end', {values: {date: 'day:2024-11-29', days: 7}}],
            ['risk.eligibility.reasons.too_few_quotes', {values: {minQuotes: 60, count: 12}}],
            ['risk.eligibility.reasons.missing_fx', {values: {currency: 'CHF'}}],
        ]);
    });

    it("falls back to the level's own label when an ineligible or warning verdict has nothing worded", () => {
        // The label is worded, the reason sentences are not: a catalogue that lacks them.
        const labelsOnly = (key: string): string => (key.startsWith('risk.eligibility.levels.') ? marker(key) : key);
        const unworded = [
            {why: 'no reason at all', reasons: [] as EligibilityReason[], reply: marker},
            {why: 'no reasons field', reasons: undefined, reply: marker},
            {why: 'a sentence the catalogue lacks', reasons: ['no_prices'] as EligibilityReason[], reply: labelsOnly},
            {why: 'a code newer than this client', reasons: [NEWER_REASON] as unknown as EligibilityReason[], reply: marker},
        ];
        for (const level of ['ineligible', 'warning'] as const) {
            for (const {why, reasons, reply} of unworded) {
                const {t} = recordingT(reply);
                expect(describeEligibility(verdict(4, {level, reasons}), VERDICTS, 'CHF', t, formatDay).texts, `${level}: ${why}`).toEqual([marker(LEVEL_KEYS[level])]);
            }
        }
    });

    it("keeps the engine's codes as they came, the ones it cannot word included", () => {
        // One code is worded, so the level's label does not stand in for the other.
        const reasons = ['no_prices', NEWER_REASON] as unknown as EligibilityReason[];
        expect(describeEligibility(verdict(4, {level: 'ineligible', reasons}), VERDICTS, 'CHF', recordingT().t, formatDay)).toEqual({
            level: 'ineligible',
            codes: ['no_prices', NEWER_REASON],
            texts: [marker('risk.eligibility.reasons.no_prices')],
        });
    });

    it('tells a never-quoted asset why it is out, instead of only saying that it is', () => {
        // What the engine sends for an asset with no quote at all (`analysis_eligibility`): no
        // date, no count, and the one reason no period can mend.
        const neverQuoted = verdict(4, {level: 'ineligible', reasons: ['no_price_history'], first_quote: null, last_quote: null, quotes_in_period: 0});
        const {t, calls} = recordingT();
        expect(describeEligibility(neverQuoted, VERDICTS, 'CHF', t, formatDay)).toEqual({
            level: 'ineligible',
            codes: ['no_price_history'],
            texts: [marker('risk.eligibility.reasons.no_price_history')],
        });
        // The reason was worded, so the level's own label was never asked to stand in for it.
        expect(calls.map(([key]) => key)).toEqual(['risk.eligibility.reasons.no_price_history']);
    });

    it('gives an eligible verdict with no reason no text, and asks for none', () => {
        for (const reasons of [[], undefined]) {
            const {t, calls} = recordingT();
            expect(describeEligibility(verdict(4, {reasons}), VERDICTS, 'CHF', t, formatDay), String(reasons)).toEqual({level: 'eligible', codes: [], texts: []});
            expect(calls).toEqual([]);
        }
    });

    it('shows no text rather than a raw key when not even the level has a sentence', () => {
        const {t, calls} = recordingT((key) => key);
        expect(describeEligibility(verdict(4, {level: 'ineligible', reasons: ['no_prices']}), VERDICTS, 'CHF', t, formatDay).texts).toEqual([]);
        // Control: the reason and then the level's label were both asked for, and both refused.
        expect(calls.map(([key]) => key)).toEqual(['risk.eligibility.reasons.no_prices', LEVEL_KEYS.ineligible]);
    });
});

describe('the catalogues word every reason the engine gives', () => {
    /** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
    const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

    function at(catalogue: unknown, key: string): unknown {
        return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    }

    /**
     * One line per generated reason `locale` cannot word the way `reasonText` asks for it: no
     * sentence at all, one that does not compile, or one naming a value `reasonText` never
     * supplies. The last is not a style point. A sentence asked for without values comes back
     * exactly as written — svelte-i18n formats only when it is given values — and one given other
     * values fails to format and comes back raw too: either way the brace reaches the screen.
     */
    function reasonAudit(locale: string, catalogue: unknown): string[] {
        return GENERATED_REASONS.flatMap((reason) => {
            const key = `risk.eligibility.reasons.${reason}`;
            const sentence = at(catalogue, key);
            if (typeof sentence !== 'string' || sentence.trim() === '') return [`${locale}: ${key} is missing`];
            let asked: string[];
            try {
                asked = [...icuArguments(sentence).keys()];
            } catch (error) {
                return [`${locale}: ${key} does not compile (${error instanceof Error ? error.message : String(error)})`];
            }
            const supplied = Object.keys(REASON_VALUES[reason]?.values ?? {});
            const unsupplied = asked.filter((name) => !supplied.includes(name)).sort();
            return unsupplied.length === 0 ? [] : [`${locale}: ${key} asks for {${unsupplied.join(', ')}}, which reasonText never supplies`];
        });
    }

    it('the audit names the locale and key of a missing sentence, and of one asking for a value nobody supplies', () => {
        const worded = Object.fromEntries(GENERATED_REASONS.map((reason) => [reason, `Synthetic sentence for ${reason}`]));
        const synthetic = {risk: {eligibility: {reasons: {...worded, no_prices: undefined, missing_fx: 'No rate to {currency} for {asset}', starts_late: 'First quote on {date}'}}}};
        // `{currency}` and `{date}` are supplied, so only `{asset}` is reported.
        expect(reasonAudit('xx', synthetic)).toEqual(['xx: risk.eligibility.reasons.no_prices is missing', 'xx: risk.eligibility.reasons.missing_fx asks for {asset}, which reasonText never supplies']);
        // A catalogue without the node is every reason missing, never a clean report.
        expect(reasonAudit('xx', {})).toHaveLength(GENERATED_REASONS.length);
    });

    it.each([...SUPPORTED_LOCALES])('%s.json words every reason, asking only for the values reasonText supplies', (locale) => {
        const catalogue = CATALOGUES[locale];
        // Barrier: the walk reaches the eligibility node — the level labels live beside the reasons.
        expect(typeof at(catalogue, 'risk.eligibility.levels.ineligible'), `${locale}.json: the walk never reached risk.eligibility`).toBe('string');
        expect(reasonAudit(locale, catalogue), `${locale}.json: a reason the engine gives would reach the screen as the level's label, a raw key or a brace`).toEqual([]);
    });
});
