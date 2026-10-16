import {describe, expect, it} from 'vitest';

import {schemas} from '$lib/api';

import {buildDriftUncertainty, type DriftUncertaintyInput, type DriftUncertaintyView} from './driftUncertainty';

/**
 * What the band leaves out, and therefore what these tests have to prove.
 *
 * The cone is dispersion *conditional on* an estimated drift, and that drift is
 * itself a sample mean: it carries a standard error that compounds over the
 * horizon. The backend publishes the resulting factor together with the sample
 * size it came from; this module turns the pair into the interval a reader can
 * act on, and into the one comparison worth making — whether estimation error
 * alone has outgrown the band drawn above it.
 *
 * Two claims follow, and each is a group below.
 *
 *   - The interval is **multiplicative**, because the quantity it qualifies is
 *     compounded. An additive margin would be a different statement, and on the
 *     Bitcoin disclosure a visibly false one.
 *   - The comparison is between two multiplicative spans, so it carries no
 *     threshold — which is precisely why it has to be tested on cases where the
 *     verdict and the size of the median disagree. A flag that fired on "big
 *     number" would pass a suite built only on Bitcoin.
 *
 * The third group is about silence. The server validator refuses to emit half
 * the pair, so a half arriving here means the payload is not one this build
 * produced — and the generated client would not stop it: `generated.ts:14561`
 * parses both fields as `z.union([z.number(), z.null()]).optional()`, having
 * dropped the `ge=1` floor and the positive-integer bound the schema declares.
 * On the client these guards are the only ones left standing.
 */

/**
 * Three disclosures read off the running backend rather than invented.
 *
 * All three are 365-day horizons over a 95-day window, which is what makes them
 * worth keeping: a small `sqrt(n)` is where the factor shows.
 *
 * They are a **snapshot, not a constant**. The lane's fixture is regenerated on
 * every `db populate`, so re-measuring moves every literal here — `n` was 93 and
 * 96 on two consecutive populations, and bitcoin's factor 29.9 and 27.5. What
 * survives that is the arithmetic and the verdict, and those are the only two
 * things asserted below. Anyone tempted to "refresh" these numbers should know
 * they will get different ones and that nothing here requires them to match.
 */
interface MeasuredDisclosure extends DriftUncertaintyInput {
    driftUncertaintyFactor: number;
    driftUncertaintyObservations: number;
    terminal: {p05: number; p50: number; p95: number};
}

/** A diversified portfolio: the factor is small because cash and covariance damp it. */
const PORTFOLIO: MeasuredDisclosure = {
    driftUncertaintyFactor: 1.2020438487233716,
    driftUncertaintyObservations: 96,
    terminal: {p05: 0.15096607972691328, p50: 0.39849746941772757, p95: 1.2430401057033476},
};

/** One volatile asset held alone: the estimate is well over twice the band. */
const BITCOIN: MeasuredDisclosure = {
    driftUncertaintyFactor: 27.460996635244182,
    driftUncertaintyObservations: 96,
    terminal: {p05: 4.31311906831466, p50: 16.826374720946625, p95: 59.70581920183222},
};

/** A mild median on a shorter history — the case the whole comparison exists for. */
const APPLE: MeasuredDisclosure = {
    driftUncertaintyFactor: 4.758843606629042,
    driftUncertaintyObservations: 68,
    terminal: {p05: -0.4318918055776699, p50: 0.0390116009830781, p95: 0.8349359054344394},
};

const MEASURED: ReadonlyArray<readonly [string, MeasuredDisclosure]> = [
    ['portfolio', PORTFOLIO],
    ['bitcoin', BITCOIN],
    ['apple', APPLE],
];

/** The span of the band itself, which is the quantity the factor is weighed against. */
function bandSpan(disclosure: MeasuredDisclosure): number {
    return (1 + disclosure.terminal.p95) / (1 + disclosure.terminal.p05);
}

/** Read a view that must exist: a null here is a broken case, not a result. */
function built(input: DriftUncertaintyInput): DriftUncertaintyView {
    const view = buildDriftUncertainty(input);
    if (view === null) throw new Error('the disclosure is complete, so a view was expected');
    return view;
}

