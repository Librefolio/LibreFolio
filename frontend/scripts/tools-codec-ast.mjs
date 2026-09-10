import ts from 'typescript';
import {
    componentName, dereference, discriminatorOptions, invariant, isRecord,
    portablePattern, unicodePattern, walkSchemas,
} from './tools-schema-document.mjs';

const factory = ts.factory;
const printer = ts.createPrinter({newLine: ts.NewLineKind.LineFeed});
const emptyFile = ts.createSourceFile('tools-codec.ts', '', ts.ScriptTarget.ES2022, true);
const chainMethods = new Set([
    'min', 'max', 'regex', 'int', 'safe', 'gte', 'lte', 'gt', 'lt', 'multipleOf', 'finite',
    'email', 'url', 'uuid', 'date', 'datetime', 'strict', 'passthrough', 'partial',
    'optional', 'nullable', 'nullish', 'default', 'describe', 'and',
]);

function parseSource(source, name = 'tools-codec.ts') {
    const file = ts.createSourceFile(name, source, ts.ScriptTarget.ES2022, true, ts.ScriptKind.TS);
    invariant(file.parseDiagnostics.length === 0,
        `invalid generated TypeScript: ${file.parseDiagnostics.map((diagnostic) =>
            ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n')).join('\n')}`);
    return file;
}

function print(node) {
    return printer.printNode(ts.EmitHint.Unspecified, node, emptyFile);
}

function zodCall(expression, name) {
    return ts.isCallExpression(expression) && ts.isPropertyAccessExpression(expression.expression) &&
        ts.isIdentifier(expression.expression.expression) && expression.expression.expression.text === 'z' &&
        expression.expression.name.text === name;
}

function callZod(name, args = []) {
    return factory.createCallExpression(
        factory.createPropertyAccessExpression(factory.createIdentifier('z'), name), undefined, args);
}

function isRecordCodec(expression) {
    return ts.isCallExpression(expression) && ts.isIdentifier(expression.expression) &&
        expression.expression.text === 'toolRecordCodec';
}

function callMethod(expression, name, args = []) {
    return factory.createCallExpression(factory.createPropertyAccessExpression(expression, name), undefined, args);
}

function jsonExpression(value) {
    if (value === null) return factory.createNull();
    if (typeof value === 'string') return factory.createStringLiteral(value);
    if (typeof value === 'boolean') return value ? factory.createTrue() : factory.createFalse();
    if (typeof value === 'number') {
        return value < 0 || Object.is(value, -0)
            ? factory.createPrefixUnaryExpression(ts.SyntaxKind.MinusToken, factory.createNumericLiteral(-value))
            : factory.createNumericLiteral(value);
    }
    if (Array.isArray(value)) return factory.createArrayLiteralExpression(value.map(jsonExpression));
    invariant(isRecord(value), 'non-JSON default in generated schema');
    return factory.createObjectLiteralExpression(Object.entries(value).map(([key, item]) =>
        factory.createPropertyAssignment(factory.createComputedPropertyName(factory.createStringLiteral(key)),
            jsonExpression(item))));
}

function splitChain(expression) {
    const chain = [];
    while (ts.isCallExpression(expression) && ts.isPropertyAccessExpression(expression.expression) &&
        !(ts.isIdentifier(expression.expression.expression) && expression.expression.expression.text === 'z')) {
        const method = expression.expression.name.text;
        invariant(chainMethods.has(method), `unhandled generated method .${method}()`);
        chain.unshift({method, args: [...expression.arguments]});
        expression = expression.expression.expression;
    }
    return {base: expression, chain};
}

function propertyKey(name) {
    if (ts.isIdentifier(name) || ts.isStringLiteral(name) || ts.isNumericLiteral(name)) return name.text;
    if (ts.isComputedPropertyName(name) && ts.isStringLiteral(name.expression)) return name.expression.text;
    throw new Error('Tool codegen: unsupported generated property key');
}

function arrayArguments(base, method, position = 0) {
    invariant(zodCall(base, method) && ts.isArrayLiteralExpression(base.arguments[position]),
        `expected generated z.${method}([...])`);
    return [...base.arguments[position].elements];
}

function lazyBody(base) {
    invariant(zodCall(base, 'lazy') && base.arguments.length === 1 &&
        ts.isArrowFunction(base.arguments[0]) && !ts.isBlock(base.arguments[0].body),
    'expected an expression-bodied z.lazy callback');
    return base.arguments[0].body;
}

