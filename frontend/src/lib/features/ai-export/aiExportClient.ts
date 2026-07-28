import {ZodiosError} from '@zodios/core';
import {isAxiosError} from 'axios';
import {z, ZodError} from 'zod';

import {schemas, zodiosApi} from '$lib/api';

import {AI_EXPORT_TASK_CATALOG} from './catalog/compatibility';
import type {AiExportCatalogCompatibilityChoice} from './catalog/compatibility';
import {AI_EXPORT_SNAPSHOT_SCHEMA_VERSION, type AiExportBackendCatalogEntry} from './catalog/shared';
import {findAiExportResponseContract} from './templates/responseContracts';

type AiExportGeneratedDomain = z.infer<typeof schemas.AiExportDomain>;
type AiExportGeneratedDetailLevel = z.infer<typeof schemas.AiExportDetailLevel>;
type AiExportPortfolioTask = z.infer<typeof schemas.AiExportPortfolioTask>;
type AiExportAssetTask = z.infer<typeof schemas.AiExportAssetTask>;
type AiExportFxTask = z.infer<typeof schemas.AiExportFxTask>;
type AiExportBrokerTask = z.infer<typeof schemas.AiExportBrokerTask>;

export interface AiExportDateRangeInput {
    start: string;
    end?: string | null;
}

interface AiExportSnapshotRequestInputBase<D extends AiExportGeneratedDomain, T> {
    domain: D;
    task: T;
    detail_level: AiExportGeneratedDetailLevel;
    date_range: AiExportDateRangeInput;
    technical_window?: AiExportDateRangeInput | null;
    target_currency: string;
}

export interface AiExportPortfolioSnapshotRequestInput extends AiExportSnapshotRequestInputBase<Extract<AiExportGeneratedDomain, 'portfolio'>, AiExportPortfolioTask> {
    broker_ids?: number[] | null | undefined;
}

export interface AiExportAssetSnapshotRequestInput extends AiExportSnapshotRequestInputBase<Extract<AiExportGeneratedDomain, 'asset'>, AiExportAssetTask> {
    asset_id: number;
    broker_ids?: number[] | null | undefined;
}

export interface AiExportFxSnapshotRequestInput extends AiExportSnapshotRequestInputBase<Extract<AiExportGeneratedDomain, 'fx'>, AiExportFxTask> {
    base_currency: string;
    quote_currency: string;
    broker_ids?: number[] | null | undefined;
}

export interface AiExportBrokerSnapshotRequestInput extends AiExportSnapshotRequestInputBase<Extract<AiExportGeneratedDomain, 'broker'>, AiExportBrokerTask> {
    broker_id: number;
}

export type AiExportSnapshotRequestInput = AiExportPortfolioSnapshotRequestInput | AiExportAssetSnapshotRequestInput | AiExportFxSnapshotRequestInput | AiExportBrokerSnapshotRequestInput;

export type AiExportSnapshotRequest = AiExportSnapshotRequestInput;
export type AiExportPortfolioSnapshotResponse = z.output<typeof schemas.AiExportPortfolioSnapshotResponse>;
export type AiExportAssetSnapshotResponse = z.output<typeof schemas.AiExportAssetSnapshotResponse>;
export type AiExportFxSnapshotResponse = z.output<typeof schemas.AiExportFxSnapshotResponse>;
export type AiExportBrokerSnapshotResponse = z.output<typeof schemas.AiExportBrokerSnapshotResponse>;
export type AiExportSnapshotResponse = AiExportPortfolioSnapshotResponse | AiExportAssetSnapshotResponse | AiExportFxSnapshotResponse | AiExportBrokerSnapshotResponse;
export type AiExportBackendExportStats = z.output<typeof schemas.AiExportExportStats>;
export type AiExportProblemDetail = z.output<typeof schemas.AiExportProblemResponse>['detail'];
export type AiExportHttpValidationResponse = z.output<typeof schemas.HTTPValidationError>;

