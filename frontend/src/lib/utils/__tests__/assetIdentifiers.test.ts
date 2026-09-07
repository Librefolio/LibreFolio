/**
 * Tests for the identifier decision rules.
 *
 * These pin the two beta-test findings that were pure logic mistakes — a prompt that reappeared
 * on codes already stored among the alternates, and a blank column reported as a conflict — plus
 * the invariant that nothing is ever discarded when a primary is elected.
 */

import {describe, expect, it} from 'vitest';
import {demotedValues, mergeOther, needsPrimaryChoice, normIdentifier, otherContains, pendingIdentifier} from '../assetIdentifiers';

describe('normIdentifier', () => {
    it('treats a blank column as absent, not as a value', () => {
        expect(normIdentifier('')).toBeNull();
        expect(normIdentifier('   ')).toBeNull();
        expect(normIdentifier(null)).toBeNull();
        expect(normIdentifier(undefined)).toBeNull();
    });

    it('trims but preserves the original casing', () => {
        expect(normIdentifier('  it0005634792 ')).toBe('it0005634792');
    });

    it('ignores non-string values instead of coercing them', () => {
        expect(normIdentifier(42)).toBeNull();
        expect(normIdentifier(['IT0005634792'])).toBeNull();
    });
});

describe('otherContains', () => {
    it('matches regardless of case and surrounding blanks', () => {
        expect(otherContains([' it0005634792 '], 'IT0005634792')).toBe(true);
    });

    it('is false for an empty needle, so a blank never looks known', () => {
        expect(otherContains(['IT0005634792'], '  ')).toBe(false);
    });

    it('tolerates a missing or malformed list', () => {
        expect(otherContains(null, 'X')).toBe(false);
        expect(otherContains('IT0005634792', 'IT0005634792')).toBe(false);
        expect(otherContains([null, 7, 'IT0005634792'], 'IT0005634792')).toBe(true);
    });
});

describe('pendingIdentifier', () => {
    it('asks nothing when the report carries no code', () => {
        expect(pendingIdentifier(null, 'IT0005634792', [], 'identifier_isin')).toBeNull();
        expect(pendingIdentifier('   ', null, [], 'identifier_isin')).toBeNull();
    });

    it('asks nothing when the asset already holds the same code as primary', () => {
        expect(pendingIdentifier('IT0005634792', 'it0005634792', [], 'identifier_isin')).toBeNull();
    });

    /** A2 — the prompt used to reappear forever on codes already saved as alternates. */
    it('asks nothing when the code is already among the alternates', () => {
        expect(pendingIdentifier('IT0005634792', 'IT0005612345', ['IT0005634792'], 'identifier_isin')).toBeNull();
        expect(pendingIdentifier('IT0005634792', 'IT0005612345', [' it0005634792'], 'identifier_isin')).toBeNull();
    });

    /** A3 — an empty ISIN column is a gap, not a clash: no "replace?" wording for it. */
    it('reports a blank column as absent rather than as a conflict', () => {
        const pending = pendingIdentifier('IT0005634792', '', [], 'identifier_isin');
        expect(pending).not.toBeNull();
        expect(pending?.existing).toBeNull();
    });

    /** The CUM case: two real codes, both must survive — so a decision is owed. */
    it('reports a genuine clash with both values in play', () => {
        const pending = pendingIdentifier('IT0005634792', 'IT0005612345', ['SOME NAME'], 'identifier_isin');
        expect(pending).toEqual({field: 'identifier_isin', extracted: ['IT0005634792'], existing: 'IT0005612345'});
    });

    it('trims the extracted value it hands back', () => {
        expect(pendingIdentifier('  IT0005634792 ', null, [], 'identifier_isin')?.extracted).toEqual(['IT0005634792']);
    });

    it('carries the field through unchanged', () => {
        expect(pendingIdentifier('VWCE', null, [], 'identifier_ticker')?.field).toBe('identifier_ticker');
    });

    // --- a unified group carries several codes at once ---

    it('asks one question for every unknown code the group carries', () => {
        const pending = pendingIdentifier(['IT0005634792', 'IT0005612345'], null, [], 'identifier_isin');
        expect(pending?.extracted).toEqual(['IT0005634792', 'IT0005612345']);
        expect(pending?.existing).toBeNull();
    });

    it('drops the codes the asset already knows and keeps the rest', () => {
        const pending = pendingIdentifier(['IT0005634792', 'IT0005612345'], 'IT0005634792', [], 'identifier_isin');
        expect(pending?.extracted).toEqual(['IT0005612345']);
        expect(pending?.existing).toBe('IT0005634792');
    });

    it('returns nothing when the group adds no code the asset lacks', () => {
        expect(pendingIdentifier(['IT0005634792', 'it0005612345'], 'IT0005634792', ['IT0005612345'], 'identifier_isin')).toBeNull();
    });

    it('deduplicates repeated codes coming from different files', () => {
        expect(pendingIdentifier(['IT0005634792', ' it0005634792 '], null, [], 'identifier_isin')?.extracted).toEqual(['IT0005634792']);
    });

    it('tolerates an empty or all-blank list', () => {
        expect(pendingIdentifier([], null, [], 'identifier_isin')).toBeNull();
        expect(pendingIdentifier(['', '  ', null], null, [], 'identifier_isin')).toBeNull();
    });
});

