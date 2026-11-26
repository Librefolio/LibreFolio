// @vitest-environment jsdom
/**
 * AllocationChips — one chip per choice, a cross that takes it away (Vitest + jsdom).
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import AllocationChips from './AllocationChips.svelte';
import {emptyFilters, type AllocationFilters} from './allocationFilters';
import {makeView} from './allocation.fixture';

beforeAll(async () => {
    await setupI18n();
});
afterEach(cleanup);

const mount = (filters: AllocationFilters, view = makeView()) => {
    const onchange = vi.fn();
    render(AllocationChips, {filters, view, onchange, testId: 'c'});
    return onchange;
};

describe('AllocationChips', () => {
    it('draws nothing with no filter on', () => {
        mount(emptyFilters());
        expect(screen.queryByTestId('c')).toBeNull();
    });

    it('draws one chip per choice: a class kept, a bucket and an asset taken out', () => {
        mount({classes: ['STOCK'], types: [], excludeBuckets: ['Unknown'], excludeAssetIds: [2]});
        const chips = screen.getAllByTestId('c-chip').map((chip) => [chip.getAttribute('data-kind'), chip.getAttribute('data-value')]);
        expect(chips).toEqual([
            ['class', 'STOCK'],
            ['bucket', 'Unknown'],
            ['asset', '2'],
        ]);
        expect(screen.getAllByTestId('c-chip')[2], 'an excluded asset by its name').toHaveTextContent('Apple Inc.');
    });

    it('names an asset by its number before the answer that holds its name', () => {
        mount({classes: null, types: [], excludeBuckets: [], excludeAssetIds: [77]}, makeView({assets: []}));
        expect(screen.getByTestId('c-chip')).toHaveTextContent('#77');
    });

    it('the cross asks for the filters without that choice; the last class kept goes back to every class', async () => {
        const onchange = mount({classes: ['STOCK'], types: [], excludeBuckets: ['Unknown'], excludeAssetIds: []});
        const [classChip, bucketChip] = screen.getAllByTestId('c-chip');
        await fireEvent.click(within(bucketChip).getByTestId('c-chip-remove'));
        expect(onchange).toHaveBeenLastCalledWith({classes: ['STOCK'], types: [], excludeBuckets: [], excludeAssetIds: []});
        await fireEvent.click(within(classChip).getByTestId('c-chip-remove'));
        expect(onchange).toHaveBeenLastCalledWith({classes: null, types: [], excludeBuckets: ['Unknown'], excludeAssetIds: []});
    });
});
