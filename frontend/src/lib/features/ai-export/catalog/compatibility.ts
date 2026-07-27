import {schemas} from '$lib/api';

import {ASSET_AI_EXPORT_TASKS} from './assetTasks';
import {BROKER_AI_EXPORT_TASKS} from './brokerTasks';
import {FX_AI_EXPORT_TASKS} from './fxTasks';
import {PORTFOLIO_AI_EXPORT_TASKS} from './portfolioTasks';
import {AI_EXPORT_CATALOG_SCHEMA_VERSION, AI_EXPORT_DETAIL_LEVELS, AI_EXPORT_DOMAIN_ORDER, aiExportCatalogTupleKey, expandAiExportTaskDefinitions, type AiExportBackendCatalogEntry, type AiExportBackendCatalogResponse, type AiExportLocalCatalogChoice, type AiExportTaskDefinition} from './shared';

export const AI_EXPORT_TASK_CATALOG = [...PORTFOLIO_AI_EXPORT_TASKS, ...ASSET_AI_EXPORT_TASKS, ...FX_AI_EXPORT_TASKS, ...BROKER_AI_EXPORT_TASKS] as const satisfies readonly AiExportTaskDefinition[];

export const AI_EXPORT_LOCAL_CHOICES = expandAiExportTaskDefinitions(AI_EXPORT_TASK_CATALOG);

export type AiExportCompatibilityReasonCode =
    | 'backend_catalog_schema_version_mismatch'
    | 'backend_presentation_text_present'
    | 'backend_entry_missing'
    | 'local_definition_missing'
    | 'duplicate_backend_entry'
    | 'profile_id_mismatch'
    | 'profile_version_mismatch'
    | 'response_contract_id_mismatch'
    | 'response_contract_version_mismatch'
    | 'supports_user_notes_mismatch'
    | 'supports_web_research_mismatch';

export interface AiExportCatalogCompatibilityChoice extends AiExportLocalCatalogChoice {
    readonly status: 'compatible' | 'disabled';
    readonly reasonCode: AiExportCompatibilityReasonCode | null;
    readonly backendEntry?: AiExportBackendCatalogEntry;
}

export interface AiExportBackendOnlyCatalogEntry {
    readonly key: string;
    readonly status: 'disabled';
    readonly reasonCode: 'local_definition_missing';
    readonly entry: AiExportBackendCatalogEntry;
}

export interface AiExportCatalogCompatibilityResult {
    readonly status: 'compatible' | 'disabled';
    readonly choices: readonly AiExportCatalogCompatibilityChoice[];
    readonly selectableChoices: readonly AiExportCatalogCompatibilityChoice[];
    readonly backendOnlyEntries: readonly AiExportBackendOnlyCatalogEntry[];
    readonly reasonCodes: readonly AiExportCompatibilityReasonCode[];
}

const PRESENTATION_FIELD_PATTERN = /(prompt|label|instruction)/i;

export class AiExportCatalogPresentationDriftError extends Error {
    readonly kind = 'presentation_drift';

