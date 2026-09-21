import {mount, unmount, type Component} from 'svelte';
import {notify, type NotifyOptions} from '$lib/stores/app/notify.svelte';
import {
    ToolClientError,
    getCompiledToolContract,
    getToolDescriptorGeneration,
    inspectToolCompatibility,
    observeToolAccount,
    runToolSessionTask,
    verifyToolDescriptor,
    type CompatibleToolDescriptor,
    type ToolCode,
    type ToolCompatibilityCode,
    type ToolDescriptor,
    type ToolVersion,
    type VerifiedToolCatalog,
    type VerifiedToolDescriptor,
} from './contracts';

export interface ToolHostPropsV1<C extends ToolCode, V extends ToolVersion<C>> {
    descriptor: CompatibleToolDescriptor<C, V>;
    accountGeneration: number;
}

export interface ToolRendererOptions<C extends ToolCode, V extends ToolVersion<C>> {
    componentKey: string;
    uiVersion: string;
    load: () => Promise<{default: Component<ToolHostPropsV1<C, V>>}>;
}

export interface ToolRendererMount {
    unmount: () => Promise<void>;
}

export interface ToolRendererMountOptions {
    context?: Map<unknown, unknown>;
    /** The host supplies localized text; teardown emits one event and optional toast. */
    cleanupFailureToast?: () => NonNullable<NotifyOptions['toast']>;
}

export interface LoadedToolRenderer {
    mount: (target: HTMLElement, options?: ToolRendererMountOptions) => ToolRendererMount;
}

export interface ToolRendererBinding {
    readonly descriptor: VerifiedToolDescriptor;
    readonly accountGeneration: number;
    peek: () => LoadedToolRenderer | null;
    load: (options?: {signal?: AbortSignal}) => Promise<LoadedToolRenderer>;
}

export type ToolRendererUnavailableCode = 'renderer_missing' | 'renderer_registration_invalid' | 'renderer_collision';

export type ToolRendererResolution = {readonly status: 'ready'; readonly binding: ToolRendererBinding} | {readonly status: 'unavailable'; readonly reason: ToolCompatibilityCode | ToolRendererUnavailableCode; readonly descriptor?: ToolDescriptor};

const registrationBrand: unique symbol = Symbol('compiled-tool-renderer');
const bindRenderer: unique symbol = Symbol('bind-compiled-tool-renderer');

export interface CompiledToolRendererRegistration {
    readonly toolCode: string;
    readonly contractVersion: string;
    readonly componentKey: string;
    readonly uiVersion: string;
    readonly [registrationBrand]: true;
    readonly [bindRenderer]: (catalog: VerifiedToolCatalog) => ToolRendererBinding;
}

function mountToolComponent<C extends ToolCode, V extends ToolVersion<C>>(component: Component<ToolHostPropsV1<C, V>>, descriptor: CompatibleToolDescriptor<C, V>, target: HTMLElement, {context, cleanupFailureToast}: ToolRendererMountOptions = {}): ToolRendererMount {
    const accountGeneration = getToolDescriptorGeneration(descriptor);
    const root = target.ownerDocument.createElement('div');
    root.dataset.testid = 'tool-renderer-mount';
    root.dataset.busy = 'false';
    root.setAttribute('aria-busy', 'false');
    target.appendChild(root);
    let instance: ReturnType<typeof mount>;
    try {
        instance = mount(component, {target: root, props: {descriptor, accountGeneration}, context});
    } catch {
        root.remove();
        throw new ToolClientError('renderer', 'renderer_mount_failed');
    }
    let disposed = false;
    let cleanup: Promise<void> | undefined;
    let unobserve = () => {};
    let cleanupFailureReported = false;
    const reportCleanupFailure = () => {
        if (cleanupFailureReported) return;
        cleanupFailureReported = true;
        notify({
            name: 'tool.renderer.unmount.failed',
            detail: {code: 'renderer_unmount_failed'},
            toast: cleanupFailureToast?.(),
        });
    };
    const destroy = (): Promise<void> => {
        if (cleanup) return cleanup;
        disposed = true;
        cleanup = Promise.resolve()
            .then(() => unmount(instance))
            .catch(() => {
                reportCleanupFailure();
                throw new ToolClientError('renderer', 'renderer_unmount_failed');
            });
        unobserve();
        root.remove();
        return cleanup;
    };
    try {
        unobserve = observeToolAccount((account) => {
            if (account.generation !== accountGeneration || !account.authenticated) {
                // Auth teardown must remove the draft even when component cleanup fails.
                void destroy().catch(reportCleanupFailure);
            }
        });
        if (disposed) unobserve();
        getToolDescriptorGeneration(descriptor);
        return {unmount: destroy};
    } catch (error) {
        void destroy().catch(reportCleanupFailure);
        if (error instanceof ToolClientError) throw error;
        throw new ToolClientError('renderer', 'renderer_mount_failed');
    }
}

