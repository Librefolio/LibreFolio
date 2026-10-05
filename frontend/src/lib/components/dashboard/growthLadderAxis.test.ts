/**
 * S7 — the category x axis of the GrowthChart ladder: the pure planner, pinned.
 *
 * `planLadderAxis` decides, for the P&L candles and Income ladders, which bucket carries a
 * label, which bucket edge carries a separator and how far an edge label moves inward so
 * the canvas does not clip it; `ladderAxisOption` turns that plan into the ECharts
 * `axisLabel` / `splitLine` options. The contract is the docblock of `growthLadderAxis.ts`.
 *
 * WHERE THE EXPECTED VALUES COME FROM. The pins (A1–A9) are literals transcribed from the
 * S7 brief's appendix and its 30/09 addendum (A8-bis), one `it` per case; nothing here
 * computes an expected value with the planner's algorithm. The sweep (A10) checks 3168
 * plans against an oracle written in this file from the contract, the calendar and Intl
 * alone: the only import from the product is the module under test.
 *
 * THE TEXTS ARE ICU'S. Every label literal is `Intl.DateTimeFormat` output (ICU 78.3,
 * Node 26.8.2). A0 asserts those texts first, with messages starting `ICU changed:`, so a
 * Node or ICU upgrade reads as an environment change, not as a planner defect.
 *
 * GREEN ON THE STUB, ON PURPOSE: A0, the empty-plan contract lines (Empty and the four
 * unmeasured geometries) and the width estimate. Everything else is red until the planner
 * is written.
 */
import {describe, expect, it} from 'vitest';
import {LADDER_EDGE_SAFETY_PX, LADDER_LABEL_GAP_PX, estimateLadderLabelWidthPx, ladderAxisOption, planLadderAxis} from './growthLadderAxis';
import type {LadderAxisInput, LadderAxisMode, LadderAxisOption, LadderAxisPlan} from './growthLadderAxis';

// WHY: below this slot width separators fall back to month edges, plus the 30/09 anchor on the first visible bucket when exactly
// one visible bucket holds a 1st and it is not the first (ECharts 6 moves a lone band tick to the axis start) — CANDLE_MIN_SLOT_PX = 8 in
// charts/timeSeriesAggregation.ts:60, written as a literal because the oracle imports nothing but the module under test.
const CANDLE_MIN_SLOT_PX = 8;

// WHY: centres are float multiples of plot / count, so a gap or an overflow that is exactly an integer can land a hair
// either side of it depending on evaluation order; 1e-9 px absorbs that noise and can never hide a real pixel.
const EPS = 1e-9;

const DAY_MS = 86_400_000;

// =============================================================================
// Fixture builders (the appendix's daily / endAnchored, UTC arithmetic)
// =============================================================================

// WHY: fixtures are calendar days; whole UTC day numbers keep the arithmetic free of time zones and DST.
function toDay(iso: string): number {
    const [year, month, day] = iso.split('-').map(Number);
    return Date.UTC(year, month - 1, day) / DAY_MS;
}

// WHY: the inverse of toDay, so every closing a builder produces is an ISO date again.
function fromDay(day: number): string {
    return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

// WHY: the appendix's daily(a, b) — every calendar day from a to b, inclusive.
function daily(first: string, last: string): string[] {
    const out: string[] = [];
    for (let day = toDay(first); day <= toDay(last); day++) out.push(fromDay(day));
    return out;
}

// WHY: the appendix's endAnchored(first, last, span) — n = ceil(days / span) closings, the last one on `last`.
function endAnchored(first: string, last: string, span: number): string[] {
    const days = toDay(last) - toDay(first) + 1;
    const n = Math.ceil(days / span);
    return Array.from({length: n}, (_, i) => fromDay(toDay(last) - span * (n - 1 - i)));
}

// WHY: the A6/A7 two-year series, one per rung, as the appendix writes it.
function twoYears(span: number): string[] {
    return endAnchored('2024-10-01', '2026-09-30', span);
}

const EX1 = daily('2026-08-31', '2026-09-30');
const EX1_FIXTURE = [31, '2026-08-31', '2026-09-30'] as const;
const EX2 = endAnchored('2026-03-31', '2026-09-30', 7);
const EX2_FIXTURE = [27, '2026-04-01', '2026-09-30'] as const;
const EX3 = daily('2026-06-25', '2026-09-24');
const EX3_FIXTURE = [92, '2026-06-25', '2026-09-24'] as const;
const EX4 = endAnchored('2024-11-02', '2025-05-30', 30);
const EX4_FIXTURE = [7, '2024-12-01', '2025-05-30'] as const;
const EX5 = endAnchored('2025-10-01', '2026-09-30', 7);
const EX5_FIXTURE = [53, '2025-10-01', '2026-09-30'] as const;

/** The reference pin's labels (Ex1 plot 527 it), shared by Ex6 and the A8 window cases. */
const EX1_527_IT_LABELS = '2:2 set | 6:6 set | 10:10 set | 14:14 set | 18:18 set | 22:22 set | 26:26 set | 30:30 set';

// WHY: every appendix input has this shape; a one-line builder keeps each pin row as readable as its heading.
function inputOf(closingDates: readonly string[], firstDate: string, [visibleStartIndex, visibleEndIndex]: readonly [number, number], plotWidthPx: number, locale: string, extra: Partial<LadderAxisInput> = {}): LadderAxisInput {
    return {closingDates, firstDate, visibleStartIndex, visibleEndIndex, plotWidthPx, locale, ...extra};
}

// WHY: the Ex1 family (31 daily closings, full window) is a third of the pins.
function ex1Input(plotWidthPx: number, locale: string, extra: Partial<LadderAxisInput> = {}): LadderAxisInput {
    return inputOf(EX1, '2026-08-31', [0, 30], plotWidthPx, locale, extra);
}

// =============================================================================
// Pin transcription and comparison
// =============================================================================

/** One appendix `####` case, transcribed. */
interface Pin {
    mode: LadderAxisMode;
    step: number;
    withYear: boolean;
    /** Appendix notation `i:text | j:text`: EVERY labelled bucket, visible or not; '' = none. */
    labels: string;
    /** 'all' = every closing date (ALL (n)); otherwise exactly these bucket indices. */
    separators: 'all' | readonly number[];
    /** [index, px] pairs; omitted = (none). */
    edgeShifts?: ReadonlyArray<readonly [number, number]>;
    keyEmpty: boolean;
    /** formatter(c[index]) of the shifted labels, where the appendix gives it. */
    formatted?: Readonly<Record<number, string>>;
    /** axisLabel.rich; omitted = `{}`. */
    rich?: Record<string, {padding: [number, number, number, number]}>;
}

interface PinRow {
    name: string;
    input: LadderAxisInput;
    /** Builder precondition [n, c[0], c[n-1]] as the appendix writes it; omitted for literal arrays. */
    fixture?: readonly [number, string, string];
    pin: Pin;
}

type PinExtra = (plan: LadderAxisPlan) => {actual: Record<string, unknown>; expected: Record<string, unknown>};

// WHY: labels are copied verbatim in the appendix's "i:text | j:text" notation, so a transcription slip shows as a diff against the appendix.
function parseLabels(spec: string): Array<[number, string]> {
    if (spec === '') return [];
    return spec.split(' | ').map((pair): [number, string] => {
        const colon = pair.indexOf(':');
        return [Number(pair.slice(0, colon)), pair.slice(colon + 1)];
    });
}

// WHY: a pin is only true of the fixture it was computed on, so the builder is checked before the planner is judged.
function expectFixture(closings: readonly string[], [n, first, last]: readonly [number, string, string]): void {
    expect({n: closings.length, first: closings[0], last: closings[closings.length - 1]}, 'fixture: the builder no longer produces the appendix closings').toEqual({n, first, last});
}

// WHY: one deep comparison per pin, so a red shows every field that differs (mode, step, year, labels, separators, shifts, key, rich) in one diff.
function expectPin(row: PinRow, extra?: PinExtra): void {
    if (row.fixture) expectFixture(row.input.closingDates, row.fixture);
    const c = row.input.closingDates;
    const {pin} = row;
    const plan = planLadderAxis(row.input);
    const option = ladderAxisOption(plan);
    const formattedAt = Object.keys(pin.formatted ?? {}).map(Number);
    const more = extra?.(plan) ?? {actual: {}, expected: {}};
    const actual = {
        mode: plan.mode,
        step: plan.step,
        withYear: plan.withYear,
        labels: plan.labels,
        separators: plan.separators,
        edgeShifts: plan.edgeShifts,
        keyIsEmpty: plan.key === '',
        formatted: Object.fromEntries(formattedAt.map((i) => [c[i], option.axisLabel.formatter(c[i])])),
        rich: option.axisLabel.rich,
        ...more.actual,
    };
    const expected = {
        mode: pin.mode,
        step: pin.step,
        withYear: pin.withYear,
        labels: new Map(parseLabels(pin.labels).map(([i, text]): [string, string] => [c[i], text])),
        separators: new Set(pin.separators === 'all' ? c : pin.separators.map((i) => c[i])),
        edgeShifts: new Map((pin.edgeShifts ?? []).map(([i, px]): [string, number] => [c[i], px])),
        keyIsEmpty: pin.keyEmpty,
        formatted: Object.fromEntries(formattedAt.map((i) => [c[i], pin.formatted?.[i]])),
        rich: pin.rich ?? {},
        ...more.expected,
    };
    expect(actual, `pin ${row.name}`).toEqual(expected);
}

// WHY: the three decisions a pan must not change, read off a plan in one object so two plans compare in one diff.
function decisions(plan: LadderAxisPlan): {mode: LadderAxisMode; step: number; withYear: boolean} {
    return {mode: plan.mode, step: plan.step, withYear: plan.withYear};
}

// =============================================================================
// A0 — ICU precondition
// =============================================================================

describe('A0 — ICU precondition (the label literals below are ICU 78.3 output)', () => {
    const MONTH_FIRSTS_2025 = Array.from({length: 12}, (_, m) => `2025-${String(m + 1).padStart(2, '0')}-01`);
    const DAY_MONTH_DATES = ['2026-09-02', '2026-09-30', '2026-08-31', '2024-12-01', '2026-05-03'];
    const DAY_MONTH_YEAR_DATES = ['2024-10-10', '2026-09-30'];
    const ICU_TABLE = [
        {locale: 'it', months: 'gen feb mar apr mag giu lug ago set ott nov dic'.split(' '), january25: 'gen 25', dayMonth: ['2 set', '30 set', '31 ago', '1 dic', '3 mag'], dayMonthYear: ['10 ott 24', '30 set 26']},
        {locale: 'en', months: 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' '), january25: 'Jan 25', dayMonth: ['Sep 2', 'Sep 30', 'Aug 31', 'Dec 1', 'May 3'], dayMonthYear: ['Oct 10, 24', 'Sep 30, 26']},
        {locale: 'fr', months: 'janv. févr. mars avr. mai juin juil. août sept. oct. nov. déc.'.split(' '), january25: 'janv. 25', dayMonth: ['2 sept.', '30 sept.', '31 août', '1 déc.', '3 mai'], dayMonthYear: ['10 oct. 24', '30 sept. 26']},
        {locale: 'es', months: 'ene feb mar abr may jun jul ago sept oct nov dic'.split(' '), january25: 'ene 25', dayMonth: ['2 sept', '30 sept', '31 ago', '1 dic', '3 may'], dayMonthYear: ['10 oct 24', '30 sept 26']},
    ];

    // WHY: every label literal in this file is ICU output; when this is red the environment changed and no planner red below can be trusted.
    it.each(ICU_TABLE)('$locale: month, day-month and two-digit-year texts', ({locale, ...expected}) => {
        // WHY: the exact call the brief's A0 table was produced with (UTC, midnight of the ISO day).
        const icu = (options: Intl.DateTimeFormatOptions, iso: string) => new Intl.DateTimeFormat(locale, {...options, timeZone: 'UTC'}).format(new Date(`${iso}T00:00:00Z`));
        const actual = {
            months: MONTH_FIRSTS_2025.map((iso) => icu({month: 'short'}, iso)),
            january25: icu({month: 'short', year: '2-digit'}, '2025-01-01'),
            dayMonth: DAY_MONTH_DATES.map((iso) => icu({day: 'numeric', month: 'short'}, iso)),
            dayMonthYear: DAY_MONTH_YEAR_DATES.map((iso) => icu({day: 'numeric', month: 'short', year: '2-digit'}, iso)),
        };
        const nonAsciiSpaces = Object.values(actual)
            .flat()
            .filter((text) => /[\u00a0\u202f]/.test(text));
        expect(nonAsciiSpaces, `ICU changed: ${locale} texts carry U+00A0 / U+202F where the pins use ASCII spaces`).toEqual([]);
        expect(actual, `ICU changed: ${locale} date texts differ from ICU 78.3 (Node 26.8.2)`).toEqual(expected);
    });
});

