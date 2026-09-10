import type {z} from 'zod';
import {toolTransportSchemas} from '$lib/api/generated-tools';
import {toolContractMap, type ToolCode, type ToolInput, type ToolOutput, type ToolVersion} from '$lib/api/tool-contract-map.generated';
import {clientSessionUserId, getClientSessionGeneration, getClientSessionUserId, registerClientSessionReset} from '$lib/stores/app/clientSession';

export type {ToolCode, ToolContractMap, ToolInput, ToolOutput, ToolVersion} from '$lib/api/tool-contract-map.generated';

export type ToolCatalogResponse = z.output<typeof toolTransportSchemas.catalog>;
export type ToolDiagnosticsResponse = z.output<typeof toolTransportSchemas.diagnostics>;
export type ToolComputeRequest = z.input<typeof toolTransportSchemas.computeRequest>;
export type ToolComputeResponse = z.output<typeof toolTransportSchemas.computeResponse>;
export type ToolDescriptor = ToolCatalogResponse['items'][number];
export type ToolPlatformPolicy = ToolCatalogResponse['policy'];
export type ToolWireResult = ToolComputeResponse['results'][number];
export type ToolItemMetrics = ToolWireResult['metrics'];
export type ToolBatchMetrics = ToolComputeResponse['metrics'];
export type ToolBatchSummary = Omit<ToolComputeResponse, 'results'>;

export type ToolClientErrorKind = 'authentication' | 'session' | 'aborted' | 'timeout' | 'network' | 'http' | 'internal' | 'validation' | 'protocol' | 'compatibility' | 'renderer' | 'environment';

export type ToolCompatibilityCode = 'tool_not_installed' | 'tool_unavailable' | 'contract_not_compiled' | 'contract_mismatch' | 'schema_mismatch' | 'ui_mismatch' | 'operation_mismatch';

export type ToolClientErrorCode =
    | ToolCompatibilityCode
    | 'authentication_required'
    | 'access_denied'
    | 'session_changed'
    | 'waiting_stopped'
    | 'transport_timeout'
    | 'network_failed'
    | 'unexpected_transport_error'
    | 'unexpected_ui_error'
    | 'request_rejected'
    | 'invalid_catalog'
    | 'invalid_diagnostics'
    | 'invalid_request'
    | 'invalid_parameters'
    | 'invalid_response'
    | 'invalid_output'
    | 'catalog_unverified'
    | 'descriptor_unverified'
    | 'response_identity_mismatch'
    | 'response_count_mismatch'
    | 'request_id_unavailable'
    | 'renderer_missing'
    | 'renderer_registration_invalid'
    | 'renderer_collision'
    | 'renderer_load_failed'
    | 'renderer_mount_failed'
    | 'renderer_unmount_failed';

export interface ToolClientIssue {
    readonly code: z.ZodIssue['code'];
    readonly path: readonly (number | '$field')[];
}

export class ToolClientError extends Error {
    readonly kind: ToolClientErrorKind;
    readonly code: ToolClientErrorCode;
    readonly httpStatus: number | undefined;
    readonly issues: readonly ToolClientIssue[];
    readonly issueCount: number;

    constructor(kind: ToolClientErrorKind, code: ToolClientErrorCode, options: {httpStatus?: number; issues?: readonly ToolClientIssue[]; issueCount?: number} = {}) {
        super(code);
        this.name = 'ToolClientError';
        this.kind = kind;
        this.code = code;
        this.httpStatus = options.httpStatus;
        this.issues = Object.freeze([...(options.issues ?? [])]);
        this.issueCount = options.issueCount ?? this.issues.length;
    }
}

