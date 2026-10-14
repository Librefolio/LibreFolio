// @vitest-environment jsdom
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {z} from 'zod';
import type {schemas} from '$lib/api/generated';
import {getClientSessionUserId, transitionClientSession} from '$lib/stores/app/clientSession';
import {createProviderProbeState, providerConfigurationKey, type ProviderConfiguration, type ProviderProbeState, type ProviderRequestTicket, type ProviderTestStatus} from './providerProbeState.svelte';

type ProbeRequest = z.infer<typeof schemas.FAProviderProbeRequest>;
type ProbeResponse = z.infer<typeof schemas.FAProviderProbeResponse>;
type Origin = 'auto' | 'manual';
type LateSettlement = 'success' | 'rejection';
type Completion = {status: 'passed' | 'failed'; response: ProbeResponse | null; error: unknown};

const {probeApi} = vi.hoisted(() => ({
    probeApi: vi.fn<(payload: ProbeRequest) => Promise<ProbeResponse>>(),
}));

vi.mock('$lib/api', () => ({
    zodiosApi: {probe_provider_config_api_v1_assets_provider_probe_post: probeApi},
}));

// No root/harness: this controller has state getters, but no effect or lifecycle hook.
// Cases stay sequential because the real session singleton and API mock are shared.
const SESSION_A = 'provider-probe-state/owner-a';
const SESSION_B = 'provider-probe-state/owner-b';
const SEED_URL = 'https://provider-probe.invalid/seed';
const WINNER_URL = 'https://provider-probe.invalid/winner';
const controllers = new Set<ProviderProbeState>();
const pendingSettlers = new Set<() => void>();
const publicCompletions: Promise<unknown>[] = [];
const unexpectedCalls: ProbeRequest[] = [];
let previousUser: string | null = null;

function probeResponse(overrides: Partial<ProbeResponse> = {}): ProbeResponse {
    return {
        provider_code: 'mockprov',
        identifier: 'PROBE-A',
        total_execution_time_ms: 37,
        provider_url: 'https://provider-probe.invalid/current',
        current_price: {
            success: true,
            execution_time_ms: 11,
            value: '123.45',
            currency: 'EUR',
            as_of_date: '2026-09-08',
        },
        history: {
            success: true,
            execution_time_ms: 19,
            points_count: 2,
            date_range: '2026-09-07 → 2026-09-08',
            sample_prices: [
                {date: '2026-09-07', close: 122.8},
                {date: '2026-09-08', close: 123.45},
            ],
        },
        ...overrides,
    };
}

function operationFailure(errorCode: string) {
    return {
        success: false,
        execution_time_ms: 7,
        error_code: errorCode,
        error: 'Synthetic provider operation failure',
    };
}

function deferred<T>(name: string, fallback: T) {
    let resolvePromise!: (value: T) => void;
    let rejectPromise!: (reason: unknown) => void;
    let settled = false;
    const promise = new Promise<T>((resolve, reject) => {
        resolvePromise = resolve;
        rejectPromise = reject;
    });
    function resolve(value: T) {
        if (settled) return;
        settled = true;
        pendingSettlers.delete(cleanup);
        resolvePromise(value);
    }
    function reject(reason: unknown) {
        if (settled) return;
        settled = true;
        pendingSettlers.delete(cleanup);
        rejectPromise(reason);
    }
    const cleanup = () => resolve(fallback);
    pendingSettlers.add(cleanup);
    return {name, promise, resolve, reject};
}

function setup(initial: Partial<ProviderConfiguration> = {}) {
    const range = {start: '2026-09-01', end: '2026-09-08'};
    const params = {currency: 'EUR', options: {precision: 2, ranges: [range]}, venues: ['XETR', 'XMIL']};
    let configuration: ProviderConfiguration = {
        providerCode: 'mockprov',
        identifier: 'PROBE-A',
        identifierType: 'TICKER',
        providerParams: params,
        noProvider: false,
        ...initial,
    };
    const state = createProviderProbeState(() => configuration);
    controllers.add(state);
    expect(state.configure()).toBe(true);
    expectVerdict(state, 'not_tested', null, null, null);
    return {
        state,
        params,
        range,
        get configuration() {
            return configuration;
        },
        set configuration(next: ProviderConfiguration) {
            configuration = next;
        },
    };
}

type Fixture = ReturnType<typeof setup>;

function startProbe(state: ProviderProbeState, source: Origin, name: string) {
    const answer = deferred(name, probeResponse());
    const received = vi.fn((_payload: ProbeRequest) => answer.promise);
    probeApi.mockImplementationOnce(received);
    const completion = state.run(source);
    publicCompletions.push(completion);
    expect(received).toHaveBeenCalledTimes(1);
    expectVerdict(state, 'testing', null, null, source);
    return {name, state, source, received, completion, resolve: answer.resolve, reject: answer.reject};
}

