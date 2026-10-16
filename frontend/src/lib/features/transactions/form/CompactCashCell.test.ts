// @vitest-environment jsdom
/**
 * CompactCashCell — component test (Vitest + jsdom).
 *
 * T1-a: the sync-down `$effect` must not rewrite the user's buffer mid-typing
 * when the incoming prop is *our own emission come back around* ("12," is
 * emitted normalized as "12."; the parent hands `{amount: "12."}` straight
 * back as `value`). Before the fix, the buffer was rewritten to the formatted
 * "12" on every such round trip, swallowing the decimal separator the user had
 * just pressed and corrupting every following keystroke.
 *
 * The bug lives in the parent ⇄ prop loop, so the test simulates the parent:
 * every `onChange` payload is fed back as the new `value` prop via `rerender`,
 * exactly what the form modal's `value={draft.cash} onChange={setCash}` does.
 *
 * Asserted only on the input's own value — never on a translated label.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import {fireEvent, render, screen, setupI18n} from '$test/component';

// CurrencySearchSelect (embedded) talks to the currency/FX stores, which hit
// the API — jsdom has no server. Stub the loaders to resolve and serve a
// fixed currency list; nothing about the amount input depends on them.
vi.mock('$lib/stores/reference/currencyStore', () => ({
    currencyStoreVersion: writable(0),
    ensureCurrenciesLoaded: vi.fn(async () => undefined),
    getAllCurrencies: vi.fn(() => [
        {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺'},
        {code: 'USD', name: 'US Dollar', symbol: '$', flag_emoji: '🇺🇸'},
    ]),
    getCurrencyInfo: vi.fn((code: string) => ({code, name: code, symbol: code, flag_emoji: '🏳️', country_codes: [], country_names: []})),
}));
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({
    fxRoutesVersion: writable(0),
    ensureFxRoutesLoaded: vi.fn(async () => undefined),
    getConfiguredCurrencySet: vi.fn(() => new Set(['EUR', 'USD'])),
}));
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));

import CompactCashCell from './CompactCashCell.svelte';

type CashValue = {amount: string; code: string};

/** Render the cell behind a faithful parent: onChange payloads come back as props. */
function mountWithParentLoop(initial: CashValue | null) {
    const emissions: Array<CashValue | null> = [];
    const props = {value: initial, defaultCode: 'EUR', testid: 'cc', onChange: (next: CashValue | null) => void emissions.push(next)};
    const rendered = render(CompactCashCell, props);
    /** The parent's half of the loop: store the emission, hand it back down. */
    const loopBack = async () => {
        const last = emissions[emissions.length - 1];
        await rendered.rerender({...props, value: last});
    };
    return {...rendered, emissions, loopBack};
}

const amountInput = (): HTMLInputElement => screen.getByTestId('cc-amount') as HTMLInputElement;

describe('CompactCashCell — decimal typing survives the prop round trip (T1-a)', () => {
    beforeEach(async () => {
        await setupI18n();
    });

    it('keeps the typed comma when the parent echoes the normalized value back', async () => {
        const {emissions, loopBack} = mountWithParentLoop({amount: '12', code: 'EUR'});
        expect(amountInput().value).toBe('12');

        // Type the decimal separator: "12," — the moment the bug bit.
        await fireEvent.input(amountInput(), {target: {value: '12,'}});
        expect(emissions.at(-1)).toEqual({amount: '12.', code: 'EUR'}); // normalized on the wire
        await loopBack();
        expect(amountInput().value, 'the separator must survive the parent echo').toBe('12,');

        // Continue typing the fraction.
        await fireEvent.input(amountInput(), {target: {value: '12,5'}});
        expect(emissions.at(-1)).toEqual({amount: '12.5', code: 'EUR'});
        await loopBack();
        expect(amountInput().value).toBe('12,5');
    });

    it('keeps trailing zeros the user is still typing', async () => {
        const {loopBack} = mountWithParentLoop({amount: '5', code: 'EUR'});

        // "5.20" mid-typing passes through "5.2" and must not collapse to "5.2"
        // being reformatted while the final 0 is on its way.
        await fireEvent.input(amountInput(), {target: {value: '5,2'}});
        await loopBack();
        await fireEvent.input(amountInput(), {target: {value: '5,20'}});
        await loopBack();
        expect(amountInput().value).toBe('5,20');
    });

    it('still syncs down a genuinely different external value', async () => {
        const {loopBack, rerender} = mountWithParentLoop({amount: '12', code: 'EUR'});

        await fireEvent.input(amountInput(), {target: {value: '12,5'}});
        await loopBack();
        expect(amountInput().value).toBe('12,5');

        // An external change (server refresh, reset, row switch) is not our own
        // emission: the number genuinely differs, so the buffer must follow.
        await rerender({value: {amount: '7.25', code: 'EUR'}, defaultCode: 'EUR', testid: 'cc', onChange: () => {}});
        expect(amountInput().value).toBe('7.25');
    });

    it('clears the buffer when the external value is cleared', async () => {
        const {loopBack, rerender} = mountWithParentLoop({amount: '12', code: 'EUR'});

        await fireEvent.input(amountInput(), {target: {value: '12,5'}});
        await loopBack();

        await rerender({value: null, defaultCode: 'EUR', testid: 'cc', onChange: () => {}});
        expect(amountInput().value).toBe('');
    });

    it('formats a zero-padded backend value on first render', async () => {
        mountWithParentLoop({amount: '6.000000', code: 'EUR'});
        // Pre-existing contract (Bugfix-4 §C14): display strips padding noise.
        expect(amountInput().value).toBe('6');
    });
});
