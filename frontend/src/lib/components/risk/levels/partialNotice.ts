/**
 * One notice above the levels, instead of one per level (developer's decision of 24/09/2026).
 *
 * Its own module for the reason `levelMetadata` has one — `levelHelpers.ts` is at its size
 * ceiling. The levels keep only the measurements that did not come back at all, named where
 * they are missing; what is partial, and why, is said once, at the top.
 */
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {degradedResults, resultReasons, type ResultHealth, type ResultReason, type WarningTranslator} from './levelHelpers';

/** The first result of each instance, in order; missing ones dropped.
 *
 *  `historical_kpi` feeds both L1 and L3, so the panel's slices overlap: without this, a warning
 *  on it would be counted twice and a partial status named twice. */
export function uniqueByInstance(results: ReadonlyArray<RiskAnalyticResult | null | undefined>): RiskAnalyticResult[] {
    const seen = new Set<string>();
    const unique: RiskAnalyticResult[] = [];
    for (const result of results) {
        if (!result || seen.has(result.instance_id)) continue;
        seen.add(result.instance_id);
        unique.push(result);
    }
    return unique;
}

/** What the notice says: the partial measurements, per instance, and every reason, once per sentence. */
export interface PartialNotice {
    partial: ResultHealth[];
    reasons: ResultReason[];
}

/**
 * The notice above the levels, from the results the levels render.
 *
 * Only `partial` is named here: a measurement that did not come back at all stays under its level,
 * where its absence is. Reasons are not filtered on status — a warning on a complete result is still
 * worth reading (the rule `resultReasons` already states).
 */
export function partialNotice(results: ReadonlyArray<RiskAnalyticResult | null | undefined>, translate?: WarningTranslator, labels: Readonly<Record<string, string>> = {}): PartialNotice {
    const unique = uniqueByInstance(results);
    return {
        partial: degradedResults(unique, labels).filter((entry) => entry.status === 'partial'),
        reasons: resultReasons(unique, translate),
    };
}

/** The part of a level's health that stays under the level: what did not come back at all. */
export function levelErrorHealth(health: readonly ResultHealth[]): ResultHealth[] {
    return health.filter((entry) => entry.status === 'unavailable' || entry.status === 'failed');
}

/** The catalogue key of an analytic's name: `historical_var` is `risk.analytics.historicalVar.name`. */
export function analyticNameKey(code: string): string {
    const camel = code.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
    return `risk.analytics.${camel}.name`;
}
