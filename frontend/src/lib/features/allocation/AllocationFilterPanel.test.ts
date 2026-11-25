// @vitest-environment jsdom
/**
 * AllocationFilterPanel — the three panels of the filters (Vitest + jsdom): classes, the buckets the backend says apply, the
 * assets of the classes on (with a search box above 10); controlled, so a click is a call with the next filters.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import AllocationFilterPanel from './AllocationFilterPanel.svelte';
import {emptyFilters, type AllocationFilters} from './allocationFilters';
import {makeView} from './allocation.fixture';
import type {AllocationResponse} from './allocationQuery';

beforeAll(async () => {
    await setupI18n();
});
beforeEach(() => setPrivacyEnabled(false));
afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

function mount(view: AllocationResponse = makeView(), filters: AllocationFilters = emptyFilters()) {
    const onchange = vi.fn();
    const rendered = render(AllocationFilterPanel, {view, filters, onchange, testId: 'f'});
    return {onchange, ...rendered};
}

const on = (id: string) => screen.getByTestId(id).getAttribute('data-on');

describe('classes', () => {
    it('lists the classes of the scope, all on at the first opening, with the count at the right', () => {
        mount();
        expect(['STOCK', 'BOND', 'Liquidity'].map((c) => on(`f-class-${c}`))).toEqual(['true', 'true', 'true']);
        expect(screen.getByTestId('f-classes-count')).toHaveTextContent(/3.*3/);
    });

    it('turning one off asks for the others', async () => {
        const {onchange} = mount();
        await fireEvent.click(screen.getByTestId('f-class-BOND-switch'));
        expect(onchange).toHaveBeenCalledWith({classes: ['STOCK', 'Liquidity'], types: [], excludeBuckets: [], excludeAssetIds: []});
    });

    it('shows a subset as it is', () => {
        mount(makeView(), {classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: []});
        expect(['STOCK', 'BOND', 'Liquidity'].map((c) => on(`f-class-${c}`))).toEqual(['true', 'false', 'false']);
        expect(screen.getByTestId('f-classes-count')).toHaveTextContent(/1.*3/);
    });
});

describe('two levels (86, D-13)', () => {
    const PART: AllocationFilters = {classes: ['BOND', 'Liquidity'], types: ['ETF_STOCK'], excludeBuckets: [], excludeAssetIds: []};
    const state = (id: string) => screen.getByTestId(id).getAttribute('data-state');

    it('a class of several types opens on them, each with its amount; a class of one does not open', async () => {
        mount();
        expect(screen.queryByTestId('f-type-ETF_STOCK')).toBeNull();
        expect(screen.queryByTestId('f-class-BOND-toggle')).toBeNull();
        const toggle = screen.getByTestId('f-class-STOCK-toggle');
        expect(toggle).toHaveAttribute('aria-expanded', 'false');
        await fireEvent.click(toggle);
        expect(toggle).toHaveAttribute('aria-expanded', 'true');
        expect(screen.getByTestId('f-class-STOCK').textContent).toMatch(/41[.,]?000/);
        expect(screen.getByTestId('f-type-ETF_STOCK').textContent).toMatch(/37[.,]?000/);
        expect(screen.getByTestId('f-type-STOCK').textContent).toMatch(/4[.,]?000/);
        await fireEvent.click(toggle);
        expect(screen.queryByTestId('f-type-ETF_STOCK')).toBeNull();
    });

    it('a type turned off asks for the others on their own', async () => {
        const {onchange} = mount();
        await fireEvent.click(screen.getByTestId('f-class-STOCK-toggle'));
        await fireEvent.click(screen.getByTestId('f-type-STOCK-switch'));
        expect(onchange).toHaveBeenCalledWith(PART);
    });

    it('a class in part starts open, is mixed, and one click turns all of it on', async () => {
        const {onchange} = mount(makeView(), PART);
        expect(state('f-class-STOCK')).toBe('mixed');
        expect([on('f-type-ETF_STOCK'), on('f-type-STOCK')]).toEqual(['true', 'false']);
        const lever = screen.getByTestId('f-class-STOCK-switch');
        expect(lever).toHaveAttribute('role', 'checkbox');
        expect(lever).toHaveAttribute('aria-checked', 'mixed');
        await fireEvent.click(lever);
        expect(onchange).toHaveBeenCalledWith(emptyFilters());
    });

    it('the switch of the title: on, off and mixed', async () => {
        const first = mount();
        expect(screen.getByTestId('f-classes-all')).toHaveAttribute('aria-checked', 'true');
        await fireEvent.click(screen.getByTestId('f-classes-all'));
        expect(first.onchange).toHaveBeenLastCalledWith({classes: [], types: [], excludeBuckets: [], excludeAssetIds: []});
        cleanup();
        const part = mount(makeView(), PART);
        expect(screen.getByTestId('f-classes-all')).toHaveAttribute('aria-checked', 'mixed');
        expect(screen.getByTestId('f-classes-count'), 'a class in part is kept').toHaveTextContent(/3.*3/);
        await fireEvent.click(screen.getByTestId('f-classes-all'));
        expect(part.onchange).toHaveBeenLastCalledWith(emptyFilters());
    });

    it('lists the assets of the types switched on, and the title switch acts on them', async () => {
        const {onchange} = mount(makeView(), PART);
        expect(screen.getByTestId('f-asset-1'), 'a stock ETF').toBeInTheDocument();
        expect(screen.queryByTestId('f-asset-2'), 'a share: its type is off').toBeNull();
        await fireEvent.click(screen.getByTestId('f-assets-all'));
        expect(onchange.mock.calls[0][0].excludeAssetIds).toEqual([1, 3]);
    });

    it('the assets’ title switch acts on the rows the search shows', async () => {
        const many = Array.from({length: 12}, (_, index) => ({asset_id: 100 + index, asset_class: 'STOCK', amount: '10.00', name: `Name ${index}`, ticker: index === 3 ? 'FIND' : null, asset_type: 'STOCK', icon_url: null}));
        const {onchange} = mount(makeView({assets: many}));
        await fireEvent.input(screen.getByTestId('f-assets-search'), {target: {value: 'find'}});
        await fireEvent.click(screen.getByTestId('f-assets-all'));
        expect(onchange.mock.calls[0][0].excludeAssetIds).toEqual([103]);
    });

    it('a class and its first type never share a name', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('f-class-STOCK-toggle'));
        const className = screen.getByTestId('f-class-STOCK-switch').getAttribute('aria-label');
        expect(className).not.toBe(screen.getByTestId('f-type-STOCK-switch').getAttribute('aria-label'));
    });
});

describe('rows (86, A2–A4)', () => {
    it('a class says its name and its amount, nothing between brackets', () => {
        mount();
        expect(screen.getByTestId('f-class-STOCK').textContent).not.toMatch(/[()]/);
    });

    it('the text takes the room left by the switch, in the three panels', () => {
        mount(makeView({applicable_buckets: ['Unknown', 'Other']}));
        for (const id of ['f-bucket-Unknown', 'f-asset-1']) expect(screen.getByTestId(id).firstElementChild, id).toHaveClass('min-w-0', 'flex-1');
        expect(screen.getByTestId('f-class-STOCK-toggle'), 'a class: the line that opens it').toHaveClass('min-w-0', 'flex-1');
    });

    it('an asset name scrolls when it does not fit, never cut by dots', () => {
        mount();
        const name = screen.getByTestId('f-asset-1-name');
        expect(name).toHaveClass('overflow-scroll-marquee');
        expect(name).not.toHaveClass('truncate');
        expect(name.getAttribute('title')).toBeTruthy();
    });
});

describe('outside the 100 %', () => {
    it('lists only the buckets the backend says apply, and excludes one on a click', async () => {
        const {onchange} = mount(makeView({applicable_buckets: ['Unknown', 'Other']}));
        expect(screen.getByTestId('f-bucket-Unknown')).toBeInTheDocument();
        expect(screen.getByTestId('f-bucket-Other')).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('f-bucket-Other-switch'));
        expect(onchange).toHaveBeenCalledWith({classes: null, types: [], excludeBuckets: ['Other'], excludeAssetIds: []});
    });

    it('is not drawn when the dimension has no bucket to take out', () => {
        mount(makeView({applicable_buckets: []}));
        expect(screen.queryByTestId('f-excluded')).toBeNull();
    });

    it('all on at first, counted; one taken out is off', () => {
        mount(makeView({applicable_buckets: ['Unknown', 'Other']}));
        expect([on('f-bucket-Unknown'), on('f-bucket-Other')]).toEqual(['true', 'true']);
        expect(screen.getByTestId('f-excluded-count')).toHaveTextContent(/2.*2/);
        cleanup();
        mount(makeView({applicable_buckets: ['Unknown', 'Other']}), {classes: null, types: [], excludeBuckets: ['Unknown'], excludeAssetIds: []});
        expect([on('f-bucket-Unknown'), on('f-bucket-Other')]).toEqual(['false', 'true']);
        expect(screen.getByTestId('f-excluded-count')).toHaveTextContent(/1.*2/);
    });

    it('the switch of its title: mixed, then everything on; from all on, everything out', async () => {
        const view = makeView({applicable_buckets: ['Unknown', 'Other']});
        const {onchange} = mount(view, {classes: null, types: [], excludeBuckets: ['Unknown'], excludeAssetIds: []});
        expect(screen.getByTestId('f-excluded-all')).toHaveAttribute('aria-checked', 'mixed');
        await fireEvent.click(screen.getByTestId('f-excluded-all'));
        expect(onchange).toHaveBeenLastCalledWith(emptyFilters());
        cleanup();
        const all = mount(view);
        await fireEvent.click(screen.getByTestId('f-excluded-all'));
        expect(all.onchange.mock.calls[0][0].excludeBuckets.sort()).toEqual(['Other', 'Unknown']);
    });
});

describe('assets', () => {
    it('lists the assets of the classes switched on, and excludes one on a click', async () => {
        const {onchange} = mount(makeView(), {classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: []});
        expect(screen.getByTestId('f-asset-1')).toBeInTheDocument();
        expect(screen.getByTestId('f-asset-2')).toBeInTheDocument();
        expect(screen.queryByTestId('f-asset-3'), 'a bond is not in the selection').toBeNull();
        await fireEvent.click(screen.getByTestId('f-asset-2-switch'));
        expect(onchange).toHaveBeenCalledWith({classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: [2]});
    });

    it('shows an excluded asset off, and turning it on takes it out of the list of exclusions', async () => {
        const {onchange} = mount(makeView(), {classes: null, types: [], excludeBuckets: [], excludeAssetIds: [2, 99]});
        expect(on('f-asset-2')).toBe('false');
        await fireEvent.click(screen.getByTestId('f-asset-2-switch'));
        expect(onchange, 'the saved asset 99, absent today, is kept').toHaveBeenCalledWith({classes: null, types: [], excludeBuckets: [], excludeAssetIds: [99]});
    });

    it('has a search box only above ten assets', async () => {
        mount();
        expect(screen.queryByTestId('f-assets-search')).toBeNull();
        cleanup();

        const many = Array.from({length: 12}, (_, index) => ({asset_id: 100 + index, asset_class: 'STOCK', amount: '10.00', name: `Name ${index}`, ticker: index === 3 ? 'FIND' : null, asset_type: 'STOCK', icon_url: null}));
        mount(makeView({assets: many}));
        const search = screen.getByTestId('f-assets-search') as HTMLInputElement;
        await fireEvent.input(search, {target: {value: 'find'}});
        expect(screen.getByTestId('f-asset-103')).toBeInTheDocument();
        expect(screen.queryByTestId('f-asset-100')).toBeNull();
        await fireEvent.input(search, {target: {value: 'zzz'}});
        expect(screen.getByTestId('f-assets-nomatch')).toBeInTheDocument();
    });
});

describe('remove filters', () => {
    it('appears only with a choice on, and asks for the first opening', async () => {
        mount();
        expect(screen.queryByTestId('f-clear')).toBeNull();
        cleanup();

        const {onchange} = mount(makeView(), {classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: []});
        await fireEvent.click(screen.getByTestId('f-clear'));
        expect(onchange).toHaveBeenCalledWith(emptyFilters());
    });
});

describe('privacy', () => {
    it('masks the amounts of the rows and shows them again, in place', async () => {
        mount();
        expect(screen.getByTestId('f-class-STOCK').textContent).not.toContain(PRIVACY_PLACEHOLDER);
        setPrivacyEnabled(true);
        await Promise.resolve();
        for (const id of ['f-class-STOCK', 'f-asset-1', 'f-bucket-Unknown']) expect(screen.getByTestId(id).textContent, id).toContain(PRIVACY_PLACEHOLDER);
        setPrivacyEnabled(false);
        await Promise.resolve();
        expect(screen.getByTestId('f-class-STOCK').textContent).not.toContain(PRIVACY_PLACEHOLDER);
    });
});
