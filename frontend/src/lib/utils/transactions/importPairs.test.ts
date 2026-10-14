// @vitest-environment jsdom
/**
 * Linked pairs in the import wizard's review step (workstream L, D3/D10 of the DEGIRO work, issue #35;
 * plan 31_brimDegiro) — the pure helpers and the two renderers, written red first against the stubs
 * of `importPairs.ts` and `pairCellHtml.ts`: their signatures are final, their behaviour comes after
 * these tests. The wizard side of the same contract is `e2e/transactions/tx-import-degiro.spec.ts`.
 *
 * importPairs
 *   pairKey            `<sourceFileId>\u0000<link_uuid>`; null for a row with no `link_uuid` (missing,
 *                      null or empty). Two files reusing one `link_uuid` are two keys.
 *   linkedPairs        a pair is EXACTLY two rows under one key (one or three are no pair);
 *                      `partnerOf` both ways; `hidden` holds the leg with the positive amount — the
 *                      receiving leg, the editor's "To" — so the paying leg is the row; when both legs
 *                      have one sign, the second in input order is hidden.
 *   setPairSelected    the row and its partner get `selected`, in a new array; a row with no partner
 *                      changes alone; the input is never mutated.
 *   completePairsOnly  drops a leg whose partner is not among the selected rows; the rows that are no
 *                      pair pass; the order is kept.
 *   freshLinkFor       one `newId()` per pair key, cached in `fresh`: both legs of a pair get the same
 *                      new id, two pairs two ids; null — and no id asked — for a row with no link.
 * pairCellHtml
 *   renderFromToHtml       the editor's `renderDualHtml`: "<from>:" then the From value, a rule, "<to>:"
 *                          then the To value; both labels `min-width:<longer label + 2>ch`.
 *   renderImpliedRateHtml  a span `import-tx-pair-rate`: base → quote @ rate.toFixed(4), base the From
 *                          currency, rate |to| / |from| as `computeFxConversionInfo`; '' for one
 *                          currency or a zero amount.
 *
 * The rows are plain objects of the `MergedTx` shape, modelled on the English sample's parse (merged
 * indices as the E2E run reads them): three INTEREST (0–2), the conversion without an Order Id
 * (EUR +3.49 at 3, USD −4.08 at 4 — the receiving leg first, as in the file), TAX and DIVIDEND (5, 6),
 * the Apple order's conversion (USD +901.25 at 7, EUR −770.16 at 8), and the DEPOSIT (9). The markup
 * is parsed in jsdom and read structurally — elements, their order, their text — never by CSS class;
 * currency codes may be wrapped by `formatCurrencyCodeHtml`, so the rate chip is read by its tokens.
 */
import {describe, expect, it} from 'vitest';
import type {TransactionCreateItem} from '$lib/types';
import {computeFxConversionInfo} from '$lib/utils/currency/fxConversionHelper';
import type {MergedTx} from './importTypes';
import {completePairsOnly, freshLinkFor, linkedPairs, pairKey, setPairSelected} from './importPairs';
import {renderFromToHtml, renderImpliedRateHtml} from './pairCellHtml';

// ---------------------------------------------------------------------------
// Rows
// ---------------------------------------------------------------------------

const FILE_EN = 'file-degiro-en';
const FILE_NL = 'file-degiro-nl';
const LINK_A = '804140e0-b474-5b37-9be8-3e77c16f701f';
const LINK_B = '7a618d5d-8d54-5a46-883f-8887c695db30';
const LINK_C = '0c5d9e2a-6f1b-5c3d-9e8f-1a2b3c4d5e6f';

/** A merged row. `link` undefined leaves `link_uuid` out of the transaction altogether. */
function row(index: number, sourceFileId: string, type: string, cash: [code: string, amount: string], link?: string | null, selected = true): MergedTx {
    const tx: Record<string, unknown> = {broker_id: 7, type, date: '2025-09-16', quantity: '0', cash: {code: cash[0], amount: cash[1]}, description: type === 'FX_CONVERSION' ? 'FX Credit / FX Debit' : type};
    if (link !== undefined) tx.link_uuid = link;
    return {index, sourceFileId, tx: tx as unknown as TransactionCreateItem, selected, duplicateStatus: 'unique', dupMatches: [], todos: []};
}

