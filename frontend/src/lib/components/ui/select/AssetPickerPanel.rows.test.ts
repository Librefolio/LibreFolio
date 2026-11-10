// @vitest-environment jsdom
/**
 * AssetPickerPanel — what its rows and groups say (Y2 FB-10), beside `AssetPickerPanel.test.ts`.
 *
 *  - the groups after the benchmarks are the Assets list's: yours, other users', watched (`assetScope`, one rule: held now);
 *  - a row writes its currency with the flag and its type as the design system's coloured badge, and a long type label gives way
 *    (capped, scrolling) instead of covering the asset's name;
 *  - the filter menus open out of the panel (viewport placement), never clipped by a short list.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {createRawSnippet} from 'svelte';
import {existsSync, readFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {assetTypeBadgeClass} from '$lib/utils/assetTypes';
import AssetPickerPanel from './AssetPickerPanel.svelte';
import {assetScope, type PickerAsset} from './assetPicker';

vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    ensureCurrenciesLoaded: vi.fn(async () => {}),
    getCurrencyInfo: (code: string) => ({code, name: code, symbol: code, flag_emoji: code === 'EUR' ? '🇪🇺' : '🇺🇸', country_codes: [], country_names: []}),
}));

beforeAll(async () => {
    await setupI18n();
});

const TEST_ID = 'probe-pick';

/** The lab's «+»: a button that opens and closes the multi panel through the `toggle` it is given. */
const openTrigger = createRawSnippet<[{toggle: () => void}]>((popover) => ({
    render: () => '<button type="button" data-testid="probe-plus">+</button>',
    setup: (button) => {
        const press = (): void => popover().toggle();
        button.addEventListener('click', press);
        return () => button.removeEventListener('click', press);
    },
}));

function asset(id: number, name: string, overrides: Partial<PickerAsset> = {}): PickerAsset {
    return {id, display_name: name, currency: 'EUR', asset_type: 'ETF', icon_url: null, active: true, ...overrides};
}

async function open(assets: PickerAsset[], extra: Record<string, unknown> = {}): Promise<HTMLElement> {
    render(AssetPickerPanel, {props: {mode: 'single', assets, blockedLabel: 'probe: blocked', testId: TEST_ID, ...extra}});
    await fireEvent.click(screen.getByTestId(`${TEST_ID}-trigger`));
    return screen.getByTestId(TEST_ID);
}

/** The headings and rows of the list, in order. */
function listOrder(root: HTMLElement): string[] {
    return within(root)
        .queryAllByTestId(/^search-select-(header|option)-/)
        .map((element) => (element.getAttribute('data-testid') ?? '').replace('search-select-', ''));
}

describe('assetScope', () => {
    it('reads what is held now: mine, else others, else watched', () => {
        expect(assetScope({held_by_me: true, held_by_others: true})).toBe('own');
        expect(assetScope({held_by_me: false, held_by_others: true})).toBe('others');
        expect(assetScope({held_by_me: false, held_by_others: false})).toBe('analysis');
        expect(assetScope({})).toBe('analysis');
    });

    it('is the declaration of the Assets list page, word for word (the copy guard of assetBrowse.ts, one more copy)', () => {
        const here = dirname(fileURLToPath(import.meta.url));
        const source = (file: string): string => readFileSync(file, 'utf8').replace(/\s+/g, ' ');
        const declaration = (file: string): string => {
            const text = source(file);
            const start = text.indexOf('function assetScope(');
            expect(start, `no assetScope declaration in ${file}`).toBeGreaterThan(-1);
            return text.slice(start, text.indexOf("return 'analysis'", start) + "return 'analysis'".length);
        };
        const page = resolve(here, '../../../../routes/(app)/assets/+page.svelte');
        expect(existsSync(page)).toBe(true);
        expect(declaration(resolve(here, 'assetPicker.ts'))).toBe(declaration(page));
    });
});