type PendingProbe = ReturnType<typeof startProbe>;

function probeView(state: ProviderProbeState) {
    const view = {status: state.status, response: state.response, error: state.error, source: state.source, url: state.url};
    // Fixtures/errors are JSON data. Detach observations from mutable rune proxies.
    return JSON.parse(JSON.stringify(view)) as typeof view;
}

function view(state: ProviderProbeState) {
    return {...probeView(state), metadataPending: state.metadataPending};
}

function expectVerdict(state: ProviderProbeState, status: ProviderTestStatus, response: ProbeResponse | null, error: unknown, source: Origin | null) {
    expect(state.status).toBe(status);
    expect(state.response).toEqual(response);
    expect(state.error).toEqual(error);
    expect(state.source).toBe(source);
}

async function accept(request: PendingProbe, expected: Completion) {
    if (expected.response === null) request.reject(expected.error);
    else request.resolve(expected.response);
    // The boolean acknowledges a current completion, including failed verdicts.
    expect(await request.completion).toBe(true);
    expectVerdict(request.state, expected.status, expected.response, expected.error, request.source);
    if (expected.response !== null) {
        expect(request.state.response?.total_execution_time_ms).toBe(expected.response.total_execution_time_ms);
    }
    if (expected.status === 'passed' && typeof expected.response?.provider_url === 'string') {
        expect(request.state.url).toBe(expected.response.provider_url);
    }
}

async function discard(request: PendingProbe, settlement: LateSettlement) {
    const owner = view(request.state);
    if (settlement === 'success') {
        request.resolve(probeResponse({provider_url: 'https://provider-probe.invalid/obsolete', total_execution_time_ms: 31}));
    } else {
        request.reject({code: 'SYNTHETIC_STALE_REJECTION', request: request.name});
    }
    expect(await request.completion).toBe(false);
    expect(view(request.state)).toEqual(owner);
}

function ignoreMetadata(state: ProviderProbeState, ticket: ProviderRequestTicket) {
    expect(state.isMetadataCurrent(ticket)).toBe(false);
    const owner = view(state);
    state.finishMetadata(ticket);
    expect(view(state)).toEqual(owner);
}

beforeEach(() => {
    previousUser = getClientSessionUserId();
    transitionClientSession(SESSION_A);
    probeApi.mockReset();
    probeApi.mockImplementation((payload) => {
        unexpectedCalls.push(payload);
        throw new Error('Unexpected synthetic provider probe request');
    });
});

afterEach(async () => {
    try {
        for (const state of controllers) {
            state.reset();
            state.dispose();
        }
        // Also release requests left pending by an interrupted assertion, after disposal.
        for (const settle of [...pendingSettlers]) settle();
        await Promise.allSettled(publicCompletions);
        // run() catches API errors, so a throwing default alone would not fail closed.
        expect(unexpectedCalls).toEqual([]);
    } finally {
        transitionClientSession(previousUser);
        controllers.clear();
        pendingSettlers.clear();
        publicCompletions.length = 0;
        unexpectedCalls.length = 0;
        probeApi.mockReset();
    }
});

const configurationChanges: {name: string; initial?: Partial<ProviderConfiguration>; change: (fixture: Fixture) => void}[] = [
    {
        name: 'providerCode',
        change: (f) => {
            f.configuration.providerCode = 'mockprov-other';
        },
    },
    {
        name: 'identifier',
        change: (f) => {
            f.configuration.identifier = 'PROBE-B';
        },
    },
    {
        name: 'identifierType',
        change: (f) => {
            f.configuration.identifierType = 'ISIN';
        },
    },
    {
        name: 'noProvider',
        change: (f) => {
            f.configuration.noProvider = true;
        },
    },
    {
        name: 'providerParams replacement',
        change: (f) => {
            f.configuration.providerParams = {currency: 'USD'};
        },
    },
    {
        name: 'nested in-place object edit',
        change: (f) => {
            f.params.options.precision = 4;
        },
    },
    {
        name: 'nested in-place array edit',
        change: (f) => {
            f.params.options.ranges.push({start: '2026-08-01', end: '2026-08-31'});
        },
    },
    {
        name: 'object inside an array edit',
        change: (f) => {
            f.range.end = '2026-09-09';
        },
    },
    {
        name: 'array order',
        change: (f) => {
            f.params.venues.reverse();
        },
    },
    {
        name: 'providerParams reset to null',
        change: (f) => {
            f.configuration.providerParams = null;
        },
    },
    {
        name: 'providerParams null to object',
        initial: {providerParams: null},
        change: (f) => {
            f.configuration.providerParams = {currency: 'EUR'};
        },
    },
];

