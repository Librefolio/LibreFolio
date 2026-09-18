/**
 * correlationHelpers — the decisions the correlation view makes before it
 * touches ECharts.
 *
 * Everything here is pure: a correlation matrix in, an ordering / a band / a
 * list of pairs out. The heatmap component mounts a canvas and subscribes to
 * i18n, so none of this is reachable from a component test — which is exactly
 * why the branch-dense parts (missing cells, zero-variance series, ties) live
 * in this file and are asserted directly.
 *
 * Two conventions hold throughout:
 *
 * - The backend emits the **full N×N matrix**, diagonal included (see
 *   `risk_plugins/correlation.py`). Callers that want half of it filter here;
 *   the payload is never assumed to be triangular.
 * - A cell whose `status` is not `ok` carries no usable number. It is treated
 *   as *unknown*, never as zero — a missing correlation is not an absence of
 *   correlation.
 */

/** A cell of the correlation payload, narrowed to what this module reads. */
export interface CorrelationCell {
    row_asset_id: number;
    column_asset_id: number;
    /**
     * Scalar in practice, array in the type.
     *
     * The generated client disagrees with itself here: the Zod validator is
     * `z.union([z.number(), z.null()]).optional()`, while the emitted TypeScript
     * widens the same field to `number | (number | null)[] | null`. Since the
     * payload reaches this module through `riskOutput()`, which *parses* with
     * that Zod schema, the runtime value is always a scalar — but the compiler
     * has to be answered, and answering it by casting would hide the day the
     * risk API really does start returning windows.
     *
     * So the wide shape is accepted and narrowed explicitly, exactly as
     * `singleValue()` does elsewhere in the risk feature. It is deliberately
     * *not* imported from `$lib/risk/riskTypes`: that module pulls in
     * `generated.ts`, which is a build artifact absent from a fresh checkout,
     * and a unit test must not depend on something that has to be generated
     * first.
     */
    value?: number | readonly (number | null)[] | null;
    observations?: number;
    coverage?: number;
    status?: string | null;
}

/** First element of a widened scalar, or the scalar itself. */
function scalar(value: CorrelationCell['value']): number | null {
    if (Array.isArray(value)) return value[0] ?? null;
    return (value as number | null | undefined) ?? null;
}

/** Qualitative reading of |ρ|. `inverse` wins over magnitude: a strongly
 *  negative correlation is first of all a *compensating* one, and saying
 *  "high" about it would invert the advice. */
export type CorrelationBand = 'high' | 'moderate' | 'low' | 'inverse';

/** Fast symmetric lookup over the cell list. */
export interface CorrelationLookup {
    /** ρ for an unordered pair, or `null` when unknown/unusable. */
    get(a: number, b: number): number | null;
    /** The cell itself, for observations and coverage. */
    cell(a: number, b: number): CorrelationCell | undefined;
}

const BAND_HIGH = 0.7;
const BAND_LOW = 0.3;

/**
 * Band a correlation coefficient.
 *
 * `null` for an unknown value: the caller must say "unknown", not "low".
 * Conflating the two is how a missing history turns into a claim of
 * diversification that was never measured.
 */
export function correlationBand(value: number | null | undefined): CorrelationBand | null {
    if (value == null || !Number.isFinite(value)) return null;
    if (value < 0) return 'inverse';
    if (value > BAND_HIGH) return 'high';
    if (value >= BAND_LOW) return 'moderate';
    return 'low';
}

function pairKey(a: number, b: number): string {
    return a < b ? `${a}|${b}` : `${b}|${a}`;
}

/** Index the cells once, then answer pair queries in O(1) and symmetrically. */
export function buildLookup(cells: readonly CorrelationCell[] | null | undefined): CorrelationLookup {
    const byPair = new Map<string, CorrelationCell>();
    for (const cell of cells ?? []) {
        const key = pairKey(cell.row_asset_id, cell.column_asset_id);
        // The payload carries both (i,j) and (j,i). Prefer whichever one is
        // usable, so a half-populated symmetric pair still answers.
        const existing = byPair.get(key);
        if (existing && existing.status === 'ok' && cell.status !== 'ok') continue;
        byPair.set(key, cell);
    }
    return {
        cell: (a, b) => byPair.get(pairKey(a, b)),
        get: (a, b) => {
            const cell = byPair.get(pairKey(a, b));
            if (!cell || cell.status !== 'ok') return null;
            const value = scalar(cell.value);
            return value !== null && Number.isFinite(value) ? value : null;
        },
    };
}

