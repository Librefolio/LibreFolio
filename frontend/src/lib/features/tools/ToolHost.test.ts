// @vitest-environment jsdom
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import type {VerifiedToolCatalog} from './contracts';
import type {LoadedToolRenderer, ToolRendererBinding, ToolRendererMount, ToolRendererResolution} from './registry';
import ToolHost from './ToolHost.svelte';

const {fetchCatalogMock, peekCatalogMock, resolveRendererMock, afterNavigateMock} = vi.hoisted(() => ({
    fetchCatalogMock: vi.fn(),
    peekCatalogMock: vi.fn(),
    resolveRendererMock: vi.fn(),
    afterNavigateMock: vi.fn(),
}));

vi.mock('$app/navigation', () => ({afterNavigate: afterNavigateMock}));
vi.mock('./client', () => ({
    fetchToolCatalog: fetchCatalogMock,
    peekToolCatalog: peekCatalogMock,
}));
vi.mock('./registry', () => ({resolveToolRenderer: resolveRendererMock}));

const descriptor = {
    tool_code: 'pac_allocator',
    contract_version: '7.4.1',
    implementation_version: 'impl-secret-99',
    schema_fingerprint: 'f'.repeat(64),
    category: 'analysis',
    description: 'Fixture tool description',
    description_i18n_key: null,
    documentation: {path: 'tools/pac-allocator', version: '7.4.1'},
    icon_key: 'calculator',
    input_schema: {},
    name: 'Fixture PAC tool',
    name_i18n_key: null,
    operations: [{operation: 'analyze'}],
    output_schema: {},
    ui: {kind: 'custom', component_key: 'pac-allocator', version: '1.0.0'},
} as const;

const catalog = {
    catalog_version: '2',
    items: [descriptor],
    unavailable: [],
    policy: {client_timeout_ms: 30_000},
} as unknown as VerifiedToolCatalog;

let accountSequence = 0;

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((res) => {
        resolve = res;
    });
    return {promise, resolve};
}

function rendererFixture(): {
    renderer: LoadedToolRenderer;
    mount: ReturnType<typeof vi.fn>;
    unmount: ReturnType<typeof vi.fn>;
} {
    const unmount = vi.fn(async () => undefined);
    const mount = vi.fn((target: HTMLElement): ToolRendererMount => {
        const marker = target.ownerDocument.createElement('div');
        marker.dataset.testid = 'fixture-tool-renderer';
        target.appendChild(marker);
        return {unmount};
    });
    return {renderer: {mount}, mount, unmount};
}

function bindingFixture(options: {peek: () => LoadedToolRenderer | null; load: ToolRendererBinding['load']}): ToolRendererBinding {
    return {
        descriptor: descriptor as unknown as ToolRendererBinding['descriptor'],
        accountGeneration: getClientSessionGeneration(),
        peek: options.peek,
        load: options.load,
    };
}

