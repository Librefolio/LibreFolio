import {readFile, writeFile} from 'node:fs/promises';

const generatedClient = new URL('../src/lib/api/generated.ts', import.meta.url);
const discriminatedSchemas = [
    'SignalPriceValueSource',
    'SignalOutputValueSource',
    'SignalBandValueSource',
    'SignalLineCrossoverRequest',
    'SignalThresholdCrossingRequest',
    'SignalLineSeries',
    'SignalBarSeries',
    'SignalBandSeries',
    'AiExportPortfolioSnapshotRequest',
    'AiExportAssetSnapshotRequest',
    'AiExportFxSnapshotRequest',
    'AiExportBrokerSnapshotRequest',
    'AiExportPortfolioSnapshotResponse',
    'AiExportAssetSnapshotResponse',
    'AiExportFxSnapshotResponse',
    'AiExportBrokerSnapshotResponse',
    'AiExportPortfolioTargetReference',
    'AiExportBrokerTargetReference',
    'AiExportAssetTargetReference',
    'AiExportFxPairTargetReference',
    'AiExportUnsupportedProfileProblem',
    'AiExportProfileContractMismatchProblem',
    'AiExportTaskNotApplicableProblem',
    'AiExportBrokerAccessDeniedProblem',
    'AiExportEntityNotFoundProblem',
    'AiExportSnapshotSourceFailureProblem',
    'AssetRiskScope',
    'AssetSetRiskScope',
    'PortfolioRiskScope',
    'BrokerRiskScope',
    'RiskKpiOutput',
    'RiskCorrelationOutput',
    'RiskContributionOutput',
    'RiskStressOutput',
    'RiskComparisonOutput',
    'RiskVarCvarOutput',
];

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
