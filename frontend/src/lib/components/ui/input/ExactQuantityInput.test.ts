// @vitest-environment jsdom
/**
 * ExactQuantityInput owns a locale-aware edit buffer while its parent owns the
 * normalized transaction quantity. These tests exercise both halves of that
 * loop: every onchange payload can be echoed back as a prop without rewriting
 * the text still under the user's cursor.
 */
import {describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, waitFor} from '$test/component';
import ExactQuantityInput from './ExactQuantityInput.svelte';

const TID = 'exact-quantity';

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
    it.each([
        ['positive', '1', 'ok', true, '163.223'],
        ['positive', '-1', 'bad', false, '25.331'],
        ['positive', '-0.000000', 'neutral', true, ''],
        ['negative', '-1', 'ok', true, '163.223'],
        ['negative', '1', 'bad', false, '25.331'],
        ['negative', '-0.000000', 'neutral', true, ''],
        ['nonzero', '-1', 'ok', true, '163.223'],
        ['nonzero', '0', 'bad', false, '25.331'],
        ['nonzero', '-0.000000', 'bad', false, '25.331'],
        ['zero', '-0.000000', 'ok', true, '163.223'],
        ['zero', '0.000001', 'bad', false, '25.331'],
        ['any', '-999999999999.123456', 'neutral', true, ''],
    ] as const)('%s classifies %j as %s', async (signRule, value, signState, signValid, expectedHue) => {
        const {input, validities, unmount} = mountWithParentLoop({signRule});

        await fireEvent.input(input, {target: {value}});
        await waitFor(() => expect(lastValidity(validities)?.signState).toBe(signState));

        expect(lastValidity(validities)?.signValid).toBe(signValid);
        expect(lastValidity(validities)?.valid).toBe(signValid);
        if (expectedHue) expect(hue(input)).toContain(expectedHue);
        else {
            expect(hue(input)).not.toContain('163.223');
            expect(hue(input)).not.toContain('25.331');
        }
        unmount();
    });

    it('suppresses sign color when syntax or digit validity fails', async () => {
        const syntax = mountWithParentLoop({signRule: 'positive'});
        await fireEvent.input(syntax.input, {target: {value: '-'}});
        expect(syntax.input).toHaveAttribute('aria-invalid', 'true');
        expect(hue(syntax.input)).not.toContain('163.223');
        expect(hue(syntax.input)).not.toContain('25.331');

        syntax.unmount();
        const digits = mountWithParentLoop({signRule: 'positive'});
        await fireEvent.input(digits.input, {target: {value: '1000000000000'}});
        expect(lastValidity(digits.validities)?.signState).toBe('ok');
        expect(digits.input).toHaveAttribute('aria-invalid', 'true');
        expect(hue(digits.input)).not.toContain('163.223');
        expect(hue(digits.input)).not.toContain('25.331');
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
        expect(input).toHaveAttribute('maxlength', '23');
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
