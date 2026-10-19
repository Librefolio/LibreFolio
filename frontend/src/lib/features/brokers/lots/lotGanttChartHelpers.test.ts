/**
 * Unit tests for lotGanttChartHelpers — the pure logic lifted out of
 * LotGanttChart.svelte. Every branch is exercised from plain inputs (no ECharts,
 * no canvas, no `renderItem` closure), and the assertions pin exact values so a
 * regression in the guard order or the arithmetic fails loudly.
 *
 * `parseDateToUtcMs` is deliberately zone-independent, so its expectations are
 * exact `Date.UTC(...)` values that hold under any TZ — unlike the component's
 * `formatDate*` label formatters, which are left in place because they carry a
 * timezone defect reported separately.
 *
 * Without a locale, `formatQuantity` writes in the interface language (M-18 CP2):
 * every figure follows the UI language through one source, `uiLocale()`, where
 * until now an absent locale meant the machine's. An explicit locale still wins.
 * The browser is pinned to en-US before any import — Node's follows the host's ICU
 * locale — so an English UI is written en-US and an Italian one bare `it` (an en-US
 * browser lends no region to Italian). The language is switched as
 * LanguageSelector does and put back to English after each case; Italian digits
 * come from `Intl.NumberFormat` in this runtime, never typed.
 *
 * C-97c-2 (decision D-C97c-1 of the coordinator, 17/10): a quantity on screen loses no
 * digit the database keeps, and a lot quantity keeps ten decimals. The Gantt's
 * `formatQuantity` cuts it at the sixth today, and `quantityPluralCount` counts on the
 * same six digits. The contract: ten for both, so the noun of the tooltip still follows
 * the digits it shows. Reds: «caps at ten» (which pinned six) and 0.1234567891 (today
 * 0.123457) in the `formatQuantity` block; 1.0000001, shown «1.0000001» at ten, counted
 * 1.5 and worded in the plural (today shown «1» at six, counted 1, singular) in the O-16
 * blocks. Guards, green today and after: the O-16 cases that pinned the cut at six read
 * 1.00000000001 now, whose fraction lies past the tenth decimal (shown «1», counted 1,
 * singular, before and after), and the count follows the digits `formatQuantity` shows,
 * whatever their number. The M-18 block's quantities stay within six decimals, so they
 * reach no cut before or after the cure and that block reads the notation alone.
 *
 * @vitest-environment node
 */

import {afterAll, afterEach, describe, it, expect, vi} from 'vitest';

// The browser, pinned before any import: the interface locale takes its region from it.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {get} from 'svelte/store';
import {waitLocale} from 'svelte-i18n';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {getBrokerColor} from '$lib/utils/broker/brokerColors';
import {
    THICKNESS_MIN,
    THICKNESS_MAX,
    BRANCH_THICKNESS_MAX,
    safeUnknownString,
    parseUnknownNumber,
    parseDateToUtcMs,
    firstPresentUnknown,
    formatQuantity,
    estimateTextWidthPx,
    signedColorField,
    segmentBaseColor,
    segmentOpacity,
    thicknessForQuantity,
    segmentIntersectsRange,
    transferPairId,
    isTransferFragment,
    laneKeyForFragmentId,
    laneKeyForSegment,
    branchDepthForLaneKey,
    laneSortKey,
    eventMarkerKind,
    eventMarkerSymbol,
    isSplitTransition,
    inferredTransitionKind,
    applySharedZoomWindow,
    type EventMarkerKind,
} from './lotGanttChartHelpers';
// O-16: the module itself too, so the helpers still to come are read as properties: a named import of an export that
// does not exist yet would fail every case of this file, not only theirs.
import * as ganttHelpers from './lotGanttChartHelpers';

afterAll(() => {
    vi.unstubAllGlobals();
});

describe('safeUnknownString', () => {
    it('unwraps a single-element array', () => {
        expect(safeUnknownString(['MARKET_PRICE'])).toBe('MARKET_PRICE');
    });

    it('recurses through nested arrays and stringifies the finite number inside', () => {
        expect(safeUnknownString([[42]])).toBe('42');
    });

    it('passes a plain string through', () => {
        expect(safeUnknownString('hello')).toBe('hello');
    });

    it('stringifies a finite number', () => {
        expect(safeUnknownString(3.5)).toBe('3.5');
    });

    it('rejects a non-finite number', () => {
        expect(safeUnknownString(Number.NaN)).toBeNull();
        expect(safeUnknownString(Number.POSITIVE_INFINITY)).toBeNull();
    });

    it('rejects null, objects and empty arrays', () => {
        expect(safeUnknownString(null)).toBeNull();
        expect(safeUnknownString({})).toBeNull();
        expect(safeUnknownString([])).toBeNull(); // value[0] is undefined → recurse → null
        expect(safeUnknownString([null])).toBeNull();
    });
});

describe('parseUnknownNumber', () => {
    it('parses a numeric string', () => {
        expect(parseUnknownNumber('3.5')).toBe(3.5);
    });

    it('parses through the scalar-or-array shape', () => {
        expect(parseUnknownNumber(['12'])).toBe(12);
    });

    it('parses a leading number out of a mixed string', () => {
        expect(parseUnknownNumber('12px')).toBe(12);
    });

    it('returns null when the field is absent', () => {
        expect(parseUnknownNumber(null)).toBeNull();
        expect(parseUnknownNumber([])).toBeNull();
    });

    it('returns null when the string has no numeric prefix', () => {
        expect(parseUnknownNumber('abc')).toBeNull();
    });
});