const completedCases: {name: string; make: () => Completion}[] = [
    {name: 'passed', make: () => ({status: 'passed', response: probeResponse(), error: null})},
    {name: 'operation-failed', make: () => ({status: 'failed', response: probeResponse({history: operationFailure('FETCH_ERROR')}), error: null})},
    {name: 'transport-failed', make: () => ({status: 'failed', response: null, error: {code: 'SYNTHETIC_TRANSPORT_ERROR', request: 'completed configuration'}})},
];
const lateSettlements = ['success', 'rejection'] as const;
const completionOrders = ['old first', 'new first'] as const;
const lateOrders = lateSettlements.flatMap((settlement) => completionOrders.map((order) => ({settlement, order})));
const restartOrders = [...lateOrders, ...lateSettlements.map((settlement) => ({settlement, order: 'before restart' as const}))];
const origins: {older: Origin; newer: Origin}[] = [
    {older: 'auto', newer: 'manual'},
    {older: 'manual', newer: 'auto'},
    {older: 'auto', newer: 'auto'},
    {older: 'manual', newer: 'manual'},
];

describe('effective configuration ownership', () => {
    describe.each(completedCases)('completed $name', ({make}) => {
        it.each(configurationChanges)('$name clears the old verdict and both tickets', async ({initial, change}) => {
            const f = setup(initial);
            const context = f.state.captureContext();
            const metadata = f.state.beginMetadata();
            const oldKey = providerConfigurationKey(f.configuration);
            await accept(startProbe(f.state, 'manual', 'completed configuration'), make());
            expect(f.state.isContextCurrent(context)).toBe(true);
            expect(f.state.isMetadataCurrent(metadata)).toBe(true);
            expect(f.state.metadataPending).toBe(true);

            change(f);
            expect(providerConfigurationKey(f.configuration)).not.toBe(oldKey);
            expect(f.state.configure()).toBe(true);
            expectVerdict(f.state, 'not_tested', null, null, null);
            expect(f.state.url).toBeNull();
            expect(f.state.isContextCurrent(context)).toBe(false);
            expect(f.state.metadataPending).toBe(false);
            ignoreMetadata(f.state, metadata);
        });
    });

    describe.each(lateSettlements)('late %s', (settlement) => {
        it.each(configurationChanges)('$name clears a pending verdict without letting it return', async ({initial, change}) => {
            const f = setup(initial);
            f.state.reset(SEED_URL);
            const context = f.state.captureContext();
            const metadata = f.state.beginMetadata();
            const oldKey = providerConfigurationKey(f.configuration);
            const old = startProbe(f.state, 'auto', 'pending configuration');
            expect(f.state.isContextCurrent(context)).toBe(true);
            expect(f.state.isMetadataCurrent(metadata)).toBe(true);
            expect(f.state.url).toBe(SEED_URL);

            change(f);
            expect(providerConfigurationKey(f.configuration)).not.toBe(oldKey);
            expect(f.state.configure()).toBe(true);
            expectVerdict(f.state, 'not_tested', null, null, null);
            expect(f.state.url).toBeNull();
            expect(f.state.isContextCurrent(context)).toBe(false);
            expect(f.state.metadataPending).toBe(false);
            await discard(old, settlement);
            ignoreMetadata(f.state, metadata);
        });

        it.each(configurationChanges)('$name is stale even before configure is called', async ({initial, change}) => {
            const f = setup(initial);
            const context = f.state.captureContext();
            const metadata = f.state.beginMetadata();
            const old = startProbe(f.state, 'auto', 'configuration not yet observed');
            expect(f.state.isContextCurrent(context)).toBe(true);
            expect(f.state.isMetadataCurrent(metadata)).toBe(true);

            change(f);
            expect(f.state.isContextCurrent(context)).toBe(false);
            expect(f.state.isMetadataCurrent(metadata)).toBe(false);
            // No eager reset is promised here: only that stale work cannot publish.
            await discard(old, settlement);
            ignoreMetadata(f.state, metadata);
        });
    });

    it.each(['testing', 'passed', 'failed'] as const)('object key order alone preserves a %s probe and active tickets', async (phase) => {
        const f = setup();
        const context = f.state.captureContext();
        const metadata = f.state.beginMetadata();
        const oldKey = providerConfigurationKey(f.configuration);
        const request = startProbe(f.state, 'manual', 'key order only');
        if (phase !== 'testing') {
            await accept(request, {status: phase, response: probeResponse(phase === 'failed' ? {history: operationFailure('FETCH_ERROR')} : {}), error: null});
        }
        expect(f.state.isContextCurrent(context)).toBe(true);
        expect(f.state.isMetadataCurrent(metadata)).toBe(true);
        const owner = view(f.state);

        f.configuration = {
            noProvider: false,
            providerParams: {
                venues: ['XETR', 'XMIL'],
                options: {ranges: [{end: '2026-09-08', start: '2026-09-01'}], precision: 2},
                currency: 'EUR',
            },
            identifierType: 'TICKER',
            identifier: 'PROBE-A',
            providerCode: 'mockprov',
        };
        expect(providerConfigurationKey(f.configuration)).toBe(oldKey);
        expect(f.state.configure()).toBe(false);
        expect(f.state.isContextCurrent(context)).toBe(true);
        expect(f.state.isMetadataCurrent(metadata)).toBe(true);
        expect(view(f.state)).toEqual(owner);
        if (phase === 'testing') await accept(request, {status: 'passed', response: probeResponse(), error: null});
        f.state.finishMetadata(metadata);
        expect(f.state.metadataPending).toBe(false);
    });

    it.each(['context', 'metadata'] as const)('%s captures configuration and request data without aliasing caller objects', async (channel) => {
        const f = setup();
        const ticket = channel === 'metadata' ? f.state.beginMetadata() : f.state.captureContext();
        const metadataPayload = f.state.requestPayload(ticket, ['metadata']);
        const request = startProbe(f.state, 'manual', 'immutable request');
        expect(f.state.isContextCurrent(ticket)).toBe(true);
        if (channel === 'metadata') expect(f.state.isMetadataCurrent(ticket)).toBe(true);

        f.params.options.precision = 4;
        f.range.end = '2026-09-09';
        f.params.options.ranges.push({start: '2026-08-01', end: '2026-08-31'});
        f.params.venues.reverse();
        f.configuration.providerCode = 'mockprov-other';
        f.configuration.identifier = 'PROBE-B';
        f.configuration.identifierType = 'ISIN';
        f.configuration.noProvider = true;
        f.configuration.providerParams = {currency: 'USD'};

        expect(ticket.configuration).toEqual({
            providerCode: 'mockprov',
            identifier: 'PROBE-A',
            identifierType: 'TICKER',
            providerParams: {
                currency: 'EUR',
                options: {precision: 2, ranges: [{start: '2026-09-01', end: '2026-09-08'}]},
                venues: ['XETR', 'XMIL'],
            },
            noProvider: false,
        });
        expect(request.received).toHaveBeenCalledWith({
            provider_code: 'mockprov',
            identifier: 'PROBE-A',
            identifier_type: 'TICKER',
            provider_params: {
                currency: 'EUR',
                options: {precision: 2, ranges: [{start: '2026-09-01', end: '2026-09-08'}]},
                venues: ['XETR', 'XMIL'],
            },
            operations: ['current_price', 'history'],
        });
        const expectedMetadataPayload = {
            provider_code: 'mockprov',
            identifier: 'PROBE-A',
            identifier_type: 'TICKER',
            provider_params: {
                currency: 'EUR',
                options: {precision: 2, ranges: [{start: '2026-09-01', end: '2026-09-08'}]},
                venues: ['XETR', 'XMIL'],
            },
            operations: ['metadata'],
        };
        expect(metadataPayload).toEqual(expectedMetadataPayload);
        expect(f.state.requestPayload(ticket, ['metadata'])).toEqual(expectedMetadataPayload);
        expect(f.state.isContextCurrent(ticket)).toBe(false);
        if (channel === 'metadata') expect(f.state.isMetadataCurrent(ticket)).toBe(false);
        await discard(request, 'success');
    });

    it.each(['auto', 'manual'] as const)('%s sends the AUTO_GENERATED sentinel and exact operation lists', async (source) => {
        const {state} = setup({providerCode: 'scheduled_investment', identifier: '', identifierType: 'AUTO_GENERATED', providerParams: null});
        const request = startProbe(state, source, 'generated identifier');
        expect(request.received).toHaveBeenCalledWith({
            provider_code: 'scheduled_investment',
            identifier: '__auto__',
            identifier_type: 'AUTO_GENERATED',
            provider_params: null,
            operations: ['current_price', 'history'],
        });
        const metadata = state.beginMetadata();
        expect(state.requestPayload(metadata, ['metadata'])).toEqual({
            provider_code: 'scheduled_investment',
            identifier: '__auto__',
            identifier_type: 'AUTO_GENERATED',
            provider_params: null,
            operations: ['metadata'],
        });
        await accept(request, {status: 'passed', response: probeResponse({provider_code: 'scheduled_investment', identifier: '__auto__'}), error: null});
        expect(state.isMetadataCurrent(metadata)).toBe(true);
        state.finishMetadata(metadata);
        expect(state.metadataPending).toBe(false);
    });
});

