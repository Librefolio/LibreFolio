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

import {afterAll, afterEach, beforeEach, describe, it, expect, vi} from 'vitest';

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
import {buildTooltipDivider, buildTooltipRow} from '$lib/components/charts/echartsTooltipHelpers';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {maskableQuantity, PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
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
import {scopeBoundaryOf} from './lotChartShared';
// Q-G29-1: the types of the tooltip contract (erased at runtime, so a missing export fails no import).
import type {GanttMarkerEvent, GanttMarkerTooltipBlock, GanttMarkerTooltipDeps} from './lotGanttChartHelpers';

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
        expect(signedColorField(5, asIs, true)).toBe('<span style="color:#5ed69a">5</span>');
        expect(signedColorField(5, asIs, false)).toBe('<span style="color:#18794e">5</span>');
    });

    it('wraps a negative value in red (dark vs light theme)', () => {
        expect(signedColorField(-5, asIs, true)).toBe('<span style="color:#ff7a86">-5</span>');
        expect(signedColorField(-5, asIs, false)).toBe('<span style="color:#c82838">-5</span>');
    });

    it('HTML-escapes the formatter output before wrapping', () => {
        expect(signedColorField(5, () => '<b>&', true)).toBe('<span style="color:#5ed69a">&lt;b&gt;&amp;</span>');
    });
});

