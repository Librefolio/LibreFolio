/**
 * @vitest-environment node
 *
 * Branch-exhaustive unit tests for the pure helpers extracted from
 * UnifiedLotsTable.svelte. State derivation, quantity formatting, broker lookup,
 * and the footer aggregations are all pure functions of their input; the HTML
 * cell renderers stay in the component and are not exercised here.
 *
 * Numbers are formatted with an explicit `'en-US'` locale so assertions are
 * deterministic regardless of the machine running them.
 *
 * Two helpers are not pure: `formatLotQuantityMasked` and `formatLotQuantityCell`
 * read the global privacy flag (decision D5′), so their blocks reset it on both
 * sides of each test — the store is module level, and a flag left on by one test
 * would mask the next one's clear-text controls.
 *
 * `sumCompleteOrNull` is the B3b footer total for columns whose cells can be
 * unknown (`null`: no FX rate). `sumNumeric` skips a hole. `sumCompleteOrNull`
 * answers `null` as soon as one cell is unknown, because a total with an unknown
 * part is itself unknown.
 *
 * `weightedAverageCompleteOrNull` applies the same rule to the two weighted-average
 * footers (opening price, open return). A row that takes part in the average (a
 * finite, non-zero weight) and has an unknown value makes the average unknown. A row
 * whose weight does not take part is still skipped, as in `weightedAverage`.
 *
 * Without a locale, the three quantity formatters write in the interface language
 * (M-18 CP2): every figure follows the UI language through one source, `uiLocale()`,
 * where until now an absent locale meant the machine's. That is how
 * `UnifiedLotsTable.svelte`, which passes none, comes to write the reader's notation.
 * An explicit locale still wins. The browser is pinned to en-US before any import —
 * Node's follows the host's ICU locale — so an English UI is written en-US and an
 * Italian one bare `it` (an en-US browser lends no region to Italian). The language is
 * switched as LanguageSelector does and put back to English after each case; Italian
 * digits come from `Intl.NumberFormat` in this runtime, never typed.
 *
 * C-97c-2 (decision D-C97c-1 of the coordinator, 17/10): a quantity on screen loses no
 * digit the database keeps, and a lot quantity keeps ten decimals. `formatLotQuantity`
 * — the table's quantity, its masked and partial cells, and with the cure the custody
 * modal's and the WAC chart's too — cuts it at the sixth today. The contract: up to ten,
 * never in exponent notation. Reds, in the `formatLotQuantity` block: «caps at ten»
 * (which pinned six), 0.1234567891 (today 0.123457) and 0.0000001, a lot of 10 satoshis
 * (today 0: the lot reads empty). Guards there, green today and after: the `—` of an
 * absent quantity, 2.5, and a quantity within six decimals passed `it` explicitly. The
 * M-18 block's quantities stay within six decimals, so they reach no cut before or after
 * the cure and that block reads the notation alone.
 */
import {afterAll, afterEach, beforeEach, describe, it, expect, vi} from 'vitest';

// The browser, pinned before any import: the interface locale takes its region from it.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {currentLanguage} from '$lib/stores/app/language';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {primaryState, secondaryStates, filterStates, formatLotQuantity, formatLotQuantityMasked, formatLotQuantityCell, findBroker, sameIdSet, sumNumeric, sumCompleteOrNull, weightedAverage, weightedAverageCompleteOrNull, ratioOrNull} from './unifiedLotsTableHelpers';

afterAll(() => {
    vi.unstubAllGlobals();
});

describe('primaryState', () => {
    it('prefers PARTIALLY_CLOSED over everything else (first if true)', () => {
        expect(primaryState(['OPEN', 'PARTIALLY_CLOSED', 'CLOSED'])).toBe('PARTIALLY_CLOSED');
    });

    it('returns OPEN when partially-closed is absent (first if false, second true)', () => {
        expect(primaryState(['OPEN', 'CLOSED'])).toBe('OPEN');
    });

    it('returns CLOSED when neither partial nor open is present (third if true)', () => {
        expect(primaryState(['CLOSED', 'DISTRIBUTED'])).toBe('CLOSED');
    });

    it('falls back to DEGRADED when none of the three are present (all ifs false)', () => {
        expect(primaryState(['IN_TRANSIT'])).toBe('DEGRADED');
        expect(primaryState([])).toBe('DEGRADED');
    });
});

