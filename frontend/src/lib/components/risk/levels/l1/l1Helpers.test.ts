import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {parse} from 'svelte/compiler';
import {describe, expect, it} from 'vitest';

import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {DAILY_VAR_INSTANCE} from '../../riskAnalysisHelpers';
import {formatShare} from '../shareFormat';
import * as l1 from './l1Helpers';
import {buildReturnHistogram, buildTailMeasures, buildUnderwater} from './l1Helpers';

/** A successful result carrying `output`, shaped like the API's. */
function ok(analyticCode: string, output: Record<string, unknown>, instanceId = `base-historical-${analyticCode}`): RiskAnalyticResult {
    return {analytic_code: analyticCode, instance_id: instanceId, status: 'ok', output} as unknown as RiskAnalyticResult;
}

/** A result the backend could not compute. */
function unavailable(analyticCode: string, instanceId = `base-historical-${analyticCode}`): RiskAnalyticResult {
    return {analytic_code: analyticCode, instance_id: instanceId, status: 'unavailable', output: null} as unknown as RiskAnalyticResult;
}

function bin(lower: number, upper: number, count: number): Record<string, unknown> {
    return {lower_bound: lower, upper_bound: upper, count};
}

function varResult(bins: Record<string, unknown>[], edge: number | null): RiskAnalyticResult {
    return ok('historical_var', {kind: 'var_cvar', return_bins: bins, var_bin_edge: edge}, DAILY_VAR_INSTANCE);
}

describe('buildUnderwater', () => {
    it('hands the chart percent units, because the chart converts nothing', () => {
        // `viewMode='percentage'` only relabels the axis; the series plots the
        // raw value. A decimal ratio here would draw the right shape against
        // numbers a hundred times too small.
        const points = buildUnderwater([ok('drawdown_summary', {underwater_series: [{date: '2024-01-02', drawdown: -0.123}]})]);
        expect(points).toEqual([{date: '2024-01-02', value: -12.3}]);
    });

    it('keeps each point on its own date rather than spreading them over the window', () => {
        const points = buildUnderwater([
            ok('drawdown_summary', {
                underwater_series: [
                    {date: '2024-01-02', drawdown: -0.01},
                    // A weekend gap: the series is shorter than the span it covers.
                    {date: '2024-01-08', drawdown: -0.04},
                ],
            }),
        ]);
        expect(points.map((point) => point.date)).toEqual(['2024-01-02', '2024-01-08']);
    });

    it('drops a point that contradicts its own le=0 convention instead of rescuing it', () => {
        const points = buildUnderwater([
            ok('drawdown_summary', {
                underwater_series: [
                    {date: '2024-01-02', drawdown: -0.05},
                    // Positive is impossible for a peak-relative drawdown. A
                    // `Math.abs` here would render it as a plausible −7%.
                    {date: '2024-01-03', drawdown: 0.07},
                ],
            }),
        ]);
        expect(points).toEqual([{date: '2024-01-02', value: -5}]);
    });

    it('prints a day at the peak as a plain zero, never as a negative one', () => {
        const [point] = buildUnderwater([ok('drawdown_summary', {underwater_series: [{date: '2024-01-02', drawdown: 0}]})]);
        // `toBe` compares with Object.is, so this fails on `-0` — which is the
        // whole point: `-0` reaches the axis formatter as "−0.0%".
        expect(point.value).toBe(0);
    });

    it('skips an entry with no usable date rather than inventing one', () => {
        const points = buildUnderwater([
            ok('drawdown_summary', {
                underwater_series: [{drawdown: -0.05}, {date: '2024-01-03', drawdown: -0.06}],
            }),
        ]);
        expect(points.map((point) => point.date)).toEqual(['2024-01-03']);
    });

    it('has nothing to draw when the analytic did not run', () => {
        expect(buildUnderwater([unavailable('drawdown_summary')])).toEqual([]);
        expect(buildUnderwater([])).toEqual([]);
        expect(buildUnderwater([ok('drawdown_summary', {})])).toEqual([]);
    });
});

