// @vitest-environment jsdom
/**
 * ExactQuantityInput owns a locale-aware edit buffer while its parent owns the
 * normalized transaction quantity. These tests exercise both halves of that
 * loop: every onchange payload can be echoed back as a prop without rewriting
 * the text still under the user's cursor.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import ExactQuantityInput from './ExactQuantityInput.svelte';

const TID = 'exact-quantity';

// A fraction past the budget renders a translated message under the field (C-97b), and tests in several
// describes below type one: svelte-i18n is booted once, for the whole file.
beforeAll(async () => {
    await setupI18n();
});

interface QuantityValidity {
    normalized: string;
    empty: boolean;
    syntaxValid: boolean;
    requiredValid: boolean;
    digitsValid: boolean;
    rangeValid: boolean;
    signState: 'ok' | 'bad' | 'neutral';
    signValid: boolean;
    valid: boolean;
}

function mountWithParentLoop(overrides: Record<string, unknown> = {}) {
    const emissions: string[] = [];
    const commits: string[] = [];
    const validities: QuantityValidity[] = [];
    const onfocus = vi.fn();
    const onblur = vi.fn();
    const props = {
        value: '',
        step: '1',
        maxIntegerDigits: 12,
        maxFractionDigits: 6,
        allowNegative: true,
        testid: TID,
        ...overrides,
        onchange: (next: string) => void emissions.push(next),
        oncommit: (next: string) => void commits.push(next),
        onvaliditychange: (state: QuantityValidity) => void validities.push(state),
        onfocus,
        onblur,
    };
    const rendered = render(ExactQuantityInput, props);
    const input = screen.getByTestId(String(overrides.testid ?? TID)) as HTMLInputElement;
    const loopBack = async () => {
        const latest = emissions.at(-1);
        if (latest === undefined) throw new Error('ExactQuantityInput emitted no value for parent loopback');
        await rendered.rerender({...props, value: latest});
    };
    return {input, emissions, commits, validities, onfocus, onblur, props, loopBack, ...rendered};
}

async function arrow(input: HTMLInputElement, key: 'ArrowUp' | 'ArrowDown', repeat = false, modifiers: Partial<KeyboardEventInit> = {}): Promise<KeyboardEvent> {
    const event = new KeyboardEvent('keydown', {key, repeat, bubbles: true, cancelable: true, ...modifiers});
    await fireEvent(input, event);
    return event;
}

function lastValidity(validities: QuantityValidity[]): QuantityValidity | undefined {
    return validities.at(-1);
}

function hue(input: HTMLInputElement): string {
    return input.getAttribute('style') ?? '';
}

/**
 * C-97b — the message that says why a value over the fractional budget is refused: the field's own id
 * followed by `-digits-error`. Its text is the cure's choice and is never read here.
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

describe('ExactQuantityInput — controlled locale buffer', () => {
    it('keeps focused locale text through the parent echo, then commits canonical display/model', async () => {
        const {input, emissions, commits, loopBack} = mountWithParentLoop();

        await fireEvent.focus(input);
        await fireEvent.input(input, {target: {value: '1.234,560000'}});
        expect(input).toHaveValue('1.234,560000');
        expect(emissions.at(-1)).toBe('1234.560000');

        await loopBack();
        expect(input, 'parent echo must not clobber the focused raw buffer').toHaveValue('1.234,560000');

        await fireEvent.blur(input);
        expect(input).toHaveValue('1234.56');
        expect(emissions.at(-1)).toBe('1234.56');
        expect(commits.at(-1)).toBe('1234.56');
    });

    it.each([
        ['1234.560000', '1234.560000', '1234.56'],
        ['1,250000', '1.250000', '1.25'],
        ['1.250000', '1.250000', '1.25'],
        ['999.999.999.999,123456', '999999999999.123456', '999999999999.123456'],
    ])('normalizes %j to model %j and commits display %j', async (raw, normalized, canonical) => {
        const {input, emissions, commits, loopBack, unmount} = mountWithParentLoop();

        await fireEvent.input(input, {target: {value: raw}});
        expect(emissions.at(-1)).toBe(normalized);
        await loopBack();
        expect(input).toHaveValue(raw);

        await fireEvent.blur(input);
        expect(input).toHaveValue(canonical);
        expect(emissions.at(-1)).toBe(canonical);
        expect(commits.at(-1)).toBe(canonical);
        unmount();
    });

    it.each([
        ['-', '-', '-', true],
        [',', ',', ',', true],
        ['12,', '12,', '12.', false],
        ['1..2', '1..2', '1.2', false],
        ['EUR 12,34abc', '12,34', '12.34', false],
    ] as const)('keeps draft %j visible as %j and emits only normalized %j', async (typed, visible, normalized, invalid) => {
        const {input, emissions, commits, loopBack, unmount} = mountWithParentLoop();

        await fireEvent.input(input, {target: {value: typed}});
        expect(input).toHaveValue(visible);
        expect(emissions.at(-1)).toBe(normalized);
        expect(input).toHaveAttribute('aria-invalid', String(invalid));

        await loopBack();
        expect(input).toHaveValue(visible);
        await fireEvent.blur(input);
        if (invalid) {
            expect(input).toHaveValue(visible);
            expect(commits).toEqual([]);
        }
        unmount();
    });

    it('reseeds for a genuine parent value change', async () => {
        const {input, loopBack, props, rerender} = mountWithParentLoop({value: '12'});

        await fireEvent.input(input, {target: {value: '12,500000'}});
        await loopBack();
        expect(input).toHaveValue('12,500000');

        await rerender({...props, value: '7.250000'});
        expect(input).toHaveValue('7.25');
    });

    it('resetKey reseeds the raw buffer even when the normalized model is unchanged', async () => {
        const {input, loopBack, props, rerender} = mountWithParentLoop({value: '1.250000', resetKey: 0});

        await fireEvent.input(input, {target: {value: '1,250000'}});
        await loopBack();
        expect(input).toHaveValue('1,250000');

        await rerender({...props, value: '1.250000', resetKey: 1});
        expect(input).toHaveValue('1.25');
    });
});

describe('ExactQuantityInput — exact digits, bounds, and hold acceleration', () => {
    it('accepts 12+6 digits and emits either overflow visibly without truncation', async () => {
        const {input, emissions} = mountWithParentLoop();

        await fireEvent.input(input, {target: {value: '999999999999.123456'}});
        expect(input).toHaveValue('999999999999.123456');
        expect(emissions.at(-1)).toBe('999999999999.123456');
        expect(input).toHaveAttribute('aria-invalid', 'false');

        await fireEvent.input(input, {target: {value: '1.1234567'}});
        expect(input).toHaveValue('1.1234567');
        expect(emissions.at(-1)).toBe('1.1234567');
        expect(input).toHaveAttribute('aria-invalid', 'true');

        await fireEvent.input(input, {target: {value: '1000000000000.1'}});
        expect(input).toHaveValue('1000000000000.1');
        expect(emissions.at(-1)).toBe('1000000000000.1');
        expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('steps the high-precision ceiling exactly and clamps at exact bounds', async () => {
        const high = mountWithParentLoop({value: '999999999999.123455', step: '0.000001'});
        await arrow(high.input, 'ArrowUp');
        expect(high.input).toHaveValue('999999999999.123456');

        high.unmount();
        const upper = mountWithParentLoop({value: '9.999999', step: '0.000002', max: '10.000000'});
        await arrow(upper.input, 'ArrowUp');
        expect(upper.input).toHaveValue('10.000000');

        upper.unmount();
        const lower = mountWithParentLoop({value: '-9.999999', step: '0.000002', min: '-10.000000'});
        await arrow(lower.input, 'ArrowDown');
        expect(lower.input).toHaveValue('-10.000000');

        lower.unmount();
        const implicitZero = mountWithParentLoop({value: '0', step: '0.1', allowNegative: false});
        await arrow(implicitZero.input, 'ArrowDown');
        expect(implicitZero.input).toHaveValue('0');
    });

    it('uses acceleration by default with the full deterministic cadence', async () => {
        const {input} = mountWithParentLoop({value: '0'});
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
    });

    it('resets acceleration on keyup, direction change, and target change', async () => {
        const first = mountWithParentLoop({testid: 'quantity-first', value: '0'});
        const second = mountWithParentLoop({testid: 'quantity-second', value: '0'});

        await arrow(first.input, 'ArrowUp');
        for (let repeat = 1; repeat <= 20; repeat += 1) await arrow(first.input, 'ArrowUp', true);
        expect(first.input).toHaveValue('30');

        await arrow(first.input, 'ArrowDown', true);
        expect(first.input).toHaveValue('29');

        await fireEvent.keyUp(first.input, {key: 'ArrowDown'});
        await arrow(first.input, 'ArrowDown', true);
        expect(first.input).toHaveValue('28');

        await arrow(second.input, 'ArrowUp', true);
        expect(second.input).toHaveValue('1');
    });

    it('accelerates a fractional high-magnitude quantity without float residue', async () => {
        const {input} = mountWithParentLoop({
            value: '999999999990.123450',
            step: '0.000001',
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
        const {input, emissions} = mountWithParentLoop({value: '7'});

        const event = await arrow(input, 'ArrowUp', false, modifiers);

        expect(event.defaultPrevented).toBe(false);
        expect(input).toHaveValue('7');
        expect(emissions).toEqual([]);
    });
});

describe('ExactQuantityInput — sign state and validity', () => {
    // The sign colour is a colour role at 70% on the inline border. No theme stylesheet is loaded here, so the unit
    // asserts the role the style names; the colour the browser resolves is the e2e's («Sign coloring», transactions-modals).
    const OK_SIGN_BORDER = 'border-color: color-mix(in oklab, var(--lf-success) 70%, transparent)';
    const BAD_SIGN_BORDER = 'border-color: color-mix(in oklab, var(--lf-danger) 70%, transparent)';

    it.each([
        ['positive', '1', 'ok', true, OK_SIGN_BORDER],
        ['positive', '-1', 'bad', false, BAD_SIGN_BORDER],
        ['positive', '-0.000000', 'neutral', true, ''],
        ['negative', '-1', 'ok', true, OK_SIGN_BORDER],
        ['negative', '1', 'bad', false, BAD_SIGN_BORDER],
        ['negative', '-0.000000', 'neutral', true, ''],
        ['nonzero', '-1', 'ok', true, OK_SIGN_BORDER],
        ['nonzero', '0', 'bad', false, BAD_SIGN_BORDER],
        ['nonzero', '-0.000000', 'bad', false, BAD_SIGN_BORDER],
        ['zero', '-0.000000', 'ok', true, OK_SIGN_BORDER],
        ['zero', '0.000001', 'bad', false, BAD_SIGN_BORDER],
        ['any', '-999999999999.123456', 'neutral', true, ''],
    ] as const)('%s classifies %j as %s', async (signRule, value, signState, signValid, expectedBorder) => {
        const {input, validities, unmount} = mountWithParentLoop({signRule});

        await fireEvent.input(input, {target: {value}});
        await waitFor(() => expect(lastValidity(validities)?.signState).toBe(signState));

        expect(lastValidity(validities)?.signValid).toBe(signValid);
        expect(lastValidity(validities)?.valid).toBe(signValid);
        if (expectedBorder) expect(hue(input)).toContain(expectedBorder);
        else expect(hue(input), 'a neutral sign paints no border colour').not.toContain('border-color');
        unmount();
    });

    it('suppresses sign color when syntax or digit validity fails', async () => {
        const syntax = mountWithParentLoop({signRule: 'positive'});
        await fireEvent.input(syntax.input, {target: {value: '-'}});
        expect(syntax.input).toHaveAttribute('aria-invalid', 'true');
        expect(hue(syntax.input)).not.toContain('border-color');

        syntax.unmount();
        const digits = mountWithParentLoop({signRule: 'positive'});
        await fireEvent.input(digits.input, {target: {value: '1000000000000'}});
        expect(lastValidity(digits.validities)?.signState).toBe('ok');
        expect(digits.input).toHaveAttribute('aria-invalid', 'true');
        expect(hue(digits.input)).not.toContain('border-color');
    });

    it.each([
        {
            name: 'required empty',
            props: {required: true},
            typed: null,
            expected: {normalized: '', empty: true, syntaxValid: true, requiredValid: false, digitsValid: true, rangeValid: true, signState: 'neutral', signValid: true, valid: false},
        },
        {
            name: 'syntax',
            props: {},
            typed: '-',
            expected: {normalized: '-', empty: false, syntaxValid: false, requiredValid: true, digitsValid: true, rangeValid: true, signState: 'neutral', signValid: true, valid: false},
        },
        {
            name: 'digits',
            props: {signRule: 'positive'},
            typed: '1000000000000',
            expected: {normalized: '1000000000000', empty: false, syntaxValid: true, requiredValid: true, digitsValid: false, rangeValid: true, signState: 'ok', signValid: true, valid: false},
        },
        {
            name: 'range',
            props: {signRule: 'positive', max: '10'},
            typed: '10.000001',
            expected: {normalized: '10.000001', empty: false, syntaxValid: true, requiredValid: true, digitsValid: true, rangeValid: false, signState: 'ok', signValid: true, valid: false},
        },
        {
            name: 'sign',
            props: {signRule: 'positive'},
            typed: '-1',
            expected: {normalized: '-1', empty: false, syntaxValid: true, requiredValid: true, digitsValid: true, rangeValid: true, signState: 'bad', signValid: false, valid: false},
        },
        {
            name: 'externalInvalid',
            props: {value: '1', signRule: 'positive', externalInvalid: true},
            typed: null,
            expected: {normalized: '1', empty: false, syntaxValid: true, requiredValid: true, digitsValid: true, rangeValid: true, signState: 'ok', signValid: true, valid: false},
        },
    ])('publishes complete validity fields for $name', async ({props, typed, expected}) => {
        const {input, validities, unmount} = mountWithParentLoop(props);
        if (typed !== null) await fireEvent.input(input, {target: {value: typed}});

        await waitFor(() => expect(lastValidity(validities)).toEqual(expected));
        unmount();
    });
});

describe('ExactQuantityInput — accessibility and inert states', () => {
    it('forwards text-input, form, ARIA, style, class, and focus contracts', async () => {
        const {input, onfocus, onblur} = mountWithParentLoop({
            value: '1.25',
            id: 'quantity-id',
            name: 'quantity-name',
            required: true,
            placeholder: 'quantity-placeholder-token',
            ariaLabel: 'quantity-label-token',
            ariaDescribedby: 'quantity-hint-token',
            ariaErrormessage: 'quantity-error-token',
            className: 'quantity-class-token',
            style: 'padding-left: 9px',
        });

        expect(input).toHaveAttribute('type', 'text');
        expect(input).toHaveAttribute('inputmode', 'decimal');
        // No maxlength pin here any more: C-97b removes the attribute (pinned below, «the digit budget says why»).
        expect(input).toHaveAttribute('id', 'quantity-id');
        expect(input).toHaveAttribute('name', 'quantity-name');
        expect(input).toBeRequired();
        expect(input).toHaveAttribute('placeholder', 'quantity-placeholder-token');
        expect(input).toHaveAttribute('aria-label', 'quantity-label-token');
        expect(input).toHaveAttribute('aria-describedby', 'quantity-hint-token');
        expect(input).toHaveAttribute('aria-errormessage', 'quantity-error-token');
        expect(input.classList.contains('quantity-class-token')).toBe(true);
        expect(input.style.paddingLeft).toBe('9px');
        expect(input).not.toHaveAttribute('aria-valuenow');
        expect(screen.queryByRole('spinbutton')).toBeNull();
        expect(screen.getByRole('textbox')).toBe(input);

        await fireEvent.focus(input);
        await fireEvent.blur(input);
        expect(onfocus).toHaveBeenCalledTimes(1);
        expect(onblur).toHaveBeenCalledTimes(1);
    });

    it.each([
        ['readonly', {readonly: true}],
        ['disabled', {disabled: true}],
    ] as const)('%s state stays visible but neither mutates nor emits', async (name, state) => {
        const {input, emissions, commits} = mountWithParentLoop({value: '1.25', ...state});

        if (name === 'readonly') expect(input).toHaveAttribute('readonly');
        else expect(input).toBeDisabled();

        await arrow(input, 'ArrowUp');
        await fireEvent.keyDown(input, {key: 'Enter'});
        await fireEvent.blur(input);

        expect(input).toHaveValue('1.25');
        expect(emissions).toEqual([]);
        expect(commits).toEqual([]);
    });
});

/**
 * C-97b — the digit budget explains itself, through this component's own testid. ExactQuantityInput
 * hands `maxFractionDigits` on to ExactDecimalInput, so the message is the inner field's, under the
 * id the caller gave (`exact-quantity-digits-error`), carrying the budget in `data-max`. Its text is
 * the cure's choice and is never read.
 *
 * The 6 of `mountWithParentLoop`'s default props is a fixture, not the transaction form's budget:
 * C-97b raises the form's to 10, and that is pinned in TransactionFormModal.test.ts.
 */
