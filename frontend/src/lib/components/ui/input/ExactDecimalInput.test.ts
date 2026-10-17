// @vitest-environment jsdom
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
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

/** A value as a failure message can show it: whole when short, its two ends and its length when it is a huge paste. */
function shown(value: string): string {
    return value.length <= 64 ? JSON.stringify(value) : `${JSON.stringify(value.slice(0, 24))}…${JSON.stringify(value.slice(-16))} (${value.length} chars)`;
}

/** Over the budget: the field is flagged, and under it a visible message carries the budget it broke. */
function expectDigitsError(input: HTMLInputElement, testid: string, max: number): void {
    expect(input, `${shown(input.value)} is over a budget of ${max} decimals`).toHaveAttribute('aria-invalid', 'true');
    const message = digitsError(testid);
    expect(message, `${testid}-digits-error must say why ${shown(input.value)} is refused; no such element is rendered`).not.toBeNull();
    if (!message) return;
    expect(message).toBeVisible();
    expect(message, 'the message carries the budget it enforces').toHaveAttribute('data-max', String(max));
    expect(input.compareDocumentPosition(message) & Node.DOCUMENT_POSITION_FOLLOWING, 'the message sits under the field: after it in document order').not.toBe(0);
}

/** Within the budget: nothing to explain — the message is absent, or rendered hidden. */
function expectNoDigitsError(input: HTMLInputElement, testid: string): void {
    expect(input, `${shown(input.value)} is within the budget`).toHaveAttribute('aria-invalid', 'false');
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
     * Red before C-97b: the field published maxlength 28 / 23, and no message element existed.
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
 * (`digitsValid` false, `aria-invalid`), and before C-97b nothing told the user why: a red border on a
 * number that looked fine. The contract: a message under the field, `<testid>-digits-error`,
 * carrying the budget in `data-max`; a value within the budget shows none; and a value longer than
 * the old `maxlength` budget is kept whole — no `maxlength` lets the browser cut a paste down to
 * something that looks valid.
 *
 * The message's text is the cure's choice (these inputs are generic UI, also used by the PAC
 * planner), so it is never read: only its id, its `data-max`, its visibility and its place.
 */
describe('ExactDecimalInput — the digit budget says why it refuses (C-97b)', () => {
    // Red before C-97b: no message element existed.
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

    // Red before C-97b: the message never appeared, so it could not be withdrawn either.
    it('withdraws the message as soon as the value is back within the budget', async () => {
        const {input} = setup({maxFractionDigits: 6});

        await fireEvent.input(input, {target: {value: '0.1234567'}});
        expectDigitsError(input, TID, 6);

        await fireEvent.input(input, {target: {value: '0.123456'}});
        expectNoDigitsError(input, TID);
    });

    // Guard: a value within the budget is valid and grows no message (before C-97b there was none at all).
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

    // Red before C-97b: the field published maxlength="22" for 12+6, and no message existed. jsdom does not
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

/*
 * W-B66 — a pasted exponent, and a huge paste (D-W66-1, 17/10).
 *
 * (a) Typed key by key, an `e` never enters the field; pasted, `1e-8` arrives whole, and until W-B66
 * `handleInput` filtered it to `18` — another number, valid, silently. The contract: a text WHOLLY in
 * scientific notation is expanded exactly to a plain decimal when |exponent| ≤ 100 (the backend's bound).
 * Any other text holding an exponent marker (a digit, an optional `.` or `,`, `e` or `E`, an optional sign,
 * a digit) is kept as typed (trimmed), its sign included even without allowNegative: the field is invalid,
 * and a `<p>` under it says why: `<testid>-exponent-error`, rendering `common.decimalExponentOutOfRange`
 * with `max` 100. That covers beyond ±100 (`1e-200`) and not wholly scientific (`1e5x`). A text holding no
 * marker reads as before: a typed `e` is dropped. Each input event re-reads the whole text, and an arrow
 * key steps no kept text. A parent may hand the field an exponent too (a satoshi formatted through Number
 * is `1e-8`): within ±100 it is valid.
 *
 * (b) A paste already over the digit budget is invalid without asking min/max, so `normalizedParts` must
 * not reach `compareExact` (a BigInt of every pasted digit, scaled by 10^places): `rangeValid` then reads
 * true. And an arrow key leaves an over-budget value as it is.
 */
const EXPONENT_MAX = 100;
const EXPONENT_KEY = 'common.decimalExponentOutOfRange';
const HUGE = 40_000;
const BOUND_MS = 1_000;

type Recorded = {mock: {calls: unknown[][]}};

function exponentError(testid: string): HTMLElement | null {
    return screen.queryByTestId(`${testid}-exponent-error`);
}

/** What the field shows, emits and says, in one object: a red shows every disagreement at once. */
function fieldState(input: HTMLInputElement, onchange: Recorded) {
    return {
        dom: input.value,
        emitted: onchange.mock.calls.at(-1)?.[0],
        ariaInvalid: input.getAttribute('aria-invalid'),
        exponentError: exponentError(TID) !== null,
    };
}

function lastValidity(onvaliditychange: Recorded): Record<string, unknown> | undefined {
    return onvaliditychange.mock.calls.at(-1)?.[0] as Record<string, unknown> | undefined;
}

/**
 * A kept text: the field is flagged, and under it a visible paragraph says why. Its text is compared with
 * what the contract's key renders in the test's own catalogue, never with a literal: what is pinned is the
 * key and its `max`, in any language.
 */
function expectExponentError(input: HTMLInputElement, testid: string): void {
    expect(input, `${shown(input.value)} holds an exponent marker and is kept as typed, so the field is invalid`).toHaveAttribute('aria-invalid', 'true');
    const message = exponentError(testid);
    expect(message, `${testid}-exponent-error must say why ${shown(input.value)} is refused; no such element is rendered`).not.toBeNull();
    if (!message) return;
    expect(message.tagName, 'a paragraph, as the digits message is').toBe('P');
    expect(message).toBeVisible();
    expect(input.compareDocumentPosition(message) & Node.DOCUMENT_POSITION_FOLLOWING, 'the message sits under the field: after it in document order').not.toBe(0);
    const rendered = get(_)(EXPONENT_KEY, {values: {max: EXPONENT_MAX}});
    expect(message.textContent?.trim(), `the message renders ${EXPONENT_KEY} with max ${EXPONENT_MAX}`).toBe(rendered);
    expect.soft(rendered, `${EXPONENT_KEY} must be in the catalogue, or the field shows its bare key`).not.toBe(EXPONENT_KEY);
}

describe('ExactDecimalInput — a pasted exponent is read exactly, or kept (W-B66, D-W66-1 (a))', () => {
    // Red before the W-B66 cure: the e and the minus are filtered out, and 1e-8 reads 18.
    it('expands a pasted 1e-8 to 0.00000001: the value, the DOM text, a valid field', async () => {
        const {input, onchange, onvaliditychange} = setup();

        await fireEvent.input(input, {target: {value: '1e-8'}});

        expect({...fieldState(input, onchange), normalized: lastValidity(onvaliditychange)?.normalized}, 'today the e and the minus are filtered out: 1e-8 reads 18').toEqual({
            dom: '0.00000001',
            emitted: '0.00000001',
            ariaInvalid: 'false',
            exponentError: false,
            normalized: '0.00000001',
        });
    });

    // Red before the W-B66 cure: each paste reads as a valid number (1200, 15, 1200), and no exponent-error exists.
    it.each([
        ['1e-200', 'beyond ±100', '1200'],
        ['1e5x', 'not wholly scientific', '15'],
        ['-1e-200', 'its sign kept without allowNegative: kept beats the sign rule', '1200'],
    ])('keeps a pasted %s as typed — %s: invalid, with the exponent message under the field', async (pasted, _reason, today) => {
        const {input, onchange} = setup();

        await fireEvent.input(input, {target: {value: pasted}});

        expect(fieldState(input, onchange), `today ${pasted} reads ${today}, valid, with nothing to explain`).toEqual({dom: pasted, emitted: pasted, ariaInvalid: 'true', exponentError: true});
        expectExponentError(input, TID);
        expect(digitsError(TID), 'no digit budget is at stake: only the exponent message shows').toBeNull();
    });

    // Red before the W-B66 cure: the first paste already reads 1200.
    it('re-reads the whole text on each edit: kept while it holds a marker, expanded once wholly scientific within ±100', async () => {
        const {input, onchange} = setup();

        await fireEvent.input(input, {target: {value: '1e-200'}});
        expect(fieldState(input, onchange), 'pasted beyond ±100: kept, invalid, explained').toEqual({dom: '1e-200', emitted: '1e-200', ariaInvalid: 'true', exponentError: true});

        await fireEvent.input(input, {target: {value: '1e-200x'}});
        expect(fieldState(input, onchange), 'a stray character after it: still holding a marker, kept — never 1200').toEqual({dom: '1e-200x', emitted: '1e-200x', ariaInvalid: 'true', exponentError: true});

        await fireEvent.input(input, {target: {value: '1e-2000'}});
        expect(fieldState(input, onchange), 'wholly scientific again, still beyond: kept').toEqual({dom: '1e-2000', emitted: '1e-2000', ariaInvalid: 'true', exponentError: true});

        await fireEvent.input(input, {target: {value: '1e-2'}});
        expect(fieldState(input, onchange), 'within ±100: expanded, valid, the message withdrawn').toEqual({dom: '0.01', emitted: '0.01', ariaInvalid: 'false', exponentError: false});
    });

    // Guard: a lone e holds no exponent marker, so a typed one is still dropped — key by key, an exponent never forms.
    it('still drops a typed e: 12e reads 12, valid, with no exponent message', async () => {
        const {input, onchange} = setup();

        await fireEvent.input(input, {target: {value: '12e'}});

        expect(fieldState(input, onchange)).toEqual({dom: '12', emitted: '12', ariaInvalid: 'false', exponentError: false});
    });

    // Red before the W-B66 cure: 1e-20 reads 120, a valid integer.
    it('expands an in-range 1e-20 whole, and the digit budget flags its 20 decimals, not the exponent message', async () => {
        const {input, onchange} = setup({maxFractionDigits: 12});
        const expanded = `0.${'0'.repeat(19)}1`;

        await fireEvent.input(input, {target: {value: '1e-20'}});

        expect(fieldState(input, onchange), 'today 1e-20 reads 120').toEqual({dom: expanded, emitted: expanded, ariaInvalid: 'true', exponentError: false});
        expectDigitsError(input, TID, 12);
    });

    // Red before the W-B66 cure: normalizedParts refuses any letter before reading the number, so the field is invalid and a blur keeps 1e-8.
    it('accepts an in-range 1e-8 from its value prop: valid, and a blur commits 0.00000001', async () => {
        const {input, oncommit, onvaliditychange} = setup({value: '1e-8'});
        await waitFor(() => expect(onvaliditychange).toHaveBeenCalled());

        const validity = lastValidity(onvaliditychange);
        expect({flaggedInvalid: input.getAttribute('aria-invalid') === 'true', normalized: validity?.normalized, valid: validity?.valid}, 'today the letter e alone makes the value invalid').toEqual({
            flaggedInvalid: false,
            normalized: '0.00000001',
            valid: true,
        });

        await fireEvent.blur(input);
        expect({dom: input.value, committed: oncommit.mock.calls.at(-1)?.[0]}, 'the blur commits the plain decimal').toEqual({dom: '0.00000001', committed: '0.00000001'});
    });

    // Guard: the letter already makes it invalid; beyond ±100 it must stay so, and a blur must not coerce it.
    it('keeps a 1e-200 value prop invalid, and a blur leaves it as given', async () => {
        const {input, oncommit, onvaliditychange} = setup({value: '1e-200'});
        await waitFor(() => expect(onvaliditychange).toHaveBeenCalled());

        expect(input).toHaveAttribute('aria-invalid', 'true');
        expect(lastValidity(onvaliditychange)?.valid).toBe(false);

        await fireEvent.blur(input);
        expect(input).toHaveValue('1e-200');
        expect(oncommit).not.toHaveBeenCalled();
    });

    // Red before the W-B66 cure: no exponent-error element exists.
    it('explains a 1e-200 value prop with the exponent message', async () => {
        const {input, onvaliditychange} = setup({value: '1e-200'});
        await waitFor(() => expect(onvaliditychange).toHaveBeenCalled());

        expectExponentError(input, TID);
    });

    // Red before the W-B66 cure: the arrow reads 1e-200 as 1200 and steps it, to 1200.000000000001.
    it('leaves a kept 1e-200 from the value prop unchanged under an arrow key', async () => {
        const {input, onchange} = setup({value: '1e-200'});

        await arrow(input, 'ArrowUp');

        expect({dom: input.value, emitted: onchange.mock.calls.length}, 'today the arrow reads 1e-200 as 1200 and steps it').toEqual({dom: '1e-200', emitted: 0});
    });

    // Red before the W-B66 cure: the paste already reads 1200, and the arrow steps it, to 1199.999999999999.
    it('leaves a pasted, kept 1e-200 unchanged under an arrow key', async () => {
        const {input, onchange} = setup();
        await fireEvent.input(input, {target: {value: '1e-200'}});
        const callsBeforeTheArrow = onchange.mock.calls.length;

        await arrow(input, 'ArrowDown');

        expect({dom: input.value, emittedByTheArrow: onchange.mock.calls.length - callsBeforeTheArrow}, 'today the paste reads 1200 and the arrow steps it').toEqual({dom: '1e-200', emittedByTheArrow: 0});
    });
});

describe('ExactDecimalInput — a value over the digit budget costs no range check and no step (W-B66, D-W66-1 (b))', () => {
    // Red before the W-B66 cure: compareExact runs on the over-budget value — each bound turns its 40 000 decimals into a BigInt and scales by 10^40000 — and judges the range (rangeValid false).
    it('does not range-check a paste already over the digit budget: no BigInt from its digits, rangeValid true, within 1 000 ms', async () => {
        const {input, onvaliditychange} = setup({min: '0', max: '1'});
        const pasted = `5.${'1234567890'.repeat(HUGE / 10)}`;
        const bigint = vi.spyOn(globalThis, 'BigInt');
        try {
            const started = performance.now();
            await fireEvent.input(input, {target: {value: pasted}});
            const ms = performance.now() - started;
            const sizedByThePaste = bigint.mock.calls.filter(([arg]) => (typeof arg === 'string' && arg.length >= HUGE) || (typeof arg === 'number' && arg >= HUGE)).length;

            expect(input.value === pasted, `the paste is kept whole; the field holds ${shown(input.value)}`).toBe(true);
            expectDigitsError(input, TID, 12);
            expect(ms, `the paste took ${ms.toFixed(0)} ms`).toBeLessThan(BOUND_MS);
            const validity = lastValidity(onvaliditychange);
            expect(
                {bigintsSizedByThePaste: sizedByThePaste, digitsValid: validity?.digitsValid, rangeValid: validity?.rangeValid, valid: validity?.valid},
                `compareExact ran on a value already over the digit budget (the paste took ${ms.toFixed(0)} ms): its ${HUGE} decimals became BigInts and the range was judged`,
            ).toEqual({bigintsSizedByThePaste: 0, digitsValid: false, rangeValid: true, valid: false});
        } finally {
            bigint.mockRestore();
        }
    });

    // Red before the W-B66 cure: the arrow steps any value it can read, budget or not, at the precision of its own digits.
    it.each([
        ['a fraction one digit past the budget', '1.1234567890123', 'ArrowUp'],
        ['an integer one digit past the budget', '1000000000000.5', 'ArrowDown'],
    ] as const)('leaves %s unchanged under an arrow key: %s, %s', async (_label, value, key) => {
        const {input, onchange} = setup({value});

        await arrow(input, key);

        expect({dom: input.value, emitted: onchange.mock.calls.length}, 'today the arrow steps it like a valid value').toEqual({dom: value, emitted: 0});
    });

    // Red before the W-B66 cure: the arrow steps a 40 000-decimal value at 40 000 places, through BigInt.
    it('leaves a 40 000-decimal value unchanged under an arrow key, within 1 000 ms', async () => {
        const value = `5.${'1234567890'.repeat(HUGE / 10)}`;
        const {input, onchange} = setup({value});

        const started = performance.now();
        await arrow(input, 'ArrowUp');
        const ms = performance.now() - started;

        expect({unchanged: input.value === value, emitted: onchange.mock.calls.length}, `today the arrow stepped it at ${HUGE} places (${ms.toFixed(0)} ms), to ${shown(input.value)}`).toEqual({unchanged: true, emitted: 0});
        expect(ms, `the arrow took ${ms.toFixed(0)} ms`).toBeLessThan(BOUND_MS);
    });

    // Guard: a value exactly at the budget is valid, and steps as before.
    it.each([
        ['twelve decimals', '1.123456789012', '0.000000000001', '1.123456789013'],
        ['twelve integer digits', '999999999998', '1', '999999999999'],
    ])('still steps a value exactly at the budget: %s', async (_label, value, step, stepped) => {
        const {input, onchange} = setup({value, step});

        await arrow(input, 'ArrowUp');

        expect(input).toHaveValue(stepped);
        expect(onchange).toHaveBeenLastCalledWith(stepped);
    });

    // Guard: within the budget, min and max are still checked.
    it.each([
        ['above max', '10.5', false],
        ['below min', '0.5', false],
        ['within', '5', true],
    ] as const)('still range-checks a value within the budget: %s (%s)', async (_label, typed, inRange) => {
        const {input, onvaliditychange} = setup({min: '1', max: '10'});

        await fireEvent.input(input, {target: {value: typed}});

        const validity = lastValidity(onvaliditychange);
        expect({ariaInvalid: input.getAttribute('aria-invalid'), digitsValid: validity?.digitsValid, rangeValid: validity?.rangeValid, valid: validity?.valid}).toEqual({
            ariaInvalid: String(!inRange),
            digitsValid: true,
            rangeValid: inRange,
            valid: inRange,
        });
    });
});

/*
 * W-B64 — the digit budget counts no zero the backend drops.
 *
 * The backend (`precision._digit_counts`) counts no leading zero of the integer part and no trailing zero of the
 * fraction. The field counted characters (`normalizedParts`, `fractionOverflow`), and refused values the backend keeps:
 * `0.10000000000`, one decimal, at 10 decimals; `5.0`, a whole number, at `maxFractionDigits={0}` (the PAC planner's
 * priorities: «whole numbers only»); `0000000000001.5`, one integer digit, at 12.
 *
 * The contract (`decimalDigitCounts`, parseDecimalInput.ts):
 * - `digitsValid` and the digits message count the digits the backend counts. The value is kept as typed while it is
 *   edited, and a blur commits it as before (`formatDecimalForDisplay`): `0.1`, `5`.
 * - A value whose TEXT is past the budget but which is within it once those zeros are dropped is range-checked and
 *   stepped from the stripped value: never through a BigInt sized by its text (W-B66). A value within the text budget
 *   still steps from its text, its typed places kept.
 * - The validity `onvaliditychange` publishes keeps its seven fields.
 *
 * A digit that is not a zero still counts: `1.10000000001` has eleven decimals.
 */
const VALIDITY_FIELDS = ['normalized', 'empty', 'syntaxValid', 'requiredValid', 'digitsValid', 'rangeValid', 'valid'];

/** The calls a BigInt spy saw that are sized by a text of HUGE characters: the text itself, or a power as large. */
function bigintsSizedByTheText(spy: Recorded): number {
    return spy.mock.calls.filter(([arg]) => (typeof arg === 'string' && arg.length >= HUGE) || (typeof arg === 'number' && arg >= HUGE)).length;
}

/** What a blur leaves, in one object: the text in the field, the last change emitted, the last value committed. */
function committedState(input: HTMLInputElement, onchange: Recorded, oncommit: Recorded) {
    return {dom: input.value, emitted: onchange.mock.calls.at(-1)?.[0], committed: oncommit.mock.calls.at(-1)?.[0]};
}

describe('ExactDecimalInput — the digit budget counts no zero the backend drops (W-B64)', () => {
    // Red before the W-B64 cure: eleven characters after the point count as eleven decimals, past 10: invalid, and explained.
    it('keeps 0.10000000000 as typed and valid at maxFractionDigits=10 — one decimal for the backend — and a blur commits 0.1', async () => {
        const {input, onchange, oncommit, onvaliditychange} = setup({maxFractionDigits: 10});

        await fireEvent.input(input, {target: {value: '0.10000000000'}});

        expect(input, 'kept as typed while it is edited').toHaveValue('0.10000000000');
        expectNoDigitsError(input, TID);
        expect(lastValidity(onvaliditychange), 'one decimal is within a budget of ten').toMatchObject({digitsValid: true, valid: true});

        await fireEvent.blur(input);

        expect(committedState(input, onchange, oncommit), 'the blur commits the value without its zeros').toEqual({dom: '0.1', emitted: '0.1', committed: '0.1'});
    });

    // Red before the W-B64 cure: one character after the point counts as one decimal, past 0: invalid, and explained.
    it('accepts 5.0 at maxFractionDigits=0 — a whole number for the backend — and a blur commits 5', async () => {
        const {input, onchange, oncommit, onvaliditychange} = setup({maxFractionDigits: 0});

        await fireEvent.input(input, {target: {value: '5.0'}});

        expect(input, 'kept as typed while it is edited').toHaveValue('5.0');
        expectNoDigitsError(input, TID);
        expect(lastValidity(onvaliditychange), 'no decimal is within a budget of none').toMatchObject({digitsValid: true, valid: true});

        await fireEvent.blur(input);

        expect(committedState(input, onchange, oncommit), 'the blur commits the whole number').toEqual({dom: '5', emitted: '5', committed: '5'});
    });

    // Red before the W-B64 cure: thirteen characters before the point count as thirteen integer digits, past 12.
    it('accepts 0000000000001.5 at the default 12 + 12: its leading zeros are no integer digits', async () => {
        const {input, onvaliditychange} = setup();

        await fireEvent.input(input, {target: {value: '0000000000001.5'}});

        expect(input).toHaveValue('0000000000001.5');
        expectNoDigitsError(input, TID);
        expect(lastValidity(onvaliditychange), 'one integer digit is within a budget of twelve').toMatchObject({digitsValid: true, valid: true});
    });

    /*
     * Red before the W-B64 cure: the 40 000 zeros count as 40 000 decimals, so the value is refused for its digits and its
     * range is never asked (digitsValid false, rangeValid true). Reading it as the 5 it is must not cost what W-B66 saved:
     * the bounds are compared with the stripped value, never through a BigInt of every pasted zero.
     */
    it('range-checks a paste of 5. and 40 000 zeros as the 5 it is: refused for its range, not its digits — no BigInt sized by its text, within 1 000 ms', async () => {
        const {input, onvaliditychange} = setup({min: '0', max: '1'});
        const pasted = `5.${'0'.repeat(HUGE)}`;
        const bigint = vi.spyOn(globalThis, 'BigInt');
        try {
            const started = performance.now();
            await fireEvent.input(input, {target: {value: pasted}});
            const ms = performance.now() - started;

            expect(input.value === pasted, `the paste is kept as typed; the field holds ${shown(input.value)}`).toBe(true);
            const validity = lastValidity(onvaliditychange);
            const counted = {bigintsSizedByTheText: bigintsSizedByTheText(bigint), digitsValid: validity?.digitsValid, rangeValid: validity?.rangeValid, valid: validity?.valid};
            expect(counted, `5 and ${HUGE} zeros is 5 for the backend: within the digit budget, above max 1 (the paste took ${ms.toFixed(0)} ms)`).toEqual({bigintsSizedByTheText: 0, digitsValid: true, rangeValid: false, valid: false});
            expect(input, 'refused, for its range').toHaveAttribute('aria-invalid', 'true');
            const message = digitsError(TID);
            if (message) expect(message, 'none of its decimals counts: the digits message must not show').not.toBeVisible();
            expect(ms, `the paste took ${ms.toFixed(0)} ms`).toBeLessThan(BOUND_MS);
        } finally {
            bigint.mockRestore();
        }
    });

    /*
     * Red before the W-B64 cure: the value counts 40 000 decimals, past the budget, and the arrow leaves it as it is
     * (W-B66). Within the budget once its zeros are dropped, it steps from the 5 it is. The step is 1 here: setup()'s
     * own, 0.000000000001, would take it to 5.000000000001.
     */
    it('steps a value of 5. and 40 000 zeros from the 5 it is: ArrowUp at step 1 gives 6 — no BigInt sized by its text, within 1 000 ms', async () => {
        const {input, onchange} = setup({value: `5.${'0'.repeat(HUGE)}`, step: '1'});
        const bigint = vi.spyOn(globalThis, 'BigInt');
        try {
            const started = performance.now();
            await arrow(input, 'ArrowUp');
            const ms = performance.now() - started;

            const emitted = onchange.mock.calls.at(-1)?.[0];
            const stepped = {dom: shown(input.value), emitted: typeof emitted === 'string' ? shown(emitted) : emitted, bigintsSizedByTheText: bigintsSizedByTheText(bigint)};
            expect(stepped, `today the value counts ${HUGE} decimals, and the arrow leaves it as it is (the arrow took ${ms.toFixed(0)} ms)`).toEqual({dom: shown('6'), emitted: shown('6'), bigintsSizedByTheText: 0});
            expect(ms, `the arrow took ${ms.toFixed(0)} ms`).toBeLessThan(BOUND_MS);
        } finally {
            bigint.mockRestore();
        }
    });

    // Guard: a digit that is not a zero still counts — 1.10000000001 has eleven decimals, past 10.
    it('still refuses 1.10000000001 at maxFractionDigits=10, and says why: its last decimal is no zero', async () => {
        const {input} = setup({maxFractionDigits: 10});

        await fireEvent.input(input, {target: {value: '1.10000000001'}});

        expect(input).toHaveValue('1.10000000001');
        expectDigitsError(input, TID, 10);
    });

    // Guard: a value within the text budget steps from its text, its typed places kept.
    it('still steps 1.50 from its text: ArrowUp at step 1 gives 2.50', async () => {
        const {input, onchange} = setup({value: '1.50', step: '1'});

        await arrow(input, 'ArrowUp');

        expect(input).toHaveValue('2.50');
        expect(onchange).toHaveBeenLastCalledWith('2.50');
    });

    // Guard: the count is the field's own business. What it publishes keeps its seven fields, none added.
    it('publishes the same seven validity fields for a value whose zeros it drops', async () => {
        const {input, onvaliditychange} = setup({maxFractionDigits: 10});

        await fireEvent.input(input, {target: {value: '0.10000000000'}});

        expect(Object.keys(lastValidity(onvaliditychange) ?? {}).sort()).toEqual([...VALIDITY_FIELDS].sort());
    });
});