/** One leg of a conversion. */
function leg(index: number, code: string, amount: string, link: string, sourceFileId = FILE_EN, selected = true): MergedTx {
    return row(index, sourceFileId, 'FX_CONVERSION', [code, amount], link, selected);
}

/** A row that is no pair. */
function lone(index: number, type: string, code: string, amount: string, selected = true): MergedTx {
    return row(index, FILE_EN, type, [code, amount], undefined, selected);
}

/** The English sample as the review gets it, in the parse's order. */
function statement(selected = true): MergedTx[] {
    return [
        lone(0, 'INTEREST', 'CZK', '3.47', selected),
        lone(1, 'INTEREST', 'EUR', '3.00', selected),
        lone(2, 'INTEREST', 'EUR', '0.75', selected),
        leg(3, 'EUR', '3.49', LINK_A, FILE_EN, selected),
        leg(4, 'USD', '-4.08', LINK_A, FILE_EN, selected),
        lone(5, 'TAX', 'USD', '-0.72', selected),
        lone(6, 'DIVIDEND', 'USD', '4.80', selected),
        leg(7, 'USD', '901.25', LINK_B, FILE_EN, selected),
        leg(8, 'EUR', '-770.16', LINK_B, FILE_EN, selected),
        lone(9, 'DEPOSIT', 'EUR', '2500.00', selected),
    ];
}

const LONE_INDICES = [0, 1, 2, 5, 6, 9];

/** `partnerOf` as sorted `[row, partner]` entries. */
function partners(pairs: ReturnType<typeof linkedPairs>): Array<[number, number]> {
    return [...pairs.partnerOf.entries()].sort((a, b) => a[0] - b[0]);
}

function hiddenOf(pairs: ReturnType<typeof linkedPairs>): number[] {
    return [...pairs.hidden].sort((a, b) => a - b);
}

function selectedIndices(rows: readonly MergedTx[]): number[] {
    return rows.filter((candidate) => candidate.selected).map((candidate) => candidate.index);
}

function snapshot<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
}

/** The legs of `statement()` by index, for readability. */
function at(rows: readonly MergedTx[], index: number): MergedTx {
    const found = rows.find((candidate) => candidate.index === index);
    if (!found) throw new Error(`No row ${index} in the fixture`);
    return found;
}

// ---------------------------------------------------------------------------
// importPairs
// ---------------------------------------------------------------------------

describe('pairKey', () => {
    it('is the file and the link_uuid, joined by a NUL', () => {
        expect(pairKey(leg(3, 'EUR', '3.49', LINK_A))).toBe(`${FILE_EN}\u0000${LINK_A}`);
    });

    it('is null for a row without a link_uuid: missing, null or empty', () => {
        expect(pairKey(lone(9, 'DEPOSIT', 'EUR', '2500.00'))).toBeNull();
        expect(pairKey(row(1, FILE_EN, 'FX_CONVERSION', ['EUR', '3.49'], null))).toBeNull();
        expect(pairKey(row(2, FILE_EN, 'FX_CONVERSION', ['EUR', '3.49'], ''))).toBeNull();
    });

    it('tells two files apart that reuse one link_uuid', () => {
        const english = pairKey(leg(3, 'EUR', '3.49', LINK_A, FILE_EN));
        const dutch = pairKey(leg(3, 'EUR', '3.49', LINK_A, FILE_NL));
        expect(english).not.toBeNull();
        expect(dutch).not.toBeNull();
        expect(english).not.toBe(dutch);
    });
});