/**
 * Distance used for clustering: `1 − |ρ|`.
 *
 * Both a strong positive and a strong negative correlation mean "these two move
 * together, one of them mirrored" — for the purpose of *grouping* they are the
 * same relationship, so the absolute value is the right measure.
 *
 * An unknown pair gets the maximum distance (1). It cannot be dropped: leaving
 * it out would silently pull two unrelated assets into the same block.
 */
export function correlationDistance(value: number | null): number {
    if (value == null) return 1;
    return 1 - Math.min(1, Math.abs(value));
}

/**
 * Reorder assets so that blocks of assets that move together become adjacent
 * squares in the matrix.
 *
 * Agglomerative clustering with average linkage. Average linkage rather than
 * single linkage because single linkage *chains*: two unrelated groups joined
 * through one intermediate asset would be drawn as a single block.
 *
 * The distances are computed **once**, into a flat `Float64Array` indexed by
 * position, and thereafter updated in place by the Lance–Williams rule. The
 * obvious implementation — recomputing each cluster-to-cluster average from the
 * `lookup` at every merge — costs on the order of a million keyed Map lookups,
 * each building a string key, at the hundred assets the API allows and D19
 * makes reachable on purpose. Same answer, and the hot path is an array read.
 *
 * The result is the leaf order of the dendrogram. Determinism matters — the
 * same matrix must always produce the same picture, or a reload looks like new
 * information — so ties are broken by the lower position, never by Map order.
 */
export function clusterOrder(assetIds: readonly number[], lookup: CorrelationLookup): number[] {
    const size = assetIds.length;
    if (size <= 2) return [...assetIds];

    // Symmetric distances, flattened: d(i,j) lives at i * size + j.
    const distances = new Float64Array(size * size);
    for (let i = 0; i < size; i += 1) {
        for (let j = i + 1; j < size; j += 1) {
            const distance = correlationDistance(lookup.get(assetIds[i], assetIds[j]));
            distances[i * size + j] = distance;
            distances[j * size + i] = distance;
        }
    }

    // Each live cluster keeps its slot; merging empties the right-hand one, so
    // the surviving slot index still addresses the distance matrix.
    const members: (number[] | null)[] = assetIds.map((id) => [id]);
    const weights = new Float64Array(size).fill(1);
    let live = size;

    while (live > 1) {
        let bestLeft = -1;
        let bestRight = -1;
        let best = Number.POSITIVE_INFINITY;
        for (let i = 0; i < size; i += 1) {
            if (members[i] === null) continue;
            for (let j = i + 1; j < size; j += 1) {
                if (members[j] === null) continue;
                const candidate = distances[i * size + j];
                if (candidate < best) {
                    best = candidate;
                    bestLeft = i;
                    bestRight = j;
                }
            }
        }
        if (bestLeft < 0) break;

        // Lance–Williams for average linkage: the merged cluster's distance to
        // every other is the size-weighted mean of its two parents'.
        const leftWeight = weights[bestLeft];
        const rightWeight = weights[bestRight];
        const total = leftWeight + rightWeight;
        for (let other = 0; other < size; other += 1) {
            if (members[other] === null || other === bestLeft || other === bestRight) continue;
            const merged = (leftWeight * distances[bestLeft * size + other] + rightWeight * distances[bestRight * size + other]) / total;
            distances[bestLeft * size + other] = merged;
            distances[other * size + bestLeft] = merged;
        }

        members[bestLeft] = [...(members[bestLeft] as number[]), ...(members[bestRight] as number[])];
        members[bestRight] = null;
        weights[bestLeft] = total;
        live -= 1;
    }

    // `live > 1` only if the search bailed, which it cannot with finite
    // distances; concatenating the survivors keeps the function total anyway.
    return members.filter((cluster): cluster is number[] => cluster !== null).flat();
}

