import {schemas} from '$lib/api';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import type {ZodType, z} from 'zod';

export type RiskKpiOutput = z.infer<typeof schemas.RiskKpiOutput>;
export type RiskCorrelationOutput = z.infer<typeof schemas.RiskCorrelationOutput>;
export type RiskContributionOutput = z.infer<typeof schemas.RiskContributionOutput>;
export type RiskStressOutput = z.infer<typeof schemas.RiskStressOutput>;
export type RiskComparisonOutput = z.infer<typeof schemas.RiskComparisonOutput>;
export type RiskVarCvarOutput = z.infer<typeof schemas.RiskVarCvarOutput>;
export type RiskSimulationOutput = z.infer<typeof schemas.RiskSimulationOutput>;
export type RiskResultMetadata = z.infer<typeof schemas.RiskResultMetadata>;
export type RiskDataQualityReport = z.infer<typeof schemas.DataQualityReport>;

function isArrayValue<T>(value: T | readonly T[] | null | undefined): value is readonly T[] {
    return Array.isArray(value);
}

export function singleValue<T>(value: T | readonly T[] | null | undefined): T | null {
    if (isArrayValue(value)) return value[0] ?? null;
    return value ?? null;
}

function parsedSingleValue<T>(value: T | readonly T[] | null | undefined, schema: ZodType<T>): T | null {
    const candidate = singleValue(value);
    const parsed = schema.safeParse(candidate);
    return parsed.success ? parsed.data : null;
}

export function riskOutput<T>(result: RiskAnalyticResult | null | undefined, schema: ZodType<T>): T | null {
    const output = singleValue(result?.output);
    const parsed = schema.safeParse(output);
    return parsed.success ? parsed.data : null;
}

export function riskMetadata(result: RiskAnalyticResult | null | undefined): RiskResultMetadata | null {
    return parsedSingleValue(result?.metadata, schemas.RiskResultMetadata);
}

export function riskDataQuality(result: RiskAnalyticResult | null | undefined): RiskDataQualityReport | null {
    return parsedSingleValue(result?.data_quality, schemas.DataQualityReport);
}