describe('parseDateToUtcMs', () => {
    it('reads a date-only string field-by-field (zone-independent)', () => {
        expect(parseDateToUtcMs('2024-03-15')).toBe(Date.UTC(2024, 2, 15));
    });

    it('normalises a full timestamp to the UTC midnight of its UTC date', () => {
        expect(parseDateToUtcMs('2024-03-15T12:00:00Z')).toBe(Date.UTC(2024, 2, 15));
    });

    it('uses the UTC calendar day after an offset crosses midnight', () => {
        // 2024-03-15T23:30-05:00 == 2024-03-16T04:30Z → UTC day is the 16th.
        expect(parseDateToUtcMs('2024-03-15T23:30:00-05:00')).toBe(Date.UTC(2024, 2, 16));
    });

    it('returns null for an unparseable value', () => {
        expect(parseDateToUtcMs('not a date')).toBeNull();
    });
});

describe('firstPresentUnknown', () => {
    it('skips a null scalar and returns the next present array element', () => {
        expect(firstPresentUnknown(null, ['x'])).toBe('x');
    });

    it('skips an array whose first element is null', () => {
        expect(firstPresentUnknown([null], 'y')).toBe('y');
    });

    it('skips an empty array', () => {
        expect(firstPresentUnknown([], 'z')).toBe('z');
    });

    it('returns a present scalar as-is, including falsy-but-present 0', () => {
        expect(firstPresentUnknown(0)).toBe(0);
    });

    it('returns the first array element when present', () => {
        expect(firstPresentUnknown(['a', 'b'])).toBe('a');
    });

    it('returns undefined when nothing qualifies', () => {
        expect(firstPresentUnknown(undefined, null, [null])).toBeUndefined();
    });
});

describe('formatQuantity', () => {
    it('groups thousands and drops trailing zeros (explicit locale)', () => {
        expect(formatQuantity(1234.5, 'en-US')).toBe('1,234.5');
        expect(formatQuantity(1000, 'en-US')).toBe('1,000');
    });

    it('caps at ten fraction digits: the tenth is shown, the eleventh is not (C-97c-2)', () => {
        // Why: the eleventh decimal, 2, reads the same whether the cap rounds or cuts; the case pins where the cap is.
        expect(formatQuantity(1.12345678912, 'en-US'), 'ten decimals, no more (today cut at the sixth: 1.123457)').toBe('1.1234567891');
    });

    // C-97c-2 — a lot quantity keeps every decimal of its column (D-C97c-1): red until the cure.
    it('0.1234567891 reads 0.1234567891: the ten decimals of its column, not six (C-97c-2)', () => {
        expect(formatQuantity(0.1234567891, 'en-US'), 'ten decimals (today cut at the sixth: 0.123457)').toBe('0.1234567891');
    });

    it('is callable without an explicit locale (default arg path)', () => {
        expect(typeof formatQuantity(5)).toBe('string');
    });
});

