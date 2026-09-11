// @vitest-environment jsdom
import {describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen} from '$test/component';
import ExactDecimalInput from './ExactDecimalInput.svelte';

const TID = 'exact-decimal';

function setup(overrides: Record<string, unknown> = {}) {
    const onchange = vi.fn();
    const utils = render(ExactDecimalInput, {
        value: '',
        step: '0.000000000001',
        maxIntegerDigits: 12,
        maxFractionDigits: 12,
        testid: TID,
        onchange,
        ...overrides,
    });
    return {input: screen.getByTestId(TID) as HTMLInputElement, onchange, ...utils};
}

describe('ExactDecimalInput', () => {
    it('keeps the raw string while editing and normalizes locale punctuation only on blur', async () => {
        const {input, onchange} = setup();

        await fireEvent.input(input, {target: {value: '1.234,500000000001'}});

        expect(input).toHaveValue('1.234,500000000001');
        expect(onchange).toHaveBeenLastCalledWith('1.234,500000000001');

        await fireEvent.blur(input);

        expect(input).toHaveValue('1234.500000000001');
        expect(onchange).toHaveBeenLastCalledWith('1234.500000000001');
    });

    it('accepts the full 12+12 digit budget and rejects either side exceeding it', async () => {
        const {input} = setup();

        await fireEvent.input(input, {target: {value: '999999999999.999999999999'}});
        expect(input).toHaveAttribute('aria-invalid', 'false');

        await fireEvent.input(input, {target: {value: '1000000000000.1'}});
        expect(input).toHaveAttribute('aria-invalid', 'true');

        await fireEvent.input(input, {target: {value: '1.1234567890123'}});
        expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('steps twelve-place values exactly without IEEE-754 drift', async () => {
        const {input, onchange} = setup({value: '0.300000000001'});

        await fireEvent.keyDown(input, {key: 'ArrowDown'});

        expect(input).toHaveValue('0.300000000000');
        expect(onchange).toHaveBeenLastCalledWith('0.300000000000');
    });

    it('clamps ArrowDown at zero unless negative values are explicitly allowed', async () => {
        const nonnegative = setup({value: '0', step: '0.1'});
        await fireEvent.keyDown(nonnegative.input, {key: 'ArrowDown'});
        expect(nonnegative.input).toHaveValue('0');
        expect(nonnegative.onchange).toHaveBeenLastCalledWith('0');

        nonnegative.unmount();
        const signed = setup({value: '0', step: '0.1', allowNegative: true});
        await fireEvent.keyDown(signed.input, {key: 'ArrowDown'});
        expect(signed.input).toHaveValue('-0.1');
        expect(signed.onchange).toHaveBeenLastCalledWith('-0.1');
    });

    it.each(['Infinity', 'NaN', 'not-a-number'])('keeps invalid text %s visible and marked invalid on blur', async (raw) => {
        const {input, onchange} = setup();

        await fireEvent.input(input, {target: {value: raw}});
        expect(input).toHaveValue(raw);
        expect(input).toHaveAttribute('aria-invalid', 'true');
        const callsBeforeBlur = onchange.mock.calls.length;

        await fireEvent.blur(input);

        expect(input).toHaveValue(raw);
        expect(onchange).toHaveBeenCalledTimes(callsBeforeBlur);
    });

    it('publishes the configured digit budget through maxlength', () => {
        const {input} = setup();
        expect(input).toHaveAttribute('maxlength', '27');
    });
});

/**
 * Enter is a submit key. Whatever the field holds at that instant is what a
 * containing form sends, so the canonicalization cannot be deferred to a blur
 * that may never happen: pressing Enter in a one-field form submits it without
 * ever moving focus, and `1.234,50` left as typed is either rejected by the
 * backend or — far worse — read as `1.234`.
 *
 * The canonical string is also compared against its own float round trip. That
 * assertion is the whole point of this component: `Number()` is never involved,
 * so 23 significant digits survive, while the arithmetic route would quietly
 * return a different number and still look like a plausible one.
 */
describe('ExactDecimalInput — Enter, and the form around it', () => {
    function setupInForm(overrides: Record<string, unknown> = {}) {
        const form = document.createElement('form');
        document.body.appendChild(form);
        const submits: string[] = [];
        const onchange = vi.fn();
        // `target` is a Svelte mount option: the form becomes the testing
        // library's container and is removed again on cleanup.
        render(ExactDecimalInput, {
            target: form,
            props: {value: '', step: '0.01', maxIntegerDigits: 12, maxFractionDigits: 12, testid: TID, onchange, ...overrides},
        });
        const input = screen.getByTestId(TID) as HTMLInputElement;
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            submits.push(input.value);
        });
        return {form, input, onchange, submits};
    }

    /**
     * Enter, dispatched raw and nothing else. No `flushSync`, no `await`, no
     * microtask: a test that flushes the scheduler here would be *creating* the
     * synchronicity it claims to observe, and would stay green against a
     * component that only canonicalizes on the task after the key.
     *
     * A browser gives the handler exactly one moment. Implicit form submission is
     * the default action of this keydown, so whatever the input holds when the
     * handler returns is what the form sends — nothing the component schedules
     * for later can reach the submission. The dispatch is cancelable and bubbling
     * for the same reason: that is the event a real Enter delivers, and it is the
     * one a handler would have to `preventDefault()` to stop the submit.
     */
    function pressEnter(input: HTMLInputElement): void {
        input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true}));
    }

    it.each([
        ['1.234,50', '1234.5'],
        ['99.999.999.999,123456789012', '99999999999.123456789012'],
    ])('turns %s into the canonical %s the moment Enter is pressed, and submits exactly that', async (typed, canonical) => {
        const {form, input, onchange, submits} = setupInForm();

        await fireEvent.input(input, {target: {value: typed}});
        expect(onchange).toHaveBeenLastCalledWith(typed);
        const callsBeforeEnter = onchange.mock.calls.length;

        // The keydown and its default action, back to back, with nothing in
        // between: no `await`, no `flushSync`, not even a microtask. This is the
        // browser's own ordering — implicit form submission *is* the default
        // action of this key — so `input.value` is read by the submit handler in
        // the same task the handler returned from. Anything the component defers
        // has not happened yet, and cannot reach the payload.
        pressEnter(input);
        form.requestSubmit();

        expect(onchange.mock.calls).toHaveLength(callsBeforeEnter + 1);

        // One assertion over three plain strings, because the interesting failure
        // is the *disagreement* between them, not any one of them alone. A diff
        // showing `callback: '1234.5'` beside `dom: '1.234,50'` and
        // `submitted: '1.234,50'` says precisely what is wrong: the component
        // computed the canonical value and told its parent, while the field the
        // user sees and the payload the form sends both still carry the raw text.
        // Split into three assertions the first red would hide the other two.
        expect({
            callback: onchange.mock.calls.at(-1)?.[0],
            dom: input.value,
            submitted: submits.at(-1),
        }).toEqual({callback: canonical, dom: canonical, submitted: canonical});
    });

    it('keeps every digit that IEEE-754 would have dropped', async () => {
        const {input, onchange} = setupInForm();

        await fireEvent.input(input, {target: {value: '99.999.999.999,123456789012'}});
        pressEnter(input);

        const canonical = onchange.mock.calls.at(-1)?.[0];
        expect(canonical).toBe('99999999999.123456789012');
        expect(String(Number(canonical))).not.toBe(canonical);
    });

    it.each(['Infinity', 'not-a-number', '1000000000000.1'])('leaves %s invalid on Enter instead of coercing it to a number', async (raw) => {
        const {input, onchange} = setupInForm();

        await fireEvent.input(input, {target: {value: raw}});
        const callsBeforeEnter = onchange.mock.calls.length;

        pressEnter(input);

        // Enter commits nothing: no callback, no rewritten text, and the refusal
        // stays published instead of a plausible-looking number appearing.
        expect(onchange.mock.calls).toHaveLength(callsBeforeEnter);
        expect(input).toHaveValue(raw);
        expect(input).toHaveAttribute('aria-invalid', 'true');
    });
});
