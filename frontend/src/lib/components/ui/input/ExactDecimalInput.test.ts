// @vitest-environment jsdom
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import ExactDecimalInput from './ExactDecimalInput.svelte';

const TID = 'exact-decimal';

// A fraction past the budget renders a translated message under the field (C-97b), and tests in every
// describe below type one: svelte-i18n is booted once, for the whole file.
beforeAll(async () => {
    await setupI18n();
});

function setup(overrides: Record<string, unknown> = {}) {
    const onchange = vi.fn();
    const oncommit = vi.fn();
    const onvaliditychange = vi.fn();
    const onfocus = vi.fn();
    const onblur = vi.fn();
    const utils = render(ExactDecimalInput, {
        value: '',
        step: '0.000000000001',
        maxIntegerDigits: 12,
        maxFractionDigits: 12,
        testid: TID,
        onchange,
        oncommit,
        onvaliditychange,
        onfocus,
        onblur,
        ...overrides,
    });
    return {
        input: screen.getByTestId(String(overrides.testid ?? TID)) as HTMLInputElement,
        onchange,
        oncommit,
        onvaliditychange,
        onfocus,
        onblur,
        ...utils,
    };
}

async function arrow(input: HTMLInputElement, key: 'ArrowUp' | 'ArrowDown', repeat = false, modifiers: Partial<KeyboardEventInit> = {}): Promise<KeyboardEvent> {
    const event = new KeyboardEvent('keydown', {key, repeat, bubbles: true, cancelable: true, ...modifiers});
    await fireEvent(input, event);
    return event;
}

/**
 * C-97b — the message that says why a value over the fractional budget is refused. Its id is the
 * field's own followed by `-digits-error`; its text is the cure's choice and is never read here.
 */
function digitsError(testid: string): HTMLElement | null {
    return screen.queryByTestId(`${testid}-digits-error`);
}

/** Over the budget: the field is flagged, and under it a visible message carries the budget it broke. */
function expectDigitsError(input: HTMLInputElement, testid: string, max: number): void {
    expect(input, `${JSON.stringify(input.value)} is over a budget of ${max} decimals`).toHaveAttribute('aria-invalid', 'true');
    const message = digitsError(testid);
    expect(message, `${testid}-digits-error must say why ${JSON.stringify(input.value)} is refused; no such element is rendered`).not.toBeNull();
    if (!message) return;
    expect(message).toBeVisible();
    expect(message, 'the message carries the budget it enforces').toHaveAttribute('data-max', String(max));
    expect(input.compareDocumentPosition(message) & Node.DOCUMENT_POSITION_FOLLOWING, 'the message sits under the field: after it in document order').not.toBe(0);
}

/** Within the budget: nothing to explain — the message is absent, or rendered hidden. */
function expectNoDigitsError(input: HTMLInputElement, testid: string): void {
    expect(input, `${JSON.stringify(input.value)} is within the budget`).toHaveAttribute('aria-invalid', 'false');
    const message = digitsError(testid);
    if (message) expect(message, `${testid}-digits-error shows for a value within the budget`).not.toBeVisible();
}

/**
 * C-97b: no `maxlength`. A browser cuts a longer paste down to fit one, silently, so the user sees a
 * number that is not the one pasted, and no reason. Soft, so the same test still reports the message.
 */