function regexExpression(pattern) {
    return factory.createNewExpression(factory.createIdentifier('RegExp'), undefined,
        [factory.createStringLiteral(pattern.source), factory.createStringLiteral(pattern.flags)]);
}

function stringValidations(expression, schema) {
    // Replace, rather than supplement, the generator's UTF-16 .min()/.max() checks.
    expression = callMethod(expression, 'regex',
        [regexExpression(unicodePattern(schema.minLength, schema.maxLength))]);
    if (schema.pattern !== undefined) {
        expression = callMethod(expression, 'regex',
            [regexExpression(new RegExp(portablePattern(schema.pattern), 'u'))]);
    }
    const formats = {date: 'date', 'date-time': 'datetime', email: 'email', uri: 'url', uuid: 'uuid'};
    if (schema.format !== undefined) {
        expression = callMethod(expression, formats[schema.format],
            schema.format === 'date-time' ? [jsonExpression({offset: true})] : []);
    }
    return expression;
}

function presence(expression, schema, required) {
    if (!required) expression = callMethod(expression, 'optional');
    if (Object.hasOwn(schema, 'default')) expression = callMethod(expression, 'default', [jsonExpression(schema.default)]);
    return expression;
}

function adaptExpression(expression, schema, schemas, required = true, allowLazy = false) {
    const {base, chain} = splitChain(expression);
    if (zodCall(base, 'lazy')) {
        invariant(allowLazy && chain.length === 0, 'unexpected lazy schema inside an inline shape');
        return callZod('lazy', [factory.createArrowFunction(undefined, undefined, [], undefined,
            factory.createToken(ts.SyntaxKind.EqualsGreaterThanToken),
            adaptExpression(lazyBody(base), schema, schemas, required))]);
    }
    let result;
    if (schema.$ref !== undefined) {
        const name = componentName(schema.$ref, schemas);
        invariant(ts.isIdentifier(base) && base.text === name, `generated reference differs from ${name}`);
        result = base;
    } else if (schema.oneOf || schema.anyOf) {
        const branches = schema.oneOf ?? schema.anyOf;
        if (branches.length === 1) {
            result = adaptExpression(base, branches[0], schemas);
        } else {
            const discriminated = schema.discriminator !== undefined;
            const method = discriminated ? 'discriminatedUnion' : 'union';
            const args = arrayArguments(base, method, discriminated ? 1 : 0);
            invariant(args.length === branches.length, 'generated union lost options');
            if (discriminated) invariant(ts.isStringLiteral(base.arguments[0]) &&
                base.arguments[0].text === schema.discriminator.propertyName, 'generated discriminator changed');
            const options = factory.createArrayLiteralExpression(args.map((argument, index) =>
                adaptExpression(argument, branches[index], schemas)));
            result = callZod(method, discriminated
                ? [factory.createStringLiteral(schema.discriminator.propertyName), options] : [options]);
        }
    } else if (schema.allOf) {
        const conjunctions = chain.filter((entry) => entry.method === 'and');
        invariant(conjunctions.length === schema.allOf.length - 1, 'generated allOf lost constraints');
        result = adaptExpression(base, schema.allOf[0], schemas);
        conjunctions.forEach((entry, index) => {
            invariant(entry.args.length === 1, 'invalid generated intersection');
            result = callMethod(result, 'and', [adaptExpression(entry.args[0], schema.allOf[index + 1], schemas)]);
        });
    } else if (schema.type === 'object' && isRecord(schema.additionalProperties)) {
        invariant(zodCall(base, 'record') && base.arguments.length === 1, 'expected a generated typed dictionary');
        const record = callZod('record', [
            stringValidations(callZod('string'), {type: 'string'}),
            adaptExpression(base.arguments[0], schema.additionalProperties, schemas),
        ]);
        result = factory.createCallExpression(factory.createIdentifier('toolRecordCodec'), undefined, [record]);
    } else if (schema.type === 'object') {
        invariant(zodCall(base, 'object') && base.arguments.length === 1 &&
            ts.isObjectLiteralExpression(base.arguments[0]), 'expected a generated strict model');
        const generated = new Map();
        for (const property of base.arguments[0].properties) {
            invariant(ts.isPropertyAssignment(property), 'generated object contains a non-property member');
            const key = propertyKey(property.name);
            invariant(!generated.has(key), `duplicate generated property ${key}`);
            generated.set(key, property.initializer);
        }
        invariant(generated.size === Object.keys(schema.properties).length &&
            Object.keys(schema.properties).every((key) => generated.has(key)), 'generated model fields differ');
        const properties = Object.entries(schema.properties).map(([key, field]) =>
            factory.createPropertyAssignment(factory.createComputedPropertyName(factory.createStringLiteral(key)),
                adaptExpression(generated.get(key), field, schemas, (schema.required ?? []).includes(key))));
        result = callMethod(callZod('object', [factory.createObjectLiteralExpression(properties, true)]), 'strict');
    } else if (schema.type === 'array') {
        invariant(zodCall(base, 'array') && base.arguments.length === 1, 'expected a generated typed array');
        result = callZod('array', [adaptExpression(base.arguments[0], schema.items, schemas)]);
        if (schema.minItems !== undefined) result = callMethod(result, 'min', [jsonExpression(schema.minItems)]);
        if (schema.maxItems !== undefined) result = callMethod(result, 'max', [jsonExpression(schema.maxItems)]);
    } else if (schema.type === 'null') {
        invariant(zodCall(base, 'null'), 'null was widened by the generator');
        result = base;
    } else if (schema.enum) {
        if (schema.enum.length === 1) {
            invariant(zodCall(base, 'literal'), 'singleton enum was widened by the generator');
            result = callZod('literal', [jsonExpression(schema.enum[0])]);
        } else if (schema.type === 'string') {
            invariant(arrayArguments(base, 'enum').length === schema.enum.length, 'generated enum lost members');
            result = callZod('enum', [factory.createArrayLiteralExpression(schema.enum.map(jsonExpression))]);
        } else {
            invariant(arrayArguments(base, 'union').length === schema.enum.length, 'generated enum lost members');
            result = callZod('union', [factory.createArrayLiteralExpression(schema.enum.map((value) =>
                callZod('literal', [jsonExpression(value)])))]);
        }
    } else if (schema.type === 'string') {
        invariant(zodCall(base, 'string'), 'string was widened by the generator');
        result = stringValidations(base, schema);
    } else if (schema.type === 'number' || schema.type === 'integer') {
        invariant(zodCall(base, 'number'), 'number was widened by the generator');
        result = callMethod(base, 'finite');
        if (schema.type === 'integer') result = callMethod(callMethod(result, 'int'), 'safe');
        for (const [keyword, method] of [
            ['minimum', 'gte'], ['maximum', 'lte'], ['exclusiveMinimum', 'gt'],
            ['exclusiveMaximum', 'lt'], ['multipleOf', 'multipleOf'],
        ]) {
            if (schema[keyword] !== undefined) result = callMethod(result, method, [jsonExpression(schema[keyword])]);
        }
    } else {
        invariant(schema.type === 'boolean' && zodCall(base, 'boolean'), 'unhandled generated primitive');
        result = base;
    }
    invariant(schema.allOf || !chain.some((entry) => entry.method === 'and'),
        'unexpected generated intersection');
    return presence(result, schema, required);
}