const verdictCases: {name: string; status: 'passed' | 'failed'; makeResponse: () => ProbeResponse}[] = [
    {name: 'full success', status: 'passed', makeResponse: () => probeResponse()},
    {name: 'current_price NO_DATA with valid history', status: 'passed', makeResponse: () => probeResponse({current_price: operationFailure('NO_DATA')})},
    {name: 'current_price NOT_IMPLEMENTED with valid history', status: 'passed', makeResponse: () => probeResponse({current_price: operationFailure('NOT_IMPLEMENTED')})},
    {name: 'history NO_DATA with valid current price', status: 'passed', makeResponse: () => probeResponse({history: operationFailure('NO_DATA')})},
    {name: 'history NOT_IMPLEMENTED with valid current price', status: 'passed', makeResponse: () => probeResponse({history: operationFailure('NOT_IMPLEMENTED')})},
    {name: 'both operations soft-fail', status: 'passed', makeResponse: () => probeResponse({current_price: operationFailure('NO_DATA'), history: operationFailure('NOT_IMPLEMENTED')})},
    {name: 'hard current_price error', status: 'failed', makeResponse: () => probeResponse({current_price: operationFailure('FETCH_ERROR')})},
    {name: 'hard history error', status: 'failed', makeResponse: () => probeResponse({history: operationFailure('PARSE_ERROR')})},
    {name: 'both operations hard-fail', status: 'failed', makeResponse: () => probeResponse({current_price: operationFailure('FETCH_ERROR'), history: operationFailure('PARSE_ERROR')})},
    {name: 'soft current_price cannot hide hard history', status: 'failed', makeResponse: () => probeResponse({current_price: operationFailure('NO_DATA'), history: operationFailure('FETCH_ERROR')})},
];