// =============================================================================
// A1 – A5 — single-plan pins
// =============================================================================

describe('A1 — closing mode, D4-bis thinning (31 daily buckets)', () => {
    const ROWS: PinRow[] = [
        // WHY: the reference pin — 31 daily closings on a desktop plot keep every 4th label, counted from the last bucket.
        {name: 'Ex1 plot 527 it', input: ex1Input(527, 'it'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 4, withYear: false, labels: EX1_527_IT_LABELS, separators: 'all', keyEmpty: false}},
        // WHY: English day-month texts fit the same step as Italian ones.
        {name: 'Ex1 plot 527 en', input: ex1Input(527, 'en'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 4, withYear: false, labels: '2:Sep 2 | 6:Sep 6 | 10:Sep 10 | 14:Sep 14 | 18:Sep 18 | 22:Sep 22 | 26:Sep 26 | 30:Sep 30', separators: 'all', keyEmpty: false}},
        // WHY: French "sept." is wider, so the step grows to 5 and the count from the last bucket reaches bucket 0.
        {name: 'Ex1 plot 527 fr', input: ex1Input(527, 'fr'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 5, withYear: false, labels: '0:31 août | 5:5 sept. | 10:10 sept. | 15:15 sept. | 20:20 sept. | 25:25 sept. | 30:30 sept.', separators: 'all', keyEmpty: false}},
        // WHY: Spanish "sept" (no dot) still fits every 4th bucket.
        {name: 'Ex1 plot 527 es', input: ex1Input(527, 'es'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 4, withYear: false, labels: '2:2 sept | 6:6 sept | 10:10 sept | 14:14 sept | 18:18 sept | 22:22 sept | 26:26 sept | 30:30 sept', separators: 'all', keyEmpty: false}},
        // WHY: a narrower plot thins further (step 7) while the last bucket keeps its label.
        {name: 'Ex1b plot 300 it', input: ex1Input(300, 'it'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 7, withYear: false, labels: '2:2 set | 9:9 set | 16:16 set | 23:23 set | 30:30 set', separators: 'all', keyEmpty: false}},
        // WHY: the same narrow plot in English lands on the same step.
        {name: 'Ex1b plot 300 en', input: ex1Input(300, 'en'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 7, withYear: false, labels: '2:Sep 2 | 9:Sep 9 | 16:Sep 16 | 23:Sep 23 | 30:Sep 30', separators: 'all', keyEmpty: false}},
    ];

    // WHY: each row is one appendix case — the D4-bis step and the labels it keeps are the contract.
    it.each(ROWS)('$name', (row) => expectPin(row));
});

