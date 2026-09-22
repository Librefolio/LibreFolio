import {beforeEach, describe, expect, it, vi} from 'vitest';
import type {Component} from 'svelte';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {getCompiledToolContract, validateToolCatalog, type VerifiedToolCatalog} from './contracts';
import {createToolRendererRegistry, defineToolRenderer, resolveToolRenderer} from './registry';

const fakeComponent = (() => undefined) as unknown as Component;
// The backend build and documentation page this fixture invents. Deliberately not the
// contract version, so nothing can pass by conflating the two.
const fixtureArtifactVersion = '1.0.0';
let accountSequence = 0;
let catalog: VerifiedToolCatalog;

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((res) => {
        resolve = res;
    });
    return {promise, resolve};
}

function makeCatalog(): VerifiedToolCatalog {
    const contracts = [getCompiledToolContract('pac_allocator', '2.0.0')];
    if (contracts.some((contract) => !contract)) {
        throw new Error('the compiled pac_allocator 2.0.0 contract must be generated');
    }
    return validateToolCatalog(
        {
            catalog_version: '2',
            items: contracts.map((contract) => {
                if (!contract) throw new Error('pac_allocator contract unexpectedly missing');
                return {
                    tool_code: contract.toolCode,
                    contract_version: contract.contractVersion,
                    implementation_version: fixtureArtifactVersion,
                    schema_fingerprint: contract.schemaFingerprint,
                    category: 'analysis',
                    description: `${contract.toolCode} fixture`,
                    description_i18n_key: null,
                    documentation: {path: `tools/${contract.componentKey}`, version: fixtureArtifactVersion},
                    icon_key: 'calculator',
                    input_schema: {},
                    name: contract.toolCode,
                    name_i18n_key: null,
                    operations: contract.operations.map((operation) => ({
                        operation,
                        cleanup_timeout_ms: 5_000,
                        client_timeout_ms: 30_000,
                        deduplication: 'none',
                        deterministic: true,
                        engine_timeout_ms: 30_000,
                        job_timeout_ms: 30_000,
                        max_parameter_bytes: 65_536,
                        max_result_bytes: 65_536,
                        memory_limit_bytes: 268_435_456,
                        pure: true,
                        queue_timeout_ms: 30_000,
                        request_timeout_ms: 30_000,
                        soft_timeout_ms: 30_000,
                    })),
                    output_schema: {},
                    ui: {
                        kind: 'custom',
                        component_key: contract.componentKey,
                        version: contract.uiVersion,
                    },
                };
            }),
            policy: {
                cleanup_timeout_ms: 5_000,
                client_timeout_ms: 30_000,
                engine_timeout_ms: 30_000,
                envelope_reserve_bytes: 1_024,
                ingress_timeout_ms: 30_000,
                job_timeout_ms: 30_000,
                max_batch_items: 1,
                max_batches_per_principal: 1,
                max_json_depth: 16,
                max_parameter_bytes: 65_536,
                max_pending_items: 4,
                max_pending_per_principal: 4,
                max_request_bytes: 65_536,
                max_response_bytes: 65_536,
                max_result_bytes: 65_536,
                memory_limit_bytes: 268_435_456,
                output_reserve_ms: 1_000,
                queue_timeout_ms: 30_000,
                request_timeout_ms: 30_000,
                response_reserve_ms: 1_000,
                soft_timeout_ms: 30_000,
                workers: 1,
            },
            unavailable: [],
        },
        getClientSessionGeneration(),
    );
}

function registration(load: () => Promise<{default: Component}> = vi.fn(async () => ({default: fakeComponent}))) {
    return defineToolRenderer('pac_allocator', '2.0.0', {
        componentKey: 'pac-allocator',
        uiVersion: '2.0.0',
        load,
    });
}

function resolveBinding(load?: () => Promise<{default: Component}>) {
    const resolution = createToolRendererRegistry([registration(load)]).resolve(catalog, 'pac_allocator');
    expect(resolution.status).toBe('ready');
    if (resolution.status !== 'ready') throw new Error(`renderer unexpectedly unavailable: ${resolution.reason}`);
    return resolution.binding;
}