describe('ExactQuantityInput — the digit budget says why it refuses (C-97b)', () => {
    // Red today: no message element exists.
    it.each([
        [6, '0.1234567', '0.1234567'],
        [10, '0,12345678912', '0.12345678912'],
    ])('over maxFractionDigits=%i, %j is kept as typed, emitted whole as %j, flagged and explained', async (max, typed, normalized) => {
        const {input, emissions, loopBack} = mountWithParentLoop({maxFractionDigits: max});

        await fireEvent.input(input, {target: {value: typed}});
        expect(emissions.at(-1), 'the model is the whole value, never cut to the budget').toBe(normalized);
        await loopBack();

        expect(input).toHaveValue(typed);
        expectDigitsError(input, TID, max);
    });

    // Red today: the message never appears, so it cannot be withdrawn either.
    it('withdraws the message once the value is back within the budget', async () => {
        const {input, loopBack} = mountWithParentLoop();

        await fireEvent.input(input, {target: {value: '0.1234567'}});
        await loopBack();
        expectDigitsError(input, TID, 6);

        await fireEvent.input(input, {target: {value: '0.123456'}});
        await loopBack();
        expectNoDigitsError(input, TID);
    });

    // Guard: green today (no message exists at all); after the cure a valid value must not grow one.
    it.each([
        [6, '0.123456'],
        [10, '0.1234567891'],
    ])('within maxFractionDigits=%i, %j is valid and shows no message', async (max, typed) => {
        const {input, loopBack} = mountWithParentLoop({maxFractionDigits: max});

        await fireEvent.input(input, {target: {value: typed}});
        await loopBack();

        expect(input).toHaveValue(typed);
        expectNoDigitsError(input, TID);
    });

    // Red today: the field publishes maxlength="23" (a signed 12+6) and no message exists. jsdom does not
    // apply maxlength to a value set by script, so the attribute is the honest handle on the browser's cut.
    it('publishes no maxlength, and keeps a longer paste whole, flagged and explained', async () => {
        const {input, emissions} = mountWithParentLoop();
        const pasted = `-0.${'1234567890'.repeat(3)}`;
        expect(pasted.length, 'premise: longer than the 23 characters the old maxlength left a signed 12+6').toBeGreaterThan(23);
        expect.soft(input.getAttribute('maxlength'), 'no maxlength may cut a paste short: the budget is applied by the flag and its message').toBeNull();

        await fireEvent.input(input, {target: {value: pasted}});

        expect(input).toHaveValue(pasted);
        expect(emissions.at(-1), 'the model is the whole paste').toBe(pasted);
        expectDigitsError(input, TID, 6);
    });
});

