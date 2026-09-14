// @vitest-environment jsdom
/**
 * ToolHost — generic renderer lifecycle contract.
 *
 * The fixture is deliberately unrelated to PAC. The host owns catalogue and
 * renderer loading, compatibility metadata, reload confirmation, and renderer
 * cleanup; a concrete tool owns only the mounted interface.
 */
import {afterAll, afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';
import {getClientSessionUserId, transitionClientSession} from '$lib/stores/app/clientSession';
import {getToolAccountState, type VerifiedToolCatalog} from './contracts';
import ToolHost from './ToolHost.svelte';

const {afterNavigateMock, fetchCatalogMock, notifyMock, resolveRendererMock} = vi.hoisted(() => ({
    afterNavigateMock: vi.fn(),
    fetchCatalogMock: vi.fn(),
    notifyMock: vi.fn(),
    resolveRendererMock: vi.fn(),
}));

vi.mock('$app/navigation', () => ({afterNavigate: afterNavigateMock}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/i18n')>();
    const {readable} = await import('svelte/store');
    const identity = readable((key: string) => key);
    return {...actual, _: identity, t: identity};
});
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: notifyMock}));
vi.mock('./client', () => ({fetchToolCatalog: fetchCatalogMock}));
vi.mock('./registry', () => ({resolveToolRenderer: resolveRendererMock}));

const TOOL_CODE = 'generic_lifecycle_tool';
const CONTRACT_VERSION = '7.4.1';
const UI_VERSION = '1.0.0';
const IMPLEMENTATION_VERSION = 'impl-secret-99';

const descriptor = {
    tool_code: TOOL_CODE,
    contract_version: CONTRACT_VERSION,
    implementation_version: IMPLEMENTATION_VERSION,
    schema_fingerprint: 'f'.repeat(64),
    category: 'analysis',
    description: 'Generic lifecycle fixture description',
    description_i18n_key: null,
    documentation: {path: 'tools/generic-lifecycle-tool', version: CONTRACT_VERSION},
    icon_key: 'calculator',
    input_schema: {},
    name: 'Generic lifecycle fixture',
    name_i18n_key: null,
    operations: [{operation: 'analyze'}],
    output_schema: {},
    ui: {kind: 'custom', component_key: TOOL_CODE, version: UI_VERSION},
} as const;

const catalog = {
    catalog_version: 'fixture',
    items: [descriptor],
    unavailable: [],
    policy: {client_timeout_ms: 30_000},
} as unknown as VerifiedToolCatalog;

const previousSession = getClientSessionUserId();
let accountSequence = 0;