describe('formatQuantity — without a locale, the interface language (M-18)', () => {
    /** A quantity as Intl writes it in `locale`, with the formatter's options: up to ten fraction digits (C-97c-2). */
    function intlQuantity(locale: string, value: number): string {
        return new Intl.NumberFormat(locale, {minimumFractionDigits: 0, maximumFractionDigits: 10}).format(value);
    }

    /** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
    async function uiLanguage(lang: 'en' | 'it'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it('an Italian UI reads Italian digits without passing a locale; an explicit locale still wins', async () => {
        // 1234.5 is grouped in en-US only (Italian groups from five digits), 12345.678 in both, and
        // 1.123456 shows its six fraction digits. None reaches a cut — the sixth decimal before C-97c-2,
        // the tenth after — so this case reads the notation alone: how many decimals a quantity keeps
        // is the subject of the C-97c-2 cases of the `formatQuantity` block.
        const quantities = [1234.5, 12345.678, 1.123456];
        const italian = quantities.map((value) => intlQuantity('it', value));
        const american = quantities.map((value) => intlQuantity('en-US', value));
        italian.forEach((text, index) => expect(text, `control: Italian writes ${quantities[index]} otherwise than en-US`).not.toBe(american[index]));
        expect(
            quantities.map((value) => formatQuantity(value)),
            'control: an English UI on an en-US browser writes en-US',
        ).toEqual(american);

        await uiLanguage('it');
        expect(uiLocale(), 'control: an Italian UI on an en-US browser is written bare it').toBe('it');
        expect(
            quantities.map((value) => formatQuantity(value, 'en-US')),
            'an explicit locale still wins',
        ).toEqual(american);

        expect(
            quantities.map((value) => formatQuantity(value)),
            'without a locale, an Italian UI must read Italian quantities',
        ).toEqual(italian);
    });
});

// ---------------------------------------------------------------------------
// O-16 — the tooltip's quantity line, in the plural its digits read
// ---------------------------------------------------------------------------
//
// The Gantt tooltip glued a fixed word to the formatted quantity (`LotGanttChart.svelte`, `buildTooltip`): «1 shares»,
// «0,5 shares». After the fix a pure helper, `lotQuantityLine(t, input)`, builds the line from two ICU plural keys,
// `brokers.lots.tooltip.quantityClosed` (count 0) and `brokers.lots.tooltip.quantityOpen`, and takes the open line's
// `count` from the digits shown, never from the double (i18n rule 6): `quantityPluralCount(value, locale?)`, beside
// `formatQuantity` and with its options, is the integer part shown plus 0.5 when a fraction is shown, and NaN for a value
// that is not finite. A masked quantity counts NaN, which every locale reads as `other`: the noun must not reveal a
// hidden 1. Both helpers are read off the module namespace (see the imports). The translated lines are asserted as
// text on purpose: the translation of a plural is the subject here.

describe('quantityPluralCount — the plural count of a quantity as formatQuantity shows it (O-16)', () => {
    /** The helper, after the precondition that it exists. */
    function pluralCount(value: number, locale: string): number {
        expect(typeof ganttHelpers.quantityPluralCount, 'lotGanttChartHelpers exports quantityPluralCount').toBe('function');
        return ganttHelpers.quantityPluralCount(value, locale);
    }

    it.each([
        {value: 1, locale: 'en', count: 1},
        {value: 3, locale: 'en', count: 3},
        {value: 0.5, locale: 'fr', count: 0.5},
        {value: 1.5, locale: 'it', count: 1.5},
    ])('$value in $locale counts $count: the integer part shown, plus one half when a fraction is shown', ({value, locale, count}) => {
        expect(pluralCount(value, locale)).toBe(count);
    });

    it('counts 1.00000000001 as 1 in en: ten fraction digits round its fraction away, so it is shown «1»', () => {
        // C-97c-2: this case read 1.0000001, whose fraction six digits rounded away. At ten that fraction is shown (the
        // C-97c-2 case below); the fraction past the cut is now an eleventh decimal's, shown «1» before and after the cure.
        expect(formatQuantity(1.00000000001, 'en'), 'control: the digits shown').toBe('1');
        expect(pluralCount(1.00000000001, 'en')).toBe(1);
    });

    it('counts 1.0000001 as 1.5 in en: at ten fraction digits its seventh is shown, «1.0000001», so the count keeps a fraction (C-97c-2)', () => {
        // Why: the case where the seventh to tenth decimals decide the plural. The control is Intl's, not formatQuantity's,
        // so the case is red for the count alone; that the count follows formatQuantity is the C-97c-2 guard below.
        expect(new Intl.NumberFormat('en', {minimumFractionDigits: 0, maximumFractionDigits: 10}).format(1.0000001), 'control: at ten fraction digits, 1.0000001 shows its seventh').toBe('1.0000001');
        expect(pluralCount(1.0000001, 'en'), 'the fraction shown is counted: 1.5, plural (today 1, singular: counted on six digits, «1»)').toBe(1.5);
    });

    it('counts 1.0004 as 1.5 in en: its fourth fraction digit is shown, so the count keeps a fraction (beyond the cases of the brief)', () => {
        // Why: the case that tells the digits shown from the double. Intl.PluralRules rounds what it is handed to three
        // fraction digits, so the raw 1.0004 would be read as one, next to a figure that shows a fraction.
        expect(formatQuantity(1.0004, 'en'), 'control: the digits shown').toBe('1.0004');
        expect(new Intl.PluralRules('en').select(1.0004), 'control: the double itself is read as one').toBe('one');
        expect(pluralCount(1.0004, 'en')).toBe(1.5);
    });

    it('reads the integer part of a grouped French quantity whole: 1234.5 counts 1234.5', () => {
        // Why: French writes 1234.5 with a group separator, so the integer is shown in two parts; the count reads both.
        const groups = new Intl.NumberFormat('fr', {minimumFractionDigits: 0, maximumFractionDigits: 10}).formatToParts(1234.5).filter((part) => part.type === 'group');
        expect(groups, 'control: French groups the integer part of 1234.5').toHaveLength(1);
        expect(pluralCount(1234.5, 'fr')).toBe(1234.5);
    });

    it('follows the digits formatQuantity shows, whatever their number: a fraction is counted exactly when one is shown (C-97c-2 guard)', () => {
        // Why: the count and the figure move together. A cure that moved one without the other would word the tooltip by
        // digits it does not show. Green before the cure (six and six) and after it (ten and ten).
        const decimalMark = (locale: string) => new Intl.NumberFormat(locale).formatToParts(0.5).find((part) => part.type === 'decimal')?.value ?? '.';
        /** The count a reader takes from a figure as shown: its integer part, plus one half when it shows a fraction. */
        const countOfShown = (shown: string, locale: string) => {
            const [whole, fraction] = shown.split(decimalMark(locale));
            return Number(whole.replace(/\D/g, '')) + (fraction === undefined ? 0 : 0.5);
        };
        expect([countOfShown('1,234.5', 'en'), countOfShown('1.234,5', 'it'), countOfShown('1', 'en')], 'control: the reading — a grouped integer part, a fraction, none').toEqual([1234.5, 1234.5, 1]);

        for (const locale of ['en', 'it']) {
            for (const value of [3, 1234.5, 1.0004, 1.0000001, 1.00000000001, 0.1234567891]) {
                const shown = formatQuantity(value, locale);
                expect(pluralCount(value, locale), `${value} in ${locale}, shown «${shown}»`).toBe(countOfShown(shown, locale));
            }
        }
    });

    it('counts NaN, which every locale reads as other, for a value that is not finite', () => {
        expect([NaN, Infinity, -Infinity].map((value) => pluralCount(value, 'en'))).toEqual([NaN, NaN, NaN]);
    });
});