describe('the interval applied to the median', () => {
    it('divides and multiplies the median by the factor', () => {
        // Hand-computed rather than re-derived from the fixture: 1.39849746941772757
        // divided and multiplied by 1.2020438487233716, minus one. Recomputing the
        // formula here would assert that the module agrees with itself.
        const view = built(PORTFOLIO);
        expect(view.low).toBeCloseTo(0.16343299, 8);
        expect(view.high).toBeCloseTo(0.68105528, 8);
        expect(view.observations).toBe(96);
    });

    it('carries the same arithmetic into a case where it dominates the answer', () => {
        // Apple's median is +3.9 %; its drift interval runs from -78 % to +394 %.
        // That gap *is* the feature — a reader shown only the cone would take the
        // median for a forecast — so it is worth pinning as a number, not as a flag.
        const view = built(APPLE);
        expect(view.low).toBeCloseTo(-0.78166721, 8);
        expect(view.high).toBeCloseTo(3.94449371, 8);
        expect(view.observations).toBe(68);
    });

    it('is multiplicative, not additive', () => {
        // Stated as the property rather than as another pair of literals: the two
        // sides are equidistant from the median in *log* space and demonstrably
        // not in level space. An additive margin would satisfy the second half and
        // fail the first, which is the mistake this asserts against.
        for (const [name, disclosure] of MEASURED) {
            const view = built(disclosure);
            const median = disclosure.terminal.p50;
            expect(Math.log1p(view.high) - Math.log1p(median), `${name}: upper leg in log space`).toBeCloseTo(Math.log1p(median) - Math.log1p(view.low), 12);
            expect(view.high - median, `${name}: the level-space legs cannot be equal`).toBeGreaterThan(median - view.low);
        }
    });

    it('collapses onto the median when the factor is exactly one', () => {
        // The guard is `factor < 1`, not `<= 1`, and the difference is a real
        // statement: a series with no dispersion has no estimation error to
        // disclose, and saying so is honest. Rejecting it would print nothing at
        // all and leave the reader with the same unqualified cone as a payload
        // predating the field.
        const view = built({...PORTFOLIO, driftUncertaintyFactor: 1});
        expect(view.low).toBeCloseTo(PORTFOLIO.terminal.p50, 12);
        expect(view.high).toBeCloseTo(PORTFOLIO.terminal.p50, 12);
        expect(view.exceedsBand).toBe(false);
    });
});

describe('exceedsBand', () => {
    it('stays quiet while the band is the wider of the two', () => {
        // ×1.95 of band against ×1.20 of estimation error: the cone already tells
        // the larger part of the story, so the line is a footnote and not a warning.
        expect(bandSpan(PORTFOLIO)).toBeCloseTo(1.9488, 4);
        expect(built(PORTFOLIO).exceedsBand).toBe(false);
    });

    it('fires when estimation error outruns the band', () => {
        // ×27.5 against a band of ×11.43 — the case that motivated the feature.
        expect(bandSpan(BITCOIN)).toBeCloseTo(11.426, 3);
        expect(built(BITCOIN).exceedsBand).toBe(true);
    });

    it('does not read the size of the median', () => {
        // The trap this guards. Apple's median is ten times *smaller* than the
        // portfolio's and its band is wider, yet it is the one flagged: 68
        // observations against a 365-day horizon, and ×4.76 beats ×3.23. A
        // rule keyed on "the number looks big" would invert both verdicts, and
        // nothing else on screen would say so.
        expect(APPLE.terminal.p50).toBeLessThan(PORTFOLIO.terminal.p50);
        expect(bandSpan(APPLE)).toBeGreaterThan(bandSpan(PORTFOLIO));
        expect(bandSpan(APPLE)).toBeCloseTo(3.2299, 4);
        expect(built(APPLE).exceedsBand).toBe(true);
        expect(built(PORTFOLIO).exceedsBand).toBe(false);
    });

    it('needs strictly more than an equal span', () => {
        // An interval exactly as wide as the band has not outgrown it. The
        // boundary is worth pinning because the comparison has no tolerance to
        // absorb it: the wording the `true` branch renders says "wider than the
        // band above", and at equality that sentence is false.
        const terminal = {p05: 0, p50: 0.2, p95: 0.5};
        expect(built({driftUncertaintyFactor: 1.5, driftUncertaintyObservations: 93, terminal}).exceedsBand).toBe(false);
        expect(built({driftUncertaintyFactor: 1.5000001, driftUncertaintyObservations: 93, terminal}).exceedsBand).toBe(true);
    });
});

