/**
 * The provenance figures of a level: how many observations, over what coverage.
 *
 * Split out of `levelHelpers` rather than added to it, because that file sits at
 * 564 lines against a 600-line ceiling and this is a whole second subject. It is
 * re-exported from there, so every consumer still has one door.
 *
 * Why the four levels need this at all: `RiskResultFrame` renders metadata and
 * is used **only** by the legacy panel. The day `RiskLevelsPanel` replaces it,
 * the observation count leaves the product — and a window is not a technical
 * detail. The same asset pair measured over one month and over one year returns
 * a correlation of 0.96 and of 0.67. A surface that shows a number without
 * saying what it was computed over is not informing, it is asserting.
 */
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import {riskMetadata, singleValue} from '$lib/risk/riskTypes';

export interface LevelMetadataRow {
    /** Dedup signature; stable across renders because it is built from the values. */
    key: string;
    /** Every analytic whose figures are the ones on this row. */
    codes: string[];
    observations: number | null;
    coverage: number | null;
    annualizationFactor: number | null;
    returnBasis: string | null;
}

function finiteOrNull(value: unknown): number | null {
    const single = singleValue(value as number | null | undefined);
    return typeof single === 'number' && Number.isFinite(single) ? single : null;
}

/**
 * One row per *distinct* set of figures, not one per analytic.
 *
 * A level renders several analytics, and `RiskResultFrame` renders exactly one
 * result — so the shape does not carry over. Picking a representative would be
 * the easy translation and the wrong one: the moment two analytics disagree,
 * the reader is shown one window and told it covers numbers computed over
 * another, which reads as a fact rather than as a missing one.
 *
 * Collapsing instead means the ordinary case is a single row — every analytic in
 * the level agreeing, which is what "Observations 93" is meant to say — and the
 * exceptional case splits in two, naming which analytics went which way. It is
 * the same choice `resultReasons` makes about a repeated sentence: publish the
 * arity rather than draw it twice.
 *
 * `method` is deliberately left out. It is a long free-form string the legacy
 * frame renders `break-all` across the full width, and repeated per analytic it
 * would be the only thing on screen. It stays available on the result for any
 * surface that wants it.
 */
export function levelMetadata(results: ReadonlyArray<RiskAnalyticResult | null | undefined>): LevelMetadataRow[] {
    const rows = new Map<string, LevelMetadataRow>();
    for (const result of results) {
        if (!result) continue;
        const metadata = riskMetadata(result);
        if (!metadata) continue;
        const observations = finiteOrNull(metadata.n_observations);
        const coverage = finiteOrNull(metadata.coverage);
        const annualizationFactor = finiteOrNull(metadata.annualization_factor);
        const basis = singleValue(metadata.return_basis as string | null | undefined);
        const returnBasis = typeof basis === 'string' && basis.trim() !== '' ? basis : null;

        const key = `${observations}|${coverage}|${annualizationFactor}|${returnBasis}`;
        const existing = rows.get(key);
        const code = typeof result.analytic_code === 'string' ? result.analytic_code : '';
        if (existing) {
            if (code && !existing.codes.includes(code)) existing.codes.push(code);
            continue;
        }
        rows.set(key, {key, codes: code ? [code] : [], observations, coverage, annualizationFactor, returnBasis});
    }
    return [...rows.values()];
}

/**
 * A catalogue value worded, falling back to the **raw value** rather than a key.
 *
 * The sibling of `translateErrorCode`, and deliberately not the same function:
 * there, an unknown code has no useful text and falls back to a generic
 * sentence. Here the raw token — `daily_simple`, `current_composition_backtest`
 * — is itself informative, so degrading to it loses formatting and keeps the
 * meaning.
 *
 * ⚠️ The comparison is the point. `RiskResultFrame:108` builds
 * `risk.returnBasis.${value}` with no guard at all, which is the defect
 * `levelHelpers` records: a value nobody has seen prints its own key on screen.
 * That line is still unguarded in the legacy frame; this is the redesign's
 * version of it, and it does not repeat the fault.
 */
export function translateOrRaw(prefix: string, value: string, translate: (key: string) => string): string {
    const key = `${prefix}.${value}`;
    const translated = translate(key);
    return translated === key ? value : translated;
}
