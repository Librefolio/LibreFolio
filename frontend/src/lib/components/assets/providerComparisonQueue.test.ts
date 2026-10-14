/**
 * providerComparisonQueue — pure unit tests (R18, the "double ISIN modal").
 *
 * A provider search selection can put one identifier question on screen twice:
 * the ISIN chooser opens at once, then the metadata read the same selection
 * started lands and the comparison asks about the very same codes. This module is
 * the decision half of the fix, exercised here with no component around it:
 *
 *   - `identifierQuestion` states what the chooser asks: its field and its codes;
 *   - `asksSameQuestion` / `pruneAnsweredRows` recognise the comparison rows that
 *     chooser answers — the same field AND a proposed code among its candidates;
 *   - `decideComparison` says whether what is left opens, waits, or is dropped.
 *
 * Node environment on purpose: no DOM, no Svelte runtime. Inputs are deep-frozen,
 * so a write inside the module throws here instead of corrupting the caller.
 */
import {describe, expect, it} from 'vitest';
import type {DiffItem} from './ProviderComparisonModal.svelte';
import {asksSameQuestion, decideComparison, identifierQuestion, pruneAnsweredRows, type IdentifierQuestion} from './providerComparisonQueue';

const REPORT_ISIN = 'IT0000000001';
const PROVIDER_ISIN = 'IT0000000002';
const THIRD_ISIN = 'IT0000000003';

/** ES modules are strict: once frozen, any mutation inside the module throws. */
function frozen<T>(value: T): T {
    if (value !== null && typeof value === 'object') {
        for (const child of Object.values(value)) frozen(child);
        Object.freeze(value);
    }
    return value;
}

function identifierRow(field: string, currentValue: unknown, providerValue: unknown): DiffItem {
    return {field, label: field.replace('identifier_', '').toUpperCase(), type: 'string', currentValue, providerValue, selected: true};
}

function nameRow(providerValue: unknown = 'Provider title'): DiffItem {
    return {field: 'display_name', label: 'Name', type: 'string', currentValue: 'Selected title', providerValue, selected: true};
}

function distributionRow(field: 'sector_area' | 'geographic_area'): DiffItem {
    const [currentValue, providerValue] = field === 'sector_area' ? [{Technology: 1}, {Technology: 0.6, Health: 0.4}] : [{USA: 1}, {USA: 0.7, FRA: 0.3}];
    return {field, label: field, type: 'distribution', currentValue, providerValue, selected: true};
}

/** The chooser's own row: the report code is current, the provider proposes its quoted code. */
function answeredIsinRow(): DiffItem {
    return identifierRow('identifier_isin', REPORT_ISIN, PROVIDER_ISIN);
}

/**
 * Hand-built rather than produced by `identifierQuestion`, so a defect in that
 * constructor fails its own block instead of cascading through every other one.
 */
function isinQuestion(): IdentifierQuestion {
    return frozen({field: 'identifier_isin', candidates: [PROVIDER_ISIN, REPORT_ISIN]});
}

describe('identifierQuestion', () => {
    it('names the comparison field of the chooser type and keeps its codes in order', () => {
        expect(identifierQuestion('ISIN', [PROVIDER_ISIN, REPORT_ISIN])).toEqual({field: 'identifier_isin', candidates: [PROVIDER_ISIN, REPORT_ISIN]});
    });

    it('derives the field from the lower-cased identifier type', () => {
        expect(identifierQuestion('TICKER', ['SYN-A']).field).toBe('identifier_ticker');
        expect(identifierQuestion('Cusip', ['123456789']).field).toBe('identifier_cusip');
    });

    it('trims and upper-cases the codes, drops blanks and duplicates, and keeps first-seen order', () => {
        const question = identifierQuestion('ISIN', ['  it0000000002 ', '', REPORT_ISIN, '   ', PROVIDER_ISIN, '\tit0000000001\n']);
        expect(question.candidates).toEqual([PROVIDER_ISIN, REPORT_ISIN]);
    });

    it('asks about no code when every value is blank', () => {
        expect(identifierQuestion('ISIN', ['', '   '])).toEqual({field: 'identifier_isin', candidates: []});
    });

    it('reads its codes without touching them', () => {
        const codes = frozen([' it0000000002 ', REPORT_ISIN]);
        expect(identifierQuestion('ISIN', codes).candidates).toEqual([PROVIDER_ISIN, REPORT_ISIN]);
        expect(codes).toEqual([' it0000000002 ', REPORT_ISIN]);
    });
});

