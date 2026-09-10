import type {z} from 'zod';
import type {schemas} from '$lib/api/generated';
import {zodiosApi} from '$lib/api';
import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
import {safeScalar, safeString} from '$lib/types/common';
import {isRealProbeError} from './providerProbe';

export interface ProviderConfiguration {
    providerCode: string;
    identifier: string;
    identifierType: string;
    providerParams: Record<string, unknown> | null;
    noProvider: boolean;
}

export type ProviderTestStatus = 'not_tested' | 'testing' | 'passed' | 'failed';
type ProbeResponse = z.infer<typeof schemas.FAProviderProbeResponse>;
type ProbeOperation = 'current_price' | 'history' | 'metadata';

export interface ProviderRequestTicket {
    readonly draft: number;
    readonly revision: number;
    readonly sequence: number;
    readonly session: number;
    readonly key: string;
    readonly configuration: ProviderConfiguration;
}

/** Object key order is irrelevant; array order and JSON values remain significant. */
export function providerConfigurationKey(configuration: ProviderConfiguration): string {
    return JSON.stringify(configuration, (_key, value: unknown) => {
        if (value === null || typeof value !== 'object' || Array.isArray(value)) return value;
        return Object.fromEntries(Object.entries(value).sort(([left], [right]) => left.localeCompare(right)));
    });
}

/** One owner per draft, shared by automatic and manual probes across panel remounts. */
export function createProviderProbeState(readConfiguration: () => ProviderConfiguration) {
    let draft = 0;
    let revision = 0;
    let probeSequence = 0;
    let metadataSequence = 0;
    let key = '';
    let alive = true;
    let status = $state<ProviderTestStatus>('not_tested');
    let response = $state<ProbeResponse | null>(null);
    let error = $state<unknown>(null);
    let source = $state<'auto' | 'manual' | null>(null);
    let url = $state<string | null>(null);
    let metadataPending = $state(false);

    function clearProbe() {
        probeSequence += 1;
        status = 'not_tested';
        response = null;
        error = null;
        source = null;
    }

    function cancelMetadata() {
        metadataSequence += 1;
        metadataPending = false;
    }

    function configure() {
        const nextKey = providerConfigurationKey(readConfiguration());
        if (key === nextKey) return false;
        key = nextKey;
        revision += 1;
        clearProbe();
        cancelMetadata();
        url = null;
        return true;
    }

    function reset(seedUrl: string | null = null) {
        draft += 1;
        key = providerConfigurationKey(readConfiguration());
        revision += 1;
        clearProbe();
        cancelMetadata();
        url = seedUrl;
    }

    function ticket(sequence: number): ProviderRequestTicket {
        configure();
        return {
            draft,
            revision,
            sequence,
            session: getClientSessionGeneration(),
            key,
            configuration: $state.snapshot(readConfiguration()),
        };
    }

    function isContextCurrent(request: ProviderRequestTicket): boolean {
        return alive && request.draft === draft && request.revision === revision && request.key === providerConfigurationKey(readConfiguration()) && isClientSessionCurrent(request.session);
    }

    function isProbeCurrent(request: ProviderRequestTicket): boolean {
        return request.sequence === probeSequence && isContextCurrent(request);
    }

    function isMetadataCurrent(request: ProviderRequestTicket): boolean {
        return request.sequence === metadataSequence && isContextCurrent(request);
    }

    function requestPayload(request: ProviderRequestTicket, operations: ProbeOperation[]) {
        const configuration = request.configuration;
        if (configuration.noProvider || !configuration.providerCode || (!configuration.identifier && configuration.identifierType !== 'AUTO_GENERATED')) {
            throw new Error('Provider configuration is incomplete.');
        }
        return {
            provider_code: configuration.providerCode,
            identifier: configuration.identifier || (configuration.identifierType === 'AUTO_GENERATED' ? '__auto__' : ''),
            identifier_type: configuration.identifierType,
            provider_params: configuration.providerParams,
            operations,
        };
    }

    async function run(origin: 'auto' | 'manual'): Promise<boolean> {
        configure();
        const request = ticket(++probeSequence);
        status = 'testing';
        response = null;
        error = null;
        source = origin;
        try {
            const result = await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post(requestPayload(request, ['current_price', 'history']));
            if (!isProbeCurrent(request)) return false;
            response = result;
            const operations = [safeScalar(result.current_price), safeScalar(result.history)];
            const hasRealError = operations.some((operation) => operation && isRealProbeError({success: operation.success, error: safeString(operation.error), error_code: safeString(operation.error_code)}));
            status = hasRealError ? 'failed' : 'passed';
            const resultUrl = safeString(result.provider_url);
            if (resultUrl) url = resultUrl;
        } catch (failure: unknown) {
            if (!isProbeCurrent(request)) return false;
            error = failure;
            status = 'failed';
        }
        return true;
    }

    function beginMetadata(): ProviderRequestTicket {
        configure();
        const request = ticket(++metadataSequence);
        metadataPending = true;
        return request;
    }

    function finishMetadata(request: ProviderRequestTicket) {
        if (isMetadataCurrent(request)) metadataPending = false;
    }

    function cancelPending() {
        probeSequence += 1;
        cancelMetadata();
        if (status === 'testing') clearProbe();
    }

    function dispose() {
        alive = false;
        cancelPending();
    }

    return {
        get status() {
            return status;
        },
        get response() {
            return response;
        },
        get error() {
            return error;
        },
        get source() {
            return source;
        },
        get url() {
            return url;
        },
        get metadataPending() {
            return metadataPending;
        },
        configure,
        reset,
        run,
        beginMetadata,
        finishMetadata,
        isContextCurrent,
        isMetadataCurrent,
        requestPayload,
        cancelPending,
        dispose,
        captureContext: () => ticket(0),
    };
}

export type ProviderProbeState = ReturnType<typeof createProviderProbeState>;
