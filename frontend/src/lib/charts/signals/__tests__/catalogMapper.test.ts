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
                unit: 'price',
                axis: {key: 'price', role: 'price'},
                kind: 'line',
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
});
