import {schemas} from '$lib/api';

import {findAiExportResponseContract} from '../templates/responseContracts';
import {findAiExportAnalysisInstruction} from '../templates/sharedInstructions';
import {
    AI_EXPORT_ANALYSIS_IDS,
    AI_EXPORT_CATALOG_VERSION,
    AI_EXPORT_DATASET_IDS,
    AI_EXPORT_SCHEMA_VERSION,
    aiExportSelectionKey,
    isAiExportAnalysisId,
    isAiExportDatasetId,
    type AiExportAnalysisCatalogEntry,
    type AiExportBackendCatalogResponse,
    type AiExportCatalogEntry,
    type AiExportCompatibleSelection,
    type AiExportDomain,
    type AiExportSelectionId,
    type AiExportSelectionKind,
} from './shared';

export type AiExportCompatibilityReasonCode = 'schema_version_mismatch' | 'catalog_version_mismatch' | 'dataset_catalog_mismatch' | 'analysis_catalog_mismatch' | 'selection_version_mismatch' | 'instruction_contract_mismatch' | 'response_contract_mismatch';

export interface AiExportCatalogCompatibilityResult {
    readonly status: 'compatible' | 'disabled';
    readonly catalog: AiExportBackendCatalogResponse;
    readonly selections: readonly AiExportCompatibleSelection[];
    readonly byKey: ReadonlyMap<string, AiExportCompatibleSelection>;
    readonly reasonCodes: readonly AiExportCompatibilityReasonCode[];
}

export class AiExportCatalogHttpError extends Error {
    readonly kind = 'http';

    constructor(
        readonly status: number,
        readonly statusText: string,
    ) {
        super(`AI Export catalog request failed: ${status}${statusText ? ` ${statusText}` : ''}`);
        this.name = 'AiExportCatalogHttpError';
    }
}

function idsMatch(actual: readonly string[], expected: readonly string[]): boolean {
    return actual.length === expected.length && new Set(actual).size === actual.length && expected.every((id) => actual.includes(id));
}

function analysisContractsMatch(entry: AiExportAnalysisCatalogEntry): boolean {
    if (!isAiExportAnalysisId(entry.id)) return false;
    const instruction = findAiExportAnalysisInstruction(entry.id);
    const responseContract = findAiExportResponseContract(entry.id);
    return instruction?.id === entry.instruction_template_id && instruction.version === entry.instruction_template_version && responseContract?.id === entry.response_contract_id && responseContract.version === entry.response_contract_version;
}

function compatibleSelection(entry: AiExportCatalogEntry): AiExportCompatibleSelection | undefined {
    if (entry.version !== 1) return undefined;
    if (entry.kind === 'dataset') {
        if (!isAiExportDatasetId(entry.id)) return undefined;
        return {
            kind: 'dataset',
            id: entry.id,
            domain: entry.domain,
            version: 1,
            supportedDetailLevels: entry.supported_detail_levels,
            entry,
        };
    }
    if (!isAiExportAnalysisId(entry.id) || !analysisContractsMatch(entry)) return undefined;
    return {
        kind: 'analysis',
        id: entry.id,
        domain: entry.domain,
        version: 1,
        supportedDetailLevels: entry.supported_detail_levels,
        entry,
    };
}