describe.each(['auto', 'manual'] as const)('literal verdict contract with the real classifier: %s', (source) => {
    it.each(verdictCases)('$name is accepted with a $status verdict', async ({status, makeResponse}) => {
        const {state} = setup();
        await accept(startProbe(state, source, 'verdict fixture'), {status, response: makeResponse(), error: null});
    });

    it('accepts a current transport rejection as failed, retaining the technical error', async () => {
        const {state} = setup();
        const error = {code: 'SYNTHETIC_TRANSPORT_ERROR', request: 'current transport'};
        await accept(startProbe(state, source, 'current transport'), {status: 'failed', response: null, error});
    });
});

const winningOutcomes: {name: string; make: () => Completion}[] = [
    {name: 'successful', make: () => ({status: 'passed', response: probeResponse({provider_url: WINNER_URL, total_execution_time_ms: 83}), error: null})},
    {name: 'operation-failed', make: () => ({status: 'failed', response: probeResponse({history: operationFailure('FETCH_ERROR'), provider_url: 'https://provider-probe.invalid/failed-winner', total_execution_time_ms: 83}), error: null})},
    {name: 'transport-failed', make: () => ({status: 'failed', response: null, error: {code: 'SYNTHETIC_TRANSPORT_ERROR', request: 'newer winner'}})},
    {name: 'successful without a URL', make: () => ({status: 'passed', response: probeResponse({provider_url: undefined, total_execution_time_ms: 83}), error: null})},
];

describe.each(origins)('same configuration: $older → $newer', ({older, newer}) => {
    it.each(winningOutcomes.flatMap((outcome) => lateOrders.map((ordering) => ({...outcome, ...ordering}))))('$name winner, $order, stale $settlement', async ({make, order, settlement}) => {
        const {state} = setup();
        const old = startProbe(state, older, 'superseded same-configuration probe');
        const current = startProbe(state, newer, 'current same-configuration probe');
        if (order === 'old first') await discard(old, settlement);
        await accept(current, make());
        if (order === 'new first') await discard(old, settlement);
        // discard compares every public field, including source, URL and response duration.
        // Error/missing-URL retention policy is intentionally not specified.
    });
});