/**
 * W-B64 — the digit budget counts no zero the backend drops. The backend counts no leading zero of the integer part and no
 * trailing zero of the fraction (`precision._digit_counts`); this wrapper counted characters too (`withinDigitBudget`), so
 * a parent value of `0.10000000000` — one decimal — was past a budget of 10: shown as given, and refused.
 *
 * The contract: within the budget once those zeros are dropped, a parent value is shown as the decimal it is
 * (`formatDecimalForDisplay`, as for any value within the budget: `0.1`) and published valid. A value whose digits are
 * past the budget is still shown whole and refused: nothing cuts it to fit.
 */
describe('ExactQuantityInput — the digit budget counts no zero the backend drops (W-B64)', () => {
    // Red before the W-B64 cure: withinDigitBudget counts eleven decimals, so the value is shown as given and refused.
    it('shows a parent value of 0.10000000000 at maxFractionDigits=10 as 0.1, and publishes it valid', async () => {
        const {input, validities} = mountWithParentLoop({value: '0.10000000000', maxFractionDigits: 10});

        // `empty: false` waits for the inner field's own verdict, never the state this wrapper starts from.
        await waitFor(() => {
            const validity = lastValidity(validities);
            expect({displayed: input.value, empty: validity?.empty, digitsValid: validity?.digitsValid, valid: validity?.valid}, 'one decimal for the backend, within a budget of ten').toEqual({displayed: '0.1', empty: false, digitsValid: true, valid: true});
        });
        expectNoDigitsError(input, TID);
    });

    // Guard: a parent value really past the budget is shown whole and refused — formatted, it would be cut to ten decimals.
    it('still shows a parent value of 0.10000000001 at maxFractionDigits=10 whole, refused, and says why', async () => {
        const {input, validities} = mountWithParentLoop({value: '0.10000000001', maxFractionDigits: 10});

        await waitFor(() => expect(lastValidity(validities)).toMatchObject({empty: false, digitsValid: false, valid: false}));
        expect(input, 'never cut to fit the budget').toHaveValue('0.10000000001');
        expectDigitsError(input, TID, 10);
    });
});

