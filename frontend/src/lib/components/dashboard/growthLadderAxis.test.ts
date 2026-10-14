/**
 * S7 — the category x axis of the GrowthChart ladder (P&L Candles and Income): the pure planner, pinned.
 *
 * `planLadderAxis` names every bucket after the calendar start of its period, lays the labels flat or
 * turns them all 45°, thins them only when even turned they would touch, and keeps the separators of D4;
 * `ladderAxisOption` turns the plan into the ECharts `axisLabel` / `splitLine` options. The contract
 * (plan-phase00PerformanceChartsIncomeColorsAxisLabels §2) replaces the text rules of D4/D4-bis:
 *   - bucket i is named after S_i = calendarPeriodOf(closingDates[i], rung).start, also when partial. Forms:
 *     day rungs SHORT «5», MONTH «Jan 5», YEAR labelWithYear(MONTH, yy); 1M «Oct»; 3M quarterLabel(q);
 *     6M «Jul–Dec» (EN DASH); 1Y always «2026»; 1M/3M/6M YEAR = labelWithYear(SHORT, yy);
 *   - the first VISIBLE labelled bucket takes MONTH on day rungs (never the year) and YEAR on 1M/3M/6M;
 *     every other one compares with the previous LABELLED bucket: YEAR on a year change, MONTH on a day
 *     rung's month change, SHORT otherwise. Two consecutive labelled buckets never share a text;
 *   - flat (rotate 0, step 1, every bucket labelled) when the D4 trial fits: visible labels 8 px apart,
 *     edge shifts included. Otherwise all turn 45°: step k = max(1, ceil(font·(14.3/14) / (slot·√½) − 1e-9)),
 *     one label ROW across the turned text being 14.3/14 em (M‴, 08/10/2026: a Chromium 14 px line is
 *     14.28 px tall, and ECharts hides an edge label whose W-wide box meets its neighbour's), labels on
 *     (n − 1 − i) % k === 0 minus the edge candidates whose turned label leaves the canvas, and no edge
 *     shifts;
 *   - `widestText` answers the formatter for an unlabelled raw: ECharts' legacy containLabel samples the
 *     formatter and ignores `interval`, and a turned label is as tall as it is wide;
 *   - `labelBox` (M‴): turned and given `measureLabelPx`, every label gets an invisible box as wide as the
 *     widest VISIBLE labelled text (`axisLabel.width`) and a font-size line (`axisLabel.lineHeight`), so the
 *     band containLabel reserves no longer depends on which categories it samples (L15, L16);
 *   - separators unchanged (CANDLE_MIN_SLOT_PX and the anchor rule).
 *
 * WHERE THE EXPECTED VALUES COME FROM. The pins (L1–L13) are literals computed by hand on
 * `buildCalendarLadder` fixtures, one row per case; two stubs stand in for the i18n keys
 * `dashboard.pnlAxisQuarter` and `dashboard.pnlAxisWithYear`. L14 checks 4160 plans against an oracle
 * written in this file from the contract, the calendar and Intl alone: the only product imports are the
 * module under test and the bucket calendar. L14-self proves the oracle reproduces every pin, and that the
 * sweep's checks pass the oracle's own plans and catch mutated ones (a positive control).
 *
 * THE TEXTS ARE ICU'S. Every literal is `Intl.DateTimeFormat` output (ICU 78.3, Node 26.8.2) through the
 * stubs. L0 asserts those forms first, with messages starting `ICU changed:`, so a Node or ICU upgrade
 * reads as an environment change, not as a planner defect.
 *
 * GREEN ON THE OLD PLANNER, ON PURPOSE: L0, the key-equality guard (L9.5), the separators (L11, L14b),
 * the width estimate (L13.11) and the oracle's own checks (L14a, L14-self). The rest is red until the
 * planner implements this contract.
 *
 * RED BEFORE THE M‴ FIX (08/10/2026), ON PURPOSE: the pins the 14.3 px row moves or adds (L7.2 and L9.1
 * moved, L7.9 added), the empty plan (L12.1–5, its `labelBox: null`), L14c (the oracle's k), and L15 and
 * L16.2–4 (the box). Green before it, on purpose: every other pin — L7.10 and L8.1 at slot 20.3 included,
 * which the row does not move — and L16.1, the SSR preconditions and the ECharts control (ECharts' own
 * behaviour, not the fix).
 */
import * as echarts from 'echarts';
import {describe, expect, it} from 'vitest';
import {LADDER_EDGE_SAFETY_PX, LADDER_LABEL_GAP_PX, LADDER_LABEL_ROW_EM, estimateLadderLabelWidthPx, ladderAxisOption, planLadderAxis} from './growthLadderAxis';
import type {LadderAxisInput, LadderAxisOption, LadderAxisPlan} from './growthLadderAxis';
import {buildCalendarLadder, calendarPeriodOf} from './growthLadderBuckets';
import type {LadderRung} from './growthLadderBuckets';

/** The contract's constants, restated so the oracle owes nothing to the module under test. */
const GAP_PX = 8;
const SAFETY_PX = 2;
const CANDLE_MIN_SLOT_PX = 8;
const DEFAULT_FONT_PX = 14;
const EPS = 1e-9;
const DAY_MS = 86_400_000;
const SQRT_HALF = Math.SQRT1_2;
/** Income's minimum slot: 4.5 px bars at 0.21875 of the slot. */
const INCOME_MIN_SLOT_PX = 4.5 / 0.21875;
/** One turned label's row across its text, in em (M‴): a Chromium 14 px line is 14.28 px tall, the pitch must exceed it. */
const LABEL_ROW_EM = 14.3 / 14;
const EN_DASH = '\u2013';
const MAX_REPORTED = 12;
const DAY_RUNGS: ReadonlySet<LadderRung> = new Set<LadderRung>(['1D', '3D', '1W', '2W']);

/** The two i18n keys GrowthChart passes, stubbed: the planner composes, it never assumes the word order. */
interface Stub {
    locale: string;
    labelWithYear: (label: string, year: string) => string;
    quarterLabel: (quarter: 1 | 2 | 3 | 4) => string;
}
const EN: Stub = {locale: 'en', labelWithYear: (label, year) => `${label} '${year}`, quarterLabel: (quarter) => `Q${quarter}`};
const IT: Stub = {locale: 'it', labelWithYear: (label, year) => `${label} ${year}`, quarterLabel: (quarter) => `T${quarter}`};
const FR: Stub = {...IT, locale: 'fr'};
const ES: Stub = {...IT, locale: 'es'};

const toDay = (iso: string): number => Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10))) / DAY_MS;
const fromDay = (day: number): string => new Date(day * DAY_MS).toISOString().slice(0, 10);

/** Consecutive calendar days, both ends included. */
function daily(first: string, last: string): string[] {
    const out: string[] = [];
    for (let day = toDay(first); day <= toDay(last); day++) out.push(fromDay(day));
    return out;
}

interface Ladder {
    rung: LadderRung;
    closingDates: string[];
    firstDate: string;
}

/** A calendar fixture the way GrowthChart builds it: each bucket closes on its last day in the series. */
function ladder(rung: LadderRung, first: string, last: string): Ladder {
    const dates = daily(first, last);
    return {rung, closingDates: buildCalendarLadder(dates, rung, last).map((bucket) => dates[bucket.endIndex]), firstDate: dates[0]};
}

interface Geometry {
    window?: readonly [number, number];
    leftRoomPx?: number;
    rightRoomPx?: number;
    fontSizePx?: number;
}

function axisInput(lad: Ladder, stub: Stub, plotWidthPx: number, geometry: Geometry = {}): LadderAxisInput {
    const [visibleStartIndex, visibleEndIndex] = geometry.window ?? [0, lad.closingDates.length - 1];
    return {
        closingDates: lad.closingDates,
        firstDate: lad.firstDate,
        visibleStartIndex,
        visibleEndIndex,
        plotWidthPx,
        ...(geometry.leftRoomPx === undefined ? {} : {leftRoomPx: geometry.leftRoomPx}),
        ...(geometry.rightRoomPx === undefined ? {} : {rightRoomPx: geometry.rightRoomPx}),
        ...(geometry.fontSizePx === undefined ? {} : {fontSizePx: geometry.fontSizePx}),
        locale: stub.locale,
        rung: lad.rung,
        quarterLabel: stub.quarterLabel,
        labelWithYear: stub.labelWithYear,
    };
}

type IcuForm = 'day' | 'dayMonth' | 'month' | 'year2' | 'year';
const ICU_OPTIONS: Record<IcuForm, Intl.DateTimeFormatOptions> = {
    day: {day: 'numeric', timeZone: 'UTC'},
    dayMonth: {day: 'numeric', month: 'short', timeZone: 'UTC'},
    month: {month: 'short', timeZone: 'UTC'},
    year2: {year: '2-digit', timeZone: 'UTC'},
    year: {year: 'numeric', timeZone: 'UTC'},
};
const icuCache = new Map<string, Intl.DateTimeFormat>();

/** One Intl form of an ISO day, in UTC: the only source of the dates' words in this file. */
function icu(locale: string, form: IcuForm, iso: string): string {
    const cacheKey = `${locale}|${form}`;
    let formatter = icuCache.get(cacheKey);
    if (formatter === undefined) {
        formatter = new Intl.DateTimeFormat(locale, ICU_OPTIONS[form]);
        icuCache.set(cacheKey, formatter);
    }
    return formatter.format(new Date(`${iso}T00:00:00Z`));
}

/** `'a · b'` → `'0:a | 1:b'`: a fully labelled axis, written the way the developer reads it. */
const dots = (axis: string): string =>
    axis
        .split(' · ')
        .map((text, index) => `${index}:${text}`)
        .join(' | ');

/** Entries keyed by raw → `'i:value | …'` in index order; a key that is not a closing date shows as `?raw:value`. */
function indexedSpec(map: ReadonlyMap<string, string | number>, closings: readonly string[]): string {
    const parts: string[] = [];
    closings.forEach((raw, index) => {
        if (map.has(raw)) parts.push(`${index}:${String(map.get(raw))}`);
    });
    for (const [raw, value] of map) if (!closings.includes(raw)) parts.push(`?${raw}:${String(value)}`);
    return parts.join(' | ');
}

function separatorIndices(separators: ReadonlySet<string>, closings: readonly string[]): Array<number | string> {
    const out: Array<number | string> = [];
    closings.forEach((raw, index) => {
        if (separators.has(raw)) out.push(index);
    });
    for (const raw of separators) if (!closings.includes(raw)) out.push(`?${raw}`);
    return out;
}

/** Consecutive labelled buckets that share a text, as `'p/i:text'`: the contract says there are none. */
function repeatsOf(labels: ReadonlyMap<string, string>, closings: readonly string[]): string[] {
    const out: string[] = [];
    let previous: string | undefined;
    closings.forEach((raw, index) => {
        const text = labels.get(raw);
        if (text === undefined) return;
        if (previous !== undefined && labels.get(previous) === text) out.push(`${closings.indexOf(previous)}/${index}:${text}`);
        previous = raw;
    });
    return out;
}

/** A plan in the notation of the pins: bucket count, rotation, step and the three keyed collections by index. */
interface AxisView {
    buckets: number;
    rotate: number;
    step: number;
    labels: string;
    widestText: string;
    edgeShifts: string;
    repeats: string[];
}

function axisView(plan: LadderAxisPlan, closings: readonly string[]): AxisView {
    return {
        buckets: closings.length,
        rotate: plan.rotate,
        step: plan.step,
        labels: indexedSpec(plan.labels, closings),
        widestText: plan.widestText,
        edgeShifts: indexedSpec(plan.edgeShifts, closings),
        repeats: repeatsOf(plan.labels, closings),
    };
}

/** A pin: flat, step 1 and no shifts unless said otherwise; never a repeated text. */
function pinOf(pin: {buckets: number; labels: string; widestText: string; rotate?: 0 | 45; step?: number; edgeShifts?: string}): AxisView {
    return {buckets: pin.buckets, rotate: pin.rotate ?? 0, step: pin.step ?? 1, labels: pin.labels, widestText: pin.widestText, edgeShifts: pin.edgeShifts ?? '', repeats: []};
}

interface PinRow {
    id: string;
    name: string;
    input: LadderAxisInput;
    pin: AxisView;
}

/** Every pinned row, collected as the groups declare them: L14-self replays them all through the oracle. */
const PIN_ROWS: PinRow[] = [];
function pinRows(list: PinRow[]): PinRow[] {
    PIN_ROWS.push(...list);
    return list;
}

function expectPin(row: PinRow): void {
    expect(axisView(planLadderAxis(row.input), row.input.closingDates), `${row.id} ${row.name}`).toEqual(row.pin);
}

/** A row by its id, never by its position in the list. */
function rowById(list: readonly PinRow[], id: string): PinRow {
    const found = list.find((candidate) => candidate.id === id);
    if (found === undefined) throw new Error(`no pin row ${id}`);
    return found;
}

// ─── The oracle: the contract restated from the calendar and Intl, independent of the planner ───

/** The texts bucket i can carry, and the calendar start S_i its rules compare. */
interface Forms {
    first: string;
    year: string;
    month: string;
    short: string;
    /** UTC year of S_i, and year · 12 + month0. */
    y: number;
    ym: number;
}

function formsOf(closing: string, rung: LadderRung, stub: Stub): Forms {
    const start = calendarPeriodOf(closing, rung).start;
    const y = Number(start.slice(0, 4));
    const m0 = Number(start.slice(5, 7)) - 1;
    const ym = y * 12 + m0;
    if (rung === '1Y') {
        const full = icu(stub.locale, 'year', start);
        return {first: full, year: full, month: full, short: full, y, ym};
    }
    const yy = icu(stub.locale, 'year2', start);
    if (DAY_RUNGS.has(rung)) {
        const dayMonth = icu(stub.locale, 'dayMonth', start);
        return {first: dayMonth, year: stub.labelWithYear(dayMonth, yy), month: dayMonth, short: icu(stub.locale, 'day', start), y, ym};
    }
    const monthOf = (iso: string) => icu(stub.locale, 'month', iso);
    let short: string;
    if (rung === '1M') short = monthOf(start);
    else if (rung === '3M') short = stub.quarterLabel((Math.floor(m0 / 3) + 1) as 1 | 2 | 3 | 4);
    else short = `${monthOf(start)}${EN_DASH}${monthOf(fromDay(Date.UTC(y, m0 + 5, 1) / DAY_MS))}`;
    const withYear = stub.labelWithYear(short, yy);
    return {first: withYear, year: withYear, month: short, short, y, ym};
}

/** The contract's rules, first match wins: 1 = 1Y, 2 = first form, 3 = year change, 4 = a day rung's month change, 5 = short. */
type Rule = 1 | 2 | 3 | 4 | 5;
function ruleOf(rung: LadderRung, current: Forms, previous: Forms | undefined, isFirst: boolean): Rule {
    if (rung === '1Y') return 1;
    if (isFirst || previous === undefined) return 2;
    if (current.y !== previous.y) return 3;
    if (DAY_RUNGS.has(rung) && current.ym !== previous.ym) return 4;
    return 5;
}
const textOfRule = (forms: Forms, rule: Rule): string => (rule <= 2 ? forms.first : rule === 3 ? forms.year : rule === 4 ? forms.month : forms.short);

/** What does not depend on the geometry, computed once per series. */
interface Series {
    lad: Ladder;
    forms: Forms[];
    /** Rule and text of bucket i when every bucket is labelled and none is the first visible (p = i − 1). */
    flatRules: Rule[];
    flatTexts: string[];
    /** The 1sts of a month bucket i covers: (closing[i − 1], closing[i]], from firstDate for bucket 0. */
    monthFirsts: number[];
}

