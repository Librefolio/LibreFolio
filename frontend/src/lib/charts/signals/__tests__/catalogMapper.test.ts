import {describe, expect, it} from 'vitest';

import {mapBackendSignalDefinition, mergeSignalDefinitions} from '../catalogMapper';
import type {BackendSignalCatalogDefinition} from '../backendTypes';
import type {SignalDefinition} from '../ChartSignal';
import {createSignalConfig} from '../registry';

function makeCatalog(signalCode: string, domains: Array<'asset' | 'fx'> = ['asset', 'fx']): BackendSignalCatalogDefinition {
    return {
        signal_code: signalCode,
        implementation_version: '1.0.0',
        category: 'trend',
        display_name_key: `chartSettings.signals.${signalCode.toLowerCase()}`,
        description_key: `chartSettings.signals.${signalCode.toLowerCase()}Desc`,
        semantic_id: `test.${signalCode.toLowerCase()}`,
        semantic_description: `Canonical description for ${signalCode}.`,
        icon: 'chart-spline',
        docs_path: `financial-theory/${signalCode.toLowerCase()}/`,
        params_schema: {
            type: 'object',
            properties: {
                period: {
                    type: 'integer',
                    default: 14,
                    minimum: 2,
                    maximum: 500,
                    'x-i18n-key': 'chartSettings.params.period',
                    'x-control-order': 1,
                    'x-step': 1,
                },
            },
        },
        default_params: {period: 14},
        input_requirements: {
            price_fields: ['close'],
            data_policy: 'strict_contiguous',
            minimum_coverage: 1,
        },
        output_specs: [
            {
                key: 'output',
                label_key: 'signals.output',
                semantic_id: `test.${signalCode.toLowerCase()}.output`,
                semantic_description: `Canonical output description for ${signalCode}.`,
                unit: 'price',
                axis: {key: 'price', role: 'price'},
                kind: 'line',
                aggregation_profile: 'last_with_range',
            },
        ],
        compatible_domains: domains,
    };
}

const localDefinition: SignalDefinition = {
    type: 'linear',
    displayName: 'Linear',
    displayNameKey: 'chartSettings.signals.linear',
    descriptionKey: 'chartSettings.signals.linearDesc',
    icon: '📈',
    category: 'benchmark',
    paramDescriptors: [],
    source: 'local',
    compatibleDomains: ['asset', 'fx'],
};

