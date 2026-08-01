import {ZodiosError} from '@zodios/core';
import {isAxiosError} from 'axios';
import {z, ZodError} from 'zod';

import {schemas, zodiosApi} from '$lib/api';

import {AI_EXPORT_SCHEMA_VERSION, normalizeAiExportSnapshotResponse, type AiExportCompatibleSelection, type AiExportSnapshotResponse} from './catalog/shared';

export type AiExportSnapshotRequestInput = z.input<typeof schemas.build_ai_export_snapshot_api_v1_ai_export_snapshot_post_Body>;
export type AiExportProblemDetail = z.output<typeof schemas.AiExportProblemResponse>['detail'];
export type AiExportHttpValidationResponse = z.output<typeof schemas.HTTPValidationError>;

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
export type AiExportSnapshotTransport = (request: AiExportSnapshotRequestInput) => Promise<unknown>;

const generatedAiExportSnapshotTransport: AiExportSnapshotTransport = (request) => zodiosApi.build_ai_export_snapshot_api_v1_ai_export_snapshot_post(request);

function canonicalCurrency(value: string): string {
    return value.trim().toUpperCase();
}

function canonicalBrokerIds(values: number[] | undefined): number[] | undefined {
    return values ? [...new Set(values)].sort((left, right) => left - right) : undefined;
}

export function canonicalizeAiExportSnapshotRequest(request: AiExportSnapshotRequestInput): AiExportSnapshotRequestInput {
    const targetCurrency = canonicalCurrency(request.target_currency);
    const period = {...request.period};
    const selection = {...request.selection};
    if (request.domain === 'portfolio') {
        return {
            domain: 'portfolio',
            selection,
            detail_level: request.detail_level,
            period,
            target_currency: targetCurrency,
            expected_catalog_version: request.expected_catalog_version,
            broker_ids: canonicalBrokerIds(request.broker_ids),
        };
    }
    if (request.domain === 'broker') {
        return {
            domain: 'broker',
            selection,
            detail_level: request.detail_level,
            period,
            target_currency: targetCurrency,
            expected_catalog_version: request.expected_catalog_version,
            broker_id: request.broker_id,
        };
    }
    if (request.domain === 'asset') {
        return {
            domain: 'asset',
            selection,
            detail_level: request.detail_level,
            period,
            target_currency: targetCurrency,
            expected_catalog_version: request.expected_catalog_version,
            asset_id: request.asset_id,
            broker_ids: canonicalBrokerIds(request.broker_ids),
        };
    }
    if (request.domain === 'fx') {
        return {
            domain: 'fx',
            selection,
            detail_level: request.detail_level,
            period,
            target_currency: targetCurrency,
            expected_catalog_version: request.expected_catalog_version,
            base_currency: canonicalCurrency(request.base_currency),
            quote_currency: canonicalCurrency(request.quote_currency),
            broker_ids: canonicalBrokerIds(request.broker_ids),
        };
    }
    return request;
}

export function normalizeAiExportClientError(error: unknown): Exclude<AiExportClientError, AiExportContractMismatchError> {
    if (error instanceof AiExportProblemError || error instanceof AiExportValidationError || error instanceof AiExportNetworkError || error instanceof AiExportUnknownError) return error;
    if (error instanceof ZodiosError) return new AiExportValidationError('response', undefined, error, error);
    if (error instanceof ZodError) return new AiExportValidationError('response', undefined, error, error);
    if (isAxiosError(error)) {
        const status = error.response?.status;
        const responseData = error.response?.data;
        const problemResult = schemas.AiExportProblemResponse.safeParse(responseData);
        if (status !== undefined && problemResult.success) return new AiExportProblemError(status, problemResult.data.detail, error);
        const validationResult = schemas.HTTPValidationError.safeParse(responseData);
        if (status !== undefined && validationResult.success && validationResult.data.detail !== undefined) return new AiExportValidationError('http', status, validationResult.data, error);
        if (error.response === undefined) return new AiExportNetworkError(error.message || 'AI Export network request failed', error.code, error);
        return new AiExportUnknownError(error.message || 'AI Export HTTP request failed', status, error);
    }
    return new AiExportUnknownError(error instanceof Error ? error.message : 'Unknown AI Export error', undefined, error);
}