describe('needsPrimaryChoice', () => {
    it('is a confirmation, not an election, for one code on an empty column', () => {
        const pending = pendingIdentifier('IT0005634792', '', [], 'identifier_isin')!;
        expect(needsPrimaryChoice(pending)).toBe(false);
    });

    it('is an election as soon as the asset already holds one', () => {
        const pending = pendingIdentifier('IT0005634792', 'IT0005612345', [], 'identifier_isin')!;
        expect(needsPrimaryChoice(pending)).toBe(true);
    });

    it('is an election when the group alone carries two codes', () => {
        const pending = pendingIdentifier(['IT0005634792', 'IT0005612345'], null, [], 'identifier_isin')!;
        expect(needsPrimaryChoice(pending)).toBe(true);
    });
});

describe('mergeOther', () => {
    it('appends only what is missing, keeping the stored casing', () => {
        expect(mergeOther(['IT0005634792'], ['it0005634792', 'BTP Piu Sc Fb33'])).toEqual(['IT0005634792', 'BTP Piu Sc Fb33']);
    });

    it('drops blanks and nullish entries', () => {
        expect(mergeOther(['A'], ['', '   ', null, undefined, 'B'])).toEqual(['A', 'B']);
    });

    it('deduplicates within the additions themselves', () => {
        expect(mergeOther([], ['X', 'x', ' X '])).toEqual(['X']);
    });

    it('returns a new array rather than mutating the input', () => {
        const current = ['A'];
        expect(mergeOther(current, ['B'])).not.toBe(current);
        expect(current).toEqual(['A']);
    });
});

describe('demotedValues', () => {
    /** The invariant: electing a primary must never cost the other code. */
    it('keeps every candidate that is not the elected one', () => {
        expect(demotedValues('IT0005612345', ['IT0005612345', 'IT0005634792'])).toEqual(['IT0005634792']);
    });

    it('matches the elected value case-insensitively', () => {
        expect(demotedValues('it0005612345', ['IT0005612345', 'IT0005634792'])).toEqual(['IT0005634792']);
    });

    it('collapses repeats and blanks', () => {
        expect(demotedValues('A', ['B', 'b', '', null, 'A'])).toEqual(['B']);
    });

    it('demotes the stored code when the report wins the election', () => {
        expect(demotedValues('IT0005634792', ['IT0005612345', 'IT0005634792'])).toEqual(['IT0005612345']);
    });
});