describe('asksSameQuestion', () => {
    it('recognises the identifier row proposing any code the chooser offered', () => {
        expect(asksSameQuestion(answeredIsinRow(), isinQuestion())).toBe(true);
        // Answered either way round: a provider proposing the report's own code is still that question.
        expect(asksSameQuestion(identifierRow('identifier_isin', PROVIDER_ISIN, REPORT_ISIN), isinQuestion())).toBe(true);
    });

    it('normalises the proposed code (whitespace, case) before comparing it', () => {
        expect(asksSameQuestion(identifierRow('identifier_isin', REPORT_ISIN, '  it0000000002\t'), isinQuestion())).toBe(true);
    });

    it('compares the string form of a proposal that is not a string', () => {
        const cusip: IdentifierQuestion = frozen({field: 'identifier_cusip', candidates: ['123456789']});
        expect(asksSameQuestion(identifierRow('identifier_cusip', '987654321', 123456789), cusip)).toBe(true);
    });

    it('treats a third code as a different question', () => {
        expect(asksSameQuestion(identifierRow('identifier_isin', REPORT_ISIN, THIRD_ISIN), isinQuestion())).toBe(false);
    });

    it('treats the same code under another identifier type as a different question', () => {
        expect(asksSameQuestion(identifierRow('identifier_ticker', 'SYN-A', PROVIDER_ISIN), isinQuestion())).toBe(false);
    });

    it('never matches a non-identifier row, even one whose value equals a candidate', () => {
        expect(asksSameQuestion(nameRow(PROVIDER_ISIN), isinQuestion())).toBe(false);
        expect(asksSameQuestion(distributionRow('sector_area'), isinQuestion())).toBe(false);
    });

    it('never matches a non-identifier row, even against a hand-built question naming that very field', () => {
        // The contract's "never" is literal, not a by-product of field equality.
        const nameQuestion: IdentifierQuestion = frozen({field: 'display_name', candidates: ['PROVIDER TITLE']});
        expect(asksSameQuestion(nameRow('Provider title'), nameQuestion)).toBe(false);
    });

    it('reads the row and the question without touching them', () => {
        const row = frozen(identifierRow('identifier_isin', REPORT_ISIN, ' it0000000002 '));
        const question = isinQuestion();
        expect(asksSameQuestion(row, question)).toBe(true);
        expect(row).toEqual(identifierRow('identifier_isin', REPORT_ISIN, ' it0000000002 '));
        expect(question).toEqual({field: 'identifier_isin', candidates: [PROVIDER_ISIN, REPORT_ISIN]});
    });
});

describe('pruneAnsweredRows', () => {
    const tickerQuestion = (): IdentifierQuestion => frozen({field: 'identifier_ticker', candidates: ['SYN-A', 'SYN-B']});

    it('removes exactly the rows a question answers and keeps the rest in order', () => {
        const rows = frozen([answeredIsinRow(), identifierRow('identifier_ticker', 'SYN-A', 'SYN-C'), nameRow(), distributionRow('sector_area'), distributionRow('geographic_area')]);
        expect(pruneAnsweredRows(rows, [isinQuestion()])).toEqual([identifierRow('identifier_ticker', 'SYN-A', 'SYN-C'), nameRow(), distributionRow('sector_area'), distributionRow('geographic_area')]);
    });

    it('applies every question it is given', () => {
        const rows = frozen([answeredIsinRow(), nameRow(), identifierRow('identifier_ticker', 'SYN-A', ' syn-b')]);
        expect(pruneAnsweredRows(rows, [isinQuestion(), tickerQuestion()])).toEqual([nameRow()]);
    });

    it('keeps an identifier row proposing a third code', () => {
        const rows = frozen([identifierRow('identifier_isin', PROVIDER_ISIN, THIRD_ISIN), nameRow()]);
        expect(pruneAnsweredRows(rows, [isinQuestion()])).toEqual([identifierRow('identifier_isin', PROVIDER_ISIN, THIRD_ISIN), nameRow()]);
    });

    it('keeps non-identifier and distribution rows whatever their values', () => {
        const rows = frozen([nameRow(PROVIDER_ISIN), distributionRow('sector_area'), distributionRow('geographic_area')]);
        expect(pruneAnsweredRows(rows, [isinQuestion()])).toEqual([nameRow(PROVIDER_ISIN), distributionRow('sector_area'), distributionRow('geographic_area')]);
    });

    it('leaves nothing when the chooser answered every row', () => {
        expect(pruneAnsweredRows(frozen([answeredIsinRow()]), [isinQuestion()])).toEqual([]);
    });

    it('returns a new array and leaves its input untouched, even with nothing to prune', () => {
        const rows = frozen([answeredIsinRow(), nameRow()]);
        const untouched = pruneAnsweredRows(rows, []);
        expect(untouched).toEqual([answeredIsinRow(), nameRow()]);
        expect(untouched).not.toBe(rows);
        expect(pruneAnsweredRows(rows, [isinQuestion()])).toEqual([nameRow()]);
        expect(rows).toEqual([answeredIsinRow(), nameRow()]);
    });

    it('composes with identifierQuestion over untidy chooser and provider codes', () => {
        const asked = identifierQuestion('ISIN', [' it0000000002', 'IT0000000001 ']);
        const rows = frozen([identifierRow('identifier_isin', REPORT_ISIN, 'It0000000002 '), nameRow()]);
        expect(pruneAnsweredRows(rows, [asked])).toEqual([nameRow()]);
    });
});