function dependencies(schemas) {
    const graph = new Map();
    for (const [name, schema] of Object.entries(schemas)) {
        const references = new Set();
        walkSchemas(schema, (node) => {
            if (node.$ref !== undefined) references.add(componentName(node.$ref, schemas));
        });
        graph.set(name, references);
    }
    const circular = new Set();
    for (const name of graph.keys()) {
        const pending = [...graph.get(name)];
        const visited = new Set();
        while (pending.length) {
            const next = pending.pop();
            if (next === name) circular.add(name);
            if (visited.has(next)) continue;
            visited.add(next);
            pending.push(...graph.get(next));
        }
    }
    return {graph, circular};
}

function declarationOrder(graph, circular) {
    const ordered = [];
    const visited = new Set();
    const visiting = new Set();
    const visit = (name) => {
        if (visited.has(name)) return;
        invariant(!visiting.has(name), `unwrapped initialization cycle at ${name}`);
        visiting.add(name);
        if (!circular.has(name)) [...graph.get(name)].sort().forEach(visit);
        visiting.delete(name);
        visited.add(name);
        ordered.push(name);
    };
    [...graph.keys()].sort().forEach(visit);
    return ordered;
}

const union = (types) => {
    const distinct = [...new Set(types)];
    return distinct.length === 1 ? distinct[0] : `(${distinct.join(' | ')})`;
};