function readyResolution(binding: ToolRendererBinding): ToolRendererResolution {
    return {status: 'ready', binding};
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    transitionClientSession(`tool-host-test-${++accountSequence}`);
    fetchCatalogMock.mockReset();
    peekCatalogMock.mockReset();
    resolveRendererMock.mockReset();
    afterNavigateMock.mockReset();
    peekCatalogMock.mockReturnValue(null);
    fetchCatalogMock.mockResolvedValue(catalog);
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

describe('ToolHost', () => {
    it('reuses the cached catalog and preloaded renderer for a warm first mount', async () => {
        const fixture = rendererFixture();
        const load = vi.fn().mockResolvedValue(fixture.renderer);
        const binding = bindingFixture({peek: () => fixture.renderer, load});
        peekCatalogMock.mockReturnValue(catalog);
        resolveRendererMock.mockReturnValue(readyResolution(binding));

        render(ToolHost, {toolCode: 'pac_allocator'});

        await waitFor(() => expect(screen.getByTestId('tool-host')).toHaveAttribute('data-state', 'ready'));
        expect(screen.getByTestId('fixture-tool-renderer')).toBeInTheDocument();
        expect(fetchCatalogMock).not.toHaveBeenCalled();
        expect(load).not.toHaveBeenCalled();
        expect(fixture.mount).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('tool-host-catalog-loading')).toBeNull();
        expect(screen.queryByTestId('tool-host-component-loading')).toBeNull();

        const versions = screen.getByTestId('tool-host-compatibility-versions');
        expect(versions).toHaveTextContent(`Backend/API ${descriptor.contract_version} · UI ${descriptor.ui.version}`);
        expect(versions).not.toHaveTextContent(descriptor.implementation_version);
        const refresh = screen.getByTestId('tool-host-refresh');
        const docs = screen.getByTestId('tool-host-docs');
        expect(refresh.getAttribute('aria-label')).toBeTruthy();
        expect(refresh.textContent).toContain(refresh.getAttribute('aria-label'));
        expect(docs.getAttribute('aria-label')).toBeTruthy();
        expect(docs.textContent).toContain(docs.getAttribute('aria-label'));
    });

    it('shows both honest loading phases for a cold direct URL', async () => {
        const catalogRequest = deferred<VerifiedToolCatalog>();
        const componentRequest = deferred<LoadedToolRenderer>();
        const fixture = rendererFixture();
        const binding = bindingFixture({peek: () => null, load: vi.fn(() => componentRequest.promise)});
        fetchCatalogMock.mockReturnValueOnce(catalogRequest.promise);
        resolveRendererMock.mockReturnValue(readyResolution(binding));

        render(ToolHost, {toolCode: 'pac_allocator'});

        expect(await screen.findByTestId('tool-host-catalog-loading')).toBeInTheDocument();
        expect(screen.getByTestId('tool-host')).toHaveAttribute('data-state', 'catalog_loading');

        catalogRequest.resolve(catalog);
        expect(await screen.findByTestId('tool-host-component-loading')).toBeInTheDocument();
        expect(screen.getByTestId('tool-host')).toHaveAttribute('data-state', 'component_loading');

        componentRequest.resolve(fixture.renderer);
        await waitFor(() => expect(screen.getByTestId('tool-host')).toHaveAttribute('data-state', 'ready'));
        expect(screen.getByTestId('fixture-tool-renderer')).toBeInTheDocument();
    });

    it('publishes an unavailable renderer without loading an interface', async () => {
        resolveRendererMock.mockReturnValue({
            status: 'unavailable',
            reason: 'renderer_missing',
            descriptor,
        });

        render(ToolHost, {toolCode: 'pac_allocator'});

        await waitFor(() => {
            expect(screen.getByTestId('tool-host')).toHaveAttribute('data-state', 'unavailable');
            expect(screen.getByTestId('tool-host-unavailable')).toHaveAttribute('data-reason', 'renderer_missing');
        });
        expect(screen.queryByTestId('tool-host-renderer')).toBeNull();
        expect(screen.getByTestId('tool-host-refresh')).toBeEnabled();
        const versions = screen.getByTestId('tool-host-compatibility-versions');
        expect(versions).toHaveTextContent(`Backend/API ${descriptor.contract_version} · UI ${descriptor.ui.version}`);
        expect(versions).not.toHaveTextContent(descriptor.implementation_version);
    });

    it('does not reload a mounted draft until the loss confirmation is accepted', async () => {
        const first = rendererFixture();
        const second = rendererFixture();
        let selectedRenderer = first.renderer;
        const binding = bindingFixture({
            peek: () => selectedRenderer,
            load: vi.fn(async () => selectedRenderer),
        });
        peekCatalogMock.mockReturnValue(catalog);
        resolveRendererMock.mockReturnValue(readyResolution(binding));

        render(ToolHost, {toolCode: 'pac_allocator'});
        await waitFor(() => expect(screen.getByTestId('tool-host')).toHaveAttribute('data-state', 'ready'));

        await fireEvent.click(screen.getByTestId('tool-host-refresh'));
        expect(screen.getByTestId('tool-host-reload-confirm')).toBeInTheDocument();
        expect(fetchCatalogMock).not.toHaveBeenCalled();
        expect(first.unmount).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        expect(screen.queryByTestId('tool-host-reload-confirm')).toBeNull();
        expect(fetchCatalogMock).not.toHaveBeenCalled();
        expect(first.unmount).not.toHaveBeenCalled();

        selectedRenderer = second.renderer;
        await fireEvent.click(screen.getByTestId('tool-host-refresh'));
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));

        await waitFor(() => expect(fetchCatalogMock).toHaveBeenCalledTimes(1));
        expect(fetchCatalogMock).toHaveBeenCalledWith({signal: expect.any(AbortSignal), reload: true});
        await waitFor(() => expect(first.unmount).toHaveBeenCalledTimes(1));
        await waitFor(() => expect(second.mount).toHaveBeenCalledTimes(1));
        expect(screen.getByTestId('tool-host')).toHaveAttribute('data-state', 'ready');
    });
});