export function reconcileAiExportCatalog(catalog: AiExportBackendCatalogResponse): AiExportCatalogCompatibilityResult {
    const reasons: AiExportCompatibilityReasonCode[] = [];
    if (catalog.schema_version !== AI_EXPORT_SCHEMA_VERSION) reasons.push('schema_version_mismatch');
    if (catalog.catalog_version !== AI_EXPORT_CATALOG_VERSION) reasons.push('catalog_version_mismatch');
    if (
        !idsMatch(
            catalog.datasets.map((entry) => entry.id),
            AI_EXPORT_DATASET_IDS,
        )
    )
        reasons.push('dataset_catalog_mismatch');
    if (
        !idsMatch(
            catalog.analyses.map((entry) => entry.id),
            AI_EXPORT_ANALYSIS_IDS,
        )
    )
        reasons.push('analysis_catalog_mismatch');

    const selections: AiExportCompatibleSelection[] = [];
    for (const entry of [...catalog.datasets, ...catalog.analyses]) {
        const compatible = compatibleSelection(entry);
        if (compatible) selections.push(compatible);
        else if (entry.version !== 1) reasons.push('selection_version_mismatch');
        else if (entry.kind === 'analysis') {
            const instruction = isAiExportAnalysisId(entry.id) ? findAiExportAnalysisInstruction(entry.id) : undefined;
            if (instruction?.id !== entry.instruction_template_id || instruction?.version !== entry.instruction_template_version) reasons.push('instruction_contract_mismatch');
            const responseContract = isAiExportAnalysisId(entry.id) ? findAiExportResponseContract(entry.id) : undefined;
            if (responseContract?.id !== entry.response_contract_id || responseContract?.version !== entry.response_contract_version) reasons.push('response_contract_mismatch');
        }
    }

    const uniqueReasons = [...new Set(reasons)];
    const byKey = new Map(selections.map((selection) => [aiExportSelectionKey(selection.kind, selection.id), selection]));
    return {
        status: uniqueReasons.length === 0 ? 'compatible' : 'disabled',
        catalog,
        selections,
        byKey,
        reasonCodes: uniqueReasons,
    };
}

export function emptyAiExportCompatibility(): AiExportCatalogCompatibilityResult {
    return reconcileAiExportCatalog({
        schema_version: AI_EXPORT_SCHEMA_VERSION,
        catalog_version: AI_EXPORT_CATALOG_VERSION,
        datasets: [],
        analyses: [],
    });
}

export function findCompatibleAiExportSelection(compatibility: AiExportCatalogCompatibilityResult, kind: AiExportSelectionKind, id: AiExportSelectionId): AiExportCompatibleSelection | undefined {
    return compatibility.byKey.get(aiExportSelectionKey(kind, id));
}

export function selectionsForDomain(compatibility: AiExportCatalogCompatibilityResult, domain: AiExportDomain, kind?: AiExportSelectionKind): readonly AiExportCompatibleSelection[] {
    return compatibility.selections.filter((selection) => selection.domain === domain && (kind === undefined || selection.kind === kind));
}

export type AiExportCatalogFetcher = () => Promise<AiExportBackendCatalogResponse>;

export async function fetchBackendAiExportCatalog(fetcher: typeof fetch = fetch): Promise<AiExportBackendCatalogResponse> {
    const response = await fetcher('/api/v1/ai-export/catalog', {
        credentials: 'same-origin',
        headers: {Accept: 'application/json'},
    });
    if (!response.ok) throw new AiExportCatalogHttpError(response.status, response.statusText);
    return schemas.AiExportCatalogResponse.parse(await response.json());
}

export class AiExportCatalogLoader {
    private cachedResult: AiExportCatalogCompatibilityResult | undefined;
    private inFlight: Promise<AiExportCatalogCompatibilityResult> | undefined;

    constructor(private readonly fetchCatalog: AiExportCatalogFetcher = fetchBackendAiExportCatalog) {}

    load(): Promise<AiExportCatalogCompatibilityResult> {
        if (this.cachedResult) return Promise.resolve(this.cachedResult);
        if (this.inFlight) return this.inFlight;
        const request = this.fetchCatalog().then(reconcileAiExportCatalog);
        this.inFlight = request;
        request.then(
            (result) => {
                this.cachedResult = result;
                if (this.inFlight === request) this.inFlight = undefined;
            },
            () => {
                if (this.inFlight === request) this.inFlight = undefined;
            },
        );
        return request;
    }

    peek(): AiExportCatalogCompatibilityResult | undefined {
        return this.cachedResult;
    }

    reset(): void {
        this.cachedResult = undefined;
        this.inFlight = undefined;
    }
}

export const aiExportCatalogLoader = new AiExportCatalogLoader();
