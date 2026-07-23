import {readFile, writeFile} from 'node:fs/promises';

const generatedClient = new URL('../src/lib/api/generated.ts', import.meta.url);
const discriminatedSchemas = ['SignalPriceValueSource', 'SignalOutputValueSource', 'SignalLineCrossoverRequest', 'SignalThresholdCrossingRequest', 'SignalLineSeries', 'SignalBarSeries', 'SignalBandSeries'];

let source = await readFile(generatedClient, 'utf8');

for (const schemaName of discriminatedSchemas) {
    // openapi-zod-client's exported type annotation hides ZodObject methods required
    // by z.discriminatedUnion. Keep exported types, but infer these concrete schemas.
    const annotatedDeclaration = `const ${schemaName}: z.ZodType<${schemaName}> =`;
    const occurrenceCount = source.split(annotatedDeclaration).length - 1;

    if (occurrenceCount !== 1) {
        throw new Error(`Expected one generated declaration for ${schemaName}, found ${occurrenceCount}`);
    }

    source = source.replace(annotatedDeclaration, `const ${schemaName} =`);
}

await writeFile(generatedClient, source);