describe('buildReturnHistogram', () => {
    it('locates the cut by inequality on a half-open interval, not by matching a float', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.03, -0.02, 4), bin(-0.02, -0.01, 9), bin(-0.01, 0, 20)], -0.015)]);
        expect(histogram?.bins.map((entry) => entry.holdsCut)).toEqual([false, true, false]);
    });

    it('gives the boundary to the bin that opens on it, and not to the one that closes there', () => {
        // `[lower, upper)`: an edge sitting exactly on a shared bound belongs to
        // the upper bin. Any equality-based search would claim both, or neither.
        const histogram = buildReturnHistogram([varResult([bin(-0.02, -0.01, 5), bin(-0.01, 0, 11)], -0.01)]);
        expect(histogram?.bins.map((entry) => entry.holdsCut)).toEqual([false, true]);
    });

    it('shades the run beyond the cut, and leaves the straddling bar out of it', () => {
        // The highlighted bar says where the number is; the shaded run says what
        // mass it is talking about. The bar holding the cut is in neither.
        const histogram = buildReturnHistogram([varResult([bin(-0.04, -0.03, 1), bin(-0.03, -0.02, 2), bin(-0.02, -0.01, 9), bin(-0.01, 0, 20)], -0.025)]);
        expect(histogram?.bins.map((entry) => entry.belowCut)).toEqual([true, false, false, false]);
        expect(histogram?.bins.map((entry) => entry.holdsCut)).toEqual([false, true, false, false]);
    });

    it('shades nothing when there is no cut to be beyond', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.02, -0.01, 5), bin(-0.01, 0, 20)], null)]);
        expect(histogram?.bins.every((entry) => !entry.belowCut)).toBe(true);
    });

    it('keeps a cut of exactly zero, which is a threshold at break-even and not a missing one', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.01, 0, 8), bin(0, 0.01, 12)], 0)]);
        expect(histogram?.cut).toBe(0);
        expect(histogram?.bins.map((entry) => entry.holdsCut)).toEqual([false, true]);
    });

    it('marks nothing when the backend published no cut at all', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.01, 0, 8), bin(0, 0.01, 12)], null)]);
        expect(histogram?.cut).toBeNull();
        expect(histogram?.bins.every((entry) => !entry.holdsCut)).toBe(true);
    });

    it('marks nothing when the cut falls outside every sampled bin, which is an answer', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.01, 0, 8), bin(0, 0.01, 12)], -0.5)]);
        expect(histogram?.cut).toBe(-50);
        expect(histogram?.bins.every((entry) => !entry.holdsCut)).toBe(true);
    });

    it('takes each bar width from its own bounds, so an uneven grid still draws true', () => {
        // The schema polices only that `lower_bound` ascends: contiguity and a
        // constant width are the producer's habit, not a guarantee.
        const histogram = buildReturnHistogram([varResult([bin(-0.08, -0.02, 3), bin(-0.02, -0.01, 7)], null)]);
        expect(histogram?.bins.map((entry) => entry.upperBound - entry.lowerBound)).toEqual([6, 1]);
    });

    it('sizes every bar against the tallest one', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.02, -0.01, 5), bin(-0.01, 0, 20)], null)]);
        expect(histogram?.bins.map((entry) => entry.share)).toEqual([0.25, 1]);
    });

    it('counts the observations it actually drew', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.02, -0.01, 5), bin(-0.01, 0, 20)], null)]);
        expect(histogram?.observations).toBe(25);
    });

    it('discards a bin with no width, which could hold neither an observation nor the cut', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.01, -0.01, 4), bin(-0.01, 0, 6)], -0.01)]);
        expect(histogram?.bins).toHaveLength(1);
        expect(histogram?.bins[0].holdsCut).toBe(true);
    });

    it('stays flat instead of dividing by zero when every bin is empty', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.01, 0, 0), bin(0, 0.01, 0)], null)]);
        expect(histogram?.bins.map((entry) => entry.share)).toEqual([0, 0]);
        expect(histogram?.observations).toBe(0);
    });

    it('has no histogram when the analytic did not run or carried no bins', () => {
        expect(buildReturnHistogram([unavailable('historical_var', DAILY_VAR_INSTANCE)])).toBeNull();
        expect(buildReturnHistogram([varResult([], null)])).toBeNull();
        expect(buildReturnHistogram([])).toBeNull();
    });
});

describe('buildTailMeasures', () => {
    it('leaves the worst day absent when the producer refused to publish one', () => {
        // Every day in the window gained. A zero here would claim a loss that
        // never happened — which is exactly why the backend sends null.
        const measures = buildTailMeasures([ok('historical_kpi', {worst_realization: null, ulcer_index: 0.04})]);
        expect(measures.worstRealization).toBeNull();
    });

    it('drops the date along with the value, so no day is named without a loss', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {worst_realization: null, worst_realization_date: '2024-03-11'})]);
        expect(measures.worstRealizationDate).toBeNull();
    });

    it('keeps the date when there is a loss to attach it to', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {worst_realization: -0.061, worst_realization_date: '2024-03-11'})]);
        expect(measures.worstRealization).toBeCloseTo(0.061, 10);
        expect(measures.worstRealizationDate).toBe('2024-03-11');
    });

    it('reads the confidence the backend used instead of assuming the default', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {drawdown_confidence_level: 0.99, drawdown_at_risk: -0.21})]);
        expect(measures.drawdownConfidence).toBe(0.99);
    });

    it('reports no confidence rather than a borrowed one when the field is absent', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {drawdown_at_risk: -0.21})]);
        expect(measures.drawdownConfidence).toBeNull();
    });

    it('reads the ulcer index as a dispersion, which is non-negative by contract', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {ulcer_index: 0.087})]);
        expect(measures.ulcerIndex).toBe(0.087);
    });

    it('turns the two drawdown tails into positive magnitudes, deepest last', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {drawdown_at_risk: -0.21, conditional_drawdown_at_risk: -0.34})]);
        expect(measures.drawdownAtRisk).toBeCloseTo(0.21, 10);
        expect(measures.conditionalDrawdownAtRisk).toBeCloseTo(0.34, 10);
    });

    it('refuses a drawdown that arrives on the wrong side of zero', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {drawdown_at_risk: 0.21})]);
        expect(measures.drawdownAtRisk).toBeNull();
    });

    it('answers every field with null when the KPI analytic never ran', () => {
        const measures = buildTailMeasures([unavailable('historical_kpi')]);
        expect(measures).toEqual({
            worstRealization: null,
            worstRealizationDate: null,
            drawdownAtRisk: null,
            conditionalDrawdownAtRisk: null,
            drawdownConfidence: null,
            ulcerIndex: null,
        });
    });
});

