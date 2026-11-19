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
 * Where the data comes from: two reads, neither of which writes, so neither can
 * trigger `notifyPortfolioMutation` and discard a risk answer in flight.
 * - the bulk read of the asset metadata (`GET /api/v1/assets?asset_ids=…`) gives
 *   each asset's type;
 * - the asset profile (plan 68, E5: `POST /api/v1/assets/profile/query`) gives its
 *   sectors and countries: one day, today, the voices `geography` and `sector`, the
 *   last step of each (I15). The old `classification_params` is no longer read: a
 *   correction written only in the profile, or an enricher's read, would never
 *   reach the matrix.
 * The country store is loaded first, so the area groups never flash as ISO codes.
 *
 * Nothing is computed here beyond reading what the backend stores: an asset
 * without a usable distribution maps to `null`, and a failed read yields empty
 * maps. The factory also publishes the read's `status` (RN-20): the matrix offers
 * its five orderings always, and an ordering it cannot use says why — still
 * reading, the read failed, or no asset has the data — so the reason is true.
 */
import {zodiosApi} from '$lib/api';
import {normalizeDistribution, type Distribution} from '$lib/features/assets/assetPayload';
import {todayIso} from '$lib/utils/dateOnly';
import {ensureCountriesLoaded} from '$lib/stores/reference/countryStore';
import {safeString} from '$lib/types/common';

/** The three maps the matrix reads, keyed by asset id. */
export interface MatrixMetadata {
    types: ReadonlyMap<number, string | null>;
    sectors: ReadonlyMap<number, Distribution | null>;
    regions: ReadonlyMap<number, Distribution | null>;
}

export const EMPTY_MATRIX_METADATA: MatrixMetadata = {types: new Map(), sectors: new Map(), regions: new Map()};

/** Where the read stands: in flight, failed (the maps are empty), or answered — the maps hold what the backend stores. */
export type MatrixMetadataStatus = 'loading' | 'ready' | 'failed';

/**
 * One row of the bulk metadata read, as this module reads it: the type. The
 * generated client types a scalar field as "a value or a list of values", so it is
 * read through `safeString` rather than trusted as a plain value.
 */
export interface MatrixMetadataRow {
    asset_id: number;
    asset_type?: unknown;
}

/** One item of the profile read, as this module reads it: the steps of each voice, or an error. */
export interface MatrixProfileItem {
    asset_id: number;
    voices?: Record<string, ReadonlyArray<{value?: unknown}>> | null;
    error?: string | null;
}

/** The voices of the profile the matrix groups by. */
const MATRIX_VOICES = ['geography', 'sector'];

/**
 * A map of the profile (`{key: weight}`, weights as Decimal strings), normalized,
 * or `null` when there is none, it is empty or emptied, or its weights are
 * unusable (`normalizeDistribution` throws on those).
 */
export function profileDistribution(value: unknown): Distribution | null {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    try {
        const distribution = normalizeDistribution(value as Record<string, string | number>);
        return Object.keys(distribution).length > 0 ? distribution : null;
    } catch {
        return null;
    }
}

/** The value of the last step of one voice of an item; undefined when the voice has no step. */
function lastValue(item: MatrixProfileItem | undefined, key: string): unknown {
    const steps = item?.voices?.[key];
    return steps && steps.length ? steps[steps.length - 1].value : undefined;
}

/**
 * The three maps from the two reads: the type from the rows, the sectors and
 * countries from the profile. Every asset the rows hold is in the three maps; one
 * with no profile, or with a voice emptied, maps to `null` there. A row the read
 * repeats keeps its last reading.
 */
export function matrixMetadataFromReads(rows: readonly MatrixMetadataRow[], profiles: readonly MatrixProfileItem[]): MatrixMetadata {
    const byAsset = new Map(profiles.filter((item) => !item.error).map((item) => [item.asset_id, item]));
    const types = new Map<number, string | null>();
    const sectors = new Map<number, Distribution | null>();
    const regions = new Map<number, Distribution | null>();
    for (const row of rows) {
        const item = byAsset.get(row.asset_id);
        types.set(row.asset_id, safeString(row.asset_type));
        sectors.set(row.asset_id, profileDistribution(lastValue(item, 'sector')));
        regions.set(row.asset_id, profileDistribution(lastValue(item, 'geography')));
    }
    return {types, sectors, regions};
}

/** Sorted, de-duplicated ids as a string: the identity of a set, so a new array with the same ids asks nothing. */
export function assetIdsKey(assetIds: readonly number[]): string {
    return [...new Set(assetIds)].sort((left, right) => left - right).join(',');
}

/** The profile items of a set of assets, today, the two maps; in requests of at most `MAX_BULK_ITEMS` (1000) items. */
async function readProfiles(assetIds: readonly number[]): Promise<MatrixProfileItem[]> {
    const ids = [...new Set(assetIds)].sort((left, right) => left - right);
    const today = todayIso();
    const items: MatrixProfileItem[] = [];
    for (let start = 0; start < ids.length; start += 1000) {
        const request = ids.slice(start, start + 1000).map((asset_id) => ({asset_id, date_range: {start: today}, keys: MATRIX_VOICES}));
        const response = await zodiosApi.query_profile_api_v1_assets_profile_query_post(request);
        items.push(...(response.items as MatrixProfileItem[]));
    }
    return items;
}

/** The two reads for a set of assets. No ids, no request. */
export async function loadMatrixMetadata(assetIds: readonly number[], language: string): Promise<MatrixMetadata> {
    if (assetIds.length === 0) return EMPTY_MATRIX_METADATA;
    await ensureCountriesLoaded(language);
    const [rows, profiles] = await Promise.all([zodiosApi.read_assets_bulk_api_v1_assets_get({queries: {asset_ids: [...assetIds]}}), readProfiles(assetIds)]);
    return matrixMetadataFromReads(rows, profiles);
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
    let status = $state<MatrixMetadataStatus>('ready');
    let request = 0;
    const idsKey = $derived(assetIdsKey(inputs().assetIds));
    const language = $derived(inputs().language);

    $effect(() => {
        const ids = idsKey ? idsKey.split(',').map(Number) : [];
        const lang = language;
        const current = ++request;
        if (ids.length === 0) {
            metadata = EMPTY_MATRIX_METADATA;
            status = 'ready';
            return;
        }
        status = 'loading';
        void (async () => {
            try {
                const next = await loadMatrixMetadata(ids, lang);
                if (current !== request) return;
                metadata = next;
                status = 'ready';
            } catch {
                if (current !== request) return;
                metadata = EMPTY_MATRIX_METADATA;
                status = 'failed';
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
        get status() {
            return status;
        },
    };
}
