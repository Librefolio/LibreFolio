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
import {tick, type ComponentProps} from 'svelte';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {ChainStep, ProviderInfo} from '$lib/utils/currency/currencyGraph';
import {findConversionPaths, getCachedFxProviders, refreshFxProviderReadiness} from '$lib/stores/currencyGraphStore';
import FxProviderSelect from './FxProviderSelect.svelte';

vi.mock('$lib/stores/currencyGraphStore', async () => {
    const {writable} = await import('svelte/store');
    return {
        findConversionPaths: vi.fn(),
        getCachedFxProviders: vi.fn(),
        // N3c: the readiness is read again after a save, and the picker redraws on the version
        refreshFxProviderReadiness: vi.fn(async () => undefined),
        fxProvidersVersion: writable(0),
    };
});

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

    it('asks to try again shortly, instead of saying no path exists, when a provider came without its currencies', async () => {
        await setupI18n();
        // B-4: ECB too slow to list its currencies right after a restart. No route is found because ECB has no edges yet.
        graphReturns([], [{...ECB, target_currencies: [], currencies_unavailable: true}, FED, BOE, MANUAL]);
        mount();

        await settled();

        expect(screen.getByTestId('fx-route-unavailable')).toBeInTheDocument();
        expect(screen.queryByTestId('fx-route-none')).toBeNull();
    });

    it('does not list a provider whose currencies are unknown among those that cannot serve the pair', async () => {
        await setupI18n();
        graphReturns([CHAIN], [{...ECB, target_currencies: [], currencies_unavailable: true}, FED, BOE, MANUAL]);
        mount();
        await settled();
        const picker = await openPicker();

        // BOE really does not serve EUR→GBP; ECB is unknown, and «cannot serve» would be a guess.
        expect(within(picker).getByTestId('fx-route-unusable')).toHaveTextContent('BOE');
        expect(within(picker).getByTestId('fx-route-unusable')).not.toHaveTextContent('ECB');
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

    describe('the providers legend: a click shows the tooltip, a double click opens the guide (R1-C of project 67)', () => {
        /** The legend entry of a provider, in the open picker. */
        async function legendItem(code: string): Promise<HTMLElement> {
            graphReturns([DIRECT], [{...ECB, docs_url: '/mkdocs/user/fx/providers/ecb/'}, FED, BOE, MANUAL]);
            await setupI18n();
            mount();
            await settled();
            const picker = await openPicker();
            const item = within(picker)
                .getAllByTestId('fx-provider-legend-item')
                .find((candidate) => candidate.getAttribute('data-provider') === code);
            if (!item) throw new Error(`no legend entry for ${code}`);
            return item;
        }

        it('a click only shows the tooltip: nothing opens, the link does not navigate', async () => {
            const open = vi.spyOn(window, 'open').mockReturnValue(null);
            const item = await legendItem('ECB');
            // fireEvent answers false when a handler prevented the default: the link did not navigate.
            expect(await fireEvent.click(item, {detail: 1, button: 0})).toBe(false);
            expect(open).not.toHaveBeenCalled();
            open.mockRestore();
        });

        it('a double click opens the provider guide in a new tab', async () => {
            const open = vi.spyOn(window, 'open').mockReturnValue(null);
            const item = await legendItem('ECB');
            await fireEvent.dblClick(item);
            expect(open).toHaveBeenCalledTimes(1);
            expect(open.mock.calls[0][0]).toBe('/mkdocs/user/fx/providers/ecb/');
            expect(open.mock.calls[0][1]).toBe('_blank');
            open.mockRestore();
        });

        it('the keyboard keeps the link: Enter (a click with no pointer) is not cancelled', async () => {
            const item = await legendItem('ECB');
            expect(item.tagName).toBe('A');
            expect(item.getAttribute('href')).toBe('/mkdocs/user/fx/providers/ecb/');
            expect(await fireEvent.click(item, {detail: 0})).toBe(true);
        });

        it('the keyboard reads the description: a focus shows the tooltip', async () => {
            const item = await legendItem('ECB');
            await fireEvent.focusIn(item);
            await waitFor(() => expect(screen.getByTestId('tooltip-content')).toBeInTheDocument());
        });

        it('a click with a modifier key keeps the link too', async () => {
            const item = await legendItem('ECB');
            expect(await fireEvent.click(item, {detail: 1, button: 0, ctrlKey: true})).toBe(true);
        });
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

    // 81 U34 (testlist 7.2/7.6): the legend of the providers drew only their initials, while the routes below drew the
    // icon. One piece draws the icon for both: a provider that carries one shows it in the legend too, one without shows its initials.
    it('draws the icon in the providers legend, as in the routes, and the initials for a provider without one', async () => {
        await setupI18n();
        graphReturns([DIRECT, CHAIN], [{...ECB, icon_url: 'https://cdn.test/ecb.png'}, FED, BOE, MANUAL]);
        mount();
        await settled();
        const picker = await openPicker();

        const legend = (code: string) => {
            const item = within(picker)
                .getAllByTestId('fx-provider-legend-item')
                .find((candidate) => candidate.getAttribute('data-provider') === code);
            if (!item) throw new Error(`no legend entry for ${code}`);
            return item;
        };
        const ecb = legend('ECB').querySelector<HTMLImageElement>('img[alt="ECB"]');
        expect(ecb, 'the legend entry of a provider with an icon draws no icon').not.toBeNull();
        expect(ecb!.src).toContain('cdn.test/ecb.png');
        expect(legend('FED').querySelector('img'), 'a provider with no icon is drawn with one').toBeNull();
        expect(legend('FED').textContent, 'a provider with no icon shows no initials').toContain('FE');
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

    it('shows an info note with the info icon, and a warning with the warning icon (lane 75)', async () => {
        await setupI18n();
        // ECB's note is a fact to know (info level, like FED's weekly release); BOE's is a warning. A route takes the
        // most serious level of its providers' notes; the icon follows it.
        graphReturns([DIRECT, CHAIN], [{...ECB, warning_i18n: {en: 'Published weekly'}, warning_level: 'info'}, {...FED, warning_i18n: {en: 'Monthly only'}, warning_level: 'warning'}, BOE, MANUAL]);
        mount();
        await settled();
        const picker = await openPicker();

        const direct = within(picker).getByTestId('fx-route-direct-ECB');
        expect(direct).toHaveAttribute('data-warnings', '1');
        expect(direct).toHaveAttribute('data-warning-level', 'info');
        expect(within(direct).getByTestId('fx-route-note-icon')).toHaveAttribute('data-level', 'info');

        // The chain ECB→FED carries both notes: the warning wins.
        await fireEvent.click(within(picker).getByTestId('fx-route-chain-toggle-2'));
        const chain = within(picker).getByTestId('fx-route-chain-2step-ECB-FED');
        expect(chain).toHaveAttribute('data-warnings', '2');
        expect(chain).toHaveAttribute('data-warning-level', 'warning');
        expect(within(chain).getByTestId('fx-route-note-icon')).toHaveAttribute('data-level', 'warning');
    });

    it('shows no warnings when no provider on the route carries one', async () => {
        await setupI18n();
        // The default fixture has no warnings — a route must not manufacture one.
        mount();
        await settled();
        const picker = await openPicker();
        expect(within(picker).getByTestId('fx-route-direct-ECB')).toHaveAttribute('data-warnings', '0');
    });

    // Drawing 200–400 chain buttons in jsdom takes a few seconds on a loaded machine: a wider timeout, not a wait.
    describe('a chain group larger than the picker draws at once (lane 75, L2d, developer decision «b1»)', {timeout: 30_000}, () => {
        /** 250 two-step chains EUR → Z000…Z249 → GBP: more than the 200 a group draws at once. */
        const MANY: ChainStep[][] = Array.from({length: 250}, (_, i) => {
            const via = `Z${String(i).padStart(3, '0')}`;
            return [
                {from: 'EUR', to: via, provider: 'ECB'},
                {from: via, to: 'GBP', provider: 'FED'},
            ];
        });
        const chainButtons = (picker: HTMLElement) => picker.querySelectorAll('[data-testid^="fx-route-chain-2step-"]');
        const keyOf = (i: number) => `EUR-Z${String(i).padStart(3, '0')}:ECB|Z${String(i).padStart(3, '0')}-GBP:FED`;

        it('draws the first 200 chains of a group in their order, and the rest on request', async () => {
            await setupI18n();
            graphReturns(MANY);
            mount();
            await settled();
            const picker = await openPicker();

            // No direct route: the 2-step group opens by itself, capped at 200.
            expect(chainButtons(picker)).toHaveLength(200);
            expect(within(picker).getByTestId('fx-route-chain-toggle-2')).toHaveTextContent('250');
            const more = within(picker).getByTestId('fx-route-chain-more-2');
            expect(more).toHaveAttribute('data-hidden', '50');
            // Today's order is kept: the first drawn is the first of the sorted list, the 201st is not drawn.
            expect(chainButtons(picker)[0]).toHaveAttribute('data-route-key', keyOf(0));
            expect(picker.querySelector(`[data-route-key="${keyOf(200)}"]`)).toBeNull();

            await fireEvent.click(more);
            expect(chainButtons(picker)).toHaveLength(250);
            expect(within(picker).queryByTestId('fx-route-chain-more-2')).toBeNull();
        });

        it('searches every chain of the group, those beyond the first 200 included', async () => {
            await setupI18n();
            graphReturns(MANY);
            mount();
            await settled();
            const picker = await openPicker();

            await fireEvent.input(within(picker).getByTestId('fx-route-search'), {target: {value: 'z240'}});

            expect(chainButtons(picker)).toHaveLength(1);
            expect(chainButtons(picker)[0]).toHaveAttribute('data-route-key', keyOf(240));
            expect(within(picker).queryByTestId('fx-route-chain-more-2')).toBeNull();
        });

        it('draws 200 again when the search changes, whatever was shown before', async () => {
            await setupI18n();
            graphReturns(MANY);
            mount();
            await settled();
            const picker = await openPicker();
            await fireEvent.click(within(picker).getByTestId('fx-route-chain-more-2'));
            expect(chainButtons(picker)).toHaveLength(250);

            // 'fed' matches every chain: a new search starts from the first 200 again.
            await fireEvent.input(within(picker).getByTestId('fx-route-search'), {target: {value: 'fed'}});
            expect(chainButtons(picker)).toHaveLength(200);
            expect(within(picker).getByTestId('fx-route-chain-more-2')).toHaveAttribute('data-hidden', '50');
        });

        it('draws 200 again when the search is cleared, after «show more» with no search', async () => {
            await setupI18n();
            graphReturns(MANY);
            mount();
            await settled();
            const picker = await openPicker();
            await fireEvent.click(within(picker).getByTestId('fx-route-chain-more-2'));
            await fireEvent.input(within(picker).getByTestId('fx-route-search'), {target: {value: 'z24'}});

            await fireEvent.click(within(picker).getByTestId('fx-route-search-clear'));

            expect(chainButtons(picker)).toHaveLength(200);
            expect(within(picker).getByTestId('fx-route-chain-more-2')).toHaveAttribute('data-hidden', '50');
        });
    });
});

// =========================================================================
// Project 76, N3c — a route through a provider that is not configured is switched off (mock section 1.3)
// =========================================================================

describe('FxProviderSelect — a route through a provider to configure (76 N3c)', () => {
    /** FED needs a key: the 2-step chain EUR→USD→GBP goes through it; the direct ECB route does not. */
    const FED_OFF: ProviderInfo = {...FED, configured: false, missing_settings: ['api_key'], missing_reason: 'missing_fields', invalid_variables: []};
    const chainRow = (picker: HTMLElement) => picker.querySelector<HTMLElement>(`[data-route-key="${CHAIN_KEY}"]`);

    beforeEach(() => {
        vi.clearAllMocks();
        graphReturns([DIRECT, CHAIN], [ECB, FED_OFF, BOE, MANUAL]);
    });

    it('N3c-1: the route is switched off in the picker; a touch asks the parent to explain (onneedssetup) and adds nothing', async () => {
        await setupI18n();
        const onneedssetup = vi.fn();
        const {onSelectionChange} = mount({onneedssetup});
        await settled();
        const picker = await openPicker();
        await fireEvent.click(within(picker).getByTestId('fx-route-chain-toggle-2'));

        const chain = await waitFor(() => {
            const row = chainRow(picker);
            if (!row) throw new Error('the chain is not drawn yet');
            return row;
        });
        expect(chain).toHaveAttribute('data-needs-setup', 'true');
        expect(chain).toHaveAttribute('aria-disabled', 'true');
        expect(chain).not.toHaveAttribute('disabled');
        expect(within(picker).getByTestId('fx-route-direct-ECB')).toHaveAttribute('data-needs-setup', 'false');

        await fireEvent.click(chain);

        expect(onneedssetup).toHaveBeenCalledTimes(1);
        expect(onneedssetup.mock.calls[0][0]).toMatchObject({code: 'FED', configured: false, missing_reason: 'missing_fields'});
        expect(onSelectionChange).not.toHaveBeenCalled();
        expect(chainRow(picker), 'still on offer, switched off').toHaveAttribute('data-needs-setup', 'true');
    });

    it('N3c-2: a provider the pair already uses in a saved route is never switched off: its routes are added as today', async () => {
        await setupI18n();
        const onneedssetup = vi.fn();
        const {onSelectionChange} = mount({savedProviderCodes: ['FED'], onneedssetup});
        await settled();
        const picker = await openPicker();
        await fireEvent.click(within(picker).getByTestId('fx-route-chain-toggle-2'));

        const chain = await waitFor(() => {
            const row = chainRow(picker);
            if (!row) throw new Error('the chain is not drawn yet');
            return row;
        });
        expect(chain).toHaveAttribute('data-needs-setup', 'false');
        await fireEvent.click(chain);
        expect(onSelectionChange).toHaveBeenCalledWith([CHAIN]);
        expect(onneedssetup).not.toHaveBeenCalled();
    });

    it('N3c-3: a saved route through it stays, with the yellow triangle; a touch on it asks the parent to explain', async () => {
        await setupI18n();
        const onneedssetup = vi.fn();
        mount({selectedRoutes: [DIRECT, CHAIN], savedProviderCodes: ['ECB', 'FED'], onneedssetup});
        await settled();

        const row = await waitFor(() => selectedRow(CHAIN_KEY));
        const triangle = within(row).getByTestId('fx-route-needs-setup');
        expect(triangle.getAttribute('title')).toBeTruthy();
        expect(within(selectedRow(DIRECT_KEY)).queryByTestId('fx-route-needs-setup'), 'a route through configured providers only has none').toBeNull();

        await fireEvent.click(triangle);
        expect(onneedssetup.mock.calls[0][0]).toMatchObject({code: 'FED'});
    });

    it('N3c-4: a list without the readiness fields (an older server) switches nothing off', async () => {
        await setupI18n();
        graphReturns([DIRECT, CHAIN]);
        mount();
        await settled();
        const picker = await openPicker();
        await fireEvent.click(within(picker).getByTestId('fx-route-chain-toggle-2'));
        await waitFor(() => expect(chainRow(picker)).not.toBeNull());
        expect(chainRow(picker)).toHaveAttribute('data-needs-setup', 'false');
        expect(refreshFxProviderReadiness, 'the readiness is read again when the picker opens').toHaveBeenCalled();
    });

    it('lane 75 L20b: an answer that arrives after a newer request is ignored — only the latest pair is drawn', async () => {
        await setupI18n();
        const deferred = <T>() => {
            let resolve!: (value: T) => void;
            const promise = new Promise<T>((res) => (resolve = res));
            return {promise, resolve};
        };
        const first = deferred<ChainStep[][]>();
        const second = deferred<ChainStep[][]>();
        const OLD_PAIR: ChainStep[] = [{from: 'EUR', to: 'GBP', provider: 'ECB'}];
        const NEW_PAIR: ChainStep[] = [{from: 'USD', to: 'GBP', provider: 'FED'}];
        vi.mocked(getCachedFxProviders).mockReturnValue([ECB, FED, BOE, MANUAL]);
        vi.mocked(findConversionPaths)
            .mockReset()
            .mockImplementationOnce(() => first.promise)
            .mockImplementationOnce(() => second.promise);

        const {rerender} = mount();
        await waitFor(() => expect(findConversionPaths).toHaveBeenCalledTimes(1));
        // The pair changes while the first search is still running.
        await rerender({baseCurrency: 'USD'});
        await waitFor(() => expect(findConversionPaths).toHaveBeenCalledTimes(2));
        expect(vi.mocked(findConversionPaths).mock.calls[1].slice(0, 2)).toEqual(['USD', 'GBP']);

        // The answers come back in REVERSE order: the newer one first, the stale one last.
        second.resolve([NEW_PAIR]);
        await second.promise;
        first.resolve([OLD_PAIR]);
        await first.promise;
        // The component's own continuation on each promise was registered first, so it has run; flush the DOM.
        await tick();

        const picker = await openPicker();
        expect(within(picker).getByTestId('fx-route-direct-FED')).toBeInTheDocument();
        expect(within(picker).queryByTestId('fx-route-direct-ECB'), 'the stale pair EUR→GBP must not be drawn').toBeNull();
    });
});