/* ------------------------------------------------- D380: the formatters --- */

/**
 * D380 (08/10/2026) — the L1 panel never prints «−0.0%».
 *
 * Two defects, one decision. `ReturnHistogram`'s `axisPercent` chose its «−» from the
 * UNROUNDED value and then printed one decimal, so a real VaR of 0.04% became a cut «at
 * −0.0%»; the cards' `lossPercent` prefixed «−» to anything, a zero included, and
 * `gainPercent` a «+». The developer's answer, verbatim: «F2: «−0.04%» nelle cifre,
 * «0.0%» sugli assi». So two rules, as pure exports of `l1Helpers`:
 *
 * - **F1, a position on an axis** — `axisPercent(percent)`, in percent units as the bins
 *   are: one decimal, and the minus only when the printed digits are not all zero.
 * - **F2, a figure** — `figurePercent(fraction)`: exactly `formatShare(fraction, 1)`, the
 *   developer's 01/10 share rule (the caller's decimal from 1% up, at least one below 1%,
 *   two below 0.1%, then «< 0.01%» / «> −0.01%»), so only a true zero reads «0.0%».
 *   `lossPercent` and `gainPercent` word a positive magnitude as a fall and as a rise.
 *
 * The minus is U+2212 everywhere, the bound included: `formatShare` emits an ASCII hyphen,
 * and the panel's E2E net asserts the typographic one. Expected strings are written with
 * escapes, never typed glyphs: the two minus characters look the same on screen.
 *
 * The four names are read through the module namespace, as `levelHelpers.test.ts` reads
 * `errorDisplayCode`: until they exist, the cases calling them fail on an assertion naming
 * what is missing — those cases only, never the collection of this file — and
 * `svelte-check` stays clean in the red phase.
 */

const MINUS = '\u2212';
const PLACEHOLDER = '\u2014';
/** A minus in front of nothing but zeros — «−0%», «−0.0%», «−0.00%»: the string D380 removes. */
const NEGATIVE_ZERO = /^\u22120(\.0+)?%$/;
const NON_FINITE = [Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY];

type FormatterName = 'axisPercent' | 'figurePercent' | 'lossPercent' | 'gainPercent';
const FORMATTER_NAMES: readonly FormatterName[] = ['axisPercent', 'figurePercent', 'lossPercent', 'gainPercent'];

/** The module's exports by name: a name it does not export reads `undefined` here, instead of failing the whole file. */
const l1Exports = l1 as unknown as Record<string, unknown>;

/**
 * One of the four, called through the module. Until the export exists every case calling it
 * fails here, on the assertion that names what is missing, rather than on a `TypeError`.
 */
function callFormatter(name: FormatterName, value: number): string {
    const formatter = l1Exports[name];
    expect(typeof formatter, `l1Helpers exports no ${name}(): the L1 panel still formats with a private copy, the one that prints «−0.0%»`).toBe('function');
    return (formatter as (value: number) => string)(value);
}

const axisPercent = (percent: number): string => callFormatter('axisPercent', percent);
const figurePercent = (fraction: number): string => callFormatter('figurePercent', fraction);
const lossPercent = (magnitude: number): string => callFormatter('lossPercent', magnitude);
const gainPercent = (magnitude: number): string => callFormatter('gainPercent', magnitude);

/** F2 by definition: `formatShare`'s figure, its ASCII hyphen swapped for the typographic minus. */
const shareWithMinus = (fraction: number): string => formatShare(fraction, 1).replaceAll('-', MINUS);

/** `from / divisor` … `to / divisor`, one integer step at a time: a sweep with no accumulated float drift. */
function sweep(from: number, to: number, divisor: number): number[] {
    const values: number[] = [];
    for (let step = from; step <= to; step += 1) values.push(step / divisor);
    return values;
}

/** A number as a test title shows it, the sign of `-0` kept. */
const shown = (value: number): string => (Object.is(value, -0) ? '-0' : String(value));

interface Example {
    value: number;
    expected: string;
}

/** `it.each` rows that keep `-0` visible in the title. */
const rows = (examples: readonly Example[]) => examples.map((example) => ({...example, shown: shown(example.value)}));

/** F1, the D380 contract's examples: percent units in, one decimal out. */
const AXIS_EXAMPLES: readonly Example[] = [
    {value: 0, expected: '0.0%'},
    {value: -0, expected: '0.0%'},
    {value: -0.04, expected: '0.0%'},
    {value: -0.049, expected: '0.0%'},
    {value: 0.04, expected: '0.0%'},
    {value: -0.05, expected: '\u22120.1%'},
    {value: -0.12, expected: '\u22120.1%'},
    {value: -8.2, expected: '\u22128.2%'},
    {value: 8.1, expected: '8.1%'},
];