describe('AssetPickerPanel single: the groups after the benchmarks', () => {
    const BENCHMARKS = [{key: 'bench', label: 'Probe benchmarks', match: (candidate: PickerAsset) => candidate.is_benchmark === true}];
    const CATALOGUE = [
        asset(1, 'Mine Fund', {held_by_me: true, held_by_others: false}),
        asset(2, 'Their Fund', {held_by_me: false, held_by_others: true}),
        asset(3, 'Watched Fund', {held_by_me: false, held_by_others: false}),
        asset(4, 'Index Benchmark', {is_benchmark: true, held_by_me: true}),
        asset(5, 'Unflagged Fund'),
    ];

    it('lists yours, other users’ and watched after the benchmarks, with the Assets list’s own titles', async () => {
        const root = await open(CATALOGUE, {sections: BENCHMARKS, restLabel: 'Probe rest'});
        expect(listOrder(root)).toEqual(['header-__section:bench', 'option-4', 'header-__section:scope-own', 'option-1', 'header-__section:scope-others', 'option-2', 'header-__section:scope-analysis', 'option-3', 'header-__section:__rest', 'option-5']);
        // Same words as the Assets list's panels: no text of its own.
        const titles = ['scope-own', 'scope-others', 'scope-analysis'].map((key) => (within(root).getByTestId(`search-select-header-__section:${key}`).textContent ?? '').trim());
        expect(new Set(titles).size).toBe(3);
        for (const title of titles) expect(title).not.toMatch(/^[\w-]+(\.[\w-]+)+$/);
    });

    it('without flags the list is as before: the benchmarks, then the rest', async () => {
        const root = await open([asset(1, 'A'), asset(2, 'B', {is_benchmark: true})], {sections: BENCHMARKS, restLabel: 'Probe rest'});
        expect(listOrder(root)).toEqual(['header-__section:bench', 'option-2', 'header-__section:__rest', 'option-1']);
    });
});

describe('AssetPickerPanel single: a row', () => {
    it('writes the currency with its flag', async () => {
        const root = await open([asset(1, 'Alpha', {currency: 'EUR'})]);
        const row = within(root).getByTestId('search-select-option-1');
        const currency = within(row).getByTestId(`${TEST_ID}-currency-1`);
        expect(currency.textContent).toContain('🇪🇺');
        expect(currency.textContent).toContain('EUR');
    });

    it('writes the type as the design system’s coloured badge', async () => {
        const root = await open([asset(1, 'Alpha', {asset_type: 'STOCK'})]);
        const badge = within(within(root).getByTestId('search-select-option-1')).getByTestId(`${TEST_ID}-type-1`);
        for (const role of assetTypeBadgeClass('STOCK').split(' ')) expect(badge.classList.contains(role), `the badge carries ${role}`).toBe(true);
    });

    it('caps a long type label and lets it scroll, and leaves the asset’s name its room', async () => {
        const root = await open([asset(1, 'Alpha', {asset_type: 'ETF_REAL_ESTATE'})]);
        const row = within(root).getByTestId('search-select-option-1');
        const badge = within(row).getByTestId(`${TEST_ID}-type-1`);
        expect(badge.className, 'a long type label is capped').toMatch(/max-w-/);
        expect(badge.querySelector('.overflow-scroll-marquee'), 'and scrolls when it does not fit').not.toBeNull();
        const name = within(row).getByText('Alpha');
        expect(name.className).toContain('min-w-0');
        expect(name.className).toContain('flex-1');
    });
});

describe('AssetPickerPanel single: the filter menus', () => {
    it('open in viewport placement, so a short list does not clip them', async () => {
        const root = await open([asset(1, 'Alpha'), asset(2, 'Beta', {asset_type: 'STOCK'})]);
        await fireEvent.click(within(root).getByTestId(`${TEST_ID}-filter-type-button`));
        const menu = await waitFor(() => within(root).getByTestId(`${TEST_ID}-filter-type-panel`));
        expect(menu.style.position).toBe('fixed');
    });

    it('stay under their button in the lab’s multi list, which does not clip them', async () => {
        render(AssetPickerPanel, {props: {mode: 'multi', assets: [asset(1, 'Alpha'), asset(2, 'Beta', {asset_type: 'STOCK'})], blockedLabel: 'probe: blocked', testId: TEST_ID, trigger: openTrigger}});
        await fireEvent.click(screen.getByTestId('probe-plus'));
        const panel = await waitFor(() => screen.getByTestId(`${TEST_ID}-panel`));
        await fireEvent.click(within(panel).getByTestId(`${TEST_ID}-filter-type-button`));
        const menu = await waitFor(() => within(panel).getByTestId(`${TEST_ID}-filter-type-panel`));
        expect(menu.style.position, 'the lab’s list keeps its absolute menu: it measures the page growing under it').not.toBe('fixed');
    });
});
