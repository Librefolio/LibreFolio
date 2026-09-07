/**
 * Pure helpers extracted from GeographyMap.svelte.
 *
 * GeographyMap renders a choropleth on an ECharts canvas, which jsdom does not
 * provide — so the component itself cannot be exercised in a unit test. But the
 * *interesting* part of it is arithmetic and string building that never touches
 * the canvas: the ISO-A3 ↔ GeoJSON name mapping, the weight→percentage
 * conversion (with its skip rules), the unclassified rollup, the touch centroid,
 * and the country label text. Kept here as free functions, each is tested
 * directly in a plain node environment; the component keeps only the wiring.
 *
 * @module charts/geographyMapHelpers
 */

/** Both directions of the ISO-A3 ↔ GeoJSON feature-name mapping. */
export interface GeoNameMaps {
    iso3ToGeoName: Record<string, string>;
    geoNameToIso3: Record<string, string>;
}

/** The subset of the world GeoJSON these helpers read. */
export interface GeoFeatureCollection {
    features?: Array<{properties?: {name?: string; ISO_A3?: string} | null} | null>;
}

/** One ECharts map data point: a GeoJSON feature name and its percentage value. */
export interface ChoroplethPoint {
    name: string;
    value: number;
}

/**
 * Percentage of value with no geographic classification. "Unknown" and "Other"
 * are both treated as unclassified ("Other" is a provider placeholder for "rest
 * of world"). Rounded to one decimal, matching the label shown under the map.
 */
export function computeUnknownPct(data: Record<string, number>): number {
    return +(((data['Unknown'] ?? 0) + (data['Other'] ?? 0)) * 100).toFixed(1);
}

/**
 * Build the ISO-A3 ↔ feature-name maps from a loaded world GeoJSON. Features
 * missing either a `name` or an `ISO_A3` property are skipped (both are needed
 * to round-trip a code to a drawable region and back).
 */
export function buildGeoNameMaps(geoJson: GeoFeatureCollection | null | undefined): GeoNameMaps {
    const iso3ToGeoName: Record<string, string> = {};
    const geoNameToIso3: Record<string, string> = {};
    for (const feature of geoJson?.features ?? []) {
        const name = feature?.properties?.name ?? '';
        const iso3 = feature?.properties?.ISO_A3 ?? '';
        if (name && iso3) {
            iso3ToGeoName[iso3] = name;
            geoNameToIso3[name] = iso3;
        }
    }
    return {iso3ToGeoName, geoNameToIso3};
}

/**
 * Convert an ISO-A3 → weight(0-1) record into ECharts map points. Skips the
 * unclassified buckets ("Unknown"/"Other") and any non-positive weight; weight
 * becomes a percentage rounded to two decimals. An ISO code absent from the
 * name map falls back to the raw code as its display name.
 */
export function buildChoroplethData(data: Record<string, number>, iso3ToGeoName: Record<string, string>): ChoroplethPoint[] {
    const points: ChoroplethPoint[] = [];
    for (const [code, weight] of Object.entries(data)) {
        if (weight <= 0 || code === 'Unknown' || code === 'Other') continue;
        const countryName = iso3ToGeoName[code] ?? code;
        points.push({name: countryName, value: +(weight * 100).toFixed(2)});
    }
    return points;
}

/**
 * Upper bound for the visualMap: the largest percentage present, or 100 when
 * there is no data (so an empty map still shows a full 0–100% legend).
 */
export function choroplethMax(points: ChoroplethPoint[]): number {
    return points.length > 0 ? Math.max(...points.map((d) => d.value)) : 100;
}

/** A point with client coordinates — the shape a `Touch` already satisfies. */
export interface PointerLike {
    clientX: number;
    clientY: number;
}

/**
 * Arithmetic mean of a set of touch points — the reference centroid the
 * two-finger pan gesture tracks between moves.
 */
export function centroidOf(touches: ArrayLike<PointerLike>): {x: number; y: number} {
    let x = 0;
    let y = 0;
    for (let i = 0; i < touches.length; i++) {
        x += touches[i].clientX;
        y += touches[i].clientY;
    }
    return {x: x / touches.length, y: y / touches.length};
}

/** The country attributes the label needs (a subset of countryStore's info). */
export interface GeoLabelCountryInfo {
    name?: string;
    flag_emoji?: string;
}

/** Injected dependencies so the label builder stays pure and store-free. */
export interface GeoLabelDeps {
    geoNameToIso3: Record<string, string>;
    amounts: Record<string, number>;
    currency: string;
    getInfo: (iso3: string) => GeoLabelCountryInfo | null;
    formatAmount: (amt: number, currency: string) => string;
}

/** The bits of an ECharts label callback param this builder consumes. */
export interface GeoLabelParams {
    name: string;
    value?: number | null;
}

/**
 * Build the fixed country label, e.g. `"🇺🇸 United States: 12.5%\n$1,234"`.
 *
 * The flag and localized name come from `getInfo(iso3)`; when the feature name
 * has no ISO code, or info is missing, it degrades to the raw name with no flag.
 * The amount line is appended only for a positive value *and* a positive known
 * amount for that country. Pure once its deps are injected.
 */
export function buildGeoLabel(params: GeoLabelParams, deps: GeoLabelDeps): string {
    const iso3 = deps.geoNameToIso3[params.name] ?? '';
    const info = iso3 ? deps.getInfo(iso3) : null;
    const flag = info?.flag_emoji ?? '';
    const displayName = info?.name ?? params.name;
    const prefix = flag ? `${flag} ` : '';
    if (params.value != null && !isNaN(params.value) && params.value > 0) {
        const absAmt = iso3 ? deps.amounts[iso3] : undefined;
        const amtLine = absAmt != null && absAmt > 0 ? `\n${deps.formatAmount(absAmt, deps.currency)}` : '';
        return `${prefix}${displayName}: ${params.value}%${amtLine}`;
    }
    return `${prefix}${displayName}`;
}
