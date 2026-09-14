// @vitest-environment jsdom
/**
 * ToolsHub — generic catalogue-card contract.
 *
 * These tests deliberately use synthetic, non-PAC descriptors. The hub owns the
 * card shell; individual tools own only their descriptor and renderer.
 *
 * The assertions use roles, test ids, fixture values, and DOM relationships.
 * jsdom cannot prove layout, so the whole-card link contract is represented by
 * the dedicated link being an empty direct child of the card while Docs remains
 * a separate action outside it.
 */
import {afterAll, afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';
import {getClientSessionUserId, transitionClientSession} from '$lib/stores/app/clientSession';
import type {VerifiedToolCatalog} from './contracts';
import ToolsHub from './ToolsHub.svelte';

const {afterNavigateMock, fetchCatalogMock, loadRendererMock, notifyMock, resolveRendererMock} = vi.hoisted(() => ({
    afterNavigateMock: vi.fn(),
    fetchCatalogMock: vi.fn(),
    loadRendererMock: vi.fn(),
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
vi.mock('$lib/features/onboarding/guideAnchors.svelte', () => ({guideAnchor: () => undefined}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: notifyMock}));
vi.mock('./client', () => ({fetchToolCatalog: fetchCatalogMock}));
vi.mock('./registry', () => ({resolveToolRenderer: resolveRendererMock}));

const READY_CODE = 'generic_ready_tool';
const UNAVAILABLE_CODE = 'generic_unavailable_tool';
const CONTRACT_VERSION = '7.4.1';
const UI_VERSION = '1.0.0';
const IMPLEMENTATION_VERSION = 'impl-secret-99';

function descriptor(toolCode: string, name: string, description: string) {
    return {
        tool_code: toolCode,
        contract_version: CONTRACT_VERSION,
        implementation_version: IMPLEMENTATION_VERSION,
        schema_fingerprint: 'f'.repeat(64),
        category: 'analysis',
        description,
        description_i18n_key: null,
        documentation: {path: `tools/${toolCode.replaceAll('_', '-')}`, version: CONTRACT_VERSION},
        icon_key: 'calculator',
        input_schema: {},
        name,
        name_i18n_key: null,
        operations: [{operation: 'analyze'}],
        output_schema: {},
        ui: {kind: 'custom', component_key: toolCode, version: UI_VERSION},
    } as const;
}

const readyDescriptor = descriptor(READY_CODE, 'Generic ready fixture', 'Ready fixture description');
const unavailableDescriptor = descriptor(UNAVAILABLE_CODE, 'Generic unavailable fixture', 'Unavailable fixture description');
const catalog = {
    catalog_version: 'fixture',
    items: [readyDescriptor, unavailableDescriptor],
    unavailable: [],
    policy: {client_timeout_ms: 30_000},
} as unknown as VerifiedToolCatalog;

const previousSession = getClientSessionUserId();
let accountSequence = 0;

beforeEach(() => {
    transitionClientSession(`tools-hub-card-test-${++accountSequence}`);
    afterNavigateMock.mockReset();
    fetchCatalogMock.mockReset();
    loadRendererMock.mockReset();
    notifyMock.mockReset();
    resolveRendererMock.mockReset();

    fetchCatalogMock.mockResolvedValue(catalog);
    loadRendererMock.mockResolvedValue({mount: vi.fn()});
    resolveRendererMock.mockImplementation((_catalog: VerifiedToolCatalog, toolCode: string) =>
        toolCode === READY_CODE
            ? {
                  status: 'ready',
                  binding: {
                      descriptor: readyDescriptor,
                      accountGeneration: 1,
                      peek: () => null,
                      load: loadRendererMock,
                  },
              }
            : {status: 'unavailable', reason: 'renderer_missing', descriptor: unavailableDescriptor},
    );
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

afterAll(() => {
    transitionClientSession(previousSession);
});

async function renderCatalog(): Promise<{readyCard: HTMLElement; unavailableCard: HTMLElement}> {
    render(ToolsHub);

    const readyCard = await screen.findByTestId(`tool-card-${READY_CODE}`);
    const unavailableCard = await screen.findByTestId(`tool-card-${UNAVAILABLE_CODE}`);
    await waitFor(() => {
        expect(within(readyCard).getAllByTestId('tool-open')).toHaveLength(1);
        expect(within(unavailableCard).getByTestId('tool-interface-unavailable')).toBeInTheDocument();
    });
    return {readyCard, unavailableCard};
}

function directCardChild(card: HTMLElement, descendant: Element): HTMLElement {
    let child = descendant;
    while (child.parentElement && child.parentElement !== card) child = child.parentElement;
    expect(child.parentElement).toBe(card);
    return child as HTMLElement;
}

function expectPublicCompatibility(card: HTMLElement, item: ReturnType<typeof descriptor>): void {
    const versions = within(card).getByTestId('tool-compatibility-versions');
    expect(versions).toHaveTextContent(`tools.backendVersion ${item.contract_version} · tools.uiVersion ${item.ui.version}`);
    expect(versions).not.toHaveTextContent(item.implementation_version);
}

describe('ToolsHub generic catalogue cards', () => {
    it('keeps the ready whole-card link and Docs as independent actions', async () => {
        const openWindow = vi.spyOn(window, 'open').mockImplementation(() => null);
        const {readyCard} = await renderCatalog();

        const openActions = within(readyCard).getAllByTestId('tool-open');
        expect(openActions).toHaveLength(1);
        const open = openActions[0];
        expect(open).toBeInstanceOf(HTMLAnchorElement);
        expect(open).toHaveAttribute('href', `/tools/${READY_CODE}`);
        expect(open.parentElement).toBe(readyCard);

        expect(open).toBeEmptyDOMElement();
        const title = within(readyCard).getByRole('heading', {level: 2});
        expect(title).toHaveTextContent(readyDescriptor.name);
        const titleRow = directCardChild(readyCard, title);

        const documentation = within(readyCard).getByTestId(`tool-docs-${READY_CODE}`);
        expect(directCardChild(readyCard, documentation)).toBe(titleRow);
        expect(documentation).toBeInstanceOf(HTMLButtonElement);
        expect(documentation).toBeEnabled();
        expect(open).not.toContainElement(documentation);
        await fireEvent.click(documentation);
        expect(openWindow).toHaveBeenCalledTimes(1);

        // This is backend-owned fixture metadata, not translated interface copy.
        const description = within(readyCard).getByText(readyDescriptor.description, {exact: true});
        expect(description).toBeInstanceOf(HTMLParagraphElement);
        expect(description).toHaveTextContent(readyDescriptor.description);
        expect(description.parentElement).toBe(readyCard);
        expect(titleRow).not.toContainElement(description);

        expectPublicCompatibility(readyCard, readyDescriptor);

        expect(within(readyCard).queryByTestId('tool-interface-unavailable')).toBeNull();

        const arrow = within(readyCard).getByTestId('tool-open-arrow');
        expect(arrow.parentElement).toBe(readyCard);
        expect(arrow).toHaveAttribute('aria-hidden', 'true');
    });

    it('keeps an unavailable generic card disabled and non-navigable', async () => {
        const {unavailableCard} = await renderCatalog();

        expect(within(unavailableCard).queryByRole('link')).toBeNull();
        const disabledOpen = within(unavailableCard).getByTestId('tool-open');
        expect(disabledOpen).toBeInstanceOf(HTMLButtonElement);
        expect(disabledOpen).toBeDisabled();

        const interfaceState = within(unavailableCard).getByTestId('tool-interface-unavailable');
        expect(interfaceState).toHaveAttribute('data-reason', 'renderer_missing');
        expect(interfaceState.parentElement).toBe(unavailableCard);

        expectPublicCompatibility(unavailableCard, unavailableDescriptor);
    });
});
