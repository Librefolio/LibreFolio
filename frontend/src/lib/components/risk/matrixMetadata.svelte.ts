/**
 * matrixMetadata — the inputs of the correlation matrix's type, sector and area
 * orderings, for any set of assets.
 *
 * The matrix (`CorrelationHeatmap`) can group its rows by type and by dominant
 * sector or area, but only when it is handed three maps. The Asset Global lab
 * built them inline (F-3b); the Dashboard's L2 matrix needs the same orderings
 * (K11), so the loading lives here, once, and both mount it. A copy in the
 * Dashboard would drift from this one the first time either is repaired.
 *
 * Where the data comes from: one bulk read of the asset metadata
 * (`GET /api/v1/assets?asset_ids=…`), which carries each asset's type and its
 * sector and country distributions. It is a GET: it cannot trigger
 * `notifyPortfolioMutation`, so it cannot discard a risk answer in flight. The
 * country store is loaded first, so the area groups never flash as ISO codes.
 *
 * Nothing is computed here beyond reading what the backend stores: an asset
 * without a usable distribution maps to `null`, and a failed read yields empty
 * maps — the matrix then simply offers fewer orderings.
 */
import {zodiosApi} from '$lib/api';
import {normalizeDistribution, type Distribution} from '$lib/components/assets/assetPayload';
import {ensureCountriesLoaded} from '$lib/stores/reference/countryStore';
import {safeScalar, safeString} from '$lib/types/common';

/** The three maps the matrix reads, keyed by asset id. */
export interface MatrixMetadata {
    types: ReadonlyMap<number, string | null>;
    sectors: ReadonlyMap<number, Distribution | null>;
    regions: ReadonlyMap<number, Distribution | null>;
}

export const EMPTY_MATRIX_METADATA: MatrixMetadata = {types: new Map(), sectors: new Map(), regions: new Map()};

/**
 * One row of the bulk metadata read, as this module reads it. The generated
 * client types a scalar field as "a value or a list of values", so both fields
 * are read through the `safe*` helpers rather than trusted as plain values.
 */
export interface MatrixMetadataRow {
    asset_id: number;
    asset_type?: unknown;
    classification_params?: unknown;
}

/**
 * A stored distribution (`{distribution: {key: weight}}`), normalized, or `null`
 * when there is none, it is empty, or its weights are unusable
 * (`normalizeDistribution` throws on those).
 */
export function distributionOf(area: unknown): Distribution | null {
    const scalar = safeScalar(area as {distribution?: Record<string, string | number>} | null);
    if (!scalar?.distribution) return null;
    try {
        const distribution = normalizeDistribution(scalar.distribution);
        return Object.keys(distribution).length > 0 ? distribution : null;
    } catch {
        return null;
    }
}

/** The three maps from the rows of one bulk read. A row the read repeats keeps its last reading. */
export function matrixMetadataFromRows(rows: readonly MatrixMetadataRow[]): MatrixMetadata {
    const types = new Map<number, string | null>();
    const sectors = new Map<number, Distribution | null>();
    const regions = new Map<number, Distribution | null>();
    for (const row of rows) {
        const classification = safeScalar(row.classification_params as {sector_area?: unknown; geographic_area?: unknown} | null);
        types.set(row.asset_id, safeString(row.asset_type));
        sectors.set(row.asset_id, distributionOf(classification?.sector_area));
        regions.set(row.asset_id, distributionOf(classification?.geographic_area));
    }
    return {types, sectors, regions};
}

/** Sorted, de-duplicated ids as a string: the identity of a set, so a new array with the same ids asks nothing. */
export function assetIdsKey(assetIds: readonly number[]): string {
    return [...new Set(assetIds)].sort((left, right) => left - right).join(',');
}

/** One read for a set of assets. No ids, no request. */
export async function loadMatrixMetadata(assetIds: readonly number[], language: string): Promise<MatrixMetadata> {
    if (assetIds.length === 0) return EMPTY_MATRIX_METADATA;
    await ensureCountriesLoaded(language);
    const rows = await zodiosApi.read_assets_bulk_api_v1_assets_get({queries: {asset_ids: [...assetIds]}});
    return matrixMetadataFromRows(rows);
}

/**
 * The three maps for a component, kept current as its assets or its language
 * change. Call it during component initialisation, like any rune-based factory:
 *
 *   const metadata = createMatrixMetadata(() => ({assetIds, language: $currentLanguage}));
 *   <CorrelationHeatmap … assetTypes={metadata.types} assetSectors={metadata.sectors} assetRegions={metadata.regions} />
 *
 * The ids are compared as a set (`assetIdsKey`): a caller that rebuilds the same
 * array on every change of something else must not re-read the metadata — the
 * F-2d lesson. An answer overtaken by a newer request is dropped.
 */
export function createMatrixMetadata(inputs: () => {assetIds: readonly number[]; language: string}) {
    let metadata = $state<MatrixMetadata>(EMPTY_MATRIX_METADATA);
    let request = 0;
    const idsKey = $derived(assetIdsKey(inputs().assetIds));
    const language = $derived(inputs().language);

    $effect(() => {
        const ids = idsKey ? idsKey.split(',').map(Number) : [];
        const lang = language;
        const current = ++request;
        if (ids.length === 0) {
            metadata = EMPTY_MATRIX_METADATA;
            return;
        }
        void (async () => {
            try {
                const next = await loadMatrixMetadata(ids, lang);
                if (current !== request) return;
                metadata = next;
            } catch {
                if (current !== request) return;
                metadata = EMPTY_MATRIX_METADATA;
            }
        })();
    });

    return {
        get types() {
            return metadata.types;
        },
        get sectors() {
            return metadata.sectors;
        },
        get regions() {
            return metadata.regions;
        },
    };
}
