/**
 * What the cone leaves out: that the drift it rests on is itself an estimate.
 *
 * A simulated band is dispersion **conditional on** an estimated drift. Drawn
 * alone it therefore reads as the whole uncertainty while being only part of
 * it, and the missing part is not small: on a 95-day window of a single volatile
 * asset the backend measures a drift interval wider than the band itself.
 *
 * The backend publishes the factor and the sample size it came from; this module
 * turns them into the two things a reader can act on — the interval **applied**
 * to the median, and whether that interval has outgrown the band above it.
 *
 * Nothing here chooses a number. The one comparison made is between two
 * multiplicative quantities, which is why it needs no threshold: a middle
 * "somewhat wide" bucket would smuggle an arbitrary constant back in through
 * the only door this design left closed.
 */

export interface DriftUncertaintyView {
    /** The sample the drift was estimated from, so the factor reads as a consequence. */
    observations: number;
    /** The median divided by the factor, as a return. */
    low: number;
    /** The median multiplied by the factor, as a return. */
    high: number;
    /** Whether estimation error alone spans more than the simulated band. */
    exceedsBand: boolean;
}

export interface DriftUncertaintyInput {
    driftUncertaintyFactor: number | null | undefined;
    driftUncertaintyObservations: number | null | undefined;
    /** The terminal band point: the cone's last day, or null when there is none. */
    terminal: {p05: number; p50: number; p95: number} | null | undefined;
}

/**
 * Build the view model, or null when there is nothing honest to say.
 *
 * Null is returned whenever the disclosure is incomplete rather than guessed at:
 * an older cached result predating the field, a band that never arrived, or a
 * factor whose paired sample size is missing. The backend's own validator
 * refuses to emit half of the pair, so a half here means the payload is not one
 * this build produced — and filling in the gap would invent the very number the
 * disclosure exists to avoid inventing.
 */
export function buildDriftUncertainty(input: DriftUncertaintyInput): DriftUncertaintyView | null {
    const {driftUncertaintyFactor: factor, driftUncertaintyObservations: observations, terminal} = input;
    if (factor == null || observations == null || !terminal) return null;
    if (!Number.isFinite(factor) || factor < 1 || !Number.isFinite(observations) || observations <= 0) return null;

    const growth = 1 + terminal.p50;
    const floor = 1 + terminal.p05;
    const bandSpan = floor > 0 ? (1 + terminal.p95) / floor : Number.NaN;

    return {
        observations,
        low: growth / factor - 1,
        high: growth * factor - 1,
        exceedsBand: Number.isFinite(bandSpan) && factor > bandSpan,
    };
}