function oracleSeries(lad: Ladder, stub: Stub): Series {
    const forms = lad.closingDates.map((closing) => formsOf(closing, lad.rung, stub));
    const flatRules = forms.map((current, index): Rule => ruleOf(lad.rung, current, index > 0 ? forms[index - 1] : undefined, false));
    const flatTexts = forms.map((current, index) => textOfRule(current, flatRules[index]));
    const monthFirsts: number[] = [];
    let from = toDay(lad.firstDate);
    for (const closing of lad.closingDates) {
        let count = 0;
        for (let day = from; day <= toDay(closing); day++) if (fromDay(day).endsWith('-01')) count++;
        monthFirsts.push(count);
        from = toDay(closing) + 1;
    }
    return {lad, forms, flatRules, flatTexts, monthFirsts};
}

/** One of the two answers the contract allows: flat or turned. */
interface Branch {
    rotate: 0 | 45;
    step: number;
    /** Text and rule by bucket index; undefined = no label. */
    texts: Array<string | undefined>;
    rules: Array<Rule | undefined>;
    /** The first visible labelled bucket, which carries the first form. */
    first: number | undefined;
    widestText: string;
    /** Flat only: the contract's exact shifts, and every value a planner honest up to float noise may give. */
    exactShifts: Map<number, number>;
    shiftChoices: Map<number, number[]>;
}

/** ceil of a value that float noise may have nudged across an integer: every answer an honest planner can give. */
function ceilChoices(value: number): number[] {
    return [...new Set([Math.max(0, Math.ceil(value - EPS)), Math.max(0, Math.ceil(value + EPS))])];
}

/** The longest visible labelled text, ties to the lowest index; '' when none is visible. */
function widestOf(texts: ReadonlyArray<string | undefined>, vs: number, ve: number): string {
    let widest = '';
    for (let index = vs; index <= ve; index++) {
        const text = texts[index];
        if (text !== undefined && text.length > widest.length) widest = text;
    }
    return widest;
}

interface OracleCase {
    n: number;
    vs: number;
    ve: number;
    slot: number;
    /** 'either': the flat trial sits within 1e-9 px of the 8 px gap, so both answers honour the contract. */
    decision: 'flat' | 'rotated' | 'either';
    flat: Branch;
    rotated: Branch;
    /** The turned answer has k or a drop on its boundary, within float noise. */
    rotatedAmbiguous: boolean;
    leftDropped: number;
    rightDropped: number;
    separators: Set<number>;
    anchor: boolean;
}

function oracleCase(series: Series, input: LadderAxisInput): OracleCase {
    const {rung, closingDates} = series.lad;
    const {forms, monthFirsts} = series;
    const n = closingDates.length;
    const clamp = (value: number, fallback: number) => (Number.isFinite(value) ? Math.max(0, Math.min(n - 1, Math.round(value))) : fallback);
    let vs = clamp(input.visibleStartIndex, 0);
    let ve = clamp(input.visibleEndIndex, n - 1);
    if (vs > ve) [vs, ve] = [ve, vs];
    const plot = input.plotWidthPx;
    const font = input.fontSizePx ?? DEFAULT_FONT_PX;
    const left = input.leftRoomPx;
    const right = input.rightRoomPx;
    const slot = plot / (ve - vs + 1);
    const centre = (index: number) => (index - vs + 0.5) * slot;
    const width = (text: string) => text.length * font * 0.6;

    // Flat: every bucket labelled, the first visible one in its first form.
    const flatRules: Array<Rule | undefined> = series.flatRules.slice();
    const flatTexts: Array<string | undefined> = series.flatTexts.slice();
    const firstRule = ruleOf(rung, forms[vs], undefined, true);
    flatRules[vs] = firstRule;
    flatTexts[vs] = textOfRule(forms[vs], firstRule);
    const w = (index: number) => width(flatTexts[index] ?? '');
    const lo = vs;
    const hi = ve;
    const loNeed = left === undefined ? undefined : -left + SAFETY_PX - (centre(lo) - w(lo) / 2);
    const hiOver = right === undefined ? undefined : centre(hi) + w(hi) / 2 - (plot + right - SAFETY_PX);
    const exactShifts = new Map<number, number>();
    if (loNeed !== undefined && loNeed > 0) exactShifts.set(lo, Math.ceil(loNeed));
    if (hiOver !== undefined && hiOver > 0) exactShifts.set(hi, (exactShifts.get(hi) ?? 0) - Math.ceil(hiOver));
    if (exactShifts.get(hi) === 0) exactShifts.delete(hi);
    const loChoices = loNeed === undefined ? [0] : ceilChoices(loNeed);
    const hiChoices = hiOver === undefined ? [0] : ceilChoices(hiOver).map((px) => -px);
    const shiftChoices = new Map<number, number[]>();
    if (lo === hi) shiftChoices.set(lo, [...new Set(loChoices.flatMap((a) => hiChoices.map((b) => a + b)))]);
    else {
        shiftChoices.set(lo, loChoices);
        shiftChoices.set(hi, hiChoices);
    }
    // WHY: the lo shift only moves right and the hi shift only left, so their largest magnitudes are the worst case for every gap.
    const fitsWith = (loShift: number, hiShift: number, threshold: number): boolean => {
        const shift = (index: number) => (index === lo ? loShift : 0) + (index === hi ? hiShift : 0);
        for (let index = vs + 1; index <= ve; index++) {
            const gap = centre(index) + shift(index) - w(index) / 2 - (centre(index - 1) + shift(index - 1) + w(index - 1) / 2);
            if (gap < threshold) return false;
        }
        return true;
    };
    const strict = fitsWith(Math.max(...loChoices), Math.min(...hiChoices), GAP_PX + EPS);
    const loose = fitsWith(Math.min(...loChoices), Math.max(...hiChoices), GAP_PX - EPS);
    const decision = strict ? 'flat' : loose ? 'either' : 'rotated';
    const flat: Branch = {rotate: 0, step: 1, texts: flatTexts, rules: flatRules, first: vs, widestText: widestOf(flatTexts, vs, ve), exactShifts, shiftChoices};

    // Turned: k from one label row (14.3/14 em) between neighbours, counted from the last bucket, then the edge drops.
    const ratio = (font * LABEL_ROW_EM) / (slot * SQRT_HALF) - EPS;
    const k = Math.max(1, Math.ceil(ratio));
    let rotatedAmbiguous = Math.round(ratio) >= 1 && Math.abs(ratio - Math.round(ratio)) < 1e-11;
    const inL0 = (index: number) => (n - 1 - index) % k === 0;
    const visibleL0: number[] = [];
    for (let index = vs; index <= ve; index++) if (inL0(index)) visibleL0.push(index);
    const dropped = new Set<number>();
    let leftDropped = 0;
    if (left !== undefined) {
        for (const candidate of visibleL0) {
            const margin = left + centre(candidate) - (width(forms[candidate].first) + font / 2) * SQRT_HALF - SAFETY_PX;
            if (Math.abs(margin) < EPS) rotatedAmbiguous = true;
            if (margin >= 0) break;
            dropped.add(candidate);
            leftDropped++;
        }
    }
    let rightDropped = 0;
    if (right !== undefined) {
        for (let at = visibleL0.length - 1; at >= 0 && !dropped.has(visibleL0[at]); at--) {
            const excess = centre(visibleL0[at]) + (font / 2) * SQRT_HALF - (plot + right - SAFETY_PX);
            if (Math.abs(excess) < EPS) rotatedAmbiguous = true;
            if (excess <= 0) break;
            dropped.add(visibleL0[at]);
            rightDropped++;
        }
    }
    const labelled: number[] = [];
    for (let index = 0; index < n; index++) if (inL0(index) && !dropped.has(index)) labelled.push(index);
    const firstVisible = labelled.find((index) => index >= vs && index <= ve);
    const rotatedTexts: Array<string | undefined> = new Array<string | undefined>(n).fill(undefined);
    const rotatedRules: Array<Rule | undefined> = new Array<Rule | undefined>(n).fill(undefined);
    labelled.forEach((index, at) => {
        const rule = ruleOf(rung, forms[index], at > 0 ? forms[labelled[at - 1]] : undefined, index === firstVisible);
        rotatedRules[index] = rule;
        rotatedTexts[index] = textOfRule(forms[index], rule);
    });
    const rotated: Branch = {rotate: 45, step: k, texts: rotatedTexts, rules: rotatedRules, first: firstVisible, widestText: widestOf(rotatedTexts, vs, ve), exactShifts: new Map(), shiftChoices: new Map()};

    // Separators, unchanged: every bucket while the slot is wide, else the month edges plus the lone-edge anchor.
    const sparse = slot < CANDLE_MIN_SLOT_PX;
    let visibleEdges = 0;
    for (let index = vs; index <= ve; index++) if (monthFirsts[index] > 0) visibleEdges++;
    const anchorIndex = sparse && visibleEdges === 1 && monthFirsts[vs] === 0 ? vs : -1;
    const separators = new Set<number>();
    for (let index = 0; index < n; index++) if (!sparse || monthFirsts[index] > 0 || index === anchorIndex) separators.add(index);
    return {n, vs, ve, slot, decision, flat, rotated, rotatedAmbiguous, leftDropped, rightDropped, separators, anchor: anchorIndex >= 0};
}

/** The oracle on a bare input: the stub and the series are read back from it. */
function oracleOf(input: LadderAxisInput): OracleCase {
    const stub: Stub = {locale: input.locale, labelWithYear: input.labelWithYear, quarterLabel: input.quarterLabel};
    return oracleCase(oracleSeries({rung: input.rung, closingDates: [...input.closingDates], firstDate: input.firstDate}, stub), input);
}

/** The oracle's answer in the notation of the pins, with the exact shifts of the contract. */
function oracleView(oracle: OracleCase, closings: readonly string[]): AxisView {
    const branch = oracle.decision === 'rotated' ? oracle.rotated : oracle.flat;
    const labels = new Map<string, string>();
    branch.texts.forEach((text, index) => {
        if (text !== undefined) labels.set(closings[index], text);
    });
    const shifts = new Map<string, number>([...branch.exactShifts].map(([index, px]): [string, number] => [closings[index], px]));
    return {buckets: oracle.n, rotate: branch.rotate, step: branch.step, labels: indexedSpec(labels, closings), widestText: branch.widestText, edgeShifts: indexedSpec(shifts, closings), repeats: repeatsOf(labels, closings)};
}

/** The rich style the contract keeps from D4: padding on the far side moves the centred glyph by half of it. */
const shiftStyle = (px: number): string => `lfShift${px < 0 ? 'L' : 'R'}${Math.abs(px)}`;
const shiftPadding = (px: number): [number, number, number, number] => (px < 0 ? [0, -2 * px, 0, 0] : [0, 0, 0, 2 * px]);

/** `axisLabel` read loosely, so `rotate`, `width` and `lineHeight` are checked whatever the option type declares. */
const axisLabelOf = (option: LadderAxisOption) => option.axisLabel as LadderAxisOption['axisLabel'] & {rotate?: unknown; width?: unknown; lineHeight?: unknown};

// ─── Fixtures: calendar ladders built the way GrowthChart builds them ───

/** 1W from Thursday 2026-01-01 (B6): 7 buckets closing Jan 4, 11, 18, 25, Feb 1, 8 and 9; bucket 0 is partial. */
const WEEKS_B6 = ladder('1W', '2026-01-01', '2026-02-09');
/** 2W from Monday 2025-10-06, a pair start: 8 fortnights up to Sunday 2026-01-25. */
const FORTNIGHTS = ladder('2W', '2025-10-06', '2026-01-25');
const MONTHS_5 = ladder('1M', '2025-10-01', '2026-02-28');
const QUARTERS_8 = ladder('3M', '2024-10-01', '2026-09-30');
const HALVES_4 = ladder('6M', '2025-07-01', '2027-06-30');
const YEARS_3 = ladder('1Y', '2024-03-15', '2026-05-20');
const DAYS_10 = ladder('1D', '2026-03-10', '2026-03-19');
const DAYS_12 = ladder('1D', '2026-03-10', '2026-03-21');
const DAYS_20 = ladder('1D', '2026-03-10', '2026-03-29');
/** Income `1M` over a year, the most common view. */
const MONTHS_INCOME = ladder('1M', '2025-10-01', '2026-09-30');
const MONTHS_2025 = ladder('1M', '2025-01-01', '2025-12-31');
const MONTHS_24 = ladder('1M', '2025-01-01', '2026-12-31');
/** GrowthChart's B9 window, April to September 2026. */
const MONTHS_APR_SEP = ladder('1M', '2026-04-01', '2026-09-30');
/** 1D from Monday 2026-08-31: 31 buckets, Sep 1 in bucket 1. */
const EX1 = ladder('1D', '2026-08-31', '2026-09-30');
/** 1D from 2026-06-25: 92 buckets, the 1sts of Jul, Aug and Sep in buckets 6, 37 and 68. */
const EX3 = ladder('1D', '2026-06-25', '2026-09-24');

