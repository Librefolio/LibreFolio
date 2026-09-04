import {describe, expect, it} from 'vitest';

import {mapBackendSignalDefinition} from '../catalogMapper';
import type {BackendSignalCatalogDefinition} from '../backendTypes';

/**
 * `fullyPartitioned` decides whether a signal may be coloured by value band —
 * RSI's oversold/neutral/overbought stripes — or whether the whole line keeps
 * one colour. It says yes only when the declared regions tile the number line:
 * every value lands in a region, so no stretch of the line is left unstyled.
 *
 * The neighbouring file pins the happy path. This one pins the refusals, since
 * a wrong yes shows the user a chart with invisible segments.
 */

type Region = NonNullable<BackendSignalCatalogDefinition['output_specs'][number]['default_value_regions']>[number];

function catalogWithRegions(regions: Region[]): BackendSignalCatalogDefinition {
    return {
        signal_code: 'RSI',
        implementation_version: '1.0.0',
        category: 'momentum',
        display_name_key: 'chartSettings.signals.rsi',
        description_key: 'chartSettings.signals.rsiDesc',
        semantic_id: 'test.rsi',
        semantic_description: 'Canonical description for RSI.',
        icon: 'chart-spline',
        params_schema: {type: 'object', properties: {}},
        default_params: {},
        input_requirements: {price_fields: ['close'], data_policy: 'strict_contiguous', minimum_coverage: 1},
        output_specs: [
            {
                key: 'output',
                label_key: 'signals.output',
                semantic_id: 'test.rsi.output',
                semantic_description: 'Canonical output description.',
                unit: 'index',
                axis: {key: 'oscillator', role: 'independent'},
                kind: 'line',
                aggregation_profile: 'last_with_range',
                default_value_regions: regions,
            },
        ],
        compatible_domains: ['asset'],
    };
}

function isPartitioned(regions: Region[]): boolean {
    return mapBackendSignalDefinition(catalogWithRegions(regions)).visualComponents![0].fullyPartitioned;
}

/** A region with a solid style, so only its bounds are under test. */
function region(key: string, bounds: Partial<Region>): Region {
    return {key, label_key: `signals.${key}`, semantic: key, line_style: {pattern: 'solid'}, ...bounds};
}

describe('catalog mapper — value regions that tile the axis', () => {
    it('accepts two regions meeting at a shared, singly-owned boundary', () => {
        // (-∞, 50) and [50, +∞) — 50 belongs to exactly one of them.
        expect(isPartitioned([region('low', {upper: 50, include_upper: false}), region('high', {lower: 50, include_lower: true})])).toBe(true);
    });

    it('reads the regions in value order, not the order they arrived in', () => {
        expect(isPartitioned([region('high', {lower: 50, include_lower: true}), region('low', {upper: 50, include_upper: false})])).toBe(true);
    });

    it('refuses when a value between two regions belongs to neither', () => {
        // (-∞, 30) and (70, +∞): everything from 30 to 70 is unstyled.
        expect(isPartitioned([region('low', {upper: 30, include_upper: false}), region('high', {lower: 70, include_lower: false})])).toBe(false);
    });

    it('refuses when the single shared boundary itself belongs to neither', () => {
        // (-∞, 50) and (50, +∞) — a one-value hole is still a hole.
        expect(isPartitioned([region('low', {upper: 50, include_upper: false}), region('high', {lower: 50, include_lower: false})])).toBe(false);
    });

    it('refuses when the axis is left open in the middle', () => {
        // A region with no upper bound cannot be followed by another.
        expect(isPartitioned([region('low', {}), region('high', {lower: 50, include_lower: true})])).toBe(false);
    });

    it('refuses when two regions both start at negative infinity', () => {
        expect(isPartitioned([region('a', {upper: 30, include_upper: false}), region('b', {upper: 70, include_upper: false})])).toBe(false);
    });

    it('refuses when the lowest values fall outside every region', () => {
        // [0, 50) and [50, +∞) leaves anything below zero unstyled.
        expect(isPartitioned([region('low', {lower: 0, upper: 50, include_upper: false}), region('high', {lower: 50, include_lower: true})])).toBe(false);
    });

    it('refuses when the highest values fall outside every region', () => {
        expect(isPartitioned([region('low', {upper: 50, include_upper: false}), region('high', {lower: 50, upper: 100, include_lower: true})])).toBe(false);
    });

    it('refuses an output that declares no regions at all', () => {
        expect(isPartitioned([])).toBe(false);
    });

    it('accepts a boundary claimed by both neighbours', () => {
        // (-∞, 50] and [50, +∞): 50 is in two regions at once, so this is a
        // cover but not strictly a partition. Accepted today — pinned so the
        // looseness is visible rather than assumed.
        expect(isPartitioned([region('low', {upper: 50, include_upper: true}), region('high', {lower: 50, include_lower: true})])).toBe(true);
    });
});

describe('catalog mapper — regions the styling panel can offer', () => {
    it('offers only the regions that carry a style of their own', () => {
        // A region with no line_style has nothing for the user to edit, so it
        // is not listed — even though it still counts towards the tiling above.
        const partitions = mapBackendSignalDefinition(catalogWithRegions([region('low', {upper: 50, include_upper: false}), {key: 'high', label_key: 'signals.high', semantic: 'high', lower: 50, include_lower: true}])).visualPartitions;

        expect(partitions?.map((partition) => partition.key)).toEqual(['output:low']);
    });

    it('namespaces each region by its output, so two outputs cannot collide', () => {
        const partitions = mapBackendSignalDefinition(catalogWithRegions([region('oversold', {upper: 30, include_upper: false})])).visualPartitions;

        expect(partitions?.[0]).toMatchObject({key: 'output:oversold', labelKey: 'signals.oversold', semantic: 'oversold'});
    });
});

describe('catalog mapper — inputs and domains it refuses', () => {
    it('accepts every OHLCV field the chart can supply', () => {
        const catalog = catalogWithRegions([]);
        catalog.input_requirements.price_fields = ['open', 'high', 'low', 'close', 'volume'];

        expect(mapBackendSignalDefinition(catalog).inputPriceFields).toEqual(['open', 'high', 'low', 'close', 'volume']);
    });

    it('refuses a price field the chart cannot supply', () => {
        const catalog = catalogWithRegions([]);
        catalog.input_requirements.price_fields = ['close', 'open_interest'] as BackendSignalCatalogDefinition['input_requirements']['price_fields'];

        expect(() => mapBackendSignalDefinition(catalog)).toThrow(/open_interest/);
    });

    it('refuses a signal offered for a domain this frontend has no charts for', () => {
        // Failing loudly at the catalog boundary beats offering the signal and
        // breaking when someone picks it.
        const catalog = catalogWithRegions([]);
        catalog.compatible_domains = ['asset', 'portfolio'] as BackendSignalCatalogDefinition['compatible_domains'];

        expect(() => mapBackendSignalDefinition(catalog)).toThrow(/RSI/);
    });

    it('refuses a category with no place in the signal picker', () => {
        const catalog = catalogWithRegions([]);
        catalog.category = 'astrology' as BackendSignalCatalogDefinition['category'];

        expect(() => mapBackendSignalDefinition(catalog)).toThrow(/astrology/);
    });
});