describe('A2 — phone plot 327, without and with rooms', () => {
    const ROOMS_L40_R12 = {leftRoomPx: 40, rightRoomPx: 12};
    const ROWS: PinRow[] = [
        // WHY: a phone plot without rooms: step 6, and the count from the last bucket reaches bucket 0.
        {name: 'Phone 327 it no rooms', input: ex1Input(327, 'it'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 6, withYear: false, labels: '0:31 ago | 6:6 set | 12:12 set | 18:18 set | 24:24 set | 30:30 set', separators: 'all', keyEmpty: false}},
        // WHY: English on the phone plot, same step as Italian.
        {name: 'Phone 327 en no rooms', input: ex1Input(327, 'en'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 6, withYear: false, labels: '0:Aug 31 | 6:Sep 6 | 12:Sep 12 | 18:Sep 18 | 24:Sep 24 | 30:Sep 30', separators: 'all', keyEmpty: false}},
        // WHY: French on the phone plot needs step 8.
        {name: 'Phone 327 fr no rooms', input: ex1Input(327, 'fr'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 8, withYear: false, labels: '6:6 sept. | 14:14 sept. | 22:22 sept. | 30:30 sept.', separators: 'all', keyEmpty: false}},
        // WHY: Spanish on the phone plot needs step 7.
        {name: 'Phone 327 es no rooms', input: ex1Input(327, 'es'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 7, withYear: false, labels: '2:2 sept | 9:9 sept | 16:16 sept | 23:23 sept | 30:30 sept', separators: 'all', keyEmpty: false}},
        // WHY: a 12 px right room moves the last label 10 px left, and that shift costs a step (6 → 7) because fit includes shifts.
        {
            name: 'Phone 327 it rooms L40 R12',
            input: ex1Input(327, 'it', ROOMS_L40_R12),
            fixture: EX1_FIXTURE,
            pin: {mode: 'closing', step: 7, withYear: false, labels: '2:2 set | 9:9 set | 16:16 set | 23:23 set | 30:30 set', separators: 'all', edgeShifts: [[30, -10]], keyEmpty: false, formatted: {30: '{lfShiftL10|30 set}'}, rich: {lfShiftL10: {padding: [0, 20, 0, 0]}}},
        },
        // WHY: the same right-edge shift in English, rendered through the rich-text padding style.
        {
            name: 'Phone 327 en rooms L40 R12',
            input: ex1Input(327, 'en', ROOMS_L40_R12),
            fixture: EX1_FIXTURE,
            pin: {mode: 'closing', step: 7, withYear: false, labels: '2:Sep 2 | 9:Sep 9 | 16:Sep 16 | 23:Sep 23 | 30:Sep 30', separators: 'all', edgeShifts: [[30, -10]], keyEmpty: false, formatted: {30: '{lfShiftL10|Sep 30}'}, rich: {lfShiftL10: {padding: [0, 20, 0, 0]}}},
        },
        // WHY: the wider French label needs a 19 px shift and step 9.
        {
            name: 'Phone 327 fr rooms L40 R12',
            input: ex1Input(327, 'fr', ROOMS_L40_R12),
            fixture: EX1_FIXTURE,
            pin: {mode: 'closing', step: 9, withYear: false, labels: '3:3 sept. | 12:12 sept. | 21:21 sept. | 30:30 sept.', separators: 'all', edgeShifts: [[30, -19]], keyEmpty: false, formatted: {30: '{lfShiftL19|30 sept.}'}, rich: {lfShiftL19: {padding: [0, 38, 0, 0]}}},
        },
        // WHY: Spanish with rooms: a 15 px shift and step 8.
        {
            name: 'Phone 327 es rooms L40 R12',
            input: ex1Input(327, 'es', ROOMS_L40_R12),
            fixture: EX1_FIXTURE,
            pin: {mode: 'closing', step: 8, withYear: false, labels: '6:6 sept | 14:14 sept | 22:22 sept | 30:30 sept', separators: 'all', edgeShifts: [[30, -15]], keyEmpty: false, formatted: {30: '{lfShiftL15|30 sept}'}, rich: {lfShiftL15: {padding: [0, 30, 0, 0]}}},
        },
    ];

    // WHY: each row is one appendix case — rooms change the step only through the edge shift they force.
    it.each(ROWS)('$name', (row) => expectPin(row));
});

describe('A3 — month mode', () => {
    const ROWS: PinRow[] = [
        // WHY: weekly buckets over six months: one short month name on the bucket holding each 1st.
        {name: 'Ex2 plot 527 it', input: inputOf(EX2, '2026-03-31', [0, 26], 527, 'it'), fixture: EX2_FIXTURE, pin: {mode: 'month', step: 1, withYear: false, labels: '0:apr | 5:mag | 9:giu | 13:lug | 18:ago | 22:set', separators: 'all', keyEmpty: false}},
        // WHY: the same month labels in English.
        {name: 'Ex2 plot 527 en', input: inputOf(EX2, '2026-03-31', [0, 26], 527, 'en'), fixture: EX2_FIXTURE, pin: {mode: 'month', step: 1, withYear: false, labels: '0:Apr | 5:May | 9:Jun | 13:Jul | 18:Aug | 22:Sep', separators: 'all', keyEmpty: false}},
        // WHY: with no room at all, the first label moves 5 px right (a positive shift, left padding in the rich style).
        {
            name: 'Ex2 plot 527 it rooms L0 R0',
            input: inputOf(EX2, '2026-03-31', [0, 26], 527, 'it', {leftRoomPx: 0, rightRoomPx: 0}),
            fixture: EX2_FIXTURE,
            pin: {mode: 'month', step: 1, withYear: false, labels: '0:apr | 5:mag | 9:giu | 13:lug | 18:ago | 22:set', separators: 'all', edgeShifts: [[0, 5]], keyEmpty: false, formatted: {0: '{lfShiftR5|apr}'}, rich: {lfShiftR5: {padding: [0, 0, 0, 10]}}},
        },
        // WHY: 92 daily slots are narrower than 8 px, so separators remain only on the buckets holding a 1st.
        {name: 'Ex3 plot 527 it', input: inputOf(EX3, '2026-06-25', [0, 91], 527, 'it'), fixture: EX3_FIXTURE, pin: {mode: 'month', step: 1, withYear: false, labels: '6:lug | 37:ago | 68:set', separators: [6, 37, 68], keyEmpty: false}},
        // WHY: the same separators and month labels in English.
        {name: 'Ex3 plot 527 en', input: inputOf(EX3, '2026-06-25', [0, 91], 527, 'en'), fixture: EX3_FIXTURE, pin: {mode: 'month', step: 1, withYear: false, labels: '6:Jul | 37:Aug | 68:Sep', separators: [6, 37, 68], keyEmpty: false}},
        // WHY: bucket 3 holds two 1sts and carries the earliest; January carries its year although withYear is false.
        {name: 'Ex4 plot 327 it', input: inputOf(EX4, '2024-11-02', [0, 6], 327, 'it'), fixture: EX4_FIXTURE, pin: {mode: 'month', step: 1, withYear: false, labels: '0:dic | 2:gen 25 | 3:feb | 5:apr | 6:mag', separators: 'all', keyEmpty: false}},
        // WHY: the same rules in English.
        {name: 'Ex4 plot 327 en', input: inputOf(EX4, '2024-11-02', [0, 6], 327, 'en'), fixture: EX4_FIXTURE, pin: {mode: 'month', step: 1, withYear: false, labels: '0:Dec | 2:Jan 25 | 3:Feb | 5:Apr | 6:May', separators: 'all', keyEmpty: false}},
        // WHY: wider French names force quarterly thinning, aligned on the calendar (January, April).
        {name: 'Ex4 plot 327 fr', input: inputOf(EX4, '2024-11-02', [0, 6], 327, 'fr'), fixture: EX4_FIXTURE, pin: {mode: 'month', step: 3, withYear: false, labels: '2:janv. 25 | 5:avr.', separators: 'all', keyEmpty: false}},
        // WHY: on a wider plot every closing date fits, so closing mode with step 1 wins over month names.
        {name: 'Ex4 plot 527 it', input: inputOf(EX4, '2024-11-02', [0, 6], 527, 'it'), fixture: EX4_FIXTURE, pin: {mode: 'closing', step: 1, withYear: false, labels: '0:1 dic | 1:31 dic | 2:30 gen | 3:1 mar | 4:31 mar | 5:30 apr | 6:30 mag', separators: 'all', keyEmpty: false}},
        // WHY: the same closing labels in English.
        {name: 'Ex4 plot 527 en', input: inputOf(EX4, '2024-11-02', [0, 6], 527, 'en'), fixture: EX4_FIXTURE, pin: {mode: 'closing', step: 1, withYear: false, labels: '0:Dec 1 | 1:Dec 31 | 2:Jan 30 | 3:Mar 1 | 4:Mar 31 | 5:Apr 30 | 6:May 30', separators: 'all', keyEmpty: false}},
    ];

    // WHY: each row is one appendix case — month mode, its calendar-aligned thinning and the January rule.
    it.each(ROWS)('$name', (row) => expectPin(row));
});