    constructor(readonly fields: readonly string[]) {
        super(`AI Export catalog contains backend presentation fields: ${fields.join(', ')}`);
        this.name = 'AiExportCatalogPresentationDriftError';
    }
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

export function findBackendCatalogPresentationFields(catalog: unknown): readonly string[] {
    const fields = new Set<string>();
    const visited = new WeakSet<object>();

    function visit(value: unknown): void {
        if (value === null || typeof value !== 'object' || visited.has(value)) return;
        visited.add(value);

        for (const [field, nestedValue] of Object.entries(value)) {
            if (PRESENTATION_FIELD_PATTERN.test(field)) fields.add(field);
            visit(nestedValue);
        }
    }

    visit(catalog);
    return [...fields].sort();
}

function compareBackendEntries(left: AiExportBackendCatalogEntry, right: AiExportBackendCatalogEntry): number {
    const domainOrder = AI_EXPORT_DOMAIN_ORDER.indexOf(left.domain) - AI_EXPORT_DOMAIN_ORDER.indexOf(right.domain);
    if (domainOrder !== 0) return domainOrder;

    const taskOrder = AI_EXPORT_TASK_CATALOG.findIndex((definition) => definition.backendTask === left.task) - AI_EXPORT_TASK_CATALOG.findIndex((definition) => definition.backendTask === right.task);
    if (taskOrder !== 0) return taskOrder;

    const detailOrder = AI_EXPORT_DETAIL_LEVELS.indexOf(left.detail_level) - AI_EXPORT_DETAIL_LEVELS.indexOf(right.detail_level);
    if (detailOrder !== 0) return detailOrder;

    return left.profile_id.localeCompare(right.profile_id);
}

function findEntryMismatch(localChoice: AiExportLocalCatalogChoice, backendEntry: AiExportBackendCatalogEntry): AiExportCompatibilityReasonCode | null {
    if (backendEntry.profile_id !== localChoice.profileId) return 'profile_id_mismatch';
    if (backendEntry.profile_version !== localChoice.profileVersion) return 'profile_version_mismatch';
    if (backendEntry.frontend_response_contract_id !== localChoice.frontendResponseContractId) return 'response_contract_id_mismatch';
    if (backendEntry.frontend_response_contract_version !== localChoice.frontendResponseContractVersion) return 'response_contract_version_mismatch';
    if (backendEntry.supports_user_notes !== localChoice.supportsUserNotes) return 'supports_user_notes_mismatch';
    if (backendEntry.supports_web_research !== localChoice.supportsWebResearch) return 'supports_web_research_mismatch';
    return null;
}

function collectReasonCodes(choices: readonly AiExportCatalogCompatibilityChoice[], backendOnlyEntries: readonly AiExportBackendOnlyCatalogEntry[]): readonly AiExportCompatibilityReasonCode[] {
    const reasonCodes: AiExportCompatibilityReasonCode[] = [];
    const seen = new Set<AiExportCompatibilityReasonCode>();

    for (const choice of choices) {
        if (choice.reasonCode !== null && !seen.has(choice.reasonCode)) {
            seen.add(choice.reasonCode);
            reasonCodes.push(choice.reasonCode);
        }
    }
    for (const backendOnlyEntry of backendOnlyEntries) {
        if (!seen.has(backendOnlyEntry.reasonCode)) {
            seen.add(backendOnlyEntry.reasonCode);
            reasonCodes.push(backendOnlyEntry.reasonCode);
        }
    }

    return reasonCodes;
}

export function reconcileAiExportCatalog(catalog: AiExportBackendCatalogResponse): AiExportCatalogCompatibilityResult {
    const backendEntries = catalog.entries ?? [];
    const localKeys = new Set(AI_EXPORT_LOCAL_CHOICES.map((choice) => choice.key));
    const backendEntriesByKey = new Map<string, AiExportBackendCatalogEntry[]>();

    for (const entry of backendEntries) {
        const key = aiExportCatalogTupleKey(entry.domain, entry.task, entry.detail_level);
        const entries = backendEntriesByKey.get(key);
        if (entries) entries.push(entry);
        else backendEntriesByKey.set(key, [entry]);
    }

    const backendOnlyEntries = backendEntries
        .filter((entry) => !localKeys.has(aiExportCatalogTupleKey(entry.domain, entry.task, entry.detail_level)))
        .sort(compareBackendEntries)
        .map(
            (entry): AiExportBackendOnlyCatalogEntry => ({
                key: aiExportCatalogTupleKey(entry.domain, entry.task, entry.detail_level),
                status: 'disabled',
                reasonCode: 'local_definition_missing',
                entry,
            }),
        );

    const presentationFields = findBackendCatalogPresentationFields(catalog);
    const globalReasonCode: AiExportCompatibilityReasonCode | null = catalog.schema_version !== AI_EXPORT_CATALOG_SCHEMA_VERSION ? 'backend_catalog_schema_version_mismatch' : presentationFields.length > 0 ? 'backend_presentation_text_present' : null;

    const choices = AI_EXPORT_LOCAL_CHOICES.map((localChoice): AiExportCatalogCompatibilityChoice => {
        if (globalReasonCode !== null) {
            return {
                ...localChoice,
                status: 'disabled',
                reasonCode: globalReasonCode,
            };
        }

        const matchingEntries = backendEntriesByKey.get(localChoice.key);
        if (!matchingEntries || matchingEntries.length === 0) {
            return {
                ...localChoice,
                status: 'disabled',
                reasonCode: 'backend_entry_missing',
            };
        }
        if (matchingEntries.length !== 1) {
            return {
                ...localChoice,
                status: 'disabled',
                reasonCode: 'duplicate_backend_entry',
            };
        }

        const backendEntry = matchingEntries[0];
        const reasonCode = findEntryMismatch(localChoice, backendEntry);
        return {
            ...localChoice,
            status: reasonCode === null ? 'compatible' : 'disabled',
            reasonCode,
            backendEntry,
        };
    });
    const selectableChoices = choices.filter((choice) => choice.status === 'compatible');
    const reasonCodes = collectReasonCodes(choices, backendOnlyEntries);

    return {
        status: reasonCodes.length === 0 ? 'compatible' : 'disabled',
        choices,
        selectableChoices,
        backendOnlyEntries,
        reasonCodes,
    };
}

export type AiExportCatalogFetcher = () => Promise<AiExportBackendCatalogResponse>;

export async function fetchBackendAiExportCatalog(fetcher: typeof fetch = fetch): Promise<AiExportBackendCatalogResponse> {
    const response = await fetcher('/api/v1/ai-export/catalog', {
        credentials: 'same-origin',
        headers: {Accept: 'application/json'},
    });
    if (!response.ok) {
        throw new AiExportCatalogHttpError(response.status, response.statusText);
    }

    const rawCatalog: unknown = await response.json();
    const presentationFields = findBackendCatalogPresentationFields(rawCatalog);
    if (presentationFields.length > 0) {
        throw new AiExportCatalogPresentationDriftError(presentationFields);
    }

    return schemas.AiExportCatalogResponse.parse(rawCatalog);
}

export class AiExportCatalogLoader {
    private cachedResult: AiExportCatalogCompatibilityResult | undefined;
    private inFlight: Promise<AiExportCatalogCompatibilityResult> | undefined;
    private generation = 0;

    constructor(private readonly fetchCatalog: AiExportCatalogFetcher = fetchBackendAiExportCatalog) {}

    load(): Promise<AiExportCatalogCompatibilityResult> {
        if (this.cachedResult) return Promise.resolve(this.cachedResult);
        if (this.inFlight) return this.inFlight;

        const generation = this.generation;
        const request = this.fetchCatalog().then((catalog) => {
            const result = reconcileAiExportCatalog(catalog);
            if (generation === this.generation) this.cachedResult = result;
            return result;
        });
        this.inFlight = request;
        request.then(
            () => {
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
        this.generation += 1;
        this.cachedResult = undefined;
        this.inFlight = undefined;
    }
}

export const aiExportCatalogLoader = new AiExportCatalogLoader();