export function parseToolCodec<Output, Input>(codec: z.ZodType<Output, z.ZodTypeDef, Input>, value: unknown, kind: 'protocol' | 'validation', code: ToolClientErrorCode): Output {
    try {
        const parsed = codec.safeParse(value);
        if (parsed.success) return parsed.data;
        const issues = parsed.error.issues.slice(0, 32).map(
            (issue): ToolClientIssue => ({
                code: issue.code,
                // Dictionary keys and Zod messages can contain scenario values.
                path: Object.freeze(issue.path.slice(0, 16).map((part): number | '$field' => (typeof part === 'number' && Number.isSafeInteger(part) && part >= 0 ? part : '$field'))),
            }),
        );
        throw new ToolClientError(kind, code, {issues, issueCount: parsed.error.issues.length});
    } catch (error) {
        if (error instanceof ToolClientError) throw error;
        throw new ToolClientError(kind, code);
    }
}

const catalogBrand: unique symbol = Symbol('verified-tool-catalog');
const descriptorBrand: unique symbol = Symbol('compatible-tool-descriptor');

export type VerifiedToolCatalog = Readonly<ToolCatalogResponse> & {
    readonly [catalogBrand]: number;
};

export type VerifiedToolDescriptor = Readonly<ToolDescriptor> & {
    readonly [descriptorBrand]: number;
};

export type CompatibleToolDescriptor<C extends ToolCode, V extends ToolVersion<C>> = VerifiedToolDescriptor & {readonly tool_code: C; readonly contract_version: V};

// A read-only view of compiled entries, not a replacement transport/domain schema.
export interface CompiledToolContract {
    readonly toolCode: string;
    readonly contractVersion: string;
    readonly schemaFingerprint: string;
    readonly componentKey: string;
    readonly uiContractVersion: number;
    readonly input: z.ZodType<unknown>;
    readonly output: z.ZodType<unknown>;
    readonly operations: readonly string[];
}

const compiledContracts: Readonly<Record<string, Readonly<Record<string, CompiledToolContract>>>> = toolContractMap;

interface DescriptorContext {
    readonly accountGeneration: number;
    readonly policy: ToolPlatformPolicy;
    readonly contract: CompiledToolContract;
}

let metadataGeneration = -1;
let catalogs = new WeakMap<VerifiedToolCatalog, ToolPlatformPolicy>();
let descriptors = new WeakMap<VerifiedToolDescriptor, DescriptorContext>();
let observerSequence = 0;

export interface ToolAccountState {
    readonly generation: number;
    readonly authenticated: boolean;
}

export function getToolAccountState(): ToolAccountState {
    const generation = getClientSessionGeneration();
    if (generation !== metadataGeneration) {
        catalogs = new WeakMap();
        descriptors = new WeakMap();
        metadataGeneration = generation;
    }
    return {generation, authenticated: getClientSessionUserId() !== null};
}

export function assertToolAccount(accountGeneration: number): void {
    const account = getToolAccountState();
    if (account.generation !== accountGeneration) throw new ToolClientError('session', 'session_changed');
    if (!account.authenticated) throw new ToolClientError('authentication', 'authentication_required');
}

export function observeToolAccount(listener: (account: ToolAccountState) => void): () => void {
    let previous: ToolAccountState | undefined;
    let active = true;
    const publish = () => {
        if (!active) return;
        const current = getToolAccountState();
        if (previous?.generation === current.generation && previous.authenticated === current.authenticated) return;
        previous = current;
        listener(current);
    };
    const unregister = registerClientSessionReset(`tools.account.${++observerSequence}`, publish);
    let unsubscribe = () => {};
    try {
        // The first resolved identity changes the store but does not run resetters.
        unsubscribe = clientSessionUserId.subscribe(publish);
    } catch (error) {
        active = false;
        unregister();
        throw error;
    }
    return () => {
        active = false;
        unregister();
        unsubscribe();
    };
}