describe('A4 — the year threshold', () => {
    const ROWS: PinRow[] = [
        // WHY: a window of exactly 365 inclusive days puts the year on every label.
        {
            name: 'Ex5 [0..52] plot 1100 it (365 days: year on)',
            input: inputOf(EX5, '2025-10-01', [0, 52], 1100, 'it'),
            fixture: EX5_FIXTURE,
            pin: {mode: 'month', step: 1, withYear: true, labels: '0:ott 25 | 5:nov 25 | 9:dic 25 | 14:gen 26 | 18:feb 26 | 22:mar 26 | 26:apr 26 | 31:mag 26 | 35:giu 26 | 39:lug 26 | 44:ago 26 | 48:set 26', separators: 'all', keyEmpty: false},
        },
        // WHY: one bucket less and the year goes, except on January; hidden bucket 0 still carries its label.
        {
            name: 'Ex5 [1..52] plot 1100 it (year off, January keeps it)',
            input: inputOf(EX5, '2025-10-01', [1, 52], 1100, 'it'),
            fixture: EX5_FIXTURE,
            pin: {mode: 'month', step: 1, withYear: false, labels: '0:ott | 5:nov | 9:dic | 14:gen 26 | 18:feb | 22:mar | 26:apr | 31:mag | 35:giu | 39:lug | 44:ago | 48:set', separators: 'all', keyEmpty: false},
        },
        // WHY: with the year on, a desktop plot thins months to every 2nd, aligned on odd-numbered months from January.
        {name: 'Ex5 [0..52] plot 527 en', input: inputOf(EX5, '2025-10-01', [0, 52], 527, 'en'), fixture: EX5_FIXTURE, pin: {mode: 'month', step: 2, withYear: true, labels: '5:Nov 25 | 14:Jan 26 | 22:Mar 26 | 31:May 26 | 39:Jul 26 | 48:Sep 26', separators: 'all', keyEmpty: false}},
    ];

    // WHY: each row is one appendix case — the 365-day threshold, counted from the covered start of the first visible bucket.
    it.each(ROWS)('$name', (row) => expectPin(row));
});

describe('A5 — edge shifts', () => {
    const ROWS: PinRow[] = [
        // WHY: on a desktop plot the last label overflows a 12 px room by 7 px and moves left without costing a step.
        {
            name: 'Ex6 = Ex1 plot 527 it rooms L40 R12',
            input: ex1Input(527, 'it', {leftRoomPx: 40, rightRoomPx: 12}),
            fixture: EX1_FIXTURE,
            pin: {mode: 'closing', step: 4, withYear: false, labels: EX1_527_IT_LABELS, separators: 'all', edgeShifts: [[30, -7]], keyEmpty: false, formatted: {30: '{lfShiftL7|30 set}'}, rich: {lfShiftL7: {padding: [0, 14, 0, 0]}}},
        },
        // WHY: with no room on either side both edge labels move inward, one rich style per direction.
        {
            name: 'Ex1 plot 527 it rooms L0 R0 (both edges move)',
            input: ex1Input(527, 'it', {leftRoomPx: 0, rightRoomPx: 0}),
            fixture: EX1_FIXTURE,
            pin: {
                mode: 'closing',
                step: 5,
                withYear: false,
                labels: '0:31 ago | 5:5 set | 10:10 set | 15:15 set | 20:20 set | 25:25 set | 30:30 set',
                separators: 'all',
                edgeShifts: [
                    [0, 19],
                    [30, -19],
                ],
                keyEmpty: false,
                formatted: {0: '{lfShiftR19|31 ago}', 30: '{lfShiftL19|30 set}'},
                rich: {lfShiftR19: {padding: [0, 0, 0, 38]}, lfShiftL19: {padding: [0, 38, 0, 0]}},
            },
        },
    ];

    // WHY: each row is one appendix case — the smallest whole-px inward move, expressed as rich-text padding.
    it.each(ROWS)('$name', (row) => expectPin(row));
});

// =============================================================================
// A6 – A7 — windows and rungs on two years
// =============================================================================

describe('A6 — pan and zoom windows on two years', () => {
    // WHY: a pan by one bucket must keep the decisions and the key, or the axis would be re-applied on every pan step; equal keys alone pass on the stub, so the mode is asserted too.
    it('Ex7 endAnchored(2024-10-01, 2026-09-30, 7), plot 527 it: [10..40] vs [11..41]', () => {
        const c = twoYears(7);
        expectFixture(c, [105, '2024-10-02', '2026-09-30']);
        const before = planLadderAxis(inputOf(c, '2024-10-01', [10, 40], 527, 'it'));
        const after = planLadderAxis(inputOf(c, '2024-10-01', [11, 41], 527, 'it'));
        expect({before: decisions(before), after: decisions(after), keysEqual: before.key === after.key}, 'pin Ex7').toEqual({
            before: {mode: 'month', step: 1, withYear: false},
            after: {mode: 'month', step: 1, withYear: false},
            keysEqual: true,
        });
    });

    const ROWS: PinRow[] = [
        // WHY: two years of monthly buckets: quarterly months, the year on every label.
        {
            name: 'Ex8 full plot 527 it',
            input: inputOf(twoYears(30), '2024-10-01', [0, 24], 527, 'it'),
            fixture: [25, '2024-10-10', '2026-09-30'],
            pin: {mode: 'month', step: 3, withYear: true, labels: '0:ott 24 | 3:gen 25 | 6:apr 25 | 9:lug 25 | 12:ott 25 | 15:gen 26 | 18:apr 26 | 21:lug 26', separators: 'all', keyEmpty: false},
        },
        // WHY: zoomed on the last six buckets every closing fits, and the labels exist for all 25 buckets so a pan does not make them swim.
        {
            name: 'Ex8 [19..24] plot 527 it',
            input: inputOf(twoYears(30), '2024-10-01', [19, 24], 527, 'it'),
            fixture: [25, '2024-10-10', '2026-09-30'],
            pin: {
                mode: 'closing',
                step: 1,
                withYear: false,
                labels: '0:10 ott | 1:9 nov | 2:9 dic | 3:8 gen | 4:7 feb | 5:9 mar | 6:8 apr | 7:8 mag | 8:7 giu | 9:7 lug | 10:6 ago | 11:5 set | 12:5 ott | 13:4 nov | 14:4 dic | 15:3 gen | 16:2 feb | 17:4 mar | 18:3 apr | 19:3 mag | 20:2 giu | 21:2 lug | 22:1 ago | 23:31 ago | 24:30 set',
                separators: 'all',
                keyEmpty: false,
            },
        },
    ];

    // WHY: each row is one appendix case — decisions on the visible window, labels on every bucket.
    it.each(ROWS)('$name', (row) => expectPin(row));
});

describe('A7 — two years, en, plot 527: every rung (identical with rooms L40 R633)', () => {
    const ROWS: PinRow[] = [
        // WHY: 105 weekly slots are under 8 px, so separators remain only on the 24 buckets holding a 1st.
        {
            name: '730d 1W plot 527 en',
            input: inputOf(twoYears(7), '2024-10-01', [0, 104], 527, 'en'),
            fixture: [105, '2024-10-02', '2026-09-30'],
            pin: {
                mode: 'month',
                step: 3,
                withYear: true,
                labels: '0:Oct 24 | 13:Jan 25 | 26:Apr 25 | 39:Jul 25 | 52:Oct 25 | 66:Jan 26 | 78:Apr 26 | 91:Jul 26',
                separators: [0, 5, 9, 13, 18, 22, 26, 31, 35, 39, 44, 48, 52, 57, 61, 66, 70, 74, 78, 83, 87, 91, 96, 100],
                keyEmpty: false,
            },
        },
        // WHY: 2W keeps quarterly labels, and its slots are wide enough for a separator on every bucket.
        {
            name: '730d 2W plot 527 en',
            input: inputOf(twoYears(14), '2024-10-01', [0, 52], 527, 'en'),
            fixture: [53, '2024-10-02', '2026-09-30'],
            pin: {mode: 'month', step: 3, withYear: true, labels: '0:Oct 24 | 7:Jan 25 | 13:Apr 25 | 20:Jul 25 | 26:Oct 25 | 33:Jan 26 | 39:Apr 26 | 46:Jul 26', separators: 'all', keyEmpty: false},
        },
        // WHY: 1M: quarterly labels on monthly buckets.
        {
            name: '730d 1M plot 527 en',
            input: inputOf(twoYears(30), '2024-10-01', [0, 24], 527, 'en'),
            fixture: [25, '2024-10-10', '2026-09-30'],
            pin: {mode: 'month', step: 3, withYear: true, labels: '0:Oct 24 | 3:Jan 25 | 6:Apr 25 | 9:Jul 25 | 12:Oct 25 | 15:Jan 26 | 18:Apr 26 | 21:Jul 26', separators: 'all', keyEmpty: false},
        },
        // WHY: 3M: every bucket holds a 1st and names its earliest month.
        {
            name: '730d 3M plot 527 en',
            input: inputOf(twoYears(90), '2024-10-01', [0, 8], 527, 'en'),
            fixture: [9, '2024-10-10', '2026-09-30'],
            pin: {mode: 'month', step: 1, withYear: true, labels: '0:Oct 24 | 1:Nov 24 | 2:Feb 25 | 3:May 25 | 4:Aug 25 | 5:Nov 25 | 6:Feb 26 | 7:May 26 | 8:Aug 26', separators: 'all', keyEmpty: false},
        },
        // WHY: 6M: five closings fit, so each carries its full date with the year.
        {
            name: '730d 6M plot 527 en',
            input: inputOf(twoYears(180), '2024-10-01', [0, 4], 527, 'en'),
            fixture: [5, '2024-10-10', '2026-09-30'],
            pin: {mode: 'closing', step: 1, withYear: true, labels: '0:Oct 10, 24 | 1:Apr 8, 25 | 2:Oct 5, 25 | 3:Apr 3, 26 | 4:Sep 30, 26', separators: 'all', keyEmpty: false},
        },
    ];

    // WHY: each row is one appendix case; generous rooms (L40 R633) need no shift, so the plan and therefore its key must not change.
    it.each(ROWS)('$name', (row) =>
        expectPin(row, (plan) => ({
            actual: {keyIdenticalWithRoomsL40R633: planLadderAxis({...row.input, leftRoomPx: 40, rightRoomPx: 633}).key === plan.key},
            expected: {keyIdenticalWithRoomsL40R633: true},
        })),
    );
});

