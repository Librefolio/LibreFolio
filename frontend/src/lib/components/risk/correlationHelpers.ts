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

/** Qualitative reading of ρ, with symmetric thresholds. `inverse` needs a
 *  coefficient at or below −0.3: calling −0.01 "compensating" told the reader
 *  two unrelated assets offset each other (F-3b, V8). Between −0.3 and +0.3 a
 *  pair is `low` whatever its sign. */
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
    if (value <= -BAND_LOW) return 'inverse';
    if (value > BAND_HIGH) return 'high';
    if (value >= BAND_LOW) return 'moderate';
    return 'low';
}

/** One key per unordered pair: the list and the matrix name the same pair in opposite orders. */
export function pairKey(a: number, b: number): string {
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

/**
 * Emoji *as emoji*, and the invisible characters that glue them together: glyphs that
 * render as emoji by default, text pictographs forced to emoji by U+FE0F, flags, skin
 * tones, keycaps, ZWJ sequences and tag sequences. Text symbols that merely *can* be
 * emoji — `®`, `©`, `™`, a bare `☀` — are kept: they are part of names such as
 * `SPDR® S&P 500®`, and the canvas measures them like any other glyph.
 */
const NAME_DECORATION = /\p{Extended_Pictographic}\uFE0F|[\p{Emoji_Presentation}\p{Regional_Indicator}\p{Emoji_Modifier}\p{Variation_Selector}\u200D\u20E3\u{E0020}-\u{E007F}]/gu;

/**
 * The name without its emoji, for the two places that must compare or measure it.
 *
 * Sorting: flags and markers typed into a name (`🇪🇺👑 Amundi…`, `Btp… 🇮🇹`) sort
 * before every letter. Drawing: the heatmap's canvas mis-measures emoji, so a
 * decorated axis label was placed as if it were shorter and landed on the cells.
 * Everywhere else — tooltips, lists, chips — the name keeps its emoji. A name
 * made of emoji alone is kept whole rather than turned into an empty string.
 */
export function plainName(name: string): string {
    return name.replace(NAME_DECORATION, '').replace(/\s+/g, ' ').trim() || name;
}

/**
 * Asset ids in the order of the names the reader sees, ties broken by id.
 *
 * The matrix's "by name" button used to keep the payload order. That stopped being
 * alphabetical the day request ids were canonicalised ascending so the cache key
 * would be stable, and from then on the button said one thing and did another —
 * it ordered by id. Sorting here keeps the promise the label makes, whatever order
 * the API returns. `locale` is optional so tests can pin it; the app passes none.
 * Emoji are ignored (`plainName`), or every decorated name files ahead of every
 * plain one.
 */
export function nameOrder(assetIds: readonly number[], nameOf: (assetId: number) => string, locale?: string): number[] {
    const compare = nameComparator(locale);
    return [...assetIds].sort((left, right) => compare(nameOf(left), nameOf(right)) || left - right);
}

/**
 * The comparison behind `nameOrder`, for a caller that sorts rows rather than ids —
 * the loss table of Asset Global sorts its "Asset" column with it, so the table and
 * the matrix's "by name" button can never disagree. Ties are the caller's to break.
 */
export function nameComparator(locale?: string): (left: string, right: string) => number {
    const collator = new Intl.Collator(locale, {sensitivity: 'base', numeric: true});
    return (left, right) => collator.compare(plainName(left), plainName(right));
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
    /** Pairs in the `high` band, most correlated first. */
    correlated: CorrelationPair[];
    /** Pairs in the `inverse` band, most negative first. Empty when nothing offsets. */
    offsetting: CorrelationPair[];
}

/**
 * The two rankings that answer the question the matrix hides: *which pairs are
 * redundant, and which actually offset each other?*
 *
 * Only pairs that clear a band enter: `high` (ρ > 0.7) for the first ranking,
 * `inverse` (ρ ≤ −0.3) for the second. The rankings used to take every positive
 * and every negative coefficient, so a 0.55 was listed as "most similar" and a
 * −0.01 as "offsetting" — titles the numbers did not support (F-3b, V8).
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
        .filter((pair) => pair.band === 'high')
        .sort((left, right) => right.value - left.value || left.rowAssetId - right.rowAssetId)
        .slice(0, limit);
    const offsetting = pairs
        .filter((pair) => pair.band === 'inverse')
        .sort((left, right) => left.value - right.value || left.rowAssetId - right.rowAssetId)
        .slice(0, limit);

    return {correlated, offsetting};
}

/**
 * Asset ids grouped by asset type, in the app's menu order, then by name.
 *
 * Types missing from `typeRank` — or assets without a type — go last, together,
 * so an unclassified asset never splits a family. The menu order is passed in
 * rather than imported, which keeps this module free of the taxonomy.
 */
export function typeOrder(assetIds: readonly number[], typeOf: (assetId: number) => string | null | undefined, nameOf: (assetId: number) => string, typeRank: readonly string[], locale?: string): number[] {
    const rank = (assetId: number): number => {
        const index = typeRank.indexOf(typeOf(assetId) ?? '');
        return index < 0 ? typeRank.length : index;
    };
    const byName = new Map(nameOrder(assetIds, nameOf, locale).map((assetId, position) => [assetId, position]));
    return [...assetIds].sort((left, right) => rank(left) - rank(right) || (byName.get(left) ?? 0) - (byName.get(right) ?? 0));
}

/** The share a sector or a country must reach to name an asset's group; below it the asset is diversified. */
export const DOMINANT_SHARE = 0.5;

/** The backend's catch-all key, in sector and country distributions alike. */
export const OTHER_EXPOSURE = 'Other';

/** An asset's group for the sector and area orderings: see `dominantExposure`. */
export interface ExposureGroup {
    /** A named sector or country; `null` when diversified; `OTHER_EXPOSURE` when only the catch-all is known. */
    key: string | null;
    /** Weight of `key` among the classified entries (the catch-all left out); 1 for the catch-all fallback. */
    share: number;
}

/**
 * Where a distribution puts most of its weight — the catch-all left out.
 *
 * "Other" says nothing about an asset, so it never names a group (the developer,
 * F-3b): the entries are weighed among themselves without it, and one reaching
 * `DOMINANT_SHARE` of that classified weight names the group; when none does the
 * asset is diversified. Only an asset known solely through "Other" falls back to
 * it, as the last named group. `null` when there is no usable distribution at all
 * (unclassified). Empty keys, non-finite and non-positive weights are ignored; a
 * tie on the largest weight goes to the key that sorts first, so the group does
 * not depend on the order the entries arrive in.
 */
export function dominantExposure(distribution: Readonly<Record<string, number>> | null | undefined, threshold = DOMINANT_SHARE): ExposureGroup | null {
    if (!distribution) return null;
    let classified = 0;
    let sawOther = false;
    let bestKey: string | null = null;
    let best = 0;
    for (const [key, weight] of Object.entries(distribution)) {
        // An empty key names nothing: it would open a group without a label.
        if (key === '' || !Number.isFinite(weight) || weight <= 0) continue;
        if (key === OTHER_EXPOSURE) {
            sawOther = true;
            continue;
        }
        classified += weight;
        if (weight > best || (weight === best && bestKey !== null && key < bestKey)) {
            best = weight;
            bestKey = key;
        }
    }
    if (bestKey === null) return sawOther ? {key: OTHER_EXPOSURE, share: 1} : null;
    const share = best / classified;
    return share >= threshold ? {key: bestKey, share} : {key: null, share};
}

/**
 * Asset ids grouped by their dominant sector or country (`dominantExposure`).
 *
 * Four tiers: named groups, sorted by `groupLabel` (the name the reader sees),
 * with the most concentrated asset leading each; then diversified assets; then
 * those known only through "Other", the final fallback; then unclassified ones —
 * the last three by name. It is an ordering, not a classification: a world fund
 * at 70% United States sits with the American assets because that is where most
 * of its weight is, and the tooltip says so.
 */
export function exposureOrder(assetIds: readonly number[], exposureOf: (assetId: number) => ExposureGroup | null, nameOf: (assetId: number) => string, groupLabel: (key: string) => string, locale?: string): number[] {
    const collator = new Intl.Collator(locale, {sensitivity: 'base', numeric: true});
    const byName = new Map(nameOrder(assetIds, nameOf, locale).map((assetId, position) => [assetId, position]));
    const tier = (group: ExposureGroup | null): number => (group === null ? 3 : group.key === OTHER_EXPOSURE ? 2 : group.key === null ? 1 : 0);
    return [...assetIds].sort((left, right) => {
        const a = exposureOf(left);
        const b = exposureOf(right);
        const byTier = tier(a) - tier(b);
        if (byTier !== 0) return byTier;
        // Same tier: groups are compared only among named ones, decided by the tier
        // itself. Testing the keys for truthiness instead let an empty key sit in the
        // named tier yet skip this comparison, which made the order depend on the
        // input (test-author, F-3b).
        if (tier(a) === 0 && a !== null && b !== null && a.key !== null && b.key !== null) {
            const byGroup = collator.compare(plainName(groupLabel(a.key)), plainName(groupLabel(b.key)));
            if (byGroup !== 0) return byGroup;
            if (a.share !== b.share) return b.share - a.share;
        }
        return (byName.get(left) ?? 0) - (byName.get(right) ?? 0);
    });
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

/** Cell bounds, in CSS pixels. Below the minimum a value no longer fits; above the maximum a small matrix turns into posters. */
export const HEATMAP_CELL = {minWidth: 44, maxWidth: 88, minHeight: 34, maxHeight: 52, aspect: 0.7} as const;

/** Geometry of the heatmap canvas. */
export interface HeatmapLayout {
    width: number;
    height: number;
    cellWidth: number;
    cellHeight: number;
    grid: {left: number; right: number; top: number; bottom: number};
}

/**
 * Size the chart from its content instead of squeezing the content into the chart.
 *
 * The chart used to take the card's width and a fixed height, so a longer
 * selection shrank the cells and a longer name had nowhere to go. Here cells keep
 * a readable minimum: when the card is too narrow for them the chart becomes
 * wider than the card, which then scrolls sideways. When the card is wider than
 * needed, cells stop at a maximum.
 *
 * `yLabelWidth` and `xLabelWidth` are the measured widths of the widest labels,
 * already capped by the caller. Column labels are rotated by 45°: a label `w`
 * wide and `h` tall reaches `(w + h)·sin 45°` below the plot, and the first one
 * reaches as far to the left of its tick, which sits half a cell into the plot.
 */
export function heatmapLayout({columns, rows, availableWidth, yLabelWidth, xLabelWidth, labelHeight}: {columns: number; rows: number; availableWidth: number; yLabelWidth: number; xLabelWidth: number; labelHeight: number}): HeatmapLayout {
    const gap = 12;
    const top = 8;
    const right = 12;
    const diagonal = (xLabelWidth + labelHeight) * Math.SQRT1_2;
    const left = Math.ceil(Math.max(yLabelWidth, diagonal - HEATMAP_CELL.minWidth / 2)) + gap;
    const bottom = Math.ceil(diagonal) + gap;
    const fitted = columns > 0 ? Math.floor((availableWidth - left - right) / columns) : HEATMAP_CELL.minWidth;
    const cellWidth = Math.min(HEATMAP_CELL.maxWidth, Math.max(HEATMAP_CELL.minWidth, fitted));
    const cellHeight = Math.min(HEATMAP_CELL.maxHeight, Math.max(HEATMAP_CELL.minHeight, Math.round(cellWidth * HEATMAP_CELL.aspect)));
    return {
        width: left + columns * cellWidth + right,
        height: top + rows * cellHeight + bottom,
        cellWidth,
        cellHeight,
        grid: {left, right, top, bottom},
    };
}

/**
 * Above this many assets the matrix stops being readable — ECharts already
 * drops the in-cell numbers past 12, and nobody reads 400 squares — so the pair
 * list is promoted from a companion to the primary answer. The matrix stays:
 * taking away what the user was looking at is not an improvement.
 */
export const PAIR_LIST_THRESHOLD = 20;
