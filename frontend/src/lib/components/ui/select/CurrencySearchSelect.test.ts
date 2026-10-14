// @vitest-environment jsdom
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import CurrencySearchSelect from './CurrencySearchSelect.svelte';

const {ensureCurrenciesLoadedMock} = vi.hoisted(() => ({
    ensureCurrenciesLoadedMock: vi.fn<() => Promise<void>>(),
}));

vi.mock('$lib/stores/reference/currencyStore', () => ({
    ensureCurrenciesLoaded: ensureCurrenciesLoadedMock,
    getAllCurrencies: () => [
        {
            code: 'EUR',
            name: 'Euro fixture',
            symbol: '€',
            flag_emoji: '🇪🇺',
            country_codes: ['EU'],
            country_names: ['Fixture Europe'],
        },
        {
            code: 'USD',
            name: 'Dollar fixture',
            symbol: '$',
            flag_emoji: '🇺🇸',
            country_codes: ['US'],
            country_names: ['Fixture United States'],
        },
    ],
}));

describe('CurrencySearchSelect', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    beforeEach(() => {
        ensureCurrenciesLoadedMock.mockReset();
        ensureCurrenciesLoadedMock.mockResolvedValue();
    });

    it('forwards one stable test id to the SearchSelect root and trigger', async () => {
        const onchange = vi.fn();
        render(CurrencySearchSelect, {value: 'EUR', testId: 'report-currency', onchange});

        const root = screen.getByTestId('report-currency');
        const trigger = screen.getByTestId('report-currency-trigger');
        expect(root).toContainElement(trigger);

        await waitFor(() => expect(ensureCurrenciesLoadedMock).toHaveBeenCalledTimes(1));
        await fireEvent.click(trigger);
        await fireEvent.click(await screen.findByTestId('search-select-option-USD'));

        expect(onchange).toHaveBeenCalledExactlyOnceWith('USD');
    });
});
