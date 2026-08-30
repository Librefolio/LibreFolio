/**
 * geographyMapHelpers — pure unit tests (node env, no jsdom).
 *
 * These functions were extracted from GeographyMap.svelte precisely because the
 * component draws on an ECharts canvas that jsdom cannot host. Everything under
 * test here is arithmetic and string building, so no DOM is needed.
 *
 * Deliberately NOT asserted: anything ECharts draws, and any translated string —
 * `buildGeoLabel` receives its localized name through an injected `getInfo`, so
 * the values compared below are the ones the test itself supplies.
 */
import {describe, expect, it, vi} from 'vitest';
import {buildChoroplethData, buildGeoLabel, buildGeoNameMaps, centroidOf, choroplethMax, computeUnknownPct, type GeoLabelDeps} from './geographyMapHelpers';

describe('computeUnknownPct', () => {
    it('sums Unknown and Other as a percentage', () => {
        expect(computeUnknownPct({Unknown: 0.1, Other: 0.05, USA: 0.85})).toBe(15);
    });

    it('treats missing buckets as zero', () => {
        expect(computeUnknownPct({USA: 1})).toBe(0);
        expect(computeUnknownPct({})).toBe(0);
    });

    it('counts Other on its own', () => {
        expect(computeUnknownPct({Other: 0.25})).toBe(25);
    });

    it('rounds to one decimal', () => {
        // 0.12345 * 100 = 12.345 → 12.3
        expect(computeUnknownPct({Unknown: 0.12345})).toBe(12.3);
    });
});

describe('buildGeoNameMaps', () => {
    const geoJson = {
        features: [
            {properties: {name: 'United States', ISO_A3: 'USA'}},
            {properties: {name: 'Germany', ISO_A3: 'DEU'}},
            {properties: {name: 'NoCode'}}, // missing ISO_A3 → skipped
            {properties: {ISO_A3: 'XXX'}}, // missing name → skipped
        ],
    };

    it('builds both directions for complete features', () => {
        const {iso3ToGeoName, geoNameToIso3} = buildGeoNameMaps(geoJson);
        expect(iso3ToGeoName).toEqual({USA: 'United States', DEU: 'Germany'});
        expect(geoNameToIso3).toEqual({'United States': 'USA', Germany: 'DEU'});
    });

    it('skips features missing a name or an ISO_A3', () => {
        const {iso3ToGeoName} = buildGeoNameMaps(geoJson);
        expect(iso3ToGeoName.XXX).toBeUndefined();
        expect(Object.keys(iso3ToGeoName)).toHaveLength(2);
    });

    it('tolerates a missing/empty feature collection', () => {
        expect(buildGeoNameMaps(undefined)).toEqual({iso3ToGeoName: {}, geoNameToIso3: {}});
        expect(buildGeoNameMaps({})).toEqual({iso3ToGeoName: {}, geoNameToIso3: {}});
        expect(buildGeoNameMaps({features: []})).toEqual({iso3ToGeoName: {}, geoNameToIso3: {}});
    });

    it('tolerates null features and null properties', () => {
        const maps = buildGeoNameMaps({features: [null, {properties: null}, {properties: {name: 'Italy', ISO_A3: 'ITA'}}]});
        expect(maps.iso3ToGeoName).toEqual({ITA: 'Italy'});
    });
});

describe('buildChoroplethData', () => {
    const names = {USA: 'United States', DEU: 'Germany'};

    it('maps ISO codes to names and weights to 2-decimal percentages', () => {
        const points = buildChoroplethData({USA: 0.1234, DEU: 0.5}, names);
        expect(points).toEqual([
            {name: 'United States', value: 12.34},
            {name: 'Germany', value: 50},
        ]);
    });

    it('skips the unclassified buckets and non-positive weights', () => {
        const points = buildChoroplethData({USA: 0.5, Unknown: 0.2, Other: 0.1, ZERO: 0, NEG: -0.3}, names);
        expect(points.map((p) => p.name)).toEqual(['United States']);
    });

    it('falls back to the raw code when the ISO code is not in the name map', () => {
        const points = buildChoroplethData({FRA: 0.4}, names);
        expect(points).toEqual([{name: 'FRA', value: 40}]);
    });

    it('returns an empty array for empty data', () => {
        expect(buildChoroplethData({}, names)).toEqual([]);
    });
});