/** F2, the D380 contract's examples: a fraction in, the share rule's digits out. The last three, positive, follow from the rule. */
const FIGURE_EXAMPLES: readonly Example[] = [
    {value: -0.0004, expected: '\u22120.04%'},
    {value: -0.00004, expected: '>\u00A0\u22120.01%'},
    {value: -0.005, expected: '\u22120.5%'},
    {value: -0.0012, expected: '\u22120.1%'},
    {value: -0.018, expected: '\u22121.8%'},
    {value: 0, expected: '0.0%'},
    {value: -0, expected: '0.0%'},
    {value: 0.0004, expected: '0.04%'},
    {value: 0.00004, expected: '<\u00A00.01%'},
    {value: 0.018, expected: '1.8%'},
];

/** A positive loss magnitude, worded as a fall. The tiny bound follows from `figurePercent`. */
const LOSS_EXAMPLES: readonly Example[] = [
    {value: 0, expected: '0.0%'},
    {value: 0.0004, expected: '\u22120.04%'},
    {value: 0.031, expected: '\u22123.1%'},
    {value: 0.00004, expected: '>\u00A0\u22120.01%'},
];

/** A positive gain magnitude, worded as a rise: the plus on a figure, never on zero or on the bound. */
const GAIN_EXAMPLES: readonly Example[] = [
    {value: 0.0004, expected: '+0.04%'},
    {value: 0.05, expected: '+5.0%'},
    {value: 0, expected: '0.0%'},
    {value: 0.00004, expected: '<\u00A00.01%'},
    // The asymmetry the recovery row exists to teach: a 50% fall needs a +100% rise.
    {value: 1, expected: '+100.0%'},
];

describe('axisPercent — a position on the return axis (D380, F1)', () => {
    it.each(rows(AXIS_EXAMPLES))('prints $shown as $expected', ({value, expected}) => {
        expect(axisPercent(value)).toBe(expected);
    });

    it('never puts the minus in front of zeros, across −0.2…+0.2 percent in steps of 0.001', () => {
        const printed = sweep(-200, 200, 1000).map((percent) => ({percent, text: axisPercent(percent)}));
        // Control first: the sweep does reach values that print with the minus, so the
        // absence asserted next is not the absence of every minus.
        expect(printed.filter(({text}) => text.startsWith(MINUS)).length).toBeGreaterThan(0);
        expect(printed.filter(({text}) => NEGATIVE_ZERO.test(text))).toEqual([]);
        expect(
            printed.filter(({text}) => text.includes('-')),
            'an ASCII hyphen where the typographic minus belongs',
        ).toEqual([]);
    });

    it('prints the placeholder for a value that is not a number', () => {
        for (const value of NON_FINITE) expect(axisPercent(value), `axisPercent(${value})`).toBe(PLACEHOLDER);
    });
});

describe('figurePercent — a signed figure (D380, F2)', () => {
    it('takes its examples from the 01/10 share rule rather than inventing them', () => {
        // Control, green before the exports exist: each example is `formatShare(fraction, 1)`
        // with the hyphen swapped. If the share rule moves, this case says the examples move too.
        for (const {value, expected} of FIGURE_EXAMPLES) expect(shareWithMinus(value), `formatShare(${shown(value)}, 1)`).toBe(expected);
        for (const {value, expected} of LOSS_EXAMPLES) expect(shareWithMinus(-value), `formatShare(${shown(-value)}, 1)`).toBe(expected);
        for (const {value, expected} of GAIN_EXAMPLES) {
            const figure = shareWithMinus(value);
            expect(value === 0 || figure.startsWith('<') ? figure : `+${figure}`, `a rise of ${value}`).toBe(expected);
        }
    });

    it.each(rows(FIGURE_EXAMPLES))('prints $shown as $expected', ({value, expected}) => {
        expect(figurePercent(value)).toBe(expected);
    });

    it('never puts the minus in front of zeros, across −0.2…+0.2 percent in steps of 0.0001', () => {
        const printed = sweep(-2000, 2000, 1_000_000).map((fraction) => ({fraction, text: figurePercent(fraction)}));
        expect(printed.filter(({text}) => text.startsWith(MINUS)).length).toBeGreaterThan(0);
        expect(printed.filter(({text}) => NEGATIVE_ZERO.test(text))).toEqual([]);
        expect(
            printed.filter(({text}) => text.includes('-')),
            'an ASCII hyphen where the typographic minus belongs, the bound included',
        ).toEqual([]);
    });

    it('is formatShare with the typographic minus at every magnitude and on both signs, so the two rules cannot drift apart', () => {
        // Ten magnitudes per decade from 1e-8 to 10, plus the edges of every branch of the rule.
        const magnitudes = [...sweep(-80, 10, 10).map((exponent) => 10 ** exponent), 0.00004999, 0.00005, 0.0000999, 0.0001, 0.000999, 0.001, 0.0099, 0.00995, 0.0099999, 0.01];
        for (const magnitude of magnitudes) {
            for (const fraction of [magnitude, -magnitude]) expect(figurePercent(fraction), `figurePercent(${fraction})`).toBe(shareWithMinus(fraction));
        }
        for (const fraction of [0, -0, ...NON_FINITE]) expect(figurePercent(fraction), `figurePercent(${shown(fraction)})`).toBe(shareWithMinus(fraction));
    });

    it('prints the placeholder for a value that is not a number', () => {
        for (const value of NON_FINITE) expect(figurePercent(value), `figurePercent(${value})`).toBe(PLACEHOLDER);
    });
});

