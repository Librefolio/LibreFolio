/**
 * The «old exchange rate» banner row (developer question 18, 28/10): the report already lists, in
 * `data_quality.stale_fx_pairs`, the pairs it valued on the last day from a stored rate older than the threshold. The
 * dashboard shows them as one warning row, like the old prices (`STALE_PRICE`), with a button that syncs those pairs.
 *
 * The report has no `DataQualityIssue` for them, so the row is built here, in the shape the banner already knows.
 *
 * @module features/dashboard/staleFxIssue
 */

import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';

/** The part of the report's `StaleFxPair` the row reads. */
export interface StaleFxPairLike {
    pair: string;
    last_rate_date: string;
    stale_days: number;
}

/** Banner code of the row; the button's action is `STALE_FX_ACTION`. */
export const STALE_FX_CODE = 'STALE_FX';
export const STALE_FX_ACTION = 'sync_stale_fx';

/**
 * One warning row for all the stale pairs, or null when none is stale.
 *
 * `message_params.date_from`/`date_to` are the oldest stored rate and `today`: `buildMissingFxRatesSyncRequest` turns
 * them into the sync of those dates (a week either side, never past today), the same request the missing-rates button sends.
 */
export function staleFxIssue(pairs: readonly StaleFxPairLike[] | null | undefined, today: string): DataQualityIssue | null {
    if (!pairs || pairs.length === 0) return null;
    const oldest = pairs.reduce((a, b) => (b.last_rate_date < a.last_rate_date ? b : a));
    const days = Math.max(...pairs.map((p) => p.stale_days));
    return {
        domain: 'portfolio',
        code: STALE_FX_CODE,
        severity: 'warning',
        message_i18n_key: 'dataQuality.staleFx',
        message_params: {count: pairs.length, days, date_from: oldest.last_rate_date, date_to: today},
        count: pairs.length,
        affected_fx_pairs: pairs.map((p) => p.pair),
        cta_action: STALE_FX_ACTION,
        cta_target: pairs[0].pair,
        group_key: 'stale_fx',
    };
}

/** `EUR/usd`, `usd-EUR` → `EUR-USD`: the spelling the sync request and the report can both be compared in. */
function pairKey(pair: string): string {
    return pair
        .split(/[-/]/)
        .map((code) => code.trim().toUpperCase())
        .filter(Boolean)
        .sort()
        .join('-');
}

/**
 * The requested pairs that the report still lists as stale after a sync that worked (Y6-6): the provider has no newer rate for them yet.
 * A pair the sync did bring up to date is no longer in `stale_fx_pairs`, so it is not here. In the order requested.
 */
export function pairsStillStale(requested: readonly string[], staleNow: readonly StaleFxPairLike[] | null | undefined): string[] {
    const stale = new Set((staleNow ?? []).map((entry) => pairKey(entry.pair)));
    return requested.filter((pair) => stale.has(pairKey(pair)));
}