const aiExportSnapshotRequestSchema = schemas.build_ai_export_snapshot_api_v1_ai_export_snapshot_post_Body.superRefine((request, context) => {
    if (request.domain === 'broker') return;

    const brokerIds = request.broker_ids;
    if (brokerIds === null || brokerIds === undefined) return;
    if (brokerIds.length === 0) {
        context.addIssue({
            code: z.ZodIssueCode.custom,
            message: 'broker_ids must contain at least one value',
            path: ['broker_ids'],
        });
    } else if (new Set(brokerIds).size !== brokerIds.length) {
        context.addIssue({
            code: z.ZodIssueCode.custom,
            message: 'broker_ids must contain unique values',
            path: ['broker_ids'],
        });
    }
});

export type AiExportCompatibleCatalogChoice = AiExportCatalogCompatibilityChoice & {
    readonly status: 'compatible';
    readonly reasonCode: null;
    readonly backendEntry: AiExportBackendCatalogEntry;
};

export function isAiExportCompatibleCatalogChoice(choice: AiExportCatalogCompatibilityChoice): choice is AiExportCompatibleCatalogChoice {
    return choice.status === 'compatible' && choice.reasonCode === null && choice.backendEntry !== undefined;
}

export type AiExportContractValue = string | number | boolean | null;

export interface AiExportContractMismatch {
    readonly field: string;
    readonly expected: AiExportContractValue;
    readonly actual: AiExportContractValue;
}

export class AiExportContractMismatchError extends Error {
    readonly kind = 'contract_mismatch';

    constructor(readonly mismatches: readonly AiExportContractMismatch[]) {
        super(`AI Export contract mismatch: ${mismatches.map((mismatch) => mismatch.field).join(', ')}`);
        this.name = 'AiExportContractMismatchError';
    }
}

export class AiExportProblemError extends Error {
    readonly kind = 'problem';

    constructor(
        readonly status: number,
        readonly problem: AiExportProblemDetail,
        readonly originalError: unknown,
    ) {
        super(problem.message);
        this.name = 'AiExportProblemError';
    }
}

export type AiExportValidationSource = 'request' | 'http' | 'response';
export type AiExportValidationDetails = AiExportHttpValidationResponse | ZodError | ZodiosError;

export class AiExportValidationError extends Error {
    readonly kind = 'validation';

    constructor(
        readonly source: AiExportValidationSource,
        readonly status: number | undefined,
        readonly details: AiExportValidationDetails,
        readonly originalError: unknown,
    ) {
        super(`AI Export ${source} validation failed`);
        this.name = 'AiExportValidationError';
    }
}

export class AiExportNetworkError extends Error {
    readonly kind = 'network';

    constructor(
        message: string,
        readonly code: string | undefined,
        readonly originalError: unknown,
    ) {
        super(message);
        this.name = 'AiExportNetworkError';
    }
}

export class AiExportUnknownError extends Error {
    readonly kind = 'unknown';

    constructor(
        message: string,
        readonly status: number | undefined,
        readonly originalError: unknown,
    ) {
        super(message);
        this.name = 'AiExportUnknownError';
    }
}

export type AiExportClientError = AiExportContractMismatchError | AiExportProblemError | AiExportValidationError | AiExportNetworkError | AiExportUnknownError;
export type AiExportSnapshotTransport = (request: AiExportSnapshotRequest) => Promise<AiExportSnapshotResponse>;

const generatedAiExportSnapshotTransport: AiExportSnapshotTransport = (request) => zodiosApi.build_ai_export_snapshot_api_v1_ai_export_snapshot_post(request);

