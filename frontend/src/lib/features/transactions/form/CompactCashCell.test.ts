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

/** Render the cell behind a faithful parent: onChange payloads come back as props. `extra` adds props (B-48's cap). */
function mountWithParentLoop(initial: CashValue | null, extra: Record<string, unknown> = {}) {
    const emissions: Array<CashValue | null> = [];
    const props = {value: initial, defaultCode: 'EUR', testid: 'cc', onChange: (next: CashValue | null) => void emissions.push(next), ...extra};
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

/**
 * B-47 — a focus and a blur on the cash change nothing.
 *
 * The amounts come back from the API padded to six decimals (`READ_MIN_SCALE`): `0.010000`. The cell shows them in their
 * display form (`0.01`), and its blur (`handleBlur`) emits that display form every time, whatever the parent holds: the
 * form's `setCash` stores `0.01` in place of `0.010000`, the Bulk's close guard (`serializeOps`, a text compare) sees a
 * change nobody made and asks to discard it. And the sync-down `$effect` compares the incoming amount with the buffer as
 * doubles (`localNum === incomingNum`), so a parent value that differs only past a double's precision is never shown.
 *
 * The contract: on blur the cell emits only when the amount, by exact value (`exactDecimalEqual`), or the code differs
 * from the current `value` prop; the sync compares by exact value. The display is the formatted value either way.
 */
describe('CompactCashCell — a blur emits only a change, the sync compares exact values (B-47)', () => {
    beforeEach(async () => {
        await setupI18n();
    });

    // Red today: the blur emits {amount: '0.01', code: 'EUR'}, the display form, for an amount nobody touched.
    it('B-47: focus and blur on an untouched amount of 0.010000 call no onChange, and the field still shows 0.01', async () => {
        const onChange = vi.fn();
        render(CompactCashCell, {value: {amount: '0.010000', code: 'EUR'}, defaultCode: 'EUR', testid: 'cc', onChange});
        expect(amountInput().value, 'premise: the padded amount is shown in its display form').toBe('0.01');

        await fireEvent.focus(amountInput());
        await fireEvent.blur(amountInput());

        expect(onChange, 'B-47: a focus and a blur emitted a change nobody made').not.toHaveBeenCalled();
        expect(amountInput().value, 'the display still reads the formatted value').toBe('0.01');
    });

    // Red today: the blur emits again {amount: '12.5'}, the value the parent already holds — a second emission.
    it('B-47: typed, echoed back by the parent, then blurred: the blur emits nothing more', async () => {
        const {emissions, loopBack} = mountWithParentLoop({amount: '12', code: 'EUR'});

        await fireEvent.input(amountInput(), {target: {value: '12,5'}});
        expect(emissions, 'premise: typing emits the normalized amount, once').toEqual([{amount: '12.5', code: 'EUR'}]);
        await loopBack();

        await fireEvent.blur(amountInput());

        expect(emissions, 'B-47: the blur emitted again the value the parent already holds').toEqual([{amount: '12.5', code: 'EUR'}]);
    });

    // Red today: the sync sees two equal doubles (both 1234567890123456.75) and keeps the old text.
    it('B-47: a new parent value that differs only past the precision of a double is shown', async () => {
        const props = {defaultCode: 'EUR', testid: 'cc', onChange: vi.fn()};
        const {rerender} = render(CompactCashCell, {...props, value: {amount: '1234567890123456.7', code: 'EUR'}});
        expect(amountInput().value, 'premise: the first value is shown').toBe('1234567890123456.7');
        expect(Number('1234567890123456.8'), 'premise: the two amounts are one double').toBe(Number('1234567890123456.7'));

        await rerender({...props, value: {amount: '1234567890123456.8', code: 'EUR'}});

        expect(amountInput().value, 'B-47: the cell kept the old amount: it compared the two as doubles').toBe('1234567890123456.8');
    });
});

/**
 * B-48 — at most fifteen significant digits in the cash (D-K3-6). The backend keeps at most 15 significant digits, leading
 * and trailing zeros not counted (`precision._digit_counts`, refusal `significantDigitsExceeded`). The cell has no cap at
 * all. The contract: an additive prop `maxSignificantDigits` (no cap by default); over it, the amount input is
 * `aria-invalid="true"`. What the form does with it is TransactionFormModal.test.ts («at most fifteen significant digits»).
 */
describe('CompactCashCell — at most maxSignificantDigits significant digits (B-48)', () => {
    beforeEach(async () => {
        await setupI18n();
    });

    /** Type `amount` behind the parent loop, with `extra` props; the amount is kept as typed. */
    async function typeAmount(amount: string, extra: Record<string, unknown>): Promise<HTMLInputElement> {
        const {loopBack} = mountWithParentLoop({amount: '1', code: 'EUR'}, extra);
        await fireEvent.input(amountInput(), {target: {value: amount}});
        await loopBack();
        expect(amountInput().value, 'premise: the amount is kept as typed').toBe(amount);
        return amountInput();
    }

    // Red today: no cap exists, so the input carries no aria-invalid at all.
    it('B-48: with maxSignificantDigits=15, 1234567890123.456 (16 significant digits) is flagged aria-invalid', async () => {
        const input = await typeAmount('1234567890123.456', {maxSignificantDigits: 15});

        expect(input, 'B-48: sixteen significant digits are past the cap of fifteen').toHaveAttribute('aria-invalid', 'true');
    });

    // Guard, green today: fifteen are within the cap.
    it('B-48 guard: with maxSignificantDigits=15, 123456789012.345 (15 significant digits) is not flagged', async () => {
        const input = await typeAmount('123456789012.345', {maxSignificantDigits: 15});

        expect(input, 'fifteen significant digits are within the cap').not.toHaveAttribute('aria-invalid', 'true');
    });

    // Guard, green today: the cap is opt-in — no prop, no cap.
    it('B-48 guard: without maxSignificantDigits, 1234567890123.456 is not flagged', async () => {
        const input = await typeAmount('1234567890123.456', {});

        expect(input, 'no cap without the prop').not.toHaveAttribute('aria-invalid', 'true');
    });
});