// =============================================================================
// A8 — edges and degenerate inputs
// =============================================================================

describe('A8 — edges and degenerate inputs', () => {
    const EMPTY_PIN: Pin = {mode: 'closing', step: 1, withYear: false, labels: '', separators: [], keyEmpty: true};
    const CONTRACT_ROWS: PinRow[] = [
        // WHY: no buckets, no plan.
        {name: 'Empty', input: inputOf([], '2026-09-30', [0, 0], 527, 'it'), pin: {...EMPTY_PIN, separators: 'all'}},
        // WHY: a zero-width plot means the grid has not been measured yet.
        {name: 'Ex1 it plot 0 (geometry not measured)', input: ex1Input(0, 'it'), fixture: EX1_FIXTURE, pin: EMPTY_PIN},
        // WHY: a negative width is not a measurement either.
        {name: 'Ex1 it plot -5 (geometry not measured)', input: ex1Input(-5, 'it'), fixture: EX1_FIXTURE, pin: EMPTY_PIN},
        // WHY: NaN (the number) is what a failed read of the grid rect produces.
        {name: 'Ex1 it plot NaN (geometry not measured)', input: ex1Input(NaN, 'it'), fixture: EX1_FIXTURE, pin: EMPTY_PIN},
        // WHY: Infinity is not a finite measurement.
        {name: 'Ex1 it plot Infinity (geometry not measured)', input: ex1Input(Infinity, 'it'), fixture: EX1_FIXTURE, pin: EMPTY_PIN},
    ];

    // WHY: GREEN on the stub by design — these pin the contract line (no buckets, or geometry not measured → the empty plan, key ''); they are not reds.
    it.each(CONTRACT_ROWS)('$name', (row) => expectPin(row));

    const SINGLE_ROWS: PinRow[] = [
        // WHY: one bucket, one closing label, one separator.
        {name: 'Single bucket, no rooms', input: inputOf(['2026-09-30'], '2026-09-24', [0, 0], 527, 'it'), pin: {mode: 'closing', step: 1, withYear: false, labels: '0:30 set', separators: 'all', keyEmpty: false}},
        // WHY: a centred label on a 527 px plot is nowhere near either edge, so rooms add no shift.
        {name: 'Single bucket, rooms L40 R12', input: inputOf(['2026-09-30'], '2026-09-24', [0, 0], 527, 'it', {leftRoomPx: 40, rightRoomPx: 12}), pin: {mode: 'closing', step: 1, withYear: false, labels: '0:30 set', separators: 'all', keyEmpty: false}},
    ];

    // WHY: each row is one appendix case — the smallest non-empty series.
    it.each(SINGLE_ROWS)('$name', (row) => expectPin(row));

    // WHY: ECharts hands over reversed, out-of-range and fractional windows; they must plan like the full window, and the label map is the witness because two empty plans would also compare equal on the stub.
    it('Ex1 plot 527 it, windows (30,0) reversed, (-5,99) out of range, (0.4,29.6) fractional', () => {
        expectFixture(EX1, EX1_FIXTURE);
        const full = planLadderAxis(ex1Input(527, 'it'));
        const windows: ReadonlyArray<readonly [number, number]> = [
            [30, 0],
            [-5, 99],
            [0.4, 29.6],
        ];
        const actual = windows.map((win) => {
            const plan = planLadderAxis(ex1Input(527, 'it', {visibleStartIndex: win[0], visibleEndIndex: win[1]}));
            return {win, ...decisions(plan), labels: plan.labels, separators: plan.separators, edgeShifts: plan.edgeShifts, keyEqualsFullWindow: plan.key === full.key};
        });
        const expected = windows.map((win) => ({
            win,
            mode: 'closing',
            step: 4,
            withYear: false,
            labels: new Map(parseLabels(EX1_527_IT_LABELS).map(([i, text]): [string, string] => [EX1[i], text])),
            separators: new Set(EX1),
            edgeShifts: new Map(),
            keyEqualsFullWindow: true,
        }));
        expect(actual, 'pin Ex1 plot 527 it, windows').toEqual(expected);
    });

    const GEOMETRY_ROWS: PinRow[] = [
        // WHY: 12 px labels are narrower than the default 14 px ones, so the same plot fits step 6 where 14 px needs 7.
        {name: 'Ex1b plot 300 it, fontSizePx 12', input: ex1Input(300, 'it', {fontSizePx: 12}), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 6, withYear: false, labels: '0:31 ago | 6:6 set | 12:12 set | 18:18 set | 24:24 set | 30:30 set', separators: 'all', keyEmpty: false}},
        // WHY: a 40 px plot is the degenerate stop: only the last bucket keeps a label; slots are under 8 px and the only visible 1st is in bucket 1 (1 Sep), which is not the first visible bucket, so bucket 0 carries the anchor (30/09).
        {name: 'Ex1 plot 40 it (degenerate geometry)', input: ex1Input(40, 'it'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 31, withYear: false, labels: '30:30 set', separators: [0, 1], keyEmpty: false}},
    ];

    // WHY: each row is one appendix case — the label width and the plot width both drive the step.
    it.each(GEOMETRY_ROWS)('$name', (row) => expectPin(row));
});

// =============================================================================
// A8-bis — addendum: the anchor separator (30/09)
// =============================================================================