describe('lotQuantityLine — the tooltip quantity line, worded by an ICU plural (O-16)', () => {
    /** The translate function the helper takes: the app's own (`$_`, svelte-i18n), as the chart passes it. */
    type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

    interface QuantityLineInput {
        closed: boolean;
        open: number;
        openText: string;
        originalText: string;
        masked: boolean;
    }

    /** What a masked quantity shows (`maskableQuantity`): the input texts of a masked line. */
    const MASK = '•••';

    /** Switches the UI language as LanguageSelector does, and answers the app's translate function in it. */
    async function speak(lang: 'en' | 'it' | 'fr' | 'es'): Promise<Translate> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        return get(_);
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await speak('en');
    });

    /** The helper, after the precondition that it exists. */
    function quantityLine(t: Translate, input: QuantityLineInput): string {
        expect(typeof ganttHelpers.lotQuantityLine, 'lotGanttChartHelpers exports lotQuantityLine').toBe('function');
        return ganttHelpers.lotQuantityLine(t, input);
    }

    /** A closed lot: nothing open, `originalText` at the start. */
    const closedLot = (originalText: string): QuantityLineInput => ({closed: true, open: 0, openText: '0', originalText, masked: false});
    /** An open lot of 10, `open` of them still open, shown as `openText`. */
    const openLot = (open: number, openText: string): QuantityLineInput => ({closed: false, open, openText, originalText: '10', masked: false});
    /** An open lot under privacy: both quantities masked, `open` still the real one. */
    const maskedLot = (open: number): QuantityLineInput => ({closed: false, open, openText: MASK, originalText: MASK, masked: true});

    it.each([
        {lang: 'en', what: 'closed', input: closedLot('10'), line: '10 → 0 shares'},
        {lang: 'en', what: '1 open', input: openLot(1, '1'), line: '1 share open out of 10'},
        {lang: 'en', what: '3 open', input: openLot(3, '3'), line: '3 shares open out of 10'},
        {lang: 'en', what: 'masked, 1 open: plural', input: maskedLot(1), line: `${MASK} shares open out of ${MASK}`},
        {lang: 'it', what: 'closed', input: closedLot('10'), line: '10 → 0 quote'},
        {lang: 'it', what: '1 open', input: openLot(1, '1'), line: '1 quota aperta su 10'},
        {lang: 'it', what: '3 open', input: openLot(3, '3'), line: '3 quote aperte su 10'},
        {lang: 'fr', what: 'closed: 0 is singular in French', input: closedLot('10'), line: '10 → 0 part'},
        {lang: 'fr', what: '1 open', input: openLot(1, '1'), line: '1 part ouverte sur 10'},
        {lang: 'fr', what: '0.5 open: singular in French', input: openLot(0.5, '0,5'), line: '0,5 part ouverte sur 10'},
        {lang: 'fr', what: '3 open', input: openLot(3, '3'), line: '3 parts ouvertes sur 10'},
        {lang: 'fr', what: 'masked, 1 open: plural', input: maskedLot(1), line: `${MASK} parts ouvertes sur ${MASK}`},
        {lang: 'es', what: 'closed', input: closedLot('10'), line: '10 → 0 participaciones'},
        {lang: 'es', what: '1 open', input: openLot(1, '1'), line: '1 participación abierta de 10'},
        {lang: 'es', what: '3 open', input: openLot(3, '3'), line: '3 participaciones abiertas de 10'},
    ] as const)('$lang, $what: «$line»', async ({lang, input, line}) => {
        const t = await speak(lang);
        expect(quantityLine(t, input)).toBe(line);
    });

    it('en: 1.00000000001 open, shown «1», reads the singular: the count comes from the digits shown (rule 6)', async () => {
        // Note: this case alone does not tell the digits shown from the double. Intl.PluralRules rounds 1.00000000001 to three
        // fraction digits too, so a count read off the double would also be singular here; the 1.0004 case below separates them.
        // C-97c-2: this case read 1.0000001, shown «1» at six fraction digits; at ten it is shown whole (the case below).
        const t = await speak('en');
        expect(formatQuantity(1.00000000001), 'control: the digits the tooltip shows').toBe('1');
        expect(new Intl.PluralRules('en').select(1.00000000001), 'control (the note above): the double itself is read as one too').toBe('one');
        expect(quantityLine(t, openLot(1.00000000001, '1'))).toBe('1 share open out of 10');
    });

    it('en: 1.0000001 open, shown «1.0000001» at ten fraction digits, reads the plural: its seventh decimal is shown, so counted (rule 6, C-97c-2)', async () => {
        // Why: the tooltip shows the seventh decimal after the cure, and the noun must follow it. Here the double itself
        // is read as one, so a count read off the double would be singular too: only the digits shown make it plural.
        const t = await speak('en');
        expect(new Intl.PluralRules('en').select(1.0000001), 'control: the double itself is read as one').toBe('one');
        expect(quantityLine(t, openLot(1.0000001, '1.0000001')), 'a fraction is shown, so the plural (today «1.0000001 share open out of 10»: counted on six digits, «1»)').toBe('1.0000001 shares open out of 10');
    });

    it('en: 1.0004 open, shown «1.0004», reads the plural, where a count read off the double would be singular (rule 6, beyond the cases of the brief)', async () => {
        const t = await speak('en');
        expect(formatQuantity(1.0004), 'control: the digits the tooltip shows').toBe('1.0004');
        expect(new Intl.PluralRules('en').select(1.0004), 'control: the double itself is read as one').toBe('one');
        expect(quantityLine(t, openLot(1.0004, '1.0004'))).toBe('1.0004 shares open out of 10');
    });
});

describe('estimateTextWidthPx', () => {
    it('uses the default font size when omitted', () => {
        expect(estimateTextWidthPx('abc')).toBeCloseTo(3 * 11 * 0.58, 6);
    });

    it('honours an explicit font size', () => {
        expect(estimateTextWidthPx('abcd', 22)).toBeCloseTo(4 * 22 * 0.58, 6);
    });

    it('is zero for the empty string', () => {
        expect(estimateTextWidthPx('')).toBe(0);
    });
});