export function canonicalizeAiExportSnapshotRequest(request: AiExportPortfolioSnapshotRequestInput): AiExportPortfolioSnapshotRequestInput;
export function canonicalizeAiExportSnapshotRequest(request: AiExportAssetSnapshotRequestInput): AiExportAssetSnapshotRequestInput;
export function canonicalizeAiExportSnapshotRequest(request: AiExportFxSnapshotRequestInput): AiExportFxSnapshotRequestInput;
export function canonicalizeAiExportSnapshotRequest(request: AiExportBrokerSnapshotRequestInput): AiExportBrokerSnapshotRequestInput;
export function canonicalizeAiExportSnapshotRequest(request: AiExportSnapshotRequestInput): AiExportSnapshotRequestInput;
export function canonicalizeAiExportSnapshotRequest(request: AiExportSnapshotRequestInput): AiExportSnapshotRequestInput {
    if (request === null || typeof request !== 'object') return request;

    const dateRange = canonicalizeDateRange(request.date_range);
    const technicalWindow = request.technical_window ? canonicalizeDateRange(request.technical_window) : request.technical_window;
    const targetCurrency = canonicalizeCurrency(request.target_currency);

    switch (request.domain) {
        case 'portfolio':
            return {
                ...request,
                date_range: dateRange,
                technical_window: technicalWindow,
                target_currency: targetCurrency,
                broker_ids: canonicalizeBrokerIds(request.broker_ids),
            };
        case 'asset':
            return {
                ...request,
                date_range: dateRange,
                technical_window: technicalWindow,
                target_currency: targetCurrency,
                broker_ids: canonicalizeBrokerIds(request.broker_ids),
            };
        case 'fx':
            return {
                ...request,
                date_range: dateRange,
                technical_window: technicalWindow,
                target_currency: targetCurrency,
                base_currency: canonicalizeCurrency(request.base_currency),
                quote_currency: canonicalizeCurrency(request.quote_currency),
                broker_ids: canonicalizeBrokerIds(request.broker_ids),
            };
        case 'broker':
            return {
                ...request,
                date_range: dateRange,
                technical_window: technicalWindow,
                target_currency: targetCurrency,
            };
    }

    return request;
}

function canonicalizeDateRange(dateRange: AiExportDateRangeInput): AiExportDateRangeInput {
    if (dateRange === null || typeof dateRange !== 'object' || Array.isArray(dateRange)) return dateRange;
    return {
        start: dateRange.start,
        end: dateRange.end ?? dateRange.start,
    };
}

function canonicalizeCurrency(value: string): string {
    return typeof value === 'string' ? value.trim().toUpperCase() : value;
}

function canonicalizeBrokerIds(brokerIds: number[] | null | undefined): number[] | null | undefined {
    return Array.isArray(brokerIds) ? [...brokerIds].sort((left, right) => left - right) : brokerIds;
}

export function normalizeAiExportClientError(error: unknown): Exclude<AiExportClientError, AiExportContractMismatchError> {
    if (error instanceof AiExportProblemError || error instanceof AiExportValidationError || error instanceof AiExportNetworkError || error instanceof AiExportUnknownError) {
        return error;
    }

    if (error instanceof ZodiosError) {
        return new AiExportValidationError('response', undefined, error, error);
    }

    if (error instanceof ZodError) {
        return new AiExportValidationError('response', undefined, error, error);
    }

    if (isAxiosError(error)) {
        const status = error.response?.status;
        const responseData = error.response?.data;

        const problemResult = schemas.AiExportProblemResponse.safeParse(responseData);
        if (status !== undefined && problemResult.success) {
            return new AiExportProblemError(status, problemResult.data.detail, error);
        }

        const validationResult = schemas.HTTPValidationError.safeParse(responseData);
        if (status !== undefined && validationResult.success && validationResult.data.detail !== undefined) {
            return new AiExportValidationError('http', status, validationResult.data, error);
        }

        if (error.response === undefined) {
            return new AiExportNetworkError(error.message || 'AI Export network request failed', error.code, error);
        }

        return new AiExportUnknownError(error.message || 'AI Export HTTP request failed', status, error);
    }

    const message = error instanceof Error ? error.message : 'Unknown AI Export error';
    return new AiExportUnknownError(message, undefined, error);
}

