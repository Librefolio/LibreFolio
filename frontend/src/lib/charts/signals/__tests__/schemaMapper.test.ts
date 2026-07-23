import {describe, expect, it} from 'vitest';

import {mapSignalParamsSchema, UnsupportedSignalSchemaError} from '../schemaMapper';

describe('signal params JSON Schema mapper', () => {
    it('maps number, integer, boolean, enum, metadata, and control order', () => {
        const descriptors = mapSignalParamsSchema(
            {
                type: 'object',
                required: ['period', 'enabled'],
                properties: {
                    mode: {
                        type: 'string',
                        enum: ['fast', 'slow'],
                        default: 'fast',
                        'x-control-order': 3,
                    },
                    enabled: {
                        type: 'boolean',
                        default: true,
                        'x-control-order': 2,
                    },
                    period: {
                        type: 'integer',
                        default: 14,
                        minimum: 2,
                        maximum: 500,
                        'x-step': 1,
                        'x-suffix': 'days',
                        'x-i18n-key': 'chartSettings.params.period',
                        'x-tooltip-key': 'chartSettings.tooltips.period',
                        'x-control-order': 1,
                    },
                    multiplier: {
                        type: 'number',
                        default: 2,
                        multipleOf: 0.1,
                        'x-control-order': 4,
                    },
                },
            },
            {period: 20},
        );

        expect(descriptors.map((descriptor) => descriptor.key)).toEqual(['period', 'enabled', 'mode', 'multiplier']);
        expect(descriptors[0]).toMatchObject({
            type: 'number',
            integer: true,
            default: 20,
            required: true,
            min: 2,
            max: 500,
            step: 1,
            suffix: 'days',
            label: 'chartSettings.params.period',
            tooltip: 'chartSettings.tooltips.period',
        });
        expect(descriptors[1]).toMatchObject({
            type: 'boolean',
            required: true,
        });
        expect(descriptors[2]).toMatchObject({
            type: 'select',
            options: [
                {value: 'fast', label: 'fast'},
                {value: 'slow', label: 'slow'},
            ],
        });
        expect(descriptors[3]).toMatchObject({
            type: 'number',
            step: 0.1,
        });
    });

    it('rejects unsupported nested parameters explicitly', () => {
        expect(() =>
            mapSignalParamsSchema({
                type: 'object',
                properties: {
                    windows: {
                        type: 'array',
                    },
                },
            }),
        ).toThrow(UnsupportedSignalSchemaError);
    });
});