describe('signedColorField', () => {
    const asIs = (v: unknown) => String(v);

    it('returns escaped plain text when the value is missing', () => {
        expect(signedColorField(null, () => 'n/a', true)).toBe('n/a');
    });

    it('returns escaped plain text when the value is exactly zero', () => {
        expect(signedColorField(0, asIs, false)).toBe('0');
    });

    it('wraps a positive value in green (dark vs light theme)', () => {
        expect(signedColorField(5, asIs, true)).toBe('<span style="color:#4ade80">5</span>');
        expect(signedColorField(5, asIs, false)).toBe('<span style="color:#16a34a">5</span>');
    });

    it('wraps a negative value in red (dark vs light theme)', () => {
        expect(signedColorField(-5, asIs, true)).toBe('<span style="color:#f87171">-5</span>');
        expect(signedColorField(-5, asIs, false)).toBe('<span style="color:#dc2626">-5</span>');
    });

    it('HTML-escapes the formatter output before wrapping', () => {
        expect(signedColorField(5, () => '<b>&', true)).toBe('<span style="color:#4ade80">&lt;b&gt;&amp;</span>');
    });
});

describe('segmentBaseColor', () => {
    const brokers = [{id: 1, name: 'Alpha'}];

    it('is violet while in transit (dark vs light)', () => {
        expect(segmentBaseColor({custodyType: 'IN_TRANSIT', brokerId: null}, true, brokers)).toBe('#c084fc');
        expect(segmentBaseColor({custodyType: 'IN_TRANSIT', brokerId: 7}, false, brokers)).toBe('#7c3aed');
    });

    it('is blue when no broker is assigned (dark vs light)', () => {
        expect(segmentBaseColor({custodyType: 'BROKER', brokerId: null}, true, brokers)).toBe('#60a5fa');
        expect(segmentBaseColor({custodyType: 'BROKER', brokerId: null}, false, brokers)).toBe('#2563eb');
    });

    it("is the broker's vivid colour otherwise (dark vs light)", () => {
        const expected = getBrokerColor(1, brokers);
        expect(segmentBaseColor({custodyType: 'BROKER', brokerId: 1}, true, brokers)).toBe(expected.vivid);
        expect(segmentBaseColor({custodyType: 'BROKER', brokerId: 1}, false, brokers)).toBe(expected.vividLight);
    });
});

describe('segmentOpacity', () => {
    it('is dim in transit', () => {
        expect(segmentOpacity({custodyType: 'IN_TRANSIT', endDate: null})).toBe(0.65);
    });

    it('is strong while open (no end date)', () => {
        expect(segmentOpacity({custodyType: 'BROKER', endDate: null})).toBe(0.9);
    });

    it('is faint once closed', () => {
        expect(segmentOpacity({custodyType: 'BROKER', endDate: '2024-01-01'})).toBe(0.45);
    });
});

describe('thicknessForQuantity', () => {
    it('collapses to the minimum when qMax is non-positive', () => {
        expect(thicknessForQuantity(5, 0, false)).toBe(THICKNESS_MIN);
        expect(thicknessForQuantity(5, -1, true)).toBe(THICKNESS_MIN);
    });

    it('reaches the trunk maximum at full quantity', () => {
        expect(thicknessForQuantity(10, 10, false)).toBe(THICKNESS_MAX);
    });

    it('reaches the (smaller) branch maximum at full quantity', () => {
        expect(thicknessForQuantity(10, 10, true)).toBe(BRANCH_THICKNESS_MAX);
    });

    it('interpolates linearly in between', () => {
        expect(thicknessForQuantity(5, 10, false)).toBe(THICKNESS_MIN + 0.5 * (THICKNESS_MAX - THICKNESS_MIN));
    });

    it('clamps an over-max quantity down to the maximum', () => {
        expect(thicknessForQuantity(20, 10, false)).toBe(THICKNESS_MAX);
    });

    it('clamps a negative quantity up to the minimum', () => {
        expect(thicknessForQuantity(-5, 10, false)).toBe(THICKNESS_MIN);
    });
});

describe('segmentIntersectsRange', () => {
    const seg = {startMs: 5, endMs: 10};

    it('always intersects when a bound is null (unbounded)', () => {
        expect(segmentIntersectsRange(seg, null, 20)).toBe(true);
        expect(segmentIntersectsRange(seg, 0, null)).toBe(true);
    });

    it('intersects when the segment overlaps the window', () => {
        expect(segmentIntersectsRange(seg, 0, 20)).toBe(true);
        expect(segmentIntersectsRange(seg, 8, 20)).toBe(true);
    });

    it('does not intersect when it ends at or before the window start', () => {
        expect(segmentIntersectsRange(seg, 10, 20)).toBe(false);
    });

    it('does not intersect when it starts at or after the window end', () => {
        expect(segmentIntersectsRange(seg, 0, 5)).toBe(false);
    });
});

describe('transferPairId', () => {
    it('extracts the pair id from a transfer fragment', () => {
        expect(transferPairId('lot:1/transfer:abc')).toBe('abc');
    });

    it('stops at the next slash', () => {
        expect(transferPairId('lot:1/transfer:abc/leg')).toBe('abc');
    });

    it('is null for a non-transfer fragment', () => {
        expect(transferPairId('plain-fragment')).toBeNull();
        expect(transferPairId('lot:1')).toBeNull();
    });
});

describe('isTransferFragment', () => {
    it('is true when the fragment id embeds a transfer', () => {
        expect(isTransferFragment({fragmentId: 'lot:1/transfer:x', custodyType: 'BROKER'})).toBe(true);
    });

    it('is true when custody is in transit', () => {
        expect(isTransferFragment({fragmentId: 'plain', custodyType: 'IN_TRANSIT'})).toBe(true);
    });

    it('is false for a plain broker fragment', () => {
        expect(isTransferFragment({fragmentId: 'plain', custodyType: 'BROKER'})).toBe(false);
    });
});