describe('A8-bis — addendum: the anchor separator (30/09)', () => {
    const ANCHOR_ROWS: PinRow[] = [
        // WHY: exactly one visible 1st (bucket 15 = 1 Sep), not on the first visible bucket, so bucket 0 carries the anchor; slot 327/45 = 7.27 px.
        {
            name: 'Anchor: daily 17 Aug–30 Sep plot 327 it',
            input: inputOf(daily('2026-08-17', '2026-09-30'), '2026-08-17', [0, 44], 327, 'it'),
            fixture: [45, '2026-08-17', '2026-09-30'],
            pin: {mode: 'closing', step: 9, withYear: false, labels: '8:25 ago | 17:3 set | 26:12 set | 35:21 set | 44:30 set', separators: [0, 15], keyEmpty: false},
        },
        // WHY: the same input in English — the anchor follows the calendar, never the locale.
        {
            name: 'Anchor: daily 17 Aug–30 Sep plot 327 en',
            input: inputOf(daily('2026-08-17', '2026-09-30'), '2026-08-17', [0, 44], 327, 'en'),
            fixture: [45, '2026-08-17', '2026-09-30'],
            pin: {mode: 'closing', step: 9, withYear: false, labels: '8:Aug 25 | 17:Sep 3 | 26:Sep 12 | 35:Sep 21 | 44:Sep 30', separators: [0, 15], keyEmpty: false},
        },
        // WHY: two visible 1sts (12 = 1 Aug, 43 = 1 Sep) already make two ticks, so no anchor.
        {
            name: 'No anchor: two visible 1sts, daily 20 Jul–30 Sep plot 327 it',
            input: inputOf(daily('2026-07-20', '2026-09-30'), '2026-07-20', [0, 72], 327, 'it'),
            fixture: [73, '2026-07-20', '2026-09-30'],
            pin: {mode: 'month', step: 1, withYear: false, labels: '12:ago | 43:set', separators: [12, 43], keyEmpty: false},
        },
        // WHY: the only visible 1st is on the first visible bucket (0 = 1 Sep), whose left edge is the plot edge anyway, so no anchor.
        {
            name: 'No anchor: the 1st is on the first visible bucket, daily 1–30 Sep plot 200 it',
            input: inputOf(daily('2026-09-01', '2026-09-30'), '2026-09-01', [0, 29], 200, 'it'),
            fixture: [30, '2026-09-01', '2026-09-30'],
            pin: {mode: 'closing', step: 9, withYear: false, labels: '2:3 set | 11:12 set | 20:21 set | 29:30 set', separators: [0], keyEmpty: false},
        },
        // WHY: window [1, 30] starts on 1 Sep, so the only visible 1st sits on the first visible bucket: no anchor, bucket 0 loses the separator the full window gives it.
        {name: 'No anchor: Ex1 window [1, 30] plot 40 it', input: inputOf(EX1, '2026-08-31', [1, 30], 40, 'it'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 30, withYear: false, labels: '0:31 ago | 30:30 set', separators: [1], keyEmpty: false}},
        // WHY: window [2, 30] holds no 1st, so no anchor; the only separator is the off-window 1 Sep (bucket 1).
        {name: 'No anchor: no visible 1st, Ex1 window [2, 30] plot 40 it', input: inputOf(EX1, '2026-08-31', [2, 30], 40, 'it'), fixture: EX1_FIXTURE, pin: {mode: 'closing', step: 29, withYear: false, labels: '1:1 set | 30:30 set', separators: [1], keyEmpty: false}},
        // WHY: zoomed Ex3 — the only visible 1st is bucket 68 (1 Sep), so the first visible bucket 44 carries the anchor; 6 and 37 are the off-window 1 Jul / 1 Aug.
        {
            name: 'Anchor in a zoomed window: Ex3 [44, 91] plot 327 it',
            input: inputOf(EX3, '2026-06-25', [44, 91], 327, 'it'),
            fixture: EX3_FIXTURE,
            pin: {mode: 'closing', step: 9, withYear: false, labels: '1:26 giu | 10:5 lug | 19:14 lug | 28:23 lug | 37:1 ago | 46:10 ago | 55:19 ago | 64:28 ago | 73:6 set | 82:15 set | 91:24 set', separators: [6, 37, 44, 68], keyEmpty: false},
        },
    ];

    // WHY: each row is one addendum case — the anchor fires only when exactly one visible bucket holds a 1st and it is not the first visible bucket.
    it.each(ANCHOR_ROWS)('$name', (row) => expectPin(row));
});

// =============================================================================
// A9 — determinism, the option probe, the width estimate
// =============================================================================

describe('A9 — determinism and the option probe', () => {
    // WHY: the component re-applies the axis only when the key changes, so the key must be a pure function of the content and must see the locale.
    it('determinism: the same input twice gives equal non-empty keys; it and en differ', () => {
        const first = planLadderAxis(ex1Input(527, 'it'));
        const again = planLadderAxis({...ex1Input(527, 'it'), closingDates: [...EX1]});
        const english = planLadderAxis(ex1Input(527, 'en'));
        expect({sameKey: first.key === again.key, nonEmpty: first.key !== '', itAndEnDiffer: first.key !== english.key}, 'A9 determinism').toEqual({sameKey: true, nonEmpty: true, itAndEnDiffer: true});
    });

    // WHY: ECharts calls interval(index, rawValue); the plan is keyed by the raw closing date, so the index argument must not matter.
    it('option probe on Ex1 plot 527 it: interval, formatter, rich and splitLine read the raw value', () => {
        const option = ladderAxisOption(planLadderAxis(ex1Input(527, 'it')));
        expect(
            {
                labelIntervalAt0ForC2: option.axisLabel.interval(0, EX1[2]),
                labelIntervalAt2ForC0: option.axisLabel.interval(2, EX1[0]),
                formatterC1: option.axisLabel.formatter(EX1[1]),
                formatterC2: option.axisLabel.formatter(EX1[2]),
                rich: option.axisLabel.rich,
                splitLineIntervalAt0ForC3: option.splitLine.interval(0, EX1[3]),
            },
            'A9 option probe',
        ).toEqual({labelIntervalAt0ForC2: true, labelIntervalAt2ForC0: false, formatterC1: '', formatterC2: '2 set', rich: {}, splitLineIntervalAt0ForC3: true});
    });

    // WHY: GREEN on the stub — the estimate is real today; every fit decision in the pins rests on 0.6 em per character.
    it('estimate: 0.6 × font size per character (14 px default, 12 px on request)', () => {
        expect(estimateLadderLabelWidthPx('30 set')).toBeCloseTo(50.4);
        expect(estimateLadderLabelWidthPx('30 set', 12)).toBeCloseTo(43.2);
    });
});

// =============================================================================
// A10 — the sweep: every plan against an independent oracle
// =============================================================================

const SWEEP_FIRST = '2024-10-01';
const SWEEP_LAST = '2026-09-30';
const SWEEP_SPANS = [1, 3, 7, 14, 30, 90, 180, 365];
const SWEEP_PLOTS = [327, 527, 1100];
const SWEEP_LOCALES = ['it', 'en', 'fr', 'es'];

interface SweepRooms {
    tag: string;
    left?: number;
    right?: number;
}

const SWEEP_ROOMS: readonly SweepRooms[] = [{tag: 'noRooms'}, {tag: 'L40R12', left: 40, right: 12}, {tag: 'L0R0', left: 0, right: 0}];

const SWEEP_WINDOWS: ReadonlyArray<{tag: string; of: (n: number) => [number, number]}> = [
    {tag: 'full', of: (n) => [0, n - 1]},
    {tag: 'last30', of: (n) => [Math.floor(0.7 * n), n - 1]},
    {tag: 'first30', of: (n) => [0, Math.ceil(0.3 * n) - 1]},
    {tag: 'mid50', of: (n) => [Math.floor(0.25 * n), Math.floor(0.75 * n)]},
    {tag: 'last2', of: (n) => [Math.max(0, n - 2), n - 1]},
    {tag: 'single', of: (n) => [n - 1, n - 1]},
    {tag: 'reversed', of: (n) => [n - 1, 0]},
    {tag: 'outOfRange', of: (n) => [-5, n + 5]},
    {tag: 'last31', of: (n) => [Math.max(0, n - 31), n - 1]},
    {tag: 'last45', of: (n) => [Math.max(0, n - 45), n - 1]},
    {tag: 'last20', of: (n) => [Math.max(0, n - 20), n - 1]},
];

type OracleStyle = 'closing' | 'closingYear' | 'month' | 'monthYear';

const ORACLE_OPTIONS: Record<OracleStyle, Intl.DateTimeFormatOptions> = {
    closing: {day: 'numeric', month: 'short'},
    closingYear: {day: 'numeric', month: 'short', year: '2-digit'},
    month: {month: 'short'},
    monthYear: {month: 'short', year: '2-digit'},
};

const oracleFormatters = new Map<string, Intl.DateTimeFormat>();
const oracleTexts = new Map<string, string>();

// WHY: the oracle's own Intl texts, cached by locale + options: uncached, 3168 plans × up to 730 buckets take ~26 s.
function oracleText(locale: string, style: OracleStyle, iso: string): string {
    const textKey = `${locale}|${style}|${iso}`;
    const cached = oracleTexts.get(textKey);
    if (cached !== undefined) return cached;
    const formatterKey = locale + JSON.stringify(ORACLE_OPTIONS[style]);
    let formatter = oracleFormatters.get(formatterKey);
    if (!formatter) {
        formatter = new Intl.DateTimeFormat(locale, {...ORACLE_OPTIONS[style], timeZone: 'UTC'});
        oracleFormatters.set(formatterKey, formatter);
    }
    const text = formatter.format(new Date(`${iso}T00:00:00Z`));
    oracleTexts.set(textKey, text);
    return text;
}

interface SweepFirst {
    iso: string;
    year: number;
    month0: number;
}

interface SweepSeries {
    span: number;
    closings: string[];
    closingSet: Set<string>;
    startDay: number[];
    endDay: number[];
    /** The 1sts inside each bucket's covered range, oldest first. */
    firsts: SweepFirst[][];
}

