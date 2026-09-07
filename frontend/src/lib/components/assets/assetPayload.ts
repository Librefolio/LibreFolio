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

/** The classification payload sub-object, each part present only when non-empty. */
export interface ClassificationParams {
    short_description?: string;
    sector_area?: {distribution: Distribution};
    geographic_area?: {distribution: Distribution};
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