describe('L0 — ICU precondition (the texts below are ICU 78.3 output)', () => {
    const DAY_MONTH_ISOS = ['2025-12-29', '2026-01-05', '2025-10-06', '2026-02-02', '2026-03-11'];
    const ICU_TABLE = [
        {locale: 'en', months: 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec', dayMonths: ['Dec 29', 'Jan 5', 'Oct 6', 'Feb 2', 'Mar 11']},
        {locale: 'it', months: 'gen feb mar apr mag giu lug ago set ott nov dic', dayMonths: ['29 dic', '5 gen', '6 ott', '2 feb', '11 mar']},
        {locale: 'fr', months: 'janv. févr. mars avr. mai juin juil. août sept. oct. nov. déc.', dayMonths: ['29 déc.', '5 janv.', '6 oct.', '2 févr.', '11 mars']},
        {locale: 'es', months: 'ene feb mar abr may jun jul ago sept oct nov dic', dayMonths: ['29 dic', '5 ene', '6 oct', '2 feb', '11 mar']},
    ];
    // WHY: every text in this file is ICU output; when this is red the environment changed and no planner red below can be trusted.
    it.each(ICU_TABLE)('$locale: short month, day-month, day and year forms', ({locale, months, dayMonths}) => {
        // WHY: the 12 short months are the 1M texts and the two halves of every 6M text.
        const monthTexts = Array.from({length: 12}, (_, m0) => icu(locale, 'month', `2025-${String(m0 + 1).padStart(2, '0')}-01`));
        expect(monthTexts.join(' '), `ICU changed: ${locale} short months`).toBe(months);
        const dayMonthTexts = DAY_MONTH_ISOS.map((iso) => icu(locale, 'dayMonth', iso));
        expect(dayMonthTexts, `ICU changed: ${locale} day-month`).toEqual(dayMonths);
        expect([icu(locale, 'day', '2026-01-05'), icu(locale, 'day', '2025-10-20')], `ICU changed: ${locale} day`).toEqual(['5', '20']);
        // WHY: yy reaches labelWithYear as a string, so 2005 must stay "05".
        expect(
            ['2025-01-01', '2005-06-01', '2026-12-31'].map((iso) => icu(locale, 'year2', iso)),
            `ICU changed: ${locale} two-digit year`,
        ).toEqual(['25', '05', '26']);
        expect(icu(locale, 'year', '2026-07-01'), `ICU changed: ${locale} full year`).toBe('2026');
        // WHY: the pins are written with plain spaces; a no-break space from ICU would read as a planner diff.
        expect(
            [...monthTexts, ...dayMonthTexts].filter((text) => /[\u00a0\u202f]/.test(text)),
            `ICU changed: ${locale} no-break space`,
        ).toEqual([]);
    });
});

type PinSpec = Parameters<typeof pinOf>[0];
const row = (id: string, name: string, input: LadderAxisInput, pin: PinSpec): PinRow => ({id, name, input, pin: pinOf(pin)});

describe('L1 — one text on every bucket, for all 8 rungs', () => {
    const NEW_YEAR_1D = ladder('1D', '2025-12-28', '2026-01-03');
    const NEW_YEAR_3D = ladder('3D', '2025-12-26', '2026-01-09');
    const ROWS = pinRows([
        // WHY: day rungs name the day; the first bucket gets the month, a month or year change gets it again, the year only where it changes.
        row('L1.1', '1D en across New Year', axisInput(NEW_YEAR_1D, EN, 527), {buckets: 7, labels: dots("Dec 28 · 29 · 30 · 31 · Jan 1 '26 · 2 · 3"), widestText: "Jan 1 '26"}),
        // WHY: the Italian stub puts the year after a space and Intl puts the day first.
        row('L1.2', '1D it across New Year', axisInput(NEW_YEAR_1D, IT, 527), {buckets: 7, labels: dots('28 dic · 29 · 30 · 31 · 1 gen 26 · 2 · 3'), widestText: '1 gen 26'}),
        // WHY: 3D buckets are named after their calendar start, every third day.
        row('L1.3', '3D en across New Year', axisInput(NEW_YEAR_3D, EN, 527), {buckets: 5, labels: dots("Dec 26 · 29 · Jan 1 '26 · 4 · 7"), widestText: "Jan 1 '26"}),
        row('L1.4', '3D it across New Year', axisInput(NEW_YEAR_3D, IT, 527), {buckets: 5, labels: dots('26 dic · 29 · 1 gen 26 · 4 · 7'), widestText: '1 gen 26'}),
        // WHY: the brief's 1W example: weeks are named after their Monday, also the partial first one.
        row('L1.5', '1W en (B6)', axisInput(WEEKS_B6, EN, 527), {buckets: 7, labels: dots("Dec 29 · Jan 5 '26 · 12 · 19 · 26 · Feb 2 · 9"), widestText: "Jan 5 '26"}),
        row('L1.6', '1W it (B6)', axisInput(WEEKS_B6, IT, 527), {buckets: 7, labels: dots('29 dic · 5 gen 26 · 12 · 19 · 26 · 2 feb · 9'), widestText: '5 gen 26'}),
        // WHY: Spanish month names through the fr/es-style stub.
        row('L1.7', '1W es (B6)', axisInput(WEEKS_B6, ES, 527), {buckets: 7, labels: dots('29 dic · 5 ene 26 · 12 · 19 · 26 · 2 feb · 9'), widestText: '5 ene 26'}),
        // WHY: French abbreviations end in a dot; a wider plot keeps them flat.
        row('L1.8', '1W fr (B6) on a wide plot', axisInput(WEEKS_B6, FR, 1100), {buckets: 7, labels: dots('29 déc. · 5 janv. 26 · 12 · 19 · 26 · 2 févr. · 9'), widestText: '5 janv. 26'}),
        // WHY: the brief's 2W example, verbatim.
        row('L1.9', '2W en', axisInput(FORTNIGHTS, EN, 527), {buckets: 8, labels: dots("Oct 6 · 20 · Nov 3 · 17 · Dec 1 · 15 · 29 · Jan 12 '26"), widestText: "Jan 12 '26"}),
        row('L1.10', '2W it', axisInput(FORTNIGHTS, IT, 527), {buckets: 8, labels: dots('6 ott · 20 · 3 nov · 17 · 1 dic · 15 · 29 · 12 gen 26'), widestText: '12 gen 26'}),
        // WHY: month rungs carry the year on the first bucket and where it changes, the bare month elsewhere.
        row('L1.11', '1M en', axisInput(MONTHS_5, EN, 527), {buckets: 5, labels: dots("Oct '25 · Nov · Dec · Jan '26 · Feb"), widestText: "Oct '25"}),
        row('L1.12', '1M it', axisInput(MONTHS_5, IT, 527), {buckets: 5, labels: dots('ott 25 · nov · dic · gen 26 · feb'), widestText: 'ott 25'}),
        // WHY: the French year form is the longest text, so it is the widest.
        row('L1.13', '1M fr', axisInput(MONTHS_5, FR, 527), {buckets: 5, labels: dots('oct. 25 · nov. · déc. · janv. 26 · févr.'), widestText: 'janv. 26'}),
        row('L1.14', '1M es', axisInput(MONTHS_5, ES, 527), {buckets: 5, labels: dots('oct 25 · nov · dic · ene 26 · feb'), widestText: 'oct 25'}),
        // WHY: quarters come from the quarterLabel stub, the year from labelWithYear.
        row('L1.15', '3M en', axisInput(QUARTERS_8, EN, 527), {buckets: 8, labels: dots("Q4 '24 · Q1 '25 · Q2 · Q3 · Q4 · Q1 '26 · Q2 · Q3"), widestText: "Q4 '24"}),
        row('L1.16', '3M it', axisInput(QUARTERS_8, IT, 527), {buckets: 8, labels: dots('T4 24 · T1 25 · T2 · T3 · T4 · T1 26 · T2 · T3'), widestText: 'T4 24'}),
        // WHY: a half is its first and last month joined by an EN DASH, no spaces.
        row('L1.17', '6M en', axisInput(HALVES_4, EN, 527), {buckets: 4, labels: dots("Jul–Dec '25 · Jan–Jun '26 · Jul–Dec · Jan–Jun '27"), widestText: "Jul–Dec '25"}),
        row('L1.18', '6M it', axisInput(HALVES_4, IT, 527), {buckets: 4, labels: dots('lug–dic 25 · gen–giu 26 · lug–dic · gen–giu 27'), widestText: 'lug–dic 25'}),
        row('L1.19', '6M fr', axisInput(HALVES_4, FR, 527), {buckets: 4, labels: dots('juil.–déc. 25 · janv.–juin 26 · juil.–déc. · janv.–juin 27'), widestText: 'juil.–déc. 25'}),
        // WHY: 1Y always shows the full year, in every locale.
        row('L1.20', '1Y en', axisInput(YEARS_3, EN, 527), {buckets: 3, labels: dots('2024 · 2025 · 2026'), widestText: '2024'}),
        row('L1.21', '1Y it', axisInput(YEARS_3, IT, 527), {buckets: 3, labels: dots('2024 · 2025 · 2026'), widestText: '2024'}),
        // WHY: a two-digit year keeps its leading zero.
        row('L1.22', '1M en across 2004/2005', axisInput(ladder('1M', '2004-11-01', '2005-02-28'), EN, 527), {buckets: 4, labels: dots("Nov '04 · Dec · Jan '05 · Feb"), widestText: "Nov '04"}),
    ]);
    // WHY: each row is one calendar case; the expected texts are Intl's forms through the stubs.
    it.each(ROWS)('$id — $name', (pinned) => expectPin(pinned));

    it('L1.23 — the stubs get the quarter as a number and the year as a two-digit string', () => {
        // WHY: the app's i18n keys interpolate both values; a numeric year would print "4" for 2004.
        const quarters: unknown[] = [];
        const years: unknown[] = [];
        const recording: Stub = {
            locale: 'en',
            labelWithYear: (label, year) => {
                years.push(year);
                return EN.labelWithYear(label, year);
            },
            quarterLabel: (quarter) => {
                quarters.push(quarter);
                return EN.quarterLabel(quarter);
            },
        };
        const lad = ladder('3M', '2004-10-01', '2005-09-30');
        const plan = planLadderAxis(axisInput(lad, recording, 527));
        expect(indexedSpec(plan.labels, lad.closingDates)).toBe(dots("Q4 '04 · Q1 '05 · Q2 · Q3"));
        expect([...new Set(quarters)].sort()).toEqual([1, 2, 3, 4]);
        expect([...new Set(years)].sort()).toEqual(['04', '05']);
    });
});

describe('L2 — a partial first bucket names its calendar start', () => {
    it('L2.1 — data from Thursday 2026-01-01 on 1W: bucket 0 is named after Monday 2025-12-29', () => {
        // WHY: the brief's own example; a label names the period, not the first day with data.
        expect(WEEKS_B6.firstDate).toBe('2026-01-01');
        expect(WEEKS_B6.closingDates[0]).toBe('2026-01-04');
        expect(calendarPeriodOf(WEEKS_B6.closingDates[0], '1W').start).toBe('2025-12-29');
        expect(planLadderAxis(axisInput(WEEKS_B6, EN, 527)).labels.get(WEEKS_B6.closingDates[0])).toBe('Dec 29');
    });
    const ROWS = pinRows([
        // WHY: 3D data from Dec 27 sits in the period that starts on Dec 26.
        row('L2.2', '3D en from 2025-12-27', axisInput(ladder('3D', '2025-12-27', '2026-01-09'), EN, 527), {buckets: 5, labels: dots("Dec 26 · 29 · Jan 1 '26 · 4 · 7"), widestText: "Jan 1 '26"}),
        // WHY: 2W data from Wednesday Oct 8 sits in the fortnight of Monday Oct 6.
        row('L2.3', '2W en from 2025-10-08', axisInput(ladder('2W', '2025-10-08', '2025-11-20'), EN, 527), {buckets: 4, labels: dots('Oct 6 · 20 · Nov 3 · 17'), widestText: 'Oct 6'}),
        // WHY: a month that starts on the 16th is still October.
        row('L2.4', '1M en from 2025-10-16', axisInput(ladder('1M', '2025-10-16', '2026-01-10'), EN, 527), {buckets: 4, labels: dots("Oct '25 · Nov · Dec · Jan '26"), widestText: "Oct '25"}),
        // WHY: a quarter that starts on Nov 20 is still Q4.
        row('L2.5', '3M en from 2025-11-20', axisInput(ladder('3M', '2025-11-20', '2026-02-10'), EN, 527), {buckets: 2, labels: dots("Q4 '25 · Q1 '26"), widestText: "Q4 '25"}),
        // WHY: a half that starts on Sep 10 is still Jul–Dec.
        row('L2.6', '6M en from 2025-09-10', axisInput(ladder('6M', '2025-09-10', '2026-02-10'), EN, 527), {buckets: 2, labels: dots("Jul–Dec '25 · Jan–Jun '26"), widestText: "Jul–Dec '25"}),
        row('L2.7', '1Y en from 2025-06-01', axisInput(ladder('1Y', '2025-06-01', '2026-02-10'), EN, 527), {buckets: 2, labels: dots('2025 · 2026'), widestText: '2025'}),
    ]);
    // WHY: every rung names a partial bucket the way it names a full one.
    it.each(ROWS)('$id — $name', (pinned) => expectPin(pinned));
});

describe('L3 — the first visible labelled bucket carries the first form', () => {
    const ROWS = pinRows([
        // WHY: on a day rung the first visible bucket takes the month, never the year, even right after New Year.
        row('L3.1', '1W en (B6), window 1..5', axisInput(WEEKS_B6, EN, 527, {window: [1, 5]}), {buckets: 7, labels: dots('Dec 29 · Jan 5 · 12 · 19 · 26 · Feb 2 · 9'), widestText: 'Jan 5'}),
        // WHY: one bucket of pan: bucket 1 compares with bucket 0 again and takes the year; bucket 2 takes the first form.
        row('L3.2', '1W en (B6), window 2..6', axisInput(WEEKS_B6, EN, 527, {window: [2, 6]}), {buckets: 7, labels: dots("Dec 29 · Jan 5 '26 · Jan 12 · 19 · 26 · Feb 2 · 9"), widestText: 'Jan 12'}),
        // WHY: the brief's example: the year does not change inside the window, so no label carries it.
        row('L3.3', '1W en from Monday 2026-01-05', axisInput(ladder('1W', '2026-01-05', '2026-02-08'), EN, 527), {buckets: 5, labels: dots('Jan 5 · 12 · 19 · 26 · Feb 2'), widestText: 'Jan 5'}),
        // WHY: on a month rung the first form carries the year.
        row('L3.4', '1M en, window 1..3', axisInput(MONTHS_5, EN, 527, {window: [1, 3]}), {buckets: 5, labels: dots("Oct '25 · Nov '25 · Dec · Jan '26 · Feb"), widestText: "Nov '25"}),
        row('L3.5', '6M en, window 2..3', axisInput(HALVES_4, EN, 527, {window: [2, 3]}), {buckets: 4, labels: dots("Jul–Dec '25 · Jan–Jun '26 · Jul–Dec '26 · Jan–Jun '27"), widestText: "Jul–Dec '26"}),
        row('L3.6', '3M it, window 2..4', axisInput(QUARTERS_8, IT, 527, {window: [2, 4]}), {buckets: 8, labels: dots('T4 24 · T1 25 · T2 25 · T3 · T4 · T1 26 · T2 · T3'), widestText: 'T2 25'}),
        // WHY: 1Y has one form, so the first visible bucket changes nothing.
        row('L3.7', '1Y en, window 1..2', axisInput(YEARS_3, EN, 527, {window: [1, 2]}), {buckets: 3, labels: dots('2024 · 2025 · 2026'), widestText: '2025'}),
    ]);
    // WHY: each row pins the first form on the first visible bucket; hidden buckets keep their own texts.
    it.each(ROWS)('$id — $name', (pinned) => expectPin(pinned));

    it('L3.8 — a pan by one bucket changes the old and the new first bucket, nothing else', () => {
        // WHY: the axis must not flicker on pan; only rule 2 moves.
        const before = planLadderAxis(axisInput(WEEKS_B6, EN, 527, {window: [1, 5]}));
        const after = planLadderAxis(axisInput(WEEKS_B6, EN, 527, {window: [2, 6]}));
        const changed = WEEKS_B6.closingDates.flatMap((raw, index) => (before.labels.get(raw) === after.labels.get(raw) ? [] : [index]));
        expect(changed).toEqual([1, 2]);
        expect([before.rotate, after.rotate]).toEqual([0, 0]);
    });
});

describe('L4 — day rungs: the year only where it changes, never on the first bucket', () => {
    const ROWS = pinRows([
        // WHY: the year appears on the bucket that starts the new year, not before and not after.
        row('L4.1', '1D en, Dec 30 to Jan 2', axisInput(ladder('1D', '2025-12-30', '2026-01-02'), EN, 527), {buckets: 4, labels: dots("Dec 30 · 31 · Jan 1 '26 · 2"), widestText: "Jan 1 '26"}),
        // WHY: a first bucket on Jan 1 is still the first form: the month, without the year.
        row('L4.2', '1D en from Jan 1', axisInput(ladder('1D', '2026-01-01', '2026-01-04'), EN, 527), {buckets: 4, labels: dots('Jan 1 · 2 · 3 · 4'), widestText: 'Jan 1'}),
        // WHY: on 2W the year lands on the first fortnight that starts in the new year.
        row('L4.3', '2W en across New Year', axisInput(ladder('2W', '2025-12-15', '2026-02-08'), EN, 527), {buckets: 4, labels: dots("Dec 15 · 29 · Jan 12 '26 · 26"), widestText: "Jan 12 '26"}),
        // WHY: the week of Dec 29 starts in 2025, so the year waits for the week of Jan 5.
        row('L4.4', '1W en across New Year', axisInput(ladder('1W', '2025-12-22', '2026-01-11'), EN, 527), {buckets: 3, labels: dots("Dec 22 · 29 · Jan 5 '26"), widestText: "Jan 5 '26"}),
        row('L4.5', '1D it, Dec 30 to Jan 2', axisInput(ladder('1D', '2025-12-30', '2026-01-02'), IT, 527), {buckets: 4, labels: dots('30 dic · 31 · 1 gen 26 · 2'), widestText: '1 gen 26'}),
    ]);
    // WHY: each row pins where the year goes on a day rung.
    it.each(ROWS)('$id — $name', (pinned) => expectPin(pinned));
});

describe('L5 — day rungs: a month change gives the MONTH form', () => {
    const ROWS = pinRows([
        // WHY: the 1st of a month names its month again, then the days go bare.
        row('L5.1', '1D en across Feb 1', axisInput(ladder('1D', '2026-01-29', '2026-02-02'), EN, 527), {buckets: 5, labels: dots('Jan 29 · 30 · 31 · Feb 1 · 2'), widestText: 'Jan 29'}),
        // WHY: 3D: the period that starts on Feb 3 is the first of February.
        row('L5.2', '3D en across Feb 1', axisInput(ladder('3D', '2026-01-25', '2026-02-08'), EN, 527), {buckets: 5, labels: dots('Jan 25 · 28 · 31 · Feb 3 · 6'), widestText: 'Jan 25'}),
        row('L5.3', '1W en across Feb 1', axisInput(ladder('1W', '2026-01-19', '2026-02-15'), EN, 527), {buckets: 4, labels: dots('Jan 19 · 26 · Feb 2 · 9'), widestText: 'Jan 19'}),
        row('L5.4', '2W en across Feb 1', axisInput(ladder('2W', '2026-01-12', '2026-03-08'), EN, 527), {buckets: 4, labels: dots('Jan 12 · 26 · Feb 9 · 23'), widestText: 'Jan 12'}),
        row('L5.5', '2W it across Feb 1', axisInput(ladder('2W', '2026-01-12', '2026-03-08'), IT, 527), {buckets: 4, labels: dots('12 gen · 26 · 9 feb · 23'), widestText: '12 gen'}),
    ]);
    // WHY: each row pins the month form on the first bucket of a new month.
    it.each(ROWS)('$id — $name', (pinned) => expectPin(pinned));
});

describe('L6 — rotation is all or nothing', () => {
    const ROWS = pinRows([
        // WHY: L1.9 on a narrower plot: one pair touches, so every label turns and none is dropped (k = 1).
        row('L6.1', '2W en on plot 400', axisInput(FORTNIGHTS, EN, 400), {buckets: 8, rotate: 45, labels: dots("Oct 6 · 20 · Nov 3 · 17 · Dec 1 · 15 · 29 · Jan 12 '26"), widestText: "Jan 12 '26"}),
        // WHY: L1.8 at plot 527: the wider French texts touch, so the whole axis turns.
        row('L6.2', '1W fr (B6) on plot 527', axisInput(WEEKS_B6, FR, 527), {buckets: 7, rotate: 45, labels: dots('29 déc. · 5 janv. 26 · 12 · 19 · 26 · 2 févr. · 9'), widestText: '5 janv. 26'}),
        // WHY: the 12 px shift that keeps "Jan 12 '26" on the canvas makes it touch "29": the axis turns and the shift is gone.
        row('L6.3', '2W en, no right room', axisInput(FORTNIGHTS, EN, 527, {leftRoomPx: 40, rightRoomPx: 0}), {buckets: 8, rotate: 45, labels: dots("Oct 6 · 20 · Nov 3 · 17 · Dec 1 · 15 · 29 · Jan 12 '26"), widestText: "Jan 12 '26"}),
    ]);
    // WHY: a turned axis keeps one text per bucket while the slot holds a text line, and never shifts.
    it.each(ROWS)('$id — $name', (pinned) => expectPin(pinned));
});

describe('L7 — the step k, only when turned', () => {
    const ALL_10 = dots('Mar 10 · 11 · 12 · 13 · 14 · 15 · 16 · 17 · 18 · 19');
    const ROWS = pinRows([
        // WHY: slot 19.7 < 20.223 (= 14.3 / √½, one 14.3 px row across the turned text): two turned neighbours would overlap, so k = 2, counted from the last bucket.
        row('L7.1', '1D, slot 19.7', axisInput(DAYS_10, EN, 197), {buckets: 10, rotate: 45, step: 2, labels: '1:Mar 11 | 3:13 | 5:15 | 7:17 | 9:19', widestText: 'Mar 11'}),
        // WHY (M‴, 08/10/2026): slot 19.9 is over the old threshold 19.799 (= 14 / √½) but under 20.223: a Chromium 14 px line is
        // 14.28 px tall, so one row is 14.3 px and 14.3 / (19.9·√½) = 1.016 gives k = 2. Re-pinned: it was k = 1, every label.
        row('L7.2', '1D, slot 19.9', axisInput(DAYS_10, EN, 199), {buckets: 10, rotate: 45, step: 2, labels: '1:Mar 11 | 3:13 | 5:15 | 7:17 | 9:19', widestText: 'Mar 11'}),
        // WHY: L0 counts from the last bucket of the series, not of the window.
        row('L7.3', '1D 12 buckets, window 0..9', axisInput(DAYS_12, EN, 197, {window: [0, 9]}), {buckets: 12, rotate: 45, step: 2, labels: '1:Mar 11 | 3:13 | 5:15 | 7:17 | 9:19 | 11:21', widestText: 'Mar 11'}),
        // WHY: the same set after a pan by two; only the first visible labelled bucket changes text.
        row('L7.4', '1D 12 buckets, window 2..11', axisInput(DAYS_12, EN, 197, {window: [2, 11]}), {buckets: 12, rotate: 45, step: 2, labels: '1:Mar 11 | 3:Mar 13 | 5:15 | 7:17 | 9:19 | 11:21', widestText: 'Mar 13'}),
        // WHY: k scales with the font: 12 px text fits a 17.5 px slot turned (12·(14.3/14) / (17.5·√½) = 0.99).
        row('L7.5', '1D, slot 17.5, font 12', axisInput(DAYS_10, EN, 175, {fontSizePx: 12}), {buckets: 10, rotate: 45, labels: ALL_10, widestText: 'Mar 10'}),
        row('L7.6', '1D, slot 17.5, font 14', axisInput(DAYS_10, EN, 175), {buckets: 10, rotate: 45, step: 2, labels: '1:Mar 11 | 3:13 | 5:15 | 7:17 | 9:19', widestText: 'Mar 11'}),
        // WHY: Income's minimum slot (4.5 / 0.21875 = 20.571 px) is over the threshold 20.223 (14.3 / (20.571·√½) = 0.983): Income is never thinned.
        row('L7.7', '1M at Income minimum slot', axisInput(MONTHS_2025, EN, 12 * INCOME_MIN_SLOT_PX), {buckets: 12, rotate: 45, labels: dots("Jan '25 · Feb · Mar · Apr · May · Jun · Jul · Aug · Sep · Oct · Nov · Dec"), widestText: "Jan '25"}),
        // WHY (M‴): slot 20.0, still under 20.223 (14.3 / (20·√½) = 1.011): k = 2, the set of L7.1.
        row('L7.9', '1D, slot 20.0', axisInput(DAYS_10, EN, 200), {buckets: 10, rotate: 45, step: 2, labels: '1:Mar 11 | 3:13 | 5:15 | 7:17 | 9:19', widestText: 'Mar 11'}),
        // WHY (M‴): slot 20.3 is just over the row's threshold (14.3 / (20.3·√½) = 0.996): k = 1, every label.
        row('L7.10', '1D, slot 20.3', axisInput(DAYS_10, EN, 203), {buckets: 10, rotate: 45, labels: ALL_10, widestText: 'Mar 10'}),
    ]);
    // WHY: each row pins k and the labelled set L0 = {i : (n − 1 − i) % k = 0}.
    it.each(ROWS)('$id — $name', (pinned) => expectPin(pinned));

    it('L7.8 — at the Income minimum slot every window keeps step 1 and every visible label', () => {
        // WHY: Income bars never go below 4.5 px, so its axis is never thinned, whatever the zoom.
        const failures: string[] = [];
        for (let visible = 1; visible <= MONTHS_24.closingDates.length; visible++) {
            const input = axisInput(MONTHS_24, EN, visible * INCOME_MIN_SLOT_PX, {window: [24 - visible, 23]});
            const plan = planLadderAxis(input);
            const missing = MONTHS_24.closingDates.slice(24 - visible).filter((raw) => !plan.labels.has(raw));
            if (plan.step !== 1 || missing.length > 0) failures.push(`${visible} visible: step ${plan.step}, ${missing.length} unlabelled`);
        }
        expect(failures).toEqual([]);
    });
});

describe('L8 — the turned edge labels that would leave the canvas are dropped', () => {
    const ROWS = pinRows([
        // WHY: with no left room the turned "Mar 10" and "Mar 11" reach left of the canvas; "Mar 12" is the first to stay and takes the first form.
        // Slot 20.3 (plot 203; was 199 before M‴, where the 14.3 px row now thins to k = 2): k = 1, so the drops alone are pinned.
        row('L8.1', '1D slot 20.3, left room 0', axisInput(DAYS_10, EN, 203, {leftRoomPx: 0, rightRoomPx: 60}), {buckets: 10, rotate: 45, labels: '2:Mar 12 | 3:13 | 4:14 | 5:15 | 6:16 | 7:17 | 8:18 | 9:19', widestText: 'Mar 12'}),
        // WHY: the Income view at its minimum slot: the first form moves to December and keeps the year.
        row('L8.2', 'Income 1M, left room 0', axisInput(MONTHS_INCOME, EN, 12 * INCOME_MIN_SLOT_PX, {leftRoomPx: 0, rightRoomPx: 60}), {buckets: 12, rotate: 45, labels: "2:Dec '25 | 3:Jan '26 | 4:Feb | 5:Mar | 6:Apr | 7:May | 8:Jun | 9:Jul | 10:Aug | 11:Sep", widestText: "Dec '25"}),
        // WHY: slot 13 < 13.9: half a text line past the last centre crosses a zero right room, so bucket 19 is dropped.
        row('L8.3', '1D 20 buckets, right room 0', axisInput(DAYS_20, EN, 260, {leftRoomPx: 40, rightRoomPx: 0}), {buckets: 20, rotate: 45, step: 2, labels: '1:Mar 11 | 3:13 | 5:15 | 7:17 | 9:19 | 11:21 | 13:23 | 15:25 | 17:27', widestText: 'Mar 11'}),
        // WHY: an undefined room is unlimited: nothing is dropped.
        row('L8.4', '1D 20 buckets, rooms undefined', axisInput(DAYS_20, EN, 260), {buckets: 20, rotate: 45, step: 2, labels: '1:Mar 11 | 3:13 | 5:15 | 7:17 | 9:19 | 11:21 | 13:23 | 15:25 | 17:27 | 19:29', widestText: 'Mar 11'}),
        row('L8.5', 'Income 1M, rooms undefined', axisInput(MONTHS_INCOME, EN, 12 * INCOME_MIN_SLOT_PX), {buckets: 12, rotate: 45, labels: dots("Oct '25 · Nov · Dec · Jan '26 · Feb · Mar · Apr · May · Jun · Jul · Aug · Sep"), widestText: "Oct '25"}),
        // WHY: the rooms act one side at a time: a right room alone drops on the right only.
        row('L8.6', '1D 20 buckets, right room only', axisInput(DAYS_20, EN, 260, {rightRoomPx: 0}), {buckets: 20, rotate: 45, step: 2, labels: '1:Mar 11 | 3:13 | 5:15 | 7:17 | 9:19 | 11:21 | 13:23 | 15:25 | 17:27', widestText: 'Mar 11'}),
        // WHY: a left room alone drops on the left only, and the first form moves to the next candidate of L0.
        row('L8.7', '1D 20 buckets, left room only', axisInput(DAYS_20, EN, 260, {leftRoomPx: 0}), {buckets: 20, rotate: 45, step: 2, labels: '3:Mar 13 | 5:15 | 7:17 | 9:19 | 11:21 | 13:23 | 15:25 | 17:27 | 19:29', widestText: 'Mar 13'}),
    ]);
    // WHY: each row pins the drops against the geometry of a 45° label: it reaches (w + h/2)·√½ left and (h/2)·√½ right of its tick.
    it.each(ROWS)('$id — $name', (pinned) => expectPin(pinned));
});

describe('L9 — widestText, the formatter fallback, rotate in the option and in the key', () => {
    const APR_SEP = dots("Apr '26 · May · Jun · Jul · Aug · Sep");
    const ROWS = pinRows([
        // WHY: the only visible candidate (9) is dropped on the right: hidden labels stay, and no visible label means no widest text.
        // The slot is 20 / 2 = 10 px, so the 14.3 px row gives k = 3 (14.3 / (10·√½) = 2.02; M‴, re-pinned from k = 2,
        // 14 / (10·√½) = 1.98): L0 = {0, 3, 6, 9}, 8 is not a candidate, 9 is dropped, 0, 3 and 6 keep their texts.
        row('L9.1', '1D window 8..9 on a 20 px plot', axisInput(DAYS_10, EN, 20, {window: [8, 9], leftRoomPx: 40, rightRoomPx: 0}), {buckets: 10, rotate: 45, step: 3, labels: '0:Mar 10 | 3:13 | 6:16', widestText: ''}),
        // WHY: the brief's key example, flat at plot 527 (slot 87.8)…
        row('L9.4a', '1M Apr–Sep 2026 on plot 527', axisInput(MONTHS_APR_SEP, EN, 527), {buckets: 6, labels: APR_SEP, widestText: "Apr '26"}),
        // WHY: …and turned at plot 200 (slot 33.3, k = 1): the same labels, separators, shifts and widest text.
        row('L9.4b', '1M Apr–Sep 2026 on plot 200', axisInput(MONTHS_APR_SEP, EN, 200), {buckets: 6, rotate: 45, labels: APR_SEP, widestText: "Apr '26"}),
    ]);
    // WHY: widestText is read over the visible labelled buckets only.
    it.each(ROWS)('$id — $name', (pinned) => expectPin(pinned));

    it('L9.2 — an unlabelled raw formats as the widest text', () => {
        // WHY: ECharts' legacy containLabel samples the formatter and ignores interval; turned, a label is as tall as it is wide.
        const [c0, c1, , c3] = DAYS_10.closingDates;
        const plan = planLadderAxis(axisInput(DAYS_10, EN, 197));
        expect(plan.widestText).toBe('Mar 11');
        const option = ladderAxisOption(plan);
        const axisLabel = axisLabelOf(option);
        expect([c0, c1, c3, '1999-01-01'].map((raw) => axisLabel.formatter(raw))).toEqual(['Mar 11', 'Mar 11', '13', 'Mar 11']);
        expect([axisLabel.interval(0, c1), axisLabel.interval(1, c0)]).toEqual([true, false]);
        expect(option.splitLine.interval(5, c0)).toBe(true);
        expect(axisLabel.rotate).toBe(45);
        expect(axisLabel.rich).toEqual({});
    });

    it('L9.3 — the option always carries rotate, 0 included', () => {
        // WHY: GrowthChart applies the axis as a partial update; without an explicit 0 a turned axis would stay turned.
        const flat = axisLabelOf(ladderAxisOption(planLadderAxis(axisInput(FORTNIGHTS, EN, 527))));
        const turned = axisLabelOf(ladderAxisOption(planLadderAxis(axisInput(FORTNIGHTS, EN, 400))));
        expect(['rotate' in flat, 'rotate' in turned]).toEqual([true, true]);
        expect([flat.rotate, turned.rotate]).toEqual([0, 45]);
    });

    it('L9.4 — the same labels flat and turned give different keys', () => {
        // WHY: the component re-applies the axis only when the key changes, so turning alone must change it.
        const flatRow = rowById(ROWS, 'L9.4a');
        const turnedRow = rowById(ROWS, 'L9.4b');
        expectPin(flatRow);
        expectPin(turnedRow);
        const flat = planLadderAxis(flatRow.input);
        const turned = planLadderAxis(turnedRow.input);
        expect(separatorIndices(flat.separators, MONTHS_APR_SEP.closingDates)).toEqual([0, 1, 2, 3, 4, 5]);
        expect(separatorIndices(turned.separators, MONTHS_APR_SEP.closingDates)).toEqual([0, 1, 2, 3, 4, 5]);
        expect([flat.key === '', turned.key === '']).toEqual([false, false]);
        expect(turned.key).not.toBe(flat.key);
    });

    it('L9.5 — equal inputs give equal keys, a different text a different key', () => {
        // WHY: the key is the component's only change detector: stable for a copy, different as soon as a label differs.
        const reference = planLadderAxis(axisInput(WEEKS_B6, EN, 527));
        const copy = planLadderAxis(axisInput({...WEEKS_B6, closingDates: [...WEEKS_B6.closingDates]}, EN, 527));
        const italian = planLadderAxis(axisInput(WEEKS_B6, IT, 527));
        expect(reference.key).not.toBe('');
        expect(copy.key).toBe(reference.key);
        expect(italian.key).not.toBe(reference.key);
    });
});

describe('L10 — texts follow the labelled set, not the bucket order', () => {
    const ROWS = pinRows([
        // WHY: thinned by 2, each remaining label compares with the previous LABELLED one, so every label changes month.
        row('L10.1', '2W en on plot 120', axisInput(FORTNIGHTS, EN, 120), {buckets: 8, rotate: 45, step: 2, labels: "1:Oct 20 | 3:Nov 17 | 5:Dec 15 | 7:Jan 12 '26", widestText: "Jan 12 '26"}),
        row('L10.2', '2W it on plot 120', axisInput(FORTNIGHTS, IT, 120), {buckets: 8, rotate: 45, step: 2, labels: '1:20 ott | 3:17 nov | 5:15 dic | 7:12 gen 26', widestText: '12 gen 26'}),
        // WHY: slot 8 gives k = 3 (14.3 / (8·√½) = 2.53); the year lands on the first labelled month of 2026, March.
        row('L10.3', '1M en 24 months on plot 192', axisInput(MONTHS_24, EN, 192), {buckets: 24, rotate: 45, step: 3, labels: "2:Mar '25 | 5:Jun | 8:Sep | 11:Dec | 14:Mar '26 | 17:Jun | 20:Sep | 23:Dec", widestText: "Mar '25"}),
    ]);
    // WHY: each row pins the rules applied over L, not over every bucket.
    it.each(ROWS)('$id — $name', (pinned) => expectPin(pinned));
});

interface SeparatorRow {
    id: string;
    name: string;
    input: LadderAxisInput;
    buckets: number;
    separators: number[];
}
const range = (from: number, to: number): number[] => Array.from({length: to - from + 1}, (_, offset) => from + offset);

/** The separator rule of D4, unchanged by this contract: pinned on the new input, replayed by L14-self through the oracle. */
const SEPARATOR_ROWS: SeparatorRow[] = [
    // WHY: daily slots under 8 px keep separators on month edges only; a lone visible edge also anchors the first visible bucket.
    {id: 'L11.1', name: '1D Aug 17..Sep 30 on plot 327 (anchor)', input: axisInput(ladder('1D', '2026-08-17', '2026-09-30'), EN, 327), buckets: 45, separators: [0, 15]},
    // WHY: two visible month edges: no anchor.
    {id: 'L11.2', name: '1D Jul 20..Sep 30 on plot 327', input: axisInput(ladder('1D', '2026-07-20', '2026-09-30'), EN, 327), buckets: 73, separators: [12, 43]},
    // WHY: the lone edge is the first visible bucket itself: no anchor.
    {id: 'L11.3', name: '1D Sep 1..30 on plot 200', input: axisInput(ladder('1D', '2026-09-01', '2026-09-30'), EN, 200), buckets: 30, separators: [0]},
    {id: 'L11.4', name: 'Ex1 on plot 40 (anchor)', input: axisInput(EX1, EN, 40), buckets: 31, separators: [0, 1]},
    {id: 'L11.5', name: 'Ex1 window 1..30 on plot 40', input: axisInput(EX1, EN, 40, {window: [1, 30]}), buckets: 31, separators: [1]},
    // WHY: no visible edge at all: nothing to anchor, and the hidden edge keeps its separator.
    {id: 'L11.6', name: 'Ex1 window 2..30 on plot 40', input: axisInput(EX1, EN, 40, {window: [2, 30]}), buckets: 31, separators: [1]},
    // WHY: the anchor follows the window: 44 is the first visible bucket, 68 the lone visible edge.
    {id: 'L11.7', name: 'Ex3 window 44..91 on plot 327 (anchor)', input: axisInput(EX3, EN, 327, {window: [44, 91]}), buckets: 92, separators: [6, 37, 44, 68]},
    {id: 'L11.8', name: 'Ex3 on plot 527', input: axisInput(EX3, EN, 527), buckets: 92, separators: [6, 37, 68]},
    // WHY: slots of 8 px or more keep a separator on every bucket.
    {id: 'L11.9', name: '2W on plot 527', input: axisInput(FORTNIGHTS, EN, 527), buckets: 8, separators: range(0, 7)},
    // WHY: bucket 0 covers from firstDate, Jan 1 itself.
    {id: 'L11.10', name: '1W (B6) on plot 50', input: axisInput(WEEKS_B6, EN, 50), buckets: 7, separators: [0, 4]},
    {id: 'L11.11', name: '1M 24 months on plot 150', input: axisInput(MONTHS_24, EN, 150), buckets: 24, separators: range(0, 23)},
    // WHY: a first month that starts on the 15th covers no 1st.
    {id: 'L11.12', name: '1M from Jan 15 on plot 150', input: axisInput(ladder('1M', '2025-01-15', '2026-12-31'), EN, 150), buckets: 24, separators: range(1, 23)},
];

describe('L11 — separators unchanged (green on the old planner, on purpose)', () => {
    // WHY: the new contract changes the labels only; a red here means the rewrite touched the separators.
    it.each(SEPARATOR_ROWS)('$id — $name', ({id, name, input, buckets, separators}) => {
        expect(input.closingDates.length, `${id} fixture`).toBe(buckets);
        expect(separatorIndices(planLadderAxis(input).separators, input.closingDates), `${id} ${name}`).toEqual(separators);
    });
});

describe('L12 — the empty plan', () => {
    // WHY `labelBox: null` (M‴): the empty plan reserves no box, and `toEqual` counts a null-valued key.
    const EMPTY = {rotate: 0, step: 1, labels: new Map(), widestText: '', separators: new Set(), edgeShifts: new Map(), labelBox: null, key: ''};
    const NO_BUCKETS: LadderAxisInput = {...axisInput(WEEKS_B6, EN, 527), closingDates: [], visibleStartIndex: 0, visibleEndIndex: 0};
    const CASES: Array<{id: string; name: string; input: LadderAxisInput}> = [
        {id: 'L12.1', name: 'no buckets', input: NO_BUCKETS},
        {id: 'L12.2', name: 'plot 0', input: axisInput(WEEKS_B6, EN, 0)},
        {id: 'L12.3', name: 'plot NaN', input: axisInput(WEEKS_B6, EN, Number.NaN)},
        {id: 'L12.4', name: 'negative plot', input: axisInput(WEEKS_B6, EN, -5)},
        {id: 'L12.5', name: 'infinite plot', input: axisInput(WEEKS_B6, EN, Number.POSITIVE_INFINITY)},
    ];
    // WHY: before the chart is measured, or with no data, the planner answers a plan that draws nothing, and never throws.
    it.each(CASES)('$id — $name', ({id, input}) => {
        expect(planLadderAxis(input), id).toEqual(EMPTY);
    });

    it('L12.6 — the option of the empty plan draws nothing, unturned', () => {
        // WHY: rotate 0 resets a turned axis; '' from the formatter keeps containLabel from reserving room.
        const option = ladderAxisOption(planLadderAxis(NO_BUCKETS));
        const axisLabel = axisLabelOf(option);
        const [c0, , , , , , c6] = WEEKS_B6.closingDates;
        expect(axisLabel.rotate).toBe(0);
        expect([c0, c6, '1999-01-01'].map((raw) => axisLabel.formatter(raw))).toEqual(['', '', '']);
        expect([axisLabel.interval(0, c0), option.splitLine.interval(0, c0)]).toEqual([false, false]);
        expect(axisLabel.rich).toEqual({});
    });
});

describe('L13 — windows, edge shifts and the option of a flat plan', () => {
    const L3_1 = {buckets: 7, labels: dots('Dec 29 · Jan 5 · 12 · 19 · 26 · Feb 2 · 9'), widestText: 'Jan 5'};
    const L1_5 = {buckets: 7, labels: dots("Dec 29 · Jan 5 '26 · 12 · 19 · 26 · Feb 2 · 9"), widestText: "Jan 5 '26"};
    const MONTHS_5_LAST = dots("Oct '25 · Nov · Dec · Jan '26 · Feb '26");
    const ROWS = pinRows([
        // WHY: a reversed window is swapped.
        row('L13.1', '1W en (B6), window 5..1', axisInput(WEEKS_B6, EN, 527, {window: [5, 1]}), L3_1),
        // WHY: fractional indices are rounded, as dataZoom reports them.
        row('L13.2', '1W en (B6), window 0.6..4.6', axisInput(WEEKS_B6, EN, 527, {window: [0.6, 4.6]}), L3_1),
        // WHY: out-of-range indices are clamped to the series.
        row('L13.3', '1W en (B6), window −3..99', axisInput(WEEKS_B6, EN, 527, {window: [-3, 99]}), L1_5),
        // WHY: a flat axis keeps the D4 shift: 6 px left keeps "Jan 12 '26" 2 px inside a 6 px room, and its gap to "29" stays ≥ 8.
        row('L13.5', '2W en, right room 6', axisInput(FORTNIGHTS, EN, 527, {leftRoomPx: 40, rightRoomPx: 6}), {buckets: 8, labels: dots("Oct 6 · 20 · Nov 3 · 17 · Dec 1 · 15 · 29 · Jan 12 '26"), widestText: "Jan 12 '26", edgeShifts: '7:-6'}),
        // WHY: with no left room "Mar 10" moves right by ceil(2.2) = 3 px.
        row('L13.6', '1D en, rooms 0', axisInput(DAYS_10, EN, 500, {leftRoomPx: 0, rightRoomPx: 0}), {buckets: 10, labels: dots('Mar 10 · 11 · 12 · 13 · 14 · 15 · 16 · 17 · 18 · 19'), widestText: 'Mar 10', edgeShifts: '0:3'}),
        // WHY: a one-bucket window: its label is both edges and the two shifts add up (+12 − 2).
        row('L13.7', '1M en, window 4..4, rooms 0 and 10', axisInput(MONTHS_5, EN, 40, {window: [4, 4], leftRoomPx: 0, rightRoomPx: 10}), {buckets: 5, labels: MONTHS_5_LAST, widestText: "Feb '26", edgeShifts: '4:10'}),
        // WHY: the two shifts cancel (+12 − 12), and a zero shift is deleted.
        row('L13.8', '1M en, window 4..4, rooms 0 and 0', axisInput(MONTHS_5, EN, 40, {window: [4, 4], leftRoomPx: 0, rightRoomPx: 0}), {buckets: 5, labels: MONTHS_5_LAST, widestText: "Feb '26"}),
    ]);
    // WHY: each row pins a window normalisation or a flat edge shift.
    it.each(ROWS)('$id — $name', (pinned) => expectPin(pinned));

    it('L13.4 — normalised windows give the key of the window they normalise to', () => {
        // WHY: a key that followed the raw indices would re-apply an unchanged axis on every dataZoom event.
        const key = (window: readonly [number, number]) => planLadderAxis(axisInput(WEEKS_B6, EN, 527, {window})).key;
        const middle = key([1, 5]);
        const full = key([0, 6]);
        expect([key([5, 1]), key([0.6, 4.6]), key([-3, 99])]).toEqual([middle, middle, full]);
        expect(middle).not.toBe(full);
    });

    it('L13.9 — a shifted label is wrapped in its rich style, the others are not', () => {
        // WHY: ECharts moves a centred label by padding its far side; twice the shift moves it by the shift.
        const leftLabel = axisLabelOf(ladderAxisOption(planLadderAxis(rowById(ROWS, 'L13.5').input)));
        expect([leftLabel.formatter(FORTNIGHTS.closingDates[7]), leftLabel.formatter(FORTNIGHTS.closingDates[6])]).toEqual(["{lfShiftL6|Jan 12 '26}", '29']);
        expect(leftLabel.rich).toEqual({lfShiftL6: {padding: [0, 12, 0, 0]}});
        const rightLabel = axisLabelOf(ladderAxisOption(planLadderAxis(rowById(ROWS, 'L13.6').input)));
        expect([rightLabel.formatter(DAYS_10.closingDates[0]), rightLabel.formatter(DAYS_10.closingDates[1])]).toEqual(['{lfShiftR3|Mar 10}', '11']);
        expect(rightLabel.rich).toEqual({lfShiftR3: {padding: [0, 0, 0, 6]}});
        expect([leftLabel.rotate, rightLabel.rotate]).toEqual([0, 0]);
    });

    it('L13.10 — a flat option labels and separates every raw, whatever the index', () => {
        // WHY: ECharts passes its own category index; the option answers by raw value.
        const option = ladderAxisOption(planLadderAxis(axisInput(WEEKS_B6, EN, 527)));
        const axisLabel = axisLabelOf(option);
        const closings = WEEKS_B6.closingDates;
        expect(closings.map((raw, index) => axisLabel.interval(closings.length - 1 - index, raw))).toEqual(closings.map(() => true));
        expect(closings.map((raw, index) => option.splitLine.interval(closings.length - 1 - index, raw))).toEqual(closings.map(() => true));
        expect(closings.map((raw) => axisLabel.formatter(raw))).toEqual(['Dec 29', "Jan 5 '26", '12', '19', '26', 'Feb 2', '9']);
        expect(axisLabel.rotate).toBe(0);
        expect(axisLabel.rich).toEqual({});
    });

    it('L13.11 — the width estimate and the two distances (green on the old planner)', () => {
        // WHY: every flat or turned decision pinned above is computed with these numbers.
        expect(estimateLadderLabelWidthPx("Jan 12 '26")).toBeCloseTo(84, 9);
        expect(estimateLadderLabelWidthPx("Jan 12 '26", 12)).toBeCloseTo(72, 9);
        expect([LADDER_LABEL_GAP_PX, LADDER_EDGE_SAFETY_PX]).toEqual([GAP_PX, SAFETY_PX]);
    });
});

// ─── L14: the oracle sweep, every rung × two stubs × 4 plots × 13 windows × 5 rooms ───

const SWEEP_FIRST = '2024-10-16';
const SWEEP_LAST = '2026-09-24';
const SWEEP_RUNGS: readonly LadderRung[] = ['1D', '3D', '1W', '2W', '1M', '3M', '6M', '1Y'];
const SWEEP_STUBS: readonly Stub[] = [EN, IT];
const SWEEP_PLOTS: readonly number[] = [120, 327, 527, 1100];
const SWEEP_ROOMS: ReadonlyArray<{name: string; geometry: Geometry}> = [
    {name: 'no rooms', geometry: {}},
    {name: 'rooms 40/12', geometry: {leftRoomPx: 40, rightRoomPx: 12}},
    {name: 'rooms 0/0', geometry: {leftRoomPx: 0, rightRoomPx: 0}},
    {name: 'left room 0', geometry: {leftRoomPx: 0}},
    {name: 'right room 0', geometry: {rightRoomPx: 0}},
];
const ISO_DAY = /\d{4}-\d{2}-\d{2}/;

/** 13 windows: whole, partial, degenerate, reversed, out of range, and both sides of the first 2026 bucket. */
function sweepWindows(n: number, newYear: number): Array<[string, readonly [number, number]]> {
    const half = Math.floor(n / 2);
    return [
        ['full', [0, n - 1]],
        ['last30%', [Math.floor(0.7 * n), n - 1]],
        ['first30%', [0, Math.ceil(0.3 * n) - 1]],
        ['mid50%', [Math.floor(0.25 * n), Math.floor(0.75 * n)]],
        ['last2', [n - 2, n - 1]],
        ['single', [half, half]],
        ['reversed', [n - 1, 0]],
        ['outOfRange', [-5, n + 5]],
        ['last31', [n - 31, n - 1]],
        ['last45', [n - 45, n - 1]],
        ['last20', [n - 20, n - 1]],
        ['toYear', [newYear - 4, newYear]],
        ['fromYear', [newYear, newYear + 4]],
    ];
}

/** What the oracle alone says the grid reached: L14a proves the sweep is not vacuous. */
interface Coverage {
    cases: number;
    flat: number;
    rotatedK1: number;
    rotatedK2: number;
    leftDrop: number;
    rightDrop: number;
    movedFirst: number;
    positiveShift: number;
    negativeShift: number;
    anchor: number;
    rule2WithPrevious: number;
    rule3Visible: number;
    rule4Visible: number;
    ambiguous: number;
    rungsFlat: Set<LadderRung>;
    rungsRotated: Set<LadderRung>;
}

function countCoverage(coverage: Coverage, rung: LadderRung, oracle: OracleCase): void {
    coverage.cases++;
    if (oracle.decision === 'either' || (oracle.decision === 'rotated' && oracle.rotatedAmbiguous)) coverage.ambiguous++;
    if (oracle.anchor) coverage.anchor++;
    if (oracle.decision === 'flat') {
        coverage.flat++;
        coverage.rungsFlat.add(rung);
        for (const px of oracle.flat.exactShifts.values()) {
            if (px > 0) coverage.positiveShift++;
            if (px < 0) coverage.negativeShift++;
        }
    }
    if (oracle.decision === 'rotated') {
        coverage.rungsRotated.add(rung);
        if (oracle.rotated.step === 1) coverage.rotatedK1++;
        else coverage.rotatedK2++;
        if (oracle.leftDropped > 0) coverage.leftDrop++;
        if (oracle.rightDropped > 0) coverage.rightDrop++;
        if (oracle.leftDropped > 0 && oracle.rotated.first !== undefined) coverage.movedFirst++;
    }
    if (oracle.decision === 'either') return;
    const branch = oracle.decision === 'flat' ? oracle.flat : oracle.rotated;
    const first = branch.first;
    if (first !== undefined && branch.texts.slice(0, first).some((text) => text !== undefined)) coverage.rule2WithPrevious++;
    for (let index = oracle.vs; index <= oracle.ve; index++) {
        if (index === first) continue;
        if (branch.rules[index] === 3) coverage.rule3Visible++;
        if (branch.rules[index] === 4) coverage.rule4Visible++;
    }
}

/** L14b: the separators of D4, bucket by bucket. Linear in n: the sweep runs 709-bucket series. */
function separatorDiff(plan: LadderAxisPlan, oracle: OracleCase, closings: readonly string[]): string | undefined {
    for (let index = 0; index < closings.length; index++) {
        const expected = oracle.separators.has(index);
        if (plan.separators.has(closings[index]) !== expected) return `separator ${index} ${expected ? 'missing' : 'unexpected'}`;
    }
    const extra = plan.separators.size - oracle.separators.size;
    return extra === 0 ? undefined : `${extra} separator(s) on raws that are not closing dates`;
}

function shiftDiff(plan: LadderAxisPlan, branch: Branch, closings: readonly string[], at: ReadonlyMap<string, number>): string | undefined {
    if (branch.rotate === 45) return plan.edgeShifts.size === 0 ? undefined : `${plan.edgeShifts.size} shift(s) on a turned axis`;
    for (const [raw, px] of plan.edgeShifts) {
        const index = at.get(raw);
        const choices = index === undefined ? undefined : branch.shiftChoices.get(index);
        if (choices === undefined) return `shift on ${raw}, which is not a visible edge`;
        if (px === 0 || !choices.includes(px)) return `shift ${px} on ${index}, oracle ${choices.join('|')}`;
    }
    for (const [index, choices] of branch.shiftChoices) if (!choices.includes(0) && !plan.edgeShifts.has(closings[index])) return `no shift on ${index}, oracle ${choices.join('|')}`;
    return undefined;
}

/** L14c: the plan against the oracle's branch; 'either' follows the plan's own rotate, a turned float boundary is skipped. */
function oracleDiff(plan: LadderAxisPlan, oracle: OracleCase, closings: readonly string[], at: ReadonlyMap<string, number>): string | undefined {
    if (oracle.decision === 'flat' && plan.rotate !== 0) return `rotate ${String(plan.rotate)}, oracle flat`;
    if (oracle.decision === 'rotated' && plan.rotate !== 45) return `rotate ${String(plan.rotate)}, oracle turned`;
    if (oracle.decision === 'either' && plan.rotate !== 0 && plan.rotate !== 45) return `rotate ${String(plan.rotate)}`;
    const branch = plan.rotate === 0 ? oracle.flat : oracle.rotated;
    if (branch.rotate === 45 && oracle.rotatedAmbiguous) return undefined;
    if (plan.step !== branch.step) return `step ${plan.step}, oracle ${branch.step}`;
    let labelled = 0;
    for (let index = 0; index < closings.length; index++) {
        const expected = branch.texts[index];
        if (expected !== undefined) labelled++;
        const actual = plan.labels.get(closings[index]);
        if (actual !== expected) return `label ${index} ${JSON.stringify(actual)}, oracle ${JSON.stringify(expected)}`;
    }
    if (plan.labels.size !== labelled) return `${plan.labels.size - labelled} label(s) on raws that are not closing dates`;
    const shiftProblem = shiftDiff(plan, branch, closings, at);
    if (shiftProblem !== undefined) return shiftProblem;
    return plan.widestText === branch.widestText ? undefined : `widestText ${JSON.stringify(plan.widestText)}, oracle ${JSON.stringify(branch.widestText)}`;
}

/** L14d: what the contract says of any plan, whatever the oracle decided. */
function propertyDiff(plan: LadderAxisPlan, oracle: OracleCase, closings: readonly string[]): string | undefined {
    if (plan.rotate !== 0 && plan.rotate !== 45) return `rotate ${String(plan.rotate)}`;
    let previous: string | undefined;
    for (let index = 0; index < closings.length; index++) {
        const text = plan.labels.get(closings[index]);
        if (text === undefined) continue;
        if (text === previous) return `bucket ${index} repeats ${JSON.stringify(text)}`;
        previous = text;
    }
    if (plan.rotate === 45) {
        if (plan.edgeShifts.size > 0) return `${plan.edgeShifts.size} shift(s) on a turned axis`;
        return Number.isInteger(plan.step) && plan.step >= 1 ? undefined : `turned step ${plan.step}`;
    }
    if (plan.step !== 1) return `flat step ${plan.step}`;
    if (plan.labels.size !== closings.length || closings.some((raw) => !plan.labels.has(raw))) return 'flat with an unlabelled bucket';
    // WHY: a flat plan must fit with its own texts and shifts: 8 px between every two visible neighbours.
    const edge = (index: number, side: -1 | 1) => {
        const raw = closings[index];
        return (index - oracle.vs + 0.5) * oracle.slot + (plan.edgeShifts.get(raw) ?? 0) + (side * ((plan.labels.get(raw) ?? '').length * DEFAULT_FONT_PX * 0.6)) / 2;
    };
    for (let index = oracle.vs + 1; index <= oracle.ve; index++) {
        const gap = edge(index, -1) - edge(index - 1, 1);
        if (gap < GAP_PX - EPS) return `flat gap ${gap.toFixed(3)} px between ${index - 1} and ${index}`;
    }
    return undefined;
}

const sortedJson = (record: object): string => JSON.stringify(Object.entries(record).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));