describe('segmentBaseColor', () => {
    const brokers = [{id: 1, name: 'Alpha'}];

    it('is violet while in transit (dark vs light)', () => {
        expect(segmentBaseColor({custodyType: 'IN_TRANSIT', brokerId: null}, true, brokers)).toBe('#b69af0');
        expect(segmentBaseColor({custodyType: 'IN_TRANSIT', brokerId: 7}, false, brokers)).toBe('#7041c6');
    });

    it('is blue when no broker is assigned (dark vs light)', () => {
        expect(segmentBaseColor({custodyType: 'BROKER', brokerId: null}, true, brokers)).toBe('#3f86fa');
        expect(segmentBaseColor({custodyType: 'BROKER', brokerId: null}, false, brokers)).toBe('#155eef');
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

// ---------------------------------------------------------------------------
// Q-G29-1 — a tooltip on every marker of the Gantt
// ---------------------------------------------------------------------------
//
// Developer decision Q-G29-1 (a): every marker the Gantt draws — ▲ BUY, ▼ SELL, ◆ TRANSFER, + ADJUSTMENT_IN, × ADJUSTMENT_OUT,
// │ SPLIT — carries a tooltip on hover or tap: the event's title, its date, its quantity (masked in privacy mode) and its
// broker — «From A / To B» for a transfer between the user's brokers. Markers that fall on the same point (same lane, same
// day) list ALL their events. Six pure helpers carry it, pinned here before they exist; the component only wires them:
// - `markerLabelKind(row)`: the label kind of a `lot_events` row. TRANSFER_IN / TRANSFER_OUT where it crosses the scope (J-48),
//   the row's own kind for TRANSFER_DEPART / TRANSFER_ARRIVE (until now `eventMarkerLabelKey` read the departure's key for
//   every transfer, arrivals included: same text in the four languages, the wrong key), else null;
// - `ganttMarkerEvent(row)`: the row as the tooltip names it (`GanttMarkerEvent`), every scalar-or-array field parsed. A row
//   at the scope's edge keeps only its own broker: the partner is never named (J-48);
// - `ganttMarkerTooltipBlocks(events, deps)`: one block per event — title, then the Date, Quantity and broker rows, plain
//   text. A same-day internal transfer has only an arrival row, with no source or destination (backlog J-68): its tooltip says
//   «To B» and never invents the origin;
// - `groupMarkerEvents(entries)`: the markers to draw, one per (kind, lane, day), each carrying every event at its point;
// - `markerTooltipHtml(blocks, theme)`: the blocks as HTML, every text escaped, one divider between two blocks.
// Red, before the cure: each case fails on its first line — lotGanttChartHelpers does not export the helper it names (read off
// the module namespace, as O-16's and J-48's were, so a missing export fails each case and not the whole file at import). Types
// only are imported by name: they are erased at runtime.

/** A `lot_events` row as the helpers read it: the optional fields scalar-or-array, as the generated client types them. */
interface RawMarkerRow {
    kind: string;
    date: unknown;
    quantity?: unknown;
    broker_id?: unknown;
    source_broker_id?: unknown;
    destination_broker_id?: unknown;
    scope_boundary?: unknown;
}

/** An entry of `groupMarkerEvents`: the drawn marker's keys, an id the case reads it back by, and its event. */
interface GroupEntry {
    id: string;
    kind: EventMarkerKind;
    laneIndex: number;
    dateMs: number;
    event: GanttMarkerEvent;
}

/** The helper `name`, after the precondition that lotGanttChartHelpers exports it. */
function contractHelper<T>(name: string): T {
    const exported = (ganttHelpers as unknown as Record<string, unknown>)[name];
    expect(typeof exported, `lotGanttChartHelpers exports ${name}`).toBe('function');
    return exported as T;
}

function markerLabelKind(row: {kind: string; scope_boundary?: unknown}): string | null {
    return contractHelper<(event: {kind: string; scope_boundary?: unknown}) => string | null>('markerLabelKind')(row);
}

function ganttMarkerEvent(row: RawMarkerRow): GanttMarkerEvent {
    return contractHelper<(row: RawMarkerRow) => GanttMarkerEvent>('ganttMarkerEvent')(row);
}

function ganttMarkerTooltipBlocks(events: readonly GanttMarkerEvent[], deps: GanttMarkerTooltipDeps): GanttMarkerTooltipBlock[] {
    return contractHelper<(events: readonly GanttMarkerEvent[], deps: GanttMarkerTooltipDeps) => GanttMarkerTooltipBlock[]>('ganttMarkerTooltipBlocks')(events, deps);
}

function groupMarkerEvents(entries: readonly GroupEntry[]): Array<{first: GroupEntry; events: GanttMarkerEvent[]}> {
    return contractHelper<(entries: readonly GroupEntry[]) => Array<{first: GroupEntry; events: GanttMarkerEvent[]}>>('groupMarkerEvents')(entries);
}

type TooltipTheme = {bg: string; border: string; textColor: string; mutedColor: string};

function markerTooltipHtml(blocks: readonly GanttMarkerTooltipBlock[], theme: TooltipTheme): string {
    return contractHelper<(blocks: readonly GanttMarkerTooltipBlock[], theme: TooltipTheme) => string>('markerTooltipHtml')(blocks, theme);
}

const TITLE_KEY = 'brokers.lots.chartMarkers.eventType';
const BROKER_NAMES: Record<number, string> = {1: 'Broker A', 2: 'Broker B', 3: 'Broker C'};

/** Fake dependencies: the translator returns the key, every figure is wrapped by what handled it, an absent broker reads «—». */
function fakeDeps(overrides: Partial<GanttMarkerTooltipDeps> = {}): GanttMarkerTooltipDeps {
    return {
        t: (key) => key,
        brokerName: (brokerId) => (brokerId == null ? '—' : (BROKER_NAMES[brokerId] ?? `#${brokerId}`)),
        formatDate: (date) => `D(${date})`,
        formatQuantity: (value) => `Q(${value})`,
        maskQuantity: (formatted) => `M(${formatted})`,
        ...overrides,
    };
}

/** A tooltip event: a plain BUY at Broker A unless overridden. */
function markerEvent(overrides: Partial<GanttMarkerEvent> = {}): GanttMarkerEvent {
    return {kind: 'BUY', labelKind: null, date: '2024-03-15', quantity: 10, brokerId: 1, sourceBrokerId: null, destinationBrokerId: null, ...overrides};
}

/** A block's rows as [label, value] pairs. */
function rowPairs(block: GanttMarkerTooltipBlock): Array<[string, string]> {
    return block.rows.map((row) => [row.label, row.value]);
}

describe('Q-G29-1 — markerLabelKind: the label kind of a lot_events row', () => {
    // A loop, not `it.each('$name')`: vitest cuts a `$name` at forty characters, and these names are the failure report.
    for (const {name, row, expected} of [
        {name: 'a transfer arrival is labelled by its own kind', row: {kind: 'TRANSFER_ARRIVE'}, expected: 'TRANSFER_ARRIVE'},
        {name: 'a transfer departure is labelled by its own kind', row: {kind: 'TRANSFER_DEPART'}, expected: 'TRANSFER_DEPART'},
        {name: 'an ADJUSTMENT_IN across the IN boundary is TRANSFER_IN', row: {kind: 'ADJUSTMENT_IN', scope_boundary: 'IN'}, expected: 'TRANSFER_IN'},
        {name: 'an ADJUSTMENT_IN across the IN boundary, array shape, is TRANSFER_IN', row: {kind: 'ADJUSTMENT_IN', scope_boundary: ['IN']}, expected: 'TRANSFER_IN'},
        {name: 'an ADJUSTMENT_OUT across the OUT boundary is TRANSFER_OUT', row: {kind: 'ADJUSTMENT_OUT', scope_boundary: 'OUT'}, expected: 'TRANSFER_OUT'},
        {name: 'an ADJUSTMENT_OUT across the OUT boundary, array shape, is TRANSFER_OUT', row: {kind: 'ADJUSTMENT_OUT', scope_boundary: ['OUT']}, expected: 'TRANSFER_OUT'},
        {name: 'a boundary decides, whatever the kind: a BUY across IN is TRANSFER_IN', row: {kind: 'BUY', scope_boundary: 'IN'}, expected: 'TRANSFER_IN'},
        {name: 'a boundary decides, whatever the kind: a SELL across OUT is TRANSFER_OUT', row: {kind: 'SELL', scope_boundary: 'OUT'}, expected: 'TRANSFER_OUT'},
        {name: 'a BUY has no label kind', row: {kind: 'BUY'}, expected: null},
        {name: 'a SELL has no label kind', row: {kind: 'SELL'}, expected: null},
        {name: 'a SPLIT has no label kind', row: {kind: 'SPLIT'}, expected: null},
        {name: 'an ADJUSTMENT_IN without a boundary has no label kind', row: {kind: 'ADJUSTMENT_IN'}, expected: null},
        {name: 'an ADJUSTMENT_OUT without a boundary has no label kind', row: {kind: 'ADJUSTMENT_OUT'}, expected: null},
        {name: 'a null boundary is no boundary', row: {kind: 'ADJUSTMENT_IN', scope_boundary: null}, expected: null},
        {name: 'an empty boundary array is no boundary', row: {kind: 'ADJUSTMENT_OUT', scope_boundary: []}, expected: null},
        {name: 'a boundary the scope does not know is no boundary', row: {kind: 'ADJUSTMENT_IN', scope_boundary: 'SIDEWAYS'}, expected: null},
    ] as ReadonlyArray<{name: string; row: {kind: string; scope_boundary?: unknown}; expected: string | null}>) {
        it(name, () => {
            expect(markerLabelKind(row)).toBe(expected);
        });
    }

    // The title key the tooltip reads: through `eventMarkerLabelKey` (which exists), so what is pinned is the pair — an arrival
    // reads its own key, where `eventMarkerLabelKey('TRANSFER')` alone reads the departure's. Red on the missing `markerLabelKind`.
    for (const {name, row, suffix} of [
        {name: 'a transfer arrival', row: {kind: 'TRANSFER_ARRIVE'}, suffix: 'TRANSFER_ARRIVE'},
        {name: 'a transfer departure', row: {kind: 'TRANSFER_DEPART'}, suffix: 'TRANSFER_DEPART'},
        {name: 'an ADJUSTMENT_IN across the IN boundary', row: {kind: 'ADJUSTMENT_IN', scope_boundary: 'IN'}, suffix: 'TRANSFER_IN'},
        {name: 'an ADJUSTMENT_OUT across the OUT boundary, array shape', row: {kind: 'ADJUSTMENT_OUT', scope_boundary: ['OUT']}, suffix: 'TRANSFER_OUT'},
        {name: 'an ADJUSTMENT_IN without a boundary', row: {kind: 'ADJUSTMENT_IN'}, suffix: 'ADJUSTMENT_IN'},
        {name: 'an ADJUSTMENT_OUT without a boundary', row: {kind: 'ADJUSTMENT_OUT'}, suffix: 'ADJUSTMENT_OUT'},
        {name: 'a BUY', row: {kind: 'BUY'}, suffix: 'BUY'},
        {name: 'a SELL', row: {kind: 'SELL'}, suffix: 'SELL'},
        {name: 'a SPLIT', row: {kind: 'SPLIT'}, suffix: 'SPLIT'},
    ] as ReadonlyArray<{name: string; row: {kind: string; scope_boundary?: unknown}; suffix: string}>) {
        it(`the title key of ${name} ends in .${suffix}`, () => {
            const labelKind = markerLabelKind(row);
            const key = ganttHelpers.eventMarkerLabelKey(eventMarkerKind(row.kind, scopeBoundaryOf(row)), labelKind);
            expect(key).toBe(`${TITLE_KEY}.${suffix}`);
        });
    }

    it('an arrival’s title key is not the departure’s', () => {
        const key = ganttHelpers.eventMarkerLabelKey(eventMarkerKind('TRANSFER_ARRIVE'), markerLabelKind({kind: 'TRANSFER_ARRIVE'}));
        expect(key.endsWith('.TRANSFER_ARRIVE'), `the arrival reads ${key}`).toBe(true);
        expect(key.endsWith('.TRANSFER_DEPART'), `the arrival reads ${key}`).toBe(false);
    });
});

describe('Q-G29-1 — ganttMarkerEvent: a lot_events row as its tooltip names it', () => {
    it('reads a plain BUY row: kind, date, quantity and broker; no label kind, no source or destination', () => {
        expect(ganttMarkerEvent({kind: 'BUY', date: '2024-03-15', quantity: 10, broker_id: 1})).toEqual({kind: 'BUY', labelKind: null, date: '2024-03-15', quantity: 10, brokerId: 1, sourceBrokerId: null, destinationBrokerId: null});
    });

    it('keeps the date as sent and the sign of the quantity (the tooltip takes the absolute value, not the row)', () => {
        const event = ganttMarkerEvent({kind: 'SELL', date: '2024-03-16', quantity: -5.5, broker_id: 2});
        expect(event.kind).toBe('SELL');
        expect(event.date).toBe('2024-03-16');
        expect(event.quantity).toBe(-5.5);
        expect(event.brokerId).toBe(2);
    });

    it('parses the scalar-or-array shape and numeric strings: quantity and the three broker ids', () => {
        const event = ganttMarkerEvent({kind: 'TRANSFER_DEPART', date: '2024-03-15', quantity: ['3.25'], broker_id: ['1'], source_broker_id: '1', destination_broker_id: [2]});
        expect(event.quantity).toBe(3.25);
        expect(event.brokerId).toBe(1);
        expect(event.sourceBrokerId).toBe(1);
        expect(event.destinationBrokerId).toBe(2);
    });

    it('reads a numeric quantity and numeric ids as they are', () => {
        const event = ganttMarkerEvent({kind: 'TRANSFER_ARRIVE', date: '2024-03-15', quantity: 7, broker_id: 2, source_broker_id: 1, destination_broker_id: 2});
        expect([event.quantity, event.brokerId, event.sourceBrokerId, event.destinationBrokerId]).toEqual([7, 2, 1, 2]);
    });

    it('anything unparsable is null, never NaN or a guess: quantity and ids', () => {
        const event = ganttMarkerEvent({kind: 'BUY', date: '2024-03-15', quantity: 'abc', broker_id: 'x', source_broker_id: [], destination_broker_id: null});
        expect(event.quantity).toBeNull();
        expect(event.brokerId).toBeNull();
        expect(event.sourceBrokerId).toBeNull();
        expect(event.destinationBrokerId).toBeNull();
    });

    it('absent fields are null', () => {
        const event = ganttMarkerEvent({kind: 'SPLIT', date: '2024-03-15'});
        expect(event).toEqual({kind: 'SPLIT', labelKind: null, date: '2024-03-15', quantity: null, brokerId: null, sourceBrokerId: null, destinationBrokerId: null});
    });

    it('an internal TRANSFER_DEPART is a TRANSFER marker labelled TRANSFER_DEPART, and keeps its source and destination', () => {
        expect(ganttMarkerEvent({kind: 'TRANSFER_DEPART', date: '2024-03-15', quantity: '3', broker_id: 1, source_broker_id: [1], destination_broker_id: ['2']})).toEqual({
            kind: 'TRANSFER',
            labelKind: 'TRANSFER_DEPART',
            date: '2024-03-15',
            quantity: 3,
            brokerId: 1,
            sourceBrokerId: 1,
            destinationBrokerId: 2,
        });
    });

    it('an internal TRANSFER_ARRIVE is a TRANSFER marker labelled TRANSFER_ARRIVE, and keeps its source and destination', () => {
        expect(ganttMarkerEvent({kind: 'TRANSFER_ARRIVE', date: '2024-03-18', quantity: '3', broker_id: 2, source_broker_id: 1, destination_broker_id: 2})).toEqual({
            kind: 'TRANSFER',
            labelKind: 'TRANSFER_ARRIVE',
            date: '2024-03-18',
            quantity: 3,
            brokerId: 2,
            sourceBrokerId: 1,
            destinationBrokerId: 2,
        });
    });

    it('a same-day arrival (broker only, no source or destination) keeps just its broker', () => {
        expect(ganttMarkerEvent({kind: 'TRANSFER_ARRIVE', date: '2024-03-15', quantity: 4, broker_id: 2})).toEqual({kind: 'TRANSFER', labelKind: 'TRANSFER_ARRIVE', date: '2024-03-15', quantity: 4, brokerId: 2, sourceBrokerId: null, destinationBrokerId: null});
    });

    it.each([
        {boundary: 'IN', kind: 'ADJUSTMENT_IN', labelKind: 'TRANSFER_IN'},
        {boundary: 'OUT', kind: 'ADJUSTMENT_OUT', labelKind: 'TRANSFER_OUT'},
    ])('a row at the scope’s edge ($boundary) is a TRANSFER marker labelled $labelKind and keeps only its broker: the partner is never named', ({boundary, kind, labelKind}) => {
        const row = {kind, date: '2024-03-15', quantity: '4', broker_id: 1, source_broker_id: 2, destination_broker_id: 3};
        expect(ganttMarkerEvent({...row, scope_boundary: boundary})).toEqual({kind: 'TRANSFER', labelKind, date: '2024-03-15', quantity: 4, brokerId: 1, sourceBrokerId: null, destinationBrokerId: null});
        // The array shape of the generated client reads the same.
        expect(ganttMarkerEvent({...row, source_broker_id: [2], destination_broker_id: [3], scope_boundary: [boundary]})).toEqual({kind: 'TRANSFER', labelKind, date: '2024-03-15', quantity: 4, brokerId: 1, sourceBrokerId: null, destinationBrokerId: null});
    });
});

describe('Q-G29-1 — ganttMarkerTooltipBlocks: one block per event', () => {
    it('is one block per event, in the given order, and none for no event', () => {
        const events = [markerEvent({kind: 'SELL', quantity: 1}), markerEvent({kind: 'BUY', quantity: 2}), markerEvent({kind: 'SPLIT', quantity: 3})];
        expect(ganttMarkerTooltipBlocks(events, fakeDeps()).map((block) => block.title)).toEqual([`${TITLE_KEY}.SELL`, `${TITLE_KEY}.BUY`, `${TITLE_KEY}.SPLIT`]);
        expect(ganttMarkerTooltipBlocks([], fakeDeps())).toEqual([]);
    });

    it('a BUY: title key, then Date, Quantity, Broker, in that order', () => {
        const [block] = ganttMarkerTooltipBlocks([markerEvent({kind: 'BUY', date: '2024-03-15', quantity: 10, brokerId: 1})], fakeDeps());
        expect(block.title).toBe(`${TITLE_KEY}.BUY`);
        expect(rowPairs(block)).toEqual([
            ['common.date', 'D(2024-03-15)'],
            ['common.quantity', 'M(Q(10))'],
            ['common.broker', 'Broker A'],
        ]);
    });

    it.each([
        {kind: 'BUY', key: 'BUY'},
        {kind: 'SELL', key: 'SELL'},
        {kind: 'SPLIT', key: 'SPLIT'},
        {kind: 'ADJUSTMENT_IN', key: 'ADJUSTMENT_IN'},
        {kind: 'ADJUSTMENT_OUT', key: 'ADJUSTMENT_OUT'},
    ] as ReadonlyArray<{kind: EventMarkerKind; key: string}>)('a $kind is titled $key and carries one Broker row, never a From or To', ({kind, key}) => {
        const [block] = ganttMarkerTooltipBlocks([markerEvent({kind, brokerId: 2})], fakeDeps());
        expect(block.title).toBe(`${TITLE_KEY}.${key}`);
        expect(block.rows.map((row) => row.label)).toEqual(['common.date', 'common.quantity', 'common.broker']);
        expect(block.rows.at(-1)?.value).toBe('Broker B');
    });

    it('the translator is the one the deps carry: the title is what it returns for the key', () => {
        const [block] = ganttMarkerTooltipBlocks([markerEvent({kind: 'SELL'})], fakeDeps({t: (key) => (key === `${TITLE_KEY}.SELL` ? 'Sale' : key === 'common.broker' ? 'Broker' : key)}));
        expect(block.title).toBe('Sale');
        expect(block.rows.at(-1)?.label).toBe('Broker');
    });

    it('a SELL with a negative quantity shows the absolute value', () => {
        const [block] = ganttMarkerTooltipBlocks([markerEvent({kind: 'SELL', quantity: -5.5})], fakeDeps());
        expect(rowPairs(block)).toContainEqual(['common.quantity', 'M(Q(5.5))']);
    });

    it('a quantity of zero is a quantity: its row is shown', () => {
        const [block] = ganttMarkerTooltipBlocks([markerEvent({quantity: 0})], fakeDeps());
        expect(rowPairs(block)).toContainEqual(['common.quantity', 'M(Q(0))']);
    });

    it('a null quantity has no quantity row, and nothing stands in for it', () => {
        const [block] = ganttMarkerTooltipBlocks([markerEvent({quantity: null})], fakeDeps());
        expect(block.rows.map((row) => row.label)).toEqual(['common.date', 'common.broker']);
    });

    it('no broker, no Broker row: the tooltip does not write «—» for it', () => {
        const [block] = ganttMarkerTooltipBlocks([markerEvent({brokerId: null})], fakeDeps());
        expect(block.rows.map((row) => row.label)).toEqual(['common.date', 'common.quantity']);
    });

    it('the date reaches formatDate as sent', () => {
        const dates: string[] = [];
        const formatDate = (date: string): string => {
            dates.push(date);
            return date;
        };
        ganttMarkerTooltipBlocks([markerEvent({date: '2023-12-31'})], fakeDeps({formatDate}));
        expect(dates).toEqual(['2023-12-31']);
    });

    describe('a transfer between the user’s brokers', () => {
        it('a multi-day transfer: the departure and the arrival both read From A, To B, under their own titles', () => {
            const departure = ganttMarkerEvent({kind: 'TRANSFER_DEPART', date: '2024-03-15', quantity: 3, broker_id: 1, source_broker_id: 1, destination_broker_id: 2});
            const arrival = ganttMarkerEvent({kind: 'TRANSFER_ARRIVE', date: '2024-03-18', quantity: 3, broker_id: 2, source_broker_id: 1, destination_broker_id: 2});
            const [depart, arrive] = ganttMarkerTooltipBlocks([departure, arrival], fakeDeps());

            expect(depart.title).toBe(`${TITLE_KEY}.TRANSFER_DEPART`);
            expect(rowPairs(depart)).toEqual([
                ['common.date', 'D(2024-03-15)'],
                ['common.quantity', 'M(Q(3))'],
                ['common.from', 'Broker A'],
                ['common.to', 'Broker B'],
            ]);
            expect(arrive.title).toBe(`${TITLE_KEY}.TRANSFER_ARRIVE`);
            expect(rowPairs(arrive)).toEqual([
                ['common.date', 'D(2024-03-18)'],
                ['common.quantity', 'M(Q(3))'],
                ['common.from', 'Broker A'],
                ['common.to', 'Broker B'],
            ]);
        });

        it('a same-day arrival (no source, no destination) says only «To B»: no From row, and nothing written for the origin it does not know', () => {
            const [block] = ganttMarkerTooltipBlocks([ganttMarkerEvent({kind: 'TRANSFER_ARRIVE', date: '2024-03-15', quantity: 3, broker_id: 2})], fakeDeps());
            expect(block.title).toBe(`${TITLE_KEY}.TRANSFER_ARRIVE`);
            expect(rowPairs(block)).toEqual([
                ['common.date', 'D(2024-03-15)'],
                ['common.quantity', 'M(Q(3))'],
                ['common.to', 'Broker B'],
            ]);
            expect(
                block.rows.some((row) => row.label === 'common.from'),
                'no From row',
            ).toBe(false);
            expect(
                block.rows.filter((row) => row.value === '—' || /null|undefined|#/.test(row.value)),
                'no row for an origin that is not known',
            ).toEqual([]);
        });

        it('a departure that names no destination says «From A» alone: the broker is the origin, the destination is not invented', () => {
            const [block] = ganttMarkerTooltipBlocks([markerEvent({kind: 'TRANSFER', labelKind: 'TRANSFER_DEPART', brokerId: 1})], fakeDeps());
            expect(block.rows.filter((row) => row.label === 'common.from' || row.label === 'common.to' || row.label === 'common.broker')).toEqual([{label: 'common.from', value: 'Broker A'}]);
        });

        it('a departure whose destination is named reads From (its own broker) and To (the destination)', () => {
            const [block] = ganttMarkerTooltipBlocks([markerEvent({kind: 'TRANSFER', labelKind: 'TRANSFER_DEPART', brokerId: 1, sourceBrokerId: null, destinationBrokerId: 3})], fakeDeps());
            expect(block.rows.filter((row) => row.label === 'common.from' || row.label === 'common.to')).toEqual([
                {label: 'common.from', value: 'Broker A'},
                {label: 'common.to', value: 'Broker C'},
            ]);
        });

        it('an arrival whose origin is named reads From (the source) and To (its own broker)', () => {
            const [block] = ganttMarkerTooltipBlocks([markerEvent({kind: 'TRANSFER', labelKind: 'TRANSFER_ARRIVE', brokerId: 2, sourceBrokerId: 3, destinationBrokerId: null})], fakeDeps());
            expect(block.rows.filter((row) => row.label === 'common.from' || row.label === 'common.to')).toEqual([
                {label: 'common.from', value: 'Broker C'},
                {label: 'common.to', value: 'Broker B'},
            ]);
        });

        it('a source and a destination the row names win over its own broker, whichever side it is on', () => {
            const [depart, arrive] = ganttMarkerTooltipBlocks(
                [markerEvent({kind: 'TRANSFER', labelKind: 'TRANSFER_DEPART', brokerId: 3, sourceBrokerId: 1, destinationBrokerId: 2}), markerEvent({kind: 'TRANSFER', labelKind: 'TRANSFER_ARRIVE', brokerId: 3, sourceBrokerId: 1, destinationBrokerId: 2})],
                fakeDeps(),
            );
            const sides = (block: GanttMarkerTooltipBlock) => block.rows.filter((row) => row.label === 'common.from' || row.label === 'common.to').map((row) => row.value);
            expect(sides(depart)).toEqual(['Broker A', 'Broker B']);
            expect(sides(arrive)).toEqual(['Broker A', 'Broker B']);
        });

        it('a TRANSFER with no label kind reads the source and the destination it carries', () => {
            const [block] = ganttMarkerTooltipBlocks([markerEvent({kind: 'TRANSFER', labelKind: null, brokerId: 3, sourceBrokerId: 1, destinationBrokerId: 2})], fakeDeps());
            expect(block.rows.filter((row) => row.label === 'common.from' || row.label === 'common.to')).toEqual([
                {label: 'common.from', value: 'Broker A'},
                {label: 'common.to', value: 'Broker B'},
            ]);
        });

        it('a TRANSFER with no label kind and no source or destination falls back to one Broker row', () => {
            const [block] = ganttMarkerTooltipBlocks([markerEvent({kind: 'TRANSFER', labelKind: null, brokerId: 2})], fakeDeps());
            expect(block.rows.filter((row) => ['common.from', 'common.to', 'common.broker'].includes(row.label))).toEqual([{label: 'common.broker', value: 'Broker B'}]);
        });

        it('a transfer that names no broker at all has no broker row', () => {
            const [block] = ganttMarkerTooltipBlocks([markerEvent({kind: 'TRANSFER', labelKind: 'TRANSFER_ARRIVE', brokerId: null})], fakeDeps());
            expect(block.rows.map((row) => row.label)).toEqual(['common.date', 'common.quantity']);
        });
    });

    describe('a transfer leg at the scope’s edge', () => {
        it.each([
            {labelKind: 'TRANSFER_IN', key: 'TRANSFER_IN'},
            {labelKind: 'TRANSFER_OUT', key: 'TRANSFER_OUT'},
        ])('$labelKind: one Broker row (its own broker), never From or To, even when the event carries a source and a destination', ({labelKind, key}) => {
            const [block] = ganttMarkerTooltipBlocks([markerEvent({kind: 'TRANSFER', labelKind, brokerId: 1, sourceBrokerId: 2, destinationBrokerId: 3})], fakeDeps());
            expect(block.title).toBe(`${TITLE_KEY}.${key}`);
            expect(rowPairs(block)).toEqual([
                ['common.date', 'D(2024-03-15)'],
                ['common.quantity', 'M(Q(10))'],
                ['common.broker', 'Broker A'],
            ]);
            expect(block.rows.some((row) => row.label === 'common.from' || row.label === 'common.to')).toBe(false);
        });

        it('end to end: a raw TRANSFER_IN row with a source and a destination names its own broker alone', () => {
            const event = ganttMarkerEvent({kind: 'ADJUSTMENT_IN', date: '2024-03-15', quantity: '10', broker_id: 1, source_broker_id: 2, destination_broker_id: 3, scope_boundary: 'IN'});
            const [block] = ganttMarkerTooltipBlocks([event], fakeDeps());
            expect(block.title).toBe(`${TITLE_KEY}.TRANSFER_IN`);
            expect(block.rows.filter((row) => ['common.from', 'common.to', 'common.broker'].includes(row.label))).toEqual([{label: 'common.broker', value: 'Broker A'}]);
        });
    });

    it('the blocks are plain text: a broker name is not escaped here (markerTooltipHtml escapes it, once)', () => {
        const name = 'Broker <A> & Co';
        const [block] = ganttMarkerTooltipBlocks([markerEvent({brokerId: 1})], fakeDeps({brokerName: () => name}));
        expect(block.rows.at(-1)?.value).toBe(name);
    });

    it('two events at one point are two blocks, each its own: a BUY and a TRANSFER_ARRIVE', () => {
        const blocks = ganttMarkerTooltipBlocks([markerEvent({kind: 'BUY', quantity: 10, brokerId: 1}), ganttMarkerEvent({kind: 'TRANSFER_ARRIVE', date: '2024-03-15', quantity: 4, broker_id: 2})], fakeDeps());
        expect(blocks.map((block) => block.title)).toEqual([`${TITLE_KEY}.BUY`, `${TITLE_KEY}.TRANSFER_ARRIVE`]);
        expect(rowPairs(blocks[0])).toContainEqual(['common.broker', 'Broker A']);
        expect(rowPairs(blocks[1])).toContainEqual(['common.to', 'Broker B']);
    });
});

describe('Q-G29-1 — ganttMarkerTooltipBlocks: privacy masks the quantity', () => {
    // The privacy flag is module level state: reset on both sides so a flag left on cannot mask a clear-text control.
    beforeEach(() => setPrivacyEnabled(false));
    afterEach(() => setPrivacyEnabled(false));

    it('the quantity value is what maskQuantity returns, over the formatted absolute value (fake mask)', () => {
        const seen: string[] = [];
        const maskQuantity = (formatted: string): string => {
            seen.push(formatted);
            return 'MASKED';
        };
        const [block] = ganttMarkerTooltipBlocks([markerEvent({kind: 'SELL', quantity: -12})], fakeDeps({formatQuantity: (value) => `fmt:${value}`, maskQuantity}));
        expect(seen, 'maskQuantity gets the formatted absolute value').toEqual(['fmt:12']);
        expect(rowPairs(block)).toContainEqual(['common.quantity', 'MASKED']);
    });

    it('with privacy ON, the real maskableQuantity hides every digit of the quantity: in the row and in the whole block', () => {
        const realDeps = fakeDeps({formatQuantity: (value) => formatQuantity(value, 'en-US'), maskQuantity: maskableQuantity});
        // Control, privacy OFF: the same call shows the digits, so the masked lines below are a substitution.
        const [clear] = ganttMarkerTooltipBlocks([markerEvent({kind: 'SELL', quantity: -4321.5})], realDeps);
        expect(clear.rows.find((row) => row.label === 'common.quantity')?.value, 'privacy OFF shows the absolute quantity').toBe('4,321.5');

        setPrivacyEnabled(true);
        const [masked] = ganttMarkerTooltipBlocks([markerEvent({kind: 'SELL', quantity: -4321.5})], realDeps);
        const value = masked.rows.find((row) => row.label === 'common.quantity')?.value ?? '';
        expect(value, 'privacy ON: the placeholder, no sign, no digit').toBe(PRIVACY_PLACEHOLDER);
        expect(/\d/.test(value), 'no digit of the quantity in the row').toBe(false);
        const everything = JSON.stringify(masked);
        for (const leak of ['4321', '4,321', '4.321', '4 321']) expect(everything.includes(leak), `the block leaks ${leak}`).toBe(false);
        // The date and the broker are not masked: only the quantity is.
        expect(rowPairs(masked)).toContainEqual(['common.date', 'D(2024-03-15)']);
        expect(rowPairs(masked)).toContainEqual(['common.broker', 'Broker A']);
    });

    it('the mask follows the flag at each call: ON, then OFF again, the digits are back', () => {
        const realDeps = fakeDeps({formatQuantity: (value) => formatQuantity(value, 'en-US'), maskQuantity: maskableQuantity});
        const quantityOf = (): string | undefined => ganttMarkerTooltipBlocks([markerEvent({quantity: 250})], realDeps)[0]?.rows.find((row) => row.label === 'common.quantity')?.value;

        setPrivacyEnabled(true);
        expect(quantityOf()).toBe(PRIVACY_PLACEHOLDER);
        setPrivacyEnabled(false);
        expect(quantityOf()).toBe('250');
    });
});

describe('Q-G29-1 — groupMarkerEvents: one marker per (kind, lane, day), carrying every event at its point', () => {
    const DAY_1 = Date.UTC(2024, 2, 15);
    const DAY_2 = Date.UTC(2024, 2, 16);

    /** An entry whose event carries `quantity`, the identity the cases read the events back by. */
    function entry(id: string, kind: EventMarkerKind, laneIndex: number, dateMs: number, quantity: number): GroupEntry {
        return {id, kind, laneIndex, dateMs, event: markerEvent({kind, quantity})};
    }

    /** What the cases compare: each marker's first entry (by id) and its events (by quantity). */
    function shape(groups: Array<{first: GroupEntry; events: GanttMarkerEvent[]}>) {
        return groups.map((group) => ({first: group.first.id, events: group.events.map((event) => event.quantity)}));
    }

    it('two BUYs on the same lane and day are one marker whose events are both', () => {
        const groups = groupMarkerEvents([entry('b1', 'BUY', 0, DAY_1, 1), entry('b2', 'BUY', 0, DAY_1, 2)]);
        expect(shape(groups)).toEqual([{first: 'b1', events: [1, 2]}]);
    });

    it('a BUY and a SELL on the same lane and day are two markers, each listing both events in input order', () => {
        const groups = groupMarkerEvents([entry('buy', 'BUY', 0, DAY_1, 1), entry('sell', 'SELL', 0, DAY_1, 2)]);
        expect(shape(groups)).toEqual([
            {first: 'buy', events: [1, 2]},
            {first: 'sell', events: [1, 2]},
        ]);
    });

    it('the events follow the input order, not the kinds’: a SELL before a BUY lists the SELL first, on both markers', () => {
        const groups = groupMarkerEvents([entry('sell', 'SELL', 0, DAY_1, 1), entry('buy', 'BUY', 0, DAY_1, 2)]);
        expect(shape(groups)).toEqual([
            {first: 'sell', events: [1, 2]},
            {first: 'buy', events: [1, 2]},
        ]);
    });

    it('a marker keeps the first entry of its kind and every event around it: BUY, SELL, BUY at one point', () => {
        const groups = groupMarkerEvents([entry('b1', 'BUY', 0, DAY_1, 1), entry('s', 'SELL', 0, DAY_1, 2), entry('b2', 'BUY', 0, DAY_1, 3)]);
        expect(shape(groups)).toEqual([
            {first: 'b1', events: [1, 2, 3]},
            {first: 's', events: [1, 2, 3]},
        ]);
    });

    it('another lane or another day is another point: its markers list only their own events', () => {
        const groups = groupMarkerEvents([
            entry('a', 'BUY', 0, DAY_1, 1), // lane 0, day 1
            entry('b', 'BUY', 1, DAY_1, 2), // lane 1, day 1
            entry('c', 'SELL', 1, DAY_1, 3), // lane 1, day 1, with b
            entry('d', 'BUY', 0, DAY_2, 4), // lane 0, day 2
        ]);
        expect(shape(groups)).toEqual([
            {first: 'a', events: [1]},
            {first: 'b', events: [2, 3]},
            {first: 'c', events: [2, 3]},
            {first: 'd', events: [4]},
        ]);
    });

    it('keeps the order of first appearance — not the date’s, not the lane’s — and folds a later duplicate into its marker', () => {
        const groups = groupMarkerEvents([
            entry('a', 'BUY', 1, DAY_2, 1), // appears first, though it is the latest day and the highest lane
            entry('b', 'SELL', 0, DAY_1, 2),
            entry('c', 'BUY', 1, DAY_2, 3), // the same point as a: folded into a’s marker
            entry('d', 'BUY', 0, DAY_1, 4), // same lane and day as b, another kind: its own marker, after b’s
        ]);
        expect(shape(groups)).toEqual([
            {first: 'a', events: [1, 3]},
            {first: 'b', events: [2, 4]},
            {first: 'd', events: [2, 4]},
        ]);
    });

    it('a marker’s `first` is the entry itself, not a copy', () => {
        const only = entry('only', 'SPLIT', 2, DAY_1, 9);
        const [group] = groupMarkerEvents([only]);
        expect(group.first).toBe(only);
    });

    it('no entry, no marker', () => {
        expect(groupMarkerEvents([])).toEqual([]);
    });
});

describe('Q-G29-1 — markerTooltipHtml: the tooltip HTML', () => {
    const THEME: TooltipTheme = {bg: '#101010', border: '#2a2a2a', textColor: '#f0f0f0', mutedColor: '#9a9a9a'};
    const BUY_BLOCK: GanttMarkerTooltipBlock = {
        title: 'Buy',
        rows: [
            {label: 'Date', value: '15 Mar 2024'},
            {label: 'Broker', value: 'Broker A'},
        ],
    };
    const SELL_BLOCK: GanttMarkerTooltipBlock = {title: 'Sale', rows: [{label: 'Date', value: '16 Mar 2024'}]};

    /** Whether the first `<div` of the markup closes only at its very end: one wrapper around everything. */
    function isOneWrapper(html: string): boolean {
        let depth = 0;
        for (const token of html.matchAll(/<div\b|<\/div>/g)) {
            depth += token[0] === '</div>' ? -1 : 1;
            if (depth === 0 && (token.index ?? 0) + token[0].length < html.length) return false;
        }
        return depth === 0 && html.startsWith('<div');
    }

    const dividerCount = (html: string): number => html.split('<hr').length - 1;

    it('escapes a broker name: markup becomes text, no raw tag comes out', () => {
        const hostile = '<img src=x onerror=alert(1)>';
        const html = markerTooltipHtml([{title: 'Buy', rows: [{label: 'Broker', value: hostile}]}], THEME);
        expect(html.includes('<img'), 'a raw <img in the markup').toBe(false);
        expect(html).toContain(escapeHtml(hostile));
        expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;');
    });

    it('escapes a title and a row label too: «&» and tags in them', () => {
        const html = markerTooltipHtml([{title: 'Buy & <b>hold</b>', rows: [{label: '<script>x</script>', value: 'a & b'}]}], THEME);
        expect(html).toContain('Buy &amp; &lt;b&gt;hold&lt;/b&gt;');
        expect(html).toContain('&lt;script&gt;x&lt;/script&gt;');
        expect(html).toContain('a &amp; b');
        expect(html.includes('<script'), 'a raw <script in the markup').toBe(false);
        expect(html.includes('<b>hold'), 'a raw <b> from the title').toBe(false);
    });

    it('opens no tag of the text’s own, whatever it carries', () => {
        const html = markerTooltipHtml(
            [
                {title: '<iframe src=x>', rows: [{label: '<a href=x>', value: '<svg onload=alert(1)>'}]},
                {title: 'x', rows: [{label: 'y', value: '<hr>'}]},
            ],
            THEME,
        );
        const tags = new Set([...html.matchAll(/<\/?([a-z][a-z0-9]*)/gi)].map((match) => match[1].toLowerCase()));
        expect([...tags].filter((tag) => ['iframe', 'a', 'svg', 'img', 'script'].includes(tag))).toEqual([]);
    });

    it('escapes once: the plain-text blocks of a hostile broker come out as &lt;, never &amp;lt;', () => {
        const blocks = ganttMarkerTooltipBlocks([markerEvent({brokerId: 1})], fakeDeps({brokerName: () => '<img src=x onerror=alert(1)>'}));
        const html = markerTooltipHtml(blocks, THEME);
        expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;');
        expect(html.includes('&amp;lt;'), 'escaped twice').toBe(false);
        expect(html.includes('<img')).toBe(false);
    });

    it('writes each block’s title, then its rows through buildTooltipRow, label and value escaped', () => {
        const html = markerTooltipHtml([BUY_BLOCK], THEME);
        const rows = BUY_BLOCK.rows.map((row) => buildTooltipRow(escapeHtml(row.label), escapeHtml(row.value)));
        for (const row of rows) expect(html, 'a row written by buildTooltipRow').toContain(row);
        expect(html.indexOf('Buy')).toBeGreaterThanOrEqual(0);
        expect(html.indexOf('Buy'), 'the title comes before its rows').toBeLessThan(html.indexOf(rows[0]));
        expect(html.indexOf(rows[0]), 'the rows keep their order').toBeLessThan(html.indexOf(rows[1]));
    });

    it('wraps everything in one <div>', () => {
        expect(isOneWrapper(markerTooltipHtml([BUY_BLOCK], THEME)), 'one block').toBe(true);
        expect(isOneWrapper(markerTooltipHtml([BUY_BLOCK, SELL_BLOCK], THEME)), 'two blocks').toBe(true);
    });

    it('two blocks have exactly one divider between them: after the first block’s rows, before the second’s title', () => {
        const html = markerTooltipHtml([BUY_BLOCK, SELL_BLOCK], THEME);
        const divider = buildTooltipDivider(THEME.border);
        expect(dividerCount(html)).toBe(1);
        expect(html, 'the divider is the shared one, in the theme’s border colour').toContain(divider);
        const lastRowOfFirst = buildTooltipRow(escapeHtml('Broker'), escapeHtml('Broker A'));
        expect(html.indexOf(lastRowOfFirst)).toBeLessThan(html.indexOf(divider));
        expect(html.indexOf(divider)).toBeLessThan(html.indexOf('Sale'));
    });

    it('three blocks have two dividers: one between each pair, none before the first or after the last', () => {
        const html = markerTooltipHtml([BUY_BLOCK, SELL_BLOCK, {title: 'Split', rows: [{label: 'Date', value: '17 Mar 2024'}]}], THEME);
        expect(dividerCount(html)).toBe(2);
        const divider = buildTooltipDivider(THEME.border);
        const lastRowOfFirst = buildTooltipRow(escapeHtml('Broker'), escapeHtml('Broker A'));
        expect(html.indexOf(divider), 'no divider before the first block’s rows end').toBeGreaterThan(html.indexOf(lastRowOfFirst));
        expect(html.lastIndexOf(divider), 'no divider after the last block’s title').toBeLessThan(html.indexOf('Split'));
    });

    it('one block has no divider, and neither does text that merely looks like one', () => {
        expect(dividerCount(markerTooltipHtml([BUY_BLOCK], THEME))).toBe(0);
        expect(dividerCount(markerTooltipHtml([{title: 'Buy', rows: [{label: 'Broker', value: '<hr>'}]}], THEME)), 'an escaped <hr> is not a divider').toBe(0);
    });
});
