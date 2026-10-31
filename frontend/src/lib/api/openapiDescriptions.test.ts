/**
 * Z-37: a backtick (or `${`) in the description of a model that a required field refers to must not break
 * `generated.ts`.
 *
 * `openapi-zod-client --with-description` writes the description of the referred model into a template literal
 * (`Inner.describe(\`…\`)`): a backtick in a docstring closes it and `api sync` stops with «Tool codegen: invalid
 * generated TypeScript». `scripts/sanitize-openapi-descriptions.mjs` rewrites the descriptions of the exported
 * OpenAPI document before the generator reads it (`npm run generate-api`), so no docstring has to be written around
 * the generator.
 */
import {execFileSync} from 'node:child_process';
import {mkdtempSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import {afterAll, describe, expect, it} from 'vitest';
import {neutralizeDescription, neutralizeOpenApiDescriptions} from '../../../scripts/sanitize-openapi-descriptions.mjs';

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const GENERATOR = path.join(FRONTEND, 'node_modules', '.bin', 'openapi-zod-client');

const document = () => ({
    openapi: '3.0.3',
    info: {title: 't', version: '1'},
    paths: {'/x': {get: {operationId: 'getX', responses: {'200': {description: 'ok', content: {'application/json': {schema: {$ref: '#/components/schemas/Outer'}}}}}}}},
    components: {
        schemas: {
            Inner: {type: 'object', description: 'A model with `backticks` and ${a_placeholder} inside\nand a second line.', properties: {a: {type: 'string', description: 'A `field`'}}, required: ['a']},
            Outer: {type: 'object', properties: {inner: {$ref: '#/components/schemas/Inner'}}, required: ['inner']},
        },
    },
});

const scratch = mkdtempSync(path.join(tmpdir(), 'lf-openapi-descriptions-'));
afterAll(() => rmSync(scratch, {recursive: true, force: true}));

function generate(doc: unknown, name: string): string {
    const input = path.join(scratch, `${name}.json`);
    const output = path.join(scratch, `${name}.ts`);
    writeFileSync(input, JSON.stringify(doc));
    execFileSync(GENERATOR, [input, '-o', output, '--export-types', '--with-docs', '--with-description'], {stdio: 'pipe'});
    return readFileSync(output, 'utf8');
}

const syntaxErrors = (source: string) => (ts.transpileModule(source, {reportDiagnostics: true, fileName: 'generated.ts'}).diagnostics ?? []).length;

describe('neutralizeDescription', () => {
    it('turns a backtick into an apostrophe and defuses ${', () => {
        expect(neutralizeDescription('a `b` c ${d}')).toBe("a 'b' c $ {d}");
    });

    it('leaves a description without them as it is', () => {
        expect(neutralizeDescription('Plain text.\nSecond line.')).toBe('Plain text.\nSecond line.');
    });
});

describe('neutralizeOpenApiDescriptions', () => {
    it('rewrites the description of every schema and property, and nothing else', () => {
        const doc = document();
        const changed = neutralizeOpenApiDescriptions(doc);

        expect(changed).toBe(2);
        expect(doc.components.schemas.Inner.description).not.toContain('`');
        expect(doc.components.schemas.Inner.properties.a.description).toBe("A 'field'");
        expect(doc.components.schemas.Inner.required).toEqual(['a']);
    });

    it('does not touch a property that is itself called description', () => {
        const doc = {components: {schemas: {M: {type: 'object', properties: {description: {type: 'string', description: 'The `text`'}}}}}};
        neutralizeOpenApiDescriptions(doc);

        expect(doc.components.schemas.M.properties.description.type).toBe('string');
        expect(doc.components.schemas.M.properties.description.description).toBe("The 'text'");
    });
});

describe('the generated client', () => {
    it('is not valid TypeScript when a referred model keeps a backtick (the defect)', () => {
        expect(syntaxErrors(generate(document(), 'raw'))).toBeGreaterThan(0);
    });

    it('is valid once the descriptions are neutralized, and keeps the text', () => {
        const doc = document();
        neutralizeOpenApiDescriptions(doc);
        const source = generate(doc, 'clean');

        expect(syntaxErrors(source)).toBe(0);
        expect(source).toContain("A model with 'backticks'");
    });
});
