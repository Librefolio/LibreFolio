const manifestKey = 'x-librefolio-tools';
const sourceKey = 'x-librefolio-tool-source';
const referencePrefix = '#/components/schemas/';
const identifierPattern = /^[A-Za-z][A-Za-z0-9_]*(?![\s\S])/u;
const scalarPattern = /^[^\uD800-\uDFFF]*(?![\s\S])/u;
const annotations = new Set([
    'title', 'description', 'default', 'examples', 'deprecated', 'readOnly', 'writeOnly',
]);
const supportedKeywords = new Set([
    ...annotations, '$ref', 'type', 'properties', 'required', 'additionalProperties',
    'items', 'oneOf', 'anyOf', 'allOf', 'discriminator', 'enum', 'const',
    'minLength', 'maxLength', 'pattern', 'format', 'minimum', 'maximum',
    'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf', 'minItems', 'maxItems',
]);
const stringFormats = new Set(['date', 'date-time', 'email', 'uri', 'uuid']);

export function invariant(condition, message) {
    if (!condition) throw new Error(`Tool codegen: ${message}`);
}

export function isRecord(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function assertJson(value, path = '$') {
    if (typeof value === 'string') {
        invariant(scalarPattern.test(value), `lone surrogate at ${path}`);
    } else if (typeof value === 'number') {
        invariant(Number.isFinite(value), `non-finite JSON number at ${path}`);
    } else if (Array.isArray(value)) {
        value.forEach((item, index) => assertJson(item, `${path}[${index}]`));
    } else if (isRecord(value)) {
        for (const [key, item] of Object.entries(value)) {
            invariant(scalarPattern.test(key), `lone surrogate in a key at ${path}`);
            assertJson(item, `${path}.${key}`);
        }
    } else {
        invariant(value === null || typeof value === 'boolean', `non-JSON value at ${path}`);
    }
}

export function componentName(reference, schemas) {
    invariant(typeof reference === 'string' && reference.startsWith(referencePrefix),
        `non-component reference ${JSON.stringify(reference)}`);
    const name = reference.slice(referencePrefix.length);
    invariant(identifierPattern.test(name) && Object.hasOwn(schemas, name),
        `missing or invalid component ${JSON.stringify(name)}`);
    return name;
}

export function schemaChildren(schema) {
    const children = [];
    if (isRecord(schema.properties)) children.push(...Object.values(schema.properties));
    if (isRecord(schema.additionalProperties)) children.push(schema.additionalProperties);
    if (isRecord(schema.items)) children.push(schema.items);
    for (const keyword of ['oneOf', 'anyOf', 'allOf']) {
        if (Array.isArray(schema[keyword])) children.push(...schema[keyword]);
    }
    return children;
}

export function walkSchemas(schema, visit) {
    visit(schema);
    for (const child of schemaChildren(schema)) walkSchemas(child, visit);
}

export function dereference(schema, schemas) {
    const visited = new Set();
    while (schema.$ref !== undefined) {
        const name = componentName(schema.$ref, schemas);
        invariant(!visited.has(name), `cyclic reference-only alias ${name}`);
        visited.add(name);
        schema = schemas[name];
    }
    return schema;
}

function integerBound(schema, keyword, path) {
    if (schema[keyword] === undefined) return;
    invariant(Number.isSafeInteger(schema[keyword]) && schema[keyword] >= 0,
        `unsupported ${keyword} at ${path}`);
}

function validateShape(schema, path) {
    invariant(isRecord(schema), `boolean or missing schema at ${path}`);
    for (const keyword of Object.keys(schema)) {
        invariant(supportedKeywords.has(keyword) || keyword.startsWith('x-'),
            `unsupported keyword ${keyword} at ${path}`);
    }
    if (schema.$ref !== undefined) {
        invariant(Object.keys(schema).every((key) =>
            key === '$ref' || annotations.has(key) || key.startsWith('x-')),
        `validation siblings on $ref require an explicit supported composition at ${path}`);
        return;
    }
    const compositions = ['oneOf', 'anyOf', 'allOf'].filter((key) => schema[key] !== undefined);
    if (compositions.length) {
        invariant(compositions.length === 1 && schema.type === undefined,
            `mixed composition/type at ${path}`);
        const keyword = compositions[0];
        invariant(Array.isArray(schema[keyword]) && schema[keyword].length > 0,
            `empty or invalid ${keyword} at ${path}`);
        invariant(keyword !== 'oneOf' || schema.discriminator !== undefined || schema.oneOf.length === 1,
            `oneOf without a discriminator cannot be widened to anyOf at ${path}`);
        invariant(Object.keys(schema).every((key) =>
            key === keyword || key === 'discriminator' || annotations.has(key) || key.startsWith('x-')),
        `unsupported constraint on ${keyword} at ${path}`);
        return;
    }
    invariant(['object', 'array', 'string', 'integer', 'number', 'boolean', 'null'].includes(schema.type),
        `untyped or unsupported schema at ${path}`);
    if (schema.type === 'object') {
        if (isRecord(schema.additionalProperties)) {
            invariant(schema.properties === undefined || Object.keys(schema.properties).length === 0,
                `mixed named properties and dictionary values at ${path}`);
            invariant(schema.required === undefined || schema.required.length === 0,
                `required dictionary keys at ${path}`);
        } else {
            invariant(schema.additionalProperties === false && isRecord(schema.properties),
                `objects must be extra-forbid models or typed dictionaries at ${path}`);
            invariant(!Object.hasOwn(schema.properties, '__proto__'),
                `a named __proto__ model field needs a concrete-object preservation strategy at ${path}`);
            const required = schema.required ?? [];
            invariant(Array.isArray(required) && new Set(required).size === required.length &&
                required.every((key) => typeof key === 'string' && Object.hasOwn(schema.properties, key)),
            `invalid required properties at ${path}`);
        }
    }
    if (schema.type === 'array') {
        invariant(isRecord(schema.items), `untyped array items at ${path}`);
        integerBound(schema, 'minItems', path);
        integerBound(schema, 'maxItems', path);
        invariant((schema.minItems ?? 0) <= (schema.maxItems ?? Infinity),
            `inverted array bounds at ${path}`);
    }
    if (schema.type === 'string') {
        integerBound(schema, 'minLength', path);
        integerBound(schema, 'maxLength', path);
        invariant((schema.minLength ?? 0) <= (schema.maxLength ?? Infinity),
            `inverted string bounds at ${path}`);
        if (schema.pattern !== undefined) {
            invariant(typeof schema.pattern === 'string', `invalid string pattern at ${path}`);
            portablePattern(schema.pattern);
        }
        invariant(schema.format === undefined || stringFormats.has(schema.format),
            `unsupported string format ${schema.format} at ${path}`);
    }
    for (const keyword of ['minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf']) {
        if (schema[keyword] === undefined) continue;
        invariant(['integer', 'number'].includes(schema.type) && Number.isFinite(schema[keyword]),
            `non-numeric ${keyword} at ${path}`);
        invariant(keyword !== 'multipleOf' || schema[keyword] > 0,
            `non-positive multipleOf at ${path}`);
    }
    for (const [keywords, type] of [
        [['minLength', 'maxLength', 'pattern', 'format'], 'string'],
        [['minItems', 'maxItems', 'items'], 'array'],
        [['properties', 'required', 'additionalProperties'], 'object'],
    ]) {
        invariant(schema.type === type || keywords.every((key) => schema[key] === undefined),
            `constraint for ${type} on ${schema.type} at ${path}`);
    }
    if (schema.const !== undefined || Object.hasOwn(schema, 'const')) {
        invariant(schema.enum === undefined || (Array.isArray(schema.enum) &&
            schema.enum.some((value) => Object.is(value, schema.const))), `inconsistent const/enum at ${path}`);
        schema.enum = [schema.const];
        delete schema.const;
    }
    if (schema.enum !== undefined) {
        invariant(Array.isArray(schema.enum) && schema.enum.length > 0,
            `empty enum at ${path}`);
        invariant(new Set(schema.enum.map((value) => JSON.stringify(value))).size === schema.enum.length,
            `duplicate enum member at ${path}`);
        for (const value of schema.enum) {
            const expected = schema.type === 'integer' ? 'number' : schema.type;
            invariant(expected === 'null' ? value === null : typeof value === expected &&
                ['string', 'number', 'boolean'].includes(expected), `enum type mismatch at ${path}`);
            if (schema.type === 'integer') invariant(Number.isInteger(value), `non-integer enum at ${path}`);
            if (typeof value === 'string') {
                invariant(unicodePattern(schema.minLength, schema.maxLength).test(value) &&
                    (schema.pattern === undefined || new RegExp(portablePattern(schema.pattern), 'u').test(value)),
                `enum and string constraints disagree at ${path}`);
                invariant(schema.format === undefined, `formatted enums are unsupported at ${path}`);
            }
            if (typeof value === 'number') {
                invariant((schema.minimum === undefined || value >= schema.minimum) &&
                    (schema.maximum === undefined || value <= schema.maximum) &&
                    (schema.exclusiveMinimum === undefined || value > schema.exclusiveMinimum) &&
                    (schema.exclusiveMaximum === undefined || value < schema.exclusiveMaximum) &&
                    schema.multipleOf === undefined, `enum and number constraints disagree at ${path}`);
            }
        }
    }
}

export function unicodePattern(minimum = 0, maximum) {
    // In Unicode mode, a valid surrogate pair is one code point and is outside this range.
    // The negative lookahead is an absolute end anchor, unlike JavaScript's dollar anchor.
    return new RegExp(`^[^\\uD800-\\uDFFF]{${minimum},${maximum ?? ''}}(?![\\s\\S])`, 'u');
}

export function portablePattern(pattern) {
    // Pydantic's default Rust engine uses Unicode decimal digits. JavaScript's \d does not.
    let converted = '';
    let inClass = false;
    for (let index = 0; index < pattern.length; index += 1) {
        const character = pattern[index];
        if (character === '\\') {
            const escaped = pattern[++index];
            invariant(escaped !== undefined, 'trailing pattern escape');
            invariant(!['w', 'W', 's', 'S', 'b', 'B', 'A', 'z', 'Z'].includes(escaped),
                `pattern escape \\${escaped} has no verified cross-engine mapping`);
            converted += escaped === 'd' ? '\\p{Decimal_Number}'
                : escaped === 'D' ? '\\P{Decimal_Number}' : `\\${escaped}`;
        } else {
            if (character === '[') inClass = true;
            if (character === ']') inClass = false;
            converted += character === '$' && !inClass ? '(?![\\s\\S])'
                : character === '.' && !inClass ? '[^\\n]' : character;
        }
    }
    invariant(!pattern.replaceAll('(?:', '(').includes('(?') && !pattern.includes('&&') &&
        !pattern.includes('--') && !pattern.includes('~~'),
    'pattern flags, lookarounds and class set operations need an explicit portable profile');
    // Non-capturing groups have identical semantics in the two engines.
    new RegExp(converted, 'u');
    return converted;
}

export function discriminatorOptions(schemas, rootNames) {
    const pending = [...rootNames];
    const seen = new Set();
    const options = new Map();
    while (pending.length) {
        const name = pending.pop();
        if (seen.has(name)) continue;
        seen.add(name);
        invariant(isRecord(schemas[name]), `missing schema ${name}`);
        walkSchemas(schemas[name], (schema) => {
            if (schema.$ref !== undefined) pending.push(componentName(schema.$ref, schemas));
            if (schema.discriminator === undefined) return;
            const {propertyName, mapping} = schema.discriminator;
            invariant(typeof propertyName === 'string' && isRecord(mapping) &&
                Array.isArray(schema.oneOf) && schema.oneOf.length > 1, 'invalid discriminator');
            const values = new Set();
            for (const branch of schema.oneOf) {
                invariant(isRecord(branch) && typeof branch.$ref === 'string',
                    'discriminator options must be named model references');
                const optionName = componentName(branch.$ref, schemas);
                const model = dereference(branch, schemas);
                const field = model.properties?.[propertyName];
                invariant(model.type === 'object' && model.additionalProperties === false &&
                    model.required?.includes(propertyName) && isRecord(field) && !Object.hasOwn(field, 'default'),
                `optional or non-strict discriminator ${optionName}.${propertyName}`);
                const tag = dereference(field, schemas);
                const literals = Object.hasOwn(tag, 'const') ? [tag.const] : tag.enum;
                invariant(!Object.hasOwn(tag, 'default') && Array.isArray(literals) &&
                    literals.length > 0 && literals.every((value) => typeof value === 'string'),
                `non-literal discriminator ${optionName}.${propertyName}`);
                for (const value of literals) {
                    invariant(!values.has(value) && mapping[value] === branch.$ref,
                        `duplicate or inconsistent discriminator mapping ${value}`);
                    values.add(value);
                }
                if (!options.has(optionName)) options.set(optionName, new Map());
                const fields = options.get(optionName);
                if (fields.has(propertyName)) {
                    invariant(JSON.stringify(fields.get(propertyName)) === JSON.stringify(literals),
                        `inconsistent discriminator declaration ${optionName}.${propertyName}`);
                }
                fields.set(propertyName, literals);
            }
            invariant(Object.keys(mapping).length === values.size, 'unused discriminator mapping');
        });
    }
    return options;
}

export function prepareToolDocument(document) {
    assertJson(document);
    invariant(document.openapi === '3.1.0' && isRecord(document.paths) &&
        Object.keys(document.paths).length === 0, 'expected a build-only OpenAPI 3.1 document with paths:{}');
    const manifest = document[manifestKey];
    const schemas = document.components?.schemas;
    invariant(isRecord(manifest) && manifest.manifestVersion === 1 &&
        Array.isArray(manifest.tools) && isRecord(manifest.transport) && isRecord(schemas),
    'missing or unsupported Tool manifest');
    const roots = new Set();
    const identities = new Set();
    for (const entry of manifest.tools) {
        invariant(isRecord(entry) && typeof entry.toolCode === 'string' &&
            typeof entry.contractVersion === 'string' && typeof entry.schemaFingerprint === 'string' &&
            /^[a-f0-9]{64}(?![\s\S])/u.test(entry.schemaFingerprint) &&
            typeof entry.componentKey === 'string' && entry.componentKey.length > 0 &&
            Number.isSafeInteger(entry.uiContractVersion) && entry.uiContractVersion > 0 &&
            Array.isArray(entry.operations) && entry.operations.length > 0 &&
            entry.operations.every((operation) => typeof operation === 'string') &&
            new Set(entry.operations).size === entry.operations.length, 'invalid Tool manifest entry');
        const identity = JSON.stringify([entry.toolCode, entry.contractVersion]);
        invariant(!identities.has(identity), `duplicate Tool identity ${identity}`);
        identities.add(identity);
        for (const [role, mode] of [['input', 'validation'], ['output', 'serialization']]) {
            const name = componentName(entry[role], schemas);
            invariant(schemas[name][sourceKey]?.mode === mode, `incorrect ${role} schema mode`);
            invariant(!roots.has(name), `shared Tool root ${name}`);
            roots.add(name);
        }
    }
    const roles = {catalog: 'serialization', computeRequest: 'validation',
        computeResponse: 'serialization', diagnostics: 'serialization'};
    invariant(Object.keys(manifest.transport).length === Object.keys(roles).length, 'unknown transport roles');
    for (const [role, mode] of Object.entries(roles)) {
        const entry = manifest.transport[role];
        invariant(isRecord(entry) && entry.mode === mode && typeof entry.model === 'string' &&
            identifierPattern.test(entry.model), `invalid transport role ${role}`);
        const name = componentName(entry.schema, schemas);
        invariant(schemas[name][sourceKey]?.mode === mode && !roots.has(name),
            `invalid transport root ${role}`);
        roots.add(name);
    }
    const adapted = structuredClone(document);
    const adaptedSchemas = adapted.components.schemas;
    for (const [name, schema] of Object.entries(adaptedSchemas)) {
        invariant(identifierPattern.test(name), `component name would be normalized by the generator: ${name}`);
        const source = schema[sourceKey];
        invariant(isRecord(source) && ['validation', 'serialization'].includes(source.mode) &&
            roots.has(componentName(source.root, adaptedSchemas)), `unowned component ${name}`);
        invariant(adaptedSchemas[componentName(source.root, adaptedSchemas)][sourceKey].mode === source.mode,
            `cross-mode component ${name}`);
        walkSchemas(schema, (node) => {
            validateShape(node, name);
            if (source.mode === 'serialization') delete node.default;
            if (node.$ref !== undefined) {
                const target = adaptedSchemas[componentName(node.$ref, adaptedSchemas)];
                invariant(target[sourceKey]?.root === source.root, `cross-namespace reference in ${name}`);
            }
        });
    }
    const options = discriminatorOptions(adaptedSchemas, [...roots]);
    const reachable = new Set();
    const pending = [...roots];
    while (pending.length) {
        const name = pending.pop();
        if (reachable.has(name)) continue;
        reachable.add(name);
        walkSchemas(adaptedSchemas[name], (schema) => {
            if (schema.$ref !== undefined) pending.push(componentName(schema.$ref, adaptedSchemas));
        });
    }
    invariant(reachable.size === Object.keys(adaptedSchemas).length, 'unreachable exported components');
    return {document: adapted, manifest, schemas: adaptedSchemas, discriminatorOptions: options};
}

export function generatorSchemaRefiner(schema) {
    // 1.18.3 interpolates literal values and property names into quoted source text.
    // Escape only that source-facing copy; the canonical document and fingerprint stay intact.
    const escape = (value) => JSON.stringify(value).slice(1, -1);
    const refined = {...schema};
    if (Array.isArray(schema.enum)) {
        refined.enum = schema.enum.map((value) => typeof value === 'string' ? escape(value) : value);
    }
    if (isRecord(schema.properties)) {
        refined.properties = Object.fromEntries(Object.entries(schema.properties).map(([key, value]) =>
            [escape(key), value]));
        if (schema.required) refined.required = schema.required.map(escape);
    }
    if (schema.discriminator) {
        refined.discriminator = {...schema.discriminator, propertyName: escape(schema.discriminator.propertyName)};
    }
    return refined;
}