describe('lossPercent and gainPercent — a magnitude worded as a fall and as a rise (D380, F2)', () => {
    it.each(rows(LOSS_EXAMPLES))('lossPercent prints $shown as $expected', ({value, expected}) => {
        expect(lossPercent(value)).toBe(expected);
    });

    it.each(rows(GAIN_EXAMPLES))('gainPercent prints $shown as $expected', ({value, expected}) => {
        expect(gainPercent(value)).toBe(expected);
    });

    it('words every loss of the sweep as the figure of its negation', () => {
        for (const magnitude of sweep(0, 2000, 1_000_000)) expect(lossPercent(magnitude), `lossPercent(${magnitude})`).toBe(figurePercent(-magnitude));
    });

    it('signs a rise only where there is a figure to sign: never a zero, never the «< 0.01%» bound', () => {
        for (const magnitude of sweep(0, 2000, 1_000_000)) {
            const figure = shareWithMinus(magnitude);
            const expected = magnitude === 0 || figure.startsWith('<') ? figure : `+${figure}`;
            expect(gainPercent(magnitude), `gainPercent(${magnitude})`).toBe(expected);
        }
    });

    it('prints the placeholder for a magnitude that is not a number', () => {
        for (const value of NON_FINITE) {
            expect(lossPercent(value), `lossPercent(${value})`).toBe(PLACEHOLDER);
            expect(gainPercent(value), `gainPercent(${value})`).toBe(PLACEHOLDER);
        }
    });
});

/* ------------------------------------------ D380: the components' wiring --- */

/**
 * The two L1 components use the formatters above — a gate over the source, not a test of behaviour.
 *
 * The formatters are pure and pinned above; the defect lived in the private copies the two
 * components declared for themselves. The rule protected here is that the copies are gone and
 * the shared functions are what the panel calls:
 *
 * - neither `ReturnHistogram.svelte` nor `L1HowMuchItHurts.svelte` declares a function, or a
 *   variable holding one, named after any of the four;
 * - `ReturnHistogram.svelte` imports `axisPercent` and `figurePercent` from `./l1Helpers`, and
 *   `L1HowMuchItHurts.svelte` imports `lossPercent` and `gainPercent` from `./l1/l1Helpers`;
 * - the cut label, `$t('risk.levels.l1.histogram.cut', …)`, is a FIGURE: its value is built by
 *   `figurePercent`, never by `axisPercent` — «−0.04%», not «0.0%».
 *
 * Read through the Svelte compiler's own parser, as `warningTranslatorSites.test.ts` does: a
 * name in a comment or a string is not a declaration, and an aliased import is followed. The
 * inline controls run the detector on sources written here, through the same functions the two
 * real files go through.
 */

type AstNode = Record<string, unknown> & {type: string};

const CUT_LABEL_KEY = 'risk.levels.l1.histogram.cut';
const HISTOGRAM_FILE = './ReturnHistogram.svelte';
const PANEL_FILE = '../L1HowMuchItHurts.svelte';

function isAstNode(value: unknown): value is AstNode {
    return value !== null && typeof value === 'object' && typeof (value as {type?: unknown}).type === 'string';
}

/** Every AST node under `root`, depth first. The seen-set guards against a shared or cyclic reference. */
function* astNodes(root: unknown, seen: WeakSet<object> = new WeakSet()): Generator<AstNode> {
    if (root === null || typeof root !== 'object' || seen.has(root)) return;
    seen.add(root);
    if (isAstNode(root)) yield root;
    for (const child of Array.isArray(root) ? root : Object.values(root)) yield* astNodes(child, seen);
}

function identifierName(node: unknown): string | null {
    const name = isAstNode(node) && node.type === 'Identifier' ? node.name : null;
    return typeof name === 'string' ? name : null;
}

interface ImportBinding {
    from: string;
    /** The name the module exports. */
    exported: string;
    /** The name the component calls it by. */
    local: string;
}

/** The value imports of a parsed component: an `import type`, or an inline `type` specifier, binds nothing anyone can call. */
function importBindings(ast: unknown): ImportBinding[] {
    const bindings: ImportBinding[] = [];
    for (const node of astNodes(ast)) {
        if (node.type !== 'ImportDeclaration' || node.importKind === 'type' || !isAstNode(node.source)) continue;
        const from = node.source.value;
        for (const specifier of Array.isArray(node.specifiers) ? node.specifiers : []) {
            if (!isAstNode(specifier) || specifier.type !== 'ImportSpecifier' || specifier.importKind === 'type') continue;
            const exported = identifierName(specifier.imported);
            const local = identifierName(specifier.local);
            if (typeof from === 'string' && exported !== null && local !== null) bindings.push({from, exported, local});
        }
    }
    return bindings;
}

/** The names a component imports from `specifier`, as that module exports them. */
function importedFrom(source: string, specifier: string): string[] {
    return importBindings(parse(source, {modern: true}))
        .filter((binding) => binding.from === specifier)
        .map((binding) => binding.exported);
}