describe('secondaryStates', () => {
    it('returns all three in fixed display order when present', () => {
        expect(secondaryStates(['DEGRADED', 'IN_TRANSIT', 'DISTRIBUTED'])).toEqual(['DISTRIBUTED', 'IN_TRANSIT', 'DEGRADED']);
    });

    it('returns only the present subset (mixed filter true/false)', () => {
        expect(secondaryStates(['OPEN', 'IN_TRANSIT'])).toEqual(['IN_TRANSIT']);
    });

    it('returns an empty list when none of the secondary states are present', () => {
        expect(secondaryStates(['OPEN', 'CLOSED'])).toEqual([]);
    });
});

describe('filterStates', () => {
    it('combines primary and secondary states without duplicates', () => {
        expect(filterStates(['OPEN', 'IN_TRANSIT'])).toEqual(['OPEN', 'IN_TRANSIT']);
    });

    it('deduplicates when DEGRADED is both the primary fallback and a secondary state', () => {
        // No PARTIALLY_CLOSED/OPEN/CLOSED ⇒ primary is DEGRADED; DEGRADED also secondary ⇒ Set collapses.
        expect(filterStates(['DEGRADED'])).toEqual(['DEGRADED']);
    });

    it('lists primary first, then secondaries in display order', () => {
        expect(filterStates(['PARTIALLY_CLOSED', 'DISTRIBUTED', 'IN_TRANSIT'])).toEqual(['PARTIALLY_CLOSED', 'DISTRIBUTED', 'IN_TRANSIT']);
    });
});

describe('formatLotQuantity', () => {
    it('renders an em dash for a null value (== null branch)', () => {
        expect(formatLotQuantity(null, 'en-US')).toBe('—');
    });

    it('formats a finite value with up to ten fraction digits (not-null branch)', () => {
        expect(formatLotQuantity(1000.5, 'en-US')).toBe('1,000.5');
    });

    it('caps at ten fraction digits: the tenth is shown, the eleventh is not (C-97c-2)', () => {
        // Why: the eleventh decimal, 2, reads the same whether the cap rounds or cuts; the case pins where the cap is.
        expect(formatLotQuantity(0.12345678912, 'en-US'), 'ten decimals, no more (today cut at the sixth: 0.123457)').toBe('0.1234567891');
    });

    it('without a locale, the interface locale: an English UI on an en-US browser writes en-US (M-18)', () => {
        // M-18 rewrite: this case accepted the machine locale and only looked for the digits. The
        // absent locale is the interface's now; the Italian side is in the M-18 block below.
        expect(formatLotQuantity(1234.5)).toBe('1,234.5');
    });

    // C-97c-2 — a lot quantity keeps every decimal of its column (D-C97c-1): red until the cure.
    it('0.1234567891 reads 0.1234567891: the ten decimals of its column, not six (C-97c-2)', () => {
        expect(formatLotQuantity(0.1234567891, 'en-US'), 'ten decimals (today cut at the sixth: 0.123457)').toBe('0.1234567891');
    });

    it('0.0000001, a lot of 10 satoshis, reads 0.0000001, not 0 (C-97c-2)', () => {
        expect(formatLotQuantity(0.0000001, 'en-US'), 'its seventh decimal (today 0: the lot reads empty)').toBe('0.0000001');
    });

    // C-97c-2 guards: green before and after the cure. The `—` of an absent quantity is the first case of this block.
    it('guard: 2.5 still reads 2.5 (C-97c-2)', () => {
        expect(formatLotQuantity(2.5, 'en-US')).toBe('2.5');
    });

    it('guard: an explicit it locale writes 12345.123456 in Italian notation, its six decimals whole (C-97c-2)', () => {
        // Why six decimals: no cut is reached before the cure (six) nor after (ten), so the case reads the notation alone.
        const atTen = (locale: string) => new Intl.NumberFormat(locale, {minimumFractionDigits: 0, maximumFractionDigits: 10}).format(12345.123456);
        const italian = atTen('it');
        expect(italian, 'control: Italian writes the quantity otherwise than English').not.toBe(atTen('en-US'));
        expect(italian.replace(/\D/g, ''), 'control: and keeps its digits').toBe('12345123456');

        expect(formatLotQuantity(12345.123456, 'it')).toBe(italian);
    });
});

