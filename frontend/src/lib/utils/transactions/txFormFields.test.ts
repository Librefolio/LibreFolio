import {describe, it, expect} from 'vitest';
import {deduplicateIssues, signLabel, signHintKey} from './txFormFields';
import type {ValidationIssue} from '$lib/components/transactions/types';

function iss(over: Partial<ValidationIssue>): ValidationIssue {
    return {operation: 'create', index: 0, error: 'boom', ...over};
}

describe('deduplicateIssues', () => {
    it('returns [] for an empty list', () => {
        expect(deduplicateIssues([])).toEqual([]);
    });

    it('keeps a single issue untouched', () => {
        const list = [iss({code: 'A'})];
        expect(deduplicateIssues(list)).toEqual(list);
    });

    it('collapses repeats sharing the same code to the first occurrence', () => {
        const first = iss({code: 'DUP', error: 'first'});
        const second = iss({code: 'DUP', error: 'second'});
        expect(deduplicateIssues([first, second])).toEqual([first]);
    });

    it('keys on the error string when code is absent (undefined)', () => {
        const a = iss({error: 'same'});
        const b = iss({error: 'same'});
        expect(deduplicateIssues([a, b])).toEqual([a]);
    });

    it('keys on the error string when code is null (?? falls through)', () => {
        const a = iss({code: null, error: 'sameErr'});
        const b = iss({code: null, error: 'sameErr'});
        expect(deduplicateIssues([a, b])).toEqual([a]);
    });

    it('treats different codes as distinct even with an identical error', () => {
        const a = iss({code: 'X', error: 'msg'});
        const b = iss({code: 'Y', error: 'msg'});
        expect(deduplicateIssues([a, b])).toHaveLength(2);
    });

    it('a coded issue and an uncoded issue whose error equals that code collide (documents the ?? keying)', () => {
        // First has no code → key = error "SHARED". Second has code "SHARED" → key = "SHARED".
        const a = iss({error: 'SHARED'});
        const b = iss({code: 'SHARED', error: 'other'});
        expect(deduplicateIssues([a, b])).toEqual([a]);
    });
});

describe('signLabel', () => {
    it('positive → (+)', () => expect(signLabel('positive')).toBe('(+)'));
    it('negative → (−)', () => expect(signLabel('negative')).toBe('(−)'));
    it('nonzero → (≠0)', () => expect(signLabel('nonzero')).toBe('(≠0)'));
    it('zero → empty (no glyph, only a hint)', () => expect(signLabel('zero')).toBe(''));
    it('free → empty (unconstrained)', () => expect(signLabel('free')).toBe(''));
});

describe('signHintKey', () => {
    it('positive → hintSignPositive key', () => expect(signHintKey('positive')).toBe('transactions.form.hintSignPositive'));
    it('negative → hintSignNegative key', () => expect(signHintKey('negative')).toBe('transactions.form.hintSignNegative'));
    it('zero → hintSignZero key (has a hint although signLabel is empty)', () => expect(signHintKey('zero')).toBe('transactions.form.hintSignZero'));
    it('nonzero → hintSignNonzero key', () => expect(signHintKey('nonzero')).toBe('transactions.form.hintSignNonzero'));
    it('free → null (no hint)', () => expect(signHintKey('free')).toBeNull());
});