describe('decideComparison', () => {
    it('opens what is left once no prompt is open', () => {
        const decision = decideComparison({differences: frozen([answeredIsinRow(), nameRow()]), questions: [isinQuestion()], promptOpen: false, current: true});
        expect(decision).toEqual({kind: 'open', differences: [nameRow()]});
    });

    it('holds what is left while a prompt is still open', () => {
        const decision = decideComparison({differences: frozen([answeredIsinRow(), nameRow()]), questions: [isinQuestion()], promptOpen: true, current: true});
        expect(decision).toEqual({kind: 'hold', differences: [nameRow()]});
    });

    it.each([false, true])('drops a comparison the chooser fully answered (promptOpen=%s)', (promptOpen) => {
        expect(decideComparison({differences: frozen([answeredIsinRow()]), questions: [isinQuestion()], promptOpen, current: true})).toEqual({kind: 'drop'});
    });

    it.each([false, true])('drops a comparison with no difference at all (promptOpen=%s)', (promptOpen) => {
        expect(decideComparison({differences: frozen([]), questions: [isinQuestion()], promptOpen, current: true})).toEqual({kind: 'drop'});
        expect(decideComparison({differences: frozen([]), questions: [], promptOpen, current: true})).toEqual({kind: 'drop'});
    });

    it.each([false, true])('drops a stale comparison before weighing anything else (promptOpen=%s)', (promptOpen) => {
        // Rows would remain in both calls: only staleness can explain the drop.
        expect(decideComparison({differences: frozen([answeredIsinRow(), nameRow()]), questions: [isinQuestion()], promptOpen, current: false})).toEqual({kind: 'drop'});
        expect(decideComparison({differences: frozen([nameRow()]), questions: [], promptOpen, current: false})).toEqual({kind: 'drop'});
    });

    it('keeps a third code for the user to decide', () => {
        const decision = decideComparison({differences: frozen([identifierRow('identifier_isin', REPORT_ISIN, THIRD_ISIN)]), questions: [isinQuestion()], promptOpen: false, current: true});
        expect(decision).toEqual({kind: 'open', differences: [identifierRow('identifier_isin', REPORT_ISIN, THIRD_ISIN)]});
    });

    it('opens an unanswered comparison whole, as a new array', () => {
        const rows = frozen([answeredIsinRow(), nameRow(), distributionRow('sector_area')]);
        const decision = decideComparison({differences: rows, questions: [], promptOpen: false, current: true});
        expect(decision).toEqual({kind: 'open', differences: [answeredIsinRow(), nameRow(), distributionRow('sector_area')]});
        expect(decision.kind === 'open' ? decision.differences : null).not.toBe(rows);
    });

    it('reads its input without touching it, whatever it decides', () => {
        const rows = frozen([answeredIsinRow(), nameRow()]);
        const questions = frozen([isinQuestion()]);
        const kinds = [false, true].flatMap((promptOpen) => [false, true].map((current) => decideComparison({differences: rows, questions, promptOpen, current}).kind));
        expect(kinds).toEqual(['drop', 'open', 'drop', 'hold']);
        expect(rows).toEqual([answeredIsinRow(), nameRow()]);
        expect(questions).toEqual([{field: 'identifier_isin', candidates: [PROVIDER_ISIN, REPORT_ISIN]}]);
    });
});