/** Keys seen in one series: a key names one plan. */
interface KeyBook {
    byKey: Map<string, string>;
}

/** L14e: the ECharts option answers by raw value from the plan, and a key never stands for two different plans. */
function optionDiff(plan: LadderAxisPlan, closings: readonly string[], book: KeyBook): string | undefined {
    const option = ladderAxisOption(plan);
    const axisLabel = axisLabelOf(option);
    if (!('rotate' in axisLabel) || axisLabel.rotate !== plan.rotate) return `option rotate ${String(axisLabel.rotate)}, plan ${String(plan.rotate)}`;
    const rich: Record<string, {padding: [number, number, number, number]}> = {};
    for (const px of plan.edgeShifts.values()) if (px !== 0) rich[shiftStyle(px)] = {padding: shiftPadding(px)};
    if (sortedJson(axisLabel.rich) !== sortedJson(rich)) return `rich ${JSON.stringify(axisLabel.rich)}`;
    const n = closings.length;
    for (let index = 0; index < n; index++) {
        const raw = closings[index];
        // WHY: the index ECharts passes is its own; called with a wrong one, the option must still answer by raw.
        if (axisLabel.interval(n - 1 - index, raw) !== plan.labels.has(raw)) return `axisLabel.interval on ${index}`;
        if (option.splitLine.interval(n - 1 - index, raw) !== plan.separators.has(raw)) return `splitLine.interval on ${index}`;
        const text = plan.labels.get(raw);
        const px = plan.edgeShifts.get(raw) ?? 0;
        const expected = text === undefined ? plan.widestText : px === 0 ? text : `{${shiftStyle(px)}|${text}}`;
        const actual = axisLabel.formatter(raw);
        if (actual !== expected) return `formatter on ${index} ${JSON.stringify(actual)}, expected ${JSON.stringify(expected)}`;
        if (ISO_DAY.test(actual)) return `formatter on ${index} prints a raw date`;
    }
    if (axisLabel.formatter('1999-01-01') !== plan.widestText) return 'formatter on an unknown raw is not widestText';
    if (typeof plan.key !== 'string' || plan.key === '') return `key ${JSON.stringify(plan.key)}`;
    // WHY: an index-ordered digest of the plan, so the check does not depend on how the planner fills its maps.
    const digest = JSON.stringify([
        plan.rotate,
        plan.step,
        closings.map((raw) => plan.labels.get(raw) ?? null),
        closings.map((raw) => (plan.separators.has(raw) ? 1 : 0)).join(''),
        closings.flatMap((raw, index) => (plan.edgeShifts.has(raw) ? [[index, plan.edgeShifts.get(raw)]] : [])),
        plan.widestText,
    ]);
    // WHY: a stale key would leave a changed axis on screen; only this direction follows from the key formula, whose entry order is not pinned.
    const knownDigest = book.byKey.get(plan.key);
    if (knownDigest !== undefined && knownDigest !== digest) return 'one key for two different plans';
    book.byKey.set(plan.key, digest);
    return undefined;
}