describe('formatLotQuantityMasked', () => {
    // A lot quantity sits next to a price, and quantity × price rebuilds what the user owns: masked under privacy (D5′).
    beforeEach(() => setPrivacyEnabled(false));
    afterEach(() => setPrivacyEnabled(false));

    it('formats exactly like formatLotQuantity while privacy is off', () => {
        expect(formatLotQuantityMasked(1000.5, 'en-US')).toBe(formatLotQuantity(1000.5, 'en-US'));
        expect(formatLotQuantityMasked(-2.5, 'en-US')).toBe('-2.5');
    });

    it('masks a present quantity under privacy, keeping the sign of a short one', () => {
        setPrivacyEnabled(true);

        expect(formatLotQuantityMasked(1000.5, 'en-US')).toBe('•••');
        expect(formatLotQuantityMasked(-2.5, 'en-US')).toBe('-•••');
    });

    it('keeps the em dash for an absent quantity in both states', () => {
        expect(formatLotQuantityMasked(null, 'en-US')).toBe('—');

        setPrivacyEnabled(true);
        // Masking an absence would claim a quantity the lot does not have.
        expect(formatLotQuantityMasked(null, 'en-US')).toBe('—');
        // Positive control: in this exact state a present quantity is masked, so
        // the em dash above is the absence check and not a flag that stayed off.
        expect(formatLotQuantityMasked(6, 'en-US')).toBe('•••');
    });
});

describe('formatLotQuantityCell', () => {
    // A partially closed lot keeps its reading key under privacy as the open share (Q8); percentages stay visible (D6).
    beforeEach(() => setPrivacyEnabled(false));
    afterEach(() => setPrivacyEnabled(false));

    it('shows open / original for a partially closed lot while privacy is off', () => {
        expect(formatLotQuantityCell(6, 10, true, 'en-US')).toBe('6 / 10');
    });

    it('shows the open share instead of the two quantities under privacy', () => {
        setPrivacyEnabled(true);

        expect(formatLotQuantityCell(6, 10, true, 'en-US')).toBe('••• (60%)');
    });

    it('falls back to the placeholder alone when there is no share to compute', () => {
        setPrivacyEnabled(true);

        expect(formatLotQuantityCell(6, 0, true, 'en-US')).toBe('•••');
        expect(formatLotQuantityCell(6, null, true, 'en-US')).toBe('•••');
        expect(formatLotQuantityCell(null, 10, true, 'en-US')).toBe('•••');
        // Positive control: same flag, and a lot with an original to divide by shows its share.
        expect(formatLotQuantityCell(6, 10, true, 'en-US')).toBe('••• (60%)');
    });

    it('renders a lot that is not partial through formatLotQuantityMasked', () => {
        expect(formatLotQuantityCell(6, 10, false, 'en-US')).toBe('6');
        expect(formatLotQuantityCell(null, 10, false, 'en-US')).toBe('—');

        setPrivacyEnabled(true);
        expect(formatLotQuantityCell(6, 10, false, 'en-US')).toBe('•••');
        expect(formatLotQuantityCell(-2.5, 10, false, 'en-US')).toBe('-•••');
        expect(formatLotQuantityCell(null, 10, false, 'en-US')).toBe('—');
    });

    it('never shows a quantity through the share: the only digits left are the percentage', () => {
        // Control: in the clear the partial cell carries both quantities, so the
        // absence checks below are able to see them.
        expect(formatLotQuantityCell(1234.5, 5000, true, 'en-US')).toBe('1,234.5 / 5,000');

        setPrivacyEnabled(true);
        const masked = formatLotQuantityCell(1234.5, 5000, true, 'en-US');
        expect(masked).toBe('••• (25%)');
        // Exactly one digit group, and it is the share (24.69%, rounded), not a quantity.
        expect(masked.match(/\d+/g)).toEqual([String(Math.round((1234.5 / 5000) * 100))]);
        expect(masked).not.toContain('1,234.5');
        expect(masked).not.toContain('5,000');

        const third = formatLotQuantityCell(1, 3, true, 'en-US');
        expect(third).toBe('••• (33%)');
        expect(third.match(/\d+/g)).toEqual(['33']);
    });
});