/** Which of the four formatters a component declares for itself: as a function, or as a variable holding one. */
function localFormatters(source: string): FormatterName[] {
    const declared = new Set<string>();
    for (const node of astNodes(parse(source, {modern: true}))) {
        const name = node.type === 'FunctionDeclaration' || node.type === 'VariableDeclarator' ? identifierName(node.id) : null;
        if (name !== null) declared.add(name);
    }
    return FORMATTER_NAMES.filter((name) => declared.has(name));
}

/**
 * For every `$t('risk.levels.l1.histogram.cut', …)` call, which of the four formatters its value
 * is built by, named as the module exports them (an alias is followed). One identifier of
 * indirection is followed too — `{value: cutText}` with `let cutText = $derived(figurePercent(…))`
 * — so a label built a line earlier counts as what it is.
 */
function cutLabelBuilders(source: string): FormatterName[][] {
    const ast = parse(source, {modern: true});
    const exportedName = new Map(importBindings(ast).map(({local, exported}) => [local, exported]));
    const initializers = new Map<string, unknown>();
    for (const node of astNodes(ast)) {
        const name = node.type === 'VariableDeclarator' ? identifierName(node.id) : null;
        if (name !== null) initializers.set(name, node.init);
    }
    const calledIn = (root: unknown): Set<string> => {
        const called = new Set<string>();
        for (const node of astNodes(root)) {
            const callee = node.type === 'CallExpression' ? identifierName(node.callee) : null;
            if (callee !== null) called.add(exportedName.get(callee) ?? callee);
        }
        return called;
    };

    const labels: FormatterName[][] = [];
    for (const node of astNodes(ast)) {
        if (node.type !== 'CallExpression' || identifierName(node.callee) !== '$t' || !Array.isArray(node.arguments)) continue;
        const [key, ...values] = node.arguments as unknown[];
        if (!isAstNode(key) || key.type !== 'Literal' || key.value !== CUT_LABEL_KEY) continue;
        const called = calledIn(values);
        for (const held of astNodes(values)) {
            const name = identifierName(held);
            if (name !== null && initializers.has(name)) for (const callee of calledIn(initializers.get(name))) called.add(callee);
        }
        labels.push(FORMATTER_NAMES.filter((name) => called.has(name)));
    }
    return labels;
}

/** A component's source, found from this file rather than from the runner's working directory. */
const componentSource = (path: string): string => readFileSync(fileURLToPath(new URL(path, import.meta.url)), 'utf8');

describe('D380 wiring gate — the detector itself', () => {
    it('sees a function declared in the script and a const holding an arrow, never a name in a comment, a string or an import', () => {
        const source = [
            '<script lang="ts">',
            "    import {gainPercent} from './l1/l1Helpers';",
            '    // function figurePercent(fraction) would be one more private copy',
            "    const hint = 'function figurePercent() {}';",
            '    function axisPercent(value: number): string {',
            '        return String(value);',
            '    }',
            '    const lossPercent = (fraction: number): string => String(fraction);',
            '</script>',
            '<p>{axisPercent(1)} {lossPercent(0.01)} {gainPercent(0.01)} {hint}</p>',
        ].join('\n');

        expect(localFormatters(source)).toEqual(['axisPercent', 'lossPercent']);
    });

    it('reads the value imports of one module, follows an alias and skips type-only imports', () => {
        const source = [
            '<script lang="ts">',
            "    import type {ReturnHistogram} from './l1Helpers';",
            "    import {axisPercent, figurePercent as asFigure, type ReturnBin} from './l1Helpers';",
            "    import {formatPercent} from '$lib/utils/core/formatPercent';",
            '    let {histogram}: {histogram: ReturnHistogram | null} = $props();',
            '    let bins: ReturnBin[] = [];',
            '</script>',
            '<p>{axisPercent(1)} {asFigure(0.01)} {formatPercent(1)} {histogram} {bins.length}</p>',
        ].join('\n');

        expect(importedFrom(source, './l1Helpers')).toEqual(['axisPercent', 'figurePercent']);
        expect(importedFrom(source, '$lib/utils/core/formatPercent')).toEqual(['formatPercent']);
    });

    it('tells which formatter builds the cut label: the axis copy of today, the figure, an alias of it, or a value built a line earlier', () => {
        // Every source also words another key with the axis formatter: only the cut label is read.
        const component = (script: string[], value: string): string => ['<script lang="ts">', ...script, '</script>', "<p>{$t('risk.levels.l1.histogram.observations', {values: {count: axisPercent(1)}})}</p>", `<p>{$t('${CUT_LABEL_KEY}', {values: {value: ${value}}})}</p>`].join('\n');

        expect(cutLabelBuilders(component(['    function axisPercent(value: number): string { return String(value); }'], 'axisPercent(histogram.cut)'))).toEqual([['axisPercent']]);
        expect(cutLabelBuilders(component(["    import {axisPercent, figurePercent} from './l1Helpers';"], 'figurePercent(histogram.cut / 100)'))).toEqual([['figurePercent']]);
        expect(cutLabelBuilders(component(["    import {axisPercent, figurePercent as asFigure} from './l1Helpers';"], 'asFigure(histogram.cut / 100)'))).toEqual([['figurePercent']]);
        expect(cutLabelBuilders(component(["    import {axisPercent, figurePercent} from './l1Helpers';", '    let cutText = $derived(figurePercent(histogram.cut / 100));'], 'cutText'))).toEqual([['figurePercent']]);
    });
});