function projectCodecType(expression, direction, declarations, rootPresence, visiting = new Set()) {
    const {base, chain} = splitChain(expression);
    let type;
    let optional = false;
    if (ts.isIdentifier(base)) {
        invariant(declarations.has(base.text), `unresolved generated type reference ${base.text}`);
        type = direction === 'input' ? `${base.text}Input` : base.text;
        optional = rootPresence(base.text, direction, visiting);
    } else if (zodCall(base, 'lazy')) {
        ({type, optional} = projectCodecType(lazyBody(base), direction, declarations, rootPresence, visiting));
    } else if (isRecordCodec(base)) {
        ({type, optional} = projectCodecType(base.arguments[0], direction, declarations, rootPresence, visiting));
    } else if (zodCall(base, 'object')) {
        const properties = base.arguments[0].properties.map((property) => {
            const projected = projectCodecType(property.initializer, direction, declarations, rootPresence, visiting);
            return `${JSON.stringify(propertyKey(property.name))}${projected.optional ? '?' : ''}: ${projected.type}`;
        });
        type = `{ ${properties.join('; ')} }`;
    } else if (zodCall(base, 'record')) {
        const value = projectCodecType(base.arguments[1], direction, declarations, rootPresence, visiting);
        type = `{ [key: string]: ${value.type} }`;
    } else if (zodCall(base, 'array')) {
        const item = projectCodecType(base.arguments[0], direction, declarations, rootPresence, visiting);
        type = `Array<${item.type}>`;
    } else if (zodCall(base, 'union') || zodCall(base, 'discriminatedUnion')) {
        const position = zodCall(base, 'discriminatedUnion') ? 1 : 0;
        const options = base.arguments[position].elements.map((option) =>
            projectCodecType(option, direction, declarations, rootPresence, visiting));
        type = union(options.map((option) => option.type));
        optional = options.some((option) => option.optional);
    } else if (zodCall(base, 'enum')) {
        type = union(base.arguments[0].elements.map(print));
    } else if (zodCall(base, 'literal')) {
        type = print(base.arguments[0]);
    } else if (zodCall(base, 'null')) {
        type = 'null';
    } else {
        const primitive = ['string', 'number', 'boolean'].find((name) => zodCall(base, name));
        invariant(primitive !== undefined, 'cannot derive an exact recursive type from generated codec');
        type = primitive;
    }
    for (const {method, args} of chain) {
        if (method === 'optional' || method === 'nullish') {
            type = union([type, 'undefined']);
            optional = true;
        }
        if (method === 'nullable' || method === 'nullish') type = union([type, 'null']);
        if (method === 'default') {
            type = direction === 'input' ? union([type, 'undefined']) : `Exclude<${type}, undefined>`;
            optional = direction === 'input';
        }
        if (method === 'and') {
            const right = projectCodecType(args[0], direction, declarations, rootPresence, visiting);
            type = `(${type} & ${right.type})`;
            optional = optional && right.optional;
        }
    }
    return {type, optional};
}

function acceptsUndefined(expression, direction, rootPresence, visiting) {
    const {base, chain} = splitChain(expression);
    let optional = false;
    if (ts.isIdentifier(base)) optional = rootPresence(base.text, direction, visiting);
    if (zodCall(base, 'lazy')) optional = acceptsUndefined(lazyBody(base), direction, rootPresence, visiting);
    if (zodCall(base, 'union') || zodCall(base, 'discriminatedUnion')) {
        const position = zodCall(base, 'discriminatedUnion') ? 1 : 0;
        optional = base.arguments[position].elements.some((option) =>
            acceptsUndefined(option, direction, rootPresence, visiting));
    }
    for (const {method, args} of chain) {
        if (method === 'optional' || method === 'nullish') optional = true;
        if (method === 'default') optional = direction === 'input';
        if (method === 'and') optional = optional && acceptsUndefined(args[0], direction, rootPresence, visiting);
    }
    return optional;
}

