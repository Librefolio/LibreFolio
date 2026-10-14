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
 * @vitest-environment node
 */

import {afterAll, afterEach, describe, it, expect, vi} from 'vitest';

// The browser, pinned before any import: the interface locale takes its region from it.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
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

    it('caps at six fraction digits', () => {
        expect(formatQuantity(1.123456789, 'en-US')).toBe('1.123457');
    });

    it('is callable without an explicit locale (default arg path)', () => {
        expect(typeof formatQuantity(5)).toBe('string');
    });
});

describe('formatQuantity — without a locale, the interface language (M-18)', () => {
    /** A quantity as Intl writes it in `locale`, with the formatter's options: up to six fraction digits. */
    function intlQuantity(locale: string, value: number): string {
        return new Intl.NumberFormat(locale, {minimumFractionDigits: 0, maximumFractionDigits: 6}).format(value);
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
        // 1.123456789 is capped at six fraction digits.
        const quantities = [1234.5, 12345.678, 1.123456789];
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