describe('D380 wiring gate — the two L1 components', () => {
    it('ReturnHistogram.svelte declares no formatter of its own', () => {
        const source = componentSource(HISTOGRAM_FILE);
        // Barrier: the parser reached the script, so an empty answer below is not an unread file.
        expect(importBindings(parse(source, {modern: true})).length).toBeGreaterThan(0);
        expect(localFormatters(source)).toEqual([]);
    });

    it('L1HowMuchItHurts.svelte declares no formatter of its own', () => {
        const source = componentSource(PANEL_FILE);
        expect(importBindings(parse(source, {modern: true})).length).toBeGreaterThan(0);
        expect(localFormatters(source)).toEqual([]);
    });

    it('ReturnHistogram.svelte takes axisPercent and figurePercent from ./l1Helpers', () => {
        expect(importedFrom(componentSource(HISTOGRAM_FILE), './l1Helpers')).toEqual(expect.arrayContaining(['axisPercent', 'figurePercent']));
    });

    it('L1HowMuchItHurts.svelte takes lossPercent and gainPercent from ./l1/l1Helpers', () => {
        expect(importedFrom(componentSource(PANEL_FILE), './l1/l1Helpers')).toEqual(expect.arrayContaining(['lossPercent', 'gainPercent']));
    });

    it('the VaR cut label is a figure, built by figurePercent and not by the axis formatter', () => {
        const labels = cutLabelBuilders(componentSource(HISTOGRAM_FILE));
        // Barrier: the label is there, exactly once, so the next assertion is about how it is built.
        expect(labels).toHaveLength(1);
        expect(labels[0]).toEqual(['figurePercent']);
    });
});

/* ---------------------------------------------- D381: a loss of money --- */

/**
 * D381 (08/10/2026) — the L1 money caption never prints «−0,00 €».
 *
 * `lossMoney` prefixed «−» to whatever `formatCurrencyAmount` printed, so a loss that rounds to
 * no cents read as a fall of nothing. `lossAmount(amount, format)` takes the sign away from the
 * string: it formats the MAGNITUDE, `format(String(Math.abs(amount)))`, and puts U+2212 in front
 * only when that magnitude is finite and `Math.round(magnitude * 100) !== 0` — the cents the
 * caption prints. A non-finite amount gets the formatter's own output, unsigned.
 *
 * Read through the module namespace like the four above: until the export exists, only the
 * cases calling it fail, on an assertion naming it.
 */

type AmountFormatter = (value: string) => string;

/** `lossAmount`, called through the module. Until the export exists every case calling it fails here. */
function lossAmount(amount: number, format: AmountFormatter): string {
    const helper = l1Exports.lossAmount;
    expect(typeof helper, 'l1Helpers exports no lossAmount(): the L1 caption still prefixes its own minus, and prints «−0.00 €» for a loss of nothing').toBe('function');
    return (helper as (amount: number, format: AmountFormatter) => string)(amount, format);
}

/** A stand-in for `formatCurrencyAmount`: its placeholder for anything that is not a finite number, two decimals otherwise. */
const currencyLike: AmountFormatter = (value) => {
    const amount = Number(value);
    return Number.isFinite(amount) ? `${amount.toFixed(2)} EUR` : PLACEHOLDER;
};

/** `PRIVACY_PLACEHOLDER`: with privacy on, `formatCurrencyAmount` prints this for ANY amount, zero included. */
const MASK = '\u2022\u2022\u2022';
const masked: AmountFormatter = () => MASK;

/** The D381 contract's cases, through `currencyLike`. */
const LOSS_AMOUNT_EXAMPLES: readonly Example[] = [
    {value: 0, expected: '0.00 EUR'},
    {value: -0, expected: '0.00 EUR'},
    {value: 0.004, expected: '0.00 EUR'},
    {value: 0.005, expected: '\u22120.01 EUR'},
    {value: 12.3, expected: '\u221212.30 EUR'},
    // A negative amount is worded by its magnitude: the sign of the input is not the sign printed.
    {value: -12.3, expected: '\u221212.30 EUR'},
];

