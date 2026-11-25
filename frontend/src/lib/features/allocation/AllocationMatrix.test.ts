// @vitest-environment jsdom
/**
 * AllocationMatrix — Class × dimension of the whole portfolio (Vitest + jsdom): the grid the backend gave, the cells the filters keep
 * framed, a click that keeps one class, a column that is a bucket to take out, and the percentages that stay under privacy.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';

vi.mock('$lib/stores/reference/countryStore', () => ({
    ensureCountriesLoaded: async () => {},
    getCountryInfo: (iso3: string) => ({iso3, iso2: '', name: `Country ${iso3}`, flag_emoji: '🏳'}),
}));
vi.mock('$lib/stores/reference/sectorStore', () => ({
    ensureSectorsLoaded: async () => {},
    getSectorEmoji: () => '🏭',
    sectorEmojiVersion: () => 0,
}));

import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import AllocationMatrix from './AllocationMatrix.svelte';
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

const matrix = {
    rows: ['STOCK', 'BOND'],
    columns: ['USA', 'ITA', 'Unknown'],
    cells: [
        {asset_class: 'STOCK', key: 'USA', amount: '23600.00', share_of_portfolio: '29.50'},
        {asset_class: 'STOCK', key: 'ITA', amount: '3000.00', share_of_portfolio: '3.75'},
        {asset_class: 'BOND', key: 'ITA', amount: '10000.00', share_of_portfolio: '12.50'},
    ],
    unattributed: [{reason: 'no_country' as const, amount: '880.00'}],
};

function mount(overrides: Partial<AllocationResponse> = {}, filters: AllocationFilters = emptyFilters()) {
    const onchange = vi.fn();
    render(AllocationMatrix, {view: makeView({dimension: 'geography', applicable_buckets: ['Unknown'], matrix, ...overrides}), filters, onchange, testId: 'm'});
    return onchange;
}

const cell = (assetClass: string, key: string) => screen.getByTestId(`m-cell-${assetClass}-${key}`);

describe('drawing', () => {
    it('is nothing in the asset dimension, where the answer has no matrix', () => {
        mount({dimension: 'asset', matrix: null});
        expect(screen.queryByTestId('m')).toBeNull();
    });

    it('is a cell per class and bucket, with the backend’s share, and a dot where there is nothing', () => {
        mount();
        expect(cell('STOCK', 'USA').textContent).toContain('29');
        expect(cell('STOCK', 'USA')).toHaveAttribute('data-share', '29.50');
        expect(cell('BOND', 'USA').textContent).toBe('·');
        expect(cell('BOND', 'Unknown').textContent).toBe('·');
        expect(screen.getByTestId('m')).toHaveAttribute('data-dimension', 'geography');
    });

    it('lists under the table what has no column, with its reason', () => {
        mount();
        expect(screen.getByTestId('m-unattributed').textContent).toContain('880');
        cleanup();
        mount({matrix: {...matrix, unattributed: [{reason: 'in_transit', amount: '0.00'}]}});
        expect(screen.queryByTestId('m-unattributed'), 'a zero row is not listed').toBeNull();
    });
});

describe('the selection', () => {
    it('frames every cell at the first opening (every class is in), but not a column taken out', () => {
        mount({}, {classes: null, types: [], excludeBuckets: ['Unknown'], excludeAssetIds: []});
        expect(cell('STOCK', 'USA')).toHaveAttribute('data-selected', 'true');
        expect(cell('BOND', 'ITA')).toHaveAttribute('data-selected', 'true');
        expect(cell('STOCK', 'Unknown')).toHaveAttribute('data-selected', 'false');
    });

    it('frames only the row of the class kept', () => {
        mount({}, {classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: []});
        expect(cell('STOCK', 'ITA')).toHaveAttribute('data-selected', 'true');
        expect(cell('BOND', 'ITA')).toHaveAttribute('data-selected', 'false');
    });
});

describe('clicking', () => {
    it('a cell, or the name of its class, keeps only that class; again on it, every class', async () => {
        const onchange = mount();
        await fireEvent.click(cell('BOND', 'ITA'));
        expect(onchange).toHaveBeenLastCalledWith({classes: ['BOND'], types: [], excludeBuckets: [], excludeAssetIds: []});
        await fireEvent.click(screen.getByTestId('m-class-STOCK'));
        expect(onchange).toHaveBeenLastCalledWith({classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: []});
        cleanup();

        const again = mount({}, {classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: []});
        await fireEvent.click(cell('STOCK', 'USA'));
        expect(again).toHaveBeenLastCalledWith({classes: null, types: [], excludeBuckets: [], excludeAssetIds: []});
    });

    it('a column that is a bucket the dimension lets the user take out toggles that exclusion; a country is no button', async () => {
        const onchange = mount();
        expect(screen.getByTestId('m-col-USA').tagName).toBe('SPAN');
        await fireEvent.click(screen.getByTestId('m-col-Unknown'));
        expect(onchange).toHaveBeenLastCalledWith({classes: null, types: [], excludeBuckets: ['Unknown'], excludeAssetIds: []});
        cleanup();

        const back = mount({}, {classes: null, types: [], excludeBuckets: ['Unknown'], excludeAssetIds: []});
        expect(screen.getByTestId('m-col-Unknown')).toHaveAttribute('data-excluded', 'true');
        await fireEvent.click(screen.getByTestId('m-col-Unknown'));
        expect(back).toHaveBeenLastCalledWith({classes: null, types: [], excludeBuckets: [], excludeAssetIds: []});
    });
});

describe('privacy', () => {
    it('keeps the percentages in the cells, masks the amounts (the tooltip and the line under the table), and shows them again', async () => {
        mount();
        expect(cell('STOCK', 'USA').getAttribute('title')).not.toContain(PRIVACY_PLACEHOLDER);
        setPrivacyEnabled(true);
        await Promise.resolve();
        await vi.waitFor(() => expect(cell('STOCK', 'USA').getAttribute('title')).toContain(PRIVACY_PLACEHOLDER));
        expect(cell('STOCK', 'USA').textContent, 'the percentage stays').toContain('29');
        expect(screen.getByTestId('m-unattributed').textContent).toContain(PRIVACY_PLACEHOLDER);
        setPrivacyEnabled(false);
        await Promise.resolve();
        await vi.waitFor(() => expect(cell('STOCK', 'USA').getAttribute('title')).not.toContain(PRIVACY_PLACEHOLDER));
    });
});