type GroupId = 'b' | 'c' | 'd' | 'e';
const GROUP_IDS: readonly GroupId[] = ['b', 'c', 'd', 'e'];
interface SweepGroup {
    count: number;
    messages: string[];
}
interface SweepResult {
    groups: Record<GroupId, SweepGroup>;
    coverage: Coverage;
    /** Cases the planner declined to plan. */
    skipped: number;
}
/** Plans one case of the grid; undefined skips the case. */
type SweepPlanner = (input: LadderAxisInput, oracle: OracleCase, closings: readonly string[]) => LadderAxisPlan | undefined;

/** Runs the grid with one planner and checks the given groups on every plan. */
function runSweep(planner: SweepPlanner, ids: readonly GroupId[]): SweepResult {
    let skipped = 0;
    const groups = {b: {count: 0, messages: []}, c: {count: 0, messages: []}, d: {count: 0, messages: []}, e: {count: 0, messages: []}} as Record<GroupId, SweepGroup>;
    const coverage: Coverage = {cases: 0, flat: 0, rotatedK1: 0, rotatedK2: 0, leftDrop: 0, rightDrop: 0, movedFirst: 0, positiveShift: 0, negativeShift: 0, anchor: 0, rule2WithPrevious: 0, rule3Visible: 0, rule4Visible: 0, ambiguous: 0, rungsFlat: new Set(), rungsRotated: new Set()};
    const report = (id: GroupId, label: string, problem: string) => {
        groups[id].count++;
        if (groups[id].messages.length < MAX_REPORTED) groups[id].messages.push(`${label}: ${problem}`);
    };
    const check = (id: GroupId, label: string, run: () => string | undefined) => {
        if (!ids.includes(id)) return;
        try {
            const problem = run();
            if (problem !== undefined) report(id, label, problem);
        } catch (error) {
            report(id, label, `threw ${String(error)}`);
        }
    };
    for (const rung of SWEEP_RUNGS) {
        const lad = ladder(rung, SWEEP_FIRST, SWEEP_LAST);
        const closings = lad.closingDates;
        const at = new Map(closings.map((raw, index): [string, number] => [raw, index]));
        const newYear = closings.findIndex((raw) => calendarPeriodOf(raw, rung).start.startsWith('2026'));
        for (const stub of SWEEP_STUBS) {
            const series = oracleSeries(lad, stub);
            const book: KeyBook = {byKey: new Map()};
            for (const plot of SWEEP_PLOTS) {
                for (const [windowName, window] of sweepWindows(closings.length, newYear)) {
                    for (const room of SWEEP_ROOMS) {
                        const input = axisInput(lad, stub, plot, {...room.geometry, window});
                        const label = `${rung} ${stub.locale} plot ${plot} ${windowName} ${room.name}`;
                        const oracle = oracleCase(series, input);
                        countCoverage(coverage, rung, oracle);
                        let planned: LadderAxisPlan | undefined;
                        try {
                            planned = planner(input, oracle, closings);
                        } catch (error) {
                            for (const id of ids) report(id, label, `the planner threw ${String(error)}`);
                            continue;
                        }
                        if (planned === undefined) {
                            skipped++;
                            continue;
                        }
                        const plan = planned;
                        check('b', label, () => separatorDiff(plan, oracle, closings));
                        check('c', label, () => oracleDiff(plan, oracle, closings, at));
                        check('d', label, () => propertyDiff(plan, oracle, closings));
                        check('e', label, () => optionDiff(plan, closings, book));
                    }
                }
            }
        }
    }
    return {groups, coverage, skipped};
}

