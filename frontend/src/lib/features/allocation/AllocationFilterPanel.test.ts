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
        expect(onchange).toHaveBeenCalledWith({classes: ['STOCK', 'Liquidity'], excludeBuckets: [], excludeAssetIds: []});
    });

    it('shows a subset as it is', () => {
        mount(makeView(), {classes: ['STOCK'], excludeBuckets: [], excludeAssetIds: []});
        expect(['STOCK', 'BOND', 'Liquidity'].map((c) => on(`f-class-${c}`))).toEqual(['true', 'false', 'false']);
        expect(screen.getByTestId('f-classes-count')).toHaveTextContent(/1.*3/);
    });
});

describe('outside the 100 %', () => {
    it('lists only the buckets the backend says apply, and excludes one on a click', async () => {
        const {onchange} = mount(makeView({applicable_buckets: ['Unknown', 'Other']}));
        expect(screen.getByTestId('f-bucket-Unknown')).toBeInTheDocument();
        expect(screen.getByTestId('f-bucket-Other')).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('f-bucket-Other-switch'));
        expect(onchange).toHaveBeenCalledWith({classes: null, excludeBuckets: ['Other'], excludeAssetIds: []});
    });

    it('is not drawn when the dimension has no bucket to take out', () => {
        mount(makeView({applicable_buckets: []}));
        expect(screen.queryByTestId('f-excluded')).toBeNull();
    });

    it('shows a bucket excluded, and counts it', () => {
        mount(makeView(), {classes: null, excludeBuckets: ['Unknown'], excludeAssetIds: []});
        expect(on('f-bucket-Unknown')).toBe('true');
        expect(screen.getByTestId('f-excluded-count')).toHaveTextContent('1');
    });
});

describe('assets', () => {
    it('lists the assets of the classes switched on, and excludes one on a click', async () => {
        const {onchange} = mount(makeView(), {classes: ['STOCK'], excludeBuckets: [], excludeAssetIds: []});
        expect(screen.getByTestId('f-asset-1')).toBeInTheDocument();
        expect(screen.getByTestId('f-asset-2')).toBeInTheDocument();
        expect(screen.queryByTestId('f-asset-3'), 'a bond is not in the selection').toBeNull();
        await fireEvent.click(screen.getByTestId('f-asset-2-switch'));
        expect(onchange).toHaveBeenCalledWith({classes: ['STOCK'], excludeBuckets: [], excludeAssetIds: [2]});
    });

    it('shows an excluded asset off, and turning it on takes it out of the list of exclusions', async () => {
        const {onchange} = mount(makeView(), {classes: null, excludeBuckets: [], excludeAssetIds: [2, 99]});
        expect(on('f-asset-2')).toBe('false');
        await fireEvent.click(screen.getByTestId('f-asset-2-switch'));
        expect(onchange, 'the saved asset 99, absent today, is kept').toHaveBeenCalledWith({classes: null, excludeBuckets: [], excludeAssetIds: [99]});
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

        const {onchange} = mount(makeView(), {classes: ['STOCK'], excludeBuckets: [], excludeAssetIds: []});
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