export async function runToolSessionTask<T>(accountGeneration: number, operation: (signal: AbortSignal) => Promise<T>, signal?: AbortSignal): Promise<T> {
    assertToolAccount(accountGeneration);
    if (signal?.aborted) throw new ToolClientError('aborted', 'waiting_stopped');
    const controller = new AbortController();
    let stopReason: ToolClientError | undefined;
    let rejectStopped: (error: ToolClientError) => void = () => {};
    const stopped = new Promise<never>((_resolve, reject) => {
        rejectStopped = reject;
    });
    const stop = (reason: ToolClientError) => {
        if (stopReason) return;
        stopReason = reason;
        controller.abort();
        rejectStopped(reason);
    };
    const onAbort = () => stop(new ToolClientError('aborted', 'waiting_stopped'));
    let unobserve = () => {};
    try {
        signal?.addEventListener('abort', onAbort, {once: true});
        unobserve = observeToolAccount((account) => {
            if (account.generation !== accountGeneration || !account.authenticated) {
                stop(new ToolClientError('session', 'session_changed'));
            }
        });
        if (signal?.aborted) onAbort();
        const work = Promise.resolve().then(() => {
            assertToolAccount(accountGeneration);
            if (stopReason) throw stopReason;
            return operation(controller.signal);
        });
        const result = await Promise.race([work, stopped]);
        assertToolAccount(accountGeneration);
        if (stopReason) throw stopReason;
        return result;
    } finally {
        signal?.removeEventListener('abort', onAbort);
        unobserve();
    }
}

function freezeSnapshot<T>(value: T): T {
    if (value !== null && typeof value === 'object') {
        for (const child of Object.values(value)) freezeSnapshot(child);
        Object.freeze(value);
    }
    return value;
}

function assertDistinctToolCodes(items: readonly ToolDescriptor[], code: 'invalid_catalog' | 'invalid_diagnostics'): void {
    if (new Set(items.map((item) => item.tool_code)).size !== items.length) {
        throw new ToolClientError('protocol', code);
    }
}

export function validateToolCatalog(raw: unknown, accountGeneration: number): VerifiedToolCatalog {
    assertToolAccount(accountGeneration);
    const parsed = parseToolCodec(toolTransportSchemas.catalog, raw, 'protocol', 'invalid_catalog');
    assertDistinctToolCodes(parsed.items, 'invalid_catalog');
    const available = new Set(parsed.items.map((item) => item.tool_code));
    if (parsed.unavailable.some((item) => item.tool_code !== null && available.has(item.tool_code))) {
        throw new ToolClientError('protocol', 'invalid_catalog');
    }
    const catalog = freezeSnapshot({...parsed, [catalogBrand]: accountGeneration});
    catalogs.set(catalog, catalog.policy);
    return catalog;
}

export function validateToolDiagnostics(raw: unknown, accountGeneration: number): ToolDiagnosticsResponse {
    assertToolAccount(accountGeneration);
    const parsed = parseToolCodec(toolTransportSchemas.diagnostics, raw, 'protocol', 'invalid_diagnostics');
    assertDistinctToolCodes(parsed.loaded, 'invalid_diagnostics');
    return freezeSnapshot(parsed);
}

function requireCatalog(catalog: VerifiedToolCatalog): ToolPlatformPolicy {
    if (!catalog || typeof catalog !== 'object' || !Object.hasOwn(catalog, catalogBrand)) {
        throw new ToolClientError('compatibility', 'catalog_unverified');
    }
    assertToolAccount(catalog[catalogBrand]);
    const policy = catalogs.get(catalog);
    if (!policy) throw new ToolClientError('compatibility', 'catalog_unverified');
    return policy;
}

export function getCompiledToolContract(code: string, version: string): CompiledToolContract | undefined {
    if (!Object.hasOwn(compiledContracts, code)) return undefined;
    const versions = compiledContracts[code];
    if (!versions || !Object.hasOwn(versions, version)) return undefined;
    const contract = versions[version];
    if (contract?.toolCode !== code || contract.contractVersion !== version) return undefined;
    return contract;
}

export type ToolCompatibility = {readonly status: 'compatible'; readonly descriptor: ToolDescriptor; readonly contract: CompiledToolContract} | {readonly status: 'unavailable'; readonly reason: ToolCompatibilityCode};

