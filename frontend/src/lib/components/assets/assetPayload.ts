/**
 * assetPayload — pure builders shared by the AssetModal create/edit save paths.
 *
 * Both `saveCreate` and `saveEdit` normalise the quote-base quantity the same way
 * and assemble `classification_params` from the same three inputs; only the
 * empty-case sentinel differs (create omits the field, edit sends `null`). Pulling
 * the two out makes those branches unit-testable and keeps the two save paths from
 * drifting apart.
 *
 * @module components/assets/assetPayload
 */

/** A distribution map: `{Technology: 0.4, Health: 0.6}` etc. */
export type Distribution = Record<string, number>;

export function normalizeDistribution(values: Record<string, string | number>): Distribution {
    return Object.fromEntries(
        Object.entries(values).map(([key, value]): [string, number] => {
            const weight = Number(value);
            if ((typeof value !== 'string' && typeof value !== 'number') || String(value).trim() === '' || !Number.isFinite(weight)) throw new Error('Invalid distribution weight.');
            return [key, weight];
        }),
    );
}

/** The classification payload sub-object, each part present only when non-empty. */
export interface ClassificationParams {
    short_description?: string;
    sector_area?: {distribution: Distribution};
    geographic_area?: {distribution: Distribution};
}

export interface ClassificationPatch {
    short_description?: string | null;
    sector_area?: {distribution: Distribution} | null;
    geographic_area?: {distribution: Distribution} | null;
}

export function sameDistribution(left: Distribution = {}, right: Distribution = {}): boolean {
    const keys = Object.keys(left);
    return keys.length === Object.keys(right).length && keys.every((key) => Object.hasOwn(right, key) && left[key] === right[key]);
}

/** Omission preserves untouched metadata; null expresses a deliberate clear. */
export function buildClassificationPatch(previous: ClassificationParams | undefined, current: ClassificationParams | undefined): ClassificationPatch | null | undefined {
    const patch: ClassificationPatch = {};
    if ((previous?.short_description ?? null) !== (current?.short_description ?? null)) patch.short_description = current?.short_description ?? null;
    if (!sameDistribution(previous?.sector_area?.distribution, current?.sector_area?.distribution)) patch.sector_area = current?.sector_area ?? null;
    if (!sameDistribution(previous?.geographic_area?.distribution, current?.geographic_area?.distribution)) patch.geographic_area = current?.geographic_area ?? null;
    if (Object.keys(patch).length === 0) return undefined;
    return current === undefined ? null : patch;
}

/**
 * The quote-base quantity sent to the API: at least 1. A falsy value (0, NaN) or a
 * non-positive number collapses to 1; any other value passes through unchanged.
 * (The integer-truncation rule is enforced separately at the input, via
 * `quoteBaseQuantityInvalid`; this is only the non-positive floor the save applies.)
 */
export function normalizeQuoteBaseQuantity(qbq: number): number {
    return !qbq || qbq <= 0 ? 1 : qbq;
}

/**
 * Assemble `classification_params` from the three editor inputs, including each
 * part only when it carries content. Returns `undefined` when nothing is set, so
 * the create path can omit the field entirely and the edit path can map it to
 * `null` with `?? null`.
 */
export function buildClassificationParams(shortDescription: string, sectorDistribution: Distribution, geographicDistribution: Distribution): ClassificationParams | undefined {
    const params: ClassificationParams = {};
    if (shortDescription) params.short_description = shortDescription;
    if (Object.keys(sectorDistribution).length > 0) params.sector_area = {distribution: sectorDistribution};
    if (Object.keys(geographicDistribution).length > 0) params.geographic_area = {distribution: geographicDistribution};
    return Object.keys(params).length > 0 ? params : undefined;
}