describe('linkedPairs', () => {
    it('pairs the two legs of each conversion, each the partner of the other', () => {
        expect(partners(linkedPairs(statement()))).toEqual([
            [3, 4],
            [4, 3],
            [7, 8],
            [8, 7],
        ]);
    });

    it('hides the receiving leg — the positive amount, the editor’s "To" — so the paying leg is the row', () => {
        expect(hiddenOf(linkedPairs(statement()))).toEqual([3, 7]);
    });

    it('hides the receiving leg whichever of the two comes first', () => {
        const reversed = [...statement()].reverse();
        const pairs = linkedPairs(reversed);
        expect(hiddenOf(pairs)).toEqual([3, 7]);
        expect(partners(pairs)).toEqual([
            [3, 4],
            [4, 3],
            [7, 8],
            [8, 7],
        ]);
    });

    it('leaves every row without a link_uuid out', () => {
        const pairs = linkedPairs(statement());
        for (const index of LONE_INDICES) {
            expect(pairs.partnerOf.has(index), `row ${index} has no partner`).toBe(false);
            expect(pairs.hidden.has(index), `row ${index} is not hidden`).toBe(false);
        }
    });

    it('a link_uuid with a single leg is no pair', () => {
        const pairs = linkedPairs([leg(0, 'EUR', '3.49', LINK_A), lone(1, 'DEPOSIT', 'EUR', '100.00')]);
        expect(partners(pairs)).toEqual([]);
        expect(hiddenOf(pairs)).toEqual([]);
    });

    it('a link_uuid with three legs is no pair', () => {
        const pairs = linkedPairs([leg(0, 'EUR', '3.49', LINK_A), leg(1, 'USD', '-4.08', LINK_A), leg(2, 'USD', '-1.00', LINK_A)]);
        expect(partners(pairs)).toEqual([]);
        expect(hiddenOf(pairs)).toEqual([]);
    });

    it('two files reusing one link_uuid are two keys: one leg in each is no pair', () => {
        const pairs = linkedPairs([leg(0, 'EUR', '3.49', LINK_A, FILE_EN), leg(1, 'USD', '-4.08', LINK_A, FILE_NL)]);
        expect(partners(pairs)).toEqual([]);
        expect(hiddenOf(pairs)).toEqual([]);
    });

    it('two files reusing one link_uuid are two keys: two legs in each are two pairs, each within its file', () => {
        const pairs = linkedPairs([leg(0, 'EUR', '3.49', LINK_A, FILE_EN), leg(1, 'EUR', '3.49', LINK_A, FILE_NL), leg(2, 'USD', '-4.08', LINK_A, FILE_EN), leg(3, 'USD', '-4.08', LINK_A, FILE_NL)]);
        expect(partners(pairs)).toEqual([
            [0, 2],
            [1, 3],
            [2, 0],
            [3, 1],
        ]);
        expect(hiddenOf(pairs)).toEqual([0, 1]);
    });

    it('with both legs of one sign, hides the second in input order', () => {
        expect(hiddenOf(linkedPairs([leg(10, 'EUR', '5.00', LINK_A), leg(11, 'USD', '6.00', LINK_A)])), 'both positive').toEqual([11]);
        expect(hiddenOf(linkedPairs([leg(20, 'EUR', '-5.00', LINK_B), leg(21, 'USD', '-6.00', LINK_B)])), 'both negative').toEqual([21]);
        expect(hiddenOf(linkedPairs([leg(31, 'EUR', '5.00', LINK_C), leg(30, 'USD', '6.00', LINK_C)])), 'input order, not index order').toEqual([30]);
    });

    it('leaves its input untouched', () => {
        const rows = statement();
        const before = snapshot(rows);
        linkedPairs(rows);
        expect(rows).toEqual(before);
    });
});

describe('setPairSelected', () => {
    it('unticks both legs of a pair through the paying leg’s row', () => {
        const rows = statement(true);
        const out = setPairSelected(rows, 4, false, linkedPairs(rows));
        expect(selectedIndices(out)).toEqual([0, 1, 2, 5, 6, 7, 8, 9]);
    });

    it('unticks both legs through the receiving leg as well', () => {
        const rows = statement(true);
        const out = setPairSelected(rows, 3, false, linkedPairs(rows));
        expect(selectedIndices(out)).toEqual([0, 1, 2, 5, 6, 7, 8, 9]);
    });

    it('ticks both legs back', () => {
        const rows = statement(false);
        const out = setPairSelected(rows, 8, true, linkedPairs(rows));
        expect(selectedIndices(out)).toEqual([7, 8]);
    });

    it('a row with no partner changes alone', () => {
        const rows = statement(true);
        expect(selectedIndices(setPairSelected(rows, 9, false, linkedPairs(rows)))).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8]);
        const single = [leg(0, 'EUR', '3.49', LINK_A), lone(1, 'DEPOSIT', 'EUR', '100.00')];
        expect(selectedIndices(setPairSelected(single, 0, false, linkedPairs(single))), 'a single leg is no pair').toEqual([1]);
    });

    it('returns a new array, in the same order, with the other fields kept, and leaves its input untouched', () => {
        const rows = statement(true);
        const before = snapshot(rows);
        const out = setPairSelected(rows, 4, false, linkedPairs(rows));
        expect(out).not.toBe(rows);
        expect(rows).toEqual(before);
        expect(out.map((candidate) => candidate.index)).toEqual(rows.map((candidate) => candidate.index));
        expect(at(out, 3)).toEqual({...at(before, 3), selected: false});
        expect(at(out, 4)).toEqual({...at(before, 4), selected: false});
        expect(at(out, 7)).toEqual(at(before, 7));
    });
});

