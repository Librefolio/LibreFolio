import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {generateZodClientFromOpenAPI} from 'openapi-zod-client';
import {adaptGeneratedToolSchemas} from './tools-codec-ast.mjs';
import {
    assertLockedToolchain, publishGenerationSet, validateGeneratedTypes, withToolGenerationLock,
} from './tools-generation-io.mjs';
import {componentName, generatorSchemaRefiner, invariant, prepareToolDocument} from './tools-schema-document.mjs';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const defaultApiDirectory = resolve(scriptDirectory, '../src/lib/api');
const lexicalOrder = (left, right) => left < right ? -1 : left > right ? 1 : 0;

export function renderToolContractMap(prepared, generation) {
    const entries = new Map();
    for (const tool of prepared.manifest.tools) {
        if (!entries.has(tool.toolCode)) entries.set(tool.toolCode, []);
        entries.get(tool.toolCode).push(tool);
    }
    const lines = [
        '// Generated from real Tool Pydantic contracts. Do not edit.',
        `// Contract generation: ${generation}`,
        'import type { z } from "zod";',
        'import * as generated from "./generated-tools";',
        `if (String(generated.toolContractGeneration) !== ${JSON.stringify(generation)}) {`,
        'throw new Error("Tool codec and contract map generations do not match");',
        '}',
        'export const toolContractMap = {',
    ];
    for (const [code, versions] of [...entries].sort(([left], [right]) => lexicalOrder(left, right))) {
        lines.push(`${JSON.stringify(code)}: {`);
        for (const entry of versions.sort((left, right) => lexicalOrder(left.contractVersion, right.contractVersion))) {
            lines.push(`${JSON.stringify(entry.contractVersion)}: {`);
            for (const key of ['toolCode', 'contractVersion', 'schemaFingerprint', 'componentKey', 'uiContractVersion']) {
                lines.push(`${key}: ${JSON.stringify(entry[key])},`);
            }
            lines.push(`input: generated.${componentName(entry.input, prepared.schemas)},`,
                `output: generated.${componentName(entry.output, prepared.schemas)},`,
                `operations: ${JSON.stringify(entry.operations)},`, '},');
        }
        lines.push('},');
    }
    lines.push('} as const;',
        'export type ToolContractMap = typeof toolContractMap;',
        'export type ToolCode = keyof ToolContractMap;',
        '// Distribute code/version unions instead of intersecting their version keys.',
        'export type ToolVersion<C extends ToolCode> = C extends ToolCode ? Extract<keyof ToolContractMap[C], string> : never;',
        'type ToolCodec<C extends ToolCode, V extends ToolVersion<C>, K extends "input" | "output"> =',
        'C extends ToolCode ? V extends keyof ToolContractMap[C]',
        '? ToolContractMap[C][V] extends { [P in K]: infer Codec extends z.ZodType<unknown, z.ZodTypeDef, unknown> } ? Codec : never',
        ': never : never;',
        'export type ToolInput<C extends ToolCode, V extends ToolVersion<C>> = z.input<ToolCodec<C, V, "input">>;',
        'export type ToolOutput<C extends ToolCode, V extends ToolVersion<C>> = z.output<ToolCodec<C, V, "output">>;');
    return `${lines.join('\n')}\n`;
}

export async function generateToolsClient({apiDirectory = defaultApiDirectory} = {}) {
    await assertLockedToolchain();
    return withToolGenerationLock(apiDirectory, async () => {
        const inputName = 'tool-contracts.openapi.json';
        const original = await readFile(join(apiDirectory, inputName));
        const prepared = prepareToolDocument(JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(original)));
        const generation = createHash('sha256').update(original).digest('hex');
        // Verified against the published 1.18.3 source. This is the programmatic
        // equivalent of --export-schemas --strict-objects, without SwaggerParser or paths.
        const generated = await generateZodClientFromOpenAPI({
            openApiDoc: structuredClone(prepared.document),
            templatePath: join(scriptDirectory, 'tools-schemas.hbs'),
            disableWriteToFile: true,
            prettierConfig: {parser: 'typescript', endOfLine: 'lf', singleQuote: false},
            options: {
                shouldExportAllSchemas: true,
                shouldExportAllTypes: false,
                exportAllNamedSchemas: true,
                strictObjects: true,
                additionalPropertiesDefaultValue: false,
                withDefaultValues: true,
                withDescription: false,
                withDocs: false,
                groupStrategy: 'none',
                complexityThreshold: 0,
                schemaRefiner: generatorSchemaRefiner,
            },
        });
        invariant(typeof generated === 'string', 'expected a single schemas-only generation');
        const recordRuntime = await readFile(join(scriptDirectory, 'tools-record-runtime.hbs'), 'utf8');
        const codecs = adaptGeneratedToolSchemas(generated, prepared, generation, recordRuntime);
        const contractMap = renderToolContractMap(prepared, generation);
        validateGeneratedTypes(new Map([
            [join(apiDirectory, 'generated-tools.ts'), codecs],
            [join(apiDirectory, 'tool-contract-map.generated.ts'), contractMap],
        ]));
        await publishGenerationSet(apiDirectory, new Map([
            [inputName, original],
            ['generated-tools.ts', codecs],
            ['tool-contract-map.generated.ts', contractMap],
        ]), new Map([[inputName, original]]));
        return {generation, toolCount: prepared.manifest.tools.length};
    });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
    try {
        invariant(process.argv.length === 2, 'generator configuration is fixed; use ./dev.py api sync');
        const result = await generateToolsClient();
        console.log(`Tool contracts generated: ${result.toolCount} tools (${result.generation})`);
    } catch (error) {
        console.error(error);
        process.exitCode = 1;
    }
}
