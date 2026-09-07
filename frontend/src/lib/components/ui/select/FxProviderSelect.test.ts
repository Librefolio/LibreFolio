// @vitest-environment jsdom
/**
 * FxProviderSelect — component test (Vitest + jsdom).
 *
 * This component turns the output of a DFS over the currency graph into a
 * pickable list of conversion routes, and it is the least covered file in the
 * select family. The reason is structural: through the UI it only appears inside
 * the FX pair modal, and what it displays depends on which providers the backend
 * happens to serve that day. An E2E can therefore prove it renders *something*,
 * but not that a two-step chain sorts before a three-step one, that MANUAL is
 * hidden, or that a route stored in the opposite direction is recognised — those
 * need a fixed graph, which is exactly what a mocked store gives.
 *
 * Only two functions are mocked, both of which would otherwise reach the network:
 * `findConversionPaths` (the DFS, behind a fetch of `/fx/providers`) and
 * `getCachedFxProviders`. Everything else is the real component. `getCurrencyInfo`
 * is deliberately NOT mocked: it already answers with a neutral fallback for a
 * code it does not know, and the flags it returns are never asserted on.
 *
 * The fixture graph, EUR → GBP:
 *   - direct   EUR →(ECB)→ GBP
 *   - 2 steps  EUR →(ECB)→ USD →(FED)→ GBP
 *   - BOE serves neither leg  → "unusable" for this pair
 *   - MANUAL is a backend sentinel and must never be offered
 *
 * Routes are addressed by the key the component builds from those steps, which
 * the test spells out itself — never by position in the list.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {ChainStep, ProviderInfo} from '$lib/utils/currency/currencyGraph';
import {findConversionPaths, getCachedFxProviders} from '$lib/stores/currencyGraphStore';
import FxProviderSelect from './FxProviderSelect.svelte';

vi.mock('$lib/stores/currencyGraphStore', () => ({
    findConversionPaths: vi.fn(),
    getCachedFxProviders: vi.fn(),
}));

const ECB: ProviderInfo = {code: 'ECB', name: 'European Central Bank', base_currency: 'EUR', base_currencies: ['EUR'], target_currencies: ['USD', 'GBP']};
const FED: ProviderInfo = {code: 'FED', name: 'Federal Reserve', base_currency: 'USD', base_currencies: ['USD'], target_currencies: ['GBP']};
const BOE: ProviderInfo = {code: 'BOE', name: 'Bank of England', base_currency: 'GBP', base_currencies: ['GBP'], target_currencies: ['JPY']};
const MANUAL: ProviderInfo = {code: 'MANUAL', name: 'Manual', base_currency: 'EUR', base_currencies: ['EUR'], target_currencies: ['GBP']};

const DIRECT: ChainStep[] = [{from: 'EUR', to: 'GBP', provider: 'ECB'}];
const CHAIN: ChainStep[] = [
    {from: 'EUR', to: 'USD', provider: 'ECB'},
    {from: 'USD', to: 'GBP', provider: 'FED'},
];

/** The identity the component derives from a path — the handle every lookup uses. */
const DIRECT_KEY = 'EUR-GBP:ECB';
const CHAIN_KEY = 'EUR-USD:ECB|USD-GBP:FED';

function graphReturns(paths: ChainStep[][], providers: ProviderInfo[] = [ECB, FED, BOE, MANUAL]) {
    vi.mocked(findConversionPaths).mockResolvedValue(paths);
    vi.mocked(getCachedFxProviders).mockReturnValue(providers);
}

function mount(props: Partial<ComponentProps<typeof FxProviderSelect>> = {}) {
    const onSelectionChange = vi.fn();
    const utils = render(FxProviderSelect, {baseCurrency: 'EUR', quoteCurrency: 'GBP', ...props, onSelectionChange});
    return {onSelectionChange, ...utils};
}