function expectNoMaxLength(input: HTMLInputElement): void {
    expect.soft(input.getAttribute('maxlength'), 'no maxlength may cut a paste short: the budget is applied by the flag and its message').toBeNull();
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

    it('accepts the full 12+12 digit budget and leaves either overflow visible and invalid', async () => {
        const {input, onchange} = setup();

        await fireEvent.input(input, {target: {value: '999999999999.999999999999'}});
        expect(input).toHaveValue('999999999999.999999999999');
        expect(input).toHaveAttribute('aria-invalid', 'false');

        await fireEvent.input(input, {target: {value: '1000000000000.1'}});
        expect(input).toHaveValue('1000000000000.1');
        expect(onchange).toHaveBeenLastCalledWith('1000000000000.1');
        expect(input).toHaveAttribute('aria-invalid', 'true');

        await fireEvent.input(input, {target: {value: '1.1234567890123'}});
        expect(input).toHaveValue('1.1234567890123');
        expect(onchange).toHaveBeenLastCalledWith('1.1234567890123');
        expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('steps twelve-place subtraction and the 12+6 ceiling exactly', async () => {
        const subtraction = setup({value: '0.300000000001'});

        await arrow(subtraction.input, 'ArrowDown');

        expect(subtraction.input).toHaveValue('0.300000000000');
        expect(subtraction.onchange).toHaveBeenLastCalledWith('0.300000000000');

        subtraction.unmount();
        const ceiling = setup({
            value: '999999999999.123455',
            step: '0.000001',
            maxFractionDigits: 6,
            allowNegative: true,
        });

        await arrow(ceiling.input, 'ArrowUp');

        expect(ceiling.input).toHaveValue('999999999999.123456');
        expect(ceiling.onchange).toHaveBeenLastCalledWith('999999999999.123456');
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

    it('rejects letters at the input boundary without discarding decimal punctuation or digits', async () => {
        const {input, onchange} = setup();

        await fireEvent.input(input, {target: {value: 'EUR 12,34abc'}});

        expect(input).toHaveValue('12,34');
        expect(onchange).toHaveBeenLastCalledWith('12,34');
        expect(input).toHaveAttribute('aria-invalid', 'false');
    });

    it('preserves a partial comma draft and applies the sign policy while editing', async () => {
        const unsigned = setup();

        await fireEvent.input(unsigned.input, {target: {value: '-12,'}});
        expect(unsigned.input).toHaveValue('12,');
        expect(unsigned.onchange).toHaveBeenLastCalledWith('12,');

        unsigned.unmount();
        const signed = setup({allowNegative: true});
        await fireEvent.input(signed.input, {target: {value: '-12,'}});
        expect(signed.input).toHaveValue('-12,');
        expect(signed.onchange).toHaveBeenLastCalledWith('-12,');
    });

    /*
     * C-97b rewrites the two pins of the old maxlength values (28 for 12+12, 23 for a signed 12+6): the
     * budget is still applied — by the flag and by the message under the field — but no longer by a
     * `maxlength`, which makes a browser truncate a longer paste silently.
     * Red today: the field publishes maxlength 28 / 23, and no message element exists.
     */
    it('applies the configured digit budget by its flag and message, without a truncating maxlength', async () => {
        const {input} = setup();
        expectNoMaxLength(input);

        await fireEvent.input(input, {target: {value: '999999999999.999999999999'}});
        expectNoDigitsError(input, TID);

        await fireEvent.input(input, {target: {value: '1.1234567890123'}});
        expect(input).toHaveValue('1.1234567890123');
        expectDigitsError(input, TID, 12);
    });

    it('keeps a sign and grouping punctuation inside the budget, with no maxlength to cut them', async () => {
        const {input} = setup({maxFractionDigits: 6, allowNegative: true});
        expectNoMaxLength(input);

        // 23 characters: exactly what the old maxlength left for a signed, grouped 12+6.
        await fireEvent.input(input, {target: {value: '-999.999.999.999,123456'}});
        expect(input).toHaveValue('-999.999.999.999,123456');
        expectNoDigitsError(input, TID);

        await fireEvent.input(input, {target: {value: '-999999999999.1234567'}});
        expect(input).toHaveValue('-999999999999.1234567');
        expectDigitsError(input, TID, 6);
    });

    it('keeps typed out-of-range values visible, while arrows clamp exactly to min/max', async () => {
        const typed = setup({value: '10', step: '0.000001', min: '0.000001', max: '10.000001'});
        await fireEvent.input(typed.input, {target: {value: '10.000002'}});
        expect(typed.input).toHaveValue('10.000002');
        expect(typed.input).toHaveAttribute('aria-invalid', 'true');
        await fireEvent.blur(typed.input);
        expect(typed.input).toHaveValue('10.000002');

        typed.unmount();
        const upper = setup({value: '10.000000', step: '0.000002', min: '0.000001', max: '10.000001'});
        await arrow(upper.input, 'ArrowUp');
        expect(upper.input).toHaveValue('10.000001');

        upper.unmount();
        const lower = setup({value: '0.000002', step: '0.000002', min: '0.000001', max: '10.000001'});
        await arrow(lower.input, 'ArrowDown');
        expect(lower.input).toHaveValue('0.000001');
    });

    it('does not accelerate unless explicitly enabled', async () => {
        const {input} = setup({value: '0', step: '1', accelerateOnHold: false});

        await arrow(input, 'ArrowUp');
        for (let repeat = 1; repeat <= 20; repeat += 1) {
            await arrow(input, 'ArrowUp', true);
        }

        expect(input).toHaveValue('21');
    });

    it('uses the deterministic opt-in hold cadence and resets on keyup or direction change', async () => {
        const {input} = setup({value: '0', step: '1', accelerateOnHold: true});
        const sequence: string[] = [];

        await arrow(input, 'ArrowUp');
        sequence.push(input.value);
        for (let repeat = 1; repeat <= 20; repeat += 1) {
            await arrow(input, 'ArrowUp', true);
            sequence.push(input.value);
        }

        expect(sequence[0]).toBe('1');
        expect(sequence[14]).toBe('15');
        expect(sequence.slice(15, 20)).toEqual(['16', '17', '18', '19', '20']);
        expect(sequence[20]).toBe('30');

        await arrow(input, 'ArrowDown', true);
        expect(input).toHaveValue('29');

        await fireEvent.keyUp(input, {key: 'ArrowDown'});
        await arrow(input, 'ArrowDown', true);
        expect(input).toHaveValue('28');
    });

    it('starts a fresh base-step run when focus moves to another target', async () => {
        const first = setup({testid: 'exact-decimal-first', value: '0', step: '1', accelerateOnHold: true});
        const second = setup({testid: 'exact-decimal-second', value: '0', step: '1', accelerateOnHold: true});

        await arrow(first.input, 'ArrowUp');
        for (let repeat = 1; repeat <= 20; repeat += 1) await arrow(first.input, 'ArrowUp', true);
        expect(first.input).toHaveValue('30');

        await arrow(second.input, 'ArrowUp', true);
        expect(second.input).toHaveValue('1');
    });

    it('accelerates fractional high-magnitude values without float residue', async () => {
        const {input} = setup({
            value: '999999999990.123450',
            step: '0.000001',
            maxFractionDigits: 6,
            accelerateOnHold: true,
        });

        await arrow(input, 'ArrowUp');
        for (let repeat = 1; repeat <= 20; repeat += 1) await arrow(input, 'ArrowUp', true);

        expect(input).toHaveValue('999999999990.123480');
    });

    it.each([
        ['ctrlKey', {ctrlKey: true}],
        ['metaKey', {metaKey: true}],
        ['altKey', {altKey: true}],
    ] as const)('leaves modified arrows untouched (%s)', async (_name, modifiers) => {
        const {input, onchange} = setup({value: '7', step: '1', accelerateOnHold: true});

        const event = await arrow(input, 'ArrowUp', false, modifiers);

        expect(event.defaultPrevented).toBe(false);
        expect(input).toHaveValue('7');
        expect(onchange).not.toHaveBeenCalled();
    });

    it.each([
        ['readonly', {readonly: true}],
        ['disabled', {disabled: true}],
    ] as const)('%s fields neither mutate nor emit', async (_name, state) => {
        const {input, onchange, oncommit} = setup({value: '1.25', ...state});

        await arrow(input, 'ArrowUp');
        await fireEvent.keyDown(input, {key: 'Enter'});
        await fireEvent.blur(input);

        expect(input).toHaveValue('1.25');
        expect(onchange).not.toHaveBeenCalled();
        expect(oncommit).not.toHaveBeenCalled();
    });

    it('forwards form, accessibility, style, class, and focus/blur contracts', async () => {
        const {input, onfocus, onblur} = setup({
            value: '1.25',
            id: 'exact-id',
            name: 'exact-name',
            required: true,
            placeholder: 'placeholder-token',
            ariaLabel: 'decimal-label-token',
            ariaDescribedby: 'decimal-hint-token',
            ariaErrormessage: 'decimal-error-token',
            className: 'forwarded-class-token',
            style: 'padding-left: 7px',
        });

        expect(input).toHaveAttribute('id', 'exact-id');
        expect(input).toHaveAttribute('name', 'exact-name');
        expect(input).toBeRequired();
        expect(input).toHaveAttribute('placeholder', 'placeholder-token');
        expect(input).toHaveAttribute('aria-label', 'decimal-label-token');
        expect(input).toHaveAttribute('aria-describedby', 'decimal-hint-token');
        expect(input).toHaveAttribute('aria-errormessage', 'decimal-error-token');
        expect(input.classList.contains('forwarded-class-token')).toBe(true);
        expect(input.style.paddingLeft).toBe('7px');
        expect(input).toHaveAttribute('type', 'text');
        expect(input).toHaveAttribute('inputmode', 'decimal');
        expect(input).not.toHaveAttribute('aria-valuenow');

        await fireEvent.focus(input);
        await fireEvent.blur(input);
        expect(onfocus).toHaveBeenCalledTimes(1);
        expect(onblur).toHaveBeenCalledTimes(1);
    });

    it('publishes every required-empty validity field exactly', async () => {
        const {input, onvaliditychange} = setup({required: true});

        await waitFor(() => {
            expect(onvaliditychange).toHaveBeenLastCalledWith({
                normalized: '',
                empty: true,
                syntaxValid: true,
                requiredValid: false,
                digitsValid: true,
                rangeValid: true,
                valid: false,
            });
        });
        expect(input.validity.valueMissing).toBe(true);
        expect(input.checkValidity()).toBe(false);
        expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('externalInvalid changes only final validity', async () => {
        const {input, onvaliditychange, rerender} = setup({value: '1.25'});
        await waitFor(() => expect(onvaliditychange).toHaveBeenCalled());
        const base = onvaliditychange.mock.calls.at(-1)?.[0];
        expect(base).toEqual({
            normalized: '1.25',
            empty: false,
            syntaxValid: true,
            requiredValid: true,
            digitsValid: true,
            rangeValid: true,
            valid: true,
        });

        await rerender({
            value: '1.25',
            step: '0.000000000001',
            maxIntegerDigits: 12,
            maxFractionDigits: 12,
            testid: TID,
            onchange: vi.fn(),
            oncommit: vi.fn(),
            onvaliditychange,
            externalInvalid: true,
        });

        await waitFor(() => expect(onvaliditychange.mock.calls.at(-1)?.[0]).toEqual({...base, valid: false}));
        expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('commits on blur and Enter even when canonical, without emitting a change', async () => {
        const {input, onchange, oncommit} = setup({value: '1.25'});

        await fireEvent.blur(input);
        await fireEvent.keyDown(input, {key: 'Enter'});

        expect(oncommit.mock.calls).toEqual([['1.25'], ['1.25']]);
        expect(onchange).not.toHaveBeenCalled();
    });
});

/**
 * Enter is a submit key. Whatever the field holds at that instant is what a
 * containing form sends, so the canonicalization cannot be deferred to a blur
 * that may never happen: pressing Enter in a one-field form submits it without
 * ever moving focus, and `1.234,50` left as typed is either rejected by the
 * backend or — far worse — read as `1.234`.
 *
 * The canonical string is asserted byte-for-byte. That is the whole point of
 * this component: no floating-point round trip may reinterpret its 23 digits.
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
        expect(canonical).not.toBe('99999999999.12346');
    });

    it('leaves an over-budget decimal invalid on Enter instead of coercing it', async () => {
        const {input, onchange} = setupInForm();
        const raw = '1000000000000.1';

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

/**
 * C-97b — «the decimal places in input». Over the fractional budget the value is flagged
 * (`digitsValid` false, `aria-invalid`), and today nothing tells the user why: a red border on a
 * number that looks fine. The contract: a message under the field, `<testid>-digits-error`,
 * carrying the budget in `data-max`; a value within the budget shows none; and a value longer than
 * the old `maxlength` budget is kept whole — no `maxlength` lets the browser cut a paste down to
 * something that looks valid.
 *
 * The message's text is the cure's choice (these inputs are generic UI, also used by the PAC
 * planner), so it is never read: only its id, its `data-max`, its visibility and its place.
 */
describe('ExactDecimalInput — the digit budget says why it refuses (C-97b)', () => {
    // Red today: no message element exists.
    it.each([
        [6, '0.1234567'],
        [10, '0.12345678912'],
        [12, '1.1234567890123'],
    ])('a fraction longer than maxFractionDigits=%i (%j) is flagged and explained, with data-max', async (max, typed) => {
        const {input, onchange} = setup({maxFractionDigits: max});

        await fireEvent.input(input, {target: {value: typed}});

        expect(input, 'the value stays as typed').toHaveValue(typed);
        expect(onchange).toHaveBeenLastCalledWith(typed);
        expectDigitsError(input, TID, max);
    });

    // Red today: the message never appears, so it cannot be withdrawn either.
    it('withdraws the message as soon as the value is back within the budget', async () => {
        const {input} = setup({maxFractionDigits: 6});

        await fireEvent.input(input, {target: {value: '0.1234567'}});
        expectDigitsError(input, TID, 6);

        await fireEvent.input(input, {target: {value: '0.123456'}});
        expectNoDigitsError(input, TID);
    });

    // Guard: green today (no message exists at all); after the cure a valid value must not grow one.
    it.each([
        [6, '0.123456'],
        [10, '0.1234567891'],
        [12, '999999999999.999999999999'],
    ])('a value within maxFractionDigits=%i (%j) is valid and shows no message', async (max, typed) => {
        const {input} = setup({maxFractionDigits: max});

        await fireEvent.input(input, {target: {value: typed}});

        expect(input).toHaveValue(typed);
        expectNoDigitsError(input, TID);
    });

    // Red today: the field publishes maxlength="22" for 12+6, and no message exists. jsdom does not
    // apply maxlength to a value set by script, so the attribute is the honest handle on the browser's
    // cut; the value assertions pin that the component itself cuts nothing either, typed or blurred.
    it('keeps a paste longer than the old maxlength budget whole, flagged and explained', async () => {
        const {input, oncommit} = setup({maxFractionDigits: 6});
        const pasted = `0.${'1234567890'.repeat(3)}`;
        expect(pasted.length, 'premise: longer than the 22 characters the old maxlength left a 12+6 field').toBeGreaterThan(22);
        expectNoMaxLength(input);

        await fireEvent.input(input, {target: {value: pasted}});
        expect(input).toHaveValue(pasted);
        expectDigitsError(input, TID, 6);

        await fireEvent.blur(input);
        expect(input, 'a refused value is not coerced on blur').toHaveValue(pasted);
        expect(oncommit).not.toHaveBeenCalled();
        expectDigitsError(input, TID, 6);
    });
});
