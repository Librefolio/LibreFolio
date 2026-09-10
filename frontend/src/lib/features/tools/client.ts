import {isAxiosError} from 'axios';
import {axiosInstance} from '$lib/api';
import {toolTransportSchemas} from '$lib/api/generated-tools';
import {
    ToolClientError,
    assertToolAccount,
    getToolAccountState,
    parseToolCodec,
    prepareToolRun,
    runToolSessionTask,
    validateToolCatalog,
    validateToolDiagnostics,
    type CompatibleToolDescriptor,
    type ToolBatchSummary,
    type ToolCode,
    type ToolComputeRequest,
    type ToolComputeResponse,
    type ToolDiagnosticsResponse,
    type ToolInput,
    type ToolOutput,
    type ToolVersion,
    type ToolWireResult,
    type VerifiedToolCatalog,
} from './contracts';

export {ToolClientError} from './contracts';

export interface ToolReadOptions {
    signal?: AbortSignal;
}

export interface ToolRunOptions<C extends ToolCode, V extends ToolVersion<C>> {
    descriptor: CompatibleToolDescriptor<C, V>;
    correlationId: ToolComputeRequest['items'][number]['correlation_id'];
    parameters: ToolInput<C, V>;
    signal?: AbortSignal;
}

type ResultContext<C extends ToolCode, V extends ToolVersion<C>> = {
    readonly tool_code: C;
    readonly contract_version: V;
    readonly accountGeneration: number;
    readonly batch: ToolBatchSummary;
};

export type ToolItemResult<C extends ToolCode, V extends ToolVersion<C>> =
    | (Omit<Extract<ToolWireResult, {status: 'success'}>, 'tool_code' | 'contract_version' | 'result'>
        & ResultContext<C, V> & {readonly result: ToolOutput<C, V>})
    | (Omit<Extract<ToolWireResult, {status: 'error'}>, 'tool_code' | 'contract_version'>
        & ResultContext<C, V>);

type ExpectedBatch = Pick<ToolComputeRequest, 'request_id'> & {
    items: readonly Omit<ToolComputeRequest['items'][number], 'parameters'>[];
};

function assertResponseCurrent(accountGeneration: number, signal: AbortSignal): void {
    assertToolAccount(accountGeneration);
    if (signal.aborted) throw new ToolClientError('aborted', 'waiting_stopped');
}

function safeTransportError(error: unknown, accountGeneration: number): ToolClientError {
    assertToolAccount(accountGeneration);
    if (error instanceof ToolClientError) return error;
    if (isAxiosError<unknown>(error)) {
        if (error.code === 'ERR_CANCELED') return new ToolClientError('aborted', 'waiting_stopped');
        if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
            return new ToolClientError('timeout', 'transport_timeout');
        }
        const status = error.response?.status;
        if (status === 401) return new ToolClientError('authentication', 'authentication_required', {httpStatus: status});
        if (status === 403) return new ToolClientError('authentication', 'access_denied', {httpStatus: status});
        if (status !== undefined && Number.isInteger(status) && status >= 100 && status <= 599) {
            return new ToolClientError('http', 'request_rejected', {httpStatus: status});
        }
        return new ToolClientError('network', 'network_failed');
    }
    // Never retain the Axios error, response body, message, headers or request config.
    return new ToolClientError('internal', 'unexpected_transport_error');
}

export async function fetchToolCatalog({signal}: ToolReadOptions = {}): Promise<VerifiedToolCatalog> {
    const {generation} = getToolAccountState();
    try {
        return await runToolSessionTask(generation, async (requestSignal) => {
            const response = await axiosInstance.get<unknown>('/api/v1/tools/catalog', {signal: requestSignal});
            assertResponseCurrent(generation, requestSignal);
            return validateToolCatalog(response.data, generation);
        }, signal);
    } catch (error) {
        throw safeTransportError(error, generation);
    }
}

export async function fetchToolDiagnostics({signal}: ToolReadOptions = {}): Promise<ToolDiagnosticsResponse> {
    const {generation} = getToolAccountState();
    try {
        return await runToolSessionTask(generation, async (requestSignal) => {
            const response = await axiosInstance.get<unknown>('/api/v1/tools/diagnostics', {signal: requestSignal});
            assertResponseCurrent(generation, requestSignal);
            return validateToolDiagnostics(response.data, generation);
        }, signal);
    } catch (error) {
        throw safeTransportError(error, generation);
    }
}