export function fetchAiExportSnapshot(request: AiExportPortfolioSnapshotRequestInput, expectedChoice: AiExportCatalogCompatibilityChoice, transport?: AiExportSnapshotTransport): Promise<AiExportPortfolioSnapshotResponse>;
export function fetchAiExportSnapshot(request: AiExportAssetSnapshotRequestInput, expectedChoice: AiExportCatalogCompatibilityChoice, transport?: AiExportSnapshotTransport): Promise<AiExportAssetSnapshotResponse>;
export function fetchAiExportSnapshot(request: AiExportFxSnapshotRequestInput, expectedChoice: AiExportCatalogCompatibilityChoice, transport?: AiExportSnapshotTransport): Promise<AiExportFxSnapshotResponse>;
export function fetchAiExportSnapshot(request: AiExportBrokerSnapshotRequestInput, expectedChoice: AiExportCatalogCompatibilityChoice, transport?: AiExportSnapshotTransport): Promise<AiExportBrokerSnapshotResponse>;
export function fetchAiExportSnapshot(request: AiExportSnapshotRequestInput, expectedChoice: AiExportCatalogCompatibilityChoice, transport?: AiExportSnapshotTransport): Promise<AiExportSnapshotResponse>;
export async function fetchAiExportSnapshot(request: AiExportSnapshotRequestInput, expectedChoice: AiExportCatalogCompatibilityChoice, transport: AiExportSnapshotTransport = generatedAiExportSnapshotTransport): Promise<AiExportSnapshotResponse> {
    const canonicalRequest = canonicalizeAiExportSnapshotRequest(request);
    const requestResult = aiExportSnapshotRequestSchema.safeParse(canonicalRequest);
    if (!requestResult.success) {
        throw new AiExportValidationError('request', undefined, requestResult.error, requestResult.error);
    }

    const normalizedRequest = requestResult.data as AiExportSnapshotRequest;
    assertCompatibleExpectedChoice(normalizedRequest, expectedChoice);

    let response: AiExportSnapshotResponse;
    try {
        response = await transport(normalizedRequest);
    } catch (error) {
        throw normalizeAiExportClientError(error);
    }

    assertSnapshotContract(normalizedRequest, expectedChoice, response);
    return response;
}

function assertCompatibleExpectedChoice(request: AiExportSnapshotRequest, choice: AiExportCatalogCompatibilityChoice): void {
    const mismatches: AiExportContractMismatch[] = [];
    const taskDefinition = AI_EXPORT_TASK_CATALOG.find((definition) => definition.domain === request.domain && definition.backendTask === request.task);
    const responseContract = findAiExportResponseContract(request.domain, request.task);

    addMismatch(mismatches, 'choice.status', 'compatible', choice.status);
    addMismatch(mismatches, 'choice.reasonCode', null, choice.reasonCode);
    addMismatch(mismatches, 'choice.domain', request.domain, choice.domain);
    addMismatch(mismatches, 'choice.taskId', request.task, choice.taskId);
    addMismatch(mismatches, 'choice.backendTask', request.task, choice.backendTask);
    addMismatch(mismatches, 'choice.detailLevel', request.detail_level, choice.detailLevel);

    if (!taskDefinition) {
        addMismatch(mismatches, 'local.taskDefinition', true, false);
    } else {
        const expectedProfile = taskDefinition.expectedProfiles[request.detail_level];
        addMismatch(mismatches, 'choice.profileId', expectedProfile.profileId, choice.profileId);
        addMismatch(mismatches, 'choice.profileVersion', expectedProfile.profileVersion, choice.profileVersion);
        addMismatch(mismatches, 'choice.frontendResponseContractId', taskDefinition.frontendResponseContract.id, choice.frontendResponseContractId);
        addMismatch(mismatches, 'choice.frontendResponseContractVersion', taskDefinition.frontendResponseContract.version, choice.frontendResponseContractVersion);
    }

    if (!responseContract) {
        addMismatch(mismatches, 'local.responseContract', true, false);
    } else {
        addMismatch(mismatches, 'choice.frontendResponseContractId', responseContract.contractId, choice.frontendResponseContractId);
        addMismatch(mismatches, 'choice.frontendResponseContractVersion', responseContract.version, choice.frontendResponseContractVersion);
    }

    if (!choice.backendEntry) {
        addMismatch(mismatches, 'choice.backendEntry', true, false);
    } else {
        addMismatch(mismatches, 'choice.backendEntry.domain', request.domain, choice.backendEntry.domain);
        addMismatch(mismatches, 'choice.backendEntry.task', request.task, choice.backendEntry.task);
        addMismatch(mismatches, 'choice.backendEntry.detail_level', request.detail_level, choice.backendEntry.detail_level);
        addMismatch(mismatches, 'choice.backendEntry.profile_id', choice.profileId, choice.backendEntry.profile_id);
        addMismatch(mismatches, 'choice.backendEntry.profile_version', choice.profileVersion, choice.backendEntry.profile_version);
        addMismatch(mismatches, 'choice.backendEntry.frontend_response_contract_id', choice.frontendResponseContractId, choice.backendEntry.frontend_response_contract_id);
        addMismatch(mismatches, 'choice.backendEntry.frontend_response_contract_version', choice.frontendResponseContractVersion, choice.backendEntry.frontend_response_contract_version);
        addMismatch(mismatches, 'choice.backendEntry.supports_user_notes', choice.supportsUserNotes, choice.backendEntry.supports_user_notes);
        addMismatch(mismatches, 'choice.backendEntry.supports_web_research', choice.supportsWebResearch, choice.backendEntry.supports_web_research);
    }

    if (mismatches.length > 0) throw new AiExportContractMismatchError(mismatches);
}