/**
 * B-48 — at most fifteen significant digits (D-K3-6). The backend keeps a quantity of at most 15 significant digits,
 * leading and trailing zeros not counted (`precision._digit_counts`, refusal `significantDigitsExceeded`); the form
 * caps the integer digits (15) and the decimals (10) apart, so `999999999999999.5` — fifteen and one, sixteen
 * significant — passes both budgets and is refused on save.
 *
 * The contract: an additive prop `maxSignificantDigits`, no cap by default. Over it the field is `aria-invalid`, and the
 * validity it publishes has `digitsValid: false`, `valid: false`; the value is kept whole, as every refused value is. The
 * cases pass the budgets the transaction form gives a quantity (15 integer digits, 10 decimals), so the significant
 * digits are the only limit in play. The message the form shows under the field is TransactionFormModal.test.ts's.
 */
describe('ExactQuantityInput — at most maxSignificantDigits significant digits (B-48)', () => {
    const FORM_BUDGET = {maxIntegerDigits: 15, maxFractionDigits: 10};

    /** Type `typed` behind the parent loop and wait for the validity published for it. */
    async function typeQuantity(typed: string, overrides: Record<string, unknown>) {
        const mounted = mountWithParentLoop(overrides);
        await fireEvent.input(mounted.input, {target: {value: typed}});
        expect(mounted.emissions.at(-1), 'the model is the whole value, never cut').toBe(typed);
        await mounted.loopBack();
        expect(mounted.input, 'kept as typed').toHaveValue(typed);
        await waitFor(() => expect(lastValidity(mounted.validities)).toMatchObject({normalized: typed, empty: false}));
        return mounted;
    }

    // Red today: nothing counts the significant digits — fifteen integer digits and one decimal are within both budgets.
    it('B-48: with maxSignificantDigits=15, 999999999999999.5 (16 significant digits) is refused: aria-invalid, digitsValid false, valid false', async () => {
        const {input, validities} = await typeQuantity('999999999999999.5', {...FORM_BUDGET, maxSignificantDigits: 15});

        await waitFor(() => expect(lastValidity(validities), 'B-48: the published validity accepts sixteen significant digits').toMatchObject({digitsValid: false, valid: false}));
        expect(input, 'B-48: sixteen significant digits are past the cap of fifteen').toHaveAttribute('aria-invalid', 'true');
    });

    // Guard, green today: fifteen are within the cap.
    it('B-48 guard: with maxSignificantDigits=15, 99999999999999.5 (15 significant digits) is valid', async () => {
        const {input, validities} = await typeQuantity('99999999999999.5', {...FORM_BUDGET, maxSignificantDigits: 15});

        expect(input).toHaveAttribute('aria-invalid', 'false');
        expect(lastValidity(validities)).toMatchObject({digitsValid: true, valid: true});
    });

    // Guard, green today: the cap is opt-in — no prop, no cap.
    it('B-48 guard: without maxSignificantDigits, 999999999999999.5 is valid', async () => {
        const {input, validities} = await typeQuantity('999999999999999.5', FORM_BUDGET);

        expect(input).toHaveAttribute('aria-invalid', 'false');
        expect(lastValidity(validities)).toMatchObject({digitsValid: true, valid: true});
    });
});