function newRequestId(): string {
    try {
        // Unlike randomUUID(), getRandomValues() also works on self-hosted HTTP origins.
        const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16));
        return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
    } catch {
        throw new ToolClientError('environment', 'request_id_unavailable');
    }
}

function encodeRequest(request: unknown): string {
    try {
        const encoded = JSON.stringify(request);
        if (typeof encoded === 'string') return encoded;
    } catch {
        throw new ToolClientError('validation', 'invalid_request');
    }
    throw new ToolClientError('validation', 'invalid_request');
}

function validateBatchResponse(raw: unknown, expected: ExpectedBatch): ToolComputeResponse {
    const batch = parseToolCodec(toolTransportSchemas.computeResponse, raw, 'protocol', 'invalid_response');
    if (batch.request_id !== expected.request_id) {
        throw new ToolClientError('protocol', 'response_identity_mismatch');
    }
    if (batch.results.length !== expected.items.length) {
        throw new ToolClientError('protocol', 'response_count_mismatch');
    }
    const executions = new Set<string>();
    for (const [index, result] of batch.results.entries()) {
        const item = expected.items[index];
        if (!item
            || result.correlation_id !== item.correlation_id
            || result.tool_code !== item.tool_code
            || result.contract_version !== item.contract_version
            || result.implementation_version !== item.implementation_version
            || result.schema_fingerprint !== item.schema_fingerprint) {
            throw new ToolClientError('protocol', 'response_identity_mismatch');
        }
        if (result.execution_id !== null) {
            if (executions.has(result.execution_id)) {
                throw new ToolClientError('protocol', 'response_identity_mismatch');
            }
            executions.add(result.execution_id);
        }
        if (result.status === 'error' && result.error.issue_count < result.error.issues.length) {
            throw new ToolClientError('protocol', 'invalid_response');
        }
    }
    const successes = batch.results.filter((result) => result.status === 'success').length;
    if (batch.success_count !== successes || batch.failed_count !== batch.results.length - successes) {
        throw new ToolClientError('protocol', 'response_count_mismatch');
    }
    return batch;
}

/** A stopped wait is not a server cancellation acknowledgement. No retries or toasts are performed here. */
export async function runTool<const C extends ToolCode, const V extends ToolVersion<C>>(
    code: C,
    version: V,
    options: ToolRunOptions<NoInfer<C>, NoInfer<V>>,
): Promise<ToolItemResult<C, V>> {
    const {descriptor, correlationId, parameters, signal} = options;
    if (signal?.aborted) throw new ToolClientError('aborted', 'waiting_stopped');
    const context = prepareToolRun(code, version, descriptor, parameters);
    const request = {
        request_id: newRequestId(),
        items: [{
            correlation_id: correlationId,
            tool_code: code,
            contract_version: version,
            implementation_version: descriptor.implementation_version,
            schema_fingerprint: descriptor.schema_fingerprint,
            parameters,
        }],
    };
    // Validate structure, but serialize the original parameters without parser-added defaults.
    parseToolCodec(toolTransportSchemas.computeRequest, request, 'validation', 'invalid_request');
    const body = encodeRequest(request);
    try {
        return await runToolSessionTask(context.accountGeneration, async (requestSignal) => {
            const response = await axiosInstance.post<unknown>('/api/v1/tools/compute', request, {
                signal: requestSignal,
                timeout: context.clientTimeoutMs,
                headers: {'Content-Type': 'application/json'},
                // Keep the raw-wire snapshot stable across asynchronous request interceptors.
                transformRequest: [() => body],
            });
            assertResponseCurrent(context.accountGeneration, requestSignal);
            const {results, ...batch} = validateBatchResponse(response.data, request);
            const item = results[0];
            if (!item) throw new ToolClientError('protocol', 'response_count_mismatch');
            const identity = {
                tool_code: code,
                contract_version: version,
                accountGeneration: context.accountGeneration,
                batch,
            };
            if (item.status === 'success') {
                return {...item, ...identity, result: context.decodeOutput(item.result)};
            }
            return {...item, ...identity};
        }, signal);
    } catch (error) {
        throw safeTransportError(error, context.accountGeneration);
    }
}