function assertSnapshotContract(request: AiExportSnapshotRequest, choice: AiExportCatalogCompatibilityChoice, response: AiExportSnapshotResponse): void {
    const mismatches: AiExportContractMismatch[] = [];
    const responseContract = findAiExportResponseContract(request.domain, request.task);

    addMismatch(mismatches, 'response.domain', request.domain, response.domain);
    addMismatch(mismatches, 'response.task', request.task, response.task);
    addMismatch(mismatches, 'response.detail_level', request.detail_level, response.detail_level);
    addMismatch(mismatches, 'response.meta.schema_version', AI_EXPORT_SNAPSHOT_SCHEMA_VERSION, response.meta.schema_version);
    addMismatch(mismatches, 'response.meta.profile_id', choice.profileId, response.meta.profile_id);
    addMismatch(mismatches, 'response.meta.profile_version', choice.profileVersion, response.meta.profile_version);

    if (!responseContract) {
        addMismatch(mismatches, 'local.responseContract', true, false);
    } else {
        addMismatch(mismatches, 'response.meta.frontend_response_contract_id', responseContract.contractId, response.meta.frontend_response_contract_id);
        addMismatch(mismatches, 'response.meta.frontend_response_contract_version', responseContract.version, response.meta.frontend_response_contract_version);
    }

    addMismatch(mismatches, 'response.meta.selected_range.start', request.date_range.start, response.meta.selected_range.start);
    addMismatch(mismatches, 'response.meta.selected_range.end', normalizeOptionalDate(request.date_range.end), normalizeOptionalDate(response.meta.selected_range.end));
    if (request.technical_window) {
        const responseTechnicalWindow = response.meta.technical_window;
        if (!responseTechnicalWindow || Array.isArray(responseTechnicalWindow)) {
            addMismatch(mismatches, 'response.meta.technical_window', true, false);
        } else {
            addMismatch(mismatches, 'response.meta.technical_window.start', request.technical_window.start, responseTechnicalWindow.start);
            addMismatch(mismatches, 'response.meta.technical_window.end', normalizeOptionalDate(request.technical_window.end), normalizeOptionalDate(responseTechnicalWindow.end));
        }
    }
    addMismatch(mismatches, 'response.meta.target_currency', request.target_currency, response.meta.target_currency);

    if (request.domain === 'asset' && response.domain === 'asset') {
        addMismatch(mismatches, 'response.facts.identity.asset_id', request.asset_id, response.facts.identity.asset_id);
    } else if (request.domain === 'fx' && response.domain === 'fx') {
        addMismatch(mismatches, 'response.facts.identity.base_currency', request.base_currency, response.facts.identity.base_currency);
        addMismatch(mismatches, 'response.facts.identity.quote_currency', request.quote_currency, response.facts.identity.quote_currency);
    } else if (request.domain === 'broker' && response.domain === 'broker') {
        addMismatch(mismatches, 'response.facts.summary.broker_id', request.broker_id, response.facts.summary.broker_id);
    }

    if (mismatches.length > 0) throw new AiExportContractMismatchError(mismatches);
}

function normalizeOptionalDate(value: unknown): string | null {
    if (value === undefined || value === null) return null;
    return typeof value === 'string' ? value : '[invalid date value]';
}

function addMismatch(mismatches: AiExportContractMismatch[], field: string, expected: AiExportContractValue | undefined, actual: AiExportContractValue | undefined): void {
    const normalizedExpected = expected ?? null;
    const normalizedActual = actual ?? null;
    if (normalizedExpected !== normalizedActual) {
        mismatches.push({
            field,
            expected: normalizedExpected,
            actual: normalizedActual,
        });
    }
}