export function inspectToolCompatibility(catalog: VerifiedToolCatalog, toolCode: string): ToolCompatibility {
    requireCatalog(catalog);
    const descriptor = catalog.items.find((item) => item.tool_code === toolCode);
    if (!descriptor) {
        return {
            status: 'unavailable',
            reason: catalog.unavailable.some((item) => item.tool_code === toolCode) ? 'tool_unavailable' : 'tool_not_installed',
        };
    }
    const contract = getCompiledToolContract(descriptor.tool_code, descriptor.contract_version);
    if (!contract) return {status: 'unavailable', reason: 'contract_not_compiled'};
    if (descriptor.schema_fingerprint !== contract.schemaFingerprint) return {status: 'unavailable', reason: 'schema_mismatch'};
    if (descriptor.ui.kind !== 'custom' || descriptor.ui.component_key !== contract.componentKey || descriptor.ui.ui_contract_version !== contract.uiContractVersion) {
        return {status: 'unavailable', reason: 'ui_mismatch'};
    }
    const operations = new Set(descriptor.operations.map((operation) => operation.operation));
    if (operations.size !== descriptor.operations.length || operations.size !== contract.operations.length || !contract.operations.every((operation) => operations.has(operation))) {
        return {status: 'unavailable', reason: 'operation_mismatch'};
    }
    return {status: 'compatible', descriptor, contract};
}

export function verifyToolDescriptor<C extends ToolCode, V extends ToolVersion<C>>(catalog: VerifiedToolCatalog, code: C, version: V): CompatibleToolDescriptor<C, V> {
    const policy = requireCatalog(catalog);
    const compatibility = inspectToolCompatibility(catalog, code);
    if (compatibility.status === 'unavailable') throw new ToolClientError('compatibility', compatibility.reason);
    if (compatibility.descriptor.contract_version !== version) throw new ToolClientError('compatibility', 'contract_mismatch');
    const descriptor: CompatibleToolDescriptor<C, V> = Object.freeze({
        ...compatibility.descriptor,
        tool_code: code,
        contract_version: version,
        [descriptorBrand]: catalog[catalogBrand],
    });
    descriptors.set(descriptor, {
        accountGeneration: catalog[catalogBrand],
        policy,
        contract: compatibility.contract,
    });
    return descriptor;
}

export function getToolDescriptorGeneration(descriptor: VerifiedToolDescriptor): number {
    if (!descriptor || typeof descriptor !== 'object' || !Object.hasOwn(descriptor, descriptorBrand)) {
        throw new ToolClientError('compatibility', 'descriptor_unverified');
    }
    assertToolAccount(descriptor[descriptorBrand]);
    const context = descriptors.get(descriptor);
    if (!context) throw new ToolClientError('compatibility', 'descriptor_unverified');
    return context.accountGeneration;
}

export function prepareToolRun<C extends ToolCode, V extends ToolVersion<C>>(
    code: C,
    version: V,
    descriptor: CompatibleToolDescriptor<C, V>,
): {
    accountGeneration: number;
    clientTimeoutMs: number;
    validateInput: (raw: unknown) => void;
    decodeOutput: (raw: unknown) => ToolOutput<C, V>;
} {
    const accountGeneration = getToolDescriptorGeneration(descriptor);
    const context = descriptors.get(descriptor);
    if (!context) throw new ToolClientError('compatibility', 'descriptor_unverified');
    if (descriptor.tool_code !== code || descriptor.contract_version !== version) {
        throw new ToolClientError('compatibility', 'contract_mismatch');
    }
    return {
        accountGeneration,
        clientTimeoutMs: context.policy.client_timeout_ms,
        validateInput(raw) {
            assertToolAccount(accountGeneration);
            parseToolCodec(context.contract.input, raw, 'validation', 'invalid_parameters');
        },
        decodeOutput(raw) {
            assertToolAccount(accountGeneration);
            const output = parseToolCodec(context.contract.output, raw, 'protocol', 'invalid_output');
            // Runtime identity/fingerprint checks select this exact generated codec.
            // The read-only runtime table erases C/V; only this checked boundary restores them.
            return output as ToolOutput<C, V>;
        },
    };
}