export function adaptGeneratedToolSchemas(source, prepared, generation, recordRuntime) {
    invariant(typeof recordRuntime === 'string' && recordRuntime.length > 0, 'missing record preservation helper');
    const file = parseSource(source);
    const {schemas, manifest} = prepared;
    const declarations = new Map();
    for (const statement of file.statements) {
        if (ts.isImportDeclaration(statement)) {
            invariant(statement.moduleSpecifier.text === 'zod', 'unexpected generated runtime import');
            continue;
        }
        invariant(ts.isVariableStatement(statement), 'unexpected schemas-only template statement');
        for (const declaration of statement.declarationList.declarations) {
            invariant(ts.isIdentifier(declaration.name) && declaration.initializer &&
                declaration.type === undefined && Object.hasOwn(schemas, declaration.name.text) &&
                !declarations.has(declaration.name.text), 'missing, duplicate or unexpected schema declaration');
            declarations.set(declaration.name.text, declaration.initializer);
        }
    }
    invariant(declarations.size === Object.keys(schemas).length, 'not all schema components were generated');
    const {graph, circular} = dependencies(schemas);
    for (const name of prepared.discriminatorOptions.keys()) {
        invariant(!circular.has(name), `recursive discriminator option ${name} needs a concrete-object strategy`);
    }
    for (const [name, expression] of declarations) {
        const isLazy = zodCall(splitChain(expression).base, 'lazy');
        invariant(isLazy === circular.has(name), `generator recursion metadata differs for ${name}`);
        declarations.set(name, adaptExpression(expression, schemas[name], schemas, true, isLazy));
        invariant(!Object.hasOwn(schemas, `${name}Input`), `generated input type name collides: ${name}Input`);
    }
    const rootPresence = (name, direction, visiting = new Set()) => {
        const key = `${name}:${direction}`;
        if (visiting.has(key)) return false;
        const next = new Set(visiting).add(key);
        return acceptsUndefined(declarations.get(name), direction, rootPresence, next);
    };
    const lines = [
        '// Generated from real Tool Pydantic contracts. Do not edit.',
        `// Contract generation: ${generation}`,
        'import { z } from "zod";',
        `export const toolContractGeneration = ${JSON.stringify(generation)};`,
        recordRuntime,
    ];
    // Upstream's recursive TS conversion widens anyOf and dictionary types. Project
    // only cycles from the generated codec AST; all other types use native Zod inference.
    for (const name of [...declarations.keys()].sort()) {
        if (circular.has(name)) {
            const output = projectCodecType(declarations.get(name), 'output', declarations, rootPresence).type;
            const input = projectCodecType(declarations.get(name), 'input', declarations, rootPresence).type;
            lines.push(`export type ${name} = ${output};`, `export type ${name}Input = ${input};`);
        } else {
            lines.push(`export type ${name} = z.output<typeof ${name}>;`,
                `export type ${name}Input = z.input<typeof ${name}>;`);
        }
    }
    for (const name of declarationOrder(graph, circular)) {
        const annotation = circular.has(name) ? `: z.ZodType<${name}, z.ZodTypeDef, ${name}Input>` : '';
        lines.push(`export const ${name}${annotation} = ${print(declarations.get(name))};`);
    }
    lines.push(`export const schemas = {${[...declarations.keys()].sort().join(', ')}} as const;`);
    lines.push('export const toolTransportSchemas = {');
    for (const [role, entry] of Object.entries(manifest.transport)) {
        lines.push(`${JSON.stringify(role)}: ${componentName(entry.schema, schemas)},`);
    }
    lines.push('} as const;',
        'export type ToolItemMetrics = z.output<typeof toolTransportSchemas.computeResponse>["results"][number]["metrics"];',
        'export type ToolBatchMetrics = z.output<typeof toolTransportSchemas.computeResponse>["metrics"];');
    const result = `${lines.join('\n')}\n`;
    parseSource(result);
    return result;
}

function normalizeMainName(name) {
    invariant(/^[A-Za-z][A-Za-z0-9_.-]*(?![\s\S])/u.test(name), `unsupported main-client schema name ${name}`);
    return name.replace(/[^A-Za-z0-9_]/gu, '_');
}