let sweepMemo: SweepResult | undefined;
/** The planner under test over the grid, run once: every L14 test reads its own group from the same pass. */
function sweep(): SweepResult {
    sweepMemo ??= runSweep((input) => planLadderAxis(input), GROUP_IDS);
    return sweepMemo;
}

/** The oracle's answer as a plan, the way a planner that follows the contract to the letter returns it. */
function oraclePlan(oracle: OracleCase, closings: readonly string[]): LadderAxisPlan {
    const branch = oracle.decision === 'rotated' ? oracle.rotated : oracle.flat;
    const labels = new Map<string, string>();
    branch.texts.forEach((text, index) => {
        if (text !== undefined) labels.set(closings[index], text);
    });
    const separators = new Set([...oracle.separators].map((index) => closings[index]));
    const edgeShifts = new Map([...branch.exactShifts].map(([index, px]): [string, number] => [closings[index], px]));
    const key = JSON.stringify([branch.rotate, branch.step, [...labels], [...separators], [...edgeShifts], branch.widestText]);
    // WHY `labelBox: null`: the oracle plans without a measure, and without one the contract reserves no box (L15).
    return {rotate: branch.rotate, step: branch.step, labels, separators, edgeShifts, widestText: branch.widestText, labelBox: null, key};
}

describe('L14 — the oracle sweep: 4160 plans against the contract', {timeout: 60_000}, () => {
    it('L14a — the grid reaches every branch of the contract (oracle only, green on the old planner)', () => {
        // WHY: a sweep that never turned, dropped, shifted or anchored would prove nothing about those rules.
        const coverage = sweep().coverage;
        const reached = {
            cases: coverage.cases,
            flat: coverage.flat > 0,
            rotatedK1: coverage.rotatedK1 > 0,
            rotatedK2: coverage.rotatedK2 > 0,
            leftDrop: coverage.leftDrop > 0,
            rightDrop: coverage.rightDrop > 0,
            movedFirst: coverage.movedFirst > 0,
            positiveShift: coverage.positiveShift > 0,
            negativeShift: coverage.negativeShift > 0,
            anchor: coverage.anchor > 0,
            rule2WithPrevious: coverage.rule2WithPrevious > 0,
            rule3Visible: coverage.rule3Visible > 0,
            rule4Visible: coverage.rule4Visible > 0,
            rungsFlat: [...coverage.rungsFlat].sort(),
            rungsRotated: [...coverage.rungsRotated].sort(),
            // WHY: float-boundary cases are skipped by L14c, so they must stay a negligible share of the grid.
            ambiguousUnder1Pct: coverage.ambiguous <= coverage.cases / 100,
        };
        const yes = true;
        expect(reached).toEqual({
            cases: 4160,
            flat: yes,
            rotatedK1: yes,
            rotatedK2: yes,
            leftDrop: yes,
            rightDrop: yes,
            movedFirst: yes,
            positiveShift: yes,
            negativeShift: yes,
            anchor: yes,
            rule2WithPrevious: yes,
            rule3Visible: yes,
            rule4Visible: yes,
            rungsFlat: [...SWEEP_RUNGS].sort(),
            rungsRotated: [...SWEEP_RUNGS].sort(),
            ambiguousUnder1Pct: yes,
        });
    });

    it('L14b — separators equal the oracle (green on the old planner, on purpose)', () => {
        // WHY: the contract keeps the D4 separators; this is the regression guard of the rewrite.
        const {count, messages} = sweep().groups.b;
        expect({count, messages}).toEqual({count: 0, messages: []});
    });

    it('L14c — rotate, step, labels, edge shifts and widestText equal the oracle', () => {
        // WHY: the oracle restates the contract from Intl and the calendar alone; any difference is a contract break.
        const {count, messages} = sweep().groups.c;
        expect({count, messages}).toEqual({count: 0, messages: []});
    });

    it('L14d — every plan: rotate 0 or 45, no repeated text, flat = all labelled and fitting, turned = no shift', () => {
        // WHY: the properties hold whatever the oracle decided, float boundaries included.
        const {count, messages} = sweep().groups.d;
        expect({count, messages}).toEqual({count: 0, messages: []});
    });

    it('L14e — the option answers by raw from the plan, and one key never names two plans', () => {
        // WHY: ECharts sees only the option, and GrowthChart re-applies it only when the key changes.
        const {count, messages} = sweep().groups.e;
        expect({count, messages}).toEqual({count: 0, messages: []});
    });
});