beforeEach(() => {
    transitionClientSession(`registry-test-${++accountSequence}`);
    catalog = makeCatalog();
});

describe('compiled tool renderer registry', () => {
    it('resolves the surviving renderer identity from catalog v2 with a SemVer UI version', () => {
        const resolution = createToolRendererRegistry([registration()]).resolve(catalog, 'pac_allocator');

        expect(resolution).toMatchObject({
            status: 'ready',
            binding: {
                descriptor: {
                    tool_code: 'pac_allocator',
                    contract_version: '2.0.0',
                    ui: {kind: 'custom', component_key: 'pac-allocator', version: '2.0.0'},
                },
            },
        });
    });

    it('reports renderer_missing for a compatible tool the compiled registry does not render', () => {
        // The compiled registry ships no renderer until the pac_allocator v2 UI exists.
        // Asserting the descriptor is the barrier: it proves the catalog entry was found
        // and judged compatible, so this is a missing renderer, not a missing tool.
        const resolution = resolveToolRenderer(catalog, 'pac_allocator');

        expect(resolution).toMatchObject({
            status: 'unavailable',
            reason: 'renderer_missing',
            descriptor: {
                tool_code: 'pac_allocator',
                contract_version: '2.0.0',
                ui: {kind: 'custom', component_key: 'pac-allocator', version: '2.0.0'},
            },
        });
    });

    it('deduplicates concurrent module preloads and exposes the loaded renderer through peek', async () => {
        const module = deferred<{default: Component}>();
        const load = vi.fn(() => module.promise);
        const binding = resolveBinding(load);

        expect(binding.peek()).toBeNull();
        const first = binding.load();
        const second = binding.load();
        await vi.waitFor(() => expect(load).toHaveBeenCalledTimes(1));

        module.resolve({default: fakeComponent});
        const [firstRenderer, secondRenderer] = await Promise.all([first, second]);

        expect(firstRenderer).toHaveProperty('mount');
        expect(secondRenderer).toHaveProperty('mount');
        expect(binding.peek()).toHaveProperty('mount');
        expect(load).toHaveBeenCalledTimes(1);
    });

    it('does not permanently cache a failed dynamic import', async () => {
        const load = vi.fn().mockRejectedValueOnce(new Error('chunk unavailable')).mockResolvedValueOnce({default: fakeComponent});
        const binding = resolveBinding(load);

        await expect(binding.load()).rejects.toMatchObject({kind: 'renderer', code: 'renderer_load_failed'});
        expect(binding.peek()).toBeNull();

        await expect(binding.load()).resolves.toHaveProperty('mount');
        expect(binding.peek()).toHaveProperty('mount');
        expect(load).toHaveBeenCalledTimes(2);
    });

    it('keeps registration metadata guarded against the compiled descriptor', () => {
        // Only the component key deviates from the compiled contract, so the guard this
        // asserts is the component key one and nothing else.
        const invalid = defineToolRenderer('pac_allocator', '2.0.0', {
            componentKey: 'not-the-compiled-component',
            uiVersion: '2.0.0',
            load: async () => ({default: fakeComponent}),
        });

        expect(createToolRendererRegistry([invalid]).resolve(catalog, 'pac_allocator')).toMatchObject({
            status: 'unavailable',
            reason: 'renderer_registration_invalid',
        });
    });

    it('rejects unverified catalog objects before resolving a renderer', () => {
        const rawCopy = JSON.parse(JSON.stringify(catalog)) as VerifiedToolCatalog;
        const registry = createToolRendererRegistry([registration()]);

        expect(() => registry.resolve(rawCopy, 'pac_allocator')).toThrowError(expect.objectContaining({kind: 'compatibility', code: 'catalog_unverified'}));
    });

    it('invalidates both peek and load when the descriptor account generation changes', async () => {
        const binding = resolveBinding();
        await binding.load();
        expect(binding.peek()).toHaveProperty('mount');

        transitionClientSession(`registry-other-account-${++accountSequence}`);

        expect(() => binding.peek()).toThrowError(expect.objectContaining({kind: 'session', code: 'session_changed'}));
        await expect(binding.load()).rejects.toMatchObject({kind: 'session', code: 'session_changed'});
    });
});
