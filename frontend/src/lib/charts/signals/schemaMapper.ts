import type {SignalParamDescriptor} from './ChartSignal';

interface JsonSchemaProperty {
    type?: unknown;
    title?: unknown;
    default?: unknown;
    enum?: unknown;
    minimum?: unknown;
    maximum?: unknown;
    multipleOf?: unknown;
    ['x-i18n-key']?: unknown;
    ['x-control-order']?: unknown;
    ['x-suffix']?: unknown;
    ['x-step']?: unknown;
    ['x-tooltip-key']?: unknown;
    ['x-affects-outputs']?: unknown;
}

interface JsonObjectSchema {
    type?: unknown;
    properties?: unknown;
    required?: unknown;
}

export class UnsupportedSignalSchemaError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'UnsupportedSignalSchemaError';
    }
}

function asFiniteNumber(value: unknown): number | undefined {
    return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function asString(value: unknown): string | undefined {
    return typeof value === 'string' && value.length > 0 ? value : undefined;
}

function readRequiredKeys(schema: JsonObjectSchema): Set<string> {
    if (schema.required === undefined) return new Set();
    if (!Array.isArray(schema.required) || schema.required.some((value) => typeof value !== 'string')) {
        throw new UnsupportedSignalSchemaError('Signal params schema has an invalid required list');
    }
    return new Set(schema.required);
}

function readProperties(schema: JsonObjectSchema): Record<string, JsonSchemaProperty> {
    if (schema.type !== 'object' || schema.properties === null || typeof schema.properties !== 'object' || Array.isArray(schema.properties)) {
        throw new UnsupportedSignalSchemaError('Signal params schema must be an object with properties');
    }
    return schema.properties as Record<string, JsonSchemaProperty>;
}

function readAffectedOutputs(key: string, value: unknown): string[] | undefined {
    if (value === undefined) return undefined;
    if (!Array.isArray(value) || value.length === 0 || value.some((item) => typeof item !== 'string' || item.length === 0)) {
        throw new UnsupportedSignalSchemaError(`Signal parameter '${key}' has invalid x-affects-outputs metadata`);
    }
    return value;
}

function mapPropertyType(key: string, property: JsonSchemaProperty): Pick<SignalParamDescriptor, 'type' | 'integer' | 'options'> {
    if (Array.isArray(property.enum)) {
        if (property.enum.length === 0 || property.enum.some((value) => typeof value !== 'string' && typeof value !== 'number')) {
            throw new UnsupportedSignalSchemaError(`Signal parameter '${key}' has an unsupported enum`);
        }
        return {
            type: 'select',
            options: property.enum.map((value) => ({
                value: String(value),
                label: String(value),
            })),
        };
    }

    switch (property.type) {
        case 'integer':
            return {type: 'number', integer: true};
        case 'number':
            return {type: 'number'};
        case 'boolean':
            return {type: 'boolean'};
        case 'string':
            return {type: 'string'};
        default:
            throw new UnsupportedSignalSchemaError(`Signal parameter '${key}' has unsupported type '${String(property.type)}'`);
    }
}

export function mapSignalParamsSchema(paramsSchema: Record<string, unknown>, defaultParams: Record<string, unknown> = {}): SignalParamDescriptor[] {
    const schema = paramsSchema as JsonObjectSchema;
    const properties = readProperties(schema);
    const requiredKeys = readRequiredKeys(schema);

    return Object.entries(properties)
        .map(([key, property], sourceIndex) => {
            const mappedType = mapPropertyType(key, property);
            const schemaDefault = Object.hasOwn(defaultParams, key) ? defaultParams[key] : property.default;
            const order = asFiniteNumber(property['x-control-order']) ?? sourceIndex;

            return {
                key,
                label: asString(property['x-i18n-key']) ?? asString(property.title) ?? key,
                default: schemaDefault,
                required: requiredKeys.has(key),
                min: asFiniteNumber(property.minimum),
                max: asFiniteNumber(property.maximum),
                step: asFiniteNumber(property['x-step']) ?? asFiniteNumber(property.multipleOf),
                suffix: asString(property['x-suffix']),
                tooltip: asString(property['x-tooltip-key']),
                affectsOutputs: readAffectedOutputs(key, property['x-affects-outputs']),
                order,
                ...mappedType,
            };
        })
        .sort((left, right) => left.order - right.order)
        .map(({order: _order, ...descriptor}) => descriptor);
}