describe('L14-self — the oracle reproduces every pin (green on the old planner, on purpose)', () => {
    it('L14-self.1 — the oracle gives every pinned row its pin', () => {
        // WHY: the oracle is evidence only while it agrees with the hand-computed pins; a difference means one of them is wrong.
        // 77 since M‴ (08/10/2026): L7.9 and L7.10 pin both sides of the 14.3 px row's threshold.
        expect(PIN_ROWS.length).toBe(77);
        expect(new Set(PIN_ROWS.map((pinned) => pinned.id)).size).toBe(PIN_ROWS.length);
        const views = Object.fromEntries(
            PIN_ROWS.map((pinned) => {
                const oracle = oracleOf(pinned.input);
                const boundary = oracle.decision === 'either' || (oracle.decision === 'rotated' && oracle.rotatedAmbiguous);
                return [pinned.id, boundary ? 'on a float boundary' : oracleView(oracle, pinned.input.closingDates)];
            }),
        );
        expect(views).toEqual(Object.fromEntries(PIN_ROWS.map((pinned) => [pinned.id, pinned.pin])));
    });

    it('L14-self.2 — the oracle gives every separator row its separators', () => {
        // WHY: the same proof for the separator pins, which L11 checks against the planner.
        expect(SEPARATOR_ROWS.length).toBe(12);
        const views = Object.fromEntries(SEPARATOR_ROWS.map(({id, input}) => [id, [...oracleOf(input).separators].sort((a, b) => a - b)]));
        expect(views).toEqual(Object.fromEntries(SEPARATOR_ROWS.map(({id, separators}) => [id, separators])));
    });

    it('L14-self.3 — plans built from the oracle pass L14b, L14c and L14d', () => {
        // WHY: those checks meet a conforming planner only after the rewrite; a check that rejects the contract's own answer must show now.
        const {groups, skipped, coverage} = runSweep((_input, oracle, closings) => (oracle.decision === 'either' ? undefined : oraclePlan(oracle, closings)), ['b', 'c', 'd']);
        const clean = {count: 0, messages: []};
        expect({b: groups.b, c: groups.c, d: groups.d, skippedOnlyOnBoundaries: skipped <= coverage.ambiguous}).toEqual({b: clean, c: clean, d: clean, skippedOnlyOnBoundaries: true});
    });

    it('L14-self.4 — L14c and L14d catch plans that break the contract (positive control)', () => {
        // WHY: "no problem found" is also what a check that never fires reports; every mutant of a conforming plan must be caught.
        type Change = (plan: LadderAxisPlan, oracle: OracleCase, closings: readonly string[]) => void;
        const caughtBy = (id: GroupId, change: Change): boolean => {
            const planner: SweepPlanner = (_input, oracle, closings) => {
                if (oracle.decision === 'either') return undefined;
                const plan = oraclePlan(oracle, closings);
                change(plan, oracle, closings);
                return plan;
            };
            return runSweep(planner, [id]).groups[id].count > 0;
        };
        const labelled = (plan: LadderAxisPlan, closings: readonly string[]) => closings.filter((raw) => plan.labels.has(raw));
        const caught = {
            text: caughtBy('c', (plan, _oracle, closings) => {
                const [raw] = labelled(plan, closings);
                if (raw !== undefined) plan.labels.set(raw, `${plan.labels.get(raw)}·`);
            }),
            widestText: caughtBy('c', (plan) => {
                plan.widestText = `${plan.widestText}·`;
            }),
            turnedAsFlat: caughtBy('c', (plan) => {
                if (plan.rotate === 45) plan.rotate = 0;
            }),
            shiftValue: caughtBy('c', (plan) => {
                for (const [raw, px] of plan.edgeShifts) plan.edgeShifts.set(raw, px + Math.sign(px) * 3);
            }),
            flatStep: caughtBy('d', (plan) => {
                if (plan.rotate === 0) plan.step = 2;
            }),
            flatUnlabelled: caughtBy('d', (plan, _oracle, closings) => {
                if (plan.rotate === 0) plan.labels.delete(closings[closings.length - 1]);
            }),
            flatCrowded: caughtBy('d', (plan, oracle, closings) => {
                if (plan.rotate === 0 && oracle.ve > oracle.vs) plan.edgeShifts.set(closings[oracle.ve], -Math.ceil(oracle.slot));
            }),
            turnedShift: caughtBy('d', (plan, oracle, closings) => {
                if (plan.rotate === 45) plan.edgeShifts.set(closings[oracle.vs], 1);
            }),
            repeatedText: caughtBy('d', (plan, _oracle, closings) => {
                const [first, second] = labelled(plan, closings);
                if (second !== undefined) plan.labels.set(second, plan.labels.get(first) ?? '');
            }),
        };
        expect(caught).toEqual({text: true, widestText: true, turnedAsFlat: true, shiftValue: true, flatStep: true, flatUnlabelled: true, flatCrowded: true, turnedShift: true, repeatedText: true});
    });
});

// ─── M‴ (08/10/2026): the label box that makes containLabel's band exact ───

/** `input` with a measure, the way GrowthChart passes one. */
const measured = (input: LadderAxisInput, measureLabelPx: (text: string) => number): LadderAxisInput => ({...input, measureLabelPx});

/** A deterministic stand-in for the painted width: 7.5 px a character. */
const byLength = (text: string): number => text.length * 7.5;

/** A measure that answers from a table and records what it is asked. */
function recordingMeasure(widths: ReadonlyMap<string, number>, fallbackPx: number): {asked: string[]; measure: (text: string) => number} {
    const asked: string[] = [];
    const measure = (text: string): number => {
        asked.push(text);
        return widths.get(text) ?? fallbackPx;
    };
    return {asked, measure};
}

/** Distinct texts, sorted: the planner may measure in any order, and a text more than once. */
const distinct = (texts: readonly string[]): string[] => [...new Set(texts)].sort();

/** The texts of the labelled buckets in the window, rounded, clamped and ordered the way the oracle does it. */
function visibleLabelledTexts(plan: LadderAxisPlan, input: LadderAxisInput): string[] {
    const n = input.closingDates.length;
    const clamp = (value: number, fallback: number) => (Number.isFinite(value) ? Math.max(0, Math.min(n - 1, Math.round(value))) : fallback);
    let vs = clamp(input.visibleStartIndex, 0);
    let ve = clamp(input.visibleEndIndex, n - 1);
    if (vs > ve) [vs, ve] = [ve, vs];
    return input.closingDates.slice(vs, ve + 1).flatMap((raw) => {
        const text = plan.labels.get(raw);
        return text === undefined ? [] : [text];
    });
}

/** L9.1's geometry: window 8..9 on a 20 px plot, k = 3, the only visible candidate (9) dropped on the right. */
const NO_VISIBLE_LABEL = axisInput(DAYS_10, EN, 20, {window: [8, 9], leftRoomPx: 40, rightRoomPx: 0});
const NO_BUCKETS_15: LadderAxisInput = {...axisInput(WEEKS_B6, EN, 527), closingDates: [], visibleStartIndex: 0, visibleEndIndex: 0};

describe('L15 — labelBox (M‴): one invisible box per label, as wide as the widest visible label', () => {
    // WHY: ECharts' legacy containLabel measures the formatter on a sample of categories (0, step, 2·step…, with
    // step = ceil(n / 40) past 40 ticks), ignores `interval`, and reserves that union's height: a long label at an
    // unsampled index is painted below the band. Given `axisLabel.width` W and a `lineHeight`, zrender gives every
    // label a W × line box, so whatever ECharts samples measures W wide and the band is exact (L16 renders it).

    it('L15.1 — LADDER_LABEL_ROW_EM is one 14.3 px row at 14 px', () => {
        // WHY: a Chromium 14 px line is 14.28 px tall; W-wide boxes closer than that across the text meet, and
        // ECharts' fixMinMaxLabelShow then hides an edge label. The planner's k counts this row (L7, L14c).
        expect(LADDER_LABEL_ROW_EM).toBe(14.3 / 14);
    });

    it('L15.2 — turned and measured: the box is the widest measured visible label, one font line tall', () => {
        const income = planLadderAxis(measured(axisInput(MONTHS_INCOME, EN, 12 * INCOME_MIN_SLOT_PX), byLength));
        const small = planLadderAxis(measured(axisInput(DAYS_10, EN, 175, {fontSizePx: 12}), byLength));
        // WHY: the preconditions of L8.5 and L7.5: both turned, every bucket labelled.
        expect([income.rotate, income.step, income.labels.size, small.rotate, small.step, small.labels.size]).toEqual([45, 1, 12, 45, 1, 10]);
        // WHY: "Oct '25" and "Jan '26" are Income's longest texts, 7 characters at 7.5 px: 52.5, unrounded.
        expect(income.labelBox).toEqual({widthPx: 52.5, lineHeightPx: 14});
        // WHY: the line is the font size: 12 px text gets a 12 px line ("Mar 10", 6 characters: 45 px).
        expect(small.labelBox).toEqual({widthPx: 45, lineHeightPx: 12});
    });

    it('L15.3 — W is the largest measured width, not the measure of widestText', () => {
        // WHY: widestText is the planner's estimate ("Mar 10"); the box must hold what is painted, and here "14" paints wider.
        const {asked, measure} = recordingMeasure(
            new Map([
                ['Mar 10', 38.5],
                ['14', 40.75],
            ]),
            15.5,
        );
        const input = measured(axisInput(DAYS_10, EN, 203), measure);
        const plan = planLadderAxis(input);
        expect([plan.rotate, plan.step, plan.widestText]).toEqual([45, 1, 'Mar 10']);
        expect(plan.labelBox).toEqual({widthPx: 40.75, lineHeightPx: 14});
        expect(distinct(asked)).toEqual(distinct(visibleLabelledTexts(plan, input)));
    });

    it('L15.4 — a labelled bucket outside the window is not measured', () => {
        // WHY: hidden labels stay in the plan (L7.4) but ECharts never paints them: counting "Mar 11" (index 1, window 2..11)
        // would make the box 999 px wide.
        const {asked, measure} = recordingMeasure(
            new Map([
                ['Mar 11', 999],
                ['Mar 13', 44.25],
                ['15', 15.5],
                ['17', 15.5],
                ['19', 15.5],
                ['21', 15.5],
            ]),
            0,
        );
        const plan = planLadderAxis(measured(axisInput(DAYS_12, EN, 197, {window: [2, 11]}), measure));
        expect(plan.labels.get(DAYS_12.closingDates[1])).toBe('Mar 11');
        expect(plan.labelBox).toEqual({widthPx: 44.25, lineHeightPx: 14});
        expect(distinct(asked)).toEqual(['15', '17', '19', '21', 'Mar 13']);
    });

    it('L15.5 — an unlabelled bucket is not measured', () => {
        // WHY: k = 2 (L7.1) leaves 0, 2, 4, 6 and 8 unlabelled and ECharts paints nothing there: the texts they would carry
        // at k = 1 ("Mar 10", "12", …) must not reach the box, and any of them would measure 1000.
        const {asked, measure} = recordingMeasure(
            new Map([
                ['Mar 11', 41.5],
                ['13', 15.5],
                ['15', 15.5],
                ['17', 15.5],
                ['19', 15.5],
            ]),
            1000,
        );
        const plan = planLadderAxis(measured(axisInput(DAYS_10, EN, 197), measure));
        expect([plan.rotate, plan.step]).toEqual([45, 2]);
        expect(plan.labelBox).toEqual({widthPx: 41.5, lineHeightPx: 14});
        expect(distinct(asked)).toEqual(['13', '15', '17', '19', 'Mar 11']);
    });

    const NULL_CASES: Array<{id: string; name: string; input: LadderAxisInput; rotate: 0 | 45}> = [
        // WHY: a flat label is one text line tall and every bucket is sampled at its own width: there is no band to fix.
        {id: 'L15.6a', name: 'flat (1M Apr–Sep on 527), measured', input: measured(axisInput(MONTHS_APR_SEP, EN, 527), byLength), rotate: 0},
        // WHY: without a measure the planner has no painted width to give (the fallback stays widestText, as before M‴).
        {id: 'L15.6b', name: 'turned (1M Apr–Sep on 200), no measure', input: axisInput(MONTHS_APR_SEP, EN, 200), rotate: 45},
        // WHY: nothing visible is labelled, so nothing on screen can size the box.
        {id: 'L15.6c', name: 'turned, no visible label (L9.1), measured', input: measured(NO_VISIBLE_LABEL, byLength), rotate: 45},
        {id: 'L15.6d', name: 'no buckets, measured', input: measured(NO_BUCKETS_15, byLength), rotate: 0},
        {id: 'L15.6e', name: 'plot 0, measured', input: measured(axisInput(WEEKS_B6, EN, 0), byLength), rotate: 0},
    ];
    it.each(NULL_CASES)('$id — $name: no box', ({input, rotate}) => {
        const plan = planLadderAxis(input);
        expect(plan.rotate).toBe(rotate);
        expect(plan.labelBox).toBeNull();
    });

    it('L15.7 — with no visible label the measure is never asked', () => {
        // WHY: L9.1 keeps 0, 3 and 6 labelled outside the window; they are not painted, so they are not measured either.
        const {asked, measure} = recordingMeasure(new Map(), 50);
        const plan = planLadderAxis(measured(NO_VISIBLE_LABEL, measure));
        expect([plan.rotate, plan.labels.size > 0]).toEqual([45, true]);
        expect(plan.labelBox).toBeNull();
        expect(asked).toEqual([]);
    });

    it('L15.8 — the box is in the key: another width, another key', () => {
        // WHY: GrowthChart re-applies the axis only when the key changes; an unchanged key would leave the old box on screen.
        const input = axisInput(MONTHS_APR_SEP, EN, 200);
        const narrow = planLadderAxis(measured(input, byLength));
        const wide = planLadderAxis(measured(input, (text) => text.length * 8));
        const again = planLadderAxis(measured(input, (text) => text.length * 7.5));
        expect(narrow.key).not.toBe(wide.key);
        expect(again.key).toBe(narrow.key);
        // WHY: the measure changes the box and nothing else.
        const view = (plan: LadderAxisPlan) => [plan.rotate, plan.step, [...plan.labels], [...plan.separators], [...plan.edgeShifts], plan.widestText];
        expect(view(wide)).toEqual(view(narrow));
    });

    it('L15.9 — the option always carries width and lineHeight: the box, or null', () => {
        // WHY: on a zoom GrowthChart sends `{xAxis}` alone, which ECharts MERGES into the previous option: an absent key would
        // keep the previous width, and a flat axis would keep a turned one's boxes. null clears it (L16.4 renders the merge).
        const optionOf = (input: LadderAxisInput) => axisLabelOf(ladderAxisOption(planLadderAxis(input)));
        const options = {
            turnedMeasured: optionOf(measured(axisInput(MONTHS_APR_SEP, EN, 200), byLength)),
            turnedUnmeasured: optionOf(axisInput(MONTHS_APR_SEP, EN, 200)),
            flatMeasured: optionOf(measured(axisInput(MONTHS_APR_SEP, EN, 527), byLength)),
            empty: optionOf(measured(NO_BUCKETS_15, byLength)),
        };
        const entries = Object.entries(options);
        expect(Object.fromEntries(entries.map(([name, label]) => [name, ['width' in label, 'lineHeight' in label]]))).toEqual({
            turnedMeasured: [true, true],
            turnedUnmeasured: [true, true],
            flatMeasured: [true, true],
            empty: [true, true],
        });
        expect(Object.fromEntries(entries.map(([name, label]) => [name, [label.width, label.lineHeight]]))).toEqual({
            turnedMeasured: [52.5, 14],
            turnedUnmeasured: [null, null],
            flatMeasured: [null, null],
            empty: [null, null],
        });
        // WHY: the box moves the reserved band only: rotate, rich styles, formatter and interval are the unmeasured plan's.
        const closings = MONTHS_APR_SEP.closingDates;
        const painted = (label: ReturnType<typeof optionOf>) => [label.rotate, label.rich, closings.map((raw, index) => [label.formatter(raw), label.interval(closings.length - 1 - index, raw)])];
        expect(painted(options.turnedMeasured)).toEqual(painted(options.turnedUnmeasured));
    });

    it('L15.10 — over the L14 grid the measure adds the box and changes nothing else', {timeout: 60_000}, () => {
        // WHY: the 4160 cases of L14, each planned with and without a measure: the plans must agree on every other field, and the
        // box must be the widest measured VISIBLE labelled text, only when turned — the rules L15.2–7 pin one case at a time.
        const sweepMeasure = (text: string): number => text.length * 7 + (text.codePointAt(0) ?? 0) / 64;
        const view = (plan: LadderAxisPlan) => JSON.stringify([plan.rotate, plan.step, [...plan.labels], [...plan.separators], [...plan.edgeShifts], plan.widestText]);
        let count = 0;
        let cases = 0;
        let boxes = 0;
        const messages: string[] = [];
        const report = (label: string, problem: string) => {
            count++;
            if (messages.length < MAX_REPORTED) messages.push(`${label}: ${problem}`);
        };
        for (const rung of SWEEP_RUNGS) {
            const lad = ladder(rung, SWEEP_FIRST, SWEEP_LAST);
            const newYear = lad.closingDates.findIndex((raw) => calendarPeriodOf(raw, rung).start.startsWith('2026'));
            for (const stub of SWEEP_STUBS) {
                for (const plot of SWEEP_PLOTS) {
                    for (const [windowName, window] of sweepWindows(lad.closingDates.length, newYear)) {
                        for (const room of SWEEP_ROOMS) {
                            cases++;
                            const label = `${rung} ${stub.locale} plot ${plot} ${windowName} ${room.name}`;
                            const input = axisInput(lad, stub, plot, {...room.geometry, window});
                            const asked: string[] = [];
                            const plain = planLadderAxis(input);
                            const boxed = planLadderAxis(
                                measured(input, (text) => {
                                    asked.push(text);
                                    return sweepMeasure(text);
                                }),
                            );
                            const texts = visibleLabelledTexts(boxed, input);
                            const expected = boxed.rotate === 45 && texts.length > 0 ? {widthPx: Math.max(...texts.map(sweepMeasure)), lineHeightPx: DEFAULT_FONT_PX} : null;
                            if (expected !== null) boxes++;
                            if (view(boxed) !== view(plain)) report(label, 'the measure changed the plan');
                            else if (JSON.stringify(boxed.labelBox) !== JSON.stringify(expected)) report(label, `labelBox ${JSON.stringify(boxed.labelBox)}, expected ${JSON.stringify(expected)}`);
                            else if (plain.labelBox !== null) report(label, `unmeasured labelBox ${JSON.stringify(plain.labelBox)}`);
                            else if (expected !== null && boxed.key === plain.key) report(label, 'the box is not in the key');
                            else if (asked.some((text) => !texts.includes(text))) report(label, `measured ${JSON.stringify(distinct(asked.filter((text) => !texts.includes(text))))}, not visible labelled texts`);
                        }
                    }
                }
            }
        }
        // WHY: the grid must reach both answers, or "no problem found" would prove nothing.
        expect({cases, someBoxes: boxes > 0, someNull: boxes < cases}).toEqual({cases: 4160, someBoxes: true, someNull: true});
        expect({count, messages}).toEqual({count: 0, messages: []});
    });
});

