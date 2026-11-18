// @vitest-environment jsdom
/**
 * SignalAssetParamControl — the «comparison asset» parameter of the backend signals (Rolling Beta), Vitest + jsdom.
 *
 * RN-12 (A1, step 3 of 02/10/2026): the control moves from `AssetSelect` onto the shared asset panel
 * (`AssetPickerPanel mode="single"`), as the benchmark picker and the «Confronto Asset» signal already did. No asset is
 * created from here (the developer, 16/11/2026). What is pinned:
 *
 *   1. **The list is the shared panel's**: its type and currency filters, and each row's type badge.
 *   2. **Benchmarks first**, under their own title, the rest under another, each in `assetSelectOrder`'s order (active
 *      first, then by name) whatever order the cache holds: the panel never sorts, so the control must.
 *   3. **`excludeAssetIds` leaves the list, never the current choice**: the trigger still shows it.
 *   4. **Choosing hands the asset id to `onchange`**, a number, as the signal parameter stores it.
 *   5. **A cache that fails to load says so** (`signal-comparison-asset-error`), and the control stays on screen.
 *
 * Fixtures are this file's own; no translated text is asserted.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const cache = vi.hoisted(() => ({
    entries: [] as Array<Record<string, unknown> & {id: number}>,
    failure: null as Error | null,
}));

vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/reference/assetStore')>();
    const {readable} = await import('svelte/store');
    return {
        ...actual,
        assetStoreVersion: readable(0),
        ensureAssetsLoaded: vi.fn(() => (cache.failure ? Promise.reject(cache.failure) : Promise.resolve())),
        getAssetInfo: vi.fn((id: number) => cache.entries.find((asset) => asset.id === id) ?? null),
        // A fresh array each call, as the real store re-derives one.
        getAllAssets: vi.fn(() => cache.entries.map((asset) => ({...asset}))),
    };
});

/** The panel's currency menu reads flags from the currency cache: kept empty, and off the network. */
vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    ensureCurrenciesLoaded: vi.fn(async () => {}),
}));

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import SignalAssetParamControl from './SignalAssetParamControl.svelte';

const TEST_ID = 'signal-comparison-asset-select';

/** Two benchmarks and three plain assets, held in the cache out of order on purpose. */
const ZENITH_INDEX = {id: 11, display_name: 'Zenith Index', currency: 'USD', asset_type: 'INDEX', active: true, is_benchmark: true};
const ALPINE_INDEX = {id: 12, display_name: 'Alpine Index', currency: 'EUR', asset_type: 'INDEX', active: true, is_benchmark: true};
const QUARTZ = {id: 21, display_name: 'Quartz Equity', currency: 'EUR', asset_type: 'STOCK', active: true, is_benchmark: false};
const BASALT = {id: 22, display_name: 'Basalt Equity', currency: 'USD', asset_type: 'STOCK', active: true, is_benchmark: false};
/** Inactive: listed after the active ones whatever its name. */
const AMBER = {id: 23, display_name: 'Amber Matured Note', currency: 'EUR', asset_type: 'BOND', active: false, is_benchmark: false};

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    cache.entries = [QUARTZ, ZENITH_INDEX, AMBER, BASALT, ALPINE_INDEX];
    cache.failure = null;
});

function mount(props: {value?: unknown; excludeAssetIds?: number[]} = {}) {
    const onchange = vi.fn();
    render(SignalAssetParamControl, {props: {value: props.value ?? null, excludeAssetIds: props.excludeAssetIds, onchange}});
    return {onchange, trigger: screen.getByTestId(`${TEST_ID}-trigger`), control: screen.getByTestId(`${TEST_ID}-control`)};
}

async function openList(trigger: HTMLElement): Promise<HTMLElement> {
    await fireEvent.click(trigger);
    const listbox = await screen.findByRole('listbox');
    await waitFor(() => expect(within(listbox).queryAllByTestId(/^search-select-option-\d+$/).length, 'the list never filled').toBeGreaterThan(0));
    return listbox;
}

/** The open list in screen order: a section title by its key, an option by its asset id. */
function rowsOf(listbox: HTMLElement): Array<string | number> {
    return Array.from(listbox.querySelectorAll<HTMLElement>('[data-testid^="search-select-header-"], [data-testid^="search-select-option-"]')).map((row) => {
        const testId = row.getAttribute('data-testid') ?? '';
        return testId.startsWith('search-select-header-') ? testId.replace('search-select-header-', '') : Number(testId.replace('search-select-option-', ''));
    });
}

describe('SignalAssetParamControl — on the shared asset panel (RN-12)', () => {
    it('opens the shared panel: its filters, and each row with its type', async () => {
        const {trigger} = mount();
        await openList(trigger);

        expect(screen.getByTestId(`${TEST_ID}-filters`)).toBeInTheDocument();
        expect(screen.getByTestId(`${TEST_ID}-type-${QUARTZ.id}`)).toBeInTheDocument();
    });

    it('lists the benchmarks first, then the rest, each active first and by name', async () => {
        const {trigger} = mount();
        const listbox = await openList(trigger);

        expect(rowsOf(listbox)).toEqual(['__section:benchmark', ALPINE_INDEX.id, ZENITH_INDEX.id, '__section:__rest', BASALT.id, QUARTZ.id, AMBER.id]);
    });

    it('leaves an excluded asset out of the list, but never the current choice', async () => {
        const {trigger} = mount({value: QUARTZ.id, excludeAssetIds: [QUARTZ.id, BASALT.id]});

        await waitFor(() => expect(trigger.textContent).toContain(QUARTZ.display_name));
        const listbox = await openList(trigger);
        const offered = rowsOf(listbox).filter((row): row is number => typeof row === 'number');
        expect(offered).toContain(QUARTZ.id);
        expect(offered).not.toContain(BASALT.id);
    });

    it('hands the chosen asset id to onchange', async () => {
        const {trigger, onchange} = mount();
        const listbox = await openList(trigger);

        await fireEvent.click(within(listbox).getByTestId(`search-select-option-${BASALT.id}`));

        expect(onchange).toHaveBeenCalledExactlyOnceWith(BASALT.id);
    });

    it('says so when the asset cache fails to load', async () => {
        cache.failure = new Error('probe: the asset list did not load');
        const {control} = mount();

        await waitFor(() => expect(within(control).getByTestId('signal-comparison-asset-error')).toBeInTheDocument());
        expect(screen.getByTestId(`${TEST_ID}-trigger`)).toBeInTheDocument();
    });
});