describe('signal catalog mapper', () => {
    it('preserves i18n, docs, domains, and schema-driven params', () => {
        const definition = mapBackendSignalDefinition(makeCatalog('STOCH_RSI'));

        expect(definition.type).toBe('stoch-rsi');
        expect(definition.displayNameKey).toBe('chartSettings.signals.stoch_rsi');
        expect(definition.docsPath).toBe('financial-theory/stoch_rsi/');
        expect(definition.indicatorGroup).toBe('trend');
        expect(definition.inputPriceFields).toEqual(['close']);
        expect(definition.compatibleDomains).toEqual(['asset', 'fx']);
        expect(definition.visualComponents).toHaveLength(1);
        expect(definition.visualComponents?.[0].fullyPartitioned).toBe(false);
        expect(definition.paramDescriptors[0]).toMatchObject({
            key: 'period',
            type: 'number',
            integer: true,
            default: 14,
        });
    });

    it('merges remote and local definitions for one domain', () => {
        const definitions = mergeSignalDefinitions([makeCatalog('EMA')], [localDefinition], 'fx');
        expect(definitions.map((definition) => definition.type)).toEqual(['ema', 'linear']);
    });

    it('maps risk as a supported backend indicator group', () => {
        const catalog = makeCatalog('RISK_ROLLING_RETURN', ['asset']);
        catalog.category = 'risk';

        expect(mapBackendSignalDefinition(catalog).indicatorGroup).toBe('risk');
    });

    it('rejects duplicate normalized codes', () => {
        expect(() => mergeSignalDefinitions([makeCatalog('LINEAR')], [localDefinition], 'asset')).toThrow("Duplicate signal definition 'linear'");
    });

    it('filters local definitions by domain compatibility', () => {
        const assetOnly: SignalDefinition = {
            ...localDefinition,
            compatibleDomains: ['asset'],
        };
        const definitions = mergeSignalDefinitions([makeCatalog('EMA')], [assetOnly], 'fx');
        expect(definitions.map((definition) => definition.type)).toEqual(['ema']);
    });

    it('creates a backend config without a signal-specific frontend class', () => {
        const definition = mapBackendSignalDefinition(makeCatalog('EMA'));
        const config = createSignalConfig(definition, 0);

        expect(config.signalType).toBe('ema');
        expect(config.params).toEqual({period: 14});
        expect(config.style).toMatchObject({
            lineWidth: 1,
            lineType: 'dotted',
            markerStart: null,
            markerEnd: null,
        });
    });

    it('marks backend line styles controlled by value regions', () => {
        const catalog = makeCatalog('RSI');
        catalog.output_specs[0].style = {
            color_role: 'accent',
            line_pattern: 'solid',
            width_delta: 1,
            opacity: 0.8,
        };
        catalog.output_specs[0].default_value_regions = [
            {
                key: 'neutral',
                label_key: 'signals.rsi.neutralRegion',
                semantic: 'neutral',
                lower: 30,
                upper: 70,
                line_style: {
                    pattern: 'dashed',
                    width_delta: 0,
                },
            },
        ];

        const definition = mapBackendSignalDefinition(catalog);
        expect(definition.visualComponents?.[0].style).toEqual({
            colorRole: 'accent',
            lineType: 'solid',
            lineWidthDelta: 1,
            opacity: 0.8,
            fillOpacity: 0.2,
        });
        expect(definition.visualComponents?.[0].fullyPartitioned).toBe(false);
        expect(definition.visualPartitions).toMatchObject([
            {
                key: 'output:neutral',
                semantic: 'neutral',
                style: {
                    lineType: 'dashed',
                },
            },
        ]);
    });

    it('marks an output fully partitioned only when regions cover the whole value domain', () => {
        const catalog = makeCatalog('RSI');
        catalog.output_specs[0].default_value_regions = [
            {
                key: 'low',
                label_key: 'signals.low',
                semantic: 'low',
                upper: 30,
                include_upper: false,
                line_style: {pattern: 'solid'},
            },
            {
                key: 'middle',
                label_key: 'signals.middle',
                semantic: 'middle',
                lower: 30,
                upper: 70,
                include_lower: true,
                include_upper: true,
                line_style: {pattern: 'dashed'},
            },
            {
                key: 'high',
                label_key: 'signals.high',
                semantic: 'high',
                lower: 70,
                include_lower: false,
                line_style: {pattern: 'solid'},
            },
        ];

        expect(mapBackendSignalDefinition(catalog).visualComponents?.[0].fullyPartitioned).toBe(true);

        catalog.output_specs[0].default_value_regions = catalog.output_specs[0].default_value_regions?.slice(1);
        expect(mapBackendSignalDefinition(catalog).visualComponents?.[0].fullyPartitioned).toBe(false);
    });

    it('maps AREA and plugin-owned aggregation/fill metadata generically', () => {
        const catalog = makeCatalog('RISK_DRAWDOWN', ['asset']);
        catalog.output_specs[0].kind = 'area';
        catalog.output_specs[0].aggregation_profile = 'min_with_range';
        catalog.output_specs[0].style = {
            color_role: 'negative',
            fill_opacity: 0.35,
        };

        expect(mapBackendSignalDefinition(catalog).visualComponents?.[0]).toMatchObject({
            kind: 'area',
            aggregationProfile: 'min_with_range',
            style: {
                colorRole: 'negative',
                fillOpacity: 0.35,
            },
        });
    });

    it('fails closed when a production output omits aggregation metadata', () => {
        const catalog = makeCatalog('EMA');
        delete catalog.output_specs[0].aggregation_profile;

        expect(() => mapBackendSignalDefinition(catalog)).toThrow('missing signal aggregation profile');
    });
});