// ─── L16: the band ECharts reserves, rendered by the real ECharts 6 (SSR, no mock in this file) ───

/** The ECharts/zrender internals L16 reads. Not public API: L16.1 checks them before anything relies on them. */
interface RectLike {
    x: number;
    y: number;
    width: number;
    height: number;
}
interface DisplayableLike {
    type: string;
    style?: {text?: unknown};
    getBoundingRect(): {clone(): RectLike & {applyTransform(transform: unknown): unknown}};
    getComputedTransform(): unknown;
}
interface ChartInternals {
    getModel(): {getComponent(mainType: string, index: number): {coordinateSystem?: {getRect(): RectLike}; getModel(path: string): {get(key: string): unknown}} | undefined};
    getZr(): {storage: {getDisplayList(update: boolean): DisplayableLike[]}};
}
interface PaintedLabel {
    text: string;
    x: number;
    /** Top of the painted text, from the grid's bottom edge. */
    top: number;
    /** Bottom of the painted text, on the canvas. */
    bottom: number;
}

/** GrowthChart's chart, reduced: its grid, a bottom legend room of 30 px, a 14 px category axis. */
const SSR = {width: 1300, height: 420, legendPx: 30, font: '14px sans-serif', marginPx: 8} as const;
/** 53 weeks from Monday 2025-10-06: label 13 is "Jan 5 '26", odd, so containLabel's step-2 sample misses it. */
const WEEKS_53 = ladder('1W', '2025-10-06', '2026-10-11');
/** A text's painted width as ECharts measures it here (zrender's Node metrics), the measure GrowthChart passes. */
const ssrTextWidth = (text: string): number => echarts.format.getTextRect(text, SSR.font).width;

function renderLadder(axisLabel: Record<string, unknown>, bottomPx: number = SSR.legendPx): echarts.ECharts {
    const chart = echarts.init(null, undefined, {renderer: 'svg', ssr: true, width: SSR.width, height: SSR.height});
    chart.setOption({
        animation: false,
        grid: {left: '3%', right: '4%', bottom: `${bottomPx}px`, top: '10px', containLabel: true},
        xAxis: {type: 'category', data: WEEKS_53.closingDates, boundaryGap: true, axisLabel},
        yAxis: {type: 'value'},
        series: [{type: 'bar', data: WEEKS_53.closingDates.map((_, index) => (index % 7) + 1)}],
    });
    chart.renderToSVGString();
    return chart;
}

function gridOf(chart: echarts.ECharts): RectLike {
    const rect = (chart as unknown as ChartInternals).getModel().getComponent('grid', 0)?.coordinateSystem?.getRect();
    if (rect === undefined) throw new Error('ECharts changed: the grid has no coordinate-system rect');
    return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
}

/** The x-axis labels as painted: zrender's display list, each text's rect through its transform, sorted left to right. */
function paintedLabels(chart: echarts.ECharts, texts: ReadonlySet<string>): PaintedLabel[] {
    const grid = gridOf(chart);
    const gridBottom = grid.y + grid.height;
    const labels: PaintedLabel[] = [];
    for (const el of (chart as unknown as ChartInternals).getZr().storage.getDisplayList(true)) {
        const text = el.style?.text;
        if (el.type !== 'tspan' || typeof text !== 'string' || !texts.has(text)) continue;
        const rect = el.getBoundingRect().clone();
        rect.applyTransform(el.getComputedTransform());
        // WHY: the y axis' numbers ("8" is also a week's text) sit beside the grid; an x label hangs below its bottom edge.
        if (rect.y <= gridBottom) continue;
        labels.push({text, x: rect.x, top: rect.y - gridBottom, bottom: rect.y + rect.height});
    }
    return labels.sort((a, b) => a.x - b.x);
}

/** The largest coordinate difference between two paintings of the same labels; Infinity when the texts differ. */
function drift(a: readonly PaintedLabel[], b: readonly PaintedLabel[]): number {
    if (a.length !== b.length || a.some((label, index) => label.text !== b[index].text)) return Number.POSITIVE_INFINITY;
    return Math.max(0, ...a.map((label, index) => Math.max(Math.abs(label.x - b[index].x), Math.abs(label.top - b[index].top))));
}

const rectDrift = (a: RectLike, b: RectLike): number => Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y), Math.abs(a.width - b.width), Math.abs(a.height - b.height));

/** The axis label GrowthChart's full render sends: its 14 px font, then the plan's option. */
const fullAxisLabel = (plan: LadderAxisPlan): Record<string, unknown> => ({fontSize: 14, ...ladderAxisOption(plan).axisLabel});

/** The same without the box: what ECharts reserves for the plan's labels when nothing sizes them. */
function unboxedAxisLabel(plan: LadderAxisPlan): Record<string, unknown> {
    const axisLabel = fullAxisLabel(plan);
    delete axisLabel.width;
    delete axisLabel.lineHeight;
    return axisLabel;
}

interface SsrSetup {
    plan: LadderAxisPlan;
    texts: ReadonlySet<string>;
    /** The widest painted label, measured here: what the box must be. */
    widthPx: number;
}
let ssrMemo: SsrSetup | undefined;
/** Two passes, like GrowthChart: render once to read the plot width, then plan on it with the measure. */
function ssrSetup(): SsrSetup {
    if (ssrMemo !== undefined) return ssrMemo;
    const first = renderLadder({fontSize: 14});
    let plotWidthPx: number;
    try {
        plotWidthPx = gridOf(first).width;
    } finally {
        first.dispose();
    }
    const plan = planLadderAxis(measured(axisInput(WEEKS_53, EN, plotWidthPx), ssrTextWidth));
    const texts = [...plan.labels.values()];
    ssrMemo = {plan, texts: new Set(texts), widthPx: Math.max(...texts.map(ssrTextWidth))};
    return ssrMemo;
}

describe('L16 — containLabel band, real ECharts (SSR)', {timeout: 30_000}, () => {
    // WHY: in Node zrender measures a 14 px line as 14 px (Chromium: 14.28), so the 14.3 px row cannot show here — L7, L14c and
    // L15.1 pin it. This describe renders what the box alone does: the band becomes (W + 14)·√½ + 8 whatever ECharts samples,
    // and the labels are painted exactly where they were.

    it('L16.1 — preconditions, and the ECharts control: unboxed, an unsampled label hangs below the band (green before the fix)', () => {
        const {plan, texts, widthPx} = ssrSetup();
        const closings = WEEKS_53.closingDates;
        expect(
            [ssrTextWidth("Jan 5 '26"), ssrTextWidth('Oct 6'), echarts.format.getTextRect('Oct 6', SSR.font).height].map((px) => Number(px.toFixed(6))),
            'ECharts changed: Node text metrics',
        ).toEqual([56.7, 33.6, 14]);
        // WHY: past 40 categories containLabel samples every ceil(53 / 40) = 2nd one, so the odd index 13 is never measured.
        expect([closings.length, Math.ceil(closings.length / 40)], 'precondition: 53 weeks, sampled every 2nd').toEqual([53, 2]);
        expect([plan.rotate, plan.step, plan.labels.size], 'precondition: turned, every week labelled').toEqual([45, 1, 53]);
        expect([plan.labels.get(closings[0]), plan.labels.get(closings[13])], 'precondition: labels 0 and 13').toEqual(['Oct 6', "Jan 5 '26"]);
        expect(
            closings.findIndex((raw) => ssrTextWidth(plan.labels.get(raw) ?? '') === widthPx),
            'precondition: the widest label is 13',
        ).toBe(13);
        const control = renderLadder(unboxedAxisLabel(plan));
        try {
            const painted = paintedLabels(control, texts);
            expect(painted.length, 'ECharts changed: every label painted').toBe(53);
            const slack = SSR.height - SSR.legendPx - Math.max(...painted.map((label) => label.bottom));
            expect(slack, 'ECharts changed: unboxed, "Jan 5 \'26" no longer hangs below the band').toBeLessThan(0);
        } finally {
            control.dispose();
        }
    });

    it("L16.2 — with the plan's box the band holds every label: grid bottom = H − 30 − 8 − (W + 14)·√½", () => {
        const {plan, texts, widthPx} = ssrSetup();
        // WHY: first, so a missing box reads as the assertion it is.
        expect(plan.labelBox).toEqual({widthPx, lineHeightPx: 14});
        const fixed = renderLadder(fullAxisLabel(plan));
        try {
            const grid = gridOf(fixed);
            expect(grid.y + grid.height).toBeCloseTo(SSR.height - SSR.legendPx - SSR.marginPx - (widthPx + 14) * SQRT_HALF, 1);
            const painted = paintedLabels(fixed, texts);
            expect(SSR.height - SSR.legendPx - Math.max(...painted.map((label) => label.bottom))).toBeGreaterThanOrEqual(0);
            expect(painted.length).toBe(53);
        } finally {
            fixed.dispose();
        }
    });

    it('L16.3 — the box moves the band, not the labels: on the same grid the unboxed axis paints them at the same places', () => {
        const {plan, texts} = ssrSetup();
        const charts: echarts.ECharts[] = [];
        const render = (axisLabel: Record<string, unknown>, bottomPx?: number) => {
            const chart = renderLadder(axisLabel, bottomPx);
            charts.push(chart);
            return chart;
        };
        try {
            const fixed = render(fullAxisLabel(plan));
            const control = render(unboxedAxisLabel(plan));
            const fixedBottom = gridOf(fixed).y + gridOf(fixed).height;
            const controlBottom = gridOf(control).y + gridOf(control).height;
            // WHY: first: before the fix both renders are the same chart.
            expect(fixedBottom).toBeLessThan(controlBottom);
            const sameGrid = render(unboxedAxisLabel(plan), SSR.legendPx + controlBottom - fixedBottom);
            expect(rectDrift(gridOf(sameGrid), gridOf(fixed))).toBeLessThan(1e-3);
            const boxed = paintedLabels(fixed, texts);
            expect(boxed.length).toBe(53);
            expect(drift(paintedLabels(sameGrid, texts), boxed)).toBeLessThan(1e-3);
        } finally {
            for (const chart of charts) chart.dispose();
        }
    });

    it('L16.4 — a flat {xAxis}-only update clears the box: the merged chart is the chart a fresh render draws', () => {
        const {plan, widthPx} = ssrSetup();
        const flatPlan = planLadderAxis(measured(axisInput(WEEKS_53, EN, 6000), ssrTextWidth));
        expect([flatPlan.rotate, flatPlan.labels.size], 'precondition: on 6000 px the 53 labels lie flat').toEqual([0, 53]);
        const flatTexts = new Set(flatPlan.labels.values());
        const merged = renderLadder(fullAxisLabel(plan));
        let fresh: echarts.ECharts | undefined;
        try {
            const axisLabelModel = () => (merged as unknown as ChartInternals).getModel().getComponent('xAxis', 0)?.getModel('axisLabel');
            // WHY: first: before the fix the turned chart carries no box, and there is nothing to clear.
            expect([axisLabelModel()?.get('width'), axisLabelModel()?.get('lineHeight')]).toEqual([widthPx, 14]);
            merged.setOption({xAxis: ladderAxisOption(flatPlan)});
            merged.renderToSVGString();
            // WHY: ECharts merges an {xAxis}-only option into the last one: only a present null replaces the turned width.
            expect([axisLabelModel()?.get('width') ?? null, axisLabelModel()?.get('lineHeight') ?? null, axisLabelModel()?.get('rotate')]).toEqual([null, null, 0]);
            fresh = renderLadder(fullAxisLabel(flatPlan));
            expect(rectDrift(gridOf(merged), gridOf(fresh))).toBeLessThan(1e-6);
            const painted = paintedLabels(merged, flatTexts);
            expect(painted.length).toBeGreaterThan(0);
            expect(drift(painted, paintedLabels(fresh, flatTexts))).toBeLessThan(1e-6);
        } finally {
            merged.dispose();
            fresh?.dispose();
        }
    });
});