describe('configuration A → B → A', () => {
    it.each(lateOrders)('never revives first-A work: $order, stale $settlement', async ({order, settlement}) => {
        const f = setup();
        const firstKey = providerConfigurationKey(f.configuration);
        const firstContext = f.state.captureContext();
        const firstMetadata = f.state.beginMetadata();
        const firstProbe = startProbe(f.state, 'auto', 'first A');
        expect(f.state.isContextCurrent(firstContext)).toBe(true);
        expect(f.state.isMetadataCurrent(firstMetadata)).toBe(true);

        f.configuration.identifier = 'PROBE-B';
        expect(f.state.configure()).toBe(true);
        expect(providerConfigurationKey(f.configuration)).not.toBe(firstKey);
        expectVerdict(f.state, 'not_tested', null, null, null);
        expect(f.state.isContextCurrent(firstContext)).toBe(false);
        expect(f.state.isMetadataCurrent(firstMetadata)).toBe(false);
        const contextB = f.state.captureContext();
        expect(f.state.isContextCurrent(contextB)).toBe(true);

        f.configuration.identifier = 'PROBE-A';
        expect(f.state.configure()).toBe(true);
        expect(providerConfigurationKey(f.configuration)).toBe(firstKey);
        expect(f.state.isContextCurrent(firstContext)).toBe(false);
        expect(f.state.isContextCurrent(contextB)).toBe(false);
        expect(f.state.isMetadataCurrent(firstMetadata)).toBe(false);
        const currentContext = f.state.captureContext();
        const currentMetadata = f.state.beginMetadata();
        const currentProbe = startProbe(f.state, 'manual', 'second A');
        expect(f.state.isContextCurrent(currentContext)).toBe(true);
        expect(f.state.isMetadataCurrent(currentMetadata)).toBe(true);
        expect(f.state.metadataPending).toBe(true);
        ignoreMetadata(f.state, firstMetadata);

        if (order === 'old first') await discard(firstProbe, settlement);
        await accept(currentProbe, {status: 'passed', response: probeResponse({provider_url: WINNER_URL, total_execution_time_ms: 83}), error: null});
        if (order === 'new first') await discard(firstProbe, settlement);
        ignoreMetadata(f.state, firstMetadata);
        expect(f.state.isContextCurrent(firstContext)).toBe(false);
        expect(f.state.isMetadataCurrent(currentMetadata)).toBe(true);
        f.state.finishMetadata(currentMetadata);
        expect(f.state.metadataPending).toBe(false);
    });
});

const restartBoundaries: {name: string; seedUrl?: string | null; apply: (f: Fixture) => void}[] = [
    {name: 'reset()', seedUrl: null, apply: (f) => f.state.reset()},
    {name: 'reset(seedUrl)', seedUrl: SEED_URL, apply: (f) => f.state.reset(SEED_URL)},
    {
        name: 'session A → B',
        apply: () => {
            expect(transitionClientSession(SESSION_B)).toBe(true);
        },
    },
    {
        name: 'session A → B → A',
        apply: () => {
            expect(transitionClientSession(SESSION_B)).toBe(true);
            expect(transitionClientSession(SESSION_A)).toBe(true);
        },
    },
];