describe('completePairsOnly', () => {
    it('keeps both legs of a pair selected whole, and every row that is no pair, in their order', () => {
        const rows = statement();
        expect(completePairsOnly(rows, linkedPairs(rows)).map((candidate) => candidate.index)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    });

    it('drops a leg whose partner is not selected — the paying leg or the receiving one', () => {
        const rows = statement();
        const pairs = linkedPairs(rows);
        const withoutReceiving = rows.filter((candidate) => candidate.index !== 3);
        expect(
            completePairsOnly(withoutReceiving, pairs).map((candidate) => candidate.index),
            'the receiving leg left out: its paying leg goes too',
        ).toEqual([0, 1, 2, 5, 6, 7, 8, 9]);
        const withoutPaying = rows.filter((candidate) => candidate.index !== 8);
        expect(
            completePairsOnly(withoutPaying, pairs).map((candidate) => candidate.index),
            'the paying leg left out: its receiving leg goes too',
        ).toEqual([0, 1, 2, 3, 4, 5, 6, 9]);
    });

    it('keeps the order it is given', () => {
        const rows = statement();
        const shuffled = [9, 4, 0, 7, 3, 8].map((index) => at(rows, index));
        expect(completePairsOnly(shuffled, linkedPairs(rows)).map((candidate) => candidate.index)).toEqual([9, 4, 0, 7, 3, 8]);
    });

    it('takes any row with an index', () => {
        const pairs = linkedPairs(statement());
        const picked = [
            {index: 4, label: 'USD -4.08'},
            {index: 9, label: 'DEPOSIT'},
            {index: 7, label: 'USD 901.25'},
            {index: 8, label: 'EUR -770.16'},
        ];
        expect(completePairsOnly(picked, pairs)).toEqual([
            {index: 9, label: 'DEPOSIT'},
            {index: 7, label: 'USD 901.25'},
            {index: 8, label: 'EUR -770.16'},
        ]);
    });

    it('leaves its input untouched', () => {
        const rows = statement().filter((candidate) => candidate.index !== 3);
        const before = snapshot(rows);
        completePairsOnly(rows, linkedPairs(statement()));
        expect(rows).toEqual(before);
    });
});

describe('freshLinkFor', () => {
    /** A counting id source: `fresh-1`, `fresh-2`, … */
    function ids() {
        let calls = 0;
        return {
            newId: () => `fresh-${++calls}`,
            calls: () => calls,
        };
    }

    it('gives both legs of a pair one new id, asked for once', () => {
        const rows = statement();
        const source = ids();
        const fresh = new Map<string, string>();
        expect(freshLinkFor(at(rows, 3), fresh, source.newId)).toBe('fresh-1');
        expect(freshLinkFor(at(rows, 4), fresh, source.newId)).toBe('fresh-1');
        expect(source.calls(), 'one newId() per pair key').toBe(1);
    });

    it('gives each pair its own id, never the link_uuid of the parse', () => {
        const rows = statement();
        const source = ids();
        const fresh = new Map<string, string>();
        const links = [3, 4, 7, 8].map((index) => freshLinkFor(at(rows, index), fresh, source.newId));
        expect(links).toEqual(['fresh-1', 'fresh-1', 'fresh-2', 'fresh-2']);
        expect(links).not.toContain(LINK_A);
        expect(links).not.toContain(LINK_B);
        expect(source.calls()).toBe(2);
    });

    it('tells two files apart that reuse one link_uuid', () => {
        const source = ids();
        const fresh = new Map<string, string>();
        const english = freshLinkFor(leg(0, 'EUR', '3.49', LINK_A, FILE_EN), fresh, source.newId);
        const dutch = freshLinkFor(leg(1, 'EUR', '3.49', LINK_A, FILE_NL), fresh, source.newId);
        expect(english).not.toBeNull();
        expect(dutch).not.toBeNull();
        expect(english).not.toBe(dutch);
        expect(source.calls()).toBe(2);
    });

    it('is null for a row without a link_uuid, and asks for no id', () => {
        const source = ids();
        const fresh = new Map<string, string>();
        expect(freshLinkFor(lone(9, 'DEPOSIT', 'EUR', '2500.00'), fresh, source.newId)).toBeNull();
        expect(freshLinkFor(row(1, FILE_EN, 'FX_CONVERSION', ['EUR', '3.49'], null), fresh, source.newId)).toBeNull();
        expect(freshLinkFor(row(2, FILE_EN, 'FX_CONVERSION', ['EUR', '3.49'], ''), fresh, source.newId)).toBeNull();
        expect(source.calls()).toBe(0);
        expect(fresh.size).toBe(0);
    });

    it('keeps its ids in `fresh` under the pair key, and reuses one already there', () => {
        const rows = statement();
        const source = ids();
        const fresh = new Map<string, string>();
        const id = freshLinkFor(at(rows, 4), fresh, source.newId);
        expect(fresh.get(pairKey(at(rows, 4)) ?? '(no pair key)')).toBe(id);

        const seeded = new Map<string, string>([[pairKey(at(rows, 7)) ?? '(no pair key)', 'kept']]);
        const reused = ids();
        expect(freshLinkFor(at(rows, 8), seeded, reused.newId)).toBe('kept');
        expect(reused.calls()).toBe(0);
    });
});

// ---------------------------------------------------------------------------
// pairCellHtml
// ---------------------------------------------------------------------------

function parse(html: string): HTMLElement {
    const host = document.createElement('div');
    host.innerHTML = html;
    return host;
}

/** `a` comes before `b` in document order. */
function precedes(a: Node, b: Node): boolean {
    return (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

/** The innermost elements whose whole text is `text`: a label, found by what it says. */
function elementsSaying(host: HTMLElement, text: string): HTMLElement[] {
    return [...host.querySelectorAll<HTMLElement>('*')].filter((element) => element.textContent?.trim() === text && ![...element.children].some((child) => child.textContent?.trim() === text));
}

const FROM_VALUE = '<span data-testid="from-value">-4.08 USD</span>';
const TO_VALUE = '<span data-testid="to-value">+3.49 EUR</span>';

describe('renderFromToHtml', () => {
    it('draws the From line, one rule, then the To line', () => {
        const host = parse(renderFromToHtml(FROM_VALUE, TO_VALUE, {from: 'From', to: 'To'}));
        const rules = host.querySelectorAll('hr');
        expect(rules).toHaveLength(1);
        const from = host.querySelector('[data-testid="from-value"]');
        const to = host.querySelector('[data-testid="to-value"]');
        expect(from?.textContent).toBe('-4.08 USD');
        expect(to?.textContent).toBe('+3.49 EUR');
        expect(precedes(from as Node, rules[0]), 'the From value is above the rule').toBe(true);
        expect(precedes(rules[0], to as Node), 'the To value is below the rule').toBe(true);
    });

    it('labels each line with its label and a colon, before its value', () => {
        const host = parse(renderFromToHtml(FROM_VALUE, TO_VALUE, {from: 'Da', to: 'A'}));
        const fromLabels = elementsSaying(host, 'Da:');
        const toLabels = elementsSaying(host, 'A:');
        expect(fromLabels).toHaveLength(1);
        expect(toLabels).toHaveLength(1);
        const rule = host.querySelector('hr') as Node;
        expect(precedes(fromLabels[0], host.querySelector('[data-testid="from-value"]') as Node), 'the From label leads the From value').toBe(true);
        expect(precedes(fromLabels[0], rule), 'the From label is above the rule').toBe(true);
        expect(precedes(rule, toLabels[0]), 'the To label is below the rule').toBe(true);
        expect(precedes(toLabels[0], host.querySelector('[data-testid="to-value"]') as Node), 'the To label leads the To value').toBe(true);
    });

    it.each([
        {labels: {from: 'From', to: 'To'}, ch: 6},
        {labels: {from: 'Da', to: 'A'}, ch: 4},
        {labels: {from: 'Von', to: 'Nach'}, ch: 6},
        {labels: {from: 'De', to: 'Hacia'}, ch: 7},
    ])('pads both labels to the longer one plus two characters: $labels.from / $labels.to → $ch ch', ({labels, ch}) => {
        const host = parse(renderFromToHtml(FROM_VALUE, TO_VALUE, labels));
        for (const text of [`${labels.from}:`, `${labels.to}:`]) {
            const [label] = elementsSaying(host, text);
            expect(label, `the label ${text} is drawn`).toBeDefined();
            expect(label?.getAttribute('style') ?? '', `${text} min-width`).toMatch(new RegExp(`min-width:\\s*${ch}ch`));
        }
    });
});

/** The chip's tokens — codes, arrow, `@`, the number — whatever wraps the codes (symbol, flag). */
function rateTokens(chip: Element): string {
    return (chip.textContent?.match(/[A-Z]{3}|→|@|\d+(?:\.\d+)?/g) ?? []).join(' ');
}

/** The one rate chip of `html`. */
function chipOf(html: string): HTMLElement {
    const chips = parse(html).querySelectorAll<HTMLElement>('[data-testid="import-tx-pair-rate"]');
    expect(chips, 'one import-tx-pair-rate chip').toHaveLength(1);
    return chips[0];
}

describe('renderImpliedRateHtml', () => {
    it('USD → EUR @ 0.8554 for the conversion without an Order Id, in a span', () => {
        const chip = chipOf(renderImpliedRateHtml({code: 'USD', amount: -4.08}, {code: 'EUR', amount: 3.49}));
        expect(chip.tagName).toBe('SPAN');
        expect(rateTokens(chip)).toBe('USD → EUR @ 0.8554');
    });

    it('EUR → USD @ 1.1702 for the Apple order’s conversion', () => {
        expect(rateTokens(chipOf(renderImpliedRateHtml({code: 'EUR', amount: -770.16}, {code: 'USD', amount: 901.25})))).toBe('EUR → USD @ 1.1702');
    });

    it.each([
        {from: {code: 'USD', amount: -4.08}, to: {code: 'EUR', amount: 3.49}},
        {from: {code: 'EUR', amount: -770.16}, to: {code: 'USD', amount: 901.25}},
        {from: {code: 'GBP', amount: -1234.5}, to: {code: 'CHF', amount: 1402.37}},
        {from: {code: 'CZK', amount: -100}, to: {code: 'EUR', amount: 4.01}},
    ])('is the rate computeFxConversionInfo implies, to four decimals: $from.code → $to.code', ({from, to}) => {
        const info = computeFxConversionInfo(from.amount, from.code, to.amount, to.code);
        expect(info).not.toBeNull();
        expect(rateTokens(chipOf(renderImpliedRateHtml(from, to)))).toBe(`${info?.base} → ${info?.quote} @ ${info?.impliedRate.toFixed(4)}`);
    });

    it('reads both amounts without their sign', () => {
        expect(rateTokens(chipOf(renderImpliedRateHtml({code: 'USD', amount: 4.08}, {code: 'EUR', amount: -3.49})))).toBe('USD → EUR @ 0.8554');
    });

    it('is empty for two legs in one currency', () => {
        expect(renderImpliedRateHtml({code: 'EUR', amount: -10}, {code: 'EUR', amount: 10})).toBe('');
    });

    it('is empty when an amount is zero', () => {
        expect(renderImpliedRateHtml({code: 'USD', amount: 0}, {code: 'EUR', amount: 3.49})).toBe('');
        expect(renderImpliedRateHtml({code: 'USD', amount: -4.08}, {code: 'EUR', amount: 0})).toBe('');
    });
});
