import {readFile, writeFile} from 'node:fs/promises';

const generatedClient = new URL('../src/lib/api/generated.ts', import.meta.url);
const discriminatedSchemas = [
    'SignalPriceValueSource',
    'SignalOutputValueSource',
    'SignalBandValueSource',
    'SignalLineCrossoverRequest',
    'SignalThresholdCrossingRequest',
    'SignalLineSeries',
    'SignalAreaSeries',
    'SignalBarSeries',
    'SignalBandSeries',
    'AiExportDatasetSelection',
    'AiExportAnalysisSelection',
    'AiExportPortfolioSnapshotRequest',
    'AiExportAssetSnapshotRequest',
    'AiExportFxSnapshotRequest',
    'AiExportBrokerSnapshotRequest',
    'AiExportPortfolioTargetReference',
    'AiExportBrokerTargetReference',
    'AiExportAssetTargetReference',
    'AiExportFxPairTargetReference',
    'AiExportVersionMismatchProblem',
    'AiExportUnsupportedSelectionProblem',
    'AiExportSelectionNotApplicableProblem',
    'AiExportBrokerAccessDeniedProblem',
    'AiExportEntityNotFoundProblem',
    'AiExportSnapshotSourceFailureProblem',
    'AssetRiskScope',
    'AssetSetRiskScope',
    'PortfolioRiskScope',
    'RiskKpiOutput',
    'RiskCorrelationOutput',
    'RiskContributionOutput',
    'RiskStressOutput',
    'RiskComparisonOutput',
    'RiskVarCvarOutput',
    'RiskSimulationOutput',
    'RiskPortfolioOptimizationOutput',
    'RiskHistoricalReplayScenario',
    'RiskHypotheticalShockScenario',
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

const requiredLiteralDiscriminators = [
    ['RiskKpiOutput', 'kind', 'kpi'],
    ['RiskCorrelationOutput', 'kind', 'matrix'],
    ['RiskContributionOutput', 'kind', 'contribution'],
    ['RiskStressOutput', 'kind', 'stress'],
    ['RiskComparisonOutput', 'kind', 'comparison'],
    ['RiskVarCvarOutput', 'kind', 'var_cvar'],
    ['RiskSimulationOutput', 'kind', 'simulation'],
    ['RiskPortfolioOptimizationOutput', 'kind', 'optimization'],
];

const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

for (const [schemaName, fieldName, literalValue] of requiredLiteralDiscriminators) {
    // The discriminator field must be a REQUIRED literal for z.discriminatedUnion, but
    // openapi-zod-client emits it as `.optional().default(...)`. Strip that suffix.
    // Robust to either quote style and to single- vs multi-line object formatting
    // (both have varied across openapi-zod-client versions).
    const q = `['"]`;
    const lit = escapeRegExp(literalValue);
    const optionalPattern = new RegExp(`${escapeRegExp(fieldName)}: z\\.literal\\(${q}${lit}${q}\\)\\.optional\\(\\)\\.default\\(${q}${lit}${q}\\)`, 'g');
    const occurrenceCount = (source.match(optionalPattern) || []).length;
    if (occurrenceCount !== 1) {
        throw new Error(`Expected one optional generated discriminator for ${schemaName}.${fieldName}, found ${occurrenceCount}`);
    }

    source = source.replace(optionalPattern, `${fieldName}: z.literal("${literalValue}")`);
}

await writeFile(generatedClient, source);