/** One entry of the pair list. */
export interface CorrelationPair {
    rowAssetId: number;
    columnAssetId: number;
    value: number;
    band: CorrelationBand;
    /** ρ ≥ `NEAR_IDENTICAL`: two products bought for a single exposure. */
    nearIdentical: boolean;
}

/** Above this, two instruments are the same bet wearing two names. */
export const NEAR_IDENTICAL = 0.9;

export interface PairLists {
    /** Most correlated, descending. */
    correlated: CorrelationPair[];
    /** Negatively correlated, most negative first. Empty when nothing offsets. */
    offsetting: CorrelationPair[];
}

/**
 * The two lists that answer the question the matrix hides: *which pairs are
 * redundant, and which actually offset each other?*
 *
 * Only the lower triangle is walked — the matrix is symmetric, so visiting both
 * halves would list every pair twice — and the diagonal is skipped, because an
 * asset correlating with itself is not a finding.
 */
export function topPairs(assetIds: readonly number[], lookup: CorrelationLookup, limit = 5): PairLists {
    const pairs: CorrelationPair[] = [];
    for (let row = 0; row < assetIds.length; row += 1) {
        for (let column = 0; column < row; column += 1) {
            const value = lookup.get(assetIds[row], assetIds[column]);
            if (value == null) continue;
            const band = correlationBand(value);
            if (band == null) continue;
            pairs.push({
                rowAssetId: assetIds[row],
                columnAssetId: assetIds[column],
                value,
                band,
                nearIdentical: value >= NEAR_IDENTICAL,
            });
        }
    }

    const correlated = pairs
        .filter((pair) => pair.value > 0)
        .sort((left, right) => right.value - left.value || left.rowAssetId - right.rowAssetId)
        .slice(0, limit);
    const offsetting = pairs
        .filter((pair) => pair.value < 0)
        .sort((left, right) => left.value - right.value || left.rowAssetId - right.rowAssetId)
        .slice(0, limit);

    return {correlated, offsetting};
}

/** A heatmap point in ECharts order: `[columnIndex, rowIndex, value]`. */
export interface HeatmapPoint {
    value: [number, number, number | null];
    rowAssetId: number;
    columnAssetId: number;
    observations: number;
    coverage: number;
    status: string;
}

/**
 * Build the points to draw, keeping only the **strict lower triangle**.
 *
 * The diagonal is always ρ = 1, so it renders as the most saturated colour in
 * the whole matrix: the loudest row on the chart says that an asset correlates
 * with itself. The upper triangle is its mirror. Dropping both takes a 10-asset
 * matrix from 100 cells to 45 without losing a single fact.
 *
 * `order` is the asset order actually rendered, so indices are positions in
 * `order` — not in the payload's `asset_ids`.
 */
export function lowerTrianglePoints(order: readonly number[], lookup: CorrelationLookup): HeatmapPoint[] {
    const points: HeatmapPoint[] = [];
    for (let row = 0; row < order.length; row += 1) {
        for (let column = 0; column < row; column += 1) {
            const cell = lookup.cell(order[row], order[column]);
            // An absent cell is still a pair the user selected. Skipping it
            // would leave an unexplained gap in a grid whose axes come from
            // `asset_ids` and therefore still lists both assets; emitting it as
            // an unknown keeps the square, and its tooltip, on the chart.
            points.push({
                value: [column, row, lookup.get(order[row], order[column])],
                rowAssetId: order[row],
                columnAssetId: order[column],
                observations: cell?.observations ?? 0,
                coverage: cell?.coverage ?? 0,
                status: cell?.status ?? 'undefined',
            });
        }
    }
    return points;
}

/**
 * Above this many assets the matrix stops being readable — ECharts already
 * drops the in-cell numbers past 12, and nobody reads 400 squares — so the pair
 * list is promoted from a companion to the primary answer. The matrix stays:
 * taking away what the user was looking at is not an improvement.
 */
export const PAIR_LIST_THRESHOLD = 20;