describe('formatLotQuantity / formatLotQuantityMasked / formatLotQuantityCell — without a locale, the interface language (M-18)', () => {
    /** A quantity as Intl writes it in `locale`, with the formatter's options: up to ten fraction digits (C-97c-2). */
    function intlQuantity(locale: string, value: number): string {
        return new Intl.NumberFormat(locale, {minimumFractionDigits: 0, maximumFractionDigits: 10}).format(value);
    }

    /** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
    async function uiLanguage(lang: 'en' | 'it'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
    }

    /** The UI in Italian on the pinned en-US browser: the interface locale is bare `it`. */
    async function italianUi(): Promise<void> {
        await uiLanguage('it');
        expect(uiLocale(), 'control: an Italian UI on an en-US browser is written bare it').toBe('it');
    }

    // The quantity is masked under privacy: every case here reads it in the clear.
    beforeEach(() => setPrivacyEnabled(false));
    afterEach(async () => {
        setPrivacyEnabled(false);
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it('formatLotQuantity: an Italian UI reads Italian digits without passing a locale; an explicit locale still wins', async () => {
        // 1234.5 is grouped in en-US only (Italian groups from five digits), 12345.678 in both, and
        // 0.123456 shows its six fraction digits. None reaches a cut — the sixth decimal before C-97c-2,
        // the tenth after — so this case reads the notation alone: how many decimals a quantity keeps
        // is the subject of the C-97c-2 cases of the `formatLotQuantity` block.
        const quantities = [1234.5, 12345.678, 0.123456];
        const italian = quantities.map((value) => intlQuantity('it', value));
        const american = quantities.map((value) => intlQuantity('en-US', value));
        italian.forEach((text, index) => expect(text, `control: Italian writes ${quantities[index]} otherwise than en-US`).not.toBe(american[index]));

        await italianUi();
        expect(
            quantities.map((value) => formatLotQuantity(value, 'en-US')),
            'an explicit locale still wins',
        ).toEqual(american);

        expect(
            quantities.map((value) => formatLotQuantity(value)),
            'without a locale, an Italian UI must read Italian quantities',
        ).toEqual(italian);
    });

    it('formatLotQuantityMasked: in the clear, the same Italian digits, the sign of a short quantity kept', async () => {
        const quantities = [1234.5, -2.5];

        await italianUi();
        expect(
            quantities.map((value) => formatLotQuantityMasked(value, 'en-US')),
            'an explicit locale still wins',
        ).toEqual(quantities.map((value) => intlQuantity('en-US', value)));

        expect(
            quantities.map((value) => formatLotQuantityMasked(value)),
            'without a locale, an Italian UI must read Italian quantities',
        ).toEqual(quantities.map((value) => intlQuantity('it', value)));
    });

    it('formatLotQuantityCell: open / original for a partially closed lot, the open quantity for a whole one — in Italian digits', async () => {
        const cells = (locale?: string) => ({partial: formatLotQuantityCell(1234.5, 5000, true, locale), whole: formatLotQuantityCell(1234.5, 5000, false, locale)});

        await italianUi();
        expect(cells('en-US'), 'an explicit locale still wins').toEqual({partial: '1,234.5 / 5,000', whole: '1,234.5'});

        expect(cells(), 'without a locale, an Italian UI must read Italian quantities').toEqual({
            partial: `${intlQuantity('it', 1234.5)} / ${intlQuantity('it', 5000)}`,
            whole: intlQuantity('it', 1234.5),
        });
    });
});

describe('findBroker', () => {
    const brokers: BrokerLike[] = [
        {id: 1, name: 'Fineco'},
        {id: 2, name: 'Directa'},
    ];

    it('returns null for a null id (== null branch)', () => {
        expect(findBroker(null, brokers)).toBeNull();
    });

    it('returns null for an undefined id (== null branch)', () => {
        expect(findBroker(undefined, brokers)).toBeNull();
    });

    it('returns the matching broker (?? left branch)', () => {
        expect(findBroker(2, brokers)).toEqual({id: 2, name: 'Directa'});
    });

    it('returns null on a miss — no synthetic placeholder, unlike the modal (?? right branch)', () => {
        expect(findBroker(99, brokers)).toBeNull();
    });
});

describe('sameIdSet', () => {
    it('returns false when the lengths differ (length guard)', () => {
        expect(sameIdSet(['a', 'b'], ['a'])).toBe(false);
    });

    it('returns true for equal sets regardless of order (every true)', () => {
        expect(sameIdSet(['a', 'b', 'c'], ['c', 'a', 'b'])).toBe(true);
    });

    it('returns false for same length but differing members (every false)', () => {
        expect(sameIdSet(['a', 'b'], ['a', 'x'])).toBe(false);
    });

    it('treats two empty lists as equal', () => {
        expect(sameIdSet([], [])).toBe(true);
    });
});

interface Row {
    v: number | null;
    w: number | null;
}

describe('sumNumeric', () => {
    it('returns null for no rows (count 0 branch)', () => {
        expect(sumNumeric<Row>([], (r) => r.v)).toBeNull();
    });

    it('sums all finite values (count > 0 branch)', () => {
        expect(
            sumNumeric<Row>(
                [
                    {v: 1, w: 0},
                    {v: 2, w: 0},
                    {v: 3, w: 0},
                ],
                (r) => r.v,
            ),
        ).toBe(6);
    });

    it('skips null cells (value == null branch)', () => {
        expect(
            sumNumeric<Row>(
                [
                    {v: 5, w: 0},
                    {v: null, w: 0},
                    {v: 5, w: 0},
                ],
                (r) => r.v,
            ),
        ).toBe(10);
    });

    it('skips non-finite cells (NaN / Infinity → !isFinite branch)', () => {
        expect(
            sumNumeric<Row>(
                [
                    {v: NaN, w: 0},
                    {v: Infinity, w: 0},
                    {v: 7, w: 0},
                ],
                (r) => r.v,
            ),
        ).toBe(7);
    });

    it('returns null when every cell is skipped', () => {
        expect(
            sumNumeric<Row>(
                [
                    {v: null, w: 0},
                    {v: NaN, w: 0},
                ],
                (r) => r.v,
            ),
        ).toBeNull();
    });
});

describe('sumCompleteOrNull', () => {
    // A footer total over cells that can be unknown (no FX rate): with an unknown part the total is unknown, shown as «—».
    const column = (...values: Array<number | null>): Row[] => values.map((v) => ({v, w: 0}));

    it('sums the column when every value is known', () => {
        expect(sumCompleteOrNull(column(1, 2, 3), (r) => r.v)).toBe(6);
        expect(sumCompleteOrNull(column(5, -2.5), (r) => r.v)).toBe(2.5);
    });

    it('treats zero as a known value', () => {
        expect(sumCompleteOrNull(column(0, 0), (r) => r.v)).toBe(0);
        expect(sumCompleteOrNull(column(-0, 4), (r) => r.v)).toBe(4);
    });

    it('is null as soon as one value is unknown, wherever it sits', () => {
        // Control: the same column without the hole has a total.
        expect(sumCompleteOrNull(column(5, 5), (r) => r.v)).toBe(10);

        expect(sumCompleteOrNull(column(null, 5, 5), (r) => r.v)).toBeNull();
        expect(sumCompleteOrNull(column(5, null, 5), (r) => r.v)).toBeNull();
        expect(sumCompleteOrNull(column(5, 5, null), (r) => r.v)).toBeNull();
        expect(sumCompleteOrNull(column(null, null), (r) => r.v)).toBeNull();
    });

    it('is null when a value is not finite (NaN / ±Infinity)', () => {
        // Control: a finite column.
        expect(sumCompleteOrNull(column(7, 1), (r) => r.v)).toBe(8);

        expect(sumCompleteOrNull(column(7, NaN), (r) => r.v)).toBeNull();
        expect(sumCompleteOrNull(column(Infinity, 7), (r) => r.v)).toBeNull();
        expect(sumCompleteOrNull(column(7, -Infinity), (r) => r.v)).toBeNull();
    });

    it('is null for no rows: there is no total to show', () => {
        expect(sumCompleteOrNull<Row>([], (r) => r.v)).toBeNull();
    });

    it('answers null on the column where sumNumeric would show the known part as the total', () => {
        const rows = column(5, null, 5);
        expect(sumNumeric(rows, (r) => r.v)).toBe(10);
        expect(sumCompleteOrNull(rows, (r) => r.v)).toBeNull();
    });
});

describe('weightedAverage', () => {
    it('weights values by the second column', () => {
        // (10*1 + 20*3) / (1+3) = 70/4 = 17.5
        expect(
            weightedAverage<Row>(
                [
                    {v: 10, w: 1},
                    {v: 20, w: 3},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(17.5);
    });

    it('skips a row whose value is null', () => {
        expect(
            weightedAverage<Row>(
                [
                    {v: null, w: 5},
                    {v: 8, w: 2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(8);
    });

    it('skips a row whose weight is null', () => {
        expect(
            weightedAverage<Row>(
                [
                    {v: 8, w: null},
                    {v: 4, w: 2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(4);
    });

    it('skips a row whose value is non-finite', () => {
        expect(
            weightedAverage<Row>(
                [
                    {v: Infinity, w: 5},
                    {v: 6, w: 2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(6);
    });

    it('skips a row whose weight is non-finite', () => {
        expect(
            weightedAverage<Row>(
                [
                    {v: 6, w: NaN},
                    {v: 9, w: 2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(9);
    });

    it('skips a row whose weight is exactly zero (weight === 0 branch)', () => {
        expect(
            weightedAverage<Row>(
                [
                    {v: 100, w: 0},
                    {v: 9, w: 2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(9);
    });

    it('uses the absolute value of a negative weight', () => {
        // (10*|−2| + 20*|−2|)/(2+2) = 60/4 = 15
        expect(
            weightedAverage<Row>(
                [
                    {v: 10, w: -2},
                    {v: 20, w: -2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(15);
    });

    it('returns null when the total weight is zero (denominator > 0 false branch)', () => {
        expect(
            weightedAverage<Row>(
                [{v: 100, w: 0}],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBeNull();
        expect(
            weightedAverage<Row>(
                [],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBeNull();
    });
});

describe('weightedAverageCompleteOrNull', () => {
    // The opening-price and open-return footers: an average that silently drops a weighted row would read as complete.
    const weighted = (...cells: Array<[number | null, number | null]>): Row[] => cells.map(([v, w]) => ({v, w}));
    const average = (rows: readonly Row[]): number | null =>
        weightedAverageCompleteOrNull(
            rows,
            (r) => r.v,
            (r) => r.w,
        );
    const today = (rows: readonly Row[]): number | null =>
        weightedAverage(
            rows,
            (r) => r.v,
            (r) => r.w,
        );

    it('averages by absolute weight like weightedAverage, a negative weight included', () => {
        // Control: today's helper on the mixed-sign column. Signed weights would give (−10 + 90) / 2 = 40.
        expect(today(weighted([10, -1], [30, 3]))).toBe(25);

        expect(average(weighted([10, 1], [20, 3]))).toBe(17.5); // (10·1 + 20·3) / 4
        expect(average(weighted([10, -2], [20, -2]))).toBe(15); // (10·2 + 20·2) / 4
        expect(average(weighted([10, -1], [30, 3]))).toBe(25); // (10·1 + 30·3) / 4
    });

    it('skips a known row whose weight does not take part (zero, null, non-finite), like weightedAverage', () => {
        const column = weighted([10, 1], [100, 0], [50, null], [70, NaN], [90, Infinity], [20, 3]);
        // Control: today's helper averages the two weighted rows only.
        expect(today(column)).toBe(17.5);

        expect(average(column)).toBe(17.5);
    });

    it('is null as soon as a row with a usable weight has an unknown value, wherever it sits', () => {
        // Control: today's helper drops the weighted row and answers with the other one, as if complete.
        expect(today(weighted([null, 5], [8, 2]))).toBe(8);

        expect(average(weighted([null, 5], [8, 2]))).toBeNull();
        expect(average(weighted([8, 2], [null, 5]))).toBeNull();
        expect(average(weighted([8, 2], [null, 5], [4, 2]))).toBeNull();
        // A negative weight is a usable weight too: it counts by its absolute value.
        expect(average(weighted([null, -5], [8, 2]))).toBeNull();
    });

    it('still skips an unknown value on a row whose weight does not take part, so the result stays known', () => {
        expect(average(weighted([null, 0], [9, 2]))).toBe(9);
        expect(average(weighted([null, -0], [9, 2]))).toBe(9);
        expect(average(weighted([null, null], [9, 2]))).toBe(9);
        expect(average(weighted([null, NaN], [9, 2]))).toBe(9);
        expect(average(weighted([null, Infinity], [9, 2]))).toBe(9);
        expect(average(weighted([NaN, 0], [9, 2]))).toBe(9);
        // Between weighted rows the skipped ones move nothing: same 17.5 as the two weighted rows alone.
        expect(average(weighted([10, 1], [null, 0], [null, null], [NaN, NaN], [20, 3]))).toBe(17.5);
    });

    it('is null when a row with a usable weight has a non-finite value (NaN / ±Infinity)', () => {
        // Control: today's helper drops the row and answers with the other one.
        expect(today(weighted([Infinity, 5], [6, 2]))).toBe(6);

        expect(average(weighted([Infinity, 5], [6, 2]))).toBeNull();
        expect(average(weighted([NaN, 1], [6, 2]))).toBeNull();
        expect(average(weighted([6, 2], [-Infinity, 1]))).toBeNull();
    });

    it('is null when no row has a usable weight, as weightedAverage is', () => {
        // Control: today's helper agrees.
        expect(today(weighted([100, 0]))).toBeNull();

        expect(average(weighted([100, 0]))).toBeNull();
        expect(average(weighted([100, null], [50, NaN]))).toBeNull();
        expect(average(weighted([null, 0]))).toBeNull();
    });

    it('is null for no rows', () => {
        expect(average([])).toBeNull();
    });
});

describe('ratioOrNull', () => {
    it('divides when both are present and the denominator is non-zero', () => {
        expect(ratioOrNull(30, 120)).toBe(0.25);
    });

    it('returns null when the numerator is null', () => {
        expect(ratioOrNull(null, 120)).toBeNull();
    });

    it('returns null when the denominator is null', () => {
        expect(ratioOrNull(30, null)).toBeNull();
    });

    it('returns null when the denominator is zero (division guard)', () => {
        expect(ratioOrNull(30, 0)).toBeNull();
    });

    it('accepts a zero numerator as a real ratio', () => {
        expect(ratioOrNull(0, 120)).toBe(0);
    });
});