function mainToolSchemas(mainDocument, manifest) {
    const schemas = mainDocument.components?.schemas;
    invariant(isRecord(schemas), 'main OpenAPI components are missing');
    const roots = new Set();
    for (const entry of Object.values(manifest.transport)) {
        const candidates = Object.entries(schemas).filter(([name, schema]) =>
            name === entry.model || schema.title === entry.model);
        invariant(candidates.length > 0, `main OpenAPI transport root ${entry.model} is missing`);
        for (const [name] of candidates) roots.add(name);
    }
    const rawName = (reference) => {
        const prefix = '#/components/schemas/';
        invariant(typeof reference === 'string' && reference.startsWith(prefix) &&
            Object.hasOwn(schemas, reference.slice(prefix.length)), 'unresolved main Tool reference');
        return reference.slice(prefix.length);
    };
    const pending = [...roots];
    const selected = new Map();
    while (pending.length) {
        const name = pending.pop();
        if (selected.has(name)) continue;
        selected.set(name, structuredClone(schemas[name]));
        walkSchemas(schemas[name], (schema) => {
            if (schema.$ref !== undefined) pending.push(rawName(schema.$ref));
        });
    }
    const normalized = {};
    for (const [name, schema] of selected) {
        const target = normalizeMainName(name);
        invariant(!Object.hasOwn(normalized, target), `main Tool name collision ${target}`);
        walkSchemas(schema, (node) => {
            if (node.$ref !== undefined) node.$ref = `#/components/schemas/${normalizeMainName(rawName(node.$ref))}`;
            if (node.discriminator?.mapping) {
                node.discriminator.mapping = Object.fromEntries(Object.entries(node.discriminator.mapping).map(
                    ([value, ref]) => [value, `#/components/schemas/${normalizeMainName(rawName(ref))}`]));
            }
        });
        normalized[target] = schema;
    }
    return {schemas: normalized, roots: [...roots].map(normalizeMainName)};
}

function discriminatorSignatures(schemas, options) {
    const signatures = new Set();
    for (const [name, fields] of options) {
        const model = dereference(schemas[name], schemas);
        invariant(typeof model.title === 'string', `missing discriminator model title: ${name}`);
        for (const [key, literals] of fields) signatures.add(JSON.stringify([model.title, key, [...literals].sort()]));
    }
    return signatures;
}

export function fixMainToolDiscriminators(source, mainDocument, prepared) {
    const selected = mainToolSchemas(mainDocument, prepared.manifest);
    const options = discriminatorOptions(selected.schemas, selected.roots);
    const transportRoots = Object.values(prepared.manifest.transport).map((entry) =>
        componentName(entry.schema, prepared.schemas));
    const expected = discriminatorSignatures(prepared.schemas,
        discriminatorOptions(prepared.schemas, transportRoots));
    const actual = discriminatorSignatures(selected.schemas, options);
    invariant(expected.size === actual.size && [...expected].every((signature) => actual.has(signature)),
        'main Tool discriminators differ from the real transport contract metadata');
    const file = parseSource(source, 'generated.ts');
    const found = new Set();
    const edits = [];
    for (const statement of file.statements) {
        if (!ts.isVariableStatement(statement)) continue;
        for (const declaration of statement.declarationList.declarations) {
            if (!ts.isIdentifier(declaration.name) || !options.has(declaration.name.text)) continue;
            const name = declaration.name.text;
            invariant(!found.has(name) && declaration.initializer, `duplicate or missing main option ${name}`);
            found.add(name);
            const {base, chain} = splitChain(declaration.initializer);
            invariant(zodCall(base, 'object') && !chain.some((entry) =>
                ['optional', 'nullable', 'nullish', 'default', 'and'].includes(entry.method)),
            `main discriminator option ${name} is not a concrete object`);
            const properties = new Map(base.arguments[0].properties.map((property) => {
                invariant(ts.isPropertyAssignment(property), 'unexpected main generated member');
                return [propertyKey(property.name), property.initializer];
            }));
            for (const [key, literals] of options.get(name)) {
                invariant(properties.has(key), `missing main discriminator ${name}.${key}`);
                const tag = splitChain(properties.get(key));
                invariant(!tag.chain.some((entry) =>
                    ['optional', 'nullable', 'nullish', 'default'].includes(entry.method)),
                `main discriminator ${name}.${key} must remain required`);
                const actual = zodCall(tag.base, 'literal') ? [tag.base.arguments[0]]
                    : zodCall(tag.base, 'enum') ? [...tag.base.arguments[0].elements] : [];
                invariant(actual.length === literals.length && actual.every((value, index) =>
                    ts.isStringLiteral(value) && value.text === literals[index]),
                `main discriminator ${name}.${key} was widened`);
            }
            if (declaration.type) {
                invariant(ts.isTypeReferenceNode(declaration.type) &&
                    declaration.type.typeName.getText(file) === 'z.ZodType' &&
                    declaration.type.typeArguments?.length === 1 &&
                    declaration.type.typeArguments[0].getText(file) === name,
                `unexpected main discriminator annotation for ${name}`);
                edits.push({start: declaration.name.end, end: declaration.type.end});
            }
        }
    }
    invariant(found.size === options.size, 'main client is missing declared Tool discriminator options');
    for (const edit of edits.sort((left, right) => right.start - left.start)) {
        source = source.slice(0, edit.start) + source.slice(edit.end);
    }
    return source;
}
