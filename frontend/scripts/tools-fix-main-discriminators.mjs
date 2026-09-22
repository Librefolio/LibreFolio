import {readFile} from 'node:fs/promises';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {fixMainToolDiscriminators} from './tools-codec-ast.mjs';
import {publishGenerationSet, withToolGenerationLock} from './tools-generation-io.mjs';
import {invariant, prepareToolDocument} from './tools-schema-document.mjs';

const apiDirectory = resolve(dirname(fileURLToPath(import.meta.url)), '../src/lib/api');

export async function fixMainClientToolOptions() {
    return withToolGenerationLock(apiDirectory, async () => {
        const [client, mainSchema, toolBytes] = await Promise.all([
            readFile(join(apiDirectory, 'generated.ts'), 'utf8'),
            readFile(join(apiDirectory, 'openapi.json'), 'utf8'),
            readFile(join(apiDirectory, 'tool-contracts.openapi.json')),
        ]);
        const prepared = prepareToolDocument(JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(toolBytes)));
        const fixed = fixMainToolDiscriminators(client, JSON.parse(mainSchema), prepared);
        await publishGenerationSet(apiDirectory, new Map([['generated.ts', fixed]]),
            new Map([['generated.ts', client], ['openapi.json', mainSchema], ['tool-contracts.openapi.json', toolBytes]]));
    });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
    try {
        invariant(process.argv.length === 2, 'main Tool discriminator postprocessor accepts no options');
        await fixMainClientToolOptions();
    } catch (error) {
        console.error(error);
        process.exitCode = 1;
    }
}
