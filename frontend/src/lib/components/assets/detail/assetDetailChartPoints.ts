/**
 * Merging new price points into the asset detail chart's data.
 *
 * @module components/assets/detail/assetDetailChartPoints
 */

/**
 * `existing` with `delta` merged in by date, sorted by date ascending (I-bis #24).
 *
 * - A new date is appended.
 * - A date already present is shallow-merged: the delta's fields update the point, and the
 *   fields only the existing point has (such as `original_close`, set by the chart load) stay.
 *
 * The page merges the `changed_points` of a sync answer and a polled live point. A sync delta
 * carries raw database values without FX applied, so the page merges it only while the chart
 * shows the asset's own currency.
 */
export function mergeChartPointsIncremental<T extends {date: string}>(existing: T[], delta: T[]): T[] {
    const byDate = new Map<string, T>(existing.map((p) => [p.date, p]));
    for (const np of delta) {
        const prev = byDate.get(np.date);
        byDate.set(np.date, prev ? ({...prev, ...np} as T) : np);
    }
    return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
}