describe('laneKeyForFragmentId / laneKeyForSegment', () => {
    it('collapses a transfer onto a shared lane key', () => {
        expect(laneKeyForFragmentId(7, 'lot:7/transfer:abc')).toBe('lot:7/transfer:abc');
        expect(laneKeyForFragmentId(7, 'lot:7/transfer:abc/leg')).toBe('lot:7/transfer:abc');
    });

    it('keys a non-transfer fragment by its own id', () => {
        expect(laneKeyForFragmentId(7, 'plain')).toBe('plain');
    });

    it('delegates for a segment', () => {
        expect(laneKeyForSegment({lotId: 3, fragmentId: 'lot:3/transfer:z'})).toBe('lot:3/transfer:z');
        expect(laneKeyForSegment({lotId: 3, fragmentId: 'solo'})).toBe('solo');
    });
});

describe('branchDepthForLaneKey', () => {
    it('is depth 1 for a transfer lane', () => {
        expect(branchDepthForLaneKey('lot:1/transfer:a')).toBe(1);
    });

    it('is depth 0 for a plain lane', () => {
        expect(branchDepthForLaneKey('plain')).toBe(0);
    });
});

describe('laneSortKey', () => {
    it('picks the earliest start and tags a trunk at depth 0', () => {
        expect(laneSortKey([{startMs: 30}, {startMs: 10}, {startMs: 20}], 'plain')).toEqual([0, 10, 'plain']);
    });

    it('tags a transfer lane at depth 1', () => {
        expect(laneSortKey([{startMs: 5}], 'lot:1/transfer:a')).toEqual([1, 5, 'lot:1/transfer:a']);
    });
});

describe('eventMarkerKind', () => {
    it('maps both transfer directions to TRANSFER', () => {
        expect(eventMarkerKind('TRANSFER_DEPART')).toBe('TRANSFER');
        expect(eventMarkerKind('TRANSFER_ARRIVE')).toBe('TRANSFER');
    });

    it('maps the adjustment kinds', () => {
        expect(eventMarkerKind('ADJUSTMENT_IN')).toBe('ADJUSTMENT_IN');
        expect(eventMarkerKind('ADJUSTMENT_OUT')).toBe('ADJUSTMENT_OUT');
    });

    it('maps SPLIT and SELL directly', () => {
        expect(eventMarkerKind('SPLIT')).toBe('SPLIT');
        expect(eventMarkerKind('SELL')).toBe('SELL');
    });

    it('falls back to BUY for known BUY and for anything unknown', () => {
        expect(eventMarkerKind('BUY')).toBe('BUY');
        expect(eventMarkerKind('SOMETHING_ELSE')).toBe('BUY');
    });
});

describe('eventMarkerSymbol', () => {
    const cases: Array<[EventMarkerKind, string]> = [
        ['SELL', '▼'],
        ['TRANSFER', '◆'],
        ['ADJUSTMENT_IN', '+'],
        ['ADJUSTMENT_OUT', '×'],
        ['SPLIT', '│'],
        ['BUY', '▲'],
    ];
    it.each(cases)('draws %s as %s', (kind, glyph) => {
        expect(eventMarkerSymbol(kind)).toBe(glyph);
    });
});

describe('isSplitTransition', () => {
    it('is false when the quantity is unchanged', () => {
        expect(isSplitTransition({quantity: 10, unitPrice: 5}, {quantity: 10, unitPrice: 5})).toBe(false);
    });

    it('is false when either unit price is non-positive', () => {
        expect(isSplitTransition({quantity: 10, unitPrice: 0}, {quantity: 20, unitPrice: 5})).toBe(false);
        expect(isSplitTransition({quantity: 10, unitPrice: 5}, {quantity: 20, unitPrice: 0})).toBe(false);
    });

    it('is false when a unit price is unknown (null: no FX rate) on either side or both, even where the known notional would match', () => {
        // Control: with both prices known, this transition is a clean 2:1 split (10×10 = 20×5).
        expect(isSplitTransition({quantity: 10, unitPrice: 10}, {quantity: 20, unitPrice: 5})).toBe(true);

        expect(isSplitTransition({quantity: 10, unitPrice: null}, {quantity: 20, unitPrice: 5})).toBe(false);
        expect(isSplitTransition({quantity: 10, unitPrice: 10}, {quantity: 20, unitPrice: null})).toBe(false);
        // Two unknown prices multiply into two zero notionals, which match: only the price guard stops this reading as a split.
        expect(isSplitTransition({quantity: 10, unitPrice: null}, {quantity: 20, unitPrice: null})).toBe(false);
    });

    it('is true when quantity changes but notional is preserved', () => {
        // 10×10 = 100 == 20×5 → a clean 2:1 split.
        expect(isSplitTransition({quantity: 10, unitPrice: 10}, {quantity: 20, unitPrice: 5})).toBe(true);
    });

    it('accepts a notional drift within the relative tolerance', () => {
        // 100 vs 100.01, tolerance = max(1e-6, 100·1e-4 = 0.01) → within.
        expect(isSplitTransition({quantity: 10, unitPrice: 10}, {quantity: 20, unitPrice: 5.0005})).toBe(true);
    });

    it('is false when notional changes beyond the tolerance', () => {
        expect(isSplitTransition({quantity: 10, unitPrice: 10}, {quantity: 20, unitPrice: 8})).toBe(false);
    });
});