describe('draft and real client-session boundaries', () => {
    describe.each(restartBoundaries)('$name on unchanged configuration', (boundary) => {
        it.each(restartOrders)('discards old work: $order, stale $settlement', async ({order, settlement}) => {
            const f = setup();
            const key = providerConfigurationKey(f.configuration);
            const oldContext = f.state.captureContext();
            const oldMetadata = f.state.beginMetadata();
            const oldProbe = startProbe(f.state, 'auto', 'previous draft or session');
            expect(f.state.isContextCurrent(oldContext)).toBe(true);
            expect(f.state.isMetadataCurrent(oldMetadata)).toBe(true);

            boundary.apply(f);
            expect(providerConfigurationKey(f.configuration)).toBe(key);
            // These checks precede new requests: channel sequencing cannot mask a missing
            // session/draft guard. Session-only rows call neither reset nor configure.
            expect(f.state.isContextCurrent(oldContext)).toBe(false);
            expect(f.state.isMetadataCurrent(oldMetadata)).toBe(false);
            if (boundary.seedUrl !== undefined) {
                expectVerdict(f.state, 'not_tested', null, null, null);
                expect(f.state.url).toBe(boundary.seedUrl);
                expect(f.state.metadataPending).toBe(false);
            }
            if (order === 'before restart') {
                // In session-only rows the session transition is the sole invalidator,
                // including when the response arrives: no new sequence can hide a bug.
                await discard(oldProbe, settlement);
                ignoreMetadata(f.state, oldMetadata);
            }
            const currentMetadata = f.state.beginMetadata();
            const currentProbe = startProbe(f.state, 'manual', 'current draft or session');
            expect(f.state.isMetadataCurrent(currentMetadata)).toBe(true);
            expect(f.state.metadataPending).toBe(true);
            ignoreMetadata(f.state, oldMetadata);

            if (order === 'old first') await discard(oldProbe, settlement);
            await accept(currentProbe, {status: 'passed', response: probeResponse({provider_url: WINNER_URL, total_execution_time_ms: 83}), error: null});
            if (order === 'new first') await discard(oldProbe, settlement);
            ignoreMetadata(f.state, oldMetadata);
            expect(f.state.isMetadataCurrent(currentMetadata)).toBe(true);
            f.state.finishMetadata(currentMetadata);
            expect(f.state.metadataPending).toBe(false);
        });
    });

    it.each(completedCases.flatMap((prior) => [null, SEED_URL].map((seedUrl) => ({...prior, seedUrl}))))('reset($seedUrl) clears a completed $name verdict on the same configuration', async ({make, seedUrl}) => {
        const f = setup();
        const key = providerConfigurationKey(f.configuration);
        const context = f.state.captureContext();
        const metadata = f.state.beginMetadata();
        await accept(startProbe(f.state, 'manual', 'completed previous draft'), make());
        expect(f.state.isContextCurrent(context)).toBe(true);
        expect(f.state.isMetadataCurrent(metadata)).toBe(true);

        if (seedUrl === null) f.state.reset();
        else f.state.reset(seedUrl);
        expect(providerConfigurationKey(f.configuration)).toBe(key);
        expectVerdict(f.state, 'not_tested', null, null, null);
        expect(f.state.url).toBe(seedUrl);
        expect(f.state.isContextCurrent(context)).toBe(false);
        expect(f.state.metadataPending).toBe(false);
        ignoreMetadata(f.state, metadata);
    });

    it.each(lateSettlements)('dispose rejects outstanding contexts, metadata and late %s', async (settlement) => {
        const {state} = setup();
        const context = state.captureContext();
        const metadata = state.beginMetadata();
        const request = startProbe(state, 'auto', 'disposed owner');
        expect(state.isContextCurrent(context)).toBe(true);
        expect(state.isMetadataCurrent(metadata)).toBe(true);
        expect(state.metadataPending).toBe(true);

        state.dispose();
        expect(state.isContextCurrent(context)).toBe(false);
        expect(state.isMetadataCurrent(metadata)).toBe(false);
        expect(state.metadataPending).toBe(false);
        await discard(request, settlement);
        ignoreMetadata(state, metadata);
    });
});

describe('independent metadata channel', () => {
    it.each(['testing', 'passed', 'failed'] as const)('begin/finish metadata preserves a %s probe', async (phase) => {
        const {state} = setup();
        const request = startProbe(state, 'auto', 'probe beside metadata');
        if (phase !== 'testing') {
            await accept(request, {status: phase, response: probeResponse(phase === 'failed' ? {history: operationFailure('FETCH_ERROR')} : {}), error: null});
        }
        const before = probeView(state);
        const metadata = state.beginMetadata();
        expect(state.isMetadataCurrent(metadata)).toBe(true);
        expect(state.metadataPending).toBe(true);
        expect(probeView(state)).toEqual(before);
        state.finishMetadata(metadata);
        expect(state.metadataPending).toBe(false);
        expect(probeView(state)).toEqual(before);
        if (phase === 'testing') await accept(request, {status: 'passed', response: probeResponse(), error: null});
    });

    it('an obsolete metadata finally cannot release a newer metadata request', async () => {
        const {state} = setup();
        const old = state.beginMetadata();
        expect(state.isMetadataCurrent(old)).toBe(true);
        expect(state.metadataPending).toBe(true);
        const delayedMetadata = deferred<void>('obsolete metadata finally', undefined);
        const finished = delayedMetadata.promise.finally(() => state.finishMetadata(old));
        publicCompletions.push(finished);
        const current = state.beginMetadata();
        expect(state.isMetadataCurrent(old)).toBe(false);
        expect(state.isMetadataCurrent(current)).toBe(true);
        expect(state.metadataPending).toBe(true);
        const owner = view(state);

        delayedMetadata.resolve(undefined);
        await finished;
        expect(view(state)).toEqual(owner);
        expect(state.isMetadataCurrent(current)).toBe(true);
        state.finishMetadata(current);
        expect(state.metadataPending).toBe(false);
        expect(probeApi).not.toHaveBeenCalled();
    });

    it.each(lateSettlements)('probes cannot supersede metadata, including a stale probe %s', async (settlement) => {
        const {state} = setup();
        const metadata = state.beginMetadata();
        expect(state.isMetadataCurrent(metadata)).toBe(true);
        expect(state.metadataPending).toBe(true);
        const old = startProbe(state, 'auto', 'old probe beside metadata');
        expect(state.isMetadataCurrent(metadata)).toBe(true);
        const current = startProbe(state, 'manual', 'new probe beside metadata');
        expect(state.isMetadataCurrent(metadata)).toBe(true);
        await discard(old, settlement);
        await accept(current, {status: 'passed', response: probeResponse(), error: null});
        expect(state.isMetadataCurrent(metadata)).toBe(true);
        expect(state.metadataPending).toBe(true);
        const before = probeView(state);
        state.finishMetadata(metadata);
        expect(state.metadataPending).toBe(false);
        expect(probeView(state)).toEqual(before);
    });

    const invalidators: {name: string; apply: (f: Fixture) => void}[] = [
        ...restartBoundaries,
        {
            name: 'configured edit',
            apply: (f) => {
                f.configuration.identifier = 'PROBE-B';
                expect(f.state.configure()).toBe(true);
            },
        },
        {
            name: 'edit before configure',
            apply: (f) => {
                f.params.options.precision = 4;
            },
        },
        {name: 'dispose', apply: (f) => f.state.dispose()},
    ];

    it.each(invalidators)('$name invalidates metadata and context without any probe sequencing', ({apply}) => {
        const f = setup();
        const context = f.state.captureContext();
        const metadata = f.state.beginMetadata();
        expect(f.state.isContextCurrent(context)).toBe(true);
        expect(f.state.isMetadataCurrent(metadata)).toBe(true);
        expect(f.state.metadataPending).toBe(true);
        apply(f);
        expect(f.state.isContextCurrent(context)).toBe(false);
        ignoreMetadata(f.state, metadata);
        expect(probeApi).not.toHaveBeenCalled();
    });
});

