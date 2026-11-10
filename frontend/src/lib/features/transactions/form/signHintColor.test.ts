import {describe, it, expect} from 'vitest';
import {computeSignHint} from './signHintColor';

describe('computeSignHint', () => {
    it('treats NaN as neither ok nor bad (no colouring)', () => {
        expect(computeSignHint(NaN, 'positive')).toEqual({ok: false, bad: false});
    });

    describe('positive rule', () => {
        it('greens a positive value and reds a negative one', () => {
            expect(computeSignHint(5, 'positive')).toEqual({ok: true, bad: false});
            expect(computeSignHint(-5, 'positive')).toEqual({ok: false, bad: true});
        });
        it('leaves zero uncoloured', () => {
            expect(computeSignHint(0, 'positive')).toEqual({ok: false, bad: false});
        });
    });

    describe('negative rule (auto-flip: user enters positive)', () => {
        it('greens a positive value and reds a negative one, like positive', () => {
            expect(computeSignHint(5, 'negative')).toEqual({ok: true, bad: false});
            expect(computeSignHint(-5, 'negative')).toEqual({ok: false, bad: true});
        });
        it('leaves zero uncoloured', () => {
            expect(computeSignHint(0, 'negative')).toEqual({ok: false, bad: false});
        });
    });

    describe('nonzero rule', () => {
        it('greens any non-zero and reds exactly zero', () => {
            expect(computeSignHint(3, 'nonzero')).toEqual({ok: true, bad: false});
            expect(computeSignHint(-3, 'nonzero')).toEqual({ok: true, bad: false});
            expect(computeSignHint(0, 'nonzero')).toEqual({ok: false, bad: true});
        });
    });

    describe('zero rule', () => {
        it('greens exactly zero and reds any non-zero', () => {
            expect(computeSignHint(0, 'zero')).toEqual({ok: true, bad: false});
            expect(computeSignHint(1, 'zero')).toEqual({ok: false, bad: true});
        });
    });

    describe('permissive / unknown rules', () => {
        it.each(['any', 'free', 'optional', 'something-else'])('never colours under %s', (rule) => {
            expect(computeSignHint(5, rule)).toEqual({ok: false, bad: false});
            expect(computeSignHint(-5, rule)).toEqual({ok: false, bad: false});
        });
    });
});
