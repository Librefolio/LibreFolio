// @vitest-environment jsdom
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {transitionClientSession} from '$lib/stores/app/clientSession';
import type {VerifiedToolCatalog} from './contracts';
import type {LoadedToolRenderer, ToolRendererBinding, ToolRendererResolution} from './registry';
import ToolsHub from './ToolsHub.svelte';

const {fetchCatalogMock, resolveRendererMock, afterNavigateMock, guideAnchorMock} = vi.hoisted(() => ({
    fetchCatalogMock: vi.fn(),
    resolveRendererMock: vi.fn(),
    afterNavigateMock: vi.fn(),
    guideAnchorMock: vi.fn(),
}));

vi.mock('$app/navigation', () => ({afterNavigate: afterNavigateMock}));
vi.mock('$lib/features/onboarding/guideAnchors.svelte', () => ({guideAnchor: guideAnchorMock}));
vi.mock('./client', () => ({fetchToolCatalog: fetchCatalogMock}));
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

const renderer: LoadedToolRenderer = {mount: vi.fn()};
let accountSequence = 0;

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

function readyResolution(load: ToolRendererBinding['load']): ToolRendererResolution {
    return {
        status: 'ready',
        binding: {
            descriptor: descriptor as unknown as ToolRendererBinding['descriptor'],
            accountGeneration: 1,
            peek: () => null,
            load,
        },
    };
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    transitionClientSession(`tools-hub-test-${++accountSequence}`);
    fetchCatalogMock.mockReset();
    resolveRendererMock.mockReset();
    afterNavigateMock.mockReset();
    guideAnchorMock.mockReset();
    fetchCatalogMock.mockResolvedValue(catalog);
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

describe('ToolsHub', () => {
    it('keeps a compatible card disabled until preload completes, then makes the whole card the tool link', async () => {
        const preload = deferred<LoadedToolRenderer>();
        const load = vi.fn(() => preload.promise);
        resolveRendererMock.mockReturnValue(readyResolution(load));
        const openWindow = vi.spyOn(window, 'open').mockImplementation(() => null);

        render(ToolsHub);

        const card = await screen.findByTestId('tool-card-pac_allocator');
        expect(guideAnchorMock).toHaveBeenCalledWith(screen.getByTestId('tools-hub'), 'tools.hub');
        await waitFor(() => expect(card).toHaveAttribute('data-interface-state', 'loading'));
        expect(within(card).queryByTestId('tool-open')).toBeNull();
        expect(within(card).getByTestId('tool-interface-loading')).toBeInTheDocument();

        preload.resolve(renderer);
        await waitFor(() => expect(card).toHaveAttribute('data-interface-state', 'ready'));

        const open = within(card).getByTestId('tool-open');
        const documentation = within(card).getByTestId('tool-docs-pac_allocator');
        expect(open).toHaveAttribute('href', '/tools/pac_allocator');
        expect(open.tagName).toBe('A');
        expect(open).not.toContainElement(documentation);

        // The only button in the card is the independent documentation action:
        // opening the tool itself is the full-card link, not a second visible button.
        expect(within(card).getAllByRole('button')).toEqual([documentation]);
        await fireEvent.click(documentation);
        expect(openWindow).toHaveBeenCalledTimes(1);

        const description = within(card).getByText(descriptor.description, {exact: true});
        expect(description.parentElement).toBe(card);
        const versions = within(card).getByTestId('tool-compatibility-versions');
        expect(versions).toHaveTextContent(`Backend/API ${descriptor.contract_version} · UI ${descriptor.ui.version}`);
        expect(versions).not.toHaveTextContent(descriptor.implementation_version);
        const arrow = within(card).getByTestId('tool-open-arrow');
        expect(arrow.parentElement).toBe(card);

        const refresh = screen.getByTestId('tools-hub-refresh');
        const refreshLabel = refresh.getAttribute('aria-label');
        expect(refreshLabel).toBeTruthy();
        expect(refresh.textContent).toContain(refreshLabel);
        expect(documentation.getAttribute('aria-label')).toBeTruthy();
        expect(documentation.textContent).toContain(documentation.getAttribute('aria-label'));
    });

    it('never exposes the card link when renderer preload fails', async () => {
        const load = vi.fn().mockRejectedValue(new Error('fixture chunk failure'));
        resolveRendererMock.mockReturnValue(readyResolution(load));

        render(ToolsHub);

        const card = await screen.findByTestId('tool-card-pac_allocator');
        await waitFor(() => expect(card).toHaveAttribute('data-interface-state', 'error'));
        expect(within(card).getByTestId('tool-interface-error')).toBeInTheDocument();
        expect(within(card).queryByTestId('tool-open')).toBeNull();
    });

    it('uses an explicit reload for the header refresh action', async () => {
        const load = vi.fn().mockResolvedValue(renderer);
        resolveRendererMock.mockReturnValue(readyResolution(load));

        render(ToolsHub);
        await waitFor(() => expect(screen.getByTestId('tools-hub')).toHaveAttribute('data-state', 'ready'));

        await fireEvent.click(screen.getByTestId('tools-hub-refresh'));
        await waitFor(() => expect(fetchCatalogMock).toHaveBeenCalledTimes(2));

        expect(fetchCatalogMock.mock.calls[0]?.[0]).toEqual({signal: expect.any(AbortSignal), reload: false});
        expect(fetchCatalogMock.mock.calls[1]?.[0]).toEqual({signal: expect.any(AbortSignal), reload: true});
    });
});