describe('choroplethMax', () => {
    it('returns the largest percentage present', () => {
        expect(
            choroplethMax([
                {name: 'a', value: 12},
                {name: 'b', value: 40},
                {name: 'c', value: 7},
            ]),
        ).toBe(40);
    });

    it('defaults to 100 for an empty set', () => {
        expect(choroplethMax([])).toBe(100);
    });
});

describe('centroidOf', () => {
    it('averages the client coordinates of all touches', () => {
        expect(
            centroidOf([
                {clientX: 100, clientY: 200},
                {clientX: 200, clientY: 400},
            ]),
        ).toEqual({x: 150, y: 300});
    });

    it('returns the single point unchanged for one touch', () => {
        expect(centroidOf([{clientX: 42, clientY: 7}])).toEqual({x: 42, y: 7});
    });
});

describe('buildGeoLabel', () => {
    /** Deps with a known USA info and a deterministic amount formatter. */
    function deps(over: Partial<GeoLabelDeps> = {}): GeoLabelDeps {
        return {
            geoNameToIso3: {'United States': 'USA', Germany: 'DEU'},
            amounts: {USA: 1234},
            currency: 'EUR',
            getInfo: (iso3) => (iso3 === 'USA' ? {name: 'Stati Uniti', flag_emoji: '🇺🇸'} : iso3 === 'DEU' ? {name: 'Germania', flag_emoji: ''} : {name: iso3, flag_emoji: ''}),
            formatAmount: (amt, cur) => `${cur} ${amt}`,
            ...over,
        };
    }

    it('shows flag, localized name, percentage and amount line for a positive value', () => {
        const label = buildGeoLabel({name: 'United States', value: 12.5}, deps());
        expect(label).toBe('🇺🇸 Stati Uniti: 12.5%\nEUR 1234');
    });

    it('omits the amount line when there is no positive amount', () => {
        const label = buildGeoLabel({name: 'United States', value: 12.5}, deps({amounts: {}}));
        expect(label).toBe('🇺🇸 Stati Uniti: 12.5%');
    });

    it('calls the amount formatter exactly once when an amount is shown', () => {
        const formatAmount = vi.fn((amt: number, cur: string) => `${cur} ${amt}`);
        buildGeoLabel({name: 'United States', value: 5}, deps({formatAmount}));
        expect(formatAmount).toHaveBeenCalledOnce();
        expect(formatAmount).toHaveBeenCalledWith(1234, 'EUR');
    });

    it('drops the flag prefix when info has no flag emoji', () => {
        const label = buildGeoLabel({name: 'Germany', value: 30}, deps({amounts: {}}));
        expect(label).toBe('Germania: 30%'); // DEU info carries a name but an empty flag
    });

    it('degrades to the raw name (no flag, no getInfo) for an unmapped feature', () => {
        const getInfo = vi.fn(() => ({name: 'should-not-be-used', flag_emoji: '🏳️'}));
        const label = buildGeoLabel({name: 'Atlantis', value: 5}, deps({getInfo}));
        expect(label).toBe('Atlantis: 5%');
        expect(getInfo).not.toHaveBeenCalled(); // no ISO code → never resolved
    });

    it('shows only the name (no percentage) when the value is null, NaN or non-positive', () => {
        const d = deps();
        expect(buildGeoLabel({name: 'United States', value: null}, d)).toBe('🇺🇸 Stati Uniti');
        expect(buildGeoLabel({name: 'United States', value: NaN}, d)).toBe('🇺🇸 Stati Uniti');
        expect(buildGeoLabel({name: 'United States', value: 0}, d)).toBe('🇺🇸 Stati Uniti');
    });

    it('falls back to the feature name when info carries no localized name', () => {
        const label = buildGeoLabel({name: 'United States', value: 5}, deps({getInfo: () => ({flag_emoji: '🇺🇸'}), amounts: {}}));
        expect(label).toBe('🇺🇸 United States: 5%');
    });
});