describe('inferredTransitionKind', () => {
    it('prefers a known transfer date', () => {
        const kind = inferredTransitionKind({quantity: 10, unitPrice: 5, startMs: 100}, {quantity: 20, unitPrice: 5, startMs: 200}, new Set([200]));
        expect(kind).toBe('TRANSFER');
    });

    it('detects a split when there is no transfer date', () => {
        const kind = inferredTransitionKind({quantity: 10, unitPrice: 10, startMs: 100}, {quantity: 20, unitPrice: 5, startMs: 200}, undefined);
        expect(kind).toBe('SPLIT');
    });

    it('calls a quantity increase an adjustment in', () => {
        const kind = inferredTransitionKind({quantity: 10, unitPrice: 5, startMs: 100}, {quantity: 20, unitPrice: 5, startMs: 200}, new Set([999]));
        expect(kind).toBe('ADJUSTMENT_IN');
    });

    it('calls a quantity decrease a sale', () => {
        const kind = inferredTransitionKind({quantity: 20, unitPrice: 5, startMs: 100}, {quantity: 10, unitPrice: 5, startMs: 200}, undefined);
        expect(kind).toBe('SELL');
    });

    it('falls back to TRANSFER when quantity is unchanged and it is not a split', () => {
        const kind = inferredTransitionKind({quantity: 10, unitPrice: 5, startMs: 100}, {quantity: 10, unitPrice: 5, startMs: 200}, undefined);
        expect(kind).toBe('TRANSFER');
    });

    it('calls a quantity increase an adjustment in, not a split, when a unit price is unknown', () => {
        // Control: with both prices known, the same 10 → 20 transition is a split.
        expect(inferredTransitionKind({quantity: 10, unitPrice: 10, startMs: 100}, {quantity: 20, unitPrice: 5, startMs: 200}, undefined)).toBe('SPLIT');

        expect(inferredTransitionKind({quantity: 10, unitPrice: null, startMs: 100}, {quantity: 20, unitPrice: 5, startMs: 200}, undefined)).toBe('ADJUSTMENT_IN');
        expect(inferredTransitionKind({quantity: 10, unitPrice: 10, startMs: 100}, {quantity: 20, unitPrice: null, startMs: 200}, undefined)).toBe('ADJUSTMENT_IN');
        expect(inferredTransitionKind({quantity: 10, unitPrice: null, startMs: 100}, {quantity: 20, unitPrice: null, startMs: 200}, undefined)).toBe('ADJUSTMENT_IN');
    });

    it('calls a quantity decrease a sale, not a split, when a unit price is unknown', () => {
        // Control: with both prices known, the same 20 → 10 transition is a reverse split (20×5 = 10×10).
        expect(inferredTransitionKind({quantity: 20, unitPrice: 5, startMs: 100}, {quantity: 10, unitPrice: 10, startMs: 200}, undefined)).toBe('SPLIT');

        expect(inferredTransitionKind({quantity: 20, unitPrice: null, startMs: 100}, {quantity: 10, unitPrice: 10, startMs: 200}, undefined)).toBe('SELL');
        expect(inferredTransitionKind({quantity: 20, unitPrice: 5, startMs: 100}, {quantity: 10, unitPrice: null, startMs: 200}, undefined)).toBe('SELL');
        expect(inferredTransitionKind({quantity: 20, unitPrice: null, startMs: 100}, {quantity: 10, unitPrice: null, startMs: 200}, undefined)).toBe('SELL');
    });

    it('still prefers a known transfer date when a unit price is unknown', () => {
        expect(inferredTransitionKind({quantity: 10, unitPrice: null, startMs: 100}, {quantity: 20, unitPrice: null, startMs: 200}, new Set([200]))).toBe('TRANSFER');
        expect(inferredTransitionKind({quantity: 20, unitPrice: 5, startMs: 100}, {quantity: 10, unitPrice: null, startMs: 200}, new Set([200]))).toBe('TRANSFER');
    });
});