/** Register source-owned literal imports only; catalogue metadata never becomes an import path. */
export function defineToolRenderer<const C extends ToolCode, const V extends ToolVersion<C>>(code: C, version: V, options: ToolRendererOptions<NoInfer<C>, NoInfer<V>>): CompiledToolRendererRegistration {
    const {componentKey, uiVersion, load} = options;
    let loadedComponent: Component<ToolHostPropsV1<C, V>> | null = null;
    let componentPromise: Promise<Component<ToolHostPropsV1<C, V>>> | null = null;

    const resolvedRenderer = (component: Component<ToolHostPropsV1<C, V>>, descriptor: CompatibleToolDescriptor<C, V>): LoadedToolRenderer => ({
        mount: (target: HTMLElement, mountOptions?: ToolRendererMountOptions) => mountToolComponent(component, descriptor, target, mountOptions),
    });

    const loadComponent = (): Promise<Component<ToolHostPropsV1<C, V>>> => {
        if (loadedComponent) return Promise.resolve(loadedComponent);
        if (componentPromise) return componentPromise;
        componentPromise = load()
            .then((module) => {
                if (typeof module.default !== 'function') {
                    throw new ToolClientError('renderer', 'renderer_load_failed');
                }
                loadedComponent = module.default;
                return loadedComponent;
            })
            .catch((error: unknown) => {
                componentPromise = null;
                if (error instanceof ToolClientError) throw error;
                throw new ToolClientError('renderer', 'renderer_load_failed');
            });
        return componentPromise;
    };

    const registration: CompiledToolRendererRegistration = {
        toolCode: code,
        contractVersion: version,
        componentKey,
        uiVersion,
        [registrationBrand]: true,
        [bindRenderer](catalog: VerifiedToolCatalog): ToolRendererBinding {
            const contract = getCompiledToolContract(code, version);
            if (!contract || contract.componentKey !== componentKey || contract.uiVersion !== uiVersion) {
                throw new ToolClientError('renderer', 'renderer_registration_invalid');
            }
            const descriptor = verifyToolDescriptor(catalog, code, version);
            const accountGeneration = getToolDescriptorGeneration(descriptor);
            return Object.freeze({
                descriptor,
                accountGeneration,
                peek(): LoadedToolRenderer | null {
                    getToolDescriptorGeneration(descriptor);
                    return loadedComponent ? resolvedRenderer(loadedComponent, descriptor) : null;
                },
                async load({signal}: {signal?: AbortSignal} = {}): Promise<LoadedToolRenderer> {
                    try {
                        getToolDescriptorGeneration(descriptor);
                        return await runToolSessionTask(
                            accountGeneration,
                            async (requestSignal) => {
                                const component = await loadComponent();
                                getToolDescriptorGeneration(descriptor);
                                if (requestSignal.aborted) throw new ToolClientError('aborted', 'waiting_stopped');
                                return resolvedRenderer(component, descriptor);
                            },
                            signal,
                        );
                    } catch (error) {
                        if (error instanceof ToolClientError) throw error;
                        throw new ToolClientError('renderer', 'renderer_load_failed');
                    }
                },
            });
        },
    };
    return Object.freeze(registration);
}

function identity(code: string, version: string): string {
    return JSON.stringify([code, version]);
}

export function createToolRendererRegistry(registrations: readonly CompiledToolRendererRegistration[]): {
    resolve: (catalog: VerifiedToolCatalog, toolCode: string) => ToolRendererResolution;
} {
    const entries = new Map<string, CompiledToolRendererRegistration>();
    const blocked = new Map<string, ToolRendererUnavailableCode>();
    const componentClaims = new Map<string, CompiledToolRendererRegistration[]>();
    for (const registration of registrations) {
        const key = identity(registration.toolCode, registration.contractVersion);
        if (entries.has(key)) blocked.set(key, 'renderer_collision');
        else entries.set(key, registration);
        const contract = getCompiledToolContract(registration.toolCode, registration.contractVersion);
        if (!contract || registration[registrationBrand] !== true || registration.componentKey !== contract.componentKey || registration.uiVersion !== contract.uiVersion) {
            if (!blocked.has(key)) blocked.set(key, 'renderer_registration_invalid');
        }
        const claims = componentClaims.get(registration.componentKey) ?? [];
        claims.push(registration);
        componentClaims.set(registration.componentKey, claims);
    }
    for (const claims of componentClaims.values()) {
        if (new Set(claims.map((entry) => entry.toolCode)).size > 1) {
            for (const claim of claims) blocked.set(identity(claim.toolCode, claim.contractVersion), 'renderer_collision');
        }
    }
    return Object.freeze({
        resolve(catalog: VerifiedToolCatalog, toolCode: string): ToolRendererResolution {
            const compatibility = inspectToolCompatibility(catalog, toolCode);
            if (compatibility.status === 'unavailable') return compatibility;
            const {descriptor} = compatibility;
            const key = identity(descriptor.tool_code, descriptor.contract_version);
            const reason = blocked.get(key);
            if (reason) return {status: 'unavailable', reason, descriptor};
            const registration = entries.get(key);
            if (!registration) return {status: 'unavailable', reason: 'renderer_missing', descriptor};
            return {status: 'ready', binding: registration[bindRenderer](catalog)};
        },
    });
}

const compiledRendererRegistrations: readonly CompiledToolRendererRegistration[] = [
    defineToolRenderer('pac_allocator', '1.0.0', {
        componentKey: 'pac-allocator',
        uiVersion: '1.0.0',
        load: () => import('./pac-allocator/PacAllocatorTool.svelte'),
    }),
    defineToolRenderer('portfolio_rebalancer', '1.0.0', {
        componentKey: 'portfolio-rebalancer',
        uiVersion: '1.0.0',
        load: () => import('./pac-allocator/PortfolioRebalancerTool.svelte'),
    }),
];
const compiledRegistry = createToolRendererRegistry(compiledRendererRegistrations);

export function resolveToolRenderer(catalog: VerifiedToolCatalog, toolCode: string): ToolRendererResolution {
    return compiledRegistry.resolve(catalog, toolCode);
}
