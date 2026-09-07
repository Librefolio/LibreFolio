import {beforeEach, describe, expect, it} from 'vitest';
import {decimalArrowStep, normalizeDecimalInput, resetDecimalArrowHold, stepDecimalValue} from '$lib/utils/core/parseDecimalInput';

describe('normalizeDecimalInput', () => {
    it('leaves canonical input untouched', () => {
        expect(normalizeDecimalInput('5.9')).toBe('5.9');
        expect(normalizeDecimalInput('1234')).toBe('1234');
        expect(normalizeDecimalInput('-0.125')).toBe('-0.125');
        expect(normalizeDecimalInput('')).toBe('');
    });

    it('reads a lone comma as the decimal separator', () => {
        expect(normalizeDecimalInput('5,9')).toBe('5.9');
        expect(normalizeDecimalInput('-1234,5678')).toBe('-1234.5678');
        expect(normalizeDecimalInput(' 0,5 ')).toBe('0.5');
    });

    it('unpacks European grouping', () => {
        expect(normalizeDecimalInput('1.234,56')).toBe('1234.56');
        expect(normalizeDecimalInput('1.234.567,89')).toBe('1234567.89');
        expect(normalizeDecimalInput('-12.345,6')).toBe('-12345.6');
        expect(normalizeDecimalInput('1.234.567')).toBe('1234567');
    });

    it('unpacks Anglo grouping', () => {
        expect(normalizeDecimalInput('1,234.56')).toBe('1234.56');
        expect(normalizeDecimalInput('1,234,567.89')).toBe('1234567.89');
        expect(normalizeDecimalInput('1,234,567')).toBe('1234567');
    });

    it('keeps every digit when the grouping is not well formed', () => {
        expect(normalizeDecimalInput('1.4,1')).toBe('1.41');
        expect(normalizeDecimalInput('4.6,30')).toBe('4.630');
        expect(normalizeDecimalInput('4,6.30')).toBe('4.630');
        expect(normalizeDecimalInput('1.2.3')).toBe('1.23');
        expect(normalizeDecimalInput('-4.6,30')).toBe('-4.630');
        expect(normalizeDecimalInput('12,34,56')).toBe('12.3456');
    });

    it('keeps half-typed values usable', () => {
        expect(normalizeDecimalInput('5,')).toBe('5.');
        expect(normalizeDecimalInput('5.')).toBe('5.');
        expect(normalizeDecimalInput('.5')).toBe('.5');
    });

    it('returns the raw input when there is no number in it', () => {
        expect(normalizeDecimalInput('abc')).toBe('abc');
        expect(normalizeDecimalInput('-')).toBe('-');
    });

    it('strips stray characters around a number', () => {
        expect(normalizeDecimalInput('1 234,5')).toBe('1234.5');
        expect(normalizeDecimalInput('€ 12,50')).toBe('12.50');
    });
});

describe('stepDecimalValue', () => {
    it('steps at the precision already in use', () => {
        expect(stepDecimalValue('5.9', 1)).toBe('6.9');
        expect(stepDecimalValue('5.9', -1)).toBe('4.9');
        expect(stepDecimalValue('5', 1)).toBe('6');
        expect(stepDecimalValue('', 1)).toBe('1');
    });

    it('does not drift on floats', () => {
        expect(stepDecimalValue('5.9', -1, 0.1)).toBe('5.8');
        expect(stepDecimalValue('0.3', -1, 0.1)).toBe('0.2');
    });

    it('normalizes before stepping', () => {
        expect(stepDecimalValue('5,9', 1)).toBe('6.9');
        expect(stepDecimalValue('1.234,50', 1)).toBe('1235.50');
    });

    it('goes below zero when asked', () => {
        expect(stepDecimalValue('0', -1)).toBe('-1');
    });
});

describe('decimalArrowStep hold acceleration', () => {
    const target = {} as EventTarget;

    function press(value: string, {repeat, key = 'ArrowUp', step = 1}: {repeat: boolean; key?: string; step?: number}): string {
        const event = {key, repeat, target, ctrlKey: false, metaKey: false, altKey: false, preventDefault: () => {}} as unknown as KeyboardEvent;
        return decimalArrowStep(event, value, step) as string;
    }

    beforeEach(() => resetDecimalArrowHold());

    it('steps by one while the key is tapped, however many times', () => {
        let value = '7';
        for (let i = 0; i < 30; i += 1) value = press(value, {repeat: false});
        expect(value).toBe('37');
    });

    it('escalates to ten only after fifteen repeats and at the next round ten', () => {
        let value = press('7', {repeat: false});
        const seen: string[] = [value];
        for (let i = 0; i < 25; i += 1) {
            value = press(value, {repeat: true});
            seen.push(value);
        }
        // Unit steps up to 30 (the first ten reached after the 15th repeat), then tens.
        expect(seen.slice(0, 22)).toEqual(Array.from({length: 22}, (_, i) => String(8 + i)));
        expect(seen).toContain('30');
        expect(seen).toContain('40');
        expect(Number(value)).toBe(60);
    });

    it('accelerates downwards too', () => {
        let value = press('100', {repeat: false, key: 'ArrowDown'});
        for (let i = 0; i < 25; i += 1) value = press(value, {repeat: true, key: 'ArrowDown'});
        // 99 … 80 one by one, then tens all the way down.
        expect(Number(value)).toBe(20);
    });

    it('drops back to the base step when the direction changes', () => {
        let value = press('7', {repeat: false});
        for (let i = 0; i < 25; i += 1) value = press(value, {repeat: true});
        const afterTurn = press(value, {repeat: true, key: 'ArrowDown'});
        expect(Number(value) - Number(afterTurn)).toBe(1);
    });
});
