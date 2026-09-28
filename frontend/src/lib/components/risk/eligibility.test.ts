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
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

import {ELIGIBILITY_BATCH, EMPTY_VERDICTS, dayFormatter, describeEligibility, eligibilityBatches, isSelectable, mergeEligibilityAnswers, reasonText, type AssetEligibilityItem, type EligibilityReason, type EligibilityVerdicts} from './eligibility';

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

/** Every reason the generated enum knows, with its full key and the values its sentence quotes for `SUBJECT`. */
const REASON_KEYS: ReadonlyArray<readonly [EligibilityReason, string, TranslateOptions | undefined]> = [
    ['no_prices', 'risk.eligibility.reasons.no_prices', undefined],
    ['too_few_quotes', 'risk.eligibility.reasons.too_few_quotes', {values: {minQuotes: 60, count: 12}}],
    ['missing_fx', 'risk.eligibility.reasons.missing_fx', {values: {currency: 'CHF'}}],
    ['starts_late', 'risk.eligibility.reasons.starts_late', {values: {date: 'day:2023-03-15'}}],
    ['stale_at_end', 'risk.eligibility.reasons.stale_at_end', {values: {date: 'day:2024-11-29', days: 7}}],
];

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
    it('asks for each reason by its full key, once, with the values its sentence quotes', () => {
        for (const [reason, key, options] of REASON_KEYS) {
            const {t, calls} = recordingT();
            expect(reasonText(reason, SUBJECT, VERDICTS, 'CHF', t, formatDay), reason).toBe(marker(key));
            expect(calls, reason).toEqual([[key, options]]);
        }
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
            {why: 'a code newer than this client', reasons: ['halted_trading'] as unknown as EligibilityReason[], reply: marker},
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
        const reasons = ['no_prices', 'halted_trading'] as unknown as EligibilityReason[];
        expect(describeEligibility(verdict(4, {level: 'ineligible', reasons}), VERDICTS, 'CHF', recordingT().t, formatDay)).toEqual({
            level: 'ineligible',
            codes: ['no_prices', 'halted_trading'],
            texts: [marker('risk.eligibility.reasons.no_prices')],
        });
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