describe('lossAmount — a loss of money as a fall (D381)', () => {
    it.each(rows(LOSS_AMOUNT_EXAMPLES))('words $shown as $expected', ({value, expected}) => {
        expect(lossAmount(value, currencyLike)).toBe(expected);
    });

    it('hands the formatter the magnitude, as a string', () => {
        const received: string[] = [];
        const recording: AmountFormatter = (value) => {
            received.push(value);
            return value;
        };
        lossAmount(-12.3, recording);
        lossAmount(-0, recording);
        expect(received).toEqual(['12.3', '0']);
    });

    it('leaves an amount that is not a number to the formatter, unsigned', () => {
        for (const amount of NON_FINITE) expect(lossAmount(amount, currencyLike), `lossAmount(${amount})`).toBe(PLACEHOLDER);
    });

    it('decides the sign on the number, because a masked amount has no digits to read', () => {
        // The reason the rule is numeric. With privacy on, every amount prints «•••»: a rule that
        // read the formatted text could not tell a loss of 12.30 from a loss of nothing, and would
        // either sign both or neither. The number still knows.
        expect(lossAmount(0, masked)).toBe(MASK);
        expect(lossAmount(0.004, masked)).toBe(MASK);
        expect(lossAmount(0.005, masked)).toBe(`${MINUS}${MASK}`);
        expect(lossAmount(12.3, masked)).toBe(`${MINUS}${MASK}`);
    });

    it('signs exactly the amounts whose caption shows a cent, across −0.02…+0.02 in steps of 0.0001', () => {
        const worded = sweep(-200, 200, 10_000).map((amount) => ({amount, text: lossAmount(amount, currencyLike), cents: currencyLike(String(Math.abs(amount)))}));
        // Control first: the sweep does reach amounts that print with the minus.
        expect(worded.filter(({text}) => text.startsWith(MINUS)).length).toBeGreaterThan(0);
        expect(worded.filter(({text}) => text === `${MINUS}0.00 EUR`)).toEqual([]);
        expect(worded.filter(({text, cents}) => text.startsWith(MINUS) !== (cents !== '0.00 EUR'))).toEqual([]);
    });
});

/* ------------------------------------ D381: the caption's wiring gate --- */

/**
 * Every sign in the L1 panel comes from `l1Helpers` — extended to the money caption.
 *
 * `L1HowMuchItHurts.svelte` must take `lossAmount` from `./l1/l1Helpers` and call it, and no
 * string or template literal in the component may carry U+2212 any more: the last one is the
 * `` `\u2212${…}` `` that `lossMoney` builds today. Literals are read by their COOKED value,
 * so an escape and a typed glyph are the same thing to the gate, while a comment or the text of
 * the page is not a literal at all. The scan covers the script and the markup's expressions
 * alike: a sign written in the markup would bypass `l1Helpers` just as well.
 */

/** The cooked text of every string literal and template chunk in a component that carries U+2212. */
function minusLiterals(source: string): string[] {
    const texts: string[] = [];
    for (const node of astNodes(parse(source, {modern: true}))) {
        if (node.type === 'Literal' && typeof node.value === 'string') texts.push(node.value);
        if (node.type === 'TemplateElement' && node.value !== null && typeof node.value === 'object') {
            const cooked = (node.value as {cooked?: unknown}).cooked;
            if (typeof cooked === 'string') texts.push(cooked);
        }
    }
    return texts.filter((text) => text.includes(MINUS));
}

/** How many calls a component makes to `exported`, through whatever local name it imported it as. */
function callsTo(source: string, exported: string): number {
    const ast = parse(source, {modern: true});
    const locals = new Set(importBindings(ast).flatMap((binding) => (binding.exported === exported ? [binding.local] : [])));
    let calls = 0;
    for (const node of astNodes(ast)) {
        const callee = node.type === 'CallExpression' ? identifierName(node.callee) : null;
        if (callee !== null && locals.has(callee)) calls += 1;
    }
    return calls;
}

describe('D381 wiring gate — the detector itself', () => {
    it('finds U+2212 in a template chunk, an escaped string and a typed one, never in a comment, the page text or another dash', () => {
        const source = [
            '<script lang="ts">',
            '    let {amount} = $props();',
            '    const built = `\\u2212${amount}`;',
            "    const escaped = '\\u2212';",
            "    const typed = '\u2212';",
            '    // a fall prints \u2212 in this comment',
            "    const dash = '\\u2014';",
            '</script>',
            "<p title={'\\u2212'}>\u2212 in the text of the page {built} {escaped} {typed} {dash}</p>",
        ].join('\n');

        expect(minusLiterals(source)).toEqual([MINUS, MINUS, MINUS, MINUS]);
    });

    it('counts the calls to an import, followed through its alias', () => {
        const source = [
            '<script lang="ts">',
            "    import {lossAmount as asLoss} from './l1/l1Helpers';",
            '    let {amount} = $props();',
            '    function lossMoney(value: number): string {',
            '        return asLoss(value, String);',
            '    }',
            '</script>',
            '<p>{lossMoney(amount)} {asLoss(amount, String)}</p>',
        ].join('\n');

        expect(callsTo(source, 'lossAmount')).toBe(2);
        expect(callsTo(source, 'lossPercent')).toBe(0);
    });
});

describe('D381 wiring gate — the L1 components', () => {
    it('L1HowMuchItHurts.svelte takes lossAmount from ./l1/l1Helpers and calls it', () => {
        const source = componentSource(PANEL_FILE);
        expect(importedFrom(source, './l1/l1Helpers')).toEqual(expect.arrayContaining(['lossAmount']));
        expect(callsTo(source, 'lossAmount')).toBeGreaterThan(0);
    });

    it.each([PANEL_FILE, HISTOGRAM_FILE])('%s builds no minus sign of its own', (file) => {
        expect(minusLiterals(componentSource(file)), `${file}: a U+2212 in a literal is a sign that did not come from l1Helpers`).toEqual([]);
    });
});