function addMismatch(mismatches: AiExportContractMismatch[], field: string, expected: AiExportContractValue, actual: AiExportContractValue): void {
    if (expected !== actual) mismatches.push({field, expected, actual});
}

function assertRequestMatchesSelection(request: AiExportSnapshotRequestInput, selection: AiExportCompatibleSelection): void {
    const mismatches: AiExportContractMismatch[] = [];
    addMismatch(mismatches, 'request.domain', selection.domain, request.domain);
    addMismatch(mismatches, 'request.selection.kind', selection.kind, request.selection.kind);
    addMismatch(mismatches, 'request.selection.id', selection.id, request.selection.id);
    addMismatch(mismatches, 'request.selection.version', selection.version, request.selection.version);
    if (!selection.supportedDetailLevels.includes(request.detail_level)) mismatches.push({field: 'request.detail_level', expected: selection.supportedDetailLevels.join(','), actual: request.detail_level});
    if (selection.kind === 'analysis' && request.selection.kind === 'analysis' && selection.entry.kind === 'analysis') {
        addMismatch(mismatches, 'request.selection.instruction_template_id', selection.entry.instruction_template_id, request.selection.instruction_template_id);
        addMismatch(mismatches, 'request.selection.instruction_template_version', selection.entry.instruction_template_version, request.selection.instruction_template_version);
        addMismatch(mismatches, 'request.selection.response_contract_id', selection.entry.response_contract_id, request.selection.response_contract_id);
        addMismatch(mismatches, 'request.selection.response_contract_version', selection.entry.response_contract_version, request.selection.response_contract_version);
    }
    if (mismatches.length) throw new AiExportContractMismatchError(mismatches);
}

function assertResponseMatchesRequest(request: AiExportSnapshotRequestInput, response: AiExportSnapshotResponse): void {
    const mismatches: AiExportContractMismatch[] = [];
    addMismatch(mismatches, 'response.domain', request.domain, response.domain);
    addMismatch(mismatches, 'response.selection.kind', request.selection.kind, response.selection.kind);
    addMismatch(mismatches, 'response.selection.id', request.selection.id, response.selection.id);
    addMismatch(mismatches, 'response.selection.version', request.selection.version, response.selection.version);
    addMismatch(mismatches, 'response.detail_level', request.detail_level, response.detail_level);
    addMismatch(mismatches, 'response.meta.schema_version', AI_EXPORT_SCHEMA_VERSION, response.meta.schema_version ?? null);
    addMismatch(mismatches, 'response.meta.catalog_version', request.expected_catalog_version, response.meta.catalog_version ?? null);
    addMismatch(mismatches, 'response.meta.target_currency', request.target_currency, response.meta.target_currency);
    addMismatch(mismatches, 'response.meta.exported_period.start', request.period.start, response.meta.exported_period.start);
    addMismatch(mismatches, 'response.meta.exported_period.end', request.period.end, response.meta.exported_period.end);
    if (mismatches.length) throw new AiExportContractMismatchError(mismatches);
}

export async function fetchAiExportSnapshot(request: AiExportSnapshotRequestInput, selection: AiExportCompatibleSelection, transport: AiExportSnapshotTransport = generatedAiExportSnapshotTransport): Promise<AiExportSnapshotResponse> {
    const canonicalRequest = canonicalizeAiExportSnapshotRequest(request);
    const requestResult = schemas.build_ai_export_snapshot_api_v1_ai_export_snapshot_post_Body.safeParse(canonicalRequest);
    if (!requestResult.success) throw new AiExportValidationError('request', undefined, requestResult.error, requestResult.error);
    assertRequestMatchesSelection(requestResult.data, selection);

    let rawResponse: unknown;
    try {
        rawResponse = await transport(requestResult.data);
    } catch (error) {
        throw normalizeAiExportClientError(error);
    }
    const responseResult = schemas.AiExportSnapshotResponse.safeParse(rawResponse);
    if (!responseResult.success) throw new AiExportValidationError('response', undefined, responseResult.error, responseResult.error);
    const response = normalizeAiExportSnapshotResponse(responseResult.data);
    assertResponseMatchesRequest(requestResult.data, response);
    return response;
}