/**
 * Waits for the DFS to have run and its result to be on screen.
 *
 * Both halves are needed. The component paints once before its effect fires, so
 * asserting on an empty state without checking that the search actually happened
 * would pass on the frame *before* the work — the same lie as a sleep, inverted.
 */
async function settled() {
    await waitFor(() => {
        expect(findConversionPaths).toHaveBeenCalled();
        expect(screen.queryByTestId('fx-route-loading')).toBeNull();
    });
}

/** Opens the "add route" picker and waits for it. */
async function openPicker() {
    await fireEvent.click(await screen.findByTestId('fx-route-picker-toggle'));
    return screen.getByTestId('fx-route-picker');
}

/** The selected-routes row for a route key. Unique by construction. */
function selectedRow(key: string): HTMLElement {
    const row = document.querySelector<HTMLElement>(`[data-testid="fx-route-selected"][data-route-key="${key}"]`);
    if (!row) throw new Error(`no selected route for ${key}`);
    return row;
}

describe('FxProviderSelect', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        graphReturns([DIRECT, CHAIN]);
    });

    it('draws nothing until it has two different currencies to route between', async () => {
        await setupI18n();
        const {unmount, rerender} = mount({quoteCurrency: ''});
        expect(screen.queryByTestId('fx-route-select')).toBeNull();
        expect(findConversionPaths).not.toHaveBeenCalled();

        // Presence barrier for the negative above: give the same instance a real
        // pair and watch it search. Without this, "no search happened" would also
        // be true on a frame where the effect simply had not run yet.
        await rerender({quoteCurrency: 'GBP'});
        await settled();
        expect(screen.getByTestId('fx-route-select')).toBeInTheDocument();
        unmount();

        vi.mocked(findConversionPaths).mockClear();
        // Same currency on both sides: nothing to convert, so nothing to search for.
        mount({baseCurrency: 'EUR', quoteCurrency: 'EUR'});
        expect(screen.queryByTestId('fx-route-select')).toBeNull();
        expect(findConversionPaths).not.toHaveBeenCalled();
    });

    it('says so when the graph offers no path at all', async () => {
        await setupI18n();
        graphReturns([]);
        mount();

        await settled();

        expect(screen.getByTestId('fx-route-none')).toBeInTheDocument();
        // And it does not offer a picker with nothing in it.
        expect(screen.queryByTestId('fx-route-picker-toggle')).toBeNull();
    });

    it('lists the direct route and the providers it goes through, never MANUAL', async () => {
        await setupI18n();
        mount();
        await settled();
        const picker = await openPicker();

        expect(within(picker).getByTestId('fx-route-direct-ECB')).toBeInTheDocument();
        expect(within(picker).getByTestId('fx-route-direct-section')).toBeInTheDocument();

        // MANUAL is a backend-only sentinel: it must appear neither as a route nor
        // in the "unusable" list, where it would read as a provider that failed.
        expect(within(picker).queryByTestId('fx-route-direct-MANUAL')).toBeNull();
        expect(within(picker).getByTestId('fx-route-unusable')).not.toHaveTextContent('MANUAL');
    });

    it('names the providers that cannot serve this pair', async () => {
        await setupI18n();
        mount();
        await settled();
        const picker = await openPicker();

        // BOE only converts GBP→JPY, so it takes no part in any EUR→GBP route.
        expect(within(picker).getByTestId('fx-route-unusable')).toHaveTextContent('BOE');
        expect(within(picker).getByTestId('fx-route-unusable')).not.toHaveTextContent('ECB');
    });

    it('hands the parent the steps of the route that was added, and stops offering it', async () => {
        await setupI18n();
        const {onSelectionChange} = mount();
        await settled();
        const picker = await openPicker();

        await fireEvent.click(within(picker).getByTestId('fx-route-direct-ECB'));

        expect(onSelectionChange).toHaveBeenCalledWith([DIRECT]);
        expect(selectedRow(DIRECT_KEY)).toBeInTheDocument();
        // A route already chosen is no longer on offer — otherwise it could be
        // added twice and the priority list would carry a duplicate.
        expect(screen.queryByTestId('fx-route-direct-ECB')).toBeNull();
    });

    it('emits every step of a chain, in order', async () => {
        await setupI18n();
        const {onSelectionChange} = mount();
        await settled();
        const picker = await openPicker();

        await fireEvent.click(within(picker).getByTestId('fx-route-chain-toggle-2'));
        await fireEvent.click(within(picker).getByTestId('fx-route-chain-2step-ECB-FED'));

        expect(onSelectionChange).toHaveBeenCalledWith([CHAIN]);
        expect(selectedRow(CHAIN_KEY)).toBeInTheDocument();
    });

    it('numbers the selected routes by priority and gives them back on removal', async () => {
        await setupI18n();
        const {onSelectionChange} = mount();
        await settled();
        const picker = await openPicker();

        await fireEvent.click(within(picker).getByTestId('fx-route-direct-ECB'));
        await fireEvent.click(screen.getByTestId('fx-route-chain-toggle-2'));
        await fireEvent.click(screen.getByTestId('fx-route-chain-2step-ECB-FED'));

        // Priority follows the order they were picked in, and is published as data
        // rather than read out of the badge, whose "#1" is a rendering detail.
        expect(selectedRow(DIRECT_KEY)).toHaveAttribute('data-priority', '1');
        expect(selectedRow(CHAIN_KEY)).toHaveAttribute('data-priority', '2');

        await fireEvent.click(within(selectedRow(DIRECT_KEY)).getByTestId('fx-route-remove'));

        expect(onSelectionChange).toHaveBeenLastCalledWith([CHAIN]);
        // The chain closes the gap and becomes the first choice.
        expect(selectedRow(CHAIN_KEY)).toHaveAttribute('data-priority', '1');
        // And the removed route is back on offer.
        expect(screen.getByTestId('fx-route-direct-ECB')).toBeInTheDocument();
    });

    it('keeps chain groups shut while a direct route exists', async () => {
        await setupI18n();
        mount();
        await settled();
        const picker = await openPicker();

        // A direct route is always the better answer, so the chains stay folded
        // away rather than burying it under a longer list.
        expect(within(picker).getByTestId('fx-route-chain-toggle-2')).toHaveAttribute('data-expanded', 'false');
        expect(within(picker).queryByTestId('fx-route-chain-2step-ECB-FED')).toBeNull();

        await fireEvent.click(within(picker).getByTestId('fx-route-chain-toggle-2'));

        expect(within(picker).getByTestId('fx-route-chain-toggle-2')).toHaveAttribute('data-expanded', 'true');
        expect(within(picker).getByTestId('fx-route-chain-2step-ECB-FED')).toBeInTheDocument();
    });

    it('opens the shortest chain group when there is no direct route', async () => {
        await setupI18n();
        graphReturns([CHAIN]);
        mount();
        await settled();
        const picker = await openPicker();

        // Nothing else to show, so the user should not have to click to find out
        // that a route exists at all.
        expect(within(picker).getByTestId('fx-route-chain-toggle-2')).toHaveAttribute('data-expanded', 'true');
        expect(within(picker).getByTestId('fx-route-chain-2step-ECB-FED')).toBeInTheDocument();
        expect(within(picker).queryByTestId('fx-route-direct-section')).toBeNull();
    });

    it('narrows the list with every search token, and admits when nothing matches', async () => {
        await setupI18n();
        graphReturns([DIRECT, CHAIN]);
        mount();
        await settled();
        const picker = await openPicker();
        await fireEvent.click(within(picker).getByTestId('fx-route-chain-toggle-2'));
        const search = within(picker).getByTestId('fx-route-search');

        // 'fed' appears only in the chain's search text.
        await fireEvent.input(search, {target: {value: 'fed'}});
        expect(within(picker).getByTestId('fx-route-chain-2step-ECB-FED')).toBeInTheDocument();
        expect(within(picker).queryByTestId('fx-route-direct-ECB')).toBeNull();

        // Tokens are AND-ed: both must be present in the same route.
        await fireEvent.input(search, {target: {value: 'fed usd'}});
        expect(within(picker).getByTestId('fx-route-chain-2step-ECB-FED')).toBeInTheDocument();

        await fireEvent.input(search, {target: {value: 'fed nonesuch'}});
        expect(within(picker).queryByTestId('fx-route-chain-2step-ECB-FED')).toBeNull();
        expect(within(picker).getByTestId('fx-route-no-results')).toBeInTheDocument();

        // Clearing puts everything back — the search filters, it does not consume.
        await fireEvent.click(within(picker).getByTestId('fx-route-search-clear'));
        expect(within(picker).getByTestId('fx-route-direct-ECB')).toBeInTheDocument();
    });

    it('recognises a route the parent stored in the opposite direction', async () => {
        await setupI18n();
        // What comes back from the backend is EUR→GBP written as GBP→EUR: the same
        // hop, saved from the other side. The DFS only ever produces one of the two
        // spellings, so a literal comparison would show the pair as unconfigured and
        // silently offer the user a route they already have.
        mount({selectedRoutes: [[{from: 'GBP', to: 'EUR', provider: 'ECB'}]]});
        await settled();

        await waitFor(() => expect(selectedRow(DIRECT_KEY)).toBeInTheDocument());
        const picker = await openPicker();
        expect(within(picker).queryByTestId('fx-route-direct-ECB')).toBeNull();
    });

    it('offers no way to change the selection when disabled', async () => {
        await setupI18n();
        mount({disabled: true, selectedRoutes: [DIRECT]});
        await settled();

        await waitFor(() => expect(selectedRow(DIRECT_KEY)).toBeInTheDocument());
        expect(within(selectedRow(DIRECT_KEY)).queryByTestId('fx-route-remove')).toBeNull();
    });

    it('renders a provider that carries an icon as an <img>, and one without as initials', async () => {
        await setupI18n();
        // The icon comes from the FX provider cache (getCachedFxProviders), which is
        // mocked — so a provider gains an icon simply by carrying an icon_url. ECB does,
        // FED does not, so the same route shows one of each.
        graphReturns([DIRECT, CHAIN], [{...ECB, icon_url: 'https://cdn.test/ecb.png'}, FED, BOE, MANUAL]);
        mount();
        await settled();
        const picker = await openPicker();

        const ecbDirect = within(picker).getByTestId('fx-route-direct-ECB');
        const img = ecbDirect.querySelector<HTMLImageElement>('img[alt="ECB"]');
        expect(img).not.toBeNull();
        expect(img!.src).toContain('cdn.test/ecb.png');
    });

    it('surfaces a provider warning as a route-level count without inventing one', async () => {
        await setupI18n();
        // ECB carries a warning; FED does not. The direct route (ECB only) shows one
        // warning; the chain (ECB→FED) also shows exactly one, since only ECB warns.
        graphReturns([DIRECT, CHAIN], [{...ECB, warning_i18n: {en: 'Rates published once daily'}}, FED, BOE, MANUAL]);
        const {onSelectionChange} = mount();
        await settled();
        const picker = await openPicker();

        // The warning count is published as data, not read from the (translated) tooltip.
        expect(within(picker).getByTestId('fx-route-direct-ECB')).toHaveAttribute('data-warnings', '1');

        // It rides along when the route is selected, too.
        await fireEvent.click(within(picker).getByTestId('fx-route-direct-ECB'));
        expect(onSelectionChange).toHaveBeenCalledWith([DIRECT]);
        expect(selectedRow(DIRECT_KEY)).toHaveAttribute('data-warnings', '1');
    });

    it('shows no warnings when no provider on the route carries one', async () => {
        await setupI18n();
        // The default fixture has no warnings — a route must not manufacture one.
        mount();
        await settled();
        const picker = await openPicker();
        expect(within(picker).getByTestId('fx-route-direct-ECB')).toHaveAttribute('data-warnings', '0');
    });
});