describe('applySharedZoomWindow', () => {
    it('overwrites with the external window when both bounds are present', () => {
        expect(applySharedZoomWindow([{start: 0, end: 100, id: 'a'}], 20, 80, 0, 100)).toEqual([{start: 20, end: 80, id: 'a'}]);
    });

    it('uses the initial window when the external start is missing', () => {
        expect(applySharedZoomWindow([{start: 5, end: 95}], null, 80, 0, 100)).toEqual([{start: 0, end: 100}]);
    });

    it('uses the initial window when the external end is missing', () => {
        expect(applySharedZoomWindow([{start: 5, end: 95}], 20, null, 0, 100)).toEqual([{start: 0, end: 100}]);
    });

    it('uses the initial window when both external bounds are undefined', () => {
        expect(applySharedZoomWindow([{start: 5, end: 95}], undefined, undefined, 0, 100)).toEqual([{start: 0, end: 100}]);
    });

    it('preserves other zoom fields and maps every entry', () => {
        expect(
            applySharedZoomWindow(
                [
                    {start: 0, end: 100, type: 'inside'},
                    {start: 0, end: 100, type: 'slider'},
                ],
                10,
                90,
                0,
                100,
            ),
        ).toEqual([
            {start: 10, end: 90, type: 'inside'},
            {start: 10, end: 90, type: 'slider'},
        ]);
    });

    it('returns an empty array unchanged', () => {
        expect(applySharedZoomWindow([], 20, 80, 0, 100)).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// J-48 — a TRANSFER leg crossing the analysis scope is drawn as a transfer
// ---------------------------------------------------------------------------
//
// The backend reads a TRANSFER leg whose partner sits at a broker outside the lots' scope as an ADJUSTMENT_IN (entering)
// or an ADJUSTMENT_OUT (leaving) row (J-10), so the Gantt draws it as an adjustment: «+» or «×», labelled by the
// ADJUSTMENT_IN / ADJUSTMENT_OUT key. J-48 gives each lot timeline event an optional `scope_boundary`, which
// lotChartShared's `scopeBoundaryOf` reads as 'IN' | 'OUT' | null, and the Gantt draws a boundary row as a transfer — its
// marker and its label only:
// - `eventMarkerKind(kind, scopeBoundary?)` answers TRANSFER for an IN or OUT boundary, ADJUSTMENT_IN and ADJUSTMENT_OUT
//   alike, and maps the kind as before without one (absent, null);
// - `eventMarkerLabelKey(kind, labelKind?)`, new, is the i18n key of a marker's label, the lookup the component's
//   `eventMarkerLabel` does today: `brokers.lots.chartMarkers.eventType.<labelKind>` when a label kind is given
//   (lotChartShared's `eventLabelKind`: TRANSFER_IN, TRANSFER_OUT, or the event's own kind), otherwise the marker kind's
//   own key, TRANSFER reading TRANSFER_DEPART's. Keys are asserted, never their translations.
// Red, before the cure: the boundary cases of `eventMarkerKind` fail on their assertion — today the second argument is
// ignored, so a boundary row keeps its adjustment marker; every case of `eventMarkerLabelKey` fails on its precondition,
// the export being missing (it is read off the module namespace, as O-16's helpers were). The cases named «control» hold
// today and after the cure.

describe('J-48 — scope boundary', () => {
    /** The two directions a leg crosses the scope, each with the adjustment kind the backend reads it as (J-10). */
    const CROSSINGS = [
        {kind: 'ADJUSTMENT_IN', boundary: 'IN'},
        {kind: 'ADJUSTMENT_OUT', boundary: 'OUT'},
    ] as const;

    describe('eventMarkerKind — a boundary row is a transfer marker', () => {
        // RED until J-48's cure: the second argument is ignored today, so the row keeps its adjustment marker (+ or ×).
        it.each(CROSSINGS)('$kind across an $boundary boundary is a TRANSFER marker, drawn ◆', ({kind, boundary}) => {
            expect(eventMarkerKind(kind, boundary), `J-48: a leg crossing the scope is a transfer (today: ${kind})`).toBe('TRANSFER');
            expect(eventMarkerSymbol(eventMarkerKind(kind, boundary)), 'J-48: drawn as a transfer, not as an adjustment').toBe('◆');
        });

        // Control, green before and after the cure: the no-boundary case beside each red.
        it.each(CROSSINGS)('control: $kind without a boundary — absent, null or undefined — keeps its own marker', ({kind}) => {
            expect(eventMarkerKind(kind), 'absent').toBe(kind);
            expect(eventMarkerKind(kind, null), 'null').toBe(kind);
            expect(eventMarkerKind(kind, undefined), 'undefined').toBe(kind);
        });

        // Control, green before and after the cure: a null boundary moves no other kind.
        it('control: every other kind keeps its marker under a null boundary', () => {
            const kinds = ['BUY', 'SELL', 'SPLIT', 'TRANSFER_DEPART', 'TRANSFER_ARRIVE'];
            expect(kinds.map((kind) => eventMarkerKind(kind, null))).toEqual(['BUY', 'SELL', 'SPLIT', 'TRANSFER', 'TRANSFER']);
        });
    });

    describe('eventMarkerLabelKey — the i18n key of a marker’s label', () => {
        const EVENT_TYPE = 'brokers.lots.chartMarkers.eventType';

        /** The helper, after the precondition that it exists. */
        function labelKeyOf(kind: EventMarkerKind, labelKind?: string | null): string {
            expect(typeof ganttHelpers.eventMarkerLabelKey, 'lotGanttChartHelpers exports eventMarkerLabelKey').toBe('function');
            return ganttHelpers.eventMarkerLabelKey(kind, labelKind);
        }

        // RED until J-48's cure: lotGanttChartHelpers exports no eventMarkerLabelKey (its precondition fails).
        it.each(['TRANSFER_IN', 'TRANSFER_OUT'])('labels a boundary row’s TRANSFER marker by its label kind, %s', (labelKind) => {
            expect(labelKeyOf('TRANSFER', labelKind)).toBe(`${EVENT_TYPE}.${labelKind}`);
        });

        // RED until J-48's cure: the export is missing. A label kind wins over the marker kind's own key: TRANSFER alone
        // reads TRANSFER_DEPART's key, so an arrival inside the scope tells the two readings apart.
        it('reads any label kind it is given: a TRANSFER marker with TRANSFER_ARRIVE reads TRANSFER_ARRIVE’s key', () => {
            expect(labelKeyOf('TRANSFER', 'TRANSFER_ARRIVE')).toBe(`${EVENT_TYPE}.TRANSFER_ARRIVE`);
        });

        // RED until J-48's cure: the export is missing. The no-label-kind case beside the reds above: the lookup
        // eventMarkerLabel does in the component today.
        it.each([
            {kind: 'BUY', key: 'BUY'},
            {kind: 'SELL', key: 'SELL'},
            {kind: 'TRANSFER', key: 'TRANSFER_DEPART'},
            {kind: 'ADJUSTMENT_IN', key: 'ADJUSTMENT_IN'},
            {kind: 'ADJUSTMENT_OUT', key: 'ADJUSTMENT_OUT'},
            {kind: 'SPLIT', key: 'SPLIT'},
        ] as ReadonlyArray<{kind: EventMarkerKind; key: string}>)('without a label kind, $kind reads the $key key', ({kind, key}) => {
            expect(labelKeyOf(kind), 'absent').toBe(`${EVENT_TYPE}.${key}`);
            expect(labelKeyOf(kind, null), 'null').toBe(`${EVENT_TYPE}.${key}`);
        });
    });
});
