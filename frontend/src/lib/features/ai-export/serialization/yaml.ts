import {stringify} from 'yaml';

export type JsonSafePrimitive = null | boolean | number | string;
export type JsonSafeValue = JsonSafePrimitive | JsonSafeValue[] | {[key: string]: JsonSafeValue};

export class SafeSerializationError extends TypeError {
    constructor(path: string, reason: string) {
        super(`Cannot safely serialize value at ${path}: ${reason}`);
        this.name = 'SafeSerializationError';
    }
}

export function normalizeJsonSafeValue(value: unknown): JsonSafeValue {
    return normalizeValue(value, '$', new WeakSet<object>());
}

export function serializeYaml(value: unknown): string {
    const normalized = normalizeJsonSafeValue(value);

    return stringify(normalized, {
        aliasDuplicateObjects: false,
        blockQuote: 'literal',
        collectionStyle: 'block',
        directives: false,
        lineWidth: 0,
        minContentWidth: 0,
        sortMapEntries: true,
    });
}

function normalizeValue(value: unknown, path: string, activeObjects: WeakSet<object>): JsonSafeValue {
    if (value === null) return null;

    switch (typeof value) {
        case 'string':
        case 'boolean':
            return value;
        case 'number':
            if (!Number.isFinite(value)) throw new SafeSerializationError(path, 'numbers must be finite');
            return value;
        case 'undefined':
        case 'function':
        case 'symbol':
        case 'bigint':
            throw new SafeSerializationError(path, `${typeof value} values are not JSON-safe`);
        case 'object':
            return Array.isArray(value) ? normalizeArray(value, path, activeObjects) : normalizeObject(value, path, activeObjects);
        default:
            throw new SafeSerializationError(path, 'unsupported value type');
    }
}

function normalizeArray(value: unknown[], path: string, activeObjects: WeakSet<object>): JsonSafeValue[] {
    if (activeObjects.has(value)) throw new SafeSerializationError(path, 'cyclic reference detected');

    const descriptors = Object.getOwnPropertyDescriptors(value);
    const indexKeys: string[] = [];

    for (const key of Reflect.ownKeys(value)) {
        if (typeof key === 'symbol') throw new SafeSerializationError(path, 'symbol-keyed array properties are not JSON-safe');
        if (key === 'length') continue;

        const index = Number(key);
        if (!Number.isInteger(index) || index < 0 || index >= value.length || String(index) !== key) {
            throw new SafeSerializationError(path, `array property ${JSON.stringify(key)} is not a JSON array index`);
        }

        const descriptor = descriptors[key];
        if (!descriptor?.enumerable) throw new SafeSerializationError(arrayPath(path, index), 'non-enumerable array elements are not JSON-safe');
        if (!('value' in descriptor)) throw new SafeSerializationError(arrayPath(path, index), 'accessor array elements are not JSON-safe');
        indexKeys.push(key);
    }

    if (indexKeys.length !== value.length) throw new SafeSerializationError(path, 'sparse arrays are not JSON-safe');

    activeObjects.add(value);
    try {
        const normalized = new Array<JsonSafeValue>(value.length);
        for (let index = 0; index < value.length; index += 1) {
            const descriptor = descriptors[String(index)];
            if (!descriptor || !('value' in descriptor)) throw new SafeSerializationError(arrayPath(path, index), 'missing array element');
            normalized[index] = normalizeValue(descriptor.value, arrayPath(path, index), activeObjects);
        }
        return normalized;
    } finally {
        activeObjects.delete(value);
    }
}

function normalizeObject(value: object, path: string, activeObjects: WeakSet<object>): {[key: string]: JsonSafeValue} {
    if (activeObjects.has(value)) throw new SafeSerializationError(path, 'cyclic reference detected');

    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null) {
        throw new SafeSerializationError(path, 'only plain objects and arrays are JSON-safe');
    }

    const descriptors = Object.getOwnPropertyDescriptors(value);
    const keys: string[] = [];

    for (const key of Reflect.ownKeys(value)) {
        if (typeof key === 'symbol') throw new SafeSerializationError(path, 'symbol-keyed object properties are not JSON-safe');

        const descriptor = descriptors[key];
        if (!descriptor?.enumerable) throw new SafeSerializationError(objectPath(path, key), 'non-enumerable object properties are not JSON-safe');
        if (!('value' in descriptor)) throw new SafeSerializationError(objectPath(path, key), 'accessor object properties are not JSON-safe');
        keys.push(key);
    }

    keys.sort();
    activeObjects.add(value);
    try {
        const normalized = Object.create(null) as {[key: string]: JsonSafeValue};
        for (const key of keys) {
            const descriptor = descriptors[key];
            if (!descriptor || !('value' in descriptor)) throw new SafeSerializationError(objectPath(path, key), 'missing object property');
            Object.defineProperty(normalized, key, {
                configurable: true,
                enumerable: true,
                value: normalizeValue(descriptor.value, objectPath(path, key), activeObjects),
                writable: true,
            });
        }
        return normalized;
    } finally {
        activeObjects.delete(value);
    }
}

function arrayPath(path: string, index: number): string {
    return `${path}[${index}]`;
}

function objectPath(path: string, key: string): string {
    return `${path}[${JSON.stringify(key)}]`;
}