// WHY: each bucket's covered days and the 1sts inside them are the oracle's ground truth, derived from the calendar alone.
function sweepSeries(span: number): SweepSeries {
    const closings = endAnchored(SWEEP_FIRST, SWEEP_LAST, span);
    const endDay = closings.map(toDay);
    const startDay: number[] = [];
    const firsts: SweepFirst[][] = [];
    for (let i = 0; i < closings.length; i++) {
        startDay.push(i === 0 ? toDay(SWEEP_FIRST) : endDay[i - 1] + 1);
        const found: SweepFirst[] = [];
        for (let day = startDay[i]; day <= endDay[i]; day++) {
            const date = new Date(day * DAY_MS);
            if (date.getUTCDate() === 1) found.push({iso: fromDay(day), year: date.getUTCFullYear(), month0: date.getUTCMonth()});
        }
        firsts.push(found);
    }
    return {span, closings, closingSet: new Set(closings), startDay, endDay, firsts};
}

interface SweepCase {
    series: SweepSeries;
    /** The window clamped to [0, n-1] and swapped if reversed. */
    vs: number;
    ve: number;
    plot: number;
    locale: string;
    rooms: SweepRooms;
}

// WHY: "the smallest whole number of px" is a ceil of a float sum; within EPS of an integer it may round either way depending on evaluation order, so both are accepted.
function shiftCandidates(overflowPx: number): number[] {
    return [...new Set([Math.max(0, Math.ceil(overflowPx - EPS)), Math.max(0, Math.ceil(overflowPx + EPS))])];
}

// WHY: the 30/09 anchor from the oracle's own firsts, never from the plan — ECharts 6 moves a lone band tick to the axis start, so a lone visible 1st off the first visible bucket needs a second tick there; -1 = no anchor.
function oracleAnchor(sc: SweepCase): number {
    if (sc.plot / (sc.ve - sc.vs + 1) >= CANDLE_MIN_SLOT_PX) return -1;
    let visibleFirsts = 0;
    for (let i = sc.vs; i <= sc.ve; i++) if (sc.series.firsts[i].length > 0) visibleFirsts++;
    return visibleFirsts === 1 && sc.series.firsts[sc.vs].length === 0 ? sc.vs : -1;
}

// WHY: the sweep's oracle — every property re-derived from the contract, the calendar and Intl, never from the planner; at most one failure per property per case.
function checkPlan(sc: SweepCase, plan: LadderAxisPlan, option: LadderAxisOption): Array<{prop: string; detail: string}> {
    const out: Array<{prop: string; detail: string}> = [];
    // WHY: one failure per property per case keeps a broken planner's report readable (the first 20 lines stay informative).
    const fail = (prop: string, detail: string) => {
        if (!out.some((f) => f.prop === prop)) out.push({prop, detail});
    };
    const {closings: c, closingSet, startDay, endDay, firsts} = sc.series;
    const n = c.length;
    const count = sc.ve - sc.vs + 1;
    const slot = sc.plot / count;
    // WHY: the brief's geometry, written once — centre without shift (P10a, P11), with the plan's shift (P3), width at the default 14 px.
    const centre = (i: number) => (i - sc.vs + 0.5) * slot;
    const shiftedCentre = (i: number) => centre(i) + (plan.edgeShifts.get(c[i]) ?? 0);
    const labelOf = (i: number) => plan.labels.get(c[i]) ?? '';
    const width = (text: string) => estimateLadderLabelWidthPx(text);
    const vis: number[] = [];
    for (let i = sc.vs; i <= sc.ve; i++) if (plan.labels.has(c[i])) vis.push(i);
    const strayLabel = [...plan.labels.keys()].find((d) => !closingSet.has(d));

    // P1 — the visible label texts are unique.
    const visTexts = vis.map(labelOf);
    if (new Set(visTexts).size !== visTexts.length) fail('P1', `duplicate visible texts ${JSON.stringify(visTexts)}`);

    // P2 — no formatter output is an ISO date.
    const isoLeak = c.find((d) => /\d{4}-\d{2}-\d{2}/.test(option.axisLabel.formatter(d)));
    if (isoLeak !== undefined) fail('P2', `formatter(${isoLeak}) = "${option.axisLabel.formatter(isoLeak)}"`);

    // P3 — consecutive visible labels keep the gap, shifts included.
    for (let j = 1; j < vis.length; j++) {
        const a = vis[j - 1];
        const b = vis[j];
        const gap = shiftedCentre(b) - width(labelOf(b)) / 2 - (shiftedCentre(a) + width(labelOf(a)) / 2);
        if (gap < LADDER_LABEL_GAP_PX - EPS) {
            fail('P3', `gap ${gap.toFixed(3)} px between "${labelOf(a)}" (${c[a]}) and "${labelOf(b)}" (${c[b]})`);
            break;
        }
    }

    // P4 — two or more visible buckets show at least two labels. WHY: true on this grid, whose smallest plot is 327 px; the pinned Ex1 plot 40 (A8) is the documented exception, where the search stops with one visible label.
    if (count >= 2 && vis.length < 2) fail('P4', `${vis.length} visible label(s) over ${count} visible buckets`);

    // P5 — closing mode: every step-th bucket from the last, day-month text (+ year iff withYear).
    if (plan.mode === 'closing') {
        const style: OracleStyle = plan.withYear ? 'closingYear' : 'closing';
        for (let i = 0; i < n; i++) {
            const wanted = (n - 1 - i) % plan.step === 0 ? oracleText(sc.locale, style, c[i]) : undefined;
            const got = plan.labels.get(c[i]);
            if (got !== wanted) {
                fail('P5', `bucket ${i} (${c[i]}) has ${got === undefined ? 'no label' : `"${got}"`}; closing/${plan.step} wants ${wanted === undefined ? 'no label' : `"${wanted}"`}`);
                break;
            }
        }
        if (strayLabel !== undefined) fail('P5', `label key ${strayLabel} is not a closing date`);
    }

    // P6 — month mode: the earliest aligned 1st of the covered range, month text (+ year iff withYear or January).
    if (plan.mode === 'month') {
        const k12 = plan.step;
        // WHY: the contract's calendar alignment — k ≤ 12 on month numbers from January, k > 12 on Januaries of years divisible by k/12.
        const aligned = (f: SweepFirst) => (k12 <= 12 ? f.month0 % k12 === 0 : f.month0 === 0 && f.year % (k12 / 12) === 0);
        for (let i = 0; i < n; i++) {
            const first = firsts[i].find(aligned);
            const wanted = first === undefined ? undefined : oracleText(sc.locale, plan.withYear || first.month0 === 0 ? 'monthYear' : 'month', first.iso);
            const got = plan.labels.get(c[i]);
            if (got !== wanted) {
                fail('P6', `bucket ${i} (${c[i]}) has ${got === undefined ? 'no label' : `"${got}"`}; month/${k12} wants ${wanted === undefined ? 'no label' : `"${wanted}"`}`);
                break;
            }
        }
        if (strayLabel !== undefined) fail('P6', `label key ${strayLabel} is not a closing date`);
    }

    // P7 — separators: every bucket while the slot is at least 8 px, otherwise the buckets holding a 1st, plus the anchor (30/09):
    // when exactly one visible bucket holds a 1st and it is not the first visible bucket, the first visible bucket carries one too.
    const everyEdge = slot >= CANDLE_MIN_SLOT_PX;
    const anchor = oracleAnchor(sc);
    for (let i = 0; i < n; i++) {
        const wanted = everyEdge || firsts[i].length > 0 || i === anchor;
        if (plan.separators.has(c[i]) !== wanted) {
            fail('P7', `bucket ${i} (${c[i]}) separator ${!wanted}, expected ${wanted} (slot ${slot.toFixed(2)} px, oracle anchor ${anchor})`);
            break;
        }
    }
    const straySeparator = [...plan.separators].find((d) => !closingSet.has(d));
    if (straySeparator !== undefined) fail('P7', `separator ${straySeparator} is not a closing date`);

    // P8 — withYear iff the visible window spans 365 inclusive days from the covered start of its first bucket.
    const windowDays = endDay[sc.ve] - startDay[sc.vs] + 1;
    if (plan.withYear !== windowDays >= 365) fail('P8', `withYear ${plan.withYear} over ${windowDays} inclusive days`);

    const roomsGiven = sc.rooms.left !== undefined && sc.rooms.right !== undefined;
    const leftRoom = sc.rooms.left ?? 0;
    const rightRoom = sc.rooms.right ?? 0;

    // P10a — anything but closing/1 means closing labels on every visible bucket do not fit.
    if (!(plan.mode === 'closing' && plan.step === 1)) {
        const style: OracleStyle = plan.withYear ? 'closingYear' : 'closing';
        // WHY: the oracle's own closing texts, never the plan's labels (the plan may hold none on these buckets).
        const text = (i: number) => oracleText(sc.locale, style, c[i]);
        const shift = new Map<number, number>();
        if (roomsGiven) {
            // The larger rounding of shiftCandidates: an overflow that is exactly an integer must not turn the planner's float noise into a P10a red.
            const left = Math.max(...shiftCandidates(-leftRoom + LADDER_EDGE_SAFETY_PX - (centre(sc.vs) - width(text(sc.vs)) / 2)));
            const right = Math.max(...shiftCandidates(centre(sc.ve) + width(text(sc.ve)) / 2 - (sc.plot + rightRoom - LADDER_EDGE_SAFETY_PX)));
            shift.set(sc.vs, left);
            shift.set(sc.ve, (shift.get(sc.ve) ?? 0) - right);
        }
        let minGap = Infinity;
        for (let i = sc.vs + 1; i <= sc.ve; i++) {
            const gap = centre(i) + (shift.get(i) ?? 0) - width(text(i)) / 2 - (centre(i - 1) + (shift.get(i - 1) ?? 0) + width(text(i - 1)) / 2);
            minGap = Math.min(minGap, gap);
        }
        if (!(minGap < LADDER_LABEL_GAP_PX + EPS)) fail('P10a', `${plan.mode}/${plan.step} chosen, but closing labels on all ${count} visible bucket(s) fit (${count === 1 ? 'a single bucket has no gap' : `min gap ${minGap.toFixed(3)} px`})`);
    }

    // P11 — edge shifts: the smallest whole px keeping the outermost visible labels SAFETY px inside the rooms.
    const gotShifts = [...plan.edgeShifts];
    if (!roomsGiven || vis.length === 0) {
        if (gotShifts.length > 0) fail('P11', `edgeShifts ${JSON.stringify(gotShifts)} with ${roomsGiven ? 'no visible label' : 'no rooms'}`);
    } else {
        const lo = vis[0];
        const hi = vis[vis.length - 1];
        const leftCandidates = shiftCandidates(-leftRoom + LADDER_EDGE_SAFETY_PX - (centre(lo) - width(labelOf(lo)) / 2));
        const rightCandidates = shiftCandidates(centre(hi) + width(labelOf(hi)) / 2 - (sc.plot + rightRoom - LADDER_EDGE_SAFETY_PX));
        const gotLo = plan.edgeShifts.get(c[lo]) ?? 0;
        const gotHi = plan.edgeShifts.get(c[hi]) ?? 0;
        const valuesOk = lo === hi ? leftCandidates.some((l) => rightCandidates.some((r) => l - r === gotLo)) : leftCandidates.includes(gotLo) && rightCandidates.some((r) => -r === gotHi);
        const strayKeys = gotShifts.filter(([d]) => d !== c[lo] && d !== c[hi]);
        const zeroEntries = gotShifts.filter(([, px]) => px === 0);
        if (!valuesOk || strayKeys.length > 0 || zeroEntries.length > 0) {
            fail('P11', `edgeShifts ${JSON.stringify(gotShifts)}; expected ${c[lo]} +${leftCandidates.join('|')}, ${c[hi]} -${rightCandidates.join('|')} (zero entries absent)`);
        }
    }

    // D4-bis — closing with step >= 2 is anchored on the last bucket of the series.
    if (plan.mode === 'closing' && plan.step >= 2) {
        for (let i = 0; i < n; i++) {
            if (plan.labels.has(c[i]) !== ((n - 1 - i) % plan.step === 0)) {
                fail('D4-bis', `bucket ${i} (${c[i]}) labelled ${plan.labels.has(c[i])} under closing/${plan.step} counted from the last bucket`);
                break;
            }
        }
    }

    return out;
}

