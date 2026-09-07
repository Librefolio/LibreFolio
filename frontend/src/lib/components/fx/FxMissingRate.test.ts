// @vitest-environment jsdom
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import {writable} from 'svelte/store';

vi.mock('$app/navigation', () => ({goto: vi.fn()}));
vi.mock('$lib/stores/reference/currencyStore', () => ({
    ensureCurrenciesLoaded: vi.fn(),
    getCurrencyInfo: (code: string) => ({code, flag_emoji: '🏳️'}),
}));
vi.mock('$lib/stores/fx/fxCardInversionStore', () => ({
    isCardInverted: vi.fn(() => false),
    setCardInverted: vi.fn(),
}));
vi.mock('$lib/stores/currencyGraphStore', () => ({fxProvidersVersion: writable(0)}));

import FxPriceSummary from './FxPriceSummary.svelte';
import FxTable from './FxTable.svelte';

beforeAll(async () => {
    await setupI18n();
});

describe('FX missing-rate UI', () => {
    it('renders a missing detail summary state instead of formatting it as zero', () => {
        const {container} = render(FxPriceSummary, {
            lastRate: null,
            deltaPercent: null,
            layoutMode: 'oneRow',
            filtersStacked: false,
        });

        expect(screen.getByTestId('fx-price-summary-missing')).toHaveAttribute('data-fx-rate-state', 'missing');
        expect(container).not.toHaveTextContent('0.0000');
    });

    it('renders table rows with missing rates as missing and sorts them last', async () => {
        const {container} = render(FxTable, {
            data: [
                {slug: 'AAA-BBB', base: 'AAA', quote: 'BBB', data: [{date: '2024-01-01', rate: null, backwardFillInfo: null}], manualOnly: false, providers: []},
                {slug: 'CCC-DDD', base: 'CCC', quote: 'DDD', data: [{date: '2024-01-01', rate: 1.2, backwardFillInfo: null}], manualOnly: false, providers: []},
                {slug: 'EEE-FFF', base: 'EEE', quote: 'FFF', data: [{date: '2024-01-01', rate: 0.9, backwardFillInfo: null}], manualOnly: false, providers: []},
            ],
            loading: false,
        });

        const missing = container.querySelector('[data-fx-rate-state="missing"]');
        expect(missing).not.toBeNull();
        expect(container).not.toHaveTextContent('0.0000');

        await fireEvent.click(screen.getByTestId('dt-sort-rate'));
        expect([...container.querySelectorAll('tbody tr[data-row-id]')].map((row) => row.getAttribute('data-row-id'))).toEqual(['EEE-FFF', 'CCC-DDD', 'AAA-BBB']);

        await fireEvent.click(screen.getByTestId('dt-sort-rate'));
        expect([...container.querySelectorAll('tbody tr[data-row-id]')].map((row) => row.getAttribute('data-row-id'))).toEqual(['CCC-DDD', 'EEE-FFF', 'AAA-BBB']);
    });
});