beforeEach(() => {
    transitionClientSession(`tool-host-test-${++accountSequence}`);
    afterNavigateMock.mockReset();
    fetchCatalogMock.mockReset();
    notifyMock.mockReset();
    resolveRendererMock.mockReset();
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

afterAll(() => {
    transitionClientSession(previousSession);
});

function deferred<T>(): {promise: Promise<T>; resolve: (value: T | PromiseLike<T>) => void} {
    let resolve!: (value: T | PromiseLike<T>) => void;
    const promise = new Promise<T>((done) => {
        resolve = done;
    });
    return {promise, resolve};
}

function rendererFixture(testId: string) {
    let node: HTMLElement | null = null;
    const unmount = vi.fn(async () => {
        node?.remove();
        node = null;
    });
    const mount = vi.fn((target: HTMLElement) => {
        node = document.createElement('div');
        node.setAttribute('data-testid', testId);
        target.append(node);
        return {unmount};
    });
    return {loaded: {mount}, mount, unmount};
}

function expectPublicCompatibility(): void {
    const versions = screen.getByTestId('tool-host-compatibility-versions');
    expect(versions).toHaveTextContent(`tools.backendVersion ${CONTRACT_VERSION} · tools.uiVersion ${UI_VERSION}`);
    expect(versions).not.toHaveTextContent(IMPLEMENTATION_VERSION);
}

describe('ToolHost generic renderer lifecycle', () => {
    it('loads, mounts, confirms a fresh reload, and disposes each renderer it owns', async () => {
        const initialCatalog = deferred<VerifiedToolCatalog>();
        const refreshedCatalog = deferred<VerifiedToolCatalog>();
        const initialRenderer = rendererFixture('generic-renderer-initial');
        const refreshedRenderer = rendererFixture('generic-renderer-refreshed');
        const initialComponent = deferred<typeof initialRenderer.loaded>();
        const refreshedComponent = deferred<typeof refreshedRenderer.loaded>();
        const loadRenderer = vi
            .fn()
            .mockImplementationOnce(() => initialComponent.promise)
            .mockImplementationOnce(() => refreshedComponent.promise);

        fetchCatalogMock.mockImplementationOnce(() => initialCatalog.promise).mockImplementationOnce(() => refreshedCatalog.promise);
        resolveRendererMock.mockImplementation(() => ({
            status: 'ready',
            binding: {
                descriptor,
                accountGeneration: getToolAccountState().generation,
                load: loadRenderer,
            },
        }));

        const {unmount} = render(ToolHost, {toolCode: TOOL_CODE});
        const host = screen.getByTestId('tool-host');

        await waitFor(() => {
            expect(fetchCatalogMock).toHaveBeenCalledTimes(1);
            expect(host).toHaveAttribute('data-state', 'catalog_loading');
            expect(screen.getByTestId('tool-host-catalog-loading')).toBeInTheDocument();
        });

        initialCatalog.resolve(catalog);
        await waitFor(() => {
            expect(resolveRendererMock).toHaveBeenCalledWith(catalog, TOOL_CODE);
            expect(loadRenderer).toHaveBeenCalledTimes(1);
            expect(host).toHaveAttribute('data-state', 'component_loading');
            expect(screen.getByTestId('tool-host-component-loading')).toBeInTheDocument();
            expect(screen.getByTestId('tool-host-renderer')).toHaveAttribute('data-busy', 'true');
        });

        initialComponent.resolve(initialRenderer.loaded);
        await waitFor(() => {
            expect(initialRenderer.mount).toHaveBeenCalledTimes(1);
            expect(host).toHaveAttribute('data-state', 'ready');
            expect(screen.getByTestId('tool-host-renderer')).toHaveAttribute('data-busy', 'false');
            expect(screen.getByTestId('generic-renderer-initial')).toBeInTheDocument();
        });
        expectPublicCompatibility();
        expect(notifyMock).toHaveBeenCalledWith(
            expect.objectContaining({
                name: 'tool.host.loaded',
                detail: {unavailable: 0},
            }),
        );

        await fireEvent.click(screen.getByTestId('tool-host-refresh'));
        await waitFor(() => {
            expect(screen.getByTestId('tool-host-reload-confirm')).toBeInTheDocument();
        });
        expect(fetchCatalogMock).toHaveBeenCalledTimes(1);
        expect(initialRenderer.unmount).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => {
            expect(initialRenderer.unmount).toHaveBeenCalledTimes(1);
            expect(fetchCatalogMock).toHaveBeenCalledTimes(2);
            expect(host).toHaveAttribute('data-state', 'catalog_loading');
            expect(screen.queryByTestId('generic-renderer-initial')).toBeNull();
        });

        refreshedCatalog.resolve(catalog);
        await waitFor(() => {
            expect(resolveRendererMock).toHaveBeenCalledTimes(2);
            expect(loadRenderer).toHaveBeenCalledTimes(2);
            expect(host).toHaveAttribute('data-state', 'component_loading');
        });

        refreshedComponent.resolve(refreshedRenderer.loaded);
        await waitFor(() => {
            expect(refreshedRenderer.mount).toHaveBeenCalledTimes(1);
            expect(host).toHaveAttribute('data-state', 'ready');
            expect(screen.getByTestId('generic-renderer-refreshed')).toBeInTheDocument();
        });
        expectPublicCompatibility();

        unmount();
        await waitFor(() => {
            expect(refreshedRenderer.unmount).toHaveBeenCalledTimes(1);
        });
    });

    it('publishes an unavailable renderer without loading an interface', async () => {
        fetchCatalogMock.mockResolvedValue(catalog);
        resolveRendererMock.mockReturnValue({
            status: 'unavailable',
            reason: 'renderer_missing',
            descriptor,
        });

        render(ToolHost, {toolCode: TOOL_CODE});
        const host = screen.getByTestId('tool-host');

        await waitFor(() => {
            expect(host).toHaveAttribute('data-state', 'unavailable');
            expect(screen.getByTestId('tool-host-unavailable')).toHaveAttribute('data-reason', 'renderer_missing');
        });

        expect(resolveRendererMock).toHaveBeenCalledWith(catalog, TOOL_CODE);
        expect(screen.queryByTestId('tool-host-renderer')).toBeNull();
        expect(screen.getByTestId('tool-host-refresh')).toBeEnabled();
        expectPublicCompatibility();
        expect(notifyMock).toHaveBeenCalledWith(
            expect.objectContaining({
                name: 'tool.host.unavailable',
                detail: {code: 'renderer_missing', unavailable: 0},
            }),
        );
    });
});