describe('an incomplete disclosure', () => {
    it('says nothing when either half of the pair is missing', () => {
        // Half a pair is not a payload this build produced, and completing it
        // here would invent the very number the disclosure exists to avoid
        // inventing. `null` and `undefined` both occur in practice: the first
        // from a cached result serialised before the field existed, the second
        // from `output?.drift_uncertainty_factor` when the analytic is absent.
        const halves: ReadonlyArray<readonly [string, DriftUncertaintyInput]> = [
            ['factor null', {...PORTFOLIO, driftUncertaintyFactor: null}],
            ['factor undefined', {...PORTFOLIO, driftUncertaintyFactor: undefined}],
            ['observations null', {...PORTFOLIO, driftUncertaintyObservations: null}],
            ['observations undefined', {...PORTFOLIO, driftUncertaintyObservations: undefined}],
        ];
        for (const [name, input] of halves) {
            expect(buildDriftUncertainty(input), name).toBeNull();
        }
    });

    it('says nothing when there is no band to apply it to', () => {
        // The interval is *the median* moved by the factor. With no terminal band
        // point there is no median, and a factor on its own is a ratio with
        // nothing to multiply.
        expect(buildDriftUncertainty({...PORTFOLIO, terminal: null}), 'terminal null').toBeNull();
        expect(buildDriftUncertainty({...PORTFOLIO, terminal: undefined}), 'terminal undefined').toBeNull();
    });

    it('says nothing for a factor that cannot be a 95 % bound', () => {
        // Below 1 the "interval" would close in on the median instead of opening
        // around it, so the panel would report estimation error as *reassurance*.
        // The non-finite entries are the shapes JSON and arithmetic can produce
        // where the schema's `ge=1` no longer applies on this side of the wire.
        for (const factor of [0.99, 0, -1, Number.NaN, Number.POSITIVE_INFINITY]) {
            expect(buildDriftUncertainty({...PORTFOLIO, driftUncertaintyFactor: factor}), `factor ${factor}`).toBeNull();
        }
    });

    it('says nothing for a sample size that cannot have produced it', () => {
        // The count is not decoration: the rendered sentence reads "the drift
        // comes from {count} observations", so a zero or a negative would print a
        // claim about a sample that does not exist.
        for (const observations of [0, -3, Number.NaN, Number.POSITIVE_INFINITY]) {
            expect(buildDriftUncertainty({...PORTFOLIO, driftUncertaintyObservations: observations}), `observations ${observations}`).toBeNull();
        }
    });
});

describe('a band floored at total loss', () => {
    it('still applies the interval but withholds the comparison', () => {
        // `(1 + p95) / (1 + p05)` is not a ratio when the floor is zero or below,
        // and the module answers by declining that one question rather than by
        // dropping the whole disclosure — the interval does not depend on `p05`.
        //
        // Today no conforming payload reaches this: the band point is `gt=-1` on
        // both sides of the wire. The guard is on this module's own signature,
        // and the reason it earns a test is the alternative — a NaN comparison is
        // false either way, so an unguarded version would look identical here and
        // differ the day the expression is rewritten as `p95 - p05`.
        for (const p05 of [-1, -1.2]) {
            const view = built({...BITCOIN, terminal: {...BITCOIN.terminal, p05}});
            expect(view.exceedsBand, `p05 ${p05}: a span that is not a number is not "narrower"`).toBe(false);
            expect(view.observations).toBe(BITCOIN.driftUncertaintyObservations);
            expect(view.low).toBeCloseTo(built(BITCOIN).low, 12);
            expect(view.high).toBeCloseTo(built(BITCOIN).high, 12);
        }
    });
});

describe('the measured fixtures', () => {
    it('are band points the wire contract admits', () => {
        // The sibling specs learned this the expensive way: a fixture the
        // generated Zod would reject makes the helper look broken when only the
        // fixture was. Here it also keeps the reconstructed portfolio percentiles
        // honest — an impossible triple would otherwise sit unnoticed under a
        // green comparison.
        for (const [name, disclosure] of MEASURED) {
            const parsed = schemas.RiskSimulationBandPoint.safeParse({day: 365, ...disclosure.terminal});
            expect(parsed.success, `${name}: terminal band point`).toBe(true);
        }
    });
});