describe('A10 — the sweep: 3168 plans against an independent oracle', {timeout: 30_000}, () => {
    // WHY: the pins prove single points; the sweep proves the contract's invariants on every rung × window × plot × locale × rooms, and its guards prove the grid reaches every branch.
    it('P1–P11 and D4-bis hold on every case, and the grid covers every mode', () => {
        const failures: Array<{prop: string; tag: string; detail: string}> = [];
        const coverage = {cases: 0, closingStep1: 0, monthStep2Plus: 0, closingStep2Plus: 0, positiveShift: 0, negativeShift: 0, withYearTrue: 0, withYearFalse: 0, anchor: 0};
        const contentByKey = new Map<string, {content: string; tag: string}>();

        for (const span of SWEEP_SPANS) {
            const series = sweepSeries(span);
            const n = series.closings.length;
            for (const win of SWEEP_WINDOWS) {
                const [from, to] = win.of(n);
                const vs = Math.min(Math.max(Math.min(from, to), 0), n - 1);
                const ve = Math.min(Math.max(Math.max(from, to), 0), n - 1);
                for (const plot of SWEEP_PLOTS) {
                    for (const locale of SWEEP_LOCALES) {
                        for (const rooms of SWEEP_ROOMS) {
                            const tag = `${span}/${win.tag}/${plot}/${locale}/${rooms.tag}`;
                            const plan = planLadderAxis({
                                closingDates: series.closings,
                                firstDate: SWEEP_FIRST,
                                visibleStartIndex: from,
                                visibleEndIndex: to,
                                plotWidthPx: plot,
                                locale,
                                ...(rooms.left === undefined ? {} : {leftRoomPx: rooms.left, rightRoomPx: rooms.right}),
                            });
                            const option = ladderAxisOption(plan);
                            const sc: SweepCase = {series, vs, ve, plot, locale, rooms};
                            coverage.cases++;
                            for (const f of checkPlan(sc, plan, option)) failures.push({...f, tag});

                            // P9 — key safety: one key never names two different plans.
                            const content = JSON.stringify([plan.mode, plan.step, plan.withYear, [...plan.labels].sort(), [...plan.separators].sort(), [...plan.edgeShifts].sort()]);
                            const seen = contentByKey.get(plan.key);
                            if (seen === undefined) contentByKey.set(plan.key, {content, tag});
                            else if (seen.content !== content) failures.push({prop: 'P9', tag, detail: `key "${plan.key}" also names a different plan at ${seen.tag}`});

                            if (plan.mode === 'closing' && plan.step === 1) coverage.closingStep1++;
                            if (plan.mode === 'month' && plan.step >= 2) coverage.monthStep2Plus++;
                            if (plan.mode === 'closing' && plan.step >= 2) coverage.closingStep2Plus++;
                            if ([...plan.edgeShifts.values()].some((px) => px > 0)) coverage.positiveShift++;
                            if ([...plan.edgeShifts.values()].some((px) => px < 0)) coverage.negativeShift++;
                            if (plan.withYear) coverage.withYearTrue++;
                            else coverage.withYearFalse++;
                            if (oracleAnchor(sc) >= 0) coverage.anchor++;
                        }
                    }
                }
            }
        }

        // WHY: the coverage guards — the grid must exercise every branch, or a green sweep proves less than it claims.
        const guard = (ok: boolean, detail: string) => {
            if (!ok) failures.push({prop: 'guard', tag: 'grid', detail});
        };
        guard(coverage.cases === 3168, `the grid ran ${coverage.cases} cases, the brief fixes 3168`);
        guard(coverage.closingStep1 >= 500, `closing/1 on ${coverage.closingStep1} plans, expected >= 500`);
        guard(coverage.monthStep2Plus >= 300, `month with step >= 2 on ${coverage.monthStep2Plus} plans, expected >= 300`);
        guard(coverage.closingStep2Plus > 0, 'no D4-bis plan (closing with step >= 2)');
        guard(coverage.positiveShift > 0, 'no positive edge shift');
        guard(coverage.negativeShift > 0, 'no negative edge shift');
        guard(coverage.withYearTrue > 0, 'withYear never true');
        guard(coverage.withYearFalse > 0, 'withYear never false');
        guard(coverage.anchor > 0, 'no anchor-separator case (slot < 8 px, exactly one visible 1st, not on the first visible bucket)');

        const perProperty = new Map<string, number>();
        for (const f of failures) perProperty.set(f.prop, (perProperty.get(f.prop) ?? 0) + 1);
        const summary = [`A10 sweep: ${failures.length} failure(s) over ${coverage.cases} cases: ${[...perProperty].map(([prop, total]) => `${prop} x${total}`).join(', ')}`, `coverage ${JSON.stringify(coverage)}`, ...failures.slice(0, 20).map((f) => `${f.prop} [${f.tag}] ${f.detail}`)].join('\n');
        expect(failures.length, summary).toBe(0);
    });
});