describe('save cancels work, not a completed current pass', () => {
    it.each(restartOrders)('cancelPending permits a new same-config request: $order, stale $settlement', async ({order, settlement}) => {
        const f = setup();
        const key = providerConfigurationKey(f.configuration);
        const oldMetadata = f.state.beginMetadata();
        const oldProbe = startProbe(f.state, 'auto', 'probe cancelled by save');
        expect(f.state.isMetadataCurrent(oldMetadata)).toBe(true);
        expect(f.state.metadataPending).toBe(true);

        f.state.cancelPending();
        expectVerdict(f.state, 'not_tested', null, null, null);
        expect(f.state.metadataPending).toBe(false);
        expect(f.state.isMetadataCurrent(oldMetadata)).toBe(false);
        expect(providerConfigurationKey(f.configuration)).toBe(key);
        // Context-ticket invalidation on save is not part of this contract.
        if (order === 'before restart') {
            await discard(oldProbe, settlement);
            ignoreMetadata(f.state, oldMetadata);
        }
        const currentMetadata = f.state.beginMetadata();
        const currentProbe = startProbe(f.state, 'manual', 'probe after save');
        expect(f.state.isMetadataCurrent(currentMetadata)).toBe(true);
        expect(f.state.metadataPending).toBe(true);
        ignoreMetadata(f.state, oldMetadata);
        if (order === 'old first') await discard(oldProbe, settlement);
        await accept(currentProbe, {status: 'passed', response: probeResponse({provider_url: WINNER_URL, total_execution_time_ms: 83}), error: null});
        if (order === 'new first') await discard(oldProbe, settlement);
        ignoreMetadata(f.state, oldMetadata);
        expect(f.state.isMetadataCurrent(currentMetadata)).toBe(true);
        f.state.finishMetadata(currentMetadata);
        expect(f.state.metadataPending).toBe(false);
    });

    it.each(origins.flatMap((pair) => (['none', ...lateSettlements] as const).map((oldSettlement) => ({...pair, oldSettlement}))))('preserves a completed $newer pass with metadata pending and older $oldSettlement', async ({older, newer, oldSettlement}) => {
        const {state} = setup();
        const old = oldSettlement === 'none' ? null : startProbe(state, older, 'old probe behind completed winner');
        await accept(startProbe(state, newer, 'completed save winner'), {
            status: 'passed',
            response: probeResponse({provider_url: WINNER_URL, total_execution_time_ms: 83}),
            error: null,
        });
        const metadata = state.beginMetadata();
        expect(state.isMetadataCurrent(metadata)).toBe(true);
        expect(state.metadataPending).toBe(true);
        expect(state.url).toBe(WINNER_URL);
        expect(state.response?.total_execution_time_ms).toBe(83);
        const completed = probeView(state);

        state.cancelPending();
        expect(probeView(state)).toEqual(completed);
        expect(state.metadataPending).toBe(false);
        ignoreMetadata(state, metadata);
        if (old !== null && oldSettlement !== 'none') await discard(old, oldSettlement);
        expect(probeView(state)).toEqual(completed);
    });
});
